"""FOL proof-term examples — De Morgan laws (intuitionistically valid directions).

Stele supports the intuitionistic fragment only.  Of the four first-order De
Morgan equivalences, two directions are intuitionistically valid:

  (a) not (exists x. P(x))  →  forall x. not P(x)        (VALID)
  (b) exists x. not P(x)    →  not (forall x. P(x))       (VALID)

The reverse directions require classical reasoning and are not provable here.

These examples are NOT Stele-Light proof scripts; they use the Python API directly.

Run:  python examples/fol/de_morgan_fol.py
"""
from stele.ast import Op, Pred, Forall, Exists
from stele.core.fol import ObjVar
from stele.core.typing import infer, check, empty_ctx
from stele.core.term_parser import parse_term
from stele.parser import parse_formula


P = lambda x: Pred("P", (ObjVar(x),))


# ---------------------------------------------------------------------------
# (a) not (exists x. P(x))  →  forall x. not P(x)
#
# Proof:
#   fun h: not (exists x. P(x)) =>
#     forall_intro x =>
#       fun px: P(x) =>
#         h(exists_intro(x, px, exists y. P(y)))
# ---------------------------------------------------------------------------

src_a = (
    "fun h: not (exists x. P(x)) => "
    "forall_intro x => "
    "fun px: P(x) => "
    "h(exists_intro(x, px, exists y. P(y)))"
)
term_a    = parse_term(src_a)
expected_a = parse_formula("not (exists x. P(x)) -> forall x. not P(x)")
check(empty_ctx(), term_a, expected_a)
print("[a] not (exists x. P(x)) -> forall x. not P(x)  OK")


# ---------------------------------------------------------------------------
# (b) exists x. not P(x)  →  not (forall x. P(x))
#
# Proof:
#   fun e: exists x. not P(x) =>
#     fun g: forall x. P(x) =>
#       exists_elim(e, x, h, h(forall_elim(g, x)))
# ---------------------------------------------------------------------------

src_b = (
    "fun e: exists x. not P(x) => "
    "fun g: forall x. P(x) => "
    "exists_elim(e, x, h, h(forall_elim(g, x)))"
)
term_b    = parse_term(src_b)
expected_b = parse_formula("(exists x. not P(x)) -> not (forall x. P(x))")
check(empty_ctx(), term_b, expected_b)
print("[b] (exists x. not P(x)) -> not (forall x. P(x))  OK")


if __name__ == "__main__":
    print("\nAll De Morgan FOL examples passed.")
