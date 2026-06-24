# 02 — Architecture and Trust Boundary

**Status:** Stable (architecture description)
**Evidence:** `stele/kernel.py`, `tests/test_regression_invariants.py`
**Doc:** `docs/development-context.md` §2, `site/architecture.html`

---

## 2.1 Layered architecture

Stele has a strict three-zone layered architecture:

```
Zone 1 — TRUSTED KERNEL
  stele/kernel.py      proof-step verifier (syntactic matching only)
  stele/logic.py       RuleSchema data objects (5 built-in logics)
  stele/parser.py      recursive-descent parser (hand-written, no deps)
  stele/ast.py         formula AST (Var, Op) — frozen dataclasses
  stele/proof.py       proof node types (Assume/Have/Suppose/Conclude/Theorem)

Zone 2 — EXPERIMENTAL / UNTRUSTED
  stele/core/          proof-term calculus (Curry–Howard)
  stele/elaborate.py   script → proof-term elaboration
  stele/diagnostics.py structural diagnostics (UNTRUSTED)
  stele/proofstate.py  proof-state hints (UNTRUSTED, trusted=False always)
  stele/kripke.py      Kripke countermodel search (Experimental)
  stele/matrix.py      many-valued matrix semantics (Demo)
  stele/world.py       world/lattice demo
  stele/certificate.py proof certificate emission
  stele/minicheck.py   independent certificate re-checker
  stele/proofgraph.py  proof dependency graph

Zone 3 — OPTIONAL / ISOLATED
  stele_ml/            ML baseline (Optional, isolated, no kernel import)
  stele_lean/          Lean 4 error bridge (Optional, isolated)
  stele/browser.py     Pyodide bridge (UI, untrusted)
  site/                public website (vanilla HTML/CSS/JS)
  stele/web.py         HTTP dev server
```

**Key invariant:** `kernel.py` never imports `matrix.py` and `matrix.py` never imports
`kernel.py`. This is enforced by `tests/test_regression_invariants.py`.

---

## 2.2 The trusted kernel

The trusted kernel consists of:

1. **`stele/kernel.py`** — the sole trusted verifier. Implements:
   - `match(rule_schema, step)` — purely syntactic; no semantic reasoning
   - `instantiate(pattern, bindings)` — template substitution
   - `check_proof(theorem, logic)` — tree walk over proof nodes
   - `discharge(label, scope)` — assumption discharge for `imp_intro`, `neg_intro`, `or_elim`, `pbc`

2. **`stele/logic.py`** — rule schema data. No code logic; only frozen dataclasses.
   ```python
   @dataclass(frozen=True)
   class RuleSchema:
       name: str
       premises: tuple[Formula, ...]
       conclusion: Formula
       discharge_labels: tuple[int, ...]  # indices of discharged premises
   ```

3. **`stele/parser.py`** — hand-written recursive-descent parser. No external parser
   libraries (no lark, no antlr, no ply).

**De Bruijn criterion (audit standard):** The kernel is small enough to audit manually.
The current implementation is ~400 lines; de Bruijn proposed that a trustworthy kernel
should be small enough for a single reader to verify. This is a design goal, not a
formally checked claim.

---

## 2.3 Trust boundary diagram (ASCII)

```
                    ┌─────────────────────────────────┐
                    │         User Proof Script         │
                    │  (Stele-Light .stele file / UI)   │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │           TRUSTED ZONE           │
                    │  parser.py → ast.py → kernel.py  │
                    │       logic.py (rule data)        │
                    │  Result: PASS / FAIL + position   │
                    └────────────────┬────────────────┘
                          ┌──────────┴──────────┐
           ┌──────────────▼──────────┐   ┌──────▼─────────────────┐
           │   CERTIFICATE PATH       │   │  DIAGNOSTICS (UNTRUSTED)│
           │  certificate.py          │   │  diagnostics.py         │
           │  minicheck.py            │   │  proofstate.py (hints)  │
           │  (code-level isolation)  │   │  kripke.py (Experimental)│
           └──────────────────────────┘   └────────────────────────┘
```

**Figure placeholder:** Replace ASCII with SVG in paper.
Source module for SVG: `site/architecture.html` contains an SVG trust-boundary diagram.

---

## 2.4 Dependency policy

| Module class | Allowed imports | Status |
|-------------|-----------------|--------|
| Trusted kernel (`kernel.py`, `logic.py`, `parser.py`) | stdlib only | Enforced |
| Proof-term core (`stele/core/`) | stdlib + `stele.ast` | Enforced |
| Diagnostics (`diagnostics.py`) | `stele.ast`, `stele.proof`, `stele.errors` (no kernel) | By convention |
| Matrix layer (`matrix.py`) | stdlib only, no kernel import | Enforced by test |
| ML layer (`stele_ml/`) | stdlib only; may import `stele.ast` for formula parsing | Enforced |
| Lean bridge (`stele_lean/`) | stdlib only; no kernel, no matrix | Enforced |

**Test:** `tests/test_regression_invariants.py` asserts:
- `stele.kernel` does not import `stele.matrix`
- `stele.matrix` does not import `stele.kernel`
- ML layer isolation (no kernel import chain from `stele_ml/`)

---

## 2.5 Proof certificate and minicheck path

```
kernel.check_proof() → OK
        ↓
certificate.emit_certificate(proof, logic) → JSON cert
        ↓
minicheck.minicheck(cert_json) → OK / FAIL
  (imports: stele.ast, stele.certificate — does NOT import stele.kernel or stele.parser)
```

**Limitation:** Same Python process. Not process-level or language-level isolation.
Not formally verified. The minicheck is an independent **software** check, not an
independent **verification system**.

---

## 2.6 Pyodide / browser-local path

All of Zone 1 (trusted kernel) and Zone 2 (experimental) run unchanged in Pyodide
(Python compiled to WebAssembly). The browser bridge is:

```
browser.py:
  browser_check(source_text, logic_name) → JSON result
  browser_diagnose(source_text) → JSON diagnostics
  browser_graph(source_text) → DOT string
  browser_kripke(formula_str, max_worlds=3) → JSON countermodel or null
  browser_state(source_text) → JSON proof state
  browser_hints(source_text) → JSON hints
```

No backend server is required. The Pyodide bundle (~8 MB download) runs the full kernel
in the browser. This is architecturally significant: the same trusted code that runs in
CI runs in the browser, with no server intermediary.

**Status:** Stable
**Module:** `stele/browser.py`, `site/studio.html`
**Test:** `tests/test_pyodide_site.py`
**Caveat:** ~8 MB first-load; CDN dependency for the Pyodide runtime.

---

## 2.7 Deployment surface

| Mode | Description | Status |
|------|-------------|--------|
| Python CLI | `python -m stele.cli` | Stable |
| Browser (Pyodide) | `site/studio.html`; no backend | Stable |
| HTTP dev server | `python -m stele.web` (port 8765) | Stable |
| Single-file HTML | `dist/stele.html` (generated; not committed) | Experimental |
| Standalone executable | `packaging/build_app.py` (PyInstaller; not committed) | Experimental |
