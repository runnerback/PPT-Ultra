# PPT Ultra

**一句话需求，生成可以直接用的演示文稿：网页演讲 PPT、主题化汇报 PPT，或原生可编辑的 .pptx。**

PPT Ultra 是一个 Claude Code Skill。它把三套成熟的开源 PPT 生成能力整合成**一个入口、一套流程**。用户不用关心底层用哪个引擎，只要说清楚"要什么、怎么用"，Skill 会自动选路线、选风格，生成后再做验收。

> 整合与架构设计：boodorg · 版本 1.0.0

---

## 能做什么

| 场景 | 交付物 | 亮点 |
|---|---|---|
| **现场演讲 / 发布会 / 分享会** | 单文件 HTML 网页 PPT | 杂志风或瑞士国际主义风；演讲者视图、提词备注、分段计时、排练记录、观众屏同步、激光笔；离线可用 |
| **汇报 / 报告 / 方案** | HTML 演示，可导出 PDF | 12 套主题；每页自动给出 3 个模板方案和 1 个定制方案，在浏览器里挑选和编辑，自动保存 |
| **交付可编辑的 PowerPoint** | 原生 .pptx | 文字、形状、图表都是 PowerPoint 原生对象，不是截图；支持套用品牌模板和母版 |
| **改造已有 PPT** | .pptx | 美化旧 PPT（文字和页序不变）、往已有模板里填新内容、只改部分页面 |
| **做模板** | 模板工作区 | 从 PPT、图片、PDF 或品牌素材里提炼出可复用的品牌、风格、版式模板 |
| **自动讲解视频** | .pptx 加 MP4 | 生成讲稿、配音、动画，导出可以自动播放的视频 |

还能直接读 PDF、Word、Excel、旧 PPT 和网页作为素材。素材不够时会补充调研；需要配图时可以 AI 生图或搜图。

---

## 架构

```
              用户需求（一句话 / 素材 / 大纲）
                          │
                ┌─────────▼──────────┐
                │  统一入口 Intake    │  只问缺的信息：先定格式，再定风格
                └─────────┬──────────┘  → 输出一份 Intake Brief
                          │
                ┌─────────▼──────────┐
                │  统一路由 Routing   │  格式优先，结果确定，不让用户在多套方案里挑
                └─────────┬──────────┘
      ┌────────────┬──────┴──────┬──────────────┬───────────────┐
      ▼            ▼             ▼              ▼               ▼
 HTML·Editorial HTML·Themed  Generate PPTX  Edit Native PPTX  Create Template
  演讲网页 PPT   主题汇报 PPT   新建 .pptx     改已有 .pptx      做模板
      │            │             │              │               │
      └────────────┴──────┬──────┴──────────────┴───────────────┘
                          ▼
          ┌──────────── 共享服务层 ─────────────┐
          │ 素材转换 · 主题调研 · 生图/搜图       │
          │ 截图美化 · 叙事模式 · 讲稿模型        │
          │ 统一验收（通过 / 待修正 / 阻塞）      │
          └─────────────────────────────────────┘
```

### 整合时解决的关键问题

1. **一个入口，不重复提问。** 原来三套工具各自有一套澄清问题。现在统一入口只负责定格式、定风格，其他问题交给各路线自己的确认环节，同一个问题不会问两遍。
2. **先定格式，再选引擎。** 原工具对"做个 PPT"的理解互相矛盾，有的默认网页，有的默认 .pptx。现在统一规则：信号明确就直接判定，说不清时只问一个问题，非交互环境用固定的默认值。
3. **风格可以跨引擎使用。** 所有风格放进一个目录：杂志风 5 套配色、瑞士风 4 套配色、主题 T01–T12，再加 .pptx 的模板库。想要"杂志风观感"但要交付 .pptx 时，会把这个风格的配色和字体作为设计要求交给 .pptx 引擎，不会拒绝，也不会悄悄换风格。
4. **能力共享。** 原来只有一个引擎能读 PDF/Word、做调研、生图，现在三条路线都能用。
5. **统一验收标准。** 每次生成都对照需求清单逐项核对，状态只有"通过 / 待修正 / 阻塞"，最多返工 2 轮，没达标不会说成完成。
6. **合规处理。** 移除了一个授权不允许整合进其他软件的专有导出组件，.pptx 统一由开源的原生引擎产出；各引擎保留原有许可证和署名（见 [`NOTICE.md`](skills/ppt-ultra/NOTICE.md)）。

---

## 快速开始

### 1. 安装

**方式 A：作为 Claude Code 插件安装（推荐）**

```text
/plugin marketplace add <GitHub用户名>/ppt-skill-ultra
/plugin install ppt-ultra@ppt-ultra
```

**方式 B：手动安装**

```bash
git clone https://github.com/<GitHub用户名>/ppt-skill-ultra.git
cp -R ppt-skill-ultra/skills/ppt-ultra ~/.claude/skills/ppt-ultra
```

### 2. 依赖（按需安装）

| 用到的路线 | 依赖 |
|---|---|
| 演讲网页 PPT（Editorial） | 只需要浏览器；校验脚本可选 Node.js |
| 主题汇报 PPT（Themed） | Node.js 20+ 和 npm；第一次生成时自动安装依赖 |
| .pptx 相关路线和共享服务 | Python 3.10–3.14：在 skill 目录下执行 `pip install -r requirements.txt` |
| AI 生图（可选） | 在 skill 目录下复制 `.env.example` 为 `.env`，填入生图服务的密钥 |

### 3. 使用示例

在 Claude Code 里直接说：

- "帮我做一个 20 分钟的 AI 行业观察分享，杂志风，要演讲者模式"
- "把这份 PDF 季度报告做成管理层汇报，用 theme05，导出 PDF"
- "用我们公司的 PPT 模板，做一份产品介绍，要可编辑的 PPTX"
- "把这个旧 PPT 美化一下，内容和页数不要动"
- "给这份 PPTX 加上讲稿和配音，导出成视频"

---

## 目录结构

```
ppt-skill-ultra/                     # 仓库根目录
├── README.md                        # 本文件
├── LICENSE                          # AGPL-3.0（项目整体许可证）
├── .claude-plugin/marketplace.json  # Claude Code 插件清单
└── skills/ppt-ultra/                # Skill 本体
    ├── SKILL.md                     # 唯一入口：加载顺序、路由表、全局执行纪律
    ├── NOTICE.md                    # 组成部分、许可证、上游合并步骤
    ├── LICENSE                      # PPTX 引擎（ppt-master）的 MIT 许可证，必须保留
    ├── workflows/
    │   ├── intake.md                # 统一入口（Stage 0）
    │   ├── routing.md               # 统一路由（§8 交付格式判定）
    │   ├── html-editorial.md        # 演讲网页 PPT 流程
    │   ├── html-themed.md           # 主题汇报 PPT 流程
    │   ├── generate-pptx.md …       # .pptx 生成、编辑、模板等流程
    │   └── stages/ profiles/        # 各路线的子阶段
    ├── references/                  # 共享服务目录、设计规范、视觉风格、叙事模式等
    ├── engines/
    │   ├── html-editorial/          # 网页 PPT 模板、版式库、演讲者运行时、校验器
    │   └── html-themed/             # 主题生成器、版式清单、预览编辑器
    ├── scripts/                     # .pptx 引擎和共享服务的工具链（Python）
    └── templates/                   # .pptx 模板库（品牌 / 风格 / 版式 / 整套）
```

---

## 致谢与许可

PPT Ultra 的底层引擎来自以下开源项目，在此致谢：

| 引擎 | 来源 | 许可证 |
|---|---|---|
| PPTX Native | [ppt-master](https://github.com/hugohe3/ppt-master)（Hugo He） | MIT |
| HTML Editorial | [guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill)（歸藏） | AGPL-3.0 |
| HTML Themed | dashi-ppt（chuspeeism），已移除其专有导出组件 | AGPL-3.0 |

项目整体按 [AGPL-3.0](LICENSE) 发布；各组成部分的许可证详见 [`NOTICE.md`](skills/ppt-ultra/NOTICE.md)。
