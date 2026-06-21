"""stele_lean — optional Lean 4 bridge for the Stele proof-verification system.

This package is isolated from the trusted stele/ core:
  - stele/ MUST NOT import stele_lean (enforced by tests)
  - Lean 4 must be installed separately; it is NOT a Python dependency
  - If Lean is not on PATH, all Lean-dependent operations skip cleanly
  - No Mathlib dependency in v1

Supported fragment (v1):
  Propositional logic: Var (→ Prop), →, ∧, ∨, ¬, False

Not supported in v1:
  K3 / LP / matrix semantics, paraconsistent worlds, first-order logic,
  dependent types beyond Lean's own elaboration, Mathlib constructs,
  full proof body translation (uses 'sorry' placeholder).
"""
__version__ = "0.1.0"
SUPPORTED_OPS = frozenset({"imp", "and", "or", "not", "bot"})
