"""Tests for rule soundness reporting and negation fixed-point directive.

Part A: rule_soundness() checks designation preservation for non-discharge rules.
Part B: cmd_soundness CLI command.
Part C: fixpoint not / liar matrix directive.
"""
import pytest
from stele.matrix import K3, LP, BOOLEAN, rule_soundness
from stele.logic import CLASSICAL, INTUITIONISTIC


# ---------------------------------------------------------------------------
# Part A: non-discharge rule soundness
# ---------------------------------------------------------------------------

def test_lem_unsound_k3():
    """lem is unsound in K3: when A=I, A or not A = I (not designated)."""
    r = rule_soundness(CLASSICAL.rules["lem"], K3)
    assert r.status == "unsound"
    assert r.counterexample is not None
    assert r.counterexample.get("A") == "I"


def test_lem_sound_boolean():
    """lem is sound in boolean: F or T = T, T or F = T, always designated."""
    r = rule_soundness(CLASSICAL.rules["lem"], BOOLEAN)
    assert r.status == "sound"
    assert r.counterexample is None


def test_lem_sound_lp():
    """lem is sound in LP: B is designated, so A or not A is always in {T, B}."""
    r = rule_soundness(CLASSICAL.rules["lem"], LP)
    assert r.status == "sound"


def test_dne_sound_k3():
    """dne is sound in K3: not not A = T only when A = T (K3 has only T designated)."""
    r = rule_soundness(CLASSICAL.rules["dne"], K3)
    assert r.status == "sound"


def test_dne_sound_lp():
    """dne is sound in LP: not not A ∈ {T,B} implies A ∈ {T,B}."""
    r = rule_soundness(CLASSICAL.rules["dne"], LP)
    assert r.status == "sound"


def test_mp_sound_k3():
    """Modus ponens preserves designation in K3 (only one designated value T)."""
    r = rule_soundness(CLASSICAL.rules["mp"], K3)
    assert r.status == "sound"


def test_mp_unsound_lp():
    """Modus ponens fails in LP: A=B, B_var=F gives A->B = B (designated), B_var not."""
    r = rule_soundness(CLASSICAL.rules["mp"], LP)
    assert r.status == "unsound"
    assert r.counterexample is not None


def test_neg_elim_sound_k3():
    """neg_elim is vacuously sound in K3: A and not A can't both be T."""
    r = rule_soundness(CLASSICAL.rules["neg_elim"], K3)
    assert r.status == "sound"


def test_neg_elim_unsound_lp():
    """neg_elim is unsound in LP: A=B gives both A and not A designated, false not."""
    r = rule_soundness(CLASSICAL.rules["neg_elim"], LP)
    assert r.status == "unsound"
    assert r.counterexample.get("A") == "B"


def test_copy_sound_all_matrices():
    for m in (K3, LP, BOOLEAN):
        r = rule_soundness(CLASSICAL.rules["copy"], m)
        assert r.status == "sound", f"copy should be sound in {m.name}"


def test_and_intro_sound_all_matrices():
    for m in (K3, LP, BOOLEAN):
        r = rule_soundness(CLASSICAL.rules["and_intro"], m)
        assert r.status == "sound"


def test_and_elim_left_sound_all_matrices():
    for m in (K3, LP, BOOLEAN):
        r = rule_soundness(CLASSICAL.rules["and_elim_left"], m)
        assert r.status == "sound"


def test_and_elim_right_sound_all_matrices():
    for m in (K3, LP, BOOLEAN):
        r = rule_soundness(CLASSICAL.rules["and_elim_right"], m)
        assert r.status == "sound"


def test_ex_falso_vacuously_sound_all_matrices():
    """ex_falso premise is BOT (always F, never designated) -- vacuously sound."""
    for m in (K3, LP, BOOLEAN):
        r = rule_soundness(CLASSICAL.rules["ex_falso"], m)
        assert r.status == "sound"


def test_or_intro_left_sound_all_matrices():
    for m in (K3, LP, BOOLEAN):
        r = rule_soundness(CLASSICAL.rules["or_intro_left"], m)
        assert r.status == "sound"


def test_or_intro_right_sound_all_matrices():
    for m in (K3, LP, BOOLEAN):
        r = rule_soundness(CLASSICAL.rules["or_intro_right"], m)
        assert r.status == "sound"


# ---------------------------------------------------------------------------
# Part A: discharge rules must be skipped in v1
# ---------------------------------------------------------------------------

def test_imp_intro_skipped():
    r = rule_soundness(CLASSICAL.rules["imp_intro"], K3)
    assert r.status == "skipped"
    assert r.reason is not None
    assert "discharge" in r.reason.lower()


def test_neg_intro_skipped():
    r = rule_soundness(CLASSICAL.rules["neg_intro"], K3)
    assert r.status == "skipped"


def test_or_elim_skipped():
    r = rule_soundness(CLASSICAL.rules["or_elim"], K3)
    assert r.status == "skipped"


def test_pbc_skipped():
    r = rule_soundness(CLASSICAL.rules["pbc"], K3)
    assert r.status == "skipped"


def test_all_rules_return_valid_status():
    for name, schema in INTUITIONISTIC.rules.items():
        r = rule_soundness(schema, K3)
        assert r.status in ("sound", "unsound", "skipped"), f"bad status for {name}"
        assert r.name == name


# ---------------------------------------------------------------------------
# Part B: soundness CLI command
# ---------------------------------------------------------------------------

def test_cmd_soundness_lem_unsound_k3(capsys):
    from stele.cli import cmd_soundness
    rc = cmd_soundness("classical_prop", "K3")
    assert rc == 0
    out = capsys.readouterr().out
    assert "lem" in out
    assert "unsound" in out


def test_cmd_soundness_lem_sound_boolean(capsys):
    from stele.cli import cmd_soundness
    rc = cmd_soundness("classical_prop", "boolean")
    assert rc == 0
    out = capsys.readouterr().out
    for line in out.splitlines():
        if "lem" in line:
            assert "unsound" not in line
            assert "sound" in line


def test_cmd_soundness_discharge_rules_skipped(capsys):
    from stele.cli import cmd_soundness
    rc = cmd_soundness("classical_prop", "K3")
    capsys.readouterr()  # consume header output from rc==0 check above
    cmd_soundness("classical_prop", "K3")
    out = capsys.readouterr().out
    for rule in ("imp_intro", "neg_intro", "or_elim", "pbc"):
        for line in out.splitlines():
            if line.strip().startswith(rule):
                assert "skipped" in line, f"expected '{rule}' skipped, got: {line!r}"


def test_cmd_soundness_intuitionistic_k3(capsys):
    from stele.cli import cmd_soundness
    rc = cmd_soundness("intuitionistic_prop", "K3")
    assert rc == 0
    out = capsys.readouterr().out
    assert "copy" in out
    # lem and pbc should not appear (not in intuitionistic)
    assert "lem" not in out
    assert "pbc" not in out


def test_cmd_soundness_bad_logic_returns_1(capsys):
    from stele.cli import cmd_soundness
    rc = cmd_soundness("nonexistent", "K3")
    assert rc == 1


def test_cmd_soundness_bad_matrix_returns_1(capsys):
    from stele.cli import cmd_soundness
    rc = cmd_soundness("classical_prop", "nonexistent")
    assert rc == 1


def test_cmd_soundness_matrix_logic_as_logic_arg_returns_1(capsys):
    """Passing a matrix logic name (K3) as --logic should fail cleanly."""
    from stele.cli import cmd_soundness
    rc = cmd_soundness("K3", "K3")
    assert rc == 1


def test_cmd_soundness_dne_sound_k3_and_lp(capsys):
    from stele.cli import cmd_soundness
    for matrix in ("K3", "LP"):
        cmd_soundness("classical_prop", matrix)
        out = capsys.readouterr().out
        for line in out.splitlines():
            if line.strip().startswith("dne"):
                assert "unsound" not in line, f"dne should be sound in {matrix}"


# ---------------------------------------------------------------------------
# Part C: fixpoint not / liar directive
# ---------------------------------------------------------------------------

def test_parse_fixpoint_not():
    from stele.parser import parse_matrix_file
    ds = parse_matrix_file("fixpoint not\n")
    assert len(ds) == 1
    assert ds[0].kind == "fixpoint"


def test_parse_liar_alias():
    from stele.parser import parse_matrix_file
    ds = parse_matrix_file("liar\n")
    assert len(ds) == 1
    assert ds[0].kind == "fixpoint"


def test_fixpoint_k3_yields_I(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("fixpoint not\n")
    rc = cmd_check(str(p), "K3")
    assert rc == 0
    out = capsys.readouterr().out
    assert "I" in out


def test_fixpoint_lp_yields_B(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("fixpoint not\n")
    rc = cmd_check(str(p), "LP")
    assert rc == 0
    out = capsys.readouterr().out
    assert "B" in out


def test_fixpoint_boolean_empty(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("fixpoint not\n")
    rc = cmd_check(str(p), "boolean")
    assert rc == 0
    out = capsys.readouterr().out
    assert "I" not in out
    assert "B" not in out
    assert "{}" in out


def test_liar_alias_via_cli(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("liar\n")
    rc = cmd_check(str(p), "LP")
    assert rc == 0
    out = capsys.readouterr().out
    assert "B" in out


def test_fixpoint_mixed_with_other_directives(tmp_path, capsys):
    from stele.cli import cmd_check
    p = tmp_path / "t.stele"
    p.write_text("tautology? P or not P\nfixpoint not\n")
    rc = cmd_check(str(p), "K3")
    assert rc == 0
    out = capsys.readouterr().out
    assert "no" in out   # tautology? returns no in K3
    assert "I" in out    # fixpoint returns I in K3
