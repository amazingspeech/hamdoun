"use strict";

// Configureerbaar API-adres: lokaal same-origin (de FastAPI-app serveert dit
// dashboard zelf onder dezelfde origin), later het live adres van de
// forecasting-API zodra dit dashboard op de Tessar-website staat — dan wordt
// TESSAR_FORECAST_API_BASIS vóór het laden van dit script gezet.
const API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";

let modelMetrics = null;

const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency", currency: "EUR", maximumFractionDigits: 0,
});

function formatDatumKort(isoDatum) {
  const d = new Date(isoDatum + "T00:00:00");
  return d.toLocaleDateString("nl-NL", { day: "numeric", month: "short" });
}

function wilGeenAnimatie() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function animeerGetal(el, doelwaarde, duurMs = 700) {
  if (wilGeenAnimatie()) {
    el.textContent = euro.format(doelwaarde);
    return;
  }
  const start = performance.now();
  function stap(nu) {
    const voortgang = Math.min(1, (nu - start) / duurMs);
    const uitEase = 1 - Math.pow(1 - voortgang, 3);
    el.textContent = euro.format(Math.round(doelwaarde * uitEase));
    if (voortgang < 1) requestAnimationFrame(stap);
  }
  requestAnimationFrame(stap);
}

async function haalMe() {
  const resp = await fetch(`${API_BASIS}/me`, { credentials: "same-origin" });
  if (!resp.ok) return null;
  return resp.json();
}

async function laadWinkels() {
  const resp = await fetch(`${API_BASIS}/winkels`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon de winkellijst niet ophalen (${resp.status})`);
  const winkels = await resp.json();
  const select = document.getElementById("store");
  select.innerHTML = "";
  for (const winkel of winkels) {
    const optie = document.createElement("option");
    optie.value = String(winkel.extern_store_id);
    optie.textContent = winkel.naam || `Winkel ${winkel.extern_store_id}`;
    select.appendChild(optie);
  }
  return winkels;
}

function toonFout(bericht) {
  const el = document.getElementById("fout");
  el.textContent = bericht;
  el.hidden = !bericht;
}

async function laadMetrics() {
  const resp = await fetch(`${API_BASIS}/metrics`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon nauwkeurigheidscijfers niet ophalen (${resp.status})`);
  const data = await resp.json();
  modelMetrics = data;

  document.getElementById("sub-basis").textContent =
    `Gebaseerd op ${data.n_observaties.toLocaleString("nl-NL")} historische verkoopdagen, ` +
    `getraind t/m ${formatDatumKort(data.trainingsperiode_eind)} — met een eerlijke bandbreedte ` +
    `in plaats van één te precies getal.`;

  const container = document.getElementById("metrics");
  container.innerHTML = "";
  const items = [
    [
      "Nauwkeurigheid",
      (data.rmspe * 100).toFixed(1) + "%",
      "Gemiddelde afwijking tussen voorspelde en werkelijke omzet, gemeten op historische data. Lager is beter.",
    ],
    [
      "Betrouwbaarheid van de bandbreedte",
      (data.coverage_p10_p90 * 100).toFixed(0) + "%",
      "Hoe vaak de werkelijke omzet historisch binnen de getoonde bandbreedte viel. Streefwaarde: ongeveer 80%.",
    ],
    ["Modelversie", data.model_versie, "Getraind tot en met " + formatDatumKort(data.trainingsperiode_eind) + "."],
  ];
  for (const [label, waarde, uitleg] of items) {
    const kaart = document.createElement("div");
    kaart.className = "metric";
    const labelEl = document.createElement("div");
    labelEl.className = "label";
    labelEl.textContent = label;
    const waardeEl = document.createElement("div");
    waardeEl.className = "value";
    waardeEl.textContent = waarde;
    const uitlegEl = document.createElement("div");
    uitlegEl.className = "uitleg";
    uitlegEl.textContent = uitleg;
    kaart.append(labelEl, waardeEl, uitlegEl);
    container.appendChild(kaart);
  }
  return data;
}

async function haalVoorspelling(storeId, startDatum, horizonDagen, promoVakantie) {
  const resp = await fetch(`${API_BASIS}/forecast`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      store_id: storeId, start_datum: startDatum, horizon_dagen: horizonDagen,
      promo_van: promoVakantie.promoVan || null, promo_tot: promoVakantie.promoTot || null,
      schoolvakantie_van: promoVakantie.vakantieVan || null, schoolvakantie_tot: promoVakantie.vakantieTot || null,
    }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Voorspelling mislukt (${resp.status})`);
  }
  return resp.json();
}

function maakSVGEl(tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [naam, waarde] of Object.entries(attrs)) el.setAttribute(naam, waarde);
  return el;
}

function tekenGrafiek(voorspellingen) {
  const svg = document.getElementById("chart");
  const breedte = 920, hoogte = 360, marge = { boven: 20, rechts: 20, onder: 34, links: 70 };
  const plotBreedte = breedte - marge.links - marge.rechts;
  const plotHoogte = hoogte - marge.boven - marge.onder;

  const alleWaarden = voorspellingen.flatMap((v) => [v.p10, v.p90]);
  const minY = Math.min(...alleWaarden) * 0.95;
  const maxY = Math.max(...alleWaarden) * 1.05;

  const x = (i) => marge.links + (i / (voorspellingen.length - 1 || 1)) * plotBreedte;
  const y = (waarde) => marge.boven + plotHoogte - ((waarde - minY) / (maxY - minY)) * plotHoogte;

  const bandPunten = [
    ...voorspellingen.map((v, i) => `${x(i)},${y(v.p90)}`),
    ...[...voorspellingen].reverse().map((v, i) => `${x(voorspellingen.length - 1 - i)},${y(v.p10)}`),
  ].join(" ");
  const lijnPunten = voorspellingen.map((v, i) => `${x(i)},${y(v.p50)}`).join(" ");

  svg.replaceChildren();

  svg.appendChild(maakSVGEl("polygon", { class: "band", points: bandPunten }));
  const lijnEl = maakSVGEl("polyline", { class: "lijn", points: lijnPunten });
  svg.appendChild(lijnEl);
  svg.appendChild(maakSVGEl("line", {
    class: "as", x1: marge.links, y1: marge.boven, x2: marge.links, y2: hoogte - marge.onder,
  }));
  svg.appendChild(maakSVGEl("line", {
    class: "as", x1: marge.links, y1: hoogte - marge.onder, x2: breedte - marge.rechts, y2: hoogte - marge.onder,
  }));

  // Y-as: drie referentiepunten (min/midden/max) zodat de band niet zomaar
  // "een vorm" is maar een af te lezen bedrag.
  const yTicks = [minY, (minY + maxY) / 2, maxY];
  for (const waarde of yTicks) {
    const label = maakSVGEl("text", {
      class: "as-label", x: marge.links - 10, y: y(waarde) + 4, "text-anchor": "end",
    });
    label.textContent = euro.format(Math.round(waarde));
    svg.appendChild(label);
    svg.appendChild(maakSVGEl("line", {
      class: "as", x1: marge.links - 4, y1: y(waarde), x2: marge.links, y2: y(waarde),
    }));
  }

  // X-as: eerste, middelste en laatste dag als datum — genoeg om de
  // horizon te kunnen aflezen zonder de as vol te proppen.
  const n = voorspellingen.length;
  const xIndices = n > 2 ? [0, Math.floor((n - 1) / 2), n - 1] : [...Array(n).keys()];
  for (const i of xIndices) {
    // Label bij het meest linkse punt groeit naar rechts (start), bij het
    // meest rechtse naar links (end) — anders kan gecentreerde tekst over
    // de vaste 920px-breedte heen steken bij het laatste punt (slechts
    // 20px marge rechts).
    const anker = i === 0 ? "start" : i === n - 1 ? "end" : "middle";
    const label = maakSVGEl("text", {
      class: "as-label", x: x(i), y: hoogte - marge.onder + 20, "text-anchor": anker,
    });
    label.textContent = formatDatumKort(voorspellingen[i].datum);
    svg.appendChild(label);
  }

  // Laatste dag als eindpunt benadrukken, zodat de lijn duidelijk "landt".
  const laatste = voorspellingen[n - 1];
  svg.appendChild(maakSVGEl("circle", { class: "stip", cx: x(n - 1), cy: y(laatste.p50), r: 4 }));

  // De lijn "tekent" zichzelf in via stroke-dasharray/-dashoffset. Twee
  // geneste rAF's: de eerste laat de browser de startstand (volledig
  // ingekort) daadwerkelijk schilderen vóórdat de tweede 'm naar 0
  // overgangt — anders wordt de overgang soms samengevoegd met de
  // beginstand en is er niets te zien. Zonder voorkeur voor animatie
  // bestaat de CSS-transition niet (zie stylesheet), dus dan is dit een
  // no-op sprong naar het eindbeeld.
  if (!wilGeenAnimatie()) {
    const lengte = lijnEl.getTotalLength();
    lijnEl.style.strokeDasharray = `${lengte}`;
    lijnEl.style.strokeDashoffset = `${lengte}`;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        lijnEl.style.strokeDashoffset = "0";
      });
    });
  }
}

function maakStat(label, waarde, toelichting) {
  const stat = document.createElement("div");
  stat.className = "stat";
  const labelEl = document.createElement("div");
  labelEl.className = "label";
  labelEl.textContent = label;
  const waardeEl = document.createElement("div");
  waardeEl.className = "waarde";
  waardeEl.textContent = waarde;
  const toelichtingEl = document.createElement("div");
  toelichtingEl.className = "toelichting";
  toelichtingEl.textContent = toelichting;
  stat.append(labelEl, waardeEl, toelichtingEl);
  return stat;
}

function maakFactorChip(factor) {
  const chip = document.createElement("span");
  chip.className = `factor-chip ${factor.richting}`;
  const pijl = document.createElement("span");
  pijl.className = "pijl";
  pijl.textContent = factor.richting === "hoger" ? "↑" : "↓";
  const tekst = document.createElement("span");
  tekst.textContent = `${factor.naam} — ${factor.richting} dan gemiddeld`;
  chip.append(pijl, tekst);
  return chip;
}

function toonFactoren(factoren) {
  const el = document.getElementById("factoren");
  if (!factoren || factoren.length === 0) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  document.getElementById("factoren-lijst").replaceChildren(...factoren.map(maakFactorChip));
}

function toonSamenvatting(voorspellingen, storeId) {
  const totaalP50 = voorspellingen.reduce((som, v) => som + v.p50, 0);
  const totaalP10 = voorspellingen.reduce((som, v) => som + v.p10, 0);
  const totaalP90 = voorspellingen.reduce((som, v) => som + v.p90, 0);
  const n = voorspellingen.length;
  const dagLabel = n === 1 ? "1 dag" : `${n} dagen`;
  const betrouwbaarheid = modelMetrics ? Math.round(modelMetrics.coverage_p10_p90 * 100) : null;

  document.getElementById("hero-lead").textContent =
    `Winkel ${storeId} verkoopt de komende ${dagLabel} waarschijnlijk ongeveer`;
  animeerGetal(document.getElementById("hero-waarde"), Math.round(totaalP50));
  document.getElementById("hero-sub").textContent =
    `${formatDatumKort(voorspellingen[0].datum)} – ${formatDatumKort(voorspellingen[n - 1].datum)}`;

  const secundairContainer = document.getElementById("secundair");
  secundairContainer.innerHTML = "";
  secundairContainer.appendChild(maakStat(
    "Bandbreedte",
    `${euro.format(Math.round(totaalP10))} – ${euro.format(Math.round(totaalP90))}`,
    betrouwbaarheid !== null
      ? `De werkelijke omzet valt hier historisch in ~${betrouwbaarheid}% van de gevallen binnen.`
      : "De omzet ligt hier meestal binnen.",
  ));
  secundairContainer.appendChild(maakStat(
    "Gemiddeld per dag",
    euro.format(Math.round(totaalP50 / n)),
    "Gebaseerd op vergelijkbare dagen uit het verleden.",
  ));

  document.getElementById("chart-titel").textContent =
    `Winkel ${storeId} — dagelijkse omzet, ${formatDatumKort(voorspellingen[0].datum)} t/m ${formatDatumKort(voorspellingen[n - 1].datum)}`;

  document.getElementById("aanbeveling").textContent =
    `Plan voorraad voor circa ${euro.format(Math.round(totaalP50))} omzet deze periode. ` +
    `Houd rekening met pieken tot ${euro.format(Math.round(totaalP90))} bij drukte, en met minder ` +
    `verkoop tot ${euro.format(Math.round(totaalP10))} als het rustiger is dan verwacht.`;
}

function toonKanttekening(promoOpgegeven, vakantieOpgegeven) {
  const el = document.getElementById("kanttekening");
  if (promoOpgegeven && vakantieOpgegeven) {
    el.textContent = "Deze voorspelling houdt rekening met de opgegeven promotie- en schoolvakantieperiode.";
  } else if (promoOpgegeven) {
    el.textContent =
      "Deze voorspelling houdt rekening met de opgegeven promotieperiode. Geen schoolvakantie opgegeven — " +
      "speelt er in deze periode ook een schoolvakantie, dan kan de werkelijke omzet hoger uitvallen.";
  } else if (vakantieOpgegeven) {
    el.textContent =
      "Deze voorspelling houdt rekening met de opgegeven schoolvakantieperiode. Geen promotie opgegeven — " +
      "speelt er in deze periode ook een promotie, dan kan de werkelijke omzet hoger uitvallen.";
  } else {
    el.textContent =
      "Houdt geen rekening met promoties of schoolvakanties — geef die hierboven op als die in deze " +
      "periode spelen, anders kan de werkelijke omzet op zulke dagen hoger uitvallen dan hier getoond.";
  }
}

async function voorspel() {
  const knop = document.getElementById("voorspel");
  knop.disabled = true;
  toonFout("");
  try {
    const storeId = Number(document.getElementById("store").value);
    const startDatum = document.getElementById("start").value;
    const horizonDagen = Number(document.getElementById("horizon").value);
    const promoVakantie = {
      promoVan: document.getElementById("promo-van").value,
      promoTot: document.getElementById("promo-tot").value,
      vakantieVan: document.getElementById("vakantie-van").value,
      vakantieTot: document.getElementById("vakantie-tot").value,
    };
    const data = await haalVoorspelling(storeId, startDatum, horizonDagen, promoVakantie);
    // Het model heeft geen ondergrens van 0 op voorspelde omzet (zie
    // KNOWN-LIMITATIONS.md) — hier, en alleen hier voor weergave, geklemd
    // op 0 zodat een winkelier nooit een letterlijk negatief omzetbedrag
    // te zien krijgt. Klemt p10/p50/p90 elk apart, wat p10 <= p50 <= p90
    // intact laat.
    const voorspellingen = data.voorspellingen.map((v) => ({
      ...v,
      p10: Math.max(0, v.p10),
      p50: Math.max(0, v.p50),
      p90: Math.max(0, v.p90),
    }));
    document.getElementById("leeg").hidden = true;
    document.getElementById("resultaat").classList.add("zichtbaar");
    toonSamenvatting(voorspellingen, data.store_id);
    tekenGrafiek(voorspellingen);
    toonKanttekening(Boolean(promoVakantie.promoVan), Boolean(promoVakantie.vakantieVan));
    toonFactoren(data.belangrijkste_factoren);
  } catch (e) {
    toonFout(e.message);
  } finally {
    knop.disabled = false;
  }
}

function vandaagPlusEen() {
  const morgen = new Date();
  morgen.setDate(morgen.getDate() + 1);
  return morgen.toISOString().slice(0, 10);
}

function eenDagNa(isoDatum) {
  const d = new Date(isoDatum + "T00:00:00");
  d.setDate(d.getDate() + 1);
  const jaar = d.getFullYear();
  const maand = String(d.getMonth() + 1).padStart(2, "0");
  const dag = String(d.getDate()).padStart(2, "0");
  return `${jaar}-${maand}-${dag}`;
}

function sluitAndereInfoKnopjes(event) {
  for (const details of document.querySelectorAll(".info[open]")) {
    if (!details.contains(event.target)) details.open = false;
  }
}

function initInfoKnopjes() {
  for (const details of document.querySelectorAll(".info")) {
    details.addEventListener("toggle", () => {
      if (!details.open) return;
      for (const ander of document.querySelectorAll(".info[open]")) {
        if (ander !== details) ander.open = false;
      }
    });
  }
}

async function initToegang() {
  const me = await haalMe();
  if (!me) {
    window.location.href = "./login.html";
    return null;
  }
  const wieBenIk = document.getElementById("wie-ben-ik");
  if (wieBenIk) wieBenIk.textContent = `Ingelogd als ${me.email}`;
  return me;
}

function initUitloggenLink() {
  const link = document.getElementById("uitloggen");
  if (!link) return;
  link.addEventListener("click", async (event) => {
    event.preventDefault();
    await fetch(`${API_BASIS}/logout`, { method: "POST", credentials: "same-origin" });
    window.location.href = "./login.html";
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  const me = await initToegang();
  if (!me) return;
  initUitloggenLink();

  const knop = document.getElementById("voorspel");
  document.addEventListener("click", sluitAndereInfoKnopjes);
  initInfoKnopjes();
  document.getElementById("start").value = vandaagPlusEen();
  knop.addEventListener("click", voorspel);

  let winkels;
  try {
    winkels = await laadWinkels();
  } catch (e) {
    toonFout(e.message);
    return;
  }
  if (winkels.length === 0) {
    document.getElementById("leeg").textContent =
      "Er zijn nog geen winkels aan jouw organisatie gekoppeld. Neem contact op om dit in te laten stellen.";
    return;
  }

  // Knop blijft uit tot /metrics geladen is: anders kan een snelle klik een
  // voorspelling opvragen met de kalenderdatum van vandaag in plaats van een
  // datum die bij de trainingsperiode van het model past, zonder dat de
  // gebruiker iets fout ziet gaan.
  laadMetrics()
    .then((data) => {
      document.getElementById("start").value = eenDagNa(data.trainingsperiode_eind);
      // Voorkomt de servergegenereerde 422-foutmelding voor het gangbare
      // geval: het veld kan nu al niet verder dan wat het model dekt.
      const horizonVeld = document.getElementById("horizon");
      horizonVeld.max = String(data.gevalideerde_horizon_dagen);
      if (Number(horizonVeld.value) > data.gevalideerde_horizon_dagen) {
        horizonVeld.value = String(data.gevalideerde_horizon_dagen);
      }
    })
    .catch((e) => toonFout(e.message))
    .finally(() => {
      knop.disabled = false;
      knop.textContent = "Voorspel";
    });
});
