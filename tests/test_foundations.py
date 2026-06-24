"""Static tests for site/foundations.html and docs/foundations-program.md (Prompt 46).

Checks page existence, required phrases, claim discipline, status labels,
forbidden overclaims, navigation wiring, companion doc, source file listing,
no external frameworks, and no /api/ calls.
"""
from __future__ import annotations

import re
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_SITE = _ROOT / "site"
_DOCS = _ROOT / "docs"


def _found() -> str:
    return (_SITE / "foundations.html").read_text(encoding="utf-8")


def _companion() -> str:
    return (_DOCS / "foundations-program.md").read_text(encoding="utf-8")


def _index() -> str:
    return (_SITE / "index.html").read_text(encoding="utf-8")


def _studio() -> str:
    return (_SITE / "studio.html").read_text(encoding="utf-8")


def _theory() -> str:
    return (_SITE / "theory.html").read_text(encoding="utf-8")


def _arch() -> str:
    return (_SITE / "architecture.html").read_text(encoding="utf-8")


# ── 1. Files exist ───────────────────────────────────────────────────────────

def test_foundations_html_exists():
    assert (_SITE / "foundations.html").exists(), \
        "site/foundations.html must exist"


def test_foundations_companion_doc_exists():
    assert (_DOCS / "foundations-program.md").exists(), \
        "docs/foundations-program.md must exist"


# ── 2. Required phrases in foundations.html ───────────────────────────────────

REQUIRED_FOUND_PHRASES = [
    "Foundations",
    "Research Program",
    "Implemented",
    "Motivation",
    "Future",
    "not yet implemented",
    "browser-local",
]


@pytest.mark.parametrize("phrase", REQUIRED_FOUND_PHRASES)
def test_foundations_has_required_phrase(phrase):
    assert phrase in _found(), \
        f"foundations.html must contain: {phrase!r}"


def test_foundations_has_yurihak():
    html = _found()
    assert "Yurihak" in html or "유리학" in html, \
        "foundations.html must mention Yurihak or 유리학"


def test_foundations_yurihak_not_implemented():
    html = _found().lower()
    # Must say explicitly that Yurihak is not implemented
    assert "not implemented" in html, \
        "foundations.html must state that Yurihak is not implemented"


# ── 3. Status labels ─────────────────────────────────────────────────────────

def test_foundations_has_stable_badge():
    assert "badge-stable" in _found(), \
        "foundations.html must include at least one badge-stable"


def test_foundations_has_experimental_badge():
    assert "badge-experimental" in _found(), \
        "foundations.html must include at least one badge-experimental"


def test_foundations_has_motivation_badge():
    assert "badge-motivation" in _found(), \
        "foundations.html must include at least one badge-motivation"


def test_foundations_has_future_badge():
    assert "badge-future" in _found(), \
        "foundations.html must include at least one badge-future"


def test_foundations_has_demo_badge():
    assert "badge-demo" in _found(), \
        "foundations.html must label matrix semantics as Demo"


def test_foundations_has_untrusted_badge():
    assert "badge-untrusted" in _found(), \
        "foundations.html must mark diagnostics/hints as Untrusted"


# ── 4. Forbidden overclaim phrases ───────────────────────────────────────────

FORBIDDEN_FOUND_PHRASES = [
    "stele implements yurihak",
    "proves relativism",
    "fully formalized yurihak",
    "proves mathematical relativism",
    "completed yurihak system",
    "universal logic",
    "world-changing philosophy",
    "ultimate truth",
    "new foundation of mathematics",
    "implements yurihak",
    "ai-powered",
    "state-of-the-art",
    "production-ready",
    "unlock the power",
    "elevate your workflow",
]


@pytest.mark.parametrize("phrase", FORBIDDEN_FOUND_PHRASES)
def test_foundations_no_forbidden_phrase(phrase):
    assert phrase.lower() not in _found().lower(), \
        f"Forbidden overclaim phrase {phrase!r} found in foundations.html"


# ── 5. Claim/evidence table ───────────────────────────────────────────────────

def test_foundations_has_claim_table():
    html = _found()
    assert "<table" in html, \
        "foundations.html must include a claim/evidence table"


def test_foundations_table_has_headers():
    html = _found()
    assert "Status" in html and "Evidence" in html and "Limitation" in html, \
        "foundations.html claim table must have Status, Evidence, and Limitation columns"


def test_foundations_table_has_yurihak_row():
    html = _found().lower()
    assert "yurihak" in html and "motivation" in html, \
        "claim table must include a Yurihak row with Motivation status"


# ── 6. Navigation wiring ─────────────────────────────────────────────────────

def test_index_links_to_foundations():
    assert "foundations.html" in _index(), \
        "index.html must link to foundations.html"


def test_studio_links_to_foundations():
    assert "foundations.html" in _studio(), \
        "studio.html must link to foundations.html"


def test_theory_links_to_foundations():
    assert "foundations.html" in _theory(), \
        "theory.html must link to foundations.html"


def test_arch_links_to_foundations():
    assert "foundations.html" in _arch(), \
        "architecture.html must link to foundations.html"


def test_foundations_links_to_theory():
    assert "theory.html" in _found(), \
        "foundations.html must link to theory.html"


def test_foundations_links_to_architecture():
    assert "architecture.html" in _found(), \
        "foundations.html must link to architecture.html"


def test_foundations_links_to_studio():
    assert "studio.html" in _found(), \
        "foundations.html must link to studio.html"


def test_foundations_links_to_research():
    assert "research.html" in _found(), \
        "foundations.html must link to research.html"


# ── 7. Companion doc content ──────────────────────────────────────────────────

def test_companion_doc_has_source_inventory():
    doc = _companion()
    assert "yurihak-introduction.pdf" in doc, \
        "foundations-program.md must list yurihak-introduction.pdf"


def test_companion_doc_has_all_four_pdfs():
    doc = _companion()
    for pdf in [
        "yurihak-introduction.pdf",
        "window-localized.pdf",
        "closure-atlases.pdf",
        "bounded-cores.pdf",
    ]:
        assert pdf in doc, \
            f"foundations-program.md must list source file: {pdf}"


def test_companion_doc_has_claim_boundaries():
    doc = _companion().lower()
    assert "not implemented" in doc or "not yet" in doc, \
        "foundations-program.md must describe claim boundaries"


def test_companion_doc_has_todo_section():
    doc = _companion()
    assert "TODO" in doc or "todo" in doc.lower(), \
        "foundations-program.md must have TODO items for unextracted papers"


def test_companion_doc_has_implemented_vs_future():
    doc = _companion().lower()
    assert "implemented" in doc and "future" in doc, \
        "foundations-program.md must have an implemented vs future mapping"


# ── 8. Source PDFs listed ────────────────────────────────────────────────────

SOURCE_PDFS = [
    "yurihak-introduction.pdf",
    "window-localized.pdf",
    "closure-atlases.pdf",
    "bounded-cores.pdf",
]


@pytest.mark.parametrize("pdf", SOURCE_PDFS)
def test_source_pdf_present_on_disk(pdf):
    pdf_path = _ROOT / "references" / "incoming" / pdf
    assert pdf_path.exists(), \
        f"Source PDF must be present at references/incoming/{pdf}"


@pytest.mark.parametrize("pdf", SOURCE_PDFS)
def test_foundations_mentions_pdf_filename(pdf):
    assert pdf in _found(), \
        f"foundations.html must reference source file: {pdf}"


# ── 9. Page structure ────────────────────────────────────────────────────────

def test_foundations_has_nav():
    html = _found()
    assert "<nav" in html and "site-nav" in html, \
        "foundations.html must have a site-nav"


def test_foundations_has_footer():
    assert "<footer" in _found(), \
        "foundations.html must have a footer"


def test_foundations_has_main():
    assert "<main" in _found(), \
        "foundations.html must have a <main> element"


def test_foundations_has_skip_link():
    assert "focus-skip" in _found(), \
        "foundations.html must have a skip-to-content link"


def test_foundations_has_hero_heading():
    html = _found()
    assert "Foundations" in html and ("Research Program" in html), \
        "foundations.html must have a hero with 'Foundations' and 'Research Program'"


def test_foundations_has_scope_clarification():
    html = _found().lower()
    assert "scope clarification" in html or "this page separates" in html or \
           "not a logic implementation" in html or "separates" in html, \
        "foundations.html must have a scope clarifier banner"


def test_foundations_has_roadmap_section():
    html = _found().lower()
    assert "roadmap" in html or "future formalization" in html, \
        "foundations.html must have a future formalization roadmap section"


def test_foundations_has_trust_boundary_section():
    html = _found().lower()
    assert "trust" in html and ("kernel" in html or "untrusted" in html), \
        "foundations.html must explain relationship to trust boundary"


# ── 10. No external frameworks ───────────────────────────────────────────────

FORBIDDEN_FRAMEWORK_REFS = [
    "react.js", "react.min.js", "three.js", "three.min.js",
    "spline", "framer-motion", "tailwindcss",
    "unpkg.com", "jsdelivr.net",
]


@pytest.mark.parametrize("ref", FORBIDDEN_FRAMEWORK_REFS)
def test_foundations_no_external_framework(ref):
    assert ref not in _found().lower(), \
        f"foundations.html must not reference external framework: {ref}"


def test_foundations_no_external_scripts():
    html = _found()
    srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    for src in srcs:
        assert not src.startswith("http"), \
            f"foundations.html must not load external scripts: {src}"


# ── 11. No /api/ calls ───────────────────────────────────────────────────────

def test_foundations_no_api_calls():
    assert "/api/" not in _found(), \
        "foundations.html must not reference /api/ backend calls"


# ── 12. Formal identity ──────────────────────────────────────────────────────

def test_foundations_formal_identity():
    html = _found().lower()
    assert "formal verification framework" in html or "proof checker" in html, \
        "foundations.html must assert the formal verification framework identity"


# ── 13. badge-motivation CSS class exists ────────────────────────────────────

def test_badge_motivation_defined_in_css():
    css_path = _SITE / "assets" / "components.css"
    css = css_path.read_text(encoding="utf-8")
    assert "badge-motivation" in css, \
        "assets/components.css must define .badge-motivation"
