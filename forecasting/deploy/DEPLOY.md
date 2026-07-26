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

Maak eerst lege `api_keys.json`- en `audit.log`-bestanden aan op de server,
vóór de eerste `docker compose`-aanroep hieronder. `docker-compose.yml`
bind-mount deze twee bestanden vanaf de host; als ze nog niet bestaan maakt
Docker er in plaats daarvan een **directory** van, wat zowel het aanmaken
van de API-key hieronder als elke latere audit-log-write in de app breekt
(zelfde reden als `touch audit.log` in `forecasting/README.md` sectie 2).
De container draait als een niet-root gebruiker met een vaste UID (10001,
zie `Dockerfile`) die deze host-bestanden niet bezit (ze staan op naam van
`job`), dus moeten ze schrijfbaar zijn voor die container-gebruiker vóór de
eerste `docker compose run`/`up` hieronder — anders faalt zowel de
key-aanmaak in stap 3 als elke audit-log-write met een permission-fout.
Dit is een gedeelde productieserver (ook Certo/n8n) — geef daarom precies
UID 10001 eigenaarschap (`chown`) in plaats van de bestanden
wereldschrijfbaar te maken:
```bash
cd /home/job/forecasting-demo
touch api_keys.json audit.log tenants.db
sudo chown 10001:10001 api_keys.json audit.log tenants.db
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

Sinds Fase 4 Stap 2 verifieert de server keys via de database, niet meer
via `api_keys.json` — dat bestand blijft verplicht aanwezig (zie
`serving/config.py`), maar de key hierboven moet ook naar `tenants.db`.
Eén organisatie bootstrappen (koppelt alle store-ID's uit het
modelartefact eraan) en de zojuist aangemaakte key overzetten:
```bash
docker compose run --rm api python3 -m db.cli \
  --models-dir /app/models --model-version <versie uit stap 2> \
  --database-pad /app/tenants.db \
  --organisatie-naam "Publieke demo" --organisatie-slug publieke-demo
docker compose run --rm api python3 -m db.migreer_keys_cli \
  --api-keys-json /app/api_keys.json --database-pad /app/tenants.db \
  --organisatie-slug publieke-demo
```
Zonder deze twee stappen faalt elke `/forecast`/`/metrics`-aanroep met
401, ook met een geldige key in `api_keys.json`.

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
`dashboard.js` laadt. `index.html` laadt hiervoor al een `config.js` vóór
`dashboard.js` (zie `dashboard/index.html`) — dat bestand bestaat lokaal
niet (harmless 404, `window.TESSAR_FORECAST_API_KEY` blijft undefined) en
moet op de server aangemaakt worden.

**Niet** rechtstreeks in `index.html` plakken: `Caddyfile-snippet` zet een
strikte `Content-Security-Policy` met `script-src 'self'` en zonder
`'unsafe-inline'`, dus een inline `<script>`-blok in `index.html` wordt
door de browser stilzwijgend geblokkeerd — `window.TESSAR_FORECAST_API_KEY`
blijft dan undefined en elke `/forecast`/`/metrics`-aanroep faalt met 401,
zonder enige foutmelding die daar direct naar wijst. Een los, same-origin
bestand valt wél binnen `script-src 'self'`.

Maak op de server `/home/job/forecasting-demo/dashboard/config.js` aan
(nieuw bestand, niet `index.html` bewerken) met als inhoud:
```javascript
window.TESSAR_FORECAST_API_KEY = "ZELFDE-KEY-ALS-STAP-3";
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
