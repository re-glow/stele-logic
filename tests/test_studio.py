"""Tests for Stele Studio: __main__ entry point, new web API helpers, static HTML."""
import json
import os
import pathlib
import sys


# ── helpers ──────────────────────────────────────────────────────────────────

WEBAPP = pathlib.Path(__file__).parent.parent / "stele" / "webapp" / "index.html"
BENCH_REPORT = pathlib.Path(__file__).parent.parent / "bench" / "reports" / "latest.json"


# ── Part A: __main__ entry point ─────────────────────────────────────────────

def test_main_build_parser_help(capsys):
    """build_parser() produces a parser whose --help exits cleanly."""
    from stele.__main__ import build_parser
    ap = build_parser()
    try:
        ap.parse_args(["--help"])
    except SystemExit as e:
        assert e.code == 0
    out = capsys.readouterr().out
    assert "Stele Studio" in out
    assert "--port" in out
    assert "--no-browser" in out


def test_main_parser_defaults():
    """Default port is 8000 and no-browser is False."""
    from stele.__main__ import build_parser
    ap = build_parser()
    args = ap.parse_args([])
    assert args.port == 8000
    assert args.no_browser is False


def test_main_parser_custom_port():
    from stele.__main__ import build_parser
    ap = build_parser()
    args = ap.parse_args(["--port", "9090"])
    assert args.port == 9090


def test_main_parser_no_browser_flag():
    from stele.__main__ import build_parser
    ap = build_parser()
    args = ap.parse_args(["--no-browser"])
    assert args.no_browser is True


def test_main_module_is_importable():
    """python -m stele loads without ImportError."""
    import stele.__main__  # noqa: F401


# ── Part B: check_source ─────────────────────────────────────────────────────

VALID_PROOF = """\
theorem chain:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
  conclude Q by h3
"""

INVALID_PROOF = """\
theorem bad:
  assume h1: P -> Q
  assume h2: R
  have h3: Q by mp h1 h2
  conclude Q by h3
"""


def test_check_source_valid():
    from stele.web import check_source
    r = check_source(VALID_PROOF, "intuitionistic_prop")
    assert r["ok"] is True
    assert r["name"] == "chain"
    assert "logic" in r


def test_check_source_invalid():
    from stele.web import check_source
    r = check_source(INVALID_PROOF, "intuitionistic_prop")
    assert r["ok"] is False
    assert "error" in r


def test_check_source_parse_error():
    from stele.web import check_source
    r = check_source("not valid stele", None)
    assert r["ok"] is False
    assert r["kind"] == "parse"


def test_check_source_classical_vs_intuitionistic():
    """dne proof passes classical, fails intuitionistic."""
    from stele.web import check_source
    src = "theorem dne_test:\n  assume h1: not not P\n  have h2: P by dne h1\n  conclude P by h2\n"
    r_cl = check_source(src, "classical_prop")
    r_in = check_source(src, "intuitionistic_prop")
    assert r_cl["ok"] is True
    assert r_in["ok"] is False


# ── Part B: diagnose_source ───────────────────────────────────────────────────

def test_diagnose_source_clean_proof():
    from stele.web import diagnose_source
    r = diagnose_source(VALID_PROOF, "intuitionistic_prop")
    assert r["ok"] is True
    assert r["diagnostics"] == []


def test_diagnose_source_invalid_has_diagnostics():
    from stele.web import diagnose_source
    r = diagnose_source(INVALID_PROOF, "intuitionistic_prop")
    assert r["ok"] is True
    assert len(r["diagnostics"]) > 0
    codes = {d["code"] for d in r["diagnostics"]}
    assert codes  # some diagnostic codes returned


def test_diagnose_source_schema():
    from stele.web import diagnose_source
    r = diagnose_source(VALID_PROOF, None)
    assert "ok" in r
    assert "diagnostics" in r
    for d in r["diagnostics"]:
        assert "code" in d
        assert "message" in d
        assert "severity" in d
        assert "line" in d


def test_diagnose_source_parse_error():
    from stele.web import diagnose_source
    r = diagnose_source("not stele source", None)
    assert r["ok"] is False
    assert r["diagnostics"] == []


# ── Part B: graph_source ──────────────────────────────────────────────────────

def test_graph_source_valid():
    from stele.web import graph_source
    r = graph_source(VALID_PROOF, "intuitionistic_prop")
    assert r["ok"] is True
    assert "nodes" in r and "edges" in r and "dot" in r
    assert r["name"] == "chain"
    labels = {n["label"] for n in r["nodes"]}
    assert "h1" in labels and "h3" in labels


def test_graph_source_schema():
    from stele.web import graph_source
    r = graph_source(VALID_PROOF, "intuitionistic_prop")
    for n in r["nodes"]:
        assert "label" in n and "kind" in n and "formula" in n
    for e in r["edges"]:
        assert "src" in e and "tgt" in e


def test_graph_source_invalid_proof_fails():
    from stele.web import graph_source
    r = graph_source(INVALID_PROOF, "intuitionistic_prop")
    assert r["ok"] is False


def test_graph_dot_is_string():
    from stele.web import graph_source
    r = graph_source(VALID_PROOF, "intuitionistic_prop")
    assert isinstance(r["dot"], str)
    assert "digraph" in r["dot"]


# ── Part B: soundness_json ────────────────────────────────────────────────────

def test_soundness_json_classical_k3():
    from stele.web import soundness_json
    r = soundness_json("classical_prop", "K3")
    assert r["ok"] is True
    assert r["logic"] == "classical_prop"
    assert r["matrix"] == "K3"
    assert len(r["rules"]) > 0
    for rule in r["rules"]:
        assert "rule" in rule
        assert rule["status"] in ("sound", "unsound", "skipped")


def test_soundness_json_missing_logic():
    from stele.web import soundness_json
    r = soundness_json("", "K3")
    assert r["ok"] is False


def test_soundness_json_unknown_matrix():
    from stele.web import soundness_json
    r = soundness_json("classical_prop", "nonexistent")
    assert r["ok"] is False
    assert "error" in r


def test_soundness_json_matrix_logic_rejected():
    from stele.web import soundness_json
    r = soundness_json("K3", "K3")
    assert r["ok"] is False


# ── Part B: lattice_json ──────────────────────────────────────────────────────

def test_lattice_json_valid_formula():
    from stele.web import lattice_json
    r = lattice_json("P or Q")
    assert r["ok"] is True
    assert r["formula"] == "P or Q"
    assert len(r["rows"]) == 3
    for row in r["rows"]:
        assert "label" in row
        assert "axioms" in row
        assert row["status"] in ("PROVABLE", "REFUTABLE", "BOTH", "INDEPENDENT")


def test_lattice_json_empty_formula():
    from stele.web import lattice_json
    r = lattice_json("")
    assert r["ok"] is False


def test_lattice_json_parse_error():
    from stele.web import lattice_json
    r = lattice_json("not a valid formula !!!")
    assert r["ok"] is False


# ── Part B: metrics_json ──────────────────────────────────────────────────────

def test_metrics_json_with_report():
    """When bench/reports/latest.json exists the response is ok=True."""
    from stele.web import metrics_json
    if not BENCH_REPORT.exists():
        import pytest; pytest.skip("no bench report available")
    r = metrics_json()
    assert r["ok"] is True
    assert "report" in r


def test_metrics_json_missing_report(tmp_path, monkeypatch):
    """When the report file does not exist, returns ok=False with hint."""
    import stele.web as web_mod
    monkeypatch.setattr(web_mod, "BENCH_REPORT", str(tmp_path / "nosuchfile.json"))
    r = web_mod.metrics_json()
    assert r["ok"] is False
    assert "error" in r
    assert "hint" in r


# ── Part C/D: static webapp ───────────────────────────────────────────────────

def test_webapp_file_exists():
    assert WEBAPP.exists(), "stele/webapp/index.html not found"


def test_webapp_studio_title():
    html = WEBAPP.read_text(encoding="utf-8")
    assert "Stele Studio" in html


def test_webapp_has_all_tabs():
    html = WEBAPP.read_text(encoding="utf-8")
    for tab_id in ("tab-verify", "tab-diagnose", "tab-graph", "tab-metrics", "tab-pluralism"):
        assert tab_id in html, f"missing tab id: {tab_id}"


def test_webapp_has_all_panels():
    html = WEBAPP.read_text(encoding="utf-8")
    for panel_id in ("panel-verify", "panel-diagnose", "panel-graph",
                     "panel-metrics", "panel-pluralism"):
        assert panel_id in html, f"missing panel id: {panel_id}"


def test_webapp_dark_theme_variables():
    html = WEBAPP.read_text(encoding="utf-8")
    assert "--bg:" in html
    assert "--cyan:" in html
    assert "--violet:" in html


def test_webapp_api_endpoints_referenced():
    html = WEBAPP.read_text(encoding="utf-8")
    for endpoint in ("/api/check", "/api/diagnose", "/api/graph",
                     "/api/soundness", "/api/lattice", "/api/metrics"):
        assert endpoint in html, f"endpoint not referenced in UI: {endpoint}"


def test_webapp_reduced_motion_css():
    html = WEBAPP.read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in html


def test_webapp_accessibility_tablist():
    html = WEBAPP.read_text(encoding="utf-8")
    assert 'role="tablist"' in html
    assert 'role="tab"' in html
    assert 'role="tabpanel"' in html
    assert 'aria-selected' in html


def test_webapp_no_external_fonts():
    html = WEBAPP.read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html
    assert "cdnjs" not in html
    assert "unpkg.com" not in html


def test_webapp_framing_text():
    html = WEBAPP.read_text(encoding="utf-8")
    assert "formal verification" in html.lower() or "Formal verification" in html


def test_webapp_no_fake_metrics():
    """Hard-coded accuracy numbers should not appear in the HTML."""
    html = WEBAPP.read_text(encoding="utf-8")
    # Ensure no hardcoded "accuracy: 99%" or similar fake values
    assert "accuracy: 99%" not in html
    assert "accuracy: 100%" not in html
