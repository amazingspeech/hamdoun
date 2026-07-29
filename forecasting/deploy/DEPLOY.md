# Live deployment — kwantiq.tessar.nl

Dit stappenplan zet de vraagvoorspelling-demo live op de bestaande
Hetzner-server (`157.90.244.24`), naast de al draaiende Certo/n8n-stack,
zonder die stack aan te raken.

**Vereist voordat je begint:**
- SSH-toegang tot `157.90.244.24`.
- Een DNS A-record voor `kwantiq.tessar.nl` naar dat IP — moet al
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
# Zet MODEL_VERSION op de versie uit stap 2, APP_BASIS_URL op
# https://kwantiq.tessar.nl, en de MAIL_SMTP_*-waarden (nodig voor
# wachtwoord-reset én de wekelijkse herbestel-mail — zie .env.example voor
# uitleg per variabele). Laat STRIPE_SECRET_KEY/STRIPE_PRICE_ID/
# STRIPE_PRICE_ID_EXTRA_LID/STRIPE_PRICE_ID_EXTRA_WINKEL/
# STRIPE_WEBHOOK_SECRET leeg tenzij je bewust self-serve signup met een
# geverifieerd live Stripe-account wilt aanzetten — leeg = POST /signup
# geeft een nette 503, verder werkt alles normaal. Alle vijf moeten samen
# gezet zijn, anders blijft self-serve aanmelden uit.
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

**Caddy draait hier als container** (`tessar-caddy-1`, onderdeel van de
losstaande `~/tessar/docker-compose.yml`-stack die ook n8n en Certo's
`protocolwijzer` draait), niet als host-proces — er is dus geen
`sudo caddy reload` beschikbaar, en `reverse_proxy 127.0.0.1:<poort>` zou
vanuit die container naar zichzelf wijzen, niet naar de host. In plaats
daarvan krijgt de forecasting-`api`-container een plek op een gedeeld
extern Docker-netwerk, zodat Caddy 'm bij naam kan bereiken.

**Vereist:** het DNS A-record voor `kwantiq.tessar.nl` moet al
actief zijn (zie de vereisten bovenaan dit document) — zonder geldige DNS
kan Caddy straks geen HTTPS-certificaat voor dit blok ophalen.

Eenmalig het gedeelde netwerk aanmaken (idempotent — als het al bestaat,
geeft dit commando een onschuldige foutmelding):
```bash
docker network create caddy-net
```

`forecasting/deploy/docker-compose.yml` heeft dit netwerk al als extern
gedeclareerd (zie dat bestand) — geen aanpassing nodig zolang je met de
huidige broncode werkt. Voeg de forecasting-app toe aan de bestaande,
gedeelde Caddyfile:
```bash
cd /home/job/tessar
cp docker-compose.yml docker-compose.yml.bak-$(date +%Y%m%d-%H%M%S)
```
Open `~/tessar/docker-compose.yml` en voeg aan de `caddy`-service toe:
```yaml
    networks:
      - default
      - caddy-net
```
en onderaan het bestand (naast de bestaande `volumes:`-sectie):
```yaml
networks:
  default: {}
  caddy-net:
    external: true
```
Voeg de inhoud van `/home/job/forecasting-demo/deploy/Caddyfile-snippet`
toe aan `~/tessar/Caddyfile` (naast de blokken voor
`vandijkprotocol.tessar.nl` en `n8n.tessar.nl`) — die snippet gebruikt al
`reverse_proxy api:8000`, niet een hostpoort.

Herstart **alleen** de caddy-container om de netwerkwijziging en de
nieuwe config op te pikken — dit raakt n8n/postgres/protocolwijzer niet,
maar geeft een paar seconden onderbreking voor wie op dat moment
`n8n.tessar.nl` of `vandijkprotocol.tessar.nl` gebruikt:
```bash
docker compose up -d caddy
```
Controleer **meteen** dat Certo (`vandijkprotocol.tessar.nl`) en n8n
(`n8n.tessar.nl`) nog steeds normaal bereikbaar zijn — vóórdat je verder
gaat naar stap 7. Bij problemen: `docker compose logs caddy` bekijken, en
zo nodig `docker-compose.yml.bak-<tijdstip>` terugzetten en de
caddy-container opnieuw starten.

## 7. Verifiëren

Open `https://kwantiq.tessar.nl/login.html` in een browser en log
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

## 8. Wekelijkse herbestel-mail inplannen (Fase 5 NODIG 3)

Geen scheduler in de app zelf (bewust — geen extra always-on service voor
deze schaal) — een cron-regel op de host draait `serving.herbestel_email_cli`
elke maandagochtend binnen de al draaiende `api`-container:
```bash
crontab -e
# 0 7 * * 1 cd /home/job/forecasting-demo && docker compose exec -T api \
#   python3 -m serving.herbestel_email_cli >> /home/job/forecasting-demo/herbestel-mail.log 2>&1
```
Vereist dat `MAIL_SMTP_*` in `.env` staat (stap 3) — zonder mailconfig
verstuurt `security/mail.py` simpelweg niets (elke organisatie wordt dan
overgeslagen met een `MailNietGeconfigureerd`-regel in het logbestand,
geen crash). Test één keer handmatig vóór je de cron-regel aanzet:
```bash
docker compose exec api python3 -m serving.herbestel_email_cli
```

## 9. Dagelijkse opschoning van gedeactiveerde organisaties inplannen (AVG)

Zelfde patroon als stap 8 — een cron-regel op de host draait
`db.opschonen_cli` elke nacht binnen de al draaiende `api`-container. Dit
verwijdert organisaties **definitief en onomkeerbaar** (AVG-vereiste, zie
`FASE4-SAAS-FOUNDATION.md` beslissing 9) 30 dagen nadat Stripe
`customer.subscription.deleted` meldde.

**Waarschuwing — handmatige reactivatie:** als een operator een
gedeactiveerde organisatie handmatig rechtzet (bv. een ten onrechte
opgezegd abonnement), MOET dat via `db.organisaties.heractiveer_organisatie()`
gebeuren — niet via een kale `UPDATE organisaties SET actief=1`. Directe SQL
moet in dezelfde statement ook `gedeactiveerd_op = NULL` zetten. Zonder dat
blijft de oude `gedeactiveerd_op`-tijdstempel staan, en komt de organisatie
bij een volgende suspensie meteen, met nul dagen respijt, in aanmerking voor
deze onomkeerbare verwijdering.
```bash
crontab -e
# 0 3 * * * cd /home/job/forecasting-demo && docker compose -f deploy/docker-compose.yml exec -T api \
#   python3 -m db.opschonen_cli >> /home/job/forecasting-demo/opschonen.log 2>&1
```
Dagelijks, niet wekelijks zoals stap 8 — een verwijdering hoeft niet
wekenlang na de wachtperiode te blijven hangen. Test één keer handmatig
vóór je de cron-regel aanzet (vanuit `/home/job/forecasting-demo/deploy`,
zelfde aangenomen werkmap als de handmatige test in stap 8 hierboven):
```bash
cd /home/job/forecasting-demo/deploy
docker compose exec api python3 -m db.opschonen_cli
```
Verwacht bij een lege/verse database: `0 organisatie(s) verwijderd uit
tenants.db: (geen)`.

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
- **Self-serve signup (Fase 5 NODIG 5) staat bewust uit bij een eerste
  soft-launch.** Zonder `STRIPE_SECRET_KEY`/`STRIPE_PRICE_ID`/
  `STRIPE_PRICE_ID_EXTRA_LID`/`STRIPE_PRICE_ID_EXTRA_WINKEL` in `.env`
  geeft `POST /signup` een nette 503 — alleen de handmatig gebootstrapte
  organisatie(s) uit stap 3 kunnen inloggen. Pas invullen zodra het
  Stripe-account voor live-modus geverifieerd is (zie `.env.example`).
  Wachtwoord-reset en de wekelijkse herbestel-mail werken hier los van —
  die hebben alleen `MAIL_SMTP_*` en `APP_BASIS_URL` nodig, geen Stripe.
