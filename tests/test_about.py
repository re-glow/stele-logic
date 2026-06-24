"""Static tests for site/about.html (Prompt 49).

Checks: required sections exist, status labels present, required links,
forbidden overclaims absent, honesty markers, privacy policy (no email/school/location),
nav completeness, limitations section.
"""
from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_ABOUT = _ROOT / "site" / "about.html"


def _html() -> str:
    return _ABOUT.read_text(encoding="utf-8")


# ── 1. File exists ───────────────────────────────────────────────────────────

def test_about_html_exists():
    assert _ABOUT.exists(), "site/about.html must exist"


def test_about_html_not_empty():
    content = _html()
    assert len(content) > 2000, "site/about.html must contain substantial content"


# ── 2. Required structural sections ─────────────────────────────────────────

REQUIRED_SECTIONS = [
    ("project story", r"project\s+story"),
    ("what was built", r"what\s+(?:was|i)\s+built"),
    ("my role", r"my\s+role"),
    ("research motivation", r"research\s+motivation"),
    ("limitations", r"<[^>]+id=['\"]limits"),
    ("cta continue section", r"<[^>]+id=['\"]cta"),
]


@pytest.mark.parametrize("label,pattern", REQUIRED_SECTIONS)
def test_required_section_present(label, pattern):
    html = _html()
    assert re.search(pattern, html, re.IGNORECASE), \
        f"site/about.html must contain section: {label!r}"


# ── 3. Author identity ────────────────────────────────────────────────────────

def test_author_name_present():
    html = _html()
    assert "Jaehwan Kim" in html, "about.html must mention author name 'Jaehwan Kim'"


def test_independent_research_mentioned():
    html = _html().lower()
    assert "independent" in html, \
        "about.html must describe Stele as an independent project"


# ── 4. Privacy: no sensitive personal information ────────────────────────────

def test_no_email_in_about():
    html = _html()
    email_pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, html)
    # Exclude allowed GitHub/CDN references (none expected)
    assert not emails, \
        f"site/about.html must not contain email addresses; found: {emails}"


def test_no_school_name_in_about():
    html = _html().lower()
    forbidden_school_patterns = [
        r"\buniversity\b", r"\bcollege\b", r"\buniv\b",
        r"\bschool of\b", r"\binstitute of technology\b",
    ]
    for pat in forbidden_school_patterns:
        m = re.search(pat, html)
        assert not m, \
            f"site/about.html must not name a school; found pattern {pat!r}"


def test_no_location_in_about():
    html = _html().lower()
    location_words = ["seoul", "korea", "united states", "california", "new york"]
    for loc in location_words:
        assert loc not in html, \
            f"site/about.html must not mention location: {loc!r}"


# ── 5. Navigation completeness ────────────────────────────────────────────────

def test_nav_has_studio_link():
    assert 'href="studio.html"' in _html(), "Nav must link to studio.html"


def test_nav_has_theory_link():
    assert 'href="theory.html"' in _html(), "Nav must link to theory.html"


def test_nav_has_architecture_link():
    assert 'href="architecture.html"' in _html(), "Nav must link to architecture.html"


def test_nav_has_research_link():
    assert 'href="research.html"' in _html(), "Nav must link to research.html"


def test_nav_has_foundations_link():
    assert 'href="foundations.html"' in _html(), "Nav must link to foundations.html"


def test_nav_has_github_link():
    assert "github.com/re-glow/stele-logic" in _html(), \
        "Nav must include GitHub link"


def test_about_marked_current_in_own_nav():
    html = _html()
    assert 'aria-current="page"' in html, \
        "about.html must mark itself as current page (aria-current)"


# ── 6. Status labels ─────────────────────────────────────────────────────────

STATUS_LABELS = ["badge-stable", "badge-experimental", "badge-untrusted"]


@pytest.mark.parametrize("badge", STATUS_LABELS)
def test_status_badge_present(badge):
    html = _html()
    assert badge in html, \
        f"about.html must include status badge: {badge!r}"


# ── 7. Evidence cards: required features ─────────────────────────────────────

REQUIRED_FEATURES = [
    ("proof checker kernel", r"kernel"),
    ("browser studio", r"[Ss]tudio"),
    ("diagnostics", r"[Dd]iagnostics"),
    ("dependency graph", r"dependency\s+graph"),
    ("Kripke", r"[Kk]ripke"),
    ("matrix semantics", r"matrix|K3|LP"),
    ("proof-term core", r"proof.term|[Cc]urry"),
    ("certificates", r"certificate"),
]


@pytest.mark.parametrize("feature,pattern", REQUIRED_FEATURES)
def test_feature_card_present(feature, pattern):
    html = _html()
    assert re.search(pattern, html), \
        f"about.html must have an evidence card for: {feature!r}"


# ── 8. Limitations ────────────────────────────────────────────────────────────

REQUIRED_LIMITATIONS = [
    ("not a theorem prover", r"[Nn]ot a theorem prover"),
    ("not Lean/Coq replacement", r"[Ll]ean|[Cc]oq|Rocq"),
    ("metatheory not machine-checked", r"not machine.checked"),
    ("Kripke bounded", r"[Bb]ounded"),
]


@pytest.mark.parametrize("limitation,pattern", REQUIRED_LIMITATIONS)
def test_limitation_stated(limitation, pattern):
    html = _html()
    assert re.search(pattern, html), \
        f"about.html must state limitation: {limitation!r}"


# ── 9. Honesty markers ────────────────────────────────────────────────────────

def test_ai_assistance_mentioned():
    html = _html().lower()
    assert "ai" in html or "coding tool" in html or "ai coding" in html or \
           "assistant" in html, \
        "about.html must mention AI tool assistance (transparency)"


def test_yurihak_not_implemented_stated():
    html = _html().lower()
    assert "yurihak" in html, "about.html must mention Yurihak"
    assert "not yet" in html or "not implemented" in html or "future work" in html, \
        "about.html must clarify Yurihak is not yet a formal Stele logic"


def test_no_overclaim_theorem_prover():
    html = _html().lower()
    # Looking for actual claims, not the negations we write
    assert "stele is a theorem prover" not in html, \
        "about.html must not claim Stele is a theorem prover"


def test_no_overclaim_ai_verifier():
    html = _html().lower()
    assert "ai-powered verifier" not in html and "ai powered verifier" not in html, \
        "about.html must not claim Stele is an AI-powered verifier"


def test_no_overclaim_lean_replacement():
    html = _html().lower()
    assert "replaces lean" not in html and "replacement for lean" not in html, \
        "about.html must not claim to replace Lean"


# ── 10. Footer ───────────────────────────────────────────────────────────────

def test_footer_has_github_link():
    html = _html()
    footer_section = html.split("<footer")[1] if "<footer" in html else ""
    assert "github.com/re-glow/stele-logic" in footer_section, \
        "Footer must include GitHub link"


def test_footer_has_author_credit():
    html = _html()
    footer_section = html.split("<footer")[1] if "<footer" in html else ""
    assert "Jaehwan Kim" in footer_section, \
        "Footer must credit Jaehwan Kim"


# ── 11. CTA links ────────────────────────────────────────────────────────────

CTA_LINKS = [
    "studio.html",
    "theory.html",
    "architecture.html",
    "foundations.html",
    "research.html",
]


@pytest.mark.parametrize("target", CTA_LINKS)
def test_cta_link_present(target):
    html = _html()
    assert target in html, \
        f"about.html must include a CTA link to {target!r}"
