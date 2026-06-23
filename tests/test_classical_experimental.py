"""Tests for the experimental classical proof-term bridge.

Covers:
  - Formula-level Gödel–Gentzen translation (atoms, connectives, bottom)
  - Glivenko mode
  - Classical principle detection
  - Bridge helper: check_negative_translation
  - Hand-written proof terms for translated classical principles
  - Isolation: no side effects on intuitionistic core
  - Status honesty: module is experimental
"""
import pytest
from stele.ast import Var, Op

# Formula shorthand
P = Var("P")
Q = Var("Q")
R = Var("R")
BOT = Op("bot", ())


def _not(f):
    return Op("imp", (f, BOT))


def _nn(f):
    return _not(_not(f))


# ---------------------------------------------------------------------------
# Part F.1 — Formula translation
# ---------------------------------------------------------------------------

class TestAtomTranslation:
    def test_atom_becomes_double_negation(self):
        from stele.core.classical_experimental import negative_translate_formula
        result = negative_translate_formula(P)
        assert result == _nn(P)

    def test_different_atoms(self):
        from stele.core.classical_experimental import negative_translate_formula
        assert negative_translate_formula(Q) == _nn(Q)
        assert negative_translate_formula(R) == _nn(R)


class TestBottomTranslation:
    def test_bottom_is_self_dual(self):
        from stele.core.classical_experimental import negative_translate_formula
        assert negative_translate_formula(BOT) == BOT


class TestConjunctionTranslation:
    def test_conjunction_structural(self):
        from stele.core.classical_experimental import negative_translate_formula
        f = Op("and", (P, Q))
        result = negative_translate_formula(f)
        assert result == Op("and", (_nn(P), _nn(Q)))

    def test_nested_conjunction(self):
        from stele.core.classical_experimental import negative_translate_formula
        f = Op("and", (Op("and", (P, Q)), R))
        result = negative_translate_formula(f)
        expected = Op("and", (Op("and", (_nn(P), _nn(Q))), _nn(R)))
        assert result == expected


class TestImplicationTranslation:
    def test_implication_structural(self):
        from stele.core.classical_experimental import negative_translate_formula
        f = Op("imp", (P, Q))
        result = negative_translate_formula(f)
        assert result == Op("imp", (_nn(P), _nn(Q)))

    def test_nested_implication(self):
        from stele.core.classical_experimental import negative_translate_formula
        f = Op("imp", (P, Op("imp", (Q, R))))
        result = negative_translate_formula(f)
        expected = Op("imp", (_nn(P), Op("imp", (_nn(Q), _nn(R)))))
        assert result == expected


class TestNegationTranslation:
    def test_negation_translates_body(self):
        from stele.core.classical_experimental import negative_translate_formula
        f = Op("not", (P,))
        result = negative_translate_formula(f)
        # ¬A → ¬(A^N) = (A^N → ⊥) = (¬¬P → ⊥)
        assert result == _not(_nn(P))

    def test_double_negation(self):
        from stele.core.classical_experimental import negative_translate_formula
        f = Op("not", (Op("not", (P,)),))
        result = negative_translate_formula(f)
        # ¬(¬P) → ¬((¬P)^N) = ¬(¬(P^N)) = ¬(¬(¬¬P))
        assert result == _not(_not(_nn(P)))


class TestDisjunctionTranslation:
    def test_disjunction_negative_encoding(self):
        from stele.core.classical_experimental import negative_translate_formula
        f = Op("or", (P, Q))
        result = negative_translate_formula(f)
        # (A ∨ B)^N = ¬(¬A^N ∧ ¬B^N)
        expected = _not(Op("and", (_not(_nn(P)), _not(_nn(Q)))))
        assert result == expected

    def test_disjunction_with_complex_disjuncts(self):
        from stele.core.classical_experimental import negative_translate_formula
        f = Op("or", (Op("and", (P, Q)), R))
        result = negative_translate_formula(f)
        a_n = Op("and", (_nn(P), _nn(Q)))
        b_n = _nn(R)
        expected = _not(Op("and", (_not(a_n), _not(b_n))))
        assert result == expected


class TestGlivenkoMode:
    def test_glivenko_wraps_in_double_negation(self):
        from stele.core.classical_experimental import negative_translate_formula
        result_gg = negative_translate_formula(P, mode="godel_gentzen")
        result_gl = negative_translate_formula(P, mode="glivenko")
        assert result_gl == _nn(result_gg)

    def test_glivenko_bottom(self):
        from stele.core.classical_experimental import negative_translate_formula
        result = negative_translate_formula(BOT, mode="glivenko")
        assert result == _nn(BOT)

    def test_unknown_mode_raises(self):
        from stele.core.classical_experimental import negative_translate_formula
        with pytest.raises(ValueError, match="unknown translation mode"):
            negative_translate_formula(P, mode="kolmogorov")


class TestUnsupportedFormulas:
    def test_quantifier_rejected(self):
        from stele.ast import Forall
        from stele.core.classical_experimental import negative_translate_formula
        f = Forall("x", P)
        with pytest.raises(ValueError, match="propositional"):
            negative_translate_formula(f)

    def test_unknown_op_rejected(self):
        from stele.core.classical_experimental import negative_translate_formula
        f = Op("xor", (P, Q))
        with pytest.raises(ValueError, match="unsupported connective"):
            negative_translate_formula(f)


# ---------------------------------------------------------------------------
# Part F.2 — Classical principle translations
# ---------------------------------------------------------------------------

class TestClassicalPrincipleTranslations:
    def test_lem_translation(self):
        from stele.core.classical_experimental import negative_translate_formula
        lem = Op("or", (P, Op("not", (P,))))
        result = negative_translate_formula(lem)
        # LEM^N = ¬(¬(¬¬P) ∧ ¬(¬(¬¬P))) = ¬(¬(¬¬P) ∧ ¬(¬(¬¬P)))
        pn = _nn(P)
        neg_pn = _not(pn)
        expected = _not(Op("and", (_not(pn), _not(neg_pn))))
        assert result == expected

    def test_dne_translation(self):
        from stele.core.classical_experimental import negative_translate_formula
        dne = Op("imp", (Op("not", (Op("not", (P,)),)), P))
        result = negative_translate_formula(dne)
        # DNE^N = (¬¬P)^N → P^N = ¬(¬(¬¬P)) → ¬¬P
        pn = _nn(P)
        expected = Op("imp", (_not(_not(pn)), pn))
        assert result == expected

    def test_peirce_translation(self):
        from stele.core.classical_experimental import negative_translate_formula
        peirce = Op("imp", (Op("imp", (Op("imp", (P, Q)), P)), P))
        result = negative_translate_formula(peirce)
        pn = _nn(P)
        qn = _nn(Q)
        expected = Op("imp", (Op("imp", (Op("imp", (pn, qn)), pn)), pn))
        assert result == expected


# ---------------------------------------------------------------------------
# Part F.2 — Classical principle detection
# ---------------------------------------------------------------------------

class TestClassicalPrincipleDetection:
    def test_detect_lem(self):
        from stele.core.classical_experimental import classical_principle_name
        lem = Op("or", (P, Op("not", (P,))))
        assert classical_principle_name(lem) == "lem"

    def test_detect_dne(self):
        from stele.core.classical_experimental import classical_principle_name
        dne = Op("imp", (Op("not", (Op("not", (P,)),)), P))
        assert classical_principle_name(dne) == "dne"

    def test_detect_peirce(self):
        from stele.core.classical_experimental import classical_principle_name
        peirce = Op("imp", (Op("imp", (Op("imp", (P, Q)), P)), P))
        assert classical_principle_name(peirce) == "peirce"

    def test_unrecognised_returns_none(self):
        from stele.core.classical_experimental import classical_principle_name
        assert classical_principle_name(P) is None
        assert classical_principle_name(Op("and", (P, Q))) is None

    def test_lem_with_different_vars(self):
        from stele.core.classical_experimental import classical_principle_name
        lem = Op("or", (Q, Op("not", (Q,))))
        assert classical_principle_name(lem) == "lem"


class TestIsSupportedPredicate:
    def test_propositional_supported(self):
        from stele.core.classical_experimental import is_negative_translation_supported
        assert is_negative_translation_supported(P) is True
        assert is_negative_translation_supported(BOT) is True
        assert is_negative_translation_supported(Op("and", (P, Q))) is True
        assert is_negative_translation_supported(Op("imp", (P, Q))) is True
        assert is_negative_translation_supported(Op("or", (P, Q))) is True
        assert is_negative_translation_supported(Op("not", (P,))) is True

    def test_quantifier_unsupported(self):
        from stele.ast import Forall, Exists
        from stele.core.classical_experimental import is_negative_translation_supported
        assert is_negative_translation_supported(Forall("x", P)) is False
        assert is_negative_translation_supported(Exists("x", P)) is False

    def test_predicate_unsupported(self):
        from stele.ast import Pred
        from stele.core.classical_experimental import is_negative_translation_supported
        assert is_negative_translation_supported(Pred("R", ())) is False

    def test_unknown_op_unsupported(self):
        from stele.core.classical_experimental import is_negative_translation_supported
        assert is_negative_translation_supported(Op("xor", (P, Q))) is False


# ---------------------------------------------------------------------------
# Part F.4 — Bridge helper
# ---------------------------------------------------------------------------

class TestCheckNegativeTranslation:
    """Test the explicit-term bridge for translated classical principles."""

    def test_dne_translated_proof_term(self):
        """DNE^N = ¬¬(¬¬P) → ¬¬P is intuitionistically provable.

        Proof: λh:(((P→⊥)→⊥)→⊥)→⊥. λk:P→⊥. h(λf:(P→⊥)→⊥. f k)
        """
        from stele.core.classical_experimental import check_negative_translation
        from stele.core.terms import Lam, App, TVar

        nnP = _nn(P)     # (P→⊥)→⊥
        nnnP = _not(nnP)  # ((P→⊥)→⊥)→⊥
        nnnnP = _not(nnnP)  # (((P→⊥)→⊥)→⊥)→⊥
        nP = _not(P)      # P→⊥

        # λh:¬¬¬¬P. λk:¬P. h(λf:¬¬P. f k)
        term = Lam("h", nnnnP,
                   Lam("k", nP,
                       App(TVar("h"),
                           Lam("f", nnP,
                               App(TVar("f"), TVar("k"))))))

        dne_formula = Op("imp", (Op("not", (Op("not", (P,)),)), P))
        result = check_negative_translation(term, dne_formula)
        # Should return the translated formula without raising
        assert result is not None

    def test_bad_term_rejected(self):
        """A wrong proof term should be rejected by the bridge."""
        from stele.core.classical_experimental import check_negative_translation
        from stele.core.terms import TVar
        from stele.core.typing import TypingError

        dne_formula = Op("imp", (Op("not", (Op("not", (P,)),)), P))
        with pytest.raises(TypingError):
            check_negative_translation(TVar("x"), dne_formula)

    def test_non_propositional_rejected(self):
        """Non-propositional formulas should be rejected."""
        from stele.ast import Forall
        from stele.core.classical_experimental import check_negative_translation
        from stele.core.terms import TVar

        with pytest.raises(ValueError, match="non-propositional"):
            check_negative_translation(TVar("x"), Forall("x", P))

    def test_identity_proof_for_simple_formula(self):
        """P → P is classically and intuitionistically valid.

        (P → P)^N = ¬¬P → ¬¬P, provable by λx.x (identity).
        """
        from stele.core.classical_experimental import check_negative_translation
        from stele.core.terms import Lam, TVar

        term = Lam("x", _nn(P), TVar("x"))
        formula = Op("imp", (P, P))
        result = check_negative_translation(term, formula)
        assert result is not None

    def test_translate_type_alias(self):
        """translate_type_for_intuitionistic_check should match negative_translate_formula."""
        from stele.core.classical_experimental import (
            translate_type_for_intuitionistic_check,
            negative_translate_formula,
        )
        f = Op("or", (P, Op("not", (P,))))
        assert translate_type_for_intuitionistic_check(f) == negative_translate_formula(f)

    def test_bridge_with_context(self):
        """Bridge accepts a non-empty context."""
        from stele.core.classical_experimental import check_negative_translation
        from stele.core.terms import TVar

        ctx = {"h": _nn(P)}
        term = TVar("h")
        # P^N = ¬¬P; "h : ¬¬P ⊢ h : ¬¬P" checks
        result = check_negative_translation(term, P, ctx=ctx)
        assert result == _nn(P)

    def test_explosion_translated(self):
        """(false → P)^N = false → ¬¬P, provable by ex falso."""
        from stele.core.classical_experimental import check_negative_translation
        from stele.core.terms import Lam, Abort, TVar

        term = Lam("x", BOT, Abort(TVar("x"), _nn(P)))
        formula = Op("imp", (BOT, P))
        result = check_negative_translation(term, formula)
        assert result is not None


# ---------------------------------------------------------------------------
# Part F.3 — Isolation
# ---------------------------------------------------------------------------

class TestIsolation:
    def test_import_has_no_side_effects(self):
        """Importing classical_experimental does not modify other modules."""
        import stele.core.typing as ty_before
        infer_before = ty_before.infer
        check_before = ty_before.check

        import stele.core.classical_experimental  # noqa: F401

        import stele.core.typing as ty_after
        assert ty_after.infer is infer_before
        assert ty_after.check is check_before

    def test_existing_intuitionistic_typing_unchanged(self):
        """Standard intuitionistic proof term still type-checks."""
        from stele.core.typing import infer, empty_ctx
        from stele.core.terms import Lam, TVar

        # λx:P. x  :  P → P
        term = Lam("x", P, TVar("x"))
        result = infer(empty_ctx(), term)
        assert result == Op("imp", (P, P))

    def test_kernel_not_modified(self):
        """classical_experimental does not import or modify the kernel."""
        import sys
        mods_before = set(sys.modules.keys())
        import stele.core.classical_experimental  # noqa: F401
        # kernel should not have been imported as a side effect
        new_mods = set(sys.modules.keys()) - mods_before
        assert not any("kernel" in m for m in new_mods)

    def test_no_new_constructors_in_terms(self):
        """No classical constructors were added to stele.core.terms."""
        import stele.core.terms as t
        constructors = {
            name for name in dir(t)
            if not name.startswith("_") and isinstance(getattr(t, name), type)
        }
        expected = {
            "TVar", "Lam", "App", "Pair", "Fst", "Snd",
            "Inl", "Inr", "Case", "Abort",
            "ForallIntro", "ForallElim", "ExistsIntro", "ExistsElim",
        }
        assert constructors == expected

    def test_classical_script_rules_unchanged(self):
        """Proof-script classical rules (dne, lem, pbc) remain in logic.py."""
        from stele.logic import get_logic
        cl = get_logic("classical_prop")
        rule_names = set(cl.rules.keys())
        assert "dne" in rule_names
        assert "lem" in rule_names
        assert "pbc" in rule_names


# ---------------------------------------------------------------------------
# Part F.5 — Status honesty
# ---------------------------------------------------------------------------

class TestStatusHonesty:
    def test_module_docstring_says_experimental(self):
        import stele.core.classical_experimental as mod
        assert "EXPERIMENTAL" in mod.__doc__ or "experimental" in mod.__doc__.lower()

    def test_module_docstring_disclaims_lambda_mu(self):
        import stele.core.classical_experimental as mod
        doc = mod.__doc__.lower()
        assert "control operator" in doc or "callcc" in doc or "μ" in doc


# ---------------------------------------------------------------------------
# Part F.6 — Regression
# ---------------------------------------------------------------------------

class TestRegression:
    def test_existing_proof_term_tests_would_pass(self):
        """Spot-check: standard proof terms work as before."""
        from stele.core.typing import infer, check, empty_ctx
        from stele.core.terms import Lam, App, TVar, Pair, Fst, Snd

        ctx = empty_ctx()

        # P → Q → P (K combinator)
        k = Lam("x", P, Lam("y", Q, TVar("x")))
        ty = infer(ctx, k)
        assert ty == Op("imp", (P, Op("imp", (Q, P))))

        # fst(pair(x, y)) : P
        ctx2 = {"x": P, "y": Q}
        term = Fst(Pair(TVar("x"), TVar("y")))
        check(ctx2, term, P)

    def test_typing_error_still_raised(self):
        """TypingError is raised for bad terms, not silenced."""
        from stele.core.typing import infer, empty_ctx, TypingError
        from stele.core.terms import TVar

        with pytest.raises(TypingError, match="unbound"):
            infer(empty_ctx(), TVar("nonexistent"))

    def test_classical_experimental_module_path(self):
        """Module can be imported by its full path."""
        from stele.core.classical_experimental import (
            negative_translate_formula,
            check_negative_translation,
            is_negative_translation_supported,
            classical_principle_name,
            translate_type_for_intuitionistic_check,
        )
        # All public functions exist and are callable
        assert callable(negative_translate_formula)
        assert callable(check_negative_translation)
        assert callable(is_negative_translation_supported)
        assert callable(classical_principle_name)
        assert callable(translate_type_for_intuitionistic_check)
