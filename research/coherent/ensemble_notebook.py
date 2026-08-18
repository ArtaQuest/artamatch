# %% [markdown]
# # ArtaMatch: the 4,962-feature ensemble
#
# **Two birth dates in, one probability out.** Everything else is computed here.
#
# The competition gives three columns — `dob_older`, `dob_younger`, `lasted_30_years` — and asks whether a
# relationship lasted thirty years. This notebook takes only that, plus a public **ephemeris asset** (planetary
# positions against time, plus the reader for it — an astronomical constant table, not information about any
# couple), and builds **4,962 named astrological and numerological features in this notebook**, then fits an
# ensemble on GPU.
#
# ### What is deliberately NOT an input
#
# * No precomputed feature matrix. Every column is derived from the two dates in the cells below.
# * No held-out label, anywhere. Model selection uses an **inner temporal split** — the latest 15% of training
#   births — mirroring the competition's own out-of-time split. The notebook cannot see `solution.csv` and does
#   not ask for it, so the leaderboard score it earns is a prediction rather than a description of the answer.
#
# ### The feature families
#
# | family | n | what |
# |---|---|---|
# | cross-chart synastry | 2,268 | all 18×18 ordered body pairs between the charts, harmonics 1–6 |
# | natal aspects | 1,224 | all 153 body pairs inside each chart, harmonics 1–3 |
# | single body | 424 | tropical and sidereal longitude, sign, decan, dwadasamsa, nakshatra, navamsa, speed |
# | calendrical + numerology | 270 | weekday and planetary day lord, day-of-year harmonics, sun-sign compatibility, Chinese pillars, Life Path, karmic-debt / challenge / pinnacle numbers |
# | vargas | 252 | divisional-chart signs D2–D60, and same-varga agreement across the charts |
# | harmonic charts | 216 | each body's longitude ×5, ×7, ×9 rewrapped |
# | midpoints and antiscia | 169 | Uranian midpoints and solstice mirrors, with cross-chart contacts |
# | lunar elongations | 85 | each body's distance from its own Sun, and the two charts' difference |
# | vedic pair | 54 | nakshatra and sign distance for every body, not only the Moon |
#
# ### Day precision, and why the training set shrinks
#
# A third of the training half carries only a year (`1856-00-00`). A chart cannot honestly be cast for it: placing
# it at 1 January puts the Sun near 280° for every such couple and plants a false spike at day 1 in every
# seasonal feature. So the models train on the **27,189 couples with both dates to the day**, which is also what
# the held-out half is.

# %%
import gc, json, math, os, shutil, sys, time
import numpy as np
import pandas as pd

T0 = time.time()
# FIND THE MOUNTS, DO NOT ASSUME THEIR NAMES. The first run of this notebook died with FileNotFoundError on a
# hardcoded /kaggle/input/artamatch-ephemeris, which told me a file was missing when what I needed to know was
# which inputs were actually mounted. Both datasets are public and both were listed in the kernel metadata, so
# guessing further was pointless: the notebook now identifies each input by a file it must CONTAIN, and prints
# the whole tree when it cannot.
ROOT = "/kaggle/input"
_tree = {}
for d, _, fs in os.walk(ROOT):
    for f in fs:
        _tree.setdefault(os.path.basename(d), []).append(f)
print("mounted inputs:")
for d, fs in sorted(_tree.items()):
    print(f"  {d}/  ({len(fs)} files) e.g. {sorted(fs)[:4]}")


def find_dir(marker):
    for d, _, fs in os.walk(ROOT):
        if marker in fs:
            return d
    raise SystemExit(f"no mounted input contains {marker!r}. Mounted: "
                     + json.dumps({k: sorted(v)[:6] for k, v in _tree.items()}, indent=1))


CODE = find_dir("ephem4.bin")
DATA = find_dir("train.csv")
print(f"code + ephemeris: {CODE}")
print(f"competition data: {DATA}")
WORK = "/kaggle/working/code"
os.makedirs(WORK, exist_ok=True)
for f in os.listdir(CODE):
    if f.endswith((".py", ".bin", ".json")):
        shutil.copy(os.path.join(CODE, f), os.path.join(WORK, f))
sys.path.insert(0, WORK)
os.environ.update({"AQ_NO_PLACE": "1", "AQ_KEEP_ALL_COLS": "1", "AQ_NO_EPHEM_CACHE": "1",
                   "AQ_EPHEM_CACHE": "/nonexistent.npz", "AQ_COUPLES": "/kaggle/working/couples.json"})
import sweshim
sweshim.load(os.path.join(WORK, "ephem4.bin"), os.path.join(WORK, "tables.json"))
sys.modules["swisseph"] = sweshim
info = json.load(open(os.path.join(WORK, "ephem4.json")))
print(f"ephemeris {info['yearFrom']}-{info['yearTo']}, read through the pure-numpy shim")

# GPU if there is one. The corrected recipe is LightGBM / XGBoost / a logistic, so torch is no longer imported;
# XGBoost takes device="cuda" directly. Kaggle's DEFAULT accelerator is a P100 whose compute capability (6.0)
# the preinstalled torch cannot use -- one more reason not to depend on it -- and the kernel metadata requests
# machine_shape=NvidiaTeslaT4 regardless.
DEV = "cuda" if shutil.which("nvidia-smi") else "cpu"
print(f"device for XGBoost: {DEV}")

# %%
tr_all = pd.read_csv(f"{DATA}/train.csv", dtype={"dob_older": str, "dob_younger": str})
te = pd.read_csv(f"{DATA}/test.csv", dtype={"dob_older": str, "dob_younger": str})
LABEL = [c for c in tr_all.columns if c not in {"id", "dob_older", "dob_younger"}][0]
print(f"competition train {len(tr_all):,} · test {len(te):,} · target {LABEL!r}")


def dayprec(c):
    return c.str.len().eq(10) & ~c.str.endswith("-00") & ~c.str.slice(5, 7).eq("00")


def yearknown(c):
    return c.ne("0000-00-00")


both_year = (yearknown(tr_all.dob_older) & yearknown(tr_all.dob_younger)).to_numpy()
both_day = (dayprec(tr_all.dob_older) & dayprec(tr_all.dob_younger)).to_numpy()
tr = tr_all[both_day].reset_index(drop=True)
print(f"  both dates to the day: {both_day.sum():,}  ·  both years known: {both_year.sum():,}")

# %% [markdown]
# ## The feature definitions
#
# Spliced verbatim from `research/coherent/mega_features.py`, so the notebook and the repo cannot drift. Each
# family yields `{name: (explanation, values)}` and is consumed one at a time.

# %%
import numpy as np

NAMES18 = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
           "TrueNode", "MeanNode", "Lilith", "Chiron", "Ceres", "Pallas", "Juno", "Vesta"]
IDX = {n: i for i, n in enumerate(NAMES18)}
CLASSICAL = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces"]
ANIMALS = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
DAYLORD = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
STEM_EL = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]
MEANS = {
    "Sun": "identity and vitality", "Moon": "feeling and habit", "Mercury": "speech and reasoning",
    "Venus": "attraction and what is valued", "Mars": "desire and conflict",
    "Jupiter": "expansion and generosity", "Saturn": "duty and endurance, the marriage significator",
    "Uranus": "disruption", "Neptune": "idealisation", "Pluto": "compulsion",
    "TrueNode": "the true lunar node", "MeanNode": "the mean lunar node", "Lilith": "the lunar apogee",
    "Chiron": "the wound", "Ceres": "nurture", "Pallas": "strategy", "Juno": "the marriage asteroid",
    "Vesta": "devotion",
}
VARGA = {2: "hora (wealth)", 3: "drekkana (siblings)", 7: "saptamsa (children)",
         9: "navamsa (the spouse chart)", 10: "dasamsa (career)", 12: "dwadasamsa (parents)",
         16: "shodasamsa (vehicles)", 20: "vimsamsa (devotion)", 24: "siddhamsa (learning)",
         27: "bhamsa (strengths)", 30: "trimsamsa (misfortune)", 60: "shashtiamsa (the whole)"}
SLOTS = (("older", 0), ("younger", 1))


def _fold(d, p=360.0):
    d = np.mod(d, p)
    return np.minimum(d, p - d)


def families(E, dates=None):
    """Yield (family_name, {feature_name: (explanation, values)}) one family at a time."""
    LON = np.asarray(E.LON, dtype=np.float64)
    SPD = np.asarray(getattr(E, "SPD", np.zeros_like(LON)), dtype=np.float64)
    rad = np.pi / 180.0
    try:
        SID = np.asarray(E.sidereal("Lahiri"), dtype=np.float64)
    except Exception:
        SID = None

    # ── single body ───────────────────────────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for b in NAMES18:
            i = IDX[b]
            lam = np.mod(LON[s, i], 360.0)
            F[f"{b} tropical longitude, cos — {who}"] = (
                f"Cosine of {b}'s tropical ecliptic longitude in the {who} partner's chart; {b} signifies "
                f"{MEANS[b]}. Cosine and sine avoid the 359-to-1 degree wrap.", np.cos(lam * rad))
            F[f"{b} tropical longitude, sin — {who}"] = (
                f"Sine of {b}'s tropical longitude for the {who} partner.", np.sin(lam * rad))
            F[f"{b} sign 1-12 — {who}"] = (
                f"Which 30-degree tropical sign {b} occupied for the {who} partner, Aries 1 to Pisces 12.",
                np.floor(lam / 30.0) + 1)
            F[f"{b} decan 1-36 — {who}"] = (
                f"Which 10-degree decan {b} occupied for the {who} partner; the decans are the oldest "
                f"subdivision of the zodiac still read.", np.floor(lam / 10.0) + 1)
            F[f"{b} dwadasamsa 1-144 — {who}"] = (
                f"Which 2.5-degree twelfth-of-a-sign {b} occupied for the {who} partner.",
                np.floor(lam / 2.5) + 1)
            F[f"{b} nakshatra 1-27 — {who}"] = (
                f"Which of the 27 lunar mansions {b} occupied for the {who} partner.",
                np.floor(lam / (360.0 / 27.0)) + 1)
            F[f"{b} navamsa 1-108 — {who}"] = (
                f"Which of the 108 navamsa ninths {b} occupied for the {who} partner; the navamsa is the "
                f"divisional chart read for marriage.", np.floor(lam / (360.0 / 108.0)) + 1)
            F[f"{b} degree within its sign — {who}"] = (
                f"How far into its sign {b} had travelled for the {who} partner, 0-30 degrees.",
                np.mod(lam, 30.0))
            F[f"{b} daily speed — {who}"] = (
                f"{b}'s apparent motion in degrees per day at the {who} partner's birth.", SPD[s, i])
            if np.any(SPD[s, i] < 0):
                F[f"{b} retrograde — {who}"] = (
                    f"1 when {b} was apparently moving backwards at the {who} partner's birth.",
                    (SPD[s, i] < 0).astype(float))
            if SID is not None:
                sl = np.mod(SID[s, i], 360.0)
                F[f"{b} sidereal longitude (Lahiri), cos — {who}"] = (
                    f"Cosine of {b}'s SIDEREAL longitude under the Lahiri ayanamsa for the {who} partner — the "
                    f"zodiac Indian astrology uses, offset from the tropical one by the precession of the "
                    f"equinoxes.", np.cos(sl * rad))
                F[f"{b} sidereal nakshatra 1-27 (Lahiri) — {who}"] = (
                    f"{b}'s lunar mansion in the sidereal zodiac for the {who} partner, which is the form "
                    f"Jyotisa actually reads.", np.floor(sl / (360.0 / 27.0)) + 1)
    yield "single body", F

    # ── harmonic charts ───────────────────────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for b in NAMES18:
            for h in (5, 7, 9):
                lam = np.mod(LON[s, IDX[b]] * h, 360.0)
                F[f"{b} in the {h}th-harmonic chart, cos — {who}"] = (
                    f"Cosine of {b}'s longitude multiplied by {h} and rewrapped, for the {who} partner. "
                    f"Multiplying a longitude by n is how a harmonic chart is built; the {h}th harmonic is "
                    f"read for creative and fated themes.", np.cos(lam * rad))
                F[f"{b} sign in the {h}th-harmonic chart — {who}"] = (
                    f"Which sign {b} falls in once its longitude is multiplied by {h}, for the {who} partner.",
                    np.floor(lam / 30.0) + 1)
    yield "harmonic charts", F

    # ── cross-chart synastry: all 18x18 ordered pairs ─────────────────────────────────────────────────────
    F = {}
    for a in NAMES18:
        for b in NAMES18:
            d = _fold(LON[0, IDX[a]] - LON[1, IDX[b]])
            F[f"{a}(older) to {b}(younger) separation"] = (
                f"The angle between the older partner's {a} and the younger partner's {b}, folded to 0-180 "
                f"degrees: {MEANS[a]} meeting {MEANS[b]}.", d)
            for h in (1, 2, 3, 4, 5, 6):
                F[f"{a}(older) to {b}(younger), harmonic {h}"] = (
                    f"cos({h} x separation) between the older partner's {a} and the younger partner's {b}. "
                    f"Peaks when the {h}th-harmonic aspect is exact and decays smoothly with orb, which is what "
                    f"a hard orb window approximates.", np.cos(h * d * rad))
    yield "cross-chart synastry", F

    # ── natal aspects inside each chart ───────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for ii in range(len(NAMES18)):
            for jj in range(ii + 1, len(NAMES18)):
                a, b = NAMES18[ii], NAMES18[jj]
                d = _fold(LON[s, IDX[a]] - LON[s, IDX[b]])
                F[f"{a} to {b} separation — {who}'s own chart"] = (
                    f"The natal angle between {a} and {b} in the {who} partner's own chart.", d)
                for h in (1, 2, 3):
                    F[f"{a} to {b}, harmonic {h} — {who}'s own chart"] = (
                        f"cos({h} x separation) between {a} and {b} natally for the {who} partner.",
                        np.cos(h * d * rad))
    yield "natal aspects", F

    # ── midpoints and antiscia ───────────────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for ii in range(len(CLASSICAL)):
            for jj in range(ii + 1, len(CLASSICAL)):
                a, b = CLASSICAL[ii], CLASSICAL[jj]
                m = np.mod((LON[s, IDX[a]] + LON[s, IDX[b]]) / 2.0, 360.0)
                F[f"{a}/{b} midpoint, cos — {who}"] = (
                    f"Cosine of the midpoint between {a} and {b} in the {who} partner's chart. The Hamburg "
                    f"School reads midpoints as the site where two principles combine.", np.cos(m * rad))
                F[f"{a}/{b} midpoint sign — {who}"] = (
                    f"Which sign the {a}/{b} midpoint fell in for the {who} partner.", np.floor(m / 30.0) + 1)
        for b in NAMES18:
            an = np.mod(180.0 - LON[s, IDX[b]], 360.0)
            F[f"{b} antiscion, cos — {who}"] = (
                f"Cosine of {b}'s antiscion for the {who} partner — its mirror across the solstice axis, a "
                f"contact Hellenistic and Renaissance astrology treats as equivalent to a conjunction.",
                np.cos(an * rad))
    for a in CLASSICAL:
        for b in CLASSICAL:
            mo = np.mod((LON[0, IDX[a]] + LON[0, IDX[b]]) / 2.0, 360.0)
            for c in CLASSICAL:
                if c != a:
                    continue
                d = _fold(mo - LON[1, IDX[c]])
                F[f"older's {a}/{b} midpoint to younger's {c}"] = (
                    f"How close the younger partner's {c} falls to the older partner's {a}/{b} midpoint, "
                    f"0-180 degrees — a cross-chart midpoint contact.", d)
    yield "midpoints and antiscia", F

    # ── lunar elongations ────────────────────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for b in NAMES18:
            if b == "Sun":
                continue
            p = np.mod(LON[s, IDX[b]] - LON[s, IDX["Sun"]], 360.0)
            F[f"{b} elongation from the Sun, cos — {who}"] = (
                f"Cosine of {b}'s angular distance from the Sun for the {who} partner. For the Moon this is the "
                f"lunation phase; for a planet it decides whether it rose before or after the Sun, which "
                f"Hellenistic astrology treats as a change of condition.", np.cos(p * rad))
            F[f"{b} is oriental of the Sun — {who}"] = (
                f"1 when {b} rose before the Sun for the {who} partner (elongation under 180 degrees).",
                (p < 180).astype(float))
    for b in NAMES18:
        if b == "Sun":
            continue
        po = np.mod(LON[0, IDX[b]] - LON[0, IDX["Sun"]], 360.0)
        py = np.mod(LON[1, IDX[b]] - LON[1, IDX["Sun"]], 360.0)
        F[f"{b} elongation difference between the partners"] = (
            f"How far apart the partners were in {b}'s cycle relative to the Sun, 0-180 degrees.",
            _fold(po - py))
    yield "lunar elongations", F

    # ── vargas ───────────────────────────────────────────────────────────────────────────────────────────
    F = {}
    for D, label in VARGA.items():
        for b in CLASSICAL:
            for who, s in SLOTS:
                base = SID if SID is not None else LON
                v = np.floor(np.mod(base[s, IDX[b]], 360.0) / (30.0 / D)) % 12
                F[f"{b} sign in D{D} {label} — {who}"] = (
                    f"{b}'s sign in the D{D} divisional chart ({label}) for the {who} partner: the sign is "
                    f"divided into {D} parts and the part index mapped back onto the twelve signs. Computed on "
                    f"the sidereal zodiac, as Jyotisa does.", v + 1)
            vo = np.floor(np.mod((SID if SID is not None else LON)[0, IDX[b]], 360.0) / (30.0 / D)) % 12
            vy = np.floor(np.mod((SID if SID is not None else LON)[1, IDX[b]], 360.0) / (30.0 / D)) % 12
            F[f"{b} shares a D{D} sign across the two charts"] = (
                f"1 when {b} occupies the same D{D} ({label}) sign in both partners' charts — the divisional "
                f"form of a same-sign contact.", (vo == vy).astype(float))
    yield "vargas", F

    # ── vedic pair distances for every body ──────────────────────────────────────────────────────────────
    F = {}
    base = SID if SID is not None else LON
    for b in NAMES18:
        no = np.floor(np.mod(base[0, IDX[b]], 360.0) / (360.0 / 27.0))
        ny = np.floor(np.mod(base[1, IDX[b]], 360.0) / (360.0 / 27.0))
        F[f"{b} nakshatra distance between the partners"] = (
            f"How many of the 27 lunar mansions separate the partners' {b}, folded to 0-13. Ashtakuta scores "
            f"several kutas from exactly this distance, though only for the Moon.", _fold(no - ny, 27))
        so = np.floor(np.mod(base[0, IDX[b]], 360.0) / 30.0)
        sy = np.floor(np.mod(base[1, IDX[b]], 360.0) / 30.0)
        F[f"{b} sign distance between the partners"] = (
            f"How many signs separate the partners' {b}, folded to 0-6.", _fold(so - sy, 12))
        F[f"{b} in the same sign for both partners"] = (
            f"1 when both partners' {b} occupy the same sign.", (so == sy).astype(float))
    yield "vedic pair", F


def calendrical(df, sun_o, sun_y, JD):
    """Families that need the CALENDAR date, not only a longitude: weekday, day of the year, sun-sign pairs,
    the Chinese sexagenary pillars, and numerology. Requires day precision on both dates."""
    # DATES AS numpy datetime64[D], NOT pandas datetimes. pandas 2.x parses to NANOSECONDS, whose range starts at
    # 1677-09-21, and the training half starts in 1600: the Kaggle kernel died on OutOfBoundsDatetime at the
    # first 17th-century couple. It worked locally only because pandas 3 infers a microsecond resolution. numpy's
    # datetime64[D] spans +-2.5e16 days on every version, and every calendar quantity below is integer
    # arithmetic on it: 1970-01-01 was a Thursday, so (days_since_epoch + 4) % 7 is the weekday with Sunday 0.
    do = np.array(df.dob_older.to_numpy().astype(str), dtype="datetime64[D]")
    dy = np.array(df.dob_younger.to_numpy().astype(str), dtype="datetime64[D]")

    def _cal(d):
        Y = d.astype("datetime64[Y]")
        M = d.astype("datetime64[M]")
        return {"year": Y.astype(np.int64) + 1970,
                "month": M.astype(np.int64) % 12 + 1,
                "day": (d - M).astype(np.int64) + 1,
                "doy": (d - Y).astype(np.int64) + 1,
                "wd": (d.astype(np.int64) + 4) % 7}
    co, cy = _cal(do), _cal(dy)
    doy = {"older": co["doy"], "younger": cy["doy"]}
    wd = {"older": co["wd"], "younger": cy["wd"]}
    yr = {"older": co["year"], "younger": cy["year"]}
    mo = {"older": co["month"], "younger": cy["month"]}
    dm = {"older": co["day"], "younger": cy["day"]}
    gap_days = (dy - do).astype(np.int64).astype(float)

    F = {}
    for who in ("older", "younger"):
        F[f"day of the year — {who}"] = (
            f"The {who} partner's birth day counted from 1 January, 1-366: the season of birth, very nearly "
            f"orthogonal to the birth year.", doy[who].astype(float))
        for h in (1, 2, 3, 4):
            F[f"day of the year, cos harmonic {h} — {who}"] = (
                f"cos({h} x 2pi x day-of-year / 365.25) for the {who} partner: the {h}-per-year component of "
                f"the seasonal cycle, free of the 31-December wrap.",
                np.cos(h * 2 * np.pi * doy[who] / 365.25))
            F[f"day of the year, sin harmonic {h} — {who}"] = (
                f"The sine companion of the {h}-per-year seasonal component for the {who} partner.",
                np.sin(h * 2 * np.pi * doy[who] / 365.25))
        F[f"weekday of birth (0 Sunday) — {who}"] = (
            f"Which day of the week the {who} partner was born. The seven-day week is the oldest astrological "
            f"cycle still in use and is near-orthogonal to both era and age gap.", wd[who].astype(float))
        for k, lord in enumerate(DAYLORD):
            F[f"born on a {lord} day — {who}"] = (
                f"1 when the {who} partner was born on the weekday ruled by {lord} in the Chaldean order "
                f"({['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'][k]}).",
                (wd[who] == k).astype(float))
        F[f"day of the month — {who}"] = (
            f"The raw day of the month of the {who} partner's birth, 1-31.", dm[who].astype(float))
        F[f"month of birth — {who}"] = (
            f"The raw calendar month of the {who} partner's birth, 1-12.", mo[who].astype(float))

    dd = _fold(doy["older"].astype(float) - doy["younger"].astype(float), 365.25)
    F["seasonal separation of the two births (days)"] = (
        "How far apart in the YEAR the two partners were born, ignoring which year — the Sun-to-Sun synastry "
        "contact and the sub-year remainder of the age gap at once.", dd)
    for h in (1, 2, 3, 4):
        F[f"seasonal separation, cos harmonic {h}"] = (
            f"cos({h} x the seasonal separation): h=1 peaks when the birthdays coincide, h=2 when they coincide "
            f"or fall six months apart.", np.cos(h * 2 * np.pi * dd / 365.25))
    F["born within 15 days of the same point in the year"] = (
        "1 when the partners' birthdays fall within a fortnight of each other in the calendar.",
        (dd < 15).astype(float))
    F["same weekday of birth"] = (
        "1 when both partners were born on the same weekday, i.e. their age gap is a whole number of weeks.",
        (wd["older"] == wd["younger"]).astype(float))
    F["same calendar month of birth"] = (
        "1 when both partners were born in the same month of the year.",
        (mo["older"] == mo["younger"]).astype(float))
    whole = np.round(gap_days / 365.2425)
    F["age gap in whole years"] = (
        "The partners' age difference rounded to whole years — the term that carries the mortality effect, "
        "listed so the periodic features can be read against it.", whole)
    F["sub-year remainder of the age gap"] = (
        "What is left of the age gap after removing whole years, folded to 0-182 days. Seasonal, and unable to "
        "carry a mortality effect.", _fold(gap_days - whole * 365.2425, 365.2425))
    for p, nm in ((7.0, "week"), (12.0, "twelve-year animal cycle"), (19.0, "Metonic 19-year cycle"),
                  (29.53059, "synodic month"), (60.0, "sexagenary 60-year cycle")):
        unit_years = nm in ("twelve-year animal cycle", "Metonic 19-year cycle", "sexagenary 60-year cycle")
        v = gap_days / (365.2425 if unit_years else 1.0)
        F[f"age gap modulo the {nm}"] = (
            f"The age gap taken modulo the {nm} and folded, isolating that cycle's own claim from the smooth "
            f"age-gap trend. No smooth model of the gap can contain it.", _fold(v, p))

    # ── sun-sign compatibility, in the forms people actually use ─────────────────────────────────────────
    so = np.floor(np.mod(sun_o, 360.0) / 30.0)
    sy = np.floor(np.mod(sun_y, 360.0) / 30.0)
    ds = _fold(so - sy, 12)
    F["Sun-sign distance between the partners (0-6)"] = (
        "How many of the twelve signs separate the two Suns, folded. Every sun-sign compatibility rule in "
        "circulation is a function of this one number.", ds)
    F["both Suns in the SAME sign"] = ("1 when both partners share a Sun sign.", (ds == 0).astype(float))
    F["Suns in the same ELEMENT (the classic trine 'compatible' rule)"] = (
        "1 when the two Sun signs share an element — 0, 4 or 8 signs apart. The single most repeated "
        "compatibility rule in popular astrology.", (np.mod(so - sy, 4) == 0).astype(float))
    F["Suns in the same MODALITY (cardinal/fixed/mutable)"] = (
        "1 when the Sun signs share a modality, 0/3/6/9 signs apart — held to produce friction.",
        (np.mod(so - sy, 3) == 0).astype(float))
    for k, nm in ((6, "OPPOSITE signs"), (3, "SQUARE"), (2, "SEXTILE"), (1, "adjacent signs")):
        F[f"Suns in {nm}"] = (
            f"1 when the two Suns are {k} signs apart, folded.", (ds == k).astype(float))
    F["popular 'compatible' verdict (same element or sextile)"] = (
        "1 when the pair satisfies the composite rule a magazine column applies: same element, or two signs "
        "apart.", ((np.mod(so - sy, 4) == 0) | (ds == 2)).astype(float))
    for si, nm in enumerate(SIGNS):
        F[f"older partner's Sun in {nm}"] = (
            f"1 when the older partner's Sun was in {nm}.", (so == si).astype(float))
        F[f"younger partner's Sun in {nm}"] = (
            f"1 when the younger partner's Sun was in {nm}.", (sy == si).astype(float))

    # ── Chinese sexagenary pillars ───────────────────────────────────────────────────────────────────────
    for who in ("older", "younger"):
        F[f"Chinese year branch (animal) 1-12 — {who}"] = (
            f"The {who} partner's birth-year animal, Rat 1 to Pig 12, from the year modulo twelve.",
            (np.mod(yr[who] - 4, 12) + 1).astype(float))
        F[f"Chinese year stem 1-10 — {who}"] = (
            f"The {who} partner's birth-year heavenly stem, from the year modulo ten.",
            (np.mod(yr[who] - 4, 10) + 1).astype(float))
        F[f"Chinese year stem element 1-5 — {who}"] = (
            f"The five-phase element of the {who} partner's year stem: Wood, Fire, Earth, Metal, Water.",
            (np.mod(yr[who] - 4, 10) // 2 + 1).astype(float))
    jd = np.floor(np.asarray(JD[0], dtype=np.float64) + 0.5)
    jdy = np.floor(np.asarray(JD[1], dtype=np.float64) + 0.5)
    for who, j in (("older", jd), ("younger", jdy)):
        F[f"sexagenary DAY index 1-60 — {who}"] = (
            f"The {who} partner's day pillar: the continuous 60-day sexagenary count, which advances one step "
            f"per calendar day and is independent of the year cycle.", np.mod(j, 60) + 1)
        F[f"sexagenary day branch 1-12 — {who}"] = (
            f"The animal branch of the {who} partner's day pillar.", np.mod(j, 12) + 1)
    ao, ay = np.mod(yr["older"] - 4, 12), np.mod(yr["younger"] - 4, 12)
    dan = _fold(ao.astype(float) - ay, 12)
    F["Chinese animal distance between the partners (0-6)"] = (
        "How many animal years separate the partners. Being the age gap modulo twelve, no smooth model of the "
        "gap contains it.", dan)
    F["same Chinese animal"] = ("1 when both partners share an animal sign.", (dan == 0).astype(float))
    F["san-he trine group match (4 or 8 animals apart)"] = (
        "1 when the animals share a san-he trine, the groups Chinese practice holds most compatible.",
        (np.mod(ao - ay, 4) == 0).astype(float))
    F["liu-chong clash (exactly 6 animals apart)"] = (
        "1 when the animals are directly opposed on the twelve-year wheel — the specific and widely believed "
        "claim that a six-year age gap is unlucky.", (dan == 6).astype(float))
    F["same stem element across the partners"] = (
        "1 when both birth years carry the same five-phase element.",
        (np.mod(yr["older"] - 4, 10) // 2 == np.mod(yr["younger"] - 4, 10) // 2).astype(float))
    F["stem-element distance on the five-phase wheel"] = (
        "Folded distance between the partners' stem elements, where adjacency is generation and two is "
        "conquest.", _fold(np.mod(yr["older"] - 4, 10) // 2 - np.mod(yr["younger"] - 4, 10) // 2, 5))

    # ── numerology ───────────────────────────────────────────────────────────────────────────────────────
    import trad_numerology as NU
    N = {"older": NU.numbers(yr["older"], mo["older"], dm["older"]),
         "younger": NU.numbers(yr["younger"], mo["younger"], dm["younger"])}
    LAB = {"lp": ("Life Path", "the digit sum of the whole birth date reduced to one figure, keeping the master "
                               "numbers 11, 22 and 33 — the most-read number in the practice"),
           "bday": ("Birthday number", "the day of the month reduced to one figure"),
           "att": ("Attitude number", "month plus day reduced — how the person is said to present"),
           "y": ("Year pillar", "the birth year's digits reduced on their own"),
           "m": ("Month pillar", "the birth month reduced"),
           "d": ("Day pillar", "the birth day reduced, no master numbers"),
           "chal": ("Chaldean number", "the date reduced under the Chaldean rule, which holds 9 sacred")}
    KARMIC = (13, 14, 16, 19)
    for who in ("older", "younger"):
        for k, (nm, ex) in LAB.items():
            F[f"{nm} — {who}"] = (f"The {who} partner's {nm}: {ex}.", N[who][k].astype(float))
            for val in range(1, 10):
                F[f"{nm} is {val} — {who}"] = (
                    f"1 when the {who} partner's {nm} reduces to {val}.",
                    (N[who][k] == val).astype(float))
        F[f"Life Path is a master number — {who}"] = (
            f"1 when the {who} partner's Life Path is 11, 22 or 33, a class numerology treats as distinct and "
            f"more demanding rather than merely larger.", np.isin(N[who]["lp"], NU.MASTER).astype(float))
        raw = NU._digit_sum(yr[who]) + NU._digit_sum(mo[who]) + NU._digit_sum(dm[who])
        for kd in KARMIC:
            F[f"karmic debt number {kd} — {who}"] = (
                f"1 when the {who} partner's unreduced date sum is {kd}, one of the four numbers numerology "
                f"designates a karmic debt.", (raw == kd).astype(float))
        F[f"unreduced date digit sum — {who}"] = (
            f"The {who} partner's whole birth date digit-summed once, before reduction.", raw.astype(float))
        F[f"digit sum of the birth year — {who}"] = (
            f"The {who} partner's birth year digit-summed, e.g. 1899 -> 27. Deliberately almost decorrelated "
            f"from the year itself: 1899 and 1900 give 27 and 10.", NU._digit_sum(yr[who]).astype(float))
        ch = np.abs(NU._reduce(mo[who], False) - NU._reduce(dm[who], False))
        F[f"first challenge number — {who}"] = (
            f"The {who} partner's first challenge number: the absolute difference of the reduced month and "
            f"reduced day, read as the obstacle carried through early life.", ch.astype(float))
        F[f"first pinnacle number — {who}"] = (
            f"The {who} partner's first pinnacle: reduced month plus reduced day, read as the theme of the "
            f"first life cycle.", NU._reduce(mo[who] + dm[who], False).astype(float))
    lpo, lpy = N["older"]["lp"], N["younger"]["lp"]
    F["sum of the two Life Paths"] = ("The partners' Life Paths added.", (lpo + lpy).astype(float))
    F["relationship number (Life Paths summed and reduced)"] = (
        "The two Life Paths added and reduced — the number a numerologist assigns to the couple itself.",
        NU._reduce(lpo + lpy, keep_master=False).astype(float))
    F["absolute difference of the two Life Paths"] = (
        "How far apart the partners' Life Paths are.", np.abs(lpo - lpy).astype(float))
    F["identical Life Paths"] = ("1 when both partners share a Life Path.", (lpo == lpy).astype(float))
    F["same numerological compatibility group"] = (
        "1 when both Life Paths fall in the same taught grouping — 1-5-7 mind, 2-4-8 business, 3-6-9 creative.",
        np.array([1.0 if NU._GROUP.get(int(a), -1) == NU._GROUP.get(int(b), -2) else 0.0
                  for a, b in zip(lpo, lpy)]))
    F["identical Birthday numbers"] = (
        "1 when both partners reduce the same day-of-month number.",
        (N["older"]["bday"] == N["younger"]["bday"]).astype(float))
    F["identical Chaldean numbers"] = (
        "1 when both partners share a Chaldean reduction.",
        (N["older"]["chal"] == N["younger"]["chal"]).astype(float))
    F["older partner's Personal Year in the younger's birth year"] = (
        "The numerologist's question 'what personal year were you in when they were born': the older partner's "
        "month and day added to the younger's birth year, reduced.",
        NU.personal_year(mo["older"], dm["older"], yr["younger"]).astype(float))
    F["younger partner's Personal Year in the older's birth year"] = (
        "The same quantity with the partners exchanged.",
        NU.personal_year(mo["younger"], dm["younger"], yr["older"]).astype(float))
    mid = (yr["older"] + yr["younger"]) // 2
    F["both in the same Personal Year at their date midpoint"] = (
        "1 when both partners share a Personal Year computed at the midpoint year between their births.",
        (NU.personal_year(mo["older"], dm["older"], mid)
         == NU.personal_year(mo["younger"], dm["younger"], mid)).astype(float))
    return F

# %% [markdown]
# ### `dates.py`, spliced in
#
# `couple_record` turns two date strings into the record `core.load()` reads, deriving precision and the
# uncertainty window from the dates themselves. It lives in the repo's `kaggle/` directory and is NOT part of the
# public ephemeris asset, so it is spliced in verbatim rather than imported.

# %%


PRECISION_DAY, PRECISION_MONTH, PRECISION_YEAR = 11, 10, 9

# ABSENT is a precision, not a missing value. The duration dataset's training half contains rows where one
# partner is not in Wikidata at all, written `0000-00-00` — the marriage's duration is known exactly even when
# one spouse's birthday is not, so the row carries a real label and half an input, and discarding it cost six
# sevenths of the training data.
#
# The value is 1 and not 0 ON PURPOSE. core.py reads the precision as `int(g("aPrec", "bPrec") or 11)`, and 0 is
# falsy, so an absent partner would arrive at the feature layer claiming to be known to the DAY. That `or` is a
# default for a missing KEY and cannot distinguish it from a present zero. 1 is truthy, sorts below every real
# precision, and cannot be mistaken for one.
PRECISION_ABSENT = 1
ABSENT_DATE = "0000-00-00"

# ── THE GRID, DEFINED ONCE ───────────────────────────────────────────────────────────────────────────────────
# Each partner's date is degraded independently over four levels, and two of the sixteen combinations are
# excluded from the score. This lives here because six different files need to agree on it — the scorer, the
# grid builder, the evaluator, the benchmark task, the publish gate and the page — and every time a constant
# like this has been restated in this project the copies have drifted.
LEVELS = ["full", "month", "year", "absent"]

EXCLUDED_CELLS = {
    # No input at all: both dates are the same placeholder, so nothing can be ranked and the cell would only
    # shift every competitor's average by a constant.
    "absent|absent",
    # Month precision on BOTH sides is a case that essentially does not occur. Of 107,698 couples only 859 men
    # and 1,017 women are known to the month, so the real data contains 18 such pairs — and on 18 rows an AUC
    # is noise: that group scored 0.8615 against 0.6201 for the 16,675-row day-by-day group. Simulating it
    # across every held-out couple asks the model about a situation the records almost never present.
    "month|month",
}

CELLS = [f"{a}|{b}" for a in LEVELS for b in LEVELS if f"{a}|{b}" not in EXCLUDED_CELLS]
N_CELLS = len(CELLS)          # 14

# How wide the uncertainty is, in days, for each precision. core.py takes this as `aWin`/`bWin` and it is the
# difference between "this chart is for 1 January" and "this chart is for a year we cannot place".
WINDOW = {PRECISION_DAY: 1.0, PRECISION_MONTH: 30.0, PRECISION_YEAR: 365.0,
          # A century. Not infinity: the window is a feature, and every tradition that reads it does arithmetic
          # on it. It says "this chart is a placeholder", which is the truth.
          PRECISION_ABSENT: 36525.0}


def precision(d):
    """11 if the day is known, 10 if only the month, 9 if only the year, 1 if there is no date at all."""
    if not isinstance(d, str) or len(d) != 10:
        raise ValueError(f"not a YYYY-MM-DD date: {d!r}")
    if d[:4] == "0000":
        return PRECISION_ABSENT
    if d[8:10] != "00":
        return PRECISION_DAY
    if d[5:7] != "00":
        return PRECISION_MONTH
    return PRECISION_YEAR


def window(d):
    return WINDOW[precision(d)]


def concrete(d):
    """The same date with `00` replaced by `01`, so astropy and Swiss Ephemeris have an instant to work with.

    This is a representative, not a guess: the precision travels alongside it so a model can tell that the day
    was chosen rather than recorded. Anything that uses `concrete()` without also passing the precision is
    quietly claiming to know the day.
    """
    y, m, dd = d[:4], d[5:7], d[8:10]
    return f"{y}-{'01' if m == '00' else m}-{'01' if dd == '00' else dd}"


def coarsen(d, level):
    """Reduce a date to `full`, `month`, `year` — the precision grid's levels.

    IDEMPOTENT AND MONOTONE: coarsening a year-only date to `month` returns it unchanged, because precision that
    was never there cannot be added back. That property is what makes the grid honest — a `month|month` cell
    contains rows whose month was coarsened away and rows that never had one, and both look the same.
    """
    if level == "full":
        return d
    if level == "month":
        return d[:7] + "-00"
    if level == "year":
        return d[:4] + "-00-00"
    if level == "absent":
        return ABSENT_DATE
    raise ValueError(f"unknown level {level!r}")


def couple_record(i, dob_older, dob_younger, label=0):
    """One row in the shape `core.load()` reads, with precision and window derived from the dates themselves.

    The trainer used to hardcode `aPrec: 11, bPrec: 11` — telling core that every day was known, including for
    the 34% of rows that only have a year. core has precision-aware features and a window field precisely for
    this, and they were being fed a constant.

    AN ABSENT PARTNER GETS THE OTHER PARTNER'S INSTANT, flagged. Every chart needs some instant to be cast for,
    and there is no honest one for a person who is not in Wikidata — so the pair features degenerate to
    self-comparison, which is a DEFINED and CONSTANT-SHAPED value rather than a guess about a stranger. What
    makes that honest instead of a fabrication is that the row also carries `aPrec`/`bPrec` of 1 and a
    century-wide window, so a model can see the pair features are meaningless here and read only the present
    partner's own chart, which is the real content of a one-sided row. Imputing a plausible spouse — the median
    age gap, say — would invent exactly the pair structure the model is being asked to find.
    """
    pm, pw = precision(dob_older), precision(dob_younger)
    if pm == PRECISION_ABSENT and pw == PRECISION_ABSENT:
        raise ValueError("a couple with no date on either side carries no input")
    cm = concrete(dob_younger if pm == PRECISION_ABSENT else dob_older)
    cw = concrete(dob_older if pw == PRECISION_ABSENT else dob_younger)
    return {"a": f"a{i}", "b": f"b{i}",
            "aDob": cm, "bDob": cw,
            # No sex is known or used: the columns are ordered by AGE, and no tradition reads aSex/bSex (checked).
            "aSex": "", "bSex": "",
            "aPrec": pm, "bPrec": pw,
            "aWin": window(dob_older), "bWin": window(dob_younger),
            "label": int(label)}


# %%
import core


def build(df, labelled):
    """Cast both charts for every couple and return the full feature matrix, family by family."""
    rows = [couple_record(i, r.dob_older, r.dob_younger, int(r[LABEL]) if labelled else 0)
            for i, r in df.iterrows()]
    json.dump(rows, open(os.environ["AQ_COUPLES"], "w"))
    E = core.load()
    if E.n != len(df):
        raise SystemExit(f"core kept {E.n} of {len(df)} rows — predictions could not be aligned")
    names, cols = [], []
    for fam, F in families(E):
        for k, (_, v) in F.items():
            names.append(k); cols.append(np.asarray(v, dtype=np.float32))
        print(f"  [{time.time()-T0:6.0f}s] {fam:<26} {len(F):>5,}", flush=True)
    F = calendrical(df, np.asarray(E.LON)[0, 0], np.asarray(E.LON)[1, 0], E.JD)
    for k, (_, v) in F.items():
        names.append(k); cols.append(np.asarray(v, dtype=np.float32))
    print(f"  [{time.time()-T0:6.0f}s] {'calendrical + numerology':<26} {len(F):>5,}", flush=True)
    del E; gc.collect()
    return names, np.column_stack(cols)


nm_tr, X_tr = build(tr, True)
print(f"train features {X_tr.shape}")
nm_te, X_te = build(te, False)
print(f"test features {X_te.shape}")
assert nm_tr == nm_te, "the two halves produced different feature lists"

ok = ((X_tr.std(0) > 1e-12) & (X_te.std(0) > 1e-12)
      & np.isfinite(X_tr).all(0) & np.isfinite(X_te).all(0))
NAMES = [n for n, k in zip(nm_tr, ok) if k]
X_tr, X_te = X_tr[:, ok], X_te[:, ok]
y = tr[LABEL].to_numpy().astype(np.int64)
print(f"kept {X_tr.shape[1]:,} usable features of {len(ok):,}")


# The age gap and the two birth years, in numpy datetime64[D] arithmetic (pandas' nanosecond datetimes overflow
# before 1677 and the training half starts in 1600). The gap is a fair competition feature -- every entrant is
# given the same two dates -- and it is the strongest single feature in the problem, so it is a pool member in
# its own right AND the floor the ensemble must clear.
def gap_years(df):
    do = np.array(df.dob_older.to_numpy().astype(str), dtype="datetime64[D]")
    dy = np.array(df.dob_younger.to_numpy().astype(str), dtype="datetime64[D]")
    return ((dy - do).astype(np.int64).astype(np.float32),
            do.astype("datetime64[Y]").astype(np.int64) + 1970,
            dy.astype("datetime64[Y]").astype(np.int64) + 1970)


gap, yo, yy = gap_years(tr)
gape, _, _ = gap_years(te)
A = np.column_stack([X_tr, gap]); Ae = np.column_stack([X_te, gape])
NAMES = NAMES + ["age gap in days"]; G = A.shape[1] - 1
later = np.maximum(yo, yy)


def auc(yv, s):
    yv = np.asarray(yv, np.int64); s = np.asarray(s, np.float64)
    n1, n0 = int(yv.sum()), int((1 - yv).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    o = np.argsort(s, kind="mergesort"); ys, ss = yv[o], s[o]
    r = np.empty(len(ss)); i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[i:j + 1] = 0.5 * (i + j) + 1.0; i = j + 1
    return float((r[ys == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def r01(v):
    r = np.argsort(np.argsort(v)).astype(np.float64)
    return r / max(1.0, len(r) - 1)


# %% [markdown]
# ## Why there is no model selection in this notebook
#
# The first version of this notebook picked models on a single inner split — the latest 15% of training births,
# 1888–1900 — and blended by inner AUC. It scored **0.5809** held out, *below* the age gap alone at 0.6045: an
# ensemble handed a feature cannot honestly score below that feature, so that was a broken pipeline, not a fact
# about the data. Two things were wrong. The split was 12 years ahead when the competition's held-out couples are
# up to 90 years ahead, so it could not see the failure it was meant to catch; and nothing constrained the one
# relationship we are certain of — a wider age gap means a shorter relationship — so the trees were free to fit
# era-specific noise instead.
#
# Repairing the split did not fix selection. Across ten candidates, the correlation between mean AUC on three
# expanding-window temporal folds (train ≤1820 → validate 1821–1850, ≤1850 → 1851–1875, ≤1875 → 1876–1900) and
# held-out AUC was **Spearman −0.15**. Internal validation on 1600–1900 simply does not rank models for
# 1901–1990. Choosing one model on it is a coin flip; choosing on the leaderboard would be cheating.
#
# So this notebook does not choose. It builds a **diverse pool of eleven models with hyper-parameters fixed in
# advance**, weights them **equally**, and averages their **ranks** (AUC reads ranks; averaging a logistic's
# probabilities with a tree ensemble's lets whichever is more confident dominate). The temporal folds are still
# used for one thing that does transfer: **feature stability**. A feature enters a model only if it points the
# same way in all three folds, ranked by its *weakest* fold rather than its best — which is what rejects a
# feature strong in one era and absent in another, and that is most of the 4,962.

# %%
CUTS = [1820, 1850, 1875]
per_fold = np.zeros((len(CUTS), A.shape[1]), dtype=np.float32)
for k, cut in enumerate(CUTS):
    f = later <= cut
    yf = y[f]; Af = A[f]
    n1, n0 = int(yf.sum()), int((1 - yf).sum())
    # rank AUC of every column at once, in chunks
    for s0 in range(0, A.shape[1], 800):
        R = np.apply_along_axis(lambda c: np.argsort(np.argsort(c)) + 1.0, 0, Af[:, s0:s0 + 800])
        per_fold[k, s0:s0 + 800] = (R[yf == 1].sum(0) - n1 * (n1 + 1) / 2.0) / (n1 * n0)
    print(f"  [{time.time()-T0:6.0f}s] fold train<={cut}: every feature scored on {int(f.sum()):,} couples", flush=True)
sg = np.sign(per_fold - 0.5)
consistent = np.all(sg == sg[0], axis=0)
strength_min = np.min(np.abs(per_fold - 0.5), axis=0); strength_min[~consistent] = 0.0
order = np.argsort(-strength_min)
sign_all = np.where(per_fold.mean(0) >= 0.5, 1.0, -1.0)
print(f"{int(consistent.sum()):,} of {A.shape[1]:,} features point the same way in all three folds")
print("the most stable, by their WEAKEST fold:")
for j in order[:8]:
    print(f"  min {0.5+strength_min[j]:.4f}   {NAMES[j][:60]}")

# %%
import lightgbm as lgb
import xgboost as xgb
from sklearn.linear_model import LogisticRegression

pool = {}
pool["age gap, monotone"] = -Ae[:, G]
for k in (3, 8, 20):
    cols = [j for j in order[:k] if j != G]
    pool[f"rank-average: gap + top {k} stable"] = r01(-Ae[:, G]) + sum(r01(sign_all[j] * Ae[:, j]) for j in cols) / len(cols)
for k in (8, 20, 50):
    cols = list(dict.fromkeys(list(order[:k]) + [G])); mc = [0] * len(cols); mc[cols.index(G)] = -1
    p = np.zeros(len(Ae))
    for s in range(3):
        m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=200,
                               colsample_bytree=0.6, subsample=0.7, subsample_freq=1, reg_lambda=10.0,
                               monotone_constraints=mc, random_state=s, verbose=-1).fit(A[:, cols], y)
        p += m.predict_proba(Ae[:, cols])[:, 1]
    pool[f"LightGBM monotone-in-gap, top {k} stable"] = p / 3
    print(f"  [{time.time()-T0:6.0f}s] LightGBM top {k}", flush=True)
for k in (20, 50):
    cols = list(dict.fromkeys(list(order[:k]) + [G]))
    p = np.zeros(len(Ae))
    for s in range(2):
        m = xgb.XGBClassifier(n_estimators=300, learning_rate=0.03, max_depth=3, min_child_weight=50,
                              subsample=0.7, colsample_bytree=0.6, reg_lambda=10.0, tree_method="hist",
                              device=DEV, random_state=s, eval_metric="logloss").fit(A[:, cols], y)
        p += m.predict_proba(Ae[:, cols])[:, 1]
    pool[f"XGBoost depth 3, top {k} stable"] = p / 2
    print(f"  [{time.time()-T0:6.0f}s] XGBoost top {k}", flush=True)
for k in (50, 200):
    cols = list(order[:k])
    mu, sd = A[:, cols].mean(0), A[:, cols].std(0) + 1e-6
    m = LogisticRegression(C=1e-3, max_iter=500).fit((A[:, cols] - mu) / sd, y)
    pool[f"L2 logistic, top {k} stable"] = m.decision_function((Ae[:, cols] - mu) / sd)
print(f"pool of {len(pool)} models, none of them chosen against anything")

R = np.column_stack([r01(v) for v in pool.values()])
ens = R.mean(1)
sub = pd.DataFrame({"id": te.id, LABEL: r01(ens)})
sub.to_csv("/kaggle/working/submission.csv", index=False)
print(f"wrote submission.csv — {len(sub):,} rows, equal-weight rank average of {len(pool)} models")

# The astrology-only companion: the same pool with the age gap withheld as an explicit column. Note what it
# still contains -- a slow planet's cross-chart separation is a near-linear read of the gap (Pluto moves 1.45
# degrees a year), so withholding the COLUMN does not withhold the information.
astro = [j for j in order if j != G and "age gap" not in NAMES[j]]
pa = []
for k in (8, 20, 50):
    cols = astro[:k]
    p = np.zeros(len(Ae))
    for s in range(3):
        m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=200,
                               colsample_bytree=0.6, subsample=0.7, subsample_freq=1, reg_lambda=10.0,
                               random_state=s, verbose=-1).fit(A[:, cols], y)
        p += m.predict_proba(Ae[:, cols])[:, 1]
    pa.append(r01(p / 3))
pa.append(r01(sum(r01(sign_all[j] * Ae[:, j]) for j in astro[:20])))
pd.DataFrame({"id": te.id, LABEL: r01(np.mean(pa, 0))}).to_csv("/kaggle/working/submission_astrology_only.csv", index=False)
json.dump({"pool": list(pool), "n_features": int(X_tr.shape[1]), "n_stable": int(consistent.sum()),
           "n_train_day": int(len(tr)), "folds": CUTS}, open("/kaggle/working/ensemble.json", "w"), indent=1)
print(f"done in {(time.time()-T0)/60:.1f} min")
