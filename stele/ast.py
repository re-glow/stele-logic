from dataclasses import dataclass


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Op:
    sym: str
    args: tuple


@dataclass(frozen=True)
class Pred:
    """First-order atomic predicate: P(t1, …, tn).

    Propositional variables remain Var.  Pred is used only when explicit
    object-term arguments are present (args is non-empty in normal use).

    args contains ObjVar / ObjConst instances from stele.core.fol.
    """
    name: str
    args: tuple  # tuple of ObjTerm


@dataclass(frozen=True)
class Forall:
    """Universal quantification: forall x. A  (first-order)."""
    var: str      # bound object variable name
    body: object  # Formula


@dataclass(frozen=True)
class Exists:
    """Existential quantification: exists x. A  (first-order)."""
    var: str      # bound object variable name
    body: object  # Formula


_PREC = {"imp": 1, "or": 2, "and": 3, "not": 4}
_BIN = {"and": "and", "or": "or", "imp": "->"}


def pretty(f):
    return _p(f, 0)


def _p(f, parent):
    if isinstance(f, Var):
        return f.name
    if isinstance(f, Pred):
        return f.name + "(" + ", ".join(str(a) for a in f.args) + ")"
    if isinstance(f, Forall):
        inner = "forall " + f.var + ". " + _p(f.body, 0)
        return "(" + inner + ")" if parent > 0 else inner
    if isinstance(f, Exists):
        inner = "exists " + f.var + ". " + _p(f.body, 0)
        return "(" + inner + ")" if parent > 0 else inner
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
