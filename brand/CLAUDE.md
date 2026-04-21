# CLAUDE.md — kujaku-meta/brand/

Operational rules for Claude Code when working anywhere inside this folder.

## Before you do anything

1. Read README.md in full. It is the architecture contract.
2. Read STYLE.md in full. It is the design rules.
3. If a request is ambiguous against either, STOP and flag — do not invent.

## Working in brand/dist/

- Never modify dist/* files except as part of an explicit Stage 3 (Promote) prompt.
- Never add new tokens (colors, fonts, easings, sizes, durations) without explicit user approval — even if the request seems to require them.
- Never use hardcoded values where a token exists.
- When adding to dist/, always update specimen.html to demonstrate the addition. Both must agree at all times.

## Working in kujaku-meta/sandbox/

- Never commit anything from sandbox/. Verify .gitignore includes "sandbox/" before creating any sandbox file.
- One file per candidate. Don't pile experiments into one mega-file.
- Sandbox files import brand from ../brand/dist/ via relative path. Never duplicate brand CSS into a sandbox file.

## Forbidden

- `git add .` — ever. Stage files explicitly.
- Editing STYLE.md rules without an explicit instruction to change a rule.
- No JavaScript in brand/dist/, EXCEPT brand/dist/charts.js which ships the chart interactivity helper (~142 lines, vanilla JS, no dependencies). This is a deliberate architectural exception documented in STYLE.md /graphs Interactivity. The helper provides hover-crosshair + tooltip + point-highlight — interactions non-trivial enough to justify centralization. All other interactivity (scroll-hide, sort state, expandable-row toggle) remains consumer-owned per the visual-affordance-only contract.
- Promoting from sandbox to dist without explicitly verifying every item in the Promotion Checklist (see README.md).

## When in doubt

Flag, don't fix. Ask the user before guessing. Brand drift is harder to fix than a paused conversation.
