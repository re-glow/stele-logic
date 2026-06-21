# Stele

**수학적 추론의 형식 검증 프레임워크** (Formal Verification Framework for Mathematical Reasoning)

증명을 가정·추론 규칙·증명 상태의 구조화된 객체로 표현하고, 규칙 기반 검증 모듈로 각 단계를 검사해 빠진 가설·잘못된 전이·미지원 결론 같은 엄밀성 오류를 발견·위치추적한다. 사용자가 단계를 명시하고, **신뢰 커널(trusted kernel)**이 각 단계가 선언된 논리에서 유효한지 판정한다.

- **이다:** 증명검증기(proof checker) + 다논리 의미론적 진단 플랫폼. 여러 논리를 나란히 비교해 추론 규칙의 건전성·독립성을 진단할 수 있다.
- **아니다:** 정리증명기(theorem prover). 증명을 탐색하지 않는다.

언어 가이드: `GUIDE.md` · 결정·근거: `DECISIONS.md` · 실행 결과: `RESULTS.md` · Claude Code 컨텍스트: `CLAUDE.md`

## 실행

요구사항: Python 3.10+ (런타임 의존성 없음; 테스트에만 `pytest`)

```
python -m stele.web                                                  # 브라우저 UI
python -m stele.cli check examples/dne.stele --logic classical_prop
python -m stele.cli check examples/dne.stele --logic intuitionistic_prop
python -m stele.cli check examples/matrix_k3.stele --logic K3      # 행렬 모드
python -m stele.cli soundness --logic classical_prop --matrix K3   # 규칙 건전성
python -m stele.cli lattice "P or Q"                               # 세계 격자 데모
python -m stele.cli demos
python -m pytest -q
```

## Development

Requirements: Python 3.10+, `pytest` (test-only dependency, no runtime deps).

```bash
# Run the test suite
python -m pytest -q

# Check a proof against a specific logic
python -m stele.cli check examples/dne.stele --logic classical_prop
python -m stele.cli check examples/dne.stele --logic intuitionistic_prop

# Matrix-mode semantic queries
python -m stele.cli check examples/matrix_k3.stele --logic K3

# Rule soundness report (do classical rules preserve designation in K3?)
python -m stele.cli soundness --logic classical_prop --matrix K3

# World lattice / CH-style independence demo
python -m stele.cli lattice "P or Q"

# Many-valued semantics demos
python -m stele.cli demos

# Local web UI (port 8765)
python -m stele.web
```

CI runs on every push and pull request via GitHub Actions (`.github/workflows/ci.yml`), testing Python 3.10–3.12.

## 웹 UI

`python -m stele.web` 를 실행하면 로컬 서버(기본 포트 8765)가 뜨고 브라우저가 열린다. 증명 편집기에서 예제를 불러오고 **논리 세계 토글**을 바꾸면 같은 증명의 판정이 즉시 뒤집히며, 하단에 K3/LP/고전 진리표와 배중률·거짓말쟁이·폭발원리 결과가 표시된다. 백엔드는 표준 라이브러리만 쓰며 기존 Python 커널을 그대로 호출한다(검사 로직 중복 없음).

## 다논리 검증 데모

같은 증명 텍스트가 선언된 논리에 따라 다르게 판정된다 — 검증기가 추론 규칙의 가용성을 논리별로 격리하기 때문이다.

```
$ python -m stele.cli check examples/dne.stele --logic classical_prop
OK Proof verified: dne_consequent   [logic: classical_prop]

$ python -m stele.cli check examples/dne.stele --logic intuitionistic_prop
X Proof failed: dne_consequent (line 3)
  rule 'dne' is not available in logic 'intuitionistic_prop'
```

`not not P |- P`는 고전논리에서는 성립하지만 직관논리에서는 성립하지 않는다. 검사기는 *그 증명이 직관논리 규칙으로 타입검사 실패함*을 보인다. (정직한 한계: 도출 불가능성 자체는 메타 주장이며, 그것을 의미론적으로 확립하는 것은 matrix 모드와 이후 크립키 의미론이다.)

## Stele-Light 문법 (MVP)

```
theorem NAME [using LOGIC]:
  assume LABEL: FORMULA
  have   LABEL: FORMULA by RULE ARG...
  suppose LABEL: FORMULA          # 들여쓰기 블록으로 가정 도입
    ...                           # 블록 종료 시 가정은 방출(discharge)
  conclude FORMULA by REF
```

식: `P`, `not P`, `P and Q`, `P or Q`, `P -> Q`, 괄호.
우선순위 `not > and > or > ->`, `->` 우결합.

## 규칙

공통 규칙 (`intuitionistic_prop` 및 `classical_prop`):

| 규칙 | 형태 | 비고 |
|---|---|---|
| `copy` | A ⊢ A | |
| `mp` (→E) | A→B, A ⊢ B | |
| `imp_intro` (→I) | [A]…B ⊢ A→B | 가정 방출 |
| `and_intro` | A, B ⊢ A∧B | |
| `and_elim_left` | A∧B ⊢ A | |
| `and_elim_right` | A∧B ⊢ B | |
| `neg_elim` (¬E) | A, ¬A ⊢ ⊥ | |
| `ex_falso` (⊥E) | ⊥ ⊢ A | |
| `or_intro_left` | A ⊢ A∨B | |
| `or_intro_right` | B ⊢ A∨B | |
| `neg_intro` (¬I) | [A]…⊥ ⊢ ¬A | 가정 방출 |
| `or_elim` (∨E) | A∨B, [A]…C, [B]…C ⊢ C | 가정 방출(2개) |

`classical_prop`이 추가하는 규칙 (직관논리에는 없음):

| 규칙 | 형태 | 비고 |
|---|---|---|
| `dne` | ¬¬A ⊢ A | 이중부정소거 |
| `lem` | ⊢ A∨¬A | 배중률 |
| `pbc` | [¬A]…⊥ ⊢ A | 귀류법, 가정 방출 |

`classical_prop`은 `intuitionistic_prop`에 `dne`, `lem`, `pbc` 세 고전 규칙을 추가한 것이다. 두 논리는 공통 규칙을 모두 공유하며, 이 세 규칙의 가용성 여부만으로 갈린다.

## 의미론적 진단 모듈 (matrix 모드, |=)

`stele/matrix.py` — K3(Kleene 강한 3치), LP(Priest), boolean(고전) 행렬. 각 행렬은 이 프로젝트가 채택한 정의를 따르며 테스트가 `I→F=I`, `F→I=T`를 고정한다. K3와 LP는 designated 값만 다르다(K3: {T}, LP: {T,B}).

이 모듈들은 **진단 도구**다 — proof 논리의 규칙이 다른 의미론 아래서 건전한지 비교하고, 명제의 다논리 독립성 패턴을 탐색할 수 있다. 신뢰 커널의 일부가 아니며, 증명 검사는 이 모듈에 의존하지 않는다.

## 의존성 정책

**신뢰 코어:** `stele/` 핵심 모듈은 표준 라이브러리만 사용한다(런타임 의존성 0). 테스트에만 `pytest`. 이 경계는 감사 가능성과 이식성을 위해 유지한다.

**선택적 확장:** 미래의 ML·Lean 브릿지·패키징·시각화·UI 컴포넌트는 선택적 extras, 별도 패키지, 또는 명확히 분리된 모듈로 격리하여 의존성을 추가할 수 있다. 이들은 신뢰 검사 경로에 진입해서는 안 된다.

## 신뢰 경계

`stele/kernel.py` 만이 신뢰 코어다(매칭 + 증명트리 검사, 순수 구문적). 파서·CLI·matrix 모듈·향후 ML은 모두 untrusted이며 커널이 재검사한다.

## 구조

```
stele/
  ast.py      식 표현(연결사 무지) + 출력기
  proof.py    증명 노드 + MatrixDirective
  parser.py   직접 구현한 토크나이저 + 재귀하강 파서
  logic.py    RuleSchema, Logic, MatrixLogic; 내장 논리(고전/직관/K3/LP/boolean)
  kernel.py   신뢰 코어: 매처 + 증명트리 검사 (proof 모드)
  matrix.py   다치 의미론: Matrix, K3/LP/boolean, 평가·항진성·귀결·고정점·건전성
  world.py    World(matrix, axioms) + status(PROVABLE/REFUTABLE/BOTH/INDEPENDENT) + lattice_status
  cli.py      check / soundness / lattice / demos
  web.py      로컬 웹 UI 서버(stdlib)
  webapp/index.html  단일 파일 프런트엔드
examples/     증명·행렬·세계 예제 (.stele + .py)
tests/        215개 테스트
```

## 구현된 것 / 로드맵

**현재 구현:**
- 자연연역 증명검증기 (proof 모드, 커널 신뢰 코어)
- 공통 명제 규칙 전체 (`neg_elim`, `ex_falso`, `or_intro`, `neg_intro`, `or_elim` 포함)
- 고전 전용 규칙 (`dne`, `lem`, `pbc`) + 상대성 데모
- 다치 의미론 (K3, LP, boolean) + 행렬 모드 표면 문법 (`.stele` 지시문)
- 규칙 건전성 자동 보고 (`soundness` 명령)
- 의미론적 세계 `World(matrix, axioms)` + 4-상태 `status()` (PROVABLE/REFUTABLE/BOTH/INDEPENDENT)
- 세계 격자 데모 — CH-스타일 명제 독립성 패턴 (`lattice` 명령)

**다음 작업 (로드맵):**
- 구조 규칙 정책 (약화·축약 제거 → 선형·관련성·초일관 세계)
- 1차 논리 (한정사, 치환, freshness)
- Lean 4 export (고전·직관 단편 한정)
- 커널 Rust/OCaml 포팅 (sum type + 망라적 패턴매칭)
- LLM 튜터 (커널이 재검사)
