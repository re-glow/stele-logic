# Stele-Light 언어 가이드

Stele-Light는 자연연역 증명을 **사람이 읽을 수 있게** 적는 표면 언어다. 커널은 정리증명기가 아니라 **검증기**다 — 당신이 단계를 명시하면, 커널은 각 단계가 *선언된 논리 세계*에서 유효한 규칙 인스턴스인지만 판정한다.

---

## 1. 한눈에 보기

```
theorem dne_law using classical_prop:
  suppose h1: not not P            # 가정을 도입하는 하위증명 시작
    have h2: P by dne h1           # 규칙 dne 적용
  have h3: not not P -> P by imp_intro h1 h2   # ->I 로 가정 방출
  conclude not not P -> P by h3
```

각 줄은 `라벨: 식`을 만들고, 이후 줄은 그 라벨로 앞선 결과를 참조한다.

---

## 2. 어휘 구조

| 종류 | 형태 |
|---|---|
| 식별자 | `[A-Za-z_][A-Za-z0-9_]*` — 명제 변수(`P`), 라벨(`h1`), 규칙명(`mp`) |
| 상수 | `false` — 항상 거짓인 식(⊥, falsum). 내부표현 `Op("bot", ())`. |
| 키워드 연산자 | `not` `and` `or` |
| 함의 기호 | `->` |
| 괄호 | `(` `)` |
| 주석 | `#` 부터 줄 끝까지 |

들여쓰기(선행 공백)는 의미가 있다 — 하위증명 블록을 정한다(§5). 탭이 아니라 공백을 쓴다.

---

## 3. 식 문법

EBNF:

```ebnf
formula = imp ;
imp     = disj [ "->" imp ] ;        (* 우결합 *)
disj    = conj { "or" conj } ;       (* 좌결합 *)
conj    = neg  { "and" neg } ;       (* 좌결합 *)
neg     = "not" neg | atom ;
atom    = ident | "false" | "(" formula ")" ;
```

`false` 는 예약 상수(falsum, ⊥)다. 명제 변수로 쓸 수 없다.

**우선순위** (강→약): `not` > `and` > `or` > `->`. `->` 는 우결합.

| 입력 | 해석 |
|---|---|
| `not P and Q` | `(not P) and Q` |
| `not not P` | `not (not P)` |
| `P -> Q -> R` | `P -> (Q -> R)` |
| `(P -> Q) -> R` | 괄호로 좌결합 강제 |
| `P and Q or R` | `(P and Q) or R` |

---

## 4. 증명 문법

```ebnf
proof     = "theorem" ident [ "using" ident ] ":" body ;
body      = INDENT statement+ ;
statement = assume | have | suppose | conclude ;

assume    = "assume"  label ":" formula ;
have      = "have"    label ":" formula "by" rule { arg } ;
suppose   = "suppose" label ":" formula INDENT statement+ ;   (* 하위증명 *)
conclude  = "conclude" formula "by" ref ;

label = ident ; rule = ident ; arg = ident ; ref = ident ;
```

- **`theorem NAME [using LOGIC]:`** — 정리 이름과 (선택적) 논리 세계. `using` 생략 시 기본은 `intuitionistic_prop`. 명령행 `--logic` 이 파일의 `using` 보다 우선한다.
- **`assume L: F`** — 가정(열린 전제) `F` 를 라벨 `L` 로 도입. 최상위에서는 정리의 전제(Γ)가 된다.
- **`have L: F by RULE args...`** — `RULE` 을 인자(앞선 라벨들)에 적용하여 `F` 를 도출. 커널이 규칙 결과와 `F` 의 일치를 검사한다.
- **`suppose L: F`** + 들여쓰기 블록 — 가정 `F` 를 두고 블록 안에서 추론한다. 블록이 닫히면 그 안의 라벨은 **스코프를 벗어난다(방출)**. 오직 `imp_intro` 만 그 블록을 참조할 수 있다(§6).
- **`conclude F by REF`** — 최상위 결론. `REF` 가 가리키는 식이 `F` 와 같아야 한다. 모든 정리에 정확히 하나 필요.

---

## 5. 규칙 레퍼런스

표기: `전제 ⊢ 결론`. 대문자 `A, B`는 임의의 식에 맞는 메타변수.

| 규칙 | 형태 | 인자 | intuitionistic | classical |
|---|---|---|:---:|:---:|
| `copy` | `A ⊢ A` | 1 | ● | ● |
| `mp` (→E) | `A→B, A ⊢ B` | 2 | ● | ● |
| `imp_intro` (→I) | `[A]…B ⊢ A→B` | 2 (방출) | ● | ● |
| `and_intro` | `A, B ⊢ A∧B` | 2 | ● | ● |
| `and_elim_left` | `A∧B ⊢ A` | 1 | ● | ● |
| `and_elim_right` | `A∧B ⊢ B` | 1 | ● | ● |
| `neg_elim` (¬E) | `A, ¬A ⊢ false` | 2 | ● | ● |
| `ex_falso` (⊥E) | `false ⊢ A` | 1 | ● | ● |
| `or_intro_left` (∨I₁) | `A ⊢ A∨B` | 1 | ● | ● |
| `or_intro_right` (∨I₂) | `B ⊢ A∨B` | 1 | ● | ● |
| `dne` | `¬¬A ⊢ A` | 1 | ✗ | ● |

두 세계는 `dne` 단 하나로 갈린다. 이것이 상대성 데모의 축이다.
`ex_falso`, `or_intro_left`, `or_intro_right` 는 **결론 주도 매칭**(conclusion-directed matching)을 사용한다 — 결론에만 나타나는 메타변수(`B` in ∨I₁, `A` in ∨I₂, `A` in ⊥E)는 사용자가 `have` 에 적은 식으로 결정된다.

**예시 (각 규칙)**

```
have c: P by copy a                       # a: P
have c: Q by mp imp a                     # imp: P -> Q, a: P
have c: P and Q by and_intro a b          # a: P, b: Q
have c: P by and_elim_left a              # a: P and Q
have c: Q by and_elim_right a             # a: P and Q
have c: false by neg_elim a na            # a: P, na: not P
have c: Q by ex_falso bot                 # bot: false  (Q 는 임의의 식)
have c: P or Q by or_intro_left a         # a: P  (Q 는 임의의 식)
have c: P or Q by or_intro_right b        # b: Q  (P 는 임의의 식)
have c: P by dne a                        # a: not not P   (classical 전용)
```

---

## 6. 가정과 방출 (suppose / imp_intro)

`->I` 는 "`A` 를 가정하고 `B` 를 얻으면 `A->B` 를 결론한다"는 규칙이다. Stele-Light에서는 `suppose` 블록으로 가정을 두고, 블록이 닫힌 뒤 `imp_intro <가정라벨> <결론라벨>` 로 방출한다.

```
theorem imp_self:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h2
  conclude P -> P by h3
```

**스코프 규칙:** 하위증명 안의 라벨(`h2`)은 블록이 닫히면 일반 규칙으로 참조할 수 없다(방출됨). 다음은 오류다:

```
theorem leak:
  suppose h1: P
    have h2: P by copy h1
  have h3: P by copy h2      # X — h2 는 이미 방출되어 스코프 밖
  conclude P by h3
```

→ `unknown reference 'h2'` (line 4).

---

## 7. 논리 선택과 상대성

같은 증명, 다른 세계, 다른 판정:

```
$ python -m stele.cli check examples/dne.stele --logic classical_prop
OK Proof verified: dne_consequent   [logic: classical_prop]

$ python -m stele.cli check examples/dne.stele --logic intuitionistic_prop
X Proof failed: dne_consequent (line 3)
  rule 'dne' is not available in logic 'intuitionistic_prop'
```

**정직한 한계.** 검사기가 보이는 것은 *그 증명이 직관논리 규칙으로는 타입검사되지 않음*이다. `dne` 없이도 `¬¬P→P` 가 도출 불가능하다는 것은 메타 주장이며, 검사기가 직접 확립하지 못한다. 그 비도출성을 *의미론적으로* 보이는 것은 matrix 모드와 이후 단계의 크립키 의미론의 몫이다(§9 참조 — `demos`).

---

## 8. 오류 카탈로그

| 메시지 | 원인 | 해결 |
|---|---|---|
| `expected 'theorem NAME [using LOGIC]:'` | 헤더 형식 오류 | 첫 줄을 `theorem 이름:` 으로 |
| `rule 'X' is not available in logic 'L'` | 그 세계에 없는 규칙 사용 | 세계를 바꾸거나(`--logic`/`using`) 다른 규칙 사용 |
| `rule 'X': premise i expected …, but 'ref' is …` | 인자의 식이 규칙 패턴과 불일치 | 올바른 라벨을 인자로, 또는 식 수정 |
| `rule 'X' yields …, but the line claims …` | 규칙 결과와 `have` 의 식이 다름 | `have` 의 식을 규칙 결과에 맞춤 |
| `unknown reference 'r'` | 없는/방출된 라벨 참조 | 라벨 철자 확인, 스코프(§6) 확인 |
| `imp_intro requires a closed subproof that assumes 'a' and derives 'b'` | `suppose` 블록과 인자 불일치 | `imp_intro <가정라벨> <블록내결론라벨>` |
| `conclusion … does not match 'r' = …` | `conclude` 식이 참조와 불일치 | 두 식을 일치 |
| `proof has no 'conclude' line` | 결론 누락 | `conclude … by …` 추가 |

---

## 9. 첫 증명 작성하기

목표: `(P → Q) → (P → Q)` 가 아니라, 간단히 **`P, P→Q ⊢ Q`** (mp) 를 증명해 보자.

```
theorem first:
  assume given_imp: P -> Q
  assume given_p: P
  have q: Q by mp given_imp given_p
  conclude Q by q
```

```
$ python -m stele.cli check first.stele --logic intuitionistic_prop
OK Proof verified: first   [logic: intuitionistic_prop]
```

두 세계 모두에서 통과한다(`mp` 는 공통 규칙). 이제 `dne` 를 써서 두 세계의 차이를 직접 확인해 보라.

웹 UI(`python -m stele.web`)에서는 예제를 불러오고 세계 토글을 바꾸며 판정이 뒤집히는 것을 즉시 볼 수 있다.

---

## 10. 한계와 다음 단계

- 현재는 **명제논리 단편**이다. 1차 논리(한정사)는 미구현 — 로드맵 Phase 6.
- 상대성은 *규칙 가용성* 수준에서 작동한다(§7의 정직한 한계).
- matrix 모드(다치 의미론)는 별도 모듈이며 표면 문법이 아직 없다 — `python -m stele.cli demos` 로 실행.
- 전체 설계·단계: `stele_redesign.md`. 결정·근거: `DECISIONS.md`.
