# Prospero Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebrand the live "Vraagvoorspelling" app to "Prospero" — a new emerald/jade color identity, "Prospero" as the primary name with "Vraagvoorspelling" kept as a small subtitle everywhere, and a domain move from `forecasting-demo.tessar.nl` to `prospero.tessar.nl` with a permanent redirect from the old domain.

**Architecture:** All renaming/coloring work (color tokens, page titles, brand markup, email text) happens first and is verified on the *existing* domain, which keeps working unchanged throughout. The domain cutover (new Caddy block, redirect, `APP_BASIS_URL`) is the last, riskiest step, done only once everything else is already live and confirmed correct.

**Tech Stack:** Vanilla CSS/HTML/JS dashboard (no build step), FastAPI backend (Python), Caddy reverse proxy (shared server-level config, not in this repo).

## Global Constraints

- The server's internal directory path (`/home/job/forecasting-demo/` on job@157.90.244.24) stays exactly as-is — never rename it. It's invisible to any customer; renaming it only adds deploy risk (docker-compose paths, volume mounts) for zero customer-facing benefit.
- Stripe's own product/price names (in the Stripe dashboard) are not touched by this plan.
- No product behavior changes — this is naming/visual/domain only.
- "Prospero" is the primary name everywhere the brand currently shows "Vraagvoorspelling"; "Vraagvoorspelling" is kept as a small subtitle underneath, never deleted outright.
- No automated frontend tests exist in this project by established convention — verify color/text changes live in-browser (claude-in-chrome) instead of writing new tests.
- The Caddy instance is **shared infrastructure** also serving Certo (`vandijkprotocol.tessar.nl`) and n8n (`n8n.tessar.nl`) from `~/tessar/Caddyfile` on the same server — any change there must be verified not to have broken those two other sites, immediately after applying it.
- Domain cutover sequencing: Caddy config change first, then `APP_BASIS_URL`, then verify both together — never flip them independently (an out-of-sync `APP_BASIS_URL` would generate password-reset/Stripe-redirect links pointing at a domain that isn't serving yet).
- Deploy: backend changes require `scp` the changed files to `job@157.90.244.24:/home/job/forecasting-demo/` then `docker compose build api && docker compose up -d` from `deploy/`. `dashboard/*` files are bind-mounted — a plain `scp` makes them live immediately, no rebuild.

---

## File Structure

- `dashboard/styles.css` (modify) — 11 color-token values (light/dark/prefers-dark accent tokens + 2 hardcoded on-accent text colors) move from amber (hue 60) to emerald/jade (hue 155); two new CSS classes (`.eyebrow-sub`, `.portfolio-sidebar-submerk`) for the new subtitle text.
- `dashboard/overview.html`, `dashboard/index.html`, `dashboard/team.html` (modify) — title tags, sidebar brand text + new subtitle line.
- `dashboard/sidebar.js` (modify) — version/copyright line text.
- `dashboard/login.html`, `dashboard/signup.html`, `dashboard/signup-gelukt.html`, `dashboard/wachtwoord-vergeten.html`, `dashboard/wachtwoord-resetten.html` (modify) — title tags, eyebrow brand text + new subtitle line.
- `dashboard/hoe-werkt-dit.html` (modify) — title tag, eyebrow + subtitle, plus two body-text sentences that name the product.
- `serving/app.py` (modify) — FastAPI `title=`, password-reset email text.
- `serving/herbestel_email.py` (modify) — weekly reorder-advice email text.
- `deploy/Caddyfile-snippet` (modify) — documents the new `prospero.tessar.nl` block + the old domain's redirect block.
- `deploy/.env.example` (modify) — `APP_BASIS_URL` example value + comment.
- `deploy/DEPLOY.md`, `RELEASE_CHECKLIST.md` (modify) — the subset of lines referring to the *domain* (not the server directory path, which stays unchanged).
- Production `~/tessar/Caddyfile` and `/home/job/forecasting-demo/deploy/.env` on the server (not repo files) — the real cutover.

---

### Task 1: Color identity — `dashboard/styles.css`

**Files:**
- Modify: `dashboard/styles.css`

**Interfaces:**
- Produces: `.eyebrow-sub` and `.portfolio-sidebar-submerk` CSS classes, consumed by Tasks 2, 3, and 4's markup changes.

- [ ] **Step 1: Replace the 9 accent-token values**

In the light-mode `:root` block (currently lines 9, 10, 15):
```css
  --accent: oklch(52% 0.13 155);
  --accent-ink: oklch(30% 0.11 155);
```
and:
```css
  --accent-soft: oklch(94% 0.03 155);
```

In the dark-mode `:root[data-theme="dark"]` block (currently lines 31, 32, 37):
```css
  --accent: oklch(76% 0.14 155);
  --accent-ink: oklch(84% 0.11 155);
```
and:
```css
  --accent-soft: oklch(30% 0.07 155);
```

In the `@media (prefers-color-scheme: dark)` block (currently lines 50, 51, 56) — identical values to the dark-mode block above:
```css
    --accent: oklch(76% 0.14 155);
    --accent-ink: oklch(84% 0.11 155);
```
and:
```css
    --accent-soft: oklch(30% 0.07 155);
```

- [ ] **Step 2: Replace the 2 hardcoded on-accent text colors**

These sit outside the theme blocks (used for text drawn directly on top of an `--accent`-colored button/badge background, same in both themes). Find both occurrences of `oklch(15% 0.02 60)` (currently lines 108 and 119) and change each to:
```css
oklch(15% 0.02 155)
```

- [ ] **Step 3: Add the two new subtitle classes**

Add near the existing `.eyebrow` rule:
```css
.eyebrow-sub { font:400 0.6875rem/1.2 var(--font-body); color:var(--ink-faint); margin:-8px 0 10px; letter-spacing:0.01em; }
```

Add near the existing `.portfolio-sidebar-merk` rule:
```css
  .portfolio-sidebar-submerk {
    font:400 0.6875rem/1.2 var(--font-body); color:var(--ink-faint); margin:-2px 0 0;
  }
```

- [ ] **Step 4: Deploy and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/styles.css job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, navigate to `https://forecasting-demo.tessar.nl/index.html` (old domain still works fine — the cutover hasn't happened yet) and verify:
- Any element previously using the amber accent (buttons, links, active-state highlights) now renders emerald/jade instead, with no visibly broken contrast (text on colored buttons/badges is still clearly legible).
- Toggle to dark mode (or check `?` — use the browser's own dark-mode emulation, or the app's own theme toggle if `dashboard/account.js`'s theme switch is present) and confirm the dark-mode accent also reads as emerald/jade, not amber, and stays legible.
- No layout is broken (the new subtitle CSS classes exist but aren't used in any markup yet — this step only confirms the color swap itself).

- [ ] **Step 5: Commit**

```bash
git add dashboard/styles.css
git commit -m "feat: replace amber accent with emerald/jade color identity for Prospero"
```

---

### Task 2: Rename — portfolio-sidebar pages (`overview.html`, `index.html`, `team.html`) + `sidebar.js`

**Files:**
- Modify: `dashboard/overview.html`, `dashboard/index.html`, `dashboard/team.html`, `dashboard/sidebar.js`

**Interfaces:**
- Consumes: `.portfolio-sidebar-submerk` (Task 1).

- [ ] **Step 1: Update title tags**

In `dashboard/overview.html`, change:
```html
<title>Overzicht — Vraagvoorspelling</title>
```
to:
```html
<title>Overzicht — Prospero</title>
```

In `dashboard/index.html`, change:
```html
<title>Vraagvoorspelling</title>
```
to:
```html
<title>Prospero</title>
```

In `dashboard/team.html`, change:
```html
<title>Team — Vraagvoorspelling</title>
```
to:
```html
<title>Team — Prospero</title>
```

- [ ] **Step 2: Update the sidebar brand markup in all three files**

In each of `dashboard/overview.html`, `dashboard/index.html`, `dashboard/team.html`, find:
```html
    <p class="portfolio-sidebar-merk">Vraagvoorspelling</p>
```
and replace with:
```html
    <p class="portfolio-sidebar-merk">Prospero</p>
    <p class="portfolio-sidebar-submerk">Vraagvoorspelling</p>
```

- [ ] **Step 3: Update the version/copyright line**

In `dashboard/sidebar.js`, change:
```javascript
  if (el) el.textContent = `Vraagvoorspelling v${APP_VERSIE} · © ${new Date().getFullYear()} Tessar`;
```
to:
```javascript
  if (el) el.textContent = `Prospero v${APP_VERSIE} · © ${new Date().getFullYear()} Tessar`;
```

- [ ] **Step 4: Deploy and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/overview.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/index.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/team.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/sidebar.js \
    job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, load each of the three pages on `https://forecasting-demo.tessar.nl/` and verify:
- Browser tab title shows the new "— Prospero" / "Prospero" text.
- Sidebar shows "Prospero" in the existing brand position, with "Vraagvoorspelling" directly beneath it in smaller, muted text — close enough to read as one lockup, not two unrelated lines.
- The version/copyright line at the bottom of the sidebar reads "Prospero v1.0.0 · © 2026 Tessar".

- [ ] **Step 5: Commit**

```bash
git add dashboard/overview.html dashboard/index.html dashboard/team.html dashboard/sidebar.js
git commit -m "feat: rename portfolio-sidebar pages to Prospero"
```

---

### Task 3: Rename — auth-flow pages (`login.html`, `signup.html`, `signup-gelukt.html`, `wachtwoord-vergeten.html`, `wachtwoord-resetten.html`)

**Files:**
- Modify: `dashboard/login.html`, `dashboard/signup.html`, `dashboard/signup-gelukt.html`, `dashboard/wachtwoord-vergeten.html`, `dashboard/wachtwoord-resetten.html`

**Interfaces:**
- Consumes: `.eyebrow-sub` (Task 1).

- [ ] **Step 1: Update title tags**

```html
<!-- login.html -->
<title>Inloggen — Prospero</title>
<!-- signup.html -->
<title>Aanmelden — Prospero</title>
<!-- signup-gelukt.html -->
<title>Aanmelding gelukt — Prospero</title>
<!-- wachtwoord-vergeten.html -->
<title>Wachtwoord vergeten — Prospero</title>
<!-- wachtwoord-resetten.html -->
<title>Nieuw wachtwoord instellen — Prospero</title>
```

- [ ] **Step 2: Update the eyebrow brand markup in all five files**

In each file, find:
```html
      <p class="eyebrow">Vraagvoorspelling</p>
```
and replace with:
```html
      <p class="eyebrow">Prospero</p>
      <p class="eyebrow-sub">Vraagvoorspelling</p>
```

- [ ] **Step 3: Deploy and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/login.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/signup.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/signup-gelukt.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/wachtwoord-vergeten.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/wachtwoord-resetten.html \
    job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, load `https://forecasting-demo.tessar.nl/login.html` and `https://forecasting-demo.tessar.nl/signup.html` and verify:
- Browser tab title updated.
- The small label above the page's main heading now shows "Prospero" with "Vraagvoorspelling" directly beneath in smaller, muted text, with sensible spacing before the heading below it (not cramped, not with an odd gap) — adjust the `.eyebrow-sub` margin value from Task 1 if the spacing looks off, and note that adjustment in this task's commit if made.

- [ ] **Step 4: Commit**

```bash
git add dashboard/login.html dashboard/signup.html dashboard/signup-gelukt.html \
        dashboard/wachtwoord-vergeten.html dashboard/wachtwoord-resetten.html
git commit -m "feat: rename auth-flow pages to Prospero"
```

---

### Task 4: Rename — `hoe-werkt-dit.html`

**Files:**
- Modify: `dashboard/hoe-werkt-dit.html`

**Interfaces:**
- Consumes: `.eyebrow-sub` (Task 1).

- [ ] **Step 1: Update the title tag**

```html
<title>Hoe dit werkt — Prospero</title>
```

- [ ] **Step 2: Update the eyebrow brand markup**

Find:
```html
      <p class="eyebrow">Vraagvoorspelling</p>
```
Replace with:
```html
      <p class="eyebrow">Prospero</p>
      <p class="eyebrow-sub">Vraagvoorspelling</p>
```

- [ ] **Step 3: Update the two body-text sentences that name the product**

This page has two prose sentences (unlike the other auth pages) that name the product directly in body text, not just in the brand markup. Find:
```html
    <p>Je hoeft niet zelf in te schatten hoeveel je deze week gaat verkopen of hoeveel je moet bijbestellen. Vraagvoorspelling doet dat voor je, op basis van je eigen verkoopgeschiedenis — automatisch bijgewerkt, zonder dat jij er iets voor hoeft te doen.</p>
```
and replace with:
```html
    <p>Je hoeft niet zelf in te schatten hoeveel je deze week gaat verkopen of hoeveel je moet bijbestellen. Prospero doet dat voor je, op basis van je eigen verkoopgeschiedenis — automatisch bijgewerkt, zonder dat jij er iets voor hoeft te doen.</p>
```

Find:
```html
    <p>Een voorspelling die beweert exact te weten wat er volgende week gebeurt, is niet eerlijk — de werkelijkheid is nooit zo voorspelbaar. Daarom toont Vraagvoorspelling altijd drie getallen: een realistische ondergrens, de meest waarschijnlijke uitkomst, en een bovengrens voor als het drukker is dan verwacht. Zo kun je plannen voor een rustige én voor een drukke week, in plaats van te vertrouwen op één getal dat toevallig verkeerd kan uitpakken.</p>
```
and replace with:
```html
    <p>Een voorspelling die beweert exact te weten wat er volgende week gebeurt, is niet eerlijk — de werkelijkheid is nooit zo voorspelbaar. Daarom toont Prospero altijd drie getallen: een realistische ondergrens, de meest waarschijnlijke uitkomst, en een bovengrens voor als het drukker is dan verwacht. Zo kun je plannen voor een rustige én voor een drukke week, in plaats van te vertrouwen op één getal dat toevallig verkeerd kan uitpakken.</p>
```

- [ ] **Step 4: Deploy and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/hoe-werkt-dit.html job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, load `https://forecasting-demo.tessar.nl/hoe-werkt-dit.html` and verify the title, eyebrow+subtitle, and both body paragraphs all read "Prospero" instead of "Vraagvoorspelling" in the expected places.

- [ ] **Step 5: Commit**

```bash
git add dashboard/hoe-werkt-dit.html
git commit -m "feat: rename hoe-werkt-dit.html to Prospero"
```

---

### Task 5: Rename — backend (`serving/app.py`, `serving/herbestel_email.py`)

**Files:**
- Modify: `serving/app.py`, `serving/herbestel_email.py`

**Interfaces:** none new — pure text changes to existing strings.

- [ ] **Step 1: Update the FastAPI app title**

In `serving/app.py`, change:
```python
    title="Tessar Vraagvoorspelling",
```
to:
```python
    title="Prospero (by Tessar)",
```

- [ ] **Step 2: Update the password-reset email text**

In `serving/app.py`, find:
```python
                    "Je hebt een wachtwoord-reset aangevraagd voor Vraagvoorspelling.\n\n"
```
and replace with:
```python
                    "Je hebt een wachtwoord-reset aangevraagd voor Prospero.\n\n"
```

- [ ] **Step 3: Update the weekly reorder-advice email text**

In `serving/herbestel_email.py`, find:
```python
        f"Hallo,\n\nDit is je wekelijkse update van Vraagvoorspelling voor {organisatie_naam}.\n\n"
```
and replace with:
```python
        f"Hallo,\n\nDit is je wekelijkse update van Prospero voor {organisatie_naam}.\n\n"
```

- [ ] **Step 4: Check for any test assertions on the old text**

```bash
grep -rn "Tessar Vraagvoorspelling\|wachtwoord-reset aangevraagd voor Vraagvoorspelling\|wekelijkse update van Vraagvoorspelling" /Users/hamdeco/development/hamdoun/forecasting/tests/
```

If this finds any matches, update those test assertions to the new "Prospero" text in the same commit — the behavior they test hasn't changed, only the literal string.

- [ ] **Step 5: Run the full backend test suite to confirm nothing broke**

Local test execution is broken in this environment (macOS native dependency issue) — run via the established remote pattern:

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest -q'"
```

Expected: all tests pass (no behavior changed, only string literals — any pre-existing failure here would indicate a typo in Steps 1-3, not a real regression). Run these commands in the foreground and wait for them to finish — do not background them.

- [ ] **Step 6: Commit**

```bash
git add serving/app.py serving/herbestel_email.py
git commit -m "feat: rename backend-generated text (app title, emails) to Prospero"
```

(Backend deploy for these two files happens together with the domain cutover in Task 6, since both require a container rebuild — no need to deploy twice.)

---

### Task 6: Domain cutover — Caddy, `APP_BASIS_URL`, deploy docs, and going live

**Files:**
- Modify: `deploy/Caddyfile-snippet`, `deploy/.env.example`, `deploy/DEPLOY.md`, `RELEASE_CHECKLIST.md`

**Interfaces:** none new — this task activates everything built in Tasks 1-5 on the new domain, and redirects the old one.

- [ ] **Step 1: Update `deploy/Caddyfile-snippet`**

Replace the entire file content:
```
# Toe te voegen aan de bestaande, gedeelde Caddyfile op de server
# (naast de blokken voor vandijkprotocol.tessar.nl en n8n.tessar.nl).
# Zelfde stijl/headers als Certo's blok — zie DEPLOY.md voor de precieze
# toepas-stappen.
#
# LET OP: Caddy draait hier als container (tessar-caddy-1, onderdeel van
# ~/tessar/docker-compose.yml), niet als host-proces — "127.0.0.1" vanuit
# die container is de container zelf, niet de host. reverse_proxy verwijst
# daarom naar de forecasting-api-container bij naam (api:8000), bereikbaar
# via het gedeelde externe caddy-net-netwerk — zie DEPLOY.md stap 6.

prospero.tessar.nl {
	reverse_proxy api:8000

	encode gzip

	header {
		Strict-Transport-Security "max-age=31536000; includeSubDomains"
		X-Frame-Options "DENY"
		X-Content-Type-Options "nosniff"
		Referrer-Policy "same-origin"
		Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; script-src 'self'; connect-src 'self'"
		-Server
	}

	log {
		output file /var/log/caddy/prospero.log
		format json
	}
}

# Permanente redirect vanaf het oude adres — bestaande bookmarks/links
# blijven werken, komen automatisch op het nieuwe domein uit. {uri} behoudt
# het pad en de querystring.
forecasting-demo.tessar.nl {
	redir https://prospero.tessar.nl{uri} permanent
}
```

- [ ] **Step 2: Update `deploy/.env.example`**

Find:
```
# https://forecasting-demo.tessar.nl, en de MAIL_SMTP_*-waarden (nodig voor
```
Replace with:
```
# https://prospero.tessar.nl, en de MAIL_SMTP_*-waarden (nodig voor
```

Find:
```
APP_BASIS_URL=https://forecasting-demo.tessar.nl
```
Replace with:
```
APP_BASIS_URL=https://prospero.tessar.nl
```

- [ ] **Step 3: Update the domain references in `deploy/DEPLOY.md`**

Update exactly these five lines — every other "forecasting-demo" occurrence in this file is the server's directory path (`/home/job/forecasting-demo/...`) and must NOT be touched, per this plan's Global Constraints.

Find:
```
# Live deployment — forecasting-demo.tessar.nl
```
Replace with:
```
# Live deployment — prospero.tessar.nl
```

Find:
```
- Een DNS A-record voor `forecasting-demo.tessar.nl` naar dat IP — moet al
```
Replace with:
```
- Een DNS A-record voor `prospero.tessar.nl` naar dat IP — moet al
```

Find:
```
# https://forecasting-demo.tessar.nl, en de MAIL_SMTP_*-waarden (nodig voor
```
Replace with:
```
# https://prospero.tessar.nl, en de MAIL_SMTP_*-waarden (nodig voor
```

Find:
```
**Vereist:** het DNS A-record voor `forecasting-demo.tessar.nl` moet al
```
Replace with:
```
**Vereist:** het DNS A-record voor `prospero.tessar.nl` moet al
```

Find:
```
Open `https://forecasting-demo.tessar.nl/login.html` in een browser en log
```
Replace with:
```
Open `https://prospero.tessar.nl/login.html` in een browser en log
```

- [ ] **Step 4: Update the domain references in `RELEASE_CHECKLIST.md`**

Update exactly these three lines — the fourth "forecasting-demo" occurrence in this file (`/home/job/forecasting-demo/deploy` in the rollback section) is the server directory path and must NOT be touched.

Find:
```
Herbruikbaar per release naar `forecasting-demo.tessar.nl`. Loop 'm van boven
```
Replace with:
```
Herbruikbaar per release naar `prospero.tessar.nl`. Loop 'm van boven
```

Find:
```
- [ ] Smoke test op productie: `curl https://forecasting-demo.tessar.nl/health`
```
Replace with:
```
- [ ] Smoke test op productie: `curl https://prospero.tessar.nl/health`
```

Find:
```
- [ ] Caddy-logs (`/var/log/caddy/forecasting-demo.log`) een paar minuten
```
Replace with:
```
- [ ] Caddy-logs (`/var/log/caddy/prospero.log`) een paar minuten
```

- [ ] **Step 5: Commit the doc/config changes**

```bash
git add deploy/Caddyfile-snippet deploy/.env.example deploy/DEPLOY.md RELEASE_CHECKLIST.md
git commit -m "docs: update deploy docs and Caddyfile-snippet for the prospero.tessar.nl domain"
```

- [ ] **Step 6: Apply the new Caddy block on the server**

SSH in and locate the existing `forecasting-demo.tessar.nl` block inside `~/tessar/Caddyfile` (the real, shared production Caddyfile — not this repo's `Caddyfile-snippet`, which is just documentation of what to paste in):

```bash
ssh job@157.90.244.24 "grep -n 'forecasting-demo.tessar.nl' ~/tessar/Caddyfile"
```

Using that line number, replace the existing `forecasting-demo.tessar.nl { ... }` block in `~/tessar/Caddyfile` with the two new blocks from Step 1 above (the `prospero.tessar.nl` block and the redirect block) — edit this file directly on the server (e.g. `ssh job@157.90.244.24` then `nano ~/tessar/Caddyfile`, or pipe a heredoc over SSH). Leave every other block in this shared file (Certo's `vandijkprotocol.tessar.nl`, n8n's `n8n.tessar.nl`) completely untouched.

- [ ] **Step 7: Restart only the Caddy container and verify the other two sites first**

```bash
ssh job@157.90.244.24 "cd ~/tessar && docker compose up -d caddy"
```

Immediately after, before doing anything else:

```bash
curl -s -o /dev/null -w "certo: %{http_code}\n" https://vandijkprotocol.tessar.nl/
curl -s -o /dev/null -w "n8n: %{http_code}\n" https://n8n.tessar.nl/
```

Both must return a normal success/redirect status code (not a connection error or 5xx). If either is broken, this is a shared-infrastructure incident — stop immediately, do not proceed to the next step, and investigate via `ssh job@157.90.244.24 "docker compose -f ~/tessar/docker-compose.yml logs caddy"` before touching anything else.

- [ ] **Step 8: Update production `APP_BASIS_URL`**

```bash
ssh job@157.90.244.24 "sed -i 's|^APP_BASIS_URL=.*|APP_BASIS_URL=https://prospero.tessar.nl|' /home/job/forecasting-demo/deploy/.env"
ssh job@157.90.244.24 "grep '^APP_BASIS_URL=' /home/job/forecasting-demo/deploy/.env"
```

- [ ] **Step 9: Deploy the renamed backend files and restart the API container**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/serving/app.py \
    /Users/hamdeco/development/hamdoun/forecasting/serving/herbestel_email.py \
    job@157.90.244.24:/home/job/forecasting-demo/serving/

ssh job@157.90.244.24 "cd /home/job/forecasting-demo/deploy && docker compose build api && docker compose up -d"
```

- [ ] **Step 10: Verify the new domain end-to-end**

```bash
curl -s https://prospero.tessar.nl/health
curl -s -o /dev/null -w "old domain redirect: %{http_code}\n" https://forecasting-demo.tessar.nl/login.html
curl -sI https://forecasting-demo.tessar.nl/login.html | grep -i location
```

Expected: the health check returns `{"status":"ok", ...}` from the new domain; the old domain's login page returns a redirect status (308) with a `Location` header pointing at `https://prospero.tessar.nl/login.html` (confirming the path was preserved, not just the bare domain).

Using claude-in-chrome, navigate to `https://prospero.tessar.nl/login.html` and confirm the page loads correctly with a valid TLS certificate (no browser warning) and the Prospero branding from Tasks 1-4 renders correctly on the new domain. Then navigate to `https://forecasting-demo.tessar.nl/login.html` directly and confirm the browser actually lands on `prospero.tessar.nl/login.html` after following the redirect.

Log in with the existing demo account (`info@tessar.nl`) on the new domain — since session cookies don't carry over across a domain change, this is expected to require a fresh login, not a bug. Confirm the login succeeds and the dashboard loads normally on `prospero.tessar.nl`.

- [ ] **Step 11: Final cleanup check**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/data alpine sh -c 'rm -rf /data/*'" 2>/dev/null || true
```

(Removes the remote test-sync scratch directory used in Task 5, if it still exists, so it doesn't go stale before a future task needs it.)

---

## Self-Review

**Spec coverage:** Every spec section maps to a task — color identity (Task 1), naming across dashboard pages including the auth-flow pages and the one page with body-text prose mentions (Tasks 2-4), backend-generated text (Task 5), and the full domain cutover including deploy-doc accuracy (Task 6). The spec's explicit "server directory path stays unchanged" boundary is respected throughout — Task 6 Steps 3-4 explicitly list which lines to change and which to leave alone, rather than a blanket find-replace that would have caught the directory-path lines too.

**Placeholder scan:** No TBD/TODO markers. Every step has the actual before/after text or exact command. Task 6 Step 6 (editing the live shared Caddyfile) can't show an exact "before" snippet since that file isn't in this repo — the step instead gives the exact `grep` command to locate it and precisely names what to paste in (the two blocks fully spelled out in Step 1), which is as concrete as this step can be without direct access to that file's current content.

**Type consistency:** The two new CSS classes (`.eyebrow-sub`, `.portfolio-sidebar-submerk`) are defined once in Task 1 and consumed with the exact same class names in Tasks 2-4's markup — no naming drift. The emerald/jade hue (155) and exact OKLCH values from Task 1 are not redefined or approximated anywhere else in the plan.
