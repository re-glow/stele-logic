# Stele Studio — Packaging

This directory contains scripts and configuration for building Stele Studio as a standalone executable with [PyInstaller](https://pyinstaller.org/).

## Quick build

```bash
# 1. Install packaging dependencies (separate from core dev deps)
pip install -r packaging/requirements-packaging.txt

# 2. Build one-file executable
python packaging/build_app.py --onefile

# Output: dist/SteleStudio   (or dist/SteleStudio.exe on Windows)
```

## Options

```
python packaging/build_app.py --onefile     # default: single executable
python packaging/build_app.py --onedir      # directory bundle (faster startup)
python packaging/build_app.py --clean       # remove dist/ and build/ first
python packaging/build_app.py --name Stele  # custom output name
python packaging/build_app.py --spec        # use SteleStudio.spec (onefile only)
```

## Using the spec file directly

```bash
pyinstaller packaging/SteleStudio.spec
```

The spec file (`SteleStudio.spec`) is committed and builds a one-file release executable. It includes the webapp assets and trims unused stdlib modules.

## Smoke test

After building, run a quick check:

```bash
python packaging/smoke_app.py
# or point at a specific path:
python packaging/smoke_app.py dist/SteleStudio
```

For a full manual test, launch the executable directly:

```bash
dist/SteleStudio --no-browser --port 8099
# Expect: prints URL, does not crash, opens if browser available
```

## What is included in the bundle

| Included | Not included |
|----------|-------------|
| `stele/` package (all modules) | `examples/` |
| `stele/webapp/index.html` | `bench/` reports |
| Python runtime | `tests/` |

Examples are not bundled by default (keeps binary small). The built-in sample proofs in the Studio UI are hardcoded in `index.html`.

## What is not yet supported

- **Code signing / notarization** — required for unsigned macOS Gatekeeper warnings. Future work.
- **Installer packages** (.msi / .pkg / .deb) — Future work.
- **Auto-update** — Future work.
- **Hosted web deployment** — Stele's trusted checker is Python-based. A hosted version would require backend hosting or a WASM port of the kernel. Future work.
- **Windows Store / macOS App Store** — Future work.

## CI / Release

Built automatically on tag pushes (`v*`) by `.github/workflows/release.yml`. The workflow builds on Windows, macOS, and Linux and uploads artifacts. See `.github/workflows/release.yml` for details.

## Core dependencies are unchanged

PyInstaller is listed only in `packaging/requirements-packaging.txt`. It is **not** added to any core requirements file. Normal development (`python -m pytest -q`) does not require PyInstaller.
