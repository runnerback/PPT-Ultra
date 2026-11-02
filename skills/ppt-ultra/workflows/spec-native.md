---
description: Generate PPTX — Spec profile. Deterministic native .pptx from one spec JSON (engines/spec-native): the agent writes semantics per page, the engine computes layout. No SVG authoring, no Confirm UI, no spec_lock; iterate by editing the JSON.
---

# Generate PPTX · Spec Profile（规格驱动的确定性 PPTX）

> 来源：本引擎为 PPT Ultra 1.1.0 新增（Runnerback，MIT），从一条在企业内跑了两个月的「智驾 Agent 制作 PPT」管线抽出。它不是 ppt-master 的 SVG 路线，也不读 `${SKILL_DIR}/scripts/`；选中本 profile 后**不要**加载 `generate-pptx.md`、`quick-generate.md` 或任何 Native 路线文档，也不跑 PPTX 引擎完整性检查。

**路径约定**：引擎根目录 = `${SKILL_DIR}/engines/spec-native`，CLI = `${SKILL_DIR}/engines/spec-native/spec_to_pptx.py`。产物写到调用方工作目录下的 `<deck-output-dir>/`（`spec.json`、`<名字>.pptx`、`images/`），绝不写进 `${SKILL_DIR}`。

**何时选它**（由 [`routing.md`](./routing.md) §3 / §8 判定）：用户明确要规格 / 确定性 / JSON 驱动；或内容是表格、多张图表、流程 / 泳道 / 时序这类数据密集的常规汇报而不要求设计师级版面；或宿主是非交互环境、不具备逐页 SVG 创作能力但明确要 .pptx。要「设计感」请回到 Default / Quick。

---

## 1. Plan → Do·Check·Act 一轮

| 阶段 | 步骤 |
|---|---|
| Plan | §2 素材 → §3 大纲 |
| Do·Check·Act | §4 写规格 → §5 校验循环 → §6 生成 → §7 验收与交付 |

交互环境下只有一个可选确认点（§3 大纲）；非交互 / 委托时全程不停。

## 2. 素材准备

| 输入 | 动作 |
|---|---|
| PDF / DOCX / PPTX / XLSX / 网页 | 共享服务 `python3 "${SKILL_DIR}/scripts/source_to_md.py" <file\|url> -o <deck-output-dir>/sources/`，之后只读转换出的 `.md`（该脚本带 ppt-master 的完整性检查，退出码 78 时按 [`shared-services.md`](../references/shared-services.md) 降级直接读原文件） |
| Markdown / 对话文字 / CSV | 直接读 |
| 只有主题、或素材缺关键事实 | [`topic-research`](./stages/topic-research.md) 只查缺口，结论写 `<deck-output-dir>/sources/research.md`，每条带来源；这些来源就是规格里 `references` 的条目 |
| 用户给的图片 | 复制到 `<deck-output-dir>/images/`，规格里用相对路径 `images/<文件名>` |

读完素材先列**事实清单**（每条：事实 + 数字 + 口径 + 来源编号），后面写页只准从这张清单取内容。

## 3. 大纲（可选确认点）

1. 选叙事模式（[`modes/_index.md`](../references/modes/_index.md) 五种之一）；汇报类默认 `pyramid`，复盘 / 现状类用 `briefing`。
2. 定有效页数：用户说了就照办；没说按素材量 5~12 页。页数口径见 [`spec-native-content-rules.md`](../references/spec-native-content-rules.md) §6。
3. 写页规划：每页一行「layout ｜ 判断句标题 ｜ 这页回答什么 ｜ 用到的事实编号」。版式按内容形态选（content-rules §5），连续 3 页不同 layout，≥8 页时至少 1 页 `section`。
4. **交互环境**：把页规划贴给用户确认一次（标题 / 页数 / 版式），用户改了按改后的继续。**委托或非交互**：不确认，直接进 §4，并在最终说明里列出假设。

## 4. 写规格 JSON

按 [`spec-native-layouts.md`](../references/spec-native-layouts.md) 的字段与容量写 `<deck-output-dir>/spec.json`。逐条对照 [`spec-native-content-rules.md`](../references/spec-native-content-rules.md)：判断句标题、每页 takeaway、不写空话、数字带口径与基线、图表只用真实可比数值、取自资料的内容带 `[n]` 角标并在顶层 `references` 登记来源。

- 第 1 页 `cover`、最后 1 页 `closing`；封底与引用出处页由引擎自动追加，不要写。
- 用户给了风格要求（品牌色、杂志风 / 瑞士风 / T 主题的配色）：填顶层 `style.palette` / `fonts`，不要去改引擎文件。
- 英文 deck 设 `"language": "en"`。
- 画流程 / 泳道 / 时序前先检查 Graphviz：`dot -V`；没有就改用 `layers` / `timeline` / `table` 表达，并在说明里写明。

## 5. 校验循环

```bash
python3 "${SKILL_DIR}/engines/spec-native/spec_to_pptx.py" <deck-output-dir>/spec.json --check
```

返回 `{"ok": false, "error": "第 N 页 …"}` 就按页改规格再跑；**最多 3 轮**，仍不过标记「阻塞」并把错误原文交给用户。常见错误与改法：

| 错误 | 改法 |
|---|---|
| 图表数值没有区分度 | 不是真实数据，改成 table / bullets，不要凑数 |
| 节点 / 标签太宽 | 缩短文字，或拆成两个节点 |
| 未知版式 / 缺字段 | 对照 layouts 文档改字段名 |
| 图片文件不存在 | 检查相对路径是否相对 spec 所在目录 |
| 未安装 Graphviz | 装 `dot`，或换非图示版式 |

## 6. 生成

```bash
python3 "${SKILL_DIR}/engines/spec-native/spec_to_pptx.py" <deck-output-dir>/spec.json <deck-output-dir>/<deck-name>.pptx
```

stdout 的 JSON 给出总页数与图表数；与页规划对不上（例如少了一页）先查规格再交付。

## 7. 验收与交付

按 [`shared-services.md`](../references/shared-services.md) 的统一验收：状态只有 **通过 / 待修正 / 阻塞**，最多 2 轮返工。

1. 逐项核对 intake brief：route / deliverable / size / language / constraints 全部落实；页数 = 封面 + 有效页 + 封底（+ 引用出处页）。
2. 有渲染能力时抽查版面：`soffice --headless --convert-to pdf <deck>.pptx`（Linux / macOS 装了 LibreOffice）或 PowerPoint 打开；重点看表格是否溢出、图示文字是否过小、角标是否渲染为上标。没有渲染能力时**不得声称已做视觉验收**，只报告结构校验结果。
3. 交付说明：页数、用了哪些图表 / 图示、哪些数字没有出处或缺口径、非交互时做了哪些假设。规格文件一并交付。

**迭代**：用户的修改意见落到 `spec.json`（改那一页的字段、增删页、换 layout），重跑 §5 → §6。规格是唯一真源，不要手改 pptx 再反推。

---

## 硬规则

- **Spec 不与 SVG 路线混用**：一份 deck 要么全走本 profile，要么全走 Default / Quick；不要在本 profile 里调用 `svg_to_pptx.py`、`project_manager.py` 等 Native 引擎脚本。
- **不改引擎**：`engines/spec-native/*.py` 是引擎本体；风格用 `style`，内容用规格，缺的版式如实告知用户而不是临时改代码。
- **不编数据**：引擎会拒绝全相同数值的图表，但不会识别编造的差异数值；所有数字都要能回到 §2 的事实清单。
- **非交互**：缺的信息按 [`intake.md`](./intake.md) §3 默认值决定，并在交付说明里全部列出。
