const listEl = document.getElementById("protocol-list");
const searchEl = document.getElementById("search");
const contentEl = document.getElementById("content");
const aiButton = document.getElementById("ai-button");
const aiPanel = document.getElementById("ai-panel");
const aiClose = document.getElementById("ai-close");
const aiLog = document.getElementById("ai-log");
const aiForm = document.getElementById("ai-form");
const aiInput = document.getElementById("ai-input");

let allProtocols = [];
let activeId = null;

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function statusBadge(status) {
  if (status === "voorbeeld") {
    return `<span class="badge badge-voorbeeld">VOORBEELD</span>`;
  }
  if (status === "te-verifieren") {
    return `<span class="badge badge-te-verifieren">TE VERIFIËREN</span>`;
  }
  return "";
}

async function loadList() {
  const res = await fetch("/api/protocols");
  allProtocols = await res.json();
  renderList(allProtocols);
}

function renderList(protocols) {
  listEl.innerHTML = "";
  let lastCategory = null;

  for (const p of protocols) {
    if (p.category !== lastCategory) {
      const heading = document.createElement("div");
      heading.className = "category-heading";
      heading.textContent = p.category;
      listEl.appendChild(heading);
      lastCategory = p.category;
    }

    const btn = document.createElement("button");
    btn.className = "protocol-item" + (p.id === activeId ? " active" : "");
    btn.innerHTML = `${escapeHtml(p.title)} ${statusBadge(p.status)}`;
    btn.addEventListener("click", () => selectProtocol(p.id));
    listEl.appendChild(btn);
  }

  if (protocols.length === 0) {
    const empty = document.createElement("p");
    empty.className = "placeholder-msg";
    empty.textContent = "Geen protocollen gevonden.";
    listEl.appendChild(empty);
  }
}

async function selectProtocol(id) {
  activeId = id;
  renderList(filterProtocols(searchEl.value));

  const res = await fetch(`/api/protocols/${encodeURIComponent(id)}`);
  if (!res.ok) {
    contentEl.innerHTML = `<p class="placeholder-msg">Kon protocol niet laden.</p>`;
    return;
  }
  const protocol = await res.json();
  contentEl.innerHTML = `
    <div class="protocol-meta">${escapeHtml(protocol.category)} ${statusBadge(protocol.status)}</div>
    ${protocol.html}
  `;
}

function filterProtocols(query) {
  const q = query.trim().toLowerCase();
  if (!q) return allProtocols;
  return allProtocols.filter(
    (p) =>
      p.title.toLowerCase().includes(q) || p.category.toLowerCase().includes(q)
  );
}

searchEl.addEventListener("input", () => {
  renderList(filterProtocols(searchEl.value));
});

// --- AI-assistent ---

aiButton.addEventListener("click", () => {
  aiPanel.classList.toggle("hidden");
  if (!aiPanel.classList.contains("hidden")) {
    aiInput.focus();
  }
});

aiClose.addEventListener("click", () => {
  aiPanel.classList.add("hidden");
});

function appendAiMessage(html, className) {
  const el = document.createElement("div");
  el.className = className;
  el.innerHTML = html;
  aiLog.appendChild(el);
  aiLog.scrollTop = aiLog.scrollHeight;
  return el;
}

function protocolTitle(id) {
  const p = allProtocols.find((p) => p.id === id);
  return p ? p.title : id;
}

aiForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = aiInput.value.trim();
  if (!question) return;

  aiInput.value = "";
  appendAiMessage(escapeHtml(question), "ai-msg ai-msg-question");
  const pending = appendAiMessage("…", "ai-msg ai-msg-pending");

  let data;
  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    data = await res.json();
    if (!res.ok) {
      pending.remove();
      appendAiMessage(escapeHtml(data.error || "Er ging iets mis."), "ai-msg ai-msg-error");
      return;
    }
  } catch (err) {
    pending.remove();
    appendAiMessage("Kon geen verbinding maken met de AI.", "ai-msg ai-msg-error");
    return;
  }

  pending.remove();

  if (data.escalate) {
    appendAiMessage(escapeHtml(data.answer), "ai-msg ai-msg-escalate");
    return;
  }

  let html = escapeHtml(data.answer);
  if (!data.covered) {
    html += `<div class="ai-not-covered">Dit staat niet in de geladen protocollen.</div>`;
  }
  if (data.sources && data.sources.length > 0) {
    const tags = data.sources
      .map(
        (id) =>
          `<button type="button" class="source-tag" data-id="${escapeHtml(id)}">${escapeHtml(protocolTitle(id))}</button>`
      )
      .join("");
    html += `<div class="ai-sources">Bron: ${tags}</div>`;
  }
  const answerEl = appendAiMessage(html, "ai-msg ai-msg-answer");
  answerEl.querySelectorAll(".source-tag").forEach((btn) => {
    btn.addEventListener("click", () => selectProtocol(btn.dataset.id));
  });
});

loadList();
