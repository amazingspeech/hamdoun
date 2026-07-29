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
   - **T.o.v. je andere winkels**: hergebruikt de portfolio-samenvatting die de zijbalk al ophaalt voor de bestaande KPI-tegels (`sidebar-kpi-winkels`/`sidebar-kpi-nauwkeurigheid`) — geen nieuwe API-aanroep, dus geen nieuwe kostenpost. Als die data (nog) niet beschikbaar is in de huidige sessie (bv. rechtstreeks op de voorspellingspagina geland zonder eerst de zijbalk-data geladen te hebben), toont deze kaart simpelweg niet — geen misleidend cijfer, consistent met hoe de rest van de app al met ontbrekende data omgaat (bv. `herbestel_advies: Optional`, `voorbeeld_store_id: Optional`).

## Components

**`dashboard/assets/` (nieuw)** — `kwantiq-logo.svg`, het losse merk-asset. Geen koppeling aan bestaande pagina's.

**`dashboard/dashboard.js`** — de bestaande grafiek-tekenfunctie wordt uitgebreid: curve-interpolatie (bv. Catmull-Rom-achtige gladde path in plaats van rechte `L`-segmenten), een `<linearGradient>`-definitie voor de bandvulling, hover-event-handlers voor tooltips. Nieuwe functie `berekenInzichten(forecastResponse, sidebarPortfolioData)` die de drie kaartwaarden client-side afleidt uit al opgehaalde data — geen nieuwe `fetch()`-aanroep.

**`dashboard/styles.css`** — nieuwe klassen voor het inzichten-paneel (`.inzichten-paneel`, `.inzicht-kaart`) volgens de bestaande kaartstijl (`.kaart`), en de grafiek-gradient/tooltip-stijl.

**`dashboard/index.html`** — nieuw `<div id="inzichten-paneel">`-blok, geplaatst tussen de hero-sectie en de grafiek (zie bestaande structuur: `#resultaat` → `.hero` → `.factoren` → `.secundair` → grafiek).

**`dashboard/sidebar.js`** — blootstellen van de al opgehaalde portfolio-samenvattingsdata via een gedeelde, in-memory variabele (bv. `window.__portfolioSamenvatting` of een module-scoped export) zodat `dashboard.js` 'm kan lezen zonder een nieuwe aanroep te doen — precies het "geen nieuwe kostenpost"-principe uit de Architecture-sectie.

## Data flow

1. Gebruiker vraagt een voorspelling op zoals nu — `POST /forecast` blijft ongewijzigd, retourneert dezelfde `ForecastResponse` (inclusief de al bestaande `belangrijkste_factoren`).
2. Frontend berekent client-side, uit de ontvangen respons: bandbreedte-volatiliteit (kaart 1) en headline-factor (kaart 2, gewoon het eerste element uit een al bestaande lijst).
3. Voor kaart 3 (portfolio-vergelijking): als de zijbalk al portfolio-data heeft opgehaald in deze sessie (normaal het geval, want de zijbalk laadt bij elke paginabezoek), wordt die hergebruikt; anders blijft de kaart weg.
4. De grafiek zelf tekent dezelfde `voorspellingen`-array als nu, alleen met een gladdere curve, een gradient-vulling, en tooltips — geen nieuwe data nodig.

## Error handling

- **Ontbrekende portfolio-data voor kaart 3**: kaart wordt niet getoond (geen lege/misleidende placeholder) — zie Architecture, Component 3.
- **Geen SHAP-factoren beschikbaar** (kan voorkomen als alle bijdrages toevallig 0 zijn, zie `belangrijkste_factoren()`'s `if waarde != 0`-filter): kaart 2 wordt niet getoond, exact zoals de bestaande "Waarom deze voorspelling"-sectie dit vandaag al afhandelt (`factoren` blijft `hidden` als de lijst leeg is).
- **Zeer korte/vlakke bandbreedte** (p90≈p10≈p50, bv. bij zeer stabiele winkels): het volatiliteitspercentage kan richting 0% gaan — dit is een geldige, informatieve uitkomst ("zeer stabiel"), geen randgeval om apart af te vangen.

## Testing

**Backend:** geen wijzigingen — geen nieuwe tests nodig, `serving/forecast.py::belangrijkste_factoren()` blijft ongewijzigd.

**Frontend:** geen geautomatiseerde tests, conform de bestaande conventie van dit project — browser-geverifieerd: de grafiek rendert correct (gladde curve, gradient, tooltips) in zowel licht als donker thema; de drie inzicht-kaarten tonen kloppende, met de hand na te rekenen waarden voor een bekende teststore; kaart 3 verdwijnt netjes (geen layout-sprong) wanneer er geen portfolio-data beschikbaar is; het logo-SVG rendert correct op meerdere formaten (16px t/m 128px) zonder vervorming.
