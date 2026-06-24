# 07 — Certificates and Minicheck

**Status:** Experimental
**Evidence:** `stele/certificate.py`, `stele/minicheck.py`
**Doc:** `docs/metatheory.md §7`, `docs/development-context.md §2`
**Tests:** `tests/test_minicheck.py` (tamper-detection, cross-validation)

---

## 7.1 Motivation

A proof certificate is a machine-readable artifact that summarizes a verified proof
in a form that a separate, lightweight checker can re-verify — without re-running the
full parser and kernel.

The design goal is: even if the certificate emitter has a bug, the minicheck provides
an independent verification path.

This design pattern is well-established in the proof-assistant literature.
See Harper, Honsell & Plotkin, "A Framework for Defining Logics", JACM 40(1), 1993
[HarperHP1993] for the LF tradition.

**Important limitation:** Stele's certificate mechanism provides **same-process, code-level**
isolation. It is not process-level or language-level isolation. The minicheck and the
kernel run in the same Python interpreter.

---

## 7.2 Certificate format

**Module:** `stele/certificate.py`

A Stele certificate is a versioned JSON document:

```json
{
  "version": "1.0",
  "theorem_name": "dne_consequent",
  "logic": "classical_prop",
  "conclusion": "P",
  "steps": [
    {
      "label": "h1",
      "formula": "not not P",
      "rule": "assume",
      "premises": []
    },
    {
      "label": "h2",
      "formula": "P",
      "rule": "dne",
      "premises": ["h1"]
    }
  ],
  "verified": true,
  "timestamp": "..."
}
```

**Emission condition:** A certificate is only emitted if `kernel.check_proof()` returns
`True`. The kernel result gates the certificate emission.

**CLI:** `python -m stele.cli cert examples/dne.stele --logic classical_prop`

---

## 7.3 Minicheck re-verifier

**Module:** `stele/minicheck.py`

The minicheck:

- Reads a certificate JSON document
- Reconstructs a minimal rule-matching check using its own rule table
- Reports PASS or FAIL independently of the main kernel

**Import isolation:** `stele/minicheck.py` does NOT import:
- `stele.kernel`
- `stele.parser`
- `stele.diagnostics`
- `stele.proof`

It imports only:
- `stele.ast` (formula AST, shared)
- `stele.certificate` (certificate data structures)
- Python stdlib

**Why this matters:** If `kernel.py` has a bug that causes it to both accept an invalid
proof AND emit a certificate for it, the minicheck provides an independent check. The
minicheck has its own rule table (smaller, simpler) and its own matching logic.

**Test:** `tests/test_minicheck.py` includes:
- Cross-validation: proofs verified by kernel are also accepted by minicheck
- Tamper detection: certificates with modified steps/formulas are rejected by minicheck
- Import isolation: verified that minicheck does not import kernel at module load time

---

## 7.4 What the minicheck does not guarantee

- **Not formally verified.** The minicheck has not been machine-checked.
- **Same process.** A runtime-level attack (e.g., monkey-patching `stele.ast`) could
  compromise both kernel and minicheck simultaneously.
- **Same language.** Both are Python. A Python implementation bug affecting the shared
  AST layer would affect both.
- **Not independently developed.** The minicheck was written alongside the kernel by the
  same author. It is not an independent implementation.

**Future work:** Porting minicheck to Rust or OCaml would provide stronger isolation
guarantees. This is on the roadmap but not implemented.

---

## 7.5 Paper wording

**Safe:** "The minicheck provides an independent software check at the code level,
re-verifying certificate steps without importing the main kernel."

**Unsafe:** "The certificate system provides formal verification" or "independently
verified" (implies formal verification).
