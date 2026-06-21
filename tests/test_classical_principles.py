"""Tests for classical-only rules: lem (LEM) and pbc (proof by contradiction).

Each classical theorem is also verified to be rejected under intuitionistic_prop
due to unavailable rules, not parser failure.
"""
import pytest
from stele.parser import parse_theorem
from stele.kernel import check_theorem
from stele.logic import LOGICS, LEM, PBC
from stele.errors import ProofError


def _ok(src, logic):
    check_theorem(parse_theorem(src), logic)


def _fail(src, logic):
    with pytest.raises(ProofError) as exc:
        check_theorem(parse_theorem(src), logic)
    return str(exc.value)


# ---------------------------------------------------------------------------
# Schema placement
# ---------------------------------------------------------------------------

def test_lem_only_in_classical():
    assert "lem" in LOGICS["classical_prop"].rules
    assert "lem" not in LOGICS["intuitionistic_prop"].rules


def test_pbc_only_in_classical():
    assert "pbc" in LOGICS["classical_prop"].rules
    assert "pbc" not in LOGICS["intuitionistic_prop"].rules


def test_lem_schema():
    assert len(LEM.premises) == 0
    assert len(LEM.hyp_premises) == 0


def test_pbc_schema():
    assert len(PBC.premises) == 0
    assert len(PBC.hyp_premises) == 1


# ---------------------------------------------------------------------------
# lem: P or not P
# ---------------------------------------------------------------------------

def test_lem_accepted_classically():
    src = """
theorem lem_demo:
  have h: P or not P by lem
  conclude P or not P by h
"""
    _ok(src, "classical_prop")


def test_lem_rejected_intuitionistically():
    src = """
theorem lem_demo:
  have h: P or not P by lem
  conclude P or not P by h
"""
    msg = _fail(src, "intuitionistic_prop")
    assert "not available" in msg and "lem" in msg


def test_lem_conclusion_must_be_A_or_not_A():
    """Claiming P or not Q (asymmetric) fails — conclusion match enforces X or not X."""
    msg = _fail("""
theorem bad_lem:
  have h: P or not Q by lem
  conclude P or not Q by h
""", "classical_prop")
    assert "conclusion" in msg or "match" in msg


def test_lem_compound_formula():
    src = """
theorem lem_compound:
  have h: (P -> Q) or not (P -> Q) by lem
  conclude (P -> Q) or not (P -> Q) by h
"""
    _ok(src, "classical_prop")


def test_lem_used_in_or_elim():
    """LEM combined with or_elim: from P or not P, derive anything in classical."""
    src = """
theorem classical_reasoning:
  assume hr: not P -> Q
  have h1: P or not P by lem
  suppose h2: P
    have h3: P or Q by or_intro_left h2
  suppose h4: not P
    have h5: Q by mp hr h4
    have h6: P or Q by or_intro_right h5
  have h7: P or Q by or_elim h1 h2 h3 h4 h6
  conclude P or Q by h7
"""
    _ok(src, "classical_prop")


# ---------------------------------------------------------------------------
# pbc: proof by contradiction
# ---------------------------------------------------------------------------

def test_pbc_accepted_classically():
    src = """
theorem pbc_demo:
  suppose hnp: not P
    assume hp: P
    have hbot: false by neg_elim hp hnp
  have h: P by pbc hnp hbot
  conclude P by h
"""
    _ok(src, "classical_prop")


def test_pbc_rejected_intuitionistically():
    src = """
theorem pbc_demo:
  suppose hnp: not P
    assume hp: P
    have hbot: false by neg_elim hp hnp
  have h: P by pbc hnp hbot
  conclude P by h
"""
    msg = _fail(src, "intuitionistic_prop")
    assert "not available" in msg and "pbc" in msg


def test_pbc_subproof_must_derive_false():
    """Subproof deriving P instead of false must be rejected."""
    msg = _fail("""
theorem bad_pbc:
  assume hp: P
  suppose hnp: not P
    have hcopy: P by copy hp
  have h: P by pbc hnp hcopy
  conclude P by h
""", "classical_prop")
    assert "subproof conclusion" in msg or "does not match" in msg


def test_pbc_subproof_must_assume_not_A():
    """Subproof assuming P (not not P) must be rejected for conclusion P."""
    msg = _fail("""
theorem bad_pbc_assume:
  suppose hp: P
    assume hnp: not P
    have hbot: false by neg_elim hp hnp
  have h: P by pbc hp hbot
  conclude P by h
""", "classical_prop")
    assert "subproof assumption" in msg or "does not match" in msg


def test_pbc_derives_dne():
    """pbc subsumes dne: prove not not P -> P using pbc instead of dne."""
    src = """
theorem dne_via_pbc:
  suppose h1: not not P
    suppose hnp: not P
      have hbot: false by neg_elim hnp h1
    have hp: P by pbc hnp hbot
  have h_thm: not not P -> P by imp_intro h1 hp
  conclude not not P -> P by h_thm
"""
    _ok(src, "classical_prop")


# ---------------------------------------------------------------------------
# Peirce's law: ((P -> Q) -> P) -> P
# ---------------------------------------------------------------------------

def test_peirce_accepted_classically():
    src = """
theorem peirce:
  suppose h: (P -> Q) -> P
    suppose hnp: not P
      suppose hp: P
        have hbot: false by neg_elim hp hnp
        have hq: Q by ex_falso hbot
      have hpq: P -> Q by imp_intro hp hq
      have hp2: P by mp h hpq
      have hbot2: false by neg_elim hp2 hnp
    have hp3: P by pbc hnp hbot2
  have h_thm: ((P -> Q) -> P) -> P by imp_intro h hp3
  conclude ((P -> Q) -> P) -> P by h_thm
"""
    _ok(src, "classical_prop")


def test_peirce_rejected_intuitionistically():
    src = """
theorem peirce:
  suppose h: (P -> Q) -> P
    suppose hnp: not P
      suppose hp: P
        have hbot: false by neg_elim hp hnp
        have hq: Q by ex_falso hbot
      have hpq: P -> Q by imp_intro hp hq
      have hp2: P by mp h hpq
      have hbot2: false by neg_elim hp2 hnp
    have hp3: P by pbc hnp hbot2
  have h_thm: ((P -> Q) -> P) -> P by imp_intro h hp3
  conclude ((P -> Q) -> P) -> P by h_thm
"""
    msg = _fail(src, "intuitionistic_prop")
    assert "not available" in msg and "pbc" in msg


# ---------------------------------------------------------------------------
# Existing classical rules still work, dne not removed
# ---------------------------------------------------------------------------

def test_dne_still_present():
    assert "dne" in LOGICS["classical_prop"].rules
    assert "dne" not in LOGICS["intuitionistic_prop"].rules


def test_dne_still_works():
    src = """
theorem dne_check:
  assume h: not not P
  have h2: P by dne h
  conclude P by h2
"""
    _ok(src, "classical_prop")
    msg = _fail(src, "intuitionistic_prop")
    assert "dne" in msg


def test_all_shared_rules_still_in_intuitionistic():
    intu = LOGICS["intuitionistic_prop"].rules
    for rule in ("copy", "mp", "imp_intro", "and_intro", "and_elim_left",
                 "and_elim_right", "neg_elim", "ex_falso",
                 "or_intro_left", "or_intro_right", "neg_intro", "or_elim"):
        assert rule in intu, f"shared rule '{rule}' missing from intuitionistic_prop"
