"""Paper 2, step 18 - Exploratory condition TH-mix: Thai-English code-mixed requests (ANALYSIS_PLAN.md section 10).

Added after the lock, so it is exploratory and never part of the confirmatory families. It reuses s15's run
machinery and s16's statistics unchanged; only what the LLM reads changes:
  TH-mix   the code-mixed text in purposes_mix.json (Thai grammar, English technical terms), English column names,
           clean request only; same zone, oracle, purpose model, needed columns and methods as EN
Units: 57 included purposes x 3 methods = 171, in outputs/confirm_mix (own results, run.log, run.lock and STOP).
Tests (family X, Holm within it, labelled exploratory):
  X1  committee retention, TH-mix clean vs EN clean: non-inferiority, margin 0.05 (as T1)
  X2  failure, committee vs single agent, TH-mix clean: exact McNemar
  X3  retention, committee vs LLM direct, TH-mix clean: Wilcoxon
usage: python s18_mix.py lock      freeze purposes_mix.json and this script (before the first TH-mix unit)
       python s18_mix.py run       after the confirmatory run has finished (needs LLM_API_KEY)
       python s18_mix.py stop | status | collect
       python s18_mix.py analyze   after collect here and the final collect of s15
"""
import datetime, json, os, shutil, sys
import numpy as np, pandas as pd
import s15_confirm as s15
import s16_confirm_analysis as s16

MAIN, OUT = s15.OUT, f"{s15.HERE}/outputs/confirm_mix"
MIX, LOCK_MIX = f"{s15.HERE}/purposes_mix.json", f"{OUT}/LOCK_MIX.json"
FROZEN_MIX = ["purposes_mix.json", "s18_mix.py"]
SELF = s15.confirm_purposes
TESTS = [
    s16.spec("X1", "exploratory", "Committee retention, TH-mix vs EN, clean", "retention",
             ("TH-mix", "clean", s16.OURS), ("EN", "clean", s16.OURS), "noninf"),
    s16.spec("X2", "exploratory", "Failure (retention < 0.80), TH-mix clean", "failure",
             ("TH-mix", "clean", s16.OURS), ("TH-mix", "clean", s16.SINGLE), "mcnemar"),
    s16.spec("X3", "exploratory", "Retention, TH-mix clean", "retention",
             ("TH-mix", "clean", s16.OURS), ("TH-mix", "clean", s16.DIRECT)),
]


def mixed(names=None):
    """The confirmatory purposes with the code-mixed text in place of the Thai one; run_unit then reads it
    with the clean (empty) suffix."""
    mix = json.load(open(MIX, encoding="utf-8"))
    return [dict(p, text_th=mix[p["id"]]) for p in SELF(names)]


def main_left():
    rec = json.load(open(s15.LOCK))
    st = s15.progress()
    return sum(s15.pending(st, u) for u in s15.all_units(rec["included"]))


def redirect():
    s15.OUT, s15.STOP = OUT, f"{OUT}/STOP"
    s15.CONDS = {"TH-mix": ["clean"]}
    s15.confirm_purposes = mixed


def lock():
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(LOCK_MIX):
        sys.exit("s18: already locked")
    included = json.load(open(s15.LOCK))["included"]
    missing = [i for i in included if i not in json.load(open(MIX, encoding="utf-8"))]
    if missing:
        sys.exit(f"s18: no code-mixed text for {missing}")
    shutil.copy2(f"{MAIN}/leak_control.json", OUT)
    rec = dict(date=f"{datetime.datetime.now():%Y-%m-%dT%H:%M:%S}", units=len(included) * len(s16.METHODS),
               sha256={f: s15.sha256(f) for f in FROZEN_MIX})
    json.dump(rec, open(LOCK_MIX, "w"), indent=1)
    print(json.dumps(rec, indent=1))


def check_mix():
    if not os.path.exists(LOCK_MIX):
        sys.exit("s18: run lock first")
    changed = [f for f, h in json.load(open(LOCK_MIX))["sha256"].items() if s15.sha256(f) != h]
    if changed:
        sys.exit(f"s18: frozen files changed since the TH-mix lock: {changed}")


def analyze():
    check_mix()
    en, mix = pd.read_csv(f"{MAIN}/results.csv"), pd.read_csv(f"{OUT}/results.csv")
    fin = pd.concat([en[en.cond == "EN"], mix])
    fin = fin[fin.method.isin(s16.METHODS)].copy()
    fin["failure"] = (fin.retention < s16.FAIL).astype(float)
    included = json.load(open(s15.LOCK))["included"]
    have = fin[fin.cond == "TH-mix"].groupby("purpose").size().reindex(included, fill_value=0)
    if (have != len(s16.METHODS)).any():
        sys.exit(f"s18: incomplete TH-mix run, {int((have != len(s16.METHODS)).sum())} purposes lack units")
    rng = np.random.default_rng(0)
    tests = pd.DataFrame([s16.run_test(fin, t, rng) for t in TESTS])
    tests["p_holm"] = s16.holm(tests.p_for_holm)
    tests["significant"] = (tests.p_holm < s16.ALPHA).map({True: "yes", False: "no"})
    tests.to_csv(f"{OUT}/analysis_mix_tests.csv", index=False)
    show = tests[["id", "hypothesis", "b", "n", "mean_a", "mean_b", "diff", "ci_lo", "ci_hi", "effect", "p_raw",
                  "p_holm", "significant"]]
    clean = fin[fin.variant == "clean"]
    desc = clean.groupby(["cond", "method"])[["safe", "retention", "failure", "unnecessary", "missing_needed",
                                              "escalated", "tokens"]].mean()
    lk = pd.read_csv(f"{OUT}/leakage.csv")
    sent = lk[lk.method != "-"]
    rep = ["# Paper 2 -- exploratory TH-mix condition (plan section 10, not confirmatory)\n",
           f"n = {len(included)} purposes; a = committee (or TH-mix for X1), b = comparator; diff = a - b.\n",
           s16.md(show), "", "## Clean requests, EN vs TH-mix (descriptive)\n", s16.md(desc.reset_index()), "",
           f"TH-mix grants judged risky by the oracle: {int((mix.safe == 0).sum())} of {len(mix)}. Leakage audit: "
           f"{int(sent.messages.sum())} messages scanned, {int(sent.leaked_values.sum())} raw values found.\n"]
    open(f"{OUT}/analysis_mix.md", "w", encoding="utf-8").write("\n".join(rep))
    print("\n".join(rep))


if __name__ == "__main__":
    cmd = (sys.argv[1:] or ["status"])[0]
    if cmd == "lock":
        lock()
        sys.exit()
    if cmd == "run" and main_left():
        sys.exit(f"s18: the confirmatory run still has {main_left()} units; let it finish first")
    if cmd in ("run", "collect", "analyze"):
        check_mix()
    if cmd == "analyze":
        analyze()
        sys.exit()
    redirect()
    {"run": s15.run, "stop": s15.stop, "status": s15.status, "collect": s15.collect}[cmd]()
