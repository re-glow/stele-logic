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


def cmd_demos():
    M.run_demos()
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

    sub.add_parser("demos", help="run the many-valued semantics demonstrations")

    args = ap.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args.file, args.logic)
    if args.cmd == "soundness":
        return cmd_soundness(args.logic, args.matrix)
    if args.cmd == "lattice":
        return cmd_lattice(args.formula)
    if args.cmd == "demos":
        return cmd_demos()
    return 2


if __name__ == "__main__":
    sys.exit(main())
