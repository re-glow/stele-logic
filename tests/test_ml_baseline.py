"""Smoke tests for the stele_ml baseline pipeline.

All tests are:
  - fast (no large dataset, no disk-heavy operations)
  - stdlib-only (no scikit-learn required)
  - deterministic (fixed seeds throughout)

Tests that DO require scikit-learn are NOT included here since the
baseline is implemented in pure Python.  The requirements-ml.txt
lists sklearn as an optional upgrade only.
"""
from __future__ import annotations
import json
import pathlib
import random
import sys

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

SAMPLE_DIR = pathlib.Path("bench/generated/sample")
MODEL_DIR = pathlib.Path("stele_ml/artifacts/baseline")
REPORT_PATH = pathlib.Path("stele_ml/reports/baseline_report.json")

_TINY_RECORDS = [
    {
        "id": "test_0", "corpus": "prop_nd", "logic": "intuitionistic_prop",
        "expected_valid": True, "expected_codes": [],
        "tags": ["valid"],
        "text": "theorem t0 using intuitionistic_prop:\n  assume h1: P -> Q\n  assume h2: P\n  have h3: Q by mp h1 h2\n  conclude Q by h3\n",
        "metadata": {},
    },
    {
        "id": "test_1", "corpus": "prop_nd", "logic": "intuitionistic_prop",
        "expected_valid": False, "expected_codes": ["UndefinedSymbol"],
        "tags": ["UndefinedSymbol"],
        "text": "theorem t1 using intuitionistic_prop:\n  assume h1: P -> Q\n  have h2: Q by mp h1 missing\n  conclude Q by h2\n",
        "metadata": {},
    },
    {
        "id": "test_2", "corpus": "prop_nd", "logic": "intuitionistic_prop",
        "expected_valid": False, "expected_codes": ["UnsupportedConclusion"],
        "tags": ["UnsupportedConclusion"],
        "text": "theorem t2 using intuitionistic_prop:\n  assume h1: P -> Q\n  assume h2: P\n  have h3: Q by mp h1 h2\n  conclude P -> Q by h3\n",
        "metadata": {},
    },
    {
        "id": "test_3", "corpus": "prop_nd", "logic": "intuitionistic_prop",
        "expected_valid": True, "expected_codes": ["UnusedAssumption"],
        "tags": ["UnusedAssumption"],
        "text": "theorem t3 using intuitionistic_prop:\n  assume h1: P -> Q\n  assume h2: P\n  assume h_extra: R\n  have h3: Q by mp h1 h2\n  conclude Q by h3\n",
        "metadata": {},
    },
    {
        "id": "test_4", "corpus": "prop_nd", "logic": "intuitionistic_prop",
        "expected_valid": False, "expected_codes": ["InvalidTransition"],
        "tags": ["InvalidTransition"],
        "text": "theorem t4 using intuitionistic_prop:\n  assume h1: P -> Q\n  assume h2: P and R\n  have h3: Q by mp h1 h2\n  conclude Q by h3\n",
        "metadata": {},
    },
    {
        "id": "test_5", "corpus": "prop_nd", "logic": "intuitionistic_prop",
        "expected_valid": False, "expected_codes": ["MissingHypothesis"],
        "tags": ["MissingHypothesis"],
        "text": "theorem t5 using intuitionistic_prop:\n  assume h1: P -> Q\n  have h3: Q by mp h1 h2\n  assume h2: P\n  conclude Q by h3\n",
        "metadata": {},
    },
]

# Use 5 for train, 1 for test
_TINY_TRAIN = _TINY_RECORDS[:5]
_TINY_TEST = _TINY_RECORDS[5:]


# ---------------------------------------------------------------------------
# Part A — featurize
# ---------------------------------------------------------------------------

def test_tokenize_deterministic():
    from stele_ml.featurize import tokenize
    t1 = tokenize("theorem t using intuitionistic_prop: assume h: P")
    t2 = tokenize("theorem t using intuitionistic_prop: assume h: P")
    assert t1 == t2


def test_tokenize_extracts_identifiers():
    from stele_ml.featurize import tokenize
    tokens = tokenize("theorem t1 using intuitionistic_prop:\n  assume h: P -> Q")
    assert "theorem" in tokens
    assert "assume" in tokens
    assert "intuitionistic_prop" in tokens


def test_build_vocabulary_deterministic():
    from stele_ml.featurize import build_vocabulary
    texts = [r["text"] for r in _TINY_TRAIN]
    v1 = build_vocabulary(texts)
    v2 = build_vocabulary(texts)
    assert v1 == v2


def test_build_vocabulary_respects_max_features():
    from stele_ml.featurize import build_vocabulary
    texts = [r["text"] for r in _TINY_TRAIN]
    vocab = build_vocabulary(texts, max_features=5)
    assert len(vocab) <= 5


def test_featurize_length_matches_vocab():
    from stele_ml.featurize import build_vocabulary, featurize
    texts = [r["text"] for r in _TINY_TRAIN]
    vocab = build_vocabulary(texts)
    vec = featurize(texts[0], vocab)
    assert len(vec) == len(vocab)


def test_featurize_batch_deterministic():
    from stele_ml.featurize import build_vocabulary, featurize_batch
    texts = [r["text"] for r in _TINY_TRAIN]
    vocab = build_vocabulary(texts)
    b1 = featurize_batch(texts, vocab)
    b2 = featurize_batch(texts, vocab)
    assert b1 == b2


def test_featurize_counts_are_nonneg():
    from stele_ml.featurize import build_vocabulary, featurize
    texts = [r["text"] for r in _TINY_TRAIN]
    vocab = build_vocabulary(texts)
    for text in texts:
        vec = featurize(text, vocab)
        assert all(v >= 0.0 for v in vec)


# ---------------------------------------------------------------------------
# Part B — classifier
# ---------------------------------------------------------------------------

def test_multinomial_nb_fit_predict():
    from stele_ml.featurize import build_vocabulary, featurize_batch
    from stele_ml.classifier import MultinomialNB
    texts = [r["text"] for r in _TINY_TRAIN]
    vocab = build_vocabulary(texts)
    X = featurize_batch(texts, vocab)
    y = ["valid" if r["expected_valid"] else "invalid" for r in _TINY_TRAIN]
    nb = MultinomialNB(alpha=1.0)
    nb.fit(X, y)
    preds = nb.predict(X)
    assert all(p in ("valid", "invalid") for p in preds)


def test_multinomial_nb_serialization():
    from stele_ml.featurize import build_vocabulary, featurize_batch
    from stele_ml.classifier import MultinomialNB
    texts = [r["text"] for r in _TINY_TRAIN]
    vocab = build_vocabulary(texts)
    X = featurize_batch(texts, vocab)
    y = ["valid" if r["expected_valid"] else "invalid" for r in _TINY_TRAIN]
    nb = MultinomialNB()
    nb.fit(X, y)

    d = nb.to_dict()
    nb2 = MultinomialNB.from_dict(d)

    # Predictions must match before and after serialization round-trip
    p1 = nb.predict(X)
    p2 = nb2.predict(X)
    assert p1 == p2


def test_nb_proba_sums_to_one():
    from stele_ml.featurize import build_vocabulary, featurize_batch
    from stele_ml.classifier import MultinomialNB
    texts = [r["text"] for r in _TINY_TRAIN]
    vocab = build_vocabulary(texts)
    X = featurize_batch(texts, vocab)
    y = ["valid" if r["expected_valid"] else "invalid" for r in _TINY_TRAIN]
    nb = MultinomialNB()
    nb.fit(X, y)
    probas = nb.predict_proba(X)
    for p in probas:
        total = sum(p.values())
        assert abs(total - 1.0) < 1e-6


def test_one_vs_rest_fit_predict():
    from stele_ml.featurize import build_vocabulary, featurize_batch
    from stele_ml.classifier import OneVsRestNB
    from stele_ml.data import SURFACE_CODES
    texts = [r["text"] for r in _TINY_TRAIN]
    vocab = build_vocabulary(texts)
    X = featurize_batch(texts, vocab)
    Y = [set(r["expected_codes"]) for r in _TINY_TRAIN]
    ovr = OneVsRestNB(alpha=1.0)
    ovr.fit(X, Y, SURFACE_CODES)
    preds = ovr.predict(X)
    assert len(preds) == len(X)
    for pred_set in preds:
        assert all(c in SURFACE_CODES for c in pred_set)


def test_one_vs_rest_serialization():
    from stele_ml.featurize import build_vocabulary, featurize_batch
    from stele_ml.classifier import OneVsRestNB
    from stele_ml.data import SURFACE_CODES
    texts = [r["text"] for r in _TINY_TRAIN]
    vocab = build_vocabulary(texts)
    X = featurize_batch(texts, vocab)
    Y = [set(r["expected_codes"]) for r in _TINY_TRAIN]
    ovr = OneVsRestNB()
    ovr.fit(X, Y, SURFACE_CODES)
    d = ovr.to_dict()
    ovr2 = OneVsRestNB.from_dict(d)
    p1 = ovr.predict(X)
    p2 = ovr2.predict(X)
    assert p1 == p2


# ---------------------------------------------------------------------------
# Part C — data loading
# ---------------------------------------------------------------------------

def test_load_from_jsonl_dir():
    from stele_ml.data import load_from_jsonl_dir
    records = load_from_jsonl_dir(SAMPLE_DIR)
    assert len(records) == 40
    assert all("text" in r for r in records)
    assert all("expected_valid" in r for r in records)


def test_load_from_bench():
    from stele_ml.data import load_from_bench
    records = load_from_bench("bench/labels.jsonl", "bench")
    assert len(records) == 31
    assert all("text" in r for r in records)


def test_load_generated_small():
    from stele_ml.data import load_generated
    records = load_generated(10, seed=0)
    assert len(records) == 10


def test_load_generated_deterministic():
    from stele_ml.data import load_generated
    r1 = load_generated(10, seed=0)
    r2 = load_generated(10, seed=0)
    assert r1 == r2


def test_split_deterministic():
    from stele_ml.data import split_train_test
    train1, test1 = split_train_test(_TINY_RECORDS, test_ratio=0.2, seed=0)
    train2, test2 = split_train_test(_TINY_RECORDS, test_ratio=0.2, seed=0)
    assert [r["id"] for r in train1] == [r["id"] for r in train2]
    assert [r["id"] for r in test1] == [r["id"] for r in test2]


def test_split_sizes():
    from stele_ml.data import split_train_test
    train, test = split_train_test(_TINY_RECORDS, test_ratio=0.2, seed=0)
    assert len(train) + len(test) == len(_TINY_RECORDS)
    assert len(test) >= 1


def test_records_to_xy():
    from stele_ml.data import records_to_xy
    texts, valid_labels, code_sets = records_to_xy(_TINY_RECORDS)
    assert len(texts) == len(_TINY_RECORDS)
    assert all(vl in ("valid", "invalid") for vl in valid_labels)
    assert all(isinstance(cs, set) for cs in code_sets)


# ---------------------------------------------------------------------------
# Part D — metrics
# ---------------------------------------------------------------------------

def test_metrics_perfect():
    from stele_ml._metrics import compute_metrics
    valid_true = ["valid", "invalid"]
    valid_pred = ["valid", "invalid"]
    code_true = [set(), {"UndefinedSymbol"}]
    code_pred = [[], ["UndefinedSymbol"]]
    codes = ["UndefinedSymbol"]
    m = compute_metrics(valid_true, valid_pred, code_true, code_pred, codes)
    assert m["validity_accuracy"] == 1.0
    assert m["exact_match"] == 1.0
    assert m["per_code"]["UndefinedSymbol"]["f1"] == 1.0
    assert m["micro_f1"] == 1.0


def test_metrics_all_wrong():
    from stele_ml._metrics import compute_metrics
    valid_true = ["valid", "invalid"]
    valid_pred = ["invalid", "valid"]
    code_true = [{"UndefinedSymbol"}, set()]
    code_pred = [[], []]
    codes = ["UndefinedSymbol"]
    m = compute_metrics(valid_true, valid_pred, code_true, code_pred, codes)
    assert m["validity_accuracy"] == 0.0
    assert m["per_code"]["UndefinedSymbol"]["recall"] == 0.0


def test_metrics_zero_division_safe():
    from stele_ml._metrics import compute_metrics
    valid_true = ["valid"]
    valid_pred = ["valid"]
    code_true = [set()]
    code_pred = [[]]
    codes = ["UndefinedSymbol"]  # zero support
    m = compute_metrics(valid_true, valid_pred, code_true, code_pred, codes)
    # Should not raise; F1 should be 0.0 (zero support)
    assert m["per_code"]["UndefinedSymbol"]["f1"] == 0.0
    assert m["macro_f1"] == 0.0  # no codes with support > 0


def test_metrics_keys_present():
    from stele_ml._metrics import compute_metrics
    from stele_ml.data import SURFACE_CODES
    m = compute_metrics(
        ["valid"], ["valid"], [set()], [[]], SURFACE_CODES
    )
    required_keys = {
        "validity_accuracy", "exact_match", "per_code",
        "micro_f1", "macro_f1", "micro_precision", "micro_recall",
        "macro_precision", "macro_recall", "validity_n_correct", "validity_n_total",
    }
    assert required_keys <= set(m.keys())


# ---------------------------------------------------------------------------
# Part E — train pipeline (tiny fixture)
# ---------------------------------------------------------------------------

def test_train_pipeline_tiny(tmp_path):
    from stele_ml.train import train_pipeline
    from stele_ml.data import SURFACE_CODES
    # Use 5 train records (alpha=1, no min_df filtering)
    artifacts, metrics = train_pipeline(
        _TINY_RECORDS,
        codes=SURFACE_CODES,
        seed=0,
        test_ratio=0.2,
        alpha=1.0,
        max_features=100,
    )
    assert artifacts["n_train"] >= 1
    assert artifacts["n_test"] >= 1
    assert "vocabulary" in artifacts
    assert "validity_model" in artifacts
    assert "code_model" in artifacts
    assert "validity_accuracy" in metrics


def test_train_pipeline_deterministic():
    from stele_ml.train import train_pipeline
    from stele_ml.data import SURFACE_CODES
    a1, m1 = train_pipeline(_TINY_RECORDS, codes=SURFACE_CODES, seed=0)
    a2, m2 = train_pipeline(_TINY_RECORDS, codes=SURFACE_CODES, seed=0)
    assert a1["vocabulary"] == a2["vocabulary"]
    assert m1["validity_accuracy"] == m2["validity_accuracy"]


def test_train_pipeline_artifacts_json_serializable():
    from stele_ml.train import train_pipeline
    from stele_ml.data import SURFACE_CODES
    artifacts, _ = train_pipeline(_TINY_RECORDS, codes=SURFACE_CODES, seed=0)
    # Should not raise
    serialized = json.dumps(artifacts, sort_keys=True)
    reloaded = json.loads(serialized)
    assert reloaded["version"] == 1


def test_train_saves_model(tmp_path):
    from stele_ml.train import main
    rc = main([
        "--n-generated", "20",
        "--out", str(tmp_path / "model"),
        "--seed", "0",
    ])
    assert rc == 0
    assert (tmp_path / "model" / "model.json").exists()
    with open(tmp_path / "model" / "model.json") as f:
        artifact = json.load(f)
    assert "vocabulary" in artifact
    assert "validity_model" in artifact


def test_train_writes_report(tmp_path):
    from stele_ml.train import main
    report_path = tmp_path / "report.json"
    rc = main([
        "--n-generated", "20",
        "--out", str(tmp_path / "model"),
        "--seed", "0",
        "--report", str(report_path),
    ])
    assert rc == 0
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert "metrics" in report
    assert "dataset" in report
    assert "model" in report
    assert "note" in report


# ---------------------------------------------------------------------------
# Part F — eval pipeline
# ---------------------------------------------------------------------------

def test_eval_on_sample_corpus():
    """Run eval on the committed sample corpus using the committed model."""
    if not MODEL_DIR.exists():
        pytest.skip("model artifact not found — run stele_ml.train first")
    from stele_ml.eval import load_model, run_eval
    from stele_ml.data import load_from_jsonl_dir
    artifact = load_model(MODEL_DIR)
    records = load_from_jsonl_dir(SAMPLE_DIR)
    metrics, _, _ = run_eval(records, artifact)
    assert 0.0 <= metrics["validity_accuracy"] <= 1.0
    assert 0.0 <= metrics["micro_f1"] <= 1.0


def test_eval_cli_writes_report(tmp_path):
    if not MODEL_DIR.exists():
        pytest.skip("model artifact not found — run stele_ml.train first")
    from stele_ml.eval import main
    report_path = tmp_path / "eval_report.json"
    rc = main([
        "--model", str(MODEL_DIR),
        "--data", str(SAMPLE_DIR),
        "--report", str(report_path),
    ])
    assert rc == 0
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    required = {"dataset", "model", "metrics", "note"}
    assert required <= set(report.keys())


# ---------------------------------------------------------------------------
# Part G — infer
# ---------------------------------------------------------------------------

def test_infer_on_valid_proof():
    if not MODEL_DIR.exists():
        pytest.skip("model artifact not found")
    from stele_ml.infer import load_model, predict_one
    artifact = load_model(MODEL_DIR)
    text = (
        "theorem t using intuitionistic_prop:\n"
        "  assume h1: P -> Q\n"
        "  assume h2: P\n"
        "  have h3: Q by mp h1 h2\n"
        "  conclude Q by h3\n"
    )
    result = predict_one(text, artifact)
    assert "predicted_valid" in result
    assert isinstance(result["predicted_valid"], bool)
    assert "predicted_codes" in result
    assert "code_probabilities" in result
    assert "disclaimer" in result


def test_infer_cli_json_output(tmp_path):
    if not MODEL_DIR.exists():
        pytest.skip("model artifact not found")
    from stele_ml.infer import main
    import io
    from contextlib import redirect_stdout
    text = "theorem t using intuitionistic_prop:\n  assume h: P\n  conclude P by h\n"
    f = io.StringIO()
    with redirect_stdout(f):
        rc = main(["--model", str(MODEL_DIR), "--text", text, "--json"])
    assert rc == 0
    output = f.getvalue().strip()
    result = json.loads(output)
    assert "predicted_valid" in result


# ---------------------------------------------------------------------------
# Part H — committed artifacts exist
# ---------------------------------------------------------------------------

def test_baseline_model_exists():
    assert MODEL_DIR.exists(), f"model directory {MODEL_DIR} must be committed"
    assert (MODEL_DIR / "model.json").exists(), "model.json must be committed"


def test_baseline_report_exists():
    assert REPORT_PATH.exists(), f"baseline report {REPORT_PATH} must be committed"


def test_baseline_report_has_required_keys():
    assert REPORT_PATH.exists()
    report = json.loads(REPORT_PATH.read_text())
    assert "metrics" in report
    m = report["metrics"]
    required_metric_keys = {
        "validity_accuracy", "exact_match", "per_code",
        "micro_f1", "macro_f1",
    }
    assert required_metric_keys <= set(m.keys())


def test_baseline_report_values_in_range():
    """All metric values should be in [0, 1] — no hardcoded magic numbers."""
    assert REPORT_PATH.exists()
    report = json.loads(REPORT_PATH.read_text())
    m = report["metrics"]
    for key in ("validity_accuracy", "exact_match", "micro_f1", "macro_f1"):
        val = m[key]
        assert 0.0 <= val <= 1.0, f"metric {key}={val} out of range"


def test_model_json_is_deterministic():
    """Loading model.json and running inference should give stable results."""
    if not MODEL_DIR.exists():
        pytest.skip("model artifact not found")
    from stele_ml.infer import load_model, predict_one
    artifact = load_model(MODEL_DIR)
    text = "theorem t using intuitionistic_prop:\n  assume h: P\n  conclude P by h\n"
    r1 = predict_one(text, artifact)
    r2 = predict_one(text, artifact)
    assert r1["predicted_valid"] == r2["predicted_valid"]
    assert r1["predicted_codes"] == r2["predicted_codes"]
