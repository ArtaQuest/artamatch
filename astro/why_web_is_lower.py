"""Why the shipped browser model scores 0.6815 where the laptop stack scored 0.7311.

The two numbers were never measured on the same couples. The laptop stack ran on a seeded 60,000-couple
subsample of the whole 1800-2030 dataset; the browser model can only run on births the shipped ephemeris
asset covers, 1900-2030, which is 81,249 couples of the 135,005 - and the 53,756 it drops are 46.3%
positive against 24.0% inside. This script measures the gap instead of arguing about it: it takes the
stack's OWN out-of-fold predictions and re-scores them on the browser model's population.
"""
import json, os, numpy as np
os.environ.setdefault("AQ_COUPLES", os.path.expanduser("~/Studio/artamatch/research/data-dob/couples-parents.json"))
os.environ.setdefault("AQ_SUBSAMPLE", "60000")
os.environ.setdefault("AQ_EPHEM_CACHE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephem-core.npz"))
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
import core

E = core.load()
P = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "astro-out/astro-oof.npy"))
assert P.shape[0] == E.n, f"OOF rows {P.shape[0]} != loaded rows {E.n} — different run, stop here"
Y, gid = E.Y, E.gid

# The shipped asset spans 1900-01-01 .. 2030-12-31. Julian day of those bounds.
LO, HI = 2415020.5, 2462867.5
jo, jy = E.JD[0], E.JD[1]
win = (jo >= LO) & (jo <= HI) & (jy >= LO) & (jy <= HI)
print(f"loaded {E.n:,} couples · positive {100*Y.mean():.1f}%")
print(f"  inside the shipped 1900-2030 asset window: {win.sum():,} ({100*win.mean():.1f}%) · "
      f"positive {100*Y[win].mean():.1f}%")
print(f"  outside (pre-1900 births):                 {(~win).sum():,} · positive {100*Y[~win].mean():.1f}%")

def meta(rows, C=0.03):
    """The stack's meta logistic, fitted and scored out-of-fold on whichever rows are given."""
    Pr, Yr, gr = P[rows], Y[rows], gid[rows]
    pred = np.zeros(len(Yr))
    for tr, te in GroupKFold(n_splits=5).split(Pr, Yr, groups=gr):
        mu, sd = Pr[tr].mean(0), Pr[tr].std(0) + 1e-9
        m = LogisticRegression(C=C, max_iter=4000).fit((Pr[tr] - mu) / sd, Yr[tr])
        pred[te] = m.predict_proba((Pr[te] - mu) / sd)[:, 1]
    return roc_auc_score(Yr, pred)

allrows = np.arange(E.n)
a_all = meta(allrows)
# Same fitted-on-everything model, but SCORED only where the browser model can run. Isolates population
# from model: nothing about the model changed between these two lines, only which rows are counted.
pred_all = np.zeros(E.n)
for tr, te in GroupKFold(n_splits=5).split(P, Y, groups=gid):
    mu, sd = P[tr].mean(0), P[tr].std(0) + 1e-9
    m = LogisticRegression(C=0.03, max_iter=4000).fit((P[tr] - mu) / sd, Y[tr])
    pred_all[te] = m.predict_proba((P[te] - mu) / sd)[:, 1]
a_scored_in = roc_auc_score(Y[win], pred_all[win])
a_refit_in = meta(np.where(win)[0])

print(f"\n  THE LAPTOP STACK, 45 base blocks, same OOF columns throughout")
print(f"    on all 1800-2030 rows            {a_all:.4f}   <- the 0.7311 headline")
print(f"    same model, scored on 1900-2030   {a_scored_in:.4f}   ({a_scored_in-a_all:+.4f})")
print(f"    refitted inside 1900-2030 only    {a_refit_in:.4f}   ({a_refit_in-a_all:+.4f})")

# Per-block, the same two regimes: which blocks were carrying the pre-1900 rows.
s = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "astro-out/astro-stack.json")))
base = s["base_models"]
rows = []
for j, b in enumerate(base):
    rows.append((b.get("key", f"col{j}"), roc_auc_score(Y, P[:, j]), roc_auc_score(Y[win], P[win, j])))
rows.sort(key=lambda r: -r[1])
print(f"\n  {'block':<58} {'1800+':>7} {'1900+':>7} {'delta':>7}")
for k, a, b in rows[:12]:
    print(f"  {k[:58]:<58} {a:>7.4f} {b:>7.4f} {b-a:>+7.4f}")
print(f"  {'...':<58}")
for k, a, b in rows[-3:]:
    print(f"  {k[:58]:<58} {a:>7.4f} {b:>7.4f} {b-a:>+7.4f}")
med = np.median([b - a for _, a, b in rows])
print(f"\n  median per-block change when the pre-1900 rows are removed: {med:+.4f}")
json.dump({"all": a_all, "scored_in_window": a_scored_in, "refit_in_window": a_refit_in,
           "n_all": int(E.n), "n_window": int(win.sum()),
           "rate_all": float(Y.mean()), "rate_window": float(Y[win].mean()),
           "per_block": [{"key": k, "auc_1800": a, "auc_1900": b} for k, a, b in rows]},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "astro-out/window-effect.json"), "w"), indent=1)
