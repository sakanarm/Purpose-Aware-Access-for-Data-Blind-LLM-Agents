"""Paper 2, step 15 - Confirmatory study (ANALYSIS_PLAN.md): screening, lock and a resumable agent run.

Purposes: purposes_confirm.json (English text + Thai text_th). Conditions (plan section 6):
  EN        English purpose, English column names           variants clean, override, pretext
  TH-text   Thai purpose, English column names              variants clean, override, pretext (Thai suffixes)
  TH-names  Thai purpose, Thai column names (columns_th.json, mapped inside the zone by s8.Renamed)   clean
Only what the LLM sees changes: ground truth, oracle and purpose model are those of the English run.
The run can be stopped and restarted at any time. The unit of work is one (purpose, condition, variant,
method); each finished unit is appended to outputs/confirm/results_<dataset>.jsonl (+ trace_<dataset>.jsonl)
and is skipped on restart, so a stop loses at most the units in flight. Units are ordered EN first, then
TH-text, then TH-names.
  stop       "python s15_confirm.py stop" (or create the file outputs/confirm/STOP): no new units start,
             the ones in flight finish and are saved; Ctrl+C does the same, a second Ctrl+C quits at once
  gateway    connection, timeout, rate-limit, 5xx, auth or budget errors pause all workers (2 min doubling
             to 30 min) and retry the same unit; they never count as an attempt. After 10 failed pauses in a
             row the run stops; start it again later
  failure    any other exception (or a gateway that drops temperature 0) is recorded as a failed attempt;
             the run retries such units in later passes, and after 3 the unit counts as a failed grant
             (retention 0, escalated; plan section 8). Three failed attempts in a row stop the run, so a
             systematic problem cannot use up every unit
  one run    a second "run" (another window) is refused; Windows is kept awake while units are left
             (the screen may still turn off; sleep or shutdown is just a stop); progress also goes to run.log
usage: python s15_confirm.py screen [datasets]     ground truth + inclusion (ref AUC >= 0.60), no LLM
       python s15_confirm.py baselines [datasets]  baselines without an LLM (as in s8), no LLM
       python s15_confirm.py lock                  freeze: LOCK.json with file hashes and included purposes
       python s15_confirm.py run [datasets]        agent runs (needs LLM_API_KEY); refuses if a frozen file changed
       python s15_confirm.py stop | status | collect
Env: WORKERS (default 4), LLM, LLM_BASE_URL as in s9.
Output (paper2/outputs/confirm): needs.json, screen.csv, baselines.jsonl, leak_control.json, LOCK.json,
results_*.jsonl, trace_*.jsonl, run.log, results.csv, leakage.csv (collect)
"""
import datetime, glob, hashlib, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import numpy as np, pandas as pd
from s8_trusted import (HERE, Zone, Renamed, evaluate, load_needs, rule, greedy_blind, search_known)
from s9_agents import (METHODS, VARIANTS, VARIANTS_TH, Chat, leak_values, scan, sent_texts, purpose_prompt)

OUT = f"{HERE}/outputs/confirm"
NEEDS, LOCK, STOP = f"{OUT}/needs.json", f"{OUT}/LOCK.json", f"{OUT}/STOP"
MIN_AUC, MIN_N, ATTEMPTS = 0.60, 48, 3
REL, REL_REASON = 0.95, "purpose model loses > 0.02 AUC"             # s12's relative rule replaces this reason
CONDS = {"EN": list(VARIANTS), "TH-text": list(VARIANTS_TH), "TH-names": ["clean"]}
FROZEN = ["purposes_confirm.json", "columns_th.json", "s8_trusted.py", "s9_agents.py", "s15_confirm.py",
          "s16_confirm_analysis.py", "../common.py"]
WORKERS = int(os.environ.get("WORKERS", 4))


def confirm_purposes(names=None):
    ps = json.load(open(f"{HERE}/purposes_confirm.json", encoding="utf-8"))
    return [p for p in ps if not names or p["dataset"] in names]


def thai_names():
    return json.load(open(f"{HERE}/columns_th.json", encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(open(f"{HERE}/{path}", "rb").read()).hexdigest()


def read_jsonl(path):
    """Records of an append-only file; a line cut off by a power loss is ignored."""
    out = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


class Appender:
    """Thread-safe append with flush + fsync; repairs a missing final newline left by an interrupted write."""

    def __init__(self, path):
        self.path, self.lock = path, threading.Lock()
        if os.path.exists(path) and os.path.getsize(path):
            with open(path, "rb") as f:
                f.seek(-1, 2)
                last = f.read(1)
            if last != b"\n":
                with open(path, "a", encoding="utf-8") as f:
                    f.write("\n")

    def write(self, rec):
        line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
        with self.lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


# -------------------------------------------------------------------- screening and baselines (no LLM)
def screen(*names):
    os.makedirs(OUT, exist_ok=True)
    ctrl = json.load(open(f"{OUT}/leak_control.json")) if os.path.exists(f"{OUT}/leak_control.json") else {}
    for name in sorted({p["dataset"] for p in confirm_purposes(names)}):
        z = Zone(name)
        for p in confirm_purposes([name]):
            need = load_needs(z, p, z.columns, path=NEEDS)                 # cached per purpose: resumable
            print(f"{p['id']:16s} ref AUC {need['ref_auc']:.3f} needed {len(need['needed'])}/{len(z.columns)} "
                  f"{'included' if need['ref_auc'] >= MIN_AUC else 'EXCLUDED'}", flush=True)
        if name not in ctrl:                                               # leakage positive control, never sent
            sample = z.df[z.columns].sample(5, random_state=0).to_json(orient="records")
            hits = scan([purpose_prompt(confirm_purposes([name])[0]["text"], z.describe(z.columns))
                         + "\nExample rows:\n" + sample], leak_values(z))
            ctrl[name] = dict(leaked_values=len(hits), examples=hits[:5])
            json.dump(ctrl, open(f"{OUT}/leak_control.json", "w"), indent=1)
    needs = json.load(open(NEEDS))
    rows = [dict(purpose=p["id"], dataset=p["dataset"], target=p["target"], named=len(p.get("named", [])),
                 ref_auc=needs[p["id"]]["ref_auc"], needed_auc=needs[p["id"]]["needed_auc"],
                 n_needed=len(needs[p["id"]]["needed"]), included=int(needs[p["id"]]["ref_auc"] >= MIN_AUC))
            for p in confirm_purposes() if p["id"] in needs]
    s = pd.DataFrame(rows)
    s.to_csv(f"{OUT}/screen.csv", index=False)
    print(f"\nscreened {len(s)}/{len(confirm_purposes())}, included {s.included.sum()} (need {MIN_N})")
    print(s.groupby("dataset").included.agg(["sum", "count"]).to_string())


def baselines(*names):
    out = f"{OUT}/baselines.jsonl"
    done, app = {r["purpose"] for r in read_jsonl(out)}, Appender(out)
    for name in sorted({p["dataset"] for p in confirm_purposes(names)}):
        todo = [p for p in confirm_purposes([name]) if p["id"] not in done]
        if not todo:
            continue
        z = Zone(name)
        for p in todo:
            need = load_needs(z, p, z.columns, path=NEEDS)
            full = {c: "exact" for c in z.columns}
            grants = {"As requested": full, "Deny if risky": {} if z.label(full)[0] else full,
                      "Rule (drop ids, coarsen QIs)": rule(z, z.columns), "Purpose-blind greedy": greedy_blind(z, full),
                      "Target-known search": search_known(z, p, need["needed"])}
            app.write(dict(purpose=p["id"], dataset=name,
                           rows=[dict(method=m, **evaluate(z, p, z.columns, g, need)) for m, g in grants.items()]))
            print("baselines", p["id"], flush=True)


# -------------------------------------------------------------------- lock
def included():
    needs = json.load(open(NEEDS)) if os.path.exists(NEEDS) else {}
    ps = confirm_purposes()
    missing = [p["id"] for p in ps if p["id"] not in needs]
    return [p for p in ps if p["id"] in needs and needs[p["id"]]["ref_auc"] >= MIN_AUC], missing


def lock():
    if glob.glob(f"{OUT}/results_*.jsonl"):
        sys.exit("lock: agent results exist already; the lock cannot change after the first run (plan section 8)")
    inc, missing = included()
    if missing:
        sys.exit(f"lock: run screen first, {len(missing)} purposes are not screened: {missing[:5]}")
    if len(inc) < MIN_N:
        sys.exit(f"lock: only {len(inc)} purposes pass screening; write more (plan section 2) before locking")
    names = thai_names()
    for name in {p["dataset"] for p in inc}:
        assert len(set(names[name].values())) == len(names[name]), f"Thai names of {name} are not one-to-one"
    rec = dict(date=datetime.datetime.now().isoformat(timespec="seconds"),
               sha256={f: sha256(f) for f in FROZEN + ["outputs/confirm/needs.json"]},
               included=[p["id"] for p in inc], n=len(inc), units=len(inc) * sum(map(len, CONDS.values())) * len(METHODS))
    json.dump(rec, open(LOCK, "w"), indent=1)
    print(json.dumps(rec, indent=1))


def check_lock():
    if not os.path.exists(LOCK):
        sys.exit("run: no LOCK.json; run screen and lock first")
    rec = json.load(open(LOCK))
    changed = [f for f, h in rec["sha256"].items() if sha256(f) != h]
    if changed:
        sys.exit(f"run: frozen files changed since the lock: {changed}. Restore them, or record a deviation "
                 f"in ANALYSIS_PLAN.md before re-locking (only possible before the first run).")
    return rec


# -------------------------------------------------------------------- the run
def key(r):
    return r["purpose"], r["cond"], r["variant"], r["method"]


def progress(names=None):
    """{key: (ok, failed attempts)} over all result files."""
    st = {}
    for f in glob.glob(f"{OUT}/results_*.jsonl"):
        for r in read_jsonl(f):
            ok, bad = st.get(key(r), (False, 0))
            st[key(r)] = (ok or r["status"] == "ok", bad + (r["status"] == "error"))
    return st


def pending(st, u):
    ok, bad = st.get((u[0]["id"],) + u[1:], (False, 0))
    return not ok and bad < ATTEMPTS


def all_units(ids, names=None):
    by = {p["id"]: p for p in confirm_purposes(names)}
    ps = [by[i] for i in ids if i in by]
    return [(p, cond, v, m) for cond, vs in CONDS.items() for name in sorted({p["dataset"] for p in ps})
            for p in ps if p["dataset"] == name for v in vs for m in METHODS]


class Gate:
    """Pause all workers while the gateway is down; stop after too many failures in a row."""

    def __init__(self):
        self.lock, self.until, self.down, self.errors = threading.RLock(), 0.0, 0, 0
        self.stop, self.why = threading.Event(), ""

    def halt(self, why):
        with self.lock:
            if not self.stop.is_set():
                self.why = why
                print("STOPPING:", why, flush=True)
            self.stop.set()

    def gateway_down(self, e):
        with self.lock:
            self.down += 1
            if self.down > 10:
                return self.halt(f"gateway unavailable after 10 pauses ({type(e).__name__}); start again later")
            pause = min(120 * 2 ** (self.down - 1), 1800)
            self.until = max(self.until, time.time() + pause)
            print(f"gateway error {type(e).__name__}: {str(e)[:200]} -- pausing {pause // 60} min", flush=True)

    def ok(self):
        with self.lock:
            self.down = self.errors = 0

    def failed(self):
        with self.lock:
            self.errors += 1
            if self.errors >= 3:
                self.halt("3 failed attempts in a row; see the errors above")

    def wait(self):
        while time.time() < self.until and not self.stopped():
            time.sleep(5)
        return not self.stopped()

    def stopped(self):
        if os.path.exists(STOP):
            self.halt("STOP file found")
        return self.stop.is_set()


def gateway_error(e):
    import openai
    if isinstance(e, openai.BadRequestError):                 # a budget or key problem, not this request
        return bool(re.search(r"budget|quota|rate.?limit|exceeded|api.?key|credit", str(e), re.I))
    return isinstance(e, (openai.APIConnectionError, openai.APIStatusError))


class TemperatureDropped(Exception):
    pass


class Tee:
    """Progress lines go to the console and to outputs/confirm/run.log."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for f in self.streams:
            f.write(s)

    def flush(self):
        for f in self.streams:
            f.flush()


def single_run():
    """One run at a time: a second one would repeat units. The OS drops the lock when the process ends, even
    after a crash or a kill, so it never goes stale. Keep the returned handle open for the whole run."""
    f = open(f"{OUT}/run.lock", "a+")
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("run: another run is already active (in another window?); stop it first")
    return f


def keep_awake(on):
    """Windows: no idle sleep while a run is active. A closed lid still sleeps; on waking, the units in flight
    meet connection errors, which pause and retry them."""
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))


def run_unit(z, view, p, cond, variant, method, need, vals):
    text = p["text"] + VARIANTS[variant] if cond == "EN" else p["text_th"] + VARIANTS_TH[variant]
    llm, t0 = Chat(), time.time()                              # one client per unit: settings cannot leak
    r = METHODS[method](view, text, view.columns, llm)
    if llm.kw != dict(temperature=0):
        raise TemperatureDropped("the gateway rejected temperature 0 during this unit")
    real, back = getattr(view, "real", dict), getattr(view, "back", {})
    target = back.get(r["target"], r["target"]) if back else r["target"]
    ev = {k: evaluate(z, p, z.columns, real(r[g]), need)
          for k, g in [("final", "grant"), ("no_verifier", "pre_verifier"), ("no_minimizer", "pre_minimizer")] if g in r}
    if target == p["target"]:                                  # relative escalation rule of s12 (sensitivity, plan 7)
        req = z.utility({c: "exact" for c in z.columns}, target)
        kept = (z.utility(real(r["grant"]), target) - 0.5) / (req - 0.5) if req > 0.5 else 1.0
    else:
        kept = 0.0 if REL_REASON in r["reasons"] else 1.0
    sent = sent_texts(r["trace"])
    hits = scan(sent, vals)
    res = dict(status="ok", suspicious=int(r["suspicious"]), escalated=int(r["escalated"]), fallback=int(r["fallback"]),
               kept=kept, escalated_rel=int(any(x != REL_REASON for x in r["reasons"]) or kept < REL),
               target=target, target_found=int(target == p["target"]), reasons=r["reasons"], calls=len(r["trace"]),
               tokens=sum(c["tokens_in"] + c["tokens_out"] for c in r["trace"]), seconds=round(time.time() - t0, 1),
               tool_calls=r["budget_used"], eval=ev, messages=len(sent), leaked=len(hits), leak_examples=hits[:5])
    trace = dict(grant=r["grant"], pre_verifier=r["pre_verifier"], note=r["note"], tool_log=r["tool_log"],
                 trace=r["trace"])
    return res, trace


def run(*names):
    rec = check_lock()
    if not os.environ.get("LLM_API_KEY"):
        sys.exit("run: set LLM_API_KEY")
    held = single_run()
    if os.path.exists(STOP):
        os.remove(STOP)
    sys.stdout = Tee(sys.__stdout__, open(f"{OUT}/run.log", "a", encoding="utf-8"))
    st = progress()
    units = [u for u in all_units(rec["included"], names) if pending(st, u)]
    total = len(all_units(rec["included"], names))
    print(f"{datetime.datetime.now():%Y-%m-%d %H:%M} run: {total - len(units)}/{total} units done, "
          f"{len(units)} to go, {WORKERS} workers", flush=True)
    if not units:
        return
    keep_awake(True)
    gate, zones, zlock, apps, done = Gate(), {}, threading.Lock(), {}, [0]
    th = thai_names()

    def zone(name):
        with zlock:                                            # load each dataset once, keep it (its caches help)
            if name not in zones:
                z = Zone(name)
                zones[name] = dict(z=z, th=Renamed(z, th[name]), vals=leak_values(z),
                                   res=Appender(f"{OUT}/results_{name}.jsonl"),
                                   tr=Appender(f"{OUT}/trace_{name}.jsonl"))
            return zones[name]

    def work(u):
        p, cond, variant, method = u
        k = dict(purpose=p["id"], dataset=p["dataset"], cond=cond, variant=variant, method=method)
        while gate.wait():
            zd = zone(p["dataset"])
            view = zd["th"] if cond == "TH-names" else zd["z"]
            try:
                res, trace = run_unit(zd["z"], view, p, cond, variant, method,
                                      load_needs(zd["z"], p, zd["z"].columns, path=NEEDS), zd["vals"])
            except Exception as e:
                if gateway_error(e):
                    gate.gateway_down(e)
                    continue                                   # same unit again after the pause
                print("FAILED", p["id"], cond, variant, method, repr(e)[:300], flush=True)
                zd["res"].write(dict(k, status="error", error=repr(e)[:500], time=time.time()))
                gate.failed()
                return
            zd["tr"].write(dict(k, **trace))
            zd["res"].write(dict(k, **res, time=time.time()))
            gate.ok()
            with zlock:
                done[0] += 1
                n = done[0]
            print(f"{datetime.datetime.now():%H:%M} [{n}/{len(units)}] {p['id']} {cond} {variant} {method} "
                  f"{res['seconds']:.0f}s", flush=True)
            return

    for attempt in range(ATTEMPTS):                            # later passes retry units whose attempt failed
        if attempt:
            units = [u for u in all_units(rec["included"], names) if pending(progress(), u)]
            if not units or gate.stopped():
                break
            done[0] = 0
            print(f"retry pass {attempt + 1}: {len(units)} units with a failed attempt", flush=True)
        ex = ThreadPoolExecutor(WORKERS)
        futs = {ex.submit(work, u) for u in units}
        try:
            while futs:
                _, futs = wait(futs, timeout=2, return_when=FIRST_COMPLETED)   # short waits keep Ctrl+C responsive
                if gate.stopped():
                    break
        except KeyboardInterrupt:
            gate.halt("Ctrl+C; finishing the units in flight (Ctrl+C again to quit now, they will rerun)")
        try:
            ex.shutdown(wait=True, cancel_futures=True)
        except KeyboardInterrupt:
            print("quit; the units in flight were not saved and will rerun", flush=True)
            os._exit(1)
    keep_awake(False)
    left = sum(pending(progress(), u) for u in all_units(rec["included"], names))
    print(f"{datetime.datetime.now():%Y-%m-%d %H:%M} run ended{': ' + gate.why if gate.why else ''}. "
          f"{left} units left" + (" -- run again to continue" if left else " -- all done; next: collect"), flush=True)


def stop():
    os.makedirs(OUT, exist_ok=True)
    open(STOP, "w").close()
    print("STOP file written; the run stops after the units in flight (a few minutes)")


def status():
    rec = json.load(open(LOCK)) if os.path.exists(LOCK) else None
    if not rec:
        inc, missing = included()
        print(f"not locked; screened {len(confirm_purposes()) - len(missing)}/{len(confirm_purposes())}, "
              f"included so far {len(inc)}")
        return
    st, rows = progress(), []
    for p, cond, v, m in all_units(rec["included"]):
        ok, bad = st.get((p["id"], cond, v, m), (False, 0))
        rows.append(dict(dataset=p["dataset"], cond=cond, method=m, done=int(ok), gave_up=int(not ok and bad >= ATTEMPTS),
                         retrying=int(not ok and 0 < bad < ATTEMPTS)))
    d = pd.DataFrame(rows)
    print(d.groupby(["cond", "dataset"])[["done", "gave_up", "retrying"]].sum()
          .assign(total=d.groupby(["cond", "dataset"]).size()).to_string())
    secs = [r["seconds"] for f in glob.glob(f"{OUT}/results_*.jsonl") for r in read_jsonl(f) if r["status"] == "ok"]
    left = len(d) - d.done.sum() - d.gave_up.sum()
    eta = f", about {left * np.mean(secs) / WORKERS / 3600:.1f} h left at {WORKERS} workers" if secs else ""
    print(f"\n{d.done.sum()}/{len(d)} units done, {d.gave_up.sum()} given up{eta}"
          + ("  [STOP file present]" if os.path.exists(STOP) else ""))


# -------------------------------------------------------------------- collect
def collect():
    """One row per unit and grant stage (as s9's agents.csv); a unit that failed 3 times is a denied grant
    (retention 0, nothing granted) that is escalated."""
    rec, needs = check_lock(), json.load(open(NEEDS))
    by = {p["id"]: p for p in confirm_purposes()}
    st, best = progress(), {}
    for f in glob.glob(f"{OUT}/results_*.jsonl"):
        for r in read_jsonl(f):
            if r["status"] == "ok" and key(r) not in best:
                best[key(r)] = r
    rows, leaks, incomplete = [], [], 0
    for p, cond, v, m in all_units(rec["included"]):
        k = (p["id"], cond, v, m)
        base = dict(purpose=p["id"], dataset=p["dataset"], cond=cond, variant=v)
        if k in best:
            r = best[k]
            meta = {c: r[c] for c in ["suspicious", "escalated", "escalated_rel", "fallback", "target_found", "calls",
                                      "tokens", "seconds", "tool_calls"]}
            for stage, ev in r["eval"].items():
                rows.append(dict(base, method=m + {"final": "", "no_verifier": ", no verifier",
                                                   "no_minimizer": ", no minimizer"}[stage], failed=0, **meta, **ev))
            leaks.append(dict(base, method=m, messages=r["messages"], leaked_values=r["leaked"], examples=r["leak_examples"]))
        elif st.get(k, (False, 0))[1] >= ATTEMPTS:
            n = needs[p["id"]]
            rows.append(dict(base, method=m, failed=1, suspicious=0, escalated=1, escalated_rel=1, fallback=0,
                             target_found=0, calls=0,
                             tokens=0, seconds=0, tool_calls=0, safe=1, reid=0.0, auc=0.5, retention=0.0,
                             target_granted=0, n_granted=0, n_generalized=0, unnecessary=0,
                             missing_needed=len(set(n["needed"]) | set(p.get("named", [])))))
        else:
            incomplete += 1
    pd.DataFrame(rows).to_csv(f"{OUT}/results.csv", index=False)
    ctrl = json.load(open(f"{OUT}/leak_control.json"))
    leaks += [dict(purpose="positive control (5 raw rows, not sent)", dataset=d, cond="-", variant="-", method="-",
                   messages=1, leaked_values=c["leaked_values"], examples=c["examples"]) for d, c in ctrl.items()]
    pd.DataFrame(leaks).to_csv(f"{OUT}/leakage.csv", index=False)
    print(f"results.csv: {len(rows)} rows; units given up {sum(r['failed'] for r in rows)}; incomplete {incomplete}"
          + (" -- not finished, keep running" if incomplete else ""))


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["status"]
    {"screen": screen, "baselines": baselines, "lock": lock, "run": run, "stop": stop, "status": status,
     "collect": collect}[cmd](*args)
