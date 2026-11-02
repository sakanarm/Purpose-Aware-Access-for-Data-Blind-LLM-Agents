# Data-Blind LLM Agents for Purpose-Aware Least-Privilege Access to Health Data

Code, frozen analysis plan and result files for the paper of the same title (manuscript in preparation).

A requester asks for a table and describes, in free text, what they want to do with it. A committee of LLM
agents decides the least data that purpose needs: which columns to grant, which to coarsen, and which to
withhold. **The agents never see a patient row.** The LLM gateway sits outside the hospital, so the agents
work only from column metadata and from the bucketed or aggregate answers of a trusted-zone Tool API. A
non-LLM verifier checks every grant against a re-identification oracle before it is issued. Grants that
lose purpose signal, or requests that carry instructions aimed at the access system, are escalated to an
administrator.

```
requester ──purpose text──▶  Purpose agent ─▶ Privacy agent ─▶ Purpose review     (LLM, outside the hospital)
                                   │  describe / assess / utility (narrowing only, budget, logged)
                                   ▼
                             Tool API ─▶ trusted zone: oracle (k = 5, τ = 0.05), purpose model   (inside)
                                   ▼
                             minimizer ─▶ non-LLM verifier (greedy repair) ─▶ grant or escalate ─▶ admin
```

## Repository layout

| Path | What it is |
|---|---|
| `s1_prepare.py` | Turns the public tables into a common format and writes `data_clean/<name>.pkl` + `catalog.json` |
| `common.py` | Shared data loading, semantic types, re-identification oracle settings |
| `data_clean/catalog.json` | Column catalogue: semantic type of every column (no values) |
| `paper2/s8_trusted.py` | Trusted zone and Tool API (`describe`, `assess`, `utility`); `Renamed` maps Thai column names |
| `paper2/s9_agents.py` | Agent committee, comparators (LLM direct, single agent with the same tools), verifier, leakage scan |
| `paper2/s10`–`s14` | Pilot: summary tables, simulated reviewer, relative escalation rule, minimizer ablation, power analysis |
| `paper2/s15_confirm.py` | Confirmatory study: screening, lock, resumable run, collect |
| `paper2/s16_confirm_analysis.py` | Confirmatory analysis exactly as pre-specified |
| `paper2/s17_en_first.py` | English families analysed before the Thai units finished (logged deviation) |
| `paper2/s18_mix.py` | Exploratory Thai–English code-mixed condition (added after the lock) |
| `paper2/fig_*.py` | Figures |
| `paper2/ANALYSIS_PLAN.md` | Pre-registered analysis plan (frozen 2026-11-01 14:28) with its deviations log |
| `paper2/purposes*.json`, `columns_th.json` | Pilot purposes, confirmatory purposes (English + Thai), code-mixed texts, Thai column names |
| `paper2/THAI_REVIEW.md` | Side-by-side English/Thai texts prepared for review before the lock |
| `paper2/outputs/` | Result files of every run (see below) |

## Setup

Python 3.12 and the packages in `requirements.txt`:

```bash
pip install -r requirements.txt
```

The LLM is reached through any OpenAI-compatible endpoint (the published runs used `gemini-3.8-flash`
behind a LiteLLM proxy, temperature 0):

| Variable | Meaning |
|---|---|
| `LLM_API_KEY` | API key for the endpoint (required for runs that call the LLM) |
| `LLM_BASE_URL` | Endpoint URL; set it to your own proxy |
| `LLM` | Model name (default `gemini-3.8-flash`) |
| `WORKERS` | Parallel units (default 4) |

Only metadata and Tool API answers are sent to the endpoint; patient rows stay in the local process.

## Data

The tables are public or synthetic but are not redistributed here. Download them into `data_raw/`:

| Folder in `data_raw/` | File(s) | Source |
|---|---|---|
| `brfss/` | `diabetes_012_health_indicators_BRFSS2015.csv` | CDC BRFSS 2015, prepared by A. Teboul — [Kaggle](https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset) |
| `diabetes130/` | `diabetic_data.csv` | Diabetes 130-US hospitals 1999–2008 — [UCI](https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008) |
| `icu/` | `dataset.csv` | WiDS Datathon 2020 ICU data, Kaggle subset “Patient Survival Prediction” (85 columns, 91,713 rows) |
| `insurance/` | `insurance.csv` | Medical cost personal dataset — [Kaggle](https://www.kaggle.com/datasets/mirichoi0218/insurance) |
| `stroke/` | `healthcare-dataset-stroke-data.csv` | Stroke prediction dataset — [Kaggle](https://www.kaggle.com/datasets/fedesoriano/stroke-prediction-dataset) |
| `synthea/csv/` | `patients.csv`, `encounters.csv`, `payers.csv`, `organizations.csv`, `conditions.csv`, `medications.csv` | Synthea CSV sample, April 2020 (1,171 patients) — [synthea.mitre.org/downloads](https://synthea.mitre.org/downloads) |
| `kaggle_healthcare/` | `healthcare_dataset.csv` | [Kaggle](https://www.kaggle.com/datasets/prasad22/healthcare-dataset); prepared by `s1_prepare.py` but not used in this paper |

```bash
python s1_prepare.py          # writes data_clean/*.pkl (BRFSS is sampled to 5,000 respondents, seed 0)
```

## Reproducing the results

All commands run from `paper2/`.

**Pilot** (12 purposes, `purposes.json`):

```bash
python s8_trusted.py          # needed columns and non-LLM baselines (no LLM)
python s9_agents.py           # committee and comparators, three request variants (LLM)
python s11_review.py          # simulated administrator review (no LLM)
python s12_escalation.py      # relative escalation rule, from the saved traces (no LLM)
python s13_minimizer.py       # minimizer ablation (no LLM)
python s10_summary.py         # paper tables
python s14_power.py           # power analysis for the confirmatory study
python fig_architecture.py; python fig_results.py
```

**Confirmatory study** (`ANALYSIS_PLAN.md`):

```bash
python s15_confirm.py screen      # ground truth and inclusion rule (ref AUC >= 0.60), no LLM
python s15_confirm.py lock        # writes outputs/confirm/LOCK.json (file hashes, included purposes)
python s15_confirm.py run         # 1,197 units; resumable: stop at any time and run again
python s15_confirm.py collect
python s16_confirm_analysis.py    # outputs/confirm/analysis.md and analysis_tests.csv
python s18_mix.py lock; python s18_mix.py run; python s18_mix.py collect; python s18_mix.py analyze
python fig_confirm.py
```

`s15_confirm.py run` refuses to start if any frozen file differs from the SHA-256 hashes in `LOCK.json`
(`s8_trusted.py`, `s9_agents.py`, `s15_confirm.py`, `s16_confirm_analysis.py`, `common.py`,
`purposes_confirm.json`, `columns_th.json`, `outputs/confirm/needs.json`). `.gitattributes` keeps the files
byte for byte so the hashes also verify on a fresh clone. One file differs on purpose: for this release the
internal gateway address was removed from `s9_agents.py` (three lines, logged under Deviations in
`ANALYSIS_PLAN.md`), so its hash no longer matches; the other seven do. A re-run is therefore a new study
with its own lock, and since it calls the LLM again its grants will not match ours exactly; the published
result files are in `outputs/`.

## Result files

| Folder | Contents |
|---|---|
| `paper2/outputs/` | Pilot: per-dataset grants (`agents_*.csv`), baselines, leakage counts, review/escalation tables, logs |
| `paper2/outputs/confirm/` | Confirmatory: `LOCK.json`, `screen.csv`, `needs.json`, `results_*.jsonl` (one line per unit), `results.csv`, `leakage.csv`, `analysis.md`, `analysis_tests.csv`, `run.log` |
| `paper2/outputs/confirm_en/` | Snapshot used for the English-first analysis |
| `paper2/outputs/confirm_mix/` | Exploratory code-mixed condition |
| `paper2/outputs/figures/` | Figures (PDF and PNG) |

The positive-control rows of `leakage.csv` and `leak_control.json` list a few raw values that the scan
detected in five local rows per dataset (never sent); they come from the public or synthetic tables above.
Not included: the full LLM traces (`*trace*.jsonl`, about 185 MB; available on request).

## Main confirmatory results

57 purposes, six datasets, 1,197 units, one model (`gemini-3.8-flash`). Retention is the share of the
purpose model's above-chance AUC kept by the grant; failure is retention below 0.8. Differences are
committee minus comparator with 95% bootstrap CIs over purposes; p-values are Holm-adjusted within their family.

| Test | Comparison | Difference (95% CI) | p (Holm) |
|---|---|---|---|
| P1 | failure rate vs single agent, clean (0.298 vs 0.386) | −0.088 (−0.211 to 0.035) | 0.27 (not confirmed) |
| P2 | retention vs LLM direct, clean | +0.145 (0.086 to 0.212) | < 0.0001 |
| P3 | unneeded columns granted vs LLM direct | −1.70 (−2.74 to −0.72) | 0.0047 |
| P4 | retention vs single agent, mean of three variants | +0.059 (−0.007 to 0.123) | 0.041 (CI includes 0) |
| S6 | tokens per request vs single agent, mean of three variants (5.7k vs 38.7k) | −33.0k (−36.1k to −29.9k) | < 0.0001 |

Thai conditions (committee retention, Thai minus English; non-inferiority margin −0.05):

| Test | Condition | Difference (95% CI) | p (Holm) |
|---|---|---|---|
| T1 | Thai purpose text | −0.005 (−0.053 to 0.037) | < 0.0001 |
| T2 | Thai purpose text and Thai column names | −0.009 (−0.070 to 0.050) | 0.0003 |
| X1 | Thai–English code-mixed text (exploratory) | −0.019 (−0.065 to 0.021) | 0.0001 |

The non-inferiority rank tests pass, but each bootstrap CI of the mean extends slightly beyond the margin.

Safety and leakage: 0 of 1,368 issued grants exceeded the re-identification threshold (the verifier repaired
14 grants, 13 of them from LLM direct); 0 raw values were found in 41,671 messages sent to the gateway, while
the positive control found 152.

## Citation

Paper in preparation; citation details will be added on publication.
