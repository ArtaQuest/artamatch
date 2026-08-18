"""
sweep_wedding_day.py — "finetune 365 options for a global optimal date of marriage that max out AUC".

For every year-only start (published as YYYY-01-01) the wedding DAY is unknown. Treat it as ONE global parameter
D in 1..365 shared by all such rows, cast the wedding-day panchanga (tithi, nakshatra, yoga, karana, vaara, lunar
month; sidereal, noon UT -- place-independent to within the day) at start_year + D, fit a small model on the
training rows, and score. The choice of D is made on an inner TEMPORAL split of the training half; the held-out
half is read once, for the chosen D, plus the whole curve for the record.

What to expect, stated before running: a single fixed day moves only the fast quantities (the Moon's tithi and
nakshatra, the weekday), which the label has never cared about at 09:00-fixed birth times either; the 365
options should differ within noise. If one D stands out on train AND out of time, that is a finding.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_o = sys.stdout; sys.stdout = open(os.devnull, "w")
from jhora import utils as JU
from jhora.panchanga import drik
sys.stdout = _o
drik.set_ayanamsa_mode("LAHIRI")
SRC = os.environ.get("AQ_SRC", "/tmp/aq3")
SOL = os.environ.get("AQ_SOL", f"{SRC}/solution.csv")
STEP = int(os.environ.get("AQ_STEP") or 1)
T0 = time.time()
PLACE = drik.Place("greenwich", 51.48, 0.0, 0.0)


def auc(y, s):
    from scipy.stats import rankdata
    y = np.asarray(y, np.int64); s = np.asarray(s, float); m = np.isfinite(s); y, s = y[m], s[m]
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(s); return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


_cache = {}


def panchanga(y, doy):
    key = (y, doy)
    if key in _cache:
        return _cache[key]
    d = pd.Timestamp(year=y, month=1, day=1) + pd.Timedelta(days=doy - 1)
    jd = JU.julian_day_number((d.year, d.month, d.day), (12, 0, 0))
    try:
        t = drik.tithi(jd, PLACE)[0]; n = drik.nakshatra(jd, PLACE)[0]; yg = drik.yogam(jd, PLACE)[0]
        k = drik.karana(jd, PLACE)[0]; v = drik.vaara(jd, PLACE); lm = drik.lunar_month(jd, PLACE)[0]
        out = (t, n, yg, k, v, lm)
    except Exception:
        out = (np.nan,) * 6
    _cache[key] = out
    return out


def main():
    import lightgbm as lgb
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    sol = pd.read_csv(SOL).set_index("id"); lab = [c for c in sol.columns if c != "Usage"][0]
    ytr = tr[lab].astype(int).to_numpy(); yte = sol.loc[te.id, lab].to_numpy().astype(int)
    j1_tr = (tr.start.str[5:] == "01-01").to_numpy(); j1_te = (te.start.str[5:] == "01-01").to_numpy()
    sy_tr = tr.start.str[:4].astype(int).to_numpy(); sy_te = te.start.str[:4].astype(int).to_numpy()
    later = np.maximum(pd.to_numeric(tr.dob_older.str[:4], errors="coerce").fillna(0),
                       pd.to_numeric(tr.dob_younger.str[:4], errors="coerce").fillna(0)).to_numpy()
    inner = later > np.quantile(later, 0.85)
    print(f"  year-only starts: train {j1_tr.sum():,} of {len(tr):,} · held out {j1_te.sum():,} of {len(te):,}")
    print(f"  sweeping D = 1..365 step {STEP}; the choice is made on the inner temporal split (births after "
          f"{np.quantile(later, 0.85):.0f}), the held-out column read once for the winner\n")
    # the rows we can move: the year-only starts. Everything else keeps its real day (control group).
    Ttr, Tte = tr[j1_tr].reset_index(drop=True), te[j1_te].reset_index(drop=True)
    yT, yE = ytr[j1_tr], yte[j1_te]; innT = inner[j1_tr]
    fitm = ~innT
    res = []
    for D in range(1, 366, STEP):
        Xtr = np.array([panchanga(int(y), D) for y in sy_tr[j1_tr]], float)
        Xte = np.array([panchanga(int(y), D) for y in sy_te[j1_te]], float)
        m = lgb.LGBMClassifier(n_estimators=150, learning_rate=0.05, num_leaves=7, min_child_samples=100,
                               reg_lambda=10.0, random_state=0, verbose=-1).fit(Xtr[fitm], yT[fitm])
        a_in = auc(yT[innT], m.predict_proba(Xtr[innT])[:, 1])
        a_out = auc(yE, m.predict_proba(Xte)[:, 1])
        res.append((D, a_in, a_out))
        if D % (25 * STEP) == 1 or D == 1:
            print(f"    D={D:>3}: inner {a_in:.4f}  held {a_out:.4f}   [{time.time()-T0:.0f}s]", flush=True)
    res = np.array(res)
    best = res[np.argmax(res[:, 1])]
    se_in = 0.5 / np.sqrt(min(int(yT[innT].sum()), int((1 - yT[innT]).sum())))
    print(f"\n  inner AUC over the {len(res)} days: mean {res[:,1].mean():.4f}, sd {res[:,1].std():.4f}, "
          f"max {res[:,1].max():.4f} at D={int(best[0])}  (inner se ~{se_in:.4f}; the max of {len(res)} nulls sits near "
          f"{0.5 + se_in*np.sqrt(2*np.log(len(res))):.4f})")
    print(f"  CHOSEN D = {int(best[0])} (inner {best[1]:.4f}) -> held out {best[2]:.4f}")
    print(f"  held-out AUC over all days: mean {res[:,2].mean():.4f}, sd {res[:,2].std():.4f}, "
          f"max {res[:,2].max():.4f} (selecting on it would be cheating)")
    print(f"  Jan 1 as published (D=1): inner {res[0,1]:.4f}, held out {res[0,2]:.4f}")
    verdict = ("one day stands out beyond noise" if best[1] > 0.5 + se_in * np.sqrt(2 * np.log(len(res))) + 0.01
               else "the 365 options differ within noise: the wedding day, when it is not known, cannot be recovered by tuning")
    print(f"  VERDICT: {verdict}")
    np.savetxt(os.path.join(SRC, "wedding_day_sweep.csv"), res, delimiter=",", header="D,inner_auc,heldout_auc", comments="")


if __name__ == "__main__":
    main()
