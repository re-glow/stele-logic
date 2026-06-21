# CLAUDE.md

이 파일은 Claude Code가 저장소를 열 때 자동으로 읽는 프로젝트 컨텍스트다.
더 긴 개발 컨텍스트(설계 결정·불변·TODO·금지사항 전체)는 [`docs/development-context.md`](docs/development-context.md)를 참조.

## 프로젝트 정체성

**Stele** — **수학적 추론의 형식 검증 프레임워크**(formal verification framework for mathematical reasoning).

증명을 가정·추론 규칙·증명 상태의 구조화된 객체로 표현하고, 규칙 기반 검증 모듈로 각 단계를 검사해 빠진 가설·잘못된 전이·순환 의존성·미정의 기호·미지원 결론 같은 엄밀성 오류를 발견·위치추적한다.

- **이다:** 증명검증기(proof checker) + 의미론적 진단 플랫폼. 사용자가 단계를 명시하고 커널이 옳은지 판정한다.
- **아니다:** 정리증명기(theorem prover). 증명을 탐색하지 않는다.

논리적 다원주의(유리학)는 배경 영감이자 선택적 의미론 모듈의 동기이며, 프로젝트의 일차 정체성이 아니다. 철학적 주장이 아닌 검증 도구로서 독립적으로 평가되어야 한다.

관련 문서: 언어 가이드 `GUIDE.md`, 결정·근거 `DECISIONS.md`, 실행 결과 `RESULTS.md`.

## 구조

```
stele/
  ast.py      식 표현(연결사 무지 Op) + pretty 출력기
  proof.py    증명 노드(Assume/Have/Suppose/Conclude/Theorem) + MatrixDirective
  parser.py   직접 구현한 토크나이저 + 재귀하강 파서 (의존성 없음)
  logic.py    RuleSchema, Logic, MatrixLogic; 내장 논리 5종
  kernel.py   ★ 신뢰 코어: 1차 구문 매처 + 증명트리 검사 (proof 모드)
  matrix.py   다치 의미론: Matrix, K3/LP/boolean + rule_soundness()
  world.py    World(matrix, axioms) + status() + lattice_status()
  cli.py      check / soundness / lattice / demos
  web.py      로컬 웹 UI 서버(stdlib http.server)
  webapp/index.html   단일 파일 프런트엔드
examples/  *.stele  (증명·행렬·세계)
tests/     pytest 226개
```

## 실행

런타임 의존성 없음(테스트에만 `pytest`). Python 3.10+.

```
python -m pytest -q
python -m stele.cli check examples/dne.stele --logic classical_prop
python -m stele.cli check examples/dne.stele --logic intuitionistic_prop   # 거부됨
python -m stele.cli soundness --logic classical_prop --matrix K3
python -m stele.cli lattice "P or Q"
python -m stele.cli demos
python -m stele.web        # 브라우저 UI (기본 포트 8765)
```

## 불변 규칙 (반드시 지킬 것)

1. **신뢰 경계 = `stele/kernel.py` 뿐.** 매칭은 *순수 구문적·결정 가능*이어야 하며, 어떤 대상 논리의 *의미*에도 호소하지 않는다. 커널은 작고 감사 가능하게 유지한다(de Bruijn 기준). 의미론 검사를 커널에 끌어들이지 말 것.
2. **커널은 규칙을 모른다.** 규칙은 코드가 아니라 `logic.py` 의 `RuleSchema` 데이터다. 새 논리는 규칙 집합을 추가하는 것이지 커널을 고치는 것이 아니다.
3. **신뢰 코어의 의존성 0.** `stele/` 핵심 모듈은 표준 라이브러리만 사용한다. 파서를 lark 등으로 대체하지 말 것. 선택적 ML·Lean·패키징 확장은 신뢰 검사 경로 밖에서만 허용된다.
4. **K3/LP 행렬 정의.** `matrix.py`의 K3/LP 표는 이 프로젝트가 채택한 Kleene/Priest 방식 진리표와 일치해야 한다(모듈 수준 행동 제약; `test_k3_imp_table_matches_manifesto`가 `I→F=I`, `F→I=T`를 고정). 변경 시 테스트로 재잠금.
5. **정직성.** 상대성은 *규칙 가용성* 수준임을 문서·메시지에서 흐리지 말 것. 도출 불가능성은 메타 주장이며 검사기가 직접 확립하지 않는다. 미측정 메트릭·코퍼스·모델 결과를 주장하지 말 것.
6. **proof 모드 ≠ matrix 모드.** `kernel.py`는 `matrix.py`를 임포트하지 않고, `matrix.py`는 `kernel.py`를 임포트하지 않는다(`test_regression_invariants` 가 보장).

## 코드 스타일

- 식별자는 영어, 사용자 대면 문자열·주석은 한국어 가능.
- AST·스키마·증명 노드는 frozen dataclass(구조적 동치/해시 필요).
- 변경 후 항상 `pytest` 통과 확인. 규칙·문법을 바꾸면 대응 테스트와 `examples/` 를 갱신.

## 로드맵 (다음 작업 후보)

**검증 코어:**
- 의존성 그래프 추출 (증명 단계 간 의존 관계)
- 증명 상태 추적 (열린 목표·해소된 가정)
- 변환 검사 (증명 이동·재구성)
- 오류 위치추정: 미정의 기호, 타입 불일치, 빠진 가설, 순환 의존성

**벤치마크·평가:**
- 정리 스타일 벤치마크 작업
- 실패 모드 분류 체계
- 회귀 테스트 인프라 확장

**선택적 확장 (신뢰 코어 밖):**
- 비형식 증명 스케치 → 형식 구조 변환 (선택적)
- ML/SLM 증명검증 보조 (선택적; 커널이 재검사)
- Lean 브릿지 (고전·직관 단편 한정, 선택적)
- 커널 Rust/OCaml 포팅

## 비목표

- 자동 증명 탐색을 커널에 넣기(검증기 ≠ 증명기; 탐색은 별도/untrusted).
- 미구현·미측정 ML/코퍼스/정확도를 문서나 README에서 주장하기.
- 다치/초일관 세계의 Lean export.
