"""Shared utilities: column statistics, Cramer's V, and the re-identification oracle."""
import json, os
import numpy as np, pandas as pd
from scipy.stats import chi2_contingency

ROOT = os.path.dirname(os.path.abspath(__file__))
CLEAN, OUT = f"{ROOT}/data_clean", f"{ROOT}/outputs"
DATASETS = ["kaggle", "diabetes", "synthea", "stroke", "insurance", "icu", "brfss"]
TYPES = ["direct_id", "quasi_id", "clinical", "financial", "operational"]
SENSITIVE = {"clinical", "financial"}
LINKABLE = {"direct_id", "quasi_id"}
K_ANON = 5          # equivalence classes with < K distinct patients are re-identifiable
TAU = 0.05          # a set is risky if >= 5% of patients become re-identifiable AND it exposes sensitive data


def load(name):
    cat = json.load(open(f"{CLEAN}/catalog.json"))[name]
    return pd.read_pickle(f"{CLEAN}/{name}.pkl"), cat


def encode(df, cols):
    """Integer-code each column (NaN gets its own code)."""
    return {c: pd.factorize(df[c].astype(str), sort=False)[0].astype(np.int64) for c in cols}


def column_stats(df, col, pid):
    s = df[col]
    n = len(s)
    vc = s.astype(str).value_counts()
    p = vc.values / n
    ent = float(-(p * np.log(p)).sum())
    nun = len(vc)
    # share of patients that are unique on this single column (single-attribute re-identification)
    g = pd.DataFrame({"v": s.astype(str), "pid": pid}).drop_duplicates()
    cls = g.groupby("v")["pid"].transform("nunique")
    reid = float(g.loc[cls < K_ANON, "pid"].nunique() / g["pid"].nunique())
    return {
        "log_card": float(np.log(nun) / np.log(n)),            # 0..1
        "entropy": ent / np.log(n),                             # normalized by log(n)
        "unique_frac": float((vc == 1).sum() / n),
        "top_freq": float(p[0]),
        "missing": float(s.isna().mean()),
        "numeric": float(pd.api.types.is_numeric_dtype(s)),
        "reid_single": reid,
    }


def discretize(s, bins=10, top=20):
    """For Cramer's V: numeric -> quantile bins; categorical -> top-k categories + 'other'."""
    if pd.api.types.is_numeric_dtype(s) and s.nunique() > bins:
        return pd.qcut(s.rank(method="first"), bins, labels=False).fillna(-1).astype(int).astype(str)
    s = s.astype(str)
    keep = s.value_counts().index[:top]
    return s.where(s.isin(keep), "__other__")


def cramers_v(a, b):
    """Bias-corrected Cramer's V (Bergsma 2013) and chi-square p-value."""
    ct = pd.crosstab(a, b)
    if min(ct.shape) < 2:
        return 0.0, 1.0
    chi2, p, _, _ = chi2_contingency(ct, correction=False)
    n = ct.values.sum(); r, k = ct.shape
    phi2 = max(0.0, chi2 / n - (k - 1) * (r - 1) / (n - 1))
    rc, kc = r - (r - 1) ** 2 / (n - 1), k - (k - 1) ** 2 / (n - 1)
    d = min(rc - 1, kc - 1)
    return (float(np.sqrt(phi2 / d)) if d > 0 else 0.0), float(p)


class ReidOracle:
    """Ground truth: share of patients that fall in an equivalence class of < K distinct patients
    when the linkable (direct/quasi) columns of a permission set are joined.
    Uses only the data and the catalog -- never the graph edges."""

    def __init__(self, df, cat):
        self.types = cat["types"]
        self.codes = encode(df, cat["resources"])
        self.pid = pd.factorize(df["_pid"])[0].astype(np.int64)
        self.n_pat = self.pid.max() + 1
        self.cache = {}

    def reid_rate(self, cols):
        key = tuple(sorted(c for c in cols if self.types[c] in LINKABLE))
        if not key:
            return 0.0
        if key in self.cache:
            return self.cache[key]
        k = np.zeros(len(self.pid), dtype=np.int64)
        for c in key:                                      # mixed-radix combination -> one class id
            k = pd.factorize(k * (self.codes[c].max() + 1) + self.codes[c])[0].astype(np.int64)
        pair = np.unique(k * self.n_pat + self.pid)        # distinct (class, patient)
        cls = pair // self.n_pat
        size = np.bincount(cls)                            # distinct patients per class
        risky_pat = np.unique((pair % self.n_pat)[size[cls] < K_ANON])
        r = len(risky_pat) / self.n_pat
        self.cache[key] = r
        return r

    def label(self, cols):
        r = self.reid_rate(cols)
        sens = any(self.types[c] in SENSITIVE for c in cols)
        return int(sens and r >= TAU), r
