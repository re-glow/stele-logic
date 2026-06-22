/**
 * stele-inline.js — Pyodide glue for the Stele single-file distribution.
 *
 * Identical to stele-pyodide.js except that the Stele source zip is read
 * from window.__steleZipB64 (base64-encoded, embedded at build time) rather
 * than fetched from a sibling URL.
 *
 * No backend API calls are made anywhere in this file.
 * All computation runs locally in the browser via Pyodide/WASM.
 * No proof text is sent to any server.
 */

"use strict";

// ── Constants ─────────────────────────────────────────────────────────────

// CDN URL is patched by build_single_html.py; do not edit this line manually.
const PYODIDE_CDN_INDEX =
  "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
const PYODIDE_CDN_BASE =
  "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";

// ── State ─────────────────────────────────────────────────────────────────

let pyodide = null;
let steleReady = false;

// ── Loading UI ────────────────────────────────────────────────────────────

function setLoadingStep(msg) {
  const el = document.getElementById("loading-step");
  if (el) el.textContent = msg;
}

function setLoadingBar(pct) {
  const bar = document.getElementById("loading-bar");
  if (bar) bar.style.width = Math.min(100, pct) + "%";
}

function hideLoadingBanner() {
  const el = document.getElementById("studio-loading");
  if (el) {
    el.classList.add("hidden");
    setTimeout(() => { el.style.display = "none"; }, 450);
  }
}

function setButtonsEnabled(enabled) {
  document.querySelectorAll("button[data-stele]").forEach(btn => {
    btn.disabled = !enabled;
  });
}

// ── Pyodide bootstrap ──────────────────────────────────────────────────────

async function loadPyodideScript() {
  return new Promise((resolve, reject) => {
    if (window.loadPyodide) { resolve(); return; }
    const script = document.createElement("script");
    script.src = PYODIDE_CDN_INDEX;
    script.onload = resolve;
    script.onerror = () =>
      reject(new Error(
        "Failed to load Pyodide from CDN. " +
        "This file requires an internet connection for the first load."
      ));
    document.head.appendChild(script);
  });
}

/** Decode the embedded base64 zip into an ArrayBuffer. */
function getEmbeddedZipBuffer() {
  const b64 = window.__steleZipB64;
  if (!b64) {
    throw new Error(
      "Embedded Stele source not found. " +
      "This file may be damaged or was not built with build_single_html.py."
    );
  }
  const binStr = atob(b64);
  const bytes = new Uint8Array(binStr.length);
  for (let i = 0; i < binStr.length; i++) bytes[i] = binStr.charCodeAt(i);
  return bytes.buffer;
}

async function initStele() {
  try {
    setLoadingStep("Loading Pyodide runtime from CDN (~8 MB, cached after first visit)…");
    setLoadingBar(5);
    await loadPyodideScript();

    setLoadingStep("Initialising Python/WASM environment…");
    setLoadingBar(25);
    pyodide = await window.loadPyodide({ indexURL: PYODIDE_CDN_BASE });

    setLoadingStep("Unpacking embedded Stele source…");
    setLoadingBar(65);
    const buf = getEmbeddedZipBuffer();
    pyodide.unpackArchive(buf, "zip", { extractDir: "/home/pyodide" });

    setLoadingStep("Importing stele.browser…");
    setLoadingBar(88);
    await pyodide.runPythonAsync("import stele.browser as _sb");

    setLoadingStep("Ready.");
    setLoadingBar(100);
    steleReady = true;

    hideLoadingBanner();
    setButtonsEnabled(true);
    showStatus("ready", "Stele loaded — all verification runs locally in this browser.");

    await loadExamples();
  } catch (err) {
    setLoadingStep("Error: " + err.message);
    showStatus("error", "Failed to initialise: " + err.message);
    console.error("[stele-inline] init error:", err);
  }
}

// ── Python call helpers ────────────────────────────────────────────────────

async function callBrowser(fn, args) {
  if (!steleReady) throw new Error("Stele is not ready yet.");
  for (const [k, v] of Object.entries(args)) {
    pyodide.globals.set("_arg_" + k, v);
  }
  const argList = Object.keys(args).map(k => "_arg_" + k).join(", ");
  const code = `import json; json.dumps(_sb.${fn}(${argList}))`;
  const raw = await pyodide.runPythonAsync(code);
  return JSON.parse(raw);
}

// ── Status bar ─────────────────────────────────────────────────────────────

function showStatus(kind, msg) {
  const bar = document.getElementById("status-bar");
  if (!bar) return;
  bar.textContent = msg;
  bar.className = "studio-status-bar";
  bar.style.display = "block";
  if (kind === "error") bar.style.color = "var(--red)";
  else if (kind === "ready") bar.style.color = "var(--green)";
  else bar.style.color = "";
}

// ── Tab navigation ─────────────────────────────────────────────────────────

function activateTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    const active = btn.dataset.tab === tabId;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });
  document.querySelectorAll(".panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === "panel-" + tabId);
  });
}

// ── HTML escaping ──────────────────────────────────────────────────────────

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ── Result rendering ───────────────────────────────────────────────────────

function showResult(elId, html, kind) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.innerHTML = html;
  el.className = "result-box show" + (kind ? " result-" + kind : "");
}

// ── Panel: Verify ──────────────────────────────────────────────────────────

async function runCheck() {
  const source = document.getElementById("proof-input").value.trim();
  const logic  = document.getElementById("logic-select").value;
  if (!source) { showResult("check-result", "Enter a proof above.", "info"); return; }

  showResult("check-result", "Checking…", "info");
  try {
    const r = await callBrowser("browser_check", { proof_text: source, logic });
    if (r.ok) {
      showResult("check-result",
        `✓ Valid  |  theorem: <strong>${esc(r.name)}</strong>  |  logic: ${esc(r.logic)}`,
        "ok");
    } else {
      const line = r.line ? ` (line ${r.line})` : "";
      showResult("check-result",
        `✗ ${esc(r.kind || "error")}${line}: ${esc(r.error)}`, "err");
    }
  } catch (e) {
    showResult("check-result", "Internal error: " + esc(e.message), "err");
  }
}

// ── Panel: Diagnostics ──────────────────────────────────────────────────────

async function runDiagnose() {
  const source = document.getElementById("proof-input").value.trim();
  const logic  = document.getElementById("logic-select").value;
  const out    = document.getElementById("diag-result");
  if (!source) { out.innerHTML = `<p class="dim-text">Enter a proof in the Verify panel first.</p>`; return; }

  out.innerHTML = `<p class="dim-text">Running diagnostics…</p>`;
  try {
    const r = await callBrowser("browser_diagnose", { proof_text: source, logic });
    if (!r.ok) { out.innerHTML = `<p style='color:var(--red)'>${esc(r.error)}</p>`; return; }
    const diags = r.diagnostics || [];
    if (!diags.length) {
      out.innerHTML = `<p style='color:var(--green)'>No diagnostics — proof structure looks clean.</p>`;
      return;
    }
    out.innerHTML = `<ul class="diag-list">${diags.map(d => `
      <li class="diag-item ${esc(d.severity || "info")}">
        <div class="diag-code">${esc(d.code || "")}</div>
        <div class="diag-msg">${esc(d.message)}</div>
        ${d.line ? `<div class="diag-line">line ${d.line}</div>` : ""}
      </li>`).join("")}</ul>`;
  } catch (e) {
    out.innerHTML = `<p style='color:var(--red)'>Error: ${esc(e.message)}</p>`;
  }
}

// ── Panel: Graph ───────────────────────────────────────────────────────────

async function runGraph() {
  const source = document.getElementById("proof-input").value.trim();
  const logic  = document.getElementById("logic-select").value;
  const dotOut = document.getElementById("graph-dot");
  const nodes  = document.getElementById("graph-nodes");
  if (!source) {
    dotOut.textContent = "Enter a proof in the Verify panel first.";
    dotOut.style.display = "block"; return;
  }
  dotOut.textContent = "Building graph…"; dotOut.style.display = "block"; nodes.innerHTML = "";
  try {
    const r = await callBrowser("browser_graph", { proof_text: source, logic });
    if (!r.ok) { dotOut.textContent = `Error: ${r.error}`; return; }
    dotOut.textContent = r.dot || "(no DOT output)";
    nodes.innerHTML = (r.nodes || []).map(n => `
      <div class="graph-node">
        <div class="lbl">${esc(n.label)}</div>
        <div class="knd">${esc(n.kind)}${n.rule ? " · " + esc(n.rule) : ""}</div>
        <div class="frm">${esc(n.formula || "")}</div>
      </div>`).join("");
  } catch (e) { dotOut.textContent = "Error: " + e.message; }
}

// ── Panel: Semantics — Soundness ───────────────────────────────────────────

async function runSoundness() {
  const logic  = document.getElementById("sem-logic-select").value;
  const matrix = document.getElementById("sem-matrix-select").value;
  const out    = document.getElementById("soundness-result");
  out.innerHTML = `<p class="dim-text">Checking…</p>`;
  try {
    const r = await callBrowser("browser_soundness", { logic, matrix });
    if (!r.ok) { out.innerHTML = `<p style='color:var(--red)'>${esc(r.error)}</p>`; return; }
    const rows = (r.rules || []).map(rule => {
      const cls = rule.status === "sound" ? "sound" : rule.status === "unsound" ? "unsound" : "skipped";
      const cx  = rule.counterexample
        ? `<br><small style='color:var(--muted)'>counterexample: ${esc(JSON.stringify(rule.counterexample))}</small>`
        : "";
      return `<tr><td>${esc(rule.rule)}</td><td class="${cls}">${esc(rule.status)}${cx}</td></tr>`;
    }).join("");
    out.innerHTML = `
      <p style='font-size:.8rem;color:var(--muted);margin-bottom:8px'>
        Logic <strong style='color:var(--text)'>${esc(r.logic)}</strong>
        · matrix <strong style='color:var(--text)'>${esc(r.matrix)}</strong>
      </p>
      <table class="soundness-table">
        <thead><tr><th>Rule</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    out.innerHTML = `<p style='color:var(--red)'>Error: ${esc(e.message)}</p>`;
  }
}

// ── Panel: Semantics — Lattice ─────────────────────────────────────────────

async function runLattice() {
  const formula = document.getElementById("lattice-input").value.trim();
  const out     = document.getElementById("lattice-result");
  if (!formula) { out.innerHTML = `<p class="dim-text">Enter a formula above.</p>`; return; }
  out.innerHTML = `<p class="dim-text">Computing…</p>`;
  try {
    const r = await callBrowser("browser_lattice", { formula });
    if (!r.ok) { out.innerHTML = `<p style='color:var(--red)'>${esc(r.error)}</p>`; return; }
    const rows = (r.rows || []).map(row =>
      `<tr>
        <td>${esc(row.label)}</td>
        <td style='color:var(--muted);font-size:.75rem'>${row.axioms.length ? row.axioms.map(esc).join(", ") : "∅"}</td>
        <td class="status-${esc(row.status)}">${esc(row.status)}</td>
      </tr>`).join("");
    out.innerHTML = `
      <p style='font-size:.8rem;color:var(--muted);margin-bottom:8px'>
        Formula: <strong style='color:var(--cyan)'>${esc(r.formula)}</strong>
      </p>
      <table class="lattice-table">
        <thead><tr><th>World</th><th>Axioms</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    out.innerHTML = `<p style='color:var(--red)'>Error: ${esc(e.message)}</p>`;
  }
}

// ── Panel: Examples ────────────────────────────────────────────────────────

const EXAMPLE_DESCRIPTIONS = {
  "dne.stele":             "Double negation elimination — classical only",
  "imp_self.stele":        "A → A — valid in all logics",
  "invalid_mp.stele":      "Malformed modus ponens — type mismatch",
  "lem.stele":             "Law of excluded middle — classical only",
  "neg_intro.stele":       "Negation introduction: ¬(P ∧ ¬P)",
  "valid_and.stele":       "Conjunction introduction and elimination",
  "or_comm.stele":         "Disjunction commutativity",
  "or_intro.stele":        "Disjunction introduction",
  "ex_falso.stele":        "Ex falso quodlibet — from ⊥, prove anything",
  "valid_imp_chain.stele": "Hypothetical syllogism: A→B, B→C ⊢ A→C",
  "peirce.stele":          "Peirce's law — classical only",
  "dne_law.stele":         "DNE as implication ¬¬A→A",
};

async function loadExamples() {
  const grid = document.getElementById("examples-grid");
  if (!grid) return;
  try {
    const r = await callBrowser("browser_examples", {});
    const examples = r.examples || {};
    const keys = Object.keys(examples);
    if (!keys.length) { grid.innerHTML = `<p class="dim-text">No examples bundled.</p>`; return; }
    grid.innerHTML = keys.map(fn => {
      const desc = EXAMPLE_DESCRIPTIONS[fn] || fn;
      return `<div class="example-card" tabindex="0" role="button"
          aria-label="Load example: ${esc(fn)}"
          data-filename="${esc(fn)}"
          data-content="${esc(examples[fn])}">
        <div class="ex-name">${esc(fn)}</div>
        <div class="ex-desc">${esc(desc)}</div>
      </div>`;
    }).join("");
    grid.querySelectorAll(".example-card").forEach(card => {
      card.addEventListener("click", () => loadExampleCard(card));
      card.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); loadExampleCard(card); }
      });
    });
  } catch (e) {
    grid.innerHTML = `<p style='color:var(--red)'>Failed to load examples: ${esc(e.message)}</p>`;
  }
}

function loadExampleCard(card) {
  const content = card.dataset.content;
  const fn = card.dataset.filename;
  const editor = document.getElementById("proof-input");
  if (editor) editor.value = content;
  const resultBox = document.getElementById("check-result");
  if (resultBox) resultBox.className = "result-box";
  activateTab("verify");
  if (editor) editor.focus();
  showStatus("info", `Loaded: ${fn}`);
}

// ── Init ───────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // Tab buttons
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });

  // Studio action buttons
  const bind = (id, fn) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  };
  bind("btn-check",     runCheck);
  bind("btn-diagnose",  runDiagnose);
  bind("btn-graph",     runGraph);
  bind("btn-soundness", runSoundness);
  bind("btn-lattice",   runLattice);

  // Ctrl+Enter in proof editor → run check
  const editor = document.getElementById("proof-input");
  if (editor) {
    editor.addEventListener("keydown", e => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault(); runCheck();
      }
    });
  }

  // Disable Studio buttons until Pyodide is ready
  setButtonsEnabled(false);

  // Start Pyodide initialisation
  initStele();
});
