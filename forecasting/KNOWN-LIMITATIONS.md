# Bekende beperkingen

Eerlijke documentatie van wat deze toolkit (nog) niet oplost — zelfde
patroon als Certo's `KNOWN-LIMITATIONS.md`.

- **Geen live historiefeed.** De serving-laag reconstrueert lag-/
  rolling-features uit een historiebundel die bij training is vastgelegd,
  niet uit een live-bijgewerkte databron. Voor een echt, lopend
  klantproject moet dit een live feed worden (extern datawarehouse, CRM,
  of periodieke re-training) — niet gebouwd in deze fase.
- **Recursieve meerdaagse voorspelling.** Voor horizons voorbij de kortste
  lag (7 dagen) gebruikt de voorspelling zijn eigen eerdere p50-uitkomsten
  als werkwaarde voor latere lag-features. Fouten kunnen zich opstapelen
  over een langere horizon — dit is inherent aan de recursieve aanpak, niet
  een bug.
- **Promotie- en schoolvakantie-features standaard nul.** Bij meerdaagse 
  recursieve voorspellingen stellen toekomstige `Promo` en `SchoolHoliday` 
  waarden zich standaard op 0 (geen promotie, geen schoolvakantie) in, omdat 
  hun werkelijke toekomstige waarden op voorspellingstijdstip onbekend zijn. 
  Dit veroorzaakt een systematische neerwaartse bias in voorspellingen op 
  dagen waarop een promotie daadwerkelijk plaatsvindt. Omdat de voorspelling 
  recursief is, voeden deze vertekende uitkomsten terug in de lag-features 
  voor volgende dagen, wat de bias verder in de horizon versterkt. Dit is 
  een onderscheiden bron van systematische fout, los van de reeds 
  gedocumenteerde foutsamenstellingen over lange horizons.
- **Rate limiting is per-instance.** De in-memory rate limiter houdt geen
  gedeelde staat bij tussen meerdere gelijktijdige API-instances. Geldig
  voor deze fase (één instance), niet voor een horizontaal geschaalde
  deployment.
- **Dataset-licentie.** Rossmann Store Sales is een Kaggle-competitiedataset
  met eigen gebruiksvoorwaarden — geverifieerd tijdens implementatie, zie
  README.md sectie 1. Deze toolkit toont er nooit ruwe cijfers uit op een
  publiek kanaal; alleen afgeleide, gevalideerde nauwkeurigheidscijfers.
- **CI-pipeline (2026-07-26).** `.github/workflows/forecasting-ci.yml` draait
  lint (`ruff`) + de testsuite + een Docker-build-verificatie bij elke
  push/PR die `forecasting/**` raakt. Nog geen CD-stap naar een staging-
  omgeving — die bestaat momenteel niet als apart concept naast de ene
  productieserver (zie DEPLOY.md).
- **Pip-audit: schoon per 2026-07-26** (`pip-audit -r requirements.txt`,
  0 kwetsbaarheden). De eerder hier gedocumenteerde 9 bevindingen
  (`click`, `starlette` x5, `pyarrow`, `pytest`, `python-dotenv`) komen niet
  meer terug bij een herrun — of dat komt doordat `requirements.txt` tussentijds
  is bijgewerkt of doordat de kwetsbaarheidsdatabase sindsdien is aangepast is
  niet met zekerheid vastgesteld, alleen de huidige uitkomst. Blijf dit
  periodiek herhalen; er is geen geautomatiseerde dependency-scan in de
  CI-pipeline (alleen lint+tests+build).
- **Geen ondergrens van 0 op voorspelde omzet.** Kwantielregressie legt
  geen niet-negativiteit af — bij lage-omzet winkels of lange horizons kan
  een p10 (of in theorie zelfs p50/p90) negatief uitkomen. De API
  (`/forecast`) geeft dat ongewijzigd terug; alleen het dashboard klemt
  weergavewaarden op 0 (`dashboard.js`, in `voorspel()`), puur cosmetisch.
  Een andere consument van de API kan dus nog steeds een negatief getal
  krijgen. Structureel oplossen (het model zelf een ondergrens geven, of
  de API-response al klemmen) is bewust niet gedaan — dat raakt de
  training-/serving-pijplijn en hoort bij Fase 3 (Forecast Intelligence),
  niet bij een cosmetische dashboard-fix.
- **Klantisolatie is nu afgedwongen (Fase 4 Stap 2), maar er is nog maar
  één klant.** `serving/app.py` checkt sinds Stap 2 per `/forecast`-verzoek
  of het gevraagde `store_id` bij de organisatie van de gebruikte API-key
  hoort (zie `FASE4-SAAS-FOUNDATION.md`). Op dit moment is er precies één
  gebootstrapte organisatie ("Tessar demo") die alle 1115 winkels uit het
  modelartefact bezit, dus dit is in de praktijk nog niet getoetst tegen
  een echte tweede klant — alleen in de testsuite
  (`tests/test_tenant_isolatie.py`). Accounts/self-service (Stap 3+) zijn
  nog niet gebouwd; nieuwe organisaties/klanten worden nu handmatig via
  `db.cli`/`db.migreer_keys_cli` aangemaakt.
- **Geen live deployment.** Draait lokaal via Docker Compose. Live
  deployment (bv. naast Certo, met een Caddy-reverse-proxy) en de
  daadwerkelijke website-demo-integratie zijn bewuste, losse
  vervolgstappen.
