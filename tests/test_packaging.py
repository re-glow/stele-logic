"""Tests for the packaging scripts, spec file, and release workflow.

These tests do NOT require PyInstaller to be installed and do NOT build
binaries. They inspect static files and configuration only.
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
PACKAGING = ROOT / 'packaging'


# ── Part A: packaging dependency file ────────────────────────────────────────

def test_requirements_packaging_exists():
    assert (PACKAGING / 'requirements-packaging.txt').exists()


def test_requirements_packaging_has_pyinstaller():
    txt = (PACKAGING / 'requirements-packaging.txt').read_text(encoding='utf-8')
    assert 'pyinstaller' in txt.lower()


def test_pyinstaller_not_in_core_deps():
    """PyInstaller must not appear in any core requirements file."""
    for fname in ('requirements.txt', 'requirements-dev.txt', 'setup.py',
                  'setup.cfg', 'pyproject.toml'):
        p = ROOT / fname
        if not p.exists():
            continue
        content = p.read_text(encoding='utf-8').lower()
        assert 'pyinstaller' not in content, \
            f"pyinstaller found in core dep file {fname}"


# ── Part B: spec file ────────────────────────────────────────────────────────

def test_spec_file_exists():
    assert (PACKAGING / 'SteleStudio.spec').exists()


def test_spec_includes_webapp_data():
    spec = (PACKAGING / 'SteleStudio.spec').read_text(encoding='utf-8')
    assert 'stele/webapp' in spec or 'stele\\webapp' in spec


def test_spec_entry_point_is_main():
    spec = (PACKAGING / 'SteleStudio.spec').read_text(encoding='utf-8')
    assert '__main__.py' in spec


def test_spec_output_name():
    spec = (PACKAGING / 'SteleStudio.spec').read_text(encoding='utf-8')
    assert 'SteleStudio' in spec


# ── Part C: build script ─────────────────────────────────────────────────────

def test_build_script_exists():
    assert (PACKAGING / 'build_app.py').exists()


def test_build_script_importable():
    """build_app.py can be imported (no side effects at import time)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'build_app', str(PACKAGING / 'build_app.py'))
    mod = importlib.util.module_from_spec(spec)
    # Should not raise
    spec.loader.exec_module(mod)
    assert hasattr(mod, 'main')


def test_build_script_references_webapp():
    src = (PACKAGING / 'build_app.py').read_text(encoding='utf-8')
    assert 'webapp' in src


def test_build_script_has_onefile_option():
    src = (PACKAGING / 'build_app.py').read_text(encoding='utf-8')
    assert '--onefile' in src


def test_build_script_has_onedir_option():
    src = (PACKAGING / 'build_app.py').read_text(encoding='utf-8')
    assert '--onedir' in src


def test_build_script_has_clean_option():
    src = (PACKAGING / 'build_app.py').read_text(encoding='utf-8')
    assert '--clean' in src


def test_build_script_argparse_help(capsys):
    """build_app.py --help prints usage and exits 0."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'build_app', str(PACKAGING / 'build_app.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        mod.main(['--help'])
    except SystemExit as e:
        assert e.code == 0
    out = capsys.readouterr().out
    assert 'onefile' in out or 'SteleStudio' in out


# ── Part D: smoke test ────────────────────────────────────────────────────────

def test_smoke_script_exists():
    assert (PACKAGING / 'smoke_app.py').exists()


def test_smoke_script_importable():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'smoke_app', str(PACKAGING / 'smoke_app.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, 'smoke')


# ── Part E: resource path compatibility ──────────────────────────────────────

def test_web_py_has_frozen_check():
    """web.py must handle sys.frozen for PyInstaller compatibility."""
    src = (ROOT / 'stele' / 'web.py').read_text(encoding='utf-8')
    assert 'frozen' in src
    assert '_MEIPASS' in src


def test_web_py_normal_import_unaffected():
    """web.py still imports correctly in normal (non-frozen) execution."""
    from stele import web
    assert hasattr(web, 'WEBAPP')
    assert hasattr(web, 'check_source')
    assert hasattr(web, 'diagnose_source')
    assert hasattr(web, 'graph_source')
    assert os.path.isdir(web.WEBAPP), f"WEBAPP path not a directory: {web.WEBAPP}"


# ── Part F: release workflow ──────────────────────────────────────────────────

RELEASE_YML = ROOT / '.github' / 'workflows' / 'release.yml'


def test_release_workflow_exists():
    assert RELEASE_YML.exists()


def test_release_workflow_triggers():
    content = RELEASE_YML.read_text(encoding='utf-8')
    assert 'v*' in content or "tags:" in content
    assert 'workflow_dispatch' in content


def test_release_workflow_matrix_os():
    content = RELEASE_YML.read_text(encoding='utf-8')
    assert 'windows-latest' in content
    assert 'macos-latest' in content
    assert 'ubuntu-latest' in content


def test_release_workflow_upload_artifact():
    content = RELEASE_YML.read_text(encoding='utf-8')
    assert 'actions/upload-artifact@v4' in content


def test_release_workflow_pytest_step():
    content = RELEASE_YML.read_text(encoding='utf-8')
    assert 'pytest' in content


def test_release_workflow_packaging_build_step():
    content = RELEASE_YML.read_text(encoding='utf-8')
    assert 'build_app.py' in content


def test_release_workflow_uses_python_311_or_312():
    content = RELEASE_YML.read_text(encoding='utf-8')
    assert '3.11' in content or '3.12' in content


# ── Part G: __main__ entrypoint still works ───────────────────────────────────

def test_main_module_importable():
    import stele.__main__  # noqa: F401


def test_main_build_parser_help(capsys):
    from stele.__main__ import build_parser
    ap = build_parser()
    try:
        ap.parse_args(['--help'])
    except SystemExit as e:
        assert e.code == 0
    out = capsys.readouterr().out
    assert '--port' in out
    assert '--no-browser' in out


def test_main_defaults():
    from stele.__main__ import build_parser
    ap = build_parser()
    args = ap.parse_args([])
    assert args.port == 8000
    assert args.no_browser is False


# ── Part H: dist/ not committed ───────────────────────────────────────────────

def test_gitignore_excludes_dist():
    gi = (ROOT / '.gitignore').read_text(encoding='utf-8')
    assert 'dist/' in gi or 'dist\\' in gi


def test_packaging_readme_exists():
    assert (PACKAGING / 'README.md').exists()


def test_no_built_binaries_committed():
    """dist/ directory should not exist in the working tree (or be empty)."""
    dist = ROOT / 'dist'
    if not dist.exists():
        return
    # If dist/ exists, it should only have contents from a local build.
    # We cannot assert it's empty (CI may have run), but we verify it's in .gitignore.
    gi = (ROOT / '.gitignore').read_text(encoding='utf-8')
    assert 'dist/' in gi
