# Stele Failure-Mode Taxonomy

This document describes every diagnostic code produced by `stele/diagnostics.py`.
Each code is a stable string; benchmark datasets and tests rely on these exact strings.

## Overview

Stele diagnostics are a **non-trusted analysis layer** separate from the kernel.
The kernel (`stele/kernel.py`) is the sole authority for proof validity.
Diagnostics describe *why* a proof failed (or has suspicious structure) without
changing the validity verdict.

Important caveats that apply to all codes:

- **Diagnostics are not proof repair.** They locate errors; they do not fix them.
- **Diagnostics are not theorem proving.** They describe structural failures in
  explicit proof steps; they do not search for missing steps.
- **Errors may cascade.** A single root cause can produce multiple codes.
  For example, a forward reference (`MissingHypothesis`) on line 2 may make a
  later step unreachable in the graph, triggering `UnusedAssumption`.
- **Parser failures prevent downstream diagnostics.** If the file cannot be parsed,
  no diagnostic codes are emitted; only the parse error is reported.
- **Line numbers are best-effort.** The diagnostics layer records the source line
  stored in each proof node. For `CircularDependency`, no single line is available
  (`line=None`).
- **Pass ordering matters.** Scope errors (pass 1) suppress `InvalidTransition`
  (pass 3) to avoid duplicating the root cause.

---

## Passes

| Pass | Name | Codes produced |
|------|------|----------------|
| 0 | Definition analysis | `UndefinedDefinition` |
| 1 | Scope analysis | `UndefinedSymbol`, `MissingHypothesis`, `UnsupportedConclusion` |
| 2 | Graph analysis | `CircularDependency`, `UnusedAssumption` |
| 3 | Kernel classification | `InvalidTransition` (only when pass 1 has no errors) |

---

## Diagnostic Codes

---

### `UndefinedSymbol`

**Origin:** Pass 1 (scope analysis)
**Severity:** error
**Category:** structural

**Meaning:** A proof step cites a label that does not exist anywhere in the proof tree.
Unlike `MissingHypothesis`, the label was never declared at all.

**Example:**
```
theorem t:
  assume h1: P -> Q
  have h2: Q by mp h1 missing    # 'missing' was never declared
  conclude Q by h2
```

**Pattern:** `cited label 'X' does not exist in this proof`

**Limitations:**
- The diagnostic is fired even if the typo is obvious (e.g., `mising` vs `missing`).
  The checker reports the location; the user must fix the name.
- In the graph pass, an undefined ref's "phantom" edge is not added to the
  backward-reachability set, so genuine assumptions may appear as
  `UnusedAssumption` when the undefined ref was the only path to the conclusion.
  Design tasks to avoid this interaction if a single-code label is needed.

---

### `MissingHypothesis`

**Origin:** Pass 1 (scope analysis)
**Severity:** error
**Category:** structural

**Meaning:** A proof step cites a label that *exists* in the proof but is not in scope
at the point of use.

Two common sub-cases:

1. **Forward reference** — the label is declared later in the proof than where it is used.
2. **Out-of-scope reference** — the label is local to a `suppose` block, but is
   referenced outside that block (e.g., in the outer `conclude`).

**Examples:**
```
# Forward reference
theorem t:
  have h2: P by copy h1    # h1 not yet in scope
  assume h1: P
  conclude P by h2

# Subproof label escaping its scope
theorem t:
  suppose h1: P
    have h2: P by copy h1
  conclude P by h2          # h2 is subproof-local; not visible here
```

**Pattern:** `label 'X' exists but is not in scope ...` or
`conclude references out-of-scope label 'X'`

**Limitations:**
- Discharge-pair refs (assume/conclude pairs in `neg_intro`, `imp_intro`, `or_elim`,
  `pbc`) require additional subproof-matching logic. A discharge pair that does not
  match any closed sibling subproof also triggers `MissingHypothesis`.

---

### `UnsupportedConclusion`

**Origin:** Pass 1 (scope analysis)
**Severity:** error
**Category:** structural

**Meaning:** The `conclude` step references a valid in-scope label, but the formula
claimed by `conclude` does not match the formula carried by that label.

**Example:**
```
theorem t:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
  conclude P -> Q by h3    # h3 carries Q, not P -> Q
```

**Pattern:** `conclusion 'P -> Q' does not match 'h3' = 'Q'`

**Limitations:**
- This is a *formula-level* mismatch at the final step only. Rule-application
  mismatches inside `have` steps are classified as `InvalidTransition`, not
  `UnsupportedConclusion`.
- The diagnostic is not emitted when the referenced label is out of scope or
  undefined (those take priority in pass 1).

---

### `CircularDependency`

**Origin:** Pass 2 (graph analysis)
**Severity:** error
**Category:** graph

**Meaning:** The proof dependency graph contains a directed cycle.
A cycle means at least one step depends (directly or transitively) on itself.

**Note on representability:** The Stele parser rejects proofs that would produce
obvious cycles through its sequential processing model. Artificial cycles require
constructing a `ProofGraph` directly (used in unit tests). In practice,
`CircularDependency` is a defensive check rather than a common surface error.

**Pattern:** `dependency graph contains a directed cycle`

**Limitations:**
- Line number is `None` (cycles span multiple nodes; no single line is canonical).
- Does not identify *which* cycle — only that one exists.

---

### `UnusedAssumption`

**Origin:** Pass 2 (graph analysis)
**Severity:** warning
**Category:** graph

**Meaning:** An `assume` or `suppose` step has no path to the `conclude` step in the
proof dependency graph. The assumption does not contribute to the conclusion, which
may indicate a missing step, a dead branch, or an unnecessary hypothesis.

**Example:**
```
theorem t:
  assume h1: P
  assume h2: Q    # h2 never appears in any subsequent step
  conclude P by h1
```

**Pattern:** `assumption 'X' does not contribute to the conclusion`

**Limitations:**
- This is a *warning*, not an error. The proof may still be valid (and pass
  strict `check`). An unused assumption is redundant, not wrong.
- Nested suppose blocks: if a suppose's local steps are all unused, the suppose
  itself may appear unused even if the suppose label appears in a discharge ref.
- Interaction with `UndefinedSymbol`: if an undefined ref was the only edge
  connecting an assumption to the conclusion, the assumption will appear unused.

---

### `UndefinedDefinition`

**Origin:** Pass 0 (definition analysis)
**Severity:** warning
**Category:** definition, heuristic

**Meaning:** A `definition` body references an identifier that looks like a definition
name but is not defined in this file.

```
definition USE_MISSING := MISSING_DEF -> P   # MISSING_DEF is not defined
```

**Pattern:** `definition body references 'X' which is not a defined name in this file`

**Heuristic classification:** Definition names are detected by the rule:
multi-character, all-uppercase identifiers (including underscores). Single-character
uppercase letters (`P`, `Q`, `R`, ...) are treated as propositional variables and
are **not** flagged.

**v1 limitations:**
- Multi-character propositional variable names (`PHI`, `PP`) will be incorrectly
  flagged as potential definition names. This is a known v1 false-positive risk;
  avoid such names or suppress the warning.
- Scanning applies only to the definition body, not to the theorem body.
- This is a heuristic `warning`, not an error. The proof itself may still be valid
  if the definition is not used in the theorem body.

---

### `InvalidTransition`

**Origin:** Pass 3 (kernel classification)
**Severity:** error
**Category:** kernel-derived

**Meaning:** All cited labels are in scope, but the rule application failed. The
formula of a cited hypothesis did not match the expected shape for the rule, or
the derived formula did not match the claimed formula.

**Examples:**
```
# mp with wrong second premise (P and R instead of P)
theorem t:
  assume h1: P -> Q
  assume h2: P and R
  have h3: Q by mp h1 h2    # mp needs h2: P, but h2 is P and R

# and_elim_left claims wrong conjunct
theorem t:
  assume h1: P and Q
  have h2: Q by and_elim_left h1    # and_elim_left gives P, not Q
```

**Pattern:** `rule 'R': premise N expected X, but 'hN' is Y`

**Mechanism:** Pass 3 calls the trusted kernel. When the kernel raises `ProofError`
with a message containing `"rule '"` but not `"is not available"`, the error is
classified as `InvalidTransition`. The kernel is the sole authority; this pass only
*labels* the kernel's output, it does not re-implement rule checking.

**Limitations:**
- Pass 3 runs only when pass 1 (scope analysis) found no errors. If `UndefinedSymbol`
  or `MissingHypothesis` is present, `InvalidTransition` is suppressed to avoid
  duplicating the root cause.
- Only the first kernel error is captured (the kernel stops at the first failure).
- Unknown rule names ("`rule 'X' is not available`") are **not** classified as
  `InvalidTransition`; they are a different failure category.

---

### `TypeMismatch`

**Origin:** Pass 3 (infrastructure; no surface trigger in v1)
**Severity:** error
**Category:** type/sort

**Meaning:** A sort-level mismatch was detected: a formula appeared where a term
(or vice versa) was expected.

**v1 status:** The `TypeMismatch` code is stable and can be instantiated directly
(`Diagnostic("TypeMismatch", ..., ..., "error")`), but the Stele v1 grammar does not
have a term language. All parsed expressions are `Sort.FORMULA`, so `TypeMismatch`
has no surface trigger in v1.

The underlying infrastructure (`stele/types.py`) is present:

```python
from stele.types import Sort, infer_sort, check_sort_compat

infer_sort(Var("P"))        # Sort.FORMULA
check_sort_compat(f, Sort.TERM)  # raises ValueError with "sort mismatch"
```

**Future:** When arithmetic or algebraic terms are introduced, `TypeMismatch` will
fire when a term appears in a formula position.

---

## Benchmark Coverage

The v1 benchmark seed (`bench/labels.jsonl`) covers the following codes:

| Code | Tasks with this code | Notes |
|------|---------------------|-------|
| `UndefinedSymbol` | 2 | — |
| `MissingHypothesis` | 3 | forward ref, subproof escape, or_elim subproof |
| `UnsupportedConclusion` | 2 | — |
| `CircularDependency` | 0 | not representable via surface syntax; unit-test only |
| `UnusedAssumption` | 2 | check still passes (warning) |
| `UndefinedDefinition` | 2 | check still passes (warning) |
| `InvalidTransition` | 3 | mp type mismatch, and_elim wrong side, mp non-implication |
| `TypeMismatch` | 0 | no surface trigger in v1; unit-test only |

---

## Adding a New Benchmark Task

1. Create `bench/tasks/<task_id>.stele` with the proof content.
2. Add a JSONL record to `bench/labels.jsonl`:
   ```json
   {"id":"<task_id>","path":"tasks/<task_id>.stele","logic":"<logic>",
    "expected_valid":<true|false>,"expected_codes":[...],
    "description":"...", "tags":["..."]}
   ```
3. Run the harness to verify the label is correct:
   ```
   python -m stele.eval bench --labels bench/labels.jsonl --tasks bench -v
   ```
4. If the task passes, the label is consistent with the current implementation.

**Honesty requirement:** `expected_valid` and `expected_codes` must reflect what
the implementation actually produces, not what you wish it produced. Run the harness
to verify before committing.
