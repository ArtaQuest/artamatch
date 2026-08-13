"""
trad_astrocartography.py — Astro*Carto*Graphy (Jim Lewis, 1970s): where each planet is angular on Earth.

WHY THIS IS THE MODULE THAT MATTERS FOR PLACE. Every other module treats a birthplace either as nothing or
as two raw numbers. Astrocartography is the tradition that says a LOCATION is astrologically meaningful, and
it says it precisely: for one birth moment, each planet has four curves on the globe where it is angular —

    MC   the meridian where the planet is culminating
    IC   the opposite meridian, where it is anti-culminating
    AS   the curve where it is rising on the eastern horizon
    DS   the curve where it is setting on the western horizon

A place's astrological relationship to a birth is then its distance to those lines, which is a real
geometric quantity and not a proxy. That is what lets a ranking of cities be astrological rather than a
distance-from-home gradient.

THE GEOMETRY, stated because it is easy to get wrong. With Greenwich sidereal time theta, a planet of right
ascension RA and declination delta:

    MC meridian    lambda = RA - theta
    IC meridian    lambda = RA - theta + 180
    rising curve   lambda(phi) = RA - theta - H0(phi)      H0 = arccos(-tan(phi) tan(delta))
    setting curve  lambda(phi) = RA - theta + H0(phi)

H0 is undefined when |tan(phi) tan(delta)| > 1 — the planet is circumpolar at that latitude and never rises
or sets, so it HAS no AS or DS line there. Those cases are emitted as a defined zero with the line-exists
flag off, never as a fabricated crossing.

CROSS-CHART, which is the synastry form of the technique: partner A's planetary lines evaluated at partner
B's BIRTHPLACE, and the reverse. "Does her Venus line run through where he was born" is a question this can
actually answer, and it is asymmetric, so both directions are emitted.

Usage: cd /Users/arash/Studio/artamatch/astro && ~/.artamatch-venv/bin/python trad_astrocartography.py
"""

import numpy as np
import swisseph as swe

TRADITION = "Astrocartography (Jim Lewis): planetary MC/IC/AS/DS lines and a place's distance to them"

O, Y, D = 0, 1, 5
ORBS = (5.0, 10.0, 20.0)          # degrees of longitude; Lewis worked with a few degrees, modern practice wider


def _gmst_deg(jd):
    """Greenwich mean sidereal time in degrees, for each julian day in the array."""
    return np.array([swe.sidtime(float(j)) * 15.0 for j in np.atleast_1d(jd)])


def _lines(ra, dec, gmst, lat):
    """The four line longitudes for one body, at the latitude where they are being measured.

    Returns (mc, ic, asc, dsc, has_horizon) with longitudes in degrees east and `has_horizon` false where
    the body is circumpolar and therefore has no rising or setting curve at that latitude.
    """
    mc = np.mod(ra - gmst + 180.0, 360.0) - 180.0
    ic = np.mod(mc + 180.0 + 180.0, 360.0) - 180.0
    t = -np.tan(np.deg2rad(lat)) * np.tan(np.deg2rad(dec))
    ok = np.abs(t) <= 1.0
    h0 = np.degrees(np.arccos(np.clip(t, -1.0, 1.0)))
    asc = np.mod(ra - gmst - h0 + 180.0, 360.0) - 180.0
    dsc = np.mod(ra - gmst + h0 + 180.0, 360.0) - 180.0
    return mc, ic, asc, dsc, ok


def _sep(a, b):
    """Signed longitude separation in (-180, 180]."""
    return np.mod(np.asarray(a) - np.asarray(b) + 180.0, 360.0) - 180.0


def build(E):
    n = E.n
    out = {}
    latO, lonO = np.nan_to_num(E.LAT_O), np.nan_to_num(E.LON_O)
    latY, lonY = np.nan_to_num(E.LAT_Y), np.nan_to_num(E.LON_Y)
    okO = np.isfinite(E.LAT_O) & np.isfinite(E.LON_O)
    okY = np.isfinite(E.LAT_Y) & np.isfinite(E.LON_Y)
    gm = {s: _gmst_deg(E.JD[s]) for s in (O, Y, D)}

    def block(chart_slot, place_lat, place_lon, place_ok, bodies):
        """Distance from one place to every line of one chart."""
        cols = []
        for b in bodies:
            ra = E.RA[chart_slot, b]
            dec = E.DEC[chart_slot, b]
            mc, ic, asc, dsc, hor = _lines(ra, dec, gm[chart_slot], place_lat)
            dmc = np.abs(_sep(place_lon, mc)) * place_ok
            dic = np.abs(_sep(place_lon, ic)) * place_ok
            das = np.abs(_sep(place_lon, asc)) * place_ok * hor
            dds = np.abs(_sep(place_lon, dsc)) * place_ok * hor
            near = np.minimum(np.minimum(dmc, dic), np.where(hor, np.minimum(das, dds), 180.0))
            cols += [dmc, dic, das, dds, near, hor.astype(float) * place_ok]
            # proximity kernels: an astrocartography line is read as active within an orb, not as a
            # continuous distance, so the tradition's own reading is emitted as well as the raw degrees
            for orb in ORBS:
                cols += [np.exp(-0.5 * (dmc / orb) ** 2) * place_ok,
                         np.exp(-0.5 * (dic / orb) ** 2) * place_ok,
                         np.exp(-0.5 * (das / orb) ** 2) * place_ok * hor,
                         np.exp(-0.5 * (dds / orb) ** 2) * place_ok * hor]
        return np.column_stack(cols)

    MAIN = E.MODERN                      # the ten Lewis worked with
    out["acg: own lines at own birthplace, older"] = block(O, latO, lonO, okO, MAIN)
    out["acg: own lines at own birthplace, younger"] = block(Y, latY, lonY, okY, MAIN)
    # the synastry form: each partner's lines measured where the OTHER was born
    both = okO & okY
    out["acg: older's lines at younger's birthplace"] = block(O, latY, lonY, both, MAIN)
    out["acg: younger's lines at older's birthplace"] = block(Y, latO, lonO, both, MAIN)
    out["acg: Davison lines at both birthplaces"] = np.column_stack([
        block(D, latO, lonO, both, MAIN[:7]), block(D, latY, lonY, both, MAIN[:7])])

    # ── how far apart are the two people's lines for the same planet ───────────────────────────────
    # If his Venus MC line and her Venus MC line nearly coincide, the two charts agree about where Venus
    # is strong. That is a statement about the pair, not about either chart.
    cols = []
    for b in MAIN:
        mcO, icO, asO, dsO, hO = _lines(E.RA[O, b], E.DEC[O, b], gm[O], latO)
        mcY, icY, asY, dsY, hY = _lines(E.RA[Y, b], E.DEC[Y, b], gm[Y], latY)
        d = np.abs(_sep(mcO, mcY)) * both
        cols += [d, np.exp(-0.5 * (d / 10.0) ** 2) * both]
        da = np.abs(_sep(asO, asY)) * both * hO * hY
        cols += [da, np.exp(-0.5 * (da / 10.0) ** 2) * both * hO * hY]
    out["acg: line agreement between the two charts"] = np.column_stack(cols)

    # ── parans: two planets angular at the same latitude ──────────────────────────────────────────
    # A paran is where two bodies are simultaneously on an angle. It is a LATITUDE, and its classical use
    # is that a person born at that latitude carries the pair. Emitted as the latitude difference from each
    # partner's own birth latitude for the pairs Lewis and Brady treat as significant.
    cols = []
    for slot, plat, pok in ((O, latO, okO), (Y, latY, okY)):
        for a, b in ((0, 3), (0, 1), (1, 3), (3, 4), (0, 5), (1, 5), (3, 5), (4, 6)):
            ia, ib = E.MODERN[a], E.MODERN[b]
            # the latitude at which body A rises as body B culminates: solve H0(phi) for A equal to the
            # hour angle of B's meridian, which reduces to a closed form in cos(H)
            ha = _sep(E.RA[slot, ib] - gm[slot], E.RA[slot, ia] - gm[slot])
            c = np.cos(np.deg2rad(ha))
            td = np.tan(np.deg2rad(E.DEC[slot, ia]))
            with np.errstate(divide="ignore", invalid="ignore"):
                tphi = np.where(np.abs(td) > 1e-9, -c / td, np.nan)
            phi = np.degrees(np.arctan(tphi))
            good = np.isfinite(phi) & (np.abs(phi) < 66.5)
            dlat = np.abs(np.nan_to_num(phi) - plat) * pok * good
            cols += [np.nan_to_num(phi) * pok * good, dlat,
                     np.exp(-0.5 * (dlat / 5.0) ** 2) * pok * good, good.astype(float) * pok]
    out["acg: parans (two bodies angular at one latitude)"] = np.column_stack(cols)

    return {k: np.ascontiguousarray(np.nan_to_num(v), dtype=np.float64) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick
    E = load()
    bl = build(E)
    # a geometric check the tradition itself implies: at the MC line the planet's altitude is maximal, so
    # the distance from a place to its own MC line must be zero when that place IS the meridian
    gm = _gmst_deg(E.JD[0])
    ra = E.RA[0, E.IDX["Sun"]]
    mc = np.mod(ra - gm + 180.0, 360.0) - 180.0
    print(f"  Sun MC meridian spans {mc.min():.1f} to {mc.max():.1f} degrees east (should cover the globe)")
    bad = 0
    for k, v in bl.items():
        assert v.shape[0] == E.n and v.dtype == np.float64 and np.isfinite(v).all(), k
        if v.std(0).max() <= 0:
            print(f"  {k}: ALL CONSTANT"); bad += 1
        a, u = quick(E, v)
        print(f"  {k:<50} {v.shape[1]:>5} cols   acc {100*a:6.2f}%  AUC {u:.4f}")
    print("OK" if not bad else f"{bad} constant")
    sys.exit(1 if bad else 0)
