---
description: Host Quick profile — Generate PPTX run driven by a machine-written host brief (bot / pipeline / script): decisions pre-resolved by the host, trimmed reading list, no questions, no servers, deterministic manifest at the end.
---

# Host Quick Profile（宿主驱动的 Quick）

> Generate PPTX 的 profile，不是独立路由。**进入条件**：用户消息来自 `host/build_prompt.py`（开头写着「宿主契约 v1」），或 WORK 下有 `host-brief.json`。它是 [`quick-generate.md`](./quick-generate.md) 的宿主版：Quick 把「不问人、自己定」交给 agent，Host Quick 把这些决定收回宿主——路由、页数、风格、字体、约束都在 brief 里写死，agent 只负责按材料写页面、过门禁、导出，并把产物清单交回程序。
>
> 版本：PPT Ultra 1.2.0（2026-11-02，Runnerback）。契约文件：[`host/brief.schema.json`](../../host/brief.schema.json)、[`host/build_prompt.py`](../../host/build_prompt.py)、[`host/collect_manifest.py`](../../host/collect_manifest.py)、说明 [`host/README.md`](../../host/README.md)。

## 1. 与 Quick 的差别

| 项 | Quick | Host Quick |
|---|---|---|
| 谁定路由 / 风格 / 字体 / 页数 | agent | 宿主（brief），agent 不得改 |
| intake / routing | 读 | **不读**（路由已定），SKILL.md 之后直接读本文件 |
| 规划批文档 | 全部索引 + 词汇表 | 精简核心包（§2），索引类不读 |
| 素材 | 任何来源，可调研 | 只用 brief 列出的材料；`web_research=false` 时不联网 |
| 图片 | 可生图 / 搜图 | 默认零图片；只用 brief 给的图片 |
| 提问 / 等待 | 不问 | 不问，也没有人会回答 |
| 常驻服务 | live preview 可选 | 一律不起 |
| 结束 | 汇报路径 | 跑 `collect_manifest.py`，回一行 JSON |
| 改稿 | 对话里改 | brief.revision，在同一 WORK 的项目上改 |

**Hard rule — paths**：`${SKILL_DIR}` 与 `skills/ppt-master/` 前缀一律换成 brief 给的 skill_dir；所有命令 `cd "<WORK>" && …`；Python 用 brief 给的解释器。

## 2. 读什么（精简核心包，按序一次读完）

```
${SKILL_DIR}/workflows/profiles/quick-generate.md      # 流程骨架：§2 建项目 / §3 写 SVG 与门禁节奏 / §4 导出；§1 的运动门禁按 brief 约束直接判「无」
${SKILL_DIR}/references/plan-core.md                   # 页面节奏、密度、关系（§4 / §5）
${SKILL_DIR}/references/canvas-formats.md              # 画布与字号起点
${SKILL_DIR}/references/shared-standards-core.md       # 文本 / 字体 / 边界硬标准
${SKILL_DIR}/references/executor-base.md               # 页面创作规则与模块路由表
${SKILL_DIR}/references/semantic-svg.md                # SVG 语义结构
${SKILL_DIR}/references/preset-shape-vocabulary.md     # 187 个预设形状名
${SKILL_DIR}/references/visual-styles/<brief.style.visual_style>.md
${SKILL_DIR}/references/modes/<brief.style.mode>.md    # brief 给了 mode 才读
```

然后按 `executor-base.md` 的路由表看 roster 会触发哪些模块（原生图表 / 表格 → `executor-chart.md` / `executor-table.md` / `native-data-interface.md`、`templates/charts/chart-vocabulary.md`、`templates/tables/table-vocabulary.md`；有图片 → `executor-image.md` 四件；都没有就不读）。**不读**：`intake.md`、`routing.md`、`modes/_index.md`、`visual-styles/_index.md`、`image-renderings/_index.md`、`templates/icons/README.md`（brief 没给图标池）、`generate-pptx.md`、任何 HTML 路由文档。

## 3. 步骤

1. **建项目**：`python project_manager.py init <slug> --quick-generate`（slug 用 brief.job_id）。注意它建出来的目录名**带日期后缀**（`<slug>_YYYYMMDD`），后续一律用 init 输出的真实路径。再 `import-sources <project_path> <brief 里每个材料的绝对路径>`。
2. **规划（只在上下文）**：按 quick-generate.md §2「Pre-P01 resolution」做，但 roster / 页数 / 风格 / 配色 / 字体 / 阅读模式取 brief；brief 没给 roster 时自己在 `pages.total` 内分页。运动门禁：brief 的 `custom_animations=false` 就是「无信号」，不读 `animations.md`。
3. **校准**：用 brief 渲染好的那条 `text_measure.py calibrate` 命令（字体就是 brief.style.fonts，不要换），把每个角色的 chars-per-100px 记在上下文里，所有文本框按它算宽。
4. **写 SVG**：文件名两位连续编号（`01_cover.svg` … `NN_end.svg`），每页根 `<svg viewBox="0 0 1280 720" lang="<brief.language>" font-family="<brief.style.fonts.cjk>" data-pptx-page-role="…">`；数字只能来自材料；`must_keep` 原样写，`must_avoid` 绝不出现；信息密集页宁可拆行、缩短措辞，不得缩小 brief 规定的字号角色（annotation 允许 ±2px）。
5. **门禁**：roster ≥ 7 页时 P05 后跑 `svg_quality_checker.py <project> --quick-generate --canonical-authoring --stage early --json`，修完再继续；全部写完跑 `--stage final --json`，0 error 才导出；每轮修复后重跑同一命令。连续 3 轮仍有 error：把剩余 error 原文记进日志，仍然导出（exporter 若拒绝就记原因）。
6. **导出**：`svg_to_pptx.py <project> --quick-generate --no-notes`（brief 开了 speaker_notes 才 `--with-notes`；`native_charts_tables=true` 且页面里有原生 chart / table 决定时加 `--native-charts-and-tables`）。
7. **收尾**：复制最终 pptx 为 `<WORK>/<output.pptx_name>`；写 `<WORK>/<output.log_name>`（时间线、读过的文档、每次检查器 errors / warnings 与修复、自行决定的事、每页一行自评）；跑 `python ${SKILL_DIR}/host/collect_manifest.py "<WORK>" --preflight -o "<WORK>/<output.manifest_name>"`；最后一条回复只写一行 JSON `{"ok": …, "manifest": "…", "note": "…"}`。导不出也要走完 7。

## 4. 改稿（brief.revision）

- 找项目：WORK 下含 `svg_output/` 的目录（`collect_manifest.py` 同一判据），不新建。
- 按 quick-generate.md「Revision after delivery」：改对应页的 SVG；页数增删先重新编号文件名 / 页脚 / 目录页；上一版 `exports/` 保留；重跑 final 检查器与导出；再走 §3 第 7 步。
- 意见与 brief 冲突（例如要求换字体）：以 brief 为准，并把冲突写进日志的「自行决定」。

## 5. 宿主侧约定（agent 不用做，写给接入方）

- 运行时：给 agent 持久 bash + 文件读写；不给网络也能跑（零图片、无调研）；单任务上限建议 30~40 分钟；取消 = 作废，重跑用新 job_id。模型网关若有内容审查（阿里云 bailian 通道会随机误伤长技术上下文），宿主在同一会话上续跑重试，不重建。
- 字体：brief.style.fonts 必须是**宿主渲染 / 预检机器上真实安装**的字体，否则检查器通过的页面在替代字体下会溢出（实测：按微软雅黑校准、用 Noto 渲染，13 页里 5~8 处溢出）。Linux 宿主用 `Noto Sans CJK SC`（思源黑体）最稳。
- 产物：只信 `manifest.json`（程序收集），不要解析 agent 的自然语言回复；`ok=false` 时看 `error` 与 `<log_name>`。
- 参考实现：`host/README.md`。
