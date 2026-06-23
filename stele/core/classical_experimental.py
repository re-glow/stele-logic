"""Experimental classical proof-term bridge via negative translation.

STATUS: EXPERIMENTAL — not part of the stable public API.

This module implements Gödel–Gentzen-style negative translation from
classical propositional formulas into intuitionistic formulas, then
delegates proof-term checking to the existing intuitionistic typechecker.

The intuitionistic proof-term core (stele.core.typing) is unchanged.
No classical constructors are added. No control operators (μ, callcc,
throw) are implemented.

Approach:
  Classical formula φ is translated to φ^N such that:
    CPC ⊢ φ   implies   IPC ⊢ φ^N

  This allows hand-written intuitionistic proof terms to be checked
  against translated classical formulas.

Gödel–Gentzen translation (propositional):
  P^N         = ¬¬P         (atoms)
  false^N     = false        (bottom is self-dual)
  (A ∧ B)^N   = A^N ∧ B^N   (conjunction is structural)
  (A → B)^N   = A^N → B^N   (implication is structural)
  (¬A)^N      = ¬(A^N)      (negation translates body)
  (A ∨ B)^N   = ¬(¬A^N ∧ ¬B^N)  (disjunction via De Morgan)

Limitations:
  - Propositional formulas only (no quantifiers in Prompt 35)
  - No automatic proof-term synthesis; terms must be hand-written
  - No λμ-calculus, no continuation typing, no classical normalization
  - Does not modify kernel.py or existing typing behavior
"""
from stele.ast import Var, Op


# ---------------------------------------------------------------------------
# Formula constructors (internal helpers)
# ---------------------------------------------------------------------------

_BOT = Op("bot", ())


def _mk_not(f):
    """Build ¬A as A → ⊥."""
    return Op("imp", (f, _BOT))


def _mk_double_neg(f):
    """Build ¬¬A as (A → ⊥) → ⊥."""
    return _mk_not(_mk_not(f))


# ---------------------------------------------------------------------------
# Negative translation
# ---------------------------------------------------------------------------

def negative_translate_formula(formula, *, mode="godel_gentzen"):
    """Translate a classical propositional formula to its intuitionistic image.

    Parameters
    ----------
    formula : Var | Op
        A propositional formula built from Var, Op("and", ...), Op("or", ...),
        Op("imp", ...), Op("not", ...), Op("bot", ()).
    mode : str
        "godel_gentzen" — standard Gödel–Gentzen translation (default).
        "glivenko" — wraps the entire translated formula in ¬¬.

    Returns
    -------
    Translated formula (Var | Op).

    Raises
    ------
    ValueError
        If the formula contains unsupported constructs (e.g., quantifiers).
    """
    if mode not in ("godel_gentzen", "glivenko"):
        raise ValueError(f"unknown translation mode: {mode!r}")

    result = _translate_gg(formula)

    if mode == "glivenko":
        result = _mk_double_neg(result)

    return result


def _translate_gg(f):
    """Core Gödel–Gentzen recursive translation."""
    if isinstance(f, Var):
        return _mk_double_neg(f)

    if not isinstance(f, Op):
        raise ValueError(
            f"negative_translate_formula: unsupported formula node "
            f"{type(f).__name__}; propositional formulas only"
        )

    sym = f.sym

    if sym == "bot":
        return _BOT

    if sym == "not":
        # ¬A → ¬(A^N)
        return _mk_not(_translate_gg(f.args[0]))

    if sym == "and":
        # (A ∧ B)^N = A^N ∧ B^N
        return Op("and", (_translate_gg(f.args[0]), _translate_gg(f.args[1])))

    if sym == "imp":
        # (A → B)^N = A^N → B^N
        return Op("imp", (_translate_gg(f.args[0]), _translate_gg(f.args[1])))

    if sym == "or":
        # (A ∨ B)^N = ¬(¬A^N ∧ ¬B^N)
        a_n = _translate_gg(f.args[0])
        b_n = _translate_gg(f.args[1])
        return _mk_not(Op("and", (_mk_not(a_n), _mk_not(b_n))))

    raise ValueError(
        f"negative_translate_formula: unsupported connective {sym!r}"
    )


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------

def is_negative_translation_supported(formula) -> bool:
    """True if the formula uses only propositional connectives.

    Returns False for quantifiers (Forall, Exists), predicates, or
    unknown Op symbols.
    """
    from stele.ast import Forall, Exists, Pred
    if isinstance(formula, (Forall, Exists, Pred)):
        return False
    if isinstance(formula, Var):
        return True
    if isinstance(formula, Op):
        if formula.sym not in ("bot", "not", "and", "or", "imp"):
            return False
        return all(is_negative_translation_supported(a) for a in formula.args)
    return False


_CLASSICAL_PRINCIPLES = {
    "lem": "excluded middle (P ∨ ¬P)",
    "dne": "double-negation elimination (¬¬P → P)",
    "peirce": "Peirce's law (((P → Q) → P) → P)",
}


def classical_principle_name(formula) -> str | None:
    """If formula matches a well-known classical principle shape, return its name.

    Currently recognises:
      - LEM: P ∨ ¬P
      - DNE: ¬¬P → P
      - Peirce: ((P → Q) → P) → P

    Returns None for unrecognised formulas.
    """
    from stele.core.typing import normalize_neg

    f = normalize_neg(formula)

    # DNE: (P → ⊥) → ⊥) → P  (i.e. ¬¬P → P after normalisation)
    if isinstance(f, Op) and f.sym == "imp":
        ante, cons = f.args
        if isinstance(ante, Op) and ante.sym == "imp":
            inner_ante, inner_cons = ante.args
            if (isinstance(inner_cons, Op) and inner_cons.sym == "bot"
                    and isinstance(inner_ante, Op) and inner_ante.sym == "imp"):
                bottom_check = inner_ante.args[1]
                if (isinstance(bottom_check, Op) and bottom_check.sym == "bot"
                        and _formula_eq_ignoring_names(inner_ante.args[0], cons)):
                    return "dne"

    # LEM: P ∨ ¬P  (after norm: P ∨ (P → ⊥))
    if isinstance(f, Op) and f.sym == "or":
        left, right = f.args
        right_norm = normalize_neg(right)
        if (isinstance(right_norm, Op) and right_norm.sym == "imp"
                and isinstance(right_norm.args[1], Op)
                and right_norm.args[1].sym == "bot"):
            if _formula_eq_ignoring_names(left, right_norm.args[0]):
                return "lem"

    # Peirce: ((P → Q) → P) → P
    if isinstance(f, Op) and f.sym == "imp":
        ante, cons = f.args
        if isinstance(ante, Op) and ante.sym == "imp":
            inner_ante, inner_cons = ante.args
            if (_formula_eq_ignoring_names(inner_cons, cons)
                    and isinstance(inner_ante, Op) and inner_ante.sym == "imp"):
                if _formula_eq_ignoring_names(inner_ante.args[0], cons):
                    return "peirce"

    return None


def _formula_eq_ignoring_names(a, b) -> bool:
    """Structural equality check for formulas (used for pattern matching)."""
    if type(a) != type(b):
        return False
    if isinstance(a, Var):
        return True  # any variable matches (for shape detection)
    if isinstance(a, Op):
        if a.sym != b.sym or len(a.args) != len(b.args):
            return False
        return all(_formula_eq_ignoring_names(x, y) for x, y in zip(a.args, b.args))
    return a == b


# ---------------------------------------------------------------------------
# Proof-term checking bridge
# ---------------------------------------------------------------------------

def translate_type_for_intuitionistic_check(formula, *, mode="godel_gentzen"):
    """Translate a classical formula for use as an intuitionistic type.

    This is a convenience alias for negative_translate_formula, making the
    intent explicit: the returned formula is suitable as a type annotation
    for the intuitionistic proof-term checker.
    """
    return negative_translate_formula(formula, mode=mode)


def check_negative_translation(term, classical_formula, ctx=None, *, mode="godel_gentzen"):
    """Check a hand-written proof term against a negatively-translated classical formula.

    Parameters
    ----------
    term : proof term (TVar, Lam, App, etc.)
        An explicitly constructed intuitionistic proof term.
    classical_formula : Var | Op
        The classical formula to translate.
    ctx : dict or None
        Typing context (defaults to empty).
    mode : str
        Translation mode ("godel_gentzen" or "glivenko").

    Returns
    -------
    translated_formula : the intuitionistic formula that was checked against.

    Raises
    ------
    ValueError
        If the formula is not propositional.
    stele.core.typing.TypingError
        If the proof term does not type-check against the translated formula.
    """
    from stele.core.typing import check, empty_ctx

    if not is_negative_translation_supported(classical_formula):
        raise ValueError(
            "check_negative_translation: formula contains non-propositional "
            "constructs; only propositional formulas are supported"
        )

    translated = negative_translate_formula(classical_formula, mode=mode)

    if ctx is None:
        ctx = empty_ctx()

    check(ctx, term, translated)
    return translated
