# 실행 결과 (실제 출력 캡처)

환경: Python 3.12.3, 런타임 의존성 없음.

## 테스트

```
...................                                                      [100%]
19 passed in 0.03s
```

## 상대성: 같은 증명, 두 세계

```
$ python -m stele.cli check examples/dne.stele --logic classical_prop
OK Proof verified: dne_consequent   [logic: classical_prop]

$ python -m stele.cli check examples/dne.stele --logic intuitionistic_prop
X Proof failed: dne_consequent (line 3)
  rule 'dne' is not available in logic 'intuitionistic_prop'

$ python -m stele.cli check examples/dne_law.stele --logic classical_prop
OK Proof verified: dne_law   [logic: classical_prop]

$ python -m stele.cli check examples/dne_law.stele --logic intuitionistic_prop
X Proof failed: dne_law (line 3)
  rule 'dne' is not available in logic 'intuitionistic_prop'
```

## 두 세계 모두에서 유효한 증명 / 오류 보고

```
$ python -m stele.cli check examples/valid_imp_chain.stele --logic intuitionistic_prop
OK Proof verified: chain   [logic: intuitionistic_prop]

$ python -m stele.cli check examples/invalid_mp.stele --logic classical_prop
X Proof failed: bad_mp (line 4)
  rule 'mp': premise 2 expected P, but 'h2' is R

$ python -m stele.cli check examples/invalid_scope.stele --logic classical_prop
X Proof failed: leak (line 6)
  unknown reference 'h2'
```

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
