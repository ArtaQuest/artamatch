"""target_fast.py — the target search, with the arithmetic done once instead of once per candidate.

THE OBSERVATION THAT MAKES THIS CHEAP. A candidate target is a weighting of twelve BINARY keyword
groups, thresholded. Two couples whose twelve indicators agree therefore get the same label under
EVERY candidate, forever. There are at most 2^12 = 4096 such patterns and in practice a few hundred,
so the label is not an n-vector that changes — it is a K-vector over patterns, and n is irrelevant.

Ridge prediction on a held-out fold is

    pred = Xte @ V diag(d) Uᵀ y        with  d = s / (s² + λ)

and y = P v for the pattern indicator matrix P and the pattern-level label v. So

    pred = [ (Xte V diag(d)) (Uᵀ P) ] v = C v

and C is n_te x K, computed ONCE per fold. Evaluating a candidate is then one small matrix-vector
product — microseconds — against a 3,000-column matvec per fold before. The search stops being the
bottleneck, which is what makes a real search of the space possible rather than a token one.

WHAT THE SURROGATE IS. The ridge target is +1 on the happy tail, -1 on the unhappy tail and 0 in the
middle, so the design stays fixed while the label moves; AUC is then measured only on the labelled
held-out rows. Fitting on the labelled rows alone would change the design per candidate and destroy
the precompute. This is a search surrogate and nothing else — the winner is refitted with the real
Lasso pipeline, on labelled rows only, in target_confirm.py.

`--verify` checks the fast path against the literal one on random candidates and prints the largest
disagreement in AUC. It should be zero to several decimal places.
"""
import json, os, sys, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G

POOL = os.path.expanduser("~/.artamatch-dev/quality_pool")
CACHE = os.path.expanduser("~/.artamatch-dev/target_cache.npz")
LAM = float(os.environ.get("AQ_LAM", "300"))
NFEAT = int(os.environ.get("AQ_NFEAT", "3000"))
KEEP = float(os.environ.get("AQ_KEEP", "0.60"))
NFOLD = int(os.environ.get("AQ_NFOLD", "5"))
SEEDS = tuple(int(x) for x in os.environ.get("AQ_SEEDS", "7,23").split(","))
ITERS = int(os.environ.get("AQ_ITERS", "300"))

GROUPS = {
 "divorce":   r"divorc|dissolv|annul|ex-husband|ex-wife|former husband|former wife|scheidung|"
              r"развод|離婚|طلاق",
 "separation":r"separat|estrang|split up|parted|left him|left her|getrennt|расстал",
 "infidelity":r"affair|mistress|lover|adulter|illegitimate|unfaithful|liaison|liebschaft|любовниц",
 "conflict":  r"quarrel|dispute|litigat|sued|feud|acrimon|bitter|court battle|streit|ссор",
 "abuse":     r"violen|abus|beat her|beat him|cruel|assault|drunken|gewalt",
 "unhappy":   r"unhapp|miserabl|lovel|of convenience|arranged marriage|unglücklich|несчаст",
 "affection": r"\blove\b|loved|devot|adored|beloved|happ|inseparable|cherish|liebe|amour|amore|"
              r"любов|愛",
 "collab":    r"collaborat|co-wrote|co-author|co-found|partnership|together they|jointly|"
              r"worked together|zusammen",
 "children":  r"\bchildren\b|\bsons\b|\bdaughters\b|\bson\b|\bdaughter\b|bore him|gave birth|"
              r"kinder|enfants|дет",
 "parted_by_death": r"his widow|her widower|was widowed|until her death|until his death|"
              r"\bshe died\b|\bhe died\b|survived by|witwe|вдов",
 "long":      r"years of marriage|long marriage|golden wedding|fifty years|forty years|"
              r"decades of marriage",
 "remarried": r"remarri|second marriage|third marriage|first husband|first wife|wieder",
}
NAMES = list(GROUPS)


def groups_of(texts):
    t = pd.Series(texts).fillna("").astype(str).str.lower()
    return np.column_stack([t.str.contains(p, regex=True).to_numpy(float) for p in GROUPS.values()])


def design(df, Z, split):
    from v22_nnls import build as bb
    from v12_fit import side
    from denylist import clause_ok
    X, n = bb(df, Z, split)
    keep = np.array([clause_ok(k) and side(k) == "AB" for k in n]) & (X.sum(0) >= 0.02 * len(df))
    X, n = X[:, keep], [k for k, kk in zip(n, keep) if kk]
    if X.shape[1] > NFEAT:
        idx = np.argsort(-X.sum(0))[:NFEAT]      # by SUPPORT — never consults a label
        X, n = X[:, idx], [n[i] for i in idx]
    return X.astype(np.float64), n


def groups_key(H):
    """collapse rows to their 12-bit pattern; returns (code per row, K x 12 pattern table)"""
    bits = (H > 0).astype(np.int64)
    code = np.zeros(len(H), np.int64)
    for j in range(bits.shape[1]):
        code |= bits[:, j] << j
    uniq, inv = np.unique(code, return_inverse=True)
    table = np.column_stack([(uniq >> j) & 1 for j in range(bits.shape[1])]).astype(float)
    return inv, table


class Fast:
    """C[fold] : n_te x K. A candidate is one matvec per fold."""

    def __init__(self, X, gid, inv, K):
        n = len(X)
        self.Xc = X - X.mean(0)
        self.inv = inv; self.K = K
        P = np.zeros((n, K))
        P[np.arange(n), inv] = 1.0
        self.folds = []
        for s in SEEDS:
            fold = np.random.default_rng(s).integers(0, NFOLD, gid.max() + 1)[gid]
            fl = []
            for k in range(NFOLD):
                tr = fold != k
                U, S, Vt = np.linalg.svd(self.Xc[tr], full_matrices=False)
                d = S / (S ** 2 + LAM)
                C = (self.Xc[~tr] @ Vt.T * d) @ (U.T @ P[tr])
                fl.append((np.where(~tr)[0], C))
            self.folds.append(fl)

    def auc(self, v, ylab, mask):
        """v: K-vector of signed ridge targets. ylab/mask: per-ROW label and mask."""
        outs = []
        for fl in self.folds:
            pred = np.full(len(self.inv), np.nan)
            for idx, C in fl:
                pred[idx] = C @ v
            m = mask & np.isfinite(pred)
            if m.sum() < 200 or len(np.unique(ylab[m])) < 2:
                return 0.5
            outs.append(G.auc(ylab[m].astype(int), pred[m]))
        return float(np.mean(outs))


def label_from(table, inv, w, keep):
    """returns (pattern signed target v, row label, row mask) with a FIXED kept share"""
    sp = table @ w                       # score per pattern
    s = sp[inv]                          # score per row
    lo, hi = np.quantile(s, [keep / 2, 1 - keep / 2])
    if lo == hi:
        return None
    v = np.where(sp >= hi, 1.0, np.where(sp <= lo, -1.0, 0.0))
    ylab = (s >= hi).astype(int)
    mask = (s <= lo) | (s >= hi)
    return v, ylab, mask


def slow_auc(Xc, gid, ylab, mask, v_rows):
    """the literal computation, for --verify only"""
    outs = []
    for s in SEEDS:
        fold = np.random.default_rng(s).integers(0, NFOLD, gid.max() + 1)[gid]
        pred = np.full(len(Xc), np.nan)
        for k in range(NFOLD):
            tr = fold != k
            U, S, Vt = np.linalg.svd(Xc[tr], full_matrices=False)
            d = S / (S ** 2 + LAM)
            beta = Vt.T @ (d * (U.T @ v_rows[tr]))
            pred[~tr] = Xc[~tr] @ beta
        m = mask & np.isfinite(pred)
        outs.append(G.auc(ylab[m].astype(int), pred[m]))
    return float(np.mean(outs))


def load():
    pool = pd.read_csv(f"{POOL}/pool.csv")
    tr = pd.read_csv(f"{POOL}/train.csv", dtype=str)
    ids = pd.read_csv(f"{POOL}/_train_ids.csv", dtype=str)
    Z = np.load(f"{POOL}/phases.npz", allow_pickle=True)
    sp = pool[pool.side == "search"].sort_values("row").reset_index(drop=True)
    assert len(sp) == len(tr), "pool.csv and train.csv disagree"
    H = groups_of(sp.desc)
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    gid = pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]
    X, names = design(tr, Z, "train")
    return sp, H, gid, X, names


def main():
    sp, H, gid, X, names = load()
    inv, table = groups_key(H)
    print(f"  {len(sp):,} search couples · {X.shape[1]:,} statements · "
          f"{len(table):,} distinct keyword patterns (of 4,096 possible)")
    for i, k in enumerate(NAMES):
        print(f"    {k:<18}{H[:, i].mean():>6.1%}")
    import time
    t0 = time.time()
    F = Fast(X, gid, inv, len(table))
    print(f"\n  precompute: {time.time()-t0:.0f}s for {len(SEEDS)}x{NFOLD} folds")

    rng = np.random.default_rng(3)
    if "--verify" in sys.argv:
        print("\n  VERIFY — fast path against the literal one")
        worst = 0.0
        for _ in range(6):
            w = rng.choice([-3., -2, -1, 0, 1, 2, 3], len(NAMES))
            got = label_from(table, inv, w, KEEP)
            if got is None:
                continue
            v, ylab, mask = got
            a_fast = F.auc(v, ylab, mask)
            a_slow = slow_auc(F.Xc, gid, ylab, mask, v[inv])
            worst = max(worst, abs(a_fast - a_slow))
            print(f"    fast {a_fast:.6f}   literal {a_slow:.6f}   diff {abs(a_fast-a_slow):.2e}")
        print(f"  largest disagreement: {worst:.2e}")
        return

    t0 = time.time()
    for _ in range(200):
        w = rng.choice([-3., -2, -1, 0, 1, 2, 3], len(NAMES))
        got = label_from(table, inv, w, KEEP)
        if got:
            F.auc(*got)
    rate = 200 / (time.time() - t0)
    print(f"  throughput: {rate:,.0f} candidate targets per second")
    if "--search" not in sys.argv:
        return

    # ---- coordinate ascent from many restarts -------------------------------------------------
    LEVELS = np.array([-3., -2, -1, 0, 1, 2, 3])
    cache = {}

    def ev(w):
        key = tuple(w)
        if key not in cache:
            got = label_from(table, inv, w, KEEP)
            cache[key] = 0.5 if got is None else F.auc(*got)
        return cache[key]

    # the reading the project has used until now, as the reference point
    ref = np.zeros(len(NAMES))
    for k, v_ in {"divorce": -3, "separation": -2, "infidelity": -2, "conflict": -2, "abuse": -3,
                  "unhappy": -2, "affection": 2, "collab": 2, "children": 1,
                  "parted_by_death": 1}.items():
        ref[NAMES.index(k)] = v_
    a_ref = ev(ref)
    print(f"\n  the reading in use today scores {a_ref:.4f}")

    best = (a_ref, ref.copy())
    t0 = time.time()
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
        a = ev(w)
        if a > best[0]:
            best = (a, w.copy())
    print(f"  searched {len(cache):,} distinct definitions in {time.time()-t0:.0f}s")
    print(f"  BEST {best[0]:.4f}   (today's reading {a_ref:.4f})")
    print(f"\n  {'group':<20}{'today':>7}{'found':>7}")
    for i, k in enumerate(NAMES):
        print(f"  {k:<20}{ref[i]:>7.0f}{best[1][i]:>7.0f}")
    json.dump({"config": {"lam": LAM, "nfeat": NFEAT, "keep": KEEP, "nfold": NFOLD,
                          "seeds": list(SEEDS), "iters": ITERS},
               "groups": NAMES, "best_weights": list(map(float, best[1])),
               "best_auc": best[0], "reference_weights": list(map(float, ref)),
               "reference_auc": a_ref, "n_definitions": len(cache),
               "n_patterns": int(len(table)), "n_couples": int(len(sp))},
              open(os.environ.get("AQ_RESULT", "/tmp/target_result.json"), "w"), indent=1)
    print(f"\n  saved {os.environ.get('AQ_RESULT', '/tmp/target_result.json')}")


if __name__ == "__main__":
    main()
