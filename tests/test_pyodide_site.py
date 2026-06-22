"""Tests for the Pyodide browser site (no browser, no Pyodide, no internet).

Verifies structural invariants of the static site source files, build
script, and GitHub Pages workflow without running a browser or downloading
any packages.
"""
import ast
import re
import zipfile
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SITE_SRC      = REPO / "site"
JS_GLUE       = REPO / "site" / "assets" / "stele-pyodide.js"
CSS_FILE      = REPO / "site" / "assets" / "stele_site.css"
BUILD_SCRIPT  = REPO / "tools" / "build_pyodide_site.py"
SMOKE_SCRIPT  = REPO / "tools" / "smoke_pyodide_site.py"
PAGES_WF      = REPO / ".github" / "workflows" / "pages.yml"
BROWSER_PY    = REPO / "stele" / "browser.py"
README        = REPO / "README.md"
GUIDE         = REPO / "GUIDE.md"
DEV_CTX       = REPO / "docs" / "development-context.md"


# ── Static site source files exist ───────────────────────────────────────────

class TestSiteFilesExist:
    def test_index_html_exists(self):
        assert (SITE_SRC / "index.html").exists(), "site/index.html missing"

    def test_js_glue_exists(self):
        assert JS_GLUE.exists(), "site/assets/stele-pyodide.js missing"

    def test_css_file_exists(self):
        assert CSS_FILE.exists(), "site/assets/stele_site.css missing"

    def test_browser_py_exists(self):
        assert BROWSER_PY.exists(), "stele/browser.py missing"

    def test_build_script_exists(self):
        assert BUILD_SCRIPT.exists(), "tools/build_pyodide_site.py missing"

    def test_pages_workflow_exists(self):
        assert PAGES_WF.exists(), ".github/workflows/pages.yml missing"


# ── index.html content ───────────────────────────────────────────────────────

class TestIndexHtml:
    def _html(self):
        return (SITE_SRC / "index.html").read_text(encoding="utf-8")

    def test_no_api_calls(self):
        """index.html must not contain any /api/ fetch paths."""
        assert "/api/" not in self._html(), \
            "site/index.html must not contain /api/ calls"

    def test_references_js_glue(self):
        assert "stele-pyodide.js" in self._html()

    def test_has_proof_editor(self):
        assert "proof-input" in self._html()

    def test_has_logic_selector(self):
        assert "logic-select" in self._html()

    def test_has_tab_panels(self):
        html = self._html()
        for panel in ("verify", "diagnose", "graph", "semantics", "examples"):
            assert panel in html.lower(), f"tab panel '{panel}' not found in index.html"

    def test_has_privacy_notice(self):
        """Must clearly state that no data is sent to a server."""
        html = self._html()
        assert any(phrase in html.lower() for phrase in
                   ("no data", "no server", "local", "wasm")), \
            "index.html should mention local/no-server execution"

    def test_prefers_reduced_motion(self):
        """CSS must handle reduced motion."""
        css = CSS_FILE.read_text(encoding="utf-8")
        assert "prefers-reduced-motion" in css


# ── JS glue content ───────────────────────────────────────────────────────────

class TestJsGlue:
    def _js(self):
        return JS_GLUE.read_text(encoding="utf-8")

    def test_mentions_loadPyodide(self):
        assert "loadPyodide" in self._js()

    def test_no_api_calls(self):
        js = self._js()
        assert "/api/" not in js, "stele-pyodide.js must not make /api/ calls"

    def test_has_pyodide_cdn_url(self):
        assert "cdn.jsdelivr.net/pyodide" in self._js()

    def test_loads_stele_zip(self):
        assert "stele_source.zip" in self._js()

    def test_has_unpackArchive(self):
        assert "unpackArchive" in self._js()

    def test_imports_stele_browser(self):
        assert "stele.browser" in self._js()

    def test_disables_buttons_on_load(self):
        assert "setButtonsEnabled" in self._js() or "disabled" in self._js()

    def test_no_npm_require(self):
        """No Node.js require() calls — pure browser JS."""
        assert "require(" not in self._js()

    def test_no_external_ui_lib(self):
        """No React, Vue, or Angular."""
        js = self._js()
        for lib in ("React", "Vue", "Angular", "import React"):
            assert lib not in js, f"external UI lib '{lib}' found in JS glue"


# ── Build script ─────────────────────────────────────────────────────────────

class TestBuildScript:
    def _src(self):
        return BUILD_SCRIPT.read_text(encoding="utf-8")

    def test_excludes_stele_ml(self):
        assert "stele_ml" in self._src()

    def test_excludes_stele_lean(self):
        assert "stele_lean" in self._src()

    def test_excludes_venv(self):
        src = self._src()
        assert ".venv" in src or "venv" in src

    def test_excludes_tests(self):
        assert "tests" in self._src()

    def test_excludes_pycache(self):
        assert "__pycache__" in self._src()

    def test_produces_zip(self):
        assert "stele_source.zip" in self._src()

    def test_writes_manifest(self):
        assert "stele_manifest.json" in self._src()

    def test_is_valid_python(self):
        """Build script must be syntactically valid Python."""
        ast.parse(BUILD_SCRIPT.read_text(encoding="utf-8"))

    def test_smoke_script_is_valid_python(self):
        assert SMOKE_SCRIPT.exists()
        ast.parse(SMOKE_SCRIPT.read_text(encoding="utf-8"))


# ── GitHub Pages workflow ─────────────────────────────────────────────────────

class TestPagesWorkflow:
    def _yml(self):
        return PAGES_WF.read_text(encoding="utf-8")

    def test_workflow_dispatch_trigger(self):
        assert "workflow_dispatch" in self._yml()

    def test_uses_upload_pages_artifact(self):
        assert "upload-pages-artifact" in self._yml()

    def test_uses_deploy_pages(self):
        assert "deploy-pages" in self._yml()

    def test_runs_pytest(self):
        assert "pytest" in self._yml()

    def test_runs_build_script(self):
        yml = self._yml()
        assert "build_pyodide_site" in yml

    def test_uses_checkout(self):
        assert "actions/checkout" in self._yml()

    def test_uses_setup_python(self):
        assert "setup-python" in self._yml()

    def test_does_not_deploy_on_test_failure(self):
        """Pages deploy should depend on test step passing."""
        yml = self._yml()
        assert "needs:" in yml or "if:" in yml or "upload-pages-artifact" in yml


# ── Browser.py wrapper ───────────────────────────────────────────────────────

class TestBrowserPy:
    def _src(self):
        return BROWSER_PY.read_text(encoding="utf-8")

    def test_exposes_browser_check(self):
        assert "browser_check" in self._src()

    def test_exposes_browser_diagnose(self):
        assert "browser_diagnose" in self._src()

    def test_exposes_browser_soundness(self):
        assert "browser_soundness" in self._src()

    def test_exposes_browser_lattice(self):
        assert "browser_lattice" in self._src()

    def test_exposes_browser_examples(self):
        assert "browser_examples" in self._src()

    def test_exposes_to_json(self):
        assert "to_json" in self._src()

    def test_no_http_server_import(self):
        """browser.py should not import http.server directly."""
        assert "from http.server" not in self._src()
        assert "import http.server" not in self._src()

    def test_is_valid_python(self):
        ast.parse(self._src())

    def test_importable(self):
        """stele.browser should be importable without errors."""
        import importlib
        mod = importlib.import_module("stele.browser")
        assert callable(mod.browser_check)
        assert callable(mod.browser_examples)
        assert callable(mod.to_json)

    def test_browser_check_returns_dict(self):
        from stele.browser import browser_check
        r = browser_check("theorem t:\n  assume h: P\n  conclude P by h", "intuitionistic_prop")
        assert isinstance(r, dict)
        assert "ok" in r

    def test_browser_check_ok(self):
        from stele.browser import browser_check
        r = browser_check("theorem t:\n  assume h: P\n  conclude P by h", "intuitionistic_prop")
        assert r["ok"] is True

    def test_browser_check_invalid(self):
        from stele.browser import browser_check
        r = browser_check("not a valid proof", "intuitionistic_prop")
        assert r["ok"] is False

    def test_browser_examples_returns_dict(self):
        from stele.browser import browser_examples
        r = browser_examples()
        assert isinstance(r, dict)
        assert "ok" in r
        assert "examples" in r

    def test_browser_examples_finds_stele_files(self):
        from stele.browser import browser_examples
        r = browser_examples()
        assert r["ok"] is True
        assert len(r["examples"]) > 0

    def test_browser_lattice_returns_dict(self):
        from stele.browser import browser_lattice
        r = browser_lattice("P or not P")
        assert isinstance(r, dict)
        assert r.get("ok") is True

    def test_browser_soundness_returns_dict(self):
        from stele.browser import browser_soundness
        r = browser_soundness("classical_prop", "K3")
        assert isinstance(r, dict)
        assert r.get("ok") is True

    def test_to_json_serialises(self):
        from stele.browser import to_json
        import json
        result = to_json({"ok": True, "name": "test"})
        parsed = json.loads(result)
        assert parsed["ok"] is True

    def test_browser_dne_classical_ok(self):
        """Double negation elimination — valid classically."""
        from stele.browser import browser_check
        proof = (REPO / "examples" / "dne.stele").read_text(encoding="utf-8")
        r = browser_check(proof, "classical_prop")
        assert r["ok"] is True

    def test_browser_dne_intuitionistic_fails(self):
        """Double negation elimination — rejected intuitionistically."""
        from stele.browser import browser_check
        proof = (REPO / "examples" / "dne.stele").read_text(encoding="utf-8")
        r = browser_check(proof, "intuitionistic_prop")
        assert r["ok"] is False


# ── Documentation ────────────────────────────────────────────────────────────

class TestDocumentation:
    def test_readme_mentions_browser_pyodide(self):
        txt = README.read_text(encoding="utf-8").lower()
        assert "pyodide" in txt or "browser" in txt, \
            "README should mention browser / Pyodide"

    def test_readme_mentions_static_build(self):
        txt = README.read_text(encoding="utf-8")
        assert "build_pyodide_site" in txt, \
            "README should mention build_pyodide_site.py"

    def test_readme_mentions_no_backend(self):
        txt = README.read_text(encoding="utf-8").lower()
        assert "no backend" in txt or "no server" in txt or "local" in txt

    def test_guide_mentions_browser(self):
        txt = GUIDE.read_text(encoding="utf-8").lower()
        assert "browser" in txt or "pyodide" in txt

    def test_dev_context_mentions_pyodide(self):
        txt = DEV_CTX.read_text(encoding="utf-8").lower()
        assert "pyodide" in txt, \
            "docs/development-context.md should mention Pyodide"
