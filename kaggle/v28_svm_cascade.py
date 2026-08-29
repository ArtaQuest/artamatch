"""v28_svm_cascade.py — three cascaded linear SVMs that FLIP what points the wrong way and DROP what says nothing.

The earlier cascade dropped every statement whose coefficient went negative. That throws information
away: a statement with a negative weight is not useless, it is the same doctrine pointing the other way,
and its complement carries exactly the signal the model wanted. So:

  stage 1   fit a linear SVM over every statement, then sort by |coefficient|:
            -> the bottom fraction q says nothing measurable            -> DROP
            -> of what remains, anything SIGNIFICANTLY negative is the same doctrine pointing the other
               way                                                      -> REFORMULATE as 1 - x, renamed
               NOT(...), and put straight back in for the next stage    -> KEEP, flipped
            -> anything significantly positive                          -> KEEP as it stands
            A statement is only ever dropped for saying nothing, never for saying the opposite.
  stage 2   refit over what remains, flip again, drop q again
  stage 3   refit, and that is the model

After stage 1 every surviving statement is formulated toward happy BY THE MODEL'S OWN RECKONING, which
is a stronger claim than a univariate direction: it accounts for what the other statements already
explain. Nothing is discarded for pointing the wrong way; only for pointing nowhere.

q — the near-zero drop fraction — is the parameter this file exists to tune, swept per stage against
cross-validation. C is swept alongside it.

DISCIPLINE. Flipping and dropping both read the label, so the whole cascade runs INSIDE every fold, from
that fold's training rows only, and the held-out rows are transformed by the flips learned there. The
test set is read ONCE, for the CV-declared (C, q).

Usage: v28_svm_cascade.py <corpus_dir> <out_model.json>
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v22_nnls import build
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev/quality_good")
OUT = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/.artamatch-dev/quality_v28.json")
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))
QS = tuple(float(x) for x in os.environ.get("AQ_Q", "0.2,0.3,0.4,0.5,0.6,0.7,0.8").split(","))
CS = tuple(float(x) for x in os.environ.get("AQ_C", "0.001,0.01,0.1").split(","))
STAGES = int(os.environ.get("AQ_STAGES", "3"))
SEEDS = tuple(int(x) for x in os.environ.get("AQ_SEEDS", "7,23").split(","))
MIN_KEEP = 8


def svm(X, y, C):
    from sklearn.svm import LinearSVC
    return LinearSVC(C=C, max_iter=4000, dual=True).fit(X, y)


def cascade(Xtr, ytr, C, q, stages=STAGES, first=None, trace=None):
    """returns (idx, flip, model) — idx into the original columns, flip in {+1,-1}, final SVM"""
    p = Xtr.shape[1]
    idx = np.arange(p)
    flip = np.ones(p, np.float32)
    Xc = Xtr
    m = None
    for st in range(stages):
        m = first if (st == 0 and first is not None) else svm(Xc, ytr, C)
        co = m.coef_[0]
        mag = np.abs(co)
        # what says nothing at all — the smallest magnitudes — is the only thing dropped
        k = int(np.floor(q * len(idx)))
        k = min(k, max(0, len(idx) - MIN_KEEP))
        keepmask = np.ones(len(idx), bool)
        if k > 0 and st < stages - 1:
            keepmask[np.argsort(mag)[:k]] = False
        # of what survives, the significantly negative are REFORMULATED, not discarded
        neg = (co < 0) & keepmask
        ncheck = 0
        if trace is not None:
            # check the reformulation before trusting it: does the statement's own univariate
            # direction on these rows agree that it points away from happy? A coefficient that is
            # negative while the raw rate is positive is a suppressor, not a reversed doctrine.
            for j in np.where(neg)[0]:
                col = Xc[:, j] > 0
                if col.any() and (~col).any() and ytr[col].mean() < ytr[~col].mean():
                    ncheck += 1
            trace.append((st + 1, int(len(idx)), int(keepmask.sum()), int(neg.sum()), int(ncheck)))
        if neg.any():
            Xc = Xc.copy()
            Xc[:, neg] = 1.0 - Xc[:, neg]
            flip[idx[neg]] *= -1.0
        if k > 0 and st < stages - 1:
            idx = idx[keepmask]
            Xc = Xc[:, keepmask]
        if st < stages - 1:
            m = svm(Xc, ytr, C)
    return idx, flip, m


def apply_cascade(X, idx, flip):
    out = X[:, idx].copy()
    neg = flip[idx] < 0
    out[:, neg] = 1.0 - out[:, neg]
    return out


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
    print(f"  bank {X.shape[1]:,} pair-only doctrine statements · {STAGES} cascaded linear SVMs\n",
          flush=True)

    folds = {s: np.random.default_rng(s).integers(0, 5, gid.max() + 1)[gid] for s in SEEDS}
    best = None
    print(f"  {'C':>7}{'q':>6}{'CV(mean)':>11}{'spread':>9}{'kept':>7}   what the cascade did")
    print("  " + "-" * 78)
    for C in CS:
        # stage 1 does not depend on q, so fit it once per (seed, fold, C) and reuse across the q sweep
        first = {(s, k): svm(X[folds[s] != k], yi[folds[s] != k], C) for s in SEEDS for k in range(5)}
        for q in QS:
            cvs, kept, shown = [], [], None
            for s in SEEDS:
                fold = folds[s]
                oof = np.zeros(len(yi))
                for k in range(5):
                    trm, tem = fold != k, fold == k
                    tr_trace = [] if (s == SEEDS[0] and k == 0) else None
                    idx, flip, m = cascade(X[trm], yi[trm], C, q, first=first[(s, k)], trace=tr_trace)
                    if tr_trace:
                        shown = tr_trace
                    oof[tem] = m.decision_function(apply_cascade(X[tem], idx, flip))
                    kept.append(len(idx))
                cvs.append(G.auc(yi, oof))
            sh = " ".join(f"{a}:{b}->{c} flip{d}" for a, b, c, d, _ in (shown or []))
            print(f"  {C:>7.3f}{q:>6.2f}{np.mean(cvs):>11.4f}{max(cvs)-min(cvs):>9.4f}"
                  f"{int(np.mean(kept)):>7}   {sh}", flush=True)
            if best is None or np.mean(cvs) > best[2]:
                best = (C, q, float(np.mean(cvs)))
    C, q, cv = best
    print(f"\n  CV winner: C={C}, q={q} (CV {cv:.4f})")

    trace = []
    idx, flip, m = cascade(X, yi, C, q, trace=trace)
    print("  cascade on the full training set:")
    for st, before, after, nneg, nchk in trace:
        agree = f"{nchk/max(nneg,1):.0%}" if nneg else "-"
        print(f"    stage {st}: {before:,} in · {nneg:,} reformulated as their negation "
              f"({agree} of those corroborated by the statement's own raw direction) · "
              f"{after:,} kept, {before - after:,} dropped for saying nothing")
    z = m.decision_function(apply_cascade(Xt, idx, flip))
    auc = G.auc(yte, z)
    bm = {}
    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    if os.path.exists(bp):
        bm = json.load(open(bp))
    se = bm.get("auc_se", float("nan")); base = bm.get("age_gap_auc", float("nan"))
    co = m.coef_[0]
    wt = {}
    for j, i in enumerate(idx):
        nm = names[i] if flip[i] > 0 else f"NOT({names[i]})"
        wt[nm] = float(co[j])
    nneg = sum(1 for k in wt if k.startswith("NOT("))
    print(f"\n  {len(wt):,} statements in the final model ({nneg:,} read as their negation)")
    print(f"  TEST AUC (read once): {auc:.4f}")
    print(f"    chance 0.5000 · age-gap baseline {base:.4f} · SE {se:.4f}")
    print(f"    above chance      {auc - 0.5:+.4f} = {(auc - 0.5) / se:+.2f} SE")
    print(f"    over the age gap  {auc - base:+.4f} = {(auc - base) / se:+.2f} SE")
    for k_, v in sorted(wt.items(), key=lambda kv: -kv[1])[:24]:
        print(f"    {k_[:76]:<78} {v:+.4f}")
    json.dump({"model": f"ArtaMatch quality — {STAGES} cascaded linear SVMs, flip-then-drop",
               "C": C, "q": q, "stages": STAGES, "cv_auc": round(cv, 4),
               "cascade": [{"stage": a, "in": b, "kept": c, "reformulated": d,
                            "reformulation_corroborated": e} for a, b, c, d, e in trace],
               "test_auc": round(float(auc), 4), "intercept": float(m.intercept_[0]),
               "n_bank": int(len(names)), "n_surviving": len(wt), "n_negated": nneg,
               "benchmark": bm, "weights": wt}, open(OUT, "w"), indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
