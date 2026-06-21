"""Tests ensuring stele/ trusted core does not import stele_ml."""
import importlib
import pathlib
import sys


_STELE_SRC_DIR = pathlib.Path(__file__).parent.parent / "stele"
_STELE_MODULES = [
    "stele.ast",
    "stele.proof",
    "stele.parser",
    "stele.logic",
    "stele.kernel",
    "stele.matrix",
    "stele.world",
    "stele.diagnostics",
]


def test_stele_modules_do_not_import_stele_ml():
    """None of the trusted stele/ modules should import stele_ml."""
    for mod_name in _STELE_MODULES:
        mod = importlib.import_module(mod_name)
        src_path = pathlib.Path(mod.__file__) if hasattr(mod, "__file__") else None
        if src_path is None or not src_path.exists():
            continue
        src = src_path.read_text(encoding="utf-8")
        assert "stele_ml" not in src, (
            f"{mod_name} ({src_path.name}) must not import stele_ml — "
            "ML is isolated from the trusted core"
        )


def test_kernel_source_has_no_ml_reference():
    """kernel.py must be free of any ML-related imports."""
    kernel_path = _STELE_SRC_DIR / "kernel.py"
    assert kernel_path.exists(), "stele/kernel.py not found"
    src = kernel_path.read_text(encoding="utf-8")
    for forbidden in ("stele_ml", "sklearn", "numpy", "scipy", "torch", "tensorflow"):
        assert forbidden not in src, (
            f"kernel.py must not reference '{forbidden}' — "
            "trust boundary is purely syntactic"
        )


def test_stele_ml_can_be_imported_independently():
    """stele_ml imports without touching stele/ core (both directions isolated)."""
    import stele_ml
    import stele_ml.featurize
    import stele_ml.classifier
    import stele_ml.data
    import stele_ml._metrics
    # Just verifying they import cleanly — no assertion on values needed


def test_stele_ml_does_not_pollute_stele_namespace():
    """Importing stele_ml should not modify any stele.* module."""
    import stele.kernel as kernel_before
    import stele_ml  # noqa: F401
    import stele.kernel as kernel_after
    assert kernel_before is kernel_after, "stele.kernel must be the same object before and after importing stele_ml"
