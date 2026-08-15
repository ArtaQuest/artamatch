"""
trad_vedic_core.py — Vedic / Jyotisha core, as feature blocks.

WHAT THIS IMPLEMENTS, AND FROM WHERE
------------------------------------
Everything here is sidereal. Because the ayanamsa is a live doctrinal parameter and not a settled
fact, the tradition's own compatibility arithmetic (Ashtakoota) is computed FOUR TIMES, under
Lahiri, Raman, Krishnamurti and True Citra, as four separately-named blocks, so the ayanamsa choice
is itself testable rather than assumed. Everything else uses Lahiri (the Indian civil standard).

Rules implemented, with the authority each comes from:

  * Ashtakoota / Guna Milan, 36 points — the eight kootas of the marriage-matching chapter of the
    Muhurta literature (Muhurta Chintamani; tabulated in B. V. Raman, *Muhurta*, ch. "Marriage"):
    Varna 1, Vashya 2, Tara/Dina 3, Yoni 4, Graha Maitri 5, Gana 6, Bhakoot/Rasi 7, Nadi 8.
    Computed exactly as specified, from the two Moons' sidereal nakshatra and rasi. Several kootas
    are asymmetric (bride vs groom) and we do not know sex, so BOTH orderings are emitted:
    older-as-groom and younger-as-groom.
  * Naisargika maitri (natural planetary friendship) — BPHS ch. 3; the five-fold panchadha maitri
    (naisargika + tatkalika) — BPHS ch. 3, combination table.
  * Vargas — BPHS ch. 6: D1 rasi, D2 hora, D3 drekkana, D7 saptamsa (the CHILDREN chart, given its
    own block), D9 navamsa (the MARRIAGE chart, given its own block), D12 dwadasamsa, D30 trimsamsa
    (Parashara's unequal 5/5/8/7/5 division, reversed in even signs), D60 shashtiamsa.
  * Panchanga — the five limbs: tithi ((Moon-Sun)/12), vara (weekday), nakshatra, yoga
    ((Sun+Moon)/13°20' sidereal), karana (60 half-tithis mapped onto the 11 named karanas with
    Kimstughna first and Shakuni/Chatushpada/Naga last).
  * Vimshottari dasha — the 120-year cycle (Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18,
    Jupiter 16, Saturn 19, Mercury 17), started from the Moon's nakshatra at birth, walked forward
    to the wedding for the mahadasha, antardasha and pratyantardasha lords in force.
  * Planetary states — combustion at the classical degree limits (Moon 12°, Mars 17°, Mercury 14°
    direct / 12° retrograde, Jupiter 11°, Venus 10° direct / 8° retrograde, Saturn 15°),
    retrogradation, exaltation/debilitation degrees (Sun 10 Ari, Moon 3 Tau, Mars 28 Cap,
    Mercury 15 Vir, Jupiter 5 Can, Venus 27 Pis, Saturn 20 Lib), Moolatrikona ranges, own signs.
  * Avastha — Baladi (bala/kumara/yuva/vriddha/mrita by 6° parts, reversed in even signs) and
    Jagradadi (jagrat/swapna/sushupti by dignity).
  * Jaimini chara karakas — Jaimini Upadesa Sutras: the eight planets Sun..Saturn plus Rahu ranked
    by degrees advanced in their sign (Rahu reversed, 30 - degree), giving AK, AmK, BK, MK, PiK, PK,
    GK and, last, DARAKARAKA — the spouse indicator, which is weighted here with its own sign,
    navamsa, nakshatra and cross-chart contact features.
  * Kuja (Mangal) dosha and papa-samya — Mars / the malefics in the 1st, 2nd, 4th, 7th, 8th, 12th.

THE HARD LIMIT: NO BIRTH TIME, THEREFORE NO LAGNA
-------------------------------------------------
Only birth DATES are known; every position is computed at 12:00 UT. In Jyotisha terms:

  * NO LAGNA (Ascendant), no bhava/house cusps, no navamsa lagna, no Upapada Lagna (A7), no
    Ashtakavarga including the lagna's contribution, no Gulika/Mandi, no birth hora lord, and no
    Jaimini chara dasha (which begins from the lagna's sign). None of that is computed here. Where a
    rule needs the lagna, this module uses an explicit, named PROXY and says so: Chandra-lagna (the
    Moon's sign as the 1st) and Surya-lagna (the Sun's sign as the 1st). Kuja dosha is therefore
    Chandra- and Surya-based, not lagna-based, and the "5th house" of the saptamsa is the 5th sign
    from the Moon. These are proxies, not the doctrine.
  * THE MOON IS UNCERTAIN BY ROUGHLY +-6°. A nakshatra is 13°20', a pada 3°20'. So the janma
    nakshatra — on which Ashtakoota, the Vimshottari start and the whole lunar apparatus rest — is
    right maybe half the time, and the pada much less often. The features are built anyway, because
    this tradition IS lunar, but no precision should be read into them.
  * THE VIMSHOTTARI BALANCE AT BIRTH is a fraction of the janma nakshatra, so it inherits that
    +-6° error: the mahadasha lord in force at the wedding can be off by one period near a boundary.
  * TITHI, YOGA AND KARANA at birth are noon values, not birth-moment values. VARA (weekday) is
    taken from the Julian day at noon UT; the Vedic day runs sunrise-to-sunrise, so for a birth in
    the local pre-dawn hours the traditional vara would be the previous one.
  * Sex is unknown, so every asymmetric bride/groom rule is emitted in both orderings using
    older/younger.

NOT COMPUTED HERE, and why
--------------------------
  * Lagna, bhavas, bhava madhya, the lagna lord, the 7th house and its lord, the Ascendant's
    nakshatra — all need a birth time and place.
  * Navamsa lagna, Upapada Lagna (A7) and every other arudha pada — derived from the lagna.
  * Jaimini chara dasha, and any dasha keyed to a house — starts from the lagna's sign.
  * Ashtakavarga (BAV/SAV bindus) — the lagna is one of the eight contributors, so the tally would
    be systematically short; and its main use is over houses.
  * Shadbala in full — Kala bala needs the time of day, Dig bala needs the houses. Only the pieces
    that are purely zodiacal (Uchcha/exaltation proximity, dignity, cheshta/retrogradation,
    naisargika) appear, inside the graha-states block.
  * Gulika/Mandi and the birth hora lord — computed from sunrise and the day's eighth parts.
  * Sunrise-relative vara, and the exact tithi/yoga/karana at birth — noon values are used instead.
  * The Tamil ten poruthams (Rajju, Vedha, Mahendra, Stree-Dirgha, Vihanga) — a South Indian
    system, not this module's family, and left to a sibling module rather than duplicated here.

Yoni koota honesty note: the same-yoni (4) and mortal-enemy (0) cells are exact — the seven
mortal-enemy pairs (cow/tiger, elephant/lion, horse/buffalo, dog/deer, monkey/sheep, cat/rat,
serpent/mongoose) are the classical list. The middle band of the 14x14 Muhurta table is
APPROXIMATED here as 3 for two tame or two wild yonis and 2 for a mixed pair; the exact per-cell
values vary between printed editions. The exactly-known parts (same-yoni flag, mortal-enemy flag,
yoni sex match) are emitted as their own columns so a model need not trust the approximation.
"""

import numpy as np

TRADITION = "Vedic / Jyotisha core (Parashara BPHS, Muhurta Ashtakoota, Jaimini chara karakas)"

YR = 365.2425

# ── the nine grahas ─────────────────────────────────────────────────────────────────────────────
GN = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"]
SU, MO, ME, VE, MA, JU, SA, RA, KE = range(9)
SEVEN = [SU, MO, ME, VE, MA, JU, SA]

# ── zodiac primitives ───────────────────────────────────────────────────────────────────────────
NAK = 360.0 / 27.0          # 13 deg 20'
PAD = 360.0 / 108.0         # 3 deg 20'


def sign_of(lon):
    return np.clip((np.mod(lon, 360.0) / 30.0).astype(int), 0, 11)


def deg_in_sign(lon):
    return np.mod(np.mod(lon, 360.0), 30.0)


def nak_of(lon):
    return np.clip((np.mod(lon, 360.0) / NAK).astype(int), 0, 26)


def pada108_of(lon):
    return np.clip((np.mod(lon, 360.0) / PAD).astype(int), 0, 107)


def frac_in_nak(lon):
    return np.mod(np.mod(lon, 360.0), NAK) / NAK


def frac_in_pada(lon):
    return np.mod(np.mod(lon, 360.0), PAD) / PAD


# ── array plumbing ──────────────────────────────────────────────────────────────────────────────
# The couple count, set once by build(). Every helper returns (n, k); anything that arrives as (..., n) — the
# natural shape of the ephemeris tables — is transposed into it.
#
# THE OLD COMMENT HERE SAID: "n is 2296 and no feature count comes anywhere near that, so the two orientations
# are never ambiguous." That is an assumption about the BATCH SIZE, and it is false for any batch whose size
# equals a block's width. `oh(idx, 27)` over fifteen stacked grahas returns (n, 405), so a batch of exactly 405
# couples produced a SQUARE array, T() could not tell which axis was which, and it silently transposed a
# one-hot — corrupting the whole block while every shape check still passed. It was found because the same
# couple scored 0.4550 in one batch and 0.4537 in another.
#
# Orientation is no longer guessed. Helpers that already produce (n, k) say so by returning an _NK view, and T()
# hands those back untouched. Anything still ambiguous RAISES rather than picking, because a wrong guess here is
# not an error message, it is a quietly different model.
_N = [0]


class _NK(np.ndarray):
    """A marker view meaning "this array is already (n, k)". Carries no data of its own."""


def _nk(a):
    return np.ascontiguousarray(np.asarray(a, dtype=np.float64)).view(_NK)


def T(a):
    """Anything shaped (n,), (k, n), (..., n) or already (n, k) -> (n, k) float64."""
    if isinstance(a, _NK):
        return np.ascontiguousarray(np.asarray(a, dtype=np.float64))
    a = np.asarray(a, dtype=np.float64)
    n = _N[0]
    if a.ndim == 1:
        if a.shape[0] == n:
            return a[:, None]
        return a[None, :]
    if a.ndim == 2 and a.shape[0] == n and a.shape[1] != n:
        return np.ascontiguousarray(a)
    if a.ndim == 2 and a.shape[0] == n and a.shape[1] == n:
        raise ValueError(
            f"cannot orient a square {a.shape} array with a batch of {n} couples: the row axis and the feature "
            f"axis are indistinguishable. Mark the producer's output with _nk() if it is already (n, k). "
            f"Guessing here silently transposes a block.")
    return np.ascontiguousarray(a.reshape(-1, a.shape[-1]).T)


def cat(*parts):
    return np.ascontiguousarray(np.concatenate([T(p) for p in parts], axis=1), dtype=np.float64)


def oh(idx, levels):
    """One-hot. idx is (..., n) of ints -> (n, m*levels) with m = prod(leading dims).

    Returned as an _NK view: this is already (n, k), and a batch of n couples where n happens to equal
    m*levels would otherwise be a square array that T() has to guess at.
    """
    idx = np.asarray(idx, dtype=int)
    n = idx.shape[-1]
    flat = idx.reshape(-1, n)
    out = np.zeros((n, flat.shape[0] * levels))
    rows = np.arange(n)
    for i in range(flat.shape[0]):
        out[rows, i * levels + np.clip(flat[i], 0, levels - 1)] = 1.0
    return _nk(out)


def circ_idx(idx, levels):
    """cos/sin of a cyclic index -> (n, 2m)."""
    a = 2.0 * np.pi * np.asarray(idx, dtype=np.float64) / levels
    return cat(np.cos(a), np.sin(a))


# ── divisional charts (BPHS ch. 6) ──────────────────────────────────────────────────────────────
def d1(lon):
    return sign_of(lon)


def d2(lon):
    """Hora: 15° halves. Odd sign -> Leo then Cancer; even sign -> Cancer then Leo."""
    s, d = sign_of(lon), deg_in_sign(lon)
    odd = (s % 2 == 0)                      # Aries is the 1st (odd) sign
    second = d >= 15.0
    return np.where(odd, np.where(second, 3, 4), np.where(second, 4, 3))


def d3(lon):
    """Drekkana: 10° thirds -> the sign, the 5th from it, the 9th from it."""
    s = sign_of(lon)
    p = np.clip((deg_in_sign(lon) / 10.0).astype(int), 0, 2)
    return (s + 4 * p) % 12


def d3_part(lon):
    return np.clip((deg_in_sign(lon) / 10.0).astype(int), 0, 2)


def d7(lon):
    """Saptamsa: 30/7 parts. Odd sign counts from itself, even sign from the 7th."""
    s = sign_of(lon)
    p = np.clip((deg_in_sign(lon) / (30.0 / 7.0)).astype(int), 0, 6)
    odd = (s % 2 == 0)
    return np.where(odd, (s + p) % 12, (s + 6 + p) % 12)


def d7_part(lon):
    return np.clip((deg_in_sign(lon) / (30.0 / 7.0)).astype(int), 0, 6)


def d9(lon):
    """Navamsa: 3°20' ninths; movable signs start from themselves, fixed from the 9th, dual from
    the 5th — which is exactly (9*sign + part) mod 12."""
    s = sign_of(lon)
    p = np.clip((deg_in_sign(lon) / (10.0 / 3.0)).astype(int), 0, 8)
    return (9 * s + p) % 12


def d9_part(lon):
    return np.clip((deg_in_sign(lon) / (10.0 / 3.0)).astype(int), 0, 8)


def d12(lon):
    """Dwadasamsa: 2°30' twelfths counted from the sign itself."""
    s = sign_of(lon)
    p = np.clip((deg_in_sign(lon) / 2.5).astype(int), 0, 11)
    return (s + p) % 12


def d30(lon):
    """Trimsamsa, Parashara's unequal division.

    Odd sign : 0-5 Mars(Ari) · 5-10 Saturn(Aqu) · 10-18 Jupiter(Sag) · 18-25 Mercury(Gem) ·
               25-30 Venus(Lib)
    Even sign: 0-5 Venus(Tau) · 5-12 Mercury(Vir) · 12-20 Jupiter(Pis) · 20-25 Saturn(Cap) ·
               25-30 Mars(Sco)
    """
    s, d = sign_of(lon), deg_in_sign(lon)
    odd = (s % 2 == 0)
    o = np.select([d < 5, d < 10, d < 18, d < 25], [0, 10, 8, 2], default=6)
    e = np.select([d < 5, d < 12, d < 20, d < 25], [1, 5, 11, 9], default=7)
    return np.where(odd, o, e)


def d60(lon):
    """Shashtiamsa: half-degree parts counted from the sign itself."""
    s = sign_of(lon)
    p = np.clip((deg_in_sign(lon) * 2.0).astype(int), 0, 59)
    return (s + p) % 12


def d60_part(lon):
    return np.clip((deg_in_sign(lon) * 2.0).astype(int), 0, 59)


VARGAS = {"D1": d1, "D2": d2, "D3": d3, "D7": d7, "D9": d9, "D12": d12, "D30": d30, "D60": d60}

# ── sign lordship, dignity, friendship (BPHS ch. 3) ─────────────────────────────────────────────
# lord of each sign, as a graha index
SIGN_LORD = np.array([MA, VE, ME, MO, SU, ME, VE, MA, JU, SA, SA, JU])

# naisargika maitri: +1 friend, 0 neutral, -1 enemy; row = the judging planet
_NAIS = np.zeros((9, 9))
_friends = {
    SU: [MO, MA, JU], MO: [SU, ME], ME: [SU, VE], VE: [ME, SA],
    MA: [SU, MO, JU], JU: [SU, MO, MA], SA: [ME, VE],
    RA: [ME, VE, SA], KE: [ME, VE, SA],
}
_enemies = {
    SU: [VE, SA], MO: [], ME: [MO], VE: [SU, MO],
    MA: [ME], JU: [ME, VE], SA: [SU, MO, MA],
    RA: [SU, MO, MA], KE: [SU, MO, MA],
}
for _p in range(9):
    for _q in _friends[_p]:
        _NAIS[_p, _q] = 1.0
    for _q in _enemies[_p]:
        _NAIS[_p, _q] = -1.0
    _NAIS[_p, _p] = 1.0
# Rahu/Ketu are not in BPHS ch.3; the reciprocal cells are filled symmetrically (documented choice)
for _p in SEVEN:
    _NAIS[_p, RA] = _NAIS[RA, _p]
    _NAIS[_p, KE] = _NAIS[KE, _p]

# Graha Maitri koota (5 points) from the two Moon-sign lords' mutual relation
_MAITRI = np.zeros((9, 9))
for _a in range(9):
    for _b in range(9):
        if _a == _b:
            _MAITRI[_a, _b] = 5.0
            continue
        ra_, rb_ = _NAIS[_a, _b], _NAIS[_b, _a]
        lo, hi = min(ra_, rb_), max(ra_, rb_)
        if lo == 1 and hi == 1:
            v = 5.0
        elif lo == 0 and hi == 1:
            v = 4.0
        elif lo == 0 and hi == 0:
            v = 3.0
        elif lo == -1 and hi == 1:
            v = 1.0
        elif lo == -1 and hi == 0:
            v = 0.5
        else:
            v = 0.0
        _MAITRI[_a, _b] = v

# panchadha maitri: (naisargika, tatkalika) -> 5 adhimitra, 4 mitra, 3 sama, 2 shatru, 1 adhishatru
def _panchadha(nat, tmp):
    """nat in {-1,0,1}; tmp in {-1,1} (temporal friend / temporal enemy)."""
    f = tmp > 0
    return np.select(
        [(nat > 0) & f, (nat > 0) & ~f, (nat == 0) & f, (nat == 0) & ~f, (nat < 0) & f],
        [5.0, 3.0, 4.0, 2.0, 3.0], default=1.0)


# exaltation longitudes (absolute degrees) and their debilitation opposites
EXALT = np.array([10.0, 33.0, 165.0, 357.0, 298.0, 95.0, 200.0, 50.0, 230.0])
OWN = {SU: [4], MO: [3], ME: [2, 5], VE: [1, 6], MA: [0, 7], JU: [8, 11], SA: [9, 10],
       RA: [], KE: []}
# Moolatrikona: sign, from-degree, to-degree
MOOL = {SU: (4, 0.0, 20.0), MO: (1, 4.0, 30.0), ME: (5, 16.0, 20.0), VE: (6, 0.0, 15.0),
        MA: (0, 0.0, 12.0), JU: (8, 0.0, 10.0), SA: (10, 0.0, 20.0)}
# classical combustion limits in degrees from the Sun (direct, retrograde)
COMBUST = {MO: (12.0, 12.0), ME: (14.0, 12.0), VE: (10.0, 8.0), MA: (17.0, 17.0),
           JU: (11.0, 11.0), SA: (15.0, 15.0)}
MEANSPD = np.array([0.9856, 13.176, 1.383, 1.602, 0.524, 0.0831, 0.0335, 0.0529, 0.0529])

DIGNITY = 7   # exalted, moolatrikona, own, friend, neutral, enemy, debilitated


def dignity_code(g, lon):
    """0 exalted · 1 moolatrikona · 2 own · 3 friend's sign · 4 neutral · 5 enemy · 6 debilitated."""
    s, d = sign_of(lon), deg_in_sign(lon)
    ex = int(EXALT[g] // 30)
    deb = (ex + 6) % 12
    code = np.full(s.shape, 4, dtype=int)
    rel = _NAIS[g][SIGN_LORD[s]]
    code = np.where(rel > 0, 3, code)
    code = np.where(rel < 0, 5, code)
    if OWN[g]:
        code = np.where(np.isin(s, OWN[g]), 2, code)
    code = np.where(s == deb, 6, code)
    code = np.where(s == ex, 0, code)
    # Moolatrikona is claimed LAST, and so wins inside its degree range: the Moon in Taurus is
    # exalted over 0-4 deg and moolatrikona over 4-30, not exalted across the whole sign.
    if g in MOOL:
        ms, lo, hi = MOOL[g]
        code = np.where((s == ms) & (d >= lo) & (d < hi), 1, code)
    return code


def dignity_by_sign(g, sgn):
    """Dignity from the SIGN alone — for a varga, where the divisional degree is not the rasi degree.

    0 exalted · 2 own · 3 friend's sign · 4 neutral · 5 enemy · 6 debilitated (no moolatrikona,
    which is a degree range and therefore meaningless once a varga sign is all that is left).
    """
    ex = int(EXALT[g] // 30)
    deb = (ex + 6) % 12
    rel = _NAIS[g][SIGN_LORD[sgn]]
    code = np.full(np.asarray(sgn).shape, 4, dtype=int)
    code = np.where(rel > 0, 3, code)
    code = np.where(rel < 0, 5, code)
    if OWN[g]:
        code = np.where(np.isin(sgn, OWN[g]), 2, code)
    code = np.where(sgn == deb, 6, code)
    code = np.where(sgn == ex, 0, code)
    return code


def baladi(lon):
    """Baladi avastha: 6° fifths, direct in odd signs and reversed in even ones."""
    s = sign_of(lon)
    p = np.clip((deg_in_sign(lon) / 6.0).astype(int), 0, 4)
    return np.where(s % 2 == 0, p, 4 - p)


def jagradadi(code):
    """Jagrat (exalted/moolatrikona/own) · swapna (friend/neutral) · sushupti (enemy/debilitated)."""
    return np.select([code <= 2, code <= 4], [0, 1], default=2)


# ── Ashtakoota tables ───────────────────────────────────────────────────────────────────────────
# Varna by Moon sign: water = Brahmin 4, fire = Kshatriya 3, earth = Vaishya 2, air = Shudra 1
VARNA_RANK = np.array([3, 2, 1, 4, 3, 2, 1, 4, 3, 2, 1, 4])

# Vashya classes: 0 chatushpada · 1 manava · 2 jalachara · 3 vanachara(Leo) · 4 keeta(Scorpio)
_VASHYA_SIGN = np.array([0, 0, 1, 2, 3, 1, 1, 4, -1, -1, 1, 2])   # -1 = split at 15° (Sag, Cap)
VASHYA_T = np.array([
    [2.0, 1.0, 1.0, 0.5, 1.0],
    [1.0, 2.0, 0.5, 0.0, 1.0],
    [1.0, 1.0, 2.0, 1.0, 0.5],
    [0.5, 0.0, 1.0, 2.0, 1.0],
    [1.0, 1.0, 0.5, 1.0, 2.0],
])


def vashya_cls(lon):
    s, d = sign_of(lon), deg_in_sign(lon)
    c = _VASHYA_SIGN[s]
    c = np.where(s == 8, np.where(d < 15.0, 1, 0), c)     # Sagittarius: human, then quadruped
    c = np.where(s == 9, np.where(d < 15.0, 0, 2), c)     # Capricorn: quadruped, then watery
    return c


# Yoni: animal per nakshatra, and its sex
YONI_ANIMAL = np.array([0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11,
                        13, 0, 13, 7, 1])
# 0 male, 1 female. Magha is the MALE rat and Purva Phalguni the female one (the standard list;
# every animal holds one of each, the mongoose of Uttara Ashadha excepted).
YONI_SEX = np.array([0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0,
                     0, 1])
_ENEMY = [(7, 9), (1, 13), (0, 8), (4, 10), (11, 2), (5, 6), (3, 12)]
_TAME = {0, 1, 2, 4, 5, 7, 8}
YONI_T = np.zeros((14, 14))
YONI_ENEMY = np.zeros((14, 14))
for _a in range(14):
    for _b in range(14):
        if _a == _b:
            YONI_T[_a, _b] = 4.0
        elif (_a, _b) in _ENEMY or (_b, _a) in _ENEMY:
            YONI_T[_a, _b] = 0.0
            YONI_ENEMY[_a, _b] = 1.0
        elif (_a in _TAME) == (_b in _TAME):
            YONI_T[_a, _b] = 3.0
        else:
            YONI_T[_a, _b] = 2.0

# Gana per nakshatra: 0 deva · 1 manushya · 2 rakshasa
GANA_CLS = np.array([0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1,
                     1, 0])
GANA_T = np.array([          # row = groom's gana, column = bride's gana
    [6.0, 6.0, 0.0],
    [5.0, 6.0, 0.0],
    [1.0, 0.0, 6.0],
])

# Nadi per nakshatra: 0 adi(vata) · 1 madhya(pitta) · 2 antya(kapha)
NADI_CLS = np.array([0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0,
                     1, 2])
_BHAKOOT_BAD = np.array([2, 5, 6, 8, 9, 12])
_TARA_FAV = np.array([0, 2, 4, 6, 8])


def kootas(gm, bm):
    """The eight kootas with `gm` in the groom's role and `bm` in the bride's.

    Returns (list of eight score arrays, dict of the intermediate categories).
    """
    gs, bs = sign_of(gm), sign_of(bm)
    gn, bn = nak_of(gm), nak_of(bm)
    varna = (VARNA_RANK[gs] >= VARNA_RANK[bs]).astype(float)
    gc, bc = vashya_cls(gm), vashya_cls(bm)
    vashya = VASHYA_T[gc, bc]
    c_bg = ((gn - bn) % 27) + 1            # count from the bride's star to the groom's
    c_gb = ((bn - gn) % 27) + 1
    r_bg, r_gb = c_bg % 9, c_gb % 9
    tara = 1.5 * np.isin(r_bg, _TARA_FAV) + 1.5 * np.isin(r_gb, _TARA_FAV)
    ga, ba = YONI_ANIMAL[gn], YONI_ANIMAL[bn]
    yoni = YONI_T[ga, ba]
    maitri = _MAITRI[SIGN_LORD[gs], SIGN_LORD[bs]]
    gana = GANA_T[GANA_CLS[gn], GANA_CLS[bn]]
    dd = ((gs - bs) % 12) + 1
    bhakoot = np.where(np.isin(dd, _BHAKOOT_BAD), 0.0, 7.0)
    nadi = np.where(NADI_CLS[gn] == NADI_CLS[bn], 0.0, 8.0)
    parts = [varna, vashya, tara, yoni, maitri, gana, bhakoot, nadi]
    aux = dict(gs=gs, bs=bs, gn=gn, bn=bn, r_bg=r_bg, r_gb=r_gb, dd=dd,
               varna_pair=VARNA_RANK[gs] * 4 + VARNA_RANK[bs] - 5,
               vashya_pair=gc * 5 + bc, gana_pair=GANA_CLS[gn] * 3 + GANA_CLS[bn],
               nadi_pair=NADI_CLS[gn] * 3 + NADI_CLS[bn],
               same_yoni=(ga == ba).astype(float), enemy_yoni=YONI_ENEMY[ga, ba],
               sex_match=(YONI_SEX[gn] != YONI_SEX[bn]).astype(float),
               lord_g=SIGN_LORD[gs], lord_b=SIGN_LORD[bs])
    return parts, aux


# ── Vimshottari dasha ───────────────────────────────────────────────────────────────────────────
VIM_ORDER = np.array([KE, VE, SU, MO, MA, RA, JU, SA, ME])
VIM_YEARS = np.array([7.0, 20.0, 6.0, 10.0, 7.0, 18.0, 16.0, 19.0, 17.0])


def vimshottari(moon_lon, years_elapsed):
    """Mahadasha, antardasha and pratyantardasha in force after `years_elapsed`.

    The cycle starts at the lord of the janma nakshatra with the unelapsed fraction of that
    nakshatra as the balance — the classical construction, but read off a NOON Moon, so the
    balance carries the +-6° lunar error described in the module docstring.
    """
    n = moon_lon.shape[0]
    md = np.zeros(n, dtype=int); ad = np.zeros(n, dtype=int); pd = np.zeros(n, dtype=int)
    mdf = np.zeros(n); adf = np.zeros(n); pdf = np.zeros(n); bal = np.zeros(n)
    nk = nak_of(moon_lon)
    fr = frac_in_nak(moon_lon)
    for k in range(n):
        i = int(nk[k]) % 9
        bal[k] = (1.0 - fr[k]) * VIM_YEARS[i]
        t = fr[k] * VIM_YEARS[i] + years_elapsed[k]
        guard = 0
        while t >= VIM_YEARS[i] and guard < 400:
            t -= VIM_YEARS[i]
            i = (i + 1) % 9
            guard += 1
        md[k] = i
        mdf[k] = t / VIM_YEARS[i]
        j, u, guard = i, t, 0
        dur = VIM_YEARS[i] * VIM_YEARS[j] / 120.0
        while u >= dur and guard < 20:
            u -= dur
            j = (j + 1) % 9
            dur = VIM_YEARS[i] * VIM_YEARS[j] / 120.0
            guard += 1
        ad[k] = j
        adf[k] = u / dur if dur > 0 else 0.0
        m, v, guard = j, u, 0
        d2_ = dur * VIM_YEARS[m] / 120.0
        while v >= d2_ and guard < 20:
            v -= d2_
            m = (m + 1) % 9
            d2_ = dur * VIM_YEARS[m] / 120.0
            guard += 1
        pd[k] = m
        pdf[k] = v / d2_ if d2_ > 0 else 0.0
    return dict(md=VIM_ORDER[md], ad=VIM_ORDER[ad], pd=VIM_ORDER[pd], md_i=md, ad_i=ad,
                mdf=mdf, adf=adf, pdf=pdf, bal=bal, nak_lord=VIM_ORDER[nk % 9])


# ── graha tables per instant ────────────────────────────────────────────────────────────────────
def graha_lon(sid, E):
    """(6, 18, n) sidereal table -> (6, 9, n) for the nine grahas, Ketu opposite Rahu."""
    out = np.empty((sid.shape[0], 9, sid.shape[2]))
    for i, nm in enumerate(GN[:7]):
        out[:, i] = sid[:, E.IDX[nm]]
    out[:, RA] = sid[:, E.IDX["TrueNode"]]
    out[:, KE] = np.mod(sid[:, E.IDX["TrueNode"]] + 180.0, 360.0)
    return out


def graha_spd(E):
    out = np.empty((E.SPD.shape[0], 9, E.SPD.shape[2]))
    for i, nm in enumerate(GN[:7]):
        out[:, i] = E.SPD[:, E.IDX[nm]]
    out[:, RA] = E.SPD[:, E.IDX["TrueNode"]]
    out[:, KE] = E.SPD[:, E.IDX["TrueNode"]]
    return out


# ── panchanga ───────────────────────────────────────────────────────────────────────────────────
def panchanga(sun_sid, moon_sid, jd):
    elong = np.mod(moon_sid - sun_sid, 360.0)
    tithi = np.clip((elong / 12.0).astype(int), 0, 29)
    vara = (np.floor(jd + 1.5).astype(int)) % 7            # 0 = Sunday
    nak = nak_of(moon_sid)
    yoga = np.clip((np.mod(sun_sid + moon_sid, 360.0) / NAK).astype(int), 0, 26)
    h = np.clip((elong / 6.0).astype(int), 0, 59)
    karana = np.where(h == 0, 0, np.where(h <= 56, ((h - 1) % 7) + 1, h - 49))
    #   h = 0 Kimstughna · 1..56 the sevenfold cycle Bava..Vishti · 57 Shakuni · 58 Chatushpada ·
    #   59 Naga  (h-49 gives 8, 9, 10)
    return dict(tithi=tithi, vara=vara, nak=nak, yoga=yoga, karana=karana, elong=elong,
                paksha=(tithi >= 15).astype(float))


# ── Jaimini chara karakas ───────────────────────────────────────────────────────────────────────
KARAKA = ["AK", "AmK", "BK", "MK", "PiK", "PK", "GK", "DK"]
K8 = [SU, MO, MA, ME, JU, VE, SA, RA]      # the eight that take karaka roles (Ketu excluded)


def chara_karakas(g):
    """g is (9, n) sidereal longitudes -> (8, n) planet index per karaka role, AK..DK.

    Jaimini Upadesa Sutras: rank the eight by degrees advanced in their sign, highest first;
    Rahu is reckoned in reverse (30 - degree). Ties break by graha order, deterministically.
    """
    val = np.stack([deg_in_sign(g[p]) for p in K8], axis=0)
    val[K8.index(RA)] = 30.0 - val[K8.index(RA)]
    order = np.argsort(-val, axis=0, kind="stable")        # (8, n) positions into K8
    planets = np.asarray(K8)[order]                        # (8, n) graha indices, AK..DK
    return planets, order


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  BLOCKS
# ════════════════════════════════════════════════════════════════════════════════════════════════
AYANAMSAS_TESTED = ["Lahiri", "Raman", "Krishnamurti", "True Citra"]
MAIN = "Lahiri"


def _ashtakoota(E, aya):
    """The tradition's own 36-point total, both bride/groom orderings, under one ayanamsa."""
    sid = E.sidereal(aya)
    g = graha_lon(sid, E)
    mo, my = g[0, MO], g[1, MO]                 # older's and younger's Moon
    A, auxA = kootas(mo, my)                    # older as groom
    B, auxB = kootas(my, mo)                    # younger as groom
    totA, totB = sum(A), sum(B)
    # Kuja/Mangal dosha — PROXY: from Chandra-lagna and Surya-lagna, since there is no lagna
    kuja = []
    for slot in (0, 1):
        ms = sign_of(g[slot, MA])
        for ref in (MO, SU):
            h = ((ms - sign_of(g[slot, ref])) % 12) + 1
            kuja.append(np.isin(h, [1, 2, 4, 7, 8, 12]).astype(float))
    kj_o, kj_y = kuja[0], kuja[2]               # Chandra-lagna Kuja dosha, older and younger
    # the classical cancellation: a dosha on BOTH sides is held to cancel
    kboth = np.maximum(kj_o, kj_y) - kj_o * kj_y      # exactly one side afflicted
    # papa-samya: malefic burden in the 1,2,4,7,8,12 from the Moon (proxy for the lagna)
    papa_w = {SU: 1.0, MA: 2.0, SA: 1.5, RA: 1.5, KE: 1.0}
    papa = []
    for slot in (0, 1):
        tot = np.zeros(E.n)
        cnt = np.zeros(E.n)
        base = sign_of(g[slot, MO])
        for p, w in papa_w.items():
            h = ((sign_of(g[slot, p]) - base) % 12) + 1
            hit = np.isin(h, [1, 2, 4, 7, 8, 12]).astype(float)
            tot += w * hit
            cnt += hit
        papa.append(tot); papa.append(cnt)
    X = cat(
        *A, totA, totA / 36.0, (totA >= 18).astype(float), (totA >= 21).astype(float),
        (totA >= 25).astype(float),
        *B, totB, totB / 36.0, (totB >= 18).astype(float), (totB >= 21).astype(float),
        (totB >= 25).astype(float),
        0.5 * (totA + totB), np.abs(totA - totB),
        oh(auxA["r_bg"], 9), oh(auxA["r_gb"], 9),
        oh(auxA["dd"] - 1, 12), oh(auxA["nadi_pair"], 9),
        oh(auxA["gana_pair"], 9), oh(auxB["gana_pair"], 9),
        oh(auxA["varna_pair"], 16), oh(auxA["vashya_pair"], 25), oh(auxB["vashya_pair"], 25),
        auxA["same_yoni"], auxA["enemy_yoni"], auxA["sex_match"],
        oh(auxA["lord_g"], 9), oh(auxA["lord_b"], 9),
        oh(auxA["gs"], 12), oh(auxA["bs"], 12),
        circ_idx(auxA["gn"], 27), circ_idx(auxA["bn"], 27),
        circ_idx(((auxA["gn"] - auxA["bn"]) % 27), 27),
        kj_o, kj_y, kuja[1], kuja[3], kj_o * kj_y, np.abs(kj_o - kj_y), kboth,
        papa[0], papa[1], papa[2], papa[3], np.abs(papa[0] - papa[2]),
        (np.abs(papa[0] - papa[2]) < 0.5).astype(float),
    )
    return X


def _nakshatra_circular(E):
    """Nakshatra (27) and pada (108) for every graha, at both births and the wedding, smoothly."""
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    cols = []
    for slot in (0, 1, 2):
        for p in range(9):
            L = g[slot, p]
            cols.append(circ_idx(nak_of(L), 27))
            cols.append(circ_idx(pada108_of(L), 108))
            cols.append(T(frac_in_nak(L)))
            cols.append(T(frac_in_pada(L)))
    for p in range(9):
        n0, n1 = nak_of(g[0, p]), nak_of(g[1, p])
        cols.append(circ_idx((n0 - n1) % 27, 27))
        cols.append(T((((n0 - n1) % 27) + 1) % 9))
        cols.append(T((n0 == n1).astype(float)))
        cols.append(T((pada108_of(g[0, p]) == pada108_of(g[1, p])).astype(float)))
    return cat(*cols)


def _nakshatra_onehot(E):
    """Discrete nakshatra 27 for five grahas at three instants, plus the Moon's 108 padas."""
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    idx = np.stack([nak_of(g[s, p]) for s in (0, 1, 2) for p in (SU, MO, VE, MA, JU)], axis=0)
    pad = np.stack([pada108_of(g[s, MO]) for s in (0, 1, 2)], axis=0)
    return cat(oh(idx, 27), oh(pad, 108))


def _navamsa(E):
    """D9 — the MARRIAGE varga. Parashara reads the navamsa for the spouse and the marriage."""
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    n9 = np.stack([[d9(g[s, p]) for p in range(9)] for s in (0, 1, 2)])        # (3, 9, n)
    cols = [oh(n9[0], 12), oh(n9[1], 12), oh(n9[2], 12)]
    for s in (0, 1):
        cols.append(circ_idx(n9[s], 12))
        cols.append(oh(d9_part(g[s, MO]), 9))
        cols.append(T([(d1(g[s, p]) == n9[s, p]).astype(float) for p in range(9)]))   # vargottama
        # the 7th sign from the navamsa Moon — a PROXY for the 7th bhava (there is no lagna)
        seventh = (n9[s, MO] + 6) % 12
        cols.append(oh(seventh, 12))
        cols.append(oh(SIGN_LORD[seventh], 9))
        for p in (MO, VE, JU, MA):
            cols.append(oh(SIGN_LORD[n9[s, p]], 9))
            cols.append(oh(dignity_by_sign(p, n9[s, p]), DIGNITY))   # Venus = kalatrakaraka
        occ = np.zeros(E.n); mal = np.zeros(E.n)
        for p in range(9):
            hit = (n9[s, p] == seventh).astype(float)
            occ += hit
            if p in (SU, MA, SA, RA, KE):
                mal += hit
        cols.append(T(occ)); cols.append(T(mal))
    same = (n9[0] == n9[1]).astype(float)                                  # (9, n)
    cols.append(T(same))
    cols.append(T(same.sum(axis=0)))
    cross = np.zeros(E.n)
    for p in range(9):
        for q in range(9):
            cross += (n9[0, p] == n9[1, q])
    cols.append(T(cross))
    # 2/12, 5/9, 6/8 between the two navamsa Moons — bhakoot read in the navamsa
    dd = ((n9[0, MO] - n9[1, MO]) % 12) + 1
    cols.append(oh(dd - 1, 12))
    cols.append(T(np.isin(dd, _BHAKOOT_BAD).astype(float)))
    return cat(*cols)


def _saptamsa(E):
    """D7 — the CHILDREN varga. Parashara: the saptamsa is read for progeny (BPHS ch. 6, ch. 25)."""
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    n7 = np.stack([[d7(g[s, p]) for p in range(9)] for s in (0, 1, 2)])
    cols = [oh(n7[0], 12), oh(n7[1], 12), oh(n7[2], 12)]
    for s in (0, 1):
        cols.append(circ_idx(n7[s], 12))
        cols.append(oh(np.stack([d7_part(g[s, p]) for p in range(9)]), 7))
        # Jupiter, the natural karaka of progeny, in the saptamsa
        cols.append(oh(SIGN_LORD[n7[s, JU]], 9))
        cols.append(oh(dignity_by_sign(JU, n7[s, JU]), DIGNITY))
        cols.append(oh(dignity_by_sign(MO, n7[s, MO]), DIGNITY))
        cols.append(oh(dignity_by_sign(VE, n7[s, VE]), DIGNITY))
        # the 5th sign from the Moon in D7 — a PROXY for the 5th bhava (no lagna is available)
        fifth = (n7[s, MO] + 4) % 12
        cols.append(oh(fifth, 12))
        cols.append(oh(SIGN_LORD[fifth], 9))
        occ = np.zeros(E.n)
        mal = np.zeros(E.n)
        for p in range(9):
            hit = (n7[s, p] == fifth).astype(float)
            occ += hit
            if p in (SU, MA, SA, RA, KE):
                mal += hit
        cols.append(T(occ)); cols.append(T(mal))
    same = (n7[0] == n7[1]).astype(float)
    cols.append(T(same)); cols.append(T(same.sum(axis=0)))
    dd = ((n7[0, MO] - n7[1, MO]) % 12) + 1
    cols.append(oh(dd - 1, 12))
    # the wedding's own saptamsa fifth
    fw = (n7[2, MO] + 4) % 12
    cols.append(oh(fw, 12)); cols.append(oh(SIGN_LORD[fw], 9))
    return cat(*cols)


def _vargas(E):
    """D1 · D2 · D3 · D12 · D30 · D60, the rest of the shadvarga/shodasavarga set."""
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    L5 = np.zeros(9, dtype=int)                        # trimsamsa lords -> 0..4
    for i, p in enumerate([MA, SA, JU, ME, VE]):
        L5[p] = i
    cols = []
    tab = {}
    for nm in ("D1", "D2", "D3", "D12", "D30", "D60"):
        f = VARGAS[nm]
        tab[nm] = np.stack([[f(g[s, p]) for p in range(9)] for s in (0, 1, 2)])
        for s in (0, 1, 2):
            cols.append(circ_idx(tab[nm][s], 12))
    for s in (0, 1):
        cols.append(oh(L5[SIGN_LORD[tab["D30"][s]]], 5))
        cols.append(T((tab["D2"][s] == 4).astype(float)))          # Sun's hora
        cols.append(oh(np.stack([d3_part(g[s, p]) for p in range(9)]), 3))
        cols.append(circ_idx(np.stack([d60_part(g[s, p]) for p in range(9)]), 60))
    cols.append(T((tab["D2"][2] == 4).astype(float)))
    agree = []
    for nm in ("D1", "D2", "D3", "D12", "D30", "D60"):
        agree.append((tab[nm][0] == tab[nm][1]).astype(float))
    cols.append(T(np.stack(agree)))                                 # 6 x 9 diagonal agreements
    cols.append(T(np.stack(agree).sum(axis=(0, 1))))
    # a vimsopaka-flavoured tally: how many of the six vargas put a graha in its own or exalted sign
    for s in (0, 1):
        tot = np.zeros(E.n)
        for nm in ("D1", "D2", "D3", "D12", "D30", "D60"):
            for p in range(9):
                sgn = tab[nm][s, p]
                ex = int(EXALT[p] // 30)
                tot += (sgn == ex).astype(float)
                if OWN[p]:
                    tot += np.isin(sgn, OWN[p]).astype(float)
        cols.append(T(tot))
    return cat(*cols)


def _panchanga_block(E):
    """The five limbs at both births and at the wedding (the muhurta)."""
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    P = [panchanga(g[s, SU], g[s, MO], E.JD[s]) for s in (0, 1, 2)]
    cols = []
    for p in P:
        cols.append(oh(p["tithi"], 30)); cols.append(oh(p["vara"], 7))
        cols.append(oh(p["nak"], 27)); cols.append(oh(p["yoga"], 27))
        cols.append(oh(p["karana"], 11))
        cols.append(circ_idx(p["tithi"], 30)); cols.append(circ_idx(p["vara"], 7))
        cols.append(circ_idx(p["yoga"], 27)); cols.append(circ_idx(p["nak"], 27))
        cols.append(T(p["paksha"])); cols.append(T(p["elong"] / 360.0))
    for a, b in ((0, 1), (0, 2), (1, 2)):
        cols.append(T((P[a]["vara"] == P[b]["vara"]).astype(float)))
        cols.append(T((P[a]["tithi"] == P[b]["tithi"]).astype(float)))
        cols.append(T((P[a]["yoga"] == P[b]["yoga"]).astype(float)))
        cols.append(circ_idx((P[a]["tithi"] - P[b]["tithi"]) % 30, 30))
        cols.append(circ_idx((P[a]["yoga"] - P[b]["yoga"]) % 27, 27))
        cols.append(oh((P[a]["vara"] - P[b]["vara"]) % 7, 7))
    return cat(*cols)


def _dasha(E):
    """Vimshottari mahadasha / antardasha / pratyantardasha in force at the wedding."""
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    el_o = (E.JD[2] - E.JD[0]) / YR
    el_y = (E.JD[2] - E.JD[1]) / YR
    A = vimshottari(g[0, MO], el_o)
    B = vimshottari(g[1, MO], el_y)
    nat = _NAIS[A["md"], B["md"]]
    nat2 = _NAIS[B["md"], A["md"]]
    cols = [
        oh(A["md"], 9), oh(B["md"], 9), oh(A["ad"], 9), oh(B["ad"], 9),
        oh(A["pd"], 9), oh(B["pd"], 9),
        oh(A["nak_lord"], 9), oh(B["nak_lord"], 9),
        oh(A["md_i"] * 9 + B["md_i"], 81),
        T(A["mdf"]), T(B["mdf"]), T(A["adf"]), T(B["adf"]), T(A["pdf"]), T(B["pdf"]),
        T(A["bal"] / 20.0), T(B["bal"] / 20.0),
        T((A["md"] == B["md"]).astype(float)), T((A["ad"] == B["ad"]).astype(float)),
        T((A["md"] == A["ad"]).astype(float)), T((B["md"] == B["ad"]).astype(float)),
        T(nat), T(nat2), T(_MAITRI[A["md"], B["md"]]),
        T(_NAIS[A["md"], B["ad"]]), T(_NAIS[B["md"], A["ad"]]),
        circ_idx(A["md_i"], 9), circ_idx(B["md_i"], 9),
    ]
    # where the running dasha lord actually sits, in the partner's chart's terms
    for (X, s) in ((A, 0), (B, 1)):
        lonl = np.take_along_axis(g[s], X["md"][None, :], axis=0)[0]
        cols.append(E.circ(lonl))
        cols.append(oh(sign_of(lonl), 12))
        cols.append(oh(nak_of(lonl), 27))
    return cat(*cols)


def _states(E):
    """Combustion, retrogradation, exaltation/debilitation, Moolatrikona, own sign, avastha."""
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    spd = graha_spd(E)
    cols = []
    for s in (0, 1, 2):
        ncomb = np.zeros(E.n); nretro = np.zeros(E.n); nex = np.zeros(E.n)
        ndeb = np.zeros(E.n); nown = np.zeros(E.n); dsum = np.zeros(E.n)
        for p in range(9):
            L = g[s, p]
            code = dignity_code(p, L)
            cols.append(oh(code, DIGNITY))
            retro = (spd[s, p] < 0).astype(float)
            cols.append(T(retro))
            cols.append(T(np.clip(spd[s, p] / MEANSPD[p], -3.0, 3.0)))
            sep = E.sep(L, g[s, SU])
            if p in COMBUST:
                # combustion (asta) at the classical limits; a retrograde planet burns sooner
                lim = np.where(retro > 0, COMBUST[p][1], COMBUST[p][0])
                cb = (sep < lim).astype(float)
                cols.append(T(cb))
                cols.append(T(np.clip(1.0 - sep / lim, 0.0, 1.0)))
            else:
                cb = np.zeros(E.n)          # the Sun cannot be combust; the nodes are not bodies
            dex = E.sep(L, EXALT[p])
            cols.append(T(np.cos(np.deg2rad(dex))))
            cols.append(T(dex / 180.0))
            cols.append(oh(baladi(L), 5))
            cols.append(oh(jagradadi(code), 3))
            ncomb += cb; nretro += retro
            nex += (code == 0); ndeb += (code == 6); nown += (code == 2)
            dsum += np.select([code == 0, code == 1, code == 2, code == 3, code == 4, code == 5],
                              [3.0, 2.5, 2.0, 1.0, 0.0, -1.0], default=-2.0)
        cols += [T(ncomb), T(nretro), T(nex), T(ndeb), T(nown), T(dsum)]
    return cat(*cols)


def _maitri(E):
    """Panchadha maitri ACROSS the two charts: every older graha against every younger graha.

    BPHS ch. 3. The naisargika (permanent) relation of graha p to graha q is a constant of the
    doctrine — Sun is always Venus's enemy — so it carries no information about a particular
    couple and is NOT emitted on its own. What varies, and is emitted, is:

      * tatkalika (temporal) friendship, which is purely positional: q standing in the 2nd, 3rd,
        4th, 10th, 11th or 12th sign from p is its temporal friend, otherwise its temporal enemy;
      * the five-fold panchadha combination of the constant naisargika with that temporal relation;
      * DISPOSITOR friendship — the naisargika relation between the lords of the signs the two
        grahas actually occupy, and between each graha and the other's dispositor. This is how a
        Jyotishi actually judges two charts against each other, and it does vary per couple.
    """
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    so, sy = sign_of(g[0]), sign_of(g[1])                     # (9, n) occupied signs
    lo, ly = SIGN_LORD[so], SIGN_LORD[sy]                     # (9, n) dispositors
    tmp = np.empty((9, 9, E.n)); pan = np.empty((9, 9, E.n))
    disp = np.empty((9, 9, E.n)); pq = np.empty((9, 9, E.n))
    for p in range(9):
        for q in range(9):
            h = ((sy[q] - so[p]) % 12) + 1
            t = np.where(np.isin(h, [2, 3, 4, 10, 11, 12]), 1.0, -1.0)
            tmp[p, q] = t
            pan[p, q] = _panchadha(np.full(E.n, _NAIS[p, q]), t)
            disp[p, q] = _NAIS[lo[p], ly[q]]                  # lord-to-lord
            pq[p, q] = _NAIS[p, ly[q]]                        # graha to the other's dispositor
    flat = lambda M: M.reshape(81, E.n)
    diag = np.stack([pan[p, p] for p in range(9)])
    cols = [T(flat(tmp)), T(flat(pan)), T(flat(disp)), T(flat(pq)),
            T(diag), T(pan.mean(axis=(0, 1))), T((pan >= 5).sum(axis=(0, 1))),
            T((pan <= 1).sum(axis=(0, 1))), T(tmp.mean(axis=(0, 1))),
            T(disp.mean(axis=(0, 1))), T((disp > 0).sum(axis=(0, 1))),
            T((disp < 0).sum(axis=(0, 1)))]
    # the seven classical grahas only, restricted mean — the tradition's own scope
    cols.append(T(pan[np.ix_(SEVEN, SEVEN)].mean(axis=(0, 1))))
    cols.append(T(disp[np.ix_(SEVEN, SEVEN)].mean(axis=(0, 1))))
    return cat(*cols)


def _karakas(E):
    """Jaimini chara karakas, with the DARAKARAKA (the spouse) weighted."""
    sid = E.sidereal(MAIN)
    g = graha_lon(sid, E)
    PA, ordA = chara_karakas(g[0])
    PB, ordB = chara_karakas(g[1])
    cols = [oh(ordA, 8), oh(ordB, 8)]                       # 8 roles x 8 planets, both partners
    dkA, dkB = PA[7], PB[7]
    akA, akB = PA[0], PB[0]
    pkA, pkB = PA[5], PB[5]
    lonA = np.take_along_axis(g[0], dkA[None, :], axis=0)[0]
    lonB = np.take_along_axis(g[1], dkB[None, :], axis=0)[0]
    for (dk, lon) in ((dkA, lonA), (dkB, lonB)):
        cols.append(oh(dk, 9))
        cols.append(oh(sign_of(lon), 12))
        cols.append(oh(d9(lon), 12))
        cols.append(oh(d7(lon), 12))
        cols.append(oh(nak_of(lon), 27))
        cols.append(circ_idx(nak_of(lon), 27))
        cols.append(T(deg_in_sign(lon) / 30.0))
        cols.append(E.circ(lon))
    sep = E.sep(lonA, lonB)
    for ang in (0.0, 60.0, 90.0, 120.0, 180.0):
        for w in (3.0, 8.0, 15.0):
            cols.append(T(E.orbkern(sep, ang, w)))
    cols.append(T(sep / 180.0))
    cols.append(E.circ(E.wrap(lonA - lonB)))
    dd = ((sign_of(lonA) - sign_of(lonB)) % 12) + 1
    cols.append(oh(dd - 1, 12))
    cols.append(T(np.isin(dd, _BHAKOOT_BAD).astype(float)))
    cols.append(T((sign_of(lonA) == sign_of(lonB)).astype(float)))
    cols.append(T((d9(lonA) == d9(lonB)).astype(float)))
    # the Darakaraka against the partner's Venus, Moon and Jupiter — the marriage significators
    for p in (VE, MO, JU):
        for (lon, other) in ((lonA, g[1, p]), (lonB, g[0, p])):
            s2 = E.sep(lon, other)
            cols.append(T(E.orbkern(s2, 0.0, 8.0)))
            cols.append(T(E.orbkern(s2, 180.0, 8.0)))
            cols.append(T(E.orbkern(s2, 120.0, 8.0)))
            cols.append(T(s2 / 180.0))
    cols.append(T((akA == akB).astype(float)))
    cols.append(T((dkA == dkB).astype(float)))
    cols.append(T((akA == dkB).astype(float)))
    cols.append(T((dkA == akB).astype(float)))
    cols.append(oh(pkA, 9)); cols.append(oh(pkB, 9))
    for pk, slot in ((pkA, 0), (pkB, 1)):
        lp = np.take_along_axis(g[slot], pk[None, :], axis=0)[0]
        cols.append(oh(sign_of(lp), 12))
        cols.append(oh(d7(lp), 12))                          # Putrakaraka in the children's varga
        cols.append(T(deg_in_sign(lp) / 30.0))
    cols.append(T((pkA == pkB).astype(float)))
    return cat(*cols)


# ════════════════════════════════════════════════════════════════════════════════════════════════
def build(E):
    _N[0] = E.n
    out = {}
    for aya in AYANAMSAS_TESTED:
        out[f"ved: ashtakoota 36 + doshas [{aya}]"] = _ashtakoota(E, aya)
    out["ved: nakshatra 27 + pada 108 circular"] = _nakshatra_circular(E)
    out["ved: nakshatra/pada one-hot"] = _nakshatra_onehot(E)
    out["ved: D9 navamsa (marriage varga)"] = _navamsa(E)
    out["ved: D7 saptamsa (children varga)"] = _saptamsa(E)
    out["ved: vargas D1 D2 D3 D12 D30 D60"] = _vargas(E)
    out["ved: panchanga 5 limbs"] = _panchanga_block(E)
    out["ved: vimshottari dasha at wedding"] = _dasha(E)
    out["ved: graha states + avastha"] = _states(E)
    out["ved: panchadha maitri cross-chart"] = _maitri(E)
    out["ved: jaimini chara karakas (DK)"] = _karakas(E)
    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    import time
    from core import load
    from evalx import quick

    t0 = time.time()
    E = load()
    B = build(E)
    print(f"{TRADITION}\n{len(B)} blocks, built in {time.time()-t0:.1f}s\n")
    total = 0
    bad = 0
    for name, X in B.items():
        try:
            assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
            assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
            assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
            assert np.isfinite(X).all(), f"{name}: non-finite values"
            assert X.std(axis=0).max() > 0, f"{name}: all-constant"
        except AssertionError as e:
            print(f"FAIL {e}")
            bad += 1
            continue
        total += X.shape[1]
        a, u = quick(E, X)
        print(f"  {name:<44} {X.shape[1]:>5} cols   acc {100*a:5.2f}%   AUC {u:.4f}")
    print(f"\ntotal columns {total}")
    if bad:
        print(f"{bad} block(s) failed")
        sys.exit(1)
    print("OK")
