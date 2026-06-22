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

### 미래 작업

향후 Stele-Light 증명 스크립트를 증명항으로 정교화(elaboration)하는 것은 이 v1의 범위 밖이다. 이 경우 각 `have ... by rule ...` 단계를 대응 증명항 생성자로 변환하는 정교화기가 필요하다.

---

## 8. 제외 범위 (재확인)

| 항목 | 이유 |
|------|------|
| 고전 증명항 (dne, lem, pbc) | 제어 연산자 또는 이중부정 번역이 필요; 별도 설계 예정 |
| K3 / LP 다치 증명항 | K3·LP는 의미론 모듈; 증명항 계산법이 아님 |
| 증명 탐색 / 정규화 | 검증기 ≠ 증명기; Stele의 핵심 정체성 밖 |
| 증명항 표면 언어 (파서) | 미구현 — 항은 Python에서 직접 조립 |
| 한정 기호, 의존 타입 | 명제논리 단편 밖 |
