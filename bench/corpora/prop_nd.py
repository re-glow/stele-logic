"""prop_nd corpus: propositional natural-deduction proof tasks.

Generates valid proofs from 10 rule templates plus 7 controlled mutations
that each inject a specific diagnostic error code.  Prop variables are drawn
from PROP_VARS via seeded RNG so the corpus is fully deterministic.

Valid/invalid ratio is controlled by VALID_RATIO (0.5 by default).
"""
from itertools import permutations

CORPUS_NAME = "prop_nd"
GENERATOR_VERSION = 1
PROP_VARS = ["P", "Q", "R"]
VALID_RATIO = 0.5

# ---------------------------------------------------------------------------
# Valid proof templates
# Each entry: (text_fn(a, b, c, idx, logic) -> str, tags)
# ---------------------------------------------------------------------------

_VALID = [
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  assume h2: {a}\n"
            f"  have h3: {b} by mp h1 h2\n"
            f"  conclude {b} by h3\n"
        ),
        ["mp"],
    ),
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  assume h2: {b} -> {c}\n"
            f"  assume h3: {a}\n"
            f"  have h4: {b} by mp h1 h3\n"
            f"  have h5: {c} by mp h2 h4\n"
            f"  conclude {c} by h5\n"
        ),
        ["mp", "chain"],
    ),
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a}\n"
            f"  assume h2: {b}\n"
            f"  have h3: {a} and {b} by and_intro h1 h2\n"
            f"  conclude {a} and {b} by h3\n"
        ),
        ["and_intro"],
    ),
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} and {b}\n"
            f"  have h2: {a} by and_elim_left h1\n"
            f"  conclude {a} by h2\n"
        ),
        ["and_elim"],
    ),
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} and {b}\n"
            f"  have h2: {b} by and_elim_right h1\n"
            f"  conclude {b} by h2\n"
        ),
        ["and_elim"],
    ),
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a}\n"
            f"  have h2: {a} or {b} by or_intro_left h1\n"
            f"  conclude {a} or {b} by h2\n"
        ),
        ["or_intro"],
    ),
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {b}\n"
            f"  have h2: {a} or {b} by or_intro_right h1\n"
            f"  conclude {a} or {b} by h2\n"
        ),
        ["or_intro"],
    ),
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  suppose h1: {a}\n"
            f"    have h2: {a} by copy h1\n"
            f"  have h3: {a} -> {a} by imp_intro h1 h2\n"
            f"  conclude {a} -> {a} by h3\n"
        ),
        ["imp_intro"],
    ),
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a}\n"
            f"  assume h2: not {a}\n"
            f"  have h3: false by neg_elim h1 h2\n"
            f"  conclude false by h3\n"
        ),
        ["neg_elim"],
    ),
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: false\n"
            f"  have h2: {a} by ex_falso h1\n"
            f"  conclude {a} by h2\n"
        ),
        ["ex_falso"],
    ),
]

# ---------------------------------------------------------------------------
# Mutation templates
# Each entry: (text_fn(a, b, c, idx, logic) -> str, expected_valid, codes, tags)
# ---------------------------------------------------------------------------

_MUTATIONS = [
    # UndefinedSymbol — mp cites nonexistent 'missing'
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  have h3: {b} by mp h1 missing\n"
            f"  conclude {b} by h3\n"
        ),
        False, ["UndefinedSymbol"], ["UndefinedSymbol", "mp"],
    ),
    # UndefinedSymbol — copy from nonexistent 'ghost'
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  have h1: {a} by copy ghost\n"
            f"  conclude {a} by h1\n"
        ),
        False, ["UndefinedSymbol"], ["UndefinedSymbol", "copy"],
    ),
    # MissingHypothesis — forward reference (h2 used before declared)
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  have h3: {b} by mp h1 h2\n"
            f"  assume h2: {a}\n"
            f"  conclude {b} by h3\n"
        ),
        False, ["MissingHypothesis"], ["MissingHypothesis", "mp"],
    ),
    # UnsupportedConclusion — conclude claims original implication, not derived fact
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  assume h2: {a}\n"
            f"  have h3: {b} by mp h1 h2\n"
            f"  conclude {a} -> {b} by h3\n"
        ),
        False, ["UnsupportedConclusion"], ["UnsupportedConclusion", "mp"],
    ),
    # InvalidTransition — mp second premise is conjunction, not atom
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  assume h2: {a} and {c}\n"
            f"  have h3: {b} by mp h1 h2\n"
            f"  conclude {b} by h3\n"
        ),
        False, ["InvalidTransition"], ["InvalidTransition", "mp"],
    ),
    # InvalidTransition — and_elim_left claims right conjunct
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} and {b}\n"
            f"  have h2: {b} by and_elim_left h1\n"
            f"  conclude {b} by h2\n"
        ),
        False, ["InvalidTransition"], ["InvalidTransition", "and_elim"],
    ),
    # UnusedAssumption (proof still VALID — warning only)
    (
        lambda a, b, c, i, lg: (
            f"theorem prop_{i:06d} using {lg}:\n"
            f"  assume h1: {a} -> {b}\n"
            f"  assume h2: {a}\n"
            f"  assume h_extra: {c}\n"
            f"  have h3: {b} by mp h1 h2\n"
            f"  conclude {b} by h3\n"
        ),
        True, ["UnusedAssumption"], ["UnusedAssumption", "mp"],
    ),
]

_PERMS = list(permutations(PROP_VARS))


def generate(n, rng, start_id=0):
    """Generate n prop_nd records. rng must be a seeded random.Random instance."""
    records = []
    for i in range(n):
        idx = start_id + i
        a, b, c = _PERMS[rng.randrange(len(_PERMS))]

        is_valid = rng.random() < VALID_RATIO
        logic = "intuitionistic_prop"

        if is_valid:
            fn, tags = _VALID[rng.randrange(len(_VALID))]
            records.append({
                "id": f"{CORPUS_NAME}_{idx:06d}",
                "corpus": CORPUS_NAME,
                "text": fn(a, b, c, idx, logic),
                "logic": logic,
                "expected_valid": True,
                "expected_codes": [],
                "tags": ["valid"] + tags,
                "metadata": {
                    "generator_version": GENERATOR_VERSION,
                    "mutation": None,
                },
            })
        else:
            fn, m_valid, m_codes, m_tags = _MUTATIONS[rng.randrange(len(_MUTATIONS))]
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
                    "mutation": m_codes[0] if m_codes else None,
                },
            })

    return records
