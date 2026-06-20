from stele.ast import Var, Op
from stele.matrix import (BOOLEAN, K3, LP, is_tautology, entails,
                          negation_fixpoints)

P = Var("P")
Q = Var("Q")
notP = Op("not", (P,))
lem = Op("or", (P, notP))


def test_lem_classical_but_not_k3():
    assert is_tautology(lem, BOOLEAN) is True
    assert is_tautology(lem, K3) is False


def test_liar_fixpoint():
    assert negation_fixpoints(K3) == ["I"]
    assert negation_fixpoints(LP) == ["B"]


def test_explosion_fails_in_lp_holds_classically():
    ok_lp, _ = entails([P, notP], Q, LP)
    ok_cl, _ = entails([P, notP], Q, BOOLEAN)
    assert ok_lp is False
    assert ok_cl is True


def test_k3_imp_table_matches_manifesto():
    # 유리학개론 p.5:  I -> F = I,  F -> I = T
    assert K3.tables["imp"][("I", "F")] == "I"
    assert K3.tables["imp"][("F", "I")] == "T"
