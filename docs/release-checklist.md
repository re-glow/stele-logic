# Stele Release Checklist

Use this checklist before creating and pushing a release tag.
**Do not create the tag until all "Before tag" items are complete.**

This checklist applies to v1.3.0 and future releases.

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
# Expected: all pass; 4 skipped (Hypothesis property tests) is expected
```

Optional extended tests (requires `pip install -r requirements-dev.txt`):

```bash
python -m pytest tests/test_proof_term_properties.py -v
```

### 3. Build artifacts (fast, no Pyodide download)

```bash
# Pyodide site (static HTML/JS, no browser needed)
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

### 5. Optional: whitepaper build (requires LaTeX)

```bash
cd paper/
latexmk -pdf stele-whitepaper.tex
# verify stele-whitepaper.pdf exists — do NOT commit the PDF
cd ..
```

### 6. Site check (post Pages deploy)

- Confirm the GitHub Pages URL loads the landing page.
  URL: `https://re-glow.github.io/stele-logic/`
- Confirm Studio page loads: `https://re-glow.github.io/stele-logic/studio.html`
- Confirm Theory page loads: `https://re-glow.github.io/stele-logic/theory.html`
- Confirm Architecture page loads: `https://re-glow.github.io/stele-logic/architecture.html`
- Confirm Foundations page loads: `https://re-glow.github.io/stele-logic/foundations.html`
- Confirm Research page loads: `https://re-glow.github.io/stele-logic/research.html`
- Confirm About page loads: `https://re-glow.github.io/stele-logic/about.html`
- Confirm the 5-minute interactive tutorial section is visible on the landing.
- Confirm the example gallery renders 15 cards.
- Confirm the Studio loads (Pyodide first-load may take ~10 s).

### 7. Documentation consistency

- [ ] `stele/__version__.py` is set to `"1.3.0"`.
- [ ] `CHANGELOG.md` has a `[v1.3.0]` entry at the top.
- [ ] README.md version heading says `# Stele — v1.3.0`.
- [ ] README.md capability matrix heading says `## v1.3 Capability Matrix`.
- [ ] No generated files tracked in git:
  ```bash
  git status  # dist/, _site/, build/, __pycache__/, paper/*.pdf must not appear
  ```

### 8. Claim audit — v1.3 specific

- [ ] No "complete theorem prover" — Stele is a proof checker.
- [ ] No "machine-checked metatheory" or "formally verified metatheory".
  Acceptable: "proof sketches + regression/property tests".
- [ ] Kripke section says "bounded finite search"; absence-of-countermodel ≠ validity.
- [ ] Certificates/minicheck: "experimental"; "independent Python code path, not formally verified".
- [ ] Proof-state hints: "UNTRUSTED"; requires kernel-recheck.
- [ ] ML baseline: "optional / experimental"; no unverified accuracy claims.
- [ ] No "fully offline" claim for single-file HTML — Pyodide loads from CDN.
- [ ] No "state-of-the-art" or "production-ready" claims.
- [ ] FOL described as "experimental proof-term fragment"; no "full first-order logic" claim.
- [ ] Lean bridge: "optional, experimental, propositional fragment only".
- [ ] Classical bridge: "experimental, formula-level only (Gödel–Gentzen)"; no λμ/callcc claim.
- [ ] Foundations/Yurihak: "research motivation / future formalization"; not "implemented logic".
- [ ] About page: no email, no school name, no location.
- [ ] Site pages: no `/api/` backend calls in static HTML.
- [ ] Site pages: no React/Three.js/Spline/Framer/Tailwind CDN references.

### 9. No accidental commits

```bash
git log --oneline -10
git diff origin/main HEAD  # confirm only intended changes
```

---

## Tag and release

Once all "Before tag" items are checked:

```bash
# Create annotated tag
git tag -a v1.2.0 -m "Stele v1.2.0"

# Push tag to trigger the release workflow
git push origin v1.2.0
```

### After push

1. Watch `.github/workflows/release.yml` run on GitHub Actions.
2. Confirm all three OS builds (Windows, macOS, Linux) upload `SteleStudio` artifacts.
3. Confirm `stele.html` artifact is uploaded.
4. Create a GitHub Release from the tag.
   - Use `docs/release-notes-v1.2.0.md` as the release description.
   - Attach the SteleStudio executables and `stele.html`.
5. Confirm GitHub Pages is still live at the expected URLs (all 7 pages).

---

## Known limitations to include in release notes (v1.2)

- Stele-Light proof-script language remains propositional — no FOL quantifiers at script level.
  FOL is available in the proof-term core (`stele.core`) only, as an experimental API.
- Kripke countermodel search is bounded finite (≤4 worlds default). Absence of countermodel
  does not guarantee intuitionistic validity.
- Classical proof-term bridge is formula-level only (Gödel–Gentzen). No λμ/callcc.
- Proof certificates and minicheck are experimental. Minicheck is an independent Python code
  path (same Python process as the main kernel); not a formally verified checker.
- Proof-state hints are UNTRUSTED structural suggestions. Must be kernel-rechecked.
- ML baseline (`stele_ml/`) is optional and experimental; metrics are for the generated sample.
- Lean bridge (`stele_lean/`) is optional, experimental, propositional fragment only.
- Metatheory claims are proof sketches + regression/property tests; not machine-checked proofs.
- Single-file `stele.html` requires internet (Pyodide CDN, ~8 MB, cached after first load).
- Whitepaper is a draft technical report; not peer-reviewed.
- Foundations page covers research motivation (Yurihak); Yurihak is not yet a formal Stele logic.
