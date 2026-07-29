# KwantIQ-logo + Forecast Insights-herontwerp

**Status:** approved design, not yet implemented
**Date:** 2026-07-29
**Context:** Vervolg op de Prospero-rebrand van eerder vanavond — het product krijgt opnieuw een naam, ditmaal "KwantIQ - Vraagvoorspelling". De gebruiker wil twee dingen tegelijk: (1) een logo voor KwantIQ, en (2) een concreet "enterprise-level" UI/UX-herontwerp van het bestaande dashboard, met als expliciete aanleiding dat de grafiek op de voorspellingspagina moderner/strakker kan en dat er meer statistische diepte uit de al binnenkomende cijfers gehaald kan worden. De gebruiker gaf expliciet brede goedkeuring om zelf de beste technische/commerciële keuzes te maken en door te pakken, inclusief bij toekomstige toestemmingsvragen in dit traject.

## Problem

De voorspellingspagina (`dashboard/index.html`) toont per winkel een p10/p50/p90-bandbreedte in een eenvoudige SVG-grafiek, plus een lijst met SHAP-factoren ("Waarom deze voorspelling") die al berekend wordt maar visueel ondergesneeuwd is in een uitklapbare lijst. Er zit al veel bruikbare data in de bestaande API-respons die nu niet als apart, herkenbaar inzicht aan de gebruiker getoond wordt. Daarnaast heeft het product (in Notion en in gesprek) een nieuwe naam gekregen zonder een bijbehorend visueel merk.

## Goal

Een moderne, gradient-gevulde grafiek met vloeiende interpolatie en hover-tooltips, een nieuw "Inzichten"-paneel met drie afgeleide statistieken die al bestaande modeloutput hergebruiken (geen nieuwe databron, geen nieuwe trage berekening), en een los KwantIQ-logo als los beschikbaar asset.

## Explicitly out of scope

- **De daadwerkelijke technische rebrand naar KwantIQ** (naamgeving door de UI heen, domeinverhuizing, deploy) — dat is een apart, later traject, net zoals de Prospero-rebrand dat eerder vanavond was. Dit voorkomt een halfslachtige productstaat waarin een KwantIQ-logo naast "Prospero"-tekst zou staan.
- **Volledige visuele herontwerp van `overview.html` en `team.html`** — de concrete aanleiding van de gebruiker (de grafiek, meer diepte uit de cijfers) zit specifiek op de voorspellingspagina (`index.html`). De hier vastgelegde visuele taal (kaartstijl, typografie, grafiekesthetiek) is herbruikbaar voor een latere uitbreiding naar de andere pagina's, maar dat is geen onderdeel van dit traject.
- **Een echte, live-herberekende portfolio-brede vergelijking.** `serving/app.py`'s `/portfolio`-endpoint berekent zijn KPI's bewust alleen over de opgevraagde pagina, niet over alle winkels van een organisatie — een volledige berekening kost bij de 1115-winkel-demo-organisatie ~88 seconden (zie de bestaande code-comment bij `/portfolio`). Dit ontwerp introduceert geen nieuwe dure full-portfolio-berekening; zie Component 3 hieronder voor de gekozen, goedkopere aanpak.
- **Wijziging van het onderliggende model of de SHAP-berekening zelf.** `serving/forecast.py::belangrijkste_factoren()` blijft ongewijzigd — dit ontwerp presenteert de al bestaande output beter, het berekent niets nieuws op modelniveau.

## Architecture

Drie onafhankelijke onderdelen:

1. **KwantIQ-logo** — een los SVG-asset (`dashboard/assets/kwantiq-logo.svg` of vergelijkbaar), geen wijziging aan enige live pagina. Geometrisch: drie oplopende staafjes (groei/voorspelling-motief), het hoogste staafje eindigend in een stip met een dunne opgaande lijn erdoorheen (het "voorspellingslijn-met-band"-motief herhaald als merk-icoon) — geen generiek AI-sparkle- of gloeilamp-icoon. Kleur: het bestaande smaragd/jade-accent (hue 155), consistent met de rest van het product. Werkt op kleine formaten (favicon-schaal).
2. **Grafiek-modernisering** in `dashboard/dashboard.js` (de SVG-rendering-functie) en `dashboard/styles.css` — vloeiende curve-interpolatie in plaats van rechte segmenten, een subtiel verlopend smaragdgroen vulling onder de bandbreedte (i.p.v. een vlakke kleur), dunnere/rustigere rasterlijnen, hover-tooltips met exacte datum+waarden, en visuele nadruk op de laatste voorspeldag.
3. **"Inzichten"-paneel** — een nieuw blok op `index.html`, direct boven of naast de grafiek, met drie kaarten:
   - **Betrouwbaarheid**: puur client-side berekend uit de al opgehaalde `voorspellingen`-array (`ForecastResponse.voorspellingen`, elk met p10/p50/p90) — gemiddelde relatieve bandbreedte `(p90-p10)/p50` over de horizon, vertaald naar een kwalitatief label plus het percentage: **&lt;15%** "Stabiel", **15-30%** "Gemiddeld", **&gt;30%** "Wisselvallig" (drie niveaus, geen simpele twee-staat-flag). Geen backend-wijziging nodig.
   - **Sterkste patroon**: het eerste element van `ForecastResponse.belangrijkste_factoren` (al gesorteerd op absolute SHAP-grootte, zie `serving/forecast.py::belangrijkste_factoren()`), als kop-inzicht getoond in plaats van weggestopt in de bestaande uitklapbare "Waarom deze voorspelling"-lijst. Geen backend-wijziging nodig — puur een presentatieverandering van bestaande data.
   - **T.o.v. je andere winkels**: **correctie na codeonderzoek** — de zijbalk op `index.html` haalt in de huidige code helemaal nooit portfolio-data op (`sidebar.js::initPortfolioSidebar()` heeft dit expliciet becommentarieerd: alleen `overview.js` roept `/portfolio` aan, om precies dezelfde reden als hierboven — een extra aanroep alleen voor twee zijbalk-cijfers zou op elke pagina onnodige serverbelasting toevoegen). "Hergebruik wat de zijbalk al ophaalt" was dus geen werkende aanname voor deze pagina. In plaats daarvan: `overview.js` cachet `kpi.totale_verwachte_omzet` (en het winkelaantal) in `localStorage`, via dezelfde org-genaamspaceerde sleutel-functie (`sidebarSleutel()`) die al bestaat voor de omzet-trendpijl (`vorige_sidebar_omzet`) — zelfde patroon, geen nieuw mechanisme. `dashboard.js` leest die cache-waarde als die bestaat én bij de huidige `organisatie_id` hoort. Bestaat de cache niet (bv. gebruiker heeft `overview.html` nog nooit in deze browser bezocht), dan toont deze kaart simpelweg niet — geen misleidend cijfer, en geen nieuwe API-aanroep alsnog. De waarde kan enigszins verouderd zijn (van een eerder bezoek aan `overview.html`), wat acceptabel is voor een oriënterende vergelijkingskaart.

## Components

**`dashboard/assets/` (nieuw)** — `kwantiq-logo.svg`, het losse merk-asset. Geen koppeling aan bestaande pagina's.

**`dashboard/dashboard.js`** — de bestaande grafiek-tekenfunctie (`tekenGrafiek()`) wordt uitgebreid: curve-interpolatie (bv. Catmull-Rom-achtige gladde path in plaats van rechte `L`-segmenten), een `<linearGradient>`-definitie voor de bandvulling, hover-event-handlers voor tooltips. Nieuwe functie `berekenInzichten(forecastResponse, portfolioCache)` die de drie kaartwaarden client-side afleidt uit al opgehaalde data (`forecastResponse` uit de bestaande `/forecast`-call, `portfolioCache` uit de nieuwe `localStorage`-cache hieronder) — geen nieuwe `fetch()`-aanroep. Leest de cache via dezelfde `sidebarSleutel()`-functie die `sidebar.js` al definieert (geladen vóór `dashboard.js`, dus beschikbaar).

**`dashboard/sidebar.js`** — `toonSidebarKpis(data)` (aangeroepen vanuit `overview.js`) cachet voortaan ook `data.kpi.totale_verwachte_omzet` in `localStorage`, via `sidebarSleutel("portfolio_omzet_cache", huidigeOrganisatieId)` — zelfde patroon als de bestaande `vorige_sidebar_omzet`-sleutel in `toonOmzetTrend()`. Geen wijziging aan wélke pagina's `/portfolio` aanroepen (blijft alleen `overview.js`).

**`dashboard/styles.css`** — nieuwe klassen voor het inzichten-paneel (`.inzichten-paneel`, `.inzicht-kaart`) volgens de bestaande kaartstijl (`.kaart`), en de grafiek-gradient/tooltip-stijl.

**`dashboard/index.html`** — nieuw `<div id="inzichten-paneel">`-blok, geplaatst tussen de hero-sectie en de grafiek (zie bestaande structuur: `#resultaat` → `.hero` → `.factoren` → `.secundair` → grafiek).

## Data flow

1. Gebruiker vraagt een voorspelling op zoals nu — `POST /forecast` blijft ongewijzigd, retourneert dezelfde `ForecastResponse` (inclusief de al bestaande `belangrijkste_factoren`).
2. Frontend berekent client-side, uit de ontvangen respons: bandbreedte-volatiliteit (kaart 1) en headline-factor (kaart 2, gewoon het eerste element uit een al bestaande lijst).
3. Voor kaart 3 (portfolio-vergelijking): `overview.js` schrijft bij elk bezoek de portfolio-omzet naar `localStorage` (zie Components). `dashboard.js` leest die cache bij het tonen van de inzichten; bestaat de cache niet (nog nooit op `overview.html` geweest in deze browser) of hoort die bij een andere organisatie, dan blijft de kaart weg.
4. De grafiek zelf tekent dezelfde `voorspellingen`-array als nu, alleen met een gladdere curve, een gradient-vulling, en tooltips — geen nieuwe data nodig.

## Error handling

- **Ontbrekende portfolio-data voor kaart 3**: kaart wordt niet getoond (geen lege/misleidende placeholder) — zie Architecture, Component 3.
- **Geen SHAP-factoren beschikbaar** (kan voorkomen als alle bijdrages toevallig 0 zijn, zie `belangrijkste_factoren()`'s `if waarde != 0`-filter): kaart 2 wordt niet getoond, exact zoals de bestaande "Waarom deze voorspelling"-sectie dit vandaag al afhandelt (`factoren` blijft `hidden` als de lijst leeg is).
- **Zeer korte/vlakke bandbreedte** (p90≈p10≈p50, bv. bij zeer stabiele winkels): het volatiliteitspercentage kan richting 0% gaan — dit is een geldige, informatieve uitkomst ("zeer stabiel"), geen randgeval om apart af te vangen.

## Testing

**Backend:** geen wijzigingen — geen nieuwe tests nodig, `serving/forecast.py::belangrijkste_factoren()` blijft ongewijzigd.

**Frontend:** geen geautomatiseerde tests, conform de bestaande conventie van dit project — browser-geverifieerd: de grafiek rendert correct (gladde curve, gradient, tooltips) in zowel licht als donker thema; de drie inzicht-kaarten tonen kloppende, met de hand na te rekenen waarden voor een bekende teststore; kaart 3 verdwijnt netjes (geen layout-sprong) wanneer er geen portfolio-data beschikbaar is; het logo-SVG rendert correct op meerdere formaten (16px t/m 128px) zonder vervorming.
