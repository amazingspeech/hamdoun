# Tessar Premium Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vervang het huidige donkere, cyaan-blauwe kleursysteem van tessar.nl door het in de spec vastgelegde lichte oker/teal-systeem, over alle 13 pagina's (index.src.html/index.html als homepage meegerekend), zonder de SEO/curl-crawlbaarheid te verslechteren.

**Architecture:** Eén nieuw gedeeld tokenbestand (`assets/tessar-design-tokens.css`) vervangt de tot nu toe overal gedupliceerde inline `:root`-blokken. Elke pagina krijgt een `<link>` naar dat bestand plus zijn eigen, kleinere aanpassingen (hero-markup, koptekst-lettertype, component-audit). Gedeelde JS-widgets (cookie-banner, Tess-conciërge) en het merkicoon worden apart herkleurd, los van de pagina-tokens. **Herzien tijdens implementatie:** er komt geen nieuwe hero-fotografie in dit plan. De twee al bestaande, eerder gegenereerde beelden (homepage-fold-motief, AI-telefonist-hoorn) worden herkleurd/opnieuw ge-scrimd voor het lichte thema; alle andere hero-pagina's krijgen geen beeld (typografie/lay-out draagt de hero, spec sectie 4/5).

**Tech Stack:** Statische HTML/CSS, geen build-tooling behalve voor `index.src.html` (Playwright-prerender via `npm run build`). Python 3 + Pillow voor deterministische beeldbewerking (icoon-herkleuring, bestaande-beeld-scrim-aanpassing — geen AI-generatie in dit plan).

**Spec:** `docs/superpowers/specs/2026-09-03-tessar-premium-redesign-design.md`

## Global Constraints

- **SEO/curl-crawlbaarheid mag niet verslechteren.** Elke wijziging blijft zichtbaar in de statische, ongerenderde HTML (`curl`/`grep`-verifieerbaar, geen JS-afhankelijkheid). `index.src.html` gaat via `npm run build` vóór elke curl-check.
- **Geen Higgsfield-beeldgeneratie, door niemand — controller of implementer.** Een poging tijdens deze uitvoering liep vast: het eerste concept had geen enkele link met AI-automatisering, het tweede (bakker/bloemist) was op zichzelf klichévrij maar stond volledig los van Tessar's eigen merk-identiteit (een geometrische wireframe-kubus/tesseract). De gebruiker heeft besloten: geen nieuwe generaties meer tot hij daar zelf om vraagt. Dit plan gebruikt uitsluitend de twee al bestaande beelden (homepage-fold-motief, AI-telefonist-hoorn); geen enkele taak roept `higgsfield generate` aan.
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

## Fotografie: geannuleerd

De oorspronkelijke "Fotografie-strategie" (vijf gebundelde Higgsfield-shoots,
Taak 6-10 hieronder) is **vervallen** tijdens implementatie — zie Global
Constraints en spec sectie 4. Er komt geen nieuwe hero-fotografie in dit
plan. Taak 11 (homepage) en Taak 14 (AI-telefonist) hergebruiken hun
bestaande beelden; alle andere hero-pagina's (Taak 12, 13, 15, 16, 17, 18)
krijgen geen beeld. Taak 19 (blog-kaart-thumbnails bijwerken naar nieuwe
foto's) is om dezelfde reden vervallen.

## Verplichte extra stap: hardcoded kleur-literals migreren (ontdekt tijdens Taak 11)

**Dit raakt elke resterende paginataak (12-18), bovenop hun eigen `:root`-swap-stap.**

Taak 11 ontdekte dat `:root`-tokens vervangen door een `<link>` naar het
gedeelde bestand **niet voldoende is**: de codebase gebruikt op veel plekken
hardcoded `oklch(...)`-kleurwaarden direct in inline `style=""`-attributen
(oude cyaan/blauw-accent-hue 220/230/200, en lichte "tekst-op-bijna-zwart"
-tinten met hue 250) in plaats van `var(--accent-text)` etc. Die literals
veranderen niet mee met de tokenswap. Zonder deze stap: onleesbare tekst en
blijvend felblauwe knoppen op wat verder een crème/teal-pagina is geworden.

**Methodologie (dezelfde als Taak 11, per pagina toe te passen als
onderdeel van de componentregel-audit-stap):**

1. Zoek alle hardcoded `oklch(... 220 ...)`/`oklch(... 230 ...)`/
   `oklch(... 200 ...)` (oude accentkleur) en `color:#FFF`/vergelijkbare
   witte tekst-literals in de pagina.
2. Voor **zelfstandige UI-elementen** (knoppen, bolletjes/dots, randen —
   dingen die hun eigen interne contrast met hun eigen tekstkleur hebben,
   ongeacht de paginabodem): roteer de hue naar `188` (dezelfde hue als
   `--accent` `#0F5C57`), lichtheid/chroma **ongewijzigd**.
3. Voor kleuren die **als tekst/icoon direct op de nieuwe lichte
   `--bg`/`--surface` staan** (percentages, iconen, labels): roteer naar
   hue `188` én **verlaag de lichtheid naar ~42-45%** voor voldoende
   contrast — controleer met een WCAG-berekening (zie Taak 21's
   contrastformule) dat het resultaat ≥ 4.5:1 haalt tegen zijn achtergrond.
4. Voor lichte "tekst-op-donker"-literals (hue 250, lichtheid 70-98%) die
   nu op een lichte achtergrond staan: vervang door `var(--text-muted)` of
   `var(--accent-text)` in plaats van een nieuwe eigen hardcoded waarde.
5. `color:#FFF`/vergelijkbare witte-tekst-literals op secties die nu een
   lichte `--bg` hebben: verwijderen (tekst erft dan `var(--text)` via
   `body`) of expliciet naar `var(--text)` zetten.
6. **Niet aanraken**: secties die *bewust* donker blijven (als de pagina
   zoiets heeft, zoals de homepage's "why-us"-band en footer) — die hebben
   hun eigen, intern consistente donkere styling en vallen buiten deze
   migratie. Alleen aanpassen als de sectie zelf naar het lichte thema gaat.
7. Documenteer in het taakrapport welke literals gevonden en aangepast zijn
   (net als Taak 11 deed) — dit is geen stilzwijgende bijvangst, het is een
   expliciet te rapporteren onderdeel van de taak.

Dit is bewust **geen losse taak** maar een vaste toevoeging aan elke
resterende paginataak se componentregel-audit-stap: elke pagina heeft zijn
eigen literals, dus het hoort bij de taak die de pagina toch al aanraakt.

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

### Taken 6-10: vervallen (geen nieuwe fotografie)

Zie "Fotografie: geannuleerd" hierboven. Deze taaknummers zijn bewust niet
hergebruikt voor andere inhoud, zodat de ledger/geschiedenis van deze
uitvoering herleidbaar blijft.

---

### Taak 11: Homepage — tokens, bestaand hero-beeld herkleuren, typografie, SEO

**Files:**
- Modify: `index.src.html`
- Modify: `index.html` (via `npm run build`, niet handmatig)

**Interfaces:**
- Consumes: `assets/tessar-design-tokens.css` (Taak 1), herkleurd icoon (Taak 2), Outfit-patroon (Taak 5, al toegepast). Geen nieuwe hero-foto — het bestaande `assets/hero-visual.webp`/`hero-visual-sm.webp` (het "gevouwen metaal"-beeld) blijft staan.

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

- [ ] **Stap 2: Pas de bestaande hero-afbeelding aan het lichte thema aan (geen nieuw beeld)**

Het `.hero-visual`-`<img>` blijft `./assets/hero-visual.webp`/`hero-visual-sm.webp` (het gevouwen-metaal-beeld) — dit wordt niet vervangen. Wel aanpassen:
- De `.hero-visual::before`-warme-gloed en de `mask-image`-radiale-fade (toegevoegd om het beeld te laten "oplossen" in het oude, bijna-zwarte `--bg`) worden herijkt op de nieuwe lichte `--bg` (`#F7F2E9`): de fade/gloed moet overvloeien naar de crème-achtergrond, niet naar zwart.
- Beoordeel of de `.grad-text-warm`-brug (het amber-gekleurde tweede deel van de koptekst, eerder toegevoegd om het warme brons-beeld te verzoenen met het toen nog koele cyaan-accent) nog nodig is: met de nieuwe warme oker-basis plus teal-accent is de kleur-botsing die deze brug oploste er niet meer op dezelfde manier — het bronzen beeld past nu van nature beter bij een warme achtergrond. Vereenvoudig (bijv. laat beide koptekst-highlights de teal-accentkleur gebruiken) als de warme brug overbodig blijkt bij visuele controle; behoud hem als het beeld anders alsnog los blijft staan. Motiveer de keuze kort in het rapport.

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
git commit -m "feat: homepage naar het lichte oker/teal-thema"
```

---

### Taak 12: `services.html` — tokens, hero, typografie

**Files:**
- Modify: `services.html`

**Interfaces:**
- Consumes: Taak 1, 2. Geen hero-foto (vervallen, zie "Fotografie: geannuleerd") — deze pagina krijgt een tekst-gedreven hero.

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

- [ ] **Stap 2: Hertoon de bestaande tekst-hero voor het lichte thema (geen beeld)**

De huidige hero (`<section style="...background:var(--bg);color:#FFF;...text-align:center;">` met H1 "Vijf diensten, één aanpak") blijft gecentreerde tekst zonder beeld — geen Vapi-model hier, spec sectie 4/5 heeft dit vervangen door het Vercel/Linear-model (typografie draagt de hero). Concreet:
- Verwijder `color:#FFF` van de sectie (de tekst kleurt nu via de pagina-eigen `--text`-token, niet via een vaste witte kleur op wat een donkere achtergrond was).
- Laat de gecentreerde structuur en de bestaande `padding`-waarden ongemoeid — de Outfit-koptekst (stap 3 hieronder) plus de nieuwe lichte tokens geven de sectie al meer gewicht zonder een beeld nodig te hebben.

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
git commit -m "feat: services.html naar het lichte oker/teal-thema"
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

- [ ] **Stap 2: Hertoon de bestaande tekst-hero voor het lichte thema (geen beeld)**

De huidige hero (`<section id="hero" style="...background:var(--bg);color:#FFF;...text-align:center;">` met H1 "Een chatbot die past bij hoe jouw praktijk werkt") blijft gecentreerde tekst zonder beeld (Vercel/Linear-model, spec sectie 4/5 — geen nieuwe fotografie). Verwijder `color:#FFF` van de sectie; laat de gecentreerde structuur en padding ongemoeid.

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
git commit -m "feat: chatbots.html naar het lichte oker/teal-thema"
```

---

### Taak 14: `ai-telefonist-voor-bedrijf.html` — tokens, bestaand hero-beeld herkleuren, typografie

Artikel-pagina-patroon (smalle 700px-kolom, geen gecentreerde sectie). De bestaande hoorn-foto (contained ~900px `<img>` tussen titelblok en lopende tekst) **blijft staan** — geen nieuwe generatie (zie "Fotografie: geannuleerd"). Alleen kleursysteem/scrim eromheen wordt aangepast aan het lichte thema.

**Files:**
- Modify: `ai-telefonist-voor-bedrijf.html`

- [ ] **Stap 1:** inline `:root`-blok verwijderen, `<link>` naar `tessar-design-tokens.css` toevoegen.
- [ ] **Stap 2:** de bestaande `<img src="./assets/blog/ai-telefonist-hero.webp" ...>` blijft ongewijzigd staan (zelfde bestand, zelfde `srcset`) — geen vervanging. Controleer alleen of de `border-radius:12px`/geen-scrim-styling van dit contained beeld nog past bij de lichte paginakleur eromheen (bijv. of er genoeg contrast/afstand is tussen het beeld en de nu lichte `--bg`); pas alleen aan als het visueel nodig blijkt.
- [ ] **Stap 3:** `og:image`/`twitter:image` blijven ongewijzigd verwijzen naar `assets/blog/ai-telefonist-voor-bedrijf.png` (de kaart-thumbnail) — geen wijziging, Taak 19 is vervallen.
- [ ] **Stap 4:** `'IBM Plex Sans'` → `'Outfit'` in de H1.
- [ ] **Stap 5:** `theme-color` bijwerken, componentregel-audit (em-dash-scan: `grep -c "—" ai-telefonist-voor-bedrijf.html`, handmatig beoordelen — dit artikel is lang, controleer de hele lopende tekst).
- [ ] **Stap 6:** curl-check + visuele controle + commit:
```bash
grep -o "tessar-design-tokens.css" ai-telefonist-voor-bedrijf.html | head -1
git add ai-telefonist-voor-bedrijf.html
git commit -m "feat: AI-telefonist-pagina naar het lichte oker/teal-thema"
```

---

### Taak 15: `ai-receptioniste-voor-bedrijven.html` — tokens, typografie (geen hero-foto)

Zelfde artikel-patroon als Taak 14, maar deze pagina heeft geen bestaand bespoke beeld en krijgt er ook geen (zie "Fotografie: geannuleerd") — alleen kleursysteem, typografie en component-audit.

**Files:**
- Modify: `ai-receptioniste-voor-bedrijven.html`

- [ ] **Stap 1:** inline `:root`-blok verwijderen, `<link>` toevoegen.
- [ ] **Stap 2:** `og:image`/`twitter:image` blijven ongewijzigd (het huidige generieke flat-icoon) — geen nieuwe fotografie, dus geen wijziging hier.
- [ ] **Stap 3:** `'IBM Plex Sans'` → `'Outfit'` in de H1.
- [ ] **Stap 4:** `theme-color` bijwerken, componentregel-audit.
- [ ] **Stap 5:** curl-check + commit:
```bash
grep -o "tessar-design-tokens.css" ai-receptioniste-voor-bedrijven.html | head -1
npm test
git add ai-receptioniste-voor-bedrijven.html
git commit -m "feat: AI-receptioniste-pagina naar het lichte oker/teal-thema"
```

---

### Taak 16: `ai-chatbot-voor-bedrijven.html` — tokens, typografie (geen hero-foto)

Artikel-patroon, identieke structuur als `ai-telefonist-voor-bedrijf.html`. Geen bestand beeld, geen nieuwe fotografie (zie "Fotografie: geannuleerd") — alleen kleursysteem, typografie, component-audit.

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

- [ ] **Stap 2:** `og:image`/`twitter:image` blijven ongewijzigd (het huidige generieke flat-icoon).
- [ ] **Stap 3:** `'IBM Plex Sans'` → `'Outfit'` in de H1 ("AI Chatbot voor Bedrijven: Automatiseer Klantenservice in 5 Stappen").
- [ ] **Stap 4:** `theme-color` bijwerken (`content="#0a0a0f"` → `content="#F7F2E9"`), componentregel-audit (em-dash-scan, eyebrow-ratio).
- [ ] **Stap 5: Verificatie + commit**
```bash
grep -o "tessar-design-tokens.css" ai-chatbot-voor-bedrijven.html | head -1
npm test
git add ai-chatbot-voor-bedrijven.html
git commit -m "feat: AI-chatbot-pagina naar het lichte oker/teal-thema"
```

---

### Taak 17: `bedrijfsprocessen-automatiseren-met-ai.html` en `workflow-automatisering-met-ai.html` — tokens, typografie (geen hero-foto's)

Beide pagina's hebben identieke structuur aan `ai-telefonist-voor-bedrijf.html`, geen bestaand beeld, en krijgen er ook geen (zie "Fotografie: geannuleerd"). Eén taak voor twee bestanden omdat het exact dezelfde wijziging is (zie "Batch small same-shape work").

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

- [ ] **Stap 2:** op beide bestanden: `og:image`/`twitter:image` blijven ongewijzigd (de huidige generieke flat-iconen) — geen nieuwe fotografie.
- [ ] **Stap 3:** op beide: `'IBM Plex Sans'` → `'Outfit'` in de H1 ("Bedrijfsprocessen automatiseren met AI: praktische gids voor het mkb" resp. "Workflow Automatisering met AI: Hoe het Werkt en Waarom mkb's het Nodig Hebben"); `theme-color` → `content="#F7F2E9"`; componentregel-audit (em-dash-scan — de tweede H1 bevat een bezitsvorm-apostrof, geen liggend streepje, geen wijziging nodig daar).

- [ ] **Stap 4: Verificatie**
```bash
grep -o "tessar-design-tokens.css" bedrijfsprocessen-automatiseren-met-ai.html workflow-automatisering-met-ai.html
npm test
```

- [ ] **Stap 5: Commit (één commit voor beide bestanden)**
```bash
git add bedrijfsprocessen-automatiseren-met-ai.html workflow-automatisering-met-ai.html
git commit -m "feat: bedrijfsprocessen- en workflow-automatisering-pagina's naar het lichte oker/teal-thema"
```

---

### Taak 18: `ai-implementatie-laten-uitvoeren.html`, `prijzen.html`, `contact.html`, `blog.html`, `privacy.html` — tokens en typografie (geen van deze vijf krijgt een hero-foto)

Vijf pagina's, geen enkele krijgt nieuwe fotografie (zie "Fotografie: geannuleerd"):
- `ai-implementatie-laten-uitvoeren.html`: artikel-patroon zoals Taak 15, alleen tokens/font/audit.
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

`og:image`/`twitter:image` (`assets/blog/ai-implementatie-laten-uitvoeren.png`) blijven ongewijzigd — geen nieuwe fotografie.

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

### Taak 19: vervallen (geen nieuwe fotografie)

Deze taak (blog-kaart-thumbnails bijwerken naar nieuwe hero-foto's) verviel samen met Taak 6-10 — er zijn geen nieuwe foto's om de thumbnails van bij te werken. De vier flat-icoon-thumbnails blijven staan tot de gebruiker nieuwe fotografie laat maken.

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

---

### Taak 23: Homepage-hero — volledig beeldvullend met nieuw beeld (vervangt Taak 11's hero-layout)

**Nieuwe, na Taak 11 toegevoegde taak — directe instructie van de gebruiker.** Taak 11 leverde de homepage-hero op als een twee-koloms grid (tekst links, beeld rechts in een gemaskeerd/wegvloeiend kader — het "gevouwen metaal"-beeld met een radiale mask-fade). De gebruiker wil dit vervangen door een **volledig beeldvullende hero** ("fullscreen"), met de koptekst rechtstreeks over het beeld heen (zoals het Vapi-model uit spec sectie 4/5, nu ook toegepast op de homepage) — geen twee-koloms lay-out, geen gemaskeerd kader meer. Het beeld zelf is ook vervangen: een nieuw, door de gebruiker goedgekeurd Higgsfield-beeld met dezelfde "verkreukeld → precies geometrisch"-signatuurstijl, maar op een lichte, warme achtergrond (niet meer bijna-zwart) — bewust zo gegenereerd omdat het donkere beeld niet meer paste op de nu lichte site. Alle overige Taak 11-wijzigingen (tokens, SEO-JSON-LD, em-dash-cleanup, kleur-literal-migratie, kaart-variatie) blijven ongewijzigd — deze taak raakt alleen de hero-sectie se structuur en het beeld.

**Files:**
- Modify: `index.src.html`
- Modify: `index.html` (via `npm run build`, niet handmatig)
- De nieuwe beeldbestanden staan al klaar: `assets/hero-visual-full.webp` (2400px breed, desktop) en `assets/hero-visual-full-sm.webp` (960×1200, mobiel, portrait-crop met de linkerkant van het object — reeds gegenereerd/gecropt en gecommit door de controller). De oude `assets/hero-visual.webp`/`hero-visual-sm.webp` blijven op schijf staan (niet verwijderen — geen ruimte om na te gaan of iets anders ernaar verwijst) maar worden door de homepage niet langer gebruikt.

**Interfaces:**
- Consumes: `assets/hero-visual-full.webp`/`-sm.webp` (al aangeleverd), alle Taak 11-tokens/structuur (ongewijzigd).

- [ ] **Stap 1: Herbouw de heropbouw naar één laag-op-laag structuur (geen twee-koloms grid meer)**

Zoek de huidige `#top`-sectie met de `.hero-layout`/`.hero-text`/`.hero-visual`-structuur (uit Taak 11/eerdere sessie-taken). Vervang door:
- Eén relatief gepositioneerde `<section id="top">` (behoud de bestaande verticale padding-conventie van de site, bijv. `clamp(64px,8vw,88px)`, maar controleer of die nog past bij een volledig beeldvullende hero of dat de sectie een eigen, hogere `min-height` nodig heeft om echt "fullscreen" aan te voelen — gebruik je eigen visuele oordeel, iets in de orde van `min-height:clamp(560px,82vh,820px)` is een redelijk startpunt, gebaseerd op eerdere sessie-onderzoek naar hero-hoogtes; niet letterlijk 100vh, dat was eerder al te hoog gebleken).
- Een absoluut gepositioneerde achtergrond-`<img>` die de hele sectie vult:
```html
<img class="hero-full-bg" src="./assets/hero-visual-full.webp" srcset="./assets/hero-visual-full-sm.webp 960w, ./assets/hero-visual-full.webp 2400w" sizes="100vw" width="2400" height="1357" alt="" loading="eager" fetchpriority="high" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center center;z-index:0;">
```
(Breedte/hoogte-attributen kloppen al met de aangeleverde bestanden — controleer bij twijfel met een snelle Pillow-check.) Test `object-position` visueel op desktop en mobiel; het beeld se rustige zone zit rechts, dus `right center` kan op sommige breedtes beter werken dan `center center` — kies wat op de meeste viewport-breedtes het minst van het interessante deel van het beeld wegsnijdt.
- Een scrim-laag die de linkerkant (waar de tekst komt) laat overvloeien naar de paginakleur, zodat de tekst leesbaar blijft zonder een nieuwe, losse overlay-kleur te verzinnen:
```html
<div class="hero-full-scrim" style="position:absolute;inset:0;background:linear-gradient(90deg, var(--bg) 0%, var(--bg) 32%, transparent 68%);pointer-events:none;z-index:0;"></div>
```
- De bestaande tekst-inhoud (badge, H1, subtekst, CTA, trust-pills) blijft **inhoudelijk en structureel ongewijzigd** — verwijder alleen de omliggende `.hero-layout`/`.hero-text`-wrapper-divs en zet de content direct in de sectie met `position:relative;z-index:1;max-width` vergelijkbaar met de oude `.hero-text`-kolombreedte (zodat de tekst niet over de volle breedte van de nu bredere sectie uitrekt).
- Verwijder de nu overbodige CSS: `.hero-layout`, `.hero-visual` (incl. `::before`-gloed en `mask-image`, die specifiek voor het oude gemaskeerde-kader-beeld waren), en de bijbehorende media-query-regels. Nieuwe, kleinere CSS-regels voor `.hero-full-bg`/`.hero-full-scrim` mogen als losse classes (i.p.v. alles inline) als dat de sectie leesbaarder maakt — jouw keuze, zolang het patroon van de rest van het bestand (veel inline styling, een paar gedeelde classes voor herbruikte elementen) niet doorbroken wordt.

- [ ] **Stap 2: Mobiele/smalle-viewport-tuning**

Controleer via een Playwright-screenshot op 390px breedte of de scrim-verhouding (32%/68%) nog steeds voldoende leesbaarheid geeft — op een smalle viewport toont `object-fit:cover` een smaller deel van het beeld, dus de scrim-percentages moeten mogelijk breder (bijv. `var(--bg) 0%, var(--bg) 50%, transparent 85%`) om de tekst leesbaar te houden. Gebruik een `@media`-query op `.hero-full-scrim` als de desktop- en mobiele verhouding uiteen moeten lopen.

- [ ] **Stap 3: WCAG-contrastcontrole**

Controleer dat de koptekst/subtekst/badge op de scrim-overgang (het gebied waar het beeld nog gedeeltelijk doorschijnt) voldoende contrast houdt — als de tekst een vaste `max-width` heeft die ruim binnen de `var(--bg) 0%...32%`-zone blijft (waar de scrim vrijwel ondoorzichtig is), is dit vermoedelijk geen probleem, maar verifieer met een screenshot.

- [ ] **Stap 4: Build en verificatie**

```bash
npm run build
grep -o "hero-visual-full.webp" index.html | head -1
grep -o "hero-full-scrim" index.html | head -1
```
Expected: beide geven een treffer.

- [ ] **Stap 5: Visuele controle + `npm test`**

Playwright-screenshots desktop (1440px) en mobiel (390px), bekeken met de Read-tool: bevestig dat (a) het beeld nu volledig beeldvullend is, geen kader/doosje meer, (b) de koptekst goed leesbaar is over het beeld, (c) de rustige/lichte zone van het beeld (rechts) nog steeds zichtbaar is en niet volledig onder de scrim verdwijnt, (d) er geen layout-breuk is t.o.v. de rest van de pagina (de secties direct onder de hero moeten nog normaal aansluiten). Draai `npm test` — moet groen blijven.

- [ ] **Stap 6: Commit**

```bash
git add index.src.html index.html
git commit -m "feat: homepage-hero volledig beeldvullend met nieuw lichtgetint beeld"
```

---

### Taak 24: Homepage-hero — subtiele "levend"-animatie op het achtergrondbeeld (gratis, geen Higgsfield)

**Nieuwe taak, directe instructie van de gebruiker.** Na Taak 23 vroeg de gebruiker om de hero "levend" te maken. Gekozen aanpak (gratis, geen nieuwe Higgsfield-generatie): een subtiele, eenmalige zoom/settle-animatie op het achtergrondbeeld bij het laden van de pagina — geen doorlopende loop (dat oogt onrustig/goedkoop), maar één rustige overgang die samen met de bestaande `heroContentIn`-tekst-animatie (spec sectie 6, al aanwezig) de hero bij het laden laat "landen".

**Files:**
- Modify: `index.src.html`
- Modify: `index.html` (via `npm run build`)

**Interfaces:**
- Consumes: `.hero-full-bg`/`.hero-full-scrim` uit Taak 23 (ongewijzigde structuur, alleen een animatie toegevoegd aan `.hero-full-bg`).

- [ ] **Stap 1: Voeg de animatie toe aan `.hero-full-bg`**

```css
.hero-full-bg { animation: heroBgSettle 2.2s cubic-bezier(0.16,1,0.3,1) both; }
@keyframes heroBgSettle {
  0% { transform: scale(1.06); opacity: 0.92; }
  100% { transform: scale(1); opacity: 1; }
}
```
(Exacte duur/schaal mag je naar eigen smaak bijstellen na visuele controle — dit is een startpunt, geen exacte eis. Doel: subtiel, premium, geen goedkope "zoom-whoosh".)

- [ ] **Stap 2: `prefers-reduced-motion` respecteren**

Voeg `.hero-full-bg` toe aan de bestaande `@media (prefers-reduced-motion: reduce)`-regel (zoek de regel die nu al `.hero-content`/`.hero-scroll-cue` bevat) zodat de animatie wordt uitgeschakeld:
```css
.hero-full-bg { animation: none; }
```

- [ ] **Stap 3: Build en visuele controle**

```bash
npm run build
grep -o "heroBgSettle" index.html | head -1
```
Expected: treffer. Maak een Playwright-screenshot/video-achtige reeks stills vlak na page-load (bijv. 0ms, 500ms, 1000ms, 2500ms na `page.goto`) op desktop, en bekijk ze met de Read-tool om te bevestigen dat de overgang rustig en subtiel oogt, niet abrupt of storend. Test ook met `page.emulateMedia({ reducedMotion: 'reduce' })` dat de animatie dan wegvalt (beeld staat meteen op eindstand).

- [ ] **Stap 4: `npm test` en commit**

```bash
npm test
git add index.src.html index.html
git commit -m "feat: subtiele settle-animatie op de homepage-hero-achtergrond"
```
