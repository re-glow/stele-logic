# Stele Public Site — Quality and Honesty Policy

This document records the public site quality commitments and what is explicitly NOT claimed.
It is intentionally lightweight. Additions should come with evidence, not aspirations.

---

## 1. What the site does

The public site (`site/index.html`, deployed via GitHub Pages) provides:

- An interactive 6-step proof tutorial.
- A verified example gallery (15 curated entries, all honesty-tested via `tests/test_gallery.py`).
- Stele Studio: proof checking, diagnostics, dependency graph, semantic tools, Kripke countermodel search.
- All computation runs locally in the user's browser via Pyodide/WebAssembly — no server, no data transmitted.

## 2. What the site does NOT do

- Does not send proof text to any server.
- Does not use cookies, analytics, tracking scripts, or local storage for user data.
- Does not claim to be an AI-powered tool, theorem prover, or production-grade system.
- Does not claim offline operation (Pyodide loads from CDN; full offline mode is future work).

## 3. First-load notice

Pyodide/WebAssembly is approximately 8 MB, loaded from CDN on first visit and cached by the browser.
This caveat is displayed in the Studio loading banner and documented in the README.
No numeric load-time claim is made because load time varies by browser, device, and network.

## 4. Status indicators

The following status labels are used in site copy and capability tables:

| Label | Meaning |
|-------|---------|
| **Stable** | Core feature; tested on every CI run; behavior is defined. |
| **Experimental** | New or bounded feature; behavior may change; documented limitations. |
| **Untrusted** | Advisory/assistant layer; must be kernel-rechecked; no correctness guarantee. |
| **Optional** | Not in the trusted checking path; requires extra setup or explicit opt-in. |
| **Demo** | Illustrative toy demo; not intended for general-purpose use. |

Features exposed in the browser Pyodide site:

| Feature | Status |
|---------|--------|
| Proof checking (kernel) | Stable |
| Structural diagnostics | Stable |
| Dependency graph | Stable |
| Matrix semantic tools (K3/LP) | Stable |
| World lattice demo | Stable (Demo) |
| Kripke countermodel search | Experimental — bounded finite search; absence ≠ proof of validity |
| Rule soundness report | Stable |

Features NOT in the public Pyodide site:
- `stele_ml/` ML baseline (optional, not included in browser build).
- `stele_lean/` Lean bridge (optional, not included in browser build).
- Proof certificates / minicheck (CLI only in v1.1).
- Proof-state hints (CLI/web API only in v1.1; not integrated in Pyodide site).

## 5. Accessibility checklist

The site aims for the following; deviations should be filed as issues:

- [ ] Keyboard navigation: tab order covers all interactive elements.
- [ ] `aria-live` regions on dynamic result panels (check-result, diagnose-result).
- [ ] `aria-current` on tutorial step indicators.
- [ ] `aria-controls` on tab-panel buttons.
- [ ] `aria-hidden` on decorative icons/emoji.
- [ ] `prefers-reduced-motion` media query honored for any animations.
- [ ] Contrast ratio: text on background ≥ 4.5:1 (WCAG AA).

## 6. No performance claims

File sizes and load times are not claimed in documentation. If measured, they belong in
release notes with the specific build/environment, not in general-purpose docs.

## 7. Onboarding clarity

- The first thing a visitor sees should make clear: "write a proof → kernel checks it".
- The distinction between `⊢` (proof-script kernel) and `⊨` (semantic diagnostics) must be
  explained before users encounter it in the semantic tools panel.
- "No install required" applies to the hosted site; not to the local Python CLI.
