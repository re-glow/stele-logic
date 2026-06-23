"""FOL proof-term examples — universal quantifier (forall).

These examples use the experimental first-order proof-term fragment.
They are NOT Stele-Light proof scripts; they use the Python API directly.

Run:  python examples/fol/universals.py
"""
from stele.ast import Var, Op, Pred, Forall
from stele.core.fol import ObjVar
from stele.core.terms import TVar, Lam, ForallIntro, ForallElim
from stele.core.typing import infer, check, empty_ctx, extend
from stele.core.term_parser import parse_term
from stele.parser import parse_formula

P = lambda x: Pred("P", (ObjVar(x),))
Q = lambda x: Pred("Q", (ObjVar(x),))


# ---------------------------------------------------------------------------
# Example 1: Universal identity  ∀x. P(x) → P(x)
# Proof: forall_intro x => fun h: P(x) => h
# ---------------------------------------------------------------------------

term1 = ForallIntro("x", Lam("h", P("x"), TVar("h")))
ty1   = Forall("x", Op("imp", (P("x"), P("x"))))
check(empty_ctx(), term1, ty1)
print(f"[1] forall x. P(x) -> P(x)  OK")


# ---------------------------------------------------------------------------
# Example 2: Universal instantiation  forall x. P(x) -> P(x)  at  a  →  P(a) -> P(a)
# Proof: forall_elim(t, a)  where t : forall x. P(x) -> P(x)
# ---------------------------------------------------------------------------

ctx2 = extend(empty_ctx(), "t", ty1)
term2 = ForallElim(TVar("t"), ObjVar("a"))
ty2   = infer(ctx2, term2)
assert ty2 == Op("imp", (P("a"), P("a")))
print(f"[2] forall_elim(t, a) : P(a) -> P(a)  OK")


# ---------------------------------------------------------------------------
# Example 3: Surface syntax round-trip via parse_term
# ---------------------------------------------------------------------------

term3 = parse_term("forall_intro x => fun h: P(x) => h")
ty3   = infer(empty_ctx(), term3)
assert ty3 == ty1
print(f"[3] parse_term round-trip  OK  (inferred: forall x. P(x) -> P(x))")


# ---------------------------------------------------------------------------
# Example 4: Universal distribution  ∀x. P(x)→Q(x)  →  ∀x. P(x)  →  ∀x. Q(x)
# Closed proof term:
#   fun f: forall x. P(x) -> Q(x) =>
#     fun g: forall x. P(x) =>
#       forall_intro x => forall_elim(f, x)(forall_elim(g, x))
# ---------------------------------------------------------------------------

src4 = (
    "fun f: forall x. P(x) -> Q(x) => "
    "fun g: forall x. P(x) => "
    "forall_intro x => forall_elim(f, x)(forall_elim(g, x))"
)
term4 = parse_term(src4)
ty4   = infer(empty_ctx(), term4)
expected4 = parse_formula(
    "(forall x. P(x) -> Q(x)) -> (forall x. P(x)) -> forall x. Q(x)"
)
check(empty_ctx(), term4, expected4)
print(f"[4] universal distribution  OK")


if __name__ == "__main__":
    print("\nAll universal examples passed.")
