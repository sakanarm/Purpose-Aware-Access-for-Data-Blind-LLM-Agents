"""Paper 2 / step 13: is the committee's gain only the minimizer? (no LLM calls)

The s9 minimizer runs inside the zone and drops the columns the Purpose agent called "useful" when the
purpose model loses < 0.005 AUC. The comparators have no such labels, so here every granted column except
the target is a candidate. It is applied to the final (verified) grant of each LLM method; removing a column
never raises the re-identification rate, so the grant stays safe. A grant without the true target is left
unchanged (the zone does not know what to optimise).
Output (paper2/outputs): minimizer_ablation[_datasets].csv
usage: python s13_minimizer.py [datasets...]
"""
import glob, json, sys

import pandas as pd

from s8_trusted import P2, Zone, evaluate, purposes, load_needs
from s9_agents import minimize

LLM = ["LLM direct", "Single agent + tools", "Multi-agent (ours)"]


def main(*names):
    sfx = "_" + "_".join(names) if names else ""
    traces = [json.loads(l) for f in glob.glob(f"{P2}/agents_trace_*.jsonl") for l in open(f, encoding="utf-8")]
    found = pd.concat([pd.read_csv(f) for f in glob.glob(f"{P2}/agents_*.csv") if "summary" not in f])
    found = found.set_index(["purpose", "variant", "method"]).target_found
    rows = []
    for name in sorted({p["dataset"] for p in purposes(names)}):
        z = Zone(name)
        for p in purposes([name]):
            need = load_needs(z, p, z.columns)
            for t in traces:
                if t["purpose"] != p["id"] or t["method"] not in LLM:
                    continue
                g, target = t["grant"], p["target"]
                if found[p["id"], t["variant"], t["method"]] and target in g:
                    g = minimize(z, g, [c for c in g if c != target], target, [])
                rows.append(dict(purpose=p["id"], dataset=name, variant=t["variant"],
                                 method=t["method"] + ", + minimizer (all columns)", **evaluate(z, p, z.columns, g, need)))
        out = pd.DataFrame(rows)
        out.to_csv(f"{P2}/minimizer_ablation{sfx}.csv", index=False)
        print(out[out.dataset == name].groupby(["variant", "method"])[["safe", "retention", "unnecessary",
              "missing_needed"]].mean().round(3).to_string(), flush=True)
    print(pd.DataFrame(rows).groupby(["variant", "method"])[["safe", "retention", "unnecessary",
          "missing_needed"]].mean().round(3).to_string())


if __name__ == "__main__":
    main(*sys.argv[1:])
