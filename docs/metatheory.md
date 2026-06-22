# Stele — 메타이론 주장과 현황

이 문서는 Stele 증명항 코어(`stele.core`)의 메타이론적 성질을 기록한다.

**중요한 정직성 원칙:**
- 이 문서에 기재된 주장은 Python 테스트로 형식 증명되지 않는다.
- 각 항목의 상태(Status)에 "검증됨"·"증명됨"이라고 적힌 것은
  **기계 검증(machine-checked proof)**을 의미하지 않는다.
- 회귀 테스트와 속성 기반 테스트는 구현 버그를 포착하는 장치이지,
  수학적 정리의 증명이 아니다.
- 미래의 Lean/Coq/Agda 등 형식 증명 보조기 통합 전까지,
  "증명됨"이 아닌 "스케치"·"회귀 테스트로 지원됨" 등의 수식어를 사용한다.

관련 문서:
- 형식 문법·타입 규칙·환원 규칙: [`docs/semantics.md`](semantics.md)
- 증명항 API 및 예시: [`docs/proof-terms.md`](proof-terms.md)

---

## 1. 용어 정의

이 문서에서 사용하는 상태 수식어:

| 수식어 | 의미 |
|--------|------|
| **형식 주장(formal claim)** | 수학적으로 진술된 성질; 증명 여부는 별도 표시 |
| **증명 스케치(proof sketch)** | 비형식적 논거; 표준 메타이론을 인용하거나 구조적 이유를 제시 |
| **구현 불변(implementation invariant)** | 코드·아키텍처가 유지하는 구조적 성질 |
| **회귀 테스트(regression test)** | 특정 사례에 대해 성질을 확인하는 단위 테스트 |
| **속성 기반 테스트(property-based test)** | 생성된 입력에 대해 성질을 확인하는 Hypothesis 테스트 |

이 중 어떤 것도 형식 증명 보조기(Lean/Coq/Agda)의 기계 검증을 의미하지 않는다.

---

## 2. 핵심 메타이론 주장 요약

| # | 이름 | 상태 |
|---|------|------|
| 1 | 정교화 건전성 | 회귀 테스트로 지원됨 (기계 증명 없음) |
| 2 | 주체 환원 (타입 보존) | 증명 스케치 + 회귀/속성 테스트 |
| 3 | 정규화 | 표준 메타정리 인용; 연료 제한 구현 |
| 4 | 국소 합류성 / 합류성 | 연기 테스트 확인; 완전한 증명 없음 |
| 5 | 코어 일관성 | 증명 스케치 + 생성 테스트 |
| 6 | 고전 배제 | 구현 불변 + 회귀 테스트 |
| 7 | 행렬 분리 | 아키텍처 불변 + 정적 임포트 검사 |
| FOL-1 | ForallIntro/Elim 주체 환원 | 증명 스케치 + 회귀 테스트 |
| FOL-2 | ExistsElim 신선도 시행 | 회귀 테스트 |

**추가 구현 불변 (섹션 5):**

| 불변 | 위치 |
|------|------|
| 이름 있는 API 유지 | `debruijn.py` — 기존 API 비변경 |
| α-동치 결정 | `alpha_equiv` via de Bruijn (증명 변수만) |
| de Bruijn shift/subst 포착 회피 | 구조적 shift 패턴 |
| 1차 논리 객체 바인더 이름 유지 | `DBForallIntro`, `DBExistsElim` — obj_var 이름 보존 |

---

## 3. 상세 주장

---

### 주장 1: 정교화 건전성 (Elaboration Soundness)

**형식 주장.**
지원되는 직관주의 증명 스크립트가 커널 검증을 통과하고 정교화 결과로 항 `t`를 생성하면,
컨텍스트 `Γ`(스크립트의 `assume` 선언들)에 대해 `Γ ⊢ t : A`가 성립한다.
여기서 `A`는 `conclude` 절의 공식이다.

더 정밀히: `crosscheck_theorem`이 반환하는 `CrossCheckResult.ok == True`이면,
커널·정교화·타입 검사 세 단계가 모두 성공한 것이다.

**증명 스케치.**
정교화(`stele.elaborate._elaborate_rule`)는 각 증명 규칙에 대해 대응하는 타입 생성자를 구성한다.
각 생성자는 해당 타입 규칙(섹션 4 of `docs/semantics.md`)의 결론을 만족하도록 설계되었다.
`crosscheck_theorem`의 3단계는 스크립트 수준의 올바름(커널)과
항 수준의 올바름(타입 검사)을 모두 확인하므로, 두 레이어의 일관성을 체계적으로 검사한다.
단, 이 논거는 구현 코드의 정확성에 의존하며, 코드 자체의 메타 검증이 아니다.

**구현 훅.**
`stele.elaborate.crosscheck_theorem`,
`stele.elaborate._elaborate_rule`,
`stele.core.typing.check`

**테스트 커버리지.**
- `tests/test_elaboration.py` — 지원 규칙 13개 각각에 대한 개별 정교화 테스트
- `tests/test_elaboration.py::TestCrosscheckAgreement` — 예시 정리들에 대한 상호 검증 파라미터 테스트
- `tests/test_proof_term_properties.py::test_generated_terms_typecheck` (속성 기반, Hypothesis 있을 때)

**한계.**
- 규칙 구현 자체의 오류는 회귀 테스트 외의 방법으로 포착하기 어렵다.
- 미지원 규칙(고전 원리 등)에 대해서는 이 주장이 성립하지 않는다.
- 특수 케이스(예: 중첩된 `or_elim`, 복잡한 `neg_intro`) 커버리지가 충분하지 않을 수 있다.

---

### 주장 2: 주체 환원 (Subject Reduction / Type Preservation)

**형식 주장.**
컨텍스트 `Γ`에서 `Γ ⊢ t : A`이고 `step(t) = t'`이면, `Γ ⊢ t' : A`이다.

**증명 스케치.**
각 β-환원 규칙에 대해 개별적으로 확인한다.

- **β_imp:** `Γ ⊢ App(Lam(x, A, body), arg) : B`이려면
  `Γ, x:A ⊢ body : B`이고 `Γ ⊢ arg : A`여야 한다.
  표준 치환 보조 정리(Substitution Lemma): `Γ ⊢ body[arg/x] : B`.
  따라서 β_imp는 타입 B를 보존한다.

- **β_fst:** `Γ ⊢ Fst(Pair(a, b)) : A`이려면 `Γ ⊢ Pair(a, b) : A and B`이고
  `Γ ⊢ a : A`여야 한다. 따라서 β_fst는 타입 A를 보존한다.

- **β_snd:** 대칭적; 타입 B를 보존한다.

- **β_case_l:** `Γ ⊢ Case(Inl(a, _), x, lb, y, rb) : C`이려면
  `Γ ⊢ a : A`이고 `Γ, x:A ⊢ lb : C`여야 한다.
  치환 보조 정리에 의해 `Γ ⊢ lb[a/x] : C`.

- **β_case_r:** 대칭적; `rb[b/y] : C`.

구조적 환원(서브텀 환원)은 귀납가설에 의해 타입을 보존한다.

**구현 훅.**
`stele.core.reduce.step`, `stele.core.typing.infer`, `stele.core.reduce.substitute`

**테스트 커버리지.**
- `tests/test_reduction.py::TestSubjectReduction` — 5개 β-규칙 각각에 대한 회귀 테스트
- `tests/test_reduction.py::TestSubjectReduction::test_type_after_multi_step_stays_same` — 다단계 환원 후 타입 보존
- `tests/test_proof_term_properties.py::test_subject_reduction_property` (속성 기반, Hypothesis 있을 때)
- `tests/test_proof_term_properties.py::test_normalization_preserves_type` (속성 기반)

**한계.**
- 치환 보조 정리 자체는 코드가 아닌 비형식 논거에 의존한다.
- 귀납 구조는 기계 검증되지 않았다.

---

### 주장 3: 정규화 (Normalization)

**형식 주장.**
직관주의 단순 타입 λ-계산(simply typed intuitionistic propositional fragment)의
모든 잘 타입된(well-typed) 닫힌(closed) 항은 β-정규형(β-normal form)을 가진다.

**증명 스케치.**
이는 직관주의 단순 타입 λ-계산의 **강한 정규화(strong normalization)** 표준 메타정리이다.
증명 개략:
1. 크기 측도(measure): 각 항에 자연수 크기를 부여한다.
2. 각 β-환원 규칙은 크기를 감소시킨다.
3. 잘 조직된(well-founded) 수열은 종료한다.

이 문서에서의 "증명 스케치"는 교과서적 논거를 인용하는 것이지,
Python 코드 내에서 기계 검증된 것이 아니다.

**구현 훅.**
`stele.core.reduce.normalize(term, fuel=1000)` —
`fuel` 매개변수는 구현 버그에 대한 안전장치이지 종료 보증 수단이 아니다.

**테스트 커버리지.**
- `tests/test_reduction.py::TestNormalize` — 여러 항에 대한 정규화 테스트
- `tests/test_reduction.py::TestNormalize::test_is_normal_after_normalize` — 정규화 후 `is_normal` 확인
- `tests/test_reduction.py::TestNormalize::test_idempotent` — 정규화의 멱등성(idempotence)
- `tests/test_proof_term_properties.py::test_normalization_reaches_normal_form` (속성 기반)
- `tests/test_proof_term_properties.py::test_idempotence_of_normalization` (속성 기반)

**한계.**
- `fuel` 한계를 초과하면 `ReductionError`가 발생한다. 이는 종료 실패가 아닌 구현 한계다.
- 열린(open) 항(free variables가 있는 항)도 정규화되나, 닫힌 항에 대한 강한 정규화 보증이 더 직접적이다.
- `normalize` 자체가 종료함을 코드 내에서 증명하지 않는다.

---

### 주장 4: 국소 합류성 / 합류성 (Local Confluence / Confluence)

**형식 주장.**
β-환원 관계(`step`을 단계로 하는 그래프)는 합류적(confluent)이다:
`t ↠ t₁`이고 `t ↠ t₂`이면, `t₁ ↠ t*`이고 `t₂ ↠ t*`인 공통 항 `t*`가 존재한다.
따라서 정규형은 (존재한다면) 유일하다.

**증명 스케치.**
단순 타입 λ-계산은 **처치-로서 정리(Church-Rosser theorem)**에 의해 합류적이다.
핵심 논거:
1. β-환원의 병렬 환원(parallel reduction)을 정의한다.
2. 병렬 환원의 마름모 성질(diamond property)을 증명한다.
3. 마름모 성질에서 합류성을 유도한다.

이 문서에서 언급되는 "증명 스케치"는 표준 교과서적 논거를 인용한 것이다.

**구현 훅.**
`stele.core.reduce.step` / `normalize` — 결정론적 전략(최좌-최외)은
합류적 시스템에서 정규형에 도달함을 보장한다.

**테스트 커버리지.**
- `tests/test_reduction.py::TestConfluence` — 4개의 연기(smoke) 테스트: 두 환원 순서가 동일 정규형에 도달하는 것을 특정 사례로 확인
- `tests/test_proof_term_properties.py::test_normalization_reaches_normal_form` — 생성 항에 대해 정규형 도달 확인 (간접적)

**한계.**
- 연기 테스트는 선택된 소수 사례만 확인한다.
- 처치-로서 정리의 전체 증명이 구현 내에 없다.
- 두 독립적 환원 경로를 체계적으로 열거하는 테스트가 없다.

---

### 주장 5: 코어 일관성 (Core Consistency)

**형식 주장.**
빈 컨텍스트에서 타입 `false`를 갖는 닫힌 항은 직관주의 단순 타입 계산에 존재하지 않는다.
즉, `{} ⊢ t : false`를 만족하는 항 `t`는 존재하지 않는다.

**증명 스케치.**
단순 타입 직관주의 계산의 일관성은 강한 정규화와 표준형(canonical form) 분석으로 유도된다.

1. **강한 정규화:** 모든 잘 타입된 항은 정규형에 도달한다.
2. **표준형 분석:** 타입 `false`의 닫힌 정규형은 존재하지 않는다.
   - `false`의 제거 규칙(Abort)은 도입 형식을 요구한다.
   - `false`의 도입 규칙은 없다.
   - 따라서 `false`를 증명하려면 이미 `false`를 갖고 있어야 한다(순환).

결론: 빈 컨텍스트에서 `false`를 가정 없이 증명할 수 없다.

**구현 훅.**
`stele.core.typing.infer` — 빈 컨텍스트에서 `Abort(TVar("x"), ...)` 호출 시 `TypingError` (x가 바인딩되지 않음).

**테스트 커버리지.**
- `tests/test_reduction.py::TestConsistency` — 5개 테스트:
  - 도입 형식으로만 구성된 닫힌 항들이 `false` 타입을 갖지 않음
  - `Abort`는 `false` 증명을 요구함
  - 정규화가 비-`false` 타입을 `false`로 바꾸지 않음
- `tests/test_proof_term_properties.py::test_no_closed_false_term_from_intro_rules` (속성 기반)

**한계.**
- 소수의 표준 생성자 조합만 테스트한다.
- 비표준 Python 조작(직접 데이터 구조 변조 등)에 대해서는 보증하지 않는다.
- 열거 테스트가 아닌 구조적 논거에 의존한다.

---

### 주장 6: 고전 배제 (Classical Exclusion)

**형식 주장.**
고전 원리 `dne`, `lem`, `pbc`는 증명항 코어 v1의 생성자 목록에 포함되지 않는다.

**증명 스케치.**
이는 형식 증명이 아닌 **설계 결정**이다.
고전 증명항을 지원하려면 제어 연산자(callcc 등) 또는 이중부정 번역이 필요하다.
v1에서는 이를 구현하지 않는다. 이 결정은 `stele.elaborate._CLASSICAL_RULES` frozenset에 반영된다.

**구현 훅.**
`stele.elaborate._CLASSICAL_RULES = frozenset({"dne", "lem", "pbc"})` —
이 규칙들에 대해 `ElaborationError`를 발생시킨다.

**테스트 커버리지.**
- `tests/test_elaboration.py::TestClassicalRejection` — `dne`, `lem`, `pbc`가 `ElaborationError`를 발생시킴을 확인
- `tests/test_proof_terms.py::TestTermConstructors` — 고전 생성자가 없음을 암시적으로 확인

**한계.**
이 주장은 "고전 증명항이 존재하지 않는다"는 논리적 불가능성이 아니라,
"우리가 v1에서 구현하지 않았다"는 설계 결정이다.

---

### 주장 7: 행렬 분리 (Matrix Separation)

**형식 주장.**
K3 / LP / boolean 행렬 의미론(`stele.matrix`, `stele.world`)은
증명항 계산법(`stele.core`)과 분리된다.
두 시스템은 서로를 임포트하지 않는다.

- `stele.kernel`은 `stele.core`를 임포트하지 않는다.
- `stele.core`는 `stele.kernel`을 임포트하지 않는다.
- `stele.kernel`은 `stele.matrix`를 임포트하지 않는다.
- `stele.matrix`는 `stele.kernel`을 임포트하지 않는다.

**증명 스케치.**
이는 아키텍처 불변이다. 임포트 의존성은 정적으로 검사 가능하다.

**구현 훅.**
각 모듈의 import 문 + 정적 검사 테스트.

**테스트 커버리지.**
- `tests/test_regression_invariants.py` — `kernel`↔`matrix` 분리 + `kernel`↔`core` 분리 정적 검사
- `tests/test_proof_terms.py::TestKernelInvariance` — `kernel.py`가 `core`를 임포트하지 않음

**한계.**
정적 임포트 검사는 동적 임포트(`importlib.import_module(...)`)를 놓칠 수 있다.
현재 구현에서 동적 임포트는 없다.

---

## 4. 속성 기반 테스트 (Property-Based Tests)

`tests/test_proof_term_properties.py`는 Hypothesis를 사용한 선택적 속성 기반 테스트를 포함한다.

**실행 방법:**
```bash
# Hypothesis 설치 (일회)
pip install -r requirements-dev.txt

# 속성 기반 테스트 실행
python -m pytest tests/test_proof_term_properties.py -v

# 전체 테스트 실행 (Hypothesis 없이도 통과)
python -m pytest -q
```

**포함된 속성:**

| 속성 | 설명 |
|------|------|
| `test_generated_terms_typecheck` | 타입-지향 생성기로 만든 항이 타입 검사를 통과함 |
| `test_subject_reduction_property` | 환원 가능한 항: `step(t)` 후 타입이 보존됨 |
| `test_normalization_preserves_type` | `normalize(t)` 후 타입이 보존됨 |
| `test_normalization_reaches_normal_form` | `is_normal(normalize(t))` |
| `test_idempotence_of_normalization` | `normalize(normalize(t)) == normalize(t)` |
| `test_substitution_lemma` | `Γ,x:A ⊢ body : B`이고 `Γ ⊢ arg : A`이면 `Γ ⊢ body[arg/x] : B` |
| `test_no_closed_false_term_from_intro_rules` | 도입 형식만으로 `false` 타입을 얻을 수 없음 |

**발견과 기계 증명의 차이:**
이 테스트들은 많은 입력에서 성질이 성립함을 확인하지만,
모든 가능한 입력에서 성립함을 수학적으로 보증하지 않는다.
테스트 통과는 구현의 신뢰도를 높이는 증거이며, 메타정리의 증명이 아니다.

---

## 5. 바인더 표현 불변 (de Bruijn 층)

`stele.core.debruijn` 모듈은 이름 있는 증명항 바인더의 내부 표현 계층이다.

### 5.1 구현 불변

| 불변 | 상태 |
|------|------|
| 이름 있는 API 유지: `TVar/Lam/App/…` API는 변경되지 않음 | 구현 불변; 회귀 테스트로 지원됨 |
| `to_debruijn(t)` 결정성: 동일 항에 동일 de Bruijn 결과 | 구현 불변 (순수 함수) |
| α-동치 결정: `alpha_equiv(t1, t2)` ↔ `to_debruijn(t1) == to_debruijn(t2)` | 구현 불변 + 회귀 테스트 |
| 그림자(shadowing) 처리: 내부 바인더가 인덱스 0을 가짐 | 회귀 테스트로 지원됨 |
| `shift` 단조성: `amount >= 0`이면 자유 인덱스 감소 없음 | 회귀 테스트로 지원됨 |
| `subst` 포착 회피: `shift(replacement, 1, 0)` 패턴으로 구조적 보증 | 증명 스케치 + 회귀 테스트 |

### 5.2 `from_debruijn` 제한

`DBCase`는 분기 변수 타입을 저장하지 않아 완전한 역변환을 지원하지 않는다.
α-동치는 `to_debruijn`만으로 결정 가능하므로 `from_debruijn`은 완전한 역함수가 아니어도 무방하다.

### 5.3 1차 논리 바인더 de Bruijn 처리 (v2 현황)

1차 논리 단편이 추가되어 두 종류의 바인더가 공존한다:
- **증명 바인더** (v1, 완전 구현): `Lam`, `Case` 분기, `ExistsElim.proof_var` — DB 인덱스 사용
- **객체 바인더** (v2, 이름 유지): `ForallIntro.obj_var`, `ExistsElim.obj_var` — 이름 그대로 유지

`DBForallIntro`, `DBForallElim`, `DBExistsIntro`, `DBExistsElim`이 추가되었으나,
객체 변수 이름은 de Bruijn 인덱스로 변환되지 않는다.
`alpha_equiv`는 증명 변수 재명명에는 둔감하지만 객체 변수 재명명에는 민감하다.
공식 수준의 α-동치는 `formula_alpha_equiv_fol`로 별도 확인한다.

두 종류 모두 DB 인덱스로 처리하는 `to_debruijn_fol`은 v3 예정이다.

---

## 6. 1차 논리 단편 주장

| # | 이름 | 상태 |
|---|------|------|
| FOL-1 | ForallIntro/Elim 주체 환원 | 증명 스케치 + 회귀 테스트 |
| FOL-2 | ExistsIntro/Elim 주체 환원 | 회귀 테스트로 지원됨 |
| FOL-3 | β_forall 타입 보존 | 회귀 테스트: `test_fol.py::test_beta_forall_subject_reduction` |
| FOL-4 | subst_obj 포착 회피 | 회귀 테스트: `test_fol.py::TestSubstObj::test_forall_capture_avoidance` |
| FOL-5 | 신선도 조건 시행 | 회귀 테스트: `test_fol.py::TestForallTyping::test_forall_intro_freshness_violation` |

### FOL-1: ForallIntro/Elim 주체 환원

**형식 주장.**
`Γ ⊢ t : forall x. A`이고 `a`가 객체 항이면,
`β_forall`: `ForallElim(ForallIntro(x, body), a)` → `subst_obj_in_term(body, x, a)` 결과의 타입은
`Γ ⊢ subst_obj_in_term(body, x, a) : A[a/x]`이다.

**증명 스케치.**
`ForallElim`의 타입은 `subst_obj(fn_type.body, fn_type.var, obj_term)`이다.
`ForallIntro`의 타입은 `Forall(x, body_type)`이다.
따라서 β 환원 전: `subst_obj(Forall(x, body_type).body, x, a)` = `subst_obj(body_type, x, a)`.
환원 결과의 타입: `infer(ctx, subst_obj_in_term(body, x, a))` = `subst_obj(body_type, x, a)`.
일치함(단, 구현 정확성 가정).

**테스트 커버리지.**
`tests/test_fol.py::TestFOLReduction::test_beta_forall_subject_reduction`

### FOL-2: ExistsElim 신선도 시행

**형식 주장.**
`ExistsElim(e, x, h, body)` 타입 검사 시, 결과 타입 `C`에 `x`가 자유로이 나타나면
`TypingError`를 발생시킨다.

**테스트 커버리지.**
`tests/test_fol.py::TestExistsTyping::test_exists_elim_freshness_violation`

---

## 7. 알려진 미검증 영역

다음은 현재 테스트로 충분히 다루어지지 않은 영역이다.

1. **동적 임포트 검사:** `importlib`를 통한 런타임 임포트는 정적 검사에서 놓인다.
2. **β_case_l / β_case_r 치환 정확성:** 복잡한 바인딩 중첩 케이스에 대한 속성 테스트가 없다.
3. **포착 회피 치환 완전성:** `substitute`의 알파 재명명이 모든 경우를 올바르게 처리하는지
   완전히 열거된 테스트가 없다(일부 케이스만 회귀 테스트로 확인됨).
4. **열린 항(open terms)의 정규화:** 자유 변수가 있는 항도 잘 동작하나,
   이에 대한 타입 보존 속성 테스트가 충분하지 않다.
5. **η-동치:** η-환원이 없으므로 η-동치 기반의 성질은 미확인이다.
6. **de Bruijn 치환 vs. 이름 있는 치환 완전 일치:** 현재 대표 사례 비교 테스트가 있으나,
   모든 입력에서 두 치환이 동치임을 속성 기반으로 확인하지 않았다.
7. **`from_debruijn` Case 지원:** DBCase의 분기 변수 타입 정보 없이는 역변환 불가.
   타입 컨텍스트를 추가 인자로 받는 확장은 미구현이다.
8. **1차 논리 β_exists 주체 환원:** `beta_exists` 환원 전후 타입 보존에 대한 속성 테스트 없음.
9. **객체 바인더 de Bruijn 인덱스화:** `ForallIntro`/`ExistsElim.obj_var`는 이름 유지;
   이를 DB 인덱스로 처리하는 `to_debruijn_fol`은 미구현.
10. **subst_obj 포착 회피 완전성:** 현재 대표 사례 테스트만 있음; 속성 기반 확인 없음.
