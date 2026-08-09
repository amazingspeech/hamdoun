# Content-brief generator voor Tessar SEO-keywords — design

Datum: 2026-08-10
Status: goedgekeurd, klaar voor implementatieplan

## Doel

Tessar (tessar.nl) is pre-launch en heeft nog nauwelijks content. De
bestaande n8n-workflow "Track keyword rankings on Google with Apify and send
AI SEO reports by email" (n8n.tessar.nl, workflow-ID `XFq6k3Am6JVsDNxA`)
volgt wekelijks 8 Nederlandse keywords en logt per keyword de top-resultaten
(titel, beschrijving, domein, positie) in het Google Sheet "Keyword
rankings". Die keyword-kansen blijven nu onbenut zolang niemand weet wélke
content Tessar moet schrijven om ze te pakken.

Deze workflow maakt daar invulling aan: op verzoek genereert hij per
tracked keyword een concrete SEO-brief (onderwerp, kopjesstructuur,
concurrentie-invalshoek) die de gebruiker zelf uitwerkt tot een artikel. De
gebruiker heeft weinig marketingervaring en wil vooral een concreet
startpunt, geen 8 losse opties om zelf te moeten prioriteren.

**Niet in scope:** het schrijven van volledige, publicatieklare artikelen
(de gebruiker werkt de briefs zelf uit); het automatisch publiceren van
content op tessar.nl; het opnieuw ophalen van SERP-data via Apify (zie
"Databron" hieronder).

## Aanpak

**Losse workflow, geen uitbreiding van de bestaande tracker.** Overwogen
alternatief: dezelfde wekelijkse run van de tracker-workflow uitbreiden met
brief-generatie. Afgewezen — de gebruiker wil de content-generator apart
kunnen aan/uitzetten zonder de rankingtracker te raken ("makkelijker te
beheren, als ik geen output nodig heb kan ik hem los uitzetten"). Twee
workflows die dezelfde Google Sheets-credential en hetzelfde Sheet lezen is
op deze schaal (8 keywords, handmatige trigger) geen probleem.

**Databron: het bestaande Sheet, geen nieuwe Apify-call.** De brief-generator
leest de titels/beschrijvingen van de top-concurrenten uit het "Keyword
rankings"-Sheet dat de tracker al wekelijks vult, in plaats van zelf opnieuw
te scrapen. Voordeel: geen extra Apify-kosten, en de twee workflows blijven
qua code volledig van elkaar losstaand terwijl ze wel dezelfde brondata
hergebruiken. Nadeel — geaccepteerd: de brief-data is zo vers als de laatste
tracker-run; als de tracker een tijd niet heeft gedraaid, genereert de
workflow briefs op verouderde concurrentiedata. Voor het huidige, wekelijkse
schema van de tracker is dat geen probleem.

**Per keyword een eigen Claude-call, geen ene grote batch-aanroep.** Bij één
aanroep die alle 8 keywords tegelijk moet afhandelen, wordt de output richting
het einde van het antwoord merkbaar dunner (bekend gedrag bij lange,
opgesomde taken in één response). Acht losse, gerichte aanroepen kosten iets
meer tokens en tijd, maar leveren consistent uitgewerkte, bruikbare briefs —
belangrijker hier omdat de gebruiker deze briefs één-op-één als
schrijfopdracht gebruikt.

**Prioritering zonder extra AI-call.** In plaats van een aparte
samenvattende Claude-aanroep die alle 8 briefs opnieuw leest om te
prioriteren, geeft elke per-keyword aanroep zelf al een machineleesbaar
moeilijkheidsgraad-label mee (`makkelijk` / `gemiddeld` / `lastig` + een
kernreden). Een Code-node sorteert daarop. Goedkoper en deterministischer
dan een tweede AI-call, en de "Waar begin je?"-lijst blijft rechtstreeks
herleidbaar tot de onderliggende brief-data.

## Architectuur en dataflow

Nieuwe, losse n8n-workflow in dezelfde n8n-instance (n8n.tessar.nl),
hergebruikt de al gekoppelde Google Sheets-, Anthropic- en
Gmail-credentials.

1. **Manual Trigger** — "Execute workflow" in de n8n-editor. Geen schema;
   de gebruiker start dit zelf, met name in het begin.
2. **Google Sheets — Read** — leest alle rijen uit het "Keyword
   rankings"-tabblad (zelfde spreadsheet als de tracker).
3. **Code node — "Bouw keyword-context"** — groepeert de rijen per keyword,
   pakt per keyword alleen de meest recente `checked_at`-datum, en houdt de
   top-3 concurrenten (rank 1-3) over met titel, beschrijving, domein en
   positie. Output: één item per tracked keyword,
   `{ keyword, top_competitors: [...], has_data: bool }`. Keywords zonder
   rijen (tracker nog niet gedraaid voor die term) krijgen `has_data: false`
   en worden niet naar Claude gestuurd — zie Foutafhandeling.
4. **Split Out** — één item per keyword de rest van de flow in.
5. **Anthropic Chat Model (Claude Opus 5) + Basic LLM Chain** — per keyword
   één aanroep, structured output (JSON) met de brief-velden (zie hieronder)
   inclusief het moeilijkheidsgraad-label. Zelfde patroon als de bestaande
   "Generate AI SEO report"-node in de tracker-workflow.
6. **Aggregate** — verzamelt alle gegenereerde briefs terug tot één lijst.
7. **Code node — "Sorteer en bouw e-mail"** — sorteert op moeilijkheidsgraad
   (makkelijk → lastig), bouwt de "Waar begin je?"-lijst bovenaan, en zet
   alle volledige briefs daaronder om naar de uiteindelijke HTML.
8. **Gmail — Send** — verstuurt één e-mail naar `info@tessar.nl`, zelfde
   Gmail-credential als de tracker.

## Inhoud van een brief

Elke brief (JSON-gestructureerde output van stap 5) bevat:

- `keyword` — het doelzoekwoord
- `title` — voorgestelde paginatitel/H1
- `meta_description` — ±155 tekens
- `content_type` — "blogartikel" of "dienstenpagina", met één zin
  onderbouwing
- `outline` — lijst van H2/H3-koppen, elk met 1-2 zinnen sturing over wat
  erin moet
- `differentiation` — de invalshoek t.o.v. de concurrent(en) die nu op dat
  keyword scoren, met naam genoemd (bijv. Voicelabs, VoxFlow, Aanloop AI,
  Frontcall, Ploko — zoals al vastgelegd in de system-prompt van de tracker)
- `estimated_word_count` — geschatte lengte
- `priority` — `makkelijk` / `gemiddeld` / `lastig`
- `priority_reason` — één zin onderbouwing (gebruikt voor de "Waar begin
  je?"-lijst)

## E-mailopmaak

- Onderwerp: `Content briefs - Tessar - {datum}`
- Bovenaan: **"Waar begin je?"** — de keywords met `has_data: true`,
  gesorteerd makkelijk → lastig, elk als één regel: keyword + `priority` +
  `priority_reason`.
- Keywords met `has_data: false` (nog geen trackerdata) komen in een apart,
  kort blokje: "Nog geen data voor: … — draai eerst de rankingtracker."
- Daaronder: de volledige briefs, in dezelfde volgorde als de "Waar begin
  je?"-lijst, elk met alle velden uit de vorige sectie.
- Zelfde simpele HTML-restrictie als de tracker-e-mail (h2/h3/p/ul/li/strong,
  geen markdown, geen CSS).

## Foutafhandeling

- **Keyword zonder trackerdata:** wordt gedetecteerd in stap 3
  (`has_data: false`), niet naar Claude gestuurd, en apart vermeld in de
  e-mail in plaats van de workflow te laten falen.
- **Claude-output voldoet niet aan het schema:** n8n's structured-output
  validatie op de LLM Chain-node retryt automatisch; geen extra
  foutafhandeling nodig bovenop wat de node al biedt.
- **Gmail-verzending faalt:** zichtbaar als node-fout in de n8n
  Executions-tab, zelfde gedrag als de bestaande tracker-workflow. Geen
  aparte retry-logica voor deze eerste versie.

## Testen

1. Stap 1-4 los uitvoeren ("Execute step" per node) en de
   keyword-contextdata controleren voordat er Claude-aanroepen worden
   gedaan.
2. De Claude-brief-node op 1-2 keywords los testen en de briefkwaliteit
   beoordelen (klopt de structuur, is de concurrentie-invalshoek concreet
   genoeg, is de moeilijkheidsgraad plausibel).
3. Pas daarna de volledige workflow end-to-end draaien (alle 8 keywords) en
   de ontvangen e-mail controleren op opmaak en volledigheid.
