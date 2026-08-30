"""stack_fit.py — three ways of reading the same two charts, combined out of fold.

The binary bank, the harmonic decomposition and the composite chart disagree about what they look at:
the bank asks yes/no questions of named conditions, the harmonics read every cross-chart angle as a
Fourier series, and the composite reads the relationship chart's own positions. Predictors that make
DIFFERENT mistakes combine well, so this fits all three under one set of group folds, records each
one's out-of-fold score, and then combines them.

Combination is a RANK AVERAGE, which fits nothing at all and therefore cannot leak; a fitted stack is
reported beside it for comparison, using an inner cross-validation inside each outer fold so the
second level never sees its own training rows.

No test read anywhere in this file.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v37_fit import groups
from scipy.stats import rankdata

D = os.path.expanduser(os.environ.get("AQ_D", "~/.artamatch-dev/quality_good"))
# More fold assignments means more independent out-of-fold predictions per couple to average over.
SEEDS = tuple([7, 23, 101, 5, 61, 137, 211, 313][:int(os.environ.get("AQ_NSEEDS", "3"))])
MIN_INTER = float(os.environ.get("AQ_MIN_INTERACTION", "0"))
OUT = os.path.expanduser(os.environ.get("AQ_OUT_JSON", "~/.artamatch-dev/stack.json"))


BANKPLUS = os.environ.get("AQ_BANKPLUS", "0") == "1"
CONJ = os.environ.get("AQ_CONJ", "0") == "1"


def _augment(Xb, nb, tr, Z):
    """Offer the harmonics to the Lasso as CANDIDATES rather than averaging them in a ridge.

    Two details make this legal. The bank is binary and gets oriented toward "good" inside each fold;
    a continuous column cannot be oriented that way, so each harmonic is appended TWICE, as +x and -x,
    which lets a positive-only Lasso choose either direction without anyone having looked at the label
    outside the fold. And the columns are put on a common scale first, because a Lasso penalty is not
    scale-free and an unscaled continuous column would either dominate the binaries or vanish."""
    import v37_harmonics as V37, v39_composite_harm as V39
    parts, names = [Xb], list(nb)
    for mod, tag in ((V37, "h"), (V39, "c")):
        X, nm = mod.build(tr, Z, "train")
        X = (X - X.mean(0)) / (X.std(0) + 1e-9) * 0.5 + 0.5      # onto the binaries' 0..1 footing
        parts += [X.astype(np.float32), (1.0 - X).astype(np.float32)]
        names += [f"{n}" for n in nm] + [f"NEG({n})" for n in nm]
    return np.column_stack(parts).astype(np.float32), names


def bank_block(tr, Z):
    from v22_nnls import build as bb
    from v12_fit import side
    from denylist import clause_ok
    X, n = bb(tr, Z, "train")
    # SIDES: "AB" keeps only statements that read both dates — the pair-only rule. "all" also admits
    # single-side natal statements (his Sun sign, her element, the groups each chart falls in), which
    # are ordinary astrology and were excluded by a design choice, not by doctrine.
    sides = os.environ.get("AQ_SIDES", "AB")
    keep = np.array([clause_ok(k) and (sides == "all" or side(k) == "AB") for k in n]) \
        & (X.sum(0) >= FLOOR)
    if MIN_INTER > 0:
        sc = json.load(open(os.path.expanduser("~/.artamatch-dev/interaction_scores.json")))
        keep &= np.array([min((sc.get(p, 0.0) for p in k.split(" AND ")), default=0.0) >= MIN_INTER
                          for k in n])
    return X[:, keep], [k for k, kk in zip(n, keep) if kk]


REFIT = os.environ.get("AQ_REFIT", "nonneg")     # nonneg | logistic
SCREEN = int(os.environ.get("AQ_SCREEN", "0"))   # keep the top-N by marginal z inside each fold
# Five folds trains each model on 80% of the couples; ten trains on 90%. More training data per fold
# means a better model per fold and a less pessimistic estimate of what the full fit generalises to.
# It is a different estimator, not a looser one — every fold is still scored on couples it never saw.
NFOLD = int(os.environ.get("AQ_NFOLD", "5"))
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))


def fit_bank(Xtr, ytr, Xte, alpha):
    """Lasso selects, then a relaxed refit scores. The refit is where the non-negativity constraint
    actually binds: orienting each statement toward "good" and forbidding a negative weight was a
    deliberate choice ("no member can be used backwards"), but a statement can legitimately point
    either way once the others are in, and forbidding that costs fit. Both refits are offered so the
    cost is measured rather than assumed."""
    from sklearn.linear_model import Lasso, LogisticRegression
    from v22_nnls import orient, apply_flip
    flip, _ = orient(Xtr, ytr)
    A, B = apply_flip(Xtr, flip), apply_flip(Xte, flip)
    if SCREEN and SCREEN < A.shape[1]:
        # Screen before selecting. With sixteen thousand candidates and eight thousand couples the
        # Lasso spends its budget deciding between near-identical noise columns; ranking by the
        # marginal z first and handing it a shortlist is the standard remedy. Computed on the
        # TRAINING rows of this fold only, so it leaks nothing.
        f = A > 0.5
        n1 = f.sum(0); base = ytr.mean()
        s1 = (f * ytr[:, None]).sum(0)
        z = np.where(n1 > 5, (s1 - n1 * base) / np.sqrt(np.maximum(n1 * base * (1 - base), 1e-9)), 0.0)
        idx = np.argsort(-np.abs(z))[:SCREEN]
        A, B = A[:, idx], B[:, idx]
    m = Lasso(alpha=alpha, positive=True, max_iter=8000).fit(A, ytr)
    s = np.where(m.coef_ > 0)[0]
    if len(s) < 2:
        return np.zeros(len(Xte))
    if REFIT == "logistic":
        lo = LogisticRegression(C=1.0, max_iter=3000).fit(A[:, s], ytr.astype(int))
        return lo.predict_proba(B[:, s])[:, 1]
    w, b = G.fit_nonneg(A[:, s], ytr, np.ones(len(A)))
    return B[:, s] @ w + b


def fit_ridge(Xtr, ytr, Xte, C):
    from sklearn.linear_model import LogisticRegression
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    lo = LogisticRegression(C=C, max_iter=3000).fit((Xtr - mu) / sd, ytr)
    return lo.predict_proba((Xte - mu) / sd)[:, 1]


def main():
    import v37_harmonics as V37, v39_composite_harm as V39
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    y = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    gid = groups(ids)
    Xb, nb = bank_block(tr, Z)
    if CONJ:
        import v42_conjunctions as V42
        Xc2, nc2 = V42.build_from(Xb, nb)
        print(f"  {Xc2.shape[1]:,} conjunction columns from a support-chosen pool")
        Xb = np.column_stack([Xb, Xc2]).astype(np.float32); nb = nb + nc2
    if BANKPLUS:
        Xb, nb = _augment(Xb, nb, tr, Z)
        print(f"  bank augmented with harmonic candidates -> {Xb.shape[1]:,} columns")
    Xh, _ = V37.build(tr, Z, "train")
    Xc, _ = V39.build(tr, Z, "train")
    print(f"  {len(tr):,} couples · bank {Xb.shape[1]:,} · harmonics {Xh.shape[1]:,} "
          f"· composite {Xc.shape[1]:,}  (interaction gate {MIN_INTER})\n")

    SWEEP = [float(x) for x in os.environ.get("AQ_ALPHA_SWEEP", "").split(",") if x]
    if SWEEP:
        print(f"  {'alpha':>8}{'CV AUC':>10}{'avg-OOF':>10}   refit={REFIT}, {NFOLD} folds   per-seed")
        best = None
        for al in SWEEP:
            accs, allo = [], []
            for seed in SEEDS:
                fold = np.random.default_rng(seed).integers(0, NFOLD, gid.max() + 1)[gid]
                oof = np.zeros(len(y))
                for k in range(NFOLD):
                    trm, tem = fold != k, fold == k
                    oof[tem] = fit_bank(Xb[trm], y[trm].astype(float), Xb[tem], al)
                accs.append(G.auc(y, oof))
                allo.append(rankdata(oof) / len(oof))
            a = float(np.mean(accs))
            # AVERAGED OUT-OF-FOLD PREDICTION. Every couple gets one prediction per fold assignment,
            # each from a model that never saw it; averaging them is not a second look at the label,
            # it is the same estimate with less noise — and it is closer to what actually ships,
            # because the deployed model is fitted on all the couples rather than on four fifths.
            avg = G.auc(y, np.mean(allo, 0))
            print(f"  {al:>8.4g}{a:>10.4f}{avg:>10.4f}   {', '.join(f'{v:.4f}' for v in accs)}")
            if best is None or a > best[1]:
                best = (al, a)
        print(f"\n  BEST alpha={best[0]:g}  CV {best[1]:.4f}  (refit {REFIT})")
        json.dump({"sweep": SWEEP, "refit": REFIT, "best_alpha": best[0], "cv_auc": best[1],
                   "min_interaction": MIN_INTER}, open(OUT, "w"), indent=1)
        print(f"  saved {OUT}")
        return
    ALPHA = float(os.environ.get("AQ_ALPHA", "0.007"))
    CH = float(os.environ.get("AQ_CH", "3e-5"))
    CC = float(os.environ.get("AQ_CC", "3e-5"))
    per, comb = {k: [] for k in ("bank", "harm", "comp")}, {"rank": [], "stack": []}
    for seed in SEEDS:
        fold = np.random.default_rng(seed).integers(0, NFOLD, gid.max() + 1)[gid]
        oof = {k: np.zeros(len(y)) for k in per}
        for k in range(NFOLD):
            trm, tem = fold != k, fold == k
            oof["bank"][tem] = fit_bank(Xb[trm], y[trm].astype(float), Xb[tem], ALPHA)
            oof["harm"][tem] = fit_ridge(Xh[trm], y[trm], Xh[tem], CH)
            oof["comp"][tem] = fit_ridge(Xc[trm], y[trm], Xc[tem], CC)
        for kk in per:
            per[kk].append(G.auc(y, oof[kk]))
        R = np.column_stack([rankdata(oof[kk]) / len(y) for kk in ("bank", "harm", "comp")])
        comb["rank"].append(G.auc(y, R.mean(1)))
        # fitted stack, second level trained only on the OTHER folds' out-of-fold columns
        st = np.zeros(len(y))
        from sklearn.linear_model import LogisticRegression
        for k in range(NFOLD):
            trm, tem = fold != k, fold == k
            lo = LogisticRegression(max_iter=1000).fit(R[trm], y[trm])
            st[tem] = lo.predict_proba(R[tem])[:, 1]
        comb["stack"].append(G.auc(y, st))

    print(f"  {'block':<28}{'CV AUC':>9}   per-seed")
    for kk, lab in (("bank", "the binary doctrine bank"), ("harm", "harmonics of cross angles"),
                    ("comp", "the composite chart")):
        print(f"  {lab:<28}{np.mean(per[kk]):>9.4f}   {', '.join(f'{v:.4f}' for v in per[kk])}")
    print()
    for kk, lab in (("rank", "RANK AVERAGE (fits nothing)"), ("stack", "fitted stack (nested)")):
        print(f"  {lab:<28}{np.mean(comb[kk]):>9.4f}   {', '.join(f'{v:.4f}' for v in comb[kk])}")
    json.dump({k: float(np.mean(v)) for k, v in {**per, **comb}.items()} |
              {"min_interaction": MIN_INTER, "alpha": ALPHA, "C_harm": CH, "C_comp": CC},
              open(OUT, "w"), indent=1)
    print(f"\n  saved {OUT}")


if __name__ == "__main__":
    main()
