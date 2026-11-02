# 发布一个 GitHub Release（维护者手册）

> 版本：1.1 ｜ 更新：2026-11-02 ｜ 适用：PPT Ultra 1.2.0 及以后（1.1 起推 tag 自动发布，手动步骤留作备用）

GitHub 的 Release 不会从 tag 自动生成，要单独建。一次发布 = **tag + 正文 + 附件**，正文和附件都由仓库里的文件生成，不临场手写。

## 0. 前置（打 tag 之前）

1. 三处版本串一致：`skills/ppt-ultra/SKILL.md` frontmatter `version`、`.claude-plugin/marketplace.json` `metadata.version`、`README.md` 的 version 徽章。
2. `skills/ppt-ultra/NOTICE.md`「修改记录」有这一版的条目（去掉「未发布」字样）。
3. 写 `docs/releases/<版本>.md`：Highlights / What's new（按模块）/ Lessons / Upgrade notes / Compatibility（上游版本钉表，取 `tools/upstream-pins.json`）/ Verification / Assets / Full changelog 对比链接 / 中文摘要。参考 `docs/releases/1.2.0.md`。
4. `PYTHON=<你的 python> bash tools/smoke.sh` 过。
5. 提交以上改动，`git tag <版本> && git push origin main <版本>`。

## 1. 推 tag 自动发布（推荐）

`.github/workflows/release.yml` 监听 `x.y.z` 形式的 tag：

```bash
git push origin main          # 先推分支（版本串、NOTICE、docs/releases/<版本>.md 都在这次提交里）
git tag 1.3.0 && git push origin 1.3.0   # 再单独推 tag
```

分支和 tag 不要混在一次 `git push origin main 1.3.0` 里：2026-11-02 实测这样推 1.4.0 时 GitHub 没有触发 tag 事件（Actions 页 0 次运行）。

Actions 页会出现 `release` 运行（约 3~5 分钟）：装依赖 → `tools/smoke.sh` → `tools/package-release.sh 1.3.0`（核对三处版本串与 `docs/releases/1.3.0.md` 存在）→ 取发布说明首行当标题、其余当正文 → `gh release create` 建 Release、传 zip 与 SHA256SUMS、标 Latest。

- smoke 不过或版本串不一致：不会建 Release。修好提交后把 tag 挪到新提交再推（`git tag -f 1.3.0 && git push -f origin 1.3.0`），或在 Actions 页 **Run workflow** 填 tag 重跑（手动触发按你选的分支的树打包，tag 只要求已存在；用它给已有 tag 补发或重传附件）。
- Release 已存在再跑：只更新标题 / 正文 / 覆盖附件，不会建第二个。
- 发布说明文件必须在打 tag 的那个提交里，否则 checkout 到 tag 时找不到它。

下面第 1~3 节是手动流程，workflow 挂了或想补发历史版本时用。

## 1a. 打附件（手动）

```bash
bash tools/package-release.sh 1.2.0
```

脚本会核对 tag 与三处版本串、生成 `dist/ppt-ultra-1.2.0.zip`（只含 `skills/ppt-ultra`，排除 node_modules / 缓存 / 输出）和 `dist/SHA256SUMS`。`dist/` 已在 `.gitignore`。

## 2. 在 GitHub 网页上建 Release（手动）

1. 打开 https://github.com/runnerback/PPT-Ultra/releases → 右上 **Draft a new release**。
2. **Choose a tag**：下拉里选已推送的 `1.2.0`（不要在这里新建 tag，tag 已经指在正确的提交上）。Target 保持 `main`。
3. **Release title**：填 `PPT Ultra 1.2.0 — Host contract`（与 `docs/releases/1.2.0.md` 第一行标题一致，去掉前导 `#`）。
4. **Describe this release**：把 `docs/releases/1.2.0.md` 全文粘进去，删掉第一行的大标题（标题栏已经有了）。右上可点 **Preview** 看渲染。不要点 **Generate release notes**，它只会把提交信息「feat: html and pptx」堆进来。
5. **Attach binaries**：把 `dist/ppt-ultra-1.2.0.zip` 和 `dist/SHA256SUMS` 拖进附件区，等上传进度条走完（zip 几十 MB，要等一下）。
6. 勾选 **Set as the latest release**；**Set as a pre-release** 不勾。
7. 点 **Publish release**。

发布后检查：Releases 页顶部出现 1.2.0 带 Latest 标签；README 的 version 徽章链接能落到它；附件区有 zip + SHA256SUMS + 两个 Source code 包。

## 3. 用命令行建（手动，等价）

需要 `gh auth login` 过一次：

```bash
gh release create 1.2.0 dist/ppt-ultra-1.2.0.zip dist/SHA256SUMS \
  --title "PPT Ultra 1.2.0 — Host contract" \
  --notes-file docs/releases/1.2.0.md \
  --latest
```

改正文：`gh release edit 1.2.0 --notes-file docs/releases/1.2.0.md`；补附件：`gh release upload 1.2.0 dist/xxx`。

## 4. 发完之后

- 用户侧的安装说明不用改：README「Download ZIP」仍指源码包，Release 附件是给「拖 zip 进聊天安装」那条路的更小包。
- 下一版开始前先在 NOTICE 加条目、写 `docs/releases/<新版本>.md`，流程同上。

## 常见问题

| 现象 | 处理 |
|---|---|
| 下拉里没有 1.2.0 | tag 没推：`git push origin 1.2.0` |
| 正文里的相对链接 404 | Release 正文里的链接要写成完整 URL（`https://github.com/runnerback/PPT-Ultra/blob/1.2.0/...`），不要写仓库相对路径 |
| 想改已发布的正文 / 附件 | Release 页右上 **Edit release**，正文可改、附件可删可加，tag 不动 |
| 发错了 | **Delete release** 只删 Release 不删 tag；tag 也要删才 `git push origin :refs/tags/1.2.0` |
