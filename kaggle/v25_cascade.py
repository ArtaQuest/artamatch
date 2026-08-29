"""v25_cascade.py — three cascaded fits, each dropping the statements the previous one turned against.

WHY. Orienting every statement toward happy makes the whole bank choosable, but it also makes every
column marginally positive, so an unregularised fit over 7,884 of them cheerfully fits noise — measured:
NNLS scored CV 0.547 against the Lasso's 0.592, and its top weights were single cells of 12x12 tables.

THE CASCADE. A statement that is positive on its own but goes NEGATIVE once its competitors are in the
model is not carrying its own weight; it is being used to cancel something. Those are exactly the
unstable ones. So:

  stage 1   fit signed over every oriented statement  ->  keep only those with a positive coefficient
  stage 2   refit over the survivors                  ->  keep only those still positive
  stage 3   refit over those survivors                ->  the model

Each round can only shrink the set, and a statement has to stay positive against three different
competitor sets to reach the end. That is a backward elimination with a sign test as its criterion,
which is stricter than L1 alone and cheaper than a stability sweep.

DISCIPLINE. The cascade is part of the FIT, so it runs inside every cross-validation fold — orientation,
all three stages, and the final weights, from that fold's training rows only. A cascade run once on the
whole training set and then cross-validated would be reporting its own selection back to itself. The
test set is read once, for the CV-declared alpha.

Usage: v25_cascade.py <corpus_dir> <out_model.json>
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v22_nnls import build, orient, apply_flip
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser(sys.argv[1])
OUT = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/.artamatch-dev/quality_v25.json")
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))
ALPHAS = tuple(float(x) for x in os.environ.get("AQ_ALPHAS", "0.0005,0.0010,0.0020,0.0035").split(","))
STAGES = int(os.environ.get("AQ_STAGES", "3"))
SEEDS = tuple(int(x) for x in os.environ.get("AQ_SEEDS", "7,23").split(","))


def cascade(Xa, y, alpha, stages=STAGES, trace=None):
    """signed fit; drop every statement whose coefficient is not positive; repeat"""
    from sklearn.linear_model import Lasso
    idx = np.arange(Xa.shape[1])
    coef = None
    for st in range(stages):
        if len(idx) < 2:
            break
        m = Lasso(alpha=alpha, max_iter=9000).fit(Xa[:, idx], y)
        pos = m.coef_ > 0
        if trace is not None:
            trace.append((st + 1, int(len(idx)), int(pos.sum())))
        if pos.sum() < 2:
            break
        idx, coef = idx[pos], m.coef_[pos]
    return idx, coef


def groups(ids):
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]


def main():
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    ytr = yi.astype(float)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)

    X, names = build(tr, Z, "train")
    Xt, nt = build(te, Z, "test")
    pos = {k: i for i, k in enumerate(nt)}
    Xt = np.column_stack([Xt[:, pos[k]] if k in pos else np.zeros(len(te), np.float32) for k in names])
    keep = np.array([clause_ok(n) for n in names]) & (X.sum(0) >= FLOOR) \
        & np.array([side(n) == "AB" for n in names])
    X, Xt = X[:, keep], Xt[:, keep]
    names = [n for n, k in zip(names, keep) if k]
    gid = groups(ids)
    print(f"  {os.path.basename(D)}: train {len(tr):,} ({yi.mean():.1%} good) · test {len(te):,}")
    print(f"  bank {X.shape[1]:,} pair-only doctrine statements · {STAGES} cascaded stages\n", flush=True)

    best = None
    print(f"  {'alpha':>8}{'CV(mean)':>10}{'spread':>9}   stages (kept -> survived)")
    print("  " + "-" * 62)
    for alpha in ALPHAS:
        cvs, shapes = [], None
        for seed in SEEDS:
            fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
            oof = np.zeros(len(yi))
            for k in range(5):
                trm, tem = fold != k, fold == k
                fl, _ = orient(X[trm], yi[trm])         # orientation from THIS fold's train rows
                Xa, Xb = apply_flip(X[trm], fl), apply_flip(X[tem], fl)
                tr_trace = [] if (seed == SEEDS[0] and k == 0) else None
                idx, coef = cascade(Xa, ytr[trm], alpha, trace=tr_trace)
                if tr_trace:
                    shapes = tr_trace
                if coef is None or len(idx) < 2:
                    oof[tem] = 0.0
                    continue
                w, b = G.fit_nonneg(Xa[:, idx], yi[trm], np.ones(int(trm.sum())))
                oof[tem] = Xb[:, idx] @ w + b
            cvs.append(G.auc(yi, oof))
        sh = " ".join(f"{a}:{b}->{c}" for a, b, c in (shapes or []))
        print(f"  {alpha:>8.4f}{np.mean(cvs):>10.4f}{max(cvs)-min(cvs):>9.4f}   {sh}", flush=True)
        if best is None or np.mean(cvs) > best[1]:
            best = (alpha, float(np.mean(cvs)))
    alpha, cv = best
    print(f"\n  CV winner: alpha={alpha} (CV {cv:.4f})")

    fl, _ = orient(X, yi)
    Xa, Xta = apply_flip(X, fl), apply_flip(Xt, fl)
    trace = []
    idx, coef = cascade(Xa, ytr, alpha, trace=trace)
    print("  cascade on the full training set:")
    for st, before, after in trace:
        print(f"    stage {st}: {before:,} statements in -> {after:,} kept "
              f"({before - after:,} dropped for turning negative)")
    w, b0 = G.fit_nonneg(Xa[:, idx], yi, np.ones(len(yi)))
    auc = G.auc(yte, Xta[:, idx] @ w + b0)
    bm = {}
    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    if os.path.exists(bp):
        bm = json.load(open(bp))
    se = bm.get("auc_se", float("nan")); base = bm.get("age_gap_auc", float("nan"))
    wt = {}
    for i, v in zip(idx, w):
        if v > 0:
            wt[names[i] if fl[i] > 0 else f"NOT({names[i]})"] = float(v)
    nneg = sum(1 for k in wt if k.startswith("NOT("))
    print(f"\n  {len(wt)} surviving statements ({nneg} read as their negation)")
    print(f"  TEST AUC (read once): {auc:.4f}")
    print(f"    chance 0.5000 · age-gap baseline {base:.4f} · SE {se:.4f}")
    print(f"    above chance      {auc - 0.5:+.4f} = {(auc - 0.5) / se:+.2f} SE")
    print(f"    over the age gap  {auc - base:+.4f} = {(auc - base) / se:+.2f} SE")
    for k_, v in sorted(wt.items(), key=lambda kv: -kv[1])[:26]:
        print(f"    {k_[:76]:<78} +{v:.4f}")
    json.dump({"model": f"ArtaMatch quality — {STAGES}-stage cascade, negatives dropped each round",
               "alpha": alpha, "stages": STAGES, "cv_auc": round(cv, 4),
               "cascade": [{"stage": a, "in": b, "kept": c} for a, b, c in trace],
               "test_auc": round(float(auc), 4), "intercept": float(b0),
               "n_bank": int(len(names)), "n_surviving": len(wt), "n_negated": nneg,
               "benchmark": bm, "weights": wt}, open(OUT, "w"), indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
