"""First-order fragment: object terms and formula-level helpers.

This module adds the object-term layer and capture-avoiding substitution in
formulas needed by the FOL proof-term extension (ForallIntro/Elim,
ExistsIntro/Elim in stele.core.terms).

It does NOT touch the trusted kernel, matrix semantics, or the proof-script
checker.  It is an optional extension layer alongside the propositional core.

Object terms (v1)
-----------------
ObjVar(name)   — an object variable; can be bound by Forall/Exists binders or
                 left free (acts as a constant when never bound).
ObjConst(name) — an explicitly declared constant; never bound by quantifiers.

In practice, the parser produces ObjVar for all object terms in predicate
arguments.  ObjConst can be constructed programmatically to mark constants
that should never be substituted.

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

formula_alpha_equiv_fol(f1, f2) -> bool
    α-equivalence for first-order formulas (object-variable renaming).
    Propositional connectives are compared structurally after negation
    normalisation.

Design note — two-namespace de Bruijn (future)
-----------------------------------------------
Object-variable binders (Forall, Exists, ForallIntro, ExistsElim) are kept
named rather than de Bruijn indexed.  A separate de Bruijn index space for
object variables (to_debruijn_fol) is left for a future extension.  The
existing proof-variable de Bruijn layer (stele.core.debruijn) is unaffected.
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
# Formula α-equivalence (object-variable level)
# ---------------------------------------------------------------------------

def formula_alpha_equiv_fol(f1, f2) -> bool:
    """Return True iff f1 and f2 are α-equivalent as first-order formulas.

    Equality is checked modulo renaming of bound object variables in
    Forall and Exists.  Propositional structure is compared structurally
    (negation is NOT normalised here; use _feq from typing.py if needed).

    Free object variable names MUST match exactly (as in standard α-equivalence).
    """
    if type(f1) != type(f2):
        return False
    if isinstance(f1, Var):
        return f1.name == f2.name
    if isinstance(f1, Pred):
        return f1.name == f2.name and f1.args == f2.args
    if isinstance(f1, Forall):
        if f1.var == f2.var:
            return formula_alpha_equiv_fol(f1.body, f2.body)
        # Rename f2.var → f1.var in f2.body, then compare
        f2_renamed = subst_obj(f2.body, f2.var, ObjVar(f1.var))
        return formula_alpha_equiv_fol(f1.body, f2_renamed)
    if isinstance(f1, Exists):
        if f1.var == f2.var:
            return formula_alpha_equiv_fol(f1.body, f2.body)
        f2_renamed = subst_obj(f2.body, f2.var, ObjVar(f1.var))
        return formula_alpha_equiv_fol(f1.body, f2_renamed)
    if isinstance(f1, Op):
        if f1.sym != f2.sym or len(f1.args) != len(f2.args):
            return False
        return all(formula_alpha_equiv_fol(a, b) for a, b in zip(f1.args, f2.args))
    return f1 == f2
