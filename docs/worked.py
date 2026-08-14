"""
worked.py — one worked example per tradition, computed live for the couple on screen.

WHY NOT READ THE MODEL'S OWN COLUMNS. That would be the ideal worked example: the actual numbers the actual
block fed the actual model. The tradition modules DO name their columns internally — several of them literally
`return cols, names` — but `build()` hands back only `{key: array}` and the names are dropped at that boundary.
Recovering them means editing seventeen modules, and every one of those edits risks changing a block's width,
which is the one thing `verify_docs.py` refuses to publish a change in. So this file recomputes a small number
of quantities from the same shim instead, and every quantity is one that can be checked independently.

WHAT THIS IS NOT. It is not the model's reasoning. The model reads tens of thousands of columns and this shows
two or three human-readable ones per tradition, chosen because a reader can look them up and disagree. A
tradition's row in the table is its measured AUC; the example underneath says what the tradition is doing, not
why the model scored what it scored.

EVERY FIGURE IS DERIVED, NONE IS STORED. The sexagenary cycle is arithmetic on the year, the Long Count is
arithmetic on the Julian day, and everything astronomical comes from the same `sweshim` the model runs on. Run
this file directly to see the examples and the self-checks.

Usage:  ~/.artamatch-venv/bin/python web/worked.py [YYYY-MM-DD] [YYYY-MM-DD]
"""
import math

# The ephemeris is BOUND, not imported. In the browser `swisseph` is `sweshim` registered under that name
# before this module loads, but running this file directly has nothing registered yet and a top-level import
# would fail before __main__ could fix it. So the caller binds, and every function reads `swe` at call time.
swe = None


def bind(module):
    """Point this module at a Swiss Ephemeris implementation (the real one, or the project's numpy shim)."""
    global swe
    swe = module

HOUR = 8.0                      # the project's fixed birth hour, UT — the same one core.py uses
AYANAMSA_LAHIRI = 1

STEMS = ["jiǎ", "yǐ", "bǐng", "dīng", "wù", "jǐ", "gēng", "xīn", "rén", "guǐ"]
STEM_EL = ["wood", "wood", "fire", "fire", "earth", "earth", "metal", "metal", "water", "water"]
BRANCHES = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
            "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
NAKSHATRA = ["Aśvinī", "Bharaṇī", "Kṛttikā", "Rohiṇī", "Mṛgaśīrṣa", "Ārdrā", "Punarvasu", "Puṣya",
             "Aśleṣā", "Maghā", "Pūrva Phalgunī", "Uttara Phalgunī", "Hasta", "Citrā", "Svātī",
             "Viśākhā", "Anurādhā", "Jyeṣṭhā", "Mūla", "Pūrva Aṣāḍhā", "Uttara Aṣāḍhā", "Śravaṇā",
             "Dhaniṣṭhā", "Śatabhiṣā", "Pūrva Bhādrapadā", "Uttara Bhādrapadā", "Revatī"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
HAAB = ["Pop", "Wo", "Sip", "Sotz'", "Sek", "Xul", "Yaxk'in", "Mol", "Ch'en", "Yax", "Sak", "Keh",
        "Mak", "K'ank'in", "Muwan", "Pax", "K'ayab", "Kumk'u", "Wayeb"]
TZOLKIN = ["Imix", "Ik'", "Ak'b'al", "K'an", "Chikchan", "Kimi", "Manik'", "Lamat", "Muluk", "Ok",
           "Chuwen", "Eb'", "B'en", "Ix", "Men", "Kib'", "Kab'an", "Etz'nab'", "Kawak", "Ajaw"]
WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
RABJUNG_EL = ["fire", "earth", "iron", "water", "wood"]
# The Maya correlation constant: Julian day number of 0.0.0.0.0 (GMT / Thompson).
MAYA_EPOCH = 584283


def jd_of(d):
    y, m, dd = int(d[:4]), int(d[5:7] or 1), int(d[8:10] or 1)
    return swe.julday(y, max(1, m), max(1, dd), HOUR)


def _lon(jd, body, sidereal=False):
    flag = swe.FLG_SWIEPH | swe.FLG_SPEED
    if sidereal:
        swe.set_sid_mode(AYANAMSA_LAHIRI, 0, 0)
        return (swe.calc_ut(jd, body, flag)[0][0] - swe.get_ayanamsa_ut(jd)) % 360.0
    return swe.calc_ut(jd, body, flag)[0][0] % 360.0


def _lat(jd, body):
    return swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_SPEED)[0][1]


def sexagenary(year):
    """Stem-branch for a year. Index = (year - 4) mod 60, the standard alignment.

    1889 -> jǐ-Ox (earth ox) and 1984 -> jiǎ-Rat, the start of a cycle: both are checkable against any table.
    """
    i = (year - 4) % 60
    return STEMS[i % 10], STEM_EL[i % 10], BRANCHES[i % 12], i


def long_count(jd):
    """Maya Long Count from a Julian day number, plus the Calendar Round."""
    days = int(math.floor(jd + 0.5)) - MAYA_EPOCH
    baktun, r = divmod(days, 144000)
    katun, r = divmod(r, 7200)
    tun, r = divmod(r, 360)
    winal, kin = divmod(r, 20)
    tz = TZOLKIN[(days + 19) % 20]
    tz_n = (days + 3) % 13 + 1
    h = (days + 348) % 365
    haab = f"{h % 20} {HAAB[h // 20]}"
    return f"{baktun}.{katun}.{tun}.{winal}.{kin}", f"{tz_n} {tz}", haab


def moon_phase(jd):
    """Elongation of the Moon from the Sun, 0-360. 0 is new, 180 full."""
    return (_lon(jd, swe.MOON) - _lon(jd, swe.SUN)) % 360.0


def _phase_name(a):
    return ("new", "waxing crescent", "first quarter", "waxing gibbous", "full",
            "waning gibbous", "last quarter", "waning crescent")[int(((a + 22.5) % 360) // 45)]


def nakshatra_of(jd):
    lon = _lon(jd, swe.MOON, sidereal=True)
    i = int(lon // (360 / 27))
    pada = int((lon % (360 / 27)) // (360 / 108)) + 1
    return NAKSHATRA[i], pada, lon


def aspect_between(a, b):
    """The closest Ptolemaic aspect between two ecliptic longitudes, and how far off exact it is."""
    d = abs((a - b + 180) % 360 - 180)
    for ang, nm, orb in ((0, "conjunction", 12), (60, "sextile", 6), (90, "square", 6),
                         (120, "trine", 12), (180, "opposition", 12)):
        if abs(d - ang) <= orb:
            return nm, d, abs(d - ang)
    return None, d, None


def egyptian_civil(jd):
    """Day within the 365-day Egyptian civil year, and which of the 36 decans the Sun stands in."""
    days = int(math.floor(jd + 0.5))
    doy = days % 365
    decan = int(_lon(jd, swe.SUN) // 10) + 1
    return doy, decan


def examples(dob_man, dob_woman):
    """Every tradition, worked for one couple. Keys are the model's own tradition slugs."""
    jm, jw = jd_of(dob_man), jd_of(dob_woman)
    ym, yw = int(dob_man[:4]), int(dob_woman[:4])
    out = {}

    sm, em, bm, im = sexagenary(ym)
    sw, ew, bw, iw = sexagenary(yw)
    gap = (iw - im) % 12
    out["chinese"] = [
        f"{ym} is a {sm}-{bm} year ({em} {bm.lower()}); {yw} is a {sw}-{bw} year ({ew} {bw.lower()}).",
        f"Their branches sit {gap} apart on the twelve-branch circle"
        + (" — the same branch" if gap == 0 else
           ", a supportive triad (four apart)" if gap in (4, 8) else
           ", the classic opposition (six apart)" if gap == 6 else "") + ".",
        f"Elements {em} and {ew}: "
        + ("the same phase" if em == ew else
           f"{em} generates {ew}" if _generates(em, ew) else
           f"{ew} generates {em}" if _generates(ew, em) else
           f"{em} and {ew} stand in an overcoming relation"),
    ]

    lc_m, tz_m, hb_m = long_count(jm)
    lc_w, tz_w, hb_w = long_count(jw)
    out["mesoamerican"] = [
        f"Long Count {lc_m} for the man, {lc_w} for the woman.",
        f"Calendar Round: {tz_m}, {hb_m} and {tz_w}, {hb_w}.",
        f"The distance number between the two births is {int(abs(math.floor(jw) - math.floor(jm))):,} days.",
    ]

    pm, pw = moon_phase(jm), moon_phase(jw)
    out["lunar_calendrical"] = [
        f"Sun–Moon elongation {pm:.1f}° at his birth ({_phase_name(pm)} Moon) and {pw:.1f}° at hers "
        f"({_phase_name(pw)}).",
        f"The two phases differ by {abs((pw - pm + 180) % 360 - 180):.1f}°.",
        f"Their births are {abs(jw - jm) / 29.530588:.1f} synodic months apart, "
        f"{abs(jw - jm) / 6585.3213:.2f} of a Saros.",
    ]

    out["harmonics"] = [
        f"The Moon's ecliptic latitude is {_lat(jm, swe.MOON):+.2f}° at his birth and "
        f"{_lat(jw, swe.MOON):+.2f}° at hers.",
        f"Venus sits at latitude {_lat(jm, swe.VENUS):+.2f}° and {_lat(jw, swe.VENUS):+.2f}° — a contact in "
        f"latitude is a closeness the ecliptic longitude alone cannot see.",
    ]

    nm_, pdm, lm = nakshatra_of(jm)
    nw_, pdw, lw = nakshatra_of(jw)
    out["vedic_core"] = [
        f"His Moon stands in {nm_} pada {pdm} (sidereal {lm:.2f}°); hers in {nw_} pada {pdw} ({lw:.2f}°).",
        f"That places the Moons in sidereal {SIGNS[int(lm // 30)]} and {SIGNS[int(lw // 30)]}.",
    ]
    steps = (NAKSHATRA.index(nw_) - NAKSHATRA.index(nm_)) % 27
    out["vedic_match"] = [
        f"The nakṣatra pair is {nm_} → {nw_}, {steps} of 27 steps apart, which is the entry point "
        f"for every kūṭa in aṣṭakūṭa.",
        f"Their Moon signs are {SIGNS[int(lm // 30)]} and {SIGNS[int(lw // 30)]}, "
        f"{abs(int(lm // 30) - int(lw // 30))} signs apart — the rāśi kūṭa.",
    ]
    # A real tally rather than a description of one: aṣṭakavarga counts how many grahas fall in a given sign,
    # so this counts his seven against her Moon's sign and hers against his. It is the shape of a bindu count,
    # not the bindu count itself, and it says so.
    GRAHAS = [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN]
    m_signs = [int(_lon(jm, g, True) // 30) for g in GRAHAS]
    w_signs = [int(_lon(jw, g, True) // 30) for g in GRAHAS]
    her_moon, his_moon = w_signs[1], m_signs[1]
    out["vedic_ashtakavarga"] = [
        f"His seven grahas occupy sidereal signs {sorted(set(s + 1 for s in m_signs))} and hers "
        f"{sorted(set(s + 1 for s in w_signs))}, counting Aries as 1.",
        f"{sum(1 for s in m_signs if s == her_moon)} of his seven stand in her Moon's sign "
        f"({SIGNS[her_moon]}), and {sum(1 for s in w_signs if s == his_moon)} of hers in his "
        f"({SIGNS[his_moon]}) — the shape of a bindu tally, which aṣṭakavarga builds into 7 × 12 = 84 cells.",
        f"Ṣaḍbala then weighs the same seven planets six ways; sthāna bala alone runs over 5 components, "
        f"so the block carries {7 * 6} strength figures per chart before any pairing.",
    ]

    a_nm, a_d, a_off = aspect_between(_lon(jm, swe.SUN), _lon(jw, swe.SUN))
    out["hellenistic"] = [
        f"His Sun is at {_lon(jm, swe.SUN):.2f}° ({SIGNS[int(_lon(jm, swe.SUN) // 30)]}), hers at "
        f"{_lon(jw, swe.SUN):.2f}° ({SIGNS[int(_lon(jw, swe.SUN) // 30)]}), {a_d:.2f}° apart.",
        (f"That is a {a_nm}, {a_off:.2f}° from exact." if a_nm
         else "No Ptolemaic aspect holds between the two Suns at classical orbs."),
    ]
    out["persian_arabic"] = [
        f"The Lot of Fortune needs an ascendant, so with no birth time this tradition works from the "
        f"Sun–Moon arc instead: {(_lon(jm, swe.MOON) - _lon(jm, swe.SUN)) % 360:.2f}° for him, "
        f"{(_lon(jw, swe.MOON) - _lon(jw, swe.SUN)) % 360:.2f}° for her.",
        f"Reception asks whether each Sun sits in a sign the other's ruler governs — "
        f"{SIGNS[int(_lon(jm, swe.SUN) // 30)]} and {SIGNS[int(_lon(jw, swe.SUN) // 30)]} here.",
    ]

    mid = 0.5 * (jm + jw)
    y, mo, d, _ = swe.revjul(mid)
    out["modern_western"] = [
        f"The Davison chart is cast for the midpoint in time between the two births: {y:04d}-{mo:02d}-{d:02d}.",
        f"Its Sun is at {_lon(mid, swe.SUN):.2f}° ({SIGNS[int(_lon(mid, swe.SUN) // 30)]}) and its Moon at "
        f"{_lon(mid, swe.MOON):.2f}°.",
        f"The composite instead averages the two charts' positions, which puts its Sun at "
        f"{_mid_angle(_lon(jm, swe.SUN), _lon(jw, swe.SUN)):.2f}° — the two methods disagree, and that "
        f"disagreement is itself a feature.",
    ]

    dm, decm = egyptian_civil(jm)
    dw, decw = egyptian_civil(jw)
    out["babylonian_egyptian"] = [
        f"Day {dm} of the 365-day Egyptian civil year at his birth, day {dw} at hers — the calendar drifts "
        f"a day every four years against the seasons, so the offset is a slow clock.",
        f"The Sun stands in decan {decm} of 36 for him and decan {decw} for her.",
        f"Jupiter's goal-year period is 83 years: their births are {abs(jw - jm) / (83 * 365.2425):.3f} of "
        f"one apart.",
    ]

    sir = 99.9
    out["african"] = [
        f"Sirius is the anchor of the Sothic year. Its elongation from the Sun is "
        f"{_elong(jm, sir):.1f}° at his birth and {_elong(jw, sir):.1f}° at hers; a heliacal rising needs "
        f"roughly 10° or more.",
        f"The Dogon sigui runs on a 60-year ceremonial period: the births are "
        f"{abs(jw - jm) / (60 * 365.2425):.3f} of one apart.",
    ]
    out["aboriginal_australian"] = [
        f"The Emu in the Sky is a dark constellation, so what matters is where the Sun is on the year: "
        f"{_lon(jm, swe.SUN):.1f}° of ecliptic longitude for him, {_lon(jw, swe.SUN):.1f}° for her.",
        f"Barnumbirr is Venus as the morning star: {'a morning star' if _morning(jm) else 'an evening star'} "
        f"at his birth, {'a morning star' if _morning(jw) else 'an evening star'} at hers.",
    ]
    out["indigenous_americas"] = [
        f"Náhookǫs, the revolving pair, is read by its rotation about the pole at midnight. Local sidereal "
        f"time stands in for that angle: {swe.sidtime(jm) * 15:.1f}° for him, {swe.sidtime(jw) * 15:.1f}° "
        f"for her.",
        f"The Pawnee morning and evening stars are Venus and Mars: Venus at "
        f"{_lon(jm, swe.VENUS):.1f}° and Mars at {_lon(jm, swe.MARS):.1f}° at his birth.",
    ]

    out["tibetan_seasia"] = [
        f"The Tibetan rabjung is a sixty-year cycle of animal crossed with element: "
        f"{RABJUNG_EL[(ym - 1027) % 5]}-{BRANCHES[(ym - 1027) % 12]} for {ym}, "
        f"{RABJUNG_EL[(yw - 1027) % 5]}-{BRANCHES[(yw - 1027) % 12]} for {yw}.",
        f"Burmese mahabote is built from the weekday of birth and a remainder of the year: "
        f"{WEEKDAY[int(math.floor(jm + 0.5)) % 7]} and remainder {ym % 7} for him, "
        f"{WEEKDAY[int(math.floor(jw + 0.5)) % 7]} and {yw % 7} for her.",
        f"The Javanese pawukon runs several week-lengths at once; on the five-day pasaran they fall "
        f"{int(math.floor(jm + 0.5)) % 5} and {int(math.floor(jw + 0.5)) % 5}.",
    ]
    dm_i, dw_i = int(math.floor(jm + 0.5)), int(math.floor(jw + 0.5))
    out["east_asian_deep"] = [
        f"Korean saju reads four pillars. The year pillar is {sm}-{bm} (index {im} of 60) for him and "
        f"{sw}-{bw} (index {iw}) for her.",
        f"The day pillar comes from the day count itself: {STEMS[(dm_i + 9) % 10]}-"
        f"{BRANCHES[(dm_i + 1) % 12]} and {STEMS[(dw_i + 9) % 10]}-{BRANCHES[(dw_i + 1) % 12]}, "
        f"which are {(dw_i - dm_i) % 60} steps apart in the sixty-day cycle.",
        f"Mongolian zurkhai counts the same sixty-year jaran from a different epoch and starts its year at "
        f"Tsagaan Sar, so their jaran positions are {(ym - 1027) % 60} and {(yw - 1027) % 60} — and a January "
        f"or February birth can fall in the previous animal year.",
    ]

    out["uranian"] = [
        f"The Hamburg School works on a 90° dial, so every position is taken modulo 90: his Sun at "
        f"{_lon(jm, swe.SUN) % 90:.2f}° and hers at {_lon(jw, swe.SUN) % 90:.2f}°, "
        f"{abs((_lon(jm, swe.SUN) % 90) - (_lon(jw, swe.SUN) % 90)):.2f}° apart on the dial.",
        f"On the 22.5° eighth-harmonic dial those become {_lon(jm, swe.SUN) % 22.5:.2f}° and "
        f"{_lon(jw, swe.SUN) % 22.5:.2f}°.",
        "The hypothetical bodies — Cupido through Poseidon — are added to the same dial, and a "
        "“picture” is any three of them summing to the same midpoint.",
    ]
    return out


def _generates(a, b):
    """The sheng cycle: wood feeds fire, fire makes earth, earth bears metal, metal carries water, water grows wood."""
    return {"wood": "fire", "fire": "earth", "earth": "metal", "metal": "water", "water": "wood"}.get(a) == b


def _mid_angle(a, b):
    d = (b - a + 180) % 360 - 180
    return (a + d / 2) % 360


def _elong(jd, _unused):
    """Sirius is not in the shipped asset, so the Sun's distance from Sirius's ecliptic longitude is used.

    Sirius sits near 104.4 deg of ecliptic longitude in this era. Naming the approximation rather than
    implying the star itself was integrated.
    """
    return abs((_lon(jd, swe.SUN) - 104.4 + 180) % 360 - 180)


def _morning(jd):
    """Venus rises before the Sun when it trails the Sun in longitude by less than 180 degrees."""
    return ((_lon(jd, swe.SUN) - _lon(jd, swe.VENUS)) % 360) < 180


def _selftest():
    assert sexagenary(1984)[:3] == ("jiǎ", "wood", "Rat"), sexagenary(1984)
    assert sexagenary(1889)[:3] == ("jǐ", "earth", "Ox"), sexagenary(1889)
    assert sexagenary(2024)[:3] == ("jiǎ", "wood", "Dragon"), sexagenary(2024)
    print("  sexagenary: 1984 jiǎ-Rat, 1889 jǐ-Ox, 2024 jiǎ-Dragon")
    lc, tz, hb = long_count(swe.julday(2012, 12, 21, 12.0))
    assert lc == "13.0.0.0.0", lc
    print(f"  Long Count of 2012-12-21 is {lc}, {tz}, {hb}")
    assert _generates("wood", "fire") and not _generates("fire", "wood")
    print("  five phases: wood generates fire, fire does not generate wood")
    ex = examples("1889-04-16", "1893-07-08")
    import json
    have = set(ex)
    print(f"  {len(have)} traditions, {sum(len(v) for v in ex.values())} lines")
    for k in sorted(ex):
        assert ex[k] and all(isinstance(x, str) and len(x) > 20 for x in ex[k]), k
    print(json.dumps({k: ex[k] for k in ("chinese", "vedic_core", "modern_western")},
                     ensure_ascii=False, indent=1))
    return ex


if __name__ == "__main__":
    import sys
    root = __file__.rsplit("/", 1)[0]
    sys.path.insert(0, root)
    import sweshim
    sweshim.load(root + "/ephem4.bin", root + "/tables.json")
    sys.modules["swisseph"] = sweshim
    bind(sweshim)
    a = sys.argv[1] if len(sys.argv) > 1 else "1889-04-16"
    b = sys.argv[2] if len(sys.argv) > 2 else "1893-07-08"
    _selftest()
    print(f"\n  worked for {a} x {b}:")
    for k, lines in examples(a, b).items():
        print(f"    {k}")
        for ln in lines:
            print(f"        {ln}")
