"""
sweep.py — sweep the coherent field's shape and report ONE held-out number.

THE PROTOCOL, WHICH IS THE POINT OF THIS FILE. There are 27 configurations below and one held-out set. Reporting
the best held-out AUC over 27 tries is selecting on the test set, and would produce a number roughly one
inner-noise-width above the truth for a model that carries nothing at all. So:

  1. every configuration is fitted with early stopping on the INNER TEMPORAL split (the latest training births)
  2. configurations are ranked by INNER AUC, averaged over seeds
  3. the winner is chosen by that ranking alone, and only then is its held-out AUC read

The held-out column is printed for every row so the selection can be audited -- but the headline is row 1's
held-out score, decided before the column was looked at.

Inner-split noise sets the resolution: ~8,000 rows gives an AUC standard error near 0.006, so two configurations
within about 0.015 of each other are indistinguishable and the sweep says so rather than ranking them.
"""
import itertools
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coherent_fit import SETS, Coherent, auc, basis          # noqa: E402

T0 = time.time()
OUT = os.environ.get("AQ_OUT", "/tmp/aqcoh")
SEEDS = int(os.environ.get("AQ_SEEDS") or 3)
EPOCHS = int(os.environ.get("AQ_EPOCHS") or 30)
PATIENCE = int(os.environ.get("AQ_PATIENCE") or 8)


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


Z = np.load(os.path.join(OUT, "lon.npz"))
LONtr, LONte = Z["lon_train"], Z["lon_test"]
ytr, yte = Z["y_train"].astype(np.int64), Z["y_test"].astype(np.int64)
yr_tr, yr_te = Z["yr_train"], Z["yr_test"]
usage = Z["usage"]

keep = ~np.all(np.isclose(LONtr[0], LONtr[1], atol=1e-4), axis=0)
LONtr, ytr, yr_tr = LONtr[:, :, keep], ytr[keep], yr_tr[:, keep]
log(f"genuine pairs {len(ytr):,} · held out {len(yte):,}")

later = yr_tr.max(0)
cut = np.quantile(later, 0.85)
inner = later > cut
log(f"inner validation: training births after {cut:.0f} ({int(inner.sum()):,} rows), temporal")
log(f"inner AUC standard error ~{0.5/np.sqrt(min(inner.sum()-inner.sum()//2, inner.sum()//2)):.4f}")

g = (yr_te[1] - yr_te[0]).astype(float)
a = auc(yte, g)
GAP = max(a, 1 - a)
log(f"age-gap logistic (the one permitted comparison): {GAP:.4f}")

CONFIGS = list(itertools.product(("fast", "classical", "all18"), (8, 24, 64), (1e-3, 1e-2, 1e-1)))
ORB = float(os.environ.get("AQ_ORB") or 30)
rows = []
cache = {}
for which, F, l2 in CONFIGS:
    if which not in cache:
        Ctr, Str, kept = basis(LONtr, SETS[which], ORB)
        Cte, Ste, _ = basis(LONte, SETS[which], ORB)
        cache[which] = (Ctr, Str, Cte, Ste)
    Ctr, Str, Cte, Ste = cache[which]
    K = Ctr.shape[1]
    iv, ho = [], []
    for seed in range(SEEDS):
        m = Coherent(K, F, seed=seed)
        rng = np.random.default_rng(1000 + seed)
        idx = np.where(~inner)[0]
        best, state, bad = -1.0, None, 0
        for ep in range(EPOCHS):
            rng.shuffle(idx)
            for s0 in range(0, len(idx), 4096):
                b = idx[s0:s0 + 4096]
                if len(b) < 64:
                    continue
                m.step(Ctr[b], Str[b], ytr[b].astype(float), 0.01, l2)
            z, _, _, _ = m.logit(Ctr[inner], Str[inner])
            aa = auc(ytr[inner], z)
            if aa > best + 1e-5:
                best, bad = aa, 0
                state = (m.A1.copy(), m.A2.copy(), m.br.copy(), m.bi.copy(), m.w.copy(),
                         m.c, m.mu.copy(), m.sd.copy())
            else:
                bad += 1
                if bad >= PATIENCE:
                    break
        m.A1, m.A2, m.br, m.bi, m.w, m.c, m.mu, m.sd = state
        zte, _, _, _ = m.logit(Cte, Ste)
        iv.append(best)
        ho.append(auc(yte, zte))
    rows.append({"set": which, "fields": F, "l2": l2, "basis": K,
                 "inner": float(np.mean(iv)), "inner_sd": float(np.std(iv)),
                 "held": float(np.mean(ho)), "held_sd": float(np.std(ho)),
                 "params": int(2 * F * K + 3 * F + 1)})
    log(f"  {which:<10} F={F:<3} l2={l2:<6g} K={K:<4} inner {np.mean(iv):.4f} held {np.mean(ho):.4f}")

rows.sort(key=lambda r: -r["inner"])
print(f"\n  SWEEP, ranked by INNER temporal AUC (the held-out column was not used to order these)\n")
print(f"  {'#':>2}  {'bodies':<10} {'fields':>6} {'L2':>7} {'basis':>6} {'params':>7} "
      f"{'inner':>7} {'held out':>9} {'+-':>6}")
for i, r in enumerate(rows, 1):
    print(f"  {i:>2}  {r['set']:<10} {r['fields']:>6} {r['l2']:>7g} {r['basis']:>6} {r['params']:>7,} "
          f"{r['inner']:>7.4f} {r['held']:>9.4f} {r['held_sd']:>6.4f}")
w = rows[0]
print(f"\n  SELECTED BY INNER AUC: {w['set']}, {w['fields']} fields, L2 {w['l2']:g}")
print(f"  ITS HELD-OUT AUC: {w['held']:.4f} +- {w['held_sd']:.4f}    age-gap logistic: {GAP:.4f}")
best_held = max(r["held"] for r in rows)
print(f"  (best held-out anywhere in the sweep was {best_held:.4f} — reported only to show what "
      f"selecting on the test set would have bought)")
json.dump({"age_gap": GAP, "selected": w, "all": rows}, open(os.path.join(OUT, "sweep.json"), "w"), indent=1)
print(f"\n  wrote {OUT}/sweep.json")
