"""
trad_houses.py — the angles and the twelve houses, and one partner's planets in the other's houses.

WHY THIS MODULE COULD NOT EXIST UNTIL NOW. A house cusp is a function of the birth TIME and the birth PLACE.
Neither was available for most of this project, so every module before this one either skipped house doctrine
or substituted a zodiacal proxy and said so. With the default hour set to 08:00 local mean time and
birthplace coordinates in hand for 76% of older partners and 66% of younger ones, Placidus cusps, the
Ascendant and the Midheaven are real quantities computed from swe.houses rather than stand-ins.

The time is still an assumption, and that assumption matters more here than anywhere else: the Ascendant
moves a full degree every four minutes, so a chart whose hour is wrong by two hours has an Ascendant wrong by
roughly a whole sign. Every block here is therefore emitted alongside HOUSE_OK, and where a birthplace is
unknown the values are a defined zero with the flag off rather than a fabricated horizon.

WHAT IS BUILT

    angles          Ascendant and Midheaven in circular form and as sign one-hots, for both partners and
                    for the Davison chart, plus the Asc-Asc and MC-MC separations between the partners
    placements      which of the twelve houses each of the eighteen bodies falls in, per partner
    angularity      angular / succedent / cadent, the classical strength classification, and a count of how
                    many bodies sit in each class
    rulers          the sign on each cusp and its traditional ruler, so "the lord of the seventh" — the
                    marriage significator of Ptolemy IV.5 and Dorotheus II, absent from this project until
                    now — is finally computable
    OVERLAY         partner A's planets in partner B's houses, and the reverse. In synastry this is the
                    house overlay, and it is the technique the whole enterprise has been unable to test:
                    where your planets land in someone else's chart is held to be what the relationship
                    does to each of you.

Usage: cd /Users/arash/Studio/artamatch/astro && ~/.artamatch-venv/bin/python trad_houses.py
"""

import numpy as np

TRADITION = "Houses and angles (Placidus cusps, the lord of the seventh, the synastry house overlay)"

# traditional rulers of the twelve signs, Aries first
SIGN_RULER = np.array([4, 3, 2, 1, 0, 2, 3, 4, 5, 6, 6, 5])   # Mars Venus Mercury Moon Sun ... indices into
RULER_BODY = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
O, Y, D = 0, 1, 5          # slot indices: older, younger, Davison


def _house_of(lon, cusps):
    """Which house (0-11) a longitude falls in, given 12 cusps in zodiacal order.

    Done by walking the cusps rather than dividing by 30: Placidus houses are unequal, which is the whole
    point of using them, so an arithmetic shortcut would silently produce equal houses instead.
    """
    n = lon.shape[-1]
    out = np.zeros(lon.shape, dtype=np.int64)
    for h in range(12):
        a = cusps[h]
        b = cusps[(h + 1) % 12]
        width = np.mod(b - a, 360.0)
        off = np.mod(lon - a, 360.0)
        inside = off < width
        out = np.where(inside, h, out)
    return out


def build(E):
    n = E.n
    out = {}
    okO, okY = E.HOUSE_OK[O], E.HOUSE_OK[Y]
    okD = E.HOUSE_OK[D]
    both = okO * okY

    def circ(v, ok):
        r = np.deg2rad(np.nan_to_num(v))
        return np.column_stack([np.cos(r) * ok, np.sin(r) * ok, ok])

    def signhot(v, ok):
        s = np.floor(np.mod(np.nan_to_num(v), 360.0) / 30.0).astype(int) % 12
        m = np.zeros((n, 12))
        m[np.arange(n), s] = ok
        return m

    ascO, ascY, ascD = E.ASC[O], E.ASC[Y], E.ASC[D]
    mcO, mcY = E.MC[O], E.MC[Y]
    dasc = np.where(both > 0, np.abs(E.wrap(np.nan_to_num(ascO) - np.nan_to_num(ascY))), 0.0)
    dmc = np.where(both > 0, np.abs(E.wrap(np.nan_to_num(mcO) - np.nan_to_num(mcY))), 0.0)
    out["hou: angles (Asc, MC) + partner separations"] = np.column_stack([
        circ(ascO, okO), circ(ascY, okY), circ(ascD, okD),
        circ(mcO, okO), circ(mcY, okY),
        dasc, dmc, both,
        # the classical hard aspects between the two Ascendants
        np.column_stack([E.orbkern(dasc, a, 6.0) * both for a in (0, 60, 90, 120, 180)]),
    ])
    out["hou: Asc + MC sign one-hots"] = np.column_stack([
        signhot(ascO, okO), signhot(ascY, okY), signhot(mcO, okO), signhot(mcY, okY),
        signhot(ascD, okD),
    ])

    # ── planets in their OWN houses ───────────────────────────────────────────────────────────────
    def placements(slot, ok):
        cus = E.CUSP[slot]
        cols = []
        ang = np.zeros((n, 3))
        for b in E.MODERN:
            h = _house_of(E.LON[slot, b], cus)
            m = np.zeros((n, 12))
            m[np.arange(n), h] = ok
            cols.append(m)
            cls = h % 3            # 0 angular, 1 succedent, 2 cadent
            for c in range(3):
                ang[:, c] += (cls == c) * ok
        return np.concatenate(cols + [ang], axis=1)

    out["hou: placements, older partner"] = placements(O, okO)
    out["hou: placements, younger partner"] = placements(Y, okY)
    out["hou: placements, Davison chart"] = placements(D, okD)

    # ── the lord of each house, and the seventh in particular ─────────────────────────────────────
    def lords(slot, ok):
        cus = E.CUSP[slot]
        cols = []
        for h in range(12):
            sign = np.floor(np.mod(np.nan_to_num(cus[h]), 360.0) / 30.0).astype(int) % 12
            rul = SIGN_RULER[sign]
            m = np.zeros((n, 7))
            m[np.arange(n), rul] = ok
            cols.append(m)
        # the lord of the SEVENTH — the marriage significator — and where it sits by house
        sign7 = np.floor(np.mod(np.nan_to_num(cus[6]), 360.0) / 30.0).astype(int) % 12
        r7 = SIGN_RULER[sign7]
        h7 = np.zeros((n, 12))
        for k, name in enumerate(RULER_BODY):
            sel = r7 == k
            if not sel.any():
                continue
            hh = _house_of(E.LON[slot, E.IDX[name]], cus)
            h7[np.arange(n)[sel], hh[sel]] = ok[sel]
        return np.concatenate(cols + [h7], axis=1)

    out["hou: house lords + lord of the 7th"] = np.concatenate(
        [lords(O, okO), lords(Y, okY)], axis=1)

    # ── THE SYNASTRY HOUSE OVERLAY ────────────────────────────────────────────────────────────────
    # Each partner's planets placed in the OTHER's houses. This is the technique the project could never
    # test, and it is asymmetric on purpose: your Venus in my seventh is not the same statement as my Venus
    # in your seventh, so both directions are emitted.
    def overlay(body_slot, house_slot, ok):
        cus = E.CUSP[house_slot]
        cols = []
        for b in E.MODERN:
            h = _house_of(E.LON[body_slot, b], cus)
            m = np.zeros((n, 12))
            m[np.arange(n), h] = ok
            cols.append(m)
        return np.concatenate(cols, axis=1)

    out["hou: overlay, older's planets in younger's houses"] = overlay(O, Y, both)
    out["hou: overlay, younger's planets in older's houses"] = overlay(Y, O, both)
    # a compact summary: how many of the partner's planets land in each of the twelve, both ways
    cnt = []
    for bs, hs in ((O, Y), (Y, O)):
        cus = E.CUSP[hs]
        c = np.zeros((n, 12))
        for b in E.MODERN:
            h = _house_of(E.LON[bs, b], cus)
            c[np.arange(n), h] += both
        cnt.append(c)
    out["hou: overlay counts per house, both directions"] = np.concatenate(cnt, axis=1)

    return {k: np.ascontiguousarray(np.nan_to_num(v), dtype=np.float64) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick
    E = load()
    print(f"  houses available: older {100*E.HOUSE_OK[0].mean():.1f}% · "
          f"younger {100*E.HOUSE_OK[1].mean():.1f}% · both {100*(E.HOUSE_OK[0]*E.HOUSE_OK[1]).mean():.1f}%")
    bl = build(E)
    bad = 0
    for k, v in bl.items():
        assert v.shape[0] == E.n and v.dtype == np.float64 and np.isfinite(v).all(), k
        if v.std(0).max() <= 0:
            print(f"  {k}: ALL CONSTANT"); bad += 1
        a, u = quick(E, v)
        print(f"  {k:<52} {v.shape[1]:>5} cols   acc {100*a:6.2f}%  AUC {u:.4f}")
    print("OK" if not bad else f"{bad} constant")
    sys.exit(1 if bad else 0)
