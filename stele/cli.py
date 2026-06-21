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
    return 0


def cmd_demos():
    M.run_demos()
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(prog="stele")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a .stele proof file")
    c.add_argument("file")
    c.add_argument("--logic", default=None,
                   help="object logic: classical_prop | intuitionistic_prop "
                        "(proof mode) or K3 | LP | boolean (matrix mode)")
    sub.add_parser("demos", help="run the many-valued semantics demonstrations")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args.file, args.logic)
    if args.cmd == "demos":
        return cmd_demos()
    return 2


if __name__ == "__main__":
    sys.exit(main())
