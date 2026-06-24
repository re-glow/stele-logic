# Stele — Annotated References

This document separates the ideas that are **implemented in Stele code** from those that are
**theoretical background**, **related systems**, **personal foundational motivation**, and
**future work**.

It is a companion to [`docs/provenance-map.md`](provenance-map.md),
which gives the structured tables.

---

## Purpose

External reviewers, collaborators, and future maintainers should be able to answer:

1. *Which algorithms are actually running in the code?*
2. *Which papers inspired design decisions without being implemented?*
3. *Which systems is Stele related to, and how?*
4. *Which foundational motivation (Yurihak / 유리학) is Stele built around, without yet implementing it as a logic?*
5. *What does Stele explicitly not claim?*

---

## 1. Implemented algorithmic foundations

Each entry below describes something actually implemented in Stele today.
Evidence links point to the module and tests, not to theoretical promises.

---

### 1.1 Natural deduction / proof checking

**What is implemented:**  
The Stele-Light proof language is a natural-deduction surface syntax with explicit
`assume`, `suppose`, `have`, and `conclude` steps. The trusted kernel
(`stele/kernel.py`) checks each step by pure syntactic pattern-matching against rule
schemas — no semantic reasoning. 12 intuitionistic rules + 3 classical rules.

**Module:** `stele/kernel.py`, `stele/logic.py`  
**Status:** Stable  
**Evidence:** `tests/test_kernel_valid.py`, `tests/test_kernel_invalid.py`, `examples/`  
**Reference:** Standard natural deduction. See, e.g., Troelstra & Schwichtenberg,
*Basic Proof Theory* (2000). The Gentzen calculus NJ is the direct inspiration.  
**Limitation:** Propositional fragment only. No FOL quantifiers in the surface language.

---

### 1.2 Bidirectional type checking

**What is implemented:**  
`stele/core/typing.py` implements bidirectional type checking for the proof-term
calculus: *check mode* (given a type, verify the term) and *infer mode* (derive the
type from the term). All term constructors are frozen dataclasses.

**Module:** `stele/core/typing.py`  
**Status:** Experimental  
**Evidence:** `tests/test_proof_term_typing.py`  
**Reference:** Pierce & Turner, "Local Type Inference", POPL 1998 [PierceT98].
The bidirectional pattern is standard; Stele's version is a simple specialization.  
**Limitation:** Simply-typed; no polymorphism, no dependent types.

---

### 1.3 Proof terms / Curry–Howard correspondence

**What is implemented:**  
`stele/core/` provides a Curry–Howard witness extractor for intuitionistic propositional
logic proofs. Term constructors: `TVar`, `Lam`, `App`, `Pair`, `Fst`, `Snd`, `Inl`,
`Inr`, `Case`, `Abort`. `stele/elaborate.py` converts a verified proof script to a
proof term.

**Module:** `stele/core/terms.py`, `stele/elaborate.py`  
**Status:** Experimental  
**Evidence:** `tests/test_elaborate.py`, `tests/test_proof_term_typing.py`  
**Reference:** Sørensen & Urzyczyn, *Lectures on the Curry–Howard Isomorphism*,
Elsevier 2006 [SorensenUrzyczyn2006].  
**Limitation:** IPL only. Classical rules (`dne`, `lem`, `pbc`) are excluded from the
elaboration path. No dependent types, no universe levels.

---

### 1.4 de Bruijn indices / substitution

**What is implemented:**  
`stele/core/debruijn.py` provides conversion between named and de Bruijn representations
for proof-variable binders. Substitution is index-shifting. Object-level FOL variables
remain named (partial de Bruijn support at the object level).

**Module:** `stele/core/debruijn.py`  
**Status:** Experimental  
**Evidence:** `tests/test_debruijn.py`  
**Reference:** de Bruijn, "Lambda Calculus Notation with Nameless Dummies", 1972.
Standard technique; no direct citation in the BibTeX yet.  
**Limitation:** Object-level variable de Bruijn conversion only partially implemented.

---

### 1.5 β-reduction / normalization

**What is implemented:**  
`stele/core/reduce.py` implements call-by-name β-reduction with a fuel counter (default
1000 steps). η-reduction is not implemented. `normalize()` reduces a closed proof term.

**Module:** `stele/core/reduce.py`  
**Status:** Experimental  
**Evidence:** `tests/test_reduce.py`, optional property-based tests (Hypothesis)  
**Reference:** Standard λ-calculus reduction. Normalization for STLC (simply-typed lambda
calculus) is a standard metatheorem; fuel guard provides a practical bound.  
**Limitation:** Call-by-name only. No β-η. Normalization not machine-checked.

---

### 1.6 Kripke semantics for intuitionistic propositional logic

**What is implemented:**  
`stele/kripke.py` performs bounded finite-frame Kripke countermodel search for IPL.
Enumerates frames up to `max_worlds` (default 3–4), checks the forcing condition at
each world, and returns the first countermodel found or `None`.

**Module:** `stele/kripke.py`  
**Status:** Experimental  
**Evidence:** `tests/test_kripke.py`, `tests/test_kripke_integration.py`  
**Reference:** Troelstra & van Dalen, *Constructivism in Mathematics*, vol. 1,
North-Holland 1988 [TroelstraVanDalen1988]. Standard Kripke semantics for IPL.  
**Limitation:** Bounded (finite frame enumeration). No-countermodel ≠ proof of validity.
Propositional only. Not complete.

---

### 1.7 Many-valued matrix semantics

#### K3 (strong Kleene)

**What is implemented:**  
Three-valued matrix with values {T, I, F}, designated set {T}.
Conventions: I→F = I, F→I = T. `rule_soundness()` checks whether each rule preserves
designated values.

**Module:** `stele/matrix.py`  
**Status:** Demo / Diagnostic  
**Evidence:** `tests/test_matrix.py`, `test_k3_imp_table_matches_manifesto`  
**Reference:** Kleene, *Introduction to Metamathematics*, North-Holland 1952
[Kleene1952].  
**Limitation:** Diagnostic tool; not a full K3 proof system.

#### LP (Logic of Paradox)

**What is implemented:**  
Three-valued matrix with values {T, I, F}, designated set {T, I}. Same truth tables as
K3 but a different designated set.

**Module:** `stele/matrix.py`  
**Status:** Demo / Diagnostic  
**Evidence:** `tests/test_matrix.py`  
**Reference:** Priest, "The Logic of Paradox", *Journal of Philosophical Logic* 8:1,
1979 [Priest1979].  
**Limitation:** Diagnostic only. Not a full paraconsistent proof system.

#### Boolean (classical)

**What is implemented:**  
Two-valued matrix {T, F} with standard classical tables. Baseline for soundness checks.

**Module:** `stele/matrix.py`  
**Status:** Stable  
**Evidence:** `tests/test_matrix.py`  
**Reference:** Standard classical propositional logic.

---

### 1.8 Classical negative translation bridge

**What is implemented:**  
`stele/core/classical_experimental.py` implements the Gödel–Gentzen double-negation
translation at the formula level. Converts a classical formula to an intuitionistic
formula such that provability is preserved. API: `goedel_gentzen(formula)`.

**Module:** `stele/core/classical_experimental.py`  
**Status:** Experimental  
**Evidence:** `tests/test_classical_experimental.py`  
**Reference:** Gödel (1933), Gentzen (1936). Standard metatheory result: if CPC ⊢ φ
then IPC ⊢ φᴺ where φᴺ is the double-negation translation.  
**Limitation:** Formula-level translation only. Does not automatically produce a proof
term for the translated formula. λμ-calculus / continuation typing not implemented.

---

### 1.9 Proof certificates and independent minicheck

**What is implemented:**  
`stele/certificate.py` emits a versioned JSON certificate after kernel verification.
`stele/minicheck.py` re-verifies the certificate without importing `stele.kernel` or
`stele.parser` — code-level isolation.

**Module:** `stele/certificate.py`, `stele/minicheck.py`  
**Status:** Experimental  
**Evidence:** `tests/test_minicheck.py` (tamper-detection, cross-validation)  
**Reference:** The idea of independently verifiable proof certificates is standard in
the proof-assistant literature. See, e.g., Harper, Honsell & Plotkin, "A Framework for
Defining Logics", *JACM* 40(1), 1993 [HarperHP1993] for the LF tradition.  
**Limitation:** Same-process isolation only (Python). Not process-level or language-level
isolation. Not formally verified.

---

### 1.10 Structural diagnostics

**What is implemented:**  
`stele/diagnostics.py` performs four-pass structural analysis:
pass 1 (definition scope), pass 2 (reference scope), pass 3 (dependency graph),
pass 4 (kernel classification). Nine stable codes.

**Module:** `stele/diagnostics.py`  
**Status:** Untrusted / Stable codes  
**Evidence:** `tests/test_diagnostics.py`  
**Reference:** No specific paper; pattern is similar to type-error diagnosis in compiler
literature. Design is original to Stele.  
**Limitation:** Advisory only. Not kernel-trusted. Not exhaustive.

---

### 1.11 Optional ML baseline

**What is implemented:**  
`stele_ml/` provides a Multinomial Naive Bayes classifier (Laplace smoothing α=1.0,
bag-of-words features). Trained on a 400-example synthetic corpus; evaluated on 40
examples. Completely outside the trusted path.

**Module:** `stele_ml/`  
**Status:** Optional  
**Evidence:** `tests/test_ml_corpus_discipline.py`, `docs/benchmark-card.md`  
**Reference:** Naive Bayes is a standard baseline classifier. The ML-for-theorem-proving
literature (e.g., Yang et al., LeanDojo, NeurIPS 2023 [Yang2023]) motivates the
positioning question, but Stele's baseline is not competitive with those systems.  
**Limitation:** Tiny synthetic corpus. Not a real proof classifier. Metrics must not be
cited as general accuracy claims.

---

### 1.12 Lean 4 type-error bridge

**What is implemented:**  
`stele_lean/` parses Lean 4 error output and maps type-mismatch patterns to Stele
diagnostic codes. One-way advisory bridge. No proof generation or round-trip.

**Module:** `stele_lean/`  
**Status:** Optional / Experimental  
**Evidence:** `tests/test_lean_bridge.py` (if present)  
**Reference:** Moura & Ullrich, "The Lean 4 Theorem Prover and Programming Language",
CADE 28, 2021 [Moura2021].  
**Limitation:** Error-message parsing only. No formal Lean-Stele correspondence.

---

## 2. Related systems

These are full proof assistants / interactive theorem provers.
Stele is **not** a replacement for any of them.

| System | Citation | What it does | Stele's relationship |
|--------|----------|-------------|----------------------|
| Lean 4 | [Moura2021] | Full ITP with dependent types, tactics, ML integration | Stele's optional Lean bridge maps error codes; Stele is not Lean-compatible |
| Rocq (Coq) | [Rocq] | Full ITP with CIC, tactics, Coq libraries | Stele has no Rocq export; machine-checked metatheory is a future goal |
| Isabelle/HOL | [Nipkow2002] | Higher-order logic ITP with Isar proof language | Natural-deduction style is similar; Stele is much smaller and not HOL |
| Agda | [Norell2009] | Dependently-typed programming language / proof assistant | Curry–Howard core is similar in spirit; Stele lacks dependent types |

**Positioning statement (see also whitepaper §2):**
Stele is designed for settings where a small, auditable, dependency-free checker is
more appropriate than a full proof assistant — such as formal reasoning courses,
proof-checking experiments, or browser-local exploration.

---

## 3. Personal / foundational research line

These papers form the theoretical motivation for the Yurihak (유리학) research program
that underlies Stele's multi-logic architecture. They are **background and motivation**,
not currently implemented as Stele logics.

PDFs are local drafting references; they are not bundled in the public repository.
Summaries below are based on filenames and author description only, as PDF extraction
was unavailable in this session. Full summaries will be added when excerpts/metadata are
ready to publish.

---

### 유리학개론 / Introduction to Yurihak

- **File:** `references/incoming/yurihak-introduction.pdf` (local; not committed)
- **Citation key:** `KimYurihak` (TODO: add to BibTeX when metadata confirmed)
- **Summary:** TODO — source not extracted. Primary theoretical motivation for Stele's
  multiple-logic architecture and rule-relativity framework.
- **Connection to Stele:** Research motivation for the `--logic` flag and `RuleSchema`
  data architecture. Not implemented as a formal Stele logic.
- **Not claimed:** Stele does not implement Yurihak as a logic. Stele does not prove
  mathematical relativism.

---

### Window-Localized

- **File:** `references/incoming/window-localized.pdf` (local; not committed)
- **Citation key:** `KimWindowLocalized` (TODO: add to BibTeX when metadata confirmed)
- **Summary:** TODO — source not extracted. Potentially concerns window-local or
  frame-relative truth frameworks.
- **Connection to Stele:** Conceptual influence on world-based semantics and Kripke
  frame-relative evaluation. No window-localized semantics implemented.
- **Not claimed:** Window-localized structures are not implemented in Stele.

---

### Closure Atlases

- **File:** `references/incoming/closure-atlases.pdf` (local; not committed)
- **Citation key:** `KimClosureAtlases` (TODO: add to BibTeX when metadata confirmed)
- **Summary:** TODO — source not extracted.
- **Connection to Stele:** Potentially related to world-lattice composition. Not
  formalized in Stele.
- **Not claimed:** Closure atlas structures are not implemented in Stele.

---

### Bounded Cores

- **File:** `references/incoming/bounded-cores.pdf` (local; not committed)
- **Citation key:** `KimBoundedCores` (TODO: add to BibTeX when metadata confirmed)
- **Summary:** TODO — source not extracted. Potentially concerns tractable
  bounded-fragment theory.
- **Connection to Stele:** Conceptual parallel with bounded Kripke frame search.
  Not implemented as a Stele semantic layer.
- **Not claimed:** Bounded core theory is not implemented in Stele.

---

## 4. Future / not yet implemented

These items may guide future work. None are currently implemented.

| Idea | Notes | Related implemented work |
|------|-------|--------------------------|
| Rust/OCaml minicheck port | Process-level isolation for stronger cert guarantee | `stele/minicheck.py` (Python) |
| Full Lean round-trip | Stele proofs exported to Lean for machine-checked metatheory | `stele_lean/` (error bridge only) |
| Equality / function-symbol FOL | Full first-order logic in the surface language | `stele/core/fol.py` (proof-term level only) |
| λμ-calculus / continuation typing | Classical proof terms via control operators | `stele/core/classical_experimental.py` (translation only) |
| Full Yurihak logic | Yurihak as a formal Stele rule set | None yet |
| Structural rule policy | Explicit weakening/contraction/exchange declarations | None yet |
| Machine-checked metatheory | Lean/Coq/Agda export of proof-term metatheory claims | None yet |
| Larger ML corpus | Real user proofs, not synthetic | `stele_ml/` (40-example synthetic only) |

---

## 5. What Stele does not claim

- Stele is **not a theorem prover**. It does not search for proofs.
- Stele is **not a Lean / Rocq / Isabelle replacement**. It is much smaller and lacks
  dependent types, tactics, higher-order unification, and theorem libraries.
- Stele is **not a full proof assistant**. There is no tactic language, no module system,
  no universe hierarchy.
- Stele is **not a full first-order logic system**. The proof-script surface is
  propositional.
- Stele does **not prove mathematical relativism**. It demonstrates that the same formula
  can be valid under one rule set and invalid under another. That is a technical fact
  about the rule sets, not a philosophical proof.
- Stele does **not implement Yurihak** as a formal logic. Yurihak is research motivation
  and a future formalization program.
- Stele's metatheory is **not formally verified**. Claims about subject reduction,
  normalization, and consistency are supported by regression tests and proof sketches —
  not by machine-checked proofs.
- The ML baseline is **not production ML**. It is a 40-example synthetic-corpus
  diagnostic tool. Its metrics must not be cited as general accuracy claims.
- Stele is **not a state-of-the-art theorem-proving benchmark** system. The evaluation
  is internal and not comparable to TPTP, Lean Mathlib benchmarks, or miniF2F.
