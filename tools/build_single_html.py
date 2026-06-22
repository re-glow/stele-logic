#!/usr/bin/env python3
"""Build Stele single-file HTML distribution (stele.html).

Usage:
    python tools/build_single_html.py [--output FILE] [--pyodide-local PATH]

Produces a self-contained single HTML file at dist/stele.html (default).
The file embeds the Stele Python core as a base64-encoded zip and inlines
CSS and JS glue. It loads the Pyodide runtime from a pinned CDN URL.

Distribution modes produced by separate scripts:
  Site (GitHub Pages):   python tools/build_pyodide_site.py
  Single-file HTML:      python tools/build_single_html.py   ← this script
  Standalone executable: python packaging/build_app.py

Serving:
    Opening dist/stele.html directly via file:// may fail in some browsers
    due to CORS restrictions on fetch(). Use a local HTTP server:
        python -m http.server --directory dist 8000
        # open http://localhost:8000/stele.html

Offline / no-CDN mode (v1 placeholder):
    --pyodide-local PATH
        Replace CDN URL with a local path to Pyodide assets.
        This script does NOT download Pyodide — provide the assets yourself.
        See: https://pyodide.org/en/stable/usage/downloading-and-deploying.html
        The resulting stele.html references the local path; it will only work
        if that path is accessible from the browser context you use to open it.
"""

import argparse
import base64
import io
import json
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT     = Path(__file__).resolve().parent.parent
STELE_PKG     = REPO_ROOT / "stele"
EXAMPLES_DIR  = REPO_ROOT / "examples"
TEMPLATE_PATH = REPO_ROOT / "site" / "single_file_template.html"
CSS_PATH      = REPO_ROOT / "site" / "assets" / "stele_site.css"
JS_PATH       = REPO_ROOT / "site" / "assets" / "stele-inline.js"

# ── Pyodide version ──────────────────────────────────────────────────────────

PYODIDE_VERSION = "0.26.4"
PYODIDE_CDN_INDEX = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/pyodide.js"
PYODIDE_CDN_BASE  = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"

# ── Exclusion config ──────────────────────────────────────────────────────────

EXCLUDE_MODULES = frozenset({"stele_ml", "stele_lean", "eval"})
EXCLUDE_EXAMPLE_PATTERNS = [
    re.compile(r"world_.*\.py$"),
    re.compile(r"__pycache__"),
]

# ── Source collection (same logic as build_pyodide_site.py) ──────────────────

def collect_stele_files() -> list[tuple[Path, str]]:
    """Return [(abs_path, arcname)] for Stele core source files."""
    entries: list[tuple[Path, str]] = []

    def _skip(name: str) -> bool:
        return Path(name).stem in EXCLUDE_MODULES or name.startswith("__pycache__")

    def _walk(pkg_dir: Path, prefix: str) -> None:
        for item in sorted(pkg_dir.iterdir()):
            if item.name.startswith("__pycache__") or item.suffix == ".pyc":
                continue
            if item.is_dir():
                if not any(item.name.startswith(ex)
                           for ex in [".venv", "__pycache__"]):
                    _walk(item, f"{prefix}/{item.name}")
            elif item.suffix == ".py" and not _skip(item.name):
                entries.append((item, f"{prefix}/{item.name}"))

    _walk(STELE_PKG, "stele")
    return entries


def collect_example_files() -> list[tuple[Path, str]]:
    """Return [(abs_path, arcname)] for bundled example .stele files."""
    if not EXAMPLES_DIR.is_dir():
        return []
    entries: list[tuple[Path, str]] = []
    for item in sorted(EXAMPLES_DIR.iterdir()):
        if not item.is_file():
            continue
        if any(p.search(item.name) for p in EXCLUDE_EXAMPLE_PATTERNS):
            continue
        if item.suffix == ".stele":
            entries.append((item, f"examples/{item.name}"))
    return entries


# ── Zip builder ───────────────────────────────────────────────────────────────

def build_zip_bytes(
    stele_files: list[tuple[Path, str]],
    example_files: list[tuple[Path, str]],
) -> bytes:
    """Build in-memory zip and return raw bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for abs_path, arcname in stele_files + example_files:
            zf.write(abs_path, arcname)
    return buf.getvalue()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stele_version() -> str:
    try:
        init = (STELE_PKG / "__init__.py").read_text(encoding="utf-8")
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "dev"


def _check_excluded(arcnames: list[str]) -> None:
    for arc in arcnames:
        for ex in EXCLUDE_MODULES:
            if arc.startswith(ex + "/") or ("/" + ex + "/") in arc:
                raise RuntimeError(
                    f"BUG: excluded module '{ex}' found in bundle: {arc}"
                )


# ── Core builder ──────────────────────────────────────────────────────────────

def build_stele_html(
    output_path: Path,
    pyodide_local: str | None = None,
) -> tuple[Path, dict]:
    """Build and write dist/stele.html. Returns (output_path, manifest)."""

    # 1. Validate template/source files exist
    for path, desc in [
        (TEMPLATE_PATH, "HTML template (site/single_file_template.html)"),
        (CSS_PATH,      "CSS (site/assets/stele_site.css)"),
        (JS_PATH,       "JS glue (site/assets/stele-inline.js)"),
    ]:
        if not path.exists():
            raise SystemExit(f"ERROR: {desc} not found at {path}")

    # 2. Collect source files
    stele_files = collect_stele_files()
    example_files = collect_example_files()
    all_files = stele_files + example_files
    arcnames = sorted(a for _, a in all_files)
    _check_excluded(arcnames)
    print(f"  source files : {len(stele_files)} Python")
    print(f"  example files: {len(example_files)} .stele")

    # 3. Build and encode zip
    zip_bytes = build_zip_bytes(stele_files, example_files)
    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")
    print(f"  zip          : {len(zip_bytes) / 1024:.1f} KB  "
          f"→ base64: {len(zip_b64) / 1024:.1f} KB")

    # 4. Read source files
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")
    js  = JS_PATH.read_text(encoding="utf-8")

    # 5. Determine CDN / local URL
    if pyodide_local:
        from urllib.request import pathname2url
        import os
        local_path = Path(pyodide_local).resolve()
        # Build a file:// URL for the local Pyodide directory
        cdn_base = "file://" + pathname2url(str(local_path)) + "/"
        cdn_index = cdn_base + "pyodide.js"
        print(f"  Pyodide      : local at {local_path}")
    else:
        cdn_base  = PYODIDE_CDN_BASE
        cdn_index = PYODIDE_CDN_INDEX
        print(f"  Pyodide      : {cdn_base} (CDN)")

    # 6. Patch JS glue with correct CDN URLs
    js_patched = js.replace(PYODIDE_CDN_INDEX, cdn_index)
    js_patched = js_patched.replace(PYODIDE_CDN_BASE, cdn_base)

    # 7. Substitute template placeholders
    version = _stele_version()
    build_date = date.today().isoformat()

    html = template
    html = html.replace("[[STELE_VERSION]]",   version)
    html = html.replace("[[BUILD_DATE]]",       build_date)
    html = html.replace("[[PYODIDE_VERSION]]",  PYODIDE_VERSION)
    html = html.replace("[[PYODIDE_CDN]]",      cdn_base)

    html = html.replace(
        "<!-- STELE:CSS -->",
        f"<style>\n{css}\n</style>",
    )
    html = html.replace(
        "<!-- STELE:ZIP_B64 -->",
        f'<script>\nwindow.__steleZipB64 = "{zip_b64}";\n</script>',
    )
    html = html.replace(
        "<!-- STELE:JS_GLUE -->",
        f"<script>\n{js_patched}\n</script>",
    )

    # Sanity: no placeholder tokens should remain
    for token in ("[[STELE_VERSION]]", "[[BUILD_DATE]]", "[[PYODIDE_VERSION]]",
                  "<!-- STELE:CSS -->", "<!-- STELE:ZIP_B64 -->", "<!-- STELE:JS_GLUE -->"):
        if token in html:
            raise RuntimeError(f"BUG: placeholder not substituted: {token!r}")

    # 8. Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    print(f"  output       : {output_path}  ({size_kb:.1f} KB)")

    # 9. Build manifest
    manifest = {
        "generator": "tools/build_single_html.py",
        "build_date": build_date,
        "stele_version": version,
        "pyodide_version": PYODIDE_VERSION,
        "pyodide_cdn": cdn_base,
        "source_files": arcnames,
        "excluded": sorted(EXCLUDE_MODULES),
        "zip_bytes": len(zip_bytes),
        "output_bytes": output_path.stat().st_size,
    }
    manifest_path = output_path.parent / "stele_html_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  manifest     : {manifest_path}")

    return output_path, manifest


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--output", default=str(REPO_ROOT / "dist" / "stele.html"),
        metavar="FILE",
        help="Output path for the generated HTML file (default: dist/stele.html)",
    )
    ap.add_argument(
        "--pyodide-local", default=None, metavar="PATH",
        help=(
            "[v1 placeholder] Local Pyodide assets directory. "
            "Replaces CDN URL. Assets are NOT downloaded — provide them yourself. "
            "Resulting file may only work if that local path is accessible. "
            "See: https://pyodide.org/en/stable/usage/downloading-and-deploying.html"
        ),
    )
    args = ap.parse_args()

    output_path = Path(args.output).resolve()
    print(f"Building stele.html → {output_path}")
    print()

    build_stele_html(output_path, pyodide_local=args.pyodide_local)

    print()
    print("Done.")
    print()
    print("To open:")
    print(f"  double-click {output_path}")
    print("  or serve with:")
    print(f"  python -m http.server --directory {output_path.parent} 8000")
    print("  # open http://localhost:8000/stele.html")
    print()
    if not args.pyodide_local:
        print("Note: Pyodide (~8 MB) is loaded from CDN on first use.")
        print("      For offline use, see --pyodide-local (requires manual Pyodide setup).")
    print()
    print("Offline bundle mode (full self-contained, no CDN) is out of scope for v1.")
    print("See: https://pyodide.org/en/stable/usage/downloading-and-deploying.html")


if __name__ == "__main__":
    main()
