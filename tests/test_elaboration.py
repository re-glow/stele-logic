"""Tests for stele.elaborate and stele.core.term_parser.

Coverage
--------
Elaboration (well-typed):
  1. Identity (imp_intro / copy) -> Lam
  2. Modus ponens (mp) -> App
  3. Conjunction intro/elim -> Pair / Fst / Snd
  4. Disjunction intro/elim -> Inl / Inr / Case
  5. Ex falso -> Abort
  6. Negation intro/elim -> Lam / App

Elaboration (rejection):
  1. Classical dne -> ElaborationError
  2. Classical lem -> ElaborationError
  3. Invalid proof script -> script_error in CrossCheckResult

Term surface parser:
  1. Variable
  2. Lambda (fun)
  3. Lambda (λ)
  4. Application f(a)
  5. Pair, Fst, Snd
  6. Inl, Inr
  7. Case
  8. Abort
  9. Nested terms
 10. Formula with ->/and/or/not inside term
 11. Malformed strings rejected

Term-check (well-typed):
  1. fun x: A => x  :  A -> A
  2. pair(x, y)  :  A and B
  3. abort(bot, C)  :  C  (with bot in context)

Term-check (ill-typed):
  1. Type mismatch

Crosscheck agreement:
  * Intuitionistic examples pass both kernel and elaboration.

CLI integration:
  * cmd_elaborate returns 0 for a valid intuitionistic proof.
  * cmd_term_check returns 0 for a well-typed term.
  * cmd_term_check returns 1 for an ill-typed term.
"""
import pathlib
import pytest

from stele.ast import Var as FVar, Op
from stele.parser import parse_theorem
from stele.core.terms import TVar, Lam, App, Pair, Fst, Snd, Inl, Inr, Case, Abort
from stele.core.typing import infer, check, TypingError, empty_ctx, extend
from stele.core.term_parser import parse_term, TermParseError
from stele.elaborate import (
    elaborate_theorem, crosscheck_theorem,
    ElaborationError, ElaboratedTheorem, CrossCheckResult,
    pretty_term,
)

ROOT = pathlib.Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Formula shorthand
# ---------------------------------------------------------------------------

P = FVar("P")
Q = FVar("Q")
R = FVar("R")
C = FVar("C")
_bot = Op("bot", ())
def _imp(a, b): return Op("imp", (a, b))
def _and(a, b): return Op("and", (a, b))
def _or(a, b):  return Op("or",  (a, b))
def _not(a):    return Op("not", (a,))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _thm(src):
    return parse_theorem(src)


# ===========================================================================
# 1. Well-typed elaboration — implication
# ===========================================================================

class TestElabImplication:

    def test_identity_term_shape(self):
        """imp_self elaborates to Lam('h1', P, TVar('h1'))."""
        src = (ROOT / "examples" / "elaborate_identity.stele").read_text()
        thm = _thm(src)
        elab = elaborate_theorem(thm)
        # The conclude ref is h3, which is the result of imp_intro h1 h2.
        # imp_intro h1 h2 -> Lam("h1", P, term_of_h2)
        # term_of_h2 = copy h1 -> TVar("h1")
        assert isinstance(elab.term, Lam)
        assert elab.term.var == "h1"
        assert isinstance(elab.term.body, TVar)

    def test_identity_inferred_type(self):
        src = (ROOT / "examples" / "elaborate_identity.stele").read_text()
        elab = elaborate_theorem(_thm(src))
        from stele.core.typing import _feq
        assert _feq(elab.inferred_type, _imp(P, P))

    def test_mp_elaborates_to_app(self):
        src = """
theorem chain:
  assume h1: P -> Q
  assume h2: Q -> R
  assume h3: P
  have h4: Q by mp h1 h3
  have h5: R by mp h2 h4
  conclude R by h5
"""
        elab = elaborate_theorem(_thm(src))
        # h5 = App(TVar("h2"), App(TVar("h1"), TVar("h3")))
        assert isinstance(elab.term, App)

    def test_mp_result_type(self):
        src = """
theorem mp_demo:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
  conclude Q by h3
"""
        elab = elaborate_theorem(_thm(src))
        ctx = extend(extend(empty_ctx(), "h1", _imp(P, Q)), "h2", P)
        inferred = infer(ctx, elab.term)
        assert inferred == Q

    def test_copy_reuses_term(self):
        src = """
theorem copy_demo:
  assume h1: P
  have h2: P by copy h1
  conclude P by h2
"""
        elab = elaborate_theorem(_thm(src))
        # copy just returns the same term reference
        assert isinstance(elab.term, TVar)
        assert elab.term.name == "h1"


# ===========================================================================
# 2. Well-typed elaboration — conjunction
# ===========================================================================

class TestElabConjunction:

    def test_and_intro_pair(self):
        src = (ROOT / "examples" / "valid_and.stele").read_text()
        thm = _thm(src)
        elab = elaborate_theorem(thm)
        # valid_and concludes Q which is Snd of the pair
        label_terms = elab.label_terms
        assert isinstance(label_terms.get("h3"), Pair)
        assert isinstance(label_terms.get("h4"), Fst)
        assert isinstance(label_terms.get("h5"), Snd)

    def test_and_elim_left_fst(self):
        src = """
theorem and_left:
  assume h1: P and Q
  have h2: P by and_elim_left h1
  conclude P by h2
"""
        elab = elaborate_theorem(_thm(src))
        assert isinstance(elab.term, Fst)

    def test_and_elim_right_snd(self):
        src = """
theorem and_right:
  assume h1: P and Q
  have h2: Q by and_elim_right h1
  conclude Q by h2
"""
        elab = elaborate_theorem(_thm(src))
        assert isinstance(elab.term, Snd)

    def test_conjunction_crosscheck(self):
        src = (ROOT / "examples" / "valid_and.stele").read_text()
        result = crosscheck_theorem(_thm(src))
        assert result.ok, f"crosscheck failed: {result}"


# ===========================================================================
# 3. Well-typed elaboration — disjunction
# ===========================================================================

class TestElabDisjunction:

    def test_or_intro_left_inl(self):
        src = """
theorem or_left:
  assume h1: P
  have h2: P or Q by or_intro_left h1
  conclude P or Q by h2
"""
        elab = elaborate_theorem(_thm(src))
        assert isinstance(elab.term, Inl)
        assert elab.term.right_type == Q

    def test_or_intro_right_inr(self):
        src = """
theorem or_right:
  assume h1: Q
  have h2: P or Q by or_intro_right h1
  conclude P or Q by h2
"""
        elab = elaborate_theorem(_thm(src))
        assert isinstance(elab.term, Inr)
        assert elab.term.left_type == P

    def test_or_elim_case(self):
        src = (ROOT / "examples" / "elaborate_disjunction.stele").read_text()
        elab = elaborate_theorem(_thm(src))
        assert isinstance(elab.term, Case)

    def test_disjunction_crosscheck(self):
        src = (ROOT / "examples" / "elaborate_disjunction.stele").read_text()
        result = crosscheck_theorem(_thm(src))
        assert result.ok, f"crosscheck failed: {result}"

    def test_or_elim_branches(self):
        src = (ROOT / "examples" / "elaborate_disjunction.stele").read_text()
        elab = elaborate_theorem(_thm(src))
        assert isinstance(elab.term, Case)
        assert isinstance(elab.term.left_body, Inr)
        assert isinstance(elab.term.right_body, Inl)


# ===========================================================================
# 4. Well-typed elaboration — bottom
# ===========================================================================

class TestElabBottom:

    def test_ex_falso_abort(self):
        src = """
theorem ef:
  assume h1: P
  assume h2: not P
  have h3: false by neg_elim h1 h2
  have h4: Q by ex_falso h3
  conclude Q by h4
"""
        elab = elaborate_theorem(_thm(src))
        assert isinstance(elab.term, Abort)
        assert elab.term.target_type == Q

    def test_ex_falso_crosscheck(self):
        src = (ROOT / "examples" / "ex_falso.stele").read_text()
        result = crosscheck_theorem(_thm(src))
        assert result.ok, f"crosscheck failed: {result}"


# ===========================================================================
# 5. Well-typed elaboration — negation
# ===========================================================================

class TestElabNegation:

    def test_neg_intro_lam(self):
        src = (ROOT / "examples" / "neg_intro.stele").read_text()
        elab = elaborate_theorem(_thm(src))
        # neg_intro -> Lam
        assert isinstance(elab.term, Lam)

    def test_neg_elim_app(self):
        src = (ROOT / "examples" / "neg_elim.stele").read_text()
        elab = elaborate_theorem(_thm(src))
        # neg_elim h1 h2: h1:P, h2:not P → App(not_P_term, P_term) : false
        assert isinstance(elab.term, App)

    def test_neg_intro_crosscheck(self):
        src = (ROOT / "examples" / "neg_intro.stele").read_text()
        result = crosscheck_theorem(_thm(src))
        assert result.ok, f"crosscheck failed: {result}"


# ===========================================================================
# 6. Rejection: classical rules
# ===========================================================================

class TestClassicalRejection:

    def test_dne_raises_elaboration_error(self):
        src = (ROOT / "examples" / "dne.stele").read_text()
        with pytest.raises(ElaborationError, match="classical"):
            elaborate_theorem(_thm(src))

    def test_dne_crosscheck_elab_fails(self):
        src = (ROOT / "examples" / "dne.stele").read_text()
        result = crosscheck_theorem(_thm(src), logic_name="classical_prop")
        assert result.script_ok
        assert not result.elaboration_ok
        assert "classical" in result.elab_error.lower()

    def test_lem_raises_elaboration_error(self):
        src = (ROOT / "examples" / "lem.stele").read_text()
        with pytest.raises(ElaborationError, match="classical"):
            elaborate_theorem(_thm(src))


# ===========================================================================
# 7. Rejection: invalid proof script
# ===========================================================================

class TestInvalidScript:

    def test_invalid_proof_crosscheck_script_fails(self):
        src = (ROOT / "examples" / "invalid_mp.stele").read_text()
        # invalid_mp has a wrong mp application; kernel check should fail
        result = crosscheck_theorem(_thm(src))
        assert not result.script_ok

    def test_invalid_proof_no_elaboration(self):
        src = (ROOT / "examples" / "invalid_mp.stele").read_text()
        result = crosscheck_theorem(_thm(src))
        assert not result.elaboration_ok


# ===========================================================================
# 8. Term surface parser
# ===========================================================================

class TestTermParser:

    def test_variable(self):
        t = parse_term("x")
        assert t == TVar("x")

    def test_fun_simple(self):
        t = parse_term("fun x: A => x")
        assert isinstance(t, Lam)
        assert t.var == "x"
        assert t.var_type == FVar("A")
        assert t.body == TVar("x")

    def test_fun_lambda_alias(self):
        t = parse_term("λ x: A => x")
        assert isinstance(t, Lam)
        assert t.var == "x"

    def test_fun_imp_type(self):
        t = parse_term("fun f: A -> B => f")
        assert isinstance(t, Lam)
        assert t.var_type == _imp(FVar("A"), FVar("B"))

    def test_application_single(self):
        t = parse_term("f(a)")
        assert t == App(TVar("f"), TVar("a"))

    def test_application_chained(self):
        # f(a)(b) => App(App(f, a), b)
        t = parse_term("f(a)(b)")
        assert t == App(App(TVar("f"), TVar("a")), TVar("b"))

    def test_pair(self):
        t = parse_term("pair(x, y)")
        assert t == Pair(TVar("x"), TVar("y"))

    def test_fst(self):
        t = parse_term("fst(pair(x, y))")
        assert t == Fst(Pair(TVar("x"), TVar("y")))

    def test_snd(self):
        t = parse_term("snd(p)")
        assert t == Snd(TVar("p"))

    def test_inl(self):
        t = parse_term("inl(x, B)")
        assert t == Inl(TVar("x"), FVar("B"))

    def test_inr(self):
        t = parse_term("inr(y, A)")
        assert t == Inr(TVar("y"), FVar("A"))

    def test_inl_compound_type(self):
        t = parse_term("inl(x, A and B)")
        assert t == Inl(TVar("x"), _and(FVar("A"), FVar("B")))

    def test_inr_imp_type(self):
        t = parse_term("inr(y, A -> B)")
        assert t == Inr(TVar("y"), _imp(FVar("A"), FVar("B")))

    def test_abort(self):
        t = parse_term("abort(bot, C)")
        assert t == Abort(TVar("bot"), FVar("C"))

    def test_abort_compound_target(self):
        t = parse_term("abort(bot, A or B)")
        assert t == Abort(TVar("bot"), _or(FVar("A"), FVar("B")))

    def test_case_simple(self):
        t = parse_term("case e of inl x => x | inr y => y")
        assert isinstance(t, Case)
        assert t.scrutinee == TVar("e")
        assert t.left_var == "x"
        assert t.left_body == TVar("x")
        assert t.right_var == "y"
        assert t.right_body == TVar("y")

    def test_fun_inside_case_branch(self):
        # case e of inl x => fun y: A => x | inr z => z
        t = parse_term("case e of inl x => fun y: A => x | inr z => z")
        assert isinstance(t, Case)
        assert isinstance(t.left_body, Lam)

    def test_nested_pair(self):
        t = parse_term("fst(snd(p))")
        assert t == Fst(Snd(TVar("p")))

    def test_grouped_parentheses(self):
        t = parse_term("(fun x: A => x)")
        assert isinstance(t, Lam)

    def test_empty_string_rejected(self):
        with pytest.raises(TermParseError):
            parse_term("")

    def test_keyword_as_var_rejected(self):
        with pytest.raises(TermParseError):
            parse_term("fun")

    def test_trailing_token_rejected(self):
        with pytest.raises(TermParseError):
            parse_term("x y")

    def test_bad_character_rejected(self):
        with pytest.raises(TermParseError):
            parse_term("@x")

    def test_missing_arrow_in_fun(self):
        with pytest.raises(TermParseError):
            parse_term("fun x: A x")   # missing =>


# ===========================================================================
# 9. Term-check via typing
# ===========================================================================

class TestTermCheck:

    def test_identity_checks(self):
        t = parse_term("fun x: A => x")
        check(empty_ctx(), t, _imp(FVar("A"), FVar("A")))

    def test_pair_checks(self):
        ctx = extend(extend(empty_ctx(), "x", FVar("A")), "y", FVar("B"))
        t = parse_term("pair(x, y)")
        check(ctx, t, _and(FVar("A"), FVar("B")))

    def test_abort_checks(self):
        ctx = extend(empty_ctx(), "bot", Op("bot", ()))
        t = parse_term("abort(bot, C)")
        check(ctx, t, FVar("C"))

    def test_type_mismatch_fails(self):
        t = parse_term("fun x: A => x")
        with pytest.raises(TypingError):
            check(empty_ctx(), t, _imp(FVar("B"), FVar("B")))

    def test_infer_identity(self):
        t = parse_term("fun x: A => x")
        ty = infer(empty_ctx(), t)
        assert ty == _imp(FVar("A"), FVar("A"))

    def test_case_infers(self):
        ctx = extend(empty_ctx(), "e", _or(FVar("A"), FVar("A")))
        t = parse_term("case e of inl x => x | inr y => y")
        ty = infer(ctx, t)
        assert ty == FVar("A")


# ===========================================================================
# 10. Pretty-term round-trip
# ===========================================================================

class TestPrettyTerm:

    def test_identity_roundtrip(self):
        t = Lam("x", P, TVar("x"))
        s = pretty_term(t)
        t2 = parse_term(s)
        assert t2 == t

    def test_app_roundtrip(self):
        t = App(TVar("f"), TVar("a"))
        s = pretty_term(t)
        t2 = parse_term(s)
        assert t2 == t

    def test_pair_roundtrip(self):
        t = Pair(TVar("x"), TVar("y"))
        s = pretty_term(t)
        assert parse_term(s) == t

    def test_inl_roundtrip(self):
        t = Inl(TVar("x"), Q)
        s = pretty_term(t)
        assert parse_term(s) == t

    def test_inr_roundtrip(self):
        t = Inr(TVar("y"), P)
        s = pretty_term(t)
        assert parse_term(s) == t

    def test_abort_roundtrip(self):
        t = Abort(TVar("bot"), C)
        s = pretty_term(t)
        assert parse_term(s) == t


# ===========================================================================
# 11. CLI command integration
# ===========================================================================

class TestCLI:

    def test_cmd_elaborate_identity(self, capsys):
        from stele.cli import cmd_elaborate
        path = str(ROOT / "examples" / "elaborate_identity.stele")
        rc = cmd_elaborate(path, logic=None)
        out = capsys.readouterr().out
        assert rc == 0
        assert "OK" in out

    def test_cmd_elaborate_classical_reports_unsupported(self, capsys):
        from stele.cli import cmd_elaborate
        path = str(ROOT / "examples" / "dne.stele")
        rc = cmd_elaborate(path, logic="classical_prop")
        out = capsys.readouterr().out
        assert rc == 1
        assert "classical" in out.lower() or "X" in out

    def test_cmd_term_check_well_typed(self, capsys):
        from stele.cli import cmd_term_check
        rc = cmd_term_check("fun x: A => x", "A -> A", infer_mode=False)
        out = capsys.readouterr().out
        assert rc == 0
        assert "OK" in out

    def test_cmd_term_check_ill_typed(self, capsys):
        from stele.cli import cmd_term_check
        rc = cmd_term_check("fun x: A => x", "B -> B", infer_mode=False)
        out = capsys.readouterr().out
        assert rc == 1
        assert "X" in out

    def test_cmd_term_check_infer(self, capsys):
        from stele.cli import cmd_term_check
        rc = cmd_term_check("fun x: A => x", None, infer_mode=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert "A -> A" in out

    def test_cmd_term_check_bad_term(self, capsys):
        from stele.cli import cmd_term_check
        rc = cmd_term_check("@bad", "A -> A", infer_mode=False)
        assert rc == 1

    def test_cmd_term_check_bad_formula(self, capsys):
        from stele.cli import cmd_term_check
        rc = cmd_term_check("fun x: A => x", "@ @@", infer_mode=False)
        assert rc == 1


# ===========================================================================
# 12. Crosscheck agreement: all intuitionistic examples
# ===========================================================================

class TestCrosscheckAgreement:

    @pytest.mark.parametrize("filename", [
        "elaborate_identity.stele",
        "elaborate_disjunction.stele",
        "valid_and.stele",
        "ex_falso.stele",
        "neg_intro.stele",
    ])
    def test_intuitionistic_examples_crosscheck(self, filename):
        src = (ROOT / "examples" / filename).read_text()
        thm = _thm(src)
        result = crosscheck_theorem(thm)
        assert result.script_ok, f"{filename}: script failed: {result.script_error}"
        assert result.elaboration_ok, f"{filename}: elab failed: {result.elab_error}"
        assert result.typecheck_ok, f"{filename}: typecheck failed: {result.type_error}"

    def test_classical_script_elab_fails_gracefully(self):
        """dne.stele passes classical kernel but fails elaboration — no exception."""
        src = (ROOT / "examples" / "dne.stele").read_text()
        result = crosscheck_theorem(_thm(src), logic_name="classical_prop")
        assert result.script_ok
        assert not result.elaboration_ok
        assert not result.ok
