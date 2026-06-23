"""Tests for the object-variable de Bruijn layer (stele.core.fol).

Covers:
  - ObjBound / ObjFree construction
  - _translate_obj_term / _untranslate_obj_term
  - to_debruijn_formula translation
  - from_debruijn_formula roundtrip
  - alpha_equiv_formula (including shadowing correctness)
  - formula_alpha_equiv_fol delegation
  - _feq in typing.py (normalisation + alpha-equiv)
  - Integration with infer / check
"""
import pytest
from stele.ast import Var, Op, Pred, Forall, Exists
from stele.core.fol import (
    ObjVar, ObjConst,
    ObjBound, ObjFree,
    DBFVarF, DBPredF, DBForallF, DBExistsF, DBOpF,
    _translate_obj_term, _untranslate_obj_term,
    to_debruijn_formula, from_debruijn_formula,
    alpha_equiv_formula,
    formula_alpha_equiv_fol,
    fol_free_obj_vars,
    subst_obj,
)
from stele.core.typing import (
    infer, check, empty_ctx, extend, _feq, normalize_neg,
    TypingError,
)
from stele.core.terms import (
    TVar, Lam, ForallIntro, ForallElim, ExistsIntro, ExistsElim,
)

# Helpers
A = Var("A")
B = Var("B")
P = lambda x: Pred("P", (ObjVar(x),))
Q = lambda x: Pred("Q", (ObjVar(x),))
PQ = lambda x, y: Pred("R", (ObjVar(x), ObjVar(y)))


# =============================================================================
# 1. ObjBound / ObjFree construction
# =============================================================================

class TestObjBoundFreeConstruct:
    def test_objbound_frozen(self):
        b = ObjBound(0)
        with pytest.raises(AttributeError):
            b.index = 1

    def test_objfree_frozen(self):
        f = ObjFree("a")
        with pytest.raises(AttributeError):
            f.name = "b"

    def test_objbound_equality(self):
        assert ObjBound(0) == ObjBound(0)
        assert ObjBound(0) != ObjBound(1)

    def test_objfree_equality(self):
        assert ObjFree("x") == ObjFree("x")
        assert ObjFree("x") != ObjFree("y")

    def test_objbound_str(self):
        assert str(ObjBound(2)) == "#2"

    def test_objfree_str(self):
        assert str(ObjFree("a")) == "a"


# =============================================================================
# 2. DB formula type construction
# =============================================================================

class TestDBFormulaConstruct:
    def test_dbfvarf(self):
        assert DBFVarF("P") == DBFVarF("P")

    def test_dbpredf(self):
        p = DBPredF("P", (ObjFree("a"),))
        assert p.name == "P"
        assert p.args == (ObjFree("a"),)

    def test_dbforallf(self):
        inner = DBPredF("P", (ObjBound(0),))
        f = DBForallF(inner)
        assert f.body == inner

    def test_dbexistsf(self):
        inner = DBPredF("P", (ObjBound(0),))
        e = DBExistsF(inner)
        assert e.body == inner

    def test_dbopf(self):
        op = DBOpF("and", (DBFVarF("A"), DBFVarF("B")))
        assert op.sym == "and"
        assert len(op.args) == 2


# =============================================================================
# 3. _translate_obj_term
# =============================================================================

class TestTranslateObjTerm:
    def test_bound_first(self):
        assert _translate_obj_term(ObjVar("x"), ["x"]) == ObjBound(0)

    def test_bound_second(self):
        assert _translate_obj_term(ObjVar("y"), ["x", "y"]) == ObjBound(1)

    def test_free(self):
        assert _translate_obj_term(ObjVar("z"), ["x", "y"]) == ObjFree("z")

    def test_objconst_unchanged(self):
        c = ObjConst("c")
        assert _translate_obj_term(c, ["x"]) is c

    def test_empty_ctx_all_free(self):
        assert _translate_obj_term(ObjVar("a"), []) == ObjFree("a")


# =============================================================================
# 4. _untranslate_obj_term
# =============================================================================

class TestUntranslateObjTerm:
    def test_bound_to_var(self):
        assert _untranslate_obj_term(ObjBound(0), ["x"]) == ObjVar("x")

    def test_bound_second(self):
        assert _untranslate_obj_term(ObjBound(1), ["x", "y"]) == ObjVar("y")

    def test_free_to_var(self):
        assert _untranslate_obj_term(ObjFree("a"), []) == ObjVar("a")

    def test_objconst_unchanged(self):
        c = ObjConst("c")
        assert _untranslate_obj_term(c, []) is c

    def test_out_of_scope_raises(self):
        with pytest.raises(ValueError, match="out of scope"):
            _untranslate_obj_term(ObjBound(2), ["x", "y"])


# =============================================================================
# 5. to_debruijn_formula — basic translation
# =============================================================================

class TestToDebruijnFormula:
    def test_propositional_var(self):
        assert to_debruijn_formula(Var("P")) == DBFVarF("P")

    def test_pred_free(self):
        db = to_debruijn_formula(Pred("P", (ObjVar("a"),)))
        assert db == DBPredF("P", (ObjFree("a"),))

    def test_pred_in_forall(self):
        db = to_debruijn_formula(Forall("x", P("x")))
        assert db == DBForallF(DBPredF("P", (ObjBound(0),)))

    def test_pred_in_exists(self):
        db = to_debruijn_formula(Exists("x", P("x")))
        assert db == DBExistsF(DBPredF("P", (ObjBound(0),)))

    def test_op_and(self):
        db = to_debruijn_formula(Op("and", (Var("A"), Var("B"))))
        assert db == DBOpF("and", (DBFVarF("A"), DBFVarF("B")))

    def test_forall_outer_inner(self):
        # forall x. forall y. R(x, y)
        f = Forall("x", Forall("y", PQ("x", "y")))
        db = to_debruijn_formula(f)
        # x → ObjBound(1), y → ObjBound(0) in inner context
        assert db == DBForallF(DBForallF(DBPredF("R", (ObjBound(1), ObjBound(0)))))

    def test_forall_only_inner_used(self):
        # forall x. forall y. P(y)  — x is unused
        f = Forall("x", Forall("y", P("y")))
        db = to_debruijn_formula(f)
        assert db == DBForallF(DBForallF(DBPredF("P", (ObjBound(0),))))

    def test_mixed_free_and_bound(self):
        # forall x. R(x, a)  — a is free
        f = Forall("x", Pred("R", (ObjVar("x"), ObjVar("a"))))
        db = to_debruijn_formula(f)
        assert db == DBForallF(DBPredF("R", (ObjBound(0), ObjFree("a"))))

    def test_objconst_in_forall(self):
        f = Forall("x", Pred("P", (ObjConst("c"),)))
        db = to_debruijn_formula(f)
        assert db == DBForallF(DBPredF("P", (ObjConst("c"),)))

    def test_with_initial_ctx(self):
        # formula Pred("P", (ObjVar("x"),)) under external ctx ["x"]
        db = to_debruijn_formula(Pred("P", (ObjVar("x"),)), ["x"])
        assert db == DBPredF("P", (ObjBound(0),))

    def test_unknown_type_raises(self):
        with pytest.raises(TypeError, match="unexpected formula type"):
            to_debruijn_formula(object())


# =============================================================================
# 6. from_debruijn_formula — roundtrip
# =============================================================================

class TestFromDebruijnFormula:
    def test_var_roundtrip(self):
        assert from_debruijn_formula(DBFVarF("A")) == Var("A")

    def test_pred_free_roundtrip(self):
        db = DBPredF("P", (ObjFree("a"),))
        f = from_debruijn_formula(db)
        assert f == Pred("P", (ObjVar("a"),))

    def test_forall_roundtrip_shape(self):
        db = DBForallF(DBPredF("P", (ObjBound(0),)))
        f = from_debruijn_formula(db)
        assert isinstance(f, Forall)
        # body should have a single free ObjVar matching the binder
        assert fol_free_obj_vars(f) == set()  # fully closed

    def test_nested_forall_roundtrip(self):
        db = DBForallF(DBForallF(DBPredF("R", (ObjBound(1), ObjBound(0)))))
        f = from_debruijn_formula(db)
        assert isinstance(f, Forall)
        assert isinstance(f.body, Forall)
        assert fol_free_obj_vars(f) == set()

    def test_roundtrip_is_alpha_equiv(self):
        # Any formula should roundtrip to something α-equivalent to the original
        original = Forall("x", Forall("y", PQ("x", "y")))
        db = to_debruijn_formula(original)
        back = from_debruijn_formula(db)
        assert alpha_equiv_formula(original, back)

    def test_op_roundtrip(self):
        db = DBOpF("imp", (DBFVarF("A"), DBFVarF("B")))
        f = from_debruijn_formula(db)
        assert f == Op("imp", (Var("A"), Var("B")))

    def test_exists_roundtrip(self):
        db = DBExistsF(DBPredF("P", (ObjBound(0),)))
        f = from_debruijn_formula(db)
        assert isinstance(f, Exists)
        assert fol_free_obj_vars(f) == set()

    def test_out_of_scope_raises(self):
        with pytest.raises(ValueError, match="out of scope"):
            from_debruijn_formula(DBForallF(DBPredF("P", (ObjBound(1),))))

    def test_unknown_type_raises(self):
        with pytest.raises(TypeError, match="unexpected type"):
            from_debruijn_formula(object())


# =============================================================================
# 7. alpha_equiv_formula — correctness
# =============================================================================

class TestAlphaEquivFormula:
    # Basic structural equality
    def test_identical_var(self):
        assert alpha_equiv_formula(Var("P"), Var("P"))

    def test_different_var(self):
        assert not alpha_equiv_formula(Var("P"), Var("Q"))

    def test_identical_pred(self):
        assert alpha_equiv_formula(P("a"), P("a"))

    def test_different_free_vars(self):
        assert not alpha_equiv_formula(P("a"), P("b"))

    # α-renaming of binders
    def test_forall_alpha_same_var(self):
        f = Forall("x", P("x"))
        assert alpha_equiv_formula(f, f)

    def test_forall_alpha_different_name(self):
        assert alpha_equiv_formula(Forall("x", P("x")), Forall("y", P("y")))

    def test_exists_alpha_different_name(self):
        assert alpha_equiv_formula(Exists("x", P("x")), Exists("y", P("y")))

    def test_forall_vs_exists_not_equiv(self):
        assert not alpha_equiv_formula(Forall("x", P("x")), Exists("x", P("x")))

    def test_free_var_names_must_match(self):
        # forall x. P(a)  vs  forall x. P(b)
        assert not alpha_equiv_formula(Forall("x", P("a")), Forall("x", P("b")))

    def test_nested_alpha(self):
        f1 = Forall("x", Forall("y", P("x")))
        f2 = Forall("u", Forall("v", P("u")))
        assert alpha_equiv_formula(f1, f2)

    def test_op_structural(self):
        assert alpha_equiv_formula(Op("and", (Var("A"), Var("B"))),
                                   Op("and", (Var("A"), Var("B"))))
        assert not alpha_equiv_formula(Op("and", (Var("A"), Var("B"))),
                                       Op("or",  (Var("A"), Var("B"))))

    # Shadowing correctness — the key case where renaming-based impls fail
    def test_shadowing_outer_vs_inner(self):
        # forall x. forall x. P(x)  — inner x shadows outer x
        # forall y. forall z. P(y)  — y is the OUTER binder
        # These are NOT α-equivalent: in the first, P's arg is bound by inner;
        # in the second, P's arg is bound by outer.
        f1 = Forall("x", Forall("x", P("x")))   # P's x → inner
        f2 = Forall("y", Forall("z", P("y")))   # P's y → outer
        assert not alpha_equiv_formula(f1, f2)

    def test_shadowing_both_inner(self):
        # forall x. forall x. P(x)  vs  forall a. forall b. P(b)
        # Both refer to the inner (depth-0) variable — α-equivalent.
        f1 = Forall("x", Forall("x", P("x")))
        f2 = Forall("a", Forall("b", P("b")))
        assert alpha_equiv_formula(f1, f2)

    def test_shadowing_both_outer(self):
        # forall x. forall y. P(x)  vs  forall a. forall b. P(a)
        # Both refer to the outer (depth-1) variable — α-equivalent.
        f1 = Forall("x", Forall("y", P("x")))
        f2 = Forall("a", Forall("b", P("a")))
        assert alpha_equiv_formula(f1, f2)

    def test_shadowing_mixed(self):
        # forall x. forall y. R(x, y)  vs  forall y. forall x. R(y, x)
        # Both: outer's var first, inner's var second — α-equivalent.
        f1 = Forall("x", Forall("y", PQ("x", "y")))
        f2 = Forall("y", Forall("x", PQ("y", "x")))
        assert alpha_equiv_formula(f1, f2)

    def test_shadowing_mixed_swapped_not_equiv(self):
        # forall x. forall y. R(x, y)  vs  forall y. forall x. R(x, y)
        # First: outer first, inner second.  Second: inner first, outer second.
        f1 = Forall("x", Forall("y", PQ("x", "y")))
        f2 = Forall("y", Forall("x", PQ("x", "y")))
        assert not alpha_equiv_formula(f1, f2)

    def test_capture_avoidance_doesnt_affect_alpha(self):
        # subst_obj might rename a binder; alpha_equiv_formula should still
        # recognise the result as α-equivalent to the original form.
        f = Forall("a", P("a"))
        renamed = subst_obj(f, "a", ObjVar("a"))  # shadows: returns f unchanged
        assert alpha_equiv_formula(f, renamed)

    def test_formula_with_objconst(self):
        f1 = Forall("x", Pred("P", (ObjConst("c"),)))
        f2 = Forall("y", Pred("P", (ObjConst("c"),)))
        assert alpha_equiv_formula(f1, f2)

    def test_formula_with_objconst_vs_objvar(self):
        f1 = Forall("x", Pred("P", (ObjConst("c"),)))
        f2 = Forall("y", Pred("P", (ObjVar("c"),)))
        # ObjConst("c") ≠ ObjFree("c") in the nameless form
        assert not alpha_equiv_formula(f1, f2)


# =============================================================================
# 8. formula_alpha_equiv_fol delegation
# =============================================================================

class TestFormulaAlphaEquivFolDelegates:
    def test_same_result_as_alpha_equiv_formula(self):
        pairs = [
            (Forall("x", P("x")), Forall("y", P("y"))),
            (Forall("x", P("x")), Exists("y", P("y"))),
            (Forall("x", Forall("x", P("x"))), Forall("a", Forall("b", P("b")))),
            (Forall("x", P("a")), Forall("y", P("b"))),
        ]
        for f1, f2 in pairs:
            assert formula_alpha_equiv_fol(f1, f2) == alpha_equiv_formula(f1, f2)

    def test_shadowing_fixed_in_legacy(self):
        f1 = Forall("x", Forall("x", P("x")))
        f2 = Forall("y", Forall("z", P("y")))
        assert not formula_alpha_equiv_fol(f1, f2)


# =============================================================================
# 9. _feq in typing.py (normalisation + alpha-equiv)
# =============================================================================

class TestFeq:
    def test_identical_var(self):
        assert _feq(Var("A"), Var("A"))

    def test_neg_normalisation(self):
        # not A  ==  A -> false  after normalisation
        assert _feq(Op("not", (Var("A"),)), Op("imp", (Var("A"), Op("bot", ()))))

    def test_forall_alpha_in_feq(self):
        f1 = Forall("x", P("x"))
        f2 = Forall("y", P("y"))
        assert _feq(f1, f2)

    def test_shadowing_fixed_in_feq(self):
        f1 = Forall("x", Forall("x", P("x")))
        f2 = Forall("y", Forall("z", P("y")))
        assert not _feq(f1, f2)

    def test_neg_forall_normalised(self):
        # not (forall x. P(x))  ==  (forall x. P(x)) -> false
        f1 = Op("not", (Forall("x", P("x")),))
        f2 = Op("imp", (Forall("x", P("x")), Op("bot", ())))
        assert _feq(f1, f2)

    def test_feq_with_alpha_in_neg(self):
        # not (forall x. P(x))  ==  not (forall y. P(y))
        f1 = Op("not", (Forall("x", P("x")),))
        f2 = Op("not", (Forall("y", P("y")),))
        assert _feq(f1, f2)


# =============================================================================
# 10. Integration: typing uses alpha_equiv_formula correctly
# =============================================================================

class TestTypingIntegration:
    def test_check_forall_alpha_variant(self):
        # ForallIntro("x", ...) checked against Forall("y", P(y) -> P(y))
        # The check rule renames the expected type, so the types must be
        # alpha-equivalent after normalisation.
        term = ForallIntro("x", Lam("h", P("x"), TVar("h")))
        expected = Forall("y", Op("imp", (P("y"), P("y"))))
        check(empty_ctx(), term, expected)  # should not raise

    def test_forall_elim_subst_correct(self):
        # forall x. P(x) -> Q(x)  instantiated at 'a'  →  P(a) -> Q(a)
        fa_type = Forall("x", Op("imp", (P("x"), Q("x"))))
        ctx = extend(empty_ctx(), "t", fa_type)
        ty = infer(ctx, ForallElim(TVar("t"), ObjVar("a")))
        assert ty == Op("imp", (P("a"), Q("a")))

    def test_forall_intro_fresh_check(self):
        ctx = extend(empty_ctx(), "h", P("x"))
        with pytest.raises(TypingError, match="free in the type of context variable"):
            infer(ctx, ForallIntro("x", TVar("h")))

    def test_exists_elim_freshness(self):
        exists_ty = Exists("x", P("x"))
        ctx = extend(empty_ctx(), "e", exists_ty)
        with pytest.raises(TypingError, match="freshness"):
            infer(ctx, ExistsElim(TVar("e"), "x", "h", TVar("h")))

    def test_case_branches_alpha_equiv(self):
        # Both Case branches return Forall("x", P(x)) using different var names
        # — they should be _feq-equal, so Case should type-check.
        from stele.core.terms import Case, Inl, Inr, Pair
        fa1 = Forall("x", P("x"))
        fa2 = Forall("y", P("y"))  # α-equivalent to fa1
        # Build context with  e : A or B,  t1 : forall x. P(x),  t2 : forall y. P(y)
        ctx = extend(
            extend(
                extend(empty_ctx(), "e", Op("or", (Var("A"), Var("B")))),
                "t1", fa1),
            "t2", fa2)
        # case e of  l => t1  |  r => t2
        term = Case(TVar("e"), "l", TVar("t1"), "r", TVar("t2"))
        ty = infer(ctx, term)
        # Both branches type to forall x. P(x) — equal up to alpha
        assert alpha_equiv_formula(ty, fa1)
