"""Lightweight sort/type foundation for Stele.

v1 scope: all current expressions have sort FORMULA. TERM is a placeholder
for future algebraic/arithmetic extensions. TypeMismatch diagnostics are wired
in the infrastructure but have no surface trigger in v1 because the grammar
does not yet have a term language.

Public API:
  Sort           — enum of logical sorts
  infer_sort(e)  — returns Sort.FORMULA for all current expressions
  expand_defs(formula, defs_dict) — formula macro expansion
"""
from enum import Enum
from .ast import Var, Op


class Sort(Enum):
    """Logical sort/kind of a Stele expression.

    FORMULA: a logical proposition (the only sort in current Stele syntax).
    TERM:    placeholder for future algebraic or arithmetic terms.
             Not inhabited by any syntax in v1.
    """
    FORMULA = "formula"
    TERM = "term"       # future: arithmetic/algebraic terms


def infer_sort(expr):
    """Return the sort of a Stele expression.

    In v1, all parsed expressions are propositional formulas, so the result is
    always Sort.FORMULA. TypeMismatch at the sort level will become meaningful
    when TERM expressions are added in a future phase.
    """
    return Sort.FORMULA


def expand_defs(formula, defs_dict, _seen=None):
    """Recursively substitute Var nodes whose name matches a definition.

    Cycle-safe: if expansion would revisit a name already being expanded,
    it leaves the Var unchanged (stops at the cycle).

    Args:
        formula:   a parsed formula (Var | Op)
        defs_dict: dict mapping name -> Definition
        _seen:     internal cycle-protection set (leave None on first call)

    Returns:
        A new formula with definition Vars replaced by their bodies.
        Returns the original object unchanged when there is nothing to expand.
    """
    if _seen is None:
        _seen = frozenset()
    if isinstance(formula, Var):
        if formula.name in defs_dict and formula.name not in _seen:
            return expand_defs(
                defs_dict[formula.name].formula,
                defs_dict,
                _seen | {formula.name},
            )
        return formula
    if isinstance(formula, Op):
        new_args = tuple(expand_defs(a, defs_dict, _seen) for a in formula.args)
        if new_args == formula.args:
            return formula
        return Op(formula.sym, new_args)
    return formula


def check_sort_compat(formula, expected_sort):
    """Check that formula has the expected sort. Raises ValueError on mismatch.

    In v1 this always succeeds (all expressions are FORMULA).
    Future: will raise when a TERM appears in a FORMULA position or vice versa.
    """
    actual = infer_sort(formula)
    if actual != expected_sort:
        from .ast import pretty
        raise ValueError(
            f"sort mismatch: expected {expected_sort.value}, "
            f"got {actual.value} for {pretty(formula)}"
        )
