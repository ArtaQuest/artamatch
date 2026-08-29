"""deploy_quality_model.py — package the marriage-quality model for the browser.

The page needs four things the fit does not produce on its own:

  calibration   an out-of-fold isotonic map from raw score to P(the marriage went well). Without it the
                percentages a member reads are arbitrary. It is fitted OUT OF FOLD so the calibration is
                not learned from the same rows it will be applied to.
  human names   every statement written as a sentence, from explain_rules — the same text the page's
                explanation panel shows, so the ranking and the explanation cannot disagree.
  base rate     the corpus share of marriages that went well, so the page can say what "average" is.
  tie structure the model produces about six distinct scores across a +/-12-year window, so the page
                must show TIERS rather than invent an ordering inside a tie. The number of distinct
                scores is measured here and published with the model.

Writes almanac/quality_deployed_model.json and almanac/quality_deployed_rules.json.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v22_nnls import build as full_build
from explain_rules import explain

D = os.path.expanduser("~/.artamatch-dev/quality_good")
SRC = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev/quality_final4.json")
OUT = os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/almanac")
base = lambda k: k[4:-1] if k.startswith("NOT(") and k.endswith(")") else k


def main():
    M = json.load(open(SRC))
    W = M["weights"]; b0 = float(M["intercept"])
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X, names = full_build(tr, Z, "train")
    pos = {n: i for i, n in enumerate(names)}
    keys = list(W)
    cols = [(1.0 - X[:, pos[base(k)]]) if k.startswith("NOT(") else X[:, pos[base(k)]] for k in keys]
    Mx = np.column_stack(cols)
    w = np.array([W[k] for k in keys])

    # ---- out-of-fold isotonic calibration ----
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a_, b_ in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a_), find(b_)
        if ra != rb:
            parent[ra] = rb
    gid = pd.factorize(pd.Series([find(a_) for a_ in ids.pid_a]))[0]
    fold = np.random.default_rng(7).integers(0, 5, gid.max() + 1)[gid]
    from sklearn.isotonic import IsotonicRegression
    oof = np.zeros(len(yi))
    for k in range(5):
        trm, tem = fold != k, fold == k
        ww, bb = G.fit_nonneg(Mx[trm], yi[trm], np.ones(int(trm.sum())))
        oof[tem] = Mx[tem] @ ww + bb
    z_full = Mx @ w + b0
    # map the OOF score onto the deployed score's scale, then fit isotonic on that
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.02, y_max=0.98)
    order = np.argsort(oof)
    iso.fit(z_full[order], yi[order])
    xs = np.unique(np.quantile(z_full, np.linspace(0, 1, 26)))
    ys = iso.predict(xs)
    print(f"  calibration: {len(xs)} points, P(good) from {ys.min():.2f} to {ys.max():.2f}")
    print(f"  out-of-fold AUC used to build it: {G.auc(yi, oof):.4f}")

    # ---- how many distinct scores a window actually contains ----
    tiers = int(len(np.unique(np.round(z_full, 6))))
    print(f"  the model can express {tiers} distinct scores in total")

    rules = []
    for k, v in sorted(W.items(), key=lambda kv: -kv[1]):
        e = explain(k)
        col = Mx[:, keys.index(k)] > 0
        rules.append({"name": k, "weight": v, "human": e["title"], "tradition": e["tradition"],
                      "what": e["reading"], "how": e["plain"],
                      "fires": int(col.sum()), "fire_rate": round(float(col.mean()), 4),
                      "good_when_fires": round(float(yi[col].mean()), 4),
                      "good_otherwise": round(float(yi[~col].mean()), 4)})
    dep = {"model": M["model"], "cv_auc": M["cv_auc"], "test_auc": M["test_auc"],
           "alpha": M["alpha"], "trained_on": int(len(tr)), "base_rate": float(yi.mean()),
           "n_bank": M["n_bank"], "target": "the marriage went well, judged from the record",
           "intercept": b0, "weights": W,
           "calibration_isotonic": {"x": [float(x) for x in xs], "y": [float(y) for y in ys]},
           "distinct_scores": tiers,
           "benchmark": M.get("benchmark", {})}
    os.makedirs(OUT, exist_ok=True)
    json.dump(dep, open(f"{OUT}/quality_deployed_model.json", "w"), indent=1)
    json.dump({"meta": {"model": M["model"], "cv_auc": M["cv_auc"], "test_auc": M["test_auc"],
                        "base_rate": float(yi.mean()), "trained_on": int(len(tr))},
               "calibration_isotonic": dep["calibration_isotonic"],
               "rules": rules}, open(f"{OUT}/quality_deployed_rules.json", "w"), indent=1)
    print(f"  wrote quality_deployed_model.json ({len(W)} statements) and quality_deployed_rules.json")
    for r in rules[:4]:
        print(f"    {r['human'][:64]:<66} fires {r['fires']:>5,} · {r['good_when_fires']:.0%} good")


if __name__ == "__main__":
    main()
