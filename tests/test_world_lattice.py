"""Tests for world lattice demo: lattice_status helper and CLI lattice command.

The CH-style world family for a formula φ consists of three boolean worlds:
  Gamma          — boolean, no axioms  → φ is INDEPENDENT
  Gamma + φ      — boolean, axiom φ   → φ is PROVABLE
  Gamma + (¬φ)   — boolean, axiom ¬φ  → φ is REFUTABLE

This is a semantic independence pattern (toy CH-style), not real CH or
set-theoretic forcing. 'PROVABLE' means matrix-semantic entailment, not
proof search or kernel derivation.
"""
import pytest
from stele.parser import parse_formula
from stele.ast import Op
from stele.world import World, lattice_status, status, PROVABLE, REFUTABLE, INDEPENDENT


# ---------------------------------------------------------------------------
# lattice_status helper
# ---------------------------------------------------------------------------

def test_lattice_status_base_independent():
    """Base boolean world (no axioms): atom x is INDEPENDENT."""
    phi = parse_formula("x")
    results = lattice_status(phi, [World("boolean", ())])
    assert results[0][1] == INDEPENDENT


def test_lattice_status_extension_provable():
    """Boolean world with axiom x: x is PROVABLE."""
    phi = parse_formula("x")
    results = lattice_status(phi, [World("boolean", (phi,))])
    assert results[0][1] == PROVABLE


def test_lattice_status_neg_extension_refutable():
    """Boolean world with axiom not x: x is REFUTABLE."""
    phi = parse_formula("x")
    neg = Op("not", (phi,))
    results = lattice_status(phi, [World("boolean", (neg,))])
    assert results[0][1] == REFUTABLE


def test_lattice_status_ch_style_triple():
    """Full CH-style triple: INDEPENDENT → PROVABLE → REFUTABLE."""
    phi = parse_formula("x")
    neg = Op("not", (phi,))
    worlds = [
        World("boolean", ()),
        World("boolean", (phi,)),
        World("boolean", (neg,)),
    ]
    results = lattice_status(phi, worlds)
    assert results[0][1] == INDEPENDENT
    assert results[1][1] == PROVABLE
    assert results[2][1] == REFUTABLE


def test_lattice_status_returns_world_objects():
    """Return value is [(world, status_str)] with correct world references."""
    phi = parse_formula("P")
    worlds = [World("boolean", ()), World("K3", ()), World("LP", ())]
    results = lattice_status(phi, worlds)
    assert len(results) == 3
    assert results[0][0] is worlds[0]
    assert results[1][0] is worlds[1]
    assert results[2][0] is worlds[2]


def test_lattice_status_preserves_order():
    """lattice_status preserves input world order."""
    phi = parse_formula("P")
    w1, w2 = World("boolean", ()), World("boolean", (phi,))
    results = lattice_status(phi, [w1, w2])
    assert results[0][0] is w1
    assert results[1][0] is w2


def test_lattice_status_compound_formula():
    """CH-style pattern works for compound formulas like P and Q."""
    phi = parse_formula("P and Q")
    neg = Op("not", (phi,))
    worlds = [
        World("boolean", ()),
        World("boolean", (phi,)),
        World("boolean", (neg,)),
    ]
    results = lattice_status(phi, worlds)
    assert results[0][1] == INDEPENDENT
    assert results[1][1] == PROVABLE
    assert results[2][1] == REFUTABLE


def test_lattice_status_single_world():
    """lattice_status works with a single-element world list."""
    phi = parse_formula("P")
    results = lattice_status(phi, [World("boolean", ())])
    assert len(results) == 1
    assert results[0][1] == INDEPENDENT


def test_lattice_status_empty_returns_empty():
    """lattice_status of an empty world list returns []."""
    phi = parse_formula("P")
    assert lattice_status(phi, []) == []


# ---------------------------------------------------------------------------
# CLI lattice command
# ---------------------------------------------------------------------------

def test_cli_lattice_all_three_statuses(capsys):
    """lattice x shows INDEPENDENT, PROVABLE, and REFUTABLE."""
    from stele.cli import cmd_lattice
    rc = cmd_lattice("x")
    assert rc == 0
    out = capsys.readouterr().out
    assert "INDEPENDENT" in out
    assert "PROVABLE" in out
    assert "REFUTABLE" in out


def test_cli_lattice_base_gamma_independent(capsys):
    """The base Gamma line (no '+') shows INDEPENDENT."""
    from stele.cli import cmd_lattice
    cmd_lattice("x")
    out = capsys.readouterr().out
    for line in out.splitlines():
        if "Gamma" in line and "+" not in line:
            assert "INDEPENDENT" in line
            break
    else:
        pytest.fail("no Gamma base line found in output")


def test_cli_lattice_extension_lines_show_provable_and_refutable(capsys):
    """The two Gamma+ extension lines show PROVABLE and REFUTABLE."""
    from stele.cli import cmd_lattice
    cmd_lattice("x")
    out = capsys.readouterr().out
    ext_lines = [l for l in out.splitlines() if "+" in l]
    statuses = {s for l in ext_lines for s in ("PROVABLE", "REFUTABLE") if s in l}
    assert "PROVABLE" in statuses
    assert "REFUTABLE" in statuses


def test_cli_lattice_formula_in_header(capsys):
    """Header line mentions the formula being evaluated."""
    from stele.cli import cmd_lattice
    cmd_lattice("P")
    out = capsys.readouterr().out
    header = out.splitlines()[0]
    assert "P" in header


def test_cli_lattice_matrix_in_header(capsys):
    """Header line mentions the matrix used (boolean)."""
    from stele.cli import cmd_lattice
    cmd_lattice("x")
    out = capsys.readouterr().out
    assert "boolean" in out.splitlines()[0]


def test_cli_lattice_parse_error_returns_1(capsys):
    """Malformed formula returns exit code 1."""
    from stele.cli import cmd_lattice
    rc = cmd_lattice("(")
    assert rc == 1


def test_cli_lattice_compound_formula(capsys):
    """CH-style triple works for compound formula 'P and Q'."""
    from stele.cli import cmd_lattice
    rc = cmd_lattice("P and Q")
    assert rc == 0
    out = capsys.readouterr().out
    assert "INDEPENDENT" in out
    assert "PROVABLE" in out
    assert "REFUTABLE" in out


def test_cli_lattice_negation_formula(capsys):
    """CH-style triple works for formula 'not P'."""
    from stele.cli import cmd_lattice
    rc = cmd_lattice("not P")
    assert rc == 0
    out = capsys.readouterr().out
    assert "INDEPENDENT" in out
    assert "PROVABLE" in out
    assert "REFUTABLE" in out


def test_cli_lattice_three_output_worlds(capsys):
    """Output has exactly three world rows (one base + two extensions)."""
    from stele.cli import cmd_lattice
    cmd_lattice("x")
    out = capsys.readouterr().out
    # Count lines that mention "=>" (each world row has one)
    world_lines = [l for l in out.splitlines() if "=>" in l]
    assert len(world_lines) == 3
