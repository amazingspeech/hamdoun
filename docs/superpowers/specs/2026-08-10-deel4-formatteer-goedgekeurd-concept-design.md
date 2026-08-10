# Deel 4 — Formatteer goedgekeurd conceptartikel — design

Datum: 2026-08-10
Status: goedgekeurd, klaar voor implementatieplan

## Doel

Deel 2 en Deel 3 (zie
[2026-08-10-tessar-content-brief-workflow-design.md](2026-08-10-tessar-content-brief-workflow-design.md))
genereren samen een SEO-brief en daarna een Nederlands conceptartikel per
tracked keyword, en mailen dat concept naar de gebruiker als ruwe markdown.
De gebruiker leest en beoordeelt het concept zelf (er is geen automatische
publicatie — zie de "Niet in scope"-sectie hieronder voor waarom). Op dit
moment moet de gebruiker, zodra een concept is goedgekeurd, zelf met de hand
elke `#`/`##`-kop en elke opsomming omzetten naar HTML-tags wanneer hij het
artikel in een nieuwe pagina van de site plakt. Deze workflow ("Deel 4")
neemt dat tik-werk over: na handmatige goedkeuring levert hij een kant-en-klare
HTML-versie van het artikel, klaar om te plakken.

**Niet in scope:** automatisch publiceren naar de live site. De site
(`preview/*.html`) is geen CMS — elke pagina is met de hand gebouwd vanuit
een `.dc.html`-designtemplate, met zorgvuldige afstemming op de opmaak van
zusterpagina's (nav, hero, footer). Er bestaat nog geen `.dc.html`-template
voor een individuele artikelpagina (`blog.html` is nu alleen een
overzichtspagina met 3 losse voorbeeldkaarten). Een workflow die zelf een
complete pagina genereert zou nav/hero opnieuw moeten construeren zonder de
zekerheid dat die in de pas blijft lopen met toekomstige site-wijzigingen.
Deze workflow levert daarom alleen de artikel-*body* als HTML — de gebruiker
bouwt de pagina zelf, zoals bij elke andere pagina op de site.

## Aanpak

**Losse workflow "Deel 4", zelfde patroon als Deel 2/3.** Manual trigger,
standaard inactief, credentials worden na aanmaken handmatig gekoppeld in de
n8n-UI. Geen nieuwe trigger-technologie (geen schedule/polling, geen sheet-
webhook) — de gebruiker start 'm zelf, net als de andere delen, nadat hij een
concept heeft goedgekeurd. Overwogen alternatieven (schedule-trigger die
periodiek pollt; een Apps Script `onEdit`-webhook in de Sheet zelf) zijn
afgewezen: ze voegen nieuwe bewegende delen toe (een cron-achtige node,
respectievelijk onderhoud van een los Apps Script) voor een taak die de
gebruiker toch al handmatig test en start.

**Statusveld uitgebreid, geen nieuwe sheet-kolommen voor output.** De
"Content briefs"-tab (spreadsheet `1SLuPNAxwQspFyDTopVQfYvb6Xyyox5fWGCnGZMWx0a0`,
gid `210428761`) kent nu de statusflow `nieuw` (Deel 2) → `concept klaar`
(Deel 3) → **`goedgekeurd`** (gebruiker zet dit handmatig na review) →
**`geformatteerd`** (Deel 4 zet dit automatisch aan het eind, zodat een rij
niet twee keer verwerkt wordt bij een herhaalde run). De output zelf gaat
per e-mail, net als Deel 2/3 — geen extra sheet-kolom nodig.

**Markdown→HTML-conversielogica los gekopieerd naar 2 plekken (niet als
gedeelde sub-workflow).** Bij het uitwerken van dit ontwerp bleek de
bestaande e-mail-opmaak in Deel 3 (node "Bouw e-mail met conceptartikelen")
onvolledig: die zet alleen `#`/`##` om naar echte HTML-koppen, maar laat
`**bold**` en opsommingen (`- item`, `1. item`) als kale markdown-tekens
staan. Dat wordt in dezelfde beurt gefixt, met een uitgebreide
`markdownToHtml`-functie (zie "Conversielogica" hieronder) die letterlijk
hetzelfde in de nieuwe Deel 4-node komt te staan. Overwogen alternatief: één
centrale converter-workflow die beide plekken via een "Execute
Workflow"-node aanroepen — afgewezen omdat dat een afhankelijkheid tussen
workflows introduceert voor zo'n 15 regels code, terwijl elke node in dit
systeem tot nu toe bewust zelfstandig is. Bij bugs moet de functie op 2
plekken gefixt worden — geaccepteerd risico op deze schaal.

## Workflow-opbouw (Deel 4)

Nieuwe workflow **"Deel 4 - Formatteer goedgekeurd conceptartikel"**,
dezelfde node-stijl als Deel 3:

1. **Manual Trigger** — "When clicking 'Execute workflow'"
2. **Google Sheets — Get Row(s)** — "Lees Content briefs" (tab via
   `mode: "list"`, waarde de bare numerieke gid `210428761` als JSON-getal,
   niet als string en niet met een `"gid="`-voorvoegsel — beide varianten
   faalden eerder stil of vielen terug op de eerste tab zonder foutmelding,
   ontdekt tijdens het debuggen van Deel 3)
3. **Code — Filter** — "Filter goedgekeurde briefs": `status === 'goedgekeurd'`
4. **Code — Formatteer HTML** — "Formatteer artikel naar HTML": past de
   uitgebreide `markdownToHtml`-functie toe op `draft_markdown`
5. **Code — Bouw e-mail** — "Bouw e-mail met opgemaakt artikel": zelfde
   visuele stijl (fonts/kleuren) als de bestaande Deel 3-mail, met de
   kant-en-klare HTML-body
6. **Gmail — Send** — "Verstuur geformatteerd artikel" (bestaande
   `gmailOAuth2`-credential hergebruiken)
7. **Google Sheets — Update** — "Zet status op 'geformatteerd'" (matcht op
   `row_number`, zelfde patroon als Deel 3's "Update status naar 'concept
   klaar'")

## Conversielogica (markdownToHtml, uitgebreid)

Uitbreiding op de bestaande functie in "Bouw e-mail met conceptartikelen"
(die alleen `#`/`##` naar `<h1>`/`<h2>` omzet). Toegevoegd:

- **Bold** (`**tekst**`) → `<strong>tekst</strong>`, ook binnen lopende
  alinea's
- **Bullet-lijsten** (aaneengesloten regels die met `- ` beginnen) → één
  `<ul>`-blok met een `<li>` per regel, in plaats van als losse `<p>`-regels
  met kale streepjes
- **Genummerde lijsten** (aaneengesloten regels `1. `, `2. `, ...) → één
  `<ol>`-blok met een `<li>` per regel
- `#` / `##` → ongewijzigd, blijft `<h1>`/`<h2>`
- Overige alinea's → `<p>` zoals nu

**Expliciet niet meegenomen (YAGNI):** italic (`*tekst*`), links, tabellen,
geneste lijsten, blockquotes. Deze komen niet voor in de huidige
brief-/artikel-prompts. Als een toekomstige prompt-wijziging dit wel
oplevert, breidt een latere iteratie de functie dan uit — niet nu alvast
bouwen voor content die niet bestaat.

## Foutafhandeling & scope-grenzen

- Als "Filter goedgekeurde briefs" 0 rijen oplevert, stopt de workflow
  stil zonder foutmelding — een normale, verwachte staat (net als bij Deel 3
  wanneer er nog niets op de juiste status staat).
- Geen wijzigingen aan Deel 1 of Deel 2. De enige wijziging aan een
  bestaande workflow is de geïsoleerde e-mail-formatter-fix in Deel 3 (node
  "Bouw e-mail met conceptartikelen").
- Credentials worden, zoals bij elke n8n-workflow in dit systeem, niet via
  de API gekoppeld — de gebruiker doet dat zelf na aanmaken in de UI.
- Workflow blijft na aanmaken inactief; de gebruiker test zelf handmatig.

## Testen

- Handmatige test in de n8n-UI, zoals bij Deel 2/3: gebruiker zet een rij op
  `goedgekeurd`, draait Deel 4, controleert de ontvangen e-mail op correcte
  HTML-weergave (koppen, bold, bullet- en genummerde lijsten) en controleert
  dat de rij in de sheet op `geformatteerd` staat na afloop.
- Los daarvan: de gefixte `markdownToHtml`-functie in Deel 3's e-mail-node
  testen door een workflow-run te draaien op het al bestaande, eerder
  gegenereerde conceptartikel en te controleren dat bold/lijstjes nu wél
  correct renderen (dit artikel bevatte al bold-tekst en zowel bullet- als
  genummerde lijsten — een representatieve test case, geen synthetische
  input nodig).
