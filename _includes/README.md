# Gedeelde Eleventy-includes voor tessar.nl

`base.njk`, `header.njk` en `footer-and-scripts.njk` worden door alle 13
gemigreerde statische pagina's gebruikt (elke pagina heeft `{% extends
"base.njk" %}` bovenaan). De homepage (`index.html`) hoort hier **niet** bij —
die wordt nog steeds door `scripts/prerender-index.mjs` gebakken en alleen als
kant-en-klaar bestand meegekopieerd door Eleventy.

Deze includes zijn bewust byte-voor-byte gebouwd om exact dezelfde HTML te
renderen als de oorspronkelijke, losse pagina's vóór de migratie (zie de
taakrapporten in `.superpowers/sdd/2026-09-09-eleventy-migratie-fase2/` voor
de diff-verificatie per pagina). Daarom staat deze uitleg hier in een losse
README in plaats van als HTML-commentaar bovenaan `base.njk` — een commentaar
daar zou in de uitgeleverde `<head>` van alle 13 pagina's verschijnen en dus
zelf weer een (onschuldig, maar onnodig) verschil met de productie-baseline
introduceren.

## De 11 opt-in front-matter-vlaggen

Elke pagina zet in zijn eigen front matter (bovenaan het `.html`-bestand,
tussen `---`) alleen de vlaggen die het nodig heeft. Niets is verplicht buiten
`permalink`; alle vlaggen hieronder zijn optioneel en vallen terug op "uit"
(falsy) tenzij een pagina ze expliciet zet.

| Vlag | Type | Doel |
|---|---|---|
| `activeNav` | string | Welke hoofdnav-link (desktop + mobiel-paneel) vetgedrukt wordt. Waarden: `"services"`, `"industries"`, `"prijzen"`, `"chatbots"`, `"blog"`, `"contact"`. Weggelaten op pagina's zonder eigen hoofdnav-item (privacy.html, 404.html, de 6 artikelpagina's). |
| `ctaHref` | string | Het `href` van de "Plan gesprek"-knop in de header (desktop én mobiel). Meestal `"./index.html#contact"` of `"#stuur-bericht"`/`"./contact.html#stuur-bericht"` op contact-achtige pagina's. |
| `ctaMobileStyle` | string | Inline `style`-attribuut voor de mobiele CTA-link. Varieert per pagina-groep: pagina's met `hasBackToTop` gebruiken de "pill"-stijl (padding+border-radius, geen `text-align`), de rest gebruikt een gecentreerde blok-stijl met `!important` — dit is 1-op-1 overgenomen uit de productie-bron per pagina, niet gestandaardiseerd. |
| `hasBackToTop` | boolean | Rendert de "naar boven"-knop plus het bijbehorende scroll-toon/verberg- en smooth-scroll-script. Alleen gezet op pagina's die deze knop in productie al hadden (privacy, services, contact). |
| `prebody` | Nunjucks block (geen front-matter-vlaag) | Hook-blok vóór `{% include "header.njk" %}` in `base.njk`, bedoeld voor content die vóór de header moet renderen. Alle 13 pagina's overschrijven dit blok momenteel leeg (`{% block prebody %}{% endblock %}`) — het is een gereserveerd uitbreidingspunt, geen actief gebruikte vlag. |
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
