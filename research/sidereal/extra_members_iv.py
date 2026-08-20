"""
extra_members_iv.py — more astrology, numerology and calendar members for the edition-IV stack (2026-08-19, "keep
brainstorming and adding astrology + numerology features"):
  CALENDAR+NUMEROLOGY  start month / weekday / day-of-year, both birth months (order-free), |Δmonth|, same-sidereal-
                       sign flag (Sun), life-path numbers of both births (order-free), their pair, start's life path —
                       the fine structure of the dates, which the ages cannot carry; LightGBM, forward OOF
  HARMONIC h synastry  coherent field over h·|θ1 − θ2| for h = 2, 3, 4, 6 (oppositions/squares, trines, sextiles)
  PROGRESSED synastry  secondary progressions (a day for a year): each partner's Sun/Moon/Mercury/Venus/Mars at
                       dob + age days, vs the other partner's natal longitude and vs the start sky — |Δθ|, even
  FAST synastry        the a-term sum over the five fast bodies alone (Sun..Mars)
Every member's train scores are forward-chained OOF; test scores from the all-train fit; written to
AQ_OUT/extra_members.npz for artamodel_iv_ensemble.py (AQ_EXTRA=).
"""
import datetime as dt
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "coherent")); sys.path.insert(0, os.path.join(ROOT, "web"))
from artamodel import BODIES14, auc, absdiff                                    # noqa: E402
from artamodel_full_stack import _fit                                           # noqa: E402
from artamodel_stack_forward import forward_member                              # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq4"); PH = os.environ.get("AQ_PHASES", "/tmp/aq4feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq4sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


def lifepath(d):
    if not d or d == "0000-00-00":
        return np.nan
    digits = [int(c) for c in d if c.isdigit() and c != "0" or c == "0"]; s = sum(int(c) for c in d if c.isdigit())
    while s > 9 and s not in (11, 22, 33):
        s = sum(int(c) for c in str(s))
    return float(s)


def progressed(df, later_col_unused=None):
    """Progressed longitudes (sidereal Lahiri) of Sun/Moon/Mercury/Venus/Mars for each partner at dob + age days."""
    import sweshim as SW
    SW.load(os.path.join(ROOT, "web", "ephem4.bin"), os.path.join(ROOT, "web", "tables.json")); SW.set_sid_mode(SW.SIDM_LAHIRI)
    codes = [SW.SUN, SW.MOON, SW.MERCURY, SW.VENUS, SW.MARS]; n = len(df)
    out = {"a": np.full((n, 5), np.nan), "b": np.full((n, 5), np.nan)}
    cache = {}
    for i, r in enumerate(df.itertuples(index=False)):
        if r.start.endswith("-00"):
            continue
        try:
            sy, sm, sd = int(r.start[:4]), int(r.start[5:7]), int(r.start[8:10])
        except Exception:
            continue
        for slot in ("a", "b"):
            d = getattr(r, f"dob_{slot}")
            if not isinstance(d, str) or d == "0000-00-00" or d.endswith("-00"):
                continue
            y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
            try:
                age_days = (dt.date(sy, sm, sd) - dt.date(y, m, dd)).days / 365.2425       # years -> progressed DAYS after birth
                jd = SW.julday(y, m, dd, 9.0) + age_days
            except Exception:
                continue
            key = round(jd, 3)
            if key not in cache:
                try:
                    aya = SW.get_ayanamsa_ut(jd); cache[key] = [(SW.calc_ut(jd, c)[0][0] - aya) % 360.0 for c in codes]
                except Exception:
                    cache[key] = [np.nan] * 5
            out[slot][i] = cache[key]
    return out


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True); s1, s2 = list(Z["slots"]); bodies = list(Z["bodies"]); y = Z["y_train"].astype(np.int64); ids = Z["id_test"]
    A, B, W = Z[f"theta_{s1}_train"], Z[f"theta_{s2}_train"], Z["theta_wed_train"]; Ae, Be, We = Z[f"theta_{s1}_test"], Z[f"theta_{s2}_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    j1 = ptr[:, pn.index("start_year_only")] == 1.0; j1e = pte[:, pn.index("start_year_only")] == 1.0; W = W.copy(); We = We.copy(); W[j1] = np.nan; We[j1e] = np.nan
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    members_tr, members_te, names, meta = [], [], [], []
    def add(s_tr, s_te, name, nfit):
        members_tr.append(s_tr); members_te.append(s_te); names.append(name); f = np.isfinite(s_tr) & (later > cuts[0])
        o = auc(y[f], s_tr[f]) if f.sum() > 500 and len(np.unique(y[f])) > 1 else float("nan"); meta.append({"member": name, "forward_oof": o, "n_fit": int(nfit)})
        log(f"  {name:<44} fit {nfit:>7,}  fwd-OOF {o:.4f}")
    # ---- CALENDAR + NUMEROLOGY (LightGBM) ----
    def cal(df, p):
        st = pd.to_datetime(df.start, errors="coerce"); m = st.dt.month.astype('float64').to_numpy().copy(); wd = st.dt.weekday.astype('float64').to_numpy().copy(); doy = st.dt.dayofyear.astype('float64').to_numpy().copy()
        noday = df.start.str.endswith("-00").to_numpy(); yearonly = df.start.str.endswith("-00-00").to_numpy(); wd[noday] = np.nan; doy[noday] = np.nan; m[yearonly] = np.nan
        m[noday & ~yearonly] = pd.to_numeric(df.start.str[5:7], errors="coerce").to_numpy()[noday & ~yearonly]
        ma = pd.to_numeric(df.dob_a.str[5:7], errors="coerce").replace(0, np.nan).to_numpy(); mb = pd.to_numeric(df.dob_b.str[5:7], errors="coerce").replace(0, np.nan).to_numpy()
        lpa = np.array([lifepath(d) for d in df.dob_a]); lpb = np.array([lifepath(d) for d in df.dob_b]); lps = np.array([lifepath(d) for d in df.start])
        dm = np.abs(ma - mb); dm = np.fmin(dm, 12 - dm)
        ia, ib = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"); a, b = p[:, ia], p[:, ib]
        return np.column_stack([np.fmax(a, b), np.fmin(a, b), np.abs(a - b), p[:, pn.index("start_year")], m, wd, doy, np.fmax(ma, mb), np.fmin(ma, mb), dm, np.fmax(lpa, lpb), np.fmin(lpa, lpb), lps,
                                (np.fmax(lpa, lpb) * 40 + np.fmin(lpa, lpb)), np.where(np.isfinite(A[:, bodies.index("sun")] if len(p) == len(A) else Ae[:, bodies.index("sun")]) & np.isfinite(B[:, bodies.index("sun")] if len(p) == len(A) else Be[:, bodies.index("sun")]),
                                          (np.floor((A if len(p) == len(A) else Ae)[:, bodies.index("sun")] / 30) == np.floor((B if len(p) == len(A) else Be)[:, bodies.index("sun")] / 30)).astype(float), np.nan)])
    Xc, Xce = cal(tr, ptr), cal(te, pte)
    prm = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)
    s_tr = np.full(len(y), np.nan)
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xc[later <= lo], y[later <= lo]); s_tr[blk] = c.predict_proba(Xc[blk])[:, 1]
    c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xc, y); add(s_tr, c.predict_proba(Xce)[:, 1], "CALENDAR + NUMEROLOGY (plain + date fine structure)", len(y))
    # the same WITHOUT the plain ages — the fine structure alone, to see whether it carries anything of its own
    s_tr = np.full(len(y), np.nan); cols = list(range(4, Xc.shape[1]))
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xc[later <= lo][:, cols], y[later <= lo]); s_tr[blk] = c.predict_proba(Xc[blk][:, cols])[:, 1]
    c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xc[:, cols], y); add(s_tr, c.predict_proba(Xce[:, cols])[:, 1], "CALENDAR + NUMEROLOGY alone (no ages)", len(y))
    # ---- HARMONIC synastry sums and the fast-body a-term ----
    Bi = [bodies.index(b) for b in BODIES14]
    D = absdiff(A[:, Bi], B[:, Bi]); De = absdiff(Ae[:, Bi], Be[:, Bi])
    for h in (2, 3, 4, 6):
        s_tr, s_te, n, _ = forward_member((h * D) % 360.0, y, later, (h * De) % 360.0, cuts); add(s_tr, s_te, f"HARMONIC {h} synastry sum (14 bodies)", n)
    fast = [BODIES14.index(b) for b in ("sun", "moon", "mercury", "venus", "mars")]
    s_tr, s_te, n, _ = forward_member(D[:, fast], y, later, De[:, fast], cuts); add(s_tr, s_te, "FAST synastry sum (Sun..Mars)", n)
    # ---- PROGRESSED synastry ----
    log("  progressed positions via sweshim …"); Pg = progressed(tr); Pge = progressed(te)
    nat = {"a": A[:, [bodies.index(b) for b in ("sun", "moon", "mercury", "venus", "mars")]], "b": B[:, [bodies.index(b) for b in ("sun", "moon", "mercury", "venus", "mars")]]}
    nate = {"a": Ae[:, [bodies.index(b) for b in ("sun", "moon", "mercury", "venus", "mars")]], "b": Be[:, [bodies.index(b) for b in ("sun", "moon", "mercury", "venus", "mars")]]}
    wedf = W[:, [bodies.index(b) for b in ("sun", "moon", "mercury", "venus", "mars")]]; wedfe = We[:, [bodies.index(b) for b in ("sun", "moon", "mercury", "venus", "mars")]]
    # progressed of each partner vs the OTHER's natal (even under swap as a set of two terms), and vs the start sky
    Ptr = np.column_stack([absdiff(Pg["a"], nat["b"]), absdiff(Pg["b"], nat["a"]), absdiff(Pg["a"], wedf), absdiff(Pg["b"], wedf)])
    Pte = np.column_stack([absdiff(Pge["a"], nate["b"]), absdiff(Pge["b"], nate["a"]), absdiff(Pge["a"], wedfe), absdiff(Pge["b"], wedfe)])
    s_tr, s_te, n, _ = forward_member(Ptr, y, later, Pte, cuts); add(s_tr, s_te, "PROGRESSED synastry + progressed-to-start (20 phasors)", n)
    s_tr, s_te, n, _ = forward_member(Ptr[:, :10], y, later, Pte[:, :10], cuts); add(s_tr, s_te, "PROGRESSED synastry only (10 phasors)", n)
    np.savez_compressed(os.path.join(OUT, "extra_members.npz"), S_train=np.column_stack(members_tr), S_test=np.column_stack(members_te), names=np.array(names), meta=json.dumps(meta))
    log(f"wrote {OUT}/extra_members.npz with {len(names)} members")


if __name__ == "__main__":
    main()
