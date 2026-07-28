"use strict";

// Gedeeld door alle drie de pagina's met een .portfolio-shell-zijbalk
// (overview.html, index.html, team.html) — zelfde laadvolgorde als
// sidebar.js: config.js, sidebar.js, onboarding.js, dan het pagina-eigen
// script. Bewust een apart, zelfstandig bestand i.p.v. functies aan
// sidebar.js toevoegen: dit gaat over een tijdelijke, per-organisatie
// aan/uit-staande onboarding-fase, niet over permanente zijbalk-chrome.
//
// Let op: alle scripts op een pagina delen één globale scope (geen ES
// modules) — dashboard.js, overview.js en account.js declareren elk al
// hun eigen top-level "const euro". Daarom hier alles prefixen met
// "onboarding"/"ONBOARDING_", zelfde patroon als sidebar.js met
// SIDEBAR_API_BASIS/sidebarSleutel.
const ONBOARDING_API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";

function onboardingFormatEuro(bedrag) {
  return new Intl.NumberFormat("nl-NL", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(bedrag);
}

function onboardingSleutel(organisatieId) {
  return `vraagvoorspelling_onboarding_verborgen_org${organisatieId}`;
}

async function haalOnboardingStatus() {
  const [verkoopdataResp, instellingenResp] = await Promise.all([
    fetch(`${ONBOARDING_API_BASIS}/organisatie/verkoopdata`, { credentials: "same-origin" }),
    fetch(`${ONBOARDING_API_BASIS}/organisatie/instellingen`, { credentials: "same-origin" }),
  ]);
  if (!verkoopdataResp.ok || !instellingenResp.ok) throw new Error("Kon onboarding-status niet ophalen");
  const verkoopdata = await verkoopdataResp.json();
  const instellingen = await instellingenResp.json();
  return {
    verkoopdataGeupload: verkoopdata.rijen.length > 0,
    prijsIngesteld: instellingen.gemiddelde_omzet_per_stuk !== null,
  };
}

function toonOnboardingChecklist(status, organisatieId) {
  const kaart = document.getElementById("onboarding-checklist");
  if (!kaart) return;

  const volledig = status.verkoopdataGeupload && status.prijsIngesteld;
  if (volledig) {
    kaart.hidden = true;
    return;
  }
  if (localStorage.getItem(onboardingSleutel(organisatieId)) === "verborgen") {
    kaart.hidden = true;
    return;
  }

  const items = [
    ["Upload je verkoopdata", status.verkoopdataGeupload, "./team.html"],
    ["Stel je herbestel-prijs in", status.prijsIngesteld, "./team.html"],
  ];
  const lijst = document.createElement("ul");
  lijst.className = "onboarding-lijst";
  for (const [label, klaar, link] of items) {
    const li = document.createElement("li");
    li.className = klaar ? "onboarding-item afgerond" : "onboarding-item";
    if (klaar) {
      li.textContent = `✓ ${label}`;
    } else {
      const a = document.createElement("a");
      a.href = link;
      a.textContent = label;
      li.appendChild(a);
    }
    lijst.appendChild(li);
  }

  const verbergKnop = document.createElement("button");
  verbergKnop.type = "button";
  verbergKnop.className = "onboarding-verbergen";
  verbergKnop.textContent = "Verbergen";
  verbergKnop.addEventListener("click", () => {
    localStorage.setItem(onboardingSleutel(organisatieId), "verborgen");
    kaart.hidden = true;
  });

  const titel = document.createElement("p");
  titel.className = "onboarding-titel";
  titel.textContent = "Aan de slag";

  kaart.replaceChildren(titel, lijst, verbergKnop);
  kaart.hidden = false;
}

async function initOnboarding(me) {
  // Een "lid" zonder toegewezen winkels zit in een heel andere situatie
  // dan een zelfbediening-organisatie zonder eigen data — de organisatie
  // zelf heeft dan gewoon al winkels, alleen is dit specifieke teamlid er
  // nog niet aan gekoppeld. Zelfde eigenaar/lid-redenering als het
  // bestaande "geen winkels"-bericht in dashboard.js.
  if (me.rol === "lid") return;
  try {
    const winkelsResp = await fetch(`${ONBOARDING_API_BASIS}/winkels`, { credentials: "same-origin" });
    if (!winkelsResp.ok) return;
    const winkels = await winkelsResp.json();
    if (winkels.length > 0) return;
    const status = await haalOnboardingStatus();
    toonOnboardingChecklist(status, me.organisatie_id);
  } catch (e) {
    // Stille fout, zelfde reden als sidebar.js's KPI-aanroep: een
    // mislukte onboarding-checklist mag de rest van de pagina niet
    // verstoren.
  }
}
