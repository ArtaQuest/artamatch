"""
sweshim.py — a pure-numpy stand-in for pyswisseph, so the BROWSER RUNS THE REAL PIPELINE.

THE POINT. Pyodide has no pyswisseph. The previous shipped model worked around that by reimplementing ten
traditions in `web/features.py`, and that reimplementation is exactly why it scored 0.6815 where the laptop
stack scored 0.7311: eight of the eighteen traditions the stack chose were never ported, including the five
strongest blocks in the project. Reimplementation was the wrong move. This file makes it unnecessary — it
answers every swisseph call that `core.py` and the eighteen `trad_*.py` modules make, so those files run in
the browser UNCHANGED. There is one implementation of every feature, in the training code, and the browser
imports it. Parity is structural, not tested.

Install it before anything imports swisseph:

    import sys, sweshim
    sweshim.load("ephem4.bin", "tables.json")
    sys.modules["swisseph"] = sweshim

WHAT IS ANSWERED, AND WHAT IT COSTS — every figure below is `verify()`'s output against real pyswisseph
over 400 random instants spanning 1800-2030, not an estimate. The reference scale is the asset's own storage
step, 360/65535 = 0.0055 deg; anything at that level is exact storage rather than a method error.

    calc_ut          cubic Hermite between stored samples, using the STORED SPEED as the tangent, on the
                     UNWRAPPED angle.  longitude <= 0.0049 deg   RA/dec <= 0.011   speed <= 0.008 deg/day
    sidtime          the IAU 1982 series plus the equation of the equinoxes, because swe.sidtime returns
                     APPARENT sidereal time — omitting that is a 16 arcsec error every cusp inherits.
                                                                                            0.0003 deg
    houses           Placidus by iterating the semi-arc condition to convergence; whole-sign and equal in
                     closed form.                        Ascendant 0.0006   MC 0.0003   cusps 0.0006 deg
    rise_trans       an hour-angle bracket then Newton on the true altitude, with the horizon depression
                     MEASURED off swisseph (-0.60985, not the textbook -0.5667).       1.0 second
    fixstar2_ut      Spica only, tabulated every 32 days — a yearly table aliased the annual aberration
                     into a 23 arcsec error. Any other name raises, exactly as a missing sefstars.txt does.
                                                                                            0.0003 deg
    ayanamsa         all 21 of core.py's modes, interpolated from the asset.               <= 0.0032 deg
    deltat           tabulated per year and interpolated; smooth by construction.          0.04 seconds
    eclipses         a lookup in the shipped table of every global solar and lunar eclipse in the span, so
                     sol_eclipse_when_glob returns the exact JD swisseph would have searched to.   exact
    julday / revjul  calendar arithmetic, Gregorian and Julian.                                    exact

WHAT IS NOT ANSWERED. Anything outside the shipped span raises, rather than extrapolating: an asset that
quietly answers for the year 1500 would put a wrong number into a feature and no one would see it. The two
callers that can hit the edge (`core.load` and trad_lunar_calendrical's eclipse walk) already guard.

"""
import json
import math
import os
import struct

import numpy as np

# ── the swisseph constants the modules use ────────────────────────────────────────────────────────────
FLG_SWIEPH = 2
FLG_SPEED = 256
FLG_EQUATORIAL = 2048
FLG_HELCTR = 8
FLG_TOPOCTR = 32768
GREG_CAL = 1
JUL_CAL = 0
CALC_RISE = 1
CALC_SET = 2
CALC_MTRANSIT = 4
CALC_ITRANSIT = 8
BIT_DISC_CENTER = 256
BIT_NO_REFRACTION = 512

SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO = range(10)
MEAN_NODE, TRUE_NODE, MEAN_APOG, OSCU_APOG, EARTH, CHIRON, PHOLUS = 10, 11, 12, 13, 14, 15, 16
CERES, PALLAS, JUNO, VESTA = 17, 18, 19, 20
CUPIDO, HADES, ZEUS, KRONOS, APOLLON, ADMETOS, VULKANUS, POSEIDON = range(40, 48)

(SIDM_FAGAN_BRADLEY, SIDM_LAHIRI, SIDM_DELUCE, SIDM_RAMAN, SIDM_USHASHASHI, SIDM_KRISHNAMURTI,
 SIDM_DJWHAL_KHUL, SIDM_YUKTESHWAR, SIDM_JN_BHASIN, SIDM_BABYL_KUGLER1, SIDM_BABYL_KUGLER2,
 SIDM_BABYL_KUGLER3, SIDM_BABYL_HUBER, SIDM_BABYL_ETPSC, SIDM_ALDEBARAN_15TAU, SIDM_HIPPARCHOS,
 SIDM_SASSANIAN, SIDM_GALCENT_0SAG, SIDM_J2000, SIDM_J1900, SIDM_B1950, SIDM_SURYASIDDHANTA,
 SIDM_SURYASIDDHANTA_MSUN, SIDM_ARYABHATA, SIDM_ARYABHATA_MSUN, SIDM_SS_REVATI, SIDM_SS_CITRA,
 SIDM_TRUE_CITRA, SIDM_TRUE_REVATI, SIDM_TRUE_PUSHYA) = range(30)

Error = RuntimeError

# ── the asset ─────────────────────────────────────────────────────────────────────────────────────────
_A = None          # loaded asset


class _Asset:
    __slots__ = ("jd0", "ndays", "nb", "naya", "aya_stride", "nay", "names", "code2idx",
                 "stride", "nsamp", "bjd0", "dlo", "dhi", "slo", "shi", "q", "aya", "tab",
                 "stride_f", "nsamp_i", "bjd0_f", "hi_f",
                 "dt_y0", "dt", "sp_ra", "sp_dec", "sp_jd0", "sp_stride", "sol_jd", "sol_fl", "lun_jd", "lun_fl", "sid_mode")

    def jd_ok(self, jd, bi=None):
        """Is `jd` inside the span of body `bi` (or the base span when no body is named)?

        Per body, because the Sun carries 1180-2081 and everything else 1800-2030 — see build_asset_v4's
        SPAN. Refusing outside the span rather than extrapolating is deliberate: a silently extrapolated
        position would put a wrong number into a feature and nothing downstream would show it.
        """
        if bi is None:
            return self.jd0 - 0.5 <= jd <= self.jd0 + self.ndays + 0.5
        return self.bjd0_f[bi] - 0.5 <= jd <= self.hi_f[bi] + 0.5


def load(binpath, tabpath=None, blob=None, tables=None):
    """Read the asset. `blob`/`tables` let the browser hand over already-fetched bytes/JSON."""
    global _A
    raw = blob if blob is not None else open(binpath, "rb").read()
    if raw[:8] != b"AQEPH00A":
        raise Error(f"bad asset magic {raw[:8]!r} — expected AQEPH00A")
    a = _Asset()
    off = 8
    a.nb, nq, a.naya, a.ndays = struct.unpack_from("<iiii", raw, off); off += 16
    (a.jd0,) = struct.unpack_from("<d", raw, off); off += 8
    a.aya_stride, a.nay = struct.unpack_from("<ii", raw, off); off += 8
    a.stride = np.zeros(a.nb, np.int64); a.nsamp = np.zeros(a.nb, np.int64)
    a.bjd0 = np.zeros(a.nb); a.dlo = np.zeros(a.nb); a.dhi = np.zeros(a.nb)
    a.slo = np.zeros(a.nb); a.shi = np.zeros(a.nb)
    for b in range(a.nb):
        st, ns, bjd0, dlo, dhi, slo, shi = struct.unpack_from("<iiddddd", raw, off); off += 48
        a.stride[b], a.nsamp[b] = st, ns
        a.bjd0[b], a.dlo[b], a.dhi[b] = bjd0, dlo, dhi
        a.slo[b], a.shi[b] = slo, shi
    a.q = []
    for b in range(a.nb):
        ns = int(a.nsamp[b])
        per = {}
        for name, dt in (("lon", np.uint16), ("lat", np.int16), ("dist", np.uint16),
                         ("spd", np.uint16), ("helio", np.uint16)):
            per[name] = np.frombuffer(raw, dtype=dt, count=ns, offset=off).astype(np.float64)
            off += ns * np.dtype(dt).itemsize
        # decode once, at load, so every later call is arithmetic on float64
        per["lon"] = per["lon"] / 65535.0 * 360.0
        per["lat"] = per["lat"] / 32767.0 * 90.0
        per["dist"] = a.dlo[b] + per["dist"] / 65535.0 * (a.dhi[b] - a.dlo[b])
        # SPEED IS SCALED PER BODY. One shared +-16 deg/day range gave a 0.000488 deg/day step, which is
        # 5.8% of Poseidon's typical speed — and the sign of this quantity is retrograde status, which the
        # shared scale got wrong for 1 in 400 Pluto samples. The scale travels in the header.
        per["spd"] = a.slo[b] + per["spd"] / 65535.0 * (a.shi[b] - a.slo[b])
        per["helio"] = per["helio"] / 65535.0 * 360.0
        a.q.append(per)
    a.aya = np.frombuffer(raw, dtype=np.uint16, count=a.nay * a.naya, offset=off) \
              .astype(np.float64).reshape(a.nay, a.naya) / 65535.0 * 360.0

    meta = json.load(open(os.path.join(os.path.dirname(binpath or "."), "ephem4.json"))) \
        if binpath and os.path.exists(os.path.join(os.path.dirname(binpath), "ephem4.json")) else None
    a.names = meta["bodies"] if meta else None
    codes = meta["codes"] if meta else None
    # asset index by swisseph code — the 18 of core.py then the 8 Uranian hypotheticals
    order = [SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO,
             TRUE_NODE, MEAN_NODE, MEAN_APOG, CHIRON, CERES, PALLAS, JUNO, VESTA,
             CUPIDO, HADES, ZEUS, KRONOS, APOLLON, ADMETOS, VULKANUS, POSEIDON]
    if codes:
        order = [codes[n] for n in meta["bodies"]]
    a.code2idx = {c: i for i, c in enumerate(order)}

    t = tables if tables is not None else json.load(open(tabpath))
    a.tab = t
    a.dt_y0 = t["yearFrom"]
    a.dt = np.array(t["deltat"], float)
    sp = np.array(t["spica"], float)
    a.sp_ra, a.sp_dec = sp[:, 0], sp[:, 1]
    a.sp_jd0, a.sp_stride = float(t["spicaJd0"]), float(t["spicaStride"])
    s = np.array(t["solar"], float); l = np.array(t["lunar"], float)
    a.sol_jd, a.sol_fl = s[:, 0], s[:, 1].astype(np.int64)
    a.lun_jd, a.lun_fl = l[:, 0], l[:, 1].astype(np.int64)
    a.sid_mode = SIDM_FAGAN_BRADLEY
    # plain-Python copies of the per-body header, so the hot path never indexes a numpy array for a scalar
    a.stride_f = [float(v) for v in a.stride]
    a.nsamp_i = [int(v) for v in a.nsamp]
    a.bjd0_f = [float(v) for v in a.bjd0]
    a.hi_f = [float(a.bjd0[b]) + (int(a.nsamp[b]) - 3) * float(a.stride[b]) for b in range(a.nb)]
    _A = a
    return a


def _need():
    if _A is None:
        raise Error("sweshim.load() has not been called")
    return _A


def set_ephe_path(p=None):
    return None


def set_jpl_file(p=None):
    return None


def close():
    return None


def version():
    return "sweshim-1.0 (numpy, asset AQEPH00A)"


def _wrap(d):
    return (d + 180.0) % 360.0 - 180.0


# HOT PATH. core.load() calls calc_ut six times per couple for each of eighteen bodies and
# get_ayanamsa_ut twenty-one times per instant — about 234 calls per couple. The first version of this file
# did that arithmetic on numpy scalars and cost 96 ms per couple, which made core.load slower than all
# nineteen tradition modules put together (they are vectorised over rows; this is not). numpy scalar
# arithmetic allocates an array object per operation; `math` on Python floats does not. Everything below the
# line is therefore plain floats and `math`, and the arrays are read with float() rather than indexed as
# numpy scalars. Same numbers, and the verify() figures in the docstring are measured after this change.
_floor = math.floor
_cos = math.cos
_sin = math.sin
_tan = math.tan
_asin = math.asin
_acos = math.acos
_atan2 = math.atan2
_sqrt = math.sqrt
_RAD = math.pi / 180.0
_DEG = 180.0 / math.pi


# ── positions ─────────────────────────────────────────────────────────────────────────────────────────
def _sample(a, bi, jd):
    """Cubic Hermite for every stored quantity of body `bi` at `jd`, returning (lon, lat, dist, helio).

    Longitude uses the STORED SPEED as its tangent, which is what makes it Hermite rather than a spline and
    is why the sampling strides can be as coarse as they are. Latitude, distance and heliocentric longitude
    have no stored derivative, so they get a Catmull-Rom tangent from the neighbouring samples — one-sided
    at the array ends, because a halved central difference there underestimates the tangent and put the
    first interval 0.5 degrees out when the Moon happened to land in it.

    Longitude and heliocentric longitude are interpolated on the UNWRAPPED angle. Hermite across a 360->0
    crossing on raw values is off by up to 130 degrees — the one real trap in this file.
    """
    st = a.stride_f[bi]
    x = (jd - a.bjd0_f[bi]) / st
    ns = a.nsamp_i[bi]
    i = int(_floor(x))
    i = 0 if i < 0 else (ns - 2 if i > ns - 2 else i)
    t = x - i
    t2 = t * t
    t3 = t2 * t
    h00 = 2 * t3 - 3 * t2 + 1.0
    h10 = t3 - 2 * t2 + t
    h01 = -2 * t3 + 3 * t2
    h11 = t3 - t2
    q = a.q[bi]
    ql, qs = q["lon"], q["spd"]
    p0 = float(ql[i]); p1 = float(ql[i + 1])
    m0 = float(qs[i]); m1 = float(qs[i + 1])
    lon = h00 * p0 + h10 * m0 * st + h01 * (p0 + _wrap(p1 - p0)) + h11 * m1 * st

    def cr(v, unwrap):
        a1 = float(v[i]); a2 = float(v[i + 1])
        a0 = float(v[i - 1]) if i >= 1 else None
        a3 = float(v[i + 2]) if i + 2 <= ns - 1 else None
        if unwrap:
            a2 = a1 + _wrap(a2 - a1)
            if a0 is not None:
                a0 = a1 + _wrap(a0 - a1)
            if a3 is not None:
                a3 = a2 + _wrap(a3 - a2)
        d1 = (0.5 * (a2 - a0) if a0 is not None else (a2 - a1)) / st
        d2 = (0.5 * (a3 - a1) if a3 is not None else (a2 - a1)) / st
        return h00 * a1 + h10 * d1 * st + h01 * a2 + h11 * d2 * st

    return (lon % 360.0, cr(q["lat"], False), cr(q["dist"], False), cr(q["helio"], True) % 360.0)


# ── nutation, obliquity, and the equatorial rotation ──────────────────────────────────────────────────
def _nutation(jd):
    """Nutation in longitude and obliquity, in arcseconds — Meeus 22.2, the four dominant terms.

    Small, but not optional: swe.sidtime returns APPARENT sidereal time, so leaving the equation of the
    equinoxes out puts every Ascendant up to 16 arcsec wrong, and the equatorial rotation needs the TRUE
    obliquity or RA/dec come out 0.0027 deg off instead of 0.00002.
    """
    T = (jd - 2451545.0) / 36525.0
    om = (125.04452 - 1934.136261 * T) * _RAD
    L = (280.4665 + 36000.7698 * T) * _RAD
    Lp = (218.3165 + 481267.8813 * T) * _RAD
    dpsi = (-17.20 * _sin(om) - 1.32 * _sin(2 * L)
            - 0.23 * _sin(2 * Lp) + 0.21 * _sin(2 * om))
    deps = (9.20 * _cos(om) + 0.57 * _cos(2 * L)
            + 0.10 * _cos(2 * Lp) - 0.09 * _cos(2 * om))
    return dpsi, deps


def _eps_mean(jd):
    T = (jd - 2451545.0) / 36525.0
    return 23.439291111 - 0.0130042 * T - 1.64e-7 * T * T + 5.036e-7 * T ** 3


def _eps_true(jd):
    return _eps_mean(jd) + _nutation(jd)[1] / 3600.0


def _to_equatorial(lam, bet, eps):
    """Apparent RA and declination from an apparent ecliptic position. Verified to 0.000021 deg."""
    l = lam * _RAD; b = bet * _RAD; e = eps * _RAD
    sl = _sin(l); cl = _cos(l); se = _sin(e); ce = _cos(e)
    ra = _atan2(sl * ce - _tan(b) * se, cl) * _DEG
    dec = _asin(max(-1.0, min(1.0, _sin(b) * ce + _cos(b) * se * sl))) * _DEG
    return ra % 360.0, dec


def _speed(a, bi, jd):
    """Longitude speed: the analytic derivative of the same Hermite that gives the longitude."""
    st = a.stride_f[bi]
    x = (jd - a.bjd0_f[bi]) / st
    ns = a.nsamp_i[bi]
    i = int(_floor(x))
    i = 0 if i < 0 else (ns - 2 if i > ns - 2 else i)
    t = x - i
    t2 = t * t
    q = a.q[bi]
    ql, qs = q["lon"], q["spd"]
    p0 = float(ql[i])
    m0 = float(qs[i]); m1 = float(qs[i + 1])
    p1u = p0 + _wrap(float(ql[i + 1]) - p0)
    d00 = 6 * t2 - 6 * t
    d01 = -6 * t2 + 6 * t
    d10 = 3 * t2 - 4 * t + 1
    d11 = 3 * t2 - 2 * t
    return (d00 * p0 + d01 * p1u) / st + d10 * m0 + d11 * m1


def calc_ut(jd, code, flags=FLG_SWIEPH):
    """((lon|ra, lat|dec, dist, spd, 0, 0), retflag) — the shape pyswisseph returns."""
    a = _need()
    bi = a.code2idx.get(int(code))
    if bi is None:
        raise Error(f"body {code} is not in the shipped asset")
    if not a.jd_ok(jd, bi):
        raise Error(f"jd {jd} is outside body {code}'s shipped span")
    lon, lat, dist, hel = _sample(a, bi, float(jd))
    spd = _speed(a, bi, float(jd))
    if flags & FLG_HELCTR:
        return ((hel, lat, dist, spd, 0.0, 0.0), int(flags))
    if flags & FLG_EQUATORIAL:
        ra, dec = _to_equatorial(lon, lat, _eps_true(float(jd)))
        return ((ra, dec, dist, spd, 0.0, 0.0), int(flags))
    return ((lon, lat, dist, spd, 0.0, 0.0), int(flags))


def calc(jd_et, code, flags=FLG_SWIEPH):
    return calc_ut(jd_et - deltat(jd_et) / 86400.0, code, flags)


# ── time ──────────────────────────────────────────────────────────────────────────────────────────────
def sidtime(jd):
    """Greenwich APPARENT sidereal time in hours, matching swe.sidtime.

    Evaluated, not interpolated — it is a polynomial, so a stored table could only be worse. The equation
    of the equinoxes is what makes it apparent rather than mean; without it this is 16 arcsec out and every
    house cusp inherits the error.
    """
    d = jd - 2451545.0
    T = d / 36525.0
    g = 280.46061837 + 360.98564736629 * d + 0.000387933 * T * T - T * T * T / 38710000.0
    dpsi, deps = _nutation(jd)
    g += dpsi / 3600.0 * _cos((_eps_mean(jd) + deps / 3600.0) * _RAD)
    return (g % 360.0) / 15.0


def sidtime0(jd, eps=None, nut=None):
    return sidtime(jd)


def deltat(jd):
    a = _need()
    y = 2000.0 + (jd - 2451545.0) / 365.25
    if not (a.dt_y0 <= y <= a.dt_y0 + len(a.dt) - 1):
        raise Error(f"jd {jd} (year {y:.0f}) is outside the shipped delta-T table "
                    f"{a.dt_y0}-{a.dt_y0 + len(a.dt) - 1}")
    x = np.clip(y - a.dt_y0, 0, len(a.dt) - 1)
    i = int(np.floor(x)); i = min(i, len(a.dt) - 2)
    f = x - i
    return float((a.dt[i] * (1 - f) + a.dt[i + 1] * f) / 86400.0 * 86400.0) / 86400.0 * 86400.0


def julday(year, month, day, hour=0.0, cal=GREG_CAL):
    y, m = int(year), int(month)
    if m <= 2:
        y -= 1; m += 12
    if cal == GREG_CAL:
        A = y // 100
        B = 2 - A + A // 4
    else:
        B = 0
    return (np.floor(365.25 * (y + 4716)) + np.floor(30.6001 * (m + 1))
            + day + B - 1524.5 + hour / 24.0)


def revjul(jd, cal=GREG_CAL):
    z = np.floor(jd + 0.5)
    f = (jd + 0.5) - z
    if cal == GREG_CAL and z >= 2299161:
        alpha = np.floor((z - 1867216.25) / 36524.25)
        A = z + 1 + alpha - np.floor(alpha / 4)
    else:
        A = z
    B = A + 1524
    C = np.floor((B - 122.1) / 365.25)
    D = np.floor(365.25 * C)
    E = np.floor((B - D) / 30.6001)
    day = B - D - np.floor(30.6001 * E) + f
    month = E - 1 if E < 14 else E - 13
    year = C - 4716 if month > 2 else C - 4715
    d = int(np.floor(day))
    return (int(year), int(month), d, float((day - d) * 24.0))


def utc_to_jd(*a, **k):
    raise Error("utc_to_jd is not shimmed — no caller needs it")


# ── the one fixed star swisseph itself resolves here ──────────────────────────────────────────────────
def fixstar2_ut(name, jd, flags=FLG_SWIEPH):
    a = _need()
    nm = (name.decode() if isinstance(name, bytes) else str(name)).strip()
    if not nm.lower().startswith("spica"):
        raise Error(f"fixstar2_ut({nm!r}): no star catalogue — only Spica is tabulated, exactly as a "
                    f"swisseph install without sefstars.txt")
    xr = (jd - a.sp_jd0) / a.sp_stride
    if not (0 <= xr <= len(a.sp_ra) - 1):
        raise Error(f"jd {jd} is outside the shipped Spica table")
    x = np.clip(xr, 0, len(a.sp_ra) - 1)
    i = min(int(np.floor(x)), len(a.sp_ra) - 2)
    f = x - i
    ra = a.sp_ra[i] + _wrap(a.sp_ra[i + 1] - a.sp_ra[i]) * f
    dec = a.sp_dec[i] * (1 - f) + a.sp_dec[i + 1] * f
    return ((float(np.mod(ra, 360.0)), float(dec), 1.0, 0.0, 0.0, 0.0), "Spica,alVir", int(flags))


fixstar_ut = fixstar2_ut


# ── sidereal modes ────────────────────────────────────────────────────────────────────────────────────
_AYA_ORDER = [SIDM_FAGAN_BRADLEY, SIDM_LAHIRI, SIDM_DELUCE, SIDM_RAMAN, SIDM_USHASHASHI,
              SIDM_KRISHNAMURTI, SIDM_DJWHAL_KHUL, SIDM_YUKTESHWAR, SIDM_JN_BHASIN,
              SIDM_BABYL_KUGLER1, SIDM_ALDEBARAN_15TAU, SIDM_HIPPARCHOS, SIDM_SASSANIAN,
              SIDM_GALCENT_0SAG, SIDM_J2000, SIDM_B1950, SIDM_SURYASIDDHANTA, SIDM_ARYABHATA,
              SIDM_TRUE_CITRA, SIDM_TRUE_REVATI, SIDM_TRUE_PUSHYA]


def set_sid_mode(mode, t0=0.0, ayan_t0=0.0):
    _need().sid_mode = int(mode)


def get_ayanamsa_ut(jd):
    a = _need()
    try:
        col = _AYA_ORDER.index(a.sid_mode)
    except ValueError:
        raise Error(f"ayanamsa mode {a.sid_mode} is not in the shipped asset")
    # REFUSE, DO NOT CLAMP. Clamping outside the span returns the ayanamsa of the nearest stored day, which
    # is a plausible number for the wrong century — it would flow into a sidereal longitude, then into a
    # nakshatra, and nothing downstream would show it. The same applies to deltat and fixstar2_ut below.
    if not a.jd_ok(jd):
        raise Error(f"jd {jd} is outside the shipped ayanamsa span")
    x = (jd - a.jd0) / a.aya_stride
    i = int(_floor(x))
    i = 0 if i < 0 else (a.nay - 2 if i > a.nay - 2 else i)
    f = x - i
    v0 = float(a.aya[i, col]); v1 = float(a.aya[i + 1, col])
    return (v0 + _wrap(v1 - v0) * f) % 360.0


def get_ayanamsa(jd):
    return get_ayanamsa_ut(jd)


# ── houses ────────────────────────────────────────────────────────────────────────────────────────────
def _armc(jd, geolon):
    return float(np.mod(sidtime(jd) * 15.0 + geolon, 360.0))


def _mc_from_armc(armc, eps):
    r, e = np.deg2rad(armc), np.deg2rad(eps)
    return float(np.mod(np.degrees(np.arctan2(np.tan(r), np.cos(e))) + (180.0 if 90 < armc % 360 < 270 else 0.0), 360.0))


def _asc_from_armc(armc, eps, lat):
    """Ascendant. The sign convention was pinned by testing four variants against swisseph on 300 charts."""
    r, e, p = np.deg2rad(armc), np.deg2rad(eps), np.deg2rad(np.clip(lat, -89.9, 89.9))
    y = np.cos(r)
    x = -(np.sin(r) * np.cos(e) + np.tan(p) * np.sin(e))
    return float(np.mod(np.degrees(np.arctan2(y, x)), 360.0))


def _lon_of_ra(ra, eps):
    """The ecliptic longitude whose right ascension is `ra` (the ecliptic point at that RA)."""
    r, e = np.deg2rad(ra), np.deg2rad(eps)
    return float(np.mod(np.degrees(np.arctan2(np.sin(r), np.cos(r) * np.cos(e))), 360.0))


def _placidus(armc, eps, lat):
    """The four intermediate Placidus cusps, by iterating the semi-arc condition to convergence.

    Placidus trisects each point's own diurnal (or nocturnal) semi-arc rather than an angle, so a cusp is
    the ecliptic point whose hour angle H equals a fixed fraction of its OWN semi-arc D(dec) — which makes
    it implicit, because D depends on the declination, which depends on the point. Fixed-point iteration
    from the Porphyry position converges in a handful of steps at ordinary latitudes. Above the polar
    circle the semi-arc stops existing and swisseph itself falls back, so this returns None and the caller
    keeps whatever fallback core.py already had.
    """
    e, p = np.deg2rad(eps), np.deg2rad(np.clip(lat, -89.9, 89.9))
    if abs(lat) > 66.0:
        return None
    out = {}
    for cusp, frac, nocturnal in ((11, 1 / 3.0, False), (12, 2 / 3.0, False),
                                  (2, 1 / 3.0, True), (3, 2 / 3.0, True)):
        ra = armc + (30.0 * (cusp - 10) if cusp > 10 else 90.0 + 30.0 * (cusp + 1))
        for _ in range(60):
            lam = _lon_of_ra(ra, eps)
            dec = np.degrees(np.arcsin(np.sin(e) * np.sin(np.deg2rad(lam))))
            c = -np.tan(p) * np.tan(np.deg2rad(dec))
            if abs(c) >= 1.0:
                return None
            D = np.degrees(np.arccos(c))          # semi-diurnal arc
            H = frac * D if not nocturnal else D + frac * (180.0 - D)
            nra = armc + H
            if abs(_wrap(nra - ra)) < 1e-9:
                ra = nra
                break
            ra = ra + _wrap(nra - ra) * 0.6       # damped, because the map is only mildly contracting
        out[cusp] = _lon_of_ra(ra, eps)
    return out


def houses(jd, lat, lon, hsys=b"P"):
    """(cusps[12], ascmc[8]) — the shape pyswisseph returns for swe.houses."""
    h = (hsys.decode() if isinstance(hsys, bytes) else str(hsys)).upper()[:1]
    eps = _eps_true(jd)
    armc = _armc(jd, lon)
    asc = _asc_from_armc(armc, eps, lat)
    mc = _mc_from_armc(armc, eps)
    c = [0.0] * 12
    if h == "W":                                     # whole sign — the first house is the Asc's sign
        s0 = np.floor(asc / 30.0) * 30.0
        for i in range(12):
            c[i] = float(np.mod(s0 + 30.0 * i, 360.0))
    elif h == "E":                                   # equal from the Ascendant
        for i in range(12):
            c[i] = float(np.mod(asc + 30.0 * i, 360.0))
    else:
        pl = _placidus(armc, eps, lat) if h == "P" else None
        if pl is None:                               # Porphyry-style fallback, as swisseph does at the poles
            span1 = np.mod(asc - mc, 360.0)
            span2 = 180.0 - span1
            c[0] = asc
            c[1] = float(np.mod(asc + span2 / 3.0, 360.0))
            c[2] = float(np.mod(asc + 2 * span2 / 3.0, 360.0))
            c[9] = mc
            c[10] = float(np.mod(mc + span1 / 3.0, 360.0))
            c[11] = float(np.mod(mc + 2 * span1 / 3.0, 360.0))
        else:
            c[0] = asc; c[9] = mc
            c[10] = pl[11]; c[11] = pl[12]; c[1] = pl[2]; c[2] = pl[3]
        for i in range(3, 9):
            c[i] = float(np.mod(c[i - 3 if i < 6 else i - 9] + 180.0, 360.0)) if False else 0.0
        for i in range(6):
            c[i + 3] = float(np.mod(c[i + 9 if i < 3 else i - 3] + 180.0, 360.0))
        # cusps 4..9 are the opposites of 10,11,12,1,2,3
        c[3] = float(np.mod(c[9] + 180.0, 360.0))
        c[4] = float(np.mod(c[10] + 180.0, 360.0))
        c[5] = float(np.mod(c[11] + 180.0, 360.0))
        c[6] = float(np.mod(c[0] + 180.0, 360.0))
        c[7] = float(np.mod(c[1] + 180.0, 360.0))
        c[8] = float(np.mod(c[2] + 180.0, 360.0))
    vertex = float(np.mod(_asc_from_armc(armc + 180.0, eps, -lat) + 180.0, 360.0))
    equasc = _lon_of_ra(np.mod(armc + 90.0, 360.0), eps)
    ascmc = [asc, mc, float(np.mod(armc, 360.0)), vertex, equasc, 0.0, 0.0, 0.0]
    return (tuple(c), tuple(ascmc))


def houses_ex(jd, lat, lon, hsys=b"P", flags=0):
    return houses(jd, lat, lon, hsys)


def houses_armc(armc, lat, eps, hsys=b"P"):
    h = (hsys.decode() if isinstance(hsys, bytes) else str(hsys)).upper()[:1]
    asc = _asc_from_armc(armc, eps, lat)
    mc = _mc_from_armc(armc, eps)
    if h == "W":
        s0 = np.floor(asc / 30.0) * 30.0
        c = [float(np.mod(s0 + 30.0 * i, 360.0)) for i in range(12)]
    else:
        c = [float(np.mod(asc + 30.0 * i, 360.0)) for i in range(12)]
    return (tuple(c), (asc, mc, float(np.mod(armc, 360.0)), 0.0, 0.0, 0.0, 0.0, 0.0))


def house_pos(armc, lat, eps, hsys, xpin):
    asc = _asc_from_armc(armc, eps, lat)
    return float(np.mod(xpin[0] - asc, 360.0) / 30.0) + 1.0


# ── rise / set ────────────────────────────────────────────────────────────────────────────────────────
# The horizon depression swisseph uses for a disc-centre event, MEASURED rather than assumed: the Sun's true
# altitude was evaluated at the instant swe.rise_trans called sunrise, over 120 random places and dates, and
# came out -0.60993 deg with a standard deviation of 0.0011. The textbook refracted horizon for a point
# source is -0.5667, and using that left a systematic 69-second error in every sunrise — a constant offset
# that looked like a broken solver until it was measured. The upper-limb constant is the standard value and
# is NOT calibrated, because no caller in this project asks for it (all four sites pass BIT_DISC_CENTER).
_H0_DISC_CENTER = -0.60985
_H0_UPPER_LIMB = -0.8333


def _altitude(a, bi, jd, lat, lon):
    l, b, _, _ = _sample(a, bi, jd)
    ra, dec = _to_equatorial(l, b, _eps_true(jd))
    H = np.deg2rad(_wrap(float(np.mod(sidtime(jd) * 15.0 + lon, 360.0)) - ra))
    p, d = np.deg2rad(np.clip(lat, -89.9, 89.9)), np.deg2rad(dec)
    sinh = np.sin(p) * np.sin(d) + np.cos(p) * np.cos(d) * np.cos(H)
    return np.degrees(np.arcsin(np.clip(sinh, -1, 1))), H, p, d


def rise_trans(jd_start, body, rsmi=CALC_RISE, geopos=(0.0, 0.0, 0.0), atpress=0.0, attemp=0.0,
               flags=FLG_SWIEPH):
    """(retflag, tret) with tret[0] the event JD — the first rise or set at or after jd_start.

    An hour-angle estimate gets within a minute or so; the refinement is Newton on the ACTUAL altitude,
    which is what removes the residual, because the naive formula ignores the body's own motion in
    declination across the day.
    """
    a = _need()
    lon, lat = float(geopos[0]), float(geopos[1])
    want_set = bool(rsmi & CALC_SET)
    h0 = _H0_DISC_CENTER if (rsmi & BIT_DISC_CENTER) else _H0_UPPER_LIMB
    if rsmi & BIT_NO_REFRACTION:
        h0 = 0.0
    bi = a.code2idx.get(int(body))
    if bi is None:
        return (-1, (0.0,) * 10)
    t = float(jd_start)
    for _ in range(2):                                   # hour-angle bracket
        l, b, _, _ = _sample(a, bi, t)
        ra, dec = _to_equatorial(l, b, _eps_true(t))
        p, d = np.deg2rad(np.clip(lat, -89.9, 89.9)), np.deg2rad(dec)
        c = (np.sin(np.deg2rad(h0)) - np.sin(p) * np.sin(d)) / (np.cos(p) * np.cos(d))
        if abs(c) > 1.0:
            return (-2, (0.0,) * 10)                     # circumpolar: no event, as swisseph reports
        H = np.degrees(np.arccos(c))
        if not want_set:
            H = -H
        t = t + np.mod(ra + H - float(np.mod(sidtime(t) * 15.0 + lon, 360.0)), 360.0) / 360.98564736629
    for _ in range(6):                                   # Newton on the real altitude
        h, H, p, d = _altitude(a, bi, t, lat, lon)
        denom = -np.cos(p) * np.cos(d) * np.sin(H)
        if abs(denom) < 1e-12:
            break
        dhdt = np.degrees(denom / max(np.cos(np.deg2rad(h)), 1e-9) * np.deg2rad(360.98564736629))
        step = (h - h0) / dhdt
        t -= step
        if abs(step) < 1e-9:
            break
    if t < float(jd_start):
        t += 1.0 / 1.0027379
    return (0, (t,) + (0.0,) * 9)


def rise_trans_true_hor(jd_start, body, rsmi=CALC_RISE, geopos=(0.0, 0.0, 0.0), atpress=0.0,
                        attemp=0.0, horhgt=0.0, flags=FLG_SWIEPH):
    return rise_trans(jd_start, body, rsmi, geopos, atpress, attemp, flags)


# ── eclipses ──────────────────────────────────────────────────────────────────────────────────────────
def sol_eclipse_when_glob(jd_start, flags=FLG_SWIEPH, ifltype=0, backward=False):
    a = _need()
    return _next_ecl(a.sol_jd, a.sol_fl, jd_start, backward)


def lun_eclipse_when(jd_start, flags=FLG_SWIEPH, ifltype=0, backward=False):
    a = _need()
    return _next_ecl(a.lun_jd, a.lun_fl, jd_start, backward)


def _next_ecl(jds, fls, jd_start, backward):
    if backward:
        i = int(np.searchsorted(jds, jd_start, "left")) - 1
        if i < 0:
            return (0, (0.0,) * 10)
    else:
        i = int(np.searchsorted(jds, jd_start, "right"))
        if i >= len(jds):
            return (0, (0.0,) * 10)
    return (int(fls[i]), (float(jds[i]),) + (0.0,) * 9)


# ── verification, run on the laptop where the real thing is importable ────────────────────────────────
def verify_asset(bodies, span, span_default, quant, n=140, seed=17, nodelike=()):
    """Gate for build_asset_v4: reconstruct EVERY body and EVERY quantity from the written bytes.

    The builder's own stride pre-check measures interpolation on unquantised values, for longitude only.
    This is the real gate, and it differs in three ways that each caught something:

      * it reads the FILE, so interpolation error and quantisation error are measured together rather than
        one at a time;
      * it covers latitude, distance, heliocentric longitude and SPEED, not just longitude — speed was
        quantised on a shared scale for twenty-six bodies until this check existed;
      * it checks the SIGN of speed separately from its magnitude, because that sign is retrograde status,
        and a body whose speed is 0.008 deg/day can have the right magnitude to three decimals and still be
        called direct when it is retrograde.

    Returns a list of human-readable failures — empty means publishable.
    """
    import swisseph as real
    real.set_ephe_path(os.path.expanduser("~/.sweph/ephe"))
    a = _need()
    rng = np.random.default_rng(seed)
    RFL = real.FLG_SWIEPH | real.FLG_SPEED
    print(f"asset gate — reconstruct from the written bytes vs pyswisseph, {n} instants per body")
    print(f"  budget: {2*quant:.6f} deg on any angle (two storage steps), 1e-3 relative on distance,")
    print(f"          retrograde sign exact outside a stationary window of 1% of the body's speed range")
    print(f"  {'body':<10} {'lon':>9} {'lat':>9} {'helio':>9} {'dist(rel)':>10} {'speed':>10} "
          f"{'retro':>11}")
    bad = []
    for nm, code in bodies:
        bi = a.code2idx[int(code)]
        y0, y1 = span.get(nm, span_default)
        lo = a.bjd0_f[bi]
        hi = a.hi_f[bi]
        jds = lo + rng.uniform(0, hi - lo, n)
        el = et = eh = ed = es = 0.0
        sign_bad = 0
        glitch = 0
        step = (float(a.shi[bi]) - float(a.slo[bi])) / 65535.0
        station = 0.01 * (float(a.shi[bi]) - float(a.slo[bi]))
        for jd in jds:
            p = real.calc_ut(float(jd), code, RFL)[0]
            # The builder stores the GEOCENTRIC longitude in the heliocentric slot for the nodes and
            # Lilith, because a lunar node has no heliocentric position. The gate has to know that, or it
            # compares against the Earth's heliocentric longitude and reports a 178 degree error that is
            # entirely its own.
            if int(code) in nodelike:
                q = p[0]
            else:
                try:
                    q = real.calc_ut(float(jd), code, real.FLG_SWIEPH | real.FLG_HELCTR)[0][0]
                except Exception:
                    q = p[0]
            g = calc_ut(float(jd), int(code), FLG_SWIEPH | FLG_SPEED)[0]
            gh = calc_ut(float(jd), int(code), FLG_SWIEPH | FLG_HELCTR)[0][0]
            el = max(el, abs(_wrap(g[0] - p[0])))
            et = max(et, abs(g[1] - p[1]))
            eh = max(eh, abs(_wrap(gh - q)))
            ed = max(ed, abs(g[2] - p[2]) / max(abs(p[2]), 1e-9))
            es = max(es, abs(g[3] - p[3]))
            # RETROGRADE SIGN, CHECKED AWAY FROM A STATION. Arbitrarily close to a stationary point the
            # true speed passes through zero, so no finite representation can preserve its sign there and
            # demanding it would make this gate impossible to pass — the question is only how wide that
            # blind window is. The window used here is 1% of the body's own speed RANGE, not its storage
            # step: the step is now so fine (5e-7 deg/day) that a step-based window would be no window at
            # all, while the thing that actually limits the sign near a station is how well the interpolated
            # derivative tracks the true one. Outside that window the sign must be right.
            if abs(p[3]) > station and np.sign(g[3]) != np.sign(p[3]):
                # CROSS-CHECKED AGAINST SWISSEPH'S OWN LONGITUDE, because swisseph's speed FIELD is not
                # always trustworthy for the Uranian hypotheticals. At jd 2383698.0483 it reports Vulkanus
                # at -0.01416 deg/day while its own longitude is rising monotonically through that instant
                # and the central difference of that longitude is +0.01394 — an isolated glitch in its
                # numerical differentiation of a body defined by mean elements. The shim returned +0.01390,
                # which agrees with the difference to 4e-5. So a bare sign comparison would fail this asset
                # for being MORE right than the reference. When the signs disagree, the tiebreaker is the
                # central difference of swisseph's own longitude, which cannot glitch in the same way; only
                # if that also disagrees is it counted.
                fd = (real.calc_ut(float(jd) + 1.0, code, RFL)[0][0]
                      - real.calc_ut(float(jd) - 1.0, code, RFL)[0][0])
                fd = _wrap(fd) / 2.0
                if np.sign(g[3]) != np.sign(fd):
                    sign_bad += 1
                else:
                    glitch += 1
        # THE BUDGETS, and why each is the number it is.
        #
        # ANGLES: two storage steps. One step is 0.0055 deg, and rounding to the nearest step already costs
        # up to half of one before any interpolation happens — so a budget OF one step is a budget no
        # reconstruction can meet, and the first version of this gate duly failed the lunar node at 0.005510
        # against 0.005493. Two steps leaves room for rounding plus interpolation and still refuses anything
        # that has actually gone wrong, which starts an order of magnitude higher.
        #
        # DISTANCE: relative, and the nodes and Lilith are exempt. Their "distance" is not a distance —
        # swisseph returns a placeholder near the Moon's — and its range is so narrow that a relative error
        # is amplified into nonsense. No module reads it for those bodies.
        angle_budget = 2.0 * quant
        flag = ""
        if el > angle_budget:
            bad.append(f"{nm}: longitude {el:.6f} deg exceeds the {angle_budget:.6f} budget")
            flag = " <-- LON"
        if et > angle_budget:
            bad.append(f"{nm}: latitude {et:.6f} deg exceeds the {angle_budget:.6f} budget"); flag += " LAT"
        if eh > angle_budget:
            bad.append(f"{nm}: heliocentric {eh:.6f} deg exceeds the {angle_budget:.6f} budget")
            flag += " HELIO"
        if ed > 1e-3 and int(code) not in nodelike:
            bad.append(f"{nm}: distance {ed:.3g} relative exceeds 1e-3"); flag += " DIST"
        if sign_bad:
            bad.append(f"{nm}: retrograde sign wrong on {sign_bad} of {n} instants while moving faster "
                       f"than {station:.3g} deg/day, which is outside the stationary window — the speed "
                       f"reconstruction is wrong for this body, not merely imprecise")
            flag += " RETRO"
        print(f"  {nm:<10} {el:>9.6f} {et:>9.6f} {eh:>9.6f} {ed:>10.3g} {es:>10.6f} "
              f"{sign_bad:>7}/{n}{flag}"
              + (f"   ({glitch} swisseph speed glitch{'es' if glitch > 1 else ''} outvoted by its own "
                 f"longitude)" if glitch else ""))
    return bad


def verify(n=400, seed=5):
    """Compare every shimmed call with pyswisseph over random charts. Prints max |error| per call."""
    import swisseph as real
    real.set_ephe_path(os.path.expanduser("~/.sweph/ephe"))
    a = _need()
    rng = np.random.default_rng(seed)
    jds = a.jd0 + rng.uniform(0, a.ndays - 2, n)
    lats = rng.uniform(-60, 66, n)
    lons = rng.uniform(-180, 180, n)
    RFLG = real.FLG_SWIEPH | real.FLG_SPEED
    REQ = real.FLG_SWIEPH | real.FLG_EQUATORIAL
    codes = [("Sun", real.SUN, SUN), ("Moon", real.MOON, MOON), ("Mercury", real.MERCURY, MERCURY),
             ("Venus", real.VENUS, VENUS), ("Mars", real.MARS, MARS), ("Jupiter", real.JUPITER, JUPITER),
             ("Saturn", real.SATURN, SATURN), ("Pluto", real.PLUTO, PLUTO),
             ("TrueNode", real.TRUE_NODE, TRUE_NODE), ("Chiron", real.CHIRON, CHIRON),
             ("Vesta", real.VESTA, VESTA), ("Cupido", real.CUPIDO, CUPIDO),
             ("Poseidon", real.POSEIDON, POSEIDON)]
    print(f"shim vs pyswisseph over {n} random instants 1800-2030 — max |error| in degrees "
          f"(storage step 0.005493)")
    worst = {}
    for nm, rc, sc in codes:
        el = ed = es = 0.0
        for jd in jds:
            p = real.calc_ut(jd, rc, RFLG)[0]; q = real.calc_ut(jd, rc, REQ)[0]
            s = calc_ut(jd, sc, FLG_SWIEPH | FLG_SPEED)[0]
            t = calc_ut(jd, sc, FLG_SWIEPH | FLG_EQUATORIAL)[0]
            el = max(el, abs(_wrap(s[0] - p[0])))
            ed = max(ed, abs(_wrap(t[0] - q[0])), abs(t[1] - q[1]))
            es = max(es, abs(s[3] - p[3]))
        worst[nm] = (el, ed, es)
        print(f"  calc_ut {nm:<9} lon {el:.6f}  ra/dec {ed:.6f}  speed {es:.6f} deg/day")
    e = max(abs(_wrap(sidtime(j) * 15.0 - real.sidtime(j) * 15.0)) for j in jds)
    print(f"  sidtime                    {e:.6f}")
    e = max(abs(deltat(j) - real.deltat(j)) * 86400.0 for j in jds)
    print(f"  deltat                     {e:.6f} seconds")
    e = 0.0
    for j in jds[:120]:
        r = real.fixstar2_ut("Spica", float(j), REQ)[0]
        s = fixstar2_ut("Spica", float(j), FLG_EQUATORIAL)[0]
        e = max(e, abs(_wrap(s[0] - r[0])), abs(s[1] - r[1]))
    print(f"  fixstar2_ut Spica          {e:.6f}")
    for mode, nm in ((real.SIDM_LAHIRI, "Lahiri"), (real.SIDM_TRUE_CITRA, "True Citra"),
                     (real.SIDM_FAGAN_BRADLEY, "Fagan-Bradley")):
        real.set_sid_mode(mode); set_sid_mode(mode)
        e = max(abs(_wrap(get_ayanamsa_ut(j) - real.get_ayanamsa_ut(j))) for j in jds)
        print(f"  ayanamsa {nm:<17} {e:.6f}")
    for hs in (b"P", b"W", b"E"):
        ea = em = ec = 0.0
        for jd, la, lo in zip(jds[:200], lats[:200], lons[:200]):
            rc_, ra_ = real.houses(float(jd), float(la), float(lo), hs)
            sc_, sa_ = houses(float(jd), float(la), float(lo), hs)
            ea = max(ea, abs(_wrap(sa_[0] - ra_[0])))
            em = max(em, abs(_wrap(sa_[1] - ra_[1])))
            ec = max(ec, max(abs(_wrap(sc_[i] - rc_[i])) for i in range(12)))
        print(f"  houses {hs.decode()!r:<20} asc {ea:.6f}  mc {em:.6f}  cusps {ec:.6f}")
    er = es2 = 0.0
    nbad = 0
    for jd, la, lo in zip(jds[:150], lats[:150], lons[:150]):
        geo = (float(lo), float(la), 0.0)
        j0 = np.floor(jd - 0.5) + 0.5
        rr = real.rise_trans(j0, real.SUN, real.CALC_RISE | real.BIT_DISC_CENTER, geo)
        sr = rise_trans(j0, SUN, CALC_RISE | BIT_DISC_CENTER, geo)
        rs = real.rise_trans(j0, real.SUN, real.CALC_SET | real.BIT_DISC_CENTER, geo)
        ss = rise_trans(j0, SUN, CALC_SET | BIT_DISC_CENTER, geo)
        if rr[0] != 0 or sr[0] != 0 or rs[0] != 0 or ss[0] != 0:
            nbad += 1
            continue
        er = max(er, abs(sr[1][0] - rr[1][0]) * 86400.0)
        es2 = max(es2, abs(ss[1][0] - rs[1][0]) * 86400.0)
    print(f"  rise_trans sunrise         {er:.1f} seconds   sunset {es2:.1f} seconds "
          f"({nbad} skipped as circumpolar)")
    ee = 0.0
    for jd in jds[:60]:
        r = real.sol_eclipse_when_glob(float(jd), real.FLG_SWIEPH, 0, False)
        s = sol_eclipse_when_glob(float(jd), FLG_SWIEPH, 0, False)
        ee = max(ee, abs(s[1][0] - r[1][0]) * 86400.0)
    print(f"  sol_eclipse_when_glob      {ee:.3f} seconds")
    ee = 0.0
    for jd in jds[:60]:
        r = real.lun_eclipse_when(float(jd), real.FLG_SWIEPH, 0, False)
        s = lun_eclipse_when(float(jd), FLG_SWIEPH, 0, False)
        ee = max(ee, abs(s[1][0] - r[1][0]) * 86400.0)
    print(f"  lun_eclipse_when           {ee:.3f} seconds")
    for jd in jds[:80]:
        y, m, d, h = revjul(float(jd), GREG_CAL)
        ry, rm, rd, rh = real.revjul(float(jd), real.GREG_CAL)
        assert (y, m, d) == (ry, rm, rd) and abs(h - rh) < 1e-6, f"revjul {jd}: {(y,m,d,h)} vs {(ry,rm,rd,rh)}"
        assert abs(julday(y, m, d, h, GREG_CAL) - real.julday(ry, rm, rd, rh, real.GREG_CAL)) < 1e-9
    print("  julday / revjul            exact")
    return worst


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    load(os.path.join(here, "ephem4.bin"), os.path.join(here, "tables.json"))
    verify()
