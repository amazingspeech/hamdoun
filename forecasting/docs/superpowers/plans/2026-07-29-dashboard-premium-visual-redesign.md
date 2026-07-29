# Dashboard Premium Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the dashboard's "AI-generated" look by replacing uniform card-grid treatment with a two-tier hierarchy, cooling the neutral color palette toward an "engineered dashboard" gray, and restricting the emerald accent to genuinely semantic uses only.

**Architecture:** Pure CSS token/rule changes in `dashboard/styles.css`, extending a hairline-row pattern the codebase already uses correctly in `.secundair` to two places that don't yet use it (`.inzicht-kaart`, `.metric`). No JS logic changes, no backend changes, no new HTML elements beyond what's needed to restructure two existing component markups.

**Tech Stack:** Static HTML/CSS/JS dashboard, OKLCH color tokens, no build step — edits apply directly to `dashboard/styles.css` and are served as-is.

## Global Constraints

- The emerald accent hue (`--accent`/`--accent-ink`/`--band`/`--band-line`/`--warn`/`--warn-soft`/`--accent-soft`/`--fout`) is **unchanged** in both light and dark mode — only the neutral scaffolding tokens change.
- `IBM Plex Mono` + `font-variant-numeric: tabular-nums` is mandatory on every number displayed on the page, per the approved design.
- The primary button (`.btn`) switches from an emerald fill to a monochrome ink fill — emerald no longer fills any card, chip, or button background, only genuinely semantic elements (forecast line/band, trend arrow, active nav state, focus rings, links).
- `.factor-chip` and `.premium-badge` (pill-shaped tags) are explicitly out of scope — pills are a distinct, legitimate idiom, not part of this fix.
- `.kaart` (used for onboarding-checklist and login/signup forms) is explicitly out of scope — it's a form/content container, not a data-summary card competing for attention like `.inzicht-kaart`/`.metric` are.
- Brand accent hue, type family pairing (Bricolage Grotesque + IBM Plex Sans/Mono), logo, KwantIQ/Vraagvoorspelling naming, sidebar nav structure, and backend/data are all out of scope for this plan.
- Never enter login credentials in any browser automation step, per the standing hard safety rule — verify via the static-harness technique (Task 1, Step 7) instead.

---

### Task 1: Color tokens, accent-usage rule, primary button, and the verification harness

**Files:**
- Modify: `forecasting/dashboard/styles.css:1-53` (color tokens, both light and both dark-mode blocks)
- Modify: `forecasting/dashboard/styles.css:128-135` (`.btn` primary button)
- Create (verification-only, deleted at the end of the task): `forecasting/dashboard/_harness.html`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the new color tokens (`--paper`, `--paper-raised`, `--ink`, `--ink-soft`, `--ink-faint`, `--line`, `--line-strong` at their new values) that Tasks 2 and 3 build their visual verification against. `--accent`/`--accent-ink`/etc. remain at their existing values — Tasks 2 and 3 do not need to know new values for those, only that they're unchanged.

- [ ] **Step 1: Replace the light-mode neutral tokens**

In `forecasting/dashboard/styles.css`, in the `:root { ... }` block (starts at line 1), replace:

```css
  --paper: oklch(97% 0.012 95);
  --paper-raised: oklch(100% 0 0);
  --ink: oklch(21% 0.025 150);
  --ink-soft: oklch(46% 0.02 150);
  --ink-faint: oklch(60% 0.015 150);
  --line: oklch(89% 0.012 95);
  --line-strong: oklch(80% 0.015 95);
```

with:

```css
  --paper: oklch(98% 0.003 240);
  --paper-raised: oklch(100% 0 0);
  --ink: oklch(18% 0.006 240);
  --ink-soft: oklch(44% 0.006 240);
  --ink-faint: oklch(58% 0.005 240);
  --line: oklch(90% 0.004 240);
  --line-strong: oklch(82% 0.005 240);
```

Do not change `--accent`, `--accent-ink`, `--band`, `--band-line`, `--warn`, `--warn-soft`, `--accent-soft`, `--fout`, or the `--font-*` declarations in this block — leave them exactly as they are.

- [ ] **Step 2: Replace the dark-mode neutral tokens in both dark-mode blocks**

`forecasting/dashboard/styles.css` has two separate dark-mode blocks with identical neutral tokens: `:root[data-theme="dark"] { ... }` and, inside `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { ... } }`. In **both** blocks, replace:

```css
  --paper: oklch(16% 0.02 55);
  --paper-raised: oklch(20% 0.022 55);
  --ink: oklch(93% 0.012 95);
  --ink-soft: oklch(76% 0.015 95);
  --ink-faint: oklch(58% 0.012 95);
  --line: oklch(32% 0.025 55);
  --line-strong: oklch(40% 0.025 55);
```

with:

```css
  --paper: oklch(15% 0.004 240);
  --paper-raised: oklch(19% 0.004 240);
  --ink: oklch(94% 0.004 240);
  --ink-soft: oklch(75% 0.005 240);
  --ink-faint: oklch(56% 0.004 240);
  --line: oklch(30% 0.006 240);
  --line-strong: oklch(38% 0.006 240);
```

Again, leave `--accent`/`--accent-ink`/`--band`/`--band-line`/`--warn`/`--warn-soft`/`--accent-soft`/`--fout` unchanged in both blocks.

- [ ] **Step 3: Verify no stray warm-hue tokens remain**

Run: `grep -n "95);\|150);\|55);" forecasting/dashboard/styles.css | grep -E "\-\-(paper|ink|line)"`
Expected: no output (the old warm-hue neutral tokens — hue 95, 150, or 55 on `--paper`/`--ink`/`--line` variants — are gone; any remaining hue-95/150/55 lines belong to `--accent`/`--band`/`--warn`/etc., which is correct and expected).

- [ ] **Step 4: Change the primary button from an emerald fill to a monochrome ink fill**

In `forecasting/dashboard/styles.css`, replace the `.btn` rule (currently):

```css
.btn {
  font:600 0.9375rem/1.4 var(--font-body); padding:10px 20px; border:none; border-radius:8px;
  background:var(--accent); color:oklch(15% 0.02 155); cursor:pointer;
  transition:transform 0.12s ease, box-shadow 0.12s ease;
}
.btn:hover:not(:disabled) { box-shadow:0 3px 10px oklch(50% 0.15 155 / 0.35); }
```

with:

```css
.btn {
  font:600 0.9375rem/1.4 var(--font-body); padding:10px 20px; border:none; border-radius:8px;
  background:var(--ink); color:var(--paper); cursor:pointer;
  transition:transform 0.12s ease, opacity 0.12s ease;
}
.btn:hover:not(:disabled) { opacity:0.85; }
```

Do not modify `.btn:active:not(:disabled)`, `.btn:disabled`, `.btn.zacht`, or `.btn.zacht:hover:not(:disabled)` — those are unaffected by this change (`.btn.zacht` was already border-only, not accent-filled).

- [ ] **Step 5: Verify the button rule change**

Run: `grep -n "^\.btn {" -A5 forecasting/dashboard/styles.css`
Expected: shows `background:var(--ink); color:var(--paper);` and `.btn:hover:not(:disabled) { opacity:0.85; }` — no `var(--accent)` or `oklch(15% 0.02 155)` in the `.btn` rule itself.

- [ ] **Step 6: Commit**

```bash
cd forecasting && git add dashboard/styles.css
git commit -m "style: cool the neutral palette and make the primary button monochrome

Replaces the warm-cream/warm-dark neutral tokens (hue 95/150/55) with a
true, low-chroma neutral (hue 240) matching the 'engineered dashboard'
gray Linear/Vercel use, and switches the primary button from an emerald
fill to a monochrome ink fill so the accent color is reserved for
genuinely semantic uses (forecast line, trend arrow, active nav, links)
instead of decorative fills. Brand accent/semantic tokens unchanged."
```

- [ ] **Step 7: Build the static verification harness**

No automated frontend tests exist in this project. Verify visually using a standalone HTML file that loads the real `dashboard.js`/`styles.css`/`index.html` markup with `window.fetch` stubbed to return realistic synthetic data — this exercises the actual production rendering code end-to-end without needing to log in (entering credentials is prohibited under all circumstances).

Create `forecasting/dashboard/_harness.html` with this exact content:

```html
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>KwantIQ</title>
<link rel="icon" type="image/svg+xml" href="./assets/kwantiq-icoon.svg">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300..800&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="./styles.css">
<script>
(function () {
  const realFetch = window.fetch.bind(window);
  const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json" } });

  const winkels = [
    { extern_store_id: 1, naam: "Bloemenwinkel De Linde" },
    { extern_store_id: 2, naam: "Buurtsuper Van Dijk" },
    { extern_store_id: 3, naam: "Kaaswinkel Hoorn" },
  ];

  function maakVoorspellingen() {
    const out = [];
    const basis = new Date("2026-08-01");
    for (let i = 0; i < 14; i++) {
      const d = new Date(basis);
      d.setDate(d.getDate() + i);
      const weekend = d.getDay() === 0 || d.getDay() === 6;
      const p50 = Math.round((weekend ? 1450 : 980) + Math.sin(i / 2) * 120);
      out.push({
        datum: d.toISOString().slice(0, 10),
        p10: Math.round(p50 * 0.72),
        p50,
        p90: Math.round(p50 * 1.34),
      });
    }
    return out;
  }

  window.fetch = async (url, opts) => {
    const u = String(url);
    if (u.endsWith("/me")) return json({ email: "eigenaar@bloemenwinkel.nl", rol: "eigenaar", in_proefperiode: false, trial_verloopt_op: null });
    if (u.endsWith("/winkels")) return json(winkels);
    if (u.endsWith("/metrics")) return json({
      rmspe: 0.083, coverage_p10_p90: 0.81, model_versie: "20260726T123220Z",
      n_observaties: 844392, trainingsperiode_eind: "2015-07-31", gevalideerde_horizon_dagen: 42,
      geschiedenis: [{ rmspe: 0.101 }, { rmspe: 0.094 }, { rmspe: 0.083 }],
    });
    if (u.endsWith("/forecast") && opts && opts.method === "POST") {
      const body = JSON.parse(opts.body);
      return json({
        store_id: body.store_id,
        voorspellingen: maakVoorspellingen(),
        vorige_periode_omzet: 13850,
        herbestel_advies: null,
        belangrijkste_factoren: [
          { naam: "Dag van de week", richting: "hoger" },
          { naam: "Seizoen", richting: "lager" },
        ],
      });
    }
    if (u.includes("/organisatie/verkoopdata") || u.includes("/organisatie/instellingen") || u.includes("/voorbeeld/forecast")) {
      return json({ detail: "not found" }, 404);
    }
    return realFetch(url, opts);
  };
})();
</script>
</head>
<body>
<div class="portfolio-shell">
  <nav class="portfolio-sidebar">
    <p class="portfolio-sidebar-merk"><svg class="merk-icoon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" aria-hidden="true" focusable="false"><rect x="4" y="20" width="5" height="8" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="13.5" y="13" width="5" height="15" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="23" y="6" width="5" height="22" rx="1.5" fill="oklch(52% 0.13 155)"/><path d="M6.5 18 L16 11 L25.5 4" fill="none" stroke="oklch(30% 0.11 155)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><circle cx="25.5" cy="4" r="2.75" fill="oklch(30% 0.11 155)"/></svg>KwantIQ</p>
    <p class="portfolio-sidebar-submerk">Vraagvoorspelling</p>
    <div class="portfolio-sidebar-groep">
      <p class="portfolio-sidebar-groepslabel">Voorspellen</p>
      <ul class="portfolio-sidebar-nav">
        <li><a href="./overview.html">Overzicht<span class="trend-pijl" id="trend-pijl" hidden></span></a></li>
        <li><a href="./index.html" class="actief">Voorspelling</a></li>
      </ul>
    </div>
    <div class="portfolio-sidebar-groep">
      <p class="portfolio-sidebar-groepslabel">Beheer</p>
      <ul class="portfolio-sidebar-nav">
        <li><a href="./team.html">Team beheren</a></li>
        <li><a href="./team.html#api-keys-kaart">API-keys</a></li>
        <li><a href="./hoe-werkt-dit.html">Hoe dit werkt</a></li>
      </ul>
    </div>
    <div class="portfolio-sidebar-kpis" id="sidebar-kpis" hidden>
      <div class="portfolio-sidebar-kpi"><span class="waarde" id="sidebar-kpi-winkels">–</span><span class="label">winkels</span></div>
      <div class="portfolio-sidebar-kpi"><span class="waarde" id="sidebar-kpi-nauwkeurigheid">–</span><span class="label">nauwkeurig</span></div>
    </div>
    <p class="portfolio-sidebar-kpis-caveat" id="sidebar-kpis-caveat" hidden></p>
    <div class="portfolio-sidebar-recent" id="sidebar-recent" hidden>
      <p class="portfolio-sidebar-groepslabel">Recent bekeken</p>
      <ul class="portfolio-sidebar-nav" id="sidebar-recent-lijst"></ul>
    </div>
    <div class="portfolio-sidebar-onder">
      <p class="portfolio-sidebar-abonnement" id="sidebar-abonnement"></p>
      <p class="portfolio-sidebar-status"><span class="live-stip" aria-hidden="true"></span>Bijgewerkt zojuist</p>
      <p class="portfolio-sidebar-wie" id="wie-ben-ik">Bezig met laden…</p>
      <a href="#" id="uitloggen">Uitloggen</a>
      <p class="portfolio-sidebar-versie" id="sidebar-versie"></p>
    </div>
  </nav>
  <div class="wrap">
  <div id="onboarding-checklist" class="kaart onboarding-checklist" hidden></div>
  <header class="top">
    <div class="kop">
      <p class="eyebrow"><svg class="merk-icoon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" aria-hidden="true" focusable="false"><rect x="4" y="20" width="5" height="8" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="13.5" y="13" width="5" height="15" rx="1.5" fill="oklch(52% 0.13 155)"/><rect x="23" y="6" width="5" height="22" rx="1.5" fill="oklch(52% 0.13 155)"/><path d="M6.5 18 L16 11 L25.5 4" fill="none" stroke="oklch(30% 0.11 155)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><circle cx="25.5" cy="4" r="2.75" fill="oklch(30% 0.11 155)"/></svg>KwantIQ</p>
      <p class="eyebrow-sub">Vraagvoorspelling</p>
      <h1>Wat gaat deze winkel de komende dagen verkopen?</h1>
      <p class="sub" id="sub-basis">Op basis van historische verkoopdata — met een eerlijke bandbreedte in plaats van één te precies getal.</p>
    </div>
    <p class="account-nav"><span id="wie-ben-ik-mobiel"></span> · <a href="./overview.html">Overzicht</a> · <a href="./team.html">Team beheren</a> · <a href="#" id="uitloggen-mobiel">Uitloggen</a></p>
    <div class="controls">
      <div class="veld"><label for="store">Winkel</label><select id="store"></select></div>
      <div class="veld"><label for="start">Startdatum</label><input type="date" id="start"></div>
      <div class="veld">
        <div class="veld-label-rij"><label for="horizon">Horizon (dagen)</label><details class="info"><summary aria-label="Wat betekent horizon?">?</summary><p class="info-inhoud">Hoeveel dagen vooruit je een voorspelling wilt zien, vanaf de startdatum.</p></details></div>
        <input type="number" id="horizon" value="14" min="1">
      </div>
      <button id="voorspel" class="btn" disabled>Laden…</button>
    </div>
    <div class="promo-vinkjes" id="promo-vinkjes">
      <label class="vinkje"><input type="checkbox" id="promo-vinkje"> Ik heb in deze periode een actie</label>
      <label class="vinkje"><input type="checkbox" id="vakantie-vinkje"> Deze periode valt in een schoolvakantie</label>
      <span class="premium-badge" id="promo-premium-badge" hidden>Premium</span>
    </div>
  </header>
  <div class="leeg" id="leeg">Kies een winkel en klik op "Voorspel" om de verwachte omzet te zien.</div>
  <div id="voorbeeld-voorspelling" class="kaart voorbeeld-kaart" hidden></div>
  <div class="skelet-resultaat" id="skelet-resultaat" hidden>
    <div class="skelet skelet-regel" style="width:45%;"></div>
    <div class="skelet skelet-groot" style="width:35%;"></div>
    <div class="skelet skelet-kaart"></div>
  </div>
  <div id="resultaat">
    <div class="hero">
      <p class="hero-lead" id="hero-lead"></p>
      <p class="waarde" id="hero-waarde">€ 0</p>
      <p class="sub-context" id="hero-sub"></p>
      <p class="periode-vergelijking" id="periode-vergelijking" hidden></p>
    </div>
    <div class="inzichten-paneel" id="inzichten-paneel" hidden></div>
    <div class="factoren" id="factoren" hidden>
      <p class="factoren-titel">Waarom deze voorspelling</p>
      <div class="factoren-lijst" id="factoren-lijst"></div>
    </div>
    <div class="secundair" id="secundair"></div>
    <p class="aanbeveling" id="aanbeveling"></p>
    <div id="chart-container">
      <p class="chart-titel" id="chart-titel"></p>
      <svg id="chart" width="920" height="360"></svg>
      <div class="legenda">
        <span><i class="zwatch lijn"></i> Verwachte omzet<details class="info"><summary aria-label="Wat is de verwachte omzet?">?</summary><p class="info-inhoud">De meest waarschijnlijke waarde per dag — geen garantie, wel de beste inschatting.</p></details></span>
        <span><i class="zwatch band"></i> Bandbreedte<details class="info"><summary aria-label="Wat is de bandbreedte?">?</summary><p class="info-inhoud">De omzet valt hier meestal binnen — een ruime, eerlijke marge in plaats van één te precies getal.</p></details></span>
      </div>
      <div class="export-knoppen" id="export-knoppen" hidden>
        <button type="button" class="btn zacht" id="export-csv">Download als CSV</button>
        <button type="button" class="btn zacht" id="export-png">Download grafiek als PNG</button>
        <span class="premium-badge" id="export-premium-badge" hidden>Premium</span>
      </div>
    </div>
    <p class="kanttekening" id="kanttekening"></p>
  </div>
  <p class="fout" id="fout" hidden></p>
  <details class="uitklap scenario-vergelijking" id="scenario-vergelijking">
    <summary>Vergelijk twee scenario's<span class="premium-badge" id="scenario-premium-badge" hidden>Premium</span></summary>
    <div id="scenario-invoer">
      <p class="sub" style="margin:0 0 14px;">Zelfde winkel, startdatum en horizon als hierboven — kies per scenario of er een actie of schoolvakantie is, en vergelijk de uitkomst direct naast elkaar.</p>
      <div class="scenario-kolommen">
        <div class="scenario-kolom"><p class="scenario-kolom-titel">Scenario A</p><label class="vinkje"><input type="checkbox" id="scenario-a-promo"> Actie</label><label class="vinkje"><input type="checkbox" id="scenario-a-vakantie"> Schoolvakantie</label></div>
        <div class="scenario-kolom"><p class="scenario-kolom-titel">Scenario B</p><label class="vinkje"><input type="checkbox" id="scenario-b-promo"> Actie</label><label class="vinkje"><input type="checkbox" id="scenario-b-vakantie"> Schoolvakantie</label></div>
      </div>
      <button type="button" class="btn" id="vergelijk-knop" style="margin-top:14px;">Vergelijk</button>
      <p class="fout" id="scenario-fout" hidden></p>
    </div>
    <div class="scenario-resultaat" id="scenario-resultaat" hidden></div>
  </details>
  <details class="uitklap model-info">
    <summary>Over dit model</summary>
    <div class="metrics" id="metrics"></div>
    <div class="nauwkeurigheid-trend" id="nauwkeurigheid-trend" hidden></div>
  </details>
  <p class="palet-hint">Snel naar een andere winkel: <kbd>Ctrl</kbd>+<kbd>K</kbd> (<kbd>⌘</kbd>+<kbd>K</kbd> op Mac)</p>
  </div>
</div>
<div class="palet-overlay" id="palet-overlay" hidden>
  <div class="palet" role="dialog" aria-modal="true" aria-label="Snel naar winkel">
    <input type="text" id="palet-zoek" placeholder="Typ een winkelnaam of -nummer…" autocomplete="off">
    <div class="palet-resultaten" id="palet-resultaten"></div>
  </div>
</div>
<script src="./config.js"></script>
<script src="./sidebar.js"></script>
<script src="./onboarding.js"></script>
<script src="./dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 8: Serve the dashboard directory locally**

Run: `cd forecasting/dashboard && python3 -m http.server 8099 &`
Expected: server starts; `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8099/_harness.html` returns `200`.

- [ ] **Step 9: Visually verify in claude-in-chrome — light and dark, desktop width**

Use claude-in-chrome to navigate a **new tab** (creating a fresh tab, not reusing one, ensures `resize_window` reliably applies before the page's `DOMContentLoaded` fires) to `http://localhost:8099/_harness.html`. Resize the window to at least 1280×900 **before** navigating (some environments only apply a resize reliably on a freshly created tab). After the page loads, run this JavaScript to select the first store and trigger a forecast render:

```javascript
await new Promise(r => setTimeout(r, 800));
document.getElementById('voorspel').click();
await new Promise(r => setTimeout(r, 900));
document.getElementById('resultaat').classList.contains('zichtbaar')
```

Expected: returns `true`. Take a screenshot of the full page (scroll as needed to see the hero, the Inzichten panel, the secondary stats, and the chart). Confirm: page background and card/border colors read as a cool neutral gray, not the previous warm cream; the "Voorspel" button is a solid dark/ink-colored fill with light text, not green. Then run `document.documentElement.setAttribute('data-theme', 'dark')` and re-screenshot — confirm the dark background is a cool near-black, not the previous warm near-black, and the button is a solid light fill with dark text.

This confirms Task 1's token and button changes render correctly. Tasks 2 and 3 will reuse this same harness (regenerate `_harness.html` with the same content if it was already deleted by a prior task's Step 10 below) rather than re-describing the recipe.

- [ ] **Step 10: Clean up the harness and local server**

```bash
rm forecasting/dashboard/_harness.html
pkill -f "http.server 8099" || true
```

Confirm no uncommitted changes remain: `git status --short forecasting/dashboard/` should show nothing (the harness file was never committed).

---

### Task 2: Card hierarchy — hairline rows for `.inzicht-kaart` and `.metric`, chart-container and portfolio-table radius tightening, hero number scale

**Files:**
- Modify: `forecasting/dashboard/styles.css:168-180` (`.secundair` reference pattern, `.inzicht-kaart` conversion)
- Modify: `forecasting/dashboard/styles.css:245-246` (`.metrics`/`.metric` conversion)
- Modify: `forecasting/dashboard/styles.css:182` (`#chart-container` radius)
- Modify: `forecasting/dashboard/styles.css:147-153` (`.hero .waarde` scale)
- Modify: `forecasting/dashboard/styles.css:308` (`.portfolio-tabel-wrap` radius, for visual consistency with the new chart-container radius)

**Interfaces:**
- Consumes: the color tokens from Task 1 (`--line`, `--paper-raised`, `--ink`, `--ink-soft`, `--ink-faint`) — already in place, no new values needed.
- Produces: nothing consumed by Task 3.

- [ ] **Step 1: Convert `.inzicht-kaart` to the hairline-row pattern**

`.secundair` (`forecasting/dashboard/styles.css:168`) already renders its two stat items as a single flex row with one `border-top`, no per-item card. `.inzicht-kaart` currently renders each item as its own bordered box. Read the current rules first:

```css
.inzichten-paneel { display:flex; gap:14px; flex-wrap:wrap; margin:20px 0 0; }
.inzicht-kaart {
  flex:1 1 200px; padding:16px; background:var(--paper-raised); border:1px solid var(--line);
  border-radius:12px; display:flex; flex-direction:column; gap:4px;
}
```

Replace with:

```css
.inzichten-paneel {
  display:flex; gap:0; flex-wrap:wrap; margin:20px 0 0;
  padding-top:20px; border-top:1px solid var(--line);
}
.inzicht-kaart {
  flex:1 1 200px; padding:0 20px; display:flex; flex-direction:column; gap:4px;
  border-left:1px solid var(--line);
}
.inzicht-kaart:first-child { padding-left:0; border-left:none; }
```

This mirrors `.secundair`'s existing top-rule-plus-row structure exactly, with a `border-left` divider between items (since `.inzicht-kaart` items sit side by side, unlike `.secundair`'s items which already had implicit spacing via `gap`). Do not modify `.inzicht-titel`, `.inzicht-waarde`, or `.inzicht-toelichting` — those typography rules are unaffected by the container change.

- [ ] **Step 2: Convert `.metrics`/`.metric` to the same pattern**

Current:

```css
.metrics { display:flex; gap:16px; margin:16px 0 0; flex-wrap:wrap; }
.metric { flex:1 1 220px; border:1px solid var(--line); border-radius:10px; padding:14px 16px; background:var(--paper-raised); }
```

Replace with:

```css
.metrics {
  display:flex; gap:0; margin:16px 0 0; flex-wrap:wrap;
  padding-top:16px; border-top:1px solid var(--line);
}
.metric { flex:1 1 220px; padding:0 16px; border-left:1px solid var(--line); }
.metric:first-child { padding-left:0; border-left:none; }
```

- [ ] **Step 3: Tighten `#chart-container`'s border radius**

Find the current rule (`forecasting/dashboard/styles.css:182`):

```css
#chart-container { position:relative; border:1px solid var(--line); border-radius:14px; background:var(--paper-raised); padding:clamp(14px,4vw,24px); overflow-x:auto; }
```

Change `border-radius:14px` to `border-radius:8px`. The rest of the rule is unchanged.

- [ ] **Step 4: Tighten `.portfolio-tabel-wrap`'s border radius to match**

Find (`forecasting/dashboard/styles.css:308`):

```css
.portfolio-tabel-wrap { overflow-x:auto; margin-top:20px; border:1px solid var(--line); border-radius:12px; }
```

Change `border-radius:12px` to `border-radius:8px`. This table wrapper already uses a real `<table>` with row-based `border-bottom` dividers (`forecasting/dashboard/styles.css:320-321`) — it does not need the hairline-row conversion from Steps 1-2, only this radius tightening for visual consistency with the chart container.

- [ ] **Step 5: Tighten the hero number's scale and switch it to the mandatory monospace numeral treatment**

Find (`forecasting/dashboard/styles.css:149-152`):

```css
.hero .waarde {
  font:600 clamp(2.75rem,9vw,4.5rem)/1 var(--font-display); letter-spacing:-0.02em;
  color:var(--ink); font-variant-numeric:tabular-nums; margin:0;
}
```

Replace with:

```css
.hero .waarde {
  font:600 clamp(2.25rem,7vw,3.5rem)/1 var(--font-mono); letter-spacing:-0.01em;
  color:var(--ink); font-variant-numeric:tabular-nums; margin:0;
}
```

Three changes: the clamp scale tightens per the redesign's "smaller hero, less landing-page-hero" direction; `var(--font-display)` (Bricolage Grotesque) becomes `var(--font-mono)` (IBM Plex Mono), per the spec's explicit "IBM Plex Mono + tabular-nums becomes mandatory on every number ... extends to the hero `.waarde` itself"; `letter-spacing` loosens slightly from `-0.02em` to `-0.01em` since tight negative tracking suits a bold display face but reads cramped on a monospace one. If visual verification in Step 8 below shows the monospace hero number reading as flat or "spreadsheet-like" rather than confident, that is worth flagging as a finding during review rather than silently reverting — this is the one deliberate risk called out in the approved design.

- [ ] **Step 6: Verify the CSS changes are syntactically valid**

Run: `python3 -c "import re; content = open('forecasting/dashboard/styles.css').read(); opens = content.count('{'); closes = content.count('}'); print('OK' if opens == closes else f'MISMATCH: {opens} opens vs {closes} closes')"`
Expected: `OK` (a quick brace-balance sanity check; this project has no CSS linter configured).

- [ ] **Step 7: Commit**

```bash
cd forecasting && git add dashboard/styles.css
git commit -m "style: replace individual card treatment with hairline rows

Extends the hairline-row pattern .secundair already used correctly to
.inzicht-kaart and .metric, so distinct concepts (Betrouwbaarheid,
Sterkste patroon, model metrics) stop each rendering as an identical
bordered white box — the actual structural cause of the dashboard
reading as templated. Also tightens chart-container and
portfolio-tabel-wrap border-radius from 12-14px to 8px, and the hero
number's clamp scale down slightly, both per the approved redesign
spec's 'tighter scale, hierarchy through restraint' direction."
```

- [ ] **Step 8: Recreate the harness and visually verify**

Recreate `forecasting/dashboard/_harness.html` with the exact same content given in Task 1 Step 7 (Task 1 deleted it at the end of its own verification). Repeat Task 1 Step 8 (serve locally) and Step 9's browser steps (new tab, resize to ≥1280px width, navigate, select store, click "Voorspel", screenshot in both light and dark).

Confirm: the Betrouwbaarheid/Sterkste patroon pair now renders as one row with a top rule and a single vertical divider between the two items, not two separate white boxes. Confirm the "Over dit model" metrics (expand the `<details>` labeled "Over dit model" via `document.querySelector('.model-info').open = true` before screenshotting) show the same row-with-divider treatment. Confirm the chart container and (if visiting `overview.html` in the same harness pattern) the portfolio table have visibly smaller corner rounding than before. Confirm the hero €-number is still clearly the largest, most prominent element on the page despite the smaller clamp values.

Clean up: `rm forecasting/dashboard/_harness.html && pkill -f "http.server 8099" || true`.

---

### Task 3: Mandatory tabular-nums on remaining numbers, portfolio-table monospace fix, deploy, and production verification

**Files:**
- Modify: `forecasting/dashboard/styles.css:204` (`.as-label`, chart axis labels)
- Modify: `forecasting/dashboard/styles.css:539-542` (`.portfolio-tabel td.cijfer`, currently desktop-only monospace)

**Interfaces:**
- Consumes: nothing new from Tasks 1-2 beyond the already-committed CSS state.
- Produces: nothing (terminal task — ends with production deploy).

- [ ] **Step 1: Add tabular-nums to the chart's axis labels**

Find (`forecasting/dashboard/styles.css:204`):

```css
.as-label { font:400 0.6875rem var(--font-mono); fill:var(--ink-faint); }
```

This already uses `var(--font-mono)` (IBM Plex Mono) — only `font-variant-numeric` is missing. Change to:

```css
.as-label { font:400 0.6875rem var(--font-mono); font-variant-numeric:tabular-nums; fill:var(--ink-faint); }
```

- [ ] **Step 2: Make the portfolio table's monospace numeral column unconditional, not desktop-only**

Find, inside the `@media (min-width: 961px) { ... }` block (`forecasting/dashboard/styles.css:539-542`):

```css
  .portfolio-tabel-wrap { margin-top:16px; }
  .portfolio-tabel th, .portfolio-tabel td { padding:9px 16px; font-size:0.875rem; }
  .portfolio-tabel td.cijfer { font-family:var(--font-mono); }
  .portfolio-tabel tbody tr:hover { background:var(--paper); }
```

Remove the `.portfolio-tabel td.cijfer { font-family:var(--font-mono); }` line from inside this media query (leave the other three lines in the media query untouched — they are legitimately desktop-only spacing/hover rules). Instead, add it as a new **unconditional** rule near the existing `.portfolio-tabel td.cijfer, .portfolio-tabel th.cijfer { text-align:right; font-variant-numeric:tabular-nums; }` rule at `forecasting/dashboard/styles.css:322`, changing that line to:

```css
.portfolio-tabel td.cijfer, .portfolio-tabel th.cijfer { text-align:right; font-variant-numeric:tabular-nums; font-family:var(--font-mono); }
```

This makes the numeral column monospace at every viewport width, not only ≥961px, consistent with the "mandatory on every number" rule. The header cells (`th.cijfer`) also gain the monospace treatment for visual consistency with their column's data cells.

- [ ] **Step 3: Verify both changes**

Run: `grep -n "as-label\|td.cijfer" forecasting/dashboard/styles.css`
Expected: the `.as-label` line shows both `var(--font-mono)` and `font-variant-numeric:tabular-nums`; the line-322 `.portfolio-tabel td.cijfer, .portfolio-tabel th.cijfer` rule shows all three of `text-align:right`, `tabular-nums`, and `var(--font-mono)`; and the media-query block (now around line 538-541) no longer contains a separate `.portfolio-tabel td.cijfer { font-family:var(--font-mono); }` line.

- [ ] **Step 4: Commit**

```bash
cd forecasting && git add dashboard/styles.css
git commit -m "style: make tabular monospace numerals unconditional and complete

Chart axis labels gain font-variant-numeric:tabular-nums (they already
had the mono font-family). Portfolio table's numeral column monospace
treatment moves out of the >=961px media query so it applies at every
viewport width, and now also covers the column header, per the
approved redesign spec's 'mandatory on every number' rule."
```

- [ ] **Step 5: Final visual verification across both pages**

Recreate `forecasting/dashboard/_harness.html` (same content as Task 1 Step 7) and serve it (Task 1 Step 8). In claude-in-chrome, verify the forecast page's chart axis labels and the flow end-to-end once more (new tab, resize ≥1280px, navigate, select store, click "Voorspel", screenshot light and dark) to confirm Tasks 1-3 together look correct as a whole, not just individually. Then clean up (`rm forecasting/dashboard/_harness.html && pkill -f "http.server 8099" || true`).

For `overview.html`'s portfolio table specifically: since it requires an authenticated session and this project's hard rule prohibits entering credentials anywhere, verify the table's monospace/radius changes via code inspection instead — re-read the final `forecasting/dashboard/styles.css` rules for `.portfolio-tabel-wrap` and `.portfolio-tabel td.cijfer, .portfolio-tabel th.cijfer` and confirm they match Task 2 Step 4 and Task 3 Step 2's intended end state exactly. This is sufficient because these are pure CSS selector/property changes with no JS logic involved — the same class of change already visually verified working correctly on the forecast page's structurally identical patterns.

- [ ] **Step 6: Deploy to production**

Sync the code (from whichever checkout has Tasks 1-3's commits) to the production server, excluding live data/secrets:

```bash
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '.venv' \
  --exclude '.env' --exclude 'api_keys.json' --exclude 'audit.log' \
  --exclude 'tenants.db' --exclude 'tenants.db.bak-*' --exclude 'data' \
  --exclude 'models' --exclude 'config.js' \
  <path-to-checkout>/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-demo/
```

Rebuild and restart the container that Caddy actually routes to (`deploy-api-1`, built from `deploy/docker-compose.yml`, not the top-level compose file):

```bash
ssh job@157.90.244.24 'cd /home/job/forecasting-demo/deploy && docker compose build api && docker compose up -d api'
```

- [ ] **Step 7: Verify production health and the deployed CSS**

```bash
curl -s https://kwantiq.tessar.nl/health
curl -s https://kwantiq.tessar.nl/styles.css | grep -c "oklch(98% 0.003 240)"
curl -s https://kwantiq.tessar.nl/styles.css | grep -c "background:var(--ink); color:var(--paper);"
```

Expected: `/health` returns `{"status":"ok",...}`; both grep counts return `1` or higher (confirms the new neutral token and the monochrome button rule are actually live, not just committed).

- [ ] **Step 8: Confirm the shared Caddy tenants are unaffected**

```bash
curl -s -o /dev/null -w "vandijkprotocol: %{http_code}\n" https://vandijkprotocol.tessar.nl/
curl -s -o /dev/null -w "n8n: %{http_code}\n" https://n8n.tessar.nl/
```

Expected: both return their normal healthy status codes (`vandijkprotocol` typically `302`, `n8n` typically `200`), confirming this deploy didn't disturb the shared Caddy container serving other Tessar products.
