# Kujaku Investments — Brand Gameplan

A reference doc and folder map. Pair this with `specimen.html` (the visual specimen) for context. Every folder section below is a contract — anything built under the Kujaku brand follows what's written here. If a decision isn't covered, ask before inventing.

> **Visual reference:** open `specimen.html` in a browser. Every rule in this doc is rendered there.

---

## How to use this

1. This file is the design rules for the Kujaku brand. It lives at kujaku-meta/brand/STYLE.md. The architecture contract — how the folder is organized, how it grows, how consumers import it — lives in `README.md` alongside this file.
2. Sub-folders below organize the system by concern (fonts, colors, assets, graphs, etc.).
3. Each section maps to one concern. The section explains the rules that govern it.
4. When asking an LLM to build something Kujaku-branded, attach `README.md` (architecture) + this file (design rules) + `specimen.html` (rendered reference) and prefix the request with: *"Use the Kujaku gameplan attached. No deviations."*
5. If a folder is empty, that's deliberate — it's a slot waiting for assets you'll add.

---

## /fonts

**Purpose:** holds the typefaces and the `@font-face` declarations.

**What lives here:** font files (`.woff2`, `.otf`, `.ttf`) and the CSS that loads them.

**Locked families** — do not introduce others.

| Role | Family | Source |
|---|---|---|
| Display, headers | Sentient | Fontshare |
| Japanese | Shippori Mincho | Google Fonts |
| Body, UI | Satoshi | Fontshare |
| Numerals, mono | JetBrains Mono | Google Fonts |

**Weights to load:** 300, 400, 500, 700 for Sentient and Satoshi. 400, 500, 700 for Mincho. 400, 500 for JetBrains Mono.

**CDN load (paste in `<head>` if not self-hosting):**
```html
<link rel="preconnect" href="https://api.fontshare.com">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=sentient@300,400,500,700&f[]=satoshi@300,400,500,700&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap">
```

**CSS variables (define in root):**
```css
--font-display: 'Sentient', Georgia, serif;
--font-body:    'Satoshi', -apple-system, sans-serif;
--font-jp:      'Shippori Mincho', 'Noto Serif JP', serif;
--font-mono:    'JetBrains Mono', ui-monospace, monospace;
```

**Forbidden:** Helvetica, Arial, Inter, Roboto, system-ui as the rendered family. They're fallbacks only. Never load Noto Sans JP, M PLUS, or any other Japanese face.

---

## /colors

**Purpose:** the canonical palette and color tokens.

**What lives here:** CSS custom properties file, JSON tokens for build tools, optional color-system docs.

**Six palette colors. No more.**

| Token | Hex | Japanese | Role |
|---|---|---|---|
| `--paper` | `#F1ECE0` | 卵殻 rankaku | Default background |
| `--paper-deep` | `#E8E1D1` | 厚紙 atsugami | Sunken sections, alt background |
| `--red` | `#C8331E` | 朱 shu | Primary accent, CTAs, signal |
| `--red-deep` | `#8A2418` | 古血 kokketsu | Strokes, hover states, seal backdrops |
| `--ink` | `#1A1815` | 墨 sumi | Body text, dark surfaces |
| `--gold` | `#B8923A` | 金箔 kinpaku | RESERVED — see rules |

**Supporting ink scale (UI structure):**

| Token | Hex | Use |
|---|---|---|
| `--ink-soft` | `#4A453E` | Secondary text |
| `--ink-mid` | `#7A736A` | Tertiary, mono labels |
| `--ink-pale` | `#B5AE9F` | Disabled, hints |
| `--ink-faint` | `#D8D2C2` | Hairline borders |

**Pairing rules:**
- Default trio: paper + ink + red. Anything builds on this.
- Red never touches pure white or pure black — only paper and ink.
- Two reds together is fine (red + red-deep). Three is not.
- Negative numerical movement is `--ink-mid`, not green or red. The brand doesn't traffic in stoplight colors.

**Gold rules — read before using:**
- Gold is an occasion, not a color. One gold element per page maximum.
- Approved uses: annual report covers, anniversary marks, the single most important figure on a flagship page.
- Forbidden: body text, UI chrome (buttons, inputs, borders, icons), decorative accents, anything paired with red in the same element.
- Default answer to "should this be gold?" is no.

---

## /typography

**Purpose:** type scale, usage rules, hierarchy.

**What lives here:** type-scale CSS, usage examples, this section's rules.

**Scale:**

| Token | Size | Use |
|---|---|---|
| `--text-xs` | 0.75rem (12px) | Caption, fine print |
| `--text-sm` | 0.875rem (14px) | Meta, small labels |
| `--text-base` | 1rem (16px) | Body |
| `--text-lg` | 1.125rem (18px) | Lead paragraphs |
| `--text-xl` | 1.375rem (22px) | Small headings |
| `--text-2xl` | 1.75rem (28px) | Section headings |
| `--text-3xl` | 2.25rem (36px) | Page headings |
| `--text-4xl` | 3rem (48px) | Hero secondary |
| `--text-5xl` | 4rem (64px) | Hero |
| `--text-6xl` | 5.5rem (88px) | Editorial display |
| `--text-7xl` | 8rem (128px) | Display moments |

**Usage table:**

| Context | Family | Weight | Notes |
|---|---|---|---|
| Hero / display | Sentient | 400, italic 300 | Tight tracking `-0.04em` |
| Section titles | Sentient | 400 | 48px |
| Lead paragraphs | Sentient italic | 300 | 20px, ink-soft |
| Body | Satoshi | 400 | 16–18px, line-height 1.6–1.7 |
| Eyebrows / labels | JetBrains Mono | 500 | 11px, uppercase, tracking `0.18em` |
| Numerals (data, prices, %) | JetBrains Mono | 500 | Tabular figures only |
| Japanese (any) | Shippori Mincho | 400 | Tracking `0.05–0.08em` |
| Hanko stamp characters | Shippori Mincho | 700 | White on red |

**Forbidden:**
- Sentient at body sizes (under 18px)
- Mono for body or display
- All caps for anything longer than a 2–3 word eyebrow
- Mincho italic — does not exist in this system

**Visual reference:** `specimen.html` → "Sentient meets mincho" section.

---

## /assets

**Purpose:** all imagery — logos, illustrations, photos, brushstrokes.

**Suggested sub-structure:**

```
assets/
├── logos/         (mark variants, wordmarks, lockups)
├── illustrations/ (koi, brushstrokes, sumi-e plates)
├── icons/         (UI icons if needed — SVG only)
└── photography/   (any photo-based content)
```

### Logo rules

The mark is three overlapping fish-scale shapes arranged in a vertical stack (top scale above, two scales below offset left and right in a slight cascade). All three scales share the same fill color — depth comes from the filter, not from color contrast.

**Naming convention** (lives in `/dist`):

  logo-mark-{token}.svg          flat variant
  logo-mark-{token}-pressed.svg  pressed-in variant (default use)
  logo-lockup-{token}.svg        mark + wordmark, flat
  logo-lockup-{token}-pressed.svg mark + wordmark, pressed scales

Where `{token}` is one of: `red`, `gold`, `ink`, `paper`.

**Color selection by context:**

| Surface | Mark variant | Filter |
|---|---|---|
| `--paper` (default body) | `logo-mark-red-pressed.svg` | `#press` (dark inner shadow) |
| `--paper-deep` | `logo-mark-red-pressed.svg` | `#press` |
| `--ink` panels | `logo-mark-paper-pressed.svg` | `#press-light` (light inner highlight) |
| Annual report / flagship covers | `logo-mark-gold-pressed.svg` | `#press` — see Gold rules in /colors |
| Print, grayscale, monochrome | `logo-mark-ink-pressed.svg` or flat ink | flat preferred |

**Default mark:** `logo-mark-red-pressed.svg`. This is the canonical Kujaku mark. Any reference to "the logo" or "the Kujaku mark" without qualification means this file.

**Default lockup:** `logo-lockup-red-pressed.svg`. Mark + wordmark in ink on paper. Pressed scales, flat text.

**Wordmark (inside lockups):** "Kujaku" in Sentient regular, "INVESTMENTS" in Sentient regular at smaller size with wide tracking. Text is rendered live — lockup SVGs rely on the consuming site loading Sentient via fonts.css. When using a lockup SVG, inline the SVG into HTML rather than loading via `<img src=>` so the font resolves. Mark-only variants have no text dependency.

**Logo never:**
- Recolored via CSS (colors are baked into the file — use the correct variant instead).
- Rotated, skewed, stretched.
- Placed on red, oxblood, or gold backgrounds. Paper and ink only.
- Smaller than 40px (mark) or 240px wide (lockup).

**Visual reference:** `specimen.html` → Logo section.

### Illustration rules

When using illustrations (koi, brushwork, sumi-e):
- Single accent color per illustration (red, ink, or both)
- Brush-style execution preferred over geometric
- One illustration per view maximum
- Illustrations earn their place — never decorative filler

---

## /components

**Purpose:** reusable UI patterns. The atomic building blocks.

**Patterns documented in `specimen.html`:**

| Pattern | Where to find |
|---|---|
| Hanko stamp | Hero corner, card seals, eyebrow accents |
| Eyebrow | Above every section title |
| Card (letterpress) | Sector intelligence cards section |
| Data row | Inside cards, label + value |
| Hero | Top of `specimen.html` |
| Empty / reserved slot | "Reserved 余白" section |

**Card recipe:**
```css
.card {
  background: #F4EFE6;
  border-radius: 6px;
  padding: 32px;
  box-shadow:
    inset 0 1px 0 rgba(255,251,240,0.7),
    0 1px 0 rgba(255,251,240,0.5),
    0 4px 12px rgba(40,30,18,0.06),
    0 16px 40px rgba(40,30,18,0.06);
}
```

**Eyebrow recipe:**
```css
.eyebrow {
  font-family: var(--font-mono);
  font-size: 11px; font-weight: 500;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--ink-mid);
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 24px;
}
.eyebrow::before {
  content: ''; width: 24px; height: 1px; background: var(--ink-mid);
}
.eyebrow .jp {
  font-family: var(--font-jp); font-size: 14px;
  letter-spacing: 0.05em; text-transform: none;
  color: var(--red); font-weight: 400;
}
```

**Hanko stamp recipe (28px size):**
```css
.hanko {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px;
  background: var(--red); border-radius: 2px;
  font-family: var(--font-jp); font-weight: 700;
  font-size: 14px; color: var(--paper); line-height: 1;
  transform: rotate(-2deg);
  box-shadow: 0 2px 6px rgba(138,36,24,0.25);
}
```

**Sizes:** 22px (in cards), 28px (inline), 48px (callouts), 72px (hero corner).

---

## /graphs

**Purpose:** chart format rules and templates.

**What lives here:** chart-style CSS, SVG chart templates, axis/grid recipes, possibly D3 or Chart.js config presets.

### Hard chart rules

1. **One accent color per chart.** Vermillion `#C8331E`. If you need a second series, use ink-soft `#4A453E` — never a second red, never green or amber.
2. **Hairline grid only.** `#D8D2C2` at 0.5px stroke. Maximum 4–5 horizontal grid lines. No vertical grid.
3. **Sparse axis labels.** Mono 10px, ink-mid color, letter-spacing 0.04–0.06em. Show the minimum needed to orient the reader.
4. **End-point marker.** Filled circle r=3.5 + outer ring r=7 stroke 0.5 opacity 0.5, both vermillion.
5. **No legends inside the chart.** Put labels in the header above the chart, never floating.
6. **No gradients.** Optional area fill is solid vermillion at 6% opacity.
7. **No animations on initial load.** Charts render flat. Hover states for individual data points are allowed (subtle ring expansion).
8. **No tooltips with shadows.** If tooltips are needed, use the card emboss recipe — same as everything else.

### Chart header pattern

```
[ Chart title in Sentient 28px ]  [ JP gloss in Mincho 14px ink-mid ]
                                                    [ Big number in Mono 32px ]
                                                    [ Delta in Mono 13px red ]
                                  ─────────── 1px ink-faint divider ───────────
[ chart body ]
```

### Chart container

Wrap every chart in the card recipe (letterpress emboss). Internal padding 40px. Border-radius 6px.

### What charts must never do

- Use color to encode positive vs. negative. Use position (above/below baseline) and the single accent.
- Stack multiple series on top of each other (small multiples instead — separate cards, same scale).
- Animate bars growing from zero on load.
- Use 3D perspective. Ever.
- Show more than ~6 months of data without explicit pagination or zoom.

**Visual reference:** `specimen.html` → "A line on paper" section.

---

## /animations

**Purpose:** motion specs and reference code. The brand has very few motions — they all live here.

**Easings — these three only:**
```css
--ease-out:      cubic-bezier(0.22, 1, 0.36, 1);   /* default */
--ease-in-out:   cubic-bezier(0.65, 0, 0.35, 1);
--ease-emphasis: cubic-bezier(0.2, 0.9, 0.2, 1);
```

**Durations:**
```css
--duration-fast:    240ms;   /* color, opacity */
--duration-default: 600ms;   /* underline reveal */
--duration-slow:    700ms;   /* frame reveal */
```

### Underline reveal (the signature motion)

Single line, fills left-to-right on hover, retracts right-to-left on un-hover.

```css
.reveal {
  position: relative; display: inline-block;
  text-decoration: none; color: inherit; cursor: pointer;
  padding-bottom: 4px;
  transition: color 240ms cubic-bezier(0.22, 1, 0.36, 1);
}
.reveal::after {
  content: ''; position: absolute; left: 0; bottom: 0;
  width: 100%; height: 1px; background: currentColor;
  transform: scaleX(0); transform-origin: right;
  transition: transform 600ms cubic-bezier(0.22, 1, 0.36, 1);
}
.reveal:hover::after { transform: scaleX(1); transform-origin: left; }
.reveal-red:hover { color: var(--red); }
```

### Frame reveal — for emphasized links

Two hairlines, one above and one below, draw inward simultaneously.

```css
.reveal-frame {
  position: relative; display: inline-block; padding: 8px 4px; cursor: pointer;
}
.reveal-frame::before, .reveal-frame::after {
  content: ''; position: absolute; left: 0;
  width: 100%; height: 1px; background: var(--ink);
  transform: scaleX(0);
  transition: transform 700ms cubic-bezier(0.22, 1, 0.36, 1);
}
.reveal-frame::before { top: 0; transform-origin: left; }
.reveal-frame::after  { bottom: 0; transform-origin: right; }
.reveal-frame:hover::before, .reveal-frame:hover::after { transform: scaleX(1); }
```

### Forbidden motions

- Bounce, spring, elastic
- Fade-in / fade-out on load
- Scale on hover (no `transform: scale(...)`)
- Rotation as decoration
- Parallax
- Scroll-triggered reveals

**Visual reference:** `specimen.html` → "Underlines that draw themselves" section. Hover the demos to see motion.

---

## /textures

**Purpose:** paper grain, embossing recipes, watermark patterns.

### Body background — three-layer cardstock

Paste this whole block as-is. It's the eggshell paper feel.

```css
body {
  background-color: #F1ECE0;
  background-image:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='f1'><feTurbulence type='fractalNoise' baseFrequency='1.4' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.26  0 0 0 0 0.20  0 0 0 0 0.13  0 0 0 0.11 0'/></filter><rect width='100%25' height='100%25' filter='url(%23f1)'/></svg>"),
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='380' height='380'><filter id='f2'><feTurbulence type='fractalNoise' baseFrequency='0.35' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.30  0 0 0 0 0.22  0 0 0 0 0.12  0 0 0 0.06 0'/></filter><rect width='100%25' height='100%25' filter='url(%23f2)'/></svg>"),
    radial-gradient(ellipse 120% 100% at center, transparent 55%, rgba(60, 40, 20, 0.06) 100%);
  background-repeat: repeat, repeat, no-repeat;
}
```

### Embossing — three states

**Surface color is part of the recipe.** Each emboss state requires a specific surface color relative to the body paper background to read correctly:
- Letterpress and Subtle: surface LIGHTER than `--paper` (use `#F4EFE6` or apply to a `--paper` surface). The shadow lifts off the page.
- Deboss: surface DARKER than `--paper` (use `var(--paper-deep)`). The inset shadow presses into the page.
Applying deboss shadows to a lighter surface inverts the illusion and reads as raised.

**Letterpress (raised) — for cards, swatches, primary surfaces**
```css
box-shadow:
  inset 0 1px 0 rgba(255,251,240,0.7),
  0 1px 0 rgba(255,251,240,0.5),
  0 4px 12px rgba(40,30,18,0.06),
  0 16px 40px rgba(40,30,18,0.06);
```

**Deboss (pressed in) — for input fields, sunken regions**
```css
box-shadow:
  inset 0 2px 4px rgba(40,30,18,0.10),
  inset 0 -1px 0 rgba(255,251,240,0.7),
  0 1px 0 rgba(255,251,240,0.7);
```

**Subtle (low elevation) — secondary cards, tiles**
```css
box-shadow:
  inset 0 1px 0 rgba(255,251,240,0.7),
  0 2px 6px rgba(40,30,18,0.06),
  0 12px 28px rgba(40,30,18,0.06);
```

### SVG press filters

Two filters for logos and pressed shapes. Shipped as part of each logo SVG's `<defs>`. Not a shared stylesheet asset — SVG filters only resolve within the same SVG when loaded via `<img src=>`.

**#press — dark inner shadow, for colored scales on paper or paper-deep:**

```xml
<filter id="press" x="-10%" y="-10%" width="120%" height="120%">
  <feGaussianBlur in="SourceAlpha" stdDeviation="1.5"/>
  <feOffset dx="0" dy="2"/>
  <feComposite in2="SourceAlpha" operator="arithmetic" k2="-1" k3="1" result="shadowDiff"/>
  <feFlood flood-color="#28201e" flood-opacity="0.7"/>
  <feComposite in2="shadowDiff" operator="in" result="innerShadow"/>
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="innerShadow"/>
  </feMerge>
</filter>
```

**#press-light — light inner highlight, for paper-colored scales on ink:**

```xml
<filter id="press-light" x="-10%" y="-10%" width="120%" height="120%">
  <feGaussianBlur in="SourceAlpha" stdDeviation="1.5"/>
  <feOffset dx="0" dy="2"/>
  <feComposite in2="SourceAlpha" operator="arithmetic" k2="-1" k3="1" result="shadowDiff"/>
  <feFlood flood-color="#ffffff" flood-opacity="0.35"/>
  <feComposite in2="shadowDiff" operator="in" result="innerShadow"/>
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="innerShadow"/>
  </feMerge>
</filter>
```

These filters create a matte "pressed into the paper" illusion matching the .emboss-deboss CSS treatment. They are NOT glossy; do not substitute with specular lighting filters.

### Kanji watermark

A single character at huge size, very low opacity (4–6%), positioned at edge or center of section. Pointer-events none, user-select none. The .watermark utility ONLY lives inside a .watermark-stage container — the stage defines the protected territory and ensures body text never overlaps the watermark.

```css
.watermark {
  position: absolute; right: -60px; top: 50%;
  transform: translateY(-50%);
  font-family: var(--font-jp); font-weight: 400;
  font-size: 720px; line-height: 1;
  color: var(--ink); opacity: 0.04;
  pointer-events: none; user-select: none;
}
```

Required wrapper. Any element containing a .watermark must be a .watermark-stage. Body text inside the stage uses position:relative and z-index:1.

```css
.watermark-stage {
  position: relative;
  overflow: hidden;
}
```

### Forbidden

- Cool-tone shadows (`rgba(0,0,0,...)` or `rgba(0,0,255,...)`). Always warm: `rgba(40,30,18,...)`.
- Blur filters, backdrop-filters, glassmorphism.
- Drop shadows that aren't from this recipe set.

---

## /voice

**Purpose:** copy, tone, vocabulary rules.

**Posture:** essayist who happens to run money. Quiet, precise, confident.

### Approved Japanese vocabulary (recurring)

| Char | Reading | Meaning | Where used |
|---|---|---|---|
| 観 | kan | observation | Section watermarks, breaks |
| 静観 | seikan | calm observation | Tagline, brand mantra |
| 孔雀 | kujaku | peacock | The brand in JP |
| 余白 | yohaku | negative space | Empty slots, reserved sections |
| 鯉 | koi | carp | Koi-related content |
| 紋 | mon | crest, mark | Logo / identity |
| 図表 | zuhyō | chart, diagram | Chart sections |
| 指標 | shihyō | indicator | Sector / metric cards |
| 色 | iro | color | Palette sections |
| 活字 | katsuji | typeface | Type sections |
| 線 | sen | line | Motion sections |
| 見本 | mihon | specimen | Documentation |

**Pattern:** English label + Japanese gloss. Example: `PALETTE   色 · iro`.

### Voice rules

**Do:**
- Short, declarative sentences.
- Financial vocabulary used precisely (breadth, base, rotation, σ).
- Sentence case throughout. Capitals only where grammar requires.
- Em dashes for asides, not for drama.
- Italic Sentient for lead paragraphs and pull quotes.

**Don't:**
- Exclamation marks.
- "Exciting," "amazing," "next-gen," "AI-powered," "game-changing," "revolutionary."
- Emoji. Ever.
- Engagement bait ("Want to know what we found?").
- ALL CAPS for emphasis. Use italic Sentient instead.

**Tone examples:**

✓ *Energy held a four-week base above its median range. Semis printed lower highs into deteriorating breadth.*

✗ *🚀 Energy is BREAKING OUT! Don't miss this exciting opportunity!*

### Forbidden Japanese usage

- Don't use kanji you can't translate.
- Don't combine kanji into phrases unless they're in the approved table.
- Don't decorate with random hiragana/katakana for "vibe." It reads as costume.
- Never use Japanese for functional UI (button labels, error messages, navigation).

---

## Open decisions

These are unconfirmed. When you decide, the doc updates.

- **Final logo treatment.** Variant 08 (embossed original) is the locked default. Override if needed.
- **Three recurring kanji.** Default trio: 観 (kan, observation), 静観 (seikan, calm observation), 孔雀 (kujaku, peacock).
- **Tagline.** Working: *Calm observation*.
- **Koi imagery.** You'll add to `/assets/illustrations/`.
- **Brushstroke plates.** You'll add to `/assets/illustrations/`.

---

*Pair with `specimen.html` for the rendered system. Update this doc when locking new decisions.*
