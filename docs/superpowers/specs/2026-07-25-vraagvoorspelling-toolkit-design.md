# Vraagvoorspelling-toolkit — design

Datum: 2026-07-25
Status: goedgekeurd, klaar voor implementatieplan

## Doel

Een herbruikbare, delivery-klare toolkit voor de dienst "Voorspellende modellen &
besluitondersteuning" (services.html, dienst 02). Fase 1 bouwt en valideert de
toolkit lokaal rond één concreet scenario: vraagvoorspelling voor retail. Het
resultaat moet zonder herontwerp kunnen doorgroeien naar (a) een interactieve
demo op de Tessar-website en (b) een echt klantproject met gevoelige data.

Niet in scope voor deze fase: live deployment naast Certo, en de daadwerkelijke
website-demo-integratie zelf. Beide zijn bewust latere, losse stappen.

## Aanpak

Drie ontkoppelde onderdelen in plaats van één alles-in-één service:

1. **Pipeline + training** (offline/batch) — bouwt en valideert het model, schrijft
   een geversied artefact weg met de bijbehorende nauwkeurigheidscijfers.
2. **Serving** (FastAPI, dun) — laadt een expliciet gepinde modelversie en
   beantwoordt voorspellingsverzoeken; traint nooit zelf.
3. **Dashboard** (statische frontend, Tessar-stijl) — praat uitsluitend via de
   API, configureerbaar API-adres. Dit is het stuk dat later grotendeels
   ongewijzigd op de website kan landen.

Deze scheiding is bewust: geen herberekening van het model per request,
reproduceerbare modelversies, en een dashboard dat al op zichzelf staat zodra
het een live API-adres krijgt.

Overwogen alternatieven:
- **Alles-in-één FastAPI-service** — sneller te bouwen, maar traint/laadt het
  model impliciet per request; geen bewuste promotiestap voor een nieuw model.
  Afgewezen.
- **Notebook/statisch rapport, geen live API** — voldoet niet aan de eigen
  dienstbelofte ("dashboard, API, of beide") en levert geen interactieve demo.
  Afgewezen.

## Data & model

- **Dataset:** Rossmann Store Sales (Kaggle), uitsluitend gebruikt om de
  methode te bouwen en te valideren — geen herpublicatie van ruwe cijfers.
  Puur winkel-niveau, **geen productdimensie** (kolommen: Store, DayOfWeek,
  Date, Sales, Customers, Open, Promo, StateHoliday, SchoolHoliday, plus
  winkelmetadata in store.csv).
- **Toegang:** vereist een Kaggle-account + API-token. Wordt als eerste
  implementatiestap geverifieerd; terugval is een synthetische dataset met
  vergelijkbare structuur (winkels, promoties, feestdagen, seizoenspatroon)
  als toegang niet lukt.
- **Licentie:** competitieregels worden bij implementatie daadwerkelijk
  gelezen (open punt, zie "Openstaande risico's"). Rossmann blijft in alle
  gevallen alleen de basis om de methode te bewijzen; de gevalideerde
  nauwkeurigheidscijfers (RMSPE, coverage) zijn statistieken, geen
  herpublicatie van de dataset. Voor een latere publieke website-demo tonen
  we geanonimiseerde/herschaalde of gekalibreerde synthetische waarden,
  nooit de ruwe Rossmann-cijfers zelf.
- **Model:** één globaal XGBoost-model over alle winkels heen (winkel-ID en
  featurewaarden als input), niet 1115 losse modellen — consistent met hoe de
  sterkste publieke oplossingen voor deze competitie zijn opgezet.
- **Onzekerheid:** naast het p50-model ook p10/p90-kwantielmodellen, voor een
  echte bandbreedte in plaats van een ongefundeerde "confidence"-claim. Drie
  onafhankelijk getrainde kwantielmodellen garanderen geen p10 ≤ p50 ≤ p90 —
  de serving-laag sorteert de drie waarden vóór teruggave.
  **Versie-risico:** native kwantiel-regressie (`reg:quantileerror`) vereist
  XGBoost ≥2.0. `requirements.txt` pint dit expliciet; LightGBM is de
  vastgelegde terugval als dat om wat voor reden dan ook niet beschikbaar is.
- **Features:** kalenderfeatures, lag- en rolling-window-features,
  promotie- en winkelmetadata. Bekende dataquirks expliciet afgehandeld:
  `StateHoliday` als string inlezen (voorkomt gemengde-type-bugs), de
  meermaandengaten die een deel van de winkels in 2014 heeft niet laten
  lekken in lag-features, ontbrekende `Open`-waarden in de testset expliciet
  afgevangen in plaats van stilzwijgend als NaN te laten doorlopen.
- **Validatie:** tijd-bewuste walk-forward validatie, geen shuffling. Metriek
  is **RMSPE** (de officiële competitiemetriek, eerlijk te vergelijken met
  gepubliceerde benchmarks), met dagen waarop de winkel dicht is (Sales=0)
  expliciet uitgesloten om deling-door-nul te voorkomen. Daarnaast rapporteert
  de evaluatie een **coverage-percentage**: het aandeel werkelijke waarden dat
  binnen de p10–p90-band valt (nominaal ~80%) — zonder die check is de
  onzekerheidsband zelf weer een ongefundeerde claim.

## Componenten & dataflow

| Component | Taak |
|---|---|
| `pipeline/` | Inlezen ruwe CSV's, schemavalidatie, featureconstructie, tijd-geordende train/validatie/test-split |
| `training/` | Traint p10/p50/p90 XGBoost-modellen via walk-forward CV, berekent RMSPE + coverage, slaat een geversied artefact op |
| `serving/` (FastAPI) | Laadt een expliciet gepinde modelversie (`MODEL_VERSION`, hard-fail indien ontbrekend/onvindbaar); serveert `/forecast`, `/metrics`, `/health`; API-key-auth via gehashte keys, CORS-allowlist, rate limiting |
| `security/` | AES-256-GCM-module (afgeleid van Certo's `encryptie.py`) voor optionele encryptie van audit-log, modelartefacten en client-data-at-rest; audit-logging zelf staat altijd aan, alleen de versleuteling ervan is toggle-baar |
| `dashboard/` | Statische frontend in Tessar-stijl (IBM Plex Sans, oklch-kleuren), configureerbaar API-basisadres, winkel-selector + datumbereik (géén productselector — zie dataset), grafiek met p10–p90-band en p50-lijn, toont de gevalideerde RMSPE en coverage prominent |
| `tests/` | Eén testbestand per module, Certo-conventie |

**Dataflow:** ruwe CSV's → `pipeline` (validatie + features, tijd-geordend) →
`training` (walk-forward CV, p10/p50/p90-modellen, RMSPE + coverage op
achtergehouden testperiode) → geversieerd artefact op schijf (model **+ de
laatste N dagen historie per winkel**, nodig om lag-/rolling-features te
reconstrueren bij een voorspellingsverzoek) → FastAPI laadt de gepinde versie
bij opstarten → dashboard roept via het configureerbare, CORS-beperkte adres
`/forecast` en `/metrics` aan → grafiek + nauwkeurigheidscijfers.

**Waarom de historie in het artefact zit:** het model gebruikt features als
"omzet t-7". Bij een `/forecast`-aanroep heeft de serving-laag die recente
historie nodig om zulke features te berekenen. Voor deze fase (statische
dataset, vaste gevalideerde horizon) volstaat een bundel met de laatste N
dagen per winkel zoals bekend op de trainingsafsluitdatum. Een echt, lopend
klantproject heeft hiervoor een live-gevoede historiebron nodig — dat is een
expliciet uitbreidingspunt, niet iets dat deze fase oplost (zie
`KNOWN-LIMITATIONS.md`).

## Foutafhandeling

Uitgangspunt: nooit stil falen, geen impliciete fallbacks (Certo-stijl).

- Ontbrekende/foute config (`MODEL_VERSION`, API-key-bestand, encryptiesleutel
  indien actief) → harde fout bij opstarten, server weigert te starten.
- Ongeldige API-input → Pydantic-validatiefout, 422 met duidelijke melding.
- Onbekend `store_id` → expliciete 404.
- Forecast-horizon buiten de tijdens training gevalideerde periode → 422,
  geen extrapolatie buiten wat bewezen is.
- Data-leakage-check in de trainingspipeline (train-einddatum vóór
  validatie-startdatum) → harde assertion-fout stopt de trainingsrun.

## Beveiliging

- **API-keys:** meerdere genoemde keys, gehasht opgeslagen (PBKDF2-HMAC-SHA256,
  600.000 iteraties — zelfde parameters als Certo) in `api_keys.json`,
  constante-tijdvergelijking bij verificatie via header `X-API-Key`. Eén
  integratie intrekken raakt de rest niet.
- **Rate limiting:** in-memory, per key — geldt alleen binnen één instance;
  expliciet gedocumenteerde beperking, geen verborgen aanname.
- **CORS:** allow-list via `CORS_ALLOWED_ORIGINS`. Ontbrekende config =
  expliciet lege allow-list (deny-all), **nooit** een wildcard-fallback.
- **Secrets:** `.env` (gitignored) + `.env.example` met alle vereiste
  variabelen — zelfde structuur als Certo. Bestanden met gehashte keys,
  versleutelde audit-log én modelartefacten krijgen chmod 600.
- **Dependencies:** versies gepind in `requirements.txt`; `pip-audit` is een
  handmatige controle die vóór oplevering wordt uitgevoerd — geen
  geautomatiseerde CI-gate, die bestaat in deze fase niet.
- **Audit-log:** altijd actief (timestamp, key-ID, opgevraagde winkel,
  horizon, statuscode, latency — nooit ruwe gevoelige payload); alleen de
  versleuteling ervan is toggle-baar (uit voor de publieke demo-data, aan
  zodra er echte klantdata bijkomt).

## Tests

Eén bestand per module:

- `test_pipeline.py` — schemavalidatie, featurecorrectheid, leakage-guard, de
  drie bekende dataquirks.
- `test_training.py` — artefact + metadata correct; RMSPE sluit
  gesloten-winkel/nul-omzet-dagen expliciet uit (geen div-by-zero); coverage
  van de p10–p90-band binnen plausibele range; split-grenzen kloppen.
- `test_serving.py` — auth (geldig/ongeldig/ontbrekend); hard-fail bij
  ontbrekende `MODEL_VERSION`/keys-bestand/encryptiesleutel; input-grenzen
  (422/404); kwantiel-sortering bij gekruiste voorspellingen; CORS weigert
  bij ontbrekende config (geen wildcard); rate-limit 429.
- `test_security.py` — aangepast van Certo's `test_encryptie.py`:
  encrypt/decrypt round-trip, tamper detection, hard-fail bij foute sleutel.

Vóór oplevering: volledige suite draaien, plus een handmatige controle van de
train/validatie-datumgrenzen.

## Deployment (deze fase: lokaal)

- `docker-compose.yml`: één `api`-service (Uvicorn/FastAPI, serveert zowel
  API als statisch dashboard onder dezelfde origin — lokaal dus geen CORS
  nodig), `models/` als volume zodat hertrainen geen rebuild vereist.
- Training draait als los eenmalig commando (`docker compose run --rm
  training ...`), geen langlopende service.
- `Dockerfile` minimaal: gepinde dependencies, alleen benodigde
  bronbestanden gekopieerd — zelfde stijl als Certo.
- `docs/`: instructie voor dataset ophalen (incl. licentie-check), trainen,
  lokaal draaien, plus `KNOWN-LIMITATIONS.md` (rate limiting
  single-instance, geen live historiefeed, dataset-licentiekader).
- Live deployment (Caddy naast Certo) en de website-demo-integratie zijn
  bewuste, losse vervolgstappen — niet in scope hier.

## Openstaande risico's (te verifiëren bij implementatie, geen blokkade voor dit ontwerp)

1. Kaggle-toegang (account/API-token) — terugval: synthetische dataset.
2. Exacte licentievoorwaarden van de Rossmann-competitie voor hergebruik van
   afgeleide statistieken.
3. XGBoost-versie in de buildomgeving ondersteunt `reg:quantileerror`
   (≥2.0) — terugval: LightGBM.
