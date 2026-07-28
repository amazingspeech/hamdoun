# Tessar Design System — specificatie

**Status:** gereconstrueerd op 2026-07-28 (het origineel uit de vooronderzoeksessie
van 2026-07-27 raakte niet bijgevoegd; deze versie is opnieuw opgebouwd uit
dezelfde bronnen: de live site `hamdoun/index.html` en de bewezen
tokenstructuur van Certo, `protocolchecker/public/style.css`).

**Geldt voor:** de generieke, herverkoopbare Tessar-producten — Protocolchecker
(generieke template) en Boekingsassistent — plus alle Tessar-marketinguitingen.
**Geldt niet voor:** de live Certo/Van Dijk Clinic-instance (behoudt de eigen
crème/karamel-huisstijl) en losse n8n-automatiseringen.

**Bronbestand:** `assets/tessar-tokens.css` in deze repo is de canonieke
tokenlaag. Productrepo's nemen daar een kopie van op (met bronverwijzing in de
header) zodat elke deployment zelfstandig offline werkt; wijzigingen gebeuren
éérst hier en worden dan doorgekopieerd.

---

## 1. Kleur

Alle kleuren in `oklch()` — dezelfde notatie als de live site, zodat waarden
één-op-één overeenkomen met wat in productie staat. De waarden hieronder zijn
letterlijk uit `hamdoun/index.html` overgenomen (niet opnieuw verzonnen).

### 1.1 Licht thema (standaard)

| Token | Waarde | Herkomst / gebruik |
|---|---|---|
| `--bg` | `oklch(100% 0 0)` | kaart-/content-achtergrond (site: witte kaarten) |
| `--panel` | `oklch(98% 0.004 90)` | pagina-achtergrond, zijbalken (site: paginabasis) |
| `--border` | `oklch(91% 0.006 90)` | randen, scheidingslijnen (site: kaartranden) |
| `--text` | `oklch(18% 0.02 255)` | lopende tekst, koppen (site: bodytekst-inkt) |
| `--text-dim` | `oklch(46% 0.012 140)` | secundaire tekst (site: gedempte alinea's) |
| `--accent` | `oklch(48% 0.12 230)` | links, labels, actieve states (site: sectielabels, link-hover) |
| `--accent-hover` | `oklch(42% 0.12 230)` | hover op accent — één stap donkerder, zelfde tint |
| `--accent-dim` | `oklch(96% 0.01 230)` | zachte accentvulling (site: flow-node-achtergrond) |

### 1.2 Semantische kleuren (licht)

Rechtstreeks uit de voor/na-sectie van de live site:

| Token | Waarde |
|---|---|
| `--ok-bg` | `oklch(98% 0.02 165)` |
| `--ok-border` | `oklch(85% 0.05 165)` |
| `--ok-text` | `oklch(45% 0.14 165)` |
| `--danger-bg` | `oklch(98% 0.01 25)` |
| `--danger-border` | `oklch(88% 0.03 30)` |
| `--danger-text` | `oklch(52% 0.15 30)` |

### 1.3 Donker thema — navy als basis

Uitgangspunt: het donkere thema is géén simpele inversie van het lichte
ontwerp, maar gebruikt het navy van de hero/footersecties van de live site als
eigen basis (`theme-color #0a0a0f`, hero-navy `oklch(12% 0.03 260)`).

| Token | Waarde | Herkomst / gebruik |
|---|---|---|
| `--bg` | `oklch(14% 0.025 260)` | basis, tussen site-navy 12% en leesbaar app-niveau |
| `--panel` | `oklch(18% 0.025 258)` | panelen, één stap lichter dan de basis |
| `--border` | `oklch(30% 0.02 250)` | site: donkere sectieranden |
| `--text` | `oklch(95% 0.01 250)` | koppen/tekst op navy |
| `--text-dim` | `oklch(65% 0.02 250)` | site: gedempte tekst op donkere secties |
| `--accent` | `oklch(70% 0.14 220)` | site: hét heldere blauw op donkere secties |
| `--accent-hover` | `oklch(76% 0.13 215)` | hover — lichter op donker |
| `--accent-dim` | `oklch(25% 0.045 235)` | zachte accentvulling op navy (solide, geen alpha) |
| `--ok-bg / -border / -text` | `oklch(22% 0.04 165)` / `oklch(40% 0.07 165)` / `oklch(75% 0.12 160)` | badge-groen op donker komt van de site |
| `--danger-bg / -border / -text` | `oklch(24% 0.04 30)` / `oklch(46% 0.08 30)` / `oklch(78% 0.10 30)` | zelfde logica als ok-reeks |

### 1.4 Het Tessar-gradient

Het bestaande, in productie staande gradient van de primaire CTA:

```css
--gradient-primary: linear-gradient(135deg, oklch(72% 0.15 210), oklch(62% 0.14 235));
--gradient-primary-hover: linear-gradient(135deg, oklch(68% 0.15 210), oklch(58% 0.14 235));
--on-gradient: #001a2e; /* tekstkleur op het gradient, uit de live CTA */
```

Voor tekst-gradients (koppen, "grad-text"):

```css
--gradient-text: linear-gradient(135deg, oklch(80% 0.14 200), oklch(74% 0.17 230) 55%, oklch(78% 0.15 190));
```

## 2. Typografie

Uit de live site: **IBM Plex Sans** voor alles, **IBM Plex Mono** voor labels,
badges en data. Geen serif — het "display"-onderscheid komt van gewicht en
letterspatiëring, niet van een tweede letterfamilie.

```css
--font-body:    'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif;
--font-display: 'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif;
--font-mono:    'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
```

Gewichten (self-hosted woff2, latin-subset): Sans 400 / 500 / 600 / 700,
Mono 400 / 500 / 600. Producten hosten fonts altijd zelf — de
offline-les van Certo (bevriezende inlogpagina op een iPad zonder
internet door een render-blokkerende externe stylesheet) geldt
Tessar-breed. De marketingsite mag wél Google Fonts laden.

Display-regels (site): koppen 600–800, `letter-spacing` −0.015 tot −0.025em bij
groot formaat; lopende tekst 400, `line-height` 1.55–1.7.

Typografische schaal: hergebruik van Certo's bewezen rem-schaal, ratio ~1.2 —
`--text-xs` 12px · `--text-sm` 14px · `--text-base` 16px · `--text-lg` 19px ·
`--text-xl` 23px · `--text-2xl` 28px · `--text-display` 34px.

## 3. Spacing & elevation

Ongewijzigd overgenomen van Certo (bewezen 4px-basis):

```css
--space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
--space-5: 20px; --space-6: 24px; --space-8: 32px; --space-10: 40px; --space-12: 48px;
```

Elevation: drie stappen, in donker thema zwaarder aangezet:

```css
/* licht */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.06);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.18);
/* donker */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.5);
--shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.6);
```

## 4. Componentrichtlijnen

**Primaire knop.** Het Tessar-gradient (`--gradient-primary`) met donkere
tekst (`--on-gradient`), geen uppercase, gewicht 700, radius 8px. Hover: het
donkerdere gradient, geen transform in app-context (de -3px-lift is
marketingsite-flair, geen app-patroon).

**Secundaire knop.** Transparant met `--border`, tekst `--text`; hover:
`--accent-dim`-vulling en `--accent`-tekst.

**Badges & labels.** IBM Plex Mono, uppercase, `letter-spacing` 0.05–0.06em,
gewicht 600, formaat `--text-xs` — het patroon van de sectielabels en
hero-badge op de live site. Semantische badgekleuren komen uit de
`--ok-*`/`--danger-*`-reeksen.

**Kaarten.** `--bg` op `--panel`-ondergrond, `--border`-rand, radius 10–12px,
`--shadow-sm` in rust; `--shadow-md` alleen bij interactieve kaarten op hover.

**Focus-ring.** 2px `--accent`, 2px offset, op alle interactieve elementen
(overgenomen van Certo — dit is een toegankelijkheidseis, geen stijlkeuze).

**Data/tijdstempels.** `--font-mono` met `font-variant-numeric: tabular-nums`.

## 5. Donker thema — richting

Navy is de basis, niet grijs en niet "licht ontwerp geïnverteerd". Regels:

1. Achtergronden hebben altijd een lichte blauwzweem (hue 250–260, chroma
   0.02–0.03) — nooit neutraal zwart/grijs.
2. Accent wordt lichter en blijft dezelfde tintfamilie (70% i.p.v. 48%);
   hover wordt op donker líchter in plaats van donkerder.
3. Vullingen (accent-dim, ok-bg, danger-bg) zijn solide donkere mengsels,
   geen alpha-overlays — voorkomt streperige randen op panelen.
4. Het gradient van de primaire knop blijft identiek in beide thema's;
   de donkere tekstkleur `--on-gradient` haalt daar ruim voldoende contrast.

## 6. Toepassing per product

| Product | Toepassing |
|---|---|
| Marketingsite (`hamdoun`) | is de bron; tokens zijn eruit geëxtraheerd |
| Protocolchecker (generieke template) | thema-laag `public/themes/tessar.css` over de bestaande token-API van `style.css`; activering per deployment via `THEMA=tessar` in `.env`. De Certo-instance zet niets en blijft ongewijzigd. |
| Boekingsassistent | zodra er een frontend is: zelfde tokenbestand als basis |
| Losse n8n-automatiseringen | geen dwingende stijl |
