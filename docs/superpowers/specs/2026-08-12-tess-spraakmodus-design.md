# Tess krijgt een stem — ontwerp

> **Status: AFGEBLAZEN.** Dit ontwerp is nooit uitgevoerd — het vereiste een STT/TTS-stap
> via een niet-Anthropic partij (OpenAI), wat botst met de staande eis dat Tessar's
> AI-productwerk uitsluitend via Claude/Anthropic loopt. Zie in plaats daarvan
> `docs/superpowers/specs/2026-08-12-tess-automatiseringsdiagnose-design.md` voor het
> project dat wél is gebouwd en live staat. Dit document blijft staan als historisch
> ontwerp-/discovery-materiaal.

**Datum:** 2026-08-12
**Status:** ontwerp goedgekeurd, wacht op review van deze spec

## Achtergrond & aanleiding

Vertrekpunt van dit gesprek was de vraag of Tessar een systeem zou willen bouwen
vergelijkbaar met de LaraContact-template (een verkoopbaar multi-user CRM met
tweeweg SMS/WhatsApp/click-to-call en AI-assistentie), maar toegesneden op waar
Tessar voor staat.

Door het gesprek is de scope een aantal keer bewust versmald:

1. **Doelgroep:** Tessar's eigen klanten (verkoopbaar product), niet een intern
   tool of alleen een showcase.
2. **Productkern:** een AI-inbox/receptioniste-product (Tessar's kernservice
   productiseren), niet een generiek CRM of een zelfbedienings-workflow-platform.
3. **Levermodel:** uiteindelijk multi-tenant SaaS met zelfregistratie — maar
   expliciet *niet* in één klap gebouwd. De gebruiker wilde niet groter bouwen
   dan LaraContact's eigen schaal, en wilde eerst het risicovolste/onbekendste
   stuk (kan AI een gesprek daadwerkelijk fatsoenlijk voeren?) bewijzen voordat
   er een heel SaaS-product met facturatie/multi-tenancy omheen ontworpen wordt.
4. Daarom is dit **project 1 van een reeks**: eerst een werkende AI-voice-agent
   bewijzen, de volledige unified-inbox SaaS (project 2) volgt later, apart
   ontworpen, ná dat dit werkt.
5. Voice vanaf nul (telefonie/PSTN, real-time streaming, barge-in) bleek zelf
   al LaraContact-schaal. De gebruiker had echter een n8n-communitytemplate
   ("Voice AI Chatbot with Document Retrieval & Guardrails for Wordpress")
   ingeladen die **turn-based** is (opname → webhook → antwoord terug, geen
   telefoonverbinding) — dat omzeilt de telefonie-complexiteit volledig.
6. Tijdens het ontwerp bleek Tessar al een **live, werkende tekst-AI-concierge**
   te hebben op de eigen site: "Tess" (`tessar-concierge-widget.js`, geladen op
   `chatbots.html`), die al sinds meerdere commits productie-klaar is en praat
   met een bestaande n8n-chatworkflow op `n8n.tessar.nl` (echte webhook-URL,
   sessiebeheer, streaming, berichtenlimiet, uitgewerkte persona).

Conclusie: de kleinste, meest voor-de-hand-liggende invulling van project 1 is
**spraak toevoegen aan de bestaande Tess-widget**, niet een nieuwe losse widget
bouwen met een eigen kennisbank. Het gedownloade template dient puur als
technische referentie voor de STT→LLM→TTS-vorm.

## Scope van dit project

**Wel:**
- Een mic-knop in het bestaande Tess-paneel op `chatbots.html` (en waar de
  widget verder geladen wordt).
- Opname van een spraakvraag, versturen naar een nieuwe voice-webhook,
  transcriptie, antwoord via dezelfde bestaande Tess-agent/persona/sessie,
  gesproken antwoord terug.
- Uitbreiding van de bestaande n8n-workflow achter Tess met een STT- en
  TTS-stap, zonder de bestaande tekst-chat-flow te breken.

**Expliciet niet:**
- Telefonie/PSTN, geen telefoonnummer om te bellen.
- Multi-tenant SaaS — dit blijft Tessar's eigen site, geen oplevering aan
  andere klanten.
- Continue/streaming audioverbinding — turn-based (opnemen → versturen →
  antwoord) blijft de aanpak, geen live duplex gesprek.
- Nieuwe database/CRM, facturatie-wijzigingen, of wijzigingen aan het
  bestaande tekst-chatgedrag van Tess buiten het toevoegen van de mic-knop.
- Project 2 (de volledige unified-inbox SaaS) — apart traject, later.

## Architectuur & dataflow

Geen nieuwe backend-service: één extra pad door de bestaande n8n-workflow
achter Tess, plus een nieuwe audio-laag in `tessar-concierge-widget.js`.

```
Browser (Tess-paneel)
  ├─ bestaand: tekst-input → chat-webhook → (streaming tekst terug)
  └─ nieuw:   mic-knop → opname (MediaRecorder) → voice-webhook
                                                      │
                                              n8n: STT (Whisper, nl)
                                                      │
                                        dezelfde Tess-agent/persona/sessie
                                        (hergebruikt bestaande memory-key
                                         zodat tekst- en spraakbeurten
                                         binnen 1 sessie context delen)
                                                      │
                                              n8n: TTS (nl-stem)
                                                      │
                                         audio terug → afspelen in paneel
                                         (+ transcript als tekstbubbel,
                                          zodat het gesprek terug te lezen
                                          is zoals nu al met tekst kan)
```

Turn-based, net als het geraadpleegde template: opnemen → versturen → antwoord
terug, geen continue streaming-verbinding. STT/TTS gebruiken OpenAI's
audiomodellen (Whisper/TTS), ongeacht welk LLM de bestaande Tess-agent
gebruikt — Anthropic heeft geen spraak-API, dus dat stuk staat los van de
vraag welk taalmodel Tess al gebruikt.

**Te verifiëren tijdens de bouw (niet aangenomen in dit ontwerp):**
- Welk LLM-node de bestaande Tess-workflow gebruikt (vermoedelijk Claude via
  de Anthropic-node, zoals bij de content-brief-workflow, maar niet
  geverifieerd — de workflow-JSON staat niet in deze repo, alleen in de
  n8n-instance zelf).
- Wat de bestaande workflow al wel/niet logt/bewaart van tekstberichten, zodat
  de nieuwe voice-stap niet meer bewaart dan de bestaande tekst-flow al doet.

## UI, interactie

- Mic-knop naast de bestaande verstuur-knop in de inputrow van het Tess-paneel.
- Klik = opnemen (visuele "luister"-status); nogmaals klikken of automatisch
  stoppen na stilte = versturen.
- Tijdens verwerking: hergebruik de bestaande typing-indicator.
- Antwoord: tekstbubbel zoals nu (leesbaar/terug te scrollen) plus een inline
  afspeelknop voor het gesproken antwoord. Niet automatisch hardop afspelen
  zonder dat de bezoeker het aanzet.
- Dezelfde sessie-berichtenlimiet (`maxMessagesPerSession`, nu 5) telt
  spraakbeurten mee. Bij de bouw kort heroverwegen of dat te ruim/krap is,
  aangezien spraak (STT+TTS) duurder is per beurt dan tekst alleen.

## Foutafhandeling

- Geen microfoon-toestemming of geen `MediaRecorder`-steun (bv. oudere
  Safari): mic-knop verbergt zichzelf stil, widget blijft gewoon tekst-only
  werken. Geen kapotte knop, geen onoplosbare foutmelding.
- STT/TTS-call mislukt: zelfde soort nette fallback als de bestaande `catch`
  in `sendMessage()` ("Er ging iets mis..., probeer het later opnieuw"), geen
  stille silent failure.
- Lege/te korte opname (bv. per ongeluk geklikt): niets versturen, geen loze
  n8n-aanroep.

## Privacy (AVG)

Een stem opnemen is gevoeliger dan getypte tekst — dat verdient een expliciete
melding, ook zonder aparte toestemmingsdialoog:

- Kort, zichtbaar tekstje bij de mic-knop (eerste gebruik): "Je spraak wordt
  alleen gebruikt om je vraag te beantwoorden, niet opgeslagen."
- Ontwerpregel: **geen ruwe audio bewaren** na transcriptie — alleen de
  tekst-transcriptie en het antwoord blijven, net als nu al met tekstberichten
  gebeurt. Bij de bouw afchecken tegen wat de bestaande workflow al wel/niet
  logt (zie open punt hierboven), zodat spraak niet meer bewaart dan tekst.

## Testen

- n8n-kant: nieuwe STT→(bestaande agent)→TTS-stappen eerst los testen in de
  workflow-editor (test-executies) voordat de webhook live aan de widget
  hangt.
- Widget-kant: handmatig testen op een preview-omgeving (niet direct tegen
  productie) — mic-toestemming, opname/versturen, afspelen van het antwoord,
  sessie-continuïteit tussen een tekst- en een spraakbeurt, gedrag bij
  bereikte berichtenlimiet, en de stille fallback in een browser zonder
  `MediaRecorder`-steun.
- Geen geautomatiseerde end-to-end audiotest (microfoon/afspelen laat zich
  niet zinnig automatiseren) — wel een handmatige checklist bij de
  implementatieplan-uitwerking.

## Vervolg (buiten dit project)

- **Project 2:** de volledige unified-inbox SaaS (multi-tenant, facturatie,
  meerdere kanalen) — pas ontworpen zodra dit project bewijst wat wel/niet
  werkt.
- Eventuele latere telefonie-uitbreiding (echt bellen) zou een apart,
  vervolgtraject zijn — niet in scope hier.
