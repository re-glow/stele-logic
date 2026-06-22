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
from .terms import (TVar, Lam, App, Pair, Fst, Snd, Inl, Inr, Case, Abort,
                    ForallIntro, ForallElim, ExistsIntro, ExistsElim)
from .fol import (ObjVar, obj_term_vars, fol_free_obj_vars,
                  subst_obj, subst_obj_in_obj_term, _fresh_obj)


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
    if isinstance(term, ForallIntro):
        return free_vars(term.body)
    if isinstance(term, ForallElim):
        return free_vars(term.fn)  # obj_term has no proof variables
    if isinstance(term, ExistsIntro):
        return free_vars(term.proof)
    if isinstance(term, ExistsElim):
        return free_vars(term.scrutinee) | (free_vars(term.body) - {term.proof_var})
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

    # ── FOL proof-term constructors (proof-variable substitution only) ────
    if isinstance(term, ForallIntro):
        return ForallIntro(term.obj_var, substitute(term.body, var, replacement))

    if isinstance(term, ForallElim):
        return ForallElim(substitute(term.fn, var, replacement), term.obj_term)

    if isinstance(term, ExistsIntro):
        return ExistsIntro(term.witness,
                           substitute(term.proof, var, replacement),
                           term.exists_type)

    if isinstance(term, ExistsElim):
        new_s = substitute(term.scrutinee, var, replacement)
        if term.proof_var == var:
            return ExistsElim(new_s, term.obj_var, term.proof_var, term.body)
        if term.proof_var in free_vars(replacement):
            avoid = free_vars(replacement) | free_vars(term.body) | {var}
            new_pv = _fresh(term.proof_var, avoid)
            renamed = substitute(term.body, term.proof_var, TVar(new_pv))
            return ExistsElim(new_s, term.obj_var, new_pv,
                              substitute(renamed, var, replacement))
        return ExistsElim(new_s, term.obj_var, term.proof_var,
                          substitute(term.body, var, replacement))

    return term   # unknown constructor — return unchanged


# ---------------------------------------------------------------------------
# Object-variable substitution in proof terms
# ---------------------------------------------------------------------------

def obj_free_in_term(term) -> set:
    """Return free object variable names appearing in formula annotations of term."""
    if isinstance(term, TVar):
        return set()
    if isinstance(term, Lam):
        return fol_free_obj_vars(term.var_type) | obj_free_in_term(term.body)
    if isinstance(term, App):
        return obj_free_in_term(term.fn) | obj_free_in_term(term.arg)
    if isinstance(term, Pair):
        return obj_free_in_term(term.left) | obj_free_in_term(term.right)
    if isinstance(term, Fst):
        return obj_free_in_term(term.pair)
    if isinstance(term, Snd):
        return obj_free_in_term(term.pair)
    if isinstance(term, Inl):
        return obj_free_in_term(term.value) | fol_free_obj_vars(term.right_type)
    if isinstance(term, Inr):
        return obj_free_in_term(term.value) | fol_free_obj_vars(term.left_type)
    if isinstance(term, Case):
        return (obj_free_in_term(term.scrutinee) |
                obj_free_in_term(term.left_body) |
                obj_free_in_term(term.right_body))
    if isinstance(term, Abort):
        return obj_free_in_term(term.false_term) | fol_free_obj_vars(term.target_type)
    if isinstance(term, ForallIntro):
        return obj_free_in_term(term.body) - {term.obj_var}
    if isinstance(term, ForallElim):
        return obj_free_in_term(term.fn) | obj_term_vars(term.obj_term)
    if isinstance(term, ExistsIntro):
        return (obj_term_vars(term.witness) |
                obj_free_in_term(term.proof) |
                fol_free_obj_vars(term.exists_type))
    if isinstance(term, ExistsElim):
        return (obj_free_in_term(term.scrutinee) |
                (obj_free_in_term(term.body) - {term.obj_var}))
    return set()


def subst_obj_in_term(term, var_name, replacement):
    """Substitute an object term for an object variable in formula annotations.

    Traverses the proof term and applies subst_obj to every formula annotation
    (var_type, right_type, left_type, target_type, exists_type) and to
    object-term fields (obj_term in ForallElim, witness in ExistsIntro).

    Object-variable binders ForallIntro and ExistsElim create scope: if they
    bind var_name, substitution stops for that scope.  Capture avoidance uses
    _fresh_obj to rename the binder when its name appears free in replacement.

    Proof-variable binders (Lam, Case) do NOT create scope for object variables.
    """
    if isinstance(term, TVar):
        return term

    if isinstance(term, Lam):
        return Lam(term.var,
                   subst_obj(term.var_type, var_name, replacement),
                   subst_obj_in_term(term.body, var_name, replacement))

    if isinstance(term, App):
        return App(subst_obj_in_term(term.fn,  var_name, replacement),
                   subst_obj_in_term(term.arg, var_name, replacement))

    if isinstance(term, Pair):
        return Pair(subst_obj_in_term(term.left,  var_name, replacement),
                    subst_obj_in_term(term.right, var_name, replacement))

    if isinstance(term, Fst):
        return Fst(subst_obj_in_term(term.pair, var_name, replacement))

    if isinstance(term, Snd):
        return Snd(subst_obj_in_term(term.pair, var_name, replacement))

    if isinstance(term, Inl):
        return Inl(subst_obj_in_term(term.value, var_name, replacement),
                   subst_obj(term.right_type, var_name, replacement))

    if isinstance(term, Inr):
        return Inr(subst_obj_in_term(term.value, var_name, replacement),
                   subst_obj(term.left_type, var_name, replacement))

    if isinstance(term, Case):
        return Case(subst_obj_in_term(term.scrutinee,   var_name, replacement),
                    term.left_var,
                    subst_obj_in_term(term.left_body,  var_name, replacement),
                    term.right_var,
                    subst_obj_in_term(term.right_body, var_name, replacement))

    if isinstance(term, Abort):
        return Abort(subst_obj_in_term(term.false_term, var_name, replacement),
                     subst_obj(term.target_type, var_name, replacement))

    if isinstance(term, ForallIntro):
        if term.obj_var == var_name:
            return term  # shadowed
        repl_vars = obj_term_vars(replacement)
        if term.obj_var in repl_vars:
            avoid = repl_vars | obj_free_in_term(term.body) | {var_name}
            new_var = _fresh_obj(term.obj_var, avoid)
            renamed = subst_obj_in_term(term.body, term.obj_var, ObjVar(new_var))
            return ForallIntro(new_var,
                               subst_obj_in_term(renamed, var_name, replacement))
        return ForallIntro(term.obj_var,
                           subst_obj_in_term(term.body, var_name, replacement))

    if isinstance(term, ForallElim):
        return ForallElim(
            subst_obj_in_term(term.fn, var_name, replacement),
            subst_obj_in_obj_term(term.obj_term, var_name, replacement))

    if isinstance(term, ExistsIntro):
        return ExistsIntro(
            subst_obj_in_obj_term(term.witness, var_name, replacement),
            subst_obj_in_term(term.proof, var_name, replacement),
            subst_obj(term.exists_type, var_name, replacement))

    if isinstance(term, ExistsElim):
        new_s = subst_obj_in_term(term.scrutinee, var_name, replacement)
        if term.obj_var == var_name:
            return ExistsElim(new_s, term.obj_var, term.proof_var, term.body)
        repl_vars = obj_term_vars(replacement)
        if term.obj_var in repl_vars:
            avoid = repl_vars | obj_free_in_term(term.body) | {var_name}
            new_var = _fresh_obj(term.obj_var, avoid)
            renamed = subst_obj_in_term(term.body, term.obj_var, ObjVar(new_var))
            return ExistsElim(new_s, new_var, term.proof_var,
                              subst_obj_in_term(renamed, var_name, replacement))
        return ExistsElim(new_s, term.obj_var, term.proof_var,
                          subst_obj_in_term(term.body, var_name, replacement))

    return term  # unknown constructor


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

    # ── ForallElim  (beta_forall) ─────────────────────────────────────────
    if isinstance(term, ForallElim):
        if isinstance(term.fn, ForallIntro):      # beta_forall
            return subst_obj_in_term(term.fn.body, term.fn.obj_var, term.obj_term)
        r = step(term.fn)
        return ForallElim(r, term.obj_term) if r is not None else None

    # ── ForallIntro: reduce under binder ────────────────────────────────
    if isinstance(term, ForallIntro):
        r = step(term.body)
        return ForallIntro(term.obj_var, r) if r is not None else None

    # ── ExistsElim  (beta_exists) ────────────────────────────────────────
    if isinstance(term, ExistsElim):
        if isinstance(term.scrutinee, ExistsIntro):   # beta_exists
            ei = term.scrutinee
            body1 = substitute(term.body, term.proof_var, ei.proof)
            return subst_obj_in_term(body1, term.obj_var, ei.witness)
        r = step(term.scrutinee)
        if r is not None:
            return ExistsElim(r, term.obj_var, term.proof_var, term.body)
        r = step(term.body)
        if r is not None:
            return ExistsElim(term.scrutinee, term.obj_var, term.proof_var, r)
        return None

    # ── ExistsIntro: reduce under proof ──────────────────────────────────
    if isinstance(term, ExistsIntro):
        r = step(term.proof)
        return ExistsIntro(term.witness, r, term.exists_type) if r is not None else None

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
