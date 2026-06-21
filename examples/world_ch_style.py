"""CH-style propositional independence pattern demo.

Shows how a single atom can be INDEPENDENT in a base world and resolved
(PROVABLE or REFUTABLE) by adding one axiom.

This is a TOY SEMANTIC INDEPENDENCE PATTERN — not real CH, not forcing,
not set-theoretic independence.  "CH-style" means only:
    Gamma  ⊭ x    and   Gamma  ⊭ ¬x      (independent)
    Gamma+x  ⊨ x                          (provable in the positive extension)
    Gamma+¬x ⊨ ¬x  →  Gamma+¬x  ⊭ x     (refutable in the negative extension)

All computation uses boolean matrix entailment; the Stele proof kernel is
never called.

Usage:
    python examples/world_ch_style.py
    python -m stele.cli lattice x
"""
from stele.parser import parse_formula
from stele.ast import Op, pretty
from stele.world import World, status, PROVABLE, REFUTABLE, INDEPENDENT

phi = parse_formula("x")
neg = Op("not", (phi,))

base     = World("boolean", ())
ext_pos  = World("boolean", (phi,))
ext_neg  = World("boolean", (neg,))

print("CH-style independence pattern for formula:", pretty(phi))
print()
print(f"  Gamma (no axioms)        => {status(phi, base)}")
print(f"  Gamma + {pretty(phi):<16}   => {status(phi, ext_pos)}")
print(f"  Gamma + {pretty(neg):<16}   => {status(phi, ext_neg)}")
print()
print("Same pattern with compound formula  P and Q:")
phi2 = parse_formula("P and Q")
neg2 = Op("not", (phi2,))
for label, w in [
    ("Gamma",             World("boolean", ())),
    (f"Gamma + P and Q", World("boolean", (phi2,))),
    (f"Gamma + not (P and Q)", World("boolean", (neg2,))),
]:
    print(f"  {label:<28} => {status(phi2, w)}")
