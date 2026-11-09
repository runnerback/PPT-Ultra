# Spec Native engine · 规格驱动的确定性原生 PPTX

> **版本**: 1.0.0 | **更新时间**: 2026-11-02 | 许可证 MIT（见本目录 `LICENSE`）
> Deterministic native .pptx from a semantic spec JSON: the model writes *what* goes on each page, the engine computes every coordinate. 31 layouts, 9 native chart types, Graphviz-laid flow / swimlane / hierarchy diagrams, citation superscripts with an auto-generated references page. One command, seconds to build, rebuild by editing the JSON.

## 1. 这是什么

把一份**规格 JSON**（每页一个 `layout` 加该版式的内容字段）变成一份**原生可编辑的 .pptx**。与 PPT-Ultra 的 SVG 路线（模型逐页画 SVG）不同，这里：

- **模型只出语义，坐标全由程序算**：卡片几列、表格行高、图表与要点如何分栏、流程图节点怎么摆，都在引擎里按内容量决定。
- **确定性**：同一份规格永远得到同一份 PPT；不要 Confirm UI、不要阻塞闸门，一次调用秒级出片，适合非交互宿主、批量生成、低算力模型。
- **校验失败即抛错**：缺字段、未知版式、图表数值没有区分度（假数据）、节点文字过宽，都按页报错，不做兜底页；照错误改规格重跑。
- **全部原生对象**：文本框、形状、表格、图表都能在 PowerPoint / WPS / 飞书里继续改；每个形状带语义化 name（`card2.body`、`chart1`、`flow3.n4`），便于程序回读改稿。
- **证据纪律**：正文里的 `[n]` 自动渲染成上标角标，`references` 给了就在末尾加「引用出处」页。

它填的是另外三条路线的空白：**大段表格、多张图表、流程 / 泳道 / 时序这类数据密集的常规汇报**，以及没有浏览器、不能多轮确认的运行环境。

## 2. 依赖

| 依赖 | 用途 | 安装 |
|---|---|---|
| Python 3.10 – 3.14 | 运行 | — |
| `python-pptx>=1.0` `Pillow` `lxml` | 生成 pptx、读图片尺寸、补 OOXML 细节 | 根目录 `pip install -r requirements.txt` 已含 |
| Graphviz `dot`（系统包，可选） | `flow` / `swimlane` / `hierarchy` 三种版式的自动布局 | macOS `brew install graphviz`；Ubuntu `apt install graphviz`；Windows 官方安装包并加入 PATH。不装也能用其它 28 种版式 |

不依赖 ppt-master 引擎的任何脚本，不读 `${SKILL_DIR}/scripts/`，不触发其完整性检查。

## 3. 用法

```bash
# 生成
python3 "${SKILL_DIR}/engines/spec-native/spec_to_pptx.py" deck/spec.json deck/deck.pptx
# 只校验（完整构建到临时文件后丢弃；报错即规格有问题）
python3 "${SKILL_DIR}/engines/spec-native/spec_to_pptx.py" deck/spec.json --check
# 列出版式 / 图表类型 / 图标名
python3 "${SKILL_DIR}/engines/spec-native/spec_to_pptx.py" --layouts
```

stdout 一行 JSON：成功 `{"ok": true, "slides": 12, "charts": 3, "out": "..."}`；失败 `{"ok": false, "error": "第 7 页图表数值没有区分度（[1.0, 1.0]）…"}` 且退出码 1。图片 / logo 的相对路径相对 spec 文件所在目录。

示例（`examples/`，都能直接构建）：

| 文件 | 覆盖 |
|---|---|
| `01-basic.json` | cover / agenda / section / bullets / cards / numbers / table / chart / closing |
| `02-charts.json` | 9 种图表、双系列、堆积、并排双图、kpi |
| `03-diagrams.json` | flow / swimlane / sequence / hierarchy / timeline / layers / cycle / funnel / compare / pros_cons / matrix / quote / icons |
| `04-evidence-en.json` | `language: en`、`style` 整体换色换字体、`[n]` 角标与自动引用出处页 |
| `05-images.json` | image / image_split / image_grid / image_callout / image_bg / vendors / logo_table（相对路径图片）；`page_numbers: false` 无页码 |

## 4. 规格速览

```json
{
  "title": "PPT 标题", "subtitle": "一句定位", "author": "制作人", "date": "2026-11-02",
  "language": "zh",
  "style": { "palette": { "primary": "003F8F" }, "fonts": { "cjk": "微软雅黑", "latin": "Arial" }, "series_colors": ["003F8F", "C00000"] },
  "thanks_line": "可选：封底致辞一句",
  "page_numbers": true,
  "references": [ { "num": 1, "title": "资料标题", "path": "位置", "changed": "2026-10-01", "author": "作者", "url": "https://…" } ],
  "slides": [
    { "layout": "cover", "title": "…", "subtitle": "…" },
    { "layout": "bullets", "title": "判断句标题", "bullets": ["要点 [1]", "…"], "takeaway": "页底结论条", "notes": "演讲备注" },
    { "layout": "closing", "title": "总结", "bullets": ["…"], "takeaway": "…" }
  ]
}
```

- 第 1 页用 `cover`，最后 1 页用 `closing`；封底「谢谢」页由引擎追加，不要写进 slides。
- 每个正文页都可带 `takeaway`（页底主色结论条）和 `notes`（演讲备注）。
- 31 种版式与每种的字段、容量上限见 [`../../references/spec-native-layouts.md`](../../references/spec-native-layouts.md)；写内容的规则见 [`../../references/spec-native-content-rules.md`](../../references/spec-native-content-rules.md)。

## 5. 设计系统与风格覆盖

默认「科研答辩风」：白底、深学术蓝 `003F8F` 结构色、正红 `C00000` 强调、浅蓝面板、细灰边框、页底深蓝结论条，字体微软雅黑 + Arial（Windows 原样显示，macOS 自动代换）。`style` 可整体覆盖：

| 键 | 说明 |
|---|---|
| `palette` | 任意子集：`primary secondary pale red ink gray mid border fill white bg gold`；拼错的键直接报错 |
| `fonts` | `cjk`（东亚字体）/ `latin`（西文字体） |
| `series_colors` | 图表系列色序，至少 2 个 |

跨引擎的 style brief（杂志风 / 瑞士风 / T01–T12 的配色）就是通过这里落地的：把选定配色的主色、强调色、底色填进 `palette` 即可。

## 6. 引擎内已固化的 python-pptx 兼容性修正

这些都是在 PowerPoint / Open XML SDK 校验器 / 飞书在线预览上踩过的坑，引擎自动处理，规格作者不用关心：

- 图表 `c:axId` / `c:crossAx` 负数改正数（schema 要求 UInt32）；雷达图 `c:ser` 里的 `c:smooth` 删除。
- `dLblPos` 只在 pie / bar / column / line 上写；doughnut / area / radar 的 OOXML 不允许，写了 PowerPoint 会要求修复并丢页。
- 图表内全部文字显式写 latin / ea / cs 字体，否则不做主题回退的在线预览会把中文渲染成乱码。
- 连接线箭头 `a:headEnd` 必须排在 `a:tailEnd` 之前（schema 顺序），双向箭头按此插入。
- 表格关掉默认样式条纹，首行 / 斑马纹自己上色，避免主题差异。
- 图片一律等比缩放，`image_bg` 用 crop 铺满而不是拉伸。

## 7. 边界

- 不做 Master / Layout / 占位符结构；输出是 `flat` 的 Slide-local 对象。要套公司模板母版，走 Create Template + Generate PPTX（SVG 路线）或 Edit Native PPTX。
- 版面是固定设计系统下的自动排布，不是逐页定制的设计师版面；要「设计师级」视觉请走 Generate PPTX 的 Default / Quick。
- 文字容量靠规格侧约束（见 layouts 文档的上限），引擎只在图示类版式按字形宽度校验；要点写太长会折行变密，不会报错。

## 8. 来源

本引擎从 Runnerback 在企业内部 Agent 制作 PPT 管线里跑了两个月的生成器抽出，去掉了企业依赖（IM 平台 / 内部知识库 / 模型网关）与企业数据，作为 PPT-Ultra 的第四引擎开源，MIT 许可。
