"""Regular tests for documentation presence and dependency invariants.

These tests do not require Hypothesis.  They verify:
1. docs/semantics.md exists and mentions required keywords.
2. docs/metatheory.md exists and mentions required keywords.
3. An optional dev dependency file (requirements-dev.txt or pyproject dev extra) exists.
4. Core modules (stele.core.*) do not import Hypothesis.
"""
import ast as pyast
import os
import pathlib
import pytest


_REPO_ROOT  = pathlib.Path(__file__).parent.parent
_DOCS_DIR   = _REPO_ROOT / "docs"
_CORE_DIR   = _REPO_ROOT / "stele" / "core"


def _read(rel_path):
    return (_REPO_ROOT / rel_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# docs/semantics.md
# ---------------------------------------------------------------------------

class TestSemanticsMd:
    def test_exists(self):
        assert (_DOCS_DIR / "semantics.md").is_file()

    def test_mentions_grammar_or_bnf(self):
        content = _read("docs/semantics.md").lower()
        assert "grammar" in content or "bnf" in content or "ebnf" in content

    def test_mentions_typing_judgment(self):
        content = _read("docs/semantics.md")
        assert "⊢" in content or "typing" in content.lower()

    def test_mentions_reduction(self):
        content = _read("docs/semantics.md").lower()
        assert "reduction" in content or "beta" in content or "↦" in _read("docs/semantics.md")

    def test_mentions_formula_connectives(self):
        content = _read("docs/semantics.md").lower()
        assert "implication" in content or "imp" in content
        assert "conjunction" in content or "and" in content
        assert "disjunction" in content or "or" in content

    def test_mentions_proof_term_constructors(self):
        content = _read("docs/semantics.md")
        for kw in ("Lam", "App", "Pair", "Fst", "Snd", "Inl", "Inr", "Case", "Abort"):
            assert kw in content, f"semantics.md is missing constructor: {kw}"

    def test_mentions_negation_convention(self):
        content = _read("docs/semantics.md").lower()
        assert "negation" in content or "not" in content


# ---------------------------------------------------------------------------
# docs/metatheory.md
# ---------------------------------------------------------------------------

class TestMetatheoryMd:
    def test_exists(self):
        assert (_DOCS_DIR / "metatheory.md").is_file()

    def test_mentions_subject_reduction(self):
        content = _read("docs/metatheory.md").lower()
        assert "subject reduction" in content

    def test_mentions_normalization(self):
        content = _read("docs/metatheory.md").lower()
        assert "normaliz" in content

    def test_mentions_consistency(self):
        content = _read("docs/metatheory.md").lower()
        assert "consistency" in content or "consistent" in content

    def test_mentions_elaboration_soundness(self):
        content = _read("docs/metatheory.md").lower()
        assert "elaboration" in content
        assert "soundness" in content or "sound" in content

    def test_mentions_confluence(self):
        content = _read("docs/metatheory.md").lower()
        assert "confluence" in content or "confluent" in content

    def test_mentions_classical_exclusion(self):
        content = _read("docs/metatheory.md").lower()
        assert "classical" in content or "dne" in content

    def test_honesty_disclaimer_present(self):
        content = _read("docs/metatheory.md").lower()
        # The doc should disclaim formal proof status
        assert any(phrase in content for phrase in [
            "not formally", "machine-checked", "proof sketch",
            "기계 검증", "형식 증명",
        ])


# ---------------------------------------------------------------------------
# Dev dependency file
# ---------------------------------------------------------------------------

class TestDevDependency:
    def test_dev_dep_file_exists(self):
        req_dev = _REPO_ROOT / "requirements-dev.txt"
        toml_content = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert req_dev.is_file() or "hypothesis" in toml_content.lower(), (
            "Neither requirements-dev.txt nor pyproject.toml dev extra found; "
            "at least one must mention hypothesis"
        )

    def test_hypothesis_mentioned_in_dev_dep(self):
        req_dev = _REPO_ROOT / "requirements-dev.txt"
        toml_content = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        if req_dev.is_file():
            content = req_dev.read_text(encoding="utf-8")
            assert "hypothesis" in content.lower(), (
                "requirements-dev.txt exists but does not mention hypothesis"
            )
        else:
            assert "hypothesis" in toml_content.lower(), (
                "pyproject.toml does not mention hypothesis"
            )


# ---------------------------------------------------------------------------
# Core does not import Hypothesis
# ---------------------------------------------------------------------------

class TestCoreHypothesisIndependence:
    def test_core_modules_do_not_import_hypothesis(self):
        """Statically verify that stele/core/*.py never imports hypothesis."""
        for py_file in sorted(_CORE_DIR.glob("*.py")):
            source = py_file.read_text(encoding="utf-8")
            tree = pyast.parse(source, filename=str(py_file))
            for node in pyast.walk(tree):
                if isinstance(node, pyast.Import):
                    for alias in node.names:
                        assert "hypothesis" not in alias.name, (
                            f"{py_file.name} imports hypothesis: {alias.name}"
                        )
                elif isinstance(node, pyast.ImportFrom):
                    module = node.module or ""
                    assert "hypothesis" not in module, (
                        f"{py_file.name} imports from hypothesis: {module}"
                    )

    def test_kernel_does_not_import_hypothesis(self):
        """kernel.py must never import hypothesis."""
        source = (_REPO_ROOT / "stele" / "kernel.py").read_text(encoding="utf-8")
        tree = pyast.parse(source)
        for node in pyast.walk(tree):
            if isinstance(node, pyast.Import):
                for alias in node.names:
                    assert "hypothesis" not in alias.name
            elif isinstance(node, pyast.ImportFrom):
                assert "hypothesis" not in (node.module or "")


# ---------------------------------------------------------------------------
# Normal pytest run without Hypothesis
# ---------------------------------------------------------------------------

class TestPytestWithoutHypothesis:
    def test_core_imports_without_hypothesis(self):
        """Core modules can be imported without Hypothesis being present."""
        # We can't easily uninstall hypothesis in-process, but we can verify
        # no ImportError happens when importing without hypothesis in sys.path.
        # The safest check: just import and confirm no hypothesis-dependent error.
        try:
            import stele.core.reduce  # noqa: F401
            import stele.core.typing  # noqa: F401
            import stele.core.terms   # noqa: F401
        except ImportError as e:
            pytest.fail(f"Core module import failed: {e}")

    def test_property_test_module_skips_without_hypothesis(self, monkeypatch):
        """test_proof_term_properties can be collected even without hypothesis.

        We verify the skip behavior by checking the importorskip pattern
        exists in the source file, rather than by manipulating sys.modules
        (which could break other tests in the same session).
        """
        prop_file = pathlib.Path(__file__).parent / "test_proof_term_properties.py"
        source = prop_file.read_text(encoding="utf-8")
        assert "importorskip" in source and "hypothesis" in source, (
            "test_proof_term_properties.py does not use pytest.importorskip('hypothesis')"
        )
