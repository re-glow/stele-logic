# 11 — Limitations and Future Work

**Status:** Stable (limitations documentation)
**Evidence:** `docs/development-context.md`, `CLAUDE.md §로드맵`, `paper/stele-whitepaper.tex §Limitations`

---

## 11.1 Current limitations

### L1 — Propositional surface language

The Stele-Light proof language is propositional. There are no quantifiers (`forall`,
`exists`) in the surface syntax. FOL is available only at the proof-term level
(`stele/core/fol.py`), not in the Stele-Light surface.

**Impact:** Cannot write a Stele-Light proof of "for all x, P(x) implies P(x)."
**Evidence:** `docs/semantics.md §2.2` (grammar has no quantifier in `formula` for proof scripts)

### L2 — No equality or function symbols

No `=` relation, no function terms (f(x)), no arithmetic. Pure propositional/predicate
logic over atomic propositions.

### L3 — No proof search

Stele is a **proof checker**, not a **proof finder**. The kernel only verifies proofs
that the user writes explicitly. There is no automation, no tactic language, no
`simp/auto/omega`.

### L4 — No machine-checked metatheory

Metatheory claims (subject reduction, normalization, consistency) are supported by
regression tests and proof sketches — not by machine-checked proofs in Lean/Coq/Agda.

**Safe wording:** "supported by regression tests and proof sketches"
**Unsafe wording:** "formally verified," "machine-checked"

### L5 — Bounded Kripke search (incomplete)

The Kripke countermodel search is bounded: it searches frames up to `max_worlds` (3–4)
worlds. Finding no countermodel does **not** prove the formula is IPL-valid. The search
is sound (countermodels found are genuine) but not complete.

### L6 — Classical proof terms excluded

Classical rules (`dne`, `lem`, `pbc`) are verified by the kernel but **cannot be
elaborated** into proof terms. The λμ-calculus / continuation-based approach for
classical proof terms is not implemented.

### L7 — Same-process certificate isolation

The minicheck re-verifier runs in the same Python process. This provides code-level
but not process-level or language-level isolation.

### L8 — ML baseline: small synthetic corpus

The ML baseline is trained on 400 generated records and evaluated on 40 committed
records. The corpus is synthetic (template-based). These numbers are too small to draw
general conclusions.

### L9 — Lean bridge: error-message parsing only

The `stele_lean/` bridge parses Lean 4 error output and maps type-mismatch patterns to
Stele diagnostic codes. This is advisory only. No formal Lean↔Stele correspondence.

### L10 — No completeness engine

Stele has no procedure for determining whether a formula is classically or
intuitionistically valid. Checking is a syntactic operation over user-supplied proofs.

### L11 — Pyodide: CDN dependency and load size

The browser-local deployment requires the Pyodide runtime (~8 MB first-load from CDN).
Not fully offline.

### L12 — Single-file HTML: CDN dependency for Pyodide

`dist/stele.html` embeds the Stele source but depends on CDN for the Pyodide runtime.
A fully self-contained offline bundle is not yet implemented.

---

## 11.2 Future work (from `CLAUDE.md §로드맵`)

### Near-term verification core

| Item | Priority | Status |
|------|----------|--------|
| FOL quantifiers in surface language | High | Future |
| Structural rule policy declarations (weakening/contraction/exchange) | Medium | Future |
| Error diagnosis improvement (more precise location) | Medium | Future |
| de Bruijn object-level variable conversion | Low | Partial |

### Optional extensions (outside trusted core)

| Item | Priority | Status |
|------|----------|--------|
| Lean bridge maturation (`stele_lean/` expansion) | Low | Optional/Future |
| Minicheck Rust/OCaml port (process-level isolation) | Medium | Future |
| Kernel Rust/OCaml port (sum types, exhaustive pattern matching) | Low | Future |
| Machine-checked metatheory (Lean/Coq/Agda export) | Distant | Future |

### Semantics and logics

| Item | Priority | Status |
|------|----------|--------|
| λμ-calculus / continuation typing for classical proof terms | Medium | Future |
| Stronger Kripke semantics (completeness for fragments) | Medium | Future |
| Equality / function-symbol FOL | Medium | Future |
| Full Yurihak logic formalization | Distant | Motivation → Future |
| Closure atlas / window-localized semantics | Distant | Motivation → Future |

### ML and measurement

| Item | Priority | Status |
|------|----------|--------|
| Larger measured ML corpus (real user proofs) | Medium | Future |
| Alternative ML models (sequence models, graph models) | Low | Speculative |

### Infrastructure

| Item | Priority | Status |
|------|----------|--------|
| Fully offline Pyodide bundle | Low | Future |
| Site / presentation polish | Low | Ongoing |

---

## 11.3 What will NOT be added

From `CLAUDE.md §비목표`:

- Automatic proof search in the kernel (checker ≠ prover)
- Many-valued / paraconsistent Lean export
- Presenting Python tests as machine-checked metatheory proofs
- Claiming implemented features that are not yet implemented
