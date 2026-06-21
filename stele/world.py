"""Semantic worlds: (matrix, axioms) pairs for computing formula status.

A World pairs a named matrix with a set of axioms (designated premises).
`status(φ, world)` determines whether φ is semantically entailed, refuted,
both (paraconsistent), or neither under those constraints.

This is purely semantic evaluation — no proof search, no kernel involvement.
The trusted proof kernel (`kernel.py`) is never called from this module.
"""
from dataclasses import dataclass
from .ast import Op
from .matrix import MATRICES, entails

# ---------------------------------------------------------------------------
# Semantic status labels
# ---------------------------------------------------------------------------

PROVABLE = "PROVABLE"         # axioms |= φ        and  axioms ⊭ ¬φ
REFUTABLE = "REFUTABLE"       # axioms ⊭ φ         and  axioms |= ¬φ
BOTH = "BOTH"                 # axioms |= φ  AND  axioms |= ¬φ  (paraconsistent)
INDEPENDENT = "INDEPENDENT"   # axioms ⊭ φ  AND  axioms ⊭ ¬φ


# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class World:
    """A semantic world: a many-valued matrix paired with a set of axioms.

    matrix_name: key into stele.matrix.MATRICES (e.g. 'K3', 'LP', 'boolean').
    axioms: tuple of Formula objects acting as designated premises.
    """
    matrix_name: str
    axioms: tuple = ()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def status(formula, world):
    """Return the semantic status of formula in the given world.

    Uses the matrix entailment relation (stele/matrix.py) — designation
    preservation over all valuations consistent with the world's axioms.

    Returns one of PROVABLE, REFUTABLE, BOTH, INDEPENDENT.

    Important: PROVABLE means *semantically entailed by the world's axioms
    under the selected matrix*, not found by proof search or kernel checking.
    BOTH is possible in paraconsistent matrices such as LP, where axioms can
    entail both φ and ¬φ simultaneously without exploding.
    """
    if world.matrix_name not in MATRICES:
        from .errors import SteleError
        raise SteleError(
            f"unknown matrix '{world.matrix_name}'. "
            f"available: {', '.join(sorted(MATRICES))}")

    m = MATRICES[world.matrix_name]
    prems = list(world.axioms)
    neg = Op("not", (formula,))

    phi_holds, _ = entails(prems, formula, m)
    neg_holds, _ = entails(prems, neg, m)

    if phi_holds and neg_holds:
        return BOTH
    if phi_holds:
        return PROVABLE
    if neg_holds:
        return REFUTABLE
    return INDEPENDENT
