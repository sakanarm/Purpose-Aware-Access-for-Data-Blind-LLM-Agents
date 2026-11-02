"""Paper 2 figure - architecture of the data-blind multi-agent access committee (print-ready, the style of
paper 1's fig_architecture.py).

Five stages: (1) data-blind agent committee, (2) Tool API, the only door to the data, (3) trusted zone,
(4) non-LLM verification and escalation, (5) human-in-the-loop review. Boxes tagged LLM call the external
gateway; every other component is deterministic and runs inside the hospital.
Output: outputs/figures/fig_architecture.pdf (vector) and .png (600 dpi)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Circle

plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman"], "mathtext.fontset": "stix",
                     "pdf.fonttype": 42, "ps.fonttype": 42})
FS, FT = 6.4, 7.0                                           # box text, panel title (pt)
INK, GRID = "#222222", "#8A8A8A"
PANEL, KEY, INPUT = "#F3F5F7", "#E6ECF2", "#FFF7E0"
OUT = f"{os.path.dirname(os.path.abspath(__file__))}/outputs/figures"

fig, ax = plt.subplots(figsize=(5.0, 5.25))
ax.set_xlim(0, 100); ax.set_ylim(0, 105); ax.axis("off")
fig.subplots_adjust(0, 0, 1, 1)


def box(x0, y0, x1, y1, text, fc="white", ec=INK, lw=0.6, fs=FS, dashed=False, llm=False, **kw):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.9",
                                fc=fc, ec=ec, lw=lw, ls=(0, (3, 2)) if dashed else "-"))
    ax.text(kw.pop("tx", (x0 + x1) / 2), kw.pop("ty", (y0 + y1) / 2), text, ha="center", va="center",
            fontsize=fs, color=INK, linespacing=1.15, **kw)
    if llm:
        tag(x0 + 4.2, y1)                                 # on the top edge, clear of the text


def tag(x, y):
    """Black pill marking a component that calls the LLM gateway."""
    ax.add_patch(FancyBboxPatch((x - 2.4, y - 0.95), 4.8, 1.9, boxstyle="round,pad=0,rounding_size=0.9",
                                fc=INK, ec="none", zorder=4))
    ax.text(x, y - 0.05, "LLM", ha="center", va="center", fontsize=FS - 1.9, color="white", weight="bold",
            zorder=5)


def panel(x0, y0, x1, y1, n, title, lw=0.6, ec=GRID):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=1.2",
                                fc=PANEL, ec=ec, lw=lw))
    ax.add_patch(Circle((x0 + 2.4, y1 - 2.3), 1.45, fc=INK, ec="none"))
    ax.text(x0 + 2.4, y1 - 2.35, str(n), ha="center", va="center", fontsize=FS, color="white", weight="bold")
    ax.text(x0 + 4.6, y1 - 2.3, title, ha="left", va="center", fontsize=FT, weight="bold", color=INK)


def arrow(*pts, dashed=False, color=INK, both=False, head=True):
    """Polyline through pts with an arrowhead at the last point (and the first when both)."""
    ls = (0, (3, 2)) if dashed else "-"
    for a, b in zip(pts[:-2], pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=0.7, ls=ls, solid_capstyle="butt")
    style = ("<|-|>" if both else "-|>") + ",head_length=0.45,head_width=0.22" if head else "-"
    ax.annotate("", xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle=style, color=color, lw=0.7, ls=ls, shrinkA=0, shrinkB=0))


def label(x, y, text, **kw):
    ax.text(x, y, text, fontsize=FS - 0.6, color=INK, ha=kw.pop("ha", "center"), va=kw.pop("va", "center"),
            style=kw.pop("style", "italic"), **kw)


# ---------------------------------------------------------------- request and LLM gateway
box(1, 92.5, 42, 103.5, "Access request from a researcher:\nrequested columns $R$ (names)\n"
                        "+ free-text purpose (untrusted)", fc=INPUT)
box(57.5, 92.5, 99, 103.5, "LLM gateway (outside the hospital)\nused only by the agents tagged LLM; prompts "
                           "carry\nmetadata and bucketed answers, never rows;\nleakage audit scans every prompt "
                           "for raw values", dashed=True)
arrow((40, 92.5), (40, 84.5))
arrow((50, 90), (50, 98), (57.5, 98), both=True)
label(49.7, 100, "LLM calls")

# ---------------------------------------------------------------- (1) data-blind agent committee
panel(1, 44, 55, 90, 1, "Data-blind agent committee")
box(3, 75.5, 53, 84.5, "Purpose agent: marks each column essential / useful /\nunnecessary, names the target, "
                       "flags injected instructions", llm=True)
box(3, 62.5, 26.5, 71.5, "Privacy agent: repairs\na risky draft (generalize\nor remove identifiers)", llm=True)
box(29.5, 62.5, 53, 71.5, "Purpose review: counter-\nproposes when essential\ncolumns are weakened", llm=True)
box(3, 53.5, 53, 59.5, "Moderator (rule): keeps the safe candidate with the higher\npurpose-model AUC; "
                       "up to 3 rounds while the draft is risky")
box(3, 45.5, 53, 50.5, "Minimizer (rule): drops columns marked useful that\ndo not lower the purpose-model AUC")
arrow((14.75, 75.5), (14.75, 71.5)); label(16, 73.5, "draft grant, if risky", ha="left")
arrow((26.5, 67), (29.5, 67))
arrow((14.75, 62.5), (14.75, 59.5))
arrow((41.25, 62.5), (41.25, 59.5))
arrow((28, 53.5), (28, 50.5))

# ---------------------------------------------------------------- (2) Tool API
panel(57.5, 44, 77, 90, 2, "Tool API")
box(59, 74, 75.5, 82.5, "describe: column\ntypes and levels\n(never values)")
box(59, 62.5, 75.5, 71.5, "assess: verdict,\nre-id bucket and\none-step options")
box(59, 50, 75.5, 59.5, "utility: purpose-\nmodel AUC\n(rounded to 0.01)")
label(67.25, 46.9, "narrowing-only,\nbudgeted, logged")
for y in (78.25, 67, 56.5):
    arrow((53, y), (59, y), both=True)

# ---------------------------------------------------------------- (3) trusted zone
panel(79.5, 44, 99, 90, 3, "Trusted zone", lw=1.1, ec=INK)
box(81, 74, 97.5, 82.5, "Patient rows and\ngeneralization\nlevels")
box(81, 62.5, 97.5, 71.5, "Re-identification\noracle\n($k=5,\\ \\tau=0.05$)")
box(81, 50, 97.5, 59.5, "Purpose model\n(grouped CV AUC)")
label(89.25, 46.9, "rows never leave;\nno LLM inside")
for y in (78.25, 67, 54.75):
    arrow((75.5, y), (81, y), both=True)

# candidate grant -> verifier (through the gap between the rows of panels)
arrow((28, 45.5), (28, 40.5), (56, 40.5), (56, 28.25), (59, 28.25))
label(42, 41.9, "candidate grant $G\\subseteq R$")

# ---------------------------------------------------------------- (4) verification and escalation
panel(57.5, 1, 99, 37.5, 4, "Verification and escalation")
box(59, 24, 78.5, 32.5, "Verifier: re-id oracle\non the final grant\n(not an LLM)", fc=KEY)
box(81.5, 24, 97.5, 32.5, "Purpose-blind\ngreedy repair\n(always escalated)")
arrow((78.5, 28.25), (81.5, 28.25)); label(80, 29.8, "fail")
dx, dy = 68.75, 13.5
ax.add_patch(Polygon([(dx, dy + 6.5), (dx + 7.5, dy), (dx, dy - 6.5), (dx - 7.5, dy)], closed=True,
                     fc="white", ec=INK, lw=0.6))
ax.text(dx, dy, "escalate?", ha="center", va="center", fontsize=FS)
arrow((dx, 24), (dx, dy + 6.5)); label(66.6, 22.6, "pass")
arrow((89.5, 24), (89.5, 22), (dx, 22), head=False)
box(81.5, 9.5, 97.5, 17.5, "Grant issued\n(automatic)", fc=KEY)
arrow((dx + 7.5, dy), (81.5, dy)); label(78.6, dy + 1.4, "no")
tag(61.5, 3.6)
label(64.4, 3.6, "uses the LLM gateway; all else is deterministic", ha="left")

# ---------------------------------------------------------------- (5) human-in-the-loop
panel(1, 1, 55, 37.5, 5, "Human-in-the-loop")
box(30.5, 23, 53, 32, "Auditor agent: note for\nthe administrator from the\ndecision record (no rows)", llm=True)
box(30.5, 9.5, 53, 18.5, "Zone hints (no LLM): each\nremoved column at its\nfinest safe level, AUC gain")
arrow((dx - 7.5, dy), (53, dy)); label(57.2, dy + 1.4, "yes")
box(3, 11, 27, 32, "Security administrator\nsees escalated cases only\n\nreasons: flagged\ninstructions, "
                   "verifier\nrepair, target withheld,\nloss of purpose AUC")
arrow((30.5, 27.5), (27, 27.5))
arrow((30.5, dy), (27, dy))
for x0, x1, t in [(3, 9.8, "Approve"), (10.8, 20, "Accept hints"), (21, 27, "Deny")]:
    box(x0, 2.5, x1, 8, t, fs=FS - 0.3)
    arrow(((x0 + x1) / 2, 11), ((x0 + x1) / 2, 8))

os.makedirs(OUT, exist_ok=True)
fig.savefig(f"{OUT}/fig_architecture.pdf")
fig.savefig(f"{OUT}/fig_architecture.png", dpi=600)
print("saved", OUT)
