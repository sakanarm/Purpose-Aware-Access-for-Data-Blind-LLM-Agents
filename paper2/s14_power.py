"""Paper 2 / step 14: how many purposes does a confirmatory study need? (no LLM calls)

Unit = purpose (its variants are not independent): the paired difference committee - comparator is taken on
the clean request and on the mean over the three variants. For n purposes, n differences are resampled from the
observed ones and tested with the two-sided Wilcoxon signed-rank test (normal approximation with tie correction:
resampling creates ties, and scipy's exact path then takes ~0.5 s per call at n=12); power = share of resamples
with p below alpha. The failure rate (retention < 0.8) is tested with the exact McNemar test on resampled discordant pairs.
alpha 0.05 and 0.0125 (Holm's first step over the four primary tests).
usage: python s14_power.py
"""
import numpy as np
import pandas as pd
from scipy.stats import binomtest, wilcoxon

from s10_summary import read

OURS, OTHERS = "Multi-agent (ours)", ["Single agent + tools", "LLM direct"]
NS, REPS, FAIL = [12, 24, 36, 48, 60, 72, 96], 2000, 0.8


def power(diff, n, rng, alphas=(0.05, 0.0125)):
    p = []
    for _ in range(REPS):
        d = rng.choice(diff, n)
        p.append(wilcoxon(d, method="approx").pvalue if np.any(d != 0) else 1.0)
    return [np.mean(np.array(p) < a) for a in alphas]


def mcnemar_power(ours, other, n, rng, alpha=0.05):
    idx, p = np.arange(len(ours)), []
    for _ in range(REPS):
        i = rng.choice(idx, n)
        b, c = int(np.sum(~ours[i] & other[i])), int(np.sum(ours[i] & ~other[i]))   # only the other / only ours fails
        p.append(binomtest(b, b + c).pvalue if b + c else 1.0)
    return np.mean(np.array(p) < alpha)


def main():
    a = read("agents_*.csv")
    rng, rows = np.random.default_rng(0), []
    for scope, d in [("clean", a[a.variant == "clean"]), ("mean of variants", a)]:
        per = d.groupby(["purpose", "method"])[["retention", "unnecessary"]].mean().unstack("method")
        fail = (d.assign(f=d.retention < FAIL).groupby(["purpose", "method"]).f.mean().unstack() > 0) \
            if scope == "clean" else None
        for other in OTHERS:
            for metric in ["retention", "unnecessary"]:
                diff = (per[metric][OURS] - per[metric][other]).to_numpy()
                for n in NS:
                    p05, p0125 = power(diff, n, rng)
                    rows.append(dict(scope=scope, comparator=other, metric=metric, observed_mean=diff.mean(),
                                     n=n, power_05=p05, power_0125=p0125))
            if fail is not None:
                for n in NS:
                    rows.append(dict(scope=scope, comparator=other, metric=f"failure (ret<{FAIL}), McNemar",
                                     observed_mean=fail[other].mean() - fail[OURS].mean(), n=n,
                                     power_05=mcnemar_power(fail[OURS].to_numpy(), fail[other].to_numpy(), n, rng),
                                     power_0125=np.nan))
    out = pd.DataFrame(rows)
    print(out.pivot_table(index=["scope", "comparator", "metric"], columns="n", values="power_05").round(2).to_string())
    print("\nalpha 0.0125 (Holm, first of four)")
    print(out.pivot_table(index=["scope", "comparator", "metric"], columns="n", values="power_0125").round(2).to_string())


if __name__ == "__main__":
    main()
