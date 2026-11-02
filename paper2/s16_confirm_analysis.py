"""Paper 2, step 16 - Confirmatory analysis exactly as in ANALYSIS_PLAN.md sections 4-7 (no LLM calls).

Input: outputs/confirm/results.csv and leakage.csv from "s15_confirm.py collect". Unit = purpose: per purpose
and method, the clean request or the mean over the three variants of a condition.
Tests (two-sided unless stated)
  Wilcoxon        signed-rank on the paired differences, zero differences dropped, normal approximation with
                  tie correction (scipy method="approx")
  McNemar         exact: binomial test on the discordant purposes (only one of the two fails)
  non-inferiority T1, T2: one-sided Wilcoxon on (TH - EN + 0.05) > 0 at 0.025; inside the Holm family its p is
                  doubled, so the family's 0.05 means 0.025 for the one-sided test
  Holm            within each family: primary P1-P4, secondary S1-S6, Thai T1-T4
Effects: mean paired difference (committee - comparator, or TH - EN) with a 95% bootstrap CI over purposes
(10,000 resamples) and the matched-pairs rank-biserial correlation (Wilcoxon) or the discordant counts (McNemar).
Sensitivity (section 7): two-stage bootstrap (datasets, then purposes within them), leave-one-dataset-out
signs, sign-flip permutation p of the signed-rank statistic (100,000 resamples) for P2-P4, P1-P4 without the
near-deterministic purposes (ref AUC >= 0.95), the relative escalation rule of s12, pilot + confirmatory pooled
(descriptive).
The script stops on an incomplete study: there is no interim analysis.
Output (outputs/confirm): analysis_tests.csv, analysis.md
usage: python s16_confirm_analysis.py
"""
import glob, json, os, sys
import numpy as np, pandas as pd
from scipy.stats import binomtest, rankdata, wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("CONFIRM_OUT", f"{HERE}/outputs/confirm")    # override only for testing the script
DIRECT, SINGLE, OURS = "LLM direct", "Single agent + tools", "Multi-agent (ours)"
METHODS = [DIRECT, SINGLE, OURS]
FAIL, MARGIN, B, PERM, ALPHA, NEAR = 0.80, 0.05, 10_000, 100_000, 0.05, 0.95
REQUESTS = {"EN": 3, "TH-text": 3, "TH-names": 1}


def spec(id, family, label, metric, a, b, test="wilcoxon"):
    """a, b = (condition, scope, method); scope "clean" or "mean" (of the condition's variants)."""
    return dict(id=id, family=family, label=label, metric=metric, a=a, b=b, test=test)


EN_C, EN_M, TH_C, THN_C = ("EN", "clean"), ("EN", "mean"), ("TH-text", "clean"), ("TH-names", "clean")
TESTS = [
    spec("P1", "primary", "Failure (retention < 0.80), clean", "failure", (*EN_C, OURS), (*EN_C, SINGLE), "mcnemar"),
    spec("P2", "primary", "Retention, clean", "retention", (*EN_C, OURS), (*EN_C, DIRECT)),
    spec("P3", "primary", "Unneeded columns, clean", "unnecessary", (*EN_C, OURS), (*EN_C, DIRECT)),
    spec("P4", "primary", "Retention, mean of the three variants", "retention", (*EN_M, OURS), (*EN_M, SINGLE)),
    spec("S1", "secondary", "Retention, clean", "retention", (*EN_C, OURS), (*EN_C, SINGLE)),
    spec("S2", "secondary", "Unneeded columns, clean", "unnecessary", (*EN_C, OURS), (*EN_C, SINGLE)),
    spec("S3", "secondary", "Unneeded columns, mean of the three variants", "unnecessary", (*EN_M, OURS), (*EN_M, SINGLE)),
    spec("S4", "secondary", "Failure (retention < 0.80), clean", "failure", (*EN_C, OURS), (*EN_C, DIRECT), "mcnemar"),
    spec("S5", "secondary", "Escalation, clean", "escalated", (*EN_C, OURS), (*EN_C, SINGLE), "mcnemar"),
    spec("S6", "secondary", "Tokens per request, mean of the three variants", "tokens", (*EN_M, OURS), (*EN_M, SINGLE)),
    spec("T1", "thai", "Committee retention, TH-text vs EN, clean", "retention", (*TH_C, OURS), (*EN_C, OURS), "noninf"),
    spec("T2", "thai", "Committee retention, TH-names vs EN, clean", "retention", (*THN_C, OURS), (*EN_C, OURS), "noninf"),
    spec("T3", "thai", "Failure (retention < 0.80), TH-text clean", "failure", (*TH_C, OURS), (*TH_C, SINGLE), "mcnemar"),
    spec("T4", "thai", "Retention, TH-text clean", "retention", (*TH_C, OURS), (*TH_C, DIRECT)),
]


# -------------------------------------------------------------------- statistics
def holm(p):
    p, adj, run = np.asarray(p, float), np.empty(len(p)), 0.0
    for i, j in enumerate(np.argsort(p)):
        run = max(run, min(1.0, (len(p) - i) * p[j]))
        adj[j] = run
    return adj


def wil(d, alternative="two-sided"):
    d = np.asarray(d, float)
    return float(wilcoxon(d, method="approx", alternative=alternative).pvalue) if np.any(d != 0) else 1.0


def rank_biserial(d):
    d = np.asarray(d, float)
    d = d[d != 0]
    if not len(d):
        return 0.0
    r = rankdata(np.abs(d))
    return float((r[d > 0].sum() - r[d < 0].sum()) / r.sum())


def mcnemar(a, b):
    """a, b binary per purpose (1 = event). Returns p, only-b count, only-a count."""
    only_b, only_a = int(np.sum((b == 1) & (a == 0))), int(np.sum((a == 1) & (b == 0)))
    return (float(binomtest(only_b, only_b + only_a).pvalue) if only_a + only_b else 1.0), only_b, only_a


def boot_ci(x, rng):
    m = x[rng.integers(0, len(x), (B, len(x)))].mean(1)
    return np.percentile(m, [2.5, 97.5])


def boot2_ci(x, ds, rng):
    groups = [x[ds == d] for d in np.unique(ds)]
    m = np.empty(B)
    for i in range(B):
        pick = rng.integers(0, len(groups), len(groups))
        m[i] = np.concatenate([groups[g][rng.integers(0, len(groups[g]), len(groups[g]))] for g in pick]).mean()
    return np.percentile(m, [2.5, 97.5])


def perm_p(d, rng):
    d = np.asarray(d, float)
    d = d[d != 0]
    if not len(d):
        return 1.0
    r = rankdata(np.abs(d))
    t = abs(np.sum(r * np.sign(d)))
    null = np.abs(rng.choice(np.array([-1.0, 1.0]), (PERM, len(r))) @ r)
    return float((np.sum(null >= t - 1e-9) + 1) / (PERM + 1))


# -------------------------------------------------------------------- data
def load():
    res = pd.read_csv(f"{OUT}/results.csv")
    lock = json.load(open(f"{OUT}/LOCK.json"))
    fin = res[res.method.isin(METHODS)].copy()
    fin["failure"] = (fin.retention < FAIL).astype(float)
    have = fin.groupby("purpose").size().reindex(lock["included"], fill_value=0)
    want = sum(REQUESTS.values()) * len(METHODS)
    if (have != want).any() or set(fin.purpose) - set(lock["included"]):
        sys.exit(f"s16: incomplete study, {int((have != want).sum())} purposes lack units; finish the run first")
    return fin, lock


def values(fin, cond, scope, method, metric):
    d = fin[(fin.cond == cond) & (fin.method == method)]
    if scope == "clean":
        d = d[d.variant == "clean"]
    return d.groupby("purpose")[metric].mean()


def run_test(fin, t, rng):
    a = values(fin, *t["a"], t["metric"])
    b = values(fin, *t["b"], t["metric"]).reindex(a.index)
    d = (a - b).to_numpy()
    lo, hi = boot_ci(d, rng)
    row = dict(id=t["id"], family=t["family"], hypothesis=t["label"], a=" / ".join(t["a"]), b=" / ".join(t["b"]),
               test=t["test"], n=len(d), mean_a=a.mean(), mean_b=b.mean(), diff=d.mean(), ci_lo=lo, ci_hi=hi)
    if t["test"] == "mcnemar":
        p, only_b, only_a = mcnemar(a.to_numpy(), b.to_numpy())
        row.update(effect=f"only comparator {only_b}, only committee {only_a}", p_raw=p, p_for_holm=p)
    elif t["test"] == "noninf":
        p = wil(d + MARGIN, "greater")
        row.update(effect=f"rank-biserial {rank_biserial(d + MARGIN):.2f} (shifted by the margin)", p_raw=p,
                   p_for_holm=min(1.0, 2 * p))
    else:
        p = wil(d)
        row.update(effect=f"rank-biserial {rank_biserial(d):.2f}", p_raw=p, p_for_holm=p)
    return row


def md(df, digits=3):
    df = df.copy()
    for c in df.columns:
        if c.startswith("p_") or c == "perm_p":
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else "<0.0001" if v < 0.0001 else f"{v:.4f}")
        elif pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else f"{v:.4f}" if abs(v) < 0.001 and v != 0 else f"{v:.{digits}f}")
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(lines)


# -------------------------------------------------------------------- analysis
def main():
    fin, lock = load()
    rng = np.random.default_rng(0)
    tests = pd.DataFrame([run_test(fin, t, rng) for t in TESTS])
    tests["p_holm"] = np.nan
    for fam, idx in tests.groupby("family").groups.items():
        tests.loc[idx, "p_holm"] = holm(tests.loc[idx, "p_for_holm"])
    tests["significant"] = (tests.p_holm < ALPHA).map({True: "yes", False: "no"})
    tests.to_csv(f"{OUT}/analysis_tests.csv", index=False)
    show = tests[["id", "hypothesis", "b", "n", "mean_a", "mean_b", "diff", "ci_lo", "ci_hi", "effect", "p_raw",
                  "p_holm", "significant"]]
    rep = [f"# Paper 2 -- confirmatory analysis\n\nLock {lock['date']}, n = {lock['n']} purposes. "
           f"a = committee (or the Thai condition for T1/T2), b = comparator; diff = a - b.\n"]
    for fam, title in [("primary", "Primary family (section 4)"), ("secondary", "Secondary family (section 5)"),
                       ("thai", "Thai family (section 6)")]:
        rep += [f"## {title}\n", md(show[tests.family == fam]), ""]

    # descriptive: means per condition / variant / method
    desc = fin.groupby(["cond", "variant", "method"])[["safe", "retention", "failure", "unnecessary", "missing_needed",
                                                      "suspicious", "escalated", "escalated_rel", "tokens"]].mean()
    rep += ["## Means per condition, variant and method (descriptive)\n", md(desc.reset_index()), ""]
    unsafe = int((fin.safe == 0).sum())
    rep += [f"Issued grants judged risky by the oracle: {unsafe} of {len(fin)}; failed units counted as denied: "
            f"{int(fin.get('failed', pd.Series(0)).sum())}.\n"]
    if os.path.exists(f"{OUT}/leakage.csv"):
        lk = pd.read_csv(f"{OUT}/leakage.csv")
        sent = lk[lk.method != "-"]
        rep += [f"Leakage audit: {int(sent.messages.sum())} messages scanned, {int(sent.leaked_values.sum())} raw values "
                f"found; positive controls found {int(lk[lk.method == '-'].leaked_values.sum())} values in "
                f"{int((lk.method == '-').sum())} datasets.\n"]

    # sensitivity
    prim = [t for t in TESTS if t["family"] == "primary"]
    sens = []
    for t in prim:
        a = values(fin, *t["a"], t["metric"])
        b = values(fin, *t["b"], t["metric"]).reindex(a.index)
        d = (a - b).to_numpy()
        ds = fin.drop_duplicates("purpose").set_index("purpose").dataset.reindex(a.index).to_numpy()
        lo, hi = boot2_ci(d, ds, rng)
        lodo = {f"without {x}": "+-0"[[1, -1, 0].index(np.sign(d[ds != x].mean()))] for x in np.unique(ds)}
        sens.append(dict(id=t["id"], diff=d.mean(), two_stage_lo=lo, two_stage_hi=hi,
                         perm_p=np.nan if t["test"] == "mcnemar" else perm_p(d, rng), **lodo))
    rep += ["## Sensitivity (section 7, not used for the claims)\n",
            "Two-stage bootstrap CI (datasets, then purposes), sign-flip permutation p (P2-P4), and the sign of the "
            "mean difference with each dataset left out.\n", md(pd.DataFrame(sens)), ""]
    if os.path.exists(f"{OUT}/screen.csv"):
        scr = pd.read_csv(f"{OUT}/screen.csv")
        sub = fin[fin.purpose.isin(scr[scr.ref_auc < NEAR].purpose)]
        rows = [{k: r[k] for k in ["id", "n", "diff", "ci_lo", "ci_hi", "effect", "p_raw"]}
                for r in (run_test(sub, t, rng) for t in prim)]
        rep += [f"Primary tests without the near-deterministic purposes (ref AUC >= {NEAR}, the target almost fixed "
                f"by other columns):\n", md(pd.DataFrame(rows)), ""]
    esc = fin[(fin.cond == "EN") & (fin.variant == "clean")].groupby("method")[["escalated", "escalated_rel"]].mean()
    a, b = values(fin, *EN_C, OURS, "escalated_rel"), values(fin, *EN_C, SINGLE, "escalated_rel")
    p, only_b, only_a = mcnemar(a.to_numpy(), b.reindex(a.index).to_numpy())
    rep += ["Escalation of clean English requests, absolute rule of s9 vs relative rule of s12 (0.95):\n",
            md(esc.reset_index()), f"\nRelative rule, committee vs single agent: exact McNemar p = {p:.4f} "
            f"(only single {only_b}, only committee {only_a}).\n"]
    pilot = [pd.read_csv(f) for f in glob.glob(f"{HERE}/outputs/agents_*.csv") if "summary" not in f]
    if pilot:
        pl = pd.concat(pilot)
        pl = pl[pl.method.isin(METHODS)].assign(cond="EN", source="pilot")
        both = pd.concat([pl, fin[fin.cond == "EN"].assign(source="confirmatory")])
        both["failure"] = (both.retention < FAIL).astype(float)
        pooled = []
        for scope in ["clean", "mean"]:
            d = both[both.variant == "clean"] if scope == "clean" else both
            g = d.groupby(["purpose", "method"])[["retention", "unnecessary", "failure"]].mean().groupby("method").mean()
            pooled.append(g.assign(scope=scope, purposes=d.purpose.nunique()).reset_index())
        rep += ["Pilot + confirmatory pooled, English (descriptive only):\n", md(pd.concat(pooled)), ""]
    open(f"{OUT}/analysis.md", "w", encoding="utf-8").write("\n".join(rep))
    print("\n".join(rep))


if __name__ == "__main__":
    main()
