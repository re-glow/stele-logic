"""De Bruijn / nameless representation for proof-term binders.

This module adds a nameless layer alongside the existing named proof-term
representation (stele.core.terms).  It is used internally for:
  - α-equivalence checking (alpha_equiv)
  - Structurally capture-avoiding substitution (shift / subst)
  - Future support for first-order quantifier binders (Prompt 25B)

The existing named proof-term API (TVar, Lam, App, …) is unchanged.
User-facing syntax, the proof-script kernel, and matrix semantics are
unaffected.

De Bruijn indices
-----------------
Bound proof variables are represented by non-negative integers:
  - Index 0 refers to the innermost enclosing binder.
  - Index 1 refers to the second-innermost binder, and so on.
  - Free named variables are represented by DBFree(name) and carry no
    index.

Example (named → nameless):
  Lam("x", A, TVar("x"))                  →  DBLam(A, DBBound(0))
  Lam("x", A, Lam("y", B, TVar("x")))     →  DBLam(A, DBLam(B, DBBound(1)))
  Lam("x", A, Lam("x", B, TVar("x")))     →  DBLam(A, DBLam(B, DBBound(0)))
                                               (inner x shadows outer x)

α-equivalence
-------------
Two named terms are α-equivalent iff their de Bruijn representations are
equal.  Binder names are erased; only the binding structure matters.

Shift (↑)
---------
shift(t, amount, cutoff) adds `amount` to every free index ≥ cutoff.
"Free" here means: not already bound by an enclosing binder within t.
Cutoff tracks the nesting depth — indices below cutoff are already bound.

Standard use: when a term is moved under k new binders, call
  shift(t, k, 0)
to keep its free-variable references pointing at the same outer bindings.

Substitution
------------
subst(t, k, s) replaces every occurrence of DBBound(k) with s.

The "decrement" convention is used: occurrences of DBBound(j) with j > k
are decremented to DBBound(j-1) because the binder for k is consumed.
When descending under a new binder, k is incremented by 1 and s is shifted
by 1 to maintain correct indices.

β-reduction consequence:
  (DBLam(A, body)) applied to arg  =  subst(body, 0, arg)

subst_top(arg, body) is a thin wrapper for this pattern.

Case binders
------------
Case has TWO independent branch binders — left_var and right_var — each
creating a separate scope. In the nameless representation (DBCase), each
branch body uses index 0 for its own branch variable:
  - left_body sees left_var as DBBound(0)
  - right_body sees right_var as DBBound(0)
The branch variable types are NOT stored in DBCase (they are derivable
from the scrutinee type).

Future first-order binders (Prompt 25B)
----------------------------------------
When forall/exists are added, they will introduce a second kind of binder:
  - Proof binders (this module): bind proof terms under implication/case.
  - Object binders (future): bind first-order term variables under forall/exists.
The de Bruijn index space for object binders will be separate from proof
binders, tracked by a distinct environment in to_debruijn_fol().  No
object-level binders are implemented here.
"""
from dataclasses import dataclass
from .terms import TVar, Lam, App, Pair, Fst, Snd, Inl, Inr, Case, Abort


# ---------------------------------------------------------------------------
# Nameless term constructors
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DBBound:
    """De Bruijn bound variable.  index 0 = innermost binder."""
    index: int


@dataclass(frozen=True)
class DBFree:
    """Free (unbound) proof variable, identified by name."""
    name: str


@dataclass(frozen=True)
class DBLam:
    """Nameless lambda.  The binder name is erased; var_type is retained
    for typing and round-trip purposes."""
    var_type: object   # Formula
    body: object       # DBTerm  (DBBound(0) = the bound variable)


@dataclass(frozen=True)
class DBApp:
    fn: object    # DBTerm
    arg: object   # DBTerm


@dataclass(frozen=True)
class DBPair:
    left: object   # DBTerm
    right: object  # DBTerm


@dataclass(frozen=True)
class DBFst:
    pair: object  # DBTerm


@dataclass(frozen=True)
class DBSnd:
    pair: object  # DBTerm


@dataclass(frozen=True)
class DBInl:
    value: object       # DBTerm
    right_type: object  # Formula annotation


@dataclass(frozen=True)
class DBInr:
    value: object      # DBTerm
    left_type: object  # Formula annotation


@dataclass(frozen=True)
class DBCase:
    """Nameless case analysis.

    Both branch binders are erased.  Each body independently uses
    DBBound(0) for its own branch variable:
      - left_body  : DBTerm (DBBound(0) = left  branch var)
      - right_body : DBTerm (DBBound(0) = right branch var)

    Branch variable types are not stored here because they are derivable
    from the scrutinee's or-type.  See from_debruijn note below.
    """
    scrutinee: object   # DBTerm
    left_body: object   # DBTerm
    right_body: object  # DBTerm


@dataclass(frozen=True)
class DBAbort:
    false_term: object   # DBTerm
    target_type: object  # Formula annotation


# Convenience type union for documentation purposes (not enforced at runtime)
DBTerm = (DBBound, DBFree, DBLam, DBApp, DBPair, DBFst, DBSnd,
          DBInl, DBInr, DBCase, DBAbort)


# ---------------------------------------------------------------------------
# Named → Nameless translation
# ---------------------------------------------------------------------------

def to_debruijn(term, env=None):
    """Translate a named proof term to its de Bruijn representation.

    Parameters
    ----------
    term : Term (from stele.core.terms)
        The named proof term to translate.
    env : list[str] | None
        The current binder environment: env[0] is the name of the
        innermost enclosing binder (index 0), env[1] is next, etc.
        Defaults to the empty environment (no enclosing binders).

    Returns
    -------
    DBTerm
        The nameless representation of term.

    Notes
    -----
    Free variables (names not in env) become DBFree nodes.
    Shadowing is handled by list.index(), which returns the position of
    the first (innermost) occurrence of a name.
    """
    if env is None:
        env = []

    if isinstance(term, TVar):
        try:
            idx = env.index(term.name)
            return DBBound(idx)
        except ValueError:
            return DBFree(term.name)

    if isinstance(term, Lam):
        return DBLam(term.var_type,
                     to_debruijn(term.body, [term.var] + env))

    if isinstance(term, App):
        return DBApp(to_debruijn(term.fn,  env),
                     to_debruijn(term.arg, env))

    if isinstance(term, Pair):
        return DBPair(to_debruijn(term.left,  env),
                      to_debruijn(term.right, env))

    if isinstance(term, Fst):
        return DBFst(to_debruijn(term.pair, env))

    if isinstance(term, Snd):
        return DBSnd(to_debruijn(term.pair, env))

    if isinstance(term, Inl):
        return DBInl(to_debruijn(term.value, env), term.right_type)

    if isinstance(term, Inr):
        return DBInr(to_debruijn(term.value, env), term.left_type)

    if isinstance(term, Case):
        # Each branch body extends the environment independently with its binder
        return DBCase(
            to_debruijn(term.scrutinee, env),
            to_debruijn(term.left_body,  [term.left_var]  + env),
            to_debruijn(term.right_body, [term.right_var] + env),
        )

    if isinstance(term, Abort):
        return DBAbort(to_debruijn(term.false_term, env), term.target_type)

    raise TypeError(f"to_debruijn: unknown term constructor {type(term).__name__!r}")


# ---------------------------------------------------------------------------
# Nameless → Named translation
# ---------------------------------------------------------------------------

def _fresh_name(avoid):
    """Return a short identifier not contained in the set `avoid`."""
    for c in ["x", "y", "z", "w", "u", "v", "p", "q", "r", "s"]:
        if c not in avoid:
            return c
    i = 0
    while True:
        cand = f"v{i}"
        if cand not in avoid:
            return cand
        i += 1


def from_debruijn(db_term, env=None):
    """Translate a de Bruijn term back to a named proof term.

    Parameters
    ----------
    db_term : DBTerm
        The nameless term to translate.
    env : list[str] | None
        The current binder environment: env[0] is the name assigned to
        de Bruijn index 0 (innermost binder).
        Defaults to the empty environment.

    Returns
    -------
    Term (from stele.core.terms)

    Raises
    ------
    NotImplementedError
        For DBCase: branch variable types are not stored in the nameless
        representation, so a fully typed named Case term cannot be
        reconstructed without external type information.
    ValueError
        If a DBBound index is out of range for the current environment.
    TypeError
        If an unknown DBTerm constructor is encountered.

    Notes
    -----
    Fresh binder names are generated by _fresh_name so they do not
    shadow names already in scope.  The generated term is structurally
    equivalent to the original but may use different binder names.
    This function is the partial inverse of to_debruijn; round-trips
    are guaranteed for Lam, App, Pair, Fst, Snd, Inl, Inr, Abort.
    DBCase is NOT supported (see NotImplementedError).
    """
    if env is None:
        env = []

    if isinstance(db_term, DBBound):
        if db_term.index >= len(env):
            raise ValueError(
                f"DBBound({db_term.index}) out of scope "
                f"(env depth is {len(env)})"
            )
        return TVar(env[db_term.index])

    if isinstance(db_term, DBFree):
        return TVar(db_term.name)

    if isinstance(db_term, DBLam):
        fresh = _fresh_name(set(env))
        body = from_debruijn(db_term.body, [fresh] + env)
        return Lam(fresh, db_term.var_type, body)

    if isinstance(db_term, DBApp):
        return App(from_debruijn(db_term.fn,  env),
                   from_debruijn(db_term.arg, env))

    if isinstance(db_term, DBPair):
        return Pair(from_debruijn(db_term.left,  env),
                    from_debruijn(db_term.right, env))

    if isinstance(db_term, DBFst):
        return Fst(from_debruijn(db_term.pair, env))

    if isinstance(db_term, DBSnd):
        return Snd(from_debruijn(db_term.pair, env))

    if isinstance(db_term, DBInl):
        return Inl(from_debruijn(db_term.value, env), db_term.right_type)

    if isinstance(db_term, DBInr):
        return Inr(from_debruijn(db_term.value, env), db_term.left_type)

    if isinstance(db_term, DBCase):
        # Branch variable types are not stored; cannot produce a typeable Case.
        raise NotImplementedError(
            "from_debruijn does not support DBCase: branch variable types "
            "are not stored in the nameless representation.  "
            "For α-equivalence, use alpha_equiv directly."
        )

    if isinstance(db_term, DBAbort):
        return Abort(from_debruijn(db_term.false_term, env), db_term.target_type)

    raise TypeError(f"from_debruijn: unknown DB term constructor {type(db_term).__name__!r}")


# ---------------------------------------------------------------------------
# Shift (index adjustment)
# ---------------------------------------------------------------------------

def shift(db_term, amount, cutoff=0):
    """Add `amount` to all free indices ≥ cutoff in db_term.

    "Free" means: not bound by a binder already inside db_term.
    `cutoff` tracks how many binders have been crossed since the top of
    the shift call.

    Use cases
    ---------
    * When placing a closed term under k new binders:
        shift(t, k, 0)
    * This is called automatically by subst when descending under binders,
      so callers of subst/subst_top do not need to call shift manually.

    Parameters
    ----------
    db_term : DBTerm
    amount  : int   (may be negative to "unshift", but rarely needed)
    cutoff  : int   (default 0; indices below this are already bound)
    """
    if isinstance(db_term, DBBound):
        if db_term.index >= cutoff:
            return DBBound(db_term.index + amount)
        return db_term

    if isinstance(db_term, DBFree):
        return db_term  # named free vars are not indexed

    if isinstance(db_term, DBLam):
        # Under the binder: cutoff increases by 1 (one more binder in scope)
        return DBLam(db_term.var_type,
                     shift(db_term.body, amount, cutoff + 1))

    if isinstance(db_term, DBApp):
        return DBApp(shift(db_term.fn,  amount, cutoff),
                     shift(db_term.arg, amount, cutoff))

    if isinstance(db_term, DBPair):
        return DBPair(shift(db_term.left,  amount, cutoff),
                      shift(db_term.right, amount, cutoff))

    if isinstance(db_term, DBFst):
        return DBFst(shift(db_term.pair, amount, cutoff))

    if isinstance(db_term, DBSnd):
        return DBSnd(shift(db_term.pair, amount, cutoff))

    if isinstance(db_term, DBInl):
        return DBInl(shift(db_term.value, amount, cutoff), db_term.right_type)

    if isinstance(db_term, DBInr):
        return DBInr(shift(db_term.value, amount, cutoff), db_term.left_type)

    if isinstance(db_term, DBCase):
        # Each branch body is under one additional binder (its own branch var)
        return DBCase(
            shift(db_term.scrutinee, amount, cutoff),
            shift(db_term.left_body,  amount, cutoff + 1),
            shift(db_term.right_body, amount, cutoff + 1),
        )

    if isinstance(db_term, DBAbort):
        return DBAbort(shift(db_term.false_term, amount, cutoff),
                       db_term.target_type)

    raise TypeError(f"shift: unknown DB term constructor {type(db_term).__name__!r}")


# ---------------------------------------------------------------------------
# Substitution
# ---------------------------------------------------------------------------

def subst(db_term, index, replacement):
    """Substitute DBBound(index) with replacement throughout db_term.

    This is the "decrement" (or "single substitution") convention:
    - Occurrences of DBBound(index) are replaced by replacement.
    - Occurrences of DBBound(j) with j > index are decremented to
      DBBound(j - 1), because the binder that owned index is consumed.
    - Occurrences of DBBound(j) with j < index are left unchanged
      (they are bound by inner binders above the substitution point).
    - When descending under a new binder (DBLam or DBCase branch), the
      target index is incremented by 1 and replacement is shifted by 1,
      because one more binder is now in scope.

    This convention makes β-reduction straightforward:
        (DBLam(A, body)) applied to arg  ≡  subst(body, 0, arg)

    Parameters
    ----------
    db_term     : DBTerm
    index       : int   — the de Bruijn index to replace
    replacement : DBTerm — the term to substitute in

    Capture-avoidance
    -----------------
    Capture is avoided structurally: replacement is shifted by 1 every
    time we cross a new binder, so its own free-variable indices continue
    to refer to the same outer bindings.  No explicit α-renaming is needed.
    """
    if isinstance(db_term, DBBound):
        if db_term.index == index:
            return replacement
        if db_term.index > index:
            return DBBound(db_term.index - 1)   # binder consumed, decrement
        return db_term                            # below substitution point

    if isinstance(db_term, DBFree):
        return db_term

    if isinstance(db_term, DBLam):
        # Under binder: the target index shifts up by 1, and replacement
        # must be shifted up by 1 so its free vars still point outward.
        return DBLam(db_term.var_type,
                     subst(db_term.body,
                           index + 1,
                           shift(replacement, 1, 0)))

    if isinstance(db_term, DBApp):
        return DBApp(subst(db_term.fn,  index, replacement),
                     subst(db_term.arg, index, replacement))

    if isinstance(db_term, DBPair):
        return DBPair(subst(db_term.left,  index, replacement),
                      subst(db_term.right, index, replacement))

    if isinstance(db_term, DBFst):
        return DBFst(subst(db_term.pair, index, replacement))

    if isinstance(db_term, DBSnd):
        return DBSnd(subst(db_term.pair, index, replacement))

    if isinstance(db_term, DBInl):
        return DBInl(subst(db_term.value, index, replacement), db_term.right_type)

    if isinstance(db_term, DBInr):
        return DBInr(subst(db_term.value, index, replacement), db_term.left_type)

    if isinstance(db_term, DBCase):
        # Each branch body is under one additional binder; same shift logic as DBLam.
        shifted = shift(replacement, 1, 0)
        return DBCase(
            subst(db_term.scrutinee, index,     replacement),
            subst(db_term.left_body,  index + 1, shifted),
            subst(db_term.right_body, index + 1, shifted),
        )

    if isinstance(db_term, DBAbort):
        return DBAbort(subst(db_term.false_term, index, replacement),
                       db_term.target_type)

    raise TypeError(f"subst: unknown DB term constructor {type(db_term).__name__!r}")


def subst_top(replacement, body):
    """β-reduction step: substitute replacement for the outermost binder.

    For a β-redex `(DBLam(A, body)) replacement`, the result is:
        subst_top(replacement, body)  =  subst(body, 0, replacement)

    Parameters
    ----------
    replacement : DBTerm  — the argument being substituted (was outside λ)
    body        : DBTerm  — the lambda body (uses DBBound(0) for the param)
    """
    return subst(body, 0, replacement)


# ---------------------------------------------------------------------------
# α-equivalence
# ---------------------------------------------------------------------------

def alpha_equiv(term1, term2) -> bool:
    """Return True iff the two named proof terms are α-equivalent.

    Two terms are α-equivalent iff they have the same structure up to
    renaming of bound variables.  This is decided by comparing their
    de Bruijn representations, which are identical for α-equivalent terms.

    Free variables must have the same names.
    Type annotations (var_type in Lam, right_type in Inl, etc.) are
    compared structurally.

    Parameters
    ----------
    term1, term2 : Term (from stele.core.terms)

    Returns
    -------
    bool

    Examples
    --------
    >>> from stele.ast import Var
    >>> alpha_equiv(Lam("x", Var("A"), TVar("x")),
    ...             Lam("y", Var("A"), TVar("y")))
    True
    >>> alpha_equiv(Lam("x", Var("A"), TVar("x")),
    ...             Lam("x", Var("A"), TVar("y")))   # body refers to different var
    False
    """
    try:
        return to_debruijn(term1) == to_debruijn(term2)
    except (TypeError, ValueError):
        return False
