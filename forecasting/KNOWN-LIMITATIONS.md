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
- **Geen CI-pipeline.** `pip-audit` en de testsuite zijn handmatige
  controles vóór oplevering, geen geautomatiseerde build-gate — die bestaat
  in deze fase niet.
- **9 pip-audit-bevindingen, gebonden aan de lokale ontwikkelomgeving, niet
  aan de toolkit-code.** `pip-audit` (uitgevoerd tijdens Task 20, finale
  verificatie) vond 9 bekende kwetsbaarheden in `click`, `starlette` (x5),
  `pyarrow`, `pytest` en `python-dotenv`. Elke gepatchte versie vereist
  Python ≥3.10; deze lokale ontwikkelmachine heeft alleen Python 3.9.6
  (Xcode's meegeleverde interpreter) beschikbaar, en een upgrade naar een
  nieuwere Python via Homebrew bleek geblokkeerd: het vereist een Xcode-versie
  die op zijn beurt een nieuwere macOS vereist dan deze machine draait (macOS
  15.5) — een macOS-upgrade is disproportioneel voor het sluiten van
  dependency-audit-bevindingen op een lokale toolkit. `requirements.in`
  bevat alleen ondergrenzen (`>=`), dus een `pip install --upgrade` op een
  machine met Python ≥3.10 lost dit direct op — maar de Docker-image bouwt
  uit `requirements.txt`, een exact-gepinde lock-file die hier onder Python
  3.9 is gegenereerd en dus dezelfde kwetsbare versies bevat. `python:3.11-
  slim` in de `Dockerfile` lost dit dus niet automatisch op: `requirements.txt`
  moet eerst opnieuw gegenereerd worden (`pip install --upgrade -r
  requirements.in && pip freeze > requirements.txt`) op een machine met
  Python ≥3.10, en dat gecommit, vóórdat een Docker-build de patches
  daadwerkelijk oppikt.
- **Geen live deployment.** Draait lokaal via Docker Compose. Live
  deployment (bv. naast Certo, met een Caddy-reverse-proxy) en de
  daadwerkelijke website-demo-integratie zijn bewuste, losse
  vervolgstappen.
