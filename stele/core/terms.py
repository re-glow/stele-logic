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


# ---------------------------------------------------------------------------
# First-order extension (universal and existential quantification)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ForallIntro:
    """Universal introduction (∀I): generalise over an object variable.

    Typing:  if  Γ ⊢ body : A   and  obj_var ∉ fv(Γ)
             then  Γ ⊢ ForallIntro(obj_var, body) : forall obj_var. A

    obj_var must be fresh for the typing context Γ (the freshness side
    condition ensures the generalisation is valid).

    Under Curry–Howard: corresponds to the dependent function type Πx:*.A(x)
    restricted to the case where A is a formula not the type of object terms.
    """
    obj_var: str   # object variable name (must be fresh for Γ at typing time)
    body: object   # Term


@dataclass(frozen=True)
class ForallElim:
    """Universal elimination (∀E): instantiate a universally quantified formula.

    Typing:  if  Γ ⊢ fn : forall x. A  and  obj_term is an object term
             then  Γ ⊢ ForallElim(fn, obj_term) : A[obj_term / x]

    obj_term may be an ObjVar (free or bound) or ObjConst.

    β-rule:  ForallElim(ForallIntro(x, body), a)  →  subst_obj_in_term(body, x, a)
    """
    fn: object       # Term (must have type forall x. A)
    obj_term: object # ObjTerm (ObjVar | ObjConst from stele.core.fol)


@dataclass(frozen=True)
class ExistsIntro:
    """Existential introduction (∃I): pack a witness into an existential type.

    Typing:  if  exists_type = Exists(x, A)
                 and  Γ ⊢ proof : A[witness / x]
             then  Γ ⊢ ExistsIntro(witness, proof, exists_type) : Exists(x, A)

    An explicit exists_type annotation is required so the quantified variable
    x and formula A are known without unification.

    β-rule (as part of ExistsElim): see ExistsElim.
    """
    witness: object     # ObjTerm — the concrete object term as evidence
    proof: object       # Term    — proof that the witness satisfies A
    exists_type: object # Exists(x, A) — required type annotation


@dataclass(frozen=True)
class ExistsElim:
    """Existential elimination (∃E): unpack an existential.

    Typing:  if  Γ ⊢ scrutinee : Exists(x, A)
                 and  Γ, h : A[obj_var/x] ⊢ body : C
                 and  obj_var ∉ fv(C)         (freshness)
             then  Γ ⊢ ExistsElim(scrutinee, obj_var, proof_var, body) : C

    obj_var  — object variable name representing the anonymous witness (x);
               it is free in body but must not appear in the result type C.
    proof_var — proof variable name for the hypothesis h : A[obj_var/x];
                bound in body.

    β-rule:
      ExistsElim(ExistsIntro(a, p, _), x, h, body)
        →  subst_obj_in_term(substitute(body, h, p), x, a)
    """
    scrutinee: object  # Term — must have type Exists(x, A)
    obj_var: str       # object variable name for the anonymous witness
    proof_var: str     # proof variable name for the witness property
    body: object       # Term
