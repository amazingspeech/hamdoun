# Release checklist — forecasting

Herbruikbaar per release naar `forecasting-demo.tessar.nl`. Loop 'm van boven
naar beneden af; sla geen stap over omdat "het toch wel goed zal zijn" — dat
is precies waar dit document voor is.

**Staging:** er is bewust geen aparte staging-omgeving. "Staging" betekent
hier: stap 4 van `deploy/DEPLOY.md` (image lokaal op de server bouwen en
handmatig opstarten vóór `docker compose up -d`) én lokaal verifiëren via
`docker compose up api` (root `docker-compose.yml`) vóórdat je release-tagt.
Pas dit uitgangspunt aan zodra er een tweede klant/omgeving bijkomt die een
echte, losstaande staging rechtvaardigt.

## Pre-release

- [ ] `git status` is schoon op de branch die je uitrolt — geen losse
      onbedoelde wijzigingen meegenomen.
- [ ] CI is groen op de laatste commit (`.github/workflows/forecasting-ci.yml`
      — lint, testsuite, Docker-build-verificatie). Controleer op GitHub, ga
      niet af op "het draaide lokaal wel".
- [ ] Testsuite lokaal nogmaals gedraaid als er sinds de laatste CI-run nog
      iets gewijzigd is:
      `DYLD_LIBRARY_PATH=<pad-naar-libomp> PYTHONPATH=.venv/lib/python3.9/site-packages
      python3 -m pytest -v` (macOS-specifieke env-vars, zie KNOWN-LIMITATIONS.md
      voor waarom).
- [ ] `pip-audit -r requirements.txt` schoon, of nieuwe bevindingen bewust
      geaccepteerd/uitgesteld — nooit stilzwijgend genegeerd.
- [ ] Geen migraties van toepassing (er is geen database in deze fase) —
      zodra Fase 4 (SaaS Foundation) een database toevoegt, voeg hier een
      concrete migratie-check-stap toe.
- [ ] `.env` op de server bevat alle verplichte variabelen uit
      `deploy/.env.example` (`MODEL_VERSION` met een echte, op Rossmann-data
      getrainde versie — nooit de synthetische testset) en
      `EXPOSE_API_DOCS` staat op `false` of ontbreekt (nooit `true` op een
      publieke deployment).
- [ ] Als het modelartefact wijzigt: RMSPE en coverage van de nieuwe versie
      bekeken (`GET /metrics` na deploy, of het trainingsrapport) — geen
      duidelijke achteruitgang t.o.v. de vorige versie zonder dat bewust te
      accepteren.

## Release

- [ ] Versie-tag gezet op de commit die uitgerold wordt (bv.
      `git tag forecasting-v<datum>` — er is nog geen semver-schema, een
      datumtag volstaat tot Fase 4).
- [ ] Wijzigingen sinds de vorige release kort genoteerd (dit project heeft
      nog geen `CHANGELOG.md` — tot die er is, volstaat de samenvatting in
      de PR/commit-berichten sinds de vorige tag: `git log <vorige-tag>..HEAD
      --oneline`).
- [ ] `deploy/DEPLOY.md` gevolgd stap voor stap, in volgorde — met name
      stap 4 (image los bouwen en testen vóór `up -d`) niet overslaan, ook
      niet bij een "kleine" wijziging.
- [ ] Vóór de eerste `docker compose run`/`up` op de server: `api_keys.json`
      en `audit.log` bestaan en zijn `chmod 666` (zie README.md sectie 2 /
      DEPLOY.md stap 3 — de container draait als non-root en kan anders niet
      schrijven).
- [ ] Rollback voorbereid: `docker compose images` of `docker images` laat
      het huidige, nog draaiende image-ID zien vóórdat je een nieuwe build
      erover heen zet — noteer het, zodat rollback (zie hieronder) niet hoeft
      te gokken welk image "het vorige" was.

## Post-release

- [ ] Smoke test op productie: `curl https://forecasting-demo.tessar.nl/health`
      geeft `{"status":"ok","model_versie":"<verwachte versie>"}`.
- [ ] Dashboard handmatig geopend in een browser: winkel kiezen, voorspellen,
      controleren dat de startdatum automatisch op de dag ná de
      trainingsperiode staat (bevestigt dat het juiste model geladen is).
- [ ] `docker compose ps` toont de container als `healthy` (niet alleen
      `Up`) — de healthcheck moet minstens één cyclus gedraaid hebben
      (~30s wachten na opstarten).
- [ ] Certo (`vandijkprotocol.tessar.nl`) en n8n (`n8n.tessar.nl`) op
      dezelfde server nog steeds normaal bereikbaar — verplicht na elke
      Caddy-wijziging, sowieso een goede gewoonte na elke deploy op deze
      gedeelde server.
- [ ] Caddy-logs (`/var/log/caddy/forecasting-demo.log`) een paar minuten
      gevolgd op ongewone errors na de release.

## Rollback

Gebruik dit als een van de post-release-checks faalt.

1. Stop de nieuwe container: `docker compose down` (in
   `/home/job/forecasting-demo/deploy`).
2. Vorige image terugzetten: bouw niet opnieuw — als je het image-ID van
   vóór de release hebt genoteerd (zie hierboven), start die direct:
   `docker run` met dat ID, of `git checkout <vorige-tag> -- forecasting/`
   gevolgd door een schone `docker compose build` als het oude image niet
   meer lokaal beschikbaar is.
3. `curl http://127.0.0.1:8010/health` bevestigt dat de oude versie weer
   draait vóórdat je verder onderzoekt wat er misging.
4. Geen `MODEL_VERSION`-wijziging in `.env` nodig als alleen de code
   teruggedraaid wordt en het modelartefact ongewijzigd bleef — check dat
   expliciet, ga er niet van uit.
