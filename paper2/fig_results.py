"""Paper 2 figures - results (print-ready, the style of fig_architecture.py).

fig_tradeoff  clean requests, mean over the 12 purposes (whiskers: +-1 s.e.)
  (a) purpose signal kept (retention) vs the share of the unneeded requested columns still granted
  (b) retention per dataset for the three LLM methods
fig_review    (a) share of grants escalated to the administrator, per request type (s9 rule)
              (b) retention before and after the simulated reviewer (s11) handles the escalated grants
Colours: the first three slots of the dataviz reference palette (all-pairs validated, light); every method
also has its own marker and a direct label or legend entry. Non-LLM baselines are grey.
Output: outputs/figures/fig_tradeoff.pdf/.png, fig_review.pdf/.png (600 dpi)
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from s10_summary import read

plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman"], "mathtext.fontset": "stix",
                     "pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 8, "axes.titlesize": 8.5,
                     "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
                     "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.6, "xtick.color": "#52514e",
                     "ytick.color": "#52514e", "xtick.major.width": 0.6, "ytick.major.width": 0.6,
                     "axes.labelcolor": "#0b0b0b", "text.color": "#0b0b0b"})
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
OURS, SINGLE, DIRECT = "Multi-agent (ours)", "Single agent + tools", "LLM direct"
STYLE = {OURS: ("#2a78d6", "o"), SINGLE: ("#eb6834", "s"), DIRECT: ("#1baf7a", "^")}
NAMES = {"brfss": "BRFSS 2015", "diabetes": "Diabetes 130-US", "icu": "WiDS ICU", "insurance": "Medical cost",
         "stroke": "Stroke", "synthea": "Synthea"}
VARIANTS = {"clean": "Clean", "pretext": "Pretext", "override": "Override"}
OUT = f"{os.path.dirname(os.path.abspath(__file__))}/outputs/figures"


def axes_style(ax, grid="y"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid, color=GRID, lw=0.5)
    ax.set_axisbelow(True)


def dot(ax, x, y, color, marker, ms=5.5, hollow=False, z=3):
    ax.plot(x, y, marker, ms=ms, mfc="white" if hollow else color, mec=color if hollow else "white",
            mew=0.9 if hollow else 0.7, zorder=z)


def handle(label, color, marker, ms=5.5):
    if marker == "x":
        return plt.Line2D([], [], ls="", marker="x", ms=ms, mew=1.0, color=color, label=label)
    return plt.Line2D([], [], ls="", marker=marker, ms=ms, mfc=color, mec="white", mew=0.7, label=label)


def legend(fig, y=-0.05, handles=None):
    """One legend row for both panels, below them (default: the three LLM methods)."""
    handles = handles or [handle(m, c, mk) for m, (c, mk) in STYLE.items()]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, y), ncol=len(handles), frameon=False,
               handletextpad=0.2, columnspacing=1.6)


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(f"{OUT}/{name}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(f"{OUT}/{name}.png", dpi=600, bbox_inches="tight", pad_inches=0.02)


def load():
    agents, base = read("agents_*.csv"), read("baselines_*.csv")
    base = base[base.purpose.isin(agents.purpose.unique())].assign(variant="clean")
    clean = pd.concat([base, agents[agents.variant == "clean"]], ignore_index=True)
    clean["dataset"] = clean.purpose.str.rsplit("_", n=1).str[0]
    asked = clean[clean.method == "As requested"].set_index("purpose").unnecessary
    clean["unneeded"] = clean.unnecessary / clean.purpose.map(asked)
    return agents, clean


def tradeoff(clean):
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.75), gridspec_kw=dict(width_ratios=[1.25, 1], wspace=0.42))
    s = clean.groupby("method")[["unneeded", "retention"]].agg(["mean", "sem"])

    def point(m, color, marker, label=None, offset=(0, 0), ha="left", ms=5.5, hollow=False):
        x, y = s.loc[m, ("unneeded", "mean")], s.loc[m, ("retention", "mean")]
        a.errorbar(x, y, xerr=s.loc[m, ("unneeded", "sem")], yerr=s.loc[m, ("retention", "sem")], fmt="none",
                   ecolor=color, elinewidth=0.6, alpha=0.7, zorder=2)
        dot(a, x, y, color, marker, ms, hollow)
        if label:
            a.annotate(label, (x, y), xytext=offset, textcoords="offset points", ha=ha, va="center",
                       fontsize=7.2)
        return x, y

    # the grey references sit too close together to label directly; they get a key row below the figure
    refs = [("Target-known search", "*", 8.5), ("Purpose-blind greedy", "v", 5),
            ("Rule (drop ids, coarsen QIs)", "D", 4)]
    for m, mk, ms in refs:
        point(m, MUTED, mk, ms=ms)
    a.plot(1, 1, "x", ms=5, mew=1.0, color=MUTED, zorder=3)
    p0 = point(OURS + ", no minimizer", STYLE[OURS][0], "o", "Multi-agent,\nno minimizer", (0, -22), "center",
               hollow=True)
    p1 = point(OURS, *STYLE[OURS], r"$\bf{Multi}$-$\bf{agent\ (ours)}$", (0, -17), "center")
    point(SINGLE, *STYLE[SINGLE], SINGLE, (-5, 9), "right")
    point(DIRECT, *STYLE[DIRECT], DIRECT, (6, -9))
    a.annotate("", xy=(p1[0] + 0.07, p1[1] + 0.003), xytext=(p0[0] - 0.04, p0[1]),
               arrowprops=dict(arrowstyle="-|>,head_length=0.35,head_width=0.18", color=INK2, lw=0.6))
    a.text((p0[0] + p1[0]) / 2 + 0.01, p0[1] + 0.008, "minimizer", ha="center", fontsize=7, style="italic",
           color=INK2)
    a.text(1.05, 0.69, "Deny if risky:\nretention 0 (off scale)", fontsize=7, color=INK2, ha="right",
           va="bottom")
    a.set_xlim(-0.05, 1.07); a.set_ylim(0.68, 1.035)
    a.set_xlabel("Unneeded requested columns still granted (share)")
    a.set_ylabel("Purpose signal kept (retention)")
    a.set_title("(a) Retention vs unneeded columns", loc="left")
    axes_style(a, "both")

    d = clean[clean.method.isin(STYLE)].pivot_table(index="dataset", columns="method", values="retention")
    d = d.sort_values(OURS)
    for i, (_, row) in enumerate(d.iterrows()):
        b.plot([row.min(), row.max()], [i, i], color="#c3c2b7", lw=0.9, zorder=1)
        for m, (c, mk) in STYLE.items():
            dot(b, row[m], i, c, mk)
    b.set_yticks(range(len(d)), [NAMES[n] for n in d.index])
    b.tick_params(axis="y", length=0)
    b.set_xlim(0.38, 1.03); b.set_ylim(-0.6, len(d) - 0.4)
    b.set_xlabel("Purpose signal kept (retention)")
    b.set_title("(b) Per dataset, LLM methods", loc="left")
    axes_style(b, "x")
    b.spines["left"].set_visible(False)
    legend(fig, -0.06)
    legend(fig, -0.12, [handle(m, MUTED, mk, ms) for m, mk, ms in refs] + [handle("As requested (unsafe)", MUTED, "x", 5)])
    save(fig, "fig_tradeoff")


def review(agents):
    llm = agents[agents.method.isin(STYLE)]
    rev = read("reviewed_*.csv").assign(method=lambda r: r.method.str.replace(", after review", ""))
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.75), gridspec_kw=dict(width_ratios=[1.1, 1], wspace=0.55))

    esc = llm.groupby(["variant", "method"]).escalated.mean() * 100
    w = 0.25
    for j, (m, (c, mk)) in enumerate(STYLE.items()):
        for i, v in enumerate(VARIANTS):
            x, h = i + (j - 1) * (w + 0.03), esc[v, m]
            a.bar(x, h, w, color=c, edgecolor="none")
            a.text(x, h + 1.5, f"{h:.0f}", ha="center", va="bottom", fontsize=6.8, color=INK2)
    a.set_xticks(range(len(VARIANTS)), [f"{t}\nrequests" for t in VARIANTS.values()])
    a.tick_params(axis="x", length=0)
    a.set_ylim(0, 112); a.set_yticks([0, 25, 50, 75, 100])
    a.set_ylabel("Grants escalated (%)")
    a.set_title("(a) Escalated to the administrator", loc="left")
    axes_style(a)

    before = llm.groupby(["variant", "method"]).retention.mean()
    after = rev.groupby(["variant", "method"]).retention.mean()
    y, ticks = 0, []
    for v, t in VARIANTS.items():                     # bold group header in the tick-label column
        b.text(-0.04, y, t + " requests", transform=b.get_yaxis_transform(), ha="right", va="center",
               fontsize=7.4, weight="bold")
        y += 1
        for m, (c, mk) in STYLE.items():
            b.plot([before[v, m], after[v, m]], [y, y], color=c, lw=1.0, alpha=0.55, zorder=1)
            dot(b, before[v, m], y, c, mk, hollow=True)
            dot(b, after[v, m], y, c, mk)
            ticks.append((y, m)); y += 1
        y += 0.3
    b.set_yticks([t for t, _ in ticks], [m for _, m in ticks])
    b.set_ylim(y - 0.6, -0.6); b.tick_params(axis="y", length=0)
    b.set_xlim(0.7, 1.0)
    b.set_xlabel("Purpose signal kept (retention)")
    b.set_title("(b) Before (hollow) and after (filled) review", loc="left")
    axes_style(b, "x")
    b.spines["left"].set_visible(False)
    legend(fig, -0.08)
    save(fig, "fig_review")


if __name__ == "__main__":
    agents, clean = load()
    tradeoff(clean)
    review(agents)
    print("saved", OUT)
