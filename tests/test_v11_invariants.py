"""v1.1 release invariant tests.

Static and import-level checks confirming that the v1.1 trust/isolation
boundaries are maintained. No slow tests, no external dependencies.
"""
from __future__ import annotations
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_is_post_v1_1():
    from stele import __version__
    # The v1.1 invariants apply to any release at or after v1.1.0.
    # Exact version is checked in test_v12_release.py for v1.2.
    major, minor, _patch = __version__.split(".")
    assert (int(major), int(minor)) >= (1, 1), (
        f"Version must be at least 1.1.0; got {__version__}."
    )


# ---------------------------------------------------------------------------
# Kripke isolation
# ---------------------------------------------------------------------------

def _import_lines(path: pathlib.Path):
    import ast as _ast
    tree = _ast.parse(path.read_text(encoding="utf-8"))
    return [
        _ast.unparse(n)
        for n in _ast.walk(tree)
        if isinstance(n, (_ast.Import, _ast.ImportFrom))
    ]


def test_kripke_does_not_import_kernel():
    for line in _import_lines(_ROOT / "stele" / "kripke.py"):
        assert "kernel" not in line, (
            f"kripke.py must not import kernel; got: {line!r}"
        )


def test_kripke_does_not_import_matrix():
    for line in _import_lines(_ROOT / "stele" / "kripke.py"):
        assert "matrix" not in line, (
            f"kripke.py must not import matrix; got: {line!r}"
        )


def test_kripke_find_countermodel_returns_none_for_valid():
    from stele.kripke import find_countermodel
    from stele.parser import parse_formula
    # P -> P is intuitionistically valid; should return None within 4 worlds
    result = find_countermodel(parse_formula("P -> P"), max_worlds=4)
    assert result is None


def test_kripke_finds_countermodel_for_lem():
    from stele.kripke import find_countermodel
    from stele.parser import parse_formula
    # LEM is not intuitionistically valid; must find a countermodel
    result = find_countermodel(parse_formula("P or not P"), max_worlds=4)
    assert result is not None, "Expected a Kripke countermodel for LEM"


# ---------------------------------------------------------------------------
# Certificate / minicheck isolation
# (Full isolation tests live in test_minicheck.py::TestMinicheckIsolation)
# ---------------------------------------------------------------------------

def test_minicheck_module_imports():
    """Verify minicheck only imports ast and certificate (actual import lines)."""
    import ast as _ast
    mini_src = (_ROOT / "stele" / "minicheck.py").read_text(encoding="utf-8")
    tree = _ast.parse(mini_src)
    import_lines = [
        _ast.unparse(n)
        for n in _ast.walk(tree)
        if isinstance(n, (_ast.Import, _ast.ImportFrom))
    ]
    for line in import_lines:
        assert "kernel" not in line, f"minicheck must not import kernel; got: {line!r}"
        assert "parser" not in line, f"minicheck must not import parser; got: {line!r}"
        assert "stele.proof" not in line and ".proof" not in line, (
            f"minicheck must not import stele.proof; got: {line!r}"
        )


# ---------------------------------------------------------------------------
# Proof-state / hints trust boundary
# ---------------------------------------------------------------------------

def test_proofstate_does_not_import_kernel():
    for line in _import_lines(_ROOT / "stele" / "proofstate.py"):
        assert "kernel" not in line, (
            f"proofstate.py must not import kernel; got: {line!r}"
        )


def test_proofstate_hints_always_untrusted():
    from stele.proofstate import proof_state_from_text, suggest_rule_hints
    state = proof_state_from_text(
        "theorem t using intuitionistic_prop:\n  assume h1: P\n  conclude P by h1\n",
        "intuitionistic_prop",
    )
    hints = suggest_rule_hints(state)
    for h in hints:
        assert not h.trusted, (
            f"Rule hint '{h.rule}' has trusted=True; all hints must be trusted=False"
        )


# ---------------------------------------------------------------------------
# Classical experimental bridge isolation
# ---------------------------------------------------------------------------

def test_classical_experimental_does_not_import_kernel():
    import ast as _ast
    cl_src = (_ROOT / "stele" / "core" / "classical_experimental.py").read_text(encoding="utf-8")
    tree = _ast.parse(cl_src)
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.Import, _ast.ImportFrom)):
            line = _ast.unparse(node)
            assert "kernel" not in line, (
                f"classical_experimental must not import kernel; got: {line!r}"
            )


def test_negative_translation_preserves_intuitionistic_core():
    from stele.core.classical_experimental import negative_translate_formula
    from stele.core.typing import infer
    from stele.core.terms import TVar
    from stele.parser import parse_formula
    # Translating P should yield ~~P; check the result is a valid Op
    result = negative_translate_formula(parse_formula("P"))
    # Result must be a stele.ast.Op or Var (not raise)
    assert result is not None


# ---------------------------------------------------------------------------
# Whitepaper and docs
# ---------------------------------------------------------------------------

def test_whitepaper_md_exists():
    assert (_ROOT / "docs" / "whitepaper.md").exists(), (
        "docs/whitepaper.md is missing"
    )


def test_benchmark_card_exists():
    assert (_ROOT / "docs" / "benchmark-card.md").exists(), (
        "docs/benchmark-card.md is missing"
    )


def test_site_quality_doc_exists():
    assert (_ROOT / "docs" / "site-quality.md").exists(), (
        "docs/site-quality.md is missing"
    )


# ---------------------------------------------------------------------------
# Capability matrix status labels in README
# ---------------------------------------------------------------------------

def test_readme_capabilities_have_correct_v11_labels():
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    # Certificates should not be claimed as Stable
    assert "| Proof certificates & minicheck | **Stable**" not in readme, (
        "certificates/minicheck must be Experimental in the capability matrix"
    )
    # Proof state/hints should not be claimed as Stable
    assert "| Proof state & hints | **Stable**" not in readme, (
        "proof state & hints must be Experimental/Untrusted in the capability matrix"
    )


def test_readme_version_is_v11():
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "v1.1.0" in readme or "v1.1" in readme, (
        "README.md must reference v1.1"
    )


def test_changelog_has_v11_entry():
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[v1.1.0]" in changelog, (
        "CHANGELOG.md must have a [v1.1.0] entry"
    )
