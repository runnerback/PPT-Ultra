# NOTICE — PPT Ultra

PPT Ultra 由三个开源 Skill 融合而成。各部分保留原作者署名和原许可证。

| 部分 | 来源 | 作者 | 许可证 | 在本包中的位置 |
|---|---|---|---|---|
| PPTX Native 引擎 | ppt-master 6.8.0 — https://github.com/hugohe3/ppt-master | Hugo He | MIT（全文见 [`LICENSE`](LICENSE)） | 根目录 `scripts/` `templates/` `references/` `workflows/`（`intake.md` `html-*.md` 和 `references/shared-services.md` 除外） |
| HTML Editorial 引擎 | guizang-ppt-skill — https://github.com/op7418/guizang-ppt-skill | 歸藏 (op7418) | AGPL-3.0（全文见 [`engines/html-editorial/LICENSE`](engines/html-editorial/LICENSE)） | `engines/html-editorial/`、`workflows/html-editorial.md` |
| HTML Themed 引擎 | dashi-ppt 0.4.14 — https://github.com/chuspeeism/dashi-ppt-skill | chuspeeism | AGPL-3.0（全文见 [`engines/html-themed/LICENSE`](engines/html-themed/LICENSE)；原版附带的专有导出组件 `html-deck-to-pptx` 及其浏览器版 `editable-pptx-browser.js` **已移除**，见下文） | `engines/html-themed/`、`workflows/html-themed.md` |
| 融合层 | 本包新增 | Runnerback <286980573@163.com>（整合与架构设计） | AGPL-3.0（与所含 AGPL 组件一致） | `SKILL.md` 正文、`workflows/intake.md`、`workflows/routing.md` §8、`references/shared-services.md`、本文件 |

## 分发注意

- 组合作品包含 AGPL-3.0 组件。对外分发本包或基于它提供网络服务时，须按 AGPL-3.0 公开对应源代码。
- guizang 和 dashi 的 AGPL-3.0 全文分别在 `engines/html-editorial/LICENSE` 和 `engines/html-themed/LICENSE`。
- dashi 的 HTML→PPTX 导出引擎是专有授权，许可证只允许它作为 Dashi PPT skill 的一部分使用，禁止用于其他软件，因此本包已将它移除，包括：`project/packages/html-deck-to-pptx/`、`project/assets/vendor/editable-pptx-browser.js`、`project/scripts/export-pptx.mjs`，以及 `export:pptx` / `export:pdf` 两个 npm 脚本。预览服务的 PPTX 和服务端 PDF 接口改为返回 501，模板里的 PPTX 导出入口已隐藏，PDF 自动改用浏览器内导出（html-to-image + pdf-lib，均为 MIT）。合并上游更新时**不要把这些文件带回来**。
- 根目录的 `LICENSE`、`SPONSORS.md`、`SPONSORS_CN.md`，以及 `SKILL.md` frontmatter 里的 copyright / license / official_repository / sponsors 四个字段，由 PPTX 引擎的完整性检查校验，修改任何一项都会导致 Native 路由停止运行。

## 修改记录

按 AGPL-3.0 第 5(a) 条，以下列出本包相对各上游版本的修改。

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

三个引擎在运行时都不自动更新。上游有新版本时，按引擎手动合并：

1. **ppt-master**：用上游 `skills/ppt-master/` 覆盖根目录下除 `SKILL.md`、`NOTICE.md`、`engines/`、`workflows/intake.md`、`workflows/html-*.md`、`references/shared-services.md` 以外的文件；再把上游 `SKILL.md` 的改动和 `workflows/routing.md` 的改动手工合进来（保留本包新增的 §8 和 HTML 路由那一行）。
2. **guizang**：用上游的 `assets/` `references/` `scripts/` 覆盖 `engines/html-editorial/`；再把上游 `SKILL.md` 的正文改动同步到 `workflows/html-editorial.md`（路径加 `engines/html-editorial/` 前缀，不要恢复 Step 0 的更新检查）。
3. **dashi**：用上游的 `skills/dashi-ppt/{project,references,assets,scripts}` 覆盖 `engines/html-themed/`（删掉 `scripts/check_latest_version.mjs`；按上文重新移除专有导出组件，并重新应用 `project/scripts/preview/export-routes.mjs`、`project/assets/template-swiss.html`、`project/src/runtime-assets.mjs` 里的禁用改动）；再把上游 `SKILL.md` 的改动同步到 `workflows/html-themed.md`。
4. 合并后跑一遍验证：`python3 scripts/attribution_guard.py`、`node engines/html-editorial/scripts/check-presenter-runtime-sync.mjs`，并做一次 themed 渲染冒烟测试。
