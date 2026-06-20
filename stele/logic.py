from dataclasses import dataclass
from .ast import Var, Op


@dataclass(frozen=True)
class RuleSchema:
    name: str
    metavars: frozenset
    premises: tuple
    conclusion: object


def _not(a):
    return Op("not", (a,))


def _and(a, b):
    return Op("and", (a, b))


def _imp(a, b):
    return Op("imp", (a, b))


A = Var("A")
B = Var("B")
BOT = Op("bot", ())

COPY           = RuleSchema("copy",           frozenset({"A"}),         (A,),              A)
MP             = RuleSchema("mp",             frozenset({"A", "B"}),    (_imp(A, B), A),   B)
AND_INTRO      = RuleSchema("and_intro",      frozenset({"A", "B"}),    (A, B),            _and(A, B))
AND_ELIM_L     = RuleSchema("and_elim_left",  frozenset({"A", "B"}),    (_and(A, B),),     A)
AND_ELIM_R     = RuleSchema("and_elim_right", frozenset({"A", "B"}),    (_and(A, B),),     B)
DNE            = RuleSchema("dne",            frozenset({"A"}),         (_not(_not(A)),),  A)
NEG_ELIM       = RuleSchema("neg_elim",       frozenset({"A"}),         (A, _not(A)),      BOT)
EX_FALSO       = RuleSchema("ex_falso",       frozenset({"A"}),         (BOT,),            A)
OR_INTRO_LEFT  = RuleSchema("or_intro_left",  frozenset({"A", "B"}),    (A,),              Op("or", (A, B)))
OR_INTRO_RIGHT = RuleSchema("or_intro_right", frozenset({"A", "B"}),    (B,),              Op("or", (A, B)))

# imp_intro (->I) is a hypothesis-discharge rule handled specially in the
# kernel; it is available in every natural-deduction logic defined here.
_SHARED = {r.name: r for r in (
    COPY, MP, AND_INTRO, AND_ELIM_L, AND_ELIM_R,
    NEG_ELIM, EX_FALSO, OR_INTRO_LEFT, OR_INTRO_RIGHT,
)}


class Logic:
    def __init__(self, name, rules, semantics="proof"):
        self.name = name
        self.rules = rules
        self.semantics = semantics


INTUITIONISTIC = Logic("intuitionistic_prop", dict(_SHARED))
CLASSICAL = Logic("classical_prop", {**_SHARED, "dne": DNE})

LOGICS = {l.name: l for l in (INTUITIONISTIC, CLASSICAL)}


def get_logic(name):
    if name not in LOGICS:
        from .errors import SteleError
        raise SteleError(
            f"unknown logic '{name}'. available: {', '.join(sorted(LOGICS))}")
    return LOGICS[name]
