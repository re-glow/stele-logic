# Stele — v1.4.0

**Formal Verification Framework for Mathematical Reasoning**
(수학적 추론의 형식 검증 프레임워크)

**Public site:** https://re-glow.github.io/stele-logic/
— browser-local Studio, interactive tutorial, verified example gallery (no install, no server, no data transmitted)

## For reviewers and advisors

> **Start here:** [Technical Overview (2-minute summary)](https://re-glow.github.io/stele-logic/overview.html)
> — what Stele is, what is Stable, what is Experimental, and what is not claimed.

| Quick path | Link |
|------------|------|
| **2-minute overview** (status-labeled, no inflation) | [`overview.html`](https://re-glow.github.io/stele-logic/overview.html) |
| **Live demo** (proof checking in browser, no install) | [`studio.html`](https://re-glow.github.io/stele-logic/studio.html) |
| **Technical whitepaper** | [`docs/whitepaper.md`](docs/whitepaper.md) |
| **Architecture & trust boundary** | [`architecture.html`](https://re-glow.github.io/stele-logic/architecture.html) |
| **Formal spec + metatheory claims** | [`docs/semantics.md`](docs/semantics.md) · [`docs/metatheory.md`](docs/metatheory.md) |
| **Full source + test suite** | This repository (2,390+ tests) |

**What it is:** proof checker for natural-deduction. The user writes explicit steps; the trusted kernel checks each inference.
**What it is not:** theorem prover, SMT solver, or AI-powered system. No proof search.
**Metatheory status:** claims are supported by regression tests and proof sketches — not machine-checked by Lean/Coq/Agda.

---

| Page | URL |
|------|-----|
| Landing | https://re-glow.github.io/stele-logic/ |
| Overview | https://re-glow.github.io/stele-logic/overview.html |
| Studio | https://re-glow.github.io/stele-logic/studio.html |
| Theory & Semantics | https://re-glow.github.io/stele-logic/theory.html |
| Architecture & Trust | https://re-glow.github.io/stele-logic/architecture.html |
| Foundations & Research | https://re-glow.github.io/stele-logic/foundations.html |
| Whitepaper | https://re-glow.github.io/stele-logic/research.html |
| About | https://re-glow.github.io/stele-logic/about.html |

Stele is an independent research software project. It provides a rule-checked proof language, proof-term core, structural diagnostics, dependency graphs, matrix semantic diagnostics, and a browser-local Studio. It is **not** a theorem prover — it does not search for proofs. The user writes each proof step; the trusted kernel checks whether each step is valid under the declared logic.

- **Is:** proof checker + multi-logic semantic diagnostics platform.
- **Is not:** theorem prover, SMT/SAT solver, or AI-powered verifier.

Language guide: `GUIDE.md` · Decisions/rationale: `DECISIONS.md` · Results: `RESULTS.md`
Proof-term core: [`docs/proof-terms.md`](docs/proof-terms.md) · Formal spec: [`docs/semantics.md`](docs/semantics.md) · Metatheory: [`docs/metatheory.md`](docs/metatheory.md) · Maintainer context: `CLAUDE.md`
**Technical whitepaper:** [`docs/whitepaper.md`](docs/whitepaper.md) (Markdown) · [`paper/stele-whitepaper.tex`](paper/stele-whitepaper.tex) (LaTeX source) · [`paper/README.md`](paper/README.md) (build instructions)
**Research notes (paper-drafting source packet):** [`docs/research-notes/`](docs/research-notes/) — modules, claims, evidence, examples, limitations, figure plan, and GPT writing instructions for a stronger paper
**Annotated references:** [`docs/references.md`](docs/references.md) — which algorithms are implemented, which are inspiration, what Stele does not claim
**Provenance map:** [`docs/provenance-map.md`](docs/provenance-map.md) — claim → module → test → source → limitation (4 structured tables)
**Site design system:** [`docs/design-system.md`](docs/design-system.md) — IA plan, design tokens, component library, accessibility policy

## v1.4 Capability Matrix

| Capability | v1.0 Status | How to use | Limitations |
|---|---|---|---|
| Proof script checker (Stele-Light) | **Stable** | `python -m stele.cli check FILE --logic L` or Studio Verify | Propositional fragment only; no FOL at script level |
| Intuitionistic propositional rules | **Stable** | `--logic intuitionistic_prop` (default) | — |
| Classical propositional extensions | **Stable** | `--logic classical_prop` | `dne`, `lem`, `pbc` not in intuitionistic |
| Structural diagnostics | **Stable** | Studio Diagnose panel; `stele.browser.browser_diagnose()` | Multi-pass; not all failure modes covered |
| Dependency graph output | **Stable** | Studio Graph panel; `python -m stele.cli graph FILE` | DOT format; visualization via external Graphviz |
| Matrix soundness diagnostics | **Stable** | `python -m stele.cli soundness --logic L --matrix M` | K3 / LP / boolean only |
| World / lattice semantic demo | **Stable** (demo) | `python -m stele.cli lattice FORMULA` | Toy propositional demo, not set-theoretic forcing |
| Proof-term core (Curry–Howard) | **Stable** | `stele.core` API; `python -m stele.cli elaborate FILE` | Intuitionistic propositional only; no classical terms |
| Script-to-term elaboration | **Stable** | `python -m stele.cli elaborate FILE` | Intuitionistic rules only; unsupported rules raise error |
| Proof-term reduction / normalization | **Stable** | `stele.core.reduce.normalize()` | Fuel limit (default 1 000 steps); no η-reduction |
| de Bruijn binder layer | **Stable** | `stele.core.debruijn` | Proof-variable binders only; FOL object-vars remain named |
| First-order proof-term fragment | **Experimental** | `stele.core` ForallIntro/Elim/ExistsIntro/Elim | No proof-script surface syntax; object-var de Bruijn incomplete |
| Kripke countermodel search | **Experimental** | `python -m stele.cli kripke FORMULA` | Propositional only; bounded finite search (≤4 worlds default); no completeness |
| Semantics & metatheory docs | **Stable** (docs) | `docs/semantics.md`, `docs/metatheory.md` | Proof sketches + regression/property tests; not machine-checked |
| Property-based tests (Hypothesis) | **Optional** | `pip install -r requirements-dev.txt && pytest tests/test_proof_term_properties.py` | Requires Hypothesis; core test suite passes without it |
| Browser Pyodide Studio | **Stable** | https://re-glow.github.io/stele-logic/ | Internet required for Pyodide CDN (~8 MB, cached) |
| GitHub Pages public site | **Stable** | Auto-deployed on push to `main` via `.github/workflows/pages.yml` | — |
| Single-file HTML (`stele.html`) | **Stable** | `python tools/build_single_html.py` → `dist/stele.html` | CDN required for Pyodide; full offline mode is future work |
| Standalone executable | **Stable** | `python packaging/build_app.py` → `dist/SteleStudio` | PyInstaller required to build; binary size ~50 MB |
| ML baseline (`stele_ml/`) | **Optional / Experimental** | `pip install -r stele_ml/requirements-ml.txt` | Isolated from trusted path; experimental; not for production use |
| Classical proof-term bridge | **Experimental** | `stele.core.classical_experimental` | Formula-level negative translation (Gödel–Gentzen); no λμ/callcc; no automatic proof translation; intuitionistic core unchanged |
| Lean bridge (`stele_lean/`) | **Optional / Experimental** | Requires Lean 4 installation | Isolated; propositional fragment only; experimental |
| Proof certificates & minicheck | **Experimental** | `python -m stele.cli cert FILE; python -m stele.cli minicheck CERT.json` | Versioned JSON certificate; independent Python re-verification path (no kernel/parser import in minicheck); same process; not formally verified |
| Proof state & hints | **Experimental / Untrusted** | `python -m stele.cli state FILE; python -m stele.cli hints FILE` | UNTRUSTED: structural context snapshot + local rule-applicability hints; no proof search; no ML; all suggestions must be kernel-rechecked |

## Distribution modes

| Mode | Description | Requires |
|------|-------------|----------|
| **Website** | Hosted public site (GitHub Pages) | Browser + internet |
| **Single-file HTML** | Portable `stele.html` — share or open from disk | Browser + internet (CDN, v1) |
| **Standalone app** | Pre-built executable | Nothing |
| **Local Python** | `python -m stele` | Python 3.10+ |

## Quickstart

### 1 — Browser Studio (no install, no Python)

Open the hosted site (GitHub Pages — see Actions tab or Settings → Pages) and start verifying proofs immediately.
The full Stele trusted kernel runs in your browser via Pyodide/WASM. No proof text is sent to any server.

The landing page includes a **5-minute interactive tutorial** (6 guided steps covering the proof format, error diagnosis, dependency graph, classical vs intuitionistic logic, and semantic tools) and a **verified example gallery** (15 curated proofs, each labeled with its expected kernel outcome).

**First-load notice:** Pyodide/WASM is ~8 MB, cached by the browser after the first visit.

**Run the browser build locally:**
```bash
python tools/build_pyodide_site.py     # produces dist/site/
python -m http.server --directory dist/site 8000
# open http://localhost:8000
```

> `file://` may fail in some browsers (CORS on `fetch()`). Use a local HTTP server.

**What runs in the browser:** full proof checking, structural diagnostics, dependency graph, rule soundness, world lattice.
**Excluded from browser build:** `stele_ml/`, `stele_lean/`, benchmark runner (`stele.eval`), tests, `__pycache__`.

### 2 — Single-file HTML (`stele.html`)

Generate a self-contained single HTML file that embeds the Stele core source and loads Pyodide from CDN:

```bash
python tools/build_single_html.py
# produces dist/stele.html (~135 KB)
```

Then double-click `dist/stele.html` to open in your browser.

> **`file://` caveat:** Some browsers restrict `fetch()` from `file://` origins.
> If opening fails, serve it locally:
> ```bash
> python -m http.server --directory dist 8000
> # open http://localhost:8000/stele.html
> ```

**Limitations (v1):**
- Requires an internet connection to load Pyodide from CDN (~8 MB, cached after first load).
- Full offline mode (self-contained, no CDN) is out of scope for v1. See `--pyodide-local` flag in the build script for a manual offline path.

**What's embedded:** same Stele core as the browser site (`stele_ml/`, `stele_lean/`, tests excluded).

### 3 — Standalone app (no Python needed)

Download the pre-built executable from [GitHub Actions](../../actions/workflows/release.yml) or a tagged release, then run:

```
SteleStudio          # macOS / Linux
SteleStudio.exe      # Windows
```

The browser opens automatically to the local Studio. No Python, no install.

**Build it yourself:**
```bash
pip install -r packaging/requirements-packaging.txt
python packaging/build_app.py --onefile
# Output: dist/SteleStudio  (or dist/SteleStudio.exe)
```

### 4 — Local Python

```bash
python -m stele        # launches Stele Studio at http://127.0.0.1:8000
python -m stele --port 8080
python -m stele --no-browser
python -m stele --help
```

No runtime dependencies. Requires Python 3.10+.

```bash
python -m pip install -U pip pytest
python -m pytest -q              # run the test suite
```

---

## 실행

요구사항: Python 3.10+ (런타임 의존성 없음; 테스트에만 `pytest`)

### Stele Studio (로컬 웹 인터페이스)

```bash
python -m stele                   # Stele Studio 실행 (기본 포트 8000, 브라우저 자동 열림)
python -m stele --port 8080       # 포트 지정
python -m stele --no-browser      # 브라우저 자동 열기 생략
python -m stele --help            # 사용법
```

Stele Studio는 로컬 전용 인터페이스로, 다음 기능을 단일 화면에서 제공한다:
- **VERIFY** — 증명 편집기 + 논리 선택 + 즉시 판정
- **DIAGNOSTICS** — 다중 패스 구조적 진단 (UndefinedSymbol, MissingHypothesis 등)
- **GRAPH** — 증명 의존성 그래프 시각화 + DOT 출력
- **METRICS** — 벤치마크 평가 리포트 (`bench/reports/latest.json`)
- **PLURALISM** — 규칙 건전성 · 세계 격자 · 다치 진리표 플레이그라운드

외부 의존성 없음. 인증·데이터베이스·클라우드 없음.

### CLI 명령 (자동화·스크립트용)

```bash
python -m stele.cli check examples/dne.stele --logic classical_prop
python -m stele.cli check examples/dne.stele --logic intuitionistic_prop
python -m stele.cli check examples/matrix_k3.stele --logic K3      # 행렬 모드
python -m stele.cli soundness --logic classical_prop --matrix K3   # 규칙 건전성
python -m stele.cli lattice "P or Q"                               # 세계 격자 데모
python -m stele.cli kripke "P or not P"                            # 크립키 반례 (v1.1)
python -m stele.cli cert examples/dne.stele --logic classical_prop # 인증서 방출 (v1.1, Experimental)
python -m stele.cli state examples/dne.stele                       # 증명 상태 (v1.1, Untrusted)
python -m stele.cli demos
python -m pytest -q
```

## Limitations (v1.2)

- **Stele-Light remains propositional** — the proof-script language does not support first-order quantifiers (`forall`, `exists`) at the surface level. The proof-term core (`stele.core`) has an experimental FOL fragment, but FOL proof scripts are not yet supported.
- **Proof checker, not prover** — Stele does not search for proofs. The user writes every step; the kernel checks them.
- **Relativity = rule availability** — the kernel shows that a proof using `dne` fails in `intuitionistic_prop` because the rule is absent. Semantic non-derivability requires matrix/Kripke semantics (separate module).
- **Kripke countermodel search is bounded** — `find_countermodel()` searches ≤4 worlds by default. Absence of a countermodel is not a proof of intuitionistic validity (no completeness theorem implemented).
- **Certificates and minicheck are experimental** — minicheck is an independent Python code path, not a separate process or formally verified checker. It shares the same Python runtime as the main kernel.
- **Proof-state hints are UNTRUSTED** — structural suggestions only; no proof search; all hints must be kernel-rechecked before use.
- **Metatheory is documented, not machine-checked** — `docs/metatheory.md` records proof sketches and regression/property tests. These are not machine-verified (Lean/Coq/Agda) proofs.
- **Single-file HTML requires internet (v1.1)** — `stele.html` loads Pyodide from CDN (~8 MB, cached after first load). A fully offline mode is future work.
- **ML baseline and Lean bridge are optional/experimental** — isolated outside the trusted checking path; measured metrics cover the generated synthetic corpus only.

## Development

Requirements: Python 3.10+, `pytest` (test-only dependency, no runtime deps).

```bash
# Run the test suite
python -m pytest -q

# Launch Stele Studio (local web interface)
python -m stele

# Or use the legacy web server entry point
python -m stele.web

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
```

CI runs on every push and pull request via GitHub Actions (`.github/workflows/ci.yml`), testing Python 3.10–3.12.

## Stele Studio

`python -m stele` launches Stele Studio, a local web interface (default port 8000). It is not hosted or deployed — it runs entirely on your machine and requires no internet connection. The trusted kernel (`stele/kernel.py`) remains the sole authority for proof validity; the Studio is an untrusted interface layer that calls the same Python modules as the CLI.

Web API endpoints (all local, no auth):
- `POST /api/check` — proof verification
- `POST /api/diagnose` — structural diagnostics
- `POST /api/graph` — dependency graph + DOT
- `GET /api/soundness?logic=...&matrix=...` — rule soundness report
- `GET /api/lattice?formula=...` — CH-style world lattice
- `GET /api/metrics` — benchmark report from `bench/reports/latest.json`

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
  __main__.py  python -m stele 진입점 (Stele Studio 실행)
  ast.py      식 표현(연결사 무지) + 출력기
  proof.py    증명 노드 + MatrixDirective
  parser.py   직접 구현한 토크나이저 + 재귀하강 파서
  logic.py    RuleSchema, Logic, MatrixLogic; 내장 논리(고전/직관/K3/LP/boolean)
  kernel.py   신뢰 코어: 매처 + 증명트리 검사 (proof 모드)
  matrix.py   다치 의미론: Matrix, K3/LP/boolean, 평가·항진성·귀결·고정점·건전성
  world.py    World(matrix, axioms) + status(PROVABLE/REFUTABLE/BOTH/INDEPENDENT) + lattice_status
  cli.py      check / soundness / lattice / graph / diagnose / demos
  web.py      Stele Studio HTTP 서버(stdlib) + JSON API 엔드포인트
  webapp/index.html  Stele Studio 단일 파일 프런트엔드
examples/     증명·행렬·세계 예제 (.stele + .py)
tests/        2,390+ 통과 (4 skipped without Hypothesis)
```

## 구현된 것 / 로드맵

**v1.2 구현 (전체 목록):**
- 자연연역 증명검증기 (proof 모드, 커널 신뢰 코어)
- 공통 명제 규칙 전체 + 고전 전용 규칙 (`dne`, `lem`, `pbc`) + 상대성 데모
- 다치 의미론 (K3, LP, boolean) + 행렬 모드 + 규칙 건전성 + 세계 격자 데모
- 유한 크립키 의미론 (직관 명제 논리, bounded search) — Experimental
- 증명항 코어 (Curry–Howard) + 스크립트 정교화 + β-환원 + de Bruijn
- 실험적 1차 논리 단편 (ForallIntro/Elim/ExistsIntro/Elim, proof-term 층) — Experimental
- 실험적 고전 증명항 브릿지 (Gödel–Gentzen 이중부정 번역) — Experimental
- 증명 인증서 + 소형 독립 검사기 (minicheck) — Experimental
- 증명 상태 스냅샷 + 구조적 규칙 힌트 (UNTRUSTED) — Experimental
- ML 기준선 (`stele_ml/`, optional, experimental) + 3-분할 + 벤치마크 카드
- Lean 4 브릿지 (`stele_lean/`, optional, experimental) + 기술 백서

**v1.3+ 후보 로드맵:**
- Stele-Light 표면에 FOL 한정사 (`forall`, `exists`) 추가
- 구조 규칙 정책 (약화·축약 제거 → 선형·관련성·초일관 세계)
- Lean 브릿지 고도화 (Lean 4 export 범위 확대)
- 커널 Rust/OCaml 포팅 (sum type + 망라적 패턴매칭)
- Minicheck Rust/OCaml 독립 포팅 (프로세스 수준 격리)
- FOL 의미론 + proof-term 층 객체 변수 de Bruijn 완성
- 기계 검증 메타이론 (Lean/Coq/Agda export) — 먼 미래
