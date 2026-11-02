# PPT Ultra User Guide

**English** | [简体中文](USER_GUIDE.zh-CN.md)

For anyone making a presentation with AI for the first time. If you haven't installed the skill yet, follow the [install steps in the README](../README.md#install) first.

- [1. Tutorial](#1-tutorial)
- [2. FAQ](#2-faq)

---

## 1. Tutorial

### 1.1 Before you start

1. **Create an empty folder** as your workspace, e.g. `My Decks` on your desktop. All output goes here.
2. Open your AI tool in this folder:
   - Claude Code / Codex CLI: `cd` into the folder, then run `claude` or `codex`.
   - Desktop apps: choose this folder as the project folder.
3. Put any materials (PDF, Word, Excel, old decks, images) into the folder.

### 1.2 Describe what you need

Just write as you would to a colleague. The clearer you are, the fewer questions the AI asks:

```text
Make a presentation:
- Topic: AI industry trends in 2026
- Purpose: team sharing session on Friday, 20-minute live talk
- Material: "industry-report.pdf" in this folder
- Style: magazine
- With presenter mode
```

If something is missing, the AI asks at most **two questions**:

1. **Which format?** Web deck for a talk / report deck (PDF export) / editable .pptx
2. **Which style?** Magazine, Swiss, or one of 12 themes (T01–T12)

Not sure? Reply "you choose" and the AI recommends one based on your purpose.

### 1.3 The three outputs and how to use them

#### A. Web deck for talks (live talks, meetups)

- **Output**: a single `.html` file. Double-click to open it in a browser; it works offline.
- **Navigate**: arrow keys, Space, or the mouse wheel.
- **Presenter mode**: the AI tells you how to open it. Your screen shows speaker notes, the next slide and timers, while the projector shows only the slides. Common shortcuts:

  | Key | Action |
  |---|---|
  | `L` | Laser pointer |
  | `C` | Circle annotation |
  | `X` | Clear annotations |
  | `B` / `W` | Black / white audience screen |
  | `F` | Freeze / resume audience screen |
  | `A` | Auto-advance on / off |
  | `R` | Start / stop rehearsal timer |
  | `?` | Show all shortcuts |

- If animations stutter on a slower computer, follow the hint at the bottom-right to switch to static mode.

#### B. Themed report deck (reports, proposals, reviews)

- **Output**: the AI opens a preview page in your browser.
- **Pick variants**: every page has **4 versions** (3 template variants + 1 AI custom variant). Switch between them in the right-hand panel and select the one you like.
- **Edit content**: edit text directly on the page; changes save automatically.
- **Export PDF**: click **Export → PDF** on the preview page. The file is saved to your browser's downloads folder like any download. Export only works in the preview page the AI opened (address starts with `http://`), not in an HTML file opened by double-click.
- **HTML file**: `output/<project-name>/ppt/index.html` in your workspace.
- This route **does not export .pptx**. For .pptx, use route C.

#### C. Editable .pptx (to keep editing in PowerPoint / Keynote / WPS)

- During the process the AI may open a **confirmation page** in your browser to approve the design before continuing; just follow the on-page prompts.
- **Output**: `projects/<project-name>/exports/` in your workspace, named like `project-name_timestamp.pptx`.
- Text, shapes and charts are directly editable, not images.
- It can also:
  - **Use your company template**: "Use 'company-template.pptx' in this folder to make a product introduction."
  - **Beautify an old deck**: "Beautify 'old-proposal.pptx'; keep the content and page count unchanged."
  - **Edit a few slides**: "Turn slides 3 and 5 into charts."
  - **Make a narrated video**: "Add a script and voice-over to this deck and export it as a video."

#### D. Spec-driven .pptx (table- and chart-heavy reports; batch or non-interactive runs)

- **How to trigger**: say "use spec mode / build from a spec JSON", ask for a deterministic or reproducible deck, or simply hand over content that is mostly tables, several charts and flow / swimlane diagrams without designer-grade demands. The AI then uses the Spec Native engine.
- **Process**: the AI lists the facts and a page plan (confirmed once when interactive), writes a `spec.json`, validates it and builds the deck with one command in seconds.
- **Output**: `<project-dir>/spec.json` and `<project-dir>/<name>.pptx` in your workspace; text, tables, charts and diagrams are native objects you can keep editing.
- **Changes**: edits go into `spec.json` and the deck is rebuilt, so "turn slide 3 into a table" or "rename the title" takes seconds; you can also edit the spec yourself and ask the AI to rebuild.
- **Styles**: name a Magazine / Swiss palette or `theme01`–`theme12` and the AI applies that theme's palette to the spec (light themes only; dark themes are redirected to route C).
- **What it enforces**: charts whose values are all identical are rejected as placeholder data; `[1]`-style citation marks become superscripts and a References page is appended. For company masters or designer-grade layouts use route C.

### 1.4 Asking for changes

Tell the AI what you don't like, as specifically as possible:

- "Slide 3 has too much text; split it into two slides."
- "Switch the overall palette to blues."
- "Change the cover title to 'Leading the Future'."
- "Add a team introduction slide before the closing slide."

After each run the AI checks the result against your request item by item. The status is only **pass / needs fix / blocked**. If something falls short, it says why instead of pretending it's done.

### 1.5 Prompt template

Copy it and replace the parts in [brackets]:

```text
Make a presentation about [topic].
Purpose: [live talk / management briefing / send to clients / course handout]
Length: [15 minutes / about 10 slides]
Material: [xxx.pdf in this folder / the text below / please research it]
Format: [web deck / PDF / editable PPTX]
Style: [magazine / Swiss / theme05 / our company template / you choose]
Other: [speaker notes / images / data charts]
```

---

## 2. FAQ

**Q: The AI says it can't find the ppt-ultra skill.**
Check three things: ① you copied the `ppt-ultra` folder itself (you can see `SKILL.md` directly inside); ② it's in the right directory (see [Install](../README.md#install) in the README); ③ you restarted the AI tool after copying.

**Q: It says `python` / `node` command not found.**
The runtime isn't installed or wasn't added to PATH. Reinstall following [Step 0](../README.md#step-0-prerequisites-all-tools) in the README, then **reopen your terminal or AI tool**.

**Q: It reports a missing Python module (ModuleNotFoundError).**
Python dependencies aren't installed. Tell the AI "Install the Python dependencies for ppt-ultra", or run `pip install -r requirements.txt` in the skill folder.

**Q: The first themed report deck is very slow.**
The first run downloads Node.js dependencies, which can take a few minutes on a slow network; later runs are fast. In mainland China you can set a mirror first: `npm config set registry https://registry.npmmirror.com`.

**Q: "Export PDF" says a preview service is required.**
You opened the local file (address starts with `file://`). Ask the AI to "reopen the preview page" and export from the `http://` address it gives you.

**Q: Which routes can export .pptx?**
Routes C (editable .pptx) and D (spec-driven .pptx). Routes A and B deliver HTML and PDF. If you want a web-deck style as .pptx, just say "a magazine-style PPTX" and the AI hands the style to the .pptx engine. Route D needs Graphviz (`dot`) only for flow / swimlane / hierarchy pages; everything else works with the Python dependencies alone.

**Q: Is the generated content accurate?**
The AI sticks to the materials you provide as much as possible. Double-check key facts such as figures, dates and names before sharing.

**Q: Does it cost anything?**
PPT Ultra itself is free and open source (AGPL-3.0). Costs come from the AI tool or model service you use, plus any optional image service.

**Q: How do I update to a new version?**
Plugin install: type `/plugin` in Claude Code and update from the plugin manager. Manual install: download again, delete the old `ppt-ultra` folder, and copy in the new one.
