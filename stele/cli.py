import sys
import argparse
from .parser import parse_theorem
from .kernel import check_theorem
from .errors import SteleError, ProofError, ParseError
from . import matrix as M


def cmd_check(path, logic):
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
                   help="object logic (classical_prop | intuitionistic_prop)")
    sub.add_parser("demos", help="run the many-valued semantics demonstrations")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args.file, args.logic)
    if args.cmd == "demos":
        return cmd_demos()
    return 2


if __name__ == "__main__":
    sys.exit(main())
