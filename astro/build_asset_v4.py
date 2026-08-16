"""
build_asset_v4.py — ship the ephemeris so the browser can run the REAL pipeline, not a copy of it.

WHY THIS EXISTS. Pyodide has no pyswisseph (a C extension nobody has built for WASM), so a browser cannot
compute a planetary position. The previous answer was `web/features.py`: a hand-written reimplementation of
ten traditions. That reimplementation is why the shipped model scored 0.6815 where the laptop stack scored
0.7311 — eight of the eighteen traditions the stack actually chose were never ported, including the five
strongest blocks in the whole project.

So this asset is built for a different plan: carry enough that a pure-numpy `swisseph` shim
(`web/sweshim.py`) can answer everything `core.py` and the eighteen `trad_*.py` modules ask, and let the
BROWSER RUN THOSE FILES UNCHANGED. Parity then stops being something to test and starts being structural —
there is only one implementation of every feature.

WHAT IS STORED. 1698-01-01 to 2032-12-31 for twenty-six bodies — core.py's eighteen in its exact order, then
the eight Uranian hypotheticals that trad_uranian resolves by name — FIVE quantities each: ecliptic
longitude, ecliptic latitude, distance, longitude speed, heliocentric longitude. Plus all twenty-one
ayanamsas core.py knows.

WHAT IS DELIBERATELY *NOT* STORED, because computing it beats storing it. Right ascension, declination and
sidereal time were all in the first cut of this asset, and all three came back WORSE than the arithmetic
that replaces them:

  * RA and declination are exact functions of the ecliptic position and the obliquity. Interpolating them as
    independent series (no stored derivative, so only Catmull-Rom) was good to 0.06 deg for the Sun and
    0.51 deg for the Moon. Rotating the already-interpolated longitude and latitude by the TRUE obliquity
    instead reproduces swisseph's own equatorial output to 0.000021 deg — a 2,400x improvement that also
    removes two sevenths of the file. Measured both ways before choosing.
  * Sidereal time is a polynomial, so it is evaluated. The one trap: swe.sidtime returns APPARENT sidereal
    time, so the equation of the equinoxes has to be added or every Ascendant is out by up to 16 arcsec.

The sampling grid is one row per day at 10:00 UT. That is a sampling PHASE, not a birth-hour convention:
the shim interpolates to any instant, so core.py's DEFAULT_HOUR (08:00 local mean time at the birthplace)
costs nothing and can change without rebuilding this file.

PER-BODY STRIDE, AND WHY IT IS FREE. Storing 231 years x 26 bodies daily would be 31 MB. But a body only
needs to be sampled finely enough that cubic Hermite interpolation between samples — using the stored
longitude AND the stored speed at each node, which is what makes it Hermite rather than a spline — lands
inside the 0.0055 degree quantisation step the storage already imposes. Measured, per body, in
`_verify_strides` below: the Moon needs every day, Mercury and the nodes every second day, and everything
from Venus outward is fine every eighth. That is 6.4 MB for 231 years and 26 bodies, where the old asset
spent 10.9 MB on 131 years and 18. The builder REFUSES TO WRITE if any body's measured interpolation error
exceeds the quantisation step, so the stride table can never silently degrade a body.

Interpolation is on the UNWRAPPED angle. Hermite across a 360->0 crossing on raw values is off by up to 130
degrees; that was measured too, and it is the one trap in this file.

THE SMALL TABLES. Four things the modules ask swisseph for that are not a planetary position, each of them
exactly tabulable rather than approximated: delta-T per year, Spica's precessed equatorial position per year
(the only fixed star any module resolves through swisseph — every other star comes from the modules' own
hardcoded J2000 catalogues), and every global solar and lunar eclipse in the span, which is what turns
swe.sol_eclipse_when_glob into a table lookup that returns the same JD swisseph would have searched for.

Usage: cd astro && ~/.artamatch-venv/bin/python build_asset_v4.py
"""
import json
import os
import struct

import numpy as np
import swisseph as swe
from astropy.time import Time

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web")
EPHE = os.path.expanduser("~/.sweph/ephe")
swe.set_ephe_path(EPHE)

FLG = swe.FLG_SWIEPH | swe.FLG_SPEED
FLG_EQ = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL
FLG_HC = swe.FLG_SWIEPH | swe.FLG_HELCTR

# THE SPAN CARRIES A MARGIN, and it is not decorative. Couples are accepted with birth years 1800-2026, but
# several modules search OUTWARD from a birth date: trad_indigenous_americas walks back to the new moon before
# it, which for a birth on 1800-01-03 wants the Moon in December 1799. That was measured, not guessed — a
# probe that pinned couples at both extremes of the accepted range found the Moon requested 65 days early
# (29 times) and delta-T 3 times, while every other body stayed inside. It never showed up in training
# because training uses real Swiss Ephemeris, which has no such edge; it appeared the moment the same code
# ran on the shipped asset, which is what a browser runs. Two years either side covers a synodic lookback
# with room to spare, and costs under 2% of the file.
Y0, Y1 = 1698, 2032
YEAR_ACCEPTED = (1700, 2026)     # what core.py will actually accept; the span above brackets it
QUANT = 360.0 / 65535.0          # 0.005493 deg — the storage step for an angle, and so the error budget

# SPEED IS SCALED PER BODY, and that is not a micro-optimisation. The first version quantised every body's
# longitude speed to int16 over one shared +-16 deg/day range, because the Moon needs 15. That gives a step
# of 0.000488 deg/day — which is 2.8% of Pluto's typical speed and 5.8% of Poseidon's. The SIGN of this
# quantity is retrograde status, a first-class feature in every tradition here, and measured against real
# swisseph the shared scale got it WRONG for 1 in 400 Pluto samples and 4 in 400 for Poseidon. Each body now
# carries its own min and max, stored in the header, so the step is a fixed fraction of that body's own range
# and the sign can never be lost to rounding.

# core.py's eighteen, in core.py's order (E.IDX depends on it), then the Uranian hypotheticals.
BODIES = [
    ("Sun", swe.SUN), ("Moon", swe.MOON), ("Mercury", swe.MERCURY), ("Venus", swe.VENUS),
    ("Mars", swe.MARS), ("Jupiter", swe.JUPITER), ("Saturn", swe.SATURN), ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE), ("Pluto", swe.PLUTO), ("TrueNode", swe.TRUE_NODE),
    ("MeanNode", swe.MEAN_NODE), ("Lilith", swe.MEAN_APOG), ("Chiron", swe.CHIRON),
    ("Ceres", swe.CERES), ("Pallas", swe.PALLAS), ("Juno", swe.JUNO), ("Vesta", swe.VESTA),
    ("Cupido", swe.CUPIDO), ("Hades", swe.HADES), ("Zeus", swe.ZEUS), ("Kronos", swe.KRONOS),
    ("Apollon", swe.APOLLON), ("Admetos", swe.ADMETOS), ("Vulkanus", swe.VULKANUS),
    ("Poseidon", swe.POSEIDON),
]
NODELIKE = {swe.TRUE_NODE, swe.MEAN_NODE, swe.MEAN_APOG}     # heliocentric is meaningless for these

# Sampling stride in days. Set from the measurement in _verify_strides, not by taste.
# Venus is at 4 rather than 8 because the asset gate said so: at 8 its ecliptic LATITUDE reconstructed to
# 0.0098 deg against a 0.0055 budget and its distance to 2.7e-4 relative against 1e-4. Longitude was fine at
# 8 — which is exactly why a gate that measures longitude alone is not a gate.
STRIDE = {"Moon": 1, "Mercury": 2, "TrueNode": 2, "MeanNode": 2, "Venus": 4}
STRIDE_DEFAULT = 8

# PER-BODY SPAN, because one body needs nine centuries and the rest need two. trad_african builds its
# heliacal-rising criterion on a fixed precession ladder, `_EPOCHS = arange(1180, 2081, 20)`, and asks for
# the Sun's apparent place on every day of each of those 46 years — 137,258 calls outside 1800-2030. That was
# measured by tracing every calc_ut the nineteen modules make: the Sun spans 1180-2081 and EVERY OTHER BODY
# stays inside 1808-1991, the couples' own dates. So the Sun gets the long span and nobody else pays for it —
# at stride 8 those nine extra centuries cost 411 kB. Guessing a uniform span would have cost 30 MB or
# silently dropped the two best blocks in the project.
SPAN = {"Sun": (1180, 2083)}
SPAN_DEFAULT = (Y0, Y1)

AYANAMSAS = [
    ("Fagan-Bradley", swe.SIDM_FAGAN_BRADLEY), ("Lahiri", swe.SIDM_LAHIRI),
    ("DeLuce", swe.SIDM_DELUCE), ("Raman", swe.SIDM_RAMAN), ("Ushashashi", swe.SIDM_USHASHASHI),
    ("Krishnamurti", swe.SIDM_KRISHNAMURTI), ("Djwhal Khul", swe.SIDM_DJWHAL_KHUL),
    ("Yukteshwar", swe.SIDM_YUKTESHWAR), ("JN Bhasin", swe.SIDM_JN_BHASIN),
    ("Babylonian/Kugler 1", swe.SIDM_BABYL_KUGLER1), ("Aldebaran 15 Tau", swe.SIDM_ALDEBARAN_15TAU),
    ("Hipparchos", swe.SIDM_HIPPARCHOS), ("Sassanian", swe.SIDM_SASSANIAN),
    ("Galactic Centre 0 Sag", swe.SIDM_GALCENT_0SAG), ("J2000", swe.SIDM_J2000),
    ("B1950", swe.SIDM_B1950), ("Suryasiddhanta", swe.SIDM_SURYASIDDHANTA),
    ("Aryabhata", swe.SIDM_ARYABHATA), ("True Citra", swe.SIDM_TRUE_CITRA),
    ("True Revati", swe.SIDM_TRUE_REVATI), ("True Pushya", swe.SIDM_TRUE_PUSHYA),
]
AYA_STRIDE = 64      # precession moves 50"/yr, so 64 days changes it by 0.0024 deg — under QUANT


def wrap(d):
    return (d + 180.0) % 360.0 - 180.0


def hermite(p0, m0, p1, m1, t, h):
    """Cubic Hermite between two samples. p1 must already be unwrapped onto p0's branch."""
    h00 = 2 * t ** 3 - 3 * t ** 2 + 1
    h10 = t ** 3 - 2 * t ** 2 + t
    h01 = -2 * t ** 3 + 3 * t ** 2
    h11 = t ** 3 - t ** 2
    return h00 * p0 + h10 * m0 * h + h01 * p1 + h11 * m1 * h


def _verify_strides():
    """Measure each body's Hermite error at its assigned stride, against swisseph itself.

    This is the gate that lets STRIDE be aggressive. A body whose interpolation error exceeds the storage
    quantisation costs nothing to sample finer, and a body that fits under it costs nothing to sample
    coarser — so the only thing that matters is knowing which is which, per body, from measurement.
    """
    rng = np.random.default_rng(11)
    print("\nstride verification — cubic Hermite error vs swisseph, budget is the quantisation step "
          f"{QUANT:.6f} deg")
    worst = {}
    bad = []
    for nm, code in BODIES:
        st = STRIDE.get(nm, STRIDE_DEFAULT)
        y0, y1 = SPAN.get(nm, SPAN_DEFAULT)
        bjd0 = Time(f"{y0}-01-01 10:00").jd
        bdays = int(round(Time(f"{y1}-12-31 10:00").jd - bjd0)) + 1
        err = 0.0
        for _ in range(40):
            d = int(rng.integers(0, bdays - st - 1))
            base = bjd0 + (d // st) * st
            for t in (0.13, 0.5, 0.86):
                a = swe.calc_ut(base, code, FLG)[0]
                b = swe.calc_ut(base + st, code, FLG)[0]
                got = hermite(a[0], a[3], a[0] + wrap(b[0] - a[0]), b[3], t, st)
                want = swe.calc_ut(base + t * st, code, FLG)[0][0]
                err = max(err, abs(wrap(got - want)))
        worst[nm] = err
        flag = "" if err <= QUANT else "   <-- OVER BUDGET"
        if err > QUANT:
            bad.append((nm, st, err))
        print(f"  {nm:<10} stride {st:>2}d   max |err| {err:.6f} deg{flag}")
    if bad:
        raise SystemExit("\nREFUSING TO WRITE — these bodies need a finer stride:\n" +
                         "\n".join(f"  {n} at {s}d is {e:.6f} deg, budget {QUANT:.6f}" for n, s, e in bad))
    return worst


SPICA_STRIDE = 32     # days. Precession is linear, but swisseph's apparent place also carries annual
                      # aberration and nutation; a yearly table aliased those into a 23 arcsec error, so
                      # the cadence is set to resolve them instead.


def _tables(jd0, jd1):
    """delta-T per year, Spica per 32 days, and every eclipse in the span — the non-positional asks."""
    yrs = list(range(Y0 - 3, Y1 + 4))       # delta-T with margin: it was asked for outside the span too
    dt = [float(swe.deltat(Time(f"{y}-01-01 00:00").jd)) for y in yrs]
    nsp = int((jd1 - jd0) // SPICA_STRIDE) + 3
    spica = []
    for i in range(nsp):
        xx = swe.fixstar2_ut("Spica", float(jd0 + i * SPICA_STRIDE), FLG_EQ)[0]
        spica.append([round(float(xx[0]), 6), round(float(xx[1]), 6)])
    sol, lun = [], []
    t = jd0 - 800.0
    while t < jd1 + 800.0:
        r, tret = swe.sol_eclipse_when_glob(t, swe.FLG_SWIEPH, 0, False)
        if tret[0] <= t:
            break
        sol.append([float(tret[0]), int(r)])
        t = tret[0] + 2.0
    t = jd0 - 800.0
    while t < jd1 + 800.0:
        r, tret = swe.lun_eclipse_when(t, swe.FLG_SWIEPH, 0, False)
        if tret[0] <= t:
            break
        lun.append([float(tret[0]), int(r)])
        t = tret[0] + 2.0
    print(f"\ntables: delta-T for {len(yrs)} years · Spica at {len(spica):,} x {SPICA_STRIDE}d · "
          f"{len(sol)} solar and {len(lun)} lunar eclipses")
    return {"yearFrom": Y0, "years": yrs, "deltat": dt,
            "spicaJd0": jd0, "spicaStride": SPICA_STRIDE, "spica": spica,
            "solar": sol, "lunar": lun}


def main():
    jd0 = Time(f"{Y0}-01-01 10:00").jd
    jd1 = Time(f"{Y1}-12-31 10:00").jd
    ndays = int(round(jd1 - jd0)) + 1
    print(f"{ndays:,} days · {Y0}-01-01 to {Y1}-12-31 at 10:00 UT · {len(BODIES)} bodies · "
          f"{len(AYANAMSAS)} ayanamsas")

    _verify_strides()

    per = {}
    total_samples = 0
    for nm, _ in BODIES:
        st = STRIDE.get(nm, STRIDE_DEFAULT)
        y0, y1 = SPAN.get(nm, SPAN_DEFAULT)
        bjd0 = Time(f"{y0}-01-01 10:00").jd
        bdays = int(round(Time(f"{y1}-12-31 10:00").jd - bjd0)) + 1
        # +2 nodes of headroom so the last day is always bracketed for interpolation
        ns = (bdays - 1) // st + 3
        per[nm] = (st, ns, bjd0, y0, y1)
        total_samples += ns
    print(f"\n{total_samples:,} body-samples total "
          f"(daily for all 26 over the base span would be {ndays*len(BODIES):,})")
    for nm, _ in BODIES:
        if nm in SPAN:
            st, ns, _, y0, y1 = per[nm]
            print(f"  {nm} carries the extended span {y0}-{y1}: {ns:,} samples at stride {st}d")

    blocks = {}
    dscale = {}
    sscale = {}
    for bi, (nm, code) in enumerate(BODIES):
        st, ns, bjd0 = per[nm][0], per[nm][1], per[nm][2]
        lon = np.zeros(ns, np.float64); lat = np.zeros(ns, np.float64)
        dist = np.zeros(ns, np.float64); spd = np.zeros(ns, np.float64)
        hel = np.zeros(ns, np.float64)
        for i in range(ns):
            jd = bjd0 + i * st
            p = swe.calc_ut(jd, code, FLG)[0]
            if code in NODELIKE:
                h = p[0]
            else:
                try:
                    h = swe.calc_ut(jd, code, FLG_HC)[0][0]
                except Exception:
                    h = p[0]
            lon[i], lat[i], dist[i], spd[i], hel[i] = p[0], p[1], p[2], p[3], h

        # THE STORED SPEED IS THE HERMITE TANGENT, AND SWISSEPH'S SPEED FIELD IS NOT ALWAYS TRUSTWORTHY for the
        # Uranian hypotheticals. Extending the span to 1698 put a sample on 1749-03-03, where swisseph reports
        # Zeus at -0.007595 deg/day while its own longitude climbs through that instant at +0.018506 — an
        # isolated glitch of the same kind already documented for Vulkanus and Poseidon. Stored as a tangent, one
        # bad speed bends the reconstructed curve for a whole stride: the shim was 0.0189 deg out at 1749-02-26,
        # against a 0.0110 budget, and the gate refused the asset. The verifier already OUTVOTES such a glitch
        # when it checks; the builder must do the same when it stores. Where swisseph's speed disagrees with the
        # central difference of swisseph's own longitude by more than a tenth of a degree per day, the central
        # difference is what gets written — the longitude is the quantity we trust, so its slope is the tangent.
        if ns >= 3:
            dl = np.zeros(ns, np.float64)
            for i in range(ns):
                jm = bjd0 + i * st - 1.0
                jp = bjd0 + i * st + 1.0
                lm = swe.calc_ut(jm, code, FLG)[0][0]
                lp = swe.calc_ut(jp, code, FLG)[0][0]
                dl[i] = ((lp - lm + 180.0) % 360.0 - 180.0) / 2.0
            # THE THRESHOLD MUST SCALE WITH THE BODY, and a fixed 0.001 deg/day did not. It flagged 115,826 of
            # the Moon's 122,358 samples, 35,230 of the node's and 15,454 of Mercury's — none of them glitches.
            # A fast body's true speed differs from a +-1-day central difference by its curvature, which for the
            # Moon is far above 0.001 deg/day, so the fixed threshold quietly replaced exact tangents with 2-day
            # secants and made the Moon WORSE. A glitch is not a small disagreement; it is a speed of the wrong
            # sign or the wrong magnitude entirely — Zeus reported -0.0076 against a true +0.0185. So the test is
            # relative: the two must differ by more than half the body's typical speed AND by more than the
            # curvature a 2-day secant can produce, which the median absolute disagreement estimates from the
            # data itself. That keeps the ~30 Uranian glitches per body and drops every false positive.
            gap = np.abs(spd - dl)
            typical = np.median(np.abs(dl)) + 1e-9
            curvature = np.median(gap)                       # what an honest secant disagrees by, for THIS body
            glitch = (gap > 0.5 * typical) & (gap > 8.0 * curvature + 1e-6)
            if glitch.any():
                idx = np.flatnonzero(glitch)
                print(f"      {nm}: swisseph's speed contradicts its own longitude at {len(idx)} sample(s) "
                      f"(first at jd {bjd0 + idx[0] * st:.1f}); storing the central difference there", flush=True)
                spd = np.where(glitch, dl, spd)

        dlo, dhi = float(dist.min()), float(dist.max())
        if dhi - dlo < 1e-12:
            dhi = dlo + 1e-9
        dscale[nm] = (dlo, dhi)
        slo, shi = float(spd.min()), float(spd.max())
        pad = 0.02 * (shi - slo) + 1e-9      # headroom, so an interpolated node can never fall outside
        slo, shi = slo - pad, shi + pad
        sscale[nm] = (slo, shi)
        blocks[nm] = {
            "lon": (np.mod(lon, 360.0) / 360.0 * 65535).round().astype(np.uint16),
            "lat": (np.clip(lat, -90, 90) / 90.0 * 32767).round().astype(np.int16),
            "dist": ((dist - dlo) / (dhi - dlo) * 65535).round().astype(np.uint16),
            "spd": ((spd - slo) / (shi - slo) * 65535).round().astype(np.uint16),
            "helio": (np.mod(hel, 360.0) / 360.0 * 65535).round().astype(np.uint16),
        }
        print(f"  [{bi+1:>2}/{len(BODIES)}] {nm:<10} stride {st}d · {ns:,} samples · "
              f"{per[nm][3]}-{per[nm][4]} · dist {dlo:.4f}..{dhi:.4f} AU · "
              f"speed step {(shi-slo)/65535:.3g} deg/day", flush=True)

    nay = (ndays - 1) // AYA_STRIDE + 3
    aya = np.zeros((nay, len(AYANAMSAS)), np.uint16)
    for i in range(nay):
        jd = jd0 + i * AYA_STRIDE
        for m, (_, mc) in enumerate(AYANAMSAS):
            swe.set_sid_mode(mc)
            aya[i, m] = int(round(np.mod(swe.get_ayanamsa_ut(jd), 360.0) / 360.0 * 65535)) & 0xFFFF
    print(f"  ayanamsas: {nay:,} samples x {len(AYANAMSAS)} "
          f"(sidereal time and RA/dec are computed, not stored — see the docstring)")

    # WRITTEN TO A TEMPORARY NAME, VERIFIED, THEN MOVED INTO PLACE. The pre-check above measures
    # interpolation on unquantised values, which is only part of the story: the shipped error is
    # interpolation AND quantisation together, on the actual bytes, for every quantity — and the pre-check
    # covers longitude alone. So the real gate is `sweshim.verify()` run against the FILE, below. Writing
    # under a temp name means a file that fails the gate never becomes the asset.
    out = os.path.join(WEB, "ephem4.bin.tmp")
    with open(out, "wb") as f:
        f.write(b"AQEPH00A")
        f.write(struct.pack("<iiii", len(BODIES), 5, len(AYANAMSAS), ndays))
        f.write(struct.pack("<d", jd0))
        f.write(struct.pack("<ii", AYA_STRIDE, nay))
        for nm, _ in BODIES:
            st, ns, bjd0 = per[nm][0], per[nm][1], per[nm][2]
            dlo, dhi = dscale[nm]
            slo, shi = sscale[nm]
            f.write(struct.pack("<iiddddd", st, ns, bjd0, dlo, dhi, slo, shi))
        for nm, _ in BODIES:
            for q in ("lon", "lat", "dist", "spd", "helio"):
                f.write(blocks[nm][q].tobytes())
        f.write(aya.tobytes(order="C"))
    size = os.path.getsize(out)

    meta = {"magic": "AQEPH00A", "days": ndays, "jd0": jd0, "hourUT": 10.0,
            "yearFrom": Y0, "yearTo": Y1, "quantStep": QUANT,
            "bodies": [b[0] for b in BODIES],
            "codes": {b[0]: int(b[1]) for b in BODIES},
            "strides": {nm: per[nm][0] for nm, _ in BODIES},
            "samples": {nm: per[nm][1] for nm, _ in BODIES},
            "spans": {nm: [per[nm][3], per[nm][4]] for nm, _ in BODIES},
            "bodyJd0": {nm: per[nm][2] for nm, _ in BODIES},
            "dist": {nm: list(dscale[nm]) for nm, _ in BODIES},
            "speed": {nm: list(sscale[nm]) for nm, _ in BODIES},
            "ayanamsas": [a[0] for a in AYANAMSAS], "ayaStride": AYA_STRIDE, "ayaSamples": nay,
            "quantities": ["lon", "lat", "dist", "spd", "helio"],
            "derived": ["ra", "dec", "sidtime"],
            "bytes": size}
    json.dump(meta, open(os.path.join(WEB, "ephem4.json"), "w"), indent=1)
    json.dump(_tables(jd0, jd1), open(os.path.join(WEB, "tables.json"), "w"))
    tsz = os.path.getsize(os.path.join(WEB, "tables.json"))

    # ── the gate: verify the bytes just written, through the reader that will read them ────────────
    import sys
    sys.path.insert(0, WEB)
    import importlib
    import sweshim
    importlib.reload(sweshim)
    sweshim.load(out, os.path.join(WEB, "tables.json"))
    print()
    bad = sweshim.verify_asset(BODIES, SPAN, SPAN_DEFAULT, QUANT, nodelike={int(c) for c in NODELIKE})
    if bad:
        print("\nREFUSING TO PUBLISH — the written asset does not reconstruct within budget:")
        for line in bad:
            print(f"    {line}")
        print(f"  the candidate file is left at {out} for inspection")
        raise SystemExit(1)
    final = os.path.join(WEB, "ephem4.bin")
    os.replace(out, final)
    print(f"\nwrote web/ephem4.bin ({size/1e6:.2f} MB) · ephem4.json · tables.json ({tsz/1e3:.0f} kB)")
    print(f"  every body reconstructs within budget, verified against pyswisseph on the written bytes")


if __name__ == "__main__":
    main()
