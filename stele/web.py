"""Local web UI for Stele — Stele Studio HTTP server.

No third-party dependencies. The Python kernel remains the single source of
truth: this server only parses requests and calls check_theorem / the matrix
helpers, exactly as the CLI does.

Preferred launch:  python -m stele  [--port PORT] [--no-browser]
Legacy launch:     python -m stele.web  [PORT]
"""
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .parser import parse_theorem
from .kernel import check_theorem
from .errors import SteleError, ProofError, ParseError
from .matrix import (BOOLEAN, K3, LP, is_tautology, entails,
                     negation_fixpoints, evaluate)
from .ast import Var, Op

# In a PyInstaller one-file bundle sys._MEIPASS is the extraction root and data
# files land at {_MEIPASS}/stele/webapp/.  In normal source execution __file__
# resolves to the stele/ package directory directly.
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    HERE = os.path.join(sys._MEIPASS, 'stele')
else:
    HERE = os.path.dirname(os.path.abspath(__file__))

WEBAPP = os.path.join(HERE, "webapp")
EXAMPLES = os.path.normpath(os.path.join(HERE, "..", "examples"))
BENCH_REPORT = os.path.normpath(
    os.path.join(HERE, "..", "bench", "reports", "latest.json")
)


# ---------------------------------------------------------------------------
# JSON helper builders (pure functions — no I/O side effects)
# ---------------------------------------------------------------------------

def _matrix_json(m):
    vals = list(m.values)

    def unary(sym):
        return {a: m.tables[sym][(a,)] for a in vals}

    def binary(sym):
        return {a: {b: m.tables[sym][(a, b)] for b in vals} for a in vals}

    return {
        "name": m.name,
        "values": vals,
        "designated": sorted(m.designated, key=lambda v: m.rank[v]),
        "tables": {"not": unary("not"), "and": binary("and"),
                   "or": binary("or"), "imp": binary("imp")},
    }


def _demos_json():
    P, Q = Var("P"), Var("Q")
    notP = Op("not", (P,))
    lem = Op("or", (P, notP))
    ok_lp, cx = entails([P, notP], Q, LP)
    ok_cl, _ = entails([P, notP], Q, BOOLEAN)
    return {
        "matrices": [_matrix_json(K3), _matrix_json(LP), _matrix_json(BOOLEAN)],
        "results": {
            "lem_k3": is_tautology(lem, K3),
            "lem_classical": is_tautology(lem, BOOLEAN),
            "lem_value_at_I": evaluate(lem, {"P": "I"}, K3),
            "liar_k3": negation_fixpoints(K3),
            "liar_lp": negation_fixpoints(LP),
            "explosion_lp": ok_lp,
            "explosion_lp_counterexample": cx,
            "explosion_classical": ok_cl,
        },
    }


def _examples_json():
    out = {}
    if os.path.isdir(EXAMPLES):
        for fn in sorted(os.listdir(EXAMPLES)):
            if fn.endswith(".stele"):
                with open(os.path.join(EXAMPLES, fn), encoding="utf-8") as f:
                    out[fn] = f.read()
    return out


# ---------------------------------------------------------------------------
# API handler functions (importable for testing)
# ---------------------------------------------------------------------------

def check_source(source, logic):
    """Verify a proof. Returns a dict with ok/error/name/logic."""
    try:
        thm = parse_theorem(source)
    except ParseError as e:
        return {"ok": False, "kind": "parse", "error": str(e),
                "line": getattr(e, "line", None)}
    try:
        lg, _ = check_theorem(thm, logic or None)
    except ProofError as e:
        return {"ok": False, "kind": "proof", "name": thm.name,
                "error": str(e), "line": getattr(e, "line", None)}
    except SteleError as e:
        return {"ok": False, "kind": "error", "name": thm.name, "error": str(e)}
    return {"ok": True, "name": thm.name, "logic": lg.name}


def diagnose_source(source, logic):
    """Run multi-pass structural diagnostics. Returns diagnostics list."""
    try:
        thm = parse_theorem(source)
    except ParseError as e:
        return {"ok": False, "kind": "parse", "error": str(e),
                "line": getattr(e, "line", None), "diagnostics": []}
    from .diagnostics import diagnose_theorem
    logic_name = logic or thm.logic or "intuitionistic_prop"
    diags = diagnose_theorem(thm, logic_name)
    return {
        "ok": True,
        "name": thm.name,
        "logic": logic_name,
        "diagnostics": [
            {"code": d.code, "message": d.message,
             "line": d.line, "severity": d.severity}
            for d in diags
        ],
    }


def graph_source(source, logic):
    """Build the proof dependency graph. Returns nodes, edges, DOT text."""
    try:
        thm = parse_theorem(source)
    except ParseError as e:
        return {"ok": False, "kind": "parse", "error": str(e),
                "line": getattr(e, "line", None)}
    from .proofgraph import (build_proof_graph, to_dot,
                              has_cycle, find_unused_assumptions,
                              find_isolated_steps)
    logic_name = logic or thm.logic or "intuitionistic_prop"
    try:
        lg, _ = check_theorem(thm, logic_name)
    except (ProofError, SteleError) as e:
        return {"ok": False, "kind": "proof", "error": str(e), "name": thm.name}
    g = build_proof_graph(thm)
    issues = []
    if has_cycle(g):
        issues.append("cycle detected in dependency graph")
    unused = find_unused_assumptions(g)
    if unused:
        issues.append(f"unused assumptions: {', '.join(sorted(unused))}")
    iso = find_isolated_steps(g)
    if iso:
        issues.append(f"isolated steps: {', '.join(sorted(iso))}")
    return {
        "ok": True,
        "name": thm.name,
        "logic": lg.name,
        "nodes": [
            {"label": n.label, "kind": n.kind,
             "formula": n.formula, "rule": n.rule}
            for n in g.nodes.values()
        ],
        "edges": [{"src": s, "tgt": t} for s, t in g.edges],
        "diagnostics": issues,
        "dot": to_dot(g),
    }


def soundness_json(logic_name, matrix_name):
    """Return per-rule soundness report for a proof logic against a matrix."""
    if not logic_name:
        return {"ok": False, "error": "missing logic parameter"}
    if not matrix_name:
        return {"ok": False, "error": "missing matrix parameter"}
    from .logic import get_logic
    from .matrix import MATRICES, rule_soundness
    try:
        logic = get_logic(logic_name)
    except SteleError as e:
        return {"ok": False, "error": str(e)}
    if logic.semantics != "proof":
        return {"ok": False,
                "error": f"'{logic_name}' is a matrix logic; use a proof logic"}
    if matrix_name not in MATRICES:
        return {"ok": False,
                "error": f"unknown matrix '{matrix_name}'; "
                         f"available: {', '.join(sorted(MATRICES))}"}
    m = MATRICES[matrix_name]
    rules = []
    for name, schema in sorted(logic.rules.items()):
        r = rule_soundness(schema, m)
        entry = {"rule": name, "status": r.status}
        if r.status == "unsound" and r.counterexample:
            entry["counterexample"] = r.counterexample
        if r.status == "skipped" and r.reason:
            entry["reason"] = r.reason
        rules.append(entry)
    return {"ok": True, "logic": logic_name, "matrix": matrix_name, "rules": rules}


def lattice_json(formula_str):
    """Return CH-style world lattice status for a formula string."""
    if not formula_str:
        return {"ok": False, "error": "missing formula parameter"}
    from .parser import parse_formula
    from .ast import Op, pretty
    from .world import World, lattice_status
    try:
        phi = parse_formula(formula_str)
    except ParseError as e:
        return {"ok": False, "error": str(e)}
    neg = Op("not", (phi,))
    phi_s = pretty(phi)
    neg_s = pretty(neg)
    labelled = [
        ("Gamma",             World("boolean", ())),
        (f"Gamma + {phi_s}",  World("boolean", (phi,))),
        (f"Gamma + {neg_s}",  World("boolean", (neg,))),
    ]
    worlds = [w for _, w in labelled]
    rows = []
    for (label, w), (_, s) in zip(labelled, lattice_status(phi, worlds)):
        rows.append({
            "label": label,
            "axioms": [pretty(a) for a in w.axioms],
            "status": s,
        })
    return {"ok": True, "formula": phi_s, "rows": rows}


def kripke_json(formula_str, max_worlds=4):
    """Search for a finite Kripke countermodel and return structured JSON."""
    if not formula_str:
        return {"ok": False, "error": "missing formula parameter"}
    from .kripke import kripke_explain, explanation_to_dict
    try:
        max_w = int(max_worlds)
    except (TypeError, ValueError):
        max_w = 4
    max_w = max(1, min(max_w, 6))
    ex = kripke_explain(formula_str, max_worlds=max_w)
    d = explanation_to_dict(ex)
    d["ok"] = True
    return d


def metrics_json():
    """Load bench/reports/latest.json or return a clear not-found response."""
    if not os.path.isfile(BENCH_REPORT):
        return {
            "ok": False,
            "error": "no benchmark report found",
            "hint": (
                "Generate a report with:\n"
                "  python -m stele.eval bench "
                "--labels bench/labels.jsonl "
                "--tasks bench "
                "--report bench/reports/latest.json"
            ),
        }
    try:
        with open(BENCH_REPORT, encoding="utf-8") as f:
            data = json.load(f)
        return {"ok": True, "report": data}
    except Exception as e:
        return {"ok": False, "error": f"failed to read report: {e}"}


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        charset = "; charset=utf-8" if ("json" in ctype or "html" in ctype) else ""
        self.send_header("Content-Type", ctype + charset)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass

    def _path_qs(self):
        parsed = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        return parsed.path, qs

    def do_GET(self):
        path, qs = self._path_qs()
        if path in ("/", "/index.html"):
            with open(os.path.join(WEBAPP, "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html")
        elif path == "/api/demos":
            self._send(200, _demos_json())
        elif path == "/api/examples":
            self._send(200, _examples_json())
        elif path == "/api/soundness":
            self._send(200, soundness_json(
                qs.get("logic", ""), qs.get("matrix", "")))
        elif path == "/api/lattice":
            formula = qs.get("formula", "")
            if not formula:
                self._send(400, {"error": "missing formula parameter"})
            else:
                self._send(200, lattice_json(formula))
        elif path == "/api/kripke":
            formula = qs.get("formula", "")
            if not formula:
                self._send(400, {"ok": False, "error": "missing formula parameter"})
            else:
                self._send(200, kripke_json(formula, qs.get("max_worlds", 4)))
        elif path == "/api/metrics":
            self._send(200, metrics_json())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode("utf-8") if n else "{}"
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            self._send(400, {"error": "bad json"})
            return
        path, _ = self._path_qs()
        if path == "/api/check":
            self._send(200, check_source(
                req.get("source", ""), req.get("logic")))
        elif path == "/api/diagnose":
            self._send(200, diagnose_source(
                req.get("source", ""), req.get("logic")))
        elif path == "/api/graph":
            self._send(200, graph_source(
                req.get("source", ""), req.get("logic")))
        else:
            self._send(404, {"error": "not found"})


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

def main(port=8765, open_browser=True):
    """Start the Stele Studio local web server."""
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Stele Studio  ·  {url}   (Ctrl+C to stop)")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        srv.server_close()


if __name__ == "__main__":
    argv = sys.argv[1:]
    port = int(argv[0]) if argv else 8765
    main(port=port)
