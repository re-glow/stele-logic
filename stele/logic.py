from dataclasses import dataclass
from .ast import Var, Op


@dataclass(frozen=True)
class RuleSchema:
    name: str
    metavars: frozenset
    premises: tuple
    conclusion: object
    hyp_premises: tuple = ()  # ((assume_pat, concl_pat), ...) for discharge rules


def _not(a):
    return Op("not", (a,))


def _and(a, b):
    return Op("and", (a, b))


def _imp(a, b):
    return Op("imp", (a, b))


A = Var("A")
B = Var("B")
C = Var("C")
BOT = Op("bot", ())

COPY           = RuleSchema("copy",           frozenset({"A"}),         (A,),              A)
MP             = RuleSchema("mp",             frozenset({"A", "B"}),    (_imp(A, B), A),   B)
AND_INTRO      = RuleSchema("and_intro",      frozenset({"A", "B"}),    (A, B),            _and(A, B))
AND_ELIM_L     = RuleSchema("and_elim_left",  frozenset({"A", "B"}),    (_and(A, B),),     A)
AND_ELIM_R     = RuleSchema("and_elim_right", frozenset({"A", "B"}),    (_and(A, B),),     B)
DNE            = RuleSchema("dne",            frozenset({"A"}),         (_not(_not(A)),),  A)
LEM            = RuleSchema("lem",            frozenset({"A"}),         (),                Op("or", (A, _not(A))))
PBC            = RuleSchema("pbc",            frozenset({"A"}),         (),                A,
                             ((_not(A), BOT),))
NEG_ELIM       = RuleSchema("neg_elim",       frozenset({"A"}),         (A, _not(A)),      BOT)
EX_FALSO       = RuleSchema("ex_falso",       frozenset({"A"}),         (BOT,),            A)
OR_INTRO_LEFT  = RuleSchema("or_intro_left",  frozenset({"A", "B"}),    (A,),              Op("or", (A, B)))
OR_INTRO_RIGHT = RuleSchema("or_intro_right", frozenset({"A", "B"}),    (B,),              Op("or", (A, B)))
IMP_INTRO      = RuleSchema("imp_intro",      frozenset({"A", "B"}),         (),                   _imp(A, B),
                             ((A, B),))
NEG_INTRO      = RuleSchema("neg_intro",      frozenset({"A"}),               (),                   _not(A),
                             ((A, BOT),))
OR_ELIM        = RuleSchema("or_elim",        frozenset({"A", "B", "C"}),     (Op("or", (A, B)),),  C,
                             ((A, C), (B, C)))

_SHARED = {r.name: r for r in (
    COPY, MP, AND_INTRO, AND_ELIM_L, AND_ELIM_R,
    NEG_ELIM, EX_FALSO, OR_INTRO_LEFT, OR_INTRO_RIGHT,
    IMP_INTRO, NEG_INTRO, OR_ELIM,
)}


class Logic:
    def __init__(self, name, rules, semantics="proof"):
        self.name = name
        self.rules = rules
        self.semantics = semantics


INTUITIONISTIC = Logic("intuitionistic_prop", dict(_SHARED))
CLASSICAL = Logic("classical_prop", {**_SHARED, "dne": DNE, "lem": LEM, "pbc": PBC})

LOGICS = {l.name: l for l in (INTUITIONISTIC, CLASSICAL)}


def get_logic(name):
    if name not in LOGICS:
        from .errors import SteleError
        raise SteleError(
            f"unknown logic '{name}'. available: {', '.join(sorted(LOGICS))}")
    return LOGICS[name]
