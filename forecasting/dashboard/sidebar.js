"use strict";

// Gedeeld door alle drie de pagina's met een .portfolio-shell-zijbalk
// (overview.html, index.html, team.html) — voorkomt dat dezelfde
// KPI/trend/abonnement-logica drie keer los onderhouden moet worden.
// Geladen ná config.js, vóór het pagina-eigen script.

const SIDEBAR_API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";
const RECENTE_WINKELS_SLEUTEL = "vraagvoorspelling_recente_winkels";
const VORIGE_OMZET_SLEUTEL = "vraagvoorspelling_vorige_sidebar_omzet";
const MAX_RECENTE_WINKELS = 5;

function markeerActieveSidebarLink() {
  const huidige = window.location.pathname.split("/").pop() || "index.html";
  for (const link of document.querySelectorAll(".portfolio-sidebar-nav a")) {
    const href = link.getAttribute("href") || "";
    // Een link met een #anker (bv. API-keys -> team.html#api-keys-kaart)
    // is een snelkoppeling binnen een pagina, geen aparte paginaweergave
    // — telt dus nooit mee als "actieve pagina", ook al is de pathname
    // hetzelfde.
    if (href.includes("#")) continue;
    if (href.replace("./", "") === huidige) link.classList.add("actief");
  }
}

function toonAbonnementStatus(me) {
  const el = document.getElementById("sidebar-abonnement");
  if (!el) return;
  if (me.in_proefperiode && me.trial_verloopt_op) {
    const vandaag = new Date();
    vandaag.setHours(0, 0, 0, 0);
    const verlooptOp = new Date(`${me.trial_verloopt_op}T00:00:00`);
    const dagenResterend = Math.max(0, Math.round((verlooptOp - vandaag) / 86400000));
    el.textContent = `${dagenResterend} ${dagenResterend === 1 ? "dag" : "dagen"} resterend in je proefperiode`;
  } else {
    el.textContent = "Alle functies actief";
  }
}

function toonSidebarKpis(data) {
  const wrap = document.getElementById("sidebar-kpis");
  const caveat = document.getElementById("sidebar-kpis-caveat");
  if (!wrap || !data || data.totaal_winkels === 0) return;

  document.getElementById("sidebar-kpi-winkels").textContent = String(data.totaal_winkels);
  document.getElementById("sidebar-kpi-nauwkeurigheid").textContent =
    `${(data.kpi.model_nauwkeurigheid_rmspe * 100).toFixed(0)}%`;
  wrap.hidden = false;

  const geladen = data.winkels.length;
  if (geladen < data.totaal_winkels) {
    caveat.textContent = `Op basis van de eerste ${geladen} van ${data.totaal_winkels} winkels.`;
    caveat.hidden = false;
  }

  toonOmzetTrend(data.kpi.totale_verwachte_omzet, geladen === data.totaal_winkels);
}

function toonOmzetTrend(huidigeOmzet, isVolledigeSet) {
  const pijl = document.getElementById("trend-pijl");
  if (!pijl || !isVolledigeSet) return;
  const vorige = localStorage.getItem(VORIGE_OMZET_SLEUTEL);
  if (vorige !== null) {
    const verschil = huidigeOmzet - parseFloat(vorige);
    // Kleine, bewust ongevoelige marge (0,5%) zodat een verwaarloosbaar
    // verschil (bv. afronding tussen twee vrijwel identieke aanvragen)
    // niet als een "trend" oogt.
    if (Math.abs(verschil) > Math.abs(parseFloat(vorige)) * 0.005) {
      pijl.textContent = verschil > 0 ? "↑" : "↓";
      pijl.className = `trend-pijl ${verschil > 0 ? "omhoog" : "omlaag"}`;
      pijl.title = `${verschil > 0 ? "Hoger" : "Lager"} dan bij je vorige bezoek`;
      pijl.hidden = false;
    }
  }
  localStorage.setItem(VORIGE_OMZET_SLEUTEL, String(huidigeOmzet));
}

function voegRecentWinkelToe(winkel) {
  let lijst = [];
  try {
    lijst = JSON.parse(localStorage.getItem(RECENTE_WINKELS_SLEUTEL) || "[]");
  } catch (e) {
    lijst = [];
  }
  lijst = lijst.filter((w) => w.id !== winkel.id);
  lijst.unshift(winkel);
  localStorage.setItem(RECENTE_WINKELS_SLEUTEL, JSON.stringify(lijst.slice(0, MAX_RECENTE_WINKELS)));
}

function toonRecenteWinkels() {
  const wrap = document.getElementById("sidebar-recent");
  const lijstEl = document.getElementById("sidebar-recent-lijst");
  if (!wrap) return;
  let lijst = [];
  try {
    lijst = JSON.parse(localStorage.getItem(RECENTE_WINKELS_SLEUTEL) || "[]");
  } catch (e) {
    lijst = [];
  }
  if (lijst.length === 0) return;

  lijstEl.replaceChildren(...lijst.map((winkel) => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `./index.html?winkel=${winkel.id}`;
    a.textContent = winkel.naam;
    li.appendChild(a);
    return li;
  }));
  wrap.hidden = false;
}

function initPortfolioSidebar(me) {
  markeerActieveSidebarLink();
  toonAbonnementStatus(me);
  toonRecenteWinkels();
  // Bewust GEEN eigen /portfolio-aanroep hier: dat endpoint berekent een
  // echte voorspelling per winkel (kostbaar — zie serving/app.py's eigen
  // toelichting bij een volledige 1115-winkel-berekening: ~88s). Een
  // tweede, aparte aanroep alleen voor twee sidebar-cijfers zou op elke
  // pagina onnodige serverbelasting toevoegen, en liep bij een organisatie
  // met veel winkels zelfs vast naast de hoofdpagina's eigen aanroep (zie
  // toonSidebarKpis hieronder). overview.js roept toonSidebarKpis() zelf
  // aan met data die het toch al ophaalt voor de hoofdtabel — op
  // index.html/team.html blijft dit gedeelte van de zijbalk dus leeg.
}
