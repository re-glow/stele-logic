"""Proof-term reduction for the intuitionistic propositional calculus.

Public API
----------
free_vars(term) -> set[str]
    Collect the set of free variable names in term.

substitute(term, var, replacement) -> Term
    Capture-avoiding substitution: term[replacement/var].
    Alpha-renames binders whose bound name would be captured.

step(term) -> Term | None
    Perform one leftmost-outermost beta-reduction step.
    Returns None if term is already in normal form.

normalize(term, fuel=1000) -> Term
    Repeatedly apply step until normal form or fuel exhausted.
    Raises ReductionError if fuel is exhausted.

is_normal(term) -> bool
    True iff no beta-redex is present anywhere in term.

ReductionError
    Exception raised when normalization exceeds the fuel bound.

Reduction rules
---------------
  App(Lam(x, A, body), arg)          =>  body[arg/x]        (beta_imp)
  Fst(Pair(a, b))                    =>  a                  (beta_fst)
  Snd(Pair(a, b))                    =>  b                  (beta_snd)
  Case(Inl(a, _), x, lb, y, rb)     =>  lb[a/x]            (beta_case_l)
  Case(Inr(b, _), x, lb, y, rb)     =>  rb[b/y]            (beta_case_r)

No eta-reduction in v1.

Reduction strategy
------------------
Leftmost-outermost (normal order).  At each composite node the outermost
redex is tried first.  If no head redex exists, subterms are reduced
left-to-right recursively.  This strategy is deterministic and, for the
simply-typed fragment, reaches the unique beta-normal form.

Relation to metatheory
----------------------
These reductions correspond to cut elimination in sequent calculus (each
beta rule eliminates an introduction followed immediately by the matching
elimination).  Subject reduction (type preservation under ->beta) is an
intended metatheoretic invariant, checked by regression tests.

The tests in test_reduction.py are regression checks, not machine-checked
proofs of strong normalization, confluence, or consistency.  The simply-
typed intuitionistic fragment normalises by standard metatheory; the fuel
bound is a defensive guard against implementation bugs.
"""
from .terms import TVar, Lam, App, Pair, Fst, Snd, Inl, Inr, Case, Abort


# ---------------------------------------------------------------------------
# ReductionError
# ---------------------------------------------------------------------------

class ReductionError(Exception):
    """Raised when normalization exceeds the fuel bound."""


# ---------------------------------------------------------------------------
# Free variables
# ---------------------------------------------------------------------------

def free_vars(term) -> set:
    """Return the set of free variable names in term."""
    if isinstance(term, TVar):
        return {term.name}
    if isinstance(term, Lam):
        return free_vars(term.body) - {term.var}
    if isinstance(term, App):
        return free_vars(term.fn) | free_vars(term.arg)
    if isinstance(term, Pair):
        return free_vars(term.left) | free_vars(term.right)
    if isinstance(term, Fst):
        return free_vars(term.pair)
    if isinstance(term, Snd):
        return free_vars(term.pair)
    if isinstance(term, Inl):
        return free_vars(term.value)
    if isinstance(term, Inr):
        return free_vars(term.value)
    if isinstance(term, Case):
        return (free_vars(term.scrutinee) |
                (free_vars(term.left_body)  - {term.left_var}) |
                (free_vars(term.right_body) - {term.right_var}))
    if isinstance(term, Abort):
        return free_vars(term.false_term)
    return set()


# ---------------------------------------------------------------------------
# Capture-avoiding substitution
# ---------------------------------------------------------------------------

def _fresh(name, avoid):
    """Return a name like `name` that is not in the set `avoid`."""
    if name not in avoid:
        return name
    i = 0
    while True:
        candidate = f"{name}_{i}"
        if candidate not in avoid:
            return candidate
        i += 1


def substitute(term, var, replacement):
    """Capture-avoiding substitution: term[replacement/var].

    Shadowing: if a binder in term re-binds var, the binder and its body
    are left unchanged (var is no longer free there).

    Capture avoidance: if a binder in term would capture a free variable
    of replacement, the binder is alpha-renamed to a fresh name before
    descending.

    The fresh-name generator produces names of the form NAME_0, NAME_1,
    ... deterministically.
    """
    if isinstance(term, TVar):
        return replacement if term.name == var else term

    if isinstance(term, Lam):
        if term.var == var:
            # var is re-bound here; no substitution in body
            return term
        if term.var in free_vars(replacement):
            # Alpha-rename to avoid capture
            avoid = free_vars(replacement) | free_vars(term.body) | {var}
            new_var = _fresh(term.var, avoid)
            renamed_body = substitute(term.body, term.var, TVar(new_var))
            return Lam(new_var, term.var_type,
                       substitute(renamed_body, var, replacement))
        return Lam(term.var, term.var_type,
                   substitute(term.body, var, replacement))

    if isinstance(term, App):
        return App(substitute(term.fn,  var, replacement),
                   substitute(term.arg, var, replacement))

    if isinstance(term, Pair):
        return Pair(substitute(term.left,  var, replacement),
                    substitute(term.right, var, replacement))

    if isinstance(term, Fst):
        return Fst(substitute(term.pair, var, replacement))

    if isinstance(term, Snd):
        return Snd(substitute(term.pair, var, replacement))

    if isinstance(term, Inl):
        return Inl(substitute(term.value, var, replacement), term.right_type)

    if isinstance(term, Inr):
        return Inr(substitute(term.value, var, replacement), term.left_type)

    if isinstance(term, Case):
        scrut = substitute(term.scrutinee, var, replacement)

        # ── Left branch ──────────────────────────────────────────────────
        if term.left_var == var:
            left_var  = term.left_var
            left_body = term.left_body          # shadowed; no subst
        elif term.left_var in free_vars(replacement):
            avoid = free_vars(replacement) | free_vars(term.left_body) | {var}
            nlv = _fresh(term.left_var, avoid)
            rlb = substitute(term.left_body, term.left_var, TVar(nlv))
            left_var  = nlv
            left_body = substitute(rlb, var, replacement)
        else:
            left_var  = term.left_var
            left_body = substitute(term.left_body, var, replacement)

        # ── Right branch ─────────────────────────────────────────────────
        if term.right_var == var:
            right_var  = term.right_var
            right_body = term.right_body        # shadowed; no subst
        elif term.right_var in free_vars(replacement):
            avoid = free_vars(replacement) | free_vars(term.right_body) | {var}
            nrv = _fresh(term.right_var, avoid)
            rrb = substitute(term.right_body, term.right_var, TVar(nrv))
            right_var  = nrv
            right_body = substitute(rrb, var, replacement)
        else:
            right_var  = term.right_var
            right_body = substitute(term.right_body, var, replacement)

        return Case(scrut, left_var, left_body, right_var, right_body)

    if isinstance(term, Abort):
        return Abort(substitute(term.false_term, var, replacement),
                     term.target_type)

    return term   # unknown constructor — return unchanged


# ---------------------------------------------------------------------------
# One-step reduction (leftmost-outermost)
# ---------------------------------------------------------------------------

def step(term):
    """Perform one leftmost-outermost beta-reduction step.

    Returns the reduced term, or None if term is already in normal form.

    Reduction rules tried in order:
      1. App(Lam(x, A, body), arg)          beta_imp
      2. Fst(Pair(a, b))                    beta_fst
      3. Snd(Pair(a, b))                    beta_snd
      4. Case(Inl(a, _), x, lb, y, rb)     beta_case_l
      5. Case(Inr(b, _), x, lb, y, rb)     beta_case_r

    Subterms are reduced left-to-right when the head is not a redex.
    """
    # ── TVar: already normal ─────────────────────────────────────────────
    if isinstance(term, TVar):
        return None

    # ── App ──────────────────────────────────────────────────────────────
    if isinstance(term, App):
        if isinstance(term.fn, Lam):               # beta_imp
            return substitute(term.fn.body, term.fn.var, term.arg)
        r = step(term.fn)
        if r is not None:
            return App(r, term.arg)
        r = step(term.arg)
        if r is not None:
            return App(term.fn, r)
        return None

    # ── Fst ──────────────────────────────────────────────────────────────
    if isinstance(term, Fst):
        if isinstance(term.pair, Pair):            # beta_fst
            return term.pair.left
        r = step(term.pair)
        return Fst(r) if r is not None else None

    # ── Snd ──────────────────────────────────────────────────────────────
    if isinstance(term, Snd):
        if isinstance(term.pair, Pair):            # beta_snd
            return term.pair.right
        r = step(term.pair)
        return Snd(r) if r is not None else None

    # ── Case ─────────────────────────────────────────────────────────────
    if isinstance(term, Case):
        if isinstance(term.scrutinee, Inl):        # beta_case_l
            return substitute(term.left_body, term.left_var,
                               term.scrutinee.value)
        if isinstance(term.scrutinee, Inr):        # beta_case_r
            return substitute(term.right_body, term.right_var,
                               term.scrutinee.value)
        r = step(term.scrutinee)
        if r is not None:
            return Case(r, term.left_var, term.left_body,
                        term.right_var, term.right_body)
        r = step(term.left_body)
        if r is not None:
            return Case(term.scrutinee, term.left_var, r,
                        term.right_var, term.right_body)
        r = step(term.right_body)
        if r is not None:
            return Case(term.scrutinee, term.left_var, term.left_body,
                        term.right_var, r)
        return None

    # ── Lam: reduce under the binder ─────────────────────────────────────
    if isinstance(term, Lam):
        r = step(term.body)
        return Lam(term.var, term.var_type, r) if r is not None else None

    # ── Pair ─────────────────────────────────────────────────────────────
    if isinstance(term, Pair):
        r = step(term.left)
        if r is not None:
            return Pair(r, term.right)
        r = step(term.right)
        return Pair(term.left, r) if r is not None else None

    # ── Inl ──────────────────────────────────────────────────────────────
    if isinstance(term, Inl):
        r = step(term.value)
        return Inl(r, term.right_type) if r is not None else None

    # ── Inr ──────────────────────────────────────────────────────────────
    if isinstance(term, Inr):
        r = step(term.value)
        return Inr(r, term.left_type) if r is not None else None

    # ── Abort ────────────────────────────────────────────────────────────
    if isinstance(term, Abort):
        r = step(term.false_term)
        return Abort(r, term.target_type) if r is not None else None

    return None


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize(term, fuel=1000):
    """Repeatedly apply step until normal form or fuel is exhausted.

    Parameters
    ----------
    term : Term
        The proof term to normalise.
    fuel : int
        Maximum number of reduction steps.  The simply-typed fragment
        terminates for all well-typed terms, but the fuel bound guards
        against bugs.  Raise fuel for unusually large terms if needed.

    Returns
    -------
    Term
        The beta-normal form of term.

    Raises
    ------
    ReductionError
        If more than `fuel` steps are needed.
    """
    for _ in range(fuel):
        r = step(term)
        if r is None:
            return term
        term = r
    raise ReductionError(
        f"normalisation exceeded {fuel} steps; "
        "raise `fuel` or check for bugs in the term"
    )


def is_normal(term) -> bool:
    """Return True iff term contains no beta-redex."""
    return step(term) is None
