"""Corpus registry for the Stele synthetic generator.

Each corpus is a deterministic generator function:
    generate(n: int, rng: random.Random, start_id: int = 0) -> list[dict]

Distribution for --corpus all (must sum to 1.0):
    prop_nd           60%
    definition_use    20%
    diagnostic_errors 20%
"""
from .prop_nd import generate as _prop_nd
from .definition_use import generate as _def_use
from .diagnostic_errors import generate as _diag

REGISTRY = {
    "prop_nd": _prop_nd,
    "definition_use": _def_use,
    "diagnostic_errors": _diag,
}

ALL_CORPORA = sorted(REGISTRY.keys())

# Proportions for --corpus all; values must sum to 1.0.
ALL_DISTRIBUTION = {
    "prop_nd": 0.6,
    "definition_use": 0.2,
    "diagnostic_errors": 0.2,
}

# Seed offsets keep each corpus's RNG stream independent of the others,
# so generating a corpus standalone produces the same records as generating
# it as part of --corpus all.
CORPUS_SEED_OFFSETS = {
    "prop_nd": 0,
    "definition_use": 1000,
    "diagnostic_errors": 2000,
}

GENERATOR_VERSION = 1
