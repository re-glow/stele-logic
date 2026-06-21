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

## 10. 의미론적 세계 (`World`)

### 10.1 World란

`World`는 행렬과 공리 집합의 쌍이다:

```
World(matrix_name, axioms)
```

- `matrix_name`: 등록된 행렬 이름 (`"K3"`, `"LP"`, `"boolean"`)
- `axioms`: 지정된 전제로 작용하는 식들의 튜플 (기본값 `()`)

```python
from stele.world import World, status, PROVABLE, REFUTABLE, BOTH, INDEPENDENT
from stele.parser import parse_formula

w = World("boolean", (parse_formula("P -> Q"), parse_formula("P")))
s = status(parse_formula("Q"), w)   # PROVABLE
```

### 10.2 세계 상태 (Semantic Status)

`status(φ, world)` 는 행렬 귀결(`stele/matrix.py`)을 두 번 호출해 φ 와 ¬φ 의 귀결 여부를 조합한다:

| 상태 | 의미 |
|---|---|
| `PROVABLE` | `axioms ⊨ φ` 이지만 `axioms ⊭ ¬φ` |
| `REFUTABLE` | `axioms ⊭ φ` 이지만 `axioms ⊨ ¬φ` |
| `BOTH` | `axioms ⊨ φ` **이고** `axioms ⊨ ¬φ` — 초일관 행렬에서 가능 |
| `INDEPENDENT` | `axioms ⊭ φ` **이고** `axioms ⊭ ¬φ` |

**중요한 구별**: `PROVABLE`은 *세계의 공리 아래 행렬 지정값 보존으로 의미론적 귀결*이 성립함을 뜻한다. 증명 탐색이나 커널 검사와는 무관하다. Stele의 신뢰 커널은 이 계산에 전혀 관여하지 않는다.

### 10.3 흥미로운 사례

**Boolean 빈 세계:**
- `P or not P` → `PROVABLE` (항진식)
- `P` → `INDEPENDENT` (우발적 명제)
- `P and not P` → `REFUTABLE` (항위식)

**K3 빈 세계:**
- `P or not P` → `INDEPENDENT` (I가 비지정값이므로 항진도 항위도 아님)
- `P -> P` → `INDEPENDENT` (P=I 이면 I→I=I, 비지정값)

**LP 초일관 세계 (공리: P, not P):**
- `P` → `BOTH` — 공리 P와 ¬P 가 동시에 지정되는 배정(P=B)이 존재하며, 그 아래 P도 ¬P도 지정됨
- `BOTH` 상태는 LP의 초일관성 — 모순이 폭발로 이어지지 않음 — 을 직접 보여 준다.

### 10.4 한계

- `PROVABLE`은 의미론적 귀결이며 증명검색(proof search)의 결과가 아니다.
- 공리가 행렬에서 결코 동시에 지정될 수 없으면(`ex_falso`처럼), 귀결이 공허하게 성립해 모든 식이 `PROVABLE`이 될 수 있다.
- 세계 격자(world lattice) — 세계들 사이의 포함·비교 관계 — 는 미구현(로드맵).
- 증명-이론적 상태(증명 커널 기반)는 별도의 미래 작업이다.

---

## 11. 세계 격자 데모 (`lattice`)

### 11.1 lattice 명령

`lattice <formula>` 명령은 하나의 식이 세 개의 세계에서 어떤 의미론적 지위를 갖는지 한눈에 보여 준다:

```
python -m stele.cli lattice x
```

출력 예:

```
lattice  [formula: x | matrix: boolean]
  Gamma                       axioms: []                =>  INDEPENDENT
  Gamma + x                   axioms: [x]               =>  PROVABLE
  Gamma + not x               axioms: [not x]           =>  REFUTABLE
```

복합 식도 가능하다 (따옴표 필요):

```
python -m stele.cli lattice "P and Q"
python -m stele.cli lattice "P or not P"
```

### 11.2 기본 세계 집합 (CH-스타일 독립성 패턴)

`lattice`는 다음 세 세계를 자동으로 구성한다:

| 세계 | 행렬 | 공리 | 역할 |
|---|---|---|---|
| Gamma | boolean | (없음) | 기저 세계 |
| Gamma + φ | boolean | φ | 양의 확장 |
| Gamma + ¬φ | boolean | ¬φ | 음의 확장 |

모든 우발적 명제(neither tautology nor contradiction)는 이 세 세계에서 각각 INDEPENDENT / PROVABLE / REFUTABLE을 보인다.

### 11.3 CH-스타일 독립성 패턴

이 패턴은 **명제 논리적 독립성의 장난감 시연**이다. 진정한 연속체 가설(CH)이나 집합론적 강제법(forcing)과는 무관하다.

**패턴이 의미하는 것:**

```
Gamma  ⊭ φ   (φ 가 귀결되지 않음)
Gamma  ⊭ ¬φ  (¬φ 도 귀결되지 않음)
Gamma ∪ {φ}  ⊨ φ   (양의 확장에서 φ 귀결)
Gamma ∪ {¬φ} ⊨ ¬φ  (음의 확장에서 ¬φ 귀결)
```

**무엇이 아닌지:**
- 증명 탐색(proof search) 결과가 아니다 — Stele 커널은 전혀 관여하지 않는다.
- 집합론의 CH(연속체 가설)가 아니다.
- 강제법(forcing)이나 모델 확장이 아니다.
- 세계 격자 전체(world lattice)가 아니다 — 격자 구조는 로드맵 항목이다.

### 11.4 Python API

`stele/world.py`의 `lattice_status` 보조 함수를 직접 사용할 수도 있다:

```python
from stele.parser import parse_formula
from stele.ast import Op
from stele.world import World, lattice_status, PROVABLE, REFUTABLE, INDEPENDENT

phi = parse_formula("P")
neg = Op("not", (phi,))

worlds = [
    World("boolean", ()),
    World("boolean", (phi,)),
    World("boolean", (neg,)),
]

for w, s in lattice_status(phi, worlds):
    print(w.axioms, "=>", s)
# () => INDEPENDENT
# (Var('P'),) => PROVABLE
# (Op('not', (Var('P'),)),) => REFUTABLE
```

데모 스크립트 `examples/world_ch_style.py` 를 실행하면 동일한 패턴을 볼 수 있다:

```
python -m examples.world_ch_style
```

---

## 12. 오류 카탈로그 (증명 모드)

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

## 13. 첫 증명 작성하기

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

## 14. 증명 의존성 그래프 (`graph`)

### 14.1 개요

검증된 증명을 구조화된 유향 그래프로 표현할 수 있다. 각 라벨(가정·have 단계·결론)이 노드가 되고, 추론 규칙이 인용하는 이전 라벨이 의존성 간선(dep → step)이 된다.

```
python -m stele.cli graph examples/peirce.stele --logic classical_prop
```

출력 예 (일부):
```
graph  [peirce | logic: classical_prop]
  nodes (11):
    h: (P -> Q) -> P
    hnp: not P
    ...
    h_thm: ((P -> Q) -> P) -> P  [imp_intro]
    _conclude: ((P -> Q) -> P) -> P
  edges (14):
    hp -> hbot
    hnp -> hbot
    ...
  diagnostics: OK
```

### 14.2 동작 방식

1. 파일을 파싱한 후 **기존 proof 검사기로 먼저 검증**한다.
2. 검증을 통과해야 그래프를 생성한다. 검증 실패 시 오류를 보고하고 종료한다.
3. `Assume` → kind=assumption, `Suppose` → kind=suppose, `Have` → kind=have (규칙 이름 포함), `Conclude` → `_conclude` 노드.
4. `Have` 노드의 모든 refs(일반 전제·방출 규칙 레이블 포함)가 의존성 간선이 된다.

### 14.3 DOT 내보내기

`--dot` 플래그를 추가하면 Graphviz DOT 텍스트를 출력한다:

```
python -m stele.cli graph examples/peirce.stele --logic classical_prop --dot
```

Graphviz가 설치돼 있으면 별도로 렌더링할 수 있다:
```
python -m stele.cli graph examples/peirce.stele --logic classical_prop --dot > peirce.dot
dot -Tpng peirce.dot -o peirce.png
```

Graphviz는 **프로젝트 의존성이 아니다**. DOT 텍스트 출력만이 이 버전의 deliverable이다.

### 14.4 진단

그래프 커맨드는 세 가지 진단을 자동으로 실행한다:

| 진단 | 의미 |
|---|---|
| 순환 감지 | 의존성 그래프에 방향 순환이 있으면 경고. 검증된 증명에서는 발생하지 않아야 한다(방어적 불변 확인). |
| 미사용 가정 | 결론에 기여하지 않는 `assume`/`suppose` 노드를 보고. 방출된 가정도 인용됐으면 미사용으로 처리하지 않는다. |
| 고립 단계 | 결론으로 이어지지 않는 `have` 단계를 보고. |

### 14.5 Python API

```python
from stele.parser import parse_theorem
from stele.proofgraph import build_proof_graph, to_dot, has_cycle

thm = parse_theorem(open("examples/peirce.stele").read())
g = build_proof_graph(thm)
print(len(g.nodes), "nodes,", len(g.edges), "edges")
print(to_dot(g))          # DOT 텍스트
print(has_cycle(g))       # False (검증된 증명은 비순환)
```

### 14.6 한계

- 그래프 분석은 **구조적**이다. 정리 증명이나 증명 탐색이 아니다.
- 검증된 증명의 순환 감지는 대부분 방어적 확인이며, 미래의 그래프 조작 도구를 위한 것이다.
- 정의(definition) 노드는 미구현(정의 문법이 없다).
- 의존성 그래프의 더 깊은 분석(타입 불일치, 순환 의존성 위치추정 등)은 로드맵 항목이다.

---

## 15. 구조적 진단 (`diagnose`)

### 15.1 개요

`diagnose` 커맨드는 증명 파일의 구조적 문제를 **목록으로 수집**한다. 첫 번째 오류에서 멈추는 `check` 와 달리, 증명을 끝까지 분석해 발견된 모든 문제를 분류하여 보고한다.

> **중요:** 진단은 **untrusted 분석 계층**이다. 트러스티드 커널(`kernel.py`)이 증명 유효성의 유일한 권위자다. 진단 결과가 통과해도 `check` 가 거부하면 증명은 무효다.

```
python -m stele.cli diagnose examples/diag_undef.stele
python -m stele.cli diagnose examples/peirce.stele --logic classical_prop
```

출력 형식:
```
ERROR UndefinedSymbol line=6: cited label 'missing' does not exist in this proof
WARNING UnusedAssumption line=5: assumption 'h2' does not contribute to the conclusion
OK no diagnostics: peirce
```

종료 코드: `error` 진단이 하나라도 있으면 1, `warning` 만 있거나 없으면 0.

### 15.2 v1 진단 코드

| 코드 | 심각도 | 감지 내용 |
|---|---|---|
| `UndefinedSymbol` | error | 이 증명 어디에도 정의되지 않은 레이블 참조 |
| `MissingHypothesis` | error | 존재하지만 현재 스코프 밖에 있는 레이블 참조 (전방 참조·닫힌 서브 증명 누출·결론 스코프 위반) |
| `UnsupportedConclusion` | error | `conclude` 포뮬러가 참조 레이블의 포뮬러와 불일치 |
| `CircularDependency` | error | 의존성 그래프에 방향 순환 감지 |
| `UnusedAssumption` | warning | 결론에 기여하지 않는 `assume`/`suppose` 레이블 |

코드 문자열은 안정적이다 — 테스트와 미래 벤치마크 데이터셋이 이 이름에 의존한다.

### 15.3 `UndefinedSymbol` vs `MissingHypothesis`

두 코드는 유사해 보이지만 구분이 중요하다:

| 상황 | 코드 |
|---|---|
| `have h2: Q by mp h1 missing` — `missing` 자체가 없음 | `UndefinedSymbol` |
| `have h1: P by copy h2` 이후에 `assume h2: P` — h2는 나중에 정의됨 | `MissingHypothesis` |
| `conclude P by h2` — h2는 닫힌 서브 증명 내부에만 있음 | `MissingHypothesis` |

### 15.4 `CircularDependency`와 그래프 분석

`diagnose` 내부에서 `stele/proofgraph.py` 의 의존성 그래프를 자동으로 구성한다. 순환이 발견되면 `CircularDependency` 가 보고된다. 검증된 증명에서 순환은 발생하지 않아야 하므로, 이는 그래프 조작 도구를 위한 방어적 확인이다.

### 15.5 Python API

```python
from stele.parser import parse_theorem
from stele.diagnostics import diagnose_theorem, diagnose_graph, Diagnostic

thm = parse_theorem(open("examples/diag_undef.stele").read())
diags = diagnose_theorem(thm)
for d in diags:
    print(f"{d.severity.upper()} {d.code} line={d.line}: {d.message}")

# 합성 그래프에 대한 직접 진단 (테스트 등)
from stele.proofgraph import ProofGraph, ProofNode
g = ProofGraph(name="test", conclusion="_c")
g.nodes["a"] = ProofNode("a", "have", "P", None)
g.nodes["b"] = ProofNode("b", "have", "Q", None)
g.edges += [("a", "b"), ("b", "a")]
print(diagnose_graph(g))   # [Diagnostic(code='CircularDependency', ...)]
```

### 15.6 v1 한계

- **증명 수리 아님.** 진단은 문제를 위치추정할 뿐, 수정하지 않는다.
- **정리증명 아님.** 올바른 규칙이나 포뮬러를 제안하지 않는다.
- **파싱 실패 시:** 파스 오류 하나만 보고하고 구조적 진단은 수행하지 않는다.
- **줄 번호는 best-effort.** 그래프 수준 진단(`CircularDependency`, `UnusedAssumption` 일부)은 `line=None` 일 수 있다.
- **`MissingHypothesis` 스코프 누출 감지의 보수성:** 알 수 없는 규칙의 경우 쉬운 false negative가 발생할 수 있다. 스키마를 아는 논리의 일반 전제에 대해서는 정확히 감지한다.
- **커널 검증이 권위자.** 진단이 문제없다고 해도 커널이 거부하면 증명은 무효다.

---

## 16. 포뮬러 정의와 정렬/타입 기초 (`definition`)

### 16.1 포뮬러 정의 문법

포뮬러 약어(formula abbreviation)를 `theorem` 앞에 선언한다:

```
definition NAME := <formula>
```

예시:

```
definition MY_IMP := P -> Q
definition LEM_P := P or not P
definition CHAIN := MY_IMP -> P
```

정의는 포뮬러 수준 매크로다.

- **정의가 아닌 것:** 추론 규칙, 공리, 정리 증명. 증명 단계에서 명시적으로 사용될 때만 포뮬러로 참여한다.
- **확장:** 파서가 정의를 파싱한 뒤, 후속 theorem 본문의 포뮬러에서 정의 이름을 출현하면 즉시 본문으로 치환(expand)한다. 신뢰 커널은 항상 완전히 확장된 포뮬러만 본다.
- **재귀/순환:** 순환 정의는 확장 시 루프하지 않는다(사이클 보호 있음). v1에서는 순환 정의를 권장하지 않는다.

사용 예:

```
definition MY_IMP := P -> Q

theorem basic_def using intuitionistic_prop:
  assume h: MY_IMP          # h의 포뮬러는 P -> Q 로 확장됨
  assume hp: P
  have hq: Q by mp h hp
  conclude Q by hq
```

```
python -m stele.cli check examples/definition_basic.stele
# OK Proof verified: definition_basic   [logic: intuitionistic_prop]
```

### 16.2 포뮬러 정의의 한계 (v1)

| 항목 | 상태 |
|---|---|
| 포뮬러 매크로 | ✓ 지원 |
| 커널 내 공리로 사용 | ✗ (정의는 명시적 assume 없이 공리가 되지 않음) |
| 새로운 추론 규칙으로 사용 | ✗ |
| 항(term) 언어 지원 | ✗ (미래 계획) |
| 의존 타입 | ✗ (미래 계획) |
| 한정사(∀, ∃) | ✗ (로드맵 Phase 6) |
| 정의 간 순서 의존 | 선형 순서로 정의; 순환은 확장 중단 |

### 16.3 `UndefinedDefinition` 진단

```
WARNING UndefinedDefinition line=N: definition body references 'NAME' which is not a defined name in this file
```

정의 본문 안에서 **다른 정의 이름을 참조**했지만 그 정의가 파일에 없을 때 보고한다.

```
# 예: MISSING_DEF 가 정의되지 않았음
definition USE_MISSING := MISSING_DEF -> P
```

**v1 한계·보수성:**
- 단일 대문자 원자(`P`, `Q`, `R` 등)는 명제 변수로 보고 플래그하지 않는다.
- 다중 문자 대문자 식별자(`LEM_P`, `DNE` 등)를 정의 이름으로 취급한다.
- `PHI`, `PP` 같은 다중 문자 명제 변수는 오탐(false positive)이 날 수 있다 — v1 한계로 문서화.
- 진단은 정의 본문만 스캔한다; theorem 본문의 포뮬러는 스캔하지 않는다.
- 심각도: `warning` (휴리스틱 기반).

### 16.4 `InvalidTransition` 진단

```
ERROR InvalidTransition line=N: rule 'mp': premise 2 expected P, but 'h2' is P and R
```

스코프 내 레이블을 사용했지만 규칙 적용이 유효하지 않은 경우 보고한다.

- 전제가 올바른 형태가 아니거나(`mp` 의 두 번째 전제가 잘못된 경우)
- 주장한 결론이 규칙의 산출물과 다를 때

**구현:** `diagnose` 가 스코프 분석(`UndefinedSymbol`·`MissingHypothesis`)에서 오류를 찾지 못한 경우에만, 신뢰 커널을 실행해 `ProofError` 를 `InvalidTransition` 으로 분류한다. **커널은 여전히 유일한 검증 권위자다.** `InvalidTransition` 은 진단 레이어의 분류일 뿐이다.

```
python -m stele.cli diagnose examples/diagnostic_invalid_transition.stele
# ERROR InvalidTransition line=7: rule 'mp': premise 2 expected P, but 'h2' is P and R
```

**v1 한계:**
- 여러 규칙 오류가 있어도 첫 번째만 보고된다(커널이 첫 오류에서 중단).
- 스코프 오류가 있으면 `InvalidTransition` 패스는 실행되지 않는다.

### 16.5 `TypeMismatch` 진단 (기초 인프라, v1)

코드 문자열은 안정적이며 미래 데이터셋이 이에 의존할 수 있다.

```
ERROR TypeMismatch ...: sort mismatch: formula expected, got term
```

**v1 현재 상태:** 모든 Stele 표현식은 `Sort.FORMULA` 정렬이다. 항(term) 언어가 없으므로 표면 수준 타입 불일치는 발생하지 않는다.

`stele/types.py` 에 인프라가 있다:

```python
from stele.types import Sort, infer_sort, expand_defs

infer_sort(Var("P"))       # Sort.FORMULA
infer_sort(Op("and", ...)) # Sort.FORMULA
expand_defs(formula, defs_dict)  # 정의 치환 유틸리티
```

미래: 산술·대수적 항 언어 도입 시 `Sort.TERM` 이 실제 사용된다.

### 16.6 `diagnose` 커맨드 전체 코드 목록 (v1)

| 코드 | 심각도 | 의미 |
|---|---|---|
| `UndefinedSymbol` | error | 증명 어디에도 없는 레이블 참조 |
| `MissingHypothesis` | error | 스코프 밖 레이블 참조 |
| `UnsupportedConclusion` | error | conclude 포뮬러 불일치 |
| `CircularDependency` | error | 의존성 그래프 사이클 |
| `UnusedAssumption` | warning | 결론에 기여 안 하는 가정 |
| `UndefinedDefinition` | warning | 정의 본문의 미정의 이름 (v1 휴리스틱) |
| `InvalidTransition` | error | 스코프 유효하나 규칙 적용 실패 |
| `TypeMismatch` | error | 정렬 불일치 (v1 인프라만; 표면 트리거 없음) |

---

## 17. 벤치마크와 평가 하네스

### 17.1 벤치마크 디렉터리 구조

```
bench/
  labels.jsonl       ← 레이블 파일 (JSONL, 한 줄 = 한 태스크)
  tasks/             ← .stele 태스크 파일
    mp_valid_001.stele
    undefined_symbol_001.stele
    ...
  reports/
    latest.json      ← 평가 하네스를 실행해 생성된 결과 (하드코딩 금지)
```

v1 시드 벤치마크: 31개 태스크 (17개 valid, 10개 error, 4개 warning).

### 17.2 레이블 형식

`bench/labels.jsonl` 은 JSON Lines 포맷으로, 한 줄 = 한 태스크 레코드:

```jsonl
{"id":"mp_valid_001","path":"tasks/mp_valid_001.stele",
 "logic":"intuitionistic_prop","expected_valid":true,"expected_codes":[],
 "description":"basic modus ponens","tags":["valid","mp"]}

{"id":"undefined_symbol_001","path":"tasks/undefined_symbol_001.stele",
 "logic":"intuitionistic_prop","expected_valid":false,
 "expected_codes":["UndefinedSymbol"],"tags":["invalid","UndefinedSymbol"]}
```

| 필드 | 설명 |
|---|---|
| `id` | 안정적인 태스크 식별자 (파일명과 일치) |
| `path` | `bench/` 기준 상대 경로 |
| `logic` | 검증에 사용할 논리 이름 |
| `expected_valid` | `check`가 통과해야 하면 `true`, 실패해야 하면 `false` |
| `expected_codes` | `diagnose`가 반환해야 할 코드 목록 (valid 태스크는 `[]`) |
| `description` | (선택) 태스크 설명 |
| `tags` | (선택) 분류 태그 |

**주의:** `expected_valid = true` + `expected_codes = ["UnusedAssumption"]` 조합이 가능하다. `check`는 통과하지만 `diagnose`는 경고를 반환할 수 있다.

### 17.3 평가 실행

```
python -m stele.eval bench \
  --labels bench/labels.jsonl \
  --tasks bench \
  --report bench/reports/latest.json
```

| 옵션 | 설명 |
|---|---|
| `--labels` | JSONL 레이블 파일 (기본: `bench/labels.jsonl`) |
| `--tasks` | 태스크 루트 디렉터리 (기본: `bench`) |
| `--report` | JSON 리포트 출력 경로 (선택) |
| `-v` | 태스크별 PASS/FAIL 출력 |

### 17.4 측정 지표

하네스는 다음을 계산한다:

**유효성 정확도 (validity_accuracy)**
- 전체 태스크 중 `predicted_valid == expected_valid` 비율

**진단 코드 정합율 (exact_match_rate)**
- 전체 태스크 중 `set(predicted_codes) == set(expected_codes)` 비율

**진단 코드 P / R / F1**

| 지표 | 계산 방법 |
|---|---|
| 코드별 precision | `TP / (TP + FP)` (분모=0이면 0.0) |
| 코드별 recall | `TP / (TP + FN)` (분모=0이면 0.0) |
| 코드별 F1 | `2·P·R / (P+R)` |
| micro P/R/F1 | 모든 코드의 TP/FP/FN 합산 후 계산 |
| macro P/R/F1 | `support > 0`인 코드의 평균 |

TP = 예측과 기대 모두에 코드 있음, FP = 예측에만 있음, FN = 기대에만 있음.

### 17.5 새 벤치마크 태스크 추가 방법

1. `bench/tasks/<task_id>.stele` 에 증명 파일 작성
2. `bench/labels.jsonl` 에 레코드 추가
3. 하네스 실행으로 레이블 확인:
   ```
   python -m stele.eval bench --labels bench/labels.jsonl --tasks bench -v
   ```
4. 모든 태스크가 PASS이면 커밋

**정직성 규칙:** `expected_valid`와 `expected_codes`는 구현이 실제로 생성하는 값이어야 한다. 바람직한 값이 아니라 측정된 값을 기록하라.

### 17.6 리포트 결정론성

`bench/reports/latest.json`은 하네스 실행으로 생성한다:
- 태스크 ID로 정렬
- 부동소수점 값은 소수 4자리 반올림
- 타임스탬프·절대경로 없음

버전 관리에 포함하면 측정 수치의 변화를 git diff로 추적할 수 있다.

---

## 18. 한계와 다음 단계

- 현재는 **명제논리 단편**이다. 1차 논리(한정사)는 미구현 — 로드맵 Phase 6.
- 상대성은 *규칙 가용성* 수준에서 작동한다(§7의 정직한 한계).
- 규칙 건전성 보고(§9)는 비방출 규칙만 다루는 v1이다. 방출 규칙의 의미론적 건전성은 추후 크립키 의미론으로 확장 예정.
- 전체 설계·단계: `stele_redesign.md`. 결정·근거: `DECISIONS.md`.
