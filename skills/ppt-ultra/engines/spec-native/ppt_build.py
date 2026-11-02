# -*- coding: utf-8 -*-
"""
Spec Native engine · deck 规格 JSON → 可编辑 .pptx（pptx_style.Deck）

模型只出语义（每页 layout + 内容字段），坐标全部在这里算；校验失败（缺字段 / 未知版式 / 假数据图表）直接抛 ValueError，不做兜底页。
入口：spec_to_pptx.py（CLI）；也可 `from ppt_build import build`。

spec 顶层：
  { "title", "subtitle", "author", "date", "language": "zh|en"（默认 zh）,
    "style"?: {"palette": {...}, "fonts": {"cjk","latin"}, "series_colors": [...]}（整体覆盖风格，见 pptx_style.apply_style）,
    "thanks_line"?: 封底致辞一句（默认不出）,
    "references"?: [{"num": 1, "title", "path"?, "changed"?, "author"?, "url"?}]（正文角标 [n] 的出处，给了就在末尾加一页引用出处页）,
    "slides": [ { "layout": ..., "title", "subtitle"?, "takeaway"?, "notes"?, 各版式自己的字段 } ] }
版式清单与字段见 references/spec-native-layouts.md；封底「谢谢」页固定由本脚本追加（spec 里的 thanks 页会被忽略）。
图片 / logo 路径：绝对路径原样用；相对路径相对 spec 文件所在目录（build 的 base_dir）。
"""
import json
import os
import sys
from datetime import date as _date

from PIL import Image
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

import pptx_style
from pptx_style import Deck, C, SLIDE_W, SLIDE_H, MARGIN, _fill_paragraph
import graph_layout   # 按内容画的图示（flow / swimlane）
import ppt_extra      # 扩展版式（timeline / layers / hierarchy / cycle / funnel / compare / pros_cons / matrix / kpi / quote / agenda / icons / image_callout / image_bg）

LAYOUTS = {'cover', 'section', 'bullets', 'cards', 'table', 'numbers', 'chart', 'image', 'image_split', 'image_grid', 'diagram', 'flow', 'swimlane', 'sequence', 'vendors', 'logo_table', 'closing', 'thanks', 'references'} | set(ppt_extra.RENDERERS)
CONTENT_W = SLIDE_W - 2 * MARGIN
BODY_Y = 1.35        # 标题（含副题）下方正文起点
BODY_BOTTOM = 6.55   # 结论条上沿之上

# 固定文案（按 spec.language 取；模型产出的内容本身不经这里）
I18N = {
    'zh': dict(thanks='谢谢', refs_title='引用出处', refs_sub='正文角标 [n] 对应的资料来源', card_default='要点 {n}',
               pros='优势', cons='不足', vs='VS', versus='对比', modified='修改 ', value='值', ql='《', qr='》'),
    'en': dict(thanks='Thank you', refs_title='References', refs_sub='Sources cited as [n] in the slides', card_default='Point {n}',
               pros='Pros', cons='Cons', vs='VS', versus='vs', modified='updated ', value='Value', ql='“', qr='”'),
}


def _lang(spec):
    lang = str(spec.get('language') or 'zh').lower()
    if lang not in I18N:
        raise ValueError(f'language 只支持 {sorted(I18N)}，收到 {lang!r}')
    return lang


def _bullets(lines):
    return [f'• {str(t).strip()}' for t in lines if str(t).strip()]


def _need(slide, key):
    v = slide.get(key)
    if v in (None, '', [], {}):
        raise ValueError(f'第 {slide.get("_no", "?")} 页（{slide.get("layout")}）缺 {key}')
    return v


def _chart_args(ch, page_no):
    """chart 对象 → (kind, categories, series)。兼容旧格式 {values, horizontal}；数值无区分度直接抛错。"""
    kind = ch.get('type') or ('bar' if ch.get('horizontal', True) else 'column')
    if kind not in Deck.CHART_TYPES:
        raise ValueError(f'第 {page_no} 页图表类型 {kind!r} 不支持（可用 {sorted(Deck.CHART_TYPES)}）')
    cats = [str(c) for c in ch.get('categories') or []]
    series = ch.get('series')
    if not series:
        series = [{'name': ch.get('unit') or I18N['zh']['value'], 'values': ch.get('values') or []}]
    if not cats:
        raise ValueError(f'第 {page_no} 页图表 categories 为空')
    if kind in ('pie', 'doughnut') and len(series) != 1:
        raise ValueError(f'第 {page_no} 页饼图 / 环图只能有 1 个系列')
    all_vals = []
    for sr in series:
        vals = [float(v) for v in sr.get('values') or []]
        if len(vals) != len(cats):
            raise ValueError(f'第 {page_no} 页图表系列「{sr.get("name", "")}」数值数 {len(vals)} 与类别数 {len(cats)} 不一致')
        sr['values'] = vals
        all_vals += vals
    if len(set(all_vals)) < 2:
        raise ValueError(f'第 {page_no} 页图表数值没有区分度（{all_vals}），不是真实数据，不应使用 chart 版式')
    return kind, cats, series


# ---- 图示重绘（diagram 版式）：dg 规格（形状 + 折线连接线）→ 原生形状，整体等比缩放进内容区 ----
DIAGRAM_SHAPES = {
    'round_rect': MSO_SHAPE.ROUNDED_RECTANGLE, 'rect': MSO_SHAPE.RECTANGLE, 'diamond': MSO_SHAPE.DIAMOND,
    'ellipse': MSO_SHAPE.OVAL, 'circle': MSO_SHAPE.OVAL, 'star': MSO_SHAPE.STAR_5_POINT, 'triangle': MSO_SHAPE.ISOSCELES_TRIANGLE,
    'hexagon': MSO_SHAPE.HEXAGON, 'parallelogram': MSO_SHAPE.PARALLELOGRAM, 'cylinder': MSO_SHAPE.CAN,
    'cloud': MSO_SHAPE.CLOUD, 'right_arrow': MSO_SHAPE.RIGHT_ARROW, 'left_arrow': MSO_SHAPE.LEFT_ARROW,
}


def _luma(hexcolor):
    r, g, b = int(hexcolor[0:2], 16), int(hexcolor[2:4], 16), int(hexcolor[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _fit_one_line(text, w_in, base=10.5, lo=6):
    """不折行：挑能把整句放进宽度的最大字号（中日韩字 1 em、其它 0.55 em）"""
    ems = sum(1.0 if ord(ch) > 0x2E7F else 0.55 for ch in text) or 1
    for size in [base, 10, 9, 8, 7, lo]:
        if ems * size / 72 <= w_in - 0.12:
            return size
    return lo


def _fit_font(text, w_in, h_in, base=12, lo=6):
    """按框大小挑最大能放下的字号（中文按 1 字 ≈ 1 em 宽估算）"""
    lines = [ln for ln in text.split('\n')]
    for size in [base, 11, 10, 9, 8, 7, lo]:
        per_line = max(1, int((w_in - 0.1) * 72 / size))
        n = sum(max(1, -(-len(ln) // per_line)) for ln in lines) if lines else 1
        if n * size * 1.25 <= (h_in - 0.06) * 72:
            return size
    return lo


def _arrow_end(line, tag):
    """a:ln 里 headEnd 必须在 tailEnd 之前（schema 顺序；双向箭头先写 tailEnd 再写 headEnd 会被 Open XML 校验器判非法）"""
    lnxml = line.line._get_or_add_ln()
    el = etree.Element(qn(tag))
    el.set('type', 'triangle'); el.set('w', 'med'); el.set('len', 'med')
    tail = lnxml.find(qn('a:tailEnd'))
    if tag == 'a:headEnd' and tail is not None:
        tail.addprevious(el)
    else:
        ext = lnxml.find(qn('a:extLst'))
        if ext is not None:
            ext.addprevious(el)
        else:
            lnxml.append(el)


def _draw_diagram(d, sl, dg, x0, y0, box_w, box_h, name='dg'):
    b = dg['bounds']
    scale = min(box_w / b['w'], box_h / b['h'])
    ox = x0 + (box_w - b['w'] * scale) / 2
    oy = y0 + (box_h - b['h'] * scale) / 2
    X = lambda v: ox + (v - b['x']) * scale
    Y = lambda v: oy + (v - b['y']) * scale
    S = lambda v: v * scale
    # 1) 容器与形状
    for i, n in enumerate(dg['nodes']):
        w, h = S(n['w']), S(n['h'])
        if w <= 0 or h <= 0:
            continue
        nm = f"{name}.n{i + 1}"
        if n['kind'] == 'group':
            if n.get('laneLabelW'):   # 泳道：容器 + 左侧主色标签块（swimlane 版式）
                d.rect(sl, X(n['x']), Y(n['y']), w, h, fill=C['bg'], line=C['border'], line_w=0.75, name=nm)
                lw = S(n['laneLabelW'])
                d.label(sl, X(n['x']), Y(n['y']), lw, h, n.get('text') or '', size=_fit_one_line(n.get('text') or '', lw), name=nm + '.label')
                continue
            d.rect(sl, X(n['x']), Y(n['y']), w, h, fill=C['bg'], line=C['border'], line_w=0.75, name=nm,
                   text=n.get('text') or None, size=9, color=C['mid'], align='left', anchor='top')
            continue
        if n['kind'] == 'text':
            size = _fit_font(n.get('text', ''), w, h, base=11)
            d.text(sl, X(n['x']), Y(n['y']), w, h, n.get('text', ''), size=size, color=C['ink'], name=nm,
                   line_spacing=1.1, margins=(0.02, 0.02))
            continue
        fill = (n.get('fill') or '').lstrip('#').upper()
        if fill:
            text_color = C['white'] if _luma(fill) < 140 else C['ink']
            line = None
        else:
            fill = C['pale']; text_color = C['ink']; line = C['primary']
        shape = DIAGRAM_SHAPES.get(n.get('shape'), MSO_SHAPE.ROUNDED_RECTANGLE)
        text = n.get('text', '')
        size = _fit_font(text, w, h, base=11) if text else 8
        d.rect(sl, X(n['x']), Y(n['y']), w, h, fill=fill, line=line, line_w=0.75, shape=shape, name=nm,
               text=text or None, size=size, color=text_color, align='center', anchor='middle',
               margins=(0.04, 0.02), line_spacing=1.05)
    # 2) 连线：逐段直线，末段（或首段）加箭头；标签放折线中点
    for j, e in enumerate(dg['edges']):
        pts = [(X(p['x']), Y(p['y'])) for p in e['points']]
        segs = list(zip(pts[:-1], pts[1:]))
        for k, ((x1, y1), (x2, y2)) in enumerate(segs):
            ln = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
            ln.name = f"{name}.e{j + 1}.{k + 1}"
            ln.line.color.rgb = RGBColor.from_string(C['gray']); ln.line.width = Pt(1)
            if e.get('style') == 'dashed':
                ln.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            if k == len(segs) - 1 and e.get('endArrow'):
                _arrow_end(ln, 'a:tailEnd')
            if k == 0 and e.get('startArrow'):
                _arrow_end(ln, 'a:headEnd')
        if e.get('label'):
            # 标签放最长的横段中点（没有横段就放最长竖段中点），略偏上：折线半长点常落在竖段上压住节点
            horiz = [s_ for s_ in segs if abs(s_[0][1] - s_[1][1]) < 0.01]
            pool = horiz or segs
            (x1, y1), (x2, y2) = max(pool, key=lambda s_: ((s_[1][0] - s_[0][0]) ** 2 + (s_[1][1] - s_[0][1]) ** 2))
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            size = 7 if scale >= 0.8 else 6
            label = e['label'] if len(e['label']) <= 24 else e['label'][:24] + '…'
            lw = min(1.6, max(0.4, len(label) * size * 0.0125 + 0.08)); lh = 0.18
            if horiz:
                my -= lh / 2 + 0.02
            d.text(sl, mx - lw / 2, my - lh / 2, lw, lh, label, size=size, color=C['gray'], align='center', anchor='middle',
                   name=f"{name}.e{j + 1}.label", fill=C['white'], margins=(0.02, 0.0), line_spacing=1.0)
    return (ox, oy, b['w'] * scale, b['h'] * scale)   # 实际绘制区域（图注贴着它放）


def _picture(sl, img_path, x, y, box_w, box_h, name, page_no, top=False):
    """图片等比缩放放进框内（默认居中；top=True 贴框顶，图文页与右侧要点顶对齐），加细边框；返回 (px, py, pw, ph)"""
    if not os.path.isfile(img_path):
        raise ValueError(f'第 {page_no} 页图片文件不存在：{img_path}')
    with Image.open(img_path) as im:
        iw, ih = im.size
    scale = min(box_w / iw, box_h / ih)
    pw, ph = iw * scale, ih * scale
    px, py = x + (box_w - pw) / 2, (y if top else y + (box_h - ph) / 2)
    pic = sl.shapes.add_picture(img_path, Inches(px), Inches(py), Inches(pw), Inches(ph))
    pic.name = name
    pic.line.color.rgb = RGBColor.from_string(C['border']); pic.line.width = Pt(0.75)
    return px, py, pw, ph


def _logo_or_chip(d, sl, x, y, w, h, name, logo_path, label, chip_size=10.5):
    """厂商标识：有 logo 文件就等比放进 (w×h) 框内居中；没有就画名称标牌（主色圆角块 + 白字）"""
    if logo_path:
        if not os.path.isfile(logo_path):
            raise ValueError(f'logo 文件不存在：{logo_path}')
        with Image.open(logo_path) as im:
            iw, ih = im.size
        scale = min(w / iw, h / ih)
        pw, ph = iw * scale, ih * scale
        pic = sl.shapes.add_picture(logo_path, Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))
        pic.name = name
        return
    d.rect(sl, x, y, w, h, fill=C['primary'], line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=name + '.chip',
           text=label, size=_fit_one_line(label, w, base=chip_size), bold=True, color=C['white'], margins=(0.06, 0.02))


def _figure_side(d, sl, s, h, box_w, cap_h, name, fig=None):
    """图示页共用：图注（贴着实际绘制区域下沿，图矮时不会掉到页底）+ 右侧解读要点（diagram / flow / swimlane / sequence）"""
    if s.get('caption'):
        cap_y = BODY_Y + h - cap_h
        if fig:
            cap_y = min(cap_y, fig[1] + fig[3] + 0.12)
        d.text(sl, MARGIN, cap_y, box_w, cap_h, s['caption'], size=10.5, color=C['mid'], align='center',
               name=name + '.caption', margins=(0, 0))
    if s.get('bullets'):
        d.text(sl, MARGIN + box_w + 0.3, BODY_Y, CONTENT_W - box_w - 0.3, h, _bullets(s['bullets']), size=12,
               color=C['ink'], name='body', line_spacing=1.3, space_after=6, margins=(0.05, 0.05))


def _draw_sequence(d, sl, seq, x0, y0, w, h, name='seq'):
    """时序图（公式布局）：参与者头框 + 虚线生命线 + 编号消息；sync 实线、async 实线灰、return 虚线灰"""
    parts = [str(p).strip() for p in seq['participants']]
    msgs = seq['messages']
    n = len(parts)
    col = w / n
    px = [x0 + col * (i + 0.5) for i in range(n)]
    head_h, head_w = 0.45, min(col - 0.25, 2.2)
    for i, p in enumerate(parts):
        d.label(sl, px[i] - head_w / 2, y0, head_w, head_h, p, size=_fit_one_line(p, head_w), name=f'{name}.p{i + 1}')
        ln = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(px[i]), Inches(y0 + head_h), Inches(px[i]), Inches(y0 + h))
        ln.name = f'{name}.life{i + 1}'; ln.line.color.rgb = RGBColor.from_string(C['border']); ln.line.width = Pt(1)
        ln.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    row_h = min(0.62, (h - head_h - 0.35) / len(msgs))
    for k, m in enumerate(msgs):
        y = y0 + head_h + 0.42 + k * row_h
        x1, x2 = px[parts.index(str(m['from']))], px[parts.index(str(m['to']))]
        kind = m.get('kind') or 'sync'
        ln = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y), Inches(x2), Inches(y))
        ln.name = f'{name}.m{k + 1}'
        ln.line.color.rgb = RGBColor.from_string(C['secondary'] if kind == 'sync' else C['gray']); ln.line.width = Pt(1.25)
        if kind == 'return':
            ln.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        _arrow_end(ln, 'a:tailEnd')
        left = min(x1, x2)
        d.badge(sl, left + 0.12, y - 0.34, k + 1, d=0.24, name=f'{name}.m{k + 1}.no')
        d.text(sl, left + 0.42, y - 0.36, abs(x2 - x1) - 0.55, 0.3, str(m['text']).strip(), size=9, color=C['ink'], anchor='middle',
               name=f'{name}.m{k + 1}.label', margins=(0.02, 0))
    return (x0, y0, w, h)


def _body_h(slide):
    return (BODY_BOTTOM if slide.get('takeaway') else SLIDE_H - 0.6) - BODY_Y


def _thanks_slide(d, spec, i, total, t):
    """封底：与封面同底色，大号「谢谢」+ 标题 / 制作人 / 日期。致辞行只在 spec 给了 thanks_line 时才出"""
    sl = d.slide()
    d.rect(sl, 0, 0, SLIDE_W, SLIDE_H, fill=C['bg'], line=None, name='thanks.bg')
    d.rect(sl, 0, 2.55, 0.32, 1.9, fill=C['primary'], line=None, name='thanks.bar')
    d.text(sl, 0.75, 2.35, CONTENT_W - 0.3, 1.3, t['thanks'], size=44, bold=True, color=C['primary'], anchor='middle',
           name='thanks.title', margins=(0, 0))
    if spec.get('thanks_line'):
        d.text(sl, 0.75, 3.7, CONTENT_W - 0.3, 0.5, spec['thanks_line'], size=16, color=C['gray'],
               name='thanks.sub', margins=(0, 0))
    meta = ' · '.join([x for x in [spec.get('title'), spec.get('author'), spec.get('date')] if x])
    if meta:
        d.rule(sl, 0.75, 5.35, 3.2, weight=1.5, name='thanks.rule')
        d.text(sl, 0.75, 5.45, CONTENT_W - 0.3, 0.4, meta, size=12, color=C['mid'], name='thanks.meta', margins=(0, 0))
    d.text(sl, SLIDE_W - MARGIN - 1.0, SLIDE_H - 0.27, 1.0, 0.22, f'{i} / {total}', size=9, color=C['mid'],
           align='right', name='pageno', margins=(0, 0))


def _references_slide(d, spec, refs, i, total, t):
    """引用出处页（角标对应的出处单独一页放在最后，不计入有效页数）：
    [n] 《标题》 · 位置 · 修改日期 · 作者，条数多时分两栏；链接放在条目下一行小字"""
    sl = d.slide()
    d.title(sl, t['refs_title'], sub=t['refs_sub'])
    n = len(refs)
    cols = 2 if n > 7 else 1
    per = -(-n // cols)
    gap = 0.3
    col_w = (CONTENT_W - gap * (cols - 1)) / cols
    size = 10.5 if n <= 7 else (9.5 if n <= 14 else 8.5)
    for c in range(cols):
        chunk = refs[c * per:(c + 1) * per]
        paras = []
        for r in chunk:
            meta = ' · '.join([x for x in [r.get('path') or '', (t['modified'] + str(r.get('changed'))[:10]) if r.get('changed') else '', r.get('author') or ''] if x])
            head = [(f"[{r.get('num')}] ", {'bold': True, 'color': C['primary']}), (f"{t['ql']}{r.get('title', '')}{t['qr']}", {'bold': True})]
            if meta:
                head.append((f'  {meta}', {'color': C['gray'], 'size': max(7.5, size - 1.5)}))
            paras.append(head)
            if r.get('url'):
                paras.append([(str(r['url']), {'color': C['mid'], 'size': max(7, size - 2.5)})])
        d.text(sl, MARGIN + c * (col_w + gap), BODY_Y, col_w, SLIDE_H - BODY_Y - 0.5, paras, size=size, color=C['ink'],
               name=f'refs{c + 1}', line_spacing=1.15, space_after=5, margins=(0.05, 0.05))
    d.page_number(sl, total)


def _resolve(base_dir, p):
    """图片 / logo 路径：绝对路径原样；相对路径相对 base_dir（spec 所在目录）"""
    p = str(p or '').strip()
    if not p or os.path.isabs(p) or not base_dir:
        return p
    return os.path.normpath(os.path.join(base_dir, p))


def _resolve_paths(spec, base_dir):
    for s in spec.get('slides') or []:
        if isinstance(s.get('image'), str):
            s['image'] = _resolve(base_dir, s['image'])
        for im_ in (s.get('images') or []) if isinstance(s.get('images'), list) else []:
            if isinstance(im_, dict) and im_.get('image'):
                im_['image'] = _resolve(base_dir, im_['image'])
        for v in (s.get('vendors') or []) if isinstance(s.get('vendors'), list) else []:
            if isinstance(v, dict):
                lp = v.get('logo') or v.get('logoPath')
                if lp:
                    v['logoPath'] = _resolve(base_dir, lp)
        if isinstance(s.get('logos'), dict):
            s['logos'] = {k: _resolve(base_dir, v) for k, v in s['logos'].items()}


def build(spec, out_path, base_dir=None):
    """spec dict → pptx 文件；返回 (总页数, 图表数)。base_dir：相对图片路径的基准目录。"""
    if not isinstance(spec, dict):
        raise ValueError('spec 须为 JSON 对象')
    lang = _lang(spec)
    t = I18N[lang]
    if spec.get('style'):
        pptx_style.apply_style(spec['style'])
    _resolve_paths(spec, base_dir)
    slides = [s for s in (spec.get('slides') or []) if s.get('layout') not in ('thanks', 'references')]
    if not slides:
        raise ValueError('spec.slides 为空')
    slides = slides + [{'layout': 'thanks'}]   # 封底固定由系统追加，模型不用产出
    refs = [r for r in (spec.get('references') or []) if isinstance(r, dict) and r.get('num')]
    if refs:
        slides = slides + [{'layout': 'references'}]   # 引用出处页：最后一页，不计入有效页数
    total = len(slides)
    d = Deck()
    chart_count = 0
    for i, s in enumerate(slides, 1):
        s['_no'] = i
        layout = s.get('layout')
        if layout not in LAYOUTS:
            raise ValueError(f'第 {i} 页未知版式 {layout!r}（可用 {sorted(LAYOUTS)}）')
        if layout == 'thanks':
            _thanks_slide(d, spec, i, total, t)
            continue
        if layout == 'references':
            _references_slide(d, spec, refs, i, total, t)
            continue
        sl = d.slide()
        if layout == 'cover':
            d.rect(sl, 0, 0, SLIDE_W, SLIDE_H, fill=C['bg'], line=None, name='cover.bg')
            d.rect(sl, 0, 2.55, 0.32, 1.9, fill=C['primary'], line=None, name='cover.bar')
            d.text(sl, 0.75, 2.4, CONTENT_W - 0.3, 1.4, _need(s, 'title'), size=34, bold=True, color=C['primary'],
                   anchor='middle', name='cover.title', margins=(0, 0), line_spacing=1.1)
            if s.get('subtitle'):
                d.text(sl, 0.75, 3.85, CONTENT_W - 0.3, 0.6, s['subtitle'], size=16, color=C['gray'], anchor='top',
                       name='cover.sub', margins=(0, 0))
            meta = ' · '.join([x for x in [spec.get('author'), spec.get('date')] if x])
            if meta:
                d.rule(sl, 0.75, 5.35, 3.2, weight=1.5, name='cover.rule')
                d.text(sl, 0.75, 5.45, CONTENT_W - 0.3, 0.4, meta, size=12, color=C['mid'], name='cover.meta', margins=(0, 0))
            continue
        if layout == 'section':
            d.rect(sl, 0, 0, SLIDE_W, SLIDE_H, fill=C['primary'], line=None, name='section.bg')
            d.text(sl, 0.9, 2.6, CONTENT_W, 1.1, _need(s, 'title'), size=32, bold=True, color=C['white'],
                   anchor='middle', name='section.title', margins=(0, 0))
            if s.get('subtitle'):
                d.text(sl, 0.9, 3.75, CONTENT_W, 0.9, s['subtitle'], size=14, color='DCE6F5', name='section.sub',
                       margins=(0, 0), line_spacing=1.2)
            d.text(sl, SLIDE_W - MARGIN - 1.0, SLIDE_H - 0.27, 1.0, 0.22, f'{i} / {total}', size=9, color='DCE6F5',
                   align='right', name='pageno', margins=(0, 0))
            continue
        if layout == 'closing':
            d.rect(sl, 0, 0, SLIDE_W, SLIDE_H, fill=C['bg'], line=None, name='closing.bg')
            d.text(sl, 0.75, 1.3, CONTENT_W - 0.3, 0.8, _need(s, 'title'), size=28, bold=True, color=C['primary'],
                   anchor='middle', name='closing.title', margins=(0, 0))
            d.rule(sl, 0.75, 2.15, CONTENT_W - 0.3, weight=2, name='closing.rule')
            if s.get('bullets'):
                d.text(sl, 0.75, 2.4, CONTENT_W - 0.3, 3.6, _bullets(s['bullets']), size=14, color=C['ink'],
                       name='closing.body', line_spacing=1.35, space_after=6, margins=(0, 0))
            if s.get('takeaway'):
                d.strip(sl, s['takeaway'], y=6.35, h=0.55, size=14)
            d.page_number(sl, total)
            continue

        ctx = dict(d=d, C=C, MARGIN=MARGIN, BODY_Y=BODY_Y, CONTENT_W=CONTENT_W, SLIDE_W=SLIDE_W, SLIDE_H=SLIDE_H, total=total,
                   need=_need, bullets=_bullets, fit_font=_fit_font, fit_one_line=_fit_one_line, picture=_picture, chart_args=_chart_args,
                   draw_diagram=_draw_diagram, figure_side=_figure_side, graph_layout=graph_layout, t=t)
        if layout in ppt_extra.FULL_PAGE:   # 整页版式（image_bg）：不画标准标题
            ctx['h'] = SLIDE_H
            chart_count += ppt_extra.render(layout, ctx, sl, s, i)
            if s.get('notes'):
                d.notes(sl, s['notes'])
            continue
        # 正文类版式：标题 + 副题 + 内容 + 结论条 + 页码
        d.title(sl, _need(s, 'title'), sub=s.get('subtitle'))
        h = _body_h(s)
        ctx['h'] = h
        if layout in ppt_extra.RENDERERS:
            chart_count += ppt_extra.render(layout, ctx, sl, s, i)
        elif layout == 'bullets':
            d.text(sl, MARGIN, BODY_Y, CONTENT_W, h, _bullets(_need(s, 'bullets')), size=15, color=C['ink'],
                   name='body', line_spacing=1.35, space_after=8, margins=(0.05, 0.05))
        elif layout == 'diagram':
            dg = _need(s, 'diagram')
            cap_h = 0.4 if s.get('caption') else 0
            box_w = CONTENT_W * (0.66 if s.get('bullets') else 1.0)
            fig = _draw_diagram(d, sl, dg, MARGIN + 0.1, BODY_Y + 0.05, box_w - 0.2, h - cap_h - 0.2, name=f'dg{i}')   # 四周留白，连线标签不压图注
            _figure_side(d, sl, s, h, box_w, cap_h, 'diagram', fig)
        elif layout in ('flow', 'swimlane'):
            # 按内容画的流程图 / 泳道图：模型给 graph（节点 / 边 / 泳道），坐标由 graph_layout（Graphviz）算，画法同 diagram
            dg = graph_layout.layout(_need(s, 'graph'), layout)
            for n in dg['nodes']:
                if n.get('emph'):
                    n['fill'] = C['primary']
            cap_h = 0.4 if s.get('caption') else 0
            wide = s.get('bullets') and dg['bounds']['w'] / max(0.1, dg['bounds']['h']) > 2.0
            if wide:
                # 横长的图（泳道图常见）：图占满内容宽、要点放图下面，否则图被压到 34% 宽后字太小
                fig_h = min(h - cap_h - 1.3, (h - cap_h) * 0.62)
                fig = _draw_diagram(d, sl, dg, MARGIN + 0.1, BODY_Y + 0.05, CONTENT_W - 0.2, fig_h, name=f'{layout}{i}')
                cap_y = fig[1] + fig[3] + 0.1
                if s.get('caption'):
                    d.text(sl, MARGIN, cap_y, CONTENT_W, cap_h, s['caption'], size=10.5, color=C['mid'], align='center', name=layout + '.caption', margins=(0, 0))
                by = cap_y + cap_h + 0.1
                d.text(sl, MARGIN, by, CONTENT_W, BODY_Y + h - by, _bullets(s['bullets']), size=11.5, color=C['ink'],
                       name='body', line_spacing=1.25, space_after=4, margins=(0.05, 0.05))
            else:
                box_w = CONTENT_W * (0.66 if s.get('bullets') else 1.0)
                fig = _draw_diagram(d, sl, dg, MARGIN + 0.1, BODY_Y + 0.05, box_w - 0.2, h - cap_h - 0.2, name=f'{layout}{i}')
                _figure_side(d, sl, s, h, box_w, cap_h, layout, fig)
        elif layout == 'sequence':
            seq = _need(s, 'sequence')
            graph_layout.validate_sequence(seq)
            cap_h = 0.4 if s.get('caption') else 0
            box_w = CONTENT_W * (0.66 if s.get('bullets') else 1.0)
            fig = _draw_sequence(d, sl, seq, MARGIN + 0.1, BODY_Y + 0.05, box_w - 0.2, h - cap_h - 0.2, name=f'seq{i}')
            _figure_side(d, sl, s, h, box_w, cap_h, 'sequence', fig)
        elif layout == 'image_split':
            # 图文页：左图右文 / 右图左文，图占 ratio（默认 0.5），图注贴图下，要点在另一侧
            img_path = _need(s, 'image')
            ratio = float(s.get('ratio') or 0.5)
            if ratio not in (0.4, 0.5, 0.6):
                raise ValueError(f'第 {i} 页 image_split 的 ratio 只能是 0.4 / 0.5 / 0.6，收到 {ratio}')
            side = s.get('side') or 'left'
            if side not in ('left', 'right'):
                raise ValueError(f'第 {i} 页 image_split 的 side 只能是 left / right，收到 {side!r}')
            if not s.get('bullets'):
                raise ValueError(f'第 {i} 页 image_split 缺 bullets（图文页要有要点）')
            gap = 0.35
            img_w = (CONTENT_W - gap) * ratio
            txt_w = CONTENT_W - gap - img_w
            img_x = MARGIN if side == 'left' else MARGIN + txt_w + gap
            txt_x = MARGIN + img_w + gap if side == 'left' else MARGIN
            cap_h = 0.35 if s.get('caption') else 0
            px, py, pw, ph = _picture(sl, img_path, img_x, BODY_Y, img_w, h - cap_h - 0.1, 'figure', i, top=True)
            if s.get('caption'):
                d.text(sl, img_x, py + ph + 0.06, img_w, cap_h, s['caption'], size=10, color=C['mid'], align='center', name='figure.caption', margins=(0, 0))
            d.text(sl, txt_x, BODY_Y, txt_w, h, _bullets(s['bullets']), size=13, color=C['ink'], name='body', line_spacing=1.35, space_after=8, margins=(0.05, 0.05))
        elif layout == 'image_grid':
            # 图片网格页：2 张 2×1、3 张 3×1、4 张 2×2，每图带图注；可选 bullets 放右侧（此时网格占 66%）
            imgs = _need(s, 'images')
            if not isinstance(imgs, list) or not (2 <= len(imgs) <= 4):
                raise ValueError(f'第 {i} 页 image_grid 需要 2~4 张图片，收到 {len(imgs) if isinstance(imgs, list) else 0}')
            grid_w = CONTENT_W * (0.66 if s.get('bullets') else 1.0)
            cols = 2 if len(imgs) in (2, 4) else 3
            rows = 2 if len(imgs) == 4 else 1
            gap = 0.3
            cell_w = (grid_w - gap * (cols - 1)) / cols
            cell_h = (h - gap * (rows - 1)) / rows
            cap_h = 0.3
            for k, im_ in enumerate(imgs):
                if not isinstance(im_, dict) or not im_.get('image'):
                    raise ValueError(f'第 {i} 页 image_grid 第 {k + 1} 张缺 image')
                cx = MARGIN + (k % cols) * (cell_w + gap)
                cy = BODY_Y + (k // cols) * (cell_h + gap)
                px, py, pw, ph = _picture(sl, im_['image'], cx, cy, cell_w, cell_h - cap_h - 0.05, f'grid{k + 1}', i)
                if im_.get('caption'):
                    d.text(sl, cx, py + ph + 0.04, cell_w, cap_h, im_['caption'], size=9.5, color=C['mid'], align='center', name=f'grid{k + 1}.caption', margins=(0, 0))
            if s.get('bullets'):
                d.text(sl, MARGIN + grid_w + 0.3, BODY_Y, CONTENT_W - grid_w - 0.3, h, _bullets(s['bullets']), size=12, color=C['ink'], name='body', line_spacing=1.3, space_after=6, margins=(0.05, 0.05))
        elif layout == 'vendors':
            # 厂商卡片页：2~4 家，每家一张卡：顶部 logo 或名称标牌 + 厂商名 + 2~3 条要点；logo 为文件路径（可选）
            vendors = _need(s, 'vendors')
            if not isinstance(vendors, list) or not (2 <= len(vendors) <= 4):
                raise ValueError(f'第 {i} 页 vendors 需要 2~4 家厂商，收到 {len(vendors) if isinstance(vendors, list) else 0}')
            gap = 0.3
            w = (CONTENT_W - gap * (len(vendors) - 1)) / len(vendors)
            for k, v in enumerate(vendors):
                nm = str(v.get('name') or '').strip()
                if not nm:
                    raise ValueError(f'第 {i} 页 vendors 第 {k + 1} 家缺 name')
                x = MARGIN + k * (w + gap)
                d.rect(sl, x, BODY_Y, w, h, fill=C['white'], line=C['border'], name=f'vendor{k + 1}.box')
                # logo 框 1.9×0.8：按高度统一，方形 logo 不显小；没 logo 的标牌用 1.6×0.5
                if v.get('logoPath'):
                    _logo_or_chip(d, sl, x + (w - min(1.9, w - 0.4)) / 2, BODY_Y + 0.2, min(1.9, w - 0.4), 0.8, f'vendor{k + 1}.logo', v.get('logoPath'), nm)
                else:
                    _logo_or_chip(d, sl, x + (w - min(1.6, w - 0.5)) / 2, BODY_Y + 0.35, min(1.6, w - 0.5), 0.5, f'vendor{k + 1}.logo', None, nm)
                d.text(sl, x + 0.1, BODY_Y + 1.1, w - 0.2, 0.35, nm, size=12, bold=True, color=C['primary'], align='center', anchor='middle', name=f'vendor{k + 1}.name', margins=(0.02, 0))
                d.rule(sl, x + 0.3, BODY_Y + 1.5, w - 0.6, weight=1, name=f'vendor{k + 1}.rule')
                d.text(sl, x + 0.12, BODY_Y + 1.6, w - 0.24, h - 1.7, _bullets(v.get('lines') or []), size=11 if len(vendors) <= 3 else 10, color=C['ink'],
                       name=f'vendor{k + 1}.body', line_spacing=1.25, space_after=4, margins=(0.05, 0.03))
        elif layout == 'logo_table':
            # 对标表页：首列是厂商，改画 logo + 名称（无 logo 画小号名称标牌）；其余列走表格；logos 为 {厂商名: 文件路径}
            rows = _need(s, 'table').get('rows') or []
            if len(rows) < 2 or len(rows) > 7 or any(len(r) != len(rows[0]) for r in rows) or len(rows[0]) > 5:
                raise ValueError(f'第 {i} 页 logo_table 表格须 2~7 行、≤5 列且各行列数一致')
            logos = s.get('logos') or {}
            first_w = 2.4
            ncols = len(rows[0])
            other_w = (CONTENT_W - first_w) / max(1, ncols - 1)
            blank = [[('' if (c == 0 and r > 0) else str(cell)) for c, cell in enumerate(row)] for r, row in enumerate(rows)]
            tbl_h = min(h, 0.6 * len(rows) + 0.2)
            d.table(sl, MARGIN, BODY_Y, CONTENT_W, tbl_h, blank, col_widths=[first_w] + [other_w] * (ncols - 1), size=10, header_size=10.5, name='table')
            row_h = tbl_h / len(rows)
            for r in range(1, len(rows)):
                nm = str(rows[r][0]).strip()
                cy = BODY_Y + r * row_h
                lp = logos.get(nm)
                if lp:
                    _logo_or_chip(d, sl, MARGIN + 0.1, cy + (row_h - 0.44) / 2, 1.0, 0.44, f'table.logo{r}', lp, nm)
                    d.text(sl, MARGIN + 1.2, cy, first_w - 1.3, row_h, nm, size=10, bold=True, color=C['ink'], anchor='middle', name=f'table.name{r}', margins=(0.02, 0))
                else:
                    _logo_or_chip(d, sl, MARGIN + 0.1, cy + (row_h - 0.34) / 2, first_w - 0.2, 0.34, f'table.logo{r}', None, nm, chip_size=10)
        elif layout == 'image':
            img_path = _need(s, 'image')
            if not os.path.isfile(img_path):
                raise ValueError(f'第 {i} 页图片文件不存在：{img_path}')
            cap_h = 0.4 if s.get('caption') else 0
            box_w = CONTENT_W * (0.62 if s.get('bullets') else 1.0)
            box_h = h - cap_h
            with Image.open(img_path) as im:
                iw, ih = im.size
            scale = min(box_w / iw, box_h / ih)
            pw, ph = iw * scale, ih * scale
            px = MARGIN + (box_w - pw) / 2
            py = BODY_Y + (box_h - ph) / 2
            pic = sl.shapes.add_picture(img_path, Inches(px), Inches(py), Inches(pw), Inches(ph))
            pic.name = 'figure'
            pic.line.color.rgb = RGBColor.from_string(C['border']); pic.line.width = Pt(0.75)
            if s.get('caption'):
                d.text(sl, MARGIN, BODY_Y + box_h, box_w, cap_h, s['caption'], size=10.5, color=C['mid'], align='center',
                       name='figure.caption', margins=(0, 0))
            if s.get('bullets'):
                d.text(sl, MARGIN + box_w + 0.3, BODY_Y, CONTENT_W - box_w - 0.3, h, _bullets(s['bullets']), size=12.5,
                       color=C['ink'], name='body', line_spacing=1.3, space_after=6, margins=(0.05, 0.05))
        elif layout == 'cards':
            cards = _need(s, 'cards')
            n = len(cards)
            if n > 4:
                raise ValueError(f'第 {i} 页卡片 {n} 张超过 4 张')
            gap = 0.25
            w = (CONTENT_W - gap * (n - 1)) / n
            for k, c in enumerate(cards):
                d.card(sl, MARGIN + k * (w + gap), BODY_Y, w, h, title=c.get('title') or t['card_default'].format(n=k + 1),
                       lines=_bullets(c.get('lines') or []), size=11.5 if n <= 2 else 10.5, name=f'card{k + 1}',
                       badge=k + 1, line_spacing=1.25, space_after=4)
        elif layout == 'table':
            rows = _need(s, 'table').get('rows') or []
            if len(rows) < 2:
                raise ValueError(f'第 {i} 页表格至少要表头 + 1 行')
            ncols = len(rows[0])
            rows = [[str(c) for c in (r + [''] * ncols)[:ncols]] for r in rows]
            th = min(h, 0.42 * len(rows) + 0.1)
            d.table(sl, MARGIN, BODY_Y, CONTENT_W, th, rows, size=10.5 if len(rows) <= 8 else 9, header_size=11)
        elif layout == 'numbers':
            tiles = _need(s, 'numbers')
            n = min(len(tiles), 5)
            gap = 0.25
            w = (CONTENT_W - gap * (n - 1)) / n
            for k, tile in enumerate(tiles[:n]):
                d.number_tile(sl, MARGIN + k * (w + gap), BODY_Y, w, 1.5, str(tile.get('number', '')), str(tile.get('caption', '')),
                              name=f'tile{k + 1}', number_size=26 if n <= 3 else 22)
            if s.get('bullets'):
                d.text(sl, MARGIN, BODY_Y + 1.75, CONTENT_W, h - 1.75, _bullets(s['bullets']), size=13.5, color=C['ink'],
                       name='body', line_spacing=1.3, space_after=6, margins=(0.05, 0.05))
        elif layout == 'chart':
            charts = s.get('charts') or [_need(s, 'chart')]
            if len(charts) > 2:
                raise ValueError(f'第 {i} 页图表 {len(charts)} 张超过 2 张')
            gap = 0.3
            cw_total = CONTENT_W * (0.58 if s.get('bullets') else 1.0)
            cw = (cw_total - gap * (len(charts) - 1)) / len(charts)
            for k, ch in enumerate(charts):
                kind, cats, series = _chart_args(ch, i)
                chart_count += 1
                d.chart(sl, MARGIN + k * (cw + gap), BODY_Y, cw, h, kind, cats, series, name=f'chart{k + 1}',
                        title=ch.get('title'), number_format=ch.get('number_format', 'General'), max_value=ch.get('max'),
                        highlight=ch.get('highlight'))
            if s.get('bullets'):
                d.text(sl, MARGIN + cw_total + 0.3, BODY_Y, CONTENT_W - cw_total - 0.3, h, _bullets(s['bullets']), size=12.5,
                       color=C['ink'], name='body', line_spacing=1.3, space_after=6, margins=(0.05, 0.05))
        if s.get('takeaway'):
            d.strip(sl, s['takeaway'])
        if s.get('notes'):
            d.notes(sl, s['notes'])
        d.page_number(sl, total)
    d.save(out_path)
    return total, chart_count


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('用法: ppt_build.py <spec.json> <out.pptx>（推荐改用 spec_to_pptx.py）', file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding='utf-8') as f:
        spec = json.load(f)
    spec.setdefault('date', _date.today().isoformat())
    n, charts = build(spec, sys.argv[2], base_dir=os.path.dirname(os.path.abspath(sys.argv[1])))
    print(json.dumps({'ok': True, 'slides': n, 'charts': charts, 'out': sys.argv[2]}, ensure_ascii=False))
