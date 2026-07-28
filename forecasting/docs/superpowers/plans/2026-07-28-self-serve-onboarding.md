# Self-serve onboarding: voorbeeld-voorspelling + "Aan de slag"-checklist — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every self-serve organisation (one where `GET /winkels` returns an empty list — a permanent structural fact for this org type, not a transient new-user state) a live example forecast on `index.html` plus a short "Aan de slag" checklist on all three dashboard pages, so a brand-new signup understands what the product produces before their own 28 days of data exist.

**Architecture:** Two independent additions, deliberately isolated from existing tenant-isolation logic rather than loosening it. Backend: a new `GET /voorbeeld/forecast` endpoint, session-gated only (`vereis_sessie`), never checking `db_winkels`/`hoort_store_bij_organisatie` — it calls the existing `voorspel_periode()` against one fixed, configured example `store_id`. Frontend: a new shared `dashboard/onboarding.js` (parallel to `dashboard/sidebar.js`), loaded on all three pages, exposing two independent functions — `initOnboarding(me)` for the checklist, `toonVoorbeeldVoorspelling()` for the example card (called only from `index.html`'s existing empty-state branch).

**Tech Stack:** FastAPI + SQLAlchemy + pandas backend (Python), vanilla JS frontend (no framework, no build step, plain `<script>` tags sharing one global scope per page).

## Global Constraints

- TDD is mandatory for all backend work: RED (watch the real failure) → GREEN → REFACTOR. No exceptions.
- Frontend has no automated test coverage by established project convention — verify live in-browser instead (claude-in-chrome), not with new test infrastructure.
- Local test execution is broken (macOS native dependency resolution for xgboost/shap fails) — run backend tests via the established rsync + remote Docker pattern (see Task 1/2 test-running steps).
- Plain `<script src="...">` tags share one global scope per page (no ES modules) — `dashboard/onboarding.js` must never redeclare a top-level `const`/function name already declared by `sidebar.js`, `dashboard.js`, `overview.js`, or `account.js` on the same page. Confirmed collision risk: `dashboard.js`, `overview.js`, and `account.js` each already declare their own top-level `const euro = new Intl.NumberFormat(...)` — `onboarding.js` must not declare a same-named `euro`. Follow `sidebar.js`'s own established convention of prefixing everything (`SIDEBAR_API_BASIS`, `sidebarSleutel`) with an `onboarding`/`ONBOARDING_` prefix.
- New UI pieces fail silently on fetch error (hide the section, no visible error) — never surface a broken-looking widget in a brand-new user's first minutes with the product.
- No lowering of the 28-day minimum-history threshold or the existing false-precision safeguards anywhere in this feature.
- Deploy: backend changes require `scp` the changed files to `job@157.90.244.24:/home/job/forecasting-demo/` then `docker compose build api && docker compose up -d` from `deploy/`. `dashboard/*` files are bind-mounted — a plain `scp` makes them live immediately, no rebuild.

---

## File Structure

**Backend:**
- `serving/config.py` (modify) — add `voorbeeld_store_id: Optional[int]` to `Settings`, read from `VOORBEELD_STORE_ID`.
- `tests/test_config.py` (modify) — two new tests for the setting above.
- `serving/app.py` (modify) — add `GET /voorbeeld/forecast`, placed directly after the existing `/forecast` endpoint (before `/metrics`).
- `tests/test_voorbeeld_forecast_endpoint.py` (create) — full TDD coverage for the new endpoint, fixture pattern copied from `tests/test_eigen_voorspelling_endpoint.py`.

**Frontend:**
- `dashboard/onboarding.js` (create) — shared, self-contained. `initOnboarding(me)` (checklist, all 3 pages) and `toonVoorbeeldVoorspelling()` (example card, `index.html` only).
- `dashboard/overview.html`, `dashboard/index.html`, `dashboard/team.html` (modify) — add `<script src="./onboarding.js">` between `sidebar.js` and the page's own script; add a checklist placeholder `<div id="onboarding-checklist" class="kaart onboarding-checklist" hidden></div>` near the top of each page's main content.
- `dashboard/index.html` (modify further) — add a voorbeeld-preview slot `<div id="voorbeeld-voorspelling" class="kaart voorbeeld-kaart" hidden></div>` immediately after the existing `#leeg` element (line 114).
- `dashboard/overview.js`, `dashboard/dashboard.js`, `dashboard/account.js` (modify) — each calls `initOnboarding(me)` right after its existing `initPortfolioSidebar(me)` call. `dashboard/dashboard.js` additionally calls `toonVoorbeeldVoorspelling()` inside its existing `winkels.length === 0` branch, only on the eigenaar side (never for `me.rol === "lid"`).
- `dashboard/styles.css` (modify) — new rules for `.onboarding-checklist`, `.onboarding-lijst`, `.onboarding-item` (+ `.afgerond` modifier), `.onboarding-verbergen`, `.voorbeeld-kaart`, `.voorbeeld-titel`, `.voorbeeld-tekst`, `.voorbeeld-badge`.

---

### Task 1: Backend — `voorbeeld_store_id` setting

**Files:**
- Modify: `serving/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Settings.voorbeeld_store_id: Optional[int]`, read from env var `VOORBEELD_STORE_ID` (empty/unset → `None`, no hard failure).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py` (near the existing `test_laad_settings_zonder_mailconfig_geeft_none` / `test_laad_settings_leest_mailconfig` pair, same file):

```python
def test_laad_settings_zonder_voorbeeld_store_id_geeft_none(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path)
    monkeypatch.delenv("VOORBEELD_STORE_ID", raising=False)
    settings = config.laad_settings()
    assert settings.voorbeeld_store_id is None


def test_laad_settings_leest_voorbeeld_store_id(monkeypatch, tmp_path):
    _basis_env(monkeypatch, tmp_path, VOORBEELD_STORE_ID="1")
    settings = config.laad_settings()
    assert settings.voorbeeld_store_id == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_config.py -v -k voorbeeld_store_id'"
```

Expected: both FAIL with `AttributeError: 'Settings' object has no attribute 'voorbeeld_store_id'`.

- [ ] **Step 3: Implement**

In `serving/config.py`, add the field to the `Settings` dataclass, right after `app_basis_url` (line 44):

```python
    # Fase "tier omhoog" onboarding: welk store_id uit het gedeelde
    # modelartefact als publiek, niet-tenant-gebonden voorbeeld dient voor
    # GET /voorbeeld/forecast (zie serving/app.py) — een self-serve
    # organisatie heeft nooit een eigen winkelbinding (zie
    # FASE4-SAAS-FOUNDATION.md beslissing 4), dus zonder dit voorbeeld ziet
    # zo'n organisatie wekenlang nooit een werkende voorspelling. Optioneel:
    # zonder ingesteld voorbeeld geeft dat endpoint een nette 503, geen crash.
    voorbeeld_store_id: Optional[int] = None
```

In `laad_settings()`, add parsing right after the `mail_smtp_poort` block (after line 101):

```python
    ruwe_voorbeeld_store_id = os.environ.get("VOORBEELD_STORE_ID")
    voorbeeld_store_id = int(ruwe_voorbeeld_store_id) if ruwe_voorbeeld_store_id else None
```

And add the field to the returned `Settings(...)` call (after `app_basis_url=os.environ.get("APP_BASIS_URL"),`):

```python
        voorbeeld_store_id=voorbeeld_store_id,
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_config.py -v'"
```

Expected: all `test_config.py` tests PASS (the two new ones plus every pre-existing one, to confirm no regression).

- [ ] **Step 5: Commit**

```bash
git add serving/config.py tests/test_config.py
git commit -m "feat: add optional voorbeeld_store_id setting for onboarding preview"
```

---

### Task 2: Backend — `GET /voorbeeld/forecast` endpoint

**Files:**
- Modify: `serving/app.py`
- Test: `tests/test_voorbeeld_forecast_endpoint.py` (new)

**Interfaces:**
- Consumes: `Settings.voorbeeld_store_id` (Task 1), `GeauthenticeerdeGebruiker`/`vereis_sessie` (existing, `serving/app.py:166-189`), `voorspel_periode()` / `OnbekendeWinkel` / `HorizonBuitenBereik` (existing, `serving/forecast.py`, already imported in `app.py`), `ForecastResponse`/`DagVoorspelling` (existing, `serving/schemas.py`, already imported in `app.py`).
- Produces: `GET /voorbeeld/forecast` → `ForecastResponse` (200), or 401 (no session), or 503 (unconfigured / configured store missing from artifact).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_voorbeeld_forecast_endpoint.py`:

```python
"""GET /voorbeeld/forecast: een bewust nooit tenant-geïsoleerd
voorbeeld-eindpunt voor self-serve organisaties zonder eigen winkelbinding
of eigen data — zie forecasting/docs/superpowers/specs/2026-07-28-
self-serve-onboarding-design.md. Zelfde fixture-patroon als
test_eigen_voorspelling_endpoint.py."""
import importlib
import sys

from fastapi.testclient import TestClient

from db.bootstrap import bootstrap_organisatie
from db.gebruikers import maak_gebruiker
from db.schema import maak_database


def _bouw_omgeving(tmp_path, monkeypatch, voorbeeld_store_id="1"):
    (tmp_path / "api_keys.json").write_text("{}", encoding="utf-8")
    (tmp_path / "models").mkdir()

    tenants_db_pad = tmp_path / "tenants.db"
    engine = maak_database(tenants_db_pad)
    # Bewust store_ids=[] — dit bewijst dat het voorbeeld-eindpunt werkt
    # zonder dat de organisatie zelf ook maar één winkelbinding heeft.
    org_id = bootstrap_organisatie(engine, naam="Zelfbediening klant", slug="zelfbediening-klant", store_ids=[])
    maak_gebruiker(engine, organisatie_id=org_id, email="eigenaar@klant.nl", wachtwoord="een-goed-wachtwoord", rol="eigenaar")

    monkeypatch.setenv("MODEL_VERSION", _bootstrap_model(tmp_path))
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("API_KEYS_FILE", str(tmp_path / "api_keys.json"))
    monkeypatch.setenv("AUDIT_LOG_FILE", str(tmp_path / "audit.log"))
    monkeypatch.setenv("TENANTS_DB_PAD", str(tenants_db_pad))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("FORECASTING_ENCRYPT_AT_REST", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUUT", "1000")
    monkeypatch.setenv("SESSIE_COOKIE_SECURE", "false")
    if voorbeeld_store_id is None:
        monkeypatch.delenv("VOORBEELD_STORE_ID", raising=False)
    else:
        monkeypatch.setenv("VOORBEELD_STORE_ID", voorbeeld_store_id)

    if "serving.app" in sys.modules:
        del sys.modules["serving.app"]
    module = importlib.import_module("serving.app")
    return TestClient(module.app)


def _bootstrap_model(tmp_path):
    import numpy as np
    import pandas as pd

    from training import artifact, train

    modellen = train.train_alle_kwantielen(pd.DataFrame({
        **{k: np.random.default_rng(1).uniform(0, 100, 200) for k in train.FEATURE_KOLOMMEN},
        "Sales": np.random.default_rng(1).uniform(500, 2000, 200),
        "Open": 1,
    }))
    historie = pd.DataFrame({
        "Store": 1, "Date": pd.date_range("2015-06-01", periods=40, freq="D"),
        "Sales": np.random.default_rng(2).uniform(500, 2000, 40), "Open": 1,
    })
    winkel_metadata = pd.DataFrame({"Store": [1], "CompetitionDistance": [500.0]})
    return artifact.schrijf_artefact(
        basis_map=tmp_path / "models", modellen=modellen, historie=historie,
        winkel_metadata=winkel_metadata,
        metrics={"rmspe": 0.15, "coverage_p10_p90": 0.79, "n_observaties": 500},
        trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")),
        gevalideerde_horizon_dagen=30, versleuteld=False,
    )


def _inloggen(client):
    resp = client.post("/login", json={"email": "eigenaar@klant.nl", "wachtwoord": "een-goed-wachtwoord"})
    assert resp.status_code == 200, resp.text


def test_voorbeeld_forecast_werkt_zonder_eigen_winkelbinding(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)
    _inloggen(client)

    resp = client.get("/voorbeeld/forecast")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["store_id"] == 1
    assert len(data["voorspellingen"]) == 14


def test_voorbeeld_forecast_zonder_sessie_geeft_401(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch)

    resp = client.get("/voorbeeld/forecast")

    assert resp.status_code == 401


def test_voorbeeld_forecast_zonder_configuratie_geeft_503(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch, voorbeeld_store_id=None)
    _inloggen(client)

    resp = client.get("/voorbeeld/forecast")

    assert resp.status_code == 503


def test_voorbeeld_forecast_onbekend_store_id_geeft_503(tmp_path, monkeypatch):
    client = _bouw_omgeving(tmp_path, monkeypatch, voorbeeld_store_id="999")
    _inloggen(client)

    resp = client.get("/voorbeeld/forecast")

    assert resp.status_code == 503
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
rsync -av --exclude='.venv' --exclude='models' --exclude='data' --exclude='*.db*' \
  /Users/hamdeco/development/hamdoun/forecasting/ \
  job@157.90.244.24:/home/job/forecasting-test-sync/

ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_voorbeeld_forecast_endpoint.py -v'"
```

Expected: all four FAIL with `404 Not Found` (route doesn't exist yet).

- [ ] **Step 3: Implement**

In `serving/app.py`, insert the new endpoint directly after the `/forecast` endpoint's closing `return ForecastResponse(...)` block (after line 755, before the `@app.get("/metrics"...)` line at 758):

```python
@app.get("/voorbeeld/forecast", response_model=ForecastResponse)
def voorbeeld_forecast(gebruiker: GeauthenticeerdeGebruiker = Depends(vereis_sessie)) -> ForecastResponse:
    # Bewust NOOIT tenant-geïsoleerd — geen db_winkels/hoort_store_bij_
    # organisatie-check, in tegenstelling tot POST /forecast hierboven. Dit
    # is geen versoepelde variant van die controle, maar een apart pad
    # ernaast: een self-serve organisatie heeft nooit een eigen
    # winkelbinding (zie FASE4-SAAS-FOUNDATION.md beslissing 4) en heeft
    # minimaal MINIMUM_DAGEN dagen eigen data nodig vóór de eigen
    # voorspelling iets teruggeeft — zonder dit voorbeeld zou zo'n
    # organisatie wekenlang nooit een werkende voorspelling zien.
    if settings.voorbeeld_store_id is None:
        raise HTTPException(status_code=503, detail="Voorbeeldvoorspelling is nog niet geconfigureerd.")

    horizon_dagen = 14
    start_datum = pd.Timestamp(artefact["metadata"]["trainingsperiode_eind"][:10]) + pd.Timedelta(days=1)
    try:
        resultaat = voorspel_periode(
            modellen=artefact["modellen"],
            historie=artefact["historie"],
            winkel_metadata=artefact["winkel_metadata"],
            store_id=settings.voorbeeld_store_id,
            start_datum=start_datum,
            horizon_dagen=horizon_dagen,
            verklaar=False,
        )
    except (OnbekendeWinkel, HorizonBuitenBereik):
        raise HTTPException(status_code=503, detail="Voorbeeldvoorspelling is momenteel niet beschikbaar.")

    return ForecastResponse(
        store_id=settings.voorbeeld_store_id,
        voorspellingen=[
            DagVoorspelling(datum=rij["Date"].date(), p10=rij["p10"], p50=rij["p50"], p90=rij["p90"])
            for _, rij in resultaat.voorspellingen.iterrows()
        ],
        belangrijkste_factoren=[],
        vorige_periode_omzet=None,
        herbestel_advies=None,
    )
```

No new imports needed — `pd`, `HTTPException`, `Depends`, `ForecastResponse`, `DagVoorspelling`, `GeauthenticeerdeGebruiker`, `vereis_sessie`, `voorspel_periode`, `OnbekendeWinkel`, `HorizonBuitenBereik` are all already imported in `serving/app.py`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest tests/test_voorbeeld_forecast_endpoint.py tests/test_config.py -v'"
```

Expected: all PASS.

- [ ] **Step 5: Run the full backend test suite to confirm no regression**

```bash
ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/app -w /app --user root deploy-api:latest bash -c 'pip install pytest >/dev/null 2>&1 && pytest -q'"
```

Expected: PASS, no new failures. If the scratch dir at `/home/job/forecasting-test-sync` ends up root-owned and blocks a later `rsync`, clean it up with `ssh job@157.90.244.24 "docker run --rm -v /home/job/forecasting-test-sync:/data alpine sh -c 'rm -rf /data/*'"` before re-syncing.

- [ ] **Step 6: Commit**

```bash
git add serving/app.py tests/test_voorbeeld_forecast_endpoint.py
git commit -m "feat: add GET /voorbeeld/forecast for self-serve onboarding preview"
```

---

### Task 3: Frontend — onboarding checklist (`onboarding.js` core + wiring on all 3 pages)

**Files:**
- Create: `dashboard/onboarding.js`
- Modify: `dashboard/overview.html`, `dashboard/index.html`, `dashboard/team.html` (script tag + checklist placeholder markup)
- Modify: `dashboard/overview.js`, `dashboard/dashboard.js`, `dashboard/account.js` (wire `initOnboarding(me)`)
- Modify: `dashboard/styles.css` (checklist CSS)

**Interfaces:**
- Consumes: `GET /winkels` (existing), `GET /organisatie/verkoopdata` (existing, returns `{rijen: [...]}`), `GET /organisatie/instellingen` (existing, returns `{gemiddelde_omzet_per_stuk: number|null}`), `me.organisatie_id` / `me.rol` (existing `haalMe()`/`initToegang()` result shape, fields already used elsewhere e.g. `dashboard/dashboard.js:843`).
- Produces: `initOnboarding(me: {organisatie_id, rol, ...}): Promise<void>` — global function, callable from any page after `initPortfolioSidebar(me)`.

- [ ] **Step 1: Create `dashboard/onboarding.js`**

```javascript
"use strict";

// Gedeeld door alle drie de pagina's met een .portfolio-shell-zijbalk
// (overview.html, index.html, team.html) — zelfde laadvolgorde als
// sidebar.js: config.js, sidebar.js, onboarding.js, dan het pagina-eigen
// script. Bewust een apart, zelfstandig bestand i.p.v. functies aan
// sidebar.js toevoegen: dit gaat over een tijdelijke, per-organisatie
// aan/uit-staande onboarding-fase, niet over permanente zijbalk-chrome.
//
// Let op: alle scripts op een pagina delen één globale scope (geen ES
// modules) — dashboard.js, overview.js en account.js declareren elk al
// hun eigen top-level "const euro". Daarom hier alles prefixen met
// "onboarding"/"ONBOARDING_", zelfde patroon als sidebar.js met
// SIDEBAR_API_BASIS/sidebarSleutel.
const ONBOARDING_API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";

function onboardingFormatEuro(bedrag) {
  return new Intl.NumberFormat("nl-NL", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(bedrag);
}

function onboardingSleutel(organisatieId) {
  return `vraagvoorspelling_onboarding_verborgen_org${organisatieId}`;
}

async function haalOnboardingStatus() {
  const [verkoopdataResp, instellingenResp] = await Promise.all([
    fetch(`${ONBOARDING_API_BASIS}/organisatie/verkoopdata`, { credentials: "same-origin" }),
    fetch(`${ONBOARDING_API_BASIS}/organisatie/instellingen`, { credentials: "same-origin" }),
  ]);
  if (!verkoopdataResp.ok || !instellingenResp.ok) throw new Error("Kon onboarding-status niet ophalen");
  const verkoopdata = await verkoopdataResp.json();
  const instellingen = await instellingenResp.json();
  return {
    verkoopdataGeupload: verkoopdata.rijen.length > 0,
    prijsIngesteld: instellingen.gemiddelde_omzet_per_stuk !== null,
  };
}

function toonOnboardingChecklist(status, organisatieId) {
  const kaart = document.getElementById("onboarding-checklist");
  if (!kaart) return;

  const volledig = status.verkoopdataGeupload && status.prijsIngesteld;
  if (volledig) {
    kaart.hidden = true;
    return;
  }
  if (localStorage.getItem(onboardingSleutel(organisatieId)) === "verborgen") {
    kaart.hidden = true;
    return;
  }

  const items = [
    ["Upload je verkoopdata", status.verkoopdataGeupload, "./team.html"],
    ["Stel je herbestel-prijs in", status.prijsIngesteld, "./team.html"],
  ];
  const lijst = document.createElement("ul");
  lijst.className = "onboarding-lijst";
  for (const [label, klaar, link] of items) {
    const li = document.createElement("li");
    li.className = klaar ? "onboarding-item afgerond" : "onboarding-item";
    if (klaar) {
      li.textContent = `✓ ${label}`;
    } else {
      const a = document.createElement("a");
      a.href = link;
      a.textContent = label;
      li.appendChild(a);
    }
    lijst.appendChild(li);
  }

  const verbergKnop = document.createElement("button");
  verbergKnop.type = "button";
  verbergKnop.className = "onboarding-verbergen";
  verbergKnop.textContent = "Verbergen";
  verbergKnop.addEventListener("click", () => {
    localStorage.setItem(onboardingSleutel(organisatieId), "verborgen");
    kaart.hidden = true;
  });

  const titel = document.createElement("p");
  titel.className = "onboarding-titel";
  titel.textContent = "Aan de slag";

  kaart.replaceChildren(titel, lijst, verbergKnop);
  kaart.hidden = false;
}

async function initOnboarding(me) {
  // Een "lid" zonder toegewezen winkels zit in een heel andere situatie
  // dan een zelfbediening-organisatie zonder eigen data — de organisatie
  // zelf heeft dan gewoon al winkels, alleen is dit specifieke teamlid er
  // nog niet aan gekoppeld. Zelfde eigenaar/lid-redenering als het
  // bestaande "geen winkels"-bericht in dashboard.js.
  if (me.rol === "lid") return;
  try {
    const winkelsResp = await fetch(`${ONBOARDING_API_BASIS}/winkels`, { credentials: "same-origin" });
    if (!winkelsResp.ok) return;
    const winkels = await winkelsResp.json();
    if (winkels.length > 0) return;
    const status = await haalOnboardingStatus();
    toonOnboardingChecklist(status, me.organisatie_id);
  } catch (e) {
    // Stille fout, zelfde reden als sidebar.js's KPI-aanroep: een
    // mislukte onboarding-checklist mag de rest van de pagina niet
    // verstoren.
  }
}
```

- [ ] **Step 2: Add the script tag to all three pages**

In `dashboard/overview.html`, `dashboard/index.html`, `dashboard/team.html`, change:

```html
<script src="./config.js"></script>
<script src="./sidebar.js"></script>
```

to (adding one line, keeping each page's own script tag unchanged after it):

```html
<script src="./config.js"></script>
<script src="./sidebar.js"></script>
<script src="./onboarding.js"></script>
```

- [ ] **Step 3: Add the checklist placeholder markup to all three pages**

In `dashboard/overview.html`, insert immediately after `<div class="wrap portfolio-main">` (line 66):

```html
    <div id="onboarding-checklist" class="kaart onboarding-checklist" hidden></div>
```

In `dashboard/index.html`, insert immediately after `<div class="wrap">` (line 66):

```html
  <div id="onboarding-checklist" class="kaart onboarding-checklist" hidden></div>
```

In `dashboard/team.html`, insert immediately after `<div class="wrap">` (line 66):

```html
  <div id="onboarding-checklist" class="kaart onboarding-checklist" hidden></div>
```

- [ ] **Step 4: Wire `initOnboarding(me)` into each page's own script**

In `dashboard/overview.js`, in the `DOMContentLoaded` handler, change:

```javascript
  initPortfolioSidebar(me);
  await laadMeer();
```

to:

```javascript
  initPortfolioSidebar(me);
  initOnboarding(me);
  await laadMeer();
```

In `dashboard/dashboard.js`, in the `DOMContentLoaded` handler, change:

```javascript
  initPortfolioSidebar(me);

  const knop = document.getElementById("voorspel");
```

to:

```javascript
  initPortfolioSidebar(me);
  initOnboarding(me);

  const knop = document.getElementById("voorspel");
```

In `dashboard/account.js`, in `initTeamPagina()`, change:

```javascript
  initPortfolioSidebar(me);

  const kanBeheren = me.rol === "eigenaar";
```

to:

```javascript
  initPortfolioSidebar(me);
  initOnboarding(me);

  const kanBeheren = me.rol === "eigenaar";
```

- [ ] **Step 5: Add checklist CSS**

Append to `dashboard/styles.css`:

```css
/* Onboarding-checklist: zichtbaar op alle drie de pagina's voor een
   zelfbediening-organisatie zonder eigen data, verdwijnt automatisch
   zodra beide stappen klaar zijn of handmatig via "Verbergen" (per
   organisatie onthouden, zie onboarding.js's onboardingSleutel()). */
.onboarding-checklist { gap:10px; }
.onboarding-titel { font:600 0.9375rem/1.2 var(--font-body); margin:0; color:var(--ink); }
.onboarding-lijst { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:8px; }
.onboarding-item { font:400 0.875rem/1.4 var(--font-body); color:var(--ink-soft); }
.onboarding-item a { color:var(--accent-ink); font-weight:600; text-decoration:none; }
.onboarding-item a:hover { text-decoration:underline; }
.onboarding-item.afgerond { color:var(--ink-faint); text-decoration:line-through; }
.onboarding-verbergen {
  align-self:flex-start; background:none; border:none; padding:0; margin:0;
  font:400 0.8125rem/1.2 var(--font-body); color:var(--ink-faint); cursor:pointer; text-decoration:underline;
}
```

- [ ] **Step 6: Deploy and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/onboarding.js \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/overview.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/index.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/team.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/overview.js \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/dashboard.js \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/account.js \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/styles.css \
    job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, navigate to `https://forecasting-demo.tessar.nl/overview.html`, log in as a self-serve organisation account with zero stores and no uploaded verkoopdata (e.g. `scrapingscrambling@gmail.com`, used earlier this engagement for exactly this scenario), and verify:
- The "Aan de slag" checklist card appears on `overview.html`, `index.html`, and `team.html`, listing both unfinished items with working links to `team.html`.
- Clicking "Verbergen" hides it; a page reload keeps it hidden.
- Logging in as the existing demo org (real winkels) shows the checklist on none of the three pages.
- Read `dashboard/team.html`, upload a small verkoopdata CSV and set a herbestel-prijs, then reload `overview.html` — the checklist must disappear automatically (both items now complete), without needing to click "Verbergen".

- [ ] **Step 7: Commit**

```bash
git add dashboard/onboarding.js dashboard/overview.html dashboard/index.html dashboard/team.html \
        dashboard/overview.js dashboard/dashboard.js dashboard/account.js dashboard/styles.css
git commit -m "feat: add self-serve onboarding checklist across all dashboard pages"
```

---

### Task 4: Frontend — voorbeeld-voorspelling card on `index.html`

**Files:**
- Modify: `dashboard/onboarding.js` (add `toonVoorbeeldVoorspelling()`)
- Modify: `dashboard/index.html` (voorbeeld-preview markup slot)
- Modify: `dashboard/dashboard.js` (wire the call into the existing empty-winkels branch)
- Modify: `dashboard/styles.css` (voorbeeld-kaart CSS)

**Interfaces:**
- Consumes: `GET /voorbeeld/forecast` (Task 2), returns `ForecastResponse` shape `{store_id, voorspellingen: [{datum, p10, p50, p90}, ...], ...}`.
- Produces: `toonVoorbeeldVoorspelling(): Promise<void>` — global function, called only from `dashboard/dashboard.js`'s empty-winkels-and-eigenaar branch.

- [ ] **Step 1: Add `toonVoorbeeldVoorspelling()` to `dashboard/onboarding.js`**

Append to the end of `dashboard/onboarding.js`:

```javascript
async function toonVoorbeeldVoorspelling() {
  const wrap = document.getElementById("voorbeeld-voorspelling");
  if (!wrap) return;
  try {
    const resp = await fetch(`${ONBOARDING_API_BASIS}/voorbeeld/forecast`, { credentials: "same-origin" });
    if (!resp.ok) return;
    const data = await resp.json();

    const totaalP50 = data.voorspellingen.reduce((som, v) => som + Math.max(0, v.p50), 0);
    const totaalP10 = data.voorspellingen.reduce((som, v) => som + Math.max(0, v.p10), 0);
    const totaalP90 = data.voorspellingen.reduce((som, v) => som + Math.max(0, v.p90), 0);

    const badge = document.createElement("span");
    badge.className = "voorbeeld-badge";
    badge.textContent = "Voorbeeld";

    const titel = document.createElement("p");
    titel.className = "voorbeeld-titel";
    titel.append("Zo ziet een voorspelling eruit ", badge);

    const tekst = document.createElement("p");
    tekst.className = "voorbeeld-tekst";
    tekst.textContent =
      `Winkel ${data.store_id} verkoopt de komende ${data.voorspellingen.length} dagen waarschijnlijk ongeveer ` +
      `${onboardingFormatEuro(Math.round(totaalP50))} (bandbreedte ${onboardingFormatEuro(Math.round(totaalP10))}` +
      `–${onboardingFormatEuro(Math.round(totaalP90))}). Upload je eigen verkoopdata op Team beheren om dit voor ` +
      `jouw winkel te zien.`;

    wrap.replaceChildren(titel, tekst);
    wrap.hidden = false;
  } catch (e) {
    // Stille fout — zelfde principe als initOnboarding hierboven.
  }
}
```

- [ ] **Step 2: Add the voorbeeld-preview markup slot to `dashboard/index.html`**

Change:

```html
  <div class="leeg" id="leeg">Kies een winkel en klik op "Voorspel" om de verwachte omzet te zien.</div>
```

to:

```html
  <div class="leeg" id="leeg">Kies een winkel en klik op "Voorspel" om de verwachte omzet te zien.</div>

  <div id="voorbeeld-voorspelling" class="kaart voorbeeld-kaart" hidden></div>
```

- [ ] **Step 3: Wire the call into `dashboard/dashboard.js`'s existing empty-winkels branch**

Change:

```javascript
    document.getElementById("leeg").textContent = me.rol === "lid"
      ? "Er zijn nog geen winkels aan jou toegewezen. Vraag de eigenaar van je organisatie om dit in te stellen via Team beheren."
      : "Er zijn nog geen winkels aan jouw organisatie gekoppeld. Neem contact op om dit in te laten stellen.";
    return;
```

to:

```javascript
    if (me.rol === "lid") {
      document.getElementById("leeg").textContent =
        "Er zijn nog geen winkels aan jou toegewezen. Vraag de eigenaar van je organisatie om dit in te stellen via Team beheren.";
    } else {
      document.getElementById("leeg").textContent =
        "Er zijn nog geen winkels aan jouw organisatie gekoppeld.";
      toonVoorbeeldVoorspelling();
    }
    return;
```

(The eigenaar-only message drops its old "Neem contact op..." phrasing since the voorbeeld card + onboarding checklist now give this user a concrete next step instead of a dead end.)

- [ ] **Step 4: Add voorbeeld-kaart CSS**

Append to `dashboard/styles.css`:

```css
/* Voorbeeld-voorspelling: op index.html, alleen voor een eigenaar van een
   zelfbediening-organisatie zonder eigen winkelbinding (zie
   dashboard.js's winkels.length === 0-tak). Bewust een neutrale, niet
   premium-gekleurde badge (.voorbeeld-badge) — dit is gratis en voor
   iedereen zichtbaar, geen premium-functie, dus geen visuele verwarring
   met .premium-badge. */
.voorbeeld-kaart { gap:8px; }
.voorbeeld-titel { display:flex; align-items:center; gap:8px; font:600 0.9375rem/1.2 var(--font-body); margin:0; color:var(--ink); }
.voorbeeld-tekst { font:400 0.9375rem/1.5 var(--font-body); margin:0; color:var(--ink-soft); }
.voorbeeld-badge {
  display:inline-flex; align-items:center; font:600 0.6875rem/1.2 var(--font-body);
  color:var(--ink-faint); background:var(--paper); border:1px solid var(--line-strong); border-radius:999px;
  padding:3px 9px; letter-spacing:0.02em; text-transform:uppercase;
}
```

- [ ] **Step 5: Deploy backend (needed for `/voorbeeld/forecast` to work) and set `VOORBEELD_STORE_ID`**

Deploy Task 2's backend change if not already live (see Task 2 Step 6-equivalent in Task 5 below), then set the example store id in production. Pick any real `store_id` present in the currently-loaded model artifact's `historie["Store"]` (e.g. `1`, consistent with every test fixture in this plan) by adding to the server's `.env`:

```bash
ssh job@157.90.244.24 "echo 'VOORBEELD_STORE_ID=1' >> /home/job/forecasting-demo/deploy/.env"
ssh job@157.90.244.24 "cd /home/job/forecasting-demo/deploy && docker compose up -d"
```

- [ ] **Step 6: Deploy frontend and browser-verify**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/dashboard/onboarding.js \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/index.html \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/dashboard.js \
    /Users/hamdeco/development/hamdoun/forecasting/dashboard/styles.css \
    job@157.90.244.24:/home/job/forecasting-demo/dashboard/
```

Using claude-in-chrome, log in as the same self-serve, zero-store organisation used in Task 3's verification, navigate to `index.html`, and verify:
- The winkel-select is empty, the existing "Er zijn nog geen winkels..." message shows, and directly below it the "Voorbeeld" card renders with a real euro figure and range (not an error, not stuck on nothing).
- Log in as a "lid" role on an org with zero assigned stores — confirm the voorbeeld card does NOT appear (only the lid-specific message does), matching the `me.rol !== "lid"` guard in Step 3.
- Log in as the existing demo org (real winkels) — confirm `index.html` behaves exactly as before (no voorbeeld card, no regression to the normal forecast flow).

- [ ] **Step 7: Commit**

```bash
git add dashboard/onboarding.js dashboard/index.html dashboard/dashboard.js dashboard/styles.css
git commit -m "feat: show example forecast on index.html for self-serve orgs with no stores"
```

---

### Task 5: Deploy backend to production and run full live verification

**Files:** none (deploy + verification only)

**Interfaces:** none new — this task exercises everything built in Tasks 1-4 together, end to end.

- [ ] **Step 1: Deploy the backend changes from Tasks 1 and 2**

```bash
scp /Users/hamdeco/development/hamdoun/forecasting/serving/config.py \
    /Users/hamdeco/development/hamdoun/forecasting/serving/app.py \
    job@157.90.244.24:/home/job/forecasting-demo/serving/
ssh job@157.90.244.24 "cd /home/job/forecasting-demo/deploy && docker compose build api && docker compose up -d"
```

(If Task 4 Step 5 already ran `docker compose up -d` with `VOORBEELD_STORE_ID` set after this same `serving/` sync, this step may already be satisfied — confirm via Step 2 below rather than assuming.)

- [ ] **Step 2: Smoke-test the new endpoint directly**

```bash
ssh job@157.90.244.24 "docker compose -f /home/job/forecasting-demo/deploy/docker-compose.yml ps"
curl -s -o /dev/null -w "%{http_code}\n" https://forecasting-demo.tessar.nl/voorbeeld/forecast
```

Expected: container `Up`/healthy; the curl (no session cookie) returns `401`.

- [ ] **Step 3: Full cross-page live verification with claude-in-chrome**

Repeat, on the live production domain `https://forecasting-demo.tessar.nl`, the same three verification passes already described in Task 3 Step 6 and Task 4 Step 6 (self-serve zero-store eigenaar sees checklist + voorbeeld card and both clear correctly; self-serve lid with no assignment sees only the lid message, no voorbeeld card; existing demo org sees neither piece and has zero regressions on any of the three pages). This step exists to catch anything that differs between the Docker-container test environment used in Tasks 1-2 and the real production deployment (env vars, model artifact contents, Caddy routing) — do not skip it even though the individual pieces were already browser-verified per-task.

- [ ] **Step 4: Update project memory**

Once verification passes, record in memory (per the existing `forecasting_toolkit_audit_roadmap` memory) that the onboarding sub-project of the "tier omhoog" initiative is shipped and live, and that the other two decomposed sub-projects (verkoopklaarheid, productdiepte) remain open for a future brainstorming round.

---

## Self-Review

**Spec coverage:** Every spec section has a task — `voorbeeld_store_id` setting (Task 1) and `GET /voorbeeld/forecast` (Task 2) cover Architecture §1; the checklist (Task 3) covers Architecture §2; `onboarding.js`'s two functions, the markup additions, and the CSS all match Components exactly; the `GET /winkels` empty-list trigger and the eigenaar/lid split are wired in Tasks 3-4 per Data flow; silent-fail frontend + clean 503 backend are implemented in Tasks 2-4 per Error handling; Task 2 covers the full backend TDD matrix from Testing, Tasks 3-4-5 cover the live-verification matrix from Testing.

**Placeholder scan:** No TBD/TODO markers; every step has real, complete code; no step says "similar to Task N" without inline code.

**Type consistency:** `initOnboarding(me)` (Task 3) and `toonVoorbeeldVoorspelling()` (Task 4) signatures match between their definition in `onboarding.js` and their call sites in `overview.js`/`dashboard.js`/`account.js`. `ForecastResponse`/`DagVoorspelling` field names used in Task 2's endpoint and Task 4's frontend fetch (`store_id`, `voorspellingen`, `datum`, `p10`, `p50`, `p90`) match the existing schema already used identically by the `/forecast` endpoint and `dashboard.js`'s own chart-rendering code elsewhere in this codebase.
