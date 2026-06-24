# Stele — Research Notes Packet

**Purpose:** Source-of-truth dossier for drafting a stronger academic paper about Stele.
This packet captures implemented capabilities, evidence paths, examples, measured metrics,
limitations, and writing instructions. It is *not* a paper and *not* a final whitepaper.

**Branch:** `docs/research-notes`
**Companion docs:** [`docs/references.md`](../references.md), [`docs/provenance-map.md`](../provenance-map.md)
**Primary whitepaper source:** [`paper/stele-whitepaper.tex`](../../paper/stele-whitepaper.tex)

---

## Contents

| File | Topic |
|------|-------|
| [01-system-overview.md](01-system-overview.md) | Identity, problem statement, non-goals |
| [02-architecture-trust-boundary.md](02-architecture-trust-boundary.md) | Layered architecture, trust boundary, dependency policy |
| [03-language-and-kernel.md](03-language-and-kernel.md) | Stele-Light syntax, rule schemas, kernel operation |
| [04-proof-terms-and-elaboration.md](04-proof-terms-and-elaboration.md) | Curry–Howard core, bidirectional typing, elaboration |
| [05-diagnostics-and-proof-state.md](05-diagnostics-and-proof-state.md) | Structural diagnostics, diagnostic codes, proof-state hints |
| [06-semantics-matrix-kripke.md](06-semantics-matrix-kripke.md) | ⊢ vs ⊨, K3/LP/Boolean matrices, Kripke countermodels |
| [07-certificates-minicheck.md](07-certificates-minicheck.md) | Certificate emission, minicheck re-verifier |
| [08-ml-corpus-and-measurement.md](08-ml-corpus-and-measurement.md) | Optional ML baseline, corpus, measured metrics |
| [09-foundations-and-yurihak.md](09-foundations-and-yurihak.md) | Yurihak research motivation, implemented vs future |
| [10-related-work-and-provenance.md](10-related-work-and-provenance.md) | Proof assistants, Curry–Howard, Kripke, K3/LP, certs, ML |
| [11-limitations-and-future-work.md](11-limitations-and-future-work.md) | Current limitations and roadmap |
| [12-paper-outline-and-figure-plan.md](12-paper-outline-and-figure-plan.md) | Paper outline, figure plan, GPT writing instructions |
| [claim-evidence-matrix.md](claim-evidence-matrix.md) | Per-claim: status, evidence, safe/unsafe wording, limitation |

---

## Provenance policy

- Every major claim in these notes must cite a module path, doc path, test path, or example path.
- If a claim has no evidence path, it is labeled **Future** or **Speculative**.
- All quantitative values are taken from committed report files or test output — not estimated.
- PDFs under `references/incoming/` are local drafting references not committed to the repo.
  Content from those files is not used here.

---

## Status labels used throughout

| Label | Meaning |
|-------|---------|
| **Stable** | Implemented, tested, in CI |
| **Experimental** | Implemented but API unstable, caveats apply |
| **Optional** | Available as isolated add-on, not in core path |
| **Demo** | Works but intended for demonstration, not production use |
| **Untrusted** | Outside the trusted kernel; advisory only |
| **Motivation** | Inspires design but not yet implemented |
| **Future** | On roadmap; not yet implemented |
| **Speculative** | Possible future direction, not committed |

---

## How to use this packet for paper drafting

1. Read `01-system-overview.md` first to calibrate identity and non-goals.
2. Read `claim-evidence-matrix.md` before drafting any claim.
3. Follow the instructions in `12-paper-outline-and-figure-plan.md`.
4. For every citation, verify it appears in `paper/references.bib`.
5. Do not promote any **Motivation** or **Future** item to an implemented claim.
