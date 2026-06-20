"""Tests for neg_intro (¬I) and or_elim (∨E).

Both rules use the generic hyp_premises discharge mechanism.
"""
import pytest
from stele.parser import parse_theorem
from stele.kernel import check_theorem
from stele.logic import LOGICS, NEG_INTRO, OR_ELIM
from stele.errors import ProofError


def _ok(src, logic="intuitionistic_prop"):
    check_theorem(parse_theorem(src), logic)


def _fail(src, logic="intuitionistic_prop"):
    with pytest.raises(ProofError) as exc:
        check_theorem(parse_theorem(src), logic)
    return str(exc.value)


# ---------------------------------------------------------------------------
# Schema sanity
# ---------------------------------------------------------------------------

def test_neg_intro_in_shared_logics():
    assert "neg_intro" in LOGICS["intuitionistic_prop"].rules
    assert "neg_intro" in LOGICS["classical_prop"].rules


def test_or_elim_in_shared_logics():
    assert "or_elim" in LOGICS["intuitionistic_prop"].rules
    assert "or_elim" in LOGICS["classical_prop"].rules


def test_neg_intro_schema():
    assert len(NEG_INTRO.premises) == 0
    assert len(NEG_INTRO.hyp_premises) == 1


def test_or_elim_schema():
    assert len(OR_ELIM.premises) == 1       # the disjunction
    assert len(OR_ELIM.hyp_premises) == 2   # left branch, right branch


# ---------------------------------------------------------------------------
# neg_intro valid
# ---------------------------------------------------------------------------

def test_neg_intro_basic_intuitionistic():
    src = """
theorem neg_intro_basic:
  suppose h1: P and not P
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h1 h4
  conclude not (P and not P) by h5
"""
    _ok(src, "intuitionistic_prop")


def test_neg_intro_basic_classical():
    src = """
theorem neg_intro_basic_cl:
  suppose h1: P and not P
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h1 h4
  conclude not (P and not P) by h5
"""
    _ok(src, "classical_prop")


def test_neg_intro_not_implication():
    """From P and not Q, derive not (P -> Q) using neg_intro."""
    src = """
theorem not_imp_from_and_not:
  assume h1: P
  assume h2: not Q
  suppose h3: P -> Q
    have h4: Q by mp h3 h1
    have h5: false by neg_elim h4 h2
  have h6: not (P -> Q) by neg_intro h3 h5
  conclude not (P -> Q) by h6
"""
    _ok(src, "intuitionistic_prop")


def test_neg_intro_chained_with_ex_falso():
    """neg_intro + ex_falso: from a contradiction derive anything."""
    src = """
theorem neg_intro_then_ex_falso:
  suppose h1: P and not P
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h1 h4
  suppose h6: P and not P
    have h7: P by and_elim_left h6
    have h8: not P by and_elim_right h6
    have h9: false by neg_elim h7 h8
    have h10: Q by ex_falso h9
  have h11: (P and not P) -> Q by imp_intro h6 h10
  conclude (P and not P) -> Q by h11
"""
    _ok(src, "intuitionistic_prop")


# ---------------------------------------------------------------------------
# neg_intro invalid
# ---------------------------------------------------------------------------

def test_neg_intro_fails_if_subproof_not_deriving_false():
    """Subproof concludes P, not false — neg_intro must reject."""
    msg = _fail("""
theorem bad_neg_intro:
  suppose h1: P and Q
    have h2: P by and_elim_left h1
  have h3: not (P and Q) by neg_intro h1 h2
  conclude not (P and Q) by h3
""")
    assert "subproof conclusion" in msg or "does not match" in msg


def test_neg_intro_fails_with_wrong_assume_label():
    msg = _fail("""
theorem bad_neg_intro_labels:
  suppose h1: P and not P
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h9 h4
  conclude not (P and not P) by h5
""")
    assert "no closed subproof" in msg or "subproof" in msg


def test_neg_intro_fails_wrong_conclusion_claim():
    """Deriving not (P and not P) but claiming not Q."""
    msg = _fail("""
theorem bad_neg_intro_claim:
  suppose h1: P and not P
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not Q by neg_intro h1 h4
  conclude not Q by h5
""")
    assert "conclusion" in msg or "match" in msg


# ---------------------------------------------------------------------------
# or_elim valid
# ---------------------------------------------------------------------------

def test_or_elim_disjunction_commutativity():
    """P or Q |- Q or P (the or_comm example)."""
    src = """
theorem or_comm:
  assume h1: P or Q
  suppose h2: P
    have h3: Q or P by or_intro_right h2
  suppose h4: Q
    have h5: Q or P by or_intro_left h4
  have h6: Q or P by or_elim h1 h2 h3 h4 h5
  conclude Q or P by h6
"""
    _ok(src, "intuitionistic_prop")
    _ok(src, "classical_prop")


def test_or_elim_both_branches_derive_same():
    """Both branches derive an implication."""
    src = """
theorem or_elim_impl:
  assume h1: P or Q
  assume h2: P -> R
  assume h3: Q -> R
  suppose h4: P
    have h5: R by mp h2 h4
  suppose h6: Q
    have h7: R by mp h3 h6
  have h8: R by or_elim h1 h4 h5 h6 h7
  conclude R by h8
"""
    _ok(src, "intuitionistic_prop")
    _ok(src, "classical_prop")


def test_or_elim_compound_disjuncts():
    """(P and Q) or (P and R) |- P."""
    src = """
theorem or_elim_compound:
  assume h1: (P and Q) or (P and R)
  suppose h2: P and Q
    have h3: P by and_elim_left h2
  suppose h4: P and R
    have h5: P by and_elim_left h4
  have h6: P by or_elim h1 h2 h3 h4 h5
  conclude P by h6
"""
    _ok(src, "intuitionistic_prop")


def test_or_elim_with_neg_intro():
    """Combine or_elim and neg_intro: not P or not Q |- not (P and Q)."""
    src = """
theorem not_and_from_or_not:
  assume h1: not P or not Q
  suppose h2: not P
    suppose h3: P and Q
      have h4: P by and_elim_left h3
      have h5: false by neg_elim h4 h2
    have h6: not (P and Q) by neg_intro h3 h5
  suppose h7: not Q
    suppose h8: P and Q
      have h9: Q by and_elim_right h8
      have h10: false by neg_elim h9 h7
    have h11: not (P and Q) by neg_intro h8 h10
  have h12: not (P and Q) by or_elim h1 h2 h6 h7 h11
  conclude not (P and Q) by h12
"""
    _ok(src, "intuitionistic_prop")
    _ok(src, "classical_prop")


# ---------------------------------------------------------------------------
# or_elim invalid
# ---------------------------------------------------------------------------

def test_or_elim_fails_if_branches_derive_different_conclusions():
    """Left branch derives R, right branch derives S — must be rejected."""
    msg = _fail("""
theorem bad_or_elim_different:
  assume h1: P or Q
  assume h2: R
  assume h3: S
  suppose h4: P
    have h5: R by copy h2
  suppose h6: Q
    have h7: S by copy h3
  have h8: R by or_elim h1 h4 h5 h6 h7
  conclude R by h8
""")
    assert "subproof conclusion" in msg or "does not match" in msg


def test_or_elim_fails_if_left_assumption_wrong_disjunct():
    """Ordinary premise is P or Q, but left branch assumes R (not P)."""
    msg = _fail("""
theorem bad_or_elim_left_disj:
  assume h1: P or Q
  assume h2: R
  suppose h3: R
    have h4: R by copy h3
  suppose h5: Q
    have h6: R by copy h2
  have h7: R by or_elim h1 h3 h4 h5 h6
  conclude R by h7
""")
    assert "subproof assumption" in msg or "does not match" in msg


def test_or_elim_fails_if_right_assumption_wrong_disjunct():
    """Left branch is fine; right branch assumes R (not Q)."""
    msg = _fail("""
theorem bad_or_elim_right_disj:
  assume h1: P or Q
  assume h2: R
  suppose h3: P
    have h4: R by copy h2
  suppose h5: R
    have h6: R by copy h5
  have h7: R by or_elim h1 h3 h4 h5 h6
  conclude R by h7
""")
    assert "subproof assumption" in msg or "does not match" in msg


def test_or_elim_fails_wrong_ordinary_premise():
    """Ordinary premise is not a disjunction."""
    msg = _fail("""
theorem bad_or_elim_not_disj:
  assume h1: P
  suppose h2: P
    have h3: P by copy h2
  suppose h4: Q
    have h5: P by copy h1
  have h6: P by or_elim h1 h2 h3 h4 h5
  conclude P by h6
""")
    assert "premise" in msg or "match" in msg


# ---------------------------------------------------------------------------
# Discharge / scope still sound
# ---------------------------------------------------------------------------

def test_neg_intro_discharged_label_invisible_outside():
    """The assume label from suppose is not accessible by copy outside."""
    msg = _fail("""
theorem neg_intro_scope_leak:
  suppose h1: P and not P
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h1 h4
  have h6: P by copy h2
  conclude P by h6
""")
    assert "unknown reference 'h2'" in msg


def test_or_elim_discharged_labels_invisible_outside():
    """Labels inside suppose blocks are not accessible by copy after they close."""
    msg = _fail("""
theorem or_elim_scope_leak:
  assume h1: P or Q
  suppose h2: P
    have h3: Q or P by or_intro_right h2
  suppose h4: Q
    have h5: Q or P by or_intro_left h4
  have h6: Q or P by or_elim h1 h2 h3 h4 h5
  have h7: Q or P by copy h3
  conclude Q or P by h7
""")
    assert "unknown reference 'h3'" in msg
