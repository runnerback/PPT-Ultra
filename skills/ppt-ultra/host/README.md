# PPT Ultra · 宿主调用契约（host contract）

> **版本**: 1.2.1（未发布） | **更新时间**: 2026-11-03 | 适用：bot / 流水线 / 脚本等**没有人在线**的宿主，让任何能跑 bash + 读写文件的 agent 运行时（Claude Code、dsh、Codex…）按 PPT Ultra 的 Native 路线出 .pptx。

```
宿主                                  agent 运行时                                  宿主
brief.json ──build_prompt.py──▶ prompt ──▶ 读 SKILL.md → host-quick.md → 写 SVG → 门禁 → 导出 ──▶ collect_manifest.py ──▶ manifest.json
```

| 文件 | 作用 |
|---|---|
| [`brief.schema.json`](brief.schema.json) | brief 的 JSON Schema：任务 id、WORK / SKILL_DIR / python、作品信息、页数与 roster、风格（visual_style / 配色 / **字体**）、材料、图片、约束（含 `page_numbers`：false = 全程无页码）、must_keep / must_avoid、改稿意见、输出文件名 |
| [`build_prompt.py`](build_prompt.py) | 校验 brief（路径存在、页数与 roster 一致、字体给全、颜色合法）并渲染成确定性的中文 prompt；`--check` 只校验 |
| [`collect_manifest.py`](collect_manifest.py) | 运行结束后程序化收集 `manifest.json`：项目目录、最新 pptx、检查器 / postflight 报告、pptx 本体（页数、原生 chart / table 数、字体）、`--preflight` 用 LibreOffice 转 PDF 并核页数 |
| [`examples/`](examples/) | 一份虚构材料 + brief 示例 |
| [`../workflows/profiles/host-quick.md`](../workflows/profiles/host-quick.md) | agent 侧的运行时 authority（Quick 的宿主版：精简读文档、不问、不起服务、改稿规则） |
| [`../workflows/profiles/host-editorial.md`](../workflows/profiles/host-editorial.md) | 交付 html 时的 authority（Editorial 引擎的宿主版：家族 / 主题由 brief 定，单文件 deck + 演讲者备注，校验器） |

## 交付格式

- `deliverable: "pptx"`（默认）→ Native 路线，`host-quick.md`，产物 `.pptx`。
- `deliverable: "html"` → Editorial 路线，`host-editorial.md`，产物单文件 `.html`（浏览器打开，带演讲者模式：`?` 看快捷键）。`html.family` 选 `swiss` / `magazine`，`html.theme` 用模板内置主题 id，或给 `brand_color` 让 `gz-theme.mjs` 生成受约束的品牌主题；`speaker_notes` 默认开；`target_minutes` 给了会校验时间计划。
- HTML 风格与 .pptx 之间是同风格重新生成，不是转换（见 `workflows/intake.md` §2.1）。
- html 模式的 manifest：`deck.slides / placeholders / notes / dark_card_fill`（深色页上的灰底卡数，应为 0，模板里 `.card-fill` 是浅色页组件）、`validators`（presenter / swiss 校验器退出码与尾行）、`forbidden_hits`、`html_copy`。

## 接入三步

```bash
# 1) 宿主准备 WORK，把材料放进去，写 brief.json（work_dir / skill_dir / python 都是绝对路径）
python skills/ppt-ultra/host/build_prompt.py WORK/brief.json --check
python skills/ppt-ultra/host/build_prompt.py WORK/brief.json -o WORK/prompt.md

# 2) 把 prompt.md 作为用户消息交给 agent 运行时（工作目录 = WORK；需要持久 bash + 文件读写；不要开 live preview）
#    agent 读 SKILL.md → workflows/profiles/host-quick.md → 写 SVG → 门禁 → 导出 → 自己跑 collect_manifest.py

# 3) 宿主再跑一次 collect_manifest（防 agent 漏跑），只信它的输出
python skills/ppt-ultra/host/collect_manifest.py WORK --preflight --brief WORK/brief.json --pptx-name deck.pptx -o WORK/manifest.json
```

`manifest.json` 关键字段：`ok`、`pptx`、`deck.slides / charts / tables / fonts / theme_fonts`、`quality`（检查器 blocking / introduced 数）、`postflight`（导出器 status / quality_gate）、`preflight`（LibreOffice 转 PDF 的 status / pages / pdf）、`forbidden_hits`（brief.forbidden_strings 在页面文字里的命中，有命中 ok=false）、`page_number_hits`（`constraints.page_numbers=false` 时页码文字 / 标记的命中，有命中 ok=false）、`workflow`（首末命令时间）、`error`。brief 的 `must_avoid` 是给 agent 看的说明，`forbidden_strings` 才是程序硬校验的字面字串，两者配合用。

## 改稿

同一 WORK、同一 job_id，brief 加 `revision.feedback`（可带 `previous_manifest`），再走一遍三步。agent 在已有项目上改页、重跑门禁、重新导出；新 pptx 带新时间戳，旧的保留。agent 运行时若支持会话续写（如 dsh 的 `session/resume`），复用同一会话能省掉重读文档。

## 字体规则（最常见的翻车点）

`style.fonts` 必须是**运行 agent / 做预检的机器上真实安装**的字体，agent 用它校准字宽、写进每页 `font-family`。按一套字体校准、用另一套渲染，检查器通过的页面也会溢出（实测微软雅黑校准 + Noto 渲染，13 页溢出 5~8 处）。Linux 宿主推荐 `Noto Sans CJK SC`。

注意导出器的字体策略：ppt-master 的 `svg_to_pptx` 会把常见 CJK 字体族（Noto Sans CJK SC / PingFang / Source Han Sans 等）统一映射成 **Microsoft YaHei** 写进 pptx（`svg_to_pptx/drawingml/utils.py` 的映射表，为了在 Office 上可移植），所以交付件的字体永远是雅黑，SVG 里的字体只决定校准与预检。Noto 的字宽比雅黑宽，按 Noto 校准的版面在雅黑下只会更宽松。预检机器没有雅黑时 LibreOffice 会随机替代，`collect_manifest.py --preflight-font <校准字体>` 会在**副本**里把雅黑换回校准字体再转 PDF，预检看到的才是校准时的版面；交付件不动。

## 运行时建议

- 持久 bash + 文件读写；可以不给网络（零图片 + 不调研的 brief 不需要）。
- 单任务 15~35 分钟（13 页：DeepSeek-V4-Pro 约 13 分钟，Claude 约 31 分钟），上限建议 30~40 分钟；超时直接杀，取消即作废。
- 读文档约 2,200~3,400 行是固定开销，支持会话续写的运行时可在改稿时复用。
- 模型侧已知坑：经阿里云 bailian 通道的模型（含 DeepSeek-V4-Pro、GLM）对长技术上下文会**随机**触发网关内容审查 400（`data_inspection_failed`）；2026-11-02 把失败那一刻的完整上下文精确重放两次都正常，说明是抽检误伤而非内容。宿主要做的是：遇到这个错在**同一会话**上续跑（上下文都在会话日志里，续跑提示「从上次停下的地方继续」），重试 2~3 次；不要重建任务。

## 版本

- 1.2.1（2026-11-03，未发布）：brief `constraints.page_numbers`（默认 true）——false 时 pptx / html 两种 prompt 都渲染「页码：不要」硬规则，`collect_manifest.py` 复核页码文字（`N / M` / 第 N 页 / Page N、page-number / slide-number 标记；html 看每个 slide 里的 `NN / TOTAL`），命中 `page_number_hits` 且 ok=false。brief_version 不变（可选字段，老 brief 行为不变）。
- 1.2.0（2026-11-02）：首版契约。brief v1、manifest v1、host-quick profile。
