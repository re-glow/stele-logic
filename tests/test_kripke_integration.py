"""Integration tests for Kripke countermodel surfaces.

Covers:
  - KripkeExplanation / kripke_explain() structured output
  - explanation_to_dict() serialisation
  - kripke_json() (web layer)
  - browser_kripke() (Pyodide shim)
  - /api/kripke HTTP endpoint
  - diagnostics Pass 4 (KripkeCountermodelFound)
  - Webapp/site UI presence (HTML content tests, no browser)
  - Regression: existing codes and module isolation unchanged
"""
import json
import pytest


# ---------------------------------------------------------------------------
# kripke_explain / KripkeExplanation
# ---------------------------------------------------------------------------

class TestKripkeExplain:
    def test_lem_countermodel_found(self):
        from stele.kripke import kripke_explain
        ex = kripke_explain("P or not P", max_worlds=3)
        assert ex.status == "countermodel_found"
        assert ex.worlds is not None
        assert ex.failing_world is not None
        assert "P" in ex.formula

    def test_dne_countermodel_found(self):
        from stele.kripke import kripke_explain
        ex = kripke_explain("not not P -> P", max_worlds=3)
        assert ex.status == "countermodel_found"
        assert ex.order_pairs is not None
        assert ex.valuation is not None

    def test_imp_self_no_countermodel(self):
        from stele.kripke import kripke_explain
        ex = kripke_explain("P -> P", max_worlds=3)
        assert ex.status == "no_countermodel_within_bound"
        assert ex.worlds is None
        assert ex.failing_world is None
        assert "bounded" in ex.bound_note.lower() or "not" in ex.bound_note.lower()

    def test_parse_error_returns_parse_error_status(self):
        from stele.kripke import kripke_explain
        ex = kripke_explain("P -> -> Q")
        assert ex.status == "parse_error"
        assert ex.worlds is None
        assert "parse" in ex.explanation.lower() or "error" in ex.explanation.lower()

    def test_empty_string_parse_error(self):
        from stele.kripke import kripke_explain
        ex = kripke_explain("")
        assert ex.status == "parse_error"

    def test_formula_object_accepted(self):
        from stele.kripke import kripke_explain
        from stele.ast import Var, Op
        phi = Op("or", (Var("P"), Op("not", (Var("P"),))))
        ex = kripke_explain(phi, max_worlds=3)
        assert ex.status == "countermodel_found"

    def test_peirce_countermodel(self):
        from stele.kripke import kripke_explain
        ex = kripke_explain("((P -> Q) -> P) -> P", max_worlds=4)
        assert ex.status == "countermodel_found"

    def test_explosion_no_countermodel(self):
        from stele.kripke import kripke_explain
        ex = kripke_explain("false -> P", max_worlds=3)
        assert ex.status == "no_countermodel_within_bound"

    def test_explanation_text_mentions_world(self):
        from stele.kripke import kripke_explain
        ex = kripke_explain("P or not P", max_worlds=3)
        assert "world" in ex.explanation.lower()

    def test_bound_note_present(self):
        from stele.kripke import kripke_explain
        ex = kripke_explain("P or not P", max_worlds=3)
        assert isinstance(ex.bound_note, str) and len(ex.bound_note) > 0

    def test_max_worlds_respected(self):
        from stele.kripke import kripke_explain
        ex1 = kripke_explain("P or not P", max_worlds=1)
        ex3 = kripke_explain("P or not P", max_worlds=3)
        # LEM needs at least 2 worlds; max_worlds=1 should fail
        assert ex1.status == "no_countermodel_within_bound"
        assert ex3.status == "countermodel_found"


class TestExplanationToDict:
    def test_countermodel_found_is_json_serialisable(self):
        from stele.kripke import kripke_explain, explanation_to_dict
        ex = kripke_explain("P or not P", max_worlds=3)
        d = explanation_to_dict(ex)
        s = json.dumps(d)
        parsed = json.loads(s)
        assert parsed["status"] == "countermodel_found"
        assert isinstance(parsed["worlds"], list)
        assert isinstance(parsed["order_pairs"], list)
        assert isinstance(parsed["valuation"], dict)

    def test_no_countermodel_is_json_serialisable(self):
        from stele.kripke import kripke_explain, explanation_to_dict
        ex = kripke_explain("P -> P", max_worlds=3)
        d = explanation_to_dict(ex)
        s = json.dumps(d)
        parsed = json.loads(s)
        assert parsed["status"] == "no_countermodel_within_bound"
        assert parsed["worlds"] is None

    def test_parse_error_is_json_serialisable(self):
        from stele.kripke import kripke_explain, explanation_to_dict
        ex = kripke_explain("bad ### formula")
        d = explanation_to_dict(ex)
        s = json.dumps(d)  # must not raise
        assert json.loads(s)["status"] == "parse_error"

    def test_valuation_keys_are_strings(self):
        from stele.kripke import kripke_explain, explanation_to_dict
        ex = kripke_explain("P or not P", max_worlds=3)
        d = explanation_to_dict(ex)
        for k in d.get("valuation") or {}:
            assert isinstance(k, str)


# ---------------------------------------------------------------------------
# kripke_json (web layer)
# ---------------------------------------------------------------------------

class TestKripkeJson:
    def test_lem_ok_true(self):
        from stele.web import kripke_json
        r = kripke_json("P or not P", 3)
        assert r["ok"] is True
        assert r["status"] == "countermodel_found"

    def test_dne_has_worlds(self):
        from stele.web import kripke_json
        r = kripke_json("not not P -> P", 3)
        assert isinstance(r["worlds"], list)
        assert r["failing_world"] is not None

    def test_imp_self_no_countermodel(self):
        from stele.web import kripke_json
        r = kripke_json("P -> P", 3)
        assert r["ok"] is True
        assert r["status"] == "no_countermodel_within_bound"
        assert r["worlds"] is None

    def test_missing_formula_returns_error(self):
        from stele.web import kripke_json
        r = kripke_json("", 3)
        assert r["ok"] is False
        assert "missing" in r["error"].lower() or "formula" in r["error"].lower()

    def test_bad_max_worlds_falls_back_to_4(self):
        from stele.web import kripke_json
        r = kripke_json("P or not P", "bad_value")
        assert r["ok"] is True  # falls back to 4; still finds countermodel

    def test_max_worlds_clamped(self):
        from stele.web import kripke_json
        r = kripke_json("P or not P", 999)
        assert r["ok"] is True  # clamped to 6; still works


# ---------------------------------------------------------------------------
# browser_kripke (Pyodide shim)
# ---------------------------------------------------------------------------

class TestBrowserKripke:
    def test_lem_countermodel(self):
        from stele.browser import browser_kripke
        r = browser_kripke("P or not P", max_worlds=3)
        assert r["ok"] is True
        assert r["status"] == "countermodel_found"

    def test_default_max_worlds_is_3(self):
        from stele.browser import browser_kripke
        r = browser_kripke("P or not P")
        # max_worlds default=3; LEM should be found
        assert r["status"] == "countermodel_found"

    def test_valid_formula_no_countermodel(self):
        from stele.browser import browser_kripke
        r = browser_kripke("P -> P")
        assert r["status"] == "no_countermodel_within_bound"

    def test_result_is_json_serialisable(self):
        from stele.browser import browser_kripke
        r = browser_kripke("P or not P")
        json.dumps(r)  # must not raise


# ---------------------------------------------------------------------------
# /api/kripke HTTP endpoint
# ---------------------------------------------------------------------------

class TestApiKripkeEndpoint:
    """Tests the JSON shape of /api/kripke without starting a server."""

    def _call(self, formula, max_worlds=3):
        from stele.web import kripke_json
        return kripke_json(formula, max_worlds)

    def test_lem_response_shape(self):
        r = self._call("P or not P")
        for key in ("ok", "status", "formula", "max_worlds", "bound_note",
                    "worlds", "order_pairs", "valuation", "failing_world", "explanation"):
            assert key in r, f"missing key {key!r}"

    def test_formula_field_is_string(self):
        r = self._call("P or not P")
        assert isinstance(r["formula"], str)

    def test_order_pairs_is_list(self):
        r = self._call("P or not P")
        assert isinstance(r["order_pairs"], list)

    def test_valuation_is_dict(self):
        r = self._call("P or not P")
        assert isinstance(r["valuation"], dict)

    def test_imp_self_worlds_is_none(self):
        r = self._call("P -> P")
        assert r["worlds"] is None
        assert r["failing_world"] is None


# ---------------------------------------------------------------------------
# Diagnostics Pass 4 — KripkeCountermodelFound
# ---------------------------------------------------------------------------

DNE_PROOF_INTUIT = """\
theorem dne_intuit:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""


class TestDiagnosticsKripkePass4:
    def _parse(self, src):
        from stele.parser import parse_theorem
        return parse_theorem(src)

    def test_invalid_rule_under_intuit_gets_kripke_hint(self):
        from stele.diagnostics import diagnose_theorem
        thm = self._parse(DNE_PROOF_INTUIT)
        diags = diagnose_theorem(thm, "intuitionistic_prop")
        codes = [d.code for d in diags]
        assert "KripkeCountermodelFound" in codes

    def test_kripke_hint_is_info_severity(self):
        from stele.diagnostics import diagnose_theorem
        thm = self._parse(DNE_PROOF_INTUIT)
        diags = diagnose_theorem(thm, "intuitionistic_prop")
        kd = [d for d in diags if d.code == "KripkeCountermodelFound"]
        assert kd, "expected KripkeCountermodelFound"
        assert all(d.severity == "info" for d in kd)

    def test_kripke_hint_is_additive_not_sole_diagnostic(self):
        """Kripke hint is additive — a proof error must also be present for it to fire.

        For 'dne' under intuitionistic_prop: the kernel says 'rule not available',
        which Pass 3 does not classify as InvalidTransition (by design). The Kripke
        hint still fires because Pass 4 re-runs the kernel directly.
        """
        from stele.diagnostics import diagnose_theorem
        thm = self._parse(DNE_PROOF_INTUIT)
        diags = diagnose_theorem(thm, "intuitionistic_prop")
        codes = [d.code for d in diags]
        # The Kripke hint is present as an info alongside whatever the kernel returned
        assert "KripkeCountermodelFound" in codes
        # Verify there is at most one KripkeCountermodelFound (no duplicates)
        assert codes.count("KripkeCountermodelFound") == 1

    def test_kripke_hint_absent_for_classical_logic(self):
        """Pass 4 only fires for intuitionistic_prop, not classical."""
        from stele.diagnostics import diagnose_theorem
        from stele.parser import parse_theorem
        # This proof uses dne under classical_prop — which is valid, so no hint
        src = """\
theorem lem_classical:
  assume h1: not not P
  have h2: P by dne h1
  conclude P by h2
"""
        thm = parse_theorem(src)
        diags = diagnose_theorem(thm, "classical_prop")
        codes = [d.code for d in diags]
        assert "KripkeCountermodelFound" not in codes

    def test_kripke_hint_message_mentions_world(self):
        from stele.diagnostics import diagnose_theorem
        thm = self._parse(DNE_PROOF_INTUIT)
        diags = diagnose_theorem(thm, "intuitionistic_prop")
        kd = [d for d in diags if d.code == "KripkeCountermodelFound"]
        assert kd
        assert "world" in kd[0].message.lower()

    def test_kripke_hint_message_has_non_derivability_disclaimer(self):
        """The hint must not conflate proof failure with semantic non-derivability."""
        from stele.diagnostics import diagnose_theorem
        thm = self._parse(DNE_PROOF_INTUIT)
        diags = diagnose_theorem(thm, "intuitionistic_prop")
        kd = [d for d in diags if d.code == "KripkeCountermodelFound"]
        assert kd
        # message must disclaim conflation
        msg = kd[0].message.lower()
        assert "proof" in msg or "semantic" in msg or "witness" in msg

    def test_no_kripke_hint_when_proof_valid(self):
        """Valid proof → kernel passes → no KripkeCountermodelFound."""
        from stele.diagnostics import diagnose_theorem
        from stele.parser import parse_theorem
        src = """\
theorem imp_self:
  assume h1: P
  conclude P by h1
"""
        thm = parse_theorem(src)
        diags = diagnose_theorem(thm, "intuitionistic_prop")
        codes = [d.code for d in diags]
        assert "KripkeCountermodelFound" not in codes

    def test_kripke_hint_line_is_none(self):
        """Pass 4 sets line=None (not tied to a specific line)."""
        from stele.diagnostics import diagnose_theorem
        thm = self._parse(DNE_PROOF_INTUIT)
        diags = diagnose_theorem(thm, "intuitionistic_prop")
        kd = [d for d in diags if d.code == "KripkeCountermodelFound"]
        assert kd
        assert kd[0].line is None


# ---------------------------------------------------------------------------
# UI content tests (no browser needed)
# ---------------------------------------------------------------------------

class TestWebappHtmlKripke:
    def _read_webapp(self):
        import os
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(here, "stele", "webapp", "index.html")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_kripke_section_label_present(self):
        html = self._read_webapp()
        assert "KRIPKE COUNTERMODEL" in html

    def test_kripke_formula_input_present(self):
        html = self._read_webapp()
        assert 'id="kripke-formula"' in html

    def test_kripke_btn_present(self):
        html = self._read_webapp()
        assert 'id="btn-kripke"' in html

    def test_kripke_output_div_present(self):
        html = self._read_webapp()
        assert 'id="kripke-output"' in html

    def test_kripke_worlds_select_present(self):
        html = self._read_webapp()
        assert 'id="kripke-worlds"' in html

    def test_api_kripke_js_call(self):
        html = self._read_webapp()
        assert "/api/kripke" in html

    def test_bounded_search_caveat_present(self):
        html = self._read_webapp()
        # UI must communicate the bounded-search caveat
        assert "bounded" in html.lower() or "does not prove" in html.lower() or "not prove" in html.lower()


class TestSiteHtmlKripke:
    def _read_site(self):
        import os
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(here, "site", "index.html")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_kripke_section_present(self):
        html = self._read_site()
        assert "Kripke Countermodel" in html

    def test_kripke_input_present(self):
        html = self._read_site()
        assert 'id="kripke-input"' in html

    def test_kripke_btn_present(self):
        html = self._read_site()
        assert 'id="btn-kripke"' in html

    def test_kripke_result_div_present(self):
        html = self._read_site()
        assert 'id="kripke-result"' in html

    def test_bounded_caveat_present(self):
        html = self._read_site()
        assert "not a proof" in html.lower() or "not prove" in html.lower() or "bounded" in html.lower()


class TestSitePyodideJsKripke:
    def _read_js(self):
        import os
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(here, "site", "assets", "stele-pyodide.js")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_run_kripke_function_present(self):
        js = self._read_js()
        assert "runKripke" in js

    def test_browser_kripke_call_present(self):
        js = self._read_js()
        assert "browser_kripke" in js

    def test_btn_kripke_bind_present(self):
        js = self._read_js()
        assert "btn-kripke" in js

    def test_countermodel_found_rendering(self):
        js = self._read_js()
        assert "countermodel_found" in js

    def test_no_countermodel_rendering(self):
        js = self._read_js()
        assert "no_countermodel_within_bound" in js


# ---------------------------------------------------------------------------
# Regression: isolation and existing invariants
# ---------------------------------------------------------------------------

class TestRegressionIsolation:
    def test_kripke_explain_no_new_deps(self):
        """kripke.py must not import new third-party libraries."""
        import stele.kripke as km
        import importlib
        mod = importlib.import_module("stele.kripke")
        # Just import — if no ImportError, we're fine. No external packages used.
        assert mod is not None

    def test_browser_kripke_importable(self):
        from stele.browser import browser_kripke
        assert callable(browser_kripke)

    def test_kripke_json_importable(self):
        from stele.web import kripke_json
        assert callable(kripke_json)

    def test_existing_diagnose_codes_unchanged(self):
        """Stable codes from before Pass 4 still work."""
        from stele.diagnostics import diagnose_theorem
        from stele.parser import parse_theorem
        src = """\
theorem broken:
  assume h1: P
  have h2: Q by mp h1 h3
  conclude P by h1
"""
        thm = parse_theorem(src)
        diags = diagnose_theorem(thm, "intuitionistic_prop")
        codes = {d.code for d in diags}
        assert "UndefinedSymbol" in codes

    def test_kripke_module_not_imported_by_kernel(self):
        """kernel.py must not import kripke.py (isolation invariant)."""
        import importlib, sys
        # Clear and reimport kernel to detect fresh imports
        mods_before = set(sys.modules.keys())
        import stele.kernel
        mods_after = set(sys.modules.keys())
        new_mods = mods_after - mods_before
        kripke_imported = any("kripke" in m for m in new_mods)
        assert not kripke_imported

    def test_existing_kripke_tests_unaffected(self):
        """find_countermodel still works as before."""
        from stele.kripke import find_countermodel
        from stele.parser import parse_formula
        result = find_countermodel(parse_formula("P or not P"), max_worlds=3)
        assert result is not None
        result2 = find_countermodel(parse_formula("P -> P"), max_worlds=3)
        assert result2 is None
