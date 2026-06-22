"""Entry point for `python -m stele` — launches Stele Studio locally."""
import argparse
import sys


def build_parser():
    ap = argparse.ArgumentParser(
        prog="python -m stele",
        description=(
            "Stele Studio — formal verification workspace for mathematical reasoning.\n\n"
            "Starts a local web server and opens Stele Studio in the default browser.\n"
            "The Studio provides tabs for: proof verification, diagnostics, dependency\n"
            "graph, benchmark metrics, and the pluralism/matrix playground."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "CLI commands are still available via:\n"
            "  python -m stele.cli check examples/dne.stele --logic classical_prop\n"
            "  python -m stele.cli soundness --logic classical_prop --matrix K3\n"
            "  python -m stele.cli lattice 'P or Q'\n"
            "  python -m stele.cli demos"
        ),
    )
    ap.add_argument(
        "--port", type=int, default=8000,
        help="local port to listen on (default: 8000)",
    )
    ap.add_argument(
        "--no-browser", dest="no_browser", action="store_true",
        help="start the server without opening a browser window",
    )
    return ap


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    ap = build_parser()
    args = ap.parse_args(argv)
    from .web import main as web_main
    web_main(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
