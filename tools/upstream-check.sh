#!/usr/bin/env bash
# PPT Ultra 上游版本核对（仓库根目录运行）：
#   读 tools/upstream-pins.json 里三上游的钉住版本，查 GitHub 当前版本，打印对照表。
#   任一上游落后 → 退出码 1（提示按 skills/ppt-ultra/NOTICE.md「合并上游更新」手动合并）。
# 用法：bash tools/upstream-check.sh          依赖：curl、python3；匿名访问 GitHub API（每小时 60 次足够）
#      GITHUB_TOKEN=... bash tools/upstream-check.sh   需要更高频率时带 token
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PINS="$ROOT/tools/upstream-pins.json"
AUTH=()
[[ -n "${GITHUB_TOKEN:-}" ]] && AUTH=(-H "Authorization: Bearer $GITHUB_TOKEN")

api() { curl -sS -m 20 ${AUTH[@]+"${AUTH[@]}"} -H "Accept: application/vnd.github+json" "https://api.github.com/$1"; }
raw() { curl -sS -m 20 "https://raw.githubusercontent.com/$1"; }

python3 - "$PINS" <<'PY' > /tmp/ppt-ultra-upstream-pins.tsv
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for name, u in d["upstreams"].items():
    print("\t".join([name, u["repo"], u["kind"], u.get("file", ""), u["pinned"], u.get("pinned_date", "")]))
PY

behind=0
printf "%-20s %-12s %-44s %-44s %s\n" "上游" "方式" "钉住" "当前" "状态"
while IFS=$'\t' read -r name repo kind file pinned pinned_date; do
  case "$kind" in
    release)
      cur="$(api "repos/$repo/releases/latest" | python3 -c 'import sys,json; d=json.load(sys.stdin); print((d.get("tag_name") or "").lstrip("v"), (d.get("published_at") or "")[:10])')" ;;
    file-version)
      ver="$(raw "$repo/main/$file" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("version",""))')"
      date="$(api "repos/$repo/commits?per_page=1" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["commit"]["committer"]["date"][:10])')"
      cur="$ver $date" ;;
    commit)
      cur="$(api "repos/$repo/commits?per_page=1" | python3 -c 'import sys,json; d=json.load(sys.stdin)[0]; print(d["sha"], d["commit"]["committer"]["date"][:10])')" ;;
    *) echo "未知 kind: $kind（$name）" >&2; exit 2 ;;
  esac
  cur_id="${cur%% *}"; cur_date="${cur#* }"
  pin_show="$pinned"; [[ -n "$pinned_date" ]] && pin_show="${pinned:0:12} ($pinned_date)"
  cur_show="$cur_id"; [[ "$kind" == commit ]] && cur_show="${cur_id:0:12}"
  if [[ "$cur_id" == "$pinned" ]]; then status="最新"; else status="落后 → 合并（NOTICE.md 第 $( [[ $name == ppt-master ]] && echo 1 || { [[ $name == guizang* ]] && echo 2 || echo 3; }) 步）"; behind=1; fi
  printf "%-20s %-12s %-44s %-44s %s\n" "$name" "$kind" "$pin_show" "$cur_show ($cur_date)" "$status"
done < /tmp/ppt-ultra-upstream-pins.tsv
rm -f /tmp/ppt-ultra-upstream-pins.tsv

if [[ $behind -eq 0 ]]; then echo "== 三上游均为钉住版本 =="; else echo "== 有上游更新：按 skills/ppt-ultra/NOTICE.md「合并上游更新」手动合并，合并后更新 tools/upstream-pins.json 并跑 bash tools/smoke.sh =="; fi
exit $behind
