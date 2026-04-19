# Brand — Kujaku Investments

The brand subsystem of the Kujaku platform. This folder is the single source of truth for what every Kujaku-branded surface looks like, how it sounds, and how it behaves visually.

This README is the architecture contract: how the folder is organized, how it grows, how it's consumed by frontends. The visual rules themselves live in `STYLE.md`. The rendered visual reference lives in `specimen.html`.

If a decision isn't covered in `STYLE.md`, it doesn't exist. Don't invent. Ask.

---

## Mental model

Brand is **identity**. Sites are the **application** of identity. These are different concerns and they live in different places.

- `brand/` contains primitives that would be **identical** on every Kujaku-branded site: colors, fonts, the card recipe, the hanko stamp, the eyebrow, the underline reveal, the paper texture.
- A consuming frontend (e.g. a future `web/` folder, or a separate `kujaku-web` repo) contains **its own** layout, navigation, page structure, and one-off styling. It pulls brand primitives in by referencing `brand/dist/`.

The promotion criterion: *would this be identical on a different Kujaku site?* If yes → brand. If "probably not" or "I'd want to tweak it for the next site" → keep it site-local.

This separation is non-negotiable. Putting site-specific styles in `brand/` turns the folder into a junk drawer and defeats the entire point of having a brand subsystem.

---

## Where brand sits in the monorepo

```
kujaku-meta/                            (the platform monorepo)
├── .git/
├── .gitignore                          (must include sandbox/)
├── README.md                           (meta README)
├── NOTES.md
├── SYSTEM.md
├── bot-kalshi15min-btc/                (Layer 2 bot service)
├── data/                               (Layer 1 collector service)
│
├── brand/                              ← THIS FOLDER
│   ├── README.md                       this file — the architecture contract
│   ├── STYLE.md                        the design rules (renamed from brand_style.md)
│   ├── specimen.html                   rendered visual reference (renamed from brand_style.html)
│   │
│   └── dist/                           the consumable surface — what frontends import
│       ├── tokens.css                  CSS custom properties (colors, fonts, sizes, easings, durations)
│       ├── fonts.css                   @font-face declarations pointing to local woff2 files
│       ├── reset.css                   base resets brand assumes
│       ├── recipes.css                 reusable patterns (.card, .eyebrow, .hanko, .reveal, etc.)
│       ├── textures.css                body background, emboss shadows, watermark
│       ├── logo-mark-red.svg           mark, flat, red (default scale color)
│       ├── logo-mark-red-pressed.svg   mark, pressed, red (primary mark — default)
│       ├── logo-mark-gold.svg          mark, flat, gold (ceremonial)
│       ├── logo-mark-gold-pressed.svg  mark, pressed, gold
│       ├── logo-mark-ink.svg           mark, flat, ink (print/monochrome)
│       ├── logo-mark-ink-pressed.svg   mark, pressed, ink
│       ├── logo-mark-paper.svg         mark, flat, paper (for dark bg)
│       ├── logo-mark-paper-pressed.svg mark, pressed, paper (press-light filter)
│       ├── logo-lockup-red.svg         lockup, flat, red + ink text
│       ├── logo-lockup-red-pressed.svg lockup, pressed scales + flat text (primary lockup)
│       ├── logo-lockup-gold.svg        lockup, flat, gold scales + paper text
│       ├── logo-lockup-gold-pressed.svg
│       ├── logo-lockup-paper.svg       lockup, flat, paper scales + paper text (dark bg)
│       ├── logo-lockup-paper-pressed.svg
│       ├── fonts/                      woff2 font files (see Fonts section)
│       └── assets/
│           ├── illustrations/          koi, brushwork, sumi-e plates
│           └── icons/                  SVG icons (when needed)
│
└── sandbox/                            ← scratch space. GITIGNORED. freely deletable.
                                          (sibling to brand, not inside it — see Sandbox section)
```

Brand is a subfolder of the meta monorepo, not a standalone repo. Frontends consume it by pinning to a `kujaku-meta` commit SHA via git submodule and referencing `vendor/kujaku-meta/brand/dist/`. This is sub-optimal — the submodule drags along the bot code, data collector code, and meta docs that the frontend doesn't need — but it's simple and works for v1. If the indirection ever becomes painful, brand splits into its own `kujaku-brand` repo. That migration is cheap and reversible.

---

## What goes in each `dist/` file

The split is by **concern**, not by component. Adding a new shadow recipe goes in `textures.css`. Adding a new component pattern goes in `recipes.css`. Adding a new color variable goes in `tokens.css`. Don't create new files unless a genuinely new concern emerges.

| File | Scope |
|---|---|
| `tokens.css` | Pure CSS custom properties. Color palette, type scale, font families, spacing scale, easing curves, durations. No selectors. No rules. Just `:root { --foo: ...; }`. |
| `fonts.css` | `@font-face` declarations only. Points to local woff2 files in `dist/fonts/`. Loads the weights specified in STYLE.md. |
| `reset.css` | Minimal base reset. Box-sizing, body defaults, link defaults, image defaults. Not a full Normalize.css — only what brand explicitly assumes. |
| `recipes.css` | Reusable component patterns. `.card`, `.eyebrow`, `.hanko`, `.reveal`, `.reveal-frame`, `.watermark`. Each must be self-contained — usable by adding the class to a single element. |
| `textures.css` | Surface treatments. Body background (the three-layer cardstock recipe), emboss shadow utilities, kanji watermark. |
| `logo-*.svg` | 14 logo variants: `logo-mark-{token}[-pressed].svg` and `logo-lockup-{token}[-pressed].svg` where `{token}` is `red`, `gold`, `ink`, or `paper`. Each SVG embeds its own `#press` or `#press-light` filter in `<defs>`. See STYLE.md /assets "Logo rules" for naming and selection. |

---

## Fonts

All four families are self-hosted in `dist/fonts/` as woff2 files. No CDN dependency.

| Family | Source | Weights | Files |
|---|---|---|---|
| Sentient | fontshare.com | 300, 400, 500, 700 (each + italic) | `sentient-{weight}[-italic].woff2` |
| Satoshi | fontshare.com | 300, 400, 500, 700 (each + italic) | `satoshi-{weight}[-italic].woff2` |
| Shippori Mincho | fonts.google.com | 400, 500, 700 | `shippori-mincho-{weight}.woff2` |
| JetBrains Mono | fonts.google.com | 400, 500 | `jetbrains-mono-{weight}.woff2` |

Total: 21 woff2 files, roughly 700-900 KB combined.

`fonts.css` declares each via `@font-face` with `font-display: swap` and points to the local file. No third-party `<link>` tags anywhere in any consuming frontend.

---

## Consumption contract

Frontends pull `kujaku-meta` in as a git submodule, pinned to a specific commit SHA. They reference brand assets at `vendor/kujaku-meta/brand/dist/`.

```bash
# In a consuming frontend repo:
git submodule add https://github.com/<owner>/kujaku-meta.git vendor/kujaku-meta
```

Inside the frontend's HTML:

```html
<link rel="stylesheet" href="/vendor/kujaku-meta/brand/dist/fonts.css">
<link rel="stylesheet" href="/vendor/kujaku-meta/brand/dist/tokens.css">
<link rel="stylesheet" href="/vendor/kujaku-meta/brand/dist/reset.css">
<link rel="stylesheet" href="/vendor/kujaku-meta/brand/dist/textures.css">
<link rel="stylesheet" href="/vendor/kujaku-meta/brand/dist/recipes.css">
```

Order matters: fonts → tokens → reset → textures → recipes.

**Frontends never modify `brand/dist/` files.** They only import them. If a frontend needs something brand doesn't provide, the frontend writes its own site-local CSS. If that site-local pattern proves reusable across sites later, it earns promotion to `brand/dist/` (see Workflow below).

**To update brand globally:** bump the submodule commit SHA in each consuming frontend. No semver, no version tags, no npm publish step. The git SHA is the version.

---

## Workflow — Propose → Sandbox → Promote

Brand grows deliberately, never by accident. Every addition follows three stages.

### Stage 1 — Propose

A focused prompt is written (in architecture conversation, or wherever planning happens) describing what should be added or changed. The prompt references `STYLE.md` and `tokens.css`, and instructs Claude Code to produce a self-contained sandbox file using only existing brand tokens.

### Stage 2 — Sandbox

Claude Code generates a single HTML file in `kujaku-meta/sandbox/` (gitignored). The file imports `../brand/dist/*.css` for everything already locked, and inlines the candidate CSS for whatever's being tested. The user opens it locally and reviews.

If "needs work" → iterate Stage 1 → 2.
If "perfect" → proceed to Stage 3.

### Stage 3 — Promote

A second prompt is written for Claude Code:

> *The sandbox file `sandbox/<name>.html` is approved. Extract its new CSS into the appropriate `brand/dist/` file. Add a demonstration to `specimen.html`. Strip all sandbox demo markup. Verify the Promotion Checklist in `brand/README.md`. Don't touch anything else.*

The user reviews the integration. Approves. Commits `brand/`. Consuming frontends bump their submodule SHA when ready.

---

## Sandbox

```
kujaku-meta/
├── brand/      ← git tracked
└── sandbox/    ← gitignored, sibling to brand, freely deletable
```

**Rules:**
- `sandbox/` is in `kujaku-meta/.gitignore` from day one. Never committed.
- Anything in `sandbox/` is by definition disposable. `rm -rf sandbox/` at any time, no consequences.
- Sandbox files import from `../brand/dist/` for already-locked primitives. They never duplicate brand CSS.
- One sandbox file per candidate. Don't pile experiments into one mega-file — it makes review harder and promotion ambiguous.
- Sandbox files are review artifacts, not deliverables. They are NEVER linked from a consuming frontend.

Sandbox lives at the meta root (sibling to brand) rather than inside `brand/` because experiments may not always be brand-only — dashboard layouts, navigation tests, and other prototypes can use the same scratch space.

---

## Promotion Checklist

A candidate must satisfy **every** item before its CSS is allowed in `brand/dist/`. Stage 3 (Promote) prompts must explicitly verify each.

1. **Tokens only.** Uses only CSS variables defined in `tokens.css`. No hardcoded hex colors, no inline font names, no magic numbers for sizing/spacing/timing. If a value isn't a token, it doesn't belong.
2. **Correct file.** Placed in the right `dist/` file per the scope table above. New colors → `tokens.css`. New shadows → `textures.css`. New component → `recipes.css`. Etc.
3. **No new tokens introduced silently.** If the candidate genuinely needs a new color, font, easing, or shadow recipe, that's a SEPARATE proposal, not a side effect of promoting a component.
4. **Naming convention.** Lowercase-kebab. No project-specific prefixes (no `.web-foo`, no `.btc-card`). Names should read as universal primitives.
5. **Self-contained.** The recipe works by applying its class to a single element. No required parent selectors, no required sibling structure unless explicitly documented in STYLE.md.
6. **Demonstrated in `specimen.html`.** A new section or example added showing the primitive in use, rendered against the brand's actual tokens. If it's not in the specimen, it doesn't exist.
7. **No demo markup carried over.** Sandbox demo HTML, placeholder text, and one-off wrappers are stripped. Only the reusable primitive survives.
8. **STYLE.md updated if rules change.** If the addition introduces a new rule or convention (not just a new component), STYLE.md gets the corresponding section. The doc and the dist must always agree.

---

## What does NOT belong in `brand/`

Hard list. These never enter brand, no matter how reusable they feel locally.

- **Site-specific layout.** Homepage grids, navigation structures, page templates. These live in the consuming frontend.
- **Page-specific styles.** One-off tweaks for a particular section of a particular page.
- **Business or content copy.** Headlines, marketing text, taglines beyond the brand-level mantra.
- **JavaScript.** Brand v1 is CSS + assets only. If a primitive requires JS to function, it's not a brand-level primitive yet — it's a frontend concern.
- **Operator-dashboard styles.** The bot and collector services have intentionally utilitarian internal HTML. Brand does not apply to them and their styles are not promoted to brand.
- **Anything that wouldn't be identical across all Kujaku-branded sites.** If you'd want to tweak it for the next site, it's not brand.

---

## Operator dashboards exemption

The bot service (`bot-kalshi15min-btc/`) and collector service (`data/`) serve operator dashboards at their `GET /` endpoints. These are **internal tooling**, not public-facing. They are explicitly exempt from the brand system and are intentionally utilitarian.

Brand applies to public-facing surfaces served from `kujaku.ai` and any future public consumer frontends. Internal services stay plain.

This exemption prevents pointless retrofitting and keeps brand from sprawling into every dashboard in the platform.

---

## Versioning

No semver. No version tags. The git commit SHA on `kujaku-meta` is the brand version (alongside the rest of the monorepo). Consuming frontends pin to a SHA via submodule and bump when they want to pull updates.

When pinning is bumped, the consumer reviews the diff in `brand/` before merging — this is the moment to catch breaking changes (renamed tokens, restructured recipes). Brand commits should be small and descriptive enough that this review takes seconds.

A `CHANGELOG.md` is intentionally NOT maintained. The git log of `brand/` is the changelog. Adding a CHANGELOG file just means another doc to forget to update.

---

## Open decisions

These are unresolved and noted in `STYLE.md`. They do not block the brand folder from being created and used — they're items that need to be locked before kujaku.ai or any other public surface ships.

- **Final logo treatment.** Variant 08 (embossed original) is the working default. Confirm or override.
- **Three recurring kanji.** Working trio: 観 (kan), 静観 (seikan), 孔雀 (kujaku). Confirm.
- **Tagline.** Working: *Calm observation*.
- **Koi illustrations.** To be added to `dist/assets/illustrations/`.
- **Brushstroke plates.** To be added to `dist/assets/illustrations/`.

---

## How to ask Claude Code for a build

Every prompt to Claude Code that touches a Kujaku-branded surface starts with this prefix:

> *Use the Kujaku brand subsystem at `vendor/kujaku-meta/brand/`. Read `brand/README.md`, `brand/STYLE.md`, and `brand/specimen.html` before writing anything. Use only existing brand tokens, recipes, and textures. Do not introduce new colors, fonts, shadow recipes, easings, or animations. If something needed isn't in brand, stop and flag it — do not invent.*

Then state the actual build request plainly.

For Promote-stage prompts (Stage 3 of the workflow), the prompt additionally references the Promotion Checklist above and requires explicit verification of each item.

---

*Pair this README with `STYLE.md` (the design rules) and `specimen.html` (the rendered reference). Update this file when the architecture changes — never when the design changes.*
