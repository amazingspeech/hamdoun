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

`api_keys.json` blijft een verplicht bestand (zie `serving/config.py`) maar
hoeft sinds Fase 4 niet meer gevuld te zijn — klanten loggen zelf in via
het dashboard, dat gebruikt een sessiecookie, geen API-key. Een leeg
bestand (`{}`, zoals hierboven al aangemaakt) volstaat.

Eén organisatie bootstrappen (koppelt alle store-ID's uit het
modelartefact eraan):
```bash
docker compose run --rm api python3 -m db.cli \
  --models-dir /app/models --model-version <versie uit stap 2> \
  --database-pad /app/tenants.db \
  --organisatie-naam "<klantnaam>" --organisatie-slug <klant-slug>
```

Het eerste (eigenaar-)account voor die klant aanmaken, zodat ze zelf
kunnen inloggen — kies zelf een tijdelijk wachtwoord en geef dat apart
(niet per e-mail) door aan de klant:
```bash
docker compose run --rm api python3 -m db.gebruikers_cli \
  --database-pad /app/tenants.db --organisatie-slug <klant-slug> \
  --email <klant-e-mailadres> --wachtwoord <tijdelijk-wachtwoord> --rol eigenaar
```
Zonder dit account kan niemand inloggen — het dashboard redirect dan
permanent naar het inlogscherm. Eenmaal ingelogd kan de eigenaar zelf
teamleden toevoegen (`team.html`) en, alleen als een externe integratie
(bv. een kassasysteem) programmatische toegang nodig heeft, een eigen
API-key aanmaken — dat hoeft een operator niet meer handmatig te doen.

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

## 7. Verifiëren

Open `https://forecasting-demo.tessar.nl/login.html` in een browser en log
in met het account uit stap 3. Je wordt automatisch naar het dashboard
doorgestuurd (het dashboard vereist sinds deze stap een geldige sessie —
zonder login redirect het permanent naar `login.html`). Kies een winkel,
klik "Voorspel". Controleer dat:
- de startdatum automatisch op de dag ná de trainingsperiode staat (niet op
  de kalenderdag van vandaag) — bevestigt dat het juiste model geladen is;
- de winkellijst overeenkomt met wat er in stap 3 gebootstrapt is, niet een
  vaste testlijst.

Controleer ook dat `HTTPS` daadwerkelijk actief is (Caddy, stap 6) vóórdat
je inlogt: de sessiecookie krijgt de `Secure`-vlag (`SESSIE_COOKIE_SECURE`,
standaard aan — zie `serving/config.py`) en wordt door de browser
stilzwijgend niet verzonden over gewone `http://`, wat inloggen laat lijken
te werken maar elke volgende aanvraag alsnog met 401 laat falen.

## Bekende beperkingen van deze live opzet

Zie ook `forecasting/KNOWN-LIMITATIONS.md`. Specifiek voor deze deployment:
- **Geen live historiefeed.** Voorspellingen zijn geankerd aan de
  trainingsperiode van het geladen model, niet aan de actuele kalenderdag —
  dit is precies waarom stap 7 hierboven de datumstandaard controleert.
- **Rate limit is per organisatie, niet per losse gebruiker/key** (Fase 4
  Stap 7) — meerdere gelijktijdige gebruikers van dezelfde klant delen één
  budget. Zet `RATE_LIMIT_PER_MINUUT` ruim genoeg voor de grootste klant.
- **Docker-image gebruikt Python 3.11, `requirements.txt` is gegenereerd
  met Python 3.9** (zie de `pip-compile`-header in dat bestand) — dit
  bestond al vóór Fase 3's `shap`-toevoeging. Vooraf gecontroleerd (`pip
  download --platform manylinux2014_x86_64 --python-version 311
  --only-binary=:all:`) dat `shap`/`numba`/`llvmlite`/`cloudpickle`/
  `slicer`/`tqdm` allemaal een kant-en-klare wheel hebben voor deze
  combinatie — geen compiler nodig tijdens de build. **Nog steeds nooit
  lokaal met Docker getest** (geen Docker op de ontwikkelmachine), dus
  stap 4 hierboven blijft de eerste echte test — maar het risico op een
  mislukte build door deze specifieke dependencies is laag gebleken.
- **`requirements.txt` bevat nog eventuele bekende pip-audit-bevindingen**
  totdat het opnieuw gegenereerd wordt op een machine met Python ≥3.10 (zie
  `forecasting/KNOWN-LIMITATIONS.md`) — niet opgelost door deze deployment.
- **Model hertrainen = handmatig herhalen van stap 2-4** (nieuw artefact
  overzetten, `MODEL_VERSION` in `.env` bijwerken, `docker compose up -d`
  opnieuw) — geen automatische "laatste versie" promotie, met opzet (zie
  het oorspronkelijke ontwerp: nooit een impliciet gepromoveerd model).
