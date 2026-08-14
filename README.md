# tessar.nl

Statische marketingsite voor Tessar — AI-implementatie en AI-geïntegreerde
applicaties voor het Nederlandse mkb. Elke pagina is een losse, met de hand
gebouwde `.html`-bestand (geen build-stap, geen CMS); nieuwe pagina's volgen
de bestaande nav/hero/footer-structuur van bijvoorbeeld `chatbots.html`.

## Structuur

- `index.html`, `services.html`, `chatbots.html`, `prijzen.html`,
  `contact.html`, `blog.html` — de hoofdpagina's.
- `ai-*.html`, `workflow-*.html`, `bedrijfsprocessen-*.html` — blogartikelen,
  gelinkt vanaf `blog.html`.
- `assets/` — logo's, favicons, `tessar-tokens.css` (canonieke kleur-/font-tokens).
- `support.js`, `tessar-concierge-widget.js` — gedeelde scripts, geladen door
  meerdere pagina's.
- `docs/content/conceptartikelen/` — brondrafts van de blogartikelen
  (markdown, met redactielog en checklist-status per artikel) uit de n8n
  content-pijplijn — zie die map's `README.md` voor hoe die pijplijn werkt.
- `preview/uploads/` — **niet aanraken.** Bevat materiaal van een klantproject
  (vandijkprotocol.tessar.nl); expliciet uitgesloten van de deploy-workflow.
- `n8n-workflows/` — brondefinities van de n8n-workflows die de content-
  pijplijn draaien, plus hun geteste JS-logica.
- `docs/superpowers/` — design specs en implementatieplannen per feature.

## Deploy

Elke push naar `main` triggert `.github/workflows/deploy-tessar.yml`: een
rsync van de repo-root naar de productieserver, direct naar `tessar.nl`
(geen staging-omgeving, geen preview-URL). Behandel `main` dus als live.

## Testen

- `npm run test:unit` — kale `node:assert`-tests, geen dependencies (zelfde
  stijl als `n8n-workflows/src/*.test.js`).
- `npm run test:e2e` — Playwright-tests voor `tessar-concierge-widget.js`
  (devdependency, eenmalig `npx playwright install chromium` nodig). Draait
  tegen een lokale statische server met het echte widget-bestand; de
  n8n-webhook wordt gemockt, er gaan geen requests naar productie.
- `npm test` draait beide.

De systeemprompt en overige backend-logica van Tess (n8n-workflow "Tessar AI
Concierge - Website") leven **niet** in deze repo — zie
`docs/tessar-concierge-systeemprompt.md` voor de laatst bekende, vastgelegde
tekst en wijzigingsgeschiedenis.
