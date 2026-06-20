from dataclasses import dataclass


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Op:
    sym: str
    args: tuple


_PREC = {"imp": 1, "or": 2, "and": 3, "not": 4}
_BIN = {"and": "and", "or": "or", "imp": "->"}


def pretty(f):
    return _p(f, 0)


def _p(f, parent):
    if isinstance(f, Var):
        return f.name
    if isinstance(f, Op):
        s = f.sym
        if s == "bot":
            return "false"
        elif s == "not":
            prec = _PREC["not"]
            out = "not " + _p(f.args[0], prec)
        elif s in _BIN:
            prec = _PREC[s]
            op = _BIN[s]
            if s == "imp":
                out = _p(f.args[0], prec + 1) + " " + op + " " + _p(f.args[1], prec)
            else:
                out = _p(f.args[0], prec) + " " + op + " " + _p(f.args[1], prec + 1)
        else:
            return s + "(" + ", ".join(_p(a, 0) for a in f.args) + ")"
        return "(" + out + ")" if prec < parent else out
    return str(f)
