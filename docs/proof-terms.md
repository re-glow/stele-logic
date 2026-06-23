# Proof-Term Core — Stele v2

이 문서는 `stele.core` 패키지에 구현된 직관주의 명제논리 + 1차 논리 단편의 증명항 계산법(proof-term calculus)을 설명한다.

---

## 1. Curry–Howard 대응

Curry–Howard 대응은 명제와 타입, 증명과 항(term)을 동일시한다.

| 논리 | 타입이론 |
|------|----------|
| 명제 A | 타입 A |
| A의 증명 | A 타입의 항 |
| A → B | 함수 타입 A → B |
| A ∧ B | 곱 타입 A × B |
| A ∨ B | 합 타입 A + B |
| ⊥ (거짓) | 공 타입 (Empty) |
| ¬A | 타입 A → ⊥ |
| ∀x. A(x) | 의존 함수 타입 (Π x. A(x) 근사) |
| ∃x. A(x) | 의존 쌍 타입 (Σ x. A(x) 근사) |

이 패키지는 이 대응을 직관주의 명제논리 + 1차 논리 단편에 대해 구현한다.

---

## 2. 지원 단편

**직관주의 명제논리(IPL) + 직관주의 1차 논리 단편(IQL)**을 지원한다.

지원 연결사:
- 함의 `->` (implication)
- 논리곱 `and` (conjunction)
- 논리합 `or` (disjunction)
- 거짓 `false` = ⊥ (bottom)
- 부정 `not A` = `A -> false` (abbreviation)
- 전칭기호 `forall x. A` (universal quantifier)
- 존재기호 `exists x. A` (existential quantifier)
- 술어 `P(x, y)` (predicate)

**제외 범위:**
- 고전 원리: `dne`, `lem`, `pbc`, 이중부정 제거
- 제어 연산자 (callcc 등)
- K3 / LP 다치 의미론 증명항
- 동치(`=`), 함수 기호(function terms)
- 의존 타입 (full CIC/CoC)
- 증명 탐색(proof search)

---

## 3. 증명항 생성자

모든 생성자는 frozen dataclass이다(`stele/core/terms.py`).

### 변수

```python
TVar(name: str)
```

컨텍스트 내 가정에 이름으로 접근한다. (`stele.ast.Var`와의 충돌을 피하기 위해 `TVar`로 명명.)

### 함의 도입 / 제거

```python
Lam(var: str, var_type: Formula, body: Term)   # →I : 람다 추상
App(fn: Term, arg: Term)                        # →E : 함수 적용 (modus ponens)
```

`var_type`은 타입 합성(synthesis)을 위한 필수 어노테이션이다.

### 논리곱 도입 / 제거

```python
Pair(left: Term, right: Term)   # ∧I
Fst(pair: Term)                  # ∧E₁ (왼쪽 사영)
Snd(pair: Term)                  # ∧E₂ (오른쪽 사영)
```

### 논리합 도입 / 제거

```python
Inl(value: Term, right_type: Formula)   # ∨I₁ (왼쪽 주입)
Inr(value: Term, left_type: Formula)    # ∨I₂ (오른쪽 주입)
Case(scrutinee: Term,
     left_var: str, left_body: Term,
     right_var: str, right_body: Term)  # ∨E (경우 분석)
```

`Inl`의 `right_type`과 `Inr`의 `left_type`은 전체 논리합 타입 합성을 위한 필수 어노테이션이다.

### 거짓 제거

```python
Abort(false_term: Term, target_type: Formula)   # ⊥E (ex falso)
```

`target_type`은 타입 합성을 위한 필수 어노테이션이다.

---

## 4. 타입 검사 규칙

아래 표기에서 `Γ`는 타입 컨텍스트, `⊢`는 타입 판단을 나타낸다.

### 변수

```
x : A ∈ Γ
──────────
Γ ⊢ TVar(x) : A
```

### 함의 도입

```
Γ, x:A ⊢ t : B
────────────────────────
Γ ⊢ Lam(x, A, t) : A → B
```

### 함의 제거 (Modus Ponens)

```
Γ ⊢ f : A → B    Γ ⊢ a : A
────────────────────────────
Γ ⊢ App(f, a) : B
```

### 논리곱 도입

```
Γ ⊢ l : A    Γ ⊢ r : B
────────────────────────
Γ ⊢ Pair(l, r) : A ∧ B
```

### 논리곱 제거

```
Γ ⊢ p : A ∧ B          Γ ⊢ p : A ∧ B
──────────────          ──────────────
Γ ⊢ Fst(p) : A          Γ ⊢ Snd(p) : B
```

### 논리합 도입

```
Γ ⊢ v : A                   Γ ⊢ v : B
──────────────────           ──────────────────
Γ ⊢ Inl(v, B) : A ∨ B       Γ ⊢ Inr(v, A) : A ∨ B
```

### 논리합 제거

```
Γ ⊢ e : A ∨ B    Γ, x:A ⊢ l : C    Γ, y:B ⊢ r : C
──────────────────────────────────────────────────────
Γ ⊢ Case(e, x, l, y, r) : C
```

### 거짓 제거

```
Γ ⊢ t : ⊥
──────────────────────
Γ ⊢ Abort(t, C) : C
```

### 부정 (약어)

```
not A  =  A → ⊥
```

타입 검사기는 `Op("not", (A,))`를 `Op("imp", (A, Op("bot", ())))`으로 정규화하여 처리한다(`normalize_neg`). 사용자는 두 표현을 혼용할 수 있다.

---

## 5. 양방향 타입 검사 (Bidirectional Typing)

`stele/core/typing.py`는 두 함수를 제공한다.

### `infer(Γ, t) → A` — 합성(synthesis) 모드

항 `t`로부터 타입 `A`를 합성한다. 모든 생성자는 타입 합성에 충분한 어노테이션을 보유하므로, `infer`는 항상 타입을 돌려주거나 `TypingError`를 발생시킨다.

### `check(Γ, t, A) → None` — 검사(checking) 모드

`t`가 타입 `A`를 가지는지 검사한다. 도입 규칙(Lam, Pair, Inl, Inr, Case)에 대해서는 기대 타입을 역방향으로 분해하는 검사 규칙을 우선 적용한다. 나머지는 `infer` 후 등치 비교로 대체된다.

### 컨텍스트

```python
empty_ctx()                   # {} 컨텍스트
extend(ctx, var, ty)          # 비파괴적 확장; 같은 이름 재바인딩 시 새 바인딩이 우선
```

### 오류

타입 오류는 `TypingError(msg)`로 발생한다. 정형화된 구조체 없이 오류 메시지에 관련 타입·항 정보를 포함한다(v1 기준).

---

## 6. Python API 예시

```python
from stele.ast import Var as FVar, Op
from stele.core import (
    TVar, Lam, App, Pair, Fst, Snd,
    Inl, Inr, Case, Abort,
    infer, check, TypingError,
    empty_ctx, extend, mk_not,
)

A = FVar("A")
B = FVar("B")

# identity: λx:A. x : A -> A
identity = Lam("x", A, TVar("x"))
print(infer(empty_ctx(), identity))  # Op("imp", (A, A))

# K combinator: λx:A. λy:B. x : A -> B -> A
K = Lam("x", A, Lam("y", B, TVar("x")))
assert infer(empty_ctx(), K) == Op("imp", (A, Op("imp", (B, A))))

# negation: not A = A -> false
not_a = mk_not(A)           # Op("imp", (A, Op("bot", ())))
lam_na = Lam("x", not_a, TVar("x"))
check(empty_ctx(), lam_na, not_a)   # ok — no exception

# bottom elimination
false_val = Op("bot", ())
ctx = extend(empty_ctx(), "absurd", false_val)
t = Abort(TVar("absurd"), B)
assert infer(ctx, t) == B

# ill-typed: unbound variable
try:
    infer(empty_ctx(), TVar("x"))
except TypingError as e:
    print(e)  # unbound variable 'x'
```

---

## 7. 기존 Stele 증명 스크립트와의 관계

### 공존

증명항 코어(`stele.core`)와 규칙 스키마 커널(`stele.kernel`)은 **독립적인 두 레이어**다.

| 레이어 | 모듈 | 역할 |
|--------|------|------|
| 규칙 스키마 커널 | `stele.kernel`, `stele.logic` | Stele-Light 증명 스크립트 검증 |
| 증명항 코어 | `stele.core` | Curry–Howard 증명항 타입 검사 |

`stele.core`는 `stele.kernel`을 임포트하지 않고, `stele.kernel`은 `stele.core`를 임포트하지 않는다. 이 불변식은 테스트 스위트(`test_proof_terms.py::TestKernelInvariance`)가 정적으로 검사한다.

### v1에서 대체하지 않는 것

기존 증명 스크립트 검사기(`check_theorem`)는 그대로 유지된다. 증명항 코어는 **추가** 레이어이며 기존 동작을 바꾸지 않는다.

---

## 7a. 스크립트 정교화(elaboration) — v2

> **Stele now has a proof-term core and an elaboration path from supported proof scripts into typed proof terms.**

`stele.elaborate` 모듈은 직관주의 단편의 Stele-Light 증명 스크립트를 증명항으로 정교화한다.

### 지원 규칙 → 증명항 생성자 대응

| 증명 규칙 | 증명항 생성자 |
|-----------|--------------|
| `assume` / `suppose` | `TVar` |
| `copy` | 변수 재사용 |
| `mp` | `App` |
| `imp_intro` | `Lam` |
| `and_intro` | `Pair` |
| `and_elim_left` | `Fst` |
| `and_elim_right` | `Snd` |
| `or_intro_left` | `Inl` |
| `or_intro_right` | `Inr` |
| `or_elim` | `Case` |
| `ex_falso` | `Abort` |
| `neg_intro` | `Lam` (not A = A → false) |
| `neg_elim` | `App` (not A = A → false) |

### 미지원 규칙 (고전)

`dne`, `lem`, `pbc`는 `ElaborationError`를 발생시킨다. 고전 증명항은 별도의 제어 연산자/이중부정 번역 설계가 필요하다.

### 상호 검증 (`crosscheck_theorem`)

```python
from stele.elaborate import crosscheck_theorem

result = crosscheck_theorem(thm, logic_name="intuitionistic_prop")
# result.script_ok      — 커널이 스크립트를 허가했는가?
# result.elaboration_ok — 스크립트가 증명항으로 정교화되었는가?
# result.typecheck_ok   — 증명항이 결론 공식에 대해 타입 검사를 통과했는가?
# result.ok             — 세 조건 모두 참인가?
```

`crosscheck_theorem`은 기존 커널 검사를 대체하지 않는다. 두 방향의 일관성 확인이다:
1. 규칙 스키마 커널이 스크립트를 허가
2. 정교화된 증명항이 결론에 대해 타입 검사를 통과

---

## 7b. 증명항 표면 문법 및 CLI

### 표면 문법 요약 (`stele.core.term_parser`)

```
fun x: A => body           람다 추상 (또는 λ x: A => body)
f(a)                        함수 적용 (f에 a를 적용)
f(a)(b)                     연쇄 적용 (좌결합)
pair(a, b)                  논리곱 도입
fst(t)                      논리곱 제거 (왼쪽)
snd(t)                      논리곱 제거 (오른쪽)
inl(t, B)                   논리합 도입 (왼쪽); B는 오른쪽 타입 어노테이션
inr(t, A)                   논리합 도입 (오른쪽); A는 왼쪽 타입 어노테이션
case e of inl x => u | inr y => v   논리합 제거
abort(t, C)                 거짓 제거; C는 목표 타입 어노테이션
```

타입 어노테이션(`:` 뒤 또는 `inl`/`inr`/`abort`의 두 번째 인자)에는 기존 공식 문법(`->`, `and`, `or`, `not`, `false`, 괄호)이 그대로 적용된다.

**1차 논리 표면 문법 확장** (Experimental — Section 10):

```
forall_intro x => body          전칭 도입; x는 객체 변수 이름
forall_elim(f, a)               전칭 제거; f는 증명항, a는 객체 변수 이름
exists_intro(a, h, exists x.A)  존재 도입; a=증인, h=증명, 세 번째 인자는 목표 타입
exists_elim(e, x, h, body)      존재 제거; e=증인증명, x=객체변수, h=증명변수, body=본문
```

공식 어노테이션에서 한정사(`forall x. A`, `exists x. A`)와 술어(`P(x)`, `R(x,y)`)를 사용할 수 있다.
`->` 오른편에 한정사를 쓸 때는 괄호 없이도 허용된다: `not A -> forall x. P(x)`.

### `term-check` CLI

```bash
# 증명항이 타입 A -> A를 갖는지 검사
python -m stele.cli term-check --term "fun x: A => x" --type "A -> A"

# 증명항의 타입을 추론
python -m stele.cli term-check --term "fun x: A => x" --infer

# 컨텍스트와 함께 사용 (FOL 예시)
python -m stele.cli term-check \
    --context "f: forall x. P(x)" \
    --term "forall_elim(f, a)" --infer

python -m stele.cli term-check \
    --context "f: forall x. P(x) -> Q(x); h: P(a)" \
    --term "forall_elim(f, a)(h)" --infer
```

### `elaborate` CLI

```bash
# 증명 스크립트를 정교화하고 결과를 보고
python -m stele.cli elaborate examples/elaborate_identity.stele
python -m stele.cli elaborate examples/elaborate_disjunction.stele
python -m stele.cli elaborate examples/dne.stele --logic classical_prop
```

출력 예시:
```
elaborate  [elaborate_identity | logic: intuitionistic_prop]
  script check:  OK
  elaboration:   OK
  term typecheck:OK
  proof term:    fun h1: P => h1
```

---

## 8. β-환원과 정규화 — v3

`stele/core/reduce.py`는 증명항의 β-환원과 정규화를 제공한다.

### 환원 규칙

| 이름 | 패턴 | 환원 결과 |
|------|------|----------|
| β_imp | `App(Lam(x, A, body), arg)` | `body[arg/x]` |
| β_fst | `Fst(Pair(a, b))` | `a` |
| β_snd | `Snd(Pair(a, b))` | `b` |
| β_case_l | `Case(Inl(a, _), x, lb, y, rb)` | `lb[a/x]` |
| β_case_r | `Case(Inr(b, _), x, lb, y, rb)` | `rb[b/y]` |

각 규칙은 순차 계산에서 **절단 제거(cut elimination)**에 대응한다. η-환원은 v1에서 미구현이다.

### 포착 회피 치환 (capture-avoiding substitution)

`substitute(term, x, replacement)`는 `term[replacement/x]`를 계산한다.

- **그림자(shadowing):** 바인더가 `x`를 재바인드하면 그 이하에 치환하지 않는다.
- **포착 회피:** 바인더의 바운드 이름이 `replacement`의 자유 변수에 속하면 알파 재명명(alpha-rename)한다. 새 이름은 `NAME_0`, `NAME_1`, … 형식으로 생성한다.

### 전략: 최좌-최외 (leftmost-outermost / normal order)

`step(term)` 함수는 한 번의 β-환원 단계를 수행한다.

- 복합 노드에서 가장 바깥 환원 쌍(redex)을 먼저 시도한다.
- 헤드 환원 쌍이 없으면 왼쪽→오른쪽 순으로 부분항을 재귀 탐색한다.
- 환원 쌍이 없으면 `None`을 반환한다(정규형).

이 전략은 결정적이며, 단순 타입 직관주의 단편에서 유일한 β-정규형에 도달한다.

### API

```python
from stele.core.reduce import free_vars, substitute, step, normalize, is_normal, ReductionError

# 자유 변수
free_vars(Lam("x", A, App(TVar("x"), TVar("y"))))  # {"y"}

# 한 단계 환원
step(App(Lam("x", A, TVar("x")), TVar("a")))  # TVar("a")
step(Fst(Pair(TVar("a"), TVar("b"))))          # TVar("a")
step(TVar("x"))                                # None  (이미 정규형)

# 정규화
normalize(App(Lam("x", A, TVar("x")), TVar("a")))          # TVar("a")
normalize(Fst(Pair(Fst(Pair(TVar("a"), TVar("b"))), TVar("c"))))  # TVar("a")

# 정규형 확인
is_normal(TVar("x"))                                        # True
is_normal(App(Lam("x", A, TVar("x")), TVar("a")))          # False

# 연료 소진 시 예외
try:
    normalize(big_term, fuel=10)
except ReductionError:
    ...
```

`stele.core.__init__`도 이 심볼들을 재내보낸다.

### `term-normalize` CLI

```bash
# 증명항을 β-정규형으로 환원
python -m stele.cli term-normalize --term "fst(pair(x, y))"
# OK x

python -m stele.cli term-normalize --term "fun x: A => fst(pair(x, x))"
# OK fun x: A => x
```

### 메타이론 관계 (주의사항)

| 성질 | 상태 |
|------|------|
| 단순 타입 직관주의 단편의 강한 정규화 | 표준 메타정리로 알려짐 (기계 검증 안 됨) |
| 합류성(confluence) | 교회-로서 정리로 알려짐; 회귀 테스트(`test_reduction.py::TestConfluence`)는 특정 사례만 확인 |
| 주체 환원(subject reduction) | 회귀 테스트(`test_reduction.py::TestSubjectReduction`)가 각 β-규칙을 확인; 기계 증명 아님 |
| 일관성(consistency) | 연기 테스트(`TestConsistency`)가 빈 컨텍스트에서 도입 규칙만으로 `false`를 증명할 수 없음을 확인; 기계 증명 아님 |

연기 테스트는 구현 버그를 포착하는 회귀 테스트이며, 형식 증명이 아니다.

---

## 9. 바인더, α-동치, de Bruijn 치환

### 9.1 이름 있는 바인더와 α-동치

`Lam("x", A, TVar("x"))`와 `Lam("y", A, TVar("y"))`는 구조적으로 다르지만
**α-동치(α-equivalent)**이다 — 바인더 이름만 다르고 구조가 같다.

`stele.core.debruijn` 모듈은 이를 결정하는 내부 표현을 제공한다:

```python
from stele.core.debruijn import alpha_equiv
from stele.core.terms import Lam, TVar
from stele.ast import Var

A = Var("A")
alpha_equiv(Lam("x", A, TVar("x")), Lam("y", A, TVar("y")))   # True
alpha_equiv(Lam("x", A, TVar("x")), Lam("x", A, TVar("y")))   # False — body differs
```

### 9.2 de Bruijn 표현

내부적으로 바인더는 **de Bruijn 인덱스**로 표현된다.
인덱스 `k`는 k번째 둘러싼 바인더를 지칭한다(0 = 가장 안쪽).

```python
from stele.core.debruijn import to_debruijn, DBLam, DBBound

# 두 항 모두 DBLam(A, DBBound(0))으로 변환됨
to_debruijn(Lam("x", A, TVar("x")))   # DBLam(A, DBBound(0))
to_debruijn(Lam("y", A, TVar("y")))   # DBLam(A, DBBound(0))
```

### 9.3 이동(Shift)과 치환(Substitution)

de Bruijn 치환은 포착을 **구조적으로 회피**한다:
바인더를 통과할 때마다 대체항을 1 이동시킨다.

```python
from stele.core.debruijn import shift, subst, subst_top, DBBound, DBFree

# shift: 인덱스 조정 (항을 새 바인더 아래로 옮길 때)
shift(DBBound(0), 1, 0)   # → DBBound(1)  (인덱스 증가)
shift(DBBound(0), 1, 1)   # → DBBound(0)  (cutoff 아래: 내부 바인더; 변경 없음)

# subst: β-환원 단계
# (DBLam(A, body)) arg  →  subst_top(arg, body)  =  subst(body, 0, arg)
subst(DBBound(0), 0, DBFree("a"))       # → DBFree("a")  (identity)
subst_top(DBFree("a"), DBBound(0))      # → DBFree("a")  (alias)
```

### 9.4 사용자 대면 구문에 미치는 영향 없음

de Bruijn 표현은 순수 내부 구현이다.
사용자는 항상 이름 있는 구문으로 작성하고, 파서와 타입 검사기는 기존대로 동작한다.
`to_debruijn` / `from_debruijn` / `alpha_equiv`는 고급 사용자를 위한 공개 API이지만
일반 증명 검증 워크플로에서는 직접 호출할 필요가 없다.

### 9.5 1차 논리 바인더 (v2)

`forall`/`exists` 한정기호가 v2에서 추가되었다.
proof-term de Bruijn 층에서 **객체 바인더는 이름 유지** 방식으로 처리된다:
- `DBForallIntro(obj_var: str, body)` — obj_var는 이름 보존
- `DBExistsElim(scrutinee, obj_var: str, body)` — obj_var 이름 보존; proof_var만 DB 인덱스

`alpha_equiv`(증명항 수준)는 증명 변수 재명명에는 둔감하지만 객체 변수 재명명에는 민감하다.

공식 수준의 α-동치는 별도의 de Bruijn 공식 층으로 처리한다:

```python
from stele.core.fol import to_debruijn_formula, alpha_equiv_formula

alpha_equiv_formula(Forall("x", P("x")), Forall("y", P("y")))  # True
# 섀도잉 케이스도 올바르게 처리
alpha_equiv_formula(
    Forall("x", Forall("x", P("x"))),   # 안쪽 x
    Forall("y", Forall("z", P("y"))),   # 바깥쪽 y — 다른 구조
)  # False
```

`formula_alpha_equiv_fol(f1, f2)` 는 하위 호환성을 위해 유지되며 `alpha_equiv_formula`에 위임한다.

---

## 10. 1차 논리 단편 (v2)

`stele.core.fol`과 `stele.core.terms.{ForallIntro, ForallElim, ExistsIntro, ExistsElim}`이 구현하는 직관주의 1차 논리 단편. 전체 명세는 `docs/semantics.md` Section 8 참조.

### 객체 항

```python
from stele.core.fol import ObjVar, ObjConst

ObjVar("a")    # 객체 변수 (한정기호에 묶이거나 자유로움)
ObjConst("c")  # 객체 상수 (치환 불가)
```

### 1차 논리 증명항

```python
from stele.core.terms import ForallIntro, ForallElim, ExistsIntro, ExistsElim
from stele.core.fol import ObjVar
from stele.ast import Var, Pred, Forall, Exists

A = Var("A")
P = lambda x: Pred("P", (ObjVar(x),))

# ∀I: ∅ ⊢ forall_intro x => fun h: P(x) => h  :  forall x. P(x) -> P(x)
term = ForallIntro("x", Lam("h", P("x"), TVar("h")))

# ∀E: 위 항을 'a'에 대해 인스턴스화  →  P(a) -> P(a)
elim = ForallElim(term, ObjVar("a"))

# ∃I: h : P(a)  →  pack(a, h, exists x. P(x))  :  exists x. P(x)
intro = ExistsIntro(ObjVar("a"), TVar("h"), Exists("x", P("x")))

# ∃E: e : exists x. P(x)  →  result : C  (x ∉ fv(C))
unpack = ExistsElim(TVar("e"), "x", "h", body)
```

### 표면 문법 (term_parser)

```
forall_intro x => t             ForallIntro("x", t)
forall_elim(t, a)               ForallElim(t, ObjVar("a"))
exists_intro(a, p, exists x. A) ExistsIntro(ObjVar("a"), p, Exists("x", A))
exists_elim(e, x, h, body)      ExistsElim(e, "x", "h", body)
```

공식 어노테이션 (`:` 뒤 또는 `exists_intro` 세 번째 인자)에서 1차 논리 공식 사용 가능.
`->` 오른편에 한정사를 괄호 없이 쓸 수 있다:

```python
from stele.core.term_parser import parse_term
from stele.parser import parse_formula
from stele.core.typing import check, empty_ctx

# 전칭 분배  ∀x.(P→Q) → ∀x.P → ∀x.Q
term = parse_term(
    "fun f: forall x. P(x) -> Q(x) => "
    "fun g: forall x. P(x) => "
    "forall_intro x => forall_elim(f, x)(forall_elim(g, x))"
)
expected = parse_formula(
    "(forall x. P(x) -> Q(x)) -> (forall x. P(x)) -> forall x. Q(x)"
)
check(empty_ctx(), term, expected)  # raises TypingError if wrong

# 직관적 드 모르간  ¬(∃x.P(x)) → ∀x.¬P(x)
term_dm = parse_term(
    "fun h: not (exists x. P(x)) => "
    "forall_intro x => "
    "fun px: P(x) => h(exists_intro(x, px, exists y. P(y)))"
)
check(empty_ctx(), term_dm,
      parse_formula("not (exists x. P(x)) -> forall x. not P(x)"))
```

동작하는 예시는 `examples/fol/` 디렉터리 참조.

### FOL 헬퍼 API

```python
from stele.core.fol import (
    fol_free_obj_vars,      # formula → set[str]
    subst_obj,              # formula × name × ObjTerm → formula (포착 회피)
    alpha_equiv_formula,     # f1 × f2 → bool (de Bruijn 기반, 섀도잉 안전)
    formula_alpha_equiv_fol, # 하위 호환; alpha_equiv_formula에 위임
)
from stele.core.reduce import (
    obj_free_in_term,       # proof term → set[str]
    subst_obj_in_term,      # proof term × name × ObjTerm → proof term
)
```

---

## 11. 실험적 고전 증명항 브릿지 (Experimental)

**상태: 실험적** — 안정 API 아님. `stele/core/classical_experimental.py` 참조.

### 11.1 접근 방법: 이중부정 번역 (Gödel–Gentzen)

고전 명제 공식을 직관 명제 공식으로 변환한 뒤, 기존 직관 증명항 검사기로 검증한다.

고전 공식 φ를 직관 공식 φ^N으로 번역:

```
P^N         = ¬¬P
false^N     = false
(A ∧ B)^N   = A^N ∧ B^N
(A → B)^N   = A^N → B^N
(¬A)^N      = ¬(A^N)
(A ∨ B)^N   = ¬(¬A^N ∧ ¬B^N)
```

핵심 성질: CPC ⊢ φ  이면  IPC ⊢ φ^N  (Gödel–Gentzen 정리).

### 11.2 구현된 기능

- `negative_translate_formula(φ, mode="godel_gentzen"|"glivenko")` — 공식 수준 번역
- `check_negative_translation(term, φ, ctx)` — 수동 작성 증명항을 번역 공식에 대해 검사
- `is_negative_translation_supported(φ)` — 명제 공식 여부 확인
- `classical_principle_name(φ)` — LEM/DNE/Peirce 패턴 인식

### 11.3 예시: DNE 번역 검사

DNE = `¬¬P → P`는 고전적으로 타당하다.

번역: DNE^N = `¬¬(¬¬P) → ¬¬P`

이 공식은 직관적으로 증명 가능하다:

```python
from stele.core.classical_experimental import check_negative_translation
from stele.core.terms import Lam, App, TVar
from stele.ast import Var, Op

P = Var("P")
BOT = Op("bot", ())
nP = Op("imp", (P, BOT))                    # P → ⊥
nnP = Op("imp", (nP, BOT))                  # (P→⊥)→⊥
nnnP = Op("imp", (nnP, BOT))                # ((P→⊥)→⊥)→⊥
nnnnP = Op("imp", (nnnP, BOT))              # (((P→⊥)→⊥)→⊥)→⊥

term = Lam("h", nnnnP,
           Lam("k", nP,
               App(TVar("h"),
                   Lam("f", nnP,
                       App(TVar("f"), TVar("k"))))))

dne = Op("imp", (Op("not", (Op("not", (P,)),)), P))
check_negative_translation(term, dne)  # 성공: TypingError 없음
```

### 11.4 미구현 사항 (설계 노트)

**직접 고전 증명항 (λμ-계산법)**

고전 논리의 증명항을 직접 표현하려면 λμ-계산법(Parigot 1992)이나
제어 연산자(`callcc`, `throw`)를 포함하는 계산법이 필요하다:

- **연속 변수(continuation variables)**: μ-바인더가 현재 연속을 포착
- **명령 판단(command judgment)**: `c : #`  (계산이 값이 아닌 제어 흐름을 반환)
- **환원 규칙**: μ-환원 + 구조적 환원
- **CPS 번역과의 관계**: λμ는 CPS 번역의 직접 항 표현

Stele은 현재 이 경로를 구현하지 않는다. 이유:

1. 직관 증명항 코어를 고전 제어 연산자로 확장하면 합류성/정규화 성질이 달라진다.
2. 이중부정 번역이 대표적 고전 원리의 검증에 충분하다.
3. 향후 필요 시 `stele/core/control_experimental.py` 등 별도 모듈로 추가 예정.

| 항목 | 상태 |
|------|------|
| λμ-계산법 | 미구현 (미래 작업) |
| `callcc` / `throw` | 미구현 |
| 연속 타이핑 | 미구현 |
| 고전 정규화/합류성 주장 | 없음 |
| 자동 증명 번역 | 미구현 |
| 증명 탐색 | 미구현 |

---

## 12. 제외 범위 (재확인)

| 항목 | 이유 |
|------|------|
| 고전 증명항 (λμ/callcc) | 제어 연산자 필요; 이중부정 번역 브릿지만 실험적 구현 (§11) |
| K3 / LP 다치 증명항 | K3·LP는 의미론 모듈; 증명항 계산법이 아님 |
| 증명 탐색 | 검증기 ≠ 증명기; Stele의 핵심 정체성 밖 |
| η-환원 | 미구현; 미래 작업 후보 |
| 증명항 표면 언어 → 스크립트 역방향 | 미구현 |
| 동치(`=`), 함수 기호 | 1차 논리 확장; 미구현 |
| 의존 타입 | 명제논리 단편 밖 |
| 객체 바인더 de Bruijn (공식 수준) | 구현됨: `to_debruijn_formula`, `alpha_equiv_formula` |
| 객체 바인더 de Bruijn (proof-term 층) | `DBForallIntro.obj_var` 등 이름 유지; 미래 작업 |
