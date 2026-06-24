/**
 * stele-pyodide.js — Pyodide glue for the Stele browser Studio.
 *
 * Architecture:
 *   1. Load Pyodide from the pinned CDN.
 *   2. Fetch stele_source.zip and extract into Pyodide's virtual filesystem.
 *   3. Import stele.browser inside Pyodide.
 *   4. Expose wrapper functions: check, diagnose, graph, soundness, lattice, kripke, examples.
 *   5. Manage loading state in the Studio section (not a full-page overlay).
 *   6. Expose window.stele.loadPreset() for the gallery/tutorial sections.
 *
 * No backend API calls are made anywhere in this file.
 * All computation runs locally in the browser via Pyodide/WASM.
 * No proof text is sent to any server.
 */

"use strict";

// ── Constants ─────────────────────────────────────────────────────────────

const PYODIDE_CDN =
  "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";

const STELE_ZIP = "./stele_source.zip";

// ── State ─────────────────────────────────────────────────────────────────

let pyodide = null;
let steleReady = false;

// ── Gallery data ───────────────────────────────────────────────────────────
// Mirrors site/examples_gallery.json — source of truth for tests.

const GALLERY_ENTRIES = [
  {
    id: "imp_self",
    title: "Identity (P → P)",
    description: "The simplest intuitionistic proof: from hypothesis P derive P → P using imp_intro to discharge the suppose block.",
    logic: "intuitionistic_prop",
    category: "basics",
    expected: "pass",
    logic_note: null,
    proof: `theorem imp_self:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h2
  conclude P -> P by h3`,
  },
  {
    id: "and_demo",
    title: "Conjunction Intro & Elim",
    description: "Introduce P ∧ Q with and_intro, then extract each component with and_elim_left and and_elim_right.",
    logic: "intuitionistic_prop",
    category: "basics",
    expected: "pass",
    logic_note: null,
    proof: `theorem and_demo:
  assume h1: P
  assume h2: Q
  have h3: P and Q by and_intro h1 h2
  have h4: P by and_elim_left h3
  have h5: Q by and_elim_right h3
  conclude Q by h5`,
  },
  {
    id: "neg_intro",
    title: "Negation Introduction",
    description: "Prove ¬(P ∧ ¬P) by assuming P ∧ ¬P, extracting both parts, deriving ⊥, then closing with neg_intro.",
    logic: "intuitionistic_prop",
    category: "basics",
    expected: "pass",
    logic_note: null,
    proof: `theorem neg_intro_demo:
  suppose h1: P and not P
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h1 h4
  conclude not (P and not P) by h5`,
  },
  {
    id: "ex_falso",
    title: "Ex Falso Quodlibet",
    description: "From P and ¬P derive ⊥, then prove any formula Q by ex_falso. A contradiction entails everything.",
    logic: "intuitionistic_prop",
    category: "basics",
    expected: "pass",
    logic_note: null,
    proof: `theorem ex_falso_demo:
  assume h1: P
  assume h2: not P
  have h3: false by neg_elim h1 h2
  have h4: Q by ex_falso h3
  conclude Q by h4`,
  },
  {
    id: "or_comm",
    title: "Disjunction Commutativity",
    description: "From P ∨ Q derive Q ∨ P using or_elim with two suppose blocks, each closing with an or_intro step.",
    logic: "intuitionistic_prop",
    category: "basics",
    expected: "pass",
    logic_note: null,
    proof: `theorem or_comm:
  assume h1: P or Q
  suppose h2: P
    have h3: Q or P by or_intro_right h2
  suppose h4: Q
    have h5: Q or P by or_intro_left h4
  have h6: Q or P by or_elim h1 h2 h3 h4 h5
  conclude Q or P by h6`,
  },
  {
    id: "imp_chain",
    title: "Hypothetical Syllogism",
    description: "From P→Q, Q→R, and P, derive R by chaining two modus ponens steps. Valid in both logics.",
    logic: "intuitionistic_prop",
    category: "basics",
    expected: "pass",
    logic_note: null,
    proof: `theorem chain:
  assume h1: P -> Q
  assume h2: Q -> R
  assume h3: P
  have h4: Q by mp h1 h3
  have h5: R by mp h2 h4
  conclude R by h5`,
  },
  {
    id: "neg_elim",
    title: "Negation Elimination",
    description: "From P and ¬P derive ⊥ directly using neg_elim. The fundamental law of contradiction.",
    logic: "intuitionistic_prop",
    category: "basics",
    expected: "pass",
    logic_note: null,
    proof: `theorem neg_elim_demo:
  assume h1: P
  assume h2: not P
  have h3: false by neg_elim h1 h2
  conclude false by h3`,
  },
  {
    id: "dne",
    title: "Double Negation Elimination",
    description: "¬¬P → P using the dne rule. Accepted by classical logic, rejected by intuitionistic — switch the logic to see the difference.",
    logic: "classical_prop",
    category: "classical",
    expected: "pass",
    logic_note: "classical only",
    proof: `theorem dne_consequent:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2`,
  },
  {
    id: "lem",
    title: "Law of Excluded Middle",
    description: "P ∨ ¬P using the lem rule. A hallmark of classical logic — not derivable intuitionistically.",
    logic: "classical_prop",
    category: "classical",
    expected: "pass",
    logic_note: "classical only",
    proof: `theorem lem_demo using classical_prop:
  have h: P or not P by lem
  conclude P or not P by h`,
  },
  {
    id: "peirce",
    title: "Peirce's Law",
    description: "((P→Q)→P)→P — a classical tautology with a complex nested proof using proof by contradiction (pbc).",
    logic: "classical_prop",
    category: "classical",
    expected: "pass",
    logic_note: "classical only",
    proof: `theorem peirce using classical_prop:
  suppose h: (P -> Q) -> P
    suppose hnp: not P
      suppose hp: P
        have hbot: false by neg_elim hp hnp
        have hq: Q by ex_falso hbot
      have hpq: P -> Q by imp_intro hp hq
      have hp2: P by mp h hpq
      have hbot2: false by neg_elim hp2 hnp
    have hp3: P by pbc hnp hbot2
  have h_thm: ((P -> Q) -> P) -> P by imp_intro h hp3
  conclude ((P -> Q) -> P) -> P by h_thm`,
  },
  {
    id: "invalid_mp",
    title: "Type Mismatch (error)",
    description: "mp requires the second premise to match the antecedent of the implication. h1 is P→Q but h2 is R, not P — InvalidTransition error.",
    logic: "intuitionistic_prop",
    category: "diagnostics",
    expected: "fail",
    logic_note: null,
    proof: `theorem bad_mp:
  assume h1: P -> Q
  assume h2: R
  have h3: Q by mp h1 h2
  conclude Q by h3`,
  },
  {
    id: "invalid_scope",
    title: "Scope Error (error)",
    description: "Hypothesis h2 introduced inside a suppose block is used after the block closes. Discharged hypotheses are out of scope.",
    logic: "intuitionistic_prop",
    category: "diagnostics",
    expected: "fail",
    logic_note: null,
    proof: `theorem leak:
  suppose h1: P
    have h2: P by copy h1
  have h3: P by copy h2
  conclude P by h3`,
  },
  {
    id: "diag_unused",
    title: "Unused Assumption (warning)",
    description: "Assumption h2 is declared but never contributes to the conclusion. The kernel accepts the proof; diagnostics report an UnusedAssumption warning.",
    logic: "intuitionistic_prop",
    category: "diagnostics",
    expected: "warn",
    logic_note: null,
    proof: `theorem diag_unused:
  assume h1: P
  assume h2: Q
  conclude P by h1`,
  },
  {
    id: "diag_undef",
    title: "Undefined Symbol (error)",
    description: "mp references 'missing', which is never introduced. The kernel reports UndefinedSymbol with an exact location.",
    logic: "intuitionistic_prop",
    category: "diagnostics",
    expected: "fail",
    logic_note: null,
    proof: `theorem diag_undef:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 missing
  conclude Q by h3`,
  },
  {
    id: "diag_conclusion",
    title: "Wrong Conclusion (error)",
    description: "The conclude step claims Q but h1 holds P — a formula mismatch. The kernel reports UnsupportedConclusion.",
    logic: "intuitionistic_prop",
    category: "diagnostics",
    expected: "fail",
    logic_note: null,
    proof: `theorem diag_conclusion:
  assume h1: P
  conclude Q by h1`,
  },
];

// ── Tutorial state ─────────────────────────────────────────────────────────

let currentTutorialStep = 1;
const TOTAL_TUTORIAL_STEPS = 6;

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
    script.src = PYODIDE_CDN;
    script.onload = resolve;
    script.onerror = () =>
      reject(new Error("Failed to load Pyodide from CDN. Check internet connection."));
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
    if (!resp.ok)
      throw new Error(`Failed to fetch ${STELE_ZIP}: ${resp.status} ${resp.statusText}`);
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

    hideLoadingBanner();
    setButtonsEnabled(true);
    showStatus("ready", "Stele loaded — all verification runs locally in this browser.");

    await loadExamples();

    /* Auto-run action if page was opened via studio.html?example=… or ?proof=… */
    if (_urlParamLoaded) {
      const _tab = (new URLSearchParams(window.location.search)).get("tab") || "verify";
      setTimeout(() => {
        if (_tab === "verify")        runCheck();
        else if (_tab === "diagnose") runDiagnose();
        else if (_tab === "graph")    runGraph();
      }, 500);
    }
  } catch (err) {
    setLoadingStep("Error: " + err.message);
    showStatus("error", "Failed to initialise: " + err.message);
    console.error("[stele-pyodide] init error:", err);
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

// ── Panel: Semantics — Kripke Countermodel ────────────────────────────────

async function runKripke() {
  const formula   = document.getElementById("kripke-input").value.trim();
  const maxWorlds = parseInt(document.getElementById("kripke-worlds-select").value) || 3;
  const out       = document.getElementById("kripke-result");
  if (!formula) { out.innerHTML = `<p class="dim-text">Enter a formula above.</p>`; return; }
  out.innerHTML = `<p class="dim-text">Searching…</p>`;
  try {
    const r = await callBrowser("browser_kripke", { formula, max_worlds: maxWorlds });
    if (r.status === "parse_error" || r.status === "unsupported_formula") {
      out.innerHTML = `<p style='color:var(--red)'>${esc(r.explanation)}</p>`; return;
    }
    if (r.status === "no_countermodel_within_bound") {
      out.innerHTML = `
        <p style='color:var(--green)'>No countermodel found (max ${esc(String(r.max_worlds))} worlds).</p>
        <p style='color:var(--muted);font-size:.75rem'>${esc(r.bound_note)}</p>`;
      return;
    }
    // countermodel_found
    const val = r.valuation || {};
    const worldRows = (r.worlds || []).map(w => {
      const atoms = val[String(w)] || [];
      const fail  = w === r.failing_world ? `<span style='color:var(--red)'>✗ fails here</span>` : "";
      return `<tr><td>${esc(String(w))}</td><td>${atoms.length ? atoms.map(esc).join(", ") : "∅"}</td><td>${fail}</td></tr>`;
    }).join("");
    const orderStr = (r.order_pairs || []).length
      ? r.order_pairs.map(p => `${esc(String(p[0]))}≤${esc(String(p[1]))}`).join(", ")
      : "discrete (reflexive only)";
    out.innerHTML = `
      <p style='font-size:.8rem;color:var(--muted);margin-bottom:6px'>
        Formula: <strong style='color:var(--red)'>${esc(r.formula)}</strong>
        · countermodel found
      </p>
      <p style='font-size:.75rem;margin-bottom:8px'>Order: ${orderStr}</p>
      <table class="lattice-table">
        <thead><tr><th>World</th><th>True atoms</th><th></th></tr></thead>
        <tbody>${worldRows}</tbody>
      </table>
      <p style='font-size:.75rem;color:var(--amber);margin-top:8px'>${esc(r.explanation)}</p>`;
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
  setEditorContent(content, null);
  activateTab("verify");
  document.getElementById("proof-input").focus();
  showStatus("info", `Loaded: ${fn}`);
}

// ── URL parameter support — studio.html?example=ID or ?proof=…&logic=…&tab=… ──

let _urlParamLoaded = false;

function loadFromURLParams() {
  if (typeof URLSearchParams === "undefined") return false;
  const params  = new URLSearchParams(window.location.search);
  const exId    = params.get("example");
  const proofTx = params.get("proof");
  const logic   = params.get("logic");
  const tab     = params.get("tab");

  if (exId) {
    const entry = GALLERY_ENTRIES.find(e => e.id === exId);
    if (entry) {
      setEditorContent(entry.proof, logic || entry.logic);
      if (tab) activateTab(tab);
      _urlParamLoaded = true;
      return true;
    }
  }
  if (proofTx) {
    setEditorContent(proofTx, logic);
    if (tab) activateTab(tab);
    _urlParamLoaded = true;
    return true;
  }
  return false;
}

function navigateToStudio(proof, logic, tab) {
  const p = new URLSearchParams();
  if (proof) p.set("proof", proof);
  if (logic) p.set("logic", logic);
  if (tab)   p.set("tab", tab);
  const qs = p.toString();
  window.location.href = "studio.html" + (qs ? "?" + qs : "");
}

// ── Gallery rendering (no Pyodide required) ────────────────────────────────

function renderGallery() {
  const grid = document.getElementById("gallery-grid");
  if (!grid) return; /* studio.html has no #gallery-grid — exits immediately */

  const cards = GALLERY_ENTRIES.map(entry => {
    const tagClass = entry.category === "classical" ? "tag-classical"
                   : entry.category === "diagnostics" ? "tag-diag"
                   : "tag-valid";
    const tagText = entry.category === "classical" ? "Classical only"
                  : entry.category === "diagnostics" ? "Diagnostic"
                  : "Intuitionistic";
    const expClass = entry.expected === "pass" ? "gcard-exp-pass"
                   : entry.expected === "warn" ? "gcard-exp-warn"
                   : "gcard-exp-fail";
    const expText = entry.expected === "pass" ? "✓ Valid"
                  : entry.expected === "warn" ? "⚠ Warning"
                  : "✗ Error";

    const lines = entry.proof.split("\n");
    const preview = lines.slice(0, 6).join("\n") + (lines.length > 6 ? "\n  …" : "");

    return `<article class="gallery-card" aria-label="${esc(entry.title)}">
      <div class="gcard-header">
        <span class="gcard-tag ${tagClass}">${tagText}</span>
        <span class="gcard-expected ${expClass}">${expText}</span>
      </div>
      <h3 class="gcard-title">${esc(entry.title)}</h3>
      <p class="gcard-desc">${esc(entry.description)}</p>
      <pre class="gcard-code" aria-hidden="true">${esc(preview)}</pre>
      <a class="btn btn-ghost gcard-btn"
         href="studio.html?example=${esc(entry.id)}"
         aria-label="Open ${esc(entry.title)} in Studio">
        Open in Studio →
      </a>
    </article>`;
  }).join("");

  grid.innerHTML = cards;
}

// ── Gallery preset loader (global) ─────────────────────────────────────────

function setEditorContent(proof, logic) {
  const editor   = document.getElementById("proof-input");
  const logicSel = document.getElementById("logic-select");
  if (editor)   editor.value = proof;
  if (logicSel && logic) logicSel.value = logic;
  const resultBox = document.getElementById("check-result");
  if (resultBox) resultBox.className = "result-box";
  const diagResult = document.getElementById("diag-result");
  if (diagResult) diagResult.innerHTML = "";
}

/**
 * loadPreset — loads a proof into the editor.
 * On studio.html: loads directly and auto-runs.
 * On other pages: navigates to studio.html with the proof as a URL parameter.
 */
function loadPreset(proof, logic) {
  if (!document.getElementById("proof-input")) {
    navigateToStudio(proof, logic || "intuitionistic_prop", "verify");
    return;
  }
  setEditorContent(proof, logic);
  activateTab("verify");
  document.getElementById("proof-input").scrollIntoView({ behavior: "smooth", block: "nearest" });
  if (steleReady) {
    setTimeout(runCheck, 600);
  } else {
    showStatus("info", "Proof loaded — click Run Check once Stele finishes loading.");
  }
}

/**
 * loadTutorialPreset — from tutorial step buttons; loads proof, activates panel,
 * and auto-runs the appropriate action if Stele is ready.
 * Only called when already on the Studio page.
 */
function loadTutorialPreset(proof, logic, tab) {
  if (proof) setEditorContent(proof, logic);
  if (tab) setTimeout(() => activateTab(tab), 300);

  if (steleReady && proof) {
    const delay = 700;
    if (!tab || tab === "verify") setTimeout(runCheck, delay);
    else if (tab === "diagnose") setTimeout(runDiagnose, delay);
    else if (tab === "graph") setTimeout(runGraph, delay);
  } else if (proof) {
    showStatus("info", "Proof loaded — click the button in the panel once Stele finishes loading.");
  }
}

// ── Tutorial navigation ────────────────────────────────────────────────────

function showTutorialStep(n) {
  if (n < 1 || n > TOTAL_TUTORIAL_STEPS) return;
  currentTutorialStep = n;

  for (let i = 1; i <= TOTAL_TUTORIAL_STEPS; i++) {
    const step = document.getElementById("tstep-" + i);
    if (step) step.classList.toggle("active", i === n);
  }

  document.querySelectorAll(".tut-dot").forEach(dot => {
    const stepNum = parseInt(dot.dataset.step, 10);
    dot.classList.toggle("active", stepNum === n);
    dot.setAttribute("aria-current", stepNum === n ? "true" : "false");
  });

  const counter = document.getElementById("tut-counter");
  if (counter) counter.textContent = `Step ${n} of ${TOTAL_TUTORIAL_STEPS}`;

  const prev = document.getElementById("tut-prev");
  const next = document.getElementById("tut-next");
  if (prev) prev.disabled = n <= 1;
  if (next) {
    next.disabled = n >= TOTAL_TUTORIAL_STEPS;
    next.textContent = n >= TOTAL_TUTORIAL_STEPS ? "Done ✓" : "Next →";
  }
}

// ── Init ───────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  /* Detect whether we're on the Studio workbench page or the landing page */
  const onStudioPage = !!document.getElementById("proof-input");

  if (onStudioPage) {
    /* ── Studio page: wire tabs, action buttons, Ctrl+Enter, then init Pyodide ── */

    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => activateTab(btn.dataset.tab));
    });

    const bind = (id, fn) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener("click", fn);
    };
    bind("btn-check",     runCheck);
    bind("btn-diagnose",  runDiagnose);
    bind("btn-graph",     runGraph);
    bind("btn-soundness", runSoundness);
    bind("btn-lattice",   runLattice);
    bind("btn-kripke",    runKripke);

    const editor = document.getElementById("proof-input");
    if (editor) {
      editor.addEventListener("keydown", e => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
          e.preventDefault(); runCheck();
        }
      });
    }

    /* Pre-populate editor from ?example= or ?proof= URL params before Pyodide loads */
    loadFromURLParams();

    /* Disable action buttons until Pyodide is ready, then initialise */
    setButtonsEnabled(false);
    initStele();
  }

  /* ── Both pages: gallery (landing only due to #gallery-grid guard) + tutorial nav ── */

  renderGallery();

  showTutorialStep(1);

  document.querySelectorAll(".tut-dot").forEach(dot => {
    dot.addEventListener("click", () => showTutorialStep(parseInt(dot.dataset.step, 10)));
  });

  const prevBtn = document.getElementById("tut-prev");
  const nextBtn = document.getElementById("tut-next");
  if (prevBtn) prevBtn.addEventListener("click", () => showTutorialStep(currentTutorialStep - 1));
  if (nextBtn) nextBtn.addEventListener("click", () => showTutorialStep(currentTutorialStep + 1));

  /* Tutorial "Load & run in Studio" buttons — navigate to studio.html from landing */
  document.querySelectorAll(".tut-load-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const proof = btn.dataset.proof || null;
      const logic = btn.dataset.logic || "intuitionistic_prop";
      const tab   = btn.dataset.tab   || "verify";
      if (onStudioPage) {
        loadTutorialPreset(proof, logic, tab);
      } else {
        navigateToStudio(proof, logic, tab);
      }
    });
  });

  /* Tutorial "open tab" buttons — navigate to studio.html?tab=… from landing */
  document.querySelectorAll(".tut-open-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      if (onStudioPage) {
        if (tab) activateTab(tab);
      } else {
        window.location.href = "studio.html" + (tab ? "?tab=" + encodeURIComponent(tab) : "");
      }
    });
  });
});

// Expose globally for gallery/tutorial onclick handlers and external scripts
window.stele = { loadPreset, loadTutorialPreset, runCheck, activateTab, navigateToStudio };
