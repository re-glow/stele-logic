"""Gallery honesty tests and site onboarding structural tests.

Gallery honesty: verify that every entry in site/examples_gallery.json
matches the actual behaviour of the Stele kernel (no fake labels).

Accessibility/structure: static checks on site/index.html and related
assets that require no browser or Pyodide.
"""
import json
import re
from pathlib import Path

import pytest

REPO     = Path(__file__).resolve().parent.parent
SITE     = REPO / "site"
EXAMPLES = REPO / "examples"
GALLERY_JSON  = SITE / "examples_gallery.json"
SITE_HTML     = SITE / "index.html"
SITE_CSS      = SITE / "assets" / "stele_site.css"
SITE_JS       = SITE / "assets" / "stele-pyodide.js"


# ── Helpers ───────────────────────────────────────────────────────────────

def load_gallery():
    return json.loads(GALLERY_JSON.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════════════════
# Gallery JSON structure
# ══════════════════════════════════════════════════════════════════════════

class TestGalleryJson:
    """Structural invariants on site/examples_gallery.json."""

    def test_gallery_json_exists(self):
        assert GALLERY_JSON.exists(), "site/examples_gallery.json not found"

    def test_gallery_is_valid_json(self):
        json.loads(GALLERY_JSON.read_text(encoding="utf-8"))

    def test_gallery_is_list(self):
        data = load_gallery()
        assert isinstance(data, list), "gallery JSON must be a list"

    def test_gallery_has_minimum_entries(self):
        assert len(load_gallery()) >= 10, "gallery should have at least 10 entries"

    def test_all_required_fields_present(self):
        required = {"id", "title", "description", "file", "logic", "category", "demonstrates", "expected"}
        for entry in load_gallery():
            missing = required - set(entry.keys())
            assert not missing, f"entry '{entry.get('id')}' missing fields: {missing}"

    def test_no_empty_titles(self):
        for entry in load_gallery():
            assert entry["title"].strip(), f"entry '{entry.get('id')}' has empty title"

    def test_no_empty_descriptions(self):
        for entry in load_gallery():
            assert entry["description"].strip(), f"entry '{entry.get('id')}' has empty description"

    def test_valid_category_values(self):
        valid = {"basics", "classical", "diagnostics"}
        for entry in load_gallery():
            assert entry["category"] in valid, (
                f"entry '{entry.get('id')}' has invalid category: {entry.get('category')}"
            )

    def test_valid_expected_values(self):
        valid = {"pass", "fail", "warn"}
        for entry in load_gallery():
            assert entry["expected"] in valid, (
                f"entry '{entry.get('id')}' has invalid expected: {entry.get('expected')}"
            )

    def test_valid_logic_values(self):
        valid = {"intuitionistic_prop", "classical_prop"}
        for entry in load_gallery():
            assert entry["logic"] in valid, (
                f"entry '{entry.get('id')}' has invalid logic: {entry.get('logic')}"
            )

    def test_demonstrates_is_list(self):
        for entry in load_gallery():
            assert isinstance(entry["demonstrates"], list), (
                f"entry '{entry.get('id')}' 'demonstrates' must be a list"
            )

    def test_no_duplicate_ids(self):
        ids = [e["id"] for e in load_gallery()]
        assert len(ids) == len(set(ids)), "gallery entries must have unique ids"

    def test_classical_entries_tagged(self):
        for entry in load_gallery():
            if entry["logic"] == "classical_prop":
                assert entry["category"] == "classical", (
                    f"entry '{entry.get('id')}' uses classical_prop but category != 'classical'"
                )

    def test_classical_entries_have_logic_note(self):
        for entry in load_gallery():
            if entry["category"] == "classical":
                assert entry.get("logic_note"), (
                    f"classical entry '{entry.get('id')}' should have a logic_note"
                )


# ══════════════════════════════════════════════════════════════════════════
# Gallery honesty — actual kernel results
# ══════════════════════════════════════════════════════════════════════════

class TestGalleryHonesty:
    """Verify that every example file exists and its labeled outcome is correct."""

    def test_all_referenced_files_exist(self):
        for entry in load_gallery():
            path = EXAMPLES / entry["file"]
            assert path.exists(), (
                f"gallery entry '{entry['id']}' references missing file: {entry['file']}"
            )

    def test_pass_entries_actually_pass(self):
        from stele.browser import browser_check
        for entry in load_gallery():
            if entry["expected"] != "pass":
                continue
            src = (EXAMPLES / entry["file"]).read_text(encoding="utf-8")
            result = browser_check(src, entry["logic"])
            assert result["ok"] is True, (
                f"gallery entry '{entry['id']}' labeled 'pass' but kernel rejected it. "
                f"Logic: {entry['logic']}. Error: {result.get('error')}"
            )

    def test_fail_entries_actually_fail(self):
        from stele.browser import browser_check
        for entry in load_gallery():
            if entry["expected"] != "fail":
                continue
            src = (EXAMPLES / entry["file"]).read_text(encoding="utf-8")
            result = browser_check(src, entry["logic"])
            assert result["ok"] is False, (
                f"gallery entry '{entry['id']}' labeled 'fail' but kernel accepted it. "
                f"Logic: {entry['logic']}"
            )

    def test_warn_entries_pass_kernel(self):
        from stele.browser import browser_check
        for entry in load_gallery():
            if entry["expected"] != "warn":
                continue
            src = (EXAMPLES / entry["file"]).read_text(encoding="utf-8")
            result = browser_check(src, entry["logic"])
            assert result["ok"] is True, (
                f"gallery entry '{entry['id']}' labeled 'warn' but kernel rejected it. "
                f"Logic: {entry['logic']}. Error: {result.get('error')}"
            )

    def test_warn_entries_have_diagnostics(self):
        from stele.browser import browser_diagnose
        for entry in load_gallery():
            if entry["expected"] != "warn":
                continue
            src = (EXAMPLES / entry["file"]).read_text(encoding="utf-8")
            result = browser_diagnose(src, entry["logic"])
            diags = result.get("diagnostics", []) if result.get("ok") else []
            assert len(diags) > 0, (
                f"gallery entry '{entry['id']}' labeled 'warn' but no diagnostics produced. "
                f"Logic: {entry['logic']}"
            )

    def test_classical_entries_fail_intuitionally(self):
        from stele.browser import browser_check
        for entry in load_gallery():
            if entry.get("expected_intuitionistic") != "fail":
                continue
            src = (EXAMPLES / entry["file"]).read_text(encoding="utf-8")
            result = browser_check(src, "intuitionistic_prop")
            assert result["ok"] is False, (
                f"gallery entry '{entry['id']}' claims to fail intuitionally "
                f"but kernel accepted it under intuitionistic_prop"
            )

    def test_classical_entries_pass_classically(self):
        from stele.browser import browser_check
        for entry in load_gallery():
            if entry["category"] != "classical":
                continue
            src = (EXAMPLES / entry["file"]).read_text(encoding="utf-8")
            result = browser_check(src, "classical_prop")
            assert result["ok"] is True, (
                f"gallery entry '{entry['id']}' is in category 'classical' "
                f"but kernel rejected it under classical_prop. Error: {result.get('error')}"
            )


# ══════════════════════════════════════════════════════════════════════════
# Tutorial structure
# ══════════════════════════════════════════════════════════════════════════

class TestTutorial:
    """Verify the tutorial section exists and has required structure."""

    def _html(self):
        return SITE_HTML.read_text(encoding="utf-8")

    def test_tutorial_section_exists(self):
        assert 'id="tutorial"' in self._html(), "index.html must have id='tutorial' section"

    def test_tutorial_has_h2_heading(self):
        html = self._html()
        assert 'id="tut-heading"' in html, "tutorial must have id='tut-heading'"
        assert 'aria-labelledby="tut-heading"' in html, \
            "tutorial section must use aria-labelledby='tut-heading'"

    def test_tutorial_has_six_steps(self):
        html = self._html()
        for i in range(1, 7):
            assert f'id="tstep-{i}"' in html, f"tutorial must have step id='tstep-{i}'"

    def test_tutorial_has_six_dots(self):
        html = self._html()
        for i in range(1, 7):
            assert f'data-step="{i}"' in html, f"tutorial must have dot with data-step='{i}'"

    def test_tutorial_has_prev_next_buttons(self):
        html = self._html()
        assert 'id="tut-prev"' in html, "tutorial must have prev button id='tut-prev'"
        assert 'id="tut-next"' in html, "tutorial must have next button id='tut-next'"

    def test_tutorial_prev_has_aria_label(self):
        html = self._html()
        assert re.search(r'id="tut-prev"[^>]*aria-label=|aria-label=[^>]*id="tut-prev"', html), \
            "tut-prev button must have aria-label"

    def test_tutorial_next_has_aria_label(self):
        html = self._html()
        assert re.search(r'id="tut-next"[^>]*aria-label=|aria-label=[^>]*id="tut-next"', html), \
            "tut-next button must have aria-label"

    def test_tutorial_counter_has_aria_live(self):
        html = self._html()
        assert 'id="tut-counter"' in html
        assert re.search(r'id="tut-counter"[^>]*aria-live=|aria-live=[^>]*id="tut-counter"', html), \
            "tut-counter must have aria-live"

    def test_tutorial_has_skip_link(self):
        html = self._html()
        assert "tut-skip" in html, "tutorial must have a skip-to-Studio link with class='tut-skip'"

    def test_tutorial_step_h3_headings(self):
        html = self._html()
        assert "tstep-title" in html, "tutorial steps should use tstep-title class for headings"
        assert "<h3" in html, "tutorial steps should use h3 headings"

    def test_tutorial_nav_has_aria_label(self):
        assert 'aria-label="Tutorial navigation"' in self._html()

    def test_tutorial_load_buttons_have_data_proof(self):
        html = self._html()
        assert "tut-load-btn" in html
        assert 'data-tab="verify"' in html
        assert 'data-tab="diagnose"' in html
        assert 'data-tab="graph"' in html

    def test_tutorial_step6_has_links(self):
        html = self._html()
        assert "tstep-6" in html
        assert "tstep-final" in html.lower() or "tstep--final" in html


# ══════════════════════════════════════════════════════════════════════════
# Site accessibility static checks
# ══════════════════════════════════════════════════════════════════════════

class TestSiteAccessibility:
    """Static checks for ARIA and accessibility markers in site assets.

    Studio-specific panel IDs (proof-input, logic-select, tab panels, etc.)
    now live in studio.html — tests for those check studio.html directly.
    """

    def _html(self):
        return SITE_HTML.read_text(encoding="utf-8")

    def _studio_html(self):
        return (SITE / "studio.html").read_text(encoding="utf-8")

    def _css(self):
        return SITE_CSS.read_text(encoding="utf-8")

    def _js(self):
        return SITE_JS.read_text(encoding="utf-8")

    def test_check_result_has_aria_live(self):
        html = self._studio_html()
        assert re.search(r'id="check-result"[^>]*aria-live=', html), \
            "check-result must have aria-live (in studio.html)"

    def test_check_result_has_role_status(self):
        html = self._studio_html()
        assert 'id="check-result"' in html
        assert 'role="status"' in html

    def test_diag_result_has_aria_live(self):
        html = self._studio_html()
        assert re.search(r'id="diag-result"[^>]*aria-live=', html), \
            "diag-result must have aria-live (in studio.html)"

    def test_soundness_result_has_aria_live(self):
        html = self._studio_html()
        assert re.search(r'id="soundness-result"[^>]*aria-live=', html), \
            "soundness-result must have aria-live (in studio.html)"

    def test_lattice_result_has_aria_live(self):
        html = self._studio_html()
        assert re.search(r'id="lattice-result"[^>]*aria-live=', html), \
            "lattice-result must have aria-live (in studio.html)"

    def test_studio_loading_banner_has_aria_live(self):
        html = self._studio_html()
        assert re.search(r'id="studio-loading"[^>]*aria-live=', html), \
            "studio-loading must have aria-live (in studio.html)"

    def test_proof_editor_has_aria_label(self):
        html = self._studio_html()
        assert 'id="proof-input"' in html
        assert re.search(r'id="proof-input"[^>]*aria-label=|aria-label=[^>]*id="proof-input"',
                         html), "proof-input must have aria-label (in studio.html)"

    def test_logic_select_has_label(self):
        html = self._studio_html()
        assert 'for="logic-select"' in html or \
               re.search(r'id="logic-select"[^>]*aria-label=', html), \
            "logic-select must have a label or aria-label (in studio.html)"

    def test_gallery_section_has_aria_labelledby(self):
        html = self._html()
        assert 'id="gallery"' in html
        assert 'aria-labelledby="gallery-heading"' in html

    def test_hero_symbols_hidden_from_screen_readers(self):
        assert 'aria-hidden="true"' in self._html()
        assert 'class="hero-symbols"' in self._html()

    def test_focus_visible_defined_in_css(self):
        css = self._css()
        assert ":focus-visible" in css, "CSS must define :focus-visible focus style"

    def test_prefers_reduced_motion_in_css(self):
        assert "prefers-reduced-motion" in self._css(), \
            "CSS must include prefers-reduced-motion media query"

    def test_tab_buttons_have_role_tab(self):
        html = self._studio_html()
        assert 'role="tab"' in html, "tab buttons must have role='tab' (in studio.html)"

    def test_tab_buttons_have_aria_selected(self):
        html = self._studio_html()
        assert 'aria-selected="true"' in html
        assert 'aria-selected="false"' in html

    def test_panels_have_role_tabpanel(self):
        assert 'role="tabpanel"' in self._studio_html()

    def test_tablist_has_aria_label(self):
        assert 'aria-label="Studio panels"' in self._studio_html()

    def test_nav_has_aria_label(self):
        assert 'aria-label="Site navigation"' in self._html()

    def test_no_autofocus(self):
        assert "autofocus" not in self._html().lower(), \
            "index.html should not use autofocus (disruptive to screen readers)"

    def test_feature_icons_aria_hidden(self):
        html = self._html()
        assert 'class="feature-icon" aria-hidden="true"' in html, \
            "decorative feature-icon spans should have aria-hidden"

    def test_gallery_grid_has_aria_live(self):
        html = self._html()
        assert re.search(r'id="gallery-grid"[^>]*aria-live=', html), \
            "gallery-grid should have aria-live for dynamic content"


# ══════════════════════════════════════════════════════════════════════════
# JS gallery rendering
# ══════════════════════════════════════════════════════════════════════════

class TestGalleryJs:
    """Verify JS gallery constants are consistent with the JSON source of truth."""

    def _js(self):
        return SITE_JS.read_text(encoding="utf-8")

    def test_gallery_entries_constant_exists(self):
        assert "GALLERY_ENTRIES" in self._js(), \
            "stele-pyodide.js must define GALLERY_ENTRIES constant"

    def test_gallery_entries_has_pass_entries(self):
        assert '"pass"' in self._js() or "'pass'" in self._js()

    def test_gallery_entries_has_fail_entries(self):
        assert '"fail"' in self._js() or "'fail'" in self._js()

    def test_gallery_entries_has_warn_entries(self):
        assert '"warn"' in self._js() or "'warn'" in self._js()

    def test_gallery_entries_has_classical_entries(self):
        assert '"classical"' in self._js() or "'classical'" in self._js()

    def test_render_gallery_function_exists(self):
        assert "renderGallery" in self._js()

    def test_render_gallery_called_on_domcontentloaded(self):
        js = self._js()
        assert "renderGallery()" in js, \
            "renderGallery() must be called in DOMContentLoaded"

    def test_load_tutorial_preset_function_exists(self):
        assert "loadTutorialPreset" in self._js()

    def test_show_tutorial_step_function_exists(self):
        assert "showTutorialStep" in self._js()

    def test_gallery_json_entry_count_matches_js(self):
        gallery_json = load_gallery()
        js = self._js()
        json_count = len(gallery_json)
        # Each entry has an "id:" key
        js_id_count = js.count("id:")
        # JS has at least as many id: occurrences as gallery entries (may have more from other objects)
        assert js_id_count >= json_count, (
            f"JS GALLERY_ENTRIES appears to have fewer entries than gallery JSON ({json_count})"
        )

    def test_window_stele_exports_load_tutorial_preset(self):
        js = self._js()
        assert "loadTutorialPreset" in js
        assert 'window.stele' in js
        # loadTutorialPreset must be in the window.stele export
        stele_export_match = re.search(r'window\.stele\s*=\s*\{([^}]+)\}', js)
        if stele_export_match:
            export_body = stele_export_match.group(1)
            assert "loadTutorialPreset" in export_body, \
                "window.stele must export loadTutorialPreset"
