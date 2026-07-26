# Tessar — vraagvoorspelling-toolkit

Herbruikbare toolkit voor dienst 02 (Voorspellende modellen & besluitondersteuning):
pipeline, training, een dunne serving-API, en een dashboard. Zie
`docs/superpowers/specs/2026-07-25-vraagvoorspelling-toolkit-design.md` in de
repo-root voor het volledige ontwerp.

## 1. Dataset ophalen (handmatige stap, vóór elke training)

Deze toolkit is gebouwd en gevalideerd op de Rossmann Store Sales-dataset
(Kaggle-competitie). Twee dingen moet je zelf controleren vóórdat je traint:

1. **Toegang.** Downloaden vereist een Kaggle-account + API-token
   (`~/.kaggle/kaggle.json`). Zonder account: gebruik voorlopig een
   synthetische dataset met vergelijkbare structuur (winkels, promoties,
   feestdagen, seizoenspatroon) — dezelfde `training.cli`-flow werkt daar
   ook mee, zie `tests/test_cli.py` voor een voorbeeld van hoe zo'n dataset
   eruitziet.
2. **Licentie.** Lees de competitieregels op de Kaggle-pagina van Rossmann
   Store Sales vóórdat je deze dataset (of afgeleide statistieken ervan)
   ergens buiten dit lokale project gebruikt. Deze toolkit gebruikt Rossmann
   uitsluitend om de methode te bouwen/valideren — er wordt geen ruwe data
   herpubliceerd. Voor een latere publieke website-demo: gebruik
   geanonimiseerde/herschaalde of gekalibreerde synthetische waarden, nooit
   de ruwe Rossmann-cijfers.

Download `train.csv` en `store.csv` naar `data/`.

## 2. Trainen

```bash
source .venv/bin/activate
python3 -m training.cli --train data/train.csv --winkels data/store.csv
```

Dit print de RMSPE en coverage, en schrijft een geversieerd artefact naar
`models/<versie>/`. Zet die versie in `.env`:

```
MODEL_VERSION=<versie uit de output>
```

Voeg minimaal één API-key toe voordat je de server start:

```bash
python3 -c "from pathlib import Path; from security import api_keys; api_keys.voeg_key_toe(Path('api_keys.json'), 'lokaal-testen', 'kies-een-eigen-key')"
```

Maak een lege `audit.log`-bestand aan; Docker zou dit anders als directory aanmaken, wat de app breekt.
De container draait als een niet-root gebruiker (zie `Dockerfile`) die dit host-bestand niet bezit, dus
moet het schrijfbaar zijn voor die gebruiker:

```bash
touch audit.log
chmod 666 audit.log
```

## 3. Lokaal draaien

```bash
docker compose up api
```

Dashboard: `http://localhost:8000/`. API: `http://localhost:8000/forecast`,
`http://localhost:8000/metrics` (beide vereisen de `X-API-Key`-header).

Hertrainen zonder rebuild. De `training`-service deelt dezelfde niet-root
container-gebruiker als `api` (zie `Dockerfile`) en schrijft een nieuwe
versiemap onder `models/` — die map moet dus ook voor die gebruiker
beschrijfbaar zijn, met het execute-bit erbij (nodig om nieuwe submappen
aan te maken, chmod 666 alleen volstaat hier niet zoals bij een los
bestand):

```bash
chmod 777 models
docker compose run --rm training --train data/train.csv --winkels data/store.csv
```

(Dit schrijft een nieuwe versie naar `models/`; `MODEL_VERSION` in `.env`
bewust handmatig bijwerken en `api` herstarten om 'm te promoveren — geen
automatische overname van de nieuwste versie.)

## 4. Tests

```bash
pytest -v
```

## 5. Bekende risico's / terugvalopties

- **XGBoost-versie:** kwantiel-regressie (`reg:quantileerror`) vereist
  XGBoost ≥2.0. Als de buildomgeving een oudere versie oplevert: vervang
  `objective="reg:quantileerror"` / `quantile_alpha` in `training/train.py`
  door LightGBM (`objective="quantile"`, `alpha=<kwantiel>`) — dezelfde
  interface (`dict[float, model]` met `.predict()`) blijft dan intact voor
  de rest van de codebase.
- Overige bekende beperkingen: zie `KNOWN-LIMITATIONS.md`.
