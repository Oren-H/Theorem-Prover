/* ============================================================
   PA Theorem Prover — Web UI logic
   ============================================================ */

"use strict";

// ── Command definitions (autocomplete) ───────────────────────
const CMD_DEFS = [
  { name: "succ_not_zero", params: "n",    hint: "n++ ≠ 0"        },
  { name: "succ_imp_eq",   params: "n, m", hint: "n++=m++ ⇒ n=m"  },
  { name: "add_zero_eq",   params: "n",    hint: "n + 0 = n"       },
  { name: "add_succ_eq",   params: "n, m", hint: "n+m++ = (n+m)++" },
  { name: "cont",          params: "L",    hint: "P⇒Q ↦ ¬Q⇒¬P"    },
  { name: "mp",            params: "P, L", hint: "P, P⇒Q ⊢ Q"     },
  { name: "flip",          params: "P",    hint: "p=r ↦ r=p"       },
];

// ── History / autocomplete state ─────────────────────────────
let cmdHistory  = [];
let historyIdx  = -1;
let pendingInput = "";
let ac = { matches: [], idx: 0, prefix: "" };

// ── DOM helpers ───────────────────────────────────────────────
const $ = id => document.getElementById(id);
const cmdEl      = () => $("cmd-input");   // the contenteditable div
const factListEl = () => $("fact-list");
const outputEl   = () => $("output-log");
const acDdEl     = () => $("ac-dropdown");

// ── HTML escape ───────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ============================================================
// ── Contenteditable value helpers ────────────────────────────
// ============================================================
// Invariant: #cmd-input always contains exactly one Text node
// (possibly empty) followed by an optional .ghost-span element.
// All setters maintain this invariant.

/** Return the typed text — everything except the ghost span. */
function getVal() {
  const el = cmdEl();
  let text = "";
  el.childNodes.forEach(n => {
    if (n.nodeType === Node.TEXT_NODE) text += n.textContent;
    // ghost-span (Element) is intentionally skipped
  });
  return text;
}

/** Replace typed text; cursor moves to end; ghost span preserved. */
function setVal(text) {
  const el    = cmdEl();
  const ghost = el.querySelector(".ghost-span");
  if (ghost) ghost.remove();
  el.textContent = text;           // replaces all child nodes with a Text node
  if (ghost) el.appendChild(ghost);
  _moveCursorToEnd();
  _updatePlaceholder();
}

/** Is the caret at the very end of the typed text (before the ghost span)? */
function isAtEnd() {
  const sel = window.getSelection();
  if (!sel.rangeCount || !sel.isCollapsed) return false;
  const { startContainer, startOffset } = sel.getRangeAt(0);
  const el = cmdEl();
  // Text node case: caret must be at end of the first text node.
  if (startContainer.nodeType === Node.TEXT_NODE && startContainer.parentNode === el) {
    return startOffset === startContainer.textContent.length;
  }
  // Element case: caret is positioned between child nodes in the div.
  // offset 0 = before all children; offset >= 1 = after the text node (= at end).
  if (startContainer === el) {
    return startOffset >= 1 || getVal().length === 0;
  }
  return false;
}

function _moveCursorToEnd() {
  const el   = cmdEl();
  const sel  = window.getSelection();
  const range = document.createRange();
  // Place cursor at end of first text node (before ghost span).
  const textNode = [...el.childNodes].find(n => n.nodeType === Node.TEXT_NODE);
  if (textNode) {
    range.setStart(textNode, textNode.textContent.length);
  } else {
    range.setStart(el, 0);
  }
  range.collapse(true);
  sel.removeAllRanges();
  sel.addRange(range);
}

function _updatePlaceholder() {
  const el = cmdEl();
  if (getVal().length > 0) {
    el.setAttribute("data-has-text", "");
  } else {
    el.removeAttribute("data-has-text");
  }
}

// ── Ghost span (inside #cmd-input) ───────────────────────────
function _ghostSpan() { return cmdEl().querySelector(".ghost-span"); }

function setGhostSpan(suffix) {
  let ghost = _ghostSpan();
  if (!suffix) { if (ghost) ghost.remove(); return; }
  if (!ghost) {
    ghost = document.createElement("span");
    ghost.className = "ghost-span";
    ghost.setAttribute("contenteditable", "false");
    cmdEl().appendChild(ghost);
  }
  ghost.textContent = suffix;
}

// ============================================================
// ── API ──────────────────────────────────────────────────────
async function apiPost(path, body = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

// ── Fact list ─────────────────────────────────────────────────
function renderFacts(facts, newIds = new Set()) {
  const list = factListEl();
  if (!facts.length) {
    list.innerHTML = '<div class="fact-empty">No facts yet — enter a command below.</div>';
    return;
  }
  const existing = new Map();
  list.querySelectorAll(".fact-item").forEach(el => existing.set(+el.dataset.id, el));
  if (facts.length < existing.size) { list.innerHTML = ""; existing.clear(); }

  facts.forEach(fact => {
    if (existing.has(fact.id)) return;
    const item = document.createElement("div");
    item.className = "fact-item" + (newIds.has(fact.id) ? " new" : "");
    item.dataset.id = fact.id;
    item.innerHTML =
      `<span class="fact-num">#${fact.id}</span>` +
      `<span class="fact-prop">${esc(fact.prop)}</span>`;
    item.addEventListener("click", () => insertRef(fact.id));
    list.appendChild(item);
  });
  if (newIds.size) list.scrollTop = list.scrollHeight;
}

function insertRef(id) {
  const ref = `#${id}`;
  cmdEl().focus();
  // Insert at caret position using execCommand (works in contenteditable).
  document.execCommand("insertText", false, ref);
  updateHints();
}

// ── Output log ────────────────────────────────────────────────
function appendEntry(command, response) {
  const entry = document.createElement("div");
  entry.className = "output-entry";
  let html = `<div class="output-cmd-line"><span class="prompt-glyph">⊢</span>${esc(command)}</div>`;
  if (response.ok) {
    response.new_facts.forEach(prop => {
      html += `<div class="output-result-line"><span class="result-mark ok">✓</span><span class="result-prop">${esc(prop)}</span></div>`;
    });
  } else {
    const label = { unknown_command: "unknown command", invalid_input: "invalid input",
                    type_mismatch: "type mismatch" }[response.error_type] ?? "error";
    html += `<div class="output-result-line"><span class="result-mark err">✗</span><span class="result-error">${label} — ${esc(response.error)}</span></div>`;
  }
  entry.innerHTML = html;
  outputEl().appendChild(entry);
  outputEl().scrollTop = outputEl().scrollHeight;
}

function appendDivider(text) {
  const el = document.createElement("div");
  el.className = "output-divider";
  el.textContent = text;
  outputEl().appendChild(el);
  outputEl().scrollTop = outputEl().scrollHeight;
}

// ── Command submission ────────────────────────────────────────
async function submitCommand() {
  const raw = getVal().trim();
  if (!raw) return;

  if (cmdHistory[cmdHistory.length - 1] !== raw) cmdHistory.push(raw);
  historyIdx  = -1;
  pendingInput = "";
  setVal("");
  setGhostSpan("");
  acDdEl().style.display = "none";
  ac = { matches: [], idx: 0, prefix: "" };

  if (raw.toLowerCase() === "reset") {
    await apiPost("/api/reset");
    appendDivider("── session reset ──");
    renderFacts([], new Set());
    return;
  }

  const data = await apiPost("/api/run", { command: raw });
  appendEntry(raw, data);
  if (data.ok) {
    const newIds = new Set(data.facts.slice(-data.new_facts.length).map(f => f.id));
    renderFacts(data.facts, newIds);
  }
}

// ============================================================
// ── Autocomplete engine ──────────────────────────────────────
// ============================================================

function getInnerCall(text, pos) {
  let depth = 0;
  for (let i = pos - 1; i >= 0; i--) {
    if (text[i] === ")") { depth++; continue; }
    if (text[i] === "(") {
      if (depth > 0) { depth--; continue; }
      const m = text.slice(0, i).match(/([A-Za-z_][A-Za-z0-9_]*)$/);
      if (!m) return null;
      const cmd = CMD_DEFS.find(c => c.name === m[1]);
      if (!cmd) return null;
      const inside = text.slice(i + 1, pos);
      let d = 0, argIdx = 0;
      for (const c of inside) {
        if (c === "(") d++;
        else if (c === ")") d--;
        else if (c === "," && d === 0) argIdx++;
      }
      return { cmd, argIdx };
    }
  }
  return null;
}

function getPrefix(text, pos) {
  const m = text.slice(0, pos).match(/([A-Za-z_][A-Za-z0-9_]*)$/);
  return m ? m[1] : "";
}

function renderDropdown(mode, payload) {
  const dd = acDdEl();
  if (mode === "list") {
    const { matches, selected } = payload;
    let html = matches.map((c, i) =>
      `<div class="ac-item${i === selected ? " selected" : ""}" data-idx="${i}">` +
      `<span class="ac-name">${esc(c.name)}</span>` +
      `<span class="ac-params">(${esc(c.params)})</span>` +
      `<span class="ac-hint">${esc(c.hint)}</span></div>`
    ).join("");
    html += `<div class="ac-tab-hint"><kbd>Tab</kbd> ${matches.length > 1 ? "cycle" : "accept"} &nbsp;·&nbsp; <kbd>→</kbd> accept</div>`;
    dd.innerHTML = html;
    dd.style.display = "block";
    dd.querySelectorAll(".ac-item").forEach(el => {
      el.addEventListener("mousedown", e => { e.preventDefault(); applyCompletion(matches[+el.dataset.idx]); });
    });
  } else if (mode === "sig") {
    const { cmd, argIdx } = payload;
    const paramsHtml = cmd.params.split(",").map((p, i) =>
      `<span class="sig-param${i === argIdx ? " active" : ""}">${esc(p.trim())}</span>`
    ).join(`<span class="sig-comma">, </span>`);
    dd.innerHTML =
      `<div class="sig-help"><span class="sig-name">${esc(cmd.name)}</span>` +
      `<span class="sig-paren">(</span>${paramsHtml}<span class="sig-paren">)</span>` +
      `<span class="sig-hint">${esc(cmd.hint)}</span></div>`;
    dd.style.display = "block";
  } else {
    dd.style.display = "none";
  }
}

function updateHints() {
  _updatePlaceholder();
  const text = getVal();
  const pos  = text.length;   // only show hints when cursor is at end

  if (!isAtEnd()) { setGhostSpan(""); renderDropdown("none"); return; }

  const prefix    = getPrefix(text, pos);
  const innerCall = getInnerCall(text, pos);

  if (prefix) {
    const matches = CMD_DEFS.filter(c => c.name.startsWith(prefix) && c.name !== prefix);
    if (matches.length > 0) {
      if (ac.prefix !== prefix) { ac.idx = 0; ac.prefix = prefix; }
      ac.matches = matches;
      if (ac.idx >= matches.length) ac.idx = 0;
      const best = matches[ac.idx];
      setGhostSpan(best.name.slice(prefix.length) + "(" + best.params + ")");
      renderDropdown("list", { matches, selected: ac.idx });
      return;
    }
    const exact = CMD_DEFS.find(c => c.name === prefix);
    if (exact && !text.endsWith("(")) {
      setGhostSpan("(" + exact.params + ")");
      renderDropdown("list", { matches: [exact], selected: 0 });
      ac = { matches: [exact], idx: 0, prefix };
      return;
    }
  }

  if (innerCall) {
    setGhostSpan("");
    renderDropdown("sig", innerCall);
    ac = { matches: [], idx: 0, prefix: "" };
    return;
  }

  setGhostSpan("");
  renderDropdown("none");
  ac = { matches: [], idx: 0, prefix: "" };
}

function acceptGhost() {
  const ghost = _ghostSpan();
  if (!ghost || !ghost.textContent) return false;
  const suffix = ghost.textContent;
  setGhostSpan("");
  ac = { matches: [], idx: 0, prefix: "" };
  document.execCommand("insertText", false, suffix);
  updateHints();
  return true;
}

function applyCompletion(cmd) {
  const text   = getVal();
  const prefix = getPrefix(text, text.length);
  const suffix = cmd.name.slice(prefix.length) + "(" + cmd.params + ")";
  // Delete prefix then insert full completion
  for (let i = 0; i < prefix.length; i++) document.execCommand("delete");
  document.execCommand("insertText", false, cmd.name + "(" + cmd.params + ")");
  setGhostSpan("");
  ac = { matches: [], idx: 0, prefix: "" };
  updateHints();
}

function cycleCompletion() {
  if (!ac.matches.length) return false;
  ac.idx = (ac.idx + 1) % ac.matches.length;
  const best = ac.matches[ac.idx];
  setGhostSpan(best.name.slice(ac.prefix.length) + "(" + best.params + ")");
  acDdEl().querySelectorAll(".ac-item").forEach((el, i) =>
    el.classList.toggle("selected", i === ac.idx));
  return true;
}

// ── Resize ────────────────────────────────────────────────────
function initHorizontalResize() {
  const handle = $("h-divider"), factPanel = $("fact-panel"), mainArea = $("main-area");
  let dragging = false, startX = 0, startW = 0;
  handle.addEventListener("mousedown", e => {
    dragging = true; startX = e.clientX; startW = factPanel.offsetWidth;
    handle.classList.add("dragging");
    document.body.style.cssText += ";cursor:ew-resize;user-select:none;";
    e.preventDefault();
  });
  document.addEventListener("mousemove", e => {
    if (!dragging) return;
    factPanel.style.flex = `0 0 ${Math.max(130, Math.min(mainArea.offsetWidth - 135, startW + e.clientX - startX))}px`;
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false; handle.classList.remove("dragging");
    document.body.style.cursor = ""; document.body.style.userSelect = "";
  });
}

function initVerticalResize() {
  const handle = $("v-divider"), mainArea = $("main-area"), terminal = $("terminal-section");
  let dragging = false, startY = 0, startMainH = 0, startTermH = 0;
  handle.addEventListener("mousedown", e => {
    dragging = true; startY = e.clientY;
    startMainH = mainArea.offsetHeight; startTermH = terminal.offsetHeight;
    handle.classList.add("dragging");
    document.body.style.cssText += ";cursor:ns-resize;user-select:none;";
    e.preventDefault();
  });
  document.addEventListener("mousemove", e => {
    if (!dragging) return;
    const dy = e.clientY - startY;
    mainArea.style.flex  = `0 0 ${Math.max(90, startMainH + dy)}px`;
    terminal.style.flex  = `0 0 ${Math.max(70, startTermH - dy)}px`;
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false; handle.classList.remove("dragging");
    document.body.style.cursor = ""; document.body.style.userSelect = "";
  });
}

// ── Input init ────────────────────────────────────────────────
function initInput() {
  const el = cmdEl();

  // Prevent newlines — contenteditable would insert <br> or <div> on Enter.
  el.addEventListener("keydown", e => {

    if (e.key === "Tab") {
      e.preventDefault();
      ac.matches.length > 1 ? cycleCompletion() : acceptGhost();
      return;
    }

    if (e.key === "ArrowRight" && isAtEnd()) {
      if (acceptGhost()) { e.preventDefault(); return; }
    }

    if (e.key === "Escape") {
      setGhostSpan(""); acDdEl().style.display = "none";
      ac = { matches: [], idx: 0, prefix: "" };
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      submitCommand();
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (historyIdx === -1) { pendingInput = getVal(); historyIdx = cmdHistory.length; }
      if (historyIdx > 0) { setVal(cmdHistory[--historyIdx]); updateHints(); }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIdx === -1) return;
      historyIdx++;
      setVal(historyIdx < cmdHistory.length ? cmdHistory[historyIdx] : (historyIdx = -1, pendingInput));
      updateHints();
      return;
    }
  });

  // Strip HTML on paste — keep plain text only.
  el.addEventListener("paste", e => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData("text/plain");
    document.execCommand("insertText", false, text);
  });

  // Update hints on every change.
  el.addEventListener("input",  updateHints);
  el.addEventListener("keyup",  updateHints);
  el.addEventListener("click",  updateHints);

  // Global: any printable key focuses the cmd div.
  document.addEventListener("keydown", e => {
    if (e.ctrlKey && e.shiftKey && e.key === "R") { e.preventDefault(); $("reset-btn").click(); }
    if (!e.ctrlKey && !e.metaKey && !e.altKey && e.key.length === 1 && document.activeElement !== el) {
      el.focus(); _moveCursorToEnd();
    }
  });
}

// ── Boot ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  $("reset-btn").addEventListener("click", async () => {
    await apiPost("/api/reset");
    appendDivider("── session reset ──");
    renderFacts([], new Set());
  });

  $("clear-btn").addEventListener("click", () => { outputEl().innerHTML = ""; });

  initHorizontalResize();
  initVerticalResize();
  initInput();
  cmdEl().focus();
});
