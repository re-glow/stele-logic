"""stele.core — proof-term calculus for the intuitionistic propositional and
first-order fragment.

This package adds a Curry–Howard proof-term layer alongside the existing
rule-schema kernel.  It does not replace or modify the trusted kernel.

Public API:
    terms    — proof term constructors (TVar, Lam, App, Pair, ...,
                ForallIntro, ForallElim, ExistsIntro, ExistsElim)
    fol      — object terms (ObjVar, ObjConst) and FOL formula helpers
    typing   — bidirectional typechecking (infer, check, TypingError)
    reduce   — beta-reduction + object-variable substitution
    debruijn — nameless binder representation, α-equivalence, shift/subst
"""
from .terms import (
    TVar, Lam, App,
    Pair, Fst, Snd,
    Inl, Inr, Case,
    Abort,
    ForallIntro, ForallElim, ExistsIntro, ExistsElim,
)
from .fol import (
    ObjVar, ObjConst,
    fol_free_obj_vars, obj_term_vars,
    subst_obj, subst_obj_in_obj_term,
    formula_alpha_equiv_fol,
)
from .typing import (
    infer, check,
    TypingError,
    Context, empty_ctx, extend,
    normalize_neg, is_imp, is_and, is_or, is_false, mk_not,
)
from .reduce import (
    free_vars, substitute, step, normalize, is_normal, ReductionError,
    obj_free_in_term, subst_obj_in_term,
)
from .debruijn import (
    DBBound, DBFree, DBLam, DBApp, DBPair, DBFst, DBSnd,
    DBInl, DBInr, DBCase, DBAbort,
    DBForallIntro, DBForallElim, DBExistsIntro, DBExistsElim,
    to_debruijn, from_debruijn,
    shift, subst, subst_top,
    alpha_equiv,
)

__all__ = [
    # propositional proof terms
    "TVar", "Lam", "App",
    "Pair", "Fst", "Snd",
    "Inl", "Inr", "Case",
    "Abort",
    # first-order proof terms
    "ForallIntro", "ForallElim", "ExistsIntro", "ExistsElim",
    # object terms and FOL formula helpers
    "ObjVar", "ObjConst",
    "fol_free_obj_vars", "obj_term_vars",
    "subst_obj", "subst_obj_in_obj_term",
    "formula_alpha_equiv_fol",
    # typing
    "infer", "check",
    "TypingError",
    "Context", "empty_ctx", "extend",
    "normalize_neg", "is_imp", "is_and", "is_or", "is_false", "mk_not",
    # reduction
    "free_vars", "substitute", "step", "normalize", "is_normal", "ReductionError",
    "obj_free_in_term", "subst_obj_in_term",
    # de Bruijn (propositional)
    "DBBound", "DBFree", "DBLam", "DBApp", "DBPair", "DBFst", "DBSnd",
    "DBInl", "DBInr", "DBCase", "DBAbort",
    # de Bruijn (first-order proof-variable layer)
    "DBForallIntro", "DBForallElim", "DBExistsIntro", "DBExistsElim",
    "to_debruijn", "from_debruijn",
    "shift", "subst", "subst_top",
    "alpha_equiv",
]
