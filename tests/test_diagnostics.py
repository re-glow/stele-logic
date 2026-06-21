"""Tests for stele/diagnostics.py: structural diagnostic collection."""
import pytest
from stele.parser import parse_theorem
from stele.diagnostics import Diagnostic, diagnose_theorem, diagnose_graph
from stele.proofgraph import ProofGraph, ProofNode

# ---------------------------------------------------------------------------
# Inline proof fixtures
# ---------------------------------------------------------------------------

_VALID_SIMPLE = """
theorem valid_simple:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
  conclude Q by h3
"""

_VALID_PEIRCE = open("examples/peirce.stele", encoding="utf-8").read()

# UndefinedSymbol: 'missing' never defined
_UNDEF = """
theorem undef:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 missing
  conclude Q by h3
"""

# MissingHypothesis: h2 used before its introduction
_FORWARD_REF = """
theorem forward_ref:
  have h1: P by copy h2
  assume h2: P
  conclude P by h1
"""

# MissingHypothesis: conclude references a label from inside a closed subproof
_CONCLUDE_SCOPE = """
theorem conclude_scope:
  suppose h1: P
    have h2: P by copy h1
  conclude P by h2
"""

# UnsupportedConclusion: h1 is P, conclusion claims Q
_WRONG_CONCLUSION = """
theorem wrong_conclusion:
  assume h1: P
  conclude Q by h1
"""

# UndefinedSymbol at conclude: nonexistent label
_UNDEF_CONCLUDE = """
theorem undef_conclude:
  assume h1: P
  conclude P by ghost
"""

# UnusedAssumption: h2 is never referenced in the proof path
_UNUSED = """
theorem unused:
  assume h1: P
  assume h2: Q
  conclude P by h1
"""

# Multiple issues in one proof: UndefinedSymbol + UnusedAssumption
_MULTI = """
theorem multi:
  assume h1: P
  assume h2: Q
  have h3: P by copy gone
  conclude P by h1
"""

# Valid imp_intro (discharge) — must produce NO diagnostics
_IMP_INTRO = """
theorem imp_i:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h2
  conclude P -> P by h3
"""

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _codes(diags):
    return [d.code for d in diags]


def _has(diags, code):
    return any(d.code == code for d in diags)


# ---------------------------------------------------------------------------
# 1. Clean proofs produce no diagnostics
# ---------------------------------------------------------------------------

def test_valid_simple_no_diagnostics():
    diags = diagnose_theorem(parse_theorem(_VALID_SIMPLE))
    assert diags == []


def test_valid_peirce_no_diagnostics():
    diags = diagnose_theorem(parse_theorem(_VALID_PEIRCE), "classical_prop")
    assert diags == []


def test_valid_imp_intro_no_diagnostics():
    """imp_intro with discharge refs must not raise false positives."""
    diags = diagnose_theorem(parse_theorem(_IMP_INTRO), "intuitionistic_prop")
    assert diags == []


def test_valid_example_files():
    """Spot-check that existing valid example files produce no error diagnostics."""
    for path in ("examples/dne.stele", "examples/neg_intro.stele"):
        import pathlib
        if not pathlib.Path(path).exists():
            continue
        src = open(path, encoding="utf-8").read()
        thm = parse_theorem(src)
        diags = diagnose_theorem(thm)
        errors = [d for d in diags if d.severity == "error"]
        assert errors == [], f"{path}: unexpected errors {errors}"


# ---------------------------------------------------------------------------
# 2. UndefinedSymbol
# ---------------------------------------------------------------------------

def test_undefined_symbol_in_have():
    diags = diagnose_theorem(parse_theorem(_UNDEF), "intuitionistic_prop")
    assert _has(diags, "UndefinedSymbol")


def test_undefined_symbol_message_contains_label():
    diags = diagnose_theorem(parse_theorem(_UNDEF), "intuitionistic_prop")
    msgs = [d.message for d in diags if d.code == "UndefinedSymbol"]
    assert any("missing" in m for m in msgs)


def test_undefined_symbol_severity_is_error():
    diags = diagnose_theorem(parse_theorem(_UNDEF), "intuitionistic_prop")
    for d in diags:
        if d.code == "UndefinedSymbol":
            assert d.severity == "error"
            break


def test_undefined_symbol_at_conclude():
    diags = diagnose_theorem(parse_theorem(_UNDEF_CONCLUDE))
    assert _has(diags, "UndefinedSymbol")
    undef = [d for d in diags if d.code == "UndefinedSymbol"]
    assert any("ghost" in d.message for d in undef)


def test_undefined_symbol_from_file():
    src = open("examples/diag_undef.stele", encoding="utf-8").read()
    diags = diagnose_theorem(parse_theorem(src))
    assert _has(diags, "UndefinedSymbol")


# ---------------------------------------------------------------------------
# 3. MissingHypothesis
# ---------------------------------------------------------------------------

def test_missing_hypothesis_forward_ref():
    """Using a label before it is introduced → MissingHypothesis."""
    diags = diagnose_theorem(parse_theorem(_FORWARD_REF), "intuitionistic_prop")
    assert _has(diags, "MissingHypothesis")


def test_missing_hypothesis_message_contains_label():
    diags = diagnose_theorem(parse_theorem(_FORWARD_REF), "intuitionistic_prop")
    msgs = [d.message for d in diags if d.code == "MissingHypothesis"]
    assert any("h2" in m for m in msgs)


def test_missing_hypothesis_severity_is_error():
    diags = diagnose_theorem(parse_theorem(_FORWARD_REF), "intuitionistic_prop")
    for d in diags:
        if d.code == "MissingHypothesis":
            assert d.severity == "error"
            break


def test_missing_hypothesis_at_conclude_scope_leak():
    """Concluding with a label from inside a closed subproof → MissingHypothesis."""
    diags = diagnose_theorem(parse_theorem(_CONCLUDE_SCOPE), "intuitionistic_prop")
    assert _has(diags, "MissingHypothesis")
    missing = [d for d in diags if d.code == "MissingHypothesis"]
    assert any("h2" in d.message for d in missing)


def test_missing_hypothesis_from_file():
    src = open("examples/diag_missing.stele", encoding="utf-8").read()
    diags = diagnose_theorem(parse_theorem(src))
    assert _has(diags, "MissingHypothesis")


# ---------------------------------------------------------------------------
# 4. UnsupportedConclusion
# ---------------------------------------------------------------------------

def test_unsupported_conclusion_formula_mismatch():
    diags = diagnose_theorem(parse_theorem(_WRONG_CONCLUSION))
    assert _has(diags, "UnsupportedConclusion")


def test_unsupported_conclusion_message():
    diags = diagnose_theorem(parse_theorem(_WRONG_CONCLUSION))
    msgs = [d.message for d in diags if d.code == "UnsupportedConclusion"]
    assert msgs, "expected at least one UnsupportedConclusion diagnostic"
    assert any("Q" in m or "P" in m for m in msgs)


def test_unsupported_conclusion_severity_is_error():
    diags = diagnose_theorem(parse_theorem(_WRONG_CONCLUSION))
    for d in diags:
        if d.code == "UnsupportedConclusion":
            assert d.severity == "error"
            break


def test_unsupported_conclusion_from_file():
    src = open("examples/diag_conclusion.stele", encoding="utf-8").read()
    diags = diagnose_theorem(parse_theorem(src))
    assert _has(diags, "UnsupportedConclusion")


# ---------------------------------------------------------------------------
# 5. CircularDependency
# ---------------------------------------------------------------------------

def test_circular_dependency_two_node_cycle():
    """Synthetic two-node cycle → CircularDependency."""
    g = ProofGraph(name="cycle2")
    g.nodes["a"] = ProofNode("a", "have", "P", "copy")
    g.nodes["b"] = ProofNode("b", "have", "Q", "copy")
    g.edges += [("a", "b"), ("b", "a")]
    diags = diagnose_graph(g)
    assert _has(diags, "CircularDependency")


def test_circular_dependency_three_node_cycle():
    """Three-node cycle a→b→c→a."""
    g = ProofGraph(name="cycle3")
    for lbl in ("a", "b", "c"):
        g.nodes[lbl] = ProofNode(lbl, "have", lbl, None)
    g.edges += [("a", "b"), ("b", "c"), ("c", "a")]
    diags = diagnose_graph(g)
    assert _has(diags, "CircularDependency")


def test_circular_dependency_severity_is_error():
    g = ProofGraph(name="cycletest")
    g.nodes["x"] = ProofNode("x", "have", "P", None)
    g.nodes["y"] = ProofNode("y", "have", "P", None)
    g.edges += [("x", "y"), ("y", "x")]
    diags = diagnose_graph(g)
    for d in diags:
        if d.code == "CircularDependency":
            assert d.severity == "error"
            return
    pytest.fail("CircularDependency not reported")


def test_no_circular_dependency_in_valid_proof():
    """A verified proof must not produce CircularDependency."""
    from stele.proofgraph import build_proof_graph
    thm = parse_theorem(_VALID_PEIRCE)
    g = build_proof_graph(thm)
    diags = diagnose_graph(g)
    assert not _has(diags, "CircularDependency")


def test_no_circular_dependency_in_linear_chain():
    g = ProofGraph(name="chain", conclusion="_c")
    for lbl in ("a", "b", "c"):
        g.nodes[lbl] = ProofNode(lbl, "have", lbl, None)
    g.edges += [("a", "b"), ("b", "c")]
    diags = diagnose_graph(g)
    assert not _has(diags, "CircularDependency")


# ---------------------------------------------------------------------------
# 6. UnusedAssumption
# ---------------------------------------------------------------------------

def test_unused_assumption_reported():
    diags = diagnose_theorem(parse_theorem(_UNUSED))
    assert _has(diags, "UnusedAssumption")


def test_unused_assumption_correct_label():
    diags = diagnose_theorem(parse_theorem(_UNUSED))
    msgs = [d.message for d in diags if d.code == "UnusedAssumption"]
    assert any("h2" in m for m in msgs)


def test_unused_assumption_severity_is_warning():
    diags = diagnose_theorem(parse_theorem(_UNUSED))
    for d in diags:
        if d.code == "UnusedAssumption":
            assert d.severity == "warning"
            return
    pytest.fail("UnusedAssumption not reported")


def test_used_assumption_not_flagged():
    """h1 contributes to the conclusion and must NOT be flagged."""
    diags = diagnose_theorem(parse_theorem(_UNUSED))
    flagged = [d.message for d in diags if d.code == "UnusedAssumption"]
    assert not any("h1" in m for m in flagged)


def test_unused_from_file():
    src = open("examples/diag_unused.stele", encoding="utf-8").read()
    diags = diagnose_theorem(parse_theorem(src))
    assert _has(diags, "UnusedAssumption")


def test_no_unused_in_peirce():
    """All assumptions in Peirce's law contribute to the conclusion."""
    diags = diagnose_theorem(parse_theorem(_VALID_PEIRCE), "classical_prop")
    assert not _has(diags, "UnusedAssumption")


def test_suppose_used_in_imp_intro_not_flagged():
    """A suppose label referenced by imp_intro discharge must not be flagged unused."""
    diags = diagnose_theorem(parse_theorem(_IMP_INTRO), "intuitionistic_prop")
    flagged = [d.message for d in diags if d.code == "UnusedAssumption"]
    assert not any("h1" in m for m in flagged)


def test_unused_assumption_with_diagnose_graph_helper():
    """diagnose_graph() directly reports UnusedAssumption for synthetic graphs."""
    from stele.proofgraph import ProofGraph, ProofNode
    g = ProofGraph(name="test_unused", conclusion="_c")
    g.nodes["h1"] = ProofNode("h1", "assumption", "P", None)
    g.nodes["h2"] = ProofNode("h2", "assumption", "Q", None)   # unused
    g.nodes["_c"] = ProofNode("_c", "conclude", "P", None)
    g.edges.append(("h1", "_c"))
    diags = diagnose_graph(g)
    assert _has(diags, "UnusedAssumption")
    assert any("h2" in d.message for d in diags if d.code == "UnusedAssumption")


# ---------------------------------------------------------------------------
# 7. Multiple diagnostics collected in one pass
# ---------------------------------------------------------------------------

def test_multiple_diagnostics_in_one_proof():
    """Multi-issue proof returns ≥2 diagnostics (UndefinedSymbol + UnusedAssumption)."""
    diags = diagnose_theorem(parse_theorem(_MULTI), "intuitionistic_prop")
    assert len(diags) >= 2
    assert _has(diags, "UndefinedSymbol")
    assert _has(diags, "UnusedAssumption")


def test_multiple_does_not_stop_at_first():
    """All distinct codes are collected, not just the first."""
    codes = _codes(diagnose_theorem(parse_theorem(_MULTI), "intuitionistic_prop"))
    assert "UndefinedSymbol" in codes
    assert "UnusedAssumption" in codes


# ---------------------------------------------------------------------------
# 8. check remains strict and unchanged
# ---------------------------------------------------------------------------

def test_check_still_raises_on_undef(tmp_path):
    """cli check must still fail on the same proof that diagnose analyses."""
    from stele.cli import cmd_check
    p = tmp_path / "undef.stele"
    p.write_text(_UNDEF)
    rc = cmd_check(str(p), "intuitionistic_prop")
    assert rc == 1


def test_check_still_passes_valid_proof(tmp_path):
    p = tmp_path / "simple.stele"
    p.write_text(_VALID_SIMPLE)
    from stele.cli import cmd_check
    rc = cmd_check(str(p), "intuitionistic_prop")
    assert rc == 0


def test_diagnose_does_not_affect_check_return_code(tmp_path):
    """Running diagnose on a file must not change check's return code."""
    from stele.cli import cmd_check, cmd_diagnose
    p = tmp_path / "valid.stele"
    p.write_text(_VALID_SIMPLE)
    before = cmd_check(str(p), "intuitionistic_prop")
    cmd_diagnose(str(p), "intuitionistic_prop")
    after = cmd_check(str(p), "intuitionistic_prop")
    assert before == after == 0


# ---------------------------------------------------------------------------
# 9. CLI diagnose output format
# ---------------------------------------------------------------------------

def test_cli_diagnose_clean_proof_returns_0(tmp_path, capsys):
    from stele.cli import cmd_diagnose
    p = tmp_path / "clean.stele"
    p.write_text(_VALID_SIMPLE)
    rc = cmd_diagnose(str(p), "intuitionistic_prop")
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_cli_diagnose_error_returns_1(tmp_path, capsys):
    from stele.cli import cmd_diagnose
    p = tmp_path / "bad.stele"
    p.write_text(_UNDEF)
    rc = cmd_diagnose(str(p), "intuitionistic_prop")
    assert rc == 1


def test_cli_diagnose_output_contains_code(tmp_path, capsys):
    from stele.cli import cmd_diagnose
    p = tmp_path / "undef.stele"
    p.write_text(_UNDEF)
    cmd_diagnose(str(p), "intuitionistic_prop")
    out = capsys.readouterr().out
    assert "UndefinedSymbol" in out


def test_cli_diagnose_output_contains_severity(tmp_path, capsys):
    from stele.cli import cmd_diagnose
    p = tmp_path / "undef.stele"
    p.write_text(_UNDEF)
    cmd_diagnose(str(p), "intuitionistic_prop")
    out = capsys.readouterr().out
    assert "ERROR" in out


def test_cli_diagnose_output_contains_line(tmp_path, capsys):
    from stele.cli import cmd_diagnose
    p = tmp_path / "undef.stele"
    p.write_text(_UNDEF)
    cmd_diagnose(str(p), "intuitionistic_prop")
    out = capsys.readouterr().out
    assert "line=" in out


def test_cli_diagnose_warning_returns_0(tmp_path, capsys):
    """Warning-only (UnusedAssumption) should return 0."""
    from stele.cli import cmd_diagnose
    p = tmp_path / "unused.stele"
    p.write_text(_UNUSED)
    rc = cmd_diagnose(str(p), "intuitionistic_prop")
    assert rc == 0
    out = capsys.readouterr().out
    assert "WARNING" in out
    assert "UnusedAssumption" in out


def test_cli_diagnose_file_undef(capsys):
    from stele.cli import cmd_diagnose
    rc = cmd_diagnose("examples/diag_undef.stele", None)
    assert rc == 1
    out = capsys.readouterr().out
    assert "UndefinedSymbol" in out


def test_cli_diagnose_file_missing(capsys):
    from stele.cli import cmd_diagnose
    rc = cmd_diagnose("examples/diag_missing.stele", None)
    assert rc == 1
    out = capsys.readouterr().out
    assert "MissingHypothesis" in out


def test_cli_diagnose_file_conclusion(capsys):
    from stele.cli import cmd_diagnose
    rc = cmd_diagnose("examples/diag_conclusion.stele", None)
    assert rc == 1
    out = capsys.readouterr().out
    assert "UnsupportedConclusion" in out


def test_cli_diagnose_file_unused(capsys):
    from stele.cli import cmd_diagnose
    rc = cmd_diagnose("examples/diag_unused.stele", None)
    assert rc == 0
    out = capsys.readouterr().out
    assert "UnusedAssumption" in out


def test_cli_diagnose_peirce_clean(capsys):
    from stele.cli import cmd_diagnose
    rc = cmd_diagnose("examples/peirce.stele", "classical_prop")
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


# ---------------------------------------------------------------------------
# 10. Diagnostic object properties
# ---------------------------------------------------------------------------

def test_diagnostic_is_frozen():
    d = Diagnostic("UndefinedSymbol", "test", 5, "error")
    try:
        d.code = "other"
        pytest.fail("Diagnostic should be frozen")
    except Exception:
        pass


def test_diagnostic_line_none_allowed():
    d = Diagnostic("CircularDependency", "cycle", None, "error")
    assert d.line is None


def test_all_required_codes_can_be_instantiated():
    """Stable code strings must be valid (not a typo)."""
    codes = [
        "UndefinedSymbol", "MissingHypothesis", "UnsupportedConclusion",
        "CircularDependency", "UnusedAssumption",
    ]
    for code in codes:
        d = Diagnostic(code, f"test {code}", None, "error")
        assert d.code == code
