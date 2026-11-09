# -*- coding: utf-8 -*-
"""
Spec Native engine · design system (python-pptx wrapper)

默认视觉是「科研答辩风」：白底、深学术蓝结构色、少量正红强调、浅蓝面板、细灰边框、深蓝结论条。
全部用原生形状 / 文本框 / 表格 / 图表复刻，页面元素全部可编辑，领导改完能回读、能按形状 name 定位。

风格可整体覆盖（apply_style）：调色板、中西文字体、图表系列色，供跨引擎的 style brief 使用。

用法：
    from pptx_style import Deck
    d = Deck()                       # 16:9，13.333 × 7.5 英寸
    s = d.slide()                    # 空白页
    d.title(s, '一、组织现状：…', sub='副题')
    d.card(s, x, y, w, h, title='…', lines=[...])
    d.strip(s, '结论一句话')
    d.save('xxx.pptx')
坐标单位：英寸。所有形状都带 name（便于回读改稿时按名字定位）。
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_LABEL_POSITION
from pptx.oxml.ns import qn
import re
from lxml import etree

# ---- 调色板（科研答辩风默认值；apply_style 可整体覆盖）----
C = dict(
    primary='003F8F',    # 深学术蓝：标题、结构色块
    secondary='0B5CAD',  # 研究蓝：次级标签
    pale='EAF2FF',       # 浅蓝面板
    red='C00000',        # 正红：关键结论 / 风险 / 缺口
    ink='111111',
    gray='333333',
    mid='6B7280',
    border='D8DEE8',
    fill='F3F6FA',
    white='FFFFFF',
    bg='F5F7FA',
    gold='F3DFA2',
)
FONT_EA = '微软雅黑'
FONT_LATIN = 'Arial'
SLIDE_W, SLIDE_H = 13.333, 7.5
MARGIN = 0.45


def _hex(v):
    s = str(v or '').strip().lstrip('#').upper()
    if not re.fullmatch(r'[0-9A-F]{6}', s):
        raise ValueError(f'颜色须为 6 位十六进制（如 003F8F），收到 {v!r}')
    return s


def apply_style(style):
    """整体覆盖风格：{"palette": {primary, secondary, pale, red, ink, gray, mid, border, fill, white, bg, gold},
    "fonts": {"cjk": "微软雅黑", "latin": "Arial"}, "series_colors": ["003F8F", ...]}。
    未知的调色板键直接抛错（不接受拼错的键静默无效）。"""
    global FONT_EA, FONT_LATIN
    if not isinstance(style, dict):
        raise ValueError('style 须为对象')
    for k, v in (style.get('palette') or {}).items():
        if k not in C:
            raise ValueError(f'style.palette 未知的键 {k!r}（可用 {sorted(C)}）')
        C[k] = _hex(v)
    fonts = style.get('fonts') or {}
    if fonts.get('cjk'):
        FONT_EA = str(fonts['cjk'])
    if fonts.get('latin'):
        FONT_LATIN = str(fonts['latin'])
    if style.get('series_colors'):
        colors = tuple(_hex(c) for c in style['series_colors'])
        if len(colors) < 2:
            raise ValueError('style.series_colors 至少 2 个颜色')
        Deck.SERIES_COLORS = colors


def rgb(h):
    return RGBColor.from_string(h)


def _set_run_font(run, size, bold=False, color='111111', italic=False):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = rgb(color)
    f.name = FONT_LATIN
    rPr = run._r.get_or_add_rPr()
    for tag in ('a:ea', 'a:cs'):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set('typeface', FONT_EA)


CITE_RE = re.compile(r'\[(\d+(?:\s*[,，、]\s*\d+)*)\]')


def split_cites(text):
    """'……占比 15% [2][5]' → [('……占比 15% ', {}), ('[2]', {'cite': True}), ('[5]', {'cite': True})]；出处角标"""
    out, pos = [], 0
    for m in CITE_RE.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], {}))
        out.append((m.group(0), {'cite': True}))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], {}))
    return out or [(text, {})]


def _fill_paragraph(p, content, size, bold, color, align, line_spacing):
    """content: str | list[(text, opts)]；opts 可含 bold/color/size/italic/cite（cite=出处角标：上标、缩小、灰色）"""
    p.alignment = {'left': PP_ALIGN.LEFT, 'center': PP_ALIGN.CENTER, 'right': PP_ALIGN.RIGHT}[align]
    p.line_spacing = line_spacing
    runs = split_cites(content) if isinstance(content, str) else content
    for text, opts in runs:
        r = p.add_run()
        r.text = text
        if opts.get('cite'):
            _set_run_font(r, max(7, round(size * 0.62)), False, opts.get('color', C['mid']), False)
            r._r.get_or_add_rPr().set('baseline', '30000')   # 上标
        else:
            _set_run_font(r, opts.get('size', size), opts.get('bold', bold), opts.get('color', color), opts.get('italic', False))


def _chart_schema_fix(chart):
    """python-pptx 图表 XML 两处不合 schema 的地方（微软 Open XML SDK 校验器报错；PowerPoint 目前宽容，但不该留隐患）：
      1) c:axId / c:crossAx 写的是负数（模板常量 -2068027336 等），schema 要求 UInt32 → 改成正数且成对一致
      2) 雷达图 c:ser 里带 c:smooth（radarChart 的 ser 不允许）→ 删掉"""
    root = chart._chartSpace
    remap = {}
    for tag in ('c:axId', 'c:crossAx'):
        for el in root.iter(qn(tag)):
            v = el.get('val')
            if v and v.startswith('-'):
                remap.setdefault(v, str(abs(int(v)) % 2147483647 or 1))
                el.set('val', remap[v])
    for radar in root.iter(qn('c:radarChart')):
        for ser in radar.findall(qn('c:ser')):
            for sm in ser.findall(qn('c:smooth')):
                ser.remove(sm)


def _chart_fonts(chart, font_size=11):
    """图表内所有文字（标题 run / 数据标签 / 坐标轴 / 图例的 defRPr）显式写 latin / ea / cs 字体。
    python-pptx 只写字号颜色不写字体，PowerPoint 靠主题回退能显示中文，部分在线预览（如飞书）不回退会乱码。
    图表级默认字号（python-pptx 模板是 18pt，雷达图轴标签等没单独设的部件会按它渲染）统一改为 font_size。"""
    root = chart._chartSpace
    for txPr in root.findall(qn('c:txPr')):   # 只动 chartSpace 直属的默认文字属性
        for d in txPr.iter(qn('a:defRPr')):
            d.set('sz', str(int(font_size * 100)))
    for tag in ('a:rPr', 'a:defRPr', 'a:endParaRPr'):
        for rpr in root.iter(qn(tag)):
            for sub in ('a:latin', 'a:ea', 'a:cs'):
                el = rpr.find(qn(sub))
                if el is None:
                    el = etree.SubElement(rpr, qn(sub))
                el.set('typeface', FONT_LATIN if sub == 'a:latin' else FONT_EA)
    cs = root
    if cs.find(qn('c:txPr')) is None:
        txPr = etree.SubElement(cs, qn('c:txPr'))
        etree.SubElement(txPr, qn('a:bodyPr'))
        etree.SubElement(txPr, qn('a:lstStyle'))
        p = etree.SubElement(txPr, qn('a:p'))
        pPr = etree.SubElement(p, qn('a:pPr'))
        d = etree.SubElement(pPr, qn('a:defRPr'))
        etree.SubElement(d, qn('a:latin')).set('typeface', FONT_LATIN)
        etree.SubElement(d, qn('a:ea')).set('typeface', FONT_EA)
        etree.SubElement(d, qn('a:cs')).set('typeface', FONT_EA)


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = Inches(SLIDE_W)
        self.prs.slide_height = Inches(SLIDE_H)
        self.page_no = 0
        self.page_numbers = True   # spec 顶层 page_numbers=false 时 page_number() 不画（ppt_build.build 设）

    # ---------- 页面 ----------
    def slide(self):
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.page_no += 1
        return s

    def save(self, path):
        self.prs.save(path)
        return path

    def notes(self, slide, text):
        slide.notes_slide.notes_text_frame.text = text

    # ---------- 基础元素 ----------
    def text(self, slide, x, y, w, h, paragraphs, size=11, bold=False, color='111111', align='left',
             anchor='top', name=None, line_spacing=1.15, margins=(0.05, 0.03), fill=None, border=None,
             border_w=0.75, space_after=0):
        """paragraphs: str | list[str | list[(text, opts)]]"""
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        if name:
            tb.name = name
        if fill:
            tb.fill.solid(); tb.fill.fore_color.rgb = rgb(fill)
        if border:
            tb.line.color.rgb = rgb(border); tb.line.width = Pt(border_w)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.auto_size = None
        tf.margin_left = tf.margin_right = Inches(margins[0])
        tf.margin_top = tf.margin_bottom = Inches(margins[1])
        tf.vertical_anchor = {'top': MSO_ANCHOR.TOP, 'middle': MSO_ANCHOR.MIDDLE, 'bottom': MSO_ANCHOR.BOTTOM}[anchor]
        paras = [paragraphs] if isinstance(paragraphs, str) else paragraphs
        for i, content in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            _fill_paragraph(p, content, size, bold, color, align, line_spacing)
            if space_after:
                p.space_after = Pt(space_after)
        return tb

    def rect(self, slide, x, y, w, h, fill='FFFFFF', line='D8DEE8', line_w=0.75, shape=MSO_SHAPE.RECTANGLE,
             name=None, text=None, size=10, bold=False, color='111111', align='center', anchor='middle',
             margins=(0.06, 0.03), line_spacing=1.1):
        sp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        if name:
            sp.name = name
        sp.shadow.inherit = False
        if fill:
            sp.fill.solid(); sp.fill.fore_color.rgb = rgb(fill)
        else:
            sp.fill.background()
        if line:
            sp.line.color.rgb = rgb(line); sp.line.width = Pt(line_w)
        else:
            sp.line.fill.background()
        if text is not None:
            tf = sp.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(margins[0])
            tf.margin_top = tf.margin_bottom = Inches(margins[1])
            tf.vertical_anchor = {'top': MSO_ANCHOR.TOP, 'middle': MSO_ANCHOR.MIDDLE, 'bottom': MSO_ANCHOR.BOTTOM}[anchor]
            paras = [text] if isinstance(text, str) else text
            for i, content in enumerate(paras):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                _fill_paragraph(p, content, size, bold, color, align, line_spacing)
        return sp

    def label(self, slide, x, y, w, h, text, size=10.5, fill=None, name=None, align='center'):
        """主色底白字的结构标签"""
        return self.rect(slide, x, y, w, h, fill=fill or C['primary'], line=None, name=name,
                         text=text, size=size, bold=True, color=C['white'], align=align)

    def badge(self, slide, x, y, n, d=0.3, name=None, fill=None):
        """编号圆标"""
        return self.rect(slide, x, y, d, d, fill=fill or C['primary'], line=None, shape=MSO_SHAPE.OVAL,
                         name=name, text=str(n), size=max(8, d * 30), bold=True, color=C['white'], margins=(0, 0))

    def rule(self, slide, x, y, w, color=None, weight=1.5, name=None):
        ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y), Inches(x + w), Inches(y))
        ln.line.color.rgb = rgb(color or C['primary']); ln.line.width = Pt(weight)
        if name:
            ln.name = name
        return ln

    def arrow(self, slide, x1, y1, x2, y2, color=None, weight=1.25, name=None):
        ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
        ln.line.color.rgb = rgb(color or C['secondary']); ln.line.width = Pt(weight)
        lnxml = ln.line._get_or_add_ln()
        tail = etree.SubElement(lnxml, qn('a:tailEnd')); tail.set('type', 'triangle'); tail.set('w', 'med'); tail.set('len', 'med')
        if name:
            ln.name = name
        return ln

    # ---------- 组合元素 ----------
    def title(self, slide, text, sub=None, name='title'):
        """页标题：左上主色粗体 + 下方细线；可带灰色副题"""
        self.text(slide, MARGIN, 0.28, SLIDE_W - 2 * MARGIN, 0.6, text, size=24, bold=True, color=C['primary'],
                  anchor='middle', name=name, margins=(0, 0))
        self.rule(slide, MARGIN, 0.92, SLIDE_W - 2 * MARGIN, weight=2, name=name + '.rule')
        if sub:
            self.text(slide, MARGIN, 0.95, SLIDE_W - 2 * MARGIN, 0.3, sub, size=10.5, color=C['mid'],
                      anchor='middle', name=name + '.sub', margins=(0, 0))

    def strip(self, slide, text, y=6.7, h=0.46, name='takeaway', size=13):
        """页底主色结论条（白字，可含强调 run）"""
        return self.rect(slide, MARGIN, y, SLIDE_W - 2 * MARGIN, h, fill=C['primary'], line=None, name=name,
                         text=text, size=size, bold=True, color=C['white'], align='center', margins=(0.15, 0.02))

    def page_number(self, slide, total, name='pageno', color=None):
        """右下角「N / M」；self.page_numbers 为 False 时不画。color 给深底页（章节页）用浅色"""
        if not self.page_numbers:
            return None
        return self.text(slide, SLIDE_W - MARGIN - 1.0, SLIDE_H - 0.27, 1.0, 0.22, f'{self.page_no} / {total}',
                         size=9, color=color or C['mid'], align='right', name=name, margins=(0, 0))

    def card(self, slide, x, y, w, h, title=None, lines=None, size=10, title_size=10.5, name='card',
             fill=None, title_fill=None, line_spacing=1.12, badge=None, body_color=None, space_after=2):
        """带标题栏的卡片：标题栏主色白字（或 title_fill），正文若干段（str 或富文本 run 列表）"""
        fill = fill or C['white']
        body_color = body_color or C['ink']
        self.rect(slide, x, y, w, h, fill=fill, line=C['border'], name=name + '.box')
        th = 0.34 if title else 0
        if title:
            self.rect(slide, x, y, w, th, fill=title_fill or C['primary'], line=None, name=name + '.title',
                      text=title, size=title_size, bold=True, color=C['white'], align='left', margins=(0.12, 0.02))
            if badge is not None:
                self.badge(slide, x + w - 0.42, y + 0.04, badge, d=0.26, fill=C['white'], name=name + '.badge')
                # 白底圆里的数字改成主色
                for sp in slide.shapes:
                    if sp.name == name + '.badge':
                        for p in sp.text_frame.paragraphs:
                            for r in p.runs:
                                r.font.color.rgb = rgb(C['primary'])
        if lines:
            self.text(slide, x + 0.02, y + th + 0.04, w - 0.04, h - th - 0.08, lines, size=size, color=body_color,
                      name=name + '.body', line_spacing=line_spacing, margins=(0.1, 0.04), space_after=space_after)

    def number_tile(self, slide, x, y, w, h, number, caption, name='tile', number_color=None, fill=None,
                    number_size=24, caption_size=9.5):
        fill = fill or C['pale']
        self.rect(slide, x, y, w, h, fill=fill, line=None, name=name + '.box')
        self.text(slide, x, y + 0.04, w, h * 0.58, number, size=number_size, bold=True,
                  color=number_color or C['primary'], align='center', anchor='middle', name=name + '.num', margins=(0.02, 0))
        self.text(slide, x, y + h * 0.58, w, h * 0.42, caption, size=caption_size, color=C['gray'], align='center',
                  anchor='top', name=name + '.cap', margins=(0.04, 0), line_spacing=1.05)

    def table(self, slide, x, y, w, h, rows, col_widths=None, size=9.5, header_size=10, name='table',
              header_fill=None, zebra=True, first_col_bold=True, align_center_cols=()):
        """rows[0] 为表头；单元格可为 str 或 (str, {'color':..,'bold':..})"""
        nrows, ncols = len(rows), len(rows[0])
        gs = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(h))
        gs.name = name
        tbl = gs.table
        # 关掉默认样式的条纹 / 首行特殊格式，自己上色
        tblPr = tbl._tbl.tblPr
        tblPr.set('firstRow', '1'); tblPr.set('bandRow', '0')
        style_id = tblPr.find(qn('a:tableStyleId'))
        if style_id is not None:
            style_id.text = '{5940675A-B579-460E-94D1-54222C63F5DA}'  # No Style, Table Grid
        if col_widths:
            for i, cw in enumerate(col_widths):
                tbl.columns[i].width = Inches(cw)
        rh = Inches(h / nrows)
        for r in range(nrows):
            tbl.rows[r].height = rh
            for c in range(ncols):
                cell = tbl.cell(r, c)
                val = rows[r][c]
                txt, opts = (val, {}) if isinstance(val, str) else val
                cell.margin_left = cell.margin_right = Inches(0.06)
                cell.margin_top = cell.margin_bottom = Inches(0.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                tf = cell.text_frame
                tf.word_wrap = True
                paras = txt.split('\n')
                for i, line in enumerate(paras):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    is_header = (r == 0)
                    bold = opts.get('bold', is_header or (first_col_bold and c == 0))
                    color = opts.get('color', C['white'] if is_header else C['ink'])
                    align = 'center' if (is_header or c in align_center_cols) else 'left'
                    _fill_paragraph(p, line, opts.get('size', header_size if is_header else size), bold, color, align, 1.05)
                cell.fill.solid()
                if r == 0:
                    cell.fill.fore_color.rgb = rgb(header_fill or C['primary'])
                elif zebra and r % 2 == 0:
                    cell.fill.fore_color.rgb = rgb(C['fill'])
                else:
                    cell.fill.fore_color.rgb = rgb(C['white'])
        return gs

    # 多系列配色（主蓝 / 正红 / 金 / 灰 / 研究蓝 …；相邻系列色相拉开）
    SERIES_COLORS = ('003F8F', 'C00000', 'D4A017', '6B7280', '0B5CAD', '7FA8E0', 'E8A0A0')
    CHART_TYPES = {
        'bar': XL_CHART_TYPE.BAR_CLUSTERED, 'bar_stacked': XL_CHART_TYPE.BAR_STACKED,
        'column': XL_CHART_TYPE.COLUMN_CLUSTERED, 'column_stacked': XL_CHART_TYPE.COLUMN_STACKED,
        'line': XL_CHART_TYPE.LINE_MARKERS, 'area': XL_CHART_TYPE.AREA_STACKED,
        'pie': XL_CHART_TYPE.PIE, 'doughnut': XL_CHART_TYPE.DOUGHNUT, 'radar': XL_CHART_TYPE.RADAR_MARKERS,
    }

    def chart(self, slide, x, y, w, h, kind, categories, series, name='chart', title=None, number_format='General',
              font_size=11, legend=None, max_value=None, highlight=None):
        """通用原生图表（可编辑）。kind 见 CHART_TYPES；series: [{'name': 系列名, 'values': [...]}]；
        legend 默认多系列 / 饼图 / 环图显示；highlight: 单系列柱图里要标红的类别下标。所有文字显式中英字体。"""
        if kind not in self.CHART_TYPES:
            raise ValueError(f'未知图表类型 {kind!r}（可用 {sorted(self.CHART_TYPES)}）')
        cd = CategoryChartData()
        cd.categories = list(categories)
        for sr in series:
            cd.add_series(sr.get('name') or '值', [float(v) for v in sr['values']])
        gf = slide.shapes.add_chart(self.CHART_TYPES[kind], Inches(x), Inches(y), Inches(w), Inches(h), cd)
        gf.name = name
        ch = gf.chart
        circular = kind in ('pie', 'doughnut')
        ch.has_title = bool(title)
        if title:
            ch.chart_title.text_frame.text = title
            r = ch.chart_title.text_frame.paragraphs[0].runs[0]
            _set_run_font(r, font_size + 1, True, C['gray'])
        show_legend = (len(series) > 1 or circular) if legend is None else legend
        ch.has_legend = show_legend
        if show_legend:
            from pptx.enum.chart import XL_LEGEND_POSITION
            ch.legend.position = XL_LEGEND_POSITION.BOTTOM
            ch.legend.include_in_layout = False
            ch.legend.font.size = Pt(font_size)
            ch.legend.font.color.rgb = rgb(C['gray'])
        plot = ch.plots[0]
        # 雷达图不放数据标签：与轴标签、网格重叠成一团，数值靠网格刻度读
        plot.has_data_labels = kind != 'radar'
        dl = plot.data_labels if plot.has_data_labels else None
        if dl is not None:
            dl.font.size = Pt(font_size); dl.font.color.rgb = rgb(C['ink'])
        if dl is None:
            pass
        elif circular:
            dl.show_percentage = True; dl.show_value = False
            dl.number_format = '0%'; dl.number_format_is_linked = False
            # dLblPos 只有 pie 允许（outEnd）；doughnut / area / radar 的 OOXML 不允许该元素，写了 PowerPoint 会提示修复并丢页
            if kind == 'pie':
                dl.position = XL_LABEL_POSITION.OUTSIDE_END
            plot.vary_by_categories = True
            for i, pt in enumerate(plot.series[0].points):
                pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(self.SERIES_COLORS[i % len(self.SERIES_COLORS)])
            if kind == 'doughnut':
                hole = plot._element.find(qn('c:holeSize'))
                if hole is None:
                    hole = etree.SubElement(plot._element, qn('c:holeSize'))
                hole.set('val', '55')
        else:
            dl.number_format = number_format; dl.number_format_is_linked = False
            dl.font.bold = True
            if kind == 'line':
                dl.position = XL_LABEL_POSITION.ABOVE
            elif kind.endswith('_stacked'):
                dl.position = XL_LABEL_POSITION.CENTER
            elif kind in ('bar', 'column'):
                dl.position = XL_LABEL_POSITION.OUTSIDE_END
            # area / radar 不写 dLblPos（schema 不允许）
            if kind in ('bar', 'column', 'bar_stacked', 'column_stacked'):
                plot.gap_width = 60 if len(series) == 1 else 80
                if kind.endswith('_stacked'):
                    plot.overlap = 100
            for i, ser in enumerate(plot.series):
                color = self.SERIES_COLORS[i % len(self.SERIES_COLORS)]
                if kind in ('line', 'radar'):
                    ser.format.line.color.rgb = rgb(color); ser.format.line.width = Pt(2.25)
                    ser.smooth = False
                    ser.marker.style = 8   # circle
                    ser.marker.size = 7
                    ser.marker.format.fill.solid(); ser.marker.format.fill.fore_color.rgb = rgb(color)
                    ser.marker.format.line.color.rgb = rgb(color)
                else:
                    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = rgb(color)
            if highlight and len(series) == 1 and kind in ('bar', 'column'):
                for i in highlight:
                    pt = plot.series[0].points[i]
                    pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(C['red'])
            if kind != 'radar':
                cat_ax = ch.category_axis
                cat_ax.tick_labels.font.size = Pt(font_size)
                cat_ax.tick_labels.font.color.rgb = rgb(C['ink'])
                cat_ax.format.line.color.rgb = rgb(C['border'])
                cat_ax.has_major_gridlines = False
                if kind in ('bar', 'bar_stacked'):
                    cat_ax.reverse_order = True
                val_ax = ch.value_axis
                val_ax.tick_labels.font.size = Pt(font_size - 1)
                val_ax.tick_labels.font.color.rgb = rgb(C['mid'])
                val_ax.format.line.color.rgb = rgb(C['border'])
                val_ax.has_major_gridlines = kind in ('line', 'column', 'column_stacked', 'area')
                if val_ax.has_major_gridlines:
                    val_ax.major_gridlines.format.line.color.rgb = rgb(C['border'])
                    val_ax.major_gridlines.format.line.width = Pt(0.5)
                if kind in ('bar', 'bar_stacked'):
                    val_ax.visible = False
                if max_value is not None:
                    val_ax.maximum_scale = max_value
                val_ax.minimum_scale = 0
            else:
                ch.category_axis.tick_labels.font.size = Pt(font_size)
                ch.value_axis.tick_labels.font.size = Pt(font_size - 1)
                ch.value_axis.has_major_gridlines = True
                ch.value_axis.major_gridlines.format.line.color.rgb = rgb(C['border'])
        _chart_fonts(ch, font_size)
        _chart_schema_fix(ch)
        return gf

    def bar_chart(self, slide, x, y, w, h, categories, values, name='chart', horizontal=True, color=None,
                  highlight=None, highlight_color=None, number_format='0.00', font_size=9, title=None,
                  max_value=None):
        """原生柱状图（可编辑）。highlight: 需要标红的类别下标列表"""
        cd = CategoryChartData()
        cd.categories = categories
        cd.add_series('值', values)
        ctype = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
        gf = slide.shapes.add_chart(ctype, Inches(x), Inches(y), Inches(w), Inches(h), cd)
        gf.name = name
        ch = gf.chart
        ch.has_legend = False
        ch.has_title = bool(title)
        if title:
            ch.chart_title.text_frame.text = title
            r = ch.chart_title.text_frame.paragraphs[0].runs[0]
            _set_run_font(r, font_size + 1, True, C['gray'])
        plot = ch.plots[0]
        plot.gap_width = 60
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.number_format = number_format
        dl.number_format_is_linked = False
        dl.position = XL_LABEL_POSITION.OUTSIDE_END
        dl.font.size = Pt(font_size); dl.font.bold = True; dl.font.color.rgb = rgb(C['ink'])
        ser = plot.series[0]
        ser.format.fill.solid(); ser.format.fill.fore_color.rgb = rgb(color or C['primary'])
        for i in (highlight or []):
            pt = ser.points[i]
            pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(highlight_color or C['red'])
        cat_ax = ch.category_axis
        cat_ax.tick_labels.font.size = Pt(font_size)
        cat_ax.tick_labels.font.color.rgb = rgb(C['ink'])
        cat_ax.format.line.color.rgb = rgb(C['border'])
        cat_ax.has_major_gridlines = False
        if horizontal:
            cat_ax.reverse_order = True
        val_ax = ch.value_axis
        val_ax.has_major_gridlines = False
        val_ax.visible = False
        if max_value is not None:
            val_ax.maximum_scale = max_value
        val_ax.minimum_scale = 0
        _chart_fonts(ch)
        _chart_schema_fix(ch)
        return gf
