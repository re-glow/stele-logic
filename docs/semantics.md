# Stele — Formal Language Specification

이 문서는 Stele 시스템의 **형식 언어**(formal language)를 명세한다.
공식 문법·타입 규칙·환원 규칙을 참조 표준으로 기록하고, 구현과의 대응 지점을 명시한다.

관련 문서:
- 메타이론 주장과 테스트 현황: [`docs/metatheory.md`](metatheory.md)
- Curry–Howard 레이어 상세: [`docs/proof-terms.md`](proof-terms.md)
- 사용자 언어 가이드: [`GUIDE.md`](../GUIDE.md)

---

## 1. 시스템 개요

Stele는 **수학적 추론의 형식 검증 프레임워크**다.
세 개의 독립적인 레이어로 구성된다.

| 레이어 | 모듈 | 역할 |
|--------|------|------|
| 증명 스크립트 커널 | `stele.kernel`, `stele.logic` | Stele-Light 자연연역 증명 검증 |
| 증명항 코어 | `stele.core` | Curry–Howard 타입 검사 + β-환원 |
| 행렬 의미론 | `stele.matrix`, `stele.world` | K3 / LP / boolean 다치 의미론 |

**증명항 코어**가 이 문서에서 다루는 형식 언어다.
나머지 두 레이어는 별도 명세를 따른다.

---

## 2. 공식(Formula) 언어

### 2.1 어휘

```
VAR      ::= [A-Za-z_][A-Za-z0-9_]*   (* not a reserved keyword *)

keywords ::= "false" | "not" | "and" | "or"
             (* "->" is a punctuation token, not a keyword *)
```

### 2.2 공식 문법 (EBNF)

```ebnf
formula     ::= implication
implication ::= disjunction ("->" implication)?
disjunction ::= conjunction  ("or" conjunction)*
conjunction ::= negation     ("and" negation)*
negation    ::= "not" negation
              | atom
atom        ::= VAR
              | "false"
              | "(" formula ")"
```

**결합 방향:**

| 연결사 | 결합 방향 | 예시 |
|--------|----------|------|
| `->` | 오른쪽(right) | `A -> B -> C` = `A -> (B -> C)` |
| `or`  | 왼쪽(left)   | `A or B or C` = `(A or B) or C` |
| `and` | 왼쪽(left)   | `A and B and C` = `(A and B) and C` |
| `not` | 전위(prefix) | `not not A` = `not (not A)` |

**우선순위 (낮은 것부터):** `->` < `or` < `and` < `not`

따라서 `not A and B or C -> D`는
`(((not A) and B) or C) -> D`로 파싱된다.

### 2.3 부정 약어

부정은 두 가지 방식으로 표현할 수 있다.

1. **표면 문법:** `not A` — 파서가 `Op("not", (A,))`로 표현
2. **내부 정규형:** `A -> false` — `Op("imp", (A, Op("bot", ())))`

타입 검사기(`stele.core.typing`)는 두 표현을 `normalize_neg`로 동일하게 처리한다.

```
not A  ≡  A -> false  (모든 규칙에서 투명하게 처리됨)
```

### 2.4 바텀(⊥)

`false`는 바텀(bottom, ⊥)을 나타내며 `Op("bot", ())`로 표현된다.

---

## 3. 증명항(Proof Term) 언어

### 3.1 어휘

```
term keywords ::= "fun" | "λ" | "case" | "of" | "inl" | "inr"
               | "pair" | "fst" | "snd" | "abort"
               | "and" | "or" | "not" | "false"   (* formula keywords *)

punctuation   ::= "(" | ")" | "," | ":" | "=>" | "->" | "|"
```

이 키워드들은 증명항 변수 이름으로 사용할 수 없다.
변수 이름은 공식 변수와 동일한 형태이지만, `TVar`로 구분된다(타입 변수가 아닌 증명항 변수임에 주의).

### 3.2 증명항 문법 (EBNF)

```ebnf
term      ::= fun_term | case_term | app_term

fun_term  ::= ("fun" | "λ") VAR ":" formula "=>" term

case_term ::= "case" app_term "of"
              "inl" VAR "=>" term "|"
              "inr" VAR "=>" term

app_term  ::= primary ("(" term ")")*

primary   ::= VAR
            | "(" term ")"
            | "pair"  "(" term "," term ")"
            | "fst"   "(" term ")"
            | "snd"   "(" term ")"
            | "inl"   "(" term "," formula ")"
            | "inr"   "(" term "," formula ")"
            | "abort" "(" term "," formula ")"
```

**적용(application):** `f(a)` — 함수 다음에 괄호로 인수를 적용한다.
연쇄 적용은 `f(a)(b)` (왼쪽 결합).

**람다:** `fun x: A => body` 또는 `λ x: A => body` — 둘 다 동일.

**타입 어노테이션:** `inl(t, B)`, `inr(t, A)`, `abort(t, C)` 의 두 번째 인수는
공식(formula) 이며, 타입 합성(synthesis)을 위해 필수다.

### 3.3 증명항 예시

```
-- 항등 함수: A -> A
fun x: A => x

-- K 조합자: A -> B -> A
fun x: A => fun y: B => x

-- MP: (A -> B) -> A -> B
fun f: A -> B => fun a: A => f(a)

-- 논리곱 소거
fst(pair(x, y))

-- 논리합 도입 (왼쪽)
inl(x, B)

-- 논리합 제거
case e of inl x => x | inr y => y

-- 거짓 제거
abort(bot_proof, A)

-- 부정 적용: not A = A -> false, 고로 App(not_a_term, a_term) 타입 false
fun h: not P => fun a: P => h(a)
```

---

## 4. 정적 의미론 (타입 규칙)

### 표기

```
Γ         — 타입 컨텍스트: 유한 부분함수 (VAR → Formula)
Γ ⊢ t : A — 컨텍스트 Γ 아래 항 t가 타입 A를 가짐
Γ, x:A    — Γ를 x:A로 확장 (x가 Γ에 이미 있으면 새 바인딩이 우선)
```

구현 대응: `stele.core.typing.infer` / `check`, `stele.core.typing.Context`

### 4.1 변수

```
x:A ∈ Γ
──────────────────    (TVar)
Γ ⊢ TVar(x) : A
```

### 4.2 함의 도입 / 제거

```
Γ, x:A ⊢ t : B
──────────────────────────────    (Lam / →I)
Γ ⊢ Lam(x, A, t) : A -> B


Γ ⊢ f : A -> B    Γ ⊢ a : A
──────────────────────────────    (App / →E, MP)
Γ ⊢ App(f, a) : B
```

**부정:** `not A = A -> false`이므로
`Lam(x, not_A, t)` : `not A -> B` 를 그대로 타입 검사한다.

### 4.3 논리곱 도입 / 제거

```
Γ ⊢ l : A    Γ ⊢ r : B
──────────────────────────────    (Pair / ∧I)
Γ ⊢ Pair(l, r) : A and B


Γ ⊢ p : A and B                  Γ ⊢ p : A and B
──────────────────────    (Fst)   ──────────────────────    (Snd)
Γ ⊢ Fst(p) : A                   Γ ⊢ Snd(p) : B
```

### 4.4 논리합 도입 / 제거

```
Γ ⊢ v : A                         Γ ⊢ v : B
──────────────────────────    (Inl / ∨I₁)
Γ ⊢ Inl(v, B) : A or B

──────────────────────────    (Inr / ∨I₂)
Γ ⊢ Inr(v, A) : A or B


Γ ⊢ e : A or B    Γ, x:A ⊢ l : C    Γ, y:B ⊢ r : C
──────────────────────────────────────────────────────    (Case / ∨E)
Γ ⊢ Case(e, x, l, y, r) : C
```

`Case` 의 두 분기는 동일한 결과 타입 C를 가져야 한다(부정 정규화 모듈로 동치 비교).

### 4.5 바텀 제거

```
Γ ⊢ t : false
──────────────────────────    (Abort / ⊥E)
Γ ⊢ Abort(t, C) : C
```

### 4.6 양방향 타입 검사

구현은 두 모드를 제공한다.

- **합성(synthesis) / `infer`:** 항으로부터 타입을 생성한다.
  모든 생성자는 타입 합성에 충분한 어노테이션을 보유한다.
- **검사(checking) / `check`:** 도입 형식(Lam, Pair, Inl, Inr, Case)에 대해
  기대 타입을 분해하는 검사 규칙을 우선 적용한다.
  그 외는 `infer` 후 동치 비교로 fallback한다.

---

## 5. 동적 의미론 (β-환원)

### 5.1 환원 규칙

구현 대응: `stele.core.reduce.step`

```
App(Lam(x, A, body), arg)          ↦  body[arg/x]           (β_imp)

Fst(Pair(a, b))                    ↦  a                     (β_fst)

Snd(Pair(a, b))                    ↦  b                     (β_snd)

Case(Inl(a, _), x, lb, y, rb)     ↦  lb[a/x]               (β_case_l)

Case(Inr(b, _), x, lb, y, rb)     ↦  rb[b/y]               (β_case_r)
```

η-환원은 v1에서 미구현이다.

각 규칙은 순차 계산에서 **절단 제거(cut elimination)**에 대응한다:
- β_imp = 함의 도입(Lam) 다음에 바로 함의 제거(App)
- β_fst / β_snd = 논리곱 도입(Pair) 다음에 바로 제거(Fst/Snd)
- β_case_l / β_case_r = 논리합 도입(Inl/Inr) 다음에 바로 제거(Case)

### 5.2 포착 회피 치환

`body[arg/x]`는 포착 회피(capture-avoiding) 치환이다(`stele.core.reduce.substitute`).

- **그림자(shadowing):** 바인더가 `x`를 재바인드하면 그 이하에 치환하지 않는다.
- **포착 회피:** 바인더의 이름이 `arg`의 자유 변수(free variable)에 속하면
  바인더를 알파 재명명한다(새 이름: `NAME_0`, `NAME_1`, …).

### 5.3 환원 전략

`stele.core.reduce.step`은 **최좌-최외(leftmost-outermost / normal order)** 전략을 사용한다.

1. 복합 노드에서 가장 바깥 환원 쌍(redex)을 먼저 시도한다.
2. 헤드 환원 쌍이 없으면 부분항을 왼쪽→오른쪽 순으로 재귀 탐색한다.
3. 환원 쌍이 없으면 `None`을 반환한다(정규형).

이 전략은 결정적이다.

### 5.4 정규화

```python
normalize(term, fuel=1000) -> Term   # step 반복, 연료 소진 시 ReductionError
is_normal(term) -> bool              # step(term) is None
```

`fuel` 매개변수는 명시적 종료 보증 없이 구현 버그를 방어하는 안전장치다.
단순 타입 직관주의 단편은 표준 메타이론에 의해 정규화됨이 알려져 있다.

---

## 6. 증명 스크립트와 증명항의 관계

### 6.1 두 레이어 공존

| 레이어 | 역할 |
|--------|------|
| 증명 스크립트(Stele-Light) | `have h by rule refs` 형식; 커널이 규칙 스키마로 검증 |
| 증명항(Curry–Howard) | 항 생성자; 타입 검사기가 추론 규칙을 검증 |

두 레이어는 **독립적이며 서로를 임포트하지 않는다**
(`test_regression_invariants.py::TestKernelInvariance`가 정적으로 보장).

### 6.2 정교화(Elaboration) — 지원 직관주의 규칙

`stele.elaborate` 모듈은 지원되는 직관주의 증명 스크립트를 증명항으로 변환한다.

| 증명 규칙 | 증명항 |
|-----------|--------|
| `assume` / `suppose` | `TVar` |
| `copy` | 변수 재사용 |
| `mp` | `App` |
| `imp_intro` | `Lam` |
| `neg_intro` | `Lam` (`not A = A -> false`) |
| `neg_elim` | `App` |
| `and_intro` | `Pair` |
| `and_elim_left` | `Fst` |
| `and_elim_right` | `Snd` |
| `or_intro_left` | `Inl` |
| `or_intro_right` | `Inr` |
| `or_elim` | `Case` |
| `ex_falso` | `Abort` |

**고전 규칙 (`dne`, `lem`, `pbc`)은 증명항 정교화를 지원하지 않는다.**
이 규칙들은 제어 연산자 또는 이중부정 번역이 필요한 별도의 설계가 필요하다.

### 6.3 상호 검증

```python
from stele.elaborate import crosscheck_theorem

result = crosscheck_theorem(thm)
# result.ok == True 조건:
#   1. 커널이 스크립트를 허가
#   2. 스크립트가 증명항으로 정교화 성공
#   3. 증명항이 결론 공식에 대해 타입 검사 통과
```

### 6.4 행렬 의미론 (K3 / LP / boolean)

행렬 의미론은 **증명항 계산법이 아니다**.
K3·LP·boolean의 `evaluate`·`is_tautology`·`entails` 함수는 `stele.matrix`에 독립적으로 존재한다.

---

## 7. v1 제외 범위

| 항목 | 설명 |
|------|------|
| 고전 증명항 | `dne`, `lem`, `pbc` 연산자가 필요; 별도 설계 필요 |
| 제어 연산자 | `callcc`, `shift/reset` 등 |
| η-환원 | β-정규형 이후 추가 정규화; v1 미구현 |
| 한정 기호 | 1차 논리 전용; 명제논리 단편 밖 |
| 의존 타입 | 프로포지션으로서의 타입; 명제논리 단편 밖 |
| K3 / LP 증명항 | K3·LP는 의미론 모듈; 증명항 구조 없음 |
| 증명 탐색 / 자동화 | Stele는 검증기이지 증명기가 아님 |
| 증명항 → 스크립트 역방향 | v1 미구현 |
