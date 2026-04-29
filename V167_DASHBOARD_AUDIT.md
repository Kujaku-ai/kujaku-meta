# V1.6.7 Dashboard Audit
**Date:** 2026-04-29  
**Auditor:** Claude Code  
**Scope:** Read-only audit of `app/templates/dashboard.html`, `app/dashboard_data.py`, `app/web.py`, and supporting spec files for the v1.6.7 wipe-and-rebuild.  
**Reference specs:** `BOT.md`, `V160_TRANSITION_SPEC.md`

---

## Section 1: Panel-by-Panel Inventory

### Panel 0: Summary Bar (sticky header)
- **Location:** `dashboard.html:1039–1088`
- **Data fields consumed:**
  - `rendered_lists.status_badge_html` — RUNNING/PAUSED/KILLED chip
  - `version` — version string from context
  - `paper_mode` — bool, renders `<span class="paper-chip">paper</span>` when true
  - `rendered_lists.bot_log_chip_html` — error/warn count chip (1h window)
  - `formatted.last_refreshed_fmt` — "last refreshed HH:MM:SS MDT"
  - `rendered_lists.portfolio_metric_html` — portfolio $ + growth%
  - `rendered_lists.continuation_wr_html` — continuation win rate chip
  - `rendered_lists.reversal_wr_html` — reversal win rate chip
  - `rendered_lists.consecutive_skips_html` — consecutive skips counter
  - `rendered_lists.sparkline_html` — 24h portfolio sparkline SVG
  - `rendered_lists.reflector_indicator_html` — reflector status pill
- **Builders:** `_render_status_badge_html` (line 1600), `_render_bot_log_chip_html` (line 1606), `_render_portfolio_metric_html` (line 1859), `_render_thesis_wr_chip_html` (line 1943), `_render_consecutive_skips_html` (line 1964), `_render_reflector_indicator_html` (line 1687)
- **Shows operator:** Single-line status strip with bot health, portfolio value, thesis win rates, skip count, and sparkline.
- **Assessment: MOSTLY USEFUL.** The six elements specified in V160_TRANSITION_SPEC.md §3.4 are all implemented. Two dead weight items exist in `_build_rendered_lists`:
  - `metrics_row_html` (line 3071) — rendered but NOT consumed by the template. The template uses `portfolio_metric_html`, `continuation_wr_html`, `reversal_wr_html`, `consecutive_skips_html` separately; the combined `metrics_row_html` is a ghost key from an older iteration. Dead code, never injected.
  - `bot_identity_html` (line 3060) — rendered in `_build_rendered_lists` but NOT referenced by any `data-refresh-list` in the template. The template renders version inline as `{{ version }}`. Dead key.

### Panel 1: Active Window
- **Location:** `dashboard.html:1107–1124`
- **Data fields consumed:**
  - `rendered_lists.active_window_grid_html` — ticker, closes, strike, YES/NO bid/ask
  - `rendered_lists.active_window_review_summary_html` — thesis banner, confluence, trade cards, entry_scenario
  - `rendered_lists.active_window_reasoning_html` — context_read, invalidation, self_critique, counter_argument
- **Builders:** `_render_active_window_grid_html` (line 2011), `_render_active_window_review_summary_html` (line 2046), `_render_active_window_reasoning_html` (line 2212)
- **Shows operator:** Current window market data + latest Claude decision with reasoning expandable.
- **Assessment: USEFUL.** `entry_scenario` is rendered (v1.6.1 fix, line 2180). `validator_warnings` are NOT rendered in Panel 1's review summary — they only appear in Panel 3 (Recent Decisions) expanded view. Missing: scale_entries are built in `_decision_to_review_dict_v15` (lines 1306–1323) but `_render_active_window_review_summary_html` ignores the `scale_entries` key entirely (no renderer for it in Panel 1). This is a gap.

### Panel 2: Positions
- **Location:** `dashboard.html:1127–1138`
- **Data fields consumed:**
  - `rendered_lists.open_trades_section_html` — open (filled, unsettled) trades table
  - `rendered_lists.waiting_triggers_section_html` — waiting trigger trades table with phase state
  - `rendered_lists.recent_settled_section_html` — last 5 settled trades
- **Builders:** `render_open_trades_html` (line 2237), `render_waiting_triggers_html` (line 2276), `render_recent_settled_html` (line 2340)
- **Shows operator:** Three sub-tables for position states.
- **Assessment: USEFUL.** Phase state added in v1.6.1 (line 2276). `trade_type` column present in all three tables (primary/hypothesis/scale distinction visible). The `min-width: 420px` on `#positions table` (dashboard.html:315) forces horizontal scroll on mobile — functional but not ideal.

### Panel 3: Recent Decisions
- **Location:** `dashboard.html:1141–1150`
- **Data fields consumed:**
  - `rendered_lists.recent_decisions_html` — 10 decision cards
  - `recent_decisions|length` — count for header label
- **Builder:** `render_recent_decisions_html` (line 2718)
- **Shows operator:** Last 10 decisions as collapsible cards with compact header (thesis pill, tier badge, side, size, R/R chips, outcome) and expanded body (full reasoning, confluence, validator warnings, FV drawer).
- **Assessment: USEFUL but overcrowded.** Solid implementation. Known gap: `entry_strategy` (e.g. `break_above`) is not in the compact summary line — only side and size appear there. The operator must expand to see the entry strategy. The `review_label` field is in `_decision_to_card_v15` but displayed only in the expanded body (`d["review_label"]` at line 2840), not the compact summary.

### Panel 4: Playbook
- **Location:** `dashboard.html:1153–1165`
- **Data fields consumed:**
  - `rendered_lists.playbook_summary_label_html` — "revision N · X tokens · HH:MM MDT"
  - `rendered_lists.playbook_content_html` — rendered markdown in scrollable div
  - `rendered_lists.playbook_recent_revisions_html` — last 10 revisions with rollback buttons
- **Builders:** `_render_playbook_summary_label_html` (line 2974), `render_playbook_content_html` (line 2913), `render_playbook_recent_revisions_html` (line 2924)
- **Shows operator:** Current playbook with revision history and rollback capability.
- **Assessment: FUNCTIONAL, KEEP.** V160_TRANSITION_SPEC.md explicitly said "carry forward as-is." No issues noted beyond cosmetic alignment.

### Charts Section
- **Location:** `dashboard.html:1170–1231`
- **Seven charts** — see Section 2 below for per-chart detail.

### Footer
- **Location:** `dashboard.html:1233–1239`
- **Data fields consumed:** `formatted.now_local_label_fmt`, `#refresh-indicator` (JS-managed)
- **Shows operator:** Timestamp + "live" / "last update Xs ago" indicator.
- **Assessment: USEFUL, minimal, keep.**

### Bot Log Drawer
- **Location:** `dashboard.html:1091–1101`
- **Mechanism:** Hidden `<section>` opened by clicking the bot_log chip in summary bar. JS fetches `/api/bot_log_recent?level=ERROR,WARN&limit=20` on open.
- **Assessment: USEFUL.** The delegated click handler (dashboard.html:1624) correctly handles post-refresh DOM replacement by walking ancestors. Keep.

---

## Section 2: Chart-by-Chart Inventory

### Chart 1: Edge Calibration Scatter (Bar Chart)
- **Builder:** `_build_edge_calibration_scatter` at `dashboard_data.py:3216`; renderer `render_edge_scatter_svg` at `dashboard_data.py:823`
- **Template location:** `dashboard.html:1175–1180` (full-width figure)
- **What it computes:** For each settled v1.5+ primary with non-NULL `break_even_prob_at_entry`: computes `real_edge = pe − BE`, bins into 10 edge buckets `[−0.10,−0.05)…[0.50,1.00]`, aggregates per-bucket `(n, wins, wr, avg_pnl_ct)` split by thesis (continuation/reversal). The v1.6.1 fix (`_build_edge_calibration_scatter` docstring: "corrected from v1.6.0") changed from `pe − 0.5` proxy to real `pe − BE` edge.
- **Query dependency:** `db.get_confluence_settled_corpus(conn, limit=500)` — same corpus shared with calibration, WR trend, signal WR, thesis matrix, and heatmap.
- **Sample-size guard:** `_EDGE_SCATTER_MIN_N = 5` (line 3183). Bars with `n < 5` render as muted stub. Chart suppresses entirely when `total_n == 0`.
- **Render type:** SVG grouped bar chart (two bars per bucket: blue=continuation, orange=reversal). NOT a scatter plot despite the name — the spec called for scatter points but the implementation uses a bar chart grouped by bucket. The name/figcaption mismatch is a defect.
- **Figcaption:** `dashboard.html:1176` — "Edge calibration — WR by edge (pe−BE) bucket (continuation / reversal)" — accurate.
- **Mobile behavior:** Full-width figure, `width_px=600`. SVG uses `preserveAspectRatio="xMidYMid meet"` so it scales down. Bucket labels use 8px font, which becomes unreadable below ~360px.
- **Colors:** `_CONT_ACCENT = "#44aaff"` (blue), `_REV_ACCENT = "#ffaa44"` (orange) — consistent with CSS vars `--cont` and `--rev`.
- **Actionability: HIGH.** This chart directly answers "were the removed hard gates doing real work?" Critical for v1.6 observation window. KEEP.

### Chart 2: Signal × Strength × Thesis Heatmap
- **Builder:** `_build_signal_strength_thesis_heatmap` at `dashboard_data.py:3311`; renderer `render_signal_strength_heatmap_html` at `dashboard_data.py:936`
- **Template location:** `dashboard.html:1183–1188` (full-width figure)
- **What it computes:** Two 19×4 HTML tables (continuation + reversal). For each settled primary, for each confluence signal cited at a given strength, increments `acc[thesis][signal][strength].{n, wins}`. Deduplicates: one primary cannot count twice in the same `(name, strength)` cell. Cells with `n < 5` render muted `"n=X"` only; cells with `n == 0` render `"—"`.
- **Query dependency:** `db.get_confluence_settled_corpus(conn, limit=500)`.
- **Sample-size guard:** `_HEATMAP_MIN_N = 5` (line 3200). Applied per-cell.
- **Render type:** HTML tables (not SVG). This is unique among all 7 charts. `render_signal_strength_heatmap_html` returns raw HTML strings, not SVG.
- **Mobile behavior:** `heatmap-table` at 10.5px → drops to 9.5px at ≤480px (dashboard.html:1031). The 120px `sig-col` plus 4 strength columns will force horizontal scroll on narrow screens because `table-layout: fixed` with `width: 100%` cannot reasonably fit 19 signal names × 4 strengths at 480px. **This is a mobile failure.**
- **Colors:** `_diverging_win_rate_color()` (line 365): red (#cc3333) below 50%, gray (#787878) at 50%, green (#4aaa4a) above 75%.
- **Actionability: HIGH.** The centerpiece analytical addition per V160 spec §2.9. KEEP.

### Chart 3: Probability Calibration Curve
- **Builder:** `_build_probability_calibration` at `dashboard_data.py:3457`; renderer `render_calibration_curve_svg` at `dashboard_data.py:389`
- **Template location:** `dashboard.html:1191–1196` (half-width)
- **What it computes:** Five bins `[0.50,0.60)…[0.90,1.00]` of settled v1.5 primaries by `probability_estimate`. Computes `(n, wins, wr)` per bin pooled AND split by thesis (continuation/reversal).
- **Query dependency:** `db.get_confluence_settled_corpus(conn, limit=500)`.
- **Render gap:** The builder (`_build_probability_calibration`) returns `by_thesis` split data at line 3550. BUT `render_calibration_curve_svg` (line 389) only accepts `points` (pooled). The thesis-split lines specified in V160 §2.6 are NOT rendered. The `by_thesis` data is built and stored in `charts["calibration_data"]` but the SVG renderer ignores it. **This is an unfulfilled Phase 2 spec item.**
- **Sample-size guard:** `_CALIBRATION_MIN_SAMPLES = 20`. Below threshold shows "Accumulating data" placeholder.
- **Mobile:** Half-width at ≥768px, full-width below. `width_px=420` SVG with `xMidYMid meet`. Should render acceptably on phones.
- **Colors:** Per-dot diverging color from `_diverging_win_rate_color`. Gray diagonal reference line.
- **Actionability: HIGH (pooled); PARTIAL (split incomplete).** KEEP but the thesis split must be implemented in v1.6.7.

### Chart 4: WR Trend Sparkline
- **Builder:** `_build_win_rate_trend` at `dashboard_data.py:3600`; renderer `render_win_rate_trend_svg` at `dashboard_data.py:519`
- **Template location:** `dashboard.html:1199–1204` (half-width)
- **Figcaption:** `dashboard.html:1200` — "Primary win rate — rolling 20 (step 5)"
- **What it computes:** Rolling WR over 20-trade windows, stepped every 5, across settled v1.5 primaries in chronological order. Also builds `by_thesis` rolling-WR arrays and `lifetime_wr` reference.
- **Query dependency:** `db.get_confluence_settled_corpus(conn, limit=500)`.
- **Render gap:** `render_win_rate_trend_svg` (line 519) accepts `points` (pooled, ordinal X-axis) only. The builder produces `by_thesis` thesis-split sparklines and `lifetime_wr` reference line. **None of this is passed to the SVG renderer.** The SVG uses ordinal X-axis `#{index}` labels — NOT timestamps as specified in V160 §2.8. **Two unfulfilled Phase 2 spec items.**
- **Sample-size guard:** `_WR_TREND_MIN_SAMPLES = 20`. Placeholder below threshold.
- **Mobile:** Half-width ≥768px. Acceptable.
- **Colors:** Single `currentColor` line. No thesis split.
- **Actionability: MODERATE (pooled trend useful; split/timestamps missing).** KEEP but fix the renderer in v1.6.7 to use timestamp X-axis and thesis split.

### Chart 5: Confluence Signal WR Bars
- **Builder:** `_build_confluence_signal_wr` at `dashboard_data.py:3656`; renderer `render_horizontal_bar_chart_svg` at `dashboard_data.py:630`
- **Template location:** `dashboard.html:1207–1212` (full-width)
- **Figcaption:** `dashboard.html:1208` — "Confluence signal win rate (cited ≥15 times, sorted by WR)"
- **What it computes:** Per canonical signal: total citations, wins, wr, plus `by_thesis` breakdown. Signals with `n < 15` excluded. Sorted by WR desc.
- **Query dependency:** `db.get_confluence_settled_corpus(conn, limit=500)`.
- **Render gap:** `render_horizontal_bar_chart_svg` (line 630) accepts `bars` list with keys `{name, win_rate, n}`. The builder produces `by_thesis` per-signal breakdown (lines 3719–3727). **The thesis-split grouped bars specified in V160 §2.7 are NOT rendered.** The renderer ignores `by_thesis` entirely.
- **Sample-size guard:** `_SIGNAL_WR_MIN_CITATIONS = 15` (per-signal), `_SIGNAL_WR_MIN_QUALIFYING_SIGNALS = 3` (chart threshold).
- **Mobile:** Full-width. Signal name label column is 260px padded (`pad_l = 260` at line 648). At 480px viewport this is catastrophic — the label column alone exceeds 50% of screen width, bar chart will be invisible or zero-width. **Mobile failure.**
- **Colors:** `_diverging_win_rate_color` per bar.
- **Actionability: MODERATE (pooled WR useful; thesis split missing; mobile broken).** KEEP but split renderer must be written.

### Chart 6: Thesis × Outcome Matrix
- **Builder:** `_build_thesis_outcome_matrix` at `dashboard_data.py:3400`; renderer `render_2x2_matrix_svg` at `dashboard_data.py:720`
- **Template location:** `dashboard.html:1215–1220` (half-width)
- **Figcaption:** `dashboard.html:1216` — "Thesis × outcome (counts + cumulative P&L)"
- **What it computes:** 2×2 grid of continuation/reversal × won/lost. Each cell: `n`, cumulative `pnl`, and computed `win_rate_pct`. The builder adds `win_rate_pct` per cell (lines 3438–3448).
- **Render gap:** `render_2x2_matrix_svg` (line 720) renders `count_text = f"n={n}"` and `pnl_text` only (lines 789, 795). The `win_rate_pct` computed by the builder is NOT rendered. **V160 §2.9 explicitly says "Add win rate per cell as a third statistic."** This is an unfulfilled spec item.
- **Sample-size guard:** `_THESIS_MATRIX_MIN_SAMPLES = 5`. Placeholder below threshold.
- **Mobile:** Half-width ≥768px, full-width below. 420×260 SVG with `xMidYMid meet`. Acceptable.
- **Colors:** Cell fill intensity scales with n; won cells green-tinted, lost cells red-tinted.
- **Actionability: HIGH (the gap requires mental math to derive WR from cells; the field exists but isn't shown).** Add `win_rate_pct` text to each cell in v1.6.7.

### Chart 7: Portfolio Growth Sparkline
- **Builder:** `render_sparkline_svg` (also used for summary bar sparkline) at `dashboard_data.py:264`
- **Template location:** `dashboard.html:1224–1229` (half-width)
- **Figcaption:** `dashboard.html:1224` — "24h portfolio growth ({{ portfolio_sparkline_sample_count }} samples)"
- **What it computes:** `(timestamp, total_value)` pairs from `portfolio_history` in the last 24h. Renders as SVG polyline with a dashed reference at starting capital.
- **Query dependency:** `db.get_portfolio_history_since(conn, since_iso)` where `since_iso` is 24h back.
- **Sample-size guard:** `_SPARKLINE_MIN_SAMPLES = 6`. Placeholder below threshold.
- **Mobile:** Half-width ≥768px. SVG uses `preserveAspectRatio="none"` — stretches to container. Acceptable.
- **Colors:** `currentColor` (accent blue `#6ea8ff`). Dashed reference line for starting capital.
- **Actionability: MODERATE.** The 24h window is short; a 7-day view would be more useful for spotting streaks. The X-axis labels (`show_axis_labels=True`) show min/max $ values not timestamps. KEEP but consider X-axis date labels per V160 §3.8.

---

## Section 3: Deprecated / Dead Content

### Fields Computed in dashboard_data.py But NOT Rendered by Template

1. **`metrics_row_html`** (`_build_rendered_lists` line 3071) — Rendered by `_render_metrics_row_html()` which bundles Portfolio + Primary WR + Hypothesis WR into one block. No `data-refresh-list="metrics_row_html"` in the template. Dead key.

2. **`bot_identity_html`** (`_build_rendered_lists` line 3060) — `_render_bot_identity_html()` still renders the old `_BOT_DISPLAY_NAME = "KevBot"` string (line 112). Not consumed by template — version is inlined directly in the template as `{{ version }}`. Dead key AND stale branding (BOT.md notes brand changed to "Kujaku" in v1.6.0).

3. **`primary_wr_summary`** / **`dissent_wr_summary`** — Present in `context` (lines 4124–4132). Passed to `_render_metrics_row_html` in `_build_rendered_lists`, which is itself dead. These are also computed and not directly consumed except through the dead `metrics_row_html` key. The thesis-split WR (`continuation_wr_summary`, `reversal_wr_summary`) replaced them in the template.

4. **`win_rate_pct`** (context line 4120) — Pooled primary win rate. Not rendered anywhere in the template. Superseded by thesis-split WRs.

5. **`win_count_primary`** / **`settled_count_primary`** (context lines 4118–4119) — Not consumed by template. Raw counts backing `win_rate_pct`.

6. **`primary_pnl_pct`** / **`hypothesis_pnl_pct`** (context lines 4121–4122) — Not consumed by template.

7. **`charts["calibration_data"]`** / **`charts["wr_trend_data"]`** / **`charts["signal_wr_data"]`** / **`charts["thesis_matrix_data"]`** / **`charts["edge_scatter_data"]`** — Raw data objects stored in `charts_block` (lines 4079–4084). Not referenced by the template or any `data-refresh-list` key. Were present for potential future client-side use but JS does no rendering.

8. **`by_thesis`** split on calibration, WR trend, signal WR bars — Built by each respective `_build_*` function, stored in raw data objects above, but NO renderer consumes them. Three cases of orphaned computation:
   - `calibration["by_thesis"]` — built at line 3550; SVG renderer `render_calibration_curve_svg` never reads it.
   - `wr_trend["by_thesis"]` — built at lines 3637–3642; SVG renderer `render_win_rate_trend_svg` never reads it.
   - `signal_wr["by_thesis"]` per bar — built at lines 3719–3727; SVG renderer `render_horizontal_bar_chart_svg` never reads it.

9. **`probability_calibration`** / **`win_rate_trend`** / **`confluence_signal_wr`** / **`thesis_outcome_matrix`** (top-level context keys, lines 4158–4161) — Duplicates of what's already in `context["charts"]`. Not referenced by template or JS. Redundant.

### Template References to Non-Existent Fields

None found — all `data-refresh-list` and `data-refresh-key` attributes in the template correspond to keys present in `rendered_lists` or `formatted` dicts.

### Code Paths for Retired Features

1. **`_BOT_DISPLAY_NAME = "KevBot"` (line 112)** — Historical project codename. Used only in the dead `_render_bot_identity_html` function. The bot was renamed "Kujaku" in v1.6.0 per BOT.md. Dead + stale.

2. **`_render_metrics_row_html` (line 1912) and `_render_wr_metric_column_html` (line 1883)** — Render the old combined metric row (Portfolio + Primary WR + Hypothesis WR). Superseded by the v1.6.0 Phase 3 individual metric columns. The old helpers are still called from `_build_rendered_lists` but the result is dead.

3. **`_render_pnl_metric_html` (line 2003)** — Defined, never called anywhere in the file. Orphaned helper.

4. **`_dissent_to_hypothesis_ui_note = None` (line 2000)** — Module-level comment/stub. Not used by any logic. Dead.

5. **v1.3 bias fields** (`bias_summary`, `confidence`, `reasoning` columns) — Present in DB schema (BOT.md lines 630, 631, 633) but correctly excluded from all v1.5 dashboard queries via `V15_CLEAN_FILTER_SQL`. No stale renders.

6. **`_render_bot_identity_html`** (line 1634) — Called from `_build_rendered_lists`, output key `bot_identity_html` never consumed by template.

7. **`hypothesis` terminology in code vs "hypothesis" in UI** — The internal comment at line 1988 explains the translation decision (`_dissent_to_hypothesis_ui_note`). Not dead code per se, but the comment artifact `= None` is garbage.

### CSS Classes Defined But Unused

1. **`.thesis-continuation { background: var(--continuation); }` and `.thesis-reversal { background: var(--reversal); }`** — The original green/amber thesis banner colors (dashboard.html:357–358). Still used by `_render_thesis_banner_html` (line 1764) and the `.thesis-mini-continuation`/`.thesis-mini-reversal` chips. However, the v1.6.0 Phase 3 introduced `--cont` (#44aaff) and `--rev` (#ffaa44) as the "correct" two-accent system. The old `--continuation: #2e7d32` and `--reversal: #e67e22` survive in CSS (dashboard.html:23–24) alongside the new vars. The thesis banner and mini pill still use the OLD dark green/amber; the chart legends use the NEW blue/orange. **Inconsistent thesis color across panels** — same thesis seen as dark green in Panel 1 banner and as blue in chart legend.

2. **`.scale-card`** — Referenced in `_render_scale_entries_block_html` (line 2654) but no CSS definition in dashboard.html. Scale entry cards inherit `.trade-card` styling but have no visual distinction. The class is referenced in JS output but not defined in CSS. Minor — no visible breakage since `.trade-card` styles apply.

3. **`.entry-scenario-block`** — Used in `_render_entry_scenario_html` (line 2189) but not defined in dashboard.html CSS. The element will render unstyled. Minor gap.

4. **`.self-critique-block`** — Used in `_render_self_critique_html` (lines 2201, 2207) but no explicit CSS in dashboard.html beyond what's inherited from `.reasoning`. Renders fine but is not styled distinctly.

### JS Event Handlers Wired to Non-Existent Elements

None found. The FV drawer toggle (`onFvToggle`, line 1540) filters on `.fv-drawer` class which exists in the rendered HTML. The bot_log drawer delegated click handler (line 1624) walks ancestors looking for `id="bot-log-chip"` which is always rendered (inside `bot_log_chip_html`). Both are robust.

### Dead Imports in dashboard_data.py and web.py

- **`dashboard_data.py` line 64:** `from app import collector_client, db, kill_switch, reflector, watcher` — all are used. No dead imports.
- **`web.py` line 56–63:** `from app import ... compactor ...` — `compactor` is used at line 28 doc and in route `/control/compactor/fire` (web.py:600+, not shown in audit window but present). No dead imports found.
- **`web.py` comment at line 14:** "v1.4.3" in route docstring is stale — the dashboard is v1.6.x now.

---

## Section 4: Data Fields Available But Unrendered

These fields are in `build_dashboard_context` output and never appear in `rendered_lists` or template HTML:

| Field | Source | What it contains | Rebuild candidate? |
|---|---|---|---|
| `win_rate_pct` | context line 4120 | Pooled primary WR % (float or None) | Replace with thesis split (already done) |
| `win_count_primary` | context line 4118 | Raw win count | Low priority |
| `settled_count_primary` | context line 4119 | Raw settled count | Low priority |
| `primary_pnl_pct` | context line 4121 | Primary cumulative P&L as % of starting capital | Useful for a "primary P&L" chip |
| `hypothesis_pnl_pct` | context line 4122 | Hypothesis cumulative P&L % | Could show hypothesis track record |
| `primary_wr_summary` | context line 4124 | `{wins, n, wr_pct}` for primary | Superseded by thesis split; low priority |
| `dissent_wr_summary` | context line 4129 | `{wins, n, wr_pct}` for hypothesis | Candidate for hypothesis WR metric |
| `charts["calibration_data"]` | charts_block line 4079 | Full calibration dict including `by_thesis` | Needed for thesis-split renderer |
| `charts["wr_trend_data"]` | charts_block line 4080 | Full WR trend dict including `by_thesis`, `lifetime_wr` | Needed for thesis-split + timestamp X-axis |
| `charts["signal_wr_data"]` | charts_block line 4081 | Signal WR dict including `by_thesis` per bar | Needed for thesis-split grouped bars |
| `charts["thesis_matrix_data"]` | charts_block line 4082 | Matrix dict including `win_rate_pct` per cell | Needed for WR-per-cell render fix |
| `charts["edge_scatter_data"]` | charts_block line 4083 | Raw scatter points + per-bucket data | Available for table beneath chart |
| `thesis_matrix["cells"][*][*]["win_rate_pct"]` | built at line 3438 | WR% per thesis×outcome cell | Must be added to SVG renderer |
| `calibration["by_thesis"]` | built at line 3550 | Thesis-split calibration points | For Phase 2.6 render |
| `wr_trend["by_thesis"]` | built at line 3637 | Thesis-split WR trend points | For Phase 2.8 render |
| `wr_trend["lifetime_wr"]` | built at line 3634 | Lifetime win rate for reference line | For Phase 2.8 reference line |
| `signal_wr["bars"][*]["by_thesis"]` | built at line 3720 | Per-signal thesis-split WR | For Phase 2.7 grouped bars |
| `active_window["last_review"]["scale_entries"]` | `_decision_to_review_dict_v15` line 1306 | Scale entry list for active window | No Panel 1 renderer yet |
| `reflector_fire_state["hours_ago"]` | line 1676 | Float hours since last reflector fire | Available for tooltip |

---

## Section 5: Theme / Visual Inventory

### Color Palette

All defined in `dashboard.html:7–33`:

| CSS Var | Hex | Purpose |
|---|---|---|
| `--bg` | `#0f1115` | Page background |
| `--panel` | `#181b22` | Panel/card background |
| `--panel-border` | `#232733` | Standard border |
| `--panel-border-strong` | `#32384a` | Emphasized border |
| `--text` | `#e6e7ea` | Body text |
| `--muted` | `#7c8290` | Subdued labels |
| `--strong` | `#f5f6f8` | Emphasized text |
| `--up` | `#4caf50` | Positive / green |
| `--down` | `#e53935` | Negative / red |
| `--accent` | `#6ea8ff` | Links, interactive elements |
| `--killed` | `#c0392b` | Kill switch, error state |
| `--paused` | `#f39c12` | Paused / warning state |
| `--cont` | `#44aaff` | v1.6.0 continuation accent |
| `--rev` | `#ffaa44` | v1.6.0 reversal accent |
| `--continuation` | `#2e7d32` | LEGACY thesis banner green (conflicts with `--cont`) |
| `--reversal` | `#e67e22` | LEGACY thesis banner amber (conflicts with `--rev`) |
| `--s2..s5` | `#3a4153`…`#7fbdff` | Strength tier badge scale (cool blue gradient) |
| `--wr-up` | `#4aaa4a` | WR > midpoint |
| `--wr-down` | `#cc3333` | WR < midpoint |
| `--wr-mid` | `#787878` | WR at midpoint / insufficient n |

**Inconsistency:** The thesis banner (Panels 1 and 3) uses `--continuation: #2e7d32` (dark green) and `--reversal: #e67e22` (amber). The chart legend and edge scatter use `--cont: #44aaff` (blue) and `--rev: #ffaa44` (orange). An operator reading the summary bar sees blue = continuation; reading Panel 1 sees dark green = continuation. This is confusing and must be unified in v1.6.7.

### Font Stack

`dashboard.html:43`: `font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`  
`font-size: 13px`, `line-height: 1.45`. Consistent across entire page — all text monospaced. This is intentional per BOT.md / V160 "monospace font" spec.

### Spacing System

No design token system. Spacing is ad-hoc per component:
- Panels: `padding: 12px` (line 288)
- Summary bar: `padding: 10px 12px` (line 66)
- Decision cards: `padding: 8px 12px` (line 461)
- Trade cards: `padding: 6px 8px` (line 436)
- Chart section: `padding: 12px` (line 921)
- Charts gap: `gap: 16px` (line 942)

The `12px` base unit is consistent but not tokenized. Not a problem for a wipe-and-rebuild.

### Component Patterns

- **Cards:** `background: rgba(0,0,0,0.2); border-left: 3px solid; border-radius: 3px` — trade cards, decision cards, skip cards.
- **Chips/Badges:** `padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; letter-spacing: 0.4px` — thesis pills, outcome badges, tier badges, strength badges.
- **Tables:** `border-collapse: collapse; border-bottom: 1px solid var(--panel-border)` — positions tables, bot_log table.
- **`<details>` patterns:** Decision cards use `<details class="decision-card">` for expand/collapse; reasoning uses nested `<details class="reasoning-drawer">`; FV uses `<details class="fv-drawer">`. Three levels of nesting exist in practice.

### What Looks Dated / Clunky

1. **Thesis banner colors** (dark green, amber) — clash with the newer blue/orange two-accent system. Looks like two different design systems on one page.
2. **Scale entries** (`<div class="trade-card scale-card">`) — no CSS defined for `.scale-card`, renders as a generic trade-card with no differentiation.
3. **`entry-scenario-block` class** — unstyled; text renders in default body style, no visual distinction from surrounding paragraph text.
4. **Skip cards in Panel 3** — `_render_skip_card_html` truncates reasoning to 120 chars with `"…"` (line 2397). V160 §3.6 says "full reason rendered, not truncated." Implementation contradicts spec.
5. **Playbook content** `max-height: 60vh; overflow-y: auto` (line 851) — on a tall desktop monitor, 60% of viewport height is a lot of scroll area. On mobile it's appropriate.
6. **The `review_label` / `window-ticker`** in Panel 3 card body — small text inside expanded view that is rarely visible and duplicates information in the summary.

### What Renders Inconsistently

- **Thesis colors:** See above — summary bar chips use blue/orange, panels use green/amber.
- **`outcome-no-fill`** (line 550): uses `font-style: italic` — the only outcome badge that's italic. Subtle inconsistency.
- **FV drawer `<summary>` hover color** (line 762): `color: var(--accent)` on hover/open, but other `<details summary>` elements use `color: var(--muted)` without hover state.

---

## Section 6: Mobile Behavior

### Breakpoints Defined in CSS

1. **`@media (min-width: 768px)` (dashboard.html:267):** Activates two-column grid layout for panels (3fr left + 2fr right). Below 768px all panels stack single-column.
2. **`@media (min-width: 768px)` (dashboard.html:943):** Activates two-column grid for charts section. Below 768px all charts stack single-column.
3. **`@media (max-width: 480px)` (dashboard.html:1027):** Four specific overrides:
   - `.fv-tf-grid`: `font-size: 10.5px`
   - `.fv-body .fv-spot-grid`: `grid-template-columns: 1fr`
   - `.bot-log-drawer table`: `font-size: 10.5px`
   - `.heatmap-table`: `font-size: 9.5px`

### Panel Behavior at Narrow Viewport (≤480px)

| Panel | Behavior |
|---|---|
| Summary bar | Flexbox wraps. Multiple lines. `flex-wrap: wrap` on `.summary-top` and `.summary-kpis`. Functional but dense. `sparkline-wrap` `flex: 1 1 200px` means sparkline gets at least 200px. |
| Active Window | Single column, reads fine. |
| Positions | **BREAKS.** `#positions table { min-width: 420px }` (dashboard.html:315) inside a `.positions-table-wrap { overflow-x: auto }` container. Triggers horizontal scroll at 420px wide — means 100% of narrow phones get a scrollable table. Tolerable but poor UX. |
| Recent Decisions | `<details>` cards stack full-width. Summary line wraps — `flex-wrap: wrap` on `.decision-summary` (line 466). The `decision-chevron` `margin-left: auto` pushes the chevron to far right but the flex-wrap may orphan it on a new line on very narrow screens. |
| Playbook | Scrollable `max-height: 60vh` content — functional. |

### Specific Mobile Failures

1. **Heatmap table (Chart 2):** `table-layout: fixed; width: 100%` with `sig-col { width: 120px }` plus 4 data columns. At 480px the signal names column is 120/480 = 25% of width; remaining 75% = ~360px for 4 columns ≈ 90px each. Signal names like `momentum_decelerating_against_thesis` will overflow ellipsis. The heatmap is essentially unreadable on a phone.
2. **Signal WR bars SVG (Chart 5):** Fixed `pad_l = 260` for signal name labels in SVG. At 480px viewport, a 260px left padding leaves only 220px for the actual bars. Bar labels (signal names in SVG text) will overlap the bars.
3. **Positions table scroll:** Min-width 420px forces scroll on all phones.
4. **Summary bar KPI row:** At very narrow widths (360px), the KPI group with Portfolio + sep + Cont WR + Rev WR + sep + Consec Skips will wrap to 2–3 rows. Readable but spacious.

### Touch Target Sizes

- **Rollback buttons:** `min-height: 32px; min-width: 64px` (line 908) — adequate.
- **`<details>` summary elements:** No explicit height set; rely on line-height (1.45 × 13px = ~19px). Below the 44px recommended touch target. Poor but not catastrophic for a developer/operator tool.
- **Bot_log chip button:** `padding: 2px 8px` — ~28px effective height. Below 44px recommendation.

---

## Section 7: Refresh / Runtime Layer

### The data-refresh-key / MutationObserver Pattern

**Status: Present, working, worth keeping.**

Three separate `<script>` blocks in `dashboard.html:1243–1724`:

**Block 1 (lines 1250–1311): Core polling refresh**
- Fetches `/api/dashboard_context` every 10 seconds.
- `applyContext(ctx)`: swaps `el.textContent` for `data-refresh-key` elements and `el.innerHTML` for `data-refresh-list` elements.
- `updateIndicator()`: Shows "live" or "last update Xs ago" in footer when >30s stale.
- Silent failure on network error — indicator goes stale automatically.
- `cache: 'no-store'` prevents stale cached responses.
- **Assessment:** Correct and clean. No issues.

**Block 2 (lines 1314–1642): FV drawer + bot_log drawer**
- FV drawer: Lazy-loads `/api/decision/{id}/feature_vector` on first open. Client-side rendering of nested feature vector (momentum, VWAP, structure chips). Cache maintained in `fvCache` object (session-scoped).
- Bot_log drawer: Fetches `/api/bot_log_recent?level=ERROR,WARN&limit=20` on chip click. Delegated click handler handles post-refresh DOM replacement.
- **Assessment:** Solid. The delegated event listener pattern for the bot_log chip (`document.addEventListener('click', ...)` walking ancestors, line 1624) is the correct pattern for dynamically replaced content. The FV drawer `toggle` event in capture phase (line 1574) is the right approach.

**Block 3 (lines 1652–1724): MutationObserver card state persistence**
- Persists `<details class="decision-card">` open/closed state to `sessionStorage` keyed by `decision_id`.
- Storage prefix: `dashboard.v2.panel3.expanded.` (line 1654).
- MutationObserver on `[data-refresh-list="recent_decisions_html"]` container; re-applies stored state after each innerHTML swap.
- **Assessment:** Works correctly. The `toggle` event listener + `safeSet/safeGet` wrappers around sessionStorage are good defensive coding. **Worth keeping verbatim.**

### /api/dashboard_context Shape

The endpoint (`web.py:308`) calls `build_dashboard_context` and JSON-serializes the result. The result is large (~50–80 fields in `rendered_lists` + nested raw data objects). Noteworthy issues:

1. **Chart raw data objects** (`calibration_data`, `wr_trend_data`, etc.) are serialized into the JSON response on every 10-second refresh. These objects can be 50–200KB of data that the client JS never reads. **Unnecessary bandwidth.** In v1.6.7, the raw data objects should be stripped from the JSON response (they live only in `rendered_lists` server-side HTML now).

2. **Top-level duplicate keys:** `probability_calibration`, `win_rate_trend`, `confluence_signal_wr`, `thesis_outcome_matrix` at context lines 4158–4161 are redundant with what's in `context["charts"]`. Double-serialized raw data.

3. **The `rendered_lists` dict contains all pre-rendered HTML.** The client never synthesizes HTML from raw data (except the FV drawer, which uses the dedicated `/api/decision/{id}/feature_vector` endpoint). This is the correct architecture: server renders, client injects.

### JS That Should Be Torn Out vs Preserved

| JS Block | Action |
|---|---|
| Core polling refresh (Block 1) | **PRESERVE verbatim** |
| FV drawer lazy loader (Block 2 FV section) | **PRESERVE** — the `/api/decision/{id}/feature_vector` endpoint and client renderer are well-written |
| Bot_log drawer (Block 2 log section) | **PRESERVE** |
| MutationObserver card state (Block 3) | **PRESERVE verbatim** |
| `fvRender*` functions (lines 1330–1538) | **PRESERVE** — client-side feature vector rendering is clean |

No JS needs to be torn out.

---

## Section 8: dashboard_data.py Architecture

**Current state: 4,176 lines, four concerns mixed.**

### The Four Concerns Currently Mixed

| Concern | Approximate lines | Examples |
|---|---|---|
| Time/label helpers (pure) | ~100 | `relative_time_from_utc`, `local_mdt_from_utc`, `closes_in_from_close_time` |
| SVG renderers (pure) | ~400 | `render_sparkline_svg`, `render_calibration_curve_svg`, `render_win_rate_trend_svg`, `render_horizontal_bar_chart_svg`, `render_2x2_matrix_svg`, `render_edge_scatter_svg` |
| HTML renderers (pure) | ~900 | All `_render_*_html` functions; `render_open_trades_html`, `render_waiting_triggers_html`, etc.; `render_signal_strength_heatmap_html`, `md_to_html` |
| Query + aggregation builders (async, I/O) | ~600 | `_build_edge_calibration_scatter`, `_build_signal_strength_thesis_heatmap`, `_build_thesis_outcome_matrix`, `_build_probability_calibration`, `_build_win_rate_trend`, `_build_confluence_signal_wr`, `build_dashboard_context` |
| Data dict builders (pure) | ~500 | `_decision_to_card_v15`, `_decision_to_review_dict_v15`, `_open_trade_dict`, `_waiting_trade_dict`, `_settled_trade_dict`, `_playbook_revision_dict` |
| Constant / color helpers | ~80 | `_diverging_win_rate_color`, `_accumulating_copy`, constants |

### Proposed Clean Module Split

| New Module | Responsibility | Estimated LoC |
|---|---|---|
| `app/dashboard_data.py` (RETAINED) | `build_dashboard_context` entry point + data dict builders (`_decision_to_card_v15` etc.) + query builders (`_build_*`) | ~700 |
| `app/dashboard_render.py` (NEW) | All HTML renderers (`_render_*_html` functions, `render_open_trades_html`, `render_waiting_triggers_html`, `render_recent_settled_html`, `render_recent_decisions_html`, `render_playbook_*_html`, `md_to_html`, `render_signal_strength_heatmap_html`, `_build_formatted_strings`, `_build_rendered_lists`) | ~1,100 |
| `app/chart_svg.py` (NEW) | Pure SVG renderer functions (`render_sparkline_svg`, `render_calibration_curve_svg`, `render_win_rate_trend_svg`, `render_horizontal_bar_chart_svg`, `render_2x2_matrix_svg`, `render_edge_scatter_svg`, `_placeholder_svg`, `_diverging_win_rate_color`) | ~500 |
| `app/dashboard_helpers.py` (NEW) | Time/label helpers (`relative_time_from_utc`, `local_mdt_from_utc`, `local_day_label_from_utc`, `closes_in_from_close_time`, `_humanize_past`, `_humanize_future`, `_parse_iso_utc`, `_now_utc`) + constants | ~150 |

**Estimated LoC after split:** Same total (~2,450 after removing dead code), but organized. The V160 spec deferred the module split ("reducing it naturally via Phase 3; further splitting deferred"). The v1.6.7 rebuild is the right time to execute this split since the render layer is being rewritten anyway.

---

## Section 9: Operator Workflow Pain Points

### Specific Pain Points (with file:line citations)

1. **Thesis colors are contradictory.** `dashboard.html:23–24` defines `--continuation: #2e7d32` (dark green) and `--reversal: #e67e22` (amber). `dashboard.html:20–21` defines `--cont: #44aaff` (blue) and `--rev: #ffaa44` (orange). An operator reads the summary bar (blue=cont, orange=rev) then looks at Panel 1 thesis banner (green=cont, amber=rev). Two different visual languages for the same concept on the same page.

2. **Skip reason truncated in Panel 3.** `_render_skip_card_html` at `dashboard_data.py:2397` truncates reasoning to 120 characters. V160 §3.6 says "full reason rendered, not truncated." An operator cannot read the full skip reason without expanding (but skip cards are non-collapsible articles, so there is no expand — the truncation is permanent).

3. **Entry strategy absent from Panel 3 compact summary.** `_render_decision_summary_html` at `dashboard_data.py:2669` renders: `#ID | ts | [THESIS TF] | [TIER] | SIDE SIZE% | R:R chips | OUTCOME`. The entry strategy (e.g. `break_above @93400`) is not in the compact view. Operator must expand every card to see how Claude entered.

4. **Consecutive skips counter counts only the most recent N decisions.** `build_dashboard_context` line 3964–3975 iterates `recent_decisions` (capped at `_RECENT_DECISIONS_LIMIT = 10`). If the bot has been skipping for 11+ windows, the counter shows at most 10. Misleading undercount.

5. **Panel 1 shows only the LAST decision for the current window** — not all reviews. If CLAUDE_REVIEWS_PER_WINDOW=2 and both reviews fired, only review 2/2 appears. The operator cannot see review 1/2's thesis or sizing without querying the DB.

6. **Validator warnings missing from Panel 1.** `_render_active_window_review_summary_html` (line 2046) renders thesis, confluence, primary/dissent cards. `primary_validator_warnings` is in `last_review` dict (built at `_decision_to_review_dict_v15` line 1279) but `_render_active_window_review_summary_html` never renders it. V160 §3.5 says active window should show validator_warnings.

7. **Scale entries not shown in Panel 1.** `last_review["scale_entries"]` is built (line 1306) but `_render_active_window_review_summary_html` ignores it. An operator sees primary + hypothesis in Panel 1 but misses any scale entries.

8. **Thesis matrix (Chart 6) shows counts and P&L but not WR.** The operator must compute `33/(33+35) = 49%` mentally. V160 §2.9 says "Add WR per cell." Field exists (`win_rate_pct`) but renderer ignores it. See Section 2.

9. **Calibration curve, WR trend, signal WR bars** all show pooled data when the thesis split is computed but unused. The reversal coin-flip finding (49% WR) that motivated V160 is not visually emphasized in these charts.

10. **Bot log drawer shows only 20 rows.** `dashboard.html:1602` fetches `limit=20`. In production this is adequate but can miss earlier errors if multiple errors fired in a burst.

11. **Charts are sorted: edge scatter → heatmap → calibration → WR trend → signal WR bars → thesis matrix → portfolio.** The last chart (portfolio) is the one most operators check first. It's buried at the bottom of a long chart strip.

12. **Playbook placed above charts** in the grid layout (BOT.md v1.6.0 implementation note: "Playbook above Charts in the rendered grid"). V160 spec §3.3 puts charts above playbook. Current DOM order: panels (active + decisions + positions + playbook) then charts. On mobile, the operator must scroll past the entire playbook before reaching any charts.

---

## Section 10: Proposed Wipe Targets vs Preserve Targets

### DELETE Entirely

| Target | Location | Reason |
|---|---|---|
| `_BOT_DISPLAY_NAME = "KevBot"` | `dashboard_data.py:112` | Stale brand; bot renamed to Kujaku |
| `_render_bot_identity_html()` | `dashboard_data.py:1634` | Dead — output key `bot_identity_html` not consumed by template |
| `_render_metrics_row_html()` | `dashboard_data.py:1912` | Dead — replaced by thesis-split individual metric cols |
| `_render_wr_metric_column_html()` | `dashboard_data.py:1883` | Dead — superseded by `_render_thesis_wr_chip_html` |
| `_render_pnl_metric_html()` | `dashboard_data.py:2003` | Orphaned — never called |
| `_dissent_to_hypothesis_ui_note = None` | `dashboard_data.py:2000` | Dead module-level stub |
| `metrics_row_html` key in `_build_rendered_lists` | `dashboard_data.py:3071` | Dead key — never consumed by template |
| `bot_identity_html` key in `_build_rendered_lists` | `dashboard_data.py:3060` | Dead key — never consumed by template |
| `win_rate_pct` in context | `dashboard_data.py:4120` | Dead — not rendered; superseded by thesis-split WRs |
| `win_count_primary` / `settled_count_primary` in context | `dashboard_data.py:4118–4119` | Dead — not rendered directly |
| `primary_pnl_pct` / `hypothesis_pnl_pct` in context | `dashboard_data.py:4121–4122` | Dead — not rendered |
| `primary_wr_summary` / `dissent_wr_summary` in context | `dashboard_data.py:4124–4132` | Dead — only consumed by the dead `metrics_row_html` key |
| `probability_calibration` / `win_rate_trend` / `confluence_signal_wr` / `thesis_outcome_matrix` top-level keys in context | `dashboard_data.py:4158–4161` | Redundant — already in `context["charts"]` |
| Raw data objects in `charts_block` (`calibration_data`, `wr_trend_data`, `signal_wr_data`, `thesis_matrix_data`, `edge_scatter_data`) | `dashboard_data.py:4079–4084` | Serialized into every 10s JSON response; client JS never reads them |
| `--continuation: #2e7d32` and `--reversal: #e67e22` CSS vars | `dashboard.html:23–24` | Stale — replaced by `--cont` and `--rev`; caused thesis color inconsistency |
| `.thesis-continuation { background: var(--continuation) }` and `.thesis-reversal { background: var(--reversal) }` | `dashboard.html:357–358` | Must be updated to use `--cont`/`--rev` |
| `.thesis-mini-continuation` / `.thesis-mini-reversal` badges | `dashboard.html:519–520` | Same — must use new accent vars |
| Skip reason truncation in `_render_skip_card_html` | `dashboard_data.py:2397` | Contradicts V160 spec §3.6; show full reason |

### PRESERVE / REUSE

| Target | Location | Why keep |
|---|---|---|
| `build_dashboard_context()` overall structure | `dashboard_data.py:3757` | Well-structured async function; DB query sequencing is correct |
| `db.get_confluence_settled_corpus()` query | Called from multiple builders | Core settled-primary corpus query; all chart builders share it; efficient |
| `_build_edge_calibration_scatter()` | `dashboard_data.py:3216` | Correct `pe − BE` edge computation (v1.6.1 fix applied); bucket structure solid |
| `_build_signal_strength_thesis_heatmap()` | `dashboard_data.py:3311` | Correct deduplication per (primary, signal, strength); per-cell n/wins/wr |
| `_build_thesis_outcome_matrix()` | `dashboard_data.py:3400` | Correct; already computes `win_rate_pct` per cell (just not rendered) |
| `_build_probability_calibration()` | `dashboard_data.py:3457` | Correct; `by_thesis` split already computed; just needs renderer update |
| `_build_win_rate_trend()` | `dashboard_data.py:3600` | Correct; `by_thesis` + `lifetime_wr` already computed; needs renderer update |
| `_build_confluence_signal_wr()` | `dashboard_data.py:3656` | Correct; `by_thesis` per bar already computed; needs renderer update |
| `_rolling_wr_points()` | `dashboard_data.py:3564` | Pure helper; tested; correct |
| `_edge_bucket_idx()` | `dashboard_data.py:3203` | Correct bucket lookup |
| `_safe_confluence_list()` | `dashboard_data.py:1157` | Robust JSON decode with sorting |
| `_safe_response_json()` | `dashboard_data.py:1117` | Robust JSON decode |
| `_safe_validator_warnings()` | `dashboard_data.py:1216` | Correct coercion |
| `_safe_trend_alignment_list()` | `dashboard_data.py:1180` | Correct coercion |
| `_extract_entry_scenario()` | `dashboard_data.py:1128` | v1.6.1 fix; correct |
| `_decision_to_card_v15()` | `dashboard_data.py:1338` | Complete; includes scale_entries, hypothesis_pnl; v1.6.3 no_fill state |
| `_decision_to_review_dict_v15()` | `dashboard_data.py:1228` | Complete; includes scale_entries and all v1.5.2 fields |
| `_open_trade_dict()` / `_waiting_trade_dict()` / `_settled_trade_dict()` | `dashboard_data.py:1511–1561` | Correct data dicts |
| `_reflector_fire_state()` | `dashboard_data.py:1660` | Correct freshness classification |
| `_diverging_win_rate_color()` | `dashboard_data.py:365` | Correct red→gray→green interpolation |
| `_accumulating_copy()` | `dashboard_data.py:3747` | Simple; useful |
| `render_sparkline_svg()` | `dashboard_data.py:264` | Correct; used for both summary bar and portfolio chart |
| `render_signal_strength_heatmap_html()` | `dashboard_data.py:936` | HTML table heatmap; correct; well-structured |
| `render_edge_scatter_svg()` | `dashboard_data.py:823` | Correct bar chart with thesis split |
| `render_2x2_matrix_svg()` | `dashboard_data.py:720` | Correct; needs `win_rate_pct` text added |
| `md_to_html()` | `dashboard_data.py:1008` | Custom markdown-to-HTML; correct subset for playbook |
| All partial-refresh JS (3 script blocks) | `dashboard.html:1243–1724` | Clean, correct, well-tested in production |
| `/api/dashboard_context` endpoint | `web.py:308` | Correct; keep as-is |
| `/api/decision/{id}/feature_vector` endpoint | `web.py:410` | Used by FV drawer; keep |
| `/api/bot_log_recent` endpoint | `web.py:469` | Used by bot_log drawer; keep |
| All playbook API endpoints | `web.py:552–619` | Functional; rollback mechanism correct |
| `_COLLECTOR_WARN_THROTTLE_SECONDS` + `_maybe_warn_collector_unreachable()` | `dashboard_data.py:151, 1092` | Prevents log spam; keep |
| `_tier_css_class()` + `_render_tier_badge_html()` | `dashboard_data.py:1199, 2488` | Correct; 5-tier visual encoding consistent |
| `_render_rr_chips_html()` | `dashboard_data.py:2508` | Correct R:R / BE / edge chip rendering |
| `_render_validator_warnings_block_html()` | `dashboard_data.py:2553` | Correct |
| `_render_outcome_pill_html()` | `dashboard_data.py:2418` | Correct; includes no_fill + hypothesis P&L |
| `_V15_CONFLUENCE_SIGNALS` tuple | `dashboard_data.py:124` | Canonical 19-signal list; matches claude_client |
| `_EDGE_BUCKETS` / `_HEATMAP_STRENGTHS` constants | `dashboard_data.py:3186–3199` | Correct bucket definitions |
| MutationObserver card state persistence (JS Block 3) | `dashboard.html:1652–1724` | Keep verbatim; elegant solution |

---

## Summary of Key Findings for v1.6.7 Architect

### Unfulfilled v1.6.x Spec Items (implemented as data but not rendered)
1. Thesis-split calibration curve (V160 §2.6) — data built, renderer unchanged.
2. Thesis-split + timestamp X-axis WR trend (V160 §2.8) — data built, renderer unchanged.
3. Thesis-split grouped signal WR bars (V160 §2.7) — data built, renderer unchanged.
4. Win rate per cell in thesis matrix (V160 §2.9) — field computed, SVG ignores it.
5. Validator warnings in Panel 1 active window (V160 §3.5) — field in dict, not rendered.
6. Scale entries in Panel 1 active window (V160 §3.5) — field in dict, not rendered.
7. Full skip reason in Panel 3 (V160 §3.6) — truncated to 120 chars instead.

### Dead Code Count
- 7 dead/orphaned Python functions in `dashboard_data.py`
- 5 dead context keys
- 5 dead `rendered_lists` keys (3 consumed only by dead context)
- 2 stale CSS variables causing thesis color inconsistency
- ~400 LoC of dead code estimable from above

### Architecture Recommendation
The four-module split proposed in Section 8 should accompany the v1.6.7 rebuild. The current 4,176-line file will grow further with thesis-split SVG renderers; splitting now prevents the file from crossing 5,000 lines. Target: `dashboard_data.py` (~700), `dashboard_render.py` (~1,100), `chart_svg.py` (~500), `dashboard_helpers.py` (~150).

### Mobile Recommendation
The heatmap and signal WR bars are fundamentally desktop charts at their current designs. For v1.6.7, either:
- Accept mobile failure and document it (operator tool, desktop-primary); OR
- Render the heatmap as a scrollable wrapper (`overflow-x: auto` around the table) and fix the SVG label approach for signal WR bars.
