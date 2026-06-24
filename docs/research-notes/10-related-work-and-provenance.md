# 10 — Related Work and Provenance

**Status:** Stable (documentation)
**Evidence:** `docs/references.md`, `docs/provenance-map.md`, `paper/references.bib`
**Note:** Do not invent citations. All BibTeX keys below are defined in `paper/references.bib`.

---

## 10.1 Proof assistants

Stele is not a replacement for any of these systems. The comparison is for positioning.

### Lean 4 [Moura2021]

De Moura & Ullrich, "The Lean 4 Theorem Prover and Programming Language," CADE 28, 2021.

| Feature | Lean 4 | Stele |
|---------|--------|-------|
| Dependent types | Yes (CIC-like) | No |
| Tactic language | Yes (mathlib tactics) | No |
| Theorem libraries | Yes (Mathlib) | No |
| Machine-checked metatheory | Yes | No |
| Propositional proof checking | Yes | Yes (focus) |
| Zero-dependency runtime | No | Yes |
| Browser-local | Partial (Lean4Web) | Yes (Pyodide) |
| Multiple logic rule sets | No (fixed foundations) | Yes |

Stele has an **optional** Lean 4 error bridge (`stele_lean/`) that maps Lean type-error
messages to Stele diagnostic codes. This is advisory only; no formal Lean↔Stele
correspondence.

### Rocq (Coq) [Rocq]

The Rocq Proof Assistant (formerly Coq).

| Feature | Rocq | Stele |
|---------|------|-------|
| Calculus of Inductive Constructions | Yes | No |
| Tactics | Yes | No |
| Extraction to Haskell/OCaml | Yes | No |
| Stele compatibility | None (no export) | — |

Machine-checked metatheory is a future goal for Stele (export to Rocq/Lean).

### Isabelle/HOL [Nipkow2002]

Nipkow, Paulson & Wenzel, "Isabelle/HOL: A Proof Assistant for Higher-Order Logic," 2002.

Natural-deduction style (Isar proof language) is similar in spirit to Stele-Light.
Isabelle is much larger; Stele is smaller and does not implement HOL.

### Agda [Norell2009]

Norell, "Towards a Practical Programming Language Based on Dependent Type Theory," 2007/2009.

Curry–Howard core is similar in spirit; Stele lacks dependent types and pattern matching.

---

## 10.2 Type theory and proof terms

### Curry–Howard correspondence [SorensenUrzyczyn2006]

Sørensen & Urzyczyn, *Lectures on the Curry–Howard Isomorphism*, Elsevier 2006.

The foundational reference for the `stele/core/` proof-term calculus. Stele implements
the IPL fragment of the Curry–Howard correspondence. Classical rules are excluded from
the elaboration path; λμ-calculus is not implemented.

### Bidirectional type checking [PierceT98]

Pierce & Turner, "Local Type Inference," POPL 1998.

The bidirectional (infer/check) architecture of `stele/core/typing.py` follows the
standard bidirectional type-checking pattern. Stele's version is a simple specialization
for STLC without polymorphism.

---

## 10.3 Kripke semantics

### Troelstra & van Dalen [TroelstraVanDalen1988]

Troelstra & van Dalen, *Constructivism in Mathematics*, vol. 1, North-Holland 1988.

The forcing semantics for intuitionistic propositional logic in `stele/kripke.py`
follows the standard Kripke/Beth semantics for IPL as described in this reference.
The bounded countermodel search is a finite-frame specialization.

---

## 10.4 Many-valued logics

### K3 — Kleene [Kleene1952]

Kleene, *Introduction to Metamathematics*, North-Holland 1952.

The strong Kleene three-valued logic in `stele/matrix.py`. Truth tables are locked by
`test_k3_imp_table_matches_manifesto` to match the Kleene conventions.

### LP — Priest [Priest1979]

Priest, "The Logic of Paradox," *Journal of Philosophical Logic* 8(1), 1979.

The Logic of Paradox (paraconsistent, designated set {T, I}) in `stele/matrix.py`.

### Many-valued logic survey [Malinowski1993]

Malinowski, *Many-Valued Logics*, Oxford Logic Guides 25, 1993.

Matrix semantics as a general framework for many-valued logics. The `rule_soundness()`
checker in `stele/matrix.py` implements matrix-based soundness checking.

---

## 10.5 Classical negative translation

The Gödel–Gentzen double-negation translation in `stele/core/classical_experimental.py`:

**Gödel (1933), Gentzen (1936):** No BibTeX entry yet; standard metatheory result.
The translation: if $\text{CPC} \vdash \phi$ then $\text{IPC} \vdash \phi^N$.

Implementation: formula-level only. Proof-term generation for translated formulas is
not implemented. λμ-calculus / continuation semantics for classical proofs is not
implemented.

---

## 10.6 Proof certificates (LF tradition)

### Harper, Honsell & Plotkin [HarperHP1993]

Harper, Honsell & Plotkin, "A Framework for Defining Logics," JACM 40(1):143–184, 1993.

The idea of emitting independently verifiable proof certificates is well-established
in the proof-assistant literature. LF (the Edinburgh Logical Framework) is the canonical
reference for this tradition.

Stele's certificate format is a lightweight JSON encoding; the minicheck re-checker is
a small independent software check (not language-level isolation).

---

## 10.7 ML for theorem proving

### LeanDojo [Yang2023]

Yang et al., "LeanDojo: Theorem Proving with Retrieval-Augmented Language Models,"
NeurIPS 2023.

Several systems apply machine learning to guide tactic selection or proof generation
in full proof assistants. Stele's ML baseline is a proof **classification** model
(valid/invalid + diagnostic codes), not a proof-generation system. It is explicitly
Untrusted, Optional, and evaluated only on a small synthetic corpus.

**Stele's ML baseline is not comparable to LeanDojo or similar systems.**
The positioning question (is classification feasible?) motivated including the baseline;
the answer from the small corpus is not general.

---

## 10.8 Provenance table

See `docs/provenance-map.md Table 4` for the complete citation-status table with all 13
current BibTeX entries and 4 planned future entries (Kim papers, metadata TBD).
