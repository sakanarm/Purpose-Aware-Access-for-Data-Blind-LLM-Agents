"""Paper 2 figures - confirmatory study (print-ready, the style of fig_results.py).

fig_confirm   paired differences with 95% bootstrap CIs (purposes resampled), from the frozen analysis outputs
  (a) retention, committee - comparator     (b) failure rate, committee - comparator
  (c) committee retention, Thai condition - English, against the non-inferiority margin -0.05
  Filled marker: significant after Holm in its family; hollow: not. TH-mix (family X) is exploratory.
fig_thai      one confirmatory purpose (c_brfss_01) as the LLM sees it in each language condition.
  Thai script needs complex text shaping, which matplotlib lacks, so the figure is an HTML page printed to
  PDF by headless Microsoft Edge.
Reads only: outputs/confirm/analysis_tests.csv, outputs/confirm_mix/analysis_mix_tests.csv,
            purposes_confirm.json, purposes_mix.json, columns_th.json (no LLM, no patient data)
Output: outputs/figures/fig_confirm.pdf/.png, fig_thai.pdf/.png
"""
import html
import json
import os
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from fig_results import DIRECT, GRID, INK2, MUTED, OURS, OUT, SINGLE, STYLE, axes_style, save

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
MARGIN = -0.05

# (test id, row label, colour key); top to bottom
PANELS = [("(a) Retention, committee $-$ comparator", [
              ("P2", "vs LLM direct, EN", DIRECT), ("T4", "vs LLM direct, TH-text", DIRECT),
              ("X3", "vs LLM direct, TH-mix$^\\dagger$", DIRECT), ("S1", "vs single agent, EN", SINGLE),
              ("P4", "vs single agent, EN, 3 variants", SINGLE)]),
          ("(b) Failure rate, committee $-$ comparator", [
              ("S4", "vs LLM direct, EN", DIRECT), ("P1", "vs single agent, EN", SINGLE),
              ("T3", "vs single agent, TH-text", SINGLE), ("X2", "vs single agent, TH-mix$^\\dagger$", SINGLE)]),
          ("(c) Committee retention, Thai $-$ English", [
              ("T1", "TH-text", OURS), ("T2", "TH-names", OURS), ("X1", "TH-mix$^\\dagger$", OURS)])]


def tests():
    t = pd.concat([pd.read_csv(f"{HERE}/outputs/confirm/analysis_tests.csv"),
                   pd.read_csv(f"{HERE}/outputs/confirm_mix/analysis_mix_tests.csv")])
    return t.set_index("id")


def fig_confirm():
    t = tests()
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 1.75), gridspec_kw={"width_ratios": [1.15, 1.0, 0.85]})
    for ax, (title, rows) in zip(axes, PANELS):
        axes_style(ax, grid="x")
        for i, (tid, label, key) in enumerate(rows):
            r, color, y = t.loc[tid], STYLE[key][0], len(rows) - 1 - i
            ax.plot([r.ci_lo, r.ci_hi], [y, y], color=color, lw=1.4, solid_capstyle="round", zorder=2)
            sig = r.significant == "yes"
            ax.plot(r["diff"], y, STYLE[key][1], ms=5.5, mfc=color if sig else "white", mec="white" if sig else color,
                    mew=0.7 if sig else 1.0, zorder=3)
        ax.set_yticks(range(len(rows)), [f"{label}  {tid}" for tid, label, _ in rows][::-1])
        ax.tick_params(axis="y", length=0)
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.axvline(0, color=MUTED, lw=0.7, zorder=1)
        ax.set_title(title, loc="left", pad=4)
        ax.spines["left"].set_visible(False)
    axes[0].set_xlim(-0.05, 0.25)
    axes[1].set_xlim(-0.35, 0.2)
    axes[2].set_xlim(-0.1, 0.07)
    axes[2].axvspan(-0.1, MARGIN, color=GRID, alpha=0.7, lw=0, zorder=0)
    axes[2].axvline(MARGIN, color=INK2, lw=0.7, ls=(0, (3, 2)), zorder=1)
    axes[2].text(MARGIN - 0.004, -0.5, "margin", ha="right", va="bottom", fontsize=6.5, color=INK2)
    axes[0].set_xlabel("Difference in retention")
    axes[1].set_xlabel("Difference in failure rate")
    axes[2].set_xlabel("Difference in retention")
    fig.subplots_adjust(wspace=0.95)
    save(fig, "fig_confirm")
    plt.close(fig)


def page(rows, width_in, height_in):
    """A one-table HTML page; each row is (condition, what the LLM sees as HTML)."""
    cells = "".join(f"<tr><th>{c}</th><td>{v}</td></tr>" for c, v in rows)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: {width_in}in {height_in}in; margin: 0; }}
html, body {{ margin: 0; background: #fff; }}
body {{ width: {width_in}in; font: 8pt/1.35 "Times New Roman", "Leelawadee UI", serif; color: #0b0b0b; }}
table {{ border-collapse: collapse; width: 100%; }}
tr {{ border-top: 0.6pt solid #c3c2b7; }}
tr:last-child {{ border-bottom: 0.6pt solid #c3c2b7; }}
th {{ text-align: left; vertical-align: top; font-weight: bold; white-space: nowrap; padding: 3pt 6pt 3pt 0; }}
td {{ padding: 3pt 0; }}
.th {{ font-family: "Times New Roman", "Leelawadee UI", serif; }}
.col {{ font-family: "Leelawadee UI", "Tahoma", sans-serif; font-size: 7.2pt; background: #f0efe9;
        border-radius: 2pt; padding: 0 2pt; white-space: nowrap; }}
.en {{ font-family: "Courier New", monospace; font-size: 7pt; background: #f0efe9; border-radius: 2pt;
       padding: 0 2pt; white-space: nowrap; }}
.note {{ color: #52514e; }}
</style></head><body><table>{cells}</table></body></html>"""


def fig_thai(pid="c_brfss_01", show=("highbp", "age", "bmi", "highchol", "genhlth", "diffwalk")):
    p = {x["id"]: x for x in json.load(open(f"{HERE}/purposes_confirm.json", encoding="utf-8"))}[pid]
    mix = json.load(open(f"{HERE}/purposes_mix.json", encoding="utf-8"))[pid]
    names = json.load(open(f"{HERE}/columns_th.json", encoding="utf-8"))[p["dataset"]]
    e = html.escape
    en_cols = " ".join(f'<span class="en">{c}</span>' for c in show)
    th_cols = " ".join(f'<span class="col">{e(names[c])}</span>' for c in show)
    rows = [("EN", f'{e(p["text"])}<br>{en_cols} <span class="note">&hellip;</span>'),
            ("TH-text", f'<span class="th">{e(p["text_th"])}</span><br>{en_cols} '
                        f'<span class="note">&hellip;</span>'),
            ("TH-names", f'<span class="th">{e(p["text_th"])}</span><br>{th_cols} '
                         f'<span class="note">&hellip;</span>'),
            ("TH-mix", f'<span class="th">{e(mix)}</span><br>{en_cols} <span class="note">&hellip;</span>')]
    os.makedirs(OUT, exist_ok=True)
    src = f"{OUT}/fig_thai.html"
    with open(src, "w", encoding="utf-8") as f:
        f.write(page(rows, 3.45, 2.8))
    url = "file:///" + src.replace("\\", "/")
    common = [EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars"]
    subprocess.run(common + ["--no-pdf-header-footer", f"--print-to-pdf={OUT}/fig_thai.pdf", url], check=True,
                   capture_output=True, timeout=120)
    subprocess.run(common + ["--force-device-scale-factor=4", "--window-size=332,269",
                             f"--screenshot={OUT}/fig_thai.png", url], check=True, capture_output=True, timeout=120)


if __name__ == "__main__":
    fig_confirm()
    fig_thai()
    print("saved to", OUT)
