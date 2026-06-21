"""Lean 4 exporter for the Stele propositional fragment.

Converts Stele formula AST nodes (Var, Op) to Lean 4 proposition syntax
and generates theorem skeletons with 'sorry' proof placeholders.

Supported operators:
  imp  → →  (implication)
  and  → ∧  (conjunction)
  or   → ∨  (disjunction)
  not  → ¬  (negation)
  bot  → False

The skeleton uses 'sorry' so Lean elaborates the TYPE only.
Lean will emit a warning for 'sorry'; this is expected and intentional.
Full proof-body translation is future work.
"""
from __future__ import annotations
import re
import sys
import pathlib

_HERE = pathlib.Path(__file__).parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from stele.ast import Var, Op   # noqa: E402
from stele.proof import Assume, Conclude, Theorem   # noqa: E402


class ExportError(Exception):
    """Raised when a Stele construct cannot be exported to Lean 4."""


# ---------------------------------------------------------------------------
# Formula → Lean 4 string
# ---------------------------------------------------------------------------

def formula_to_lean(f) -> str:
    """Convert a Stele formula AST node to a Lean 4 proposition string.

    Compound sub-expressions are explicitly parenthesized to avoid any
    precedence ambiguity in the Lean 4 output.

    Examples:
        Var("P")              → "P"
        Op("bot", ())         → "False"
        Op("not", [Var("P")]) → "¬P"
        Op("imp", [P, Q])     → "P → Q"
        Op("and", [P, Q])     → "P ∧ Q"
        Op("or", [P, Q])      → "P ∨ Q"
        Op("imp", [and(P,Q), R]) → "(P ∧ Q) → R"
    """
    if isinstance(f, Var):
        return f.name
    if isinstance(f, Op):
        sym = f.sym
        if sym == "bot":
            return "False"
        if sym == "not":
            return f"¬{_paren(f.args[0])}"
        if sym == "imp":
            # Right-associative: right arg keeps parens only if it is a non-imp compound
            return f"{_paren(f.args[0])} → {_imp_rhs(f.args[1])}"
        if sym == "and":
            return f"{_paren(f.args[0])} ∧ {_paren(f.args[1])}"
        if sym == "or":
            return f"{_paren(f.args[0])} ∨ {_paren(f.args[1])}"
        raise ExportError(
            f"Operator {sym!r} is not in the supported Lean export fragment. "
            "Supported: imp, and, or, not, bot."
        )
    raise ExportError(f"Cannot export formula node of type {type(f).__name__!r}")


def _paren(f) -> str:
    """Return atomic formula as-is; wrap compound formulas in parentheses.

    Lean 4 precedence note: ¬ (not) is a tight prefix operator with higher
    precedence than all binary connectives, so ¬X never needs outer parens
    regardless of context.
    """
    if isinstance(f, Var):
        return f.name
    if isinstance(f, Op) and f.sym in ("bot", "not"):
        return formula_to_lean(f)
    return f"({formula_to_lean(f)})"


def _imp_rhs(f) -> str:
    """Right-hand side of →: skip parens for nested →, ¬, and atoms."""
    if isinstance(f, Var):
        return f.name
    if isinstance(f, Op) and f.sym in ("bot", "imp", "not"):
        return formula_to_lean(f)
    return f"({formula_to_lean(f)})"


# ---------------------------------------------------------------------------
# Free-variable collection
# ---------------------------------------------------------------------------

def collect_free_vars(f) -> list[str]:
    """Return prop variable names from f in order of first appearance."""
    seen: list[str] = []
    _visit_vars(f, seen)
    return seen


def _visit_vars(f, seen: list[str]) -> None:
    if isinstance(f, Var):
        if f.name not in seen:
            seen.append(f.name)
    elif isinstance(f, Op):
        for arg in f.args:
            _visit_vars(arg, seen)


# ---------------------------------------------------------------------------
# Lean name sanitization
# ---------------------------------------------------------------------------

_LEAN_INVALID_CHARS = re.compile(r"[^a-zA-Z0-9_']")


def sanitize_lean_name(name: str) -> str:
    """Convert a Stele theorem/variable name to a valid Lean 4 identifier."""
    result = _LEAN_INVALID_CHARS.sub("_", name)
    if result and result[0].isdigit():
        result = "s_" + result
    return result or "unnamed"


# ---------------------------------------------------------------------------
# Theorem-type extraction
# ---------------------------------------------------------------------------

def extract_theorem_type(thm: Theorem):
    """Build the Lean proposition type for a Stele theorem.

    Collects top-level Assume formulas and the Conclude formula,
    then builds the curried implication:
        assume_1 → assume_2 → ... → conclusion

    Suppose/subproof hypotheses are NOT included (they are discharged
    internally and represented in the concluded formula's type).
    """
    assumes: list = []
    conclusion = None

    for node in thm.lines:
        if isinstance(node, Assume):
            assumes.append(node.formula)
        elif isinstance(node, Conclude):
            conclusion = node.formula

    if conclusion is None:
        raise ExportError("Theorem has no 'conclude' statement — cannot export type.")

    # Build curried type: A1 → (A2 → (... → conclusion))
    result = conclusion
    for assume_f in reversed(assumes):
        result = Op("imp", (assume_f, result))
    return result


# ---------------------------------------------------------------------------
# Skeleton generation
# ---------------------------------------------------------------------------

_SKELETON_TEMPLATE = """\
-- Generated by stele_lean v1
-- Source theorem: {source_name}
-- Logic: {logic}
-- Fragment: propositional logic only (→, ∧, ∨, ¬, False)
--
-- The proof body uses 'sorry' (placeholder).
-- Lean elaborates the TYPE; the sorry produces a warning, not an error.
-- Type errors in the statement reflect genuine elaboration failures.
-- Full proof-body translation is NOT implemented in v1.

{variable_decl}
theorem {lean_name} : {lean_type} := by
  exact sorry
"""


def theorem_to_lean_skeleton(thm: Theorem, logic_name: str | None = None) -> str:
    """Generate a Lean 4 skeleton file for a Stele theorem.

    The skeleton declares prop variables, states the theorem type, and
    uses 'sorry' as a proof placeholder so Lean validates the type only.

    Args:
        thm: parsed Stele Theorem object
        logic_name: logic name string (for documentation in the header)

    Returns:
        Lean 4 file content as a string.

    Raises:
        ExportError: if the theorem uses unsupported constructs.
    """
    theorem_type = extract_theorem_type(thm)
    free_vars = collect_free_vars(theorem_type)
    lean_type_str = formula_to_lean(theorem_type)
    lean_name = sanitize_lean_name(thm.name)

    if free_vars:
        var_list = " ".join(free_vars)
        variable_decl = f"variable ({var_list} : Prop)"
    else:
        variable_decl = "-- (no propositional variables)"

    logic_str = logic_name or thm.logic or "unspecified"

    return _SKELETON_TEMPLATE.format(
        source_name=thm.name,
        logic=logic_str,
        lean_name=lean_name,
        lean_type=lean_type_str,
        variable_decl=variable_decl,
    )
