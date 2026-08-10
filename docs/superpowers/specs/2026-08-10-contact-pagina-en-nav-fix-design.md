# Contact-pagina + navigatie-overflow fix

**Datum:** 2026-08-10
**Repo:** `amazingspeech/hamdoun` (lokaal `/Users/hamdeco/development/hamdoun`), publieke site onder `preview/`

## Doel

1. Een nieuwe, vindbare Contact-pagina toevoegen aan de tessar.nl-site met bedrijfsgegevens
   (telefoon, e-mail, BTW-nummer, KVK-nummer) en een contactformulier met anti-spam.
2. Een bestaande layout-bug oplossen: op `index.html`, `services.html`, `chatbots.html` en
   `prijzen.html` verdwijnt de "Plan gesprek"-knop uit beeld (buiten de zichtbare paginabreedte)
   bij vensterbreedtes net boven de mobiele hamburger-breakpoint (680px) — zichtbaar bevestigd via
   screenshots van `chatbots.html` en `prijzen.html`.

## 1. Nieuwe pagina: `preview/contact.html`

Zelfde bouwpatroon als `services.html`/`chatbots.html`/`prijzen.html`: losse statische NL-pagina
(geen `{{ }}`-templating, geen taal-toggle — die pagina's hebben dat ook niet), met dezelfde
header/footer/back-to-top/mobiele-nav-scripts en dezelfde SEO-boilerplate (`<title>`, canonical,
OG/Twitter-tags) aangepast naar "Contact — Tessar".

**Inhoud:**
- Hero: titel "Contact"
- Bedrijfsgegevens-blok:
  - Telefoon: weergave `+31 6 25577016`, `href="tel:+31625577016"`
  - E-mail: `info@tessar.nl` (al elders op de site gebruikt), `mailto:`-link
  - BTW-nummer: `NL004739184B63`
  - KVK-nummer: `89498593`
- Contactformulier (hergebruikt exact het patroon van `index.html#contact`):
  - Velden: naam (verplicht), e-mail (verplicht), telefoon (optioneel), bericht (verplicht) —
    geen branche-select, want die hoort bij de homepage-flow, niet bij een algemene contactpagina
  - **Anti-spam**, identiek aan het bestaande homepage-formulier zodat de backend (`/api/contact`)
    zonder wijzigingen compatibel blijft:
    - Honeypot-veld `website` (verborgen input, `tabindex="-1"`, `aria-hidden="true"`)
    - `started_at`-timestamp (paginalaadtijd, meegestuurd in de payload — backend kan formulieren
      afwijzen die te snel worden ingediend)
    - `industry` blijft als leeg string-veld in de payload voor schema-compatibiliteit met de
      bestaande backend, maar heeft geen UI-veld op deze pagina
  - Zelfde submit-/statusafhandeling (fetch naar `/api/contact`, succes/foutmelding, disabled state
    tijdens versturen) — gekopieerd, niet herschreven

## 2. Navigatie: Contact-link + overflow-fix

**Contact-link toegevoegd** aan de hoofdnav (desktop + mobiel paneel) op `index.html`,
`services.html`, `chatbots.html`, `prijzen.html` en `contact.html` zelf — tussen "Chatbots" en de
"Plan gesprek"-knop. "Plan gesprek" blijft ongewijzigd naar `#contact` (homepage-sectie, voor het
plannen van een call); de nieuwe link wijst naar `./contact.html` (bedrijfsgegevens + algemeen
bericht).

**Overflow-fix**, toegepast op dezelfde vijf pagina's:
1. Hamburger-breakpoint van `max-width:680px` naar `max-width:960px` — ruime marge boven het punt
   waar de volledige desktop-rij (logo + 6 links + knop, straks met Contact erbij nog breder) krap
   komt te staan.
2. `flex-wrap:wrap` (+ passende `row-gap`) op de desktop-nav-rij als vangnet: als het ondanks de
   hogere breakpoint ooit toch net niet past (zoom-niveau, systeemlettertype als fallback, etc.),
   wrapt de rij netjes naar een tweede regel in plaats van een knop onzichtbaar buiten beeld te
   duwen.
3. Nav-gap gelijkgetrokken naar één waarde op alle vijf pagina's (momenteel wisselt dit tussen
   `12px–28px`, `14px–28px` en `16px–32px` per pagina) zodat alle pagina's identiek breakpoint-gedrag
   vertonen.

`index.html` heeft een extra element in de nav (de NL/EN taal-toggle) dat de andere pagina's niet
hebben — dat blijft ongewijzigd, de fix moet daar ook mee blijven werken.

## Buiten scope

- Geen wijzigingen aan `/api/contact` (backend) — de payload-vorm blijft identiek aan wat de
  homepage al verstuurt, dus geen serverwijziging nodig.
- Geen wijzigingen aan de "Binnenkort online"-gate op de root `index.html` — die blijft ongewijzigd
  (zie bestaande afspraak: root blijft placeholder, echte site staat onder `/preview/`).
- Geen adres toegevoegd (niet aangeleverd door de gebruiker).
- De orphaned `.dc.html`-pagina's (Blog/Pricing/Team/Project Detail/Workflow) worden niet
  aangepast — die zitten niet in de hoofdnavigatie en vallen buiten deze wijziging.

## Verificatie

- Elke pagina lokaal/na deploy bekijken op meerdere breedtes (bewust ruim rond 680–960px) om te
  bevestigen dat de "Plan gesprek"-knop nooit meer buiten beeld valt.
- Contactformulier op `contact.html` end-to-end testen (verzenden, honeypot niet triggeren bij
  normaal gebruik, succesmelding).
- Alle vijf pagina's visueel controleren op consistente nav (incl. nieuwe Contact-link) desktop en
  mobiel.
