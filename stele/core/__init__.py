"""stele.core — proof-term calculus for the intuitionistic propositional fragment.

This package adds a Curry–Howard proof-term layer alongside the existing
rule-schema kernel.  It does not replace or modify the trusted kernel.

Public API:
    terms    — proof term constructors (TVar, Lam, App, Pair, ...)
    typing   — bidirectional typechecking (infer, check, TypingError)
    reduce   — beta-reduction (free_vars, substitute, step, normalize, is_normal)
    debruijn — nameless binder representation, α-equivalence, shift/subst
"""
from .terms import (
    TVar, Lam, App,
    Pair, Fst, Snd,
    Inl, Inr, Case,
    Abort,
)
from .typing import (
    infer, check,
    TypingError,
    Context, empty_ctx, extend,
    normalize_neg, is_imp, is_and, is_or, is_false, mk_not,
)
from .reduce import (
    free_vars, substitute, step, normalize, is_normal, ReductionError,
)
from .debruijn import (
    DBBound, DBFree, DBLam, DBApp, DBPair, DBFst, DBSnd,
    DBInl, DBInr, DBCase, DBAbort,
    to_debruijn, from_debruijn,
    shift, subst, subst_top,
    alpha_equiv,
)

__all__ = [
    "TVar", "Lam", "App",
    "Pair", "Fst", "Snd",
    "Inl", "Inr", "Case",
    "Abort",
    "infer", "check",
    "TypingError",
    "Context", "empty_ctx", "extend",
    "normalize_neg", "is_imp", "is_and", "is_or", "is_false", "mk_not",
    "free_vars", "substitute", "step", "normalize", "is_normal", "ReductionError",
    "DBBound", "DBFree", "DBLam", "DBApp", "DBPair", "DBFst", "DBSnd",
    "DBInl", "DBInr", "DBCase", "DBAbort",
    "to_debruijn", "from_debruijn",
    "shift", "subst", "subst_top",
    "alpha_equiv",
]
