"""First-order fragment: object terms and formula-level helpers.

This module adds the object-term layer and capture-avoiding substitution in
formulas needed by the FOL proof-term extension (ForallIntro/Elim,
ExistsIntro/Elim in stele.core.terms).

It does NOT touch the trusted kernel, matrix semantics, or the proof-script
checker.  It is an optional extension layer alongside the propositional core.

Object terms (named)
--------------------
ObjVar(name)   — an object variable; can be bound by Forall/Exists binders or
                 left free (acts as a constant when never bound).
ObjConst(name) — an explicitly declared constant; never bound by quantifiers.

In practice, the parser produces ObjVar for all object terms in predicate
arguments.  ObjConst can be constructed programmatically to mark constants
that should never be substituted.

Object terms (nameless)
-----------------------
ObjBound(index) — bound object variable in de Bruijn form; index 0 = innermost
ObjFree(name)   — free object variable in de Bruijn form

These appear only in DB formula types (DBPredF args).

Formula-level operations
------------------------
fol_free_obj_vars(formula) -> set[str]
    Object variable names that appear free in formula.

obj_term_vars(obj_term) -> set[str]
    Variable names in an object term (ObjVar only; ObjConst contributes none).

subst_obj(formula, var_name, obj_term) -> Formula
    Capture-avoiding substitution in formulas: formula[obj_term / var_name].
    Renames quantifier binders that would capture a free variable of obj_term.

subst_obj_in_obj_term(obj_term, var_name, replacement) -> ObjTerm
    Substitute within an object term (replaces ObjVar(var_name) only).

to_debruijn_formula(formula, obj_ctx=None) -> DBFormula
    Translate a named formula to its de Bruijn (nameless) form.
    Two formulas are α-equivalent iff their DB forms are equal.

from_debruijn_formula(db_formula, obj_ctx=None) -> Formula
    Translate a de Bruijn formula back to a named formula (roundtrip).

alpha_equiv_formula(f1, f2) -> bool
    α-equivalence using de Bruijn comparison — sound for all shadowing cases.
    Supersedes formula_alpha_equiv_fol (which now delegates here).

formula_alpha_equiv_fol(f1, f2) -> bool
    Retained for backwards compatibility; delegates to alpha_equiv_formula.

Design note — two namespaces
-----------------------------
Proof-variable binders (Lam, Case, ExistsElim.proof_var) are handled by the
de Bruijn layer in stele.core.debruijn (proof-variable index space).
Object-variable binders (Forall, Exists, ForallIntro.obj_var, ExistsElim.obj_var)
are handled at the formula level by to_debruijn_formula (object-variable index
space).  The two index spaces are completely separate: neither affects the other.
"""
from dataclasses import dataclass
from stele.ast import Var, Op, Pred, Forall, Exists


# ---------------------------------------------------------------------------
# Object terms
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObjVar:
    """Object-language variable.  May be bound by a quantifier or left free."""
    name: str

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class ObjConst:
    """Object-language constant.  Never bound; not substituted by subst_obj."""
    name: str

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Free-variable helpers
# ---------------------------------------------------------------------------

def obj_term_vars(obj_term) -> set:
    """Return the set of variable names in an object term.

    ObjConst contributes no names (it is a constant, not a variable).
    """
    if isinstance(obj_term, ObjVar):
        return {obj_term.name}
    return set()  # ObjConst or unknown


def fol_free_obj_vars(formula) -> set:
    """Return the set of free object variable names in a formula.

    Traverses Pred args (ObjVar), Op args recursively, and Forall/Exists
    with binding: the bound variable is removed from the body's free set.
    """
    if isinstance(formula, Var):
        return set()  # propositional variable — no object variables
    if isinstance(formula, Pred):
        result = set()
        for a in formula.args:
            result |= obj_term_vars(a)
        return result
    if isinstance(formula, Forall):
        return fol_free_obj_vars(formula.body) - {formula.var}
    if isinstance(formula, Exists):
        return fol_free_obj_vars(formula.body) - {formula.var}
    if isinstance(formula, Op):
        result = set()
        for a in formula.args:
            result |= fol_free_obj_vars(a)
        return result
    return set()


# ---------------------------------------------------------------------------
# Fresh-name generator
# ---------------------------------------------------------------------------

def _fresh_obj(name, avoid):
    """Return a name similar to `name` that is not in `avoid`."""
    if name not in avoid:
        return name
    i = 0
    while True:
        cand = f"{name}_{i}"
        if cand not in avoid:
            return cand
        i += 1


# ---------------------------------------------------------------------------
# Object-variable substitution in formulas
# ---------------------------------------------------------------------------

def subst_obj_in_obj_term(obj_term, var_name, replacement):
    """Replace ObjVar(var_name) with replacement in an object term."""
    if isinstance(obj_term, ObjVar) and obj_term.name == var_name:
        return replacement
    return obj_term  # ObjConst and non-matching ObjVar are unchanged


def subst_obj(formula, var_name, replacement):
    """Capture-avoiding substitution in formulas: formula[replacement / var_name].

    Replaces free occurrences of ObjVar(var_name) inside Pred argument lists.
    When a Forall/Exists binder re-binds var_name, substitution stops there.
    When the binder name appears free in replacement, the binder is α-renamed
    before descending to avoid capture.

    Parameters
    ----------
    formula     : Formula (Var | Op | Pred | Forall | Exists)
    var_name    : str       — the object variable to replace
    replacement : ObjTerm   — the term to substitute in

    Returns
    -------
    Formula (with all free occurrences of ObjVar(var_name) replaced)
    """
    if isinstance(formula, Var):
        return formula  # propositional variable — no object terms inside

    if isinstance(formula, Pred):
        new_args = tuple(subst_obj_in_obj_term(a, var_name, replacement)
                         for a in formula.args)
        return Pred(formula.name, new_args) if new_args != formula.args else formula

    if isinstance(formula, Forall):
        if formula.var == var_name:
            return formula  # shadowed — var_name is re-bound here
        repl_vars = obj_term_vars(replacement)
        if formula.var in repl_vars:
            # Rename the binder to avoid capture
            avoid = repl_vars | fol_free_obj_vars(formula.body) | {var_name}
            new_var = _fresh_obj(formula.var, avoid)
            renamed_body = subst_obj(formula.body, formula.var, ObjVar(new_var))
            return Forall(new_var, subst_obj(renamed_body, var_name, replacement))
        return Forall(formula.var, subst_obj(formula.body, var_name, replacement))

    if isinstance(formula, Exists):
        if formula.var == var_name:
            return formula
        repl_vars = obj_term_vars(replacement)
        if formula.var in repl_vars:
            avoid = repl_vars | fol_free_obj_vars(formula.body) | {var_name}
            new_var = _fresh_obj(formula.var, avoid)
            renamed_body = subst_obj(formula.body, formula.var, ObjVar(new_var))
            return Exists(new_var, subst_obj(renamed_body, var_name, replacement))
        return Exists(formula.var, subst_obj(formula.body, var_name, replacement))

    if isinstance(formula, Op):
        new_args = tuple(subst_obj(a, var_name, replacement) for a in formula.args)
        return Op(formula.sym, new_args) if new_args != formula.args else formula

    return formula  # unknown formula type — unchanged


# ---------------------------------------------------------------------------
# Nameless object-term representation (de Bruijn for object variables)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObjBound:
    """Bound object variable in de Bruijn nameless form.
    index 0 refers to the innermost enclosing Forall/Exists binder."""
    index: int

    def __str__(self):
        return f"#{self.index}"


@dataclass(frozen=True)
class ObjFree:
    """Free object variable in de Bruijn nameless form, identified by name."""
    name: str

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Nameless formula types (de Bruijn object-variable context)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DBFVarF:
    """Nameless propositional variable."""
    name: str


@dataclass(frozen=True)
class DBPredF:
    """Nameless predicate.  args: tuple of ObjBound | ObjFree | ObjConst."""
    name: str
    args: tuple


@dataclass(frozen=True)
class DBForallF:
    """Nameless universal quantifier.  The bound variable name is erased."""
    body: object  # DBFormula


@dataclass(frozen=True)
class DBExistsF:
    """Nameless existential quantifier.  The bound variable name is erased."""
    body: object  # DBFormula


@dataclass(frozen=True)
class DBOpF:
    """Nameless propositional connective."""
    sym: str
    args: tuple  # tuple[DBFormula]


# ---------------------------------------------------------------------------
# Translation helpers
# ---------------------------------------------------------------------------

def _translate_obj_term(obj_term, obj_ctx):
    """Translate a named object term to nameless form.

    obj_ctx is a list of bound variable names, innermost first.
    ObjVar whose name appears in obj_ctx → ObjBound(index).
    ObjVar whose name is not in obj_ctx → ObjFree(name).
    ObjConst is returned unchanged.
    """
    if isinstance(obj_term, ObjVar):
        try:
            idx = obj_ctx.index(obj_term.name)
            return ObjBound(idx)
        except ValueError:
            return ObjFree(obj_term.name)
    return obj_term  # ObjConst unchanged


def _untranslate_obj_term(obj_term, obj_ctx):
    """Translate a nameless object term back to named form.

    ObjBound(i) → ObjVar(obj_ctx[i]).
    ObjFree(name) → ObjVar(name).
    ObjConst is returned unchanged.

    Raises ValueError if an ObjBound index is out of scope.
    """
    if isinstance(obj_term, ObjBound):
        if obj_term.index >= len(obj_ctx):
            raise ValueError(
                f"ObjBound({obj_term.index}) is out of scope "
                f"(context depth {len(obj_ctx)})"
            )
        return ObjVar(obj_ctx[obj_term.index])
    if isinstance(obj_term, ObjFree):
        return ObjVar(obj_term.name)
    return obj_term  # ObjConst unchanged


# ---------------------------------------------------------------------------
# de Bruijn formula translation
# ---------------------------------------------------------------------------

def to_debruijn_formula(formula, obj_ctx=None):
    """Translate a named formula to its de Bruijn (nameless) form.

    Parameters
    ----------
    formula  : Formula (Var | Op | Pred | Forall | Exists)
    obj_ctx  : list[str] | None
        Bound object variable names in scope, innermost first.
        Pass None (or omit) at the top level.

    Returns
    -------
    A nameless formula built from DBFVarF / DBPredF / DBForallF /
    DBExistsF / DBOpF, with ObjVar replaced by ObjBound / ObjFree
    in Pred arguments.

    Two named formulas f1, f2 are α-equivalent iff::

        to_debruijn_formula(f1) == to_debruijn_formula(f2)

    This comparison is sound for all shadowing cases, including
    ``forall x. forall x. P(x)`` vs ``forall y. forall z. P(y)``
    (which differ because the inner P argument is bound at different
    depths), a case mishandled by renaming-based implementations.
    """
    if obj_ctx is None:
        obj_ctx = []

    if isinstance(formula, Var):
        return DBFVarF(formula.name)

    if isinstance(formula, Pred):
        return DBPredF(
            formula.name,
            tuple(_translate_obj_term(a, obj_ctx) for a in formula.args),
        )

    if isinstance(formula, Forall):
        return DBForallF(to_debruijn_formula(formula.body, [formula.var] + obj_ctx))

    if isinstance(formula, Exists):
        return DBExistsF(to_debruijn_formula(formula.body, [formula.var] + obj_ctx))

    if isinstance(formula, Op):
        return DBOpF(
            formula.sym,
            tuple(to_debruijn_formula(a, obj_ctx) for a in formula.args),
        )

    raise TypeError(
        f"to_debruijn_formula: unexpected formula type {type(formula).__name__!r}"
    )


def from_debruijn_formula(db_formula, obj_ctx=None):
    """Translate a de Bruijn formula back to a named formula.

    Generates fresh object variable names for each Forall/Exists binder.
    Useful for roundtrip tests and human-readable output.

    Parameters
    ----------
    db_formula : DBFormula (DBFVarF | DBPredF | DBForallF | DBExistsF | DBOpF)
    obj_ctx    : list[str] | None   — bound names in scope, innermost first
    """
    if obj_ctx is None:
        obj_ctx = []

    if isinstance(db_formula, DBFVarF):
        return Var(db_formula.name)

    if isinstance(db_formula, DBPredF):
        return Pred(
            db_formula.name,
            tuple(_untranslate_obj_term(a, obj_ctx) for a in db_formula.args),
        )

    if isinstance(db_formula, DBForallF):
        fresh = _fresh_obj("x", set(obj_ctx))
        return Forall(fresh, from_debruijn_formula(db_formula.body, [fresh] + obj_ctx))

    if isinstance(db_formula, DBExistsF):
        fresh = _fresh_obj("x", set(obj_ctx))
        return Exists(fresh, from_debruijn_formula(db_formula.body, [fresh] + obj_ctx))

    if isinstance(db_formula, DBOpF):
        return Op(
            db_formula.sym,
            tuple(from_debruijn_formula(a, obj_ctx) for a in db_formula.args),
        )

    raise TypeError(
        f"from_debruijn_formula: unexpected type {type(db_formula).__name__!r}"
    )


# ---------------------------------------------------------------------------
# α-equivalence (de Bruijn-based, sound for all shadowing cases)
# ---------------------------------------------------------------------------

def alpha_equiv_formula(f1, f2) -> bool:
    """Return True iff f1 and f2 are α-equivalent as first-order formulas.

    Uses de Bruijn structural comparison, which is sound for all shadowing
    cases.  Free object variable names must match exactly.

    Propositional connectives are compared structurally.  Negation is NOT
    normalised here; use ``_feq`` (stele.core.typing) when normalisation is
    needed.
    """
    try:
        return to_debruijn_formula(f1) == to_debruijn_formula(f2)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Formula α-equivalence (object-variable level)
# ---------------------------------------------------------------------------

def formula_alpha_equiv_fol(f1, f2) -> bool:
    """Return True iff f1 and f2 are α-equivalent as first-order formulas.

    Delegates to alpha_equiv_formula, which uses de Bruijn comparison for
    sound structural equality modulo bound variable renaming.

    Propositional structure is compared structurally (negation is NOT
    normalised here; use _feq from typing.py if needed).

    Free object variable names MUST match exactly.
    """
    return alpha_equiv_formula(f1, f2)
