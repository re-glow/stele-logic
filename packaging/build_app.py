"""Build Stele Studio standalone executable with PyInstaller.

Run from the project root:

    python packaging/build_app.py                # one-file (default)
    python packaging/build_app.py --onefile      # same
    python packaging/build_app.py --onedir       # one-directory bundle
    python packaging/build_app.py --clean        # remove dist/ and build/ first
    python packaging/build_app.py --name Stele   # custom output name

Output lands in dist/:
    dist/SteleStudio        (or dist/SteleStudio.exe on Windows)
    dist/SteleStudio/       (if --onedir)

Prerequisites:
    pip install -r packaging/requirements-packaging.txt
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ENTRY = ROOT / 'stele' / '__main__.py'
WEBAPP_SRC = ROOT / 'stele' / 'webapp'
DIST = ROOT / 'dist'
BUILD = ROOT / 'build'


def webapp_data_arg():
    """Return the --add-data argument for the webapp directory.

    PyInstaller uses OS path separator in --add-data values:
      Unix: src:dest
      Windows: src;dest
    """
    sep = ';' if sys.platform == 'win32' else ':'
    return f"{WEBAPP_SRC}{sep}stele/webapp"


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='python packaging/build_app.py',
        description='Build Stele Studio standalone executable.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        '--onefile', dest='mode', action='store_const', const='onefile',
        default='onefile', help='single-file executable (default)',
    )
    mode.add_argument(
        '--onedir', dest='mode', action='store_const', const='onedir',
        help='one-directory bundle',
    )
    ap.add_argument(
        '--name', default='SteleStudio',
        help='output executable name (default: SteleStudio)',
    )
    ap.add_argument(
        '--clean', action='store_true',
        help='remove dist/ and build/ directories before building',
    )
    ap.add_argument(
        '--spec', action='store_true',
        help='use packaging/SteleStudio.spec instead of CLI flags (onefile only)',
    )
    args = ap.parse_args(argv)

    if args.clean:
        for d in (DIST, BUILD):
            if d.exists():
                print(f'Removing {d}')
                shutil.rmtree(d)

    if args.spec and args.mode == 'onefile':
        # Spec-file path: clean and reproducible, useful for CI.
        spec_path = HERE / 'SteleStudio.spec'
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            str(spec_path),
            f'--distpath={DIST}',
            f'--workpath={BUILD}',
            '--noconfirm',
        ]
    else:
        # CLI-flag path: flexible, works for both onefile and onedir.
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            f'--{args.mode}',
            f'--name={args.name}',
            f'--add-data={webapp_data_arg()}',
            '--console',
            f'--distpath={DIST}',
            f'--workpath={BUILD}',
            '--noconfirm',
            str(ENTRY),
        ]

    print('Command:', ' '.join(str(c) for c in cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print('Build failed.', file=sys.stderr)
        sys.exit(result.returncode)

    # Report the output location.
    suffix = '.exe' if sys.platform == 'win32' else ''
    out_file = DIST / f'{args.name}{suffix}'
    out_dir  = DIST / args.name
    if out_file.exists():
        size_mb = out_file.stat().st_size / (1024 * 1024)
        print(f'\nBuild successful: {out_file}  ({size_mb:.1f} MB)')
    elif out_dir.exists():
        print(f'\nBuild successful (onedir): {out_dir}')
    else:
        print('\nBuild complete (output location unclear — check dist/).')


if __name__ == '__main__':
    main()
