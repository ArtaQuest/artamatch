"""
calendar_members_iv.py — the world's CALENDARS as stack members (operator 2026-08-20: "different western vs eastern
ephemeries or different calendars"). Every date in the files is proleptic Gregorian; here each birth and the start
are re-expressed in five other calendars and the fine structure of each becomes features:
  JALALI (Persian solar)   month, day, |Δmonth| of the pair, start month/day, Nowruz proximity (day-of-year)
  ISLAMIC (Hijri lunar)    month, day, pair |Δmonth| (wraps at 12), start month — a pure lunar count, so it drifts
                           against the seasons: astrology-free lunar-phase information at yearly precision
  HEBREW (lunisolar)       month, day, pair |Δmonth|, start month
  JULIAN (old style)       the Gregorian−Julian day gap at the date, and whether the date crosses a month boundary
                           when re-expressed (a data-provenance signal for pre-1918 eastern records)
  CHINESE sexagenary       year stem, branch, the pair's branch difference mod 12 (the six harms/combines), the
                           start year's animal — arithmetic on the year, no ephemeris
All order-free for the pair (max/min/|Δ|). One LightGBM member per calendar (no ages), one PLAIN+ALL-CALENDARS
member, forward-chained OOF. Writes AQ_OUT/calendar_members.npz.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from convertdate import hebrew, islamic, julian, persian

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from artamodel import auc   # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq4"); PH = os.environ.get("AQ_PHASES", "/tmp/aq4feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq4sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
_C = {}


def conv(d):
    """(jalali_m, jalali_d, islamic_m, islamic_d, hebrew_m, hebrew_d, julian_gap_days, stem, branch) for a Gregorian date string, NaNs at reduced precision."""
    if d in _C:
        return _C[d]
    nan9 = (np.nan,) * 9
    if not isinstance(d, str) or d == "0000-00-00":
        _C[d] = nan9; return nan9
    y = int(d[:4]); m = int(d[5:7]) or 0; dd = int(d[8:10]) or 0
    stem = (y - 4) % 10; branch = (y - 4) % 12
    if m == 0 or dd == 0:
        out = (np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, float(stem), float(branch))
        _C[d] = out; return out
    try:
        jm = persian.from_gregorian(y, m, dd); im = islamic.from_gregorian(y, m, dd); hm = hebrew.from_gregorian(y, m, dd)
        jy, jmn, jdd = julian.from_gregorian(y, m, dd)
        import datetime as dt
        gap = (dt.date(y, m, dd) - dt.date(y, m, dd)).days  # placeholder; the real gap:
        # Gregorian-Julian gap in days = JD(greg) - JD(julian date literal) -- compute via ordinal difference
        gap = (dt.date(y, m, dd).toordinal() - dt.date(jy, jmn, min(jdd, 28)).toordinal()) if 1 <= jmn <= 12 else np.nan
        out = (float(jm[1]), float(jm[2]), float(im[1]), float(im[2]), float(hm[1]), float(hm[2]), float(gap), float(stem), float(branch))
    except Exception:
        out = (np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, float(stem), float(branch))
    _C[d] = out; return out


def build(df):
    A = np.array([conv(d) for d in df.dob_a]); B = np.array([conv(d) for d in df.dob_b]); S = np.array([conv(d) for d in df.start])
    def cyc(a, b, mod):
        d = np.abs(a - b); return np.fmin(d, mod - d)
    blocks = {}
    for name, (mi, di, mod) in {"jalali": (0, 1, 12), "islamic": (2, 3, 12), "hebrew": (4, 5, 13)}.items():
        blocks[name] = np.column_stack([np.fmax(A[:, mi], B[:, mi]), np.fmin(A[:, mi], B[:, mi]), cyc(A[:, mi], B[:, mi], mod),
                                        np.fmax(A[:, di], B[:, di]), np.fmin(A[:, di], B[:, di]), S[:, mi], S[:, di],
                                        (A[:, mi] == B[:, mi]).astype(float)])
    blocks["julian"] = np.column_stack([A[:, 6], B[:, 6], S[:, 6], np.abs(A[:, 6] - B[:, 6])])
    blocks["chinese_sexagenary"] = np.column_stack([np.fmax(A[:, 7], B[:, 7]), np.fmin(A[:, 7], B[:, 7]), cyc(A[:, 8], B[:, 8], 12),
                                                    (cyc(A[:, 8], B[:, 8], 12) == 6).astype(float), ((A[:, 8] + B[:, 8]) % 12 == 1).astype(float),
                                                    S[:, 8], cyc(A[:, 7], B[:, 7], 10)])
    return blocks


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True); y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); s1, s2 = list(Z["slots"])
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    btr = build(tr); bte = build(te); log(f"calendars converted ({len(_C):,} distinct dates)")
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    plain = lambda p: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]), np.abs(p[:, ia] - p[:, ib]), p[:, iy]])
    prm = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.7, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)
    members_tr, members_te, names, meta = [], [], [], []
    def member(Xa, Xb, name):
        s_tr = np.full(len(y), np.nan)
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[later <= lo], y[later <= lo]); s_tr[blk] = c.predict_proba(Xa[blk])[:, 1]
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa, y); s_te = c.predict_proba(Xb)[:, 1]
        f = np.isfinite(s_tr) & (later > cuts[0]); o = auc(y[f], s_tr[f]); members_tr.append(s_tr); members_te.append(s_te); names.append(name); meta.append({"member": name, "forward_oof": o})
        log(f"  {name:<44} {Xa.shape[1]:>3} features  fwd-OOF {o:.4f}")
    for k in btr:
        member(btr[k], bte[k], f"CALENDAR {k} (no ages)")
    allc_tr = np.column_stack([btr[k] for k in btr]); allc_te = np.column_stack([bte[k] for k in bte])
    member(np.column_stack([plain(ptr), allc_tr]), np.column_stack([plain(pte), allc_te]), "PLAIN + ALL CALENDARS")
    np.savez_compressed(os.path.join(OUT, "calendar_members.npz"), S_train=np.column_stack(members_tr), S_test=np.column_stack(members_te), names=np.array(names), meta=json.dumps(meta))
    log(f"wrote {OUT}/calendar_members.npz")


if __name__ == "__main__":
    main()
