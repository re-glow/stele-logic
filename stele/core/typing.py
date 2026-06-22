"""Bidirectional typechecker for the intuitionistic propositional proof-term
calculus defined in stele.core.terms.

Public API
----------
infer(ctx, term) -> Formula
    Synthesize the type of term in typing context ctx.
    Raises TypingError on failure.

check(ctx, term, expected_type) -> None
    Verify that term has type expected_type in ctx.
    Uses checking rules for introduction forms; falls back to
    infer + equality comparison for all other terms.
    Raises TypingError on failure.

Context helpers
---------------
Context   alias for dict[str, Formula]
empty_ctx()   -> Context
extend(ctx, var, ty) -> Context   (non-destructive)

Formula helpers
---------------
normalize_neg(f)   convert not A to (A -> false) recursively
is_imp / is_and / is_or / is_false
mk_not(f)          build not A as (A -> false)

Design notes
------------
* Negation is treated as abbreviation: not A = A -> false.
  normalize_neg converts Op("not", (A,)) to Op("imp", (A, Op("bot", ())))
  so that structural matching works uniformly.  Formula equality for
  type comparison always normalises both sides via _feq.

* All term constructors carry enough annotations for full type synthesis,
  so infer never fails for annotation-completeness reasons alone.  check
  provides checking-mode rules for introduction forms for better errors
  and to allow independent branch checking in Case.

* This module does not import stele.kernel and is not imported by it.
  The proof-term core is an independent layer alongside the rule-schema
  kernel (invariant preserved by the test suite).
"""
from stele.ast import Var as _FVar, Op, pretty

from .terms import (TVar, Lam, App,
                    Pair, Fst, Snd,
                    Inl, Inr, Case,
                    Abort)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class TypingError(Exception):
    """Raised when a proof term fails to type-check."""


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

Context = dict  # dict[str, Formula]


def empty_ctx() -> Context:
    """Return an empty typing context."""
    return {}


def extend(ctx: Context, var: str, ty) -> Context:
    """Return a new context with var bound to ty (non-destructive).

    Shadowing policy: a later binding for the same variable name masks
    any earlier binding.  The original ctx is not modified.
    """
    return {**ctx, var: ty}


# ---------------------------------------------------------------------------
# Formula helpers
# ---------------------------------------------------------------------------

def normalize_neg(f):
    """Recursively normalise 'not A' to '(A -> false)'.

    This implements the Curry–Howard convention that negation is an
    abbreviation for implication to bottom.  After normalisation, all
    formulas that represent negative propositions have the uniform shape
    Op("imp", (A, Op("bot", ()))).

    The original formula AST is not mutated; a new formula is returned.
    """
    if isinstance(f, Op):
        if f.sym == "not":
            return Op("imp", (normalize_neg(f.args[0]), Op("bot", ())))
        return Op(f.sym, tuple(normalize_neg(a) for a in f.args))
    return f


def _feq(a, b) -> bool:
    """Formula equality modulo negation normalisation."""
    return normalize_neg(a) == normalize_neg(b)


def is_imp(f) -> bool:
    """True if f is an implication or a negation (normalised to A -> false)."""
    n = normalize_neg(f)
    return isinstance(n, Op) and n.sym == "imp"


def is_and(f) -> bool:
    """True if f is a conjunction."""
    return isinstance(f, Op) and f.sym == "and"


def is_or(f) -> bool:
    """True if f is a disjunction."""
    return isinstance(f, Op) and f.sym == "or"


def is_false(f) -> bool:
    """True if f is bottom (false / ⊥)."""
    return isinstance(f, Op) and f.sym == "bot"


def mk_not(f):
    """Construct 'not A' in the normalised implication form (A -> false).

    This is the canonical representation used by the proof-term calculus.
    The Stele-Light AST form Op("not", (A,)) is also accepted everywhere
    in the type checker via normalize_neg.
    """
    return Op("imp", (f, Op("bot", ())))


# ---------------------------------------------------------------------------
# Type inference (synthesis)
# ---------------------------------------------------------------------------

def infer(ctx: Context, term):
    """Synthesise the type of term in typing context ctx.

    Every term constructor carries explicit type annotations so that type
    synthesis is always decidable without guessing.

    Returns: Formula
    Raises:  TypingError
    """
    if isinstance(term, TVar):
        if term.name not in ctx:
            raise TypingError(
                f"unbound variable '{term.name}'"
            )
        return ctx[term.name]

    if isinstance(term, Lam):
        extended = extend(ctx, term.var, term.var_type)
        B = infer(extended, term.body)
        return Op("imp", (term.var_type, B))

    if isinstance(term, App):
        fn_ty = infer(ctx, term.fn)
        fn_norm = normalize_neg(fn_ty)
        if not (isinstance(fn_norm, Op) and fn_norm.sym == "imp"):
            raise TypingError(
                f"application: function must have an implication type, "
                f"got {pretty(fn_ty)}"
            )
        A, B = fn_norm.args
        check(ctx, term.arg, A)
        return B

    if isinstance(term, Pair):
        A = infer(ctx, term.left)
        B = infer(ctx, term.right)
        return Op("and", (A, B))

    if isinstance(term, Fst):
        pair_ty = normalize_neg(infer(ctx, term.pair))
        if not (isinstance(pair_ty, Op) and pair_ty.sym == "and"):
            raise TypingError(
                f"fst: expected a conjunction type, "
                f"got {pretty(pair_ty)}"
            )
        return pair_ty.args[0]

    if isinstance(term, Snd):
        pair_ty = normalize_neg(infer(ctx, term.pair))
        if not (isinstance(pair_ty, Op) and pair_ty.sym == "and"):
            raise TypingError(
                f"snd: expected a conjunction type, "
                f"got {pretty(pair_ty)}"
            )
        return pair_ty.args[1]

    if isinstance(term, Inl):
        A = infer(ctx, term.value)
        return Op("or", (A, term.right_type))

    if isinstance(term, Inr):
        B = infer(ctx, term.value)
        return Op("or", (term.left_type, B))

    if isinstance(term, Case):
        s_ty = normalize_neg(infer(ctx, term.scrutinee))
        if not (isinstance(s_ty, Op) and s_ty.sym == "or"):
            raise TypingError(
                f"case: scrutinee must have a disjunction type, "
                f"got {pretty(s_ty)}"
            )
        A, B = s_ty.args
        lctx = extend(ctx, term.left_var, A)
        rctx = extend(ctx, term.right_var, B)
        C1 = infer(lctx, term.left_body)
        C2 = infer(rctx, term.right_body)
        if not _feq(C1, C2):
            raise TypingError(
                f"case: branch result types do not agree — "
                f"left branch has {pretty(C1)}, right branch has {pretty(C2)}"
            )
        return C1

    if isinstance(term, Abort):
        check(ctx, term.false_term, Op("bot", ()))
        return term.target_type

    raise TypingError(
        f"unknown term constructor: {type(term).__name__}"
    )


# ---------------------------------------------------------------------------
# Type checking
# ---------------------------------------------------------------------------

def check(ctx: Context, term, expected_type) -> None:
    """Check that term has type expected_type in ctx.

    Uses dedicated checking rules for introduction forms when the expected
    type matches the term's head constructor.  Falls back to synthesising
    the type and comparing for all other cases.

    Returns: None (success)
    Raises:  TypingError (failure)
    """
    exp_norm = normalize_neg(expected_type)

    # ── Pair checks against A and B ─────────────────────────────────────────
    if isinstance(term, Pair) and isinstance(exp_norm, Op) and exp_norm.sym == "and":
        A, B = exp_norm.args
        check(ctx, term.left, A)
        check(ctx, term.right, B)
        return

    # ── Lam checks against A -> B ────────────────────────────────────────────
    if isinstance(term, Lam) and isinstance(exp_norm, Op) and exp_norm.sym == "imp":
        A, B = exp_norm.args
        if not _feq(term.var_type, A):
            raise TypingError(
                f"lam: parameter type annotation {pretty(term.var_type)} "
                f"does not match expected antecedent {pretty(A)}"
            )
        extended = extend(ctx, term.var, term.var_type)
        check(extended, term.body, B)
        return

    # ── Inl checks against A or B ────────────────────────────────────────────
    if isinstance(term, Inl) and isinstance(exp_norm, Op) and exp_norm.sym == "or":
        A, B = exp_norm.args
        if not _feq(term.right_type, B):
            raise TypingError(
                f"inl: right-type annotation {pretty(term.right_type)} "
                f"does not match expected right disjunct {pretty(B)}"
            )
        check(ctx, term.value, A)
        return

    # ── Inr checks against A or B ────────────────────────────────────────────
    if isinstance(term, Inr) and isinstance(exp_norm, Op) and exp_norm.sym == "or":
        A, B = exp_norm.args
        if not _feq(term.left_type, A):
            raise TypingError(
                f"inr: left-type annotation {pretty(term.left_type)} "
                f"does not match expected left disjunct {pretty(A)}"
            )
        check(ctx, term.value, B)
        return

    # ── Case: check both branches against expected type ──────────────────────
    if isinstance(term, Case):
        s_ty = normalize_neg(infer(ctx, term.scrutinee))
        if not (isinstance(s_ty, Op) and s_ty.sym == "or"):
            raise TypingError(
                f"case: scrutinee must have a disjunction type, "
                f"got {pretty(s_ty)}"
            )
        A, B = s_ty.args
        check(extend(ctx, term.left_var, A),  term.left_body,  expected_type)
        check(extend(ctx, term.right_var, B), term.right_body, expected_type)
        return

    # ── Default: synthesise and compare ──────────────────────────────────────
    actual = infer(ctx, term)
    if not _feq(actual, expected_type):
        raise TypingError(
            f"type mismatch: expected {pretty(expected_type)}, "
            f"got {pretty(actual)}"
        )
