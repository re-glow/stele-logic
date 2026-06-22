"""Proof term constructors for the intuitionistic propositional fragment.

Each constructor corresponds to a natural-deduction rule under the
Curry–Howard correspondence.  Formula/type objects are taken from
stele.ast (Var for proposition variables, Op for connectives).

Note on naming: proof-term variables are called TVar (not Var) to
avoid a name collision with stele.ast.Var, which names proposition
variables in formulas.

Supported fragment: implication (->), conjunction (and), disjunction
(or), bottom (false).  Negation is the abbreviation not A = A -> false,
handled transparently by the type checker.

Out of scope in v1: classical proof terms (dne, lem, pbc), control
operators, quantifiers, dependent types, many-valued proof terms.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TVar:
    """Proof variable: a named hypothesis in the typing context.

    Typing:  Γ, x:A ⊢ TVar(x) : A
    """
    name: str


@dataclass(frozen=True)
class Lam:
    """Lambda abstraction: proof of an implication.

    Typing:  if Γ, x:A ⊢ body : B  then  Γ ⊢ Lam(x, A, body) : A -> B

    The parameter annotation var_type (A) is required for type synthesis.
    """
    var: str
    var_type: object   # Formula (stele.ast.Var | stele.ast.Op)
    body: object       # Term


@dataclass(frozen=True)
class App:
    """Function application: modus ponens.

    Typing:  if Γ ⊢ fn : A -> B  and  Γ ⊢ arg : A  then  Γ ⊢ App(fn, arg) : B
    """
    fn: object    # Term
    arg: object   # Term


@dataclass(frozen=True)
class Pair:
    """Conjunction introduction (∧I).

    Typing:  if Γ ⊢ left : A  and  Γ ⊢ right : B
             then  Γ ⊢ Pair(left, right) : A and B
    """
    left: object   # Term
    right: object  # Term


@dataclass(frozen=True)
class Fst:
    """Conjunction elimination — left component (∧E₁).

    Typing:  if Γ ⊢ pair : A and B  then  Γ ⊢ Fst(pair) : A
    """
    pair: object  # Term


@dataclass(frozen=True)
class Snd:
    """Conjunction elimination — right component (∧E₂).

    Typing:  if Γ ⊢ pair : A and B  then  Γ ⊢ Snd(pair) : B
    """
    pair: object  # Term


@dataclass(frozen=True)
class Inl:
    """Disjunction introduction — left injection (∨I₁).

    Typing:  if Γ ⊢ value : A  then  Γ ⊢ Inl(value, B) : A or B

    right_type (B) is an explicit annotation required for type synthesis;
    without it, the full disjunction type A or B cannot be determined.
    """
    value: object      # Term
    right_type: object # Formula — type annotation for the right disjunct


@dataclass(frozen=True)
class Inr:
    """Disjunction introduction — right injection (∨I₂).

    Typing:  if Γ ⊢ value : B  then  Γ ⊢ Inr(value, A) : A or B

    left_type (A) is an explicit annotation required for type synthesis.
    """
    value: object     # Term
    left_type: object # Formula — type annotation for the left disjunct


@dataclass(frozen=True)
class Case:
    """Disjunction elimination — case analysis (∨E).

    Typing:  if Γ ⊢ scrutinee : A or B
                and  Γ, left_var:A  ⊢ left_body  : C
                and  Γ, right_var:B ⊢ right_body : C
             then  Γ ⊢ Case(scrutinee, left_var, left_body,
                              right_var, right_body) : C

    Both branch result types must agree (checked by infer; or a common
    expected type is checked against both branches in check mode).
    """
    scrutinee: object   # Term
    left_var: str
    left_body: object   # Term
    right_var: str
    right_body: object  # Term


@dataclass(frozen=True)
class Abort:
    """Bottom elimination — ex falso quodlibet (⊥E).

    Typing:  if Γ ⊢ false_term : false
             then  Γ ⊢ Abort(false_term, C) : C

    target_type (C) is an explicit annotation required for type synthesis.
    """
    false_term: object   # Term — must have type false (Op("bot", ()))
    target_type: object  # Formula — the conclusion type
