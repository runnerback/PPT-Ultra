---
description: Host Editorial profile — Generate HTML Deck (Editorial engine) driven by a machine-written host brief: family / theme / pages fixed by the host, single-file index.html with presenter notes, no questions, no servers, manifest at the end.
---

# Host Editorial Profile（宿主驱动的网页 deck）

> Generate HTML Deck · Editorial 的宿主版。**进入条件**：用户消息来自 `host/build_prompt.py` 且交付格式为 html（开头写着「宿主契约 v1，交付 HTML」）。与 [`host-quick.md`](./host-quick.md) 同一套宿主契约：决定权在 brief，agent 只负责按材料写页面、过校验、交回产物清单。引擎本体与规则仍是 [`../html-editorial.md`](../html-editorial.md)，本文件只说明宿主模式下哪些步骤跳过、哪些必须做。
>
> 版本：PPT Ultra 1.2.0（2026-11-02，Runnerback）。

## 1. 与交互式 Editorial 的差别

| 项 | 交互式（html-editorial.md） | Host Editorial |
|---|---|---|
| Step 1 需求澄清 | 问用户 | **跳过**：标题 / 页数 / 风格族 / 主题 / 备注都在 brief |
| 风格与主题 | 推荐或问 | brief.html.family + theme（或 brand_color → `gz-theme.mjs brand`） |
| 配图 | 可生图 / 搜图 | 只用 brief.images；没有就零图片（排版 + 色块 + 原生 CSS 图表） |
| Step 5 本地预览 | 打开浏览器 | **不做**，不起任何服务 |
| 结束 | 汇报路径 | 复制单文件产物 → `collect_manifest.py` → 一行 JSON |
| 改稿 | 对话里改 | brief.revision，在 WORK/deck/index.html 上改 |

**Hard rule — paths**：`${SKILL_DIR}` 换成 brief 给的 skill_dir；deck 写在 `<WORK>/deck/index.html`；命令 `cd "<WORK>" && …`。

## 2. 读什么

```
${SKILL_DIR}/workflows/html-editorial.md                          # 引擎规则全文（Step 2~4、设计原则）
${SKILL_DIR}/engines/html-editorial/assets/template(-swiss).html  # 选定风格的模板，至少读到 <style> 末尾（类名唯一来源）
${SKILL_DIR}/engines/html-editorial/references/layouts(-swiss).md # 版式骨架与主题节奏规则
${SKILL_DIR}/engines/html-editorial/references/themes(-swiss).md  # 主题 id 与颜色变量
```

**不读**：`intake.md`、`routing.md`、任何 Native 路线文档、`html-themed.md`、image-prompts / screenshot-framing（brief 没给图就用不到）。

## 3. 步骤

1. `mkdir -p "<WORK>/deck/images"`，按 brief.html.family 拷模板到 `<WORK>/deck/index.html`。
2. 改 `<title>`；主题：`theme` 是内置 id 就改 `<html data-theme>`；是 `brand` 就跑 `gz-theme.mjs brand "<brand_color>" --family <family>`，输出贴进 `<style>` 末尾并把 `data-theme` 设为 `brand`（脚本判不达标 → 改用该风格默认预设，记进日志）。
3. **主题节奏**：先按 roster 列出每页的 `light / dark / hero light / hero dark`（html-editorial.md §3.0.5 的硬规则：连续同主题 ≤ 2、8 页以上至少一个 hero dark 和一个 hero light、不能只有 light 正文页），写进日志。
4. 按 roster 逐页写 `<section class="slide …">`：只用模板里存在的类与颜色变量（先对照 layouts 的 Pre-flight 列表），数字只来自材料，`must_keep` 原样、`must_avoid` / `forbidden_strings` 不出现；页数严格等于 `pages.total`；`constraints.page_numbers=false` 时每页 `.chrome` 右侧不放 `NN / TOTAL`（模板 / checklist 要求 chrome 放页码的条目不用），`collect_manifest.py` 复核命中 ok=false。
   - **深色页（`dark` / `accent`）不放 `.card-fill` 灰底卡**：灰底卡的文字色跟随页面文字变量，深色页上变成浅字浅底、整卡不可读（宿主基准 2026-11-02 实测一页四卡全盲）。卡片网格放浅色页；深色页用 `.duo-compare` / `.timeline-*` / `.card-ink` 这类随页面取色的组件。
5. brief.html.speaker_notes 为 true 时写 `SPEAKER_NOTES`：每页一条、与页面 id 一一对应、口语化。
6. 校验：`grep -c "\[必填\]" deck/index.html` 为 0；有 node 时跑 `node ${SKILL_DIR}/engines/html-editorial/scripts/validate-presenter-mode.mjs deck/index.html [--target-minutes N]`，瑞士风再跑 `validate-swiss-deck.mjs deck/index.html`；报错就修，连续 3 轮仍过不去把剩余项记进日志继续。
7. 产物：把 `deck/index.html` 复制为 `<WORK>/<output.html_name>`。有 images/ 时优先把图片内联成 data URI（单文件可直接发给别人），做不到就在日志写明 images 目录要随文件一起交付。
8. 收尾：写 `<WORK>/<output.log_name>`；跑 `python ${SKILL_DIR}/host/collect_manifest.py "<WORK>" --brief "<WORK>/brief.json" -o "<WORK>/<output.manifest_name>"`；最后一条回复只写一行 JSON `{"ok": …, "manifest": "…", "note": "…"}`。

## 4. 改稿（brief.revision）

在 `<WORK>/deck/index.html` 上改对应 `<section>`；增删页同步页序与 `SPEAKER_NOTES`；重跑第 6~8 步。

## 5. 宿主侧约定

- 运行时：bash + 文件读写；node 有则校验器可跑（Playwright 不是必需，没有就只做静态检查）；不需要网络。
- 交付：单个 `.html`（模板引用 Google Fonts / unpkg / jsdelivr 三个 CDN，观众机器离线时字体与图标回退但页面可用）。
- 产物只信 `manifest.json`：`deck.slides`（`<section class="slide` 计数）、`deck.placeholders`（残留 `[必填]` 数，必须 0）、`deck.notes`（SPEAKER_NOTES 条数）、`deck.dark_card_fill`（深色页上的灰底卡数，应为 0）、`validators`（校验器退出码与尾行）、`forbidden_hits`、`page_number_hits`（`constraints.page_numbers=false` 时每页「NN / TOTAL」命中，有命中 ok=false）。
