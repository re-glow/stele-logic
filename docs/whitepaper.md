# Stele: A Lightweight Formal Verification Framework for Mathematical Reasoning

*Version 1.0.0 — Research Software Artifact*

---

## Table of Contents

1. [Abstract](#abstract)
2. [Introduction](#introduction)
3. [Positioning and Non-goals](#positioning-and-non-goals)
4. [Architecture and Trust Boundary](#architecture-and-trust-boundary)
5. [Stele-Light Proof Language](#stele-light-proof-language)
6. [Proof-Term Core and Elaboration](#proof-term-core-and-elaboration)
7. [Structural Diagnostics and Proof-State Tooling](#structural-diagnostics-and-proof-state-tooling)
8. [Semantic Diagnostics](#semantic-diagnostics)
9. [Proof Certificates and Minicheck](#proof-certificates-and-minicheck)
10. [Browser Deployment and Distribution](#browser-deployment-and-distribution)
11. [Optional ML Baseline and Corpus Discipline](#optional-ml-baseline-and-corpus-discipline)
12. [Evaluation and Testing](#evaluation-and-testing)
13. [Related Work](#related-work)
14. [Limitations](#limitations)
15. [Future Work](#future-work)
16. [Conclusion](#conclusion)
17. [Appendix: Component Status Table](#appendix-component-status-table)

---

## Abstract

We present **Stele**, a lightweight formal verification framework for mathematical reasoning, implemented as a rule-checked proof language with an explicit trust boundary. The core contribution is a small, auditable symbolic proof checker — *Stele-Light* — in which users write natural-deduction proofs, and the kernel verifies each step against a declared rule schema. The trusted kernel is a 142-line Python module with zero runtime dependencies. Stele additionally provides a Curry–Howard proof-term core with bidirectional type checking and β-reduction for intuitionistic propositional logic; structural diagnostics that locate missing hypotheses, invalid transitions, undefined symbols, and unused assumptions; matrix-valued semantic diagnostics for Boolean, K3 (strong Kleene), and LP (Logic of Paradox) logics; a bounded Kripke countermodel search for intuitionistic non-theorems; versioned proof certificates with an independent re-verification path; a browser-local Studio running via Pyodide/WebAssembly; and an optional statistical ML baseline for proof classification. The entire system has zero runtime dependencies and 1808 tests. Stele is not a theorem prover, SMT solver, AI-powered verifier, or full proof assistant. All metatheoretic claims about the proof-term layer are supported by regression and property-based tests, not machine-checked formal proofs.

---

## Introduction

Students and researchers working with formal arguments — logic courses, foundations of mathematics, proof-theoretic investigations — need tools that are small, auditable, and honest about what they verify. Existing options occupy two extremes. Full proof assistants such as Lean 4, Rocq (formerly Coq), and Isabelle are extremely powerful, but they require substantial learning investment, have large codebases, and can be difficult to deploy or audit. At the other extreme, AI-based systems can generate proof-like text but obscure the trust boundary between heuristic suggestion and verified derivation.

Stele occupies a different niche: a *small, inspectable proof-checking framework* with explicit, documented trust boundaries. The user writes every inference step; the kernel decides whether each step is a valid instance of the declared rule. The kernel does not search for proofs and does not use any semantic knowledge of the target logic — it only matches step conclusions against rule schemata syntactically. This design makes the trust boundary precise and auditable: `stele/kernel.py` is 142 lines of pure Python with no external dependencies.

Stele further provides several optional layers that assist reasoning without entering the trust boundary: structural diagnostics that identify likely error causes, a Curry–Howard proof-term core for proof-term extraction and metatheoretic exploration, matrix-valued semantic diagnostics, Kripke-model counterexample search, and a browser-local interactive Studio. These layers are always marked UNTRUSTED and require re-verification by the kernel before any claims are made.

This document describes Stele v1.0.0 as a research software artifact. It is intended for researchers and educators interested in small verification tools, proof-theoretic tooling, logical pluralism, or the architecture of trusted software systems.

---

## Positioning and Non-goals

Stele is positioned as a **proof checker and semantic diagnostics platform**. It is explicitly *not*:

- **A theorem prover.** Stele does not search for proofs. If the user does not supply every inference step, Stele cannot supply them.
- **An SMT or SAT solver.** There is no constraint solving, satisfiability checking, or arithmetic reasoning.
- **An AI-powered verifier.** ML components are optional, isolated, and UNTRUSTED. The ML baseline predicts likely validity/error codes but does not verify anything.
- **A production proof assistant.** Stele lacks dependent types, a module system, higher-order unification, tactics, and the theorem libraries that characterize systems such as Lean, Rocq, or Isabelle.
- **A full first-order prover.** The proof-script surface is propositional. First-order logic is available only in the experimental proof-term layer.
- **A formally verified system.** Metatheoretic properties of the proof-term core are supported by regression tests and proof sketches, not by machine-checked proofs in a formal proof assistant.

Stele *is*:

- A **rule-checked natural-deduction proof language** with a small, auditable trusted kernel.
- A **proof-term and metatheory playground** for exploring Curry–Howard correspondences and reduction behavior.
- A **semantic diagnostics platform** for Boolean, K3, and LP matrix logics and bounded Kripke models.
- A **reproducible research software artifact** with zero runtime dependencies, a comprehensive test suite, and documented claim boundaries.

The motivation for logical pluralism — studying how different inference rules behave in different semantic environments — is a background inspiration for the semantic tools, but Stele does not make first-order philosophical claims about logical pluralism. It is a tool that can help investigate such questions empirically.

---

## Architecture and Trust Boundary

```
┌────────────────────────────────────────────────────┐
│  TRUSTED: stele/kernel.py (142 lines, stdlib only) │
│  stele/ast.py · stele/proof.py · stele/parser.py  │
│  stele/logic.py · stele/errors.py                 │
└──────────────────┬─────────────────────────────────┘
                   │ re-verified by kernel
┌──────────────────▼──────────────────────────────────┐
│  UNTRUSTED / OPTIONAL layers                         │
│  stele/diagnostics.py   structural diagnostics       │
│  stele/proofgraph.py    dependency graph             │
│  stele/proofstate.py    proof-state hints            │
│  stele/matrix.py        many-valued semantics        │
│  stele/world.py         world/lattice demo           │
│  stele/kripke.py        Kripke countermodel search   │
│  stele/certificate.py   certificate emission         │
│  stele/minicheck.py     independent re-checker       │
│  stele/elaborate.py     script→term elaboration      │
│  stele/core/            proof-term calculus (IPL+IQL)│
│  stele/browser.py       Pyodide bridge               │
│  stele/web.py           HTTP Studio server           │
├─────────────────────────────────────────────────────┤
│  EXTERNAL / ISOLATED (not in trusted path)           │
│  stele_ml/              optional ML baseline         │
│  stele_lean/            optional Lean 4 bridge       │
└─────────────────────────────────────────────────────┘
```

### The Trusted Core

The trust boundary is `stele/kernel.py`. Its design follows the de Bruijn criterion: the trusted code should be small enough for a human auditor to read completely. The kernel contains:

1. `match(pat, tgt, metavars, subst)` — syntactic first-order pattern matching; no semantic knowledge.
2. `instantiate(pat, subst)` — apply a substitution to a pattern.
3. `check_theorem(thm, logic_override)` — entry point; calls `_check_block`.
4. `_check_block(lines, env, logic, top)` — walks proof nodes; dispatches to `_check_have` and `_check_suppose`.

The kernel imports only `ast`, `proof`, `errors`, and `logic` from the same package — all standard-library-only modules. No matrix semantics, ML, or diagnostic code is imported by the kernel.

**Rule-data separation:** Rules are not compiled into the kernel. They live in `logic.py` as `RuleSchema` frozen dataclass instances. Adding a new logic means adding a `RuleSchema` set; it never requires touching the kernel.

### The Parser

`stele/parser.py` is a hand-written recursive descent tokenizer and parser. It has no third-party dependencies. The parser is logically part of the trusted input layer (a parse error before the kernel sees any input is caught at the parse stage), but it is not part of the semantic trust boundary — a malformed proof that passes the parser and fails the kernel is still correctly rejected.

### Untrusted Layers

Every module outside `kernel.py` is considered untrusted in the sense that bugs in those modules cannot cause a false-positive kernel verification. Structural diagnostics, proof-state hints, dependency graphs, Kripke search, and certificate emission all call back through the kernel for any claim of proof validity.

---

## Stele-Light Proof Language

Stele-Light is the surface proof language. It is a natural-deduction language at the propositional level.

### Proof Structure

A Stele-Light proof consists of:

```
theorem <name> [using <logic>]:
  assume <label>: <formula>     # introduce a hypothesis
  suppose <label>: <formula>    # begin a sub-proof (will be discharged)
    have <label>: <formula> by <rule> <ref>...
    ...
  have <label>: <formula> by <rule> <ref>...
  conclude <formula> by <ref>
```

`suppose` blocks introduce dischargeable assumptions. When a `suppose` block closes, the assumption is no longer available; the rule that discharges it (e.g., `imp_intro`) must reference both the suppose label and the block's conclusion.

### Built-in Logics

| Logic name | Rules | Notes |
|------------|-------|-------|
| `intuitionistic_prop` | 12 rules | Default; IPL natural deduction |
| `classical_prop` | 12 + 3 = 15 rules | Adds `dne`, `lem`, `pbc` |
| `K3` | matrix mode | Strong Kleene three-valued semantics |
| `LP` | matrix mode | Logic of Paradox (Priest) |
| `boolean` | matrix mode | Classical Boolean semantics |

### Inference Rules

The intuitionistic rule set:

| Rule | Premises | Conclusion |
|------|----------|------------|
| `copy` | A | A |
| `mp` | A→B, A | B |
| `and_intro` | A, B | A∧B |
| `and_elim_left` | A∧B | A |
| `and_elim_right` | A∧B | B |
| `neg_elim` | A, ¬A | ⊥ |
| `ex_falso` | ⊥ | A |
| `or_intro_left` | A | A∨B |
| `or_intro_right` | B | A∨B |
| `imp_intro` | *(A ⊢ B)* | A→B (discharge) |
| `neg_intro` | *(A ⊢ ⊥)* | ¬A (discharge) |
| `or_elim` | A∨B, *(A ⊢ C)*, *(B ⊢ C)* | C (2 discharges) |

Classical extensions: `dne` (¬¬A ⊢ A), `lem` (⊢ A∨¬A), `pbc` (*(¬A ⊢ ⊥)* ⊢ A).

### Example: Double-Negation Elimination (Classical)

```
theorem dne_consequent:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
```

This proof is accepted under `classical_prop` and rejected under `intuitionistic_prop` because `dne` is not in the intuitionistic rule set.

### Example: Implication Introduction (Intuitionistic)

```
theorem imp_self using intuitionistic_prop:
  suppose h: P
    have hcopy: P by copy h
  have result: P -> P by imp_intro h hcopy
  conclude P -> P by result
```

### Formula Definitions

Stele supports formula abbreviations via `definition` declarations:

```
definition IMP_SELF := P -> P

theorem t using intuitionistic_prop:
  assume h: IMP_SELF
  ...
```

Definitions are expanded before the kernel sees the proof, maintaining the kernel's syntactic purity.

---

## Proof-Term Core and Elaboration

### Curry–Howard Correspondence

Stele includes a proof-term core (`stele.core`) implementing a typed lambda calculus corresponding to intuitionistic propositional logic (IPL) plus an experimental first-order logic (FOL) fragment. The Curry–Howard correspondence maps:

| Logic | Proof-term |
|-------|------------|
| A→B | λx:A. e : A→B |
| A∧B | Pair(e₁, e₂) : A×B |
| A∨B | Inl(e) / Inr(e) : A+B |
| ⊥ | AbsurdElim(e, A) |
| ¬A | λx:A. ⊥ (abbreviation) |
| ∀x. A(x) | ΛForall(x, e) : ∀x. A(x) |
| ∃x. A(x) | PairExists(t, e) : ∃x. A(x) |

All proof-term constructors are frozen dataclasses. The type checker is bidirectional (checking and inference modes), operating on a context of type bindings.

### de Bruijn Binders

Proof-variable binders in the term calculus use de Bruijn indices (`stele.core.debruijn`). The named API is preserved for user-facing code; the internal representation uses indices to eliminate α-renaming issues in substitution and α-equivalence checking. Object-level variables in the experimental FOL fragment remain named (de Bruijn conversion at the object level is implemented but incomplete).

### Script-to-Term Elaboration

`stele.elaborate.crosscheck_theorem` provides a three-stage verification pipeline:

1. **Kernel check** — verifies the proof script with `check_theorem`.
2. **Elaboration** — translates each proof step to its Curry–Howard proof term.
3. **Type check** — re-verifies the elaborated term with the core type checker.

If all three stages succeed, the result is a `CrossCheckResult` containing the proof term. The elaboration path currently supports the full intuitionistic rule set (including discharge rules `imp_intro`, `neg_intro`, `or_elim`). Classical rules are not supported in the elaboration path; the kernel remains the authority for classical proofs.

### Reduction and Normalization

`stele.core.reduce.normalize` reduces a closed proof term to normal form via β-reduction. The reducer is fuel-limited (default 1000 steps) to ensure termination on potentially non-normalizing terms. η-reduction is not implemented.

**Claimed metatheory (not machine-checked):**
- Subject reduction (type preservation): supported by regression and property-based tests; proof sketch in `docs/metatheory.md`.
- Normalization: follows from standard strong normalization for simply typed lambda calculus; fuel limit provides a conservative bound.
- Confluence: local confluence tests pass; full Church-Rosser proof not machine-checked.
- Consistency: no closed term of type `⊥` can be constructed; verified for the rule set by construction.

These claims are supported by 1836 regression tests (including optional Hypothesis property-based tests) and by proof sketches in `docs/metatheory.md`. They are **not machine-checked proofs** in a formal proof assistant.

### Experimental FOL Fragment

The proof-term core contains an experimental first-order logic fragment supporting `ForallIntro`, `ForallElim`, `ExistsIntro`, and `ExistsElim` with a freshness condition on the existential elimination variable. This fragment has no corresponding proof-script surface syntax; it is accessible only through the `stele.core` API. Object-variable de Bruijn conversion is partially implemented.

### Experimental Classical Bridge

`stele.core.classical_experimental` provides a formula-level Gödel–Gentzen negative translation from classical propositional logic to intuitionistic logic. This is a formula transformation only; it does not automatically translate classical proof scripts to intuitionistic ones, and it does not extend the trusted kernel. The module is explicitly marked experimental.

---

## Structural Diagnostics and Proof-State Tooling

### Structural Diagnostics

`stele.diagnostics` performs multi-pass structural analysis of a proof script *outside* the kernel. Diagnostics identify likely error causes for human readers and are always labeled UNTRUSTED — they can produce false positives and do not constitute proof verification.

**Stable diagnostic codes:**

| Code | Description |
|------|-------------|
| `UndefinedSymbol` | A propositional variable used before any introduction |
| `MissingHypothesis` | A referenced label is not in scope |
| `UnsupportedConclusion` | The stated conclusion does not follow from the steps |
| `CircularDependency` | A step directly or transitively references itself |
| `UnusedAssumption` | An assumed formula is never referenced |
| `UndefinedDefinition` | A formula definition references an undeclared name |
| `InvalidTransition` | A rule application is structurally inconsistent |
| `TypeMismatch` | A rule argument has the wrong formula type |
| `KripkeCountermodelFound` | The conclusion has a Kripke countermodel (intuitionistic) |

Each diagnostic includes a line number, severity (error/warning), and a `DiagnosticExplanation` (short description, likely cause, how-to-fix, example, related codes).

### Dependency Graph

`stele.proofgraph` builds a labeled dependency graph of a proof. Each node is a labeled step (assume/have/conclude), and directed edges represent logical dependencies. The graph can be exported in DOT format for visualization with external tools. Graph analysis detects cycles, unused assumptions, and isolated steps.

### Proof-State Inspection

`stele.proofstate` provides UNTRUSTED proof-state snapshots and rule-applicability hints. At any cursor position in a proof:

- `proof_state_from_text(source, logic, cursor_line)` returns a `ProofState` recording available labels, their formulas and scope depths, open assumptions, discharged labels, and the current pending goal.
- `suggest_rule_hints(state)` returns structural pattern-matching hints (up to 10 patterns: `mp`, `and_elim_left/right`, `neg_elim`, `ex_falso`, `imp_intro`, `and_intro`, `or_intro_left/right`, `neg_intro`, `dne`/`lem`/`pbc` if classical). Hints have `trusted=False` always and must be kernel-rechecked.

The `cli state` and `cli hints` subcommands expose these at the command line; the web API exposes them via POST `/api/state` and `/api/hints`.

---

## Semantic Diagnostics

### Matrix Semantics

`stele.matrix` implements many-valued matrix semantics. A `Matrix` consists of a set of truth values, designated values, and truth tables for `not`, `and`, `or`, `imp`.

Three matrices are built in:

| Matrix | Values | Designated | Notes |
|--------|--------|------------|-------|
| `boolean` | {T, F} | {T} | Classical Boolean |
| `K3` | {T, I, F} | {T} | Strong Kleene (K3) |
| `LP` | {T, I, F} | {T, I} | Logic of Paradox (Priest) |

The K3 and LP truth tables follow standard Kleene/Priest conventions, fixed by test `test_k3_imp_table_matches_manifesto`: `I→F = I`, `F→I = T`.

**Rule soundness:** `rule_soundness(schema, matrix)` checks whether each rule schema preserves designated values in all assignments. Classical LEM is sound in Boolean but not in K3 (counterexample: A=I). Explosion (ex falso) is sound in K3 but not in LP (LP is paraconsistent: `P, ¬P` do not entail `Q`). This illustrates how the same natural-deduction rule set can behave differently across semantic environments.

**Example soundness report** (`classical_prop` against K3):

```
lem: unsound  counterexample: A=I
dne: sound
```

Matrix semantics and kernel are mutually non-importing — `kernel.py` never imports `matrix.py` and vice versa (enforced by `test_regression_invariants`).

### World and Lattice Demo

`stele.world` provides a toy propositional world system where each `World` carries a matrix and an axiom set. `lattice_status` computes the status (valid, invalid, contingent) of a formula across a small set of worlds. This is a pedagogical demonstration of how different axiom sets affect formula validity; it is explicitly **not** a set-theoretic forcing construction or a full Kripke completeness theorem.

### Kripke Countermodel Search

`stele.kripke` implements finite bounded Kripke model search for intuitionistic propositional logic. Given a formula, the searcher enumerates Kripke frames with up to *n* worlds (default n=4), checking the intuitionistic forcing condition at each world.

**Algorithm:** The searcher builds all reflexive-and-transitive accessibility relations on *n* worlds, assigns propositional variable values to worlds (respecting monotonicity: if P is true at world w and w ≤ v, then P is true at v), and evaluates the formula under the Kripke forcing semantics.

**Example:** For `P or not P` (excluded middle):

```
result: countermodel found (not intuitionistically valid)
worlds: [0, 1]   order: reflexive + {0 ≤ 1}
  world 0: {}     (neither P nor not-P forced)
  world 1: {P}    (P is forced)
```

This correctly shows that LEM is not intuitionistically valid, since at world 0, neither P nor ¬P is forced.

**Double-negation elimination** (`not not P -> P`) similarly yields a countermodel: a world where P is not yet decided but ¬¬P holds vacuously.

**Limitations:** The search is bounded (finite frame enumeration), not complete. For larger formulae or with many variables, the search may exhaust the bound without finding a countermodel even if one exists beyond the bound. The search is propositional only.

---

## Proof Certificates and Minicheck

### Certificate Format

Stele can emit a versioned JSON proof certificate from a verified proof:

```json
{
  "format": "stele-proof-certificate",
  "version": "1",
  "theorem": "dne_consequent",
  "logic": "classical_prop",
  "conclusion": {"kind": "var", "name": "P"},
  "steps": [...],
  "metadata": {"generator": "stele", "stele_version": "1.0.0"}
}
```

The certificate records each proof step (assume, have, conclude) with its formula (as a JSON-serialized AST), applied rule, and references. It is emitted only after the kernel has verified the proof; a valid certificate is evidence that the proof passed the kernel at version `stele_version`.

### Minicheck

`stele.minicheck` is an independent re-verification path that reads a certificate and verifies it **without importing `stele.kernel` or `stele.parser`**. It implements its own minimal rule-matching logic from first principles, operating only on the serialized certificate JSON.

This design provides a partial independence guarantee: a tampered certificate that passes minicheck without having passed the kernel would indicate a bug in minicheck, not a kernel bypass. The tests include tamper detection (modifying a step formula, removing steps, changing the rule name) and cross-validation (kernel output vs. minicheck output on the same proof).

**Limitation:** Minicheck is implemented in Python in the same process and is not formally verified. It provides an independent *software* check, not a formally verified check. A fully independent verifier would ideally be implemented in a different language (Rust, OCaml, or a proof assistant itself) — this is a documented future direction.

---

## Browser Deployment and Distribution

### Pyodide Browser-Local Studio

Stele Studio is a browser-local interactive proof environment powered by Pyodide (Python compiled to WebAssembly). The Studio runs the full Stele trusted kernel inside the browser — no proof text is sent to any external server.

The Studio provides five panels: **Verify** (kernel check result), **Diagnose** (structural diagnostics), **Graph** (proof dependency graph), **Semantic** (matrix soundness, world lattice, Kripke search), and **Proof State** (context snapshot and rule-applicability hints).

First-load Pyodide runtime is approximately 8 MB (cached by the browser after the initial visit).

**What runs locally:** full proof checking, structural diagnostics, dependency graph, rule soundness, world lattice, Kripke search, proof state.
**Excluded from browser build:** `stele_ml/`, `stele_lean/`, benchmark runner, tests.

### Distribution Modes

| Mode | How to use | Notes |
|------|------------|-------|
| **Hosted site** (GitHub Pages) | Open URL | Auto-deployed on push to `main` |
| **Single-file HTML** (`stele.html`) | `python tools/build_single_html.py` | CDN for Pyodide; share or open from disk |
| **Standalone executable** | `python packaging/build_app.py` → `dist/SteleStudio` | PyInstaller; ~50 MB binary |
| **Local Python** | `python -m stele` | Python 3.10+, no extra dependencies |

The local Python server (`stele.web`) serves the same Studio SPA via a stdlib HTTP server.

---

## Optional ML Baseline and Corpus Discipline

### Architecture

`stele_ml/` is an optional, fully isolated package providing a statistical approximation baseline for proof classification. It is **entirely outside the trusted verification path**. The package is never imported by `stele/` (enforced by `test_ml_isolation.py`).

The model is a Multinomial Naive Bayes classifier with Laplace smoothing (α=1.0), implemented in pure Python (stdlib only, no scikit-learn required). It predicts:

1. **Proof validity** — binary (valid / invalid).
2. **Diagnostic codes** — multi-label one-vs-rest, over the 6 surface diagnostic codes.

### Corpus

The training corpus is generated by `bench/generate.py` from three synthetic families:

| Corpus family | Proportion | Description |
|--------------|-----------|-------------|
| `prop_nd` | 60% | Natural-deduction proofs in propositional logic |
| `definition_use` | 20% | Proofs with formula definitions (valid and with errors) |
| `diagnostic_errors` | 20% | Proofs with injected errors |

Generation is fully deterministic given `(--corpus, --n, --seed, --shard-size)`. The committed sample is 40 records (seed=0). The manifest records `label_stats` (n_valid, n_invalid, code distribution) and `creation_command` for reproducibility.

### Measured Metrics

The following metrics are measured from the actual pipeline on the committed 40-example sample (model trained on 400 in-memory examples, seed=0):

| Metric | Value | Note |
|--------|-------|------|
| Validity accuracy | 0.85 | 34/40 examples correct |
| Exact match | 0.60 | Validity AND all codes correct |
| Micro F1 | 0.50 | Weighted across code predictions |
| Macro F1 | 0.36 | Averaged over codes with support |

**These numbers must not be cited as general accuracy claims.** They are measurements on a 40-example synthetic corpus. The distribution is not representative of real user proofs. Template-level leakage may inflate metrics relative to a genuinely held-out test set.

### Corpus Discipline

Data discipline features implemented:

- **Manifest schema** includes `label_stats` and `creation_command`; all generation is reproducible from the manifest.
- **3-way split** via `stele_ml/build_dataset.py` produces disjoint train/dev/test JSONL files with a `split_manifest.json`.
- **Failure-mode analysis** in `stele_ml/reports/baseline_report.json` categorizes codes as under-predicted, over-predicted, or well-predicted.
- **Benchmark card** at `docs/benchmark-card.md` documents limitations, known leakage, and full reproduction steps.

---

## Evaluation and Testing

### Test Suite

Stele has 1836 tests (1836 passing, 4 skipped without Hypothesis), organized into 44+ test files:

| Category | Tests | Notes |
|----------|-------|-------|
| Parser | `test_parser.py` | Token/AST correctness |
| Kernel (valid) | `test_kernel_valid.py` | Correct proofs accepted |
| Kernel (invalid) | `test_kernel_invalid.py` | Incorrect proofs rejected |
| Classical principles | `test_classical_principles.py` | dne/lem/pbc in classical, absent in intuitionistic |
| Discharge rules | `test_discharge_rules.py`, `test_generalized_discharge.py` | imp_intro/neg_intro/or_elim |
| Matrix semantics | `test_matrix.py`, `test_matrix_surface.py` | K3/LP/boolean truth tables |
| Rule soundness | `test_rule_soundness.py` | Per-rule soundness checks |
| World/lattice | `test_world.py`, `test_world_lattice.py` | World status computation |
| Proof terms | `test_proof_terms.py`, `test_reduction.py`, `test_debruijn.py` | Term calculus |
| Elaboration | `test_elaboration.py` | Script-to-term pipeline |
| FOL fragment | `test_fol.py`, `test_fol_surface.py`, `test_fol_object_debruijn.py` | FOL proof terms |
| Kripke | `test_kripke.py`, `test_kripke_integration.py` | Countermodel search |
| Diagnostics | `test_diagnostics.py` | Structural error detection |
| Certificates | `test_certificate.py`, `test_minicheck.py` | Emission and verification |
| Proof state | `test_proofstate.py` | State/hint extraction |
| ML baseline | `test_ml_baseline.py`, `test_ml_isolation.py` | Baseline pipeline, isolation |
| ML corpus discipline | `test_ml_corpus_discipline.py` | Determinism, schema, claims |
| Gallery | `test_gallery.py` | Honesty of 15 curated examples |
| Regression | `test_regression_invariants.py` | Trust boundary enforcement |
| Classical experimental | `test_classical_experimental.py` | Gödel–Gentzen translation |
| Property-based | `test_proof_term_properties.py` | Optional Hypothesis tests |

### Gallery Honesty Tests

The site's example gallery contains 15 curated proofs with expected labels:
- 7 `basics` — valid intuitionistic proofs
- 3 `classical` — classical-only proofs (fail intuitionistically)
- 5 `diagnostics` — error/warning cases

Every CI run (`ci.yml`) re-verifies all 15 labels against the live kernel via `test_gallery.py`. If any proof is edited in a way that changes its verification outcome, the CI fails. This prevents the gallery from containing stale claims.

### Kernel Isolation Invariants

`test_regression_invariants.py` enforces:
- `kernel.py` does not import `matrix.py` (matrix ≠ proof mode)
- `matrix.py` does not import `kernel.py`
- `stele_ml/` modules contain no imports of `stele.kernel` or `stele.diagnostics`
- Minicheck does not import `stele.kernel` or `stele.parser`

### CI Workflows

| Workflow | Trigger | Notes |
|----------|---------|-------|
| `ci.yml` | Every push/PR | Python 3.10/3.11/3.12; no ML deps required |
| `pages.yml` | Push to main | Build/deploy GitHub Pages site |
| `release.yml` | Annotated tag | Build executable + `stele.html` |
| `ml.yml` | Manual only | Optional ML pipeline; not in core CI |

The core CI (`ci.yml`) requires only `pytest` — no ML, LaTeX, or Lean dependencies.

---

## Related Work

### Proof Assistants

Systems such as Lean 4, Rocq (formerly Coq), and Isabelle/HOL are full proof assistants offering dependent types, rich tactic languages, large theorem libraries, and machine-checked metatheory. Agda provides dependent types with a focus on type-theoretic programming. These systems have significantly larger codebases and steeper learning curves than Stele. Stele is not a replacement for these tools; it is designed for settings where a small, auditable checker is more appropriate than a full proof assistant.

### Curry–Howard Correspondence and Proof Terms

The Curry–Howard correspondence between proofs and typed programs is foundational to the design of Stele's proof-term core. The correspondence between natural-deduction proofs in intuitionistic logic and simply typed lambda calculus is classical [Curry–Howard]; the extension to first-order logic via dependent types is standard in type theory. Stele's implementation follows the standard bidirectional type-checking architecture.

### Normalization and Reduction

Strong normalization of simply typed lambda calculus is a classical result. Stele's fuel-limited normalization provides a practical termination guarantee consistent with this; the theoretical underpinning is standard. Normalization by evaluation is a related technique for obtaining normal forms efficiently; Stele uses explicit reduction rather than NbE.

### Kripke Semantics for Intuitionistic Logic

Kripke models for intuitionistic logic, in which formulas are evaluated at possible worlds with a monotone accessibility relation, were introduced by Saul Kripke in the 1960s. The forcing condition (A is forced at w iff A is forced in all accessible worlds when A is a disjunction of subformulas not yet decided at w) is standard. Stele's bounded search implements this forcing condition directly.

### Paraconsistent and Many-Valued Logics

LP (Logic of Paradox) was introduced by Graham Priest as a paraconsistent logic in which contradictions can be true without trivializing the logic. K3 (strong Kleene) was developed independently for three-valued semantics. Both are matrix logics in the sense of Łukasiewicz. Stele implements their standard truth tables and uses them for rule soundness diagnostics, illustrating how the same natural-deduction rules have different semantic properties across these systems.

### Proof Certificates and Independent Verification

The idea of emitting proof certificates that can be checked independently of the generating system is well-established in formal verification (e.g., the LF logical framework). Stele's certificate format is a lightweight JSON encoding of the checked proof steps, verified by an independent Python re-checker. This is much simpler than a full logical framework and is not formally verified.

### ML for Theorem Proving

Several systems apply machine learning to support automated theorem proving (e.g., neural network guidance for tactic selection, LLM-based proof generation). Stele's ML baseline is of a different character: it is a *classification* model that predicts likely validity and diagnostic codes, not a proof-generating system. The baseline is explicitly UNTRUSTED and is evaluated only on a small synthetic corpus. We note the existence of ML-assisted proving research without claiming membership in that line of work.

---

## Limitations

### Proof Language

- **Propositional only.** The Stele-Light surface language is propositional. There is no quantifier syntax in the proof script level.
- **No equality or function symbols.** The formula language contains only propositional variables, connectives, and (in the proof-term FOL fragment) uninterpreted predicates. Arithmetic, equality, and function terms are absent.
- **No proof search.** The checker is purely a verifier. If the user does not supply every inference step, Stele cannot find missing steps.
- **Linear proof structure.** Stele-Light proofs are structured as linear sequences of steps with `suppose` sub-blocks. More complex proof structures (e.g., structured Isar-style blocks, or tree-based proof terms with multiple goals) are not supported in the surface language.

### Proof-Term Core

- **Intuitionistic only.** The elaboration path supports only the intuitionistic rule set. Classical proofs (with `dne`, `lem`, `pbc`) cannot be elaborated.
- **FOL experimental.** The first-order proof-term fragment is experimental; object-variable de Bruijn conversion is incomplete; there is no surface syntax for FOL proofs.
- **No dependent types.** The proof-term calculus is simply typed; it cannot express dependent types, propositions-as-types beyond the first-order level, or inductive types.
- **Metatheory not machine-checked.** Subject reduction, normalization, confluence, and consistency are supported by proof sketches and tests, not by proofs in a formal proof assistant.

### Semantic Tools

- **Kripke search is bounded.** The Kripke countermodel search is limited to finite frames of up to 4 worlds by default (configurable). It is neither sound nor complete as a proof procedure — it can fail to find a countermodel that exists beyond the bound.
- **Matrix semantics are propositional.** K3, LP, and Boolean matrix diagnostics are propositional; there is no predicate-level matrix semantics.
- **World/lattice is a toy demo.** The world/lattice module provides a pedagogical propositional demonstration; it is not set-theoretic forcing, not Kripke completeness, and not a model-theoretic metatheorem.

### Infrastructure

- **ML is experimental and small-corpus.** The ML baseline trains on a 40–400 record synthetic corpus, which is too small to support general accuracy claims.
- **Lean bridge is experimental.** The Lean 4 bridge supports only a propositional fragment and requires an external Lean 4 installation.
- **Browser requires Pyodide CDN.** The browser Studio requires fetching Pyodide (~8 MB) from the CDN on first load. Fully offline deployment is a future direction.
- **Minicheck is Python, not formally verified.** The minicheck re-verification path is an independent Python implementation, not a mechanically proved checker.

---

## Future Work

### Verification Core

- **First-order surface syntax.** Adding quantifiers (`forall`, `exists`) to the Stele-Light proof script language, with corresponding kernel rules for universal instantiation and existential introduction/elimination.
- **Equality and function symbols.** Extending the formula language with equality and uninterpreted function symbols, relevant for formalizing mathematical arguments beyond pure propositional logic.
- **Structural rule policies.** Explicit declarations of structural rules (weakening, contraction, exchange) to support linear, relevant, and hyperintensional logical worlds.
- **Proof-state tracking.** Richer open-goal tracking so that the proof-state module can more precisely report which sub-goals remain open.

### Semantic Expansion

- **Kripke semantics for predicates.** Extending the Kripke countermodel search to first-order Kripke frames, enabling countermodel generation for predicate-logic formulae.
- **Completeness diagnostics.** Studying what it would mean for the bounded search to be sound and complete for the propositional fragment (the answer is yes up to the frame bound).

### Infrastructure

- **Rust/OCaml minicheck.** Implementing the certificate re-checker in a statically typed compiled language, providing a stronger independence guarantee than the current Python implementation.
- **Lean import/export maturation.** Stabilizing the Lean bridge to support a larger fragment, possibly bidirectional (Stele to Lean and Lean to Stele).
- **ML data scaling.** After the corpus discipline infrastructure is validated, scaling the training corpus with larger synthetic generation runs and evaluating on a properly held-out real-world sample.
- **Fully offline browser mode.** Bundling the Pyodide runtime into the single-file HTML for operation without CDN access.
- **Proof-assistant integration tests.** Formally verifying key metatheoretic claims (subject reduction, confluence) using Lean or Rocq, providing a machine-checked foundation for the proof-term core.

---

## Conclusion

Stele is a lightweight, auditable formal verification framework occupying a space between informal mathematical notation and full proof assistants. Its primary contribution is a small, inspectable trusted kernel — 142 lines, zero runtime dependencies — that checks natural-deduction proofs against declared rule schemata syntactically. Around this kernel, Stele provides a Curry–Howard proof-term core, structural diagnostics, matrix-valued semantic tools, bounded Kripke countermodel search, proof certificates, and a browser-local Studio.

Stele is designed to make the trust boundary explicit and auditable at every layer. Components outside the kernel are systematically marked UNTRUSTED and require kernel re-verification. The optional ML baseline is statistically measured, uses disciplined corpus management, and makes no verified claims. Metatheoretic properties are supported by proof sketches and tests, not by machine-checked proofs, and this limitation is consistently documented.

Stele v1.1.0 comprises 1836 tests, 15 curated gallery examples with CI-enforced honesty labels, and zero runtime dependencies for the core verification path. It is available as a public GitHub Pages site, a single-file HTML, a standalone executable, and a local Python package.

---

## Appendix: Component Status Table

The following table summarizes every major component's implementation status, supporting evidence, and known limitations.

| Component | Status | Supporting Evidence | Key Limitation |
|-----------|--------|---------------------|----------------|
| Stele-Light proof checker | **Stable** | 1808 tests; `test_kernel_valid.py`, `test_kernel_invalid.py` | Propositional only |
| Intuitionistic prop rules (12) | **Stable** | All kernel tests | — |
| Classical prop extensions (dne, lem, pbc) | **Stable** | `test_classical_principles.py` | Not in intuitionistic |
| Formula definitions | **Stable** | `test_definitions.py` | Expansion before kernel; no recursive definitions |
| Structural diagnostics | **Stable** | `test_diagnostics.py` | UNTRUSTED; multi-pass; not all modes covered |
| Dependency graph | **Stable** | `test_proofgraph.py` | DOT format; visualization needs external Graphviz |
| Matrix semantics (K3/LP/boolean) | **Stable** | `test_matrix.py`, `test_rule_soundness.py` | Propositional; discharge rules skipped in soundness |
| World/lattice demo | **Stable (demo)** | `test_world.py`, `test_world_lattice.py` | Toy propositional demo; not set-theoretic forcing |
| Proof-term core (IPL, Curry–Howard) | **Stable** | `test_proof_terms.py`, `test_elaboration.py` | Intuitionistic only; no classical terms |
| Script-to-term elaboration | **Stable** | `test_elaboration.py` | Intuitionistic rules only |
| Proof-term reduction/normalization | **Stable** | `test_reduction.py` | Fuel-limited; no η-reduction |
| de Bruijn binder layer | **Stable** | `test_debruijn.py` | Proof variables only; FOL object vars remain named |
| Proof-state inspection | **Stable (UNTRUSTED)** | `test_proofstate.py` (78 tests) | UNTRUSTED; hints require kernel recheck |
| Kripke countermodel search | **Experimental** | `test_kripke.py`, `test_kripke_integration.py` | Bounded (≤4 worlds default); propositional only |
| Proof certificates | **Stable** | `test_certificate.py` | Versioned JSON; not formally verified |
| Minicheck re-verifier | **Stable** | `test_minicheck.py` | Python only; not formally verified |
| Classical proof-term bridge | **Experimental** | `test_classical_experimental.py` | Formula translation only; no proof translation |
| FOL proof-term fragment | **Experimental** | `test_fol.py`, `test_fol_object_debruijn.py` | No surface syntax; object-var de Bruijn incomplete |
| Property-based tests | **Optional** | `test_proof_term_properties.py` | Requires Hypothesis |
| Browser Studio (Pyodide) | **Stable** | `test_studio.py`, `test_pyodide_site.py` | CDN required; ~8 MB first load |
| Single-file HTML | **Stable** | `test_single_html.py` | CDN for Pyodide |
| Standalone executable | **Stable** | `test_packaging.py` | PyInstaller required to build |
| ML baseline | **Optional / Experimental** | `test_ml_baseline.py`, `test_ml_corpus_discipline.py` | Isolated; 40-record sample; UNTRUSTED |
| Lean 4 bridge | **Optional / Experimental** | `test_lean_bridge.py` (skip-if-unavailable) | Propositional only; requires Lean 4 |
| Metatheory (subject reduction, normalization) | **Proof sketches + tests** | `docs/metatheory.md`; `test_proof_term_properties.py` | Not machine-checked |

---

*Source repository: `paper/stele-whitepaper.tex` (LaTeX source); this Markdown version is at `docs/whitepaper.md`.*
*For build instructions, see `paper/README.md`.*
