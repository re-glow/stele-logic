"""Finite Kripke semantics for propositional intuitionistic logic.

A KripkeModel encodes a finite Kripke frame with a monotone valuation:

  worlds    — finite tuple of world identifiers (integers by default)
  order     — reflexive-transitive preorder as frozenset of (w, v) pairs
  valuation — monotone atom assignment as frozenset of (world, atom_name) pairs

The intuitionistic forcing relation  w ⊩ A  is:

  w ⊩ P          iff  (w, "P") ∈ valuation
  w ⊩ false       never
  w ⊩ A ∧ B      iff  w ⊩ A  and  w ⊩ B
  w ⊩ A ∨ B      iff  w ⊩ A  or   w ⊩ B
  w ⊩ A → B      iff  for all v ≥ w:  v ⊩ A  implies  v ⊩ B
  w ⊩ ¬A         iff  for all v ≥ w:  not v ⊩ A   (= A → false)

Persistence (Beth's lemma): if w ≤ v and w ⊩ A, then v ⊩ A.

find_countermodel performs bounded exhaustive search over small finite models.
A None result means "no countermodel found within the bound" — it is NOT a
proof of intuitionistic validity (no completeness claim is made).
"""
from __future__ import annotations
import itertools
from dataclasses import dataclass
from typing import Optional

from .ast import Var, Op


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KripkeModel:
    """Finite Kripke model for propositional intuitionistic logic.

    worlds     — tuple of world names (integers in normal use)
    order      — frozenset of (w, v) pairs encoding  w ≤ v
    valuation  — frozenset of (world, atom_name) pairs; (w, "P") means w ⊩ P
    """
    worlds: tuple
    order: frozenset      # frozenset of (w, v) pairs, including reflexive
    valuation: frozenset  # frozenset of (world, atom_name) pairs


@dataclass(frozen=True)
class KripkeCountermodel:
    """A finite Kripke countermodel: the formula fails at world in model."""
    model: KripkeModel
    world: object    # the world where the formula is not forced
    formula: object  # the formula that fails


class KripkeModelError(Exception):
    """Raised when a KripkeModel is not well-formed."""


# ---------------------------------------------------------------------------
# Model properties
# ---------------------------------------------------------------------------

def leq(model: KripkeModel, w, v) -> bool:
    """True iff w ≤ v in model."""
    return (w, v) in model.order


def successors(model: KripkeModel, w) -> tuple:
    """Worlds v such that w ≤ v (including w itself)."""
    return tuple(v for v in model.worlds if (w, v) in model.order)


def is_reflexive(model: KripkeModel) -> bool:
    return all((w, w) in model.order for w in model.worlds)


def is_transitive(model: KripkeModel) -> bool:
    for w in model.worlds:
        for v in model.worlds:
            if (w, v) not in model.order:
                continue
            for u in model.worlds:
                if (v, u) in model.order and (w, u) not in model.order:
                    return False
    return True


def is_antisymmetric(model: KripkeModel) -> bool:
    """True iff the order is antisymmetric (partial order, not just preorder)."""
    for w in model.worlds:
        for v in model.worlds:
            if w != v and (w, v) in model.order and (v, w) in model.order:
                return False
    return True


def is_monotone_valuation(model: KripkeModel) -> bool:
    """True iff valuation respects persistence: w ≤ v and w ⊩ P implies v ⊩ P."""
    for (w, atom) in model.valuation:
        for v in model.worlds:
            if (w, v) in model.order and (v, atom) not in model.valuation:
                return False
    return True


def validate_model(model: KripkeModel) -> None:
    """Validate well-formedness; raise KripkeModelError if invalid."""
    worlds_set = frozenset(model.worlds)
    for (w, v) in model.order:
        if w not in worlds_set:
            raise KripkeModelError(f"order references unknown world {w!r}")
        if v not in worlds_set:
            raise KripkeModelError(f"order references unknown world {v!r}")
    for (w, _) in model.valuation:
        if w not in worlds_set:
            raise KripkeModelError(f"valuation references unknown world {w!r}")
    if not is_reflexive(model):
        raise KripkeModelError("order is not reflexive (every world must relate to itself)")
    if not is_transitive(model):
        raise KripkeModelError("order is not transitive")
    if not is_monotone_valuation(model):
        raise KripkeModelError(
            "valuation violates persistence: atom forced at w must be forced at all v ≥ w"
        )


# ---------------------------------------------------------------------------
# Forcing relation
# ---------------------------------------------------------------------------

def forces(model: KripkeModel, w, formula) -> bool:
    """Intuitionistic forcing: True iff w ⊩ formula in model."""
    if isinstance(formula, Var):
        return (w, formula.name) in model.valuation
    if not isinstance(formula, Op):
        raise ValueError(
            f"forces: unsupported formula type {type(formula).__name__!r}; "
            "Kripke semantics covers propositional logic only"
        )
    sym = formula.sym
    if sym == "bot":
        return False
    if sym == "not":
        A = formula.args[0]
        return all(not forces(model, v, A) for v in successors(model, w))
    if sym == "and":
        return forces(model, w, formula.args[0]) and forces(model, w, formula.args[1])
    if sym == "or":
        return forces(model, w, formula.args[0]) or forces(model, w, formula.args[1])
    if sym == "imp":
        A, B = formula.args
        return all(
            not forces(model, v, A) or forces(model, v, B)
            for v in successors(model, w)
        )
    raise ValueError(f"forces: unknown connective {sym!r}")


def valid_in_model(model: KripkeModel, formula) -> bool:
    """True iff formula is forced at every world in the model."""
    return all(forces(model, w, formula) for w in model.worlds)


# ---------------------------------------------------------------------------
# Propositional atom extraction
# ---------------------------------------------------------------------------

def _atoms(formula) -> set:
    if isinstance(formula, Var):
        return {formula.name}
    if isinstance(formula, Op):
        result: set = set()
        for arg in formula.args:
            result |= _atoms(arg)
        return result
    return set()


# ---------------------------------------------------------------------------
# Countermodel search — internal helpers
# ---------------------------------------------------------------------------

def _all_preorders(n: int):
    """Generate all reflexive-transitive relations on {0, …, n-1}.

    Yields frozensets of (i, j) pairs (including reflexive pairs).
    """
    refl = frozenset((i, i) for i in range(n))
    non_refl = [(i, j) for i in range(n) for j in range(n) if i != j]
    for combo in _powerset_iter(non_refl):
        order = refl | frozenset(combo)
        if _transitive_check(n, order):
            yield order


def _powerset_iter(seq):
    for r in range(len(seq) + 1):
        yield from itertools.combinations(seq, r)


def _transitive_check(n: int, order: frozenset) -> bool:
    for i in range(n):
        for j in range(n):
            if (i, j) not in order:
                continue
            for k in range(n):
                if (j, k) in order and (i, k) not in order:
                    return False
    return True


def _upward_closed_sets(n: int, order: frozenset):
    """Yield all upward-closed subsets of {0,...,n-1} under order."""
    for bits in range(1 << n):
        worlds = frozenset(i for i in range(n) if bits & (1 << i))
        if all(
            j in worlds
            for i in worlds
            for j in range(n)
            if (i, j) in order
        ):
            yield worlds


def _all_monotone_valuations(n: int, atoms: list, order: frozenset):
    """Yield all monotone valuations: for each atom, an upward-closed set of worlds."""
    if not atoms:
        yield frozenset()
        return
    upsets = list(_upward_closed_sets(n, order))
    for combo in itertools.product(upsets, repeat=len(atoms)):
        yield frozenset(
            (w, atom)
            for atom, worlds_set in zip(atoms, combo)
            for w in worlds_set
        )


# ---------------------------------------------------------------------------
# Bounded countermodel search
# ---------------------------------------------------------------------------

def find_countermodel(
    formula,
    max_worlds: int = 4,
) -> Optional[KripkeCountermodel]:
    """Search for a finite Kripke countermodel with at most max_worlds worlds.

    Enumerates all preorders and monotone valuations up to max_worlds worlds,
    returning the first (smallest) model where some world fails to force formula.

    Returns None if no countermodel is found within the bound.

    IMPORTANT: None does NOT imply intuitionistic validity.  This is a bounded
    search, not a completeness proof.  Increase max_worlds if needed.
    """
    atom_list = sorted(_atoms(formula))
    for n in range(1, max_worlds + 1):
        worlds = tuple(range(n))
        for order in _all_preorders(n):
            for valuation in _all_monotone_valuations(n, atom_list, order):
                model = KripkeModel(worlds=worlds, order=order, valuation=valuation)
                for w in worlds:
                    if not forces(model, w, formula):
                        return KripkeCountermodel(
                            model=model, world=w, formula=formula
                        )
    return None


# ---------------------------------------------------------------------------
# Structured explanation (for CLI, web API, and diagnostics)
# ---------------------------------------------------------------------------

@dataclass
class KripkeExplanation:
    """Structured result of a Kripke countermodel search.

    status values:
      "countermodel_found"          — a finite countermodel was found
      "no_countermodel_within_bound" — search exhausted the bound; not a validity proof
      "parse_error"                 — the formula could not be parsed
      "unsupported_formula"         — formula contains non-propositional constructs
    """
    formula: str            # pretty-printed formula
    status: str
    max_worlds: int
    bound_note: str         # one-line caveat about the result
    worlds: Optional[list]          # world ids, or None
    order_pairs: Optional[list]     # [[w, v], …] non-reflexive pairs, or None
    valuation: Optional[dict]       # {world_id: [atom, …]}, or None
    failing_world: Optional[object] # world where formula fails, or None
    explanation: str                # human-readable sentence


def kripke_explain(
    formula_or_str,
    max_worlds: int = 4,
    *,
    formula_str: str = "",
) -> KripkeExplanation:
    """Run bounded Kripke countermodel search and return a structured explanation.

    formula_or_str may be a Formula object or a formula string.
    formula_str overrides the display string (optional).
    """
    from .ast import pretty as pretty_formula
    from .parser import parse_formula
    from .errors import ParseError

    # Resolve formula
    if isinstance(formula_or_str, str):
        raw = formula_or_str
        try:
            formula = parse_formula(raw)
        except ParseError as e:
            return KripkeExplanation(
                formula=raw, status="parse_error", max_worlds=max_worlds,
                bound_note="Formula could not be parsed.",
                worlds=None, order_pairs=None, valuation=None, failing_world=None,
                explanation=f"Parse error: {e}",
            )
    else:
        formula = formula_or_str
        raw = formula_str or pretty_formula(formula)

    display = formula_str or pretty_formula(formula)

    # Reject non-propositional formulas
    try:
        _ = _atoms(formula)
    except Exception:
        return KripkeExplanation(
            formula=display, status="unsupported_formula", max_worlds=max_worlds,
            bound_note="Kripke semantics covers propositional logic only.",
            worlds=None, order_pairs=None, valuation=None, failing_world=None,
            explanation="Formula contains non-propositional constructs (FOL/quantifiers); Kripke semantics not applicable.",
        )

    cm = find_countermodel(formula, max_worlds=max_worlds)

    if cm is None:
        return KripkeExplanation(
            formula=display,
            status="no_countermodel_within_bound",
            max_worlds=max_worlds,
            bound_note=(
                f"No countermodel found up to {max_worlds} worlds. "
                "This is NOT a proof of intuitionistic validity — "
                "bounded search, not completeness."
            ),
            worlds=None, order_pairs=None, valuation=None, failing_world=None,
            explanation=(
                f"No finite Kripke countermodel found within {max_worlds} worlds. "
                "The formula may be intuitionistically valid, or a larger model may be needed."
            ),
        )

    m = cm.model
    w0 = cm.world
    order_pairs = sorted((a, b) for (a, b) in m.order if a != b)
    val_dict = {
        wid: sorted(atom for (u, atom) in m.valuation if u == wid)
        for wid in m.worlds
    }
    return KripkeExplanation(
        formula=display,
        status="countermodel_found",
        max_worlds=max_worlds,
        bound_note="Bounded finite Kripke countermodel found.",
        worlds=list(m.worlds),
        order_pairs=[[a, b] for a, b in order_pairs],
        valuation=val_dict,
        failing_world=w0,
        explanation=(
            f"At world {w0}, '{display}' is not forced. "
            f"This is a finite Kripke countermodel showing the formula is not "
            f"intuitionistically valid in this model."
        ),
    )


def explanation_to_dict(ex: KripkeExplanation) -> dict:
    """Serialise a KripkeExplanation to a JSON-compatible dict."""
    return {
        "formula":       ex.formula,
        "status":        ex.status,
        "max_worlds":    ex.max_worlds,
        "bound_note":    ex.bound_note,
        "worlds":        ex.worlds,
        "order_pairs":   ex.order_pairs,
        "valuation":     {str(k): v for k, v in (ex.valuation or {}).items()},
        "failing_world": ex.failing_world,
        "explanation":   ex.explanation,
    }


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------

def pretty_model(model: KripkeModel) -> str:
    """Human-readable multi-line description of a KripkeModel."""
    parts = [f"worlds: {list(model.worlds)}"]
    strict_pairs = sorted(
        (w, v) for (w, v) in model.order if w != v
    )
    if strict_pairs:
        pairs_str = ", ".join(f"{w}<={v}" for w, v in strict_pairs)
        parts.append(f"order:  reflexive + {{{pairs_str}}}")
    else:
        parts.append("order:  discrete (reflexive only, every world isolated)")
    for w in model.worlds:
        atoms = sorted(a for (u, a) in model.valuation if u == w)
        parts.append(f"  world {w}: {{{', '.join(atoms)}}}")
    return "\n".join(parts)
