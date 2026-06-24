"""Static release-readiness tests for Stele v1.2.0 (Prompt 50).

Checks: version, CHANGELOG, README links, site pages, overclaim phrases,
Yurihak scope, no backend API calls, no heavy frameworks, accessibility,
research notes/provenance references.
"""
from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_SITE = _ROOT / "site"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _site_html(name: str) -> str:
    return _read(_SITE / name)


# ── 1. Version ────────────────────────────────────────────────────────────────

def test_version_is_1_2_0():
    version_file = _ROOT / "stele" / "__version__.py"
    assert version_file.exists(), "stele/__version__.py must exist"
    content = version_file.read_text(encoding="utf-8")
    assert '"1.2.0"' in content, f"Version must be 1.2.0; got: {content.strip()!r}"


# ── 2. CHANGELOG ─────────────────────────────────────────────────────────────

def test_changelog_has_v1_2_0_entry():
    changelog = _read(_ROOT / "CHANGELOG.md")
    assert "[v1.2.0]" in changelog, "CHANGELOG.md must have a [v1.2.0] entry"


def test_changelog_v1_2_entry_before_v1_1():
    changelog = _read(_ROOT / "CHANGELOG.md")
    idx_12 = changelog.find("[v1.2.0]")
    idx_11 = changelog.find("[v1.1.0]")
    assert idx_12 != -1 and idx_11 != -1, "Both v1.2.0 and v1.1.0 entries must exist"
    assert idx_12 < idx_11, "v1.2.0 entry must appear before v1.1.0 in CHANGELOG"


# ── 3. README links ───────────────────────────────────────────────────────────

def test_readme_version_heading():
    readme = _read(_ROOT / "README.md")
    assert "v1.2.0" in readme, "README.md must reference v1.2.0"


def test_readme_links_to_public_site():
    readme = _read(_ROOT / "README.md")
    assert "re-glow.github.io/stele-logic" in readme, \
        "README must link to the public GitHub Pages site"


def test_readme_links_to_studio():
    readme = _read(_ROOT / "README.md")
    assert "studio.html" in readme, "README must link to studio.html"


def test_readme_links_to_theory():
    readme = _read(_ROOT / "README.md")
    assert "theory.html" in readme, "README must link to theory.html"


def test_readme_links_to_architecture():
    readme = _read(_ROOT / "README.md")
    assert "architecture.html" in readme, "README must link to architecture.html"


def test_readme_links_to_foundations():
    readme = _read(_ROOT / "README.md")
    assert "foundations.html" in readme, "README must link to foundations.html"


def test_readme_links_to_about():
    readme = _read(_ROOT / "README.md")
    assert "about.html" in readme, "README must link to about.html"


def test_readme_links_to_whitepaper():
    readme = _read(_ROOT / "README.md")
    assert "whitepaper" in readme.lower(), "README must link to the whitepaper"


def test_readme_links_to_research_notes():
    readme = _read(_ROOT / "README.md")
    assert "research-notes" in readme, "README must link to docs/research-notes/"


def test_readme_links_to_provenance_map():
    readme = _read(_ROOT / "README.md")
    assert "provenance-map" in readme, "README must link to docs/provenance-map.md"


# ── 4. Site pages exist ───────────────────────────────────────────────────────

REQUIRED_SITE_PAGES = [
    "index.html",
    "studio.html",
    "theory.html",
    "architecture.html",
    "foundations.html",
    "about.html",
]


@pytest.mark.parametrize("page", REQUIRED_SITE_PAGES)
def test_site_page_exists(page):
    assert (_SITE / page).exists(), f"site/{page} must exist"


@pytest.mark.parametrize("page", REQUIRED_SITE_PAGES)
def test_site_page_not_empty(page):
    content = _site_html(page)
    assert len(content) > 1000, f"site/{page} must contain substantial content"


# ── 5. Navigation completeness ────────────────────────────────────────────────

@pytest.mark.parametrize("page", [p for p in REQUIRED_SITE_PAGES if p != "studio.html"])
def test_site_page_has_studio_link(page):
    html = _site_html(page)
    assert "studio.html" in html, f"site/{page} nav must link to studio.html"


def test_studio_page_links_to_theory():
    html = _site_html("studio.html")
    assert "theory.html" in html, "studio.html must link to theory.html in its nav"


@pytest.mark.parametrize("page", REQUIRED_SITE_PAGES)
def test_site_page_has_github_link(page):
    html = _site_html(page)
    assert "github.com/re-glow/stele-logic" in html, \
        f"site/{page} must include GitHub link"


# ── 6. Overclaim phrases absent ───────────────────────────────────────────────

OVERCLAIM_PHRASES = [
    "complete theorem prover",
    "stele is an ai-powered verifier",
    "stele is ai-powered",
    "stele is fully verified",
    "stele has machine-checked metatheory",
    "stele has formally verified metatheory",
    "production-ready",
    "state-of-the-art",
    "stele is production ready",
    "automatic proof search",
    "guaranteed hint",
    "large corpus",
    "stele implements yurihak",
    "proves relativism",
]


def _all_public_content() -> str:
    parts = []
    for p in REQUIRED_SITE_PAGES:
        parts.append(_site_html(p).lower())
    parts.append(_read(_ROOT / "README.md").lower())
    parts.append(_read(_ROOT / "CHANGELOG.md").lower())
    if (_ROOT / "docs" / "release-notes-v1.2.0.md").exists():
        parts.append(_read(_ROOT / "docs" / "release-notes-v1.2.0.md").lower())
    return "\n".join(parts)


@pytest.mark.parametrize("phrase", OVERCLAIM_PHRASES)
def test_no_overclaim_phrase(phrase):
    content = _all_public_content()
    assert phrase.lower() not in content, \
        f"Forbidden overclaim phrase found in public content: {phrase!r}"


# ── 7. Yurihak is not described as implemented ────────────────────────────────

def test_yurihak_not_implemented_in_foundations():
    html = _site_html("foundations.html").lower()
    assert "yurihak" in html, "foundations.html must mention Yurihak"
    assert "stele implements yurihak" not in html, \
        "foundations.html must NOT claim 'Stele implements Yurihak'"


def test_yurihak_marked_as_motivation_in_foundations():
    html = _site_html("foundations.html")
    assert re.search(r"[Mm]otivation|[Ff]uture|[Nn]ot yet", html), \
        "foundations.html must mark Yurihak as motivation or future work"


def test_about_page_yurihak_not_implemented():
    html = _site_html("about.html").lower()
    assert "yurihak" in html, "about.html must mention Yurihak"
    assert "not yet" in html or "motivation" in html or "future" in html, \
        "about.html must clarify Yurihak is not yet a formal Stele logic"


# ── 8. No backend /api/ calls in static site ─────────────────────────────────

@pytest.mark.parametrize("page", REQUIRED_SITE_PAGES)
def test_no_api_backend_calls(page):
    html = _site_html(page)
    api_calls = re.findall(r"""fetch\(['"]\/api\/""", html)
    assert not api_calls, \
        f"site/{page} must not contain fetch('/api/...) calls (static site, no backend): {api_calls}"


# ── 9. No heavy external frameworks ──────────────────────────────────────────

FORBIDDEN_FRAMEWORKS = [
    "react.js", "react.min.js", "cdn.tailwindcss", "three.js", "three.min.js",
    "spline", "framer-motion", "cdn.jsdelivr.net/npm/vue",
]


@pytest.mark.parametrize("page", REQUIRED_SITE_PAGES)
def test_no_heavy_framework(page):
    html = _site_html(page).lower()
    for fw in FORBIDDEN_FRAMEWORKS:
        assert fw not in html, \
            f"site/{page} must not load heavy framework: {fw!r}"


# ── 10. Accessibility: reduced-motion and focus styles ───────────────────────

def test_reduced_motion_in_site_css():
    css_files = list((_SITE / "assets").glob("*.css"))
    assert css_files, "site/assets/ must contain CSS files"
    all_css = "\n".join(f.read_text(encoding="utf-8") for f in css_files)
    assert "prefers-reduced-motion" in all_css, \
        "Site CSS must include @media (prefers-reduced-motion: reduce) rules"


def test_focus_visible_in_site_css():
    css_files = list((_SITE / "assets").glob("*.css"))
    all_css = "\n".join(f.read_text(encoding="utf-8") for f in css_files)
    assert "focus" in all_css.lower(), \
        "Site CSS must include focus/focus-visible styles"


def test_aria_labels_in_studio():
    html = _site_html("studio.html")
    assert "aria-" in html, "studio.html must include aria-* accessibility attributes"


# ── 11. Research notes and provenance references ─────────────────────────────

def test_research_notes_directory_exists():
    notes_dir = _ROOT / "docs" / "research-notes"
    assert notes_dir.exists() and notes_dir.is_dir(), \
        "docs/research-notes/ directory must exist"


def test_provenance_map_exists():
    assert (_ROOT / "docs" / "provenance-map.md").exists(), \
        "docs/provenance-map.md must exist"


def test_references_md_exists():
    assert (_ROOT / "docs" / "references.md").exists(), \
        "docs/references.md must exist"


def test_release_notes_exists():
    assert (_ROOT / "docs" / "release-notes-v1.2.0.md").exists(), \
        "docs/release-notes-v1.2.0.md must exist"


# ── 12. No generated artifacts tracked ───────────────────────────────────────

def test_no_dist_directory_tracked():
    dist = _ROOT / "dist"
    # dist/ should be in .gitignore, so it shouldn't exist in a clean checkout.
    # If it exists, it was likely manually created — still acceptable.
    # The key check: no dist/ files are accidentally added to git index.
    # We check via .gitignore presence instead.
    gitignore = _read(_ROOT / ".gitignore")
    assert "dist/" in gitignore, ".gitignore must exclude dist/"


def test_no_latex_aux_tracked():
    gitignore = _read(_ROOT / ".gitignore")
    assert "paper/*.aux" in gitignore or ".aux" in gitignore, \
        ".gitignore must exclude LaTeX aux files"


def test_no_pdf_committed_in_paper():
    pdfs = list((_ROOT / "paper").glob("*.pdf"))
    assert not pdfs, \
        f"No PDFs should be committed to paper/: {[p.name for p in pdfs]}"


# ── 13. Honesty: not-a-theorem-prover stated ─────────────────────────────────

def test_readme_says_not_theorem_prover():
    readme = _read(_ROOT / "README.md").lower()
    assert "not" in readme and "theorem prover" in readme, \
        "README must state Stele is not a theorem prover"


def test_about_says_not_theorem_prover():
    html = _site_html("about.html").lower()
    assert "not a theorem prover" in html, \
        "about.html must state Stele is not a theorem prover"
