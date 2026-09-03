"""systems_minor-bodies.py — MINOR BODIES & POINTS the corpus does not yet hold, as CONTINUOUS pseudo-bodies.

Every system here is n == 0: fn(y, m, d, L) returns a SIDEREAL (Lahiri) longitude in degrees, [0, 360),
at 12:00 UT of the birth date. The corpus (phases.npz) already carries sun, moon, mercury, venus, mars,
jupiter, saturn, uranus, neptune, pluto, true_node, chiron, mean_lilith; nothing below duplicates one of
those, and a body that would be a constant offset from one of them (mean south node, mean perigee) is
deliberately left out — the fitted phase absorbs a constant offset, so it would be the same pseudo-body.

Interface: fn(y, m, d, L) with L = {"sun": deg, "moon": deg, ...} sidereal. Three sources, in order:
  1. L itself — if the caller already holds this body's sidereal longitude under the key in "key" below
     (e.g. a browser that batch-read the shim once), it is used as-is;
  2. PURE PYTHON, standard library only, where the maths allows it: the mean node (Meeus polynomial),
     Eris (Keplerian two-body from JPL Horizons osculating elements, validated below), the Sun-Moon and
     Venus-Mars midpoints / sums, the lunar phase angle;
  3. `import swisseph` for the bodies that need an ephemeris file (Ceres, Pallas, Juno, Vesta, Pholus,
     the osculating and interpolated lunar apogee/perigee, the eight Uranian points). In the browser the
     import resolves to docs/sweshim.py (sys.modules["swisseph"] = sweshim), whose ephem4.bin serves
     exactly the 26 bodies listed in docs/ephem4.json — the "shim" flag on each entry says whether it can.

SHIM COVERAGE (docs/ephem4.json bodies: Sun Moon Mercury Venus Mars Jupiter Saturn Uranus Neptune Pluto
TrueNode MeanNode Lilith Chiron Ceres Pallas Juno Vesta Cupido Hades Zeus Kronos Apollon Admetos
Vulkanus Poseidon; span 1598-2199):
  served      mb_ceres mb_pallas mb_juno mb_vesta mb_mean_node (also pure) and the eight mb_uranian_*
  pure        mb_mean_node mb_eris mb_sunmoon_midpoint mb_sunmoon_sum mb_lunar_phase
              mb_venusmars_midpoint mb_venusmars_sum — need no ephemeris at all
  NOT served  mb_pholus (16), mb_oscu_lilith (13), mb_intp_apogee (21), mb_intp_perigee (22): the shim's
              calc_ut raises for an ipl it does not hold. If one of these survives selection the asset
              must gain the body (build_ephem) or the browser must be handed the longitude via L.

SKIPPED, WITH THE REASON
  * Eris from swisseph: no s136199s.se1 in ~/ephe or ~/.sweph/ephe (tested 2026-09-03) — so Eris is the
    pure Keplerian body below instead, validated against 81 JPL Horizons of-date points 1600-2000 (worst case printed by verify()).
  * Sedna: no se90377s.se1 either; not in the lens; not added (a 11,400-year orbit is a constant).
  * Vertex, Ascendant, MC, Part of Fortune, house cusps: need a birth TIME and place — the corpus holds
    a date at 12:00 UT only.
  * mean south node (= mean node + 180), mean perigee (= mean apogee + 180), osculating perigee
    (= osculating apogee + 180): constant offsets of bodies present here or in the corpus.
  * a discrete 8-phase Moon: the continuous phase angle carries every harmonic of it; a quantisation of a
    body already in the bank is not a new body.
  * Earth (heliocentric charts): a different frame, not a point on the geocentric circle.

Angle-only, date-only, deterministic, no randomness, no network. Names are never read.
"""
import math

SLUG = "minor-bodies"


# ---------------------------------------------------------------- helpers
def jdn(y, m, d):
    """Julian Day Number at noon, proleptic Gregorian (Fliegel & Van Flandern 1968).
    JDN == the Julian Day at 12:00 UT, so it is also the JD_UT we evaluate every body at."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def ayanamsa(y):
    """Lahiri ayanamsa in degrees for a birth year (good to a few arcminutes)."""
    return 23.853 + 0.013971 * (y - 2000)


def _norm(x):
    x = math.fmod(x, 360.0)
    return x + 360.0 if x < 0 else x


def _sidereal_from_tropical(lon, y):
    return _norm(lon - ayanamsa(y))


def _from_L(L, key):
    """The caller's own longitude for this body, if it holds one (sidereal degrees), else None."""
    if not L:
        return None
    v = L.get(key)
    if v is None:
        return None
    v = float(v)
    if v != v:                      # NaN — treat as absent
        return None
    return _norm(v)


# ---------------------------------------------------------------- swisseph (real, or the browser shim)
_SWE = None
_EPHE_DIRS = ("~/ephe", "~/.sweph/ephe", "/usr/share/swisseph", "/usr/local/share/swisseph")


def _swe():
    """Lazy import: real pyswisseph on the laptop (ephemeris path set to the first directory that
    holds seas_18.se1), or whatever the browser installed under sys.modules['swisseph'] (sweshim)."""
    global _SWE
    if _SWE is None:
        import os
        import swisseph as swe
        if not hasattr(swe, "load"):                     # the real library, not the shim
            for p in _EPHE_DIRS:
                p = os.path.expanduser(p)
                if os.path.exists(os.path.join(p, "seas_18.se1")):
                    swe.set_ephe_path(p)
                    break
        _SWE = swe
    return _SWE


# swisseph body numbers (constants copied so a missing library still lets the table read)
_IPL = {
    "ceres": 17, "pallas": 18, "juno": 19, "vesta": 20, "pholus": 16,
    "oscu_lilith": 13, "intp_apogee": 21, "intp_perigee": 22, "mean_node": 10,
    "cupido": 40, "hades": 41, "zeus": 42, "kronos": 43,
    "apollon": 44, "admetos": 45, "vulkanus": 46, "poseidon": 47,
}
_FLG_SWIEPH, _FLG_SPEED = 2, 256


def _swe_body(key, y, m, d, L):
    v = _from_L(L, key)
    if v is not None:
        return v
    swe = _swe()
    lon = swe.calc_ut(float(jdn(y, m, d)), _IPL[key], _FLG_SWIEPH | _FLG_SPEED)[0][0]
    return _sidereal_from_tropical(lon, y)


def _mk_swe(key):
    def fn(y, m, d, L):
        return _swe_body(key, y, m, d, L)
    fn.__name__ = "mb_" + key
    return fn


# ---------------------------------------------------------------- pure: the mean lunar node
def mean_node_tropical(jd):
    """Mean ascending node of the Moon, tropical of date (Meeus, Astronomical Algorithms, ch. 47).
    T in Julian centuries from J2000; UT vs TT ignored (< 1e-4 deg over 1600-2000)."""
    T = (jd - 2451545.0) / 36525.0
    om = (125.0445479 - 1934.1362891 * T + 0.0020754 * T * T
          + T ** 3 / 467441.0 - T ** 4 / 60616000.0)
    return _norm(om)


def mb_mean_node(y, m, d, L):
    v = _from_L(L, "mean_node")
    if v is not None:
        return v
    return _sidereal_from_tropical(mean_node_tropical(jdn(y, m, d)), y)


# ---------------------------------------------------------------- pure: Eris, Keplerian two-body
# 136199 Eris: JPL Horizons osculating heliocentric elements, ecliptic + equinox J2000, one set every 20
# years 1600-2000 (Horizons has no Eris before 1599-12-11). A single ellipse drifts ~1 deg per 200 years
# from the Neptune perturbation; propagating from the NEAREST epoch keeps the two-body error at the
# <= 0.06 deg over 1600-2010 (verify() measures it against the 81-point of-date series below: 0.055 max). Before 1600 the
# 1600 set is extrapolated (the corpus reaches 1500) — no reference exists there; expect <= ~0.5 deg.
_ERIS_ELEMENTS = (
    # (epoch JD_TDB, e, a AU, i, Omega, omega, M0, n deg/day) — JPL Horizons, heliocentric ecliptic J2000, every 20 y 1600-2000
    (2305447.5, 0.4406777676108, 68.30218274172, 44.03885066638, 36.03787741376, 150.51486187339, 296.94276008605, 1.746032003855079e-03),
    (2312752.5, 0.4368908319861, 68.06309329601, 43.89017835581, 35.81563739502, 150.75980988465, 309.15126941123, 1.755240170797911e-03),
    (2320057.5, 0.4372292055683, 67.39643503699, 44.02610529511, 36.07042948221, 151.81502351671, 321.15620074622, 1.781347655280890e-03),
    (2327362.5, 0.4438656440918, 68.60525332960, 43.99433860869, 36.09041005243, 150.56143066265, 335.29807006949, 1.734474883821852e-03),
    (2334667.5, 0.4381163534520, 67.86567591096, 44.03856044494, 35.84659869206, 150.95158960567, 347.64569164185, 1.762904578379386e-03),
    (2341972.5, 0.4377948757091, 67.75180649651, 43.98641240241, 35.99657803092, 151.60952340606, 0.27703590492, 1.767350774969027e-03),
    (2349276.5, 0.4447264019081, 68.60726211798, 43.90747280468, 35.95887126701, 151.39088953375, 13.00105200392, 1.734398707465759e-03),
    (2356581.5, 0.4364238193978, 67.40320901547, 44.07160697056, 36.05338307973, 150.59294499639, 26.65044835538, 1.781079125614524e-03),
    (2363886.5, 0.4384770359754, 68.29758162184, 44.00554795987, 36.01968582638, 152.09730064300, 38.47695149865, 1.746208448709138e-03),
    (2371191.5, 0.4410936967908, 68.12812632935, 43.95341789634, 35.77138151078, 151.60959937759, 51.46213189246, 1.752727522490842e-03),
    (2378496.5, 0.4388471946018, 67.38897727750, 44.00040729355, 36.09578283057, 150.34426861650, 65.72504531163, 1.781643368996976e-03),
    (2385800.5, 0.4347869281435, 68.31410078358, 43.97446955350, 36.12394305393, 152.08160678883, 76.99101516014, 1.745575106055649e-03),
    (2393105.5, 0.4399646585252, 68.01376026440, 44.04667925560, 35.71029530467, 151.73256777906, 89.98385480471, 1.757150233231120e-03),
    (2400410.5, 0.4408680456429, 67.46620562418, 43.97612536209, 36.03963283868, 150.46419195061, 104.52787109052, 1.778585082541491e-03),
    (2407715.5, 0.4326590837105, 68.19616436332, 43.88903240562, 36.21461701295, 151.61131627868, 116.03630899928, 1.750105181770406e-03),
    (2415020.5, 0.4391947185026, 67.93909336183, 44.11973162485, 35.74296256768, 151.76340690726, 128.52591394177, 1.760047762485418e-03),
    (2422324.5, 0.4423607427973, 67.54443843864, 44.02332960422, 35.93870614679, 150.71834710021, 143.14270242664, 1.775495929200526e-03),
    (2429629.5, 0.4319856814284, 68.14199462456, 43.79302271312, 36.21583476387, 151.18140268197, 155.16882598238, 1.752192475651353e-03),
    (2436934.5, 0.4384220940102, 67.86905925510, 44.13994741146, 35.83054656359, 151.73849407053, 167.09961586835, 1.762772756045221e-03),
    (2444239.5, 0.4429179134057, 67.62178371791, 44.10758021137, 35.89085453059, 151.00089598336, 181.61033513204, 1.772450602414942e-03),
    (2451544.5, 0.4325025330795, 68.13996291965, 43.74048049505, 36.12853608789, 150.84504524521, 194.28883857280, 1.752270842980364e-03),
)


def _precession_lon(jd):
    """Accumulated general precession in longitude from J2000, degrees (Lieske 1979 / IAU 1976):
    5029.0966 T + 1.11113 T^2 - 0.000006 T^3 arcsec, T in Julian centuries."""
    T = (jd - 2451545.0) / 36525.0
    return (5029.0966 * T + 1.11113 * T * T - 0.000006 * T ** 3) / 3600.0


def _kepler(M, e):
    """Eccentric anomaly by Newton (radians). Deterministic, fixed iteration count."""
    E = M if e < 0.8 else math.pi
    for _ in range(40):
        E = E - (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
    return E


def _helio_xyz(a, e, i, Om, w, M):
    """Heliocentric ecliptic rectangular coordinates from Keplerian elements (degrees in, AU out)."""
    Mr = math.radians(_norm(M))
    E = _kepler(Mr, e)
    nu = 2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(E / 2.0), math.sqrt(1.0 - e) * math.cos(E / 2.0))
    r = a * (1.0 - e * math.cos(E))
    u = math.radians(w) + nu
    ci, si = math.cos(math.radians(i)), math.sin(math.radians(i))
    cO, sO = math.cos(math.radians(Om)), math.sin(math.radians(Om))
    cu, su = math.cos(u), math.sin(u)
    return (r * (cO * cu - sO * su * ci), r * (sO * cu + cO * su * ci), r * su * si)


def _earth_xyz(jd):
    """Earth-Moon barycentre from JPL's approximate Keplerian elements (3000 BC - 3000 AD table),
    ecliptic + equinox J2000. Good to ~0.001 AU here, far below what a body at 40-100 AU can feel."""
    T = (jd - 2451545.0) / 36525.0
    a = 1.00000018 - 0.00000003 * T
    e = 0.01673163 - 0.00003661 * T
    i = -0.00054346 - 0.01337178 * T
    Lm = 100.46691572 + 35999.37306329 * T
    wb = 102.93005885 + 0.31795260 * T
    Om = -5.11260389 - 0.24123856 * T
    return _helio_xyz(a, e, i, Om, wb - Om, Lm - wb)


def eris_lon_j2000(jd):
    """Geocentric ecliptic longitude of Eris, equinox J2000, degrees — Keplerian two-body from the
    element set whose epoch is nearest to jd."""
    el = min(_ERIS_ELEMENTS, key=lambda t: abs(t[0] - jd))
    epoch, e, a, i, Om, w, M0, n = el
    ex, ey, ez = _helio_xyz(a, e, i, Om, w, M0 + n * (jd - epoch))
    hx, hy, hz = _earth_xyz(jd)
    return _norm(math.degrees(math.atan2(ey - hy, ex - hx)))


def eris_lon_of_date(jd):
    return _norm(eris_lon_j2000(jd) + _precession_lon(jd))


def mb_eris(y, m, d, L):
    v = _from_L(L, "eris")
    if v is not None:
        return v
    jd = jdn(y, m, d)
    return _sidereal_from_tropical(eris_lon_of_date(jd), y)


# ---------------------------------------------------------------- pure: midpoints, sums, phase
def _need(L, key):
    v = _from_L(L, key)
    if v is None:
        raise KeyError(f"L lacks '{key}' (sidereal degrees) — required by this pseudo-body")
    return v


def _near_midpoint(a, b):
    """The midpoint on the SHORTER arc between two longitudes (the astrological midpoint)."""
    diff = _norm(b - a)
    if diff > 180.0:
        diff -= 360.0
    return _norm(a + diff / 2.0)


def mb_sunmoon_midpoint(y, m, d, L):
    """(sun + moon) / 2 on the shorter arc — the Sun/Moon midpoint (Ebertin's 'the marriage point')."""
    v = _from_L(L, "sunmoon_midpoint")
    return v if v is not None else _near_midpoint(_need(L, "sun"), _need(L, "moon"))


def mb_sunmoon_sum(y, m, d, L):
    """(sun + moon) mod 360 — the midpoint AXIS, doubled: unambiguous (no near/far choice); its k-th
    harmonic is the 2k-th of the midpoint. A sum, allowed as a pseudo-body."""
    v = _from_L(L, "sunmoon_sum")
    return v if v is not None else _norm(_need(L, "sun") + _need(L, "moon"))


def mb_lunar_phase(y, m, d, L):
    """Elongation moon - sun, 0..360: 0 new, 90 first quarter, 180 full, 270 last quarter."""
    v = _from_L(L, "lunar_phase")
    return v if v is not None else _norm(_need(L, "moon") - _need(L, "sun"))


def mb_venusmars_midpoint(y, m, d, L):
    """Venus/Mars midpoint on the shorter arc — beyond the lens, the other classical relationship
    midpoint; cheap and date-only, so tested rather than assumed."""
    v = _from_L(L, "venusmars_midpoint")
    return v if v is not None else _near_midpoint(_need(L, "venus"), _need(L, "mars"))


def mb_venusmars_sum(y, m, d, L):
    v = _from_L(L, "venusmars_sum")
    return v if v is not None else _norm(_need(L, "venus") + _need(L, "mars"))


# ---------------------------------------------------------------- the table
def _S(name, desc, fn, key, shim, pure):
    return {"name": name, "n": 0, "desc": desc, "fn": fn, "key": key, "shim": shim, "pure": pure}


SYSTEMS = [
    # the four main asteroids (swisseph seas_*.se1; shim: ephem4 holds all four)
    _S("mb_ceres", "Ceres (1), sidereal longitude at 12:00 UT; swisseph ipl 17", _mk_swe("ceres"), "ceres", True, False),
    _S("mb_pallas", "Pallas (2), sidereal longitude; swisseph ipl 18", _mk_swe("pallas"), "pallas", True, False),
    _S("mb_juno", "Juno (3), the marriage asteroid, sidereal longitude; swisseph ipl 19", _mk_swe("juno"), "juno", True, False),
    _S("mb_vesta", "Vesta (4), sidereal longitude; swisseph ipl 20", _mk_swe("vesta"), "vesta", True, False),
    # the centaur the corpus lacks (Chiron is already there)
    _S("mb_pholus", "Pholus (5145), sidereal longitude; swisseph ipl 16 — NOT in the shim asset", _mk_swe("pholus"), "pholus", False, False),
    # the mean node (true node is in the corpus) — pure polynomial, no ephemeris
    _S("mb_mean_node", "mean lunar ascending node, Meeus ch.47 polynomial, sidereal", mb_mean_node, "mean_node", True, True),
    # the other lunar apsides (mean apogee = mean_lilith is in the corpus)
    _S("mb_oscu_lilith", "osculating ('true') lunar apogee, sidereal; swisseph ipl 13 — NOT in the shim asset", _mk_swe("oscu_lilith"), "oscu_lilith", False, False),
    _S("mb_intp_apogee", "interpolated lunar apogee (Koch), sidereal; swisseph ipl 21 — NOT in the shim asset", _mk_swe("intp_apogee"), "intp_apogee", False, False),
    _S("mb_intp_perigee", "interpolated lunar perigee (Koch), sidereal; swisseph ipl 22 — NOT in the shim asset", _mk_swe("intp_perigee"), "intp_perigee", False, False),
    # Eris — no local ephemeris file, so a validated Keplerian two-body (pure Python)
    _S("mb_eris", "Eris (136199), Keplerian two-body from 21 Horizons element sets (every 20 y 1600-2000, nearest epoch), sidereal", mb_eris, "eris", True, True),
    # derived points from the longitudes already in L (pure)
    _S("mb_sunmoon_midpoint", "Sun/Moon midpoint on the shorter arc, sidereal", mb_sunmoon_midpoint, "sunmoon_midpoint", True, True),
    _S("mb_sunmoon_sum", "(sun + moon) mod 360 — the Sun/Moon midpoint axis doubled", mb_sunmoon_sum, "sunmoon_sum", True, True),
    _S("mb_lunar_phase", "lunar phase angle = moon - sun elongation, 0..360", mb_lunar_phase, "lunar_phase", True, True),
    _S("mb_venusmars_midpoint", "Venus/Mars midpoint on the shorter arc, sidereal (beyond the lens)", mb_venusmars_midpoint, "venusmars_midpoint", True, True),
    _S("mb_venusmars_sum", "(venus + mars) mod 360 — the Venus/Mars midpoint axis doubled (beyond the lens)", mb_venusmars_sum, "venusmars_sum", True, True),
    # the eight Uranian (Hamburg school) hypothetical points: swisseph built-in orbital elements; the shim holds all eight
    _S("mb_uranian_cupido", "Cupido (Hamburg school), sidereal; swisseph ipl 40", _mk_swe("cupido"), "cupido", True, False),
    _S("mb_uranian_hades", "Hades (Hamburg school), sidereal; swisseph ipl 41", _mk_swe("hades"), "hades", True, False),
    _S("mb_uranian_zeus", "Zeus (Hamburg school), sidereal; swisseph ipl 42", _mk_swe("zeus"), "zeus", True, False),
    _S("mb_uranian_kronos", "Kronos (Hamburg school), sidereal; swisseph ipl 43", _mk_swe("kronos"), "kronos", True, False),
    _S("mb_uranian_apollon", "Apollon (Hamburg school), sidereal; swisseph ipl 44", _mk_swe("apollon"), "apollon", True, False),
    _S("mb_uranian_admetos", "Admetos (Hamburg school), sidereal; swisseph ipl 45", _mk_swe("admetos"), "admetos", True, False),
    _S("mb_uranian_vulkanus", "Vulkanus (Hamburg school), sidereal; swisseph ipl 46", _mk_swe("vulkanus"), "vulkanus", True, False),
    _S("mb_uranian_poseidon", "Poseidon (Hamburg school), sidereal; swisseph ipl 47", _mk_swe("poseidon"), "poseidon", True, False),
]


# ---------------------------------------------------------------- smoke test + verification
SMOKE_DATES = [
    (1600, 1, 1), (1600, 2, 29), (1617, 11, 22), (1650, 7, 4), (1666, 6, 6), (1700, 3, 1),
    (1721, 12, 31), (1750, 5, 15), (1776, 7, 4), (1789, 7, 14), (1800, 2, 28), (1815, 6, 18),
    (1833, 3, 22), (1850, 10, 10), (1869, 11, 11), (1879, 3, 14), (1888, 8, 8), (1900, 2, 28),
    (1911, 11, 11), (1922, 2, 22), (1933, 3, 3), (1945, 8, 15), (1955, 2, 24), (1966, 6, 29),
    (1979, 3, 22), (1984, 12, 31), (1999, 9, 9), (2000, 1, 1), (2000, 12, 31),
]
BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
          "pluto", "true_node", "chiron", "mean_lilith"]

_ERIS_REF = [
    # JPL Horizons 136199 Eris, ObsEcLon: geocentric APPARENT ecliptic-OF-DATE longitude, 12:00 UT, every 5 y (fetched 2026-09-03)
    ((1600, 1, 15), 57.2173727), ((1605, 1, 15), 59.8992586), ((1610, 1, 15), 62.8306620),
    ((1615, 1, 15), 66.0453873), ((1620, 1, 15), 69.5806087), ((1625, 1, 15), 73.4901662),
    ((1630, 1, 15), 77.8393272), ((1635, 1, 15), 82.7497770), ((1640, 1, 15), 88.2693970),
    ((1645, 1, 15), 94.4780044), ((1650, 1, 15), 101.5385151), ((1655, 1, 15), 109.4441542),
    ((1660, 1, 15), 118.2230017), ((1665, 1, 15), 127.6909270), ((1670, 1, 15), 137.7060798),
    ((1675, 1, 15), 147.9435333), ((1680, 1, 15), 157.9927063), ((1685, 1, 15), 167.6237369),
    ((1690, 1, 15), 176.6639283), ((1695, 1, 15), 185.0290840), ((1700, 1, 15), 192.7635845),
    ((1705, 1, 15), 199.9067962), ((1710, 1, 15), 206.6155402), ((1715, 1, 15), 212.9359190),
    ((1720, 1, 15), 218.9526068), ((1725, 1, 15), 224.7826139), ((1730, 1, 15), 230.4160249),
    ((1735, 1, 15), 235.9364536), ((1740, 1, 15), 241.3418629), ((1745, 1, 15), 246.7018321),
    ((1750, 1, 15), 251.9956295), ((1755, 1, 15), 257.1902750), ((1760, 1, 15), 262.3324739),
    ((1765, 1, 15), 267.4040361), ((1770, 1, 15), 272.3580647), ((1775, 1, 15), 277.1980951),
    ((1780, 1, 15), 281.8996276), ((1785, 1, 15), 286.5163190), ((1790, 1, 15), 290.9293001),
    ((1795, 1, 15), 295.1797578), ((1800, 1, 15), 299.2692221), ((1805, 1, 15), 303.1811102),
    ((1810, 1, 15), 306.9329236), ((1815, 1, 15), 310.4936273), ((1820, 1, 15), 313.9137346),
    ((1825, 1, 15), 317.1849875), ((1830, 1, 15), 320.2656464), ((1835, 1, 15), 323.2142228),
    ((1840, 1, 15), 326.0189765), ((1845, 1, 15), 328.7228186), ((1850, 1, 15), 331.2683635),
    ((1855, 1, 15), 333.7068901), ((1860, 1, 15), 336.0496814), ((1865, 1, 15), 338.2843706),
    ((1870, 1, 15), 340.4242428), ((1875, 1, 15), 342.4754791), ((1880, 1, 15), 344.4609596),
    ((1885, 1, 15), 346.3683927), ((1890, 1, 15), 348.1881983), ((1895, 1, 15), 349.9660402),
    ((1900, 1, 15), 351.6719435), ((1905, 1, 15), 353.3272661), ((1910, 1, 15), 354.9286445),
    ((1915, 1, 15), 356.4940161), ((1920, 1, 15), 358.0137958), ((1925, 1, 15), 359.4806663),
    ((1930, 1, 15), 0.9262905), ((1935, 1, 15), 2.3344143), ((1940, 1, 15), 3.7115437),
    ((1945, 1, 15), 5.0569553), ((1950, 1, 15), 6.3758540), ((1955, 1, 15), 7.6814580),
    ((1960, 1, 15), 8.9442874), ((1965, 1, 15), 10.2038013), ((1970, 1, 15), 11.4454583),
    ((1975, 1, 15), 12.6705499), ((1980, 1, 15), 13.8729704), ((1985, 1, 15), 15.0621533),
    ((1990, 1, 15), 16.2588283), ((1995, 1, 15), 17.4301100), ((2000, 1, 15), 18.5958865),
]


def _absdiff(a, b):
    x = abs(_norm(a) - _norm(b))
    return min(x, 360.0 - x)


def smoke():
    checked = 0
    for (y, m, d) in SMOKE_DATES:
        L = {b: (i * 27.3 + y % 360 + m * 11.1 + d) % 360.0 for i, b in enumerate(BODIES)}
        for s in SYSTEMS:
            v = s["fn"](y, m, d, L)
            assert isinstance(v, float), (s["name"], y, m, d, v)
            assert 0.0 <= v < 360.0 and v == v, (s["name"], y, m, d, v)
            assert s["fn"](y, m, d, L) == v, (s["name"], "not deterministic")
            # the L-first path returns exactly what it is handed
            assert s["fn"](y, m, d, dict(L, **{s["key"]: 123.456})) == 123.456, (s["name"], "L-first")
            checked += 1
    assert jdn(2000, 1, 1) == 2451545 and jdn(1600, 1, 1) == 2305448
    assert _near_midpoint(350.0, 10.0) == 0.0 and _near_midpoint(10.0, 350.0) == 0.0
    assert _near_midpoint(0.0, 180.0) in (90.0, 270.0)
    assert _absdiff(mb_lunar_phase(0, 0, 0, {"sun": 350.0, "moon": 10.0}), 20.0) < 1e-9
    return checked


def verify():
    """Cross-checks that need the real swisseph / the embedded Horizons points. Returns a dict of
    worst-case errors in degrees."""
    out = {}
    # Eris vs Horizons: geocentric, ecliptic of date; the refs are APPARENT so ~0.006 deg of aberration remains
    out["eris_vs_horizons_max_deg"] = max(_absdiff(eris_lon_of_date(jdn(*ymd)), ref) for ymd, ref in _ERIS_REF)
    out["eris_ref_points"] = len(_ERIS_REF)
    # pure mean node vs swisseph MEAN_NODE (tropical, both at 12:00 UT)
    try:
        swe = _swe()
        out["mean_node_vs_swe_max_deg"] = max(
            _absdiff(mean_node_tropical(jdn(y, m, d)), swe.calc_ut(float(jdn(y, m, d)), 10, _FLG_SWIEPH)[0][0])
            for (y, m, d) in SMOKE_DATES)
        # helper ayanamsa vs swisseph Lahiri
        swe.set_sid_mode(1)                                   # SIDM_LAHIRI
        out["ayanamsa_helper_vs_swe_max_deg"] = max(
            abs(ayanamsa(y) - swe.get_ayanamsa_ut(float(jdn(y, m, d)))) for (y, m, d) in SMOKE_DATES)
    except ImportError:
        out["swisseph"] = "unavailable"
    return out


def build(D_, out_name="systems_minor-bodies.npz"):
    """Write AQ_DIR/<out_name> in build_systems.py's shape: theta_a_sys, theta_b_sys (degrees),
    names, nstates — one column per SYSTEMS entry, for every couple of full.csv, from phases.npz's
    own sidereal longitudes (so the derived points use exactly the corpus' sun/moon/venus/mars)."""
    import numpy as np
    import pandas as pd
    full = pd.read_csv(f"{D_}/full.csv", dtype=str)
    Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
    bodies = [str(b) for b in Z["bodies"]]

    def side(col, theta):
        rows = []
        for iso, row in zip(full[col], theta):
            y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
            L = {b: float(v) for b, v in zip(bodies, row)}
            rows.append([s["fn"](y, m, d, L) for s in SYSTEMS])
        return np.array(rows, np.float64)

    A = side("true_dob_a", Z["theta_a_train"])
    B = side("true_dob_b", Z["theta_b_train"])
    assert np.isfinite(A).all() and np.isfinite(B).all()
    np.savez_compressed(f"{D_}/{out_name}", theta_a_sys=A, theta_b_sys=B,
                        names=np.array([s["name"] for s in SYSTEMS]),
                        nstates=np.array([s["n"] for s in SYSTEMS]))
    return f"wrote {D_}/{out_name} · {len(SYSTEMS)} systems x {len(full):,} couples"


if __name__ == "__main__":
    import os
    import sys
    n = smoke()
    print(f"smoke ok: {len(SYSTEMS)} systems x {len(SMOKE_DATES)} dates = {n} states in range")
    print("verify:", verify())
    if "--build" in sys.argv:
        print(build(os.environ.get("AQ_DIR", os.path.expanduser("~/.artamatch-dev/tilldeath_wt3"))))
