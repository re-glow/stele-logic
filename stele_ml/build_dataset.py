"""Build a train/dev/test dataset from a generated corpus.

Usage:
    python stele_ml/build_dataset.py \\
        --source bench/generated/sample \\
        --out stele_ml/data/sample_split \\
        --seed 0

Produces:
    {out}/train.jsonl
    {out}/dev.jsonl
    {out}/test.jsonl
    {out}/split_manifest.json

Split strategy: records are sorted by task ID (deterministic order), then
shuffled by seeded RNG. The same (source, seed, splits) tuple always produces
the same partition. IDs across splits are disjoint by construction.

Leakage note: within-corpus-family records that share the same proof template
may appear across splits. This is a known limitation of template-based
synthetic generation and is documented in split_manifest.json.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from stele_ml.data import load_from_jsonl_dir, split_three_way


def write_jsonl(records: list[dict], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True))
            f.write("\n")


def compute_split_stats(records: list[dict]) -> dict:
    n_valid = sum(1 for r in records if r.get("expected_valid"))
    code_dist: dict[str, int] = {}
    for r in records:
        for code in r.get("expected_codes") or []:
            code_dist[code] = code_dist.get(code, 0) + 1
    corpus_dist: dict[str, int] = {}
    for r in records:
        c = r.get("corpus", "unknown")
        corpus_dist[c] = corpus_dist.get(c, 0) + 1
    return {
        "n": len(records),
        "n_valid": n_valid,
        "n_invalid": len(records) - n_valid,
        "code_distribution": dict(sorted(code_dist.items())),
        "corpus_distribution": dict(sorted(corpus_dist.items())),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python stele_ml/build_dataset.py",
        description=(
            "Build a deterministic train/dev/test split from a generated corpus.\n"
            "All splits are disjoint by ID. Template-level leakage is documented."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--source", required=True,
                    help="directory with shard_*.jsonl files (e.g. bench/generated/sample)")
    ap.add_argument("--out", required=True,
                    help="output directory for split files")
    ap.add_argument("--seed", type=int, default=0,
                    help="RNG seed for split (default: 0)")
    ap.add_argument("--train-ratio", type=float, default=0.7, dest="train_ratio",
                    help="fraction for training set (default: 0.70)")
    ap.add_argument("--dev-ratio", type=float, default=0.15, dest="dev_ratio",
                    help="fraction for dev set (default: 0.15)")
    args = ap.parse_args(argv)

    src = pathlib.Path(args.source)
    if not src.exists():
        print(f"ERROR: source directory not found: {src}", file=sys.stderr)
        return 1

    records = load_from_jsonl_dir(src)
    if not records:
        print(f"ERROR: no records found in {src}", file=sys.stderr)
        return 1

    # Sort by ID for stable input order before shuffle
    records.sort(key=lambda r: r.get("id", ""))

    print(f"Loaded {len(records)} records from {src}")

    train, dev, test = split_three_way(
        records,
        train_ratio=args.train_ratio,
        dev_ratio=args.dev_ratio,
        seed=args.seed,
    )

    # Verify disjointness
    train_ids = {r["id"] for r in train}
    dev_ids = {r["id"] for r in dev}
    test_ids = {r["id"] for r in test}
    assert not (train_ids & dev_ids), "train/dev overlap"
    assert not (train_ids & test_ids), "train/test overlap"
    assert not (dev_ids & test_ids), "dev/test overlap"
    assert len(train_ids) + len(dev_ids) + len(test_ids) == len(records), "partition incomplete"

    out = pathlib.Path(args.out)
    write_jsonl(train, out / "train.jsonl")
    write_jsonl(dev, out / "dev.jsonl")
    write_jsonl(test, out / "test.jsonl")

    # Build split manifest
    cmd = (
        f"python stele_ml/build_dataset.py"
        f" --source {args.source}"
        f" --out {args.out}"
        f" --seed {args.seed}"
        f" --train-ratio {args.train_ratio}"
        f" --dev-ratio {args.dev_ratio}"
    )
    manifest = {
        "creation_command": cmd,
        "dev": compute_split_stats(dev),
        "leakage_note": (
            "Within-corpus-family records may share proof templates across splits. "
            "Template-level leakage is a known limitation of synthetic generation. "
            "Treat metrics on this split as indicative, not conclusive."
        ),
        "seed": args.seed,
        "source": str(src.resolve()),
        "split_ratios": {
            "dev": args.dev_ratio,
            "test": round(1.0 - args.train_ratio - args.dev_ratio, 4),
            "train": args.train_ratio,
        },
        "test": compute_split_stats(test),
        "total_records": len(records),
        "train": compute_split_stats(train),
    }
    with open(out / "split_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"  Train: {len(train)}  Dev: {len(dev)}  Test: {len(test)}")
    print(f"Output: {out}/")
    print(f"  train.jsonl  dev.jsonl  test.jsonl  split_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
