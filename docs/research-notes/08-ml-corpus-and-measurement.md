# 08 — ML Corpus and Measurement

**Status:** Optional, Experimental, Isolated
**Evidence:** `stele_ml/`, `bench/`, `stele_ml/reports/baseline_report.json`
**Doc:** `docs/benchmark-card.md`
**Tests:** `tests/test_ml_corpus_discipline.py`

---

## 8.1 Architecture and isolation

The ML baseline is explicitly **outside the trusted path**.

```
stele_ml/          (OPTIONAL, ISOLATED)
  train.py         MultinomialNaiveBayes training
  eval.py          evaluation + failure_mode_analysis
  data.py          split_three_way() (seeded, disjoint, exhaustive)
  build_dataset.py train/dev/test split builder
  artifacts/       trained model artifacts (not committed)
  reports/         baseline_report.json, training_report.json
```

**Import isolation:** `stele_ml/` does not import `stele.kernel`. The ML layer is
never in the trusted path. Enforced by `tests/test_regression_invariants.py`.

**Purpose:** Demonstrate that a classical ML approach can be trained on the
Stele corpus and evaluated against the symbolic verifier's ground truth. This is a
**classification** model (valid/invalid + diagnostic codes), not a proof generator.

---

## 8.2 Corpus description

**Source:** `bench/generate.py` (deterministic, templated)

| Corpus family | Proportion | Description |
|--------------|-----------|-------------|
| `prop_nd` | 60% | Natural-deduction proofs in propositional logic |
| `definition_use` | 20% | Proofs with formula definitions (valid + `UndefinedDefinition` errors) |
| `diagnostic_errors` | 20% | Proofs with injected errors (MissingHypothesis, InvalidTransition, etc.) |

| Split | Count (seed=0) | Location |
|-------|---------------|----------|
| Committed sample | 40 records | `bench/generated/sample/` |
| In-memory training set | 400 records | Generated on demand |
| Train split | 320 | `stele_ml/data/sample_split/` (generated) |
| Test split | 80 | `stele_ml/data/sample_split/` (generated) |

**Labels:** All labels (`expected_valid`, `expected_codes`) are produced by running the
symbolic checker and diagnostic module. No label is manually entered.

**Source:** `docs/benchmark-card.md §Dataset`

---

## 8.3 Model

**Type:** Multinomial Naive Bayes
**Features:** Bag-of-words (token n-gram) from Stele proof text
**Laplace smoothing:** α = 1.0
**External dependencies:** None (stdlib only)
**Vocab size:** 454 (from `stele_ml/reports/baseline_report.json`, field `n_vocab`)

---

## 8.4 Measured metrics

**Source:** `stele_ml/reports/baseline_report.json`
**Evaluation set:** n = 40 (committed sample)

> **Do not cite these numbers as "current accuracy."** These metrics are from the current
> committed report. Re-run the pipeline to get updated numbers.

### Validity classification

| Metric | Value | Source path |
|--------|-------|-------------|
| Validity accuracy | 0.85 (34/40) | `baseline_report.json .metrics.validity_accuracy` |

### Diagnostic code prediction (multi-label)

| Metric | Value | Source path |
|--------|-------|-------------|
| Exact match | 0.60 (24/40) | `.metrics.exact_match` |
| Macro F1 | 0.3611 | `.metrics.macro_f1` |
| Macro precision | 0.4167 | `.metrics.macro_precision` |
| Macro recall | 0.3333 | `.metrics.macro_recall` |
| Micro F1 | 0.50 | `.metrics.micro_f1` |
| Micro precision | 0.875 | `.metrics.micro_precision` |
| Micro recall | 0.35 | `.metrics.micro_recall` |

### Per-code breakdown (from `baseline_report.json`)

| Code | F1 | Precision | Recall | Support |
|------|-----|-----------|--------|---------|
| `InvalidTransition` | 0.50 | 0.50 | 0.50 | 2 |
| `MissingHypothesis` | 0.00 | 0.00 | 0.00 | 4 |
| `UndefinedDefinition` | 1.00 | 1.00 | 1.00 | 4 |
| `UndefinedSymbol` | 0.67 | 1.00 | 0.50 | 4 |
| `UnsupportedConclusion` | 0.00 | 0.00 | 0.00 | 3 |
| `UnusedAssumption` | 0.00 | 0.00 | 0.00 | 3 |

### Failure mode analysis

From `baseline_report.json .failure_mode_analysis`:

- **Well predicted (F1 ≥ 0.5):** `InvalidTransition`, `UndefinedDefinition`, `UndefinedSymbol`
- **Under predicted (recall < 0.5):** `MissingHypothesis`, `UnsupportedConclusion`, `UnusedAssumption`
- **Over predicted:** none
- **No support in test:** none (all 6 codes have support)

---

## 8.5 Known limitations

From `docs/benchmark-card.md §Known Limitations`:

1. **Template-level leakage:** Records within a corpus family share templates. Train/test
   split by record ID does not guarantee template-level separation.
2. **Small corpus:** 40 committed records; 400 in-memory training records. Both are too
   small to draw general conclusions.
3. **Synthetic distribution:** All proofs from a small template set. Does not reflect
   real user proofs.
4. **Naive Bayes limitation:** Bag-of-words model; no structural understanding of proofs.
5. **Class imbalance:** Some codes appear rarely; small support leads to unreliable F1.

---

## 8.6 Honesty constraints (mandatory for paper)

- Do not cite `0.85` validity accuracy as a general accuracy claim. It is a small-corpus,
  synthetic-data result.
- Do not present the ML baseline as competitive with LeanDojo [Yang2023] or similar systems.
- Do not present ML predictions as verified. Only `stele/kernel.py` verifies.
- If updated metrics are needed, re-run the pipeline (see `docs/benchmark-card.md §Reproducibility`).
- The ML baseline is UNTRUSTED and OPTIONAL. It is a demonstration of data discipline,
  not a production proof-classification system.

---

## 8.7 Data discipline features

From `docs/benchmark-card.md` and `stele_ml/`:

- Manifest schema (`manifests.json`) includes `label_stats` and `creation_command`
- 3-way train/dev/test split builder with seeded shuffle and disjointness verification
- Failure-mode analysis section in evaluation reports
- Benchmark card at `docs/benchmark-card.md` documenting limitations and reproduction steps
- All steps deterministic given the same seed
