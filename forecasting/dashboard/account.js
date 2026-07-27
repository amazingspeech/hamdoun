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

function maakTeamlidEl(lid) {
  const rij = document.createElement("div");
  rij.className = "teamlid";
  const email = document.createElement("span");
  email.className = "email";
  email.textContent = lid.email;
  const rol = document.createElement("span");
  rol.className = "rol";
  rol.textContent = lid.rol;
  rij.append(email, rol);
  return rij;
}

async function verversTeamlijst() {
  const teamEl = document.getElementById("teamlijst");
  const team = await haalTeam();
  teamEl.replaceChildren(...team.map(maakTeamlidEl));
}

function initNieuwLidForm() {
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
      await verversTeamlijst();
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

  try {
    await verversTeamlijst();
  } catch (e) {
    toonFout("fout", e.message);
  }

  if (me.rol === "eigenaar") {
    document.getElementById("nieuw-lid-kaart").hidden = false;
    document.getElementById("api-keys-kaart").hidden = false;
    try {
      await verversApiKeysLijst();
    } catch (e) {
      toonFout("fout", e.message);
    }
    initNieuweKeyForm();
  }

  initNieuwLidForm();
  initUitloggenLink();
}

document.addEventListener("DOMContentLoaded", () => {
  initLoginPagina();
  initTeamPagina();
});
