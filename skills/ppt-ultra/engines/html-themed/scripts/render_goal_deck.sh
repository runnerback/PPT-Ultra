#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${DASHI_PPT_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../project" && pwd)}"
CALLER_CWD="$(pwd)"

if [[ $# -ne 2 ]]; then
  echo "Usage: render_goal_deck.sh <goal-spec.json> <output/ppt/index.html>" >&2
  exit 2
fi

SPEC_PATH="$1"
OUT_PATH="$2"

if [[ "$SPEC_PATH" != /* ]]; then
  SPEC_PATH="$CALLER_CWD/$SPEC_PATH"
fi

if [[ "$OUT_PATH" != /* ]]; then
  OUT_PATH="$CALLER_CWD/$OUT_PATH"
fi

cd "$PROJECT_ROOT"
# .npmrc 缺失时从模板重建(npm publish 会剔除 .npmrc,个别安装路径可能丢失)。
if [[ ! -f .npmrc && -f npmrc.template ]]; then
  cp npmrc.template .npmrc
fi
if [[ ! -f node_modules/.package-lock.json || package.json -nt node_modules/.package-lock.json || package-lock.json -nt node_modules/.package-lock.json ]]; then
  NPM_REGISTRY="$(node scripts/ensure-registry.mjs)"
  npm ci --ignore-scripts --no-audit --no-fund --registry "$NPM_REGISTRY"
fi
# Browser provisioning belongs to the host, outside generation. Use an approved
# preinstalled Chrome/Chromium (CHROME_PATH), or a host-provisioned Playwright cache.
# No browser binary is downloaded or installed by this script.
mkdir -p "$(dirname "$OUT_PATH")"
npm run props:safe -- --goal "$SPEC_PATH" --write
npm run validate:goal-spec -- "$SPEC_PATH"
npm run render:goal -- "$SPEC_PATH" "$OUT_PATH"
npm run validate:swiss -- "$OUT_PATH"
npm run validate:goal-copy -- "$SPEC_PATH" "$OUT_PATH"
OUT_DIR="$(dirname "$OUT_PATH")"
# 缺省端口落在 SKILL.md 约定的 5200-5999 段(4178/4300/4400 为用户保留端口);被占用时服务自增。
PREVIEW_PORT="${DASHI_PPT_PREVIEW_PORT:-5200}"
npm run preview:start -- "$OUT_DIR" "$PREVIEW_PORT"
