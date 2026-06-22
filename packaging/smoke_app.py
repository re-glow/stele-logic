"""Smoke test for the Stele Studio built executable.

Usage:
    python packaging/smoke_app.py                       # auto-find in dist/
    python packaging/smoke_app.py dist/SteleStudio
    python packaging/smoke_app.py dist/SteleStudio.exe

Checks:
    1. The executable exists.
    2. --help returns exit code 0 and mentions Stele.
    3. Does NOT start a blocking server (no long-running test).

For a full launch test, run manually:
    ./dist/SteleStudio --no-browser --port 8099
and check that it prints a URL.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'


def find_exe(explicit=None):
    if explicit:
        return Path(explicit)
    for candidate in ('SteleStudio.exe', 'SteleStudio'):
        p = DIST / candidate
        if p.exists():
            return p
    # onedir layout
    p = DIST / 'SteleStudio' / ('SteleStudio.exe' if sys.platform == 'win32' else 'SteleStudio')
    if p.exists():
        return p
    return None


def smoke(exe):
    exe = Path(exe)
    print(f'Smoke test: {exe}')

    # Check 1: exists
    if not exe.exists():
        print(f'FAIL: executable not found: {exe}')
        sys.exit(1)
    print('  [1/2] executable found')

    # Check 2: --help
    result = subprocess.run(
        [str(exe), '--help'],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f'FAIL: --help exited {result.returncode}')
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    if 'Stele' not in result.stdout and 'Stele' not in result.stderr:
        print('FAIL: --help output does not mention "Stele"')
        print(result.stdout)
        sys.exit(1)
    print('  [2/2] --help OK')

    print('Smoke test passed.')


def main():
    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    exe = find_exe(explicit)
    if exe is None:
        print('No executable found. Build first with:')
        print('  python packaging/build_app.py --onefile')
        sys.exit(1)
    smoke(exe)


if __name__ == '__main__':
    main()
