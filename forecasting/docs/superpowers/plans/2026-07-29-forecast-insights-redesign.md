# KwantIQ Logo + Forecast Insights Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a standalone KwantIQ logo asset, modernize the forecast-page chart (smooth curves, gradient fill, hover tooltips), and add a new "Inzichten" panel with three derived-statistic cards computed entirely from data the app already fetches.

**Architecture:** Three independent pieces landing on top of the existing `dashboard/index.html`/`dashboard.js` forecast page: a self-contained SVG logo (not wired into any live page), an in-place upgrade of the existing SVG chart-drawing code, and a new insights panel that reads (a) the just-returned `/forecast` response and (b) a small `localStorage` cache that `overview.js`/`sidebar.js` now write on every portfolio-page visit — no new backend endpoints, no new network calls from the forecast page.

**Tech Stack:** Vanilla JS/HTML/CSS (no build step, no framework), SVG (hand-authored + programmatically generated), existing FastAPI backend (untouched by this plan).

## Global Constraints

- No backend changes anywhere in this plan — `serving/forecast.py::belangrijkste_factoren()` and the `/forecast`/`/portfolio` endpoints stay exactly as they are.
- No new network requests from `dashboard/index.html` — the third insight card reads a `localStorage` cache written by `overview.js`, never triggers its own `/portfolio` call (that endpoint is deliberately expensive to compute across a full portfolio — see the existing comment in `serving/app.py`'s `/portfolio` handler).
- Betrouwbaarheid thresholds are exact: **&lt;15%** relative band width = "Stabiel", **15–30%** = "Gemiddeld", **&gt;30%** = "Wisselvallig".
- The KwantIQ logo is a standalone asset only — it must not be referenced from any live HTML page in this plan (the actual product rename is a separate, later task).
- No automated frontend tests exist in this project by established convention — every frontend task ends with a claude-in-chrome browser-verification step in both light and dark theme, not a test file.
- The `/portfolio` endpoint's KPI is computed only over the current page of stores (`data.winkels.length`), which can be smaller than `data.totaal_winkels` under pagination — any cached count must be `data.winkels.length`, never `data.totaal_winkels`.
- `/portfolio` always requests a fixed 7-day horizon (`overview.js`'s `HORIZON_DAGEN = 7`), independent of whatever horizon the user has selected on the forecast page (default 14, user-adjustable) — any comparison between the two must normalize to a per-day figure, never compare raw period totals directly.

---

## File Structure

- `dashboard/assets/kwantiq-icoon.svg` (create) — icon-only mark, works from favicon scale up.
- `dashboard/assets/kwantiq-logo.svg` (create) — icon + wordmark lockup for larger display use.
- `dashboard/dashboard.js` (modify) — smooth-curve chart rendering, gradient fill, hover tooltips; new insights-panel functions.
- `dashboard/sidebar.js` (modify) — `toonSidebarKpis()` now also caches portfolio omzet/count to `localStorage`; new reader function.
- `dashboard/styles.css` (modify) — new classes for the insights panel, the chart gradient/tooltip, and the smooth band path.
- `dashboard/index.html` (modify) — new `<div id="inzichten-paneel">` placement.

---

### Task 1: KwantIQ logo (standalone asset)

**Files:**
- Create: `dashboard/assets/kwantiq-icoon.svg`
- Create: `dashboard/assets/kwantiq-logo.svg`

**Interfaces:** none — these files are not referenced from any other file in this plan.

- [ ] **Step 1: Create the icon-only mark**

Create `dashboard/assets/kwantiq-icoon.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32" role="img" aria-label="KwantIQ">
  <rect x="4" y="20" width="5" height="8" rx="1.5" fill="oklch(52% 0.13 155)"/>
  <rect x="13.5" y="13" width="5" height="15" rx="1.5" fill="oklch(52% 0.13 155)"/>
  <rect x="23" y="6" width="5" height="22" rx="1.5" fill="oklch(52% 0.13 155)"/>
  <path d="M6.5 18 L16 11 L25.5 4" fill="none" stroke="oklch(30% 0.11 155)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="25.5" cy="4" r="2.75" fill="oklch(30% 0.11 155)"/>
</svg>
```

Three ascending bars (the emerald/jade accent already used across the app, `oklch(52% 0.13 155)`, matching `dashboard/styles.css`'s light-mode `--accent`) reading as a growth/forecast motif, with a rising line and endpoint dot (the darker `--accent-ink` tone, `oklch(30% 0.11 155)`) echoing the forecast-line-with-endpoint-emphasis pattern already used in the real chart (`dashboard.js::tekenGrafiek()`'s `.stip` circle on the final data point).

- [ ] **Step 2: Create the icon+wordmark lockup**

Create `dashboard/assets/kwantiq-logo.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 32" width="200" height="32" role="img" aria-label="KwantIQ">
  <rect x="4" y="20" width="5" height="8" rx="1.5" fill="oklch(52% 0.13 155)"/>
  <rect x="13.5" y="13" width="5" height="15" rx="1.5" fill="oklch(52% 0.13 155)"/>
  <rect x="23" y="6" width="5" height="22" rx="1.5" fill="oklch(52% 0.13 155)"/>
  <path d="M6.5 18 L16 11 L25.5 4" fill="none" stroke="oklch(30% 0.11 155)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="25.5" cy="4" r="2.75" fill="oklch(30% 0.11 155)"/>
  <text x="40" y="23" font-family="'Bricolage Grotesque', -apple-system, sans-serif" font-size="20" font-weight="700" fill="oklch(21% 0.025 150)">KwantIQ</text>
</svg>
```

Reuses the same mark from Step 1, positioned left of a wordmark set in the same display typeface used across the rest of the app (`--font-display` in `dashboard/styles.css`: `'Bricolage Grotesque', -apple-system, sans-serif`), in the app's ink/text color (`oklch(21% 0.025 150)`, matching `styles.css`'s light-mode `--ink`). No slogan, no subtitle — matches the explicit "geen slogan" instruction.

- [ ] **Step 3: Verify both render correctly**

Using claude-in-chrome, navigate directly to `file:///Users/hamdeco/development/hamdoun/forecasting/dashboard/assets/kwantiq-icoon.svg` and `file:///Users/hamdeco/development/hamdoun/forecasting/dashboard/assets/kwantiq-logo.svg` and confirm both render as expected: three ascending emerald bars, a dark rising line ending in a dot, and — for the lockup — legible "KwantIQ" text next to the mark. Confirm neither file references any external resource that could fail to load (both should render identically with no network access, since Bricolage Grotesque falls back to `-apple-system, sans-serif` when not loaded outside the main app's `<link>`-loaded context — this is expected and acceptable for a standalone asset file).

- [ ] **Step 4: Commit**

```bash
git add dashboard/assets/kwantiq-icoon.svg dashboard/assets/kwantiq-logo.svg
git commit -m "feat: add standalone KwantIQ logo assets"
```

---

### Task 2: Chart modernization — smooth curves, gradient fill, hover tooltips

**Files:**
- Modify: `dashboard/dashboard.js:192-275` (the existing `tekenGrafiek()` function)
- Modify: `dashboard/styles.css` (chart-related classes, currently around lines 163-188)

**Interfaces:**
- Produces: `gladPadSegment(punten, startCommando)`, `lijnPadData(voorspellingen, x, y)`, `bandPadData(voorspellingen, x, y)`, `initGrafiekTooltip(svg, voorspellingen, x, y)` — new helper functions in `dashboard.js`, called from the rewritten `tekenGrafiek()`. Not consumed by any other task.

- [ ] **Step 1: Add the Catmull-Rom smoothing helper**

In `dashboard/dashboard.js`, add this function directly above `tekenGrafiek` (currently at line 192):

```javascript
// Zet een reeks punten om in een vloeiend gebogen SVG-pad-string via
// Catmull-Rom-naar-Bezier-conversie, in plaats van rechte lijnsegmenten
// tussen elk punt. startCommando is "M" voor het eerste subpad in een
// grotere path, of "L" om aan te sluiten op een al lopend pad (zie
// bandPadData hieronder, die twee van deze segmenten aan elkaar plakt).
function gladPadSegment(punten, startCommando) {
  if (punten.length === 0) return "";
  let d = `${startCommando} ${punten[0][0]},${punten[0][1]}`;
  if (punten.length < 3) {
    for (let i = 1; i < punten.length; i++) d += ` L ${punten[i][0]},${punten[i][1]}`;
    return d;
  }
  for (let i = 0; i < punten.length - 1; i++) {
    const p0 = punten[i === 0 ? i : i - 1];
    const p1 = punten[i];
    const p2 = punten[i + 1];
    const p3 = punten[i + 2 < punten.length ? i + 2 : i + 1];
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2[0]},${p2[1]}`;
  }
  return d;
}

function lijnPadData(voorspellingen, x, y) {
  return gladPadSegment(voorspellingen.map((v, i) => [x(i), y(v.p50)]), "M");
}

// De band als één gesloten, vloeiend gebogen pad: de bovenrand (p90, van
// links naar rechts) gevolgd door de onderrand (p10, van rechts naar
// links) — zelfde punt-volgorde als de bestaande polygon-aanpak, nu als
// twee aan elkaar geplakte gladde segmenten in plaats van rechte
// polygon-zijden.
function bandPadData(voorspellingen, x, y) {
  const bovenPunten = voorspellingen.map((v, i) => [x(i), y(v.p90)]);
  const onderPunten = [...voorspellingen].reverse().map((v, i) => [x(voorspellingen.length - 1 - i), y(v.p10)]);
  return `${gladPadSegment(bovenPunten, "M")} ${gladPadSegment(onderPunten, "L")} Z`;
}
```

- [ ] **Step 2: Add the gradient-definition helper**

Add this function directly below the functions from Step 1:

```javascript
// Maakt (of hergebruikt) een <defs>-blok met de gradient-definitie voor de
// bandvulling — een subtiele overgang van het accentkleur naar transparant,
// in plaats van de bestaande vlakke --band-kleur.
function maakBandGradient(svg) {
  let defs = svg.querySelector("defs");
  if (!defs) {
    defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    svg.insertBefore(defs, svg.firstChild);
  }
  defs.innerHTML =
    '<linearGradient id="band-gradient" x1="0" y1="0" x2="0" y2="1">' +
    '<stop offset="0%" stop-color="var(--accent)" stop-opacity="0.35"/>' +
    '<stop offset="100%" stop-color="var(--accent)" stop-opacity="0.05"/>' +
    "</linearGradient>";
}
```

- [ ] **Step 3: Add the hover-tooltip helper**

Add this function directly below the function from Step 2:

```javascript
// Onzichtbare, ruimere hit-cirkels bovenop elk datapunt (straal 10, i.p.v.
// de zichtbare 4px-eindpunt-stip) — een muis hoeft niet pixel-precies op de
// dunne lijn te staan om de tooltip te zien. De tooltip zelf is een
// gewoon HTML-element (geen SVG), gepositioneerd via de al berekende
// x(i)/y(v.p50)-coördinaten van de plot.
function initGrafiekTooltip(svg, voorspellingen, x, y) {
  let tooltip = document.getElementById("grafiek-tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.id = "grafiek-tooltip";
    tooltip.className = "grafiek-tooltip";
    tooltip.hidden = true;
    document.getElementById("chart-container").appendChild(tooltip);
  }
  voorspellingen.forEach((v, i) => {
    const hitCirkel = maakSVGEl("circle", { class: "hit-stip", cx: x(i), cy: y(v.p50), r: 10 });
    hitCirkel.addEventListener("mouseenter", () => {
      tooltip.innerHTML =
        `<strong>${formatDatumKort(v.datum)}</strong><br>` +
        `${euro.format(Math.round(v.p50))} (${euro.format(Math.round(v.p10))}–${euro.format(Math.round(v.p90))})`;
      tooltip.style.left = `${x(i)}px`;
      tooltip.style.top = `${y(v.p50) - 12}px`;
      tooltip.hidden = false;
    });
    hitCirkel.addEventListener("mouseleave", () => { tooltip.hidden = true; });
    svg.appendChild(hitCirkel);
  });
}
```

- [ ] **Step 4: Rewrite `tekenGrafiek()` to use the new helpers**

In `dashboard/dashboard.js`, replace the existing band/line-drawing portion of `tekenGrafiek()` (currently lines 205-215):

```javascript
  const bandPunten = [
    ...voorspellingen.map((v, i) => `${x(i)},${y(v.p90)}`),
    ...[...voorspellingen].reverse().map((v, i) => `${x(voorspellingen.length - 1 - i)},${y(v.p10)}`),
  ].join(" ");
  const lijnPunten = voorspellingen.map((v, i) => `${x(i)},${y(v.p50)}`).join(" ");

  svg.replaceChildren();

  svg.appendChild(maakSVGEl("polygon", { class: "band", points: bandPunten }));
  const lijnEl = maakSVGEl("polyline", { class: "lijn", points: lijnPunten });
  svg.appendChild(lijnEl);
```

with:

```javascript
  svg.replaceChildren();
  maakBandGradient(svg);

  svg.appendChild(maakSVGEl("path", { class: "band", d: bandPadData(voorspellingen, x, y) }));
  const lijnEl = maakSVGEl("path", { class: "lijn", d: lijnPadData(voorspellingen, x, y) });
  svg.appendChild(lijnEl);
```

**Important:** deliberately no inline `fill` attribute on the `band` path — the existing `.band` CSS rule (`dashboard/styles.css`, currently `fill:var(--band);`) has higher specificity than an SVG presentation attribute and would silently override it. Step 6 below updates that CSS rule itself to point at the new gradient, keeping the fill's source of truth in one place (consistent with how `.lijn`'s stroke color already works purely through CSS, never inline).

Then, at the end of `tekenGrafiek()` (after the existing endpoint-emphasis `.stip` circle, currently around line 256), add:

```javascript
  initGrafiekTooltip(svg, voorspellingen, x, y);
```

- [ ] **Step 5: Confirm the animation code still works with the path element**

`tekenGrafiek()`'s existing self-drawing animation (currently lines 258-274) calls `lijnEl.getTotalLength()` and sets `stroke-dasharray`/`stroke-dashoffset` — these SVG APIs work identically on `<path>` as they did on `<polyline>`, so no change is needed there. Re-read the current state of `tekenGrafiek()` after Step 4's edit to confirm the animation block still references `lijnEl` correctly (it should, since the variable name is unchanged) — no separate edit required, this step is a verification-only check.

- [ ] **Step 6: Point the `.band` fill at the new gradient, and add CSS for the tooltip and hit-circles**

In `dashboard/styles.css`, find the existing band rule (currently line 181):

```css
.band { fill:var(--band); }
```

Replace with:

```css
.band { fill:url(#band-gradient); }
```

Then add, near the existing chart-related rules (around line 185, after `.as-label`):

```css
.hit-stip { fill:transparent; cursor:pointer; }
.grafiek-tooltip {
  position:absolute; transform:translate(-50%,-100%); pointer-events:none;
  background:var(--ink); color:var(--paper); font:400 0.75rem/1.4 var(--font-body);
  padding:6px 10px; border-radius:6px; white-space:nowrap; z-index:5;
  box-shadow:0 4px 12px oklch(0% 0 0 / 0.25);
}
```

`#chart-container` (line 163) already has no `position` set — add `position:relative;` to its existing rule so the absolutely-positioned tooltip anchors correctly within it:

Find:
```css
#chart-container { border:1px solid var(--line); border-radius:14px; background:var(--paper-raised); padding:clamp(14px,4vw,24px); overflow-x:auto; }
```

Replace with:
```css
#chart-container { position:relative; border:1px solid var(--line); border-radius:14px; background:var(--paper-raised); padding:clamp(14px,4vw,24px); overflow-x:auto; }
```

- [ ] **Step 7: Deploy and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/dashboard.js \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/styles.css \
    job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, log in and load `https://prospero.tessar.nl/index.html`, pick a store, click "Voorspel". Confirm: the p50 line renders as a smooth curve (not straight segments between days), the band has a visible top-to-bottom gradient fade instead of a flat fill, hovering near any point on the line shows a tooltip with that day's date and p10/p50/p90 values, and the animation (line "drawing itself" in) still plays. Repeat in dark mode (toggle via the app's theme mechanism or `prefers-color-scheme` emulation) and confirm the gradient and tooltip remain legible.

- [ ] **Step 8: Commit**

```bash
git add dashboard/dashboard.js dashboard/styles.css
git commit -m "feat: modernize forecast chart with smooth curves, gradient fill, hover tooltips"
```

---

### Task 3: Portfolio-omzet caching for cross-page comparison

**Files:**
- Modify: `dashboard/sidebar.js:53-70` (the existing `toonSidebarKpis()` function)

**Interfaces:**
- Produces: `haalPortfolioOmzetCache() -> {totaleOmzet: number, aantalWinkels: number, horizonDagen: number} | null` — consumed by Task 4's `dashboard.js` insights code.

- [ ] **Step 1: Extend `toonSidebarKpis()` to write the cache**

In `dashboard/sidebar.js`, find the end of `toonSidebarKpis()` (currently line 69):

```javascript
  toonOmzetTrend(data.kpi.totale_verwachte_omzet, geladen === data.totaal_winkels);
}
```

Replace with:

```javascript
  toonOmzetTrend(data.kpi.totale_verwachte_omzet, geladen === data.totaal_winkels);
  cachePortfolioOmzet(data.kpi.totale_verwachte_omzet, data.winkels.length);
}

// Voor de "T.o.v. je andere winkels"-inzichtkaart op index.html (zie
// dashboard.js) — index.html haalt bewust nooit zelf /portfolio op (zie
// initPortfolioSidebar hieronder), dus deze cache is de enige manier om
// die vergelijking zonder een nieuwe, dure aanroep te tonen. aantalWinkels
// is expliciet data.winkels.length (het aantal winkels waarover de
// omzetsom daadwerkelijk berekend is), niet data.totaal_winkels — die twee
// lopen uiteen zodra paginering actief is, en delen door het verkeerde
// getal zou het gemiddelde per winkel structureel te laag laten uitkomen.
// horizonDagen ligt vast op de HORIZON_DAGEN-constante uit overview.js
// (vandaag 7) — apart gecachet i.p.v. aangenomen, zodat een toekomstige
// wijziging van die constante deze vergelijking niet stilzwijgend scheef
// trekt.
function cachePortfolioOmzet(totaleOmzet, aantalWinkels) {
  const waarde = JSON.stringify({ totaleOmzet, aantalWinkels, horizonDagen: 7 });
  localStorage.setItem(sidebarSleutel("portfolio_omzet_cache", huidigeOrganisatieId), waarde);
}

function haalPortfolioOmzetCache() {
  const ruw = localStorage.getItem(sidebarSleutel("portfolio_omzet_cache", huidigeOrganisatieId));
  if (!ruw) return null;
  try {
    return JSON.parse(ruw);
  } catch (e) {
    return null;
  }
}
```

- [ ] **Step 2: Deploy and browser-verify the cache is written**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/sidebar.js job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, log in and load `https://prospero.tessar.nl/overview.html` (this triggers `toonSidebarKpis()`). Then run, via the browser automation's JavaScript execution capability, `localStorage.getItem(Object.keys(localStorage).find(k => k.includes('portfolio_omzet_cache')))` and confirm it returns a JSON string with `totaleOmzet`, `aantalWinkels`, and `horizonDagen` fields with real numeric values (not `null`, not zero unless the organization genuinely has zero forecastable stores).

- [ ] **Step 3: Commit**

```bash
git add dashboard/sidebar.js
git commit -m "feat: cache portfolio omzet for cross-page insight comparison"
```

---

### Task 4: "Inzichten" panel — three derived-statistic cards

**Files:**
- Modify: `dashboard/index.html` (new panel placement)
- Modify: `dashboard/dashboard.js` (new panel-rendering functions, wired into `voorspel()`)
- Modify: `dashboard/styles.css` (new panel/card classes)

**Interfaces:**
- Consumes: `haalPortfolioOmzetCache()` from Task 3 (`dashboard/sidebar.js`, loaded before `dashboard.js` in `index.html`'s script order — confirmed at `index.html:222-225`).
- Produces: `berekenBetrouwbaarheid(voorspellingen)`, `maakInzichtKaart(titel, waarde, toelichting)`, `toonInzichten(voorspellingen, factoren, totaalP50, n)` — called from `voorspel()`, not consumed by any later task.

- [ ] **Step 1: Add the panel placement to `index.html`**

In `dashboard/index.html`, find the end of the `.hero` div (currently lines 128-133):

```html
    <div class="hero">
      <p class="hero-lead" id="hero-lead"></p>
      <p class="waarde" id="hero-waarde">€ 0</p>
      <p class="sub-context" id="hero-sub"></p>
      <p class="periode-vergelijking" id="periode-vergelijking" hidden></p>
    </div>
```

Replace with:

```html
    <div class="hero">
      <p class="hero-lead" id="hero-lead"></p>
      <p class="waarde" id="hero-waarde">€ 0</p>
      <p class="sub-context" id="hero-sub"></p>
      <p class="periode-vergelijking" id="periode-vergelijking" hidden></p>
    </div>

    <div class="inzichten-paneel" id="inzichten-paneel" hidden></div>
```

- [ ] **Step 2: Add the betrouwbaarheid-calculation and card-rendering helpers to `dashboard.js`**

Add these functions to `dashboard/dashboard.js`, directly above `toonSamenvatting` (currently line 405):

```javascript
// Gemiddelde relatieve bandbreedte (p90-p10)/p50 over de horizon, vertaald
// naar een van drie kwalitatieve niveaus. Grenzen: <15% Stabiel, 15-30%
// Gemiddeld, >30% Wisselvallig (vastgelegd in de designspec, niet ter
// plekke verzonnen).
function berekenBetrouwbaarheid(voorspellingen) {
  const relatieveBreedtes = voorspellingen.map((v) => (v.p50 > 0 ? (v.p90 - v.p10) / v.p50 : 0));
  const gemiddelde = relatieveBreedtes.reduce((a, b) => a + b, 0) / relatieveBreedtes.length;
  const percentage = Math.round(gemiddelde * 100);
  let label;
  if (gemiddelde < 0.15) label = "Stabiel";
  else if (gemiddelde < 0.30) label = "Gemiddeld";
  else label = "Wisselvallig";
  return { label, percentage };
}

function maakInzichtKaart(titel, waarde, toelichting) {
  const kaart = document.createElement("div");
  kaart.className = "inzicht-kaart";
  const titelEl = document.createElement("p");
  titelEl.className = "inzicht-titel";
  titelEl.textContent = titel;
  const waardeEl = document.createElement("p");
  waardeEl.className = "inzicht-waarde";
  waardeEl.textContent = waarde;
  const toelichtingEl = document.createElement("p");
  toelichtingEl.className = "inzicht-toelichting";
  toelichtingEl.textContent = toelichting;
  kaart.append(titelEl, waardeEl, toelichtingEl);
  return kaart;
}

// Drie kaarten, elk optioneel: kaart 2 (sterkste patroon) blijft weg zonder
// SHAP-factoren, kaart 3 (portfolio-vergelijking) blijft weg zonder cache
// (zie dashboard/sidebar.js::haalPortfolioOmzetCache) — nooit een gokwaarde
// tonen. totaalP50/n is de al elders berekende gemiddelde omzet per dag
// voor déze winkel (zelfde berekening als de bestaande "Gemiddeld per
// dag"-stat in toonSamenvatting), vergeleken met het portfolio-gemiddelde
// per winkel per dag — beide genormaliseerd naar "per dag" omdat de
// portfolio-cache een vaste 7-dagen-horizon gebruikt (overview.js'
// HORIZON_DAGEN) terwijl deze winkel een andere, door de gebruiker
// gekozen horizon kan hebben.
function toonInzichten(voorspellingen, factoren, totaalP50, n) {
  const paneel = document.getElementById("inzichten-paneel");
  const kaarten = [];

  const { label, percentage } = berekenBetrouwbaarheid(voorspellingen);
  kaarten.push(maakInzichtKaart(
    "Betrouwbaarheid",
    `${label} — ±${percentage}%`,
    "Gemiddelde bandbreedte over de voorspelde periode, relatief aan de verwachte omzet.",
  ));

  if (factoren && factoren.length > 0) {
    const sterkste = factoren[0];
    kaarten.push(maakInzichtKaart(
      "Sterkste patroon",
      `${sterkste.naam} — ${sterkste.richting}`,
      "De factor met de grootste invloed op deze voorspelling.",
    ));
  }

  const portfolioCache = haalPortfolioOmzetCache();
  if (portfolioCache && portfolioCache.aantalWinkels > 0 && portfolioCache.horizonDagen > 0) {
    const portfolioGemiddeldePerWinkelPerDag =
      portfolioCache.totaleOmzet / portfolioCache.aantalWinkels / portfolioCache.horizonDagen;
    if (portfolioGemiddeldePerWinkelPerDag > 0) {
      const dezeWinkelPerDag = totaalP50 / n;
      const verschilPct = Math.round(
        ((dezeWinkelPerDag - portfolioGemiddeldePerWinkelPerDag) / portfolioGemiddeldePerWinkelPerDag) * 100,
      );
      const richtingTekst =
        Math.abs(verschilPct) < 2 ? "Vergelijkbaar" : verschilPct > 0 ? `${verschilPct}% hoger` : `${Math.abs(verschilPct)}% lager`;
      kaarten.push(maakInzichtKaart(
        "T.o.v. je andere winkels",
        richtingTekst,
        "Gemiddelde omzet per dag, vergeleken met het gemiddelde over je hele portfolio (laatst bekende stand).",
      ));
    }
  }

  paneel.replaceChildren(...kaarten);
  paneel.hidden = kaarten.length === 0;
}
```

- [ ] **Step 3: Wire `toonInzichten()` into the existing prediction flow**

In `dashboard/dashboard.js`, find the call to `toonFactoren` inside `voorspel()` (currently line 564):

```javascript
    toonFactoren(data.belangrijkste_factoren);
```

Replace with:

```javascript
    toonFactoren(data.belangrijkste_factoren);
    const totaalP50VoorInzichten = voorspellingen.reduce((som, v) => som + v.p50, 0);
    toonInzichten(voorspellingen, data.belangrijkste_factoren, totaalP50VoorInzichten, voorspellingen.length);
```

- [ ] **Step 4: Add CSS for the panel and cards**

In `dashboard/styles.css`, add near the existing `.factoren`/`.secundair` rules (around line 158, after the `.secundair`/`.stat` block):

```css
.inzichten-paneel { display:flex; gap:14px; flex-wrap:wrap; margin:20px 0 0; }
.inzicht-kaart {
  flex:1 1 200px; padding:16px; background:var(--paper-raised); border:1px solid var(--line);
  border-radius:12px; display:flex; flex-direction:column; gap:4px;
}
.inzicht-titel { font:600 0.75rem/1.2 var(--font-body); color:var(--ink-soft); text-transform:uppercase; letter-spacing:0.03em; }
.inzicht-waarde { font:600 1.0625rem/1.3 var(--font-body); color:var(--ink); font-variant-numeric:tabular-nums; }
.inzicht-toelichting { font-size:0.75rem; color:var(--ink-faint); line-height:1.4; }
```

- [ ] **Step 5: Deploy and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/index.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/dashboard.js \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/styles.css \
    job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome:
1. Load `https://prospero.tessar.nl/overview.html` first (populates the portfolio cache), then navigate to `index.html`, pick a store, click "Voorspel". Confirm all three insight cards render with real, plausible values — the betrouwbaarheid label/percentage matches the visible band width in the chart, "Sterkste patroon" shows the same factor as the first chip in the existing "Waarom deze voorspelling" list, and "T.o.v. je andere winkels" shows a percentage comparison.
2. Open a fresh incognito/private browser context (or clear `localStorage` for the domain), log in, and navigate directly to `index.html` **without** visiting `overview.html` first. Predict a forecast and confirm exactly two cards render (Betrouwbaarheid, Sterkste patroon) with no layout gap or empty third card where "T.o.v. je andere winkels" would be — the `paneel.hidden`/card-count logic must never show a blank/placeholder third card.
3. Repeat step 1 in dark mode and confirm the cards remain legible (background, border, text contrast).

- [ ] **Step 6: Commit**

```bash
git add dashboard/index.html dashboard/dashboard.js dashboard/styles.css
git commit -m "feat: add Inzichten panel with betrouwbaarheid, sterkste patroon, and portfolio comparison"
```

---

## Self-Review

**Spec coverage:** Logo (standalone, no live-page wiring) is Task 1. Chart modernization (smooth curves, gradient fill, tooltips) is Task 2. The corrected portfolio-comparison mechanism (localStorage cache written by `overview.js`/`sidebar.js`, read by `dashboard.js`, never a new fetch) is Tasks 3-4. All three Inzichten cards (Betrouwbaarheid with exact thresholds, Sterkste patroon reusing the existing sorted SHAP list, T.o.v. je andere winkels with correct per-day/per-store normalization) are in Task 4. The spec's explicit out-of-scope items (technical rename, `overview.html`/`team.html` redesign, new backend computation) are respected — no task touches the backend or any page besides `index.html`, and the logo is deliberately never referenced from a live page.

**Placeholder scan:** No TBD/TODO. Every code block is complete, runnable JS/CSS/SVG — no "add appropriate styling" language.

**Type consistency:** `haalPortfolioOmzetCache()` (Task 3) returns `{totaleOmzet, aantalWinkels, horizonDagen} | null`, consumed in Task 4 with exactly those three field names and the same null-check pattern. `berekenBetrouwbaarheid()`, `maakInzichtKaart()`, `toonInzichten()` are defined and consumed within the same task (Task 4), with consistent parameter names throughout. `gladPadSegment`/`lijnPadData`/`bandPadData`/`maakBandGradient`/`initGrafiekTooltip` (Task 2) are all defined and called within that same task — no cross-task naming drift.
