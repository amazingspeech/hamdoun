# KwantIQ Rename Completion — Design

**Status:** Approved (mechanical continuation of the already-approved 2026-07-28 Prospero rebrand; domain/deploy infra already cut over to `kwantiq.tessar.nl`).

## Goal

Finish the KwantIQ rename: replace remaining "Prospero" UI/backend text with "KwantIQ", and wire the two already-created, currently-unwired logo SVGs (`dashboard/assets/kwantiq-icoon.svg`, `dashboard/assets/kwantiq-logo.svg`) into the live brand areas. No color, layout, or type-system changes — those are inherited unchanged from the Prospero rebrand (OKLCH emerald/jade, hue 155).

## Scope

**In scope — text rename** (all currently read "Prospero", verified via grep 2026-07-29):
- `dashboard/index.html:5,16,71` — `<title>`, `.portfolio-sidebar-merk`, `.eyebrow`
- `dashboard/team.html:5,16,71`
- `dashboard/overview.html:5,16`
- `dashboard/login.html:5,17`
- `dashboard/signup.html:5,17`
- `dashboard/signup-gelukt.html:5,17`
- `dashboard/wachtwoord-vergeten.html:5,17`
- `dashboard/wachtwoord-resetten.html:5,17`
- `dashboard/hoe-werkt-dit.html:5,17,26,37` (title, eyebrow, two body-text mentions)
- `dashboard/sidebar.js:168` — footer version/copyright string
- `serving/app.py:126` — FastAPI `title="Prospero (by Tessar)"`
- `serving/app.py:289` — password-reset email body text
- `serving/herbestel_email.py:92` — weekly herbestel email body text

Subtitle "Vraagvoorspelling" is kept unchanged everywhere (`.eyebrow-sub`, `.portfolio-sidebar-submerk`) — same primary-name-plus-subtitle pattern as Certo's "BY TESSAR" and the prior Prospero rebrand.

**In scope — logo wiring:**
- `.portfolio-sidebar-merk` (in `index.html`, `overview.html`, `team.html`) and `.eyebrow` (in every auth/marketing page) currently render as plain `<p>Prospero</p>`. Replace with the inline `kwantiq-icoon.svg` markup (16×16 via CSS) placed inline before the text "KwantIQ", flex-aligned.
- Add two small CSS rules: `.eyebrow, .portfolio-sidebar-merk { display:flex; align-items:center; gap:6px; }` and `.merk-icoon { width:16px; height:16px; flex-shrink:0; }`.
- Add a favicon: `<link rel="icon" type="image/svg+xml" href="assets/kwantiq-icoon.svg">` in every page's `<head>` — the icon SVG was explicitly authored "sized to work from favicon scale up", and no favicon currently exists anywhere in the app. One line per page, zero design risk.
- `kwantiq-logo.svg` (the full wordmark) is authored but has no additional placement in this scope — inlining the icon + live "KwantIQ" text achieves the same visual result with correct dark/light theming (the wordmark SVG hardcodes a single text fill color; the live `<p>` text instead inherits `color:var(--ink)`, which already adapts to dark mode, so using the icon-only mark plus real text is strictly better here). The wordmark file stays in the repo as a standalone asset (e.g. future marketing use) — not a defect, no cleanup needed.

**Explicitly out of scope:**
- Any further domain/deploy/DNS work (already done).
- Stripe product/pricing naming (user handles separately, confirmed in prior session).
- Color, type, or layout changes beyond the two small CSS rules above.
- `kwantiq-logo.svg` wordmark placement anywhere — deferred, not a gap.

## Testing

No automated frontend tests exist in this project (established convention) — verify via curl (backend text: `/`, password-reset and herbestel email templates if testable without triggering real sends) and claude-in-chrome for the HTML/CSS changes, in both light and dark theme, without ever entering login credentials (hard rule). Where login-gated pages can't be interactively verified, fall back to curl-based deployment checks plus code tracing, same pattern as the forecast-insights-redesign work.

## Self-review

- Placeholder scan: none — every location has exact file:line and exact old/new text.
- Consistency: subtitle pattern, color tokens, and scope boundaries all match the approved Prospero-rebrand precedent; no contradiction.
- Scope: single cohesive rename + logo-wiring task, appropriately sized for one plan, no decomposition needed.
- Ambiguity: resolved the one open design choice (icon-only inline vs. full wordmark SVG) in favor of icon+live-text, with reasoning (dark-mode correctness) documented above.
