# Live deployment van de vraagvoorspelling-demo — design

Datum: 2026-07-26
Status: goedgekeurd, klaar voor implementatieplan

## Doel

De lokaal gebouwde vraagvoorspelling-toolkit (`forecasting/`, gemerged naar
`main` op 2026-07-25) live en publiek bereikbaar maken als demo voor
bezoekers van de Tessar-website, op `forecasting-demo.tessar.nl` — naast de
al bestaande Certo/n8n-stack op dezelfde Hetzner-server (`157.90.244.24`).

**Niet in scope voor deze fase:** het daadwerkelijk "aanzetten" (live
`docker compose up`) gebeurt pas zodra er een op echte Rossmann-data
getraind model is — de gebruiker heeft expliciet gekozen te wachten op
werkende Kaggle-toegang in plaats van live te gaan met de huidige
synthetische testdata (dekking van de p10–p90-band was daar maar 39%,
technisch verklaarbaar maar niet iets om aan een prospect te laten zien).
Deze fase bouwt en bereidt alles voor zodat het daarna alleen nog een
kwestie van bestanden overzetten en `docker compose up` is.

## Aanpak

**Los Docker Compose-project, gedeelde Caddy.** De forecasting-service komt
in een eigen `docker-compose.yml` (eigen map, eigen Compose-project), volledig
gescheiden van de bestaande `tessar`-stack die Certo/n8n/Postgres draait.
Caddy (al gedeeld voor alle subdomeinen op de server) krijgt één extra,
additieve regel voor `forecasting-demo.tessar.nl`, toegepast via
`caddy reload` — niet `restart`. Caddy valideert een nieuwe configuratie
vóór toepassing en behoudt de oude bij een fout, dus een tikfout in het
nieuwe blok kan Certo/n8n niet offline halen.

Overwogen alternatief: de service toevoegen aan de bestaande
`tessar`-stack (Certo's eigen `docker-compose.yml`) — afgewezen omdat elke
wijziging daaraan een wijziging is aan een bestand waar een echte, betalende
klant (Van Dijk Clinic) al op draait; een fout daarin kan in het ergste geval
de hele stack laten falen bij herstart. Maximale isolatie van productie
weegt zwaarder dan het beheersgemak van "alles in één compose-bestand."

## Model-artefact zonder Python op de server

We trainen **lokaal** (op deze ontwikkelmachine) zodra er werkende
Kaggle-toegang is, en zetten alleen het resulterende `models/<versie>/`-mapje
via `scp`/`rsync` over naar de server. De productiecontainer laadt en serveert
een al-getraind artefact; er hoeft nooit een trainings-toolchain op de server
te draaien. Dit vermijdt het risico dat we lokaal al tegenkwamen (een uur
kwijt aan het ontbreken van de OpenMP-runtime voor XGBoost op macOS) opnieuw
tegen te komen, nu in productie.

## Docker-image: gecorrigeerde risico's

Twee dingen die tijdens het ontwerp kritisch zijn nagelopen en niet eerder
geverifieerd waren (Task 17's review was puur statisch — Docker was lokaal
niet beschikbaar, er is nooit een echte `docker build` gedraaid):

1. **`libgomp1` ontbreekt waarschijnlijk in `python:3.11-slim`.** Dit is de
   Linux-tegenhanger van het macOS `libomp.dylib`-probleem dat we lokaal
   oplosten. XGBoost's Linux-wheels hebben `libgomp.so.1` nodig; Debian's
   slim-images bevatten dit niet standaard. Fix: `Dockerfile` krijgt
   `RUN apt-get update && apt-get install -y --no-install-recommends libgomp1
   && rm -rf /var/lib/apt/lists/*` vóór de pip-install.
2. **De image is nog nooit daadwerkelijk gebouwd.** `requirements.txt` is
   gegenereerd onder lokaal Python 3.9; of die exacte pins zonder problemen
   installeren onder de Python 3.11 van het image was nooit geverifieerd. Het
   deploy-stappenplan bevat daarom een expliciete, bewaakte "bouw en test de
   image eerst los"-stap vóór `docker compose up -d`, niet blind vertrouwen
   dat de eerste build meteen slaagt.

## Rate limiting voor een publieke, gedeelde demo-key

Het dashboard heeft een API-key nodig om de backend aan te roepen, maar
draait in de browser — de key staat zichtbaar in de paginabron. Gekozen
oplossing: een eigen, herroepbare demo-key (niet de aanpak met een
verbergende proxy — te veel bouwwerk voor wat uiteindelijk alleen publieke
demo-data serveert).

Belangrijke correctie tijdens het ontwerp: de rate-limiter (na de
whole-branch-review-fix) limiteert per API-key, niet per IP — bedoeld voor
meerdere klanten met elk hun eigen key. Bij één gedeelde publieke demo-key
delen **alle bezoekers tegelijk dezelfde rate-limit-bucket**. Het limiet
moet dus niet ingesteld worden als streng-per-bezoeker (bv. 20/minuut zou
een paar gelijktijdige bezoekers al laten blokkeren), maar als **totale
gedeelde democapaciteit** (bv. 90/minuut), met een duidelijke comment in
`.env.example` die dit uitlegt.

Overige beveiliging: CORS blijft dicht (lege allow-list — dashboard en API
zijn same-origin, geen andere origin nodig), encryptie-at-rest blijft uit
(publieke demo-data, geen klantgegevens), audit-logging staat aan zoals
overal in het project.

## Bekende bug die nu mee wordt opgelost: standaard-startdatum

Het dashboard zet de startdatum-invoer standaard op "morgen" (een
kalenderdag in 2026), terwijl elk getraind model geankerd is aan zijn eigen
trainingsperiode (voor Rossmann-data ergens medio 2015). Zonder fix krijgt
elke bezoeker die direct op "Voorspel" klikt een foutmelding. Dit was al
gesignaleerd als Minor bevinding in de eerdere whole-branch-review; nu
relevant genoeg om op te lossen vóór een publieke demo.

Oplossing:
- `serving/schemas.py`: `MetricsResponse` krijgt een extra veld
  `trainingsperiode_eind: date`.
- `serving/app.py`: geeft dat veld door vanuit de
  `metadata.json` (`metadata["trainingsperiode_eind"]` bestaat al —
  alleen nooit doorgegeven aan de API-response).
- `dashboard/dashboard.js`: haalt bij het laden van de metrics ook
  `trainingsperiode_eind` op, en zet de standaard-startdatum op die datum
  + 1 dag in plaats van op de kalenderdag van vandaag.
- Nieuwe/aangepaste tests voor beide wijzigingen, zelfde TDD-aanpak als de
  rest van het project.

## Nieuwe/gewijzigde bestanden

| Bestand | Wijziging |
|---|---|
| `forecasting/Dockerfile` | `libgomp1`-installatiestap toegevoegd |
| `forecasting/deploy/docker-compose.yml` | nieuw — geïsoleerd productie-Compose-project |
| `forecasting/deploy/.env.example` | nieuw — productiewaarden, incl. toelichting op gedeelde rate limit |
| `forecasting/deploy/Caddyfile-snippet` | nieuw — het ene blok voor de gedeelde Caddyfile |
| `forecasting/deploy/DEPLOY.md` | nieuw — exact, getest stappenplan (DNS, overzetten, bouwen/testen, live zetten) |
| `forecasting/serving/schemas.py` | `MetricsResponse.trainingsperiode_eind` |
| `forecasting/serving/app.py` | geeft `trainingsperiode_eind` door |
| `forecasting/dashboard/dashboard.js` | standaard-startdatum afgeleid van `trainingsperiode_eind` |
| `forecasting/tests/test_schemas.py`, `test_app.py` | tests voor bovenstaande |

## Volgorde naar live

1. **Nu:** bovenstaande bestanden bouwen en testen (dit implementatieplan).
2. **Zodra Kaggle-toegang werkt:** `train.csv`/`store.csv` downloaden, lokaal
   trainen, RMSPE/dekking controleren (net als bij de synthetische run).
3. **Overzetten:** `models/<versie>/` via `scp`/`rsync` naar de server.
4. **DNS:** A-record voor `forecasting-demo.tessar.nl` → `157.90.244.24`
   (door de gebruiker, buiten deze sessie om).
5. **Live zetten:** `DEPLOY.md` volgen op de server — bouwen, los testen,
   dan pas `docker compose up -d`; Caddyfile-snippet toevoegen, `caddy reload`.
6. **Linken vanaf de Tessar-website** naar `https://forecasting-demo.tessar.nl`
   (bv. vanuit de bestaande services.html/cases-sectie) — niet in scope van
   deze fase, aparte, latere stap.

## Openstaande risico's

1. Kaggle-download blijft geblokkeerd (Kaggle-zijdig "compressie
   bezig"-probleem, niet oplosbaar vanuit deze sessie) — blokkeert stap 2,
   niet de voorbereiding in deze fase.
2. De Docker-image is na de `libgomp1`-fix nog steeds niet lokaal getest
   (geen Docker beschikbaar op deze ontwikkelmachine) — de eerste echte test
   is de bewaakte build-stap op de server zelf, per `DEPLOY.md`.
