# 03 — Stele-Light Language and Kernel

**Status:** Stable
**Evidence:** `stele/kernel.py`, `stele/logic.py`, `stele/parser.py`
**Doc:** `GUIDE.md`, `docs/semantics.md`
**Tests:** `tests/test_kernel_valid.py`, `tests/test_kernel_invalid.py`, `tests/test_parser.py`

---

## 3.1 The Stele-Light proof format

A Stele-Light proof consists of a theorem declaration followed by a sequence of labeled
steps.

### Grammar (EBNF, from `docs/semantics.md`)

```ebnf
proof       ::= "theorem" IDENT ("using" logic_name)? ":" body
body        ::= step*
step        ::= assume_step | suppose_block | have_step | conclude_step

assume_step    ::= "assume" IDENT ":" formula
suppose_block  ::= "suppose" IDENT ":" formula NEWLINE indent body dedent
have_step      ::= "have" IDENT ":" formula "by" rule_app
conclude_step  ::= "conclude" formula "by" IDENT
rule_app       ::= rule_name IDENT*
logic_name     ::= IDENT
```

**Formula grammar** (from `docs/semantics.md §2.2`):

```ebnf
formula     ::= quantifier | implication
quantifier  ::= ("forall" | "exists") VAR "." formula   (* proof-term level only *)
implication ::= disjunction ("->" formula)?
disjunction ::= conjunction ("or" conjunction)*
conjunction ::= negation  ("and" negation)*
negation    ::= "not" negation | atom
atom        ::= VAR | "false" | "(" formula ")"
```

**Precedence** (low to high): `->` < `or` < `and` < `not`

`not A` is syntactic sugar for `A -> false` (internal form: `Op("imp", (A, Op("bot", ())))`).

---

## 3.2 Minimal example — modus ponens

```
theorem mp_example:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
  conclude Q by h3
```

**Logic:** `intuitionistic_prop` (default) or `classical_prop`
**Rule applied:** `mp` (modus ponens, →E)
**Expected result:** `OK Proof verified`
**Tested:** yes, in `tests/test_kernel_valid.py`

---

## 3.3 Classical vs intuitionistic

The same proof script may be accepted under one logic and rejected under another.

### Example: double-negation elimination (dne)

```
theorem dne_consequent:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
```

Source: `examples/dne.stele`

| Logic | Result |
|-------|--------|
| `classical_prop` | `OK Proof verified: dne_consequent` |
| `intuitionistic_prop` | `FAIL: rule 'dne' is not available in logic 'intuitionistic_prop'` |

Source of this output: `RESULTS.md` §상대성.

This behavior is the primary demonstration of **rule relativity**: validity is relative
to the chosen rule set, not an absolute property of the formula.

---

## 3.4 Complete rule set

### Intuitionistic rules (12)

| Rule name | Natural deduction rule | Type |
|-----------|----------------------|------|
| `copy` | identity (reiteration) | non-discharging |
| `mp` | →E (modus ponens) | non-discharging |
| `imp_intro` | →I | **discharging** (discharges 1 assumption) |
| `and_intro` | ∧I | non-discharging |
| `and_elim_left` | ∧E₁ | non-discharging |
| `and_elim_right` | ∧E₂ | non-discharging |
| `neg_elim` | ¬E: from A and ¬A derive ⊥ | non-discharging |
| `ex_falso` | ⊥E (ex falso quodlibet) | non-discharging |
| `or_intro_left` | ∨I₁ | non-discharging |
| `or_intro_right` | ∨I₂ | non-discharging |
| `neg_intro` | ¬I: [A]…⊥ ⊢ ¬A | **discharging** (discharges 1 assumption) |
| `or_elim` | ∨E: A∨B, [A]…C, [B]…C ⊢ C | **discharging** (discharges 2 assumptions) |

### Classical-only rules (+3)

| Rule name | Natural deduction rule | Type |
|-----------|----------------------|------|
| `dne` | ¬¬A ⊢ A (double-negation elimination) | non-discharging |
| `lem` | ⊢ A ∨ ¬A (law of excluded middle) | non-discharging |
| `pbc` | [¬A]…⊥ ⊢ A (proof by contradiction) | **discharging** |

`classical_prop = intuitionistic_prop ∪ {dne, lem, pbc}`

**Module:** `stele/logic.py`
**Doc:** `GUIDE.md` §9, `docs/semantics.md`
**Test:** `tests/test_kernel_valid.py` (each rule tested individually),
         `tests/test_kernel_invalid.py` (each rule misuse rejected)

---

## 3.5 How the kernel works

The kernel (`stele/kernel.py`) operates by syntactic pattern matching:

1. **Parse** the proof script into a tree of `Assume`, `Suppose`, `Have`, `Conclude` nodes.
2. **Walk** the tree top-down.
3. **For each `have` step:** look up the rule name in the current logic's rule schemas.
   Apply `match(rule_schema, step)` — purely syntactic unification of pattern variables.
4. **For discharging rules:** verify that the discharged labels are in scope and were
   introduced by a `suppose` block.
5. **For the `conclude` step:** verify that the stated formula matches a previously derived
   formula.

**Key property:** The kernel performs no semantic reasoning. It does not evaluate formulas
in any model. It does not search for proofs. It does not call the matrix or Kripke layers.

**Module:** `stele/kernel.py`

---

## 3.6 Suppose blocks and discharge

Subproof blocks (`suppose ... conclude`) introduce temporary assumptions:

```
theorem neg_intro_demo:
  suppose h1: P and not P          # introduce assumption h1
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h1 h4   # discharge h1
  conclude not (P and not P) by h5
```

Source: `examples/neg_intro.stele`

The `neg_intro h1 h4` step **discharges** `h1`. After discharge, `h1` is no longer in
scope. The `conclude` step uses the discharged result `h5`.

---

## 3.7 Gallery

The public gallery has 15 curated examples in three categories:

| Category | Count | Description |
|----------|-------|-------------|
| `basics` | 7 | Valid IPL proofs: `imp_self`, `and`, `neg_intro`, `ex_falso`, `or_comm`, `imp_chain`, `neg_elim` |
| `classical` | 3 | Classical-only proofs that fail under IPL: `dne`, `lem`, `peirce` |
| `diagnostics` | 5 | Error cases: type mismatch, scope error, unused assumption, undefined symbol, wrong conclusion |

**Source:** `site/examples_gallery.json`
**Test:** `tests/test_gallery.py` — all 15 examples re-verified against the live kernel
on every CI run.

---

## 3.8 Limitations

- **Propositional only.** The surface language has no quantifiers (`forall`, `exists`).
  FOL is available only at the proof-term level (`stele/core/fol.py`).
- **No equality or function symbols.** No `=` relation, no terms.
- **No proof search.** The user must write every step; the kernel only checks.
- **No tactic language.** No `intro`, `apply`, `simp`, or similar tactics.
- **No module system.** Each proof file is self-contained.
- **No type polymorphism.** Formulas contain propositional variables only.
