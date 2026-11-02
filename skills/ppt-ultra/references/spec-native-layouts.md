---
description: Spec Native engine field reference — top-level spec keys, the 31 layouts with their fields and capacity limits, chart / graph / sequence rules, image paths, style overrides.
---

# Spec Native · 规格字段参考

写规格时对照本文；写完先跑 `spec_to_pptx.py <spec> --check`，按报错逐页修。容量上限是**版面能放下的量**，不是建议值：超了会折行变密或直接报错。

## 1. 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` `subtitle` `author` `date` | title 必填 | 封面与封底元信息；`date` 缺省为当天 |
| `language` | 否 | `zh`（默认）/ `en`；只影响引擎自带文案（谢谢 / 引用出处 / 优势 / 不足 / 默认卡片标题），不影响你写的内容 |
| `style` | 否 | `{"palette": {...}, "fonts": {"cjk", "latin"}, "series_colors": [...]}`，见引擎 README §5 |
| `thanks_line` | 否 | 封底致辞一句；不给就只有「谢谢」+ 标题 / 作者 / 日期 |
| `references` | 否 | `[{"num", "title", "path"?, "changed"?, "author"?, "url"?}]`；给了就在最后追加「引用出处」页，正文里 `[n]` 自动渲染为上标角标 |
| `slides` | 是 | 页数组；第 1 页 `cover`，最后 1 页 `closing`；不要写 `thanks` / `references` 页，引擎自动追加并忽略 |

每个正文页通用字段：`layout`（必填）、`title`（除 image_bg 外必填，写判断句）、`subtitle`（可选副题）、`takeaway`（页底结论条，可选但建议每页都有）、`notes`（演讲备注）。

## 2. 版式总表

### 2.1 结构页

| layout | 字段 | 容量 |
|---|---|---|
| `cover` | `title`, `subtitle` | — |
| `section` | `title`, `subtitle` | 主色整页，章节分隔 |
| `agenda` | `items:[str]`, `current`（1 起，高亮当前章） | 3~8 项 |
| `closing` | `title`, `bullets`, `takeaway` | 总结页，算有效页 |

### 2.2 文字与数据页

| layout | 字段 | 容量 |
|---|---|---|
| `bullets` | `bullets:[str]` | 3~6 条，每条 ≤40 字 |
| `cards` | `cards:[{title, lines:[str]}]` | 2~4 张，每张 2~4 条 ≤30 字 |
| `numbers` | `numbers:[{number, caption}]`, `bullets?` | 2~5 个数字卡；caption 写口径 |
| `table` | `table:{rows:[[str]]}`（首行表头） | ≤7 行 × ≤5 列，单元格 ≤20 字 |
| `chart` | `chart:{…}` 或 `charts:[chart, chart]`, `bullets?` | 一页 1~2 张；见 §3 |
| `kpi` | `numbers:[2~4]` + `chart` | 数字卡在上、图表在下 |
| `quote` | `quote`, `source?`, `bullets?` | 原话原样引用；bullets ≤2 条 |
| `compare` | `left:{title, lines}`, `right:{title, lines}` | 各 1~6 条 |
| `pros_cons` | `pros:[str]`, `cons:[str]`, `pros_title?`, `cons_title?` | 各 1~6 条；默认标题 优势 / 不足 |
| `matrix` | `axes:{x, y}?`, `quadrants:[{title, items}]` | 正好 4 格（左上 右上 左下 右下），每格 ≤5 条 |
| `icons` | `items:[{icon, title, lines}]` | 2~4 张；`icon` 见 §5 |

### 2.3 流程与结构图（坐标程序算）

| layout | 字段 | 容量 |
|---|---|---|
| `flow` | `graph:{direction:"LR"\|"TB", nodes:[{id, text, shape?, emph?}], edges:[{from, to, label?, style?, arrow?}]}`, `caption?`, `bullets?` | 节点 ≤14、边 ≤20；见 §4 |
| `swimlane` | 同上，加 `graph.lanes:[str]`，每个节点必填 `lane` | 泳道 1~5 条 |
| `sequence` | `sequence:{participants:[str], messages:[{from, to, text, kind?}]}`, `caption?`, `bullets?` | 参与者 2~6，消息 1~12 |
| `hierarchy` | `tree:{nodes:[{id, text, parent:""\|id, emph?}]}`, `caption?`, `bullets?` | ≤14 节点，必须有根（parent 为空） |
| `timeline` | `milestones:[{date, text, status:"done"\|"doing"\|"todo"}]` | 3~8 个 |
| `layers` | `layers:[{name, items:[str]}]` | 2~5 层，每层 1~6 项 ≤10 字 |
| `cycle` | `steps:[str]`, `center?`, `bullets?` | 3~6 步 ≤10 字 |
| `funnel` | `stages:[{label, value?}]`, `bullets?` | 3~6 层 |
| `diagram` | `diagram:{bounds, nodes, edges}`（已算好坐标的图示规格，供外部工具 / 白板导出直接喂入） | 单位英寸，整体等比缩放进内容区 |

图示页都可配 `caption`（图注一句）和 2~4 条 `bullets`（放右侧；横长的图自动改放图下）。

### 2.4 图片与厂商页

| layout | 字段 | 容量 |
|---|---|---|
| `image` | `image:路径`, `caption?`, `bullets?` | 等比缩放居中；有 bullets 时图占左 62% |
| `image_split` | `image`, `side:"left"\|"right"`, `ratio:0.4\|0.5\|0.6`, `bullets`（必填）, `caption?` | 图文页 |
| `image_grid` | `images:[{image, caption?}]`, `bullets?` | 2 张 2×1、3 张 3×1、4 张 2×2 |
| `image_callout` | `image`, `markers:[{x:0~1, y:0~1, text}]`, `caption?` | 1~5 个标注，坐标为图内相对位置 |
| `image_bg` | `image`, `title`, `subtitle?` | 整页：大图铺底 + 半透明主色块 + 大字；不画标准标题 |
| `vendors` | `vendors:[{name, logo?:路径, lines:[str]}]` | 2~4 家；没 logo 画名称标牌 |
| `logo_table` | `table:{rows}`（首列厂商名）, `logos?:{厂商名: 路径}` | 2~7 行 ≤5 列 |

图片路径：绝对路径原样用；相对路径相对 **spec 文件所在目录**。文件不存在直接报错。

## 3. 图表规则

```json
"chart": { "type": "bar|bar_stacked|column|column_stacked|line|area|pie|doughnut|radar",
           "title": "图题（带单位）", "categories": ["A", "B"],
           "series": [{ "name": "系列名（含单位）", "values": [1, 2] }],
           "max": 100, "highlight": [4], "number_format": "0.0" }
```

- 只在有**真实、可比**的数值时用图表（3~8 个类别，数值互不相同）；全相同的数值被判为示意值直接报错。没有数字就改用 table / cards / bullets。
- 类型按数据选：对比排名 `bar` / `column`，构成 `column_stacked` / `pie` / `doughnut`（后两者只允许 1 个系列），趋势 `line` / `area`（多系列各一条线），多维能力对比 `radar`。
- `highlight` 只对单系列 bar / column 生效（把指定类别标红）；`max` 固定值轴上限；雷达图不放数据标签。
- 一页最多 2 张（`charts` 数组并排）；整份建议 ≤3 页图表。

## 4. 流程 / 泳道 / 时序的限制

- 节点 `shape`：`rect` `round`（默认）`diamond`（判断）`pill`（起止）`circle`；`emph:true` 用主色填充。
- 边：`label`（判断分支的两条出边都要带）、`style:"dashed"`、`arrow:"end"|"both"|"none"`；`from` / `to` 必须是已定义的 id，不能自指。
- 宽度按字形估算：节点文字约 ≤15 个汉字宽、边标签约 ≤11 个汉字宽、参与者约 ≤9 个汉字宽、消息约 ≤14 个汉字宽（英文字母按 0.55 个汉字计）。
- 时序消息 `kind`：`sync`（实线主色）`async`（实线灰）`return`（虚线灰）；按时间顺序写。
- `flow` / `swimlane` / `hierarchy` 需要系统里有 Graphviz `dot`；没有会报「未安装 Graphviz」。

## 5. 图标名（`icons` 版式）

`star bolt heart gear cloud sun moon warning stop plus minus equal multiply arrow_right arrow_up arrow_down arrow_left arrows cube donut pie document database smile chat diamond hexagon chevron wave drop octagon pentagon cycle target block flag decision`

## 6. 出处角标

任何文本字段（bullets、cards.lines、table 单元格、numbers.caption、takeaway、chart.title）里出现 `[n]` 或 `[2][5]`、`[2, 5]` 都会渲染为上标灰色小字；`n` 要能在 `references` 里找到。没有出处的内容不要编号。角标是上标小字，单独一个 `[1]` 放在表格单元格里会小到看不清：表格的「来源」列写成 `BI 看板 [1]` 这样带一个词，或直接写资料简称。
