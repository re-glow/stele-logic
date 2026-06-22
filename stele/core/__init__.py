"""stele.core — proof-term calculus for the intuitionistic propositional fragment.

This package adds a Curry–Howard proof-term layer alongside the existing
rule-schema kernel.  It does not replace or modify the trusted kernel.

Public API:
    terms   — proof term constructors (TVar, Lam, App, Pair, ...)
    typing  — bidirectional typechecking (infer, check, TypingError)
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

__all__ = [
    "TVar", "Lam", "App",
    "Pair", "Fst", "Snd",
    "Inl", "Inr", "Case",
    "Abort",
    "infer", "check",
    "TypingError",
    "Context", "empty_ctx", "extend",
    "normalize_neg", "is_imp", "is_and", "is_or", "is_false", "mk_not",
]
