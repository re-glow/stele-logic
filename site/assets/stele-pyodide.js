/**
 * stele-pyodide.js — Pyodide glue for the Stele browser Studio.
 *
 * Architecture:
 *   1. Load Pyodide from the pinned CDN (several MB, first visit only).
 *   2. Fetch stele_source.zip and extract into Pyodide's virtual filesystem.
 *   3. Import stele.browser inside Pyodide.
 *   4. Expose wrapper functions: check, diagnose, graph, soundness, lattice, examples.
 *   5. Manage loading state and disable/enable UI elements.
 *
 * IMPORTANT: No backend API calls are made anywhere in this file.
 *            All computation runs locally in the browser via Pyodide/WASM.
 *            No proof text is sent to any server.
 */

"use strict";

// ── Constants ────────────────────────────────────────────────────────────────

const PYODIDE_CDN =
  "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";

const STELE_ZIP = "./stele_source.zip";

// ── State ────────────────────────────────────────────────────────────────────

let pyodide = null;
let steleReady = false;

// ── Loading UI helpers ───────────────────────────────────────────────────────

function setLoadingStep(msg) {
  const el = document.getElementById("loading-step");
  if (el) el.textContent = msg;
}

function setLoadingBar(pct) {
  const bar = document.getElementById("loading-bar");
  if (bar) bar.style.width = Math.min(100, pct) + "%";
}

function hideLoadingOverlay() {
  const el = document.getElementById("loading-overlay");
  if (el) {
    el.classList.add("hidden");
    setTimeout(() => { el.style.display = "none"; }, 400);
  }
}

function setButtonsEnabled(enabled) {
  document.querySelectorAll("button[data-stele]").forEach(btn => {
    btn.disabled = !enabled;
  });
}

// ── Pyodide bootstrap ────────────────────────────────────────────────────────

async function loadPyodideScript() {
  return new Promise((resolve, reject) => {
    if (window.loadPyodide) { resolve(); return; }
    const script = document.createElement("script");
    script.src = PYODIDE_CDN;
    script.onload = resolve;
    script.onerror = () => reject(new Error("Failed to load Pyodide from CDN. Check your internet connection."));
    document.head.appendChild(script);
  });
}

async function initStele() {
  try {
    setLoadingStep("Downloading Pyodide runtime (~8 MB, cached after first visit)…");
    setLoadingBar(5);
    await loadPyodideScript();

    setLoadingStep("Initialising Python/WASM environment…");
    setLoadingBar(25);
    pyodide = await window.loadPyodide({
      indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/",
    });

    setLoadingStep("Fetching Stele source bundle…");
    setLoadingBar(55);
    const resp = await fetch(STELE_ZIP);
    if (!resp.ok) throw new Error(`Failed to fetch ${STELE_ZIP}: ${resp.status} ${resp.statusText}`);
    const buf = await resp.arrayBuffer();

    setLoadingStep("Extracting Stele modules into virtual filesystem…");
    setLoadingBar(72);
    pyodide.unpackArchive(buf, "zip", { extractDir: "/home/pyodide" });

    setLoadingStep("Importing stele.browser…");
    setLoadingBar(88);
    await pyodide.runPythonAsync("import stele.browser as _sb");

    setLoadingStep("Ready.");
    setLoadingBar(100);
    steleReady = true;

    hideLoadingOverlay();
    setButtonsEnabled(true);
    showStatus("ready", "Stele loaded. All verification runs locally in this browser.");

    await loadExamples();
  } catch (err) {
    setLoadingStep("Error: " + err.message);
    showStatus("error", "Failed to initialise: " + err.message);
    console.error("[stele-pyodide] init error:", err);
  }
}

// ── Python call helpers ──────────────────────────────────────────────────────

async function callPython(code) {
  if (!steleReady) throw new Error("Stele is not ready yet.");
  const result = await pyodide.runPythonAsync(code);
  return JSON.parse(result);
}

async function callBrowser(fn, args) {
  // Set args as Pyodide globals to avoid injection
  for (const [k, v] of Object.entries(args)) {
    pyodide.globals.set("_arg_" + k, v);
  }
  const argList = Object.keys(args).map(k => "_arg_" + k).join(", ");
  const code = `import json; json.dumps(_sb.${fn}(${argList}))`;
  return callPython(code);
}

// ── Status bar ───────────────────────────────────────────────────────────────

function showStatus(kind, msg) {
  const bar = document.getElementById("status-bar");
  if (!bar) return;
  bar.textContent = msg;
  bar.className = "status-bar status-" + kind;
  bar.style.display = "block";
}

// ── Tab navigation ───────────────────────────────────────────────────────────

function activateTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
    btn.setAttribute("aria-selected", btn.dataset.tab === tabId ? "true" : "false");
  });
  document.querySelectorAll(".panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === "panel-" + tabId);
  });
}

// ── Result rendering ─────────────────────────────────────────────────────────

function showResult(elId, html, kind) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.innerHTML = html;
  el.className = "result-box show result-" + (kind || "info");
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Panel: Verify ────────────────────────────────────────────────────────────

async function runCheck() {
  const source = document.getElementById("proof-input").value.trim();
  const logic = document.getElementById("logic-select").value;
  if (!source) { showResult("check-result", "Enter a proof above.", "info"); return; }

  showResult("check-result", "Checking…", "info");
  try {
    const r = await callBrowser("browser_check", { proof_text: source, logic });
    if (r.ok) {
      showResult(
        "check-result",
        `✓ Valid  |  theorem: <strong>${escHtml(r.name)}</strong>  |  logic: ${escHtml(r.logic)}`,
        "ok"
      );
    } else {
      const line = r.line ? ` (line ${r.line})` : "";
      showResult("check-result", `✗ ${escHtml(r.kind || "error")}${line}: ${escHtml(r.error)}`, "err");
    }
  } catch (e) {
    showResult("check-result", "Internal error: " + escHtml(e.message), "err");
  }
}

// ── Panel: Diagnostics ───────────────────────────────────────────────────────

async function runDiagnose() {
  const source = document.getElementById("proof-input").value.trim();
  const logic = document.getElementById("logic-select").value;
  if (!source) { document.getElementById("diag-result").innerHTML = "<p style='color:var(--muted)'>Enter a proof in the Verify panel first.</p>"; return; }

  document.getElementById("diag-result").innerHTML = "<p style='color:var(--muted)'>Running diagnostics…</p>";
  try {
    const r = await callBrowser("browser_diagnose", { proof_text: source, logic });
    const diags = r.diagnostics || [];
    if (!r.ok) {
      document.getElementById("diag-result").innerHTML =
        `<p style='color:var(--red)'>${escHtml(r.error)}</p>`;
      return;
    }
    if (diags.length === 0) {
      document.getElementById("diag-result").innerHTML =
        `<p style='color:var(--green)'>No diagnostics — proof structure looks clean.</p>`;
      return;
    }
    const items = diags.map(d => {
      const sv = d.severity || "info";
      const lineStr = d.line ? `<div class="diag-line">line ${d.line}</div>` : "";
      return `<li class="diag-item ${escHtml(sv)}">
        <div class="diag-code">${escHtml(d.code || "")}</div>
        <div class="diag-msg">${escHtml(d.message)}</div>
        ${lineStr}
      </li>`;
    }).join("");
    document.getElementById("diag-result").innerHTML = `<ul class="diag-list">${items}</ul>`;
  } catch (e) {
    document.getElementById("diag-result").innerHTML =
      `<p style='color:var(--red)'>Error: ${escHtml(e.message)}</p>`;
  }
}

// ── Panel: Graph ─────────────────────────────────────────────────────────────

async function runGraph() {
  const source = document.getElementById("proof-input").value.trim();
  const logic = document.getElementById("logic-select").value;
  const dotOut = document.getElementById("graph-dot");
  const nodesOut = document.getElementById("graph-nodes");
  if (!source) {
    dotOut.textContent = "Enter a proof in the Verify panel first.";
    dotOut.style.display = "block"; return;
  }

  dotOut.textContent = "Building graph…";
  dotOut.style.display = "block";
  nodesOut.innerHTML = "";
  try {
    const r = await callBrowser("browser_graph", { proof_text: source, logic });
    if (!r.ok) {
      dotOut.textContent = `Error: ${r.error}`;
      return;
    }
    dotOut.textContent = r.dot || "(no DOT output)";
    const nodes = r.nodes || [];
    nodesOut.innerHTML = nodes.map(n => `
      <div class="graph-node">
        <div class="lbl">${escHtml(n.label)}</div>
        <div class="knd">${escHtml(n.kind)}${n.rule ? " · " + escHtml(n.rule) : ""}</div>
        <div class="frm">${escHtml(n.formula || "")}</div>
      </div>`).join("");
  } catch (e) {
    dotOut.textContent = "Error: " + e.message;
  }
}

// ── Panel: Semantics — Soundness ─────────────────────────────────────────────

async function runSoundness() {
  const logic = document.getElementById("sem-logic-select").value;
  const matrix = document.getElementById("sem-matrix-select").value;
  const out = document.getElementById("soundness-result");
  out.innerHTML = "Checking…";

  try {
    const r = await callBrowser("browser_soundness", { logic, matrix });
    if (!r.ok) { out.innerHTML = `<p style='color:var(--red)'>${escHtml(r.error)}</p>`; return; }
    const rows = (r.rules || []).map(rule => {
      const cls = rule.status === "sound" ? "sound" : rule.status === "unsound" ? "unsound" : "skipped";
      let cx = "";
      if (rule.counterexample) {
        cx = `<br><small style='color:var(--muted)'>counterexample: ${escHtml(JSON.stringify(rule.counterexample))}</small>`;
      }
      return `<tr>
        <td>${escHtml(rule.rule)}</td>
        <td class="${cls}">${escHtml(rule.status)}${cx}</td>
      </tr>`;
    }).join("");
    out.innerHTML = `
      <p style='font-size:.8rem;color:var(--muted);margin-bottom:8px'>
        Logic <strong style='color:var(--text)'>${escHtml(r.logic)}</strong>
        against matrix <strong style='color:var(--text)'>${escHtml(r.matrix)}</strong>
      </p>
      <table class="soundness-table">
        <thead><tr><th>Rule</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    out.innerHTML = `<p style='color:var(--red)'>Error: ${escHtml(e.message)}</p>`;
  }
}

// ── Panel: Semantics — Lattice ────────────────────────────────────────────────

async function runLattice() {
  const formula = document.getElementById("lattice-input").value.trim();
  const out = document.getElementById("lattice-result");
  if (!formula) { out.innerHTML = `<p style='color:var(--muted)'>Enter a formula above.</p>`; return; }
  out.innerHTML = "Computing…";

  try {
    const r = await callBrowser("browser_lattice", { formula });
    if (!r.ok) { out.innerHTML = `<p style='color:var(--red)'>${escHtml(r.error)}</p>`; return; }
    const rows = (r.rows || []).map(row => {
      const axioms = row.axioms.length ? row.axioms.map(escHtml).join(", ") : "∅";
      return `<tr>
        <td>${escHtml(row.label)}</td>
        <td style='color:var(--muted);font-size:.75rem'>${axioms}</td>
        <td class="status-${escHtml(row.status)}">${escHtml(row.status)}</td>
      </tr>`;
    }).join("");
    out.innerHTML = `
      <p style='font-size:.8rem;color:var(--muted);margin-bottom:8px'>
        Formula: <strong style='color:var(--cyan)'>${escHtml(r.formula)}</strong>
      </p>
      <table class="lattice-table">
        <thead><tr><th>World</th><th>Axioms</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    out.innerHTML = `<p style='color:var(--red)'>Error: ${escHtml(e.message)}</p>`;
  }
}

// ── Panel: Examples ───────────────────────────────────────────────────────────

const EXAMPLE_DESCRIPTIONS = {
  "dne.stele":        "Double negation elimination — valid classically, rejected intuitionistically",
  "imp_self.stele":   "A → A — valid in all logics",
  "invalid_mp.stele": "Malformed modus ponens — type mismatch",
  "lem.stele":        "Law of excluded middle (P ∨ ¬P) — classical only",
  "neg_intro.stele":  "Negation introduction — ¬(P ∧ ¬P)",
  "valid_and.stele":  "Conjunction introduction and elimination",
  "or_comm.stele":    "Disjunction commutativity",
  "or_intro.stele":   "Disjunction introduction",
  "ex_falso.stele":   "Ex falso quodlibet — from ⊥, prove anything",
  "valid_imp_chain.stele": "Hypothetical syllogism: A→B, B→C ⊢ A→C",
  "peirce.stele":     "Peirce's law — classical only",
  "dne_law.stele":    "DNE as implication ¬¬A→A",
};

async function loadExamples() {
  const grid = document.getElementById("examples-grid");
  if (!grid) return;
  try {
    const r = await callBrowser("browser_examples", {});
    const examples = r.examples || {};
    const keys = Object.keys(examples);
    if (keys.length === 0) {
      grid.innerHTML = `<p style='color:var(--muted)'>No examples bundled.</p>`;
      return;
    }
    grid.innerHTML = keys.map(fn => {
      const desc = EXAMPLE_DESCRIPTIONS[fn] || fn;
      return `<div class="example-card" tabindex="0" role="button"
          aria-label="Load example: ${escHtml(fn)}"
          data-filename="${escHtml(fn)}"
          data-content="${escHtml(examples[fn])}">
        <div class="ex-name">${escHtml(fn)}</div>
        <div class="ex-desc">${escHtml(desc)}</div>
      </div>`;
    }).join("");
    grid.querySelectorAll(".example-card").forEach(card => {
      card.addEventListener("click", () => loadExample(card));
      card.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); loadExample(card); }
      });
    });
  } catch (e) {
    grid.innerHTML = `<p style='color:var(--red)'>Failed to load examples: ${escHtml(e.message)}</p>`;
  }
}

function loadExample(card) {
  const content = card.dataset.content;
  const fn = card.dataset.filename;
  const editor = document.getElementById("proof-input");
  if (editor) {
    editor.value = content;
    // Clear previous results
    document.getElementById("check-result").className = "result-box";
    document.getElementById("diag-result").innerHTML = "";
    // Switch to Verify tab
    activateTab("verify");
    editor.focus();
    showStatus("info", `Loaded example: ${fn}`);
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // Tab buttons
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });

  // Action buttons
  const bind = (id, fn) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  };

  bind("btn-check",     runCheck);
  bind("btn-diagnose",  runDiagnose);
  bind("btn-graph",     runGraph);
  bind("btn-soundness", runSoundness);
  bind("btn-lattice",   runLattice);

  // Keyboard shortcut: Ctrl+Enter in proof editor → run check
  const editor = document.getElementById("proof-input");
  if (editor) {
    editor.addEventListener("keydown", e => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        runCheck();
      }
    });
  }

  // Disable all stele buttons until ready
  setButtonsEnabled(false);

  // Start Pyodide init
  initStele();
});
