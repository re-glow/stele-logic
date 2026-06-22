#!/usr/bin/env python3
"""Build the static Pyodide browser site.

Usage:
    python tools/build_pyodide_site.py [--output-dir OUTDIR]

Produces a self-contained static site in the output directory (default:
dist/site) that can be served with any static HTTP server:

    python -m http.server --directory dist/site 8000

Opening dist/site/index.html directly via file:// may fail in some
browsers due to CORS restrictions on fetch(); use a local server instead.

What is built:
  dist/site/
    index.html            — copied from site/index.html
    assets/               — copied from site/assets/
    stele_source.zip      — Stele Python package + bundled examples (no ML/Lean)
    stele_manifest.json   — manifest of files included in the zip

Excluded from stele_source.zip:
  stele_ml/, stele_lean/, tests/, bench/, packaging/,
  __pycache__/, *.pyc, .venv*/, stele/eval.py (benchmark runner, heavy deps optional)
"""

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = REPO_ROOT / "site"
STELE_PKG = REPO_ROOT / "stele"
EXAMPLES_DIR = REPO_ROOT / "examples"

# Stele source files to include (relative to REPO_ROOT).
# We include the core package and its subpackage; exclude heavy/optional modules.

EXCLUDE_MODULES = frozenset({
    "stele_ml",
    "stele_lean",
    # eval.py is a benchmark runner that has optional heavy dependencies
    # and is not needed in the browser build.
    "eval",
})

# Top-level packages to exclude entirely
EXCLUDE_TOPLEVEL_DIRS = frozenset({
    "stele_ml",
    "stele_lean",
    "tests",
    "bench",
    "packaging",
})

# Example files to exclude from the bundle (matrix/world demos, not proof examples)
EXCLUDE_EXAMPLE_PATTERNS = [
    re.compile(r"world_.*\.py$"),
    re.compile(r"__pycache__"),
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def collect_stele_files() -> list[tuple[Path, str]]:
    """Return list of (abs_path, zip_arcname) for Stele source files."""
    entries: list[tuple[Path, str]] = []

    def _skip_module(name: str) -> bool:
        stem = Path(name).stem
        return stem in EXCLUDE_MODULES or name.startswith("__pycache__")

    def _add_py_dir(pkg_dir: Path, zip_prefix: str) -> None:
        for item in sorted(pkg_dir.iterdir()):
            if item.name.startswith("__pycache__"):
                continue
            if item.suffix == ".pyc":
                continue
            if item.is_dir():
                if not any(item.name.startswith(ex) for ex in [".venv", "__pycache__"]):
                    _add_py_dir(item, zip_prefix + "/" + item.name)
                continue
            if item.suffix == ".py":
                if _skip_module(item.name):
                    continue
                arcname = zip_prefix + "/" + item.name
                entries.append((item, arcname))

    _add_py_dir(STELE_PKG, "stele")
    return entries


def collect_example_files() -> list[tuple[Path, str]]:
    """Return list of (abs_path, zip_arcname) for bundled example .stele files."""
    if not EXAMPLES_DIR.is_dir():
        return []
    entries: list[tuple[Path, str]] = []
    for item in sorted(EXAMPLES_DIR.iterdir()):
        if not item.is_file():
            continue
        skip = any(pat.search(item.name) for pat in EXCLUDE_EXAMPLE_PATTERNS)
        if skip:
            continue
        if item.suffix == ".stele":
            entries.append((item, "examples/" + item.name))
    return entries


def build_zip(output_zip: Path, stele_files, example_files) -> list[str]:
    """Write the zip and return sorted list of arcnames included."""
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    arcnames: list[str] = []
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for abs_path, arcname in stele_files + example_files:
            zf.write(abs_path, arcname)
            arcnames.append(arcname)
    return sorted(arcnames)


def copy_static_site(out_dir: Path) -> None:
    """Copy site/ static files to the output directory."""
    if not SITE_SRC.is_dir():
        raise SystemExit(f"ERROR: site/ directory not found at {SITE_SRC}\n"
                         "Run this script from the repo root or ensure site/ exists.")

    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy index.html
    src_html = SITE_SRC / "index.html"
    if not src_html.exists():
        raise SystemExit(f"ERROR: {src_html} not found")
    shutil.copy2(src_html, out_dir / "index.html")

    # Copy assets/
    src_assets = SITE_SRC / "assets"
    dst_assets = out_dir / "assets"
    if dst_assets.exists():
        shutil.rmtree(dst_assets)
    if src_assets.is_dir():
        shutil.copytree(src_assets, dst_assets)


def write_manifest(out_dir: Path, arcnames: list[str], zip_name: str) -> None:
    manifest = {
        "generator": "tools/build_pyodide_site.py",
        "bundle": zip_name,
        "files": arcnames,
        "excluded": sorted(EXCLUDE_MODULES | EXCLUDE_TOPLEVEL_DIRS),
    }
    manifest_path = out_dir / "stele_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def check_excluded(arcnames: list[str]) -> None:
    """Assert that excluded modules are not in the bundle."""
    for arc in arcnames:
        for ex in EXCLUDE_MODULES | EXCLUDE_TOPLEVEL_DIRS:
            if arc.startswith(ex + "/") or ("/" + ex + "/") in arc:
                raise RuntimeError(
                    f"BUG: excluded module '{ex}' found in bundle: {arc}"
                )


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "dist" / "site"),
                        help="Output directory (default: dist/site)")
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve()

    print(f"Building Stele browser site → {out_dir}")
    print()

    # 1. Collect source files
    stele_files = collect_stele_files()
    example_files = collect_example_files()
    print(f"  stele source files : {len(stele_files)}")
    print(f"  example .stele files: {len(example_files)}")

    # 2. Copy static site files
    print("  Copying static site files…")
    copy_static_site(out_dir)

    # 3. Build zip
    zip_name = "stele_source.zip"
    zip_path = out_dir / zip_name
    print(f"  Building {zip_name}…")
    arcnames = build_zip(zip_path, stele_files, example_files)

    # 4. Sanity check
    check_excluded(arcnames)

    # 5. Manifest
    manifest_path = write_manifest(out_dir, arcnames, zip_name)

    print()
    print(f"  stele_source.zip   : {zip_path.stat().st_size / 1024:.1f} KB "
          f"({len(arcnames)} files)")
    print(f"  stele_manifest.json: {manifest_path}")
    print()
    print("Done. Serve with:")
    print(f"  python -m http.server --directory {out_dir} 8000")
    print("Then open: http://localhost:8000")
    print()
    print("Note: opening dist/site/index.html via file:// may fail in some")
    print("browsers (CORS on fetch). Use a local HTTP server instead.")


if __name__ == "__main__":
    main()
