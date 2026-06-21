# Stele — Development Context (Claude Code Handoff)

이 문서는 Stele Logic System을 Claude Code로 이어받기 위한 압축 핸드오프다.
보강 문서: 설계 `stele_redesign.md`, 언어 `GUIDE.md`, 결정 `DECISIONS.md`, 결과 `RESULTS.md`, 운영 규칙 `CLAUDE.md`.

런타임: Python 3.10+, **외부 의존성 0** (테스트만 `pytest`).

---

## 1. Stele는 무엇이고, 무엇이 아닌가

- **이다:** 사람이 읽는 형식언어(Stele-Light)로 자연연역 증명을 적으면, 트러스티드 커널이 각 단계를 검증하는 **증명검증기(proof checker)**. 핵심은 **logical framework** — 커널은 어떤 논리에도 헌신하지 않고, 로드된 *논리 정의(규칙 집합 = 공리 함수 A(S))*에 상대적으로 검사한다. 고전논리는 여러 세계 중 하나일 뿐. 배경 철학(유리학: 국소적 진리·논리적 다원주의)을 실행 가능하게 만든 것.
- **아니다:** 정리증명기(prover)가 아니다 — 증명을 *탐색*하지 않는다. 사용자가 단계를 명시하고 커널은 옳은지만 판정한다. SMT/SAT 솔버도, 단일 고전 기초(Lean/Coq류)도 아니다.

---

## 2. 이미 구현된 것 (215개 테스트 통과)

```
stele/
  ast.py     uniform Formula: Var, Op(연결사 무지) + pretty()
  proof.py   frozen dataclass: Assume/Have/Suppose/Conclude/Theorem (+line) + MatrixDirective
  parser.py  직접 구현 토크나이저 + 재귀하강 파서(의존성 0) + parse_matrix_file()
  logic.py   RuleSchema, Logic, MatrixLogic; 내장 논리 5종(intuitionistic/classical/K3/LP/boolean)
  kernel.py  ★신뢰 코어: match()(1차 구문) + instantiate() + 증명트리 검사 + discharge
  matrix.py  다치 의미론: Matrix, K3/LP/boolean, evaluate/is_tautology/entails/negation_fixpoints
             + SoundnessResult + rule_soundness()
  world.py   World(matrix_name, axioms) frozen dataclass
             + status(φ, world) → PROVABLE/REFUTABLE/BOTH/INDEPENDENT
             + lattice_status(φ, worlds) — 교차 세계 상태 질의
  cli.py     check / soundness / lattice / demos
  web.py     로컬 웹 UI 서버(stdlib http.server)
  webapp/index.html  단일 파일 SPA(편집기 + 세계 토글 + 진리표)
examples/  proof: dne, dne_law, valid_*, invalid_*, peirce, lem, neg_intro, or_elim, ...
           matrix: matrix_k3.stele, matrix_lp.stele, matrix_boolean.stele
           world: world_ch_style.py
tests/     parser / kernel_valid / kernel_invalid / relativism / matrix
           conclusion_directed / new_rules / generalized_discharge / discharge_rules
           classical_principles / matrix_surface / rule_soundness / world / world_lattice
```

- **proof 모드 공통 규칙:**
  `copy`, `mp`(→E), `imp_intro`(→I, 방출), `and_intro`, `and_elim_left`, `and_elim_right`,
  `neg_elim`(¬E: A, ¬A⊢⊥), `ex_falso`(⊥E: ⊥⊢A),
  `or_intro_left`, `or_intro_right`,
  `neg_intro`(¬I: [A]…⊥⊢¬A, 방출), `or_elim`(∨E: A∨B,[A]…C,[B]…C⊢C, 방출 2개).
- **고전 전용 규칙:** `dne`(¬¬A⊢A), `lem`(⊢A∨¬A), `pbc`([¬A]…⊥⊢A, 방출).
  `classical_prop = intuitionistic_prop + {dne, lem, pbc}`.
- **matrix 모드:** K3/LP/boolean 행렬을 `--logic K3` 등으로 선택. `.stele` 파일에서
  `evaluate`, `tautology?`, `entails ... |- ...`, `fixpoint not`, `liar` 지시문 사용 가능.
- **규칙 건전성:** `python -m stele.cli soundness --logic L --matrix M` 으로
  proof 논리 L의 각 비방출 규칙이 행렬 M에서 지정값을 보존하는지 보고.
- **의미론적 세계:** `World(matrix_name, axioms)` + `status(φ, w)` —
  φ가 세계의 공리 아래 귀결(`PROVABLE`), 부정만 귀결(`REFUTABLE`),
  둘 다 귀결(`BOTH`, 초일관 LP), 둘 다 아님(`INDEPENDENT`).
  *PROVABLE은 행렬 의미론적 귀결이며 증명 탐색이 아니다.*
- **세계 격자 데모:** `python -m stele.cli lattice <φ>` — CH-스타일 명제 독립성 패턴
  (Γ:INDEPENDENT → Γ+φ:PROVABLE, Γ+¬φ:REFUTABLE). 집합론적 강제법 아님.
- **상대성 데모:** 동일 증명이 `classical_prop`에서 검증, `intuitionistic_prop`에서 거부(`dne`/`lem`/`pbc` 미가용). 웹 토글로 즉시 뒤집힘.

---

## 3. 아키텍처와 신뢰 경계

- **신뢰 경계 = `stele/kernel.py` 뿐.** `match`+`instantiate`+트리검사 = de Bruijn 기준(손으로 감사 가능). 파서·CLI·web·LLM·증명탐색은 전부 **untrusted**이며 커널이 재검사한다.
- **커널은 규칙을 모른다.** 규칙은 `logic.py`의 `RuleSchema` *데이터*. 새 논리 = 새 규칙 집합, 커널 수정 아님.
- **두 검사 모드:** proof 모드(`kernel.py`, ⊢)와 matrix 모드(`matrix.py`, ⊨)는 별개. 논리의 `semantics` 태그로 구분(개념상).
- **메타논리는 고정·최소·구성적.** 커널 매칭은 순수 구문적·결정 가능해야 하며, 어떤 대상 논리의 *의미*에도 호출 금지 — 그래야 고전적 가정이 직관 세계로 누출되지 않는다.

---

## 4. 이 대화에서 내린 핵심 설계 결정

- **커널 = logical framework**(유리학 실행형). 초일관 세계 = ECQ(폭발) 규칙을 뺀 논리 파일; 다치 세계 = matrix 모드. 고전논리는 한 파일로 격하.
- **무한후퇴는 메타논리에서 멈춘다.** 절대성을 *제거*하는 게 아니라 메타층으로 *이전*·최소화(타르스키 위계). "보편 논리는 없다"는 강한 주장은 자기반박적이므로, 입장은 "최소 메타논리 위 다원적 대상논리".
- **"진리 위상"의 엄밀형 = 크립키/헤이팅/토포스 의미론.** 위상공간 열린집합 = 헤이팅 대수이며, 그 위 국소적 진리의 논리는 *직관논리*. 따라서 직관논리가 "국소성의 논리"로서 특권적.
- **언어:** 지금 Python(반복 속도·실증·의존성 0). 커널 경화는 이후 **Rust/OCaml**(sum type + 망라적 패턴매칭 → 구성적 정확성). 비채택: C++/Java/Go/JS, Lean self-host(다원주의와 충돌).
- **파서는 직접 구현**(lark 미사용) — 신뢰 경로·이식성.
- **상대성의 정직한 한계:** 검사기가 보이는 건 *고전 전용 규칙에 의존하는 증명이 직관 세계에서 타입검사 실패*. 완전한 비도출성은 메타 주장이며 의미론(matrix/크립키)의 몫.
- **K3/LP 표는 유리학개론 pp.4–5와 정확히 일치**(검증: →(I,F)=I, →(F,I)=T). LP designated {T,B}.

---

## 5. 보존해야 할 형식논리 제약 (불변)

1. 커널 매칭은 **순수 구문적·결정 가능**; 의미론 호출 금지. 메타논리 ≤ 모든 대상 논리(최소·구성적 유지).
2. 규칙은 데이터. 새 논리는 규칙 추가이지 커널 변경이 아니다.
3. **도출가능성(⊢, 결정 가능, 커널)** 과 **세계의 건전성/무모순성(메타, 종종 결정 불가)** 을 분리. 커널은 세계가 무모순/건전하다고 **결코 주장하지 않는다**.
4. **⊢ 와 ⊨ 를 혼동하지 말 것**(proof vs matrix). 비도출성을 과장하지 말 것.
5. K3/LP 진리표는 매니페스토와 일치 유지(`test_k3_imp_table_matches_manifesto`가 →(I,F)=I, →(F,I)=T 고정). K3 designated{T}, LP designated{T,B}. 변경 시 테스트로 재잠금.
6. **방출/스코프:** `suppose` 블록 내부 라벨은 블록이 닫히면 스코프를 벗어난다. 오직 `imp_intro`만 그 블록을 참조 가능(`test_kernel_invalid::test_discharged_hypothesis_out_of_scope` 보장).
7. `classical_prop = intuitionistic_prop + dne` *정확히*. 직관논리에 LEM/DNE를 몰래 추가하지 말 것.

---

## 6. 알려진 한계 / TODO

- **명제논리 단편**만. 1차 논리(한정사·치환) 없음.
- **상대성 = 규칙 가용성 수준**(의미론적 비도출성 자체를 커널이 확립하지 않음). 완전한 비도출성 증명은 matrix/크립키 의미론의 몫.
- `world.py`의 PROVABLE은 행렬 의미론적 귀결이며 증명 탐색이 아니다. 두 가지를 혼동하지 말 것.
- CH-스타일 독립성 패턴은 명제 수준의 장난감 시연이며 집합론적 강제법이 아니다.
- 구조 규칙 정책(약화·축약 제거 → 선형/관련성/초일관 세계) 미구현.
- 세계 격자 전체(세계들 사이의 포함·비교 관계) 미구현(로드맵).
- Lean 4 export, LLM 튜터 미구현.
- pretty-printer 괄호는 근사적(메시지용; 왕복 정규형 아님).
- 증명 탐색/자동화 없음(설계상 — 검사기≠증명기).
- 웹 UI는 단일 로컬 사용자(영속성·계정 없음).

---

## 7. 권장 다음 작업 (우선순위 순)

1~3은 완료됨 (명제 규칙 전체, matrix 표면 문법, 세계/격자 데모). 이후:

1. **구조 규칙 정책** — 약화/축약/교환을 논리별 선언으로 → 선형·관련성·초일관 세계.
2. **커널 Rust/OCaml 포팅** — 파서·CLI·web은 Python 유지; 공유 테스트 코퍼스로 동작 잠금.
3. **1차 논리** — Bind 노드, 포획회피 치환, freshness, α-동치.
4. **Lean 4 export** — 고전·직관 단편 **한정**.
5. **세계 격자 전체** — 세계 포함 관계, 크립키 의미론 기반.
6. (마지막) **LLM 튜터** — 세계/증명/논리정의 제안, 전부 커널 검증.

---

## 8. Claude Code가 하지 말아야 할 것

- 논리별 규칙·의미 지식을 `kernel.py`에 넣지 말 것. 규칙은 `logic.py` 데이터로 유지.
- 커널을 비구문적/결정불가 매처로 바꾸거나 의미론에 호출하게 하지 말 것.
- **의존성 추가 금지**(stdlib 전용; lark·웹 프레임워크 재도입 금지). 테스트는 `pytest`만.
- 커널이 세계의 무모순/건전을 주장하게 하지 말 것 — "선언된 L에서 유효" 까지만.
- ⊢/⊨ 혼동, 비도출성 과장(문서·메시지·UI)을 하지 말 것.
- K3/LP 표를 매니페스토에서 벗어나게 변경하지 말 것(테스트 그린 유지; 변경 시 정당화 후 재잠금).
- 트러스티드 커널에 증명 탐색/자동화를 넣지 말 것(탐색은 untrusted).
- 직관논리에 LEM/DNE를 몰래 추가하거나 고전/직관의 단일 규칙 구분을 흐리지 말 것.
- 다치/초일관 세계의 Lean export를 만들지 말 것(건전한 대상 없음).
- 방출/스코프 의미를 깨지 말 것(방출된 가정 누출 금지).
- 동작하는 모듈을 통째로 재작성하지 말 것 — 표적 편집 선호, 매 변경 후 `pytest` 그린 유지.
