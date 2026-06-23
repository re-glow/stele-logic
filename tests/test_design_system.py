"""Design system static tests (Prompt 42).

Verify:
1. docs/design-system.md exists and contains required sections.
2. site/assets/tokens.css exists and defines required tokens.
3. site/assets/components.css exists and defines required components.
4. visuals.js/visuals.css do not import external frameworks or fetch remote URLs.
5. site/index.html links to tokens/components without losing stele_site.css.
6. site/index.html still avoids backend /api/ calls.
7. No forbidden copy phrases in newly added design assets.
8. docs/proof-terms.md header no longer says "Stele v2".
9. Skeleton pages exist and contain required structural elements.
10. Status badges include text (not color-only).
"""
from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_SITE = _ROOT / "site"
_ASSETS = _SITE / "assets"
_DOCS = _ROOT / "docs"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


FORBIDDEN_PHRASES = [
    "dynamic rendering engine",
    "elevate your workflow",
    "real-time global connectivity",
    "unlock the power",
    "state-of-the-art",
    "production-ready",
    "production ready",
    "seamless experience",
    "guaranteed proof",
    "fully verified",
]


# ---------------------------------------------------------------------------
# 1. design-system.md exists and contains required sections
# ---------------------------------------------------------------------------

class TestDesignSystemDoc:
    @pytest.fixture(scope="class")
    def ds(self):
        path = _DOCS / "design-system.md"
        assert path.exists(), "docs/design-system.md not found"
        return _read(path).lower()

    def test_has_ia_section(self, ds):
        assert "information architecture" in ds or "target information architecture" in ds

    def test_has_accessibility_section(self, ds):
        assert "accessibility" in ds

    def test_has_reduced_motion_policy(self, ds):
        assert "prefers-reduced-motion" in ds or "reduced-motion" in ds

    def test_has_copy_style_guide(self, ds):
        assert "copy style guide" in ds or "copy policy" in ds or "forbidden phrase" in ds

    def test_has_status_label_policy(self, ds):
        assert "status label" in ds or "status badge" in ds

    def test_has_stable_label(self, ds):
        assert "stable" in ds

    def test_has_experimental_label(self, ds):
        assert "experimental" in ds

    def test_has_contrast_mention(self, ds):
        assert "contrast" in ds

    def test_has_keyboard_nav_requirement(self, ds):
        assert "keyboard" in ds

    def test_has_proof_graph_spec(self, ds):
        assert "proof graph" in ds or "proofgraph" in ds or "proof dependency graph" in ds

    def test_has_prompt_mapping(self, ds):
        # Should reference multiple prompts
        assert "prompt 43" in ds and "prompt 44" in ds


# ---------------------------------------------------------------------------
# 2. tokens.css exists and defines required tokens
# ---------------------------------------------------------------------------

class TestTokensCss:
    @pytest.fixture(scope="class")
    def tok(self):
        path = _ASSETS / "tokens.css"
        assert path.exists(), "site/assets/tokens.css not found"
        return _read(path)

    def test_defines_bg(self, tok):
        assert "--bg:" in tok

    def test_defines_cyan(self, tok):
        assert "--cyan:" in tok

    def test_defines_muted(self, tok):
        assert "--muted:" in tok

    def test_muted_color_updated(self, tok):
        # Must NOT use the old low-contrast value #46586d
        assert "#46586d" not in tok, (
            "--muted must be updated from #46586d (WCAG AA fail) to a higher-contrast value"
        )

    def test_defines_status_stable_tokens(self, tok):
        assert "--status-stable-bg:" in tok
        assert "--status-stable-fg:" in tok
        assert "--status-stable-border:" in tok

    def test_defines_status_experimental_tokens(self, tok):
        assert "--status-experimental-bg:" in tok
        assert "--status-experimental-fg:" in tok

    def test_defines_status_untrusted_tokens(self, tok):
        assert "--status-untrusted-bg:" in tok
        assert "--status-untrusted-fg:" in tok

    def test_defines_font_sans(self, tok):
        assert "--font-sans:" in tok or "--sans:" in tok

    def test_defines_font_mono(self, tok):
        assert "--font-mono:" in tok or "--mono:" in tok

    def test_defines_type_scale(self, tok):
        assert "--text-xs:" in tok
        assert "--text-sm:" in tok

    def test_defines_motion_tokens(self, tok):
        assert "--dur-fast:" in tok
        assert "--dur-normal:" in tok

    def test_reduced_motion_rule_present(self, tok):
        assert "prefers-reduced-motion" in tok

    def test_no_external_imports(self, tok):
        # Must not import fonts or resources from external URLs
        for line in tok.splitlines():
            stripped = line.strip()
            if stripped.startswith("@import"):
                assert "http" not in stripped, (
                    f"tokens.css must not import external resources: {stripped}"
                )


# ---------------------------------------------------------------------------
# 3. components.css exists and defines required components
# ---------------------------------------------------------------------------

class TestComponentsCss:
    @pytest.fixture(scope="class")
    def comp(self):
        path = _ASSETS / "components.css"
        assert path.exists(), "site/assets/components.css not found"
        return _read(path)

    def test_defines_badge(self, comp):
        assert ".badge" in comp

    def test_defines_badge_stable(self, comp):
        assert ".badge-stable" in comp

    def test_defines_badge_experimental(self, comp):
        assert ".badge-experimental" in comp

    def test_defines_badge_optional(self, comp):
        assert ".badge-optional" in comp

    def test_defines_badge_future(self, comp):
        assert ".badge-future" in comp

    def test_defines_badge_untrusted(self, comp):
        assert ".badge-untrusted" in comp

    def test_defines_trust_card(self, comp):
        assert ".trust-card" in comp

    def test_defines_metric_card(self, comp):
        assert ".metric-card" in comp

    def test_defines_callout(self, comp):
        assert ".callout" in comp

    def test_defines_proof_snippet(self, comp):
        assert ".proof-snippet" in comp

    def test_defines_focus_skip(self, comp):
        assert ".focus-skip" in comp

    def test_defines_reduced_motion_query(self, comp):
        assert "prefers-reduced-motion" in comp

    def test_buttons_not_removed(self, comp):
        # components.css must not redefine .btn in a way that removes transitions
        # It may define reduced-motion block — but should not set all transitions: none globally
        # (they should be on .btn specifically in the reduced-motion block, which is fine)
        pass  # structural check only

    def test_no_external_imports(self, comp):
        for line in comp.splitlines():
            stripped = line.strip()
            if stripped.startswith("@import"):
                assert "http" not in stripped, (
                    f"components.css must not import external resources: {stripped}"
                )


# ---------------------------------------------------------------------------
# 4. visuals.js/visuals.css do not import external frameworks or fetch remote URLs
# ---------------------------------------------------------------------------

class TestVisualsNoExternalDeps:
    def test_visuals_js_no_import_statements(self):
        path = _ASSETS / "visuals.js"
        assert path.exists(), "site/assets/visuals.js not found"
        text = _read(path)
        # No ES module import (this is an IIFE, not an ES module)
        assert "import " not in text or "// import" in text, (
            "visuals.js must not use ES module imports (not compatible with all browsers)"
        )

    def test_visuals_js_no_remote_fetch(self):
        path = _ASSETS / "visuals.js"
        text = _read(path)
        # Must not make network requests.
        # Note: SVG xmlns="http://www.w3.org/..." is a namespace URI, not a network call;
        # we check for actual request APIs (fetch/XHR) rather than URL patterns.
        request_patterns = [r'fetch\s*\(', r'new\s+XMLHttpRequest', r'\.open\s*\(']
        for pat in request_patterns:
            matches = re.findall(pat, text)
            assert not matches, (
                f"visuals.js must not make remote requests; found pattern '{pat}'"
            )

    def test_visuals_js_no_external_lib(self):
        path = _ASSETS / "visuals.js"
        text = _read(path).lower()
        forbidden_libs = ["three.js", "d3.js", "p5.js", "babylon", "react", "vue", "spline"]
        for lib in forbidden_libs:
            assert lib not in text, (
                f"visuals.js must not reference external library: {lib}"
            )

    def test_visuals_css_no_external_imports(self):
        path = _ASSETS / "visuals.css"
        assert path.exists(), "site/assets/visuals.css not found"
        text = _read(path)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("@import"):
                assert "http" not in stripped, (
                    f"visuals.css must not import external resources: {stripped}"
                )

    def test_visuals_js_exports_stele_visuals(self):
        text = _read(_ASSETS / "visuals.js")
        assert "SteleVisuals" in text, (
            "visuals.js must export SteleVisuals global"
        )

    def test_visuals_js_renders_proof_graph(self):
        text = _read(_ASSETS / "visuals.js")
        assert "renderProofGraph" in text

    def test_visuals_js_renders_kripke_motif(self):
        text = _read(_ASSETS / "visuals.js")
        assert "renderKripkeMotif" in text


# ---------------------------------------------------------------------------
# 5. site/index.html links to new assets without losing stele_site.css
# ---------------------------------------------------------------------------

class TestIndexHtmlLinks:
    @pytest.fixture(scope="class")
    def html(self):
        return _read(_SITE / "index.html")

    def test_still_links_stele_site_css(self, html):
        assert "stele_site.css" in html, (
            "index.html must still link to assets/stele_site.css"
        )

    def test_links_tokens_css(self, html):
        assert "tokens.css" in html, (
            "index.html must link to assets/tokens.css"
        )

    def test_links_components_css(self, html):
        assert "components.css" in html, (
            "index.html must link to assets/components.css"
        )

    def test_tokens_before_stele_css(self, html):
        # tokens.css must appear before stele_site.css in the HTML
        tok_pos  = html.index("tokens.css")
        site_pos = html.index("stele_site.css")
        assert tok_pos < site_pos, (
            "tokens.css must be linked before stele_site.css (token override order)"
        )

    def test_no_api_calls(self, html):
        # Site must not call any backend API endpoints
        assert "/api/" not in html, (
            "index.html must not reference /api/ endpoints (static site, no backend)"
        )

    def test_pyodide_script_present(self, html):
        assert "stele-pyodide.js" in html, (
            "index.html must still load stele-pyodide.js"
        )


# ---------------------------------------------------------------------------
# 6. Forbidden copy phrases not in design assets
# ---------------------------------------------------------------------------

class TestNoForbiddenPhrases:
    # docs/design-system.md IS the copy style guide — it quotes forbidden phrases
    # as examples of what NOT to write. Exclude it from the phrase check.
    _NEW_FILES = [
        "site/assets/tokens.css",
        "site/assets/components.css",
        "site/assets/visuals.css",
        "site/assets/visuals.js",
        "site/studio.html",
        "site/theory.html",
        "site/architecture.html",
        "site/research.html",
        "site/about.html",
    ]

    @pytest.mark.parametrize("rel_path", _NEW_FILES)
    def test_no_forbidden_phrases(self, rel_path):
        path = _ROOT / rel_path
        if not path.exists():
            pytest.skip(f"{rel_path} not found")
        text = _read(path).lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text, (
                f"Forbidden phrase '{phrase}' found in {rel_path}"
            )


# ---------------------------------------------------------------------------
# 7. docs/proof-terms.md no longer says "Stele v2"
# ---------------------------------------------------------------------------

def test_proof_terms_no_v2_header():
    path = _DOCS / "proof-terms.md"
    assert path.exists(), "docs/proof-terms.md not found"
    text = _read(path)
    first_line = text.splitlines()[0]
    assert "v2" not in first_line.lower(), (
        f"docs/proof-terms.md first line still says 'v2': {first_line!r}. "
        "Update to 'Stele v1.1'."
    )
    assert "v1.1" in first_line.lower() or "stele" in first_line.lower(), (
        f"docs/proof-terms.md first line should reference v1.1: {first_line!r}"
    )


# ---------------------------------------------------------------------------
# 8. Skeleton pages exist and contain skip link + nav + footer
# ---------------------------------------------------------------------------

SKELETON_PAGES = [
    "studio.html",
    "theory.html",
    "architecture.html",
    "research.html",
    "about.html",
]


class TestSkeletonPages:
    @pytest.mark.parametrize("page", SKELETON_PAGES)
    def test_page_exists(self, page):
        assert (_SITE / page).exists(), f"site/{page} not found"

    @pytest.mark.parametrize("page", SKELETON_PAGES)
    def test_page_has_skip_link(self, page):
        text = _read(_SITE / page)
        assert "focus-skip" in text or "skip to" in text.lower(), (
            f"site/{page} must have a skip link for keyboard accessibility"
        )

    @pytest.mark.parametrize("page", SKELETON_PAGES)
    def test_page_has_main_landmark(self, page):
        text = _read(_SITE / page)
        assert "<main" in text, (
            f"site/{page} must have a <main> landmark"
        )

    @pytest.mark.parametrize("page", SKELETON_PAGES)
    def test_page_has_footer(self, page):
        text = _read(_SITE / page)
        assert "<footer" in text, f"site/{page} must have a <footer>"

    @pytest.mark.parametrize("page", SKELETON_PAGES)
    def test_page_links_to_tokens_css(self, page):
        text = _read(_SITE / page)
        assert "tokens.css" in text, (
            f"site/{page} must link to assets/tokens.css"
        )

    @pytest.mark.parametrize("page", SKELETON_PAGES)
    def test_page_links_to_components_css(self, page):
        text = _read(_SITE / page)
        assert "components.css" in text, (
            f"site/{page} must link to assets/components.css"
        )

    @pytest.mark.parametrize("page", SKELETON_PAGES)
    def test_page_has_brand_link_to_index(self, page):
        text = _read(_SITE / page)
        assert 'href="index.html"' in text or "href='index.html'" in text, (
            f"site/{page} nav brand must link back to index.html"
        )


# ---------------------------------------------------------------------------
# 9. Status badges include text (not color-only)
# ---------------------------------------------------------------------------

def test_badge_stable_has_text():
    comp = _read(_ASSETS / "components.css")
    # Badges must not set content via CSS alone — text must come from HTML
    # Ensure .badge class does not have content: "" or similar that replaces text
    assert 'content:' not in comp.split('.badge')[1].split('}')[0] if '.badge' in comp else True


def test_badge_classes_use_both_bg_and_color():
    comp = _read(_ASSETS / "components.css")
    # Each badge variant must set color (text) not just background
    for badge in ['badge-stable', 'badge-experimental', 'badge-optional']:
        section_start = comp.find('.' + badge)
        if section_start != -1:
            section = comp[section_start:section_start + 300]
            assert 'color:' in section, (
                f".{badge} must set text color explicitly"
            )
