"""Dataset loading utilities for stele_ml.

Supports three data sources:
  1. JSONL shard directories (bench/generated/sample/ format)
  2. bench/labels.jsonl + bench/tasks/*.stele (curated benchmark format)
  3. In-memory generation via bench/generate.py (no file I/O required)

Record schema (internal):
  id, corpus, text, logic, expected_valid, expected_codes, tags, metadata
"""
from __future__ import annotations
import json
import pathlib
import random
import sys


# Diagnostic codes that appear as surface labels in generated data.
# TypeMismatch and CircularDependency are excluded (no surface trigger in v1).
SURFACE_CODES: list[str] = sorted([
    "InvalidTransition",
    "MissingHypothesis",
    "UndefinedDefinition",
    "UndefinedSymbol",
    "UnusedAssumption",
    "UnsupportedConclusion",
])

# All 8 stable codes defined in the diagnostics module.
ALL_CODES: list[str] = sorted([
    "CircularDependency",
    "InvalidTransition",
    "MissingHypothesis",
    "TypeMismatch",
    "UndefinedDefinition",
    "UndefinedSymbol",
    "UnusedAssumption",
    "UnsupportedConclusion",
])


def load_from_jsonl_dir(data_dir: str | pathlib.Path) -> list[dict]:
    """Load records from all shard_*.jsonl files in data_dir."""
    records = []
    data_path = pathlib.Path(data_dir)
    for shard in sorted(data_path.glob("shard_*.jsonl")):
        with open(shard, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def load_from_bench(
    labels_path: str | pathlib.Path,
    tasks_root: str | pathlib.Path = "bench",
) -> list[dict]:
    """Load records from bench/labels.jsonl + bench/tasks/*.stele files."""
    records = []
    labels_file = pathlib.Path(labels_path)
    tasks_dir = pathlib.Path(tasks_root)
    with open(labels_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            label = json.loads(line)
            task_path = tasks_dir / label["path"]
            text = task_path.read_text(encoding="utf-8")
            records.append({
                "id": label["id"],
                "corpus": "bench",
                "text": text,
                "logic": label.get("logic", "intuitionistic_prop"),
                "expected_valid": label["expected_valid"],
                "expected_codes": label["expected_codes"],
                "tags": label.get("tags", []),
                "metadata": {
                    "source": "bench",
                    "description": label.get("description", ""),
                },
            })
    return records


def load_generated(n: int = 400, seed: int = 0) -> list[dict]:
    """Generate n examples in-memory via the bench corpus generator.

    Requires bench/ to be importable (project root on sys.path).
    No files are written; generation is deterministic for a given (n, seed).
    """
    _root = pathlib.Path(__file__).parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from bench.generate import generate_all   # noqa: PLC0415
    records, _ = generate_all(n, seed)
    return records


def split_train_test(
    records: list[dict],
    test_ratio: float = 0.2,
    seed: int = 0,
) -> tuple[list[dict], list[dict]]:
    """Deterministic stratified-by-order train/test split.

    Shuffles index list with the given seed, then takes the first
    round(n * test_ratio) shuffled indices as the test set.
    """
    n = len(records)
    indices = list(range(n))
    random.Random(seed).shuffle(indices)
    n_test = max(1, round(n * test_ratio))
    test_set = set(indices[:n_test])
    train = [records[i] for i in range(n) if i not in test_set]
    test = [records[i] for i in range(n) if i in test_set]
    return train, test


def records_to_xy(
    records: list[dict],
) -> tuple[list[str], list[str], list[set[str]]]:
    """Extract (texts, validity_labels, code_labelsets) from records.

    validity_labels are "valid" or "invalid" strings (not booleans) to
    ensure clean JSON round-trips through the NB model serialization.
    """
    texts = [r["text"] for r in records]
    valid_labels = ["valid" if r["expected_valid"] else "invalid" for r in records]
    code_labelsets = [set(r.get("expected_codes") or []) for r in records]
    return texts, valid_labels, code_labelsets
