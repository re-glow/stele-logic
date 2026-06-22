#!/usr/bin/env python3
"""Smoke test for the built Pyodide static site.

Runs the build then checks that the expected output files exist,
the manifest is valid, Stele source files are included, and
excluded modules are absent.

Usage:
    python tools/smoke_pyodide_site.py [--output-dir OUTDIR]

Exits 0 on success, 1 on failure.
Does NOT require Pyodide, a browser, or internet access.
"""

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_SITE_FILES = [
    "index.html",
    "assets/stele-pyodide.js",
    "assets/stele_site.css",
    "stele_source.zip",
    "stele_manifest.json",
]

REQUIRED_IN_ZIP = [
    "stele/__init__.py",
    "stele/kernel.py",
    "stele/parser.py",
    "stele/browser.py",
    "stele/core/__init__.py",
]

MUST_NOT_BE_IN_ZIP = [
    "stele_ml/",
    "stele_lean/",
    "tests/",
]


def check(condition: bool, msg: str) -> None:
    if condition:
        print(f"  [ok] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "dist" / "site"))
    parser.add_argument("--skip-build", action="store_true",
                        help="Skip running the build script (use existing output)")
    args = parser.parse_args()
    out_dir = Path(args.output_dir).resolve()

    # 1. Run build
    if not args.skip_build:
        print("Running build script…")
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "build_pyodide_site.py"),
             "--output-dir", str(out_dir)],
            capture_output=False,
        )
        if result.returncode != 0:
            print("Build script failed.")
            sys.exit(1)
        print()

    print(f"Checking output in: {out_dir}")
    print()

    # 2. Check required files exist
    for rel in REQUIRED_SITE_FILES:
        p = out_dir / rel
        check(p.exists(), f"exists: {rel}")

    print()

    # 3. Check manifest is valid JSON
    manifest_path = out_dir / "stele_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        check(isinstance(manifest["files"], list), "manifest.files is a list")
        check(len(manifest["files"]) > 5, f"manifest has >{5} files ({len(manifest['files'])} found)")
    except Exception as e:
        print(f"  [FAIL] manifest JSON invalid: {e}")
        sys.exit(1)

    print()

    # 4. Check zip contents
    zip_path = out_dir / "stele_source.zip"
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())

    for req in REQUIRED_IN_ZIP:
        check(req in names, f"zip contains: {req}")

    print()

    for excl in MUST_NOT_BE_IN_ZIP:
        found = [n for n in names if n.startswith(excl)]
        check(not found, f"zip excludes: {excl}")

    print()

    # 5. Check index.html has no /api/ calls
    html = (out_dir / "index.html").read_text(encoding="utf-8")
    check("/api/" not in html, "index.html contains no /api/ calls")

    # 6. Check JS mentions loadPyodide
    js = (out_dir / "assets" / "stele-pyodide.js").read_text(encoding="utf-8")
    check("loadPyodide" in js, "stele-pyodide.js mentions loadPyodide")

    print()
    print("All smoke checks passed.")


if __name__ == "__main__":
    main()
