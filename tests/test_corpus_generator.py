"""Tests for the synthetic corpus generator (bench/generate.py and bench/corpora/)."""
import json
import pathlib
import random
import sys

import pytest

# Ensure project root is on path so bench.* is importable.
_ROOT = pathlib.Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bench.corpora import REGISTRY, ALL_CORPORA, ALL_DISTRIBUTION, CORPUS_SEED_OFFSETS
from bench.corpora.prop_nd import generate as prop_nd_gen
from bench.corpora.definition_use import generate as def_use_gen
from bench.corpora.diagnostic_errors import generate as diag_gen
from bench.generate import (
    distribute,
    generate_corpus,
    generate_all,
    write_shards,
    write_manifest,
    validate_records,
)

SAMPLE_DIR = pathlib.Path("bench/generated/sample")
REQUIRED_FIELDS = {"id", "corpus", "text", "logic", "expected_valid", "expected_codes", "tags", "metadata"}


# ---------------------------------------------------------------------------
# Part A — Corpus registry
# ---------------------------------------------------------------------------

def test_registry_has_all_corpora():
    assert set(REGISTRY.keys()) == {"prop_nd", "definition_use", "diagnostic_errors"}


def test_all_corpora_list():
    assert set(ALL_CORPORA) == set(REGISTRY.keys())


def test_distribution_sums_to_one():
    total = sum(ALL_DISTRIBUTION.values())
    assert abs(total - 1.0) < 1e-9


def test_seed_offsets_distinct():
    offsets = list(CORPUS_SEED_OFFSETS.values())
    assert len(offsets) == len(set(offsets)), "corpus seed offsets must be distinct"


# ---------------------------------------------------------------------------
# Part B — Generator determinism
# ---------------------------------------------------------------------------

def test_prop_nd_deterministic():
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    r1 = prop_nd_gen(10, rng1)
    r2 = prop_nd_gen(10, rng2)
    assert r1 == r2


def test_def_use_deterministic():
    rng1 = random.Random(7)
    rng2 = random.Random(7)
    r1 = def_use_gen(5, rng1)
    r2 = def_use_gen(5, rng2)
    assert r1 == r2


def test_diag_deterministic():
    rng1 = random.Random(99)
    rng2 = random.Random(99)
    r1 = diag_gen(6, rng1)
    r2 = diag_gen(6, rng2)
    assert r1 == r2


def test_generate_corpus_deterministic():
    r1 = generate_corpus("prop_nd", 20, seed=0)
    r2 = generate_corpus("prop_nd", 20, seed=0)
    assert r1 == r2


def test_generate_all_deterministic():
    r1, n1 = generate_all(40, seed=0)
    r2, n2 = generate_all(40, seed=0)
    assert r1 == r2
    assert n1 == n2


def test_different_seeds_differ():
    r0 = generate_corpus("prop_nd", 10, seed=0)
    r1 = generate_corpus("prop_nd", 10, seed=1)
    ids0 = [r["id"] for r in r0]
    ids1 = [r["id"] for r in r1]
    # IDs are the same (index-based), but text/codes should differ for at least some
    texts0 = [r["text"] for r in r0]
    texts1 = [r["text"] for r in r1]
    assert texts0 != texts1, "different seeds should produce different records"


# ---------------------------------------------------------------------------
# Part C — distribute helper
# ---------------------------------------------------------------------------

def test_distribute_exact():
    n_per = distribute(100, {"a": 0.6, "b": 0.2, "c": 0.2})
    assert sum(n_per.values()) == 100


def test_distribute_with_remainder():
    n_per = distribute(41, ALL_DISTRIBUTION)
    assert sum(n_per.values()) == 41


def test_distribute_zero_n():
    n_per = distribute(0, ALL_DISTRIBUTION)
    assert sum(n_per.values()) == 0


def test_distribute_large_n():
    n_per = distribute(500000, ALL_DISTRIBUTION)
    assert sum(n_per.values()) == 500000
    # prop_nd should be the largest share
    assert n_per["prop_nd"] > n_per["definition_use"]
    assert n_per["prop_nd"] > n_per["diagnostic_errors"]


# ---------------------------------------------------------------------------
# Part D — generate_corpus standalone vs inside generate_all
# ---------------------------------------------------------------------------

def test_standalone_corpus_matches_inside_all():
    """Standalone prop_nd generation must produce the same first k records as
    inside --corpus all, because corpus_seed_offsets are applied consistently."""
    n_per = distribute(60, ALL_DISTRIBUTION)
    n_prop = n_per["prop_nd"]

    standalone = generate_corpus("prop_nd", n_prop, seed=0)
    all_records, _ = generate_all(60, seed=0)
    from_all = [r for r in all_records if r["corpus"] == "prop_nd"]

    assert standalone == from_all


# ---------------------------------------------------------------------------
# Part E — Label integrity
# ---------------------------------------------------------------------------

def _make_records(n=20, corpus="prop_nd"):
    return generate_corpus(corpus, n, seed=0)


def test_required_fields_present():
    for corpus in ALL_CORPORA:
        for rec in _make_records(6, corpus):
            missing = REQUIRED_FIELDS - set(rec.keys())
            assert not missing, f"missing fields in {rec['id']}: {missing}"


def test_valid_records_have_empty_codes():
    for corpus in ALL_CORPORA:
        for rec in _make_records(20, corpus):
            if rec["expected_valid"] is True and not rec["expected_codes"]:
                # Truly valid: expected_codes must be []
                assert rec["expected_codes"] == []


def test_error_records_have_nonempty_codes():
    """Records where expected_valid=False must have at least one expected code."""
    for corpus in ALL_CORPORA:
        for rec in _make_records(30, corpus):
            if rec["expected_valid"] is False:
                assert rec["expected_codes"], f"error record {rec['id']} has empty codes"


def test_warning_records_have_codes_but_valid():
    """UnusedAssumption and UndefinedDefinition are warnings: valid=True, codes non-empty."""
    records = generate_corpus("diagnostic_errors", 12, seed=0)
    warning_recs = [r for r in records if "UnusedAssumption" in r["expected_codes"]
                    or "UndefinedDefinition" in r["expected_codes"]]
    assert len(warning_recs) > 0
    for rec in warning_recs:
        assert rec["expected_valid"] is True


def test_ids_are_unique():
    for corpus in ALL_CORPORA:
        records = _make_records(30, corpus)
        ids = [r["id"] for r in records]
        assert len(ids) == len(set(ids)), f"duplicate IDs in {corpus}"


def test_ids_prefixed_by_corpus():
    for corpus in ALL_CORPORA:
        for rec in _make_records(5, corpus):
            assert rec["id"].startswith(corpus)


def test_corpus_field_matches():
    for corpus in ALL_CORPORA:
        for rec in _make_records(5, corpus):
            assert rec["corpus"] == corpus


def test_expected_codes_are_lists():
    for corpus in ALL_CORPORA:
        for rec in _make_records(5, corpus):
            assert isinstance(rec["expected_codes"], list)


def test_metadata_has_generator_version():
    for corpus in ALL_CORPORA:
        for rec in _make_records(3, corpus):
            assert "generator_version" in rec["metadata"]
            assert isinstance(rec["metadata"]["generator_version"], int)


# ---------------------------------------------------------------------------
# Part F — Shard writing and manifest
# ---------------------------------------------------------------------------

def test_shard_count(tmp_path):
    records = generate_corpus("prop_nd", 25, seed=0)
    names = write_shards(records, tmp_path / "out", shard_size=10)
    # ceil(25/10) = 3 shards
    assert len(names) == 3
    shard_files = list((tmp_path / "out").glob("shard_*.jsonl"))
    assert len(shard_files) == 3


def test_shard_record_count(tmp_path):
    records = generate_corpus("prop_nd", 25, seed=0)
    write_shards(records, tmp_path / "out", shard_size=10)
    total = 0
    for path in sorted((tmp_path / "out").glob("shard_*.jsonl")):
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        total += len(lines)
    assert total == 25


def test_shard_records_are_valid_json(tmp_path):
    records = generate_corpus("prop_nd", 10, seed=0)
    write_shards(records, tmp_path / "out", shard_size=5)
    for path in (tmp_path / "out").glob("shard_*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                assert "id" in obj


def test_shard_filenames_numbered(tmp_path):
    records = generate_corpus("prop_nd", 3, seed=0)
    names = write_shards(records, tmp_path / "out", shard_size=3)
    assert names == ["shard_00000.jsonl"]


def test_manifest_written(tmp_path):
    records, n_per = generate_all(20, seed=0)
    names = write_shards(records, tmp_path / "out", shard_size=10)
    write_manifest(
        tmp_path / "out",
        corpus_arg="all",
        n_total=20,
        seed=0,
        shard_size=10,
        n_per_corpus=n_per,
        shard_names=names,
    )
    manifest_path = tmp_path / "out" / "manifest.json"
    assert manifest_path.exists()


def test_manifest_fields(tmp_path):
    records, n_per = generate_all(20, seed=0)
    names = write_shards(records, tmp_path / "out", shard_size=10)
    write_manifest(
        tmp_path / "out",
        corpus_arg="all",
        n_total=20,
        seed=0,
        shard_size=10,
        n_per_corpus=n_per,
        shard_names=names,
    )
    m = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert m["n_total"] == 20
    assert m["n_shards"] == 2
    assert m["shard_size"] == 10
    assert "corpora" in m
    assert "n_per_corpus" in m
    assert "args" in m
    assert m["args"]["seed"] == 0
    assert "generator_version" in m


def test_manifest_n_per_corpus_sums(tmp_path):
    records, n_per = generate_all(40, seed=0)
    names = write_shards(records, tmp_path / "out", shard_size=20)
    write_manifest(
        tmp_path / "out",
        corpus_arg="all",
        n_total=40,
        seed=0,
        shard_size=20,
        n_per_corpus=n_per,
        shard_names=names,
    )
    m = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert sum(m["n_per_corpus"].values()) == 40


# ---------------------------------------------------------------------------
# Part G — diagnostic_errors covers all codes
# ---------------------------------------------------------------------------

def test_diagnostic_errors_covers_all_codes():
    from bench.corpora.diagnostic_errors import _PATTERNS
    covered = set()
    for _, _, codes, _ in _PATTERNS:
        covered.update(codes)
    expected = {
        "UndefinedSymbol", "MissingHypothesis", "UnsupportedConclusion",
        "InvalidTransition", "UndefinedDefinition", "UnusedAssumption",
    }
    assert expected <= covered


def test_diagnostic_errors_cycles(tmp_path):
    """n=12 covers each of the 6 patterns exactly twice."""
    records = generate_corpus("diagnostic_errors", 12, seed=0)
    codes_seen = {}
    for rec in records:
        for code in rec["expected_codes"]:
            codes_seen[code] = codes_seen.get(code, 0) + 1
    for code in ["UndefinedSymbol", "MissingHypothesis", "UnsupportedConclusion",
                 "InvalidTransition", "UndefinedDefinition", "UnusedAssumption"]:
        assert codes_seen.get(code, 0) == 2, f"{code} not exactly 2 in 12 records"


# ---------------------------------------------------------------------------
# Part H — Validation function
# ---------------------------------------------------------------------------

def test_validate_all_ok():
    records, _ = generate_all(40, seed=0)
    n_ok, n_fail, failures = validate_records(records)
    assert n_fail == 0, (
        f"{n_fail} records failed validation:\n" +
        "\n".join(str(f) for f in failures[:5])
    )
    assert n_ok == 40


def test_validate_prop_nd_small():
    records = generate_corpus("prop_nd", 20, seed=0)
    n_ok, n_fail, _ = validate_records(records)
    assert n_fail == 0


def test_validate_definition_use_small():
    records = generate_corpus("definition_use", 10, seed=0)
    n_ok, n_fail, _ = validate_records(records)
    assert n_fail == 0


def test_validate_diagnostic_errors_small():
    records = generate_corpus("diagnostic_errors", 12, seed=0)
    n_ok, n_fail, _ = validate_records(records)
    assert n_fail == 0


# ---------------------------------------------------------------------------
# Part I — Committed sample is small
# ---------------------------------------------------------------------------

def test_sample_exists():
    assert SAMPLE_DIR.exists(), "bench/generated/sample/ must be committed"
    assert (SAMPLE_DIR / "manifest.json").exists()


def test_sample_is_small():
    """Committed sample must have <= 100 records."""
    total = 0
    for shard in SAMPLE_DIR.glob("shard_*.jsonl"):
        lines = [l for l in shard.read_text(encoding="utf-8").splitlines() if l.strip()]
        total += len(lines)
    assert total <= 100, f"committed sample has {total} records (limit 100)"


def test_sample_manifest_matches_records():
    m = json.loads((SAMPLE_DIR / "manifest.json").read_text(encoding="utf-8"))
    total_in_shards = 0
    for shard in SAMPLE_DIR.glob("shard_*.jsonl"):
        lines = [l for l in shard.read_text(encoding="utf-8").splitlines() if l.strip()]
        total_in_shards += len(lines)
    assert m["n_total"] == total_in_shards


def test_sample_records_have_required_fields():
    for shard in SAMPLE_DIR.glob("shard_*.jsonl"):
        for line in shard.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            missing = REQUIRED_FIELDS - set(rec.keys())
            assert not missing, f"missing fields in sample record {rec.get('id')}: {missing}"


# ---------------------------------------------------------------------------
# Part J — CLI smoke test
# ---------------------------------------------------------------------------

def test_cli_prop_nd(tmp_path):
    import importlib.util, types
    # Import generate.main() without re-running __main__
    from bench.generate import main
    rc = main(["--corpus", "prop_nd", "--n", "10", "--out", str(tmp_path / "out"), "--seed", "42"])
    assert rc == 0
    assert (tmp_path / "out" / "manifest.json").exists()
    m = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert m["n_total"] == 10


def test_cli_all(tmp_path):
    from bench.generate import main
    rc = main(["--corpus", "all", "--n", "18", "--out", str(tmp_path / "out"),
               "--seed", "0", "--shard-size", "6"])
    assert rc == 0
    m = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert m["n_total"] == 18
    assert m["n_shards"] == 3


def test_cli_validate(tmp_path):
    from bench.generate import main
    rc = main(["--corpus", "all", "--n", "12", "--out", str(tmp_path / "out"),
               "--seed", "0", "--validate"])
    assert rc == 0
