"""Proof certificate emission for Stele proof scripts.

A certificate is a versioned JSON document that records a verified proof
in a canonical normalized form.  It is self-contained: minicheck.py can
re-verify it without accessing the original .stele source file or calling
the main kernel/parser/diagnostics layers.

Certificate format:
  {
    "format":     "stele-proof-certificate",
    "version":    "1",
    "theorem":    <str>,
    "logic":      <str>,
    "conclusion": <formula_json>,
    "steps":      [<step_json>, ...],
    "metadata":   {"generator": "stele", "stele_version": <str>}
  }

Formula JSON:
  Atom   : {"kind": "var", "name": "P"}
  Bottom : {"kind": "bot"}
  Op     : {"kind": "op",  "op": "imp", "args": [...]}
           (op values: "imp" | "and" | "or" | "not")

Step JSON:
  {"kind": "assume",       "label": str, "formula": formula_json}
  {"kind": "suppose_open", "label": str, "formula": formula_json}
  {"kind": "suppose_close","label": str}
  {"kind": "have",         "label": str, "formula": formula_json,
                            "rule": str,  "refs": [str, ...]}
  {"kind": "conclude",     "ref": str,   "formula": formula_json}

Discharge rules encode their subproof references via refs pairs that
correspond to (suppose_open.label, inner_have.label).  The suppose_open
/ suppose_close brackets allow minicheck to reconstruct which labels
were derived inside which scope without re-parsing the source.
"""
import json as _json

from .ast import Var, Op, pretty
from .proof import Assume, Have, Suppose, Conclude


# ---------------------------------------------------------------------------
# Formula serialization
# ---------------------------------------------------------------------------

def formula_to_json(f) -> dict:
    """Serialize a formula to a JSON-compatible dict.

    Only propositional formulas (Var, Op with sym in {imp,and,or,not,bot})
    are handled.  Raises ValueError for unsupported constructs.
    """
    if isinstance(f, Var):
        return {"kind": "var", "name": f.name}
    if isinstance(f, Op):
        if f.sym == "bot":
            return {"kind": "bot"}
        if f.sym in ("imp", "and", "or"):
            return {"kind": "op", "op": f.sym,
                    "args": [formula_to_json(a) for a in f.args]}
        if f.sym == "not":
            return {"kind": "op", "op": "not",
                    "args": [formula_to_json(f.args[0])]}
        raise ValueError(
            f"formula_to_json: unsupported connective {f.sym!r}")
    raise ValueError(
        f"formula_to_json: unsupported formula type {type(f).__name__}")


def formula_from_json(d) -> object:
    """Deserialize a formula from its JSON-compatible dict representation.

    Returns Var | Op.  Raises ValueError on malformed input.
    """
    if not isinstance(d, dict):
        raise ValueError(f"formula_from_json: expected dict, got {type(d).__name__}")
    kind = d.get("kind")
    if kind == "var":
        return Var(d["name"])
    if kind == "bot":
        return Op("bot", ())
    if kind == "op":
        op = d["op"]
        args = tuple(formula_from_json(a) for a in d.get("args", []))
        return Op(op, args)
    raise ValueError(f"formula_from_json: unknown kind {kind!r}")


# ---------------------------------------------------------------------------
# Certificate emission
# ---------------------------------------------------------------------------

def emit_certificate(thm, logic_name: str) -> dict:
    """Verify the proof with the main kernel, then emit a certificate.

    Calls the main kernel's check_theorem first.  If verification fails,
    raises ProofError (from the kernel) rather than emitting a certificate.
    Only emits on verified success.

    Parameters
    ----------
    thm : Theorem
        A parsed Theorem object (from stele.parser).
    logic_name : str
        Logic name override (e.g. "intuitionistic_prop", "classical_prop").

    Returns
    -------
    dict  — JSON-serializable certificate.
    """
    from .kernel import check_theorem
    from .__version__ import __version__ as _ver

    # Verification gate: raises ProofError if proof is invalid.
    resolved_logic, conclusion_formula = check_theorem(thm, logic_name)

    steps = []
    _flatten_to_steps(thm.lines, steps)

    return {
        "format":     "stele-proof-certificate",
        "version":    "1",
        "theorem":    thm.name,
        "logic":      resolved_logic.name,
        "conclusion": formula_to_json(conclusion_formula),
        "steps":      steps,
        "metadata":   {
            "generator":     "stele",
            "stele_version": _ver,
        },
    }


def _flatten_to_steps(nodes, steps: list):
    """Recursively flatten a proof-node sequence to certificate steps."""
    for node in nodes:
        if isinstance(node, Assume):
            steps.append({
                "kind":    "assume",
                "label":   node.label,
                "formula": formula_to_json(node.formula),
            })
        elif isinstance(node, Suppose):
            steps.append({
                "kind":    "suppose_open",
                "label":   node.label,
                "formula": formula_to_json(node.formula),
            })
            _flatten_to_steps(node.body, steps)
            steps.append({
                "kind":  "suppose_close",
                "label": node.label,
            })
        elif isinstance(node, Have):
            steps.append({
                "kind":    "have",
                "label":   node.label,
                "formula": formula_to_json(node.formula),
                "rule":    node.rule,
                "refs":    list(node.refs),
            })
        elif isinstance(node, Conclude):
            steps.append({
                "kind":    "conclude",
                "ref":     node.ref,
                "formula": formula_to_json(node.formula),
            })


# ---------------------------------------------------------------------------
# JSON serialization helpers
# ---------------------------------------------------------------------------

def certificate_to_json(cert: dict, *, indent: int = 2) -> str:
    """Serialize a certificate dict to a JSON string."""
    return _json.dumps(cert, indent=indent, ensure_ascii=False)


def certificate_from_json(text: str) -> dict:
    """Deserialize a certificate from a JSON string.

    Raises ValueError on malformed JSON or missing required fields.
    """
    try:
        cert = _json.loads(text)
    except _json.JSONDecodeError as e:
        raise ValueError(f"certificate_from_json: invalid JSON — {e}") from e
    _validate_cert_structure(cert)
    return cert


def _validate_cert_structure(cert: dict):
    required = ("format", "version", "theorem", "logic", "conclusion", "steps")
    for key in required:
        if key not in cert:
            raise ValueError(f"certificate_from_json: missing required field {key!r}")
    if cert["format"] != "stele-proof-certificate":
        raise ValueError(
            f"certificate_from_json: unrecognised format {cert['format']!r}")
    if cert["version"] != "1":
        raise ValueError(
            f"certificate_from_json: unsupported version {cert['version']!r}")
