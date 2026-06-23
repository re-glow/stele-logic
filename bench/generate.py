#!/usr/bin/env python3
"""Synthetic corpus generator for Stele proof-verification tasks.

Usage:
    python bench/generate.py --corpus prop_nd --n 100 --out bench/generated/demo --seed 0
    python bench/generate.py --corpus all --n 300 --out bench/generated/demo --seed 0 --shard-size 100
    python bench/generate.py --corpus all --n 50  --out bench/generated/sample --seed 0 --validate

Large-scale (do NOT commit — store externally or in release artifacts):
    python bench/generate.py --corpus all --n 500000 --out bench/generated/500k --seed 0 --shard-size 10000

All outputs are deterministic for a given (--corpus, --n, --seed, --shard-size) tuple.
No metrics are fabricated: run the eval harness separately to measure performance.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys

# ---------------------------------------------------------------------------
# Ensure project root is importable when this script runs as __main__
# (python bench/generate.py) or is imported from tests.
# ---------------------------------------------------------------------------
_HERE = pathlib.Path(__file__).resolve().parent   # bench/
_ROOT = _HERE.parent                              # project root
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bench.corpora import (                        # noqa: E402
    REGISTRY,
    ALL_CORPORA,
    ALL_DISTRIBUTION,
    CORPUS_SEED_OFFSETS,
    GENERATOR_VERSION,
)

GENERATOR_VERSION_STR = f"bench.generate v{GENERATOR_VERSION}"


# ---------------------------------------------------------------------------
# Distribution helpers
# ---------------------------------------------------------------------------

def distribute(n_total: int, distribution: dict[str, float]) -> dict[str, int]:
    """Allocate n_total records across corpora proportionally.

    Uses floor allocation; any remainder goes to the last corpus in
    sorted order (prop_nd has the highest proportion).
    """
    corpora = sorted(distribution.keys())
    n_per = {c: int(n_total * distribution[c]) for c in corpora}
    remainder = n_total - sum(n_per.values())
    if remainder > 0:
        n_per[corpora[-1]] += remainder
    return n_per


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------

def generate_corpus(
    corpus_name: str,
    n: int,
    seed: int,
    start_id: int = 0,
) -> list[dict]:
    """Generate n records for a single named corpus.

    The RNG seed is offset per-corpus so that standalone generation produces
    the same records as generation via --corpus all.
    """
    offset = CORPUS_SEED_OFFSETS.get(corpus_name, 0)
    rng = random.Random(seed + offset)
    generator = REGISTRY[corpus_name]
    return generator(n, rng, start_id=start_id)


def generate_all(n_total: int, seed: int) -> tuple[list[dict], dict[str, int]]:
    """Generate records for all corpora according to ALL_DISTRIBUTION.

    Returns (records, n_per_corpus_dict).
    Corpora are sorted alphabetically; records within each corpus come first.
    """
    n_per = distribute(n_total, ALL_DISTRIBUTION)
    records: list[dict] = []
    for corpus in sorted(n_per.keys()):
        records.extend(generate_corpus(corpus, n_per[corpus], seed))
    return records, n_per


# ---------------------------------------------------------------------------
# Shard writing
# ---------------------------------------------------------------------------

def write_shards(
    records: list[dict],
    out_dir: str | pathlib.Path,
    shard_size: int,
) -> list[str]:
    """Write records to numbered JSONL shards. Returns list of shard filenames."""
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    n_shards = max(1, math.ceil(len(records) / shard_size))
    shard_names = []

    for s in range(n_shards):
        chunk = records[s * shard_size : (s + 1) * shard_size]
        name = f"shard_{s:05d}.jsonl"
        shard_names.append(name)
        path = out / name
        with open(path, "w", encoding="utf-8") as f:
            for rec in chunk:
                f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True))
                f.write("\n")

    return shard_names


def compute_label_stats(records: list[dict]) -> dict:
    """Count valid/invalid and per-code frequencies across a record list."""
    n_valid = sum(1 for r in records if r.get("expected_valid"))
    code_dist: dict[str, int] = {}
    for r in records:
        for code in r.get("expected_codes") or []:
            code_dist[code] = code_dist.get(code, 0) + 1
    return {
        "n_invalid": len(records) - n_valid,
        "n_valid": n_valid,
        "code_distribution": dict(sorted(code_dist.items())),
    }


def write_manifest(
    out_dir: str | pathlib.Path,
    *,
    corpus_arg: str,
    n_total: int,
    seed: int,
    shard_size: int,
    n_per_corpus: dict[str, int],
    shard_names: list[str],
    label_stats: dict | None = None,
    creation_command: str | None = None,
) -> None:
    """Write manifest.json to out_dir."""
    out = pathlib.Path(out_dir)
    manifest = {
        "args": {
            "corpus": corpus_arg,
            "n": n_total,
            "seed": seed,
            "shard_size": shard_size,
        },
        "corpora": sorted(n_per_corpus.keys()),
        "creation_command": creation_command,
        "generator": GENERATOR_VERSION_STR,
        "generator_version": GENERATOR_VERSION,
        "label_stats": label_stats,
        "n_per_corpus": dict(sorted(n_per_corpus.items())),
        "n_shards": len(shard_names),
        "n_total": n_total,
        "shard_size": shard_size,
        "shards": shard_names,
    }
    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")


# ---------------------------------------------------------------------------
# Optional validation
# ---------------------------------------------------------------------------

def validate_records(records: list[dict]) -> tuple[int, int, list[tuple]]:
    """Run Stele check + diagnose over generated records and compare to labels.

    Requires stele to be importable (it is when running from the project root).
    Returns (n_ok, n_fail, failures).
    Failures is a list of (id, reason, expected_valid, expected_codes, pred_valid, pred_codes).
    """
    try:
        from stele.parser import parse_theorem
        from stele.kernel import check_theorem
        from stele.diagnostics import diagnose_theorem
        from stele.errors import ParseError, ProofError, SteleError
    except ImportError as exc:
        print(f"WARNING: cannot import stele for validation: {exc}", file=sys.stderr)
        return 0, 0, []

    failures: list[tuple] = []

    for rec in records:
        try:
            thm = parse_theorem(rec["text"])
        except (ParseError, SteleError, Exception) as exc:
            failures.append((rec["id"], f"ParseError: {exc}",
                             rec["expected_valid"], rec["expected_codes"], False, []))
            continue

        try:
            check_theorem(thm, rec.get("logic"))
            pred_valid = True
        except (ProofError, SteleError):
            pred_valid = False

        diags = diagnose_theorem(thm, rec.get("logic"))
        pred_codes = sorted(set(d.code for d in diags))

        valid_ok = pred_valid == rec["expected_valid"]
        codes_ok = set(pred_codes) == set(rec["expected_codes"])

        if not (valid_ok and codes_ok):
            failures.append((
                rec["id"], "label mismatch",
                rec["expected_valid"], rec["expected_codes"],
                pred_valid, pred_codes,
            ))

    n_ok = len(records) - len(failures)
    return n_ok, len(failures), failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="bench/generate.py",
        description=(
            "Synthetic corpus generator for Stele proof-verification tasks.\n"
            "Outputs deterministic sharded JSONL corpora.\n"
            "All labels are truthful; no metrics are fabricated."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--corpus",
        default="all",
        choices=["all"] + list(REGISTRY.keys()),
        help="corpus family to generate, or 'all' (default: all)",
    )
    ap.add_argument(
        "--n",
        type=int,
        default=100,
        help="total number of examples (default: 100)",
    )
    ap.add_argument(
        "--out",
        default="bench/generated/run",
        help="output directory (default: bench/generated/run)",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=0,
        help="random seed for deterministic generation (default: 0)",
    )
    ap.add_argument(
        "--shard-size",
        type=int,
        default=1000,
        dest="shard_size",
        help="records per JSONL shard (default: 1000)",
    )
    ap.add_argument(
        "--validate",
        action="store_true",
        help="run Stele checker over generated examples to verify labels",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Generate records
    if args.corpus == "all":
        records, n_per = generate_all(args.n, args.seed)
    else:
        records = generate_corpus(args.corpus, args.n, args.seed)
        n_per = {args.corpus: args.n}

    print(f"Generated {len(records)} records  "
          f"(corpus={args.corpus}, n={args.n}, seed={args.seed})")
    for name, count in sorted(n_per.items()):
        print(f"  {name}: {count}")

    # Optional label validation
    if args.validate:
        print("\nValidating labels against Stele checker…")
        n_ok, n_fail, failures = validate_records(records)
        print(f"  OK: {n_ok}  FAIL: {n_fail}")
        if failures:
            for fid, reason, ev, ec, pv, pc in failures[:20]:
                print(f"    [{fid}] {reason}: "
                      f"valid {pv} (exp {ev}), codes {pc} (exp {ec})")
            if len(failures) > 20:
                print(f"    … {len(failures) - 20} more")
        if n_fail:
            print("WARNING: some labels disagree with the current implementation.")

    # Write shards and manifest
    shard_names = write_shards(records, args.out, args.shard_size)
    cmd = (
        f"python bench/generate.py"
        f" --corpus {args.corpus}"
        f" --n {args.n}"
        f" --out {args.out}"
        f" --seed {args.seed}"
        f" --shard-size {args.shard_size}"
    )
    write_manifest(
        args.out,
        corpus_arg=args.corpus,
        n_total=len(records),
        seed=args.seed,
        shard_size=args.shard_size,
        n_per_corpus=n_per,
        shard_names=shard_names,
        label_stats=compute_label_stats(records),
        creation_command=cmd,
    )

    out = pathlib.Path(args.out)
    print(f"\nOutput: {args.out}/")
    print(f"  {len(shard_names)} shard(s), manifest.json")
    print(f"  total records: {len(records)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
