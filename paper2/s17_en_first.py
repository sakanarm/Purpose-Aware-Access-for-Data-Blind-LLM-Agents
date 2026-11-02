"""Paper 2, step 17 - English families before the Thai run ends (deviation of 2026-11-01 in ANALYSIS_PLAN.md).

Copies the result files of outputs/confirm to outputs/confirm_en (a snapshot; the running study is not touched),
collects them there with s15's collect, keeps the English units and runs s16's analysis unchanged on them:
primary P1-P4, secondary S1-S6 and the sensitivity analyses. The Thai family is left to the final s16 run.
Stops if any English unit is missing. No LLM calls.
Output (outputs/confirm_en): results.csv, leakage.csv, analysis_tests.csv, analysis.md
usage: python s17_en_first.py
"""
import glob, os, shutil, sys
import pandas as pd
import s15_confirm as s15
import s16_confirm_analysis as s16

SRC, DST = s15.OUT, f"{s15.HERE}/outputs/confirm_en"


def main():
    rec = s15.check_lock()
    os.makedirs(DST, exist_ok=True)
    for f in glob.glob(f"{SRC}/results_*.jsonl") + [f"{SRC}/leak_control.json", f"{SRC}/screen.csv"]:
        shutil.copy2(f, DST)
    s15.OUT = DST
    s15.collect()

    res = pd.read_csv(f"{DST}/results.csv")
    fin = res[res.method.isin(s16.METHODS) & (res.cond == "EN")].copy()
    fin["failure"] = (fin.retention < s16.FAIL).astype(float)
    have = fin.groupby("purpose").size().reindex(rec["included"], fill_value=0)
    if (have != s16.REQUESTS["EN"] * len(s16.METHODS)).any():
        sys.exit(f"s17: {int((have != 9).sum())} purposes lack English units")
    lk = pd.read_csv(f"{DST}/leakage.csv")
    lk[lk.cond.isin(["EN", "-"])].to_csv(f"{DST}/leakage.csv", index=False)

    s16.OUT = DST
    s16.TESTS = [t for t in s16.TESTS if t["family"] != "thai"]
    s16.load = lambda: (fin, rec)
    s16.main()
    rep = open(f"{DST}/analysis.md", encoding="utf-8").read()
    rep = rep.replace("# Paper 2 -- confirmatory analysis",
                      "# Paper 2 -- confirmatory analysis, English units only (deviation 2026-11-01; the Thai family "
                      "comes with the final s16 run)", 1)
    open(f"{DST}/analysis.md", "w", encoding="utf-8").write(rep)


if __name__ == "__main__":
    main()
