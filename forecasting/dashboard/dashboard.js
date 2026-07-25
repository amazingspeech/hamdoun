"use strict";

// Configureerbaar API-adres: lokaal same-origin (de FastAPI-app serveert dit
// dashboard zelf onder dezelfde origin), later het live adres van de
// forecasting-API zodra dit dashboard op de Tessar-website staat — dan wordt
// TESSAR_FORECAST_API_BASIS vóór het laden van dit script gezet.
const API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";
const API_KEY = window.TESSAR_FORECAST_API_KEY || "";

const WINKEL_IDS = [1, 2, 3, 4, 5, 10, 25, 50, 100, 250];

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
  const container = document.getElementById("metrics");
  container.innerHTML = "";
  const items = [
    ["RMSPE", (data.rmspe * 100).toFixed(1) + "%"],
    ["Dekking p10–p90-band", (data.coverage_p10_p90 * 100).toFixed(0) + "%"],
    ["Modelversie", data.model_versie],
  ];
  for (const [label, waarde] of items) {
    const kaart = document.createElement("div");
    kaart.className = "metric";
    const labelEl = document.createElement("div");
    labelEl.className = "label";
    labelEl.textContent = label;
    const waardeEl = document.createElement("div");
    waardeEl.className = "value";
    waardeEl.textContent = waarde;
    kaart.append(labelEl, waardeEl);
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

function tekenGrafiek(voorspellingen) {
  const svg = document.getElementById("chart");
  const breedte = 920, hoogte = 360, marge = { boven: 20, rechts: 20, onder: 30, links: 50 };
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

  svg.innerHTML = `
    <polygon class="band" points="${bandPunten}"></polygon>
    <polyline class="lijn" points="${lijnPunten}"></polyline>
    <line class="as" x1="${marge.links}" y1="${marge.boven}" x2="${marge.links}" y2="${hoogte - marge.onder}"></line>
    <line class="as" x1="${marge.links}" y1="${hoogte - marge.onder}" x2="${breedte - marge.rechts}" y2="${hoogte - marge.onder}"></line>
  `;
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
    tekenGrafiek(data.voorspellingen);
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

document.addEventListener("DOMContentLoaded", () => {
  vulWinkelSelect();
  document.getElementById("start").value = vandaagPlusEen();
  document.getElementById("voorspel").addEventListener("click", voorspel);
  laadMetrics().catch((e) => toonFout(e.message));
});
