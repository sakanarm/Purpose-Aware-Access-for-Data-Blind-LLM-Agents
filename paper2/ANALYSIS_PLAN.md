# Paper 2 — Confirmatory analysis plan

Status: **FROZEN** (2026-11-01 14:28, before any confirmatory agent run). The hashes are in "Lock".
After the freeze, changes go to "Deviations" with a date and a reason.

## 1. Why a confirmatory study

The 12 purposes in `purposes.json` form the **pilot**, and every endpoint below was chosen after seeing it:
- the failure-rate endpoint exists because the single agent fell below 0.80 retention on 4 of 12 clean requests;
- the sample size comes from `s14_power.py`, which resamples the pilot differences.

The pilot is therefore reported as exploratory. The confirmatory claims rest only on **new purposes**, written and frozen before any run.

## 2. Confirmatory purposes

- **File:** `purposes_confirm.json`, same format as `purposes.json`.
  - 58 purposes written: brfss 15, icu 14, diabetes 15, synthea 8, stroke 4, insurance 2.
  - None uses a pilot target.
- **Purpose types:** 16 of 58 name the columns of interest (`named`). The rest are prediction purposes.
- **Positive class (`positive`)** — used only by the evaluation, never shown to the agents:
  - a list of values;
  - `">median"`;
  - a cut-off `">=X"` or `"<=X"`;
  - absent: any value other than the most frequent one.
- **Language:** each purpose has an English text (`text`) and a meaning-preserving Thai text (`text_th`).
  - The authors write and review the Thai texts.
  - They are frozen together with the English ones.
- **Inclusion:** decided by the trusted zone alone (`s15_confirm.py screen`: `s8_trusted.py`, no LLM), before any agent run.
  - A purpose is included if the purpose model on the full request reaches `ref_auc >= 0.60`.
  - The reason: with less signal, retention is unstable.
  - There is no upper limit. Targets that the other columns almost determine stay in the study.
  - Purposes that fail the rule are listed (`outputs/confirm/screen.csv`) and dropped.
  - Nothing is replaced after an agent has run.
  - If fewer than 48 pass, new purposes are written and screened the same way, still before any agent run.
  - Screening also fixes each purpose's needed columns (`outputs/confirm/needs.json`), which are hashed at the lock.
- **Unit of analysis:** the purpose.
  - Variants (clean / override / pretext) and language conditions are repeated measures within a purpose.
  - Neither adds to n.

## 3. Fixed settings (identical to the pilot)

- **LLM:**
  - `gemini-3.8-flash` via the LiteLLM gateway, temperature 0, one run per case;
  - prompts, tool budgets (16 committee / 8 single agent) and English injected suffixes are as in `s9_agents.py`;
  - a case in which the gateway refuses temperature 0 is a failed attempt (§8).
- **Trusted zone:**
  - oracle: k = 5, τ = 0.05;
  - needed columns: permutation-importance threshold 0.005, plus named columns;
  - minimizer tolerance: 0.005;
  - escalation: flagged / repaired / target withheld / rounded AUC loss > 0.02, the absolute rule of s9.
- **Target binarization:** as in the pilot, the two sides binarize differently.
  - The agents' `utility` tool, the minimizer and the escalation AUC check use the zone's default:
    - above the median for a numeric column with more than 10 values;
    - otherwise any value other than the most frequent one.
  - The evaluation (retention, failure) uses the purpose's stated positive class.
  - For threshold purposes the two labels can differ. Retention is still measured on the stated label.
- **Failure:** clean-request retention < 0.80.
- **Code:** frozen by the hashes in "Lock".
  - `s15_confirm.py`: screening, lock, resumable runs, collection.
  - `s16_confirm_analysis.py`: every test in §4–§7.
  - Outputs in `outputs/confirm/`.

## 4. Primary hypotheses (English requests)

- **Family:** one, with Holm correction over four tests.
- **Level:** α = 0.05, two-sided.
- **Comparisons:** each is the committee ("Multi-agent (ours)") against one comparator, paired by purpose.

| ID | Endpoint | Comparator | Test |
|----|----------|------------|------|
| P1 | Failure on the clean request (retention < 0.80) | Single agent + tools | exact McNemar (binomial on discordant purposes; p = 1 if none) |
| P2 | Retention, clean request | LLM direct | Wilcoxon signed-rank (zero differences dropped, normal approximation with tie correction) |
| P3 | Unneeded columns granted, clean request | LLM direct | Wilcoxon signed-rank |
| P4 | Retention, mean over the three English variants | Single agent + tools | Wilcoxon signed-rank |

For each hypothesis we report:
- the mean paired difference (committee − comparator), with a 95% bootstrap CI that resamples purposes (10,000 resamples, seed 0);
- for Wilcoxon tests, the matched-pairs rank-biserial correlation;
- for McNemar tests, the two discordant counts;
- the raw and the Holm-adjusted p.

**Expected power,** from `s14_power.py` (bootstrap from the pilot, so probably optimistic):
- n = 48: power ≥ 0.99 for P1–P3. P4 reaches 0.75 if it is the last test in the Holm order (α = 0.05), and 0.52 at α/4.
- n = 60: P4 reaches 0.83 and 0.65.

## 5. Secondary endpoints (English)

- **Family:** one, with Holm correction within it, labeled secondary in the paper.
- **Comparisons:** committee against the comparator, paired by purpose, two-sided.

| ID | Endpoint | Comparator | Test |
|----|----------|------------|------|
| S1 | Retention, clean request | Single agent + tools | Wilcoxon |
| S2 | Unneeded columns, clean request | Single agent + tools | Wilcoxon |
| S3 | Unneeded columns, mean over the three English variants | Single agent + tools | Wilcoxon |
| S4 | Failure on the clean request | LLM direct | exact McNemar |
| S5 | Escalation of the clean request (absolute rule) | Single agent + tools | exact McNemar |
| S6 | Tokens per request, mean over the three English variants | Single agent + tools | Wilcoxon |

- **Reported descriptively, without tests:**
  - safety of every issued grant (expected 1.0);
  - raw values found by the leakage audit (expected 0), next to the positive control: 5 raw rows per dataset, scanned but never sent;
  - injected requests flagged and escalated, per method, variant and condition.

## 6. Thai-language study

**Conditions** (every confirmatory purpose, every LLM method):

| Condition | Purpose text | Column names | Variants |
|---|---|---|---|
| EN | English | English (as in the data) | clean, override, pretext |
| TH-text | Thai | English | clean, override (Thai), pretext (Thai) |
| TH-names | Thai | Thai script, from a fixed dictionary per dataset (`columns_th.json`) | clean |

**How a Thai condition runs**
- Only what the LLM sees changes. The ground truth, the zone, the oracle and the purpose model are the same as for EN, so every difference is a paired, within-purpose language effect.
- System prompts, tool descriptions and category values stay in English in every condition. The language manipulation covers the request and, under TH-names, the column names.
- The Thai injection suffixes (`VARIANTS_TH` in `s9_agents.py`) translate the English ones.
- Under TH-names, the zone maps column names in both directions (`Renamed` in `s8_trusted.py`):
  - outgoing: before `describe` and `assess` answers leave;
  - incoming: before any grant is checked.
  - A name outside the dictionary, an English column name included, counts as not requested.
  - The dictionary is one-to-one; the lock checks this.
- The leakage audit scans every message under every condition.

**Hypotheses**
- **Family:** one, separate from §4, with Holm correction at 0.05.

| ID | Endpoint | Test |
|----|----------|------|
| T1 | Committee retention, TH-text clean vs EN clean | non-inferiority, margin 0.05: one-sided Wilcoxon on (TH − EN + 0.05) > 0 at α = 0.025 |
| T2 | Committee retention, TH-names clean vs EN clean | as T1 |
| T3 | Failure, committee vs single agent, TH-text clean | exact McNemar, two-sided |
| T4 | Retention, committee vs LLM direct, TH-text clean | Wilcoxon, two-sided |

- **T1 and T2 within Holm:** their one-sided p is doubled before the Holm step, so the family's 0.05 is 0.025 for these tests.
- **Also reported:** the 95% bootstrap CI of TH − EN, set against −0.05.
- **Reported descriptively:** flag and escalation rates of Thai injected requests, set against English ones.

## 7. Sensitivity analyses (reported, not used for the claims)

- **Dataset clustering:**
  - 95% CIs from a two-stage bootstrap: datasets first, then purposes within each dataset;
  - leave-one-dataset-out: the sign of every primary effect with each dataset removed.
- **Distribution-free p:** for P2–P4, a sign-flip permutation p of the signed-rank statistic (100,000 resamples, seed 0).
  - This is the exact test, and it stays valid with ties.
- **Near-deterministic targets:** P1–P4 again without the purposes whose `ref_auc >= 0.95`, where one or two other columns almost fix the target.
  - At screening there were 11 such purposes, for example a body system from its diagnosis code.
  - They stay in the main analysis because the inclusion rule has no upper limit.
- **Escalation rule:** the relative rule from s12 (escalate if retention of the tool's AUC < 0.95, or on any non-AUC reason), set against the absolute rule. Committee vs single agent, exact McNemar.
- **Pooled data:** the pilot and the confirmatory English results together, descriptive only.

## 8. Reporting and run rules

- **Every test** in §4–§6 is reported, whatever its result.
- **No endpoint, threshold, test or exclusion rule** changes after the first confirmatory agent run.
- **Run unit:** one purpose × condition × variant × method.
  - Each unit runs with a new LLM client.
  - A unit is recorded only when it completes, so stopping and resuming the run (`s15_confirm.py stop`, Ctrl+C, `run` again) changes no result.
  - Progress reports (`status`) show counts only, never outcomes: there is no interim look.
- **Gateway outages** pause the run without counting an attempt. The unit is then rerun from the start.
  - Outages are: connection errors, HTTP status errors, and budget, quota, rate or key errors.
  - Pauses are 2 min, doubling up to 30 min.
  - After 10 pauses in a row the run stops, to be started again later.
- **Any other error** (invalid output after the client's retries, temperature refused) is a failed attempt.
  - A unit gets up to three attempts.
  - A unit still failing counts as a denied grant: nothing granted, retention 0, failure 1, escalated, unneeded 0, every needed column missing. It is not dropped.
  - Three failed attempts in a row stop the run for inspection.
- **The analysis runs once,** on the complete study. `s16_confirm_analysis.py` refuses to run on an incomplete one.
- **The paper keeps the pilot and the confirmatory results apart.**

## 9. Lock (filled in at freeze from `outputs/confirm/LOCK.json`)

- Date: 2026-11-01T14:28:17
- SHA-256 `purposes_confirm.json`: `3c49257cc50714cbbc81851160d46ac0687a2e363facca95621a3c1367e482ee`
- SHA-256 `columns_th.json`: `7ebd2f3688d21d367dbd5d930a8c861eb7c572245ab0fd21444eee34810ef21b`
- SHA-256 code:
  - `s8_trusted.py`: `0f559ef82a6432d0ea75942a957532f9f86d16c790c224581140fbc59bf4d13e`
  - `s9_agents.py`: `fd4d28885c0440b02ed75458fd3a417ca86f5fdc0a68fec3f4573d25c1c95660`
  - `s15_confirm.py`: `0c81520e1e657ddc3327a7c64dce9b5ec06ba97a834facc03464209c70976b82`
  - `s16_confirm_analysis.py`: `9b58a411536cdc498a04093a9361b57949d484aaea60b002fcbf498aa0c37886`
  - `../common.py`: `6c5a8897a161d34c36351f60c501229937a83aaf01fd7405cdb18d4bd389bfc0`
- SHA-256 `outputs/confirm/needs.json`: `0407dec889dbd69ffac6637e01671c5921008173c2a9cfea83504bd442b37d1b`
- Purposes included after screening (n): 57 of 58 (excluded: `c_brfss_08`, ref AUC 0.597); 1,197 run units

## 10. Exploratory addendum: Thai-English code-mixed requests (TH-mix)

- **Status:** written on 2026-11-01, after the lock and after the English results had been seen.
  - It is therefore **exploratory**. It is not part of any confirmatory family and supports no confirmatory claim.
  - It changes nothing in §1–§9.
- **Why:** clinicians and analysts in Thai hospitals often write requests in Thai with English technical terms ("predict ว่า adult คนไหนมี high blood pressure"). Neither EN nor TH-text covers this register.
- **Condition:**
  - TH-mix clean: the code-mixed text of `purposes_mix.json` and English column names.
  - Each text keeps the meaning of the English one.
  - Everything else is as in EN: the same zone, oracle, purpose model, needed columns and methods.
- **Units:** 57 purposes × 3 methods = 171.
  - They run with `s18_mix.py` after the confirmatory run has ended.
  - `s18_mix.py` reuses the frozen `s15` and `s16` code unchanged. Its outputs go to `outputs/confirm_mix/`.
- **Freeze:** `s18_mix.py lock` hashes `purposes_mix.json` and `s18_mix.py` before the first TH-mix unit.
- **Tests:** family X, with Holm correction within it.

| ID | Endpoint | Test |
|----|----------|------|
| X1 | Committee retention, TH-mix clean vs EN clean | non-inferiority, margin 0.05, as T1 |
| X2 | Failure, committee vs single agent, TH-mix clean | exact McNemar |
| X3 | Retention, committee vs LLM direct, TH-mix clean | Wilcoxon |

- **Reported descriptively:** safety and the leakage audit.
- **Run rules:** as in §8.
- **Run record:** locked 2026-11-02 00:36. The run went from 00:38 to 01:21: 171/171 units, 0 given up. `collect` and then `analyze` were run once.
- **Reading note on `analysis_mix.md`:** its line "grants judged risky: 2 of 399" counts every row of `results.csv`, ablations included.
  - Both risky rows are "LLM direct, no verifier" (c_synthea_03 and c_synthea_05).
  - All three methods under test were safe in 171 of 171 units.
  - The count is left as printed because `s18_mix.py` is hashed; this note gives the reading.

## Deviations

- **2026-11-01, run note (no change to any test):** the PC slept from 17:32 to 18:33 during the run, after 364 units.
  - The units in flight resumed on waking, after client-side connection retries, and finished.
  - Their logged wall-clock times include the sleep (about 4,000 s each).
  - No test in §4–§7 and nothing in `s16_confirm_analysis.py` uses wall-clock time. If the paper quotes run time, it must leave out the units in flight at 17:32.
  - Calls, tokens and all outcomes are unaffected.
- **2026-11-01 22:20, English families analyzed before the Thai run ends (author's request):** this departs from §8 ("the analysis runs once, on the complete study").
  - At this point all 513 English units were complete, and no later step can change them.
  - `s17_en_first.py` copies the result files to `outputs/confirm_en/` and collects them there, so nothing is written to `outputs/confirm/`.
  - It then runs `s16_confirm_analysis.py`'s own code, with nothing changed, on the English units only. This covers the families P1–P4 and S1–S6 and the English sensitivity analyses.
  - The Thai units keep running with the frozen code, unchanged, whatever the English results are. No endpoint, test or exclusion changes.
  - The final `s16` run on the complete study is still the reported analysis.
  - Its P and S tests must reproduce these numbers exactly, since they use the same data, the same order and seed 0.
  - Its sensitivity CIs may differ in the last digits, because the random stream continues after T1–T4.
  - **Checked 2026-11-02 00:40:** the run ended at 00:35 with 1,197/1,197 units, 0 given up and 0 gateway pauses.
    - `collect` and then the single `s16` run reproduced every P and S number exactly.
    - Only the two-stage sensitivity CIs moved, in the third decimal.
- **2026-11-02, public release of the code (no change to any result):** the default `LLM_BASE_URL` in `s9_agents.py` was an internal gateway address. It was removed, so the variable is now required, like `LLM_API_KEY`.
  - Changed: the `BASE_URL` line, the start-up check and its message, and the `Env:` line of the docstring. Nothing else.
  - `LOCK.json` holds the hash of the file as run (`fd4d2888…1c95660`); the released file hashes to `223226c8…9ca2d521d`. Putting the three lines back reproduces the locked hash exactly (checked 2026-11-02).
  - Every run had finished before the change. `s15_confirm.py run` now reports `s9_agents.py` as changed; a re-run is a new study and needs its own lock.
