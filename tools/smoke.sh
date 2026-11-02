#!/usr/bin/env bash
# PPT Ultra 维护者冒烟测试（仓库根目录运行）：
#   1) PPTX Native 引擎完整性检查（attribution_guard）
#   2) Spec Native 引擎：--layouts、全部示例 --check 并构建到 output/smoke/
#   2b) 风格 brief 表 themes.json 与来源一致 + theme05 的 spec_style 能构建
#   3) HTML Editorial：演讲者运行时同步检查（有 node 才跑）
#   4) 可选：装了 LibreOffice 时把第一份示例转 PDF 看能否打开
# 用法：bash tools/smoke.sh        依赖：python3（已 pip install -r skills/ppt-ultra/requirements.txt）、可选 node / dot / soffice
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$ROOT/skills/ppt-ultra"
PY="${PYTHON:-python3}"
OUT="$ROOT/output/smoke"
mkdir -p "$OUT"
fail=0

echo "== 1. attribution_guard =="
if "$PY" "$SKILL/scripts/attribution_guard.py"; then echo "ok"; else echo "FAIL: attribution_guard"; fail=1; fi

echo "== 2. spec-native =="
"$PY" "$SKILL/engines/spec-native/spec_to_pptx.py" --layouts >/dev/null && echo "layouts ok"
if command -v dot >/dev/null 2>&1; then echo "graphviz: $(dot -V 2>&1)"; else echo "graphviz: 未安装，03-diagrams 预期失败（flow / swimlane / hierarchy 需要 dot）"; fi
for f in "$SKILL"/engines/spec-native/examples/*.json; do
  b="$(basename "$f" .json)"
  if ! command -v dot >/dev/null 2>&1 && [[ "$b" == 03-* ]]; then echo "skip $b（无 dot）"; continue; fi
  if r="$("$PY" "$SKILL/engines/spec-native/spec_to_pptx.py" "$f" "$OUT/$b.pptx")"; then echo "$b: $r"; else echo "FAIL: $b: $r"; fail=1; fi
done
# 错误路径必须报错
if "$PY" "$SKILL/engines/spec-native/spec_to_pptx.py" <(printf '{"slides":[{"layout":"nope","title":"x"}]}') --check >/dev/null 2>&1; then echo "FAIL: 未知版式没有报错"; fail=1; else echo "error path ok"; fi

echo "== 2b. style briefs =="
if command -v node >/dev/null 2>&1; then
  if node "$ROOT/tools/build-style-briefs.mjs" --check; then
    # 浅底主题的 spec_style 必须能被引擎接受：用 theme05 覆盖 01-basic 构建一次
    if "$PY" - "$SKILL" "$OUT" <<'PY'
import json, subprocess, sys, copy
skill, out = sys.argv[1], sys.argv[2]
themes = json.load(open(f"{skill}/references/style-briefs/themes.json")); spec = json.load(open(f"{skill}/engines/spec-native/examples/01-basic.json"))
spec["style"] = themes["themed"]["theme05"]["spec_style"]; json.dump(spec, open(f"{out}/01-basic-theme05.json", "w"), ensure_ascii=False)
r = subprocess.run([sys.executable, f"{skill}/engines/spec-native/spec_to_pptx.py", f"{out}/01-basic-theme05.json", f"{out}/01-basic-theme05.pptx"], capture_output=True, text=True)
print(r.stdout.strip()); sys.exit(0 if '"ok": true' in r.stdout else 1)
PY
    then echo "theme05 spec_style ok"; else echo "FAIL: theme05 spec_style build"; fail=1; fi
  else echo "FAIL: themes.json 与来源不一致"; fail=1; fi
else echo "skip（无 node）"; fi

echo "== 3. html-editorial runtime sync =="
if command -v node >/dev/null 2>&1; then
  if node "$SKILL/engines/html-editorial/scripts/check-presenter-runtime-sync.mjs" >/dev/null 2>&1; then echo "ok"; else echo "FAIL: check-presenter-runtime-sync"; fail=1; fi
else echo "skip（无 node）"; fi

echo "== 4. render (optional) =="
if command -v soffice >/dev/null 2>&1; then
  soffice --headless --convert-to pdf --outdir "$OUT" "$OUT/01-basic.pptx" >/dev/null 2>&1 && echo "pdf: $OUT/01-basic.pdf" || { echo "FAIL: soffice convert"; fail=1; }
else echo "skip（无 soffice）"; fi

echo "== result: $([[ $fail -eq 0 ]] && echo PASS || echo FAIL) =="
exit $fail
