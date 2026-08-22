"""
maya_members_iv.py — the MESOAMERICAN count as its own family (operator 2026-08-22: "u forgot the maya").

The Maya calendar is the most structurally different time system in the pool: it does not track the Sun at all.
The Tzolkʼin runs 13 numbers against 20 day-signs (260 days, coprime cycles), the Haabʼ runs 365 days as 18
months of 20 plus the 5 Wayebʼ, the two mesh into a 18,980-day Calendar Round, and the Long Count is a pure
positional day count. Because 260 and 365 share no factor with the year, these cycles are almost decorrelated
from everything else the model reads — which is exactly why they are worth their own family rather than a
footnote in the tropical traditions module.

Correlation: GMT 584283 (0.0.0.0.0 = 4 Ahau 8 Cumkʼu). Everything is exact integer arithmetic on the date, so it
is computable for any past or future day and carries no precision assumptions — a year-only date yields NaN, as
it should, because the Tzolkʼin position of an unknown day is unknown.

Features, per partner and for the wedding: Tzolkʼin number (1-13) and day-sign (20), the sign's directional
quarter (E/N/W/S) and its Lord-of-the-Night (9), the trecena, the Haabʼ month and day, the Wayebʼ flag, the
Calendar-Round position, the Long Count digits, and the Year Bearer. For the couple: same-sign and same-number
agreement, the cyclic distances between the two Tzolkʼin positions (the Maya reading of compatibility is the
relation between day-signs), and the same between each partner and the wedding day.
Writes AQ_OUT/maya_members.npz.
"""
import datetime as dt
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from artamodel import auc   # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq9c"); PH = os.environ.get("AQ_PHASES", "/tmp/aq9feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq9sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
GMT = 584283            # the Goodman-Martinez-Thompson correlation: JDN of 0.0.0.0.0, 4 Ahau 8 Cumkʼu
# the 20 day-signs in order, with the directional quarter each belongs to (Imix=East, then N, W, S, repeating)
SIGNS = ["imix", "ik", "akbal", "kan", "chicchan", "cimi", "manik", "lamat", "muluc", "oc",
         "chuen", "eb", "ben", "ix", "men", "cib", "caban", "etznab", "cauac", "ahau"]
YEAR_BEARERS = {2, 7, 12, 17}      # Ikʼ, Manikʼ, Ebʼ, Kabʼan in the classic system (sign indices)


def jdn(dstr):
    """Julian Day Number of a proleptic-Gregorian YYYY-MM-DD, or NaN when the day is not known."""
    if not isinstance(dstr, str) or len(dstr) < 10 or dstr.endswith("-00") or dstr[:4] == "0000":
        return np.nan
    try:
        return float(dt.date(int(dstr[:4]), int(dstr[5:7]), int(dstr[8:10])).toordinal() + 1721425)
    except Exception:
        return np.nan


def maya(dstr):
    """The full Mesoamerican reading of one day: Tzolkʼin, Haabʼ, Calendar Round, Long Count, Lord of the Night."""
    j = jdn(dstr)
    if not np.isfinite(j):
        return [np.nan] * 14
    d = int(j) - GMT                                   # days since the Long Count zero
    tz_num = ((d + 4 - 1) % 13) + 1                    # 0.0.0.0.0 was 4 Ahau
    tz_sign = (d + 19) % 20                            # ... and Ahau is sign 19
    tz_pos = d % 260                                   # position in the 260-day round
    trecena = tz_pos // 13
    haab_doy = (d + 348) % 365                         # 8 Cumkʼu = month 17, day 8 -> 348
    haab_m = haab_doy // 20; haab_d = haab_doy % 20
    wayeb = float(haab_m == 18)
    cr = d % 18980                                     # the 52-year Calendar Round
    lord = ((d + 8) % 9) + 1                           # the nine Lords of the Night
    quarter = tz_sign % 4                              # East / North / West / South
    bearer = float(tz_sign in YEAR_BEARERS)
    baktun = (d // 144000) % 20; katun = (d // 7200) % 20; tun = (d // 360) % 20
    return [float(tz_num), float(tz_sign), float(tz_pos), float(trecena), float(haab_m), float(haab_d), wayeb,
            float(cr), float(lord), float(quarter), bearer, float(baktun), float(katun), float(tun)]


NAMES1 = ["tz_num", "tz_sign", "tz_pos", "trecena", "haab_month", "haab_day", "wayeb", "cal_round", "lord_night",
          "quarter", "year_bearer", "baktun", "katun", "tun"]


def cyc(a, b, m):
    d = np.abs(a - b); return np.fmin(d, m - d)


def build(df):
    A = np.array([maya(x) for x in df.dob_a], dtype=float)
    B = np.array([maya(x) for x in df.dob_b], dtype=float)
    W = np.array([maya(x) for x in df.start], dtype=float)
    i = {n: k for k, n in enumerate(NAMES1)}
    cols, names = [], []
    def add(x, nm):
        cols.append(np.asarray(x, dtype=float).reshape(len(df), -1)); names.extend(nm if isinstance(nm, list) else [nm])
    for tag, M in (("a", A), ("b", B), ("wed", W)):
        add(M, [f"{tag}_{n}" for n in NAMES1])
    # the couple's reading: agreement and cyclic distance between the two day-signs, numbers and rounds
    add(cyc(A[:, i["tz_sign"]], B[:, i["tz_sign"]], 20), "pair_sign_dist")
    add((A[:, i["tz_sign"]] == B[:, i["tz_sign"]]).astype(float), "pair_same_sign")
    add(cyc(A[:, i["tz_num"]], B[:, i["tz_num"]], 13), "pair_num_dist")
    add((A[:, i["tz_num"]] == B[:, i["tz_num"]]).astype(float), "pair_same_num")
    add(cyc(A[:, i["tz_pos"]], B[:, i["tz_pos"]], 260), "pair_tzolkin_dist")
    add((A[:, i["quarter"]] == B[:, i["quarter"]]).astype(float), "pair_same_quarter")
    add((A[:, i["lord_night"]] == B[:, i["lord_night"]]).astype(float), "pair_same_lord")
    add(cyc(A[:, i["haab_month"]] * 20 + A[:, i["haab_day"]], B[:, i["haab_month"]] * 20 + B[:, i["haab_day"]], 365), "pair_haab_dist")
    add(cyc(A[:, i["cal_round"]], B[:, i["cal_round"]], 18980), "pair_calround_dist")
    # each partner against the WEDDING day — the electional half of the system
    for tag, M in (("a", A), ("b", B)):
        add(cyc(M[:, i["tz_sign"]], W[:, i["tz_sign"]], 20), f"{tag}_wed_sign_dist")
        add((M[:, i["tz_sign"]] == W[:, i["tz_sign"]]).astype(float), f"{tag}_wed_same_sign")
        add(cyc(M[:, i["tz_pos"]], W[:, i["tz_pos"]], 260), f"{tag}_wed_tzolkin_dist")
        add(cyc(M[:, i["tz_num"]], W[:, i["tz_num"]], 13), f"{tag}_wed_num_dist")
    X = np.column_stack(cols).astype(np.float32)
    return X, names


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True); y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); s1, s2 = list(Z["slots"])
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    Xtr, names = build(tr); Xte, _ = build(te)
    log(f"{Xtr.shape[1]} Mesoamerican features · train {Xtr.shape[0]:,} · test {Xte.shape[0]:,} · "
        f"day-precision rows: train {np.isfinite(Xtr[:, 0]).mean():.0%}, test {np.isfinite(Xte[:, 0]).mean():.0%}")
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    plain = lambda p: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]), np.abs(p[:, ia] - p[:, ib]), p[:, iy]])
    prm = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.7, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)
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
        members_tr.append(s_tr); members_te.append(s_te); mnames.append(name); meta.append({"member": name, "forward_oof": o, "n_features": int(Xa.shape[1]), "n_rows": int(rows.sum())})
        log(f"  {name:<44} {Xa.shape[1]:>3} feats · {rows.sum():>7,} rows · fwd-OOF {o:.4f}")
    tzo = [k for k, n in enumerate(names) if "tz_" in n or "trecena" in n or "quarter" in n or "lord" in n]
    member(Xtr[:, tzo], Xte[:, tzo], "MAYA Tzolkʼin only (260-day, no ages)")
    member(Xtr, Xte, "MAYA full count (Tzolkʼin+Haabʼ+Long Count, no ages)")
    member(np.column_stack([plain(ptr), Xtr]), np.column_stack([plain(pte), Xte]), "PLAIN + MAYA")
    np.savez_compressed(os.path.join(OUT, "maya_members.npz"), S_train=np.column_stack(members_tr), S_test=np.column_stack(members_te),
                        names=np.array(mnames), meta=json.dumps(meta), feature_names=np.array(names, dtype=object))
    log(f"wrote {OUT}/maya_members.npz with {len(mnames)} members")


if __name__ == "__main__":
    main()
