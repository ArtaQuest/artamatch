"""interaction_filter.py — which statements are really about TWO people, and which are about an era?

`side()` calls a statement pair-only when its name lacks a his_/her_ prefix. That is a test of NAMING,
not of behaviour, and it passes things it should not. comp_pluto_sign is the midpoint of the two Plutos;
cycle_neptune_pluto_phase averages each planet across the two charts. Both read both dates — and both
are functions of the MIDPOINT alone. Hold the midpoint fixed, move the two births apart by twenty years,
and neither changes. They cannot be about a couple, because they say the same thing about every couple
with that midpoint.

THE TEST. Build synthetic couples on a grid: M midpoint dates, and for each, S separations from zero up
to +/-14 years, keeping the midpoint exactly fixed. A genuine interaction must CHANGE as the separation
changes. A statement whose value is constant within every midpoint group is a function of the midpoint
alone, whatever its name says.

  interaction score = the share of midpoint groups in which the statement takes more than one value

Statements scoring zero are era in disguise. The threshold is reported, not assumed, and the whole
distribution is printed so the cut can be argued with.

Writes interaction_scores.json.
"""
import json, os, subprocess, sys, tempfile, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from v22_nnls import build
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser("~/.artamatch-dev/quality_good")
N_MID = int(os.environ.get("AQ_MID", "60"))
SEPS = [0, 1, 2, 3, 5, 7, 9, 11, 13, 14]     # years of half-separation, midpoint held fixed


def main():
    import datetime as dt
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    # some corpus dates carry a 00-00 precision marker; only full dates can anchor a midpoint grid
    full = tr.dob_a[~tr.dob_a.str.contains("-00")]
    mids = pd.to_datetime(full, format="%Y-%m-%d").iloc[:N_MID]
    rows = []
    for gi, m in enumerate(mids):
        for s in SEPS:
            a = m - pd.Timedelta(days=int(s * 365.2422))
            b = m + pd.Timedelta(days=int(s * 365.2422))
            if a.year < 1600 or b.year > 2010:
                continue
            rows.append({"dob_a": a.strftime("%Y-%m-%d"), "dob_b": b.strftime("%Y-%m-%d"),
                         "start": "0000-00-00", "ended_in_divorce": 0, "_g": gi})
    sw = pd.DataFrame(rows)
    print(f"  {sw._g.nunique()} midpoints x up to {len(SEPS)} separations = {len(sw):,} synthetic couples")
    print(f"  every couple in a group has the SAME midpoint date and a different separation\n", flush=True)

    tmp = tempfile.mkdtemp(prefix="aq_inter_")
    sw[["dob_a", "dob_b", "start", "ended_in_divorce"]].to_csv(f"{tmp}/train.csv", index=False)
    sw.head(50).assign(id=[f"r{i:06d}" for i in range(50)])[
        ["id", "dob_a", "dob_b", "start"]].to_csv(f"{tmp}/test.csv", index=False)
    env = dict(os.environ, AQ_NO_PLACE="1", AQ_SRC=tmp, AQ_OUT=tmp)
    subprocess.run([os.path.expanduser("~/.artamatch-venv/bin/python"),
                    os.path.expanduser("~/Studio/artamatch/research/sidereal/kerykeion_phases.py")],
                   env=env, capture_output=True)
    Z = np.load(f"{tmp}/phases.npz", allow_pickle=True)
    df = pd.read_csv(f"{tmp}/train.csv", dtype=str)
    X, names = build(df, Z, "train")
    g = sw._g.to_numpy()
    ok = np.array([clause_ok(n) and side(n) == "AB" for n in names])
    print(f"  bank {X.shape[1]:,} · {int(ok.sum()):,} pass the naming test\n", flush=True)

    varies = np.zeros(X.shape[1]); groups = 0
    for gi in np.unique(g):
        m = g == gi
        if m.sum() < 3:
            continue
        groups += 1
        sub = X[m]
        varies += (sub.max(0) != sub.min(0)).astype(float)
    score = varies / max(groups, 1)
    out = {names[i]: float(score[i]) for i in range(len(names)) if ok[i]}
    sc = np.array([out[n] for n in out])
    print(f"  interaction score = share of the {groups} midpoint groups in which a statement varies\n")
    for lo, hi, lab in ((0, 1e-9, "NEVER varies — a function of the midpoint alone"),
                        (1e-9, .05, "varies in under 5% of groups"),
                        (.05, .25, "5-25%"), (.25, .6, "25-60%"), (.6, 1.01, "over 60% — a real interaction")):
        k = int(((sc >= lo) & (sc < hi)).sum())
        print(f"    {lab:<48}{k:>6,}  ({k/len(sc):.0%})")
    dead = sorted([n for n in out if out[n] == 0.0])
    print(f"\n  statements that never vary with separation: {len(dead):,}")
    from collections import Counter
    import re
    c = Counter(re.sub(r"=.*", "", d.split(" AND ")[0]) for d in dead)
    for k, v in c.most_common(10):
        print(f"    {k:<44}{v:>6,}")
    json.dump(out, open(os.path.expanduser("~/.artamatch-dev/interaction_scores.json"), "w"))
    print(f"\n  saved interaction_scores.json")
    # and what the SHIPPED model would keep
    M = json.load(open(os.path.expanduser("~/.artamatch-dev/quality_final4.json")))
    base = lambda k: k[4:-1] if k.startswith("NOT(") and k.endswith(")") else k
    print(f"\n  the nine statements now shipped:")
    for k in M["weights"]:
        b = base(k)
        s_ = out.get(b, float("nan"))
        tag = "MIDPOINT ONLY" if s_ == 0 else ("weak" if s_ < .25 else "interaction")
        print(f"    {tag:<14} {s_:>5.0%}  {k[:60]}")


if __name__ == "__main__":
    main()
