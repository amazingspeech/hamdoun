# Eigen winkels: geüploade verkoopdata per naam scheiden

**Status:** approved design, not yet implemented
**Date:** 2026-07-29
**Context:** de gebruiker uploadde eigen verkoopdata (na de puntkomma-CSV-fix van
vandaag) en was verward: de upload werd geen "Winkel" in de sidebar, kreeg
geen naam of nummer, en de grafiek was onduidelijk. Onderzoek wees uit dat
`eigen_verkoopdata`/`eigen_product_verkoopdata` nu org-breed zijn (één bucket
per organisatie, geen koppeling aan een winkel) — een nieuwe upload
*vervangt* de vorige set volledig. Dit is een echte productbeslissing, geen
bugfix: dit ontwerp introduceert een naam-baar "eigen winkel"-concept zodat
meerdere datareeksen naast elkaar kunnen bestaan.

## Problem

- Geüploade verkoopdata (`POST /organisatie/verkoopdata`,
  `POST /organisatie/product-verkoopdata`) is gekoppeld op `organisatie_id`,
  niet op een winkel. Eén upload = één bucket per organisatie; een tweede
  upload vervangt de eerste volledig (`vervang_verkoopdata`).
- Dit is onafhankelijk van de bestaande `winkels`-tabel (ML-model-winkels,
  gekoppeld via `extern_store_id`) — een organisatie met een geüploade CSV
  ziet die nergens terug als "Winkel X", wat verwarrend is.
- De sparkline-grafiek op `team.html` toont alleen begin- en einddatum op de
  x-as, geen tussenliggende labels, geen gridlines, geen hover-waarde per
  punt.
- De prijsinstelling "Gemiddelde omzet per verkocht stuk" (nodig voor een
  stuks-advies i.p.v. alleen een omzetbedrag) is een handmatig ingevoerd
  getal, org-breed.

## Goal

1. Een organisatie kan meerdere genoemde "eigen winkels" aanmaken (bv.
   "Webshop A", "Marktkraam"), elk met een eigen, onafhankelijke
   verkoopdata-geschiedenis (zowel de omzet-per-dag- als de
   product-per-dag-CSV).
2. Uploaden en het resultaat bekijken (grafiek, herbestel-advies) gebeurt via
   een expliciete winkel-keuze — nooit meer een stille org-brede vervanging.
3. De grafiek wordt leesbaarder: meer datumlabels, een gridline, hover-waarde
   per datapunt.
4. De prijs per stuk wordt, waar mogelijk, automatisch afgeleid uit de eigen
   data in plaats van handmatig ingevoerd.

## Explicitly out of scope

- Aanpassen van de bestaande `winkels`-tabel (ML-model-winkels) of het
  forecast-/portfolio-pad dat daarop draait — "eigen winkels" is een volledig
  gescheiden concept, geen uitbreiding van dat mechanisme.
- Samenvoegen/dedupliceren van overlappende datums bij upload — een nieuwe
  upload blijft de volledige set van die eigen winkel vervangen (bestaand,
  bewust gedrag; nu alleen gescoped per eigen winkel i.p.v. per organisatie).
- Migratie van bestaande data: productie heeft precies 1 organisatie
  ("Tessar demo") met 30 testrijen in `eigen_verkoopdata` — geen echte
  klantdata. Deze rijen worden simpelweg niet overgezet; de tabellen worden
  leeg herbouwd met het nieuwe schema.
- Alembic/migratietooling — nog steeds niet nodig op deze schaal. Het
  bestaande `_migreer_ontbrekende_kolommen()`-mechanisme (`db/schema.py`)
  voegt alleen ontbrekende *kolommen* toe aan een bestaande tabel; het kan
  geen kolom hernoemen, een constraint wijzigen, of een tabel herstructureren
  — precies wat deze wijziging nodig heeft voor `eigen_verkoopdata`/
  `eigen_product_verkoopdata`. In plaats daarvan: vóór de deploy die deze
  wijziging bevat, eenmalig handmatig `DROP TABLE eigen_verkoopdata,
  eigen_product_verkoopdata` op `tenants.db` (alleen deze twee — geen ander
  data verloren). De daaropvolgende herstart roept, zoals bij elke deploy,
  `serving/app.py`'s module-level `maak_database()` aan, die beide tabellen
  automatisch opnieuw aanmaakt met het nieuwe schema via `create_all()`.

## Architecture

### 1. Datamodel

Nieuwe tabel `eigen_winkels`:
- `id`, `organisatie_id` (FK), `naam` (String, verplicht), `aangemaakt_op`.
- `UniqueConstraint(organisatie_id, naam)` — voorkomt twee winkels met
  dezelfde naam binnen één organisatie; namen zijn verder vrije tekst.

Wijzigingen aan bestaande tabellen:
- `eigen_verkoopdata`: `organisatie_id`-kolom vervangen door
  `eigen_winkel_id` (FK naar `eigen_winkels.id`). Unique constraint wordt
  `(eigen_winkel_id, datum)` i.p.v. `(organisatie_id, datum)`.
- `eigen_product_verkoopdata`: zelfde wijziging, unique constraint wordt
  `(eigen_winkel_id, product, datum)`.

Organisatie-scoping blijft gegarandeerd via een join met `eigen_winkels` (elke
query op verkoopdata gaat altijd via een `eigen_winkel_id` die eerst
geverifieerd is te horen bij `gebruiker.organisatie_id` — zelfde patroon als
`hoort_store_bij_organisatie()` voor de ML-model-winkels).

### 2. Backend API

Nieuw, in `db/eigen_winkels.py` + endpoints in `serving/app.py`:
- `POST /organisatie/eigen-winkels` (eigenaar-only) — `{naam}` → 201, nieuwe
  winkel. 409 bij dubbele naam binnen de organisatie.
- `GET /organisatie/eigen-winkels` — lijst (elke ingelogde gebruiker, zelfde
  leesrecht-patroon als `/organisatie/verkoopdata`). Elke winkel in de lijst
  bevat naast `id`/`naam`: `gemiddelde_omzet_per_stuk` (handmatig ingesteld
  bedrag, of `None`), `automatische_prijs_per_stuk` (het uit sectie 3
  afgeleide bedrag, of `None` zonder overlappende data), en `heeft_verkoopdata`
  (afgeleide boolean, zie sectie 4). `heeft_prijs` is dan simpelweg
  `gemiddelde_omzet_per_stuk is not None or automatische_prijs_per_stuk is
  not None` — client-side afleidbaar, dus geen apart veld nodig. Dit
  onderscheid voorkomt dat de frontend `heeft_prijs=true` ziet zonder te
  weten welk bedrag daadwerkelijk geldt (nodig omdat sectie 3 de automatische
  waarde laat voorgaan op de handmatige).
- `PUT /organisatie/eigen-winkels/{id}/instellingen` (eigenaar-only) —
  `{gemiddelde_omzet_per_stuk}`, vervangt het huidige
  `PUT /organisatie/instellingen` (zie sectie 4).
- `PATCH /organisatie/eigen-winkels/{id}` (eigenaar-only) — hernoemen. 404
  voor een winkel van een andere organisatie (zelfde
  enumeratie-preventie-patroon als overal elders: nooit 403).
- `DELETE /organisatie/eigen-winkels/{id}` (eigenaar-only) — verwijdert de
  winkel en, expliciet in dezelfde transactie (niet via FK `ondelete=CASCADE`
  — dit project gebruikt SQLAlchemy Core zonder ORM-cascade-configuratie, dus
  cascades worden overal expliciet in de python-functie gedaan, zelfde
  patroon als organisatie-offboarding in `db/organisaties.py`), alle
  bijbehorende rijen in `eigen_verkoopdata` en `eigen_product_verkoopdata`.
  404 voor een winkel van een andere organisatie.

Gewijzigd — elk van deze krijgt een verplichte `eigen_winkel_id`
(query-param voor GET, form-veld naast het bestand voor POST):
- `POST /organisatie/verkoopdata`, `GET /organisatie/verkoopdata`
- `POST /organisatie/product-verkoopdata`,
  `GET /organisatie/herbestel-advies-per-product`
- `GET /organisatie/eigen-voorspelling`

Elk van deze endpoints valideert eerst dat de opgegeven `eigen_winkel_id`
bestaat én bij `gebruiker.organisatie_id` hoort — 404 anders (nooit 403,
consistent met de rest van de app).

### 3. Prijs per stuk — automatische afleiding

Nieuwe module `serving/prijs_per_stuk.py`:
`bereken_gemiddelde_prijs_per_stuk(verkoopdata_rijen, product_verkoopdata_rijen) -> float | None`
— sommeert `omzet` uit `eigen_verkoopdata` en `aantal` uit
`eigen_product_verkoopdata`, uitsluitend over de datums die in **beide** sets
voorkomen voor die eigen winkel, en deelt de twee totalen. Geeft `None` als
er geen overlappende datums zijn. Losstaande, puur-functionele module (geen
DB-toegang) — zelfde stijl als `serving/verkoopdata.py`, makkelijk te testen
zonder database-fixtures.

Het bestaande org-brede prijsveld verhuist naar een nieuwe tabel
`eigen_winkel_instellingen` (`eigen_winkel_id` PK/FK,
`gemiddelde_omzet_per_stuk` Float nullable) — de huidige
`organisaties`-kolom voor dit veld vervalt, `db/organisaties.py`'s
`stel_gemiddelde_omzet_per_stuk_in()`/`haal_gemiddelde_omzet_per_stuk()`
verhuizen naar een nieuwe `db/eigen_winkel_instellingen.py` met een
`eigen_winkel_id`-parameter in plaats van `organisatie_id`.

`GET /organisatie/eigen-voorspelling` gebruikt, per eigen winkel, in
volgorde: (1) de automatisch berekende prijs indien beschikbaar, (2) anders
het handmatig ingestelde bedrag uit `eigen_winkel_instellingen`, (3) anders
geen stuks-advies (bestaand fallback-gedrag: alleen een omzetbedrag tonen).

Dit betekent dat `eigen_product_verkoopdata` (premium-only) niet meer alleen
het per-product-herbestel-advies voedt, maar ook — als bijeffect — de
prijsberekening voor het gewone omzet-gebaseerde advies kan verbeteren voor
organisaties die de premium-functie gebruiken.

### 4. Bestaande features die meeveranderen

Twee al-gebouwde features lezen vandaag rechtstreeks de org-brede
verkoopdata/prijs en zouden zonder aanpassing stilzwijgend breken —
expliciet in scope van deze wijziging, niet los na te ruimen:

**`GET`/`PUT /organisatie/instellingen`** had precies één veld
(`gemiddelde_omzet_per_stuk`), dat nu per eigen winkel bestaat. Dit endpoint
vervalt volledig. Het prijsformulier verhuist van een los blok op
`team.html` naar een veld per rij in de nieuwe "Eigen winkels"-kaart, met een
nieuw endpoint `PUT /organisatie/eigen-winkels/{id}/instellingen` (eigenaar-only,
`{gemiddelde_omzet_per_stuk}`) — zelfde autorisatiepatroon als het huidige
`PUT /organisatie/instellingen`.

**`serving/herbestel_email.py`** (wekelijkse cron-mail): `_verzamel_forecast_via_eigen_data()`
en `db_organisaties.haal_gemiddelde_omzet_per_stuk()` gebruiken vandaag
precies één org-brede waarde per organisatie. Wordt: itereer over
`db_eigen_winkels.lijst_eigen_winkels(engine, organisatie_id=org.id)`, bereken
per eigen winkel een eigen forecast + prijs + advies (zelfde
`bereken_eigen_voorspelling`/`herbestel_advies`-functies, nu per winkel
aangeroepen i.p.v. één keer per organisatie). **Niet optellen** tot één
org-totaal zoals de gedeeld-model-tak wel doet voor meerdere echte
winkels — verschillende eigen winkels kunnen andere producten/prijzen
hebben, dus een opgeteld stuks-advies zou betekenisloos zijn. In plaats
daarvan: één e-mail per organisatie zoals nu, met een apart tekstblok per
eigen winkel die genoeg historie heeft (`bouw_email_inhoud()` krijgt een
lijst van (winkelnaam, forecast, advies)-items i.p.v. één set totalen).

**`dashboard/onboarding.js`** (self-serve-onboardingchecklist,
`haalOnboardingStatus()`): las tot nu toe `/organisatie/verkoopdata` (org-breed,
zonder parameter) en `/organisatie/instellingen`. Beide bestaan straks niet
meer in die vorm. Om N+1-fetches (één call per eigen winkel) te voorkomen,
gebruikt de checklist voortaan uitsluitend `GET /organisatie/eigen-winkels`
(zie sectie 2 hierboven voor de veldnamen): "Upload je verkoopdata" voltooid
zodra minstens één eigen winkel `heeft_verkoopdata`; "Stel je
herbestel-prijs in" voltooid zodra minstens één eigen winkel
`gemiddelde_omzet_per_stuk` of `automatische_prijs_per_stuk` niet-`None`
heeft.

### 5. Frontend (`dashboard/team.html` + `account.js`)

Nieuwe kaart bovenaan, vóór de bestaande upload-kaarten: **"Eigen winkels"**
— tekstveld + "Aanmaken"-knop, lijst met bestaande winkels (naam,
hernoemen-knop die het label inline editable maakt, verwijderen-knop).
Verwijderen vraagt een `confirm()`-bevestiging vóór de aanroep — dit wijkt
bewust af van `verwijderTeamlid()` (dat direct, zonder bevestiging,
verwijdert): een teamlid kan opnieuw uitgenodigd worden, maar een eigen
winkel verwijderen vernietigt cascaderend de geüploade verkoopdata, die niet
zomaar opnieuw beschikbaar is als de bron-CSV niet meer bij de hand is.

Beide bestaande upload-kaarten (`verkoopdata-kaart`,
`product-verkoopdata-kaart`) krijgen een `<select>` met de eigen-winkel-lijst
vóór het bestandsveld, verplicht om te kunnen uploaden. Wisselen van
selectie ververst de grafiek/het advies voor die winkel (herbruikt de
bestaande `haalVerkoopdata()`/`haalEigenVoorspelling()`-fetch-logica, nu met
`eigen_winkel_id` als parameter). Leeg-staat (geen eigen winkels) toont een
duidelijke prompt om er eerst één aan te maken, met de upload-velden disabled
— consistent met hoe de product-verkoopdata-kaart nu al een proefperiode-
melding + disabled velden toont.

**Grafiek (`tekenVerkoopdataGrafiek` in `account.js`):**
- Meer x-as-labels: elke ~5e datapunt (of een vast aantal, gelijk verdeeld
  over de reeks) i.p.v. alleen begin/eind.
- Eén horizontale gridline op de y-as-middenwaarde, naast de bestaande
  boven/onder-labels.
- Hover-tooltip per datapunt: een onzichtbare bredere hit-target per punt
  (cirkel of verticale strook) die op hover de exacte datum + het
  omzetbedrag toont — zelfde `<title>`-gebaseerde aanpak als andere simpele
  tooltips in dit dashboard, geen externe library.

## Data flow

1. Gebruiker opent "Team beheren" → ziet "Eigen winkels"-kaart, maakt een
   winkel aan (of kiest een bestaande uit de dropdown in de upload-kaarten).
2. Upload van een CSV stuurt nu `eigen_winkel_id` mee; backend valideert
   organisatie-eigendom, parseert (bestaande, net gefixte parser), vervangt
   de data van **die specifieke winkel** (niet de hele organisatie).
3. Wisselen van winkel in de dropdown haalt opnieuw
   `/organisatie/verkoopdata?eigen_winkel_id=...` en
   `/organisatie/eigen-voorspelling?eigen_winkel_id=...` op en tekent de
   grafiek/het advies opnieuw.
4. Verwijderen van een eigen winkel verwijdert stil ook zijn verkoopdata
   (cascade) — geen aparte bevestigingsstap voor die subdata, wel een
   bevestiging voor het verwijderen van de winkel zelf.

## Error handling

- Elk endpoint dat een `eigen_winkel_id` accepteert: 404 (nooit 403) als die
  niet bestaat of bij een andere organisatie hoort — zelfde
  enumeratie-preventie-patroon als de rest van de app.
- Dubbele naam bij aanmaken: 409, met een duidelijke Nederlandstalige
  foutmelding (zelfde patroon als de bestaande teamlid-duplicate-email-409).
- Prijsberekening zonder overlappende datums: `None`, geen fout — de
  frontend valt terug op het handmatige veld of toont geen stuks-advies,
  precies zoals het bestaande fallback-gedrag nu al werkt zonder ingestelde
  prijs.

## Testing

- **Backend**: volledig TDD, zoals de rest van dit project. `db/eigen_winkels.py`
  (aanmaken, dubbele naam, lijst met `heeft_verkoopdata`/`heeft_prijs`,
  hernoemen, verwijderen+cascade), `serving/prijs_per_stuk.py`
  (overlap-berekening, geen-overlap-geval), endpoint-tests voor alle nieuwe
  en gewijzigde routes (inclusief de tenant-isolatie-check: een
  `eigen_winkel_id` van organisatie A geeft 404 voor een gebruiker van
  organisatie B).
- **Bestaande tests die herschreven moeten worden, niet alleen uitgebreid**
  (blast radius van sectie 4 hierboven): `tests/test_organisatie_instellingen_endpoint.py`
  (endpoint verdwijnt, tests verhuizen naar de nieuwe
  eigen-winkel-instellingen-tests), `tests/test_herbestel_email.py` (de
  eigen-data-fallback-tak itereert nu per eigen winkel i.p.v. één org-brede
  aanroep — bestaande fixtures/asserts moeten mee), `tests/test_eigen_voorspelling_endpoint.py`
  en `tests/test_verkoopdata_endpoint.py` (verplichte `eigen_winkel_id`-parameter),
  `tests/test_db_organisaties.py` (verliest de
  `stel_gemiddelde_omzet_per_stuk_in`/`haal_gemiddelde_omzet_per_stuk`-tests,
  die verhuizen naar `tests/test_db_eigen_winkel_instellingen.py`),
  `tests/test_db_schema.py` (schema-assertions voor de gewijzigde/nieuwe
  tabellen).
- **Frontend**: geen automated JS-tests (consistent met eerdere
  dashboard-only rondes in dit project) — live geverifieerd in de browser:
  twee eigen winkels aanmaken, elk een eigen CSV uploaden, bevestigen dat de
  grafieken/adviezen onafhankelijk van elkaar zijn, hernoemen, verwijderen
  (inclusief dat de data echt weg is), en de nieuwe grafiek-labels/tooltip
  visueel controleren in beide thema's.
