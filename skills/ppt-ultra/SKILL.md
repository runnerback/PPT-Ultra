---
name: ppt-ultra
description: >
  一站式 PPT / 演示文稿 / 幻灯片生成 Skill（融合 ppt-master、guizang-ppt、dashi-ppt）。
  可生成原生可编辑 PPTX（SVG→DrawingML、模板/母版、美化或编辑已有 .pptx、
  旁白/动画/视频）；也可按一份规格 JSON 确定性生成原生 PPTX（Spec Native：31 版式、9 种原生图表、
  流程 / 泳道 / 时序自动布局、出处角标，秒级出片，适合数据密集汇报与非交互环境）；
  也可生成横向翻页网页 PPT：杂志风 / 瑞士国际主义风（演讲者模式、
  提词、计时、观众屏同步），或 12 套主题、每页 3+1 方案、可导出 PDF 的 HTML 演示。
  Use when the user asks to create, generate, reconstruct, beautify, redesign, template,
  fill, or edit a presentation, PPT, PPTX, slide deck, web/HTML deck, keynote-style talk,
  courseware, or narrated deck video; or mentions 杂志风 PPT, 瑞士风 PPT, Swiss Style,
  horizontal swipe deck, 演讲者模式, theme01–theme12, ppt-master, guizang, dashi,
  spec-native, 规格 JSON, or a deterministic / data-dense .pptx report.
metadata:
  version: "1.2.0"
  fused_from: "ppt-master 6.8.0 (MIT); guizang-ppt-skill (AGPL-3.0); dashi-ppt 0.4.14 (AGPL-3.0); spec-native 1.0.0 (MIT, Runnerback)"
  copyright: "Copyright (c) 2025-2026 Hugo He"
  license: "MIT"
  official_repository: "https://github.com/hugohe3/ppt-master"
  sponsors:
    - "SPONSORS.md"
    - "SPONSORS_CN.md"
---

# PPT Ultra Skill

PPT Ultra 是一个统一的演示文稿 Skill：**一个入口（intake）→ 一张路由表 → 四条路由 → 一组共享服务**。原来三个 Skill 的能力成为这些路由、引擎和服务的组成部分，不再是三个并列的 Skill。

> 上面 `metadata` 中的 copyright / license / official_repository / sponsors 四个字段属于 PPT Native 引擎（源自 ppt-master，MIT）的署名要求，由其完整性检查校验，**不得修改或删除**。整个包的来源和许可证见 [`NOTICE.md`](NOTICE.md)。

## Mandatory Load Order

**Hard rule — paths before commands**: Retain the host-provided absolute
directory containing this file as `SKILL_DIR`. Per tool call, expand
`${SKILL_DIR}` and replace any `skills/ppt-master/` prefix with it. Never `cd`,
use CWD, or assume a repo checkout. If unavailable, ask; never search or guess.

1. Read this file.
2. Read [`workflows/intake.md`](workflows/intake.md) (`${SKILL_DIR}/workflows/intake.md`) and resolve the route, profile, and style; it applies [`workflows/routing.md`](workflows/routing.md), which wins on any route conflict.
3. **Only if a Native PPTX route was selected**, run the PPTX engine integrity gate
   `python3 "${SKILL_DIR}/scripts/attribution_guard.py"`. Any non-zero result
   stops the Native routes immediately; do not inspect, repair, or bypass the
   integrity gate. On Windows, a `python3` that never starts (the WindowsApps
   stub exits 9009 with no output) is not a guard result: rerun with `python`
   first. HTML routes and the Spec profile skip this step (neither uses the Native
   engine's scripts).
4. Read only the selected runtime authority below and its explicitly triggered supporting documents.

| Selected route / profile | Runtime authority |
|---|---|
| Generate HTML Deck — Editorial (Magazine / Swiss, presenter mode) | [`workflows/html-editorial.md`](workflows/html-editorial.md) |
| Generate HTML Deck — Themed (12 themes, 3+1 variants, in-browser PDF) | [`workflows/html-themed.md`](workflows/html-themed.md) |
| Generate PPTX — Image to PPTX | [`workflows/profiles/image-to-pptx.md`](workflows/profiles/image-to-pptx.md); Codex-supported, always Quick |
| Generate PPTX — Beautify | [`workflows/profiles/beautify-pptx.md`](workflows/profiles/beautify-pptx.md); explicit Quick intent selects Quick, otherwise Default |
| Generate PPTX — ordinary Default | [`workflows/generate-pptx.md`](workflows/generate-pptx.md) |
| Generate PPTX — ordinary explicit Quick | [`workflows/profiles/quick-generate.md`](workflows/profiles/quick-generate.md) |
| Generate PPTX — Spec (deterministic spec JSON → native PPTX, no SVG authoring) | [`workflows/spec-native.md`](workflows/spec-native.md) |
| Generate PPTX — Host Quick (machine-written host brief from `host/build_prompt.py`; decisions pre-resolved, no questions, manifest at the end) | [`workflows/profiles/host-quick.md`](workflows/profiles/host-quick.md) |
| Create Template | [`workflows/create-template.md`](workflows/create-template.md) |
| Edit Native PPTX | [`workflows/edit-native-pptx.md`](workflows/edit-native-pptx.md) |

**Hard rule — selected authority only**: Do not load another top-level route's
procedure after routing. Image to PPTX and Beautify are mutually exclusive;
Image to PPTX activates Quick, while Beautify selects from explicit Quick
intent. Never load both runtimes. Spec is a third Generate PPTX profile: it never
loads `generate-pptx.md`, `quick-generate.md`, or any Native engine script, and a
deck never mixes Spec with SVG authoring. Host Quick is Quick driven by a host brief: it
skips `intake.md` / `routing.md` (the brief fixed them), reads the trimmed core in
`host-quick.md` §2, and ends with `host/collect_manifest.py`. Editorial and Themed are mutually exclusive
HTML profiles. Supporting documents refine one route; they never compete with it.

## Engines and Shared Services

| Layer | Location | Role |
|---|---|---|
| PPTX Native engine | `scripts/` `templates/` `references/` `workflows/`（根目录） | SVG 编写 → 原生 PPTX、模板工作区、编辑已有 PPTX、旁白 / 动画 / 视频 |
| HTML Editorial engine | `engines/html-editorial/` | 单文件 HTML：杂志风 / 瑞士风模板、版式库、演讲者模式运行时、校验器 |
| HTML Themed engine | `engines/html-themed/` | Node 生成器：12 主题、版式查询、3+1 方案、本地预览编辑器、浏览器内 PDF 导出（不导出 PPTX；.pptx 由 PPTX Native 或 Spec Native 引擎产出） |
| Spec Native engine | `engines/spec-native/` | 规格 JSON → 原生 PPTX（python-pptx）：31 版式、9 种原生图表、Graphviz 流程 / 泳道 / 层次布局、出处角标与引用页；确定性、无交互、不依赖 Native 引擎脚本（[`engines/spec-native/README.md`](engines/spec-native/README.md)） |
| Shared services | [`references/shared-services.md`](references/shared-services.md) | 素材转 Markdown、主题调研、生图 / 搜图、截图美化、叙事模式、演讲备注模型、HTML 统一验收 |

**Hard rule — engines stay intact**: never edit files under `engines/*/assets`, `engines/html-themed/project/src`, `engines/spec-native/*.py`, or the Native engine's guarded scripts to complete a deck. Decks are written to the caller's working directory, never inside `${SKILL_DIR}`.

**Hard rule — no engine self-update**: none of the engines checks for or pulls upstream updates at runtime.

---

## Authored Expression Range (Native PPTX routes)

**Reference — not a constraint**: what a native generated page can carry. Text — inline
emphasis runs, lead-in, kicker, pull quote, hero number, takeaway line. Geometry
— 187 Office presets, Boolean merge, connectors, freeform, page-field and
outline-carrier composition. Image — full-bleed field, editorial crop, shaped
picture, registered layers, scrim and spotlight, cross-page continuity. Paint —
gradients, channel alpha, native shadow and glow, halftone, faceted form.
Recurrence — one cross-page motif varied by page role. Each form's syntax lives
in the selected runtime authority's construction references.

---

## Vocabulary

One meaning per term across every loaded file. Where a word is used in
more than one sense, the sense is named here and the files say which one.

| Term | Meaning |
|---|---|
| **Reference** (label) | A starting sketch the executing role adjusts or replaces freely, with no upstream repair or stated reason; `(binding)` after a field label removes that freedom |
| **Relationships** | The §IX line naming a page's semantic units and their source-stated `order` / `link` / `parent` / `membership` / `contrast` / `overlap`, or `none` |
| **Topology decision** | The per-page yes/no on whether geometry must carry the page's `Relationships` (`topology=yes` / `topology=no`); unrelated to `pptx_structure.mode` |
| **`pptx_structure.mode`** | `flat` (every object Slide-local) or `structured` (declared Master/Layout/slot metadata); a packaging route, never information structure |
| **Composition** | The §IX `Composition` line: a Reference for a page's macro composition, hierarchy, and focus |
| **Image pattern** | The §VIII column carrying one image-composition suggestion in ordinary words (optionally citing `#P`/`#M` ids) |
| **Layout** | A PowerPoint Layout under a Master, or the Layout template kind; never a page-composition sketch |
| **Device** | An everyday page carrier — card, band, icon-and-label, KPI tile, divider, quote block — recalled in the Executor's device menu |
| **Carrier** | What a page unit sits in: a device, an image, or native geometry; the family names are carrier and field, direction and sequence, grouping and ownership, emphasis and annotation. `data-pptx-carrier` is a structured-slot attribute, not this term. The **carrier receipt** is the checker's per-page inventory of what was actually drawn |
| **Page job** | What one page must do for the reader; the input every carrier, contour, and effect decision is judged against |
| **Page field** | One large surface, outline, aperture, or off-canvas contour that organizes zones instead of a card per unit |
| **Contour / preset / atom** | A contour is a shape's silhouette; a preset is one of the 187 Office `prst` contours drawn through `preset_shape_svg.py`; an atom is one object that compiles to one DrawingML shape |
| **Geometry signature** | The retained line `page job → composition move → contour / edge language` kept per page and compared before the next page |
| **Texture** (of a block) | Whether a §IX block is prose, bullets, keywords, or labels; distinct from visual texture (grain, halftone) |
| **Anchor** | Two senses: a lock anchor (a deck-wide color, type, or spacing value) and the `page_rhythm` tag `anchor` for structural pages |
| **Sheet / slice / plate** | A sheet is one generated image holding several elements on a chroma key; a slice is one element cut from it; a plate is a registered full-canvas layer of several non-overlapping objects |
| **Module line** | The `P<NN> modules: …` line written before each page naming the triggered modules it uses |
| **Mode** | Named by qualifier: communication `mode` (how the deck argues), reading mode (`consumption_mode`), `generation_mode` (`continuous` / `split`), `pptx_structure.mode`, `replication_mode` (how a template was created) |

## Phase Frame

Every route is one Plan → Do·Check·Act cycle: Plan ends when every authoring
input exists as a file or retained decision; Do authors pages, Check runs the
route's gates, Act repairs at the owning layer (discipline 7), and the cycle
ends at export. Step numbers stay as written.

| Phase | Default | Quick | Edit Native | Create Template |
|---|---|---|---|---|
| **Plan** | Steps 1–5 | §2 | §1–4 | Steps 1–3 |
| **Do·Check·Act** | Steps 6–7 | §3–4 | §5–7 | Steps 4–8 |

Generate HTML Deck follows the same cycle: Plan = intake brief + outline / PageContentPack; Do·Check·Act = author or render, engine validators, unified acceptance ([`shared-services.md`](references/shared-services.md)), at most two repair rounds.

## Global Execution Discipline

1. **Serial execution** — Follow the selected authority's steps in order. A completed non-blocking step may continue directly to the next eligible step.
2. **Blocking means stop** — At every `⛔ BLOCKING` gate, wait for explicit user confirmation. Do not decide on the user's behalf.
3. **No cross-phase bundling** — Do not combine work across an unclosed gate. Once the route's final user gate closes, later non-blocking steps may continue automatically.
4. **Gate before entry** — Verify every listed prerequisite before entering a step.
5. **No speculative execution** — Do not prepare later-phase artifacts before their owning step.
6. **Deterministic routing** — Do not add a route-choice question when [`routing.md`](workflows/routing.md) resolves the request. If a route prerequisite is missing, state it and stop that route.
7. **Act at the owning layer** — On failure, repair at the shallowest layer that owns the fault: the page for a page-local issue, the Plan artifact for a roster/spec/resource fault, the owning source artifact for a tool failure; then resume from the route's declared pointer. Do not silently downgrade a required artifact.

## Global Communication Rules

- Match the user's language and source language unless the user explicitly overrides it.
- Localize user-facing option labels and explanations. Render each fixed message template (role-switch banner, completion report) in the user's chat language when it differs from the template's. Keep exact enum IDs or field names when needed for precision.
- Keep `design_spec.md` section headings and field names in the template's original English; content values may use the user's language.
- Before switching roles, read the corresponding role reference and output:

```markdown
## [Role Switch: <Role Name>]
📖 Reading role definition: references/<filename>.md
📋 Current task: <brief description>
```

---

## Repository Compatibility

- Do not run `scripts/update_repo.py`: this fused package is not a checkout of any single upstream repository. Upstream updates are a maintainer merge (see [`NOTICE.md`](NOTICE.md)).
- This package is a workflow/skill, not a generic application scaffold. Do not create `.worktrees/`, `tests/`, branch workflows, or generic engineering structure by default.
- Keep required workflow, reference, script, and template documentation inside this Skill directory.
- Repository-level documents may point into the package; package runtime files must not depend on repository-level instructions.
- On Windows, if a documented `python3 ...` command is unavailable, rerun the same command with `python`.
- Sponsor information is optional reference material. Read the matching [`SPONSORS.md`](SPONSORS.md) or [`SPONSORS_CN.md`](SPONSORS_CN.md) only when the user explicitly requests a model, AI image model, API/provider, or hosted-service recommendation. Never surface sponsor or model recommendations proactively during normal generation, troubleshooting, or quality review.
