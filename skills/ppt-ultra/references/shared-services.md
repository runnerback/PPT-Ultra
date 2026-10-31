---
description: Fusion-layer services that every PPT Ultra route may call — source conversion, topic research, image generation/search, narrative modes, speaker-notes model, unified acceptance.
---

# Shared Services

这些能力原本只属于某一个引擎，融合后**所有路由都能调用**。PPTX 系路由按自己 runtime 规定的时机使用它们（以 runtime 为准）；HTML 路由按本文的时机使用。

所有 Python 命令都依赖根目录的 PPTX 引擎工具链：首次使用前执行 `pip install -r "${SKILL_DIR}/requirements.txt"`。这些脚本启动时会自动做完整性检查；检查失败时（退出码 78）不要排查或绕过，改走下表的"降级"列。

| 服务 | 命令 / 文档 | HTML 路由的使用时机 | 降级 |
|---|---|---|---|
| 素材转 Markdown | `python3 "${SKILL_DIR}/scripts/source_to_md.py" <file\|dir\|url> -o <deck-output-dir>/sources/`（支持 PDF/DOCX/PPTX/XLSX/EPUB/网页；详见 [`../scripts/docs/conversion.md`](../scripts/docs/conversion.md)） | 用户给了文件或 URL 时，在写大纲 / PageContentPack **之前**执行；之后只读转换得到的 `.md` | 直接读原文件；读不了的说明原因 |
| 主题调研 | [`../workflows/stages/topic-research.md`](../workflows/stages/topic-research.md) | 只有主题、或素材缺少关键事实时。只查缺口，结论写进 `<deck-output-dir>/sources/research.md`，并标注来源 | 用通用知识写，明确标出"待核实" |
| AI 生图 | `python3 "${SKILL_DIR}/scripts/image_gen.py" "<prompt>" --aspect_ratio <比例> -o <deck-output-dir>/images`（后端和密钥配置见 [`../scripts/docs/image.md`](../scripts/docs/image.md)，`.env.example`） | 用户**明确**同意生图之后。提示词规则按引擎：editorial 用 `engines/html-editorial/references/image-prompts.md`；themed 生成后再跑 `media:stage`。宿主自带 image-gen 工具时，两种方式任选 | 不生图：editorial 改用无图版式，themed 选无媒体页 |
| 网图搜索 | `python3 "${SKILL_DIR}/scripts/image_search.py" …`（见 [`../references/image-searcher.md`](../references/image-searcher.md)） | 用户要求真实照片或素材图时 | 改用无图版式 |
| 截图美化 | `engines/html-editorial/references/screenshot-framing.md` 和 `engines/html-editorial/assets/screenshot-backgrounds/` | 任何路由处理用户截图时都可以借用这些背景资产 | 原图加留白 |
| 叙事模式 | [`modes/_index.md`](./modes/_index.md) | 写大纲前选定一种 mode；editorial 的叙事弧对应 `narrative` | 用 `briefing` |
| 演讲备注模型 | 字段：`purpose` / `talk` / `transition` / `minutes` / `section`；落地方式：editorial 写 `SPEAKER_NOTES`（`engines/html-editorial/references/presenter-mode.md`），PPTX 写备注（[`executor-notes.md`](./executor-notes.md)） | 场景是演讲时必须写；没有来源支持的事实不写进备注 | — |

## 统一验收（HTML 路由）

两个 HTML 引擎共用同一套状态和返工预算。PPTX 路由使用自己的 gate，不套用这一节。

- 状态只有三种：**通过** / **待修正** / **阻塞**。
- 逐项核对 intake brief：route、deliverable、style、size、language、media、constraints 是否全部落实；有没有残留模板默认文案；有没有与主题无关的内容。
- 引擎自己的校验必须全部通过。editorial：`validate-presenter-mode`、`validate-swiss-deck`（风格 B），再加 checklist P0 项。themed：`validate:goal-spec`、`validate:swiss`、`validate:goal-copy`。
- 有浏览器能力时，逐页打开预览做可见性检查；没有时，不得声称已完成视觉验收。
- 最多修正 2 轮。仍不通过就标记"阻塞"，说明未达标项，不得写成"已完成"。
