# Gedeelde Eleventy-includes voor tessar.nl

`base.njk`, `header.njk` en `footer-and-scripts.njk` worden door alle 13
gemigreerde statische pagina's gebruikt (elke pagina heeft `{% extends
"base.njk" %}` bovenaan). De homepage (`index.html`) hoort hier **niet** bij —
die wordt nog steeds door `scripts/prerender-index.mjs` gebakken en alleen als
kant-en-klaar bestand meegekopieerd door Eleventy.

Deze includes zijn bewust byte-voor-byte gebouwd om exact dezelfde HTML te
renderen als de oorspronkelijke, losse pagina's vóór de migratie (zie de
taakrapporten in `.superpowers/sdd/2026-09-09-eleventy-migratie-fase2/` voor
de diff-verificatie per pagina), met één bewuste, sindsdien toegevoegde
uitzondering: sinds Fase 3 van het CSS-consolidatietraject stuurt `base.njk`
een extra `<link rel="stylesheet" href="./assets/tessar.css">`-regel uit (zie
hieronder), dus de output is niet langer een absolute byte-voor-byte-claim
maar "byte-identiek op die ene, bewuste `<link>`-regel na". Daarom staat deze
uitleg hier in een losse README in plaats van als HTML-commentaar bovenaan
`base.njk` — een commentaar daar zou in de uitgeleverde `<head>` van alle 13
pagina's verschijnen en dus zelf weer een (onschuldig, maar onnodig) verschil
met de productie-baseline introduceren.

## Gedeelde CSS: `assets/tessar.css`

Sinds Fase 3 van het CSS-consolidatietraject bestaat `assets/tessar.css` als
het gedeelde stijlbestand voor deze 13 Eleventy-pagina's. Het wordt gelinkt
vanuit `base.njk` (naast `assets/tessar-design-tokens.css`, dat de
kleurtokens/variabelen levert). Een nieuwe CSS-regel die op meerdere pagina's
identiek zou zijn hoort voortaan thuis in `assets/tessar.css`, niet herhaald
in een pagina's eigen `{% block styles %}` — zie het commentaar bovenaan
`assets/tessar.css` en `scripts/extract-shared-css.mjs` voor hoe gedeelde
regels daarheen zijn verplaatst en geverifieerd.

## De 11 opt-in front-matter-vlaggen

Elke pagina zet in zijn eigen front matter (bovenaan het `.html`-bestand,
tussen `---`) alleen de vlaggen die het nodig heeft. Op twee na (zie hieronder)
is niets verplicht buiten `permalink`: alle overige vlaggen zijn optioneel en
vallen terug op "uit" (falsy) tenzij een pagina ze expliciet zet.

**Uitzondering: `ctaHref` en `ctaMobileStyle` zijn VERPLICHT, niet optioneel.**
`_includes/header.njk` rendert `href="{{ ctaHref }}"` en
`style="{{ ctaMobileStyle }}"` zonder default en zonder guard. Laat een
pagina deze weg, dan bouwt Eleventy gewoon door (geen fout, geen waarschuwing)
en rendert stilletjes `href=""` (de "Plan gesprek"-knop wordt een reload van
de huidige pagina) en `style=""` (onopgemaakte mobiele CTA). Er is bewust geen
gedeelde default toegevoegd, omdat de waarde per pagina-groep verschilt (zie
de tabel hieronder), maar dat maakt deze twee vlaggen mandatory-met-stille-
fallback, precies de gevaarlijkste combinatie. Zet ze op elke nieuwe pagina.

| Vlag | Type | Doel |
|---|---|---|
| `activeNav` | string | Welke hoofdnav-link (desktop + mobiel-paneel) vetgedrukt wordt. Waarden: `"services"`, `"industries"`, `"prijzen"`, `"chatbots"`, `"blog"`, `"contact"`. Weggelaten op pagina's zonder eigen hoofdnav-item (privacy.html, 404.html, de 6 artikelpagina's). |
| `ctaHref` **(VERPLICHT)** | string | Het `href` van de "Plan gesprek"-knop in de header (desktop én mobiel). Meestal `"./index.html#contact"` of `"#stuur-bericht"`/`"./contact.html#stuur-bericht"` op contact-achtige pagina's. Geen default in `header.njk`: weggelaten geeft stil `href=""`. |
| `ctaMobileStyle` **(VERPLICHT)** | string | Inline `style`-attribuut voor de mobiele CTA-link. Varieert per pagina-groep: pagina's met `hasBackToTop` gebruiken de "pill"-stijl (padding+border-radius, geen `text-align`), de rest gebruikt een gecentreerde blok-stijl met `!important`, dit is 1-op-1 overgenomen uit de productie-bron per pagina, niet gestandaardiseerd. Geen default in `header.njk`: weggelaten geeft stil `style=""`. |
| `hasBackToTop` | boolean | Rendert de "naar boven"-knop plus het bijbehorende scroll-toon/verberg- en smooth-scroll-script. Alleen gezet op pagina's die deze knop in productie al hadden (privacy, services, contact). |
| `prebody` | Nunjucks block (geen front-matter-vlaag) | Content-hook helemaal bovenaan `<body>`, vóór `{% include "header.njk" %}` in `base.njk`. Wél actief gebruikt, op drie manieren: `prijzen.html` vult dit blok met een echt, substantieel JSON-LD-blok (FAQPage-structured-data, 28 regels), dat komt zo terecht in `<body>`, vóór `<header>`, wat geldig is (Google accepteert JSON-LD overal in het document) en 1-op-1 overeenkomt met de productie-bron. `blog.html` + de 6 artikelpagina's (7 pagina's) zetten `{% block prebody %}{% endblock %}` juist leeg, puur om een blanco regel te onderdrukken die `base.njk`'s eigen block-default (een kale newline tussen `{% block prebody %}` en `{% endblock %}` in `base.njk` zelf) anders zou renderen vóór `{% include "header.njk" %}`, functioneel een 4e whitespace-vlag naast `tightHeaderGap`/`tightFooterGap`/`noTrailingNewline`. De overige 5 pagina's (`privacy`, `services`, `chatbots`, `contact`, `404`) laten het blok volledig weg en krijgen dus wél die default blanco regel vóór `<header>`, dat is precies wat hun eigen productie-bron ook had, vandaar dat deze 5 pagina's byte-identiek blijven. |
| `tightHeaderGap` | boolean | Onderdrukt een blanco regel die `base.njk` normaal vóór `{% block content %}` zou renderen. Puur whitespace-byte-parity met pagina's wier bron-HTML géén lege regel had op die plek (prijzen.html, blog.html). Geen zichtbaar effect. |
| `tightFooterGap` | boolean | Zelfde mechanisme als `tightHeaderGap`, maar dan ná `{% block content %}` / vóór de footer-include. Ook puur whitespace, geen zichtbaar effect. |
| `noTrailingNewline` | boolean | Onderdrukt de trailing newline die `base.njk` normaal ná `</html>` zou schrijven. Whitespace-byte-parity met bronbestanden die geen eind-regeleinde hadden. |
| `extraScripts` | string (raw HTML, via `\| safe`) | Injecteert extra `<script>`-blokken in `footer-and-scripts.njk`, ná het reveal-script en vóór het nav-toggle-script. Alleen gebruikt door chatbots.html (demo-tab-wisselscript dat in productie ook op die plek stond). |
| `blogLinkBold` | boolean | Maakt de "Blog"-link in de hoofdnav (desktop) vetgedrukt, onafhankelijk van `activeNav`. Gebruikt door de 6 artikelpagina's: die horen inhoudelijk bij de blog-sectie maar hebben geen eigen `activeNav`-waarde (ze zijn zelf geen hoofdnav-item). Werkt additief naast `activeNav`, niet als vervanging. |
| `noRevealScript` | boolean | Laat het hele IntersectionObserver scroll-reveal-script (dat `[data-reveal]`-elementen bij scroll-in-beeld `is-visible` maakt) weg. Alleen gezet op 404.html, de enige pagina zonder `data-reveal`-elementen — productie leverde dit script daar nooit uit. |

## Waarom zoveel vlaggen voor "alleen maar whitespace"?

Drie van de vlaggen (`tightHeaderGap`, `tightFooterGap`, `noTrailingNewline`)
bestaan uitsluitend om een lege regel of ontbrekend regeleinde weg te werken
— geen enkel zichtbaar of functioneel verschil. Dat is een bewuste, in Taak 4
bekrachtigde afweging: voor de eerste paar pagina's (privacy, services,
contact, chatbots, prijzen) is gekozen voor "geen enkele tolerantie, ook niet
voor whitespace" via deze vlaggen, omdat toen nog onduidelijk was of
whitespace-verschillen soms toch een teken van een dieperliggende fout waren.
Vanaf Taak 5 is dat versoepeld: nieuwe pure-whitespace-verschillen worden
sindsdien gewoon genoteerd in het taakrapport in plaats van een nieuwe vlag te
forceren (zie `.superpowers/sdd/2026-09-09-eleventy-migratie-fase2/progress.md`,
"Ruling" onder Taak 4). De 5 taak-4-vlaggen zelf zijn blijven staan — ze
werken en zijn al gereviewd — maar er zijn dus bewust geen 5-10 vergelijkbare
vlaggen bijgekomen voor de resterende 7 pagina's.

## `social`/`jsonld`: op 3 pagina's staat de inhoud omgewisseld

`base.njk` plaatst `{% block social %}{% endblock %}{% block jsonld %}{% endblock %}`
als twee aangrenzende, volgorde-behoudende content-slots in `<head>`, de
namen suggereren een strikte betekenis ("social meta" versus "structured
data"), maar dat zijn ze niet. Op **`chatbots.html`**, **`contact.html`** en
**`blog.html`** is de inhoud bewust omgewisseld om de exacte byte-volgorde van
productie op die 3 pagina's te behouden (productie had daar JSON-LD vóór de
og/twitter-meta staan):

- `{% block social %}` bevat op deze 3 pagina's de JSON-LD `<script
  type="application/ld+json">`-tag(s).
- `{% block jsonld %}` bevat op deze 3 pagina's juist de og/twitter
  `<meta>`-tags.

Op de overige 10 pagina's komt de inhoud wél overeen met de blocknaam
(`social` = og/twitter-meta, `jsonld` = structured data). De uitgeleverde
HTML is op alle 13 pagina's correct (byte-identiek aan productie), dit is
puur een documentatie-valkuil: wie op `chatbots.html`, `contact.html` of
`blog.html` "het social-block" gaat aanpassen, vindt daar JSON-LD, niet
og/twitter-meta. Niet in deze fix-ronde opgelost door de blocks te hernoemen
of de 3 pagina's te herstructureren, dat is expliciet Fase-3-werk dat een
verse byte-diff-pas over die 3 pagina's vereist.
