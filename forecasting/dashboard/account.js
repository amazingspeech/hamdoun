"use strict";

const API_BASIS = window.TESSAR_FORECAST_API_BASIS || "";

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
  const link = document.getElementById("uitloggen");
  if (!link) return;
  link.addEventListener("click", async (event) => {
    event.preventDefault();
    await logout();
    window.location.href = "./login.html";
  });
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
    } catch (e) {
      toonFout("herbestel-fout", e.message);
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
  document.getElementById("wie-ben-ik").textContent = `Ingelogd als ${me.email} (${me.rol}).`;

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
  }

  initNieuwLidForm(kanBeheren, alleWinkels);
  initUitloggenLink();
}

document.addEventListener("DOMContentLoaded", () => {
  initLoginPagina();
  initTeamPagina();
});
