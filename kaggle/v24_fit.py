"""v24_fit.py — oriented toward happy AND regularised. The combination, not either alone.

Three fits, and the middle one is the point:

  Lasso, unoriented   CV 0.592   only the 51% of statements that happen to predict happy can be chosen;
                                 the other 2,819 are structurally unusable under positive=True
  NNLS, oriented      CV 0.547   every statement is now choosable, but nothing shrinks it — 5,771
                                 free non-negative weights on 7,909 rows fits noise, and orienting
                                 every column to correlate positively makes that EASIER, not harder
  Lasso, oriented     <- here    the whole bank is choosable and L1 still pays for each rule

Orientation is computed inside each fold on that fold's training rows only, because it reads the label.
The alpha is declared by cross-validation across three fold seeds, and the test set is read ONCE, for
the CV winner.

Usage: v24_fit.py <corpus_dir> <out_model.json>
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
OUT = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/.artamatch-dev/quality_v24.json")
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))
# A statement must be about TWO PEOPLE, not about when they were born. `side()` tests the NAME; this
# tests the behaviour: hold the midpoint date fixed, move the two births apart, and a real interaction
# changes while a midpoint quantity does not. Scores come from interaction_filter.py.
MIN_INTER = float(os.environ.get("AQ_MIN_INTERACTION", "0"))
ALPHAS = tuple(float(x) for x in os.environ.get(
    "AQ_ALPHAS", "0.0010,0.0020,0.0030,0.0040,0.0050,0.0070").split(","))
SEEDS = (7, 23, 101)
# The alternative to orienting: let the weights be SIGNED. Non-negativity was a deliberate choice
# ("no member can be used backwards"), but for a doctrine bank where a statement may legitimately
# point either way it costs half the bank, and a signed weight is just as explainable — a negative
# one reads as a caution rather than a support. Signed needs no orientation, so it cannot leak.
SIGNED = os.environ.get("AQ_SIGNED", "0") == "1"
# Restrict the bank to named systems. Selecting over twelve thousand columns dilutes: at any penalty
# loose enough to keep the statements that carry signal, the Lasso also keeps several hundred that do
# not, and the joint model scores WORSE in cross-validation than a single system fitted alone. The
# systems are chosen by system_ranking.py, which is cross-validated on the training couples only and
# never touches the test set, so narrowing the bank this way spends no test information.
ONLY = os.environ.get("AQ_ONLY", "")


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
    from sklearn.linear_model import Lasso, LogisticRegression
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
    if ONLY:
        import re as _re
        sel = np.array([bool(_re.search(ONLY, n)) for n in names])
        print(f"  restricted to the named systems that beat the age gap on their own: "
              f"{int((keep & sel).sum()):,} of {int(keep.sum()):,} statements")
        keep = keep & sel
    if MIN_INTER > 0:
        ip = os.path.expanduser("~/.artamatch-dev/interaction_scores.json")
        sc = json.load(open(ip)) if os.path.exists(ip) else {}
        inter = np.array([min((sc.get(p, 0.0) for p in n.split(" AND ")), default=0.0)
                          for n in names])
        dropped = int((keep & (inter < MIN_INTER)).sum())
        keep = keep & (inter >= MIN_INTER)
        print(f"  interaction filter at {MIN_INTER:.2f}: dropped {dropped:,} statements that do not "
              f"change when the two births move apart around a fixed midpoint")
    X, Xt = X[:, keep], Xt[:, keep]
    names = [n for n, k in zip(names, keep) if k]

    # Drop statements that are near-copies of one already in the bank. The composite chart (midpoint in
    # SPACE) and the Davison (midpoint in TIME) necessarily agree on the slow planets — Pluto moves four
    # thousandths of a degree a day — so comp_pluto_sign=Pis and dav_pluto_sign=Pis correlate at 0.997.
    # Keeping both doubles their multiple-comparison cost, splits their weight, and makes each look
    # worthless on a drop-one test because the other covers it. Worse, it shows a reader the same fact
    # twice under two names. Columns are bucketed by support so this stays cheap; the first name in the
    # bank wins, which keeps the composite (the exact construction) over the Davison (an approximation).
    sup = X.sum(0)
    order = np.argsort(-sup)
    seen, drop, dropped_pairs = {}, np.zeros(len(names), bool), []
    for i in order:
        b = int(sup[i])
        # a RELATIVE window: two columns correlated at 0.95+ can still differ in support by more than a
        # couple of rows. An absolute +/-2 window let comp_pluto_sign=Pis (609) and dav_pluto_sign=Pis
        # (606) past each other at r=0.997, because they differ by three.
        wnd = max(3, int(0.05 * b))
        cand = [j for k in range(b - wnd, b + wnd + 1) for j in seen.get(k, [])]
        xi = X[:, i]
        for j in cand:
            xj = X[:, j]
            # PHI, not Jaccard. Jaccard on two DENSE flags is high whatever they mean: a statement
            # true of 96% of couples overlaps any other 96% statement in ~96% of the union, so
            # "porutham_vedha_clear ~ maya_same_baktun" scored 0.961 and one of two unrelated
            # traditions was deleted. Phi is the correlation of two binaries and is near zero for
            # independent columns however dense; it still reads 0.997 for the comp/dav Pluto pair
            # this pruning exists to catch.
            n11 = float(np.minimum(xi, xj).sum())
            n1_ = float(xi.sum()); n_1 = float(xj.sum()); N = float(len(xi))
            den = n1_ * (N - n1_) * n_1 * (N - n_1)
            phi = (n11 * N - n1_ * n_1) / np.sqrt(den) if den > 0 else 0.0
            if phi > 0.95:
                drop[i] = True
                dropped_pairs.append((names[i], names[j], phi))
                break
        if not drop[i]:
            seen.setdefault(b, []).append(i)
    if drop.any():
        print(f"  dropped {int(drop.sum())} near-duplicate statements "
              f"(phi > 0.95 with one already kept)")
        for a_, b_, r_ in dropped_pairs[:4]:
            print(f"    {a_[:46]:<48} ~ {b_[:40]:<42} {r_:.3f}")
        X, Xt = X[:, ~drop], Xt[:, ~drop]
        names = [n for n, d in zip(names, drop) if not d]
    gid = groups(ids)
    print(f"  {os.path.basename(D)}: train {len(tr):,} ({yi.mean():.1%} good) · test {len(te):,}")
    print(f"  bank {X.shape[1]:,} pair-only doctrine statements, every one choosable once oriented\n",
          flush=True)

    best = None
    print(f"  {'alpha':>8}{'CV(mean3)':>11}{'spread':>9}{'rules':>7}{'flipped':>9}")
    print("  " + "-" * 46)
    for alpha in ALPHAS:
        cvs, nr = [], []
        for seed in SEEDS:
            fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
            oof = np.zeros(len(yi))
            for k in range(5):
                trm, tem = fold != k, fold == k
                if SIGNED:
                    m = Lasso(alpha=alpha, max_iter=8000).fit(X[trm], ytr[trm])
                    s = np.where(m.coef_ != 0)[0]; nr.append(len(s))
                    if len(s) >= 2:
                        oof[tem] = X[tem][:, s] @ m.coef_[s] + m.intercept_
                else:
                    fl, _ = orient(X[trm], yi[trm])
                    Xa, Xb = apply_flip(X[trm], fl), apply_flip(X[tem], fl)
                    m = Lasso(alpha=alpha, positive=True, max_iter=8000).fit(Xa, ytr[trm])
                    s = np.where(m.coef_ > 0)[0]; nr.append(len(s))
                    if len(s) >= 2:
                        w, b = G.fit_nonneg(Xa[:, s], yi[trm], np.ones(int(trm.sum())))
                        oof[tem] = Xb[:, s] @ w + b
            cvs.append(G.auc(yi, oof))
        if SIGNED:
            m = Lasso(alpha=alpha, max_iter=15000).fit(X, ytr)
            s = np.where(m.coef_ != 0)[0]
            nflip = int((m.coef_[s] < 0).sum())
        else:
            fl_full, _ = orient(X, yi)
            m = Lasso(alpha=alpha, positive=True, max_iter=15000).fit(apply_flip(X, fl_full), ytr)
            s = np.where(m.coef_ > 0)[0]
            nflip = int((fl_full[s] < 0).sum())
        print(f"  {alpha:>8.4f}{np.mean(cvs):>11.4f}{max(cvs)-min(cvs):>9.4f}{len(s):>7}{nflip:>9}",
              flush=True)
        if best is None or np.mean(cvs) > best[1]:
            best = (alpha, float(np.mean(cvs)))
    alpha, cv = best
    print(f"\n  CV winner: alpha={alpha} (CV {cv:.4f})")

    if SIGNED:
        m = Lasso(alpha=alpha, max_iter=20000).fit(X, ytr)
        surv = np.where(m.coef_ != 0)[0]
        w, b0 = m.coef_[surv], float(m.intercept_)
        fl = np.ones(len(names), np.float32)
        Xta = Xt
        auc = G.auc(yte, Xt[:, surv] @ w + b0)
    else:
        fl, _ = orient(X, yi)
        Xa, Xta = apply_flip(X, fl), apply_flip(Xt, fl)
        m = Lasso(alpha=alpha, positive=True, max_iter=20000).fit(Xa, ytr)
        surv = np.where(m.coef_ > 0)[0]
        w, b0 = G.fit_nonneg(Xa[:, surv], yi, np.ones(len(yi)))
        auc = G.auc(yte, Xta[:, surv] @ w + b0)
    bm = {}
    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    if os.path.exists(bp):
        bm = json.load(open(bp))
    se = bm.get("auc_se", float("nan"))
    wt = {}
    for i, v in zip(surv, w):
        if SIGNED:
            # a signed model says the same thing by sign: negative = a caution, not a support
            wt[names[i] if v > 0 else f"NOT({names[i]})"] = abs(float(v))
        elif v > 0:
            wt[names[i] if fl[i] > 0 else f"NOT({names[i]})"] = float(v)
    nflip = sum(1 for k in wt if k.startswith("NOT("))
    print(f"\n  {len(wt)} surviving statements ({nflip} of them read as their NEGATION)")
    print(f"  TEST AUC (read once): {auc:.4f}")
    base = bm.get('age_gap_auc', float('nan'))
    print(f"    chance 0.5000 · age-gap baseline {base:.4f} · SE {se:.4f}")
    print(f"    above chance        {auc - 0.5:+.4f} = {(auc - 0.5) / se:+.2f} SE")
    print(f"    over the age gap    {auc - base:+.4f} = {(auc - base) / se:+.2f} SE")
    for k_, v in sorted(wt.items(), key=lambda kv: -kv[1])[:26]:
        print(f"    {k_[:76]:<78} +{v:.4f}")
    json.dump({"model": ("ArtaMatch quality — signed Lasso over every statement" if SIGNED else
                         "ArtaMatch quality — oriented toward happy, Lasso-selected, non-negative"),
               "signed": SIGNED,
               "alpha": alpha, "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4),
               "intercept": float(b0),
               "n_bank": int(len(names)), "n_surviving": len(wt), "n_negated": nflip,
               "benchmark": bm, "weights": wt}, open(OUT, "w"), indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
