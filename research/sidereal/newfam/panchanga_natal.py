"""
panchanga_natal.py — the five limbs of the almanac AT EACH BIRTH, and their marriage compatibilities.

Every electional module read the WEDDING's panchanga; with no wedding date in this edition, the classical
object is each partner's JANMA (birth) panchanga: vara (weekday), tithi (Moon-Sun phase), nakshatra (already
elsewhere), yoga (Moon+Sun), karana (half-tithi). Tithi and yoga need both luminaries -> day precision; vara
needs only the date. Directional where the doctrine is directional.
"""
import numpy as np
import pandas as pd

FRIEND = {(0,1),(1,0),(0,4),(4,0),(0,2),(2,0),(1,3),(3,1),(2,4),(4,2),(3,5),(5,3),(5,6),(6,5),(3,6),(6,3)}
# vara lords by weekday(): Mon=Moon(1) Tue=Mars(2) Wed=Mercury(3) Thu=Jupiter(4) Fri=Venus(5) Sat=Saturn(6) Sun=Sun(0)
VARA_LORD = [1, 2, 3, 4, 5, 6, 0]


def _wd(col):
    out = np.full(len(col), np.nan)
    for i, v in enumerate(col.astype(str)):
        if len(v) >= 10 and v[:4].isdigit() and v[:4] != "0000" and v[5:7] not in ("00",) and v[8:10] not in ("00",):
            try:
                y, mo, d = int(v[:4]), int(v[5:7]), int(v[8:10])
                a = (14 - mo) // 12; yy = y + 4800 - a; mm = mo + 12 * a - 3
                j = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
                out[i] = j % 7          # 0 = Monday for this JDN convention offset? fixed below
            except Exception:
                pass
    return out


def build(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in ("sun", "moon", "true_node")}
    cols, names = [], []
    per = {}
    for tag, C, dob in (("h", A, df.dob_a), ("w", B, df.dob_b)):
        sun, moon, node = C[:, ix["sun"]], C[:, ix["moon"]], C[:, ix["true_node"]]
        el = (moon - sun) % 360.0
        lum_ok = np.isfinite(moon) & np.isfinite(sun)
        NAg = lambda v: np.where(lum_ok, v, np.nan)      # a flag from an unknown tithi is NaN, never a quiet 0:
        tithi = NAg(np.floor(el / 12.0) + 1)             # np.nan == 3 is False, and False casts to 0.0 — the
        karana = NAg(np.floor(el / 6.0) % 60)            # tradition would then be ASSERTING "no dosha" about a
        yoga = NAg(np.floor(((moon + sun) % 360.0) / (360.0 / 27.0)))   # couple it cannot read
        paksha = NAg((tithi > 15).astype(float))
        tclass = NAg((tithi - 1) % 5)
        rikta = NAg((tclass == 3).astype(float))
        # eclipse-born: luminaries' syzygy near the nodal axis
        near_node = np.fmin(np.abs((sun - node + 180) % 360 - 180), np.abs((sun - node) % 360 - 180) * 0 + 999)
        node_arc = np.abs((sun - node + 180) % 360 - 180)
        node_axis = np.fmin(node_arc, 180 - node_arc)
        newfull = np.fmin(el % 360, 360 - el % 360); newfull = np.fmin(newfull, np.abs(180 - el))
        eclipse_born = np.where(lum_ok & np.isfinite(node), ((node_axis < 15) & (newfull < 24)).astype(float), np.nan)
        vr = _wd(dob)
        vara_lord = np.where(np.isfinite(vr), np.array(VARA_LORD * 1)[np.nan_to_num(vr).astype(int) % 7], np.nan)
        per[tag] = dict(tithi=tithi, karana=karana, yoga=yoga, paksha=paksha, tclass=tclass, lord=vara_lord)
        for nm, v in (("tithi", tithi), ("karana", karana), ("yoga", yoga), ("paksha", paksha),
                      ("tithi_class", tclass), ("rikta", rikta), ("eclipse_born", eclipse_born),
                      ("vara_lord", vara_lord)):
            cols.append(np.where(np.isfinite(v), v, np.nan)); names.append(f"{tag}_{nm}")
    h, w = per["h"], per["w"]
    both = lambda x, y: np.where(np.isfinite(x) & np.isfinite(y), 1.0, np.nan)
    # DIRECTIONAL tithi kuta: counted bride-to-groom in the southern reckoning
    tk = np.where(np.isfinite(h["tithi"] + w["tithi"]), ((h["tithi"] - w["tithi"]) % 30), np.nan)
    cols += [tk, np.where(np.isfinite(tk), np.isin(tk, [0, 6, 12, 18, 24]).astype(float), np.nan)]
    names += ["tithi_count_b2g", "tithi_kuta_bad"]
    cols += [np.where(np.isfinite(h["paksha"] + w["paksha"]), (h["paksha"] == w["paksha"]).astype(float), np.nan)]
    names += ["same_paksha"]
    cols += [np.where(np.isfinite(h["yoga"] + w["yoga"]), (h["yoga"] == w["yoga"]).astype(float), np.nan)]
    names += ["same_yoga"]
    lh, lw = h["lord"], w["lord"]
    okl = np.isfinite(lh) & np.isfinite(lw)
    f_hw = np.array([1.0 if (int(x), int(y)) in FRIEND else 0.0 if np.isfinite(x) and np.isfinite(y) else np.nan
                     for x, y in zip(np.nan_to_num(lh, nan=-1), np.nan_to_num(lw, nan=-1))])
    cols += [np.where(okl, f_hw, np.nan), np.where(okl, (lh == lw).astype(float), np.nan)]
    names += ["vara_lords_friends", "vara_lords_same"]
    return np.column_stack(cols).astype(np.float32), names
