"use strict";

// Gedeeld door alle drie de pagina's met een .portfolio-shell-zijbalk
// (overview.html, index.html, team.html) — voorkomt dat dezelfde
// KPI/trend/abonnement-logica drie keer los onderhouden moet worden.
// Geladen ná config.js, vóór het pagina-eigen script.

const SIDEBAR_API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";
const MAX_RECENTE_WINKELS = 5;
const APP_VERSIE = "1.0.0";

// Genamespacet per organisatie_id — zonder dit zou op een gedeelde
// browser (bv. dezelfde laptop, twee klanten na elkaar ingelogd) de
// ene organisatie de winkelnamen en omzettrend van de andere te zien
// krijgen, want localStorage is niet vanzelf gescheiden per sessie.
function sidebarSleutel(naam, organisatieId) {
  return `vraagvoorspelling_${naam}_org${organisatieId}`;
}

// Gezet door initPortfolioSidebar() zodra /me bekend is — de overige
// zijbalk-functies (aangeroepen vanuit dashboard.js/overview.js, ook ná
// initPortfolioSidebar) lezen 'm hiervandaan i.p.v. dat elke aanroeper
// zelf organisatie_id moet doorgeven.
let huidigeOrganisatieId = null;

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
  cachePortfolioOmzet(data.kpi.totale_verwachte_omzet, data.winkels.length);
}

// Voor de "T.o.v. je andere winkels"-inzichtkaart op index.html (zie
// dashboard.js) — index.html haalt bewust nooit zelf /portfolio op (zie
// initPortfolioSidebar hieronder), dus deze cache is de enige manier om
// die vergelijking zonder een nieuwe, dure aanroep te tonen. aantalWinkels
// is expliciet data.winkels.length (het aantal winkels waarover de
// omzetsom daadwerkelijk berekend is), niet data.totaal_winkels — die twee
// lopen uiteen zodra paginering actief is, en delen door het verkeerde
// getal zou het gemiddelde per winkel structureel te laag laten uitkomen.
// horizonDagen ligt vast op de HORIZON_DAGEN-constante uit overview.js
// (vandaag 7) — apart gecachet i.p.v. aangenomen, zodat een toekomstige
// wijziging van die constante deze vergelijking niet stilzwijgend scheef
// trekt.
function cachePortfolioOmzet(totaleOmzet, aantalWinkels) {
  const waarde = JSON.stringify({ totaleOmzet, aantalWinkels, horizonDagen: 7 });
  localStorage.setItem(sidebarSleutel("portfolio_omzet_cache", huidigeOrganisatieId), waarde);
}

function haalPortfolioOmzetCache() {
  const ruw = localStorage.getItem(sidebarSleutel("portfolio_omzet_cache", huidigeOrganisatieId));
  if (!ruw) return null;
  try {
    return JSON.parse(ruw);
  } catch (e) {
    return null;
  }
}

function toonOmzetTrend(huidigeOmzet, isVolledigeSet) {
  const pijl = document.getElementById("trend-pijl");
  if (!pijl || !isVolledigeSet) return;
  const sleutel = sidebarSleutel("vorige_sidebar_omzet", huidigeOrganisatieId);
  const vorige = localStorage.getItem(sleutel);
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
  localStorage.setItem(sleutel, String(huidigeOmzet));
}

function voegRecentWinkelToe(winkel) {
  const sleutel = sidebarSleutel("recente_winkels", huidigeOrganisatieId);
  let lijst = [];
  try {
    lijst = JSON.parse(localStorage.getItem(sleutel) || "[]");
  } catch (e) {
    lijst = [];
  }
  lijst = lijst.filter((w) => w.id !== winkel.id);
  lijst.unshift(winkel);
  localStorage.setItem(sleutel, JSON.stringify(lijst.slice(0, MAX_RECENTE_WINKELS)));
}

function toonRecenteWinkels() {
  const wrap = document.getElementById("sidebar-recent");
  const lijstEl = document.getElementById("sidebar-recent-lijst");
  if (!wrap) return;
  let lijst = [];
  try {
    lijst = JSON.parse(localStorage.getItem(sidebarSleutel("recente_winkels", huidigeOrganisatieId)) || "[]");
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

function toonVersieEnMaker() {
  const el = document.getElementById("sidebar-versie");
  if (el) el.textContent = `Prospero v${APP_VERSIE} · © ${new Date().getFullYear()} Tessar`;
}

function initPortfolioSidebar(me) {
  huidigeOrganisatieId = me.organisatie_id;
  markeerActieveSidebarLink();
  toonAbonnementStatus(me);
  toonRecenteWinkels();
  toonVersieEnMaker();
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
