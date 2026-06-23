"""Evaluation CLI for the stele_ml baseline.

Usage:
    python -m stele_ml.eval \\
        --model stele_ml/artifacts/baseline \\
        --data bench/generated/sample \\
        --report stele_ml/reports/baseline_report.json

The script loads a trained model artifact, runs predictions on the
provided data, and writes a measured evaluation report.
No values are hardcoded; all metrics are computed from actual predictions.
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
    records_to_xy, SURFACE_CODES,
)
from stele_ml.featurize import featurize_batch
from stele_ml.classifier import MultinomialNB, OneVsRestNB
from stele_ml._metrics import compute_metrics


def compute_failure_analysis(metrics: dict, codes: list[str]) -> dict:
    """Identify per-code failure modes from a metrics dict.

    under_predicted: recall < 0.5 and support > 0 (model misses most positives)
    over_predicted:  precision < 0.5 and fp > 0 (false-positive prone)
    well_predicted:  f1 >= 0.5
    no_support:      code absent from test set
    """
    under, over, well, no_sup = [], [], [], []
    for code in codes:
        m = metrics.get("per_code", {}).get(code, {})
        if m.get("support", 0) == 0:
            no_sup.append(code)
            continue
        f1 = m.get("f1", 0.0)
        fp = m.get("fp", 0)
        if f1 >= 0.5:
            well.append(code)
        elif fp > 0 and m.get("precision", 0.0) < 0.5:
            over.append(code)
        else:
            under.append(code)
    return {
        "note": (
            "under_predicted = recall < 0.5 (model misses positives); "
            "over_predicted = precision < 0.5 with FP > 0; "
            "well_predicted = F1 >= 0.5."
        ),
        "no_support_in_test": sorted(no_sup),
        "over_predicted": sorted(over),
        "under_predicted": sorted(under),
        "well_predicted": sorted(well),
    }


def load_model(model_dir: str | pathlib.Path) -> dict:
    """Load model artifact from model_dir/model.json."""
    path = pathlib.Path(model_dir) / "model.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_eval(
    records: list[dict],
    model_artifact: dict,
) -> tuple[dict, list[str], list[list[str]]]:
    """Run predictions and compute metrics.

    Returns:
        (metrics_dict, validity_predictions, code_predictions)
    """
    vocab = model_artifact["vocabulary"]
    codes = model_artifact["codes"]

    texts, valid_true, code_true_sets = records_to_xy(records)
    X = featurize_batch(texts, vocab)

    valid_model = MultinomialNB.from_dict(model_artifact["validity_model"])
    code_model = OneVsRestNB.from_dict(model_artifact["code_model"])

    valid_pred = valid_model.predict(X)
    code_pred = code_model.predict(X)

    metrics = compute_metrics(valid_true, valid_pred, code_true_sets, code_pred, codes)
    return metrics, valid_pred, code_pred


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m stele_ml.eval",
        description=(
            "Evaluate a trained stele_ml model on a dataset.\n"
            "All reported values are measured — nothing is hardcoded."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--model", required=True,
                    help="directory containing model.json artifact")
    ap.add_argument("--data", default=None,
                    help="directory of shard_*.jsonl files (generated corpus)")
    ap.add_argument("--labels", default=None,
                    help="bench/labels.jsonl path (curated benchmark)")
    ap.add_argument("--tasks", default="bench",
                    help="bench/ root for task .stele files (default: bench)")
    ap.add_argument("--n-generated", type=int, default=80, dest="n_generated",
                    help="if no --data/--labels, generate this many examples (default: 80)")
    ap.add_argument("--seed", type=int, default=99,
                    help="seed for in-memory generation (default: 99 — different from train)")
    ap.add_argument("--report", default=None,
                    help="write evaluation report JSON to this path")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="print per-example predictions")
    args = ap.parse_args(argv)

    # Load model
    print(f"Loading model from: {args.model}")
    artifact = load_model(args.model)
    print(f"  Vocab size: {artifact['n_vocab']}, codes: {artifact['codes']}")

    # Load eval data
    records: list[dict]
    data_desc: str

    if args.data:
        records = load_from_jsonl_dir(args.data)
        data_desc = str(args.data)
    elif args.labels:
        records = load_from_bench(args.labels, args.tasks)
        data_desc = str(args.labels)
    else:
        records = load_generated(args.n_generated, seed=args.seed)
        data_desc = f"generated (seed={args.seed}, n={args.n_generated})"

    print(f"Eval data: {data_desc}  ({len(records)} records)")

    if not records:
        print("ERROR: no records to evaluate", file=sys.stderr)
        return 1

    # Run evaluation
    metrics, valid_pred, code_pred = run_eval(records, artifact)

    # Print summary
    print(f"\nResults on {len(records)} examples:")
    print(f"  Validity accuracy : {metrics['validity_accuracy']:.4f}"
          f"  ({metrics['validity_n_correct']}/{metrics['validity_n_total']})")
    print(f"  Exact match       : {metrics['exact_match']:.4f}"
          f"  ({metrics['exact_n_correct']}/{metrics['validity_n_total']})")
    print(f"  Micro F1 (codes)  : {metrics['micro_f1']:.4f}")
    print(f"  Macro F1 (codes)  : {metrics['macro_f1']:.4f}")
    print()
    print("  Per-code:")
    for code, m in sorted(metrics["per_code"].items()):
        if m["support"] > 0:
            print(f"    {code:25s}  P={m['precision']:.3f}  R={m['recall']:.3f}"
                  f"  F1={m['f1']:.3f}  (support={m['support']})")

    if args.verbose:
        _, valid_true, code_true = records_to_xy(records)
        print("\n  Predictions:")
        for i, rec in enumerate(records):
            print(f"    [{rec['id']}]  true={valid_true[i]}/{sorted(code_true[i])}"
                  f"  pred={valid_pred[i]}/{sorted(code_pred[i])}")

    # Write report
    if args.report:
        failure_analysis = compute_failure_analysis(
            metrics, artifact.get("codes", [])
        )
        report = {
            "dataset": {
                "source": data_desc,
                "n_eval": len(records),
            },
            "failure_mode_analysis": failure_analysis,
            "metrics": metrics,
            "model": {
                "n_train": artifact.get("n_train"),
                "n_test": artifact.get("n_test"),
                "n_vocab": artifact["n_vocab"],
                "path": str(args.model),
                "type": "MultinomialNaiveBayes (stdlib baseline)",
            },
            "note": (
                "Evaluation of stdlib Naive Bayes baseline. "
                "All values are measured from actual predictions. "
                "Small-data metrics should not be treated as final accuracy claims."
            ),
        }
        rp = pathlib.Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        with open(rp, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write("\n")
        print(f"\nReport saved: {rp}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
