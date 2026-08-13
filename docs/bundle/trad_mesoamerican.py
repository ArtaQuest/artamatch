"""
trad_mesoamerican.py — the Mesoamerican calendars (Maya and Aztec) as feature blocks.

WHAT THIS TRADITION ACTUALLY IS, AND WHY IT FITS THIS DATASET UNUSUALLY WELL

The Mesoamerican systems are not zodiacal. Nothing here is a planetary longitude: the whole doctrine
is a set of interlocking *day counts*, and the unit of divination is the WHOLE DAY. A Maya day-keeper
(ajq'ij) or an Aztec tonalpouhqui reads the day a person was born, not the hour. So — uniquely among
the traditions in this exercise — the "no birth time" limit costs almost nothing: a birth DATE is
exactly the input the tradition wants.

The one residual limit, stated plainly: the Mesoamerican day began at sunrise (Landa; some sources
say sunset), not at midnight, and we have neither a birth time nor a birth place. A birth in the
hours between local midnight and local sunrise therefore belongs to the PREVIOUS Mesoamerican day,
and we cannot tell which births those are. Every instant in `core` is 12:00 UT, so the assignment is
right for the great majority of births and off by exactly one day for a minority near the boundary
(and for births far from the Greenwich meridian near local midnight). One day of slip changes the
day-sign and the coefficient completely — this is the dominant noise source in every block below,
and it cannot be reduced with the data available.

THE CORRELATION CONSTANT, SAID OUT LOUD

Every count below is anchored on the GOODMAN–MARTINEZ–THOMPSON correlation, **JDN 584283**: Long
Count 0.0.0.0.0 = 4 Ajaw 8 Kumk'u = Julian Day Number 584283. This is the standard ("584283 GMT")
correlation of Thompson 1935/1950 and of essentially all modern Maya epigraphy. Three consequences
are asserted in the self-test as proof the arithmetic is right:

  * 21 December 2012 (JDN 2456283)  ->  13.0.0.0.0, 4 Ajaw 3 K'ank'in, Lord of the Night G9
  * 0.0.0.0.0                       ->  4 Ajaw 8 Kumk'u
  * the four Haab year bearers that fall out of GMT are Ik', Manik', Eb', Kab'an — exactly the
    Classic-period (Tikal) year-bearer set, one in each of the four world-quarters.

WHAT IS COMPUTED (and the authority for each rule)

  Tzolk'in, the 260-day sacred round — 20 day-signs x 13 coefficients. Position 0..259, day-sign
    0..19, coefficient 1..13. `tzolkin_position = (long_count_day + 159) mod 260` because 4 Ajaw sits
    at position 159 of the round.
  Haab, the 365-day vague year — 18 "months" of 20 days plus the 5-day Wayeb. `haab_position =
    (long_count_day + 348) mod 365` because 8 Kumk'u is position 348. The five Wayeb days are the
    nameless, unlucky days of Landa's *Relación de las cosas de Yucatán*; born-in-Wayeb and
    married-in-Wayeb are emitted as flags.
  Calendar Round — the 18,980-day (52 Haab year) meshing of the two, plus the YEAR BEARER: the
    day-sign standing on the seating of Pop, `(day_sign - haab_position) mod 20`, with its
    coefficient. Under GMT this yields the Classic set {Ik', Manik', Eb', Kab'an}, one per
    world-quarter — which is the documented Maya scheme, not something imposed here.
  Long Count — baktun / katun / tun / winal / k'in, plus the "wheel of the katuns": the coefficient
    of the Ajaw day on which the current katun ends (13, 11, 9, 7, ... — the katun prophecy cycle of
    the Books of Chilam Balam). Distance numbers (the LC intervals Maya inscriptions actually record
    between two events) are a separate, deliberately-quarantined block, because a wedding-minus-birth
    interval is an age and has nothing astrological about it.
  Nine Lords of the Night, G1–G9 — locked to the Long Count. Thompson (Maya Hieroglyphic Writing,
    1950) established that the Glyph-G cycle runs so that every katun ending carries G9; since
    7200 = 9 x 800, that fixes the phase to `G = ((d - 1) mod 9) + 1`, i.e. d ≡ 0 (mod 9) -> G9.
  The 819-day count — four directional/colour stations (East-red, North-white, West-black,
    South-yellow), period 4 x 819 = 3276 days. 819 = 63 x 13, so the Tzolk'in COEFFICIENT is
    invariant across the stations of a series, and Thompson's documented property is that the
    stations fall on a day with coefficient 1; 819 mod 20 = 19, so the day-SIGN retreats one step per
    station (1 Ajaw, 1 Kawak, 1 Etz'nab', ...). The phase here is fixed by that property, anchored on
    the 1 Ajaw station (d ≡ 140 mod 819 — verified in the self-test). HONEST CAVEAT: sources differ on
    which Palenque station is the absolute anchor, so the four quadrant LABELS are fixed only up to
    rotation. That does not affect the cycle structure, and it does not affect any pair feature
    (a difference of quadrants is invariant under relabelling).
  Aztec tonalpohualli — the same 260-day count with the Nahuatl day-sign names, anchored
    independently on Caso's correlation: the fall of Tenochtitlan, 13 August 1521 (Julian) = JDN
    2276828 = the day 1 Coatl. A NICE CONFIRMATION, asserted in the self-test: that day is 1
    Chikchan under GMT — Chikchan is the Maya cognate of Coatl (serpent) and the coefficient is 1, so
    Caso's Aztec count and the GMT Maya count are in exact phase, and the Aztec day-sign adds no
    information beyond a rename. Where the Aztec side DOES add something is the pair structure, so
    the Aztec block is built out of the 13 Lords of the Day (Tonalteuctin, keyed to the coefficient)
    and the 9 Lords of the Night (Yohualteuctin) as 13x13 and 9x9 PAIR interactions.
  The four world-direction groups of the day-signs — Codex Fejérváry-Mayer p.1 / Codex Borgia: the
    20 signs run East, North, West, South, East, ... so direction = day_sign_index mod 4. This
    reproduces the documented quarters exactly (East: Cipactli, Coatl, Atl, Acatl, Ollin; North:
    Ehecatl, Miquiztli, Itzcuintli, Ocelotl, Tecpatl; West: Calli, Mazatl, Ozomatli, Cuauhtli,
    Quiahuitl; South: Cuetzpalin, Tochtli, Malinalli, Cozcacuauhtli, Xochitl) and is asserted in the
    self-test.
  Dreamspell / Wavespell — a SEPARATE, CLEARLY LABELLED block. This is José Argüelles' modern
    (1987–1990) "13-Moon / Dreamspell" system, NOT the classical count. It uses its own correlation
    and drops the leap day (29 February is not counted), so it drifts against the true Tzolk'in and
    is genuinely different information rather than a rename. Anchored on the widely published
    Dreamspell value 21 December 2012 = Kin 207, Blue Crystal Hand — which is internally consistent
    (kin 207 -> seal 7 Hand, tone 12 Crystal, colour Blue). Emits kin / tone / solar seal / colour /
    wavespell / castle and the full Dreamspell Oracle relations between the partners: analog
    (seal_i + seal_j ≡ 17 mod 20), antipode (seal_i - seal_j ≡ 10 mod 20), occult (≡ 19 mod 20),
    guide (tone-driven, same colour), same colour, same seal, same tone.

PAIRING — THE TRADITION'S OWN TESTS

Mesoamerica has no Ashtakoot-style points table; nothing in the sources sums a compatibility score.
Pretending otherwise would be inventing doctrine. What the sources DO give are individual, checkable
tests, and those are computed exactly and emitted individually, plus one additive tally whose WEIGHTS
are labelled openly as this module's assembly (not a traditional table) so a model can reweight them:

  * Sahagún, *Florentine Codex* Book VI ch. 23 (on marriage): the matchmakers chose the wedding day
    from the favourable signs **Acatl, Ozomatli, Cipactli, Cuauhtli, Calli**. Computed on the actual
    wedding day-sign — a real yes/no test of the tradition, on the real event date.
  * Landa: birth or marriage inside the five Wayeb days is inauspicious.
  * Same day-sign ("one nawal"), same coefficient, same trecena — allied.
  * Same world-quarter (Δsign ≡ 0 mod 4) — allied; opposite quarter (Δdirection = 2) — opposed.
  * Antipodal day-signs, Δsign = 10 — the opposing day of the 20-round.
  * Same Lord of the Night, same 819-day quadrant, same year-bearer quarter.

REPRESENTATIONS

The same doctrine is encoded four ways on purpose, because they score very differently: circular
(cos/sin of a cycle and of a difference of cycles, several harmonics), one-hot bins (day-sign,
coefficient, trecena, Haab month, G-lord, quadrant), pair interactions (Δ one-hot, Σ one-hot, the
full 20x20 sign pair, 13x13 lord pairs), and orb-style Gaussian kernels over the 20-sign circle at
the tradition's own intervals (0, Δ4 = 72 degrees, Δ10 = 180 degrees) at two widths.

Deterministic, no randomness, no I/O, no use of E.Y.
"""

import numpy as np

TRADITION = "Mesoamerican (Maya Tzolk'in/Haab/Long Count at GMT 584283, Aztec tonalpohualli, Dreamspell)"

# ── constants ───────────────────────────────────────────────────────────────────────────────────
GMT = 584283            # Goodman-Martinez-Thompson: JDN of Long Count 0.0.0.0.0 = 4 Ajaw 8 Kumk'u
TZ_AT_ZERO = 159        # position of 4 Ajaw in the 260-round
HAAB_AT_ZERO = 348      # position of 8 Kumk'u in the 365-round (month 17, day 8)
E819_STATION = 140      # d ≡ 140 (mod 819) are the "1 Ajaw" stations (Thompson: coefficient 1)
CASO_JDN = 2276828      # 13 Aug 1521 Julian = fall of Tenochtitlan = the day 1 Coatl (Caso)
DS_ANCHOR_JDN = 2456283  # 21 Dec 2012
DS_ANCHOR_KIN = 207      # Dreamspell: Kin 207, Blue Crystal Hand

DAYSIGN = ["Imix", "Ik'", "Ak'b'al", "K'an", "Chikchan", "Kimi", "Manik'", "Lamat", "Muluk", "Ok",
           "Chuwen", "Eb'", "B'en", "Ix", "Men", "Kib'", "Kab'an", "Etz'nab'", "Kawak", "Ajaw"]
AZTEC = ["Cipactli", "Ehecatl", "Calli", "Cuetzpalin", "Coatl", "Miquiztli", "Mazatl", "Tochtli",
         "Atl", "Itzcuintli", "Ozomatli", "Malinalli", "Acatl", "Ocelotl", "Cuauhtli",
         "Cozcacuauhtli", "Ollin", "Tecpatl", "Quiahuitl", "Xochitl"]
HAABM = ["Pop", "Wo", "Sip", "Sotz'", "Sek", "Xul", "Yaxk'in", "Mol", "Ch'en", "Yax", "Sak", "Keh",
         "Mak", "K'ank'in", "Muwan", "Pax", "K'ayab", "Kumk'u", "Wayeb"]
DIRNAME = ["East/red", "North/white", "West/black", "South/yellow"]
# Sahagun, Florentine Codex Book VI ch.23: the day signs the matchmakers held good for a marriage
SAHAGUN_MARRIAGE = [AZTEC.index(s) for s in ("Acatl", "Ozomatli", "Cipactli", "Cuauhtli", "Calli")]


# ── small encoders ──────────────────────────────────────────────────────────────────────────────
def _oh(idx, k):
    """One-hot of an integer index, wrapped into [0, k)."""
    idx = np.mod(np.asarray(idx).astype(np.int64), k)
    out = np.zeros((idx.shape[0], k), dtype=np.float64)
    out[np.arange(idx.shape[0]), idx] = 1.0
    return out


def _cyc(x, period, h=1):
    """cos/sin of x on a cycle of `period`, for harmonics 1..h."""
    x = np.asarray(x, dtype=np.float64)
    cols = []
    for j in range(1, h + 1):
        a = 2.0 * np.pi * j * x / float(period)
        cols += [np.cos(a), np.sin(a)]
    return np.stack(cols, axis=-1)


def _col(x):
    return np.asarray(x, dtype=np.float64).reshape(-1, 1)


def _cdist(a, b, k):
    """Shortest distance between two positions on a cycle of length k, in steps."""
    d = np.mod(np.asarray(a) - np.asarray(b), k)
    return np.minimum(d, k - d).astype(np.float64)


# ── the Gregorian conversion needed only by the Dreamspell (leap-day) count ─────────────────────
def _greg(jdn):
    """JDN (noon-based, integer) -> proleptic Gregorian (year, month, day). Fliegel-Van Flandern."""
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    dd = (4 * c + 3) // 1461
    e = c - (1461 * dd) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    mon = m + 3 - 12 * (m // 10)
    yr = 100 * b + dd - 4800 + m // 10
    return yr, mon, day


def _ds_index(jdn):
    """A day index that SKIPS every 29 February — the Dreamspell count ignores the leap day."""
    y, m, d = _greg(jdn)
    leaps = (y - 1) // 4 - (y - 1) // 100 + (y - 1) // 400
    isleap = ((np.mod(y, 4) == 0) & (np.mod(y, 100) != 0)) | (np.mod(y, 400) == 0)
    past = (m > 2) | ((m == 2) & (d == 29))
    return jdn - (leaps + (isleap & past).astype(np.int64))


_DS0 = int(_ds_index(np.array([DS_ANCHOR_JDN], dtype=np.int64))[0])


# ── the calendars ───────────────────────────────────────────────────────────────────────────────
def calendars(JD):
    """Every Mesoamerican count for an array of Julian days. Returns int arrays of JD's shape."""
    jdn = np.floor(np.asarray(JD, dtype=np.float64) + 0.5).astype(np.int64)
    d = jdn - GMT                                     # days since 0.0.0.0.0 (Long Count day number)
    C = {"jdn": jdn, "d": d}

    # Tzolk'in
    C["tzpos"] = np.mod(d + TZ_AT_ZERO, 260)
    C["sign"] = np.mod(C["tzpos"], 20)
    C["num"] = np.mod(C["tzpos"], 13) + 1
    C["trecena"] = C["tzpos"] // 13                   # 0..19, which of the 20 trecenas
    C["trec_sign"] = np.mod(13 * C["trecena"], 20)    # the day-sign that names the trecena

    # Haab
    C["haabpos"] = np.mod(d + HAAB_AT_ZERO, 365)
    C["hmonth"] = C["haabpos"] // 20                  # 0..17 named months, 18 = Wayeb
    C["hday"] = np.mod(C["haabpos"], 20)
    C["wayeb"] = (C["hmonth"] == 18).astype(np.int64)

    # Calendar Round + year bearer (day-sign seated on 0 Pop)
    C["cr"] = np.mod(d, 18980)
    C["cryear"] = C["cr"] // 365                      # 0..51, the Haab year of the 52-year round
    C["bearer"] = np.mod(C["sign"] - C["haabpos"], 20)
    C["bearer_num"] = np.mod(C["num"] - 1 - C["haabpos"], 13) + 1
    C["bearer_dir"] = np.mod(C["bearer"], 4)

    # Long Count
    C["baktun"] = d // 144000
    C["katun_abs"] = d // 7200
    C["katun"] = np.mod(C["katun_abs"], 20)
    C["tun"] = np.mod(d // 360, 20)
    C["winal"] = np.mod(d // 20, 18)
    C["kin"] = np.mod(d, 20)
    C["katun_ajaw"] = np.mod((C["katun_abs"] + 1) * 7200 + 3, 13) + 1   # katun-wheel coefficient

    # Nine Lords of the Night: G9 on every katun ending (Thompson 1950)
    C["g"] = np.mod(d - 1, 9) + 1

    # the 819-day count, four directional stations
    C["e819"] = np.mod(d - E819_STATION, 819)
    C["quad819"] = np.mod((d - E819_STATION) // 819, 4)

    # the four world-quarters of the day-signs (Fejervary-Mayer p.1)
    C["dir"] = np.mod(C["sign"], 4)

    # Aztec: Caso's anchor. Nine Lords of the Night counted from the 1 Cipactli that opens the
    # 260-round holding 13 Aug 1521 (which is position 104 of that round).
    az0 = CASO_JDN - 104 - GMT
    C["az_night"] = np.mod(d - az0, 9) + 1
    C["az_day_lord"] = C["num"]                        # Tonalteuctin: keyed to the coefficient

    # Dreamspell (modern, Arguelles) — leap day not counted
    kin = np.mod(_ds_index(jdn) - _DS0 + (DS_ANCHOR_KIN - 1), 260) + 1
    C["ds_kin"] = kin
    C["ds_tone"] = np.mod(kin - 1, 13) + 1
    C["ds_seal"] = np.mod(kin - 1, 20) + 1
    C["ds_color"] = np.mod(C["ds_seal"] - 1, 4)
    C["ds_wave"] = (kin - 1) // 13 + 1
    C["ds_castle"] = (kin - 1) // 52 + 1
    # Dreamspell guide: same colour, offset driven by the tone
    C["ds_guide"] = np.mod(C["ds_seal"] - 1 + 4 * np.mod(3 * (C["ds_tone"] - 1), 5), 20) + 1
    return C


# ── the feature blocks ──────────────────────────────────────────────────────────────────────────
def build(E):
    C = calendars(E.JD)
    iO, iY, iW, iPO, iPY, iDV = 0, 1, 2, 3, 4, 5
    ALL = (iO, iY, iW, iPO, iPY, iDV)
    MAIN = (iO, iY, iW, iDV)
    PAIRS = [(iO, iY), (iO, iW), (iY, iW), (iO, iDV)]
    B = {}

    # 1 ── Tzolk'in as smooth circles, every instant ─────────────────────────────────────────────
    c = []
    for s in ALL:
        c += [_cyc(C["sign"][s], 20, 2), _cyc(C["num"][s] - 1, 13, 2), _cyc(C["tzpos"][s], 260, 3)]
    B["meso: tzolkin circular per instant"] = np.concatenate(c, axis=1)

    # 2 ── Tzolk'in differences between instants (offset-invariant by construction) ──────────────
    c = []
    for a, b in PAIRS:
        c += [_cyc(C["sign"][a] - C["sign"][b], 20, 3),
              _cyc(C["num"][a] - C["num"][b], 13, 3),
              _cyc(C["tzpos"][a] - C["tzpos"][b], 260, 3),
              np.stack([_cdist(C["sign"][a], C["sign"][b], 20),
                        _cdist(C["num"][a], C["num"][b], 13),
                        _cdist(C["tzpos"][a], C["tzpos"][b], 260)], axis=-1)]
    B["meso: tzolkin pair differences circular"] = np.concatenate(c, axis=1)

    # 3 ── the discrete bins the day-keeper actually names ───────────────────────────────────────
    c = [_oh(C["sign"][s], 20) for s in MAIN]
    c += [_oh(C["num"][s] - 1, 13) for s in (iO, iY, iW)]
    c += [_oh(C["trecena"][s], 20) for s in (iO, iY, iW)]
    B["meso: tzolkin day-sign + trecena one-hot"] = np.concatenate(c, axis=1)

    # 4 ── Haab vague year, Calendar Round, year bearer ──────────────────────────────────────────
    c = []
    for s in MAIN:
        c += [_cyc(C["haabpos"][s], 365, 2), _cyc(C["hday"][s], 20, 1),
              _col(C["hmonth"][s] / 18.0), _col(C["wayeb"][s]),
              _cyc(C["cr"][s], 18980, 2), _cyc(C["cryear"][s], 52, 2)]
    c += [_oh(C["hmonth"][s], 19) for s in (iO, iY, iW)]
    c += [_oh(C["bearer_dir"][s], 4) for s in (iO, iY, iW)]
    c += [_oh(C["bearer_num"][s] - 1, 13) for s in (iO, iY)]
    for a, b in PAIRS[:3]:
        c += [_cyc(C["haabpos"][a] - C["haabpos"][b], 365, 2),
              _col(C["hmonth"][a] == C["hmonth"][b]),
              _col(C["bearer"][a] == C["bearer"][b])]
    c += [_cyc(C["cryear"][iO] - C["cryear"][iY], 52, 2),
          _oh(C["bearer_dir"][iO] - C["bearer_dir"][iY], 4)]
    B["meso: haab + calendar round + year bearer"] = np.concatenate(c, axis=1)

    # 5 ── Long Count components + the katun prophecy wheel ──────────────────────────────────────
    c = []
    for s in (iO, iY, iW):
        c += [np.stack([C["baktun"][s], C["katun"][s], C["tun"][s],
                        C["winal"][s], C["kin"][s]], axis=-1).astype(np.float64),
              _cyc(C["tun"][s], 20), _cyc(C["winal"][s], 18), _cyc(C["kin"][s], 20)]
    c += [_oh(C["katun_ajaw"][s] - 1, 13) for s in (iO, iY, iW)]
    B["meso: long count components + katun wheel"] = np.concatenate(c, axis=1)

    # 6 ── distance numbers: the LC intervals an inscription records between two events.
    #      Quarantined in their own tiny block because these are ages, not divination.
    B["meso: distance numbers (LC intervals)"] = np.concatenate([
        _col((C["d"][iW] - C["d"][iO]) / 360.0),        # older's age at the wedding, in tuns
        _col((C["d"][iW] - C["d"][iY]) / 360.0),        # younger's age at the wedding, in tuns
        _col((C["d"][iY] - C["d"][iO]) / 360.0),        # the gap between the births, in tuns
        _col(C["d"][iW] / 7200.0),                      # the wedding's katun position in the era
    ], axis=1)

    # 7 ── the Nine Lords of the Night, G1-G9 ────────────────────────────────────────────────────
    c = []
    for s in MAIN:
        c += [_oh(C["g"][s] - 1, 9), _cyc(C["g"][s] - 1, 9, 2)]
    for a, b in PAIRS[:3]:
        c += [_oh(C["g"][a] - C["g"][b], 9), _col(C["g"][a] == C["g"][b])]
    B["meso: nine lords of the night G1-G9"] = np.concatenate(c, axis=1)

    # 8 ── the 819-day count and its four colour-directions ──────────────────────────────────────
    c = []
    for s in MAIN:
        c += [_col(C["e819"][s] / 819.0), _cyc(C["e819"][s], 819, 2),
              _oh(C["quad819"][s], 4), _cyc(C["quad819"][s], 4)]
    for a, b in PAIRS[:3]:
        c += [_oh(C["quad819"][a] - C["quad819"][b], 4), _col(C["quad819"][a] == C["quad819"][b])]
    B["meso: 819-day cycle + directional quadrant"] = np.concatenate(c, axis=1)

    # 9 ── the four world-quarters, the pairing rule of the Fejervary-Mayer cross ────────────────
    c = [_oh(C["dir"][s], 4) for s in MAIN]
    c += [_oh(4 * C["dir"][iO] + C["dir"][iY], 16),
          _oh(4 * C["bearer_dir"][iO] + C["bearer_dir"][iY], 16)]
    c += [_oh(C["bearer_dir"][s], 4) for s in (iO, iY)]
    for a, b in PAIRS[:3]:
        dd = np.mod(C["dir"][a] - C["dir"][b], 4)
        c += [_oh(dd, 4), _col(dd == 0), _col(dd == 2), _col((dd == 1) | (dd == 3))]
    B["meso: four world-quarters pairing"] = np.concatenate(c, axis=1)

    # 10 ── day-sign pair relations: allied, antipodal, analog couplet, occult partner ───────────
    def _rel(a, b, full):
        si, sj = C["sign"][a], C["sign"][b]
        dd = np.mod(si - sj, 20)
        ss = np.mod(si + sj, 20)
        flags = [_col(dd == 0),                        # one nawal: the same day-sign
                 _col(np.mod(dd, 4) == 0),             # same world-quarter (allied)
                 _col(dd == 10),                       # antipodal: the opposing day of the round
                 _col(ss == 17),                       # analog couplet
                 _col(ss == 19),                       # occult partner
                 _col((dd == 5) | (dd == 15)),         # the year-bearer step
                 _col((dd == 4) | (dd == 16)),         # quarter-neighbour
                 _col((dd == 1) | (dd == 19))]         # adjacent days
        out = [_oh(dd, 20)] + flags
        if full:
            theta = 18.0 * _cdist(si, sj, 20)          # the 20-round drawn as a 360-degree circle
            out += [_oh(ss, 20)]
            for w in (12.0, 25.0):
                out += [_col(E.orbkern(theta, 0.0, w)),
                        _col(E.orbkern(theta, 72.0, w)),
                        _col(E.orbkern(theta, 180.0, w))]
        return out

    c = _rel(iO, iY, True) + _rel(iO, iW, False) + _rel(iY, iW, False)
    B["meso: day-sign pair relations (allied/antipodal/analog/occult)"] = np.concatenate(c, axis=1)

    # 11 ── the raw 20x20 pair of birth day-signs (pure interaction; trees and kernels only) ─────
    B["meso: day-sign pair one-hot 20x20"] = _oh(20 * C["sign"][iO] + C["sign"][iY], 400)

    # 12 ── Aztec: the 13 Lords of the Day and the 9 Lords of the Night, as pairs ────────────────
    c = [_oh(13 * (C["az_day_lord"][iO] - 1) + (C["az_day_lord"][iY] - 1), 169),
         _oh(9 * (C["az_night"][iO] - 1) + (C["az_night"][iY] - 1), 81),
         _col(C["az_day_lord"][iO] == C["az_day_lord"][iY]),
         _col(C["az_night"][iO] == C["az_night"][iY]),
         _oh(C["az_night"][iW] - 1, 9),
         _oh(C["az_day_lord"][iW] - 1, 13)]
    B["meso: aztec lord pairs (13 day-lords x 9 night-lords)"] = np.concatenate(c, axis=1)

    # 13 ── Dreamspell / Wavespell — MODERN (Arguelles), not the classical count ──────────────────
    c = []
    for s in MAIN:
        c += [_cyc(C["ds_kin"][s], 260, 3), _cyc(C["ds_tone"][s] - 1, 13, 2),
              _cyc(C["ds_seal"][s] - 1, 20, 2), _oh(C["ds_color"][s], 4),
              _oh(C["ds_castle"][s] - 1, 5)]
    si, sj = C["ds_seal"][iO] - 1, C["ds_seal"][iY] - 1
    dd, ss = np.mod(si - sj, 20), np.mod(si + sj, 20)
    c += [_col(ss == 17), _col(ss == 19), _col(dd == 10), _col(np.mod(dd, 4) == 0),
          _col(C["ds_guide"][iO] == C["ds_seal"][iY]), _col(C["ds_guide"][iY] == C["ds_seal"][iO]),
          _col(dd == 0), _col(C["ds_tone"][iO] == C["ds_tone"][iY]),
          _cyc(C["ds_kin"][iO] - C["ds_kin"][iY], 260, 3),
          _oh(C["ds_tone"][iO] - C["ds_tone"][iY], 13), _oh(dd, 20)]
    for s in (iO, iY):
        k, m = C["ds_seal"][iW] - 1, C["ds_seal"][s] - 1
        c += [_col(np.mod(k + m, 20) == 17), _col(np.mod(k + m, 20) == 19),
              _col(np.mod(k - m, 20) == 10), _col(np.mod(k - m, 4) == 0)]
    B["meso: dreamspell oracle (Arguelles, modern)"] = np.concatenate(c, axis=1)

    # 14 ── the documented tests, computed exactly, plus one openly-assembled tally ──────────────
    sO, sY, sW = C["sign"][iO], C["sign"][iY], C["sign"][iW]
    dd, ss = np.mod(sO - sY, 20), np.mod(sO + sY, 20)
    same_nawal = (dd == 0).astype(np.float64)
    same_quarter = (np.mod(dd, 4) == 0).astype(np.float64)
    opp_quarter = (np.mod(C["dir"][iO] - C["dir"][iY], 4) == 2).astype(np.float64)
    antipodal = (dd == 10).astype(np.float64)
    analog = (ss == 17).astype(np.float64)
    same_num = (C["num"][iO] == C["num"][iY]).astype(np.float64)
    same_trec = (C["trecena"][iO] == C["trecena"][iY]).astype(np.float64)
    same_g = (C["g"][iO] == C["g"][iY]).astype(np.float64)
    same_q819 = (C["quad819"][iO] == C["quad819"][iY]).astype(np.float64)
    same_bearer = (C["bearer"][iO] == C["bearer"][iY]).astype(np.float64)
    wayeb_birth = ((C["wayeb"][iO] + C["wayeb"][iY]) > 0).astype(np.float64)
    wayeb_wed = C["wayeb"][iW].astype(np.float64)
    good_wed = np.isin(sW, SAHAGUN_MARRIAGE).astype(np.float64)   # Sahagun, Fl. Codex VI.23
    # the tally: weights are THIS MODULE's assembly of the individual documented tests above,
    # not a Mesoamerican points table (no source gives one). Components are emitted separately
    # so a model can reweight them freely.
    tally = (2.0 * same_nawal + 1.0 * same_quarter + 1.0 * same_num + 1.0 * same_trec
             + 1.0 * analog + 1.0 * same_g - 2.0 * antipodal - 1.0 * opp_quarter
             - 1.0 * wayeb_birth + 2.0 * good_wed - 2.0 * wayeb_wed)
    c = [_col(x) for x in (same_nawal, same_quarter, opp_quarter, antipodal, analog, same_num,
                           same_trec, same_g, same_q819, same_bearer, wayeb_birth, wayeb_wed,
                           good_wed, tally)]
    c += [_oh(np.searchsorted(np.array(sorted(SAHAGUN_MARRIAGE)), sW,
                              side="right") * np.isin(sW, SAHAGUN_MARRIAGE), 6)]
    c += [_col(C["num"][iW]), _col(C["num"][iO]), _col(C["num"][iY]),
          _col(_cdist(sO, sY, 20)), _col(_cdist(C["num"][iO], C["num"][iY], 13))]
    B["meso: documented rule tests + tally"] = np.concatenate(c, axis=1)

    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in B.items()}


# ── self-test ───────────────────────────────────────────────────────────────────────────────────
def _doctrine_checks():
    """Prove the correlation arithmetic against published Long Count / Tzolk'in facts."""
    C = calendars(np.array([2456283.0, 584283.0, float(CASO_JDN)]))
    # 21 Dec 2012 = 13.0.0.0.0, 4 Ajaw 3 K'ank'in, G9
    assert C["d"][0] == 1872000, C["d"][0]
    assert C["num"][0] == 4 and DAYSIGN[C["sign"][0]] == "Ajaw", (C["num"][0], C["sign"][0])
    assert HAABM[C["hmonth"][0]] == "K'ank'in" and C["hday"][0] == 3
    assert C["g"][0] == 9, C["g"][0]
    # 0.0.0.0.0 = 4 Ajaw 8 Kumk'u
    assert C["num"][1] == 4 and DAYSIGN[C["sign"][1]] == "Ajaw"
    assert HAABM[C["hmonth"][1]] == "Kumk'u" and C["hday"][1] == 8
    # Caso's Aztec anchor: 13 Aug 1521 Julian = 1 Coatl, and GMT gives 1 Chikchan (= Coatl)
    assert C["num"][2] == 1 and AZTEC[C["sign"][2]] == "Coatl", (C["num"][2], C["sign"][2])
    assert DAYSIGN[C["sign"][2]] == "Chikchan"
    # Dreamspell anchor is internally consistent: Kin 207 = seal 7 (Hand), tone 12, Blue
    assert C["ds_kin"][0] == 207 and C["ds_seal"][0] == 7 and C["ds_tone"][0] == 12
    assert C["ds_color"][0] == 2                                     # 0 red 1 white 2 blue 3 yellow
    # the GMT year bearers are the Classic set, one per world-quarter
    yb = calendars(584283.0 + np.arange(0, 365 * 8, 1.0))
    bset = sorted(set(yb["bearer"].tolist()))
    assert [DAYSIGN[i] for i in bset] == ["Ik'", "Manik'", "Eb'", "Kab'an"], bset
    assert sorted({i % 4 for i in bset}) == [0, 1, 2, 3]
    # every 819-day station carries Tzolk'in coefficient 1 (Thompson); 819 = 63x13 so the
    # coefficient is invariant, while 819 mod 20 = 19 makes the day-sign retreat one step per
    # station: 1 Ajaw, 1 Kawak, 1 Etz'nab', ...
    st = calendars(584283.0 + E819_STATION + 819.0 * np.arange(6))
    assert (st["num"] == 1).all(), st["num"]
    assert st["sign"][0] == 19 and (np.diff(st["sign"]) % 20 == 19).all(), st["sign"]
    # the four world-quarters reproduce the Fejervary-Mayer groups
    east = {AZTEC[i] for i in range(20) if i % 4 == 0}
    assert east == {"Cipactli", "Coatl", "Atl", "Acatl", "Ollin"}, east
    print("doctrine checks   OK  (GMT 584283: 13.0.0.0.0 = 4 Ajaw 3 K'ank'in G9; Caso 1521 = 1 Coatl;"
          " bearers Ik'/Manik'/Eb'/Kab'an; 819 stations coefficient 1)")


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick

    _doctrine_checks()
    E = load()
    C = calendars(E.JD)
    print(f"couples {E.n}   older birth day 1 = {C['num'][0,0]} {DAYSIGN[C['sign'][0,0]]} "
          f"{C['hday'][0,0]} {HAABM[C['hmonth'][0,0]]}, G{C['g'][0,0]}, "
          f"LC {C['baktun'][0,0]}.{C['katun'][0,0]}.{C['tun'][0,0]}."
          f"{C['winal'][0,0]}.{C['kin'][0,0]}, Dreamspell kin {C['ds_kin'][0,0]}")
    blocks = build(E)
    total = 0
    bad = 0
    print(f"\n{TRADITION}\n")
    for name, X in blocks.items():
        assert isinstance(X, np.ndarray), name
        assert X.dtype == np.float64, (name, X.dtype)
        assert X.ndim == 2 and X.shape[0] == E.n, (name, X.shape)
        assert np.isfinite(X).all(), name
        assert X.std(axis=0).max() > 0, f"{name} is all-constant"
        total += X.shape[1]
        a, u = quick(E, X)
        print(f"  {name:<58} {X.shape[1]:>4} cols   acc {100*a:5.2f}%   AUC {u:.4f}")
    print(f"\n{len(blocks)} blocks, {total} columns total")
    if bad:
        sys.exit(1)
