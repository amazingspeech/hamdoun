"use strict";

// Configureerbaar API-adres: lokaal same-origin (de FastAPI-app serveert dit
// dashboard zelf onder dezelfde origin), later het live adres van de
// forecasting-API zodra dit dashboard op de Tessar-website staat — dan wordt
// TESSAR_FORECAST_API_BASIS vóór het laden van dit script gezet.
const API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";
const API_KEY = window.TESSAR_FORECAST_API_KEY || "";

const WINKEL_IDS = [1, 2, 3, 4, 5, 10, 25, 50, 100, 250];

let modelMetrics = null;

const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency", currency: "EUR", maximumFractionDigits: 0,
});

function formatDatumKort(isoDatum) {
  const d = new Date(isoDatum + "T00:00:00");
  return d.toLocaleDateString("nl-NL", { day: "numeric", month: "short" });
}

function vulWinkelSelect() {
  const select = document.getElementById("store");
  for (const id of WINKEL_IDS) {
    const optie = document.createElement("option");
    optie.value = String(id);
    optie.textContent = `Winkel ${id}`;
    select.appendChild(optie);
  }
}

function toonFout(bericht) {
  const el = document.getElementById("fout");
  el.textContent = bericht;
  el.hidden = !bericht;
}

async function laadMetrics() {
  const resp = await fetch(`${API_BASIS}/metrics`, { headers: { "X-API-Key": API_KEY } });
  if (!resp.ok) throw new Error(`Kon nauwkeurigheidscijfers niet ophalen (${resp.status})`);
  const data = await resp.json();
  modelMetrics = data;

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

async function haalVoorspelling(storeId, startDatum, horizonDagen) {
  const resp = await fetch(`${API_BASIS}/forecast`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify({ store_id: storeId, start_datum: startDatum, horizon_dagen: horizonDagen }),
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
  svg.appendChild(maakSVGEl("polyline", { class: "lijn", points: lijnPunten }));
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
}

function maakKaart(label, waarde, toelichting, hoofdKaart) {
  const kaart = document.createElement("div");
  kaart.className = hoofdKaart ? "kaart hoofd" : "kaart";
  const labelEl = document.createElement("div");
  labelEl.className = "label";
  labelEl.textContent = label;
  const waardeEl = document.createElement("div");
  waardeEl.className = "waarde";
  waardeEl.textContent = waarde;
  const toelichtingEl = document.createElement("div");
  toelichtingEl.className = "toelichting";
  toelichtingEl.textContent = toelichting;
  kaart.append(labelEl, waardeEl, toelichtingEl);
  return kaart;
}

function toonSamenvatting(voorspellingen, storeId) {
  const totaalP50 = voorspellingen.reduce((som, v) => som + v.p50, 0);
  const totaalP10 = voorspellingen.reduce((som, v) => som + v.p10, 0);
  const totaalP90 = voorspellingen.reduce((som, v) => som + v.p90, 0);
  const n = voorspellingen.length;
  const dagLabel = n === 1 ? "1 dag" : `${n} dagen`;
  const betrouwbaarheid = modelMetrics ? Math.round(modelMetrics.coverage_p10_p90 * 100) : null;

  const container = document.getElementById("samenvatting");
  container.innerHTML = "";
  container.appendChild(maakKaart(
    `Verwachte omzet — komende ${dagLabel}`,
    euro.format(Math.round(totaalP50)),
    `Winkel ${storeId}, van ${formatDatumKort(voorspellingen[0].datum)} t/m ${formatDatumKort(voorspellingen[n - 1].datum)}.`,
    true,
  ));
  container.appendChild(maakKaart(
    "Meest waarschijnlijke bandbreedte",
    `${euro.format(Math.round(totaalP10))} – ${euro.format(Math.round(totaalP90))}`,
    betrouwbaarheid !== null
      ? `De werkelijke omzet valt hier historisch in ongeveer ${betrouwbaarheid}% van de gevallen binnen.`
      : "De omzet ligt hier meestal binnen.",
    false,
  ));
  container.appendChild(maakKaart(
    "Gemiddeld per dag",
    euro.format(Math.round(totaalP50 / n)),
    "Gebaseerd op vergelijkbare dagen uit het verleden.",
    false,
  ));

  document.getElementById("chart-titel").textContent =
    `Winkel ${storeId} — dagelijkse omzet, ${formatDatumKort(voorspellingen[0].datum)} t/m ${formatDatumKort(voorspellingen[n - 1].datum)}`;
}

async function voorspel() {
  const knop = document.getElementById("voorspel");
  knop.disabled = true;
  toonFout("");
  try {
    const storeId = Number(document.getElementById("store").value);
    const startDatum = document.getElementById("start").value;
    const horizonDagen = Number(document.getElementById("horizon").value);
    const data = await haalVoorspelling(storeId, startDatum, horizonDagen);
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

document.addEventListener("DOMContentLoaded", () => {
  const knop = document.getElementById("voorspel");
  vulWinkelSelect();
  document.getElementById("start").value = vandaagPlusEen();
  knop.addEventListener("click", voorspel);

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
