"""Tests for stele.core — proof-term calculus and bidirectional typechecker.

Coverage
--------
Well-typed terms:
  1. Identity                 λx:A. x : A -> A
  2. K combinator             λx:A. λy:B. x : A -> B -> A
  3. Modus ponens application f a : B  when f:A->B, a:A
  4. Conjunction              Pair, Fst, Snd
  5. Disjunction              Inl, Inr, Case
  6. Bottom                   Abort
  7. Negation                 not A = A -> false (convention documented + tested)

Ill-typed terms:
  1. Unbound variable
  2. Applying a non-function
  3. Argument type mismatch
  4. Fst on a non-pair
  5. Case branch result mismatch
  6. Abort on non-false

Invariant check:
  * kernel.py does not import stele.core
  * stele.core.typing does not import stele.kernel
"""
import pytest

from stele.ast import Var as FVar, Op
from stele.core import (
    TVar, Lam, App,
    Pair, Fst, Snd,
    Inl, Inr, Case,
    Abort,
    infer, check,
    TypingError,
    empty_ctx, extend,
    normalize_neg, is_imp, is_and, is_or, is_false, mk_not,
)

# ---------------------------------------------------------------------------
# Shorthand formula constructors used throughout the tests
# ---------------------------------------------------------------------------

A = FVar("A")
B = FVar("B")
C = FVar("C")

_false = Op("bot", ())

def _imp(x, y):  return Op("imp", (x, y))
def _and(x, y):  return Op("and", (x, y))
def _or(x, y):   return Op("or",  (x, y))
def _not(x):     return Op("not", (x,))


# ===========================================================================
# 1. Well-typed terms — implication
# ===========================================================================

class TestImplication:

    def test_identity_infer(self):
        """λx:A. x synthesises A -> A."""
        t = Lam("x", A, TVar("x"))
        assert infer(empty_ctx(), t) == _imp(A, A)

    def test_identity_check(self):
        """λx:A. x checks against A -> A."""
        t = Lam("x", A, TVar("x"))
        check(empty_ctx(), t, _imp(A, A))  # must not raise

    def test_k_combinator_infer(self):
        """λx:A. λy:B. x synthesises A -> B -> A."""
        t = Lam("x", A, Lam("y", B, TVar("x")))
        expected = _imp(A, _imp(B, A))
        assert infer(empty_ctx(), t) == expected

    def test_k_combinator_check(self):
        t = Lam("x", A, Lam("y", B, TVar("x")))
        check(empty_ctx(), t, _imp(A, _imp(B, A)))

    def test_modus_ponens_app_infer(self):
        """App(f, a) : B when f:A->B and a:A."""
        ctx = extend(extend(empty_ctx(), "f", _imp(A, B)), "a", A)
        t = App(TVar("f"), TVar("a"))
        assert infer(ctx, t) == B

    def test_var_looks_up_context(self):
        ctx = extend(empty_ctx(), "x", A)
        assert infer(ctx, TVar("x")) == A

    def test_nested_app(self):
        """App(App(f, a), b) : C  when f:A->B->C, a:A, b:B."""
        ctx = extend(
            extend(extend(empty_ctx(), "f", _imp(A, _imp(B, C))), "a", A),
            "b", B,
        )
        t = App(App(TVar("f"), TVar("a")), TVar("b"))
        assert infer(ctx, t) == C


# ===========================================================================
# 2. Well-typed terms — conjunction
# ===========================================================================

class TestConjunction:

    def test_pair_intro_infer(self):
        ctx = extend(extend(empty_ctx(), "a", A), "b", B)
        t = Pair(TVar("a"), TVar("b"))
        assert infer(ctx, t) == _and(A, B)

    def test_pair_intro_check(self):
        ctx = extend(extend(empty_ctx(), "a", A), "b", B)
        t = Pair(TVar("a"), TVar("b"))
        check(ctx, t, _and(A, B))

    def test_fst_infer(self):
        ctx = extend(empty_ctx(), "p", _and(A, B))
        assert infer(ctx, Fst(TVar("p"))) == A

    def test_snd_infer(self):
        ctx = extend(empty_ctx(), "p", _and(A, B))
        assert infer(ctx, Snd(TVar("p"))) == B

    def test_fst_nested(self):
        """Fst of a nested pair."""
        ctx = extend(empty_ctx(), "p", _and(_and(A, B), C))
        assert infer(ctx, Fst(TVar("p"))) == _and(A, B)

    def test_pair_then_fst(self):
        ctx = extend(extend(empty_ctx(), "a", A), "b", B)
        t = Fst(Pair(TVar("a"), TVar("b")))
        assert infer(ctx, t) == A

    def test_pair_check_mode(self):
        """Pair in check mode decomposes expected type without requiring
        components to be inferrable independently first."""
        ctx = extend(extend(empty_ctx(), "a", A), "b", B)
        check(ctx, Pair(TVar("a"), TVar("b")), _and(A, B))


# ===========================================================================
# 3. Well-typed terms — disjunction
# ===========================================================================

class TestDisjunction:

    def test_inl_infer(self):
        ctx = extend(empty_ctx(), "a", A)
        t = Inl(TVar("a"), B)
        assert infer(ctx, t) == _or(A, B)

    def test_inr_infer(self):
        ctx = extend(empty_ctx(), "b", B)
        t = Inr(TVar("b"), A)
        assert infer(ctx, t) == _or(A, B)

    def test_inl_check(self):
        ctx = extend(empty_ctx(), "a", A)
        check(ctx, Inl(TVar("a"), B), _or(A, B))

    def test_inr_check(self):
        ctx = extend(empty_ctx(), "b", B)
        check(ctx, Inr(TVar("b"), A), _or(A, B))

    def test_case_infer(self):
        """case e of inl x -> x | inr y -> y : A  when e : A or A."""
        ctx = extend(empty_ctx(), "e", _or(A, A))
        t = Case(TVar("e"), "x", TVar("x"), "y", TVar("y"))
        assert infer(ctx, t) == A

    def test_case_infer_branches_produce_b(self):
        """case e of inl x -> f x | inr y -> g y : B."""
        ctx = extend(
            extend(extend(empty_ctx(), "e", _or(A, A)), "f", _imp(A, B)),
            "g", _imp(A, B),
        )
        t = Case(
            TVar("e"),
            "x", App(TVar("f"), TVar("x")),
            "y", App(TVar("g"), TVar("y")),
        )
        assert infer(ctx, t) == B

    def test_case_check(self):
        ctx = extend(empty_ctx(), "e", _or(A, B))
        # both branches introduce a lam-bound constant that ignores its input
        t = Case(
            TVar("e"),
            "x", Lam("_", A, TVar("x")),   # A -> A (but won't be used here)
            "y", Lam("_", B, TVar("y")),   # B -> B
        )
        # checking against A -> A / B -> B independently is ambiguous;
        # infer mode requires branches to agree — use a simpler case:
        ctx2 = extend(empty_ctx(), "e", _or(A, A))
        t2 = Case(TVar("e"), "x", TVar("x"), "y", TVar("y"))
        check(ctx2, t2, A)

    def test_case_shadows_outer_var(self):
        """Case branches shadow outer bindings for their pattern variable."""
        ctx = extend(extend(empty_ctx(), "e", _or(A, B)), "x", B)
        # left branch binds "x" to A, shadowing outer "x":B
        t = Case(TVar("e"), "x", TVar("x"), "y", TVar("y"))
        # left branch infers A, right branch infers B — mismatch
        with pytest.raises(TypingError, match="branch"):
            infer(ctx, t)


# ===========================================================================
# 4. Well-typed terms — bottom
# ===========================================================================

class TestBottom:

    def test_abort_infer(self):
        """abort absurd C  :  C  when absurd : false."""
        ctx = extend(empty_ctx(), "absurd", _false)
        t = Abort(TVar("absurd"), C)
        assert infer(ctx, t) == C

    def test_abort_check(self):
        ctx = extend(empty_ctx(), "absurd", _false)
        check(ctx, Abort(TVar("absurd"), C), C)

    def test_abort_any_target_type(self):
        ctx = extend(empty_ctx(), "absurd", _false)
        # ex falso: any type is derivable
        for ty in [A, B, _imp(A, B), _and(A, B), _or(A, B)]:
            assert infer(ctx, Abort(TVar("absurd"), ty)) == ty


# ===========================================================================
# 5. Negation as implication to false
# ===========================================================================

class TestNegation:

    def test_mk_not_builds_imp_form(self):
        """mk_not(A) produces A -> false (not Op('not',...))."""
        result = mk_not(A)
        assert result == _imp(A, _false)

    def test_normalize_neg_converts_not(self):
        """normalize_neg converts Op('not', (A,)) to Op('imp', (A, false))."""
        not_a = _not(A)
        norm = normalize_neg(not_a)
        assert norm == _imp(A, _false)

    def test_normalize_neg_idempotent_on_imp_form(self):
        imp_false = _imp(A, _false)
        assert normalize_neg(imp_false) == imp_false

    def test_normalize_neg_recursive(self):
        """not (not A) normalises to (A -> false) -> false."""
        not_not_a = _not(_not(A))
        norm = normalize_neg(not_not_a)
        expected = _imp(_imp(A, _false), _false)
        assert norm == expected

    def test_lam_over_not_type_works(self):
        """λx:(not A). x  should have type (not A) -> (not A).

        The type checker accepts Op('not', ...) as a parameter type and
        normalises for comparison, so the resulting type is A->false -> A->false
        when compared with _feq.
        """
        not_a = _not(A)
        t = Lam("x", not_a, TVar("x"))
        result = infer(empty_ctx(), t)
        # result is Op("imp", (not_a, not_a)) which normalises to
        # (A->false) -> (A->false)
        from stele.core.typing import _feq
        assert _feq(result, _imp(mk_not(A), mk_not(A)))

    def test_check_lam_against_not_type(self):
        """check accepts Lam whose parameter carries a not-type annotation.

        λx:(not A). x  has type  (not A) -> (not A).
        The checker normalises Op('not', ...) on both sides, so the
        annotation and expected type agree in normalised form.
        """
        not_a = _not(A)
        t = Lam("x", not_a, TVar("x"))
        # correct expected type: (not A) -> (not A)
        check(empty_ctx(), t, _imp(not_a, not_a))

    def test_negation_convention_documented(self):
        """Sanity-check that the _feq convention works for negation."""
        from stele.core.typing import _feq
        assert _feq(_not(A), _imp(A, _false))
        assert _feq(_imp(A, _false), _not(A))

    def test_is_imp_recognises_not(self):
        assert is_imp(_not(A))

    def test_is_false_recognises_bot(self):
        assert is_false(_false)
        assert not is_false(A)


# ===========================================================================
# 6. Context helpers
# ===========================================================================

class TestContext:

    def test_empty_ctx_is_empty(self):
        assert empty_ctx() == {}

    def test_extend_non_destructive(self):
        ctx = empty_ctx()
        ctx2 = extend(ctx, "x", A)
        assert "x" not in ctx
        assert ctx2["x"] == A

    def test_extend_shadowing(self):
        ctx = extend(extend(empty_ctx(), "x", A), "x", B)
        assert ctx["x"] == B

    def test_extend_multiple(self):
        ctx = extend(extend(empty_ctx(), "x", A), "y", B)
        assert ctx["x"] == A
        assert ctx["y"] == B


# ===========================================================================
# 7. Ill-typed terms — should raise TypingError
# ===========================================================================

class TestIllTyped:

    def test_unbound_variable(self):
        """Variable not in context raises TypingError."""
        with pytest.raises(TypingError, match="unbound"):
            infer(empty_ctx(), TVar("x"))

    def test_apply_non_function(self):
        """Applying a non-function type raises TypingError."""
        ctx = extend(extend(empty_ctx(), "a", A), "b", B)
        # 'a' has type A (a proposition variable, not an implication)
        with pytest.raises(TypingError, match="implication"):
            infer(ctx, App(TVar("a"), TVar("b")))

    def test_argument_type_mismatch(self):
        """Argument type does not match function parameter type."""
        ctx = extend(extend(empty_ctx(), "f", _imp(A, B)), "b", B)
        # f expects A, but we supply b:B
        with pytest.raises(TypingError):
            infer(ctx, App(TVar("f"), TVar("b")))

    def test_fst_on_non_pair(self):
        """Fst applied to a non-conjunction type raises TypingError."""
        ctx = extend(empty_ctx(), "x", A)
        with pytest.raises(TypingError, match="conjunction"):
            infer(ctx, Fst(TVar("x")))

    def test_snd_on_non_pair(self):
        ctx = extend(empty_ctx(), "x", A)
        with pytest.raises(TypingError, match="conjunction"):
            infer(ctx, Snd(TVar("x")))

    def test_case_branch_mismatch(self):
        """Case branches with different result types raises TypingError."""
        # scrutinee : A or B; left branch : A; right branch : B
        ctx = extend(empty_ctx(), "e", _or(A, B))
        t = Case(TVar("e"), "x", TVar("x"), "y", TVar("y"))
        with pytest.raises(TypingError, match="branch"):
            infer(ctx, t)

    def test_case_scrutinee_not_disjunction(self):
        ctx = extend(empty_ctx(), "e", A)
        t = Case(TVar("e"), "x", TVar("x"), "y", TVar("y"))
        with pytest.raises(TypingError, match="disjunction"):
            infer(ctx, t)

    def test_abort_on_non_false(self):
        """Abort applied to a non-false term raises TypingError."""
        ctx = extend(empty_ctx(), "x", A)
        with pytest.raises(TypingError):
            infer(ctx, Abort(TVar("x"), B))

    def test_check_type_mismatch(self):
        """check raises when inferred type != expected type."""
        ctx = extend(empty_ctx(), "x", A)
        with pytest.raises(TypingError, match="mismatch"):
            check(ctx, TVar("x"), B)

    def test_lam_annotation_mismatch_in_check(self):
        """Lam parameter annotation does not match expected antecedent."""
        # Lam("x", A, TVar("x")) has annotation A; check against B -> B
        t = Lam("x", A, TVar("x"))
        with pytest.raises(TypingError, match="parameter type"):
            check(empty_ctx(), t, _imp(B, B))

    def test_inl_annotation_mismatch_in_check(self):
        """Inl right-type annotation does not match expected right disjunct."""
        ctx = extend(empty_ctx(), "a", A)
        t = Inl(TVar("a"), B)  # annotation says right is B
        # but we check against A or C
        with pytest.raises(TypingError, match="right-type"):
            check(ctx, t, _or(A, C))

    def test_inr_annotation_mismatch_in_check(self):
        ctx = extend(empty_ctx(), "b", B)
        t = Inr(TVar("b"), A)  # annotation says left is A
        # check against C or B (left should be C, not A)
        with pytest.raises(TypingError, match="left-type"):
            check(ctx, t, _or(C, B))


# ===========================================================================
# 8. Invariant: trusted kernel independence
# ===========================================================================

class TestKernelInvariance:

    def test_kernel_does_not_import_core(self):
        """kernel.py must not import stele.core (trusted boundary)."""
        import ast as _ast
        import pathlib
        kernel_src = (
            pathlib.Path(__file__).parent.parent / "stele" / "kernel.py"
        ).read_text(encoding="utf-8")
        tree = _ast.parse(kernel_src)
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    assert "core" not in alias.name, (
                        f"kernel.py imports {alias.name!r} — "
                        "trusted kernel must not depend on stele.core"
                    )
            if isinstance(node, _ast.ImportFrom):
                mod = node.module or ""
                assert "core" not in mod, (
                    f"kernel.py has 'from {mod} import ...' — "
                    "trusted kernel must not depend on stele.core"
                )

    def test_typing_does_not_import_kernel(self):
        """stele.core.typing must not import stele.kernel."""
        import ast as _ast
        import pathlib
        typing_src = (
            pathlib.Path(__file__).parent.parent
            / "stele" / "core" / "typing.py"
        ).read_text(encoding="utf-8")
        tree = _ast.parse(typing_src)
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    assert "kernel" not in alias.name
            if isinstance(node, _ast.ImportFrom):
                mod = node.module or ""
                assert "kernel" not in mod


# ===========================================================================
# 9. Formula helper predicates
# ===========================================================================

class TestFormulaHelpers:

    def test_is_imp_on_imp(self):
        assert is_imp(_imp(A, B))

    def test_is_imp_on_not(self):
        assert is_imp(_not(A))

    def test_is_imp_false_for_var(self):
        assert not is_imp(A)

    def test_is_imp_false_for_and(self):
        assert not is_imp(_and(A, B))

    def test_is_and(self):
        assert is_and(_and(A, B))
        assert not is_and(_or(A, B))
        assert not is_and(A)

    def test_is_or(self):
        assert is_or(_or(A, B))
        assert not is_or(_and(A, B))

    def test_is_false(self):
        assert is_false(_false)
        assert not is_false(A)

    def test_mk_not_roundtrip(self):
        """mk_not(A) normalised equals normalize_neg(not A)."""
        assert mk_not(A) == normalize_neg(_not(A))
