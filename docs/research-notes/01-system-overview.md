# 01 — System Overview

**Status:** Stable
**Evidence:** `stele/kernel.py`, `stele/logic.py`, `CLAUDE.md`, `docs/development-context.md`

---

## 1.1 Identity

Stele is a **formal verification framework for mathematical reasoning**.

The one-sentence description:

> Stele represents proofs as structured objects of assumptions, inference rules, and proof
> states, and uses a rule-based verification module to check each step — detecting
> missing hypotheses, invalid transitions, circular dependencies, undefined symbols, and
> unsupported conclusions.

**Module:** `stele/kernel.py`, `stele/logic.py`
**Doc:** `CLAUDE.md` §프로젝트 정체성, `docs/development-context.md` §1
**Test:** `tests/test_kernel_valid.py`, `tests/test_kernel_invalid.py`

---

## 1.2 What problem does Stele address?

Most formal verification systems are designed for professional mathematicians or
experienced type theorists. They require dependent types, tactic languages, large
libraries, and significant installation overhead. The tradeoff is power vs. accessibility.

Stele targets a different point:

- **Small, auditable:** the trusted kernel is a single Python file (~400 lines).
- **Zero runtime dependencies:** Python 3.10+ standard library only; runs in a browser
  via Pyodide/WASM without installation.
- **Readable proof format:** the Stele-Light proof language resembles typed
  natural-deduction derivations; no tactic syntax required.
- **Multi-logic:** rule sets are pure data (`RuleSchema` frozen dataclasses); switching
  logics is a runtime flag, not a code change.
- **Honest diagnostics:** structural errors (missing hypothesis, invalid transition) are
  detected and located, not just reported as a pass/fail binary.

**Primary use cases:**
- Formal reasoning education: students write proofs and see which step failed and why.
- Proof-checking experiments: verify that a manually written derivation is valid under a
  chosen logic.
- Browser-local exploration: the full checker runs in-browser with no backend.

---

## 1.3 What Stele is not

| Claim | Correct statement |
|-------|------------------|
| Theorem prover | Stele is a **proof checker**. It verifies proofs written by the user; it does not search for proofs. |
| SMT/SAT solver | No constraint solving, no quantifier elimination, no decision procedures. |
| AI verifier | The ML baseline (`stele_ml/`) is Optional, isolated, untrusted, and not a verifier. |
| Lean 4 replacement | Lean has dependent types, HOL, tactics, libraries, metatheory. Stele is propositional. |
| Rocq/Coq replacement | Same as above. |
| Isabelle/HOL replacement | Same as above. |
| Full proof assistant | No tactic language, no module system, no universe hierarchy. |
| Full first-order logic system | Surface language is propositional; FOL is proof-term level only. |

**Doc:** `docs/development-context.md` §1, `docs/references.md §2`, `docs/provenance-map.md` Table 2

---

## 1.4 Core contributions (honest summary)

The following are implemented and tested as of v1.1.0.

### C1 — Trusted natural-deduction proof checker

A small (~400 line), dependency-free trusted kernel that checks proof scripts by
**syntactic pattern matching** against rule schemas. No semantic reasoning.

- **Status:** Stable
- **Module:** `stele/kernel.py`
- **Evidence:** `tests/test_kernel_valid.py` (correct proofs accepted),
  `tests/test_kernel_invalid.py` (incorrect proofs rejected)
- **Example:** `examples/dne.stele` (classical), `examples/neg_intro.stele` (intuitionistic)

### C2 — Rule sets as data

Five built-in logic objects: `intuitionistic_prop`, `classical_prop`, `K3`, `LP`,
`boolean`. Adding a new logic means adding `RuleSchema` objects; the kernel is never
modified.

- **Status:** Stable
- **Module:** `stele/logic.py`
- **Evidence:** `tests/test_logic.py`, `tests/test_kernel_valid.py`

### C3 — Structural diagnostics (untrusted)

Four-pass structural analysis that locates and classifies errors: undefined symbols,
missing hypotheses, invalid transitions, circular dependencies.

- **Status:** Untrusted / 9 stable diagnostic codes
- **Module:** `stele/diagnostics.py`
- **Evidence:** `tests/test_diagnostics.py`

### C4 — Multi-valued matrix semantics (demo/diagnostic)

K3 (strong Kleene), LP (Logic of Paradox), and Boolean matrix evaluators with a
rule-soundness checker. Separates syntactic derivability (⊢) from semantic validity (⊨).

- **Status:** Demo
- **Module:** `stele/matrix.py`
- **Evidence:** `tests/test_matrix.py`

### C5 — Finite Kripke countermodel search (experimental)

Bounded enumeration of Kripke frames to find countermodels for IPL formulas.

- **Status:** Experimental (bounded; no completeness)
- **Module:** `stele/kripke.py`
- **Evidence:** `tests/test_kripke.py`

### C6 — Proof-term core / Curry–Howard (experimental)

IPL proof terms with bidirectional typing, β-reduction, de Bruijn indices, and a
script-to-term elaboration pass.

- **Status:** Experimental
- **Module:** `stele/core/`, `stele/elaborate.py`
- **Evidence:** `tests/test_elaboration.py`, `tests/test_proof_term_typing.py`

### C7 — Proof certificates and independent minicheck (experimental)

After kernel verification, a versioned JSON certificate is emitted. `minicheck.py`
re-verifies without importing `kernel.py` or `parser.py`.

- **Status:** Experimental
- **Module:** `stele/certificate.py`, `stele/minicheck.py`
- **Evidence:** `tests/test_minicheck.py`

### C8 — Browser-local deployment via Pyodide

The complete checker (kernel, parser, diagnostics) runs in-browser. No backend server.

- **Status:** Stable
- **Module:** `stele/browser.py`, `site/studio.html`
- **Evidence:** `tests/test_pyodide_site.py`

---

## 1.5 Version and test status

- **Version:** `1.1.0` (`stele/__version__.py`)
- **Tests:** 2280 passed, 4 skipped (without Hypothesis); CI on Python 3.10, 3.11, 3.12
- **Test count source:** pytest output, current repo state
- **Runtime dependencies:** 0 (stdlib only)
- **Optional dev dependencies:** `pytest`, `hypothesis` (property-based tests)
