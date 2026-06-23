"""Tests for stele.kripke — finite Kripke semantics for intuitionistic logic.

Sections:
  A. Model construction and validation
  B. Forcing — atoms, connectives, negation
  C. Persistence (Beth's lemma)
  D. Countermodel search (P or not P, not not P -> P, Peirce, valid formulas)
  E. Classical separation
  F. Regression — matrix/world/kernel untouched
"""
import pytest
from stele.ast import Var, Op
from stele.parser import parse_formula
from stele.kripke import (
    KripkeModel, KripkeCountermodel, KripkeModelError,
    leq, successors, is_reflexive, is_transitive, is_antisymmetric,
    is_monotone_valuation, validate_model,
    forces, valid_in_model,
    find_countermodel, pretty_model,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def model1():
    """Trivial single-world model; P is false."""
    return KripkeModel(
        worlds=(0,),
        order=frozenset({(0, 0)}),
        valuation=frozenset(),
    )


def model1P():
    """Single-world model; P is true."""
    return KripkeModel(
        worlds=(0,),
        order=frozenset({(0, 0)}),
        valuation=frozenset({(0, "P")}),
    )


def model2():
    """Two-world linear model: 0 ≤ 1, P false at 0 and true at 1."""
    return KripkeModel(
        worlds=(0, 1),
        order=frozenset({(0, 0), (0, 1), (1, 1)}),
        valuation=frozenset({(1, "P")}),
    )


def model3():
    """Three-world chain: 0 ≤ 1 ≤ 2, P false at 0, true at 1 and 2."""
    return KripkeModel(
        worlds=(0, 1, 2),
        order=frozenset({(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2)}),
        valuation=frozenset({(1, "P"), (2, "P")}),
    )


P = Var("P")
Q = Var("Q")
bot = Op("bot", ())
neg = lambda f: Op("not", (f,))
imp = lambda a, b: Op("imp", (a, b))
conj = lambda a, b: Op("and", (a, b))
disj = lambda a, b: Op("or", (a, b))
dne = imp(neg(neg(P)), P)
lem = disj(P, neg(P))
peirce = imp(imp(imp(P, Q), P), P)
ppp = imp(P, P)


# ---------------------------------------------------------------------------
# A. Model construction and validation
# ---------------------------------------------------------------------------

class TestModelValidation:
    def test_valid_model1(self):
        validate_model(model1())  # no exception

    def test_valid_model2(self):
        validate_model(model2())

    def test_valid_model3(self):
        validate_model(model3())

    def test_non_reflexive_rejected(self):
        m = KripkeModel(
            worlds=(0, 1),
            order=frozenset({(0, 1), (1, 1)}),  # missing (0, 0)
            valuation=frozenset(),
        )
        with pytest.raises(KripkeModelError, match="reflexive"):
            validate_model(m)

    def test_non_transitive_rejected(self):
        # 0 ≤ 1, 1 ≤ 2, but 0 ≤ 2 is missing
        m = KripkeModel(
            worlds=(0, 1, 2),
            order=frozenset({(0, 0), (0, 1), (1, 1), (1, 2), (2, 2)}),
            valuation=frozenset(),
        )
        with pytest.raises(KripkeModelError, match="transitive"):
            validate_model(m)

    def test_non_monotone_valuation_rejected(self):
        # 0 ≤ 1, P true at 0 but false at 1 — violates persistence
        m = KripkeModel(
            worlds=(0, 1),
            order=frozenset({(0, 0), (0, 1), (1, 1)}),
            valuation=frozenset({(0, "P")}),  # P at 0 but not at 1
        )
        with pytest.raises(KripkeModelError, match="monotone|persistence"):
            validate_model(m)

    def test_order_references_unknown_world(self):
        m = KripkeModel(
            worlds=(0,),
            order=frozenset({(0, 0), (0, 99)}),
            valuation=frozenset(),
        )
        with pytest.raises(KripkeModelError, match="unknown world"):
            validate_model(m)

    def test_valuation_references_unknown_world(self):
        m = KripkeModel(
            worlds=(0,),
            order=frozenset({(0, 0)}),
            valuation=frozenset({(99, "P")}),
        )
        with pytest.raises(KripkeModelError, match="unknown world"):
            validate_model(m)

    def test_is_reflexive(self):
        assert is_reflexive(model2())

    def test_is_transitive(self):
        assert is_transitive(model3())

    def test_is_antisymmetric_chain(self):
        assert is_antisymmetric(model2())

    def test_is_not_antisymmetric_equiv(self):
        # 0 ≤ 1 and 1 ≤ 0 — preorder but not partial order
        m = KripkeModel(
            worlds=(0, 1),
            order=frozenset({(0, 0), (0, 1), (1, 0), (1, 1)}),
            valuation=frozenset(),
        )
        assert not is_antisymmetric(m)

    def test_leq_helper(self):
        m = model2()
        assert leq(m, 0, 0)
        assert leq(m, 0, 1)
        assert leq(m, 1, 1)
        assert not leq(m, 1, 0)

    def test_successors(self):
        m = model3()
        assert set(successors(m, 0)) == {0, 1, 2}
        assert set(successors(m, 1)) == {1, 2}
        assert set(successors(m, 2)) == {2}


# ---------------------------------------------------------------------------
# B. Forcing
# ---------------------------------------------------------------------------

class TestForcing:
    # atoms
    def test_atom_false_at_world_without_it(self):
        assert not forces(model2(), 0, P)

    def test_atom_true_at_world_with_it(self):
        assert forces(model2(), 1, P)

    def test_atom_false_single_world_no_val(self):
        assert not forces(model1(), 0, P)

    def test_atom_true_single_world_with_val(self):
        assert forces(model1P(), 0, P)

    # bottom
    def test_bot_never_forced(self):
        assert not forces(model1(), 0, bot)
        assert not forces(model2(), 0, bot)
        assert not forces(model2(), 1, bot)

    # conjunction
    def test_and_both_true(self):
        m = KripkeModel(
            worlds=(0,),
            order=frozenset({(0, 0)}),
            valuation=frozenset({(0, "P"), (0, "Q")}),
        )
        assert forces(m, 0, conj(P, Q))

    def test_and_one_false(self):
        m = KripkeModel(
            worlds=(0,),
            order=frozenset({(0, 0)}),
            valuation=frozenset({(0, "P")}),
        )
        assert not forces(m, 0, conj(P, Q))

    # disjunction
    def test_or_first_true(self):
        assert forces(model1P(), 0, disj(P, Q))

    def test_or_second_true(self):
        m = KripkeModel(
            worlds=(0,),
            order=frozenset({(0, 0)}),
            valuation=frozenset({(0, "Q")}),
        )
        assert forces(m, 0, disj(P, Q))

    def test_or_both_false(self):
        assert not forces(model1(), 0, disj(P, Q))

    # implication
    def test_imp_trivial_PP(self):
        assert forces(model1(), 0, ppp)
        assert forces(model2(), 0, ppp)
        assert forces(model2(), 1, ppp)

    def test_imp_false_when_P_true_Q_false(self):
        m = KripkeModel(
            worlds=(0,),
            order=frozenset({(0, 0)}),
            valuation=frozenset({(0, "P")}),
        )
        assert not forces(m, 0, imp(P, Q))

    def test_imp_rhs_weaker_world(self):
        # In model2: at world 0, P false, Q false
        # P -> Q at 0: for all v ≥ 0 (={0,1}), if v forces P then v forces Q
        # v=1: forces P but not Q. So fails.
        m = KripkeModel(
            worlds=(0, 1),
            order=frozenset({(0, 0), (0, 1), (1, 1)}),
            valuation=frozenset({(1, "P")}),
        )
        assert not forces(m, 0, imp(P, Q))

    # negation (= A -> false)
    def test_not_false_when_P_eventually_true(self):
        # model2: P true at 1, so not P should be false at 0 (successor 1 forces P)
        assert not forces(model2(), 0, neg(P))

    def test_not_true_when_P_never_true(self):
        # model1: P false; not P = for all v ≥ 0: not P(v). True.
        assert forces(model1(), 0, neg(P))

    def test_not_P_true_at_root_when_P_only_at_top(self):
        # model2: at world 1, P is true. not P at world 1: for all v ≥ 1 (={1}), not forces(v,P). forces(1,P)=True. False.
        assert not forces(model2(), 1, neg(P))

    # DNE failure (classical principle)
    def test_dne_fails_at_root_of_model2(self):
        assert not forces(model2(), 0, dne)

    # LEM failure
    def test_lem_fails_at_root_of_model2(self):
        assert not forces(model2(), 0, lem)

    # Closed intuitionistic tautologies hold
    def test_PP_valid_in_model2(self):
        assert valid_in_model(model2(), ppp)

    def test_PP_valid_in_model3(self):
        assert valid_in_model(model3(), ppp)

    def test_conjunction_to_first_valid(self):
        assert valid_in_model(model2(), imp(conj(P, Q), P))

    def test_modus_ponens_valid(self):
        # (P and (P -> Q)) -> Q
        assert valid_in_model(model2(), imp(conj(P, imp(P, Q)), Q))

    def test_explosion_valid(self):
        # false -> P
        assert valid_in_model(model2(), imp(bot, P))


# ---------------------------------------------------------------------------
# C. Persistence (Beth's lemma)
# ---------------------------------------------------------------------------

class TestPersistence:
    def _check_persistence(self, model, formula):
        for w in model.worlds:
            for v in model.worlds:
                if leq(model, w, v) and forces(model, w, formula):
                    assert forces(model, v, formula), (
                        f"persistence failed: w={w} forces {formula} "
                        f"but v={v} (≥ w) does not"
                    )

    def _formulas(self):
        return [P, Q, bot, conj(P, Q), disj(P, Q), imp(P, Q), neg(P),
                imp(P, P), dne, lem,
                imp(conj(P, Q), P), imp(P, disj(P, Q))]

    def _models(self):
        return [model1(), model1P(), model2(), model3()]

    def test_persistence_model1_formulas(self):
        for f in self._formulas():
            self._check_persistence(model1(), f)

    def test_persistence_model1P_formulas(self):
        for f in self._formulas():
            self._check_persistence(model1P(), f)

    def test_persistence_model2_formulas(self):
        for f in self._formulas():
            self._check_persistence(model2(), f)

    def test_persistence_model3_formulas(self):
        for f in self._formulas():
            self._check_persistence(model3(), f)

    def test_persistence_three_world_diamond(self):
        # Diamond: 0 ≤ 1, 0 ≤ 2, 1 ≤ 3, 2 ≤ 3
        m = KripkeModel(
            worlds=(0, 1, 2, 3),
            order=frozenset({
                (0, 0), (0, 1), (0, 2), (0, 3),
                (1, 1), (1, 3),
                (2, 2), (2, 3),
                (3, 3),
            }),
            valuation=frozenset({(1, "P"), (2, "P"), (3, "P")}),
        )
        validate_model(m)
        for f in self._formulas():
            self._check_persistence(m, f)


# ---------------------------------------------------------------------------
# D. Countermodel search
# ---------------------------------------------------------------------------

class TestCountermodelSearch:
    def test_lem_has_countermodel(self):
        cm = find_countermodel(lem)
        assert cm is not None
        assert isinstance(cm, KripkeCountermodel)
        assert not forces(cm.model, cm.world, lem)

    def test_dne_has_countermodel(self):
        cm = find_countermodel(dne)
        assert cm is not None
        assert not forces(cm.model, cm.world, dne)

    def test_peirce_has_countermodel(self):
        cm = find_countermodel(peirce, max_worlds=4)
        assert cm is not None
        assert not forces(cm.model, cm.world, peirce)

    def test_PP_no_countermodel(self):
        cm = find_countermodel(ppp)
        assert cm is None

    def test_bottom_false_has_countermodel(self):
        cm = find_countermodel(bot)
        assert cm is not None

    def test_false_to_P_no_countermodel(self):
        cm = find_countermodel(imp(bot, P))
        assert cm is None

    def test_conjunction_intro_no_countermodel(self):
        # P -> Q -> P and Q
        f = imp(P, imp(Q, conj(P, Q)))
        assert find_countermodel(f) is None

    def test_countermodel_is_valid_model(self):
        cm = find_countermodel(lem)
        assert cm is not None
        validate_model(cm.model)  # must be well-formed

    def test_countermodel_world_in_model(self):
        cm = find_countermodel(dne)
        assert cm is not None
        assert cm.world in cm.model.worlds

    def test_lem_countermodel_at_expected_world(self):
        cm = find_countermodel(lem)
        assert cm is not None
        # The failing world must genuinely not force LEM
        assert not forces(cm.model, cm.world, lem)
        # And the model must be validated
        validate_model(cm.model)

    def test_max_worlds_1_no_countermodel_PP(self):
        cm = find_countermodel(ppp, max_worlds=1)
        assert cm is None

    def test_lem_countermodel_within_2_worlds(self):
        # A 2-world linear model is sufficient for LEM
        cm = find_countermodel(lem, max_worlds=2)
        assert cm is not None

    def test_dne_countermodel_within_2_worlds(self):
        cm = find_countermodel(dne, max_worlds=2)
        assert cm is not None

    def test_countermodel_determinism(self):
        # Same formula, same max_worlds → same result every call
        cm1 = find_countermodel(lem)
        cm2 = find_countermodel(lem)
        assert cm1 is not None and cm2 is not None
        assert cm1.model == cm2.model
        assert cm1.world == cm2.world

    def test_parsed_lem(self):
        f = parse_formula("P or not P")
        cm = find_countermodel(f)
        assert cm is not None
        assert not forces(cm.model, cm.world, f)

    def test_parsed_dne(self):
        f = parse_formula("not not P -> P")
        cm = find_countermodel(f)
        assert cm is not None
        assert not forces(cm.model, cm.world, f)

    def test_parsed_pp(self):
        f = parse_formula("P -> P")
        assert find_countermodel(f) is None

    def test_parsed_modus_ponens(self):
        f = parse_formula("P and (P -> Q) -> Q")
        assert find_countermodel(f) is None


# ---------------------------------------------------------------------------
# E. Classical separation
# ---------------------------------------------------------------------------

class TestClassicalSeparation:
    def test_lem_invalid_intuitionistically(self):
        # LEM should fail in some finite Kripke model
        cm = find_countermodel(lem)
        assert cm is not None

    def test_dne_invalid_intuitionistically(self):
        cm = find_countermodel(dne)
        assert cm is not None

    def test_peirce_invalid_intuitionistically(self):
        cm = find_countermodel(peirce, max_worlds=4)
        assert cm is not None

    def test_intuitionistic_tautologies_have_no_countermodel(self):
        intuit_valid = [
            parse_formula("P -> P"),
            parse_formula("P -> P or Q"),
            parse_formula("P and Q -> P"),
            parse_formula("P and Q -> Q"),
            parse_formula("P -> Q -> P"),
            parse_formula("(P -> Q -> R) -> (P -> Q) -> P -> R"),
            parse_formula("false -> P"),
            parse_formula("(P -> false) -> not P"),
            parse_formula("not P -> P -> false"),
        ]
        for f in intuit_valid:
            cm = find_countermodel(f, max_worlds=4)
            assert cm is None, f"unexpected countermodel for {f}"

    def test_lem_valid_in_boolean_matrix(self):
        # Sanity check: LEM is a tautology classically (matrix semantics)
        from stele.matrix import MATRICES, is_tautology
        assert is_tautology(lem, MATRICES["boolean"])

    def test_lem_not_valid_in_kripke(self):
        # LEM is not Kripke-valid for intuitionistic logic
        cm = find_countermodel(lem)
        assert cm is not None

    def test_dne_valid_in_boolean_matrix(self):
        from stele.matrix import MATRICES, is_tautology
        assert is_tautology(dne, MATRICES["boolean"])

    def test_dne_not_valid_in_kripke(self):
        cm = find_countermodel(dne)
        assert cm is not None


# ---------------------------------------------------------------------------
# F. Regression — existing modules unchanged
# ---------------------------------------------------------------------------

class TestRegression:
    def test_matrix_module_unchanged(self):
        from stele.matrix import MATRICES, is_tautology
        m = MATRICES["boolean"]
        assert is_tautology(Var("P"), m) is False
        assert is_tautology(lem, m) is True

    def test_world_module_unchanged(self):
        from stele.world import World, status, INDEPENDENT, PROVABLE
        w = World("boolean", ())
        assert status(Var("P"), w) == INDEPENDENT

    def test_kernel_unchanged(self):
        from stele.parser import parse_theorem
        from stele.kernel import check_theorem
        src = """
theorem identity:
  assume h: P
  conclude P by h
"""
        check_theorem(parse_theorem(src), "intuitionistic_prop")

    def test_no_new_runtime_deps(self):
        """kripke.py must not import third-party packages."""
        import ast as pyast
        import pathlib
        src = pathlib.Path(__file__).parent.parent / "stele" / "kripke.py"
        tree = pyast.parse(src.read_text(encoding="utf-8"))
        for node in pyast.walk(tree):
            if not isinstance(node, (pyast.Import, pyast.ImportFrom)):
                continue
            if isinstance(node, pyast.ImportFrom):
                if node.level and node.level > 0:
                    continue
                mod = node.module or ""
            else:
                mod = node.names[0].name
            stdlib = {"__future__", "itertools", "dataclasses", "typing"}
            top = mod.split(".")[0]
            if top not in stdlib and top != "stele":
                raise AssertionError(f"kripke.py imports third-party module: {mod!r}")

    def test_kernel_not_imported_by_kripke(self):
        import ast as pyast, pathlib
        src = pathlib.Path(__file__).parent.parent / "stele" / "kripke.py"
        tree = pyast.parse(src.read_text(encoding="utf-8"))
        for node in pyast.walk(tree):
            if isinstance(node, pyast.ImportFrom) and node.module == "stele.kernel":
                raise AssertionError("kripke.py must not import kernel.py")

    def test_pretty_model_runs(self):
        s = pretty_model(model2())
        assert "worlds" in s
        assert "world 0" in s
        assert "world 1" in s
