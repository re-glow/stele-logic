# Corpus Generation

Stele의 합성 코퍼스 생성기(`bench/generate.py`)는 증명 검증 태스크를 위한
레이블된 JSONL 데이터셋을 결정론적으로 생성한다.

> **정직성 규칙:** 이 페이지는 실제로 생성·측정된 값만 기술한다.
> 500k 코퍼스는 존재하지 않는다(커밋되지 않았다). 정확도 수치를 주장하지 않는다.

---

## 설계 원칙

| 원칙 | 구현 |
|------|------|
| 결정론적 | `--seed` + corpus별 고정 오프셋 → 동일 입력 = 동일 출력 |
| 격리 | `bench/generate.py`는 `stele/` 신뢰 코어를 임포트하지 않음(검증 경로 밖) |
| 레이블 진실성 | `--validate` 플래그가 실제 체커와 비교해 불일치를 경고함 |
| 확장 가능 | 알고리즘은 500k+를 지원하나, 대용량 출력은 커밋하지 말 것 |
| 의존성 없음 | stdlib만 사용(pytest는 테스트 전용) |

---

## 디렉터리 구조

```
bench/
  generate.py               CLI 진입점 + 코어 함수
  corpora/
    __init__.py             레지스트리 (REGISTRY, ALL_DISTRIBUTION, ...)
    prop_nd.py              명제 자연연역 corpus
    definition_use.py       formula definitions corpus
    diagnostic_errors.py    진단코드별 전용 패턴 corpus
  generated/
    sample/                 ★ 커밋된 소형 샘플 (40개)
      shard_00000.jsonl
      shard_00001.jsonl
      manifest.json
    # 대용량 출력은 여기에 두되 .gitignore 처리
```

---

## CLI 사용법

```bash
# 기본 (--corpus all, --n 100, --seed 0)
python bench/generate.py

# prop_nd corpus 100개
python bench/generate.py --corpus prop_nd --n 100 --seed 0 --out bench/generated/demo

# 전체 corpus 300개, 샤드 크기 100
python bench/generate.py --corpus all --n 300 --out bench/generated/demo --seed 42 --shard-size 100

# 레이블 검증 포함
python bench/generate.py --corpus all --n 50 --out bench/generated/test --seed 0 --validate

# 대용량 생성 (커밋 금지 — 외부 스토리지 또는 릴리즈 아티팩트에 저장)
python bench/generate.py --corpus all --n 500000 --out bench/generated/500k --seed 0 --shard-size 10000
```

### 인수

| 인수 | 기본값 | 설명 |
|------|--------|------|
| `--corpus` | `all` | `all`, `prop_nd`, `definition_use`, `diagnostic_errors` 중 선택 |
| `--n` | `100` | 총 레코드 수 |
| `--out` | `bench/generated/run` | 출력 디렉터리 |
| `--seed` | `0` | 결정론적 RNG 시드 |
| `--shard-size` | `1000` | JSONL 샤드당 레코드 수 |
| `--validate` | off | Stele 체커로 레이블 검증 실행 |

---

## 출력 형식

### 레코드 필드

각 레코드는 JSON 객체 한 줄로 출력된다:

```json
{
  "id": "prop_nd_000003",
  "corpus": "prop_nd",
  "text": "theorem prop_000003 using intuitionistic_prop:\n  assume h1: P -> Q\n  ...",
  "logic": "intuitionistic_prop",
  "expected_valid": true,
  "expected_codes": [],
  "tags": ["valid", "mp"],
  "metadata": {
    "generator_version": 1,
    "mutation": null
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | string | `{corpus}_{index:06d}` — corpus 내에서 유일 |
| `corpus` | string | 생성기 패밀리 이름 |
| `text` | string | 파서에 직접 전달 가능한 `.stele` 형식 텍스트 |
| `logic` | string | `intuitionistic_prop` 또는 `classical_prop` |
| `expected_valid` | bool | `check_theorem`이 통과해야 하면 `true` |
| `expected_codes` | list[str] | `diagnose_theorem`이 반환해야 할 코드 목록 |
| `tags` | list[str] | 필터링/분석용 레이블 |
| `metadata.generator_version` | int | 생성기 스키마 버전 |
| `metadata.mutation` | str \| null | 주입된 오류 코드 (없으면 null) |

### 경고 레코드의 expected_valid

`UnusedAssumption`과 `UndefinedDefinition`은 경고(warning)다. 체커는 통과하지만
진단은 코드를 반환한다:

```json
{
  "expected_valid": true,
  "expected_codes": ["UnusedAssumption"]
}
```

오류(error) 레코드는 `expected_valid: false`다.

### 샤드 형식

```
out/
  shard_00000.jsonl   # 첫 shard_size 레코드
  shard_00001.jsonl
  ...
  manifest.json
```

### manifest.json

```json
{
  "args": { "corpus": "all", "n": 40, "seed": 0, "shard_size": 20 },
  "corpora": ["definition_use", "diagnostic_errors", "prop_nd"],
  "generator": "bench.generate v1",
  "generator_version": 1,
  "n_per_corpus": { "definition_use": 8, "diagnostic_errors": 8, "prop_nd": 24 },
  "n_shards": 2,
  "n_total": 40,
  "shard_size": 20,
  "shards": ["shard_00000.jsonl", "shard_00001.jsonl"]
}
```

---

## Corpus 패밀리

### prop_nd

명제 자연연역 증명. 10개의 유효 템플릿과 7개의 변이 템플릿으로 구성된다.

**유효 템플릿 (valid):**
`mp_basic`, `mp_chain`, `and_intro`, `and_elim_left`, `and_elim_right`,
`or_intro_left`, `or_intro_right`, `imp_intro`, `neg_elim`, `ex_falso`

**변이 (mutation):**

| 변이 | expected_valid | expected_codes |
|------|----------------|----------------|
| undef_ref (mp) | false | UndefinedSymbol |
| undef_ref (copy) | false | UndefinedSymbol |
| forward_ref | false | MissingHypothesis |
| wrong_conclusion | false | UnsupportedConclusion |
| wrong_premise_type (mp) | false | InvalidTransition |
| wrong_elim (and_elim_left) | false | InvalidTransition |
| add_unused | **true** | UnusedAssumption |

비율: 유효 50% / 변이 50% (seeded RNG로 선택).
로직: `intuitionistic_prop`.

### definition_use

정의 매크로를 사용하는 증명. 절반은 유효(정의 전개 후 mp 적용),
절반은 정의 본문에서 미정의 이름 참조(UndefinedDefinition).

UndefinedDefinition 레코드는 정리 본문이 자명하게 유효하므로
`expected_valid: true`이지만 `expected_codes: ["UndefinedDefinition"]`이다.

### diagnostic_errors

진단 코드별 전용 패턴을 6개 단위로 순환한다:
`UndefinedSymbol → MissingHypothesis → UnsupportedConclusion →
InvalidTransition → UndefinedDefinition → UnusedAssumption → (반복)`

n=6k이면 각 코드가 정확히 k회 등장한다.

---

## 결정론 보장

동일한 (`--corpus`, `--n`, `--seed`, `--shard-size`) 조합은 항상 동일한 출력을 생성한다.

corpus별 시드 오프셋(`CORPUS_SEED_OFFSETS`)을 적용하므로, prop_nd를 단독 생성할 때의
레코드와 `--corpus all` 내 prop_nd 레코드가 동일하다:

```python
# bench/corpora/__init__.py
CORPUS_SEED_OFFSETS = {
    "prop_nd": 0,
    "definition_use": 1000,
    "diagnostic_errors": 2000,
}
```

> **주의:** Python의 `random` 모듈 내부 알고리즘은 메이저 버전 간에 변경될 수 있다.
> 동일 Python 버전 내에서만 완전한 재현성이 보장된다.

---

## 레이블 검증

`--validate` 플래그는 생성 후 각 레코드에 대해
`stele.kernel.check_theorem`과 `stele.diagnostics.diagnose_theorem`을 실행해
예측값과 레이블을 비교한다:

```
Validating labels against Stele checker…
  OK: 40  FAIL: 0
```

불일치가 발견되면 경고를 출력하되 종료 코드 0을 반환한다(검증은 정보성).
생성기 템플릿을 수정할 경우 반드시 `--validate`로 레이블 정확도를 재확인할 것.

---

## 대용량 생성 가이드라인

500k 이상 생성은 알고리즘적으로 지원되지만 **저장소에 커밋하지 말 것.**

```bash
# 외부 스토리지용 500k 생성 예시
python bench/generate.py \
  --corpus all --n 500000 --seed 0 \
  --shard-size 10000 \
  --out /path/to/external/storage/stele-500k
```

대용량 출력을 저장소에 추가하기 전에 반드시 `.gitignore`에 경로를 등록하라.
`bench/generated/sample/`만 커밋 대상이다.

---

## 새 Corpus 패밀리 추가

1. `bench/corpora/new_corpus.py` 작성: `generate(n, rng, start_id=0)` 함수 구현
2. `bench/corpora/__init__.py`의 `REGISTRY`, `ALL_DISTRIBUTION`, `CORPUS_SEED_OFFSETS`에 등록
3. `ALL_DISTRIBUTION` 값의 합이 1.0이 되도록 조정
4. `tests/test_corpus_generator.py`에 레이블 정확도 테스트 추가
5. `python bench/generate.py --corpus new_corpus --n 20 --validate`로 검증

---

## 관련 문서

- [`docs/failure-modes.md`](failure-modes.md) — 진단 코드 분류 체계
- [`GUIDE.md §17`](../GUIDE.md) — 벤치마크 평가 하네스
- [`GUIDE.md §18`](../GUIDE.md) — 합성 코퍼스 생성기
