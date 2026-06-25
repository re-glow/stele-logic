# Changelog

Development history of Stele Logic System.

---

## [v1.4.0] — 2026-06-25  `release/v1.4-overhaul-freeze`

v1.4 editorial and visual overhaul: site pages rewritten, ops files added,
SEO/OG/favicon applied, kernel LOC corrected, version footer on all pages,
claim and link audit. No new proof semantics, no kernel changes.

### Added

- **Hero constellation + verdict pulse (Tasks 57–58):** `site/index.html` rebuilt
  from scratch — hero SVG constellation of proof steps, animated pulse propagating
  along edges every ~6 s (reduced-motion → static); live proof demo with
  syntax-highlighted editor, error bar, verdict card; trust-boundary SVG;
  classical vs intuitionistic comparison; Space Grotesk variable display font
  (self-hosted OFL); 6-category glow hierarchy.
- **Studio workbench (Task 59):** `site/studio.html` and `site/assets/stele-pyodide.js`
  rewritten — 60/40 editor/result split; rich verdict card with kernel/logic/steps/
  theorem/diagnostics meta; gutter error highlights; inline SVG dependency graph
  with BFS layout; 4 semantic preset buttons; 3-phase Pyodide loading indicator.
- **Site-wide SEO/OG (Task 60):** `og:title`, `og:description`, `og:type`,
  `twitter:card` added to all 7 pages.
- **Favicon:** `site/favicon.svg` (amethyst ⊢ on dark background).
- **Versioned footer:** all pages now show `v1.4.0 · CHANGELOG` link.
- **Ops files:** `LICENSE` (MIT), `CITATION.cff`, `CONTRIBUTING.md`,
  `SECURITY.md`, `docs/limitations.md`.

### Changed

- `stele/__version__.py`: `"1.3.0"` → `"1.4.0"`.
- `README.md`: version heading updated to v1.4.0; test count to 2,390+;
  capability matrix heading updated to v1.4.
- `site/about.html`: kernel LOC corrected `~400` → `≈160`; test count
  `Over 2,000` → `2,390+`.
- `site/research.html`: hero abstract sharpened — "Stele asks whether logical
  validity can be treated as a configurable rule boundary rather than a fixed
  assumption of the verifier."
- `tests/test_v12_release.py`: version assertions updated to v1.4.0.

### QA / v1.4 audit

- Kernel LOC verified: `wc -l stele/kernel.py` → 159 lines (reported ≈160).
- All overclaim phrases absent (no `~400 line kernel`, no fabricated test counts).
- OG meta tags on all 7 pages; favicon linked on all 7 pages.
- Footer version link on all 7 pages.
- `python -m pytest -q` passes.

### Known limitations (v1.4)

- No new proof semantics relative to v1.3.
- All v1.3 known limitations carry forward (propositional surface, bounded Kripke,
  code-level cert isolation, untrusted hints, sketch-level metatheory, CDN Pyodide).

---

## [v1.3.0] — 2026-06-24  `release/v1.3-presentation-freeze`

v1.3 presentation freeze: amethyst visual system applied across all site pages;
full internal/external link audit; claim/status audit; accessibility pass (WCAG AA,
keyboard, reduced-motion); clean static build; pytest green. No new proof semantics.

### Changed

- **Design system — landing (Prompt 53):** Full visual overhaul on `design/visual-system-landing`.
  - New amethyst palette (`#7C5CFF`/`#9D7BFF` primary, `#3E9C8F` success, `#36D6FF` cyan-accent-only).
  - Background graphite `#0B0A10`. Terminal-mint retired across all CSS/JS.
  - Self-hosted OFL fonts: Spectral (display headings), IBM Plex Sans (body/UI), IBM Plex Mono (code/proofs).
  - 10 woff2 files + `site/assets/fonts/fonts.css` + `OFL.txt`.
  - `tokens.css` rewritten as palette/typography source of truth.
  - `stele_site.css`, `components.css`, `visuals.css` updated (cyan→amethyst, mint→success).
  - ProofOrb particle palette updated to amethyst.
  - Hero copy: "Write a proof. Verify each step." + natural prose (no stacked negatives).

- **Page design polish — all sub-pages (Prompt 54):** Applied v1.3 design system to
  studio, theory, architecture, research, foundations, about on `design/page-polish`.
  - All hardcoded old-palette SVG/inline colors fixed (`#52c97a`→`#3E9C8F`, `#b06aff`→`#9D7BFF`, etc.).
  - `.page-motif` CSS: dim decorative glyph per page (⊢ studio/arch, ∴ theory/research, ∀ foundations, λ about).
  - `.trust-grid` class replaces cramped `gap:14px` inline card grids.
  - `.prose-reading` class: 72ch reading column for academic pages.
  - `research.html` rewritten: skeleton placeholders replaced with real content
    (Research Motivation, Proof Assistants comparison table, References table).

- `stele/__version__.py`: `"1.2.0"` → `"1.3.0"`.
- `README.md`: version heading and capability matrix updated to v1.3.0.
- `docs/site-quality.md`: accessibility checklist updated with v1.3 audit results.
- `docs/release-checklist.md`: updated for v1.3.

### QA / v1.3 audit (Prompt 55)

- Internal link audit: all 7 nav links resolve to deployed pages; no broken paths.
- External link audit: all GitHub repo links verified to exist in current main.
- Claim/status audit: no invented metrics; all experimental features carry Experimental/Untrusted labels.
- Accessibility: `prefers-reduced-motion` honored everywhere; SVGs have `role="img"` + `<title>`/`<desc>`; focus rings on all interactive elements; `.focus-skip` on every page.
- Build: `python tools/build_pyodide_site.py` deploys all 7 pages; 2512 tests pass (4 skipped).

### Documentation

- `CHANGELOG.md` — this v1.3.0 entry.
- `docs/site-quality.md` — v1.3 accessibility audit results.
- `docs/release-checklist.md` — v1.3 checklist.

---

## [v1.2.0] — 2026-06-24  `release/v1.2-presentation-freeze`

v1.2 public-presentation freeze: Prompts 42–49 site/research integration arc consolidated,
claim-audited, and synchronized. No new proof semantics in this release — version update,
documentation synchronization, site completion, release preparation only.

### Added

- **Public site pages (Prompts 42–50):** Information architecture redesigned; landing,
  Studio, Theory, Architecture, Foundations, Research, About pages fully implemented.
  - `site/index.html` — redesigned landing with proof-graph hero, tutorial, gallery.
  - `site/studio.html` — separate Studio workbench page (Pyodide-backed, no backend).
  - `site/theory.html` — theory and semantics documentation page (⊢ vs ⊨, proof terms,
    Kripke, matrix, metatheory).
  - `site/architecture.html` — trust boundary and architecture page.
  - `site/foundations.html` — Yurihak research program page (motivation/future, not
    implemented logic).
  - `site/research.html` — whitepaper and references page.
  - `site/about.html` — author and project-story page.
- **Design system** (`docs/design-system.md`, `site/assets/tokens.css`,
  `site/assets/stele_site.css`, `site/assets/components.css`, `site/assets/visuals.css`):
  design tokens, component library, accessibility policy, IA plan.
- **Annotated references** (`docs/references.md`): 6-section reference guide mapping each
  algorithmic foundation to implementation module, status, and limitation.
- **Provenance map** (`docs/provenance-map.md`): 4 structured tables — claim → module →
  test → source → limitation; citation status; inspiration vs implementation.
- **Research notes packet** (`docs/research-notes/`): 12 structured notes covering
  architecture, proof language, proof terms, diagnostics, semantics, certificates, ML,
  foundations, related work, limitations, and paper outline. Includes
  `claim-evidence-matrix.md` (26 rows, 7 columns per claim) and GPT writing instructions.
- **BibTeX entries** (`paper/references.bib`): Malinowski 1993, Harper et al. 1993,
  Yang et al. 2023 (LeanDojo). Replaced `\cite{TODO:*}` keys in whitepaper.
- **Public-readiness audit** (`docs/audit-public-readiness.md`): full v1.2 closure section
  documenting resolution of all P0/P1 items from Prompt 41.
- **Release notes draft** (`docs/release-notes-v1.2.0.md`): copy-pasteable GitHub
  Release description.

### Changed

- `stele/__version__.py`: `"1.1.0"` → `"1.2.0"`.
- README.md: version heading updated to v1.2.0; capability matrix updated; site page links
  added (Studio, Theory, Architecture, Foundations, Research, About); provenance map and
  research notes links added; test count updated.
- `CLAUDE.md`: structure section updated to v1.2; test count updated.
- `docs/development-context.md`: version string and test count updated; site page inventory
  updated; roadmap section updated.
- `docs/release-checklist.md`: updated for v1.2.0 steps.
- `docs/whitepaper.md`: test count references updated; version in conclusion updated.

### Documentation

- `CHANGELOG.md` — this v1.2.0 entry.
- `docs/references.md` — new annotated references document.
- `docs/provenance-map.md` — new claim/implementation provenance tables.
- `docs/research-notes/` — new 12-file research notes packet.
- `docs/release-notes-v1.2.0.md` — release notes draft.
- `docs/audit-public-readiness.md` — v1.2 closure section added.
- `docs/release-checklist.md` — updated for v1.2.

### Site / UX

- Landing page: proof-dependency-graph hero motif (Canvas/SVG), tutorial, 15-entry gallery.
- Studio separated from landing: `site/studio.html` (dedicated page, Pyodide-backed).
- Theory page: ⊢ vs ⊨ diagram, proof terms, Kripke semantics, matrix semantics, metatheory.
- Architecture page: trust-boundary diagram, import invariants, certificate flow, deployment modes.
- Foundations page: Yurihak program framing (motivation/future distinction enforced).
- Research page: whitepaper link, BibTeX references link, research notes.
- About page: project story, evidence cards, author role, AI-tool transparency note, limitations.
- Status badges (Stable/Experimental/Optional/Demo/Motivation/Untrusted) applied across all pages.
- Navigation complete: all 7 pages linked from every page nav, with `aria-current` on active page.
- Accessibility: `prefers-reduced-motion`, `focus-visible`, `aria-*` labels throughout.

### CI / Release

- No workflow changes: `ci.yml` (Python 3.10–3.12), `pages.yml` (GitHub Pages),
  `release.yml` (executables + stele.html), `ml.yml` (optional dispatch) unchanged.
- `.gitignore` updated: `references/incoming/`, `test_out.txt` added.

### Known limitations (v1.2)

- Stele-Light proof-script surface remains propositional — no `forall`/`exists` at script level.
- Kripke countermodel search is bounded finite (≤4 worlds default); no completeness theorem.
- Classical proof-term bridge is formula-level only (Gödel–Gentzen); no λμ/callcc.
- Minicheck is a Python code path (same process as kernel); not formally isolated.
- Proof-state hints are UNTRUSTED structural suggestions; require kernel-recheck.
- ML baseline remains optional/experimental; metrics cover the 40-record synthetic corpus only.
- Metatheory claims are proof sketches + regression/property tests; not machine-checked.
- Single-file `stele.html` requires Pyodide CDN (~8 MB, cached after first load).
- Whitepaper is a draft technical report; not peer-reviewed.
- Foundations page covers research motivation only; Yurihak is not yet a formal Stele logic.

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
