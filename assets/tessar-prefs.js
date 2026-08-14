/*
 * Tessar — cookiebanner voor Google Analytics (GA4).
 *
 * Bestand heet bewust NIET "cookie-consent.js" of iets vergelijkbaars: die
 * naam staat op vrijwel elke ad-/cookieblocker-filterlijst (bv. EasyList
 * "Cookie Notices"), waardoor het script bij veel bezoekers stil zou falen
 * en de banner nooit zou verschijnen. Zie ook: git-geschiedenis van dit
 * bestand (was eerst assets/cookie-consent.js, hernoemd na een testbezoek
 * waarbij de banner niet laadde).
 *
 * Werkt samen met de inline Consent Mode v2-snippet in de <head> van elke
 * pagina (die zet analytics_storage/ad_* standaard op "denied" vóórdat
 * gtag.js laadt). Dit bestand toont de banner, onthoudt de keuze in
 * localStorage en stuurt bij "Accepteren" een gtag('consent','update', ...)
 * zodat GA4 pas dan daadwerkelijk cookies zet.
 *
 * Nieuwe pagina toevoegen? Kopieer het <head>-blok (Consent Mode + gtag.js +
 * dit script) uit een bestaande pagina, bv. index.html.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "tessar-consent";

  function getStoredConsent() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function storeConsent(value) {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (e) {
      /* privémodus o.i.d. — banner verschijnt dan gewoon opnieuw */
    }
  }

  function updateConsent(granted) {
    if (typeof window.gtag !== "function") return;
    window.gtag("consent", "update", {
      analytics_storage: granted ? "granted" : "denied",
    });
  }

  function removeBanner(el) {
    el.style.transform = "translateY(24px)";
    el.style.opacity = "0";
    window.setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 220);
  }

  function renderBanner() {
    var wrap = document.createElement("div");
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-label", "Cookievoorkeuren");
    wrap.style.cssText =
      "position:fixed;left:16px;right:16px;bottom:16px;z-index:9999;" +
      "max-width:520px;margin:0 auto;" +
      "background:var(--bg,#0f1115);color:var(--text,#f2f2f2);" +
      "border:1px solid var(--border,rgba(255,255,255,0.14));" +
      "border-radius:12px;padding:20px 22px;" +
      "box-shadow:0 12px 36px rgba(0,0,0,0.35);" +
      "font:400 0.9rem/1.5 var(--font-body,'IBM Plex Sans',-apple-system,'Segoe UI',sans-serif);" +
      "display:flex;flex-direction:column;gap:14px;" +
      "opacity:0;transform:translateY(24px);transition:opacity 220ms ease,transform 220ms ease;";

    var text = document.createElement("p");
    text.style.cssText = "margin:0;color:var(--text-dim,#b8b8b8);";
    text.appendChild(
      document.createTextNode(
        "We gebruiken alleen analytics-cookies om te zien hoe bezoekers de site gebruiken — geen advertentietracking. Ga je akkoord? Lees ons "
      )
    );
    var policyLink = document.createElement("a");
    policyLink.href = "/privacy.html";
    policyLink.style.cssText = "color:var(--accent-text,#7dd3fc);text-decoration:underline;";
    policyLink.textContent = "privacybeleid";
    text.appendChild(policyLink);
    text.appendChild(document.createTextNode("."));
    wrap.appendChild(text);

    var actions = document.createElement("div");
    actions.style.cssText = "display:flex;gap:10px;flex-wrap:wrap;";

    var decline = document.createElement("button");
    decline.type = "button";
    decline.textContent = "Weigeren";
    decline.style.cssText =
      "background:transparent;color:var(--text,#f2f2f2);" +
      "border:1px solid var(--border,rgba(255,255,255,0.24));" +
      "border-radius:6px;padding:10px 18px;font:600 0.875rem/1 inherit;" +
      "cursor:pointer;transition:border-color 160ms ease;";

    var accept = document.createElement("button");
    accept.type = "button";
    accept.textContent = "Accepteren";
    accept.style.cssText =
      "background:linear-gradient(135deg, oklch(72% 0.15 210), oklch(62% 0.14 235));" +
      "color:#001a2e;border:none;border-radius:6px;padding:10px 20px;" +
      "font:700 0.875rem/1 inherit;cursor:pointer;transition:transform 160ms ease;";

    accept.addEventListener("click", function () {
      storeConsent("granted");
      updateConsent(true);
      removeBanner(wrap);
    });
    decline.addEventListener("click", function () {
      storeConsent("denied");
      updateConsent(false);
      removeBanner(wrap);
    });

    actions.appendChild(decline);
    actions.appendChild(accept);
    wrap.appendChild(actions);
    document.body.appendChild(wrap);

    // volgende frame: fade/slide in
    window.requestAnimationFrame(function () {
      wrap.style.opacity = "1";
      wrap.style.transform = "translateY(0)";
    });
  }

  function init() {
    var stored = getStoredConsent();
    if (stored === "granted") {
      updateConsent(true);
      return;
    }
    if (stored === "denied") {
      // blijft "denied" (= de Consent Mode-default), niets te doen
      return;
    }
    renderBanner();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
