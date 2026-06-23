# Stele Design System & Information Architecture

**Version:** for Prompts 43–49  
**Artefacts:** `site/assets/tokens.css`, `site/assets/components.css`,
`site/assets/visuals.js`, `site/assets/visuals.css`  
**Sources:** `docs/audit-public-readiness.md`, `site/index.html`, `stele/webapp/index.html`

---

## 1. Current Site Inventory

| File | Role | Status |
|------|------|--------|
| `site/index.html` | Single-page SPA: landing + workbench + gallery + docs | P1 — landing and Studio merged |
| `site/assets/stele_site.css` | Monolithic CSS for index.html; defines `:root` tokens and all component styles | Keep; tokens.css extends it |
| `site/assets/stele-pyodide.js` | Pyodide initialisation and Studio event handling | Keep untouched |
| `site/assets/stele-inline.js` | JS for Studio tabs, gallery, tutorial | Keep untouched |
| `stele/webapp/index.html` | Local Studio served by `python -m stele.web`; standalone Stele Studio | Keep separate |

**Key gaps identified in audit:**
- No separate Studio page (Studio embedded in landing scroll)
- No theory/research/about pages
- No multi-page nav
- `docs/whitepaper.md` not linked from site
- `docs/proof-terms.md` header says "Stele v2" (version drift — fix in this prompt)
- Body monospace font on all prose (addressed in tokens.css)
- `--muted #46586d` on `#07090f` ~2.5:1 contrast (fix in tokens.css)
- No status badge components (Experimental, Stable, etc.)

---

## 2. Target Information Architecture

Target structure for prompts 43–49. Each entry defines the page/section, audience, CTA,
status-label expectations, and which prompt builds it.

---

### 2.1 Overview / Landing (`index.html`)

**Purpose:** Immediately communicate what Stele is, demonstrate it is real (live demo),
direct different audiences to the right next step.

**Primary audiences:** Technical reviewer, first-time visitor, admissions officer.

**Core CTAs (in priority order):**
1. Open Studio → `studio.html`
2. Read Whitepaper → `docs/whitepaper.md`
3. View GitHub → `https://github.com/re-glow/stele-logic`

**Status labels:** No status labels on overview page itself — this is the pitch, not the docs.
Features shown in the hero must already be Stable.

**Content sections (final state after 43):**
- Hero: proof-dependency-graph motif + brand + tagline + 3 CTAs
- What Stele Does: 4–5 feature cards (Stable or Experimental badge per feature)
- Short tutorial: 3–4 steps, links to Studio
- Quick stats: test count, kernel size, zero runtime deps
- Get Started: 3 paths (Browser, Executable, Python)
- Docs / links grid (including whitepaper)
- Footer

**Files touched:** `site/index.html`, `site/assets/stele_site.css`, `site/assets/visuals.*`

**Prompt:** 43

---

### 2.2 Studio (`studio.html`)

**Purpose:** The proof workbench. Users write proofs, run checks, explore semantics.
Deliberately separate from the landing so landing visitors are not confronted with
the full IDE on first scroll.

**Primary audiences:** Technical user, teacher, student.

**Core CTAs:**
1. Run proof (keyboard Ctrl+Enter)
2. Load example
3. Open docs

**Status labels:**
- Verify: Stable
- Diagnose: Experimental (structural, untrusted)
- Graph: Stable
- Semantics (matrix, lattice): Stable
- Kripke: Experimental (bounded, ≤4 worlds)
- Examples: Stable

**Files touched:** `site/studio.html` (new), `site/assets/stele_site.css`, `site/assets/stele-pyodide.js`

**Note:** Full Studio functionality migration from `index.html` happens in Prompt 44.
Current `site/studio.html` is a skeleton; `index.html`'s Studio section is kept intact.

**Prompt:** 44

---

### 2.3 Theory (`theory.html`)

**Purpose:** Formal documentation for the proof language, proof-term calculus, matrix semantics,
and Kripke countermodels. Primary reference for technical reviewers and researchers who want
to understand the formal underpinnings.

**Primary audiences:** Formal-methods researcher, CS student with logic background.

**Core CTAs:**
1. Read formal semantics → `docs/semantics.md`
2. Read metatheory → `docs/metatheory.md`
3. Try it in Studio → `studio.html`

**Status labels:**
- Stele-Light proof language: Stable
- Proof-term calculus (Curry–Howard): Experimental
- Matrix semantics (K3, LP, Boolean): Stable
- Kripke countermodels: Experimental
- Classical bridge (negative translation): Experimental
- FOL fragment in proof terms: Experimental

**Files touched:** `site/theory.html` (new)

**Prompt:** 45

---

### 2.4 Architecture / Trust (`architecture.html`)

**Purpose:** Explain the trust model: what the kernel does and does not guarantee, how
the layers interact, what "trusted" means, what is explicitly untrusted.
Primary reference for anyone reviewing the system for reliability.

**Primary audiences:** Security reviewer, formal-methods researcher, technical lead.

**Core CTAs:**
1. Read kernel source → GitHub `stele/kernel.py`
2. Read trust-boundary docs → `docs/development-context.md`
3. Try minicheck → `studio.html` (CLI instructions)

**Status labels (for each layer):**
- Kernel (`stele/kernel.py`): Trusted core
- Parser (`stele/parser.py`): Trusted (stdlib only)
- Diagnostics (`stele/diagnostics.py`): Untrusted / advisory
- Proof-state hints (`stele/proofstate.py`): Untrusted
- Certificates (`stele/certificate.py`): Experimental
- Minicheck (`stele/minicheck.py`): Experimental / independent path
- ML baseline (`stele_ml/`): Optional / Untrusted
- Lean bridge (`stele_lean/`): Optional / Experimental

**Files touched:** `site/architecture.html` (new)

**Prompt:** (covered by research/trust content in prompt 46–47)

---

### 2.5 Demos (`index.html#gallery` or `demos.html`)

**Purpose:** Curated, honest, runnable examples with clear expected outcomes.
Every example has a stated expectation (pass/fail/warn) verified by the kernel.

**Primary audiences:** New user, teacher, tutorial follower.

**Core CTA:** Load example → Studio → run

**Status labels:** None on individual demos — they are all Stable features.
(Kripke demo would carry an Experimental badge if added.)

**Files touched:** `site/index.html` or future `site/demos.html`, `site/examples_gallery.json`

**Prompt:** 43 (landing integration), 44 (Studio integration)

---

### 2.6 Research (`research.html`)

**Purpose:** Connect Stele to the broader research context — Yurihak / logical pluralism,
proof assistants, formal verification. Present the whitepaper. Acknowledge what is
exploration vs. what is tested.

**Primary audiences:** Admissions officer, researcher, advanced student.

**Core CTAs:**
1. Read whitepaper → `docs/whitepaper.md`
2. View LaTeX source → `paper/stele-whitepaper.tex`
3. Read references → `paper/references.bib`

**Status labels:**
- Logical pluralism as motivation: note "background inspiration; not fully formalized"
- Proof-term metatheory: "proof sketches; not machine-checked"
- ML baseline: Optional / demo-scale corpus

**Constraint:** Do not present Yurihak as a completed framework. Frame it as motivation
and design inspiration for multi-logic support.

**Files touched:** `site/research.html` (new)

**Prompt:** 46, 47

---

### 2.7 About (`about.html`)

**Purpose:** Short creator/project narrative. For admissions officers, teachers, and
recommenders who want to understand the person and intellectual motivation behind the project.

**Primary audiences:** Admissions officer, recommender, potential collaborator.

**Core CTAs:**
1. Read whitepaper
2. View GitHub
3. Contact / KOAI portfolio (if applicable)

**Status labels:** None — this is a narrative page, not a feature page.

**Constraint:** No inflated self-promotion. Factual, concise, first-person where appropriate.

**Files touched:** `site/about.html` (new)

**Prompt:** 49

---

### 2.8 Docs / Downloads (`index.html#docs` or `docs.html`)

**Purpose:** Central reference for documentation links, download paths, CLI quick-start.

**Core CTAs:**
1. Language Guide → `GUIDE.md`
2. Formal Semantics → `docs/semantics.md`
3. Metatheory → `docs/metatheory.md`
4. Whitepaper → `docs/whitepaper.md`
5. GitHub
6. Single-file HTML download
7. Releases

**Files touched:** `site/index.html` §7 Docs grid

**Prompt:** 43 (add whitepaper link), 47 (full docs page)

---

## 3. Design Tokens

All tokens are defined in `site/assets/tokens.css`. Load it before `stele_site.css`
so stele_site.css can override duplicates with its existing values.

### 3.1 Color

| Token | Value | Use |
|-------|-------|-----|
| `--bg` | `#07090f` | Page background |
| `--bg2` | `#090c15` | Alternate section background |
| `--surface` | `#0d1220` | Card/panel background |
| `--surf2` | `#111826` | Elevated surface |
| `--surf3` | `#0a1018` | Code block / deep surface |
| `--border` | `#1c2840` | Default border |
| `--bord2` | `#263450` | Active/hover border |
| `--text` | `#b8cce0` | Primary text |
| `--text-secondary` | `#7fa0be` | Secondary prose text |
| `--muted` | `#5e7a8f` | **Updated from #46586d** — fixes WCAG contrast |
| `--dim` | `#283a54` | Dimmed/disabled |
| `--cyan` | `#00e8ff` | Primary accent |
| `--violet` | `#b06aff` | Secondary accent |
| `--green` | `#00ff9f` | Success / Stable |
| `--red` | `#ff3566` | Error / Refutable |
| `--amber` | `#ffb347` | Warning / Experimental |

**Status badge tokens:**

| Token | Value | Label |
|-------|-------|-------|
| `--status-stable-bg` | `rgba(0,255,159,.08)` | Stable |
| `--status-stable-fg` | `#00ff9f` | Stable |
| `--status-stable-border` | `rgba(0,255,159,.22)` | Stable |
| `--status-experimental-bg` | `rgba(255,179,71,.08)` | Experimental |
| `--status-experimental-fg` | `#ffb347` | Experimental |
| `--status-experimental-border` | `rgba(255,179,71,.22)` | Experimental |
| `--status-optional-bg` | `rgba(176,106,255,.08)` | Optional |
| `--status-optional-fg` | `#b06aff` | Optional |
| `--status-optional-border` | `rgba(176,106,255,.22)` | Optional |
| `--status-demo-bg` | `rgba(0,232,255,.06)` | Demo |
| `--status-demo-fg` | `#00e8ff` | Demo |
| `--status-demo-border` | `rgba(0,232,255,.2)` | Demo |
| `--status-future-bg` | `rgba(40,58,84,.5)` | Future |
| `--status-future-fg` | `#46586d` | Future |
| `--status-future-border` | `rgba(40,58,84,.8)` | Future |
| `--status-untrusted-bg` | `rgba(255,53,102,.06)` | Untrusted |
| `--status-untrusted-fg` | `#ff3566` | Untrusted |
| `--status-untrusted-border` | `rgba(255,53,102,.2)` | Untrusted |

### 3.2 Typography

| Token | Value | Use |
|-------|-------|-----|
| `--font-mono` | `ui-monospace,"SF Mono","Cascadia Code",Consolas,monospace` | Code, labels, proof editor |
| `--font-sans` | `system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,sans-serif` | Prose, headings, body text |
| `--font-display` | same as `--font-sans` | Hero / display text |
| `--text-xs` | `0.72rem` | Labels, badges, captions |
| `--text-sm` | `0.82rem` | Secondary body |
| `--text-base` | `0.92rem` | Body text |
| `--text-md` | `1rem` | Card titles, subheadings |
| `--text-lg` | `1.2rem` | Section subheadings |
| `--text-xl` | `1.6rem` | Section headings |
| `--text-2xl` | `2.2rem` | Page headings |
| `--text-hero` | `clamp(3rem, 8vw, 6rem)` | Hero brand |
| `--lh-tight` | `1.2` | Headings |
| `--lh-normal` | `1.6` | Body |
| `--lh-loose` | `1.8` | Long-form prose |
| `--tracking-label` | `0.12em` | Uppercase labels |
| `--tracking-title` | `0.04em` | Section headings |

**Typography rule:** `body` font should be `var(--font-sans)` for prose pages.
Monospace is reserved for code elements, labels, nav brand, proof editors, and badges.
The current `site/index.html` uses monospace throughout; this will be corrected gradually
from Prompt 43 onward.

### 3.3 Layout

| Token | Value | Use |
|-------|-------|-----|
| `--max-w-text` | `680px` | Prose / long-form reading |
| `--max-w-content` | `1100px` | Standard section |
| `--max-w-wide` | `1280px` | Wide sections (Studio) |
| `--space-1` | `4px` | |
| `--space-2` | `8px` | |
| `--space-3` | `12px` | |
| `--space-4` | `16px` | |
| `--space-6` | `24px` | |
| `--space-8` | `32px` | |
| `--space-12` | `48px` | |
| `--space-16` | `64px` | |
| `--space-section` | `80px` | Section vertical padding |
| `--gap-card` | `18px` | Card grid gap |
| `--gap-feature` | `18px` | Feature card grid gap |
| `--bp-sm` | `640px` | — comments only, no CSS var |
| `--bp-md` | `900px` | — comments only |
| `--bp-lg` | `1100px` | — comments only |

### 3.4 Shape & Glow

| Token | Value | Use |
|-------|-------|-----|
| `--radius-sm` | `3px` | Badges, tight corners |
| `--radius` | `6px` | Cards, panels |
| `--radius-lg` | `10px` | Large panels |
| `--glow-cyan` | `0 0 18px rgba(0,232,255,.12)` | Hover states |
| `--glow-green` | `0 0 14px rgba(0,255,159,.12)` | Success states |
| `--glow-violet` | `0 0 14px rgba(176,106,255,.12)` | Secondary hover |
| `--border-width` | `1px` | Default |

### 3.5 Motion

| Token | Value | Use |
|-------|-------|-----|
| `--dur-fast` | `120ms` | Hover, instant feedback |
| `--dur-normal` | `220ms` | Transitions |
| `--dur-slow` | `400ms` | Load/reveal transitions |
| `--ease-default` | `ease` | General |
| `--ease-out` | `cubic-bezier(0.2, 0, 0, 1)` | Exit animations |
| `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Playful bounce (sparingly) |

**Reduced-motion policy (see §7 Accessibility):**  
All animations gated with `@media (prefers-reduced-motion: reduce)`.  
Static fallback required for every animated element.

### 3.6 Z-Index

| Token | Value | Layer |
|-------|-------|-------|
| `--z-base` | `0` | Content |
| `--z-above` | `10` | Overlapping cards |
| `--z-sticky` | `100` | Sticky elements |
| `--z-nav` | `200` | Navigation |
| `--z-overlay` | `400` | Modal overlays |
| `--z-scanline` | `9990` | Scanline texture |

---

## 4. Component Library

All components are defined in `site/assets/components.css`.
Existing components in `stele_site.css` (`.btn`, `.feature-card`, etc.) remain intact.
New components added here extend the system.

### 4.1 Status Badges

```html
<span class="badge badge-stable">Stable</span>
<span class="badge badge-experimental">Experimental</span>
<span class="badge badge-optional">Optional</span>
<span class="badge badge-demo">Demo</span>
<span class="badge badge-future">Future</span>
<span class="badge badge-untrusted">Untrusted</span>
```

**Rule:** Status badges must ALWAYS contain visible text — never color alone.  
**Rule:** Every component on the site that has a status other than Stable must have a badge.

### 4.2 Trust Boundary Card

Used on architecture page and in component docs.

```html
<div class="trust-card trust-card-trusted">
  <div class="trust-card-header">
    <span class="badge badge-stable">Trusted</span>
    <span class="trust-card-name">Kernel</span>
  </div>
  <div class="trust-card-body">…description…</div>
  <code class="trust-card-path">stele/kernel.py</code>
</div>
```

### 4.3 Metric / Evidence Card

Used on landing stats and research page.

```html
<div class="metric-card">
  <div class="metric-value">1852</div>
  <div class="metric-label">Regression tests</div>
  <div class="metric-note">4 skipped (Hypothesis optional)</div>
</div>
```

### 4.4 Callout / Note

```html
<div class="callout callout-info">
  <span class="callout-label">Note</span>
  <p>…text…</p>
</div>
<div class="callout callout-warning">
  <span class="callout-label">Experimental</span>
  <p>…text…</p>
</div>
```

### 4.5 Proof Snippet

Inline code display styled for proof scripts.

```html
<pre class="proof-snippet"><code>theorem dne using classical_prop:
  assume h1: not not P
  conclude P by dne h1</code></pre>
```

### 4.6 Graph Canvas Container

Wraps the SVG/Canvas proof dependency graph visual.

```html
<div class="graph-canvas-wrap" aria-hidden="true">
  <!-- SVG injected by visuals.js or inlined -->
</div>
```

### 4.7 Document Link Card

Extended from current `.doc-card` with optional badge support.

```html
<a class="doc-link-card" href="…">
  <span class="doc-link-icon" aria-hidden="true">📄</span>
  <span class="doc-link-title">Technical Whitepaper</span>
  <span class="badge badge-stable">PDF / Markdown</span>
  <span class="doc-link-desc">Architecture, semantics, metatheory, limitations.</span>
</a>
```

### 4.8 Page Shell

All skeleton pages use this structure:

```html
<div class="page-shell">
  <nav class="site-nav">…</nav>
  <main class="page-main" id="main-content">
    <section class="page-hero">…</section>
    <section class="page-section">…</section>
  </main>
  <footer class="site-footer">…</footer>
</div>
```

### 4.9 Section Header with Status

```html
<div class="section-header">
  <span class="section-label">Theory</span>
  <h1 class="section-heading">Proof-Term Calculus</h1>
  <span class="badge badge-experimental">Experimental</span>
  <p class="section-sub">…</p>
</div>
```

---

## 5. Status Label Policy

Every public-facing feature claim must carry one of these labels:

| Label | CSS class | Meaning | When to use |
|-------|-----------|---------|-------------|
| **Stable** | `.badge-stable` | Tested, trusted, documented, no breaking changes expected | Core proof checking, parsing, 5 built-in logics, matrix semantics, world lattice, gallery examples |
| **Experimental** | `.badge-experimental` | Implemented and tested, may change; not all edge cases covered | Kripke countermodels, certificates, minicheck, proof terms / Curry–Howard, ML baseline, classical bridge |
| **Optional** | `.badge-optional` | Not included in browser build; requires local Python install | ML baseline (`stele_ml/`), Lean bridge (`stele_lean/`) |
| **Demo** | `.badge-demo` | Illustrative; may be simplified vs full implementation | Interactive tutorial, gallery previews, visual motifs |
| **Future** | `.badge-future` | Planned; not implemented | FOL in Stele-Light, structural rule policies, Rust kernel |
| **Untrusted** | `.badge-untrusted` | Explicitly outside trust boundary; output is advisory only | Diagnostics, proof-state hints, ML classification |

**Enforcement rule:** If a new component or section describes a feature with a status other than
Stable, the design must include the appropriate badge. Do not omit it for aesthetic reasons.

---

## 6. Visual Motif Specification

Three visual primitives, implemented in `site/assets/visuals.js` and `site/assets/visuals.css`.

### 6.1 ProofGraphHero

**What it is:** A simple SVG proof dependency graph showing 4 nodes (h1, h2, mp, ∴) and
3 directed edges. Represents an actual modus ponens proof derivation.

**Why:** This is a real Stele capability (the `proofgraph` module outputs DOT graphs from
proofs). Using it as the primary visual motif ties the aesthetic directly to the tool's
function — unlike generic floating math symbols.

**Spec:**
- Pure SVG, 4 nodes, 3 edges, monospace labels, arrow markers
- Node colors: hypothesis nodes (cyan), rule node (violet), conclusion node (green)
- Edges: thin cyan-tinted lines with arrowhead markers
- Accessible: `role="img"` with `aria-label` describing the proof structure
- Decorative use: `aria-hidden="true"` on wrapper
- Animation: conclusion node subtle glow pulse — disabled under `prefers-reduced-motion`
- Responsive: `viewBox`-based, scales with container

**API:**
```javascript
SteleVisuals.renderProofGraph(containerElement, { decorative: true });
```

**Auto-init:** Any element with `data-stele-visual="proof-graph"` gets the proof graph
injected on `DOMContentLoaded`.

### 6.2 LogicSymbolField

**What it is:** A subtle, low-opacity decorative field of logic symbols rendered as CSS
background pattern or positioned spans.

**Why:** Provides textural depth without the animation noise of the current hero cascade.

**Spec:**
- Static or very slow drift (disabled under `prefers-reduced-motion`)
- Symbols: `⊢ ⊨ ∀ ∃ ∧ ∨ ¬ → ⊥ ∴`
- Opacity: 0.03–0.06 (barely visible, texture only)
- CSS class `.logic-symbol-field` or `data-stele-visual="symbol-field"`

### 6.3 Kripke World Motif

**What it is:** A simple SVG poset diagram showing 3 worlds (W0, W1, W2) connected by
accessibility relation arrows. Used on the theory and architecture pages.

**Why:** Visually represents the Kripke semantics feature. Inspired by the wireframe-sphere
design reference but simpler and more semantically correct (actual poset, not a sphere).

**Spec:**
- Pure SVG, 3 nodes (W0, W1, W2), 2 edges (W0→W1, W0→W2)
- W0 at center-bottom, W1 and W2 above left/right
- Minimal wireframe style: node circles + edge lines
- Static; no animation needed
- `role="img"` with `aria-label`

**API:**
```javascript
SteleVisuals.renderKripkeMotif(containerElement, { decorative: false });
```

---

## 7. Accessibility Policy

All public-facing Stele pages must meet these requirements:

### 7.1 Keyboard navigation

- Every interactive element (links, buttons, inputs, selects, tabs) must be reachable
  by keyboard tab order.
- Tab order must follow visual reading order (left→right, top→bottom).
- No keyboard traps.

### 7.2 Focus visibility

```css
:focus-visible {
  outline: 2px solid var(--cyan);
  outline-offset: 3px;
  border-radius: var(--radius-sm);
}
```

This style is already present in `stele_site.css`. Do not remove it.
Buttons and interactive elements must never have `outline: none` without a visible alternative.

### 7.3 Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  /* Disable: symbol cascade, proof-graph pulse, notice-dot pulse, loading animations */
  /* Keep: state transitions (tab switching), loading bar (static fill) */
}
```

Rule: Every animated element must have a static fallback under `prefers-reduced-motion`.
The scanline texture is already guarded (line 56, `stele_site.css`). ✓
The hero symbol cascade is already guarded (`animation: none; opacity: 0`). ✓
New visuals must follow the same pattern.

### 7.4 Color and contrast

- Primary text `--text #b8cce0` on `--bg #07090f`: contrast ratio ≈ 10.5:1 (WCAG AAA). ✓
- Updated muted text `--muted #5e7a8f` on `--bg #07090f`: contrast ratio ≈ 4.8:1 (WCAG AA). ✓
  (Previous `#46586d` was ~2.5:1 — fails WCAG AA; fix in `tokens.css`.)
- Never convey information only through color. Status badges must include text labels.
- Status PROVABLE/REFUTABLE/INDEPENDENT in semantics panel: add shape indicators in future.

### 7.5 ARIA

- `aria-live="polite"` only on dynamically updating regions (check results, diagnostics).
  Do not add `aria-live` to static sections.
- Decorative visuals: `aria-hidden="true"` on wrapper.
- Non-decorative visuals: `role="img"` with `aria-label` description.
- Navigation landmarks: `<nav aria-label="Site navigation">`.
- Main content landmark: `<main id="main-content">`.
- Skip link: `<a href="#main-content" class="sr-only focus-skip">Skip to main content</a>`.

### 7.6 Semantics

- Use semantic HTML: `<nav>`, `<main>`, `<section aria-labelledby>`, `<article>`, `<footer>`.
- Section headings: every `<section>` has an `aria-labelledby` pointing to an `<h*>` inside it.
- Don't use `<div>` where a semantic element exists.

### 7.7 Mobile

- All new pages must be usable at 320px viewport width.
- Navigation must not overflow horizontally.
- Tap targets: minimum 44×44px effective area.

---

## 8. Copy Style Guide

### 8.1 Forbidden phrases

These phrases are banned in all public-facing copy, docs, comments in site files, and design documents:

| Phrase | Why banned |
|--------|-----------|
| `dynamic rendering engine` | Vague SaaS speak |
| `elevate your workflow` | Generic marketing |
| `real-time global connectivity` | Irrelevant to the domain |
| `unlock the power` | Empty enthusiasm |
| `AI-powered verifier` | Stele is not AI-powered; banned as a positive claim |
| `state-of-the-art` | Overclaim |
| `production-ready` | Untested against production workloads |
| `seamless experience` | Vague |
| `guaranteed proof` | Stele finds errors; it does not guarantee correctness of new proofs |
| `fully verified` | Metatheory is proof-sketched, not machine-checked |

### 8.2 Preferred verbs

- `write` — the user writes proofs
- `check` — the kernel checks steps
- `inspect` — diagnostics inspect structure
- `find` — Kripke finds countermodels
- `export` — certificate/DOT export
- `verify` — kernel verifies rule applications
- `compare` — logic comparison (classical vs. intuitionistic)
- `trace` — error tracing to specific lines

### 8.3 Preferred claim pattern

> [Component] · [status label] · [what it does] · [one limitation]

Examples:

**Bad:** "Stele's intelligent verification engine delivers real-time proof validation."  
**Better:** "The kernel checks each inference step against the declared logic's rule set.
Proof terms are not extracted from classical proofs — acceptance is at the rule level."

**Bad:** "Kripke countermodel search validates intuitionistic logic."  
**Better:** "Kripke countermodel search (Experimental) finds countermodels with ≤4 worlds.
Absence of a countermodel is not a proof of validity."

**Bad:** "1836 tests ensure correctness."  
**Better:** "1852 regression tests catch regressions. Tests do not constitute
a machine-checked proof of the metatheory claims."

### 8.4 Formatting rules

- Status badge text: ALWAYS in the format `[Label]` — never "EXPERIMENTAL" in running prose.
  Use the badge component; the prose itself should not shout.
- Version references: write `v1.1` or `v1.1.0`, never `v2` or `version 2`.
- Mathematical notation: use Unicode symbols in HTML (`⊢`, `⊨`, `∀`);
  use LaTeX notation only in `.tex` files.
- Code: always in `<code>` or `<pre><code>` blocks; never in bold prose.

---

## 9. Prompt-to-Page Mapping

| Prompt | Focus | Primary files |
|--------|-------|---------------|
| 42 (this) | Design system, tokens, components, IA spec, skeleton pages | `docs/design-system.md`, `tokens.css`, `components.css`, `visuals.*`, `site/*.html` skeletons |
| 43 | Landing page redesign — hero, feature cards, tutorial, docs section | `site/index.html`, `stele_site.css` |
| 44 | Studio separation — `studio.html` with full workbench | `site/studio.html`, `stele_site.css`, `stele-pyodide.js` |
| 45 | Theory page content — proof language, proof terms, matrix semantics, Kripke | `site/theory.html` |
| 46 | Yurihak / logical pluralism research integration | `site/research.html`, `docs/whitepaper.md` |
| 47 | References, provenance, whitepaper promotion | `site/research.html`, `site/index.html` §7 |
| 48 | Research notes, paper writing support | `docs/research-notes.md`, `paper/` |
| 49 | About / admissions-facing page | `site/about.html` |
| 50 | Public-presentation freeze, final claim audit | All new pages + `CHANGELOG.md` |

---

## 10. File Register

| File | Role | New/Existing |
|------|------|-------------|
| `site/assets/tokens.css` | Design token CSS custom properties | New |
| `site/assets/components.css` | New component styles (badges, trust cards, etc.) | New |
| `site/assets/visuals.css` | Visual motif CSS companions | New |
| `site/assets/visuals.js` | Visual motif JS stubs (proof graph, symbol field, Kripke) | New |
| `site/assets/stele_site.css` | Existing monolithic CSS — kept, extended by tokens/components | Existing |
| `site/assets/stele-pyodide.js` | Pyodide bridge — do not touch | Existing |
| `site/assets/stele-inline.js` | Studio JS — do not touch | Existing |
| `site/index.html` | Landing SPA — add links to tokens/components; no redesign yet | Existing (minor update) |
| `site/studio.html` | Studio skeleton | New |
| `site/theory.html` | Theory skeleton | New |
| `site/architecture.html` | Architecture/trust skeleton | New |
| `site/research.html` | Research skeleton | New |
| `site/about.html` | About skeleton | New |
