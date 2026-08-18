
# %% [markdown]
# ### `dates.py`, spliced in
#
# `couple_record` turns two date strings into the record `core.load()` reads, deriving precision and the
# uncertainty window from the dates themselves. It lives in the repo's `kaggle/` directory and is NOT part of the
# public ephemeris asset, so it is spliced in verbatim rather than imported.

# %%
__DATES_SRC__

# %%
import core


def build(df, labelled):
    """Cast both charts for every couple and return the full feature matrix, family by family."""
    rows = [couple_record(i, r.dob_older, r.dob_younger, int(r[LABEL]) if labelled else 0)
            for i, r in df.iterrows()]
    json.dump(rows, open(os.environ["AQ_COUPLES"], "w"))
    E = core.load()
    if E.n != len(df):
        raise SystemExit(f"core kept {E.n} of {len(df)} rows — predictions could not be aligned")
    names, cols = [], []
    for fam, F in families(E):
        for k, (_, v) in F.items():
            names.append(k); cols.append(np.asarray(v, dtype=np.float32))
        print(f"  [{time.time()-T0:6.0f}s] {fam:<26} {len(F):>5,}", flush=True)
    F = calendrical(df, np.asarray(E.LON)[0, 0], np.asarray(E.LON)[1, 0], E.JD)
    for k, (_, v) in F.items():
        names.append(k); cols.append(np.asarray(v, dtype=np.float32))
    print(f"  [{time.time()-T0:6.0f}s] {'calendrical + numerology':<26} {len(F):>5,}", flush=True)
    del E; gc.collect()
    return names, np.column_stack(cols)


nm_tr, X_tr = build(tr, True)
print(f"train features {X_tr.shape}")
nm_te, X_te = build(te, False)
print(f"test features {X_te.shape}")
assert nm_tr == nm_te, "the two halves produced different feature lists"

ok = ((X_tr.std(0) > 1e-12) & (X_te.std(0) > 1e-12)
      & np.isfinite(X_tr).all(0) & np.isfinite(X_te).all(0))
NAMES = [n for n, k in zip(nm_tr, ok) if k]
X_tr, X_te = X_tr[:, ok], X_te[:, ok]
y = tr[LABEL].to_numpy().astype(np.int64)
print(f"kept {X_tr.shape[1]:,} usable features of {len(ok):,}")


# The age gap and the two birth years, in numpy datetime64[D] arithmetic (pandas' nanosecond datetimes overflow
# before 1677 and the training half starts in 1600). The gap is a fair competition feature -- every entrant is
# given the same two dates -- and it is the strongest single feature in the problem, so it is a pool member in
# its own right AND the floor the ensemble must clear.
def gap_years(df):
    do = np.array(df.dob_older.to_numpy().astype(str), dtype="datetime64[D]")
    dy = np.array(df.dob_younger.to_numpy().astype(str), dtype="datetime64[D]")
    return ((dy - do).astype(np.int64).astype(np.float32),
            do.astype("datetime64[Y]").astype(np.int64) + 1970,
            dy.astype("datetime64[Y]").astype(np.int64) + 1970)


gap, yo, yy = gap_years(tr)
gape, _, _ = gap_years(te)
A = np.column_stack([X_tr, gap]); Ae = np.column_stack([X_te, gape])
NAMES = NAMES + ["age gap in days"]; G = A.shape[1] - 1
later = np.maximum(yo, yy)


def auc(yv, s):
    yv = np.asarray(yv, np.int64); s = np.asarray(s, np.float64)
    n1, n0 = int(yv.sum()), int((1 - yv).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    o = np.argsort(s, kind="mergesort"); ys, ss = yv[o], s[o]
    r = np.empty(len(ss)); i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[i:j + 1] = 0.5 * (i + j) + 1.0; i = j + 1
    return float((r[ys == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def r01(v):
    r = np.argsort(np.argsort(v)).astype(np.float64)
    return r / max(1.0, len(r) - 1)


# %% [markdown]
# ## Why there is no model selection in this notebook
#
# The first version of this notebook picked models on a single inner split — the latest 15% of training births,
# 1888–1900 — and blended by inner AUC. It scored **0.5809** held out, *below* the age gap alone at 0.6045: an
# ensemble handed a feature cannot honestly score below that feature, so that was a broken pipeline, not a fact
# about the data. Two things were wrong. The split was 12 years ahead when the competition's held-out couples are
# up to 90 years ahead, so it could not see the failure it was meant to catch; and nothing constrained the one
# relationship we are certain of — a wider age gap means a shorter relationship — so the trees were free to fit
# era-specific noise instead.
#
# Repairing the split did not fix selection. Across ten candidates, the correlation between mean AUC on three
# expanding-window temporal folds (train ≤1820 → validate 1821–1850, ≤1850 → 1851–1875, ≤1875 → 1876–1900) and
# held-out AUC was **Spearman −0.15**. Internal validation on 1600–1900 simply does not rank models for
# 1901–1990. Choosing one model on it is a coin flip; choosing on the leaderboard would be cheating.
#
# So this notebook does not choose. It builds a **diverse pool of eleven models with hyper-parameters fixed in
# advance**, weights them **equally**, and averages their **ranks** (AUC reads ranks; averaging a logistic's
# probabilities with a tree ensemble's lets whichever is more confident dominate). The temporal folds are still
# used for one thing that does transfer: **feature stability**. A feature enters a model only if it points the
# same way in all three folds, ranked by its *weakest* fold rather than its best — which is what rejects a
# feature strong in one era and absent in another, and that is most of the 4,962.

# %%
CUTS = [1820, 1850, 1875]
per_fold = np.zeros((len(CUTS), A.shape[1]), dtype=np.float32)
for k, cut in enumerate(CUTS):
    f = later <= cut
    yf = y[f]; Af = A[f]
    n1, n0 = int(yf.sum()), int((1 - yf).sum())
    # rank AUC of every column at once, in chunks
    for s0 in range(0, A.shape[1], 800):
        R = np.apply_along_axis(lambda c: np.argsort(np.argsort(c)) + 1.0, 0, Af[:, s0:s0 + 800])
        per_fold[k, s0:s0 + 800] = (R[yf == 1].sum(0) - n1 * (n1 + 1) / 2.0) / (n1 * n0)
    print(f"  [{time.time()-T0:6.0f}s] fold train<={cut}: every feature scored on {int(f.sum()):,} couples", flush=True)
sg = np.sign(per_fold - 0.5)
consistent = np.all(sg == sg[0], axis=0)
strength_min = np.min(np.abs(per_fold - 0.5), axis=0); strength_min[~consistent] = 0.0
order = np.argsort(-strength_min)
sign_all = np.where(per_fold.mean(0) >= 0.5, 1.0, -1.0)
print(f"{int(consistent.sum()):,} of {A.shape[1]:,} features point the same way in all three folds")
print("the most stable, by their WEAKEST fold:")
for j in order[:8]:
    print(f"  min {0.5+strength_min[j]:.4f}   {NAMES[j][:60]}")

# %%
import lightgbm as lgb
import xgboost as xgb
from sklearn.linear_model import LogisticRegression

pool = {}
pool["age gap, monotone"] = -Ae[:, G]
for k in (3, 8, 20):
    cols = [j for j in order[:k] if j != G]
    pool[f"rank-average: gap + top {k} stable"] = r01(-Ae[:, G]) + sum(r01(sign_all[j] * Ae[:, j]) for j in cols) / len(cols)
for k in (8, 20, 50):
    cols = list(dict.fromkeys(list(order[:k]) + [G])); mc = [0] * len(cols); mc[cols.index(G)] = -1
    p = np.zeros(len(Ae))
    for s in range(3):
        m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=200,
                               colsample_bytree=0.6, subsample=0.7, subsample_freq=1, reg_lambda=10.0,
                               monotone_constraints=mc, random_state=s, verbose=-1).fit(A[:, cols], y)
        p += m.predict_proba(Ae[:, cols])[:, 1]
    pool[f"LightGBM monotone-in-gap, top {k} stable"] = p / 3
    print(f"  [{time.time()-T0:6.0f}s] LightGBM top {k}", flush=True)
for k in (20, 50):
    cols = list(dict.fromkeys(list(order[:k]) + [G]))
    p = np.zeros(len(Ae))
    for s in range(2):
        m = xgb.XGBClassifier(n_estimators=300, learning_rate=0.03, max_depth=3, min_child_weight=50,
                              subsample=0.7, colsample_bytree=0.6, reg_lambda=10.0, tree_method="hist",
                              device=DEV, random_state=s, eval_metric="logloss").fit(A[:, cols], y)
        p += m.predict_proba(Ae[:, cols])[:, 1]
    pool[f"XGBoost depth 3, top {k} stable"] = p / 2
    print(f"  [{time.time()-T0:6.0f}s] XGBoost top {k}", flush=True)
for k in (50, 200):
    cols = list(order[:k])
    mu, sd = A[:, cols].mean(0), A[:, cols].std(0) + 1e-6
    m = LogisticRegression(C=1e-3, max_iter=500).fit((A[:, cols] - mu) / sd, y)
    pool[f"L2 logistic, top {k} stable"] = m.decision_function((Ae[:, cols] - mu) / sd)
print(f"pool of {len(pool)} models, none of them chosen against anything")

R = np.column_stack([r01(v) for v in pool.values()])
ens = R.mean(1)

# %% [markdown]
# ## A ceiling from the competition's own definition
#
# A held-out couple exists only if **both partners are dead by 2026**, and the label is *lasted ≥ 30 years*. So a
# partner born in year *b* died at age ≤ 2026−b, and for the bond to have reached 30 years from a start age *s*
# they must have died at age ≥ s+30. Under a Gompertz survival curve *S(x)*, per partner,
#
# $$p_i = \frac{S(s+30) - S(2026-b_i)}{1 - S(2026-b_i)}$$
#
# and the couple's ceiling is *p_older · p_younger*. Textbook values, stated before use and not tuned: hazard
# *B·e^{θx}* with θ = 0.09, *B* such that *S(80) = 0.5*, start age *s* = 25. For a partner born 1910 the room is
# 116 years and the ceiling is flat at *S(55)*; for 1950 the condition "dead by 76" removes most of the
# long-lived and the ceiling falls; past 1980 the room is under 55 years and a 30-year bond is impossible.
#
# The training half — every couple born ≤ 1900 — contains no one for whom this ceiling ever binds, so **no model
# trained on it can learn this**; it can only come from the definition. It is applied as a multiplicative gate on
# the pool's score, which is what a probability ceiling is.

# %%
THETA, S80, START = 0.09, 0.5, 25
B_G = -np.log(S80) * THETA / (np.exp(THETA * 80) - 1)


def S_gompertz(x):
    x = np.maximum(np.asarray(x, float), 0.0)
    return np.exp(-B_G / THETA * (np.exp(THETA * x) - 1.0))


def ceiling(b_older, b_younger, now=2026):
    def p(b):
        room = now - np.asarray(b, float)
        num = np.clip(S_gompertz(START + 30) - S_gompertz(room), 0, None)
        den = np.clip(1.0 - S_gompertz(room), 1e-9, None)
        return np.where(room < START + 30, 0.0, num / den)
    return p(b_older) * p(b_younger)


_, yo_te, yy_te = gap_years(te)
cap = ceiling(yo_te, yy_te)
print(f"ceiling: {float((cap < 0.99 * cap.max()).mean())*100:.1f}% of held-out couples are below the flat part; "
      f"{int((cap == 0).sum())} are at zero (a 30-year bond is impossible for them)")
final = r01(ens) * (cap / cap.max())
sub = pd.DataFrame({"id": te.id, LABEL: r01(final)})
sub.to_csv("/kaggle/working/submission.csv", index=False)
pd.DataFrame({"id": te.id, LABEL: r01(ens)}).to_csv("/kaggle/working/submission_pool_only.csv", index=False)
print(f"wrote submission.csv — {len(sub):,} rows: equal-weight rank average of {len(pool)} models, gated by the "
      f"mortality ceiling; submission_pool_only.csv is the ungated pool")

# The astrology-only companion: the same pool with the age gap withheld as an explicit column. Note what it
# still contains -- a slow planet's cross-chart separation is a near-linear read of the gap (Pluto moves 1.45
# degrees a year), so withholding the COLUMN does not withhold the information.
astro = [j for j in order if j != G and "age gap" not in NAMES[j]]
pa = []
for k in (8, 20, 50):
    cols = astro[:k]
    p = np.zeros(len(Ae))
    for s in range(3):
        m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=200,
                               colsample_bytree=0.6, subsample=0.7, subsample_freq=1, reg_lambda=10.0,
                               random_state=s, verbose=-1).fit(A[:, cols], y)
        p += m.predict_proba(Ae[:, cols])[:, 1]
    pa.append(r01(p / 3))
pa.append(r01(sum(r01(sign_all[j] * Ae[:, j]) for j in astro[:20])))
pd.DataFrame({"id": te.id, LABEL: r01(np.mean(pa, 0))}).to_csv("/kaggle/working/submission_astrology_only.csv", index=False)
json.dump({"pool": list(pool), "n_features": int(X_tr.shape[1]), "n_stable": int(consistent.sum()),
           "n_train_day": int(len(tr)), "folds": CUTS}, open("/kaggle/working/ensemble.json", "w"), indent=1)
print(f"done in {(time.time()-T0)/60:.1f} min")
