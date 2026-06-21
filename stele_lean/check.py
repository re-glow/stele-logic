"""Lean 4 invocation wrapper and CLI entry point.

Usage:
    python -m stele_lean.check <file.stele>
    python -m stele_lean.check --lean-file <file.lean>
    python -m stele_lean.check --export-only <file.stele>

If Lean is not installed, the command exits with a clear message rather than
raising an exception. Tests that require Lean must guard with
    pytest.mark.skipif(not lean_available(), reason="Lean not installed")

Architecture:
    stele/ must NOT import this module.
    Lean is discovered via shutil.which — no Python-level Lean dependency.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import pathlib


def lean_available() -> bool:
    """Return True if 'lean' is found on PATH."""
    return shutil.which("lean") is not None


def check_lean_file(path: str | pathlib.Path) -> "LeanCheckResult":
    """Run Lean on a .lean file and return a LeanCheckResult.

    If Lean is not installed, returns a result with available=False
    and an empty diagnostics list.
    """
    from .diagnostics import LeanCheckResult, parse_lean_output

    path = pathlib.Path(path)
    if not lean_available():
        return LeanCheckResult(
            available=False,
            returncode=None,
            stdout="",
            stderr="",
            diagnostics=[],
        )

    lean_exe = shutil.which("lean")
    proc = subprocess.run(
        [lean_exe, str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    combined = proc.stderr + proc.stdout
    diagnostics = parse_lean_output(combined)
    return LeanCheckResult(
        available=True,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        diagnostics=diagnostics,
    )


def check_stele_file(stele_path: str | pathlib.Path) -> "LeanCheckResult":
    """Export a Stele theorem to a Lean skeleton and check it.

    Parses the .stele file, exports the first theorem to a temporary .lean
    file, runs Lean, and returns the result.  The temporary file is cleaned
    up after Lean exits.
    """
    from .diagnostics import LeanCheckResult
    from .export import theorem_to_lean_skeleton, ExportError

    stele_path = pathlib.Path(stele_path)
    text = stele_path.read_text(encoding="utf-8")

    _add_stele_root_to_path()
    from stele.parser import parse_theorem  # noqa: E402

    try:
        thm = parse_theorem(text)
    except Exception as exc:
        from .diagnostics import LeanDiagnostic
        diag = LeanDiagnostic(
            code="LeanTypeError",
            message=f"Stele parse error: {exc}",
            file=str(stele_path),
            line=0,
            col=0,
            severity="error",
            raw=str(exc),
        )
        return LeanCheckResult(
            available=lean_available(),
            returncode=1,
            stdout="",
            stderr="",
            diagnostics=[diag],
        )

    try:
        lean_source = theorem_to_lean_skeleton(thm)
    except ExportError as exc:
        from .diagnostics import LeanDiagnostic
        diag = LeanDiagnostic(
            code="LeanTypeError",
            message=f"Export error: {exc}",
            file=str(stele_path),
            line=0,
            col=0,
            severity="error",
            raw=str(exc),
        )
        return LeanCheckResult(
            available=lean_available(),
            returncode=1,
            stdout="",
            stderr="",
            diagnostics=[diag],
        )

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".lean",
        prefix="stele_",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(lean_source)
        tmp_path = pathlib.Path(tmp.name)

    try:
        result = check_lean_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    return result


def export_stele_to_lean(stele_path: str | pathlib.Path) -> str:
    """Parse a .stele file and return the Lean 4 skeleton source as a string."""
    from .export import theorem_to_lean_skeleton

    stele_path = pathlib.Path(stele_path)
    text = stele_path.read_text(encoding="utf-8")

    _add_stele_root_to_path()
    from stele.parser import parse_theorem  # noqa: E402

    thm = parse_theorem(text)
    return theorem_to_lean_skeleton(thm)


def _add_stele_root_to_path() -> None:
    root = str(pathlib.Path(__file__).parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """CLI entry point: python -m stele_lean.check [options] [file]"""
    parser = argparse.ArgumentParser(
        prog="python -m stele_lean.check",
        description="Check a Stele theorem or Lean file using Lean 4.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        help=".stele or .lean file to check",
    )
    parser.add_argument(
        "--lean-file",
        metavar="FILE",
        help="Directly check a .lean file (skips Stele export)",
    )
    parser.add_argument(
        "--export-only",
        metavar="FILE",
        help="Export a .stele file to Lean 4 and print; do not run Lean",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress all output except errors",
    )
    args = parser.parse_args(argv)

    # --- export-only mode ---
    if args.export_only:
        try:
            lean_src = export_stele_to_lean(args.export_only)
            print(lean_src, end="")
            return 0
        except Exception as exc:
            print(f"Export error: {exc}", file=sys.stderr)
            return 1

    # --- determine target ---
    target_file = args.lean_file or args.file
    if not target_file:
        parser.error("Specify a .stele or .lean file, or use --lean-file / --export-only")

    if not lean_available():
        print(
            "Lean not found on PATH. Install Lean 4 to use the bridge.\n"
            "See: https://leanprover.github.io/lean4/doc/quickstart.html",
            file=sys.stderr,
        )
        return 2

    # --- run Lean ---
    target_path = pathlib.Path(target_file)
    if not target_path.exists():
        print(f"File not found: {target_file}", file=sys.stderr)
        return 1

    if args.lean_file or target_file.endswith(".lean"):
        result = check_lean_file(target_path)
    else:
        result = check_stele_file(target_path)

    if not args.quiet:
        print(f"Lean check: {target_file}")
        print(f"Return code: {result.returncode}")
        print(f"Summary: {result.summary()}")
        if result.diagnostics:
            print("\nDiagnostics:")
            for d in result.diagnostics:
                print(f"  [{d.severity.upper()}] {d.file}:{d.line}:{d.col} — {d.message}")

    return 0 if not result.has_errors else 1


if __name__ == "__main__":
    sys.exit(main())
