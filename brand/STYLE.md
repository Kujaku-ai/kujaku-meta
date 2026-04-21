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
- **Gold primitives — chain:** `.eyebrow.is-gold`, `.eyebrow-dark` (default gold JP), `.indicator-gloss.is-dark`, `.btn.is-oxblood .jp`, `.tbl.is-eyebrow-header` (with gold caption JP). Any ONE per page; never two together. Each primitive's subsection cross-references this rule.

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

**Gold-budget chain:**

`.eyebrow.is-gold` CLAIMS the page's one-gold budget. Cross-refers to `.eyebrow-dark` (default), `.indicator-gloss.is-dark`, `.btn.is-oxblood .jp`, and `.tbl.is-eyebrow-header` (with gold caption JP) — no two of these may appear on the same page. See /colors one-gold rule.

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

**Gold-budget chain:**

Default `.eyebrow-dark` uses `--gold` for the JP gloss. This CLAIMS the page's one-gold budget. For a dark-card page that needs gold elsewhere (a gold eyebrow, a gold indicator-gloss, a gold button kanji, a gold table caption), use `.eyebrow-dark.is-paper` (no-gold variant) instead. Chains with `.eyebrow.is-gold`, `.indicator-gloss.is-dark`, `.btn.is-oxblood .jp`, and `.tbl.is-eyebrow-header` (with gold caption JP) — no two of these may appear on the same page. See /colors one-gold rule.

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

Red seal stamp — distinctive Japanese signature element. Inline-flex element holding one or more JP characters in Mincho 700, white-on-red, axis-aligned, with a soft cast.

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
- Never recolor (red is the seal color); never add a border; never apply a rotation (the hanko is axis-aligned by design).
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
| `.nav-rail .mark` | Top of rail. Height 48px to match `.nav-masthead` (forms the crisp "+" corner intersection at the rail-masthead boundary). Holds the mark logo (visible in collapsed state) and the full lockup logo (visible in expanded state) as two `<img>` children: `.mark .svg` (28×28 mark) + `.mark .lockup` (max-height 28px lockup). Crossfades between the two on state change. |
| `.nav-rail .items` | Vertical stack containing `.nav-section` and `.nav-item` children. |
| `.nav-rail .footer` | Build-info footer at rail bottom. Three lines of mono 9px `--ink-pale`. Only visible when rail is expanded. Scoped selector — consumers should not use `.footer` inside the rail for unrelated content. |
| `.nav-section` | Section heading group (SYSTEM, LOG, STATIC). Contains `.nav-section .label` + nested `.nav-item` children. |
| `.nav-section .label` | Section name. Mono 9px letterspaced caps. Hidden in collapsed rail via opacity 0. |
| `.nav-item` | Single nav row. Mono 11px. Flex row with `.nav-item .slash` + `.nav-item .label` children. |
| `.nav-item .slash` | The `/` prefix character. `--ink-pale` opacity by default. |
| `.nav-item .label` | Route name. Hidden in collapsed state; fades in when rail expands. |
| `.nav-masthead` | Top bar positioned inside main content column (NOT above the rail). 48px tall (matches `.nav-rail .mark`). Flex row: `.ticker-viewport` (flex 1) + `.actions` (fixed width). Paper background, ink-faint border-bottom. |
| `.nav-masthead .ticker-viewport` | Horizontally scrolling carousel container. `overflow: hidden`. Contains a single `.ticker-track`. |
| `.nav-masthead .ticker-track` | Flex row holding ticker blocks. CSS `@keyframes translateX 0 → -50%` on a 60-second linear infinite loop. Consumers must duplicate the ticker block markup (each ticker appears twice in sequence) for seamless looping. `:hover` pauses the animation. |
| `.nav-masthead .ticker-block` | Single ticker cell. Contains `.symbol`, `.delta`, `.price`. The `.delta` shows by default; on hover of the block, `.delta` fades to 0 opacity and `.price` fades to 1 opacity (200ms ease-out). |
| `.nav-masthead .ticker-block .symbol` | Ticker symbol. Mono 11px, uppercase tracked. `/`-prefix via `::before` pseudo-element, borrowing the rail's route vernacular. |
| `.nav-masthead .ticker-block .delta` | Percent change display. Mono 11px, `--ink-mid`. No color coding (direction encoded by +/- sign). Default visible. |
| `.nav-masthead .ticker-block .price` | Absolute numeric price. Mono 11px, `--ink-mid`. Default hidden (opacity 0). Revealed on `.ticker-block:hover`. |
| `.nav-masthead .actions` | Right-aligned navigation links (Login, About, Contact, etc.). Not animated. `a + a { margin-left: 24px }` for spacing between actions. |
| `.nav-masthead .actions a` | Individual action link. Mono 11px uppercase tracked, `--ink-mid` color. `:hover` shifts to `--red`. |

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
      <div class="ticker-viewport">
        <div class="ticker-track">
          <!-- DUPLICATE THE TICKER LIST: -->
          <div class="ticker-block">
            <span class="symbol">SPX</span>
            <span class="delta">+0.18%</span>
            <span class="price">5,248.30</span>
          </div>
          <div class="ticker-block">
            <span class="symbol">NVDA</span>
            <span class="delta">-0.42%</span>
            <span class="price">932.14</span>
          </div>
          <!-- ...repeat all tickers once, then REPEAT THE ENTIRE LIST A SECOND TIME for seamless loop... -->
        </div>
      </div>
      <div class="actions">
        <a href="/login">Login</a>
        <a href="/about">About</a>
      </div>
    </header>
    <!-- page content -->
  </main>
</div>
```

**Animation behavior:**

- Ticker marquee: 60-second linear infinite loop on `.nav-masthead .ticker-track`. CSS-only. Consumers MUST duplicate the ticker block markup (each ticker listed twice in sequence) for the `translateX(-50%)` mechanic to seamlessly loop.
- Ticker hover-swap: 200ms `--ease-out` opacity transition on `.delta` and `.price`. Triggered by `:hover` on `.ticker-block`.
- Ticker pause on hover: `.ticker-track:hover` sets `animation-play-state: paused` so the whole marquee halts when user hovers anywhere in the viewport.
- Rail width, hover background, chevron, mark/lockup crossfade, masthead scroll-hide transform: unchanged from prior nav promotion.

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
- Ticker marquee requires duplicated markup. Each ticker block appears TWICE in sequence inside `.ticker-track`. Without duplication, the `translateX(-50%)` marquee mechanic shows blank space as the list ends.
- Delta color is always `--ink-mid`. No color coding by direction (no green for positive, no red for negative). Direction is encoded by the `+/-` sign. Matches `/graphs` "never a second red, never green or amber" rule.
- Ticker block count in the actual data is open to consumer apps. Brand ships the structure; consumers populate the data.

**Usage:**

- Page shell: set `min-height: 100vh` on a page container OR on `.nav-composition` itself.
- Embedded widget: default `min-height: 0` on `.nav-composition` means the nav fits inside its container's height naturally.

### Indicator

Stat / numeral / delta primitives for the observational voice. Four recipes, each for a distinct job. All share the `.indicator` base class + `.label` / `.num` / `.delta` children, plus `.is-sm` / default / `.is-lg` size modifiers and `.is-dark` for coal / oxblood surfaces.

Indicators are content-sized by default. Consumers add `width: 100%` at their site when a column wants fill.

**The four recipes:**

| Class | Job |
|---|---|
| `.indicator-row` | Dashboard atom. Label / numeral / delta on one grid line. Default layout: `auto 1fr auto` grid. Ships with `.is-stacked` for narrow KPI cells (flex-column layout, delta left-aligned). |
| `.indicator-tabular` | Period-column comparison. Outer label + N rows of `.period / .val / .d`. Uses `font-variant-numeric: tabular-nums` for digit alignment. Canonical use: 1M / 3M / YTD performance. |
| `.indicator-gloss` | Editorial callout. JP kanji bookend (`.jp`) + Latin label + numeral + delta. Follows the `.eyebrow-gloss` convention. The JP character glosses the metric. |
| `.indicator-trend` | Sparkline + numeral. Tight cluster: numeral left, sparkline right of it with 10px gap. Sparkline is 1px `--ink` polyline with filled `--red` end-dot r=2. See `/graphs` sparkline micro-chart for the stroke + end-point convention. |

**Shared children (all four recipes):**

| Child | Role |
|---|---|
| `.label` | Metric name. Mono-caps, letterspaced. `--ink-mid` default, dimmed on dark surfaces via `.is-dark`. |
| `.num` | The primary numeric value. Mono tabular-nums. `--ink` default. Size steps per `.is-sm` / default / `.is-lg`. |
| `.delta` | The change value. Mono tabular-nums, `--ink-mid`. Direction encoded by `+/-` sign — NEVER color-coded. See Rules below. |

**Recipe-specific children:**

| Child | Recipe | Role |
|---|---|---|
| `.row` | `.indicator-tabular` | One period-row inside a tabular. Contains `.period`, `.val`, `.d`. |
| `.period`, `.val`, `.d` | `.indicator-tabular .row` | Period label (mono caps), numeric value, delta. Tabular-aligned. |
| `.label-row` | `.indicator-gloss` | Flex row containing `.jp` bookend + `.label`. |
| `.jp` | `.indicator-gloss` | The JP kanji gloss. `--red` on light surfaces, `--gold` via `.is-dark`. |
| `.main-row` | `.indicator-trend` | Flex row containing `.num` + `.spark`. Tight 10px gap; no space-between. |
| `.spark` | `.indicator-trend` | Inline SVG sparkline. 1px `--ink` stroke. Width/height steps per size modifier. |
| `.spark .endpoint` | `.indicator-trend .spark` | Filled `--red` circle at the polyline's last coordinate. r=2 default, r=3 at `.is-lg`. |

**Size modifiers:**

| Modifier | Use case |
|---|---|
| `.is-sm` | Peripheral / dense grids, KPI strips, inline-in-prose. |
| (default) | Dashboards, article embeds, standard cards. |
| `.is-lg` | Hero figures, ceremonial section anchors, chapter breaks. |

Each size modifier steps ALL of: label font-size + letter-spacing, numeral font-size, delta font-size, and the outer / inner gap appropriate to the recipe. Sparkline dimensions in `.indicator-trend` also step (52 / 84 / 220 px width).

**State modifiers:**

| Modifier | Applied to | Effect |
|---|---|---|
| `.is-dark` | Any `.indicator-*` | Flips foreground colors for use on `--paper-coal`, `--red-deep`, or `--ink` surfaces. On `.indicator-gloss`, also flips the JP character from `--red` to `--gold`. |
| `.is-stacked` | `.indicator-row` | Switches to a flex-column layout (label / num / delta stacked, delta left-aligned). Use in narrow KPI cells where the default horizontal grid would compress unreadably. |

**Canonical markup:**

```html
<!-- .indicator-row (default horizontal) -->
<div class="indicator indicator-row">
  <span class="label">PORTFOLIO</span>
  <span class="num">$847,230</span>
  <span class="delta">+2.3%</span>
</div>

<!-- .indicator-row.is-stacked for narrow KPI cells -->
<div class="indicator indicator-row is-stacked is-sm">
  <span class="label">EXPOSURE</span>
  <span class="num">72%</span>
  <span class="delta">+3.1%</span>
</div>

<!-- .indicator-tabular -->
<div class="indicator indicator-tabular">
  <span class="label">PORTFOLIO</span>
  <div class="row">
    <span class="period">1M</span>
    <span class="val">$847,230</span>
    <span class="d">+2.3%</span>
  </div>
  <div class="row">
    <span class="period">3M</span>
    <span class="val">$823,100</span>
    <span class="d">+5.2%</span>
  </div>
  <div class="row">
    <span class="period">YTD</span>
    <span class="val">$798,450</span>
    <span class="d">+8.4%</span>
  </div>
</div>

<!-- .indicator-gloss -->
<div class="indicator indicator-gloss">
  <div class="label-row">
    <span class="jp">指標</span>
    <span class="label">ALPHA · Q4</span>
  </div>
  <span class="num">+12.4%</span>
  <span class="delta">vs sector · S&P 500</span>
</div>

<!-- .indicator-trend -->
<div class="indicator indicator-trend">
  <span class="label">BTC</span>
  <div class="main-row">
    <span class="num">67,420</span>
    <svg class="spark" viewBox="0 0 84 24" preserveAspectRatio="none">
      <polyline points="0,18 12,16 24,17 36,13 48,11 60,9 72,7 84,5"/>
      <circle class="endpoint" cx="84" cy="5" r="2"/>
    </svg>
  </div>
  <span class="delta">+0.82% today</span>
</div>
```

**Rules:**

- Delta color is ALWAYS `--ink-mid`. NEVER color-code direction (no green for positive, no red for negative). Direction is encoded by the `+/-` sign. Matches the `/graphs` and `.nav-masthead` conventions. A site that genuinely needs direction coding must do it locally — it's not a brand primitive.
- Width defaults to content-sized. Consumers add `width: 100%` in their scene CSS where fill is wanted (ledgers, single-column stacks, card-bound rows).
- The sparkline stroke (1px `--ink`) and end-dot (filled `--red` r=2) are canonical. Do NOT override stroke color to red or widen the polyline to create a bar-like effect — that's a chart, not a sparkline.
- `.indicator-gloss.is-dark` on an oxblood or coal card flips the JP kanji to `--gold`. This CLAIMS the page's one-gold budget. Chains with `.eyebrow.is-gold`, `.eyebrow-dark` (default), `.btn.is-oxblood .jp`, and `.tbl.is-eyebrow-header` (with gold caption JP) — no two of these may appear on the same page. See /colors one-gold rule.
- `.is-stacked` is for narrow KPI cells. Don't use it in wide dashboards where horizontal would read cleaner.
- When composing `.indicator-row` with a sparkline next to it (positions list with trajectories), the pattern is scene-local, not a promoted recipe. Use a custom grid at the consuming site. Brand may promote an `.indicator-list` primitive in a future cycle.

**Composition:**

Indicators compose inside `.card-paper`, `.card-paper-sunken`, `.card-coal`, and `.card-oxblood`. Dark cards require `.is-dark` on the indicator. Light cards do not.

Indicators work inline inside `.nav-composition` content columns, inside editorial article bodies (max-width constrained), and in grid dashboards.

### Button

Press-mechanic primitives for CTAs, actions, and route navigation. Every button uses the same core mechanic:

- **REST** — raised (letterpress shadow, button sits slightly proud of the paper).
- **HOVER** — deboss (inset shadow, button visibly presses IN).
- **ACTIVE** — identical to HOVER. Touch users see the press animation briefly on tap; desktop users hold pressed-in while hovering.

Shadow transitions are `--duration-fast` `--ease-out`. No scale transforms, no rotations, no color-flipping on hover — the press IS the interaction.

**Surface modifiers:**

| Modifier | Surface |
|---|---|
| (default) `.btn` | Paper. Subtle letterpress. The common case. |
| `.is-primary` | Red fill. Main CTA. The loud voice. |
| `.is-ink` | Paper-coal fill with paper text. Rare use (dark standalone surface). |
| `.is-oxblood` | Red-deep ceremonial. Optional `.jp` kanji slot renders in gold. |
| `.is-outline` | Transparent fill with 1px `--ink` border. Ghost / secondary. |
| `.is-on-dark` | For buttons placed INSIDE `.card-coal`, `.card-oxblood`, or `.card-ink`. Transparent fill, paper border, paper text. Different press grammar: border-darkens on hover instead of deboss shadow. |

**Semantic modifier — `.is-route`:**

`.is-route` indicates the button NAVIGATES somewhere (to another page, to a position detail, to a route). It ADDS a `/` prefix via a `::before` pseudo-element — consumers DO NOT include the literal slash in the button's text content.

| With `.is-route` | Without `.is-route` |
|---|---|
| Button navigates: `/subscribe`, `/btc`, `/about` | Button performs: Submit, Cancel, Confirm, Close |
| Label: tight letter-spacing, mixed case | Label: mono uppercase, tracked 0.16em |

The `/` prefix is semantic, not decorative. Matches the `.nav-rail .nav-item .slash` and `.nav-masthead .ticker-block .symbol::before` conventions already established in brand.

**Size modifiers:**

| Modifier | Use case |
|---|---|
| `.is-sm` | Inline-in-prose, tertiary actions, dense UI rows. |
| (default) | Standard CTAs, form buttons, standard nav. |
| `.is-lg` | Hero CTAs, marketing flagship, feature callouts. |

Each size modifier steps padding, font-size, and shadow offset proportionally. The press mechanic stays legible across all three sizes — though `.is-sm` raise is subtle-by-design at inline-prose scale (correct behavior: a tiny button shouldn't dominate a paragraph).

**Disabled state:**

Any button can be disabled via the `disabled` attribute or `[aria-disabled="true"]`. Disabled vocabulary:

- Text: `--ink-pale`
- Background: unchanged (keeps surface context)
- Shadow: flat (no raise, no press response)
- `cursor: not-allowed`
- `pointer-events: none` (hover/active states don't fire)

This is brand's DISABLED CONVENTION. A future cycle may apply this convention across other primitives (form fields, nav items, indicators) — for now it's established in Button.

**Canonical markup:**

```html
<!-- Default action button (no slash) -->
<button class="btn">Submit</button>

<!-- Primary CTA -->
<button class="btn is-primary">Subscribe</button>

<!-- Route button (navigates; slash added by ::before) -->
<a class="btn is-route" href="/subscribe">subscribe</a>
<!-- Consumer writes "subscribe" — the "/" renders automatically. -->

<!-- Primary route CTA -->
<a class="btn is-primary is-route" href="/open-position">open-position</a>

<!-- Outline secondary -->
<button class="btn is-outline">Learn More</button>

<!-- Size variants -->
<button class="btn is-sm">Copy</button>
<button class="btn is-primary is-lg">Schedule a Call</button>

<!-- Oxblood ceremonial with optional gold kanji -->
<button class="btn is-oxblood">
  <span class="jp">観</span>
  Open Position
</button>
<!-- The .jp kanji claims the page's one-gold budget. -->

<!-- Button inside a dark card -->
<div class="card card-oxblood">
  <a class="btn is-on-dark is-route" href="/methodology">methodology</a>
</div>

<!-- Disabled button -->
<button class="btn is-primary" disabled>Submit</button>
<button class="btn is-primary" aria-disabled="true">Submit</button>
```

**Rules:**

- Press mechanic is non-negotiable. Every on-brand button uses REST→HOVER→ACTIVE as raised→deboss→deboss. No alternative hover behaviors (no fade, no slide, no scale).
- `.is-primary` and `.is-oxblood` are mutually exclusive. Red on red-deep is unreadable. A page's flagship CTA is EITHER primary OR oxblood, never both.
- `.is-primary` inside `.card-oxblood` is forbidden — same readability failure. Use `.is-on-dark` for buttons nested inside dark cards.
- `.is-route` indicates the button navigates. NEVER use it for buttons that perform an action (Submit, Cancel, etc.). The slash semantic must mean "there is a route here."
- Button text for `.is-route` does NOT include a literal `/` — the slash is supplied by a `::before` pseudo-element. Consumers write `href="/subscribe"` and label text `subscribe` — the pseudo-element adds the visible prefix.
- Gold kanji slot (`.btn.is-oxblood .jp`) CLAIMS the page's one-gold budget. Cross-refers /colors one-gold rule and chains with `.eyebrow.is-gold`, `.eyebrow-dark` (default), `.indicator-gloss.is-dark`, and `.tbl.is-eyebrow-header` (with gold caption JP) — no two of these may appear on the same page.
- Sentient italic is NEVER used for button labels. Sentient is editorial display typography; UI chrome uses mono or Satoshi.
- Disabled state is `--ink-pale` text + flat shadow + cursor not-allowed. No red-X, no strikethrough, no tooltip chrome.
- `.is-masthead`-style buttons (mono-caps, no press, color-shift-only) are NOT a button variant. The masthead-action pattern lives at `.nav-masthead .actions a` — it's a nav concern, not a button concern.

**Composition:**

Buttons compose inside forms, card footers, nav rails, editorial article bodies, ticker mastheads (as form actions, not as masthead-action links), and inline within Satoshi prose.

Inside dark cards (`.card-coal`, `.card-oxblood`, `.card-ink`), ALWAYS use `.btn.is-on-dark` — NEVER `.is-primary` or other filled variants. The `.is-on-dark` modifier exists specifically for this composition.

A form footer typically pairs one `.is-outline` or default button (Cancel) with one `.is-primary` button (Save, Submit). Primary sits on the right (forward action convention).

**Naming note — `.is-on-dark` vs `.is-dark`:**

Button uses `.is-on-dark` (not `.is-dark`) because the modifier describes a button's POSITION — it sits ON a dark surface — not its own identity. The press mechanic actually changes in this context (border-darken instead of deboss shadow).

Eyebrow uses `.eyebrow-dark` (compound class, legacy from earlier promotion). Indicator uses `.is-dark` (modifier, matches the indicator's own identity when placed on dark). The three conventions differ by intent.

A future cycle may harmonize these into one convention. For now, each primitive's dark-surface treatment uses its own established pattern.

### Table

Tabular data primitive. Hairline-only structural base. Mono-caps left-aligned headers. `tabular-nums` on all numeric cells. Hover shifts row background to `--paper-deep`. Single `.tbl` recipe with two categories of modifiers.

**Architecture — surface vs capability modifiers:**

| Category | Prefix | Behavior |
|---|---|---|
| Surface | `.is-*` | Assert a surface treatment. Do NOT compose with each other — each takes over styling. Pick one at most. |
| Capability | `.has-*` | Feature flags. Compose freely with each other AND with surface modifiers. Stack as many as needed. |

This split is a cross-cutting brand pattern. Future recipes that need mutually-exclusive treatments plus feature additions can adopt the same convention.

**Surface modifiers (at most one per table):**

| Modifier | Treatment |
|---|---|
| (default) `.tbl` | Hairline base. Dashboard-ready at default density. |
| `.is-dense` | Tight dashboard density (8/0 padding, 12px body, 9px caps headers). |
| `.is-article` | Article-embedded density (10/0 padding, 32px col-gap, paragraph-friendly). |
| `.is-dark` | Paper text + rgba-paper row dividers. For placement inside `.card-coal`, `.card-oxblood`, `.card-ink`. |
| `.is-slash` | First-column row labels prefixed with `/` via `::before`. Matches `.nav-rail .nav-item .slash`, `.nav-masthead .ticker-block .symbol::before`, and `.btn.is-route::before` conventions. |
| `.is-eyebrow-header` | `<caption>` renders as an eyebrow-gloss banner. If caption contains a JP character in `--gold`, CLAIMS the page's one-gold budget. |

**Capability flags (stack freely):**

| Modifier | Adds |
|---|---|
| `.has-sort` | Sortable-column carets on `th.is-sortable`. See sort-indicator spec below. |
| `.has-totals` | `tfoot.totals` row with distinct weight + 1px `--ink` top rule. |
| `.has-hanko` | Reserves `td.cell-hanko` (36px, pad-stripped). Consumer places `.hanko.is-22` inside. |
| `.has-trend` | Reserves `td.cell-trend`. Consumer places `.indicator-trend .spark` SVG inside. |
| `.has-expandable` | `.row.is-expandable` + `.row.is-open` + `.row-detail` for click-to-expand detail drawer. Visual affordance only — consumer owns state toggle (matches `.nav-masthead .is-hidden` contract). |

**Preset bundle:**

| Preset | Expands to |
|---|---|
| `.is-ledger` | `td.balance` + `th.balance-h` styling — hairline separator + 500 weight on a running-balance column. Use for transaction ledgers. |

**Cell-role helpers (scoped under `.tbl`):**

| Helper | Use |
|---|---|
| `td.num`, `td.pct`, `td.wt`, `td.delta` | Right-aligned numeric cells with tabular-nums. |
| `td.sym` | Ticker symbols — mono 500 weight. |
| `td.name` | Narrative labels — Satoshi normal. |
| `td.muted`, `td.pale` | Color tier helpers (`--ink-mid`, `--ink-pale`). |

**Sort-indicator spec (first brand use):**

Tables with `.has-sort` add visible sort indicators to sortable columns.

- Inactive column: dual caret `▲▼` in `--ink-pale`.
- Active column: single arrow (`▲` for asc, `▼` for desc) in `--ink`.
- Monochrome only. No colored sort states. No bouncy animation on sort change — direction change is instantaneous.
- Consumer markup: `<th class="is-sortable">` for sortable columns, adding `.is-sorted-asc` or `.is-sorted-desc` for the active direction.

This convention applies anywhere sort indicators are needed, not just tables. Future primitives (filterable lists, sortable card grids) reuse the same caret + color rules.

**Pagination:**

Tables can include a `tfoot.pagination` row or trailing `.pagination-bar` with prev/next links. Disabled state reuses the Button DISABLED CONVENTION:

- `--ink-pale` text
- `pointer-events: none`
- `cursor: not-allowed`
- No shadow

See /components Button for the full disabled spec.

**Canonical markup:**

```html
<!-- Base dashboard table -->
<table class="tbl is-dense">
  <thead><tr>
    <th>Ticker</th><th>Name</th>
    <th class="num">Shares</th><th class="num">Entry</th>
    <th class="num">Current</th><th class="num">P&L</th>
  </tr></thead>
  <tbody>
    <tr>
      <td class="sym">BTC</td>
      <td class="name">Bitcoin</td>
      <td class="num">0.5</td>
      <td class="num">$63,200</td>
      <td class="num">$67,420</td>
      <td class="num">+$2,110</td>
    </tr>
    <!-- ... more rows ... -->
  </tbody>
</table>

<!-- Dashboard with sort, trend, totals (capability stack) -->
<table class="tbl is-dense has-sort has-trend has-totals">
  <thead><tr>
    <th class="is-sortable is-sorted-desc">Ticker <span class="caret">▼</span></th>
    <th>Name</th>
    <th class="num is-sortable">Shares <span class="caret">▲▼</span></th>
    <th class="num">Current</th>
    <th>Trend</th>
  </tr></thead>
  <tbody>
    <tr>
      <td class="sym">BTC</td>
      <td class="name">Bitcoin</td>
      <td class="num">0.5</td>
      <td class="num">$67,420</td>
      <td class="cell-trend">
        <svg class="spark" viewBox="0 0 84 24" preserveAspectRatio="none">
          <polyline points="..."/>
          <circle class="endpoint" cx="84" cy="5" r="2"/>
        </svg>
      </td>
    </tr>
  </tbody>
  <tfoot class="totals">
    <tr>
      <td class="label" colspan="3">Total</td>
      <td class="num">$247,230</td>
      <td></td>
    </tr>
  </tfoot>
</table>

<!-- Ledger with running balance (preset) -->
<table class="tbl is-ledger">
  <thead><tr>
    <th>Date</th><th>Description</th>
    <th class="num">Debit</th><th class="num">Credit</th>
    <th class="balance-h num">Balance</th>
  </tr></thead>
  <tbody>
    <tr>
      <td>2025-04-18</td>
      <td class="name">Initial deposit</td>
      <td class="num"></td>
      <td class="num">$50,000</td>
      <td class="balance num">$50,000</td>
    </tr>
  </tbody>
</table>

<!-- Schedule/calendar (base .tbl + .badge, no preset needed) -->
<table class="tbl is-dense">
  <thead><tr>
    <th>Date</th><th>Event</th><th>Impact</th>
    <th class="num">Forecast</th><th class="num">Prior</th>
  </tr></thead>
  <tbody>
    <tr>
      <td>May 1</td>
      <td class="name">FOMC Statement</td>
      <td><span class="badge is-high">High</span></td>
      <td class="num">—</td>
      <td class="num">5.50%</td>
    </tr>
  </tbody>
</table>

<!-- Inside a dark card -->
<div class="card card-coal">
  <table class="tbl is-dark is-dense">
    <!-- same structure; .is-dark handles the color flips -->
  </table>
</div>

<!-- Slash vernacular -->
<table class="tbl is-slash is-dense">
  <tbody>
    <tr><td>spx</td><td class="num">5,248.30</td><td class="num">+0.18%</td></tr>
    <!-- first-column "/" prefix added by ::before -->
  </tbody>
</table>
```

**Rules:**

- Surface modifiers (`.is-dense`, `.is-article`, `.is-dark`, `.is-slash`, `.is-eyebrow-header`) do NOT compose with each other. One surface assertion per table.
- Capability flags (`.has-sort`, `.has-totals`, `.has-hanko`, `.has-trend`, `.has-expandable`) compose freely with each other and with surface modifiers.
- Numeric cells use `tabular-nums`. Non-negotiable for financial data.
- Row dividers are 1px `--ink-faint` hairlines on paper surfaces, `rgba(241,236,224,0.08)` on dark surfaces. No thick borders, no double lines.
- Delta cells use `+/-` sign for direction. NEVER color-code direction (matches `/graphs`, `.nav-masthead`, `.indicator-*`, `.btn` conventions).
- Red usage: one emphasis per table maximum. Red does not encode direction — only ceremonial attention on a specific row.
- Sort indicators are monochrome carets — never colored.
- `.tbl.is-eyebrow-header` with a gold JP character in its caption CLAIMS the page's one-gold budget. Chains with `.eyebrow.is-gold`, `.eyebrow-dark` (default), `.indicator-gloss.is-dark`, `.btn.is-oxblood .jp` — no two of these may appear on the same page. See /colors one-gold rule.
- `.has-expandable` ships the visual affordance only. Consumer owns the state toggle (via `.is-open` class or `:checked + sibling` CSS pattern or ~5 lines of JS). Matches `.nav-masthead .is-hidden` scroll-hide contract.
- Sentient italic is NEVER used inside a table cell. Sentient is editorial display; data cells use mono + Satoshi.
- Cross-recipe composition is encouraged: `.hanko.is-22` in `.has-hanko td.cell-hanko`, `.indicator-trend .spark` in `.has-trend td.cell-trend`, `.badge` in any cell.

**Composition:**

Tables compose inside `.card-paper`, `.card-paper-sunken`, `.card-coal`, `.card-oxblood`, inside article columns (with `.is-article`), and in dashboard grids. Dark cards ALWAYS use `.is-dark`.

### Badge

Small inline severity/status tag. Usable in table cells, log entries, incident rows, inline prose, anywhere a status pill fits. Severity encoded by INK WEIGHT, never by color.

**Hierarchy — base is neutral, modifiers step up or down:**

| Class | Treatment | Use case |
|---|---|---|
| `.badge` (default) | `--ink-mid` text + `--ink-faint` border, 500 weight | Informational/default status |
| `.badge.is-low` | `--ink-pale` text + `--ink-pale` border | Quietest. Minor items. |
| `.badge.is-med` | `--ink-mid` text + `--ink-mid` border, 500 weight | Elevated. Notable items. |
| `.badge.is-high` | `--ink` text + `--ink` border, 600 weight | Loudest. Critical items. Still ink-only — never red/amber/green. |

**Canonical markup:**

```html
<span class="badge">Active</span>
<span class="badge is-low">Draft</span>
<span class="badge is-med">Review</span>
<span class="badge is-high">Critical</span>
```

**Rules:**

- Severity is encoded by ink WEIGHT (500 → 600) and ink TIER (`--ink-pale` → `--ink-mid` → `--ink`). NEVER by color. No red for critical, no amber for warning, no green for success.
- The lowest severity fades toward `--ink-pale`; the highest approaches `--ink`. Same vocabulary as `.indicator-gloss` label hierarchy.
- Badges use `font-variant-numeric: normal` so they render correctly inside table cells that have `tabular-nums` applied.
- Badges are INLINE elements. Don't use them as block-level status banners — use cards or eyebrows for that.
- Badges do NOT have a `.is-red` or `.is-gold` variant. Ceremony belongs to eyebrows and indicators; badges are utilitarian.

**Composition:**

Badges compose inside table cells (impact columns, status columns), inside log entries, inline-in-prose (for status noting), and inside `.indicator-row`'s delta cell when a text status fits better than a numeric delta (rare).

### Chart

Full-scale line and bar chart primitive. Ships as `.chart` with chart-type modifiers (`.is-line-single`, `.is-line-multi`, `.is-bar-grouped`), surface modifier (`.is-dark`), size modifiers (`.is-sm` / `.is-lg`), and capability flags (`.has-gridlines`, `.has-reference-line`, `.has-value-labels`, `.has-annotations`).

Full specification lives at /graphs — see **Line chart**, **Bar chart**, and **Interactivity** subsections there. This entry exists in /components for discoverability alongside the other primitives.

The chart primitive is the first brand recipe to ship with a companion JavaScript helper (`brand/dist/charts.js`). Sort indicators, scroll-hide, and expandable-row interactions remain consumer-owned per the visual-affordance-only contract. Charts are the documented exception.

See /graphs for:

- Sparkline micro-chart (the `.indicator-trend .spark` precedent)
- Line chart (full-scale extension, single + multi series)
- Bar chart (grouped, diverging)
- Interactivity (`data-chart-interactive` opt-in, tooltip/crosshair JS)

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

### Sparkline micro-chart

The `.indicator-trend` recipe renders a sparkline: a miniature line chart co-located with a numeral. Sparklines follow the same stroke + end-point convention as full `/graphs` charts, just scaled down.

**Canonical treatment:**

- Stroke: `polyline`, 1px, `--ink` color. At `.is-lg`, stroke-width steps to 1.25 for the hero figure.
- Fill: none (no filled area under the curve).
- End-point marker: filled `--red` circle at the polyline's final coordinate. r=2 default (`.is-sm` and default sizes), r=3 at `.is-lg`.
- No axis lines, no tick marks, no gridlines, no axis labels. Sparkline communicates shape, not magnitude.
- No baseline rule (no horizontal line at zero). The polyline and end-dot carry the full signal.

**Rationale:**

A sparkline is the chart language at miniature scale. The line carries trajectory. The filled red end-dot is the same signal-carrier as the r=3.5 red dot on a full chart — it marks the most recent observation. The reader's eye collects shape before parsing the numeral.

**Dimensions:**

| Size modifier | Width | Height |
|---|---|---|
| `.indicator-trend.is-sm .spark` | 52 px | 14 px |
| `.indicator-trend .spark` (default) | 84 px | 24 px |
| `.indicator-trend.is-lg .spark` | 220 px | 44 px |

All widths and heights are literals tuned to the size ladder — not tokens.

**Rules:**

- Stroke color is `--ink` (dark ink on paper surfaces). On dark surfaces via `.is-dark`, stroke flips to `--paper`. End-dot stays `--red` across all surfaces — it is the brand signal.
- Never widen the stroke to create a bar-like effect. A sparkline is a line, not a chart.
- Never use a second color on the polyline. Only `--ink` or (dark surfaces) `--paper`. The red dot is the ONLY color.
- Polyline data points: 6-10 is ideal. Too few (3-4) reads as a fragment; too many (20+) becomes noise at miniature scale.
- `preserveAspectRatio="none"` on the SVG: the polyline stretches to fill the cell exactly. Intended — sparklines are about relative shape, not absolute proportion.

**Forbidden:**

- Bar-chart micro-charts. Brand has no bar primitive at any scale.
- Area-filled sparklines. Fill under the curve violates the "signal in line + dot" contract.
- Second end-dot, tick marks, or gridlines.
- Axis labels inside the sparkline SVG. Context is provided by the surrounding `.indicator-trend` label and delta.

**Composition:**

The sparkline lives exclusively inside `.indicator-trend`. It is not a standalone primitive. Consumers do not render `<svg class="spark">` outside the `.indicator-trend` markup.

For full-size charts (anything larger than `.indicator-trend.is-lg` at 220×44), use the main `/graphs` conventions at the top of this section — not the sparkline spec.

### Line chart

Full-scale line chart. Extends the sparkline language to charts with axes, labels, and interactivity. Ships as a single `.chart` recipe with chart-type + surface + size + capability modifiers.

**Continuity with sparkline:**

| Scale | Stroke width | Endpoint radius |
|---|---|---|
| Sparkline `.is-sm` | 1 px `--ink` | r=2 |
| Sparkline default | 1 px `--ink` | r=2 |
| Sparkline `.is-lg` | 1.25 px `--ink` | r=3 |
| Chart `.is-sm` | 1.25 px `--ink` | r=3 |
| Chart default | 1.25 px `--ink` | r=3.5 |
| Chart `.is-lg` | 1.5 px `--ink` | r=4 |

Continuous ladder from micro to hero. A sparkline is a chart that chose to be quiet; a chart is a sparkline that earned labels.

**Single-series line (`.chart.is-line-single`):**

| Element | Treatment |
|---|---|
| Polyline | 1.25 px stroke `--ink`, no fill |
| End-point | Filled `--red`, r=3.5 default (r=3 small, r=4 large) |
| X-axis | 1 px `--ink` baseline |
| Y-axis | No visible line; 3-4 tick labels floating in `--ink-pale` mono 9 px |
| Gridlines | OFF by default. `.has-gridlines` adds 1 px `--ink-faint` horizontal rules at each y-tick. |
| Background | `--paper` (inherited from page) |

**Multi-series line (`.chart.is-line-multi`):**

Up to 3 series. Ink-family ladder; red reserved for a single end-dot on the primary series.

| Series | Stroke | Width | Dash |
|---|---|---|---|
| `.is-primary` | `--ink` | 1.25 px | none |
| `.is-secondary` | `--ink-soft` | 1 px | none |
| `.is-tertiary` | `--ink-mid` | 1 px | 3-2 |

End-point labels (not a legend row). Each line ends with its name in mono 9 px at the final coordinate, colored to match the line. This keeps the legend visually tied to the data and avoids a separate chrome row above the chart.

NEVER use a second red. NEVER use green, amber, or teal. Only the ink family ladder + one red end-dot total per chart.

**Size modifiers:**

| Modifier | Max width |
|---|---|
| `.is-sm` | 360 px |
| (default) | 640 px |
| `.is-lg` | 960 px |

Consumer SVG viewBox should be proportioned to the size modifier (viewBox `0 0 640 260` is a reasonable default).

**Dark surface (`.is-dark`):**

For charts nested inside `.card-coal`, `.card-oxblood`, or `.card-ink`. Polyline stroke flips to `--paper`. Axis tick and gridline colors flip to rgba-paper alpha. Red end-dot STAYS red — the red dot is the brand signal, not a surface-dependent color.

**Capability flags (line chart):**

| Modifier | Adds |
|---|---|
| `.has-gridlines` | 1 px `--ink-faint` horizontal rules at each y-tick |
| `.has-reference-line` | 1 px `--ink-pale` horizontal dashed (4-3 pattern) at a named benchmark value. Include via `<line class="reference-line">` element. |
| `.has-annotations` | Consumer adds `<line class="annotation-pointer">` + `<text class="annotation-label">` to call out specific points. |

**Canonical markup:**

```html
<!-- Single-series, minimal (no gridlines default) -->
<svg class="chart is-line-single" viewBox="0 0 640 260" preserveAspectRatio="xMidYMid meet">
  <!-- optional: x-axis line, y-tick labels -->
  <line class="axis-line" x1="40" y1="240" x2="620" y2="240"/>
  <text class="axis-tick" x="40" y="20">$70k</text>
  <text class="axis-tick" x="40" y="80">$65k</text>
  <text class="axis-tick" x="40" y="140">$60k</text>
  <text class="axis-tick" x="40" y="200">$55k</text>
  <!-- the data -->
  <polyline class="series" points="40,180 100,165 160,170 220,150 ..."/>
  <circle class="endpoint" cx="620" cy="85" r="3.5"/>
</svg>

<!-- Multi-series with end-point labels -->
<svg class="chart is-line-multi" viewBox="0 0 640 260">
  <polyline class="series is-primary" points="..."/>
  <polyline class="series is-secondary" points="..."/>
  <polyline class="series is-tertiary" points="..."/>
  <circle class="endpoint" cx="620" cy="95" r="3.5"/>
  <text class="end-label" x="624" y="98" fill="var(--ink)">FUND</text>
  <text class="end-label" x="624" y="118" fill="var(--ink-soft)">BENCH</text>
  <text class="end-label" x="624" y="138" fill="var(--ink-mid)">INDEX</text>
</svg>
```

**Rules:**

- Polyline stroke: `--ink` on paper, `--paper` on dark. Never `--red`. The polyline carries trajectory; red carries the signal.
- Red: ONE per chart maximum — the end-dot on the primary series. Not on every series.
- Multi-series: ink-family ladder only. Never a second red, never green/amber/teal.
- End-point labels over legend rows. The label is the data's name at its destination.
- Gridlines OFF by default (line-single). Opt in via `.has-gridlines` when magnitude comparison matters.
- Dash patterns reserved by semantic: 3-2 for tertiary series (continuous data, de-emphasized), 4-3 for reference lines and forecast extensions (interpretive overlay), 4-3 for the interactive crosshair (transient cursor).
- All chart text (ticks, labels, annotations) uses mono. Never Sentient. Never Satoshi. Data is not display.
- Interactive charts MUST have an explicit `viewBox` attribute. The charts.js helper reads viewBox dimensions to size the crosshair.

### Bar chart

Grouped bar charts for categorical comparison. Vertical bars, 2-3 bars per category.

**Grouped bar (`.chart.is-bar-grouped`):**

| Element | Treatment |
|---|---|
| Primary bars | Fill `--red`, no stroke |
| Secondary bars | Fill `--ink-soft`, no stroke |
| Tertiary bars | Fill `--ink-mid`, no stroke |
| X-axis | 1 px `--ink` baseline |
| Y-axis | No visible line; tick labels in `--ink-mid` mono 9 px |
| Gridlines | ON by default. 1 px `--ink-faint` horizontal rules. Bars need gridlines for magnitude comparison. |
| Bar width | 12 px default. 8 px at `.is-sm`, 16 px at `.is-lg`. |
| Inter-bar gap | 2 px (within a group) |
| Inter-group gap | 16 px default, 10 px at `.is-sm`, 24 px at `.is-lg` |
| Category labels | Mono 9 px `--ink-mid` below x-axis, centered under each group |

**Color encoding:** Same rule as line charts — ink-family ladder plus ONE red. Primary position uses red; secondary and tertiary step through `--ink-soft` and `--ink-mid`. Red is ceremony, not direction. Negative values do NOT get a different color — they get a negative sign and stay in the ink family.

**Capability flags (bar chart):**

| Modifier | Adds |
|---|---|
| `.has-value-labels` | Numeric value above each bar in mono 9 px `--ink` |
| `.has-reference-line` | Dashed `--ink-pale` horizontal benchmark line |
| `.has-gridlines` | Redundant on bar charts (already ON); present for consistency |

**Diverging bar pattern:**

For signed data (e.g. P&L by position), place the x-axis at y=0 with positive bars extending up and negative bars extending down. Both directions use the same red/ink-soft/ink-mid palette. Do NOT color-code positive vs negative.

**Canonical markup:**

```html
<svg class="chart is-bar-grouped has-value-labels" viewBox="0 0 640 280">
  <!-- gridlines default on -->
  <line class="gridline" x1="50" y1="50" x2="620" y2="50"/>
  <line class="gridline" x1="50" y1="110" x2="620" y2="110"/>
  <line class="gridline" x1="50" y1="170" x2="620" y2="170"/>
  <!-- x-axis -->
  <line class="axis-line" x1="50" y1="230" x2="620" y2="230"/>
  <!-- y-ticks -->
  <text class="axis-tick" x="40" y="54">$30k</text>
  <text class="axis-tick" x="40" y="114">$20k</text>
  <text class="axis-tick" x="40" y="174">$10k</text>
  <!-- group 1 -->
  <rect class="bar is-primary"   x="80"  y="120" width="12" height="110"/>
  <rect class="bar is-secondary" x="94"  y="145" width="12" height="85"/>
  <rect class="bar is-tertiary"  x="108" y="160" width="12" height="70"/>
  <text class="value-label" x="86"  y="115">$22k</text>
  <text class="value-label" x="100" y="140">$17k</text>
  <text class="value-label" x="114" y="155">$14k</text>
  <text class="axis-tick" x="105" y="248">Q1</text>
  <!-- group 2, 3, 4 ... -->
</svg>
```

**Rules:**

- Primary = red. Secondary = `--ink-soft`. Tertiary = `--ink-mid`.
- Negative values: same palette, extend below x-axis baseline.
- Never color-code positive vs negative direction.
- Bar width is fixed by size modifier (8/12/16 px). Consumers don't override unless the chart is unusually wide.
- Gridlines default ON for bar charts — bars need them.
- Value labels (`.has-value-labels`) are optional. Use when exact values matter more than shape comparison.

### Interactivity

Brand ships a single JS helper, `brand/dist/charts.js`, that wires hover + tooltip + crosshair behavior on any chart SVG opted in via the `data-chart-interactive` attribute.

This is the ONLY JavaScript in brand/dist/. All other brand interactivity (scroll-hide masthead, sort indicators, expandable table rows) remains consumer-owned per the visual-affordance-only contract. Charts are the documented exception — hover tooltip logic is non-trivial enough to justify centralization.

**What charts.js provides:**

| Feature | Behavior |
|---|---|
| Vertical crosshair | 1 px `--ink-faint` dashed line tracking mouse X. Dash pattern 4-3 (same as reference lines). |
| Point highlight | Nearest data point gets a visible ring on hover. |
| Tooltip | Mono 10 px box above the hovered point. `--paper` background, 1 px `--ink-faint` border, 2 px radius. Shows x/y values using `data-xlabel` and `data-ylabel` from the polyline. |
| Series dim | When hovering a multi-series chart, non-hovered series dim to 0.3 opacity. |

**Consumer contract:**

1. Load `brand/dist/charts.js` via a `<script src="..." defer>` tag.
2. Add `data-chart-interactive` to any `.chart` SVG to opt in.
3. Optionally add `data-xlabel` and `data-ylabel` attributes on each `<polyline class="series">` to customize tooltip text.
4. SVG MUST have an explicit `viewBox` attribute — the helper reads viewBox dimensions to size the crosshair.

```html
<svg class="chart is-line-multi" viewBox="0 0 640 260"
     data-chart-interactive>
  <polyline class="series is-primary"
            points="..."
            data-xlabel="Month" data-ylabel="$"/>
  ...
</svg>
```

**What charts.js does NOT provide:**

- Sort logic, zoom, pan, real-time data updates — consumer-owned.
- Animation on render — brand ships static charts; animated entry is a consumer choice.
- Mobile touch/tap interactions beyond default hover emulation.
- Multiple-point tooltip (showing all series values at one X) — current helper shows only the hovered polyline's nearest point. Future helper iteration may add this.

**Dark-surface tooltips:**

Tooltips inside `.card-coal` or `.card-oxblood` get a subtle cast shadow to lift off the dark background. Tooltip background stays `--paper` — the tooltip is a callout, not a surface-dependent element.

**Dash-pattern vocabulary:**

Three distinct dash patterns with distinct semantics:

| Pattern | Used for |
|---|---|
| 3-2 | Tertiary series (continuous, de-emphasized) |
| 4-3 | Reference lines, forecast extensions, interactive crosshair |
| No dash | Primary + secondary series, axis lines, gridlines |

**Data-attribute API pattern:**

`data-chart-interactive` is brand's first opt-in data-attribute API. Future primitives that need consumer JS opt-in (e.g. sortable tables, expandable cards) will follow the same pattern: `data-[feature]-interactive` or `data-[feature]-enabled`.

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
