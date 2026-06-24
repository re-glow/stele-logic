# Stele — Provenance Map

Structured tables mapping every public claim or feature to its implementation evidence,
source reference, and explicit limitation.

Companion documents:
- [`docs/references.md`](references.md) — annotated prose references
- [`docs/foundations-program.md`](foundations-program.md) — Yurihak research program
- [`site/foundations.html`](../site/foundations.html) — public foundations page
- [`paper/references.bib`](../paper/references.bib) — BibTeX bibliography

---

## Table 1: Claim → Implementation → Source

| Claim / feature | Public status | Stele module(s) | Tests / evidence | Source / reference | Limitation |
|----------------|--------------|----------------|------------------|--------------------|------------|
| Rule-checked natural-deduction proof checker | Stable | `stele/kernel.py`, `stele/logic.py` | `test_kernel_valid.py`, `test_kernel_invalid.py` | Standard NJ natural deduction | Propositional surface only |
| Intuitionistic rule set (12 rules) | Stable | `stele/logic.py` | `test_kernel_valid.py` | Gentzen NJ; Troelstra & Schwichtenberg | Propositional only |
| Classical rule set (+3: dne, lem, pbc) | Stable | `stele/logic.py` | `test_kernel_valid.py`, `test_kernel_invalid.py` | Standard classical propositional logic | Propositional only |
| K3 matrix semantics (diagnostic) | Demo | `stele/matrix.py` | `test_matrix.py`, `test_k3_imp_table_matches_manifesto` | Kleene 1952 [Kleene1952] | Diagnostic only; not a K3 proof system |
| LP matrix semantics (diagnostic) | Demo | `stele/matrix.py` | `test_matrix.py` | Priest 1979 [Priest1979] | Diagnostic only; not a full paraconsistent system |
| Boolean matrix semantics | Demo | `stele/matrix.py` | `test_matrix.py` | Standard classical logic | Diagnostic only |
| Kripke countermodel search | Experimental | `stele/kripke.py` | `test_kripke.py`, `test_kripke_integration.py` | Troelstra & van Dalen 1988 [TroelstraVanDalen1988] | Bounded; no-countermodel ≠ validity |
| Proof-term calculus (IPL Curry–Howard) | Experimental | `stele/core/terms.py`, `stele/elaborate.py` | `test_elaborate.py`, `test_proof_term_typing.py` | Sørensen & Urzyczyn 2006 [SorensenUrzyczyn2006] | IPL only; no classical terms |
| Bidirectional type checking | Experimental | `stele/core/typing.py` | `test_proof_term_typing.py` | Pierce & Turner 1998 [PierceT98] | Simply-typed only |
| de Bruijn indices | Experimental | `stele/core/debruijn.py` | `test_debruijn.py` | de Bruijn 1972 (standard technique) | Object-level partial |
| β-reduction / normalization | Experimental | `stele/core/reduce.py` | `test_reduce.py` | Standard STLC; fuel guard in code | Not machine-checked |
| FOL proof-term fragment (∀, ∃) | Experimental | `stele/core/fol.py` | `test_fol.py` | Standard dependent-type correspondence | No surface language support yet |
| Classical negative translation | Experimental | `stele/core/classical_experimental.py` | `test_classical_experimental.py` | Gödel 1933, Gentzen 1936 | Formula-level only; no term generation |
| Proof certificates (JSON) | Experimental | `stele/certificate.py` | `test_minicheck.py` | LF tradition [HarperHP1993] | JSON encoding only |
| Independent minicheck | Experimental | `stele/minicheck.py` | `test_minicheck.py` (tamper-detection) | Independent-checker principle | Same Python process; not language-isolated |
| Structural diagnostics (9 codes) | Untrusted / Stable codes | `stele/diagnostics.py` | `test_diagnostics.py` | Original design | Advisory only; not kernel-trusted |
| Proof-state hints | Untrusted | `stele/proofstate.py` | `test_proofstate.py` | Structural pattern matching | `trusted=False` always |
| Browser-local Studio (Pyodide) | Stable | `site/studio.html`, `stele/browser.py` | `test_pyodide_site.py` | Pyodide [Pyodide] | ~8 MB first-load; CDN dependency |
| ML baseline classifier | Optional | `stele_ml/` | `test_ml_corpus_discipline.py` | Naive Bayes; LeanDojo positioning [Yang2023] | 40-example synthetic corpus only |
| Lean 4 error bridge | Optional | `stele_lean/` | Tests in stele_lean/ | Lean 4 [Moura2021] | Error-message parsing only |
| Yurihak research program | Motivation | — | `site/foundations.html` | Kim, *유리학개론* (local) | Not implemented as a Stele logic |
| Window-localized semantics | Future | — | — | Kim, *Window-Localized* (local) | Not implemented |
| Closure atlas structures | Future | — | — | Kim, *Closure Atlases* (local) | Not implemented |
| Bounded core theory | Future | — | — | Kim, *Bounded Cores* (local) | Not implemented |

---

## Table 2: Inspiration vs Implementation

| Idea | Implemented in Stele? | If yes, where | If no, how is it used | Risk if overclaimed |
|------|----------------------|---------------|----------------------|---------------------|
| Natural deduction | Yes | `kernel.py`, `logic.py` | — | — |
| Curry–Howard correspondence | Partially (IPL only) | `stele/core/` | Classical case motivates future λμ work | Claiming "full Curry–Howard" would miss classical limitation |
| Gödel–Gentzen translation | Partially (formula only) | `core/classical_experimental.py` | Cannot auto-produce translated proof terms | Claiming "classical proof terms" is wrong |
| Kripke frame semantics | Yes (bounded search) | `stele/kripke.py` | — | Claiming completeness would be wrong |
| K3 / LP many-valued logics | As diagnostics | `stele/matrix.py` | Not full proof systems | Claiming "K3 proof assistant" overstates |
| Yurihak logical framework | No | — | Research motivation for multi-logic architecture | "Stele implements Yurihak" is false |
| Window-localized truth | No | — | Conceptual influence on world semantics | "Window semantics implemented" is false |
| Closure atlas | No | — | Conceptual influence on world-lattice composition | "Closure atlas implemented" is false |
| Bounded core | No | — | Parallel with bounded Kripke search | "Bounded core implemented" is false |
| Machine-checked metatheory | No | — | Regression tests are evidence, not proofs | "Formally verified" is false |
| Full FOL | No (proof-term level only) | `stele/core/fol.py` | Surface language is propositional | "FOL proof checker" overstates |
| Proof certificates (LF tradition) | Partial | `certificate.py`, `minicheck.py` | Lightweight JSON; not full LF | "Formally independent" overstates |

---

## Table 3: Module Provenance

| Module | Role | Trusted? | Main theoretical dependency | Tests | Related docs |
|--------|------|----------|-----------------------------|-------|-------------|
| `stele/kernel.py` | Proof step verifier — the sole trusted core | **Yes** | NJ natural deduction, syntactic matching | `test_kernel_valid.py`, `test_kernel_invalid.py` | `docs/semantics.md`, whitepaper §3 |
| `stele/logic.py` | Rule schema data — 5 built-in logic objects | **Yes** (data) | NJ rules; Kleene/Priest conventions | `test_logic.py` | `docs/semantics.md`, GUIDE.md |
| `stele/parser.py` | Recursive-descent tokenizer + parser | **Yes** | BNF in `docs/semantics.md` | `tests/test_parser.py` | `docs/semantics.md` |
| `stele/ast.py` | Formula AST (Var, Op) | **Yes** (data) | Standard AST design | `tests/test_ast.py` | `docs/semantics.md` |
| `stele/proof.py` | Proof node types (frozen dataclasses) | **Yes** (data) | — | — | — |
| `stele/matrix.py` | Many-valued matrix semantics | No (diagnostic) | Kleene 1952, Priest 1979 | `test_matrix.py` | `docs/semantics.md` §3 |
| `stele/world.py` | World/lattice demo | No (diagnostic) | Conceptual | `test_world.py` | — |
| `stele/kripke.py` | Kripke countermodel search | No (experimental) | Troelstra & van Dalen 1988 | `test_kripke.py` | `docs/metatheory.md` |
| `stele/core/typing.py` | Bidirectional type checker | No (experimental) | Pierce & Turner 1998 | `test_proof_term_typing.py` | `docs/proof-terms.md` |
| `stele/core/reduce.py` | β-reduction + normalization | No (experimental) | Standard STLC | `test_reduce.py` | `docs/proof-terms.md` |
| `stele/core/debruijn.py` | de Bruijn index layer | No (experimental) | de Bruijn 1972 | `test_debruijn.py` | `docs/proof-terms.md` |
| `stele/core/fol.py` | FOL proof-term fragment | No (experimental) | Standard ∀/∃ types | `test_fol.py` | `docs/proof-terms.md` |
| `stele/core/classical_experimental.py` | Gödel–Gentzen bridge | No (experimental) | Gödel 1933, Gentzen 1936 | `test_classical_experimental.py` | `docs/metatheory.md` |
| `stele/certificate.py` | Proof certificate emission | No (experimental) | LF tradition | `test_minicheck.py` | `docs/metatheory.md` |
| `stele/minicheck.py` | Independent certificate re-checker | No (experimental) | Independent-checker principle | `test_minicheck.py` | `docs/metatheory.md` |
| `stele/diagnostics.py` | Structural proof analysis | No (untrusted) | Original design | `test_diagnostics.py` | `docs/failure-modes.md` |
| `stele/proofstate.py` | Proof-state hints | No (untrusted) | Pattern matching | `test_proofstate.py` | — |
| `stele/browser.py` | Pyodide JSON bridge | No (UI) | — | `test_pyodide_site.py` | — |
| `stele_ml/` | ML baseline classifier | No (optional/isolated) | Naive Bayes | `test_ml_corpus_discipline.py` | `docs/benchmark-card.md` |
| `stele_lean/` | Lean 4 error bridge | No (optional/isolated) | Lean 4 error format | Tests in stele_lean/ | — |

---

## Table 4: Citation status

| Citation key | Complete metadata? | Used in whitepaper? | Used in site/docs? | Needs verification? |
|-------------|-------------------|--------------------|--------------------|---------------------|
| `Moura2021` | Yes | Yes (§1, §7, §8) | Yes (foundations.html, theory.html) | No |
| `Nipkow2002` | Yes | Yes (§1, §8) | Yes (theory.html) | No |
| `Rocq` | Yes (URL-based) | Yes (§1, §8) | Yes (theory.html) | No |
| `Norell2009` | Yes | Yes (§8) | Yes (theory.html) | No |
| `SorensenUrzyczyn2006` | Yes | Yes (§5, §8) | Yes (theory.html) | No |
| `PierceT98` | Yes | Yes (§5, §8) | Yes | No |
| `Kleene1952` | Yes | Yes (§6) | Yes | No |
| `Priest1979` | Yes | Yes (§6, §8) | Yes | No |
| `TroelstraVanDalen1988` | Yes | Yes (§6, §8) | Yes | No |
| `Pyodide` | Yes (URL-based) | Yes (§9) | Yes | No |
| `HarperHP1993` | Yes | Yes (§8) | Yes (references.md) | No |
| `Malinowski1993` | Yes | Yes (§8) | Yes (references.md) | No |
| `Yang2023` | Yes | Yes (§10) | Yes (references.md) | No |
| `KimYurihak` | **No — TODO** | No | Yes (foundations.html) | Yes — awaiting PDF metadata |
| `KimWindowLocalized` | **No — TODO** | No | Yes (foundations.html) | Yes — awaiting PDF metadata |
| `KimClosureAtlases` | **No — TODO** | No | Yes (foundations.html) | Yes — awaiting PDF metadata |
| `KimBoundedCores` | **No — TODO** | No | Yes (foundations.html) | Yes — awaiting PDF metadata |

---

## What Stele does not claim

A summary — see `docs/references.md §5` for the full list.

- Not a theorem prover
- Not a Lean / Rocq / Isabelle replacement
- Not a full proof assistant
- Not a full first-order logic system
- Not a proof of mathematical relativism
- Not a formalized Yurihak implementation
- Not formally verified metatheory
- Not production ML
- Not a state-of-the-art theorem-proving benchmark
