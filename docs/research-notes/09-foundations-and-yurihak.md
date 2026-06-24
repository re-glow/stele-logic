# 09 — Foundations and Yurihak Research Program

**Status:** Motivation (not implemented)
**Evidence:** `site/foundations.html`, `docs/foundations-program.md`
**Doc:** `docs/references.md §3`, `docs/provenance-map.md Table 1`
**Tests:** `tests/test_foundations.py`

---

## 9.1 What Yurihak (유리학) is

Yurihak (유리학) is the author's personal foundational research program that motivates
Stele's multi-logic architecture.

The central idea — as described in the public facing text and research program documents —
is that **logical rules are relative** to a chosen rule set, not absolute. The same
formula can be valid under one logic (e.g., classical) and invalid under another
(e.g., intuitionistic), and this is a technical fact about rule sets rather than a
philosophical claim about truth.

**What Yurihak is in Stele:**
- **Research motivation** for the `--logic` flag and `RuleSchema` data architecture
- **Research motivation** for the multi-matrix semantic layer
- **Background inspiration** for the `World` and `lattice_status` design

**What Yurihak is NOT in Stele:**
- Not a formal Stele logic (no `yurihak` logic object in `stele/logic.py`)
- Not a rule set (no `RuleSchema` objects defining Yurihak rules)
- Not a proof system (no `examples/yurihak_*.stele` files)
- Not a formalized mathematical system anywhere in the codebase

**Critical claim discipline:** Papers about Stele must not claim "Stele implements
Yurihak" or "Stele proves Yurihak's claims." These are false.

---

## 9.2 Connected foundational papers

Four papers form the personal research line. They are local drafting references not
committed to the public repository. Summaries are based on filenames and project
context only — PDF contents were not extracted in this session.

| Title | File | Connection to Stele | Status |
|-------|------|---------------------|--------|
| 유리학개론 / Introduction to Yurihak | `yurihak-introduction.pdf` | Primary theoretical motivation for multi-logic architecture | PDF local, not committed |
| Window-Localized | `window-localized.pdf` | Conceptual influence on world-based semantics | PDF local, not committed |
| Closure Atlases | `closure-atlases.pdf` | Potential influence on world-lattice composition | PDF local, not committed |
| Bounded Cores | `bounded-cores.pdf` | Parallel with bounded Kripke frame search | PDF local, not committed |

**Policy:** Do not summarize content from unavailable PDFs. The above descriptions are
taken from `docs/foundations-program.md` and `docs/references.md §3`.

---

## 9.3 What is actually implemented vs motivated

| Feature | Motivated by Yurihak? | Implemented? | Where |
|---------|----------------------|-------------|-------|
| `--logic` flag | Yes | Yes | `stele/cli.py`, `stele/logic.py` |
| Multiple rule sets | Yes | Yes | `stele/logic.py` (5 logics) |
| K3/LP matrix semantics | Yes (many-valued logic tradition) | Yes (Demo) | `stele/matrix.py` |
| World/lattice demo | Yes | Yes (Demo) | `stele/world.py` |
| Rule relativity demonstration | Yes | Yes | `RESULTS.md` §상대성 |
| Yurihak as a formal logic | Yes (future) | No | — |
| Window-localized semantics | Yes (future) | No | — |
| Closure atlas structures | Yes (future) | No | — |
| Bounded core theory | Yes (future) | No | — |

---

## 9.4 Safe framing for the paper

**Correct framing:**

> The Yurihak research program motivates Stele's multi-logic architecture. Stele
> demonstrates that logical validity is relative to the chosen rule set: the same formula
> can be provable under classical logic but not intuitionistic logic, and this is
> implemented as a runtime rule-set selection. Stele does not implement Yurihak as a
> formal system; Yurihak's full formalization is a planned future direction.

**Incorrect framing:**

> ~~Stele implements Yurihak.~~
> ~~Stele proves that logic is relative.~~
> ~~Stele is based on Yurihak.~~

---

## 9.5 Positioning in related work

In the related work section of a paper, Yurihak should be positioned as:

- A **personal foundational research program** by the author
- Distinct from logical pluralism in analytic philosophy (Beall & Restall, Graham Priest)
- Distinct from paraconsistency as a formal discipline (Priest's LP is in the matrix
  layer, not as a Yurihak logic)
- The **inspiration** for multi-logic architecture, not the system itself

**Relation to implemented logics:**
- `intuitionistic_prop`: standard IPL, not Yurihak
- `classical_prop`: standard CPC, not Yurihak
- `K3`: strong Kleene, based on Kleene 1952 [Kleene1952], not Yurihak
- `LP`: Logic of Paradox, based on Priest 1979 [Priest1979], not Yurihak
- `boolean`: standard Boolean, not Yurihak
