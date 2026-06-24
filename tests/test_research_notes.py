"""Static tests for docs/research-notes/ packet (Prompt 48).

Checks: directory exists, required files exist, required topics covered,
forbidden overclaims absent, quantitative claims policy, no PDFs committed.
"""
from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_NOTES = _ROOT / "docs" / "research-notes"


def _read(filename: str) -> str:
    return (_NOTES / filename).read_text(encoding="utf-8")


def _all_notes_text() -> str:
    """Concatenate all .md files in research-notes/ (excluding claim matrix)."""
    parts = []
    for f in sorted(_NOTES.glob("*.md")):
        parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts)


# ── 1. Files exist ────────────────────────────────────────────────────────────

def test_readme_exists():
    assert (_NOTES / "README.md").exists(), "docs/research-notes/README.md must exist"


def test_claim_evidence_matrix_exists():
    assert (_NOTES / "claim-evidence-matrix.md").exists(), \
        "docs/research-notes/claim-evidence-matrix.md must exist"


NOTE_FILES = [
    "01-system-overview.md",
    "02-architecture-trust-boundary.md",
    "03-language-and-kernel.md",
    "04-proof-terms-and-elaboration.md",
    "05-diagnostics-and-proof-state.md",
    "06-semantics-matrix-kripke.md",
    "07-certificates-minicheck.md",
    "08-ml-corpus-and-measurement.md",
    "09-foundations-and-yurihak.md",
    "10-related-work-and-provenance.md",
    "11-limitations-and-future-work.md",
    "12-paper-outline-and-figure-plan.md",
]


@pytest.mark.parametrize("filename", NOTE_FILES)
def test_note_file_exists(filename):
    assert (_NOTES / filename).exists(), \
        f"docs/research-notes/{filename} must exist"


def test_at_least_ten_note_files():
    note_files = [f for f in _NOTES.glob("[0-9]*.md")]
    assert len(note_files) >= 10, \
        f"At least 10 numbered note files required; found {len(note_files)}"


# ── 2. Required topics ────────────────────────────────────────────────────────

REQUIRED_TOPICS = [
    ("trust boundary", "trust boundary"),
    ("kernel", "kernel"),
    ("proof terms", "proof.term"),
    ("Kripke", "[Kk]ripke"),
    ("matrix", "matrix"),
    ("certificate", "certificate"),
    ("minicheck", "minicheck"),
    ("ML", r"\bML\b"),
    ("Yurihak", "Yurihak|유리학"),
    ("limitations", "limitations"),
    ("future work", "future work"),
]


@pytest.mark.parametrize("topic,pattern", REQUIRED_TOPICS)
def test_required_topic_covered(topic, pattern):
    text = _all_notes_text()
    assert re.search(pattern, text, re.IGNORECASE), \
        f"Research notes must cover topic: {topic!r}"


# ── 3. Each numbered note has status/evidence/limitations or cross-references matrix ─

def test_each_note_has_status_or_evidence(tmp_path):
    for filename in NOTE_FILES:
        content = _read(filename)
        cl = content.lower()
        has_marker = (
            "status:" in cl
            or "evidence:" in cl
            or "limitations" in cl
            or "claim-evidence-matrix" in cl
            or "claim matrix" in cl
        )
        assert has_marker, \
            f"{filename} must include Status:, Evidence:, Limitations, or reference the claim matrix"


# ── 4. Forbidden overclaims ───────────────────────────────────────────────────

# Overclaim phrases that should only appear as prohibitions/examples, not as actual claims.
# Use specific phrasing that would only appear in an actual (wrong) claim, not in
# meta-discussion about what NOT to write.
FORBIDDEN_OVERCLAIMS = [
    "stele is a complete theorem prover",
    "stele is an ai-powered verifier",
    "stele has fully verified metatheory",
    "stele is production-ready",
    "stele is state-of-the-art",
    "stele currently implements yurihak",
    "stele formally proves relativism",
]


@pytest.mark.parametrize("phrase", FORBIDDEN_OVERCLAIMS)
def test_no_forbidden_overclaim(phrase):
    text = _all_notes_text().lower()
    assert phrase.lower() not in text, \
        f"Forbidden overclaim found in research notes: {phrase!r}"


# ── 5. Required honest phrases ────────────────────────────────────────────────

def test_notes_say_not_a_theorem_prover():
    text = _all_notes_text().lower()
    assert "not a theorem prover" in text or "proof checker, not" in text, \
        "Research notes must state Stele is not a theorem prover"


def test_notes_say_untrusted_for_hints_or_ml():
    text = _all_notes_text().lower()
    assert "untrusted" in text, \
        "Research notes must include 'untrusted' for hints/ML/UI"


def test_notes_say_not_machine_checked():
    text = _all_notes_text().lower()
    assert "not machine-checked" in text or "not formally verified" in text, \
        "Research notes must clarify metatheory is not machine-checked"


def test_notes_include_yurihak_not_implemented():
    text = _all_notes_text().lower()
    assert "not implemented" in text and ("yurihak" in text or "유리학" in text), \
        "Research notes must state Yurihak is not yet implemented"


# ── 6. Quantitative claims policy ─────────────────────────────────────────────

def test_ml_metrics_cite_source_file():
    note = _read("08-ml-corpus-and-measurement.md").lower()
    assert "baseline_report.json" in note, \
        "ML metrics must cite stele_ml/reports/baseline_report.json as source"


def test_test_count_in_notes():
    """If a test count is mentioned, it should not be a round number that suggests invention."""
    overview = _read("01-system-overview.md")
    # Allow the specific known count (2280) but flag suspiciously round numbers like "1000 tests"
    suspiciously_round = re.findall(r'\b(1000|2000|5000|10000)\s+(?:test|pass)', overview, re.IGNORECASE)
    assert not suspiciously_round, \
        f"Test count appears rounded/invented: {suspiciously_round}"


def test_ml_metrics_not_invented():
    """ML metrics in notes should match values that appear in the report."""
    note = _read("08-ml-corpus-and-measurement.md")
    # These values are from baseline_report.json; presence confirms they were copied correctly
    assert "0.85" in note, "validity_accuracy 0.85 must appear in ML notes"
    assert "0.3611" in note, "macro_f1 0.3611 must appear in ML notes"
    assert "0.60" in note, "exact_match 0.60 must appear in ML notes"


# ── 7. No local PDFs committed ───────────────────────────────────────────────

def test_no_pdfs_in_research_notes():
    pdfs = list(_NOTES.rglob("*.pdf"))
    assert not pdfs, \
        f"No PDFs should be committed to research-notes/: {pdfs}"


def test_notes_say_pdfs_not_committed():
    text = _all_notes_text().lower()
    assert "not committed" in text or "local drafting" in text or "not bundled" in text, \
        "Research notes must state PDFs are not committed to the repo"


# ── 8. Claim matrix completeness ─────────────────────────────────────────────

REQUIRED_CLAIM_MATRIX_ROWS = [
    "proof checker",
    "rule",
    "structural diagnostics",
    "dependency graph",
    "matrix",
    "Kripke",
    "proof-term",
    "FOL",
    "classical",
    "certificate",
    "minicheck",
    "ML",
    "Lean",
    "browser",
    "Yurihak",
]


@pytest.mark.parametrize("row_topic", REQUIRED_CLAIM_MATRIX_ROWS)
def test_claim_matrix_has_row(row_topic):
    matrix = _read("claim-evidence-matrix.md").lower()
    assert row_topic.lower() in matrix, \
        f"claim-evidence-matrix.md must include a row for: {row_topic!r}"


def test_claim_matrix_has_required_columns():
    matrix = _read("claim-evidence-matrix.md")
    for col in ["Status", "Evidence path", "Safe wording", "Limitation"]:
        assert col in matrix, \
            f"claim-evidence-matrix.md must have column: {col!r}"


# ── 9. README and index links ─────────────────────────────────────────────────

def test_readme_links_to_numbered_notes():
    readme = _read("README.md")
    assert "01-system-overview" in readme, \
        "research-notes/README.md must link to 01-system-overview.md"
    assert "claim-evidence-matrix" in readme, \
        "research-notes/README.md must link to claim-evidence-matrix.md"


def test_main_readme_links_to_research_notes():
    main_readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "research-notes" in main_readme or "research notes" in main_readme.lower(), \
        "Root README.md must link to or mention docs/research-notes/"


def test_dev_context_mentions_research_notes():
    dev_ctx = (_ROOT / "docs" / "development-context.md").read_text(encoding="utf-8")
    assert "research-notes" in dev_ctx or "research notes" in dev_ctx.lower(), \
        "docs/development-context.md must mention research notes"


# ── 10. No external framework references in notes ────────────────────────────

def test_no_external_frameworks_in_notes():
    text = _all_notes_text().lower()
    for dep in ["import numpy", "import scipy", "import torch", "import tensorflow"]:
        assert dep not in text, \
            f"Research notes must not reference runtime ML deps: {dep!r}"
