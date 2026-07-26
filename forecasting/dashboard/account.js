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

async function initTeamPagina() {
  if (!document.getElementById("teamlijst")) return;

  const me = await haalMe();
  if (!me) {
    window.location.href = "./login.html";
    return;
  }
  document.getElementById("wie-ben-ik").textContent = `Ingelogd als ${me.email} (${me.rol}).`;
  if (me.rol === "eigenaar") document.getElementById("nieuw-lid-kaart").hidden = false;

  try {
    await verversTeamlijst();
  } catch (e) {
    toonFout("fout", e.message);
  }

  initNieuwLidForm();
  initUitloggenLink();
}

document.addEventListener("DOMContentLoaded", () => {
  initLoginPagina();
  initTeamPagina();
});
