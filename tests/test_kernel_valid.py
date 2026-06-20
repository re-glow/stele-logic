from stele.parser import parse_theorem
from stele.kernel import check_theorem


def _ok(src, logic):
    check_theorem(parse_theorem(src), logic)


def test_mp_chain_valid_in_both_logics():
    src = """
theorem chain:
  assume h1: P -> Q
  assume h2: Q -> R
  assume h3: P
  have h4: Q by mp h1 h3
  have h5: R by mp h2 h4
  conclude R by h5
"""
    _ok(src, "classical_prop")
    _ok(src, "intuitionistic_prop")


def test_and_rules():
    src = """
theorem and_demo:
  assume h1: P
  assume h2: Q
  have h3: P and Q by and_intro h1 h2
  have h4: P by and_elim_left h3
  have h5: Q by and_elim_right h3
  conclude Q by h5
"""
    _ok(src, "intuitionistic_prop")


def test_imp_intro_discharge():
    src = """
theorem imp_self:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h2
  conclude P -> P by h3
"""
    _ok(src, "intuitionistic_prop")
