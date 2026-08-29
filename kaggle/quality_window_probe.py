"""quality_window_probe.py — can the model actually RANK dates inside the window the product offers?

ArtaMatch's product question is not "is this couple's AUC above chance". It is: given HIS fixed birth
date, order HER candidate birth dates across +/-12 years. A model can score well on held-out couples and
still be useless at that, if what it reads is birth ERA — because era is very nearly constant across a
24-year window, so every candidate gets almost the same score and the ranking is noise.

This measures it on the artifact rather than arguing it from the rule names. For each of N real men it
sweeps her date across +/-12 years, one candidate per month, scores every candidate with the saved model,
and compares two spreads:

  WITHIN  the spread of scores inside one man's window   — the signal the product ranks on
  BETWEEN the spread of scores across different men      — the signal the AUC measured

If WITHIN is a small fraction of BETWEEN, the held-out AUC is real but belongs to era, and the ranking
the product shows a member is arbitrary. It also reports how many of the model's own rules ever change
state inside a window: a rule that never flips cannot contribute to the ordering at all.

Usage: quality_window_probe.py <corpus_dir> <model.json> [n_men]
"""
import json, os, subprocess, sys, tempfile, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from v22_nnls import build as full_build

D = os.path.expanduser(sys.argv[1])
MODEL = json.load(open(os.path.expanduser(sys.argv[2])))
N_MEN = int(sys.argv[3]) if len(sys.argv) > 3 else 120
STEP_MONTHS = 1
SPAN_YEARS = 12


def main():
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    men = te.dob_a.dropna().unique()[:N_MEN]
    rows = []
    for m in men:
        y, mo, d = int(m[:4]), int(m[5:7]), int(m[8:10])
        for k in range(-SPAN_YEARS * 12, SPAN_YEARS * 12 + 1, STEP_MONTHS):
            yy = y + (mo - 1 + k) // 12
            mm = (mo - 1 + k) % 12 + 1
            dd = min(d, 28)
            rows.append({"dob_a": m, "dob_b": f"{yy:04d}-{mm:02d}-{dd:02d}",
                         "start": "0000-00-00", "ended_in_divorce": 0, "_man": m, "_off": k})
    sw = pd.DataFrame(rows)
    print(f"  {len(men)} men x {len(sw)//len(men)} candidate dates = {len(sw):,} pairs "
          f"across +/-{SPAN_YEARS} years")

    tmp = tempfile.mkdtemp(prefix="aq_window_")
    sw[["dob_a", "dob_b", "start", "ended_in_divorce"]].to_csv(f"{tmp}/train.csv", index=False)
    sw.head(50).assign(id=[f"r{i:06d}" for i in range(50)])[["id", "dob_a", "dob_b", "start"]].to_csv(
        f"{tmp}/test.csv", index=False)
    env = dict(os.environ, AQ_NO_PLACE="1", AQ_SRC=tmp, AQ_OUT=tmp)
    r = subprocess.run([os.path.expanduser("~/.artamatch-venv/bin/python"),
                        os.path.expanduser("~/Studio/artamatch/research/sidereal/kerykeion_phases.py")],
                       env=env, capture_output=True, text=True)
    if not os.path.exists(f"{tmp}/phases.npz"):
        print("  chart build failed:\n" + r.stdout[-1500:] + r.stderr[-1500:]); sys.exit(1)
    Z = np.load(f"{tmp}/phases.npz", allow_pickle=True)
    tr = pd.read_csv(f"{tmp}/train.csv", dtype=str)
    # use the SAME bank builder the model was fitted with, or the probe silently drops the very
    # statements it is meant to be testing
    X, names = full_build(tr, Z, "train")
    pos = {n: i for i, n in enumerate(names)}
    w = MODEL["weights"]
    # a statement may be carried as its negation; rebuild that column rather than skipping it
    base = lambda k: k[4:-1] if k.startswith("NOT(") and k.endswith(")") else k
    missing = [k for k in w if base(k) not in pos]
    keys = [k for k in w if base(k) in pos]
    built = []
    for k in keys:
        col = X[:, pos[base(k)]]
        built.append(1.0 - col if k.startswith("NOT(") else col)
    X = np.column_stack(built) if built else X[:, :0]
    cols = list(range(X.shape[1]))
    coef = np.array([w[k] for k in keys])
    if missing:
        print(f"  note: {len(missing)} of {len(w)} model rules are not reproducible here, skipped")
    score = X[:, cols] @ coef + MODEL.get("intercept", 0.0)
    sw["score"] = score

    g = sw.groupby("_man").score
    within = (g.max() - g.min())
    between = sw.groupby("_man").score.mean()
    print(f"\n  WITHIN  one man's +/-12y window: mean spread {within.mean():.4f} "
          f"(median {within.median():.4f})")
    print(f"  BETWEEN different men:            spread {between.max() - between.min():.4f} "
          f"(sd {between.std():.4f})")
    ratio = within.mean() / max(1e-12, (between.max() - between.min()))
    print(f"  ratio WITHIN/BETWEEN: {ratio:.3f}")

    flip = 0
    for c in cols:
        v = X[:, c]
        if any(v[sw._man.values == m].std() > 0 for m in men[:40]):
            flip += 1
        del v
    print(f"\n  model rules that ever change state inside a window: {flip} of {len(cols)}")
    # where does the best candidate sit? if the model is era-driven the optimum pins to a window edge
    best = sw.loc[g.idxmax()]
    edge = (best._off.abs() >= SPAN_YEARS * 12 - STEP_MONTHS).mean()
    print(f"  best candidate lands on the window EDGE for {edge:.0%} of men "
          f"(a monotone era trend pins it there; genuine pair structure would not)")
    print(f"  best-candidate offset in years: mean {best._off.mean()/12:+.1f} · "
          f"sd {best._off.std()/12:.1f}")
    json.dump({"n_men": int(len(men)), "within_mean": float(within.mean()),
               "between_range": float(between.max() - between.min()), "ratio": float(ratio),
               "rules_that_flip": int(flip), "rules_total": int(len(cols)),
               "best_on_edge_share": float(edge)},
              open(os.path.expanduser("~/.artamatch-dev/window_probe.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
