"""Tests for stele.proofstate — proof-state extraction and rule hints.

All ProofState and RuleHint objects are UNTRUSTED. These tests verify structural
correctness of the extraction logic and hint patterns, not proof validity.
The kernel (stele/kernel.py) is never called from proofstate.py.
"""
import pytest
from stele.ast import Var, Op

P = Var("P")
Q = Var("Q")
R = Var("R")
BOT = Op("bot", ())
P_IMP_Q = Op("imp", (P, Q))
P_AND_Q = Op("and", (P, Q))
P_OR_Q = Op("or", (P, Q))
NOT_P = Op("not", (P,))
NOT_NOT_P = Op("not", (NOT_P,))


# ── Proof source fixtures ──────────────────────────────────────────────────

IMP_SELF_SRC = """\
theorem imp_self:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h2
  conclude P -> P by h3
"""

AND_DEMO_SRC = """\
theorem and_demo:
  assume h1: P
  assume h2: Q
  have h3: P and Q by and_intro h1 h2
  conclude P and Q by h3
"""

NEG_INTRO_SRC = """\
theorem neg_demo:
  suppose h1: P and not P
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h1 h4
  conclude not (P and not P) by h5
"""

DNE_SRC = """\
theorem dne_demo using classical_prop:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""

OR_COMM_SRC = """\
theorem or_comm:
  assume h1: P or Q
  suppose h2: P
    have h3: Q or P by or_intro_right h2
  suppose h4: Q
    have h5: Q or P by or_intro_left h4
  have h6: Q or P by or_elim h1 h2 h3 h4 h5
  conclude Q or P by h6
"""

PARTIAL_SRC = """\
theorem partial:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
"""


def _parse(src):
    from stele.parser import parse_theorem
    return parse_theorem(src)


def _state(src, logic=None, cursor_line=None):
    from stele.proofstate import proof_state_from_text
    return proof_state_from_text(src, logic=logic, cursor_line=cursor_line)


# ── Part A: Dataclass structure ────────────────────────────────────────────

class TestDataclassStructure:
    def test_context_entry_fields(self):
        from stele.proofstate import ContextEntry
        e = ContextEntry(
            label="h1", formula_str="P", formula_raw=P,
            kind="assume", line=1, scope_depth=0, available=True,
        )
        assert e.label == "h1"
        assert e.formula_raw == P
        assert e.available is True
        assert e.kind == "assume"

    def test_rule_hint_trusted_always_false(self):
        from stele.proofstate import RuleHint
        h = RuleHint(
            rule="mp", title="Modus Ponens",
            why_applicable="test", required_refs=["h1", "h2"],
            candidate_line_template="have hN: Q by mp h1 h2",
            confidence="high",
        )
        assert h.trusted is False
        # Cannot be set to True (it's a default, but let's check it)
        assert not h.trusted

    def test_proof_state_fields(self):
        state = _state(AND_DEMO_SRC)
        assert state.theorem == "and_demo"
        assert state.logic in ("intuitionistic_prop", "classical_prop")
        assert isinstance(state.context, list)
        assert isinstance(state.available_labels, list)
        assert isinstance(state.closed_labels, list)
        assert state.parse_error is None


# ── Part B: Proof-state extraction ────────────────────────────────────────

class TestProofStateExtraction:
    def test_assume_labels_available(self):
        state = _state(AND_DEMO_SRC)
        assert "h1" in state.available_labels
        assert "h2" in state.available_labels
        assert "h3" in state.available_labels

    def test_conclude_formula_is_target(self):
        state = _state(AND_DEMO_SRC)
        assert state.target is not None
        assert "and" in state.target.lower() or "∧" in state.target

    def test_suppose_labels_are_closed_after_block(self):
        state = _state(IMP_SELF_SRC)
        # h1 and h2 are inside the suppose block
        assert "h1" in state.closed_labels
        assert "h2" in state.closed_labels
        # h3 is top-level
        assert "h3" in state.available_labels

    def test_open_assumptions(self):
        state = _state(AND_DEMO_SRC)
        assert "h1" in state.open_assumptions
        assert "h2" in state.open_assumptions
        # h3 is a have, not an assume
        assert "h3" not in state.open_assumptions

    def test_logic_from_theorem(self):
        state = _state(DNE_SRC)
        assert "classical" in state.logic

    def test_logic_override(self):
        state = _state(AND_DEMO_SRC, logic="classical_prop")
        assert state.logic == "classical_prop"

    def test_context_entries_have_formulas(self):
        state = _state(AND_DEMO_SRC)
        entries = {e.label: e for e in state.context}
        assert entries["h1"].formula_raw == P
        assert entries["h2"].formula_raw == Q

    def test_suppose_entries_have_correct_scope_depth(self):
        state = _state(IMP_SELF_SRC)
        entries = {e.label: e for e in state.context}
        assert entries["h1"].scope_depth == 0
        # h2 is inside the suppose block (depth 1)
        assert entries["h2"].scope_depth == 1

    def test_suppose_entries_marked_unavailable(self):
        state = _state(IMP_SELF_SRC)
        entries = {e.label: e for e in state.context}
        assert entries["h1"].available is False
        assert entries["h2"].available is False
        assert entries["h3"].available is True

    def test_or_comm_two_subproofs_both_closed(self):
        state = _state(OR_COMM_SRC)
        # h2, h3, h4, h5 are all in suppose blocks
        for label in ("h2", "h3", "h4", "h5"):
            assert label in state.closed_labels, f"{label} should be closed"
        # h1 (assume) and h6 (top-level have) should be available
        assert "h1" in state.available_labels
        assert "h6" in state.available_labels

    def test_last_step_is_last_available_label(self):
        state = _state(AND_DEMO_SRC)
        assert state.last_step == "h3"

    def test_pending_goal_when_proof_complete(self):
        state = _state(AND_DEMO_SRC)
        # h3 holds P and Q, conclude is P and Q — pending_goal should be None
        # (last step matches conclude formula)
        assert state.pending_goal is None

    def test_pending_goal_when_proof_incomplete(self):
        state = _state(PARTIAL_SRC)
        # No conclude step — pending_goal is None
        assert state.pending_goal is None
        assert state.target is None

    def test_parse_error_graceful(self):
        from stele.proofstate import proof_state_from_text
        state = proof_state_from_text("not valid python {{ }")
        assert state.parse_error is not None
        assert state.context == []
        assert state.available_labels == []


# ── Part C: Context helpers ────────────────────────────────────────────────

class TestContextHelpers:
    def test_visible_context_at(self):
        from stele.proofstate import visible_context_at
        thm = _parse(AND_DEMO_SRC)
        ctx = visible_context_at(thm, line=100)
        labels = [e.label for e in ctx]
        assert "h1" in labels
        assert "h2" in labels
        assert "h3" in labels

    def test_available_labels_at(self):
        from stele.proofstate import available_labels_at
        thm = _parse(AND_DEMO_SRC)
        labels = available_labels_at(thm, line=100)
        assert "h1" in labels
        assert "h2" in labels

    def test_proof_state_direct(self):
        from stele.proofstate import proof_state
        thm = _parse(AND_DEMO_SRC)
        state = proof_state(thm, "intuitionistic_prop")
        assert state.theorem == "and_demo"
        assert state.parse_error is None


# ── Part D: Rule hints ────────────────────────────────────────────────────

class TestRuleHints:
    def _hints(self, src, logic=None, goal_f=None):
        from stele.proofstate import suggest_rule_hints
        state = _state(src, logic=logic)
        return suggest_rule_hints(state, goal=goal_f)

    def test_hints_all_untrusted(self):
        hints = self._hints(AND_DEMO_SRC)
        for h in hints:
            assert h.trusted is False

    def test_mp_hint_when_context_has_imp_and_antecedent(self):
        src = """\
theorem mp_test:
  assume h1: P -> Q
  assume h2: P
  conclude Q by h2
"""
        hints = self._hints(src)
        rules = [h.rule for h in hints]
        assert "mp" in rules

    def test_mp_hint_refs_correct(self):
        src = """\
theorem mp_test:
  assume h1: P -> Q
  assume h2: P
  conclude Q by h2
"""
        hints = self._hints(src)
        mp_hints = [h for h in hints if h.rule == "mp"]
        assert mp_hints
        mp = mp_hints[0]
        assert "h1" in mp.required_refs
        assert "h2" in mp.required_refs

    def test_and_elim_hints_when_context_has_conjunction(self):
        src = """\
theorem and_test:
  assume h1: P and Q
  conclude P by h1
"""
        hints = self._hints(src)
        rules = [h.rule for h in hints]
        assert "and_elim_left" in rules
        assert "and_elim_right" in rules

    def test_neg_elim_hint_when_context_has_p_and_not_p(self):
        src = """\
theorem neg_e:
  assume h1: P
  assume h2: not P
  conclude P by h1
"""
        hints = self._hints(src)
        rules = [h.rule for h in hints]
        assert "neg_elim" in rules

    def test_ex_falso_hint_when_context_has_false(self):
        src = """\
theorem ef:
  assume h1: false
  conclude P by h1
"""
        hints = self._hints(src, goal_f=P)
        rules = [h.rule for h in hints]
        assert "ex_falso" in rules

    def test_imp_intro_hint_for_goal_imp(self):
        src = """\
theorem hint_test:
  assume h1: P
  conclude P -> Q by h1
"""
        hints = self._hints(src, goal_f=P_IMP_Q)
        rules = [h.rule for h in hints]
        assert "imp_intro" in rules

    def test_and_intro_hint_for_goal_and(self):
        src = """\
theorem hint_test:
  assume h1: P
  assume h2: Q
  conclude P and Q by h1
"""
        hints = self._hints(src, goal_f=P_AND_Q)
        rules = [h.rule for h in hints]
        assert "and_intro" in rules

    def test_or_intro_left_when_context_has_left_disjunct(self):
        src = """\
theorem or_test:
  assume h1: P
  conclude P or Q by h1
"""
        hints = self._hints(src, goal_f=P_OR_Q)
        rules = [h.rule for h in hints]
        assert "or_intro_left" in rules

    def test_or_intro_right_when_context_has_right_disjunct(self):
        src = """\
theorem or_test:
  assume h1: Q
  conclude P or Q by h1
"""
        hints = self._hints(src, goal_f=P_OR_Q)
        rules = [h.rule for h in hints]
        assert "or_intro_right" in rules

    def test_neg_intro_hint_for_goal_neg(self):
        hints = self._hints(AND_DEMO_SRC, goal_f=NOT_P)
        rules = [h.rule for h in hints]
        assert "neg_intro" in rules

    def test_dne_hint_classical_with_double_neg_in_context(self):
        src = """\
theorem dne_test using classical_prop:
  assume h1: not not P
  conclude P by h1
"""
        hints = self._hints(src, logic="classical_prop")
        rules = [h.rule for h in hints]
        assert "dne" in rules

    def test_dne_hint_not_in_intuitionistic(self):
        src = """\
theorem test:
  assume h1: not not P
  conclude P by h1
"""
        hints = self._hints(src, logic="intuitionistic_prop")
        rules = [h.rule for h in hints]
        assert "dne" not in rules

    def test_lem_hint_classical_for_lem_goal(self):
        lem_goal = Op("or", (P, NOT_P))
        hints = self._hints(AND_DEMO_SRC, logic="classical_prop", goal_f=lem_goal)
        rules = [h.rule for h in hints]
        assert "lem" in rules

    def test_lem_hint_not_in_intuitionistic(self):
        lem_goal = Op("or", (P, NOT_P))
        hints = self._hints(AND_DEMO_SRC, logic="intuitionistic_prop", goal_f=lem_goal)
        rules = [h.rule for h in hints]
        assert "lem" not in rules

    def test_pbc_hint_only_classical(self):
        hints_cl = self._hints(AND_DEMO_SRC, logic="classical_prop", goal_f=P)
        hints_in = self._hints(AND_DEMO_SRC, logic="intuitionistic_prop", goal_f=P)
        assert "pbc" in [h.rule for h in hints_cl]
        assert "pbc" not in [h.rule for h in hints_in]

    def test_max_hints_respected(self):
        from stele.proofstate import suggest_rule_hints
        state = _state(DNE_SRC, logic="classical_prop")
        hints = suggest_rule_hints(state, max_hints=2)
        assert len(hints) <= 2

    def test_no_hints_with_empty_state(self):
        from stele.proofstate import proof_state_from_text, suggest_rule_hints
        state = proof_state_from_text("not valid {{ }")
        hints = suggest_rule_hints(state)
        assert hints == []

    def test_hints_have_candidate_template(self):
        src = """\
theorem test:
  assume h1: P -> Q
  assume h2: P
  conclude Q by h2
"""
        hints = self._hints(src)
        for h in hints:
            assert h.candidate_line_template
            assert len(h.candidate_line_template) > 0

    def test_hints_have_confidence(self):
        src = """\
theorem test:
  assume h1: P -> Q
  assume h2: P
  conclude Q by h2
"""
        hints = self._hints(src)
        for h in hints:
            assert h.confidence in ("low", "medium", "high")

    def test_hints_no_duplicates(self):
        src = """\
theorem test:
  assume h1: P -> Q
  assume h2: P
  conclude Q by h2
"""
        hints = self._hints(src)
        rules = [h.rule for h in hints]
        assert len(rules) == len(set(rules)), "Duplicate rules in hints"


# ── Part E: Diagnostic explanations ───────────────────────────────────────

class TestDiagnosticExplanations:
    def test_explain_undefined_symbol(self):
        from stele.diagnostics import explain_diagnostic_code, DiagnosticExplanation
        ex = explain_diagnostic_code("UndefinedSymbol")
        assert isinstance(ex, DiagnosticExplanation)
        assert ex.code == "UndefinedSymbol"
        assert len(ex.short) > 0
        assert len(ex.how_to_fix) > 0

    def test_explain_missing_hypothesis(self):
        from stele.diagnostics import explain_diagnostic_code
        ex = explain_diagnostic_code("MissingHypothesis")
        assert ex.code == "MissingHypothesis"
        assert "scope" in ex.how_to_fix.lower() or "block" in ex.how_to_fix.lower()

    def test_explain_unsupported_conclusion(self):
        from stele.diagnostics import explain_diagnostic_code
        ex = explain_diagnostic_code("UnsupportedConclusion")
        assert ex.code == "UnsupportedConclusion"

    def test_explain_circular_dependency(self):
        from stele.diagnostics import explain_diagnostic_code
        ex = explain_diagnostic_code("CircularDependency")
        assert ex.code == "CircularDependency"

    def test_explain_unused_assumption(self):
        from stele.diagnostics import explain_diagnostic_code
        ex = explain_diagnostic_code("UnusedAssumption")
        assert ex.code == "UnusedAssumption"

    def test_explain_invalid_transition(self):
        from stele.diagnostics import explain_diagnostic_code
        ex = explain_diagnostic_code("InvalidTransition")
        assert ex.code == "InvalidTransition"

    def test_explain_kripke_countermodel(self):
        from stele.diagnostics import explain_diagnostic_code
        ex = explain_diagnostic_code("KripkeCountermodelFound")
        assert ex.code == "KripkeCountermodelFound"
        assert "intuitionistic" in ex.likely_cause.lower() or "classical" in ex.likely_cause.lower()

    def test_explain_unknown_code_fallback(self):
        from stele.diagnostics import explain_diagnostic_code
        ex = explain_diagnostic_code("TotallyUnknownCode")
        # Falls back to a generic explanation
        assert ex.short is not None

    def test_explain_diagnostic_from_object(self):
        from stele.diagnostics import explain_diagnostic, Diagnostic
        diag = Diagnostic("UndefinedSymbol", "test message", line=2, severity="error")
        ex = explain_diagnostic(diag)
        assert ex.code == "UndefinedSymbol"

    def test_all_stable_codes_have_entries(self):
        from stele.diagnostics import explain_diagnostic_code, DiagnosticExplanation
        codes = [
            "UndefinedSymbol", "MissingHypothesis", "UnsupportedConclusion",
            "CircularDependency", "UnusedAssumption", "UndefinedDefinition",
            "InvalidTransition", "TypeMismatch", "KripkeCountermodelFound",
        ]
        for code in codes:
            ex = explain_diagnostic_code(code)
            assert ex.code == code, f"Expected catalog entry for {code}"

    def test_explanation_fields_not_empty_for_stable_codes(self):
        from stele.diagnostics import explain_diagnostic_code
        for code in ["UndefinedSymbol", "MissingHypothesis", "UnsupportedConclusion"]:
            ex = explain_diagnostic_code(code)
            assert ex.short, f"{code}.short is empty"
            assert ex.likely_cause, f"{code}.likely_cause is empty"
            assert ex.how_to_fix, f"{code}.how_to_fix is empty"


# ── Part F: Web API ────────────────────────────────────────────────────────

class TestWebAPI:
    def test_state_json_returns_ok(self):
        from stele.web import state_json
        result = state_json(AND_DEMO_SRC, "intuitionistic_prop")
        assert result["ok"] is True
        assert result["_untrusted"] is True
        assert "_disclaimer" in result

    def test_state_json_has_context(self):
        from stele.web import state_json
        result = state_json(AND_DEMO_SRC, "intuitionistic_prop")
        ctx = result.get("context", [])
        labels = [e["label"] for e in ctx]
        assert "h1" in labels
        assert "h2" in labels

    def test_hints_json_returns_ok(self):
        from stele.web import hints_json
        src = """\
theorem test:
  assume h1: P -> Q
  assume h2: P
  conclude Q by h2
"""
        result = hints_json(src, "intuitionistic_prop")
        assert result["ok"] is True
        assert result["_untrusted"] is True
        hints = result.get("hints", [])
        assert isinstance(hints, list)

    def test_hints_json_all_hints_untrusted(self):
        from stele.web import hints_json
        src = """\
theorem test:
  assume h1: P -> Q
  assume h2: P
  conclude Q by h2
"""
        result = hints_json(src, "intuitionistic_prop")
        for h in result.get("hints", []):
            assert h["trusted"] is False

    def test_state_json_parse_error_graceful(self):
        from stele.web import state_json
        result = state_json("not valid {{ }", "intuitionistic_prop")
        assert result["ok"] is True  # state extraction is always "ok"
        # But parse_error is set
        assert result.get("parse_error") is not None

    def test_hints_json_with_goal_override(self):
        from stele.web import hints_json
        result = hints_json(AND_DEMO_SRC, "intuitionistic_prop", goal="P -> Q")
        assert result["ok"] is True

    def test_hints_json_classical_has_pbc(self):
        from stele.web import hints_json
        src = """\
theorem test using classical_prop:
  assume h1: P
  conclude P by h1
"""
        result = hints_json(src, "classical_prop")
        rules = [h["rule"] for h in result.get("hints", [])]
        assert "pbc" in rules


# ── Part G: Browser / Pyodide wrappers ────────────────────────────────────

class TestBrowserWrappers:
    def test_browser_state_exists(self):
        from stele.browser import browser_state
        assert callable(browser_state)

    def test_browser_hints_exists(self):
        from stele.browser import browser_hints
        assert callable(browser_hints)

    def test_browser_state_returns_dict(self):
        from stele.browser import browser_state
        result = browser_state(AND_DEMO_SRC, "intuitionistic_prop")
        assert isinstance(result, dict)
        assert result.get("ok") is True

    def test_browser_hints_returns_dict(self):
        from stele.browser import browser_hints
        result = browser_hints(AND_DEMO_SRC, "intuitionistic_prop")
        assert isinstance(result, dict)
        assert result.get("ok") is True

    def test_browser_state_untrusted_flag(self):
        from stele.browser import browser_state
        result = browser_state(AND_DEMO_SRC, "intuitionistic_prop")
        assert result.get("_untrusted") is True

    def test_browser_hints_untrusted_flag(self):
        from stele.browser import browser_hints
        result = browser_hints(AND_DEMO_SRC, "intuitionistic_prop")
        assert result.get("_untrusted") is True


# ── Part H: Serialization ─────────────────────────────────────────────────

class TestSerialization:
    def test_proof_state_to_dict_structure(self):
        from stele.proofstate import proof_state_from_text, proof_state_to_dict
        state = proof_state_from_text(AND_DEMO_SRC)
        d = proof_state_to_dict(state)
        assert "theorem" in d
        assert "logic" in d
        assert "context" in d
        assert "available_labels" in d
        assert "closed_labels" in d

    def test_proof_state_to_dict_context_entries(self):
        from stele.proofstate import proof_state_from_text, proof_state_to_dict
        state = proof_state_from_text(AND_DEMO_SRC)
        d = proof_state_to_dict(state)
        ctx = d["context"]
        assert all("label" in e for e in ctx)
        assert all("formula" in e for e in ctx)
        assert all("available" in e for e in ctx)

    def test_rule_hints_to_list_structure(self):
        from stele.proofstate import proof_state_from_text, suggest_rule_hints, rule_hints_to_list
        state = proof_state_from_text(AND_DEMO_SRC)
        hints = suggest_rule_hints(state)
        lst = rule_hints_to_list(hints)
        assert isinstance(lst, list)
        for h in lst:
            assert "rule" in h
            assert "trusted" in h
            assert h["trusted"] is False


# ── Part I: CLI ────────────────────────────────────────────────────────────

class TestCLI:
    def test_state_command_succeeds(self, tmp_path):
        from stele.cli import cmd_state
        f = tmp_path / "t.stele"
        f.write_text(AND_DEMO_SRC, encoding="utf-8")
        rc = cmd_state(str(f), "intuitionistic_prop", None, None)
        assert rc == 0

    def test_hints_command_succeeds(self, tmp_path):
        from stele.cli import cmd_hints
        f = tmp_path / "t.stele"
        f.write_text(AND_DEMO_SRC, encoding="utf-8")
        rc = cmd_hints(str(f), "intuitionistic_prop", None, None)
        assert rc == 0

    def test_state_command_missing_file(self, tmp_path):
        from stele.cli import cmd_state
        rc = cmd_state(str(tmp_path / "missing.stele"), None, None, None)
        assert rc != 0

    def test_hints_command_missing_file(self, tmp_path):
        from stele.cli import cmd_hints
        rc = cmd_hints(str(tmp_path / "missing.stele"), None, None, None)
        assert rc != 0

    def test_main_state_subcommand(self, tmp_path):
        from stele.cli import main
        f = tmp_path / "t.stele"
        f.write_text(AND_DEMO_SRC, encoding="utf-8")
        rc = main(["state", str(f)])
        assert rc == 0

    def test_main_hints_subcommand(self, tmp_path):
        from stele.cli import main
        f = tmp_path / "t.stele"
        f.write_text(AND_DEMO_SRC, encoding="utf-8")
        rc = main(["hints", str(f)])
        assert rc == 0


# ── Part J: Untrusted path verification ───────────────────────────────────

class TestUntrustedBoundary:
    def test_hints_are_not_trusted(self):
        """Hints must never be returned with trusted=True."""
        from stele.proofstate import suggest_rule_hints, proof_state_from_text
        state = proof_state_from_text(DNE_SRC, logic="classical_prop")
        hints = suggest_rule_hints(state)
        for h in hints:
            assert h.trusted is False

    def test_proof_state_does_not_verify(self):
        """proof_state_from_text must succeed even for invalid proofs."""
        from stele.proofstate import proof_state_from_text
        # Using dne under intuitionistic — kernel would reject this but state should succeed
        bad_src = """\
theorem bad_dne:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""
        state = proof_state_from_text(bad_src, logic="intuitionistic_prop")
        assert state.parse_error is None
        # State extraction succeeds regardless of proof validity
        assert "h1" in state.available_labels

    def test_state_module_does_not_import_kernel(self):
        """proofstate.py must not import stele.kernel (trust boundary)."""
        import ast as pyast
        import os
        module_path = os.path.join(
            os.path.dirname(__file__), "..", "stele", "proofstate.py"
        )
        src = open(module_path, encoding="utf-8").read()
        tree = pyast.parse(src)
        forbidden_imports = set()
        for node in pyast.walk(tree):
            if isinstance(node, pyast.ImportFrom):
                if node.module and "kernel" in node.module:
                    forbidden_imports.add(node.module)
            elif isinstance(node, pyast.Import):
                for alias in node.names:
                    if "kernel" in alias.name:
                        forbidden_imports.add(alias.name)
        assert not forbidden_imports, (
            f"proofstate.py must not import kernel; found: {forbidden_imports}"
        )

    def test_state_module_does_not_import_diagnostics(self):
        """proofstate.py must not import stele.diagnostics."""
        import ast as pyast
        import os
        module_path = os.path.join(
            os.path.dirname(__file__), "..", "stele", "proofstate.py"
        )
        src = open(module_path, encoding="utf-8").read()
        tree = pyast.parse(src)
        forbidden = set()
        for node in pyast.walk(tree):
            if isinstance(node, pyast.ImportFrom):
                if node.module and "diagnostics" in node.module:
                    forbidden.add(node.module)
        assert not forbidden, (
            f"proofstate.py must not import diagnostics; found: {forbidden}"
        )
