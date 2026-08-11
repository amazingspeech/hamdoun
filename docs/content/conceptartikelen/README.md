# Conceptartikelen — status en werking van de pijplijn

Deze map bevat de 6 conceptartikelen die de n8n-contentpijplijn (Deel 1–4,
zie [`tessar-content-brief-generator.md`](../../superpowers/plans/2026-08-10-tessar-content-brief-generator.md)
en [`deel4-formatteer-goedgekeurd-concept-design.md`](../../superpowers/specs/2026-08-10-deel4-formatteer-goedgekeurd-concept-design.md))
per e-mail heeft aangeleverd, met Nederlandse grammatica/spelling gecorrigeerd
en een paar inhoudelijke fouten rechtgezet (zie per bestand de sectie
"Redactie — wat is aangepast en waarom" bovenaan). Dit is de eerste keer dat
conceptartikelen uit deze pijplijn in de repo worden opgeslagen — er bestond
nog geen vaste plek voor.

## Hoe de pijplijn werkt (Deel 1 → 4)

1. **Deel 1** — houdt keyword-posities bij in de Google Sheet "Keyword
   rankings" (los van deze artikel-pijplijn).
2. **Deel 2** — genereert per tracked keyword een SEO-contentbrief
   (zoekintentie, concurrentie-analyse, CTA-richting) en zet die klaar in de
   sheet "Content briefs" met status `nieuw`.
3. **Deel 3** — schrijft op basis van elke brief een volledig Nederlands
   conceptartikel (ruwe markdown) en **e-mailt dat naar jou** — dit is precies
   de tekst die je hierboven hebt geplakt. Status gaat naar `concept klaar`.
4. **Jij beoordeelt het concept.** Er is bewust **geen automatische
   publicatie**. Zodra je akkoord bent, zet je de rij in de sheet handmatig
   op status `goedgekeurd`.
5. **Deel 4** — zet het goedgekeurde markdown-concept om naar kant-en-klare
   HTML (koppen, **bold**, bullet- en genummerde lijsten) en e-mailt die
   HTML naar je terug. Status gaat naar `geformatteerd`.
6. **Jij plakt de HTML handmatig in een nieuwe pagina.** Dit is de enige
   stap die geen workflow doet — bewust, zie hieronder.

## Waarom niet alles automatisch naar blog.html?

`preview/blog.html` is **geen CMS en geen verzamelpagina voor volledige
artikelen** — het is een overzichtspagina met kaarten die doorlinken naar
losse artikelpagina's. Op dit moment staan er nog 3 placeholder-kaarten in
("EU AI Act", "Wanneer automatisering fout gaat", "Het juiste knelpunt
kiezen") met het label "Binnenkort" en `href="#"` — dat is voorbeeldcontent
uit het originele ontwerp (`Blog.dc.html`), geen gepubliceerde artikelen (zie
de TODO-comment boven die sectie in `blog.html` en commit `3efc84b`).

Elke pagina op de site is met de hand gebouwd (nav, hero, footer manueel
afgestemd op de zusterpagina's) — er bestaat nog **geen `.dc.html`-template
voor een individuele artikelpagina**. Dat is de reden dat Deel 4 bewust
stopt bij "lever kant-en-klare HTML" in plaats van zelf een pagina te bouwen
(zie de "Niet in scope"-sectie in de Deel 4-spec): een workflow die zelf
nav/hero/footer zou construeren loopt het risico uit de pas te lopen zodra
de site verandert.

**Concreet betekent dit, voordat deze 6 artikelen live kunnen:**
1. Er moet een `artikel.dc.html`-sjabloon komen (of losse `.html`-bestanden
   per artikel, zoals `preview/services.html` etc.) met dezelfde nav/hero/
   footer-opbouw als de rest van de site.
2. Elk artikel krijgt een eigen bestand (bijv.
   `preview/blog/ai-receptioniste-voor-bedrijven.html`) met de geformatteerde
   HTML uit Deel 4 als body.
3. De 3 placeholder-kaarten in `blog.html` worden vervangen door echte
   kaarten die naar deze nieuwe artikelpagina's linken (`href="#"` → echte
   URL, "Binnenkort" → echte publicatiedatum).

**Update 2026-08-11:** dat sjabloon bestaat nu wel, en de eerste echte
artikelpagina staat live in deze worktree:
`preview/ai-receptioniste-voor-bedrijven.html`. Gebouwd door de exacte
nav/hero/footer/dark-mode/FAQ-accordion-structuur van `chatbots.html` en
`services.html` te hergebruiken (inclusief hun `Article`- en `FAQPage`
JSON-LD-schema's), met de artikeltekst uit
`ai-receptioniste-voor-bedrijven.md` als body. `blog.html`'s eerste kaart
linkt er nu ook echt naartoe (was `href="#"`/"Binnenkort", is nu een
werkende link met "Augustus 2026"). Geverifieerd in licht + donker + mobiel
via een lokale preview-server; alle tags in balans.

De overige 5 artikelen hebben nog geen eigen pagina — dat volgt hetzelfde
patroon: kopieer de structuur van `ai-receptioniste-voor-bedrijven.html`,
vervang hero/meta/FAQ/body met de tekst uit het betreffende `.md`-bestand,
voeg een kaart toe aan `blog.html`. Niets hiervan is gecommit of gedeployed
— staat alleen lokaal in deze worktree klaar voor review.

## Wat wel en niet is rechtgezet in deze redactieronde

**Wel gedaan (tekst, geen code):**
- Grammatica/spelfouten uit de Haiku-generatie (zie per bestand).
- Eén weggelaten placeholder rechtgezet: artikel 4 noemde letterlijk
  "Competitor 1, 2 en 3" in plaats van een afgemaakte zin — verwijderd en
  herschreven zonder naamsverwijzing, in lijn met de eigen instructie in dat
  artikel's redactie-checklist ("geen impliciete claims over concurrenten
  die niet in de brief staan").
- Een niet-onderbouwde compliance-claim in artikel 1 en 5 ("versleuteld
  opgeslagen op Nederlandse servers, voldoet aan AVG") afgezwakt naar
  "AVG-bewust" — dezelfde aanpak die al eerder is toegepast op
  `chatbots.html` (commit `3efc84b`, daar stond exact dit probleem: een
  certificerings-achtige claim zonder onderliggende audit).
  **Let op: dit is een terugkerend patroon in de Haiku-output** — de
  generator claimt makkelijk certificering/nalevingsclaims. Waard om in de
  Deel 2/3-prompt zelf te verankeren dat dit soort claims vermeden moet
  worden, in plaats van het steeds achteraf te herstellen.
- Twee niet-onderbouwde, verdacht ronde statistieken in artikel 3 (41%
  tijdsbesteding aan administratie, 60-70% e-mails automatisch afgehandeld)
  afgezwakt naar kwalitatieve taal — geen bron voor de exacte cijfers.
- Hoofdlettergebruik "MKB" in artikel 6 genormaliseerd naar "mkb" (kleine
  letters), conform de rest van de site (`index.html`, `services.html`,
  `contact.html`, `prijzen.html`, `chatbots.html` gebruiken allemaal
  kleine letters — geverifieerd met een grep over `preview/*.html`).
- CTA-verwijzingen gecontroleerd tegen de bestaande site: `contact.html`
  heeft een echt werkend formulier (`#contact-form` → `/api/contact`) plus
  directe `tel:`/`mailto:`-links. Artikel-CTA's die naar "een gratis demo"
  of "kennismakingsgesprek" verwijzen kunnen naar `contact.html` of
  `index.html#contact` linken — die routes bestaan.

**Niet gedaan / geblokkeerd (bewust, niet vergeten):**
- Artikel 6's CTA noemt een downloadbare "procesaudit-checklist" en een
  boekbare "gratis consult" als losse lead-magnet — **geen van beide bestaat
  nu op tessar.nl** (geen download, geen losse boekingslink los van het
  contactformulier). Tot die gebouwd zijn, moet die CTA-tekst naar het
  bestaande contactformulier wijzen, anders belooft het artikel iets dat
  niet klikbaar is.
- Klantcases, integratie-verificatie (Google Calendar/Outlook/HubSpot/Zoom),
  concrete prijsstelling — dit staat expliciet en terecht als "wacht op
  launch" in de eigen checklists van de artikelen; niet iets wat ik nu kan
  onderzoeken of verzinnen.
- De inhoudelijke toon/structuur is verder niet herschreven — alleen taal-
  en feitcorrectie, geen contentstrategie-wijziging.
