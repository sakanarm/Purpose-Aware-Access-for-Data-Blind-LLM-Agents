"""Paper 2 / step 12: relative escalation rule, recomputed from the saved traces (no LLM calls).

The rule in s9 escalates when the purpose model loses more than 0.02 AUC (rounded to 2 decimals). A weak
purpose model can lose a large share of its signal inside that margin (diabetes_p1: 0.64 -> 0.62 keeps
only 86% of the above-chance AUC and was approved). The relative rule escalates instead when the grant
keeps less than REL of the requested model's above-chance AUC, (auc_fin - 0.5) / (auc_req - 0.5) < REL,
unrounded; the other reasons (flagged instructions, verifier repair, target withheld) are unchanged.
This rule was chosen after the s9 runs, so both rules are reported. Escalated grants then go through the
same simulated reviewer as s11.
Output (paper2/outputs): escalation_relative[_datasets].csv (per grant, both rules and the sensitivity of
REL), review_relative[_datasets].csv (s11 rows under the relative rule)
usage: python s12_escalation.py [datasets...]
"""
import glob, json, sys

import pandas as pd

from s8_trusted import P2, Zone, evaluate, purposes, load_needs
from s11_review import LLM, review

REL, SENS = 0.95, [0.90, 0.95, 0.98]
AUC_REASON = "purpose model loses > 0.02 AUC"


def main(*names):
    agents = pd.concat([pd.read_csv(f) for f in glob.glob(f"{P2}/agents_*.csv") if "summary" not in f])
    found = agents.set_index(["purpose", "variant", "method"]).target_found.to_dict()
    traces = [json.loads(line) for f in glob.glob(f"{P2}/agents_trace_*.jsonl") for line in open(f, encoding="utf-8")]
    flags, rows = [], []
    for name in sorted({p["dataset"] for p in purposes(names)}):
        z = Zone(name)
        for p in purposes([name]):
            need, t = load_needs(z, p, z.columns), p["target"]
            auc_req = z.utility({c: "exact" for c in z.columns}, t)    # as in s9: no positive class
            for r in traces:
                if r["purpose"] != p["id"] or r["method"] not in LLM:
                    continue
                key = (p["id"], r["variant"], r["method"])
                other = [x for x in r["reasons"] if x != AUC_REASON]
                if found[key]:                                    # the agent named the true target
                    auc_fin = z.utility(r["grant"], t)
                    kept = (auc_fin - 0.5) / (auc_req - 0.5)
                else:                                             # agent's own target unknown: keep s9's verdict
                    auc_fin, kept = None, 0.0 if AUC_REASON in r["reasons"] else 1.0
                f = dict(purpose=p["id"], dataset=name, variant=r["variant"], method=r["method"],
                         auc_req=auc_req, auc_fin=auc_fin, kept=kept, other_reasons="; ".join(other),
                         escalated_abs=int(bool(r["reasons"])))
                f |= {f"escalated_rel{s:.2f}": int(bool(other) or kept < s) for s in SENS}
                flags.append(f)
                e = f[f"escalated_rel{REL:.2f}"]
                g = review(z, p, z.columns, r["grant"]) if e else r["grant"]
                rows.append(dict(method=r["method"] + ", after review", purpose=p["id"], dataset=name,
                                 variant=r["variant"], escalated=e, reviewer_added=len(set(g) - set(r["grant"])),
                                 **evaluate(z, p, z.columns, g, need)))
        print(name, "done", flush=True)
    sfx = "_" + "_".join(names) if names else ""
    flags, rows = pd.DataFrame(flags), pd.DataFrame(rows)
    flags.to_csv(f"{P2}/escalation_relative{sfx}.csv", index=False)
    rows.to_csv(f"{P2}/review_relative{sfx}.csv", index=False)
    cols = ["escalated_abs"] + [f"escalated_rel{s:.2f}" for s in SENS]
    print(flags.groupby(["variant", "method"])[cols].mean().round(3).to_string())
    print(rows.groupby(["variant", "method"])[["escalated", "reviewer_added", "safe", "retention", "unnecessary",
                                               "missing_needed"]].mean().round(3).to_string())


if __name__ == "__main__":
    main(*sys.argv[1:])
