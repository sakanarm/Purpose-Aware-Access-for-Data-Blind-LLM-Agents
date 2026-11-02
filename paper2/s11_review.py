"""Paper 2 / step 11: simulated human review of escalated grants.

The admin sees only the escalated requests. For each one the trusted zone lists the requested columns
that were removed, each at the finest level that still passes the verifier, with the purpose-model AUC
it would add (column names and AUC only; rows never leave the zone). The simulated reviewer accepts the
hints, largest gain first, until the purpose model is within 0.02 AUC of the full request; a hint is
skipped when it no longer passes the verifier or adds < 0.005 AUC. Grants that were not escalated are
approved unchanged. The reviewer is optimistic: it accepts every useful hint.
Output (paper2/outputs): reviewed[_datasets].csv
usage: python s11_review.py [datasets...]
"""
import glob, json, sys

import pandas as pd

from s8_trusted import P2, Zone, evaluate, purposes, load_needs

LLM = ["LLM direct", "Single agent + tools", "Multi-agent (ours)"]
TOL, MIN_GAIN = 0.02, 0.005


def hints(z, grant, request, t, pos):
    """Removed columns at their finest safe level, with the AUC each adds to the grant."""
    base, out = z.utility(grant, t, pos), []
    for c in request:
        if c in grant or z.types[c] == "direct_id":
            continue
        lv = next((lv for lv in z.levels[c] if z.verify({**grant, c: lv}, request)["passed"]), None)
        if lv:
            out.append((z.utility({**grant, c: lv}, t, pos) - base, c, lv))
    return sorted(out, reverse=True)


def review(z, p, request, grant):
    t, pos = p["target"], p.get("positive")
    g = dict(grant)
    if t not in g and z.verify({**g, t: "exact"}, request)["passed"]:
        g[t] = "exact"                                            # the reviewer knows what the purpose predicts
    goal = z.utility({c: "exact" for c in request}, t, pos) - TOL
    for gain, c, lv in hints(z, g, request, t, pos):
        if gain < MIN_GAIN or z.utility(g, t, pos) >= goal:
            break
        g2 = {**g, c: lv}
        if z.verify(g2, request)["passed"] and z.utility(g2, t, pos) >= z.utility(g, t, pos) + MIN_GAIN:
            g = g2
    return g


def main(*names):
    agents = pd.concat([pd.read_csv(f) for f in glob.glob(f"{P2}/agents_*.csv") if "summary" not in f])
    escalated = agents.set_index(["purpose", "variant", "method"]).escalated.to_dict()
    traces = [json.loads(line) for f in glob.glob(f"{P2}/agents_trace_*.jsonl") for line in open(f, encoding="utf-8")]
    rows = []
    for name in sorted({p["dataset"] for p in purposes(names)}):
        z = Zone(name)
        for p in purposes([name]):
            need = load_needs(z, p, z.columns)
            for r in traces:
                if r["purpose"] != p["id"] or r["method"] not in LLM:
                    continue
                e = escalated[p["id"], r["variant"], r["method"]]
                g = review(z, p, z.columns, r["grant"]) if e else r["grant"]
                rows.append(dict(method=r["method"] + ", after review", purpose=p["id"], dataset=name,
                                 variant=r["variant"], escalated=e, reviewer_added=len(set(g) - set(r["grant"])),
                                 **evaluate(z, p, z.columns, g, need)))
        print(name, "done", flush=True)
    sfx = "_" + "_".join(names) if names else ""
    out = pd.DataFrame(rows)
    out.to_csv(f"{P2}/reviewed{sfx}.csv", index=False)
    print(out.groupby(["variant", "method"])[["escalated", "reviewer_added", "safe", "retention", "unnecessary",
                                              "missing_needed"]].mean().round(3).to_string())


if __name__ == "__main__":
    main(*sys.argv[1:])
