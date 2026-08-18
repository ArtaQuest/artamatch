"""
decisive.py — is the fitted coherent field carrying anything the age gap does not already carry?

WHY THIS TEST AND NOT ANOTHER. The sweep found that every configuration restricted to FAST bodies scores at
chance out of time, and every configuration including JUPITER AND SLOWER scores 0.52-0.56. There is a mechanical
reason that could produce exactly that pattern without any astrology: |b + sum w_k e^{i h theta_k}|^2 expands to
cross terms cos(theta_j^older - theta_k^younger), and for a SLOW body that phase difference is very nearly
(mean motion) x (difference in birth dates) -- a direct, unwrapped, monotone encoding of the AGE GAP.

    Pluto 1.45 deg/yr -> a 0-60 year gap spans 0-87 deg, no wrapping at all
    Neptune 2.19       -> 0-131 deg
    Uranus 4.29        -> 0-257 deg
    Saturn 12.2        -> wraps twice
    Mars 191, Sun 360+ -> wraps hundreds of times, unreadable as a gap

So the slow bodies give the field a clean channel to the age gap, and the fast bodies give it none. If that is
what is happening, the field is a worse instrument for the age gap than the age gap, and it adds nothing.

THREE MEASUREMENTS DECIDE IT
  1. rank correlation between the field's held-out score and the age gap
  2. the field's AUC WITHIN narrow age-gap bands, pooled over concordant pairs -- if the field only reads the
     gap, holding the gap flat removes its whole score
  3. whether a two-feature combiner (gap + field) beats the gap alone out of time, with the combiner FITTED ON
     THE TRAINING HALF -- the only question that matters for the deliverable
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coherent_fit import SETS, Coherent, auc, basis          # noqa: E402

OUT = os.environ.get("AQ_OUT", "/tmp/aqcoh")
Z = np.load(os.path.join(OUT, "lon.npz"))
LONtr, LONte = Z["lon_train"], Z["lon_test"]
ytr, yte = Z["y_train"].astype(np.int64), Z["y_test"].astype(np.int64)
yr_tr, yr_te = Z["yr_train"], Z["yr_test"]

keep = ~np.all(np.isclose(LONtr[0], LONtr[1], atol=1e-4), axis=0)
LONtr, ytr, yr_tr = LONtr[:, :, keep], ytr[keep], yr_tr[:, keep]
later = yr_tr.max(0)
inner = later > np.quantile(later, 0.85)

WHICH, F, L2, ORB = os.environ.get("AQ_SET", "all18"), 8, 1e-2, 30.0
Ctr, Str, kept = basis(LONtr, SETS[WHICH], ORB)
Cte, Ste, _ = basis(LONte, SETS[WHICH], ORB)
K = Ctr.shape[1]

# The configuration the sweep selected on the inner split. Refitted here over more seeds and averaged, which is
# what an ensemble of this model would ship as.
str_tr, str_te = [], []
for seed in range(5):
    m = Coherent(K, F, seed=seed)
    rng = np.random.default_rng(1000 + seed)
    idx = np.where(~inner)[0]
    best, state, bad = -1.0, None, 0
    for ep in range(30):
        rng.shuffle(idx)
        for s0 in range(0, len(idx), 4096):
            b = idx[s0:s0 + 4096]
            if len(b) >= 64:
                m.step(Ctr[b], Str[b], ytr[b].astype(float), 0.01, L2)
        z, _, _, _ = m.logit(Ctr[inner], Str[inner])
        a = auc(ytr[inner], z)
        if a > best + 1e-5:
            best, bad = a, 0
            state = (m.A1.copy(), m.A2.copy(), m.br.copy(), m.bi.copy(), m.w.copy(),
                     m.c, m.mu.copy(), m.sd.copy())
        else:
            bad += 1
            if bad >= 8:
                break
    m.A1, m.A2, m.br, m.bi, m.w, m.c, m.mu, m.sd = state
    str_tr.append(m.logit(Ctr, Str)[0])
    str_te.append(m.logit(Cte, Ste)[0])
s_tr, s_te = np.mean(str_tr, 0), np.mean(str_te, 0)

gap_tr = (yr_tr[1] - yr_tr[0]).astype(float)
gap_te = (yr_te[1] - yr_te[0]).astype(float)
a_field = auc(yte, s_te)
ag = auc(yte, gap_te)
a_gap = max(ag, 1 - ag)
sign = 1.0 if ag > 0.5 else -1.0
print(f"  set '{WHICH}', {F} fields, L2 {L2:g}, orb {ORB:g} — 5-seed mean")
print(f"    field held-out AUC     {a_field:.4f}")
print(f"    age-gap held-out AUC   {a_gap:.4f}")

# ── 1. rank correlation with the age gap ──────────────────────────────────────────────────────────────────
def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


rho = spearman(s_te, gap_te)
print(f"\n  1. rank correlation between the field's score and the age gap: rho = {rho:+.3f}")

# ── 2. the field's AUC with the gap held flat ─────────────────────────────────────────────────────────────
def pooled(y, s, band):
    num = den = 0.0
    used = 0
    for b in np.unique(band):
        m_ = band == b
        yy, ss = y[m_], s[m_]
        n1, n0 = int(yy.sum()), int((1 - yy).sum())
        if n1 == 0 or n0 == 0:
            continue
        num += auc(yy, ss) * n1 * n0
        den += n1 * n0
        used += 1
    return (num / den if den else float("nan")), used, int(den)


for w in (1, 2, 3):
    band = (np.abs(gap_te) // w) * w
    af, nb, npr = pooled(yte, s_te, band)
    agp, _, _ = pooled(yte, sign * gap_te, band)
    print(f"  2. gap held flat in {w}-year bands ({nb} bands, {npr:,} pairs): "
          f"field {af:.4f} · gap itself {agp:.4f}")

# ── 3. does the field ADD to the gap, out of time? combiner fitted on the training half ───────────────────
def fit_logit(X, y, iters=3000, lr=0.3, l2=1e-4):
    X = np.column_stack([np.ones(len(X)), X])
    mu, sd = X[:, 1:].mean(0), X[:, 1:].std(0) + 1e-9
    X[:, 1:] = (X[:, 1:] - mu) / sd
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ w, -30, 30)))
        g = X.T @ (p - y) / len(y) + l2 * w
        g[0] -= l2 * w[0]
        w -= lr * g
    return w, mu, sd


def apply_logit(w, mu, sd, X):
    X = np.column_stack([np.ones(len(X)), (np.asarray(X, float) - mu) / sd])
    return X @ w


for name, Xtr, Xte in (("gap alone", gap_tr[:, None], gap_te[:, None]),
                       ("field alone", s_tr[:, None], s_te[:, None]),
                       ("gap + field", np.column_stack([gap_tr, s_tr]),
                        np.column_stack([gap_te, s_te]))):
    w, mu, sd = fit_logit(Xtr, ytr.astype(float))
    print(f"  3. {name:<12} held-out AUC {auc(yte, apply_logit(w, mu, sd, Xte)):.4f}")
