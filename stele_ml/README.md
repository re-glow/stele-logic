# stele_ml — ML Baseline for Stele Proof Verification

Isolated optional package providing a **statistical approximation baseline**
for the Stele proof-verification system.

## Purpose

The symbolic checker (`stele/kernel.py`) is the authoritative validator.
This package adds a separate, untrusted ML layer that can:

1. Predict whether a proof task is likely valid or invalid
2. Predict which diagnostic codes are likely to appear

This is useful for:
- Studying what surface text patterns correlate with specific error codes
- Measuring how much a simple baseline can learn from proof structure
- Supporting future research on ML-assisted proof validation

> **Architecture invariant:** `stele/` never imports `stele_ml`.
> ML is optional and lives entirely outside the trusted core.

---

## Honesty Policy

- **Only report measured values.** All metrics in `reports/` come from
  running the pipeline, not from manual entry.
- **87% is not a current claim.** If any future version achieves 87%,
  it will appear in a measured report — not in prose.
- **Small-sample metrics are not final.** The committed baseline trains on
  400 synthetic examples; treat those numbers as a smoke-test baseline.
- **This model does not prove anything.** Only the symbolic kernel proves.

---

## Installation

The baseline runs **without any external dependencies** (pure Python stdlib).

For an optional scikit-learn-backed upgrade:

```bash
pip install -r stele_ml/requirements-ml.txt
```

---

## Commands

### Train

```bash
# Default: generate 400 examples in-memory (deterministic, seed=0)
python -m stele_ml.train --out stele_ml/artifacts/baseline

# From committed sample corpus (40 examples)
python -m stele_ml.train --data bench/generated/sample --out stele_ml/artifacts/baseline

# From curated benchmark (31 tasks)
python -m stele_ml.train --labels bench/labels.jsonl --tasks bench --out stele_ml/artifacts/baseline

# Generate a larger in-memory corpus
python -m stele_ml.train --n-generated 1000 --out stele_ml/artifacts/baseline --report /tmp/report.json
```

### Evaluate

```bash
# Evaluate on committed sample, write report
python -m stele_ml.eval \
    --model stele_ml/artifacts/baseline \
    --data bench/generated/sample \
    --report stele_ml/reports/baseline_report.json

# Verbose per-example output
python -m stele_ml.eval \
    --model stele_ml/artifacts/baseline \
    --data bench/generated/sample \
    --verbose
```

### Infer

```bash
# Raw text
python -m stele_ml.infer \
    --model stele_ml/artifacts/baseline \
    --text "theorem t using intuitionistic_prop:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
  conclude Q by h3"

# From a .stele file (JSON output)
python -m stele_ml.infer \
    --model stele_ml/artifacts/baseline \
    --file examples/dne.stele \
    --json
```

---

## Report Interpretation

The committed `reports/baseline_report.json` contains:

| Field | Meaning |
|-------|---------|
| `validity_accuracy` | Fraction of examples where validity prediction is correct |
| `exact_match` | Validity correct AND all codes correct |
| `micro_f1` | F1 averaged across all code predictions (weighted by frequency) |
| `macro_f1` | F1 averaged over codes that appear in the test set |
| `per_code.{code}.f1` | Per-code F1 for each diagnostic code |
| `per_code.{code}.support` | Number of test examples with this code |

Codes with `support=0` in the test set are excluded from macro averages.

---

## Architecture

```
stele_ml/
  __init__.py       Package init
  featurize.py      Bag-of-words tokenizer + vocabulary builder + feature vectors
  classifier.py     MultinomialNB + OneVsRestNB (stdlib, JSON-serializable)
  data.py           Dataset loading (JSONL shards, bench labels, in-memory generation)
  _metrics.py       P/R/F1 computation (micro, macro, per-code)
  train.py          Training CLI
  eval.py           Evaluation CLI
  infer.py          Inference CLI
  artifacts/
    baseline/
      model.json    Trained model (small JSON, safe to commit)
  reports/
    baseline_report.json    Measured evaluation report
  requirements-ml.txt       Optional sklearn upgrade
  README.md                 This file
```

### Model Details (v1 baseline)

- **Type:** Multinomial Naive Bayes with Laplace smoothing (α=1.0)
- **Features:** Bag-of-words over identifier tokens from proof text
- **Validity model:** Binary (`valid` / `invalid`)
- **Code model:** One-vs-rest binary NB per diagnostic code
- **No external deps:** Fits and predicts with pure Python stdlib
- **Serialization:** JSON (no pickle, no binary formats)

---

## Tests

```bash
python -m pytest tests/test_ml_isolation.py tests/test_ml_baseline.py -v
```

The full core suite also passes without ML dependencies:

```bash
python -m pytest -q
```
