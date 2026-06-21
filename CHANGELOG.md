# Changelog

Development history of Stele Logic System.

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
