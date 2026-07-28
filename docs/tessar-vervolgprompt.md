# Prompt voor de volgende sessie — Tessar-merkuitrol, fase 2

> Plakken in een nieuwe sessie (model naar keuze, bv. Sonnet), bij voorkeur met toegang tot
> `/Users/hamdeco/development/hamdoun` én
> `/Users/hamdeco/Downloads/Claude Downloads/Claude Code/Eerste workspace CODE/protocolchecker`.

---

Ik werk verder aan de Tessar-merkuitrol over mijn producten. Fase 1 is op
28 juli 2026 afgerond en teruggeschreven naar beide repos; deze sessie bouwt
daarop voort. Lees eerst de stand van zaken, dan de opdracht.

## Stand van zaken (geverifieerd, niet opnieuw uitzoeken)

- **Spec:** `hamdoun/docs/tessar-design-system-spec.md` — volledig designsysteem
  (oklch-kleurtokens uit de live site, IBM Plex-typografie, 4px/1.2-schaal,
  componentrichtlijnen, navy-dark-mode-regels).
- **Canonieke tokens:** `hamdoun/assets/tessar-tokens.css` — dé bron voor alle
  Tessar-kleuren/fonts. Wijzigingen gebeuren éérst hier, daarna doorgekopieerd
  naar productrepo's.
- **Protocolchecker-template:** thememechanisme is af. `THEMA=tessar` in `.env`
  → server levert `public/themes/tessar.css` als `/theme.css` ná `style.css`;
  zonder `THEMA` is `/theme.css` leeg en blijft de Certo-look exact zoals hij
  is. IBM Plex staat self-hosted in `public/fonts/` (offline-eis). Testsuite:
  52 tests groen, waaronder `tests/test_thema.py` (path-traversal, fonts,
  linkvolgorde).
- **Bewuste fix uit fase 1:** de inlogknop in `login.html` en
  `wachtwoord-resetten.html` gebruikt nu `button button-primary login-knop`
  (de oude class `ai-button` was dood sinds de componentconsolidatie van
  24 juli en de knop viel terug op browser-default grijs).

## Onwrikbare kaders (niet ter discussie, niet "verbeteren")

1. **Certo (de live Van Dijk Clinic-instance) blijft visueel ongewijzigd.**
   Alles wat je bouwt moet inert zijn zolang `THEMA` leeg is. Bij twijfel:
   maak vóór/na-screenshots zonder `THEMA` en vergelijk.
2. **Offline-eis:** geen externe stylesheets, fonts of CDN's in de
   Protocolchecker — alles self-hosted (dit heeft eerder een inlogpagina op
   een iPad zonder internet bevroren).
3. **Tokens hebben één bron:** `hamdoun/assets/tessar-tokens.css`. Nooit
   nieuwe kleurwaarden verzinnen; afwijkingen eerst daar doorvoeren.
4. **Geen wijzigingen aan bedrijfslogica** (auth, encryptie, klantreizen,
   AI-escalatie) — deze fase is presentatie en branding.

## Opdracht (in deze volgorde)

### 1. Tessar-logopakket + logo-swap in het thema
Er is nog geen Tessar-wordmark-SVG. Maak er een op basis van de bestaande
assets (`hamdoun/Tessar-logo-symbol.png`, `hamdoun/assets/tessar-logo.png` en
de tekststijl van de live site: "Tessar" in IBM Plex Sans 700,
letter-spacing −0.015em) in licht + donker, plus favicons (16/32/180) —
zelfde formatenset als `protocolchecker/public/logo/`. Breid het
thememechanisme uit zodat bij `THEMA=tessar` óók logo's, favicons en
paginatitels meewisselen (server-side of via CSS/JS — kies wat het kleinst en
robuustst is, en documenteer waarom). Van Dijk-logo's en "Certo"-naam blijven
het gedrag zonder `THEMA`.

**Klaar wanneer:** screenshots van login + app + klantpagina in beide thema's
tonen het juiste logo; zonder `THEMA` is er pixel-voor-pixel niets veranderd;
tests groen plus een nieuwe test die de logo-routes dekt.

### 2. HTTP-test voor de /theme.css-route
De route zelf (publiek vóór de auth-gate, 200 + leeg bestand zonder `THEMA`,
juiste Content-Type) is nog ongetest — dat is regressiegevoelig bij latere
`do_GET`-refactors. Voeg een test toe die de server echt aanspreekt
(threading + `HTTPServer` op een vrije poort volstaat).

### 3. E-mail- en tekstbranding parametriseren (als tijd het toelaat)
`server.py` bevat hardcoded "Van Dijk Clinic" in klant-e-mails en
`PRAKTIJK_*`-defaults. Maak hier nette `.env`-parameters van
(`PRAKTIJK_NAAM=` met Van Dijk als default zodat de live instance niets
merkt), zodat een Tessar-klant-deployment volledig zonder Van Dijk-sporen
kan draaien.

## Werkwijze

- Werk zelfstandig door met je eigen test-/reviewronde per stap (zoals
  gebruikelijk via `subagent-driven-development`): implementeer → draai de
  volledige testsuite → maak screenshots van beide thema's in licht én donker
  → laat een onafhankelijke subagent adversarieel reviewen → verwerk de
  bevindingen.
- Draai de bestaande suite vóór je begint (baseline) en na elke stap.
- Documenteer nieuwe `.env`-variabelen in `.env.example` én README.

## Beslisruimte

Zelf beslissen (en achteraf melden): implementatiedetails, bestandsindeling,
testopzet, SVG-opbouw van de wordmark. **Eerst aan mij voorleggen:** alles wat
de Certo-look zichtbaar verandert, wijzigingen aan de spec of de canonieke
tokens, en de vraag of Boekingsassistent al een eigen frontend moet krijgen
(bewust buiten deze fase gehouden).

## Rapportage

Sluit af met: (1) wat er gebouwd is met bestandspaden, (2) bewijs — testrun-
uitkomst en screenshots, (3) wat je hebt opengelaten, (4) welke keuzes een
beslissing van mij vragen. Kort en feitelijk, geen procesverslag.
