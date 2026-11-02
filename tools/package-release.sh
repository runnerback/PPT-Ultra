#!/usr/bin/env bash
# 打 GitHub Release 的附件（仓库根目录运行）：
#   bash tools/package-release.sh 1.2.0
# 做三件事：① 核对版本串（git tag、SKILL.md、.claude-plugin/marketplace.json、README 徽章）一致；
#          ② 把 skills/ppt-ultra 打成 dist/ppt-ultra-<版本>.zip（排除 node_modules / __pycache__ / output / .DS_Store / *.pyc）；
#          ③ 生成 dist/SHA256SUMS。dist/ 不进 git。
set -euo pipefail
VER="${1:-}"
[ -n "$VER" ] || { echo "用法: bash tools/package-release.sh <版本，如 1.2.0>"; exit 2; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== 1. 版本串核对 =="
fail=0
git rev-parse -q --verify "refs/tags/$VER" >/dev/null || { echo "FAIL: 没有 git tag $VER（先 git tag $VER && git push origin $VER）"; fail=1; }
grep -q "version: \"$VER\"" skills/ppt-ultra/SKILL.md || { echo "FAIL: skills/ppt-ultra/SKILL.md 的 version 不是 $VER"; fail=1; }
grep -q "\"version\": \"$VER\"" .claude-plugin/marketplace.json || { echo "FAIL: .claude-plugin/marketplace.json 的 version 不是 $VER"; fail=1; }
grep -q "version-$VER-" README.md || { echo "FAIL: README.md 版本徽章不是 $VER"; fail=1; }
[ -f "docs/releases/$VER.md" ] || { echo "FAIL: 缺 docs/releases/$VER.md（Release 正文）"; fail=1; }
[ "$fail" = 0 ] || exit 1
echo "tag / SKILL.md / marketplace.json / README 徽章 / 发布说明 都是 $VER"

echo "== 2. 打包 skills/ppt-ultra =="
mkdir -p dist
ZIP="dist/ppt-ultra-$VER.zip"
rm -f "$ZIP"
( cd skills && zip -q -r "../$ZIP" ppt-ultra \
    -x "ppt-ultra/**/node_modules/*" -x "ppt-ultra/**/__pycache__/*" -x "ppt-ultra/**/*.pyc" \
    -x "ppt-ultra/**/output/*" -x "ppt-ultra/**/.DS_Store" -x "ppt-ultra/.DS_Store" )
echo "$ZIP  $(du -h "$ZIP" | cut -f1)  $(unzip -l "$ZIP" | tail -1 | awk '{print $2}') 个文件"

echo "== 3. 校验和 =="
( cd dist && shasum -a 256 "ppt-ultra-$VER.zip" > SHA256SUMS && cat SHA256SUMS )
echo "== 完成：上传 dist/ppt-ultra-$VER.zip 与 dist/SHA256SUMS 到 Release =="
