# Stele Release Checklist

Use this checklist before creating and pushing a release tag.
**Do not create the tag until all "Before tag" items are complete.**

---

## Before tag

### 1. Working tree

```bash
git checkout main
git pull origin main
git status          # must be clean
```

### 2. Tests

```bash
python -m pytest -q
# all tests must pass; 4 skipped (Hypothesis property tests) is expected
```

Optional extended tests (requires `pip install -r requirements-dev.txt`):

```bash
python -m pytest tests/test_proof_term_properties.py -v
```

### 3. Build artifacts (fast, no Pyodide download)

```bash
# Pyodide site (static HTML/JS, no browser)
python tools/build_pyodide_site.py --output-dir _site
# verify _site/index.html exists and is not empty

# Single-file HTML (no internet; builds from local source)
python tools/build_single_html.py --output dist/stele.html
# verify dist/stele.html exists, contains loadPyodide and __steleZipB64
```

### 4. Packaging smoke (optional — requires PyInstaller)

```bash
pip install -r packaging/requirements-packaging.txt
python packaging/build_app.py --onefile --clean
python packaging/smoke_app.py
# verify dist/SteleStudio (or .exe) exists and smoke test passes
```

### 5. Site check

- Confirm the GitHub Pages URL loads the Studio landing page.
  URL: `https://re-glow.github.io/stele-logic/`
- Confirm the 5-minute tutorial section is visible.
- Confirm the example gallery renders 15 cards.
- Confirm the Studio loads (Pyodide first-load may take ~10 s).

### 6. Documentation consistency

- [ ] CHANGELOG.md has a `[v1.0.0]` entry.
- [ ] README.md capability matrix matches the actual implementation.
- [ ] `stele/__version__.py` is set to the release version.
- [ ] No generated files tracked in git:
  ```bash
  git status  # dist/, _site/, build/, __pycache__/ must not appear
  ```

### 7. Claim audit

- [ ] No "complete theorem prover" claims — Stele is a proof checker.
- [ ] No "formalized metatheory" claims — metatheory uses proof sketches + regression/property tests.
- [ ] No "fully offline" claim for single-file HTML v1 — Pyodide loads from CDN.
- [ ] No ML corpus metrics claimed if stele_ml results are not current.
- [ ] No Lean integration claimed as core — stele_lean is optional and experimental.

### 8. No accidental commits

```bash
git log --oneline -10     # confirm no stray commits
git diff origin/main HEAD  # confirm only intended changes
```

---

## Tag and release

Once all "Before tag" items are checked:

```bash
# Create annotated tag
git tag -a v1.0.0 -m "Stele v1.0.0"

# Push tag to trigger the release workflow
git push origin v1.0.0
```

### After push

1. Watch `.github/workflows/release.yml` run on GitHub Actions.
2. Confirm all three OS builds (Windows, macOS, Linux) upload `SteleStudio` artifacts.
3. Confirm `stele.html` artifact is uploaded.
4. Create a GitHub Release from the tag and attach the artifacts.
5. Confirm GitHub Pages is still live at the expected URL.

---

## Known limitations to include in release notes

- Propositional logic only — no first-order quantifiers at the proof-script level.
- Relativity is at the rule-availability level; semantic non-derivability requires matrix/Kripke semantics.
- Single-file `stele.html` requires internet (Pyodide CDN, ~8 MB, cached after first load).
- Proof-term core supports intuitionistic fragment only; classical rules are excluded by design.
- de Bruijn layer covers proof-variable binders; object-variable binders in the FOL fragment remain name-based.
- ML baseline (`stele_ml/`) is optional and isolated — not part of the trusted checking path.
- Lean bridge (`stele_lean/`) is optional, experimental, and limited to the propositional fragment.
