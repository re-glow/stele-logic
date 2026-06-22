# Stele — Development Context (Claude Code Handoff)

이 문서는 Stele Logic System을 Claude Code로 이어받기 위한 압축 핸드오프다.
보강 문서: 설계 `stele_redesign.md`, 언어 `GUIDE.md`, 결정 `DECISIONS.md`, 결과 `RESULTS.md`, 운영 규칙 `CLAUDE.md`.

런타임: Python 3.10+, **외부 의존성 0** (테스트: `pytest`; 속성 기반 테스트: `hypothesis`, 선택적).

외부 의존성 0이라는 원칙은 단순한 설계 선택 이상의 실질적 의미를 갖는다:
Stele 코어는 Pyodide/WASM을 통해 **브라우저에서 직접 실행**할 수 있다.
`tools/build_pyodide_site.py`가 정적 사이트(`dist/site/`)를 생성하며,
GitHub Pages 워크플로우(`.github/workflows/pages.yml`)가 자동 배포한다.

**배포 면:**
- **로컬 Python Studio** (`python -m stele`) — Python 설치 필요, 전 기능
- **독립 실행 앱** (`packaging/build_app.py`) — Python 불필요, PyInstaller 번들
- **브라우저 전용 사이트** (`site/`, Pyodide) — Python·설치 불필요, 백엔드 없음, 정적 호스팅

속성 기반 테스트: `pip install -r requirements-dev.txt` 후 `pytest tests/test_proof_term_properties.py`.
Hypothesis 없이 `python -m pytest -q`는 항상 통과한다.

---

## 1. Stele는 무엇이고, 무엇이 아닌가

- **이다:** **수학적 추론의 형식 검증 프레임워크**. 사람이 읽는 형식언어(Stele-Light)로 자연연역 증명을 적으면, 트러스티드 커널이 각 단계를 검증하는 **증명검증기(proof checker)**. 증명을 구조화된 객체(가정·추론 규칙·증명 상태)로 표현하고, 규칙 기반 검증 모듈로 엄밀성 오류(빠진 가설·잘못된 전이·미지원 결론)를 발견·위치추적한다. 다논리 의미론 모듈은 추론 규칙을 여러 의미론 아래 비교 진단하는 지원 도구다.
- **아니다:** 정리증명기(prover)가 아니다 — 증명을 *탐색*하지 않는다. 사용자가 단계를 명시하고 커널은 옳은지만 판정한다. SMT/SAT 솔버도, 단일 고전 기초(Lean/Coq류)도 아니다.

논리적 다원주의(유리학)는 배경 영감이자 의미론 모듈의 연구 동기다. 프로젝트의 일차 정체성은 검증 도구로서의 유용성이며, 철학적 주장과 독립적으로 평가되어야 한다.

---

## 2. 이미 구현된 것 (888개 테스트 통과, Hypothesis 포함)

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
stele/core/   terms.py / typing.py / reduce.py / term_parser.py
              — 증명항 계산법: TVar/Lam/App/Pair/Fst/Snd/Inl/Inr/Case/Abort
              — 양방향 타입 검사(infer/check) + β-환원(step/normalize/is_normal)
              — 표면 문법 파서(parse_term)
stele/elaborate.py  — 스크립트 → 증명항 정교화(crosscheck_theorem)
docs/semantics.md   — 형식 문법(BNF/EBNF) + 타입 규칙 + 환원 규칙 참조 명세
docs/metatheory.md  — 7개 메타이론 주장과 현황(주체 환원·정규화·합류성·일관성 등)
docs/proof-terms.md — 증명항 API + 정교화 가이드 + CLI 사용법
tests/     parser / kernel_valid / kernel_invalid / relativism / matrix
           conclusion_directed / new_rules / generalized_discharge / discharge_rules
           classical_principles / matrix_surface / rule_soundness / world / world_lattice
           test_proof_terms / test_elaboration / test_reduction
           test_proof_term_properties (선택적, Hypothesis 필요)
           test_docs_and_deps
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

## 4. 핵심 설계 결정

- **커널 = logical framework.** 초일관 세계 = ECQ(폭발) 규칙을 뺀 논리 파일; 다치 세계 = matrix 모드. 고전논리는 여러 논리 중 하나. 이 구조는 추론 규칙의 가용성을 논리별로 격리해 *검증 프레임워크*로서의 비교 분석을 가능케 한다(논리적 다원주의는 이 구조의 철학적 배경이며 시스템의 유일한 정의가 아니다).
- **언어:** Python(반복 속도·실증·의존성 0). 커널 경화는 이후 **Rust/OCaml**(sum type + 망라적 패턴매칭 → 구성적 정확성).
- **파서는 직접 구현**(lark 미사용) — 신뢰 경로·이식성.
- **정직한 한계:** 검사기가 보이는 건 *고전 전용 규칙에 의존하는 증명이 직관 세계에서 타입검사 실패*. 완전한 비도출성은 메타 주장이며 의미론(matrix/크립키)의 몫.
- **K3/LP 행렬 정의:** 이 프로젝트가 채택한 Kleene/Priest 방식 진리표를 따른다(→(I,F)=I, →(F,I)=T 고정). LP designated {T,B}. 이것은 모듈 수준 행동 제약이며 전체 시스템의 정의가 아니다.

---

## 5. 보존해야 할 형식논리 제약 (불변)

1. 커널 매칭은 **순수 구문적·결정 가능**; 의미론 호출 금지. 메타논리 ≤ 모든 대상 논리(최소·구성적 유지).
2. 규칙은 데이터. 새 논리는 규칙 추가이지 커널 변경이 아니다.
3. **도출가능성(⊢, 결정 가능, 커널)** 과 **세계의 건전성/무모순성(메타, 종종 결정 불가)** 을 분리. 커널은 세계가 무모순/건전하다고 **결코 주장하지 않는다**.
4. **⊢ 와 ⊨ 를 혼동하지 말 것**(proof vs matrix). 비도출성을 과장하지 말 것.
5. K3/LP 진리표는 채택된 Kleene/Priest 정의와 일치 유지(`test_k3_imp_table_matches_manifesto`가 →(I,F)=I, →(F,I)=T 고정). K3 designated{T}, LP designated{T,B}. 변경 시 테스트로 재잠금.
6. **방출/스코프:** `suppose` 블록 내부 라벨은 블록이 닫히면 스코프를 벗어난다. 오직 `imp_intro`만 그 블록을 참조 가능(`test_kernel_invalid::test_discharged_hypothesis_out_of_scope` 보장).
7. `classical_prop = intuitionistic_prop + {dne, lem, pbc}`. 직관논리에 고전 규칙을 몰래 추가하지 말 것.

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

**검증 코어 강화:**
1. **의존성 그래프** — 증명 단계 간 의존 관계 추출·시각화.
2. **증명 상태 추적** — 열린 목표·해소된 가정을 명시적으로 추적.
3. **오류 진단 강화** — 미정의 기호, 타입 불일치, 빠진 가설, 순환 의존성 위치추정.
4. **1차 논리** — Bind 노드, 포획회피 치환, freshness, α-동치.
5. **구조 규칙 정책** — 약화/축약/교환을 논리별 선언으로 → 선형·관련성·초일관 세계.

**벤치마크·평가:**
6. **정리 스타일 벤치마크 작업** — 정형화된 증명 검증 태스크.
7. **실패 모드 분류** — 오류 유형 taxonomy + 회귀 테스트 인프라.

**선택적 확장 (신뢰 코어 밖):**
8. **비형식 → 형식 스케치 변환** — 비형식 증명을 형식 구조로 변환 보조 (선택적).
9. **ML/SLM 증명검증 보조** — 커널이 재검사하는 untrusted 보조자 (선택적).
10. **Lean 4 브릿지** — 고전·직관 단편 한정 (선택적).
11. **커널 Rust/OCaml 포팅** — 파서·CLI·web은 Python 유지.

주의: 8–10번은 미구현이며 측정된 메트릭·코퍼스·정확도가 없다. 구현·측정 전까지 주장하지 말 것.

---

## 8. Claude Code가 하지 말아야 할 것

- 논리별 규칙·의미 지식을 `kernel.py`에 넣지 말 것. 규칙은 `logic.py` 데이터로 유지.
- 커널을 비구문적/결정불가 매처로 바꾸거나 의미론에 호출하게 하지 말 것.
- **의존성 추가 금지**(stdlib 전용; lark·웹 프레임워크 재도입 금지). 테스트는 `pytest`만.
- 커널이 세계의 무모순/건전을 주장하게 하지 말 것 — "선언된 L에서 유효" 까지만.
- ⊢/⊨ 혼동, 비도출성 과장(문서·메시지·UI)을 하지 말 것.
- K3/LP 표를 매니페스토에서 벗어나게 변경하지 말 것(테스트 그린 유지; 변경 시 정당화 후 재잠금).
- 트러스티드 커널에 증명 탐색/자동화를 넣지 말 것(탐색은 untrusted).
- 직관논리에 고전 규칙(`dne`, `lem`, `pbc`)을 몰래 추가하거나 고전/직관의 규칙 구분을 흐리지 말 것.
- 다치/초일관 세계의 Lean export를 만들지 말 것(건전한 대상 없음).
- 방출/스코프 의미를 깨지 말 것(방출된 가정 누출 금지).
- 동작하는 모듈을 통째로 재작성하지 말 것 — 표적 편집 선호, 매 변경 후 `pytest` 그린 유지.
- 미구현·미측정 ML 코퍼스·모델 정확도·Lean 통합 결과를 문서·README·메시지에서 주장하지 말 것.
