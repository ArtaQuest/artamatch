"""era_control.py — how much of any score here is just WHEN the two were born?

The corpus is Wikipedia marriages, and Wikipedia writes more about scandal than about a quiet forty
years, so record richness tracks fame, fame tracks era, and era is legible from a birth date through
any slow planet. This measures the confound directly instead of arguing about it:

  1. the birth decades alone, two numbers, under the same folds
  2. the astrology model alone
  3. both together — does astrology ADD anything to the decades?
  4. the astrology model measured WITHIN decade strata, where era cannot help it

Same group folds, same seeds, everything inside the fold.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v37_fit import groups, design

D = os.path.expanduser(os.environ.get("AQ_D", "~/.artamatch-dev/quality_good"))
SEEDS = (7, 23, 101)
C = float(os.environ.get("AQ_C", "3e-5"))


def oof_of(X, y, gid, C_, seeds=SEEDS):
    from sklearn.linear_model import LogisticRegression
    outs = []
    for seed in seeds:
        fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
        oof = np.zeros(len(y))
        for k in range(5):
            trm, tem = fold != k, fold == k
            mu = X[trm].mean(0); sd = X[trm].std(0) + 1e-9
            lo = LogisticRegression(C=C_, max_iter=3000).fit((X[trm] - mu) / sd, y[trm])
            oof[tem] = lo.predict_proba((X[tem] - mu) / sd)[:, 1]
        outs.append(oof)
    return np.mean(outs, 0)


def main():
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    y = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    gid = groups(ids)
    ya = pd.to_numeric(tr.dob_a.str[:4]).to_numpy(float)
    yb = pd.to_numeric(tr.dob_b.str[:4]).to_numpy(float)
    E = np.column_stack([ya / 100, yb / 100, (ya / 100) ** 2, (yb / 100) ** 2, (ya - yb) / 100])
    Xa, names = design(tr, Z, "train")
    print(f"  {len(tr):,} couples · astrology block {Xa.shape[1]:,} features\n")

    p_era = oof_of(E, y, gid, 1.0)
    p_ast = oof_of(Xa, y, gid, C)
    p_both = oof_of(np.column_stack([E, Xa]), y, gid, C)
    a_era, a_ast, a_both = (G.auc(y, p) for p in (p_era, p_ast, p_both))
    print(f"  1. birth years alone (5 terms)           CV AUC {a_era:.4f}")
    print(f"  2. the astrology block alone             CV AUC {a_ast:.4f}")
    print(f"  3. both together                         CV AUC {a_both:.4f}")
    print(f"     astrology adds over era               {a_both - a_era:+.4f}")
    print(f"  correlation of the two predictions       {np.corrcoef(p_era, p_ast)[0,1]:+.3f}")

    # 4. WITHIN decade strata: pool the astrology model's ranking inside blocks that share an era, so
    #    era cannot separate the couples. A concordance computed pair-by-pair inside each stratum.
    dec = ((ya // 10) * 10).astype(int)
    num = den = 0
    for d in np.unique(dec):
        m = dec == d
        if m.sum() < 30 or y[m].mean() in (0.0, 1.0):
            continue
        s, yy = p_ast[m], y[m]
        pos, neg = s[yy == 1], s[yy == 0]
        num += (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
        den += len(pos) * len(neg)
    print(f"\n  4. astrology WITHIN birth decades        AUC {num/max(den,1):.4f}"
          f"   ({den:,} comparable pairs)")
    json.dump({"era": a_era, "astro": a_ast, "both": a_both, "added": a_both - a_era,
               "within_decade": num / max(den, 1), "n_features": int(Xa.shape[1])},
              open(os.path.expanduser(os.environ.get("AQ_OUT_JSON",
                   "~/.artamatch-dev/era_control.json")), "w"), indent=1)


if __name__ == "__main__":
    main()
