"""Many-valued (matrix) semantics -- the |= side of the framework.

K3 and LP use the Kleene strong tables (the tables from 유리학개론, pp.4-5);
they differ only in which values are *designated*. This is the executable
form of the manifesto's claims about a third truth value, the Liar, and the
locality of non-contradiction.
"""
import itertools
from .ast import Var, Op


class Matrix:
    def __init__(self, name, order, designated):
        self.name = name
        self.values = tuple(order)            # low -> high
        self.designated = frozenset(designated)
        self.rank = {v: i for i, v in enumerate(order)}
        self.tables = {}
        self._build()

    def _build(self):
        vals, rank = self.values, self.rank
        mx = len(vals) - 1
        inv = {v: vals[mx - rank[v]] for v in vals}                 # not: mirror
        self.tables["not"] = {(v,): inv[v] for v in vals}
        self.tables["and"] = {(a, b): (a if rank[a] <= rank[b] else b)
                              for a in vals for b in vals}          # and = min
        self.tables["or"] = {(a, b): (a if rank[a] >= rank[b] else b)
                             for a in vals for b in vals}           # or = max
        self.tables["imp"] = {(a, b): self.tables["or"][(inv[a], b)]
                              for a in vals for b in vals}          # a->b = ~a or b


def evaluate(f, val, m):
    if isinstance(f, Var):
        return val[f.name]
    if f.sym == "bot":          # Op("bot",()) = false; no table entry needed
        return m.values[0]
    return m.tables[f.sym][tuple(evaluate(a, val, m) for a in f.args)]


def variables(f, acc=None):
    if acc is None:
        acc = set()
    if isinstance(f, Var):
        acc.add(f.name)
    else:
        for a in f.args:
            variables(a, acc)
    return acc


def _valuations(varnames, m):
    names = sorted(varnames)
    for combo in itertools.product(m.values, repeat=len(names)):
        yield dict(zip(names, combo))


def is_tautology(f, m):
    return all(evaluate(f, v, m) in m.designated for v in _valuations(variables(f), m))


def entails(premises, conclusion, m):
    vs = set()
    for p in premises:
        variables(p, vs)
    variables(conclusion, vs)
    for v in _valuations(vs, m):
        if all(evaluate(p, v, m) in m.designated for p in premises):
            if evaluate(conclusion, v, m) not in m.designated:
                return False, v
    return True, None


def negation_fixpoints(m):
    return [x for x in m.values if m.tables["not"][(x,)] == x]


BOOLEAN = Matrix("boolean", ["F", "T"], {"T"})
K3 = Matrix("K3", ["F", "I", "T"], {"T"})
LP = Matrix("LP", ["F", "B", "T"], {"T", "B"})
MATRICES = {m.name: m for m in (BOOLEAN, K3, LP)}


def run_demos():
    P, Q = Var("P"), Var("Q")
    notP = Op("not", (P,))
    lem = Op("or", (P, notP))
    bar = "-" * 64
    print(bar)
    print("다치 의미론 데모 - 유리학의 |= 측면 (진리치 I/B, 무모순율의 국소성)")
    print(bar)
    print("[배중률]   P or not P 가 항진식인가?")
    print(f"           K3: {is_tautology(lem, K3)}     고전: {is_tautology(lem, BOOLEAN)}")
    print(f"           -> K3에서 P=I 이면 (P or not P) = "
          f"{evaluate(lem, {'P': 'I'}, K3)}  (designated 아님)")
    print()
    print("[거짓말쟁이] L = not L 의 고정점 (not v = v):")
    print(f"           K3: {negation_fixpoints(K3)}   -> 진리치 I (정의되지 않음)")
    print(f"           LP: {negation_fixpoints(LP)}   -> 진리치 B (참이면서 거짓)")
    print()
    ok_lp, cx = entails([P, notP], Q, LP)
    ok_cl, _ = entails([P, notP], Q, BOOLEAN)
    print("[폭발원리]  {P, not P} |= Q 가 성립하는가?")
    print(f"           LP:   {ok_lp}   (반례 평가: {cx})")
    print(f"           고전: {ok_cl}")
    print("           -> LP에서는 모순을 허용해도 임의 명제로 폭발하지 않는다 (초일관).")
    print(bar)
