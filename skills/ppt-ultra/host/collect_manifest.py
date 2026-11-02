#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
host/collect_manifest.py · 从一次 host-quick 运行的 work_dir 里程序化收集产物清单 manifest.json（不信任 agent 的自述）。

用法：python host/collect_manifest.py <work_dir> [-o manifest.json] [--preflight] [--pptx-name deck.pptx]
  - 找项目：work_dir 下任意层级（最多 3 层）含 svg_output/ 的目录；取 exports/ 里最新的 .pptx
  - 读检查器 / 导出报告：validation/svg_quality_report.json（errors / warnings）、validation/<stem>.report.json（postflight status / quality_gate）
  - 看 pptx 本体（zip）：页数、原生 chart 数、原生 table 数、用到的字体、备注页数
  - --preflight：有 soffice 就转 PDF 到 work_dir/preflight/，页数与 pptx 一致才算通过（没有 soffice 记 skipped，不装通过）
  - --pptx-name：顺手把最新 pptx 复制为 work_dir/<name>（agent 忘了复制时宿主兜住的是「复制」这一步，不是产物本身）
退出码：找到 pptx 且（未做预检或预检通过）为 0，否则 1；manifest 不论成败都写出来。
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile


def find_projects(work):
    hits = []
    for depth in ('*', '*/*', '*/*/*'):
        for d in glob.glob(os.path.join(work, depth, 'svg_output')):
            hits.append(os.path.dirname(d))
    return sorted(set(hits))


def latest_pptx(project):
    files = glob.glob(os.path.join(project, 'exports', '*.pptx'))
    files = [f for f in files if not os.path.basename(f).startswith('~$')]
    return max(files, key=os.path.getmtime) if files else None


def read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def quality_summary(project):
    q = read_json(os.path.join(project, 'validation', 'svg_quality_report.json'))
    if not q:
        return None
    cats = q.get('categories') or {}
    def n(cat):
        c = cats.get(cat) or {}
        if not isinstance(c, dict):
            return 0
        return c['count'] if isinstance(c.get('count'), int) else len(c.get('issues') or [])
    summary = q.get('summary') if isinstance(q.get('summary'), dict) else {}
    return {'stage': q.get('stage'), 'blocking': n('blocking'), 'introduced': n('introduced'), 'inherited': n('inherited'),
            'summary': {k: v for k, v in summary.items() if isinstance(v, (int, str, bool))}}


def postflight_summary(project, pptx):
    stem = os.path.splitext(os.path.basename(pptx))[0]
    rep = read_json(os.path.join(project, 'validation', f'{stem}.report.json'))
    if not rep:
        return None
    out = {'status': rep.get('status')}
    for k in ('quality', 'checks', 'package'):
        v = rep.get(k)
        if isinstance(v, dict):
            out[k] = {kk: vv for kk, vv in v.items() if isinstance(vv, (int, str, bool))}
    return out


def inspect_pptx(pptx):
    out = {'slides': 0, 'charts': 0, 'tables': 0, 'notes_slides': 0, 'fonts': []}
    fonts = {}
    with zipfile.ZipFile(pptx) as z:
        names = z.namelist()
        slides = [n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
        out['slides'] = len(slides)
        out['charts'] = len([n for n in names if re.fullmatch(r'ppt/charts/chart\d+\.xml', n)])
        out['notes_slides'] = len([n for n in names if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml', n)])
        for n in slides:
            xml = z.read(n).decode('utf-8', 'replace')
            out['tables'] += xml.count('<a:tbl>')
            for m in re.finditer(r'typeface="([^"]+)"', xml):
                fonts[m.group(1)] = fonts.get(m.group(1), 0) + 1
    out['fonts'] = [k for k, _ in sorted(fonts.items(), key=lambda kv: -kv[1])[:8]]
    return out


def workflow_times(project):
    log = os.path.join(project, 'validation', 'workflow.log')
    if not os.path.isfile(log):
        return None
    stamps = re.findall(r'=== (\d{4}-\d{2}-\d{2}T[\d:.]+Z) ', open(log, encoding='utf-8', errors='replace').read())
    if not stamps:
        return None
    return {'first': stamps[0], 'last': stamps[-1], 'commands': len(stamps) // 2}


def preflight(work, pptx, expect_slides):
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice:
        return {'status': 'skipped', 'reason': '没有 soffice'}
    outdir = os.path.join(work, 'preflight')
    os.makedirs(outdir, exist_ok=True)
    t0 = time.time()
    try:
        subprocess.run([soffice, '--headless', '--convert-to', 'pdf', '--outdir', outdir, pptx], capture_output=True, timeout=300, check=False)
    except subprocess.TimeoutExpired:
        return {'status': 'fail', 'reason': 'soffice 转换超时（300s）'}
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(pptx))[0] + '.pdf')
    if not os.path.isfile(pdf):
        return {'status': 'fail', 'reason': 'soffice 没有产出 PDF'}
    pages = None
    try:
        import pymupdf
        pages = len(pymupdf.open(pdf))
    except ImportError:
        try:
            import fitz
            pages = len(fitz.open(pdf))
        except ImportError:
            pass
    res = {'status': 'ok', 'pdf': pdf, 'pages': pages, 'seconds': round(time.time() - t0, 1)}
    if pages is None:
        res['status'] = 'unknown'; res['reason'] = '没有 PyMuPDF，数不了页'
    elif pages != expect_slides:
        res['status'] = 'fail'; res['reason'] = f'PDF {pages} 页 ≠ pptx {expect_slides} 页'
    return res


def main():
    ap = argparse.ArgumentParser(description='收集 host-quick 运行产物清单')
    ap.add_argument('work_dir')
    ap.add_argument('-o', '--output')
    ap.add_argument('--preflight', action='store_true')
    ap.add_argument('--pptx-name', help='把最新 pptx 复制为 work_dir/<name>')
    a = ap.parse_args()
    work = os.path.abspath(a.work_dir)
    out_path = a.output or os.path.join(work, 'manifest.json')
    m = {'manifest_version': 1, 'work_dir': work, 'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'ok': False}
    projects = find_projects(work)
    m['projects'] = projects
    if not projects:
        m['error'] = 'work_dir 下没有含 svg_output/ 的项目目录'
    else:
        cands = [(latest_pptx(p), p) for p in projects]
        cands = [(f, p) for f, p in cands if f]
        if not cands:
            m['error'] = '项目里没有导出的 pptx（exports/*.pptx）'
            m['svg_count'] = {p: len(glob.glob(os.path.join(p, 'svg_output', '*.svg'))) for p in projects}
        else:
            pptx, project = max(cands, key=lambda c: os.path.getmtime(c[0]))
            m['project'] = project
            m['pptx'] = pptx
            m['pptx_size'] = os.path.getsize(pptx)
            m['pptx_mtime'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(os.path.getmtime(pptx)))
            m['svg_count'] = len(glob.glob(os.path.join(project, 'svg_output', '*.svg')))
            m['quality'] = quality_summary(project)
            m['postflight'] = postflight_summary(project, pptx)
            m['deck'] = inspect_pptx(pptx)
            m['workflow'] = workflow_times(project)
            if a.pptx_name:
                dst = os.path.join(work, a.pptx_name)
                if os.path.abspath(dst) != os.path.abspath(pptx):
                    shutil.copyfile(pptx, dst)
                m['pptx_copy'] = dst
            if a.preflight:
                m['preflight'] = preflight(work, pptx, m['deck']['slides'])
            pf = m.get('preflight') or {}
            m['ok'] = pf.get('status') in (None, 'ok', 'skipped', 'unknown') and m['deck']['slides'] > 0
            if pf.get('status') == 'fail':
                m['error'] = f'预检失败：{pf.get("reason")}'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    print(json.dumps({'ok': m['ok'], 'manifest': out_path, 'pptx': m.get('pptx'), 'slides': (m.get('deck') or {}).get('slides'),
                      'preflight': (m.get('preflight') or {}).get('status'), 'error': m.get('error')}, ensure_ascii=False))
    sys.exit(0 if m['ok'] else 1)


if __name__ == '__main__':
    main()
