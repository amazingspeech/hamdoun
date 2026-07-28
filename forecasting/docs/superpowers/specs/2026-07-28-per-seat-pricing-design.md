# Self-serve pricing model: per-teamlid, per-vestiging, en KVK-hergebruik

**Status:** approved design, not yet implemented
**Date:** 2026-07-28
**Context:** Product owner wants to move self-serve signups from a single flat price to a usage-based model. This spec covers only the pricing-model change. A related but separate request from the same conversation — auditing which existing features should join the "visible but Premium-locked" pattern — is out of scope here and will get its own spec.

## Problem

The self-serve signup flow (`POST /signup` → Stripe Checkout → `POST /webhooks/stripe`) currently charges one flat price (`STRIPE_PRICE_ID`) for every organisation, regardless of team size or number of store locations, and has no concept of a company signing up more than once. The product owner wants to:

1. Charge €5/month for each team member beyond the eigenaar.
2. Charge €10/month for each store location ("vestiging") beyond the first, declared at signup time.
3. Let a company sign up more than once under the same KVK-nummer (deliberately allowed, not blocked — the owner wants to encourage this as extra revenue), but skip the 14-day free trial for any signup after the first under a given KVK-nummer.
4. Show a live-updating total price on the signup screen as the prospect adjusts team-member and vestiging counts.

## Explicitly out of scope

- **Real multi-winkel self-serve forecasting.** Self-serve organisations today get one combined forecast from one uploaded sales-history CSV per organisation — there is no per-store data model in that path at all (unlike shared-model organisations, which do have real per-store records). Building actual per-store forecasting for self-serve customers is a large, separate feature. In this spec, "vestiging" is a **billing-only declared number** — it changes the price, not what the product does. Explicitly deferred to a future project.
- **Verified KVK-nummer lookups.** The KVK-nummer field is validated for format only (8 digits), not checked against the real KVK register. This means the "no free trial on repeat KVK-nummer" rule can be defeated by entering a different made-up number each time. Accepted trade-off: the goal here is encouraging legitimate repeat signups to pay full price, not airtight fraud prevention. Real KVK verification (an external API integration) is a candidate for later if abuse is actually observed.
- **Self-serve seat/vestiging upgrades after signup.** If an eigenaar wants more team members or wants to update their declared vestiging count after signing up, there is no in-product flow for that in this spec — they're pointed to contact support. A self-serve "buy more seats" flow (with a live Stripe subscription-quantity update) is a reasonable future iteration once "contact us" starts feeling like real friction, but isn't built now.
- **Existing (already-signed-up) self-serve organisations are not retroactively limited.** They have no `ingekochte_leden`/`ingekochte_winkels`/`kvk_nummer` on file after this ships; a missing (`NULL`) purchased-seat count means "no limit" — the new cap check simply never applies to them. No backfill, no forced migration to the new model.
- **Manually onboarded (shared-model) organisations are untouched.** This entire pricing model applies only to the self-serve Stripe signup path (`POST /signup`). Operator-onboarded organisations (`db.bootstrap.bootstrap_organisatie` called directly, outside the signup flow) are unaffected.

## Architecture

Three new inputs join `SignupVerzoek`: `kvk_nummer` (string, 8 digits), `aantal_leden` (int, ≥1, default 1 — **total** desired users including the eigenaar, not "extra" members), `aantal_winkels` (int, ≥1, default 1). These flow through the existing pending-signup mechanism (`db.aanmeldingen`) exactly the way every other signup field already does, and get written onto the new `organisatie` row by the webhook handler at the same point `trial_verloopt_op` is already set today — no new plumbing pattern, just extending the existing one.

**Pricing:** two new Stripe Price objects are created in the Stripe dashboard (not in code) — "extra teamlid" (€5/mo) and "extra vestiging" (€10/mo) — referenced via two new settings, `stripe_price_id_extra_lid` and `stripe_price_id_extra_winkel`, following the exact optional/fail-gracefully pattern `stripe_price_id` already uses. The Checkout Session gets up to three line items: the base price (always, quantity 1) plus the two extras, each included only when its quantity is greater than zero (Stripe rejects a zero-quantity line item). **The backend never computes or stores a euro amount itself** — it only ever deals in Price IDs and quantities; Stripe's own configured Price amounts are the sole source of truth for what gets charged. Only the signup page's JavaScript needs the actual €29/€5/€10 figures, purely to render a live preview before the prospect is redirected to Stripe — an accepted, minor duplication (if a price is ever changed in the Stripe dashboard, the frontend's hardcoded preview number needs a matching manual update, or the preview will silently drift from the real charge).

**Base price note:** the signup page currently displays "€ 49 per maand," a pre-existing inconsistency with the actual product direction. Market research into comparable demand-forecasting/inventory-optimization SaaS (ProfitRover, Inventoro, StockTrim, Fabrikatör — all €40-300+/month; the closest Dutch comparable, Foreseen, has no public self-serve price at all) found nothing in this category priced near €9,99, and confirmed €29/month as a defensible middle ground: serious enough for an analytics/decision-support tool, softer than €49 for a first-time price-sensitive zzp buyer, and proportionate against the new €5/€10 add-ons (a €10 add-on costing more than a €9,99 base would have been an incoherent pricing ladder). €29/month is the base price used throughout this spec and the implementation plan.

**KVK-nummer reuse:** at signup, if the submitted `kvk_nummer` already belongs to an existing organisation, two things change from the normal flow: (1) the Stripe Checkout Session is created *without* `trial_period_days` at all (Stripe requires that field to be a positive integer if present — there's no such thing as "0 days trial," so for a repeat KVK-nummer the field is omitted entirely, meaning Stripe charges the card immediately on checkout completion), and (2) the webhook sets the new organisation's `trial_verloopt_op` to `NULL` instead of "+14 days," which is the exact same value a manually-onboarded organisation already has — reusing `is_in_proefperiode()`'s existing NULL-means-never-in-trial logic (`db/organisaties.py:75-88`) rather than inventing a new "already expired" state.

**Seat cap:** `ingekochte_leden` (the `aantal_leden` value from signup) is stored on the organisation. `POST /gebruikers` gains one new check: count of active (`actief=True`) `gebruikers` in the organisation must be below `ingekochte_leden`, else 403. If `ingekochte_leden` is `NULL` (every organisation that existed before this feature shipped), the check is skipped entirely — no limit. Removing a team member frees up their slot for a new one, since the check counts *active* members, not lifetime signups — this uses the `actief` flag the schema already has, no new concept.

**Vestiging count** (`ingekochte_winkels`) is stored purely for display (e.g. on `team.html`, so a seat-cap 403 later has visible context) — nothing in the product enforces or reacts to it.

## Components

**Backend**
- `serving/schemas.py` — `SignupVerzoek` gains `kvk_nummer: str` (regex-validated, 8 digits), `aantal_leden: int = 1` (≥1), `aantal_winkels: int = 1` (≥1).
- `db/schema.py` — `aanmeldingen` gains `kvk_nummer`, `aantal_leden`, `aantal_winkels` columns. `organisaties` gains `kvk_nummer`, `ingekochte_leden`, `ingekochte_winkels` columns. All nullable, added via the existing auto-migration path already used for `trial_verloopt_op` and others — no new migration tooling needed.
- `db/aanmeldingen.py` — `maak_aanmelding()` extended to accept and store the three new fields.
- `db/organisaties.py` — new `kvk_nummer_heeft_organisatie(engine, kvk_nummer) -> bool`, used by `POST /signup` to decide trial-or-not. `bootstrap_organisatie()` (in `db/bootstrap.py`) extended with optional `kvk_nummer`, `ingekochte_leden`, `ingekochte_winkels` parameters, mirroring how it already accepts `trial_verloopt_op`.
- `serving/betaalintegratie.py` — `maak_checkout_sessie()`: `proefperiode_dagen` becomes `Optional[int]`; when `None` (or not provided), `subscription_data` is built without a `trial_period_days` key at all, instead of passing `0`. `line_items` becomes a list built from up to three components (base + conditionally extra-lid + conditionally extra-winkel) instead of a single hardcoded entry.
- `serving/config.py` — two new optional settings, `stripe_price_id_extra_lid` and `stripe_price_id_extra_winkel`, same pattern as `stripe_price_id`.
- `serving/app.py`:
  - `POST /signup` — the existing config-check (`all([stripe_secret_key, stripe_price_id, app_basis_url])`) grows to also require both new price IDs. Computes `is_herhaling = kvk_nummer_heeft_organisatie(...)`, passes `proefperiode_dagen=None if is_herhaling else SIGNUP_PROEFPERIODE_DAGEN` to `maak_checkout_sessie`, and stores the three new fields via `maak_aanmelding`.
  - `POST /webhooks/stripe` — reads the three new fields off the `aanmelding` row, passes them into `bootstrap_organisatie(...)`, and sets `trial_verloopt_op=None if aanmelding.kvk_nummer_was_herhaling else (now + 14 days)`. (Whether "was this a repeat" is re-derived at webhook time or carried on the `aanmeldingen` row from signup time is an implementation detail for the plan — re-deriving is simpler but has a tiny theoretical race if two signups for the same new KVK-nummer complete within the same window; carrying a flag on the row avoids that at the cost of one more column. Flagging for the plan to pick one, not blocking here.)
  - `POST /gebruikers` — new check: `aantal_actieve_gebruikers(organisatie_id) < ingekochte_leden` (skipped when `ingekochte_leden IS NULL`), else 403 with a clear message.

**Frontend**
- `dashboard/signup.html` + `account.js` (`initSignupPagina`) — new fields: KVK-nummer text input, "Totaal aantal gebruikers (inclusief jezelf)" number input (default 1, so the label is explicit about including the eigenaar — this was a real ambiguity caught during design review), "Aantal vestigingen" number input (default 1, with a helper note that the first is free). A price line recomputes on every change of either number, using the same €29 + €5×(leden−1) + €10×(winkels−1) formula the backend implicitly encodes via its Stripe line items — display-only, not the actual charge mechanism.
- `dashboard/team.html` — a small read-only line showing the organisation's purchased counts, so a future seat-cap 403 has visible context instead of appearing out of nowhere.

## Data flow

1. Prospect on `signup.html` adjusts the teamleden/vestigingen steppers (or leaves both at 1, the free tier) and sees the live total update.
2. Submits bedrijfsnaam, e-mail, wachtwoord, KVK-nummer.
3. `POST /signup` validates the KVK-nummer format, checks whether it's a repeat, builds the Checkout Session (with or without a trial period, and with the correct line items), and stores everything in `aanmeldingen`.
4. Prospect completes payment on Stripe's own hosted page — unchanged, still the only place card data is entered.
5. Stripe's `checkout.session.completed` webhook fires; the handler creates the organisation + eigenaar exactly as today, additionally writing `kvk_nummer`/`ingekochte_leden`/`ingekochte_winkels` and setting `trial_verloopt_op` per the repeat-KVK rule above.
6. Later, if the eigenaar tries to add a team member beyond their purchased count, `POST /gebruikers` returns 403 with a message pointing them to contact support — no live Stripe interaction happens at this point, consistent with this being a fixed-at-signup model for now.

## Error handling

- Malformed/missing `kvk_nummer`, or either count field `< 1` → standard 422 (Pydantic), same as every other `SignupVerzoek` field today.
- Any of the three Stripe price IDs unconfigured → `POST /signup` returns 503 "Self-serve aanmelden is nog niet geconfigureerd," identical wording/behavior to the existing single-price check.
- Seat cap reached → 403 on `POST /gebruikers`, with a clear, visible message — this is a real stop the user needs to see and act on, not a background/silent failure.
- A `checkout.session.completed` webhook whose matching `aanmeldingen` row is somehow missing one of the new fields (shouldn't happen, but defensively): fall back to `aantal_leden=1`/`aantal_winkels=1` rather than fail the webhook — a slightly-wrong purchased count is recoverable via support contact; a crashed webhook means a paying customer never gets their account created at all.

## Testing

**Backend**, full TDD per this project's established discipline:
- Checkout line-item construction: base-only when both counts are 1; correct additional line items and quantities when either count is higher; zero-quantity lines are never sent to Stripe.
- `trial_period_days` omitted (not zero) when the signup is a KVK repeat.
- `kvk_nummer_heeft_organisatie()` correctly detects a repeat vs. a first-time KVK-nummer.
- Webhook correctly transfers `kvk_nummer`/`ingekochte_leden`/`ingekochte_winkels` from `aanmeldingen` onto the new `organisatie`, and sets `trial_verloopt_op` to `NULL` for a repeat KVK-nummer vs. +14 days for a first-time one.
- `POST /gebruikers` seat-cap check: blocked at cap, allowed under cap, no limit applied when `ingekochte_leden IS NULL` (pre-existing organisations).

**Frontend**, browser-verified only (no automated JS tests, per established project convention):
- The price line updates correctly as both steppers change, including back to the free-tier defaults.
- Form validation and the pre-redirect portion of the flow work end to end.
- Actually completing a Stripe Checkout payment cannot be verified via automated browser session (entering card data, even a Stripe test card, is out of scope for an agentic session) — full "the right amount actually gets charged" verification relies on the backend's line-item-construction test coverage as the primary guarantee, with a manual pass in Stripe test mode as a secondary check if the product owner wants one before going live.
