"""Regression tests for the generalized hypothesis-discharge mechanism.

imp_intro is now expressed as a normal RuleSchema with hyp_premises instead
of a hardcoded kernel branch.  These tests verify that:
  - imp_intro still works exactly as before from the user's perspective,
  - discharged assumptions remain out of scope after a subproof closes,
  - the generic mechanism correctly binds assumption and conclusion formulas.
"""
import pytest
from stele.parser import parse_theorem
from stele.kernel import check_theorem
from stele.logic import LOGICS
from stele.errors import ProofError


def _ok(src, logic="intuitionistic_prop"):
    check_theorem(parse_theorem(src), logic)


def _fail(src, logic="intuitionistic_prop"):
    with pytest.raises(ProofError) as exc:
        check_theorem(parse_theorem(src), logic)
    return str(exc.value)


# ---------------------------------------------------------------------------
# imp_intro still works through the generic discharge path
# ---------------------------------------------------------------------------

def test_imp_intro_basic():
    src = """
theorem imp_self:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h2
  conclude P -> P by h3
"""
    _ok(src, "intuitionistic_prop")
    _ok(src, "classical_prop")


def test_imp_intro_nontrivial():
    src = """
theorem mp_as_theorem:
  suppose h1: P
    suppose h2: P -> Q
      have h3: Q by mp h2 h1
    have h4: (P -> Q) -> Q by imp_intro h2 h3
  have h5: P -> ((P -> Q) -> Q) by imp_intro h1 h4
  conclude P -> ((P -> Q) -> Q) by h5
"""
    _ok(src, "intuitionistic_prop")


def test_imp_intro_classical_dne_law():
    """The dne_law example from examples/dne_law.stele still passes."""
    src = """
theorem dne_law using classical_prop:
  suppose h1: not not P
    have h2: P by dne h1
  have h3: not not P -> P by imp_intro h1 h2
  conclude not not P -> P by h3
"""
    _ok(src, "classical_prop")


def test_imp_intro_intuitionistic_dne_law_fails():
    """dne inside a subproof is rejected in intuitionistic logic."""
    src = """
theorem dne_law:
  suppose h1: not not P
    have h2: P by dne h1
  have h3: not not P -> P by imp_intro h1 h2
  conclude not not P -> P by h3
"""
    with pytest.raises(ProofError):
        _ok(src, "intuitionistic_prop")


def test_imp_intro_is_in_both_logics_via_shared():
    """imp_intro is now in _SHARED, so it is present in both built-in logics."""
    assert "imp_intro" in LOGICS["intuitionistic_prop"].rules
    assert "imp_intro" in LOGICS["classical_prop"].rules


def test_imp_intro_schema_has_hyp_premises():
    """The schema itself carries hyp_premises, not just a kernel string check."""
    from stele.logic import IMP_INTRO
    assert len(IMP_INTRO.hyp_premises) == 1
    assert len(IMP_INTRO.premises) == 0


# ---------------------------------------------------------------------------
# Discharged assumption scope still enforced
# ---------------------------------------------------------------------------

def test_discharged_label_cannot_be_referenced_by_copy():
    msg = _fail("""
theorem leak:
  suppose h1: P
    have h2: P by copy h1
  have h3: P by copy h2
  conclude P by h3
""")
    assert "unknown reference 'h2'" in msg


def test_discharged_label_cannot_be_referenced_by_mp():
    msg = _fail("""
theorem leak_mp:
  assume h0: P -> Q
  suppose h1: P
    have h2: Q by mp h0 h1
  have h3: Q by copy h2
  conclude Q by h3
""")
    assert "unknown reference 'h2'" in msg


def test_imp_intro_wrong_subproof_labels_rejected():
    """imp_intro with non-existent subproof labels raises an error."""
    msg = _fail("""
theorem bad_imp_intro:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h9
  conclude P -> P by h3
""")
    assert "no closed subproof" in msg or "derives" in msg


def test_imp_intro_wrong_conclusion_claim_rejected():
    """imp_intro that derives P but claims Q -> P is rejected."""
    msg = _fail("""
theorem bad_claim:
  suppose h1: P
    have h2: P by copy h1
  have h3: Q -> P by imp_intro h1 h2
  conclude Q -> P by h3
""")
    # The conclusion match (A->B with A=P, B=P vs claimed Q->P) should fail
    assert "conclusion" in msg or "match" in msg


# ---------------------------------------------------------------------------
# Non-discharge rules are unaffected (n_hyp == 0 path)
# ---------------------------------------------------------------------------

def test_mp_unaffected():
    src = """
theorem mp_ok:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
  conclude Q by h3
"""
    _ok(src)


def test_ex_falso_unaffected():
    src = """
theorem ex_falso_ok:
  assume h1: false
  have h2: P by ex_falso h1
  conclude P by h2
"""
    _ok(src)
