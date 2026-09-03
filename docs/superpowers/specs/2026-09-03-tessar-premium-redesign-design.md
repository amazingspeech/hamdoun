# Tessar Premium Redesign — Design Spec

## Context

Tessar's marketing site (tessar.nl) reads as "flat, templated, obviously AI":
platte iconen-in-een-grid, geen fotografie, en een cyaan-blauw accent dat
statistisch het meest oververzadigde kleurenpatroon in tech-branding is. Twee
losse pogingen om dit te verbeteren binnen de bestaande donkere stijl (een
gegenereerd hero-beeld op de homepage, en op de AI-telefonist-pagina) lieten
zien dat losse ingrepen niet volstaan: een mooi beeld in een kader tegen een
niet-passend kleursysteem oogt als een los plakplaatje, niet als ontwerp.

Dit document specificeert een systematische, sitebrede herziening: kleursysteem,
typografie, beeldtaal en componentregels, gebaseerd op (a) concrete
premium-designregels uit Higgsfield's eigen `design-recipe.md`/
`design-taste-frontend.md` documentatie (zie eerdere sessie-research), (b)
directe inspectie van vijf huidige premium tech/AI-referenties (Linear, Vercel,
Anthropic, Ramp, Vapi — de laatste is de meest directe categorie-vergelijking:
een voice-AI-agent-platform), en (c) actueel kleuronderzoek naar
merkkleur-verzadiging in AI/tech-branding.

## Niet-onderhandelbare randvoorwaarden

- **SEO/crawlbaarheid mag niet verslechteren.** Elke pagina moet curl-
  verifieerbaar volledig gerenderde HTML blijven teruggeven, zonder JS. De
  bestaande Playwright-prerender-pipeline (`scripts/prerender-index.mjs`,
  `npm run build`) voor `index.src.html` blijft ongewijzigd van aanpak; alle
  overige pagina's zijn al pure statische HTML en blijven dat.
- **Zelf hosten op de bestaande Hetzner-server** blijft het uitgangspunt — geen
  overstap naar een extern gehost platform (dit was al eerder afgewogen en
  afgewezen voor zowel Lovable als Higgsfield's eigen website-builder-product).
- **Nederlands-only, één stijl van CTA-copy, AVG/EU-servers-taal** blijven
  ongewijzigde harde eisen.
- **Geen Higgsfield-beeldgeneratie meer, door niemand, tot de gebruiker er
  zelf om vraagt.** Aanvankelijk gold "toestemming per batch"; na een
  mislukte poging (zie sectie 4 — een op zich klichévrij concept dat
  volledig losstond van Tessar's eigen merk-identiteit) is dit aangescherpt
  tot een volledige pauze. Dit project gebruikt uitsluitend de twee al
  bestaande, eerder gegenereerde beelden (homepage, AI-telefonist-pagina).
  Geen enkele taak in dit plan mag een nieuwe Higgsfield-generatie starten.

## 1. Kleursysteem

Basis: warm, aards licht thema (oker/klei) met één diep, ongebruikelijk accent
(teal) — een combinatie die uit onderzoek naar voren kwam als tegelijk
vertrouwenwekkend, premium én menselijk, en die niet samenvalt met de drie
inmiddels oververzadigde AI-brancheclusters (blauw, paars, en het "zachte
warme AI-pastel" dat warme aardse paletten zelf al aan het worden zijn).

Exacte tokens (vervangen de huidige donkere `:root`-tokens 1-op-1 in elke
pagina — zie sectie 11 voor de technische aanpak):

```css
:root {
  color-scheme: light;
  --bg:            #F7F2E9;  /* warm oker/klei-wit, hoofdachtergrond */
  --surface:       #F1EADA;  /* iets dieper, voor kaarten/panelen */
  --surface-inset: #EAE1CC;  /* nog dieper, voor ingesloten vlakken (inputs, code) */
  --border:        #DCD0B8;  /* subtiele randen op de oker-basis */
  --text:          #211C14;  /* bijna-zwart, warme ondertoon */
  --text-muted:    #5F5646;  /* gedempte secundaire tekst */
  --text-muted-2:  #8A8070;  /* nog gedempter (bijv. datums, meta) */
  --accent:        #0F5C57;  /* diepe teal — het merk-accent */
  --accent-hover:  #0C4B47;  /* iets donkerder voor hover-states */
  --accent-text:   #0F5C57;  /* zelfde teal voor links/tekst-accenten */
  --accent-dim:    #E3EEEC;  /* zeer lichte teal-tint, voor badge-achtergronden */
  --ok-bg:         #EAF3E9;  /* succes-status, blijft functioneel gescheiden van het merk-accent */
  --ok-border:     #C3DCC0;
  --ok-text:       #2F6B2C;
  --danger-bg:     #FBEAE6;  /* fout-status, eveneens functioneel gescheiden */
  --danger-border: #E8C3B8;
  --danger-text:   #A23F24;
}
```

Regels:

- **Eén accentkleur** (teal) voor alle interactieve/merk-elementen (links,
  primaire knoppen, actieve nav-items, highlight-spans in koppen). Geen tweede
  concurrerende merkkleur.
- Succes-/fout-kleuren (`--ok-*`/`--danger-*`) blijven wat ze al waren:
  functionele statuskleuren, geen merk-accent — dit voorkomt dat het "before/
  after"-vergelijkingsblok op de homepage (rood/groen kaarten) per ongeluk het
  merk-accent kaapt.
- Geen gradients, geen glow/particle-effecten (bestaande harde eis, blijft
  overeind — dit is een kleursysteem-wissel, geen terugkeer naar de
  glow/gradient-stijl die eerder al bewust is verwijderd).
- `color-scheme: light` (was `dark`) zodat browser-UI (scrollbars,
  formuliervelden) meeschakelt.

## 2. Typografie

**IBM Plex Sans blijft voor lopende tekst, IBM Plex Mono blijft voor
labels/eyebrow-tekst.** Voor grote koppen (H1/H2, de plekken waar
typografie het meeste "premium"-gewicht draagt) komt **Outfit** erbij — een
geometrische, herkenbare display-sans die in Higgsfield's eigen
goedgekeurde-combinaties-lijst expliciet samen met IBM Plex Mono genoemd
wordt, dus geen kliché-keuze (Inter is wél verboden als default; Outfit
niet). Motivatie voor deze bijstelling: bij een volledige visuele
herziening (kleur, beeld, lay-out) is uniform IBM Plex-gebruik tot in de
grootste koppen een gemiste kans — typografie is een van de sterkste
premium-signalen, en één, bewust gekozen display-lettertype naast de
bestaande twee is een kleine, goed onderbouwde toevoeging, geen
fontwissel-project.

- H1/H2 → Outfit (nieuw, alleen voor koppen).
- Lopende tekst, knoppen, navigatie → IBM Plex Sans (ongewijzigd).
- Labels/eyebrow/mono-context → IBM Plex Mono (ongewijzigd).
- Groter, zelfverzekerder gebruik van de bestaande `clamp()`-schaal voor
  H1's — zoals al gedaan bij de homepage-hero-herziening.
- Body-tekst nooit onder 16px (bestaande regel, blijft — voorkomt ook de
  eerder gefixte Mobile-Safari-zoom-bug).
- Outfit wordt zelf-gehost of via Google Fonts geladen naast de bestaande
  IBM Plex-`<link>` (zelfde patroon, één regel extra per pagina).

## 3. Logo

Bestaande merktekens (`assets/logo-*.png`, `assets/logo-mark*.svg`,
`assets/tessar-icon*.png`) worden herkleurd van het huidige blauw naar de
nieuwe teal (`#0F5C57`). Vorm/silhouet blijft ongewijzigd — dit is een
kleurwijziging, geen redesign van het merkteken zelf. De "dark"-varianten
(`logo-*-dark.png`, bedoeld voor lichte achtergronden — de naming is
ietwat verwarrend t.o.v. het thema-migratie, maar verwijst naar het contrast
van het merkteken zelf) worden het uitgangspunt nu de site licht wordt; de
"light"-varianten (bedoeld voor donkere achtergronden) blijven bewaard voor
eventuele toekomstige donkere contexten (bijv. een voettekst-vlak in
`--surface-inset` als dat ooit donker zou worden — vooralsnog niet gepland).

## 4. Beeldtaal: bestaande beelden hergebruiken, geen nieuwe generatie

**Herzien tijdens implementatie, op expliciete instructie van de gebruiker.**
Een poging om voor de homepage nieuwe, documentair-ogende hero-fotografie te
laten genereren (Vapi-model: beeldvullende foto van een echt persoon in een
echte situatie) liep vast op twee mislukte concepten — waarvan de tweede
(een bakker/bloemist-scène) weliswaar los van eerdere fouten stond
(geen kliché, wel een AI-automatiserings-signaal verwerkt), maar **volledig
losstond van Tessar's eigen merk-identiteit**: de naam "Tessar" en het
merkicoon zijn een geometrische wireframe-kubus (tesseract-achtig) — een
willekeurige ambachtelijke-winkel-scène past daar niet bij, hoe goed
uitgevoerd ook. Dit werd terecht afgekeurd.

**Nieuwe, definitieve richtlijn voor dit project:**

- **Geen nieuwe Higgsfield-generaties meer**, door niemand — controller
  of implementer — totdat de gebruiker zelf expliciet om nieuwe fotografie
  vraagt. Dit vervangt de eerdere "toestemming per batch"-regel met een
  hardere: generatie is volledig gepauzeerd, geen batches meer voorstellen.
- **De twee al bestaande, eerder deze sessie gegenereerde beelden blijven
  gehandhaafd, niet vervangen:** het "gevouwen metaal"-motief (homepage) en
  de telefoonhoorn (AI-telefonist-pagina). Beide zijn geometrisch/sculptuur
  van aard — wat, met de tesseract-connectie nu expliciet erkend, párt bij
  het merk in plaats van ertegen inwerkt zoals eerder aangenomen. Ze worden
  in de uitrol (sectie 12) alleen qua **kleur/scrim aangepast** aan het
  nieuwe lichte thema (dezelfde soort fix als al eerder live toegepast op de
  homepage: radiale mask-fade + warme gloed i.p.v. een harde kader-rand),
  niet vervangen door iets nieuws.
- **Pagina's zonder bestaand bespoke beeld krijgen voorlopig geen hero-foto.**
  Dit raakt `services.html`, `chatbots.html`, `ai-receptioniste-voor-bedrijven.html`,
  `ai-chatbot-voor-bedrijven.html`, `bedrijfsprocessen-automatiseren-met-ai.html`,
  `workflow-automatisering-met-ai.html` en `ai-implementatie-laten-uitvoeren.html`.
  Deze pagina's krijgen wél het volledige kleursysteem, de Outfit-koptekst,
  de componentregel-audit en motion — alleen geen nieuw beeld. Dit volgt het
  Vercel/Linear-model uit het eerdere sitebrede onderzoek (dit was al een
  volwaardig onderbouwde premium-richting, geen noodgreep): typografisch
  zelfvertrouwen en lay-out dragen de pagina, geen beeld nodig. Hun huidige
  `og:image`-thumbnails (de generieke flat-iconen) blijven vooralsnog staan —
  ook dat wordt pas vervangen zodra er nieuwe fotografie is.
- Wanneer de gebruiker later alsnog nieuwe fotografie laat maken, geldt
  alsnog: documentair/foto-realistisch waar zinvol, beeldvullend zonder
  kader, en — nieuw geleerd — **eerst expliciet toetsen of het concept bij
  Tessar's eigen merk-identiteit past**, niet alleen of het op zichzelf goed
  en klichévrij is.

## 5. Hero-patroon

Dit patroon geldt alleen voor de twee pagina's met een bestaand bespoke beeld
(homepage, AI-telefonist — sectie 4). `services.html` en `chatbots.html`
hebben ook een gecentreerde hero-sectie, maar krijgen **geen beeld**: die
twee behouden een tekst-gedreven hero (groter/zelfverzekerder Outfit-koptekst,
geen beeldvullende foto, geen kader) — het Vercel/Linear-model uit het
sitebrede onderzoek, niet dit beeld-plus-scrim-patroon.

```
┌──────────────────────────────────────────────┐
│ [nav]                                         │
├──────────────────────────────────────────────┤
│  ███████████████████████████████████████████ │  <- beeldvullende foto,
│  ███████████████████████████████████████████ │     volledige breedte/hoogte
│  ███ Eyebrow-label                          ██│     van de hero-sectie.
│  ███ Koptekst, direct op de foto            ██│     Tekst-blok staat waar
│  ███ Subtekst                               ██│     de foto rustige,
│  ███ [CTA-knop]                             ██│     lege ruimte heeft
│  ███████████████████████████████████████████ │     (net als bij Vapi: dat
└──────────────────────────────────────────────┘     kan links, rechts,
                                                       boven of onder zijn)
```

- Max. 4 tekstelementen (eyebrow, kop, sub, CTA) — bestaande regel, blijft.
- Trust-pills (bestaande inhoud: EU AI Act-bewust, AVG-bewust, etc.) blijven
  gehandhaafd, buiten de foto, in een rustige strook direct onder de hero —
  géén verzonnen bewijs (client-logo's, cijfers, demo) toegevoegd; dat is
  expliciet **uitgesteld** (zie "Buiten scope").
- **Scrim-richting én -sterkte volgen de foto, niet een vast voorschrift.**
  Elke gegenereerde foto heeft zijn eigen rustige zone (zoals bij het
  fold-beeld: chaos links, rust rechts) — de tekst en de gradient-richting
  (`linear-gradient` naar boven, opzij, of een lokale radiale vignet)
  worden daarop afgestemd tijdens implementatie, met als enige harde eis:
  WCAG AA-contrast op de kop-tekst, ongeacht de gekozen richting.
- **Mobiele art-direction, vast patroon voor elke hero-foto**: net als bij de
  homepage-hero wordt elke foto in twee varianten geleverd — een brede
  desktop-crop en een eigen, apart gekozen mobiele crop (niet zomaar dezelfde
  foto verkleind) via `srcset`/`sizes`, `loading="eager" fetchpriority="high"`.
  Een implementer kiest de mobiele crop zo dat het belangrijkste beeldelement
  (gezicht, handeling) niet wegvalt in een smallere/kortere uitsnede — zoals
  concreet gedaan bij `hero-visual.webp`/`hero-visual-sm.webp` op de homepage.

## 6. Motion & dynamiek

Dit hele traject begon met de wens om van een statische, "obviously AI"-site
naar iets dynamisch te gaan (de 21st.dev-vergelijking uit een eerdere sessie).
Kleur en beeld lossen de statische *uitstraling* op; deze sectie gaat over
statische *beleving* — hoe de site aanvoelt tijdens het scrollen en
interacteren, niet alleen hoe een screenshot eruitziet.

Uitgangspunt: **één signatuur-motion-moment per pagina, plus consistente,
terughoudende micro-interacties overal** — niet overal losse effecten
toevoegen (dat oogt weer als een sjabloon vol widgetjes).

- **Bestaand `[data-reveal]`-scroll-fade-patroon** (al aanwezig op de
  homepage: elementen faden/schuiven in bij scrollen, met gestaffelde
  vertraging voor grids via `nth-child`) wordt **consistent doorgevoerd naar
  alle 14 pagina's**, niet alleen de homepage. Dit is de belangrijkste,
  laagste-risico hefboom voor "dynamisch aanvoelen" — puur CSS-transities op
  bestaande content, geen nieuwe library, geen SEO-risico (content staat al
  in de statische HTML, alleen de zichtbaarheids-transitie is client-side).
- **Eén signatuur-hero-moment per pagina**: een subtiele, doelgerichte
  intro-animatie op de hero zelf (bijv. de kop-tekst en foto die apart,
  licht gestaffeld, invallen bij het laden — vergelijkbaar met de bestaande
  `heroContentIn`-animatie op de homepage) — geen scroll-gestuurde
  video/canvas-effecten (te grote technische stap voor een statische
  multi-page site zonder build-pipeline op de meeste pagina's).
- **Micro-interacties consistent overal**: de bestaande knop-hover
  (`transform:translateY(-2px)` op `.hero-cta-primary`) en de sticky-header
  met blur-backdrop worden het sitebrede patroon voor alle knoppen/links,
  niet alleen in de hero.
- **`prefers-reduced-motion: reduce` blijft overal gerespecteerd** (bestaande
  harde eis) — elke nieuwe animatie krijgt een reduced-motion-uitschakeling,
  zoals nu al het geval is voor `.hero-content`/`.hero-scroll-cue`.
- **Uitdrukkelijk NIET**: autoplay-achtergrondvideo's zonder functie,
  decoratieve deeltjes-/canvas-effecten (bestaande harde eis tegen
  gradients/glow/particles blijft onverkort gelden — motion is geen
  achterdeur om die eis alsnog te omzeilen), aangepaste cursors.
- Wanneer het bewijs-element (sectie 13, uitgesteld) later wordt toegevoegd en
  echte cijfers bevat, is een langzaam optellende teller bij het in beeld
  scrollen een voor de hand liggende, doelgerichte toevoeging — niet nu
  bouwen, wel alvast genoteerd zodat het niet als losse toevoeging aanvoelt
  wanneer het zover is.

## 7. Sitebrede componentregels

Mechanisch controleerbare regels, toe te passen op elke pagina tijdens
implementatie (uit Higgsfield's eigen audit-checklist, zie eerdere
sessie-research):

1. Geen drie identieke feature-kaarten naast elkaar waar dat nu wel zo is
   (bijv. de "why-us"-grid en de capabilities-grid op de homepage) — minimaal
   visuele variatie tussen kaarten, of een ander lay-outpatroon.
2. Max. 1 "eyebrow"-label (uppercase, kleine kader-tekst boven een kop) per 3
   secties op een pagina.
3. Elk lay-outpatroon (bijv. "twee-koloms tekst+beeld") komt max. 1x per
   pagina voor.
4. Exact één CTA-label sitewide (bestaande eis, blijft: "Plan gratis
   kennismaking").
5. **Copy-audit per pagina**, mechanisch controleerbaar (uit Higgsfield's
   eigen AI-tell-checklist, breder dan alleen het liggend streepje):
   - Het gedachtestreepje "—" (em-dash) is **volledig verboden** in
     zichtbare copy — vervangen door een punt, komma, of "en"/"maar" al
     naar gelang de zin.
   - Geen vulwoorden/overdrijvingen zoals "naadloos", "ontketen",
     "baanbrekend", "revolutionair" — concreet benoemen wat iets doet, niet
     hypen.
   - Geen verzonnen statistieken ("92% sneller", "4x ROI") zonder bron —
     bestaande, onderbouwde claims (bijv. "24/7 bereikbaar", "EU-servers")
     mogen blijven staan, nieuwe cijfers alleen als ze kloppen.
   - Geen generieke "trusted by"-achtige zinnen zonder onderbouwing.
   - Elke pagina krijgt precies één duidelijke H1 met het hoofdonderwerp
     van de pagina; geen tekstniveaus overslaan (H1 direct naar H3 zonder
     H2 ertussen).

## 8. Toegankelijkheid

Het volledige kleurenpalet (sectie 1) is nieuw en moet expliciet op
toegankelijkheid gecontroleerd worden, niet alleen de hero:

- **Contrastcontrole (WCAG AA, 4.5:1 voor lopende tekst, 3:1 voor grote
  tekst)** voor elke tekst/achtergrond-combinatie die de tokens opleveren:
  `--text`/`--text-muted`/`--text-muted-2` op `--bg`/`--surface`/
  `--surface-inset`, en `--accent`/`--accent-text` op diezelfde
  achtergronden. Dit is één keer te verifiëren zodra de tokens vastliggen
  (vóór de uitrol naar 14 pagina's), niet per pagina opnieuw.
- **Focus-states**: elk interactief element (links, knoppen, formuliervelden)
  houdt een zichtbare focus-ring in de nieuwe accentkleur — geen
  `outline:none` zonder vervanging.
- **`contact.html`-formuliervelden**: labels, foutmeldingen en
  focus/hover-states krijgen expliciet de nieuwe tokens; dit raakt meer
  toestanden dan de generieke kleursysteem-vervanging in sectie 11 dekt
  (een leeg/ongeldig veld heeft een eigen kleur, niet alleen de tekens
  `--text`/`--border`).
- Bestaande alt-tekst-conventie (decoratieve beelden `alt=""`, functionele
  beelden een beschrijving) blijft gehandhaafd voor alle nieuwe hero-foto's.

## 9. Gedeelde, sitebrede elementen

Deze verschijnen op (bijna) elke pagina via gedeelde JS-bestanden of
per-pagina `<head>`-tags, en staan los van de losse `.html`-bestanden in de
pagina-inventaris (sectie 12) — ze zouden anders gemist worden:

- **Cookie-consent-banner** (`assets/tessar-prefs.js`) — rendert nu in het
  oude donkere kleurenschema. Moet meeverhuizen naar de nieuwe tokens.
- **Tess-conciërge-widget** (`tessar-concierge-widget.js`) — de chatbubbel en
  het gespreksvenster gebruiken nu het oude cyaan-blauw. Idem.
- **`<meta name="theme-color" content="#0a0a0f">`** — dit staat hardcoded in
  de `<head>` van elke pagina (geen CSS-token, dus niet automatisch
  meeveranderd door sectie 1). Wordt `content="#F7F2E9"` (of de exacte
  `--bg`-waarde) op elke pagina.
- **Favicon** (`assets/favicon-*.png`, `apple-touch-icon.png`) — huidig
  favicon is het blauwe merkteken; wordt herkleurd samen met het logo
  (sectie 3), zodat het browsertabblad niet het oude blauw blijft tonen
  terwijl de site zelf al teal is.

## 10. SEO-verrijking (niet alleen "niet verslechteren")

De niet-onderhandelbare eis in dit document is defensief: SEO mag niet
achteruitgaan. Een sitebrede herziening is ook een logisch moment om het
actief te verbeteren, gebaseerd op eerder deze sessie onderzochte
Higgsfield-SEO-regels:

- **JSON-LD structured data** waar nog niet aanwezig: `Organization` +
  `ProfessionalService` + `WebSite` op de homepage (al deels aanwezig op
  sommige artikel-pagina's, bijv. `Article`/`FAQPage` op
  `ai-telefonist-voor-bedrijf.html` — dat patroon wordt het sitebrede
  minimum).
- **Meta-descriptions**: elke pagina behoudt of krijgt een unieke,
  150-160-tekens beschrijving met het hoofdonderwerp in de eerste 100
  tekens — geen duplicaten tussen pagina's.
- Dit is een **toevoeging**, geen vervanging van de bestaande
  SEO-terminologie-afstemming (eerdere sessie) — waar structured data al
  aanwezig is, wordt die gecontroleerd tegen de nieuwe content, niet
  opnieuw opgebouwd.

## 11. Technische aanpak: één gedeeld tokenbestand

De site heeft nu **geen gedeeld CSS-bestand voor kleurtokens** — elke pagina
definieert zijn eigen `:root { ... }`-blok inline (geverifieerd: 8+ pagina's
gecheckt). `assets/tessar-tokens.css` bestaat wel, maar wordt door geen
enkele pagina gelinkt — dat bestand hoort bij een andere tool, niet bij deze
marketingsite, en blijft ongemoeid (geen naam-hergebruik, ter voorkoming van
verwarring).

**Gekozen aanpak: één nieuw bestand, `assets/tessar-design-tokens.css`**, met
daarin exact het `:root`-blok uit sectie 1. Elke pagina (14 stuks + homepage)
krijgt in de `<head>` één regel toegevoegd: `<link rel="stylesheet"
href="./assets/tessar-design-tokens.css">`, vóór de bestaande pagina-eigen
`<style>`-blokken. De pagina-eigen `<style>`-blokken zelf (component-CSS als
`.hero-badge`, `.hero-cta-primary`, animaties, etc.) **blijven inline**, per
pagina — alleen de kleurtokens verhuizen. Dit is bewust een kleinere
ingreep dan de hele stylesheet-architectuur consolideren (zie "Buiten
scope").

Overwegingen die tot deze omslag leidden (eerdere aanname was: bij het
bestaande per-pagina-patroon blijven):

| | Losse `:root` per pagina | Eén gedeeld bestand |
|---|---|---|
| Drift-risico | Reëel, en inconsistent met sectie 14's eigen doel — een handmatige eind-controle compenseert een probleem dat structureel te voorkomen was | Structureel onmogelijk: één bron |
| Consistentie met bestaand patroon | Schijnbaar wel, maar de site laadt al gedeelde externe bestanden (`tessar-concierge-widget.js`, `tessar-prefs.js`) op elke pagina — een gedeeld CSS-bestand is dezelfde categorie, geen nieuw patroon | Zelfde patroon als de bestaande gedeelde JS-bestanden |
| Nieuw faalpunt | Klein voordeel, maar overdreven: een 404 op dit bestand is dezelfde faalklasse als een 404 op een van de bestaande gedeelde JS-bestanden nu al zou zijn; bestaande deploy-verificatie (curl-check na elke deploy) vangt dit | Zelfde, al geaccepteerde risicoklasse |
| Performance | 14× dezelfde tokens inline: meer bytes, opnieuw geparsed per paginabezoek | Eén klein bestand (~1-2KB), zelfde origin (geen extra DNS/TLS zoals bij Google Fonts wél het geval is), na het eerste bezoek uit cache |
| Onderhoud | Een toekomstige kleuraanpassing = 14 bestanden bewerken | Een toekomstige kleuraanpassing = 1 bestand |

De enige echte reden om het wél per pagina te doen (geen nieuwe
laad-afhankelijkheid) weegt niet op tegen dat de site die afhankelijkheids-
categorie (gedeelde externe bestanden) al kent en er al deploy-verificatie
voor bestaat. Vandaar het gedeelde bestand.

## 12. Pagina-inventaris en uitrol

Alle pagina's krijgen minimaal het nieuwe kleursysteem (sectie 1) en een scan
op de componentregels (sectie 7). De twee pagina's met een bestaand bespoke
beeld krijgen dat beeld herkleurd/opnieuw ge-scrimd voor het lichte thema
(sectie 4/5) — geen nieuwe generatie. De overige hero-pagina's krijgen géén
beeld (sectie 4), enkel kleursysteem/typografie/motion. De gedeelde elementen
uit sectie 9 worden **één keer** aangepast en gelden daarna voor alle
pagina's die ze insluiten.

| Pagina | Kleursysteem | Hero-beeld | Opmerking |
|---|---|---|---|
| `index.src.html` (homepage) | ✅ | bestaand fold-beeld, herkleurd/scrim aangepast | dc-runtime, via `npm run build` |
| `ai-telefonist-voor-bedrijf.html` | ✅ | bestaande hoorn-sculptuur, herkleurd/scrim aangepast | |
| `ai-receptioniste-voor-bedrijven.html` | ✅ | geen (nog geen bespoke beeld, geen nieuwe generatie) | og:image blijft het huidige flat-icoon |
| `ai-chatbot-voor-bedrijven.html` | ✅ | geen | og:image blijft het huidige flat-icoon |
| `bedrijfsprocessen-automatiseren-met-ai.html` | ✅ | geen | og:image blijft het huidige flat-icoon |
| `workflow-automatisering-met-ai.html` | ✅ | geen | og:image blijft het huidige flat-icoon |
| `ai-implementatie-laten-uitvoeren.html` | ✅ | geen | og:image blijft het huidige flat-icoon |
| `services.html` | ✅ | geen — typografie/lay-out draagt de hero (Vercel/Linear-model) | heeft wel een gecentreerde hero-sectie, alleen zonder beeld |
| `chatbots.html` | ✅ | geen — idem | heeft wel een gecentreerde hero-sectie, alleen zonder beeld |
| `prijzen.html` | ✅ | nee (prijstabel, geen hero-behoefte) | `data-mcp-*`-attributen (MCP-server) blijven ongewijzigd |
| `contact.html` | ✅ | nee | formulier-functionaliteit blijft ongewijzigd; zie sectie 8 voor extra veld-states |
| `blog.html` | ✅ | nee (overzichtspagina, kaarten blijven) | kaart-thumbnails blijven ongewijzigd (geen nieuwe artikel-beelden) |
| `privacy.html` | ✅ | nee | puur tekst, geen hero |
| `googleb2c866753bf6b639.html` | — | — | Google-verificatiebestand, geen echte pagina, buiten scope |
| Cookie-banner + Tess-widget (sectie 9) | ✅ | n.v.t. | gedeeld, één keer aan te passen |
| `theme-color` + favicon (sectie 9) | ✅ | n.v.t. | per pagina een simpele attribuut-wijziging |

## 13. Buiten scope (bewust, apart te bespreken)

- **Bewijs-element in de hero** (klantlogo's, cijfers, interactieve demo) —
  gebruiker wil dit later apart beoordelen, mogelijk met echte klantnamen.
  Voor nu blijven de bestaande trust-pills staan.
- **Verdergaande fontwissel** buiten de in sectie 2 vastgelegde toevoeging
  (Outfit voor koppen) — lopende tekst blijft IBM Plex Sans, geen bredere
  font-herziening.
- **Verdere CSS-consolidatie voorbij kleurtokens** — sectie 11 verplaatst
  alléén de `:root`-tokens naar een gedeeld bestand. De overige, per pagina
  al bestaande component-CSS (`.hero-badge`, `.hero-cta-primary`, animaties,
  etc.) blijft inline per pagina; die volledig consolideren tot een
  gedeelde stylesheet is een grotere, aparte afweging.
- **Nieuwe hero-fotografie voor de pagina's zonder bestaand beeld** — bewust
  uitgesteld tot de gebruiker er zelf om vraagt (zie sectie 4). Tot die tijd
  dragen typografie en lay-out die pagina's.

## 14. Eind-consistentiecontrole

Met 14 pagina's, waarschijnlijk verdeeld over meerdere implementatietaken
(zie de aankomende writing-plans/subagent-driven-development-fase), blijft
er ondanks het gedeelde tokenbestand (sectie 11) nog drift mogelijk buiten
de kleurtokens om: een vergeten `theme-color`-attribuut, een pagina die de
scrim-richting anders opbouwt dan de rest, een `<link>` naar het tokenbestand
die per ongeluk ontbreekt. Daarom, als laatste stap vóór afronding (niet per
pagina, maar over de hele site heen):

- Eén controle-taak die op **alle** pagina's grept naar de aanwezigheid van
  de `<link>` naar `tessar-design-tokens.css`, naar de exacte
  `theme-color`-waarde, en naar het exacte CTA-label. (De kleurtokens zelf
  hoeven niet meer per pagina gecontroleerd te worden — die staan nu maar op
  één plek.)
- Eén visuele langslangs (screenshots van elke pagina, desktop + mobiel)
  door één reviewer, specifiek op "voelt dit als één site" — niet opnieuw
  elke pagina inhoudelijk beoordelen (dat gebeurde al per taak), alleen op
  visuele samenhang.

## 15. Testen/verificatie

- Per pagina: `curl`/grep-controle dat de nieuwe kleurwaarden en (waar van
  toepassing) het nieuwe hero-beeld in de **statische, ongerenderde** HTML
  staan (geen JS-afhankelijkheid) — voor `index.src.html` via `npm run build`
  gevolgd door dezelfde controle op `index.html`.
- Visuele controle desktop (1440px) + mobiel (390px) per pagina via
  Playwright-screenshots, vergelijkbaar met de aanpak bij de eerdere
  homepage- en AI-telefonist-wijzigingen.
- `npm test` (bestaande widget-unit/e2e-tests) moet groen blijven na elke
  taak — deze tests raken geen kleurwaarden, maar bewaken dat er geen
  functionele regressie optreedt.
- Contrast-check (WCAG AA) op elke hero-koptekst tegen zijn scrim/foto, plus
  de sitebrede contrast-matrix uit sectie 8.
