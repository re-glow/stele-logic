# Contributing to Stele

Stele is an independent research project. Contributions are welcome within the
constraints described here. Read this document before opening an issue or PR.

## What this project is

Stele is a proof checker, not a theorem prover. It checks proofs you write;
it does not search for proofs. The primary design invariants are in `CLAUDE.md`
and `docs/development-context.md`. Please read those before contributing.

## Hard constraints (non-negotiable)

1. **Do not modify `stele/kernel.py`** unless fixing a correctness bug with a
   failing test that demonstrates the bug. The kernel is the trust boundary.
2. **Do not add runtime dependencies** to `stele/`. The trusted core must remain
   stdlib-only. Tests may use `pytest` and optionally `hypothesis`.
3. **Do not add new research claims** without corresponding evidence in the
   repository (tests, measurements, documented limitations).
4. **Do not commit generated artifacts** (`dist/`, `*.pyc`, `paper/*.pdf`,
   `paper/*.aux`). Check `.gitignore`.
5. **Do not use npm, webpack, React, Tailwind, Three.js, or other build
   frameworks** for the site. The site is plain HTML/CSS/JS.

## How to contribute

### Bug reports

Open a GitHub issue with:
- The proof script that triggers the bug (`.stele` file content)
- The `--logic` flag used
- Expected output vs actual output
- Python version and OS

### Feature requests

Open a GitHub issue describing:
- What the feature would do
- Which invariant from `CLAUDE.md` it affects (if any)
- Whether it belongs inside or outside the trusted kernel

### Code contributions

1. Fork the repository.
2. Create a branch from `main`.
3. Make your changes. Run `python -m pytest -q` — all tests must pass.
4. If you change any inference rule or add a new logic, add corresponding tests
   and update `examples/` with at least one working `.stele` proof.
5. If you change any public site claim, verify the evidence is in the repo.
6. Open a PR against `main`. Describe what changed and why.

### Documentation contributions

Corrections and clarifications are welcome. Do not add claims that are not
supported by the repository's tests or measurements.

## Status labels

The project uses explicit status labels on all features:

| Label | Meaning |
|-------|---------|
| `Stable` | Tested, documented, part of the public API |
| `Experimental` | Working but not yet fully stabilized |
| `Untrusted` | Explicitly outside the trust boundary |
| `Optional` | Requires extra install; isolated from trusted path |
| `Demo` | Illustrative only; not for production use |
| `Motivation` | Research context that motivated the design; not implemented |
| `Future` | Planned but not yet started |

New contributions must carry an appropriate status label.

## Code style

- Python identifiers in English; user-facing strings may be in Korean.
- AST, schema, and proof-node types are frozen dataclasses.
- No comments explaining what the code does; only the non-obvious why.
- Run `python -m pytest -q` before every commit.

## Questions

Open a GitHub issue with the `question` label.
