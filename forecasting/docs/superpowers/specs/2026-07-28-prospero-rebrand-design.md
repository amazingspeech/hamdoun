# Prospero rebrand: name, color identity, domain

**Status:** approved design, not yet implemented
**Date:** 2026-07-28
**Context:** Started as a request to give the live "Vraagvoorspelling" dashboard its own distinct color, separate from generic Tessar branding — the same way Certo (another Tessar product) has its own cream/caramel house style rather than using generic Tessar colors. During the conversation this grew into a full rebrand: a new product name ("Prospero"), following Certo's own pattern of having a real product name distinct from "Tessar" (the agency name, not a product name); and a domain move to match.

## Problem

"Vraagvoorspelling" is a literal Dutch description ("demand forecasting"), not a product name, and the app currently uses generic-adjacent styling rather than an identity of its own. As the product has grown a self-serve pricing model, signup flow, and onboarding UI this session, it increasingly reads as a real, standalone product — one that deserves its own name and visual identity the way Certo already has, rather than staying a feature-described tool running under the shared Tessar palette.

## Goal

Rebrand the live app to "Prospero": a new emerald/jade color identity replacing the current amber accent, "Prospero" as the primary name everywhere with "Vraagvoorspelling" kept as a small subtitle (matching Certo's "BY TESSAR" pattern), and a domain move from `forecasting-demo.tessar.nl` to `prospero.tessar.nl` with a permanent redirect from the old domain.

## Explicitly out of scope

- **The server's internal directory path** (`/home/job/forecasting-demo/` on the Hetzner server) stays exactly as-is. It's invisible to any customer; renaming it would touch docker-compose paths and volume mounts for zero customer-facing benefit, purely added deploy risk. Every reference in this spec to "the server directory" means the existing `forecasting-demo` path, unchanged.
- **Stripe's own product/price names**, as configured in the Stripe dashboard, are not touched by this work — those are the user's own account to update if they want to, separately.
- **Real per-store forecasting, the underlying model, pricing amounts, or any other product behavior** — this is a naming/visual/domain change only, nothing about what the product does changes.

## Architecture

Three coordinated pieces:

1. **Color identity.** `dashboard/styles.css`'s existing `--accent`/`--accent-ink`/`--accent-soft` tokens (light mode, dark mode, and the `@media (prefers-color-scheme: dark)` mirror) move from the current amber (OKLCH hue ~60) to a deep emerald/jade. Reusing the existing token structure — no new CSS architecture, just new values, deliberately chosen to sit far from both Tessar's generic blue (hue ~220–235) and Certo's cream/caramel (warm hue ~30–60), so all three products stay visually distinct from each other.
2. **Naming.** "Prospero" becomes the primary name everywhere the brand currently shows "Vraagvoorspelling": page `<title>` tags, the sidebar/header logo text, the version/copyright line, the FastAPI app's own internal `title=`, and outgoing email text (password-reset email, weekly reorder-advice email). In each spot, "Vraagvoorspelling" is kept as a small subtitle underneath the new name — not deleted — so the descriptive function ("this is a demand-forecasting tool") isn't lost for a first-time visitor.
3. **Domain.** A new Caddy block for `prospero.tessar.nl` (a copy of the existing block, reverse-proxying to the same running API container — same backend, new hostname, auto-provisioned TLS via the existing ACME setup already used for every other `*.tessar.nl` subdomain). The old `forecasting-demo.tessar.nl` block becomes a `redir {uri} permanent` (308, path-preserving) instead of serving the app directly. Production's `APP_BASIS_URL` moves to `https://prospero.tessar.nl` in lockstep, since that value drives password-reset links and Stripe checkout redirect URLs — a functional dependency, not just cosmetic.

## Components

**Color (`dashboard/styles.css`):** new emerald/jade OKLCH values for `--accent`, `--accent-ink`, `--accent-soft` in both the light-mode `:root` block and the dark-mode `:root[data-theme="dark"]` + `@media (prefers-color-scheme: dark)` blocks.

**Naming — dashboard pages** (all in `dashboard/`): `overview.html`, `index.html`, `team.html`, `login.html`, `signup.html`, `signup-gelukt.html`, `wachtwoord-vergeten.html`, `wachtwoord-resetten.html`, `hoe-werkt-dit.html`. Each gets two updates: the `<title>` tag, and wherever the brand appears in the visible page (sidebar `portfolio-sidebar-merk`, or the equivalent header/eyebrow text on the auth-flow pages that don't have the full sidebar).

**Naming — `dashboard/sidebar.js`:** the version/copyright line ("Vraagvoorspelling v1.0.0 · © 2026 Tessar" → "Prospero v1.0.0 · © 2026 Tessar", "Vraagvoorspelling" subtitle handled at the markup level, not duplicated here).

**Naming — backend:** `serving/app.py`'s FastAPI `title="Tessar Vraagvoorspelling"` and the password-reset email body text; `serving/herbestel_email.py`'s weekly email opening line.

**Infrastructure:** `deploy/Caddyfile-snippet` (new `prospero.tessar.nl` block with its own `prospero.log`; old block converted to a redirect, dropping its now-irrelevant JSON access-log directive since it no longer serves real app traffic); `deploy/.env.example` (`APP_BASIS_URL` example value and any comment referencing the old domain); production `.env` on the server (the real `APP_BASIS_URL` value).

**Documentation that operationally matters** (so a future redeploy doesn't regress the domain): `deploy/DEPLOY.md`'s references to `forecasting-demo.tessar.nl`; `RELEASE_CHECKLIST.md` (explicitly marked "reusable per release" — its smoke-test URL and Caddy-log-path lines need to point at the new domain, or the next release run would check the wrong thing).

## Data flow

1. On the server: add the new `prospero.tessar.nl` Caddy block and convert the old block to a redirect; reload Caddy. TLS for the new domain provisions automatically.
2. Update `APP_BASIS_URL` in production `.env` to `https://prospero.tessar.nl`.
3. Deploy the renamed dashboard files (frontend: plain `scp`, live immediately — no rebuild) and the two updated backend files (`serving/app.py`, `serving/herbestel_email.py` — `scp` + `docker compose build && up -d`).
4. Verify both together: `prospero.tessar.nl` serves the fully rebranded app; `forecasting-demo.tessar.nl` returns a 308 to the equivalent path on the new domain; a fresh password-reset request generates a link pointing at the new domain.

Sequencing matters here: Caddy/domain first, then `APP_BASIS_URL`, then verify — never flip them independently, or a generated link could point at a domain that isn't serving yet.

## Error handling

- The redirect is path-preserving (`redir {uri} permanent`), so a bookmarked deep link — not just the homepage — still resolves correctly on the new domain.
- **Existing sessions don't survive the domain switch.** Session cookies are scoped to the domain they were issued on, so anyone already logged in via the old domain (including the demo account, `info@tessar.nl`) will need to log in again on `prospero.tessar.nl` after the cutover. This is an unavoidable, one-time, expected consequence of a domain change — not something to engineer around.

## Testing

**Backend:** this is copy/config changes, not new logic — no new unit tests needed. If any existing test asserts on the literal old brand text (e.g. in an email-content test), that assertion gets updated to match, since the behavior it's testing hasn't changed, only the text.

**Frontend:** no automated tests, per this project's established convention — browser-verified instead: the new color renders correctly in both light and dark mode across `overview.html`/`index.html`/`team.html`; "Prospero" shows as the primary name with "Vraagvoorspelling" as subtitle everywhere the brand appears (including the auth-flow pages); `prospero.tessar.nl` loads with a valid certificate; `forecasting-demo.tessar.nl` returns a 308 redirect to the matching page on the new domain.
