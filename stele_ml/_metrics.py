"""Shared metric computation for train.py and eval.py."""
from __future__ import annotations


def _safe_div(a: float, b: float) -> float:
    return a / b if b > 0 else 0.0


def f1(precision: float, recall: float) -> float:
    return _safe_div(2.0 * precision * recall, precision + recall)


def compute_metrics(
    valid_true: list[str],
    valid_pred: list[str],
    code_true_sets: list[set[str]],
    code_pred_sets: list[list[str]],
    codes: list[str],
) -> dict:
    """Compute classification metrics for validity and diagnostic codes.

    Args:
        valid_true: ground-truth validity labels ("valid"/"invalid")
        valid_pred: predicted validity labels
        code_true_sets: ground-truth sets of diagnostic codes per example
        code_pred_sets: predicted lists of diagnostic codes per example
        codes: all possible diagnostic codes to report

    Returns:
        Dict with validity_accuracy, exact_match, per_code, micro_*, macro_*.
    """
    n = len(valid_true)
    assert n == len(valid_pred) == len(code_true_sets) == len(code_pred_sets)

    # --- validity accuracy ---
    valid_correct = sum(1 for t, p in zip(valid_true, valid_pred) if t == p)

    # --- exact match (validity AND codes both correct) ---
    exact = sum(
        1
        for vt, vp, ct, cp in zip(valid_true, valid_pred, code_true_sets, code_pred_sets)
        if vt == vp and set(ct) == set(cp)
    )

    # --- per-code P/R/F1 ---
    per_code: dict[str, dict] = {}
    for code in codes:
        tp = sum(1 for ct, cp in zip(code_true_sets, code_pred_sets)
                 if code in ct and code in cp)
        fp = sum(1 for ct, cp in zip(code_true_sets, code_pred_sets)
                 if code not in ct and code in cp)
        fn = sum(1 for ct, cp in zip(code_true_sets, code_pred_sets)
                 if code in ct and code not in cp)
        support = tp + fn
        p = _safe_div(tp, tp + fp)
        r = _safe_div(tp, support)
        per_code[code] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1(p, r), 4),
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    # --- micro avg ---
    total_tp = sum(per_code[c]["tp"] for c in codes)
    total_fp = sum(per_code[c]["fp"] for c in codes)
    total_fn = sum(per_code[c]["fn"] for c in codes)
    micro_p = _safe_div(total_tp, total_tp + total_fp)
    micro_r = _safe_div(total_tp, total_tp + total_fn)

    # --- macro avg (only over codes with positive support) ---
    codes_with_support = [c for c in codes if per_code[c]["support"] > 0]
    if codes_with_support:
        macro_p = sum(per_code[c]["precision"] for c in codes_with_support) / len(codes_with_support)
        macro_r = sum(per_code[c]["recall"] for c in codes_with_support) / len(codes_with_support)
        macro_f = sum(per_code[c]["f1"] for c in codes_with_support) / len(codes_with_support)
    else:
        macro_p = macro_r = macro_f = 0.0

    return {
        "validity_accuracy": round(valid_correct / n, 4) if n else 0.0,
        "validity_n_correct": valid_correct,
        "validity_n_total": n,
        "exact_match": round(exact / n, 4) if n else 0.0,
        "exact_n_correct": exact,
        "per_code": per_code,
        "micro_precision": round(micro_p, 4),
        "micro_recall": round(micro_r, 4),
        "micro_f1": round(f1(micro_p, micro_r), 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f, 4),
        "n_codes_with_support": len(codes_with_support),
    }
