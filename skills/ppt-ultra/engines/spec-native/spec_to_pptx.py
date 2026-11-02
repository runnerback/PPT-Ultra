#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spec Native engine · CLI：deck 规格 JSON → 可编辑 .pptx

用法：
  python3 spec_to_pptx.py <spec.json> <out.pptx>            生成
  python3 spec_to_pptx.py <spec.json> --check               只校验（完整构建到临时文件后丢弃，报错即规格有问题）
  python3 spec_to_pptx.py --layouts                         列出全部版式名

输出：stdout 一行 JSON（{"ok": true, "slides": n, "charts": m, "out": path}）；
      规格有问题时 stdout {"ok": false, "error": "..."}，退出码 1。错误信息按页指出缺什么字段 / 哪里超限，照着改规格重跑即可。
图片 / logo 的相对路径相对 spec 文件所在目录。
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import date as _date

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import ppt_build  # noqa: E402


def _emit(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False))
    return code


def main(argv=None):
    ap = argparse.ArgumentParser(description='deck 规格 JSON → 可编辑 .pptx（Spec Native engine）')
    ap.add_argument('spec', nargs='?', help='规格 JSON 文件')
    ap.add_argument('out', nargs='?', help='输出 .pptx 路径')
    ap.add_argument('--check', action='store_true', help='只校验规格，不落产物')
    ap.add_argument('--layouts', action='store_true', help='列出全部版式名后退出')
    a = ap.parse_args(argv)

    if a.layouts:
        return _emit({'ok': True, 'layouts': sorted(ppt_build.LAYOUTS - {'thanks', 'references'}),
                      'chart_types': sorted(ppt_build.Deck.CHART_TYPES), 'icons': sorted(ppt_build.ppt_extra.ICONS)})
    if not a.spec:
        ap.error('缺少 spec.json')
    if not a.check and not a.out:
        ap.error('缺少输出路径（或加 --check 只校验）')
    if not a.check and not a.out.lower().endswith('.pptx'):
        ap.error('输出路径须以 .pptx 结尾')

    spec_path = os.path.abspath(a.spec)
    try:
        with open(spec_path, encoding='utf-8') as f:
            spec = json.load(f)
    except FileNotFoundError:
        return _emit({'ok': False, 'error': f'规格文件不存在：{spec_path}'}, 1)
    except json.JSONDecodeError as e:
        return _emit({'ok': False, 'error': f'规格不是合法 JSON：第 {e.lineno} 行第 {e.colno} 列 {e.msg}'}, 1)
    if isinstance(spec, dict) and 'date' not in spec:
        spec['date'] = _date.today().isoformat()
    base_dir = os.path.dirname(spec_path)

    try:
        if a.check:
            with tempfile.TemporaryDirectory() as td:
                n, charts = ppt_build.build(spec, os.path.join(td, 'check.pptx'), base_dir=base_dir)
            return _emit({'ok': True, 'checked': True, 'slides': n, 'charts': charts})
        out = os.path.abspath(a.out)
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        n, charts = ppt_build.build(spec, out, base_dir=base_dir)
        return _emit({'ok': True, 'slides': n, 'charts': charts, 'out': out})
    except (ValueError, RuntimeError) as e:
        return _emit({'ok': False, 'error': str(e)}, 1)


if __name__ == '__main__':
    sys.exit(main())
