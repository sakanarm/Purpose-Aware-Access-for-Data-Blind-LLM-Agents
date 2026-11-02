# Paper 2 -- confirmatory analysis, English units only (deviation 2026-11-01; the Thai family comes with the final s16 run)

Lock 2026-11-01T14:28:17, n = 57 purposes. a = committee (or the Thai condition for T1/T2), b = comparator; diff = a - b.

## Primary family (section 4)

| id | hypothesis | b | n | mean_a | mean_b | diff | ci_lo | ci_hi | effect | p_raw | p_holm | significant |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | Failure (retention < 0.80), clean | EN / clean / Single agent + tools | 57 | 0.298 | 0.386 | -0.088 | -0.211 | 0.035 | only comparator 9, only committee 4 | 0.2668 | 0.2668 | no |
| P2 | Retention, clean | EN / clean / LLM direct | 57 | 0.836 | 0.691 | 0.145 | 0.086 | 0.212 | rank-biserial 0.69 | <0.0001 | <0.0001 | yes |
| P3 | Unneeded columns, clean | EN / clean / LLM direct | 57 | 4.140 | 5.842 | -1.702 | -2.737 | -0.719 | rank-biserial -0.57 | 0.0016 | 0.0047 | yes |
| P4 | Retention, mean of the three variants | EN / mean / Single agent + tools | 57 | 0.828 | 0.769 | 0.059 | -0.007 | 0.123 | rank-biserial 0.36 | 0.0203 | 0.0406 | yes |

## Secondary family (section 5)

| id | hypothesis | b | n | mean_a | mean_b | diff | ci_lo | ci_hi | effect | p_raw | p_holm | significant |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | Retention, clean | EN / clean / Single agent + tools | 57 | 0.836 | 0.754 | 0.082 | 0.013 | 0.150 | rank-biserial 0.43 | 0.0063 | 0.0250 | yes |
| S2 | Unneeded columns, clean | EN / clean / Single agent + tools | 57 | 4.140 | 4.035 | 0.105 | -0.877 | 1.140 | rank-biserial -0.02 | 0.9200 | 0.9772 | no |
| S3 | Unneeded columns, mean of the three variants | EN / mean / Single agent + tools | 57 | 4.187 | 4.468 | -0.281 | -1.368 | 0.848 | rank-biserial -0.11 | 0.4886 | 0.9772 | no |
| S4 | Failure (retention < 0.80), clean | EN / clean / LLM direct | 57 | 0.298 | 0.491 | -0.193 | -0.316 | -0.088 | only comparator 12, only committee 1 | 0.0034 | 0.0171 | yes |
| S5 | Escalation, clean | EN / clean / Single agent + tools | 57 | 0.456 | 0.561 | -0.105 | -0.228 | 0.018 | only comparator 10, only committee 4 | 0.1796 | 0.5387 | no |
| S6 | Tokens per request, mean of the three variants | EN / mean / Single agent + tools | 57 | 5733.936 | 38739.503 | -33005.567 | -36071.318 | -29944.843 | rank-biserial -1.00 | <0.0001 | <0.0001 | yes |

## Thai family (section 6)

| id | hypothesis | b | n | mean_a | mean_b | diff | ci_lo | ci_hi | effect | p_raw | p_holm | significant |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Means per condition, variant and method (descriptive)

| cond | variant | method | safe | retention | failure | unnecessary | missing_needed | suspicious | escalated | escalated_rel | tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EN | clean | LLM direct | 1.000 | 0.691 | 0.491 | 5.842 | 3.877 | 0.000 | 0.737 | 0.842 | 3606.175 |
| EN | clean | Multi-agent (ours) | 1.000 | 0.836 | 0.298 | 4.140 | 3.509 | 0.000 | 0.456 | 0.544 | 5557.123 |
| EN | clean | Single agent + tools | 1.000 | 0.754 | 0.386 | 4.035 | 3.772 | 0.000 | 0.561 | 0.649 | 35695.228 |
| EN | override | LLM direct | 1.000 | 0.666 | 0.561 | 5.719 | 3.912 | 1.000 | 1.000 | 1.000 | 3274.228 |
| EN | override | Multi-agent (ours) | 1.000 | 0.820 | 0.351 | 4.018 | 3.614 | 1.000 | 1.000 | 1.000 | 5657.912 |
| EN | override | Single agent + tools | 1.000 | 0.770 | 0.333 | 4.456 | 3.667 | 1.000 | 1.000 | 1.000 | 36395.667 |
| EN | pretext | LLM direct | 1.000 | 0.706 | 0.509 | 6.333 | 3.825 | 0.930 | 0.982 | 0.982 | 3515.035 |
| EN | pretext | Multi-agent (ours) | 1.000 | 0.829 | 0.281 | 4.404 | 3.211 | 1.000 | 1.000 | 1.000 | 5986.772 |
| EN | pretext | Single agent + tools | 1.000 | 0.784 | 0.316 | 4.912 | 3.491 | 0.965 | 0.965 | 0.982 | 44127.614 |

Issued grants judged risky by the oracle: 0 of 513; failed units counted as denied: 0.

Leakage audit: 15978 messages scanned, 0 raw values found; positive controls found 152 values in 6 datasets.

## Sensitivity (section 7, not used for the claims)

Two-stage bootstrap CI (datasets, then purposes), sign-flip permutation p (P2-P4), and the sign of the mean difference with each dataset left out.

| id | diff | two_stage_lo | two_stage_hi | perm_p | without brfss | without diabetes | without icu | without insurance | without stroke | without synthea |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | -0.088 | -0.240 | 0.047 |  | - | - | - | - | - | - |
| P2 | 0.145 | 0.075 | 0.249 | <0.0001 | + | + | + | + | + | + |
| P3 | -1.702 | -3.154 | -0.381 | 0.0010 | - | - | - | - | - | - |
| P4 | 0.059 | -0.020 | 0.145 | 0.0194 | + | + | + | + | + | + |

Primary tests without the near-deterministic purposes (ref AUC >= 0.95, the target almost fixed by other columns):

| id | n | diff | ci_lo | ci_hi | effect | p_raw |
|---|---|---|---|---|---|---|
| P1 | 46 | -0.087 | -0.239 | 0.065 | only comparator 8, only committee 4 | 0.3877 |
| P2 | 46 | 0.145 | 0.081 | 0.216 | rank-biserial 0.65 | 0.0002 |
| P3 | 46 | -1.391 | -2.630 | -0.261 | rank-biserial -0.50 | 0.0144 |
| P4 | 46 | 0.025 | -0.044 | 0.087 | rank-biserial 0.23 | 0.1912 |

Escalation of clean English requests, absolute rule of s9 vs relative rule of s12 (0.95):

| method | escalated | escalated_rel |
|---|---|---|
| LLM direct | 0.737 | 0.842 |
| Multi-agent (ours) | 0.456 | 0.544 |
| Single agent + tools | 0.561 | 0.649 |

Relative rule, committee vs single agent: exact McNemar p = 0.2379 (only single 12, only committee 6).

Pilot + confirmatory pooled, English (descriptive only):

| method | retention | unnecessary | failure | scope | purposes |
|---|---|---|---|---|---|
| LLM direct | 0.705 | 6.304 | 0.493 | clean | 69 |
| Multi-agent (ours) | 0.855 | 4.159 | 0.246 | clean | 69 |
| Single agent + tools | 0.758 | 4.652 | 0.377 | clean | 69 |
| LLM direct | 0.701 | 6.343 | 0.512 | mean | 69 |
| Multi-agent (ours) | 0.846 | 4.208 | 0.266 | mean | 69 |
| Single agent + tools | 0.775 | 4.700 | 0.343 | mean | 69 |
