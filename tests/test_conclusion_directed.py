"""Tests for conclusion-directed rule matching in the kernel.

Verifies that metavariables appearing only in a rule's conclusion
(not in any premise) are resolved from the user's claimed formula,
and that fully-determined rules like mp are unaffected.
"""
import pytest
from stele.ast import Var, Op
from stele.logic import Logic, RuleSchema, LOGICS
from stele.parser import parse_theorem
from stele.kernel import check_theorem
from stele.errors import ProofError


# ---------------------------------------------------------------------------
# Temporary logic fixture
# A rule with a conclusion-only metavariable: A ⊢ A or B
# (B does not appear in the premise, so it is free until the conclusion match)
# ---------------------------------------------------------------------------

_A, _B = Var("A"), Var("B")
_OR_INTRO_LEFT = RuleSchema(
    "or_intro_left",
    frozenset({"A", "B"}),
    (_A,),
    Op("or", (_A, _B)),
)


def _with_test_logic(rules):
    """Register a temporary Logic and yield its name; clean up on exit."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        name = "_test_conclusion_directed"
        LOGICS[name] = Logic(name, rules)
        try:
            yield name
        finally:
            del LOGICS[name]

    return _ctx()


# ---------------------------------------------------------------------------
# New behaviour: conclusion-only metavariable resolved from claimed formula
# ---------------------------------------------------------------------------

def test_conclusion_only_metavar_resolved():
    """or_intro_left: premise fixes A; B is free and must come from the claim."""
    with _with_test_logic({"or_intro_left": _OR_INTRO_LEFT}) as logic:
        src = """
theorem or_from_p:
  assume h1: P
  have h2: P or Q by or_intro_left h1
  conclude P or Q by h2
"""
        check_theorem(parse_theorem(src), logic)


def test_conclusion_only_metavar_wrong_claim_rejected():
    """Claiming 'P or Q' when the premise is 'R' should fail on premise 1."""
    with _with_test_logic({"or_intro_left": _OR_INTRO_LEFT}) as logic:
        src = """
theorem bad_or:
  assume h1: R
  have h2: P or Q by or_intro_left h1
  conclude P or Q by h2
"""
        # Premise 1 (A) matches R, conclusion becomes R or B;
        # claiming "P or Q" means P != R  ->  conclusion match fails.
        with pytest.raises(ProofError) as exc:
            check_theorem(parse_theorem(src), logic)
        assert "conclusion" in str(exc.value) or "premise" in str(exc.value)


def test_conclusion_only_metavar_multiple_uses_consistent():
    """A appears in both premise and conclusion — must be the same formula."""
    with _with_test_logic({"or_intro_left": _OR_INTRO_LEFT}) as logic:
        src = """
theorem or_consistent:
  assume h1: P and Q
  have h2: (P and Q) or R by or_intro_left h1
  conclude (P and Q) or R by h2
"""
        check_theorem(parse_theorem(src), logic)


# ---------------------------------------------------------------------------
# Regression: fully-determined rules are unaffected
# ---------------------------------------------------------------------------

def test_mp_still_works():
    src = """
theorem mp_regression:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
  conclude Q by h3
"""
    check_theorem(parse_theorem(src), "classical_prop")
    check_theorem(parse_theorem(src), "intuitionistic_prop")


def test_dne_still_works_classical_only():
    src = """
theorem dne_regression:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""
    check_theorem(parse_theorem(src), "classical_prop")
    with pytest.raises(ProofError):
        check_theorem(parse_theorem(src), "intuitionistic_prop")


def test_and_intro_still_works():
    src = """
theorem and_regression:
  assume h1: P
  assume h2: Q
  have h3: P and Q by and_intro h1 h2
  conclude P and Q by h3
"""
    check_theorem(parse_theorem(src), "intuitionistic_prop")
