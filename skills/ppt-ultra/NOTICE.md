# NOTICE — PPT Ultra

PPT Ultra 由三个开源 Skill 融合而成。各部分保留原作者署名和原许可证。

| 部分 | 来源 | 作者 | 许可证 | 在本包中的位置 |
|---|---|---|---|---|
| PPTX Native 引擎 | ppt-master 6.8.0 — https://github.com/hugohe3/ppt-master | Hugo He | MIT（全文见 [`LICENSE`](LICENSE)） | 根目录 `scripts/` `templates/` `references/` `workflows/`（`intake.md` `html-*.md` 和 `references/shared-services.md` 除外） |
| HTML Editorial 引擎 | guizang-ppt-skill — https://github.com/op7418/guizang-ppt-skill | 歸藏 (op7418) | AGPL-3.0（全文见 [`engines/html-editorial/LICENSE`](engines/html-editorial/LICENSE)） | `engines/html-editorial/`、`workflows/html-editorial.md` |
| HTML Themed 引擎 | dashi-ppt 0.4.14 — https://github.com/chuspeeism/dashi-ppt-skill | chuspeeism | AGPL-3.0（全文见 [`engines/html-themed/LICENSE`](engines/html-themed/LICENSE)；原版附带的专有导出组件 `html-deck-to-pptx` 及其浏览器版 `editable-pptx-browser.js` **已移除**，见下文） | `engines/html-themed/`、`workflows/html-themed.md` |
| Spec Native 引擎 | 本包新增（1.1.0） | Runnerback | MIT（全文见 [`engines/spec-native/LICENSE`](engines/spec-native/LICENSE)） | `engines/spec-native/`、`workflows/spec-native.md`、`references/spec-native-layouts.md`、`references/spec-native-content-rules.md` |
| 融合层 | 本包新增 | Runnerback <286980573@163.com>（整合与架构设计） | AGPL-3.0（与所含 AGPL 组件一致） | `SKILL.md` 正文、`workflows/intake.md`、`workflows/routing.md` §8、`references/shared-services.md`、本文件 |

## 分发注意

- 组合作品包含 AGPL-3.0 组件。对外分发本包或基于它提供网络服务时，须按 AGPL-3.0 公开对应源代码。
- guizang 和 dashi 的 AGPL-3.0 全文分别在 `engines/html-editorial/LICENSE` 和 `engines/html-themed/LICENSE`。
- dashi 的 HTML→PPTX 导出引擎是专有授权，许可证只允许它作为 Dashi PPT skill 的一部分使用，禁止用于其他软件，因此本包已将它移除，包括：`project/packages/html-deck-to-pptx/`、`project/assets/vendor/editable-pptx-browser.js`、`project/scripts/export-pptx.mjs`，以及 `export:pptx` / `export:pdf` 两个 npm 脚本。预览服务的 PPTX 和服务端 PDF 接口改为返回 501，模板里的 PPTX 导出入口已隐藏，PDF 自动改用浏览器内导出（html-to-image + pdf-lib，均为 MIT）。合并上游更新时**不要把这些文件带回来**。
- 根目录的 `LICENSE`、`SPONSORS.md`、`SPONSORS_CN.md`，以及 `SKILL.md` frontmatter 里的 copyright / license / official_repository / sponsors 四个字段，由 PPTX 引擎的完整性检查校验，修改任何一项都会导致 Native 路由停止运行。

## 修改记录

按 AGPL-3.0 第 5(a) 条，以下列出本包相对各上游版本的修改。

**2026-11-02 — PPT Ultra 1.2.0（Runnerback，未发布）**

- 新增**宿主调用契约** `host/`：`brief.schema.json`（宿主写的任务说明：WORK / SKILL_DIR / python、作品信息、页数与 roster、风格与字体、材料、约束、改稿意见、输出名）、`build_prompt.py`（校验并渲染确定性 prompt）、`collect_manifest.py`（程序化收集 manifest.json：项目、最新 pptx、检查器 / postflight 报告、pptx 页数 / 原生 chart / table / 字体、LibreOffice 预检）、`examples/`、`README.md`。
- 新增 `workflows/profiles/host-quick.md`：Generate PPTX 的宿主 profile——Quick 的决定权收回宿主，跳过 intake / routing，精简核心包读文档，不问不起服务，改稿在同一项目上做，收尾跑 collect_manifest。`SKILL.md` 运行时表、`routing.md` §8、`intake.md` §3、`workflows/index.md` 各加一行。
- 基准教训写进契约：校准字体必须是渲染端真实安装的字体（Linux 宿主用 Noto Sans CJK SC）；阿里云通道模型对长技术上下文可能触发网关内容审查。

**2026-11-02 — PPT Ultra 1.1.1（Runnerback，未发布）**

- 新增跨引擎风格 brief 表 `references/style-briefs/themes.json`（由仓库级 `tools/build-style-briefs.mjs` 从 Editorial 主题表、Themed `theme-profiles.mjs` + `options.md`、Spec Native `pptx_style.py` 生成，不手抄）：每个主题给 `html`（本引擎选法）/ `native_style_brief`（Native 路线风格 brief）/ `spec_style`（Spec profile 的 `style`，暗底主题为 null）三种消费方式，另给 Spec 默认风格转 Editorial 瑞士风的 `gz-theme.mjs brand` 配方。`workflows/intake.md` §2.1 跨格式映射改为取表、不再看风格图猜色；`workflows/spec-native.md` §4 与 `references/spec-native-layouts.md` 的 `style` 行指向它。
- 修复 `tools/upstream-check.sh` 在 bash 3.2 下的两处问题；新增 `tools/upstream-pins.json`；NOTICE 合并步骤前后加核对与回写；中英 USER_GUIDE FAQ「哪些路线能出 .pptx」补 D 路线；Spec Native 的来源说明去掉作者所在企业的产品名。

**2026-11-02 — PPT Ultra 1.1.0（Runnerback）**

- 新增 **Spec Native 引擎** `engines/spec-native/`（MIT）：规格 JSON → 原生 PPTX 的确定性生成器（`spec_to_pptx.py` CLI、`pptx_style.py` 设计系统与风格覆盖、`ppt_build.py` 31 种版式、`ppt_extra.py` 扩展版式、`graph_layout.py` Graphviz 流程 / 泳道布局、5 份可构建示例）。源自作者在企业内部运行的 Agent 制作 PPT 管线，已去掉企业依赖与企业数据；不读 ppt-master 的任何脚本，不触发其完整性检查。
- 新增 `workflows/spec-native.md`（Generate PPTX 的 Spec profile 运行时）、`references/spec-native-layouts.md`、`references/spec-native-content-rules.md`。
- `SKILL.md`：description 与 `fused_from` 加 Spec Native；路由表、引擎表各加一行；完整性检查说明「HTML 路由与 Spec profile 跳过」；「engines stay intact」加 `engines/spec-native/*.py`。受完整性检查的四个 frontmatter 字段未动。
- `workflows/routing.md`：§2 Generate PPTX 行加 Spec authority；§3 加 Spec 触发条件行与「Spec is a profile, not a fifth route」硬规则；§8 加两行格式判定。
- `workflows/intake.md`：§1 信号表、§3 非交互默认、§4 brief 的 profile 枚举、§5 交接表各加 Spec。
- `workflows/index.md` 登记 `spec-native`。
- `requirements.txt` 末尾加 Spec Native 依赖说明（python-pptx / Pillow 已含；Graphviz 为系统包可选）。
- 仓库级：`tools/smoke.sh` 冒烟脚本；README（中英）、`docs/USER_GUIDE(.zh-CN).md`、`.claude-plugin/marketplace.json` 加 Spec Native 说明，版本 1.1.0。

**2026-11-01 — PPT Ultra 1.0.0（Runnerback）**

- **ppt-master 6.8.0**
  - 改写 `SKILL.md`：name 改为 `ppt-ultra`，新增 `fused_from` 元数据、统一加载顺序和"Generate HTML Deck"路由；frontmatter 中受完整性检查的四个字段保持原样。
  - `workflows/routing.md`：路由表新增 HTML 路由一行，新增 §8 交付格式判定。
  - `workflows/index.md`：登记新增的工作流。
  - 新增 `workflows/intake.md`、`workflows/html-editorial.md`、`workflows/html-themed.md`、`references/shared-services.md`。
  - 删除 `scripts/tests/`。
- **guizang-ppt-skill**
  - `SKILL.md` 正文移植为 `workflows/html-editorial.md`，删除 Step 0 的 git 自动更新检查，资源路径加 `engines/html-editorial/` 前缀。
  - `assets/` `references/` `scripts/` 原样放入 `engines/html-editorial/`。
- **dashi-ppt 0.4.14**
  - `SKILL.md` 正文移植为 `workflows/html-themed.md`，删除版本检查，资源路径加 `${SKILL_DIR}/engines/html-themed` 前缀。
  - 删除 `scripts/check_latest_version.mjs`。
  - 移除专有导出组件（见上文"分发注意"），并修改 `project/package.json`（删除 `export:pptx` / `export:pdf` 脚本）、`project/scripts/preview/export-routes.mjs`（PPTX 和服务端 PDF 接口返回 501）、`project/src/runtime-assets.mjs`（删除导出组件的 bundle 条目）、`project/assets/template-swiss.html`（隐藏 PPTX 按钮、导出函数改为提示不支持、PDF 改用浏览器内导出）。
- **全部引擎**：删除 `node_modules/`、`.npmrc`、`__pycache__/` 等安装产物，不影响功能。

## 合并上游更新（维护者）

三个引擎在运行时都不自动更新。先在仓库根目录跑 `bash tools/upstream-check.sh`（读 `tools/upstream-pins.json` 里钉住的版本，查 GitHub 当前 release / 版本文件 / 最新提交，落后的退出码 1），再按引擎手动合并：

1. **ppt-master**：用上游 `skills/ppt-master/` 覆盖根目录下除 `SKILL.md`、`NOTICE.md`、`engines/`、`workflows/intake.md`、`workflows/html-*.md`、`references/shared-services.md` 以外的文件；再把上游 `SKILL.md` 的改动和 `workflows/routing.md` 的改动手工合进来（保留本包新增的 §8 和 HTML 路由那一行）。
2. **guizang**：用上游的 `assets/` `references/` `scripts/` 覆盖 `engines/html-editorial/`；再把上游 `SKILL.md` 的正文改动同步到 `workflows/html-editorial.md`（路径加 `engines/html-editorial/` 前缀，不要恢复 Step 0 的更新检查）。
3. **dashi**：用上游的 `skills/dashi-ppt/{project,references,assets,scripts}` 覆盖 `engines/html-themed/`（删掉 `scripts/check_latest_version.mjs`；按上文重新移除专有导出组件，并重新应用 `project/scripts/preview/export-routes.mjs`、`project/assets/template-swiss.html`、`project/src/runtime-assets.mjs` 里的禁用改动）；再把上游 `SKILL.md` 的改动同步到 `workflows/html-themed.md`。
4. 合并后跑一遍验证：仓库根目录 `bash tools/smoke.sh`（含 `attribution_guard.py`、Spec Native 全部示例构建、`check-presenter-runtime-sync.mjs`、可选 LibreOffice 转 PDF），再做一次 themed 渲染冒烟测试。Spec Native 引擎没有上游，只随本仓库维护。
5. 把合并到的版本 / 提交写回 `tools/upstream-pins.json`，并在上面的「修改记录」加一条。
