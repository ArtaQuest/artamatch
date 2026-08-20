"""
zodiac_members_iv.py — WESTERN vs EASTERN zodiacs as stack members (operator 2026-08-20). The phases in phases.npz
are sidereal Lahiri; every other zodiac is the same longitudes shifted by (ayanāṁśa difference)(t) — so the
TROPICAL, FAGAN-BRADLEY (western sidereal), KRISHNAMURTI, RAMAN and YUKTESHWAR zodiacs come free from sweshim's
ayanāṁśa table, no chart recast. What differs between systems is everything SIGN-based:
  per system: each partner's Sun/Moon/Venus SIGN (order-free pair encoding), same-sign flags, element (fire/earth/
  air/water) match, mode (cardinal/fixed/mutable) match, the classical sign-distance (1..6) of the pair's Suns and
  Moons, the start-day Sun sign
One LightGBM member per zodiac system (no ages), one PLAIN + ALL-ZODIACS member; forward-chained OOF.
Writes AQ_OUT/zodiac_members.npz.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "web"))
from artamodel import auc   # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq4feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq4sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
SYSTEMS = ["TROPICAL", "FAGAN_BRADLEY", "KRISHNAMURTI", "RAMAN", "YUKTESHWAR"]


def aya_diff_tables(SW, years):
    """For each system, ayanāṁśa(Lahiri) − ayanāṁśa(system) per year (0 for tropical means: add Lahiri back)."""
    modes = {"FAGAN_BRADLEY": SW.SIDM_FAGAN_BRADLEY, "KRISHNAMURTI": SW.SIDM_KRISHNAMURTI, "RAMAN": SW.SIDM_RAMAN, "YUKTESHWAR": SW.SIDM_YUKTESHWAR}
    out = {}
    jd = {y: SW.julday(int(y), 7, 1, 0.0) for y in years}
    SW.set_sid_mode(SW.SIDM_LAHIRI); lah = {y: SW.get_ayanamsa_ut(jd[y]) for y in years}
    out["TROPICAL"] = {y: lah[y] for y in years}                      # sidereal + ayanāṁśa = tropical
    for name, mode in modes.items():
        SW.set_sid_mode(mode); out[name] = {y: lah[y] - SW.get_ayanamsa_ut(jd[y]) for y in years}
    SW.set_sid_mode(SW.SIDM_LAHIRI)
    return out


ELEM = np.arange(12) % 4; MODE = np.arange(12) % 3


def sign_feats(sunA, sunB, moonA, moonB, venA, venB, sunS):
    sA, sB = np.floor(sunA / 30) % 12, np.floor(sunB / 30) % 12; mA, mB = np.floor(moonA / 30) % 12, np.floor(moonB / 30) % 12
    vA, vB = np.floor(venA / 30) % 12, np.floor(venB / 30) % 12; sS = np.floor(sunS / 30) % 12
    def dist(a, b):
        d = np.abs(a - b); return np.fmin(d, 12 - d)
    take = lambda tab, idx: np.where(np.isfinite(idx), tab[np.nan_to_num(idx).astype(int) % 12], np.nan)
    return np.column_stack([np.fmax(sA, sB), np.fmin(sA, sB), dist(sA, sB), (sA == sB).astype(float),
                            (take(ELEM, sA) == take(ELEM, sB)).astype(float), (take(MODE, sA) == take(MODE, sB)).astype(float),
                            np.fmax(mA, mB), np.fmin(mA, mB), dist(mA, mB), (mA == mB).astype(float), (take(ELEM, mA) == take(ELEM, mB)).astype(float),
                            dist(sA, mB), dist(sB, mA),                              # sun-moon crossings, order-free as a set
                            np.fmax(vA, vB), np.fmin(vA, vB), dist(vA, vB), sS, dist(sA, sS) + dist(sB, sS)])


def main():
    import lightgbm as lgb
    import sweshim as SW
    SW.load(os.path.join(ROOT, "web", "ephem4.bin"), os.path.join(ROOT, "web", "tables.json"))
    Z = np.load(PH, allow_pickle=True); y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    bodies = list(Z["bodies"]); s1, s2 = list(Z["slots"]); ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    A, B, W = Z[f"theta_{s1}_train"], Z[f"theta_{s2}_train"], Z["theta_wed_train"]; Ae, Be, We = Z[f"theta_{s1}_test"], Z[f"theta_{s2}_test"], Z["theta_wed_test"]
    ysA = Z["yr_train"][:, 0].astype(int); ysB = Z["yr_train"][:, 1].astype(int)
    ysAe = pd.read_csv("/tmp/aq4/test.csv", dtype=str).dob_a.str[:4].astype(int).to_numpy(); ysBe = pd.read_csv("/tmp/aq4/test.csv", dtype=str).dob_b.str[:4].astype(int).to_numpy()
    yrs = sorted(set(ysA[ysA > 0]) | set(ysB[ysB > 0]) | set(ysAe) | set(ysBe) | set(ptr[:, pn.index("start_year")].astype(int)) | set(pte[:, pn.index("start_year")].astype(int)))
    D = aya_diff_tables(SW, yrs); log(f"ayanāṁśa tables for {len(yrs)} years, {len(SYSTEMS)} systems")
    i_sun, i_moon, i_ven = bodies.index("sun"), bodies.index("moon"), bodies.index("venus")
    sy_tr = ptr[:, pn.index("start_year")].astype(int); sy_te = pte[:, pn.index("start_year")].astype(int)
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
        log(f"  {name:<40} fwd-OOF {o:.4f}")
    allX_tr, allX_te = [], []
    for sysname in SYSTEMS:
        off_tr_a = np.array([D[sysname].get(v, np.nan) for v in ysA]); off_tr_b = np.array([D[sysname].get(v, np.nan) for v in ysB]); off_tr_s = np.array([D[sysname].get(v, np.nan) for v in sy_tr])
        off_te_a = np.array([D[sysname].get(v, np.nan) for v in ysAe]); off_te_b = np.array([D[sysname].get(v, np.nan) for v in ysBe]); off_te_s = np.array([D[sysname].get(v, np.nan) for v in sy_te])
        Xa = sign_feats((A[:, i_sun] + off_tr_a) % 360, (B[:, i_sun] + off_tr_b) % 360, (A[:, i_moon] + off_tr_a) % 360, (B[:, i_moon] + off_tr_b) % 360,
                        (A[:, i_ven] + off_tr_a) % 360, (B[:, i_ven] + off_tr_b) % 360, (W[:, i_sun] + off_tr_s) % 360)
        Xb = sign_feats((Ae[:, i_sun] + off_te_a) % 360, (Be[:, i_sun] + off_te_b) % 360, (Ae[:, i_moon] + off_te_a) % 360, (Be[:, i_moon] + off_te_b) % 360,
                        (Ae[:, i_ven] + off_te_a) % 360, (Be[:, i_ven] + off_te_b) % 360, (We[:, i_sun] + off_te_s) % 360)
        member(Xa, Xb, f"ZODIAC {sysname} signs (no ages)"); allX_tr.append(Xa); allX_te.append(Xb)
    member(np.column_stack([plain(ptr)] + allX_tr), np.column_stack([plain(pte)] + allX_te), "PLAIN + ALL ZODIAC SIGN SYSTEMS")
    np.savez_compressed(os.path.join(OUT, "zodiac_members.npz"), S_train=np.column_stack(members_tr), S_test=np.column_stack(members_te), names=np.array(names), meta=json.dumps(meta))
    log(f"wrote {OUT}/zodiac_members.npz")


if __name__ == "__main__":
    main()
