"""Regression tests for core system invariants.

These guard properties that must never break, regardless of feature additions.
Each test is deliberately minimal and targets a single invariant.
"""
import importlib
import types
import pytest
from stele.parser import parse_formula, parse_theorem
from stele.kernel import check_theorem
from stele.logic import LOGICS
from stele.errors import ProofError


# ---------------------------------------------------------------------------
# Invariant 1: K3 implication table matches 유리학개론 pp.4–5
# (locked by test_matrix.py::test_k3_imp_table_matches_manifesto — repeat here
#  to surface the invariant explicitly in one place)
# ---------------------------------------------------------------------------

def test_k3_imp_I_F_equals_I():
    from stele.matrix import K3
    assert K3.tables["imp"][("I", "F")] == "I"


def test_k3_imp_F_I_equals_T():
    from stele.matrix import K3
    assert K3.tables["imp"][("F", "I")] == "T"


# ---------------------------------------------------------------------------
# Invariant 2: Discharge / scope soundness
# Discharged assumptions cannot be referenced outside their subproof.
# ---------------------------------------------------------------------------

def test_discharged_label_cannot_leak():
    src = """
theorem scope_check:
  suppose h1: P
    have h2: P by copy h1
  have h3: P by copy h2
  conclude P by h3
"""
    with pytest.raises(ProofError) as exc:
        check_theorem(parse_theorem(src), "classical_prop")
    assert "h2" in str(exc.value)


# ---------------------------------------------------------------------------
# Invariant 3: Classical-only rules are absent from intuitionistic_prop
# dne, lem, and pbc must each be absent from intuitionistic_prop.rules.
# ---------------------------------------------------------------------------

def test_dne_not_in_intuitionistic():
    assert "dne" not in LOGICS["intuitionistic_prop"].rules


def test_lem_not_in_intuitionistic():
    assert "lem" not in LOGICS["intuitionistic_prop"].rules


def test_pbc_not_in_intuitionistic():
    assert "pbc" not in LOGICS["intuitionistic_prop"].rules


def test_classical_rules_present():
    rules = LOGICS["classical_prop"].rules
    for rule in ("dne", "lem", "pbc"):
        assert rule in rules, f"classical rule '{rule}' missing"


# ---------------------------------------------------------------------------
# Invariant 4: Proof and matrix modes are separate — no cross-import.
# kernel.py must not import from matrix.py, and matrix.py must not import
# from kernel.py.  world.py must not import from kernel.py.
# ---------------------------------------------------------------------------

def _module_imports(module_name):
    """Return the set of stele sub-module names imported by module_name."""
    mod = importlib.import_module(module_name)
    imported = set()
    for attr in vars(mod).values():
        if isinstance(attr, types.ModuleType) and attr.__name__.startswith("stele."):
            imported.add(attr.__name__)
    # Also check __spec__ of sub-attributes for lazy imports
    src = importlib.util.find_spec(module_name)
    if src and src.origin:
        import ast as _ast
        with open(src.origin, encoding="utf-8") as f:
            tree = _ast.parse(f.read())
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.Import, _ast.ImportFrom)):
                if isinstance(node, _ast.ImportFrom) and node.module:
                    if node.module.startswith("stele.") or node.module.startswith("."):
                        # relative or absolute stele import
                        base = node.module.lstrip(".")
                        imported.add(f"stele.{base}" if not base.startswith("stele") else base)
                elif isinstance(node, _ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("stele."):
                            imported.add(alias.name)
    return imported


def test_kernel_does_not_import_matrix():
    imported = _module_imports("stele.kernel")
    assert "stele.matrix" not in imported, \
        "kernel.py must not import matrix.py (trust boundary violation)"


def test_matrix_does_not_import_kernel():
    imported = _module_imports("stele.matrix")
    assert "stele.kernel" not in imported, \
        "matrix.py must not import kernel.py (separation of proof/semantic modes)"


def test_world_does_not_import_kernel():
    imported = _module_imports("stele.world")
    assert "stele.kernel" not in imported, \
        "world.py must not import kernel.py (status() is semantic, not proof search)"


# ---------------------------------------------------------------------------
# Invariant 5: World status includes BOTH for paraconsistent LP
# ---------------------------------------------------------------------------

def test_lp_paraconsistent_world_gives_both():
    from stele.world import World, status, BOTH
    phi = parse_formula("P")
    from stele.ast import Op
    neg = Op("not", (phi,))
    w = World("LP", (phi, neg))
    assert status(phi, w) == BOTH, "LP with axioms {P, not P} must give P status BOTH"


# ---------------------------------------------------------------------------
# Invariant 6: Version file exists and is importable
# ---------------------------------------------------------------------------

def test_version_string_exists():
    from stele.__version__ import __version__
    assert isinstance(__version__, str) and len(__version__) > 0, \
        "stele.__version__.__version__ must be a non-empty string"


def test_version_exposed_on_package():
    import stele
    assert hasattr(stele, "__version__"), \
        "stele.__version__ must be accessible as stele.__version__"


# ---------------------------------------------------------------------------
# Invariant 7: Core modules do not import external runtime packages
# The trusted stele/ core must depend only on the Python standard library.
# ---------------------------------------------------------------------------

import ast as _ast
import pathlib as _pathlib

_REPO_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_CORE_MODULES = [
    "stele.ast", "stele.proof", "stele.parser",
    "stele.logic", "stele.kernel", "stele.matrix",
    "stele.world", "stele.errors",
]
_STDLIB_EXCEPTIONS = {
    # known stdlib modules that may appear in imports
    "abc", "ast", "collections", "copy", "dataclasses", "enum", "functools",
    "itertools", "json", "math", "operator", "pathlib", "re", "sys",
    "typing", "types", "io", "os", "platform", "struct", "textwrap",
    "__future__", "stele",  # stele itself is ok
}


def _third_party_imports(module_name: str):
    """Return set of top-level module names imported that are not stdlib or stele."""
    import importlib.util
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        return set()
    src = _pathlib.Path(spec.origin).read_text(encoding="utf-8")
    tree = _ast.parse(src)
    third_party = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in _STDLIB_EXCEPTIONS and not top.startswith("stele"):
                    third_party.add(top)
        elif isinstance(node, _ast.ImportFrom):
            # Relative imports (level > 0) are always within the same package — skip
            if node.level and node.level > 0:
                continue
            if node.module:
                top = node.module.split(".")[0]
                if top not in _STDLIB_EXCEPTIONS and not top.startswith("stele") and top != "":
                    third_party.add(top)
    return third_party


def test_core_modules_have_no_runtime_third_party_deps():
    for module_name in _CORE_MODULES:
        found = _third_party_imports(module_name)
        assert not found, (
            f"{module_name} imports third-party packages: {found}. "
            "Core stele modules must depend only on the standard library."
        )
