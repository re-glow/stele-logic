# stele_lean — Optional Lean 4 Bridge

> **Status:** Experimental / v1.  
> **Lean requirement:** Optional. All Lean-dependent operations skip cleanly when `lean` is not on `PATH`.  
> **Isolation:** `stele/` (trusted core) must NOT import `stele_lean`. Verified by `tests/test_lean_bridge.py`.

---

## What it does

`stele_lean` exports Stele propositional theorems to Lean 4 skeletons and surfaces Lean elaboration errors as `LeanDiagnostic` objects.

The primary use case is **type-checking the theorem statement** — verifying that a Stele-expressed proposition is well-typed in Lean 4's propositional logic fragment. The proof body is always `sorry` (a Lean placeholder); Lean accepts it with a warning, which is expected.

---

## Supported fragment (v1)

| Stele operator | Lean 4 output |
|---|---|
| `P -> Q` | `P → Q` |
| `P and Q` | `P ∧ Q` |
| `P or Q` | `P ∨ Q` |
| `not P` | `¬P` |
| `false` | `False` |
| `Var("P")` | `P : Prop` (via `variable` decl) |

**Not supported in v1:**
- K3 / LP / matrix semantics
- Paraconsistent worlds
- First-order logic
- Mathlib constructs
- Full proof-body translation (future work)
- Lean as a Python dependency (it is discovered via `shutil.which`)

---

## Installation

Lean 4 must be installed separately. Python-level installation is not required — the bridge discovers `lean` via `PATH`.

Install Lean 4: https://leanprover.github.io/lean4/doc/quickstart.html

---

## Usage

### CLI

```sh
# Export .stele to Lean 4 (no Lean required)
python -m stele_lean.check --export-only examples/dne.stele

# Check a .stele file with Lean
python -m stele_lean.check examples/dne.stele

# Check a raw .lean file
python -m stele_lean.check --lean-file stele_lean/examples/mp_valid.lean

# Export only (print Lean source, do not run Lean)
python -m stele_lean.check --export-only examples/dne.stele
```

### Python API

```python
from stele_lean.export import formula_to_lean, theorem_to_lean_skeleton
from stele_lean.check import lean_available, check_lean_file, check_stele_file
from stele_lean.diagnostics import parse_lean_output

# Check Lean availability
if not lean_available():
    print("Lean not found; bridge unavailable")

# Export a formula
from stele.ast import Var, Op
f = Op("imp", (Var("P"), Var("Q")))
print(formula_to_lean(f))   # → "P → Q"

# Check a .stele file
result = check_stele_file("examples/dne.stele")
print(result.summary())       # e.g. "1 warning(s)" (sorry warning)
print(result.has_errors)      # False for a valid theorem
print(result.lean_type_errors)  # [] if no type errors
```

---

## Architecture

```
stele_lean/
  __init__.py       package init + metadata
  export.py         Stele AST → Lean 4 syntax; theorem skeleton generator
  diagnostics.py    LeanDiagnostic, LeanCheckResult, parse_lean_output()
  check.py          Lean invocation wrapper + CLI (python -m stele_lean.check)
  examples/
    mp_valid.lean   valid modus ponens skeleton
    type_error.lean intentionally invalid (demonstrates error capture)
```

**Isolation invariant:** `stele/` must not import `stele_lean`. The bridge imports from `stele.ast` and `stele.parser` — but not vice versa. Enforced by `tests/test_lean_bridge.py::test_stele_does_not_import_stele_lean`.

---

## Diagnostics

When Lean is run, its output is parsed into `LeanDiagnostic` objects:

| Code | Lean severity | Meaning |
|---|---|---|
| `LeanTypeError` | `error` | Lean could not elaborate the theorem type |
| `LeanWarning` | `warning` | Warning (typically `sorry` usage — expected) |
| `LeanInfo` | `info` | Informational message |

`LeanDiagnostic` is **not** a subtype of `stele.diagnostics.Diagnostic` — the two diagnostic systems are independent to preserve isolation.

---

## Limitations (v1)

1. **Proof body not translated.** The skeleton uses `sorry` for all proofs.
2. **No soundness guarantee.** Lean accepting a proposition does not mean Stele's rule-based checker accepts it, or vice versa. The bridge is an optional cross-check, not authoritative.
3. **K3/LP/matrix not exported.** Multi-valued semantics have no Lean 4 equivalent in v1.
4. **No Mathlib.** stdlib Lean 4 only.
5. **Single theorem per file.** The CLI exports the first `theorem` block found in a `.stele` file.

---

## Running tests

```sh
# All tests (Lean-dependent tests skip cleanly if Lean not installed)
python -m pytest tests/test_lean_bridge.py -v

# Quick smoke: pure export tests (no Lean required)
python -m pytest tests/test_lean_bridge.py -v -k "not lean_required"
```
