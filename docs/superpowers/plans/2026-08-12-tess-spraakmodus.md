# Tess krijgt een stem — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Voeg spraakinvoer/-uitvoer toe aan de bestaande Tess-conciergewidget op tessar.nl, door de bestaande n8n-chatworkflow uit te breiden met een STT→(bestaande agent)→TTS-pad, zonder de bestaande tekst-chat te breken.

**Architecture:** Turn-based (opnemen → versturen → antwoord terug, geen streaming audio). De browser-widget krijgt een mic-knop die audio opneemt (`MediaRecorder`) en naar een nieuwe voice-webhook in de bestaande n8n-workflow stuurt; die workflow transcribeert (Whisper), voert de tekst door dezelfde bestaande Tess-agent/persona/sessie, zet het antwoord om naar spraak (OpenAI TTS), en stuurt transcript + tekstantwoord + audio als JSON terug.

**Tech Stack:** Vanilla JS (geen dependencies, zelfde stijl als het bestaande bestand), n8n (self-hosted op `n8n.tessar.nl`), OpenAI audio-modellen (Whisper voor STT, TTS voor spraak) via de `@n8n/n8n-nodes-langchain.openAi`-node — ongeacht welk LLM de bestaande Tess-agent gebruikt, want Anthropic heeft geen spraak-API.

## Global Constraints

- Geen telefonie/PSTN, geen telefoonnummer (uit spec).
- Geen multi-tenant SaaS — dit blijft Tessar's eigen site (uit spec).
- Geen continue/streaming audioverbinding — turn-based blijft de aanpak (uit spec).
- Geen nieuwe database/CRM, geen facturatie-wijzigingen (uit spec).
- Geen wijziging aan bestaand tekst-chatgedrag van Tess buiten het toevoegen van de mic-knop (uit spec).
- Geen ruwe audio bewaren na transcriptie — alleen tekst-transcriptie en antwoord blijven bewaard (uit spec, AVG).
- Mic-knop moet zichzelf stil verbergen bij ontbrekende `MediaRecorder`-steun of geweigerde microfoon-toestemming — widget blijft dan gewoon tekst-only werken (uit spec).
- Dezelfde sessie-berichtenlimiet (`maxMessagesPerSession`) telt spraakbeurten mee (uit spec, met heroverweging van de waarde in Task 5).
- Volg de bestaande codestijl van `tessar-concierge-widget.js`: zelfstandige IIFE, geen build-stap, geen frameworks, Nederlandstalige UI-teksten en commentaar.

---

## Voorbereiding: n8n-toegang

Taken 1 en 2 gebeuren in de n8n-webinterface op `https://n8n.tessar.nl`, niet in deze repo. Dit vereist een ingelogde sessie in die n8n-instance (in de browser van wie dit plan uitvoert). Als er geen toegang is, geef dat expliciet aan voordat je aan Task 1 begint — de rest van het plan is daarvan afhankelijk.

---

### Task 1: Bestaande Tess-workflow exporteren en documenteren

**Doel:** een vastgelegde baseline van de huidige productie-workflow (rollback-punt) en de feiten die Task 2 nodig heeft — welk LLM-node, en welk veld de sessie/memory-key voedt.

**Files:**
- Create: `n8n-workflows/tessar-concierge-chat.json` (export van de huidige workflow, zelfde patroon als het al gecommitte `n8n-workflows/tessar-content-brief-generator.json`)
- Create: `docs/superpowers/plans/2026-08-12-tess-spraakmodus-notes.md` (bevindingen uit deze task, input voor Task 2)

**Interfaces:**
- Produces: de exacte node-naam en het veld dat de sessie/memory-key van de agent voedt (bijv. `{{ $json.body.sessionId }}`) — Task 2 moet de nieuwe voice-flow op exact datzelfde veld laten uitkomen, anders delen tekst- en spraakbeurten geen sessiecontext.
- Produces: het model/de credentials-node die de bestaande agent als taalmodel gebruikt (om te bevestigen dat dit los staat van de nieuwe STT/TTS-nodes).

- [ ] **Stap 1: Log in op `https://n8n.tessar.nl` en open de workflow achter de Tess-chat-webhook**

De huidige productie-webhook-URL staat in `tessar-concierge-widget.js` regel 29
(`CONFIG.webhookUrl`). Zoek in n8n naar de workflow met een webhook-trigger
waarvan het pad overeenkomt met die URL.

- [ ] **Stap 2: Noteer de agent-configuratie**

Open de node die de chat-response genereert (het LangChain Agent-node, of
gelijkwaardig). Schrijf in `docs/superpowers/plans/2026-08-12-tess-spraakmodus-notes.md`:
- De naam en het type van het taalmodel-node (bijv. Anthropic Chat Model,
  welk model).
- Het exacte veld/expressie dat de memory/session-key voedt (bijv.
  `{{ $json.body.sessionId }}` op de Memory-node).
- Of er al een guardrail-/moderation-node in de flow zit.

- [ ] **Stap 3: Exporteer de workflow als JSON**

In n8n: workflow openen → "..." menu → "Download". Sla het resulterende
bestand op als `n8n-workflows/tessar-concierge-chat.json` in deze repo
(vervang credential-ID's niet handmatig — n8n exporteert die al als
neutrale placeholders, zoals te zien in het bestaande
`tessar-content-brief-generator.json`).

- [ ] **Stap 4: Commit**

```bash
git add n8n-workflows/tessar-concierge-chat.json docs/superpowers/plans/2026-08-12-tess-spraakmodus-notes.md
git commit -m "Baseline-export van de bestaande Tess-chatworkflow + bevindingen voor spraakmodus"
```

---

### Task 2: STT→agent→TTS-pad toevoegen aan de n8n-workflow

**Doel:** een nieuwe webhook-trigger die audio ontvangt, transcribeert, door
dezelfde bestaande agent stuurt, en een gesproken antwoord teruggeeft als
JSON (transcript + tekstantwoord + base64-audio) — zonder de bestaande
tekst-chat-trigger of -flow aan te raken.

**Files:**
- Modify: `n8n-workflows/tessar-concierge-chat.json` (bijgewerkte export ná de
  wijzigingen in de n8n-UI)

**Interfaces:**
- Consumes: de agent-node en memory-sessionKey-expressie gedocumenteerd in
  Task 1's notes.
- Produces: de productie-URL van de nieuwe voice-webhook (vorm
  `https://n8n.tessar.nl/webhook/<id>/voice`) — Task 4 heeft deze exacte URL
  nodig voor `CONFIG.voiceWebhookUrl`.
- Produces: het JSON-responseformaat
  `{ "transcript": string, "output": string, "audioBase64": string, "mimeType": "audio/mpeg" }`
  — Task 4's fetch-afhandeling verwacht precies deze drie velden.

- [ ] **Stap 1: Nieuwe Webhook-trigger node toevoegen**

Node-type `n8n-nodes-base.webhook`. Parameters:
- `httpMethod`: `POST`
- `path`: `voice` (custom pad, zodat de URL voorspelbaar
  `https://n8n.tessar.nl/webhook/voice` wordt in plaats van een
  auto-gegenereerde UUID — makkelijker te documenteren en te onthouden)
- `responseMode`: `responseNode`
- Verwacht binnenkomende body: `multipart/form-data` met een veld `audio`
  (de opname als blob) en velden `sessionId` en `clientId` (zelfde namen als
  de bestaande tekst-chat-payload stuurt, zie `tessar-concierge-widget.js`
  regel 411-416).

- [ ] **Stap 2: STT-node toevoegen (Whisper)**

Node-type `@n8n/n8n-nodes-langchain.openAi`, parameters:
- `resource`: `audio`
- `operation`: `transcribe`
- `binaryPropertyName`: `audio` (moet overeenkomen met het binaire veld dat
  de Webhook-node doorgeeft)
- Extra optie/parameter voor taal: `nl` (Whisper accepteert een
  `language`-hint; zet die op `nl` voor betere transcriptienauwkeurigheid
  van Nederlandse spraak)
- Credentials: hergebruik de bestaande OpenAI-credential in deze n8n-instance
  (zelfde patroon als het gedownloade referentie-template gebruikt voor zijn
  "Generate text (STT)"-node).

Verbind: Webhook → STT-node.

- [ ] **Stap 3: STT-output doorsturen naar de bestaande agent-node**

Gebruik de agent-node die in Task 1 gedocumenteerd is. Zorg dat:
- De tekst-input van de agent de STT-transcriptie is (`{{ $json.text }}` of
  het equivalente output-veld van de STT-node — controleer de exacte
  veldnaam in de node-output na een testrun).
- De memory/session-key-expressie exact hetzelfde veld gebruikt als Task 1
  documenteerde, maar nu wijzend naar het inkomende webhook-body-veld
  `sessionId` van déze nieuwe trigger (bijv.
  `{{ $('Webhook - voice').item.json.body.sessionId }}`) — dit is de stap
  die tekst- en spraakgesprekken dezelfde sessiecontext laat delen.

Verbind: STT-node → bestaande agent-node (niet de bestaande tekst-webhook
aanraken; de agent-node krijgt nu twee inkomende paden, één per trigger).

- [ ] **Stap 4: TTS-node toevoegen**

Node-type `@n8n/n8n-nodes-langchain.openAi`, parameters:
- `resource`: `audio`
- `operation`: `speech` (of de exacte operatienaam voor spraak-generatie in
  de huidige node-versie — controleer in de node-UI; het referentie-template
  gebruikt hiervoor dezelfde node met `resource: audio` en een `voice`-optie)
- `voice`: `onyx` (zelfde stem als het referentie-template; multilingual,
  volgt automatisch de taal van de invoertekst)
- `input`: `{{ $json.output }}` (het tekstantwoord van de agent-node)
- Credentials: zelfde OpenAI-credential als de STT-node.

Verbind: agent-node → TTS-node.

- [ ] **Stap 5: Audio omzetten naar base64 voor een JSON-response**

Voeg een `n8n-nodes-base.extractFromFile`-node toe na de TTS-node, met
operatie "Binary naar Property" (base64-encodeert het binaire audioveld naar
een JSON-stringveld, bijv. `data`). Controleer de exacte node-naam/operatie
in de huidige n8n-versie — als "Extract from File" niet beschikbaar is,
gebruik een Code-node met
`return [{ json: { audioBase64: $input.first().binary.data.data } }]`
(n8n bewaart binaire data intern al als base64-string; dit ontsluit 'm als
gewoon JSON-veld).

- [ ] **Stap 6: Response samenstellen**

Voeg een `n8n-nodes-base.set`-node (Edit Fields) toe die drie velden
samenvoegt tot één JSON-object:
- `transcript`: `{{ $('STT-node-naam').item.json.text }}`
- `output`: `{{ $('agent-node-naam').item.json.output }}`
- `audioBase64`: `{{ $json.audioBase64 }}` (of het veldnaam uit Stap 5)
- `mimeType`: vaste waarde `audio/mpeg`

Verbind naar een `n8n-nodes-base.respondToWebhook`-node met `respondWith`:
`json`.

- [ ] **Stap 7: Testen in n8n**

Gebruik n8n's "Test workflow"-knop met een handmatig geüploade
Nederlandstalige audio-testfile (bijv. een kort opgenomen memo "Wat kost een
traject?"). Controleer in de execution-log:
- STT-node geeft een correcte Nederlandse transcriptie.
- De agent-node reageert inhoudelijk zoals de bestaande tekst-chat dat ook
  zou doen (test dezelfde vraag eventueel ook via de bestaande tekst-widget
  ter vergelijking).
- De uiteindelijke JSON-response bevat alle vier de velden
  (`transcript`, `output`, `audioBase64`, `mimeType`) en `audioBase64` is een
  niet-lege string.

- [ ] **Stap 8: Workflow activeren en exporteren**

Zet de workflow op actief (als dat nog niet zo was — de bestaande
tekst-chat-trigger blijft ongewijzigd actief). Download de bijgewerkte
workflow-JSON en overschrijf `n8n-workflows/tessar-concierge-chat.json`.
Noteer de definitieve productie-URL van de voice-webhook (uit de
Webhook-node, "Production URL") in
`docs/superpowers/plans/2026-08-12-tess-spraakmodus-notes.md` — Task 4 heeft
die letterlijk nodig.

- [ ] **Stap 9: Commit**

```bash
git add n8n-workflows/tessar-concierge-chat.json docs/superpowers/plans/2026-08-12-tess-spraakmodus-notes.md
git commit -m "n8n: STT/agent/TTS-pad + voice-webhook toegevoegd aan Tess-workflow"
```

---

### Task 3: Capability-detectie en mic-knop UI-skelet

**Doel:** de mic-knop verschijnt naast de verstuurknop, alleen in browsers
die opname ondersteunen — nog zonder daadwerkelijk op te nemen of iets te
versturen. Dit ontkoppelt het "zichzelf stil verbergen"-gedrag (spec-eis) van
de rest van de opname-logica, zodat het apart te verifiëren is.

**Files:**
- Modify: `tessar-concierge-widget.js`

**Interfaces:**
- Produces: `micSupported` (boolean, module-scope var) — Task 4 gebruikt deze
  om te bepalen of opname-event-listeners überhaupt worden aangesloten.
- Produces: DOM-element `micBtn` (via `panel.querySelector("[data-tsc-mic]")`)
  — Task 4 hangt hier de click-handler aan.

- [ ] **Stap 1: CSS voor de mic-knop toevoegen**

Voeg toe aan de bestaande `css`-string (na regel 105, na de
`.tsc-send:disabled`-regel):

```js
    + ".tsc-mic{background:oklch(96% 0.015 220);border:1px solid oklch(88% 0.03 220);color:oklch(30% 0.05 240);"
    + "width:40px;border-radius:10px;cursor:pointer;flex:none;display:flex;align-items:center;justify-content:center;"
    + "transition:background 150ms ease, border-color 150ms ease;}"
    + ".tsc-mic:hover{background:oklch(92% 0.03 220);}"
    + ".tsc-mic.tsc-recording{background:oklch(60% 0.2 25);border-color:oklch(60% 0.2 25);color:#fff;"
    + "animation:tsc-pulse 1.4s infinite ease-in-out;}"
    + "@keyframes tsc-pulse{0%,100%{box-shadow:0 0 0 0 oklch(60% 0.2 25 / 0.5);}50%{box-shadow:0 0 0 8px oklch(60% 0.2 25 / 0);}}"
    + ".tsc-mic-hint{font-size:0.6875rem;color:oklch(55% 0.02 250);padding:0 12px 8px;flex:none;}"
```

- [ ] **Stap 2: Mic-knop en privacy-hint toevoegen aan de panel-HTML**

Wijzig het `panel.innerHTML`-blok (regel 148-169). Vervang de
`tsc-inputrow`-div zodat de mic-knop vóór de verstuurknop staat, en voeg de
privacy-hint toe direct erboven:

```js
    '<div class="tsc-mic-hint" data-tsc-mic-hint style="display:none">Je spraak wordt alleen gebruikt om je vraag te beantwoorden, niet opgeslagen.</div>' +
    '<div class="tsc-inputrow">' +
      '<textarea class="tsc-input" rows="1" data-tsc-input placeholder="' + CONFIG.inputPlaceholder + '"></textarea>' +
      '<button class="tsc-mic" type="button" data-tsc-mic aria-label="Spreek je vraag in" style="display:none">' +
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/></svg>' +
      '</button>' +
      '<button class="tsc-send" type="button" data-tsc-send aria-label="Versturen">' +
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z"/></svg>' +
      '</button>' +
    '</div>';
```

- [ ] **Stap 3: Capability-detectie en zichtbaarheid koppelen**

Voeg toe direct na de bestaande DOM-lookups (na regel 180,
`var closeBtn = ...`):

```js
  var micBtn = panel.querySelector("[data-tsc-mic]");
  var micHintEl = panel.querySelector("[data-tsc-mic-hint]");
  var micSupported = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
  if (micSupported) {
    micBtn.style.display = "";
    micHintEl.style.display = "";
  }
```

- [ ] **Stap 4: Handmatig verifiëren**

Open `chatbots.html` lokaal in een browser die `MediaRecorder` ondersteunt
(recente Chrome/Firefox/Edge/Safari) → open het Tess-paneel → de mic-knop en
de privacy-hint moeten zichtbaar zijn naast de verstuurknop. Simuleer
niet-ondersteund door in de devtools-console vóór het laden van het script
`window.MediaRecorder = undefined;` uit te voeren en de pagina te herladen
met het script als losse `<script>`-tag (of tijdelijk `micSupported = false`
hardcoderen) → mic-knop en hint moeten dan verborgen blijven en de widget
moet verder normaal (tekst-only) werken.

- [ ] **Stap 5: Commit**

```bash
git add tessar-concierge-widget.js
git commit -m "Mic-knop UI-skelet + capability-detectie voor Tess-spraakmodus"
```

---

### Task 4: Opnemen, versturen en antwoord afspelen

**Doel:** de mic-knop neemt daadwerkelijk audio op, stuurt die naar de
voice-webhook uit Task 2, toont het transcript + tekstantwoord als bubbels
(zelfde als tekst-chat), en biedt een afspeelknop voor het gesproken
antwoord.

**Files:**
- Modify: `tessar-concierge-widget.js`

**Interfaces:**
- Consumes: `micBtn`, `micSupported` (Task 3).
- Consumes: `addMessage(role, text)`, `showTyping()`, `getMessageCount()`,
  `incrementMessageCount()`, `sessionId`, `CONFIG.maxMessagesPerSession`
  (bestaande functies/vars, ongewijzigd).
- Consumes: de productie-voice-webhook-URL uit Task 2 (regel 29-gebied,
  nieuw `CONFIG.voiceWebhookUrl`-veld).
- Produces: `sendVoiceMessage(audioBlob)` — geen andere task hangt hiervan
  af, maar het is de tegenhanger van de bestaande `sendMessage(text)`.

- [ ] **Stap 1: `voiceWebhookUrl` toevoegen aan CONFIG**

Wijzig het `CONFIG`-object (na regel 29, na `webhookUrl`):

```js
    voiceWebhookUrl: "https://n8n.tessar.nl/webhook/voice",
```

Vervang de placeholder-URL door de echte productie-URL zodra Task 2 die
oplevert (zelfde werkwijze als destijds bij `webhookUrl` — zie de
commit-geschiedenis van dit bestand: "Echte n8n-webhook-URL invullen voor de
Tess-concierge-widget").

- [ ] **Stap 2: Opname-state en recorder-logica toevoegen**

Voeg toe na de bestaande `getMessageCount`/`incrementMessageCount`-functies
(na regel 382, vóór `async function sendMessage`):

```js
  // ----------------------- SPRAAKOPNAME -----------------------
  var mediaRecorder = null;
  var recordedChunks = [];
  var isRecording = false;

  function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      recordedChunks = [];
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.addEventListener("dataavailable", function (e) {
        if (e.data && e.data.size > 0) recordedChunks.push(e.data);
      });
      mediaRecorder.addEventListener("stop", function () {
        stream.getTracks().forEach(function (t) { t.stop(); });
        // Gebruik het daadwerkelijke mimeType van de recorder i.p.v. een vaste
        // waarde: Chrome/Firefox nemen doorgaans audio/webm, Safari doorgaans
        // audio/mp4 - een verkeerd gelabelde Blob kan de STT-stap laten falen.
        var mimeType = mediaRecorder.mimeType || "audio/webm";
        var blob = new Blob(recordedChunks, { type: mimeType });
        if (blob.size < 1000) return; // te kort/leeg, niets versturen
        sendVoiceMessage(blob, mimeType);
      });
      mediaRecorder.start();
      isRecording = true;
      micBtn.classList.add("tsc-recording");
    }).catch(function (err) {
      console.warn("[Tessar concierge] microfoon-toestemming geweigerd of mislukt:", err);
    });
  }

  function stopRecording() {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
    }
    isRecording = false;
    micBtn.classList.remove("tsc-recording");
  }

  if (micSupported) {
    micBtn.addEventListener("click", function () {
      if (isRecording) {
        stopRecording();
      } else {
        startRecording();
      }
    });
  }
```

- [ ] **Stap 3: `sendVoiceMessage` toevoegen**

Voeg toe direct na de bestaande `async function sendMessage(text) { ... }`
(na regel 455, vóór de `sendBtn.addEventListener`-regel):

```js
  async function sendVoiceMessage(audioBlob, mimeType) {
    if (getMessageCount() >= CONFIG.maxMessagesPerSession) {
      addMessage("bot", CONFIG.limitReachedMessage);
      return;
    }
    incrementMessageCount();
    hasSentFirstMessage = true;
    startersEl.style.display = "none";

    var typingEl = showTyping();

    try {
      // Bestandsextensie afleiden van het echte mimeType (bv. "audio/webm;codecs=opus"
      // -> "webm"), zodat de bestandsnaam overeenkomt met de daadwerkelijke inhoud.
      var extMatch = /audio\/([a-z0-9]+)/i.exec(mimeType || "");
      var ext = extMatch ? extMatch[1] : "webm";
      var formData = new FormData();
      formData.append("audio", audioBlob, "opname." + ext);
      formData.append("sessionId", sessionId);
      formData.append("clientId", CONFIG.clientId);

      var res = await fetch(CONFIG.voiceWebhookUrl, { method: "POST", body: formData });
      if (!res.ok) throw new Error("HTTP " + res.status);

      var data = await res.json();
      typingEl.remove();

      if (data.transcript) addMessage("user", data.transcript);
      var botMsgEl = addMessage("bot", data.output || "Sorry, daar ging iets mis.");

      if (data.audioBase64) {
        var audioEl = document.createElement("audio");
        audioEl.controls = true;
        audioEl.style.marginTop = "8px";
        audioEl.style.maxWidth = "100%";
        audioEl.src = "data:" + (data.mimeType || "audio/mpeg") + ";base64," + data.audioBase64;
        botMsgEl.appendChild(audioEl);
      }
    } catch (err) {
      typingEl.remove();
      addMessage("bot", "Er ging iets mis bij het verwerken van je spraakbericht. Probeer het later opnieuw, of typ je vraag.");
      console.error("[Tessar concierge] fout bij verwerken spraakbericht:", err);
    }
  }
```

- [ ] **Stap 4: Handmatig end-to-end verifiëren**

Op een preview-omgeving (niet direct tegen productie): open het Tess-paneel,
klik de mic-knop, geef microfoon-toestemming, spreek een vraag in
(bijv. "Wat kost een traject?"), klik nogmaals om te stoppen. Verwacht:
typing-indicator → een tekstbubbel met het transcript als gebruikersbericht →
een tekstbubbel met het antwoord → een afspeelbaar audio-element eronder.
Klik play en controleer dat het antwoord verstaanbaar Nederlands is.

- [ ] **Stap 5: Commit**

```bash
git add tessar-concierge-widget.js
git commit -m "Opname, versturen en afspelen van spraakantwoorden in Tess-widget"
```

---

### Task 5: Foutafhandeling, rate-limit heroverweging en privacy-polish

**Doel:** de resterende spec-eisen die nog niet door Taken 3-4 gedekt zijn:
expliciete lege-opname-guard (al gedaan in Task 4 stap 2, hier verifiëren),
heroverweging van `maxMessagesPerSession` voor spraak, en een korte
eindcontrole dat er geen ruwe audio ergens onnodig blijft hangen.

**Files:**
- Modify: `tessar-concierge-widget.js`

**Interfaces:**
- Consumes: alles uit Taken 3-4.

- [ ] **Stap 1: Rate-limit heroverwegen**

Spraakbeurten kosten meer (STT + TTS bovenop het LLM-antwoord) dan
tekstberichten. Beoordeel `CONFIG.maxMessagesPerSession` (nu `5`, regel 55):
blijft dit staan, of wordt het verlaagd specifiek voor spraak? Als een apart,
lager plafond voor spraak gewenst is, voeg toe:

```js
    maxVoiceMessagesPerSession: 3,
```

en gebruik dat in `sendVoiceMessage`'s limiet-check (Task 4 stap 3) in
plaats van `CONFIG.maxMessagesPerSession`. Documenteer de gekozen waarde met
een kort commentaar (zelfde stijl als het bestaande commentaar bij
`maxMessagesPerSession`, regel 49-54) over waarom (kostenbeheersing).

- [ ] **Stap 2: Bevestigen dat er geen audio client-side blijft hangen**

Controleer `sendVoiceMessage` (Task 4 stap 3): `recordedChunks` wordt bij
elke nieuwe opname gereset (`startRecording`, Task 4 stap 2), en de
verstuurde `Blob` wordt nergens in een variabele buiten de functiescope
bewaard. Aan de n8n-kant (Task 2): controleer dat er geen node in de
workflow het binaire audioveld naar een bestand/database schrijft — alleen
transcript en tekstantwoord passeren de Set-node in Stap 6 van Task 2. Als er
wél een audio-loggingnode blijkt te bestaan, verwijder die.

- [ ] **Stap 3: Handmatig verifiëren van foutpaden**

- Weiger microfoon-toestemming in de browser → console-warning verschijnt,
  geen crash, widget blijft bruikbaar.
- Zet `CONFIG.voiceWebhookUrl` tijdelijk op een niet-bestaande URL, verstuur
  een spraakbericht → de nette foutbubbel verschijnt ("Er ging iets mis bij
  het verwerken van je spraakbericht...").
- Zet 'm terug op de echte URL na de test.
- Klik de mic-knop aan en direct weer uit (opname <1 seconde) → er wordt
  niets verstuurd (geen typing-indicator, geen netwerkverzoek in de
  devtools Network-tab).

- [ ] **Stap 4: Commit**

```bash
git add tessar-concierge-widget.js
git commit -m "Rate-limit voor spraak, audio-privacy-verificatie, foutpaden getest"
```

---

### Task 6: Volledige QA-checklist en oplevering

**Doel:** de spec's testsectie als geheel afvinken op een preview-omgeving
vóór (eventuele) productie-deploy, en de spec-notes/plan-notes opruimen.

**Files:**
- Modify: `docs/superpowers/plans/2026-08-12-tess-spraakmodus-notes.md`
  (afvinken/afronden)

- [ ] **Stap 1: Volledige checklist doorlopen op een preview-omgeving**

- [ ] Mic-toestemming: eerste keer klikken vraagt netjes toestemming.
- [ ] Opname → versturen → transcript-bubbel → antwoord-bubbel → afspeelbare
      audio, in die volgorde.
- [ ] Sessie-continuïteit: stel een tekstvraag, beantwoord die, stel
      daarna een vervolgvraag via spraak die verwijst naar het eerdere
      antwoord ("en hoe lang duurt dat dan?") — de agent moet de context
      begrijpen zonder dat je het onderwerp opnieuw benoemt.
- [ ] Berichtenlimiet: bereik het spraak- of totaalplafond (afhankelijk van
      de Task 5-keuze) → `limitReachedMessage` verschijnt, geen nieuw
      verzoek wordt gestuurd.
- [ ] Fallback: in een browser/context zonder `MediaRecorder`-steun blijft
      de widget volledig tekst-only bruikbaar, geen zichtbare mic-knop.
- [ ] Mobiel (klein scherm): mic-knop blijft binnen de bestaande
      `@media (max-width:480px)`-aanpassing van het paneel bruikbaar.

- [ ] **Stap 2: Notities afronden en committen**

Werk `docs/superpowers/plans/2026-08-12-tess-spraakmodus-notes.md` bij met
de definitieve gekozen waarden (rate-limit, TTS-stem, evt. afwijkingen van
dit plan die tijdens uitvoering nodig bleken) zodat een toekomstige lezer
niet opnieuw hoeft te ontdekken wat er precies gebouwd is.

```bash
git add docs/superpowers/plans/2026-08-12-tess-spraakmodus-notes.md
git commit -m "QA-checklist tess-spraakmodus afgerond, notities bijgewerkt"
```

- [ ] **Stap 3: Niet automatisch deployen**

Deze wijzigingen raken de live productie-widget van tessar.nl. Vraag
expliciet aan de gebruiker of/wanneer dit naar `origin/main` gepusht mag
worden — niet zelfstandig pushen, zelfde werkwijze als eerdere wijzigingen
aan deze site (zie `contact-page-nav-fix` in het geheugen).
