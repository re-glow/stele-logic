# Foundations Research Program — Companion Document

This document tracks source materials, claim boundaries, and connections between
Stele's implemented features and the broader Yurihak foundational research program.

**Status:** In progress — source PDFs not yet extracted (see §3 below).
**Public page:** `site/foundations.html`
**Provenance map:** `docs/provenance-map.md`
**Annotated references:** `docs/references.md`
**Last updated:** 2026-06-24

---

## §1. Source file inventory

| Filename | Repo status | Content status |
|----------|-------------|----------------|
| `yurihak-introduction.pdf` | Not committed (local drafting reference) | Pending extraction / publication |
| `window-localized.pdf` | Not committed (local drafting reference) | Pending extraction / publication |
| `closure-atlases.pdf` | Not committed (local drafting reference) | Pending extraction / publication |
| `bounded-cores.pdf` | Not committed (local drafting reference) | Pending extraction / publication |

**Note:** These PDFs are local drafting references and are **not bundled in the public
repository** (`references/` is gitignored by default).
The filenames are recorded here for provenance planning only.
When excerpts or metadata are ready to publish, update §2 and the public page accordingly.

---

## §2. Paper summaries

### 유리학개론 / Introduction to Yurihak
- **File:** `references/incoming/yurihak-introduction.pdf`
- **Content:** TODO — not yet extracted
- **Inferred scope (filename only):** Introduction to the Yurihak (유리학) philosophical
  and logical framework developed by Jaehwan Kim.
- **Connection to Stele:** Primary theoretical motivation for the multiple-logic
  architecture and the separation of syntactic derivability from semantic validity.
- **What is not implemented:** Yurihak as a formal logic system in Stele.
- **Action item:** Extract and summarize when PDF tool available. Identify specific
  formal definitions that could become `RuleSchema` candidates.

### Window-Localized
- **File:** `references/incoming/window-localized.pdf`
- **Content:** TODO — not yet extracted
- **Inferred scope (filename only):** Some work on window-localized or frame-local
  truth/semantics frameworks.
- **Connection to Stele:** Potentially related to world-based semantics (`stele/world.py`),
  Kripke frame-relative forcing, and the `lattice_status` API.
- **What is not implemented:** Window-localized semantics in Stele.
- **Action item:** Extract, summarize, and identify whether frame-locality maps
  to Kripke accessibility or to a distinct semantic structure.

### Closure Atlases
- **File:** `references/incoming/closure-atlases.pdf`
- **Content:** TODO — not yet extracted
- **Inferred scope (filename only):** Construction of "closure atlases" — possibly
  systems of closure operators on logical or topological structures.
- **Connection to Stele:** Potentially related to how multiple semantic interpretations
  (worlds, matrices) can be organized into a coherent collection. Closure conditions
  may relate to structural rules (contraction, weakening, exchange).
- **What is not implemented:** Closure atlas structures in Stele.
- **Action item:** Extract, summarize, and assess whether a closure-atlas perspective
  on Stele's world lattice is formally expressible.

### Bounded Cores
- **File:** `references/incoming/bounded-cores.pdf`
- **Content:** TODO — not yet extracted
- **Inferred scope (filename only):** Theory of "bounded cores" in logical or mathematical
  structures — possibly tractable fragments, bounded complexity, or minimal core systems.
- **Connection to Stele:** Potentially related to the bounded Kripke frame search
  (`stele/kripke.py`), which operates within a finite bound for tractability, and to
  the propositional fragment as a bounded-complexity subset of full FOL.
- **What is not implemented:** Bounded core theory as a Stele semantic layer.
- **Action item:** Extract, summarize, and check whether "bounded core" is a
  complexity-theoretic notion or a structural one, to determine the appropriate
  Stele connection.

---

## §3. PDF extraction limitation

The `Read` tool used in this session requires `pdftoppm` to extract PDF content.
This tool is not available in the current environment (`pdftoppm: command not found`).

**Impact:** All four source PDFs remain unread. The foundations page (`site/foundations.html`)
and this companion document contain only filename-derived titles and structural scaffolding.
Paper-specific content is marked TODO.

**Resolution:** When PDF extraction becomes available:
1. Read each paper (first 5–10 pages minimum)
2. Write accurate 2–3 paragraph summaries
3. Update the paper cards in `site/foundations.html`
4. Update §2 of this document
5. Update the claim/evidence table in `site/foundations.html`
6. Run `python -m pytest -q` to ensure no tests break

---

## §4. Implemented vs future mapping

| Concept | Implemented in Stele | Status |
|---------|----------------------|--------|
| Multiple proof rule sets | `stele/logic.py` — 5 built-in logics | Stable |
| Syntactic proof checking | `stele/kernel.py` | Stable |
| K3 three-valued matrix | `stele/matrix.py` | Demo |
| LP Logic of Paradox matrix | `stele/matrix.py` | Demo |
| World lattice | `stele/world.py` | Demo |
| Bounded Kripke countermodels | `stele/kripke.py` | Experimental |
| Proof-term calculus (IPL) | `stele/core/` | Experimental |
| Certificates + minicheck | `stele/certificate.py`, `stele/minicheck.py` | Experimental |
| Proof-state hints | `stele/proofstate.py` | Untrusted |
| Browser Studio | `site/studio.html` + Pyodide | Stable |
| **Yurihak logic** | **Not implemented** | **Motivation / Future** |
| **Window-localized semantics** | **Not implemented** | **Motivation / Future** |
| **Closure atlas structures** | **Not implemented** | **Motivation / Future** |
| **Bounded core theory** | **Not implemented** | **Motivation / Future** |
| **FOL surface syntax** | Not implemented (proof-term layer only) | Roadmap |
| **Machine-checked metatheory** | Not implemented (regression tests only) | Future |

---

## §5. Claim boundaries

The following claims are explicitly not made by Stele:

- Stele implements Yurihak.
- Stele proves mathematical relativism.
- Stele replaces classical foundations.
- Yurihak is now formally verified.
- The foundational research papers are formalized in Stele.
- Stele is a complete proof assistant.
- Stele provides automatic theorem proving.

The following claims are explicitly made by Stele:

- Stele is a proof checker: it checks proofs supplied by the user.
- Stele's proof checker is purely syntactic and does not embed semantic reasoning.
- Stele supports multiple logic rule sets as explicit, variable parameters.
- Stele's matrix and Kripke layers provide semantic diagnostics — not validity verdicts.
- Stele was motivated by research into logical pluralism and Yurihak.
- Future formalization of Yurihak in Stele is a research aspiration with a defined path.

---

## §6. TODO for future formalization (Prompt 47 and beyond)

- [ ] Extract and summarize all four source PDFs when tool available
- [ ] Identify specific Yurihak formal definitions that map to `RuleSchema`
- [ ] Write a specification document for a minimal Yurihak fragment (`docs/yurihak-spec.md`)
- [ ] Implement a prototype Yurihak rule set as an isolated module (not in `logic.py` yet)
- [ ] Write worked proof examples for the prototype
- [ ] Test soundness via `rule_soundness()` against K3, LP, and a Yurihak-specific matrix
- [ ] Assess whether window-localized / closure-atlas / bounded-core concepts
      require new Stele infrastructure or can use existing matrix/Kripke/world APIs
- [ ] Update `DECISIONS.md` if a Yurihak logic is approved for inclusion
- [ ] Note for Prompt 47: build the references/provenance map in `docs/references.md`

---

## §7. Notes for Prompt 47 — references/provenance map

Prompt 47 is expected to build a full references and provenance map.
The following will need to be tracked:

- Each source PDF: author, title, year (to be extracted from papers)
- Each claim in `site/foundations.html` and its backing source
- Connection between paper claims and Stele module behaviors
- Status labels for each connection (Implemented / Conceptual influence / Future)
- Any papers cited in `paper/stele-whitepaper.tex` that intersect with the Yurihak program
