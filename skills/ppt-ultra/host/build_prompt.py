#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
host/build_prompt.py · 把宿主 brief（host/brief.schema.json）渲染成交给 agent 的 prompt（中文，确定性）。

用法：python host/build_prompt.py <brief.json> [-o prompt.md]
      python host/build_prompt.py <brief.json> --check     只校验 brief，不输出 prompt
校验：必填字段、枚举、材料 / 图片文件在 work_dir 下存在、总页数与 roster 一致、字体给全。错了直接报错退出码 2，不猜。
改稿：brief.revision.feedback 存在 → 渲染改稿 prompt（在 work_dir 已有项目上改，不重建）。
agent 收到 prompt 后：读 SKILL.md → 读 workflows/profiles/host-quick.md → 按它执行；最后跑 host/collect_manifest.py。
"""
import argparse
import json
import os
import sys

STYLE_DEFAULTS = {'visual_style': 'swiss-minimal', 'mode': 'pyramid', 'body_px': 18}
CONSTRAINT_DEFAULTS = {'speaker_notes': False, 'custom_animations': False, 'narration': False, 'native_charts_tables': True,
                       'ai_images': False, 'web_research': False, 'zero_image': True}
OUTPUT_DEFAULTS = {'pptx_name': 'deck.pptx', 'manifest_name': 'manifest.json', 'log_name': 'HOST-LOG.md'}


class BriefError(ValueError):
    pass


def _need(d, key, where='brief'):
    if key not in d or d[key] in (None, '', [], {}):
        raise BriefError(f'{where}.{key} 缺失')
    return d[key]


def load_brief(path):
    with open(path, encoding='utf-8') as f:
        b = json.load(f)
    if not isinstance(b, dict):
        raise BriefError('brief 须为 JSON 对象')
    if b.get('brief_version') != 1:
        raise BriefError(f'brief_version 只支持 1，收到 {b.get("brief_version")!r}')
    for k in ('job_id', 'work_dir', 'skill_dir', 'python', 'deck', 'pages', 'materials'):
        _need(b, k)
    if not os.path.isabs(b['work_dir']) or not os.path.isabs(b['skill_dir']) or not os.path.isabs(b['python']):
        raise BriefError('work_dir / skill_dir / python 必须是绝对路径')
    if not os.path.isdir(b['work_dir']):
        raise BriefError(f'work_dir 不存在：{b["work_dir"]}')
    if not os.path.isfile(os.path.join(b['skill_dir'], 'SKILL.md')):
        raise BriefError(f'skill_dir 下没有 SKILL.md：{b["skill_dir"]}')
    if b.get('deliverable', 'pptx') != 'pptx':
        raise BriefError('deliverable 目前只支持 pptx')
    _need(b['deck'], 'title', 'deck')
    total = _need(b['pages'], 'total', 'pages')
    if not isinstance(total, int) or not (1 <= total <= 60):
        raise BriefError('pages.total 须为 1~60 的整数')
    roster = b['pages'].get('roster') or []
    if roster:
        nos = [r.get('no') for r in roster]
        if nos != list(range(1, total + 1)):
            raise BriefError(f'pages.roster 的 no 须为 1..{total} 连续，收到 {nos}')
        for r in roster:
            _need(r, 'title', f'roster[{r.get("no")}]')
    for i, m in enumerate(b['materials']):
        _need(m, 'path', f'materials[{i}]'); _need(m, 'role', f'materials[{i}]')
        if m['role'] not in ('primary', 'facts', 'outline', 'reference'):
            raise BriefError(f'materials[{i}].role 非法：{m["role"]!r}')
        if not os.path.isfile(os.path.join(b['work_dir'], m['path'])):
            raise BriefError(f'材料文件不存在：{os.path.join(b["work_dir"], m["path"])}')
    for i, im in enumerate(b.get('images') or []):
        _need(im, 'path', f'images[{i}]')
        if not os.path.isfile(os.path.join(b['work_dir'], im['path'])):
            raise BriefError(f'图片文件不存在：{os.path.join(b["work_dir"], im["path"])}')
    style = {**STYLE_DEFAULTS, **(b.get('style') or {})}
    fonts = style.get('fonts') or {}
    if not fonts.get('cjk') or not fonts.get('latin'):
        raise BriefError('style.fonts.cjk / latin 必须都给（必须是渲染端真实安装的字体）')
    for k, v in (style.get('palette') or {}).items():
        s = str(v).lstrip('#')
        if len(s) != 6 or any(c not in '0123456789abcdefABCDEF' for c in s):
            raise BriefError(f'style.palette.{k} 不是 6 位十六进制：{v!r}')
    b['style'] = style
    b['constraints'] = {**CONSTRAINT_DEFAULTS, **(b.get('constraints') or {})}
    b['output'] = {**OUTPUT_DEFAULTS, **(b.get('output') or {})}
    b.setdefault('language', 'zh-CN'); b.setdefault('canvas', 'ppt169')
    fs_ = b.get('forbidden_strings') or []
    if not isinstance(fs_, list) or any(not isinstance(x, str) or not x.strip() for x in fs_):
        raise BriefError('forbidden_strings 须为非空字符串数组')
    b['forbidden_strings'] = [x.strip() for x in fs_]
    if b.get('revision') is not None:
        _need(b['revision'], 'feedback', 'revision')
    return b


def _lines(items, prefix='- '):
    return '\n'.join(f'{prefix}{x}' for x in items)


def render(b):
    deck, pages, style, cons, out = b['deck'], b['pages'], b['style'], b['constraints'], b['output']
    W, S, PY = b['work_dir'], b['skill_dir'], b['python']
    fonts = style['fonts']
    body = style['body_px']
    roles = f'--role title:"{fonts["cjk"]}":{round(body * 1.9)} --role subtitle:"{fonts["cjk"]}":{round(body * 1.3)} --role body:"{fonts["cjk"]}":{body} --role annotation:"{fonts["cjk"]}":{max(12, body - 3)} --role footnote:"{fonts["cjk"]}":{max(11, body - 5)}'
    mats = _lines(f'`{W}/{m["path"]}`（{m["role"]}{"；" + m["note"] if m.get("note") else ""}）' for m in b['materials'])
    imgs = _lines(f'`{W}/{im["path"]}`{"：" + im["caption"] if im.get("caption") else ""}{"（建议放第 " + str(im["page_hint"]) + " 页）" if im.get("page_hint") else ""}' for im in (b.get('images') or []))
    roster = pages.get('roster') or []
    roster_md = '\n'.join(f'| {r["no"]} | {r["title"]} | {r.get("job", "")} | {r.get("content_ref", "")} |' for r in roster)
    pal = '、'.join(f'{k} {("#" + str(v).lstrip("#")).upper()}' for k, v in (style.get('palette') or {}).items())
    deck_meta = _lines(f'{k}：{deck[key]}' for key, k in (('title', '标题'), ('subtitle', '副标题'), ('author', '落款'), ('date', '日期'), ('audience', '对象'), ('purpose', '用途'), ('tone', '语气')) if deck.get(key))
    rev = b.get('revision')

    images_md = ('## 图片（只用这些，不生图不搜图）\n' + imgs) if imgs else '## 图片\n- 零图片 deck：不放任何图片，不生图、不搜图，信息靠文字、原生形状、原生图表 / 表格承载。'
    mode_md = ('，另读 `' + S + '/references/modes/' + style['mode'] + '.md`') if style.get('mode') else ''
    theme_md = ('；主题参考 themes.json 键 `' + style['theme_ref'] + '`') if style.get('theme_ref') else ''
    notes_md = ('；' + style['notes']) if style.get('notes') else ''
    keep_md = ('- 必须保留（原样）：\n' + _lines(b['must_keep'], '  - ')) if b.get('must_keep') else ''
    avoid_md = ('- 不许出现：\n' + _lines(b['must_avoid'], '  - ')) if b.get('must_avoid') else ''
    forbid_md = ('- **禁用字串（程序硬校验，导出前用 grep 逐个确认 svg_output 里一处都没有，命中就改写）**：' + '、'.join('「' + x + '」' for x in b['forbidden_strings'])) if b.get('forbidden_strings') else ''
    prev_md = ('上一版 manifest：`' + W + '/' + rev['previous_manifest'] + '`。') if rev and rev.get('previous_manifest') else ''
    head = f"""你收到一份宿主交来的 PPT 任务（PPT Ultra 宿主契约 v1）。先读 `{S}/SKILL.md`，再读 `{S}/workflows/profiles/host-quick.md` 并严格按它执行；路由、profile、风格、页数、字体都已由宿主定好，不要再做 intake 提问，也不要自行改动这些决定。

## 固定参数
- SKILL_DIR = `{S}`；文档里的 `${{SKILL_DIR}}` 与 `skills/ppt-master/` 前缀一律换成它。
- WORK = `{W}`；项目、产物、日志只写在这里面，命令写成 `cd "{W}" && …`。
- Python = `{PY}`（替换文档里的 python3）。
- 任务 id：`{b["job_id"]}`；交付格式：{b["deliverable"]}；语言：{b["language"]}（每页根 `<svg lang="{b["language"]}">`）；画布：{b["canvas"]}。
- 宿主没有人在线，不要提问、不要等待确认；不要启动任何常驻服务（live preview / 编辑器 / confirm UI / 预览服务器）。

## 材料（数字只能来自这里）
{mats}
{images_md}

## 作品信息
{deck_meta}
"""
    if roster:
        pages_md = f"""## 页面（总页数 {pages["total"]}，严格等于，顺序与标题意图照此）
| 页 | 标题意图 | 这页要完成的事 | 材料定位 |
|---|---|---|---|
{roster_md}
"""
    else:
        pages_md = f"""## 页面
- 总页数 {pages["total"]}（含封面与收尾），严格等于；分页由你定，每页一个核心信息，标题写判断句。
"""
    style_md = f"""## 风格（宿主已定，不要改）
- visual_style = `{style["visual_style"]}`（读 `{S}/references/visual-styles/{style["visual_style"]}.md`{mode_md}）{theme_md}
- 配色：{pal or "按 visual_style 预设"}
- 字体：中文 `{fonts["cjk"]}`，西文 `{fonts["latin"]}`。每页根 `<svg font-family="{fonts["cjk"]}">`；校准命令固定为：
  `{PY} {S}/scripts/text_measure.py calibrate <project_path> {roles}`
  这是渲染端真实安装的字体，不要换成别的，也不要在 SVG 里写别的 font-family。
- 正文字号 {body}px；标题约 {round(body * 1.9)}px；脚注不小于 {max(11, body - 5)}px。{notes_md}
"""
    cons_md = f"""## 约束
- Speaker Notes {"开" if cons["speaker_notes"] else "关"}、Custom Animations {"开" if cons["custom_animations"] else "关"}、旁白 {"开" if cons["narration"] else "关"}；AI 生图 {"允许" if cons["ai_images"] else "不允许"}；联网调研 {"允许" if cons["web_research"] else "不允许"}。
- 图表 / 表格：{"有可比数值就用原生 chart、表格用原生 table（导出加 --native-charts-and-tables）" if cons["native_charts_tables"] else "全部用形状与文本，不用原生 chart / table"}。
{keep_md}
{avoid_md}
{forbid_md}
"""
    if rev:
        task_md = f"""## 这是一次改稿
WORK 下已有上一版项目（按 host-quick.md「改稿」一节找到它，不要新建项目）。改稿意见：

> {rev["feedback"]}

按意见改对应页面的 SVG（页数增删要按 quick-generate.md 的 Revision 规则重新编号与改页脚），重跑 final 检查器，重新导出；上一版产物保留，新产物带新时间戳。{prev_md}
"""
    else:
        task_md = """## 这是一次新做
按 host-quick.md 的步骤：建项目 → 导入材料 → 校准 → 逐页手写 SVG → 门禁 → 导出。
"""
    tail = f"""## 收尾（必须做）
1. 过程记录写到 `{W}/{out["log_name"]}`（时间线、读了哪些文档、每次检查器的 errors / warnings 与修复、自行决定的事、每页一行自评）。
2. 导出成功后把最终 pptx 复制为 `{W}/{out["pptx_name"]}`。
3. 跑 `{PY} {S}/host/collect_manifest.py "{W}" --preflight --brief "{W}/brief.json" -o "{W}/{out["manifest_name"]}"`，它会写出 manifest.json（产物、门禁状态、页数、字体、预检结果、禁用字串命中）；有禁用字串命中它会判 ok=false，所以导出前自己先 grep。
4. 最后一条回复只写一行 JSON：`{{"ok": true|false, "manifest": "{W}/{out["manifest_name"]}", "note": "一句话"}}`。导不出 pptx 也要走第 3、4 步并把原因写进 {out["log_name"]}。
"""
    return head + pages_md + style_md + cons_md + task_md + tail


def main():
    ap = argparse.ArgumentParser(description='宿主 brief → agent prompt')
    ap.add_argument('brief')
    ap.add_argument('-o', '--output')
    ap.add_argument('--check', action='store_true', help='只校验 brief')
    a = ap.parse_args()
    try:
        b = load_brief(a.brief)
    except (BriefError, OSError, json.JSONDecodeError) as e:
        print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
    if a.check:
        print(json.dumps({'ok': True, 'job_id': b['job_id'], 'pages': b['pages']['total'], 'revision': bool(b.get('revision'))}, ensure_ascii=False))
        return
    text = render(b)
    if a.output:
        with open(a.output, 'w', encoding='utf-8') as f:
            f.write(text)
        print(json.dumps({'ok': True, 'prompt': a.output, 'chars': len(text)}, ensure_ascii=False))
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
