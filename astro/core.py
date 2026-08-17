"""
core.py — the shared substrate every tradition module builds on.

ONE JOB: turn the couple list into a rich, cached ephemeris table plus leak-free splits, and expose it
through a stable contract so tradition modules never touch Swiss Ephemeris or the dataset themselves.

WHAT IS AVAILABLE, AND THE ONE HARD LIMIT

The dataset gives birth and wedding DATES, never times. Everything is therefore computed at 12:00 UT.
That has two consequences no amount of modelling can undo, and every module should know them:

  NO HOUSES, NO ASCENDANT, NO MIDHEAVEN. Those need a birth time and a birth place. Any tradition that
  rests on them (Placidus houses, whole-sign houses, the Ascendant lord, house-based Vedic charts) can
  only be approximated by a zodiacal proxy, and modules that do so must say so in their docstring.
  MOON UNCERTAINTY. The Moon moves 12-15 degrees a day, so its noon longitude carries roughly +-6
  degrees of error against the true birth moment. Sign-level lunar features are about half reliable;
  nakshatra-level (13 deg 20') features are worse. Use them, but do not expect precision from them.

SIX INSTANTS PER COUPLE, because several traditions need charts other than the three obvious ones:

  0 older partner's birth          3 older partner's SECONDARY PROGRESSION to the wedding (a day for a year)
  1 younger partner's birth        4 younger partner's secondary progression to the wedding
  2 the wedding                    5 the DAVISON chart: the true midpoint in time between the two births

EIGHTEEN BODIES, with real Swiss Ephemeris files (not Moshier), so the asteroids are available. Juno is
in the list deliberately: it is the asteroid traditionally read for marriage.

SIDEREAL IS FREE. A sidereal longitude is the tropical longitude minus the ayanamsa at that instant, so
storing the ayanamsa per instant per mode (a scalar) covers all 48 sidereal modes without recomputing a
single body position. `sidereal(mode)` does that arithmetic.

Usage from a tradition module:

    from core import load
    E = load()
    E.LON[i, b, k]     tropical longitude, degrees, instant-slot i in 0..5, body b, couple k
    E.build_matrix(...) helpers listed below

Every module exposes exactly:

    def build(E) -> dict[str, numpy.ndarray]      # name -> (n_couples, n_features), finite, float64
"""

import json
import os
import warnings
import numpy as np
import swisseph as swe
from astropy.time import Time
from erfa import ErfaWarning

warnings.simplefilter("ignore", ErfaWarning)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# Both paths are overridable so the identical module runs on Kaggle, where the checkout does not exist
# and everything arrives flat in one dataset directory (Kaggle serves only the dataset ROOT).
EPHE = os.environ.get("AQ_EPHE") or os.path.expanduser("~/.sweph/ephe")
swe.set_ephe_path(EPHE)
FLG = swe.FLG_SWIEPH | swe.FLG_SPEED
YR = 365.2425
CACHE = os.environ.get("AQ_EPHEM_CACHE") or os.path.join(HERE, "ephem-cache.npz")
COUPLES = os.environ.get("AQ_COUPLES") or os.path.join(ROOT, "research/data-divorce/with-kids.json")

# ── the bodies ──────────────────────────────────────────────────────────────────────────────────
BODIES = [
    ("Sun", swe.SUN), ("Moon", swe.MOON), ("Mercury", swe.MERCURY), ("Venus", swe.VENUS),
    ("Mars", swe.MARS), ("Jupiter", swe.JUPITER), ("Saturn", swe.SATURN), ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE), ("Pluto", swe.PLUTO), ("TrueNode", swe.TRUE_NODE),
    ("MeanNode", swe.MEAN_NODE), ("Lilith", swe.MEAN_APOG), ("Chiron", swe.CHIRON),
    ("Ceres", swe.CERES), ("Pallas", swe.PALLAS), ("Juno", swe.JUNO), ("Vesta", swe.VESTA),
]
NAME = [b[0] for b in BODIES]
IDX = {n: i for i, n in enumerate(NAME)}
NB = len(BODIES)
# the seven visible bodies of every pre-telescopic tradition
CLASSICAL = [IDX[n] for n in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")]
MODERN = [IDX[n] for n in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                           "Uranus", "Neptune", "Pluto")]
# sidereal periods in tropical years, for anything that needs a body's speed class
PERIOD = {"Sun": 1.0, "Moon": 0.0748, "Mercury": 0.2408, "Venus": 0.6152, "Mars": 1.881,
          "Jupiter": 11.862, "Saturn": 29.457, "Uranus": 84.02, "Neptune": 164.8, "Pluto": 248.0,
          "TrueNode": 18.6, "MeanNode": 18.6, "Lilith": 8.85, "Chiron": 50.4, "Ceres": 4.60,
          "Pallas": 4.62, "Juno": 4.36, "Vesta": 3.63}

# ── instant slots ───────────────────────────────────────────────────────────────────────────────
SLOT = {"older": 0, "younger": 1, "wedding": 2, "prog_older": 3, "prog_younger": 4, "davison": 5}
# When the dataset carries no marriage date (the DOB-only study), slots 2, 3 and 4 cannot mean what they
# say. Rather than fabricate a wedding they are all set to the DAVISON MIDPOINT — the true midpoint in time
# between the two births, which is a real and long-standing DOB-only relationship chart. So a block named
# for the wedding is, in that mode, reading the Davison chart, and E.HAS_WEDDING says which mode you are in.
# The three modules written specifically for the marriage date are skipped entirely; see MARRIAGE_MODULES.
MARRIAGE_MODULES = ("muhurta", "electional", "wedding_transits")
NSLOT = 6

# ── the sidereal modes worth having (name, swisseph constant) ───────────────────────────────────
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
AYA_NAME = [a[0] for a in AYANAMSAS]

DATE = lambda s: isinstance(s, str) and len(s) == 10 and s[0].isdigit() and s[4] == "-" and s[7] == "-"

# DEFAULT BIRTH TIME. No birth times exist in the data, so one has to be assumed, and the assumption is
# 08:00 — set by the operator 2026-08-12, replacing the earlier 10:00 and the noon before that. Where the
# birthplace longitude is known it is 08:00 LOCAL MEAN TIME at that birthplace — the clock time a person
# would have called eight in the morning at their own meridian — which is what makes a chart here comparable
# to a stated "8 am in Tehran". Where no coordinates exist it falls back to 08:00 UT and the `tzKnown` flag
# records which case a row is in, so nothing silently pretends to a precision it lacks.
#
# THE SAME VALUE MUST HOLD FOR TRAINING AND FOR INFERENCE. It is read here, once, and everything downstream
# — the pipeline, the shipped browser bundle, the candidate search — inherits it, so the two can never
# disagree about what hour a chart is cast for.
DEFAULT_HOUR = float(os.environ.get("AQ_BIRTH_HOUR", "8.0"))

# THE ACCEPTED BIRTH RANGE, in one place, because four other files have to agree with it: the ephemeris span
# in build_asset_v4.py brackets it by two years (several modules search outward from a birth date, so a birth
# on 1 January reaches into the previous December), trad_lunar_calendrical's Spica grid brackets it by one,
# runner.py refuses anything outside it rather than let core.load silently drop rows from the middle of a
# batch, and ship.py probes both ends before publishing.
#
# 1800 is where the dataset starts. A floor of 1900 was tried on 2026-08-12 and reverted the same day: it
# would have dropped 53,756 of 135,005 couples, and the dropped ones are 46.3% parents against 24.0% for
# those kept — so it removes the most separable part of the data along with the era confound, and the same
# stacked model measures 0.7012 there against 0.7311 on everything. Worth knowing which number is which.
YEAR_FLOOR = int(os.environ.get("AQ_YEAR_FLOOR", "1600"))
YEAR_CEIL = int(os.environ.get("AQ_YEAR_CEIL", "2026"))


def _hour_offset_days(lon):
    """Days to subtract from a UT timestamp to make DEFAULT_HOUR mean local mean time at longitude `lon`."""
    if lon is None:
        return 0.0
    try:
        return -float(lon) / 360.0          # 15 deg per hour == 1/360 of a day per degree
    except (TypeError, ValueError):
        return 0.0


class Ephem:
    """Everything a tradition module is allowed to need."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    # ── zodiac helpers ──────────────────────────────────────────────────────────────────────────
    def sidereal(self, mode):
        """Tropical minus the ayanamsa for `mode` (name or index) — a sidereal longitude table."""
        m = AYA_NAME.index(mode) if isinstance(mode, str) else mode
        return np.mod(self.LON - self.AYA[m][:, None, :], 360.0)

    def slot(self, arr, which):
        """Pick one instant slot out of a (NSLOT, NB, n) table -> (NB, n)."""
        return arr[SLOT[which]]

    # ── the unknown birth hour, marginalised over 12 two-hour slots ─────────────────────────────
    HOURS = 12
    # slot centres in hours UT: 01:00, 03:00, … 23:00 — the Chinese double-hour, which is also exactly
    # the resolution at which the birth time is being marginalised.
    HOUR_OFFSETS = (np.arange(HOURS) * 2 + 1 - 12.0) / 24.0          # days from 12:00 UT

    def hours(self, slot):
        """Longitudes at all 12 slot centres for one instant slot -> (NB, 12, n), degrees.

        Extrapolated from the noon longitude and its own speed rather than recomputed. That is not a
        shortcut taken on faith: measured against the real ephemeris over 400 dates x 12 slots, the worst
        error is 0.053 degrees for the Moon and under 0.021 for everything else. The quantity being
        repaired is the Moon's +-6 degree noon uncertainty, and a nakshatra is 13 degrees 20' wide, so an
        error two orders of magnitude smaller than either changes no boundary decision.
        """
        i = SLOT[slot] if isinstance(slot, str) else slot
        off = Ephem.HOUR_OFFSETS
        L = self.LON[i][:, None, :] + self.SPD[i][:, None, :] * off[None, :, None]
        return np.mod(L, 360.0)

    def soft_bins(self, slot, body, nbins, offset=None):
        """The fraction of the 12 possible birth hours that puts `body` in each of `nbins` equal bins.

        This is what marginalising actually buys. A noon chart says "the Moon is in Hasta"; this says
        "8 of the 12 hours put it in Hasta and 4 in Chitra", which is strictly more information and is
        honest about the ones it cannot decide.
        """
        L = self.hours(slot)[body]                                    # (12, n)
        if offset is not None:
            L = np.mod(L - offset, 360.0)
        idx = np.floor(L / (360.0 / nbins)).astype(int) % nbins
        n = L.shape[1]
        out = np.zeros((n, nbins))
        for h in range(Ephem.HOURS):
            out[np.arange(n), idx[h]] += 1.0
        return out / Ephem.HOURS

    @staticmethod
    def entropy(p):
        """Shannon entropy of each row of a distribution, in bits — how undecided the marginal is."""
        q = np.clip(p, 1e-12, 1.0)
        return -(q * np.log2(q)).sum(axis=1)

    @staticmethod
    def wrap(d):
        """Signed angular difference in (-180, 180]."""
        return (np.asarray(d) + 180.0) % 360.0 - 180.0

    @staticmethod
    def sep(a, b):
        """Absolute separation in [0, 180]."""
        return np.abs(Ephem.wrap(np.asarray(a) - np.asarray(b)))

    @staticmethod
    def circ(lon):
        """cos/sin pair for a longitude array, stacked on the last axis."""
        r = np.deg2rad(lon)
        return np.stack([np.cos(r), np.sin(r)], axis=-1)

    @staticmethod
    def orbkern(sepdeg, angle, width):
        """A Gaussian aspect kernel: 1 when exact, falling off over `width` degrees."""
        return np.exp(-0.5 * ((np.asarray(sepdeg) - angle) / width) ** 2)


def _instants(recs, has_wedding=True):
    """The six instants per couple, as julian days."""
    out = np.empty((NSLOT, len(recs)))
    for k, r in enumerate(recs):
        o, y = r["old"], r["yng"]
        dav = 0.5 * (o + y)                   # Davison: the real midpoint in time between the births
        m = r["tm"] if has_wedding else dav
        out[0, k] = o
        out[1, k] = y
        out[2, k] = m
        out[3, k] = (o + (m - o) / YR) if has_wedding else dav   # secondary progression, one day per year
        out[4, k] = (y + (m - y) / YR) if has_wedding else dav
        out[5, k] = dav
    return out


def load(force=False):
    """Load couples, compute or read the cached ephemeris, and return an Ephem."""
    raw = json.load(open(COUPLES))
    # A dataset with no marriage date at all is the DOB-only study: two birth dates and a child count.
    HAS_WED = any(DATE(r.get("start")) for r in raw[:2000])
    recs = []
    for r in raw:
        if not (DATE(r["aDob"]) and DATE(r["bDob"])):
            continue
        if HAS_WED and not DATE(r.get("start")):
            continue
        # 1200 is the Swiss Ephemeris floor for the files on hand, verified body by body. The previous
        # 1600 cut was discarding every medieval and Renaissance marriage for no astronomical reason.
        # In DOB-only mode there is no marriage date to bound; bound the BIRTH years instead, which is
        # what the ephemeris actually constrains.
        yrs = [int(r["aDob"][:4]), int(r["bDob"][:4])] + ([int(r["start"][:4])] if HAS_WED else [])
        if min(yrs) < YEAR_FLOOR or max(yrs) > YEAR_CEIL:
            continue
        hh = f"{int(DEFAULT_HOUR):02d}:{int(round((DEFAULT_HOUR % 1) * 60)):02d}"
        t1 = Time(r["aDob"] + " " + hh).jd + _hour_offset_days(r.get("aLon"))
        t2 = Time(r["bDob"] + " " + hh).jd + _hour_offset_days(r.get("bLon"))
        tm = (Time(r["start"] + " " + hh).jd) if HAS_WED else 0.5 * (t1 + t2)
        # A marriage with no recorded end is still running; that is not a reason to drop it here.
        dur = ((Time(r["end"] + " " + hh).jd - tm) / YR) if DATE(r.get("end")) else 0.0
        old, yng = (t1, t2) if t1 <= t2 else (t2, t1)
        pold, pyng = (r["a"], r["b"]) if t1 <= t2 else (r["b"], r["a"])
        if HAS_WED:
            ao, ay = (tm - old) / YR, (tm - yng) / YR
            if not (0 <= dur <= 80 and 14 <= ay <= 85 and 14 <= ao <= 90):
                continue
        else:
            # no marriage, so the only sanity check available is that the two were plausibly contemporary
            if abs(old - yng) / YR > 60:
                continue
        # TARGET: hasKids when the dataset states it (any children vs none), otherwise the >=2 rule the
        # earlier datasets were built for. Kept explicit so a file's own definition always wins.
        # A dataset's own label always wins: "label" (the child-success studies), then hasKids (any
        # children), then the >=2 rule the first datasets were built for.
        kk = int(r.get("kidsStrict", r.get("nKids", 0)))
        if "label" in r:
            yy = int(r["label"])
        elif "hasKids" in r:
            yy = int(r["hasKids"])
        else:
            yy = 1 if kk >= 2 else 0
        # Context travels with the couple: citizenship, sex and birthplace, keyed to the OLDER/YOUNGER
        # convention rather than the file's a/b order, so a feature never silently swaps partners.
        swap = not (t1 <= t2)
        g = (lambda ka, kb: r.get(kb if swap else ka))
        recs.append({"pold": pold, "pyng": pyng, "old": old, "yng": yng, "tm": tm, "k": kk, "y": yy,
                     "natO": g("aNatQ", "bNatQ") or g("aNatIso", "bNatIso") or [],
                     "natY": g("bNatQ", "aNatQ") or g("bNatIso", "aNatIso") or [],
                     "sexO": g("aSex", "bSex") or "", "sexY": g("bSex", "aSex") or "",
                     "latO": g("aLat", "bLat"), "lonO": g("aLon", "bLon"),
                     "latY": g("bLat", "aLat"), "lonY": g("bLon", "aLon"),
                     # PLACE OF BIRTH is the primary geography now: single-valued, coordinate-bearing and
                     # true at the moment of birth, unlike citizenship which is multi-valued and drifts.
                     "pobO": g("aPob", "bPob") or "", "pobY": g("bPob", "aPob") or "",
                     "pcoO": g("aPobCountry", "bPobCountry") or "",
                     "pcoY": g("bPobCountry", "aPobCountry") or "",
                     "resO": g("aGeoRes", "bGeoRes") or 0, "resY": g("bGeoRes", "aGeoRes") or 0,
                     # date precision and the width of the uncertainty window, in days
                     "tzO": 1 if g("aLon", "bLon") is not None else 0,
                     "tzY": 1 if g("bLon", "aLon") is not None else 0,
                     "precO": int(g("aPrec", "bPrec") or 11), "precY": int(g("bPrec", "aPrec") or 11),
                     "winO": float(g("aWin", "bWin") or 1), "winY": float(g("bWin", "aWin") or 1)})

    # PRECISION FILTER. The exhaustive Wikidata scrape keeps year- and month-precision dates, where a
    # year-precision value arrives as 1 January. Set AQ_MIN_PREC=11 to demand a real day on all three
    # dates; the default keeps everything and lets the caller decide.
    minp = int(os.environ.get("AQ_MIN_PREC") or 0)
    if minp:
        before = len(recs)
        recs = [r for r in recs
                if min(int(r.get("aPrec", 11)), int(r.get("bPrec", 11)), int(r.get("sPrec", 11))) >= minp]
        print(f"  precision filter >= {minp}: {len(recs):,} of {before:,} kept")

    # SUBSAMPLE. Materialising all 211 blocks needs about 28 GB at 100,000 couples, so the screening pass
    # runs on a seeded subsample and only the surviving blocks are recomputed at full scale. The subsample
    # is drawn by PERSON GROUP, not by row, so a couple is never split from its own partner's other
    # marriages — that would leak across the split boundary later.
    sub = int(os.environ.get("AQ_SUBSAMPLE") or 0)
    if sub and sub < len(recs):
        rng2 = np.random.default_rng(int(os.environ.get("AQ_SUBSAMPLE_SEED") or 7))
        keyof = [tuple(sorted((r["pold"], r["pyng"]))) for r in recs]
        uniq = sorted({k for k in keyof})
        pick = set(map(tuple, rng2.permutation(np.array(uniq, dtype=object).reshape(len(uniq), 2))[:sub]))
        recs = [r for r, k in zip(recs, keyof) if k in pick]
        print(f"  subsample: {len(recs):,} couples")

    # THE INPUT CONTRACT: TWO DATES AND NOTHING ELSE (operator instruction, 2026-08-12).
    #
    # Birthplaces are dropped here, at the single point where they enter, rather than by remembering not to
    # use them in nineteen separate modules. Everything downstream then takes its own place-free path,
    # because the module contract already required a "known" flag instead of an imputed coordinate: with no
    # coordinates there is no Ascendant, no Midheaven, no house cusp, no astrocartography line and no local
    # sidereal time, and the hour offset in _hour_offset_days collapses to zero so every chart is cast at
    # 08:00 UT rather than 08:00 local mean time. The two modules that are nothing BUT place
    # (astrocartography, houses) go all-constant and are dropped by the global prune.
    #
    # This also retires the second baseline. The signed distance gap between birthplaces was the spatial
    # twin of the signed age gap; with no birthplaces there is one permitted baseline again, the signed
    # subtraction of the two dates, which is where this project started.
    if os.environ.get("AQ_NO_PLACE") == "1":
        for r in recs:
            r["latO"] = r["lonO"] = r["latY"] = r["lonY"] = None
            r["tzO"] = r["tzY"] = 0
            r["resO"] = r["resY"] = 0
            r["pobO"] = r["pobY"] = r["pcoO"] = r["pcoY"] = ""
        print(f"  AQ_NO_PLACE: birthplaces dropped — inputs are the two birth dates only, 08:00 UT")

    # ROW COUNT PROBE. Writes the surviving record count and each row's two person keys, then stops —
    # before a single planetary position is computed. collect_chunked.py needs the post-filter row count to
    # decide its chunk boundaries, and computing 135,005 couples' ephemeris just to learn how many there are
    # would cost minutes and a gigabyte.
    dump = os.environ.get("AQ_DUMP_ROWS")
    if dump:
        json.dump({"n": len(recs),
                   "keys": [[r["pold"], r["pyng"]] for r in recs]}, open(dump, "w"))
        print(f"  AQ_DUMP_ROWS: wrote {len(recs):,} rows to {dump} and stopped before the ephemeris")
        raise SystemExit(0)

    # ROW INDEX. A file of integer indices into this record order, selecting the rows to build. It exists
    # because one tradition module emits 5,846 columns, which at 135,005 couples is 6.3 GB of float64 output
    # on a 17 GB machine — so the full run is built in chunks and concatenated. The indices are chosen by
    # collect_chunked.py, which partitions by PERSON GROUP rather than by row: a couple's group is computed
    # here by union-find over whatever records are present, so splitting a group across two chunks would
    # invent two groups where there is one and quietly leak a person across a CV fold boundary. Whole groups
    # per chunk means each chunk's own union-find reproduces the global grouping exactly.
    ridx = os.environ.get("AQ_ROW_INDEX")
    if ridx:
        keep_rows = np.load(ridx) if ridx.endswith(".npy") else np.array(json.load(open(ridx)), dtype=np.int64)
        before = len(recs)
        recs = [recs[i] for i in keep_rows]
        print(f"  row index {os.path.basename(ridx)}: {len(recs):,} of {before:,} rows")

    Yall = np.array([r["y"] for r in recs])
    if os.environ.get("AQ_BALANCE") == "1":
        rng = np.random.default_rng(20260809)
        pos, neg = np.where(Yall == 1)[0], np.where(Yall == 0)[0]
        if len(neg) > len(pos):
            keep = np.sort(np.concatenate([pos, rng.choice(neg, len(pos), replace=False)]))
        else:
            keep = np.sort(np.concatenate([rng.choice(pos, len(neg), replace=False), neg]))
        recs = [recs[i] for i in keep]
    n = len(recs)
    Y = np.array([r["y"] for r in recs], float)
    JD = _instants(recs, HAS_WED)

    if not HAS_WED:
        print("  DOB-ONLY MODE: no marriage date. Slots 'wedding', 'prog_older' and 'prog_younger' all "
              "carry the\n                 Davison midpoint chart, and the three marriage-date modules "
              "are skipped.")
    # NO CACHE AT ALL when AQ_NO_EPHEM_CACHE=1, which is how the browser runs. The cache below is validated
    # by SHAPE ALONE, so two batches with the same row count would collide and the second would be scored on
    # the first batch's planetary positions — every feature wrong, nothing raised. On the laptop each caller
    # passes its own AQ_EPHEM_CACHE path; in the browser, where a search scores equal-sized batches back to
    # back, that collision is the default case rather than a remote one. It is also what the operator asked
    # for on 2026-08-12: nothing cached, every position computed from the two dates on the spot.
    _nocache = os.environ.get("AQ_NO_EPHEM_CACHE") == "1"
    if os.path.exists(CACHE) and not force and not _nocache:
        z = np.load(CACHE, allow_pickle=False)
        if z["LON"].shape == (NSLOT, NB, n):
            return _mk(recs, Y, JD, z["LON"], z["LAT"], z["DIST"], z["SPD"], z["DEC"], z["RA"],
                       z["HELIO"], z["AYA"], HAS_WED,
                       z["ASC"] if "ASC" in z else None, z["MC"] if "MC" in z else None,
                       z["CUSP"] if "CUSP" in z else None, z["HOK"] if "HOK" in z else None)

    # HOUSES, at last. Every earlier phase of this project had to skip them: a house cusp needs a birth
    # TIME and a birth PLACE, and neither was available. Both now are — the default hour is 08:00 local mean
    # time and 53% of couples have coordinates for both partners — so the Ascendant, the Midheaven and the
    # twelve cusps become real quantities rather than a proxy. Where a place is unknown the cusps are left
    # at NaN and HOUSE_OK says so, so nothing silently invents a horizon.
    ASC = np.full((NSLOT, n), np.nan); MC = np.full((NSLOT, n), np.nan)
    CUSP = np.full((NSLOT, 12, n), np.nan)
    HOK = np.zeros((NSLOT, n), dtype=bool)
    LON = np.empty((NSLOT, NB, n)); LAT = np.empty_like(LON); DIST = np.empty_like(LON)
    SPD = np.empty_like(LON); DEC = np.empty_like(LON); RA = np.empty_like(LON)
    HELIO = np.empty_like(LON); AYA = np.empty((len(AYANAMSAS), NSLOT, n))
    # cache by rounded JD: many couples share a wedding year and the same day recurs
    seen = {}
    for s in range(NSLOT):
        for k in range(n):
            jd = float(JD[s, k])
            key = round(jd, 6)
            if key not in seen:
                col = np.empty((7, NB))
                for b, (_, code) in enumerate(BODIES):
                    p = swe.calc_ut(jd, code, FLG)[0]
                    col[0, b], col[1, b], col[2, b], col[3, b] = p[0], p[1], p[2], p[3]
                    q = swe.calc_ut(jd, code, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)[0]
                    col[4, b], col[5, b] = q[1], q[0]          # declination, right ascension
                    if code in (swe.TRUE_NODE, swe.MEAN_NODE, swe.MEAN_APOG):
                        col[6, b] = p[0]                        # no heliocentric sense; keep geocentric
                    else:
                        col[6, b] = swe.calc_ut(jd, code, swe.FLG_SWIEPH | swe.FLG_HELCTR)[0][0]
                ay = np.empty(len(AYANAMSAS))
                for m, (_, mc) in enumerate(AYANAMSAS):
                    swe.set_sid_mode(mc)
                    ay[m] = swe.get_ayanamsa_ut(jd)
                seen[key] = (col, ay)
            col, ay = seen[key]
            # the horizon for this slot: each partner's own birthplace, and the geographic MIDPOINT for the
            # derived charts, which is what a Davison chart is defined on
            if s == 0:
                la, lo = recs[k].get("latO"), recs[k].get("lonO")
            elif s == 1:
                la, lo = recs[k].get("latY"), recs[k].get("lonY")
            else:
                pa, pb = recs[k].get("latO"), recs[k].get("latY")
                qa, qb = recs[k].get("lonO"), recs[k].get("lonY")
                la = 0.5 * (pa + pb) if (pa is not None and pb is not None) else None
                lo = 0.5 * (qa + qb) if (qa is not None and qb is not None) else None
            if la is not None and lo is not None and np.isfinite(la) and np.isfinite(lo):
                try:
                    cu, asc = swe.houses(jd, float(la), float(lo), b"P")   # Placidus
                    CUSP[s, :, k] = cu[:12]
                    ASC[s, k], MC[s, k] = asc[0], asc[1]
                    HOK[s, k] = True
                except Exception:
                    pass
            LON[s, :, k], LAT[s, :, k], DIST[s, :, k], SPD[s, :, k] = col[0], col[1], col[2], col[3]
            DEC[s, :, k], RA[s, :, k], HELIO[s, :, k] = col[4], col[5], col[6]
            AYA[:, s, k] = ay
    if _nocache:
        return _mk(recs, Y, JD, LON, LAT, DIST, SPD, DEC, RA, HELIO, AYA, HAS_WED, ASC, MC, CUSP, HOK)
    np.savez_compressed(CACHE, LON=LON, LAT=LAT, DIST=DIST, SPD=SPD, DEC=DEC, RA=RA,
                        HELIO=HELIO, AYA=AYA, ASC=ASC, MC=MC, CUSP=CUSP, HOK=HOK)
    return _mk(recs, Y, JD, LON, LAT, DIST, SPD, DEC, RA, HELIO, AYA, HAS_WED, ASC, MC, CUSP, HOK)


def _mk(recs, Y, JD, LON, LAT, DIST, SPD, DEC, RA, HELIO, AYA, has_wed=True,
        ASC=None, MC=None, CUSP=None, HOK=None):
    n = len(recs)
    # ── person-disjoint groups, so no partner appears on both sides of a split ───────────────────
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for r in recs:
        union(r["pold"], r["pyng"])
        union(("c", r["pold"], r["pyng"]), r["pold"])
    groups = np.array([find(r["pold"]) for r in recs], dtype=object)
    _, gid = np.unique(groups.astype(str), return_inverse=True)
    natO = [[q for q in (r.get("natO") or []) if q] for r in recs]
    natY = [[q for q in (r.get("natY") or []) if q] for r in recs]
    nn = len(recs)
    return Ephem(ASC=ASC if ASC is not None else np.full((NSLOT, nn), np.nan),
                 MC=MC if MC is not None else np.full((NSLOT, nn), np.nan),
                 CUSP=CUSP if CUSP is not None else np.full((NSLOT, 12, nn), np.nan),
                 HOUSE_OK=(HOK if HOK is not None else np.zeros((NSLOT, nn), dtype=bool)).astype(float),
                 NAT_O=natO, NAT_Y=natY,
                 POB_O=np.array([r.get("pobO", "") for r in recs], dtype=object),
                 POB_Y=np.array([r.get("pobY", "") for r in recs], dtype=object),
                 PCO_O=np.array([r.get("pcoO", "") for r in recs], dtype=object),
                 PCO_Y=np.array([r.get("pcoY", "") for r in recs], dtype=object),
                 GEORES_O=np.array([r.get("resO", 0) for r in recs], float),
                 GEORES_Y=np.array([r.get("resY", 0) for r in recs], float),
                 TZ_O=np.array([r.get("tzO", 0) for r in recs], float),
                 TZ_Y=np.array([r.get("tzY", 0) for r in recs], float),
                 PREC_O=np.array([r.get("precO", 11) for r in recs], float),
                 PREC_Y=np.array([r.get("precY", 11) for r in recs], float),
                 WIN_O=np.array([r.get("winO", 1.0) for r in recs], float),
                 WIN_Y=np.array([r.get("winY", 1.0) for r in recs], float),
                 SEX_O=np.array([r.get("sexO", "") for r in recs], dtype=object),
                 SEX_Y=np.array([r.get("sexY", "") for r in recs], dtype=object),
                 LAT_O=np.array([np.nan if r.get("latO") is None else r["latO"] for r in recs], float),
                 LON_O=np.array([np.nan if r.get("lonO") is None else r["lonO"] for r in recs], float),
                 LAT_Y=np.array([np.nan if r.get("latY") is None else r["latY"] for r in recs], float),
                 LON_Y=np.array([np.nan if r.get("lonY") is None else r["lonY"] for r in recs], float),
                 HAS_WEDDING=has_wed, recs=recs, n=n, Y=Y, JD=JD, LON=LON, LAT=LAT, DIST=DIST, SPD=SPD, DEC=DEC,
                 RA=RA, HELIO=HELIO, AYA=AYA, gid=gid, NAME=NAME, IDX=IDX, NB=NB,
                 CLASSICAL=CLASSICAL, MODERN=MODERN, PERIOD=PERIOD, SLOT=SLOT, AYA_NAME=AYA_NAME)


if __name__ == "__main__":
    import time
    t0 = time.time()
    E = load()
    _s = json.load(open(COUPLES))[:5]
    lab = ("positive" if any("label" in r for r in _s)
           else "with children" if any("hasKids" in r for r in _s) else "with >=2 children")
    print(f"couples            {E.n:,}   ({int(E.Y.sum()):,} {lab}, {int(E.n-E.Y.sum()):,} without)")
    print(f"person groups      {len(set(E.gid.tolist())):,}  (leak-free splits are by group)")
    print(f"bodies             {E.NB}   {', '.join(E.NAME)}")
    print(f"instant slots      {E.LON.shape[0]}   {', '.join(E.SLOT)}")
    print(f"ayanamsas          {len(E.AYA_NAME)}")
    print(f"LON table          {E.LON.shape}   finite={np.isfinite(E.LON).all()}")
    print(f"built in           {time.time()-t0:.1f}s")
    # spot checks that would catch a wrong slot or a wrong frame
    o = E.LON[0, E.IDX["Sun"], 0]; w = E.LON[2, E.IDX["Sun"], 0]
    print(f"\nspot check couple 0: Sun at older's birth {o:.3f} deg, at wedding {w:.3f} deg")
    sid = E.sidereal("Lahiri")
    print(f"  Lahiri sidereal Sun at that birth {sid[0, E.IDX['Sun'], 0]:.3f} deg "
          f"(ayanamsa {E.AYA[E.AYA_NAME.index('Lahiri'), 0, 0]:.3f})")
    if E.HAS_WEDDING:
        prog = E.JD[3] - E.JD[0]
        age = (E.JD[2] - E.JD[0]) / YR
        print(f"  progression offset vs age in years: max |diff| {np.abs(prog - age).max():.2e} days")
        assert np.abs(prog - age).max() < 1e-6, "secondary progression must advance one day per year"
    else:
        # There is no wedding to progress to, so slots 2, 3 and 4 must all BE the Davison midpoint.
        for sl in (2, 3, 4):
            assert np.abs(E.JD[sl] - E.JD[5]).max() < 1e-9, f"slot {sl} must equal the Davison midpoint"
        print("  DOB-only: slots 2, 3, 4 all equal the Davison midpoint, as intended")
    d = E.sep(E.LON[0, E.IDX["Sun"]], E.LON[0, E.IDX["Moon"]])
    print(f"  Sun-Moon separation at births: min {d.min():.2f} max {d.max():.2f} (must be 0..180)")
    assert d.min() >= 0 and d.max() <= 180.0001
    print("\nOK")
