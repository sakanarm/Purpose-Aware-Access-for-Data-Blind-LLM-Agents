"""Paper 2 / step 10: combine baselines, agents and leakage over every dataset into the paper tables.

usage: python s10_summary.py      (reads outputs/baselines_*.csv, agents_*.csv, leakage_*.csv and, when present,
                                   reviewed_*.csv from s11, escalation_relative_*.csv and review_relative_*.csv from s12,
                                   minimizer_ablation*.csv from s13)
"""
import glob

import pandas as pd

from s8_trusted import P2

METRICS = ["safe", "retention", "target_granted", "n_granted", "n_generalized", "unnecessary", "missing_needed"]
LLM = ["LLM direct", "Single agent + tools", "Multi-agent (ours)"]


def read(pattern):
    files = [f for f in glob.glob(f"{P2}/{pattern}") if "summary" not in f]
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def main():
    agents, base, leaks = read("agents_*.csv"), read("baselines_*.csv"), read("leakage_*.csv")
    base = base[base.purpose.isin(agents.purpose.unique())].assign(variant="clean")
    base["dataset"] = base.purpose.str.rsplit("_", n=1).str[0]
    print("purposes:", agents.purpose.nunique(), "datasets:", sorted(agents.dataset.unique()))

    # table 1: clean requests, every method, mean over purposes
    clean = pd.concat([base, agents[agents.variant == "clean"]], ignore_index=True)
    t1 = clean.groupby("method", sort=False)[METRICS + ["auc"]].mean()
    cost = agents[agents.variant == "clean"].groupby("method")[["calls", "tool_calls", "tokens", "seconds"]].mean()
    t1 = t1.join(cost)
    t1.to_csv(f"{P2}/table_main.csv")
    print("\n== clean requests, mean over purposes\n" + t1.round(3).to_string())

    # table 2: per dataset retention and unnecessary columns
    t2 = clean.pivot_table(index="dataset", columns="method", values=["retention", "unnecessary"], sort=False)
    t2.to_csv(f"{P2}/table_dataset.csv")
    print("\n== per dataset\n" + t2.round(2).to_string())

    # table 3: injected purpose text
    m = agents[agents.method.isin(LLM)]
    t3 = m.groupby(["variant", "method"])[["suspicious", "escalated", "safe", "retention", "missing_needed"]].mean()
    t3.to_csv(f"{P2}/table_injection.csv")
    print("\n== injection\n" + t3.round(3).to_string())

    # table 4: what the verifier and the minimizer change
    abl = agents.groupby(["method"])[["safe", "fallback", "retention", "unnecessary", "missing_needed"]].mean()
    abl.to_csv(f"{P2}/table_ablation.csv")
    print("\n== ablations (all variants)\n" + abl.round(3).to_string())
    llm = agents[agents.method.isin(LLM)]
    print("verifier repairs:", int(llm.fallback.sum()), "of", len(llm), "LLM grants")

    # table 5: leakage audit
    t5 = leaks.assign(kind=leaks.method.where(leaks.method != "-", "positive control")) \
              .groupby("kind")[["messages", "leaked_values"]].sum()
    t5.to_csv(f"{P2}/table_leakage.csv")
    print("\n== leakage\n" + t5.to_string())

    # escalation reasons for the multi-agent committee
    ours = agents[agents.method == "Multi-agent (ours)"]
    print("\n== multi-agent escalation by variant\n" + ours.groupby("variant")[["escalated", "suspicious"]].mean().round(3).to_string())
    worst = ours.nsmallest(5, "retention")[["purpose", "variant", "retention", "missing_needed", "escalated"]]
    print("\n== lowest retention, multi-agent\n" + worst.round(3).to_string(index=False))

    # table 6: after the simulated reviewer (s11) handles the escalated grants
    if glob.glob(f"{P2}/reviewed_*.csv"):
        rev = pd.concat([agents[agents.method.isin(LLM)], read("reviewed_*.csv")], ignore_index=True)
        t6 = rev.groupby(["method", "variant"])[["escalated", "reviewer_added", "safe", "retention", "unnecessary",
                                                 "missing_needed"]].mean()
        t6.to_csv(f"{P2}/table_review.csv")
        print("\n== human review (simulated)\n" + t6.round(3).to_string())

    # table 7: escalation rule chosen after the runs (s12), reported beside the original rule
    if glob.glob(f"{P2}/escalation_relative_*.csv"):
        esc = read("escalation_relative_*.csv")
        cols = [c for c in esc.columns if c.startswith("escalated_")]
        t7 = esc.groupby(["variant", "method"])[cols].mean()
        rel = read("review_relative_*.csv").groupby(["variant", "method"])[["reviewer_added", "retention"]].mean()
        t7 = t7.join(rel.rename(index=lambda m: m.replace(", after review", ""), level=1).add_suffix("_rel"))
        t7.to_csv(f"{P2}/table_escalation_rule.csv")
        print("\n== escalation: absolute (s9) vs relative (s12)\n" + t7.round(3).to_string())
        changed = esc[esc.escalated_abs != esc["escalated_rel0.95"]]
        print(changed[["purpose", "variant", "method", "auc_req", "auc_fin", "kept"]].round(3).to_string(index=False))

    # table 8: the committee's minimizer on the final grant of every LLM method, every column a candidate (s13)
    if glob.glob(f"{P2}/minimizer_ablation*.csv"):
        mz = pd.concat([agents[agents.method.isin(LLM)], read("minimizer_ablation*.csv")], ignore_index=True)
        cols = ["safe", "retention", "unnecessary", "missing_needed"]
        t8 = pd.concat({"clean": mz[mz.variant == "clean"].groupby("method")[cols].mean(),
                        "all": mz.groupby("method")[cols].mean()}, axis=1)
        t8.to_csv(f"{P2}/table_minimizer.csv")
        print("\n== minimizer on every LLM method (s13)\n" + t8.round(3).to_string())


if __name__ == "__main__":
    main()
