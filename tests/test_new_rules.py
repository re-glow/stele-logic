"""Tests for falsum and nondischarge rules: neg_elim, ex_falso,
or_intro_left, or_intro_right.  Also covers false parsing/pretty-printing.
"""
import pytest
from stele.parser import parse_theorem, parse_formula
from stele.kernel import check_theorem
from stele.ast import Op, pretty
from stele.errors import ProofError


def _ok(src, logic="intuitionistic_prop"):
    check_theorem(parse_theorem(src), logic)


def _fail(src, logic="intuitionistic_prop"):
    with pytest.raises(ProofError) as exc:
        check_theorem(parse_theorem(src), logic)
    return str(exc.value)


# ---------------------------------------------------------------------------
# false parsing and pretty-printing
# ---------------------------------------------------------------------------

def test_false_parses_to_bot():
    f = parse_formula("false")
    assert f == Op("bot", ())


def test_false_pretty_prints():
    assert pretty(Op("bot", ())) == "false"


def test_false_roundtrips():
    src = """
theorem trivial_false:
  assume h1: false
  conclude false by h1
"""
    _ok(src)


def test_false_in_compound_formula():
    f = parse_formula("P -> false")
    assert pretty(f) == "P -> false"


# ---------------------------------------------------------------------------
# neg_elim: A, not A ⊢ false
# ---------------------------------------------------------------------------

def test_neg_elim_valid_intuitionistic():
    src = """
theorem neg_elim_demo:
  assume h1: P
  assume h2: not P
  have h3: false by neg_elim h1 h2
  conclude false by h3
"""
    _ok(src, "intuitionistic_prop")


def test_neg_elim_valid_classical():
    src = """
theorem neg_elim_classical:
  assume h1: P
  assume h2: not P
  have h3: false by neg_elim h1 h2
  conclude false by h3
"""
    _ok(src, "classical_prop")


def test_neg_elim_compound_formula():
    src = """
theorem neg_elim_compound:
  assume h1: P and Q
  assume h2: not (P and Q)
  have h3: false by neg_elim h1 h2
  conclude false by h3
"""
    _ok(src, "intuitionistic_prop")


def test_neg_elim_requires_matching_negation():
    msg = _fail("""
theorem bad_neg_elim:
  assume h1: P
  assume h2: not Q
  have h3: false by neg_elim h1 h2
  conclude false by h3
""")
    assert "premise" in msg or "conclusion" in msg


def test_neg_elim_order_matters():
    # h1 must be A, h2 must be not A (not the reverse)
    msg = _fail("""
theorem bad_neg_elim_order:
  assume h1: not P
  assume h2: P
  have h3: false by neg_elim h1 h2
  conclude false by h3
""")
    assert "premise" in msg or "conclusion" in msg


# ---------------------------------------------------------------------------
# ex_falso: false ⊢ A  (conclusion-only metavariable)
# ---------------------------------------------------------------------------

def test_ex_falso_valid_intuitionistic():
    src = """
theorem ex_falso_demo:
  assume h1: false
  have h2: Q by ex_falso h1
  conclude Q by h2
"""
    _ok(src, "intuitionistic_prop")


def test_ex_falso_valid_classical():
    src = """
theorem ex_falso_classical:
  assume h1: false
  have h2: Q by ex_falso h1
  conclude Q by h2
"""
    _ok(src, "classical_prop")


def test_ex_falso_arbitrary_conclusion():
    src = """
theorem ex_falso_complex:
  assume h1: false
  have h2: P -> Q by ex_falso h1
  conclude P -> Q by h2
"""
    _ok(src, "intuitionistic_prop")


def test_ex_falso_requires_false_premise():
    msg = _fail("""
theorem bad_ex_falso:
  assume h1: P
  have h2: Q by ex_falso h1
  conclude Q by h2
""")
    assert "premise" in msg or "conclusion" in msg


def test_ex_falso_chained_with_neg_elim():
    src = """
theorem explosion:
  assume h1: P
  assume h2: not P
  have h3: false by neg_elim h1 h2
  have h4: Q by ex_falso h3
  conclude Q by h4
"""
    _ok(src, "intuitionistic_prop")
    _ok(src, "classical_prop")


# ---------------------------------------------------------------------------
# or_intro_left: A ⊢ A or B  (B is conclusion-only metavariable)
# ---------------------------------------------------------------------------

def test_or_intro_left_valid():
    src = """
theorem or_left_demo:
  assume h1: P
  have h2: P or Q by or_intro_left h1
  conclude P or Q by h2
"""
    _ok(src, "intuitionistic_prop")
    _ok(src, "classical_prop")


def test_or_intro_left_compound_left():
    src = """
theorem or_left_compound:
  assume h1: P and Q
  have h2: (P and Q) or R by or_intro_left h1
  conclude (P and Q) or R by h2
"""
    _ok(src, "intuitionistic_prop")


def test_or_intro_left_wrong_left_side():
    # Premise is P but claimed disjunction has Q as left side
    msg = _fail("""
theorem bad_or_left:
  assume h1: P
  have h2: Q or R by or_intro_left h1
  conclude Q or R by h2
""")
    assert "conclusion" in msg or "premise" in msg


def test_or_intro_left_not_a_disjunction():
    msg = _fail("""
theorem bad_or_left_not_disj:
  assume h1: P
  have h2: P and Q by or_intro_left h1
  conclude P and Q by h2
""")
    assert "conclusion" in msg or "premise" in msg


# ---------------------------------------------------------------------------
# or_intro_right: B ⊢ A or B  (A is conclusion-only metavariable)
# ---------------------------------------------------------------------------

def test_or_intro_right_valid():
    src = """
theorem or_right_demo:
  assume h1: Q
  have h2: P or Q by or_intro_right h1
  conclude P or Q by h2
"""
    _ok(src, "intuitionistic_prop")
    _ok(src, "classical_prop")


def test_or_intro_right_compound_right():
    src = """
theorem or_right_compound:
  assume h1: P -> Q
  have h2: R or (P -> Q) by or_intro_right h1
  conclude R or (P -> Q) by h2
"""
    _ok(src, "intuitionistic_prop")


def test_or_intro_right_wrong_right_side():
    # Premise is P but claimed disjunction has Q as right side
    msg = _fail("""
theorem bad_or_right:
  assume h1: P
  have h2: Q or R by or_intro_right h1
  conclude Q or R by h2
""")
    assert "conclusion" in msg or "premise" in msg


def test_or_intro_right_not_a_disjunction():
    msg = _fail("""
theorem bad_or_right_not_disj:
  assume h1: Q
  have h2: P and Q by or_intro_right h1
  conclude P and Q by h2
""")
    assert "conclusion" in msg or "premise" in msg


# ---------------------------------------------------------------------------
# Classical-vs-intuitionistic distinction is still exactly dne
# ---------------------------------------------------------------------------

def test_new_rules_available_in_both_logics():
    src = """
theorem available_everywhere:
  assume h1: P
  assume h2: not P
  have h3: false by neg_elim h1 h2
  have h4: Q by ex_falso h3
  have h5: Q or R by or_intro_left h4
  conclude Q or R by h5
"""
    _ok(src, "intuitionistic_prop")
    _ok(src, "classical_prop")


def test_dne_still_classical_only():
    src = """
theorem dne_still_classical:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""
    _ok(src, "classical_prop")
    with pytest.raises(ProofError):
        _ok(src, "intuitionistic_prop")
