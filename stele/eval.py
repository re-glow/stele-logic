"""Benchmark evaluation harness for the Stele proof checker.

Measures proof-checking correctness and diagnostic failure-mode localization
by running the checker over a labeled benchmark dataset.

Usage:
    python -m stele.eval bench \\
        --labels bench/labels.jsonl \\
        --tasks  bench \\
        --report bench/reports/latest.json

All numeric results are computed from the benchmark; nothing is hardcoded.
"""
import argparse
import json
import pathlib
import sys


# ---------------------------------------------------------------------------
# Label loading
# ---------------------------------------------------------------------------

def load_labels(labels_path):
    """Load a JSONL label file. Returns a list of dicts sorted by id."""
    with open(labels_path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    return sorted(records, key=lambda r: r["id"])


# ---------------------------------------------------------------------------
# Single-task execution
# ---------------------------------------------------------------------------

def run_task(task_path, logic_name):
    """Run strict check + diagnose on one .stele file.

    Returns a dict with:
      predicted_valid  — bool from check_theorem
      predicted_codes  — sorted list of unique diagnostic code strings
      error            — str if a non-proof error occurred, else None
    """
    from .parser import parse_theorem
    from .kernel import check_theorem
    from .diagnostics import diagnose_theorem
    from .errors import ParseError, ProofError, SteleError

    try:
        text = pathlib.Path(task_path).read_text(encoding="utf-8")
    except OSError as exc:
        return {"predicted_valid": False, "predicted_codes": [], "error": str(exc)}

    try:
        thm = parse_theorem(text)
    except (ParseError, SteleError, Exception) as exc:
        return {"predicted_valid": False, "predicted_codes": [], "error": f"ParseError: {exc}"}

    # Strict validity from the trusted kernel.
    try:
        check_theorem(thm, logic_name)
        predicted_valid = True
    except (ProofError, SteleError):
        predicted_valid = False

    # Diagnostic codes from the untrusted analysis layer.
    try:
        diags = diagnose_theorem(thm, logic_name)
        predicted_codes = sorted(set(d.code for d in diags))
    except Exception as exc:
        predicted_codes = []
        # Diagnostic failure is non-fatal; harness continues.
        return {
            "predicted_valid": predicted_valid,
            "predicted_codes": predicted_codes,
            "error": f"DiagnosticError: {exc}",
        }

    return {"predicted_valid": predicted_valid, "predicted_codes": predicted_codes, "error": None}


# ---------------------------------------------------------------------------
# Benchmark evaluation loop
# ---------------------------------------------------------------------------

def evaluate_bench(labels, task_root, verbose=False):
    """Run all labeled benchmark tasks and return per-task result dicts."""
    task_root = pathlib.Path(task_root)
    results = []

    for label in labels:
        task_id = label["id"]
        task_path = task_root / label["path"]
        logic = label.get("logic", "intuitionistic_prop")

        r = run_task(task_path, logic)

        expected_valid = label["expected_valid"]
        expected_codes = sorted(label.get("expected_codes", []))
        predicted_valid = r["predicted_valid"]
        predicted_codes = r["predicted_codes"]

        valid_match = (predicted_valid == expected_valid)
        code_exact_match = (set(predicted_codes) == set(expected_codes))

        result = {
            "id": task_id,
            "expected_valid": expected_valid,
            "predicted_valid": predicted_valid,
            "expected_codes": expected_codes,
            "predicted_codes": predicted_codes,
            "valid_match": valid_match,
            "code_exact_match": code_exact_match,
            "error": r.get("error"),
        }
        results.append(result)

        if verbose:
            ok = "PASS" if (valid_match and code_exact_match) else "FAIL"
            print(f"  [{ok}] {task_id}: valid={predicted_valid}, codes={predicted_codes}")

    return results


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def _safe_div(num, den):
    return num / den if den > 0 else 0.0


def _f1(p, r):
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def compute_metrics(results):
    """Compute validity accuracy, exact-match rate, per-code and micro/macro P/R/F1.

    Zero-denominator convention: precision, recall, and F1 are 0.0 when their
    denominator is zero (no predicted or no expected instances for that code).
    Macro average is taken only over codes that have at least one expected instance
    (support > 0); codes with support=0 are included in per_code for transparency.

    Returns a dict. All floats are rounded to 4 decimal places.
    """
    n_total = len(results)
    if n_total == 0:
        return {}

    # --- validity accuracy ---
    n_valid_match = sum(1 for r in results if r["valid_match"])
    validity_accuracy = _safe_div(n_valid_match, n_total)

    # --- code exact-match rate (all tasks, including valid ones with expected=[]) ---
    n_exact = sum(1 for r in results if r["code_exact_match"])
    exact_match_rate = _safe_div(n_exact, n_total)

    # --- collect all distinct codes that appear in either column ---
    all_codes = sorted(set(
        c
        for r in results
        for c in (r["expected_codes"] + r["predicted_codes"])
    ))

    per_code = {}
    total_tp = total_fp = total_fn = 0

    for code in all_codes:
        tp = fp = fn = 0
        for r in results:
            exp = set(r["expected_codes"])
            pred = set(r["predicted_codes"])
            in_exp = code in exp
            in_pred = code in pred
            if in_exp and in_pred:
                tp += 1
            elif (not in_exp) and in_pred:
                fp += 1
            elif in_exp and (not in_pred):
                fn += 1

        prec = _safe_div(tp, tp + fp)
        rec = _safe_div(tp, tp + fn)
        f1 = _f1(prec, rec)
        support = tp + fn  # number of tasks where code was expected

        per_code[code] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

        total_tp += tp
        total_fp += fp
        total_fn += fn

    # --- micro averages (aggregate TP/FP/FN across all codes) ---
    micro_p = _safe_div(total_tp, total_tp + total_fp)
    micro_r = _safe_div(total_tp, total_tp + total_fn)
    micro_f1 = _f1(micro_p, micro_r)

    # --- macro averages (mean over codes with support > 0) ---
    codes_with_support = [c for c in all_codes if per_code[c]["support"] > 0]
    if codes_with_support:
        macro_p = sum(per_code[c]["precision"] for c in codes_with_support) / len(codes_with_support)
        macro_r = sum(per_code[c]["recall"] for c in codes_with_support) / len(codes_with_support)
        macro_f1 = _f1(macro_p, macro_r)
    else:
        macro_p = macro_r = macro_f1 = 0.0

    n_valid_expected = sum(1 for r in results if r["expected_valid"])

    return {
        "n_tasks": n_total,
        "n_valid_expected": n_valid_expected,
        "n_invalid_expected": n_total - n_valid_expected,
        "n_valid_match": n_valid_match,
        "n_exact_match": n_exact,
        "validity_accuracy": round(validity_accuracy, 4),
        "exact_match_rate": round(exact_match_rate, 4),
        "per_code": per_code,
        "micro": {
            "precision": round(micro_p, 4),
            "recall": round(micro_r, 4),
            "f1": round(micro_f1, 4),
        },
        "macro": {
            "precision": round(macro_p, 4),
            "recall": round(macro_r, 4),
            "f1": round(macro_f1, 4),
        },
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def print_summary(metrics, results):
    """Print a human-readable evaluation summary to stdout."""
    n = metrics.get("n_tasks", 0)
    print("=== Stele Benchmark Evaluation ===")
    print(f"Tasks:              {n}")
    print(f"  expected valid:   {metrics.get('n_valid_expected', 0)}")
    print(f"  expected invalid: {metrics.get('n_invalid_expected', 0)}")
    print()
    va = metrics.get("validity_accuracy", 0.0)
    nm = metrics.get("n_valid_match", 0)
    em = metrics.get("exact_match_rate", 0.0)
    ne = metrics.get("n_exact_match", 0)
    print(f"Validity accuracy:  {va:.4f}  ({nm}/{n})")
    print(f"Code exact match:   {em:.4f}  ({ne}/{n})")
    print()
    micro = metrics.get("micro", {})
    macro = metrics.get("macro", {})
    print("Diagnostic P / R / F1:")
    print(f"  micro: P={micro.get('precision', 0.0):.4f}  "
          f"R={micro.get('recall', 0.0):.4f}  "
          f"F1={micro.get('f1', 0.0):.4f}")
    print(f"  macro: P={macro.get('precision', 0.0):.4f}  "
          f"R={macro.get('recall', 0.0):.4f}  "
          f"F1={macro.get('f1', 0.0):.4f}")
    print()

    per_code = metrics.get("per_code", {})
    supported = {c: m for c, m in per_code.items() if m["support"] > 0}
    if supported:
        print("Per-code metrics (expected support > 0):")
        for code, m in sorted(supported.items()):
            print(f"  {code:<28}  P={m['precision']:.4f}  R={m['recall']:.4f}  "
                  f"F1={m['f1']:.4f}  support={m['support']}")
        print()

    failures = [r for r in results if not (r["valid_match"] and r["code_exact_match"])]
    if failures:
        print(f"Mismatches ({len(failures)}):")
        for r in failures:
            print(f"  {r['id']}:")
            if not r["valid_match"]:
                print(f"    validity: predicted={r['predicted_valid']}  "
                      f"expected={r['expected_valid']}")
            if not r["code_exact_match"]:
                print(f"    codes:    predicted={r['predicted_codes']}  "
                      f"expected={r['expected_codes']}")
            if r.get("error"):
                print(f"    error: {r['error']}")
    else:
        print("All tasks matched expected labels.")


def build_report(labels_path, tasks_root, metrics, results):
    """Build the JSON-serializable report dict.

    Designed to be deterministic: task results are sorted by id, codes are
    sorted, numeric values are rounded. No timestamps or machine paths.
    """
    return {
        "labels_path": str(labels_path),
        "tasks_root": str(tasks_root),
        "metrics": metrics,
        "results": results,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]

    ap = argparse.ArgumentParser(
        prog="stele.eval",
        description="Stele benchmark evaluation harness. "
                    "All metrics are computed from the benchmark; nothing is hardcoded.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    bc = sub.add_parser("bench", help="evaluate against a labeled benchmark")
    bc.add_argument(
        "--labels", default="bench/labels.jsonl",
        help="JSONL label file (default: bench/labels.jsonl)",
    )
    bc.add_argument(
        "--tasks", default="bench",
        help="root directory; task paths in labels are relative to this "
             "(default: bench)",
    )
    bc.add_argument(
        "--report", default=None,
        help="write JSON report to this path (optional)",
    )
    bc.add_argument(
        "-v", "--verbose", action="store_true",
        help="print per-task PASS/FAIL lines",
    )

    args = ap.parse_args(argv)

    if args.cmd == "bench":
        labels = load_labels(args.labels)
        print(f"Loaded {len(labels)} labels from {args.labels}\n")

        results = evaluate_bench(labels, args.tasks, verbose=args.verbose)
        metrics = compute_metrics(results)
        print_summary(metrics, results)

        if args.report:
            report = build_report(args.labels, args.tasks, metrics, results)
            out = pathlib.Path(args.report)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, sort_keys=True)
                f.write("\n")
            print(f"\nReport written to {args.report}")

        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
