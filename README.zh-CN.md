<div align="center">

[English](README.md) | **简体中文**

# PPT Ultra

**一句话需求，生成可以直接用的演示文稿：网页演讲 PPT、主题化汇报 PPT，或原生可编辑的 .pptx。**

[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.1-brightgreen.svg)](https://github.com/runnerback/PPT-Ultra/releases)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-8A2BE2.svg)](skills/ppt-ultra/SKILL.md)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757.svg)](#claude-code)
[![Python](https://img.shields.io/badge/python-3.10--3.14-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/node-%E2%89%A520-339933.svg?logo=node.js&logoColor=white)](https://nodejs.org)
[![GitHub stars](https://img.shields.io/github/stars/runnerback/PPT-Ultra?style=social)](https://github.com/runnerback/PPT-Ultra)

[安装](#安装) · [使用](#使用) · [使用指南](docs/USER_GUIDE.zh-CN.md) · [架构](#架构) · [致谢与许可](#致谢与许可)

</div>

PPT Ultra 是一个 Agent Skill（技能包），可以装进 Claude Code、Codex、WorkBuddy 等能操作电脑的 AI 工具。它把三套成熟的开源 PPT 生成能力，加上一套自研的规格驱动确定性 PPTX 引擎，整合成**一个入口、一套流程**。用户不用关心底层用哪个引擎，只要说清楚"要什么、怎么用"，Skill 会自动选路线、选风格，生成后再做验收。

> 整合与架构设计：Runnerback <286980573@163.com> · 版本 1.1.1

---

## 能做什么

| 场景 | 交付物 | 亮点 |
|---|---|---|
| **现场演讲 / 发布会 / 分享会** | 单文件 HTML 网页 PPT | 杂志风或瑞士国际主义风；演讲者视图、提词备注、分段计时、排练记录、观众屏同步、激光笔；离线可用 |
| **汇报 / 报告 / 方案** | HTML 演示，可导出 PDF | 12 套主题；每页自动给出 3 个模板方案和 1 个定制方案，在浏览器里挑选和编辑，自动保存 |
| **交付可编辑的 PowerPoint** | 原生 .pptx | 文字、形状、图表都是 PowerPoint 原生对象，不是截图；支持套用品牌模板和母版 |
| **数据密集的常规汇报 / 批量或非交互生成** | 原生 .pptx | Spec Native 引擎：一份规格 JSON 一次成片，31 种版式、9 种原生图表、流程 / 泳道 / 时序自动布局、出处角标与引用页；确定性、秒级，改 JSON 重出 |
| **改造已有 PPT** | .pptx | 美化旧 PPT（文字和页序不变）、往已有模板里填新内容、只改部分页面 |
| **做模板** | 模板工作区 | 从 PPT、图片、PDF 或品牌素材里提炼出可复用的品牌、风格、版式模板 |
| **自动讲解视频** | .pptx 加 MP4 | 生成讲稿、配音、动画，导出可以自动播放的视频 |

还能直接读 PDF、Word、Excel、旧 PPT 和网页作为素材。素材不够时会补充调研；需要配图时可以 AI 生图或搜图。

---

## 安装

PPT Ultra 需要装进**能读写文件、运行命令**的 AI 工具里，由 AI 在你的电脑上生成 PPT 文件。只能聊天的 AI 用不了它。

> [!TIP]
> **嫌下面的步骤麻烦？让你的 AI 帮你装。**
>
> 打开下表中任意一个支持的 AI 工具，把下面一段话复制进对话框：
>
> - **还没下载**（AI 会自己从 GitHub 获取）：
>   ```text
>   请帮我安装这个 AI 技能：https://github.com/runnerback/PPT-Ultra 。把其中的 skills/ppt-ultra 文件夹放进你的技能目录，安装它需要的 Python、Node.js 运行环境和依赖，最后确认技能已加载，并告诉我怎么使用。
>   ```
> - **已经下载了 ZIP**：把压缩包或解压后的文件夹直接拖进对话框，再发送：
>   ```text
>   这是 PPT Ultra 技能包，请帮我安装：需要的话先解压，把其中的 skills/ppt-ultra 文件夹放进你的技能目录，安装它需要的 Python、Node.js 运行环境和依赖，最后确认技能已加载，并告诉我怎么使用。
>   ```
>
> AI 会自己找到正确的目录、复制文件、安装依赖。过程中它请求执行命令时，点"允许"即可。有些工具装完新技能要重启才能识别，AI 会提醒你。如果它卡住了，再按下面的手动步骤操作。

找到你用的工具，点链接直接跳到对应的安装步骤：

| AI 工具 | 支持程度 | 安装步骤 |
|---|---|---|
| **Claude Code**（终端 / 桌面 App / VS Code） | ✅ 完整支持，推荐 | [跳转](#claude-code) |
| **Claude Code + 豆包模型**（火山方舟） | ✅ 完整支持，国内用户推荐 | [跳转](#claude-code--豆包模型火山方舟) |
| **Codex**（OpenAI 出品，ChatGPT 账号登录） | ✅ 兼容 | [跳转](#codexchatgpt-用户) |
| **WorkBuddy**（腾讯） | ✅ 兼容 | [跳转](#workbuddy腾讯) |
| **豆包电脑版**（办公任务模式） | ⚠️ 可以尝试 | [跳转](#豆包电脑版) |
| **ChatGPT 网页版 / App** | ❌ 不推荐 | 只有企业类套餐能上传技能，上传包约限 25MB，本技能包约 48MB 超限；云端也开不了本地预览。**请改用 Codex** |
| **豆包网页版 / 手机 App** 等纯聊天工具 | ❌ 不支持 | 不能在本机运行脚本 |

> 除 Claude Code 外，其他工具的安装方式来自各工具的公开资料，作者没有逐一实测，界面和路径可能随版本变化。遇到问题欢迎提 [Issue](https://github.com/runnerback/PPT-Ultra/issues)。生成质量和所用模型有关，模型能力越强，完成度越高。

### 第 0 步：准备工作（所有工具通用）

**1. 下载技能包**（插件方式安装 Claude Code 的可以跳过）

- 不会用 git：点本页上方绿色的 **Code** 按钮 → **Download ZIP**，解压。
- 会用 git：`git clone https://github.com/runnerback/PPT-Ultra.git`

技能包是里面的 **`skills/ppt-ultra` 文件夹**（打开能直接看到 `SKILL.md`）。下文的安装就是把这个文件夹复制到各工具的技能目录。

**2. 安装运行环境**（按要做的 PPT 类型安装，不确定就全装）

| 你要做的 | 需要安装 |
|---|---|
| 演讲用的网页 PPT | 只要一个浏览器 |
| 主题汇报 PPT（可导出 PDF） | [Node.js](https://nodejs.org) 20 或更高版本（选 LTS）；依赖在第一次生成时自动安装 |
| 可编辑的 .pptx | [Python](https://www.python.org/downloads/) 3.10 – 3.14（Windows 安装时勾选 **Add Python to PATH**） |

**3. 安装 Python 依赖**（做 .pptx 才需要）

技能装好后对 AI 说"**帮我检查并安装 ppt-ultra 需要的依赖**"即可。手动安装：在技能包目录执行 `pip install -r requirements.txt`。

**4. AI 生图（可选）**：把技能包目录里的 `.env.example` 复制为 `.env`，填入生图服务的密钥。不配置也能用。

> 下文路径里的 `~` 指用户文件夹（macOS：`/Users/你的用户名`，Windows：`C:\Users\你的用户名`）。`.` 开头的文件夹默认隐藏：macOS 访达按 `Cmd + Shift + .` 显示，Windows 资源管理器"查看"里勾选"隐藏的项目"。

### Claude Code

1. **安装 Claude Code**：下载 [桌面 App](https://claude.com/download)，或在终端运行 `npm install -g @anthropic-ai/claude-code`，然后运行 `claude` 登录。
2. **安装 PPT Ultra**，任选一种：

   **方式 A：插件安装（推荐，方便以后更新）**。在 Claude Code 对话框里依次输入：

   ```text
   /plugin marketplace add runnerback/PPT-Ultra
   /plugin install ppt-ultra@ppt-ultra
   ```

   **方式 B：手动复制**到 `~/.claude/skills/`：

   ```bash
   # macOS / Linux
   mkdir -p ~/.claude/skills && cp -R PPT-Ultra/skills/ppt-ultra ~/.claude/skills/

   # Windows（PowerShell）
   New-Item -ItemType Directory -Force "$HOME\.claude\skills"
   Copy-Item -Recurse PPT-Ultra\skills\ppt-ultra "$HOME\.claude\skills\"
   ```

3. **验证**：重启 Claude Code，问"你有 ppt-ultra 技能吗？"，能介绍功能就是装好了。

### Claude Code + 豆包模型（火山方舟）

没有 Claude 账号时，用 Claude Code 当"工具"，豆包编程模型当"大脑"。

1. 按上一节装好 Claude Code 和 PPT Ultra。
2. 在 [火山方舟](https://www.volcengine.com/product/ark) 开通 **Coding Plan**，获取 API Key。
3. 设置环境变量（macOS 写进 `~/.zshrc`；Windows 在"系统环境变量"里添加）：

   ```bash
   export ANTHROPIC_BASE_URL="https://ark.cn-beijing.volces.com/api/coding"
   export ANTHROPIC_AUTH_TOKEN="你的火山方舟 API Key"
   export ANTHROPIC_MODEL="ark-code-latest"
   ```

4. 重新打开终端，运行 `claude`。

> 火山方舟也提供一键配置工具 Ark Helper（目前支持 macOS / Linux）。请使用 `/api/coding` 地址，`/api/v3` 不走套餐额度，会额外计费。地址和模型名以 [火山方舟官方文档](https://www.volcengine.com/docs/82379) 为准。

### Codex（ChatGPT 用户）

1. **安装 Codex 并登录**（需要先装 Node.js）：`npm install -g @openai/codex`，然后运行 `codex`，用 ChatGPT 账号登录。
2. **复制技能包**到 `~/.codex/skills/`：

   ```bash
   # macOS / Linux
   mkdir -p ~/.codex/skills && cp -R PPT-Ultra/skills/ppt-ultra ~/.codex/skills/

   # Windows（PowerShell）
   New-Item -ItemType Directory -Force "$HOME\.codex\skills"
   Copy-Item -Recurse PPT-Ultra\skills\ppt-ultra "$HOME\.codex\skills\"
   ```

3. **验证**：重启 Codex，问"你有 ppt-ultra 技能吗？"。

### WorkBuddy（腾讯）

任选一种：

- **对话导入**：在聊天框输入"导入技能"，按提示选择 `ppt-ultra` 文件夹（或拖入其中的 `SKILL.md`）。
- **手动放置**：把 `ppt-ultra` 文件夹复制到 `~/.workbuddy/skills/`，重启 WorkBuddy。

不同版本入口可能不同，以 WorkBuddy"技能"菜单为准。

### 豆包电脑版

"办公任务"模式支持本地技能，但官方没有公开安装文档，以下做法来自网络资料：

1. 打开豆包电脑版，切换到 **"办公任务"** 模式。
2. 输入 `/创建技能` 随便建一个测试技能，看它保存在哪个文件夹（网络资料显示通常是 `~/.agents/skills`）。
3. 把 `ppt-ultra` 文件夹复制到同一个文件夹，重启豆包。

找不到技能入口时，可能当前账号或版本不支持，建议改用 [Claude Code + 豆包模型](#claude-code--豆包模型火山方舟)。

---

## 使用

1. **新建一个空文件夹**当工作目录，把素材（PDF、Word、Excel、旧 PPT、图片）放进去，在这个文件夹里打开 AI 工具。
2. **直接说需求**，说得越清楚 AI 问得越少。信息不全时，AI 最多问两个问题：做成什么格式、用什么风格。
3. **拿到成品**：网页 PPT 是一个 `.html` 文件；主题汇报在浏览器预览页里挑方案、导出 PDF；可编辑 PPTX 在 `projects/<项目名>/exports/` 里。

示例：

- "帮我做一个 20 分钟的 AI 行业观察分享，杂志风，要演讲者模式"
- "把这份 PDF 季度报告做成管理层汇报，用 theme05，导出 PDF"
- "用我们公司的 PPT 模板，做一份产品介绍，要可编辑的 PPTX"
- "把这个旧 PPT 美化一下，内容和页数不要动"
- "给这份 PPTX 加上讲稿和配音，导出成视频"

> 📖 **详细教程见 [docs/USER_GUIDE.zh-CN.md](docs/USER_GUIDE.zh-CN.md)**：三种成品的用法、演讲者模式快捷键、怎么修改、提示词模板和常见问题。

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
7. **多了一条确定性路线（1.1.0）。** 原来三套工具做 .pptx 都要模型逐页创作版面，token 多、耗时长、需要多轮确认。新增的 Spec Native 引擎让模型只写每页的语义（版式 + 内容字段），坐标全由程序算，一条命令秒级出片，数值没有区分度的图表会被直接拒绝；适合表格和图表多的常规汇报、批量生成和不能追问的运行环境。详见 [`engines/spec-native/README.md`](skills/ppt-ultra/engines/spec-native/README.md)。

---

## 目录结构

```
PPT-Ultra/                           # 仓库根目录
├── README.md                        # 英文说明
├── README.zh-CN.md                  # 中文说明（本文件）
├── LICENSE                          # AGPL-3.0（项目整体许可证）
├── .claude-plugin/marketplace.json  # Claude Code 插件清单
├── docs/USER_GUIDE(.zh-CN).md       # 详细使用教程和常见问题（英 / 中）
├── tools/smoke.sh                   # 维护者冒烟：完整性检查 + Spec Native 示例构建 + 校验器
├── tools/upstream-check.sh          # 维护者：对照 tools/upstream-pins.json 查三上游是否有新版本
├── tools/build-style-briefs.mjs     # 维护者：从三个引擎的主题真值生成 references/style-briefs/themes.json
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
    │   ├── html-themed/             # 主题生成器、版式清单、预览编辑器
    │   └── spec-native/             # 规格 JSON → 原生 PPTX 确定性引擎（MIT，本仓库新增）
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
| HTML Themed | [dashi-ppt-skill](https://github.com/chuspeeism/dashi-ppt-skill)（chuspeeism），已移除其专有导出组件 | AGPL-3.0 |
| Spec Native | 本仓库新增（Runnerback），源自作者在企业内运行的 Agent 制作 PPT 管线 | MIT |

项目整体按 [AGPL-3.0](LICENSE) 发布；各组成部分的许可证详见 [`NOTICE.md`](skills/ppt-ultra/NOTICE.md)。
