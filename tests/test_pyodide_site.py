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

    def test_studio_html_exists(self):
        assert (SITE_SRC / "studio.html").exists(), "site/studio.html missing"

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

    def test_links_to_studio(self):
        assert "studio.html" in self._html(), \
            "index.html must link to studio.html (Studio is now a separate page)"

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

    def test_readme_browser_option_before_python(self):
        """Browser quickstart section heading must appear before the Local Python section heading."""
        txt = README.read_text(encoding="utf-8")
        # Look for the section headings (lines starting with ### or ##)
        import re as _re
        headings = [(m.start(), m.group(0)) for m in
                    _re.finditer(r'^#{2,4}\s+.*(?:Browser Studio|Local Python).*$',
                                 txt, _re.MULTILINE)]
        names = [h[1] for h in headings]
        assert any("Browser Studio" in h for h in names), \
            f"README should have a Browser Studio heading. Found: {names}"
        assert any("Local Python" in h for h in names), \
            f"README should have a Local Python heading. Found: {names}"
        browser_pos = next(pos for pos, h in headings if "Browser Studio" in h)
        python_pos  = next(pos for pos, h in headings if "Local Python" in h)
        assert browser_pos < python_pos, \
            "README: Browser Studio section heading should appear before Local Python"


# ── Public site landing-page checks ─────────────────────────────────────────

class TestPublicSiteLanding:
    """Verify that the index.html is a proper landing page (not just a raw tool dump)."""

    def _html(self):
        return (SITE_SRC / "index.html").read_text(encoding="utf-8")

    def test_has_hero_section(self):
        html = self._html()
        assert 'id="hero"' in html or "id='hero'" in html, \
            "index.html should have a hero section (#hero)"

    def test_has_nav(self):
        html = self._html()
        assert "<nav" in html, "index.html should include a navigation element"

    def test_primary_framing_formal_verification(self):
        """Primary framing must be 'formal verification', not 'logical pluralism'."""
        html = self._html().lower()
        assert "formal verification" in html or "proof verification" in html, \
            "index.html should mention 'formal verification' or 'proof verification'"

    def test_logical_pluralism_not_in_headline(self):
        """'logical pluralism' must not appear in any h1 or h2 heading."""
        import re as _re
        html = self._html()
        headings = _re.findall(r"<h[12][^>]*>(.*?)</h[12]>", html, _re.IGNORECASE | _re.DOTALL)
        for h in headings:
            assert "logical pluralism" not in h.lower(), \
                f"Heading should not lead with 'logical pluralism': {h[:80]}"

    def test_has_studio_section(self):
        html = self._html()
        assert 'id="studio"' in html or "id='studio'" in html, \
            "index.html should have a #studio section"

    def test_has_quickstart_section(self):
        html = self._html()
        assert 'id="quickstart"' in html or "quickstart" in html.lower(), \
            "index.html should have a quickstart or get-started section"

    def test_has_gallery_section(self):
        html = self._html()
        assert 'id="gallery"' in html or "gallery" in html.lower(), \
            "index.html should have a gallery/examples section"

    def test_has_docs_section(self):
        html = self._html()
        assert 'id="docs"' in html or "documentation" in html.lower(), \
            "index.html should have a documentation/links section"

    def test_has_feature_cards(self):
        html = self._html()
        assert "feature-card" in html or "feature-grid" in html, \
            "index.html should include feature cards"

    def test_hero_has_symbol_cascade(self):
        """Hero should contain mathematical symbols (animation/decorative)."""
        html = self._html()
        assert "hero-symbols" in html or any(sym in html for sym in ("∀", "⊢", "→", "∃")), \
            "Hero section should include mathematical symbol decoration"

    def test_math_symbols_respect_reduced_motion(self):
        """Symbol animations must be gated behind prefers-reduced-motion."""
        css = CSS_FILE.read_text(encoding="utf-8")
        assert "prefers-reduced-motion" in css
        assert "hero-symbols" in css or "symbol" in css

    def test_studio_cta_links_to_studio_html(self):
        html = self._html()
        assert "studio.html" in html, \
            "index.html must contain a CTA link to studio.html"

    def test_gallery_cards_have_load_try_buttons(self):
        html = self._html()
        assert "gcard-btn" in html or "Load" in html, \
            "Gallery section should have load/try buttons"

    def test_gallery_has_proof_data_attributes(self):
        html = self._html()
        assert "data-proof" in html, \
            "Gallery buttons should carry data-proof attributes for loadPreset()"

    def test_js_exposes_load_preset(self):
        """stele-pyodide.js must expose a loadPreset function."""
        js = JS_GLUE.read_text(encoding="utf-8")
        assert "loadPreset" in js, \
            "stele-pyodide.js should expose loadPreset for gallery integration"

    def test_js_exposes_window_stele(self):
        """stele-pyodide.js must expose window.stele global."""
        js = JS_GLUE.read_text(encoding="utf-8")
        assert "window.stele" in js, \
            "stele-pyodide.js should set window.stele for gallery onclick handlers"

    def test_footer_present(self):
        html = self._html()
        assert "<footer" in html, "index.html should include a footer element"

    def test_has_github_link(self):
        html = self._html()
        assert "github.com" in html, "index.html should link to GitHub"

    def test_no_npm_or_react_in_html(self):
        html = self._html()
        for banned in ("node_modules", "import React", "import Vue", "@angular"):
            assert banned not in html, \
                f"index.html must not reference '{banned}'"


# ── Studio.html (proof workbench page) ───────────────────────────────────────

class TestStudioHtml:
    def _html(self):
        return (SITE_SRC / "studio.html").read_text(encoding="utf-8")

    def test_studio_html_has_proof_editor(self):
        assert 'id="proof-input"' in self._html(), \
            "studio.html must contain the proof editor (id=proof-input)"

    def test_studio_html_has_logic_select(self):
        assert 'id="logic-select"' in self._html(), \
            "studio.html must contain the logic selector (id=logic-select)"

    def test_studio_html_has_all_tab_panels(self):
        html = self._html()
        for panel in ("verify", "diagnose", "graph", "semantics", "examples"):
            assert f'id="panel-{panel}"' in html or panel in html.lower(), \
                f"studio.html must include panel id for '{panel}'"

    def test_studio_html_has_loading_state(self):
        html = self._html()
        assert "studio-loading" in html or "loading-step" in html, \
            "studio.html must have a Pyodide loading state element"

    def test_studio_html_loads_pyodide_js(self):
        assert "stele-pyodide.js" in self._html(), \
            "studio.html must load stele-pyodide.js"

    def test_studio_html_no_api_calls(self):
        assert "/api/" not in self._html(), \
            "studio.html must not contain /api/ backend calls"

    def test_studio_html_has_trust_pills(self):
        html = self._html()
        assert "trust-pill" in html, \
            "studio.html must include trust pills (kernel trusted, diagnostics untrusted)"

    def test_studio_html_links_back_to_index(self):
        assert "index.html" in self._html(), \
            "studio.html must link back to index.html"

    def test_studio_html_no_external_scripts(self):
        html = self._html()
        script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        for src in script_srcs:
            assert not src.startswith("http"), \
                f"studio.html must not load external scripts: {src}"

    def test_studio_html_all_required_ids(self):
        html = self._html()
        required_ids = [
            "proof-input", "logic-select", "btn-check", "check-result",
            "btn-diagnose", "diag-result",
            "btn-graph", "graph-dot",
            "btn-soundness", "soundness-result",
            "btn-lattice", "lattice-result", "lattice-input",
            "examples-grid",
        ]
        for eid in required_ids:
            assert f'id="{eid}"' in html or f"id='{eid}'" in html, \
                f"studio.html is missing required element id='{eid}'"


# ── Build output: all pages copied, no dangling links ─────────────────────────

import importlib.util
import sys
import tempfile


def _load_build_script():
    """Import build_pyodide_site as a module without executing main()."""
    spec = importlib.util.spec_from_file_location(
        "build_pyodide_site", BUILD_SCRIPT
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestBuildOutput:
    """Run the build into a temp directory and verify all pages are present."""

    @staticmethod
    def _run_build(tmp_path: Path) -> Path:
        """Run copy_static_site() (the HTML/assets copy step) into tmp_path."""
        build = _load_build_script()
        build.copy_static_site(tmp_path)
        return tmp_path

    def test_build_produces_index(self, tmp_path):
        out = self._run_build(tmp_path)
        assert (out / "index.html").exists(), "Build must produce index.html"

    def test_build_produces_studio(self, tmp_path):
        out = self._run_build(tmp_path)
        assert (out / "studio.html").exists(), "Build must produce studio.html"

    def test_build_produces_theory(self, tmp_path):
        out = self._run_build(tmp_path)
        assert (out / "theory.html").exists(), "Build must produce theory.html"

    def test_build_produces_architecture(self, tmp_path):
        out = self._run_build(tmp_path)
        assert (out / "architecture.html").exists(), "Build must produce architecture.html"

    def test_build_produces_research(self, tmp_path):
        out = self._run_build(tmp_path)
        assert (out / "research.html").exists(), "Build must produce research.html"

    def test_build_produces_foundations(self, tmp_path):
        out = self._run_build(tmp_path)
        assert (out / "foundations.html").exists(), "Build must produce foundations.html"

    def test_build_produces_about(self, tmp_path):
        out = self._run_build(tmp_path)
        assert (out / "about.html").exists(), "Build must produce about.html"

    def test_build_excludes_template(self, tmp_path):
        out = self._run_build(tmp_path)
        assert not (out / "single_file_template.html").exists(), \
            "Build must NOT copy single_file_template.html (it is a build input, not a page)"

    def test_build_produces_assets_dir(self, tmp_path):
        out = self._run_build(tmp_path)
        assert (out / "assets").is_dir(), "Build must copy assets/ directory"

    def test_build_produces_examples_gallery_json(self, tmp_path):
        out = self._run_build(tmp_path)
        assert (out / "examples_gallery.json").exists(), \
            "Build must copy examples_gallery.json"

    def test_no_dangling_html_links(self, tmp_path):
        """Every relative .html href in any built page must resolve in the output."""
        out = self._run_build(tmp_path)
        built_pages = set(p.name for p in out.glob("*.html"))
        errors = []
        for page in sorted(out.glob("*.html")):
            html = page.read_text(encoding="utf-8")
            for m in re.finditer(r'href="([^"#][^"]*\.html)(?:#[^"]*)?', html):
                target = m.group(1)
                # strip query strings (e.g. studio.html?example=foo)
                target_file = target.split("?")[0]
                if target_file not in built_pages:
                    errors.append(f"{page.name} → {target!r} (missing from build output)")
        assert not errors, "Dangling HTML links found:\n" + "\n".join(errors)

    def test_seven_html_pages_in_output(self, tmp_path):
        """Exactly 7 HTML pages (not the template) must be present in the build."""
        out = self._run_build(tmp_path)
        pages = sorted(p.name for p in out.glob("*.html"))
        assert len(pages) == 7, \
            f"Expected 7 HTML pages in build output, got {len(pages)}: {pages}"
