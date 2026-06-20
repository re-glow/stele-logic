# CLAUDE.md

이 파일은 Claude Code가 저장소를 열 때 자동으로 읽는 프로젝트 컨텍스트다.
더 긴 개발 컨텍스트(설계 결정·불변·TODO·금지사항 전체)는 [`docs/development-context.md`](docs/development-context.md)를 참조.

## 프로젝트

**Stele Logic System** — 사람이 읽는 형식언어(Stele-Light)로 증명을 작성하면 커널이 검증하는 **증명검증기**(proof checker, *정리증명기 아님*). 핵심 설계는 **logical framework**: 커널은 어떤 논리에도 헌신하지 않고, 로드된 논리 정의(규칙 집합 = 공리 함수 `A(S)`)에 *상대적으로* 검사한다. 고전논리는 여러 논리 중 하나다. 이것이 배경 철학(유리학: 국소적 진리·논리적 다원주의)을 실행 가능하게 만든다.

관련 문서: 설계 `stele_redesign.md`, 언어 가이드 `GUIDE.md`, 결정·근거 `DECISIONS.md`, 실행 결과 `RESULTS.md`.

## 구조

```
stele/
  ast.py      식 표현(연결사 무지 Op) + pretty 출력기
  proof.py    증명 노드(Assume/Have/Suppose/Conclude/Theorem)
  parser.py   직접 구현한 토크나이저 + 재귀하강 파서 (의존성 없음)
  logic.py    RuleSchema, Logic, 내장 논리(classical_prop / intuitionistic_prop)
  kernel.py   ★ 신뢰 코어: 1차 구문 매처 + 증명트리 검사 (proof 모드)
  matrix.py   다치 의미론: Matrix, K3/LP/boolean, 평가·항진성·귀결·고정점
  cli.py      check / demos
  web.py      로컬 웹 UI 서버(stdlib http.server)
  webapp/index.html   단일 파일 프런트엔드
examples/  *.stele  (검증·오류·상대성)
tests/     pytest 19개
```

## 실행

런타임 의존성 없음(테스트에만 `pytest`). Python 3.10+.

```
python -m pytest -q
python -m stele.cli check examples/dne.stele --logic classical_prop
python -m stele.cli check examples/dne.stele --logic intuitionistic_prop   # 거부됨
python -m stele.cli demos
python -m stele.web        # 브라우저 UI (기본 포트 8765)
```

## 불변 규칙 (반드시 지킬 것)

1. **신뢰 경계 = `stele/kernel.py` 뿐.** 매칭은 *순수 구문적·결정 가능*이어야 하며, 어떤 대상 논리의 *의미*에도 호소하지 않는다. 커널은 작고 감사 가능하게 유지한다(de Bruijn 기준). 편의를 위해 의미론 검사를 커널에 끌어들이지 말 것.
2. **커널은 규칙을 모른다.** 규칙은 코드가 아니라 `logic.py` 의 `RuleSchema` 데이터다. 새 논리는 규칙 집합을 추가하는 것이지 커널을 고치는 것이 아니다.
3. **런타임 의존성 0 유지.** 파서를 lark 등으로 대체하지 말 것(신뢰 경로·이식성). 표준 라이브러리만.
4. **다치 표의 충실성.** `matrix.py` 의 K3/LP 표는 유리학개론 pp.4–5와 일치해야 한다(테스트 `test_k3_imp_table_matches_manifesto`가 `I→F=I`, `F→I=T` 를 고정). 변경 시 테스트로 잠글 것.
5. **정직성.** 상대성은 *규칙 가용성* 수준임을 문서·메시지에서 흐리지 말 것. 도출 불가능성은 메타 주장이며 검사기가 직접 확립하지 않는다.

## 코드 스타일

- 식별자는 영어, 사용자 대면 문자열·주석은 한국어 가능.
- AST·스키마·증명 노드는 frozen dataclass(구조적 동치/해시 필요).
- 변경 후 항상 `pytest` 통과 확인. 규칙·문법을 바꾸면 대응 테스트와 `examples/` 를 갱신.

## 로드맵 (다음 작업 후보)

- matrix 모드 표면 문법(`evaluate` / `valid?` / `entails` 지시문) + 거짓말쟁이.
- 세계 격자(진리 위상): `World = (logic, axioms)`, `status(φ, W) ∈ {provable, refutable, independent}`.
- 구조 규칙 정책(약화·축약 제거 → 선형·관련성·초일관 세계).
- 1차 논리(한정사, 치환, freshness, 결국 고차 매칭).
- Lean export — **고전·직관 단편 한정**(다치·초일관 세계는 비목표).
- **커널의 Rust/OCaml 포팅** — sum type + 망라적 패턴매칭으로 신뢰 코어를 구성적으로 경화. 파서·CLI·web 은 Python 유지.

## 비목표

- 다치/초일관 세계의 Lean export.
- 자동 증명 탐색을 커널에 넣기(검증기 ≠ 증명기; 탐색은 별도/untrusted).
- 명제 단편이 안정화되기 전 1차 논리 일반화.
