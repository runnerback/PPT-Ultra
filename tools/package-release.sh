#!/usr/bin/env bash
# 打 GitHub Release 的附件（仓库根目录运行）：
#   bash tools/package-release.sh 1.2.2
# 做四件事：① 核对版本串（git tag、SKILL.md、.claude-plugin/marketplace.json、README 徽章）一致；
#          ② 把 skills/ppt-ultra 打成 dist/ppt-ultra-<版本>.zip（排除 node_modules / __pycache__ / output / .DS_Store / *.pyc）；
#          ③ 生成并验证最多 500 个文件的上传包（完整资源无损归档）；
#          ④ 生成 dist/SHA256SUMS。dist/ 不进 git。
set -euo pipefail
VER="${1:-}"
[ -n "$VER" ] || { echo "用法: bash tools/package-release.sh <版本，如 1.2.0>"; exit 2; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== 1. 版本串核对 =="
fail=0
[[ "$VER" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "FAIL: 无效版本号"; exit 1; }
git rev-parse -q --verify "refs/tags/$VER" >/dev/null || { echo "FAIL: 没有 git tag $VER（请在验证并提交后由维护者创建）"; fail=1; }
if [[ "$(git rev-parse "refs/tags/$VER^{commit}" 2>/dev/null)" != "$(git rev-parse HEAD)" ]]; then
  echo "FAIL: 必须在对应 tag 的提交上构建"; fail=1
fi
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "FAIL: 请提交已跟踪文件的修改后再构建正式 Release"; fail=1
fi
grep -q "version: \"$VER\"" skills/ppt-ultra/SKILL.md || { echo "FAIL: skills/ppt-ultra/SKILL.md 的 version 不是 $VER"; fail=1; }
grep -q "\"version\": \"$VER\"" .claude-plugin/marketplace.json || { echo "FAIL: .claude-plugin/marketplace.json 的 version 不是 $VER"; fail=1; }
grep -q "version-$VER-" README.md || { echo "FAIL: README.md 版本徽章不是 $VER"; fail=1; }
[ -f "docs/releases/$VER.md" ] || { echo "FAIL: 缺 docs/releases/$VER.md（Release 正文）"; fail=1; }
[ "$fail" = 0 ] || exit 1
echo "tag / SKILL.md / marketplace.json / README 徽章 / 发布说明 都是 $VER"
python3 tools/test_security.py
python3 tools/privacy-check.py
python3 tools/test_privacy.py

echo "== 2. 打包 skills/ppt-ultra =="
mkdir -p dist
ZIP="dist/ppt-ultra-$VER.zip"
python3 - "$ZIP" <<'PY'
import importlib.util, sys, zipfile
spec = importlib.util.spec_from_file_location('packager', 'tools/package-upload.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)
with zipfile.ZipFile(sys.argv[1], 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in packager.tracked_files():
        archive.write(path, 'ppt-ultra/' + path.relative_to(packager.SKILL).as_posix())
PY
echo "$ZIP  $(du -h "$ZIP" | cut -f1)  $(unzip -l "$ZIP" | tail -1 | awk '{print $2}') 个文件"

echo "== 3. 生成并验证紧凑上传包 =="
UPLOAD_ZIP="dist/ppt-ultra-$VER-upload.zip"
python3 tools/package-upload.py --output "$UPLOAD_ZIP" --audit-dir dist
python3 tools/test_upload_package.py --zip "$UPLOAD_ZIP" --audit-manifest "dist/ppt-ultra-$VER-source-manifest.json"

echo "== 4. 校验和 =="
( cd dist && shasum -a 256 "ppt-ultra-$VER.zip" "ppt-ultra-$VER-upload.zip" "ppt-ultra-$VER-source-"*.zip "ppt-ultra-$VER-source-manifest.json" > SHA256SUMS && cat SHA256SUMS )
echo "== 完成：完整包、上传包、明文源码分卷、来源清单与 SHA256SUMS =="
