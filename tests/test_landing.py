"""Static tests for the redesigned landing page (Prompt 43).

Checks identity, CTAs, proof graph, audience cards, Kripke mention,
whitepaper link, multi-page nav, trust boundary, Studio panel IDs,
forbidden phrases, and asset-loading constraints.
"""
from __future__ import annotations

import re
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_SITE = _ROOT / "site"
_CSS  = _SITE / "assets" / "stele_site.css"
_TOK  = _SITE / "assets" / "tokens.css"


def _html() -> str:
    return (_SITE / "index.html").read_text(encoding="utf-8")


# ── 1. Landing identity ──────────────────────────────────────────────────────

def test_hero_formal_verification_identity():
    html = _html().lower()
    assert "formal verification framework" in html, \
        "index.html hero must state 'Formal Verification Framework'"


def test_hero_not_logical_pluralism_headline():
    html = _html()
    headings = re.findall(r"<h[12][^>]*>(.*?)</h[12]>", html, re.IGNORECASE | re.DOTALL)
    for h in headings:
        assert "logical pluralism" not in h.lower(), \
            f"Heading must not be framed as 'logical pluralism': {h[:80]}"


# ── 2. Concrete hero headline ────────────────────────────────────────────────

def test_hero_concrete_headline():
    html = _html().lower()
    assert ("write a proof" in html or "check every rule" in html or
            "mathematical reasoning, verified" in html), \
        "Hero headline should be concrete and action-oriented"


# ── 3. Not-a-theorem-prover ──────────────────────────────────────────────────

def test_not_a_theorem_prover_stated():
    html = _html().lower()
    assert "not a theorem prover" in html or "proof checker" in html, \
        "index.html must clarify: Stele is not a theorem prover"


# ── 4. Status badges ─────────────────────────────────────────────────────────

def test_status_badge_stable_present():
    assert "badge-stable" in _html(), \
        "index.html must include at least one badge-stable status label"


def test_status_badge_experimental_present():
    assert "badge-experimental" in _html(), \
        "index.html must include at least one badge-experimental status label"


# ── 5. Hero CTAs ─────────────────────────────────────────────────────────────

def test_hero_open_studio_cta():
    assert "Open Studio" in _html(), "Hero must include 'Open Studio' CTA"


def test_hero_whitepaper_cta():
    html = _html().lower()
    assert "whitepaper" in html or "research.html" in html, \
        "Hero or navigation must link to the whitepaper / research page"


# ── 6. Proof graph visual ────────────────────────────────────────────────────

def test_proof_graph_visual_present():
    html = _html()
    assert ("stele-conclude-pulse" in html or
            'data-stele-visual="proof-graph"' in html or
            "hero-graph" in html), \
        "Hero must include a proof dependency graph visual"


def test_proof_graph_has_conclude_node():
    assert "∴" in _html(), \
        "Proof graph must include the ∴ (therefore) conclusion node"


# ── 7. Audience navigation ───────────────────────────────────────────────────

def test_audience_cards_present():
    assert "audience-card" in _html(), \
        "Landing must include audience-specific navigation cards"


def test_audience_card_technical_reviewer():
    assert "technical reviewer" in _html().lower(), \
        "Audience cards must include path for technical reviewers"


def test_audience_card_research():
    assert "research" in _html().lower(), \
        "Audience cards must include path to research/whitepaper"


# ── 8. Kripke mentioned in §2 ────────────────────────────────────────────────

def test_kripke_mentioned_in_what_section():
    html = _html()
    what_start = html.find('id="what"')
    studio_start = html.find('id="studio"')
    if what_start == -1:
        pytest.skip("#what section not found")
    end = studio_start if studio_start > what_start else len(html)
    section_html = html[what_start:end]
    assert "kripke" in section_html.lower(), \
        "§2 What Stele Does should mention Kripke countermodel search"


# ── 9. Whitepaper link ───────────────────────────────────────────────────────

def test_whitepaper_link_present():
    html = _html().lower()
    assert "whitepaper" in html or "research.html" in html, \
        "index.html must link to the technical whitepaper / research page"


def test_whitepaper_in_docs_section():
    html = _html()
    docs_start = html.find('id="docs"')
    if docs_start == -1:
        pytest.skip("#docs section not found")
    docs_html = html[docs_start:]
    assert ("whitepaper" in docs_html.lower() or "research.html" in docs_html.lower()), \
        "Docs section must link to the whitepaper or research page"


def test_whitepaper_in_tutorial_step6():
    html = _html()
    step6_start = html.find('id="tstep-6"')
    if step6_start == -1:
        pytest.skip("#tstep-6 not found")
    step6_html = html[step6_start:step6_start + 2000]
    assert ("whitepaper" in step6_html.lower() or "research.html" in step6_html.lower()), \
        "Tutorial step 6 'What's next' must include a whitepaper card"


# ── 10. Multi-page nav ───────────────────────────────────────────────────────

def test_nav_links_theory_page():
    assert "theory.html" in _html(), \
        "Navigation must link to theory.html"


def test_nav_links_research_page():
    assert "research.html" in _html(), \
        "Navigation must link to research.html (whitepaper page)"


# ── 11. Trust boundary ───────────────────────────────────────────────────────

def test_trust_boundary_mentioned():
    html = _html().lower()
    assert "trust" in html and "kernel" in html, \
        "index.html must mention the trust boundary and kernel"


def test_trust_cards_present():
    html = _html()
    assert "trust-card-trusted" in html and "trust-card-untrusted" in html, \
        "index.html must include trusted and untrusted trust cards in §2"


# ── 12. Studio panel IDs intact (regression guard) ──────────────────────────

REQUIRED_STUDIO_IDS = [
    "proof-input", "logic-select", "btn-check", "check-result",
    "btn-diagnose", "diag-result",
    "btn-graph", "graph-dot",
    "btn-soundness", "soundness-result",
    "btn-lattice", "lattice-result", "lattice-input",
    "examples-grid",
]


@pytest.mark.parametrize("eid", REQUIRED_STUDIO_IDS)
def test_studio_id_intact(eid):
    html = _html()
    assert f'id="{eid}"' in html or f"id='{eid}'" in html, \
        f"Studio panel id='{eid}' must remain intact after landing redesign"


# ── 13. No forbidden copy phrases ────────────────────────────────────────────

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


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_no_forbidden_phrase_in_landing(phrase):
    assert phrase not in _html().lower(), \
        f"Forbidden phrase '{phrase}' found in index.html"


# ── 14. Reduced-motion in CSS ────────────────────────────────────────────────

def test_stele_site_css_has_reduced_motion():
    assert "prefers-reduced-motion" in _CSS.read_text(encoding="utf-8")


def test_tokens_css_has_reduced_motion():
    assert "prefers-reduced-motion" in _TOK.read_text(encoding="utf-8")


# ── 15. No /api/ calls ───────────────────────────────────────────────────────

def test_no_api_calls():
    assert "/api/" not in _html(), \
        "index.html must not contain /api/ backend calls"


# ── 16. Local asset loading ──────────────────────────────────────────────────

def test_no_external_script_src():
    html = _html()
    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    for src in script_srcs:
        assert not src.startswith("http"), \
            f"index.html must not load external scripts: {src}"


def test_no_external_css_links():
    html = _html()
    link_tags = re.findall(r'<link([^>]+)>', html, re.IGNORECASE)
    for tag in link_tags:
        if 'stylesheet' in tag.lower():
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', tag)
            for href in hrefs:
                assert not href.startswith("http"), \
                    f"index.html must not load external CSS: {href}"
