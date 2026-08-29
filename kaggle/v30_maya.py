"""v30_maya.py — the Maya almanac in full, as pair statements.

The bank had the Tzolkin day sign and tone and three of the four Dreamspell oracle relations. The Maya
kept several interlocking counts at once, and a reading uses all of them, so this adds the rest:

  TZOLKIN      the 260-day sacred round: day sign (20), tone (13), and the kin itself (260)
  TRECENA      the thirteen-day run a date falls in, named for the sign that opens it. A Maya day is
               read through its trecena as much as through itself.
  HAAB         the 365-day solar year: eighteen twenty-day months, plus Wayeb, the five nameless days
  YEAR BEARER  only four day signs can begin a Haab year, and the bearer colours the whole year
  CALENDAR ROUND  the 52-year meshing of Tzolkin and Haab — the Maya century
  LORDS OF THE NIGHT  the nine-day cycle (G1-G9) run alongside both calendars
  LONG COUNT   baktun, katun and tun — the linear count, for the era a birth falls in
  819-DAY      the 819-day station, with its colour and world-direction
  DREAMSPELL   the complete oracle: guide, antipode, analog and occult — the guide was missing, and it
               is the one a modern reading leads with; plus the colour family, wavespell and castle
  VENUS ROUND  the 584-day Venus cycle the Dresden Codex tabulates, and its phase — Maya astronomy's
               most watched body, and the one they timed war and marriage by

Correlation: GMT 584283 throughout, and the Tzolkin anchor is the same one the rest of the bank uses,
so a statement here means the same thing as one in v21 or v23.

Every statement uses BOTH dates. build(df, Z, split, exclude, min_support) -> (X, names).
"""
import numpy as np
import pandas as pd

TZ = ["Imix", "Ik", "Akbal", "Kan", "Chicchan", "Cimi", "Manik", "Lamat", "Muluc", "Oc",
      "Chuen", "Eb", "Ben", "Ix", "Men", "Cib", "Caban", "Etznab", "Cauac", "Ahau"]
HAAB = ["Pop", "Wo", "Sip", "Sotz", "Sek", "Xul", "Yaxkin", "Mol", "Chen", "Yax", "Sak", "Keh",
        "Mak", "Kankin", "Muwan", "Pax", "Kayab", "Kumku", "Wayeb"]
COLOR = ["Red", "White", "Blue", "Yellow"]
DIRECTION = ["East", "North", "West", "South"]
GMT = 584283


def _jdn(y, m, d):
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _cats(vals, prefix, names, cols, ms):
    vals = np.asarray(vals)
    for v in pd.unique(vals):
        c = (vals == v).astype(np.float32)
        if c.sum() >= ms:
            cols.append(c); names.append(f"{prefix}={v}")


def _flag(cols, names, arr, nm, ms):
    c = np.nan_to_num(np.asarray(arr, dtype=float)).astype(np.float32)
    if ms <= c.sum() <= len(c) - ms:
        cols.append(c); names.append(nm)


def build(df, Z=None, split=None, exclude=frozenset(), min_support=40):
    n = len(df); ms = min_support
    ya = pd.to_numeric(df.dob_a.str[:4]).to_numpy(int); ma = pd.to_numeric(df.dob_a.str[5:7]).to_numpy(int)
    da = pd.to_numeric(df.dob_a.str[8:10]).to_numpy(int)
    yb = pd.to_numeric(df.dob_b.str[:4]).to_numpy(int); mb = pd.to_numeric(df.dob_b.str[5:7]).to_numpy(int)
    db = pd.to_numeric(df.dob_b.str[8:10]).to_numpy(int)
    ja = np.array([_jdn(y, m, d) for y, m, d in zip(ya, ma, da)])
    jb = np.array([_jdn(y, m, d) for y, m, d in zip(yb, mb, db)])
    cols, names = [], []

    ka, kb = (ja + 159) % 260, (jb + 159) % 260          # kin index, same anchor as the rest of the bank
    sa, sb = ka % 20, kb % 20                             # day sign
    ta, tb = ka % 13, kb % 13                             # tone (0-based)
    la, lb = ja - GMT, jb - GMT                           # Long Count day

    # ---------- TZOLKIN ----------
    _cats([f"{TZ[i]}x{TZ[j]}" for i, j in zip(sa, sb)], "maya_daysignpair", names, cols, ms)
    _cats([f"{i+1}x{j+1}" for i, j in zip(ta, tb)], "maya_tonepair", names, cols, ms)
    _flag(cols, names, sa == sb, "maya_same_daysign", ms)
    _flag(cols, names, ta == tb, "maya_same_tone", ms)
    _flag(cols, names, ka == kb, "maya_same_kin", ms)
    _cats(np.minimum((ta - tb) % 13, (tb - ta) % 13), "maya_tone_distance", names, cols, ms)

    # ---------- TRECENA ----------
    tra = (ka - (ka % 13)) % 20; trb = (kb - (kb % 13)) % 20
    _cats([f"{TZ[i]}x{TZ[j]}" for i, j in zip(tra, trb)], "maya_trecenapair", names, cols, ms)
    _flag(cols, names, tra == trb, "maya_same_trecena", ms)

    # ---------- HAAB and the YEAR BEARER ----------
    ha, hb = (la + 348) % 365, (lb + 348) % 365
    _cats([f"{HAAB[min(i // 20, 18)]}x{HAAB[min(j // 20, 18)]}" for i, j in zip(ha, hb)],
          "maya_haabmonthpair", names, cols, ms)
    _flag(cols, names, (ha // 20) == (hb // 20), "maya_same_haab_month", ms)
    _flag(cols, names, ha == hb, "maya_same_haab_day", ms)
    _flag(cols, names, (ha >= 360) | (hb >= 360), "maya_wayeb_either",  ms)   # the five nameless days
    _flag(cols, names, (ha >= 360) & (hb >= 360), "maya_wayeb_both", ms)
    yba = (ka - ha) % 260 % 20; ybb = (kb - hb) % 260 % 20
    _cats([f"{TZ[i]}x{TZ[j]}" for i, j in zip(yba, ybb)], "maya_yearbearerpair", names, cols, ms)
    _flag(cols, names, yba == ybb, "maya_same_yearbearer", ms)

    # ---------- CALENDAR ROUND (52 years) ----------
    cra, crb = la % 18980, lb % 18980
    _flag(cols, names, cra == crb, "maya_same_calendar_round_position", ms)
    _cats(np.minimum(np.abs(cra - crb), 18980 - np.abs(cra - crb)) // 1898,
          "maya_calendar_round_gap_tenths", names, cols, ms)

    # ---------- LORDS OF THE NIGHT ----------
    ga, gb = la % 9, lb % 9
    _cats([f"G{i+1}xG{j+1}" for i, j in zip(ga, gb)], "maya_lordnightpair", names, cols, ms)
    _flag(cols, names, ga == gb, "maya_same_lord_of_night", ms)

    # ---------- LONG COUNT ----------
    for unit, size in (("tun", 360), ("katun", 7200), ("baktun", 144000)):
        ua, ub = la // size, lb // size
        _flag(cols, names, ua == ub, f"maya_same_{unit}", ms)
        if unit != "tun":
            _cats([f"{i}x{j}" for i, j in zip(ua, ub)], f"maya_{unit}pair", names, cols, ms)

    # ---------- THE 819-DAY STATION ----------
    ea, eb = la % 819, lb % 819
    _flag(cols, names, (ea // 205) == (eb // 205), "maya_same_819_quarter", ms)
    _cats([f"{COLOR[(i//205)%4]}{DIRECTION[(i//205)%4]}x{COLOR[(j//205)%4]}{DIRECTION[(j//205)%4]}"
           for i, j in zip(ea, eb)], "maya_819_stationpair", names, cols, ms)

    # ---------- DREAMSPELL: the complete oracle ----------
    _flag(cols, names, ((sa + 10) % 20) == sb, "maya_oracle_antipode", ms)
    _flag(cols, names, (19 - sa) == sb, "maya_oracle_analog", ms)
    _flag(cols, names, (ka + kb) == 259, "maya_oracle_occult", ms)
    # the GUIDE — the relation a modern Dreamspell reading leads with, and the one the bank lacked
    gsa = (sa + 4 * (ta % 5)) % 20; gsb = (sb + 4 * (tb % 5)) % 20
    _flag(cols, names, gsa == sb, "maya_his_guide_is_her_daysign", ms)
    _flag(cols, names, gsb == sa, "maya_her_guide_is_his_daysign", ms)
    _flag(cols, names, gsa == gsb, "maya_same_guide", ms)
    ca_, cb_ = sa % 4, sb % 4
    _cats([f"{COLOR[i]}x{COLOR[j]}" for i, j in zip(ca_, cb_)], "maya_colorpair", names, cols, ms)
    _flag(cols, names, ca_ == cb_, "maya_same_color_family", ms)
    wa, wb = ka // 13, kb // 13                              # wavespell (20 of them)
    _flag(cols, names, wa == wb, "maya_same_wavespell", ms)
    _cats([f"{i}x{j}" for i, j in zip(ka // 52, kb // 52)], "maya_castlepair", names, cols, ms)
    _flag(cols, names, (ka // 52) == (kb // 52), "maya_same_castle", ms)

    # ---------- VENUS ROUND (the Dresden Codex table) ----------
    va, vb = la % 584, lb % 584
    _flag(cols, names, (va // 73) == (vb // 73), "maya_same_venus_eighth", ms)
    # the four stations the codex names: morning star, superior conjunction, evening star, inferior
    STA = ["MorningStar", "Superior", "EveningStar", "Inferior"]
    pa = np.digitize(va, [236, 326, 576]); pb = np.digitize(vb, [236, 326, 576])
    _cats([f"{STA[min(i,3)]}x{STA[min(j,3)]}" for i, j in zip(pa, pb)], "maya_venus_stationpair",
          names, cols, ms)
    _flag(cols, names, pa == pb, "maya_same_venus_station", ms)

    keep = [i for i, nm in enumerate(names) if nm not in exclude]
    X = np.column_stack([cols[i] for i in keep]).astype(np.float32) if keep else np.zeros((n, 0), np.float32)
    return X, [names[i] for i in keep]
