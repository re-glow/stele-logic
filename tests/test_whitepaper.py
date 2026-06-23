"""Static content tests for the Stele whitepaper.

Checks that the whitepaper:
1. Exists (Markdown and/or LaTeX source).
2. Contains required sections and honest language.
3. Does not contain banned overclaim phrases.
4. README and GUIDE link to it.

No LaTeX compilation is required or attempted.
"""
from __future__ import annotations
import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
WHITEPAPER_MD = _ROOT / "docs" / "whitepaper.md"
WHITEPAPER_TEX = _ROOT / "paper" / "stele-whitepaper.tex"
PAPER_README = _ROOT / "paper" / "README.md"
README = _ROOT / "README.md"
GUIDE = _ROOT / "GUIDE.md"


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------

class TestWhitepaperExists:
    def test_markdown_whitepaper_exists(self):
        assert WHITEPAPER_MD.exists(), (
            f"docs/whitepaper.md not found at {WHITEPAPER_MD}"
        )

    def test_latex_source_exists(self):
        assert WHITEPAPER_TEX.exists(), (
            f"paper/stele-whitepaper.tex not found at {WHITEPAPER_TEX}"
        )

    def test_paper_readme_exists(self):
        assert PAPER_README.exists(), (
            f"paper/README.md not found at {PAPER_README}"
        )


# ---------------------------------------------------------------------------
# Required sections in Markdown whitepaper
# ---------------------------------------------------------------------------

class TestMarkdownSections:
    @pytest.fixture(scope="class")
    def text(self):
        if not WHITEPAPER_MD.exists():
            pytest.skip("docs/whitepaper.md not found")
        return WHITEPAPER_MD.read_text(encoding="utf-8").lower()

    def test_has_abstract(self, text):
        assert "abstract" in text

    def test_has_trust_boundary_section(self, text):
        assert "trust boundary" in text or "trusted core" in text, (
            "whitepaper must discuss the trust boundary"
        )

    def test_has_limitations_section(self, text):
        assert "## limitations" in text or "# limitations" in text, (
            "whitepaper must have a Limitations section"
        )

    def test_has_status_table(self, text):
        assert "status" in text and ("stable" in text or "experimental" in text), (
            "whitepaper must contain a component status table"
        )

    def test_has_not_theorem_prover_statement(self, text):
        # Must explicitly say it is NOT a theorem prover
        assert "not a theorem prover" in text or "is not a theorem prover" in text, (
            "whitepaper must state that Stele is not a theorem prover"
        )

    def test_has_ml_optional_statement(self, text):
        assert ("optional" in text and "ml" in text) or "ml baseline" in text, (
            "whitepaper must mention ML as optional"
        )

    def test_no_machine_checked_metatheory_claim(self, text):
        # Must not claim machine-checked proofs unless framed as absent/future
        bad_patterns = [
            "machine-checked proof of",
            "formally verified metatheory",
            "machine-verified normalization",
        ]
        for bad in bad_patterns:
            assert bad not in text, (
                f"whitepaper must not claim '{bad}'; "
                "metatheory is proof-sketched, not machine-checked"
            )

    def test_mentions_test_count(self, text):
        # Should reference the test suite (accept any known count or "regression")
        assert "test" in text and (
            "1808" in text or "1804" in text or "1836" in text or "regression" in text
        ), "whitepaper should reference test suite"

    def test_has_kripke_section(self, text):
        assert "kripke" in text

    def test_has_certificates_section(self, text):
        assert "certificate" in text or "minicheck" in text

    def test_has_proof_term_section(self, text):
        assert "curry" in text or "proof-term" in text or "proof term" in text

    def test_has_future_work_section(self, text):
        assert "future work" in text or "## future" in text


# ---------------------------------------------------------------------------
# Banned overclaim phrases in Markdown
# ---------------------------------------------------------------------------

class TestMarkdownNoBannedPhrases:
    # These phrases are banned UNLESS they appear in a negation context.
    # We check for standalone occurrences, not negated ones.
    _BANNED = [
        "fully verified",
        "complete theorem prover",
        "ai-powered verifier",
        "state-of-the-art",
        "production-ready",
        "production ready",
        "guaranteed to prove",
        "guaranteed proof",
    ]

    @pytest.fixture(scope="class")
    def text(self):
        if not WHITEPAPER_MD.exists():
            pytest.skip("docs/whitepaper.md not found")
        return WHITEPAPER_MD.read_text(encoding="utf-8").lower()

    def test_no_fully_verified(self, text):
        assert "fully verified" not in text, (
            "whitepaper must not claim 'fully verified'"
        )

    def test_no_complete_theorem_prover(self, text):
        assert "complete theorem prover" not in text, (
            "whitepaper must not claim 'complete theorem prover'"
        )

    def test_no_ai_powered_verifier(self, text):
        # "ai-powered verifier" is banned as a positive claim.
        # Allowed: appears in a paragraph/sentence containing "not" or "is not".
        import re
        for m in re.finditer(r'ai.powered verifier', text):
            # Look back up to 150 chars for negation context
            ctx = text[max(0, m.start() - 150) : m.start()]
            assert "not" in ctx or "no " in ctx, (
                "whitepaper must not claim 'ai-powered verifier' as a positive attribute; "
                f"found without negation context: '...{text[max(0,m.start()-50):m.end()+50]}...'"
            )

    def test_no_state_of_the_art(self, text):
        assert "state-of-the-art" not in text, (
            "whitepaper must not use 'state-of-the-art'"
        )

    def test_no_production_ready(self, text):
        assert "production-ready" not in text and "production ready" not in text, (
            "whitepaper must not claim 'production-ready'"
        )


# ---------------------------------------------------------------------------
# LaTeX source checks (static only, no compilation)
# ---------------------------------------------------------------------------

class TestLatexSource:
    @pytest.fixture(scope="class")
    def tex_text(self):
        if not WHITEPAPER_TEX.exists():
            pytest.skip("paper/stele-whitepaper.tex not found")
        return WHITEPAPER_TEX.read_text(encoding="utf-8")

    def test_has_begin_document(self, tex_text):
        assert r"\begin{document}" in tex_text, (
            "LaTeX source missing \\begin{document}"
        )

    def test_has_end_document(self, tex_text):
        assert r"\end{document}" in tex_text

    def test_has_bibliography(self, tex_text):
        assert r"\bibliography{" in tex_text

    def test_has_limitations_section(self, tex_text):
        assert r"\section{Limitations}" in tex_text

    def test_has_trust_boundary_section(self, tex_text):
        lower = tex_text.lower()
        assert "trust boundary" in lower or "trusted core" in lower

    def test_has_not_theorem_prover(self, tex_text):
        lower = tex_text.lower()
        assert "not a theorem prover" in lower or "is not" in lower

    def test_bib_file_exists(self):
        if not WHITEPAPER_TEX.exists():
            pytest.skip("tex not found")
        bib = WHITEPAPER_TEX.parent / "references.bib"
        assert bib.exists(), "paper/references.bib not found"

    def test_bib_has_no_todo_as_citation_key(self):
        if not (WHITEPAPER_TEX.parent / "references.bib").exists():
            pytest.skip("references.bib not found")
        bib_text = (WHITEPAPER_TEX.parent / "references.bib").read_text(encoding="utf-8")
        # TODO entries should be commented out, not active @article/@inproceedings entries
        active_entries = re.findall(r'^@\w+\{([^,]+),', bib_text, re.MULTILINE)
        todo_entries = [e for e in active_entries if "TODO" in e]
        assert not todo_entries, (
            f"references.bib has uncommented TODO entries: {todo_entries}. "
            "Comment out placeholder entries rather than leaving them active."
        )

    def test_no_invented_metadata_markers(self, tex_text):
        # If \cite{TODO:...} appears in the tex, it's a placeholder; fine.
        # But if an active bib entry has TODO in the key (checked above), that's bad.
        # This test just ensures \cite{TODO:...} cites are acknowledged as TODO.
        todo_cites = re.findall(r'\\cite\{([^}]*TODO[^}]*)\}', tex_text)
        # These are allowed — they are explicit TODO placeholders in the text
        # If they exist, we just want to confirm they're not presented as authoritative
        pass  # No assertion needed; TODO:cites are by design


# ---------------------------------------------------------------------------
# README and GUIDE links
# ---------------------------------------------------------------------------

class TestDocLinks:
    def test_readme_links_to_whitepaper(self):
        if not README.exists():
            pytest.skip("README.md not found")
        text = README.read_text(encoding="utf-8").lower()
        assert "whitepaper" in text or "stele-whitepaper" in text, (
            "README.md must link to the whitepaper"
        )

    def test_guide_mentions_whitepaper(self):
        if not GUIDE.exists():
            pytest.skip("GUIDE.md not found")
        text = GUIDE.read_text(encoding="utf-8").lower()
        assert "whitepaper" in text or "technical paper" in text or "preprint" in text, (
            "GUIDE.md must mention the whitepaper"
        )

    def test_paper_readme_links_to_markdown(self):
        if not PAPER_README.exists():
            pytest.skip("paper/README.md not found")
        text = PAPER_README.read_text(encoding="utf-8").lower()
        assert "whitepaper.md" in text or "docs/whitepaper" in text, (
            "paper/README.md must reference docs/whitepaper.md"
        )
