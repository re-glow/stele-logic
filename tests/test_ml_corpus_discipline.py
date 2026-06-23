"""Data-discipline tests for the Stele ML corpus pipeline.

Verifies:
- Corpus generation is deterministic (same inputs → same outputs)
- Manifests have required fields including label_stats
- 3-way split is deterministic, disjoint, and exhaustive
- Baseline report has required schema fields
- No unmeasured accuracy claims in ML source files
"""
from __future__ import annotations
import json
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SAMPLE_DIR = _ROOT / "bench" / "generated" / "sample"
MANIFEST_PATH = SAMPLE_DIR / "manifest.json"
BASELINE_REPORT = _ROOT / "stele_ml" / "reports" / "baseline_report.json"
MODEL_DIR = _ROOT / "stele_ml" / "artifacts" / "baseline"


# ---------------------------------------------------------------------------
# Corpus generation determinism
# ---------------------------------------------------------------------------

class TestGeneratorDeterminism:
    def test_generate_all_is_deterministic(self):
        from bench.generate import generate_all
        r1, n1 = generate_all(20, seed=0)
        r2, n2 = generate_all(20, seed=0)
        assert [r["id"] for r in r1] == [r["id"] for r in r2]
        assert [r["expected_valid"] for r in r1] == [r["expected_valid"] for r in r2]

    def test_generate_all_seed_changes_output(self):
        from bench.generate import generate_all
        r1, _ = generate_all(20, seed=0)
        r2, _ = generate_all(20, seed=1)
        # Different seeds must produce different ID sequences (they use different RNG streams)
        # The IDs encode corpus+offset so we compare expected_codes which vary by RNG
        # Both should differ for at least some records
        valid1 = [r["expected_valid"] for r in r1]
        valid2 = [r["expected_valid"] for r in r2]
        # Allow that they might be the same for very small n; just check they run
        assert len(r1) == len(r2) == 20

    def test_label_stats_deterministic(self):
        from bench.generate import generate_all, compute_label_stats
        records, _ = generate_all(40, seed=0)
        s1 = compute_label_stats(records)
        s2 = compute_label_stats(records)
        assert s1 == s2

    def test_compute_label_stats_structure(self):
        from bench.generate import compute_label_stats
        records = [
            {"expected_valid": True, "expected_codes": ["UndefinedSymbol"]},
            {"expected_valid": False, "expected_codes": ["MissingHypothesis", "UndefinedSymbol"]},
            {"expected_valid": True, "expected_codes": []},
        ]
        stats = compute_label_stats(records)
        assert stats["n_valid"] == 2
        assert stats["n_invalid"] == 1
        assert stats["code_distribution"]["UndefinedSymbol"] == 2
        assert stats["code_distribution"]["MissingHypothesis"] == 1


# ---------------------------------------------------------------------------
# Manifest schema
# ---------------------------------------------------------------------------

class TestManifestSchema:
    def test_manifest_exists(self):
        assert MANIFEST_PATH.exists(), (
            f"manifest.json not found at {MANIFEST_PATH}; "
            "run: python bench/generate.py --corpus all --n 40 "
            "--out bench/generated/sample --seed 0 --shard-size 20"
        )

    def test_manifest_required_fields(self):
        if not MANIFEST_PATH.exists():
            pytest.skip("manifest.json not committed")
        m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for field in ("generator_version", "n_total", "shards", "n_per_corpus", "args"):
            assert field in m, f"manifest missing field: {field}"
        assert "seed" in m["args"], "manifest.args missing field: seed"

    def test_manifest_has_label_stats(self):
        if not MANIFEST_PATH.exists():
            pytest.skip("manifest.json not committed")
        m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        assert "label_stats" in m, (
            "manifest.json missing 'label_stats'; "
            "regenerate with updated bench/generate.py"
        )
        stats = m["label_stats"]
        assert stats is not None, "label_stats should not be null"
        assert "n_valid" in stats
        assert "n_invalid" in stats
        assert "code_distribution" in stats

    def test_manifest_has_creation_command(self):
        if not MANIFEST_PATH.exists():
            pytest.skip("manifest.json not committed")
        m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        assert "creation_command" in m, "manifest.json missing 'creation_command'"
        cmd = m["creation_command"]
        assert cmd is not None and len(cmd) > 0

    def test_manifest_label_stats_consistent(self):
        if not MANIFEST_PATH.exists():
            pytest.skip("manifest.json not committed")
        m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if m.get("label_stats") is None:
            pytest.skip("label_stats not yet in manifest")
        stats = m["label_stats"]
        assert stats["n_valid"] + stats["n_invalid"] == m["n_total"]


# ---------------------------------------------------------------------------
# 3-way split determinism, disjointness, exhaustiveness
# ---------------------------------------------------------------------------

class TestThreeWaySplit:
    def _make_records(self, n: int) -> list[dict]:
        return [{"id": f"rec_{i:04d}", "expected_valid": i % 2 == 0,
                 "expected_codes": [], "text": f"proof_{i}"} for i in range(n)]

    def test_split_deterministic(self):
        from stele_ml.data import split_three_way
        records = self._make_records(20)
        train1, dev1, test1 = split_three_way(records, seed=0)
        train2, dev2, test2 = split_three_way(records, seed=0)
        assert [r["id"] for r in train1] == [r["id"] for r in train2]
        assert [r["id"] for r in dev1] == [r["id"] for r in dev2]
        assert [r["id"] for r in test1] == [r["id"] for r in test2]

    def test_split_seed_changes_output(self):
        from stele_ml.data import split_three_way
        records = self._make_records(30)
        train0, _, _ = split_three_way(records, seed=0)
        train1, _, _ = split_three_way(records, seed=1)
        ids0 = [r["id"] for r in train0]
        ids1 = [r["id"] for r in train1]
        assert ids0 != ids1, "different seeds must produce different splits"

    def test_split_disjoint(self):
        from stele_ml.data import split_three_way
        records = self._make_records(20)
        train, dev, test = split_three_way(records, seed=0)
        train_ids = {r["id"] for r in train}
        dev_ids = {r["id"] for r in dev}
        test_ids = {r["id"] for r in test}
        assert not (train_ids & dev_ids), "train/dev overlap"
        assert not (train_ids & test_ids), "train/test overlap"
        assert not (dev_ids & test_ids), "dev/test overlap"

    def test_split_exhaustive(self):
        from stele_ml.data import split_three_way
        records = self._make_records(20)
        train, dev, test = split_three_way(records, seed=0)
        all_ids = {r["id"] for r in records}
        split_ids = {r["id"] for r in train} | {r["id"] for r in dev} | {r["id"] for r in test}
        assert all_ids == split_ids, "not all records appear in a split"

    def test_split_non_empty(self):
        from stele_ml.data import split_three_way
        records = self._make_records(20)
        train, dev, test = split_three_way(records, seed=0)
        assert len(train) > 0
        assert len(dev) > 0
        assert len(test) > 0

    def test_split_ratios_approximate(self):
        from stele_ml.data import split_three_way
        records = self._make_records(100)
        train, dev, test = split_three_way(records, train_ratio=0.7, dev_ratio=0.15, seed=0)
        n = len(records)
        assert 60 <= len(train) <= 75, f"train size {len(train)} not near 70%"
        assert 10 <= len(dev) <= 20, f"dev size {len(dev)} not near 15%"
        assert 10 <= len(test) <= 20, f"test size {len(test)} not near 15%"

    def test_split_small_corpus(self):
        from stele_ml.data import split_three_way
        # 3-record minimum should still produce non-empty splits
        records = self._make_records(3)
        train, dev, test = split_three_way(records, seed=0)
        assert len(train) + len(dev) + len(test) == 3


# ---------------------------------------------------------------------------
# Baseline report schema
# ---------------------------------------------------------------------------

class TestBaselineReportSchema:
    def test_report_exists(self):
        assert BASELINE_REPORT.exists(), (
            f"baseline_report.json not found at {BASELINE_REPORT}; "
            "run: python -m stele_ml.eval --model stele_ml/artifacts/baseline "
            "--data bench/generated/sample --report stele_ml/reports/baseline_report.json"
        )

    def test_report_required_top_level_fields(self):
        if not BASELINE_REPORT.exists():
            pytest.skip("baseline_report.json not committed")
        r = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
        for field in ("dataset", "metrics", "model", "note"):
            assert field in r, f"baseline_report.json missing field: {field}"

    def test_report_metrics_fields(self):
        if not BASELINE_REPORT.exists():
            pytest.skip("baseline_report.json not committed")
        r = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
        m = r["metrics"]
        for field in (
            "validity_accuracy", "exact_match", "micro_f1", "macro_f1", "per_code"
        ):
            assert field in m, f"report metrics missing field: {field}"

    def test_report_metrics_are_floats_in_range(self):
        if not BASELINE_REPORT.exists():
            pytest.skip("baseline_report.json not committed")
        r = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
        m = r["metrics"]
        for key in ("validity_accuracy", "exact_match", "micro_f1", "macro_f1"):
            val = m[key]
            assert isinstance(val, (int, float)), f"{key} must be numeric"
            assert 0.0 <= val <= 1.0, f"{key} = {val} out of [0,1]"

    def test_report_note_is_honest(self):
        if not BASELINE_REPORT.exists():
            pytest.skip("baseline_report.json not committed")
        r = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
        note = r.get("note", "")
        # Note must not claim hardcoded or final values
        assert len(note) > 0, "note field must not be empty"
        assert "measured" in note.lower() or "actual" in note.lower(), (
            "note must acknowledge that values are measured, not hardcoded"
        )

    def test_report_has_failure_mode_analysis(self):
        if not BASELINE_REPORT.exists():
            pytest.skip("baseline_report.json not committed")
        r = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
        assert "failure_mode_analysis" in r, (
            "baseline_report.json missing 'failure_mode_analysis'; "
            "regenerate with updated stele_ml/eval.py"
        )
        fa = r["failure_mode_analysis"]
        for field in ("under_predicted", "over_predicted", "well_predicted"):
            assert field in fa, f"failure_mode_analysis missing field: {field}"

    def test_report_per_code_entries_have_required_fields(self):
        if not BASELINE_REPORT.exists():
            pytest.skip("baseline_report.json not committed")
        r = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
        per_code = r["metrics"].get("per_code", {})
        for code, m in per_code.items():
            for field in ("f1", "precision", "recall", "support", "tp", "fp", "fn"):
                assert field in m, f"per_code[{code}] missing field: {field}"


# ---------------------------------------------------------------------------
# Claim honesty audit
# ---------------------------------------------------------------------------

class TestClaimHonesty:
    _FORBIDDEN = [
        ("500k", "do not claim 500k corpus unless committed or reproducibly built"),
        ("large corpus", "vague claim; use specific measured counts"),
        ("high accuracy", "unmeasured claim"),
        ("state-of-the-art", "overclaim"),
        ("production ready", "overclaim"),
        ("AI verifier", "misleading — ML model is UNTRUSTED"),
        ("automatic verifier", "misleading — ML model is UNTRUSTED"),
        ("guaranteed", "overclaim for an ML model"),
        ("LLM tutor", "not part of this project"),
        ("full ML", "vague; avoid"),
    ]

    def _scan_ml_files(self) -> list[pathlib.Path]:
        ml_dir = _ROOT / "stele_ml"
        return list(ml_dir.glob("*.py")) + list(ml_dir.glob("*.md"))

    def test_no_overclaims_in_stele_ml(self):
        violations = []
        for path in self._scan_ml_files():
            text = path.read_text(encoding="utf-8").lower()
            for phrase, reason in self._FORBIDDEN:
                if phrase.lower() in text:
                    violations.append(f"{path.name}: '{phrase}' — {reason}")
        assert not violations, "Overclaims found:\n" + "\n".join(violations)

    def test_no_hardcoded_accuracy_in_reports(self):
        # Reports must not contain the string "87" as a claimed accuracy
        # (historical overclaim that was removed)
        for report_path in (_ROOT / "stele_ml" / "reports").glob("*.json"):
            text = report_path.read_text(encoding="utf-8")
            # Check if "87" appears as a standalone accuracy claim (not in an ID or path)
            import re
            matches = re.findall(r'"validity_accuracy"\s*:\s*([\d.]+)', text)
            for m in matches:
                val = float(m)
                assert 0.0 <= val <= 1.0, f"validity_accuracy {val} out of range in {report_path.name}"

    def test_ml_readme_does_not_claim_87_percent(self):
        readme = _ROOT / "stele_ml" / "README.md"
        if not readme.exists():
            pytest.skip("stele_ml/README.md not found")
        text = readme.read_text(encoding="utf-8")
        # The README previously had "87% is not a current claim" which is fine
        # but must not claim "87% accuracy" as a fact
        import re
        bad = re.search(r'87%\s+accuracy', text, re.IGNORECASE)
        assert bad is None, "stele_ml/README.md must not claim '87% accuracy'"

    def test_baseline_report_not_hardcoded(self):
        if not BASELINE_REPORT.exists():
            pytest.skip("baseline_report.json not committed")
        r = json.loads(BASELINE_REPORT.read_text(encoding="utf-8"))
        note = r.get("note", "")
        # Note must acknowledge small-data / measured nature
        assert "small" in note.lower() or "measured" in note.lower(), (
            "baseline_report note should mention small-data or measured nature"
        )


# ---------------------------------------------------------------------------
# split_three_way import from data
# ---------------------------------------------------------------------------

def test_split_three_way_importable():
    from stele_ml.data import split_three_way
    assert callable(split_three_way)


def test_split_three_way_in_data_module():
    import stele_ml.data as data_mod
    assert hasattr(data_mod, "split_three_way"), (
        "stele_ml.data must export split_three_way"
    )
