-- Example: intentionally invalid Lean file (type error)
-- This file demonstrates the kind of type error stele_lean can detect.
--
-- The theorem claims h : P proves Q, which is a type mismatch.
-- Running: lean type_error.lean  should produce:
--   type_error.lean:14:8: error: type mismatch
--     term
--       h
--     has type
--       P : Prop
--     but is expected to have type
--       Q : Prop

variable (P Q : Prop)

theorem wrong_conclusion : P → Q := by
  intro h
  exact h   -- type error: h : P, expected Q
