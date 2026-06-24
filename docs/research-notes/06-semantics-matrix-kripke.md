# 06 — Semantics: ⊢ vs ⊨, Matrix Logics, and Kripke

**Status:** Demo (matrix), Experimental (Kripke)
**Evidence:** `stele/matrix.py`, `stele/world.py`, `stele/kripke.py`
**Doc:** `docs/semantics.md §3`, `RESULTS.md`
**Tests:** `tests/test_matrix.py`, `tests/test_rule_soundness.py`, `tests/test_kripke.py`,
           `tests/test_kripke_integration.py`, `tests/test_world.py`

---

## 6.1 The ⊢ vs ⊨ distinction

Stele maintains a strict architectural separation between:

$$\Gamma \vdash \varphi \quad \text{(syntactic derivability)} \qquad \text{vs} \qquad \Gamma \models \varphi \quad \text{(semantic validity)}$$

| Symbol | Meaning in Stele | Where |
|--------|-----------------|-------|
| $\vdash$ | The kernel has verified a proof of $\varphi$ from $\Gamma$ using the chosen rule set | `stele/kernel.py` |
| $\models_M$ | $\varphi$ evaluates to a designated value in matrix $M$ for all valuations | `stele/matrix.py` |
| $\models_K$ | $\varphi$ is forced at all worlds in all frames of a given class | `stele/kripke.py` |

**Import invariant:** `kernel.py` never imports `matrix.py` and `matrix.py` never imports
`kernel.py`. This is enforced by `tests/test_regression_invariants.py`.

The rule soundness checker connects these two sides: it asks whether each syntactic rule
**preserves** designated values in a given matrix.

---

## 6.2 Many-valued matrix semantics

### Boolean (classical two-valued)

| Value | Designated? |
|-------|------------|
| T | Yes |
| F | No |

Standard classical truth tables. Baseline for soundness checks.

### K3 — Strong Kleene three-valued logic

| Value | Designated? |
|-------|------------|
| T | Yes |
| I (indeterminate) | No |
| F | No |

Key K3 tables (from `stele/matrix.py`, locked by `test_k3_imp_table_matches_manifesto`):

$$\begin{array}{c|ccc}
A \to B & T & I & F \\\hline
T & T & I & F \\
I & T & I & I \\
F & T & T & T
\end{array}$$

**LEM failure in K3:** When $A = I$, $\neg A = I$, and $A \lor \neg A = I \notin \{T\}$.
Therefore LEM is not a K3 tautology.

**Reference:** Kleene 1952 [Kleene1952]

### LP — Logic of Paradox

Same truth tables as K3, but the designated set is $\{T, I\}$.

| Value | Designated? |
|-------|------------|
| T | Yes |
| I (both true and false) | **Yes** |
| F | No |

LP is paraconsistent: both $A$ and $\neg A$ can be true (value $I$) without trivializing
the system. **Reference:** Priest 1979 [Priest1979]

---

## 6.3 Rule soundness checker

`rule_soundness(logic, matrix)` checks each non-discharging rule of `logic` against the
designated values of `matrix`:

A rule $\varphi_1, \ldots, \varphi_n \vdash \psi$ is **sound** in matrix $M$ iff
for every valuation $v$:
$$\text{If } v(\varphi_i) \in D_M \text{ for all } i, \text{ then } v(\psi) \in D_M$$

**CLI:** `python -m stele.cli soundness --logic classical_prop --matrix K3`

Sample output (from `RESULTS.md`):
```
soundness  [logic: classical_prop | matrix: K3]
  and_elim_left: sound
  dne: sound
  lem: unsound  counterexample: A=I
  mp: sound
  neg_elim: sound
```

Note: `lem` is syntactically valid in `classical_prop` but semantically unsound in K3.
This is the key demonstration of the ⊢/⊨ separation.

**Status:** Demo / Diagnostic
**Test:** `tests/test_rule_soundness.py`

---

## 6.4 World and lattice demo

**Module:** `stele/world.py`

`World(matrix_name, axioms)` represents a semantic world with a named matrix and a set
of assumed formulas.

`status(φ, world)` returns one of:

| Status | Meaning |
|--------|---------|
| `PROVABLE` | $\varphi$ follows from the axioms in matrix $M$ |
| `REFUTABLE` | $\neg\varphi$ follows from the axioms |
| `BOTH` | Both $\varphi$ and $\neg\varphi$ follow (LP paraconsistency) |
| `INDEPENDENT` | Neither follows |

`lattice_status(φ, worlds)` queries multiple worlds and returns a cross-world summary.

**CLI:** `python -m stele.cli lattice P`

Sample output (from `RESULTS.md`):
```
lattice  [formula: x | matrix: boolean]
  Gamma                  axioms: []        =>  INDEPENDENT
  Gamma + x              axioms: [x]       =>  PROVABLE
  Gamma + not x          axioms: [not x]   =>  REFUTABLE
```

**Important:** `PROVABLE` here means semantic entailment, not proof-term existence.
This demo is at the **matrix semantics** level, not the kernel level.

---

## 6.5 Kripke countermodel search

**Module:** `stele/kripke.py`
**Status:** Experimental

The Kripke semantics for intuitionistic propositional logic uses **Kripke frames**
$(W, \leq)$ where $W$ is a set of worlds and $\leq$ is a reflexive, transitive
accessibility relation (a partial order).

**Forcing condition** (from `docs/semantics.md`):

$$w \Vdash A \land B \iff w \Vdash A \text{ and } w \Vdash B$$
$$w \Vdash A \lor B \iff w \Vdash A \text{ or } w \Vdash B$$
$$w \Vdash A \to B \iff \forall v \geq w,\; v \Vdash A \implies v \Vdash B$$
$$w \Vdash \neg A \iff \forall v \geq w,\; v \not\Vdash A$$

**Algorithm:** `find_countermodel(formula, max_worlds=3)` enumerates all frames
with $|W| \leq \texttt{max\_worlds}$, all valuations, and checks whether forcing fails
at any root world.

### Key examples

| Formula | IPL provable? | K3 tautology? | Kripke countermodel? |
|---------|-------------|--------------|----------------------|
| `P -> P` | Yes | No | No (IPL provable) |
| `P or not P` (LEM) | No | No | Yes (3-world frame) |
| `not not P -> P` (DNE) | No | Yes | Yes (2-world frame) |
| `(P -> Q) -> P -> P` | Yes | — | No |

**CLI:** `python -m stele.cli kripke "P or not P"`

Sample output: a JSON description of the countermodel with worlds, accessibility, and
forcing assignments at each world.

**Limitation:**
- **Bounded:** searches frames up to `max_worlds` worlds. Default is 3–4.
- **Incomplete:** if no countermodel is found, this does not prove the formula is IPL-valid.
  It only shows no small countermodel exists.
- **Propositional only:** no quantifiers.

**Test:** `tests/test_kripke.py`, `tests/test_kripke_integration.py`

---

## 6.6 Figure notes for paper

**Planned Figure 4:** ⊢ vs ⊨ diagram showing:
- Left side: kernel checks proof script → PASS/FAIL
- Right side: matrix evaluates formula → designated or not
- Connecting arrow: "rule soundness checker"

**Planned Figure 5:** Kripke countermodel for LEM (P ∨ ¬P):
- Two worlds: $w_0 \leq w_1$
- $w_0 \not\Vdash P$, $w_1 \Vdash P$
- At $w_0$: $P$ not forced, $\neg P$ not forced (since $w_1 \Vdash P$)
- Therefore $P \lor \neg P$ not forced at $w_0$

Source for figures: `stele/kripke.py` output + `site/theory.html` SVG diagrams.
