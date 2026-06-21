"""Deterministic text featurization for Stele proof tasks (stdlib only).

The featurizer extracts bag-of-words features from raw proof text.
Tokenization is whitespace + identifier-boundary based; no external
NLP libraries are used.
"""
from __future__ import annotations
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    """Lowercase identifier tokenizer.

    Extracts sequences matching [a-zA-Z_][a-zA-Z0-9_]* — the same
    character class used in the Stele parser for identifiers.
    This naturally captures rule names, variable names, and keywords.
    """
    return re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text.lower())


def build_vocabulary(
    train_texts: list[str],
    min_df: int = 1,
    max_features: int = 500,
) -> list[str]:
    """Build a sorted vocabulary from training texts.

    Args:
        train_texts: list of raw proof text strings
        min_df: minimum document frequency for inclusion
        max_features: cap on vocabulary size (most-frequent first)

    Returns:
        Sorted list of vocabulary tokens (stable ordering — deterministic).
    """
    df: Counter = Counter()
    for text in train_texts:
        df.update(set(tokenize(text)))

    # Primary sort: descending doc-frequency; secondary: alphabetical (tie-break)
    candidates = [
        (word, count)
        for word, count in df.items()
        if count >= min_df
    ]
    candidates.sort(key=lambda x: (-x[1], x[0]))

    return [word for word, _ in candidates[:max_features]]


def featurize(text: str, vocabulary: list[str]) -> list[float]:
    """Convert a single text to a term-frequency feature vector.

    Returns a list of float counts, one per vocabulary entry.
    Deterministic for a given (text, vocabulary) pair.
    """
    counts = Counter(tokenize(text))
    return [float(counts.get(word, 0)) for word in vocabulary]


def featurize_batch(texts: list[str], vocabulary: list[str]) -> list[list[float]]:
    """Featurize a list of texts (deterministic, no shuffling)."""
    return [featurize(t, vocabulary) for t in texts]
