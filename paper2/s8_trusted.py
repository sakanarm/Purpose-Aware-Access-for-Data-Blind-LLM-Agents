"""Paper 2, step 8 - Trusted zone for data-blind, purpose-aware least privilege.

Patient rows never leave this module. The LLM agents (s9) only see what the Tool API returns:
  describe   column metadata: name, semantic type, value kind, generalization levels (never values)
  assess     verdict, bucketed re-identification rate, sensitive columns exposed and single-step
             options (generalize or remove one identifier column) with the bucket each would give
  utility    cross-validated AUC of the purpose model on a candidate grant, rounded to 0.01
Every call goes through ToolAPI: a grant may only narrow the request, a query budget applies and every
call and answer is appended to an audit log (scanned for raw values in the s9 leakage audit).
Grant = {column: level}, level in exact / banded / coarse; a column left out is removed.
Generalization levels come from the data: numeric -> 10 / 3 quantile bands, date -> month / year,
categorical -> 9 / 2 most common values + other; identifiers cannot be generalized, only removed.
Verifier = the re-identification oracle of paper 1 (k=5, tau=0.05) on the generalized columns. It is
not an LLM, it sees the data and its decision is final.
Also here: ground truth per purpose (columns the purpose model really uses, permutation importance),
the evaluation of a grant and the baselines that need no LLM:
  as requested, deny if risky, rule (drop direct ids, coarsen quasi ids), purpose-blind greedy,
  target-known search (upper reference: knows the target and the needed columns).
Output (paper2/outputs): needs.json, baselines[_datasets].csv
usage: python s8_trusted.py [datasets...]
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                # paper-1 code: data loading and the oracle
from common import load, K_ANON, TAU, SENSITIVE, LINKABLE

P2 = f"{HERE}/outputs"
LEVELS = ["exact", "banded", "coarse"]
BUCKETS = [(0.01, "<1%"), (TAU, "1-5%"), (0.2, "5-20%"), (0.5, "20-50%"), (1.01, ">50%")]
N_UTIL = 5000                     # patients sampled for the purpose model
NEED_THR = 0.005                  # permutation-importance AUC drop that makes a column "needed"
MEANING = {"numeric": {"exact": "exact value", "banded": "10 quantile bands", "coarse": "3 bands"},
           "date": {"exact": "exact date", "banded": "month", "coarse": "year"},
           "categorical": {"exact": "exact value", "banded": "9 most common values + other",
                           "coarse": "2 most common values + other"},
           "identifier": {"exact": "identifier (cannot be generalized)"}}


def bucket(r):
    return next(b for t, b in BUCKETS if r < t)


def count_bucket(n):
    return "2" if n <= 2 else "3-10" if n <= 10 else "11-100" if n <= 100 else "101-1000" if n <= 1000 else ">1000"


def value_kind(s, typ):
    if typ == "direct_id":
        return "identifier"
    if pd.api.types.is_numeric_dtype(s):
        return "numeric"
    x = s.dropna().astype(str).head(500)
    if len(x) and pd.to_numeric(x, errors="coerce").notna().mean() > 0.9:
        return "numeric"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if len(x) and pd.to_datetime(x, errors="coerce").notna().mean() > 0.9:
            return "date"
    return "categorical"


def generalize(s, kind):
    """{level: model feature (float, ordered)}; categorical codes are frequency ranks."""
    if kind == "numeric":
        x = pd.to_numeric(s, errors="coerce")
        return {"exact": x, **{lv: pd.qcut(x, q, labels=False, duplicates="drop") for lv, q in [("banded", 10), ("coarse", 3)]}}
    if kind == "date":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            d = pd.to_datetime(s, errors="coerce")
        return {"exact": (d - pd.Timestamp(0)).dt.days, "banded": d.dt.year * 12 + d.dt.month, "coarse": d.dt.year}
    s = s.astype(str); rank = {v: i for i, v in enumerate(s.value_counts().index)}
    x = s.map(rank)
    if kind == "identifier":
        return {"exact": x}
    return {"exact": x, "banded": x.where(x < 9, 9), "coarse": x.where(x < 2, 2)}


def apply(grant, col, level):
    g = dict(grant)
    if level is None:
        g.pop(col, None)
    else:
        g[col] = level
    return g


class Zone:
    """All data access of paper 2: generalization codes, oracle, purpose model."""

    def __init__(self, name, seed=0):
        df, cat = load(name)
        self.name, self.types, self.columns, self.df = name, cat["types"], list(cat["resources"]), df
        self.pid = pd.factorize(df["_pid"])[0].astype(np.int64)
        self.n_pat = int(self.pid.max()) + 1
        self.kind, self.levels, self.code, self.feat, self.n_values = {}, {}, {}, {}, {}
        for c in self.columns:
            self.kind[c] = k = value_kind(df[c], self.types[c])
            raw = pd.factorize(df[c].astype(str))[0].astype(np.int64)      # exact level = paper-1 oracle codes
            self.levels[c] = []
            for lv, f in generalize(df[c], k).items():
                code = raw if lv == "exact" else pd.factorize(pd.Series(f).astype(str))[0].astype(np.int64)
                n = int(code.max()) + 1
                if self.levels[c] and n >= self.n_values[c, self.levels[c][-1]]:
                    continue                                              # keep a level only if it merges values
                self.levels[c].append(lv)
                self.code[c, lv], self.n_values[c, lv] = code, n
                self.feat[c, lv] = np.asarray(f, dtype=float)
        rng = np.random.default_rng(seed)
        pats = rng.permutation(self.n_pat)[:N_UTIL]
        rows = np.flatnonzero(np.isin(self.pid, pats))
        if len(rows) > 2 * N_UTIL:
            rows = np.sort(rng.choice(rows, 2 * N_UTIL, replace=False))
        self.us, self._risk, self._util = rows, {}, {}

    # ---------------------------------------------------------------- oracle
    def reid(self, grant):
        key = tuple(sorted((c, lv) for c, lv in grant.items() if self.types[c] in LINKABLE))
        if not key:
            return 0.0
        if key not in self._risk:
            k = np.zeros(len(self.pid), dtype=np.int64)
            for c, lv in key:                                              # mixed radix -> one class id
                code = self.code[c, lv]
                k = pd.factorize(k * (code.max() + 1) + code)[0].astype(np.int64)
            pair = np.unique(k * self.n_pat + self.pid)
            cls = pair // self.n_pat
            size = np.bincount(cls)
            self._risk[key] = len(np.unique((pair % self.n_pat)[size[cls] < K_ANON])) / self.n_pat
        return self._risk[key]

    def label(self, grant):
        r = self.reid(grant)
        return int(r >= TAU and any(self.types[c] in SENSITIVE for c in grant)), r

    def actions(self, grant):
        """Single steps that can lower the risk: coarser level or removal of an identifier column."""
        for c, lv in grant.items():
            if self.types[c] in LINKABLE:
                for lv2 in self.levels[c][self.levels[c].index(lv) + 1:]:
                    yield c, lv2
                yield c, None

    # ---------------------------------------------------------------- purpose model
    def target_y(self, target, positive=None):
        s = self.df[target]
        if isinstance(positive, str) and positive[:2] in (">=", "<="):                # clinical cut-off, e.g. ">=30"
            x, v = pd.to_numeric(s, errors="coerce"), float(positive[2:])
            return (x >= v if positive[:2] == ">=" else x <= v).values.astype(int)
        if positive == ">median" or (positive is None and self.kind[target] == "numeric" and s.nunique() > 10):
            x = pd.to_numeric(s, errors="coerce")
            return (x > x.median()).values.astype(int)
        s = s.astype(str)
        return (s.isin(positive) if positive else s != s.mode()[0]).values.astype(int)

    def _xy(self, cols, grant, target, positive):
        X = np.column_stack([self.feat[c, grant[c]][self.us] for c in cols])
        cat = np.array([self.kind[c] == "categorical" and self.n_values[c, grant[c]] <= 250 for c in cols])
        return X, cat, self.target_y(target, positive)[self.us], self.pid[self.us]

    @staticmethod
    def _model(cat):
        return HistGradientBoostingClassifier(max_iter=150, categorical_features=cat if cat.any() else None,
                                              random_state=0)

    def utility(self, grant, target, positive=None):
        """Cross-validated AUC of the purpose model on the granted columns (0.5 when the target is withheld)."""
        cols = sorted(c for c in grant if c != target and self.types[c] != "direct_id")
        if target not in grant or not cols:
            return 0.5
        key = (tuple((c, grant[c]) for c in cols), target, str(positive))
        if key not in self._util:
            X, cat, y, g = self._xy(cols, grant, target, positive)
            auc = [roc_auc_score(y[te], self._model(cat).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1])
                   for tr, te in GroupKFold(3).split(X, y, g)]
            self._util[key] = float(np.mean(auc))
        return self._util[key]

    def needs(self, target, request, positive=None):
        """Ground truth: columns whose permutation lowers the held-out AUC by >= NEED_THR."""
        cols = [c for c in request if c != target and self.types[c] != "direct_id"]
        grant = {c: "exact" for c in cols}
        X, cat, y, g = self._xy(cols, grant, target, positive)
        imp = np.zeros(len(cols))
        for tr, te in GroupKFold(3).split(X, y, g):
            m = self._model(cat).fit(X[tr], y[tr])
            imp += permutation_importance(m, X[te], y[te], scoring="roc_auc", n_repeats=5,
                                          random_state=0).importances_mean / 3
        return {c: round(float(v), 4) for c, v in zip(cols, imp)}

    # ---------------------------------------------------------------- what the agents may see
    def describe(self, cols):
        return [dict(column=c, type=self.types[c], kind=self.kind[c],
                     levels={lv: f"{MEANING[self.kind[c]][lv]} ({count_bucket(self.n_values[c, lv])} values)"
                             for lv in self.levels[c]}) for c in cols]

    def assess(self, grant, top=10):
        y, r = self.label(grant)
        out = dict(verdict="risky" if y else "safe", reid_bucket=bucket(r),
                   sensitive_columns=[c for c in grant if self.types[c] in SENSITIVE],
                   identifier_columns=[c for c in grant if self.types[c] in LINKABLE])
        if y:
            opts = []
            for c, lv in self.actions(grant):
                y2, r2 = self.label(apply(grant, c, lv))
                opts.append((y2, r2, dict(column=c, action="remove" if lv is None else f"generalize to {lv}",
                                          result="risky" if y2 else "safe", reid_bucket=bucket(r2))))
            out["single_step_options"] = [o for *_, o in sorted(opts, key=lambda t: t[:2])][:top]
        return out

    def verify(self, grant, request):
        """Final, non-LLM check: grant narrows the request, levels exist, oracle says safe."""
        bad = [f"{c} not requested" for c in grant if c not in request]
        bad += [f"{c}: no level {lv}" for c, lv in grant.items() if c in self.types and lv not in self.levels[c]]
        if bad:
            return dict(passed=False, reasons=bad)
        y, r = self.label(grant)
        return dict(passed=not y, reid=r, reasons=[f"re-identification {r:.1%} >= {TAU:.0%} with sensitive columns"] if y else [])


class ToolAPI:
    """The only door from the agents to the zone: narrowing-only grants, a query budget, an audit log."""

    def __init__(self, zone, request, budget=12):
        self.zone, self.request, self.budget, self.used, self.log = zone, list(request), budget, 0, []

    def _bad(self, grant):
        if not isinstance(grant, dict):
            return "grant must be an object {column: level}"
        bad = [c for c, lv in grant.items() if c not in self.request or lv not in self.zone.levels[c]]
        return f"not allowed (outside the request or unknown level): {bad}" if bad else None

    def __call__(self, tool, **args):
        if tool == "describe":                                             # metadata only, free
            res = self.zone.describe(self.request)
        elif self.used >= self.budget:
            res = {"error": "query budget exhausted"}
        elif tool in ("assess", "utility"):
            self.used += 1
            grant = args.get("grant")
            err = self._bad(grant)
            if err:
                res = {"error": err}
            elif tool == "assess":
                res = self.zone.assess(grant)
            elif args.get("target") not in self.request:
                res = {"error": "target must be a requested column"}
            else:
                res = {"auc": round(self.zone.utility(grant, args["target"]), 2)}
        else:
            res = {"error": f"unknown tool {tool}"}
        self.log.append(dict(tool=tool, args=args, result=res))
        return res


class Renamed:
    """Language condition TH-names: the agents see other column names (a fixed dictionary, Thai script). The zone
    maps every name back before a check and renames what its answers contain; a name outside the dictionary
    (an English column name included) is unknown, so the verifier rejects it as not requested."""

    def __init__(self, zone, names):
        self.zone, self.name = zone, zone.name
        self.out = {c: names[c] for c in zone.columns}
        self.back = {a: c for c, a in self.out.items()}
        assert len(self.back) == len(self.out), "column dictionary is not one-to-one"
        self.columns = [self.out[c] for c in zone.columns]
        self.types, self.kind, self.levels = ({self.out[c]: d[c] for c in zone.columns}
                                              for d in (zone.types, zone.kind, zone.levels))

    def real(self, grant):
        return {self.back[c]: lv for c, lv in grant.items() if c in self.back}

    def label(self, grant):
        return self.zone.label(self.real(grant))

    def reid(self, grant):
        return self.zone.reid(self.real(grant))

    def actions(self, grant):
        for c, lv in self.zone.actions(self.real(grant)):
            yield self.out[c], lv

    def utility(self, grant, target, positive=None):
        return self.zone.utility(self.real(grant), self.back.get(target), positive)

    def describe(self, cols):
        return [dict(d, column=self.out[d["column"]]) for d in self.zone.describe([self.back[c] for c in cols])]

    def assess(self, grant, top=10):
        a = self.zone.assess(self.real(grant), top)
        for k in ("sensitive_columns", "identifier_columns"):
            a[k] = [self.out[c] for c in a[k]]
        for o in a.get("single_step_options", []):
            o["column"] = self.out[o["column"]]
        return a

    def verify(self, grant, request):
        return self.zone.verify({self.back.get(c, f"(unknown) {c}"): lv for c, lv in grant.items()},
                                [self.back[c] for c in request])


# -------------------------------------------------------------------- baselines without an LLM
def loss(z, c, old, new):
    return len(LEVELS) if new is None else LEVELS.index(new) - LEVELS.index(old)


def greedy_blind(z, grant):
    """Purpose-blind repair: the cheapest single step that makes the grant safe, else the step that
    lowers the re-identification rate most; repeat."""
    g = dict(grant)
    while z.label(g)[0]:
        steps = [(z.label(apply(g, c, lv)), loss(z, c, g[c], lv), c, lv) for c, lv in z.actions(g)]
        safe = [s for s in steps if s[0][0] == 0]
        _, _, c, lv = min(safe, key=lambda s: s[1]) if safe else min(steps, key=lambda s: (s[0][1], s[1]))
        g = apply(g, c, lv)
    return g


def rule(z, request):
    g = {c: z.levels[c][-1] if z.types[c] == "quasi_id" else "exact" for c in request if z.types[c] != "direct_id"}
    return greedy_blind(z, g)


def search_known(z, p, needed):
    """Upper reference: knows the target and the needed columns; repairs by the step that keeps the most AUC."""
    t, pos = p["target"], p.get("positive")
    g = {c: "exact" for c in needed + [t]}
    while z.label(g)[0]:
        steps = []
        for c, lv in z.actions(g):
            g2 = apply(g, c, lv); y2, r2 = z.label(g2)
            steps.append((y2, z.utility(g2, t, pos), z.reid(g) - r2, g2))
        safe = [s for s in steps if s[0] == 0]
        g = max(safe, key=lambda s: s[1])[3] if safe else \
            max(steps, key=lambda s: s[2] / (z.utility(g, t, pos) - s[1] + 0.01))[3]
    return g


def evaluate(z, p, request, grant, need):
    t, pos = p["target"], p.get("positive")
    needed = set(need["needed"])
    y, r = z.label(grant)
    auc = z.utility(grant, t, pos)
    return dict(safe=1 - y, reid=r, auc=auc, retention=(auc - 0.5) / (need["ref_auc"] - 0.5),
                target_granted=int(t in grant), n_granted=len(grant),
                n_generalized=sum(lv != "exact" for lv in grant.values()),
                unnecessary=len(set(grant) - needed - {t}), missing_needed=len(needed - set(grant)))


def purposes(names=None):
    ps = json.load(open(f"{HERE}/purposes.json", encoding="utf-8"))
    return [p for p in ps if not names or p["dataset"] in names]


def load_needs(z, p, request, path=None):
    """Ground truth per purpose (importance cached in outputs/needs.json or path); columns the purpose text names
    explicitly ("named" in purposes.json) are needed whatever their importance."""
    path = path or f"{P2}/needs.json"
    allneeds = json.load(open(path)) if os.path.exists(path) else {}
    if p["id"] not in allneeds:
        imp = z.needs(p["target"], request, p.get("positive"))
        needed = sorted(c for c, v in imp.items() if v >= NEED_THR)
        full = {c: "exact" for c in request}
        allneeds[p["id"]] = dict(importance=imp, needed=needed,
                                 ref_auc=z.utility(full, p["target"], p.get("positive")),
                                 needed_auc=z.utility({c: "exact" for c in needed + [p["target"]]},
                                                      p["target"], p.get("positive")))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):                          # another run may have added purposes meanwhile
            allneeds = {**json.load(open(path)), p["id"]: allneeds[p["id"]]}
        with open(path + f".{os.getpid()}", "w") as f:    # atomic: parallel runs read this file
            json.dump(allneeds, f, indent=1)
        os.replace(path + f".{os.getpid()}", path)
    need = allneeds[p["id"]]
    return dict(need, needed=sorted(set(need["needed"]) | set(p.get("named", []))))


def main(*names):
    rows = []
    for name in sorted({p["dataset"] for p in purposes(names)}):
        z = Zone(name)
        for p in purposes([name]):
            request = z.columns                                              # requester asks for the whole table
            need = load_needs(z, p, request)
            full = {c: "exact" for c in request}
            grants = {"As requested": full, "Deny if risky": {} if z.label(full)[0] else full,
                      "Rule (drop ids, coarsen QIs)": rule(z, request),
                      "Purpose-blind greedy": greedy_blind(z, full),
                      "Target-known search": search_known(z, p, need["needed"])}
            for m, g in grants.items():
                rows.append(dict(purpose=p["id"], method=m, **evaluate(z, p, request, g, need)))
            print(p["id"], "needed", len(need["needed"]), "/", len(request), "ref AUC", round(need["ref_auc"], 3),
                  "needed AUC", round(need["needed_auc"], 3), flush=True)
            print(pd.DataFrame(rows[-len(grants):]).drop(columns="purpose").round(3).to_string(index=False), flush=True)
    out = pd.DataFrame(rows)
    os.makedirs(P2, exist_ok=True)
    out.to_csv(f"{P2}/baselines{'_' + '_'.join(names) if names else ''}.csv", index=False)


if __name__ == "__main__":
    main(*sys.argv[1:])
