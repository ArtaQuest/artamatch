"""target_search.py — which definition of "a marriage that went well" does the sky explain best?

THE QUESTION. There is no single true label here. The record supports many defensible readings of
"happy": divorce counts against, stated affection counts for, children count for or not, a marriage
parted by death counts for or not. Each reading is a different target, and they are not equally
predictable from two birth dates. This searches that space of readings.

THE DANGER, AND THE GUARD. Searching targets until one scores well is how a measurement gets forged:
run enough definitions and one will fit the noise. Three things keep this honest.

  1. A THIRD of the couples were split off by bio_pool.py before any of this ran, by connected
     component of the marriage graph, and are not read here at all. The winner is evaluated there
     once, with its definition frozen.
  2. The number of rows kept is FIXED. A definition that labels only the clearest 5% of marriages
     would score better for free, so every candidate keeps the same fraction, split evenly between
     the two tails, and the AUCs are therefore comparable.
  3. The search is counted. The gap between the best score found here and the score it earns on the
     held-back third is the inflation the search bought, and it is reported as a number rather than
     hoped away.

HOW IT IS FAST. The sky does not change when the label does. The astrology design is built once and
decomposed per fold, so evaluating a candidate target is a matrix-vector product rather than a fit —
milliseconds instead of minutes, which is what makes a real search possible at all.

  AQ_KEEP=0.6   share of couples labelled (half from each tail)
  AQ_ITERS=400  random restarts + coordinate ascent steps
"""
import json, os, re, sys, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G

POOL = os.path.expanduser("~/.artamatch-dev/quality_pool")
OUT = os.path.expanduser("~/.artamatch-dev/target_search.json")
KEEP = float(os.environ.get("AQ_KEEP", "0.60"))
ITERS = int(os.environ.get("AQ_ITERS", "400"))
LAM = float(os.environ.get("AQ_LAM", "300"))
NFEAT = int(os.environ.get("AQ_NFEAT", "3000"))
SEEDS = (7, 23)

# The readings the search chooses among. Multilingual where the corpus is: a group that only fires in
# English would make the target a statement about which Wikipedia wrote the article.
GROUPS = {
 "divorce":   r"divorc|dissolv|annul|ex-husband|ex-wife|former husband|former wife|scheidung|"
              r"divorce|развод|離婚|طلاق",
 "separation":r"separat|estrang|split up|parted|left him|left her|apart|getrennt|расстал",
 "infidelity":r"affair|mistress|lover|adulter|illegitimate|unfaithful|liaison|liebschaft|любовниц",
 "conflict":  r"quarrel|dispute|litigat|sued|feud|acrimon|bitter|court battle|streit|ссор",
 "abuse":     r"violen|abus|beat her|beat him|cruel|assault|drunken|gewalt",
 "unhappy":   r"unhapp|miserabl|lovel|of convenience|arranged marriage|unglücklich|несчаст",
 "affection": r"\blove\b|loved|devot|adored|beloved|happ|inseparable|cherish|liebe|amour|"
              r"amore|любов|愛",
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


def build_design(df, Z, split):
    from v22_nnls import build as bb
    from v12_fit import side
    from denylist import clause_ok
    X, n = bb(df, Z, split)
    keep = np.array([clause_ok(k) and side(k) == "AB" for k in n]) & (X.sum(0) >= 0.02 * len(df))
    X, n = X[:, keep], [k for k, kk in zip(n, keep) if kk]
    if X.shape[1] > NFEAT:                        # cap by SUPPORT, which never looks at a label
        idx = np.argsort(-X.sum(0))[:NFEAT]
        X, n = X[:, idx], [n[i] for i in idx]
    return X, n


class FoldRidge:
    """Ridge on a fixed design, decomposed once. Scoring a new label is then a few products."""

    def __init__(self, X, gid, seeds, nfold=5):
        self.parts = []
        Xc = X - X.mean(0)
        for s in seeds:
            fold = np.random.default_rng(s).integers(0, nfold, gid.max() + 1)[gid]
            fs = []
            for k in range(nfold):
                tr = fold != k
                A = Xc[tr]
                U, S, Vt = np.linalg.svd(A, full_matrices=False)
                d = S / (S ** 2 + LAM)
                fs.append((tr, U, d, Vt, Xc[~tr]))
            self.parts.append((fold, fs))

    def auc(self, y, mask):
        """y in {0,1} on the masked rows; rows outside the mask take no part"""
        outs = []
        for fold, fs in self.parts:
            oof = np.full(len(y), np.nan)
            for (tr, U, d, Vt, Xte) in fs:
                trm = tr & mask
                if trm.sum() < 50 or len(np.unique(y[trm])) < 2:
                    continue
                yy = np.zeros(len(y)); yy[trm] = y[trm] - y[trm].mean()
                beta = Vt.T @ (d * (U.T @ yy[tr]))
                oof[~tr] = Xte @ beta
            m = mask & np.isfinite(oof)
            if m.sum() < 100 or len(np.unique(y[m])) < 2:
                return 0.5
            outs.append(G.auc(y[m].astype(int), oof[m]))
        return float(np.mean(outs)) if outs else 0.5


def label_of(H, w, keep):
    """H: n x groups indicator. Returns (y, mask) with a FIXED share of rows kept."""
    s = H @ w
    if np.allclose(s, 0):
        return np.zeros(len(s), int), np.zeros(len(s), bool)
    lo, hi = np.quantile(s, [keep / 2, 1 - keep / 2])
    if lo == hi:
        return np.zeros(len(s), int), np.zeros(len(s), bool)
    y = (s >= hi).astype(int)
    mask = (s <= lo) | (s >= hi)
    return y, mask


def main():
    pool = pd.read_csv(f"{POOL}/pool.csv")
    tr = pd.read_csv(f"{POOL}/train.csv", dtype=str)
    ids = pd.read_csv(f"{POOL}/_train_ids.csv", dtype=str)
    Z = np.load(f"{POOL}/phases.npz", allow_pickle=True)
    sp = pool[pool.side == "search"].sort_values("row").reset_index(drop=True)
    assert len(sp) == len(tr), "pool.csv and train.csv disagree"
    txt = sp.desc.fillna("").astype(str).str.lower()
    H = np.column_stack([txt.str.contains(p, regex=True).to_numpy(float) for p in GROUPS.values()])
    print(f"  {len(sp):,} search couples · {len(NAMES)} keyword groups")
    for i, k in enumerate(NAMES):
        print(f"    {k:<18}{H[:, i].mean():>6.1%} of couples")

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

    X, names = build_design(tr, Z, "train")
    print(f"\n  astrology design {X.shape[1]:,} statements · decomposing per fold "
          f"({len(SEEDS)} seeds x 5 folds)...", flush=True)
    FR = FoldRidge(X.astype(float), gid, SEEDS)
    print("  ready\n", flush=True)

    def score(w):
        y, m = label_of(H, np.asarray(w, float), KEEP)
        if m.sum() < 500:
            return 0.5, 0
        return FR.auc(y, m), int(m.sum())

    # the reading the project has used until now, as the reference point
    ref = np.zeros(len(NAMES))
    for k, v in {"divorce": -3, "separation": -2, "infidelity": -2, "conflict": -2, "abuse": -3,
                 "unhappy": -2, "affection": 2, "collab": 2, "children": 1,
                 "parted_by_death": 1}.items():
        ref[NAMES.index(k)] = v
    a0, n0 = score(ref)
    print(f"  the current reading scores {a0:.4f} on {n0:,} couples\n")

    rng = np.random.default_rng(11)
    LEVELS = np.array([-3, -2, -1, 0, 1, 2, 3], float)
    best = (a0, ref.copy(), n0)
    seen = {}
    for it in range(ITERS):
        w = (ref.copy() if it == 0 else
             rng.choice(LEVELS, len(NAMES)) if it % 4 else best[1].copy())
        improved = True
        while improved:                                   # coordinate ascent
            improved = False
            for j in rng.permutation(len(NAMES)):
                cur = w[j]
                for v in LEVELS:
                    if v == cur:
                        continue
                    w[j] = v
                    key = tuple(w)
                    if key in seen:
                        a, n = seen[key]
                    else:
                        a, n = score(w); seen[key] = (a, n)
                    if a > best[0] + 1e-6:
                        best = (a, w.copy(), n); cur = v; improved = True
                    else:
                        w[j] = cur
                w[j] = cur
        if it % 50 == 0:
            print(f"    iter {it:>4}  best {best[0]:.4f}  ({len(seen):,} definitions tried)",
                  flush=True)

    a, w, n = best
    print(f"\n  BEST on the search half: {a:.4f} on {n:,} couples "
          f"({len(seen):,} definitions evaluated)")
    print(f"  the current reading:     {a0:.4f}")
    print(f"\n  {'group':<20}{'current':>9}{'found':>8}")
    for i, k in enumerate(NAMES):
        print(f"  {k:<20}{ref[i]:>9.0f}{w[i]:>8.0f}")
    json.dump({"groups": NAMES, "weights": list(map(float, w)), "reference": list(map(float, ref)),
               "search_auc": a, "reference_auc": a0, "kept": n, "keep_frac": KEEP,
               "definitions_tried": len(seen), "lam": LAM, "n_features": int(X.shape[1]),
               "patterns": {k: v for k, v in GROUPS.items()}},
              open(OUT, "w"), indent=1)
    print(f"\n  saved {OUT}")
    print("  NOTHING is claimed from this number. Run target_confirm.py to spend the held-back third.")


if __name__ == "__main__":
    main()
