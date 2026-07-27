"use strict";

const API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";
const PAGINA_GROOTTE = 50;
const HORIZON_DAGEN = 7;

let alleWinkels = [];
let volgendeOffset = 0;
let totaalWinkels = 0;
let modelNauwkeurigheidRmspe = null;
let sorteerVeld = null;
let sorteerRichting = -1;

const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency", currency: "EUR", maximumFractionDigits: 0,
});

function toonFout(bericht) {
  const el = document.getElementById("fout");
  el.textContent = bericht;
  el.hidden = !bericht;
}

async function haalMe() {
  const resp = await fetch(`${API_BASIS}/me`, { credentials: "same-origin" });
  if (!resp.ok) return null;
  return resp.json();
}

async function haalPortfolioPagina(offset) {
  const resp = await fetch(
    `${API_BASIS}/portfolio?horizon_dagen=${HORIZON_DAGEN}&limiet=${PAGINA_GROOTTE}&offset=${offset}`,
    { credentials: "same-origin" },
  );
  if (!resp.ok) throw new Error(`Kon het overzicht niet ophalen (${resp.status})`);
  return resp.json();
}

function maakSparklineSvg(reeks) {
  const breedte = 90, hoogte = 26;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(breedte));
  svg.setAttribute("height", String(hoogte));
  svg.setAttribute("class", "sparkline");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Verwacht verloop over de periode");
  if (reeks.length < 2) return svg;

  const min = Math.min(...reeks), max = Math.max(...reeks);
  const spreiding = max - min || 1;
  const x = (i) => (i / (reeks.length - 1)) * (breedte - 4) + 2;
  const y = (v) => hoogte - 3 - ((v - min) / spreiding) * (hoogte - 6);

  const lijn = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  lijn.setAttribute("points", reeks.map((v, i) => `${x(i)},${y(v)}`).join(" "));
  lijn.setAttribute("class", "sparkline-lijn");
  svg.appendChild(lijn);

  const laatste = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  laatste.setAttribute("cx", String(x(reeks.length - 1)));
  laatste.setAttribute("cy", String(y(reeks[reeks.length - 1])));
  laatste.setAttribute("r", "2");
  laatste.setAttribute("class", "sparkline-stip");
  svg.appendChild(laatste);

  return svg;
}

function maakRij(winkel) {
  const tr = document.createElement("tr");

  const naamTd = document.createElement("td");
  const link = document.createElement("a");
  link.href = `./index.html?winkel=${winkel.extern_store_id}`;
  link.textContent = winkel.naam || `Winkel ${winkel.extern_store_id}`;
  naamTd.appendChild(link);
  if (winkel.afwijkend) {
    const badge = document.createElement("span");
    badge.className = "afwijkend-badge";
    badge.textContent = "Wijkt af van gebruikelijk patroon";
    naamTd.appendChild(badge);
  }

  const omzetTd = document.createElement("td");
  omzetTd.className = "cijfer";
  omzetTd.textContent = euro.format(Math.max(0, Math.round(winkel.totaal_p50)));

  const trendTd = document.createElement("td");
  trendTd.appendChild(maakSparklineSvg(winkel.sparkline));

  tr.append(naamTd, omzetTd, trendTd);
  return tr;
}

function toonKpis() {
  const el = document.getElementById("portfolio-kpis");
  el.replaceChildren();
  const totaleOmzet = alleWinkels.reduce((som, w) => som + Math.max(0, w.totaal_p50), 0);
  const aantalAfwijkend = alleWinkels.filter((w) => w.afwijkend).length;
  const omvangTekst = alleWinkels.length < totaalWinkels
    ? `Over de ${alleWinkels.length} van ${totaalWinkels} geladen winkels.`
    : `Over alle ${totaalWinkels} winkels.`;

  const items = [
    ["Verwachte omzet", euro.format(Math.round(totaleOmzet)), `Komende ${HORIZON_DAGEN} dagen. ${omvangTekst}`],
    [
      "Modelnauwkeurigheid", (modelNauwkeurigheidRmspe * 100).toFixed(1) + "%",
      "Gemiddelde afwijking tussen voorspelde en werkelijke omzet, gemeten op historische data.",
    ],
    ["Afwijkende winkels", String(aantalAfwijkend), "Voorspelling wijkt sterk af van het eigen historische patroon van die winkel."],
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
    el.appendChild(kaart);
  }
}

function tekenTabel() {
  const zoekterm = document.getElementById("zoeken").value.trim().toLowerCase();
  let getoond = alleWinkels.filter((w) =>
    !zoekterm || String(w.extern_store_id).includes(zoekterm) || (w.naam || "").toLowerCase().includes(zoekterm)
  );
  if (sorteerVeld) {
    getoond = [...getoond].sort((a, b) => (a[sorteerVeld] - b[sorteerVeld]) * sorteerRichting);
  }
  document.getElementById("portfolio-rijen").replaceChildren(...getoond.map(maakRij));
}

async function laadMeer() {
  const knop = document.getElementById("meer-laden");
  knop.disabled = true;
  toonFout("");
  try {
    const data = await haalPortfolioPagina(volgendeOffset);
    alleWinkels = alleWinkels.concat(data.winkels);
    volgendeOffset += data.winkels.length;
    totaalWinkels = data.totaal_winkels;
    modelNauwkeurigheidRmspe = data.kpi.model_nauwkeurigheid_rmspe;
    toonKpis();
    tekenTabel();
    knop.hidden = volgendeOffset >= totaalWinkels || data.winkels.length === 0;
  } catch (e) {
    toonFout(e.message);
  } finally {
    knop.disabled = false;
  }
}

function initSortering() {
  for (const th of document.querySelectorAll("[data-sorteer]")) {
    th.addEventListener("click", () => {
      const veld = th.dataset.sorteer;
      sorteerRichting = sorteerVeld === veld ? sorteerRichting * -1 : -1;
      sorteerVeld = veld;
      tekenTabel();
    });
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const me = await haalMe();
  if (!me) {
    window.location.href = "./login.html";
    return;
  }
  document.getElementById("wie-ben-ik").textContent = `Ingelogd als ${me.email}`;

  document.getElementById("uitloggen").addEventListener("click", async (event) => {
    event.preventDefault();
    await fetch(`${API_BASIS}/logout`, { method: "POST", credentials: "same-origin" });
    window.location.href = "./login.html";
  });

  document.getElementById("zoeken").addEventListener("input", tekenTabel);
  initSortering();
  document.getElementById("meer-laden").addEventListener("click", laadMeer);

  await laadMeer();
});
