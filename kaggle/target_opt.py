"""target_opt.py — the target search, with every shared quantity computed exactly once.

The first parallel attempt ran eight processes and was SLOWER than it needed to be, because seven of
them were recomputing work the eighth had already done. Ridge only meets lambda as a diagonal shift:

    beta = (XᵀX + lambda I)^-1 Xᵀ y

so XᵀX does not depend on lambda, on the kept fraction, or on the candidate target. Nor does Xᵀ P,
the design against the keyword-pattern indicators. Three configurations differing only in lambda
therefore share everything expensive and differ by one Cholesky each. The kept fraction and the
candidate weights cost nothing at all.

What is actually distinct, and so what is actually computed:

    design            once
    XᵀX, XᵀP, Xte     once per (fold seed, fold)          <- the expensive part, ~70 GFlop each
    Cholesky + solve  once per (fold seed, fold, lambda)  <- cheap, and shared by every candidate
    C = Xte Z         once per (fold seed, fold, lambda)  <- n_te x 333
    a candidate       one matvec against C, per fold

The search then runs over every (lambda, keep) pair in one process, reusing all of it, which is both
faster than eight processes and simpler to reason about. Threads are left to BLAS, which uses the
whole machine on one big matrix multiply far better than eight processes fighting over it.

STILL GUARDED. The confirm third that bio_pool.py split off is not read here.
"""
import json, os, sys, time, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from target_fast import GROUPS, NAMES, groups_of, groups_key, load

OUT = os.path.expanduser(os.environ.get("AQ_RESULT", "~/.artamatch-dev/target_opt.json"))
LAMS = tuple(float(x) for x in os.environ.get("AQ_LAMS", "100,300,1000,3000").split(","))
KEEPS = tuple(float(x) for x in os.environ.get("AQ_KEEPS", "0.40,0.60,0.80").split(","))
SEEDS = tuple(int(x) for x in os.environ.get("AQ_SEEDS", "7,23").split(","))
NFOLD = int(os.environ.get("AQ_NFOLD", "5"))
ITERS = int(os.environ.get("AQ_ITERS", "250"))
LEVELS = np.array([-3., -2, -1, 0, 1, 2, 3])


def fast_auc(y, s):
    """Mann-Whitney over one argsort. G.auc re-sorts and re-validates; this is the hot loop."""
    o = np.argsort(s, kind="stable")
    r = np.empty(len(s), float)
    r[o] = np.arange(1, len(s) + 1)
    # average ranks over ties, which matters because many couples share a keyword pattern
    ss = s[o]
    i = 0
    while i < len(ss):
        j = i + 1
        while j < len(ss) and ss[j] == ss[i]:
            j += 1
        if j > i + 1:
            r[o[i:j]] = (i + 1 + j) / 2.0
        i = j
    n1 = y.sum(); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return 0.5
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def build_blocks(X, gid, inv, K):
    """XᵀX, XᵀP and the held-out block, per (seed, fold). Computed once, reused by every lambda."""
    from scipy.linalg import cho_factor, cho_solve
    n, p = X.shape
    Xc = X - X.mean(0)
    P = np.zeros((n, K)); P[np.arange(n), inv] = 1.0
    blocks = []
    for s in SEEDS:
        fold = np.random.default_rng(s).integers(0, NFOLD, gid.max() + 1)[gid]
        for k in range(NFOLD):
            tr = fold != k
            A = Xc[tr]
            blocks.append({"te": np.where(~tr)[0], "G": A.T @ A, "B": A.T @ P[tr],
                           "Xte": Xc[~tr]})
    return blocks


def cs_for(blocks, lam):
    """C = Xte (XᵀX + lam I)^-1 XᵀP, one per fold. The only per-lambda work."""
    from scipy.linalg import cho_factor, cho_solve
    out = []
    for b in blocks:
        p = b["G"].shape[0]
        c = cho_factor(b["G"] + lam * np.eye(p), lower=True, check_finite=False)
        Zs = cho_solve(c, b["B"], check_finite=False)
        out.append((b["te"], b["Xte"] @ Zs))
    return out


def main():
    t0 = time.time()
    sp, H, gid, X, names = load()
    inv, table = groups_key(H)
    n = len(sp)
    print(f"  {n:,} search couples · {X.shape[1]:,} statements · {len(table)} keyword patterns")
    print(f"  design + load: {time.time()-t0:.0f}s", flush=True)

    t0 = time.time()
    blocks = build_blocks(X.astype(np.float64), gid, inv, len(table))
    print(f"  Gram blocks ({len(SEEDS)}x{NFOLD} folds): {time.time()-t0:.0f}s  "
          f"— shared by every lambda, keep fraction and candidate\n", flush=True)

    ref = np.zeros(len(NAMES))
    for k, v_ in {"divorce": -3, "separation": -2, "infidelity": -2, "conflict": -2, "abuse": -3,
                  "unhappy": -2, "affection": 2, "collab": 2, "children": 1,
                  "parted_by_death": 1}.items():
        ref[NAMES.index(k)] = v_

    results = []
    print(f"  {'lam':>6}{'keep':>6}{'today':>9}{'found':>9}{'gain':>8}{'defs':>9}{'sec':>7}")
    print("  " + "-" * 56)
    for lam in LAMS:
        t1 = time.time()
        CS = cs_for(blocks, lam)
        prep = time.time() - t1
        for keep in KEEPS:
            t2 = time.time()
            sp_cache = {}

            def ev(w):
                key = tuple(w)
                if key in sp_cache:
                    return sp_cache[key]
                s = (table @ np.asarray(w, float))
                row = s[inv]
                lo, hi = np.quantile(row, [keep / 2, 1 - keep / 2])
                if lo == hi:
                    sp_cache[key] = 0.5; return 0.5
                v = np.where(s >= hi, 1.0, np.where(s <= lo, -1.0, 0.0))
                y = (row >= hi).astype(int); m = (row <= lo) | (row >= hi)
                outs = []
                pred = np.empty(n)
                for te, C in CS:
                    pred[te] = C @ v
                for i in range(0, len(CS), NFOLD):        # one AUC per seed, over its 5 folds
                    idx = np.concatenate([CS[j][0] for j in range(i, i + NFOLD)])
                    mm = m[idx]
                    if mm.sum() < 200 or len(np.unique(y[idx][mm])) < 2:
                        outs.append(0.5); continue
                    outs.append(fast_auc(y[idx][mm], pred[idx][mm]))
                a = float(np.mean(outs))
                sp_cache[key] = a
                return a

            a_ref = ev(ref)
            rng = np.random.default_rng(5)
            best = (a_ref, ref.copy())
            for it in range(ITERS):
                w = ref.copy() if it == 0 else rng.choice(LEVELS, len(NAMES))
                moved = True
                while moved:
                    moved = False
                    for j in rng.permutation(len(NAMES)):
                        cur, cur_a = w[j], ev(w)
                        for lv in LEVELS:
                            if lv == cur:
                                continue
                            w[j] = lv
                            if ev(w) > cur_a + 1e-9:
                                cur, cur_a, moved = lv, ev(w), True
                        w[j] = cur
                if ev(w) > best[0]:
                    best = (ev(w), w.copy())
            results.append({"lam": lam, "keep": keep, "reference_auc": a_ref,
                            "best_auc": best[0], "weights": list(map(float, best[1])),
                            "n_definitions": len(sp_cache)})
            print(f"  {lam:>6.0f}{keep:>6.2f}{a_ref:>9.4f}{best[0]:>9.4f}"
                  f"{best[0]-a_ref:>+8.4f}{len(sp_cache):>9,}{time.time()-t2+prep/len(KEEPS):>7.0f}",
                  flush=True)

    W = np.array([r["weights"] for r in results])
    print(f"\n  CONSENSUS over {len(results)} configurations")
    print(f"  {'group':<20}{'today':>7}{'median':>8}{'sign agreement':>16}")
    for i, k in enumerate(NAMES):
        sg = np.sign(W[:, i])
        frac = max((sg > 0).mean(), (sg < 0).mean(), (sg == 0).mean())
        print(f"  {k:<20}{ref[i]:>7.0f}{np.median(W[:, i]):>8.1f}{frac:>15.0%}")
    med = np.median(W, 0)
    json.dump({"groups": NAMES, "reference": list(map(float, ref)), "results": results,
               "consensus_median": list(map(float, med)),
               "n_patterns": int(len(table)), "n_couples": int(n),
               "n_features": int(X.shape[1]), "patterns": dict(GROUPS)},
              open(OUT, "w"), indent=1)
    print(f"\n  saved {OUT}")
    print("  Nothing is claimed yet. target_confirm.py spends the held-back third, once.")


if __name__ == "__main__":
    main()
