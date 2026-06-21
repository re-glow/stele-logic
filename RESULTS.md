# 실행 결과 (실제 출력 캡처)

환경: Python 3.12, 런타임 의존성 없음. 2026-06.

## 테스트

```
215 passed in 0.45s
```

## 상대성: 같은 증명, 두 세계

```
$ python -m stele.cli check examples/dne.stele --logic classical_prop
OK Proof verified: dne_consequent   [logic: classical_prop]

$ python -m stele.cli check examples/dne.stele --logic intuitionistic_prop
X Proof failed: dne_consequent (line 3)
  rule 'dne' is not available in logic 'intuitionistic_prop'
```

LEM과 pbc도 동일하게 거부됨:

```
$ python -m stele.cli check examples/lem.stele --logic classical_prop
OK Proof verified: lem_demo   [logic: classical_prop]

$ python -m stele.cli check examples/lem.stele --logic intuitionistic_prop
X Proof failed: lem_demo (line 2)
  rule 'lem' is not available in logic 'intuitionistic_prop'
```

## 행렬 모드 표면 문법

```
$ python -m stele.cli check examples/matrix_k3.stele --logic K3
line 2:  evaluate P or not P  =>  I
line 3:  tautology? P or not P  =>  no  (counterexample: {'P': 'I'})
line 5:  fixpoint not  =>  {I}
```

## 규칙 건전성 보고 (일부)

```
$ python -m stele.cli soundness --logic classical_prop --matrix K3
soundness  [logic: classical_prop | matrix: K3]
  and_elim_left: sound
  ...
  dne: sound
  lem: unsound  counterexample: A=I
  mp: sound
  ...
  neg_elim: sound
```

## 세계 격자 / CH-스타일 독립성 패턴

```
$ python -m stele.cli lattice x
lattice  [formula: x | matrix: boolean]
  Gamma                       axioms: []                =>  INDEPENDENT
  Gamma + x                   axioms: [x]               =>  PROVABLE
  Gamma + not x               axioms: [not x]           =>  REFUTABLE
```

x는 기저 세계에서 독립적이지만 공리를 하나 추가하면 즉시 해결된다.
이것은 명제 수준의 장난감 독립성 패턴이며 집합론적 CH·강제법이 아니다.

## 다치 의미론 데모

```
$ python -m stele.cli demos
----------------------------------------------------------------
다치 의미론 데모 - 유리학의 |= 측면 (진리치 I/B, 무모순율의 국소성)
----------------------------------------------------------------
[배중률]   P or not P 가 항진식인가?
           K3: False     고전: True
           -> K3에서 P=I 이면 (P or not P) = I  (designated 아님)

[거짓말쟁이] L = not L 의 고정점 (not v = v):
           K3: ['I']   -> 진리치 I (정의되지 않음)
           LP: ['B']   -> 진리치 B (참이면서 거짓)

[폭발원리]  {P, not P} |= Q 가 성립하는가?
           LP:   False   (반례 평가: {'P': 'B', 'Q': 'F'})
           고전: True
           -> LP에서는 모순을 허용해도 임의 명제로 폭발하지 않는다 (초일관).
----------------------------------------------------------------
```

## 증명 오류 보고

```
$ python -m stele.cli check examples/invalid_mp.stele --logic classical_prop
X Proof failed: bad_mp (line 4)
  rule 'mp': premise 2 expected P, but 'h2' is R

$ python -m stele.cli check examples/invalid_scope.stele --logic classical_prop
X Proof failed: leak (line 6)
  unknown reference 'h2'
```
