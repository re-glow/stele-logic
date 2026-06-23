"""Tests for FOL surface syntax: formula parser, term parser, CLI, examples.

Parts:
  1. Formula parser — forall/exists/predicates/precedence/scope
  2. Object term parsing
  3. Term parser — quantifier proof terms
  4. Typechecking from surface syntax
  5. Reduction from surface syntax
  6. CLI term-check with --context
  7. Example files
  8. Negative examples
  9. Propositional regression
"""
import subprocess
import sys
import pytest

from stele.ast import Var, Op, Pred, Forall, Exists
from stele.core.fol import ObjVar, ObjConst
from stele.core.terms import (TVar, Lam, ForallIntro, ForallElim,
                               ExistsIntro, ExistsElim)
from stele.core.typing import (infer, check, empty_ctx, extend,
                                TypingError, normalize_neg)
from stele.core.term_parser import parse_term, TermParseError
from stele.core.reduce import step, normalize
from stele.parser import parse_formula
from stele.errors import ParseError

PY = sys.executable
P = lambda x: Pred("P", (ObjVar(x),))
Q = lambda x: Pred("Q", (ObjVar(x),))
R = lambda x, y: Pred("R", (ObjVar(x), ObjVar(y)))


# =============================================================================
# 1. Formula parser — forall / exists / predicates / precedence / scope
# =============================================================================

class TestFormulaParserFOL:
    def test_forall_simple(self):
        f = parse_formula("forall x. P(x)")
        assert f == Forall("x", P("x"))

    def test_exists_simple(self):
        f = parse_formula("exists x. P(x)")
        assert f == Exists("x", P("x"))

    def test_forall_nested(self):
        f = parse_formula("forall x. forall y. R(x, y)")
        assert isinstance(f, Forall) and isinstance(f.body, Forall)

    def test_exists_nested(self):
        f = parse_formula("exists x. exists y. R(x, y)")
        assert isinstance(f, Exists) and isinstance(f.body, Exists)

    def test_forall_exists_mixed(self):
        f = parse_formula("forall x. exists y. R(x, y)")
        assert isinstance(f, Forall) and isinstance(f.body, Exists)

    def test_exists_forall_mixed(self):
        f = parse_formula("exists x. forall y. R(x, y)")
        assert isinstance(f, Exists) and isinstance(f.body, Forall)

    # Wide-scope quantifier rule: forall x. A -> B  means  forall x. (A -> B)
    def test_forall_wide_scope_imp(self):
        f = parse_formula("forall x. P(x) -> Q(x)")
        assert isinstance(f, Forall)
        assert isinstance(f.body, Op) and f.body.sym == "imp"

    def test_exists_wide_scope_imp(self):
        f = parse_formula("exists x. P(x) -> Q(x)")
        assert isinstance(f, Exists)
        assert isinstance(f.body, Op) and f.body.sym == "imp"

    # Parentheses narrow quantifier scope
    def test_forall_narrow_scope_with_parens(self):
        f = parse_formula("(forall x. P(x)) -> Q")
        assert isinstance(f, Op) and f.sym == "imp"
        assert isinstance(f.args[0], Forall)

    def test_exists_narrow_scope_with_parens(self):
        f = parse_formula("(exists x. P(x)) -> Q")
        assert isinstance(f, Op) and f.sym == "imp"
        assert isinstance(f.args[0], Exists)

    # Quantifier on RHS of ->
    def test_imp_rhs_forall(self):
        f = parse_formula("P -> forall x. Q(x)")
        assert isinstance(f, Op) and f.sym == "imp"
        assert isinstance(f.args[1], Forall)

    def test_imp_rhs_exists(self):
        f = parse_formula("P -> exists x. Q(x)")
        assert isinstance(f, Op) and f.sym == "imp"
        assert isinstance(f.args[1], Exists)

    # Multi-quantifier formulae that require correct imp right-hand recursion
    def test_imp_chain_ending_in_forall(self):
        f = parse_formula("(forall x. P(x)) -> (forall x. P(x)) -> forall x. P(x)")
        assert isinstance(f, Op) and f.sym == "imp"
        assert isinstance(f.args[1], Op) and f.args[1].sym == "imp"
        assert isinstance(f.args[1].args[1], Forall)

    def test_forall_and_body(self):
        f = parse_formula("forall x. P(x) and Q(x)")
        assert isinstance(f, Forall)
        assert isinstance(f.body, Op) and f.body.sym == "and"

    def test_forall_not_body(self):
        f = parse_formula("forall x. not P(x)")
        assert isinstance(f, Forall)
        assert isinstance(f.body, Op) and f.body.sym == "not"

    def test_error_missing_dot(self):
        with pytest.raises(ParseError):
            parse_formula("forall x P(x)")

    def test_error_missing_var(self):
        with pytest.raises(ParseError):
            parse_formula("forall . P(x)")

    def test_nullary_predicate_allowed(self):
        # P() parses as a nullary predicate (0-ary); no error
        f = parse_formula("P()")
        assert isinstance(f, Pred) and f.name == "P" and f.args == ()

    # Propositional formulas still work unchanged
    def test_prop_var_unchanged(self):
        assert parse_formula("A") == Var("A")

    def test_prop_imp_unchanged(self):
        f = parse_formula("A -> B")
        assert f == Op("imp", (Var("A"), Var("B")))

    def test_prop_not_unchanged(self):
        f = parse_formula("not A")
        assert f == Op("not", (Var("A"),))

    def test_prop_and_or_unchanged(self):
        f = parse_formula("A and B or C")
        assert isinstance(f, Op) and f.sym == "or"


# =============================================================================
# 2. Object term parsing
# =============================================================================

class TestObjectTermParsing:
    def test_objvar_in_predicate(self):
        f = parse_formula("P(a)")
        assert f == Pred("P", (ObjVar("a"),))

    def test_two_args(self):
        f = parse_formula("R(a, b)")
        assert f == Pred("R", (ObjVar("a"), ObjVar("b")))

    def test_bound_var_under_forall(self):
        f = parse_formula("forall x. P(x)")
        assert isinstance(f, Forall) and f.var == "x"
        assert f.body == Pred("P", (ObjVar("x"),))

    def test_different_vars_different_preds(self):
        f = parse_formula("P(a) and Q(b)")
        assert f.args[0] == Pred("P", (ObjVar("a"),))
        assert f.args[1] == Pred("Q", (ObjVar("b"),))

    def test_constant_style_arg(self):
        # All identifiers in pred args become ObjVar (parser convention)
        f = parse_formula("P(c)")
        assert f == Pred("P", (ObjVar("c"),))

    def test_mixed_vars_in_nested(self):
        f = parse_formula("forall x. R(x, a)")
        assert isinstance(f, Forall)
        assert f.body == Pred("R", (ObjVar("x"), ObjVar("a")))


# =============================================================================
# 3. Term parser — quantifier proof terms
# =============================================================================

class TestTermParserFOL:
    def test_forall_intro(self):
        t = parse_term("forall_intro x => fun h: P(x) => h")
        assert isinstance(t, ForallIntro) and t.obj_var == "x"
        assert isinstance(t.body, Lam)

    def test_forall_elim_syntax(self):
        t = parse_term("forall_elim(f, a)")
        assert isinstance(t, ForallElim)
        assert t.fn == TVar("f")
        assert t.obj_term == ObjVar("a")

    def test_exists_intro_syntax(self):
        t = parse_term("exists_intro(a, h, exists x. P(x))")
        assert isinstance(t, ExistsIntro)
        assert t.witness == ObjVar("a")
        assert t.proof == TVar("h")
        assert t.exists_type == Exists("x", P("x"))

    def test_exists_elim_syntax(self):
        t = parse_term("exists_elim(e, x, h, h)")
        assert isinstance(t, ExistsElim)
        assert t.scrutinee == TVar("e")
        assert t.obj_var == "x"
        assert t.proof_var == "h"
        assert t.body == TVar("h")

    def test_nested_forall_intro(self):
        t = parse_term("forall_intro x => forall_intro y => fun h: P(x) => h")
        assert isinstance(t, ForallIntro)
        assert isinstance(t.body, ForallIntro)

    def test_forall_elim_application(self):
        # forall_elim(f, x)(arg) — application of the result
        t = parse_term("forall_elim(f, x)(arg)")
        from stele.core.terms import App
        assert isinstance(t, App)
        assert isinstance(t.fn, ForallElim)

    def test_forall_intro_wide_body(self):
        # forall_intro captures everything after =>
        t = parse_term("forall_intro x => forall_intro y => fun h: P(x) => h")
        assert t.obj_var == "x"
        inner = t.body
        assert isinstance(inner, ForallIntro) and inner.obj_var == "y"

    def test_exists_intro_with_nested_exists(self):
        t = parse_term("exists_intro(x, h, exists y. P(y))")
        assert isinstance(t, ExistsIntro)
        assert t.exists_type == Exists("y", P("y"))

    def test_error_forall_elim_no_parens(self):
        with pytest.raises(TermParseError):
            parse_term("forall_elim f a")  # needs parens

    def test_propositional_fun_unchanged(self):
        t = parse_term("fun x: A => x")
        assert isinstance(t, Lam) and t.var == "x"

    def test_propositional_pair_unchanged(self):
        from stele.core.terms import Pair
        t = parse_term("pair(x, y)")
        assert isinstance(t, Pair)

    def test_propositional_case_unchanged(self):
        from stele.core.terms import Case
        t = parse_term("case e of inl x => x | inr y => y")
        assert isinstance(t, Case)


# =============================================================================
# 4. Typechecking from surface syntax
# =============================================================================

class TestTypecheckingFOL:
    def test_universal_identity(self):
        t = parse_term("forall_intro x => fun h: P(x) => h")
        ty = infer(empty_ctx(), t)
        assert ty == Forall("x", Op("imp", (P("x"), P("x"))))

    def test_universal_elim(self):
        ctx = extend(empty_ctx(), "f", Forall("x", P("x")))
        t = parse_term("forall_elim(f, a)")
        ty = infer(ctx, t)
        assert ty == P("a")

    def test_exists_intro(self):
        ctx = extend(empty_ctx(), "h", P("a"))
        t = parse_term("exists_intro(a, h, exists x. P(x))")
        ty = infer(ctx, t)
        assert ty == Exists("x", P("x"))

    def test_exists_self_transport(self):
        t = parse_term(
            "fun e: exists x. P(x) => "
            "exists_elim(e, x, h, exists_intro(x, h, exists y. P(y)))"
        )
        expected = parse_formula("(exists x. P(x)) -> exists x. P(x)")
        check(empty_ctx(), t, expected)

    def test_univ_to_exists(self):
        t = parse_term(
            "fun h: forall x. P(x) => "
            "exists_intro(a, forall_elim(h, a), exists x. P(x))"
        )
        expected = parse_formula("(forall x. P(x)) -> exists x. P(x)")
        check(empty_ctx(), t, expected)

    def test_de_morgan_a(self):
        src = (
            "fun h: not (exists x. P(x)) => "
            "forall_intro x => "
            "fun px: P(x) => "
            "h(exists_intro(x, px, exists y. P(y)))"
        )
        expected = parse_formula("not (exists x. P(x)) -> forall x. not P(x)")
        check(empty_ctx(), parse_term(src), expected)

    def test_de_morgan_b(self):
        src = (
            "fun e: exists x. not P(x) => "
            "fun g: forall x. P(x) => "
            "exists_elim(e, x, h, h(forall_elim(g, x)))"
        )
        expected = parse_formula("(exists x. not P(x)) -> not (forall x. P(x))")
        check(empty_ctx(), parse_term(src), expected)

    def test_universal_distribution(self):
        src = (
            "fun f: forall x. P(x) -> Q(x) => "
            "fun g: forall x. P(x) => "
            "forall_intro x => forall_elim(f, x)(forall_elim(g, x))"
        )
        expected = parse_formula(
            "(forall x. P(x) -> Q(x)) -> (forall x. P(x)) -> forall x. Q(x)"
        )
        check(empty_ctx(), parse_term(src), expected)

    def test_exists_split_and(self):
        src = (
            "fun e: exists x. P(x) and Q(x) => "
            "exists_elim(e, x, h, "
            "  pair(exists_intro(x, fst(h), exists y. P(y)), "
            "       exists_intro(x, snd(h), exists y. Q(y))))"
        )
        expected = parse_formula(
            "(exists x. P(x) and Q(x)) -> (exists x. P(x)) and (exists x. Q(x))"
        )
        check(empty_ctx(), parse_term(src), expected)

    def test_check_against_alpha_variant_type(self):
        # Check ForallIntro against Forall with different var name
        t = parse_term("forall_intro x => fun h: P(x) => h")
        expected = parse_formula("forall y. P(y) -> P(y)")
        check(empty_ctx(), t, expected)


# =============================================================================
# 5. Reduction from surface syntax
# =============================================================================

class TestReductionFOL:
    def test_beta_forall_surface(self):
        # ForallElim(ForallIntro(x, Lam(h, P(x), TVar(h))), ObjVar(a))
        # → Lam(h, P(a), TVar(h))
        inner = parse_term("forall_intro x => fun h: P(x) => h")
        from stele.core.terms import App
        elim = ForallElim(inner, ObjVar("a"))
        result = step(elim)
        assert result == Lam("h", P("a"), TVar("h"))

    def test_beta_forall_normalize(self):
        inner = parse_term("forall_intro x => fun h: P(x) => h")
        elim = ForallElim(inner, ObjVar("a"))
        n = normalize(elim)
        assert n == Lam("h", P("a"), TVar("h"))

    def test_beta_exists_surface(self):
        ctx = extend(empty_ctx(), "h0", P("a"))
        intro = ExistsIntro(ObjVar("a"), TVar("h0"), Exists("x", P("x")))
        elim = ExistsElim(intro, "x", "h", TVar("h"))
        result = step(elim)
        assert result == TVar("h0")

    def test_subject_reduction_surface(self):
        t = parse_term("forall_intro x => fun h: P(x) => h")
        elim = ForallElim(t, ObjVar("a"))
        ty_before = infer(empty_ctx(), elim)
        result = step(elim)
        ty_after = infer(empty_ctx(), result)
        assert ty_before == ty_after


# =============================================================================
# 6. CLI term-check with --context
# =============================================================================

def _cli(*args):
    """Run the stele CLI and return (returncode, stdout)."""
    result = subprocess.run(
        [PY, "-m", "stele.cli"] + list(args),
        capture_output=True, text=True, cwd=None
    )
    return result.returncode, result.stdout.strip()


class TestCLITermCheck:
    def test_closed_forall_intro_infer(self):
        rc, out = _cli("term-check",
                       "--term", "forall_intro x => fun h: P(x) => h",
                       "--infer")
        assert rc == 0
        assert "forall" in out.lower() or "OK" in out

    def test_closed_forall_intro_check(self):
        rc, out = _cli("term-check",
                       "--term", "forall_intro x => fun h: P(x) => h",
                       "--type", "forall x. P(x) -> P(x)")
        assert rc == 0
        assert "OK" in out

    def test_context_forall_elim(self):
        rc, out = _cli("term-check",
                       "--context", "f: forall x. P(x)",
                       "--term", "forall_elim(f, a)",
                       "--infer")
        assert rc == 0
        assert "OK" in out

    def test_context_exists_intro(self):
        rc, out = _cli("term-check",
                       "--context", "h: P(a)",
                       "--term", "exists_intro(a, h, exists x. P(x))",
                       "--type", "exists x. P(x)")
        assert rc == 0
        assert "OK" in out

    def test_context_multiple_entries(self):
        rc, out = _cli("term-check",
                       "--context", "f: forall x. P(x) -> Q(x); h: P(a)",
                       "--term", "forall_elim(f, a)(h)",
                       "--infer")
        assert rc == 0
        assert "OK" in out

    def test_context_parse_error(self):
        rc, out = _cli("term-check",
                       "--context", "bad-entry-no-colon",
                       "--term", "h",
                       "--infer")
        assert rc == 1

    def test_type_mismatch_fails(self):
        rc, out = _cli("term-check",
                       "--term", "forall_intro x => fun h: P(x) => h",
                       "--type", "P(a)")
        assert rc == 1

    def test_unbound_variable_fails(self):
        rc, out = _cli("term-check",
                       "--term", "forall_elim(f, a)",
                       "--infer")
        assert rc == 1
        assert ("unbound" in out.lower() or "type error" in out.lower() or "X" in out)


# =============================================================================
# 7. Example files
# =============================================================================

class TestExampleFiles:
    def _run_module(self, module_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location("_fol_example", module_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # raises on any assertion failure

    def test_universals_example(self):
        from pathlib import Path
        path = Path(__file__).parent.parent / "examples" / "fol" / "universals.py"
        self._run_module(str(path))

    def test_existentials_example(self):
        from pathlib import Path
        path = Path(__file__).parent.parent / "examples" / "fol" / "existentials.py"
        self._run_module(str(path))

    def test_de_morgan_fol_example(self):
        from pathlib import Path
        path = Path(__file__).parent.parent / "examples" / "fol" / "de_morgan_fol.py"
        self._run_module(str(path))


# =============================================================================
# 8. Negative examples
# =============================================================================

class TestNegativeExamples:
    def test_freshness_violation_forall_intro(self):
        ctx = extend(empty_ctx(), "h", P("x"))
        t = parse_term("forall_intro x => h")
        with pytest.raises(TypingError, match="free in the type"):
            infer(ctx, t)

    def test_escaping_existential_witness(self):
        ctx = extend(empty_ctx(), "e", Exists("x", P("x")))
        t = parse_term("exists_elim(e, x, h, h)")
        with pytest.raises(TypingError, match="freshness"):
            infer(ctx, t)

    def test_wrong_witness(self):
        ctx = extend(empty_ctx(), "h", P("b"))
        t = parse_term("exists_intro(a, h, exists x. P(x))")
        with pytest.raises(TypingError):
            infer(ctx, t)

    def test_forall_elim_on_non_forall_type(self):
        ctx = extend(empty_ctx(), "h", P("a"))
        t = parse_term("forall_elim(h, a)")
        with pytest.raises(TypingError, match="universal type"):
            infer(ctx, t)

    def test_exists_intro_non_exists_annotation(self):
        ctx = extend(empty_ctx(), "h", P("a"))
        t = parse_term("exists_intro(a, h, P(a))")
        with pytest.raises(TypingError, match="existential type"):
            infer(ctx, t)

    def test_malformed_quantifier_no_dot(self):
        with pytest.raises(ParseError):
            parse_formula("forall x P(x)")

    def test_malformed_quantifier_no_var(self):
        with pytest.raises(ParseError):
            parse_formula("exists . P(x)")

    def test_forall_elim_unbound(self):
        with pytest.raises(TypingError, match="unbound"):
            infer(empty_ctx(), parse_term("forall_elim(notbound, a)"))


# =============================================================================
# 9. Propositional regression — existing behavior is unchanged
# =============================================================================

class TestPropositionalRegression:
    def test_parse_prop_unchanged(self):
        assert parse_formula("P -> Q") == Op("imp", (Var("P"), Var("Q")))

    def test_parse_not_unchanged(self):
        assert parse_formula("not P") == Op("not", (Var("P"),))

    def test_parse_false(self):
        assert parse_formula("false") == Op("bot", ())

    def test_parse_double_imp(self):
        f = parse_formula("A -> B -> C")
        assert f == Op("imp", (Var("A"), Op("imp", (Var("B"), Var("C")))))

    def test_parse_and_or_prec(self):
        # and binds tighter than or
        f = parse_formula("A or B and C")
        assert f == Op("or", (Var("A"), Op("and", (Var("B"), Var("C")))))

    def test_prop_term_fun(self):
        assert isinstance(parse_term("fun x: A => x"), Lam)

    def test_prop_term_case(self):
        from stele.core.terms import Case
        assert isinstance(parse_term("case e of inl x => x | inr y => y"), Case)

    def test_kernel_unchanged(self):
        from stele.parser import parse_theorem
        from stele.kernel import check_theorem
        src = """
theorem mp_test:
  assume h1: P
  assume h2: P -> Q
  have h3: Q by mp h2 h1
  conclude Q by h3
"""
        check_theorem(parse_theorem(src), "classical_prop")
