/**
 * Tessar AI Concierge - embeddable website widget
 * ---------------------------------------------------------
 * Zelfstandig script, geen dependencies. Voeg toe vlak voor </body>:
 *   <script src="./tessar-concierge-widget.js" defer></script>
 *
 * BELANGRIJK - dit moet je nog invullen voordat dit live kan:
 *   1) WEBHOOK_URL hieronder: de echte production-URL van de "Website Chat
 *      Trigger"-node in je n8n-workflow (Tessar-AI-Concierge.json).
 *      Vorm is meestal: https://<jouw-n8n-domein>/webhook/<webhookId>/chat
 *      Kijk in n8n zelf op het chatTrigger-node op de exacte URL - die hangt
 *      af van jouw instance en is niet te raden vanuit deze sessie.
 *   2) De allowedOrigins in die node moet exact het domein bevatten
 *      waarop dit script draait (nu ingesteld op
 *      https://amazingspeech.github.io - werk dat bij zodra je een eigen
 *      domein gebruikt).
 *
 * De streaming-parser hieronder gaat uit van newline-gescheiden JSON-chunks
 * (het gebruikelijke patroon voor n8n's LangChain chatTrigger in streaming-
 * modus), met een tekst-fallback als een regel geen geldige JSON is. Test dit
 * met de browser Network-tab zodra de echte webhook-URL is ingevuld, en
 * pas parseStreamChunk() aan als het werkelijke formaat afwijkt.
 */
(function () {
  "use strict";

  // ----------------------- CONFIG -----------------------
  var CONFIG = {
    webhookUrl: "https://n8n.tessar.nl/webhook/c1a2b3c4-1111-4ed4-9c97-e633ab209b8c/chat",
    clientId: "tessar",
    brandName: "Tessar",
    assistantName: "Tess",
    assistantInitial: "T",
    greetingRotation: [
      "Hoi, ik ben Tess. Vragen over AI-automatisering of AI-applicaties?",
      "Benieuwd of dit iets voor jouw bedrijf is? Vraag het me gerust.",
      "Wil je weten hoe een traject eruitziet? Ik leg het je uit."
    ],
    starterQuestions: [
      "Wat kost een traject?",
      "Is dit iets voor mijn bedrijf?",
      "Hoe lang duurt een traject?"
    ],
    inputPlaceholder: "Vraag het aan Tess...",
    panelTitle: "Tess",
    panelSubtitle: "AI-concierge bij Tessar",
    launcherLabel: "Chat met Tess van Tessar",
    greetingMessage: "Hoi, ik ben Tess — de AI-concierge van Tessar. Stel gerust een vraag, of kies een van de opties hieronder.",
    // Kostenbeheersing: maximum aantal berichten dat 1 bezoeker in 1 browsersessie
    // mag versturen (telt door na een pagina-refresh, via sessionStorage, zolang
    // dezelfde tab/sessie openstaat). Dit is een client-side softcap - iemand die
    // echt wil, kan 'm omzeilen door sessionStorage te wissen of de webhook direct
    // aan te roepen. De echte backstop hoort op edge-niveau (zie opmerking bij
    // CONFIG.webhookUrl hierboven) en/of een spend-limit in de Anthropic Console.
    maxMessagesPerSession: 5,
    limitReachedMessage: "Ik denk dat ik je al goed op weg kan helpen, en het scherpste vervolg is nu een gratis kennismaking van 30 minuten — daar bespreken we jouw situatie echt concreet. Plan die hierboven in, of mail ons via het contactformulier onderaan de pagina."
  };

  // ----------------------- STYLES -----------------------
  var css = ""
    + ".tsc-root{position:fixed;bottom:24px;right:24px;z-index:2147483000;font-family:'IBM Plex Sans',-apple-system,'Segoe UI',sans-serif;}"
    + ".tsc-launcher{width:60px;height:60px;border-radius:50%;border:none;cursor:pointer;"
    + "background:linear-gradient(135deg, oklch(70% 0.14 220), oklch(60% 0.15 170));"
    + "box-shadow:0 10px 30px -8px oklch(18% 0.02 255 / 0.45);display:flex;align-items:center;justify-content:center;"
    + "transition:transform 180ms ease, box-shadow 180ms ease;}"
    + ".tsc-launcher:hover{transform:translateY(-2px) scale(1.03);box-shadow:0 14px 34px -8px oklch(18% 0.02 255 / 0.55);}"
    + ".tsc-launcher svg{width:26px;height:26px;fill:#fff;}"
    + ".tsc-bubble-hint{position:absolute;bottom:70px;right:0;max-width:230px;background:oklch(18% 0.02 255);color:#fff;"
    + "padding:10px 14px;border-radius:12px 12px 4px 12px;font-size:0.8125rem;line-height:1.4;box-shadow:0 8px 24px rgba(0,0,0,0.25);"
    + "opacity:0;transform:translateY(6px);transition:opacity 320ms ease, transform 320ms ease;pointer-events:none;}"
    + ".tsc-bubble-hint.tsc-show{opacity:1;transform:translateY(0);}"
    + ".tsc-panel{position:fixed;bottom:24px;right:24px;width:380px;max-width:calc(100vw - 32px);height:600px;max-height:calc(100vh - 48px);"
    + "z-index:2147483000;"
    + "background:#fff;border-radius:18px;box-shadow:0 24px 64px -12px rgba(15,15,20,0.35);display:none;flex-direction:column;overflow:hidden;"
    + "border:1px solid oklch(90% 0.01 250);}"
    + ".tsc-panel.tsc-open{display:flex;}"
    + ".tsc-header{padding:18px 18px 16px;background:oklch(18% 0.02 255);color:#fff;display:flex;align-items:center;gap:12px;flex:none;cursor:grab;touch-action:none;user-select:none;}"
    + ".tsc-header.tsc-dragging{cursor:grabbing;}"
    + ".tsc-header-avatar{position:relative;width:36px;height:36px;flex:none;}"
    + ".tsc-header-avatar-circle{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg, oklch(70% 0.14 220), oklch(60% 0.15 170));"
    + "display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:0.9375rem;font-family:'IBM Plex Sans',sans-serif;}"
    + ".tsc-header-dot{position:absolute;right:-1px;bottom:-1px;width:10px;height:10px;border-radius:50%;background:oklch(70% 0.18 150);border:2px solid oklch(18% 0.02 255);flex:none;}"
    + ".tsc-header-text{flex:1;min-width:0;}"
    + ".tsc-header-title{font-weight:700;font-size:0.9375rem;letter-spacing:-0.01em;}"
    + ".tsc-header-sub{font-size:0.75rem;color:oklch(78% 0.06 250);margin-top:1px;}"
    + ".tsc-close{background:none;border:none;color:#fff;opacity:0.75;cursor:pointer;padding:4px;line-height:0;}"
    + ".tsc-close:hover{opacity:1;}"
    + ".tsc-body{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;background:oklch(98% 0.005 250);}"
    + ".tsc-msg{max-width:85%;padding:10px 13px;border-radius:14px;font-size:0.875rem;line-height:1.5;white-space:pre-wrap;word-wrap:break-word;}"
    + ".tsc-msg-bot{align-self:flex-start;background:#fff;border:1px solid oklch(92% 0.008 250);color:oklch(20% 0.02 255);border-bottom-left-radius:4px;}"
    + ".tsc-msg-bot p{margin:0 0 8px 0;}"
    + ".tsc-msg-bot p:last-child{margin-bottom:0;}"
    + ".tsc-msg-bot ul,.tsc-msg-bot ol{margin:4px 0 8px 0;padding-left:20px;}"
    + ".tsc-msg-bot li{margin:2px 0;}"
    + ".tsc-msg-bot strong{font-weight:700;}"
    + ".tsc-msg-user{align-self:flex-end;background:oklch(18% 0.02 255);color:#fff;border-bottom-right-radius:4px;}"
    + ".tsc-starters{display:flex;flex-direction:column;gap:8px;padding:0 16px 12px;flex:none;}"
    + ".tsc-starter-btn{text-align:left;background:oklch(96% 0.015 220);border:1px solid oklch(88% 0.03 220);color:oklch(30% 0.05 240);"
    + "padding:9px 12px;border-radius:10px;font-size:0.8125rem;cursor:pointer;transition:background 150ms ease;font-family:inherit;}"
    + ".tsc-starter-btn:hover{background:oklch(92% 0.03 220);}"
    + ".tsc-inputrow{display:flex;gap:8px;padding:12px;border-top:1px solid oklch(92% 0.008 250);flex:none;background:#fff;}"
    + ".tsc-input{flex:1;border:1px solid oklch(88% 0.01 250);border-radius:10px;padding:10px 12px;font-size:0.875rem;font-family:inherit;resize:none;outline:none;}"
    + ".tsc-input:focus{border-color:oklch(70% 0.14 220);}"
    + ".tsc-send{background:oklch(18% 0.02 255);border:none;color:#fff;width:40px;border-radius:10px;cursor:pointer;flex:none;display:flex;align-items:center;justify-content:center;}"
    + ".tsc-send:disabled{opacity:0.5;cursor:default;}"
    + ".tsc-typing{align-self:flex-start;display:flex;gap:4px;padding:10px 13px;}"
    + ".tsc-typing span{width:6px;height:6px;border-radius:50%;background:oklch(70% 0.02 250);animation:tsc-bounce 1.2s infinite ease-in-out;}"
    + ".tsc-typing span:nth-child(2){animation-delay:0.15s;} .tsc-typing span:nth-child(3){animation-delay:0.3s;}"
    + "@keyframes tsc-bounce{0%,80%,100%{transform:translateY(0);opacity:0.5;}40%{transform:translateY(-4px);opacity:1;}}"
    + "@media (max-width:480px){.tsc-panel{right:8px;bottom:8px;width:calc(100vw - 16px);height:calc(100vh - 90px);}.tsc-root{right:16px;bottom:16px;}}";

  var styleEl = document.createElement("style");
  styleEl.setAttribute("data-tessar-concierge", "");
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ----------------------- STATE -----------------------
  var sessionId = null;
  try {
    sessionId = sessionStorage.getItem("tsc_session_id");
    if (!sessionId) {
      sessionId = (crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + "-" + Math.random().toString(16).slice(2);
      sessionStorage.setItem("tsc_session_id", sessionId);
    }
  } catch (e) {
    sessionId = String(Date.now()) + "-" + Math.random().toString(16).slice(2);
  }

  var isOpen = false;
  var hasSentFirstMessage = false;

  // ----------------------- DOM -----------------------
  var root = document.createElement("div");
  root.className = "tsc-root";

  var launcher = document.createElement("button");
  launcher.className = "tsc-launcher";
  launcher.type = "button";
  launcher.setAttribute("aria-label", CONFIG.launcherLabel);
  launcher.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.03 2 11c0 2.4 1.05 4.57 2.77 6.19-.09.86-.44 2.16-1.4 3.6-.15.23.03.54.3.5 1.86-.27 3.32-.98 4.29-1.6 1.24.42 2.62.65 4.04.65 5.52 0 10-4.03 10-9 0-4.97-4.48-9-10-9z"/></svg>';

  var hint = document.createElement("div");
  hint.className = "tsc-bubble-hint";
  hint.textContent = CONFIG.greetingRotation[0];

  var panel = document.createElement("div");
  panel.className = "tsc-panel";
  panel.innerHTML =
    '<div class="tsc-header">' +
      '<div class="tsc-header-avatar">' +
        '<div class="tsc-header-avatar-circle">' + CONFIG.assistantInitial + '</div>' +
        '<span class="tsc-header-dot"></span>' +
      '</div>' +
      '<div class="tsc-header-text">' +
        '<div class="tsc-header-title">' + CONFIG.panelTitle + '</div>' +
        '<div class="tsc-header-sub">' + CONFIG.panelSubtitle + '</div>' +
      '</div>' +
      '<button class="tsc-close" type="button" aria-label="Sluiten">' +
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>' +
      '</button>' +
    '</div>' +
    '<div class="tsc-body" data-tsc-body></div>' +
    '<div class="tsc-starters" data-tsc-starters></div>' +
    '<div class="tsc-inputrow">' +
      '<textarea class="tsc-input" rows="1" data-tsc-input placeholder="' + CONFIG.inputPlaceholder + '"></textarea>' +
      '<button class="tsc-send" type="button" data-tsc-send aria-label="Versturen">' +
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z"/></svg>' +
      '</button>' +
    '</div>';

  root.appendChild(hint);
  root.appendChild(launcher);
  document.body.appendChild(root);
  document.body.appendChild(panel);

  var bodyEl = panel.querySelector("[data-tsc-body]");
  var startersEl = panel.querySelector("[data-tsc-starters]");
  var inputEl = panel.querySelector("[data-tsc-input]");
  var sendBtn = panel.querySelector("[data-tsc-send]");
  var closeBtn = panel.querySelector(".tsc-close");
  var headerEl = panel.querySelector(".tsc-header");

  // ----------------------- IDLE HINT ROTATION -----------------------
  var hintIndex = 0;
  var hintTimer = null;
  function showHint() {
    if (isOpen) return;
    hint.textContent = CONFIG.greetingRotation[hintIndex % CONFIG.greetingRotation.length];
    hint.classList.add("tsc-show");
    hintIndex++;
  }
  function scheduleHints() {
    setTimeout(function () {
      showHint();
      hintTimer = setInterval(function () {
        hint.classList.remove("tsc-show");
        setTimeout(showHint, 400);
      }, 7000);
    }, 1800);
  }
  scheduleHints();

  // ----------------------- STARTERS -----------------------
  function renderStarters() {
    startersEl.innerHTML = "";
    CONFIG.starterQuestions.forEach(function (q) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tsc-starter-btn";
      btn.textContent = q;
      btn.addEventListener("click", function () { sendMessage(q); });
      startersEl.appendChild(btn);
    });
  }
  renderStarters();

  // ----------------------- OPEN / CLOSE -----------------------
  function openPanel() {
    isOpen = true;
    panel.classList.add("tsc-open");
    root.style.display = "none";
    hint.classList.remove("tsc-show");
    clearInterval(hintTimer);
    if (!hasSentFirstMessage) {
      addMessage("bot", CONFIG.greetingMessage);
    }
    inputEl.focus();
  }
  function closePanel() {
    isOpen = false;
    panel.classList.remove("tsc-open");
    root.style.display = "";
  }
  launcher.addEventListener("click", function () { isOpen ? closePanel() : openPanel(); });
  closeBtn.addEventListener("click", closePanel);

  // ----------------------- SLEPEN (header als handvat) -----------------------
  // Zet het paneel bij het eerste sleepmoment om van rechts/onder-verankerd
  // naar een vaste links/boven-positie in pixels, zodat het daarna vrij
  // over het scherm te verplaatsen is. Blijft altijd binnen de viewport.
  (function enableDragging() {
    var dragging = false;
    var startX, startY, startLeft, startTop;

    function switchToLeftTopPositioning() {
      var rect = panel.getBoundingClientRect();
      panel.style.left = rect.left + "px";
      panel.style.top = rect.top + "px";
      panel.style.right = "auto";
      panel.style.bottom = "auto";
    }

    headerEl.addEventListener("pointerdown", function (e) {
      if (e.target === closeBtn || closeBtn.contains(e.target)) return;
      dragging = true;
      switchToLeftTopPositioning();
      startX = e.clientX;
      startY = e.clientY;
      startLeft = parseFloat(panel.style.left);
      startTop = parseFloat(panel.style.top);
      headerEl.classList.add("tsc-dragging");
      headerEl.setPointerCapture(e.pointerId);
    });

    headerEl.addEventListener("pointermove", function (e) {
      if (!dragging) return;
      var rect = panel.getBoundingClientRect();
      var newLeft = startLeft + (e.clientX - startX);
      var newTop = startTop + (e.clientY - startY);
      newLeft = Math.max(0, Math.min(newLeft, window.innerWidth - rect.width));
      newTop = Math.max(0, Math.min(newTop, window.innerHeight - rect.height));
      panel.style.left = newLeft + "px";
      panel.style.top = newTop + "px";
    });

    function stopDragging(e) {
      if (!dragging) return;
      dragging = false;
      headerEl.classList.remove("tsc-dragging");
      try { headerEl.releasePointerCapture(e.pointerId); } catch (err) {}
    }
    headerEl.addEventListener("pointerup", stopDragging);
    headerEl.addEventListener("pointercancel", stopDragging);
  })();

  // ----------------------- MESSAGES -----------------------
  // Lichte, veilige markdown-renderer voor bot-antwoorden: escaped eerst
  // alle HTML (dus geen injectie mogelijk via modelinvoer), en zet daarna
  // alleen **vet**, "- "/"1. "-lijsten en alinea's om naar echte tags.
  // Gebruikersberichten blijven via textContent gaan (geen opmaak nodig).
  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function renderBotHtml(text) {
    var escaped = escapeHtml(text).replace(/\*\*([^\n*]+?)\*\*/g, "<strong>$1</strong>");
    var lines = escaped.split("\n");
    var html = "";
    var i = 0;
    while (i < lines.length) {
      if (/^\s*[-*]\s+/.test(lines[i])) {
        var items = [];
        while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
          items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
          i++;
        }
        html += "<ul>" + items.map(function (it) { return "<li>" + it + "</li>"; }).join("") + "</ul>";
        continue;
      }
      if (/^\s*\d+\.\s+/.test(lines[i])) {
        var oitems = [];
        while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
          oitems.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
          i++;
        }
        html += "<ol>" + oitems.map(function (it) { return "<li>" + it + "</li>"; }).join("") + "</ol>";
        continue;
      }
      if (lines[i].trim() === "") { i++; continue; }
      var para = [lines[i]];
      i++;
      while (i < lines.length && lines[i].trim() !== "" && !/^\s*[-*]\s+/.test(lines[i]) && !/^\s*\d+\.\s+/.test(lines[i])) {
        para.push(lines[i]);
        i++;
      }
      html += "<p>" + para.join("<br>") + "</p>";
    }
    return html;
  }

  function addMessage(role, text) {
    var el = document.createElement("div");
    el.className = "tsc-msg " + (role === "user" ? "tsc-msg-user" : "tsc-msg-bot");
    if (role === "user") {
      el.textContent = text;
    } else {
      el.innerHTML = renderBotHtml(text);
    }
    bodyEl.appendChild(el);
    bodyEl.scrollTop = bodyEl.scrollHeight;
    return el;
  }

  function showTyping() {
    var el = document.createElement("div");
    el.className = "tsc-typing";
    el.setAttribute("data-tsc-typing", "");
    el.innerHTML = "<span></span><span></span><span></span>";
    bodyEl.appendChild(el);
    bodyEl.scrollTop = bodyEl.scrollHeight;
    return el;
  }

  // Best-effort parser for a streamed chat response. n8n's LangChain
  // chatTrigger in streaming mode typically emits newline-separated JSON
  // objects; this tries a few known shapes and falls back to raw text.
  function parseStreamChunk(raw) {
    var text = "";
    raw.split("\n").forEach(function (line) {
      line = line.trim();
      if (!line) return;
      if (line.indexOf("data:") === 0) line = line.slice(5).trim();
      try {
        var obj = JSON.parse(line);
        if (typeof obj === "string") { text += obj; return; }
        text += obj.content || obj.chunk || obj.text || obj.output || "";
      } catch (e) {
        // Onherkenbare (niet-JSON) regels stil negeren i.p.v. tonen aan de
        // bezoeker - dit voorkomt dat interne fout-/debugoutput van n8n
        // (bijv. een falende tool-aanroep) rechtstreeks in de chat lekt.
        console.warn("[Tessar concierge] kon streamregel niet verwerken, genegeerd:", line);
      }
    });
    return text;
  }

  function getMessageCount() {
    try { return parseInt(sessionStorage.getItem("tsc_msg_count") || "0", 10) || 0; } catch (e) { return 0; }
  }
  function incrementMessageCount() {
    try { sessionStorage.setItem("tsc_msg_count", String(getMessageCount() + 1)); } catch (e) {}
  }

  async function sendMessage(text) {
    text = (text || inputEl.value).trim();
    if (!text) return;

    if (getMessageCount() >= CONFIG.maxMessagesPerSession) {
      hasSentFirstMessage = true;
      addMessage("user", text);
      inputEl.value = "";
      startersEl.style.display = "none";
      addMessage("bot", CONFIG.limitReachedMessage);
      return;
    }
    incrementMessageCount();

    hasSentFirstMessage = true;
    addMessage("user", text);
    inputEl.value = "";
    sendBtn.disabled = true;
    startersEl.style.display = "none";

    var typingEl = showTyping();
    var botMsgEl = null;

    try {
      var res = await fetch(CONFIG.webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chatInput: text,
          sessionId: sessionId,
          clientId: CONFIG.clientId,
          metadata: { page: location.href, referrer: document.referrer }
        })
      });

      if (!res.ok) throw new Error("HTTP " + res.status);

      if (res.body && res.body.getReader) {
        var reader = res.body.getReader();
        var decoder = new TextDecoder("utf-8");
        var accumulated = "";
        while (true) {
          var chunk = await reader.read();
          if (chunk.done) break;
          var decoded = decoder.decode(chunk.value, { stream: true });
          accumulated += parseStreamChunk(decoded);
          if (!botMsgEl) {
            typingEl.remove();
            botMsgEl = addMessage("bot", accumulated);
          } else {
            botMsgEl.innerHTML = renderBotHtml(accumulated);
            bodyEl.scrollTop = bodyEl.scrollHeight;
          }
        }
        if (!botMsgEl) {
          typingEl.remove();
          addMessage("bot", "Sorry, ik kreeg geen antwoord terug. Probeer het nog eens of mail ons via de contactpagina.");
        }
      } else {
        var data = await res.json();
        typingEl.remove();
        addMessage("bot", data.output || data.text || "Sorry, daar ging iets mis.");
      }
    } catch (err) {
      typingEl.remove();
      addMessage("bot", "Er ging iets mis bij het versturen van je bericht. Probeer het later opnieuw, of neem contact op via het formulier onderaan de pagina.");
      console.error("[Tessar concierge] fout bij ophalen antwoord:", err);
    } finally {
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  sendBtn.addEventListener("click", function () { sendMessage(); });
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  inputEl.addEventListener("input", function () {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + "px";
  });

  // ----------------------- AUTO-OPEN NA 10 SECONDEN -----------------------
  // Opent het paneel vanzelf 10s na binnenkomst, zodat direct duidelijk is
  // dat dit een AI-concierge is en geen standaard chat-widget die wacht tot
  // je 'm zelf ontdekt. Gebeurt maar 1x per browsersessie (sessionStorage),
  // zodat het niet bij elke paginanavigatie binnen dezelfde site opnieuw
  // opduikt, en niet als de bezoeker het paneel intussen al zelf heeft
  // geopend of gesloten.
  var AUTO_OPEN_DELAY_MS = 5000;
  var userInteractedManually = false;
  launcher.addEventListener("click", function () { userInteractedManually = true; }, { once: true });
  closeBtn.addEventListener("click", function () { userInteractedManually = true; }, { once: true });

  var alreadyAutoOpened = false;
  try { alreadyAutoOpened = sessionStorage.getItem("tsc_auto_opened") === "1"; } catch (e) {}

  if (!alreadyAutoOpened) {
    setTimeout(function () {
      if (!userInteractedManually && !isOpen) {
        openPanel();
        try { sessionStorage.setItem("tsc_auto_opened", "1"); } catch (e) {}
      }
    }, AUTO_OPEN_DELAY_MS);
  }
})();
