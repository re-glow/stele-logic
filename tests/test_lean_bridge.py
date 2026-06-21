"""Tests for stele_lean — Lean 4 bridge.

Part A: Formula export (no Lean required)
Part B: Theorem-type extraction and skeleton generation (no Lean required)
Part C: Lean name sanitization (no Lean required)
Part D: Free-variable collection (no Lean required)
Part E: Lean stderr parsing (no Lean required)
Part F: LeanCheckResult and LeanDiagnostic data model (no Lean required)
Part G: Lean availability helper and unavailable-path (no Lean required)
Part H: Import isolation — stele/ must not import stele_lean (no Lean required)
Part I: Lean-dependent checks (skipped if Lean not on PATH)

All tests in Parts A-H pass without Lean installed.
"""
import pathlib
import shutil
import sys

import pytest

# ---------------------------------------------------------------------------
# Root path setup
# ---------------------------------------------------------------------------
_ROOT = pathlib.Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Lean availability marker (used for Parts I)
# ---------------------------------------------------------------------------
_lean_available = shutil.which("lean") is not None
lean_required = pytest.mark.skipif(
    not _lean_available,
    reason="Lean 4 not installed — test requires 'lean' on PATH",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
from stele.ast import Var, Op  # noqa: E402


def _var(name):
    return Var(name)


def _imp(a, b):
    return Op("imp", (a, b))


def _and(a, b):
    return Op("and", (a, b))


def _or(a, b):
    return Op("or", (a, b))


def _not(a):
    return Op("not", (a,))


def _bot():
    return Op("bot", ())


# ===========================================================================
# Part A — Formula export (no Lean required)
# ===========================================================================

class TestFormulaToLean:
    """Tests for stele_lean.export.formula_to_lean."""

    def test_var(self):
        from stele_lean.export import formula_to_lean
        assert formula_to_lean(_var("P")) == "P"

    def test_var_multi_char(self):
        from stele_lean.export import formula_to_lean
        assert formula_to_lean(_var("Alpha")) == "Alpha"

    def test_bot(self):
        from stele_lean.export import formula_to_lean
        assert formula_to_lean(_bot()) == "False"

    def test_not_var(self):
        from stele_lean.export import formula_to_lean
        assert formula_to_lean(_not(_var("P"))) == "¬P"

    def test_not_compound(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_not(_and(_var("P"), _var("Q"))))
        assert result == "¬(P ∧ Q)"

    def test_not_not(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_not(_not(_var("P"))))
        assert result == "¬¬P"

    def test_imp_vars(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_imp(_var("P"), _var("Q")))
        assert result == "P → Q"

    def test_imp_right_assoc(self):
        from stele_lean.export import formula_to_lean
        # P → Q → R  (right-associative, inner imp not extra-parenthesized)
        result = formula_to_lean(_imp(_var("P"), _imp(_var("Q"), _var("R"))))
        assert result == "P → Q → R"

    def test_imp_left_compound(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_imp(_and(_var("P"), _var("Q")), _var("R")))
        assert result == "(P ∧ Q) → R"

    def test_and_vars(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_and(_var("P"), _var("Q")))
        assert result == "P ∧ Q"

    def test_and_nested(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_and(_and(_var("P"), _var("Q")), _var("R")))
        assert result == "(P ∧ Q) ∧ R"

    def test_or_vars(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_or(_var("P"), _var("Q")))
        assert result == "P ∨ Q"

    def test_mixed_and_or(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_or(_and(_var("P"), _var("Q")), _var("R")))
        assert result == "(P ∧ Q) ∨ R"

    def test_imp_with_or_right(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_imp(_var("P"), _or(_var("Q"), _var("R"))))
        assert result == "P → (Q ∨ R)"

    def test_not_false(self):
        from stele_lean.export import formula_to_lean
        result = formula_to_lean(_not(_bot()))
        assert result == "¬False"

    def test_dne_formula(self):
        from stele_lean.export import formula_to_lean
        # not not P -> P
        dne = _imp(_not(_not(_var("P"))), _var("P"))
        result = formula_to_lean(dne)
        assert result == "¬¬P → P"

    def test_unsupported_op_raises(self):
        from stele_lean.export import formula_to_lean, ExportError
        unsupported = Op("xor", (_var("P"), _var("Q")))
        with pytest.raises(ExportError, match="xor"):
            formula_to_lean(unsupported)


# ===========================================================================
# Part B — Theorem type extraction and skeleton (no Lean required)
# ===========================================================================

class TestTheoremSkeleton:
    """Tests for extract_theorem_type and theorem_to_lean_skeleton."""

    def _parse(self, text):
        from stele.parser import parse_theorem
        return parse_theorem(text)

    def test_extract_type_mp(self):
        from stele_lean.export import extract_theorem_type, formula_to_lean
        thm = self._parse(
            "theorem mp:\n  assume h1: P -> Q\n  assume h2: P\n  have hq: Q by mp h1 h2\n  conclude Q by hq\n"
        )
        typ = extract_theorem_type(thm)
        lean_str = formula_to_lean(typ)
        assert "→" in lean_str
        assert "Q" in lean_str

    def test_extract_type_dne(self):
        from stele_lean.export import extract_theorem_type, formula_to_lean
        thm = self._parse(
            "theorem dne:\n  assume h1: not not P\n  have h2: P by dne h1\n  conclude P by h2\n"
        )
        typ = extract_theorem_type(thm)
        lean_str = formula_to_lean(typ)
        # ¬¬P → P
        assert "¬¬P" in lean_str
        assert "→ P" in lean_str

    def test_extract_type_no_assumes(self):
        from stele_lean.export import extract_theorem_type, formula_to_lean
        # imp_self: suppose h1; conclude P -> P
        thm = self._parse(
            "theorem imp_self:\n  suppose h1: P\n    have h2: P by copy h1\n  have h3: P -> P by imp_intro h1 h2\n  conclude P -> P by h3\n"
        )
        typ = extract_theorem_type(thm)
        lean_str = formula_to_lean(typ)
        assert lean_str == "P → P"

    def test_skeleton_contains_sorry(self):
        from stele_lean.export import theorem_to_lean_skeleton
        thm = self._parse(
            "theorem mp:\n  assume h1: P -> Q\n  assume h2: P\n  have hq: Q by mp h1 h2\n  conclude Q by hq\n"
        )
        skeleton = theorem_to_lean_skeleton(thm)
        assert "sorry" in skeleton

    def test_skeleton_variable_decl(self):
        from stele_lean.export import theorem_to_lean_skeleton
        thm = self._parse(
            "theorem mp:\n  assume h1: P -> Q\n  assume h2: P\n  have hq: Q by mp h1 h2\n  conclude Q by hq\n"
        )
        skeleton = theorem_to_lean_skeleton(thm)
        assert "variable" in skeleton
        assert "Prop" in skeleton
        assert "P" in skeleton
        assert "Q" in skeleton

    def test_skeleton_theorem_keyword(self):
        from stele_lean.export import theorem_to_lean_skeleton
        thm = self._parse(
            "theorem my_thm:\n  assume h1: P\n  conclude P by h1\n"
        )
        skeleton = theorem_to_lean_skeleton(thm)
        assert "theorem my_thm" in skeleton

    def test_skeleton_no_conclude_raises(self):
        from stele_lean.export import extract_theorem_type, ExportError
        from stele.proof import Theorem, Assume
        from stele.ast import Var
        thm = Theorem(name="t", logic="classical_prop", lines=(
            Assume(label="h1", formula=Var("P"), line=1),
        ))
        with pytest.raises(ExportError, match="conclude"):
            extract_theorem_type(thm)

    def test_skeleton_logic_header(self):
        from stele_lean.export import theorem_to_lean_skeleton
        thm = self._parse(
            "theorem t using classical_prop:\n  assume h1: P\n  conclude P by h1\n"
        )
        skeleton = theorem_to_lean_skeleton(thm, logic_name="classical_prop")
        assert "classical_prop" in skeleton

    def test_skeleton_gen_comment_header(self):
        from stele_lean.export import theorem_to_lean_skeleton
        thm = self._parse(
            "theorem t:\n  assume h1: P\n  conclude P by h1\n"
        )
        skeleton = theorem_to_lean_skeleton(thm)
        assert "Generated by stele_lean" in skeleton

    def test_dne_file_export(self):
        from stele_lean.export import theorem_to_lean_skeleton
        dne_path = _ROOT / "examples" / "dne.stele"
        if not dne_path.exists():
            pytest.skip("examples/dne.stele not found")
        from stele.parser import parse_theorem
        text = dne_path.read_text(encoding="utf-8")
        thm = parse_theorem(text)
        skeleton = theorem_to_lean_skeleton(thm)
        assert "¬¬P → P" in skeleton or ("¬¬" in skeleton and "P" in skeleton)

    def test_and_demo_export(self):
        from stele_lean.export import theorem_to_lean_skeleton
        thm = self._parse(
            "theorem and_demo:\n  assume h1: P\n  assume h2: Q\n  have h3: P and Q by and_intro h1 h2\n  conclude Q by h5\n"
        )
        skeleton = theorem_to_lean_skeleton(thm)
        assert "P" in skeleton
        assert "Q" in skeleton


# ===========================================================================
# Part C — Lean name sanitization (no Lean required)
# ===========================================================================

class TestSanitizeLeanName:
    def test_plain_ascii(self):
        from stele_lean.export import sanitize_lean_name
        assert sanitize_lean_name("mp") == "mp"

    def test_underscore_preserved(self):
        from stele_lean.export import sanitize_lean_name
        assert sanitize_lean_name("dne_law") == "dne_law"

    def test_hyphen_replaced(self):
        from stele_lean.export import sanitize_lean_name
        assert sanitize_lean_name("my-theorem") == "my_theorem"

    def test_digit_start_prefixed(self):
        from stele_lean.export import sanitize_lean_name
        result = sanitize_lean_name("1bad")
        assert result.startswith("s_")

    def test_empty_string(self):
        from stele_lean.export import sanitize_lean_name
        result = sanitize_lean_name("")
        assert result == "unnamed"

    def test_spaces_replaced(self):
        from stele_lean.export import sanitize_lean_name
        result = sanitize_lean_name("a theorem")
        assert " " not in result


# ===========================================================================
# Part D — Free-variable collection (no Lean required)
# ===========================================================================

class TestCollectFreeVars:
    def test_single_var(self):
        from stele_lean.export import collect_free_vars
        assert collect_free_vars(_var("P")) == ["P"]

    def test_no_vars_in_bot(self):
        from stele_lean.export import collect_free_vars
        assert collect_free_vars(_bot()) == []

    def test_imp_two_vars(self):
        from stele_lean.export import collect_free_vars
        result = collect_free_vars(_imp(_var("P"), _var("Q")))
        assert result == ["P", "Q"]

    def test_dedup(self):
        from stele_lean.export import collect_free_vars
        # P → P should yield ["P"] not ["P", "P"]
        result = collect_free_vars(_imp(_var("P"), _var("P")))
        assert result == ["P"]

    def test_order_of_appearance(self):
        from stele_lean.export import collect_free_vars
        result = collect_free_vars(_and(_var("Q"), _var("P")))
        assert result == ["Q", "P"]

    def test_nested(self):
        from stele_lean.export import collect_free_vars
        f = _imp(_and(_var("P"), _var("Q")), _or(_var("Q"), _var("R")))
        result = collect_free_vars(f)
        assert result == ["P", "Q", "R"]
        assert result.count("Q") == 1


# ===========================================================================
# Part E — Lean stderr parsing (no Lean required)
# ===========================================================================

_SAMPLE_LEAN_STDERR_ERROR = """\
/tmp/stele_test.lean:7:8: error: type mismatch
  term
    h
  has type
    P : Prop
  but is expected to have type
    Q : Prop
"""

_SAMPLE_LEAN_STDERR_SORRY = """\
/tmp/stele_mp.lean:14:12: warning: declaration uses 'sorry'
"""

_SAMPLE_LEAN_STDERR_MIXED = """\
/tmp/stele_bad.lean:3:0: error: unknown identifier 'Foo'
/tmp/stele_bad.lean:5:2: warning: declaration uses 'sorry'
"""

_SAMPLE_LEAN_STDERR_INFO = """\
/tmp/stele_test.lean:1:0: info: file OK
"""


class TestParseLeanOutput:
    def test_error_parsed(self):
        from stele_lean.diagnostics import parse_lean_output
        diags = parse_lean_output(_SAMPLE_LEAN_STDERR_ERROR)
        assert len(diags) == 1
        d = diags[0]
        assert d.code == "LeanTypeError"
        assert d.severity == "error"
        assert d.line == 7
        assert d.col == 8
        assert "type mismatch" in d.message

    def test_sorry_warning_parsed(self):
        from stele_lean.diagnostics import parse_lean_output
        diags = parse_lean_output(_SAMPLE_LEAN_STDERR_SORRY)
        assert len(diags) == 1
        d = diags[0]
        assert d.code == "LeanWarning"
        assert d.severity == "warning"
        assert "sorry" in d.message

    def test_mixed_error_and_warning(self):
        from stele_lean.diagnostics import parse_lean_output
        diags = parse_lean_output(_SAMPLE_LEAN_STDERR_MIXED)
        assert len(diags) == 2
        codes = [d.code for d in diags]
        assert "LeanTypeError" in codes
        assert "LeanWarning" in codes

    def test_info_parsed(self):
        from stele_lean.diagnostics import parse_lean_output
        diags = parse_lean_output(_SAMPLE_LEAN_STDERR_INFO)
        assert len(diags) == 1
        assert diags[0].code == "LeanInfo"
        assert diags[0].severity == "info"

    def test_empty_string(self):
        from stele_lean.diagnostics import parse_lean_output
        assert parse_lean_output("") == []

    def test_no_match_plain_text(self):
        from stele_lean.diagnostics import parse_lean_output
        assert parse_lean_output("compilation complete") == []

    def test_file_path_captured(self):
        from stele_lean.diagnostics import parse_lean_output
        diags = parse_lean_output(_SAMPLE_LEAN_STDERR_ERROR)
        assert "/tmp/stele_test.lean" in diags[0].file

    def test_raw_field_preserved(self):
        from stele_lean.diagnostics import parse_lean_output
        diags = parse_lean_output(_SAMPLE_LEAN_STDERR_SORRY)
        assert "warning" in diags[0].raw

    def test_diagnostic_is_frozen(self):
        from stele_lean.diagnostics import parse_lean_output, LeanDiagnostic
        diags = parse_lean_output(_SAMPLE_LEAN_STDERR_ERROR)
        assert len(diags) == 1
        with pytest.raises((AttributeError, TypeError)):
            diags[0].message = "new"  # type: ignore


# ===========================================================================
# Part F — LeanCheckResult data model (no Lean required)
# ===========================================================================

class TestLeanCheckResult:
    def _make_result(self, diagnostics=None, returncode=0, available=True):
        from stele_lean.diagnostics import LeanCheckResult
        return LeanCheckResult(
            available=available,
            returncode=returncode,
            stdout="",
            stderr="",
            diagnostics=diagnostics or [],
        )

    def _make_diag(self, severity, message="msg"):
        from stele_lean.diagnostics import LeanDiagnostic
        return LeanDiagnostic(
            code="LeanTypeError" if severity == "error" else "LeanWarning",
            message=message,
            file="test.lean",
            line=1,
            col=0,
            severity=severity,
            raw="",
        )

    def test_no_errors_empty(self):
        result = self._make_result()
        assert not result.has_errors

    def test_has_errors_with_error(self):
        result = self._make_result([self._make_diag("error")])
        assert result.has_errors

    def test_lean_type_errors_filter(self):
        from stele_lean.diagnostics import LeanDiagnostic
        error_d = self._make_diag("error")
        warn_d = self._make_diag("warning", "sorry")
        result = self._make_result([error_d, warn_d])
        assert len(result.lean_type_errors) == 1
        assert result.lean_type_errors[0].severity == "error"

    def test_has_sorry_warning(self):
        warn_d = self._make_diag("warning", "declaration uses 'sorry'")
        result = self._make_result([warn_d])
        assert result.has_sorry_warning

    def test_summary_unavailable(self):
        result = self._make_result(available=False)
        assert "not available" in result.summary().lower() or "Lean" in result.summary()

    def test_summary_ok(self):
        result = self._make_result(returncode=0)
        assert "OK" in result.summary()

    def test_summary_with_error(self):
        result = self._make_result([self._make_diag("error")], returncode=1)
        assert "error" in result.summary()


# ===========================================================================
# Part G — Lean availability (no Lean required for the "unavailable" test)
# ===========================================================================

class TestLeanAvailability:
    def test_lean_available_returns_bool(self):
        from stele_lean.check import lean_available
        result = lean_available()
        assert isinstance(result, bool)

    def test_check_lean_unavailable_graceful(self, monkeypatch):
        """When lean not on PATH, check_lean_file returns available=False."""
        monkeypatch.setattr("shutil.which", lambda name: None)
        from stele_lean.check import check_lean_file
        import importlib
        import stele_lean.check as c
        monkeypatch.setattr(c, "lean_available", lambda: False)
        result = c.check_lean_file("nonexistent.lean")
        assert result.available is False
        assert result.returncode is None
        assert result.diagnostics == []

    def test_lean_available_consistent_with_shutil(self):
        from stele_lean.check import lean_available
        expected = shutil.which("lean") is not None
        assert lean_available() == expected


# ===========================================================================
# Part H — Import isolation (no Lean required)
# ===========================================================================

_STELE_MODULES = [
    "stele.ast",
    "stele.proof",
    "stele.parser",
    "stele.logic",
    "stele.kernel",
    "stele.matrix",
    "stele.world",
    "stele.diagnostics",
]


class TestImportIsolation:
    def test_stele_does_not_import_stele_lean(self):
        """None of the trusted stele/ modules should reference stele_lean."""
        import importlib
        stele_src = _ROOT / "stele"
        for mod_name in _STELE_MODULES:
            mod = importlib.import_module(mod_name)
            src_path = pathlib.Path(mod.__file__) if hasattr(mod, "__file__") else None
            if src_path is None or not src_path.exists():
                continue
            src = src_path.read_text(encoding="utf-8")
            assert "stele_lean" not in src, (
                f"{mod_name} must not reference stele_lean — "
                "trust boundary must not import the Lean bridge"
            )

    def test_kernel_has_no_lean_reference(self):
        """kernel.py must not reference lean, subprocess, or stele_lean."""
        kernel_path = _ROOT / "stele" / "kernel.py"
        assert kernel_path.exists(), "stele/kernel.py not found"
        src = kernel_path.read_text(encoding="utf-8")
        for forbidden in ("stele_lean", "subprocess", "lean"):
            assert forbidden not in src, (
                f"kernel.py must not contain '{forbidden}' — "
                "kernel is trusted, synchronous, and subprocess-free"
            )

    def test_stele_lean_imports_cleanly(self):
        import stele_lean
        import stele_lean.export
        import stele_lean.diagnostics
        import stele_lean.check

    def test_stele_lean_version_defined(self):
        import stele_lean
        assert hasattr(stele_lean, "__version__")
        assert stele_lean.__version__

    def test_stele_lean_supported_ops(self):
        import stele_lean
        assert hasattr(stele_lean, "SUPPORTED_OPS")
        assert "imp" in stele_lean.SUPPORTED_OPS
        assert "and" in stele_lean.SUPPORTED_OPS
        assert "or" in stele_lean.SUPPORTED_OPS
        assert "not" in stele_lean.SUPPORTED_OPS
        assert "bot" in stele_lean.SUPPORTED_OPS


# ===========================================================================
# Part I — Lean-dependent tests (skipped if Lean not on PATH)
# ===========================================================================

@lean_required
class TestLeanIntegration:
    """Tests that require Lean 4 to be installed."""

    def test_check_lean_valid_file(self):
        from stele_lean.check import check_lean_file
        example_path = _ROOT / "stele_lean" / "examples" / "mp_valid.lean"
        assert example_path.exists(), "mp_valid.lean example not found"
        result = check_lean_file(example_path)
        assert result.available is True
        # Valid file with sorry → no type errors (only sorry warning)
        assert not result.has_errors

    def test_check_lean_type_error_file(self):
        from stele_lean.check import check_lean_file
        error_path = _ROOT / "stele_lean" / "examples" / "type_error.lean"
        assert error_path.exists(), "type_error.lean example not found"
        result = check_lean_file(error_path)
        assert result.available is True
        # This file has a deliberate type error
        assert result.has_errors or result.returncode != 0

    def test_check_stele_dne(self):
        from stele_lean.check import check_stele_file
        dne_path = _ROOT / "examples" / "dne.stele"
        if not dne_path.exists():
            pytest.skip("examples/dne.stele not found")
        result = check_stele_file(dne_path)
        assert result.available is True
        # dne has a valid type; sorry skeleton should not produce type errors
        assert not result.has_errors

    def test_check_stele_mp(self):
        from stele_lean.check import check_stele_file
        import tempfile
        import os
        stele_text = (
            "theorem mp_test:\n"
            "  assume h1: P -> Q\n"
            "  assume h2: P\n"
            "  have hq: Q by mp h1 h2\n"
            "  conclude Q by hq\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".stele", delete=False, encoding="utf-8"
        ) as f:
            f.write(stele_text)
            tmp = f.name
        try:
            result = check_stele_file(tmp)
            assert result.available is True
            assert not result.has_errors
        finally:
            os.unlink(tmp)
