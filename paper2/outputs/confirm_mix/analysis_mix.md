# Paper 2 -- exploratory TH-mix condition (plan section 10, not confirmatory)

n = 57 purposes; a = committee (or TH-mix for X1), b = comparator; diff = a - b.

| id | hypothesis | b | n | mean_a | mean_b | diff | ci_lo | ci_hi | effect | p_raw | p_holm | significant |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 | Committee retention, TH-mix vs EN, clean | EN / clean / Multi-agent (ours) | 57 | 0.817 | 0.836 | -0.019 | -0.065 | 0.021 | rank-biserial 0.61 (shifted by the margin) | <0.0001 | 0.0001 | yes |
| X2 | Failure (retention < 0.80), TH-mix clean | TH-mix / clean / Single agent + tools | 57 | 0.368 | 0.333 | 0.035 | -0.088 | 0.158 | only comparator 5, only committee 7 | 0.7744 | 0.7744 | no |
| X3 | Retention, TH-mix clean | TH-mix / clean / LLM direct | 57 | 0.817 | 0.697 | 0.120 | 0.073 | 0.173 | rank-biserial 0.73 | <0.0001 | <0.0001 | yes |

## Clean requests, EN vs TH-mix (descriptive)

| cond | method | safe | retention | failure | unnecessary | missing_needed | escalated | tokens |
|---|---|---|---|---|---|---|---|---|
| EN | LLM direct | 1.000 | 0.691 | 0.491 | 5.842 | 3.877 | 0.737 | 3606.175 |
| EN | Multi-agent (ours) | 1.000 | 0.836 | 0.298 | 4.140 | 3.509 | 0.456 | 5557.123 |
| EN | Single agent + tools | 1.000 | 0.754 | 0.386 | 4.035 | 3.772 | 0.561 | 35695.228 |
| TH-mix | LLM direct | 1.000 | 0.697 | 0.509 | 6.333 | 3.754 | 0.667 | 3346.719 |
| TH-mix | Multi-agent (ours) | 1.000 | 0.817 | 0.368 | 4.228 | 3.614 | 0.491 | 5767.123 |
| TH-mix | Single agent + tools | 1.000 | 0.783 | 0.333 | 5.842 | 3.333 | 0.491 | 35425.772 |

TH-mix grants judged risky by the oracle: 2 of 399. Leakage audit: 5104 messages scanned, 0 raw values found.
