# -*- coding: utf-8 -*-
"""
Spec Native engine · 扩展版式：全部由基础原语（rect / label / badge / card / number_tile / table / chart / arrow / picture）组合，原生形状可编辑。

版式与规格（模型只出语义，坐标全在这里算；校验不过直接抛 ValueError）：
  timeline      milestones:[{date, text, status:done|doing|todo}] 3~8            时间轴 / 路线图
  layers        layers:[{name, items:[≤6]}] 2~5                                   分层架构
  hierarchy     tree:{nodes:[{id, text, parent:''|id, emph}]} ≤14               组织树 / 分解树（转成 TB 流程图交 graph_layout）
  cycle         steps:[str|{text}] 3~6, center?                                  闭环 / PDCA
  funnel        stages:[{label, value}] 3~6                                       漏斗
  compare       left:{title, lines}, right:{title, lines}                         两栏 VS
  pros_cons     pros:[…], cons:[…]                                                优势 / 不足
  matrix        axes:{x, y}?, quadrants:[{title, items}] ×4（左上 右上 左下 右下）  2×2 四象限
  kpi           numbers:[{number, caption}] 2~4 + chart                          数字卡 + 图表
  quote         quote, source?, bullets?(≤2)                                     原话引用页
  agenda        items:[…] 3~8, current?(1 起)                                    目录页
  icons         items:[{icon, title, lines}] 2~4，icon ∈ ICONS                    图标 + 文字（原生形状图标）
  image_callout image:'路径', markers:[{x:0~1, y:0~1, text}] 1~5, caption?        图上编号标注 + 右侧说明
  image_bg      image:'路径', title, subtitle?                                    大图铺底 + 半透明色块 + 大字（整页，不画标准标题）
render(layout, ctx, sl, s, i) → 本页图表数；ctx 由 ppt_build 提供（d / 常量 / 助手函数 / 文案表 t）。
"""
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.util import Inches, Pt
from pptx.oxml.ns import qn
from lxml import etree

ICONS = {
    'star': MSO_SHAPE.STAR_5_POINT, 'bolt': MSO_SHAPE.LIGHTNING_BOLT, 'heart': MSO_SHAPE.HEART, 'gear': MSO_SHAPE.GEAR_6,
    'cloud': MSO_SHAPE.CLOUD, 'sun': MSO_SHAPE.SUN, 'moon': MSO_SHAPE.MOON, 'warning': MSO_SHAPE.ISOSCELES_TRIANGLE,
    'stop': MSO_SHAPE.NO_SYMBOL, 'plus': MSO_SHAPE.MATH_PLUS, 'minus': MSO_SHAPE.MATH_MINUS, 'equal': MSO_SHAPE.MATH_EQUAL,
    'multiply': MSO_SHAPE.MATH_MULTIPLY, 'arrow_right': MSO_SHAPE.RIGHT_ARROW, 'arrow_up': MSO_SHAPE.UP_ARROW,
    'arrow_down': MSO_SHAPE.DOWN_ARROW, 'arrow_left': MSO_SHAPE.LEFT_ARROW, 'arrows': MSO_SHAPE.LEFT_RIGHT_ARROW,
    'cube': MSO_SHAPE.CUBE, 'donut': MSO_SHAPE.DONUT, 'pie': MSO_SHAPE.PIE, 'document': MSO_SHAPE.FLOWCHART_DOCUMENT,
    'database': MSO_SHAPE.CAN, 'smile': MSO_SHAPE.SMILEY_FACE, 'chat': MSO_SHAPE.ROUNDED_RECTANGULAR_CALLOUT,
    'diamond': MSO_SHAPE.DIAMOND, 'hexagon': MSO_SHAPE.HEXAGON, 'chevron': MSO_SHAPE.CHEVRON, 'wave': MSO_SHAPE.WAVE,
    'drop': MSO_SHAPE.TEAR, 'octagon': MSO_SHAPE.OCTAGON, 'pentagon': MSO_SHAPE.PENTAGON, 'cycle': MSO_SHAPE.CIRCULAR_ARROW,
    'target': MSO_SHAPE.DONUT, 'block': MSO_SHAPE.BEVEL, 'flag': MSO_SHAPE.PENTAGON, 'decision': MSO_SHAPE.FLOWCHART_DECISION,
}
STATUS = ('done', 'doing', 'todo')
FULL_PAGE = {'image_bg'}   # 不画标准标题的整页版式


def _count(name, arr, lo, hi, page):
    if not isinstance(arr, list) or not (lo <= len(arr) <= hi):
        raise ValueError(f'第 {page} 页 {name} 需要 {lo}~{hi} 项，收到 {len(arr) if isinstance(arr, list) else 0}')


def _s(x):
    return str(x if x is not None else '').strip()


# ---------------------------------------------------------------- 结构类

def timeline(ctx, sl, s, i):
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    ms = need(s, 'milestones'); _count('milestones', ms, 3, 8, i)
    h = ctx['h']
    for m in ms:
        if m.get('status') and m['status'] not in STATUS:
            raise ValueError(f'第 {i} 页时间轴 status {m["status"]!r} 只能是 done / doing / todo')
        if not _s(m.get('text')):
            raise ValueError(f'第 {i} 页时间轴有里程碑缺 text')
    n = len(ms)
    x0, x1 = ctx['MARGIN'] + 0.6, ctx['MARGIN'] + ctx['CONTENT_W'] - 0.6
    y_line = ctx['BODY_Y'] + h * 0.5
    step = (x1 - x0) / (n - 1)
    d.rule(sl, x0 - 0.3, y_line, x1 - x0 + 0.6, color=C['border'], weight=2.5, name='tl.line')
    box_w = min(2.2, step * 1.9 if n > 5 else step - 0.15)
    for k, m in enumerate(ms):
        x = x0 + k * step
        st = m.get('status') or 'done'
        fill, line = (C['primary'], None) if st == 'done' else (C['red'], None) if st == 'doing' else (C['white'], C['primary'])
        d.rect(sl, x - 0.15, y_line - 0.15, 0.3, 0.3, fill=fill, line=line, line_w=1.5, shape=MSO_SHAPE.OVAL, name=f'tl.dot{k + 1}')
        above = (n > 5 and k % 2 == 1)
        date_y = y_line - 0.55 if not above else y_line + 0.22
        text_y = y_line + 0.28 if not above else y_line - 0.28 - 1.1
        d.text(sl, x - box_w / 2, date_y, box_w, 0.3, _s(m.get('date')), size=10.5, bold=True, color=C['primary'], align='center', anchor='middle',
               name=f'tl.date{k + 1}', margins=(0, 0))
        d.text(sl, x - box_w / 2, text_y, box_w, 1.1, _s(m.get('text')), size=ctx['fit_font'](_s(m.get('text')), box_w, 1.1, base=10.5),
               color=C['ink'], align='center', anchor='top' if not above else 'bottom', name=f'tl.text{k + 1}', margins=(0.02, 0.02))
    return 0


def layers(ctx, sl, s, i):
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    ls = need(s, 'layers'); _count('layers', ls, 2, 5, i)
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    n = len(ls)
    gap = 0.15
    band_h = (h - gap * (n - 1)) / n
    label_w = 1.7
    for k, l in enumerate(ls):
        items = l.get('items') or []
        if not _s(l.get('name')):
            raise ValueError(f'第 {i} 页分层第 {k + 1} 层缺 name')
        if not isinstance(items, list) or not (1 <= len(items) <= 6):
            raise ValueError(f'第 {i} 页分层「{l.get("name")}」的 items 需要 1~6 项')
        y = Y + k * (band_h + gap)
        d.rect(sl, M, y, W, band_h, fill=C['bg'] if k % 2 else C['fill'], line=C['border'], name=f'layer{k + 1}.band')
        d.label(sl, M, y, label_w, band_h, _s(l['name']), size=ctx['fit_one_line'](_s(l['name']), label_w, base=12), name=f'layer{k + 1}.label')
        m = len(items)
        pill_gap = 0.2
        pill_w = (W - label_w - 0.4 - pill_gap * (m - 1)) / m
        pill_h = min(0.55, band_h * 0.6)
        for j, it in enumerate(items):
            x = M + label_w + 0.2 + j * (pill_w + pill_gap)
            d.rect(sl, x, y + (band_h - pill_h) / 2, pill_w, pill_h, fill=C['white'], line=C['primary'], shape=MSO_SHAPE.ROUNDED_RECTANGLE,
                   name=f'layer{k + 1}.item{j + 1}', text=_s(it), size=ctx['fit_font'](_s(it), pill_w, pill_h, base=11), color=C['ink'])
    return 0


def hierarchy(ctx, sl, s, i):
    need = ctx['need']
    tree = need(s, 'tree')
    nodes = tree.get('nodes') if isinstance(tree, dict) else None
    _count('tree.nodes', nodes, 2, 14, i)
    ids = {_s(n.get('id')) for n in nodes}
    roots = [n for n in nodes if not _s(n.get('parent'))]
    if not roots:
        raise ValueError(f'第 {i} 页层次图没有根节点（parent 为空的节点）')
    edges = []
    for n in nodes:
        p = _s(n.get('parent'))
        if p and p not in ids:
            raise ValueError(f'第 {i} 页层次图节点「{n.get("text")}」的 parent {p!r} 不存在')
        if p:
            edges.append({'from': p, 'to': _s(n.get('id'))})
    g = {'direction': 'TB', 'nodes': [{'id': _s(n.get('id')), 'text': _s(n.get('text')), 'emph': bool(n.get('emph')), 'shape': 'round'} for n in nodes], 'edges': edges}
    dg = ctx['graph_layout'].layout(g, 'flow')
    for n in dg['nodes']:
        if n.get('emph'):
            n['fill'] = ctx['C']['primary']
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    cap_h = 0.4 if s.get('caption') else 0
    box_w = W * (0.66 if s.get('bullets') else 1.0)
    fig = ctx['draw_diagram'](ctx['d'], sl, dg, M + 0.1, Y + 0.05, box_w - 0.2, h - cap_h - 0.2, name=f'tree{i}')
    ctx['figure_side'](ctx['d'], sl, s, h, box_w, cap_h, 'hierarchy', fig)
    return 0


def _arrow_between(sl, C, x1, y1, x2, y2, name):
    ln = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    ln.name = name
    ln.line.color.rgb = RGBColor.from_string(C['secondary']); ln.line.width = Pt(1.75)
    el = etree.SubElement(ln.line._get_or_add_ln(), qn('a:tailEnd')); el.set('type', 'triangle'); el.set('w', 'med'); el.set('len', 'med')


def cycle(ctx, sl, s, i):
    import math
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    steps = need(s, 'steps'); _count('steps', steps, 3, 6, i)
    texts = [_s(x.get('text') if isinstance(x, dict) else x) for x in steps]
    if any(not t for t in texts):
        raise ValueError(f'第 {i} 页循环图有空步骤')
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    area_w = W * (0.62 if s.get('bullets') else 1.0)
    cx, cy = M + area_w / 2, Y + h / 2
    R = min(h / 2 - 0.55, 2.3)
    n = len(texts)
    nw, nh = 1.7, 0.62
    pts = []
    for k in range(n):
        a = -math.pi / 2 + 2 * math.pi * k / n
        pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    for k, (x, y) in enumerate(pts):
        d.rect(sl, x - nw / 2, y - nh / 2, nw, nh, fill=C['pale'], line=C['primary'], shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=f'cyc.n{k + 1}',
               text=texts[k], size=ctx['fit_font'](texts[k], nw, nh, base=11), color=C['ink'])
        d.badge(sl, x - nw / 2 - 0.12, y - nh / 2 - 0.12, k + 1, d=0.3, name=f'cyc.n{k + 1}.no')
    for k in range(n):
        (x1, y1), (x2, y2) = pts[k], pts[(k + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        # 从当前框边缘出、到下一框边缘止（按框半宽 / 半高的近似半径）
        _arrow_between(sl, C, x1 + ux * 0.9, y1 + uy * 0.55, x2 - ux * 0.9, y2 - uy * 0.55, f'cyc.e{k + 1}')
    if _s(s.get('center')):
        d.text(sl, cx - 1.2, cy - 0.35, 2.4, 0.7, _s(s['center']), size=13, bold=True, color=C['primary'], align='center', anchor='middle', name='cyc.center', margins=(0, 0))
    if s.get('bullets'):
        d.text(sl, M + area_w + 0.3, Y, W - area_w - 0.3, h, ctx['bullets'](s['bullets']), size=12, color=C['ink'], name='body', line_spacing=1.3, space_after=6, margins=(0.05, 0.05))
    return 0


def funnel(ctx, sl, s, i):
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    stages = need(s, 'stages'); _count('stages', stages, 3, 6, i)
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    n = len(stages)
    fw = W * (0.6 if s.get('bullets') else 0.72)
    fx = M if s.get('bullets') else M + (W - fw) / 2
    gap = 0.08
    band_h = (h - gap * (n - 1)) / n
    fills = [C['primary'], C['secondary'], '3B7DD8', '6B9BE0', '9BBCEA', 'BFD4F2']
    for k, st in enumerate(stages):
        label, value = _s(st.get('label')), _s(st.get('value'))
        if not label:
            raise ValueError(f'第 {i} 页漏斗第 {k + 1} 层缺 label')
        w = fw * (1 - 0.13 * k)
        x = fx + (fw - w) / 2
        y = Y + k * (band_h + gap)
        fill = fills[k]
        dark = k < 3
        d.rect(sl, x, y, w, band_h, fill=fill, line=None, name=f'funnel{k + 1}')
        d.text(sl, x + 0.15, y, w * 0.6, band_h, label, size=12, bold=True, color=C['white'] if dark else C['ink'], anchor='middle', name=f'funnel{k + 1}.label', margins=(0.05, 0))
        if value:
            d.text(sl, x + w * 0.6, y, w * 0.4 - 0.15, band_h, value, size=13, bold=True, color=C['white'] if dark else C['ink'], align='right', anchor='middle', name=f'funnel{k + 1}.value', margins=(0.05, 0))
    if s.get('bullets'):
        d.text(sl, M + fw + 0.4, Y, W - fw - 0.4, h, ctx['bullets'](s['bullets']), size=12, color=C['ink'], name='body', line_spacing=1.3, space_after=6, margins=(0.05, 0.05))
    return 0


def _two_cards(ctx, sl, s, i, left, right, left_fill, right_fill, mid_text, prefix_l='', prefix_r=''):
    d, C = ctx['d'], ctx['C']
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    gap = 0.9
    w = (W - gap) / 2
    for side, blk, fill, x, pre in (('left', left, left_fill, M, prefix_l), ('right', right, right_fill, M + w + gap, prefix_r)):
        lines = blk.get('lines') or []
        if not _s(blk.get('title')) or not isinstance(lines, list) or not (1 <= len(lines) <= 6):
            raise ValueError(f'第 {i} 页 {side} 需要 title 与 1~6 条 lines')
        d.card(sl, x, Y, w, h, title=_s(blk['title']), lines=ctx['bullets']([f'{pre}{_s(l)}' for l in lines]), size=12, title_size=12,
               name=f'cmp.{side}', title_fill=fill, line_spacing=1.3, space_after=6)
    d.rect(sl, M + w + gap / 2 - 0.32, Y + h / 2 - 0.32, 0.64, 0.64, fill=C['ink'], line=None, shape=MSO_SHAPE.OVAL, name='cmp.vs',
           text=mid_text, size=12, bold=True, color=C['white'], margins=(0, 0))


def compare(ctx, sl, s, i):
    need = ctx['need']
    _two_cards(ctx, sl, s, i, need(s, 'left'), need(s, 'right'), ctx['C']['primary'], ctx['C']['secondary'], ctx['t']['vs'])
    return 0


def pros_cons(ctx, sl, s, i):
    need, t = ctx['need'], ctx['t']
    pros, cons = need(s, 'pros'), need(s, 'cons')
    _two_cards(ctx, sl, s, i, {'title': _s(s.get('pros_title')) or t['pros'], 'lines': pros}, {'title': _s(s.get('cons_title')) or t['cons'], 'lines': cons},
               '2E7D32', ctx['C']['red'], t['versus'], '+ ', '- ')
    return 0


def matrix(ctx, sl, s, i):
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    q = need(s, 'quadrants'); _count('quadrants', q, 4, 4, i)
    axes = s.get('axes') or {}
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    x0, y0 = M + 0.55, Y + 0.05
    AW, AH = W - 0.6, h - 0.5
    gap = 0.12
    cw, ch = (AW - gap) / 2, (AH - gap) / 2
    for k, blk in enumerate(q):
        col, row = k % 2, k // 2
        x, y = x0 + col * (cw + gap), y0 + row * (ch + gap)
        items = blk.get('items') or []
        if not _s(blk.get('title')) or not isinstance(items, list) or len(items) > 5:
            raise ValueError(f'第 {i} 页四象限第 {k + 1} 格需要 title 与 ≤5 条 items')
        d.rect(sl, x, y, cw, ch, fill=C['pale'] if (col + row) % 2 == 0 else C['white'], line=C['border'], name=f'quad{k + 1}.box')
        d.text(sl, x + 0.1, y + 0.08, cw - 0.2, 0.36, _s(blk['title']), size=12.5, bold=True, color=C['primary'], name=f'quad{k + 1}.title', margins=(0.02, 0))
        if items:
            d.text(sl, x + 0.1, y + 0.48, cw - 0.2, ch - 0.55, ctx['bullets']([_s(t) for t in items]), size=10.5, color=C['ink'], name=f'quad{k + 1}.body', line_spacing=1.25, space_after=3, margins=(0.02, 0.02))
    # 坐标轴：左侧竖轴（文字旋转）、底部横轴
    if _s(axes.get('y')):
        t = d.text(sl, M - 0.75 + 0.05, y0 + AH / 2 - 0.2, 1.6, 0.4, _s(axes['y']), size=10.5, bold=True, color=C['mid'], align='center', anchor='middle', name='axis.y', margins=(0, 0))
        t.rotation = 270
    if _s(axes.get('x')):
        d.text(sl, x0, y0 + AH + 0.08, AW, 0.35, _s(axes['x']), size=10.5, bold=True, color=C['mid'], align='center', anchor='middle', name='axis.x', margins=(0, 0))
    return 0


def kpi(ctx, sl, s, i):
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    nums = need(s, 'numbers'); _count('numbers', nums, 2, 4, i)
    ch = need(s, 'chart')
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    top_h = 1.25
    n = len(nums)
    gap = 0.25
    w = (W - gap * (n - 1)) / n
    for k, nm in enumerate(nums):
        d.number_tile(sl, M + k * (w + gap), Y, w, top_h, _s(nm.get('number')), _s(nm.get('caption')), name=f'kpi{k + 1}', number_size=26)
    kind, cats, series = ctx['chart_args'](ch, i)
    d.chart(sl, M, Y + top_h + 0.25, W, h - top_h - 0.25, kind, cats, series, name='chart1', title=ch.get('title'),
            number_format=ch.get('number_format', 'General'), max_value=ch.get('max'), highlight=ch.get('highlight'))
    return 1


def quote(ctx, sl, s, i):
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    text = _s(need(s, 'quote'))
    if not text:
        raise ValueError(f'第 {i} 页引用页 quote 为空')
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    d.text(sl, M, Y - 0.25, 1.2, 1.3, '“', size=96, bold=True, color=C['pale'], name='quote.mark', margins=(0, 0), line_spacing=1.0)
    qh = h * (0.55 if s.get('bullets') else 0.7)
    d.text(sl, M + 0.9, Y + 0.25, W - 1.8, qh, text, size=ctx['fit_font'](text, W - 1.8, qh, base=22, lo=14), color=C['ink'], name='quote.text', line_spacing=1.45, margins=(0.05, 0.05))
    if _s(s.get('source')):
        d.text(sl, M + 0.9, Y + 0.25 + qh + 0.1, W - 1.8, 0.4, f'—— {_s(s["source"])}', size=12, color=C['mid'], align='right', name='quote.source', margins=(0, 0))
    if s.get('bullets'):
        d.text(sl, M + 0.9, Y + 0.25 + qh + 0.6, W - 1.8, h - qh - 0.9, ctx['bullets'](s['bullets'][:2]), size=12.5, color=C['ink'], name='body', line_spacing=1.3, space_after=6, margins=(0.05, 0.05))
    return 0


def agenda(ctx, sl, s, i):
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    items = need(s, 'items'); _count('items', items, 3, 8, i)
    cur = int(s.get('current') or 0)
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    n = len(items)
    gap = 0.12
    row_h = min(0.72, (h - gap * (n - 1)) / n)
    for k, it in enumerate(items):
        y = Y + k * (row_h + gap)
        active = (k + 1 == cur)
        d.rect(sl, M, y, W, row_h, fill=C['primary'] if active else C['bg'], line=None if active else C['border'], name=f'agenda{k + 1}.row')
        d.badge(sl, M + 0.22, y + (row_h - 0.36) / 2, k + 1, d=0.36, fill=C['red'] if active else C['primary'], name=f'agenda{k + 1}.no')
        d.text(sl, M + 0.8, y, W - 1.0, row_h, _s(it), size=14 if active else 13, bold=active, color=C['white'] if active else C['ink'], anchor='middle', name=f'agenda{k + 1}.text', margins=(0.02, 0))
    return 0


def icons(ctx, sl, s, i):
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    items = need(s, 'items'); _count('items', items, 2, 4, i)
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    n = len(items)
    gap = 0.3
    w = (W - gap * (n - 1)) / n
    for k, it in enumerate(items):
        icon = _s(it.get('icon'))
        if icon not in ICONS:
            raise ValueError(f'第 {i} 页图标「{icon}」不在图标集内（可用：{", ".join(sorted(ICONS))}）')
        if not _s(it.get('title')):
            raise ValueError(f'第 {i} 页图标卡第 {k + 1} 张缺 title')
        x = M + k * (w + gap)
        d.rect(sl, x, Y, w, h, fill=C['white'], line=C['border'], name=f'icon{k + 1}.box')
        cx = x + w / 2
        d.rect(sl, cx - 0.5, Y + 0.3, 1.0, 1.0, fill=C['pale'], line=None, shape=MSO_SHAPE.OVAL, name=f'icon{k + 1}.bg')
        d.rect(sl, cx - 0.28, Y + 0.52, 0.56, 0.56, fill=C['primary'], line=None, shape=ICONS[icon], name=f'icon{k + 1}.glyph')
        d.text(sl, x + 0.1, Y + 1.45, w - 0.2, 0.4, _s(it['title']), size=13, bold=True, color=C['primary'], align='center', anchor='middle', name=f'icon{k + 1}.title', margins=(0.02, 0))
        d.rule(sl, x + 0.3, Y + 1.9, w - 0.6, weight=1, name=f'icon{k + 1}.rule')
        if it.get('lines'):
            d.text(sl, x + 0.12, Y + 2.0, w - 0.24, h - 2.1, ctx['bullets']([_s(l) for l in it['lines']]), size=11 if n <= 3 else 10, color=C['ink'], name=f'icon{k + 1}.body', line_spacing=1.25, space_after=4, margins=(0.05, 0.03))
    return 0


# ---------------------------------------------------------------- 图片类

def image_callout(ctx, sl, s, i):
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    img = need(s, 'image')
    markers = need(s, 'markers'); _count('markers', markers, 1, 5, i)
    h, M, W, Y = ctx['h'], ctx['MARGIN'], ctx['CONTENT_W'], ctx['BODY_Y']
    for k, m in enumerate(markers):
        try:
            mx, my = float(m.get('x')), float(m.get('y'))
        except (TypeError, ValueError):
            raise ValueError(f'第 {i} 页标注第 {k + 1} 个缺 x / y')
        if not (0 <= mx <= 1 and 0 <= my <= 1) or not _s(m.get('text')):
            raise ValueError(f'第 {i} 页标注第 {k + 1} 个 x / y 须在 0~1 内且有 text')
    box_w = W * 0.62
    cap_h = 0.35 if s.get('caption') else 0
    px, py, pw, ph = ctx['picture'](sl, img, M, Y, box_w, h - cap_h - 0.1, 'figure', i, top=True)
    if s.get('caption'):
        d.text(sl, M, py + ph + 0.06, box_w, cap_h, _s(s['caption']), size=10, color=C['mid'], align='center', name='figure.caption', margins=(0, 0))
    for k, m in enumerate(markers):
        mx, my = px + float(m['x']) * pw, py + float(m['y']) * ph
        d.badge(sl, mx - 0.17, my - 0.17, k + 1, d=0.34, fill=C['red'], name=f'callout{k + 1}.mark')
    rx, rw = M + box_w + 0.35, W - box_w - 0.35
    y = Y
    row_h = min(0.95, h / len(markers))
    for k, m in enumerate(markers):
        d.badge(sl, rx, y + 0.06, k + 1, d=0.32, fill=C['red'], name=f'callout{k + 1}.no')
        d.text(sl, rx + 0.42, y, rw - 0.42, row_h - 0.05, _s(m['text']), size=11.5, color=C['ink'], name=f'callout{k + 1}.text', line_spacing=1.25, margins=(0.02, 0.02))
        y += row_h
    return 0


def image_bg(ctx, sl, s, i):
    """整页：大图铺底（等比放大裁切铺满）+ 下半部半透明主色块 + 大字标题 / 副题；不画标准标题"""
    from PIL import Image
    import os
    d, C, need = ctx['d'], ctx['C'], ctx['need']
    img = need(s, 'image')
    if not os.path.isfile(img):
        raise ValueError(f'第 {i} 页图片文件不存在：{img}')
    SW, SH = ctx['SLIDE_W'], ctx['SLIDE_H']
    with Image.open(img) as im:
        iw, ih = im.size
    scale = max(SW / iw, SH / ih)
    pw, ph = iw * scale, ih * scale
    pic = sl.shapes.add_picture(img, Inches((SW - pw) / 2), Inches((SH - ph) / 2), Inches(pw), Inches(ph))
    pic.name = 'bg.image'
    # 裁切到页面：把超出页面的部分按比例 crop 掉，避免形状越界
    if pw > SW:
        c = (pw - SW) / 2 / pw
        pic.crop_left = c; pic.crop_right = c
        pic.left = Inches(0); pic.width = Inches(SW)
    if ph > SH:
        c = (ph - SH) / 2 / ph
        pic.crop_top = c; pic.crop_bottom = c
        pic.top = Inches(0); pic.height = Inches(SH)
    ov = d.rect(sl, 0, SH * 0.52, SW, SH * 0.48, fill=C['primary'], line=None, name='bg.overlay')
    clr = ov.fill._xPr.find(qn('a:solidFill')).find(qn('a:srgbClr'))
    a = etree.SubElement(clr, qn('a:alpha')); a.set('val', '62000')
    d.text(sl, 0.9, SH * 0.56, SW - 1.8, 1.3, _s(need(s, 'title')), size=30, bold=True, color=C['white'], anchor='middle', name='bg.title', margins=(0, 0), line_spacing=1.15)
    if _s(s.get('subtitle')):
        d.text(sl, 0.9, SH * 0.56 + 1.35, SW - 1.8, 1.0, _s(s['subtitle']), size=15, color='DCE6F5', name='bg.sub', margins=(0, 0), line_spacing=1.25)
    d.page_number(sl, ctx['total'], color='DCE6F5')   # 顶层 page_numbers=false 时不画
    return 0


RENDERERS = {
    'timeline': timeline, 'layers': layers, 'hierarchy': hierarchy, 'cycle': cycle, 'funnel': funnel, 'compare': compare,
    'pros_cons': pros_cons, 'matrix': matrix, 'kpi': kpi, 'quote': quote, 'agenda': agenda, 'icons': icons,
    'image_callout': image_callout, 'image_bg': image_bg,
}


def render(layout, ctx, sl, s, i):
    return RENDERERS[layout](ctx, sl, s, i)
