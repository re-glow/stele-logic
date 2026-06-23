# Changelog

Development history of Stele Logic System.

---

## [v1.1.0] — 2026-06-23  `release/v1.1-freeze`

v1.1 freeze: post-v1.0 research arc (Prompts 34–42) consolidated, audited, and stabilized.
No new major features in this release commit — version update, claim audit, capability matrix
update, documentation synchronization, and release preparation only.

### Added

- **FOL object-variable de Bruijn** (`stele/core/debruijn.py`, `stele/core/fol.py`):
  `to_debruijn_formula`, `alpha_equiv_formula`, `DBForallIntro/Elim/ExistsIntro/Elim`
  for formula-level α-equivalence. Proof-term-layer object-variable de Bruijn (`to_debruijn_fol`)
  remains future work.
- **FOL quantifier surface syntax** (`stele/core/fol.py`, `stele/core/term_parser.py`):
  `forall x. φ` / `exists x. φ` in proof-term formulas and terms; ForallIntro/Elim/ExistsIntro/Elim
  proof-term constructors; freshness/capture-avoidance enforcement.
  Stele-Light proof-script surface remains propositional (no FOL at script level).
- **Finite Kripke semantics and countermodel search** (`stele/kripke.py`):
  `KripkeModel`, `forces()`, `find_countermodel()` (bounded exhaustive search ≤4 worlds default),
  `KripkeExplanation`, `kripke_explain()`. Intuitionistic propositional logic only.
  CLI: `python -m stele.cli kripke "P or not P"`.
- **Kripke countermodel surfaces** (CLI, Studio API, Pyodide site, diagnostic pass 4).
- **Experimental classical proof-term bridge** (`stele/core/classical_experimental.py`):
  Gödel–Gentzen negative translation and `check_negative_translation`.
  Formula-level only; λμ/callcc/automatic proof translation not implemented.
- **Proof certificates and minicheck** (`stele/certificate.py`, `stele/minicheck.py`):
  kernel-gated certificate emission, versioned JSON format, independent Python re-verification
  path that does not import the main kernel/parser/diagnostics.
- **Proof-state context and untrusted rule hints** (`stele/proofstate.py`):
  `ProofState`, `suggest_rule_hints()` (10 structural patterns, no proof search, no ML).
  All hints carry `trusted=False`; all API responses include `_untrusted: true`.
- **ML corpus data discipline** (`stele_ml/build_dataset.py`, `docs/benchmark-card.md`):
  deterministic 3-way split, failure-mode analysis, optional ML workflow.
- **Technical whitepaper** (`docs/whitepaper.md`, `paper/stele-whitepaper.tex`,
  `paper/references.bib`): full Markdown and LaTeX source.
- New test files: `test_kripke.py` (55), `test_kripke_integration.py` (61),
  `test_classical_experimental.py` (45), `test_certificate.py` + `test_minicheck.py` (48),
  `test_proofstate.py` (78), `test_fol_object_debruijn.py` + `test_fol_surface.py` (81+),
  `test_ml_corpus_discipline.py` (29), `test_whitepaper.py` (32), `test_v11_invariants.py` (new).
- `docs/site-quality.md`: lightweight public site quality and honesty policy.

### Changed

- Test count: 1,298 (v1.0) → 1,836 (v1.1) passed, 4 skipped (Hypothesis optional).
- README version heading and capability matrix updated to v1.1.
- Capability matrix corrections:
  - `Proof certificates & minicheck`: `Stable` → `Experimental` (v1.1 feature, not formally verified).
  - `Proof state & hints`: `Stable` → `Experimental / Untrusted`.
- `stele/__version__.py`: `"1.0.0"` → `"1.1.0"`.
- `docs/metatheory.md` section labels corrected: certificates/proof-state sections labelled
  "v1.2"/"v1.3" during development; corrected to "v1.1".
- `docs/development-context.md`: test count, version string, roadmap updated.

### Fixed

- `docs/metatheory.md` section 9/10 version labels corrected from "v1.2"/"v1.3" to "v1.1".

### Documentation

- `CHANGELOG.md` — this v1.1.0 entry.
- `docs/whitepaper.md` + `paper/stele-whitepaper.tex` — technical whitepaper.
- `docs/benchmark-card.md` — ML corpus benchmark card.
- `docs/site-quality.md` — site quality policy.
- README, GUIDE, CLAUDE.md, development-context.md, metatheory.md, release-checklist.md updated.

### CI / Packaging

- `.github/workflows/ml.yml`: optional manual ML workflow (non-blocking, `workflow_dispatch` only).
- All existing workflows unchanged; continue using stable action versions.

### Known limitations (v1.1)

- Stele-Light proof-script surface remains propositional — no `forall`/`exists` at script level.
- Kripke countermodel search is bounded finite (≤4 worlds default); no completeness theorem.
- Classical proof-term bridge is formula-level only; no λμ/callcc.
- Minicheck is an independent Python code path, not a separate process or formally verified checker.
- Proof-state hints are UNTRUSTED structural suggestions; must be kernel-rechecked.
- ML baseline remains optional/experimental; measured metrics are for the generated sample only.
- Metatheory claims are proof sketches + regression/property tests, not machine-checked proofs.

---

## [v1.0.0] — 2026-06-22  `release/v1.0-freeze`

Public v1.0 freeze. No new features — release engineering, documentation
synchronization, CI stabilization, and claim audit only.

### Added

- `stele/__version__.py` — version string `"1.0.0"`; exposed via `stele.__version__`.
- `docs/release-checklist.md` — pre-tag and post-tag release checklist.
- Capability matrix in README (v1.0 status table for all subsystems).
- "First five minutes" section in `GUIDE.md` (§0) with tutorial map and gallery reference.
- Gallery honesty tests (`tests/test_gallery.py`, 65 tests) verifying that every
  `site/examples_gallery.json` entry label (`pass`/`fail`/`warn`) matches the
  actual kernel result on every CI run.
- Interactive 6-step tutorial and 15-entry verified example gallery on the public site
  (`site/index.html`, `site/assets/stele-pyodide.js`).

### Changed

- README restructured to be public-first: public site URL, capability matrix,
  distribution modes, limitations, development notes.
- Test count references updated throughout (1,298 tests collected; ~1,294 pass,
  4 skipped pending `hypothesis`).
- `docs/development-context.md` updated: added missing modules (`browser.py`,
  `diagnostics.py`, `proofgraph.py`, `errors.py`, `eval.py`, `types.py`);
  corrected test count; updated roadmap to reflect completed items (dependency
  graph, structural diagnostics, corpus generator, public site, packaging).

### Fixed

- Removed outdated roadmap item "LLM 튜터" from README (not implemented; moved to
  optional future work in development context).
- Corrected stale test-count claims: "226개 이상" / "888개" → "1,298개 수집됨".

### Documentation

- `CHANGELOG.md` — this v1.0.0 entry.
- `docs/release-checklist.md` — new.
- README: capability matrix, limitations section, public site URL, corrected claims.
- `GUIDE.md` §0: "First five minutes" orientation section.
- `docs/development-context.md`: corrected module list, test count, roadmap.

### CI / Packaging

- Workflows verified: `ci.yml` (Python 3.10–3.12), `pages.yml` (Pyodide site →
  GitHub Pages), `release.yml` (executables + `stele.html` on tag push).
- All actions use current stable major versions (checkout@v4, setup-python@v5,
  upload-pages-artifact@v3, deploy-pages@v4, upload-artifact@v4).
- Release workflow confirms `stele.html` excludes `stele_ml/`, `stele_lean/`,
  and `/api/` calls.

### Known limitations (v1.0)

- Proof-script language covers propositional logic only (no first-order quantifiers
  at the Stele-Light surface level).
- Relativity is at rule-availability level; semantic non-derivability requires
  matrix/Kripke semantics (not the kernel).
- Single-file `stele.html` requires internet for Pyodide CDN (~8 MB, cached after
  first load); full offline mode is out of scope for v1.
- Proof-term core is intuitionistic only; classical rules are excluded by design.
- de Bruijn layer covers proof-variable binders only; FOL object-variable binders
  remain name-based (full `to_debruijn_fol` is future work).
- ML baseline (`stele_ml/`) and Lean bridge (`stele_lean/`) are optional, isolated,
  and experimental — not part of the trusted checking path.

---

## [onboarding-tutorial-gallery] — 2026-06  `feat/onboarding-tutorial-gallery`

- Interactive 6-step tutorial on the public landing page (proof format, error
  diagnosis, dependency graph, classical vs intuitionistic, semantic tools,
  next steps). Prev/next navigation, dot indicators, `aria-live` counter, skip link.
- Verified example gallery: 15 curated proof entries with category tags
  (intuitionistic / classical-only / diagnostics) and expected-outcome badges
  (✓ Valid / ⚠ Warning / ✗ Error).
- `site/examples_gallery.json`: source of truth for gallery honesty tests.
  Each `expected` label (`pass`/`fail`/`warn`) verified against the real kernel.
- `tests/test_gallery.py` (65 tests): gallery JSON structure, honesty (actual
  kernel results match labels), tutorial HTML structure, site accessibility
  markers, JS rendering invariants.
- Accessibility improvements: `aria-live` on result panels, `aria-current` on
  tutorial dots, `aria-controls` on tab buttons, `aria-hidden` on decorative icons.
- `GUIDE.md` §0 "First five minutes" section added.

---

## [reframe] — 2026-06  `docs/reframe-verification-framework`

- Reframed project primary identity as "Formal Verification Framework for Mathematical Reasoning."
  - First impression is now: structured proof objects, rule-based checking, diagnostics, error localization.
  - Logical pluralism / "유리학" demoted to background inspiration and optional semantic module motivation.
  - Matrix semantics, K3/LP, rule soundness, world status, lattice demo are described as diagnostic support modules, not the project's primary identity.
- Updated dependency policy: trusted `stele/` core remains stdlib-only; optional future ML/Lean/UI extensions may add isolated dependencies outside the trusted checking path.
- Aligned roadmap with formal-verification trajectory: dependency graphs, proof-state tracking, error diagnostics, benchmarks, failure-mode taxonomy, optional ML/Lean bridge.
- Honesty clause added: do not claim corpus sizes, model accuracy, or Lean integration before implementation and measurement.
- DECISIONS.md: added reframing note (historical decisions preserved).

---

## [stabilize] — 2026-06  `chore/stabilize-presentation-ready`

- Renamed `tests.yml` → `ci.yml`; updated README CI reference.
- Synchronized README, docs/development-context.md, RESULTS.md with implemented feature set.
  Fixed stale claims: "dne only" classical distinction, "no matrix surface syntax", "no world/lattice", "19 tests".
- Added CHANGELOG.md.
- Added regression test: proof and matrix modules do not cross-import.

---

## [world-lattice] — 2026-06  `feat/world-lattice-demo`

- Added `lattice_status(formula, worlds)` helper to `stele/world.py`.
- Added `python -m stele.cli lattice <formula>` command.
  Builds a CH-style three-world family: base (INDEPENDENT), Γ+φ (PROVABLE), Γ+¬φ (REFUTABLE).
- Added `examples/world_ch_style.py` Python demo.
- Added 18 tests in `tests/test_world_lattice.py`.
- Updated `GUIDE.md` §11 documenting the `lattice` command with explicit disclaimer:
  this is a toy propositional independence pattern, not real CH or set-theoretic forcing.

---

## [world-status] — 2026-06  `feat/world-semantic-status`

- Added `stele/world.py`: `World(matrix_name, axioms)` frozen dataclass;
  status constants `PROVABLE`, `REFUTABLE`, `BOTH`, `INDEPENDENT`;
  `status(formula, world)` using matrix entailment (no proof search, no kernel call).
- `BOTH` status covers paraconsistent LP where axioms can entail both φ and ¬φ.
- Added 27 tests in `tests/test_world.py`.
- Updated `GUIDE.md` §10 with clear distinction: PROVABLE = semantic entailment, not derivability.

---

## [rule-soundness] — 2026-06  `feat/rule-soundness-report`

- Added `SoundnessResult` and `rule_soundness(schema, matrix)` to `stele/matrix.py`.
  Enumerates all metavar valuations; checks designation preservation for non-discharge rules.
- Added `python -m stele.cli soundness --logic L --matrix M` command.
- Added `fixpoint not` / `liar` matrix directives (parse to `MatrixDirective("fixpoint", ...)`).
- Added 36 tests in `tests/test_rule_soundness.py`.

---

## [matrix-surface] — 2026-06  `feat/matrix-surface-mode`

- Added `MatrixLogic` class in `logic.py`; registered K3/LP/boolean in the `LOGICS` namespace.
- Added `MatrixDirective` dataclass in `proof.py`.
- Added `parse_matrix_file()` in `parser.py` supporting:
  `evaluate`, `tautology?`, `entails ... |- ...`, `fixpoint not`, `liar`.
- Added `_check_matrix()` dispatch in `cli.py`; CLI routes `--logic K3/LP/boolean` to matrix mode.
- Added `Op("bot",())` (falsum) handling in `matrix.py` `evaluate`.
- Added 37 tests in `tests/test_matrix_surface.py`.
- Added `examples/matrix_k3.stele`, `matrix_lp.stele`, `matrix_boolean.stele`.

---

## [classical-principles] — 2026-06  `feat/classical-principles`

- Added `lem` (`⊢ A∨¬A`) and `pbc` (`[¬A]…⊥ ⊢ A`) schemas to `logic.py`; added `LEM`, `PBC` exports.
- `classical_prop` now differs from `intuitionistic_prop` by three rules: `dne`, `lem`, `pbc`.
- Added `examples/peirce.stele` (Peirce's law), `examples/lem.stele`.
- Added 16 tests in `tests/test_classical_principles.py`.
- Updated `GUIDE.md`.

---

## [generic-discharge] — 2026-06  `feat/generic-discharge`

- Added `hyp_premises: tuple` field to `RuleSchema` for generic hypothesis-discharge rules.
- Implemented `neg_intro` (`[A]…⊥ ⊢ ¬A`) and `or_elim` (`A∨B,[A]…C,[B]…C ⊢ C`).
- `pbc` reuses the same discharge mechanism.
- Added tests in `tests/test_generalized_discharge.py` and `tests/test_discharge_rules.py`.

---

## [new-rules] — 2026-06  `feat/propositional-rules`

- Added to both logics: `neg_elim` (¬E), `ex_falso` (⊥E), `or_intro_left`, `or_intro_right`.
- Added `false` keyword → `Op("bot",())` in parser.
- Added `neg_intro` (¬I) as a discharge rule.
- Added tests in `tests/test_new_rules.py`.
- Updated examples.

---

## [conclusion-directed] — 2026-06  `feat/conclusion-directed`

- Kernel rule matching is now conclusion-directed: kernel extracts the expected pattern from
  the rule's conclusion, unifies with the claimed formula, then verifies premises.
- Added tests in `tests/test_conclusion_directed.py`.

---

## [initial-mvp] — 2026-06  `Initial Stele Logic MVP`

- Initial proof checker: `ast.py`, `proof.py`, `parser.py`, `logic.py`, `kernel.py`.
- Two logics: `intuitionistic_prop` (copy, mp, imp_intro, and_intro/elim)
  and `classical_prop` (adds `dne`).
- Many-valued semantics: `matrix.py` with K3, LP, boolean; `demos` CLI command.
- Web UI: `web.py` + `webapp/index.html`.
- CI via GitHub Actions.
- 19 initial tests.
