"""
world3_members_iv.py — the last of the world's popular date-keyed marriage rules.

After world_members (calendars + the big electional systems) and world2 (the remaining matching algorithms),
an audit against actual populations found nine systems still missing, each consulted by millions and each a
pure function of the dates:

  손 없는 날 (Korea)         "the day without spirits" — lunar days ending in 9 or 0. This, not gunghap, is what
                            actually decides when a Korean wedding or house-move is booked.
  寡婦年 / 雙春年 (China)     the "widow year", a lunar year containing no Lì Chūn, and its opposite the
                            "double-spring year" with two. The belief moves the national marriage rate enough
                            that the Ministry of Civil Affairs has commented on it.
  YATYAZA · PYATHADA (Myanmar) the inauspicious days printed on every Burmese calendar, from the Myanmar month
                            and weekday (see mmcal.py, verified against the reference implementation).
  WAN PHRA (Thailand/Laos/Cambodia) the Buddhist sabbath — 8th and 15th waxing, 8th and last waning.
  TU B'AV · LAG BA'OMER (Jewish) the two days that are the EXCEPTIONS to the mourning periods world_members
                            already blocks on — Lag BaOmer is the single day inside the Omer when a wedding is
                            held, and Tu B'Av is the traditional day of matches.
  НЕ В МАЕ (Slavic)         "marry in May and toil all your life", plus the Orthodox rule against Wednesday and
                            Friday eves.
  KAULANA MAHINA / MARAMATAKA (Hawai'i, Aotearoa) the thirty named moon-nights, still used to schedule.
  RĀHU KĀLAM (South India, Sri Lanka) the weekday-keyed inauspicious eighth of the day — the rule a Sri Lankan
                            or Tamil family checks before fixing the nekath.
  PARSI / ZOROASTRIAN       the thirty day-names of the Shahenshahi calendar.
  AKAN KRA DIN (Ghana)      the soul-name given by the birth weekday, gendered.

Writes AQ_OUT/world3_members.npz.
"""
import datetime as dt
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from artamodel import auc          # noqa: E402
import mmcal                        # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq9c"); PH = os.environ.get("AQ_PHASES", "/tmp/aq9feat/phases.npz")
OUT = os.environ.get("AQ_OUT", "/tmp/aq9sub"); QS = (0.40, 0.55, 0.70, 0.85, 1.0)
import time
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)

_LD = {}


def lunar(d):
    k = d.toordinal()
    if k not in _LD:
        try:
            from lunardate import LunarDate
            L = LunarDate.from_solar_date(d.year, d.month, d.day)
            _LD[k] = (L.month, L.day, int(getattr(L, "isLeapMonth", False)))
        except Exception:
            _LD[k] = None
    return _LD[k]


_CNY = {}


def cny(year):
    """Gregorian date of Chinese New Year — lunar 1/1 of that year."""
    if year not in _CNY:
        _CNY[year] = None
        for off in range(0, 62):                       # CNY always falls between 21 Jan and 21 Feb
            d = dt.date(year, 1, 21) + dt.timedelta(days=off)
            L = lunar(d)
            if L and L[0] == 1 and L[1] == 1 and not L[2]:
                _CNY[year] = d
                break
    return _CNY[year]


def spring_count(d):
    """Lì Chūn count in the lunar year containing d: 0 = 寡婦年 widow year, 2 = 雙春年 double spring."""
    if lunar(d) is None:
        return None
    this = cny(d.year)
    if this is None:
        return None
    y = d.year if d >= this else d.year - 1        # which lunar year the date falls in
    a, b = cny(y), cny(y + 1)
    if a is None or b is None:
        return None
    n = 0
    for yy in (y, y + 1):
        lc = dt.date(yy, 2, 4)                          # Lì Chūn, 315° solar longitude, ±1 day
        if a <= lc < b:
            n += 1
    return n


HAWAIIAN = ["Hilo", "Hoaka", "Kukahi", "Kulua", "Kukolu", "Kupau", "Olekukahi", "Olekulua", "Olekukolu",
            "Olepau", "Huna", "Mohalu", "Hua", "Akua", "Hoku", "Mahealani", "Kulu", "Laaukukahi", "Laaukulua",
            "Laaupau", "Olekukahi2", "Olekulua2", "Olepau2", "Kaloakukahi", "Kaloakulua", "Kaloapau", "Kane",
            "Lono", "Mauli", "Muku"]
RAHU_ORDER = {6: 8, 0: 2, 1: 7, 2: 5, 3: 6, 4: 4, 5: 3}    # weekday() → which eighth of the day is Rāhu Kālam
AKAN_M = ["Kwasi", "Kwadwo", "Kwabena", "Kwaku", "Yaw", "Kofi", "Kwame"]


def day3(dstr):
    if not isinstance(dstr, str) or len(dstr) < 10 or dstr.endswith("-00") or dstr[:4] == "0000":
        return [np.nan] * 18
    try:
        d = dt.date(int(dstr[:4]), int(dstr[5:7]), int(dstr[8:10]))
    except Exception:
        return [np.nan] * 18
    J = d.toordinal() + 1721425; wd = d.weekday()
    L = lunar(d)
    lm, ld = (L[0], L[1]) if L else (np.nan, np.nan)
    # 손 없는 날 — the lunar day ends in 9 or 0
    son = float(ld % 10 in (9, 0)) if L else np.nan
    # 寡婦年 / 雙春年
    sc = spring_count(d); widow = float(sc == 0) if sc is not None else np.nan
    dbl = float(sc == 2) if sc is not None else np.nan
    # Myanmar
    myt, my, mm, md = mmcal.j2m(J); mwd = (J + 2) % 7      # 0=Sat … 6=Fri
    yat = float(mmcal.yatyaza(mm, mwd)); pya = float(mmcal.pyathada(mm, mwd))
    mp = mmcal.cal_mp(md, mm, myt)
    sabbath = float(mp in (1, 3) or md in (8, 23))
    # Wan Phra — the Theravāda sabbath, off the same lunar day
    wanphra = float(ld in (8, 15, 23, 29, 30)) if L else np.nan
    # Hebrew exceptions to the mourning periods
    try:
        from convertdate import hebrew
        hy, hm, hd = hebrew.from_gregorian(d.year, d.month, d.day)
        # Nisan=1 numbering: Av is 5 (Tu B'Av = 15 Av), Iyyar is 2 (Lag BaOmer = 18 Iyyar)
        tubav = float(hm == hebrew.AV and hd == 15); lag = float(hm == hebrew.IYYAR and hd == 18)
    except Exception:
        tubav = lag = np.nan
    # Slavic + Orthodox
    may = float(d.month == 5); wedfri = float(wd in (2, 4))
    # the thirty moon-nights
    moonnight = float((ld - 1) % 30) if L else np.nan
    kapu = float(ld in (3, 4, 5, 6, 13, 14, 15, 27, 28)) if L else np.nan   # the kapu (restricted) nights
    # Rāhu Kālam
    rahu = float(RAHU_ORDER[wd])
    # Parsi Shahenshahi: a flat 365-day year, so the day-name is a pure count from a known anchor
    parsi_day = float((J - 1945351) % 365 % 30); parsi_month = float(((J - 1945351) % 365) // 30)
    return [float(wd), lm, ld, son, widow, dbl, float(mm), yat, pya, sabbath, wanphra, tubav, lag, may, wedfri,
            moonnight, kapu, rahu]


D3 = ["wd", "lunar_month", "lunar_day", "son_eomneun_nal", "widow_year", "double_spring", "myanmar_month",
      "yatyaza", "pyathada", "myanmar_sabbath", "wan_phra", "tu_bav", "lag_baomer", "married_in_may",
      "wed_or_fri", "moon_night", "kapu_night", "rahu_kalam"]


def build(df, Z, half):
    cols = []; names = []
    for tag, s in (("wed", df.start), ("a", df.dob_a), ("b", df.dob_b)):
        E = np.array([day3(v) for v in s], dtype=float)
        keep = list(range(len(D3))) if tag == "wed" else [D3.index(n) for n in ("wd", "lunar_day", "moon_night", "myanmar_month")]
        cols.append(E[:, keep]); names += [f"{tag}_{D3[k]}" for k in keep]
        if tag == "a":
            Ea = E
        elif tag == "b":
            Eb = E
    # AKAN KRA DIN — the soul-name from the birth weekday; the dataset is gendered, a is the man
    wa = Ea[:, 0]; wb = Eb[:, 0]
    cols.append(np.column_stack([wa, wb, (wa == wb).astype(float), (wa - wb) % 7]))
    names += ["akan_a", "akan_b", "akan_same_day", "akan_day_dist"]
    # the two moon-night readings against each other
    ma = Ea[:, D3.index("moon_night")]; mb = Eb[:, D3.index("moon_night")]
    ok = np.isfinite(ma) & np.isfinite(mb)
    cols.append(np.column_stack([np.where(ok, (ma == mb).astype(float), np.nan), np.where(ok, (ma - mb) % 30, np.nan)]))
    names += ["moon_night_same", "moon_night_dist"]
    return np.column_stack(cols).astype(np.float32), names


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True); y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1)
    cuts = [np.quantile(later, q) for q in QS]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); s1, s2 = list(Z["slots"])
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    Xtr, names = build(tr, Z, "train"); log(f"train built: {Xtr.shape[1]} features"); Xte, _ = build(te, Z, "test"); log("test built")
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    plain = lambda p: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]), np.abs(p[:, ia] - p[:, ib]), p[:, iy]])
    prm = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.7,
               subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)
    mt, me, mn, meta = [], [], [], []
    def member(cols, name):
        Xa = Xtr[:, cols]; Xb = Xte[:, cols]; rows = np.isfinite(Xa).any(1); s_tr = np.full(len(y), np.nan)
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = rows & (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); fit = rows & (later <= lo)
            if fit.sum() < 500:
                continue
            c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[fit], y[fit]); s_tr[blk] = c.predict_proba(Xa[blk])[:, 1]
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[rows], y[rows])
        s_te = np.full(len(Xb), np.nan); rte = np.isfinite(Xb).any(1); s_te[rte] = c.predict_proba(Xb[rte])[:, 1]
        f = np.isfinite(s_tr) & (later > cuts[0]); o = auc(y[f], s_tr[f]) if f.sum() > 500 else float("nan")
        mt.append(s_tr); me.append(s_te); mn.append(name); meta.append({"member": name, "forward_oof": o, "n_features": len(cols)})
        log(f"  {name:<50} {len(cols):>3} feats · fwd-OOF {o:.4f}")
    idx = lambda p: [i for i, n in enumerate(names) if p(n)]
    member(idx(lambda n: "son_eomneun" in n), "손 없는 날 — the Korean day without spirits")
    member(idx(lambda n: "widow_year" in n or "double_spring" in n), "寡婦年 / 雙春年 — widow and double-spring years")
    member(idx(lambda n: "yatyaza" in n or "pyathada" in n or "myanmar" in n), "YATYAZA · PYATHADA (Myanmar)")
    member(idx(lambda n: "wan_phra" in n), "WAN PHRA — the Theravāda sabbath")
    member(idx(lambda n: "tu_bav" in n or "lag_baomer" in n), "TU B'AV · LAG BA'OMER")
    member(idx(lambda n: "married_in_may" in n or "wed_or_fri" in n), "НЕ В МАЕ — the Slavic and Orthodox day rules")
    member(idx(lambda n: "moon_night" in n or "kapu" in n), "KAULANA MAHINA · MARAMATAKA — the thirty moon-nights")
    member(idx(lambda n: "rahu_kalam" in n), "RĀHU KĀLAM")
    member(idx(lambda n: n.startswith("akan_")), "AKAN KRA DIN — the soul-name of the birth weekday")
    member(list(range(len(names))), "WORLD3 ALL (no ages)")
    Xtr = np.column_stack([plain(ptr), Xtr]); Xte = np.column_stack([plain(pte), Xte])
    names = ["age_older", "age_younger", "age_gap", "start_year"] + names
    member(list(range(len(names))), "PLAIN + WORLD3 ALL")
    np.savez_compressed(os.path.join(OUT, "world3_members.npz"), S_train=np.column_stack(mt), S_test=np.column_stack(me),
                        names=np.array(mn), meta=json.dumps(meta), feature_names=np.array(names, dtype=object))
    log(f"wrote {OUT}/world3_members.npz with {len(mn)} members")


if __name__ == "__main__":
    main()
