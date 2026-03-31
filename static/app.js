/* ============================================================
   PA Theorem Prover — Web UI logic
   ============================================================ */

"use strict";

// ── State ────────────────────────────────────────────────────
let cmdHistory = [];
let historyIdx = -1;
let pendingInput = "";          // saved while navigating history

// ── DOM refs ─────────────────────────────────────────────────
const factListEl  = () => document.getElementById("fact-list");
const outputLogEl = () => document.getElementById("output-log");
const cmdInputEl  = () => document.getElementById("cmd-input");

// ── API helpers ───────────────────────────────────────────────
async function apiPost(path, body = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

// ── HTML escaping ─────────────────────────────────────────────
function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ── Fact list ─────────────────────────────────────────────────
function renderFacts(facts, newIds = new Set()) {
  const list = factListEl();

  if (!facts.length) {
    list.innerHTML = '<div class="fact-empty">No facts yet — enter a command below.</div>';
    return;
  }

  // Build a map of existing items so we can avoid a full re-render.
  const existing = new Map();
  list.querySelectorAll(".fact-item").forEach(el => {
    existing.set(Number(el.dataset.id), el);
  });

  // Remove items that are no longer present (e.g. after reset).
  if (facts.length < existing.size) {
    list.innerHTML = "";
    existing.clear();
  }

  facts.forEach(fact => {
    if (existing.has(fact.id)) return;           // already rendered

    const item = document.createElement("div");
    item.className = "fact-item" + (newIds.has(fact.id) ? " new" : "");
    item.dataset.id = fact.id;
    item.innerHTML =
      `<span class="fact-num">#${fact.id}</span>` +
      `<span class="fact-prop">${esc(fact.prop)}</span>`;
    item.addEventListener("click", () => insertRef(fact.id));
    list.appendChild(item);
  });

  // Scroll to bottom if new facts were added.
  if (newIds.size) list.scrollTop = list.scrollHeight;
}

function insertRef(id) {
  const input = cmdInputEl();
  const ref   = `#${id}`;
  const s     = input.selectionStart;
  const e2    = input.selectionEnd;
  input.value = input.value.slice(0, s) + ref + input.value.slice(e2);
  input.selectionStart = input.selectionEnd = s + ref.length;
  input.focus();
}

// ── Output log ────────────────────────────────────────────────
function appendEntry(command, response) {
  const log   = outputLogEl();
  const entry = document.createElement("div");
  entry.className = "output-entry";

  let html =
    `<div class="output-cmd-line">` +
    `<span class="prompt-glyph">⊢</span>${esc(command)}` +
    `</div>`;

  if (response.ok) {
    response.new_facts.forEach(prop => {
      html +=
        `<div class="output-result-line">` +
        `<span class="result-mark ok">✓</span>` +
        `<span class="result-prop">${esc(prop)}</span>` +
        `</div>`;
    });
  } else {
    const label = {
      unknown_command: "unknown command",
      invalid_input:   "invalid input",
      type_mismatch:   "type mismatch",
    }[response.error_type] ?? "error";

    html +=
      `<div class="output-result-line">` +
      `<span class="result-mark err">✗</span>` +
      `<span class="result-error">${label} — ${esc(response.error)}</span>` +
      `</div>`;
  }

  entry.innerHTML = html;
  log.appendChild(entry);
  log.scrollTop = log.scrollHeight;
}

function appendDivider(text) {
  const log = outputLogEl();
  const el  = document.createElement("div");
  el.className = "output-divider";
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}

// ── Command submission ────────────────────────────────────────
async function submitCommand() {
  const input = cmdInputEl();
  const raw   = input.value.trim();
  if (!raw) return;

  // History
  if (cmdHistory[cmdHistory.length - 1] !== raw) cmdHistory.push(raw);
  historyIdx  = -1;
  pendingInput = "";
  input.value = "";

  // Meta-commands
  if (raw.toLowerCase() === "reset") {
    const data = await apiPost("/api/reset");
    appendDivider("── session reset ──");
    renderFacts([], new Set());
    return;
  }

  // Run
  const n_before_unknown = document.querySelectorAll(".fact-item").length;
  const data = await apiPost("/api/run", { command: raw });
  appendEntry(raw, data);

  if (data.ok) {
    const newIds = new Set(data.facts.slice(-data.new_facts.length).map(f => f.id));
    renderFacts(data.facts, newIds);
  }
}

// ── Keyboard handling ─────────────────────────────────────────
function initInput() {
  const input = cmdInputEl();

  input.addEventListener("keydown", e => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitCommand();
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (historyIdx === -1) {
        pendingInput = input.value;
        historyIdx = cmdHistory.length;
      }
      if (historyIdx > 0) {
        historyIdx--;
        input.value = cmdHistory[historyIdx];
        input.selectionStart = input.selectionEnd = input.value.length;
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIdx === -1) return;
      historyIdx++;
      if (historyIdx >= cmdHistory.length) {
        historyIdx  = -1;
        input.value = pendingInput;
      } else {
        input.value = cmdHistory[historyIdx];
      }
      input.selectionStart = input.selectionEnd = input.value.length;
      return;
    }
  });

  // Global shortcuts
  document.addEventListener("keydown", e => {
    // Ctrl+Shift+R → reset
    if (e.ctrlKey && e.shiftKey && e.key === "R") {
      e.preventDefault();
      document.getElementById("reset-btn").click();
    }
    // Any printable key (not in an input) → focus cmd input
    if (
      !e.ctrlKey && !e.metaKey && !e.altKey &&
      e.key.length === 1 &&
      document.activeElement !== input
    ) {
      input.focus();
    }
  });
}

// ── Resize: horizontal (fact vs cmd) ─────────────────────────
function initHorizontalResize() {
  const handle    = document.getElementById("h-divider");
  const factPanel = document.getElementById("fact-panel");
  const mainArea  = document.getElementById("main-area");
  let dragging = false;
  let startX = 0, startW = 0;

  handle.addEventListener("mousedown", e => {
    dragging = true;
    startX   = e.clientX;
    startW   = factPanel.offsetWidth;
    handle.classList.add("dragging");
    document.body.style.cssText += ";cursor:ew-resize;user-select:none;";
    e.preventDefault();
  });

  document.addEventListener("mousemove", e => {
    if (!dragging) return;
    const dx    = e.clientX - startX;
    const total = mainArea.offsetWidth;
    const newW  = Math.max(130, Math.min(total - 135, startW + dx));
    factPanel.style.flex = `0 0 ${newW}px`;
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove("dragging");
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  });
}

// ── Resize: vertical (main vs terminal) ──────────────────────
function initVerticalResize() {
  const handle   = document.getElementById("v-divider");
  const mainArea = document.getElementById("main-area");
  const terminal = document.getElementById("terminal-section");
  let dragging = false;
  let startY = 0, startMainH = 0, startTermH = 0;

  handle.addEventListener("mousedown", e => {
    dragging    = true;
    startY      = e.clientY;
    startMainH  = mainArea.offsetHeight;
    startTermH  = terminal.offsetHeight;
    handle.classList.add("dragging");
    document.body.style.cssText += ";cursor:ns-resize;user-select:none;";
    e.preventDefault();
  });

  document.addEventListener("mousemove", e => {
    if (!dragging) return;
    const dy       = e.clientY - startY;
    const newMainH = Math.max(90, startMainH + dy);
    const newTermH = Math.max(70, startTermH - dy);
    mainArea.style.flex = `0 0 ${newMainH}px`;
    terminal.style.flex = `0 0 ${newTermH}px`;
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove("dragging");
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  });
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Buttons
  document.getElementById("reset-btn").addEventListener("click", async () => {
    const data = await apiPost("/api/reset");
    appendDivider("── session reset ──");
    renderFacts([], new Set());
  });

  document.getElementById("clear-btn").addEventListener("click", () => {
    outputLogEl().innerHTML = "";
  });

  // Resize handles
  initHorizontalResize();
  initVerticalResize();

  // Input
  initInput();
  cmdInputEl().focus();
});
