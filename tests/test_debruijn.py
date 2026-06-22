"""Tests for the de Bruijn binder representation (stele.core.debruijn).

Coverage:
  TestToDebruijn         — basic named → nameless translation
  TestShadowing          — shadowed binders get the innermost index
  TestFromDebruijn       — nameless → named (non-Case constructors)
  TestFromDebruijnCase   — DBCase raises NotImplementedError
  TestAlphaEquiv         — α-equivalence via to_debruijn comparison
  TestShift              — index adjustment, cutoff, nested binders
  TestSubst              — single-index substitution (decrement convention)
  TestSubstTop           — thin β-step wrapper
  TestConsistency        — named substitute vs de Bruijn subst on examples
  TestRegression         — existing reduction / typing must still work
"""
import pytest

from stele.ast import Var as FVar, Op
from stele.core.terms import TVar, Lam, App, Pair, Fst, Snd, Inl, Inr, Case, Abort
from stele.core.debruijn import (
    DBBound, DBFree,
    DBLam, DBApp, DBPair, DBFst, DBSnd, DBInl, DBInr, DBCase, DBAbort,
    to_debruijn, from_debruijn,
    shift, subst, subst_top,
    alpha_equiv,
)
from stele.core.reduce import free_vars, substitute, normalize
from stele.core.typing import infer

# ---------------------------------------------------------------------------
# Shared formula constants
# ---------------------------------------------------------------------------
A = FVar("A")
B = FVar("B")
C = FVar("C")


# ---------------------------------------------------------------------------
# TestToDebruijn
# ---------------------------------------------------------------------------

class TestToDebruijn:
    def test_free_variable_becomes_dbfree(self):
        assert to_debruijn(TVar("x")) == DBFree("x")

    def test_free_variable_in_empty_env(self):
        assert to_debruijn(TVar("a"), []) == DBFree("a")

    def test_bound_variable_in_env(self):
        # x is bound by the outermost binder → index 0
        assert to_debruijn(TVar("x"), ["x"]) == DBBound(0)

    def test_second_bound_variable(self):
        # y at index 0, x at index 1
        assert to_debruijn(TVar("x"), ["y", "x"]) == DBBound(1)

    def test_lambda_binds_body_index_0(self):
        # fun x: A => x  →  DBLam(A, DBBound(0))
        term = Lam("x", A, TVar("x"))
        expected = DBLam(A, DBBound(0))
        assert to_debruijn(term) == expected

    def test_lambda_free_variable_stays_free(self):
        # fun x: A => y  →  DBLam(A, DBFree("y"))
        term = Lam("x", A, TVar("y"))
        assert to_debruijn(term) == DBLam(A, DBFree("y"))

    def test_nested_lambda_inner_index_0(self):
        # fun x: A => fun y: B => y  →  DBLam(A, DBLam(B, DBBound(0)))
        term = Lam("x", A, Lam("y", B, TVar("y")))
        expected = DBLam(A, DBLam(B, DBBound(0)))
        assert to_debruijn(term) == expected

    def test_nested_lambda_outer_index_1(self):
        # K combinator: fun x: A => fun y: B => x  →  DBLam(A, DBLam(B, DBBound(1)))
        term = Lam("x", A, Lam("y", B, TVar("x")))
        expected = DBLam(A, DBLam(B, DBBound(1)))
        assert to_debruijn(term) == expected

    def test_app_translation(self):
        term = App(TVar("f"), TVar("a"))
        assert to_debruijn(term) == DBApp(DBFree("f"), DBFree("a"))

    def test_pair_translation(self):
        term = Pair(TVar("a"), TVar("b"))
        assert to_debruijn(term) == DBPair(DBFree("a"), DBFree("b"))

    def test_fst_translation(self):
        assert to_debruijn(Fst(TVar("p"))) == DBFst(DBFree("p"))

    def test_snd_translation(self):
        assert to_debruijn(Snd(TVar("p"))) == DBSnd(DBFree("p"))

    def test_inl_translation(self):
        assert to_debruijn(Inl(TVar("a"), B)) == DBInl(DBFree("a"), B)

    def test_inr_translation(self):
        assert to_debruijn(Inr(TVar("b"), A)) == DBInr(DBFree("b"), A)

    def test_abort_translation(self):
        assert to_debruijn(Abort(TVar("f"), A)) == DBAbort(DBFree("f"), A)

    def test_case_left_binder_index_0(self):
        # case s of inl x => x | inr y => y
        # left body: x → DBBound(0); right body: y → DBBound(0)
        s = TVar("s")
        term = Case(s, "x", TVar("x"), "y", TVar("y"))
        db = to_debruijn(term)
        assert db.scrutinee == DBFree("s")
        assert db.left_body  == DBBound(0)
        assert db.right_body == DBBound(0)

    def test_case_right_binder_independent(self):
        # Left branch uses x, right branch uses y; both become index 0
        s = TVar("s")
        term = Case(s, "x", TVar("x"), "y", TVar("y"))
        db = to_debruijn(term)
        assert db.left_body == db.right_body == DBBound(0)

    def test_case_outer_var_in_branch_body(self):
        # case s of inl x => z | inr y => z  — z is free
        term = Case(TVar("s"), "x", TVar("z"), "y", TVar("z"))
        db = to_debruijn(term)
        assert db.left_body  == DBFree("z")
        assert db.right_body == DBFree("z")

    def test_unknown_constructor_raises(self):
        with pytest.raises(TypeError, match="unknown term constructor"):
            to_debruijn(object())


# ---------------------------------------------------------------------------
# TestShadowing
# ---------------------------------------------------------------------------

class TestShadowing:
    def test_inner_rebinding_gives_index_0(self):
        # fun x: A => fun x: B => x   — inner x at index 0
        term = Lam("x", A, Lam("x", B, TVar("x")))
        db = to_debruijn(term)
        assert db == DBLam(A, DBLam(B, DBBound(0)))

    def test_outer_shadowed_var_not_accessible(self):
        # fun x: A => fun x: B => x   — outer x is shadowed, cannot be named
        term = Lam("x", A, Lam("x", B, TVar("x")))
        db = to_debruijn(term)
        inner_body = db.body.body   # DBBound(0)
        assert inner_body == DBBound(0)

    def test_outer_var_accessible_before_shadow(self):
        # fun x: A => App(x, fun x: B => x)
        # outer x is DBBound(0) in App position, inner x is DBBound(0) in inner body
        term = Lam("x", A, App(TVar("x"), Lam("x", B, TVar("x"))))
        db = to_debruijn(term)
        outer_body = db.body   # DBApp(DBBound(0), DBLam(B, DBBound(0)))
        assert isinstance(outer_body, DBApp)
        assert outer_body.fn  == DBBound(0)            # outer x
        assert outer_body.arg == DBLam(B, DBBound(0))  # inner λx.x

    def test_three_level_shadowing(self):
        # fun x: A => fun x: B => fun x: C => x   — innermost x at index 0
        term = Lam("x", A, Lam("x", B, Lam("x", C, TVar("x"))))
        db = to_debruijn(term)
        assert db == DBLam(A, DBLam(B, DBLam(C, DBBound(0))))

    def test_shadowing_in_case_branch(self):
        # case s of inl x => (fun x: B => x) | inr y => y
        # inner fun x shadows the case binder x
        s = TVar("s")
        inner_lam = Lam("x", B, TVar("x"))
        term = Case(s, "x", inner_lam, "y", TVar("y"))
        db = to_debruijn(term)
        # left_body: Lam translated with env=["x",...]; inner x shadows, becomes 0
        assert db.left_body  == DBLam(B, DBBound(0))
        assert db.right_body == DBBound(0)


# ---------------------------------------------------------------------------
# TestFromDebruijn
# ---------------------------------------------------------------------------

class TestFromDebruijn:
    def test_dbfree_becomes_tvar(self):
        assert from_debruijn(DBFree("a")) == TVar("a")

    def test_dbbound_in_env(self):
        assert from_debruijn(DBBound(0), ["p"]) == TVar("p")

    def test_dbbound_second_in_env(self):
        assert from_debruijn(DBBound(1), ["y", "x"]) == TVar("x")

    def test_dbbound_out_of_range_raises(self):
        with pytest.raises(ValueError, match="out of scope"):
            from_debruijn(DBBound(0), [])

    def test_dblam_generates_fresh_name(self):
        db = DBLam(A, DBBound(0))
        term = from_debruijn(db)
        assert isinstance(term, Lam)
        assert isinstance(term.body, TVar)
        assert term.body.name == term.var  # body refers to the binder

    def test_dblam_avoids_existing_env_name(self):
        # If env already has "x", fresh name should not be "x"
        db = DBLam(A, DBBound(0))
        term = from_debruijn(db, ["x"])
        assert term.var != "x"

    def test_round_trip_identity(self):
        # Lam("x", A, TVar("x")) → DB → back to named → should be α-equiv
        named = Lam("x", A, TVar("x"))
        db = to_debruijn(named)
        restored = from_debruijn(db)
        assert alpha_equiv(named, restored)

    def test_round_trip_k_combinator(self):
        named = Lam("x", A, Lam("y", B, TVar("x")))
        db = to_debruijn(named)
        restored = from_debruijn(db)
        assert alpha_equiv(named, restored)

    def test_round_trip_pair(self):
        named = Pair(TVar("a"), TVar("b"))
        db = to_debruijn(named)
        restored = from_debruijn(db)
        assert restored == named  # no binders, exact equality

    def test_round_trip_inl(self):
        named = Inl(TVar("a"), B)
        assert from_debruijn(to_debruijn(named)) == named

    def test_round_trip_inr(self):
        named = Inr(TVar("b"), A)
        assert from_debruijn(to_debruijn(named)) == named

    def test_round_trip_abort(self):
        named = Abort(TVar("f"), A)
        assert from_debruijn(to_debruijn(named)) == named

    def test_case_raises_not_implemented(self):
        db = DBCase(DBFree("s"), DBBound(0), DBBound(0))
        with pytest.raises(NotImplementedError):
            from_debruijn(db)

    def test_unknown_constructor_raises(self):
        with pytest.raises(TypeError, match="unknown DB term constructor"):
            from_debruijn(object())


# ---------------------------------------------------------------------------
# TestAlphaEquiv
# ---------------------------------------------------------------------------

class TestAlphaEquiv:
    def test_identity_alpha_equiv_different_names(self):
        # fun x: A => x  ≡α  fun y: A => y
        t1 = Lam("x", A, TVar("x"))
        t2 = Lam("y", A, TVar("y"))
        assert alpha_equiv(t1, t2)

    def test_identity_alpha_equiv_same_names(self):
        t = Lam("x", A, TVar("x"))
        assert alpha_equiv(t, t)

    def test_k_combinator_different_names(self):
        t1 = Lam("x", A, Lam("y", B, TVar("x")))
        t2 = Lam("a", A, Lam("b", B, TVar("a")))
        assert alpha_equiv(t1, t2)

    def test_different_body_not_alpha_equiv(self):
        t1 = Lam("x", A, TVar("x"))
        t2 = Lam("x", A, TVar("y"))   # body free var differs
        assert not alpha_equiv(t1, t2)

    def test_different_body_structure_not_alpha_equiv(self):
        # fun x: A => fun y: B => x  vs  fun x: A => fun y: B => y
        t1 = Lam("x", A, Lam("y", B, TVar("x")))
        t2 = Lam("x", A, Lam("y", B, TVar("y")))
        assert not alpha_equiv(t1, t2)

    def test_different_type_annotation_not_alpha_equiv(self):
        # fun x: A => x  vs  fun x: B => x
        t1 = Lam("x", A, TVar("x"))
        t2 = Lam("x", B, TVar("x"))
        assert not alpha_equiv(t1, t2)

    def test_case_branch_names_do_not_matter(self):
        # case s of inl x => x | inr y => y  ≡α  case s of inl a => a | inr b => b
        s = TVar("s")
        t1 = Case(s, "x", TVar("x"), "y", TVar("y"))
        t2 = Case(s, "a", TVar("a"), "b", TVar("b"))
        assert alpha_equiv(t1, t2)

    def test_case_different_bodies_not_alpha_equiv(self):
        s = TVar("s")
        t1 = Case(s, "x", TVar("x"), "y", TVar("y"))
        t2 = Case(s, "x", TVar("z"), "y", TVar("y"))  # left body uses free z
        assert not alpha_equiv(t1, t2)

    def test_free_var_names_matter(self):
        # free vars must match
        t1 = TVar("a")
        t2 = TVar("b")
        assert not alpha_equiv(t1, t2)

    def test_free_var_equal(self):
        assert alpha_equiv(TVar("x"), TVar("x"))

    def test_pair_alpha_equiv(self):
        t1 = Pair(Lam("x", A, TVar("x")), TVar("b"))
        t2 = Pair(Lam("z", A, TVar("z")), TVar("b"))
        assert alpha_equiv(t1, t2)


# ---------------------------------------------------------------------------
# TestShift
# ---------------------------------------------------------------------------

class TestShift:
    def test_shift_dbfree_unchanged(self):
        assert shift(DBFree("a"), 1, 0) == DBFree("a")

    def test_shift_bound_at_cutoff(self):
        # DBBound(0) with cutoff=0: index >= cutoff, shift by 1
        assert shift(DBBound(0), 1, 0) == DBBound(1)

    def test_shift_bound_below_cutoff(self):
        # DBBound(0) with cutoff=1: index < cutoff, unchanged
        assert shift(DBBound(0), 1, 1) == DBBound(0)

    def test_shift_bound_above_cutoff(self):
        assert shift(DBBound(3), 2, 2) == DBBound(5)

    def test_shift_zero_amount_unchanged(self):
        assert shift(DBBound(5), 0, 0) == DBBound(5)

    def test_shift_lam_increments_cutoff(self):
        # DBLam(A, DBBound(0)): inside binder cutoff=1; DBBound(0) < 1 → unchanged
        assert shift(DBLam(A, DBBound(0)), 1, 0) == DBLam(A, DBBound(0))

    def test_shift_lam_shifts_free_index(self):
        # DBLam(A, DBBound(1)): inside binder cutoff=1; DBBound(1) >= 1 → DBBound(2)
        assert shift(DBLam(A, DBBound(1)), 1, 0) == DBLam(A, DBBound(2))

    def test_shift_nested_lam(self):
        # DBLam(A, DBLam(B, DBBound(2))): cutoff goes 0→1→2; DBBound(2) >= 2 → DBBound(3)
        inner = DBLam(B, DBBound(2))
        assert shift(DBLam(A, inner), 1, 0) == DBLam(A, DBLam(B, DBBound(3)))

    def test_shift_app(self):
        t = DBApp(DBBound(0), DBBound(1))
        assert shift(t, 1, 0) == DBApp(DBBound(1), DBBound(2))

    def test_shift_pair(self):
        assert shift(DBPair(DBBound(0), DBFree("b")), 1, 0) == DBPair(DBBound(1), DBFree("b"))

    def test_shift_case_scrutinee_and_bodies(self):
        # scrutinee: cutoff=0; bodies: cutoff=1
        db = DBCase(DBBound(0), DBBound(0), DBBound(1))
        result = shift(db, 1, 0)
        assert result.scrutinee == DBBound(1)    # 0 + 1 = 1 (>= cutoff 0)
        assert result.left_body  == DBBound(0)   # 0 < cutoff 1 inside branch
        assert result.right_body == DBBound(2)   # 1 + 1 = 2 (>= cutoff 1 inside branch)

    def test_shift_inl_inr(self):
        assert shift(DBInl(DBBound(0), B), 1, 0) == DBInl(DBBound(1), B)
        assert shift(DBInr(DBBound(0), A), 1, 0) == DBInr(DBBound(1), A)

    def test_shift_abort(self):
        assert shift(DBAbort(DBBound(0), A), 1, 0) == DBAbort(DBBound(1), A)


# ---------------------------------------------------------------------------
# TestSubst
# ---------------------------------------------------------------------------

class TestSubst:
    def test_subst_exact_match(self):
        assert subst(DBBound(0), 0, DBFree("t")) == DBFree("t")

    def test_subst_index_above_target_decrements(self):
        # DBBound(1) with index=0 → 1 > 0 → DBBound(0)
        assert subst(DBBound(1), 0, DBFree("t")) == DBBound(0)

    def test_subst_index_below_target_unchanged(self):
        # DBBound(0) with index=1 → 0 < 1 → unchanged
        assert subst(DBBound(0), 1, DBFree("t")) == DBBound(0)

    def test_subst_dbfree_unchanged(self):
        assert subst(DBFree("x"), 0, DBFree("t")) == DBFree("x")

    def test_subst_under_lam_shifts_replacement(self):
        # subst(DBLam(A, DBBound(1)), 0, DBFree("t"))
        # Under Lam: index becomes 1, replacement shifted → DBFree("t") (shift of free = free)
        # DBBound(1) == 1 → return DBFree("t")
        result = subst(DBLam(A, DBBound(1)), 0, DBFree("t"))
        assert result == DBLam(A, DBFree("t"))

    def test_subst_under_lam_leaves_bound_alone(self):
        # subst(DBLam(A, DBBound(0)), 0, DBFree("t"))
        # Under Lam: index=1, DBBound(0) < 1 → unchanged
        result = subst(DBLam(A, DBBound(0)), 0, DBFree("t"))
        assert result == DBLam(A, DBBound(0))

    def test_beta_identity(self):
        # (λ.DBBound(0)) applied to DBFree("a") → DBFree("a")
        body = DBBound(0)
        assert subst(body, 0, DBFree("a")) == DBFree("a")

    def test_beta_constant(self):
        # (λ.DBFree("c")) applied to anything → DBFree("c")
        assert subst(DBFree("c"), 0, DBFree("anything")) == DBFree("c")

    def test_beta_k_combinator(self):
        # (λ.λ.DBBound(1)) arg  →  λ.shift(arg,1)
        # body of outer lambda: DBLam(B, DBBound(1))
        body = DBLam(B, DBBound(1))
        result = subst(body, 0, DBFree("a"))
        # Under inner Lam: index=1, repl=shift(DBFree("a"),1)=DBFree("a"); DBBound(1)==1→DBFree("a")
        assert result == DBLam(B, DBFree("a"))

    def test_beta_k_combinator_bound_replacement(self):
        # Replacement is a bound variable itself: DBBound(0)
        # (λ.λ.DBBound(1)) DBBound(0)  →  λ.DBBound(1)
        # shift(DBBound(0), 1, 0) = DBBound(1)
        # subst(DBBound(1), 1, DBBound(1)) = DBBound(1) matches → DBBound(1)
        body = DBLam(B, DBBound(1))
        result = subst(body, 0, DBBound(0))
        assert result == DBLam(B, DBBound(1))

    def test_subst_decrement_multiple(self):
        # DBApp(DBBound(2), DBBound(1)) with index=0
        # DBBound(2): 2 > 0 → DBBound(1)
        # DBBound(1): 1 > 0 → DBBound(0)
        t = DBApp(DBBound(2), DBBound(1))
        result = subst(t, 0, DBFree("x"))
        assert result == DBApp(DBBound(1), DBBound(0))

    def test_subst_case_scrutinee(self):
        db = DBCase(DBBound(0), DBBound(1), DBBound(1))
        result = subst(db, 0, DBFree("s"))
        # scrutinee: DBBound(0) == 0 → DBFree("s")
        assert result.scrutinee == DBFree("s")

    def test_subst_case_branch_bodies(self):
        # DBCase(DBFree("s"), DBBound(1), DBBound(1)) with index=0
        # Left body under 1 binder: index=1, repl shifted; DBBound(1) == 1 → repl shifted = DBFree("x")
        db = DBCase(DBFree("s"), DBBound(1), DBBound(1))
        result = subst(db, 0, DBFree("x"))
        assert result.left_body  == DBFree("x")
        assert result.right_body == DBFree("x")

    def test_subst_pair(self):
        t = DBPair(DBBound(0), DBBound(1))
        result = subst(t, 0, DBFree("a"))
        assert result == DBPair(DBFree("a"), DBBound(0))  # 1 > 0 → 0

    def test_capture_avoidance_structural(self):
        # The whole point: shifting replacement under binders prevents capture.
        # (λ.λ.DBBound(1)) applied to DBBound(0) (outer bound var)
        # Should give λ.DBBound(1), not λ.DBBound(0)
        body = DBLam(B, DBBound(1))
        result = subst(body, 0, DBBound(0))
        # Under inner Lam: repl = shift(DBBound(0), 1, 0) = DBBound(1)
        # DBBound(1) == 1 → return DBBound(1)
        assert result == DBLam(B, DBBound(1))


# ---------------------------------------------------------------------------
# TestSubstTop
# ---------------------------------------------------------------------------

class TestSubstTop:
    def test_identity_application(self):
        # (λ.0) t  =  t
        assert subst_top(DBFree("t"), DBBound(0)) == DBFree("t")

    def test_constant_application(self):
        # (λ.free "c") t  =  free "c"
        assert subst_top(DBFree("t"), DBFree("c")) == DBFree("c")

    def test_k_application(self):
        # (λ.λ.1) t  =  λ.t
        body = DBLam(B, DBBound(1))
        result = subst_top(DBFree("t"), body)
        assert result == DBLam(B, DBFree("t"))

    def test_subst_top_is_subst_at_zero(self):
        body = DBApp(DBBound(0), DBBound(2))
        repl = DBFree("arg")
        assert subst_top(repl, body) == subst(body, 0, repl)


# ---------------------------------------------------------------------------
# TestConsistency — named substitute vs de Bruijn subst
# ---------------------------------------------------------------------------

class TestConsistency:
    """Compare named capture-avoiding substitution with de Bruijn substitution.

    For any closed term body and replacement, the results should be
    structurally α-equivalent after translating named result to DB form.

    Strategy: pick representative named terms, perform both substitutions,
    translate the named result to de Bruijn, compare with pure de Bruijn result.
    """

    def _check(self, named_body, var, named_repl, db_body, db_repl):
        """Shared check helper."""
        named_result = substitute(named_body, var, named_repl)
        db_result    = subst_top(db_repl, db_body) if False else subst(db_body, 0, db_repl)
        # Compare named result (translated) vs direct DB result
        # Note: db_body already has var at index 0 because we construct it that way
        named_db = to_debruijn(named_result)
        assert named_db == db_result

    def test_identity_lambda_substitute(self):
        # (fun x: A => x)[TVar("a")/x]  =  TVar("a")
        body = Lam("x", A, TVar("x"))
        # But substituting x in (fun x => x) — x is bound, so result = (fun x => x)
        named_result = substitute(body, "x", TVar("a"))
        assert named_result == body  # shadowed, unchanged

    def test_simple_var_substitute(self):
        # TVar("x")[TVar("a")/x] = TVar("a")
        body = TVar("x")
        repl = TVar("a")
        named_result = substitute(body, "x", repl)
        assert named_result == repl

        # DB: DBBound(0)[0 := DBFree("a")] = DBFree("a")
        db_result = subst(DBBound(0), 0, DBFree("a"))
        named_db = to_debruijn(named_result, [])
        assert named_db == db_result

    def test_app_substitute(self):
        # App(TVar("x"), TVar("y"))[TVar("z")/x]  =  App(TVar("z"), TVar("y"))
        body = App(TVar("x"), TVar("y"))
        named_result = substitute(body, "x", TVar("z"))
        assert named_result == App(TVar("z"), TVar("y"))

        # DB: DBApp(DBBound(0), DBFree("y"))[0 := DBFree("z")]
        db_body = DBApp(DBBound(0), DBFree("y"))
        db_result = subst(db_body, 0, DBFree("z"))
        assert db_result == DBApp(DBFree("z"), DBFree("y"))
        assert to_debruijn(named_result, []) == db_result

    def test_lam_no_capture(self):
        # (fun y: B => x)[TVar("y")/x]  should alpha-rename y → y_0
        # because y is in free_vars(TVar("y")) = {"y"}
        body = Lam("y", B, TVar("x"))
        repl = TVar("y")
        named_result = substitute(body, "x", repl)
        # Named result should be a Lam with y renamed, body = TVar("y") (the replacement)
        assert isinstance(named_result, Lam)
        assert named_result.var != "y"       # binder was renamed
        assert named_result.body == TVar("y")

        # De Bruijn: subst(DBLam(B, DBBound(1)), 0, DBFree("y"))
        # Under lam: index=1, repl=shift(DBFree("y"),1)=DBFree("y"); DBBound(1)==1→DBFree("y")
        db_body = DBLam(B, DBBound(1))
        db_result = subst(db_body, 0, DBFree("y"))
        assert db_result == DBLam(B, DBFree("y"))
        # Named result translated (binder is renamed, body is TVar("y") = DBFree("y"))
        assert to_debruijn(named_result) == db_result

    def test_nested_lam_consistency(self):
        # (fun y: B => fun z: C => x)[TVar("a")/x]
        # x not captured; result = fun y: B => fun z: C => TVar("a")
        body = Lam("y", B, Lam("z", C, TVar("x")))
        repl = TVar("a")
        named_result = substitute(body, "x", repl)
        assert named_result == Lam("y", B, Lam("z", C, TVar("a")))

        # DB: subst(DBLam(B, DBLam(C, DBBound(2))), 0, DBFree("a"))
        # Under outer Lam: index=1, repl=DBFree("a"); under inner Lam: index=2, repl=DBFree("a")
        # DBBound(2) == 2 → DBFree("a")
        db_body = DBLam(B, DBLam(C, DBBound(2)))
        db_result = subst(db_body, 0, DBFree("a"))
        assert db_result == DBLam(B, DBLam(C, DBFree("a")))
        assert to_debruijn(named_result) == db_result


# ---------------------------------------------------------------------------
# TestRegression — existing reduction and typing must still work
# ---------------------------------------------------------------------------

class TestRegression:
    def test_identity_beta_still_works(self):
        from stele.core.reduce import step
        t = App(Lam("x", A, TVar("x")), TVar("a"))
        r = step(t)
        assert r == TVar("a")

    def test_normalize_still_works(self):
        # (fun x => fun y => fst(pair(x, y))) applied to a, then b
        inner = Fst(Pair(TVar("x"), TVar("y")))
        t = App(App(Lam("x", A, Lam("y", B, inner)), TVar("a")), TVar("b"))
        result = normalize(t)
        assert result == TVar("a")

    def test_typing_infer_still_works(self):
        ctx = {"a": A, "b": B}
        t = Pair(TVar("a"), TVar("b"))
        ty = infer(ctx, t)
        assert ty == Op("and", (A, B))

    def test_debruijn_alpha_equiv_of_beta_result(self):
        # After beta, named result and DB result should be α-equivalent
        # (fun x => fun y => x) a  →  fun y => a
        named_body = Lam("x", A, Lam("y", B, TVar("x")))
        named_result = App(named_body, TVar("a"))
        from stele.core.reduce import normalize
        reduced = normalize(named_result)

        # Should be α-equiv to fun y: B => a
        expected = Lam("y", B, TVar("a"))
        assert alpha_equiv(reduced, expected)

    def test_to_debruijn_does_not_affect_kernel(self):
        # Importing debruijn must not affect kernel isolation
        from stele import kernel  # noqa: F401
        import stele.core.debruijn  # noqa: F401
        # If we got here without ImportError, isolation is intact

    def test_all_db_constructors_are_frozen(self):
        db_instances = [
            DBBound(0), DBFree("x"), DBLam(A, DBBound(0)),
            DBApp(DBFree("a"), DBFree("b")), DBPair(DBFree("a"), DBFree("b")),
            DBFst(DBFree("p")), DBSnd(DBFree("p")),
            DBInl(DBFree("a"), B), DBInr(DBFree("b"), A),
            DBCase(DBFree("s"), DBBound(0), DBBound(0)),
            DBAbort(DBFree("f"), A),
        ]
        for inst in db_instances:
            with pytest.raises(AttributeError):  # FrozenInstanceError is a subclass
                inst.new_attr = "x"  # frozen dataclasses raise FrozenInstanceError
