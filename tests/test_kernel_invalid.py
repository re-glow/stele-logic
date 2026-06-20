import pytest
from stele.parser import parse_theorem
from stele.kernel import check_theorem
from stele.errors import ProofError


def _fail(src, logic="classical_prop"):
    with pytest.raises(ProofError) as e:
        check_theorem(parse_theorem(src), logic)
    return str(e.value)


def test_wrong_premise_reports_mismatch():
    msg = _fail("""
theorem bad_mp:
  assume h1: P -> Q
  assume h2: R
  have h3: Q by mp h1 h2
  conclude Q by h3
""")
    assert "premise 2" in msg and "R" in msg


def test_unknown_reference():
    msg = _fail("""
theorem bad_ref:
  assume h1: P
  have h2: Q by copy h9
  conclude Q by h2
""")
    assert "unknown reference" in msg


def test_discharged_hypothesis_out_of_scope():
    msg = _fail("""
theorem leak:
  suppose h1: P
    have h2: P by copy h1
  have h3: P by copy h2
  conclude P by h3
""")
    assert "unknown reference 'h2'" in msg


def test_conclusion_mismatch():
    msg = _fail("""
theorem bad_concl:
  assume h1: P
  conclude Q by h1
""")
    assert "does not match" in msg
