# Dashboard Premium Visual Redesign — Design

**Status:** Approved (Approach A — "monochrome-plus-signal").

## Problem

The dashboard (`forecasting/dashboard/`) reads as "AI-generated" despite deliberate work tonight on color and branding. Research (see below) shows the actual cause is structural, not a palette choice: every distinct concept — Betrouwbaarheid, Sterkste patroon, each secondary stat, each metric — gets identical treatment (white card, 1px border, 8–14px radius, occasional shadow), so nothing signals importance and the page reads as an undifferentiated grid of boxes. This is the same underlying pattern as the well-documented "AI slop" tells (uniform rounded-card grids, one accent color spread everywhere, big-number-small-label repeated as the only visual idiom) even though the specific values (emerald accent, Bricolage Grotesque, no purple/Inter) were genuinely chosen, not defaulted.

Research grounding (2026-07-29): "AI slop" tells — Inter/purple-gradient defaults, uniform rounded-card grids, weightless copy (925studios.co, dev.to/alanwest). Premium B2B patterns (Stripe/Linear/Vercel, via mantlr.com) — typography as a deliberate brand anchor, color restricted to 4–5 semantic meanings rather than decorative spread, crafted microstates, hairline borders at low alpha, tabular numerals everywhere, hierarchy through restraint rather than density.

## Goal

Fix the structural sameness, not the brand. Keep the emerald accent hue and the Bricolage Grotesque/IBM Plex pairing — both already good, both already "chosen" per the research checklist. Change what actually reads as generic: card hierarchy, color's *job*, type scale density, border treatment.

## Direction: Approach A, "monochrome-plus-signal"

### 1. Color tokens (`dashboard/styles.css` `:root` and `:root[data-theme="dark"]` / `@media (prefers-color-scheme: dark)` blocks)

Base neutrals shift from the current warm-cream/warm-dark hue (95 light / 55 dark) to a true, cool-neutral hue (240) with very low chroma — the "engineered dashboard" neutral Linear/Vercel use, versus today's "cozy consumer app" warmth. Exact new values:

**Light:**
```
--paper: oklch(98% 0.003 240);
--paper-raised: oklch(100% 0 0);        /* unchanged, already neutral */
--ink: oklch(18% 0.006 240);            /* was 21% 0.025 150 — darker, cooler, more contrast */
--ink-soft: oklch(44% 0.006 240);
--ink-faint: oklch(58% 0.005 240);
--line: oklch(90% 0.004 240);
--line-strong: oklch(82% 0.005 240);
```

**Dark:** (apply to both `:root[data-theme="dark"]` and the `@media (prefers-color-scheme: dark)` block, matching the existing dual-block pattern)
```
--paper: oklch(15% 0.004 240);
--paper-raised: oklch(19% 0.004 240);
--ink: oklch(94% 0.004 240);
--ink-soft: oklch(75% 0.005 240);
--ink-faint: oklch(56% 0.004 240);
--line: oklch(30% 0.006 240);
--line-strong: oklch(38% 0.006 240);
```

`--accent`, `--accent-ink`, `--band`, `--band-line`, `--warn`, `--warn-soft`, `--accent-soft`, `--fout` are **unchanged** in both modes — the brand hue and semantic colors stay exactly as they are; only the neutral scaffolding around them changes.

**Accent usage rule (behavioral, not just a token change):** emerald stops being a decorative fill. It appears only where it signals something: the forecast line/band, the "up" trend arrow, active nav state, `:focus-visible` rings, links. It no longer fills the primary button or any card/chip background.

**Primary button (`.btn`, `dashboard/styles.css:128-135`):** switches from `background:var(--accent); color:oklch(15% 0.02 155)` to `background:var(--ink); color:var(--paper)` — a solid monochrome fill, matching Stripe/Linear's primary-action treatment. Hover state changes from the current emerald-tinted box-shadow to a simple opacity or subtle lightness shift on the ink fill (exact value decided at implementation time — no new semantic token needed, reuse `--ink-soft`-adjacent logic). `.btn.zacht` (secondary button) is unaffected — it's already border-only.

### 2. Typography scale

Font families unchanged: `--font-display: 'Bricolage Grotesque'`, `--font-body: 'IBM Plex Sans'`, `--font-mono: 'IBM Plex Mono'`. What changes is the scale and its application:

- Hero number (`.hero .waarde`, currently `clamp(2.75rem,9vw,4.5rem)`) tightens to `clamp(2.25rem,7vw,3.5rem)` — still unmistakably the largest thing on the page, but less "landing-page hero," more "dashboard balance."
- `IBM Plex Mono` + `font-variant-numeric: tabular-nums` becomes mandatory on every number on the page. Before this fix wave, `.stat .waarde` and `.inzicht-waarde` only had `font-variant-numeric: tabular-nums` — they were still rendered in `IBM Plex Sans`, never actually in the mono face — while `.portfolio-tabel td.cijfer` did have both. A later fix pass (final-review Important #1) closed that gap by adding `font-family:var(--font-mono)` to `.stat .waarde`, `.inzicht-waarde`, `.metric .value`, `.scenario-resultaat-kaart .waarde`, and `.cockpit-item .value`'s mobile base, so the constraint is now actually met project-wide. This spec also extends it to the hero `.waarde` itself and to the chart's axis labels (`dashboard.js`'s axis-label rendering, currently `IBM Plex Sans` inherited by default), which currently are not monospaced.
- General padding/margin tightening of ~30% across the components touched in section 3 below (exact per-rule values decided at implementation time against the existing scale, not invented wholesale — e.g. `.inzicht-kaart`'s `padding:16px` becomes part of a row with no per-item padding box at all, see below).

### 3. Card hierarchy — the core structural fix

Two tiers, replacing today's uniform "everything is a bordered white box":

**Tier 0 (hero):** `.hero .waarde` keeps zero card/border/background — it already has none, this stays as-is. No change needed here; it's already correctly the exception.

**Tier 1 (grouped secondary data) — the actual fix:** `.inzicht-kaart` (`dashboard/styles.css:174-178`, used for Betrouwbaarheid/Sterkste patroon/portfolio-comparison) and `.metric` (`dashboard/styles.css:246`, used in the "Over dit model" panel) currently each render as an individual `background:var(--paper-raised); border:1px solid var(--line); border-radius:12px` box in a flex-wrap grid. Both convert to the pattern `.secundair` (`dashboard/styles.css:168`) **already uses successfully**: one flex row with `border-top:1px solid var(--line)` (or `border-top` + `border-bottom` if visually needed once implemented) and no per-item border/radius/shadow/background — items are separated by spacing and an optional thin `border-left` divider between flex children, not by each being its own box. This is a direct extension of an already-correct existing pattern to the two places that don't yet use it.

**Tier 2 (chart container):** `#chart-container` (`dashboard/styles.css:182`) keeps its container — a chart legitimately benefits from a visual frame — but `border-radius:14px` shrinks to `8px` and the border itself should read as a hairline (evaluate at implementation time whether `--line` at 1px already reads as hairline against the new cooler neutral palette, or whether a lower-alpha variant is needed).

**Not touched:** `.factor-chip` (pill-shaped chips, `border-radius:999px`) and `.premium-badge` keep their current pill treatment — pills are a distinct, legitimate UI idiom for tags/labels, not part of the "everything is a card" problem this spec targets.

### 4. Scope

This is a `dashboard/styles.css` token/rule change plus applying the Tier-1 hairline-row pattern to `.inzicht-kaart` and `.metric`. It also touches `dashboard/dashboard.js` (chart axis labels gain `font-family:var(--font-mono)` + tabular-nums) and `dashboard/overview.js`/`overview.html` if the portfolio table wrapper (`.portfolio-tabel-wrap`, `dashboard/styles.css:308`) has any per-row-group card treatment worth reconciling with the same Tier-1 pattern — confirm at plan time by reading `overview.html`'s current markup, since it wasn't audited in this design pass.

**Explicitly out of scope:** the brand accent hue, the type family pairing, the logo, the KwantIQ/Vraagvoorspelling name treatment, the sidebar navigation structure, and any backend/data changes. This is a CSS/light-JS visual pass, not a feature or information-architecture change.

## Testing

No automated frontend tests exist in this project (established convention). Verify via claude-in-chrome in both light and dark theme, using the static-harness technique already proven tonight: a standalone HTML file loading the real `dashboard.js`/`styles.css`/`index.html` markup with `window.fetch` stubbed to return realistic synthetic data (`/me`, `/winkels`, `/metrics`, `/forecast`), so the actual production rendering code runs end-to-end without needing to log in — no credentials entered anywhere, consistent with the standing hard rule. Compare before/after screenshots at desktop width (≥961px, where the sidebar grid layout activates) for both the forecast page and, if `overview.html` is touched, the portfolio table.

## Self-review

- Placeholder scan: none — every token has an exact OKLCH value; the one deferred decision (chart-container border alpha, button hover exact shade) is explicitly flagged as "decided at implementation time" with the reasoning for why it's safe to defer (small, reversible, no architectural impact), not a vague gap.
- Consistency: accent/semantic tokens explicitly unchanged in both light and dark blocks; the dual dark-mode block pattern (`:root[data-theme="dark"]` + `@media (prefers-color-scheme: dark)`) is preserved, matching the codebase's established convention from tonight's earlier work.
- Scope: focused enough for a single implementation plan — one CSS token/rule pass plus two small JS touch-points (chart axis font, and a to-confirm portfolio-table check). Does not need decomposition.
- Ambiguity: resolved the one real open question (how "dense" the technical direction gets vs. usability for non-technical shop owners) by design — density lives only in secondary information (Tier 1), the hero number stays maximally legible (Tier 0, unchanged), matching the explicit reasoning given when this approach was chosen over the table-first alternative.
