-- Example: modus ponens skeleton exported by stele_lean v1
-- Corresponds to: theorem mp using classical_prop
--   assume h1: P -> Q
--   assume h2: P
--   have hq: Q by mp h1 h2
--   conclude Q by hq
--
-- Lean elaborates the TYPE successfully. The 'sorry' proof is a placeholder.

variable (P Q : Prop)

theorem mp : (P → Q) → P → Q := by
  exact sorry
