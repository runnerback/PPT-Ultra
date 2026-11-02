<div align="center">

**English** | [简体中文](README.zh-CN.md)

# PPT Ultra

**Turn a one-line request into a ready-to-use presentation: a web deck for live talks, a themed report deck, or a natively editable .pptx.**

[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.2.0-brightgreen.svg)](https://github.com/runnerback/PPT-Ultra/releases)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-8A2BE2.svg)](skills/ppt-ultra/SKILL.md)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757.svg)](#claude-code)
[![Python](https://img.shields.io/badge/python-3.10--3.14-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/node-%E2%89%A520-339933.svg?logo=node.js&logoColor=white)](https://nodejs.org)
[![GitHub stars](https://img.shields.io/github/stars/runnerback/PPT-Ultra?style=social)](https://github.com/runnerback/PPT-Ultra)

[Install](#install) · [Usage](#usage) · [User Guide](docs/USER_GUIDE.md) · [Architecture](#architecture) · [Credits & License](#credits--license)

</div>

PPT Ultra is an Agent Skill that plugs into AI tools able to work on your computer, such as Claude Code, Codex and WorkBuddy. It merges three mature open-source PPT generators into **one entry point and one workflow**. You don't need to know which engine runs underneath: just say what you need and how it will be used, and the skill picks the route and style, generates the deck, and checks the result.

> Integration & architecture: Runnerback <286980573@163.com> · Version 1.0.0

---

## What it does

| Scenario | Output | Highlights |
|---|---|---|
| **Live talks / launches / meetups** | Single-file HTML web deck | Magazine or Swiss International style; presenter view, speaker notes, section timers, rehearsal log, audience-screen sync, laser pointer; works offline |
| **Reports / proposals / reviews** | HTML deck, exportable to PDF | 12 themes; every page gets 3 template variants plus 1 custom variant to pick and edit in the browser, with autosave |
| **Editable PowerPoint** | Native .pptx | Text, shapes and charts are native PowerPoint objects, not screenshots; supports brand templates and slide masters |
| **Data-dense reports, batch or non-interactive runs** | Native .pptx | Spec Native engine: one spec JSON builds the whole deck in seconds; 31 layouts, 9 native chart types, auto-laid flow / swimlane / sequence diagrams, citation superscripts with a references page; deterministic, rebuild by editing the JSON |
| **Rework an existing deck** | .pptx | Beautify an old deck (text and slide order unchanged), fill an existing template with new content, or edit selected slides only |
| **Build templates** | Template workspace | Extract reusable brand, style and layout templates from decks, images, PDFs or brand assets |
| **Narrated video** | .pptx + MP4 | Generate a script, voice-over and animations, then export a self-playing video |

It reads PDF, Word, Excel, existing decks and web pages as source material. When material is thin it can research the topic, and it can generate or search for images.

---

## Install

PPT Ultra must run inside an AI tool that can **read and write files and run commands**, because the AI generates the deck on your computer. Chat-only AI cannot use it.

> [!TIP]
> **Too many steps? Let your AI install it for you.**
>
> Open any supported tool from the table below, then paste one of these prompts into the chat:
>
> - **Haven't downloaded anything** (the AI fetches it from GitHub):
>   ```text
>   Please install the AI skill from https://github.com/runnerback/PPT-Ultra for me: put the skills/ppt-ultra folder into your skills directory, install the Python and Node.js runtimes and dependencies it needs, then confirm the skill is loaded and tell me how to use it.
>   ```
> - **Already downloaded the ZIP**: drag the ZIP or the unzipped folder into the chat, then send:
>   ```text
>   This is the PPT Ultra skill package. Please install it for me: unzip it if needed, put the skills/ppt-ultra folder into your skills directory, install the Python and Node.js runtimes and dependencies it needs, then confirm the skill is loaded and tell me how to use it.
>   ```
>
> The AI finds the right directory, copies the files and installs dependencies on its own. When it asks for permission to run a command, approve it. Some tools need a restart before a new skill shows up; the AI will tell you. If it gets stuck, fall back to the manual steps below.

Find your tool and jump to its steps:

| AI tool | Support | Steps |
|---|---|---|
| **Claude Code** (terminal / desktop app / VS Code) | ✅ Full, recommended | [Go](#claude-code) |
| **Claude Code + Doubao model** (Volcano Engine Ark) | ✅ Full, recommended in mainland China | [Go](#claude-code--doubao-volcano-engine-ark) |
| **Codex** (by OpenAI, sign in with ChatGPT) | ✅ Compatible | [Go](#codex-chatgpt-users) |
| **WorkBuddy** (Tencent) | ✅ Compatible | [Go](#workbuddy-tencent) |
| **Doubao desktop app** (Office Tasks mode) | ⚠️ Worth a try | [Go](#doubao-desktop-app) |
| **ChatGPT web / app** | ❌ Not recommended | Skill upload is limited to workplace plans with a ~25 MB package limit; this skill is ~48 MB. The cloud sandbox also can't open local previews. **Use Codex instead** |
| **Doubao web / mobile** and other chat-only tools | ❌ Not supported | Can't run scripts on your machine |

> Except for Claude Code, the install steps below come from each tool's public docs and have not all been tested by the author; menus and paths may change between versions. Please open an [Issue](https://github.com/runnerback/PPT-Ultra/issues) if something doesn't work. Output quality depends on the model: the stronger the model, the more complete the result.

### Step 0: Prerequisites (all tools)

**1. Download the skill** (skip if you install the Claude Code plugin)

- Without git: click the green **Code** button at the top of this page → **Download ZIP**, then unzip.
- With git: `git clone https://github.com/runnerback/PPT-Ultra.git`

The skill is the **`skills/ppt-ultra` folder** inside (you'll see `SKILL.md` directly in it). Installing means copying this folder into your tool's skills directory.

**2. Install runtimes** (by deck type; if unsure, install all)

| You want | Install |
|---|---|
| Web deck for live talks | Just a browser |
| Themed report deck (PDF export) | [Node.js](https://nodejs.org) 20+ (LTS); dependencies install automatically on first run |
| Editable .pptx | [Python](https://www.python.org/downloads/) 3.10 – 3.14 (on Windows, tick **Add Python to PATH**) |

**3. Python dependencies** (only for .pptx)

Once the skill is installed, tell the AI: "**Check and install the dependencies for the ppt-ultra skill.**" Or manually, inside the skill folder: `pip install -r requirements.txt`.

**4. AI image generation (optional)**: copy `.env.example` in the skill folder to `.env` and fill in your image-service API key. Everything works without it.

> `~` below means your home folder (macOS: `/Users/<you>`, Windows: `C:\Users\<you>`). Folders starting with `.` are hidden by default: press `Cmd + Shift + .` in macOS Finder, or enable "Hidden items" under View in Windows Explorer.

### Claude Code

1. **Install Claude Code**: get the [desktop app](https://claude.com/download), or run `npm install -g @anthropic-ai/claude-code` in a terminal, then run `claude` and sign in.
2. **Install PPT Ultra**, either way:

   **Option A: plugin (recommended, easy to update).** In Claude Code, enter:

   ```text
   /plugin marketplace add runnerback/PPT-Ultra
   /plugin install ppt-ultra@ppt-ultra
   ```

   **Option B: copy manually** into `~/.claude/skills/`:

   ```bash
   # macOS / Linux
   mkdir -p ~/.claude/skills && cp -R PPT-Ultra/skills/ppt-ultra ~/.claude/skills/

   # Windows (PowerShell)
   New-Item -ItemType Directory -Force "$HOME\.claude\skills"
   Copy-Item -Recurse PPT-Ultra\skills\ppt-ultra "$HOME\.claude\skills\"
   ```

3. **Verify**: restart Claude Code and ask "Do you have the ppt-ultra skill?" If it describes the skill, you're set.

### Claude Code + Doubao (Volcano Engine Ark)

No Claude account? Use Claude Code as the tool and ByteDance's Doubao coding model as the brain.

1. Install Claude Code and PPT Ultra as in the previous section.
2. Subscribe to the **Coding Plan** on [Volcano Engine Ark](https://www.volcengine.com/product/ark) and get an API key.
3. Set environment variables (macOS: add to `~/.zshrc`; Windows: add under System Environment Variables):

   ```bash
   export ANTHROPIC_BASE_URL="https://ark.cn-beijing.volces.com/api/coding"
   export ANTHROPIC_AUTH_TOKEN="<your Ark API key>"
   export ANTHROPIC_MODEL="ark-code-latest"
   ```

4. Open a new terminal and run `claude`.

> Ark also offers a one-click setup tool, Ark Helper (macOS / Linux for now). Use the `/api/coding` endpoint; `/api/v3` bypasses the plan quota and is billed separately. Outside mainland China, BytePlus ModelArk offers the same service. Check the [official Ark docs](https://www.volcengine.com/docs/82379) for current endpoints and model names.

### Codex (ChatGPT users)

1. **Install Codex and sign in** (requires Node.js): `npm install -g @openai/codex`, then run `codex` and sign in with your ChatGPT account.
2. **Copy the skill** into `~/.codex/skills/`:

   ```bash
   # macOS / Linux
   mkdir -p ~/.codex/skills && cp -R PPT-Ultra/skills/ppt-ultra ~/.codex/skills/

   # Windows (PowerShell)
   New-Item -ItemType Directory -Force "$HOME\.codex\skills"
   Copy-Item -Recurse PPT-Ultra\skills\ppt-ultra "$HOME\.codex\skills\"
   ```

3. **Verify**: restart Codex and ask "Do you have the ppt-ultra skill?"

### WorkBuddy (Tencent)

Either way:

- **Import in chat**: type "导入技能" (import skill) in the chat box and select the `ppt-ultra` folder (or drag in its `SKILL.md`).
- **Copy manually**: copy the `ppt-ultra` folder into `~/.workbuddy/skills/` and restart WorkBuddy.

Entry points may differ between versions; follow WorkBuddy's Skills menu.

### Doubao desktop app

The "办公任务" (Office Tasks) mode supports local skills, but there is no official install guide yet. These steps come from community sources:

1. Open the Doubao desktop app and switch to **"办公任务"** mode.
2. Type `/创建技能` (create skill) to create any test skill, and note which folder it is saved in (reportedly `~/.agents/skills`).
3. Copy the `ppt-ultra` folder into that same folder and restart Doubao.

If you can't find the skills entry, your account or version may not support it; use [Claude Code + Doubao](#claude-code--doubao-volcano-engine-ark) instead.

---

## Usage

1. **Create an empty folder** as your workspace, put your materials in it (PDF, Word, Excel, old decks, images), and open your AI tool in that folder.
2. **Describe what you need** in plain language. The clearer you are, the fewer questions the AI asks. If something is missing, it asks at most two: which format, and which style.
3. **Get the result**: the web deck is a single `.html` file; the themed report opens in a browser preview where you pick variants and export PDF; the editable .pptx lands in `projects/<project-name>/exports/`.

Examples (any language works):

- "Make a 20-minute talk on AI industry trends, magazine style, with presenter mode."
- "Turn this quarterly report PDF into a management briefing using theme05, and export PDF."
- "Use our company PPT template to make a product introduction as an editable PPTX."
- "Beautify this old deck; keep the content and page count unchanged."
- "Add a script and voice-over to this PPTX and export it as a video."

> 📖 **Full tutorial: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)**: how to use each output, presenter shortcuts, how to request changes, a prompt template, and FAQ.

---

## Architecture

```
            User request (one line / materials / outline)
                              │
                   ┌──────────▼──────────┐
                   │   Unified Intake    │  asks only what's missing: format first, then style
                   └──────────┬──────────┘  → produces an Intake Brief
                              │
                   ┌──────────▼──────────┐
                   │   Unified Routing   │  format-first, deterministic; no menu of engines
                   └──────────┬──────────┘
      ┌─────────────┬─────────┴────┬───────────────┬────────────────┐
      ▼             ▼              ▼               ▼                ▼
HTML·Editorial  HTML·Themed   Generate PPTX  Edit Native PPTX  Create Template
 talk web deck  report deck     new .pptx    edit .pptx        build templates
      │             │              │               │                │
      └─────────────┴─────────┬────┴───────────────┴────────────────┘
                              ▼
            ┌─────────────── Shared services ───────────────┐
            │ source conversion · topic research · images   │
            │ screenshot framing · narrative modes · notes  │
            │ acceptance: pass / needs fix / blocked       │
            └───────────────────────────────────────────────┘
```

### Key problems solved in the merge

1. **One entry point, no repeated questions.** Each original tool had its own clarifying questions. Intake now only settles format and style; everything else goes to each route's own confirmation step, so nothing is asked twice.
2. **Format first, then engine.** The originals disagreed on what "make a PPT" means: some defaulted to web, others to .pptx. Now clear signals decide directly, an unclear request gets exactly one question, and non-interactive runs use fixed defaults.
3. **Styles work across engines.** All styles live in one catalog: 5 magazine palettes, 4 Swiss palettes, themes T01–T12, plus the .pptx template library. If you want a magazine look delivered as .pptx, the style's colors and fonts are handed to the .pptx engine as a design brief, instead of refusing or silently switching styles.
4. **Shared capabilities.** Reading PDF/Word, research and image generation used to exist in one engine only; now all three routes can use them.
5. **One acceptance standard.** Every run is checked item by item against the request. The status is only "pass / needs fix / blocked", with at most 2 rework rounds; nothing is reported as done unless it meets the bar.
6. **License compliance.** A proprietary export component whose license forbids use in other software was removed; .pptx output comes only from the open-source native engine. Each engine keeps its original license and attribution (see [`NOTICE.md`](skills/ppt-ultra/NOTICE.md)).
7. **A deterministic route (1.1.0).** The three original tools all need the model to author every page's visual layout for .pptx, which costs tokens, time and confirmation rounds. The new Spec Native engine lets the model write only each page's semantics (layout name plus content fields) while the engine computes every coordinate; one command builds the deck in seconds, and charts without real variance are rejected. Built for table- and chart-heavy reports, batch generation and hosts that cannot ask follow-up questions. See [`engines/spec-native/README.md`](skills/ppt-ultra/engines/spec-native/README.md).

---

## Repository layout

```
PPT-Ultra/                           # repository root
├── README.md                        # English README (this file)
├── README.zh-CN.md                  # Chinese README
├── LICENSE                          # AGPL-3.0 (project license)
├── .claude-plugin/marketplace.json  # Claude Code plugin manifest
├── docs/USER_GUIDE(.zh-CN).md       # detailed tutorial and FAQ (EN / ZH)
├── tools/smoke.sh                   # maintainer smoke test: integrity gate + Spec Native examples + validators
├── tools/upstream-check.sh          # maintainer: compare the three upstreams against tools/upstream-pins.json
├── tools/build-style-briefs.mjs     # maintainer: regenerate references/style-briefs/themes.json from the engines' own theme sources
│   └── skills/ppt-ultra/host/       # host contract (1.2.0): brief.schema.json, build_prompt.py, collect_manifest.py for bots / pipelines; deliverable pptx (host-quick) or html (host-editorial)
└── skills/ppt-ultra/                # the skill itself
    ├── SKILL.md                     # single entry: load order, route table, global rules
    ├── NOTICE.md                    # components, licenses, upstream merge steps
    ├── LICENSE                      # MIT license of the PPTX engine (ppt-master); must be kept
    ├── workflows/
    │   ├── intake.md                # unified intake (Stage 0)
    │   ├── routing.md               # unified routing (§8 delivery format)
    │   ├── html-editorial.md        # talk web deck workflow
    │   ├── html-themed.md           # themed report deck workflow
    │   ├── generate-pptx.md …       # .pptx generate / edit / template workflows
    │   └── stages/ profiles/        # per-route sub-stages
    ├── references/                  # shared services, design specs, visual styles, narrative modes
    ├── engines/
    │   ├── html-editorial/          # web deck templates, layouts, presenter runtime, validators
    │   ├── html-themed/             # theme generator, layout manifest, preview editor
    │   └── spec-native/             # spec JSON → native PPTX deterministic engine (MIT, new in this repo)
    ├── scripts/                     # .pptx engine and shared-service toolchain (Python)
    └── templates/                   # .pptx template library (brand / style / layout / full decks)
```

---

## Credits & License

PPT Ultra is built on these open-source projects, with thanks:

| Engine | Source | License |
|---|---|---|
| PPTX Native | [ppt-master](https://github.com/hugohe3/ppt-master) (Hugo He) | MIT |
| HTML Editorial | [guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) (歸藏 / op7418) | AGPL-3.0 |
| HTML Themed | [dashi-ppt-skill](https://github.com/chuspeeism/dashi-ppt-skill) (chuspeeism), with its proprietary export component removed | AGPL-3.0 |
| Spec Native | New in this repository (Runnerback), extracted from the author's in-house AI-agent deck pipeline | MIT |

The project as a whole is released under [AGPL-3.0](LICENSE); see [`NOTICE.md`](skills/ppt-ultra/NOTICE.md) for each component's license.
