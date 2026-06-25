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

/* Reduced-motion preference */
const reduced = typeof window !== "undefined" &&
  window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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

/* Step indices: 1=pyodide download, 2=kernel+zip, 3=examples */
function setLoadingPhase(phase) {
  /* Mark previous phases done, current active */
  for (let i = 1; i <= 3; i++) {
    const icon = document.getElementById("lstep-icon-" + i);
    if (!icon) continue;
    if (i < phase)       icon.textContent = "✓";
    else if (i === phase) icon.textContent = "›";
    else                  icon.textContent = "○";
    icon.className = "loading-step-icon" +
      (i < phase ? " lstep-done" : i === phase ? " lstep-active" : "");
  }
}

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
    setLoadingPhase(1);
    setLoadingStep("Downloading Pyodide runtime (~8 MB, cached after first visit)…");
    setLoadingBar(5);
    await loadPyodideScript();

    setLoadingPhase(1);
    setLoadingStep("Initialising Python/WASM environment…");
    setLoadingBar(25);
    pyodide = await window.loadPyodide({
      indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/",
    });

    setLoadingPhase(2);
    setLoadingStep("Loading trusted kernel — fetching Stele source bundle…");
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

    setLoadingPhase(3);
    setLoadingStep("Mounting proof examples…");
    setLoadingBar(95);

    steleReady = true;
    setLoadingBar(100);
    setLoadingPhase(3);

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
  else if (kind === "ready") bar.style.color = "var(--success)";
  else bar.style.color = "";
}

// ── Result sub-tab navigation ──────────────────────────────────────────────

function activateResultTab(tabId) {
  document.querySelectorAll(".result-tab").forEach(btn => {
    const active = btn.dataset.resultTab === tabId;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });
  document.querySelectorAll(".result-panel").forEach(p => {
    p.classList.toggle("active", p.id === "rpanel-" + tabId);
  });
}

function showResultPane() {
  const empty = document.getElementById("studio-empty-state");
  const card  = document.getElementById("studio-verdict-card");
  const tabs  = document.getElementById("result-tabs");
  if (empty) empty.hidden = true;
  if (card)  card.hidden  = false;
  if (tabs)  tabs.hidden  = false;
}

// ── Tab navigation (legacy: landing tutorial support) ─────────────────────

function activateTab(tabId) {
  /* Map old tab names to result pane tabs */
  const MAP = { verify: "result", diagnose: "diag", graph: "graph" };
  const resultTab = MAP[tabId] || tabId;
  if (resultTab === "result" || resultTab === "diag" || resultTab === "graph") {
    showResultPane();
    activateResultTab(resultTab);
  }
}

// ── HTML escaping ──────────────────────────────────────────────────────────

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ── Result rendering (legacy) ──────────────────────────────────────────────

function showResult(elId, html, kind) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.innerHTML = html;
  el.className = "result-box studio-check-result show" + (kind ? " result-" + kind : "");
}

// ── Editor gutter sync ─────────────────────────────────────────────────────

function syncGutter() {
  const ta     = document.getElementById("proof-input");
  const gutter = document.getElementById("editor-gutter");
  if (!ta || !gutter) return;
  const lines  = ta.value.split("\n");
  gutter.innerHTML = lines.map((_, i) =>
    `<span data-line="${i + 1}">${i + 1}</span>`
  ).join("");
}

function highlightErrorLine(lineNum) {
  const gutter = document.getElementById("editor-gutter");
  if (!gutter) return;
  gutter.querySelectorAll("span").forEach(span => {
    span.classList.toggle("gutter-line--err",
      parseInt(span.dataset.line) === lineNum);
  });
}

function clearErrorLine() {
  const gutter = document.getElementById("editor-gutter");
  if (!gutter) return;
  gutter.querySelectorAll("span").forEach(span => {
    span.classList.remove("gutter-line--err");
  });
  const bar = document.getElementById("editor-errorbar");
  if (bar) bar.hidden = true;
}

function showErrorBar(kind, msg) {
  const bar  = document.getElementById("editor-errorbar");
  const kEl  = document.getElementById("errorbar-kind");
  const mEl  = document.getElementById("errorbar-msg");
  if (!bar) return;
  if (kEl) kEl.textContent = kind || "";
  if (mEl) mEl.textContent = msg  || "";
  bar.hidden = false;
}

function highlightGraphLine(lineNum) {
  const gutter = document.getElementById("editor-gutter");
  if (!gutter) return;
  gutter.querySelectorAll("span").forEach(span => {
    span.classList.toggle("gutter-line--graph",
      parseInt(span.dataset.line) === lineNum);
  });
}

function clearGraphHighlight() {
  const gutter = document.getElementById("editor-gutter");
  if (!gutter) return;
  gutter.querySelectorAll("span").forEach(s =>
    s.classList.remove("gutter-line--graph"));
}

// ── Run button pulse ───────────────────────────────────────────────────────

function pulseRunBtn() {
  if (reduced) return;
  const btn = document.getElementById("btn-check");
  if (!btn) return;
  btn.classList.remove("btn--pulsing");
  void btn.offsetWidth; /* force reflow to restart animation */
  btn.classList.add("btn--pulsing");
  setTimeout(() => btn.classList.remove("btn--pulsing"), 600);
}

// ── Verdict card rendering ────────────────────────────────────────────────

function renderVerdictCard(state, data) {
  /* state: "valid" | "invalid" | "error" | "checking" */
  const card     = document.getElementById("studio-verdict-card");
  const badge    = document.getElementById("verdict-badge");
  const icon     = document.getElementById("verdict-icon");
  const text     = document.getElementById("verdict-text");
  const logicEl  = document.getElementById("verdict-logic");
  const stepsRow = document.getElementById("verdict-steps-row");
  const stepsEl  = document.getElementById("verdict-steps");
  const nameRow  = document.getElementById("verdict-name-row");
  const nameEl   = document.getElementById("verdict-name");
  const diagsEl  = document.getElementById("verdict-diags");
  if (!card) return;

  card.dataset.state = state;
  badge.dataset.state = state;

  if (state === "checking") {
    icon.textContent = "·";
    text.textContent = "Checking…";
    if (logicEl) logicEl.textContent = data.logic || "—";
    if (stepsRow) stepsRow.hidden = true;
    if (nameRow)  nameRow.hidden  = true;
    if (diagsEl)  diagsEl.textContent = "—";
    return;
  }

  if (state === "valid") {
    icon.textContent = "✓";
    text.textContent = "Valid";
    if (logicEl) logicEl.textContent = data.logic || "—";
    if (stepsRow) { stepsRow.hidden = false; stepsEl.textContent = String(data.steps || "—"); }
    if (nameRow)  { nameRow.hidden  = false; nameEl.textContent  = data.name  || "—"; }
    if (diagsEl)  diagsEl.textContent = data.diags || "none";
    return;
  }

  if (state === "invalid") {
    icon.textContent = "✗";
    text.textContent = "Invalid";
    if (logicEl) logicEl.textContent = data.logic || "—";
    if (stepsRow) stepsRow.hidden = true;
    if (nameRow)  nameRow.hidden  = true;
    if (diagsEl)  diagsEl.textContent = data.error_summary || "—";
    return;
  }

  /* error / parse */
  icon.textContent = "✗";
  text.textContent = "Error";
  if (logicEl) logicEl.textContent = "—";
  if (stepsRow) stepsRow.hidden = true;
  if (nameRow)  nameRow.hidden  = true;
  if (diagsEl)  diagsEl.textContent = data.error_summary || "—";
}

// ── Panel: Verify ──────────────────────────────────────────────────────────

async function runCheck() {
  const source = document.getElementById("proof-input").value.trim();
  const logic  = document.getElementById("logic-select").value;
  if (!source) {
    showResultPane();
    showResult("check-result", "Enter a proof on the left.", "info");
    renderVerdictCard("error", { error_summary: "No proof text." });
    return;
  }

  pulseRunBtn();
  clearErrorLine();
  showResultPane();
  activateResultTab("result");

  renderVerdictCard("checking", { logic });
  showResult("check-result", "Checking…", "info");

  try {
    const r = await callBrowser("browser_check", { proof_text: source, logic });
    if (r.ok) {
      const stepsCount = (source.match(/\b(have|conclude)\b/g) || []).length;
      renderVerdictCard("valid", {
        logic: r.logic || logic,
        steps: stepsCount,
        name:  r.name,
        diags: "none",
      });
      showResult("check-result",
        `<div class="check-result-valid">
           <span class="check-result-icon" aria-hidden="true">✓</span>
           <div class="check-result-body">
             <strong>Valid</strong> — theorem <code>${esc(r.name)}</code>
             checked by kernel.py<br>
             <span class="check-result-meta">Logic: ${esc(r.logic || logic)}</span>
           </div>
         </div>`, "ok");
    } else {
      const line = r.line ? ` at line ${r.line}` : "";
      const kind = r.kind || "error";
      renderVerdictCard("invalid", {
        logic: logic,
        error_summary: `${kind}${line}: ${r.error}`,
      });
      /* Highlight error line in gutter */
      if (r.line) {
        highlightErrorLine(r.line);
        showErrorBar(kind + line, r.error || "");
      }
      /* Build rich error card */
      let errHTML = `<div class="check-result-error">
        <span class="check-result-icon" aria-hidden="true">✗</span>
        <div class="check-result-body">
          <strong>${esc(kind)}</strong>${line ? `<span class="check-result-line">${esc(line)}</span>` : ""}
          <br><span class="check-result-errmsg">${esc(r.error || "")}</span>`;
      if (r.expected)  errHTML += `<br><span class="check-result-detail">Expected: <code>${esc(r.expected)}</code></span>`;
      if (r.received)  errHTML += `<span class="check-result-detail"> · Got: <code>${esc(r.received)}</code></span>`;
      if (r.rule)      errHTML += `<br><span class="check-result-detail">Rule: <code>${esc(r.rule)}</code></span>`;
      errHTML += `</div></div>`;
      showResult("check-result", errHTML, "err");
    }
  } catch (e) {
    renderVerdictCard("error", { error_summary: e.message });
    showResult("check-result", "Internal error: " + esc(e.message), "err");
  }
}

// ── Panel: Diagnostics ──────────────────────────────────────────────────────

async function runDiagnose() {
  const source = document.getElementById("proof-input").value.trim();
  const logic  = document.getElementById("logic-select").value;
  const out    = document.getElementById("diag-result");
  if (!source) { out.innerHTML = `<p class="dim-text">Enter a proof on the left first.</p>`; return; }

  out.innerHTML = `<p class="dim-text">Running diagnostics…</p>`;
  try {
    const r = await callBrowser("browser_diagnose", { proof_text: source, logic });
    if (!r.ok) { out.innerHTML = `<p class="result-err-text">${esc(r.error)}</p>`; return; }
    const diags = r.diagnostics || [];
    if (!diags.length) {
      out.innerHTML = `<div class="diag-clean">
        <span class="diag-clean-icon" aria-hidden="true">✓</span>
        <span>No diagnostics — proof structure looks clean.</span>
      </div>`;
      return;
    }
    out.innerHTML = `<ul class="diag-list">${diags.map(d => {
      const sev = d.severity || "info";
      const sevIcon = sev === "error" ? "✗" : sev === "warning" ? "⚠" : "ℹ";
      return `<li class="diag-item ${esc(sev)}">
        <div class="diag-header">
          <span class="diag-sev-icon" aria-hidden="true">${sevIcon}</span>
          <span class="diag-code">${esc(d.code || sev)}</span>
          ${d.line ? `<span class="diag-line-tag">line ${d.line}</span>` : ""}
        </div>
        <div class="diag-msg">${esc(d.message)}</div>
      </li>`;
    }).join("")}</ul>`;
  } catch (e) {
    out.innerHTML = `<p class="result-err-text">Error: ${esc(e.message)}</p>`;
  }
}

// ── Panel: Graph ───────────────────────────────────────────────────────────

async function runGraph() {
  const source = document.getElementById("proof-input").value.trim();
  const logic  = document.getElementById("logic-select").value;
  const dotOut  = document.getElementById("graph-dot");
  const svgWrap = document.getElementById("studio-graph-svg-wrap");
  const dotDets = document.getElementById("graph-dot-details");
  const nodesEl = document.getElementById("graph-nodes");
  if (!source) {
    if (dotOut) dotOut.textContent = "Enter a proof on the left first.";
    if (dotDets) { dotDets.hidden = false; dotDets.open = true; }
    return;
  }
  if (svgWrap)  svgWrap.innerHTML = `<p class="dim-text">Building graph…</p>`;
  if (dotOut)   dotOut.textContent = "";
  if (nodesEl)  nodesEl.innerHTML  = "";

  try {
    const r = await callBrowser("browser_graph", { proof_text: source, logic });
    if (!r.ok) {
      if (svgWrap) svgWrap.innerHTML = `<p class="result-err-text">Error: ${esc(r.error)}</p>`;
      if (svgWrap) svgWrap.hidden = false;
      return;
    }
    /* DOT output */
    if (dotOut)  dotOut.textContent = r.dot || "(no DOT output)";
    if (dotDets) dotDets.hidden = false;

    /* In-page SVG graph */
    if (svgWrap) {
      svgWrap.hidden = false;
      svgWrap.innerHTML = buildSVGGraph(r.nodes || [], r.edges || []);
      /* Wire hover → gutter highlight */
      svgWrap.querySelectorAll("[data-line]").forEach(el => {
        el.addEventListener("mouseenter", () => {
          const ln = parseInt(el.dataset.line);
          if (ln) highlightGraphLine(ln);
        });
        el.addEventListener("mouseleave", clearGraphHighlight);
        el.addEventListener("focus", () => {
          const ln = parseInt(el.dataset.line);
          if (ln) highlightGraphLine(ln);
        });
        el.addEventListener("blur", clearGraphHighlight);
      });
    }

    /* Node summary list (for test coverage — graph-nodes id) */
    if (nodesEl) {
      nodesEl.hidden = true; /* hidden; SVG handles visual; nodes div kept for test */
      nodesEl.innerHTML = (r.nodes || []).map(n =>
        `<div class="graph-node">
          <div class="lbl">${esc(n.label)}</div>
          <div class="knd">${esc(n.kind)}${n.rule ? " · " + esc(n.rule) : ""}</div>
          <div class="frm">${esc(n.formula || "")}</div>
        </div>`).join("");
    }
  } catch (e) {
    if (svgWrap) { svgWrap.innerHTML = `<p class="result-err-text">Error: ${esc(e.message)}</p>`; svgWrap.hidden = false; }
  }
}

// ── In-page SVG dependency graph renderer ─────────────────────────────────

function buildSVGGraph(nodes, edges) {
  if (!nodes.length) return `<p class="dim-text">No nodes in graph.</p>`;

  /* Assign depth by BFS from root (theorem / node with no incoming edge) */
  const labels = new Set(nodes.map(n => n.label));
  const incoming = new Map();
  nodes.forEach(n => incoming.set(n.label, 0));
  edges.forEach(e => { incoming.set(e.tgt, (incoming.get(e.tgt) || 0) + 1); });

  const roots = nodes.filter(n => (incoming.get(n.label) || 0) === 0).map(n => n.label);
  if (!roots.length) roots.push(nodes[0].label); /* cycle fallback */

  const depth  = new Map();
  const queue  = [];
  roots.forEach(r => { depth.set(r, 0); queue.push(r); });
  const adj = new Map();
  edges.forEach(e => {
    if (!adj.has(e.src)) adj.set(e.src, []);
    adj.get(e.src).push(e.tgt);
  });
  let head = 0;
  while (head < queue.length) {
    const cur = queue[head++];
    (adj.get(cur) || []).forEach(tgt => {
      if (!depth.has(tgt)) { depth.set(tgt, (depth.get(cur) || 0) + 1); queue.push(tgt); }
    });
  }
  nodes.forEach(n => { if (!depth.has(n.label)) depth.set(n.label, 0); });

  /* Group by depth */
  const cols = new Map();
  nodes.forEach(n => {
    const d = depth.get(n.label) || 0;
    if (!cols.has(d)) cols.set(d, []);
    cols.get(d).push(n);
  });
  const maxDepth = Math.max(...cols.keys());

  /* Layout constants */
  const NODE_W  = 120;
  const NODE_H  = 44;
  const COL_GAP = 160;
  const ROW_GAP = 60;
  const PAD_X   = 30;
  const PAD_Y   = 30;

  const maxNodesInCol = Math.max(...[...cols.values()].map(c => c.length));
  const svgW = PAD_X * 2 + (maxDepth + 1) * COL_GAP;
  const svgH = PAD_Y * 2 + maxNodesInCol * (NODE_H + ROW_GAP);

  /* Compute positions */
  const pos = new Map();
  cols.forEach((colNodes, d) => {
    const totalColH = colNodes.length * (NODE_H + ROW_GAP) - ROW_GAP;
    const startY    = PAD_Y + (svgH - PAD_Y * 2 - totalColH) / 2;
    colNodes.forEach((n, i) => {
      pos.set(n.label, {
        x: PAD_X + d * COL_GAP,
        y: startY + i * (NODE_H + ROW_GAP),
      });
    });
  });

  /* Detect which nodes have errors (incoming edges that fail) */
  /* We detect unused assumptions by nodes w/ 0 outgoing in edges to non-root */
  const outDeg = new Map();
  nodes.forEach(n => outDeg.set(n.label, 0));
  edges.forEach(e => outDeg.set(e.src, (outDeg.get(e.src) || 0) + 1));

  function nodeColor(n) {
    if (n.kind === "theorem")  return { stroke: "#7C5CFF", fill: "rgba(124,92,255,.12)" };
    if (n.kind === "conclude") return { stroke: "#3E9C8F", fill: "rgba(62,156,143,.10)" };
    if (n.kind === "suppose")  return { stroke: "#D4A050", fill: "rgba(212,160,80,.08)" };
    if (n.kind === "assume" && (outDeg.get(n.label) || 0) === 0)
      return { stroke: "#D4A050", fill: "rgba(212,160,80,.08)" }; /* unused assumption */
    return { stroke: "#5A5070", fill: "rgba(90,80,112,.10)" };
  }

  function nodeTextColor(n) {
    if (n.kind === "theorem")  return "#9D7BFF";
    if (n.kind === "conclude") return "#3E9C8F";
    if (n.kind === "suppose")  return "#D4A050";
    if (n.kind === "assume" && (outDeg.get(n.label) || 0) === 0) return "#D4A050";
    return "#C9C4D6";
  }

  /* Edge paths (curved) */
  function edgePath(src, tgt) {
    const s = pos.get(src), t = pos.get(tgt);
    if (!s || !t) return "";
    const sx = s.x + NODE_W, sy = s.y + NODE_H / 2;
    const tx = t.x,           ty = t.y + NODE_H / 2;
    const mx = (sx + tx) / 2;
    return `M ${sx},${sy} C ${mx},${sy} ${mx},${ty} ${tx},${ty}`;
  }

  /* Assign line numbers: assume ordering by proof line (approx by label sort in col) */
  function approxLine(n, allNodes) {
    const idx = allNodes.findIndex(x => x.label === n.label);
    return idx + 1; /* 1-based approximate */
  }

  /* SVG */
  let svg = `<svg viewBox="0 0 ${svgW} ${svgH}" xmlns="http://www.w3.org/2000/svg"
    role="img" aria-label="Proof dependency graph"
    class="studio-graph-svg"
    style="width:100%;max-width:${svgW}px;height:${svgH}px">
  <defs>
    <marker id="sgraph-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
      <path d="M0,1 L6,3.5 L0,6 Z" fill="rgba(90,80,112,0.7)"/>
    </marker>
    <marker id="sgraph-arrow-ok" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
      <path d="M0,1 L6,3.5 L0,6 Z" fill="rgba(62,156,143,0.7)"/>
    </marker>
  </defs>`;

  /* Edges */
  edges.forEach(e => {
    const path = edgePath(e.src, e.tgt);
    if (!path) return;
    const isFinal = nodes.find(n => n.label === e.tgt && n.kind === "conclude");
    const color   = isFinal ? "rgba(62,156,143,0.45)" : "rgba(90,80,112,0.45)";
    const marker  = isFinal ? "url(#sgraph-arrow-ok)" : "url(#sgraph-arrow)";
    svg += `<path d="${esc(path)}" fill="none" stroke="${color}" stroke-width="1.5"
      marker-end="${marker}"/>`;
  });

  /* Nodes */
  nodes.forEach(n => {
    const p   = pos.get(n.label);
    if (!p) return;
    const col = nodeColor(n);
    const tc  = nodeTextColor(n);
    const ln  = approxLine(n, nodes);

    /* Truncate formula for display */
    const formula = n.formula ? (n.formula.length > 16 ? n.formula.slice(0, 14) + "…" : n.formula) : "";
    const tabIdx  = n.kind === "theorem" ? "0" : "-1";

    svg += `<g class="sgraph-node" data-line="${ln}" data-label="${esc(n.label)}"
      tabindex="${tabIdx}" role="button" aria-label="${esc(n.label)}: ${esc(n.kind)} ${esc(n.formula || "")}">
      <rect x="${p.x}" y="${p.y}" width="${NODE_W}" height="${NODE_H}" rx="4"
        fill="${col.fill}" stroke="${col.stroke}" stroke-width="1.5"/>
      <text x="${p.x + NODE_W / 2}" y="${p.y + 15}" text-anchor="middle"
        font-family="monospace" font-size="10" fill="${tc}" font-weight="600">${esc(n.label)}</text>
      <text x="${p.x + NODE_W / 2}" y="${p.y + 27}" text-anchor="middle"
        font-family="monospace" font-size="8" fill="rgba(${col.stroke.startsWith('#') ? hexToRgbStr(col.stroke) : "90,80,112"},0.7)">${esc(n.kind)}</text>
      ${formula ? `<text x="${p.x + NODE_W / 2}" y="${p.y + 38}" text-anchor="middle"
        font-family="monospace" font-size="8" fill="rgba(201,196,214,0.6)">${esc(formula)}</text>` : ""}
    </g>`;
  });

  svg += `</svg>`;

  /* Legend */
  svg += `<div class="sgraph-legend" aria-label="Graph legend">
    <span class="sgraph-legend-item"><span class="sgraph-swatch" style="border-color:#7C5CFF"></span>theorem</span>
    <span class="sgraph-legend-item"><span class="sgraph-swatch" style="border-color:#3E9C8F"></span>conclude</span>
    <span class="sgraph-legend-item"><span class="sgraph-swatch" style="border-color:#D4A050"></span>suppose / unused</span>
    <span class="sgraph-legend-item"><span class="sgraph-swatch" style="border-color:#5A5070"></span>have / assume</span>
  </div>`;

  return svg;
}

function hexToRgbStr(hex) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r},${g},${b}`;
}

// ── Panel: Semantics — Soundness ───────────────────────────────────────────

async function runSoundness() {
  const logic  = document.getElementById("sem-logic-select").value;
  const matrix = document.getElementById("sem-matrix-select").value;
  const out    = document.getElementById("soundness-result");
  out.innerHTML = `<p class="dim-text">Checking…</p>`;
  try {
    const r = await callBrowser("browser_soundness", { logic, matrix });
    if (!r.ok) { out.innerHTML = `<p class="result-err-text">${esc(r.error)}</p>`; return; }
    const rows = (r.rules || []).map(rule => {
      const cls = rule.status === "sound" ? "sound" : rule.status === "unsound" ? "unsound" : "skipped";
      const statusIcon = rule.status === "sound" ? "✓" : rule.status === "unsound" ? "✗" : "—";
      const cx  = rule.counterexample
        ? `<br><small style='color:var(--muted)'>counterexample: ${esc(JSON.stringify(rule.counterexample))}</small>`
        : "";
      return `<tr>
        <td>${esc(rule.rule)}</td>
        <td class="${cls}">
          <span aria-hidden="true">${statusIcon}</span> ${esc(rule.status)}${cx}
        </td>
      </tr>`;
    }).join("");
    out.innerHTML = `
      <p class="sem-meta">
        Logic <strong>${esc(r.logic)}</strong>
        · matrix <strong>${esc(r.matrix)}</strong>
      </p>
      <table class="soundness-table">
        <thead><tr><th>Rule</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    out.innerHTML = `<p class="result-err-text">Error: ${esc(e.message)}</p>`;
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
    if (!r.ok) { out.innerHTML = `<p class="result-err-text">${esc(r.error)}</p>`; return; }
    const rows = (r.rows || []).map(row =>
      `<tr>
        <td>${esc(row.label)}</td>
        <td class="lat-axioms">${row.axioms.length ? row.axioms.map(esc).join(", ") : "∅"}</td>
        <td class="status-${esc(row.status)}">${esc(row.status)}</td>
      </tr>`).join("");
    out.innerHTML = `
      <p class="sem-meta">Formula: <strong>${esc(r.formula)}</strong></p>
      <table class="lattice-table">
        <thead><tr><th>World</th><th>Axioms</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    out.innerHTML = `<p class="result-err-text">Error: ${esc(e.message)}</p>`;
  }
}

// ── Panel: Semantics — Kripke Countermodel ────────────────────────────────

async function runKripke() {
  const formula   = document.getElementById("kripke-input").value.trim();
  const maxWorlds = parseInt(document.getElementById("kripke-worlds-select").value) || 3;
  const out       = document.getElementById("kripke-result");
  if (!formula) { out.innerHTML = `<p class="dim-text">Enter a formula above.</p>`; return; }
  out.innerHTML = `<p class="dim-text">Searching for countermodel…</p>`;
  try {
    const r = await callBrowser("browser_kripke", { formula, max_worlds: maxWorlds });
    if (r.status === "parse_error" || r.status === "unsupported_formula") {
      out.innerHTML = `<p class="result-err-text">${esc(r.explanation)}</p>`; return;
    }
    if (r.status === "no_countermodel_within_bound") {
      out.innerHTML = `
        <div class="kripke-no-cm">
          <span aria-hidden="true">✓</span>
          No countermodel found (max ${esc(String(r.max_worlds))} worlds).
        </div>
        <p class="kripke-bound-note">${esc(r.bound_note)}</p>`;
      return;
    }
    /* status === "countermodel_found" */
    const val = r.valuation || {};
    const worldRows = (r.worlds || []).map(w => {
      const atoms = val[String(w)] || [];
      const fail  = w === r.failing_world
        ? `<span class="kripke-fail-badge" aria-label="fails here">✗ fails</span>` : "";
      return `<tr>
        <td>${esc(String(w))}</td>
        <td>${atoms.length ? atoms.map(esc).join(", ") : "∅"}</td>
        <td>${fail}</td>
      </tr>`;
    }).join("");
    const orderStr = (r.order_pairs || []).length
      ? r.order_pairs.map(p => `${esc(String(p[0]))}≤${esc(String(p[1]))}`).join(", ")
      : "discrete (reflexive only)";
    out.innerHTML = `
      <div class="kripke-found-header">
        <span aria-hidden="true">✗</span>
        Countermodel found — formula fails in this model.
      </div>
      <p class="sem-meta">Formula: <strong>${esc(r.formula)}</strong> · Order: ${orderStr}</p>
      <table class="lattice-table">
        <thead><tr><th>World</th><th>True atoms</th><th></th></tr></thead>
        <tbody>${worldRows}</tbody>
      </table>
      <p class="kripke-bound-note">${esc(r.explanation)}</p>`;
  } catch (e) {
    out.innerHTML = `<p class="result-err-text">Error: ${esc(e.message)}</p>`;
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
    grid.innerHTML = `<p class="result-err-text">Failed to load examples: ${esc(e.message)}</p>`;
  }
}

function loadExampleCard(card) {
  const content = card.dataset.content;
  const fn      = card.dataset.filename;
  setEditorContent(content, null);
  document.getElementById("proof-input").focus();
  showStatus("info", `Loaded: ${fn}`);
  /* Scroll to editor on mobile */
  const editorPane = document.getElementById("studio-editor-pane");
  if (editorPane) editorPane.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── URL parameter support ──────────────────────────────────────────────────

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
      _urlParamLoaded = true;
      return true;
    }
  }
  if (proofTx) {
    setEditorContent(proofTx, logic);
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
  if (!grid) return;

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

// ── Editor content setter ──────────────────────────────────────────────────

function setEditorContent(proof, logic) {
  const editor   = document.getElementById("proof-input");
  const logicSel = document.getElementById("logic-select");
  if (editor)   editor.value = proof;
  if (logicSel && logic) logicSel.value = logic;
  /* Clear prior results */
  clearErrorLine();
  const resultBox = document.getElementById("check-result");
  if (resultBox) resultBox.className = "result-box studio-check-result";
  const diagResult = document.getElementById("diag-result");
  if (diagResult) diagResult.innerHTML = "";
  /* Reset verdict card */
  const empty = document.getElementById("studio-empty-state");
  const card  = document.getElementById("studio-verdict-card");
  const tabs  = document.getElementById("result-tabs");
  if (empty) empty.hidden = false;
  if (card)  card.hidden  = true;
  if (tabs)  tabs.hidden  = true;
  /* Sync gutter */
  syncGutter();
}

// ── loadPreset (global — called from landing/tutorial) ────────────────────

function loadPreset(proof, logic) {
  if (!document.getElementById("proof-input")) {
    navigateToStudio(proof, logic || "intuitionistic_prop", "verify");
    return;
  }
  setEditorContent(proof, logic);
  document.getElementById("proof-input").scrollIntoView({ behavior: "smooth", block: "nearest" });
  if (steleReady) {
    setTimeout(runCheck, 600);
  } else {
    showStatus("info", "Proof loaded — click Run Check once Stele finishes loading.");
  }
}

function loadTutorialPreset(proof, logic, tab) {
  if (proof) setEditorContent(proof, logic);
  if (steleReady && proof) {
    const delay = 700;
    if (!tab || tab === "verify")   setTimeout(runCheck,   delay);
    else if (tab === "diagnose")    setTimeout(runDiagnose, delay);
    else if (tab === "graph")       setTimeout(runGraph,    delay);
  } else if (proof) {
    showStatus("info", "Proof loaded — click the run button once Stele finishes loading.");
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
    next.disabled  = n >= TOTAL_TUTORIAL_STEPS;
    next.textContent = n >= TOTAL_TUTORIAL_STEPS ? "Done ✓" : "Next →";
  }
}

// ── Semantic preset wiring ────────────────────────────────────────────────

function wirePresets() {
  /* LEM fails in K3: switch to Semantics → Soundness, set classical_prop + K3 */
  const lemK3 = document.getElementById("preset-lem-k3");
  if (lemK3) {
    lemK3.addEventListener("click", () => {
      const semLogic  = document.getElementById("sem-logic-select");
      const semMatrix = document.getElementById("sem-matrix-select");
      if (semLogic)  semLogic.value  = "classical_prop";
      if (semMatrix) semMatrix.value = "K3";
      const sem = document.getElementById("panel-semantics");
      if (sem) sem.scrollIntoView({ behavior: "smooth", block: "start" });
      if (steleReady) setTimeout(runSoundness, 400);
      else showStatus("info", "LEM in K3: go to Semantic Tools → Rule Soundness (classical_prop + K3) and click Check Soundness.");
    });
  }

  /* DNE classical-only: load dne proof, set logic to intuitionistic, run check */
  const dne = document.getElementById("preset-dne");
  if (dne) {
    dne.addEventListener("click", () => {
      const entry = GALLERY_ENTRIES.find(e => e.id === "dne");
      if (!entry) return;
      setEditorContent(entry.proof, "intuitionistic_prop");
      const logicSel = document.getElementById("logic-select");
      if (logicSel) logicSel.value = "intuitionistic_prop";
      showStatus("info", "DNE proof loaded with intuitionistic_prop — expected: rejected.");
      if (steleReady) setTimeout(runCheck, 600);
    });
  }

  /* ¬¬P→P countermodel: set Kripke input + scroll to it */
  const kripkePr = document.getElementById("preset-kripke");
  if (kripkePr) {
    kripkePr.addEventListener("click", () => {
      const ki = document.getElementById("kripke-input");
      if (ki) ki.value = "not not P -> P";
      const sem = document.getElementById("panel-semantics");
      if (sem) sem.scrollIntoView({ behavior: "smooth", block: "start" });
      if (steleReady) setTimeout(runKripke, 400);
      else showStatus("info", "Go to Semantic Tools → Kripke Countermodel and click Find Countermodel for ¬¬P→P.");
    });
  }

  /* Peirce's law: load proof, set classical */
  const peirce = document.getElementById("preset-peirce");
  if (peirce) {
    peirce.addEventListener("click", () => {
      const entry = GALLERY_ENTRIES.find(e => e.id === "peirce");
      if (!entry) return;
      setEditorContent(entry.proof, "classical_prop");
      showStatus("info", "Peirce's law loaded — classical_prop.");
      if (steleReady) setTimeout(runCheck, 600);
    });
  }
}

// ── Init ───────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  const onStudioPage = !!document.getElementById("proof-input");

  if (onStudioPage) {
    /* Gutter: sync on input */
    const editor = document.getElementById("proof-input");
    if (editor) {
      syncGutter();
      editor.addEventListener("input", syncGutter);
      editor.addEventListener("keydown", e => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
          e.preventDefault(); runCheck();
        }
        /* Sync gutter on Tab key (indent) */
        if (e.key === "Tab") {
          e.preventDefault();
          const start = editor.selectionStart;
          const end   = editor.selectionEnd;
          editor.value = editor.value.slice(0, start) + "  " + editor.value.slice(end);
          editor.selectionStart = editor.selectionEnd = start + 2;
          syncGutter();
        }
      });
      editor.addEventListener("scroll", () => {
        const gutter = document.getElementById("editor-gutter");
        if (gutter) gutter.scrollTop = editor.scrollTop;
      });
    }

    /* Result sub-tabs */
    document.querySelectorAll(".result-tab").forEach(btn => {
      btn.addEventListener("click", () => activateResultTab(btn.dataset.resultTab));
    });

    /* Action buttons */
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

    /* Preset buttons */
    wirePresets();

    /* URL params */
    loadFromURLParams();

    /* Disable action buttons until Pyodide ready */
    setButtonsEnabled(false);
    initStele();

    /* Mobile: if viewport narrow, scroll result pane into view after run */
    document.getElementById("btn-check")?.addEventListener("click", () => {
      if (window.innerWidth < 900) {
        setTimeout(() => {
          const res = document.getElementById("studio-result-pane");
          if (res) res.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 200);
      }
    });
  }

  /* Both pages */
  renderGallery();
  showTutorialStep(1);

  document.querySelectorAll(".tut-dot").forEach(dot => {
    dot.addEventListener("click", () => showTutorialStep(parseInt(dot.dataset.step, 10)));
  });

  const prevBtn = document.getElementById("tut-prev");
  const nextBtn = document.getElementById("tut-next");
  if (prevBtn) prevBtn.addEventListener("click", () => showTutorialStep(currentTutorialStep - 1));
  if (nextBtn) nextBtn.addEventListener("click", () => showTutorialStep(currentTutorialStep + 1));

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

window.stele = { loadPreset, loadTutorialPreset, runCheck, activateTab, navigateToStudio };
