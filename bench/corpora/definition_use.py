"""definition_use corpus: tasks involving formula definitions.

Half the records are valid proofs that use a macro definition (definition NAME := FORMULA).
The other half inject UndefinedDefinition by referencing an undefined name inside a
definition body.

The theorem body in invalid records is still a valid trivial proof — the diagnostic fires
at the definition layer, not the theorem body.  Therefore expected_valid=True for those
records (check_theorem passes) but expected_codes=["UndefinedDefinition"].
"""
from itertools import permutations

CORPUS_NAME = "definition_use"
GENERATOR_VERSION = 1
PROP_VARS = ["P", "Q", "R"]
VALID_RATIO = 0.5

_PERMS = list(permutations(PROP_VARS))


def generate(n, rng, start_id=0):
    """Generate n definition_use records."""
    records = []
    for i in range(n):
        idx = start_id + i
        a, b, c = _PERMS[rng.randrange(len(_PERMS))]
        logic = "intuitionistic_prop"

        is_valid = rng.random() < VALID_RATIO

        if is_valid:
            # Definition expands to a -> b; theorem uses it via mp.
            def_name = f"DEF_{a}_{b}"
            text = (
                f"definition {def_name} := {a} -> {b}\n\n"
                f"theorem def_{idx:06d} using {logic}:\n"
                f"  assume h: {def_name}\n"
                f"  assume hp: {a}\n"
                f"  have hq: {b} by mp h hp\n"
                f"  conclude {b} by hq\n"
            )
            records.append({
                "id": f"{CORPUS_NAME}_{idx:06d}",
                "corpus": CORPUS_NAME,
                "text": text,
                "logic": logic,
                "expected_valid": True,
                "expected_codes": [],
                "tags": ["valid", "definition"],
                "metadata": {
                    "generator_version": GENERATOR_VERSION,
                    "mutation": None,
                },
            })
        else:
            # Definition body references an undefined name.
            # Theorem body is trivially valid (check passes), but UndefinedDefinition fires.
            undef_ref = f"UNDEF_{a}_{idx:04d}"
            def_name = f"USE_UNDEF_{idx:06d}"
            text = (
                f"definition {def_name} := {undef_ref} -> {a}\n\n"
                f"theorem def_{idx:06d}:\n"
                f"  assume h: {a}\n"
                f"  conclude {a} by h\n"
            )
            records.append({
                "id": f"{CORPUS_NAME}_{idx:06d}",
                "corpus": CORPUS_NAME,
                "text": text,
                "logic": logic,
                "expected_valid": True,   # theorem body passes check
                "expected_codes": ["UndefinedDefinition"],
                "tags": ["warning", "UndefinedDefinition"],
                "metadata": {
                    "generator_version": GENERATOR_VERSION,
                    "mutation": "UndefinedDefinition",
                },
            })

    return records
