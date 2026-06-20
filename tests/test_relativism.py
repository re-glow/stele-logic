"""Flagship: the same proof text is valid in one world and not another."""
import pytest
from stele.parser import parse_theorem
from stele.kernel import check_theorem
from stele.errors import ProofError

DNE = """
theorem dne_consequent:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""

DNE_LAW = """
theorem dne_law:
  suppose h1: not not P
    have h2: P by dne h1
  have h3: not not P -> P by imp_intro h1 h2
  conclude not not P -> P by h3
"""


def test_dne_verified_classically():
    lg, _ = check_theorem(parse_theorem(DNE), "classical_prop")
    assert lg.name == "classical_prop"


def test_dne_rejected_intuitionistically():
    with pytest.raises(ProofError) as e:
        check_theorem(parse_theorem(DNE), "intuitionistic_prop")
    m = str(e.value)
    assert "dne" in m and "not available" in m


def test_dne_law_classical_only():
    check_theorem(parse_theorem(DNE_LAW), "classical_prop")
    with pytest.raises(ProofError):
        check_theorem(parse_theorem(DNE_LAW), "intuitionistic_prop")
