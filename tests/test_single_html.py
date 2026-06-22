"""Tests for the single-file HTML distribution.

All tests run without Pyodide, a browser, or internet access.
The build script is executed (in a temp dir) to generate a test stele.html,
then structural invariants are verified on the result.
"""
import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO   = Path(__file__).resolve().parent.parent
TOOLS  = REPO / "tools"
SITE   = REPO / "site"
BUILD_SCRIPT    = TOOLS / "build_single_html.py"
TEMPLATE_HTML   = SITE / "single_file_template.html"
INLINE_JS       = SITE / "assets" / "stele-inline.js"
RELEASE_WF      = REPO / ".github" / "workflows" / "release.yml"
PKG_REQS        = REPO / "packaging" / "requirements-packaging.txt"
PKG_BUILD       = REPO / "packaging" / "build_app.py"
GITIGNORE       = REPO / ".gitignore"

PY = sys.executable


# ── Build script source checks ────────────────────────────────────────────────

class TestBuildScriptSource:
    def _src(self):
        return BUILD_SCRIPT.read_text(encoding="utf-8")

    def test_build_script_exists(self):
        assert BUILD_SCRIPT.exists(), "tools/build_single_html.py not found"

    def test_build_script_is_valid_python(self):
        ast.parse(self._src())

    def test_template_exists(self):
        assert TEMPLATE_HTML.exists(), "site/single_file_template.html not found"

    def test_inline_js_exists(self):
        assert INLINE_JS.exists(), "site/assets/stele-inline.js not found"

    def test_script_references_template(self):
        src = self._src()
        assert "single_file_template.html" in src

    def test_script_embeds_zip_as_b64(self):
        src = self._src()
        assert "base64" in src

    def test_script_excludes_stele_ml(self):
        assert "stele_ml" in self._src()

    def test_script_excludes_stele_lean(self):
        assert "stele_lean" in self._src()

    def test_script_excludes_eval(self):
        assert '"eval"' in self._src() or "'eval'" in self._src()

    def test_script_has_pyodide_local_option(self):
        src = self._src()
        assert "pyodide-local" in src or "pyodide_local" in src

    def test_script_has_offline_disclaimer(self):
        src = self._src()
        assert "offline" in src.lower() or "out of scope" in src.lower()

    def test_script_documents_offline_bundle_future(self):
        src = self._src()
        # Must explicitly document that full offline bundle is v1 out-of-scope
        assert "v1" in src or "out of scope" in src.lower()

    def test_no_pyinstaller_import(self):
        src = self._src()
        assert "PyInstaller" not in src
        assert "pyinstaller" not in src


# ── Template checks ───────────────────────────────────────────────────────────

class TestSingleFileTemplate:
    def _html(self):
        return TEMPLATE_HTML.read_text(encoding="utf-8")

    def test_has_css_placeholder(self):
        assert "<!-- STELE:CSS -->" in self._html()

    def test_has_zip_b64_placeholder(self):
        assert "<!-- STELE:ZIP_B64 -->" in self._html()

    def test_has_js_glue_placeholder(self):
        assert "<!-- STELE:JS_GLUE -->" in self._html()

    def test_has_version_placeholder(self):
        assert "[[STELE_VERSION]]" in self._html()

    def test_has_required_panel_ids(self):
        html = self._html()
        required = [
            "proof-input", "logic-select", "btn-check", "check-result",
            "btn-diagnose", "diag-result",
            "btn-graph", "graph-dot",
            "btn-soundness", "soundness-result",
            "btn-lattice", "lattice-result", "lattice-input",
            "examples-grid",
        ]
        for eid in required:
            assert f'id="{eid}"' in html, f"template missing id='{eid}'"

    def test_has_file_distribution_notice(self):
        html = self._html()
        assert any(phrase in html.lower() for phrase in
                   ("single-file", "cdn", "file://", "internet")), \
            "template should mention CDN/file:// caveats"

    def test_no_backend_api(self):
        assert "/api/" not in self._html()

    def test_no_npm_or_react(self):
        html = self._html()
        for banned in ("node_modules", "import React", "@angular", "import Vue"):
            assert banned not in html


# ── Inline JS checks ──────────────────────────────────────────────────────────

class TestInlineJs:
    def _js(self):
        return INLINE_JS.read_text(encoding="utf-8")

    def test_reads_embedded_zip(self):
        js = self._js()
        assert "__steleZipB64" in js, "inline JS must read window.__steleZipB64"

    def test_decodes_base64(self):
        js = self._js()
        assert "atob" in js, "inline JS must decode base64 with atob()"

    def test_uses_unpackArchive(self):
        assert "unpackArchive" in self._js()

    def test_imports_stele_browser(self):
        assert "stele.browser" in self._js()

    def test_no_fetch_stele_zip(self):
        js = self._js()
        assert "stele_source.zip" not in js, \
            "inline JS must not fetch stele_source.zip (uses embedded b64)"

    def test_no_api_calls(self):
        assert "/api/" not in self._js()

    def test_no_npm_require(self):
        assert "require(" not in self._js()

    def test_mentions_loadPyodide(self):
        assert "loadPyodide" in self._js()

    def test_is_valid_js_structure(self):
        js = self._js()
        assert "function" in js or "=>" in js
        assert "DOMContentLoaded" in js


# ── Generated HTML (build integration test) ───────────────────────────────────

class TestGeneratedHtml:
    """Run the build script and verify the output HTML."""

    def _build(self, tmp_path):
        """Run build_single_html.py into a temp directory."""
        output = tmp_path / "stele.html"
        result = subprocess.run(
            [PY, str(BUILD_SCRIPT), "--output", str(output)],
            capture_output=True, text=True, timeout=120,
        )
        return output, result

    def test_build_script_runs_successfully(self, tmp_path):
        _, result = self._build(tmp_path)
        assert result.returncode == 0, \
            f"build_single_html.py failed:\n{result.stdout}\n{result.stderr}"

    def test_output_file_created(self, tmp_path):
        output, _ = self._build(tmp_path)
        assert output.exists(), "dist/stele.html was not created"

    def test_output_is_single_file(self, tmp_path):
        output, _ = self._build(tmp_path)
        files = list(tmp_path.iterdir())
        html_files = [f for f in files if f.suffix == ".html"]
        assert len(html_files) == 1, f"Expected exactly 1 HTML file; got {[f.name for f in html_files]}"

    def test_generated_html_has_loadPyodide(self, tmp_path):
        output, _ = self._build(tmp_path)
        assert "loadPyodide" in output.read_text(encoding="utf-8")

    def test_generated_html_has_embedded_zip(self, tmp_path):
        output, _ = self._build(tmp_path)
        html = output.read_text(encoding="utf-8")
        assert "window.__steleZipB64" in html, "generated HTML must embed source zip"
        assert len(html) > 100_000, "generated HTML seems too small — zip may not be embedded"

    def test_generated_html_no_api_calls(self, tmp_path):
        output, _ = self._build(tmp_path)
        assert "/api/" not in output.read_text(encoding="utf-8")

    def test_generated_html_no_stele_ml(self, tmp_path):
        output, _ = self._build(tmp_path)
        html = output.read_text(encoding="utf-8")
        # stele_ml should not appear in script body (only possibly in excluded list comment)
        # We check it doesn't appear in the embedded zip content as a module path
        assert "stele_ml/" not in html

    def test_generated_html_no_stele_lean(self, tmp_path):
        output, _ = self._build(tmp_path)
        assert "stele_lean/" not in output.read_text(encoding="utf-8")

    def test_generated_html_has_local_notice(self, tmp_path):
        output, _ = self._build(tmp_path)
        html = output.read_text(encoding="utf-8").lower()
        assert any(phrase in html for phrase in ("local", "no data", "no backend", "wasm")), \
            "generated HTML should mention local/no-backend execution"

    def test_generated_html_has_proof_editor(self, tmp_path):
        output, _ = self._build(tmp_path)
        assert "proof-input" in output.read_text(encoding="utf-8")

    def test_generated_html_has_css_inlined(self, tmp_path):
        output, _ = self._build(tmp_path)
        html = output.read_text(encoding="utf-8")
        assert "<style>" in html, "CSS should be inlined"
        assert "stele_site.css" not in html, "should not reference external CSS file"

    def test_generated_html_has_js_inlined(self, tmp_path):
        output, _ = self._build(tmp_path)
        html = output.read_text(encoding="utf-8")
        assert "<script>" in html, "JS should be inlined"
        # Must not have an external <script src="..."> pointing to a local JS file
        import re as _re
        ext_scripts = _re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
        local_scripts = [s for s in ext_scripts if not s.startswith("http")]
        assert not local_scripts, \
            f"generated HTML should not reference local JS files via src=: {local_scripts}"

    def test_no_sibling_assets_needed(self, tmp_path):
        """Generated HTML must not reference local sibling files (only CDN URLs)."""
        output, _ = self._build(tmp_path)
        html = output.read_text(encoding="utf-8")
        # Should not have src="./..." or href="./..." pointing to sibling files
        # (CDN references like https:// are fine)
        import re
        local_refs = re.findall(r'(?:src|href)=["\'](?!\s*https?://)([^"\'#]+)["\']', html)
        # Filter out empty, anchors, and data URIs
        problem_refs = [r for r in local_refs
                        if r and not r.startswith("#") and not r.startswith("data:")]
        assert not problem_refs, \
            f"generated HTML references local sibling files: {problem_refs}"

    def test_manifest_created(self, tmp_path):
        self._build(tmp_path)
        manifest_path = tmp_path / "stele_html_manifest.json"
        assert manifest_path.exists(), "stele_html_manifest.json not created"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "source_files" in manifest
        assert len(manifest["source_files"]) > 10
        assert "pyodide_version" in manifest
        assert "build_date" in manifest

    def test_manifest_excludes_ml_lean(self, tmp_path):
        self._build(tmp_path)
        manifest = json.loads(
            (tmp_path / "stele_html_manifest.json").read_text(encoding="utf-8")
        )
        excluded = manifest.get("excluded", [])
        assert "stele_ml" in excluded
        assert "stele_lean" in excluded
        for f in manifest["source_files"]:
            assert not f.startswith("stele_ml/"), f"stele_ml in bundle: {f}"
            assert not f.startswith("stele_lean/"), f"stele_lean in bundle: {f}"


# ── Release workflow ──────────────────────────────────────────────────────────

class TestReleaseWorkflow:
    def _yml(self):
        return RELEASE_WF.read_text(encoding="utf-8")

    def test_release_workflow_exists(self):
        assert RELEASE_WF.exists()

    def test_has_build_html_job(self):
        yml = self._yml()
        assert "build-html" in yml or "build_html" in yml or "stele.html" in yml, \
            "release.yml should include a stele.html build job"

    def test_has_upload_artifact_v4(self):
        assert "upload-artifact@v4" in self._yml()

    def test_has_exe_build_step(self):
        yml = self._yml()
        assert "build_app.py" in yml or "packaging" in yml

    def test_runs_pytest(self):
        assert "pytest" in self._yml()

    def test_html_artifact_uploaded(self):
        yml = self._yml()
        assert "stele.html" in yml

    def test_no_commit_dist(self):
        yml = self._yml()
        assert "git commit" not in yml, "release workflow should not commit generated artifacts"


# ── Packaging invariants ──────────────────────────────────────────────────────

class TestPackagingInvariants:
    def test_pyinstaller_not_in_core_requirements(self):
        """PyInstaller must only be in packaging/requirements-packaging.txt."""
        for req_file in ["requirements.txt", "requirements-dev.txt"]:
            path = REPO / req_file
            if path.exists():
                txt = path.read_text(encoding="utf-8").lower()
                assert "pyinstaller" not in txt, \
                    f"PyInstaller should not appear in {req_file}"

    def test_pyinstaller_in_packaging_requirements(self):
        assert PKG_REQS.exists()
        assert "pyinstaller" in PKG_REQS.read_text(encoding="utf-8").lower()

    def test_build_app_is_valid_python(self):
        ast.parse(PKG_BUILD.read_text(encoding="utf-8"))

    def test_packaging_build_does_not_import_pyinstaller(self):
        src = PKG_BUILD.read_text(encoding="utf-8")
        assert "import PyInstaller" not in src
        assert "from PyInstaller" not in src

    def test_smoke_app_is_valid_python(self):
        smoke = REPO / "packaging" / "smoke_app.py"
        assert smoke.exists()
        ast.parse(smoke.read_text(encoding="utf-8"))

    def test_spec_file_has_webapp_assets(self):
        spec = REPO / "packaging" / "SteleStudio.spec"
        if spec.exists():
            content = spec.read_text(encoding="utf-8")
            assert "webapp" in content, "spec file should include webapp assets"

    def test_gitignore_covers_dist(self):
        gi = GITIGNORE.read_text(encoding="utf-8")
        assert "dist/" in gi or "dist" in gi

    def test_gitignore_covers_build(self):
        gi = GITIGNORE.read_text(encoding="utf-8")
        assert "build/" in gi or "build" in gi

    def test_gitignore_mentions_pyodide_local(self):
        gi = GITIGNORE.read_text(encoding="utf-8")
        assert "pyodide" in gi.lower(), \
            ".gitignore should note local Pyodide asset directories"
