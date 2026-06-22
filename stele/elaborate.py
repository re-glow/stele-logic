"""Script-to-proof-term elaboration for the intuitionistic propositional fragment.

Walks the Stele proof AST and constructs a corresponding proof term under
the Curry-Howard correspondence.  Does not modify or replace the trusted kernel.

Supported rules
---------------
  copy, mp
  and_intro, and_elim_left, and_elim_right
  imp_intro, neg_intro, neg_elim
  ex_falso
  or_intro_left, or_intro_right, or_elim

Unsupported rules (classical)
------------------------------
  dne, lem, pbc -> ElaborationError

Usage
-----
  from stele.elaborate import elaborate_theorem, crosscheck_theorem

  elab = elaborate_theorem(thm)          # proof term only
  result = crosscheck_theorem(thm)       # kernel + elaboration + typecheck
"""
from dataclasses import dataclass, field

from .ast import Op, pretty
from .proof import Assume, Have, Suppose, Conclude
from .core.terms import TVar, Lam, App, Pair, Fst, Snd, Inl, Inr, Case, Abort
from .core.typing import infer, check, TypingError, empty_ctx, extend


class ElaborationError(Exception):
    """Raised when a proof script step cannot be elaborated into a proof term."""


_CLASSICAL_RULES = frozenset({"dne", "lem", "pbc"})


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------

@dataclass
class ElaboratedTheorem:
    """A proof script successfully elaborated into a typed proof term."""
    name: str
    conclusion: object              # Formula
    term: object                    # Term
    inferred_type: object           # Formula
    label_terms: dict = field(default_factory=dict)  # label -> Term


@dataclass
class CrossCheckResult:
    """Combined result of kernel verification + proof-term elaboration + typecheck."""
    name: str
    script_ok: bool = False
    elaboration_ok: bool = False
    typecheck_ok: bool = False
    term: object = None
    script_error: str = None
    elab_error: str = None
    type_error: str = None

    @property
    def ok(self):
        return self.script_ok and self.elaboration_ok and self.typecheck_ok


# ---------------------------------------------------------------------------
# Internal subproof tracker
# ---------------------------------------------------------------------------

class _ESubproof:
    def __init__(self, assume_label, assume_formula, locals_term):
        self.assume_label = assume_label
        self.assume_formula = assume_formula
        self.locals_term = locals_term   # dict[str, Term]


def _find_subproof(assume_label, concl_label, subproofs):
    for sp in reversed(subproofs):
        if sp.assume_label == assume_label and concl_label in sp.locals_term:
            return sp
    raise ElaborationError(
        f"no closed subproof found that assumes '{assume_label}' "
        f"and derives '{concl_label}'"
    )


# ---------------------------------------------------------------------------
# Core elaboration
# ---------------------------------------------------------------------------

def _elaborate_block(nodes, term_env, formula_env, subproofs):
    for node in nodes:
        if isinstance(node, Assume):
            term_env[node.label] = TVar(node.label)
            formula_env[node.label] = node.formula

        elif isinstance(node, Suppose):
            inner_term = dict(term_env)
            inner_formula = dict(formula_env)
            inner_term[node.label] = TVar(node.label)
            inner_formula[node.label] = node.formula
            inner_subproofs = list(subproofs)
            _elaborate_block(node.body, inner_term, inner_formula, inner_subproofs)
            locals_term = {k: v for k, v in inner_term.items() if k not in term_env}
            subproofs.append(_ESubproof(
                assume_label=node.label,
                assume_formula=node.formula,
                locals_term=locals_term,
            ))

        elif isinstance(node, Have):
            t = _elaborate_rule(node, term_env, formula_env, subproofs)
            term_env[node.label] = t
            formula_env[node.label] = node.formula

        elif isinstance(node, Conclude):
            pass  # term is already in term_env[node.ref]


def _elaborate_rule(node, term_env, formula_env, subproofs):
    rule = node.rule
    refs = node.refs
    formula = node.formula

    if rule in _CLASSICAL_RULES:
        raise ElaborationError(
            f"rule '{rule}' is a classical rule; "
            "proof-term elaboration for classical principles is not supported in v1"
        )

    if rule == "copy":
        if refs[0] not in term_env:
            raise ElaborationError(f"copy: unknown reference '{refs[0]}'")
        return term_env[refs[0]]

    if rule == "mp":
        return App(term_env[refs[0]], term_env[refs[1]])

    if rule == "and_intro":
        return Pair(term_env[refs[0]], term_env[refs[1]])

    if rule == "and_elim_left":
        return Fst(term_env[refs[0]])

    if rule == "and_elim_right":
        return Snd(term_env[refs[0]])

    if rule == "imp_intro":
        assume_label, concl_label = refs[0], refs[1]
        sp = _find_subproof(assume_label, concl_label, subproofs)
        return Lam(assume_label, sp.assume_formula, sp.locals_term[concl_label])

    if rule == "neg_intro":
        # not A = A -> false; same elaboration as imp_intro
        assume_label, bot_label = refs[0], refs[1]
        sp = _find_subproof(assume_label, bot_label, subproofs)
        return Lam(assume_label, sp.assume_formula, sp.locals_term[bot_label])

    if rule == "neg_elim":
        # neg_elim a_ref not_a_ref; since not A = A -> false: App(not_a, a)
        return App(term_env[refs[1]], term_env[refs[0]])

    if rule == "ex_falso":
        return Abort(term_env[refs[0]], formula)

    if rule == "or_intro_left":
        if not (isinstance(formula, Op) and formula.sym == "or"):
            raise ElaborationError(
                f"or_intro_left: result formula must be a disjunction, got {pretty(formula)}"
            )
        B = formula.args[1]
        return Inl(term_env[refs[0]], B)

    if rule == "or_intro_right":
        if not (isinstance(formula, Op) and formula.sym == "or"):
            raise ElaborationError(
                f"or_intro_right: result formula must be a disjunction, got {pretty(formula)}"
            )
        A = formula.args[0]
        return Inr(term_env[refs[0]], A)

    if rule == "or_elim":
        disj_ref = refs[0]
        left_assume, left_concl = refs[1], refs[2]
        right_assume, right_concl = refs[3], refs[4]
        left_sp = _find_subproof(left_assume, left_concl, subproofs)
        right_sp = _find_subproof(right_assume, right_concl, subproofs)
        return Case(
            term_env[disj_ref],
            left_assume, left_sp.locals_term[left_concl],
            right_assume, right_sp.locals_term[right_concl],
        )

    raise ElaborationError(
        f"rule '{rule}' is not supported by the proof-term elaborator in v1"
    )


def _find_conclusion_node(thm):
    for node in thm.lines:
        if isinstance(node, Conclude):
            return node
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def elaborate_theorem(thm, logic_name="intuitionistic_prop"):
    """Elaborate a proof script into a proof term.

    Does NOT run the kernel; the proof script is assumed valid by the caller.
    Use crosscheck_theorem for combined kernel + elaboration + typecheck.

    Returns: ElaboratedTheorem
    Raises:  ElaborationError
    """
    term_env = {}
    formula_env = {}
    subproofs = []
    _elaborate_block(thm.lines, term_env, formula_env, subproofs)

    conclude_node = _find_conclusion_node(thm)
    if conclude_node is None:
        raise ElaborationError("theorem has no 'conclude' statement")

    concl_ref = conclude_node.ref
    conclusion_formula = conclude_node.formula
    result_term = term_env.get(concl_ref)
    if result_term is None:
        raise ElaborationError(f"conclude references unknown label '{concl_ref}'")

    # Build typing context from top-level Assume nodes only.
    top_ctx = empty_ctx()
    for node in thm.lines:
        if isinstance(node, Assume):
            top_ctx = extend(top_ctx, node.label, node.formula)

    try:
        inferred = infer(top_ctx, result_term)
    except TypingError as e:
        raise ElaborationError(f"proof term failed to typecheck: {e}") from e

    return ElaboratedTheorem(
        name=thm.name,
        conclusion=conclusion_formula,
        term=result_term,
        inferred_type=inferred,
        label_terms=dict(term_env),
    )


def crosscheck_theorem(thm, logic_name="intuitionistic_prop"):
    """Run kernel verification, elaborate into proof term, and typecheck.

    Step 1: kernel check (proof script validity).
    Step 2: elaboration into a proof term.
    Step 3: proof-term typecheck against theorem conclusion.

    All three must succeed for CrossCheckResult.ok to be True.
    The kernel check uses logic_name; elaboration always targets the
    intuitionistic fragment regardless of logic_name.
    """
    from .kernel import check_theorem
    from .errors import ProofError, SteleError

    result = CrossCheckResult(name=thm.name)

    # Step 1: kernel
    try:
        check_theorem(thm, logic_name)
        result.script_ok = True
    except (ProofError, SteleError) as e:
        result.script_error = str(e)
        return result

    # Step 2: elaborate
    try:
        elab = elaborate_theorem(thm, logic_name)
        result.elaboration_ok = True
        result.term = elab.term
    except ElaborationError as e:
        result.elab_error = str(e)
        return result

    # Step 3: typecheck
    top_ctx = empty_ctx()
    for node in thm.lines:
        if isinstance(node, Assume):
            top_ctx = extend(top_ctx, node.label, node.formula)
    try:
        check(top_ctx, elab.term, elab.conclusion)
        result.typecheck_ok = True
    except TypingError as e:
        result.type_error = str(e)

    return result


# ---------------------------------------------------------------------------
# Pretty printer for proof terms (Part E)
# ---------------------------------------------------------------------------

def pretty_term(term):
    """Return a surface-syntax string for a proof term.

    The output uses the same syntax accepted by stele.core.term_parser.parse_term,
    so it can be round-tripped back to a term object.
    """
    if isinstance(term, TVar):
        return term.name
    if isinstance(term, Lam):
        body_s = pretty_term(term.body)
        return f"fun {term.var}: {pretty(term.var_type)} => {body_s}"
    if isinstance(term, App):
        fn_s = pretty_term(term.fn)
        arg_s = pretty_term(term.arg)
        if isinstance(term.fn, (Lam, Case)):
            fn_s = f"({fn_s})"
        if isinstance(term.arg, (Lam, App, Case, Pair)):
            arg_s = f"({arg_s})"
        return f"{fn_s}({arg_s})"
    if isinstance(term, Pair):
        return f"pair({pretty_term(term.left)}, {pretty_term(term.right)})"
    if isinstance(term, Fst):
        return f"fst({pretty_term(term.pair)})"
    if isinstance(term, Snd):
        return f"snd({pretty_term(term.pair)})"
    if isinstance(term, Inl):
        return f"inl({pretty_term(term.value)}, {pretty(term.right_type)})"
    if isinstance(term, Inr):
        return f"inr({pretty_term(term.value)}, {pretty(term.left_type)})"
    if isinstance(term, Case):
        s = pretty_term(term.scrutinee)
        lb = pretty_term(term.left_body)
        rb = pretty_term(term.right_body)
        return (f"case {s} of inl {term.left_var} => {lb} | "
                f"inr {term.right_var} => {rb}")
    if isinstance(term, Abort):
        return f"abort({pretty_term(term.false_term)}, {pretty(term.target_type)})"
    return repr(term)
