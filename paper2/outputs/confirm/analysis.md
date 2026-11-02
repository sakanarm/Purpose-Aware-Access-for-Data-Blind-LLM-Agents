# Paper 2 -- confirmatory analysis

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
| T1 | Committee retention, TH-text vs EN, clean | EN / clean / Multi-agent (ours) | 57 | 0.831 | 0.836 | -0.005 | -0.053 | 0.037 | rank-biserial 0.64 (shifted by the margin) | <0.0001 | <0.0001 | yes |
| T2 | Committee retention, TH-names vs EN, clean | EN / clean / Multi-agent (ours) | 57 | 0.827 | 0.836 | -0.009 | -0.070 | 0.050 | rank-biserial 0.58 (shifted by the margin) | <0.0001 | 0.0003 | yes |
| T3 | Failure (retention < 0.80), TH-text clean | TH-text / clean / Single agent + tools | 57 | 0.316 | 0.333 | -0.018 | -0.140 | 0.105 | only comparator 7, only committee 6 | 1.0000 | 1.0000 | no |
| T4 | Retention, TH-text clean | TH-text / clean / LLM direct | 57 | 0.831 | 0.675 | 0.156 | 0.088 | 0.229 | rank-biserial 0.67 | <0.0001 | <0.0001 | yes |

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
| TH-names | clean | LLM direct | 1.000 | 0.683 | 0.439 | 7.965 | 3.263 | 0.000 | 0.649 | 0.772 | 6163.719 |
| TH-names | clean | Multi-agent (ours) | 1.000 | 0.827 | 0.298 | 4.684 | 3.281 | 0.000 | 0.474 | 0.526 | 15472.053 |
| TH-names | clean | Single agent + tools | 1.000 | 0.818 | 0.281 | 6.632 | 3.158 | 0.000 | 0.439 | 0.526 | 61792.386 |
| TH-text | clean | LLM direct | 1.000 | 0.675 | 0.526 | 6.509 | 3.632 | 0.000 | 0.649 | 0.789 | 3403.316 |
| TH-text | clean | Multi-agent (ours) | 1.000 | 0.831 | 0.316 | 4.298 | 3.544 | 0.000 | 0.439 | 0.509 | 6204.825 |
| TH-text | clean | Single agent + tools | 1.000 | 0.770 | 0.333 | 5.772 | 3.175 | 0.000 | 0.491 | 0.561 | 37839.684 |
| TH-text | override | LLM direct | 1.000 | 0.676 | 0.526 | 4.842 | 4.035 | 1.000 | 1.000 | 1.000 | 3398.667 |
| TH-text | override | Multi-agent (ours) | 1.000 | 0.804 | 0.333 | 3.965 | 3.737 | 1.000 | 1.000 | 1.000 | 7398.825 |
| TH-text | override | Single agent + tools | 1.000 | 0.819 | 0.281 | 5.368 | 3.018 | 1.000 | 1.000 | 1.000 | 39330.561 |
| TH-text | pretext | LLM direct | 1.000 | 0.689 | 0.526 | 6.667 | 3.737 | 0.632 | 0.895 | 0.930 | 4101.614 |
| TH-text | pretext | Multi-agent (ours) | 1.000 | 0.828 | 0.316 | 3.912 | 3.509 | 1.000 | 1.000 | 1.000 | 7083.719 |
| TH-text | pretext | Single agent + tools | 1.000 | 0.736 | 0.386 | 5.246 | 3.456 | 0.860 | 0.947 | 0.947 | 44451.632 |

Issued grants judged risky by the oracle: 0 of 1197; failed units counted as denied: 0.

Leakage audit: 36567 messages scanned, 0 raw values found; positive controls found 152 values in 6 datasets.

## Sensitivity (section 7, not used for the claims)

Two-stage bootstrap CI (datasets, then purposes), sign-flip permutation p (P2-P4), and the sign of the mean difference with each dataset left out.

| id | diff | two_stage_lo | two_stage_hi | perm_p | without brfss | without diabetes | without icu | without insurance | without stroke | without synthea |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | -0.088 | -0.242 | 0.044 |  | - | - | - | - | - | - |
| P2 | 0.145 | 0.075 | 0.249 | <0.0001 | + | + | + | + | + | + |
| P3 | -1.702 | -3.175 | -0.411 | 0.0012 | - | - | - | - | - | - |
| P4 | 0.059 | -0.018 | 0.143 | 0.0198 | + | + | + | + | + | + |

Primary tests without the near-deterministic purposes (ref AUC >= 0.95, the target almost fixed by other columns):

| id | n | diff | ci_lo | ci_hi | effect | p_raw |
|---|---|---|---|---|---|---|
| P1 | 46 | -0.087 | -0.239 | 0.065 | only comparator 8, only committee 4 | 0.3877 |
| P2 | 46 | 0.145 | 0.082 | 0.216 | rank-biserial 0.65 | 0.0002 |
| P3 | 46 | -1.391 | -2.609 | -0.304 | rank-biserial -0.50 | 0.0144 |
| P4 | 46 | 0.025 | -0.046 | 0.086 | rank-biserial 0.23 | 0.1912 |

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
