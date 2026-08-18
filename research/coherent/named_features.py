"""
named_features.py — several hundred INDIVIDUALLY NAMED AND EXPLAINED astrology and numerology features.

WHY THIS FILE EXISTS. The nineteen tradition modules return bare matrices: a feature there can only be referred
to as `block :: column 37`, which is unreadable and unciteable. Nobody can argue with column 37. This file
defines every feature explicitly, each with a NAME and a one-sentence EXPLANATION of the quantity it measures,
so that a ranking of them is a statement about astrology rather than about array indices.

WHAT A "2-PARAMETER LOGISTIC AUC" IS, EXACTLY

    logit P(lasted 30 years) = b0 + b1 * x

is MONOTONE in x, and AUC is invariant under any monotone transform of the score. So the fitted logistic's AUC
is identically the feature's own rank AUC, and the only thing the fit decides is the SIGN of b1. That makes the
number exact rather than an optimisation outcome — there is no learning rate, no convergence question, no
regularisation choice that could change it.

The sign is fitted on the TRAINING half and then applied to the held-out half. Taking max(auc, 1-auc) on the
held-out set instead would be choosing the direction using the answers, worth up to a few thousandths of free
AUC per feature and much more across hundreds of them.

CIRCULAR QUANTITIES ARE SPLIT, NEVER USED RAW. A longitude of 359 degrees is adjacent to 1 degree, so a
monotone model reads the wrap as the largest jump in the data. Every angle therefore enters as its cosine and
its sine, which are the two genuinely monotone-usable projections of a circle, and both are named.

ASPECTS ARE HARMONICS OF A SEPARATION. cos(h * delta) peaks where the h-th harmonic aspect is exact:
h=1 conjunction (and its opposite pole), h=2 the opposition/square axis, h=3 the trine, h=4 the square. This is
the standard way to make an aspect differentiable instead of a hard orb window, and it is what an orb-based
tally approximates.

WHAT IS NOT HERE. No houses, Ascendant or MC: those need a birth TIME and this dataset has birth dates only.
No name numerology (Expression, Soul Urge): that needs letters and there are no names. Both are large parts of
their traditions and are absent by necessity, said plainly.
"""
import numpy as np

# core.BODIES order
NAMES18 = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
           "TrueNode", "MeanNode", "Lilith", "Chiron", "Ceres", "Pallas", "Juno", "Vesta"]
IDX = {n: i for i, n in enumerate(NAMES18)}
CLASSICAL = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces"]
ELEMENT = ["fire", "earth", "air", "water"]
SLOT = {"older": 0, "younger": 1}
HARMONIC_NAME = {1: "conjunction axis", 2: "opposition/square axis", 3: "trine axis", 4: "square axis",
                 5: "quintile axis", 6: "sextile axis"}
# What each body is taken to signify, used only to write an honest explanation string.
MEANS = {
    "Sun": "identity and vitality", "Moon": "feeling, habit and the domestic",
    "Mercury": "speech and reasoning", "Venus": "attraction, affection and what is valued",
    "Mars": "desire, drive and conflict", "Jupiter": "expansion, luck and generosity",
    "Saturn": "duty, limitation and endurance — the classical marriage significator",
    "Uranus": "disruption and sudden change", "Neptune": "idealisation and dissolution",
    "Pluto": "compulsion and transformation", "TrueNode": "the karmic node of the Moon's orbit (true)",
    "MeanNode": "the karmic node of the Moon's orbit (mean)", "Lilith": "the lunar apogee, the disowned",
    "Chiron": "the wound and its healing", "Ceres": "nurture and sustenance",
    "Pallas": "strategy and craft", "Juno": "the marriage asteroid, partnership and its bargains",
    "Vesta": "devotion and what is kept sacred",
}


def _fold(d):
    """A separation in degrees folded to 0..180 — the form an aspect is actually read in."""
    d = np.mod(d, 360.0)
    return np.minimum(d, 360.0 - d)


def build(E):
    """Returns a list of (name, explanation, values) triples. `values` is a 1-D float array of length E.n."""
    LON = np.asarray(E.LON, dtype=np.float64)
    SPD = np.asarray(getattr(E, "SPD", np.zeros_like(LON)), dtype=np.float64)
    rad = np.pi / 180.0
    F = []

    def add(name, expl, v):
        v = np.asarray(v, dtype=np.float64).ravel()
        if np.all(np.isfinite(v)) and v.std() > 1e-12:
            F.append((name, expl, v))

    # ── A. each body in each partner's own chart ──────────────────────────────────────────────────────────
    for who, s in SLOT.items():
        for b in NAMES18:
            i = IDX[b]
            lam = LON[s, i]
            add(f"{b} longitude, cos — {who} partner",
                f"Cosine of {b}'s tropical ecliptic longitude in the {who} partner's chart. {b} signifies "
                f"{MEANS[b]}. Cosine and sine together locate it on the zodiac circle without the 359-to-1 "
                f"degree wrap that would otherwise dominate a monotone model.", np.cos(lam * rad))
            add(f"{b} longitude, sin — {who} partner",
                f"Sine of {b}'s tropical ecliptic longitude in the {who} partner's chart; the companion "
                f"projection to the cosine above.", np.sin(lam * rad))
            add(f"{b} zodiac sign (1 Aries .. 12 Pisces) — {who} partner",
                f"Which of the twelve 30-degree signs {b} occupied at the {who} partner's birth, as an ordinal "
                f"1-12. A monotone model can only read a trend across the sign order, not a preference for one "
                f"sign, so this tests whether the zodiac has a DIRECTION for {b}.",
                np.floor(np.mod(lam, 360.0) / 30.0) + 1)
            add(f"{b} degree within its sign (0-30) — {who} partner",
                f"How far {b} had travelled into its sign, 0 to 30 degrees. Early and late degrees are held to "
                f"differ in strength by most traditions.", np.mod(lam, 30.0))
            add(f"{b} element of its sign (1 fire .. 4 water) — {who} partner",
                f"The element of {b}'s sign as an ordinal: fire, earth, air, water in zodiacal order.",
                (np.floor(np.mod(lam, 360.0) / 30.0) % 4) + 1)
            if np.any(SPD[s, i] < 0):
                add(f"{b} retrograde — {who} partner",
                    f"1 when {b} was apparently moving backwards through the zodiac at the {who} partner's "
                    f"birth, 0 otherwise. Retrogradation is read as an inward or frustrated expression of "
                    f"{MEANS[b]}.", (SPD[s, i] < 0).astype(float))
            add(f"{b} daily speed — {who} partner",
                f"{b}'s apparent motion in degrees per day at the {who} partner's birth. Fast or slow relative "
                f"to its mean is read as strength or weakness.", SPD[s, i])

    # ── B. cross-chart contacts: the whole synastry grid, as harmonics ────────────────────────────────────
    for a in CLASSICAL:
        for b in CLASSICAL:
            d = _fold(LON[0, IDX[a]] - LON[1, IDX[b]])
            add(f"{a}(older) to {b}(younger) separation",
                f"The angle between the older partner's {a} and the younger partner's {b}, folded to 0-180 "
                f"degrees. This is the raw synastry contact: {MEANS[a]} meeting {MEANS[b]}.", d)
            for h in (1, 2, 3, 4):
                add(f"{a}(older) to {b}(younger), harmonic {h} ({HARMONIC_NAME[h]})",
                    f"cos({h} x separation) between the older partner's {a} and the younger partner's {b}. "
                    f"Peaks when the {HARMONIC_NAME[h]} is exact and falls away smoothly with orb, which is "
                    f"what a hard orb window approximates.", np.cos(h * d * rad))

    # ── C. contacts inside each partner's own chart ───────────────────────────────────────────────────────
    for who, s in SLOT.items():
        for ii in range(len(CLASSICAL)):
            for jj in range(ii + 1, len(CLASSICAL)):
                a, b = CLASSICAL[ii], CLASSICAL[jj]
                d = _fold(LON[s, IDX[a]] - LON[s, IDX[b]])
                add(f"{a} to {b} separation — {who} partner's own chart",
                    f"The natal angle between {a} and {b} in the {who} partner's own chart, 0-180 degrees: "
                    f"{MEANS[a]} against {MEANS[b]} within one person.", d)
                for h in (1, 2):
                    add(f"{a} to {b}, harmonic {h} ({HARMONIC_NAME[h]}) — {who} partner's own chart",
                        f"cos({h} x separation) between {a} and {b} natally for the {who} partner.",
                        np.cos(h * d * rad))

    # ── D. the luminaries: phase, and the two charts' phase relationship ──────────────────────────────────
    ph = {}
    for who, s in SLOT.items():
        p = np.mod(LON[s, IDX["Moon"]] - LON[s, IDX["Sun"]], 360.0)
        ph[who] = p
        add(f"Moon phase angle (0-360) — {who} partner",
            f"The Moon's elongation from the Sun at the {who} partner's birth: 0 is new moon, 180 full. The "
            f"lunation cycle is the single most widely read cycle in every tradition here.", p)
        add(f"Moon phase, cos — {who} partner",
            f"Cosine of the {who} partner's Moon phase; +1 at new moon, -1 at full moon, and free of the "
            f"360-degree wrap.", np.cos(p * rad))
        add(f"Moon phase, sin — {who} partner",
            f"Sine of the {who} partner's Moon phase; separates the waxing half of the cycle from the waning.",
            np.sin(p * rad))
        add(f"illuminated fraction of the Moon — {who} partner",
            f"The fraction of the Moon's disc lit at the {who} partner's birth, (1 - cos(phase))/2: 0 at new, "
            f"1 at full.", (1 - np.cos(p * rad)) / 2)
    dph = _fold(ph["older"] - ph["younger"])
    add("Moon-phase difference between the partners",
        "How far apart the two partners were in the lunation cycle, 0-180 degrees. 0 means both were born at "
        "the same phase of the Moon — the same 'lunar season'.", dph)
    add("Moon-phase difference, cos", "Cosine of the partners' lunation-phase difference.", np.cos(dph * rad))
    add("both born within 30 degrees of the same Moon phase",
        "1 when the partners' lunation phases differ by less than 30 degrees, a commonly cited compatibility "
        "claim.", (dph < 30).astype(float))

    # ── E. Vedic: the Moon's nakshatra, the backbone of Indian marriage matching ──────────────────────────
    for who, s in SLOT.items():
        lam = np.mod(LON[s, IDX["Moon"]], 360.0)
        n27 = np.floor(lam / (360.0 / 27.0))
        add(f"Moon nakshatra 1-27 (tropical) — {who} partner",
            f"Which of the 27 lunar mansions the Moon occupied for the {who} partner, as an ordinal. The "
            f"nakshatra pair is the foundation of ashtakuta marriage matching.", n27 + 1)
        add(f"Moon nakshatra cycle, cos — {who} partner",
            f"Cosine of the {who} partner's position around the 27-nakshatra wheel, wrap-free.",
            np.cos(2 * np.pi * n27 / 27.0))
        add(f"Moon nakshatra cycle, sin — {who} partner",
            f"Sine of the {who} partner's position around the same 27-fold nakshatra wheel; the companion "
            f"projection to the cosine above.", np.sin(2 * np.pi * n27 / 27.0))
        add(f"Moon pada 1-4 within its nakshatra — {who} partner",
            f"Which quarter of the nakshatra the Moon fell in for the {who} partner; the 108 padas are the "
            f"finest division routinely read.", np.floor(np.mod(lam, 360.0 / 27.0) / (360.0 / 108.0)) + 1)
    dn = np.abs(np.floor(np.mod(LON[0, IDX["Moon"]], 360.0) / (360.0 / 27.0))
                - np.floor(np.mod(LON[1, IDX["Moon"]], 360.0) / (360.0 / 27.0)))
    add("nakshatra distance between the partners (0-26)",
        "The count of lunar mansions between the two Moons. Ashtakuta scores several of its eight kutas "
        "directly from this distance.", np.minimum(dn, 27 - dn))

    # ── F. numerology ─────────────────────────────────────────────────────────────────────────────────────
    try:
        import os
        import sys
        # research/coherent/named_features.py -> research/coherent -> research -> repo root -> repo/astro
        _a = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "astro")
        if _a not in sys.path:
            sys.path.insert(0, _a)
        import trad_numerology as NU
        yO, mO, dO = NU._ymd(E.JD[0])
        yY, mY, dY = NU._ymd(E.JD[1])
        NO, NY = NU.numbers(yO, mO, dO), NU.numbers(yY, mY, dY)
        LABEL = {"lp": ("Life Path", "the digit sum of the whole birth date reduced to one figure, keeping the "
                                     "master numbers 11, 22 and 33 — the single most-read number in the practice"),
                 "bday": ("Birthday number", "the day of the month reduced to one figure"),
                 "att": ("Attitude number", "month plus day reduced — how the person is said to present"),
                 "y": ("Year pillar", "the birth year's digits reduced on their own"),
                 "m": ("Month pillar", "the birth month reduced"),
                 "d": ("Day pillar", "the birth day reduced with no master numbers"),
                 "chal": ("Chaldean number", "the same date reduced under the Chaldean rule, which holds 9 sacred "
                                             "and reduces to 1-8")}
        for who, N in (("older", NO), ("younger", NY)):
            for k, (nm, ex) in LABEL.items():
                add(f"{nm} — {who} partner", f"The {who} partner's {nm}: {ex}.", N[k])
            add(f"Life Path is a master number (11/22/33) — {who} partner",
                f"1 when the {who} partner's Life Path is 11, 22 or 33, which numerology treats as a distinct "
                f"and more demanding class rather than a larger number.", np.isin(N["lp"], NU.MASTER).astype(float))
        add("sum of the two Life Paths",
            "The partners' Life Paths added. Numerologists read the pair, not each number alone.",
            NO["lp"] + NY["lp"])
        add("relationship number (Life Paths summed and reduced)",
            "The two Life Paths added and reduced to a single figure — the number a numerologist assigns to the "
            "couple itself.", NU._reduce(NO["lp"] + NY["lp"], keep_master=False))
        add("absolute difference of the two Life Paths",
            "How far apart the partners' Life Paths are.", np.abs(NO["lp"] - NY["lp"]))
        add("identical Life Paths",
            "1 when both partners share the same Life Path number.", (NO["lp"] == NY["lp"]).astype(float))
        add("same numerological compatibility group",
            "1 when both Life Paths fall in the same taught grouping — 1-5-7 (mind), 2-4-8 (business), "
            "3-6-9 (creative).",
            np.array([1.0 if NU._GROUP.get(int(a), -1) == NU._GROUP.get(int(b), -2) else 0.0
                      for a, b in zip(NO["lp"], NY["lp"])]))
        add("identical Birthday numbers",
            "1 when both partners reduce the same day-of-month number.", (NO["bday"] == NY["bday"]).astype(float))
        add("identical Chaldean numbers",
            "1 when both partners share a Chaldean reduction.", (NO["chal"] == NY["chal"]).astype(float))
        add("older partner's Personal Year in the younger's birth year",
            "The numerologist's question 'what personal year were you in when they were born': the older "
            "partner's birth month and day added to the younger partner's birth year, reduced.",
            NU.personal_year(mO, dO, yY))
        add("younger partner's Personal Year in the older's birth year",
            "The same quantity with the partners exchanged.", NU.personal_year(mY, dY, yO))
        add("both in the same Personal Year at their date midpoint",
            "1 when both partners share a Personal Year computed at the midpoint date between their births.",
            (NU.personal_year(mO, dO, (yO + yY) // 2)
             == NU.personal_year(mY, dY, (yO + yY) // 2)).astype(float))
        for who, y_, m_, d_ in (("older", yO, mO, dO), ("younger", yY, mY, dY)):
            add(f"birth day of the month — {who} partner",
                f"The raw day of the month of the {who} partner's birth, 1-31, before any reduction.", d_)
            add(f"birth month — {who} partner",
                f"The raw calendar month of the {who} partner's birth, 1-12.", m_)
            add(f"digit sum of the birth year — {who} partner",
                f"The {who} partner's birth year with its digits added, e.g. 1899 -> 27. Deliberately almost "
                f"decorrelated from the year itself: 1899 and 1900 are adjacent in time and give 27 and 10.",
                NU._digit_sum(y_))
    except Exception as e:                                    # pragma: no cover
        # NEVER SILENT. The first run of this file printed this line and produced 643 features instead of 686,
        # and a "643 features" headline reads like success. Numerology is a third of what was asked for.
        raise SystemExit(f"numerology features FAILED to build: {type(e).__name__} {e}\n"
                         f"  trad_numerology needs sys.modules['swisseph'] set to the shim before import")

    return F


if __name__ == "__main__":
    # trad_numerology imports swisseph at module scope. In the real run train_on_csv has already put the shim
    # in sys.modules; the self-test has to do it too, or the numerology features silently vanish -- which is
    # exactly what happened on the first run of this file.
    import os as _os
    import sys as _sys
    _root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    _sys.path[:0] = [f"{_root}/astro", f"{_root}/web"]
    import sweshim as _sh
    _sh.load(f"{_root}/web/ephem4.bin", f"{_root}/web/tables.json")
    _sys.modules["swisseph"] = _sh

    class _E:
        pass
    n = 500
    e = _E()
    rng = np.random.default_rng(0)
    e.LON = rng.uniform(0, 360, (6, 18, n))
    e.SPD = rng.normal(0, 1, (6, 18, n))
    e.JD = np.full((6, n), 2400000.0) + rng.uniform(0, 100000, (6, n))
    F = build(e)
    names = [f[0] for f in F]
    assert len(names) == len(set(names)), "feature names must be unique"
    for nm, ex, v in F:
        assert v.shape == (n,), (nm, v.shape)
        assert np.all(np.isfinite(v)), nm
        assert len(ex) > 40, f"explanation too thin: {nm}"
    print(f"  {len(F)} named features, all unique, all finite, every one explained in >40 chars")
    from collections import Counter
    c = Counter("cross-chart" if "(older) to" in n else
                "own chart" if "own chart" in n else
                "numerology" if any(k in n for k in ("Life Path", "Personal Year", "Birthday number",
                                                     "Chaldean", "pillar", "Attitude", "digit sum",
                                                     "relationship number", "birth day", "birth month")) else
                "nakshatra" if "nakshatra" in n or "pada" in n else
                "lunation" if "Moon phase" in n or "illuminated" in n else "single body" for n in names)
    for k, v in c.most_common():
        print(f"    {k:<14} {v:>4}")
