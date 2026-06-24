# 12 — Paper Outline, Figure Plan, and GPT Writing Instructions

**Status:** Research notes (not a final paper)
**Use:** GPT-oriented guide for drafting a stronger LaTeX preprint from this packet

---

## 12.1 Target paper title variants

1. **"Stele: A Small, Auditable Proof Checker for Natural-Deduction Reasoning"**
   — emphasizes size, auditability, and proof-checking identity

2. **"Stele: A Dependency-Free Formal Verification Framework with Multi-Logic Semantics"**
   — emphasizes zero-dependency and multi-logic architecture

3. **"Stele: Rule-Relative Proof Checking with Structural Diagnostics and Semantic Layers"**
   — emphasizes the rule-relativity demonstration and multi-layer design

**Recommendation:** Title 1 or 2. Avoid "framework for" if it implies theorem proving.
Stele is a **checker**, not a **prover**.

---

## 12.2 Abstract skeleton

```
Stele is a formal proof checker for propositional natural-deduction reasoning.
Users write proof scripts in the Stele-Light surface language, and a small
trusted kernel (~400 lines, zero runtime dependencies) verifies each step by
syntactic rule-schema matching.

Stele's multi-logic architecture separates rule sets from the kernel: adding a
new logic means adding data (RuleSchema objects), not modifying the verifier.
Five built-in logics are provided: intuitionistic and classical propositional
logic, and three many-valued matrix logics (K3, LP, Boolean) for semantic
diagnostics.

The system includes [enumerate implemented experimental components]...

Stele runs unchanged in a browser via Pyodide/WebAssembly, with no backend
server. [Test count] tests run in CI on Python 3.10–3.12.
```

**Instructions:** Fill in the bracketed items from these research notes.
Do not add claims that are not in the notes. Do not say "novel" or "state-of-the-art."

---

## 12.3 Section-by-section outline

### §1 Introduction (target: 1–1.5 pages)

- Motivation: auditable, dependency-free, multi-logic proof checking
- Identity: proof checker, not theorem prover
- Key contributions list (C1–C8 from `01-system-overview.md §1.4`)
- What Stele is not (brief table)
- Paper structure sentence

### §2 The Stele-Light Language (target: 1.5–2 pages)

- Grammar (from `03-language-and-kernel.md §3.1`)
- Rule table: 12 IPL rules + 3 classical rules (from `03-language-and-kernel.md §3.4`)
- Worked example: `examples/neg_intro.stele` or `examples/or_comm.stele`
- Classical vs intuitionistic: `dne` accepted/rejected (from `RESULTS.md`)
- Gallery mention: 15 curated examples, all tested in CI

### §3 The Trusted Kernel (target: 1–1.5 pages)

- Architecture: parser → AST → kernel → PASS/FAIL + position
- Trust boundary (from `02-architecture-trust-boundary.md §2.1–2.2`)
- Rule-data separation: `RuleSchema` data in `logic.py`, zero kernel modification
- Discharge mechanism (from `03-language-and-kernel.md §3.6`)
- Import invariant: kernel ⊬ matrix (from `02-architecture-trust-boundary.md §2.4`)

### §4 Proof-Term Core and Elaboration (target: 1.5–2 pages)

- Curry–Howard correspondence table (from `04-proof-terms-and-elaboration.md §4.1`)
- Term constructors (from `04-proof-terms-and-elaboration.md §4.2`)
- Bidirectional type checking (from `04-proof-terms-and-elaboration.md §4.3`)
- Script-to-term elaboration: `crosscheck_theorem` (from `04-proof-terms-and-elaboration.md §4.8`)
- Metatheory claims table with honest status (from `04-proof-terms-and-elaboration.md §4.9`)
- FOL fragment status; classical bridge status (brief)

### §5 Diagnostics and Proof State (target: 0.5–1 page)

- Untrusted diagnostic layer (from `05-diagnostics-and-proof-state.md §5.1`)
- Four-pass structural analysis (from `05-diagnostics-and-proof-state.md §5.2`)
- 9 stable codes (from `05-diagnostics-and-proof-state.md §5.3`)
- Dependency graph (from `05-diagnostics-and-proof-state.md §5.4`)
- Proof-state hints (brief, untrusted caveat)

### §6 Semantics: ⊢ vs ⊨ (target: 1.5–2 pages)

- ⊢ vs ⊨ distinction (from `06-semantics-matrix-kripke.md §6.1`)
- K3/LP truth tables and key examples (from `06-semantics-matrix-kripke.md §6.2`)
- Rule soundness checker: LEM unsound in K3 (from `06-semantics-matrix-kripke.md §6.3`)
- Kripke countermodel search (from `06-semantics-matrix-kripke.md §6.5`)
- Bounded search limitation

### §7 Certificates and Minicheck (target: 0.5–1 page)

- Certificate emission (from `07-certificates-minicheck.md §7.2`)
- Minicheck isolation (from `07-certificates-minicheck.md §7.3`)
- Limitations: same-process, not formally verified (from `07-certificates-minicheck.md §7.4`)

### §8 Optional ML Baseline (target: 0.5–1 page)

- Architecture and isolation (from `08-ml-corpus-and-measurement.md §8.1`)
- Corpus (from `08-ml-corpus-and-measurement.md §8.2`)
- Measured metrics (from `08-ml-corpus-and-measurement.md §8.4`)
- Known limitations (from `08-ml-corpus-and-measurement.md §8.5`)

### §9 Browser-Local Deployment (target: 0.5 page)

- Pyodide/WASM architecture (from `02-architecture-trust-boundary.md §2.6`)
- Same kernel code in browser and CLI
- Caveat: CDN dependency, first-load size

### §10 Related Work (target: 1.5–2 pages)

- Proof assistants (from `10-related-work-and-provenance.md §10.1`)
- Type theory / Curry–Howard (from `10-related-work-and-provenance.md §10.2`)
- Kripke semantics (from `10-related-work-and-provenance.md §10.3`)
- Many-valued logics (from `10-related-work-and-provenance.md §10.4`)
- Proof certificates (from `10-related-work-and-provenance.md §10.6`)
- ML for theorem proving (brief, from `10-related-work-and-provenance.md §10.7`)

### §11 Limitations and Future Work (target: 0.5–1 page)

- Key limitations (from `11-limitations-and-future-work.md §11.1`)
- Key future work (from `11-limitations-and-future-work.md §11.2`)

### §12 Conclusion (target: 0.25–0.5 page)

- Restate identity
- Summarize contributions
- Note honest status of experimental components

---

## 12.4 Figure plan

### Figure 1 — Architecture / trust boundary diagram

- **Source:** `site/architecture.html` (SVG trust-boundary diagram)
- **Content:** Three-zone diagram: Trusted Zone (kernel/parser/AST/logic), Experimental/Untrusted
  Zone (diagnostics/proofstate/kripke/matrix/certs), Optional/Isolated Zone (ML/Lean)
- **Module refs:** `stele/kernel.py`, `stele/logic.py`, `stele/matrix.py`, `stele_ml/`
- **Caption draft:** "Stele's trust architecture. Zone 1 (trusted) contains the kernel,
  parser, and rule data. Zone 2 (experimental/untrusted) contains semantics, diagnostics,
  and certificates. Zone 3 (optional/isolated) contains the ML baseline and Lean bridge.
  Import invariants between zones are enforced by tests."

### Figure 2 — Stele-Light proof example

- **Source:** `examples/neg_intro.stele` or `examples/or_comm.stele`
- **Content:** Annotated proof script with rule names labeled and discharge step highlighted
- **Caption draft:** "A Stele-Light proof of ¬(P ∧ ¬P) using `neg_intro`. Each step
  carries a label; the `suppose` block introduces a temporary assumption discharged at
  line 7. The kernel verifies each step by syntactic pattern matching."

### Figure 3 — Proof dependency graph

- **Source:** `stele/proofgraph.py` applied to `examples/or_comm.stele`
- **Content:** DOT-rendered graph showing which steps depend on which
- **Caption draft:** "Proof dependency graph for `or_comm` (disjunction commutativity).
  Nodes are labeled steps; edges show direct dependencies. The `or_elim` step at h6
  depends on three prior steps."

### Figure 4 — ⊢ vs ⊨ diagram

- **Source:** `site/theory.html` (SVG ⊢ vs ⊨ diagram)
- **Content:** Split diagram: left side shows kernel syntactic check, right side shows
  matrix semantic evaluation, center shows rule-soundness connection
- **Caption draft:** "Separation of syntactic derivability (⊢) and semantic validity (⊨).
  The rule soundness checker asks whether each rule preserves designated matrix values.
  LEM (P ∨ ¬P) is classically provable (⊢) but not a K3 tautology (⊭_K3)."

### Figure 5 — Kripke countermodel for LEM

- **Source:** `stele/kripke.py` output for `P or not P`
- **Content:** Two-world Kripke frame diagram showing forcing failure for LEM
- **Caption draft:** "A Kripke countermodel for P ∨ ¬P. In this two-world frame,
  w₀ ≤ w₁ with P forced at w₁ but not w₀. At w₀, neither P nor ¬P is forced,
  so P ∨ ¬P fails. (Output from `stele/kripke.py`.)"

### Figure 6 — Certificate / minicheck flow

- **Source:** `site/architecture.html` (certificate flow SVG)
- **Content:** Flow diagram: proof script → kernel → certificate JSON → minicheck → OK/FAIL
- **Caption draft:** "Certificate emission and minicheck flow. A certificate is emitted
  only after kernel verification. The minicheck re-verifies the certificate without
  importing the kernel. Note: same-process isolation only."

### Figure 7 (optional) — ML corpus and evaluation pipeline

- **Source:** `docs/benchmark-card.md`, `stele_ml/`
- **Content:** Pipeline: corpus generator → labeled records → train/test split → Naive
  Bayes training → evaluation → baseline_report.json
- **Caption draft:** "Optional ML baseline evaluation pipeline. The corpus is synthetic
  and template-based (n=40 committed records, n=400 in-memory training). Results are
  not representative of real-world proof corpora."

### Figure 8 (optional) — Foundations / research program map

- **Source:** `site/foundations.html` (three-column status map)
- **Content:** Three-column grid: Implemented, Motivation, Future
- **Caption draft:** "Stele's relationship to the Yurihak research program. Implemented
  components (kernel, logic, matrix, Kripke) are in the left column. The Yurihak
  theoretical framework motivates the multi-logic architecture (center) but is not yet
  formalized as a Stele logic."

---

## 12.5 GPT paper-writing instructions

When drafting the paper from this packet:

### Tone and accuracy

1. **Use sober academic prose.** Do not use marketing language ("powerful," "seamlessly,"
   "cutting-edge," "state-of-the-art," "unlock").
2. **Never overclaim.** If in doubt, use the safe wording from `claim-evidence-matrix.md`.
3. **Preserve status labels.** Every claim should carry its status: Stable, Experimental,
   Optional, Demo, Untrusted, or Future. Use hedges like "experimentally," "as a demo,"
   "in an optional extension."
4. **Distinguish carefully:**
   - **Implemented and tested** → present tense, exact module path
   - **Experimental** → state the limitation
   - **Proof sketch** → "by a proof sketch" or "standard metatheory argument"
   - **Future** → "future work" or "planned"
5. **Cite test counts from a source.** Do not round or estimate. If the count in
   `RESULTS.md` (215) differs from the current pytest output (2280), use the current
   output and note the source.

### Citations

6. **Do not invent citations.** Every `\cite{}` key must be in `paper/references.bib`.
   Current defined keys: `Moura2021`, `Nipkow2002`, `Rocq`, `Norell2009`,
   `SorensenUrzyczyn2006`, `PierceT98`, `Kleene1952`, `Priest1979`,
   `TroelstraVanDalen1988`, `Pyodide`, `HarperHP1993`, `Malinowski1993`, `Yang2023`.
7. **Do not use `\cite{TODO:*}` keys.** These were removed from the whitepaper.
8. **For uncited claims** (e.g., de Bruijn indices, Gödel–Gentzen translation), use
   prose attribution: "the standard de Bruijn index technique" or cite a standard
   textbook if available.

### Module paths and evidence

9. **Use exact module paths** when making implementation claims. "as implemented in
   `stele/kernel.py`" is better than "as implemented in the kernel."
10. **Use exact test file names** when citing test evidence: "verified by
    `tests/test_kernel_valid.py`."
11. **Use exact report paths** for quantitative claims: "from
    `stele_ml/reports/baseline_report.json`."

### Stele identity

12. **Do not present Stele as a theorem prover or proof assistant.** Use: "proof checker,"
    "formal verification framework," "rule-schema-based verifier."
13. **Do not present Yurihak as implemented.** Use: "Yurihak research motivation,"
    "multi-logic architecture inspired by [...]."
14. **Do not say "formally verified"** for metatheory claims. Use: "supported by
    regression tests" or "by a proof sketch (not machine-checked)."
15. **For missing metrics:** ask for them rather than estimating. If `RESULTS.md` has a
    stale test count, grep the pytest output in the repo or note "current count not
    available in notes."

### LaTeX drafting

16. **Transform notes to LaTeX only after** the claim-evidence matrix is checked for the
    relevant section.
17. **Use the figure descriptions** in §12.4 as captions. Replace ASCII figures with
    proper LaTeX/TikZ or imported SVG.
18. **Use the section outline** in §12.3. Do not add sections not in the outline without
    checking the research notes for evidence.
19. **The metatheory table** (from `04-proof-terms-and-elaboration.md §4.9`) should be
    presented as-is: claims + honest status. Do not upgrade "proof sketch" to "proven."
