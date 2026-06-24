"""Static tests for theory.html and architecture.html (Prompt 45).

Checks page existence, required phrases, status badges, forbidden phrases,
navigation wiring, no external frameworks, no /api/ calls, and internal
link consistency.
"""
from __future__ import annotations

import re
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_SITE = _ROOT / "site"


def _theory() -> str:
    return (_SITE / "theory.html").read_text(encoding="utf-8")


def _arch() -> str:
    return (_SITE / "architecture.html").read_text(encoding="utf-8")


def _index() -> str:
    return (_SITE / "index.html").read_text(encoding="utf-8")


def _studio() -> str:
    return (_SITE / "studio.html").read_text(encoding="utf-8")


# ── 1. Pages exist ───────────────────────────────────────────────────────────

def test_theory_html_exists():
    assert (_SITE / "theory.html").exists(), "site/theory.html must exist"


def test_architecture_html_exists():
    assert (_SITE / "architecture.html").exists(), "site/architecture.html must exist"


# ── 2. Navigation wiring ─────────────────────────────────────────────────────

def test_index_links_to_theory():
    assert "theory.html" in _index(), "index.html must link to theory.html"


def test_index_links_to_architecture():
    assert "architecture.html" in _index(), "index.html must link to architecture.html"


def test_studio_links_to_theory():
    assert "theory.html" in _studio(), "studio.html must link to theory.html"


def test_studio_links_to_architecture():
    assert "architecture.html" in _studio(), "studio.html must link to architecture.html"


def test_theory_links_to_architecture():
    assert "architecture.html" in _theory(), "theory.html must link to architecture.html"


def test_theory_links_to_studio():
    assert "studio.html" in _theory(), "theory.html must link to studio.html"


def test_arch_links_to_theory():
    assert "theory.html" in _arch(), "architecture.html must link to theory.html"


def test_arch_links_to_studio():
    assert "studio.html" in _arch(), "architecture.html must link to studio.html"


# ── 3. Required phrases — theory.html ────────────────────────────────────────

REQUIRED_THEORY_PHRASES = [
    "proof checker, not theorem prover",
    "trusted kernel",
    "untrusted",
    "browser-local",
    "⊢",
    "⊨",
    "Kripke",
    "certificate",
    "minicheck",
]


@pytest.mark.parametrize("phrase", REQUIRED_THEORY_PHRASES)
def test_theory_has_required_phrase(phrase):
    html = _theory()
    assert phrase in html, \
        f"theory.html must contain the phrase: {phrase!r}"


# ── 4. Required phrases — architecture.html ───────────────────────────────────

REQUIRED_ARCH_PHRASES = [
    "trusted kernel",
    "untrusted",
    "kernel.py",
    "certificate",
    "minicheck",
    "browser-local",
    "zero runtime dependencies",
    "Pyodide",
]


@pytest.mark.parametrize("phrase", REQUIRED_ARCH_PHRASES)
def test_arch_has_required_phrase(phrase):
    html = _arch().lower()
    assert phrase.lower() in html, \
        f"architecture.html must contain the phrase: {phrase!r}"


# ── 5. Status badges ─────────────────────────────────────────────────────────

def test_theory_has_stable_badges():
    assert "badge-stable" in _theory(), \
        "theory.html must include at least one badge-stable status label"


def test_theory_has_experimental_badges():
    assert "badge-experimental" in _theory(), \
        "theory.html must include at least one badge-experimental status label"


def test_theory_has_demo_badge():
    assert "badge-demo" in _theory(), \
        "theory.html must label matrix semantics as Demo"


def test_theory_has_optional_badge():
    assert "badge-optional" in _theory(), \
        "theory.html must label ML/Lean as Optional"


def test_arch_has_stable_badge():
    assert "badge-stable" in _arch(), \
        "architecture.html must include at least one badge-stable label"


def test_arch_has_experimental_badge():
    assert "badge-experimental" in _arch(), \
        "architecture.html must include at least one badge-experimental label"


def test_arch_has_untrusted_badge():
    assert "badge-untrusted" in _arch(), \
        "architecture.html must mark untrusted layers"


# ── 6. Forbidden overclaim phrases ───────────────────────────────────────────

FORBIDDEN_PHRASES = [
    "fully verified",
    "fully verified metatheory",
    "complete proof assistant",
    "ai-powered verifier",
    "state-of-the-art",
    "production-ready",
    "production ready",
    "proves mathematical relativism",
    "implements yurihak",
    "unlock the power",
    "elevate your workflow",
    "dynamic rendering engine",
    "guaranteed proof",
]


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_theory_no_forbidden_phrase(phrase):
    assert phrase.lower() not in _theory().lower(), \
        f"Forbidden phrase {phrase!r} found in theory.html"


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_arch_no_forbidden_phrase(phrase):
    assert phrase.lower() not in _arch().lower(), \
        f"Forbidden phrase {phrase!r} found in architecture.html"


# ── 7. Key content — theory.html ─────────────────────────────────────────────

def test_theory_mentions_kripke_bounded():
    html = _theory().lower()
    assert "bounded" in html, \
        "theory.html must describe Kripke search as bounded"


def test_theory_kripke_not_complete():
    html = _theory().lower()
    # Must NOT claim completeness
    assert "complete kripke" not in html and \
           "kripke completeness" not in html, \
        "theory.html must not overclaim Kripke completeness"


def test_theory_has_proof_term_limitation():
    html = _theory().lower()
    # Must acknowledge classical proof-term limitation
    assert "classical" in html and ("limitation" in html or "not" in html), \
        "theory.html must note classical proof-term limitation"


def test_theory_has_metatheory_honesty():
    html = _theory().lower()
    assert "not machine" in html or "regression test" in html or "not formally" in html, \
        "theory.html must note that metatheory is not machine-checked"


def test_theory_has_stele_light_rules():
    html = _theory()
    # Should mention the rule names
    assert "imp_intro" in html and "mp" in html, \
        "theory.html must mention core rule names (imp_intro, mp)"


def test_theory_has_imp_self_example():
    html = _theory()
    assert "imp_self" in html or "P -> P" in html, \
        "theory.html must include the P → P example"


def test_theory_has_dne_example():
    html = _theory()
    assert "dne" in html.lower(), \
        "theory.html must include the dne example"


def test_theory_has_fol_section():
    html = _theory().lower()
    assert "fol" in html or "first-order" in html or "forall" in html, \
        "theory.html must cover the FOL proof-term fragment"


def test_theory_has_curry_howard():
    html = _theory().lower()
    assert "curry" in html and "howard" in html, \
        "theory.html must mention Curry-Howard"


def test_theory_has_matrix_section():
    html = _theory().lower()
    assert "k3" in html and "lp" in html, \
        "theory.html must cover K3 and LP matrix semantics"


# ── 8. Key content — architecture.html ───────────────────────────────────────

def test_arch_mentions_six_invariants():
    html = _arch().lower()
    # Must describe multiple invariants
    assert "invariant" in html, \
        "architecture.html must describe structural invariants"


def test_arch_has_kernel_path():
    html = _arch()
    assert "kernel.py" in html, \
        "architecture.html must reference kernel.py"


def test_arch_has_parser():
    html = _arch()
    assert "parser.py" in html, \
        "architecture.html must reference parser.py"


def test_arch_has_diagnostics():
    html = _arch()
    assert "diagnostics.py" in html, \
        "architecture.html must reference diagnostics.py"


def test_arch_minicheck_no_kernel_import():
    html = _arch().lower()
    assert "no kernel import" in html or "does not import" in html, \
        "architecture.html must note that minicheck does not import kernel"


def test_arch_has_certificate_flow():
    html = _arch().lower()
    assert "certificate" in html and "minicheck" in html, \
        "architecture.html must describe the certificate/minicheck flow"


def test_arch_has_pyodide_section():
    html = _arch().lower()
    assert "pyodide" in html and "wasm" in html, \
        "architecture.html must describe Pyodide/WASM execution"


def test_arch_has_zero_runtime_deps():
    html = _arch().lower()
    assert "zero runtime" in html or "no runtime dep" in html or \
           "zero runtime dependencies" in html, \
        "architecture.html must state zero runtime dependencies"


def test_arch_has_trust_diagram():
    html = _arch()
    assert "<svg" in html, \
        "architecture.html must include an SVG trust boundary diagram"


def test_arch_has_cert_flow_diagram():
    # Should have at least 2 SVGs (trust boundary + cert flow)
    html = _arch()
    count = html.count("<svg")
    assert count >= 2, \
        f"architecture.html must include at least 2 SVG diagrams; found {count}"


# ── 9. Diagrams are accessible ───────────────────────────────────────────────

def test_theory_svgs_have_titles():
    html = _theory()
    svgs = re.findall(r"<svg[^>]*>.*?</svg>", html, re.DOTALL)
    for svg in svgs:
        assert "<title" in svg, \
            "Each SVG in theory.html must have a <title> element for accessibility"


def test_arch_svgs_have_titles():
    html = _arch()
    svgs = re.findall(r"<svg[^>]*>.*?</svg>", html, re.DOTALL)
    for svg in svgs:
        assert "<title" in svg, \
            "Each SVG in architecture.html must have a <title> element for accessibility"


def test_theory_has_figure_captions():
    assert "figcaption" in _theory(), \
        "theory.html SVG diagrams should have figcaption descriptions"


def test_arch_has_figure_captions():
    assert "figcaption" in _arch(), \
        "architecture.html SVG diagrams should have figcaption descriptions"


# ── 10. No external frameworks ────────────────────────────────────────────────

FORBIDDEN_FRAMEWORK_REFS = [
    "react.js", "react.min.js", "three.js", "three.min.js",
    "spline", "framer-motion", "tailwindcss",
    "unpkg.com", "jsdelivr.net",
]


@pytest.mark.parametrize("ref", FORBIDDEN_FRAMEWORK_REFS)
def test_theory_no_external_framework(ref):
    assert ref not in _theory().lower(), \
        f"theory.html must not reference external framework/CDN: {ref}"


@pytest.mark.parametrize("ref", FORBIDDEN_FRAMEWORK_REFS)
def test_arch_no_external_framework(ref):
    assert ref not in _arch().lower(), \
        f"architecture.html must not reference external framework/CDN: {ref}"


def test_theory_no_external_scripts():
    html = _theory()
    srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    for src in srcs:
        assert not src.startswith("http"), \
            f"theory.html must not load external scripts: {src}"


def test_arch_no_external_scripts():
    html = _arch()
    srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    for src in srcs:
        assert not src.startswith("http"), \
            f"architecture.html must not load external scripts: {src}"


# ── 11. No /api/ calls ───────────────────────────────────────────────────────

def test_theory_no_api_calls():
    assert "/api/" not in _theory(), \
        "theory.html must not reference /api/ backend calls"


def test_arch_no_api_calls():
    assert "/api/" not in _arch(), \
        "architecture.html must not reference /api/ backend calls"


# ── 12. Basic HTML structure ─────────────────────────────────────────────────

def test_theory_has_nav():
    assert "<nav" in _theory() and "site-nav" in _theory()


def test_theory_has_footer():
    assert "<footer" in _theory()


def test_theory_has_main():
    assert '<main' in _theory()


def test_arch_has_nav():
    assert "<nav" in _arch() and "site-nav" in _arch()


def test_arch_has_footer():
    assert "<footer" in _arch()


def test_arch_has_main():
    assert '<main' in _arch()


def test_theory_has_skip_link():
    assert "focus-skip" in _theory(), \
        "theory.html must have a skip-to-content link"


def test_arch_has_skip_link():
    assert "focus-skip" in _arch(), \
        "architecture.html must have a skip-to-content link"


# ── 13. Formal identity ──────────────────────────────────────────────────────

def test_theory_formal_verification_identity():
    html = _theory().lower()
    assert "formal verification framework" in html or \
           "proof checker" in html, \
        "theory.html must assert the formal verification framework identity"


def test_arch_formal_verification_identity():
    html = _arch().lower()
    assert "formal verification framework" in html or \
           "proof checker" in html, \
        "architecture.html must include formal verification framework identity"
