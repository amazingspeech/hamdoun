# Tess geeft een automatiseringsdiagnose — ontwerp

**Datum:** 2026-08-12
**Status:** geïmplementeerd en live in productie (zie `docs/superpowers/plans/2026-08-12-tess-automatiseringsdiagnose.md` voor de uitvoering en `docs/superpowers/plans/2026-08-12-tess-automatiseringsdiagnose-qa-resultaten.md` voor de QA-resultaten)

## Achtergrond & aanleiding

Dit is het tweede concept in dezelfde brainstorm-sessie als
[[2026-08-12-tess-spraakmodus-design.md]] (zie ook de memory-notitie
`tess-spraakmodus-plan.md`, status: abandoned). Kort de weg hiernaartoe:

1. Startpunt: een systeem bouwen vergelijkbaar met de LaraContact-template
   (verkoopbaar CRM met AI-assistentie), toegesneden op wat Tessar voor
   staat.
2. Via stapsgewijze scope-versmalling kwam de eerste uitwerking uit op
   "Tess spraak geven" (voice mode voor de bestaande live tekst-concierge).
3. Dat plan is **afgeblazen**: de STT/TTS-stap vereiste onvermijdelijk een
   niet-Anthropic partij (Anthropic heeft geen spraak-API), en de gebruiker
   wil AI-productwerk voor Tessar uitsluitend via Claude/Anthropic laten
   lopen — geen andere AI-leveranciers, ook niet de gratis/account-loze
   Web Speech API. Dit is een **staande beperking** voor toekomstig
   Tessar-productwerk, niet alleen voor dit ene geval.
4. Terug naar de tekentafel, breed heroverwogen: het kernprobleem bij
   klanten is niet "ze willen niet automatiseren" maar "ze missen kennis/tijd
   om het zelf te doen" — en de gebruiker wil dat de AI zelf het "opzetten"
   voorstelt (in plaats van dat Tessar het handmatig per klant bouwt), maar
   met een mens die de daadwerkelijke koppeling/activering goedkeurt en
   uitvoert (geen autonome AI die op systemen van klanten inlogt).
5. Doelgroep versmald naar: nieuwe leads/prospects tijdens het eerste
   contact (een verkoop-tool), niet een doorlopend product voor bestaande,
   betalende klanten met eigen accounts.
6. Kernzorg van de gebruiker: een volledig, concreet automatiseringsplan
   gratis weggeven in de chat betekent dat een bezoeker het kan meenemen en
   zelf (of via een goedkopere concurrent) laten bouwen, zonder dat Tessar
   er iets aan overhoudt.
7. Onderzoek (zie sectie hieronder) bevestigde: dit is een reëel risico,
   maar met een bekende, goed gedocumenteerde oplossing — **diagnose, niet
   recept**. Meerdere directe Nederlandse concurrenten (Skrepr, Aanloop AI,
   AI-Bureau) passen dit patroon al toe: gratis een gescoorde, gerangschikte
   diagnose, nooit een bouwklaar plan.

## Onderzoeksbevindingen (samenvatting)

Volledig onderzoeksrapport is niet apart gearchiveerd; kernpunten hieronder
ter onderbouwing van de ontwerpkeuzes verderop.

- **Het onderliggende patroon is beproefd:** gratis, persoonlijke diagnose
  vooraf als verkoop-tactiek is een gevestigde aanpak (bv. HubSpot's Website
  Grader: gratis score + concrete verbeterpunten, gate op e-mailadres,
  10M+ leads over de levensduur van de tool). De reciprociteitsprincipe uit
  marketingliteratuur onderbouwt waarom dit werkt: echte waarde eerst geven
  verhoogt de kans op een tegenprestatie.
- **De precieze uitvoering (AI die tijdens een open gesprek een diagnose
  opstelt, i.p.v. een quiz/formulier) is minder beproefd** — alle gevonden
  voorbeelden zijn quiz-/scoreformulier-gebaseerd, geen open
  gesprek-naar-diagnose. Dit is dus een iets nieuwere uitvoering van een wel
  bewezen onderliggend mechanisme, geen volledig bewezen exacte aanpak.
- **De consistente grens bij elk gevonden voorbeeld — consulting-literatuur
  én directe concurrenten:** geef gratis het "wat" (probleemherkenning +
  categorie oplossing + richting van de impact), houd het "hoe" (specifieke
  tools/API's, koppelvolgorde, effort-inschatting) achter een gesprek/betaald
  traject. Geen van de onderzochte Nederlandse concurrenten (Skrepr, Aanloop
  AI, AI-Bureau) geeft een bouwklaar plan gratis weg.
- **Wat niet werkt als bescherming:** de gratis output vaag/algemeen houden
  in de hoop dat het te weinig waard is om mee weg te lopen. Dat ondermijnt
  juist de hele tactiek (niemand vertrouwt een vage diagnose). De aanbevolen
  aanpak is specifiek zijn over het *probleem*, stil zijn over de
  *oplossing*.

## Scope van dit project

**Wel:**
- Een uitbreiding van de systeemprompt van de bestaande "Tessar Concierge
  Agent"-node (in de al-lopende n8n-workflow achter Tess) die haar leert
  wanneer en hoe een automatiseringsdiagnose te geven wanneer een lead een
  proces-probleem beschrijft.
- De diagnose bevat: probleemherkenning (met concrete details uit het
  gesprek, dat mag wél specifiek zijn), categorie van de oplossing (in
  algemene termen), en een richtinggevende impact-inschatting (een range,
  geen harde belofte).
- Een expliciete, eerlijk geformuleerde overgang naar een vervolggesprek
  voor de concrete invulling — met een oprechte reden ("de exacte stappen
  hangen af van jouw systemen"), niet als kunstmatige afkapping.
- Verrijking van de bestaande `stuur_lead_naar_team`-tool: de
  gegenereerde diagnose gaat mee in de lead-mail naar het team, zodat zij
  met meer context het vervolggesprek ingaan.

**Expliciet niet:**
- Geen technisch bouwplan/spec voor de lead: geen specifieke tool-/
  API-namen, geen stap-voor-stap koppelvolgorde, geen effort-/
  tijdsinschatting voor de bouw zelf.
- Geen automatische activering/koppeling met systemen van de klant — een
  mens (Tessar, en later mogelijk de klant) beoordeelt en zet altijd zelf
  iets live.
- Geen klant-accounts of doorlopend product — dit blijft een verkoop-tool
  voor het eerste contact, geen SaaS-schil.
- Geen nieuwe AI-leverancier — blijft volledig binnen Claude Haiku 4.5 via
  de bestaande Anthropic-node in n8n.
- Geen nieuwe webhook, nieuw node-type, of nieuwe UI-component in de
  widget.

## Architectuur

Geen nieuwe infrastructuur: een prompt-/gedragswijziging binnen de
bestaande, al-lopende workflow.

```
Bezoeker beschrijft een proces-probleem in de Tess-chat
        │
        ▼
Bestaande "Tessar Concierge Agent" (Claude Haiku 4.5, ongewijzigde node)
  herkent dit als een automatiseringsvraag (nieuwe systeemprompt-instructie)
        │
        ▼
Genereert een diagnose-antwoord binnen de vastgelegde grenzen:
  - Probleemherkenning (specifiek, uit het gesprek)
  - Categorie oplossing (algemeen: "koppeling tussen X en Y met een
    AI-classificatiestap", geen exacte tools/API's)
  - Richting van de impact (range, geen harde belofte)
  - Eerlijke overgang naar een gesprek voor de concrete invulling
        │
        ├─► Weergave: bestaande chatbubbel-rendering in de widget
        │   (`renderBotHtml` in tessar-concierge-widget.js — vet/lijsten,
        │   geen nieuwe UI nodig)
        │
        └─► `stuur_lead_naar_team` (bestaande tool, ongewijzigd qua
            trigger-logica): mailt de diagnose mee naar het team
```

## Content-grens (kern van dit ontwerp)

De systeemprompt-instructie moet expliciet en met voorbeelden vastleggen
wat wel en niet in een diagnose mag:

**Wel (het "wat"):**
- Concrete, specifieke probleemherkenning gebaseerd op wat de bezoeker
  vertelde ("je verwerkt nu handmatig offerteaanvragen die binnenkomen via
  het contactformulier").
- Categorie van de oplossing, in algemene termen ("een koppeling tussen je
  contactformulier en je CRM, met een AI-stap die de aanvraag classificeert
  en doorstuurt").
- Richtinggevende impact ("dit kan al snel een paar uur per week schelen"),
  nooit een precies, hard cijfer gebaseerd op een aanname over hun
  facturatie/proces.
- Een oprechte, specifieke reden waarom de concrete invulling een gesprek
  vereist ("welke exacte koppeling het beste past, hangt af van welk CRM je
  gebruikt").

**Nooit (het "hoe"):**
- Specifieke tool-, product- of API-namen (geen "gebruik hiervoor
  Zapier/n8n-node X met endpoint Y").
- Stap-voor-stap bouw-/implementatievolgorde.
- Een effort- of tijdsinschatting voor de bouw zelf (impact voor de klant
  mag wel, bouwtijd voor Tessar niet).
- Iets dat leest als een spec waar een freelancer/concurrent direct tegen
  zou kunnen offreren.

## Testen

Handmatig, met een reeks representatieve proces-beschrijvingen door de
Tess-chat gestuurd (bijv. "we missen leads omdat niemand snel genoeg
reageert op offerteaanvragen", "we plannen afspraken nu volledig
handmatig in"):

- Controleren dat Tess een gestructureerde diagnose teruggeeft (niet een
  vage "we plannen een gesprek in"-reactie zoals nu).
- Controleren dat de grens niet wordt overschreden — expliciet naast de
  "wat mag niet"-lijst hierboven leggen bij elk testantwoord.
- Controleren dat de overgang naar het gesprek natuurlijk/eerlijk aanvoelt,
  niet als een kunstmatige afkapping.
- Controleren dat de lead-mail naar het team de diagnose meekrijgt.

## Vervolg (buiten dit project)

- Als dit goed werkt, is een logische vervolgvraag of/hoe dit ooit uitgroeit
  naar iets voor bestaande klanten (het bredere SaaS-idee van eerder in de
  brainstorm) — expliciet niet nu, apart traject als het zover komt.
