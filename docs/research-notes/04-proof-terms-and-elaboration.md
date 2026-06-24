# 04 — Proof Terms and Elaboration

**Status:** Experimental
**Evidence:** `stele/core/`, `stele/elaborate.py`
**Doc:** `docs/proof-terms.md`, `docs/semantics.md §3`, `docs/metatheory.md`
**Tests:** `tests/test_elaboration.py`, `tests/test_proof_term_typing.py`,
           `tests/test_reduce.py`, `tests/test_debruijn.py`, `tests/test_fol.py`

---

## 4.1 Curry–Howard correspondence

The proof-term core implements the Curry–Howard correspondence for IPL:

| Logic | Type theory |
|-------|------------|
| Proposition $A$ | Type $A$ |
| Proof of $A$ | Term of type $A$ |
| $A \to B$ | Function type $A \to B$ |
| $A \land B$ | Product type $A \times B$ |
| $A \lor B$ | Sum type $A + B$ |
| $\bot$ (false) | Empty type |
| $\neg A$ | $A \to \bot$ |
| $\forall x.\, A(x)$ | Dependent function (Π-type approximation) |
| $\exists x.\, A(x)$ | Dependent pair (Σ-type approximation) |

**Reference:** Sørensen & Urzyczyn 2006 [SorensenUrzyczyn2006]
**Module:** `stele/core/terms.py`

---

## 4.2 Term constructors

All constructors are frozen Python dataclasses (`stele/core/terms.py`):

| Constructor | Logic operation | Python |
|-------------|----------------|--------|
| `TVar(name)` | hypothesis reference | variable |
| `Lam(var, var_type, body)` | →I (implication introduction) | λ-abstraction |
| `App(fn, arg)` | →E (modus ponens) | function application |
| `Pair(left, right)` | ∧I | product introduction |
| `Fst(pair)` | ∧E₁ | left projection |
| `Snd(pair)` | ∧E₂ | right projection |
| `Inl(term, right_type)` | ∨I₁ | left injection |
| `Inr(left_type, term)` | ∨I₂ | right injection |
| `Case(discriminant, lvar, lbranch, rvar, rbranch)` | ∨E | case split |
| `Abort(term, result_type)` | ⊥E (ex falso) | abort |

**Module:** `stele/core/terms.py`
**Test:** `tests/test_proof_term_typing.py`

---

## 4.3 Bidirectional type checking

The type checker (`stele/core/typing.py`) has two modes:

- **Infer mode** (`infer(ctx, term) → type`): synthesizes the type of a term
- **Check mode** (`check(ctx, term, expected_type) → bool`): verifies a term has a given type

```python
# Example: check that (λx:P. x) has type P → P
ctx = {}
term = Lam("x", Var("P"), TVar("x"))
expected = Op("imp", (Var("P"), Var("P")))
assert check(ctx, term, expected)
```

The bidirectional architecture is standard; see Pierce & Turner 1998 [PierceT98].
Stele's version is a simple specialization for propositional IPL without polymorphism.

**Status:** Experimental (simply-typed; no polymorphism, no dependent types)

---

## 4.4 β-reduction and normalization

**Module:** `stele/core/reduce.py`

Reduction rules (from `docs/semantics.md §4`):

$$(\lambda x{:}A.\,t)\,u \;\longrightarrow_\beta\; t[u/x] \quad (\beta_{\to})$$

$$\mathtt{fst}(\mathtt{pair}(a, b)) \;\longrightarrow_\beta\; a \quad (\beta_{\land_1})$$

$$\mathtt{snd}(\mathtt{pair}(a, b)) \;\longrightarrow_\beta\; b \quad (\beta_{\land_2})$$

$$\mathtt{case}(\mathtt{inl}(a), x, l, y, r) \;\longrightarrow_\beta\; l[a/x] \quad (\beta_{\lor_l})$$

$$\mathtt{case}(\mathtt{inr}(b), x, l, y, r) \;\longrightarrow_\beta\; r[b/y] \quad (\beta_{\lor_r})$$

Implementation: call-by-name with a fuel counter (default 1000 steps).
η-reduction is not implemented.

**Normalization claim:** For STLC (simply-typed lambda calculus), all typeable terms
normalize (standard metatheory; see e.g., Sørensen & Urzyczyn 2006). The fuel guard
provides a practical bound that catches non-normalizing situations.
**Caveat:** Not machine-checked; supported by regression tests.

**Test:** `tests/test_reduce.py`, optional `tests/test_proof_term_properties.py` (Hypothesis)

---

## 4.5 de Bruijn indices

**Module:** `stele/core/debruijn.py`

Provides conversion between **named** and **de Bruijn** representations:

- `to_debruijn(term, ctx)` — convert named term to de Bruijn indices
- `from_debruijn(db_term, ctx)` — convert back to named term
- `alpha_equiv(t1, t2)` — α-equivalence via de Bruijn (proof variables only)

Variable capture-avoidance is handled by index shifting during substitution.

**Limitation:** Object-level FOL variables remain named; proof-variable de Bruijn
conversion is implemented.

---

## 4.6 FOL proof-term fragment

**Module:** `stele/core/fol.py`
**Status:** Experimental

Extends the IPL proof-term calculus with FOL quantifiers:

| Constructor | Logic operation |
|-------------|----------------|
| `ForallIntro(obj_var, body)` | ∀I (universal introduction) |
| `ForallElim(term, witness)` | ∀E (universal elimination) |
| `ExistsIntro(formula, witness, body)` | ∃I (existential introduction) |
| `ExistsElim(term, obj_var, pf_var, body)` | ∃E (existential elimination) |

**Freshness condition for `ExistsElim`:** The `obj_var` must not appear free in the
conclusion formula. This is enforced in the FOL type checker.

**Limitation:** No surface language support for quantifiers. FOL is proof-term level
only. No equality or function symbols.

**Test:** `tests/test_fol.py`

---

## 4.7 Classical negative translation bridge

**Module:** `stele/core/classical_experimental.py`
**Status:** Experimental

Implements the Gödel–Gentzen double-negation translation at the **formula level**:

$$\phi^N = \text{double-negation translation of } \phi$$

The translation converts a classical formula to an intuitionistic formula such that
provability is preserved:

$$\text{CPC} \vdash \phi \implies \text{IPC} \vdash \phi^N$$

**API:** `negative_translate_formula(formula)`, `check_negative_translation(formula)`

**Limitation:**
- Formula-level translation only.
- Does not produce a proof term for the translated formula.
- λμ-calculus / continuation-style classical proof terms are **not** implemented.
- Not part of the kernel or the trusted path.

**Test:** `tests/test_classical_experimental.py`

---

## 4.8 Script-to-term elaboration

**Module:** `stele/elaborate.py`
**Status:** Experimental (IPL only)

`crosscheck_theorem(theorem, logic)` runs three passes:

1. **Kernel pass:** `kernel.check_proof()` — syntactic check
2. **Elaboration pass:** `_elaborate_rule()` — constructs a proof term for each step
3. **Type-check pass:** `core.typing.check()` — verifies the term has the expected type

If all three pass, `CrossCheckResult.ok == True`.

**What elaboration supports:** all 12 intuitionistic rules.
**What elaboration does NOT support:** classical rules (`dne`, `lem`, `pbc`),
FOL proof-term level, K3/LP matrix logics.

**Example:**

```
theorem imp_self using intuitionistic_prop:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h2
  conclude P -> P by h3
```

Elaborated term: `Lam("h1", P, TVar("h1"))` (identity function on type P).

Source: `examples/elaborate_identity.stele`

---

## 4.9 Metatheory claims (honest status)

The following are the official metatheory claims from `docs/metatheory.md`.
**None are machine-verified.** All are supported by regression tests and/or proof sketches.

| # | Claim | Status |
|---|-------|--------|
| 1 | Elaboration soundness | Regression tests + proof sketch |
| 2 | Subject reduction (type preservation) | Proof sketch + regression/property tests |
| 3 | Normalization (STLC terminates) | Standard metatheory citation; fuel guard implementation |
| 4 | Local confluence | Deferred tests; full proof absent |
| 5 | Core consistency (no closed term of type ⊥) | Proof sketch + generative tests |
| 6 | Classical exclusion (no classical rules in IPL elaboration) | Architecture invariant + regression tests |
| 7 | Matrix separation (kernel ⊬ matrix) | Import invariant enforced by test |
| FOL-1 | ForallIntro/Elim subject reduction | Proof sketch + regression tests |
| FOL-2 | ExistsElim freshness enforcement | Regression tests |

**Safe wording:** "supported by regression tests" or "proof sketch (not machine-checked)."
**Unsafe wording:** "formally verified," "machine-checked," "proven."
