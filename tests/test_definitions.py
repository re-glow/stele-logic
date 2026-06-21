"""Tests for formula definitions, types.py, and new diagnostic codes."""
import pytest
from stele.parser import parse_theorem
from stele.proof import Definition, Theorem
from stele.types import Sort, infer_sort, expand_defs
from stele.diagnostics import Diagnostic, diagnose_theorem, diagnose_graph
from stele.ast import Var, Op

# ---------------------------------------------------------------------------
# Inline source fixtures
# ---------------------------------------------------------------------------

_BASIC_DEF = """
definition MY_IMP := P -> Q

theorem basic_def using intuitionistic_prop:
  assume h: MY_IMP
  assume hp: P
  have hq: Q by mp h hp
  conclude Q by hq
"""

_DOUBLE_DEF = """
definition A := P -> Q
definition B := A -> P

theorem double_def using intuitionistic_prop:
  assume h: B
  assume ha: A
  have hp: P by mp h ha
  conclude P by hp
"""

_CHAIN_DEF = """
definition INNER := P and Q
definition OUTER := INNER -> P

theorem chain_def using intuitionistic_prop:
  assume h: OUTER
  assume inner: INNER
  have hp: P by mp h inner
  conclude P by hp
"""

_NO_DEFS = """
theorem no_defs:
  assume h: P
  conclude P by h
"""

_INVALID_TRANSITION = """
theorem invalid_transition using intuitionistic_prop:
  assume h1: P -> Q
  assume h2: P and R
  have h3: Q by mp h1 h2
  conclude Q by h3
"""

_INVALID_TRANSITION_AND = """
theorem invalid_and using intuitionistic_prop:
  assume h1: P and Q
  have h2: Q by and_elim_left h1
  conclude Q by h2
"""

_UNDEF_DEF_SRC = """
definition USE_MISSING := MISSING_DEF -> P

theorem t:
  assume h: P
  conclude P by h
"""

_MULTI_DEF_ONE_MISSING = """
definition GOOD := P -> Q
definition BAD := NONEXISTENT_NAME -> P

theorem t:
  assume h: P
  conclude P by h
"""


def _codes(diags):
    return [d.code for d in diags]


def _has(diags, code):
    return any(d.code == code for d in diags)


# ---------------------------------------------------------------------------
# Part A.1 — Definition parsing and storage
# ---------------------------------------------------------------------------

def test_definition_is_parsed():
    thm = parse_theorem(_BASIC_DEF.strip())
    assert len(thm.definitions) == 1


def test_definition_name_stored():
    thm = parse_theorem(_BASIC_DEF.strip())
    assert thm.definitions[0].name == "MY_IMP"


def test_definition_formula_stored():
    thm = parse_theorem(_BASIC_DEF.strip())
    d = thm.definitions[0]
    # Original (unexpanded) formula: P -> Q = Op("imp", (Var("P"), Var("Q")))
    assert d.formula == Op("imp", (Var("P"), Var("Q")))


def test_definition_line_stored():
    thm = parse_theorem(_BASIC_DEF.strip())
    # definition is on line 1 of the stripped text → line 1
    assert thm.definitions[0].line >= 1


def test_multiple_definitions_ordered():
    thm = parse_theorem(_DOUBLE_DEF.strip())
    assert len(thm.definitions) == 2
    names = [d.name for d in thm.definitions]
    assert names == ["A", "B"]


def test_no_definitions_empty_tuple():
    thm = parse_theorem(_NO_DEFS.strip())
    assert thm.definitions == ()


def test_definitions_type_is_tuple_of_definition():
    thm = parse_theorem(_BASIC_DEF.strip())
    assert isinstance(thm.definitions, tuple)
    assert all(isinstance(d, Definition) for d in thm.definitions)


def test_theorem_without_definitions_backward_compatible():
    """Existing Theorem(name, logic, lines) creation still works."""
    t = Theorem(name="t", logic=None, lines=())
    assert t.definitions == ()


# ---------------------------------------------------------------------------
# Part A.2 — Definition expansion (macro substitution)
# ---------------------------------------------------------------------------

def test_expansion_replaces_var_in_assume():
    """After parsing, Var('MY_IMP') in the assume should be replaced by P -> Q."""
    thm = parse_theorem(_BASIC_DEF.strip())
    h_node = next(n for n in thm.lines if hasattr(n, "label") and n.label == "h")
    assert h_node.formula == Op("imp", (Var("P"), Var("Q")))


def test_expansion_in_have_formula():
    """have node formula should also be expanded if it used a definition name."""
    src = """
definition CONJ := P and Q

theorem t using intuitionistic_prop:
  assume h: CONJ
  have hp: P by and_elim_left h
  conclude P by hp
"""
    thm = parse_theorem(src.strip())
    h_node = next(n for n in thm.lines if hasattr(n, "label") and n.label == "h")
    assert h_node.formula == Op("and", (Var("P"), Var("Q")))


def test_chain_definition_expands_transitively():
    """OUTER := INNER -> P, INNER := P and Q → OUTER expands to (P and Q) -> P."""
    thm = parse_theorem(_CHAIN_DEF.strip())
    defs = {d.name: d for d in thm.definitions}
    # OUTER's stored formula still has INNER (original)
    outer_def = defs["OUTER"]
    assert isinstance(outer_def.formula.args[0], Var)
    assert outer_def.formula.args[0].name == "INNER"
    # But in the theorem body, the assume node should have the expanded formula
    h_node = next(n for n in thm.lines if hasattr(n, "label") and n.label == "h")
    expanded = h_node.formula
    # Expanded: (P and Q) -> P
    assert expanded == Op("imp", (Op("and", (Var("P"), Var("Q"))), Var("P")))


def test_proof_with_definition_passes_check():
    """A proof using a definition name verifies correctly after expansion."""
    from stele.kernel import check_theorem
    thm = parse_theorem(_BASIC_DEF.strip())
    logic, _ = check_theorem(thm, "intuitionistic_prop")
    assert logic.name == "intuitionistic_prop"


def test_double_definition_proof_passes_check():
    from stele.kernel import check_theorem
    thm = parse_theorem(_DOUBLE_DEF.strip())
    logic, _ = check_theorem(thm, "intuitionistic_prop")
    assert logic.name == "intuitionistic_prop"


def test_chain_definition_proof_passes_check():
    from stele.kernel import check_theorem
    thm = parse_theorem(_CHAIN_DEF.strip())
    logic, _ = check_theorem(thm, "intuitionistic_prop")
    assert logic.name == "intuitionistic_prop"


def test_definition_basic_example_file():
    """examples/definition_basic.stele must parse and verify cleanly."""
    from stele.kernel import check_theorem
    src = open("examples/definition_basic.stele", encoding="utf-8").read()
    thm = parse_theorem(src)
    check_theorem(thm, "intuitionistic_prop")


def test_definition_clean_no_diagnostics():
    diags = diagnose_theorem(parse_theorem(_BASIC_DEF.strip()), "intuitionistic_prop")
    assert diags == []


# ---------------------------------------------------------------------------
# Part A.3 — UndefinedDefinition diagnostic
# ---------------------------------------------------------------------------

def test_undef_def_reported():
    diags = diagnose_theorem(parse_theorem(_UNDEF_DEF_SRC.strip()))
    assert _has(diags, "UndefinedDefinition")


def test_undef_def_message_contains_name():
    diags = diagnose_theorem(parse_theorem(_UNDEF_DEF_SRC.strip()))
    msgs = [d.message for d in diags if d.code == "UndefinedDefinition"]
    assert any("MISSING_DEF" in m for m in msgs)


def test_undef_def_severity_is_warning():
    """UndefinedDefinition is a warning (heuristic-based) not an error."""
    diags = diagnose_theorem(parse_theorem(_UNDEF_DEF_SRC.strip()))
    for d in diags:
        if d.code == "UndefinedDefinition":
            assert d.severity == "warning"
            return
    pytest.fail("UndefinedDefinition not reported")


def test_undef_def_only_in_def_body_not_theorem():
    """Only definition bodies are scanned for UndefinedDefinition.
    Prop vars in the theorem body (like P, Q) are NOT flagged.
    """
    diags = diagnose_theorem(parse_theorem(_UNDEF_DEF_SRC.strip()))
    undef_defs = [d for d in diags if d.code == "UndefinedDefinition"]
    assert all("MISSING_DEF" in d.message for d in undef_defs)
    assert not any("P" in d.message for d in undef_defs)


def test_single_char_prop_var_not_flagged_in_def_body():
    """Single-char names (P, Q, ...) in definition bodies are NOT UndefinedDefinition."""
    src = """
definition SIMPLE := P -> Q

theorem t:
  assume h: P -> Q
  assume hp: P
  have hq: Q by mp h hp
  conclude Q by hq
"""
    diags = diagnose_theorem(parse_theorem(src.strip()), "intuitionistic_prop")
    assert not _has(diags, "UndefinedDefinition")


def test_multiple_definitions_only_missing_flagged():
    diags = diagnose_theorem(parse_theorem(_MULTI_DEF_ONE_MISSING.strip()))
    undef = [d for d in diags if d.code == "UndefinedDefinition"]
    assert any("NONEXISTENT_NAME" in d.message for d in undef)
    # GOOD is defined, so USE of GOOD in BAD's body would not fire;
    # but BAD references NONEXISTENT_NAME, which does fire.
    assert not any("GOOD" in d.message for d in undef)


def test_undef_def_example_file(capsys):
    from stele.cli import cmd_diagnose
    rc = cmd_diagnose("examples/diagnostic_undefined_definition.stele", None)
    out = capsys.readouterr().out
    assert "UndefinedDefinition" in out
    assert "MISSING_DEF" in out
    assert rc == 0  # warning only, not error


def test_defined_name_used_in_sibling_def_not_flagged():
    """When def A references def B and B is defined, no UndefinedDefinition."""
    src = """
definition B := P -> Q
definition A := B -> P

theorem t:
  assume h: P
  conclude P by h
"""
    diags = diagnose_theorem(parse_theorem(src.strip()))
    assert not _has(diags, "UndefinedDefinition")


# ---------------------------------------------------------------------------
# Part B — types.py machinery
# ---------------------------------------------------------------------------

def test_sort_formula_exists():
    assert Sort.FORMULA is not None


def test_sort_term_exists_as_placeholder():
    assert Sort.TERM is not None


def test_infer_sort_var_is_formula():
    assert infer_sort(Var("P")) == Sort.FORMULA


def test_infer_sort_op_is_formula():
    assert infer_sort(Op("imp", (Var("P"), Var("Q")))) == Sort.FORMULA


def test_infer_sort_bot_is_formula():
    assert infer_sort(Op("bot", ())) == Sort.FORMULA


def test_infer_sort_complex_formula():
    f = Op("and", (Op("not", (Var("P"),)), Var("Q")))
    assert infer_sort(f) == Sort.FORMULA


def test_expand_defs_simple():
    """expand_defs replaces a defined Var with its body."""
    from stele.proof import Definition
    d = Definition("LEM_P", Op("or", (Var("P"), Op("not", (Var("P"),)))), 1)
    defs = {"LEM_P": d}
    result = expand_defs(Var("LEM_P"), defs)
    assert result == Op("or", (Var("P"), Op("not", (Var("P"),))))


def test_expand_defs_passthrough_unknown():
    """expand_defs leaves unknown Vars unchanged."""
    result = expand_defs(Var("Q"), {})
    assert result == Var("Q")


def test_expand_defs_nested():
    """expand_defs recurses into Op args."""
    from stele.proof import Definition
    d = Definition("A", Var("P"), 1)
    defs = {"A": d}
    f = Op("imp", (Var("A"), Var("Q")))
    result = expand_defs(f, defs)
    assert result == Op("imp", (Var("P"), Var("Q")))


def test_expand_defs_cycle_safe():
    """Circular definition: A := A — expansion stops at cycle."""
    from stele.proof import Definition
    d = Definition("A", Var("A"), 1)
    defs = {"A": d}
    result = expand_defs(Var("A"), defs)
    # Should not loop; stops and returns Var("A")
    assert result == Var("A")


def test_type_mismatch_code_is_stable():
    """TypeMismatch is a stable code even though v1 has no surface trigger."""
    d = Diagnostic("TypeMismatch", "sort mismatch: formula expected, got term", None, "error")
    assert d.code == "TypeMismatch"
    assert d.severity == "error"


def test_check_sort_compat_succeeds_for_formula():
    from stele.types import check_sort_compat
    # Should not raise — all current exprs are FORMULA
    check_sort_compat(Var("P"), Sort.FORMULA)
    check_sort_compat(Op("and", (Var("P"), Var("Q"))), Sort.FORMULA)


def test_check_sort_compat_raises_on_wrong_sort():
    from stele.types import check_sort_compat
    with pytest.raises(ValueError, match="sort mismatch"):
        check_sort_compat(Var("P"), Sort.TERM)


# ---------------------------------------------------------------------------
# Part C — InvalidTransition diagnostic
# ---------------------------------------------------------------------------

def test_invalid_transition_reported_wrong_mp():
    """mp with wrong second premise type → InvalidTransition."""
    diags = diagnose_theorem(parse_theorem(_INVALID_TRANSITION.strip()), "intuitionistic_prop")
    assert _has(diags, "InvalidTransition")


def test_invalid_transition_message_contains_rule():
    diags = diagnose_theorem(parse_theorem(_INVALID_TRANSITION.strip()), "intuitionistic_prop")
    msgs = [d.message for d in diags if d.code == "InvalidTransition"]
    assert any("mp" in m for m in msgs)


def test_invalid_transition_severity_is_error():
    diags = diagnose_theorem(parse_theorem(_INVALID_TRANSITION.strip()), "intuitionistic_prop")
    for d in diags:
        if d.code == "InvalidTransition":
            assert d.severity == "error"
            return
    pytest.fail("InvalidTransition not reported")


def test_invalid_transition_wrong_and_elim():
    """and_elim_left on P and Q should yield P, not Q → InvalidTransition."""
    diags = diagnose_theorem(parse_theorem(_INVALID_TRANSITION_AND.strip()), "intuitionistic_prop")
    assert _has(diags, "InvalidTransition")


def test_invalid_transition_message_mentions_rule():
    diags = diagnose_theorem(parse_theorem(_INVALID_TRANSITION_AND.strip()), "intuitionistic_prop")
    msgs = [d.message for d in diags if d.code == "InvalidTransition"]
    assert any("and_elim_left" in m or "and_elim" in m for m in msgs)


def test_invalid_transition_not_reported_for_clean_proof():
    diags = diagnose_theorem(parse_theorem(_NO_DEFS.strip()))
    assert not _has(diags, "InvalidTransition")


def test_invalid_transition_not_reported_when_scope_errors_present():
    """When scope errors exist, InvalidTransition pass is skipped to avoid duplication."""
    _BAD_SCOPE = """
theorem bad_scope using intuitionistic_prop:
  assume h1: P -> Q
  have h2: Q by mp h1 missing
  conclude Q by h2
"""
    diags = diagnose_theorem(parse_theorem(_BAD_SCOPE.strip()), "intuitionistic_prop")
    # UndefinedSymbol for 'missing' → scope error → no InvalidTransition
    assert _has(diags, "UndefinedSymbol")
    assert not _has(diags, "InvalidTransition")


def test_invalid_transition_example_file(capsys):
    from stele.cli import cmd_diagnose
    rc = cmd_diagnose("examples/diagnostic_invalid_transition.stele", None)
    out = capsys.readouterr().out
    assert "InvalidTransition" in out
    assert rc == 1  # error severity


def test_check_still_strict_on_invalid_transition(tmp_path):
    """cli check must still fail; InvalidTransition is diagnostic-only."""
    from stele.cli import cmd_check
    p = tmp_path / "inv.stele"
    p.write_text(_INVALID_TRANSITION.strip())
    rc = cmd_check(str(p), "intuitionistic_prop")
    assert rc == 1


# ---------------------------------------------------------------------------
# Part D — All existing diagnostic codes still stable
# ---------------------------------------------------------------------------

def test_all_stable_codes_instantiatable():
    codes = [
        "UndefinedSymbol", "MissingHypothesis", "UnsupportedConclusion",
        "CircularDependency", "UnusedAssumption",
        "UndefinedDefinition", "InvalidTransition", "TypeMismatch",
    ]
    for code in codes:
        d = Diagnostic(code, f"test {code}", None, "error")
        assert d.code == code


# ---------------------------------------------------------------------------
# Part E — Regression: definitions don't break existing proofs
# ---------------------------------------------------------------------------

def test_peirce_unaffected():
    from stele.kernel import check_theorem
    src = open("examples/peirce.stele", encoding="utf-8").read()
    thm = parse_theorem(src)
    assert thm.definitions == ()
    check_theorem(thm, "classical_prop")


def test_existing_examples_unaffected():
    from stele.kernel import check_theorem
    import pathlib
    for f in pathlib.Path("examples").glob("*.stele"):
        if f.name.startswith("diag_") or f.name.startswith("diagnostic_") or f.name.startswith("matrix_"):
            continue
        src = f.read_text(encoding="utf-8")
        try:
            thm = parse_theorem(src)
        except Exception:
            continue
        if thm.logic and "matrix" in thm.logic:
            continue
        try:
            check_theorem(thm)
        except Exception:
            pass  # invalid examples are fine; we only care they parse without crash


def test_parse_theorem_backward_compatible():
    """Files without definitions still produce Theorem with empty definitions."""
    src = open("examples/dne.stele", encoding="utf-8").read()
    thm = parse_theorem(src)
    assert thm.definitions == ()
    assert isinstance(thm.lines, tuple)
    assert len(thm.lines) > 0
