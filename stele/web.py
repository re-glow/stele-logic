"""Local web UI for Stele -- a thin stdlib HTTP server over the existing checker.

No third-party dependencies. The Python kernel remains the single source of
truth: this server only parses requests and calls check_theorem / the matrix
helpers, exactly as the CLI does.

Run:  python -m stele.web  [port]
"""
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .parser import parse_theorem
from .kernel import check_theorem
from .errors import SteleError, ProofError, ParseError
from .matrix import (BOOLEAN, K3, LP, is_tautology, entails,
                     negation_fixpoints, evaluate)
from .ast import Var, Op

HERE = os.path.dirname(os.path.abspath(__file__))
WEBAPP = os.path.join(HERE, "webapp")
EXAMPLES = os.path.normpath(os.path.join(HERE, "..", "examples"))


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


def check_source(source, logic):
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

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(WEBAPP, "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html")
        elif self.path == "/api/demos":
            self._send(200, _demos_json())
        elif self.path == "/api/examples":
            self._send(200, _examples_json())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/check":
            self._send(404, {"error": "not found"})
            return
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode("utf-8") if n else "{}"
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            self._send(400, {"error": "bad json"})
            return
        self._send(200, check_source(req.get("source", ""), req.get("logic")))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    port = int(argv[0]) if argv else 8765
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Stele web UI running at {url}   (Ctrl+C to stop)")
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
    main()
