"""Tests for matrix surface mode.

--logic K3/LP/boolean dispatches to matrix evaluation via the same check command.
Proof-mode behaviour must be unaffected.
"""
import pytest
from stele.ast import Var
from stele.errors import SteleError, ParseError
from stele.logic import get_logic, LOGICS
from stele.matrix import K3, LP, BOOLEAN, is_tautology, entails
from stele.parser import parse_formula, parse_matrix_file


# ---------------------------------------------------------------------------
# Logic namespace: matrix logics reachable via get_logic
# ---------------------------------------------------------------------------

def test_k3_in_get_logic():
    lg = get_logic("K3")
    assert lg.semantics == "matrix"
    assert lg.name == "K3"


def test_lp_in_get_logic():
    lg = get_logic("LP")
    assert lg.semantics == "matrix"
    assert lg.name == "LP"


def test_boolean_in_get_logic():
    lg = get_logic("boolean")
    assert lg.semantics == "matrix"
    assert lg.name == "boolean"


def test_matrix_logic_carries_matrix_object():
    assert get_logic("K3").matrix is K3
    assert get_logic("LP").matrix is LP
    assert get_logic("boolean").matrix is BOOLEAN


def test_proof_logics_still_semantics_proof():
    assert get_logic("classical_prop").semantics == "proof"
    assert get_logic("intuitionistic_prop").semantics == "proof"


def test_unknown_logic_raises():
    with pytest.raises(SteleError):
        get_logic("nonexistent")


# ---------------------------------------------------------------------------
# Matrix directive parser
# ---------------------------------------------------------------------------

def test_parse_evaluate_directive():
    ds = parse_matrix_file("evaluate P or not P\n")
    assert len(ds) == 1
    assert ds[0].kind == "evaluate"


def test_parse_tautology_directive():
    ds = parse_matrix_file("tautology? P -> Q\n")
    assert len(ds) == 1
    assert ds[0].kind == "tautology"


def test_parse_entails_directive():
    ds = parse_matrix_file("entails P, not P |- Q\n")
    assert len(ds) == 1
    d = ds[0]
    assert d.kind == "entails"
    assert len(d.premises) == 2
    assert d.formula == Var("Q")


def test_parse_entails_no_premises():
    ds = parse_matrix_file("entails |- P or not P\n")
    assert ds[0].premises == ()


def test_parse_entails_single_premise():
    ds = parse_matrix_file("entails P -> Q |- Q or not P\n")
    assert len(ds[0].premises) == 1


def test_parse_multiple_directives():
    src = "evaluate P\ntautology? P -> P\nentails P |- P\n"
    ds = parse_matrix_file(src)
    assert [d.kind for d in ds] == ["evaluate", "tautology", "entails"]


def test_parse_blank_and_comment_lines_skipped():
    src = "# comment\n\nevaluate P\n# another\n"
    ds = parse_matrix_file(src)
    assert len(ds) == 1


def test_parse_inline_comment_stripped():
    ds = parse_matrix_file("evaluate P  # this is P\n")
    assert ds[0].formula == Var("P")


def test_parse_empty_file_raises():
    with pytest.raises(ParseError):
        parse_matrix_file("# just comments\n\n")


def test_parse_unknown_directive_raises():
    with pytest.raises(ParseError):
        parse_matrix_file("check P\n")


def test_parse_entails_missing_turnstile_raises():
    with pytest.raises(ParseError):
        parse_matrix_file("entails P Q\n")


# ---------------------------------------------------------------------------
# K3 semantics: P or not P is not a tautology
# ---------------------------------------------------------------------------

def test_lem_not_tautology_k3():
    f = parse_formula("P or not P")
    assert not is_tautology(f, K3)


def test_lem_tautology_boolean():
    f = parse_formula("P or not P")
    assert is_tautology(f, BOOLEAN)


def test_evaluate_lem_k3_reaches_I():
    """P or not P can be I in K3 (when P=I)."""
    import itertools
    f = parse_formula("P or not P")
    from stele.matrix import evaluate, variables
    vals = set()
    vs = sorted(variables(f))
    for combo in itertools.product(K3.values, repeat=len(vs)):
        val = dict(zip(vs, combo))
        vals.add(evaluate(f, val, K3))
    assert "I" in vals


# ---------------------------------------------------------------------------
# LP semantics: explosion fails
# ---------------------------------------------------------------------------

def test_explosion_fails_lp():
    P = parse_formula("P")
    notP = parse_formula("not P")
    Q = parse_formula("Q")
    ok, cx = entails([P, notP], Q, LP)
    assert not ok
    assert cx is not None


def test_explosion_holds_boolean():
    P = parse_formula("P")
    notP = parse_formula("not P")
    Q = parse_formula("Q")
    ok, _ = entails([P, notP], Q, BOOLEAN)
    assert ok



# ---------------------------------------------------------------------------
# CLI dispatch: cmd_check dispatches by logic.semantics
# ---------------------------------------------------------------------------

def test_cmd_check_k3_tautology_no(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("tautology? P or not P\n")
    rc = cmd_check(str(p), "K3")
    assert rc == 0
    out = capsys.readouterr().out
    assert "no" in out


def test_cmd_check_boolean_tautology_yes(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("tautology? P or not P\n")
    rc = cmd_check(str(p), "boolean")
    assert rc == 0
    out = capsys.readouterr().out
    assert "yes" in out


def test_cmd_check_lp_explosion_no_with_counterexample(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("entails P, not P |- Q\n")
    rc = cmd_check(str(p), "LP")
    assert rc == 0
    out = capsys.readouterr().out
    assert "no" in out
    assert "counterexample" in out


def test_cmd_check_evaluate_output(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("evaluate P or not P\n")
    rc = cmd_check(str(p), "K3")
    assert rc == 0
    out = capsys.readouterr().out
    assert "=>" in out
    # K3: reachable values include I and T
    assert "I" in out
    assert "T" in out


def test_cmd_check_evaluate_boolean(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("evaluate P or not P\n")
    rc = cmd_check(str(p), "boolean")
    assert rc == 0
    out = capsys.readouterr().out
    # Boolean: only T (P or not P is always T)
    assert "T" in out
    assert "I" not in out


def test_cmd_check_entails_yes(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("entails P -> Q, P |- Q\n")
    rc = cmd_check(str(p), "K3")
    assert rc == 0
    out = capsys.readouterr().out
    assert "yes" in out


def test_cmd_check_parse_error_returns_1(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("bad directive here\n")
    rc = cmd_check(str(p), "K3")
    assert rc == 1


def test_cmd_check_unknown_logic_returns_1(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("tautology? P\n")
    rc = cmd_check(str(p), "nonexistent_logic")
    assert rc == 1


# ---------------------------------------------------------------------------
# Proof mode is unaffected by matrix logic registration
# ---------------------------------------------------------------------------

def test_proof_mode_unchanged(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("theorem simple:\n  assume h: P\n  conclude P by h\n")
    rc = cmd_check(str(p), "intuitionistic_prop")
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK Proof verified" in out


def test_proof_mode_no_logic_flag(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("theorem simple:\n  assume h: P\n  conclude P by h\n")
    rc = cmd_check(str(p), None)
    assert rc == 0


def test_proof_mode_classical_still_works(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("theorem dne_check:\n  assume h: not not P\n  have h2: P by dne h\n  conclude P by h2\n")
    rc = cmd_check(str(p), "classical_prop")
    assert rc == 0
