"""Trusted core: rule-schema instantiation + proof-tree checking.

The kernel does not know what any connective *means*. It only checks that
each step is a valid instance of a rule declared by the loaded logic, and
that hypothesis scope/discharge is respected. Matching is purely syntactic
and decidable -- de Bruijn criterion: this file is the entire trust boundary.
"""
from .ast import Var, Op, pretty
from .proof import Assume, Have, Suppose, Conclude
from .errors import ProofError
from .logic import get_logic


def match(pat, tgt, metavars, subst):
    if isinstance(pat, Var):
        if pat.name in metavars:
            if pat.name in subst:
                return subst if subst[pat.name] == tgt else None
            out = dict(subst)
            out[pat.name] = tgt
            return out
        return subst if pat == tgt else None
    if isinstance(pat, Op):
        if not isinstance(tgt, Op) or pat.sym != tgt.sym or len(pat.args) != len(tgt.args):
            return None
        for p, t in zip(pat.args, tgt.args):
            subst = match(p, t, metavars, subst)
            if subst is None:
                return None
        return subst
    return None


def instantiate(pat, subst):
    if isinstance(pat, Var):
        return subst.get(pat.name, pat)
    if isinstance(pat, Op):
        return Op(pat.sym, tuple(instantiate(a, subst) for a in pat.args))
    return pat


class Subproof:
    def __init__(self, assume_label, assume_formula, local_env):
        self.assume_label = assume_label
        self.assume_formula = assume_formula
        self.locals = local_env


def check_theorem(thm, logic_override=None):
    name = logic_override or thm.logic or "intuitionistic_prop"
    logic = get_logic(name)
    env = {}
    concluded = _check_block(thm.lines, env, logic, top=True)
    return logic, concluded


def _check_block(lines, env, logic, top=False):
    subproofs = []
    concluded = None
    for node in lines:
        if isinstance(node, Assume):
            if node.label in env:
                raise ProofError(f"duplicate label '{node.label}'", node.line)
            env[node.label] = node.formula
        elif isinstance(node, Suppose):
            inner = dict(env)
            if node.label in inner:
                raise ProofError(f"duplicate label '{node.label}'", node.line)
            inner[node.label] = node.formula
            _check_block(node.body, inner, logic)
            local_env = {k: v for k, v in inner.items() if k not in env}
            subproofs.append(Subproof(node.label, node.formula, local_env))
        elif isinstance(node, Have):
            result = _apply_rule(node, env, logic, subproofs)
            if result != node.formula:
                raise ProofError(
                    f"rule '{node.rule}' yields {pretty(result)}, "
                    f"but the line claims {pretty(node.formula)}", node.line)
            if node.label in env:
                raise ProofError(f"duplicate label '{node.label}'", node.line)
            env[node.label] = node.formula
        elif isinstance(node, Conclude):
            if node.ref not in env:
                raise ProofError(f"unknown reference '{node.ref}'", node.line)
            if env[node.ref] != node.formula:
                raise ProofError(
                    f"conclusion {pretty(node.formula)} does not match "
                    f"'{node.ref}' = {pretty(env[node.ref])}", node.line)
            concluded = node.formula
    if top and concluded is None:
        raise ProofError("proof has no 'conclude' line")
    return concluded


def _apply_rule(node, env, logic, subproofs):
    rule = node.rule
    schema = logic.rules.get(rule)
    if schema is None:
        raise ProofError(
            f"rule '{rule}' is not available in logic '{logic.name}'", node.line)
    n_ord = len(schema.premises)
    n_hyp = len(schema.hyp_premises)
    expected = n_ord + 2 * n_hyp
    if len(node.refs) != expected:
        raise ProofError(
            f"rule '{rule}' expects {expected} argument(s) "
            f"({n_ord} premise(s), {n_hyp} subproof(s)), "
            f"got {len(node.refs)}", node.line)

    subst = {}

    # Ordinary premises — matched against the current environment.
    for i, (pat, ref) in enumerate(zip(schema.premises, node.refs[:n_ord]), start=1):
        if ref not in env:
            raise ProofError(f"unknown reference '{ref}'", node.line)
        new = match(pat, env[ref], schema.metavars, subst)
        if new is None:
            expected_f = pretty(instantiate(pat, subst))
            raise ProofError(
                f"rule '{rule}': premise {i} expected {expected_f}, "
                f"but '{ref}' is {pretty(env[ref])}", node.line)
        subst = new

    # Hypothesis premises — each consumes two refs (assume_label, concl_label)
    # that name labels inside a closed sibling subproof.
    hyp_refs = node.refs[n_ord:]
    for j, (assume_pat, concl_pat) in enumerate(schema.hyp_premises, start=1):
        a, b = hyp_refs[2 * (j - 1)], hyp_refs[2 * (j - 1) + 1]
        sp_found = None
        for sp in subproofs:
            if sp.assume_label == a and b in sp.locals:
                sp_found = sp
                break
        if sp_found is None:
            raise ProofError(
                f"rule '{rule}': no closed subproof found that assumes '{a}' "
                f"and derives '{b}'", node.line)
        new = match(assume_pat, sp_found.assume_formula, schema.metavars, subst)
        if new is None:
            raise ProofError(
                f"rule '{rule}': subproof assumption '{a}' "
                f"({pretty(sp_found.assume_formula)}) does not match expected pattern",
                node.line)
        new = match(concl_pat, sp_found.locals[b], schema.metavars, new)
        if new is None:
            raise ProofError(
                f"rule '{rule}': subproof conclusion '{b}' "
                f"({pretty(sp_found.locals[b])}) does not match expected pattern",
                node.line)
        subst = new

    # Conclusion-directed matching: resolves any metavariable not yet bound
    # (e.g. conclusion-only free variables) and verifies structural consistency.
    final = match(schema.conclusion, node.formula, schema.metavars, subst)
    if final is None:
        raise ProofError(
            f"rule '{rule}': conclusion does not match claimed formula "
            f"{pretty(node.formula)}", node.line)
    return instantiate(schema.conclusion, final)
