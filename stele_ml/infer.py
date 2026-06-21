"""Inference CLI for the stele_ml baseline.

Usage:
    # From raw text
    python -m stele_ml.infer --model stele_ml/artifacts/baseline \\
        --text "theorem t using intuitionistic_prop: ..."

    # From a .stele file
    python -m stele_ml.infer --model stele_ml/artifacts/baseline \\
        --file examples/dne.stele

Output:
    predicted_valid: true/false
    predicted_codes: [list of diagnostic codes]
    code_probabilities: {code: probability}  (if model supports it)

NOTE: This is a statistical approximation. For authoritative proof
validation, use: python -m stele.cli check <file> --logic <logic>
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from stele_ml.featurize import featurize
from stele_ml.classifier import MultinomialNB, OneVsRestNB


def load_model(model_dir: str | pathlib.Path) -> dict:
    path = pathlib.Path(model_dir) / "model.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def predict_one(text: str, artifact: dict) -> dict:
    """Run a single inference on proof text.

    Returns a dict with:
        predicted_valid: bool
        predicted_valid_label: "valid" or "invalid"
        valid_confidence: float (0-1)
        predicted_codes: list of diagnostic code strings
        code_probabilities: dict {code: float}
    """
    vocab = artifact["vocabulary"]
    x = featurize(text, vocab)

    valid_model = MultinomialNB.from_dict(artifact["validity_model"])
    code_model = OneVsRestNB.from_dict(artifact["code_model"])

    # Validity prediction
    valid_label = valid_model.predict([x])[0]
    valid_proba = valid_model.predict_proba([x])[0]
    valid_conf = round(valid_proba.get(valid_label, 0.5), 4)

    # Code predictions
    code_preds = code_model.predict([x])[0]
    code_proba = code_model.predict_proba([x])[0]

    return {
        "predicted_valid": valid_label == "valid",
        "predicted_valid_label": valid_label,
        "valid_confidence": valid_conf,
        "predicted_codes": sorted(code_preds),
        "code_probabilities": {k: round(v, 4) for k, v in sorted(code_proba.items())},
        "disclaimer": (
            "Statistical approximation only. "
            "Use 'python -m stele.cli check' for authoritative validation."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m stele_ml.infer",
        description=(
            "Run stele_ml baseline inference on a proof text.\n"
            "Output is a statistical approximation — not authoritative validation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--model", required=True,
                    help="directory containing model.json artifact")
    ap.add_argument("--text", default=None,
                    help="raw proof text to predict")
    ap.add_argument("--file", default=None,
                    help="path to a .stele file to predict")
    ap.add_argument("--json", action="store_true", dest="json_output",
                    help="output results as JSON")
    args = ap.parse_args(argv)

    if not args.text and not args.file:
        ap.error("provide --text or --file")

    text: str
    if args.file:
        text = pathlib.Path(args.file).read_text(encoding="utf-8")
    else:
        text = args.text

    artifact = load_model(args.model)
    result = predict_one(text, artifact)

    if args.json_output:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"predicted_valid  : {result['predicted_valid']}"
              f"  (confidence: {result['valid_confidence']:.3f})")
        print(f"predicted_codes  : {result['predicted_codes']}")
        print("code_probabilities:")
        for code, prob in result["code_probabilities"].items():
            print(f"  {code:25s}: {prob:.4f}")
        print()
        print(f"⚠  {result['disclaimer']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
