"""Tests for stele/world.py: semantic world status.

A World = (matrix_name, axioms) defines a semantic context.
status(φ, world) returns PROVABLE / REFUTABLE / BOTH / INDEPENDENT
by calling matrix entailment twice (for φ and ¬φ).

All assertions here are about matrix semantics, not proof derivability.
"""
import pytest
from stele.parser import parse_formula
from stele.world import World, status, PROVABLE, REFUTABLE, BOTH, INDEPENDENT
from stele.errors import SteleError


def _w(matrix_name, *formula_strings):
    """Build a World from formula strings."""
    return World(matrix_name, tuple(parse_formula(s) for s in formula_strings))


# ---------------------------------------------------------------------------
# Boolean empty world: classical tautologies and contradictions
# ---------------------------------------------------------------------------

def test_boolean_lem_provable():
    """P or not P is a boolean tautology: PROVABLE."""
    assert status(parse_formula("P or not P"), _w("boolean")) == PROVABLE


def test_boolean_atom_independent():
    """In an empty boolean world, P is contingent: INDEPENDENT."""
    assert status(parse_formula("P"), _w("boolean")) == INDEPENDENT


def test_boolean_contradiction_refutable():
    """P and not P is a contradiction in boolean: REFUTABLE."""
    assert status(parse_formula("P and not P"), _w("boolean")) == REFUTABLE


def test_boolean_implication_tautology_provable():
    """P -> P is a tautology in boolean: PROVABLE."""
    assert status(parse_formula("P -> P"), _w("boolean")) == PROVABLE


# ---------------------------------------------------------------------------
# Boolean world with axioms
# ---------------------------------------------------------------------------

def test_boolean_axiom_p_provable():
    """Axiom P: P itself is PROVABLE."""
    assert status(parse_formula("P"), _w("boolean", "P")) == PROVABLE


def test_boolean_axiom_not_p_refutable():
    """Axiom not P: P is REFUTABLE (negation entailed)."""
    assert status(parse_formula("P"), _w("boolean", "not P")) == REFUTABLE


def test_boolean_axiom_p_q_independent():
    """Axiom P: unrelated Q is INDEPENDENT."""
    assert status(parse_formula("Q"), _w("boolean", "P")) == INDEPENDENT


def test_boolean_mp_axioms_q_provable():
    """Axioms P->Q and P entail Q: PROVABLE."""
    assert status(parse_formula("Q"), _w("boolean", "P -> Q", "P")) == PROVABLE


def test_boolean_and_intro_axioms():
    """Axioms P and Q entail P and Q: PROVABLE."""
    assert status(parse_formula("P and Q"), _w("boolean", "P", "Q")) == PROVABLE


# ---------------------------------------------------------------------------
# K3 empty world: LEM is not provable
# ---------------------------------------------------------------------------

def test_k3_lem_not_provable():
    """P or not P is NOT a K3 tautology: must not be PROVABLE."""
    s = status(parse_formula("P or not P"), _w("K3"))
    assert s != PROVABLE


def test_k3_lem_independent():
    """P or not P is INDEPENDENT in K3 (not provable and not refutable)."""
    assert status(parse_formula("P or not P"), _w("K3")) == INDEPENDENT


def test_k3_atom_independent():
    """In an empty K3 world, P is INDEPENDENT."""
    assert status(parse_formula("P"), _w("K3")) == INDEPENDENT


def test_k3_axiom_p_provable():
    """Axiom P in K3: P is PROVABLE."""
    assert status(parse_formula("P"), _w("K3", "P")) == PROVABLE


def test_k3_axiom_not_p_refutable():
    """Axiom not P in K3: P is REFUTABLE."""
    assert status(parse_formula("P"), _w("K3", "not P")) == REFUTABLE


def test_k3_imp_pp_provable():
    """P -> P is PROVABLE in K3 (empty world) via modus ponens soundness."""
    # entails([], P->P, K3): check all K3 valuations.
    # For any val, P->P = max(not P, P) -- always >= P, specifically:
    # P=F: max(T,F)=T; P=I: max(I,I)=I (NOT designated!); P=T: max(F,T)=T
    # So P->P with P=I gives I, not designated -- P->P is actually NOT a K3 tautology.
    s = status(parse_formula("P -> P"), _w("K3"))
    # K3: P->P with P=I gives I (not designated) -- INDEPENDENT
    assert s == INDEPENDENT


# ---------------------------------------------------------------------------
# LP empty world: paraconsistent properties
# ---------------------------------------------------------------------------

def test_lp_lem_provable():
    """P or not P is PROVABLE in LP (B is designated, A or not A always in {T,B})."""
    assert status(parse_formula("P or not P"), _w("LP")) == PROVABLE


def test_lp_atom_independent():
    """In an empty LP world, P is INDEPENDENT."""
    assert status(parse_formula("P"), _w("LP")) == INDEPENDENT


# ---------------------------------------------------------------------------
# LP inconsistent world: BOTH status (paraconsistency)
# ---------------------------------------------------------------------------

def test_lp_both_p():
    """LP world with axioms P and not P: P has status BOTH."""
    w = _w("LP", "P", "not P")
    assert status(parse_formula("P"), w) == BOTH


def test_lp_both_not_p():
    """LP world with axioms P and not P: not P also has status BOTH."""
    w = _w("LP", "P", "not P")
    assert status(parse_formula("not P"), w) == BOTH


def test_lp_both_conjunction():
    """LP world with axioms P and not P: P and not P has status BOTH."""
    w = _w("LP", "P", "not P")
    assert status(parse_formula("P and not P"), w) == BOTH


def test_lp_axiom_p_q_independent():
    """LP: axiom P, unrelated Q is INDEPENDENT."""
    assert status(parse_formula("Q"), _w("LP", "P")) == INDEPENDENT


# ---------------------------------------------------------------------------
# World is a frozen dataclass: equality and hashability
# ---------------------------------------------------------------------------

def test_world_equality():
    w1 = _w("boolean", "P")
    w2 = _w("boolean", "P")
    assert w1 == w2


def test_world_inequality_different_matrix():
    w1 = _w("K3")
    w2 = _w("LP")
    assert w1 != w2


def test_world_hashable():
    w = _w("K3")
    mapping = {w: "value"}
    assert mapping[w] == "value"


def test_world_default_axioms():
    w = World("boolean")
    assert w.axioms == ()


def test_world_immutable():
    w = World("boolean", ())
    with pytest.raises((TypeError, AttributeError)):
        w.matrix_name = "K3"  # type: ignore


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_unknown_matrix_raises():
    w = World("nonexistent", ())
    with pytest.raises(SteleError):
        status(parse_formula("P"), w)
