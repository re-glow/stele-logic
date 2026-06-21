"""diagnostic_errors corpus: one dedicated pattern per supported diagnostic code.

Cycles through 6 patterns deterministically so that every n=6 examples covers
all diagnostic codes exactly once.

Codes covered (surface-triggerable in v1):
  UndefinedSymbol, MissingHypothesis, UnsupportedConclusion,
  InvalidTransition, UndefinedDefinition, UnusedAssumption

Codes NOT included (no surface trigger or not naturally representable):
  TypeMismatch         — v1 grammar has no term language
  CircularDependency   — parser sequential model prevents natural cycles;
                         tested at the unit level via synthetic ProofGraph objects
"""
from itertools import permutations

CORPUS_NAME = "diagnostic_errors"
GENERATOR_VERSION = 1
PROP_VARS = ["P", "Q", "R"]

# One entry per diagnostic code.
# (text_fn(a, b, c, idx, logic), expected_valid, expected_codes, tags)
_PATTERNS = [
    # 0: UndefinedSymbol — mp cites 'phantom' which does not exist
    (
        lambda a, b, c, i, lg: (
            f"theorem diag_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  have h2: {b} by mp h1 phantom\n"
            f"  conclude {b} by h2\n"
        ),
        False, ["UndefinedSymbol"], ["UndefinedSymbol"],
    ),
    # 1: MissingHypothesis — h3 used before it is declared
    (
        lambda a, b, c, i, lg: (
            f"theorem diag_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  have h2: {b} by mp h1 h3\n"
            f"  assume h3: {a}\n"
            f"  conclude {b} by h2\n"
        ),
        False, ["MissingHypothesis"], ["MissingHypothesis"],
    ),
    # 2: UnsupportedConclusion — conclude formula does not match the referenced label
    (
        lambda a, b, c, i, lg: (
            f"theorem diag_{i:06d} using {lg}:\n"
            f"  assume h1: {a}\n"
            f"  conclude {b} by h1\n"
        ),
        False, ["UnsupportedConclusion"], ["UnsupportedConclusion"],
    ),
    # 3: InvalidTransition — mp second premise has wrong type
    (
        lambda a, b, c, i, lg: (
            f"theorem diag_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  assume h2: {a} and {c}\n"
            f"  have h3: {b} by mp h1 h2\n"
            f"  conclude {b} by h3\n"
        ),
        False, ["InvalidTransition"], ["InvalidTransition"],
    ),
    # 4: UndefinedDefinition — definition body refs undefined name
    (
        lambda a, b, c, i, lg: (
            f"definition UNDEF_NAME_{i:06d} := UNDEF_REF_{i:06d} -> {a}\n\n"
            f"theorem diag_{i:06d}:\n"
            f"  assume h: {a}\n"
            f"  conclude {a} by h\n"
        ),
        True, ["UndefinedDefinition"], ["UndefinedDefinition"],
    ),
    # 5: UnusedAssumption — h2 declared but never used (proof still valid)
    (
        lambda a, b, c, i, lg: (
            f"theorem diag_{i:06d} using {lg}:\n"
            f"  assume h1: {a}\n"
            f"  assume h2: {b}\n"
            f"  conclude {a} by h1\n"
        ),
        True, ["UnusedAssumption"], ["UnusedAssumption"],
    ),
]

N_PATTERNS = len(_PATTERNS)
_PERMS = list(permutations(PROP_VARS))


def generate(n, rng, start_id=0):
    """Generate n diagnostic_errors records, cycling through all 6 patterns."""
    records = []
    for i in range(n):
        idx = start_id + i
        a, b, c = _PERMS[rng.randrange(len(_PERMS))]
        logic = "intuitionistic_prop"

        # Deterministic cycle: pattern index depends only on i, not on rng
        pattern_idx = i % N_PATTERNS
        fn, m_valid, m_codes, m_tags = _PATTERNS[pattern_idx]

        records.append({
            "id": f"{CORPUS_NAME}_{idx:06d}",
            "corpus": CORPUS_NAME,
            "text": fn(a, b, c, idx, logic),
            "logic": logic,
            "expected_valid": m_valid,
            "expected_codes": m_codes,
            "tags": m_tags,
            "metadata": {
                "generator_version": GENERATOR_VERSION,
                "pattern_index": pattern_idx,
                "mutation": m_codes[0] if m_codes else None,
            },
        })

    return records
