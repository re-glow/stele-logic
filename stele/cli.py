import sys
import itertools
import argparse
from .parser import parse_theorem
from .kernel import check_theorem
from .errors import SteleError, ProofError, ParseError
from . import matrix as M


def cmd_check(path, logic):
    # Resolve the logic early; matrix logics bypass the proof parser entirely.
    if logic is not None:
        try:
            from .logic import get_logic
            resolved = get_logic(logic)
        except SteleError as e:
            print(f"X Error: {e}")
            return 1
        if resolved.semantics == "matrix":
            return _check_matrix(path, resolved)

    # Proof mode (existing behaviour — logic may be None, handled by check_theorem).
    text = open(path, encoding="utf-8").read()
    try:
        thm = parse_theorem(text)
    except ParseError as e:
        loc = f" (line {e.line})" if getattr(e, "line", None) else ""
        print(f"X Parse error{loc}: {e}")
        return 1
    try:
        lg, _ = check_theorem(thm, logic)
    except ProofError as e:
        loc = f" (line {e.line})" if getattr(e, "line", None) else ""
        print(f"X Proof failed: {thm.name}{loc}")
        print(f"  {e}")
        return 1
    except SteleError as e:
        print(f"X Error: {e}")
        return 1
    print(f"OK Proof verified: {thm.name}   [logic: {lg.name}]")
    return 0


def _check_matrix(path, logic):
    from .parser import parse_matrix_file
    from .matrix import evaluate, is_tautology, entails, variables
    from .ast import pretty

    text = open(path, encoding="utf-8").read()
    try:
        directives = parse_matrix_file(text)
    except ParseError as e:
        loc = f" (line {e.line})" if getattr(e, "line", None) else ""
        print(f"X Parse error{loc}: {e}")
        return 1

    from .matrix import negation_fixpoints
    m = logic.matrix
    for d in directives:
        if d.kind == "evaluate":
            vs = sorted(variables(d.formula))
            vals = set()
            for combo in itertools.product(m.values, repeat=len(vs)):
                val = dict(zip(vs, combo))
                vals.add(evaluate(d.formula, val, m))
            sorted_vals = sorted(vals, key=lambda v: m.rank[v])
            print(f"evaluate {pretty(d.formula)}  =>  {{{', '.join(sorted_vals)}}}")
        elif d.kind == "tautology":
            ok = is_tautology(d.formula, m)
            print(f"tautology? {pretty(d.formula)}  =>  {'yes' if ok else 'no'}")
        elif d.kind == "entails":
            prems = list(d.premises)
            ok, cx = entails(prems, d.formula, m)
            prem_str = ", ".join(pretty(p) for p in prems)
            conc_str = pretty(d.formula)
            label = (f"entails {prem_str} |- {conc_str}" if prems
                     else f"entails |- {conc_str}")
            if ok:
                print(f"{label}  =>  yes")
            else:
                cx_str = ", ".join(f"{k}={v}" for k, v in sorted(cx.items()))
                print(f"{label}  =>  no  (counterexample: {cx_str})")
        elif d.kind == "fixpoint":
            fps = negation_fixpoints(m)
            fps_str = ", ".join(fps) if fps else ""
            print(f"fixpoint not  =>  {{{fps_str}}}")
    return 0


def cmd_soundness(logic_name, matrix_name):
    from .logic import get_logic, LOGICS
    from .matrix import MATRICES, rule_soundness
    from .errors import SteleError

    try:
        logic = get_logic(logic_name)
    except SteleError as e:
        print(f"X Error: {e}")
        return 1

    if logic.semantics != "proof":
        print(f"X Error: '{logic_name}' is a matrix logic; "
              f"--logic must name a proof logic (e.g. classical_prop)")
        return 1

    if matrix_name not in MATRICES:
        print(f"X Error: unknown matrix '{matrix_name}'. "
              f"available: {', '.join(sorted(MATRICES))}")
        return 1

    m = MATRICES[matrix_name]
    print(f"soundness  [logic: {logic_name} | matrix: {matrix_name}]")
    for name, schema in sorted(logic.rules.items()):
        r = rule_soundness(schema, m)
        if r.status == "sound":
            print(f"  {name}: sound")
        elif r.status == "unsound":
            cx_str = ", ".join(f"{k}={v}" for k, v in sorted(r.counterexample.items()))
            print(f"  {name}: unsound  counterexample: {cx_str}")
        else:
            print(f"  {name}: skipped  ({r.reason})")
    return 0


def cmd_lattice(formula_str):
    from .parser import parse_formula
    from .ast import Op, pretty
    from .world import World, lattice_status
    from .errors import ParseError

    try:
        phi = parse_formula(formula_str)
    except ParseError as e:
        print(f"X Parse error: {e}")
        return 1

    neg = Op("not", (phi,))
    phi_s = pretty(phi)
    neg_s = pretty(neg)

    # CH-style default world family: base, positive extension, negative extension.
    labelled = [
        ("Gamma",             World("boolean", ())),
        (f"Gamma + {phi_s}",  World("boolean", (phi,))),
        (f"Gamma + {neg_s}",  World("boolean", (neg,))),
    ]
    worlds = [w for _, w in labelled]

    print(f"lattice  [formula: {phi_s} | matrix: boolean]")
    for (label, w), (_, s) in zip(labelled, lattice_status(phi, worlds)):
        axioms_s = "[" + ", ".join(pretty(a) for a in w.axioms) + "]"
        print(f"  {label:<26}  axioms: {axioms_s:<16}  =>  {s}")

    return 0


def cmd_graph(path, logic, dot_mode):
    from .proofgraph import (build_proof_graph, to_dot,
                              has_cycle, find_unused_assumptions, find_isolated_steps)

    text = open(path, encoding="utf-8").read()
    try:
        thm = parse_theorem(text)
    except ParseError as e:
        loc = f" (line {e.line})" if getattr(e, "line", None) else ""
        print(f"X Parse error{loc}: {e}")
        return 1

    logic_name = logic or thm.logic or "intuitionistic_prop"
    try:
        lg, _ = check_theorem(thm, logic_name)
    except (ProofError, SteleError) as e:
        print(f"X {type(e).__name__}: {e}")
        print("  Graph not built: file must pass verification first.")
        return 1

    g = build_proof_graph(thm)

    if dot_mode:
        print(to_dot(g))
        return 0

    print(f"graph  [{thm.name} | logic: {lg.name}]")
    print(f"  nodes ({len(g.nodes)}):")
    for label, node in g.nodes.items():
        rule_s = f"  [{node.rule}]" if node.rule else ""
        print(f"    {label}: {node.formula}{rule_s}")
    print(f"  edges ({len(g.edges)}):")
    for src, tgt in g.edges:
        print(f"    {src} -> {tgt}")

    # Diagnostics
    issues = []
    if has_cycle(g):
        issues.append("cycle detected in dependency graph")
    unused = find_unused_assumptions(g)
    if unused:
        issues.append(f"unused: {', '.join(sorted(unused))}")
    iso = find_isolated_steps(g)
    if iso:
        issues.append(f"isolated steps: {', '.join(sorted(iso))}")

    if issues:
        for msg in issues:
            print(f"  [WARN] {msg}")
    else:
        print("  diagnostics: OK")
    return 0


def cmd_diagnose(path, logic):
    from .diagnostics import diagnose_theorem
    from .errors import ParseError

    text = open(path, encoding="utf-8").read()
    try:
        thm = parse_theorem(text)
    except ParseError as e:
        loc = f" (line {e.line})" if getattr(e, "line", None) else ""
        print(f"X Parse error{loc}: {e}")
        return 1

    logic_name = logic or thm.logic or "intuitionistic_prop"
    diags = diagnose_theorem(thm, logic_name)

    if not diags:
        print(f"OK no diagnostics: {thm.name}")
        return 0

    for d in diags:
        line_s = f"line={d.line}" if d.line is not None else "line=?"
        print(f"{d.severity.upper()} {d.code} {line_s}: {d.message}")

    has_error = any(d.severity == "error" for d in diags)
    return 1 if has_error else 0


def cmd_demos():
    M.run_demos()
    return 0


def cmd_elaborate(path, logic):
    """Elaborate a proof script into a proof term and typecheck it."""
    from .elaborate import crosscheck_theorem, pretty_term, ElaborationError
    from .ast import pretty as pretty_formula
    from .errors import ParseError

    text = open(path, encoding="utf-8").read()
    try:
        thm = parse_theorem(text)
    except ParseError as e:
        loc = f" (line {e.line})" if getattr(e, "line", None) else ""
        print(f"X Parse error{loc}: {e}")
        return 1

    logic_name = logic or thm.logic or "intuitionistic_prop"
    result = crosscheck_theorem(thm, logic_name)

    print(f"elaborate  [{thm.name} | logic: {logic_name}]")

    tag = "OK" if result.script_ok else "X"
    print(f"  script check:  {tag}")
    if result.script_error:
        print(f"    {result.script_error}")

    if result.script_ok:
        tag = "OK" if result.elaboration_ok else "X"
        print(f"  elaboration:   {tag}")
        if result.elab_error:
            print(f"    {result.elab_error}")

    if result.elaboration_ok:
        tag = "OK" if result.typecheck_ok else "X"
        print(f"  term typecheck:{tag}")
        if result.type_error:
            print(f"    {result.type_error}")
        if result.term is not None:
            print(f"  proof term:    {pretty_term(result.term)}")

    return 0 if result.ok else 1


def _parse_context_str(context_str):
    """Parse a semicolon-separated context string into a typing context dict.

    Format: ``"name: formula; name2: formula2"``
    Returns an empty dict for None or empty string.
    Raises ParseError on malformed entries.
    """
    from .parser import parse_formula
    from .errors import ParseError
    if not context_str:
        return {}
    ctx = {}
    for entry in context_str.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            raise ParseError(
                f"context entry {entry!r} must have the form 'name: formula'"
            )
        name, _, formula_str = entry.partition(":")
        name = name.strip()
        if not name:
            raise ParseError("context entry has empty variable name")
        ctx[name] = parse_formula(formula_str.strip())
    return ctx


def cmd_term_check(term_str, type_str, infer_mode, context_str=None):
    """Parse and typecheck (or infer the type of) a surface proof term."""
    from .core.term_parser import parse_term, TermParseError
    from .core.typing import infer as term_infer, check as term_check, TypingError
    from .ast import pretty as pretty_formula
    from .errors import ParseError
    from .parser import parse_formula

    # Parse the term
    try:
        term = parse_term(term_str)
    except TermParseError as e:
        print(f"X Term parse error: {e}")
        return 1

    # Build typing context from --context flag
    try:
        ctx = _parse_context_str(context_str)
    except ParseError as e:
        print(f"X Context parse error: {e}")
        return 1

    if infer_mode:
        try:
            ty = term_infer(ctx, term)
            print(f"OK inferred type: {pretty_formula(ty)}")
            return 0
        except TypingError as e:
            print(f"X Type error: {e}")
            return 1

    if not type_str:
        print("X --type is required (or use --infer)")
        return 1

    try:
        expected = parse_formula(type_str)
    except ParseError as e:
        print(f"X Formula parse error: {e}")
        return 1

    try:
        term_check(ctx, term, expected)
        print(f"OK term checks as {pretty_formula(expected)}")
        return 0
    except TypingError as e:
        print(f"X Type error: {e}")
        return 1


def cmd_term_normalize(term_str):
    """Normalize a proof term to its beta-normal form."""
    from .core.term_parser import parse_term, TermParseError
    from .core.reduce import normalize, is_normal, ReductionError
    from .elaborate import pretty_term

    try:
        term = parse_term(term_str)
    except TermParseError as e:
        print(f"X Term parse error: {e}")
        return 1

    try:
        normal = normalize(term)
        print(f"OK {pretty_term(normal)}")
        return 0
    except ReductionError as e:
        print(f"X Reduction error: {e}")
        return 1


def cmd_kripke(formula_str, max_worlds):
    """Search for a finite Kripke countermodel for a propositional formula."""
    from .parser import parse_formula
    from .ast import pretty
    from .kripke import find_countermodel, forces, pretty_model
    from .errors import ParseError

    try:
        formula = parse_formula(formula_str)
    except ParseError as e:
        print(f"X Parse error: {e}")
        return 1

    print(f"kripke  formula: {pretty(formula)}")
    cm = find_countermodel(formula, max_worlds=max_worlds)

    if cm is None:
        print(f"  result:  no countermodel found within {max_worlds} world(s)")
        print(f"  note:    this does NOT prove intuitionistic validity")
        print(f"           (bounded search, not completeness)")
        return 0

    print(f"  result:  countermodel found (not intuitionistically valid)")
    print(f"  failing world: {cm.world}")
    lines = pretty_model(cm.model).splitlines()
    for line in lines:
        print(f"  {line}")
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(prog="stele")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="check a .stele proof or matrix file")
    c.add_argument("file")
    c.add_argument("--logic", default=None,
                   help="object logic: classical_prop | intuitionistic_prop "
                        "(proof mode) or K3 | LP | boolean (matrix mode)")

    s = sub.add_parser("soundness",
                       help="report whether proof rules preserve designation in a matrix")
    s.add_argument("--logic", required=True,
                   help="proof logic whose rules to check (e.g. classical_prop)")
    s.add_argument("--matrix", required=True,
                   help="matrix semantics to check against (K3 | LP | boolean)")

    lt = sub.add_parser("lattice",
                        help="show formula status across the CH-style world family")
    lt.add_argument("formula",
                    help="formula to evaluate (quote multi-word formulas: 'P or Q')")

    gr = sub.add_parser("graph",
                        help="build and analyse the proof dependency graph of a .stele file")
    gr.add_argument("file")
    gr.add_argument("--logic", default=None,
                    help="proof logic to verify against before building the graph")
    gr.add_argument("--dot", action="store_true",
                    help="output DOT text instead of the human-readable summary")

    dg = sub.add_parser(
        "diagnose",
        help="collect structural diagnostics without stopping at first error",
    )
    dg.add_argument("file")
    dg.add_argument(
        "--logic", default=None,
        help="proof logic to use for schema-aware ref checking "
             "(default: theorem's 'using' clause or intuitionistic_prop)",
    )

    sub.add_parser("demos", help="run the many-valued semantics demonstrations")

    el = sub.add_parser(
        "elaborate",
        help="elaborate a proof script into a proof term and typecheck it",
    )
    el.add_argument("file")
    el.add_argument(
        "--logic", default=None,
        help="proof logic to verify against (default: theorem's 'using' clause "
             "or intuitionistic_prop)",
    )

    tc = sub.add_parser(
        "term-check",
        help="parse and typecheck (or infer the type of) a proof term",
    )
    tc.add_argument("--term", required=True,
                    help="proof term in surface syntax, e.g. 'fun x: A => x'")
    tc.add_argument("--type", dest="type_str", default=None,
                    help="expected formula type, e.g. 'A -> A'")
    tc.add_argument("--infer", dest="infer_mode", action="store_true",
                    help="infer the term's type instead of checking against --type")
    tc.add_argument("--context", dest="context_str", default=None,
                    help="typing context, e.g. 'f: forall x. P(x); h: P(a)'")

    tn = sub.add_parser(
        "term-normalize",
        help="beta-normalize a proof term to its normal form",
    )
    tn.add_argument("--term", required=True,
                    help="proof term in surface syntax, e.g. 'fst(pair(x, y))'")

    kr = sub.add_parser(
        "kripke",
        help="search for a finite Kripke countermodel for a propositional formula",
    )
    kr.add_argument(
        "formula",
        help="propositional formula to test, e.g. 'P or not P'",
    )
    kr.add_argument(
        "--max-worlds", dest="max_worlds", type=int, default=4,
        help="maximum number of worlds to search (default: 4)",
    )

    args = ap.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args.file, args.logic)
    if args.cmd == "soundness":
        return cmd_soundness(args.logic, args.matrix)
    if args.cmd == "lattice":
        return cmd_lattice(args.formula)
    if args.cmd == "graph":
        return cmd_graph(args.file, args.logic, args.dot)
    if args.cmd == "diagnose":
        return cmd_diagnose(args.file, args.logic)
    if args.cmd == "demos":
        return cmd_demos()
    if args.cmd == "elaborate":
        return cmd_elaborate(args.file, args.logic)
    if args.cmd == "term-check":
        return cmd_term_check(args.term, args.type_str, args.infer_mode,
                              getattr(args, "context_str", None))
    if args.cmd == "term-normalize":
        return cmd_term_normalize(args.term)
    if args.cmd == "kripke":
        return cmd_kripke(args.formula, args.max_worlds)
    return 2


if __name__ == "__main__":
    sys.exit(main())
