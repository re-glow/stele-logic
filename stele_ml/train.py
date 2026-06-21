"""Training CLI for the stele_ml Naive Bayes baseline.

Usage:
    # Default: generate 400 examples in-memory
    python -m stele_ml.train --out stele_ml/artifacts/baseline

    # From committed sample JSONL shards
    python -m stele_ml.train --data bench/generated/sample --out stele_ml/artifacts/baseline

    # From curated benchmark
    python -m stele_ml.train --labels bench/labels.jsonl --tasks bench --out stele_ml/artifacts/baseline

    # Combined: bench + generated
    python -m stele_ml.train --labels bench/labels.jsonl --tasks bench \\
        --augment 200 --out stele_ml/artifacts/baseline

No external dependencies are required. All metrics are measured on a
held-out test split — no values are hardcoded or fabricated.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from stele_ml.data import (
    load_from_jsonl_dir, load_from_bench, load_generated,
    split_train_test, records_to_xy, SURFACE_CODES,
)
from stele_ml.featurize import build_vocabulary, featurize_batch
from stele_ml.classifier import MultinomialNB, OneVsRestNB
from stele_ml._metrics import compute_metrics


def train_pipeline(
    records: list[dict],
    codes: list[str] = SURFACE_CODES,
    seed: int = 0,
    test_ratio: float = 0.2,
    alpha: float = 1.0,
    max_features: int = 500,
) -> tuple[dict, dict]:
    """Train NB models on records and evaluate on held-out test split.

    Returns:
        (artifacts_dict, metrics_dict) — both are plain JSON-serializable dicts.
    """
    train_recs, test_recs = split_train_test(records, test_ratio=test_ratio, seed=seed)

    train_texts, train_valid, train_codes = records_to_xy(train_recs)
    test_texts, test_valid, test_codes = records_to_xy(test_recs)

    # Build vocabulary from train set only (prevents data leakage)
    vocab = build_vocabulary(train_texts, min_df=1, max_features=max_features)

    X_train = featurize_batch(train_texts, vocab)
    X_test = featurize_batch(test_texts, vocab)

    # Validity model (binary: "valid" vs "invalid")
    valid_model = MultinomialNB(alpha=alpha)
    valid_model.fit(X_train, train_valid)
    valid_pred = valid_model.predict(X_test)

    # Diagnostic-code model (multi-label one-vs-rest)
    code_model = OneVsRestNB(alpha=alpha, threshold=0.5)
    code_model.fit(X_train, train_codes, codes)
    code_pred = code_model.predict(X_test)

    metrics = compute_metrics(test_valid, valid_pred, test_codes, code_pred, codes)

    artifacts = {
        "version": 1,
        "alpha": alpha,
        "codes": list(codes),
        "n_train": len(train_recs),
        "n_test": len(test_recs),
        "n_vocab": len(vocab),
        "seed": seed,
        "vocabulary": vocab,
        "validity_model": valid_model.to_dict(),
        "code_model": code_model.to_dict(),
    }

    return artifacts, metrics


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m stele_ml.train",
        description=(
            "Train Stele ML baseline (Multinomial Naive Bayes, stdlib-only).\n"
            "All metrics are measured on a held-out split — nothing is hardcoded."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--data", default=None,
                    help="directory of shard_*.jsonl files (generated corpus)")
    ap.add_argument("--labels", default=None,
                    help="bench/labels.jsonl path (curated benchmark)")
    ap.add_argument("--tasks", default="bench",
                    help="bench/ root for task .stele files (default: bench)")
    ap.add_argument("--augment", type=int, default=0,
                    help="generate this many extra in-memory examples to append")
    ap.add_argument("--out", default="stele_ml/artifacts/baseline",
                    help="output directory for model artifacts (default: stele_ml/artifacts/baseline)")
    ap.add_argument("--seed", type=int, default=0,
                    help="random seed (default: 0)")
    ap.add_argument("--n-generated", type=int, default=400, dest="n_generated",
                    help="if neither --data nor --labels given, generate this many (default: 400)")
    ap.add_argument("--alpha", type=float, default=1.0,
                    help="Laplace smoothing (default: 1.0)")
    ap.add_argument("--max-features", type=int, default=500, dest="max_features",
                    help="vocabulary cap (default: 500)")
    ap.add_argument("--report", default=None,
                    help="additionally write training report JSON here")
    args = ap.parse_args(argv)

    # Load data
    records: list[dict] = []
    data_source_desc: str

    if args.data:
        print(f"Loading from JSONL shards: {args.data}")
        records = load_from_jsonl_dir(args.data)
        data_source_desc = str(args.data)
    elif args.labels:
        print(f"Loading from bench labels: {args.labels}")
        records = load_from_bench(args.labels, args.tasks)
        data_source_desc = str(args.labels)
    else:
        print(f"Generating {args.n_generated} examples in-memory (seed={args.seed})")
        records = load_generated(args.n_generated, seed=args.seed)
        data_source_desc = f"generated (seed={args.seed}, n={args.n_generated})"

    if args.augment > 0:
        print(f"Augmenting with {args.augment} generated examples")
        extra = load_generated(args.augment, seed=args.seed + 9999)
        records = records + extra
        data_source_desc += f" + generated-augment(n={args.augment})"

    print(f"Total records: {len(records)}")
    if len(records) < 4:
        print("ERROR: need at least 4 records for train/test split", file=sys.stderr)
        return 1

    # Train and evaluate
    artifacts, metrics = train_pipeline(
        records,
        seed=args.seed,
        alpha=args.alpha,
        max_features=args.max_features,
    )

    # Print summary
    print(f"Train: {artifacts['n_train']}  |  Test: {artifacts['n_test']}")
    print(f"  Validity accuracy : {metrics['validity_accuracy']:.4f}"
          f"  ({metrics['validity_n_correct']}/{metrics['validity_n_total']})")
    print(f"  Exact match       : {metrics['exact_match']:.4f}"
          f"  ({metrics['exact_n_correct']}/{metrics['validity_n_total']})")
    print(f"  Micro F1 (codes)  : {metrics['micro_f1']:.4f}")
    print(f"  Macro F1 (codes)  : {metrics['macro_f1']:.4f}")

    # Save model
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "model.json"
    with open(model_path, "w", encoding="utf-8") as f:
        json.dump(artifacts, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"Model saved: {model_path}")

    # Build and optionally save report
    report = {
        "dataset": {
            "source": data_source_desc,
            "n_total": len(records),
            "n_train": artifacts["n_train"],
            "n_test": artifacts["n_test"],
        },
        "model": {
            "type": "MultinomialNaiveBayes (stdlib baseline)",
            "alpha": args.alpha,
            "n_vocab": artifacts["n_vocab"],
        },
        "metrics": metrics,
        "note": (
            "Stdlib Naive Bayes baseline on synthetic/benchmark data. "
            "Metrics reflect this small corpus and simple model. "
            "These are measured values — not targets or claims."
        ),
    }

    if args.report:
        rp = pathlib.Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        with open(rp, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write("\n")
        print(f"Report saved: {rp}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
