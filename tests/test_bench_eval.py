"""Tests for the benchmark evaluation harness (stele/eval.py)."""
import json
import pathlib
import pytest

from stele.eval import (
    load_labels,
    run_task,
    evaluate_bench,
    compute_metrics,
    build_report,
    _safe_div,
    _f1,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BENCH_DIR = pathlib.Path("bench")
LABELS_PATH = BENCH_DIR / "labels.jsonl"


def _write_task(tmp_path, name, content):
    """Write a .stele task file and return its path."""
    p = tmp_path / "tasks" / f"{name}.stele"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _mini_labels(tmp_path):
    """Create a tiny 2-task benchmark fixture in tmp_path."""
    valid_src = (
        "theorem mini_valid using intuitionistic_prop:\n"
        "  assume h: P\n"
        "  conclude P by h\n"
    )
    invalid_src = (
        "theorem mini_invalid using intuitionistic_prop:\n"
        "  assume h: P\n"
        "  conclude Q by h\n"
    )
    _write_task(tmp_path, "mini_valid", valid_src)
    _write_task(tmp_path, "mini_invalid", invalid_src)
    labels = [
        {
            "id": "mini_invalid",
            "path": "tasks/mini_invalid.stele",
            "logic": "intuitionistic_prop",
            "expected_valid": False,
            "expected_codes": ["UnsupportedConclusion"],
            "description": "mini invalid fixture",
            "tags": [],
        },
        {
            "id": "mini_valid",
            "path": "tasks/mini_valid.stele",
            "logic": "intuitionistic_prop",
            "expected_valid": True,
            "expected_codes": [],
            "description": "mini valid fixture",
            "tags": [],
        },
    ]
    return labels


# ---------------------------------------------------------------------------
# Part A — Label loading
# ---------------------------------------------------------------------------

def test_load_labels_returns_list():
    labels = load_labels(LABELS_PATH)
    assert isinstance(labels, list)


def test_load_labels_count():
    labels = load_labels(LABELS_PATH)
    assert len(labels) >= 30


def test_load_labels_sorted_by_id():
    labels = load_labels(LABELS_PATH)
    ids = [l["id"] for l in labels]
    assert ids == sorted(ids)


def test_load_labels_required_fields():
    labels = load_labels(LABELS_PATH)
    for l in labels:
        assert "id" in l
        assert "path" in l
        assert "logic" in l
        assert "expected_valid" in l
        assert "expected_codes" in l
        assert isinstance(l["expected_valid"], bool)
        assert isinstance(l["expected_codes"], list)


def test_load_labels_has_valid_and_invalid():
    labels = load_labels(LABELS_PATH)
    valids = [l for l in labels if l["expected_valid"]]
    invalids = [l for l in labels if not l["expected_valid"]]
    assert len(valids) >= 10
    assert len(invalids) >= 5


def test_load_labels_all_paths_exist():
    labels = load_labels(LABELS_PATH)
    for l in labels:
        task_path = BENCH_DIR / l["path"]
        assert task_path.exists(), f"task file missing: {task_path}"


def test_load_labels_from_fixture(tmp_path):
    """Load labels from a scratch JSONL file."""
    jl = tmp_path / "labels.jsonl"
    record = {
        "id": "test_001",
        "path": "tasks/test_001.stele",
        "logic": "intuitionistic_prop",
        "expected_valid": True,
        "expected_codes": [],
    }
    jl.write_text(json.dumps(record) + "\n", encoding="utf-8")
    labels = load_labels(jl)
    assert len(labels) == 1
    assert labels[0]["id"] == "test_001"


def test_load_labels_skips_blank_lines(tmp_path):
    jl = tmp_path / "labels.jsonl"
    rec = json.dumps({"id": "x", "path": "t.stele", "logic": "intuitionistic_prop",
                      "expected_valid": True, "expected_codes": []})
    jl.write_text(f"\n{rec}\n\n", encoding="utf-8")
    labels = load_labels(jl)
    assert len(labels) == 1


# ---------------------------------------------------------------------------
# Part B — Single task execution
# ---------------------------------------------------------------------------

def test_run_task_valid(tmp_path):
    src = (
        "theorem t using intuitionistic_prop:\n"
        "  assume h: P\n"
        "  conclude P by h\n"
    )
    p = tmp_path / "t.stele"
    p.write_text(src, encoding="utf-8")
    r = run_task(p, "intuitionistic_prop")
    assert r["predicted_valid"] is True
    assert r["predicted_codes"] == []
    assert r["error"] is None


def test_run_task_unsupported_conclusion(tmp_path):
    src = (
        "theorem t:\n"
        "  assume h: P\n"
        "  conclude Q by h\n"
    )
    p = tmp_path / "t.stele"
    p.write_text(src, encoding="utf-8")
    r = run_task(p, "intuitionistic_prop")
    assert r["predicted_valid"] is False
    assert "UnsupportedConclusion" in r["predicted_codes"]


def test_run_task_undefined_symbol(tmp_path):
    src = (
        "theorem t using intuitionistic_prop:\n"
        "  have h: P by copy ghost\n"
        "  conclude P by h\n"
    )
    p = tmp_path / "t.stele"
    p.write_text(src, encoding="utf-8")
    r = run_task(p, "intuitionistic_prop")
    assert r["predicted_valid"] is False
    assert "UndefinedSymbol" in r["predicted_codes"]


def test_run_task_missing_file():
    r = run_task(pathlib.Path("nonexistent.stele"), "intuitionistic_prop")
    assert r["predicted_valid"] is False
    assert r["error"] is not None


def test_run_task_codes_are_sorted(tmp_path):
    src = (
        "theorem t:\n"
        "  assume h1: P\n"
        "  assume h2: Q\n"
        "  conclude P by h1\n"
    )
    p = tmp_path / "t.stele"
    p.write_text(src, encoding="utf-8")
    r = run_task(p, "intuitionistic_prop")
    assert r["predicted_codes"] == sorted(r["predicted_codes"])


def test_run_task_unused_assumption_valid_check(tmp_path):
    src = (
        "theorem t:\n"
        "  assume h1: P\n"
        "  assume h2: Q\n"
        "  conclude P by h1\n"
    )
    p = tmp_path / "t.stele"
    p.write_text(src, encoding="utf-8")
    r = run_task(p, "intuitionistic_prop")
    assert r["predicted_valid"] is True  # check passes
    assert "UnusedAssumption" in r["predicted_codes"]


# ---------------------------------------------------------------------------
# Part C — evaluate_bench
# ---------------------------------------------------------------------------

def test_evaluate_bench_mini(tmp_path):
    labels = _mini_labels(tmp_path)
    results = evaluate_bench(labels, tmp_path)
    assert len(results) == 2


def test_evaluate_bench_result_fields(tmp_path):
    labels = _mini_labels(tmp_path)
    results = evaluate_bench(labels, tmp_path)
    for r in results:
        assert "id" in r
        assert "expected_valid" in r
        assert "predicted_valid" in r
        assert "expected_codes" in r
        assert "predicted_codes" in r
        assert "valid_match" in r
        assert "code_exact_match" in r


def test_evaluate_bench_valid_task_passes(tmp_path):
    labels = _mini_labels(tmp_path)
    results = evaluate_bench(labels, tmp_path)
    valid_r = next(r for r in results if r["id"] == "mini_valid")
    assert valid_r["valid_match"] is True
    assert valid_r["code_exact_match"] is True


def test_evaluate_bench_invalid_task_passes(tmp_path):
    labels = _mini_labels(tmp_path)
    results = evaluate_bench(labels, tmp_path)
    invalid_r = next(r for r in results if r["id"] == "mini_invalid")
    assert invalid_r["valid_match"] is True
    assert invalid_r["code_exact_match"] is True


# ---------------------------------------------------------------------------
# Part D — compute_metrics (isolated unit tests)
# ---------------------------------------------------------------------------

def _make_result(id_, ev, pv, ec, pc):
    return {
        "id": id_,
        "expected_valid": ev,
        "predicted_valid": pv,
        "expected_codes": sorted(ec),
        "predicted_codes": sorted(pc),
        "valid_match": ev == pv,
        "code_exact_match": set(ec) == set(pc),
        "error": None,
    }


def test_metrics_empty_input():
    m = compute_metrics([])
    assert m == {}


def test_metrics_perfect_valid():
    r = _make_result("t1", True, True, [], [])
    m = compute_metrics([r])
    assert m["validity_accuracy"] == 1.0
    assert m["exact_match_rate"] == 1.0
    assert m["n_tasks"] == 1


def test_metrics_perfect_invalid_single_code():
    r = _make_result("t1", False, False, ["UndefinedSymbol"], ["UndefinedSymbol"])
    m = compute_metrics([r])
    assert m["validity_accuracy"] == 1.0
    assert m["exact_match_rate"] == 1.0
    assert m["per_code"]["UndefinedSymbol"]["precision"] == 1.0
    assert m["per_code"]["UndefinedSymbol"]["recall"] == 1.0
    assert m["per_code"]["UndefinedSymbol"]["f1"] == 1.0
    assert m["per_code"]["UndefinedSymbol"]["support"] == 1


def test_metrics_validity_miss():
    r = _make_result("t1", True, False, [], [])
    m = compute_metrics([r])
    assert m["validity_accuracy"] == 0.0


def test_metrics_code_fp():
    """Predicted code not in expected → FP, precision drops."""
    r = _make_result("t1", False, False, ["UndefinedSymbol"], ["UndefinedSymbol", "UnusedAssumption"])
    m = compute_metrics([r])
    pc = m["per_code"]
    assert pc["UndefinedSymbol"]["tp"] == 1
    assert pc["UndefinedSymbol"]["fp"] == 0
    assert pc["UnusedAssumption"]["fp"] == 1
    assert pc["UnusedAssumption"]["tp"] == 0
    assert m["exact_match_rate"] == 0.0


def test_metrics_code_fn():
    """Expected code not predicted → FN, recall drops."""
    r = _make_result("t1", False, False, ["UndefinedSymbol"], [])
    m = compute_metrics([r])
    pc = m["per_code"]
    assert pc["UndefinedSymbol"]["fn"] == 1
    assert pc["UndefinedSymbol"]["recall"] == 0.0
    assert m["micro"]["recall"] == 0.0


def test_metrics_micro_average():
    r1 = _make_result("t1", False, False, ["UndefinedSymbol"], ["UndefinedSymbol"])
    r2 = _make_result("t2", False, False, ["MissingHypothesis"], [])
    m = compute_metrics([r1, r2])
    # total_tp=1, total_fp=0, total_fn=1
    assert m["micro"]["precision"] == 1.0
    assert m["micro"]["recall"] == 0.5
    assert m["micro"]["f1"] == round(_f1(1.0, 0.5), 4)


def test_metrics_macro_average_ignores_zero_support():
    r = _make_result("t1", False, False, ["UndefinedSymbol"], ["UndefinedSymbol"])
    m = compute_metrics([r])
    # Only UndefinedSymbol has support; macro should equal per-code value
    assert m["macro"]["precision"] == 1.0
    assert m["macro"]["f1"] == 1.0


def test_metrics_safe_div_zero():
    assert _safe_div(0, 0) == 0.0
    assert _safe_div(1, 2) == 0.5


def test_metrics_f1_zero_denominator():
    assert _f1(0.0, 0.0) == 0.0


def test_metrics_n_valid_invalid_counts():
    r1 = _make_result("t1", True, True, [], [])
    r2 = _make_result("t2", False, False, ["UndefinedSymbol"], ["UndefinedSymbol"])
    r3 = _make_result("t3", True, True, [], [])
    m = compute_metrics([r1, r2, r3])
    assert m["n_valid_expected"] == 2
    assert m["n_invalid_expected"] == 1


def test_metrics_values_are_rounded():
    r = _make_result("t1", False, False, ["A", "B"], ["A"])
    m = compute_metrics([r])
    # All float values in per_code / micro / macro should have <= 4 decimal places
    for v in [m["micro"]["f1"], m["macro"]["f1"]]:
        assert isinstance(v, float)
        assert abs(v - round(v, 4)) < 1e-9


# ---------------------------------------------------------------------------
# Part E — build_report and JSON structure
# ---------------------------------------------------------------------------

def test_build_report_keys():
    r1 = _make_result("t1", True, True, [], [])
    m = compute_metrics([r1])
    report = build_report("bench/labels.jsonl", "bench", m, [r1])
    assert "labels_path" in report
    assert "tasks_root" in report
    assert "metrics" in report
    assert "results" in report


def test_report_metrics_has_expected_keys():
    r1 = _make_result("t1", True, True, [], [])
    m = compute_metrics([r1])
    report = build_report("bench/labels.jsonl", "bench", m, [r1])
    keys = set(report["metrics"].keys())
    for k in ("n_tasks", "validity_accuracy", "exact_match_rate", "per_code", "micro", "macro"):
        assert k in keys, f"missing key: {k}"


def test_report_is_json_serializable():
    r1 = _make_result("t1", True, True, [], [])
    m = compute_metrics([r1])
    report = build_report("bench/labels.jsonl", "bench", m, [r1])
    serialized = json.dumps(report)
    loaded = json.loads(serialized)
    assert loaded["metrics"]["n_tasks"] == 1


def test_report_written_to_file(tmp_path):
    labels = _mini_labels(tmp_path)
    results = evaluate_bench(labels, tmp_path)
    m = compute_metrics(results)
    report_path = tmp_path / "reports" / "test.json"
    report_path.parent.mkdir()
    report = build_report("bench/labels.jsonl", str(tmp_path), m, results)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert loaded["metrics"]["n_tasks"] == 2
    assert loaded["metrics"]["validity_accuracy"] == 1.0


# ---------------------------------------------------------------------------
# Part F — real benchmark smoke test
# ---------------------------------------------------------------------------

def test_real_benchmark_loads():
    labels = load_labels(LABELS_PATH)
    assert len(labels) >= 30


def test_real_benchmark_all_pass():
    """Full smoke test: every labeled task should match its expected outputs."""
    labels = load_labels(LABELS_PATH)
    results = evaluate_bench(labels, BENCH_DIR)
    m = compute_metrics(results)

    failures = [r for r in results if not (r["valid_match"] and r["code_exact_match"])]
    assert failures == [], (
        f"{len(failures)} task(s) did not match labels:\n" +
        "\n".join(
            f"  {r['id']}: valid={r['predicted_valid']} (exp {r['expected_valid']}), "
            f"codes={r['predicted_codes']} (exp {r['expected_codes']})"
            for r in failures
        )
    )

    assert m["validity_accuracy"] == 1.0
    assert m["exact_match_rate"] == 1.0


def test_real_benchmark_report_exists():
    """The generated report file should exist after the harness has run."""
    assert (BENCH_DIR / "reports" / "latest.json").exists()


def test_real_benchmark_report_structure():
    report_path = BENCH_DIR / "reports" / "latest.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    m = report["metrics"]
    assert m["n_tasks"] >= 30
    assert m["validity_accuracy"] == 1.0
    assert m["exact_match_rate"] == 1.0
    assert "per_code" in m
    assert "micro" in m
    assert "macro" in m


def test_real_benchmark_coverage_per_code():
    """Every supported error code (except TypeMismatch/CircularDependency which have
    no surface trigger) should appear at least once in the benchmark labels."""
    labels = load_labels(LABELS_PATH)
    all_expected = set(c for l in labels for c in l["expected_codes"])
    required = {
        "UndefinedSymbol",
        "MissingHypothesis",
        "UnsupportedConclusion",
        "UnusedAssumption",
        "UndefinedDefinition",
        "InvalidTransition",
    }
    missing = required - all_expected
    assert not missing, f"codes not in benchmark: {missing}"


def test_single_real_task_mp_valid():
    r = run_task(BENCH_DIR / "tasks" / "mp_valid_001.stele", "intuitionistic_prop")
    assert r["predicted_valid"] is True
    assert r["predicted_codes"] == []


def test_single_real_task_invalid_transition():
    r = run_task(BENCH_DIR / "tasks" / "invalid_transition_001.stele", "intuitionistic_prop")
    assert r["predicted_valid"] is False
    assert "InvalidTransition" in r["predicted_codes"]


def test_single_real_task_classical_dne():
    r = run_task(BENCH_DIR / "tasks" / "dne_valid_001.stele", "classical_prop")
    assert r["predicted_valid"] is True
    assert r["predicted_codes"] == []
