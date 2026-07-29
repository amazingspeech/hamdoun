# KwantIQ Rename Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all remaining "Prospero" text with "KwantIQ" across the dashboard frontend and backend, and wire the two already-created KwantIQ logo SVG assets into the live sidebar/eyebrow brand areas, then deploy to production.

**Architecture:** Pure text substitution across 12 files (9 HTML pages, `sidebar.js`, `app.py`, `herbestel_email.py`) plus two small additive CSS rules and one inlined SVG icon per brand-name element. No backend logic, schema, or API surface changes. No color/type/layout changes.

**Tech Stack:** Static HTML/CSS/JS dashboard, FastAPI backend (`serving/app.py`), Docker Compose deployment on `job@157.90.244.24`, Caddy reverse proxy already pointing at `kwantiq.tessar.nl`.

## Global Constraints

- Subtitle "Vraagvoorspelling" stays unchanged everywhere (`.eyebrow-sub`, `.portfolio-sidebar-submerk`) — only the primary name changes from "Prospero" to "KwantIQ".
- No color, type, or layout changes beyond the two CSS rules specified in this plan.
- No Stripe product/pricing naming changes (out of scope, handled separately).
- No further domain/DNS/Caddy changes — `kwantiq.tessar.nl` is already live and correctly configured.
- Never enter login credentials in any browser automation step, per the standing hard safety rule. Use curl-based deployment verification for anything login-gated.
- `kwantiq-logo.svg` (full wordmark) is not placed anywhere in this plan — that's an intentional, documented non-gap (see spec).

---

### Task 1: Backend text rename

**Files:**
- Modify: `forecasting/serving/app.py:126` (FastAPI `title=`)
- Modify: `forecasting/serving/app.py:289` (password-reset email body)
- Modify: `forecasting/serving/herbestel_email.py:92` (weekly herbestel email body)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing consumed by later tasks — this is a leaf change verified independently via curl/text inspection.

- [ ] **Step 1: Update the FastAPI app title**

In `forecasting/serving/app.py`, change line 126:

```python
    title="Prospero (by Tessar)",
```

to:

```python
    title="KwantIQ (by Tessar)",
```

- [ ] **Step 2: Update the password-reset email text**

In `forecasting/serving/app.py`, change line 289:

```python
                    "Je hebt een wachtwoord-reset aangevraagd voor Prospero.\n\n"
```

to:

```python
                    "Je hebt een wachtwoord-reset aangevraagd voor KwantIQ.\n\n"
```

- [ ] **Step 3: Update the weekly herbestel email text**

In `forecasting/serving/herbestel_email.py`, change line 92:

```python
        f"Hallo,\n\nDit is je wekelijkse update van Prospero voor {organisatie_naam}.\n\n"
```

to:

```python
        f"Hallo,\n\nDit is je wekelijkse update van KwantIQ voor {organisatie_naam}.\n\n"
```

- [ ] **Step 4: Verify no remaining "Prospero" in these two files**

Run: `grep -n "Prospero" forecasting/serving/app.py forecasting/serving/herbestel_email.py`
Expected: no output (no matches).

- [ ] **Step 5: Run the existing backend test suite**

Run: `cd forecasting && python -m pytest tests/ -x -q`
Expected: all tests pass (this is a pure string-literal change; no test asserts on the old "Prospero" string — if any test unexpectedly fails on the new string, read it and update the expected value to "KwantIQ", since the test would be asserting stale copy, not behavior).

- [ ] **Step 6: Commit**

```bash
cd forecasting && git add serving/app.py serving/herbestel_email.py
git commit -m "rename: KwantIQ in backend-generated text (API title, emails)"
```

---

### Task 2: Frontend text rename + logo/favicon wiring

**Files:**
- Modify: `forecasting/dashboard/index.html:5,16` (title, `.portfolio-sidebar-merk`) + add favicon link + wrap merk in icon
- Modify: `forecasting/dashboard/team.html:5,16,71` (title, `.portfolio-sidebar-merk`, `.eyebrow`) + favicon + icon wiring on both
- Modify: `forecasting/dashboard/overview.html:5,16` (title, `.portfolio-sidebar-merk`) + favicon + icon wiring
- Modify: `forecasting/dashboard/login.html:5,17` (title, `.eyebrow`) + favicon + icon wiring
- Modify: `forecasting/dashboard/signup.html:5,17` + favicon + icon wiring
- Modify: `forecasting/dashboard/signup-gelukt.html:5,17` + favicon + icon wiring
- Modify: `forecasting/dashboard/wachtwoord-vergeten.html:5,17` + favicon + icon wiring
- Modify: `forecasting/dashboard/wachtwoord-resetten.html:5,17` + favicon + icon wiring
- Modify: `forecasting/dashboard/hoe-werkt-dit.html:5,17,26,37` (title, `.eyebrow`, two body mentions) + favicon + icon wiring
- Modify: `forecasting/dashboard/sidebar.js:168` (footer version string)
- Modify: `forecasting/dashboard/styles.css` (two new CSS rules)

**Interfaces:**
- Consumes: `forecasting/dashboard/assets/kwantiq-icoon.svg` (already exists in repo, unmodified by this task) — its exact current markup is:
  ```html
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32" role="img" aria-label="KwantIQ">
    <rect x="4" y="20" width="5" height="8" rx="1.5" fill="oklch(52% 0.13 155)"/>
    <rect x="13.5" y="13" width="5" height="15" rx="1.5" fill="oklch(52% 0.13 155)"/>
    <rect x="23" y="6" width="5" height="22" rx="1.5" fill="oklch(52% 0.13 155)"/>
    <path d="M6.5 18 L16 11 L25.5 4" fill="none" stroke="oklch(30% 0.11 155)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="25.5" cy="4" r="2.75" fill="oklch(30% 0.11 155)"/>
  </svg>
  ```
- Produces: nothing consumed by Task 3 except the fact that all frontend files are renamed and ready to deploy.

- [ ] **Step 1: Add the two CSS rules to `forecasting/dashboard/styles.css`**

Insert immediately after the existing `.eyebrow-sub` rule (currently line 72):

```css
.eyebrow, .portfolio-sidebar-merk { display:flex; align-items:center; gap:6px; }
.merk-icoon { width:16px; height:16px; flex-shrink:0; }
```

Note: `.eyebrow` already has a rule on line 71 (`font:600 0.8125rem/1.2 var(--font-body); color:var(--accent-ink); margin:0 0 10px;`) — this new rule adds `display:flex` etc. as a *second* rule targeting the same selector; both apply (no override conflict, since they set different properties). Same reasoning applies to `.portfolio-sidebar-merk` (existing rule at line 453 inside the `@media (min-width: 961px)` block) — add the new combined selector rule near the top-level rules (not inside that media block), since `display:flex; gap:6px` should apply at all viewport widths.

- [ ] **Step 2: Rename `index.html`**

In `forecasting/dashboard/index.html`, change line 5:
```html
<title>Prospero</title>
```
to:
```html
<title>KwantIQ</title>
```

Add a favicon link right after line 5 (the `<title>` line):
```html
<link rel="icon" type="image/svg+xml" href="./assets/kwantiq-icoon.svg">
```

Change line 16 from:
```html
    <p class="portfolio-sidebar-merk">Prospero</p>
```
to:
```html
    <p class="portfolio-sidebar-merk"><svg class="merk-icoon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img" aria-label="KwantIQ"><rect x="4" y="20" width="5" height="8" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="13.5" y="13" width="5" height="15" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="23" y="6" width="5" height="22" rx="1.5" fill="oklch(52% 0.13 155)"/><path d="M6.5 18 L16 11 L25.5 4" fill="none" stroke="oklch(30% 0.11 155)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><circle cx="25.5" cy="4" r="2.75" fill="oklch(30% 0.11 155)"/></svg>KwantIQ</p>
```

- [ ] **Step 3: Repeat the same pattern for `team.html` and `overview.html`**

Both have the identical `<title>Prospero</title>` (line 5) and `<p class="portfolio-sidebar-merk">Prospero</p>` (line 16) structure as `index.html` — apply the exact same three edits (title text, favicon link insertion, merk-icon wiring) from Step 2 to both files.

`team.html` additionally has a separate `<p class="eyebrow">Prospero</p>` at line 71 (its own page-level eyebrow, distinct from the sidebar). Apply the same icon-wiring transform there too:
```html
      <p class="eyebrow"><svg class="merk-icoon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img" aria-label="KwantIQ"><rect x="4" y="20" width="5" height="8" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="13.5" y="13" width="5" height="15" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="23" y="6" width="5" height="22" rx="1.5" fill="oklch(52% 0.13 155)"/><path d="M6.5 18 L16 11 L25.5 4" fill="none" stroke="oklch(30% 0.11 155)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><circle cx="25.5" cy="4" r="2.75" fill="oklch(30% 0.11 155)"/></svg>KwantIQ</p>
```

`overview.html`'s own eyebrow at line 71 says "Overzicht", not "Prospero" — leave it untouched, it is not a brand-name occurrence.

- [ ] **Step 4: Rename the six auth/marketing pages**

`login.html`, `signup.html`, `signup-gelukt.html`, `wachtwoord-vergeten.html`, `wachtwoord-resetten.html` all share this exact structure — title on line 5, eyebrow on line 17 (`hoe-werkt-dit.html` is handled separately in Step 5 since it has extra body text).

For each of these five files:

Change line 5 from (example shown for `login.html`; each file has its own existing prefix before " — Prospero"):
```html
<title>Inloggen — Prospero</title>
```
to:
```html
<title>Inloggen — KwantIQ</title>
```
(Apply the same `Prospero` → `KwantIQ` substitution to each file's own title text — `Aanmelden — Prospero` in `signup.html`, `Aanmelding gelukt — Prospero` in `signup-gelukt.html`, `Wachtwoord vergeten — Prospero` in `wachtwoord-vergeten.html`, `Nieuw wachtwoord instellen — Prospero` in `wachtwoord-resetten.html`.)

Add the favicon link right after each file's `<title>` line:
```html
<link rel="icon" type="image/svg+xml" href="./assets/kwantiq-icoon.svg">
```

Change each file's line 17 from:
```html
      <p class="eyebrow">Prospero</p>
```
to:
```html
      <p class="eyebrow"><svg class="merk-icoon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img" aria-label="KwantIQ"><rect x="4" y="20" width="5" height="8" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="13.5" y="13" width="5" height="15" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="23" y="6" width="5" height="22" rx="1.5" fill="oklch(52% 0.13 155)"/><path d="M6.5 18 L16 11 L25.5 4" fill="none" stroke="oklch(30% 0.11 155)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><circle cx="25.5" cy="4" r="2.75" fill="oklch(30% 0.11 155)"/></svg>KwantIQ</p>
```

- [ ] **Step 5: Rename `hoe-werkt-dit.html` (title, eyebrow, and two body-text mentions)**

Change line 5:
```html
<title>Hoe dit werkt — Prospero</title>
```
to:
```html
<title>Hoe dit werkt — KwantIQ</title>
```

Add the favicon link right after line 5:
```html
<link rel="icon" type="image/svg+xml" href="./assets/kwantiq-icoon.svg">
```

Change line 17:
```html
      <p class="eyebrow">Prospero</p>
```
to:
```html
      <p class="eyebrow"><svg class="merk-icoon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img" aria-label="KwantIQ"><rect x="4" y="20" width="5" height="8" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="13.5" y="13" width="5" height="15" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="23" y="6" width="5" height="22" rx="1.5" fill="oklch(52% 0.13 155)"/><path d="M6.5 18 L16 11 L25.5 4" fill="none" stroke="oklch(30% 0.11 155)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><circle cx="25.5" cy="4" r="2.75" fill="oklch(30% 0.11 155)"/></svg>KwantIQ</p>
```

Change line 26 from:
```html
    <p>Je hoeft niet zelf in te schatten hoeveel je deze week gaat verkopen of hoeveel je moet bijbestellen. Prospero doet dat voor je, op basis van je eigen verkoopgeschiedenis — automatisch bijgewerkt, zonder dat jij er iets voor hoeft te doen.</p>
```
to:
```html
    <p>Je hoeft niet zelf in te schatten hoeveel je deze week gaat verkopen of hoeveel je moet bijbestellen. KwantIQ doet dat voor je, op basis van je eigen verkoopgeschiedenis — automatisch bijgewerkt, zonder dat jij er iets voor hoeft te doen.</p>
```

Change line 37 from:
```html
    <p>Een voorspelling die beweert exact te weten wat er volgende week gebeurt, is niet eerlijk — de werkelijkheid is nooit zo voorspelbaar. Daarom toont Prospero altijd drie getallen: een realistische ondergrens, de meest waarschijnlijke uitkomst, en een bovengrens voor als het drukker is dan verwacht. Zo kun je plannen voor een rustige én voor een drukke week, in plaats van te vertrouwen op één getal dat toevallig verkeerd kan uitpakken.</p>
```
to:
```html
    <p>Een voorspelling die beweert exact te weten wat er volgende week gebeurt, is niet eerlijk — de werkelijkheid is nooit zo voorspelbaar. Daarom toont KwantIQ altijd drie getallen: een realistische ondergrens, de meest waarschijnlijke uitkomst, en een bovengrens voor als het drukker is dan verwacht. Zo kun je plannen voor een rustige én voor een drukke week, in plaats van te vertrouwen op één getal dat toevallig verkeerd kan uitpakken.</p>
```

- [ ] **Step 6: Rename `sidebar.js`'s footer string**

Change line 168 from:
```javascript
  if (el) el.textContent = `Prospero v${APP_VERSIE} · © ${new Date().getFullYear()} Tessar`;
```
to:
```javascript
  if (el) el.textContent = `KwantIQ v${APP_VERSIE} · © ${new Date().getFullYear()} Tessar`;
```

- [ ] **Step 7: Verify no remaining "Prospero" anywhere in the dashboard directory**

Run: `grep -rn "Prospero" forecasting/dashboard/`
Expected: no output (no matches).

- [ ] **Step 8: Verify every HTML file has exactly one favicon link and one merk-icoon SVG**

Run: `for f in forecasting/dashboard/*.html; do echo "$f: favicon=$(grep -c 'rel="icon"' "$f") icoon=$(grep -c 'merk-icoon' "$f")"; done`
Expected: `index.html`, `team.html`, `overview.html` show `favicon=1 icoon=1` each (`team.html` shows `icoon=2` since it has both sidebar-merk and its own eyebrow); `login.html`, `signup.html`, `signup-gelukt.html`, `wachtwoord-vergeten.html`, `wachtwoord-resetten.html`, `hoe-werkt-dit.html` show `favicon=1 icoon=1` each.

- [ ] **Step 9: Visual verification in claude-in-chrome (light + dark theme)**

Serve the dashboard directory locally (e.g. `python -m http.server 8080` from `forecasting/dashboard/`) and open `http://localhost:8080/login.html` (a page reachable without authentication) in claude-in-chrome. Confirm:
- Browser tab shows the KwantIQ icon as favicon.
- The eyebrow row shows the inline icon mark followed by "KwantIQ" text, vertically aligned, in both light and dark OS theme (toggle via the browser/OS theme, do not attempt to log in).
- "Vraagvoorspelling" subtitle still renders unchanged below it.

Do not attempt to log in to reach `index.html`, `overview.html`, or `team.html` — per the hard rule, no credentials may be entered. For those three pages, verify the same icon+text markup renders correctly by opening the static file directly via `file://` URL instead (no auth required for a `file://` load of the HTML), or by inspecting the rendered DOM structure via `read_page` after loading `login.html`'s equivalent markup pattern, since all three use byte-identical merk-icon HTML to what was just verified.

- [ ] **Step 10: Commit**

```bash
cd forecasting && git add dashboard/
git commit -m "rename: KwantIQ across dashboard frontend, wire logo icon + favicon"
```

---

### Task 3: Deploy to production and verify

**Files:** none (deployment only, no code changes).

**Interfaces:**
- Consumes: the committed state of Tasks 1-2.
- Produces: nothing (terminal task).

- [ ] **Step 1: Sync updated code to the production server**

```bash
rsync -avz --exclude '.git' --exclude '__pycache__' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-demo/
```

- [ ] **Step 2: Rebuild and restart the API container**

```bash
ssh job@157.90.244.24 'cd /home/job/forecasting-demo && docker compose build api && docker compose up -d api'
```

- [ ] **Step 3: Verify the API is healthy and reports the new title**

```bash
curl -s https://kwantiq.tessar.nl/health
curl -s https://kwantiq.tessar.nl/openapi.json | grep -o '"title":"[^"]*"'
```
Expected: `/health` returns `{"status":"ok",...}`; the openapi title shows `"title":"KwantIQ (by Tessar)"`.

- [ ] **Step 4: Verify the frontend is serving the renamed pages**

```bash
curl -s https://kwantiq.tessar.nl/login.html | grep -c "Prospero"
curl -s https://kwantiq.tessar.nl/login.html | grep -o '<title>[^<]*</title>'
curl -s https://kwantiq.tessar.nl/login.html | grep -c 'rel="icon"'
curl -s https://kwantiq.tessar.nl/assets/kwantiq-icoon.svg -o /dev/null -w "%{http_code}\n"
```
Expected: first command outputs `0`; title shows `KwantIQ`; icon-link count is `1`; the SVG asset returns HTTP `200`.

- [ ] **Step 5: Confirm shared Caddy instance still serves the other two tenants**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://vandijkprotocol.tessar.nl/
curl -s -o /dev/null -w "%{http_code}\n" https://n8n.tessar.nl/
```
Expected: both return `200` (or the expected redirect/auth status they normally return) — confirms this deploy did not disturb the shared Caddy container.

- [ ] **Step 6: Update `KNOWN-LIMITATIONS.md` if the "half-finished brand state" note exists**

Run: `grep -n "Prospero" forecasting/KNOWN-LIMITATIONS.md`

If a note exists describing the dashboard still displaying "Prospero" branding while the domain is `kwantiq.tessar.nl`, remove that bullet (the gap is now closed) and commit:
```bash
cd forecasting && git add KNOWN-LIMITATIONS.md
git commit -m "docs: remove resolved Prospero/KwantIQ brand-mismatch known-limitation"
```
If no such note exists, skip this step — nothing to update.
