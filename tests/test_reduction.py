"""Tests for stele.core.reduce — beta-reduction, substitution, and normalization.

Coverage
--------
A. free_vars — structural recursion, binder scoping
B. _fresh   — name generation
C. substitute — capture-avoiding, shadowing
D. step     — head redexes (beta_imp / beta_fst / beta_snd / beta_case_l / beta_case_r)
              structural reduction (reduces in subterms)
              already-normal terms return None
E. Subject reduction (type preservation under step)
F. normalize — multi-step convergence, idempotence, is_normal after
G. is_normal
H. ReductionError on fuel exhaustion
I. Confluence smoke tests — two reduction orders converge
J. Consistency smoke tests — closed terms cannot have type false via intro rules alone
K. CLI term-normalize command
"""
import pytest
from stele.ast import Var as FVar, Op
from stele.core.terms import TVar, Lam, App, Pair, Fst, Snd, Inl, Inr, Case, Abort
from stele.core.typing import (
    infer, check, TypingError, empty_ctx, extend, normalize_neg,
)
from stele.core.reduce import (
    free_vars, _fresh, substitute, step, normalize, is_normal, ReductionError,
)


# ---------------------------------------------------------------------------
# Formula shortcuts
# ---------------------------------------------------------------------------

def A():       return FVar("A")
def B():       return FVar("B")
def C():       return FVar("C")
def imp(a, b): return Op("imp", (a, b))
def and_(a, b): return Op("and", (a, b))
def or_(a, b):  return Op("or",  (a, b))
def bot():      return Op("bot", ())


# ---------------------------------------------------------------------------
# A. free_vars
# ---------------------------------------------------------------------------

class TestFreeVars:
    def test_tvar(self):
        assert free_vars(TVar("x")) == {"x"}

    def test_lam_binds(self):
        assert free_vars(Lam("x", A(), TVar("x"))) == set()

    def test_lam_free(self):
        assert free_vars(Lam("x", A(), TVar("y"))) == {"y"}

    def test_app(self):
        assert free_vars(App(TVar("f"), TVar("a"))) == {"f", "a"}

    def test_pair(self):
        assert free_vars(Pair(TVar("a"), TVar("b"))) == {"a", "b"}

    def test_fst(self):
        assert free_vars(Fst(TVar("p"))) == {"p"}

    def test_snd(self):
        assert free_vars(Snd(TVar("p"))) == {"p"}

    def test_inl(self):
        assert free_vars(Inl(TVar("a"), B())) == {"a"}

    def test_inr(self):
        assert free_vars(Inr(TVar("b"), A())) == {"b"}

    def test_abort(self):
        assert free_vars(Abort(TVar("f"), A())) == {"f"}

    def test_case_both_bound(self):
        t = Case(TVar("e"), "x", TVar("x"), "y", TVar("y"))
        assert free_vars(t) == {"e"}

    def test_case_left_free(self):
        t = Case(TVar("e"), "x", TVar("z"), "y", TVar("y"))
        assert free_vars(t) == {"e", "z"}

    def test_case_right_free(self):
        t = Case(TVar("e"), "x", TVar("x"), "y", TVar("w"))
        assert free_vars(t) == {"e", "w"}

    def test_nested_lam_closed(self):
        t = Lam("x", A(), Lam("y", B(), App(TVar("x"), TVar("y"))))
        assert free_vars(t) == set()

    def test_nested_lam_outer_free(self):
        t = Lam("y", B(), App(TVar("x"), TVar("y")))
        assert free_vars(t) == {"x"}


# ---------------------------------------------------------------------------
# B. _fresh
# ---------------------------------------------------------------------------

class TestFresh:
    def test_not_in_avoid(self):
        assert _fresh("x", set()) == "x"
        assert _fresh("x", {"y"}) == "x"

    def test_already_taken(self):
        assert _fresh("x", {"x"}) == "x_0"

    def test_first_candidate_taken(self):
        assert _fresh("x", {"x", "x_0"}) == "x_1"

    def test_multiple_taken(self):
        assert _fresh("x", {"x", "x_0", "x_1"}) == "x_2"


# ---------------------------------------------------------------------------
# C. substitute
# ---------------------------------------------------------------------------

class TestSubstitute:
    def test_identity(self):
        assert substitute(TVar("x"), "x", TVar("a")) == TVar("a")

    def test_no_match(self):
        assert substitute(TVar("y"), "x", TVar("a")) == TVar("y")

    def test_lam_shadow(self):
        # Lambda re-binds x; substitution for x is blocked entirely
        t = Lam("x", A(), TVar("x"))
        assert substitute(t, "x", TVar("a")) == t

    def test_lam_no_capture(self):
        # y is not free in TVar("a") so no alpha-rename needed
        t = Lam("y", B(), TVar("x"))
        assert substitute(t, "x", TVar("a")) == Lam("y", B(), TVar("a"))

    def test_lam_capture_avoidance(self):
        # substitute y -> TVar("x") in Lam("x", A, TVar("y"))
        # x is free in replacement so binder x must be renamed
        t = Lam("x", A(), TVar("y"))
        result = substitute(t, "y", TVar("x"))
        assert isinstance(result, Lam)
        assert result.var != "x"                    # renamed to avoid capture
        assert result.body == TVar("x")             # replacement is TVar("x")

    def test_app(self):
        t = App(TVar("f"), TVar("x"))
        assert substitute(t, "x", TVar("a")) == App(TVar("f"), TVar("a"))

    def test_pair(self):
        t = Pair(TVar("x"), TVar("y"))
        assert substitute(t, "x", TVar("a")) == Pair(TVar("a"), TVar("y"))

    def test_fst(self):
        assert substitute(Fst(TVar("x")), "x", TVar("a")) == Fst(TVar("a"))

    def test_snd(self):
        assert substitute(Snd(TVar("x")), "x", TVar("a")) == Snd(TVar("a"))

    def test_inl(self):
        assert (substitute(Inl(TVar("x"), B()), "x", TVar("a"))
                == Inl(TVar("a"), B()))

    def test_inr(self):
        assert (substitute(Inr(TVar("x"), A()), "x", TVar("a"))
                == Inr(TVar("a"), A()))

    def test_abort(self):
        assert (substitute(Abort(TVar("x"), A()), "x", TVar("a"))
                == Abort(TVar("a"), A()))

    def test_case_left_shadow(self):
        # left_var == var → left body is untouched; right body IS substituted
        t = Case(TVar("e"), "x", TVar("x"), "y", TVar("x"))
        result = substitute(t, "x", TVar("a"))
        assert result.left_body == TVar("x")    # shadowed
        assert result.right_body == TVar("a")   # substituted

    def test_case_right_shadow(self):
        # right_var == var → right body is untouched; left body IS substituted
        t = Case(TVar("e"), "z", TVar("y"), "y", TVar("y"))
        result = substitute(t, "y", TVar("a"))
        assert result.left_body == TVar("a")    # y substituted in left branch
        assert result.right_body == TVar("y")   # shadowed in right branch

    def test_case_capture_avoidance_left(self):
        # substitute "y" -> TVar("x") in Case(e, "x", TVar("y"), "z", TVar("y"))
        # left binder "x" is free in replacement TVar("x") → needs rename
        t = Case(TVar("e"), "x", TVar("y"), "z", TVar("y"))
        result = substitute(t, "y", TVar("x"))
        assert result.left_var != "x"           # renamed
        assert result.left_body == TVar("x")    # y -> TVar("x")
        assert result.right_var == "z"          # z not in {"x"}, no rename
        assert result.right_body == TVar("x")   # y -> TVar("x")

    def test_not_present_is_noop(self):
        assert substitute(TVar("x"), "z", TVar("a")) == TVar("x")


# ---------------------------------------------------------------------------
# D. step — head redexes
# ---------------------------------------------------------------------------

class TestStepHeadRedexes:
    def test_beta_imp_identity(self):
        # (λx:A. x) a → a
        t = App(Lam("x", A(), TVar("x")), TVar("a"))
        assert step(t) == TVar("a")

    def test_beta_imp_body_substitution(self):
        # (λx:A. pair(x, x)) a → pair(a, a)
        t = App(Lam("x", A(), Pair(TVar("x"), TVar("x"))), TVar("a"))
        assert step(t) == Pair(TVar("a"), TVar("a"))

    def test_beta_fst(self):
        assert step(Fst(Pair(TVar("a"), TVar("b")))) == TVar("a")

    def test_beta_snd(self):
        assert step(Snd(Pair(TVar("a"), TVar("b")))) == TVar("b")

    def test_beta_case_l(self):
        t = Case(Inl(TVar("a"), B()), "x", TVar("x"), "y", TVar("y"))
        assert step(t) == TVar("a")

    def test_beta_case_r(self):
        t = Case(Inr(TVar("b"), A()), "x", TVar("x"), "y", TVar("y"))
        assert step(t) == TVar("b")

    def test_beta_case_l_body(self):
        # case(inl(a, B), x, pair(x, x), y, y) → pair(a, a)
        t = Case(Inl(TVar("a"), B()), "x", Pair(TVar("x"), TVar("x")),
                 "y", TVar("y"))
        assert step(t) == Pair(TVar("a"), TVar("a"))

    def test_beta_case_r_body(self):
        # case(inr(b, A), x, x, y, pair(y, y)) → pair(b, b)
        t = Case(Inr(TVar("b"), A()), "x", TVar("x"),
                 "y", Pair(TVar("y"), TVar("y")))
        assert step(t) == Pair(TVar("b"), TVar("b"))


# ---------------------------------------------------------------------------
# D. step — already normal
# ---------------------------------------------------------------------------

class TestStepNormal:
    def test_tvar(self):
        assert step(TVar("x")) is None

    def test_lam_normal(self):
        assert step(Lam("x", A(), TVar("x"))) is None

    def test_app_no_redex(self):
        assert step(App(TVar("f"), TVar("a"))) is None

    def test_pair_normal(self):
        assert step(Pair(TVar("a"), TVar("b"))) is None

    def test_inl_normal(self):
        assert step(Inl(TVar("a"), B())) is None

    def test_inr_normal(self):
        assert step(Inr(TVar("b"), A())) is None

    def test_abort_normal(self):
        assert step(Abort(TVar("f"), A())) is None

    def test_case_no_redex(self):
        t = Case(TVar("e"), "x", TVar("x"), "y", TVar("y"))
        assert step(t) is None


# ---------------------------------------------------------------------------
# D. step — structural reduction
# ---------------------------------------------------------------------------

class TestStepStructural:
    def test_app_reduces_fn_first(self):
        # fn has a redex; fn is reduced before arg
        inner = App(Lam("x", A(), TVar("x")), TVar("a"))
        outer = App(inner, TVar("b"))
        assert step(outer) == App(TVar("a"), TVar("b"))

    def test_app_reduces_arg_after_fn_normal(self):
        # fn is already normal; arg has a redex
        inner = App(Lam("x", A(), TVar("x")), TVar("a"))
        outer = App(TVar("f"), inner)
        assert step(outer) == App(TVar("f"), TVar("a"))

    def test_fst_reduces_inside(self):
        # pair subterm has a redex (not a Pair constructor)
        inner = App(Lam("x", and_(A(), B()), TVar("x")), TVar("p"))
        assert step(Fst(inner)) == Fst(TVar("p"))

    def test_snd_reduces_inside(self):
        inner = App(Lam("x", and_(A(), B()), TVar("x")), TVar("p"))
        assert step(Snd(inner)) == Snd(TVar("p"))

    def test_lam_reduces_body(self):
        body = Fst(Pair(TVar("x"), TVar("y")))
        assert step(Lam("x", A(), body)) == Lam("x", A(), TVar("x"))

    def test_pair_reduces_left_first(self):
        left  = Fst(Pair(TVar("a"), TVar("b")))   # has redex
        right = Snd(Pair(TVar("c"), TVar("d")))   # also has redex, but left first
        assert step(Pair(left, right)) == Pair(TVar("a"), right)

    def test_pair_reduces_right_when_left_normal(self):
        left  = TVar("a")
        right = Fst(Pair(TVar("b"), TVar("c")))
        assert step(Pair(left, right)) == Pair(TVar("a"), TVar("b"))

    def test_case_reduces_scrutinee(self):
        sc = App(Lam("x", or_(A(), B()), TVar("x")), TVar("e"))
        t  = Case(sc, "a", TVar("a"), "b", TVar("b"))
        assert step(t) == Case(TVar("e"), "a", TVar("a"), "b", TVar("b"))

    def test_inl_reduces_value(self):
        inner = App(Lam("x", A(), TVar("x")), TVar("a"))
        assert step(Inl(inner, B())) == Inl(TVar("a"), B())

    def test_inr_reduces_value(self):
        inner = App(Lam("x", B(), TVar("x")), TVar("b"))
        assert step(Inr(inner, A())) == Inr(TVar("b"), A())

    def test_abort_reduces_inside(self):
        inner = App(Lam("x", bot(), TVar("x")), TVar("f"))
        assert step(Abort(inner, A())) == Abort(TVar("f"), A())


# ---------------------------------------------------------------------------
# E. Subject reduction (type preservation under step)
# ---------------------------------------------------------------------------

class TestSubjectReduction:
    def _types_agree(self, ctx, before, after):
        ty_b = normalize_neg(infer(ctx, before))
        ty_a = normalize_neg(infer(ctx, after))
        return ty_b == ty_a

    def test_beta_imp(self):
        ctx = {"a": A()}
        t = App(Lam("x", A(), TVar("x")), TVar("a"))
        assert self._types_agree(ctx, t, step(t))

    def test_beta_fst(self):
        ctx = {"a": A(), "b": B()}
        t = Fst(Pair(TVar("a"), TVar("b")))
        assert self._types_agree(ctx, t, step(t))

    def test_beta_snd(self):
        ctx = {"a": A(), "b": B()}
        t = Snd(Pair(TVar("a"), TVar("b")))
        assert self._types_agree(ctx, t, step(t))

    def test_beta_case_l(self):
        ctx = {"a": A()}
        # Both branches produce A or B; beta_case_l reduces to Inl(a, B)
        t = Case(Inl(TVar("a"), B()),
                 "x", Inl(TVar("x"), B()),
                 "y", Inr(TVar("y"), A()))
        assert self._types_agree(ctx, t, step(t))

    def test_beta_case_r(self):
        ctx = {"b": B()}
        t = Case(Inr(TVar("b"), A()),
                 "x", Inl(TVar("x"), B()),
                 "y", Inr(TVar("y"), A()))
        assert self._types_agree(ctx, t, step(t))

    def test_structural_pair(self):
        ctx = {"a": A(), "b": B()}
        t = Pair(Fst(Pair(TVar("a"), TVar("b"))), TVar("b"))
        assert self._types_agree(ctx, t, step(t))

    def test_type_after_multi_step_stays_same(self):
        ctx = {"a": A(), "b": B()}
        # pair(fst(pair(a,b)), snd(pair(a,b))) : A and B
        t = Pair(Fst(Pair(TVar("a"), TVar("b"))),
                 Snd(Pair(TVar("a"), TVar("b"))))
        expected_ty = normalize_neg(infer(ctx, t))
        n = normalize(t)
        assert normalize_neg(infer(ctx, n)) == expected_ty


# ---------------------------------------------------------------------------
# F. normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_already_normal(self):
        assert normalize(TVar("x")) == TVar("x")

    def test_one_step_beta_imp(self):
        t = App(Lam("x", A(), TVar("x")), TVar("a"))
        assert normalize(t) == TVar("a")

    def test_fst_pair(self):
        assert normalize(Fst(Pair(TVar("a"), TVar("b")))) == TVar("a")

    def test_snd_pair(self):
        assert normalize(Snd(Pair(TVar("a"), TVar("b")))) == TVar("b")

    def test_multi_step_curried_app(self):
        # (λf:A->B. λa:A. f(a)) g b → g(b)
        t = App(
            App(
                Lam("f", imp(A(), B()),
                    Lam("a", A(), App(TVar("f"), TVar("a")))),
                TVar("g"),
            ),
            TVar("b"),
        )
        assert normalize(t) == App(TVar("g"), TVar("b"))

    def test_nested_fst(self):
        # fst(pair(fst(pair(a, b)), c)) → a
        t = Fst(Pair(Fst(Pair(TVar("a"), TVar("b"))), TVar("c")))
        assert normalize(t) == TVar("a")

    def test_case_inl_with_inner_redex(self):
        # case(inl(fst(pair(a,b)), B), x, x, y, y) → fst(pair(a,b)) → a
        t = Case(
            Inl(Fst(Pair(TVar("a"), TVar("b"))), B()),
            "x", TVar("x"), "y", TVar("y"),
        )
        assert normalize(t) == TVar("a")

    def test_lam_under_reduction(self):
        # λx:A. fst(pair(x, y)) → λx:A. x
        t = Lam("x", A(), Fst(Pair(TVar("x"), TVar("y"))))
        assert normalize(t) == Lam("x", A(), TVar("x"))

    def test_idempotent(self):
        t = App(Lam("x", A(), Pair(TVar("x"), TVar("x"))), TVar("a"))
        n1 = normalize(t)
        n2 = normalize(n1)
        assert n1 == n2

    def test_is_normal_after_normalize(self):
        t = App(Lam("x", A(), App(Lam("y", B(), TVar("y")), TVar("x"))), TVar("a"))
        assert is_normal(normalize(t))

    def test_normalize_pair_both_sides(self):
        t = Pair(App(Lam("x", A(), TVar("x")), TVar("a")),
                 App(Lam("y", B(), TVar("y")), TVar("b")))
        assert normalize(t) == Pair(TVar("a"), TVar("b"))


# ---------------------------------------------------------------------------
# G. is_normal
# ---------------------------------------------------------------------------

class TestIsNormal:
    def test_tvar(self):
        assert is_normal(TVar("x"))

    def test_lam_normal(self):
        assert is_normal(Lam("x", A(), TVar("x")))

    def test_app_no_redex(self):
        assert is_normal(App(TVar("f"), TVar("a")))

    def test_app_redex_not_normal(self):
        assert not is_normal(App(Lam("x", A(), TVar("x")), TVar("a")))

    def test_fst_pair_not_normal(self):
        assert not is_normal(Fst(Pair(TVar("a"), TVar("b"))))

    def test_snd_pair_not_normal(self):
        assert not is_normal(Snd(Pair(TVar("a"), TVar("b"))))

    def test_case_inl_not_normal(self):
        t = Case(Inl(TVar("a"), B()), "x", TVar("x"), "y", TVar("y"))
        assert not is_normal(t)

    def test_case_inr_not_normal(self):
        t = Case(Inr(TVar("b"), A()), "x", TVar("x"), "y", TVar("y"))
        assert not is_normal(t)

    def test_nested_redex_in_lam_not_normal(self):
        t = Lam("x", A(), Fst(Pair(TVar("x"), TVar("y"))))
        assert not is_normal(t)


# ---------------------------------------------------------------------------
# H. ReductionError
# ---------------------------------------------------------------------------

class TestReductionError:
    def test_fuel_exhausted_one_step_term(self):
        # fuel=1 means 1 loop iteration: reduces but never checks normality
        t = App(Lam("x", A(), TVar("x")), TVar("a"))
        with pytest.raises(ReductionError):
            normalize(t, fuel=1)

    def test_sufficient_fuel(self):
        # fuel=2: reduce once, then confirm normal on second iter
        t = App(Lam("x", A(), TVar("x")), TVar("a"))
        assert normalize(t, fuel=2) == TVar("a")

    def test_two_step_fuel_boundary(self):
        # (λx:A. (λy:A. y) x) a requires 2 reductions + 1 normal check = fuel≥3
        t = App(Lam("x", A(), App(Lam("y", A(), TVar("y")), TVar("x"))), TVar("a"))
        with pytest.raises(ReductionError):
            normalize(t, fuel=2)
        assert normalize(t, fuel=3) == TVar("a")

    def test_error_message_contains_fuel(self):
        t = App(Lam("x", A(), TVar("x")), TVar("a"))
        with pytest.raises(ReductionError, match="1"):
            normalize(t, fuel=1)


# ---------------------------------------------------------------------------
# I. Confluence smoke tests
# ---------------------------------------------------------------------------

class TestConfluence:
    """Two different reduction orders must converge to the same normal form."""

    def test_pair_two_independent_redexes(self):
        # pair(id_A(a), fst(pair(b, c))) — two independent redexes
        t = Pair(
            App(Lam("x", A(), TVar("x")), TVar("a")),
            Fst(Pair(TVar("b"), TVar("c"))),
        )
        normal = normalize(t)
        assert normal == Pair(TVar("a"), TVar("b"))

        # Manually simulate the alternative (right-first) order
        t_right_first = Pair(
            App(Lam("x", A(), TVar("x")), TVar("a")),
            TVar("b"),                                      # right already reduced
        )
        assert normalize(t_right_first) == normal

    def test_outer_vs_inner_order(self):
        # (λx:A->A. x(a)) (λy:A. y)
        # Outer beta: substitute → (λy:A. y)(a) → a
        t = App(
            Lam("x", imp(A(), A()), App(TVar("x"), TVar("a"))),
            Lam("y", A(), TVar("y")),
        )
        assert normalize(t) == TVar("a")

        # Manual step sequence for verification
        s1 = step(t)
        assert s1 == App(Lam("y", A(), TVar("y")), TVar("a"))
        assert normalize(s1) == TVar("a")

    def test_fst_and_snd_of_same_pair(self):
        # fst and snd of the same pair converge independently
        p = Pair(Pair(TVar("a"), TVar("b")), Pair(TVar("c"), TVar("d")))
        assert normalize(Fst(p)) == Pair(TVar("a"), TVar("b"))
        assert normalize(Snd(p)) == Pair(TVar("c"), TVar("d"))

    def test_lam_body_redex_same_as_beta_then_reduce(self):
        # λx:A. (λy:A. y) x
        # Strategy A: reduce under lambda first → λx:A. x → already normal
        # Strategy B: first apply to some arg a, then normalize
        t = Lam("x", A(), App(Lam("y", A(), TVar("y")), TVar("x")))
        n_lam = normalize(t)
        assert n_lam == Lam("x", A(), TVar("x"))

        # Apply to TVar("a"), normalize: (λx:A. (λy:A. y) x) a → ...
        applied = App(t, TVar("a"))
        assert normalize(applied) == TVar("a")


# ---------------------------------------------------------------------------
# J. Consistency smoke tests
# ---------------------------------------------------------------------------

class TestConsistency:
    """Intro-rule terms cannot have type false in an empty context."""

    def test_closed_intro_terms_not_false(self):
        false_ty = normalize_neg(bot())
        terms = [
            Lam("x", A(), TVar("x")),                        # A -> A
            Pair(Lam("x", A(), TVar("x")),
                 Lam("y", B(), TVar("y"))),                   # (A->A) and (B->B)
            Inl(Lam("x", A(), TVar("x")), B()),               # (A->A) or B
            Inr(Lam("y", B(), TVar("y")), A()),               # A or (B->B)
            Lam("x", bot(), TVar("x")),                       # false -> false (not false)
        ]
        for t in terms:
            ty = normalize_neg(infer({}, t))
            assert ty != false_ty, f"unexpectedly typed {t} as false"

    def test_abort_requires_false_proof(self):
        # In empty context, Abort(unbound_var, A) fails: variable is unbound
        with pytest.raises(TypingError):
            infer({}, Abort(TVar("bot_proof"), A()))

    def test_abort_in_context_gives_target_type(self):
        # In a context with a false assumption, Abort is valid but not closed
        ctx = {"f": bot()}
        ty = infer(ctx, Abort(TVar("f"), A()))
        assert ty == A()

    def test_normalization_preserves_non_false_type(self):
        # Reducing non-false terms cannot produce a term of type false
        false_ty = normalize_neg(bot())
        ctx = {"a": A(), "b": B()}
        terms = [
            App(Lam("x", A(), TVar("x")), TVar("a")),
            Fst(Pair(TVar("a"), TVar("b"))),
            Snd(Pair(TVar("a"), TVar("b"))),
            Pair(Fst(Pair(TVar("a"), TVar("b"))),
                 Snd(Pair(TVar("a"), TVar("b")))),
        ]
        for t in terms:
            ty_before = normalize_neg(infer(ctx, t))
            ty_after  = normalize_neg(infer(ctx, normalize(t)))
            assert ty_before == ty_after, f"type changed after normalization for {t}"
            assert ty_before != false_ty, f"type is false for {t}"

    def test_false_arrow_false_is_not_false(self):
        # false -> false is a valid type but it is not the same as false
        t = Lam("x", bot(), TVar("x"))
        ty = infer({}, t)
        assert normalize_neg(ty) != normalize_neg(bot())
        assert normalize_neg(ty) == imp(bot(), bot())


# ---------------------------------------------------------------------------
# K. CLI term-normalize
# ---------------------------------------------------------------------------

class TestCLITermNormalize:
    def test_basic_redex(self, capsys):
        from stele.cli import main
        rc = main(["term-normalize", "--term", "fst(pair(x, y))"])
        out, _ = capsys.readouterr()
        assert rc == 0
        assert "x" in out

    def test_already_normal_var(self, capsys):
        from stele.cli import main
        rc = main(["term-normalize", "--term", "x"])
        out, _ = capsys.readouterr()
        assert rc == 0
        assert "x" in out

    def test_lam_body_reduces(self, capsys):
        from stele.cli import main
        rc = main(["term-normalize", "--term", "fun x: A => fst(pair(x, x))"])
        out, _ = capsys.readouterr()
        assert rc == 0
        assert "fun x" in out

    def test_multi_step(self, capsys):
        from stele.cli import main
        # fst(pair(fst(pair(a, b)), c)) → a
        rc = main(["term-normalize", "--term", "fst(pair(fst(pair(a, b)), c))"])
        out, _ = capsys.readouterr()
        assert rc == 0
        assert "a" in out

    def test_parse_error(self, capsys):
        from stele.cli import main
        rc = main(["term-normalize", "--term", "???"])
        out, _ = capsys.readouterr()
        assert rc == 1
        assert "parse error" in out.lower() or "X" in out
