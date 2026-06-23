"""FOL proof-term examples — existential quantifier (exists).

These examples use the experimental first-order proof-term fragment.
They are NOT Stele-Light proof scripts; they use the Python API directly.

Run:  python examples/fol/existentials.py
"""
from stele.ast import Var, Op, Pred, Forall, Exists
from stele.core.fol import ObjVar
from stele.core.terms import TVar, Lam, ForallIntro, ForallElim, ExistsIntro, ExistsElim
from stele.core.typing import infer, check, empty_ctx, extend, TypingError
from stele.core.term_parser import parse_term
from stele.parser import parse_formula

P = lambda x: Pred("P", (ObjVar(x),))
Q = lambda x: Pred("Q", (ObjVar(x),))


# ---------------------------------------------------------------------------
# Example 1: Existential introduction — from P(a) prove exists x. P(x)
# Proof: exists_intro(a, h, exists x. P(x))
# ---------------------------------------------------------------------------

ctx1  = extend(empty_ctx(), "h", P("a"))
term1 = ExistsIntro(ObjVar("a"), TVar("h"), Exists("x", P("x")))
ty1   = infer(ctx1, term1)
assert ty1 == Exists("x", P("x"))
print("[1] exists x. P(x)  introduction from P(a)  OK")


# ---------------------------------------------------------------------------
# Example 2: Existential self-transport — (exists x. P(x)) -> (exists x. P(x))
# Proof: fun e: exists x. P(x) =>
#          exists_elim(e, x, h, exists_intro(x, h, exists y. P(y)))
# ---------------------------------------------------------------------------

src2  = ("fun e: exists x. P(x) => "
         "exists_elim(e, x, h, exists_intro(x, h, exists y. P(y)))")
term2 = parse_term(src2)
ty2   = infer(empty_ctx(), term2)
expected2 = parse_formula("(exists x. P(x)) -> exists x. P(x)")
check(empty_ctx(), term2, expected2)
print("[2] (exists x. P(x)) -> exists x. P(x)  OK")


# ---------------------------------------------------------------------------
# Example 3: Universal → existential  (forall x. P(x)) -> (exists x. P(x))
# Proof: fun h: forall x. P(x) =>
#          exists_intro(a, forall_elim(h, a), exists x. P(x))
# Note: 'a' is a free object variable (constant in this context).
# ---------------------------------------------------------------------------

src3  = ("fun h: forall x. P(x) => "
         "exists_intro(a, forall_elim(h, a), exists x. P(x))")
term3 = parse_term(src3)
ty3   = infer(empty_ctx(), term3)
expected3 = parse_formula("(forall x. P(x)) -> exists x. P(x)")
check(empty_ctx(), term3, expected3)
print("[3] (forall x. P(x)) -> (exists x. P(x))  OK")


# ---------------------------------------------------------------------------
# Example 4: Existential elimination — from (exists x. P(x) and Q(x)) derive
#            (exists x. P(x)) and (exists x. Q(x))
# Proof (closed):
#   fun e: exists x. P(x) and Q(x) =>
#     exists_elim(e, x, h,
#       pair(exists_intro(x, fst(h), exists y. P(y)),
#            exists_intro(x, snd(h), exists y. Q(y))))
# ---------------------------------------------------------------------------

PandQ = lambda x: Pred("PandQ", (ObjVar(x),))

src4 = (
    "fun e: exists x. P(x) and Q(x) => "
    "exists_elim(e, x, h, "
    "  pair(exists_intro(x, fst(h), exists y. P(y)), "
    "       exists_intro(x, snd(h), exists y. Q(y))))"
)
term4 = parse_term(src4)
expected4 = parse_formula(
    "(exists x. P(x) and Q(x)) -> (exists x. P(x)) and (exists x. Q(x))"
)
check(empty_ctx(), term4, expected4)
print("[4] (exists x. P(x) and Q(x)) -> (exists x. P(x)) and (exists x. Q(x))  OK")


# ---------------------------------------------------------------------------
# Example 5 (Negative): Freshness violation — escaping existential witness
# exists_elim(e, x, h, h)  — body type P(x) has x free → TypingError
# ---------------------------------------------------------------------------

ctx5  = extend(empty_ctx(), "e", Exists("x", P("x")))
term5 = ExistsElim(TVar("e"), "x", "h", TVar("h"))
try:
    infer(ctx5, term5)
    print("[5] FAIL — expected TypingError for escaping witness")
except TypingError as exc:
    assert "freshness" in str(exc).lower()
    print("[5] freshness violation detected  OK (raised TypingError as expected)")


# ---------------------------------------------------------------------------
# Example 6 (Negative): Wrong witness — h: P(b) used to pack as exists x. P(x) at a
# exists_intro(a, h, exists x. P(x))  where h: P(b) ≠ P(a)
# ---------------------------------------------------------------------------

ctx6  = extend(empty_ctx(), "h", P("b"))
term6 = ExistsIntro(ObjVar("a"), TVar("h"), Exists("x", P("x")))
try:
    infer(ctx6, term6)
    print("[6] FAIL — expected TypingError for wrong witness")
except TypingError:
    print("[6] wrong-witness type error detected  OK (raised TypingError as expected)")


if __name__ == "__main__":
    print("\nAll existential examples passed.")
