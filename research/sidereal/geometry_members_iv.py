"""
geometry_members_iv.py — the SAME sky read in other geometries (operator 2026-08-21: diversity + robustness).
Everything here is derived from the stored sidereal longitudes, so it costs no new ephemeris and cannot drift
from the rest of the pipeline:

  DRACONIC     every body measured from the true node (λ − λ☊): the "soul chart" of 20th-century practice; a whole
               zodiac the model has never seen, and one that is INVARIANT to the ayanāṁśa by construction.
  ANTISCIA     the solstice mirror λ' = (180° − λ): a symmetry the Hellenistic authors read as strongly as an
               aspect; contacts between one partner's antiscia and the other's natal degrees.
  FIXED STARS  separations from Regulus, Spica, Algol, Aldebaran, Antares and the Galactic Centre — in the SIDEREAL
               frame these sit still, so a constant longitude is correct to within a degree over the data's span.
  HARMONICS    node-relative harmonics h·|Δθ| for h = 5, 7, 9 (quintile / septile / novile families) — the
               harmonics nobody in the earlier sweep tried, and the ones traditions read for "fated" bonds.
  SOFT SIGNS   the birth hour is UNKNOWN, so a hard sign is a coin flip near a boundary: every sign and nakṣatra
               here is a MEMBERSHIP — the fraction of the ±6.5° hour-uncertainty window (the Moon's half-day
               motion) that falls in the dominant division, plus the boundary-crossed flag.
Writes AQ_OUT/geometry_members.npz.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from artamodel import BODIES14, auc, absdiff   # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq8feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq8sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
# sidereal (Lahiri) longitudes of the fixed points — stationary in this frame to within ~1° across 1600-2030
STARS = {"regulus": 149.7, "spica": 180.0, "algol": 56.5, "aldebaran": 45.6, "antares": 225.3, "galactic_centre": 242.3}
FAST = ("sun", "moon", "venus", "mars")


def soft_membership(lon, width, unc=6.5):
    """(dominant index, membership fraction, boundary-crossed) for a longitude known only to ±unc degrees."""
    lo = (lon - unc) % 360.0; hi = (lon + unc) % 360.0
    i_lo = np.floor(lo / width); i_hi = np.floor(hi / width)
    crossed = (i_lo != i_hi).astype(float)
    edge = (i_lo + 1) * width
    span_lo = np.where(crossed > 0, (edge - lo) % 360.0, 2 * unc)
    frac_lo = np.clip(span_lo / (2 * unc), 0, 1)
    dom = np.where(frac_lo >= 0.5, i_lo, i_hi); frac = np.maximum(frac_lo, 1 - frac_lo)
    out_dom = np.where(np.isfinite(lon), dom, np.nan); out_frac = np.where(np.isfinite(lon), frac, np.nan)
    return out_dom, out_frac, np.where(np.isfinite(lon), crossed, np.nan)


def build(A, B, W, bodies):
    """A/B/W are (n, nbodies) sidereal longitudes; returns the feature block and its names."""
    j = {b: bodies.index(b) for b in BODIES14}
    node_a, node_b, node_w = A[:, j["true_node"]], B[:, j["true_node"]], W[:, j["true_node"]]
    cols, names = [], []
    def add(x, nm):
        cols.append(x.reshape(len(A), -1) if x.ndim > 1 else x.reshape(-1, 1)); names.extend(nm if isinstance(nm, list) else [nm])
    # ── DRACONIC synastry: both charts rotated onto their own nodes, then compared ─────────────────────────────
    dra = []
    for b in BODIES14:
        da = (A[:, j[b]] - node_a) % 360.0; db = (B[:, j[b]] - node_b) % 360.0
        dra.append(absdiff(da, db))
    add(np.column_stack(dra), [f"draconic_syn_{b}" for b in BODIES14])
    # the wedding sky in each partner's draconic frame (the slow bodies carry it)
    for b in ("jupiter", "saturn", "uranus", "neptune", "pluto"):
        add(absdiff((W[:, j[b]] - node_w) % 360.0, (A[:, j[b]] - node_a) % 360.0), f"draconic_wed_a_{b}")
        add(absdiff((W[:, j[b]] - node_w) % 360.0, (B[:, j[b]] - node_b) % 360.0), f"draconic_wed_b_{b}")
    # ── ANTISCIA: one partner's solstice mirror against the other's natal degree ───────────────────────────────
    anti = []
    for b in BODIES14:
        anti.append(absdiff((180.0 - A[:, j[b]]) % 360.0, B[:, j[b]]))
        anti.append(absdiff((180.0 - B[:, j[b]]) % 360.0, A[:, j[b]]))
    add(np.column_stack(anti), [f"antiscia_{d}_{b}" for b in BODIES14 for d in ("ab", "ba")][:len(anti)])
    # ── FIXED STARS: each partner's fast bodies against the six fixed points ───────────────────────────────────
    st = []; stn = []
    for star, sl in STARS.items():
        for b in FAST:
            st.append(absdiff(A[:, j[b]], np.full(len(A), sl))); stn.append(f"star_a_{star}_{b}")
            st.append(absdiff(B[:, j[b]], np.full(len(A), sl))); stn.append(f"star_b_{star}_{b}")
        st.append(np.fmin(absdiff(A[:, j["sun"]], np.full(len(A), sl)), absdiff(B[:, j["sun"]], np.full(len(A), sl)))); stn.append(f"star_min_{star}_sun")
    add(np.column_stack(st), stn)
    # ── UNTRIED HARMONICS of the synastry separation ───────────────────────────────────────────────────────────
    for h in (5, 7, 9):
        hh = []
        for b in BODIES14:
            hh.append(absdiff((h * (A[:, j[b]] - B[:, j[b]])) % 360.0, 0.0))
        add(np.column_stack(hh), [f"h{h}_{b}" for b in BODIES14])
    # ── SOFT SIGN / NAKṢATRA MEMBERSHIPS (robustness: the hour is unknown) ─────────────────────────────────────
    for tag, M in (("a", A), ("b", B)):
        for b in ("sun", "moon", "venus"):
            for nm, width in (("sign", 30.0), ("nak", 360.0 / 27)):
                d_, f_, c_ = soft_membership(M[:, j[b]], width)
                add(d_, f"{tag}_{b}_{nm}"); add(f_, f"{tag}_{b}_{nm}_conf"); add(c_, f"{tag}_{b}_{nm}_cross")
    # same-sign / same-nakṣatra agreement WEIGHTED by both memberships (a soft match, not a claim)
    for b in ("sun", "moon", "venus"):
        for nm, width in (("sign", 30.0), ("nak", 360.0 / 27)):
            da, fa, _ = soft_membership(A[:, j[b]], width); db, fb, _ = soft_membership(B[:, j[b]], width)
            add(np.where(np.isfinite(da + db), (da == db).astype(float) * fa * fb, np.nan), f"soft_same_{nm}_{b}")
    X = np.column_stack(cols).astype(np.float32)
    return X, names


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True); s1, s2 = list(Z["slots"]); bodies = list(Z["bodies"])
    y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    A, B, W = Z[f"theta_{s1}_train"], Z[f"theta_{s2}_train"], Z["theta_wed_train"]
    Ae, Be, We = Z[f"theta_{s1}_test"], Z[f"theta_{s2}_test"], Z["theta_wed_test"]
    Xtr, names = build(A, B, W, bodies); Xte, _ = build(Ae, Be, We, bodies)
    log(f"{Xtr.shape[1]} geometry features · train {Xtr.shape[0]:,} · test {Xte.shape[0]:,}")
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    plain = lambda p: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]), np.abs(p[:, ia] - p[:, ib]), p[:, iy]])
    prm = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.5, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)
    members_tr, members_te, mnames, meta = [], [], [], []
    def member(Xa, Xb, name):
        rows = np.isfinite(Xa).any(1); s_tr = np.full(len(y), np.nan)
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = rows & (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); fit = rows & (later <= lo)
            if fit.sum() < 500:
                continue
            c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[fit], y[fit]); s_tr[blk] = c.predict_proba(Xa[blk])[:, 1]
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[rows], y[rows])
        s_te = np.full(len(Xb), np.nan); rte = np.isfinite(Xb).any(1); s_te[rte] = c.predict_proba(Xb[rte])[:, 1]
        f = np.isfinite(s_tr) & (later > cuts[0]); o = auc(y[f], s_tr[f]) if f.sum() > 500 else float("nan")
        members_tr.append(s_tr); members_te.append(s_te); mnames.append(name); meta.append({"member": name, "forward_oof": o, "n_features": int(Xa.shape[1])})
        log(f"  {name:<48} {Xa.shape[1]:>4} feats  fwd-OOF {o:.4f}")
    grp = lambda pref: [i for i, n in enumerate(names) if n.startswith(pref)]
    for pref, nm in (("draconic", "DRACONIC (node-relative zodiac)"), ("antiscia", "ANTISCIA (solstice mirrors)"),
                     ("star_", "FIXED STARS (Regulus, Spica, Algol, …)"), ("h5", "HARMONIC 5 (quintiles)"),
                     ("h7", "HARMONIC 7 (septiles)"), ("h9", "HARMONIC 9 (noviles)"),
                     ("a_", "SOFT SIGNS/NAKṢATRAS (hour-marginalised)")):
        cols = grp(pref) + (grp("b_") + grp("soft_same") if pref == "a_" else [])
        if cols:
            member(Xtr[:, cols], Xte[:, cols], nm + " (no ages)")
    member(Xtr, Xte, "GEOMETRY ALL (no ages)")
    member(np.column_stack([plain(ptr), Xtr]), np.column_stack([plain(pte), Xte]), "PLAIN + GEOMETRY ALL")
    np.savez_compressed(os.path.join(OUT, "geometry_members.npz"), S_train=np.column_stack(members_tr), S_test=np.column_stack(members_te),
                        names=np.array(mnames), meta=json.dumps(meta), feature_names=np.array(names, dtype=object))
    log(f"wrote {OUT}/geometry_members.npz with {len(mnames)} members")


if __name__ == "__main__":
    main()
