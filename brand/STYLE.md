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

**Seven palette colors.** Extensions require a design-rationale proposal; see /components Cards for the precedent that earned `--paper-coal`.

| Token | Hex | Japanese | Role |
|---|---|---|---|
| `--paper` | `#F1ECE0` | 卵殻 rankaku | Default background |
| `--paper-deep` | `#E8E1D1` | 厚紙 atsugami | Sunken sections, alt background |
| `--paper-coal` | `#3E362F` | 墨紙 sumigami | Dark paper surface |
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

**Paper surface family** (four tones for card and surface use):

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#F1ECE0` | Default body background, primary surface |
| `--paper-deep` | `#E8E1D1` | Sunken sections, alt background, cardstock |
| `--paper-coal` | `#3E362F` | Dark editorial surface, coal cards |
| `--red-deep` | `#8A2418` | Oxblood surface for ceremonial red cards |

Paper surfaces are what content sits on. They are never text colors. The gold token (`--gold` `#B8923A`) serves as a ceremonial fourth paper surface when used for `.card-gold`, but it is governed by the gold rules below and is not part of the paper family.

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

**Gold cards are permitted.** `.card-gold` and `.card-gold-sunken` are ceremonial content blocks subject to the one-gold-per-page rule. The rule applies collectively: one gold card OR one gold eyebrow OR one gold figure, not one of each. Gold card interiors must contain no `--red` anywhere (the two-reds prohibition stands). For eyebrow labels inside gold cards, use `.eyebrow-dark.is-ink`.

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

### Eyebrow

Three variants share a composable modifier system. Use these above section headings to label content and carry the brand's editorial voice.

**Variants:**

| Class | Usage |
|---|---|
| `.eyebrow` | Default. Column-spanning hairline with mono label and JP gloss. The signature Kujaku eyebrow — use it unless you have a reason not to. |
| `.eyebrow-quiet` | No stroke, no mark — voice-only mono label with JP gloss. For running section headers inside long-form content where a hairline would feel too loud. |
| `.eyebrow-gloss` | JP character with italic mono reading, no Latin label. For chapter breaks, thematic dividers, or typographic punctuation. |

**Color modifiers (apply to any variant):**

| Class | Accent color | Usage |
|---|---|---|
| _none_ | `--red` | Default. Brand color on the JP character (`.eyebrow`, `.eyebrow-quiet`) or on the full JP element (`.eyebrow-gloss`). |
| `.is-ink` | `--ink` | Neutral variant for sections that don't need brand accent. Preserves base weight. |
| `.is-gold` | `--gold` | Ceremonial — important notices, flagship figures, annual marks. **One gold eyebrow per page maximum.** Weight steps up one (mono 500→700, Mincho 400→500). Gold and red never mix; applying `.is-gold` replaces red fully. |

**Alignment modifiers (apply to any variant):**

| Class | Effect |
|---|---|
| _none_ | Left-aligned. Default. |
| `.is-center` | Center-aligned. For hero sections and flagship pages. |
| `.is-right` | Right-aligned. For sidebar captions or asymmetric layouts. Note: `.eyebrow-gloss.is-right` inverts the natural hierarchy (JP character floats into margin) — use deliberately or prefer left/center for gloss. |

**Numbered modifier:**

| Class | Effect |
|---|---|
| `.is-numbered` | Prepends "01 · " ordinal in the eyebrow's own type family. For ordered section lists, methodology steps, chapter breaks. |

**Composing:**

Classes compose freely. Examples:
- `<p class="eyebrow">INDICATORS · <span class="jp">指標 · shihyō</span></p>` — default
- `<p class="eyebrow-quiet is-ink is-center">FIELD NOTES · <span class="jp">見本 · mihon</span></p>` — quiet, neutral, centered
- `<p class="eyebrow is-gold is-center is-numbered"><span class="num">01 · </span>IMPORTANT · <span class="jp">観 · kan</span></p>` — gold hero with ordinal

**Don't:**
- Apply `.is-gold` to more than one eyebrow per page.
- Pair gold with red elsewhere on the same line or element.
- Use JP characters outside the /voice approved vocabulary table.

### Eyebrow · Dark

Companion to `.eyebrow` for dark card surfaces (`.card-coal`, `.card-oxblood`, `.card-gold` and their sunken variants). The base `.eyebrow` recipe's `--ink-mid` text and `--red` JP gloss are unreadable on dark surfaces; `.eyebrow-dark` swaps in paper-family colors with a gold JP accent as default.

**Default:** paper-colored label, gold JP gloss, paper-toned hairline (`rgba(255,251,240,0.25)`). Use on `.card-coal`, `.card-oxblood`, and their sunken variants.

**Color modifiers:**

| Class | Effect |
|---|---|
| _(default)_ | Paper label, gold JP gloss. Default for dark cards. |
| `.is-paper` | Paper label, paper JP gloss. Monochromatic on dark. Use when the card already contains a gold element (eyebrow cannot claim gold if another element has). |
| `.is-gold` | Gold label, paper JP gloss. Reverses the accent pairing. Use for emphasis on coal or oxblood, never on gold. |
| `.is-ink` | Ink label, ink JP gloss. Only usable on `.card-gold` (where ink reads against warm gold); do NOT use on coal or oxblood (ink invisible on warm-dark). |

**Alignment + numbered modifiers:** `.is-center`, `.is-right`, and `.is-numbered` compose exactly as with `.eyebrow`. See that section for details.

**Don't:**
- Use `.eyebrow-dark.is-gold` on `.card-gold` (two gold elements; breaks one-per-page rule).
- Use `.eyebrow-dark.is-ink` on `.card-coal` or `.card-oxblood` (ink invisible on warm-dark).
- Use the base `.eyebrow` on any dark card surface (the gray and red disappear).

### Cards

Eight card recipes in four colors × two states. Cards frame content: text, data, charts, images, titles, any block-level content. Static — no hover states.

**Variants:**

| Class | Surface | State | Use |
|---|---|---|---|
| `.card-paper` | `#F4EFE6` | raised | Default editorial card. Lifts off body paper. |
| `.card-paper-sunken` | `var(--paper-deep)` | sunken | Pressed-in regions: inputs, pulled quotes, inset panels. |
| `.card-coal` | `var(--paper-coal)` | raised | Dark editorial card. High-contrast sections. |
| `.card-coal-sunken` | `#2E2824` | sunken | Dark pressed-in region. |
| `.card-oxblood` | `var(--red-deep)` | raised | Ceremonial red card. Announcements, chapter breaks, pull quotes. |
| `.card-oxblood-sunken` | `#6B1C12` | sunken | Sunken oxblood for deep-red moments. |
| `.card-gold` | `var(--gold)` | raised | Ceremonial gold card. One-per-page rule. |
| `.card-gold-sunken` | `#8F7128` | sunken | Sunken gold. Illusion weakest of the eight — strongest when nested inside a `.card-gold` parent. |

**Size modifiers (compose with any variant):**

| Class | Padding |
|---|---|
| `.is-sm` | 20px 24px |
| _(default)_ | 32px 40px |
| `.is-lg` | 48px 56px |

**Internal layout helpers (optional):** `.card-title` (Sentient 28px), `.card-body` (Satoshi 16px), `.card-data` (JetBrains Mono 44px for stat numerals), `.card-delta` (JetBrains Mono 13px for deltas and change labels). Use when useful; compose freely.

**Rules:**

- Cards only on `--paper`, `--paper-deep`, or `--paper-coal` backgrounds. Cards on `--ink` lose their cast shadows and should use a different pattern (e.g. a bordered block).
- No red interior content on `.card-oxblood` or its sunken variant — red on red-deep is invisible; the two-reds rule permits red + red-deep as the only red pair.
- No red or gold interior content on `.card-gold` or its sunken variant (the one-gold-per-page rule and two-reds rule both apply). Use `.eyebrow-dark.is-ink` for eyebrow labels inside gold cards.
- Nesting: same-variant nesting works (e.g. `.card-paper` inside `.card-paper`). Cross-variant nesting works (e.g. `.card-paper.is-sm` inside `.card-coal.is-lg` for dashboard composition). No hard rule — use judgment; if the illusion fails visually, reconsider the composition.
- Use `.eyebrow-dark` (NOT `.eyebrow`) on any dark card.

### Hanko

Red seal stamp — distinctive Japanese signature element. Inline-flex element holding one or more JP characters in Mincho 700, white-on-red, slightly rotated, with a soft cast.

**Variants:**

| Class | Size | Use |
|---|---|---|
| `.hanko.is-22` | 22px | In-card or in-row contexts |
| `.hanko.is-28` | 28px | Default inline use (no class needed; `.is-28` permitted for explicit clarity) |
| `.hanko.is-48` | 48px | Section callouts, hero corners |
| `.hanko.is-72` | 72px | Page-level hero corner, oversized brand moment |

**Rules:**
- One hanko per content region. Multiple hanko in close proximity reads as decorative noise.
- JP characters inside must come from the `/voice` approved vocabulary table.
- Never recolor (red is the seal color); never remove the rotation; never add a border.
- The cast shadow uses an alpha of the red-deep family — preserved as a literal in the recipe (CSS cannot resolve alpha against `var()`).

**Composes with:**
- `.nav-rail` (may be placed at rail bottom via consumer markup — no canonical slot)
- `.card-*` (placed in a corner via positioning)
- Inline within body text (small variant)

### Nav

Two-piece brutalist navigation: a left rail that expands on hover, and a top masthead that hides on scroll-down and reappears on scroll-up. Terminal/mono aesthetic. Light paper surfaces. No chevrons, no expanding category submenus — routes are organized into SYSTEM / LOG / STATIC sections.

**Structure:**

| Class | Role |
|---|---|
| `.nav-composition` | Optional flex-row wrapper holding rail + main column. Default `min-height: 0` (embeddable). For page shells, consumer sets its own min-height. |
| `.nav-rail` | Left rail. Collapsed 64px default. Expands to 180px on `:hover` OR when `.is-expanded` applied. |
| `.nav-rail .mark` | Top of rail. Height 48px to match `.nav-masthead` (forms the crisp "+" corner intersection at the rail-masthead boundary). Holds logo mark (visible in collapsed state) and wordmark (visible in expanded state). Children: `.mark .svg` + `.mark .wordmark`. Crossfades between the two on state change. |
| `.nav-rail .items` | Vertical stack containing `.nav-section` and `.nav-item` children. |
| `.nav-rail .footer` | Build-info footer at rail bottom. Three lines of mono 9px `--ink-pale`. Only visible when rail is expanded. Scoped selector — consumers should not use `.footer` inside the rail for unrelated content. |
| `.nav-section` | Section heading group (SYSTEM, LOG, STATIC). Contains `.nav-section .label` + nested `.nav-item` children. |
| `.nav-section .label` | Section name. Mono 9px letterspaced caps. Hidden in collapsed rail via opacity 0. |
| `.nav-item` | Single nav row. Mono 11px. Flex row with `.nav-item .slash` + `.nav-item .label` children. |
| `.nav-item .slash` | The `/` prefix character. `--ink-pale` opacity by default. |
| `.nav-item .label` | Route name. Hidden in collapsed state; fades in when rail expands. |
| `.nav-masthead` | Top bar positioned inside the main content column (NOT above the rail). Height 48px. Mono 11px metadata content. |
| `.nav-masthead .meta` | The metadata row. Uppercase, letterspaced 0.12em. |

**State modifiers:**

| Class | Applied to | Effect |
|---|---|---|
| `.is-expanded` | `.nav-rail` | Forces 180px expanded state (overrides the :hover behavior). Useful for desktop "locked-open" preferences. |
| `.is-active` | `.nav-item` | Current route indicator. Shows `>` prefix + `--red` text color. Single treatment; never combine with left-bar or background-fill active variants. |
| `.is-hidden` | `.nav-masthead` | Translates the masthead up via `translateY(-100%)`. Consumer's JS toggles this class based on scroll direction. Only visible under `position: sticky` or `position: fixed` (a static masthead vacating its layout slot does nothing). |
| `.is-drawer` | `.nav-rail` | Full-width mobile drawer state. Requires consumer JS to toggle based on viewport width + hamburger trigger. |

**Corner alignment:**

The rail's right-edge border and the masthead's bottom-edge border must meet at a single intersection point. This is achieved by placing the masthead INSIDE the main content column (not above the rail), and by sizing `.nav-rail .mark` to 48px — the same height as `.nav-masthead` — so their two bottom-edge hairlines share a single Y coordinate. Canonical markup:

```html
<div class="nav-composition">
  <aside class="nav-rail">
    <div class="mark">...</div>
    <nav class="items">
      <div class="nav-section">
        <p class="label">System</p>
        <a class="nav-item is-active" href="/overview">
          <span class="slash">/</span>
          <span class="label">overview</span>
        </a>
        ...
      </div>
      ...
    </nav>
    <div class="footer">...</div>
  </aside>
  <main>
    <header class="nav-masthead">
      <div class="meta">12:00:04 UTC · SESSION · 04.19 / MON · MODE · OBSERVATIONAL · BOT · ONLINE</div>
    </header>
    <!-- page content -->
  </main>
</div>
```

**Animation behavior:**

- Rail width transitions 200ms `--ease-out` between 64px and 180px. Note: 200ms is a nav-specific duration literal (not `--duration-fast` at 240ms) — tuned to match the approved interaction feel from sandbox Variant 1.
- Rail shadow transitions 200ms `--ease-out` (subtle letterpress on expand; flat on collapse).
- Label/section/footer opacity transitions 200ms `--ease-out`.
- Mark → wordmark crossfade 200ms `--ease-out`.
- Nav item color transitions 80ms on hover (fast feedback).
- Masthead transform transitions `--duration-fast` `--ease-out` (token-aligned).

All animations are interaction-coupled (hover, class toggle). Per /animations: interaction-coupled opacity and transform transitions are permitted. The forbidden "fade-in on load" rule still applies — never fade any nav element in on page load.

**JS contract (important — brand ships classes, not behavior):**

Brand ships the CSS for `.nav-rail`, `.nav-masthead`, and their state classes. Brand does NOT ship the JavaScript for scroll-based hiding or drawer-based mobile toggling. The consuming app writes those ~15 lines.

Minimal reference implementation for masthead scroll-hide:

```js
// Scroll-direction-based masthead hide. ~15 lines.
// Toggles .is-hidden on .nav-masthead when user scrolls down;
// removes it on scroll up.
const masthead = document.querySelector('.nav-masthead');
const scrollEl = /* the scrollable element or window */;
let lastY = 0;
scrollEl.addEventListener('scroll', () => {
  const y = scrollEl.scrollTop ?? window.scrollY;
  if (y > lastY && y > 40) {
    masthead.classList.add('is-hidden');
  } else if (y < lastY) {
    masthead.classList.remove('is-hidden');
  }
  lastY = y;
}, { passive: true });
```

This snippet is a reference, not a shipped helper. Consuming apps own their scroll-detection logic.

**Rules:**

- Rail uses `--paper` background at rest. Expands with a subtle letterpress shadow (~50% intensity of the `.emboss-letterpress` stack). Never use dark rail surfaces (`--paper-coal`, `--ink`).
- Active state is exclusively `>` + `--red` text color. Never combine with a left border bar, background fill, or dot indicator.
- Masthead sits inside the main content column, not above the rail. This makes the corner alignment automatic and lets the rail maintain a continuous top-to-bottom visual line.
- Rail expands ONLY on mouseenter (or `.is-expanded` class). No click-to-expand behavior. The direct-hover model is the approved interaction.
- Sections (SYSTEM, LOG, STATIC) are flat groupings — not expandable categories. Each route is a top-level `.nav-item` inside a `.nav-section`.

**Usage:**

- Page shell: set `min-height: 100vh` on a page container OR on `.nav-composition` itself.
- Embedded widget: default `min-height: 0` on `.nav-composition` means the nav fits inside its container's height naturally.

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
