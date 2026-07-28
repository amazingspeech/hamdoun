# Self-serve onboarding: voorbeeld-voorspelling + "Aan de slag"-checklist

**Status:** approved design, not yet implemented
**Date:** 2026-07-28
**Context:** part of a larger "tier omhoog" (level-up) initiative for Vraagvoorspelling, decomposed into three independent sub-projects: onboarding (this spec), verkoopklaarheid (marketing/pricing page), and productdiepte (integraties/alerts). Onboarding was chosen to go first — a polished pricing page sending people into a confusing first experience costs more than it earns, and productdiepte serves existing customers rather than growth.

## Problem

A self-serve organisation (self-serve signup, no shared Rossmann-model store bindings — see `FASE4-SAAS-FOUNDATION.md` decision 4) lands on a nearly empty product:

- `index.html` (single-store forecast) can never show anything meaningful for a self-serve org — its winkel-select is always empty, because self-serve orgs never get shared-model store bindings. This is a **permanent** structural fact about this org type, not a transient "new user" state.
- The organisation's own forecast (`serving/eigen_voorspelling.py`) requires a minimum of `MINIMUM_DAGEN` (28) days of uploaded sales history before it produces anything at all — so even a highly motivated new signup sees nothing useful for weeks.
- There is currently no in-product guidance pointing a new signup toward "upload your CSV on Team beheren" as the very next action.

Net effect: a brand-new self-serve customer's first real experience of the product is several empty states in a row, with no clear next step and no sense of what the finished product actually looks like.

## Goal

Give every self-serve organisation (defined as: `GET /winkels` returns an empty list — this condition is permanent for this org type, not new-user-only) two things:

1. On `index.html`, where the single-store forecast view is permanently empty for this org type: a real, live, clearly-labelled example forecast, so they understand what the tool produces before their own data exists.
2. On all three pages: a short, persistent checklist pointing at the two concrete actions that unlock their own real forecast.

## Explicitly out of scope

- The public marketing/pricing page ("verkoopklaarheid" sub-project — separate spec).
- POS/webshop integrations, proactive alerts, deeper per-product analytics ("productdiepte" sub-project — separate spec).
- Lowering the 28-day minimum-history threshold, or showing an early/unreliable forecast with a caveat — considered and explicitly rejected during brainstorming, since it reintroduces the false-precision risk this project has deliberately avoided everywhere else (see `serving/eigen_voorspelling.py`'s own docstring).
- A full multi-step onboarding wizard — considered as "Approach C" during brainstorming and rejected as more build/maintenance surface than this audience (time-poor zzp'ers) needs; the lighter checklist + inline example covers the same need.

## Architecture

Two independent additions, deliberately isolated from the existing tenant-isolation logic rather than loosening it:

### 1. A separate, deliberately public "voorbeeld" forecast endpoint

`GET /voorbeeld/forecast` — session-gated (any logged-in user, no organisatie/store binding check at all). It calls the same `serving.forecast.voorspel_periode()` function `/forecast` already uses internally, but against one fixed, **configured** example store id — never against `db_winkels`/`hoort_store_bij_organisatie`. This is not a loosened version of the real tenant-isolation check; it is a code path that was never tenant-scoped to begin with, which keeps zero risk of ever accidentally weakening the real isolation logic used by `/forecast`, `/portfolio`, etc.

- New setting in `serving/config.py`: `voorbeeld_store_id` (int), read from an environment variable so the example store can change without a code deploy. No default baked into code — if unset, the endpoint returns a clean 503 (see Error handling).
- Fixed horizon (14 days) and a `start_datum` computed the same way `/portfolio` already does (`trainingsperiode_eind + 1 dag`) — no query parameters, since this is a canned example, not a user-configurable forecast.
- Response reuses the existing `ForecastResponse` schema.

### 2. A lightweight, computed "Aan de slag"-checklist

No new backend endpoint. Two items, each derived from data the backend already exposes:

- "Upload je verkoopdata" — complete once `GET /organisatie/verkoopdata` returns ≥1 row.
- "Stel je herbestel-prijs in" — complete once `GET /organisatie/instellingen`'s `gemiddelde_omzet_per_stuk` is non-null.

## Components

**Backend**
- `serving/config.py` — add `voorbeeld_store_id: Optional[int] = None`, loaded from `VOORBEELD_STORE_ID` env var, following the existing optional-settings pattern (Stripe/mail vars) rather than failing hard at startup.
- `serving/app.py` — new `GET /voorbeeld/forecast` endpoint (`Depends(vereis_sessie)`), returns `ForecastResponse`. Raises 503 if `voorbeeld_store_id` is unset, or if the configured store id isn't present in the currently-loaded model artifact (an anticipated failure mode after a future model retrain, not an accidental crash).

**Frontend — new shared `dashboard/onboarding.js`** (parallel to the existing `dashboard/sidebar.js`, loaded on all three pages after `sidebar.js`):
- `initOnboarding(me, heeftWinkels)` — orchestrates both pieces below. Called from each page's existing `DOMContentLoaded` handler, right after `initPortfolioSidebar(me)`, passing whether `laadWinkels()`/`haalWinkels()` returned any rows (each page already fetches this for its own purposes — no duplicate call).
- `toonOnboardingChecklist(status)` — renders/hides the checklist card. Dismiss state stored in localStorage, namespaced by `organisatie_id` (same `sidebarSleutel()`-style helper as the sidebar fix from earlier today — duplicated as a small local helper rather than imported, to keep `onboarding.js` independent of `sidebar.js` internals). Auto-hides once both items are complete, independent of the manual-dismiss flag.
- `toonVoorbeeldVoorspelling()` — fetches `/voorbeeld/forecast` and renders a **compact, self-contained** summary card ("Voorbeeld — Winkel 1 verkoopt de komende 14 dagen waarschijnlijk ongeveer €X, bandbreedte €Y–€Z"), clearly labelled "Voorbeeld" via a badge reusing the existing `.premium-badge`-style visual treatment (different color, same shape) so it can never be mistaken for the organisation's own numbers. Deliberately does **not** reuse `dashboard.js`'s full chart/SHAP-factors rendering — this keeps `onboarding.js` self-contained rather than reaching into another page-specific file's internals.

**Markup** (small additions to `overview.html`, `index.html`, `team.html`):
- A checklist placeholder near the top of each page's main content: `<div id="onboarding-checklist" hidden>`.
- `index.html` only: a voorbeeld-preview slot inside the existing empty state (`#leeg`), enriching it rather than replacing its structure.

**CSS**: new rules in `dashboard/styles.css` for `.onboarding-checklist`, `.onboarding-item` (checked/unchecked states), and `.voorbeeld-kaart` + a "Voorbeeld" badge variant — additive only, no existing rules touched (same discipline as every prior frontend round this engagement).

## Data flow

1. On page load, after `initToegang()`/`haalMe()` resolves and the page's own winkel-list fetch completes, call `initOnboarding(me, winkels.length > 0)`.
2. If `winkels.length > 0` (shared-model org — always operator-onboarded, already has working data from day one): do nothing. Neither the checklist nor the voorbeeld-preview is relevant for this org type.
3. If `winkels.length === 0` (self-serve org, permanent condition for this type):
   - Fetch `/organisatie/verkoopdata` + `/organisatie/instellingen`, derive checklist completion, render or hide the checklist per the dismiss/completion rules above.
   - On `index.html` specifically: inside the existing empty-winkel-select branch, additionally fetch `/voorbeeld/forecast` and render the compact preview card.

## Error handling

Both new UI pieces fail silently on any fetch error (hide the section, no visible error) — a broken-looking widget in someone's first minutes with the product is a worse outcome than the widget simply not appearing, consistent with how the sidebar's mini-KPIs already handle their own fetch failures. The backend endpoint itself distinguishes its two anticipated failure modes (unconfigured, or configured store missing from the current model) with a clean 503 rather than an unhandled 500.

## Testing

- **Backend** (`/voorbeeld/forecast`): full TDD, RED-then-GREEN, covering — works for a session with zero store bindings of its own (the core point of the endpoint), requires a session (401 without one), returns the expected `ForecastResponse` shape, and the two 503 cases (unconfigured store id; configured store id absent from the loaded artifact).
- **Frontend**: no automated JS tests, consistent with every prior dashboard-only round this engagement — live-verified in-browser instead: a self-serve org (zero winkels) sees the voorbeeld card on `index.html` and the checklist on all three pages; uploading a CSV and setting a herbestel-prijs make the checklist items flip and the whole card disappear; a shared-model org (like the live demo org) sees neither piece at all.
