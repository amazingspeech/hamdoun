"use strict";

// Configureerbaar API-adres: lokaal same-origin (de FastAPI-app serveert dit
// dashboard zelf onder dezelfde origin), later het live adres van de
// forecasting-API zodra dit dashboard op de Tessar-website staat — dan wordt
// TESSAR_FORECAST_API_BASIS vóór het laden van dit script gezet.
const API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";

let modelMetrics = null;
let alleWinkelsCache = [];
let laatsteVoorspelling = null;

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
  toonNauwkeurigheidTrend(data.geschiedenis);
  return data;
}

function maakNauwkeurigheidSparkline(reeks) {
  const breedte = 160, hoogte = 32;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(breedte));
  svg.setAttribute("height", String(hoogte));
  svg.setAttribute("class", "sparkline");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Nauwkeurigheid per modelversie, oudste naar nieuwste");
  if (reeks.length < 2) return svg;

  const min = Math.min(...reeks), max = Math.max(...reeks);
  const spreiding = max - min || 1;
  const x = (i) => (i / (reeks.length - 1)) * (breedte - 6) + 3;
  const y = (v) => hoogte - 4 - ((v - min) / spreiding) * (hoogte - 8);

  svg.appendChild(maakSVGEl("polyline", {
    points: reeks.map((v, i) => `${x(i)},${y(v)}`).join(" "), class: "sparkline-lijn",
  }));
  svg.appendChild(maakSVGEl("circle", {
    cx: x(reeks.length - 1), cy: y(reeks[reeks.length - 1]), r: "2.5", class: "sparkline-stip",
  }));
  return svg;
}

// "Nauwkeurigheid" hier = 100% - RMSPE, zodat hoger in de grafiek ook
// beter betekent — RMSPE zelf loopt de andere kant op (lager is beter),
// wat in een sparkline-context verwarrend zou ogen ("stijgende lijn" die
// eigenlijk verslechtering betekent).
function toonNauwkeurigheidTrend(geschiedenis) {
  const el = document.getElementById("nauwkeurigheid-trend");
  if (!geschiedenis || geschiedenis.length < 2) {
    el.hidden = true;
    return;
  }
  const accuraatheid = geschiedenis.map((g) => 100 - g.rmspe * 100);
  const eerste = accuraatheid[0];
  const laatste = accuraatheid[accuraatheid.length - 1];
  const verschil = laatste - eerste;
  const richting = Math.abs(verschil) < 1 ? "blijft stabiel" : verschil > 0 ? "verbetert" : "is afgenomen";

  el.replaceChildren();
  const titel = document.createElement("p");
  titel.className = "nauwkeurigheid-trend-titel";
  titel.textContent = "Nauwkeurigheid over tijd";
  const rij = document.createElement("div");
  rij.className = "nauwkeurigheid-trend-rij";
  rij.appendChild(maakNauwkeurigheidSparkline(accuraatheid));
  const tekst = document.createElement("span");
  tekst.textContent =
    `${eerste.toFixed(0)}% → ${laatste.toFixed(0)}% over de laatste ${geschiedenis.length} versies — ${richting}.`;
  rij.appendChild(tekst);
  el.append(titel, rij);
  el.hidden = false;
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

function downloadBlob(blob, bestandsnaam) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = bestandsnaam;
  link.click();
  URL.revokeObjectURL(url);
}

function exporteerCsv() {
  if (!laatsteVoorspelling) return;
  const { voorspellingen, storeId } = laatsteVoorspelling;
  const regels = ["datum,p10,p50,p90"];
  for (const v of voorspellingen) regels.push(`${v.datum},${v.p10},${v.p50},${v.p90}`);
  const blob = new Blob([regels.join("\n")], { type: "text/csv;charset=utf-8" });
  downloadBlob(blob, `voorspelling-winkel-${storeId}.csv`);
}

// Kopieert de live SVG en zet berekende stijlen (kleur, lijndikte,
// lettertype) om naar inline attributen: een <img>/data-URL-SVG laadt
// nooit de externe stylesheet, dus zonder dit zou de PNG kleurloos zijn.
function inlineerSvgStijlen(bron, kloon) {
  const bronElementen = bron.querySelectorAll("*");
  const kloonElementen = kloon.querySelectorAll("*");
  bronElementen.forEach((bronEl, i) => {
    const berekend = getComputedStyle(bronEl);
    const kloonEl = kloonElementen[i];
    if (berekend.fill && berekend.fill !== "none") kloonEl.setAttribute("fill", berekend.fill);
    if (berekend.stroke && berekend.stroke !== "none") kloonEl.setAttribute("stroke", berekend.stroke);
    if (parseFloat(berekend.strokeWidth) > 0) kloonEl.setAttribute("stroke-width", berekend.strokeWidth);
    if (kloonEl.tagName === "text") {
      kloonEl.setAttribute("font-family", berekend.fontFamily);
      kloonEl.setAttribute("font-size", berekend.fontSize);
    }
  });
}

function exporteerPng() {
  if (!laatsteVoorspelling) return;
  const bronSvg = document.getElementById("chart");
  const breedte = bronSvg.width.baseVal.value;
  const hoogte = bronSvg.height.baseVal.value;
  const kloon = bronSvg.cloneNode(true);
  inlineerSvgStijlen(bronSvg, kloon);
  kloon.setAttribute("xmlns", "http://www.w3.org/2000/svg");

  const achtergrond = getComputedStyle(document.getElementById("chart-container")).backgroundColor;
  const svgTekst = new XMLSerializer().serializeToString(kloon);
  const svgUrl = URL.createObjectURL(new Blob([svgTekst], { type: "image/svg+xml;charset=utf-8" }));

  const img = new Image();
  img.onload = () => {
    const schaal = 2; // scherper dan 1:1 op scherms met hoge pixeldichtheid
    const canvas = document.createElement("canvas");
    canvas.width = breedte * schaal;
    canvas.height = hoogte * schaal;
    const ctx = canvas.getContext("2d");
    ctx.scale(schaal, schaal);
    ctx.fillStyle = achtergrond;
    ctx.fillRect(0, 0, breedte, hoogte);
    ctx.drawImage(img, 0, 0, breedte, hoogte);
    URL.revokeObjectURL(svgUrl);
    canvas.toBlob((blob) => downloadBlob(blob, `voorspelling-winkel-${laatsteVoorspelling.storeId}.png`));
  };
  img.onerror = () => toonFout("Grafiek exporteren als PNG is niet gelukt.");
  img.src = svgUrl;
}

function toonExportKnoppen(zichtbaar) {
  document.getElementById("export-knoppen").hidden = !zichtbaar;
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

function toonPeriodeVergelijking(totaalP50, vorigePeriodeOmzet) {
  const el = document.getElementById("periode-vergelijking");
  if (vorigePeriodeOmzet === null || vorigePeriodeOmzet === undefined || vorigePeriodeOmzet === 0) {
    el.hidden = true;
    return;
  }
  const verschilPct = Math.round(((totaalP50 - vorigePeriodeOmzet) / vorigePeriodeOmzet) * 100);
  const vorigeTekst = `de vergelijkbare voorgaande periode (${euro.format(Math.round(vorigePeriodeOmzet))})`;
  if (Math.abs(verschilPct) < 2) {
    el.textContent = `Vergelijkbaar met ${vorigeTekst}.`;
  } else if (verschilPct > 0) {
    el.textContent = `↑ ${verschilPct}% meer dan ${vorigeTekst}.`;
  } else {
    el.textContent = `↓ ${Math.abs(verschilPct)}% minder dan ${vorigeTekst}.`;
  }
  el.hidden = false;
}

function toonSamenvatting(voorspellingen, storeId, vorigePeriodeOmzet, herbestelAdvies) {
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
  toonPeriodeVergelijking(totaalP50, vorigePeriodeOmzet);

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

  // Herbestel-advies (Fase 5 NODIG 1) vervangt het omzetgetal door een
  // stuks-advies zodra de organisatie een gemiddelde prijs per stuk heeft
  // ingesteld (Team beheren) — dat is nuttiger om echt op te bestellen dan
  // een omzetbedrag. Zonder die prijs blijft de bestaande omzet-tekst
  // ongewijzigd staan, geen verzonnen stuks-aantal.
  if (herbestelAdvies) {
    document.getElementById("aanbeveling").textContent =
      `Bestel voor deze periode ongeveer ${herbestelAdvies.stuks_p50} stuks bij. ` +
      `Houd rekening met pieken tot ${herbestelAdvies.stuks_p90} stuks bij drukte, en met minder ` +
      `verkoop tot ${herbestelAdvies.stuks_p10} stuks als het rustiger is dan verwacht.`;
  } else {
    document.getElementById("aanbeveling").textContent =
      `Plan voorraad voor circa ${euro.format(Math.round(totaalP50))} omzet deze periode. ` +
      `Houd rekening met pieken tot ${euro.format(Math.round(totaalP90))} bij drukte, en met minder ` +
      `verkoop tot ${euro.format(Math.round(totaalP10))} als het rustiger is dan verwacht.`;
  }
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

// Koppelt formuliervelden aan hun URL-parameternaam, zodat een specifieke
// weergave (winkel/datum/horizon/promo-vakantie) te delen of te
// bookmarken is — de URL wordt na elke geslaagde voorspelling bijgewerkt
// (synchroniseerUrl) en bij het laden gelezen (pasUrlParamsToe).
const VELD_PARAM_MAP = {
  store: "winkel",
  start: "start",
  horizon: "horizon",
};

function synchroniseerUrl() {
  const params = new URLSearchParams();
  for (const [veldId, paramNaam] of Object.entries(VELD_PARAM_MAP)) {
    const waarde = document.getElementById(veldId).value;
    if (waarde) params.set(paramNaam, waarde);
  }
  if (document.getElementById("promo-vinkje").checked) params.set("promo", "1");
  if (document.getElementById("vakantie-vinkje").checked) params.set("vakantie", "1");
  history.replaceState(null, "", `?${params.toString()}`);
}

function pasUrlParamsToe(winkels, params) {
  let heeftWeergave = false;
  const winkelId = params.get("winkel");
  if (winkelId && winkels.some((w) => String(w.extern_store_id) === winkelId)) {
    document.getElementById("store").value = winkelId;
    heeftWeergave = true;
  }
  for (const [veldId, paramNaam] of Object.entries(VELD_PARAM_MAP)) {
    if (veldId === "store") continue;
    const waarde = params.get(paramNaam);
    if (waarde) {
      document.getElementById(veldId).value = waarde;
      heeftWeergave = true;
    }
  }
  if (params.get("promo") === "1") {
    document.getElementById("promo-vinkje").checked = true;
    heeftWeergave = true;
  }
  if (params.get("vakantie") === "1") {
    document.getElementById("vakantie-vinkje").checked = true;
    heeftWeergave = true;
  }
  return heeftWeergave;
}

async function voorspel() {
  const knop = document.getElementById("voorspel");
  knop.disabled = true;
  toonFout("");
  document.getElementById("leeg").hidden = true;
  document.getElementById("resultaat").classList.remove("zichtbaar");
  document.getElementById("skelet-resultaat").hidden = false;
  try {
    const storeId = Number(document.getElementById("store").value);
    const startDatum = document.getElementById("start").value;
    const horizonDagen = Number(document.getElementById("horizon").value);
    // Vinkje i.p.v. configuratiescherm: een aangevinkte actie/vakantie
    // geldt voor de hele opgevraagde periode (start t/m start+horizon-1),
    // niet voor een apart te kiezen deelperiode — simpeler voor iemand die
    // geen tijd heeft om twee datumbereiken uit te zoeken.
    const laatsteDag = dagenNa(startDatum, horizonDagen - 1);
    const promoVakantie = {
      promoVan: document.getElementById("promo-vinkje").checked ? startDatum : "",
      promoTot: document.getElementById("promo-vinkje").checked ? laatsteDag : "",
      vakantieVan: document.getElementById("vakantie-vinkje").checked ? startDatum : "",
      vakantieTot: document.getElementById("vakantie-vinkje").checked ? laatsteDag : "",
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
    document.getElementById("skelet-resultaat").hidden = true;
    document.getElementById("resultaat").classList.add("zichtbaar");
    const storeSelect = document.getElementById("store");
    const storeNaam = storeSelect.options[storeSelect.selectedIndex]?.textContent || `Winkel ${data.store_id}`;
    if (typeof voegRecentWinkelToe === "function") voegRecentWinkelToe({ id: data.store_id, naam: storeNaam });
    toonSamenvatting(voorspellingen, data.store_id, data.vorige_periode_omzet, data.herbestel_advies);
    tekenGrafiek(voorspellingen);
    toonKanttekening(Boolean(promoVakantie.promoVan), Boolean(promoVakantie.vakantieVan));
    toonFactoren(data.belangrijkste_factoren);
    laatsteVoorspelling = { voorspellingen, storeId: data.store_id };
    toonExportKnoppen(true);
    synchroniseerUrl();
  } catch (e) {
    document.getElementById("skelet-resultaat").hidden = true;
    document.getElementById("leeg").hidden = false;
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

function dagenNa(isoDatum, aantalDagen) {
  const d = new Date(isoDatum + "T00:00:00");
  d.setDate(d.getDate() + aantalDagen);
  const jaar = d.getFullYear();
  const maand = String(d.getMonth() + 1).padStart(2, "0");
  const dag = String(d.getDate()).padStart(2, "0");
  return `${jaar}-${maand}-${dag}`;
}

function eenDagNa(isoDatum) {
  return dagenNa(isoDatum, 1);
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
  const wieBenIkMobiel = document.getElementById("wie-ben-ik-mobiel");
  if (wieBenIkMobiel) wieBenIkMobiel.textContent = `Ingelogd als ${me.email}`;
  const wieBenIk = document.getElementById("wie-ben-ik");
  if (wieBenIk) wieBenIk.textContent = me.email;
  return me;
}

function initUitloggenLink() {
  const uitloggen = async (event) => {
    event.preventDefault();
    await fetch(`${API_BASIS}/logout`, { method: "POST", credentials: "same-origin" });
    window.location.href = "./login.html";
  };
  for (const id of ["uitloggen", "uitloggen-mobiel"]) {
    const link = document.getElementById(id);
    if (link) link.addEventListener("click", uitloggen);
  }
}

// Command palette (Ctrl/Cmd+K): snel van winkel wisselen zonder de muis —
// vooral waardevol met veel winkels, waar de kale <select> traag bladert.
function initCommandPalette() {
  const overlay = document.getElementById("palet-overlay");
  const invoer = document.getElementById("palet-zoek");
  const resultatenEl = document.getElementById("palet-resultaten");
  let actieveIndex = -1;

  function toonResultaten(zoekterm) {
    const term = zoekterm.trim().toLowerCase();
    const treffers = alleWinkelsCache
      .filter((w) => !term || String(w.extern_store_id).includes(term) || (w.naam || "").toLowerCase().includes(term))
      .slice(0, 20);
    actieveIndex = treffers.length > 0 ? 0 : -1;
    if (treffers.length === 0) {
      const leeg = document.createElement("p");
      leeg.className = "palet-leeg";
      leeg.textContent = "Geen winkel gevonden.";
      resultatenEl.replaceChildren(leeg);
      return;
    }
    resultatenEl.replaceChildren(...treffers.map((w, i) => {
      const item = document.createElement("div");
      item.className = "palet-item" + (i === 0 ? " actief" : "");
      item.textContent = w.naam || `Winkel ${w.extern_store_id}`;
      item.addEventListener("click", () => kiesWinkel(w.extern_store_id));
      return item;
    }));
  }

  function open() {
    overlay.hidden = false;
    invoer.value = "";
    toonResultaten("");
    invoer.focus();
  }
  function sluit() {
    overlay.hidden = true;
  }
  function kiesWinkel(storeId) {
    document.getElementById("store").value = String(storeId);
    sluit();
    voorspel();
  }

  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      open();
    } else if (event.key === "Escape" && !overlay.hidden) {
      sluit();
    }
  });
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) sluit();
  });
  invoer.addEventListener("input", () => toonResultaten(invoer.value));
  invoer.addEventListener("keydown", (event) => {
    const items = [...resultatenEl.querySelectorAll(".palet-item")];
    if (event.key === "ArrowDown") {
      event.preventDefault();
      actieveIndex = Math.min(actieveIndex + 1, items.length - 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      actieveIndex = Math.max(actieveIndex - 1, 0);
    } else if (event.key === "Enter" && items[actieveIndex]) {
      items[actieveIndex].click();
      return;
    } else {
      return;
    }
    items.forEach((el, i) => el.classList.toggle("actief", i === actieveIndex));
    items[actieveIndex]?.scrollIntoView({ block: "nearest" });
  });
}

function pasPremiumStatusToe(inProefperiode) {
  const promoVinkjes = document.getElementById("promo-vinkjes");
  if (promoVinkjes) {
    document.getElementById("promo-premium-badge").hidden = !inProefperiode;
    document.getElementById("promo-vinkje").disabled = inProefperiode;
    document.getElementById("vakantie-vinkje").disabled = inProefperiode;
    if (inProefperiode) promoVinkjes.setAttribute("data-premium-vergrendeld", "");
    else promoVinkjes.removeAttribute("data-premium-vergrendeld");
  }
  const exportKnoppen = document.getElementById("export-knoppen");
  if (exportKnoppen) {
    document.getElementById("export-premium-badge").hidden = !inProefperiode;
    document.getElementById("export-csv").disabled = inProefperiode;
    document.getElementById("export-png").disabled = inProefperiode;
    if (inProefperiode) exportKnoppen.setAttribute("data-premium-vergrendeld", "");
    else exportKnoppen.removeAttribute("data-premium-vergrendeld");
  }
  const scenarioInvoer = document.getElementById("scenario-invoer");
  if (scenarioInvoer) {
    document.getElementById("scenario-premium-badge").hidden = !inProefperiode;
    for (const id of ["scenario-a-promo", "scenario-a-vakantie", "scenario-b-promo", "scenario-b-vakantie", "vergelijk-knop"]) {
      document.getElementById(id).disabled = inProefperiode;
    }
    if (inProefperiode) scenarioInvoer.setAttribute("data-premium-vergrendeld", "");
    else scenarioInvoer.removeAttribute("data-premium-vergrendeld");
  }
}

function maakScenarioResultaatKaart(titel, voorspellingen) {
  const totaalP10 = voorspellingen.reduce((som, v) => som + Math.max(0, v.p10), 0);
  const totaalP50 = voorspellingen.reduce((som, v) => som + Math.max(0, v.p50), 0);
  const totaalP90 = voorspellingen.reduce((som, v) => som + Math.max(0, v.p90), 0);

  const kaart = document.createElement("div");
  kaart.className = "scenario-resultaat-kaart";
  const titelEl = document.createElement("p");
  titelEl.className = "titel";
  titelEl.textContent = titel;
  const waardeEl = document.createElement("p");
  waardeEl.className = "waarde";
  waardeEl.textContent = euro.format(Math.round(totaalP50));
  const bandEl = document.createElement("p");
  bandEl.className = "bandbreedte";
  bandEl.textContent = `Bandbreedte ${euro.format(Math.round(totaalP10))} – ${euro.format(Math.round(totaalP90))}`;
  kaart.append(titelEl, waardeEl, bandEl);
  return { kaart, totaalP50 };
}

async function vergelijkScenarios() {
  const knop = document.getElementById("vergelijk-knop");
  const foutEl = document.getElementById("scenario-fout");
  const storeId = Number(document.getElementById("store").value);
  const startDatum = document.getElementById("start").value;
  const horizonDagen = Number(document.getElementById("horizon").value);
  if (!storeId || !startDatum || !horizonDagen) {
    foutEl.textContent = "Kies eerst een winkel, startdatum en horizon hierboven.";
    foutEl.hidden = false;
    return;
  }
  const laatsteDag = dagenNa(startDatum, horizonDagen - 1);
  const scenarioParams = (prefix) => {
    const promo = document.getElementById(`${prefix}-promo`).checked;
    const vakantie = document.getElementById(`${prefix}-vakantie`).checked;
    return {
      promoVan: promo ? startDatum : "", promoTot: promo ? laatsteDag : "",
      vakantieVan: vakantie ? startDatum : "", vakantieTot: vakantie ? laatsteDag : "",
    };
  };

  knop.disabled = true;
  foutEl.hidden = true;
  try {
    const [dataA, dataB] = await Promise.all([
      haalVoorspelling(storeId, startDatum, horizonDagen, scenarioParams("scenario-a")),
      haalVoorspelling(storeId, startDatum, horizonDagen, scenarioParams("scenario-b")),
    ]);

    const resultaatEl = document.getElementById("scenario-resultaat");
    const { kaart: kaartA, totaalP50: totaalA } = maakScenarioResultaatKaart("Scenario A", dataA.voorspellingen);
    const { kaart: kaartB, totaalP50: totaalB } = maakScenarioResultaatKaart("Scenario B", dataB.voorspellingen);

    const verschilEl = document.createElement("p");
    verschilEl.className = "scenario-verschil";
    const verschil = Math.round(totaalA - totaalB);
    if (verschil === 0) {
      verschilEl.textContent = "Beide scenario's komen op ongeveer dezelfde verwachte omzet uit.";
    } else {
      const grootste = verschil > 0 ? "A" : "B";
      verschilEl.textContent = `Scenario ${grootste} levert naar verwachting ${euro.format(Math.abs(verschil))} meer op dan het andere scenario.`;
    }

    resultaatEl.replaceChildren(kaartA, kaartB, verschilEl);
    resultaatEl.hidden = false;
  } catch (e) {
    foutEl.textContent = e.message;
    foutEl.hidden = false;
  } finally {
    knop.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const me = await initToegang();
  if (!me) return;
  initUitloggenLink();
  pasPremiumStatusToe(me.in_proefperiode);
  initPortfolioSidebar(me);

  const knop = document.getElementById("voorspel");
  document.addEventListener("click", sluitAndereInfoKnopjes);
  initInfoKnopjes();
  document.getElementById("start").value = vandaagPlusEen();
  knop.addEventListener("click", voorspel);
  document.getElementById("vergelijk-knop").addEventListener("click", vergelijkScenarios);

  let winkels;
  try {
    winkels = await laadWinkels();
  } catch (e) {
    toonFout(e.message);
    return;
  }
  if (winkels.length === 0) {
    // "Geen winkels" betekent voor een lid vaak iets anders dan voor een
    // eigenaar: een eigenaar ziet altijd de volledige organisatie (dus
    // leeg = de organisatie heeft écht nog geen winkels), terwijl een lid
    // met een lege toewijzing gewoon nog niet is ingesteld door de
    // eigenaar — een normale, verwachte tussenstap na het toevoegen van
    // een teamlid, geen organisatiebreed probleem.
    document.getElementById("leeg").textContent = me.rol === "lid"
      ? "Er zijn nog geen winkels aan jou toegewezen. Vraag de eigenaar van je organisatie om dit in te stellen via Team beheren."
      : "Er zijn nog geen winkels aan jouw organisatie gekoppeld. Neem contact op om dit in te laten stellen.";
    return;
  }
  alleWinkelsCache = winkels;
  initCommandPalette();

  // Opgeslagen weergave: een gedeelde/gebookmarkte URL (of een drill-down
  // vanuit overview.html met ?winkel=<id>) vult vooraf de velden en
  // voorspelt meteen, zodat een klik op zo'n link direct bij het juiste
  // resultaat uitkomt i.p.v. bij een leeg formulier.
  const urlParams = new URLSearchParams(window.location.search);
  const heeftOpgeslagenWeergave = pasUrlParamsToe(winkels, urlParams);

  // Knop blijft uit tot /metrics geladen is: anders kan een snelle klik een
  // voorspelling opvragen met de kalenderdatum van vandaag in plaats van een
  // datum die bij de trainingsperiode van het model past, zonder dat de
  // gebruiker iets fout ziet gaan.
  laadMetrics()
    .then((data) => {
      // Alleen de trainingsperiode-standaard toepassen als de URL zelf
      // geen startdatum opgaf — anders overschrijft dit een opgeslagen
      // weergave stilzwijgend met een andere datum.
      if (!urlParams.get("start")) {
        document.getElementById("start").value = eenDagNa(data.trainingsperiode_eind);
      }
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
      if (heeftOpgeslagenWeergave) voorspel();
    });

  document.getElementById("export-csv").addEventListener("click", exporteerCsv);
  document.getElementById("export-png").addEventListener("click", exporteerPng);
});
