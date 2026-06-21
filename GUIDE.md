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
| `neg_intro` (¬I) | `[A]…false ⊢ ¬A` | 2 (방출) | ● | ● |
| `or_elim` (∨E) | `A∨B, [A]…C, [B]…C ⊢ C` | 5 (방출×2) | ● | ● |
| `dne` | `¬¬A ⊢ A` | 1 | ✗ | ● |
| `lem` | `⊢ A∨¬A` | 0 | ✗ | ● |
| `pbc` | `[¬A]…false ⊢ A` | 2 (방출) | ✗ | ● |

`classical_prop` 는 `intuitionistic_prop` 에 고전 원리 `dne`, `lem`, `pbc` 를 추가한다. 세 규칙은 고전논리 안에서 서로 도출 가능하지만(쌍방 동치), 직관논리에서는 성립하지 않으며 Stele에서는 별개의 이름 있는 규칙으로 노출된다.

`ex_falso`, `or_intro_left`, `or_intro_right`, `lem` 은 **결론 주도 매칭**(conclusion-directed matching)을 사용한다 — 결론에만 나타나는 메타변수는 사용자가 `have` 에 적은 식으로 결정된다.
`neg_intro`, `or_elim`, `pbc` 는 일반화된 방출 메커니즘(`RuleSchema.hyp_premises`)을 사용한다.

**예시 (각 규칙)**

```
have c: P by copy a                           # a: P
have c: Q by mp imp a                         # imp: P -> Q, a: P
have c: P and Q by and_intro a b              # a: P, b: Q
have c: P by and_elim_left a                  # a: P and Q
have c: Q by and_elim_right a                 # a: P and Q
have c: false by neg_elim a na                # a: P, na: not P
have c: Q by ex_falso bot                     # bot: false  (Q 는 임의의 식)
have c: P or Q by or_intro_left a             # a: P  (Q 는 임의의 식)
have c: P or Q by or_intro_right b            # b: Q  (P 는 임의의 식)
have c: not A by neg_intro h_a h_bot          # h_a: suppose label (A), h_bot: false 유도
have c: C by or_elim h_ab h_a h_c1 h_b h_c2  # h_ab: A or B, [h_a]C, [h_b]C  (C 는 임의의 식)
have c: P by dne a                            # a: not not P   (classical 전용)
have c: P or not P by lem                     # (classical 전용, 인자 없음, A는 결론에서 결정)
have c: P by pbc h_np h_bot                   # h_np: suppose label (not P), h_bot: false 유도 (classical 전용)
```

**`neg_intro` 예시 (완전한 증명)**

```
theorem neg_intro_demo:
  suppose h1: P and not P       # 가정 A
    have h2: P by and_elim_left h1
    have h3: not P by and_elim_right h1
    have h4: false by neg_elim h2 h3
  have h5: not (P and not P) by neg_intro h1 h4
  conclude not (P and not P) by h5
```

**`or_elim` 예시 — 선언 교환(commutativity)**

```
theorem or_comm:
  assume h1: P or Q
  suppose h2: P                         # 좌 분기 시작 (가정 라벨 h2)
    have h3: Q or P by or_intro_right h2
  suppose h4: Q                         # 우 분기 시작 (가정 라벨 h4)
    have h5: Q or P by or_intro_left h4
  have h6: Q or P by or_elim h1 h2 h3 h4 h5
  conclude Q or P by h6
```

`or_elim <선언라벨> <좌가정> <좌결론> <우가정> <우결론>` — 인자 5개.

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

고전 원리 `dne`, `lem`, `pbc` 는 모두 `classical_prop` 에서만 사용할 수 있다.
예를 들어 배중률(`P or not P`)과 피어스 법칙(`((P→Q)→P)→P`)은 고전논리에서 검증되지만 직관논리에서는 거부된다:

```
$ python -m stele.cli check examples/lem.stele
OK Proof verified: lem_demo   [logic: classical_prop]

$ python -m stele.cli check examples/peirce.stele
OK Proof verified: peirce   [logic: classical_prop]
```

`lem` 이나 `pbc` 를 직관논리 증명 안에서 쓰면 `"rule '...' is not available in logic 'intuitionistic_prop'"` 오류가 발생한다.

**논리 경계(logic boundary).** `classical_prop = intuitionistic_prop + {dne, lem, pbc}`. 세 추가 규칙은 고전논리 안에서 서로 도출 가능(쌍방 동치)하다. Stele는 그것들을 별개의 이름 있는 규칙으로 노출함으로써 어떤 원리를 쓰는지를 증명 텍스트 수준에서 명시적으로 드러낸다.

**정직한 한계.** 검사기가 보이는 것은 *그 증명이 직관논리 규칙으로는 타입검사되지 않음*이다. `dne`/`lem`/`pbc` 없이도 해당 명제가 도출 불가능하다는 것은 메타 주장이며, 검사기가 직접 확립하지 못한다. 그 비도출성을 *의미론적으로* 보이는 것은 matrix 모드(§8)와 `soundness` 명령(§9)의 몫이다.

---

## 8. 행렬 모드 (matrix mode)

Stele의 두 번째 평가 경로 — **행렬 의미론(`⊨` 측면)** — 을 `.stele` 파일과 CLI에서 직접 쓸 수 있다.

### 8.1 논리 선택

`--logic` 에 아래 행렬 이름 중 하나를 지정하면 check 명령이 자동으로 행렬 모드로 전환한다.

| `--logic` | 지정값 | 세 번째 진리치 |
|---|---|---|
| `boolean` | `{T}` | 없음 (고전 2치) |
| `K3` | `{T}` | `I` (정의되지 않음) |
| `LP` | `{T, B}` | `B` (참이면서 거짓) |

증명 모드 논리(`classical_prop`, `intuitionistic_prop`)와 행렬 모드 논리는 완전히 별개의 평가 경로다. 증명 파일을 행렬 논리에 넘기거나 행렬 파일을 증명 논리에 넘기면 파서 오류가 발생한다.

### 8.2 행렬 지시문 문법

행렬 모드 `.stele` 파일은 지시문(directive) 한 줄씩으로 구성된다. `#` 이후는 주석.

**`evaluate <식>`** — 모든 변수 배정에 걸쳐 식이 취할 수 있는 진리치 집합을 보고한다.

```
evaluate P or not P
```

출력 예 (K3): `evaluate P or not P  =>  {I, T}`

**`tautology? <식>`** — 모든 배정에서 식이 지정값이면 `yes`, 아니면 `no`.

```
tautology? P or not P
```

출력 예 (K3): `tautology? P or not P  =>  no`

**`entails <전제>, ..., |- <결론>`** — 반례가 없으면 `yes`; 반례가 있으면 반례 배정과 함께 `no`.
전제가 없으면 `|-` 만 쓴다.

```
entails P, not P |- Q
entails |- P or not P
```

출력 예 (LP): `entails P, not P |- Q  =>  no  (counterexample: P=B, Q=F)`

**`fixpoint not`** — 부정의 고정점: `not v = v` 를 만족하는 진리치를 보고한다. 별칭 `liar` 도 동일하게 동작한다.

```
fixpoint not
liar
```

출력 예 (K3): `fixpoint not  =>  {I}`
출력 예 (LP): `fixpoint not  =>  {B}`
출력 예 (boolean): `fixpoint not  =>  {}`

고정점은 거짓말쟁이 역설의 진리치에 해당한다. K3에서는 "정의되지 않음"(I), LP에서는 "참이면서 거짓"(B), 고전논리(boolean)에서는 고정점이 없다.

### 8.3 예시 실행

```
$ python -m stele.cli check examples/matrix_k3.stele --logic K3
tautology? P or not P  =>  no
evaluate P or not P  =>  {I, T}
entails P -> Q, P |- Q  =>  yes
tautology? P -> P  =>  no

$ python -m stele.cli check examples/matrix_lp.stele --logic LP
entails P, not P |- Q  =>  no  (counterexample: P=B, Q=F)
...

$ python -m stele.cli check examples/matrix_boolean.stele --logic boolean
tautology? P or not P  =>  yes
...
```

### 8.4 증명 모드와 행렬 모드의 관계

| 기준 | 증명 모드 (`⊢`) | 행렬 모드 (`⊨`) |
|---|---|---|
| 선택 | `--logic classical_prop` 등 | `--logic K3` 등 |
| 파일 문법 | `theorem … :` | `evaluate / tautology? / entails` |
| 검사 방식 | 신뢰 커널이 규칙 인스턴스 확인 | `matrix.py` 가 진리표 계산 |
| 주장 범위 | 특정 증명이 규칙에 맞는가 | 명제가 의미론적으로 타당한가 |

두 모드는 직교한다. 직관논리에서 `dne` 없이 증명이 안 된다는 것은 증명 모드의 판정이다. 그 명제가 의미론적으로 도출 불가능하다는 것은 별개의 메타 주장이며, 행렬 모드가 반례 탐색으로 접근한다.

---

## 9. 규칙 건전성 보고 (`soundness` 명령)

### 9.1 명령 형식

```
python -m stele.cli soundness --logic <증명논리> --matrix <행렬>
```

예:

```
python -m stele.cli soundness --logic classical_prop --matrix K3
python -m stele.cli soundness --logic classical_prop --matrix boolean
python -m stele.cli soundness --logic intuitionistic_prop --matrix K3
```

`--logic` 에는 증명 논리(`classical_prop`, `intuitionistic_prop`)를, `--matrix` 에는 행렬 이름(`K3`, `LP`, `boolean`)을 지정한다.

### 9.2 출력 형식

```
soundness  [logic: classical_prop | matrix: K3]
  and_elim_left: sound
  lem: unsound  counterexample: A=I
  imp_intro: skipped  (discharge rules not checked in v1)
  ...
```

각 규칙에 대해 세 가지 상태 중 하나를 보고한다:

| 상태 | 의미 |
|---|---|
| `sound` | 모든 배정에서 전제가 지정되면 결론도 지정됨 |
| `unsound` | 전제는 지정되지만 결론이 지정되지 않는 반례 배정이 존재함 |
| `skipped` | v1에서 검사 대상이 아닌 방출 규칙(discharge rule) |

### 9.3 v1 범위와 한계

**검사 대상**: `hyp_premises == ()` 인 규칙 (비방출 규칙)만 검사.
**건너뜀**: `imp_intro`, `neg_intro`, `or_elim`, `pbc` 등 방출 규칙 — `hyp_premises` 가 있는 규칙.

방출 규칙의 의미론적 건전성은 더 정교한 의미론(예: 크립키 의미론)이 필요하며, v1에서는 다루지 않는다.

### 9.4 결과 해석 — 중요한 의미론적 주의사항

**행렬 건전성은 증명-이론적 도출가능성과 다르다.** 이 명령이 보고하는 것은 *지정값 보존(designation preservation)* — "전제가 지정되면 결론도 지정되는가". 이것은 해당 논리가 그 행렬에 대해 건전(sound)한지의 *조건 중 일부*이지, 완전한 증명이 아니다.

**예상 밖의 결과들:**

- `dne` (¬¬A ⊢ A): K3와 LP 모두에서 **건전**. K3에서 ¬¬A가 지정값(=T)이 되려면 A = T이어야 하므로 결론도 T.
- `lem` (⊢ A∨¬A): K3에서 **불건전** (A=I 반례), LP에서 **건전** (B가 지정값이므로 A∨¬A ∈ {T,B}).
- `neg_elim` (A, ¬A ⊢ false): LP에서 **불건전** (A=B이면 A와 ¬A 모두 지정값 B, 결론 false는 비지정값).
- `mp` (A→B, A ⊢ B): LP에서 **불건전** (A=B, B_var=F이면 A→B=B 지정값, A=B 지정값, B_var=F 비지정값).

이 결과들은 LP가 폭발 원리와 전건긍정을 거부하는 초일관 논리임을 의미론적으로 확인해 준다.

**주의**: `unsound` 판정이 "그 규칙을 써서 만든 증명이 Stele에서 거부된다"는 뜻이 아니다. Stele의 proof checker는 행렬 의미론에 의존하지 않는다. 건전성 보고는 순수하게 *의미론적 진단*이다. 이 두 가지를 혼동하지 말 것.

---

## 10. 오류 카탈로그 (증명 모드)

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

## 11. 첫 증명 작성하기

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

## 12. 한계와 다음 단계

- 현재는 **명제논리 단편**이다. 1차 논리(한정사)는 미구현 — 로드맵 Phase 6.
- 상대성은 *규칙 가용성* 수준에서 작동한다(§7의 정직한 한계).
- 규칙 건전성 보고(§9)는 비방출 규칙만 다루는 v1이다. 방출 규칙의 의미론적 건전성은 추후 크립키 의미론으로 확장 예정.
- 전체 설계·단계: `stele_redesign.md`. 결정·근거: `DECISIONS.md`.
