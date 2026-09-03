"""build_systems_all.py — MERGE every systems_*.py module into ONE pseudo-body file for the corpus.

For AQ_DIR (default ~/.artamatch-dev/tilldeath_wt3) read full.csv + phases.npz, build for every
person (pid_a = him, pid_b = her) the longitude dict L from phases.npz (body order from the npz
'bodies' array; true_/mean_ prefixes stripped; NaN bodies — ascendant / medium_coeli — dropped;
L["_female"] added), call every system's fn(y, m, d, L), map the state to its angle

        discrete   state s of N  ->  (s + 1) * 360 / N
        continuous (n == 0)      ->  degrees as returned, mod 360

and write

        AQ_DIR/systems_all.npz            theta_a_sys, theta_b_sys (degrees), names, nstates
        AQ_DIR/systems_all_manifest.json  [{name, n, tradition, desc}], plus 'skipped'

A system that throws (or returns an out-of-range state) for ANY row is skipped entirely and
recorded in the manifest under 'skipped' with the first offending row and the error.

Every module exposes SYSTEMS = [{"name", "n", "desc", "fn"}, ...]; the tradition is the module's
SLUG if it has one, else the filename suffix after 'systems_'. Modules are loaded by path
(importlib) because several filenames carry hyphens.

    AQ_DIR=~/.artamatch-dev/tilldeath_wt3 python build_systems_all.py
    AQ_MODULES=systems_western.py,systems_vedic.py   # optional subset, comma-separated basenames
    AQ_NPROC=8                                       # workers (fork), default = cpu count
    AQ_LIMIT=2000                                    # optional: first N couples only (smoke)
"""
import glob, importlib.util, json, math, os, sys, time
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
NPROC = int(os.environ.get("AQ_NPROC", "0")) or max(1, os.cpu_count() or 1)
LIMIT = int(os.environ.get("AQ_LIMIT", "0"))
MODS = [x for x in os.environ.get("AQ_MODULES", "").split(",") if x] or \
       sorted(os.path.basename(p) for p in glob.glob(f"{HERE}/systems_*.py"))


def load_module(basename):
    path = f"{HERE}/{basename}"
    modname = "aq_" + basename[:-3].replace("-", "_")
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- the merged table ---------------------------------------------------------------------------
MODULES = [(b, load_module(b)) for b in MODS]
TABLE = []      # (name, n, tradition, desc, fn)
for base, mod in MODULES:
    trad = getattr(mod, "SLUG", None) or base[len("systems_"):-3]
    for s in mod.SYSTEMS:
        TABLE.append((s["name"], int(s["n"]), trad, s.get("desc", ""), s["fn"]))
_names = [t[0] for t in TABLE]
_dup = sorted({x for x in _names if _names.count(x) > 1})
assert not _dup, f"duplicate system names across modules: {_dup}"
NAMES = _names
NST = [t[1] for t in TABLE]
FNS = [t[4] for t in TABLE]


def angle_of(v, n, name):
    """State -> angle in degrees; raises on an out-of-contract value."""
    if n == 0:
        f = float(v)
        if not math.isfinite(f):
            raise ValueError(f"{name}: non-finite continuous value {v!r}")
        return f % 360.0
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"{name}: state must be int, got {type(v).__name__} {v!r}")
    if not 0 <= v < n:
        raise ValueError(f"{name}: state {v} out of range [0,{n})")
    return (v + 1) * 360.0 / n


# ---- per-row work (runs in forked workers) -------------------------------------------------------
_G = {}


def _work(args):
    """args: (side, lo, hi). Returns (side, lo, angles[hi-lo, nsys] with NaN where a system failed,
    errors {name: (row, err)} — first failure only per system)."""
    side, lo, hi = args
    dobs, theta, bodies, female = _G["dob"][side], _G["theta"][side], _G["bodies"], side == "b"
    out = np.full((hi - lo, len(TABLE)), np.nan, np.float64)
    errs = {}
    for r in range(lo, hi):
        iso = dobs[r]
        y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
        row = theta[r]
        L = {b: float(v) for b, v in zip(bodies, row) if not (isinstance(v, float) and math.isnan(v))}
        L["_female"] = female
        for k, (name, n, _t, _d, fn) in enumerate(TABLE):
            if name in errs:
                continue
            try:
                out[r - lo, k] = angle_of(fn(y, m, d, dict(L)), n, name)
            except Exception as e:      # noqa: BLE001 — recorded, the system is dropped later
                errs[name] = (r, f"{type(e).__name__}: {e}")
    return side, lo, out, errs


def build():
    t0 = time.time()
    full = pd.read_csv(f"{D_}/full.csv", dtype=str)
    if LIMIT:
        full = full.iloc[:LIMIT]
    Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
    raw_bodies = [str(b) for b in Z["bodies"]]
    bodies = [b.replace("true_", "").replace("mean_", "") for b in raw_bodies]
    nrow = len(full)
    _G["dob"] = {"a": full["true_dob_a"].tolist(), "b": full["true_dob_b"].tolist()}
    _G["theta"] = {"a": np.asarray(Z["theta_a_train"], np.float64)[:nrow],
                   "b": np.asarray(Z["theta_b_train"], np.float64)[:nrow]}
    _G["bodies"] = bodies
    print(f"{len(MODULES)} modules · {len(TABLE)} systems · {nrow:,} couples · bodies={bodies} · {NPROC} workers", flush=True)

    chunk = max(500, nrow // (NPROC * 8) + 1)
    jobs = [(side, lo, min(lo + chunk, nrow)) for side in ("a", "b") for lo in range(0, nrow, chunk)]
    A = np.full((nrow, len(TABLE)), np.nan, np.float64)
    B = np.full((nrow, len(TABLE)), np.nan, np.float64)
    errs = {}
    if NPROC > 1:
        import multiprocessing as mp
        ctx = mp.get_context("fork")
        with ctx.Pool(NPROC) as pool:
            results = pool.imap_unordered(_work, jobs)
            done = 0
            for side, lo, out, e in results:
                (A if side == "a" else B)[lo:lo + len(out)] = out
                for k, v in e.items():
                    errs.setdefault(k, v)
                done += 1
                if done % 8 == 0 or done == len(jobs):
                    print(f"  {done}/{len(jobs)} chunks  {time.time() - t0:6.1f}s", flush=True)
    else:
        for j in jobs:
            side, lo, out, e = _work(j)
            (A if side == "a" else B)[lo:lo + len(out)] = out
            for k, v in e.items():
                errs.setdefault(k, v)

    # a system that failed anywhere, or came back NaN anywhere, is dropped whole
    bad = set(errs)
    for k, name in enumerate(NAMES):
        if name not in bad and (np.isnan(A[:, k]).any() or np.isnan(B[:, k]).any()):
            r = int(np.argmax(np.isnan(A[:, k]) | np.isnan(B[:, k])))
            errs[name] = (r, "NaN angle")
            bad.add(name)
    keep = [k for k, name in enumerate(NAMES) if name not in bad]
    A, B = A[:, keep], B[:, keep]
    assert np.isfinite(A).all() and np.isfinite(B).all()
    assert (A >= 0).all() and (A <= 360).all() and (B >= 0).all() and (B <= 360).all()
    names = [NAMES[k] for k in keep]
    nst = [NST[k] for k in keep]
    np.savez_compressed(f"{D_}/systems_all.npz", theta_a_sys=A, theta_b_sys=B,
                        names=np.array(names), nstates=np.array(nst))
    manifest = {
        "corpus": D_, "couples": nrow, "modules": [b for b, _ in MODULES],
        "bodies_in_L": bodies + ["_female"],
        "angle_rule": "discrete: (state+1)*360/N; continuous (n=0): degrees mod 360",
        "n_systems": len(names),
        "systems": [{"name": TABLE[k][0], "n": TABLE[k][1], "tradition": TABLE[k][2], "desc": TABLE[k][3]} for k in keep],
        "skipped": [{"name": nm, "row": int(errs[nm][0]), "error": errs[nm][1],
                     "tradition": TABLE[NAMES.index(nm)][2]} for nm in sorted(bad)],
        "per_tradition": {},
    }
    for s in manifest["systems"]:
        manifest["per_tradition"][s["tradition"]] = manifest["per_tradition"].get(s["tradition"], 0) + 1
    json.dump(manifest, open(f"{D_}/systems_all_manifest.json", "w"), indent=1)
    print(f"wrote {D_}/systems_all.npz · {len(names)} systems x {nrow:,} couples · skipped {len(bad)} · {time.time() - t0:.1f}s", flush=True)
    for nm in sorted(bad):
        print(f"  SKIPPED {nm}: row {errs[nm][0]} {errs[nm][1]}", flush=True)
    return manifest


if __name__ == "__main__":
    build()
