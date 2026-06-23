"""Tests for stele.certificate — formula serialization and certificate emission."""
import json
import pytest
from stele.ast import Var, Op

P = Var("P")
Q = Var("Q")
BOT = Op("bot", ())


# ---------------------------------------------------------------------------
# Formula serialization round-trips
# ---------------------------------------------------------------------------

class TestFormulaSerialization:
    def test_var(self):
        from stele.certificate import formula_to_json, formula_from_json
        d = formula_to_json(P)
        assert d == {"kind": "var", "name": "P"}
        assert formula_from_json(d) == P

    def test_bot(self):
        from stele.certificate import formula_to_json, formula_from_json
        d = formula_to_json(BOT)
        assert d == {"kind": "bot"}
        assert formula_from_json(d) == BOT

    def test_imp(self):
        from stele.certificate import formula_to_json, formula_from_json
        f = Op("imp", (P, Q))
        d = formula_to_json(f)
        assert d["kind"] == "op"
        assert d["op"] == "imp"
        assert formula_from_json(d) == f

    def test_and(self):
        from stele.certificate import formula_to_json, formula_from_json
        f = Op("and", (P, Q))
        assert formula_from_json(formula_to_json(f)) == f

    def test_or(self):
        from stele.certificate import formula_to_json, formula_from_json
        f = Op("or", (P, Q))
        assert formula_from_json(formula_to_json(f)) == f

    def test_not(self):
        from stele.certificate import formula_to_json, formula_from_json
        f = Op("not", (P,))
        d = formula_to_json(f)
        assert d["op"] == "not"
        assert formula_from_json(d) == f

    def test_nested(self):
        from stele.certificate import formula_to_json, formula_from_json
        f = Op("imp", (Op("not", (P,)), P))
        assert formula_from_json(formula_to_json(f)) == f

    def test_unknown_op_raises(self):
        from stele.certificate import formula_to_json
        with pytest.raises(ValueError, match="unsupported connective"):
            formula_to_json(Op("xor", (P, Q)))

    def test_from_json_bad_kind_raises(self):
        from stele.certificate import formula_from_json
        with pytest.raises(ValueError, match="unknown kind"):
            formula_from_json({"kind": "unknown"})

    def test_from_json_not_dict_raises(self):
        from stele.certificate import formula_from_json
        with pytest.raises(ValueError):
            formula_from_json([1, 2, 3])


# ---------------------------------------------------------------------------
# Certificate emission from real proof sources
# ---------------------------------------------------------------------------

IMP_SELF_SRC = """\
theorem imp_self:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h2
  conclude P -> P by h3
"""

DNE_SRC = """\
theorem dne_consequent using classical_prop:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""

NEG_INTRO_SRC = """\
theorem neg_intro_demo:
  suppose h1: P and not P
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h1 h4
  conclude not (P and not P) by h5
"""

OR_COMM_SRC = """\
theorem or_comm:
  assume h1: P or Q
  suppose h2: P
    have h3: Q or P by or_intro_right h2
  suppose h4: Q
    have h5: Q or P by or_intro_left h4
  have h6: Q or P by or_elim h1 h2 h3 h4 h5
  conclude Q or P by h6
"""


def _parse(src):
    from stele.parser import parse_theorem
    return parse_theorem(src)


def _emit(src, logic=None):
    from stele.certificate import emit_certificate
    thm = _parse(src)
    logic_name = logic or thm.logic or "intuitionistic_prop"
    return emit_certificate(thm, logic_name)


class TestCertEmission:
    def test_imp_self_format(self):
        cert = _emit(IMP_SELF_SRC)
        assert cert["format"] == "stele-proof-certificate"
        assert cert["version"] == "1"
        assert cert["theorem"] == "imp_self"
        assert cert["logic"] == "intuitionistic_prop"

    def test_imp_self_has_steps(self):
        cert = _emit(IMP_SELF_SRC)
        kinds = [s["kind"] for s in cert["steps"]]
        assert "suppose_open" in kinds
        assert "suppose_close" in kinds
        assert "have" in kinds
        assert "conclude" in kinds

    def test_imp_self_suppose_open_close_balanced(self):
        cert = _emit(IMP_SELF_SRC)
        opens = [s for s in cert["steps"] if s["kind"] == "suppose_open"]
        closes = [s for s in cert["steps"] if s["kind"] == "suppose_close"]
        assert len(opens) == len(closes)

    def test_dne_emission_classical(self):
        cert = _emit(DNE_SRC, "classical_prop")
        assert cert["logic"] == "classical_prop"
        have_rules = [s["rule"] for s in cert["steps"] if s["kind"] == "have"]
        assert "dne" in have_rules

    def test_neg_intro_structure(self):
        cert = _emit(NEG_INTRO_SRC)
        steps = cert["steps"]
        opens = [s for s in steps if s["kind"] == "suppose_open"]
        closes = [s for s in steps if s["kind"] == "suppose_close"]
        assert len(opens) == len(closes) == 1

    def test_or_comm_two_subproofs(self):
        cert = _emit(OR_COMM_SRC)
        opens = [s for s in cert["steps"] if s["kind"] == "suppose_open"]
        closes = [s for s in cert["steps"] if s["kind"] == "suppose_close"]
        assert len(opens) == len(closes) == 2

    def test_invalid_proof_does_not_emit(self):
        from stele.certificate import emit_certificate
        from stele.errors import ProofError
        # dne under intuitionistic should raise ProofError
        src = """\
theorem bad:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""
        thm = _parse(src)
        with pytest.raises(ProofError):
            emit_certificate(thm, "intuitionistic_prop")

    def test_cert_contains_metadata(self):
        cert = _emit(IMP_SELF_SRC)
        assert "metadata" in cert
        assert cert["metadata"]["generator"] == "stele"

    def test_conclusion_formula_correct(self):
        from stele.certificate import formula_from_json
        cert = _emit(IMP_SELF_SRC)
        concl = formula_from_json(cert["conclusion"])
        assert concl == Op("imp", (P, P))


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

class TestCertJsonRoundtrip:
    def test_roundtrip(self):
        from stele.certificate import certificate_to_json, certificate_from_json
        cert = _emit(IMP_SELF_SRC)
        text = certificate_to_json(cert)
        cert2 = certificate_from_json(text)
        assert cert2["theorem"] == cert["theorem"]
        assert cert2["logic"] == cert["logic"]
        assert cert2["steps"] == cert["steps"]

    def test_bad_json_raises(self):
        from stele.certificate import certificate_from_json
        with pytest.raises(ValueError, match="invalid JSON"):
            certificate_from_json("{bad json]")

    def test_missing_field_raises(self):
        from stele.certificate import certificate_from_json
        partial = json.dumps({"format": "stele-proof-certificate", "version": "1"})
        with pytest.raises(ValueError, match="missing required field"):
            certificate_from_json(partial)

    def test_wrong_format_raises(self):
        from stele.certificate import certificate_from_json, certificate_to_json
        cert = _emit(IMP_SELF_SRC)
        cert["format"] = "unknown-format"
        text = certificate_to_json(cert)
        with pytest.raises(ValueError, match="unrecognised format"):
            certificate_from_json(text)

    def test_wrong_version_raises(self):
        from stele.certificate import certificate_from_json, certificate_to_json
        cert = _emit(IMP_SELF_SRC)
        cert["version"] = "99"
        with pytest.raises(ValueError, match="unsupported version"):
            certificate_from_json(certificate_to_json(cert))
