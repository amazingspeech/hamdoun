# Van Dijk Clinic — context voor protocolchecker-project

Dit document bundelt alles wat tot nu toe over Van Dijk Clinic is verzameld, plus de
oorspronkelijke vraag van Kevin B. over een AI-protocolchecker voor personeel. Bedoeld
als startcontext voor een nieuwe workflow/applicatie (bijv. in Claude Code), los van de
bestaande n8n boekingsassistent.

---

## 1. De oorspronkelijke vraag (Kevin B., telefonisch)

> "Protocollen zijn zo divers. Case: als een nieuwe werknemer bij hem komt en ze moeten
> weten hoe ze moeten bereiden van botox, of inspectie komt langs — dat ze een cloud
> hebben dat ze met een AI kunnen checken op basis van protocollen."

Kern van het idee: een systeem waarin personeel (vooral nieuwe werknemers) protocollen
kan opzoeken/checken via AI — bijvoorbeeld hoe een botoxbehandeling voor te bereiden, of
wat te doen bij een inspectiebezoek.

**Status:** dit stond on hold sinds het eerste teamoverleg, vanwege:
- EU AI Act-risico (Shanks' veto) — een systeem dat personeel instrueert over medische
  voorbereiding/uitvoering kan als hoog-risico AI gelden zodra het gezondheidsgerelateerde
  beslissingen raakt.
- Nico Robin's eis: geen livegang zonder geverifieerde, gecontroleerde brondata — de AI
  mag protocollen nooit zelf "samenvatten" zonder controle.
- Mihawk's validate-first-principe: eerst de boekingsassistent bewijzen, dan pas dit
  oppakken.

## 2. Praktijkgegevens Van Dijk Clinic

- **Naam:** Van Dijk Clinic (medisch cosmetische behandelingen)
- **Adres:** Weverssingel 7, 3811 GJ Amersfoort
- **Hoofdlijn:** 033 - 78 50 391
- **E-mail:** info@vandijkclinic.nl
- **Spoednummer:** 06 - 44 53 27 36 — uitsluitend voor koorts, heftige pijn, of
  abnormale zwelling na een behandeling (kliniek-eigen criterium)
- **Parkeren:** niet voor de deur (autoluwe binnenstad), parkeergarage De Flint,
  Walikerstraat 14
- **Taxi-service** naar de auto na een behandeling, aan te vragen bij de manager
- **Website:** vandijkclinic.nl (WordPress/Elementor)
- **Praktijkbeheersysteem:** Clinicminds — clinic-ID `ed399bdb-b1b6-11eb-90eb-02a15c8163fa`
- **Klachtenprocedure:** via Klachtenportaal Zorg (externe, onafhankelijke organisatie)

## 3. Officiële behandelingenlijst (uit de Clinicminds-boekingswidget)

- Algemeen advies gesprek (consult)
- Botox Toxine type A (botox)
- Botuline Toxine type A herhaalbehandeling (bestaande cliënten)
- Hyaluronzuur filler
- Hyaluronzuur filler herhaalbehandeling (bestaande cliënten)
- Oplossen hyaluronzuur filler
- Philart — collageen en elastine skinbooster
- Aptos Threading — Draadlift
- Lipofilling (behandeling met eigen vet)
- Lipolaser (1 kleine zone) (onderkin)
- Ooglidcorrectie — boven
- Ooglidcorrectie boven inclusief chirurgische wenkbrauwlift
- Ooglidcorrectie (onder)
- PRP behandeling
- TCA peeling
- Schaamlipcorrectie (binnenste)
- Microneedling
- Complicatie spreekuur inclusief echo begeleiding

## 4. Clinicminds — technische aansluiting

- Clinicminds heeft een **Triggers & Actions API** (HTTP/JSON, webhooks), los van hun
  Zapier-integratie. Bereikbaar via: **Menu > App settings > Integrations** in het
  Clinicminds-account van de kliniek — zelf te activeren, geen support-ticket nodig.
- Relevante triggers: nieuwe boeking, boeking geannuleerd, **no-show geregistreerd**,
  status → "occurred", nieuwe patiënt aangemaakt.
- Clinicminds heeft daarnaast een **ingebouwde QMS-module (Quality Management System)**
  voor protocollen/documenten — mogelijk de plek waar de daadwerkelijke protocollen al
  gestructureerd staan, in plaats van losse Word-bestanden. **Nog te verifiëren met Kevin.**

## 5. Medische aandachtspunten (Chopper — medisch-inhoudelijke check)

Voor een protocolchecker die met behandel-gerelateerde content werkt, gelden in ieder
geval deze medische alarmsignalen als "nooit door AI zelf beoordelen, altijd escaleren":

- **Levensbedreigend (112):** ademhalingsproblemen, bewusteloosheid, hevig/onstelpbaar
  bloedverlies, ernstige allergische reactie (opzwellen keel/gezicht + ademhaling)
- **Matig spoed (kliniek-eigen spoednummer):** koorts, heftige pijn, abnormale zwelling
- **Specifiek bij filler-behandelingen — vasculaire occlusie:** plotselinge, hevige pijn
  die niet in verhouding staat tot de ingreep, huidverkleuring (wit/blauwig-paars
  wordend), of **plotselinge visusklachten** (wazig zien, minder zien) na een filler,
  vooral rond lippen, neus of tussen de wenkbrauwen. Zeldzaam maar ernstig — kan tot
  weefselschade of blindheid leiden. Telt als hetzelfde spoedniveau als 112-signalen.

Deze zelfde signalen zijn relevant voor een protocolchecker: als personeel een protocol
raadpleegt tijdens/na een behandeling en een van deze signalen beschrijft, moet het
systeem dat herkennen als "stop, escaleer" — niet als een gewone protocol-vraag.

## 6. Juridisch kader (Shanks — niet-bindend advies, geen vervanging voor een jurist)

- Verwerkersovereenkomst (VWO) nodig zodra er patiënt- of praktijkdata doorheen gaat.
- Bijzondere persoonsgegevens (gezondheidsdata) → verzwaarde AVG-eisen, mogelijk DPIA
  bij schaal.
- Sub-verwerkers (bijv. Anthropic, hostingpartij) moeten benoemd worden in de VWO.
- EU AI Act: een systeem dat personeel instrueert over medische voorbereiding/uitvoering
  moet zorgvuldig geclassificeerd worden — mogelijk hoog-risico. Dit was de reden dat
  het protocolchecker-idee eerder on hold ging; dat risico is niet verdwenen, alleen
  het project verplaatst zich nu naar een andere bouwomgeving.

## 7. Kernprincipes uit het teamoverleg (blijven gelden, ongeacht platform)

- **Validate before build** (Mihawk): eerst één ding goed bewijzen, dan pas uitbreiden.
- **Geen scope-kruip**: nieuwe features toetsen op "nodig vóór validatie of kan wachten".
- **Eerlijkheid boven enthousiasme**: geen overdreven claims over wat het systeem kan.
- **Juridisch risico vroeg signaleren**, niet achteraf patchen.
- **Bewijs voor bouwen, validatie vóór opschalen.**
- **Geen AI-gegenereerde medische input zonder controle** — protocollen moeten uit een
  geverifieerde, gecontroleerde bron komen, nooit door de AI zelf "verzonnen" of vrij
  samengevat zonder brontoetsing.

---

*Dit document is een overdracht van context, geen goedgekeurde spec. Bij het opzetten
van de nieuwe workflow/applicatie gelden dezelfde teamprincipes als hierboven — met name
Shanks' en Chopper's aandachtspunten voordat dit ook maar richting een test met echte
protocollen gaat.*
