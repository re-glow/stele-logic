# 05 — Diagnostics and Proof State

**Status:** Untrusted (diagnostics); Untrusted (proof state)
**Evidence:** `stele/diagnostics.py`, `stele/proofstate.py`, `stele/proofgraph.py`
**Doc:** `docs/failure-modes.md` (if present), `docs/development-context.md §2`
**Tests:** `tests/test_diagnostics.py`, `tests/test_proofstate.py`

---

## 5.1 Design philosophy

Diagnostics in Stele are **structurally separated from the trusted kernel**.

The kernel returns only PASS or FAIL with a position. The diagnostic module performs
additional analysis to characterize *why* a proof failed and *where* the error is.

**Critical constraint:** Diagnostic output must never affect kernel soundness. A diagnostic
module bug can produce misleading output but cannot cause the kernel to accept an invalid
proof.

All diagnostic APIs are labeled `UNTRUSTED` in the codebase and documentation.

---

## 5.2 Structural diagnostics — four passes

`stele/diagnostics.py` implements four analysis passes:

| Pass | Name | Description |
|------|------|-------------|
| 1 | Definition scope | Check that all label definitions appear before use |
| 2 | Reference scope | Check that all references resolve to in-scope labels |
| 3 | Dependency graph | Build the step dependency graph; detect cycles |
| 4 | Kernel classification | Run kernel check; classify the resulting error code |

Pass 4 calls the kernel; if the kernel reports a failure, the diagnostic module maps it
to a structured diagnostic code.

---

## 5.3 Stable diagnostic codes (9 codes)

From `stele/errors.py` and `docs/development-context.md`:

| Code | Description | Example |
|------|-------------|---------|
| `UndefinedSymbol` | Propositional variable used before introduction | `assume h1: P and Q; have h2: R by copy h1` |
| `MissingHypothesis` | A referenced label is not in scope | `have h2: P by mp h99 h1` (h99 undefined) |
| `InvalidTransition` | Rule application does not match available hypotheses | `have h3: Q by mp h1` (mp requires 2 premises) |
| `UnsupportedConclusion` | The conclusion does not follow from stated steps | wrong formula in `conclude` |
| `UnusedAssumption` | An assumption is introduced but never referenced | warning-level |
| `UndefinedDefinition` | A definition name references an undefined symbol | formula references undefined predicate |
| `CircularDependency` | Dependency cycle detected in proof graph | step A depends on step B which depends on step A |
| `TypeMismatch` | Formula in step does not match the formula derivable by the rule | `and_elim_left h1` where h1: P → Q |
| `KripkeCountermodelFound` | Classical rule used with IPL; Kripke countermodel found | info-level (Pass 4) |

**Note:** `CircularDependency` and `TypeMismatch` are defined in the diagnostic system
but not yet surfaced by the v1 corpus generator (see `docs/benchmark-card.md`).

---

## 5.4 Dependency graph

**Module:** `stele/proofgraph.py`

The proof dependency graph records which `have` steps reference which prior steps.
Output is a Graphviz DOT string that can be visualized.

```python
from stele.proofgraph import build_proof_graph, to_dot
graph = build_proof_graph(theorem)
dot_str = to_dot(graph)
```

**CLI:** `python -m stele.cli graph examples/or_comm.stele`

The graph is also available in the browser Studio as a DOT export button.

**Use in paper:** Figure 3 (paper outline) is planned as a proof dependency graph
for the `or_comm` example.

---

## 5.5 Examples of diagnostic errors

### Missing hypothesis

```
theorem missing:
  have h1: P by mp h99 h0   # h99 undefined
  conclude P by h1
```

Source: `examples/diag_missing.stele`

Diagnostic: `MissingHypothesis` at `have h1`.

### Undefined symbol

```
theorem undef:
  assume h1: P
  have h2: Q by copy h1   # Q never introduced; P ≠ Q
  conclude Q by h2
```

Source: `examples/diag_undef.stele`

Diagnostic: `UndefinedSymbol` (Q not in scope) or `InvalidTransition` (P ≠ Q).

### Unused assumption

```
theorem unused_ex:
  assume h1: P
  assume h2: Q             # h2 is never referenced
  have h3: P by copy h1
  conclude P by h3
```

Source: `examples/diag_unused.stele`

Diagnostic: `UnusedAssumption` on `h2` (warning level).

---

## 5.6 Proof-state hints

**Module:** `stele/proofstate.py`
**Status:** Untrusted

The proof-state module analyzes a proof script and returns:

- The **current context** at each point (what formulas are in scope)
- **Rule hints**: which rules could plausibly apply next, given the current context

**Critical constraint:** All hints carry `trusted=False` always. The module does not
import `stele.kernel` or `stele.diagnostics`.

```python
from stele.proofstate import proof_state_from_text, suggest_rule_hints
state = proof_state_from_text(source)
hints = suggest_rule_hints(state)
# Each hint: RuleHint(rule_name=..., trusted=False)
```

**CLI:** `python -m stele.cli hints examples/neg_intro.stele`

**Limitation:** Structural pattern matching only. No proof search. Hints may be wrong;
they are advisory.

---

## 5.7 Untrusted policy

The following are explicitly untrusted and must be stated as such in any paper:

| Component | `trusted` flag | Cannot affect kernel? |
|-----------|---------------|----------------------|
| `diagnostics.py` | No `trusted` flag; doc says UNTRUSTED | Yes — kernel runs independently |
| `proofstate.py` | `RuleHint.trusted = False` always | Yes — does not import kernel |
| `kripke.py` | Experimental, no kernel link | Yes — kernel runs independently |
| `matrix.py` | Demo, no kernel link | Yes — import invariant enforced |
| `stele_ml/` | Optional, isolated | Yes — no kernel import |
