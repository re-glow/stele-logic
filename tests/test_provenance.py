"""Static tests for docs/references.md, docs/provenance-map.md,
and paper/references.bib (Prompt 47 — References & Provenance Map).

Checks: file existence, required tables, required sections,
citation-key consistency, claim-discipline phrases, no private PDFs bundled,
no runtime dependencies in docs.
"""
from __future__ import annotations

import re
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_DOCS = _ROOT / "docs"
_PAPER = _ROOT / "paper"


def _references() -> str:
    return (_DOCS / "references.md").read_text(encoding="utf-8")


def _provenance() -> str:
    return (_DOCS / "provenance-map.md").read_text(encoding="utf-8")


def _bib() -> str:
    return (_PAPER / "references.bib").read_text(encoding="utf-8")


def _whitepaper() -> str:
    return (_PAPER / "stele-whitepaper.tex").read_text(encoding="utf-8")


# ── 1. Files exist ────────────────────────────────────────────────────────────

def test_references_md_exists():
    assert (_DOCS / "references.md").exists(), "docs/references.md must exist"


def test_provenance_map_md_exists():
    assert (_DOCS / "provenance-map.md").exists(), "docs/provenance-map.md must exist"


# ── 2. references.md required sections ───────────────────────────────────────

REQUIRED_REFS_SECTIONS = [
    "## 1. Implemented algorithmic foundations",
    "## 2. Related systems",
    "## 3. Personal / foundational research line",
    "## 4. Future / not yet implemented",
    "## 5. What Stele does not claim",
]


@pytest.mark.parametrize("section", REQUIRED_REFS_SECTIONS)
def test_references_has_section(section):
    assert section in _references(), \
        f"docs/references.md must contain section: {section!r}"


def test_references_has_implemented_entries():
    doc = _references()
    assert "kernel.py" in doc, \
        "docs/references.md must mention kernel.py in implemented foundations"
    assert "matrix.py" in doc, \
        "docs/references.md must mention matrix.py in implemented foundations"
    assert "kripke.py" in doc, \
        "docs/references.md must mention kripke.py in implemented foundations"


def test_references_has_related_systems_table():
    doc = _references()
    assert "Lean" in doc and "Rocq" in doc and "Isabelle" in doc, \
        "docs/references.md must list related systems (Lean, Rocq, Isabelle)"


def test_references_not_a_replacement():
    doc = _references().lower()
    assert "not a replacement" in doc or "not" in doc and "replacement" in doc, \
        "docs/references.md must state Stele is not a replacement for proof assistants"


def test_references_yurihak_section_present():
    doc = _references()
    assert "Yurihak" in doc or "유리학" in doc, \
        "docs/references.md must mention the Yurihak research line"


def test_references_yurihak_not_implemented():
    doc = _references().lower()
    assert "not currently implemented" in doc or "not implemented" in doc, \
        "docs/references.md must clarify Yurihak is not implemented"


def test_references_pdf_filenames_listed():
    doc = _references()
    for pdf in [
        "yurihak-introduction.pdf",
        "window-localized.pdf",
        "closure-atlases.pdf",
        "bounded-cores.pdf",
    ]:
        assert pdf in doc, \
            f"docs/references.md must list source filename for provenance: {pdf}"


def test_references_pdfs_not_committed():
    doc = _references().lower()
    assert "not bundled" in doc or "not committed" in doc or "local" in doc, \
        "docs/references.md must state that PDFs are not bundled/committed"


def test_references_what_stele_does_not_claim():
    doc = _references()
    assert "What Stele does not claim" in doc, \
        "docs/references.md must have a 'What Stele does not claim' section"


def test_references_not_theorem_prover():
    doc = _references()
    assert "not a theorem prover" in doc.lower() or "not a theorem prover" in doc, \
        "docs/references.md must state Stele is not a theorem prover"


def test_references_not_formally_verified():
    doc = _references().lower()
    assert "not formally verified" in doc or "not machine-checked" in doc, \
        "docs/references.md must clarify metatheory is not formally verified"


def test_references_ml_not_production():
    doc = _references().lower()
    assert "not production ml" in doc or "not production" in doc, \
        "docs/references.md must state the ML baseline is not production ML"


# ── 3. provenance-map.md required tables ─────────────────────────────────────

REQUIRED_PROVENANCE_SECTIONS = [
    "## Table 1:",
    "## Table 2:",
    "## Table 3:",
    "## Table 4:",
    "What Stele does not claim",
]


@pytest.mark.parametrize("section", REQUIRED_PROVENANCE_SECTIONS)
def test_provenance_has_section(section):
    assert section in _provenance(), \
        f"docs/provenance-map.md must contain section: {section!r}"


def test_provenance_table1_has_required_columns():
    doc = _provenance()
    for col in ["Claim", "Public status", "module", "Tests", "Source", "Limitation"]:
        assert col.lower() in doc.lower(), \
            f"Table 1 must have column: {col!r}"


def test_provenance_table2_inspiration_vs_implementation():
    doc = _provenance()
    assert "Inspiration vs Implementation" in doc or "Inspiration" in doc, \
        "docs/provenance-map.md must have an inspiration vs implementation table"


def test_provenance_table3_module_provenance():
    doc = _provenance()
    assert "Module Provenance" in doc or "Module" in doc and "Trusted" in doc, \
        "docs/provenance-map.md must have a module provenance table"


def test_provenance_table4_citation_status():
    doc = _provenance()
    assert "Citation status" in doc or "Citation Status" in doc, \
        "docs/provenance-map.md must have a citation status table"


def test_provenance_table1_has_kernel_row():
    doc = _provenance()
    assert "kernel.py" in doc, \
        "provenance-map.md Table 1 must include a kernel.py row"


def test_provenance_table1_has_yurihak_row():
    doc = _provenance()
    assert "Yurihak" in doc, \
        "provenance-map.md Table 1 must include a Yurihak row"


def test_provenance_table4_all_bibtex_keys_listed():
    doc = _provenance()
    for key in [
        "Moura2021", "Nipkow2002", "Rocq", "Norell2009",
        "SorensenUrzyczyn2006", "PierceT98", "Kleene1952",
        "Priest1979", "TroelstraVanDalen1988", "Pyodide",
        "HarperHP1993", "Malinowski1993", "Yang2023",
    ]:
        assert key in doc, \
            f"provenance-map.md Table 4 must list citation key: {key!r}"


def test_provenance_links_to_references():
    doc = _provenance()
    assert "references.md" in doc, \
        "docs/provenance-map.md must link to docs/references.md"


def test_provenance_links_to_foundations():
    doc = _provenance()
    assert "foundations" in doc.lower(), \
        "docs/provenance-map.md must reference foundations docs"


# ── 4. BibTeX citation-key completeness ──────────────────────────────────────

def _bib_keys() -> set[str]:
    """Extract all BibTeX entry keys from the .bib file (non-commented lines)."""
    keys = set()
    for line in _bib().splitlines():
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        m = re.match(r'@\w+\{([^,\s]+)', stripped)
        if m:
            keys.add(m.group(1))
    return keys


def _whitepaper_cite_keys() -> set[str]:
    """Extract all \\cite{...} keys from the whitepaper (non-commented lines)."""
    keys = set()
    for line in _whitepaper().splitlines():
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        for match in re.finditer(r'\\cite\{([^}]+)\}', stripped):
            for key in match.group(1).split(","):
                keys.add(key.strip())
    return keys


def test_all_whitepaper_cite_keys_defined_in_bib():
    bib_keys = _bib_keys()
    tex_keys = _whitepaper_cite_keys()
    undefined = tex_keys - bib_keys
    assert not undefined, \
        f"Whitepaper uses cite keys not defined in references.bib: {sorted(undefined)}"


def test_bib_has_malinowski():
    assert "Malinowski1993" in _bib_keys(), \
        "references.bib must have a Malinowski1993 entry"


def test_bib_has_harper_lf():
    assert "HarperHP1993" in _bib_keys(), \
        "references.bib must have a HarperHP1993 (LF) entry"


def test_bib_has_yang_leandojo():
    assert "Yang2023" in _bib_keys(), \
        "references.bib must have a Yang2023 (LeanDojo) entry"


def test_bib_has_no_todo_keys_active():
    bib_keys = _bib_keys()
    todo_keys = {k for k in bib_keys if k.startswith("TODO:")}
    assert not todo_keys, \
        f"references.bib must not have active (uncommented) TODO: keys: {todo_keys}"


def test_whitepaper_has_no_todo_cite_keys():
    tex_keys = _whitepaper_cite_keys()
    todo_keys = {k for k in tex_keys if k.startswith("TODO:")}
    assert not todo_keys, \
        f"Whitepaper must not use TODO: cite keys: {todo_keys}"


# ── 5. Claim discipline — no overclaim phrases in docs ───────────────────────

# Phrases that must NOT appear (positive overclaims, not negations).
# Avoid phrases that also appear in valid negation context ("not formally verified").
FORBIDDEN_PHRASES = [
    "stele is formally verified",
    "machine-checked proof of",
    "proves relativism",
    "proves mathematical relativism",
    "production-ready",
    "state-of-the-art proof",
    "stele is a theorem prover",
    "stele is the theorem prover",
]


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_references_no_forbidden_phrase(phrase):
    assert phrase.lower() not in _references().lower(), \
        f"Forbidden phrase {phrase!r} found in docs/references.md"


@pytest.mark.parametrize("phrase", [
    "proves relativism",
    "proves mathematical relativism",
    "production-ready",
    "stele is a theorem prover",
    "stele is the theorem prover",
])
def test_provenance_no_forbidden_phrase(phrase):
    assert phrase.lower() not in _provenance().lower(), \
        f"Forbidden phrase {phrase!r} found in docs/provenance-map.md"


# ── 6. No private PDF bundling claims ────────────────────────────────────────

def test_references_no_pdf_bundle_claim():
    doc = _references().lower()
    assert "bundled in the public" not in doc or "not bundled in the public" in doc, \
        "docs/references.md must not claim PDFs are bundled in the public repo"


# ── 7. No runtime dependency hints ───────────────────────────────────────────

def test_references_no_runtime_deps():
    doc = _references().lower()
    for dep in ["import numpy", "import scipy", "import torch", "import tensorflow"]:
        assert dep not in doc, \
            f"docs/references.md must not reference runtime ML deps: {dep!r}"


# ── 8. Companion link integrity ───────────────────────────────────────────────

def test_foundations_links_to_provenance_map():
    html = (pathlib.Path(_ROOT) / "site" / "foundations.html").read_text(encoding="utf-8")
    assert "provenance-map" in html, \
        "site/foundations.html must link to docs/provenance-map.md"


def test_foundations_links_to_references_doc():
    html = (pathlib.Path(_ROOT) / "site" / "foundations.html").read_text(encoding="utf-8")
    assert "references.md" in html, \
        "site/foundations.html must link to docs/references.md"


def test_foundations_program_links_to_provenance_map():
    doc = (_DOCS / "foundations-program.md").read_text(encoding="utf-8")
    assert "provenance-map" in doc, \
        "docs/foundations-program.md must reference provenance-map.md"


def test_foundations_program_links_to_references():
    doc = (_DOCS / "foundations-program.md").read_text(encoding="utf-8")
    assert "references.md" in doc, \
        "docs/foundations-program.md must reference references.md"
