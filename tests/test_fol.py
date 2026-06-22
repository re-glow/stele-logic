"""Tests for the first-order proof-term extension.

Covers:
  - ObjVar / ObjConst construction
  - Pred / Forall / Exists in stele.ast
  - fol_free_obj_vars, obj_term_vars
  - subst_obj (formula substitution, capture avoidance)
  - subst_obj_in_term (formula annotations inside proof terms)
  - formula_alpha_equiv_fol
  - FOL proof-term typing: ForallIntro/Elim, ExistsIntro/Elim
  - FOL β-reduction: beta_forall, beta_exists
  - Surface-syntax parsing for formulas and proof terms
  - De Bruijn layer for new constructors
  - Regression: propositional API unchanged
"""
import pytest
from stele.ast import Var, Op, Pred, Forall, Exists, pretty
from stele.core.fol import (
    ObjVar, ObjConst,
    fol_free_obj_vars, obj_term_vars,
    subst_obj, subst_obj_in_obj_term,
    formula_alpha_equiv_fol,
)
from stele.core.terms import (
    TVar, Lam, App, Pair, Fst, Snd, Inl, Inr, Case, Abort,
    ForallIntro, ForallElim, ExistsIntro, ExistsElim,
)
from stele.core.typing import infer, check, TypingError, empty_ctx, extend, normalize_neg
from stele.core.reduce import (
    free_vars, substitute, step, normalize, is_normal,
    subst_obj_in_term, obj_free_in_term,
)
from stele.core.debruijn import (
    to_debruijn, from_debruijn, shift, subst, alpha_equiv,
    DBForallIntro, DBForallElim, DBExistsIntro, DBExistsElim,
    DBBound, DBFree, DBLam,
)
from stele.parser import parse_formula
from stele.core.term_parser import parse_term, TermParseError
from stele.errors import ParseError


# ── Helpers ──────────────────────────────────────────────────────────────────

A = Var("A")
B = Var("B")
P = lambda x: Pred("P", (ObjVar(x),))
Q = lambda x: Pred("Q", (ObjVar(x),))
PQ = lambda x, y: Pred("PQ", (ObjVar(x), ObjVar(y)))


# =============================================================================
# 1. Object terms
# =============================================================================

class TestObjTerms:
    def test_objvar_str(self):
        assert str(ObjVar("a")) == "a"

    def test_objconst_str(self):
        assert str(ObjConst("c")) == "c"

    def test_objvar_frozen(self):
        v = ObjVar("x")
        with pytest.raises(AttributeError):
            v.name = "y"

    def test_objconst_frozen(self):
        c = ObjConst("c")
        with pytest.raises(AttributeError):
            c.name = "d"

    def test_obj_term_vars_var(self):
        assert obj_term_vars(ObjVar("x")) == {"x"}

    def test_obj_term_vars_const(self):
        assert obj_term_vars(ObjConst("c")) == set()

    def test_obj_term_vars_unknown(self):
        assert obj_term_vars("not-an-obj") == set()


# =============================================================================
# 2. FOL formula AST and pretty-printing
# =============================================================================

class TestFOLFormulaAST:
    def test_pred_frozen(self):
        p = Pred("P", (ObjVar("x"),))
        with pytest.raises(AttributeError):
            p.name = "Q"

    def test_forall_frozen(self):
        f = Forall("x", P("x"))
        with pytest.raises(AttributeError):
            f.var = "y"

    def test_exists_frozen(self):
        e = Exists("x", P("x"))
        with pytest.raises(AttributeError):
            e.var = "y"

    def test_pred_pretty(self):
        assert pretty(Pred("P", (ObjVar("a"),))) == "P(a)"

    def test_pred_binary_pretty(self):
        assert pretty(Pred("R", (ObjVar("a"), ObjVar("b")))) == "R(a, b)"

    def test_forall_pretty_toplevel(self):
        r = pretty(Forall("x", P("x")))
        assert r == "forall x. P(x)"

    def test_exists_pretty_toplevel(self):
        r = pretty(Exists("x", P("x")))
        assert r == "exists x. P(x)"

    def test_forall_in_imp_parenthesised(self):
        f = Op("imp", (Forall("x", P("x")), B))
        r = pretty(f)
        assert "(forall x. P(x))" in r

    def test_forall_nested_body(self):
        f = Forall("x", Forall("y", P("x")))
        assert pretty(f) == "forall x. forall y. P(x)"


# =============================================================================
# 3. fol_free_obj_vars
# =============================================================================

class TestFOLFreeObjVars:
    def test_var_empty(self):
        assert fol_free_obj_vars(Var("P")) == set()

    def test_pred_one_arg(self):
        assert fol_free_obj_vars(P("x")) == {"x"}

    def test_pred_two_args(self):
        assert fol_free_obj_vars(PQ("x", "y")) == {"x", "y"}

    def test_forall_binds(self):
        assert fol_free_obj_vars(Forall("x", P("x"))) == set()

    def test_exists_binds(self):
        assert fol_free_obj_vars(Exists("x", P("x"))) == set()

    def test_forall_free_in_body(self):
        # forall x. P(x) and Q(y)  — y is free
        body = Op("and", (P("x"), Q("y")))
        assert fol_free_obj_vars(Forall("x", body)) == {"y"}

    def test_op_collects(self):
        f = Op("and", (P("x"), Q("y")))
        assert fol_free_obj_vars(f) == {"x", "y"}

    def test_nested_forall(self):
        # forall x. forall y. P(x) and Q(y)  — both bound
        f = Forall("x", Forall("y", Op("and", (P("x"), Q("y")))))
        assert fol_free_obj_vars(f) == set()


# =============================================================================
# 4. subst_obj — formula-level capture-avoiding substitution
# =============================================================================

class TestSubstObj:
    def test_pred_simple(self):
        result = subst_obj(P("x"), "x", ObjVar("a"))
        assert result == Pred("P", (ObjVar("a"),))

    def test_pred_no_occurrence(self):
        result = subst_obj(P("y"), "x", ObjVar("a"))
        assert result == P("y")

    def test_pred_const_unchanged(self):
        f = Pred("P", (ObjConst("c"),))
        result = subst_obj(f, "c", ObjVar("a"))
        assert result == f  # ObjConst is not substituted

    def test_var_unchanged(self):
        assert subst_obj(Var("P"), "P", ObjVar("a")) == Var("P")

    def test_forall_shadowed(self):
        # forall x. P(x)  [a/x]  →  unchanged (x is shadowed)
        f = Forall("x", P("x"))
        assert subst_obj(f, "x", ObjVar("a")) == f

    def test_forall_substitute_in_body(self):
        # forall y. P(y) and Q(x)  [a/x]  →  forall y. P(y) and Q(a)
        f = Forall("y", Op("and", (P("y"), Q("x"))))
        result = subst_obj(f, "x", ObjVar("a"))
        assert result == Forall("y", Op("and", (P("y"), Q("a"))))

    def test_forall_capture_avoidance(self):
        # forall a. P(a) and Q(x)  [a/x]  →  rename bound 'a' to avoid capture
        f = Forall("a", Op("and", (P("a"), Q("x"))))
        result = subst_obj(f, "x", ObjVar("a"))
        # The bound 'a' must be renamed because 'a' appears free in replacement
        assert isinstance(result, Forall)
        assert result.var != "a"   # renamed to avoid capture
        # replacement ObjVar("a") is now free in result (that's expected)
        assert "a" in fol_free_obj_vars(result)
        # the renamed bound var is NOT free in result
        assert result.var not in fol_free_obj_vars(result)

    def test_exists_capture_avoidance(self):
        f = Exists("a", Q("x"))
        result = subst_obj(f, "x", ObjVar("a"))
        assert isinstance(result, Exists)
        assert result.var != "a"

    def test_op_recursive(self):
        f = Op("and", (P("x"), Q("x")))
        result = subst_obj(f, "x", ObjVar("b"))
        assert result == Op("and", (P("b"), Q("b")))


# =============================================================================
# 5. formula_alpha_equiv_fol
# =============================================================================

class TestFormulaAlphaEquiv:
    def test_identical_forall(self):
        f = Forall("x", P("x"))
        assert formula_alpha_equiv_fol(f, f)

    def test_alpha_renamed_forall(self):
        f1 = Forall("x", P("x"))
        f2 = Forall("y", P("y"))
        assert formula_alpha_equiv_fol(f1, f2)

    def test_alpha_renamed_exists(self):
        f1 = Exists("x", P("x"))
        f2 = Exists("y", P("y"))
        assert formula_alpha_equiv_fol(f1, f2)

    def test_free_vars_matter(self):
        f1 = Forall("x", P("a"))  # body has free 'a'
        f2 = Forall("x", P("b"))  # body has free 'b'
        assert not formula_alpha_equiv_fol(f1, f2)

    def test_different_connectives(self):
        assert not formula_alpha_equiv_fol(Forall("x", P("x")),
                                           Exists("x", P("x")))

    def test_nested_alpha(self):
        f1 = Forall("x", Forall("y", P("x")))
        f2 = Forall("u", Forall("v", P("u")))
        assert formula_alpha_equiv_fol(f1, f2)

    def test_prop_formula(self):
        assert formula_alpha_equiv_fol(Op("and", (A, B)), Op("and", (A, B)))
        assert not formula_alpha_equiv_fol(Op("and", (A, B)), Op("or", (A, B)))


# =============================================================================
# 6. ForallIntro / ForallElim typing
# =============================================================================

class TestForallTyping:
    def test_forall_intro_basic(self):
        # Γ = {} ⊢  forall_intro x => fun h: P(x) => h  :  forall x. P(x) -> P(x)
        term = ForallIntro("x", Lam("h", P("x"), TVar("h")))
        ty = infer(empty_ctx(), term)
        assert ty == Forall("x", Op("imp", (P("x"), P("x"))))

    def test_forall_elim_basic(self):
        # given t : forall x. P(x) -> P(x),  forall_elim(t, a) : P(a) -> P(a)
        t = ForallIntro("x", Lam("h", P("x"), TVar("h")))
        elim = ForallElim(t, ObjVar("a"))
        ty = infer(empty_ctx(), elim)
        assert ty == Op("imp", (P("a"), P("a")))

    def test_forall_intro_freshness_violation(self):
        # ctx has h : P(x); can't universalise over x
        ctx = extend(empty_ctx(), "h", P("x"))
        term = ForallIntro("x", TVar("h"))
        with pytest.raises(TypingError, match="free in the type of context variable"):
            infer(ctx, term)

    def test_forall_elim_wrong_type(self):
        # trying to eliminate on a non-forall term
        t = Lam("h", P("a"), TVar("h"))
        with pytest.raises(TypingError, match="universal type"):
            infer(empty_ctx(), ForallElim(t, ObjVar("a")))

    def test_forall_intro_two_step(self):
        # forall x. forall y. P(x) -> P(x)  (vacuous inner)
        term = ForallIntro("x", ForallIntro("y", Lam("h", P("x"), TVar("h"))))
        ty = infer(empty_ctx(), term)
        assert ty == Forall("x", Forall("y", Op("imp", (P("x"), P("x")))))

    def test_forall_elim_instantiation(self):
        # forall x. P(x) -> Q(x)  instantiated at 'a' gives  P(a) -> Q(a)
        univ = ForallIntro("x", Lam("h", P("x"), Lam("_", Q("x"), TVar("h"))))
        # actually, build it directly as type annotation
        # This checks subst_obj is wired correctly
        fa_type = Forall("x", Op("imp", (P("x"), Q("x"))))
        ctx = extend(empty_ctx(), "t", fa_type)
        elim = ForallElim(TVar("t"), ObjVar("a"))
        ty = infer(ctx, elim)
        assert ty == Op("imp", (P("a"), Q("a")))

    def test_check_forall_intro(self):
        term = ForallIntro("x", Lam("h", P("x"), TVar("h")))
        expected = Forall("x", Op("imp", (P("x"), P("x"))))
        check(empty_ctx(), term, expected)  # should not raise


# =============================================================================
# 7. ExistsIntro / ExistsElim typing
# =============================================================================

class TestExistsTyping:
    def test_exists_intro_basic(self):
        # pack(a, h, exists x. P(x))  where h : P(a)
        ctx = extend(empty_ctx(), "h", P("a"))
        exists_ty = Exists("x", P("x"))
        term = ExistsIntro(ObjVar("a"), TVar("h"), exists_ty)
        ty = infer(ctx, term)
        assert ty == exists_ty

    def test_exists_intro_wrong_proof_type(self):
        ctx = extend(empty_ctx(), "h", P("b"))  # h : P(b), not P(a)
        exists_ty = Exists("x", P("x"))
        term = ExistsIntro(ObjVar("a"), TVar("h"), exists_ty)
        with pytest.raises(TypingError):
            infer(ctx, term)

    def test_exists_intro_wrong_annotation(self):
        ctx = extend(empty_ctx(), "h", P("a"))
        term = ExistsIntro(ObjVar("a"), TVar("h"), A)  # A is not Exists
        with pytest.raises(TypingError, match="existential type"):
            infer(ctx, term)

    def test_exists_elim_basic(self):
        # exists x. P(x)  →  Q(constant)  where body doesn't use x
        exists_ty = Exists("x", P("x"))
        ctx = extend(empty_ctx(), "e", exists_ty)
        # unpack e as x, h => fun _: Q(c) => fun _: Q(c) => TVar("_")
        # Simpler: body just returns A (doesn't mention x)
        body = Lam("dummy", A, TVar("dummy"))
        term = ExistsElim(TVar("e"), "x", "h", body)
        ty = infer(ctx, term)
        assert ty == Op("imp", (A, A))

    def test_exists_elim_uses_hypothesis(self):
        # Exists x. (A -> A)  — body doesn't mention x, so h has closed type
        exists_ty = Exists("x", Op("imp", (A, A)))
        ctx = extend(empty_ctx(), "e", exists_ty)
        body = TVar("h")   # h : A -> A  (x doesn't appear in A -> A)
        term = ExistsElim(TVar("e"), "x", "h", body)
        ty = infer(ctx, term)
        assert ty == Op("imp", (A, A))

    def test_exists_elim_freshness_violation(self):
        # result type P(x) has x free — should fail
        exists_ty = Exists("x", P("x"))
        ctx = extend(empty_ctx(), "e", exists_ty)
        # body produces P(x) — x appears in result
        body = TVar("h")  # type P(x) — and x is the obj_var
        term = ExistsElim(TVar("e"), "x", "h", body)
        with pytest.raises(TypingError, match="freshness"):
            infer(ctx, term)

    def test_exists_elim_scrutinee_not_exists(self):
        ctx = extend(empty_ctx(), "e", A)
        term = ExistsElim(TVar("e"), "x", "h", TVar("h"))
        with pytest.raises(TypingError, match="existential type"):
            infer(ctx, term)


# =============================================================================
# 8. FOL β-reduction
# =============================================================================

class TestFOLReduction:
    def test_beta_forall(self):
        # ForallElim(ForallIntro(x, Lam(h, P(x), TVar(h))), ObjVar(a))
        # → Lam(h, P(a), TVar(h))
        inner = Lam("h", P("x"), TVar("h"))
        term = ForallElim(ForallIntro("x", inner), ObjVar("a"))
        result = step(term)
        assert result == Lam("h", P("a"), TVar("h"))

    def test_beta_forall_nested_annotation(self):
        # ForallIntro(x, Inl(TVar(h), Q(x)))  →  Inl(TVar(h), Q(a)) after elim
        ctx = extend(empty_ctx(), "h", P("a"))
        body = Inl(TVar("h"), Q("x"))
        term = ForallElim(ForallIntro("x", body), ObjVar("a"))
        result = step(term)
        assert result == Inl(TVar("h"), Q("a"))

    def test_beta_forall_normal_after_step(self):
        inner = Lam("h", P("x"), TVar("h"))
        term = ForallElim(ForallIntro("x", inner), ObjVar("a"))
        result = normalize(term)
        assert result == Lam("h", P("a"), TVar("h"))
        assert is_normal(result)

    def test_beta_exists(self):
        # ExistsElim(ExistsIntro(a, h, exists x. P(x)), x, h, body)
        # where body = TVar(h) and h : P(x)
        # Result: substitute h → proof_from_intro, x → a
        # Then: return P(a)-typed term
        ctx = extend(empty_ctx(), "h0", P("a"))
        exists_ty = Exists("x", P("x"))
        intro = ExistsIntro(ObjVar("a"), TVar("h0"), exists_ty)
        body = TVar("h")  # bound by exists_elim
        term = ExistsElim(intro, "x", "h", body)
        result = step(term)
        # After substituting h → TVar("h0") and x → ObjVar("a"):
        # body = TVar("h0") (proof vars substituted first, no x occurs in TVar)
        assert result == TVar("h0")

    def test_beta_forall_subject_reduction(self):
        # Type-preserving: after β, the type is preserved
        inner = Lam("h", P("x"), TVar("h"))
        term = ForallElim(ForallIntro("x", inner), ObjVar("a"))
        ty_before = infer(empty_ctx(), term)
        result = step(term)
        ty_after = infer(empty_ctx(), result)
        assert ty_before == ty_after

    def test_reduce_under_forall_intro(self):
        # ForallIntro reduces its body
        inner = App(Lam("h", A, TVar("h")), TVar("q"))
        ctx = extend(empty_ctx(), "q", A)
        term = ForallIntro("x", inner)
        result = step(term)
        assert result == ForallIntro("x", TVar("q"))

    def test_free_vars_forall_intro(self):
        # ForallIntro("x", TVar("h")) has "h" free (proof var)
        term = ForallIntro("x", TVar("h"))
        assert free_vars(term) == {"h"}

    def test_free_vars_exists_elim(self):
        # ExistsElim(TVar("e"), "x", "h", TVar("h")) — proof_var "h" is bound
        term = ExistsElim(TVar("e"), "x", "h", TVar("h"))
        assert free_vars(term) == {"e"}


# =============================================================================
# 9. subst_obj_in_term
# =============================================================================

class TestSubstObjInTerm:
    def test_lam_annotation(self):
        # fun h: P(x) => h  [a/x]  →  fun h: P(a) => h
        term = Lam("h", P("x"), TVar("h"))
        result = subst_obj_in_term(term, "x", ObjVar("a"))
        assert result == Lam("h", P("a"), TVar("h"))

    def test_inl_annotation(self):
        term = Inl(TVar("h"), Q("x"))
        result = subst_obj_in_term(term, "x", ObjVar("a"))
        assert result == Inl(TVar("h"), Q("a"))

    def test_forall_intro_shadows(self):
        # forall_intro x => Lam(h, P(x), h)  [a/x] — x is shadowed by ForallIntro
        term = ForallIntro("x", Lam("h", P("x"), TVar("h")))
        result = subst_obj_in_term(term, "x", ObjVar("a"))
        assert result == term  # unchanged

    def test_forall_elim_obj_term(self):
        # ForallElim(fn, ObjVar(x))  [a/x]  →  ForallElim(fn, ObjVar(a))
        fn = TVar("t")
        term = ForallElim(fn, ObjVar("x"))
        result = subst_obj_in_term(term, "x", ObjVar("a"))
        assert result == ForallElim(fn, ObjVar("a"))

    def test_exists_intro_witness(self):
        # ExistsIntro(ObjVar(x), proof, exists y. P(x))  [a/x]
        # → ExistsIntro(ObjVar(a), proof, exists y. P(a))
        exists_ty = Exists("y", P("x"))
        term = ExistsIntro(ObjVar("x"), TVar("h"), exists_ty)
        result = subst_obj_in_term(term, "x", ObjVar("a"))
        assert result == ExistsIntro(ObjVar("a"), TVar("h"), Exists("y", P("a")))

    def test_tvar_unchanged(self):
        assert subst_obj_in_term(TVar("h"), "x", ObjVar("a")) == TVar("h")


# =============================================================================
# 10. obj_free_in_term
# =============================================================================

class TestObjFreeInTerm:
    def test_tvar_empty(self):
        assert obj_free_in_term(TVar("h")) == set()

    def test_lam_annotation(self):
        assert obj_free_in_term(Lam("h", P("x"), TVar("h"))) == {"x"}

    def test_forall_intro_binds(self):
        assert obj_free_in_term(ForallIntro("x", Lam("h", P("x"), TVar("h")))) == set()

    def test_forall_elim_obj_term(self):
        assert obj_free_in_term(ForallElim(TVar("t"), ObjVar("a"))) == {"a"}

    def test_exists_elim_binds(self):
        term = ExistsElim(TVar("e"), "x", "h", Lam("_", P("x"), TVar("h")))
        # x is bound by ExistsElim, so P("x") reference is bound
        assert obj_free_in_term(term) == set()


# =============================================================================
# 11. Formula parsing (FOL surface syntax)
# =============================================================================

class TestFOLFormulaParsing:
    def test_pred_one_arg(self):
        f = parse_formula("P(a)")
        assert f == Pred("P", (ObjVar("a"),))

    def test_pred_two_args(self):
        f = parse_formula("R(a, b)")
        assert f == Pred("R", (ObjVar("a"), ObjVar("b")))

    def test_forall(self):
        f = parse_formula("forall x. P(x)")
        assert f == Forall("x", Pred("P", (ObjVar("x"),)))

    def test_exists(self):
        f = parse_formula("exists x. P(x)")
        assert f == Exists("x", Pred("P", (ObjVar("x"),)))

    def test_forall_imp(self):
        # forall x. P(x) -> Q(x)  parses as  forall x. (P(x) -> Q(x))
        f = parse_formula("forall x. P(x) -> Q(x)")
        assert isinstance(f, Forall)
        assert isinstance(f.body, Op) and f.body.sym == "imp"

    def test_propositional_backward_compat(self):
        # existing propositional parsing still works
        f = parse_formula("P and Q -> R")
        assert isinstance(f, Op) and f.sym == "imp"

    def test_pred_in_imp(self):
        f = parse_formula("P(a) -> Q(b)")
        assert isinstance(f, Op) and f.sym == "imp"
        assert f.args[0] == Pred("P", (ObjVar("a"),))

    def test_forall_in_paren(self):
        f = parse_formula("(forall x. P(x)) -> Q")
        assert isinstance(f, Op) and f.sym == "imp"
        assert isinstance(f.args[0], Forall)

    def test_parse_error_missing_dot(self):
        with pytest.raises(ParseError):
            parse_formula("forall x P(x)")

    def test_parse_error_missing_var(self):
        with pytest.raises(ParseError):
            parse_formula("forall . P(x)")


# =============================================================================
# 12. Proof-term surface syntax (FOL terms)
# =============================================================================

class TestFOLTermParsing:
    def test_forall_intro(self):
        t = parse_term("forall_intro x => fun h: P(x) => h")
        assert isinstance(t, ForallIntro)
        assert t.obj_var == "x"
        assert isinstance(t.body, Lam)

    def test_forall_elim(self):
        t = parse_term("forall_elim(f, a)")
        assert isinstance(t, ForallElim)
        assert t.fn == TVar("f")
        assert t.obj_term == ObjVar("a")

    def test_exists_intro(self):
        t = parse_term("exists_intro(a, h, exists x. P(x))")
        assert isinstance(t, ExistsIntro)
        assert t.witness == ObjVar("a")
        assert t.proof == TVar("h")
        assert isinstance(t.exists_type, Exists)

    def test_exists_elim(self):
        t = parse_term("exists_elim(e, x, h, h)")
        assert isinstance(t, ExistsElim)
        assert t.scrutinee == TVar("e")
        assert t.obj_var == "x"
        assert t.proof_var == "h"
        assert t.body == TVar("h")

    def test_forall_intro_nested(self):
        t = parse_term("forall_intro x => forall_intro y => fun h: P(x) => h")
        assert isinstance(t, ForallIntro)
        assert isinstance(t.body, ForallIntro)

    def test_parse_error_forall_elim_no_parens(self):
        with pytest.raises(TermParseError):
            parse_term("forall_elim f a")  # missing parens


# =============================================================================
# 13. De Bruijn for FOL constructors
# =============================================================================

class TestFOLDebruijn:
    def test_forall_intro_to_db(self):
        # ForallIntro("x", Lam("h", P(x), TVar("h")))
        term = ForallIntro("x", Lam("h", P("x"), TVar("h")))
        db = to_debruijn(term)
        assert isinstance(db, DBForallIntro)
        assert db.obj_var == "x"  # obj_var kept named
        assert isinstance(db.body, DBLam)  # proof binder converted

    def test_forall_elim_to_db(self):
        term = ForallElim(TVar("f"), ObjVar("a"))
        db = to_debruijn(term)
        assert isinstance(db, DBForallElim)
        assert db.obj_term == ObjVar("a")  # kept named

    def test_exists_intro_to_db(self):
        term = ExistsIntro(ObjVar("a"), TVar("h"), Exists("x", P("x")))
        db = to_debruijn(term)
        assert isinstance(db, DBExistsIntro)
        assert db.witness == ObjVar("a")

    def test_exists_elim_proof_var_indexed(self):
        # ExistsElim: proof_var becomes DBBound(0) in body
        term = ExistsElim(TVar("e"), "x", "h", TVar("h"))
        db = to_debruijn(term)
        assert isinstance(db, DBExistsElim)
        assert db.obj_var == "x"
        # body should reference DBBound(0) for h
        from stele.core.debruijn import DBBound
        assert db.body == DBBound(0)

    def test_forall_intro_from_db(self):
        term = ForallIntro("x", Lam("h", P("x"), TVar("h")))
        db = to_debruijn(term)
        reconstructed = from_debruijn(db)
        assert isinstance(reconstructed, ForallIntro)
        assert reconstructed.obj_var == "x"

    def test_exists_elim_from_db(self):
        term = ExistsElim(TVar("e"), "x", "h", TVar("h"))
        db = to_debruijn(term)
        reconstructed = from_debruijn(db)
        assert isinstance(reconstructed, ExistsElim)
        assert reconstructed.obj_var == "x"
        # proof_var may differ from "h" (fresh name generated)

    def test_alpha_equiv_forall_intro_proof_vars(self):
        # Two ForallIntros with different PROOF variable names in the body
        # are α-equivalent (same proof structure)
        t1 = ForallIntro("x", Lam("h", P("x"), TVar("h")))
        t2 = ForallIntro("x", Lam("z", P("x"), TVar("z")))
        assert alpha_equiv(t1, t2)

    def test_shift_forall_intro(self):
        # ForallIntro does not add a proof binder; shift treats it transparently
        term = ForallIntro("x", Lam("h", P("x"), TVar("h")))
        db = to_debruijn(term)
        shifted = shift(db, 1, 0)
        assert isinstance(shifted, DBForallIntro)

    def test_subst_exists_elim(self):
        # ExistsElim: subst goes into scrutinee and body (under +1)
        term = ExistsElim(TVar("e"), "x", "h", TVar("h"))
        db = to_debruijn(term)
        # No error on subst
        from stele.core.debruijn import DBFree
        result = subst(db, 0, DBFree("q"))
        assert isinstance(result, DBExistsElim)


# =============================================================================
# 14. Regression: propositional API unchanged
# =============================================================================

class TestRegression:
    def test_propositional_parse_unchanged(self):
        f = parse_formula("P -> Q")
        assert isinstance(f, Op) and f.sym == "imp"

    def test_propositional_parse_not(self):
        f = parse_formula("not P")
        assert isinstance(f, Op) and f.sym == "not"

    def test_kernel_not_import_fol(self):
        import ast as _ast, pathlib
        src = pathlib.Path("stele/kernel.py").read_text(encoding="utf-8")
        tree = _ast.parse(src)
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.Import, _ast.ImportFrom)):
                if isinstance(node, _ast.ImportFrom):
                    assert node.module is None or "fol" not in node.module
                else:
                    for alias in node.names:
                        assert "fol" not in alias.name

    def test_proof_term_typing_unchanged(self):
        # Basic Lam/App still works: (fun h: A => h)(w) : A
        ctx = extend(empty_ctx(), "w", A)
        term = App(Lam("h", A, TVar("h")), TVar("w"))
        ty = infer(ctx, term)
        assert ty == A

    def test_normalize_unchanged(self):
        term = App(Lam("h", A, TVar("h")), TVar("q"))
        ctx = extend(empty_ctx(), "q", A)
        assert normalize(term) == TVar("q")

    def test_alpha_equiv_unchanged(self):
        from stele.core.debruijn import alpha_equiv
        t1 = Lam("x", A, TVar("x"))
        t2 = Lam("y", A, TVar("y"))
        assert alpha_equiv(t1, t2)
