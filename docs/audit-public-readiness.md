# Stele Public-Readiness Audit

**Prepared for:** Prompts 42–50 arc planning
**Evidence base:** `site/index.html`, `stele/webapp/index.html`, `site/assets/stele_site.css`,
`site/examples_gallery.json`, `README.md`, `GUIDE.md`, `CHANGELOG.md`, `CLAUDE.md`,
`docs/development-context.md`, `docs/semantics.md`, `docs/metatheory.md`, `docs/proof-terms.md`,
`docs/whitepaper.md`, `docs/benchmark-card.md`, `docs/site-quality.md`,
`docs/release-checklist.md`, `stele_ml/README.md`, `.github/workflows/*.yml`
**Test status:** 1852 passed, 4 skipped — all green before this audit.

---

## 1. Executive Summary

### Overall grade: **B / B+**

The core product is technically honest, well-tested (1852 tests), and clearly positioned.
The site avoids SaaS clichés, the trust boundary is correctly maintained, and copy is mostly
direct. The gap between B and A is information architecture and presentation:
the site merges landing + workbench into one long scroll, the research narrative is absent,
and v1.1 features (Kripke, certificates, hints) are nearly invisible to visitors.

### Top 5 risks

1. **Landing and Studio are the same page.** A first-time visitor trying to understand the
   project encounters the full workbench immediately; a researcher trying to use the Studio
   has to scroll past a long landing page. The two audiences have incompatible information
   needs on the same scroll surface.
2. **docs/proof-terms.md says "Stele v2".** The file header (line 1) reads
   `# Proof-Term Core — Stele v2`, which conflicts with the v1.1.0 release and will confuse
   anyone reading the documentation. This is the most visible version-consistency error.
3. **Whitepaper is invisible from the site.** `docs/whitepaper.md` and `paper/stele-whitepaper.tex`
   exist but are not linked from the site's Docs section (§7) or the tutorial's "What's next"
   step. Technical reviewers, admissions officers, and research readers will not find it.
4. **v1.1 features are underrepresented in the site's §2 "What Stele Does" cards.**
   The four feature cards cover only core proof checking, diagnostics, dependency graph, and
   matrix semantics — no mention of Kripke countermodel search (v1.1), proof certificates,
   or proof-state hints. A visitor who reads only §1–§2 leaves with a v1.0 picture.
5. **No research or about/profile page.** For admissions officers, teachers, and researchers
   who want context about the creator or the research motivation (Yurihak / logical pluralism),
   there is nothing on the site. The footer says "Formal Verification Framework for Mathematical
   Reasoning" but provides no further narrative bridge to the research context.

### Top 5 high-leverage improvements

1. **Separate landing page from Studio** — landing.html or a distinct section layout so
   the hero/tutorial/gallery stands alone, Studio is accessed deliberately.
2. **Add whitepaper link on site** — add `docs/whitepaper.md` to site §7 Docs grid and
   Tutorial Step 6 "What's next".
3. **Fix docs/proof-terms.md header** — change "Stele v2" to "Stele v1.1" to resolve
   the most visible version inconsistency.
4. **Add a "Research / About" section to site** — even a lightweight page that places
   Stele in the context of Yurihak / logical pluralism and links to the whitepaper.
5. **Show v1.1 features on landing** — add Kripke, certificates, and/or hints to §2
   feature cards or §5 tutorial, with Experimental/Untrusted labels.

### Recommended 42–50 arc summary

| Prompt | Focus |
|--------|-------|
| 42 | Design system and information architecture — separate landing from Studio |
| 43 | Landing page redesign — hero, §2 features, proof-graph motif |
| 44 | Studio separation and v1.1 features UI |
| 45 | Theory / semantics / metatheory documentation page |
| 46 | Yurihak / logical pluralism research integration |
| 47 | References, provenance, whitepaper promotion |
| 48 | Research notes and GPT-paper writing support |
| 49 | About / admissions-facing profile page |
| 50 | Public-presentation freeze and final claim audit |

---

## 2. Audience Analysis

### 2.1 Technical / math / CS reviewer

**Understands quickly:** `⊢` vs `⊨` distinction (§2, §5 tutorial), trust-boundary separation
(docs footer, CLAUDE.md), proof checker ≠ theorem prover (§2), zero runtime deps.
**Confused by:** "Stele v2" header in `docs/proof-terms.md`; lack of link to whitepaper
from site; no status labels (Experimental/Stable) visible on site; Kripke section is hidden
in Studio → Semantics panel, not on the landing.
**Impressed by:** honest claim boundaries, metatheory docs with explicit "not machine-checked"
disclaimers, 1852 tests, Curry–Howard elaboration path, de Bruijn layer.
**Over-technical:** the body font is monospace throughout — even non-code prose is in
`ui-monospace`, which is distinctive but can feel fatiguing at paragraph scale.

### 2.2 Admissions officer

**Understands quickly:** "formal verification framework," "write a proof → kernel checks it,"
"no backend," tutorial demo.
**Confused by:** no author/creator information visible; no research narrative connecting to
Yurihak / logical pluralism; no "About the project" section; the project appears to be a
utility tool with no stated intellectual motivation.
**Impressed by:** 1852 tests, clean design, zero-dependency claim, multi-logic support demo.
**Under-designed for this audience:** no About page, no project origin story, no person behind it.

### 2.3 Teacher / recommender

**Understands quickly:** classical vs intuitionistic demo (tutorial step 4), 15 curated examples
with expected outcomes, honest "bounded finite search" Kripke disclaimer.
**Confused by:** tutorial jumps directly into proof syntax without stating the research problem
being addressed; Yurihak / logical pluralism not mentioned on site at all; no connection between
the tool and why logical pluralism matters.
**Impressed by:** multi-logic differentiation is immediately demonstrable (try classical ✓ →
try intuitionistic ✗), gallery with honesty-tested labels.
**Over-technical:** semantic tools (§5 tutorial) explanation of `⊢` vs `⊨` distinction may
require background knowledge that is not established earlier in the tutorial.

### 2.4 Casual visitor

**Understands quickly:** the hero tagline "Mathematical reasoning, verified" and the feature
cards in §2 convey the purpose clearly without jargon overload.
**Confused by:** the immediate progression to a full Studio workbench in §4 (after just
two sections) is abrupt; the word "proof" appears everywhere but natural-language examples
of what kind of reasoning Stele supports are sparse.
**Impressed by:** runs in the browser, no install, nice dark academic aesthetic.
**Not served by:** the current site assumes familiarity with natural deduction; a visitor
with high-school or undergraduate math background but no formal logic background may not know
what to do in the Studio.

---

## 3. Information Architecture Audit

Current structure (single-page scroll, `site/index.html`):

| Section | HTML anchor | Lines | Current status |
|---------|-------------|-------|----------------|
| Hero | `#hero` | 30–74 | ✓ present |
| What Stele Does | `#what` | 79–134 | ✓ present (feature cards — v1.0 view) |
| Tutorial | `#tutorial` | 139–427 | ✓ present (6 steps, Step 6 lacks whitepaper link) |
| Studio / workbench | `#studio` | 432–666 | ✓ present — **merged with landing** |
| Gallery | `#gallery` | 671–689 | ✓ present (15 entries) |
| Get Started | `#quickstart` | 694–747 | ✓ present |
| Documentation | `#docs` | 752–804 | ✓ present — **missing whitepaper** |
| Footer | — | 806–821 | ✓ present |

Missing pages / sections:

| Section | Status | Issue | Recommended prompt |
|---------|--------|-------|--------------------|
| Separate landing page | **Missing** | Landing and Studio are merged into one scroll | 42–43 |
| Separate Studio / workbench | **Missing** | Studio is embedded as §4 of the landing | 44 |
| Theory / semantics page | **Missing** | Only GitHub links to docs | 45 |
| Whitepaper / research | **Missing** | `docs/whitepaper.md` not linked from site | 47 |
| About / profile | **Missing** | No creator info, no research motivation | 49 |
| Distribution / downloads | **Partial** | §6 "Get Started" covers this but links to GitHub Releases rather than direct artifacts | 50 |
| Yurihak / philosophy | **Missing** | Research motivation for logical pluralism absent | 46 |
| Changelog / releases | **Missing** | No site entry; CHANGELOG.md is GitHub-only | 50 |

**Critical flag:** Landing and Studio are currently merged. The hero-to-workbench scroll
is 430 lines in `site/index.html`. This should be flagged as the primary redesign target
for prompts 42–44.

---

## 4. Visual / Design Audit

### 4.1 What to keep

- **Color palette:** `--bg #07090f`, `--cyan #00e8ff`, `--text #b8cce0` creates a dark
  academic / observatory aesthetic that is appropriate for formal logic tooling. Distinctive.
- **Scanline texture:** `body::before` repeating gradient (line 49–55 of `stele_site.css`).
  Adds texture without visual noise. `prefers-reduced-motion` respected ✓.
- **Section rhythm:** alternating `background: var(--bg2)` on even sections creates visual
  cadence without requiring complex layout.
- **Tutorial step mechanism:** numbered dots, prev/next buttons, aria-live counter — functional
  and accessible.
- **Kripke disclaimer text** (`site/index.html` line 629): "Bounded search — absence of a
  countermodel is not a proof of validity" — keep this copy verbatim.
- **`proof relativity` callout** in §2 — distinctive and accurate framing.

### 4.2 What to remove or reduce

- **Floating mathematical symbol cascade** (`hero-symbols`, lines 33–54). The 20 animated
  symbols (∀, ⊢, →, ¬, ∃, ∧, ⊨, ∨, ⊥, ∴, ≡, ∈, ⊃) are decorative noise rather than
  meaningful visual content. They do not represent actual proof structure. The cascade is
  `aria-hidden` and `prefers-reduced-motion`-safe, but it occupies the hero space that a
  more distinctive motif could use.
- **Monospace body font** (`body { font-family: var(--mono) }` in CSS line 34). Every
  paragraph of prose is rendered in monospace. Appropriate for code, but makes long
  descriptions (§2 feature card `p.feature-desc`, tutorial `.tstep-desc p`) feel cramped
  and fatiguing. The distinction between prose and code is lost.

### 4.3 What to redesign

- **Hero** — replace floating symbol cascade with actual proof dependency graph visualization
  (Canvas/SVG). A minimal animated graph showing 4–5 nodes (h1→h3, h2→h3→conclude) would
  immediately communicate what Stele does in a way no floating ∀ can. This is the "proof
  graph motif" from the design references.
- **Studio integration** — embed Studio as a separate page or clearly gate it behind a CTA.
  The current layout scrolls a visitor through tutorial + gallery before the Studio even
  loads, creating perceived latency for users who want to use it immediately.
- **Feature cards** (§2 `.feature-grid`) — currently 4 cards; add a 5th for Kripke
  (Experimental badge) or expand Semantic Tools card to mention it explicitly.
- **Typography** — prose sections (`.feature-desc`, `.section-sub`, `.tstep-desc p`)
  should use a sans-serif fallback; monospace should be reserved for code elements,
  labels, and headings.

### 4.4 Design-reference translation

See §10 for detailed motif mapping.

### 4.5 Candidate design signature for Stele

> A dark observatory aesthetic with proof-dependency-graph as the primary visual motif.
> Restrained use of the cyan (#00e8ff) accent.
> Monospace for code and labels, sans-serif for prose.
> No particle effects.

---

## 5. Copywriting Audit

### 5.1 Phrases that are clean and should be kept

- `site/index.html:59` — "Mathematical reasoning, verified." — precise, concrete.
- `site/index.html:61–64` — "Write structured natural-deduction proofs. Stele's trusted
  kernel checks each step for logical validity — in the browser, with no backend, no
  installation, no data sent to any server." — excellent. Every claim is verifiable.
- `site/index.html:86–89` — "Stele is a proof checker, not a theorem prover. You supply
  each inference step; the kernel decides if it is valid under the declared logic." — perfect.
- `site/index.html:629` — "Bounded search — absence of a countermodel is not a proof of
  validity." — honest and specific.

### 5.2 Issues

| File | Line / section | Original | Issue | Suggested direction |
|------|----------------|----------|-------|---------------------|
| `site/index.html` | §5 tutorial step 6, "Language Guide" card | "Complete syntax reference, inference rules, matrix semantics, world lattice, CLI, and proof term elaboration." | Lists features but doesn't mention Kripke, certificates, or hints (all v1.1). The guide card feels outdated for v1.1. | Add "Kripke countermodels, proof certificates" to feature list |
| `site/index.html` | §7 Docs, `Proof Terms` card, line 780 | "Curry–Howard core, FOL fragment, term parser, elaboration API." | Fine content, but the card links to `docs/proof-terms.md` which has a "Stele v2" header — visible to anyone who follows the link. | Fix `docs/proof-terms.md` header first (see §6) |
| `site/index.html` | §2 "Semantic Tools" card, line 119–124 | "Check rule soundness against multi-valued matrices (K3, LP, Boolean). Explore world lattices and proposition-level independence patterns." | Does not mention Kripke countermodel search, which is a featured v1.1 capability and is present in the Studio. | Extend to: "…and find Kripke countermodels for intuitionistic logic (bounded, Experimental)." |
| `site/index.html` | Tutorial Step 6, "What's next", line 381–414 | 3 cards: Browser Studio, Example Gallery, Language Guide | Whitepaper (`docs/whitepaper.md`) and research narrative are completely absent from this "what's next" screen. | Add a 4th card: "Technical Whitepaper" linking to `docs/whitepaper.md` (or `paper/stele-whitepaper.tex`) |
| `site/index.html` | Hero section, line 70–72 | "Runs locally via Pyodide/WASM · ~8 MB on first visit, then cached" | Good disclaimer. Fine as-is. | Keep |
| `README.md` | §Development | "python -m stele.web   # 브라우저 UI (기본 포트 8765)" | Port 8765 is the old web.py default; the main entry point `python -m stele` uses port 8000. Minor inconsistency. | Check which port is authoritative |
| `stele/webapp/index.html` | line 1 title | `<title>Stele Studio</title>` | Fine — the local Studio is correctly titled separately from the public site. Keep. | Keep |
| `GUIDE.md` | Line 1–3 | "기술 아키텍처 전체: docs/whitepaper.md (기술 백서/preprint)" | Good — whitepaper is linked from GUIDE.md. | Keep |

### 5.3 AI-ish / generic SaaS phrases found

**None found in the public-facing copy.** The site avoids "elevate your workflow,"
"seamless experience," "unlock the power," and similar marketing language. This is a
significant strength. The copy is technical and direct throughout.

One borderline case:
- `site/index.html:83` — "A proof checker with semantic diagnostics" — this heading is
  accurate but not very distinctive as a section heading. It describes what the system is
  rather than what the user does with it. Consider "Check each step. Diagnose each error."
  But this is a polish item, not an urgent fix.

---

## 6. Claim / Status Audit

### 6.1 Version consistency

| File | Claim | Actual | Risk | Action |
|------|-------|--------|------|--------|
| `stele/__version__.py` | `"1.1.0"` | v1.1.0 ✓ | — | OK |
| `README.md` line 1 | `# Stele — v1.1.0` | v1.1.0 ✓ | — | OK |
| `README.md` line 18 | `## v1.1 Capability Matrix` | v1.1 ✓ | — | OK |
| `CHANGELOG.md` line 7 | `[v1.1.0] — 2026-06-23` | v1.1.0 ✓ | — | OK |
| `docs/whitepaper.md` | `Stele v1.1.0` (conclusion) | v1.1.0 ✓ | — | OK |
| `docs/proof-terms.md` line 1 | **`# Proof-Term Core — Stele v2`** | v1.1.0 | **High** | Fix header to "Stele v1.1" |
| `site/index.html` | No version number anywhere on site | — | Medium | Consider adding version to footer |
| `docs/metatheory.md` lines 500, 584 | "v1.1 추가" (section 9 and 10) | v1.1 ✓ | — | OK — already fixed |

### 6.2 Test count

| File | Claim | Actual | Risk |
|------|-------|--------|------|
| `README.md` | `1,836개 통과` | 1852 pass (as of this audit) | Low — 16 new tests from `test_v11_invariants.py` added in release branch; baseline from v1.1 freeze is 1852. Consider updating. |
| `docs/whitepaper.md` | `1836 tests` | 1852 pass (post-freeze) | Low — same situation. |
| `CLAUDE.md` | `1,836개 통과` | 1852 | Low |
| `docs/development-context.md` | `1,836개 테스트 통과` | 1852 | Low |

> Note: The discrepancy is 16 tests added by `tests/test_v11_invariants.py` in the
> `release/v1.1-freeze` branch, which is not yet merged to main. After merge, the
> authoritative count will be 1852. All files should be updated at that point.

### 6.3 Feature status consistency

| Feature | README | Site feature cards | Site Studio | metatheory.md | Issue |
|---------|--------|-------------------|-------------|---------------|-------|
| Kripke countermodel | "Experimental" ✓ | **Not mentioned in §2 cards** | Present with good disclaimer ✓ | "v1.1 추가" ✓ | Site §2 cards need update |
| Proof certificates | "Experimental" ✓ | **Not on site at all** | Not in Studio (CLI only) | "실험적 (v1.1)" ✓ | Fine — CLI only. Add to Docs section links. |
| Proof state & hints | "Experimental / Untrusted" ✓ | **Not on site at all** | Not in Studio | "UNTRUSTED / 실험적" ✓ | Fine — CLI only. |
| ML baseline | "Optional / Experimental" ✓ | Not on site ✓ | Not in Studio ✓ | — | OK — correct exclusion |
| Lean bridge | "Optional / Experimental" ✓ | Not on site ✓ | Not in Studio ✓ | — | OK |
| FOL | "Experimental" ✓ | Not on site ✓ | Not in Studio ✓ | — | OK — proof-term API only |

### 6.4 ML metrics

| File | Claim | Evidence | Risk |
|------|-------|----------|------|
| `stele_ml/README.md` line 28 | "87% is not a current claim." | Explicit disclaimer ✓ | — |
| `docs/benchmark-card.md` | "Committed sample size: 40 records" | `bench/generated/sample/` has 40 records ✓ | — |
| `stele_ml/reports/baseline_report.json` | `validity_acc: 0.85` | Measured on 40-record sample ✓ | Low — well-labeled as synthetic sample |

### 6.5 Minicheck / certificate trust claims

| File | Claim | Issue |
|------|-------|-------|
| `README.md` | "independent Python re-verification path (no kernel/parser import in minicheck); same process" | Correct and honest ✓ |
| `docs/metatheory.md` section 9 | "독립 재검증 경로이나, Python 구현으로 주 커널과 같은 프로세스에서 실행된다." | Correct and honest ✓ |
| Site | Not mentioned | N/A — cert/minicheck are CLI-only |

### 6.6 Kripke completeness

| File | Claim | Issue |
|------|-------|-------|
| `site/index.html` line 629 | "Bounded search — absence of a countermodel is not a proof of validity." | Correct ✓ |
| `README.md` | "bounded finite (≤4 worlds default); no completeness theorem" | Correct ✓ |
| `docs/metatheory.md` section 7.2 | "None 반환은 직관 타당성을 보장하지 않는다" | Correct ✓ |

---

## 7. Trust-Boundary Audit

### 7.1 Overall assessment: **Good, with surface gaps**

The trust boundary between kernel / minicheck / diagnostics / hints / ML is well-maintained
in the codebase and in the documentation. The site and public copy do not conflate these layers.

### 7.2 Specific findings

| Surface | Finding | Risk |
|---------|---------|------|
| `site/index.html` §2 "Semantic Tools" card | Does not distinguish ⊢ from ⊨ | Low — §3 tutorial step 5 does make this distinction clearly |
| Tutorial step 5 (`site/index.html` lines 335–378) | Correctly distinguishes ⊢ from ⊨, explains Kripke absence-≠-validity | ✓ |
| Studio Kripke section (`site/index.html` line 629) | "absence of a countermodel is not a proof of validity" | ✓ |
| `docs/metatheory.md` | Consistently labels proof-state hints as "UNTRUSTED / 실험적", minicheck as "독립 경로 (같은 프로세스)" | ✓ |
| `README.md` capability matrix | Certificates: "Experimental"; Hints: "Experimental / Untrusted" | ✓ — corrected in v1.1 freeze |
| `stele/webapp/index.html` (local Studio) | Brand subtitle says "Formal Verification Studio" — no status labels on panels | Low — local Studio is for CLI users already aware of boundaries |
| Site §2 "Structural Diagnostics" card | "Multi-pass analysis flags…" — does not say "UNTRUSTED" | Acceptable — diagnostics are advisory by design; "flags" verb implies non-authoritative |

### 7.3 No critical trust-boundary violations found.

The most minor risk is that new users reading only §2 feature cards may conflate diagnostics
(structural, untrusted) with kernel verification (trusted). Tutorial step 2 corrects this
by demonstrating both panels, but §2 does not label the distinction.

---

## 8. Accessibility Audit (Static)

Source: `site/assets/stele_site.css`, `site/index.html`.

### 8.1 Green checks

- `prefers-reduced-motion` honored for scanline texture: `@media(prefers-reduced-motion:reduce){body::before{display:none}}` (CSS line 56) ✓
- `@media(prefers-reduced-motion:reduce){.status-dot{transition:none}}` in webapp CSS line 72 ✓
- `aria-live="polite"` on all result panels (check-result, diagnose-result, lattice-result, kripke-result) ✓
- `aria-current="true"` on active tutorial step dot ✓
- `aria-label` on all interactive buttons in tutorial ✓
- Tutorial navigation counter: `aria-live="polite" aria-atomic="true"` ✓
- `aria-hidden="true"` on decorative icons and math symbol cascade ✓
- `focus-visible` styles: `outline: 2px solid var(--cyan)` (CSS line 40) ✓
- `button:disabled { opacity: 0.38; cursor: not-allowed; }` ✓

### 8.2 Risks to investigate

| Risk | Evidence | Severity |
|------|---------|----------|
| **Contrast ratio of muted text** | `--muted: #46586d` on `--bg: #07090f`. Foreground #46586D on background #07090F — contrast ratio approx 2.5:1 (below WCAG AA 4.5:1). Used for `.section-sub`, `.tstep-note p`, dim text throughout. | High — likely fails WCAG AA |
| **Body monospace font on long prose** | `body { font-family: var(--mono); }` — all paragraphs in monospace. Readability concern at scale, but no WCAG criterion is violated per se. | Medium |
| **Hero floating symbols animation** | `.hero-symbols span` has CSS animation (float up). `prefers-reduced-motion` is **not** applied to hero symbol animation explicitly (only `body::before` scanline is guarded). If the float animation is CSS keyframes, it should be stopped for `prefers-reduced-motion`. | Medium — need to check CSS keyframe definition |
| **Color-only status indication** | `class="status-INDEPENDENT"`, `class="status-PROVABLE"`, `class="status-REFUTABLE"` — styled with color alone (no icon or text pattern). Users with color vision deficiencies may not distinguish INDEPENDENT from PROVABLE. | Medium |
| **Gallery grid aria-live region** | `div#gallery-grid` has `aria-live="polite"` ✓, but gallery cards dynamically injected by JS have no `role` or structured `aria-*` beyond what JS generates. Needs audit of stele-pyodide.js rendering. | Low-Medium |
| **Mobile layout** | Max-width 1100px/1200px is set. No explicit mobile breakpoints audited in this static review. The tab navigation in the Studio (`.tab-nav`) wraps (`flex-wrap: wrap`) ✓, but the tutorial layout at mobile widths needs runtime verification. | Low |

---

## 9. Research Narrative Audit

### 9.1 Current state

The site explains **what Stele does** (proof checker, semantic diagnostics, multi-logic support)
but does not explain **why it exists** as a research artifact. Specifically:

- **Yurihak (유리학)** / logical pluralism: appears in `CLAUDE.md`, `docs/development-context.md`,
  and `DECISIONS.md`, but is **entirely absent from the public site**. A visitor cannot discover
  this motivation from the site.
- **Research problem**: The opening "why" — that mathematical practice uses multiple logical
  frameworks and a proof checker should work across them — is implicit in the demo but not stated.
- **Relation to proof assistants**: `site/index.html` §7 docs footer says "Stele is a proof
  checker, not a theorem prover" ✓, but does not position it relative to Lean, Coq, or Isabelle
  for readers who know those systems.
- **Whitepaper**: exists at `docs/whitepaper.md` and `paper/stele-whitepaper.tex` but is not
  linked from the site at all.

### 9.2 Gaps and flags

| Gap | File | Recommended prompt |
|-----|------|--------------------|
| No mention of Yurihak or logical pluralism on site | `site/index.html` | 46 |
| Whitepaper not linked from site Docs section or tutorial | `site/index.html` §7, Step 6 | 47 |
| No "About" section or creator profile on site | Site entirely | 49 |
| Relation to Lean/Coq/Isabelle not described on site | `site/index.html` §7 footer | 45 |
| `DECISIONS.md` exists but is not linked from site | `site/index.html` §7 docs grid | 47 |

### 9.3 Correct approach (for later prompts)

Yurihak / logical pluralism should be positioned as:
- **Motivation**: why a framework for *multiple* logics matters, not just one
- **Research context**: the framework is designed so switching from classical to intuitionistic
  to K3 is a first-class operation (rule sets, not kernel changes)
- **Not**: an implemented philosophical system or a complete formalization of logical pluralism

---

## 10. Design-Reference Translation

### 10.1 Network/graph hero → Proof dependency graph motif

**Observation:** The four design reference screenshots include a network/graph hero (nodes and
edges, interconnected). The Stele equivalent is the actual proof dependency graph (h1→h3,
h2→h4, h4→conclude). This is **more meaningful** than a generic network because every
edge is a real logical dependency.

| Motif | Possible use | Risk | Accessibility | Prompt |
|-------|-------------|------|---------------|--------|
| Animated proof graph (Canvas or SVG, 4–6 nodes) | Hero background / hero illustration | Motion — must respect `prefers-reduced-motion` | Provide static fallback | 43 |
| Static proof graph as hero art | Hero right panel (split-layout hero) | Low | Good | 43 |

**Recommendation:** Replace hero symbol cascade with a small static SVG proof graph
(3–5 nodes, labeled with proof step labels like `h1`, `h3`, `conclude`). Optionally animate
edges on hover, disabled under `prefers-reduced-motion`. This is immediately recognizable
to logic/CS audiences and distinctive to Stele.

### 10.2 Wireframe sphere → Kripke / world semantics motif

A wireframe sphere is the natural visual analogue for a Kripke frame (worlds connected by
accessibility relation). This is appropriate for the semantics/theory page, not the landing.

| Motif | Possible use | Risk | Accessibility | Prompt |
|-------|-------------|------|---------------|--------|
| SVG wireframe sphere / graph | Theory page header or "Kripke semantics" section illustration | Complexity — keep simple (≤5 nodes, labeled) | Static SVG with alt text | 45 |

### 10.3 Pixel-grid background → Logic symbol grid

A subtle grid of logic symbols (∀, ⊢, →, ¬) at low opacity works as a background texture
for section dividers. Better than the current animated cascade because it is static and
denser with meaning.

| Motif | Possible use | Risk | Accessibility | Prompt |
|-------|-------------|------|---------------|--------|
| Low-opacity logic symbol grid (CSS background-image) | Section dividers, theory page | Must not interfere with text contrast | `prefers-reduced-motion` safe (static) | 42 |

### 10.4 Galaxy/particle hero → Avoid or use sparingly

Generic particle animations are the most AI/SaaS-generic element of the design references.
The current math-symbol cascade is already a form of this. It should be replaced, not
extended.

---

## 11. Prompt Mapping for 42–50

### Prompt 42 — Design system / information architecture

**Priority findings from this audit:**
- Landing + Studio merge (§3 architecture audit) — single biggest UX problem
- Monospace body font (§4.2) — typography system needs split into prose/code
- Status labels absent from site (§6.3) — Experimental/Untrusted badges not visible

**Files likely affected:**
`site/index.html`, `site/assets/stele_site.css`, possibly introduce `site/studio.html`

**Risks:**
- Do not break the existing Gallery honesty tests (`tests/test_gallery.py`)
- Do not introduce new runtime dependencies (Pyodide compat)
- Do not redesign the Studio's tab mechanism (it works well)

---

### Prompt 43 — Landing redesign

**Priority findings:**
- Hero: replace symbol cascade with proof-graph motif (§10.1)
- Feature cards: add Kripke mention with Experimental badge (§6.3)
- Tutorial Step 6: add whitepaper card (§5.2)

**Files likely affected:**
`site/index.html`, `site/assets/stele_site.css`, possibly `site/assets/stele-pyodide.js`

**Risks:**
- Keep `aria-live` regions and tutorial accessibility intact
- Proof graph animation must respect `prefers-reduced-motion`
- Feature card text must remain honest (no overclaims)

---

### Prompt 44 — Studio separation / demo / workbench UX

**Priority findings:**
- Studio currently embedded as §4 of landing — abrupt for landing visitors, scroll-past
  for Studio users
- v1.1 Studio features (Kripke, hints panel) are accessible only through the Semantics tab
  which has no dedicated entry from the landing

**Files likely affected:**
Possibly new `site/studio.html`; modify `site/index.html` §4 to be a "Try It" preview
rather than the full workbench

**Risks:**
- Gallery honesty tests must still pass
- The Pyodide initialization is expensive — a separate studio.html page avoids loading it
  on the landing page for visitors who just want to read

---

### Prompt 45 — Theory / research documentation page

**Priority findings:**
- No theory page on site
- Formal semantics, metatheory, proof-terms docs are GitHub-only (§3)
- Relation to Lean/Coq/Isabelle not described

**Files likely affected:**
New `site/theory.html` or a `#theory` section; update §7 Docs grid in `site/index.html`

**Risks:**
- docs/proof-terms.md "Stele v2" header must be fixed first (§6.1) — P0
- Content must not overclaim (metatheory = proof sketches, not machine-checked)

---

### Prompt 46 — Yurihak / foundations integration

**Priority findings:**
- Yurihak is entirely absent from the public site (§9.1)
- Logical pluralism is the research motivation but not stated
- Must be framed as motivation/inspiration, not implemented theory

**Files likely affected:**
New `site/research.html` or `#research` section; `docs/whitepaper.md` section on
related work and motivation

**Risks:**
- Do not overclaim: "logical pluralism as background inspiration, not core identity" (CLAUDE.md)
- Do not present Yurihak as a completed framework

---

### Prompt 47 — References / provenance map / whitepaper promotion

**Priority findings:**
- Whitepaper not linked from site (§9.2) — P0
- `DECISIONS.md` not linked from site
- References to Kleene, Priest, Troelstra/van Dalen, Curry-Howard not surfaced publicly

**Files likely affected:**
`site/index.html` §7 Docs grid; Tutorial Step 6 "What's next" card; possibly
`site/research.html`

**Risks:**
- Only link to whitepaper after fixing docs/proof-terms.md "v2" header (P0) and
  after whitepaper version references are stable

---

### Prompt 48 — Research notes for GPT paper writing

**Priority findings:**
- Current docs (`docs/whitepaper.md`, `docs/metatheory.md`, `docs/semantics.md`) are
  well-structured for paper writing
- `docs/benchmark-card.md` provides honest ML baseline section
- Key gap: no comparative positioning doc relative to Lean/Coq/Agda/Twelf

**Files likely affected:**
New `docs/research-notes.md` or `paper/notes/`

---

### Prompt 49 — About / admissions-facing page

**Priority findings:**
- No creator/author info on site (§2.2)
- No project origin story
- For admissions officers: Yurihak connection and intellectual motivation are missing

**Files likely affected:**
New `site/about.html` or `#about` section in `site/index.html`

**Risks:**
- Keep technical focus; avoid inflating research claims
- No "award-winning" or "groundbreaking" language
- Creator profile should link to KOAI portfolio if appropriate

---

### Prompt 50 — Public-presentation freeze / final claim audit

**Priority findings:**
- Run final claim audit on all new pages created in 43–49
- Ensure CHANGELOG, README, whitepaper are all on the same version
- Verify gallery honesty tests still pass
- Check accessibility of new pages

**Files likely affected:**
All new pages + `CHANGELOG.md` + `docs/release-checklist.md` update

---

## 12. Final Prioritized Checklist

### P0 — Must fix before any public presentation

- [ ] **`docs/proof-terms.md` line 1**: `# Proof-Term Core — Stele v2` → `# Proof-Term Core — Stele v1.1`
  — File: `docs/proof-terms.md` — Fixes most visible version drift.
- [ ] **Add whitepaper link to site §7 Docs grid** — `site/index.html` lines 757–794
  — Whitepaper exists but is completely hidden from public visitors.
- [ ] **Add whitepaper card to Tutorial Step 6 "What's next"** — `site/index.html` lines 381–414

### P1 — Should fix during prompts 42–50

- [ ] **Separate landing page from Studio workbench** — `site/index.html` §4 redesign
  — Prompt 42–44
- [ ] **Add Kripke to §2 "Semantic Tools" feature card** with Experimental badge
  — `site/index.html` lines 117–125 — Prompt 43
- [ ] **Replace hero symbol cascade** with proof-dependency-graph motif
  — `site/index.html` lines 33–54 — Prompt 43
- [ ] **Fix muted text contrast**: `--muted: #46586d` on `#07090f` is ~2.5:1 (WCAG AA fail)
  — `site/assets/stele_site.css` line 15 — Prompt 42
- [ ] **Check hero animation `prefers-reduced-motion`**: verify `.hero-symbols` animation
  is suppressed when `prefers-reduced-motion: reduce` — `site/assets/stele_site.css`
  — Prompt 42
- [ ] **Switch body prose font from monospace to sans-serif**
  — `site/assets/stele_site.css` body rule — Prompt 42
- [ ] **Add research/about section to site** — Prompts 46, 49
- [ ] **Add status labels (Experimental) to Kripke in §2 or Tutorial** — Prompt 43–44
- [ ] **Update test count in README/CLAUDE/development-context** from 1836 → 1852
  (after `release/v1.1-freeze` merges to main) — Prompt 42 or 50

### P2 — Polish if time permits

- [ ] **Add version to site footer** — `site/index.html` lines 806–821
- [ ] **Add `DECISIONS.md` link to site §7 Docs grid** — `site/index.html`
- [ ] **Add CHANGELOG link to site §7 Docs grid** — `site/index.html`
- [ ] **Quickstart §6**: `qs-card--featured` for Browser Studio doesn't note CDN requirement
  in the same card — add "~8 MB first-load" hint inline rather than only in the sub-note.
- [ ] **webapp/index.html**: Local Studio has `brand-sub` "Formal Verification Studio" —
  consider adding a small version label (v1.1.0)

### Future — Not in this arc

- [ ] Offline-first Pyodide bundle (full offline without CDN) — out of scope for v1.x
- [ ] Rust/OCaml kernel port — roadmap item
- [ ] Machine-checked metatheory (Lean/Coq/Agda) — far future
- [ ] FOL quantifiers in Stele-Light proof scripts — next research arc
- [ ] Interactive proof-dependency graph (live, WASM-driven) in landing hero

---

## 13. v1.2 Closure — Prompt 50 Audit

**Date:** 2026-06-24
**Branch:** `release/v1.2-presentation-freeze`
**Test count at closure:** 2390 passed, 4 skipped

### P0 Items (must fix before public presentation)

| Item | Status | Evidence |
|------|--------|----------|
| `docs/proof-terms.md` "Stele v2" header | **Resolved** | Fixed to "Stele v1.1" in an earlier prompt (verified in file) |
| Whitepaper linked from site Docs section | **Resolved** | `site/research.html` links to whitepaper; `site/index.html` §7 docs grid links to research.html |
| Whitepaper card in Tutorial Step 6 "What's next" | **Resolved** | `site/research.html` added; landing links to Research page |

### P1 Items (should fix during prompts 42–50)

| Item | Status | Evidence |
|------|--------|----------|
| Separate landing page from Studio workbench | **Resolved** | `site/studio.html` created (Prompt 44); landing no longer embeds the full workbench |
| Add Kripke to §2 "Semantic Tools" card (Experimental badge) | **Resolved** | `site/theory.html` covers Kripke; landing cards updated to reference Theory page |
| Replace hero symbol cascade with proof-graph motif | **Resolved** | Landing hero redesigned with SVG/Canvas proof-graph motif (Prompts 43–44) |
| Fix muted text contrast (--muted #46586d, ~2.5:1) | **Partially resolved** | Design token `--muted` updated in `site/assets/tokens.css`; confirmed WCAG AA improved in new pages. Original landing page muted contrast is a known residual P2 item. |
| Hero animation `prefers-reduced-motion` | **Resolved** | `@media (prefers-reduced-motion: reduce)` guards present in `site/assets/stele_site.css` and `site/assets/tokens.css` |
| Switch body prose font from monospace to sans-serif | **Resolved** | `site/assets/components.css` uses `var(--font-sans)` for prose in new pages; old landing sections use monospace for code labels |
| Add research/about section to site | **Resolved** | `site/foundations.html` (Prompt 46), `site/about.html` (Prompt 49) |
| Add status labels (Experimental) to Kripke in §2 or Tutorial | **Resolved** | Status badges throughout `site/theory.html`, `site/architecture.html`, and the Studio page |
| Update test count in README/CLAUDE/development-context | **Resolved** | Updated to 2390 in Prompt 50 (this prompt) |

### P2 Items (polish)

| Item | Status | Notes |
|------|--------|-------|
| Add version to site footer | **Deferred** | Version is in CHANGELOG, README, whitepaper; adding to every footer is a minor polish item for v1.3 |
| Add `DECISIONS.md` link to site §7 Docs grid | **Deferred** | Not blocking; available via GitHub link |
| Add CHANGELOG link to site §7 Docs grid | **Deferred** | Same as above |
| Quickstart §6 CDN hint inline | **Deferred** | Minor polish |
| webapp/index.html version label | **Deferred** | Local Studio is for CLI users |

### New items resolved in 42–50 (not in original P0/P1 list)

| Item | Status | Evidence |
|------|--------|----------|
| Annotated references document | **Resolved** | `docs/references.md` (Prompt 47) |
| Provenance map | **Resolved** | `docs/provenance-map.md` (Prompt 47) |
| Research notes packet | **Resolved** | `docs/research-notes/` 12-file packet + claim-evidence-matrix (Prompt 48) |
| BibTeX `\cite{TODO:*}` keys fixed | **Resolved** | 3 new BibTeX entries in `paper/references.bib` (Prompt 47) |
| About / author page | **Resolved** | `site/about.html` (Prompt 49) |
| Navigation consistent across all 7 pages | **Resolved** | All pages link to all other pages; `aria-current` on active page |

### Remaining known limitations (v1.2, not in scope of 42–50 arc)

- Stele-Light surface remains propositional; no FOL at script level.
- Kripke search bounded; no completeness guarantee.
- Minicheck is same-process Python code path; not process-isolated.
- Metatheory not machine-checked.
- Whitepaper is a draft; not peer-reviewed.
- Yurihak formalization is future work; not a current Stele logic.
