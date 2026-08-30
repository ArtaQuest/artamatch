"""bio_pool.py — one corpus of every scoreable couple, with charts, and NO label.

The target search needs to move the label while the sky stays still. Every other corpus in this
project bakes one label into the directory, which makes relabelling mean recomputing 26,000 natal
charts each time. This builds the charts once, keyed to the couple, and leaves the label out.

Also fixes the split in advance and writes it down. SEARCH is where every target definition is tried;
CONFIRM is never touched until one definition has been chosen and frozen. The split is by connected
component of the marriage graph, so a person cannot appear on both sides.

-> ~/.artamatch-dev/quality_pool/{train.csv,test.csv,phases.npz,pool.csv}
   train.csv holds the SEARCH couples, test.csv the CONFIRM couples; both carry a placeholder label,
   because the chart builder expects the columns. pool.csv is the real key: couple -> text, side.
"""
import os, subprocess, sys
import numpy as np
import pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
OUT = os.path.expanduser("~/.artamatch-dev/quality_pool")
MISSING = "0000-00-00"


def main():
    m = pd.read_csv(f"{BIO}/marriages.csv", dtype=str)
    m["desc"] = m.description.fillna("").astype(str)
    m["ya"] = pd.to_numeric(m.dob_a.astype(str).str[:4], errors="coerce")
    m["yb"] = pd.to_numeric(m.dob_b.astype(str).str[:4], errors="coerce")
    m["mid"] = (m.ya + m.yb) / 2
    weak = pd.to_numeric(m.get("weak_name", 0), errors="coerce").fillna(0)
    q = m[(weak == 0) & m.name_a.notna() & m.name_b.notna() & m.mid.notna()
          & (m.desc.str.len() >= 100)].copy()
    # full-precision dates only: a chart cast from "1881-00-00" is meaningless and the bank silently
    # fills it with NaN, which the search would then read as a feature of the label
    q = q[~q.dob_a.str.contains("-00") & ~q.dob_b.str.contains("-00")].reset_index(drop=True)

    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(q.pid_a, q.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    comp = np.array([find(a) for a in q.pid_a])
    rng = np.random.default_rng(20260830)
    uniq = rng.permutation(np.unique(comp))
    sizes = pd.Series(comp).value_counts()
    cum = np.cumsum([sizes[c] for c in uniq])
    conf = set(uniq[cum <= int(len(q) * 0.35)])          # a THIRD held back, because a target search
    q["side"] = np.where([c in conf for c in comp], "confirm", "search")
    q["comp"] = comp

    os.makedirs(OUT, exist_ok=True)
    tr = q[q.side == "search"].reset_index(drop=True)
    te = q[q.side == "confirm"].reset_index(drop=True)
    for f in (tr, te):
        f["start"] = MISSING
    tr.assign(ended_in_divorce=0)[["dob_a", "dob_b", "start", "ended_in_divorce"]].to_csv(
        f"{OUT}/train.csv", index=False)
    te.insert(0, "id", [f"c{i:06d}" for i in range(len(te))])
    te[["id", "dob_a", "dob_b", "start"]].to_csv(f"{OUT}/test.csv", index=False)
    te.assign(ended_in_divorce=0)[["id", "ended_in_divorce"]].to_csv(f"{OUT}/solution.csv", index=False)
    tr[["pid_a", "pid_b"]].assign(y_rule=0, y_alive=0).to_csv(f"{OUT}/_train_ids.csv", index=False)
    te[["id", "pid_a", "pid_b"]].assign(y_rule=0, y_alive=0).to_csv(f"{OUT}/_test_ids.csv", index=False)
    pd.concat([tr.assign(row=range(len(tr))), te.assign(row=range(len(te)))])[
        ["side", "row", "pid_a", "pid_b", "dob_a", "dob_b", "mid", "comp", "desc"]].to_csv(
        f"{OUT}/pool.csv", index=False)
    print(f"  {len(q):,} couples · search {len(tr):,} · confirm {len(te):,}")

    np_ = f"{OUT}/phases.npz"
    if os.path.exists(np_):
        os.remove(np_)
    r = subprocess.run([sys.executable, os.path.expanduser(
        "~/Studio/artamatch/research/sidereal/kerykeion_phases.py")],
        env=dict(os.environ, AQ_NO_PLACE="1", AQ_SRC=OUT, AQ_OUT=OUT),
        capture_output=True, text=True)
    if not os.path.exists(np_):
        print("    ! chart build FAILED"); print("     " + (r.stdout + r.stderr).strip()[-400:]); return
    Z = np.load(np_, allow_pickle=True)
    assert Z["theta_a_train"].shape[0] == len(tr), "charts do not match train.csv"
    ok = int(np.isfinite(Z["theta_a_train"][:, :10]).all(1).sum())
    print(f"    charts: {ok:,}/{len(tr):,} search couples complete")


if __name__ == "__main__":
    main()
