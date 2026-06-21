"""Multinomial Naive Bayes and one-vs-rest multi-label classifier (stdlib only).

Both classes are fully serializable to/from plain Python dicts (JSON-safe)
so model artifacts can be stored as small .json files without pickle.

All class labels are stored as strings internally to ensure JSON round-trip
stability (JSON object keys are always strings).
"""
from __future__ import annotations
import math


class MultinomialNB:
    """Multinomial Naive Bayes with additive (Laplace) smoothing.

    Inputs:
        X: list of feature vectors (list[list[float]])
        y: list of string labels

    All class keys are stored as strings in serialized form.
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = float(alpha)
        self.classes_: list[str] = []
        self.log_class_prior_: dict[str, float] = {}
        self.log_feature_prob_: dict[str, list[float]] = {}
        self.n_features_: int = 0

    def fit(self, X: list[list[float]], y: list[str]) -> "MultinomialNB":
        n = len(X)
        self.n_features_ = len(X[0]) if X else 0
        self.classes_ = sorted(set(y))

        for cls in self.classes_:
            indices = [i for i, yi in enumerate(y) if yi == cls]
            self.log_class_prior_[cls] = math.log(len(indices) / n)

            feat_sum = [0.0] * self.n_features_
            for i in indices:
                for j, v in enumerate(X[i]):
                    feat_sum[j] += v

            denom = sum(feat_sum) + self.alpha * self.n_features_
            self.log_feature_prob_[cls] = [
                math.log((feat_sum[j] + self.alpha) / denom)
                for j in range(self.n_features_)
            ]
        return self

    def _log_joint(self, x: list[float], cls: str) -> float:
        lp = self.log_class_prior_[cls]
        lfp = self.log_feature_prob_[cls]
        for j, v in enumerate(x):
            if v > 0.0:
                lp += v * lfp[j]
        return lp

    def predict(self, X: list[list[float]]) -> list[str]:
        return [max(self.classes_, key=lambda c: self._log_joint(x, c)) for x in X]

    def predict_proba(self, X: list[list[float]]) -> list[dict[str, float]]:
        """Return softmax-normalized class probabilities."""
        result = []
        for x in X:
            log_probs = {cls: self._log_joint(x, cls) for cls in self.classes_}
            max_lp = max(log_probs.values())
            exp_p = {cls: math.exp(lp - max_lp) for cls, lp in log_probs.items()}
            total = sum(exp_p.values())
            result.append({cls: p / total for cls, p in exp_p.items()})
        return result

    def to_dict(self) -> dict:
        return {
            "alpha": self.alpha,
            "classes_": self.classes_,
            "log_class_prior_": dict(self.log_class_prior_),
            "log_feature_prob_": dict(self.log_feature_prob_),
            "n_features_": self.n_features_,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MultinomialNB":
        nb = cls(alpha=d["alpha"])
        nb.classes_ = d["classes_"]
        nb.log_class_prior_ = d["log_class_prior_"]
        nb.log_feature_prob_ = d["log_feature_prob_"]
        nb.n_features_ = d["n_features_"]
        return nb


class OneVsRestNB:
    """One-vs-rest multi-label classifier using MultinomialNB.

    For each label, trains a binary NB model predicting "pos" or "neg".
    Labels with zero positive training examples are skipped (never predicted).
    """

    def __init__(self, alpha: float = 1.0, threshold: float = 0.5) -> None:
        self.alpha = float(alpha)
        self.threshold = float(threshold)
        self.labels_: list[str] = []
        self.binary_models_: dict[str, MultinomialNB | None] = {}

    def fit(
        self,
        X: list[list[float]],
        Y: list[set[str]],
        labels: list[str],
    ) -> "OneVsRestNB":
        self.labels_ = sorted(labels)
        for label in self.labels_:
            y_bin = ["pos" if label in y_set else "neg" for y_set in Y]
            n_pos = sum(1 for yb in y_bin if yb == "pos")
            if n_pos == 0:
                self.binary_models_[label] = None  # always predicts absent
            else:
                nb = MultinomialNB(alpha=self.alpha)
                nb.fit(X, y_bin)
                self.binary_models_[label] = nb
        return self

    def predict(self, X: list[list[float]]) -> list[list[str]]:
        result = []
        for x in X:
            predicted = []
            for label in self.labels_:
                nb = self.binary_models_.get(label)
                if nb is None:
                    continue
                proba = nb.predict_proba([x])[0]
                if proba.get("pos", 0.0) >= self.threshold:
                    predicted.append(label)
            result.append(predicted)
        return result

    def predict_proba(self, X: list[list[float]]) -> list[dict[str, float]]:
        """Return per-label probability of being present."""
        result = []
        for x in X:
            proba: dict[str, float] = {}
            for label in self.labels_:
                nb = self.binary_models_.get(label)
                if nb is None:
                    proba[label] = 0.0
                else:
                    p = nb.predict_proba([x])[0]
                    proba[label] = round(p.get("pos", 0.0), 4)
            result.append(proba)
        return result

    def to_dict(self) -> dict:
        return {
            "alpha": self.alpha,
            "threshold": self.threshold,
            "labels_": self.labels_,
            "binary_models_": {
                label: (m.to_dict() if m is not None else None)
                for label, m in self.binary_models_.items()
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OneVsRestNB":
        ovr = cls(alpha=d["alpha"], threshold=d["threshold"])
        ovr.labels_ = d["labels_"]
        ovr.binary_models_ = {
            label: (MultinomialNB.from_dict(m) if m is not None else None)
            for label, m in d["binary_models_"].items()
        }
        return ovr
