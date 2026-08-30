"""target_confirm.py — spend the held-back third, once, on a frozen target definition.

Every number in target_opt.py and target_cca.py came from a search over tens of thousands of ways to
define "a marriage that went well". A search that large finds noise; the only question worth asking is
how much of what it found survives on couples the search never touched.

bio_pool.py split 5,191 couples off by connected component of the marriage graph before any of this
existed, so no person in the confirm third appears in the search half. This applies a frozen label
definition to both sides, fits the astrology model on SEARCH and scores it on CONFIRM, and prints the
three numbers that matter together:

    search AUC      what the search reported
    confirm AUC     what it is worth on untouched couples
    inflation       the difference, which is the price of having searched

It also prints the same three for the definition the project shipped BEFORE any search, so the search
is compared against something rather than against zero.

Nothing here chooses anything. It reports.
"""
import json, os, sys, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))

POOL = os.path.expanduser("~/.artamatch-dev/quality_pool")
LAM = float(os.environ.get("AQ_LAM", "1000"))
KEEP = float(os.environ.get("AQ_KEEP", "0.60"))


def fast_auc(y, s):
    o = np.argsort(s, kind="stable")
    r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1)
    ss = s[o]; i = 0
    while i < len(ss):
        j = i + 1
        while j < len(ss) and ss[j] == ss[i]:
            j += 1
        if j > i + 1:
            r[o[i:j]] = (i + 1 + j) / 2.0
        i = j
    n1 = y.sum(); n0 = len(y) - n1
    return 0.5 if n1 == 0 or n0 == 0 else (r[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def design_both():
    """the astrology bank on BOTH halves, built by one code path so the columns line up"""
    from v22_nnls import build as bb
    from v12_fit import side
    from denylist import clause_ok
    tr = pd.read_csv(f"{POOL}/train.csv", dtype=str)
    te = pd.read_csv(f"{POOL}/test.csv", dtype=str)
    Z = np.load(f"{POOL}/phases.npz", allow_pickle=True)
    Xs, ns = bb(tr, Z, "train")
    Xc, nc = bb(te, Z, "test")
    pos = {k: i for i, k in enumerate(nc)}
    Xc = np.column_stack([Xc[:, pos[k]] if k in pos else np.zeros(len(te), np.float32) for k in ns])
    keep = np.array([clause_ok(k) and side(k) == "AB" for k in ns]) & (Xs.sum(0) >= 0.02 * len(tr))
    return (Xs[:, keep].astype(np.float64), Xc[:, keep].astype(np.float64),
            [k for k, kk in zip(ns, keep) if kk])


def evaluate(Xs, Xc, ys, ms, yc, mc):
    """fit the sky on the SEARCH half, score the CONFIRM half. One direction, no peeking."""
    from scipy.linalg import cho_factor, cho_solve
    mu = Xs.mean(0)
    A = (Xs - mu)[ms]
    if ms.sum() < 200 or len(np.unique(ys[ms])) < 2:
        return 0.5
    t = ys[ms] - ys[ms].mean()
    c = cho_factor(A.T @ A + LAM * np.eye(A.shape[1]), lower=True, check_finite=False)
    beta = cho_solve(c, A.T @ t, check_finite=False)
    pred = (Xc - mu) @ beta
    return fast_auc(yc[mc].astype(int), pred[mc])


def main():
    from target_fast import groups_of, NAMES
    from bio_label_apply import present
    pool = pd.read_csv(f"{POOL}/pool.csv")
    S = pool[pool.side == "search"].sort_values("row").reset_index(drop=True)
    Cf = pool[pool.side == "confirm"].sort_values("row").reset_index(drop=True)
    Xs, Xc, names = design_both()
    print(f"  search {len(S):,} · confirm {len(Cf):,} · {Xs.shape[1]:,} statements\n")

    Hs, Hc = groups_of(S.desc), groups_of(Cf.desc)

    def lab(score, keep):
        lo, hi = np.quantile(score, [keep / 2, 1 - keep / 2])
        return (score >= hi).astype(int), (score <= lo) | (score >= hi)

    cands = []

    # 1. the reading the project used before any search
    ref = np.zeros(len(NAMES))
    for k, v in {"divorce": -3, "separation": -2, "infidelity": -2, "conflict": -2, "abuse": -3,
                 "unhappy": -2, "affection": 2, "collab": 2, "children": 1,
                 "parted_by_death": 1}.items():
        ref[NAMES.index(k)] = v
    cands.append(("the reading used before any search", Hs @ ref, Hc @ ref, None))

    # 2. the shipped keyword auto-labeller
    M = json.load(open(os.path.expanduser("~/.artamatch-dev/label_model.json")))
    wt, b = M["weights"], M["intercept"]
    sc = lambda df: np.array([b + sum(wt[k] for k in present(t) if k in wt)
                              for t in df.desc.fillna("").astype(str)])
    cands.append(("the shipped keyword auto-labeller", sc(S), sc(Cf), None))

    # 3. the winner of the twelve-group search
    p = os.path.expanduser("~/.artamatch-dev/target_opt.json")
    if os.path.exists(p):
        O = json.load(open(p))
        bestr = max(O["results"], key=lambda r: r["best_auc"])
        w = np.array(bestr["weights"])
        cands.append((f"group search winner (lam={bestr['lam']:.0f}, keep={bestr['keep']})",
                      Hs @ w, Hc @ w, bestr["best_auc"]))

    # 4. the canonical-correlation direction
    p = os.path.expanduser("~/.artamatch-dev/target_cca.json")
    if os.path.exists(p):
        Cj = json.load(open(p))
        cw = Cj["weights"]
        f = lambda df: np.array([sum(cw[k] for k in present(t) if k in cw)
                                 for t in df.desc.fillna("").astype(str)])
        cands.append(("canonical correlation direction", f(S), f(Cf), Cj["astro_auc"]))

    print(f"  {'target definition':<44}{'search':>9}{'CONFIRM':>10}{'inflation':>11}")
    print("  " + "-" * 76)
    out = []
    for nm, ss, scf, searched in cands:
        ys, ms = lab(ss, KEEP)
        yc, mc = lab(scf, KEEP)
        a_conf = evaluate(Xs, Xc, ys, ms, yc, mc)
        a_srch = evaluate(Xs, Xs, ys, ms, ys, ms)          # in-sample on search, for the gap
        shown = searched if searched is not None else a_srch
        print(f"  {nm:<44}{shown:>9.4f}{a_conf:>10.4f}{shown - a_conf:>+11.4f}")
        out.append({"name": nm, "search": float(shown), "confirm": float(a_conf),
                    "kept_confirm": int(mc.sum())})
    json.dump({"lam": LAM, "keep": KEEP, "n_search": len(S), "n_confirm": len(Cf),
               "results": out}, open(os.path.expanduser("~/.artamatch-dev/target_confirm.json"),
                                     "w"), indent=1)
    print(f"\n  confirm couples are {len(Cf):,}; a difference under about 0.02 is noise at that size")


if __name__ == "__main__":
    main()
