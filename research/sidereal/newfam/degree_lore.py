"""
degree_lore.py — the degree-level doctrines, the void-of-course of BaZi, and the Moon yogas.

GANDANTA: the three water-fire junctions (0/120/240 sidereal), +-3d20' — a Moon or lagna there is classically
catastrophic for marriage. MRTYU BHAGA: the per-sign death degree of the Moon (classical table). PUSHKARA:
the auspicious degree of each sign. ANARETIC 29th and zero degrees. AVASTHA: the five life-states of Sun and
Moon by sign parity and degree fifth. KONG WANG: from the day pillar's decade, the two VOID branches — a
spouse whose day branch falls in one's void is the classical "empty spouse palace". MOON YOGAS per partner:
Gajakesari, Sunapha, Anapha, Durudhara, Kemadruma, Adhi, and the kartari pair on the Moon.
"""
import numpy as np
import pandas as pd

MRTYU_MOON = [8, 25, 22, 22, 25, 2, 4, 23, 18, 20, 20, 10]     # Moon's mrityu bhaga degree per sidereal sign
PUSHKARA = [21, 14, 24, 7, 21, 14, 24, 7, 21, 14, 24, 7]       # pushkara bhaga per sign


def _jdn(col):
    out = np.full(len(col), np.nan)
    for i, v in enumerate(col.astype(str)):
        if len(v) >= 10 and v[:4].isdigit() and v[:4] != "0000" and v[5:7] != "00" and v[8:10] != "00":
            try:
                y, mo, d = int(v[:4]), int(v[5:7]), int(v[8:10])
                a = (14 - mo) // 12; yy = y + 4800 - a; mm = mo + 12 * a - 3
                out[i] = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
            except Exception:
                pass
    return out


def build(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ten = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
    ix = {b: bodies.index(b) for b in ten}
    cols, names = [], []
    for tag, C in (("h", A), ("w", B)):
        TH = np.column_stack([C[:, ix[b]] for b in ten]) % 360.0
        din = TH % 30.0
        anaretic = np.nansum(din >= 29.0, 1).astype(float); anaretic[~np.isfinite(TH).any(1)] = np.nan
        zero = np.nansum(din < 1.0, 1).astype(float); zero[~np.isfinite(TH).any(1)] = np.nan
        g = TH % 120.0
        gand = np.nansum((g >= 120 - 10.0/3) | (g < 10.0/3), 1).astype(float); gand[~np.isfinite(TH).any(1)] = np.nan
        moon = C[:, ix["moon"]] % 360.0
        msign = np.floor(moon / 30.0); mdeg = moon % 30.0
        mok = np.isfinite(moon)
        mrtyu = np.where(mok, (np.abs(mdeg - np.array(MRTYU_MOON)[np.nan_to_num(msign).astype(int) % 12]) < 1.0).astype(float), np.nan)
        push = np.where(mok, (np.abs(mdeg - np.array(PUSHKARA)[np.nan_to_num(msign).astype(int) % 12]) < 1.0).astype(float), np.nan)
        moon_gand = np.where(mok, (((moon % 120) >= 120 - 10.0/3) | ((moon % 120) < 10.0/3)).astype(float), np.nan)
        # avastha of the Moon: odd signs count up, even signs count down, in fifths of the sign
        fifth = np.floor(mdeg / 6.0)
        av = np.where(msign % 2 == 0, fifth, 4 - fifth)
        mrita = np.where(mok, (av == 4).astype(float), np.nan)
        # Moon yogas: whole-sign houses FROM THE MOON
        hs = lambda b: np.where(np.isfinite(C[:, ix[b]]) & mok,
                                (np.floor((C[:, ix[b]] % 360) / 30) - msign) % 12 + 1, np.nan)
        jup, ven, mer, mar, sat = hs("jupiter"), hs("venus"), hs("mercury"), hs("mars"), hs("saturn")
        gaja = np.where(np.isfinite(jup), np.isin(jup, [1, 4, 7, 10]).astype(float), np.nan)
        second = lambda x: np.isfinite(x) & (x == 2); twelfth = lambda x: np.isfinite(x) & (x == 12)
        any2 = second(ven) | second(mer) | second(mar) | second(sat) | second(jup)
        any12 = twelfth(ven) | twelfth(mer) | twelfth(mar) | twelfth(sat) | twelfth(jup)
        sun_ok = np.isfinite(ven) & np.isfinite(sat)
        sunapha = np.where(sun_ok, any2.astype(float), np.nan)
        anapha = np.where(sun_ok, any12.astype(float), np.nan)
        durudhara = np.where(sun_ok, (any2 & any12).astype(float), np.nan)
        kemadruma = np.where(sun_ok, (~any2 & ~any12).astype(float), np.nan)
        ben678 = np.where(sun_ok, (np.isin(jup, [6, 7, 8]) | np.isin(ven, [6, 7, 8]) | np.isin(mer, [6, 7, 8])).astype(float), np.nan)
        papak = np.where(sun_ok, ((mar == 2) | (sat == 2)).astype(float) * ((mar == 12) | (sat == 12)).astype(float), np.nan)
        for nm, v in (("anaretic_n", anaretic), ("zero_deg_n", zero), ("gandanta_n", gand),
                      ("moon_gandanta", moon_gand), ("moon_mrtyu", mrtyu), ("moon_pushkara", push),
                      ("moon_mrita_avastha", mrita), ("gajakesari", gaja), ("sunapha", sunapha),
                      ("anapha", anapha), ("durudhara", durudhara), ("kemadruma", kemadruma),
                      ("adhi_seed", ben678), ("papa_kartari_moon", papak)):
            cols.append(v); names.append(f"{tag}_{nm}")
    # KONG WANG — the void branches of each day pillar, and the spouse's branch against them
    ja, jb = _jdn(df.dob_a), _jdn(df.dob_b)
    sxa = np.where(np.isfinite(ja), (np.nan_to_num(ja) + 49) % 60, np.nan)
    sxb = np.where(np.isfinite(jb), (np.nan_to_num(jb) + 49) % 60, np.nan)
    bra = sxa % 12; brb = sxb % 12
    void_lo_a = (sxa - sxa % 10 + 10) % 12; void_hi_a = (sxa - sxa % 10 + 11) % 12
    void_lo_b = (sxb - sxb % 10 + 10) % 12; void_hi_b = (sxb - sxb % 10 + 11) % 12
    okd = np.isfinite(sxa) & np.isfinite(sxb)
    wife_in_husband_void = np.where(okd, ((brb == void_lo_a) | (brb == void_hi_a)).astype(float), np.nan)
    husband_in_wife_void = np.where(okd, ((bra == void_lo_b) | (bra == void_hi_b)).astype(float), np.nan)
    day_clash = np.where(okd, ((bra - brb) % 12 == 6).astype(float), np.nan)
    day_he = np.where(okd, ((bra + brb) % 12 == 1).astype(float), np.nan)
    cols += [wife_in_husband_void, husband_in_wife_void, day_clash, day_he]
    names += ["wife_in_husband_void", "husband_in_wife_void", "day_branch_clash", "day_branch_he"]
    return np.column_stack(cols).astype(np.float32), names
