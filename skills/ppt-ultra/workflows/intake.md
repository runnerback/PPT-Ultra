---
description: Unified Stage 0 for every PPT Ultra request — resolve the route and engine profile, pick the style from the unified catalog, and hand an intake brief to the selected runtime.
---

# Unified Intake (Stage 0)

每个请求都先经过本阶段，然后才进入某一条路由。本阶段只做三件事：**定路由 → 定风格族 → 写 intake brief**。它不做素材转换、不建项目、不写页面；这些归所选 runtime 负责（遵守 SKILL.md 的 *No speculative execution*）。

**Hard rule — 只问缺的**：从用户原话、附件和上下文能确定的字段直接填，不再提问。只有路由判别问题（Q1）和 HTML 风格问题（Q2）属于本阶段；其余问题留给所选 runtime 自己的确认环节（PPTX Default 的 Stage 1 Confirm UI、editorial 的 Step 1、themed 的"开工前确认"）。不要在这里先问一遍，进入 runtime 后又问一遍。

---

## 1. 路由判别（Q1）

按 [`routing.md`](./routing.md) §2 和 §8 判断。判断不出来时，只问一个问题，把交付格式和使用场景合在一起问：

> 这份 PPT 主要怎么用？
> ① **现场演讲 / 投屏分享**：网页 PPT，带演讲者视图、提词和计时（HTML · Editorial）
> ② **汇报 / 报告 / 方案**：网页 PPT，12 套主题，每页给 4 个方案挑选，可导出 PDF（HTML · Themed）
> ③ **要交付可编辑的 .pptx**：原生 PowerPoint 对象，可套模板、母版，后续可加旁白或视频（Native PPTX）

能看出倾向时，把推荐项放在第一位并标"推荐"。

| 用户信号 | 直接判定（不提问） |
|---|---|
| `PPTX` / `PowerPoint` / 可编辑 / 母版 / 套我们公司模板 / 给了 `.pptx` 要修改或美化 / 做模板 / 旁白 / 自动播放视频 | ③ Native PPTX 系路由（具体是哪条路由由 routing.md §2–§5 决定） |
| 网页 / HTML / 浏览器打开 / 演讲者模式 / 提词 / 计时 / 观众屏 / 杂志风 / 瑞士风 / Swiss | ① Editorial |
| `theme01`–`theme12`、点名某个 Themed 主题 / 想先看几个方案再挑 / 要 HTML 同时要 PDF | ② Themed |
| 「规格 / spec / JSON 驱动」、要确定性可复现、或大段表格 + 多张图表 + 流程图的常规汇报且不要求设计师级版面，交付 .pptx | ③ Native PPTX · Spec profile（[`spec-native.md`](./spec-native.md)） |
| 只说"做个 PPT"，看不出场景 | 问 Q1 |
| 无法提问（脚本 / 批处理 / 用户已全权委托） | 按 §3 的非交互默认值 |

## 2. 风格族（Q2 · 仅 HTML 路由）

PPTX 路由不在这里问风格：免费设计、模板库、视觉风格统一由 PPTX Default 的 Stage 1 一次确认（Quick 则自行决定）。

HTML 路由从统一风格目录里选，选定的风格同时决定用哪个引擎：

| 风格 ID | 名称 | 引擎 / 配色 | 适合 |
|---|---|---|---|
| `E-mag` | 电子杂志 × 电子墨水 | Editorial · 5 套配色（`ink-classic` `indigo-porcelain` `forest-ink` `kraft-paper` `dune`）或品牌色 | 人文、行业观察、故事、商业发布 |
| `E-swiss` | 瑞士国际主义 | Editorial · 4 套配色（`ikb` `lemon` `lemon-green` `safety-orange`）或品牌色 | 科技产品、数据汇报、工程设计分享、年度总结 |
| `T01`–`T12` | Dashi 12 主题 | Themed · `theme01`–`theme12`（清单及"适合/人群"见 [`html-themed.md`](./html-themed.md)） | 产品、企业汇报、数据、调研、品牌、增长等 |

- 已经判到 ① 但没定风格：问 A/B，顺带一句推荐理由（参考 [`html-editorial.md`](./html-editorial.md) "风格选择参考"）。
- 已经判到 ② 但没定风格：按 themed 引擎的规则展示风格图，再列主题清单。
- 用户只描述了感觉（"科技感""高级""年轻"）：给 2–3 个跨引擎候选，每个标明引擎和能力差异，例如 `E-swiss` 带演讲者模式，`T02` 带多方案挑选和 PDF 导出；要 .pptx 则只能走 ③。

### 2.1 跨格式风格映射

用户要的风格和格式不在同一个引擎里时，按下表转换，不要拒绝，也不要悄悄换风格：

| 想要 | 实际走法 |
|---|---|
| `E-mag` / `E-swiss` 的观感，但要交付 .pptx | 走 Native PPTX Generate。在 Stage 1 把风格作为 **style brief**（不是模板）提出：`E-mag` 对应 `references/visual-styles/editorial.md`，`E-swiss` 对应 `references/visual-styles/swiss-minimal.md`；配色从 `engines/html-editorial/references/themes.md` / `themes-swiss.md` 里所选配色的 token 取值。用户仍需在 Stage 1 确认 |
| `T01`–`T12` 的观感，要交付 .pptx | 走 Native PPTX Generate，把主题作为 style brief 提出：主题名、"适合/人群"描述，加上从 `engines/html-themed/assets/skill/theme-style-grid.png` 中该主题读到的主色和明暗基调；用户仍需在 Stage 1 确认。Themed 引擎本身不导出 PPTX |
| 已有 .pptx，想变成网页 PPT 去演讲 | 把 .pptx 当素材：走 HTML 路由，用共享服务里的 `source_to_md` 把 PPTX 转成 Markdown |
| 一份内容同时要网页版和 .pptx | 分两次交付：HTML 路由（Editorial 或 Themed）一次，Native PPTX 一次；两次共用同一个 intake brief 和转换好的素材 Markdown，不重复调研 |

## 3. 委托与非交互默认值

| 情形 | 默认 |
|---|---|
| 用户整体委托（"都你定""直接开干"） | 自行定路由和风格，在最终交付说明里列出全部假设 |
| 只说内容"随意 / 自拟" | 只自拟内容；格式、风格、页数这类用户没给的，照常按 Q1/Q2 提问 |
| 非交互且格式未知 | ② Themed，按其非交互规则执行（交付 HTML） |
| 非交互且明确要 PPTX | Native PPTX 的 Quick profile（Default 有阻塞闸门，非交互环境走不通） |
| 非交互且明确要 PPTX，且内容以表格 / 数字 / 流程为主，或宿主声明不具备逐页 SVG 创作能力 | Native PPTX 的 Spec profile（[`spec-native.md`](./spec-native.md)）：一份规格 JSON 一次成片，无任何闸门 |

## 4. Intake Brief（交接契约）

路由和风格定下来后，在对话里输出下面这份 brief，交给所选 runtime。HTML 路由同时写到 `<deck-output-dir>/intake_brief.md`；PPTX 路由在 Step 2 初始化项目后，再把 brief 放进项目目录。

```markdown
## Intake Brief
- route: generate-html-deck | generate-pptx | create-template | edit-native-pptx
- profile: editorial | themed | default | quick | spec | beautify | image-to-pptx | —
- deliverable: html | html+pdf | pptx | pptx+mp4 | template-workspace（同时要 HTML 和 .pptx 时写两份 brief）
- style: E-mag:<配色> | E-swiss:<配色> | T01..T12 | pptx-stage1 | brief:<描述>
- scenario / audience: <现场演讲 · 内部汇报 · 发布会 …> / <受众>
- size: <页数，或时长分钟数（15 分钟约 10 页，30 分钟约 20 页）>
- language: <deck 语言，跟随用户>
- sources: <用户给的文件 / URL / 大纲；未转换>
- media: none | provided:<路径> | generate:<n> | reserve-slots
- narrative_mode: pyramid | narrative | instructional | showcase | briefing | undecided
- constraints: <必含 / 禁止 / 品牌色 / 截止要求>
- delegation: interactive | delegated | non-interactive
- unresolved: <留给 runtime 确认环节去问的问题>
```

`narrative_mode` 沿用 [`../references/modes/_index.md`](../references/modes/_index.md) 的五种模式。HTML 路由用它搭大纲骨架，例如 editorial 的"钩子→定调→主体→转折→收束"就是 `narrative`。PPTX Default 把它作为 Stage 1 的候选值，仍需用户确认。

## 5. 交接

| route / profile | 下一步读取 |
|---|---|
| generate-html-deck / editorial | [`html-editorial.md`](./html-editorial.md) |
| generate-html-deck / themed | [`html-themed.md`](./html-themed.md) |
| generate-pptx / spec | [`spec-native.md`](./spec-native.md)（不跑 PPTX 引擎完整性检查，不读 generate-pptx / quick-generate） |
| 其余 PPTX 系路由 | 先跑 SKILL.md 规定的 PPTX 引擎完整性检查，再读 SKILL.md 路由表里对应的 runtime authority |

交接后只读所选 runtime 及它自己触发的文档；不要再加载其他路由的流程文件。
