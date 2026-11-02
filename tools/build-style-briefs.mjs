#!/usr/bin/env node
// 生成跨引擎风格 brief 表 skills/ppt-ultra/references/style-briefs/themes.json（2026-11-02，PPT Ultra 1.1.1）。
// 来源（都是引擎自己的真值，不手抄）：
//   - Editorial 杂志 / 瑞士主题：engines/html-editorial/references/themes.md、themes-swiss.md 的主题表（paper / ink / accent / accent-ink / accent-on）
//   - Themed 12 主题：engines/html-themed/project/src/components/bespoke/theme-profiles.mjs（bg / surface / ink / muted / accent / accent2 / line / 字体 / 图表系列色）
//     + engines/html-themed/references/options.md 的名称 / 适合 / 人群
//   - Spec Native 默认调色板：engines/spec-native/pptx_style.py 的 C
// 每个主题给出三种消费方式：html（本引擎怎么选它）、native_style_brief（Native 路线 Stage 1 / Quick 的风格 brief 字段）、
// spec_style（Spec profile 直接填进 spec.style；暗底主题为 null 并写明原因——Spec 引擎是白卡浅底设计系统）。
// 用法：node tools/build-style-briefs.mjs            写文件
//       node tools/build-style-briefs.mjs --check    只比对，不一致退出码 1（smoke.sh 用）
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SKILL = path.join(ROOT, 'skills/ppt-ultra')
const OUT = path.join(SKILL, 'references/style-briefs/themes.json')
const read = (p) => fs.readFileSync(path.join(SKILL, p), 'utf8')

// ---- 颜色工具 ----
const hex6 = (s) => {
  const m = String(s).trim().match(/#?([0-9a-fA-F]{6})\b/)
  if (!m) throw new Error(`不是 6 位十六进制颜色：${s}`)
  return m[1].toUpperCase()
}
const firstHex = (s) => { const m = String(s).match(/#([0-9a-fA-F]{6})\b/); return m ? m[1].toUpperCase() : null }
const rgb = (h) => [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16))
const toHex = (c) => c.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('').toUpperCase()
const mix = (a, b, t) => toHex(rgb(a).map((v, i) => v + (rgb(b)[i] - v) * t))   // t=0 → a，t=1 → b
const lum = (h) => { const [r, g, b] = rgb(h).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }); return 0.2126 * r + 0.7152 * g + 0.0722 * b }
const isWarm = (h) => { const [r, g, b] = rgb(h); return r > g && r > b && r - b > 60 }

// Spec 引擎调色板派生：主色必须能当文字 / 色块用（亮度太高就换 accent_ink），其余按主色与墨色调出浅底 / 边框 / 灰阶
function specPalette({ accent, accentInk, accent2, ink, paper, muted }) {
  const primary = lum(accent) > 0.45 ? (accentInk || mix(accent, '000000', 0.45)) : accent
  const secondary = accent2 && lum(accent2) <= 0.45 && accent2 !== primary ? accent2 : mix(primary, 'FFFFFF', 0.25)
  return {
    primary, secondary,
    pale: mix(primary, 'FFFFFF', 0.88), fill: mix(primary, 'FFFFFF', 0.94),
    red: 'C00000', ink, gray: mix(ink, 'FFFFFF', 0.2), mid: muted || mix(ink, 'FFFFFF', 0.55),
    border: mix(ink, 'FFFFFF', 0.82), white: 'FFFFFF', bg: paper,
    gold: accent2 && isWarm(accent2) ? mix(accent2, 'FFFFFF', 0.6) : 'F3DFA2',
  }
}

// ---- Editorial：解析两份主题 md ----
function parseEditorial(file, family) {
  const text = read(`engines/html-editorial/references/${file}`)
  const out = {}
  const blocks = text.split(/^## /m).slice(1)
  for (const b of blocks) {
    const head = b.match(/^(?:\S+\s+)?(.+?)\s+·\s+`([a-z0-9-]+)`/)
    if (!head) continue
    const [, name, id] = head
    const fit = (b.match(/\*\*适合\*\*[：:]\s*(.+)/) || [])[1]?.trim() || ''
    const tone = (b.match(/\*\*调性\*\*[：:]\s*(.+)/) || [])[1]?.trim() || ''
    const row = b.match(/^\|\s*`(#[0-9a-fA-F]{6})`\s*\|\s*`(#[0-9a-fA-F]{6})`\s*\|\s*`(#[0-9a-fA-F]{6})`\s*\|\s*`(#[0-9a-fA-F]{6})`\s*\|\s*`(#[0-9a-fA-F]{6})`/m)
    if (!row) throw new Error(`${file} 的 ${id} 没找到 5 列色值表`)
    const [paper, ink, accent, accentInk, accentOn] = row.slice(1, 6).map(hex6)
    out[id] = {
      name, fit, tone, default: /（默认）/.test(b.split('\n')[0]),
      tokens: { paper, ink, accent, accent_ink: accentInk, accent_on: accentOn },
      html: { engine: 'html-editorial', family, data_theme: id, template: family === 'swiss' ? 'template-swiss.html' : 'template.html' },
      native_style_brief: { visual_style: family === 'swiss' ? 'swiss-minimal' : 'editorial', primary: accent, primary_text: accentInk, ink, background: paper, on_primary: accentOn },
      spec_style: { palette: specPalette({ accent, accentInk, ink, paper }) },
    }
  }
  if (!Object.keys(out).length) throw new Error(`${file} 没解析出主题`)
  return out
}

// ---- Themed：导入主题 profile + options.md 的名称 / 适合 / 人群 ----
async function parseThemed() {
  const mod = await import(path.join(SKILL, 'engines/html-themed/project/src/components/bespoke/theme-profiles.mjs'))
  const profiles = mod.BESPOKE_THEME_PROFILES
  const options = read('engines/html-themed/references/options.md')
  const meta = {}
  for (const m of options.matchAll(/^\|\s*`(theme\d\d)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|/gm)) meta[m[1]] = { name: m[2], fit: m[3], audience: m[4] }
  const out = {}
  for (const [key, p] of Object.entries(profiles)) {
    if (!meta[key]) throw new Error(`options.md 没有 ${key} 的说明行`)
    const bg = firstHex(p.paper || '') || firstHex(p.bg) || (() => { const all = [...String(p.bg).matchAll(/#([0-9a-fA-F]{6})\b/g)]; return all.length ? all[all.length - 1][1].toUpperCase() : null })()
    if (!bg) throw new Error(`${key} 的 bg 里没有十六进制底色：${p.bg}`)
    const ink = hex6(p.ink), accent = hex6(p.accent), accent2 = p.accent2 ? hex6(p.accent2) : null
    const muted = p.muted ? firstHex(p.muted) : null
    const dark = lum(bg) < 0.4
    out[key] = {
      ...meta[key], dark,
      tokens: { bg, bg_css: p.bg, surface: p.surface, ink, muted: p.muted, accent, accent2, line: p.line, font_display: p.fontDisplay, font_body: p.fontBody, font_mono: p.fontMono, radius: p.radius, chart_series: (p.chartTreatment?.series || []).map((c) => firstHex(c) || c) },
      html: { engine: 'html-themed', themePack: key },
      native_style_brief: { visual_style: 'brief', theme: `${key} ${meta[key].name}`, primary: accent, secondary: accent2, ink, background: bg, dark, fonts: { display: p.fontDisplay, body: p.fontBody }, radius: p.radius },
      spec_style: dark ? null : { palette: specPalette({ accent, accent2, ink, paper: bg, muted }), series_colors: (p.chartTreatment?.series || []).map((c) => firstHex(c)).filter(Boolean) },
      spec_style_note: dark ? 'Spec 引擎是白卡浅底设计系统，暗底主题不派生 spec_style；要这个观感的 .pptx 走 Native 路线' : undefined,
    }
    if (out[key].spec_style && out[key].spec_style.series_colors.length < 2) delete out[key].spec_style.series_colors
  }
  return out
}

// ---- Spec Native 默认调色板（从 pptx_style.py 的 C 读）----
function parseSpecDefault() {
  const py = read('engines/spec-native/pptx_style.py')
  const block = py.match(/^C = dict\(([\s\S]*?)^\)/m)
  if (!block) throw new Error('pptx_style.py 里没找到 C = dict(...)')
  const palette = {}
  for (const m of block[1].matchAll(/^\s*(\w+)='([0-9A-Fa-f]{6})'/gm)) palette[m[1]] = m[2].toUpperCase()
  const fonts = { cjk: (py.match(/^FONT_EA = '(.+?)'/m) || [])[1], latin: (py.match(/^FONT_LATIN = '(.+?)'/m) || [])[1] }
  return {
    name: '科研答辩风（Spec Native 默认）', palette, fonts,
    editorial_recipe: { family: 'swiss', brand: `#${palette.primary}`, command: `node engines/html-editorial/scripts/gz-theme.mjs brand "#${palette.primary}" --family swiss` },
    native_style_brief: { visual_style: 'brief', primary: palette.primary, secondary: palette.secondary, ink: palette.ink, background: palette.bg, accent_red: palette.red, note: '白底、深学术蓝结构色、少量正红强调、浅蓝面板、细灰边框、深蓝结论条' },
  }
}

const data = {
  _generated_by: 'tools/build-style-briefs.mjs（不要手改；改主题请改各引擎的来源文件后重新生成）',
  _fields: {
    html: '该主题在它自己的 HTML 引擎里怎么选：Editorial 改 <html data-theme>，Themed 填 goal 的 themePack',
    native_style_brief: 'Native PPTX 路线（Default Stage 1 / Quick 自定）把它当 style brief：visual_style 是 references/visual-styles/ 里的 id，brief 表示没有对应预设、按字段描述',
    spec_style: 'Spec profile 直接填进 spec.style（palette 键与 pptx_style.C 一致，series_colors 为图表系列色）；null = 暗底主题，Spec 引擎不支持',
  },
  spec_default: parseSpecDefault(),
  editorial: { magazine: parseEditorial('themes.md', 'magazine'), swiss: parseEditorial('themes-swiss.md', 'swiss') },
  themed: await parseThemed(),
}
const json = JSON.stringify(data, null, 2) + '\n'
if (process.argv.includes('--check')) {
  const cur = fs.existsSync(OUT) ? fs.readFileSync(OUT, 'utf8') : ''
  if (cur !== json) { console.error(`themes.json 与来源不一致：node tools/build-style-briefs.mjs 重新生成`); process.exit(1) }
  console.log('themes.json 与来源一致'); process.exit(0)
}
fs.writeFileSync(OUT, json)
const n = (o) => Object.keys(o).length
console.log(`写入 ${path.relative(ROOT, OUT)}：magazine ${n(data.editorial.magazine)} / swiss ${n(data.editorial.swiss)} / themed ${n(data.themed)}（暗底 ${Object.values(data.themed).filter((t) => t.dark).length}）`)
