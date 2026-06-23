"""Small independent-ish certificate checker for Stele proof certificates.

PURPOSE
-------
Provide an additional verification path that re-checks a stele-proof-certificate
JSON document without calling the main stele.kernel, stele.parser, or
stele.diagnostics layers.  This increases confidence by checking the same
certified claim through a different code path.

INDEPENDENCE BOUNDARY
---------------------
This module:
  - does NOT import stele.kernel
  - does NOT import stele.parser
  - does NOT import stele.diagnostics
  - does NOT import stele.proof  (proof-node AST; only needed by parser/kernel)
  - DOES import stele.ast for Var/Op formula dataclasses (pure frozen data)
  - DOES import stele.certificate for formula_from_json (formula deserializer)

stele.ast contains only frozen dataclasses and a pretty-printer; it has
no trust-relevant logic.  stele.certificate's formula_from_json is a
trivial JSON→dataclass converter.

IMPORTANT: This is still Python and is not formally verified.  It provides
an independent-ish second check, not a proof of checker correctness.
A future Rust/OCaml port may provide stronger independence guarantees.

SUPPORTED RULES
---------------
Shared (intuitionistic_prop and classical_prop):
  copy, mp, and_intro, and_elim_left, and_elim_right,
  neg_elim, ex_falso, or_intro_left, or_intro_right,
  imp_intro, neg_intro, or_elim

Classical-only (classical_prop only):
  dne, lem, pbc

DISCHARGE RULES
---------------
imp_intro, neg_intro, pbc each consume one subproof reference pair
(suppose_label, inner_label).  or_elim consumes one ordinary premise
and two subproof reference pairs.

The certificate encodes subproof scopes via suppose_open / suppose_close
steps.  Minicheck reconstructs closed subproof records from these
markers and uses them to verify discharge-rule applications.
"""
from .ast import Var, Op
from .certificate import formula_from_json


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class MiniCheckError(Exception):
    """Raised by minicheck() when the certificate is rejected."""


class MiniCheckResult:
    """Result of a minicheck run."""
    __slots__ = ("ok", "message", "theorem", "logic")

    def __init__(self, ok: bool, message: str, theorem: str = "", logic: str = ""):
        self.ok = ok
        self.message = message
        self.theorem = theorem
        self.logic = logic

    def __repr__(self):
        return (f"MiniCheckResult(ok={self.ok}, theorem={self.theorem!r}, "
                f"logic={self.logic!r}, message={self.message!r})")


def minicheck(cert: dict) -> MiniCheckResult:
    """Re-verify a stele-proof-certificate dict.

    Parameters
    ----------
    cert : dict
        A certificate as returned by certificate.emit_certificate() or
        loaded via certificate.certificate_from_json().

    Returns
    -------
    MiniCheckResult  with ok=True on success.

    Raises
    ------
    MiniCheckError  if the certificate is structurally malformed.
    On rule/logic/formula failures, returns MiniCheckResult(ok=False, ...).
    """
    try:
        return _minicheck_inner(cert)
    except MiniCheckError:
        raise
    except Exception as e:
        return MiniCheckResult(ok=False, message=f"unexpected error: {e}")


# ---------------------------------------------------------------------------
# Logic rule sets (no import of stele.logic or stele.kernel)
# ---------------------------------------------------------------------------

_INTUIT_RULES = frozenset({
    "copy", "mp", "and_intro", "and_elim_left", "and_elim_right",
    "neg_elim", "ex_falso", "or_intro_left", "or_intro_right",
    "imp_intro", "neg_intro", "or_elim",
})
_CLASSICAL_RULES = _INTUIT_RULES | frozenset({"dne", "lem", "pbc"})

_RULES_BY_LOGIC = {
    "intuitionistic_prop": _INTUIT_RULES,
    "classical_prop":      _CLASSICAL_RULES,
}


# ---------------------------------------------------------------------------
# Formula helpers (local; no import of stele.kernel or typing)
# ---------------------------------------------------------------------------

_BOT = Op("bot", ())


def _norm(f):
    """Normalise Op("not", (A,)) to Op("imp", (A, ⊥)).

    Mirrors the normalisation performed by stele.core.typing.normalize_neg,
    implemented here independently to avoid importing the proof-term layer.
    """
    if isinstance(f, Op):
        if f.sym == "not":
            return Op("imp", (_norm(f.args[0]), _BOT))
        return Op(f.sym, tuple(_norm(a) for a in f.args))
    return f


def _feq(a, b) -> bool:
    """Formula equality modulo not-normalisation."""
    return _norm(a) == _norm(b)


def _expect_imp(f):
    n = _norm(f)
    if isinstance(n, Op) and n.sym == "imp":
        return n.args
    raise _Fail(f"expected implication, got {_pp(f)}")


def _expect_and(f):
    if isinstance(f, Op) and f.sym == "and":
        return f.args
    raise _Fail(f"expected conjunction, got {_pp(f)}")


def _expect_or(f):
    if isinstance(f, Op) and f.sym == "or":
        return f.args
    raise _Fail(f"expected disjunction, got {_pp(f)}")


def _expect_not(f):
    """Return the body of a negation (A → ⊥ or Op('not',…))."""
    n = _norm(f)
    if isinstance(n, Op) and n.sym == "imp":
        A, B = n.args
        if isinstance(B, Op) and B.sym == "bot":
            return A
    raise _Fail(f"expected negation, got {_pp(f)}")


def _expect_bot(f):
    if not (isinstance(f, Op) and f.sym == "bot"):
        raise _Fail(f"expected ⊥, got {_pp(f)}")


def _pp(f) -> str:
    from .ast import pretty
    return pretty(f)


class _Fail(Exception):
    """Internal short-circuit for rule-check failures."""


# ---------------------------------------------------------------------------
# Closed-subproof record
# ---------------------------------------------------------------------------

class _ClosedSubproof:
    __slots__ = ("assume_label", "assume_formula", "inner")

    def __init__(self, assume_label: str, assume_formula, inner: dict):
        self.assume_label = assume_label
        self.assume_formula = assume_formula
        # inner: {label → formula} for all labels introduced inside this scope
        self.inner = inner


# ---------------------------------------------------------------------------
# Rule checkers
# Each takes (refs, scope, closed_subproofs) and returns the conclusion formula.
# scope: dict[label → formula] — currently accessible labels
# closed_subproofs: dict[assume_label → _ClosedSubproof]
# ---------------------------------------------------------------------------

def _get(scope, label):
    if label not in scope:
        raise _Fail(f"label {label!r} not in current scope")
    return scope[label]


def _get_subproof(csp, assume_label, concl_label):
    sp = csp.get(assume_label)
    if sp is None:
        raise _Fail(f"no closed subproof for assume label {assume_label!r}")
    if concl_label not in sp.inner:
        raise _Fail(
            f"label {concl_label!r} not derived in subproof of {assume_label!r}")
    return sp


def _check_refs(rule, refs, expected):
    if len(refs) != expected:
        raise _Fail(
            f"rule {rule!r} expects {expected} ref(s), got {len(refs)}")


def _rule_copy(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 1)
    f = _get(scope, refs[0])
    if not _feq(f, concl):
        raise _Fail(f"copy: {_pp(f)} ≠ {_pp(concl)}")
    return concl


def _rule_mp(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 2)
    imp_f = _get(scope, refs[0])
    ant_f = _get(scope, refs[1])
    A, B = _expect_imp(imp_f)
    if not _feq(ant_f, A):
        raise _Fail(f"mp: antecedent {_pp(ant_f)} ≠ {_pp(A)}")
    if not _feq(B, concl):
        raise _Fail(f"mp: consequent {_pp(B)} ≠ {_pp(concl)}")
    return concl


def _rule_and_intro(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 2)
    A = _get(scope, refs[0])
    B = _get(scope, refs[1])
    expected = Op("and", (A, B))
    if not _feq(expected, concl):
        raise _Fail(f"and_intro: {_pp(expected)} ≠ {_pp(concl)}")
    return concl


def _rule_and_elim_left(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 1)
    A, _ = _expect_and(_get(scope, refs[0]))
    if not _feq(A, concl):
        raise _Fail(f"and_elim_left: {_pp(A)} ≠ {_pp(concl)}")
    return concl


def _rule_and_elim_right(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 1)
    _, B = _expect_and(_get(scope, refs[0]))
    if not _feq(B, concl):
        raise _Fail(f"and_elim_right: {_pp(B)} ≠ {_pp(concl)}")
    return concl


def _rule_neg_elim(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 2)
    A   = _get(scope, refs[0])
    nA  = _get(scope, refs[1])
    _expect_not(nA)  # checks it is negation; body should match A
    body = _expect_not(nA)
    if not _feq(A, body):
        raise _Fail(f"neg_elim: positive {_pp(A)} ≠ negation body {_pp(body)}")
    _expect_bot(concl)
    return concl


def _rule_ex_falso(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 1)
    _expect_bot(_get(scope, refs[0]))
    return concl


def _rule_or_intro_left(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 1)
    A = _get(scope, refs[0])
    L, R = _expect_or(concl)
    if not _feq(A, L):
        raise _Fail(f"or_intro_left: premise {_pp(A)} ≠ left disjunct {_pp(L)}")
    return concl


def _rule_or_intro_right(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 1)
    B = _get(scope, refs[0])
    L, R = _expect_or(concl)
    if not _feq(B, R):
        raise _Fail(f"or_intro_right: premise {_pp(B)} ≠ right disjunct {_pp(R)}")
    return concl


def _rule_imp_intro(rule, refs, scope, csp, concl):
    # refs = [assume_label, concl_label]  (one hyp_premise)
    _check_refs(rule, refs, 2)
    sp = _get_subproof(csp, refs[0], refs[1])
    A = sp.assume_formula
    B = sp.inner[refs[1]]
    expected = Op("imp", (A, B))
    if not _feq(expected, concl):
        raise _Fail(f"imp_intro: {_pp(expected)} ≠ {_pp(concl)}")
    return concl


def _rule_neg_intro(rule, refs, scope, csp, concl):
    # refs = [assume_label, false_label]  (one hyp_premise: A → ⊥)
    _check_refs(rule, refs, 2)
    sp = _get_subproof(csp, refs[0], refs[1])
    A = sp.assume_formula
    _expect_bot(sp.inner[refs[1]])
    # conclusion must be not A  (= A → ⊥)
    body = _expect_not(concl)
    if not _feq(A, body):
        raise _Fail(f"neg_intro: assumed {_pp(A)} ≠ negation body {_pp(body)}")
    return concl


def _rule_or_elim(rule, refs, scope, csp, concl):
    # refs = [disj_label, a_label, ca_label, b_label, cb_label]
    # one ordinary premise + two hyp_premises
    _check_refs(rule, refs, 5)
    disj = _get(scope, refs[0])
    A, B = _expect_or(disj)
    sp1 = _get_subproof(csp, refs[1], refs[2])
    sp2 = _get_subproof(csp, refs[3], refs[4])
    if not _feq(sp1.assume_formula, A):
        raise _Fail(
            f"or_elim: left subproof assumes {_pp(sp1.assume_formula)}, "
            f"expected left disjunct {_pp(A)}")
    if not _feq(sp2.assume_formula, B):
        raise _Fail(
            f"or_elim: right subproof assumes {_pp(sp2.assume_formula)}, "
            f"expected right disjunct {_pp(B)}")
    C1 = sp1.inner[refs[2]]
    C2 = sp2.inner[refs[4]]
    if not _feq(C1, C2):
        raise _Fail(
            f"or_elim: branch conclusions disagree — "
            f"{_pp(C1)} vs {_pp(C2)}")
    if not _feq(C1, concl):
        raise _Fail(f"or_elim: {_pp(C1)} ≠ {_pp(concl)}")
    return concl


def _rule_dne(rule, refs, scope, csp, concl):
    _check_refs(rule, refs, 1)
    nn_f = _get(scope, refs[0])
    # nn_f should be ¬¬A; extract A
    inner = _expect_not(nn_f)   # inner = ¬A
    A = _expect_not(inner)      # A
    if not _feq(A, concl):
        raise _Fail(f"dne: {_pp(A)} ≠ {_pp(concl)}")
    return concl


def _rule_lem(rule, refs, scope, csp, concl):
    # lem: 0 ordinary refs, conclusion = A or not A
    _check_refs(rule, refs, 0)
    L, R = _expect_or(concl)
    body = _expect_not(R)
    if not _feq(L, body):
        raise _Fail(
            f"lem: conclusion {_pp(concl)} does not have shape A or not A")
    return concl


def _rule_pbc(rule, refs, scope, csp, concl):
    # refs = [not_assume_label, false_label]  (one hyp_premise: ¬A → ⊥)
    _check_refs(rule, refs, 2)
    sp = _get_subproof(csp, refs[0], refs[1])
    nA = sp.assume_formula
    A = _expect_not(nA)
    _expect_bot(sp.inner[refs[1]])
    if not _feq(A, concl):
        raise _Fail(f"pbc: {_pp(A)} ≠ {_pp(concl)}")
    return concl


_RULE_CHECKERS = {
    "copy":            _rule_copy,
    "mp":              _rule_mp,
    "and_intro":       _rule_and_intro,
    "and_elim_left":   _rule_and_elim_left,
    "and_elim_right":  _rule_and_elim_right,
    "neg_elim":        _rule_neg_elim,
    "ex_falso":        _rule_ex_falso,
    "or_intro_left":   _rule_or_intro_left,
    "or_intro_right":  _rule_or_intro_right,
    "imp_intro":       _rule_imp_intro,
    "neg_intro":       _rule_neg_intro,
    "or_elim":         _rule_or_elim,
    "dne":             _rule_dne,
    "lem":             _rule_lem,
    "pbc":             _rule_pbc,
}


# ---------------------------------------------------------------------------
# Core checker
# ---------------------------------------------------------------------------

def _minicheck_inner(cert: dict) -> MiniCheckResult:
    # ── Structural validation ───────────────────────────────────────────────
    fmt = cert.get("format")
    ver = cert.get("version")
    if fmt != "stele-proof-certificate":
        raise MiniCheckError(f"unknown certificate format: {fmt!r}")
    if ver != "1":
        raise MiniCheckError(f"unsupported certificate version: {ver!r}")

    theorem = cert.get("theorem", "?")
    logic   = cert.get("logic",   "?")

    if logic not in _RULES_BY_LOGIC:
        return MiniCheckResult(
            ok=False,
            message=f"unsupported logic {logic!r}",
            theorem=theorem, logic=logic,
        )
    allowed_rules = _RULES_BY_LOGIC[logic]

    conclusion_json = cert.get("conclusion")
    if conclusion_json is None:
        raise MiniCheckError("certificate missing 'conclusion' field")

    try:
        expected_conclusion = formula_from_json(conclusion_json)
    except (ValueError, KeyError, TypeError) as e:
        raise MiniCheckError(f"malformed conclusion formula: {e}") from e

    steps = cert.get("steps")
    if not isinstance(steps, list):
        raise MiniCheckError("certificate 'steps' must be a list")

    # ── Scope state ─────────────────────────────────────────────────────────
    scope: dict = {}          # label → formula (currently accessible)
    # scope_frames: list of (frozenset_of_outer_keys, assume_label)
    scope_frames: list = []
    # closed_subproofs: assume_label → _ClosedSubproof
    closed_subproofs: dict = {}
    actual_conclusion = None

    # ── Process steps ───────────────────────────────────────────────────────
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise MiniCheckError(f"step {i}: not a dict")
        kind = step.get("kind")

        try:
            if kind == "assume":
                label   = _req_str(step, "label", i)
                formula = _req_formula(step, "formula", i)
                _check_unique(scope, label, i)
                scope[label] = formula

            elif kind == "suppose_open":
                label   = _req_str(step, "label", i)
                formula = _req_formula(step, "formula", i)
                _check_unique(scope, label, i)
                scope_frames.append((frozenset(scope.keys()), label))
                scope[label] = formula

            elif kind == "suppose_close":
                label = _req_str(step, "label", i)
                if not scope_frames:
                    raise MiniCheckError(
                        f"step {i}: suppose_close without matching suppose_open")
                outer_keys, open_label = scope_frames[-1]
                if open_label != label:
                    raise MiniCheckError(
                        f"step {i}: suppose_close {label!r} mismatches "
                        f"innermost suppose_open {open_label!r}")
                scope_frames.pop()
                # Collect all labels introduced in this scope
                inner_labels = {k for k in scope if k not in outer_keys}
                inner = {k: scope[k] for k in inner_labels}
                assume_formula = scope[label]
                closed_subproofs[label] = _ClosedSubproof(
                    assume_label=label,
                    assume_formula=assume_formula,
                    inner=inner,
                )
                # Remove inner labels from active scope
                for k in inner_labels:
                    del scope[k]

            elif kind == "have":
                label   = _req_str(step, "label", i)
                formula = _req_formula(step, "formula", i)
                rule    = _req_str(step, "rule", i)
                refs    = step.get("refs", [])
                if not isinstance(refs, list):
                    raise MiniCheckError(f"step {i}: 'refs' must be a list")

                if rule not in allowed_rules:
                    return MiniCheckResult(
                        ok=False,
                        message=(f"step {i} (label {label!r}): "
                                 f"rule {rule!r} is not available in logic {logic!r}"),
                        theorem=theorem, logic=logic,
                    )

                checker = _RULE_CHECKERS.get(rule)
                if checker is None:
                    return MiniCheckResult(
                        ok=False,
                        message=f"step {i}: unsupported rule {rule!r} in minicheck",
                        theorem=theorem, logic=logic,
                    )

                try:
                    checker(rule, refs, scope, closed_subproofs, formula)
                except _Fail as e:
                    return MiniCheckResult(
                        ok=False,
                        message=(f"step {i} (label {label!r}, rule {rule!r}): {e}"),
                        theorem=theorem, logic=logic,
                    )

                _check_unique(scope, label, i)
                scope[label] = formula

            elif kind == "conclude":
                ref     = _req_str(step, "ref", i)
                formula = _req_formula(step, "formula", i)
                if ref not in scope:
                    return MiniCheckResult(
                        ok=False,
                        message=f"step {i}: conclude references unknown label {ref!r}",
                        theorem=theorem, logic=logic,
                    )
                if not _feq(scope[ref], formula):
                    return MiniCheckResult(
                        ok=False,
                        message=(
                            f"step {i}: conclude formula {_pp(formula)!r} "
                            f"does not match {ref!r} = {_pp(scope[ref])!r}"),
                        theorem=theorem, logic=logic,
                    )
                actual_conclusion = formula

            else:
                raise MiniCheckError(f"step {i}: unknown step kind {kind!r}")

        except MiniCheckError:
            raise

    # ── Final checks ────────────────────────────────────────────────────────
    if scope_frames:
        return MiniCheckResult(
            ok=False,
            message="unclosed subproof scopes at end of certificate",
            theorem=theorem, logic=logic,
        )

    if actual_conclusion is None:
        return MiniCheckResult(
            ok=False, message="no 'conclude' step found",
            theorem=theorem, logic=logic,
        )

    if not _feq(actual_conclusion, expected_conclusion):
        return MiniCheckResult(
            ok=False,
            message=(f"actual conclusion {_pp(actual_conclusion)!r} "
                     f"does not match declared conclusion {_pp(expected_conclusion)!r}"),
            theorem=theorem, logic=logic,
        )

    return MiniCheckResult(
        ok=True,
        message=f"certificate for '{theorem}' verified under {logic!r}",
        theorem=theorem, logic=logic,
    )


# ---------------------------------------------------------------------------
# Step field helpers
# ---------------------------------------------------------------------------

def _req_str(step, key, i):
    v = step.get(key)
    if not isinstance(v, str):
        raise MiniCheckError(f"step {i}: {key!r} must be a string, got {v!r}")
    return v


def _req_formula(step, key, i):
    d = step.get(key)
    if d is None:
        raise MiniCheckError(f"step {i}: missing {key!r}")
    try:
        return formula_from_json(d)
    except (ValueError, KeyError, TypeError) as e:
        raise MiniCheckError(f"step {i}: malformed formula for {key!r}: {e}") from e


def _check_unique(scope, label, i):
    if label in scope:
        raise MiniCheckError(f"step {i}: duplicate label {label!r}")
