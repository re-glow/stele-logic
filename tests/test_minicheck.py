"""Tests for stele.minicheck — small independent certificate checker."""
import copy
import json
import pytest
from stele.ast import Var, Op

P = Var("P")
Q = Var("Q")
BOT = Op("bot", ())


# ---------------------------------------------------------------------------
# Shared helpers
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

LEM_SRC = """\
theorem lem_classical using classical_prop:
  have h1: P or not P by lem
  conclude P or not P by h1
"""

PBC_SRC = """\
theorem pbc_demo using classical_prop:
  assume h1: not not P
  suppose h2: not P
    have h3: false by neg_elim h2 h1
  have h4: P by pbc h2 h3
  conclude P by h4
"""


def _parse(src):
    from stele.parser import parse_theorem
    return parse_theorem(src)


def _cert(src, logic=None):
    from stele.certificate import emit_certificate
    thm = _parse(src)
    logic_name = logic or thm.logic or "intuitionistic_prop"
    return emit_certificate(thm, logic_name)


def _minicheck(cert):
    from stele.minicheck import minicheck
    return minicheck(cert)


# ---------------------------------------------------------------------------
# Basic acceptance: valid proofs pass
# ---------------------------------------------------------------------------

class TestMinicheckAccepts:
    def test_imp_self_passes(self):
        r = _minicheck(_cert(IMP_SELF_SRC))
        assert r.ok, r.message

    def test_dne_passes(self):
        r = _minicheck(_cert(DNE_SRC, "classical_prop"))
        assert r.ok, r.message

    def test_neg_intro_passes(self):
        r = _minicheck(_cert(NEG_INTRO_SRC))
        assert r.ok, r.message

    def test_or_comm_passes(self):
        r = _minicheck(_cert(OR_COMM_SRC))
        assert r.ok, r.message

    def test_lem_passes(self):
        r = _minicheck(_cert(LEM_SRC, "classical_prop"))
        assert r.ok, r.message

    def test_pbc_passes(self):
        r = _minicheck(_cert(PBC_SRC, "classical_prop"))
        assert r.ok, r.message

    def test_result_contains_theorem_and_logic(self):
        r = _minicheck(_cert(IMP_SELF_SRC))
        assert r.theorem == "imp_self"
        assert r.logic == "intuitionistic_prop"


# ---------------------------------------------------------------------------
# Logic boundary: classical rules rejected under intuitionistic
# ---------------------------------------------------------------------------

class TestMinicheckLogicBoundary:
    def test_classical_cert_rejected_under_intuitionistic(self):
        cert = _cert(DNE_SRC, "classical_prop")
        cert = copy.deepcopy(cert)
        cert["logic"] = "intuitionistic_prop"
        r = _minicheck(cert)
        assert not r.ok
        assert "dne" in r.message

    def test_lem_rejected_under_intuitionistic(self):
        cert = _cert(LEM_SRC, "classical_prop")
        cert = copy.deepcopy(cert)
        cert["logic"] = "intuitionistic_prop"
        r = _minicheck(cert)
        assert not r.ok
        assert "lem" in r.message

    def test_pbc_rejected_under_intuitionistic(self):
        cert = _cert(PBC_SRC, "classical_prop")
        cert = copy.deepcopy(cert)
        cert["logic"] = "intuitionistic_prop"
        r = _minicheck(cert)
        assert not r.ok

    def test_intuitionistic_proof_passes_under_classical(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        cert["logic"] = "classical_prop"
        r = _minicheck(cert)
        assert r.ok, r.message

    def test_unsupported_logic_returns_failure(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        cert["logic"] = "nonexistent_logic"
        r = _minicheck(cert)
        assert not r.ok
        assert "nonexistent_logic" in r.message


# ---------------------------------------------------------------------------
# Tamper detection: formula tampering
# ---------------------------------------------------------------------------

class TestTamperFormula:
    def test_tamper_assume_formula(self):
        cert = _cert(DNE_SRC, "classical_prop")
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "assume" and step["label"] == "h1":
                # Change ¬¬P to just P
                step["formula"] = {"kind": "var", "name": "P"}
                break
        r = _minicheck(cert)
        assert not r.ok

    def test_tamper_have_formula(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have" and step.get("rule") == "copy":
                step["formula"] = {"kind": "var", "name": "Q"}
                break
        r = _minicheck(cert)
        assert not r.ok

    def test_tamper_conclude_formula(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "conclude":
                step["formula"] = {"kind": "var", "name": "Q"}
                break
        r = _minicheck(cert)
        assert not r.ok

    def test_tamper_declared_conclusion(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        cert["conclusion"] = {"kind": "var", "name": "Q"}
        r = _minicheck(cert)
        assert not r.ok

    def test_tamper_have_formula_mismatch_conclusion(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have" and step.get("label") == "h3":
                # Change P -> P to P -> Q
                step["formula"] = {
                    "kind": "op", "op": "imp",
                    "args": [{"kind": "var", "name": "P"},
                             {"kind": "var", "name": "Q"}]
                }
                break
        r = _minicheck(cert)
        assert not r.ok


# ---------------------------------------------------------------------------
# Tamper detection: rule tampering
# ---------------------------------------------------------------------------

class TestTamperRule:
    def test_tamper_rule_name(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have" and step.get("rule") == "copy":
                step["rule"] = "mp"
                break
        r = _minicheck(cert)
        assert not r.ok

    def test_swap_rule_with_unavailable_classical(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have":
                step["rule"] = "dne"
                step["refs"] = [step["refs"][0]] if step.get("refs") else ["h1"]
                break
        r = _minicheck(cert)
        assert not r.ok

    def test_tamper_rule_nonexistent(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have" and step.get("rule") == "imp_intro":
                step["rule"] = "fake_rule"
                break
        r = _minicheck(cert)
        assert not r.ok


# ---------------------------------------------------------------------------
# Tamper detection: ref tampering
# ---------------------------------------------------------------------------

class TestTamperRefs:
    def test_remove_ref(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have" and step.get("rule") == "imp_intro":
                step["refs"] = []
                break
        r = _minicheck(cert)
        assert not r.ok

    def test_change_ref_to_nonexistent(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have" and step.get("rule") == "copy":
                step["refs"] = ["nonexistent_label"]
                break
        r = _minicheck(cert)
        assert not r.ok

    def test_swap_ref_labels(self):
        cert = _cert(OR_COMM_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have" and step.get("rule") == "or_elim":
                # swap the two subproof arm pairs (refs[1:3] ↔ refs[3:5])
                r = step["refs"]
                if len(r) == 5:
                    step["refs"] = [r[0], r[3], r[4], r[1], r[2]]
                break
        result = _minicheck(cert)
        # The formulas of the two arms differ, so this should fail
        assert not result.ok


# ---------------------------------------------------------------------------
# Tamper detection: structural step tampering
# ---------------------------------------------------------------------------

class TestTamperStructure:
    def test_remove_step(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        # Remove the suppose_open step
        cert["steps"] = [s for s in cert["steps"] if s["kind"] != "suppose_open"]
        r = _minicheck(cert)
        assert not r.ok

    def test_remove_conclude_step(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        cert["steps"] = [s for s in cert["steps"] if s["kind"] != "conclude"]
        r = _minicheck(cert)
        assert not r.ok

    def test_malformed_json(self):
        from stele.minicheck import minicheck, MiniCheckError
        # Pass a dict that is not a valid certificate (missing required fields)
        try:
            result = minicheck({"format": "stele-proof-certificate", "version": "1"})
            assert not result.ok
        except MiniCheckError:
            pass  # also acceptable — structural error

    def test_steps_empty(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        cert["steps"] = []
        r = _minicheck(cert)
        assert not r.ok

    def test_suppose_close_without_open(self):
        from stele.minicheck import minicheck, MiniCheckError
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        # Remove the suppose_open
        cert["steps"] = [s for s in cert["steps"] if s["kind"] != "suppose_open"]
        # This should raise MiniCheckError (structural error) or return failure
        try:
            result = minicheck(cert)
            assert not result.ok
        except MiniCheckError:
            pass  # also acceptable


# ---------------------------------------------------------------------------
# Discharge rule tamper tests
# ---------------------------------------------------------------------------

class TestDischargeRuleTamper:
    def test_neg_intro_wrong_assume_formula(self):
        cert = _cert(NEG_INTRO_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "suppose_open" and step["label"] == "h1":
                # Change assume formula from P and not P to just P
                step["formula"] = {"kind": "var", "name": "P"}
                break
        r = _minicheck(cert)
        assert not r.ok

    def test_imp_intro_wrong_subproof_pair(self):
        cert = _cert(IMP_SELF_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have" and step.get("rule") == "imp_intro":
                # Use refs that don't correspond to a real closed subproof
                step["refs"] = ["h99", "h100"]
                break
        r = _minicheck(cert)
        assert not r.ok

    def test_or_elim_both_arms_required(self):
        cert = _cert(OR_COMM_SRC)
        cert = copy.deepcopy(cert)
        for step in cert["steps"]:
            if step["kind"] == "have" and step.get("rule") == "or_elim":
                # Remove the second arm refs
                step["refs"] = step["refs"][:3]
                break
        r = _minicheck(cert)
        assert not r.ok


# ---------------------------------------------------------------------------
# Cross-validation: main kernel and minicheck agree
# ---------------------------------------------------------------------------

ADDITIONAL_PROOFS = [
    ("and_intro_demo", "intuitionistic_prop", """\
theorem and_intro_demo:
  assume h1: P
  assume h2: Q
  have h3: P and Q by and_intro h1 h2
  conclude P and Q by h3
"""),
    ("and_elim_demo", "intuitionistic_prop", """\
theorem and_elim_demo:
  assume h1: P and Q
  have h2: P by and_elim_left h1
  have h3: Q by and_elim_right h1
  conclude P by h2
"""),
    ("ex_falso_demo", "intuitionistic_prop", """\
theorem ex_falso_demo:
  assume h1: false
  have h2: P by ex_falso h1
  conclude P by h2
"""),
]


class TestCrossValidation:
    def test_main_and_mini_agree_imp_self(self):
        cert = _cert(IMP_SELF_SRC)
        r = _minicheck(cert)
        assert r.ok

    def test_main_and_mini_agree_dne(self):
        cert = _cert(DNE_SRC, "classical_prop")
        r = _minicheck(cert)
        assert r.ok

    @pytest.mark.parametrize("name,logic,src", ADDITIONAL_PROOFS)
    def test_additional_proofs(self, name, logic, src):
        cert = _cert(src, logic)
        r = _minicheck(cert)
        assert r.ok, f"{name}: {r.message}"

    def test_cert_rejected_by_kernel_never_emitted(self):
        """Certs can only be emitted for proofs the kernel accepts."""
        from stele.certificate import emit_certificate
        from stele.errors import ProofError
        src = """\
theorem bad_dne:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""
        thm = _parse(src)
        with pytest.raises(ProofError):
            emit_certificate(thm, "intuitionistic_prop")


# ---------------------------------------------------------------------------
# Isolation: minicheck does not import kernel/parser/diagnostics
# ---------------------------------------------------------------------------

def _actual_import_lines(module_file):
    """Return lines that are actual import statements (skip docstrings and comments)."""
    result = []
    src = open(module_file, encoding="utf-8").read()
    # Strip module docstring (content between first triple-quotes at file start)
    import ast as _ast
    tree = _ast.parse(src)
    # Collect only import nodes from the AST
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.Import, _ast.ImportFrom)):
            result.append(_ast.unparse(node))
    return result


class TestMinicheckIsolation:
    def test_minicheck_does_not_import_kernel(self):
        import stele.minicheck as mc_mod
        imports = _actual_import_lines(mc_mod.__file__)
        for imp in imports:
            assert "kernel" not in imp, (
                f"minicheck.py must not import kernel; found: {imp!r}")

    def test_minicheck_does_not_import_parser(self):
        import stele.minicheck as mc_mod
        imports = _actual_import_lines(mc_mod.__file__)
        for imp in imports:
            assert "parser" not in imp, (
                f"minicheck.py must not import parser; found: {imp!r}")

    def test_minicheck_does_not_import_diagnostics(self):
        import stele.minicheck as mc_mod
        imports = _actual_import_lines(mc_mod.__file__)
        for imp in imports:
            assert "diagnostics" not in imp, (
                f"minicheck.py must not import diagnostics; found: {imp!r}")

    def test_minicheck_does_not_import_proof_nodes(self):
        import stele.minicheck as mc_mod
        imports = _actual_import_lines(mc_mod.__file__)
        for imp in imports:
            assert ".proof" not in imp and "stele.proof" not in imp, (
                f"minicheck.py must not import stele.proof; found: {imp!r}")

    def test_certificate_does_not_import_kernel_at_module_level(self):
        """certificate.py imports kernel lazily inside emit_certificate only."""
        import stele.certificate as cert_mod
        src = open(cert_mod.__file__, encoding="utf-8").read()
        lines = src.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "from .kernel" in stripped or ("import" in stripped and "kernel" in stripped):
                # Must be inside a function/method (indented)
                assert line.startswith(" ") or line.startswith("\t"), (
                    f"kernel imported at module level on line {i+1}: {line!r}")
