# Forecasting Live Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare (but not yet activate) live deployment of the forecasting demo at `forecasting-demo.tessar.nl`, isolated from the production Certo/n8n stack on the same server, plus fix a dashboard bug that would break every demo visit.

**Architecture:** A new, self-contained `forecasting/deploy/` directory (its own Docker Compose project, a Caddyfile snippet to append to the server's shared Caddy config, an `.env.example`, and an exact runbook) — none of it touches the existing Certo `docker-compose.yml`. Two code fixes ride along: the `Dockerfile` gets the Linux OpenMP dependency it was silently missing, and the dashboard's default forecast date gets derived from the model's actual training period instead of the browser's calendar date.

**Tech Stack:** Same as the existing `forecasting/` toolkit (FastAPI, XGBoost, pytest) plus Docker Compose and Caddy for deployment.

## Global Constraints

- No task in this plan modifies the existing production `docker-compose.yml` used by Certo/n8n/Postgres — only additive changes to the shared Caddyfile (a snippet to append, applied via `caddy reload`, never `restart`).
- The live rate limit is shared democapacity, not a per-visitor limit — the public dashboard uses one shared API key, so the per-key rate limiter (fixed in the toolkit's final review) collapses to one bucket for all visitors. Document this explicitly wherever the rate limit value is set.
- CORS stays closed (empty allow-list) — dashboard and API are same-origin in this deployment; never set `CORS_ALLOWED_ORIGINS` to a wildcard.
- Encryption-at-rest stays off (`FORECASTING_ENCRYPT_AT_REST=false`) — public demo data, not client data.
- No task actually runs `docker compose up -d` against the live server — this plan prepares files and a runbook only; go-live is a manual, later step gated on real Rossmann-trained metrics (per the design spec).
- The Docker image has never been built (no Docker available on the local dev machine) — every claim about it must say so honestly; verification happens for the first time on the server itself, as an explicit, watched step in the runbook.

---

## Task 1: `MetricsResponse.trainingsperiode_eind`

**Files:**
- Modify: `forecasting/serving/schemas.py`
- Modify: `forecasting/serving/app.py:122-130`
- Modify: `forecasting/tests/test_schemas.py`
- Modify: `forecasting/tests/test_app.py:101-108`

**Interfaces:**
- Consumes: `training.artifact.laad_artefact`'s returned `metadata` dict, which already has a `"trainingsperiode_eind"` key (an ISO-8601 datetime string like `"2015-06-30T00:00:00"`, written by `training/artifact.py`'s `schrijf_artefact`) — this task does not touch `training/artifact.py`.
- Produces: `MetricsResponse.trainingsperiode_eind: date`, present in the JSON response of `GET /metrics`.

- [ ] **Step 1: Add a failing test for the new field in `test_schemas.py`**

Append to `forecasting/tests/test_schemas.py`:

```python
def test_metrics_response_bevat_trainingsperiode_eind():
    response = MetricsResponse(
        model_versie="20260101T000000Z", rmspe=0.12, coverage_p10_p90=0.81,
        n_observaties=1000, gevalideerde_horizon_dagen=48,
        trainingsperiode_eind="2015-06-30",
    )
    assert response.model_dump(mode="json")["trainingsperiode_eind"] == "2015-06-30"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd forecasting && source .venv/bin/activate && pytest tests/test_schemas.py::test_metrics_response_bevat_trainingsperiode_eind -v`
Expected: FAIL — `pydantic.ValidationError: ... trainingsperiode_eind Field required` (the field doesn't exist yet on `MetricsResponse`).

- [ ] **Step 3: Add the field to `MetricsResponse`**

In `forecasting/serving/schemas.py`, replace:

```python
class MetricsResponse(BaseModel):
    model_versie: str
    rmspe: float
    coverage_p10_p90: float
    n_observaties: int
    gevalideerde_horizon_dagen: int
```

with:

```python
class MetricsResponse(BaseModel):
    model_versie: str
    rmspe: float
    coverage_p10_p90: float
    n_observaties: int
    gevalideerde_horizon_dagen: int
    trainingsperiode_eind: date
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_schemas.py -v`
Expected: all tests pass, including the new one.

- [ ] **Step 5: Update `test_app.py`'s existing metrics test to expect the new field (RED)**

In `forecasting/tests/test_app.py`, replace the body of `test_metrics_geeft_gevalideerde_cijfers` (currently lines 101-108):

```python
def test_metrics_geeft_gevalideerde_cijfers(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.get("/metrics", headers={"X-API-Key": "test-key-123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["rmspe"] == 0.15
    assert data["coverage_p10_p90"] == 0.79
```

with:

```python
def test_metrics_geeft_gevalideerde_cijfers(tmp_path, monkeypatch):
    client = _bouw_test_omgeving(tmp_path, monkeypatch)
    resp = client.get("/metrics", headers={"X-API-Key": "test-key-123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["rmspe"] == 0.15
    assert data["coverage_p10_p90"] == 0.79
    assert data["trainingsperiode_eind"] == "2015-06-30"
```

(The fixture already calls `artifact.schrijf_artefact(..., trainingsperiode=(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-06-30")), ...)` at `test_app.py:24-30` — so `"2015-06-30"` is already the real value that will be written to `metadata.json`; no fixture change needed.)

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_app.py::test_metrics_geeft_gevalideerde_cijfers -v`
Expected: FAIL — `KeyError: 'trainingsperiode_eind'` (the `/metrics` endpoint doesn't return this field yet).

- [ ] **Step 7: Wire the field through in `serving/app.py`**

In `forecasting/serving/app.py`, replace the body of the `metrics` function (currently lines 122-130):

```python
def metrics(key_naam: str = Depends(vereis_api_key)) -> MetricsResponse:
    m = artefact["metadata"]
    return MetricsResponse(
        model_versie=m["versie"],
        rmspe=m["metrics"]["rmspe"],
        coverage_p10_p90=m["metrics"]["coverage_p10_p90"],
        n_observaties=m["metrics"]["n_observaties"],
        gevalideerde_horizon_dagen=m["gevalideerde_horizon_dagen"],
    )
```

with:

```python
def metrics(key_naam: str = Depends(vereis_api_key)) -> MetricsResponse:
    m = artefact["metadata"]
    return MetricsResponse(
        model_versie=m["versie"],
        rmspe=m["metrics"]["rmspe"],
        coverage_p10_p90=m["metrics"]["coverage_p10_p90"],
        n_observaties=m["metrics"]["n_observaties"],
        gevalideerde_horizon_dagen=m["gevalideerde_horizon_dagen"],
        trainingsperiode_eind=m["trainingsperiode_eind"][:10],
    )
```

`m["trainingsperiode_eind"]` is the full ISO-8601 datetime string written by `training/artifact.py` (e.g. `"2015-06-30T00:00:00"`). Slicing the first 10 characters extracts `"2015-06-30"` explicitly rather than relying on Pydantic to coerce a datetime-shaped string into a `date` field — a deliberate, unambiguous choice over an implicit one.

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_schemas.py tests/test_app.py -v`
Expected: all pass, including `test_metrics_response_bevat_trainingsperiode_eind` and the updated `test_metrics_geeft_gevalideerde_cijfers`.

- [ ] **Step 9: Run the full suite**

Run: `pytest -v`
Expected: all 85 tests pass (83 baseline + the 1 new test in this task; `test_metrics_geeft_gevalideerde_cijfers` is a modification, not a new test).

- [ ] **Step 10: Commit**

```bash
git add forecasting/serving/schemas.py forecasting/serving/app.py \
        forecasting/tests/test_schemas.py forecasting/tests/test_app.py
git commit -m "forecasting: expose trainingsperiode_eind on /metrics"
```

---

## Task 2: Dashboard default start date

**Files:**
- Modify: `forecasting/dashboard/dashboard.js`

**Interfaces:**
- Consumes: `GET /metrics`'s `trainingsperiode_eind` field (produced by Task 1) — the response shape returned by `laadMetrics()`.
- Produces: the `#start` date input defaults to the day after `trainingsperiode_eind` once metrics load, instead of staying on tomorrow's calendar date.

No automated test — the dashboard has no JS test framework by design (see the original plan's Task 16, which established manual/curl verification as the pattern for this file). This task follows the same convention.

- [ ] **Step 1: Add a helper function and wire it into the metrics-load flow**

In `forecasting/dashboard/dashboard.js`, add this function (place it near `vandaagPlusEen`, which it replaces as the source of truth once metrics load):

```javascript
function eenDagNa(isoDatum) {
  const d = new Date(isoDatum + "T00:00:00");
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}
```

Then replace the `DOMContentLoaded` handler (currently):

```javascript
document.addEventListener("DOMContentLoaded", () => {
  vulWinkelSelect();
  document.getElementById("start").value = vandaagPlusEen();
  document.getElementById("voorspel").addEventListener("click", voorspel);
  laadMetrics().catch((e) => toonFout(e.message));
});
```

with:

```javascript
document.addEventListener("DOMContentLoaded", () => {
  vulWinkelSelect();
  document.getElementById("start").value = vandaagPlusEen();
  document.getElementById("voorspel").addEventListener("click", voorspel);
  laadMetrics()
    .then((data) => {
      document.getElementById("start").value = eenDagNa(data.trainingsperiode_eind);
    })
    .catch((e) => toonFout(e.message));
});
```

`vandaagPlusEen()` still runs first as an immediate, always-valid fallback (so the input is never blank), then gets overridden with the training-period-aware date once `/metrics` resolves. If `/metrics` fails, the fallback stays and `toonFout` shows the error — same failure behavior as before this change.

- [ ] **Step 2: Manual verification**

This requires a running server with a real artifact — reuse the same setup as the original Task 16/Task 20 manual checks:

```bash
cd forecasting
source .venv/bin/activate
# (assumes a trained artifact, API key, and env vars are already set up —
# see forecasting/README.md sections 2-3, or reuse a prior local test setup)
uvicorn serving.app:app --reload
```

Open `http://127.0.0.1:8000/` in a browser (or re-check via curl: `curl -s http://127.0.0.1:8000/metrics -H "X-API-Key: <jouw-key>"` and confirm the response includes `trainingsperiode_eind`). In the browser, confirm the "Startdatum" field shows the day after the training period ends (e.g. `2015-07-01` if `trainingsperiode_eind` is `2015-06-30`), not tomorrow's real-world date.

- [ ] **Step 3: Commit**

```bash
git add forecasting/dashboard/dashboard.js
git commit -m "forecasting: default dashboard start date to training period end + 1 day"
```

---

## Task 3: Dockerfile `libgomp1` fix + `.dockerignore`

**Files:**
- Modify: `forecasting/Dockerfile`
- Create: `forecasting/.dockerignore`

**Interfaces:** none — this task doesn't change any Python interface, only the container build.

No automated test possible — Docker isn't installed on this development machine. This is stated honestly rather than skipped silently; real verification happens in Task 6's runbook, on the server, as an explicit build-and-test step before going live.

- [ ] **Step 1: Add the `libgomp1` install step to the Dockerfile**

Replace the full contents of `forecasting/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY security/ ./security/
COPY pipeline/ ./pipeline/
COPY training/ ./training/
COPY serving/ ./serving/
COPY dashboard/ ./dashboard/

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

`libgomp1` provides `libgomp.so.1`, the Linux OpenMP runtime XGBoost's compiled extension links against — `python:3.11-slim` is Debian-based and does not include it by default. This is the direct Linux analog of the `libomp.dylib` problem already solved for local macOS development (see `forecasting/.venv/bin/activate`'s `DYLD_LIBRARY_PATH` addition) — same root cause (XGBoost needs an OpenMP runtime the base OS doesn't ship), different OS-specific fix.

- [ ] **Step 2: Add `.dockerignore` to keep the build context small and avoid baking in dev-only files**

Create `forecasting/.dockerignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
tests/
data/
models/
.env
api_keys.json
audit.log
deploy/
```

`models/`, `api_keys.json`, and `audit.log` are bind-mounted at container runtime (see Task 4's `docker-compose.yml`), so excluding them from the build context is safe — nothing depends on them being baked into the image. `deploy/` is excluded because it contains the deployment configuration itself, not application code the container needs.

- [ ] **Step 3: State what could not be verified**

No build/run step here — write this down in the task's commit message rather than skip it silently (see Step 4). Verification happens in Task 6.

- [ ] **Step 4: Commit**

```bash
git add forecasting/Dockerfile forecasting/.dockerignore
git commit -m "$(cat <<'EOF'
forecasting: add libgomp1 for XGBoost on Linux, add .dockerignore

Not build-tested locally (no Docker on this dev machine) — this is
the Linux analog of the libomp.dylib fix already applied to the local
macOS venv. First real verification happens in the deploy runbook
(Task 6), as an explicit, watched build-and-run step before going live.
EOF
)"
```

---

## Task 4: `deploy/docker-compose.yml` + `deploy/.env.example`

**Files:**
- Create: `forecasting/deploy/docker-compose.yml`
- Create: `forecasting/deploy/.env.example`

**Interfaces:**
- Consumes: `forecasting/Dockerfile` (Task 3) as the build source; `serving/config.py`'s environment variables (`MODEL_VERSION`, `MODELS_DIR`, `API_KEYS_FILE`, `AUDIT_LOG_FILE`, `CORS_ALLOWED_ORIGINS`, `FORECASTING_ENCRYPT_AT_REST`, `FORECASTING_ENCRYPTIE_SLEUTEL`, `RATE_LIMIT_PER_MINUUT` — all already defined and hard-failing on missing required values, per `serving/config.py`).
- Produces: a `docker compose -f deploy/docker-compose.yml ...` project, run from `forecasting/deploy/` on the server, that Task 6's runbook references by exact path and command.

No automated test — this is infrastructure configuration, verified for the first time on the server in Task 6.

- [ ] **Step 1: Write `forecasting/deploy/docker-compose.yml`**

```yaml
services:
  api:
    build:
      context: ..
    ports:
      - "8010:8000"
    env_file:
      - .env
    volumes:
      - ../models:/app/models
      - ../dashboard:/app/dashboard
      - ../api_keys.json:/app/api_keys.json
      - ../audit.log:/app/audit.log
    restart: unless-stopped
```

Notes for whoever reads this later:
- `context: ..` means this must be run from `forecasting/deploy/` with the full `forecasting/` tree present alongside it on the server (via Task 6's `rsync` step) — not just this one file copied in isolation.
- Port `8010` (not `8000`) is the host-side port Caddy will reverse-proxy to (see Task 5) — chosen to avoid colliding with Certo's existing `8420` on the same server.
- `../dashboard:/app/dashboard` is a bind mount, not baked into the image at build time (the `Dockerfile` still `COPY`s it for the case where this file isn't used, e.g. local dev) — this lets the API key be added to `dashboard/index.html` on the server (Task 6, step 7) without rebuilding the image.
- No `training` service here (unlike the local dev `forecasting/docker-compose.yml`) — per the design spec, training never runs on the server; only a pre-trained artifact gets copied in.

- [ ] **Step 2: Write `forecasting/deploy/.env.example`**

```
MODEL_VERSION=
MODELS_DIR=models
API_KEYS_FILE=api_keys.json
AUDIT_LOG_FILE=audit.log
CORS_ALLOWED_ORIGINS=
FORECASTING_ENCRYPT_AT_REST=false
FORECASTING_ENCRYPTIE_SLEUTEL=
# Gedeelde democapaciteit, GEEN per-bezoeker-limiet: het publieke dashboard
# gebruikt één gedeelde API-key voor alle bezoekers, dus de per-key
# rate-limiter (serving/app.py) valt terug op één gezamenlijke bucket voor
# iedereen die de demo tegelijk gebruikt. Zet dit ruim genoeg voor een paar
# gelijktijdige bezoekers — niet zo streng dat de tweede bezoeker al
# geblokkeerd wordt door de eerste.
RATE_LIMIT_PER_MINUUT=90
```

- [ ] **Step 3: Commit**

```bash
git add forecasting/deploy/docker-compose.yml forecasting/deploy/.env.example
git commit -m "forecasting: add isolated production Docker Compose project"
```

---

## Task 5: `deploy/Caddyfile-snippet`

**Files:**
- Create: `forecasting/deploy/Caddyfile-snippet`

**Interfaces:**
- Consumes: port `8010` from Task 4's `docker-compose.yml`.
- Produces: a block to be appended (by hand, on the server) to the existing shared Caddyfile that already routes Certo (`vandijkprotocol.tessar.nl`) and n8n (`n8n.tessar.nl`) — referenced by Task 6's runbook.

- [ ] **Step 1: Write `forecasting/deploy/Caddyfile-snippet`**

```
# Toe te voegen aan de bestaande, gedeelde Caddyfile op de server
# (naast de blokken voor vandijkprotocol.tessar.nl en n8n.tessar.nl).
# Zelfde stijl/headers als Certo's blok — zie DEPLOY.md voor de precieze
# toepas-stappen (caddy validate, dan caddy reload — nooit restart).

forecasting-demo.tessar.nl {
	reverse_proxy 127.0.0.1:8010

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
		output file /var/log/caddy/forecasting-demo.log
		format json
	}
}
```

`script-src 'self'` (without `'unsafe-inline'`) is stricter than Certo's own CSP block, which allows inline scripts — `dashboard/index.html` has no inline `<script>` content (only the external `dashboard.js`), so the stricter policy is correct here and doesn't need loosening.

- [ ] **Step 2: Commit**

```bash
git add forecasting/deploy/Caddyfile-snippet
git commit -m "forecasting: add Caddy config snippet for forecasting-demo.tessar.nl"
```

---

## Task 6: `deploy/DEPLOY.md`

**Files:**
- Create: `forecasting/deploy/DEPLOY.md`

**Interfaces:**
- Consumes: everything from Tasks 1-5 (references exact file paths, port `8010`, the `.env.example` contents, the Caddyfile snippet).
- Produces: the exact, ordered runbook a human follows to actually go live — this task writes the document only; no step in this task executes anything against the real server.

- [ ] **Step 1: Write `forecasting/deploy/DEPLOY.md`**

```markdown
# Live deployment — forecasting-demo.tessar.nl

Dit stappenplan zet de vraagvoorspelling-demo live op de bestaande
Hetzner-server (`157.90.244.24`), naast de al draaiende Certo/n8n-stack,
zonder die stack aan te raken.

**Vereist voordat je begint:**
- SSH-toegang tot `157.90.244.24`.
- Een DNS A-record voor `forecasting-demo.tessar.nl` naar dat IP — moet al
  actief zijn vóórdat Caddy een geldig HTTPS-certificaat kan ophalen.
- Een lokaal getraind modelartefact, getraind op **echte** Rossmann-data
  (niet de synthetische testdata — zie `forecasting/README.md` secties 1-2).
  Ga hier pas doorheen zodra dat er is.

## 1. Broncode naar de server

Vanaf je lokale machine, vanuit de repo-root:
```bash
ssh job@157.90.244.24 "mkdir -p /home/job/forecasting-demo/models"
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  --exclude 'data' --exclude 'models' --exclude 'api_keys.json' \
  --exclude 'audit.log' --exclude '.env' \
  forecasting/ job@157.90.244.24:/home/job/forecasting-demo/
```

## 2. Modelartefact overzetten

```bash
scp -r forecasting/models/<versie> job@157.90.244.24:/home/job/forecasting-demo/models/
```
(Vervang `<versie>` door de map-naam die `training.cli` printte, bv.
`20260101T000000Z`.)

## 3. `.env` en API-key op de server aanmaken

Op de server:
```bash
cd /home/job/forecasting-demo/deploy
cp .env.example .env
nano .env
# Zet MODEL_VERSION op de versie uit stap 2.
```

API-key genereren (dezelfde key komt in stap 7 in het dashboard-JS):
```bash
cd /home/job/forecasting-demo/deploy
docker compose run --rm api python3 -c "
from pathlib import Path
from security import api_keys
api_keys.voeg_key_toe(Path('/app/api_keys.json'), 'publieke-demo', 'ZET-HIER-EEN-EIGEN-WILLEKEURIGE-KEY-NEER')
"
```
(`--rm api` bouwt en start de container kort om het commando uit te voeren
en verwijdert 'm daarna weer — dit is dezelfde image die straks ook live
draait, dus dit is meteen een eerste rooktest dat de image kan bouwen.)

## 4. Bouw en test de image LOS, vóórdat je live gaat

Dit is nooit lokaal getest (geen Docker beschikbaar op de ontwikkelmachine)
— behandel de eerste build als een echte test, niet als een formaliteit:
```bash
cd /home/job/forecasting-demo/deploy
docker compose build
```
Controleer dat dit zonder fouten doorloopt. Start dan tijdelijk handmatig op
de voorgrond om te bevestigen dat de container ook echt opstart:
```bash
docker compose up
```
Verwacht in de logs: `Application startup complete.` — **geen**
`XGBoostError`, `libomp`, of `libgomp`-gerelateerde fouten (dat zou
betekenen dat de `libgomp1`-fix in de `Dockerfile` niet werkt zoals bedacht,
en verdere uitzoekwerk nodig heeft vóórdat je verdergaat). Stop met
`Ctrl+C` zodra bevestigd.

## 5. Live starten

```bash
docker compose up -d
curl http://127.0.0.1:8010/health
```
Verwacht: `{"status":"ok","model_versie":"<jouw versie>"}`.

## 6. Caddy: nieuw subdomein toevoegen

Voeg de inhoud van `/home/job/forecasting-demo/deploy/Caddyfile-snippet` toe
aan de bestaande, gedeelde Caddyfile (`/etc/caddy/Caddyfile` — waar ook
Certo's en n8n's blokken staan). Valideer vóór je herlaadt, en herlaad —
**nooit herstart**, want reload valideert eerst en behoudt de oude config
bij een fout, restart niet:
```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo caddy reload --config /etc/caddy/Caddyfile
```
Controleer meteen dat Certo (`vandijkprotocol.tessar.nl`) en n8n
(`n8n.tessar.nl`) nog steeds normaal bereikbaar zijn na deze stap.

## 7. Dashboard-API-key invullen

Het dashboard verwacht de key als globale JS-variabele, gezet vóór
`dashboard.js` laadt. Voeg in
`/home/job/forecasting-demo/dashboard/index.html`, vlak vóór de regel
`<script src="./dashboard.js"></script>`, dit toe:
```html
<script>
  window.TESSAR_FORECAST_API_KEY = "ZELFDE-KEY-ALS-STAP-3";
</script>
```
Geen rebuild of restart nodig: `dashboard/` is bind-gemount (zie
`deploy/docker-compose.yml`), dus de container serveert dit bestand direct
van schijf bij elk verzoek.

## 8. Verifiëren

Open `https://forecasting-demo.tessar.nl` in een browser. Kies een winkel,
klik "Voorspel". Controleer dat de startdatum automatisch op de dag ná de
trainingsperiode staat (niet op de kalenderdag van vandaag) — dat bevestigt
dat de `trainingsperiode_eind`-fix (zie het implementatieplan, Taken 1-2)
op de live server ook echt werkt, niet alleen lokaal.

## Bekende beperkingen van deze live opzet

Zie ook `forecasting/KNOWN-LIMITATIONS.md`. Specifiek voor deze deployment:
- **Geen live historiefeed.** Voorspellingen zijn geankerd aan de
  trainingsperiode van het geladen model, niet aan de actuele kalenderdag —
  dit is precies waarom stap 8 hierboven de datumstandaard controleert.
- **Gedeelde rate limit, geen per-bezoeker-limiet.** Eén publieke demo-key
  voor alle bezoekers — zie de comment in `deploy/.env.example`.
- **`requirements.txt` bevat nog de 9 bekende pip-audit-bevindingen** totdat
  het opnieuw gegenereerd wordt op een machine met Python ≥3.10 (zie
  `forecasting/KNOWN-LIMITATIONS.md`) — niet opgelost door deze deployment.
- **Model hertrainen = handmatig herhalen van stap 2-4** (nieuw artefact
  overzetten, `MODEL_VERSION` in `.env` bijwerken, `docker compose up -d`
  opnieuw) — geen automatische "laatste versie" promotie, met opzet (zie
  het oorspronkelijke ontwerp: nooit een impliciet gepromoveerd model).
```

- [ ] **Step 2: Commit**

```bash
git add forecasting/deploy/DEPLOY.md
git commit -m "forecasting: add live deployment runbook"
```

---

## Self-Review Notes

- **Spec coverage:** every file listed in the design spec's "Nieuwe/gewijzigde bestanden" table has a task (Dockerfile → Task 3, `deploy/docker-compose.yml` + `.env.example` → Task 4, `Caddyfile-snippet` → Task 5, `DEPLOY.md` → Task 6, `schemas.py`/`app.py` → Task 1, `dashboard.js` → Task 2). The two "openstaande risico's" from the spec (Kaggle access, untested Docker image) are handled honestly — Task 3 states the build is unverified locally, and `DEPLOY.md` makes the first real build an explicit, watched step rather than assuming success.
- **Placeholder scan:** no TBD/TODO; every code step contains complete, real content; `DEPLOY.md` is the actual runbook text, not a description of what a runbook should contain.
- **Type consistency:** `MetricsResponse.trainingsperiode_eind` (Task 1) is a `date`, matching `DagVoorspelling.datum` and `ForecastVerzoek.start_datum`'s existing `date` type in the same file — consistent with the schema's established conventions. `dashboard.js`'s `eenDagNa()` (Task 2) consumes the field as the ISO string the API actually serializes it as (confirmed via `model_dump(mode="json")` in Task 1's test), not a raw Python `date` object.
