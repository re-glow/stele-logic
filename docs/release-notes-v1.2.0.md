# Stele v1.2.0 — Release Notes

**Public-presentation freeze: 프레젠테이션·연구 통합 아크 완성**

---

## Summary

Stele v1.2.0 is a documentation and presentation freeze, not a feature release. It completes the Prompts 42–50 arc that added public-facing site pages, a design system, research documentation, and claim/status audits. The core proof semantics and trusted kernel are unchanged from v1.1.

In brief: v1.2.0 adds seven complete public site pages, a structured research-notes packet for paper drafting, annotated references, a provenance map, and version/documentation synchronization across all public-facing files.

---

## Highlights

### Public site — 7 complete pages

- **Landing** (`/`): proof-dependency-graph hero, 5-step interactive tutorial, 15-entry CI-verified gallery.
- **Studio** (`/studio.html`): dedicated Pyodide-backed workbench. No backend. No data transmitted. Full kernel runs in-browser.
- **Theory & Semantics** (`/theory.html`): ⊢ vs ⊨, proof language rules, Curry–Howard proof-term core, Kripke countermodel search, K3/LP/Boolean matrix semantics.
- **Architecture & Trust** (`/architecture.html`): trust-boundary diagram, import invariants, certificate flow, deployment modes.
- **Foundations** (`/foundations.html`): Yurihak research program framing — what is implemented vs what is research motivation vs what is future. Enforces "motivation, not implemented logic" distinction.
- **Research** (`/research.html`): whitepaper link, BibTeX references, research notes.
- **About** (`/about.html`): project story, evidence cards, author role (includes AI-tool transparency note), limitations.

### Research documentation

- **`docs/research-notes/`** — 12 structured notes (system overview, architecture, language/kernel, proof terms, diagnostics, semantics, certificates, ML, foundations, related work, limitations, paper outline) + `claim-evidence-matrix.md` (26 claims × 7 columns: status, evidence, safe wording, unsafe wording, limitation). Structured for academic paper drafting.
- **`docs/references.md`** — annotated references: which algorithms are implemented, which are inspiration, what Stele does not claim.
- **`docs/provenance-map.md`** — four tables: claim → module → test → source → limitation; inspiration vs implementation; module provenance; citation status.

### BibTeX completeness

Three `\cite{TODO:*}` keys replaced with real BibTeX entries:
`Malinowski1993`, `HarperHP1993`, `Yang2023` (LeanDojo).
All 13 whitepaper citation keys are now defined in `paper/references.bib`.

### Version and claim synchronization

- `stele/__version__.py`: `1.1.0` → `1.2.0`
- README, CLAUDE.md, `docs/development-context.md`, whitepaper, release checklist updated.
- Test count references updated throughout (2390 passing, 4 skipped without Hypothesis).

---

## What Changed Since v1.1

v1.1 added the proof-term core, Kripke semantics, certificates, ML baseline, and whitepaper.

v1.2 adds:
- Seven complete public site pages with a consistent design system.
- Research notes packet (12 files + claim matrix).
- Annotated references and provenance map.
- About / author page.
- Documentation synchronization and release preparation.

No changes to the trusted kernel, proof language, rule sets, or proof semantics.

---

## Limitations

- **Not a theorem prover.** Stele does not search for proofs. You write each step; the kernel checks it.
- **Propositional surface language.** The Stele-Light proof-script language is propositional. The proof-term core has an experimental FOL fragment, but FOL proof scripts are not yet supported.
- **Kripke search is bounded.** `find_countermodel()` searches ≤4 worlds by default. No countermodel found does not imply the formula is intuitionistically valid.
- **Certificates and minicheck are experimental.** Minicheck is an independent Python code path in the same process; not a formally isolated or verified checker.
- **Proof-state hints are UNTRUSTED.** Structural suggestions only; require kernel-recheck.
- **Metatheory is documented, not machine-checked.** Proof sketches + regression/property tests.
- **Browser Studio requires Pyodide CDN** (~8 MB, cached after first load).
- **Whitepaper is a draft.** Not peer-reviewed.
- **Yurihak is not yet a Stele logic.** The Foundations page covers research motivation; there is no `yurihak_prop` logic object in the system.

---

## How to Use

**Browser (no install):**
```
https://re-glow.github.io/stele-logic/studio.html
```

**Local Python (CLI):**
```bash
python -m stele.cli check examples/dne.stele --logic classical_prop
python -m stele.cli kripke "P or not P"
python -m pytest -q
```

**Local Studio (web interface):**
```bash
python -m stele
# opens http://127.0.0.1:8000
```

**Single-file HTML (shareable):**
```bash
python tools/build_single_html.py
# produces dist/stele.html (~135 KB + CDN Pyodide on first load)
```

---

## Links

| Resource | URL |
|----------|-----|
| Public site | https://re-glow.github.io/stele-logic/ |
| Studio | https://re-glow.github.io/stele-logic/studio.html |
| Theory & Semantics | https://re-glow.github.io/stele-logic/theory.html |
| Architecture & Trust | https://re-glow.github.io/stele-logic/architecture.html |
| Foundations | https://re-glow.github.io/stele-logic/foundations.html |
| About | https://re-glow.github.io/stele-logic/about.html |
| GitHub repository | https://github.com/re-glow/stele-logic |
| Whitepaper (Markdown) | docs/whitepaper.md |
| Whitepaper (LaTeX) | paper/stele-whitepaper.tex |
| Research notes | docs/research-notes/ |
| Provenance map | docs/provenance-map.md |
| Annotated references | docs/references.md |
| CHANGELOG | CHANGELOG.md |

---

*Independent research project by Jaehwan Kim.
Stele is a proof checker, not a theorem prover.
All metatheory claims are supported by regression tests and proof sketches, not machine-checked proofs.*
