"""Browser wrappers for Pyodide / WASM deployments.

Thin shims over the same pure functions used by the local HTTP server.
Safe to import in a Pyodide context: no server startup, no webbrowser
calls, no OS filesystem assumptions beyond the virtual FS paths set up
by build_pyodide_site.py.

Return type: Python dict (JSON-serialisable).
JavaScript glue converts with to_json() or json.dumps() and JSON.parse().
"""
from __future__ import annotations

import json
import os


# ---------------------------------------------------------------------------
# Proof checking
# ---------------------------------------------------------------------------

def browser_check(proof_text: str, logic: str = "intuitionistic_prop") -> dict:
    """Verify a proof. Returns {ok, name?, logic?, error?, kind?, line?}."""
    from .web import check_source
    return check_source(proof_text, logic)


def browser_diagnose(proof_text: str, logic: str = "intuitionistic_prop") -> dict:
    """Run structural diagnostics. Returns {ok, name?, logic?, diagnostics: [...]}."""
    from .web import diagnose_source
    return diagnose_source(proof_text, logic)


def browser_graph(proof_text: str, logic: str = "intuitionistic_prop") -> dict:
    """Build proof dependency graph. Returns {ok, nodes, edges, dot, diagnostics}."""
    from .web import graph_source
    return graph_source(proof_text, logic)


# ---------------------------------------------------------------------------
# Semantic tools
# ---------------------------------------------------------------------------

def browser_soundness(logic: str = "classical_prop", matrix: str = "K3") -> dict:
    """Per-rule soundness of a proof logic against a semantic matrix."""
    from .web import soundness_json
    return soundness_json(logic, matrix)


def browser_lattice(formula: str = "P") -> dict:
    """CH-style world lattice status for a formula string."""
    from .web import lattice_json
    return lattice_json(formula)


def browser_kripke(formula: str, max_worlds: int = 3) -> dict:
    """Bounded finite Kripke countermodel search for a propositional formula.

    Returns a JSON-serialisable dict with keys:
      ok, formula, status, max_worlds, bound_note, worlds, order_pairs,
      valuation, failing_world, explanation
    """
    from .web import kripke_json
    return kripke_json(formula, max_worlds)


def browser_demos() -> dict:
    """Return matrix demo data (truth tables, LEM, explosion, liar)."""
    from .web import _demos_json
    return _demos_json()


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

def browser_examples() -> dict:
    """Return bundled example .stele files as {filename: content}.

    Searches several candidate locations so this works in both the Pyodide
    context (after unpackArchive into /home/pyodide) and a normal dev env.
    """
    _env_dir = os.environ.get("STELE_EXAMPLES_DIR", "")
    _pkg_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        _env_dir,
        os.path.join(_pkg_dir, "..", "examples"),   # normal dev / test
        "/home/pyodide/examples",                   # Pyodide after unpackArchive
        "/examples",
    ]
    for d in candidates:
        if d and os.path.isdir(d):
            out: dict[str, str] = {}
            try:
                for fn in sorted(os.listdir(d)):
                    if fn.endswith(".stele"):
                        with open(os.path.join(d, fn), encoding="utf-8") as f:
                            out[fn] = f.read()
            except OSError:
                continue
            if out:
                return {"ok": True, "examples": out}
    return {"ok": True, "examples": {}}


# ---------------------------------------------------------------------------
# JS interop helper
# ---------------------------------------------------------------------------

def to_json(d: dict) -> str:
    """Serialise a result dict to a JSON string for JS consumption."""
    return json.dumps(d)
