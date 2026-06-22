# Proof-Term Core — Stele v1

이 문서는 `stele.core` 패키지에 구현된 직관주의 명제논리 증명항 계산법(proof-term calculus)을 설명한다.

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

이 패키지는 이 대응을 직관주의 명제논리 단편에 대해 구현한다.

---

## 2. 지원 단편

**직관주의 명제논리(intuitionistic propositional logic)**만 지원한다.

지원 연결사:
- 함의 `->` (implication)
- 논리곱 `and` (conjunction)
- 논리합 `or` (disjunction)
- 거짓 `false` = ⊥ (bottom)
- 부정 `not A` = `A -> false` (abbreviation)

**제외 범위 (v1):**
- 고전 원리: `dne`, `lem`, `pbc`, 이중부정 제거
- 제어 연산자 (callcc 등)
- K3 / LP 다치 의미론 증명항
- 한정 기호(quantifiers), 의존 타입
- 증명항 표면 언어(파서)
- 정규화(normalization), 증명 탐색(proof search)

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

### `term-check` CLI

```bash
# 증명항이 타입 A -> A를 갖는지 검사
python -m stele.cli term-check --term "fun x: A => x" --type "A -> A"

# 증명항의 타입을 추론
python -m stele.cli term-check --term "fun x: A => x" --infer
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

## 9. 제외 범위 (재확인)

| 항목 | 이유 |
|------|------|
| 고전 증명항 (dne, lem, pbc) | 제어 연산자 또는 이중부정 번역이 필요; 별도 설계 예정 |
| K3 / LP 다치 증명항 | K3·LP는 의미론 모듈; 증명항 계산법이 아님 |
| 증명 탐색 | 검증기 ≠ 증명기; Stele의 핵심 정체성 밖 |
| η-환원 | v1에서 미구현; 미래 작업 후보 |
| 증명항 표면 언어 → 스크립트 역방향 | v1에서 미구현; 미래 작업 |
| 한정 기호, 의존 타입 | 명제논리 단편 밖 |
