# Tessar Premium Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vervang het huidige donkere, cyaan-blauwe, beeldloze kleursysteem van tessar.nl door het in de spec vastgelegde lichte oker/teal-systeem met documentaire fotografie, over alle 13 pagina's (index.src.html/index.html als homepage meegerekend), zonder de SEO/curl-crawlbaarheid te verslechteren.

**Architecture:** Eén nieuw gedeeld tokenbestand (`assets/tessar-design-tokens.css`) vervangt de tot nu toe overal gedupliceerde inline `:root`-blokken. Elke pagina krijgt een `<link>` naar dat bestand plus zijn eigen, kleinere aanpassingen (hero-markup, koptekst-lettertype, component-audit). Gedeelde JS-widgets (cookie-banner, Tess-conciërge) en het merkicoon worden apart herkleurd, los van de pagina-tokens. Hero-fotografie wordt **niet door implementers gegenereerd** — dat blijft een controller-taak met expliciete toestemming van de gebruiker per generatie-batch (credit-budget).

**Tech Stack:** Statische HTML/CSS, geen build-tooling behalve voor `index.src.html` (Playwright-prerender via `npm run build`). Python 3 + Pillow voor deterministische beeldbewerking (icoon-herkleuring, geen AI-generatie). Higgsfield-CLI voor hero-fotografie (uitsluitend door de controller, na toestemming).

**Spec:** `docs/superpowers/specs/2026-09-03-tessar-premium-redesign-design.md`

## Global Constraints

- **SEO/curl-crawlbaarheid mag niet verslechteren.** Elke wijziging blijft zichtbaar in de statische, ongerenderde HTML (`curl`/`grep`-verifieerbaar, geen JS-afhankelijkheid). `index.src.html` gaat via `npm run build` vóór elke curl-check.
- **Geen Higgsfield-beeldgeneratie door implementers.** Waar een taak een nieuwe hero-foto nodig heeft, gebruikt de implementer een door de controller aangeleverd, al goedgekeurd bestand (pad staat in de taak zodra beschikbaar) — de implementer roept zelf nooit `higgsfield generate` aan.
- **Credit-budget is krap.** ~180 Higgsfield-credits resterend (starter-plan) bij aanvang van dit plan. Zie "Fotografie-strategie" hieronder — er worden gedeelde foto's per "shoot" hergebruikt over verwante pagina's, niet 9 losse eenmalige shoots.
- **Exacte kleurtokens** (uit spec sectie 1, letterlijk over te nemen, nergens anders vandaan):
  ```css
  :root {
    color-scheme: light;
    --bg:            #F7F2E9;
    --surface:       #F1EADA;
    --surface-inset: #EAE1CC;
    --border:        #DCD0B8;
    --text:          #211C14;
    --text-muted:    #5F5646;
    --text-muted-2:  #8A8070;
    --accent:        #0F5C57;
    --accent-hover:  #0C4B47;
    --accent-text:   #0F5C57;
    --accent-dim:    #E3EEEC;
    --ok-bg:         #EAF3E9;
    --ok-border:     #C3DCC0;
    --ok-text:       #2F6B2C;
    --danger-bg:     #FBEAE6;
    --danger-border: #E8C3B8;
    --danger-text:   #A23F24;
  }
  ```
- **`theme-color`-meta wordt overal** `<meta name="theme-color" content="#F7F2E9">` (was `content="#0a0a0f"`).
- **Eén CTA-label sitewide** blijft ongewijzigd: "Plan gratis kennismaking" (of de bestaande header-variant "Plan gesprek" — dat onderscheid bestond al vóór dit project en blijft zo, dit plan verandert geen CTA-tekst).
- **Geen liggend streepje (—/em-dash)** in nieuwe of aangepaste zichtbare copy.
- **`npm test` moet groen blijven** na elke taak die JS/widget-bestanden raakt.

## Fotografie-strategie (geldt voor alle hero-taken)

Negen pagina's krijgen een nieuwe/vervangende hero-foto (zie pagina-inventaris in de spec). Tegen het credit-budget aan wordt dit **niet** als negen losse fotoshoots aangepakt, maar als een klein aantal "shoots" die hergebruikt worden met een andere crop/uitsnede per pagina — zoals een echt fotograaf-opdracht voor één merk ook één coherente set oplevert, geen negen incidentele losse beelden:

1. **Shoot A — "Aan de balie/telefoon"**: voor `ai-telefonist-voor-bedrijf.html` en `ai-receptioniste-voor-bedrijven.html` (nauw verwante onderwerpen: telefonie/receptie).
2. **Shoot B — "Klantcontact/chat"**: voor `ai-chatbot-voor-bedrijven.html` en `chatbots.html`.
3. **Shoot C — "Kantoor/proces"**: voor `bedrijfsprocessen-automatiseren-met-ai.html`, `workflow-automatisering-met-ai.html` en `ai-implementatie-laten-uitvoeren.html`.
4. **Shoot D — homepage**: eigen, herkenbaarste beeld (de belangrijkste pagina verdient een uniek beeld, geen hergebruikte crop).
5. **Shoot E — `services.html`**: eigen beeld (overzichtspagina van alle diensten, past niet bij één van de andere shoots).

Dit brengt het aantal generatie-momenten van negen naar vijf, elk met een paar downloadbare crops voor de betrokken pagina's. **Elke shoot is een aparte controller-taak vóór de bijbehorende implementatietaken** (zie Taak 6-7-8-9-10 hieronder) — de gebruiker geeft per shoot toestemming, zoals eerder deze sessie bij de homepage en AI-telefonist-pagina.

---

### Taak 1: Gedeeld tokenbestand aanmaken

**Files:**
- Create: `assets/tessar-design-tokens.css`

**Interfaces:**
- Produces: een `<link rel="stylesheet" href="./assets/tessar-design-tokens.css">`-regel die alle volgende pagina-taken in hun `<head>` opnemen, vóór hun eigen `<style>`-blok.

- [ ] **Stap 1: Maak het bestand aan met exact de tokens uit de Global Constraints**

```css
:root {
  color-scheme: light;
  --bg:            #F7F2E9;
  --surface:       #F1EADA;
  --surface-inset: #EAE1CC;
  --border:        #DCD0B8;
  --text:          #211C14;
  --text-muted:    #5F5646;
  --text-muted-2:  #8A8070;
  --accent:        #0F5C57;
  --accent-hover:  #0C4B47;
  --accent-text:   #0F5C57;
  --accent-dim:    #E3EEEC;
  --ok-bg:         #EAF3E9;
  --ok-border:     #C3DCC0;
  --ok-text:       #2F6B2C;
  --danger-bg:     #FBEAE6;
  --danger-border: #E8C3B8;
  --danger-text:   #A23F24;
}
```

- [ ] **Stap 2: Verifieer dat het bestand losstaand geldig CSS is**

Run: `npx --yes csso-cli --version >/dev/null 2>&1 || true; node -e "require('fs').readFileSync('assets/tessar-design-tokens.css','utf8')"`

Simpeler en voldoende: open het bestand in de browser-devtools-achtige check door een tijdelijke HTML te maken:
Run: `node -e "const css=require('fs').readFileSync('assets/tessar-design-tokens.css','utf8'); if(!css.includes('--accent:') || !css.includes('#0F5C57')) throw new Error('tokens missing'); console.log('OK, ' + css.split(String.fromCharCode(10)).length + ' regels');"`
Expected: `OK, <n> regels` zonder foutmelding.

- [ ] **Stap 3: Commit**

```bash
git add assets/tessar-design-tokens.css
git commit -m "feat: gedeeld design-tokens-bestand voor lichte oker/teal-huisstijl"
```

---

### Taak 2: Merkicoon en favicons herkleuren (cyaan → teal)

Het enige daadwerkelijk gebruikte merkbeeld is `assets/tessar-icon-optimized.png` (32×35, wireframe-kubus-icoon, gebruikt op alle 13 pagina's, inclusief de homepage). De overige bestanden die op "logo" lijken (`assets/logo-*.png`, `assets/logo-mark*.svg`, `assets/tessar-icon.png`, `assets/tessar-logo.png`, `assets/Tessar-logo-symbol.webp`) zijn **niet gekoppeld aan enige pagina** (geverifieerd: `grep -rl` op alle 14 `.html`-bestanden op schijf geeft 0 treffers — 14 fysieke bestanden omdat `index.src.html` en het gebakken `index.html` allebei meetellen als losse bestanden voor één logische homepage-pagina) — `logo-full-dark.png`/`logo-full-light.png` bevatten zelfs een volledig ander, niet-gerelateerd merk ("BlackLarch", een dennenboom-logo). Deze taak raakt **alleen** `tessar-icon-optimized.png` en de drie favicon-bestanden die daarvan zijn afgeleid; de ongebruikte bestanden blijven onaangeroerd (opruimen is een aparte, niet in deze spec opgenomen beslissing).

**Files:**
- Modify: `assets/tessar-icon-optimized.png`
- Modify: `assets/favicon-16.png`
- Modify: `assets/favicon-32.png`
- Modify: `assets/apple-touch-icon.png`
- Create (tijdelijk script, niet commiten): `/tmp/recolor-icon.py`

**Interfaces:**
- Consumes: niets van eerdere taken.
- Produces: dezelfde vier bestandsnamen, nu met teal (`#0F5C57`-familie) in plaats van cyaan (`#00A8FF`-familie) — geen enkele pagina-referentie verandert (zelfde bestandsnamen).

- [ ] **Stap 1: Schrijf het herkleuringsscript**

De huidige iconen zijn anti-aliased PNG's met een cyaan hoofdkleur (~200° hue in HSV) en een donkerdere blauw-grijze schaduwkleur voor de kubus-dieptelijnen. Een uniforme hue-rotatie (delta tussen huidige en nieuwe hue, toegepast op elke pixel, verzadiging/helderheid ongemoeid) behoudt de highlight/schaduw-verhoudingen van het icoon.

```python
# /tmp/recolor-icon.py
import colorsys
from PIL import Image

# Bron-hue: het fel-cyaan #00A8FF (de dominante, meest verzadigde kleur
# in het icoon). Doel-hue: het nieuwe accent #0F5C57.
def hex_to_hsv(hexstr):
    r = int(hexstr[0:2], 16) / 255
    g = int(hexstr[2:4], 16) / 255
    b = int(hexstr[4:6], 16) / 255
    return colorsys.rgb_to_hsv(r, g, b)

src_h, _, _ = hex_to_hsv("00A8FF")
dst_h, _, _ = hex_to_hsv("0F5C57")
delta_h = dst_h - src_h  # hue-verschuiving, toe te passen op elke pixel

def shift_hue(img_path, out_path):
    img = Image.open(img_path).convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            hh = (hh + delta_h) % 1.0
            nr, ng, nb = colorsys.hsv_to_rgb(hh, s, v)
            pixels[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    img.save(out_path, "PNG")

for f in [
    "assets/tessar-icon-optimized.png",
    "assets/favicon-16.png",
    "assets/favicon-32.png",
    "assets/apple-touch-icon.png",
]:
    shift_hue(f, f)
    print("herkleurd:", f)
```

- [ ] **Stap 2: Voer het script uit**

Run: `python3 /tmp/recolor-icon.py`
Expected: vier regels `herkleurd: assets/...` zonder foutmelding.

- [ ] **Stap 3: Verifieer visueel en met een kleurcheck**

Run:
```bash
python3 -c "
from PIL import Image
img = Image.open('assets/tessar-icon-optimized.png').convert('RGBA')
colors = [c for c in img.getcolors(maxcolors=100000) if c[1][3] > 200]
colors.sort(reverse=True)
top = colors[0][1]
print('top opaque color:', '#%02X%02X%02X' % top[:3])
"
```
Expected: de uitvoer toont een teal-achtige hex (groen/blauwe familie rond `#0F` / `#5C` / `#57`-achtige tinten), niet meer een cyaan `#00A8FF`-achtige waarde. Bekijk daarnaast `assets/tessar-icon-optimized.png` visueel (via de Read-tool of een browser) om te bevestigen dat de kubus-vorm intact is gebleven en er geen banding/artefacten zijn ontstaan.

- [ ] **Stap 4: Ruim het tijdelijke script op en commit**

```bash
rm /tmp/recolor-icon.py
git add assets/tessar-icon-optimized.png assets/favicon-16.png assets/favicon-32.png assets/apple-touch-icon.png
git commit -m "feat: merkicoon en favicons herkleurd van cyaan naar teal"
```

---

### Taak 3: Cookie-consent-banner herkleuren

**Files:**
- Modify: `assets/tessar-prefs.js`
- Test: geen geautomatiseerde test bestaat hiervoor; visuele verificatie via Playwright-screenshot (stap 3).

**Interfaces:**
- Consumes: niets.
- Produces: dezelfde publieke API van `tessar-prefs.js` (dit bestand wordt ongewijzigd aangeroepen door alle 13 pagina's via `<script src="./assets/tessar-prefs.js" defer></script>`) — alleen de kleurwaarden in de gerenderde banner veranderen.

- [ ] **Stap 1: Lokaliseer de hardcoded kleuren**

Run: `grep -n "#001a2e\|#0f1115\|#7dd3fc\|#b8b8b8\|#f2f2f2\|oklch(70% 0.14 220)" assets/tessar-prefs.js`

Dit toont de exacte regels. Vervang elk consequent:
- `#0f1115` (donkere paneel-achtergrond) → `#F1EADA` (`--surface`)
- `#001a2e` (donkere tekst-op-accent, bijv. knoptekst op de accentkleur) → `#F7F2E9` (`--bg`, want de nieuwe knop wordt donker-op-licht i.p.v. licht-op-donker — zie volgende punt)
- `oklch(70% 0.14 220)` (cyaan accent/knop-achtergrond) → `#0F5C57` (`--accent`)
- `#7dd3fc` (lichte cyaan link-kleur) → `#0F5C57` (`--accent-text`)
- `#b8b8b8` (gedempte tekst) → `#5F5646` (`--text-muted`)
- `#f2f2f2` (lichte hoofdtekst, was licht-op-donker) → `#211C14` (`--text`, want de banner wordt nu donkere tekst op een lichte achtergrond)

- [ ] **Stap 2: Voer de vervangingen door**

Bewerk `assets/tessar-prefs.js` met deze exacte mapping. Controleer na het bewerken dat geen van de oude waarden nog voorkomt:

Run: `grep -c "#001a2e\|#0f1115\|#7dd3fc\|#b8b8b8\|#f2f2f2\|oklch(70% 0.14 220)" assets/tessar-prefs.js`
Expected: `0`

- [ ] **Stap 3: Visuele verificatie**

Serveer de site lokaal en maak een screenshot van de cookie-banner (verschijnt bij een verse paginalaad zonder eerder gegeven toestemming — gebruik een incognito/nieuwe Playwright-context zodat er geen bestaande `localStorage`-voorkeur is):

```bash
python3 -m http.server 8795 --directory . &
SERVER_PID=$!
sleep 1
cat > ./__cookie_shot.mjs <<'SCRIPT'
import { chromium } from '@playwright/test';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1024, height: 800 } });
await page.goto('http://localhost:8795/contact.html', { waitUntil: 'networkidle' });
await page.screenshot({ path: '/tmp/cookie-banner-check.png' });
await browser.close();
SCRIPT
node ./__cookie_shot.mjs
rm ./__cookie_shot.mjs
kill $SERVER_PID
```

Bekijk `/tmp/cookie-banner-check.png` (via de Read-tool): de banner moet nu warm oker/wit met donkere tekst en een teal-knop tonen, geen donkerblauw meer.

- [ ] **Stap 4: Commit**

```bash
git add assets/tessar-prefs.js
git commit -m "feat: cookie-consent-banner herkleurd naar het lichte oker/teal-thema"
```

---

### Taak 4: Tess-conciërge-widget herkleuren

**Files:**
- Modify: `tessar-concierge-widget.js`
- Test: `tessar-concierge-widget.test.js` (bestaande unit-tests, mogen niet breken — ze testen logica, geen kleuren)

**Interfaces:**
- Consumes: niets.
- Produces: dezelfde publieke API (dit bestand exporteert geen kleur-gerelateerde functies; de bestaande `npm run test:unit`-tests testen tekst-verwerkingslogica, niet styling, en moeten dus ongewijzigd slagen).

- [ ] **Stap 1: Lokaliseer alle hardcoded kleuren**

Run: `grep -n "oklch(" tessar-concierge-widget.js`

De widget gebruikt een eigen, in zichzelf consistente set `oklch(L% C H)`-waarden met hue `220` (blauw, het huidige accent), hue `240-255` (blauwig-donkere panelen/achtergronden), en hue `150` (groen, functionele succes-status — deze blijft ongewijzigd, is geen merk-accent).

- [ ] **Stap 2: Voer de vervangingen door**

Vervang consequent, overal waar ze voorkomen:
- Elke `oklch(70% 0.14 220)` (het huidige merk-accent) → `oklch(34% 0.05 175)` (equivalent van `#0F5C57` in oklch, het nieuwe teal-accent)
- Elke achtergrond/paneel-kleur met hue `240-255` bij lage lichtheid (`oklch(18-30% ... 240-255)`, de donkere paneel-achtergronden van het chatvenster) → dezelfde lichtheid maar met hue `70` (de warme oker-ondertoon van `--surface`/`--surface-inset`), bijv. `oklch(18% 0.02 255)` → `oklch(18% 0.02 70)`, `oklch(30% 0.05 240)` → `oklch(30% 0.05 70)`
- Elke lichte tekst-kleur met hue `250` (`oklch(70-98% ... 250)`, bedoeld als lichte tekst op de donkere panelen) → dezelfde structuur maar hue `70` in plaats van `250`, bijv. `oklch(92% 0.008 250)` → `oklch(92% 0.008 70)`
- `oklch(70% 0.18 150)` (functionele succes-kleur) **blijft ongewijzigd** — dit is een status-kleur, geen merk-accent (zie spec sectie 1: succes-/foutkleuren blijven functioneel gescheiden).

- [ ] **Stap 3: Draai de bestaande unit-tests**

Run: `npm run test:unit`
Expected: alle tests slagen (deze testen tekst-streaming-logica, niet kleuren — een regressie hier zou duiden op een per ongeluk geraakte niet-kleur-regel).

- [ ] **Stap 4: Visuele verificatie van de widget**

```bash
python3 -m http.server 8796 --directory . &
SERVER_PID=$!
sleep 1
cat > ./__widget_shot.mjs <<'SCRIPT'
import { chromium } from '@playwright/test';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 500, height: 700 } });
await page.goto('http://localhost:8796/contact.html', { waitUntil: 'networkidle' });
await page.click('#tess-concierge-launcher, [id*="launcher"], [class*="launcher"]').catch(() => {});
await page.waitForTimeout(500);
await page.screenshot({ path: '/tmp/widget-check.png' });
await browser.close();
SCRIPT
node ./__widget_shot.mjs
rm ./__widget_shot.mjs
kill $SERVER_PID
```

Bekijk `/tmp/widget-check.png`: als de launcher-knop niet aanklikbaar bleek (selector kan afwijken — inspecteer eerst `tessar-concierge-widget.js` op de daadwerkelijke launcher-id/class), pas de selector aan en herhaal. Het geopende venster moet warm/licht ogen, geen donkerblauw paneel meer.

- [ ] **Stap 5: Commit**

```bash
git add tessar-concierge-widget.js
git commit -m "feat: Tess-conciërge-widget herkleurd naar het lichte oker/teal-thema"
```

---

### Taak 5: Outfit-lettertype toevoegen (referentie-implementatie op de homepage)

Deze taak legt het patroon vast dat alle volgende pagina-taken herhalen: Outfit laden naast de bestaande IBM Plex-fonts, en toepassen op H1/H2.

**Files:**
- Modify: `index.src.html`

**Interfaces:**
- Produces: het `<link>`-patroon voor Outfit en de exacte vervangingsregel (`'IBM Plex Sans'` → `'Outfit'` binnen `<h1`/`<h2`-inline-`style`-attributen) die elke volgende pagina-taak toepast op zijn eigen H1/H2's.

- [ ] **Stap 1: Voeg de Outfit-font-link toe naast de bestaande Google Fonts-link**

Zoek de bestaande regel (rond de `<head>`):
```html
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```
Vervang door (Outfit toegevoegd aan dezelfde Google Fonts-aanvraag, één request, geen extra DNS-lookup):
```html
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
```

- [ ] **Stap 2: Pas de H1 toe**

Zoek de hero-H1 (`<h1 style="font:800 clamp(2.25rem,5.6vw,4rem)/1.15 'IBM Plex Sans';...`) en vervang `'IBM Plex Sans'` door `'Outfit'` in die ene `style`-declaratie. Doe hetzelfde voor elke andere `<h1` en `<h2`-tag in het bestand die `'IBM Plex Sans'` in zijn `font:`-shorthand heeft — lopende tekst (`<p>`, `<span>` zonder kop-rol) blijft `'IBM Plex Sans'`.

Run: `grep -c "<h1[^>]*'IBM Plex Sans'\|<h2[^>]*'IBM Plex Sans'" index.src.html`
Expected: `0` (alle H1/H2-inline-fonts zijn nu Outfit)

- [ ] **Stap 3: Build en verifieer**

```bash
npm run build
grep -c "Outfit" index.html
```
Expected: minstens 2 (de font-link + minstens één H1/H2-declaratie).

- [ ] **Stap 4: Commit**

```bash
git add index.src.html index.html
git commit -m "feat: Outfit-lettertype voor koppen naast IBM Plex Sans/Mono"
```

---

### Taak 6 (controller, geen implementer-dispatch): Shoot D — homepage hero-foto

Deze taak wordt **door de controller uitgevoerd, niet door een gedispatchte implementer** (Global Constraint: geen Higgsfield-generatie door implementers). Volgt hetzelfde patroon als eerder deze sessie: concept voorstellen, toestemming vragen, 2-3 varianten genereren, gebruiker laat kiezen, downloaden en optimaliseren naar `assets/hero-visual-v2.webp` (+ `-sm` variant) — documentair/foto-realistisch, geen sculptuur (spec sectie 4). Resultaat: bestandspad(en) die Taak 11 als input consumeert.

**Interfaces:**
- Produces: `assets/hero-visual-v2.webp` + `assets/hero-visual-v2-sm.webp` (of vergelijkbare namen, definitief pad wordt genoteerd bij afronding van deze taak) — vervangt `assets/hero-visual.webp`/`-sm.webp` uit de vorige (sculptuur-)aanpak.

---

### Taak 7 (controller): Shoot A — telefonie/receptie hero-foto's

Voor `ai-telefonist-voor-bedrijf.html` en `ai-receptioniste-voor-bedrijven.html`. Zelfde controller-only aanpak als Taak 6. Documentair, geen sculptuur — vervangt de bestaande hoorn-sculptuurfoto op de AI-telefonist-pagina.

**Interfaces:**
- Produces: `assets/blog/ai-telefonist-hero-v2.webp` + `-sm.webp`, `assets/blog/ai-receptioniste-hero.webp` + `-sm.webp` (twee crops/varianten uit dezelfde shoot, of twee losse maar thematisch identieke generaties — ter beoordeling bij uitvoering, binnen het credit-budget).

---

### Taak 8 (controller): Shoot B — klantcontact/chat hero-foto's

Voor `ai-chatbot-voor-bedrijven.html` en `chatbots.html`.

**Interfaces:**
- Produces: `assets/blog/ai-chatbot-hero.webp` + `-sm.webp`, `assets/chatbots-hero.webp` + `-sm.webp`.

---

### Taak 9 (controller): Shoot C — kantoor/proces hero-foto's

Voor `bedrijfsprocessen-automatiseren-met-ai.html`, `workflow-automatisering-met-ai.html`, `ai-implementatie-laten-uitvoeren.html`.

**Interfaces:**
- Produces: `assets/blog/bedrijfsprocessen-hero.webp` + `-sm.webp`, `assets/blog/workflow-hero.webp` + `-sm.webp`, `assets/blog/ai-implementatie-hero.webp` + `-sm.webp`.

---

### Taak 10 (controller): Shoot E — services.html hero-foto

**Interfaces:**
- Produces: `assets/services-hero.webp` + `-sm.webp`.

---

### Taak 11: Homepage — tokens, hero, typografie, SEO

**Files:**
- Modify: `index.src.html`
- Modify: `index.html` (via `npm run build`, niet handmatig)

**Interfaces:**
- Consumes: `assets/tessar-design-tokens.css` (Taak 1), herkleurd icoon (Taak 2), Outfit-patroon (Taak 5, al toegepast), hero-foto uit Taak 6.

- [ ] **Stap 1: Verwijder het huidige inline `:root`-blok en voeg de link toe**

Zoek het bestaande blok (met de extra `--danger-*`/`--success-*`-page-lokale tokens voor de before/after-vergelijking) en vervang door een verwijzing naar het gedeelde bestand plus alléén de page-lokale, niet-gedeelde tokens:

```css
/* --danger-*/--success-* blijven hier: page-lokaal voor de before/after-vergelijking,
   horen niet in het gedeelde tokenbestand (komen alleen op deze pagina voor). */
:root {
  --danger-bg: oklch(97% 0.02 30);
  --danger-border: oklch(88% 0.05 30);
  --danger-text: oklch(45% 0.12 30);
  --danger-accent: oklch(55% 0.16 30);
  --success-bg: oklch(96% 0.03 155);
  --success-border: oklch(85% 0.06 155);
  --success-text: oklch(40% 0.10 155);
  --success-accent: oklch(50% 0.14 155);
}
```
(Deze waarden zijn de donkere originelen omgezet naar lichte equivalenten met behoud van dezelfde hue — rood blijft rood, groen blijft groen, alleen lichtheid/achtergrond omgekeerd voor het lichte thema.)

In de `<head>`, vóór het bestaande `<style>`-blok:
```html
<link rel="stylesheet" href="./assets/tessar-design-tokens.css">
```

- [ ] **Stap 2: Vervang het hero-beeld**

In de `.hero-visual`-`<img>` (toegevoegd in een eerdere sessie-taak): vervang `src`/`srcset` van `./assets/hero-visual.webp`/`hero-visual-sm.webp` naar de nieuwe bestanden uit Taak 6. Verwijder de `.hero-visual::before`-warme-gloed-CSS en de `mask-image`-fade die specifiek op de sculptuur-foto waren afgestemd (donker-op-donker-effect) — met een documentaire foto op een lichte pagina-achtergrond is een scherpe, volledig beeldvullende foto met een scrim precies op de tekstzone het juiste patroon (spec sectie 5), geen wegvloeiende rand.

- [ ] **Stap 3: `theme-color` bijwerken**

Zoek `<meta name="theme-color" content="#0a0a0f">` → `content="#F7F2E9"`.

- [ ] **Stap 4: SEO — Organization + WebSite toevoegen aan het bestaande JSON-LD**

Het bestaande `ProfessionalService`-blok blijft staan; voeg `Organization` en `WebSite` toe via `@graph` in hetzelfde `<script type="application/ld+json">`-blok (niet een nieuw blok — één blok per logische schema-groep, spec sectie 10):

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://tessar.nl/#org",
      "name": "Tessar",
      "url": "https://tessar.nl",
      "logo": "https://tessar.nl/assets/tessar-icon-optimized.png"
    },
    {
      "@type": "WebSite",
      "@id": "https://tessar.nl/#website",
      "name": "Tessar",
      "url": "https://tessar.nl",
      "publisher": { "@id": "https://tessar.nl/#org" }
    },
    {
      "@type": "ProfessionalService",
      "@id": "https://tessar.nl/#service"
      /* bestaande ProfessionalService-velden hier ongewijzigd overnemen */
    }
  ]
}
```

- [ ] **Stap 5: Componentregels-audit (spec sectie 7)**

Run: `grep -c "—" index.src.html`
Expected: `0` in zichtbare copy-teksten (JSON-LD/comments negeren — controleer elke treffer handmatig, vervang liggende streepjes in copy door een punt/komma/"en").

Controleer de "why-us"-grid en capabilities-grid op visuele variatie (spec sectie 7, punt 1) — voeg zo nodig een klein visueel verschil toe tussen kaarten (bijv. niet elke kaart exact identieke iconengrootte/uitlijning) als ze nu 100% identiek zijn.

- [ ] **Stap 6: Build en curl-verificatie**

```bash
npm run build
curl -s http://localhost:0 2>/dev/null; true  # placeholder-vrij: gebruik onderstaande echte check
grep -o "tessar-design-tokens.css" index.html | head -1
grep -o "F7F2E9" index.html | head -1
grep -o "Organization" index.html | head -1
```
Expected: alle drie geven een treffer.

- [ ] **Stap 7: Visuele controle + `npm test`**

Herhaal de Playwright-screenshot-aanpak uit eerdere sessie-taken (desktop 1440px + mobiel 390px, lokale server + `browser.newPage`/`page.screenshot`). Bekijk beide screenshots. Draai `npm test` — moet groen blijven.

- [ ] **Stap 8: Commit**

```bash
git add index.src.html index.html
git commit -m "feat: homepage naar het lichte oker/teal-thema met nieuwe hero-fotografie"
```

---

### Taak 12: `services.html` — tokens, hero, typografie

**Files:**
- Modify: `services.html`

**Interfaces:**
- Consumes: Taak 1, 2, 10.

- [ ] **Stap 1: Verwijder het inline `:root`-blok, voeg de link toe**

Het huidige blok (identiek aan alle andere niet-homepage-pagina's):
```css
:root {
  color-scheme: dark;
  --bg: oklch(14% 0.016 260);
  --surface: oklch(19% 0.016 260);
  --text: oklch(95% 0.006 90);
  --text-muted: oklch(72% 0.014 140);
  --text-muted-2: oklch(60% 0.014 140);
  --border: oklch(28% 0.014 260);
  --accent-text: oklch(66% 0.13 226);
  --surface-inset: oklch(25% 0.018 260);
}
```
volledig verwijderen, en in de `<head>` toevoegen:
```html
<link rel="stylesheet" href="./assets/tessar-design-tokens.css">
```

- [ ] **Stap 2: Herbouw de hero naar het Vapi-model**

De huidige hero (`<section style="...background:var(--bg);color:#FFF;...text-align:center;">` met H1 "Vijf diensten, één aanpak") is gecentreerde tekst zonder beeld. Herbouw naar: beeldvullende foto (Taak 10) met de tekst rechtstreeks erover en een scrim, zoals spec sectie 5. Verwijder `color:#FFF` van de sectie (de tekst kleurt nu via de scrim/foto-context, niet via een vaste witte kleur op een donkere paginakleur).

- [ ] **Stap 3: Outfit toepassen op de H1**

Vervang `'IBM Plex Sans'` door `'Outfit'` in de H1-inline-`font`-declaratie (zelfde patroon als Taak 5).

- [ ] **Stap 4: `theme-color` bijwerken, componentregels-auditen**

`<meta name="theme-color" content="#0a0a0f">` → `content="#F7F2E9"`. Scan op het liggend streepje en corrigeer:
```bash
grep -c "—" services.html
```
Expected na correctie: `0` in zichtbare copy (JSON-LD/comments negeren). Controleer de dienstenkaarten (5 diensten volgens de H1 "Vijf diensten, één aanpak") op visuele variatie t.o.v. elkaar (spec sectie 7 punt 1) en de eyebrow-ratio (max. 1 per 3 secties, punt 2).

- [ ] **Stap 5: Curl- en visuele verificatie, `npm test`, commit**

```bash
grep -o "tessar-design-tokens.css" services.html | head -1
grep -o "F7F2E9" services.html | head -1
npm test
git add services.html
git commit -m "feat: services.html naar het lichte oker/teal-thema met nieuwe hero-fotografie"
```

---

### Taak 13: `chatbots.html` — tokens, hero, typografie

**Files:**
- Modify: `chatbots.html`

- [ ] **Stap 1: Verwijder het inline `:root`-blok, voeg de link toe**

Het huidige blok (identiek aan alle andere niet-homepage-pagina's):
```css
:root {
  color-scheme: dark;
  --bg: oklch(14% 0.016 260);
  --surface: oklch(19% 0.016 260);
  --text: oklch(95% 0.006 90);
  --text-muted: oklch(72% 0.014 140);
  --text-muted-2: oklch(60% 0.014 140);
  --border: oklch(28% 0.014 260);
  --accent-text: oklch(66% 0.13 226);
  --surface-inset: oklch(25% 0.018 260);
}
```
volledig verwijderen, en in de `<head>` toevoegen:
```html
<link rel="stylesheet" href="./assets/tessar-design-tokens.css">
```

- [ ] **Stap 2: Herbouw de hero naar het Vapi-model**

De huidige hero (`<section id="hero" style="...background:var(--bg);color:#FFF;...text-align:center;">` met H1 "Een chatbot die past bij hoe jouw praktijk werkt") is gecentreerde tekst zonder beeld. Herbouw naar: beeldvullende foto (Taak 8, bestand `assets/chatbots-hero.webp`/`-sm.webp`) met de tekst rechtstreeks erover en een scrim, zoals spec sectie 5. Verwijder `color:#FFF` van de sectie.

- [ ] **Stap 3: Outfit toepassen op de H1**

Vervang `'IBM Plex Sans'` door `'Outfit'` in de H1-inline-`font`-declaratie ("Een chatbot die past bij hoe jouw praktijk werkt").

- [ ] **Stap 4: `theme-color` bijwerken, componentregels-audit**

`<meta name="theme-color" content="#0a0a0f">` → `content="#F7F2E9"`. Deze pagina heeft een `#demo`/`#tiers`/`#how`/`#faq`-structuur met meerdere secties — controleer specifiek de eyebrow-ratio (max. 1 "eyebrow"-label per 3 secties, spec sectie 7 punt 2) en scan op het liggend streepje:
```bash
grep -c "—" chatbots.html
```
Expected na correctie: `0` in zichtbare copy (JSON-LD/comments negeren).

- [ ] **Stap 5: Verificatie + `npm test` + commit**
```bash
grep -o "tessar-design-tokens.css" chatbots.html | head -1
grep -o "F7F2E9" chatbots.html | head -1
npm test
git add chatbots.html
git commit -m "feat: chatbots.html naar het lichte oker/teal-thema met nieuwe hero-fotografie"
```

---

### Taak 14: `ai-telefonist-voor-bedrijf.html` — tokens, nieuwe hero-foto, typografie

Artikel-pagina-patroon (smalle 700px-kolom, geen gecentreerde sectie) — vervangt de bestaande hoorn-sculptuurfoto (uit een eerdere sessie-taak) door de documentaire foto uit Taak 7, in dezelfde structuur (contained ~900px `<img>` tussen titelblok en lopende tekst, zoals al aanwezig).

**Files:**
- Modify: `ai-telefonist-voor-bedrijf.html`

- [ ] **Stap 1:** inline `:root`-blok verwijderen, `<link>` naar `tessar-design-tokens.css` toevoegen.
- [ ] **Stap 2:** de bestaande `<img src="./assets/blog/ai-telefonist-hero.webp" ...>` (artikel-hero) vervangen door de nieuwe bestanden uit Taak 7 (`ai-telefonist-hero-v2.webp`/`-sm.webp`).
- [ ] **Stap 3:** `og:image`/`twitter:image` blijven verwijzen naar `assets/blog/ai-telefonist-voor-bedrijf.png` (de kaart-thumbnail) — dat bestand wordt in Taak 19 (blog-kaarten-sweep) bijgewerkt naar een crop van dezelfde nieuwe foto, niet in deze taak.
- [ ] **Stap 4:** `'IBM Plex Sans'` → `'Outfit'` in de H1.
- [ ] **Stap 5:** `theme-color` bijwerken, componentregel-audit (em-dash-scan: `grep -c "—" ai-telefonist-voor-bedrijf.html`, handmatig beoordelen — dit artikel is lang, controleer de hele lopende tekst).
- [ ] **Stap 6:** curl-check + visuele controle + commit:
```bash
grep -o "tessar-design-tokens.css" ai-telefonist-voor-bedrijf.html | head -1
git add ai-telefonist-voor-bedrijf.html
git commit -m "feat: AI-telefonist-pagina naar het lichte thema met nieuwe documentaire hero-foto"
```

---

### Taak 15: `ai-receptioniste-voor-bedrijven.html` — tokens, nieuwe hero-foto, typografie

Zelfde artikel-patroon als Taak 14, maar deze pagina heeft **nu nog geen enkel in-pagina hero-beeld** (alleen een og:image met het generieke flat-icoon) — dit is dus een toevoeging, geen vervanging.

**Files:**
- Modify: `ai-receptioniste-voor-bedrijven.html`

- [ ] **Stap 1:** inline `:root`-blok verwijderen, `<link>` toevoegen.
- [ ] **Stap 2:** voeg, direct na het titelblok (dezelfde structuur als `ai-telefonist-voor-bedrijf.html`: `<section>` met `max-width:700px`-titel, gevolgd door de prose-`<section>`) een nieuwe `<section>` toe met de hero-foto uit Taak 7, exact naar het patroon dat al in `ai-telefonist-voor-bedrijf.html` staat:
```html
<section style="padding:0 clamp(20px,5vw,40px) clamp(32px,4vw,44px);background:var(--bg);">
  <div style="max-width:900px;margin:0 auto;">
    <img src="./assets/blog/ai-receptioniste-hero.webp" srcset="./assets/blog/ai-receptioniste-hero-sm.webp 800w, ./assets/blog/ai-receptioniste-hero.webp 1600w" sizes="(min-width: 900px) 900px, 100vw" width="1600" height="905" alt="" loading="eager" fetchpriority="high" style="display:block;width:100%;height:auto;border-radius:12px;">
  </div>
</section>
```
(Breedte/hoogte-attributen aanpassen aan de daadwerkelijke afmetingen van het door de controller aangeleverde bestand uit Taak 7.)
- [ ] **Stap 3:** `og:image`/`twitter:image` blijven ongewijzigd in deze taak (bijgewerkt in Taak 19).
- [ ] **Stap 4:** `'IBM Plex Sans'` → `'Outfit'` in de H1.
- [ ] **Stap 5:** `theme-color` bijwerken, componentregel-audit.
- [ ] **Stap 6:** curl-check + commit:
```bash
grep -o "tessar-design-tokens.css" ai-receptioniste-voor-bedrijven.html | head -1
grep -o "ai-receptioniste-hero" ai-receptioniste-voor-bedrijven.html | head -1
git add ai-receptioniste-voor-bedrijven.html
git commit -m "feat: AI-receptioniste-pagina naar het lichte thema met nieuwe hero-foto"
```

---

### Taak 16: `ai-chatbot-voor-bedrijven.html` — tokens, nieuwe hero-foto, typografie

Artikel-patroon, identieke structuur als `ai-telefonist-voor-bedrijf.html`. Deze pagina heeft nu nog geen in-pagina hero-beeld (alleen een og:image met het generieke flat-icoon) — dit is een toevoeging.

**Files:**
- Modify: `ai-chatbot-voor-bedrijven.html`

- [ ] **Stap 1: Verwijder het inline `:root`-blok, voeg de link toe**
```css
:root {
  color-scheme: dark;
  --bg: oklch(14% 0.016 260);
  --surface: oklch(19% 0.016 260);
  --text: oklch(95% 0.006 90);
  --text-muted: oklch(72% 0.014 140);
  --text-muted-2: oklch(60% 0.014 140);
  --border: oklch(28% 0.014 260);
  --accent-text: oklch(66% 0.13 226);
  --surface-inset: oklch(25% 0.018 260);
}
```
volledig verwijderen; in de `<head>` toevoegen:
```html
<link rel="stylesheet" href="./assets/tessar-design-tokens.css">
```

- [ ] **Stap 2: Voeg de hero-foto toe**

Direct na het titelblok (vóór de prose-`<section>`):
```html
<section style="padding:0 clamp(20px,5vw,40px) clamp(32px,4vw,44px);background:var(--bg);">
  <div style="max-width:900px;margin:0 auto;">
    <img src="./assets/blog/ai-chatbot-hero.webp" srcset="./assets/blog/ai-chatbot-hero-sm.webp 800w, ./assets/blog/ai-chatbot-hero.webp 1600w" sizes="(min-width: 900px) 900px, 100vw" width="1600" height="905" alt="" loading="eager" fetchpriority="high" style="display:block;width:100%;height:auto;border-radius:12px;">
  </div>
</section>
```
(Breedte/hoogte aanpassen aan de daadwerkelijke afmetingen van het door de controller aangeleverde bestand uit Taak 8.)

- [ ] **Stap 3:** `og:image`/`twitter:image` blijven ongewijzigd in deze taak (bijgewerkt in Taak 19).
- [ ] **Stap 4:** `'IBM Plex Sans'` → `'Outfit'` in de H1 ("AI Chatbot voor Bedrijven: Automatiseer Klantenservice in 5 Stappen").
- [ ] **Stap 5:** `theme-color` bijwerken (`content="#0a0a0f"` → `content="#F7F2E9"`), componentregel-audit (em-dash-scan, eyebrow-ratio).
- [ ] **Stap 6: Verificatie + commit**
```bash
grep -o "tessar-design-tokens.css" ai-chatbot-voor-bedrijven.html | head -1
grep -o "ai-chatbot-hero" ai-chatbot-voor-bedrijven.html | head -1
npm test
git add ai-chatbot-voor-bedrijven.html
git commit -m "feat: AI-chatbot-pagina naar het lichte thema met nieuwe hero-foto"
```

---

### Taak 17: `bedrijfsprocessen-automatiseren-met-ai.html` en `workflow-automatisering-met-ai.html` — tokens, nieuwe hero-foto's, typografie

Beide pagina's hebben identieke structuur aan `ai-telefonist-voor-bedrijf.html` en geen van beide heeft nu een in-pagina hero-beeld. Eén taak voor twee bestanden omdat het exact dezelfde wijziging is (zie "Batch small same-shape work").

**Files:**
- Modify: `bedrijfsprocessen-automatiseren-met-ai.html`
- Modify: `workflow-automatisering-met-ai.html`

- [ ] **Stap 1: Op beide bestanden: verwijder het inline `:root`-blok, voeg de link toe**
```css
:root {
  color-scheme: dark;
  --bg: oklch(14% 0.016 260);
  --surface: oklch(19% 0.016 260);
  --text: oklch(95% 0.006 90);
  --text-muted: oklch(72% 0.014 140);
  --text-muted-2: oklch(60% 0.014 140);
  --border: oklch(28% 0.014 260);
  --accent-text: oklch(66% 0.13 226);
  --surface-inset: oklch(25% 0.018 260);
}
```
volledig verwijderen op beide bestanden; in beide `<head>`s toevoegen:
```html
<link rel="stylesheet" href="./assets/tessar-design-tokens.css">
```

- [ ] **Stap 2: Voeg de hero-foto toe op `bedrijfsprocessen-automatiseren-met-ai.html`**
```html
<section style="padding:0 clamp(20px,5vw,40px) clamp(32px,4vw,44px);background:var(--bg);">
  <div style="max-width:900px;margin:0 auto;">
    <img src="./assets/blog/bedrijfsprocessen-hero.webp" srcset="./assets/blog/bedrijfsprocessen-hero-sm.webp 800w, ./assets/blog/bedrijfsprocessen-hero.webp 1600w" sizes="(min-width: 900px) 900px, 100vw" width="1600" height="905" alt="" loading="eager" fetchpriority="high" style="display:block;width:100%;height:auto;border-radius:12px;">
  </div>
</section>
```

- [ ] **Stap 3: Voeg de hero-foto toe op `workflow-automatisering-met-ai.html`**
```html
<section style="padding:0 clamp(20px,5vw,40px) clamp(32px,4vw,44px);background:var(--bg);">
  <div style="max-width:900px;margin:0 auto;">
    <img src="./assets/blog/workflow-hero.webp" srcset="./assets/blog/workflow-hero-sm.webp 800w, ./assets/blog/workflow-hero.webp 1600w" sizes="(min-width: 900px) 900px, 100vw" width="1600" height="905" alt="" loading="eager" fetchpriority="high" style="display:block;width:100%;height:auto;border-radius:12px;">
  </div>
</section>
```

- [ ] **Stap 4:** op beide: `og:image`/`twitter:image` blijven ongewijzigd (bijgewerkt in Taak 19); `'IBM Plex Sans'` → `'Outfit'` in de H1 ("Bedrijfsprocessen automatiseren met AI: praktische gids voor het mkb" resp. "Workflow Automatisering met AI: Hoe het Werkt en Waarom mkb's het Nodig Hebben"); `theme-color` → `content="#F7F2E9"`; componentregel-audit (em-dash-scan — de tweede H1 bevat een bezitsvorm-apostrof, geen liggend streepje, geen wijziging nodig daar).

- [ ] **Stap 5: Verificatie**
```bash
grep -o "tessar-design-tokens.css" bedrijfsprocessen-automatiseren-met-ai.html workflow-automatisering-met-ai.html
grep -o "bedrijfsprocessen-hero" bedrijfsprocessen-automatiseren-met-ai.html | head -1
grep -o "workflow-hero" workflow-automatisering-met-ai.html | head -1
npm test
```

- [ ] **Stap 6: Commit (één commit voor beide bestanden)**
```bash
git add bedrijfsprocessen-automatiseren-met-ai.html workflow-automatisering-met-ai.html
git commit -m "feat: bedrijfsprocessen- en workflow-automatisering-pagina's naar het lichte thema met nieuwe hero-foto's"
```

---

### Taak 18: `ai-implementatie-laten-uitvoeren.html`, `prijzen.html`, `contact.html`, `blog.html`, `privacy.html` — tokens en typografie (geen nieuw hero-beeld voor de laatste vier)

Vijf pagina's, verschillend qua hero-behoefte:
- `ai-implementatie-laten-uitvoeren.html`: artikel-patroon zoals Taak 15, met de hero-foto `ai-implementatie-hero.webp` uit Taak 9.
- `prijzen.html`, `blog.html`, `privacy.html`: geen hero, alleen tokens/font/audit (spec sectie 12: geen hero-behoefte).
- `contact.html`: geen hero, tokens/font/audit, plús formulier-toegankelijkheid (spec sectie 8).

- [ ] **Stap 1: `ai-implementatie-laten-uitvoeren.html`**

Verwijder het inline `:root`-blok:
```css
:root {
  color-scheme: dark;
  --bg: oklch(14% 0.016 260);
  --surface: oklch(19% 0.016 260);
  --text: oklch(95% 0.006 90);
  --text-muted: oklch(72% 0.014 140);
  --text-muted-2: oklch(60% 0.014 140);
  --border: oklch(28% 0.014 260);
  --accent-text: oklch(66% 0.13 226);
  --surface-inset: oklch(25% 0.018 260);
}
```
Voeg in de `<head>` toe: `<link rel="stylesheet" href="./assets/tessar-design-tokens.css">`.

Voeg direct na het titelblok (vóór de prose-`<section>`) de hero-foto toe:
```html
<section style="padding:0 clamp(20px,5vw,40px) clamp(32px,4vw,44px);background:var(--bg);">
  <div style="max-width:900px;margin:0 auto;">
    <img src="./assets/blog/ai-implementatie-hero.webp" srcset="./assets/blog/ai-implementatie-hero-sm.webp 800w, ./assets/blog/ai-implementatie-hero.webp 1600w" sizes="(min-width: 900px) 900px, 100vw" width="1600" height="905" alt="" loading="eager" fetchpriority="high" style="display:block;width:100%;height:auto;border-radius:12px;">
  </div>
</section>
```

`og:image`/`twitter:image` blijven in deze taak ongewijzigd (dit bestand — `assets/blog/ai-implementatie-laten-uitvoeren.png` — is niet opgenomen in Taak 19's blog-kaarten-sweep omdat het niet op `blog.html` als kaart verschijnt; controleer of dat klopt en werk het bestand hier zelf bij met dezelfde Pillow-crop-aanpak als Taak 19 stap 1 als het wél ergens als thumbnail gebruikt wordt).

Vervang `'IBM Plex Sans'` door `'Outfit'` in de H1 ("AI implementatie laten uitvoeren: Maatwerk automation voor jouw mkb"). Werk `theme-color` bij naar `content="#F7F2E9"`. Voer de componentregel-audit uit (em-dash-scan, eyebrow-ratio).

- [ ] **Stap 2: `prijzen.html`, `blog.html`, `privacy.html`** — voor elk: inline `:root`-blok verwijderen, `<link>` toevoegen, `theme-color` bijwerken, `'IBM Plex Sans'` → `'Outfit'` op de H1 (indien aanwezig — `blog.html`/`prijzen.html` hebben een H1, controleer `privacy.html` op eigen H1), componentregel-audit. Voor `prijzen.html` specifiek: verifieer dat de `data-mcp-tier`/`data-mcp-price`/`data-mcp-duration`-attributen op de 5 prijskaarten **ongewijzigd** blijven (deze voeden de `get_pricing()`-tool van de MCP-server):
```bash
grep -c "data-mcp-tier" prijzen.html
```
Expected: `5` (ongewijzigd t.o.v. vóór deze taak).

- [ ] **Stap 3: `contact.html` — formulier-toegankelijkheid (spec sectie 8)**

Naast tokens/font/audit: controleer dat elk van de vier zichtbare velden (`cf-name`, `cf-email`, `cf-phone`, `cf-message`) een gekoppeld `<label>` heeft (nu waarschijnlijk alleen `placeholder`, geen `<label>` — placeholders zijn geen vervanging voor labels, WCAG-eis). Voeg toe waar ontbrekend, bijv.:
```html
<label for="cf-name" style="font:500 0.875rem/1.4 'IBM Plex Sans';color:var(--text-muted);">Naam</label>
<input type="text" name="name" id="cf-name" required placeholder="Naam" class="contact-field"/>
```
(Herhalen voor `cf-email`, `cf-phone`, `cf-message` met hun eigen labeltekst.) Verifieer focus-states: `.contact-field:focus` moet een zichtbare rand/outline in `--accent` tonen — controleer of deze regel al bestaat in `contact.html`'s `<style>`-blok; zo niet, toevoegen:
```css
.contact-field:focus { outline: 2px solid var(--accent); outline-offset: 2px; border-color: var(--accent); }
```

- [ ] **Stap 4: Verificatie en commit (per bestand of gebundeld, naar keuze van de implementer — dit zijn onafhankelijke, gelijksoortige wijzigingen)**
```bash
grep -o "tessar-design-tokens.css" ai-implementatie-laten-uitvoeren.html prijzen.html blog.html privacy.html contact.html
grep -c "<label for=\"cf-" contact.html  # verwacht: 4
npm test
git add ai-implementatie-laten-uitvoeren.html prijzen.html blog.html privacy.html contact.html
git commit -m "feat: overige pagina's naar het lichte oker/teal-thema, contactformulier toegankelijker"
```

---

### Taak 19: Blog-kaart-thumbnails bijwerken naar de nieuwe hero-foto's

`blog.html` toont voor elk artikel een kaart met een thumbnail (`<img src="./assets/blog/<artikel>.png" ... style="...object-fit:cover;">` in een 600×160-box). Deze thumbnails zijn dezelfde bestanden als de `og:image`-meta-tags van de bijbehorende artikel-pagina's (zie sessie-precedent bij `ai-telefonist-voor-bedrijf.html`, waar dit al eenmalig is gedaan). Deze taak werkt de resterende vier bij: `ai-receptioniste-voor-bedrijven.png`, `ai-chatbot-voor-bedrijven.png`, `bedrijfsprocessen-automatiseren-met-ai.png`, `workflow-automatisering-met-ai.png`.

**Files:**
- Modify: `assets/blog/ai-receptioniste-voor-bedrijven.png`
- Modify: `assets/blog/ai-chatbot-voor-bedrijven.png`
- Modify: `assets/blog/bedrijfsprocessen-automatiseren-met-ai.png`
- Modify: `assets/blog/workflow-automatisering-met-ai.png`

**Interfaces:**
- Consumes: de hero-foto's uit Taak 7, 8, 9 (nog ongecropte, hoge-resolutie brondata van dezelfde generatie, niet de al-verkleinde webp's).

- [ ] **Stap 1: Genereer voor elk artikel een 600:160-crop (3.75:1) uit de bijbehorende brondata**, zelfde aanpak als eerder in de sessie bij `ai-telefonist-voor-bedrijf.png` (Pillow, crop gebiast naar het belangrijkste beeldelement, niet blind center-crop):
```python
from PIL import Image
img = Image.open("<pad naar de hoge-resolutie bron uit Taak 7/8/9>").convert("RGB")
w, h = img.size
target_ratio = 600 / 160
crop_h = round(w / target_ratio)
leftover = h - crop_h
top = round(leftover * 0.30)  # zelfde bias als eerder, aanpassen indien het onderwerp elders in het beeld staat
crop = img.crop((0, top, w, top + crop_h))
out = crop.resize((1200, round(1200 / target_ratio)), Image.LANCZOS)
out.save("assets/blog/<artikel>.png", "PNG", optimize=True)
```
Herhalen voor alle vier de artikelen, telkens de crop visueel controleren (Read-tool) vóór opslaan naar het definitieve pad.

- [ ] **Stap 2: Verifieer op de blog-overzichtspagina**

Herhaal de Playwright-screenshot-aanpak op `blog.html` (zoals eerder bij de AI-telefonist-kaart) en bekijk of alle vier de kaarten nu de nieuwe documentaire foto tonen i.p.v. het oude flat-icoon.

- [ ] **Stap 3: Commit**
```bash
git add assets/blog/ai-receptioniste-voor-bedrijven.png assets/blog/ai-chatbot-voor-bedrijven.png assets/blog/bedrijfsprocessen-automatiseren-met-ai.png assets/blog/workflow-automatisering-met-ai.png
git commit -m "feat: blog-kaart-thumbnails bijgewerkt naar de nieuwe documentaire hero-foto's"
```

---

### Taak 20: Motion & dynamiek — `[data-reveal]`-patroon sitebreed doorvoeren

Spec sectie 6: het bestaande scroll-fade-patroon (`[data-reveal]`/`[data-reveal-grid]`, nu alleen op de homepage) consistent toepassen op alle overige pagina's.

**Files:**
- Modify: alle 12 niet-homepage `.html`-bestanden (CSS-regels + `data-reveal`-attributen op content-blokken): `ai-telefonist-voor-bedrijf.html`, `ai-receptioniste-voor-bedrijven.html`, `ai-chatbot-voor-bedrijven.html`, `bedrijfsprocessen-automatiseren-met-ai.html`, `workflow-automatisering-met-ai.html`, `ai-implementatie-laten-uitvoeren.html`, `services.html`, `chatbots.html`, `prijzen.html`, `contact.html`, `blog.html`, `privacy.html`
- Modify: het `<script>`-blok van elk bestand dat de IntersectionObserver-logica bevat (kopiëren uit `index.src.html`'s bestaande implementatie — zoek de bestaande `[data-reveal]`-IntersectionObserver-code in `index.src.html`'s `<script>`-sectie en hergebruik die exacte logica op elke pagina, aangezien er geen gedeeld JS-bestand voor is)

- [ ] **Stap 1: Lokaliseer de bestaande implementatie**

Run: `grep -n "data-reveal" index.src.html | head -5` en `grep -n "IntersectionObserver" index.src.html`

Noteer de exacte CSS (`[data-reveal] { opacity:0; transform:translateY(18px); ... }`, al aanwezig in het `<style>`-blok van elke pagina, geverifieerd eerder) en de JS-observer-logica.

- [ ] **Stap 2: Voeg `data-reveal`/`data-reveal-grid`-attributen toe aan content-secties**

Voor elke niet-homepage-pagina: voeg `data-reveal` toe aan de belangrijkste content-blokken per sectie (feature-lijsten, kaarten, FAQ-items) — dezelfde granulariteit als de homepage al gebruikt (per kaart/item, niet per hele sectie).

- [ ] **Stap 3: Voeg de IntersectionObserver-JS toe (indien nog niet aanwezig op die pagina)**

Kopieer de exacte bestaande observer-code uit `index.src.html` naar het eigen `<script>`-blok van elke pagina (elke pagina heeft al een eigen `<script>` voor nav-toggle/back-to-top-logica — de observer-code voegt zich daarbij).

- [ ] **Stap 4: `prefers-reduced-motion`-check**

Verifieer dat de bestaande `@media (prefers-reduced-motion: reduce) { [data-reveal] { opacity:1; transform:none; transition:none; } ... }`-regel nog klopt (deze staat al op elke pagina, gecontroleerd bij eerdere sessie-taken — alleen bevestigen, niet opnieuw schrijven).

- [ ] **Stap 5: Visuele/functionele verificatie**

Scroll door 2-3 representatieve pagina's in de browser (Playwright, `page.evaluate` om te scrollen + screenshots vóór/na scroll) en bevestig dat content in beeld invalt.

- [ ] **Stap 6: `npm test` en commit**
```bash
npm test
git add ai-chatbot-voor-bedrijven.html ai-implementatie-laten-uitvoeren.html ai-receptioniste-voor-bedrijven.html ai-telefonist-voor-bedrijf.html bedrijfsprocessen-automatiseren-met-ai.html blog.html chatbots.html contact.html prijzen.html privacy.html services.html workflow-automatisering-met-ai.html
git commit -m "feat: scroll-fade-motion-patroon sitebreed doorgevoerd naar alle pagina's"
```

---

### Taak 21: Toegankelijkheids-contrastmatrix (eenmalig, sitebreed)

Spec sectie 8: contrastcontrole voor de volledige tokenset, één keer uitgevoerd zodra de tokens vastliggen (Taak 1 is klaar) — niet per pagina.

**Files:**
- Geen bestandswijziging tenzij er een contrastprobleem wordt gevonden (dan: `assets/tessar-design-tokens.css` aanpassen en de verificatiestap van Taak 1 opnieuw draaien).

- [ ] **Stap 1: Bereken de contrastratio's**

```python
def relative_luminance(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = (int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = lin(r), lin(g), lin(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(hex1, hex2):
    l1, l2 = relative_luminance(hex1), relative_luminance(hex2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

pairs = [
    ("#211C14", "#F7F2E9"), ("#211C14", "#F1EADA"), ("#211C14", "#EAE1CC"),
    ("#5F5646", "#F7F2E9"), ("#5F5646", "#F1EADA"),
    ("#8A8070", "#F7F2E9"),
    ("#0F5C57", "#F7F2E9"), ("#0F5C57", "#F1EADA"),
]
for fg, bg in pairs:
    print(fg, "op", bg, "->", round(contrast_ratio(fg, bg), 2))
```

- [ ] **Stap 2: Toets tegen WCAG AA**

Expected: alle combinaties ≥ 4.5 (lopende tekst) of ≥ 3.0 (grote tekst, 24px+/vet 18.66px+). Als `--text-muted-2` (`#8A8070`) op `--bg` (`#F7F2E9`) onder 4.5 uitkomt, mag die kleur alleen gebruikt worden voor grote tekst of moet hij worden verdonkerd — pas in dat geval de waarde in `assets/tessar-design-tokens.css` aan en herhaal de verificatie van Taak 1.

- [ ] **Stap 3: Documenteer het resultaat**

Voeg de uitkomst als commentaar toe bovenaan `assets/tessar-design-tokens.css`:
```css
/* Contrast geverifieerd (WCAG AA) op <datum>: alle tekst/achtergrond-combinaties
   uit dit bestand voldoen aan 4.5:1 (lopende tekst) resp. 3:1 (grote tekst). */
```

- [ ] **Stap 4: Commit (alleen als er iets is aangepast)**
```bash
git add assets/tessar-design-tokens.css
git commit -m "docs: contrastverificatie tokens gedocumenteerd" # of "fix: ... " als een waarde is aangepast
```

---

### Taak 22: Eind-consistentiecontrole

Spec sectie 14. Laatste taak, ná alle voorgaande.

**Files:** geen wijziging tenzij drift wordt gevonden.

- [ ] **Stap 1: Sitebrede grep-controle**

```bash
for f in index.html ai-*.html bedrijfsprocessen-automatiseren-met-ai.html workflow-automatisering-met-ai.html blog.html chatbots.html contact.html prijzen.html privacy.html services.html; do
  echo "=== $f ==="
  grep -c "tessar-design-tokens.css" "$f"
  grep -o 'theme-color" content="[^"]*"' "$f"
done
```
Expected: elke pagina toont `1` voor de link-check en `theme-color" content="#F7F2E9"`. Onderzoek en herstel elke afwijking.

- [ ] **Stap 2: Meta-description-uniciteit (spec sectie 10)**

```bash
for f in index.html ai-*.html bedrijfsprocessen-automatiseren-met-ai.html workflow-automatisering-met-ai.html blog.html chatbots.html contact.html prijzen.html privacy.html services.html; do
  grep -o 'name="description" content="[^"]*"' "$f"
done | sort | uniq -c | sort -rn
```
Expected: elke regel telt `1` (geen twee pagina's met identieke meta-description). Een telling ≥2 wijst op een duplicaat — herschrijf de beschrijving van de betrokken pagina('s) zodat hij uniek is en het hoofdonderwerp van díe pagina in de eerste 100 tekens noemt (bestaande, al-unieke beschrijvingen blijven ongewijzigd, spec sectie 10 is een aanvulling, geen verplichte herschrijving van wat al goed is).

- [ ] **Stap 3: Visuele langslangs**

Maak van alle 13 pagina's (12 + homepage) een desktop- (1440px) en mobiel- (390px) screenshot in één Playwright-run, en bekijk ze na elkaar (Read-tool) met de vraag "voelt dit als één site" — niet de inhoud opnieuw beoordelen.

- [ ] **Stap 4: `npm test` een laatste keer**

```bash
npm test
```
Expected: alle tests slagen.

- [ ] **Stap 5: Geen commit nodig tenzij stap 1 of 2 een fix vereiste** (dan een losse `fix:`-commit met de specifieke afwijking benoemd).
