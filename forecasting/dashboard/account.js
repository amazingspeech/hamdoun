"use strict";

const API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";
const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency", currency: "EUR", maximumFractionDigits: 0,
});

function toonFout(elId, bericht) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.textContent = bericht;
  el.hidden = !bericht;
}

async function login(email, wachtwoord) {
  const resp = await fetch(`${API_BASIS}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ email, wachtwoord }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Inloggen mislukt (${resp.status})`);
  }
}

async function haalMe() {
  const resp = await fetch(`${API_BASIS}/me`, { credentials: "same-origin" });
  if (!resp.ok) return null;
  return resp.json();
}

async function haalTeam() {
  const resp = await fetch(`${API_BASIS}/gebruikers`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon het team niet ophalen (${resp.status})`);
  return resp.json();
}

async function voegLidToe(email, wachtwoord) {
  const resp = await fetch(`${API_BASIS}/gebruikers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ email, wachtwoord }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Toevoegen mislukt (${resp.status})`);
  }
  return resp.json();
}

async function logout() {
  await fetch(`${API_BASIS}/logout`, { method: "POST", credentials: "same-origin" });
}

async function meldAan(organisatieNaam, email, wachtwoord, kvkNummer, aantalLeden, aantalWinkels) {
  const resp = await fetch(`${API_BASIS}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      organisatie_naam: organisatieNaam, email, wachtwoord,
      kvk_nummer: kvkNummer, aantal_leden: aantalLeden, aantal_winkels: aantalWinkels,
    }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Aanmelden mislukt (${resp.status})`);
  }
  return resp.json();
}

function initSignupPagina() {
  const form = document.getElementById("signup-form");
  if (!form) return;

  const werkPrijsPreviewBij = () => {
    const ledenEl = document.getElementById("aantal-leden");
    const winkelsEl = document.getElementById("aantal-winkels");
    const previewEl = document.getElementById("prijs-preview");
    if (!ledenEl || !winkelsEl || !previewEl) return;
    const leden = Math.max(1, parseInt(ledenEl.value, 10) || 1);
    const winkels = Math.max(1, parseInt(winkelsEl.value, 10) || 1);
    const totaal = 29 + (leden - 1) * 5 + (winkels - 1) * 10;
    previewEl.textContent = `Totaal: ${euro.format(totaal)} per maand`;
  };
  document.getElementById("aantal-leden")?.addEventListener("input", werkPrijsPreviewBij);
  document.getElementById("aantal-winkels")?.addEventListener("input", werkPrijsPreviewBij);
  werkPrijsPreviewBij();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("signup-knop");
    knop.disabled = true;
    toonFout("fout", "");
    try {
      const { checkout_url: checkoutUrl } = await meldAan(
        document.getElementById("organisatie-naam").value,
        document.getElementById("email").value,
        document.getElementById("wachtwoord").value,
        document.getElementById("kvk-nummer").value,
        parseInt(document.getElementById("aantal-leden").value, 10) || 1,
        parseInt(document.getElementById("aantal-winkels").value, 10) || 1,
      );
      window.location.href = checkoutUrl;
    } catch (e) {
      toonFout("fout", e.message);
      knop.disabled = false;
    }
  });
}

async function vraagWachtwoordResetAan(email) {
  const resp = await fetch(`${API_BASIS}/wachtwoord-reset/aanvragen`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ email }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Aanvragen mislukt (${resp.status})`);
  }
}

async function voltooiWachtwoordReset(token, nieuwWachtwoord) {
  const resp = await fetch(`${API_BASIS}/wachtwoord-reset/voltooien`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ token, nieuw_wachtwoord: nieuwWachtwoord }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Instellen mislukt (${resp.status})`);
  }
}

function initWachtwoordVergetenPagina() {
  const form = document.getElementById("wachtwoord-vergeten-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("wachtwoord-vergeten-knop");
    const emailVeld = document.getElementById("email");
    knop.disabled = true;
    // Altijd dezelfde melding tonen, ongeacht of het versturen lukte —
    // het backend-endpoint lekt zelf ook nooit of een e-mailadres bestaat
    // (zie serving/app.py), dus de UI mag dat niet alsnog via een aparte
    // foutmelding verraden.
    await vraagWachtwoordResetAan(emailVeld.value).catch(() => {});
    const melding = document.getElementById("melding");
    melding.textContent = "Als dit e-mailadres bekend is, ontvang je een link om je wachtwoord te resetten.";
    melding.hidden = false;
    emailVeld.disabled = true;
  });
}

function initWachtwoordResettenPagina() {
  const form = document.getElementById("wachtwoord-resetten-form");
  if (!form) return;
  const token = new URLSearchParams(window.location.search).get("token");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("wachtwoord-resetten-knop");
    knop.disabled = true;
    toonFout("fout", "");
    try {
      if (!token) throw new Error("Ongeldige of onvolledige reset-link.");
      await voltooiWachtwoordReset(token, document.getElementById("nieuw-wachtwoord").value);
      window.location.href = "./login.html";
    } catch (e) {
      toonFout("fout", e.message);
      knop.disabled = false;
    }
  });
}

function initLoginPagina() {
  const form = document.getElementById("login-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("login-knop");
    knop.disabled = true;
    toonFout("fout", "");
    try {
      await login(document.getElementById("email").value, document.getElementById("wachtwoord").value);
      window.location.href = "./team.html";
    } catch (e) {
      toonFout("fout", e.message);
      knop.disabled = false;
    }
  });
}

async function haalWinkels() {
  const resp = await fetch(`${API_BASIS}/winkels`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon winkels niet ophalen (${resp.status})`);
  return resp.json();
}

async function haalWinkeltoewijzing(lidId) {
  const resp = await fetch(`${API_BASIS}/gebruikers/${lidId}/winkels`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon winkeltoewijzing niet ophalen (${resp.status})`);
  return resp.json();
}

async function stelWinkeltoewijzingIn(lidId, winkelIds) {
  const resp = await fetch(`${API_BASIS}/gebruikers/${lidId}/winkels`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ winkel_ids: winkelIds }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Opslaan mislukt (${resp.status})`);
  }
  return resp.json();
}

async function vulWinkeltoewijzing(container, lidId, alleWinkels) {
  const status = document.createElement("p");
  status.className = "sub";
  status.textContent = "Bezig met laden…";
  container.replaceChildren(status);

  let toegewezen;
  try {
    toegewezen = new Set((await haalWinkeltoewijzing(lidId)).winkel_ids);
  } catch (e) {
    status.textContent = e.message;
    return;
  }

  if (alleWinkels.length === 0) {
    status.textContent = "Deze organisatie heeft nog geen winkels.";
    return;
  }

  const lijst = document.createElement("div");
  lijst.className = "winkeltoewijzing-lijst";
  for (const winkel of alleWinkels) {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = String(winkel.extern_store_id);
    checkbox.checked = toegewezen.has(winkel.extern_store_id);
    label.append(checkbox, document.createTextNode(winkel.naam || `Winkel ${winkel.extern_store_id}`));
    lijst.appendChild(label);
  }

  const opslaanRij = document.createElement("div");
  opslaanRij.className = "winkeltoewijzing-opslaan";
  const opslaanKnop = document.createElement("button");
  opslaanKnop.type = "button";
  opslaanKnop.className = "btn zacht";
  opslaanKnop.textContent = "Opslaan";
  const melding = document.createElement("span");
  melding.className = "sub";

  opslaanKnop.addEventListener("click", async () => {
    opslaanKnop.disabled = true;
    melding.textContent = "";
    const winkelIds = [...lijst.querySelectorAll("input:checked")].map((el) => Number(el.value));
    try {
      await stelWinkeltoewijzingIn(lidId, winkelIds);
      melding.textContent = "Opgeslagen.";
    } catch (e) {
      melding.textContent = e.message;
    } finally {
      opslaanKnop.disabled = false;
    }
  });

  opslaanRij.append(opslaanKnop, melding);
  container.replaceChildren(lijst, opslaanRij);
}

function maakTeamlidEl(lid, kanBeheren, alleWinkels) {
  const rij = document.createElement("div");
  rij.className = "teamlid";
  const email = document.createElement("span");
  email.className = "email";
  email.textContent = lid.email;
  const rol = document.createElement("span");
  rol.className = "rol";
  rol.textContent = lid.rol;
  rij.append(email, rol);

  if (!kanBeheren || lid.rol !== "lid") return [rij];

  if (lid.actief) {
    const verwijderKnop = document.createElement("button");
    verwijderKnop.type = "button";
    verwijderKnop.className = "btn zacht";
    verwijderKnop.textContent = "Verwijderen";
    verwijderKnop.addEventListener("click", async () => {
      verwijderKnop.disabled = true;
      try {
        await verwijderTeamlid(lid.id);
        await verversTeamlijst(kanBeheren, alleWinkels);
      } catch (e) {
        toonFout("fout", e.message);
        verwijderKnop.disabled = false;
      }
    });
    rij.append(verwijderKnop);
  } else {
    rol.textContent = "verwijderd";
  }

  if (!lid.actief) return [rij];

  const details = document.createElement("details");
  details.className = "winkeltoewijzing";
  const summary = document.createElement("summary");
  summary.textContent = "Winkels beheren";
  const inhoud = document.createElement("div");
  inhoud.className = "winkeltoewijzing-inhoud";
  details.append(summary, inhoud);

  details.addEventListener("toggle", async () => {
    if (!details.open || inhoud.dataset.geladen) return;
    inhoud.dataset.geladen = "1";
    await vulWinkeltoewijzing(inhoud, lid.id, alleWinkels);
  });

  return [rij, details];
}

async function verversTeamlijst(kanBeheren, alleWinkels) {
  const teamEl = document.getElementById("teamlijst");
  const team = await haalTeam();
  teamEl.replaceChildren(...team.flatMap((lid) => maakTeamlidEl(lid, kanBeheren, alleWinkels)));
}

function initNieuwLidForm(kanBeheren, alleWinkels) {
  const form = document.getElementById("nieuw-lid-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("nieuw-lid-knop");
    knop.disabled = true;
    toonFout("nieuw-lid-fout", "");
    try {
      await voegLidToe(document.getElementById("nieuw-email").value, document.getElementById("nieuw-wachtwoord").value);
      document.getElementById("nieuw-email").value = "";
      document.getElementById("nieuw-wachtwoord").value = "";
      await verversTeamlijst(kanBeheren, alleWinkels);
    } catch (e) {
      toonFout("nieuw-lid-fout", e.message);
    } finally {
      knop.disabled = false;
    }
  });
}

function initUitloggenLink() {
  const uitloggen = async (event) => {
    event.preventDefault();
    await logout();
    window.location.href = "./login.html";
  };
  for (const id of ["uitloggen", "uitloggen-mobiel"]) {
    const link = document.getElementById(id);
    if (link) link.addEventListener("click", uitloggen);
  }
}

async function haalOrganisatieInstellingen() {
  const resp = await fetch(`${API_BASIS}/organisatie/instellingen`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon instellingen niet ophalen (${resp.status})`);
  return resp.json();
}

async function stelGemiddeldeOmzetPerStukIn(bedrag) {
  const resp = await fetch(`${API_BASIS}/organisatie/instellingen`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ gemiddelde_omzet_per_stuk: bedrag }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Opslaan mislukt (${resp.status})`);
  }
  return resp.json();
}

function initHerbestelForm() {
  const form = document.getElementById("herbestel-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("herbestel-knop");
    knop.disabled = true;
    toonFout("herbestel-fout", "");
    document.getElementById("herbestel-melding").hidden = true;
    try {
      const bedrag = Number(document.getElementById("herbestel-prijs").value);
      await stelGemiddeldeOmzetPerStukIn(bedrag);
      const melding = document.getElementById("herbestel-melding");
      melding.textContent = "Opgeslagen.";
      melding.hidden = false;
      // Deze prijs voedt uitsluitend het herbestel-advies op het echte
      // /forecast (index.html/dashboard.js) — dat heeft hier geen
      // rechtstreeks zichtbaar effect op deze pagina, dus geen lokale
      // kaart om na te verversen (in tegenstelling tot de per-eigen-
      // winkel prijs, zie stelEigenWinkelPrijsIn()).
    } catch (e) {
      toonFout("herbestel-fout", e.message);
    } finally {
      knop.disabled = false;
    }
  });
}

async function haalEigenWinkels() {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon eigen winkels niet ophalen (${resp.status})`);
  return resp.json();
}

async function maakEigenWinkel(naam) {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ naam }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Aanmaken mislukt (${resp.status})`);
  }
  return resp.json();
}

async function hernoemEigenWinkel(id, naam) {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ naam }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Hernoemen mislukt (${resp.status})`);
  }
  return resp.json();
}

async function verwijderEigenWinkel(id) {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels/${id}`, { method: "DELETE", credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Verwijderen mislukt (${resp.status})`);
}

async function stelEigenWinkelPrijsIn(id, bedrag) {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-winkels/${id}/instellingen`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ gemiddelde_omzet_per_stuk: bedrag }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Opslaan mislukt (${resp.status})`);
  }
  return resp.json();
}

function maakEigenWinkelEl(winkel, opGewijzigd) {
  const rij = document.createElement("div");
  rij.className = "teamlid";

  const naam = document.createElement("span");
  naam.className = "email";
  naam.textContent = winkel.naam;

  const rechts = document.createElement("span");
  rechts.className = "rechts";

  const prijsVeld = document.createElement("input");
  prijsVeld.type = "number";
  prijsVeld.min = "0.01";
  prijsVeld.step = "0.01";
  prijsVeld.style.width = "90px";
  prijsVeld.placeholder = winkel.automatische_prijs_per_stuk !== null
    ? `auto: €${winkel.automatische_prijs_per_stuk.toFixed(2)}` : "prijs/stuk";
  if (winkel.gemiddelde_omzet_per_stuk !== null) prijsVeld.value = winkel.gemiddelde_omzet_per_stuk;
  const prijsKnop = document.createElement("button");
  prijsKnop.type = "button";
  prijsKnop.className = "btn zacht";
  prijsKnop.textContent = "Opslaan";
  prijsKnop.addEventListener("click", async () => {
    prijsKnop.disabled = true;
    try {
      await stelEigenWinkelPrijsIn(winkel.id, Number(prijsVeld.value));
      await opGewijzigd();
    } catch (e) {
      toonFout("eigen-winkel-aanmaken-fout", e.message);
    } finally {
      prijsKnop.disabled = false;
    }
  });

  const hernoemKnop = document.createElement("button");
  hernoemKnop.type = "button";
  hernoemKnop.className = "btn zacht";
  hernoemKnop.textContent = "Hernoemen";
  hernoemKnop.addEventListener("click", async () => {
    const nieuweNaam = window.prompt("Nieuwe naam:", winkel.naam);
    if (!nieuweNaam || nieuweNaam === winkel.naam) return;
    try {
      await hernoemEigenWinkel(winkel.id, nieuweNaam);
      await opGewijzigd();
    } catch (e) {
      toonFout("eigen-winkel-aanmaken-fout", e.message);
    }
  });

  const verwijderKnop = document.createElement("button");
  verwijderKnop.type = "button";
  verwijderKnop.className = "btn zacht";
  verwijderKnop.textContent = "Verwijderen";
  verwijderKnop.addEventListener("click", async () => {
    if (!window.confirm(`"${winkel.naam}" en al zijn geüploade verkoopdata verwijderen? Dit kan niet ongedaan worden gemaakt.`)) return;
    verwijderKnop.disabled = true;
    try {
      await verwijderEigenWinkel(winkel.id);
      await opGewijzigd();
    } catch (e) {
      toonFout("eigen-winkel-aanmaken-fout", e.message);
      verwijderKnop.disabled = false;
    }
  });

  rechts.append(prijsVeld, prijsKnop, hernoemKnop, verwijderKnop);
  rij.append(naam, rechts);
  return rij;
}

let alleEigenWinkels = [];

function vulEigenWinkelSelects(winkels) {
  for (const selectId of ["verkoopdata-eigen-winkel", "product-verkoopdata-eigen-winkel"]) {
    const select = document.getElementById(selectId);
    if (!select) continue;
    const huidige = select.value;
    select.replaceChildren(...winkels.map((w) => {
      const optie = document.createElement("option");
      optie.value = String(w.id);
      optie.textContent = w.naam;
      return optie;
    }));
    if (winkels.some((w) => String(w.id) === huidige)) select.value = huidige;
    select.disabled = winkels.length === 0;
  }
  const verkoopdataKnop = document.getElementById("verkoopdata-knop");
  const productKnop = document.getElementById("product-verkoopdata-knop");
  if (verkoopdataKnop) verkoopdataKnop.disabled = winkels.length === 0;
  if (productKnop) productKnop.disabled = winkels.length === 0;
}

async function verversEigenWinkelsKaart() {
  alleEigenWinkels = await haalEigenWinkels();
  const lijstEl = document.getElementById("eigen-winkels-lijst");
  lijstEl.replaceChildren(...alleEigenWinkels.map((w) => maakEigenWinkelEl(w, verversEigenWinkelsKaart)));
  document.getElementById("eigen-winkels-leeg").hidden = alleEigenWinkels.length > 0;
  vulEigenWinkelSelects(alleEigenWinkels);
}

function initEigenWinkelAanmakenForm() {
  const form = document.getElementById("eigen-winkel-aanmaken-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("eigen-winkel-aanmaken-knop");
    knop.disabled = true;
    toonFout("eigen-winkel-aanmaken-fout", "");
    try {
      const naamVeld = document.getElementById("eigen-winkel-naam");
      await maakEigenWinkel(naamVeld.value);
      naamVeld.value = "";
      await verversEigenWinkelsKaart();
    } catch (e) {
      toonFout("eigen-winkel-aanmaken-fout", e.message);
    } finally {
      knop.disabled = false;
    }
  });
}

async function haalVerkoopdata(eigenWinkelId) {
  const resp = await fetch(`${API_BASIS}/organisatie/verkoopdata?eigen_winkel_id=${eigenWinkelId}`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon verkoopdata niet ophalen (${resp.status})`);
  return resp.json();
}

async function uploadVerkoopdata(eigenWinkelId, bestand) {
  const formData = new FormData();
  formData.append("eigen_winkel_id", eigenWinkelId);
  formData.append("bestand", bestand);
  const resp = await fetch(`${API_BASIS}/organisatie/verkoopdata`, {
    method: "POST",
    credentials: "same-origin",
    body: formData,
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Uploaden mislukt (${resp.status})`);
  }
  return resp.json();
}

function maakSvgEl(tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [naam, waarde] of Object.entries(attrs)) el.setAttribute(naam, waarde);
  return el;
}

function tekenVerkoopdataGrafiek(rijen) {
  const svg = document.getElementById("verkoopdata-grafiek");
  svg.replaceChildren();
  if (rijen.length < 2) return;

  const breedte = 920, hoogte = 200, marge = { boven: 16, rechts: 16, onder: 24, links: 70 };
  const plotBreedte = breedte - marge.links - marge.rechts;
  const plotHoogte = hoogte - marge.boven - marge.onder;
  const omzetten = rijen.map((r) => r.omzet);
  const minY = Math.min(...omzetten) * 0.95;
  const maxY = Math.max(...omzetten) * 1.05 || 1;

  const x = (i) => marge.links + (i / (rijen.length - 1)) * plotBreedte;
  const y = (waarde) => marge.boven + plotHoogte - ((waarde - minY) / (maxY - minY || 1)) * plotHoogte;

  svg.appendChild(maakSvgEl("polyline", {
    class: "lijn",
    points: rijen.map((r, i) => `${x(i)},${y(r.omzet)}`).join(" "),
  }));

  for (const waarde of [minY, maxY]) {
    const label = maakSvgEl("text", {
      class: "as-label", x: marge.links - 10, y: y(waarde) + 4, "text-anchor": "end",
    });
    label.textContent = euro.format(Math.round(waarde));
    svg.appendChild(label);
  }
  const eersteLabel = maakSvgEl("text", {
    class: "as-label", x: marge.links, y: hoogte - 4, "text-anchor": "start",
  });
  eersteLabel.textContent = rijen[0].datum;
  const laatsteLabel = maakSvgEl("text", {
    class: "as-label", x: breedte - marge.rechts, y: hoogte - 4, "text-anchor": "end",
  });
  laatsteLabel.textContent = rijen[rijen.length - 1].datum;
  svg.append(eersteLabel, laatsteLabel);
}

function toonVerkoopdata(rijen) {
  const wrap = document.getElementById("verkoopdata-grafiek-wrap");
  if (rijen.length === 0) {
    wrap.hidden = true;
    return;
  }
  document.getElementById("verkoopdata-samenvatting").textContent =
    `${rijen.length} dagen geüpload, van ${rijen[0].datum} t/m ${rijen[rijen.length - 1].datum}.`;
  tekenVerkoopdataGrafiek(rijen);
  wrap.hidden = false;
}

async function haalEigenVoorspelling(eigenWinkelId) {
  const resp = await fetch(`${API_BASIS}/organisatie/eigen-voorspelling?eigen_winkel_id=${eigenWinkelId}`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon eigen voorspelling niet ophalen (${resp.status})`);
  return resp.json();
}

function toonEigenVoorspelling(data) {
  const voortgang = document.getElementById("eigen-voorspelling-voortgang");
  const aanbeveling = document.getElementById("eigen-voorspelling-aanbeveling");

  if (!data.beschikbaar) {
    if (data.dagen_verzameld === 0) {
      voortgang.hidden = true;
      aanbeveling.hidden = true;
      return;
    }
    const nogTeGaan = data.dagen_nodig - data.dagen_verzameld;
    voortgang.textContent =
      `${data.dagen_verzameld} van de ${data.dagen_nodig} dagen verzameld voor een eigen voorspelling — ` +
      `nog ${nogTeGaan} ${nogTeGaan === 1 ? "dag" : "dagen"} te gaan.`;
    voortgang.hidden = false;
    aanbeveling.hidden = true;
    return;
  }

  voortgang.hidden = true;
  if (data.herbestel_advies) {
    aanbeveling.textContent =
      `Op basis van je eigen verkoopdata: bestel de komende week ongeveer ${data.herbestel_advies.stuks_p50} ` +
      `stuks bij. Houd rekening met pieken tot ${data.herbestel_advies.stuks_p90} stuks bij drukte, en met ` +
      `minder verkoop tot ${data.herbestel_advies.stuks_p10} stuks als het rustiger is dan verwacht.`;
  } else {
    aanbeveling.textContent =
      `Op basis van je eigen verkoopdata: verwachte omzet komende week circa ` +
      `${euro.format(Math.round(data.totaal_p50))}. Houd rekening met pieken tot ` +
      `${euro.format(Math.round(data.totaal_p90))} bij drukte, en met minder omzet tot ` +
      `${euro.format(Math.round(data.totaal_p10))} als het rustiger is dan verwacht.`;
  }
  aanbeveling.hidden = false;
}

async function toonVerkoopdataVoorSelectie() {
  const select = document.getElementById("verkoopdata-eigen-winkel");
  if (!select.value) {
    document.getElementById("verkoopdata-grafiek-wrap").hidden = true;
    document.getElementById("eigen-voorspelling-voortgang").hidden = true;
    document.getElementById("eigen-voorspelling-aanbeveling").hidden = true;
    return;
  }
  const eigenWinkelId = Number(select.value);
  toonVerkoopdata((await haalVerkoopdata(eigenWinkelId)).rijen);
  toonEigenVoorspelling(await haalEigenVoorspelling(eigenWinkelId));
}

function initVerkoopdataForm() {
  const form = document.getElementById("verkoopdata-form");
  if (!form) return;
  document.getElementById("verkoopdata-eigen-winkel").addEventListener("change", () => {
    toonVerkoopdataVoorSelectie().catch((e) => toonFout("fout", e.message));
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("verkoopdata-knop");
    const bestandVeld = document.getElementById("verkoopdata-bestand");
    const eigenWinkelId = Number(document.getElementById("verkoopdata-eigen-winkel").value);
    knop.disabled = true;
    toonFout("verkoopdata-fout", "");
    document.getElementById("verkoopdata-melding").hidden = true;
    try {
      const bestand = bestandVeld.files[0];
      const resultaat = await uploadVerkoopdata(eigenWinkelId, bestand);
      const melding = document.getElementById("verkoopdata-melding");
      melding.textContent = `${resultaat.aantal_rijen} dagen geüpload.`;
      melding.hidden = false;
      bestandVeld.value = "";
      toonVerkoopdata((await haalVerkoopdata(eigenWinkelId)).rijen);
      toonEigenVoorspelling(await haalEigenVoorspelling(eigenWinkelId));
      await verversEigenWinkelsKaart();
    } catch (e) {
      toonFout("verkoopdata-fout", e.message);
    } finally {
      knop.disabled = false;
    }
  });
}

async function haalApiKeys() {
  const resp = await fetch(`${API_BASIS}/api-keys`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon API-keys niet ophalen (${resp.status})`);
  return resp.json();
}

async function maakApiKey(naam) {
  const resp = await fetch(`${API_BASIS}/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ naam }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Aanmaken mislukt (${resp.status})`);
  }
  return resp.json();
}

async function trekApiKeyIn(keyId) {
  const resp = await fetch(`${API_BASIS}/api-keys/${keyId}`, { method: "DELETE", credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Intrekken mislukt (${resp.status})`);
}

async function verwijderTeamlid(gebruikerId) {
  const resp = await fetch(`${API_BASIS}/gebruikers/${gebruikerId}`, { method: "DELETE", credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Verwijderen mislukt (${resp.status})`);
}

function maakApiKeyEl(rij) {
  const row = document.createElement("div");
  row.className = "teamlid";
  const naam = document.createElement("span");
  naam.className = "email";
  naam.textContent = rij.naam;

  const rechts = document.createElement("span");
  rechts.className = "rechts";
  const status = document.createElement("span");
  status.className = "rol";
  status.textContent = rij.actief ? "Actief" : "Ingetrokken";
  rechts.appendChild(status);

  if (rij.actief) {
    const knop = document.createElement("button");
    knop.type = "button";
    knop.className = "btn zacht";
    knop.textContent = "Intrekken";
    knop.addEventListener("click", async () => {
      knop.disabled = true;
      try {
        await trekApiKeyIn(rij.id);
        await verversApiKeysLijst();
      } catch (e) {
        toonFout("fout", e.message);
        knop.disabled = false;
      }
    });
    rechts.appendChild(knop);
  }

  row.append(naam, rechts);
  return row;
}

async function verversApiKeysLijst() {
  const lijstEl = document.getElementById("api-keys-lijst");
  lijstEl.replaceChildren(...(await haalApiKeys()).map(maakApiKeyEl));
}

function toonNieuweKey(ruweKey) {
  const el = document.getElementById("nieuwe-key-getoond");
  el.hidden = false;
  el.textContent = "Nieuwe key aangemaakt — kopieer 'm nu, hij wordt niet nog een keer getoond: ";
  const code = document.createElement("code");
  code.className = "sleutel-code";
  code.textContent = ruweKey;
  el.appendChild(code);
}

function pasApiKeysPremiumStatusToe(inProefperiode) {
  document.getElementById("api-keys-premium-badge").hidden = !inProefperiode;
  document.getElementById("api-keys-proefperiode-melding").hidden = !inProefperiode;
  const form = document.getElementById("nieuwe-key-form");
  if (inProefperiode) {
    form.setAttribute("data-premium-vergrendeld", "");
  } else {
    form.removeAttribute("data-premium-vergrendeld");
  }
  document.getElementById("nieuwe-key-naam").disabled = inProefperiode;
  document.getElementById("nieuwe-key-knop").disabled = inProefperiode;
}

function pasProductVerkoopdataPremiumStatusToe(inProefperiode) {
  document.getElementById("product-verkoopdata-premium-badge").hidden = !inProefperiode;
  document.getElementById("product-verkoopdata-proefperiode-melding").hidden = !inProefperiode;
  const form = document.getElementById("product-verkoopdata-form");
  if (inProefperiode) {
    form.setAttribute("data-premium-vergrendeld", "");
  } else {
    form.removeAttribute("data-premium-vergrendeld");
  }
  document.getElementById("product-verkoopdata-bestand").disabled = inProefperiode;
  document.getElementById("product-verkoopdata-knop").disabled = inProefperiode;
}

async function haalProductHerbestelAdvies(eigenWinkelId) {
  const resp = await fetch(`${API_BASIS}/organisatie/herbestel-advies-per-product?eigen_winkel_id=${eigenWinkelId}`, { credentials: "same-origin" });
  if (!resp.ok) throw new Error(`Kon herbestel-advies per product niet ophalen (${resp.status})`);
  return resp.json();
}

async function uploadProductVerkoopdata(eigenWinkelId, bestand) {
  const formData = new FormData();
  formData.append("eigen_winkel_id", eigenWinkelId);
  formData.append("bestand", bestand);
  const resp = await fetch(`${API_BASIS}/organisatie/product-verkoopdata`, {
    method: "POST",
    credentials: "same-origin",
    body: formData,
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail || `Uploaden mislukt (${resp.status})`);
  }
  return resp.json();
}

function toonProductHerbestelAdvies(items) {
  const lijst = document.getElementById("product-herbestel-lijst");
  const leeg = document.getElementById("product-herbestel-leeg");
  lijst.replaceChildren();
  if (items.length === 0) {
    leeg.hidden = false;
    return;
  }
  leeg.hidden = true;
  for (const item of items) {
    const rij = document.createElement("div");
    rij.className = "teamlid";
    const naam = document.createElement("span");
    naam.className = "email";
    naam.textContent = item.product;
    const advies = document.createElement("span");
    advies.className = "rol";
    advies.textContent = `~${Math.round(item.aantal_p50)} stuks (${Math.round(item.aantal_p10)}–${Math.round(item.aantal_p90)})`;
    rij.append(naam, advies);
    lijst.appendChild(rij);
  }
}

async function toonProductAdviesVoorSelectie() {
  const select = document.getElementById("product-verkoopdata-eigen-winkel");
  if (!select.value) return;
  toonProductHerbestelAdvies((await haalProductHerbestelAdvies(Number(select.value))).items);
}

function initProductVerkoopdataForm() {
  const form = document.getElementById("product-verkoopdata-form");
  if (!form) return;
  document.getElementById("product-verkoopdata-eigen-winkel").addEventListener("change", () => {
    toonProductAdviesVoorSelectie().catch((e) => toonFout("fout", e.message));
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("product-verkoopdata-knop");
    const bestandVeld = document.getElementById("product-verkoopdata-bestand");
    const eigenWinkelId = Number(document.getElementById("product-verkoopdata-eigen-winkel").value);
    knop.disabled = true;
    toonFout("product-verkoopdata-fout", "");
    document.getElementById("product-verkoopdata-melding").hidden = true;
    try {
      const bestand = bestandVeld.files[0];
      const resultaat = await uploadProductVerkoopdata(eigenWinkelId, bestand);
      const melding = document.getElementById("product-verkoopdata-melding");
      melding.textContent = `${resultaat.aantal_rijen} rijen geüpload.`;
      melding.hidden = false;
      bestandVeld.value = "";
      toonProductHerbestelAdvies((await haalProductHerbestelAdvies(eigenWinkelId)).items);
      await verversEigenWinkelsKaart();
    } catch (e) {
      toonFout("product-verkoopdata-fout", e.message);
    } finally {
      knop.disabled = false;
    }
  });
}

function initNieuweKeyForm() {
  const form = document.getElementById("nieuwe-key-form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const knop = document.getElementById("nieuwe-key-knop");
    knop.disabled = true;
    toonFout("nieuwe-key-fout", "");
    try {
      const naamVeld = document.getElementById("nieuwe-key-naam");
      const resultaat = await maakApiKey(naamVeld.value);
      naamVeld.value = "";
      toonNieuweKey(resultaat.ruwe_key);
      await verversApiKeysLijst();
    } catch (e) {
      toonFout("nieuwe-key-fout", e.message);
    } finally {
      knop.disabled = false;
    }
  });
}

async function initTeamPagina() {
  if (!document.getElementById("teamlijst")) return;

  const me = await haalMe();
  if (!me) {
    window.location.href = "./login.html";
    return;
  }
  document.getElementById("wie-ben-ik-mobiel").textContent = `Ingelogd als ${me.email} (${me.rol}).`;
  document.getElementById("wie-ben-ik").textContent = me.email;
  initPortfolioSidebar(me);
  if (me.ingekochte_leden != null || me.ingekochte_winkels != null) {
    const el = document.getElementById("abonnement-aantallen");
    if (el) {
      const delen = [];
      if (me.ingekochte_leden != null) delen.push(`${me.ingekochte_leden} teamleden`);
      if (me.ingekochte_winkels != null) delen.push(`${me.ingekochte_winkels} vestigingen`);
      el.textContent = `Abonnement: ${delen.join(", ")} inbegrepen.`;
      el.hidden = false;
    }
  }
  initOnboarding(me);

  const kanBeheren = me.rol === "eigenaar";
  let alleWinkels = [];
  if (kanBeheren) {
    try {
      alleWinkels = await haalWinkels();
    } catch (e) {
      toonFout("fout", e.message);
    }
  }

  try {
    await verversTeamlijst(kanBeheren, alleWinkels);
  } catch (e) {
    toonFout("fout", e.message);
  }

  if (kanBeheren) {
    document.getElementById("nieuw-lid-kaart").hidden = false;
    document.getElementById("herbestel-kaart").hidden = false;
    document.getElementById("api-keys-kaart").hidden = false;
    pasApiKeysPremiumStatusToe(me.in_proefperiode);
    try {
      const instellingen = await haalOrganisatieInstellingen();
      if (instellingen.gemiddelde_omzet_per_stuk !== null) {
        document.getElementById("herbestel-prijs").value = instellingen.gemiddelde_omzet_per_stuk;
      }
    } catch (e) {
      toonFout("fout", e.message);
    }
    initHerbestelForm();
    try {
      await verversApiKeysLijst();
    } catch (e) {
      toonFout("fout", e.message);
    }
    initNieuweKeyForm();

    document.getElementById("eigen-winkels-kaart").hidden = false;
    try {
      await verversEigenWinkelsKaart();
    } catch (e) {
      toonFout("fout", e.message);
    }
    initEigenWinkelAanmakenForm();
  } else {
    // Een lid kan geen eigen winkel aanmaken/beheren (eigenaar-only, zie
    // serving/app.py), maar moet wel de bestaande winkels in de
    // upload-kaart-dropdowns kunnen zien (die kaarten zijn voor iedereen
    // zichtbaar, zie hieronder) — vul de selects zonder de beheerkaart te
    // tonen.
    try {
      alleEigenWinkels = await haalEigenWinkels();
      vulEigenWinkelSelects(alleEigenWinkels);
    } catch (e) {
      toonFout("fout", e.message);
    }
  }

  // Verkoopdata-kaart: voor iedereen zichtbaar (je eigen verkoophistorie
  // bekijken is geen beheertaak), maar het upload-formulier zelf alleen
  // voor de eigenaar — zelfde eigenaar/lid-verdeling als de herbestel-prijs.
  // De selects zijn hierboven al gevuld (verversEigenWinkelsKaart() voor
  // een eigenaar, de losse haalEigenWinkels()-aanroep voor een lid).
  document.getElementById("verkoopdata-kaart").hidden = false;
  document.getElementById("verkoopdata-form").hidden = !kanBeheren;
  try {
    await toonVerkoopdataVoorSelectie();
  } catch (e) {
    toonFout("fout", e.message);
  }
  if (kanBeheren) initVerkoopdataForm();

  // Zelfde eigenaar/lid-verdeling als hierboven, plus de premium-gate:
  // tijdens de proefperiode is /organisatie/herbestel-advies-per-product
  // hard geblokkeerd (403) server-side, dus die aanroep overslaan i.p.v.
  // een verwachte fout in de generieke foutmelding te tonen.
  document.getElementById("product-verkoopdata-kaart").hidden = false;
  document.getElementById("product-verkoopdata-form").hidden = !kanBeheren;
  pasProductVerkoopdataPremiumStatusToe(me.in_proefperiode);
  if (!me.in_proefperiode) {
    try {
      await toonProductAdviesVoorSelectie();
    } catch (e) {
      toonFout("fout", e.message);
    }
  }
  if (kanBeheren) initProductVerkoopdataForm();

  initNieuwLidForm(kanBeheren, alleWinkels);
  initUitloggenLink();
}

document.addEventListener("DOMContentLoaded", () => {
  initSignupPagina();
  initLoginPagina();
  initWachtwoordVergetenPagina();
  initWachtwoordResettenPagina();
  initTeamPagina();
});
