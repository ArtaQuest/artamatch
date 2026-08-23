"""vedic_varga — VARGA (divisional) charts, the Parasara backbone of Jyotisha.

A rasi (D1) position says where a graha stands in the visible zodiac.  Parasara's
shodasavarga says that each sign is subdivided again and again, and that the sign a
graha lands in *within a division* is what actually reports on the department of life
that division owns.  Nothing here is invented: every division below uses the classical
BPHS rule, and the departments are the classical ones —

    D1  rasi          the body, the visible life
    D2  hora          wealth / sustenance                (Sun's and Moon's horas only)
    D3  drekkana      siblings, courage
    D7  saptamsa      progeny
    D9  NAVAMSA       THE MARRIAGE CHART — the spouse, and the inner strength of every
                      graha.  In classical practice a marriage is read from D9 before
                      it is read from anything else, so it gets the deepest treatment.
    D10 dasamsa       career, action in the world
    D12 dwadasamsa    parents, inheritance
    D16 shodasamsa    vehicles, comforts, happiness in the home
    D20 vimsamsa      spiritual practice
    D24 siddhamsa     learning
    D27 bhamsa        strengths and weaknesses of the body
    D30 trimsamsa     EVILS / misfortune — the chart of what goes wrong.  Unequal
                      portions, ruled by Mars, Saturn, Jupiter, Mercury, Venus; the
                      Mars and Saturn portions are the malefic ones.
    D40 khavedamsa    matrilineal legacy
    D45 akshavedamsa  patrilineal legacy
    D60 shashtiamsa   the sum of past karma, the finest division Parasara gives

WHAT THIS MODULE EMITS.  15 divisions x 10-ish bodies x 2 partners is ~300 raw sign
columns, all of them order-dependent (the model would learn column order, not doctrine).
So the raw per-partner signs are computed but never emitted directly.  What is emitted is
the SYNASTRY those signs support, and every column is a symmetric function of the two
partners (a match count, an absolute sign distance, or a max/min pair) so swapping a and b
cannot change a single value.

BODIES.  The doctrinal set is the classical grahas: Sun, Moon, Mercury, Venus, Mars,
Jupiter, Saturn and Rahu (true_node) — eight.  Ketu (true_south_node) is by definition
exactly 180 deg from Rahu, so its sign in EVERY division is a fixed rotation of Rahu's and
its match/distance columns would be bit-identical to Rahu's; including it would only
double-weight the node axis, so it is dropped and said so here.  Uranus, Neptune and Pluto
have no rasi lordship, no exaltation and no varga rule in Parasara — they are given exactly
two clearly-labelled columns (`modern_*`) so they can be dropped in one grep, because at
their speeds they act as era clocks rather than as doctrine.

MISSING DATA.  Nothing is parsed for the charts themselves: Z already carries NaN wherever
a longitude is unknown, and NaN propagates through every division and every reduction here.
A fraction is over the bodies BOTH partners actually have (0/0 -> NaN, never 0).  A max/min
pair is strict: if either direction is unknown the pair is NaN rather than quietly reporting
the one direction that happened to be observable.  Only two columns are read from df at all
(the date-precision counts), and they are metadata about the row, not about a chart.

Pure function of (df, Z, half): no file reads, no network, no randomness, no global state.
"""

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- doctrine

# planet codes used for lordship / friendship / dignity
_SUN, _MOO, _MAR, _MER, _JUP, _VEN, _SAT = 0, 1, 2, 3, 4, 5, 6

# lord of each sign, Aries..Pisces (0..11) — Parasara's rasi lordships
_LORD_OF_SIGN = np.array([_MAR, _VEN, _MER, _MOO, _SUN, _MER,
                          _VEN, _MAR, _JUP, _SAT, _SAT, _JUP], dtype=np.int64)

# naisargika maitri (natural friendship), row = viewer, col = viewed.
# 0 = enemy, 1 = neutral, 2 = friend, 3 = the same graha (identical lord).
# The table is deliberately ASYMMETRIC where Parasara is asymmetric (Mercury calls the
# Sun a friend while the Sun calls Mercury neutral, etc.), which is why every friendship
# feature below is emitted as a (min, max) pair over the two directions — that is both
# faithful to the table and order-free.
_FRIEND = np.array([
    # sun moo mar mer jup ven sat
    [3,  2,  2,  1,  2,  0,  0],   # sun
    [2,  3,  1,  2,  1,  1,  1],   # moon
    [2,  2,  3,  0,  2,  1,  1],   # mars
    [2,  0,  1,  3,  1,  2,  1],   # mercury
    [2,  2,  2,  0,  3,  0,  1],   # jupiter
    [0,  0,  1,  2,  1,  3,  2],   # venus
    [0,  0,  0,  2,  1,  2,  3],   # saturn
], dtype=np.float64)

_OWN = {_SUN: (4,), _MOO: (3,), _MAR: (0, 7), _MER: (2, 5),
        _JUP: (8, 11), _VEN: (1, 6), _SAT: (9, 10)}
_EXALT = {_SUN: 0, _MOO: 1, _MAR: 9, _MER: 5, _JUP: 3, _VEN: 11, _SAT: 6}
_DEBIL = {k: (v + 6) % 12 for k, v in _EXALT.items()}

# the divisions computed, in classical order
_V = [1, 2, 3, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60]

_GRAHAS = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'true_node']
_CODE = {'sun': _SUN, 'moon': _MOO, 'mercury': _MER, 'venus': _VEN,
         'mars': _MAR, 'jupiter': _JUP, 'saturn': _SAT}          # rahu has no lordship
_MODERN = ['uranus', 'neptune', 'pluto']
_ALL_BODIES = _GRAHAS + _MODERN


# --------------------------------------------------------------------------- helpers

def _varga(L, n):
    """Sign (0..11 = Aries..Pisces) a longitude falls in, in the n-th division.

    L: sidereal ecliptic longitude in degrees, NaN allowed (and preserved).
    Every rule below is the standard Parasara one; the derivations that look like bare
    arithmetic are the closed forms of the stated rule and are noted as such.
    """
    L = np.asarray(L, dtype=np.float64)
    good = np.isfinite(L)
    Lm = np.where(good, np.mod(np.where(good, L, 0.0), 360.0), np.nan)
    s = np.floor(Lm / 30.0)          # rasi index, NaN-preserving
    d = Lm - 30.0 * s                # degrees travelled inside the sign, [0,30)

    odd = (np.mod(s, 2.0) == 0.0)    # Aries is the 1st = "odd" sign (0-indexed: s even)
    mov = (np.mod(s, 3.0) == 0.0)    # movable (chara):  Ar Cn Li Cp
    fix = (np.mod(s, 3.0) == 1.0)    # fixed  (sthira):  Ta Le Sc Aq   (else dual)

    if n == 1:
        r = s
    elif n == 2:                     # hora: 15 deg each. Odd sign -> Leo then Cancer;
        p = np.clip(np.floor(d / 15.0), 0, 1)          # even sign -> Cancer then Leo.
        first = np.where(odd, 4.0, 3.0)                # 4 = Leo (Sun), 3 = Cancer (Moon)
        r = np.where(p == 0.0, first, 7.0 - first)     # 7 - x swaps 3 <-> 4
    elif n == 3:                     # drekkana: 10 deg each -> same sign, 5th, 9th
        p = np.clip(np.floor(d / 10.0), 0, 2)
        r = s + 4.0 * p
    elif n == 7:                     # saptamsa: odd counts from the sign, even from the 7th
        p = np.clip(np.floor(d / (30.0 / 7.0)), 0, 6)
        r = np.where(odd, s, s + 6.0) + p
    elif n == 9:                     # navamsa: movable from the sign, fixed from the 9th,
        p = np.clip(np.floor(d / (30.0 / 9.0)), 0, 8)  # dual from the 5th — closed form:
        r = 9.0 * s + p                                # (9*s + p) mod 12
    elif n == 10:                    # dasamsa: odd from the sign, even from the 9th
        p = np.clip(np.floor(d / 3.0), 0, 9)
        r = np.where(odd, s, s + 8.0) + p
    elif n == 12:                    # dwadasamsa: always counted from the sign itself
        p = np.clip(np.floor(d / 2.5), 0, 11)
        r = s + p
    elif n == 16:                    # shodasamsa: movable Ar, fixed Le, dual Sg
        p = np.clip(np.floor(d / (30.0 / 16.0)), 0, 15)
        r = np.where(mov, 0.0, np.where(fix, 4.0, 8.0)) + p
    elif n == 20:                    # vimsamsa: movable Ar, fixed Sg, dual Le
        p = np.clip(np.floor(d / 1.5), 0, 19)
        r = np.where(mov, 0.0, np.where(fix, 8.0, 4.0)) + p
    elif n == 24:                    # siddhamsa: odd from Leo, even from Cancer
        p = np.clip(np.floor(d / 1.25), 0, 23)
        r = np.where(odd, 4.0, 3.0) + p
    elif n == 27:                    # bhamsa: fiery Ar, earthy Cn, airy Li, watery Cp —
        p = np.clip(np.floor(d / (30.0 / 27.0)), 0, 26)   # closed form (27*s + p) mod 12
        r = 27.0 * s + p
    elif n == 30:                    # trimsamsa: UNEQUAL portions, no part index at all.
        # odd sign: Mars 0-5 (Ar), Saturn 5-10 (Aq), Jupiter 10-18 (Sg),
        #           Mercury 18-25 (Ge), Venus 25-30 (Li)
        # even sign: the mirror — Venus 0-5 (Ta), Mercury 5-12 (Vi), Jupiter 12-20 (Pi),
        #           Saturn 20-25 (Cp), Mars 25-30 (Sc)
        r_odd = np.select([d < 5.0, d < 10.0, d < 18.0, d < 25.0],
                          [0.0, 10.0, 8.0, 2.0], default=6.0)
        r_even = np.select([d < 5.0, d < 12.0, d < 20.0, d < 25.0],
                           [1.0, 5.0, 11.0, 9.0], default=7.0)
        r = np.where(odd, r_odd, r_even)
    elif n == 40:                    # khavedamsa: odd from Aries, even from Libra
        p = np.clip(np.floor(d / 0.75), 0, 39)
        r = np.where(odd, 0.0, 6.0) + p
    elif n == 45:                    # akshavedamsa: movable Ar, fixed Le, dual Sg
        p = np.clip(np.floor(d / (30.0 / 45.0)), 0, 44)
        r = np.where(mov, 0.0, np.where(fix, 4.0, 8.0)) + p
    elif n == 60:                    # shashtiamsa: degrees x 2, remainder from the sign
        p = np.clip(np.floor(d * 2.0), 0, 59)
        r = s + p
    else:
        raise ValueError('unsupported division D%s' % n)

    r = np.mod(r, 12.0)
    # Final mask: some branches (D2, D30) select through np.where on a NaN-derived
    # condition, which would otherwise hand back a real sign for an unknown longitude.
    return np.where(good, r, np.nan)


def _sdist(sa, sb):
    """Circular distance between two signs, in signs: 0 (same) .. 6 (opposite).
    Order-free by construction: _sdist(a,b) == _sdist(b,a).  NaN preserved."""
    dd = np.mod(sa - sb, 12.0)
    return np.minimum(dd, 12.0 - dd)


def _lord(sign):
    """Lord of a sign array. NaN in -> NaN out; the int cast only ever sees finite values."""
    out = np.full(np.shape(sign), np.nan, dtype=np.float64)
    ok = np.isfinite(sign)
    if ok.any():
        out[ok] = _LORD_OF_SIGN[np.mod(sign[ok], 12.0).astype(np.int64)]
    return out


def _friend(la, lb):
    """Directional naisargika value of lord la towards lord lb (NaN-safe indexing)."""
    out = np.full(np.shape(la), np.nan, dtype=np.float64)
    ok = np.isfinite(la) & np.isfinite(lb)
    if ok.any():
        out[ok] = _FRIEND[la[ok].astype(np.int64), lb[ok].astype(np.int64)]
    return out


def _in_set(sign, wanted):
    out = np.zeros(np.shape(sign), dtype=bool)
    for w in wanted:
        out |= (sign == float(w))
    return out


def _matrix(Z, key):
    try:
        T = np.asarray(Z[key], dtype=np.float64)
    except Exception:
        return None
    return T if (T.ndim == 2) else None


def _body_col(T, j, n):
    out = np.full(n, np.nan, dtype=np.float64)
    if T is None or j is None:
        return out
    if j < 0 or j >= T.shape[1]:
        return out
    m = min(n, T.shape[0])
    if m:
        out[:m] = T[:m, j]
    out[~np.isfinite(out)] = np.nan
    return out


def _body_names(Z):
    try:
        raw = list(np.asarray(Z['bodies']).ravel())
    except Exception:
        return []
    names = []
    for b in raw:
        if isinstance(b, bytes):
            b = b.decode('utf-8', 'ignore')
        names.append(str(b).strip().lower())
    return names


def _date_flags(df, n):
    """Two row-metadata counts, honestly derived from the four date shapes.
    'YYYY-MM-DD' -> full; 'YYYY-00-00' -> year only; '0000-MM-DD' -> year unknown (no
    chart is possible at all); '0000-00-00' -> absent.  Nothing is imputed: these two
    columns only report HOW MANY of the two partners have a usable date, which is what
    explains the NaN density of everything else in this module."""
    yr = []
    dp = []
    for c in ('dob_a', 'dob_b'):
        if c in getattr(df, 'columns', []):
            s = df[c].astype(str).str.strip()
        else:
            s = pd.Series([''] * n)
        parts = s.str.split('-', n=2, expand=True)
        got = []
        for k in range(3):
            if parts.shape[1] > k:
                got.append(pd.to_numeric(parts[k], errors='coerce').to_numpy(dtype=np.float64))
            else:
                got.append(np.zeros(n, dtype=np.float64))
        y, m, d = [np.where(np.isfinite(g), g, 0.0) for g in got]
        y = y[:n] if y.shape[0] >= n else np.concatenate([y, np.zeros(n - y.shape[0])])
        m = m[:n] if m.shape[0] >= n else np.concatenate([m, np.zeros(n - m.shape[0])])
        d = d[:n] if d.shape[0] >= n else np.concatenate([d, np.zeros(n - d.shape[0])])
        yr.append((y > 0).astype(np.float64))
        dp.append(((y > 0) & (m > 0) & (d > 0)).astype(np.float64))
    return yr[0] + yr[1], dp[0] + dp[1]


# --------------------------------------------------------------------------- build

def build(df, Z, half):
    n = int(len(df))
    idx = {nm: i for i, nm in enumerate(_body_names(Z))}
    TA = _matrix(Z, 'theta_a_%s' % half)
    TB = _matrix(Z, 'theta_b_%s' % half)

    LA = {b: _body_col(TA, idx.get(b), n) for b in _ALL_BODIES}
    LB = {b: _body_col(TB, idx.get(b), n) for b in _ALL_BODIES}

    # every division, every body, both partners
    SA = {v: {b: _varga(LA[b], v) for b in _ALL_BODIES} for v in _V}
    SB = {v: {b: _varga(LB[b], v) for b in _ALL_BODIES} for v in _V}

    cols, names = [], []

    def add(name, arr):
        a = np.asarray(arr, dtype=np.float64).reshape(-1)
        if a.shape[0] != n:
            raise ValueError('feature %s has length %d, expected %d' % (name, a.shape[0], n))
        cols.append(np.where(np.isfinite(a), a, np.nan))
        names.append(name)

    def pair(name, sa1, sb2, sa2, sb1):
        """Order-free (min,max) of a cross-aspect measured both ways.  Strict: if either
        direction is unmeasurable the pair is NaN, rather than reporting the one that
        happened to be observable (which would mean something different row to row)."""
        d1 = _sdist(sa1, sb2)
        d2 = _sdist(sa2, sb1)
        add(name + '_min', np.minimum(d1, d2))
        add(name + '_max', np.maximum(d1, d2))

    # ---- A. concordance of the two charts, division by division -------------------
    # The plainest varga synastry there is: in how many divisions does a graha land in
    # the SAME sign for both partners.  Reported as a fraction of the grahas both
    # partners actually have, so a couple with day-precision on one side only is scored
    # on the bodies that are genuinely comparable instead of being penalised for NaN.
    fin = {b: (np.isfinite(LA[b]) & np.isfinite(LB[b])) for b in _GRAHAS}
    known = np.zeros(n)
    for b in _GRAHAS:
        known += fin[b].astype(np.float64)
    cnt = {}
    for v in _V:
        m = np.zeros(n)
        for b in _GRAHAS:
            m += (fin[b] & (SA[v][b] == SB[v][b])).astype(np.float64)
        cnt[v] = np.where(known > 0, m, np.nan)
        add('varga_match_frac_D%d' % v, np.where(known > 0, m / np.maximum(known, 1.0), np.nan))
    add('varga_match_n_D1', cnt[1])          # raw counts for the two charts that matter
    add('varga_match_n_D9', cnt[9])          # most, so the model can see the denominator
    add('varga_grahas_known', known)         # 0..8 — how much chart the couple actually has

    # classical groupings: shadvarga (6), dasavarga (10), and the whole set we compute
    def grp(name, vs):
        add(name, np.mean(np.vstack([np.where(known > 0,
                                              cnt[v] / np.maximum(known, 1.0), np.nan)
                                     for v in vs]), axis=0))
    grp('varga_match_frac_shadvarga', [1, 2, 3, 9, 12, 30])
    grp('varga_match_frac_dasavarga', [1, 2, 3, 7, 9, 10, 12, 16, 30, 60])
    grp('varga_match_frac_all15', _V)

    # ---- B. body-by-body distance in the marriage chart ---------------------------
    # |sign(a) - sign(b)| in D9, as a circular distance 0..6.  0 = the same navamsa
    # sign (the strongest classical "meeting"), 6 = the 7th-from (the marriage axis
    # itself), 4 = trine.  D1 is given for the four marriage significators only, so the
    # model can tell whether D9 is adding anything beyond the visible chart.
    for b in _GRAHAS:
        add('d9_dist_%s' % b, _sdist(SA[9][b], SB[9][b]))
    for b in ('moon', 'venus', 'mars', 'jupiter'):
        add('d1_dist_%s' % b, _sdist(SA[1][b], SB[1][b]))

    # ---- C. the classical marriage cross-aspects, in D9 ---------------------------
    # Read genderlessly: BOTH directions of each cross are measured and reduced to a
    # (min,max) pair, so nothing depends on which partner is in column a.
    #   Venus x Jupiter — the two karakas of marriage (spouse-as-lover, spouse-as-husband)
    #   Moon x Venus    — mind meeting affection
    #   Mars x Venus    — the mangal-style affliction of the karaka of love
    #   Saturn x Venus  — coldness, delay, denial laid on the karaka of love
    #   Rahu x Venus    — the unconventional / sudden-rupture contact
    #   Saturn x Moon   — grief laid on the mind
    #   Mars x Moon     — friction laid on the mind
    for nm, x, y in (('d9_cross_venus_jupiter', 'venus', 'jupiter'),
                     ('d9_cross_moon_venus', 'moon', 'venus'),
                     ('d9_cross_mars_venus', 'mars', 'venus'),
                     ('d9_cross_saturn_venus', 'saturn', 'venus'),
                     ('d9_cross_rahu_venus', 'true_node', 'venus'),
                     ('d9_cross_saturn_moon', 'saturn', 'moon'),
                     ('d9_cross_mars_moon', 'mars', 'moon')):
        pair(nm, SA[9][x], SB[9][y], SA[9][y], SB[9][x])

    # How the two D9 charts sit against each other as a whole, by relationship type.
    # (distance 0 is already Group A's D9 fraction, so it is not repeated.)
    #   3 = kendra (square, the 4/10 axis)      4 = trikona (trine, 5/9 — the friendly one)
    #   5 = the 6/8 shashtashtaka axis (the classical marriage-breaker)
    #   6 = opposition, the 7th — the marriage axis itself
    for k, lab in ((3.0, 'kendra'), (4.0, 'trikona'), (5.0, 'shashtashtaka'), (6.0, 'opposite')):
        m = np.zeros(n)
        for b in _GRAHAS:
            m += (fin[b] & (_sdist(SA[9][b], SB[9][b]) == k)).astype(np.float64)
        add('d9_frac_%s' % lab, np.where(known > 0, m / np.maximum(known, 1.0), np.nan))
    for k, lab in ((5.0, 'shashtashtaka'), (6.0, 'opposite')):
        m = np.zeros(n)
        for b in _GRAHAS:
            m += (fin[b] & (_sdist(SA[1][b], SB[1][b]) == k)).astype(np.float64)
        add('d1_frac_%s' % lab, np.where(known > 0, m / np.maximum(known, 1.0), np.nan))

    # ---- D. do the two charts' LORDS get on ---------------------------------------
    # A sign is read through its lord.  Take the lord of each partner's D9 sign for a
    # significator and score the two lords against the naisargika maitri table: 3 = the
    # same graha rules both, 2 = friends, 1 = neutral, 0 = enemies.  The table is
    # asymmetric, so each pair is emitted as (min,max) over the two directions — which
    # is also exactly what makes it order-free.
    def lords(name, sa, sb):
        la, lb = _lord(sa), _lord(sb)
        f1, f2 = _friend(la, lb), _friend(lb, la)
        add(name + '_min', np.minimum(f1, f2))
        add(name + '_max', np.maximum(f1, f2))
    lords('d9_lordfriend_moon', SA[9]['moon'], SB[9]['moon'])
    lords('d9_lordfriend_venus', SA[9]['venus'], SB[9]['venus'])
    lords('d9_lordfriend_jupiter', SA[9]['jupiter'], SB[9]['jupiter'])
    # cross: one partner's Moon-lord against the other's Venus-lord, both ways
    fx1 = _friend(_lord(SA[9]['moon']), _lord(SB[9]['venus']))
    fx2 = _friend(_lord(SB[9]['moon']), _lord(SA[9]['venus']))
    add('d9_lordfriend_moon_venus_min', np.minimum(fx1, fx2))
    add('d9_lordfriend_moon_venus_max', np.maximum(fx1, fx2))
    lords('d1_lordfriend_moon', SA[1]['moon'], SB[1]['moon'])

    # ---- E. vargottama and varga dignity ------------------------------------------
    # Vargottama = the same sign in D1 and D9.  Classically the single strongest thing
    # that can be said about a graha with no birth time, and it is a property of ONE
    # chart, so it is combined across partners as max/min (and as a both-partners count).
    va = np.zeros(n)
    vb = np.zeros(n)
    ka = np.zeros(n)
    kb = np.zeros(n)
    vboth = np.zeros(n)
    for b in _GRAHAS:
        fa, fb = np.isfinite(LA[b]), np.isfinite(LB[b])
        ga = fa & (SA[1][b] == SA[9][b])
        gb = fb & (SB[1][b] == SB[9][b])
        va += ga.astype(np.float64); ka += fa.astype(np.float64)
        vb += gb.astype(np.float64); kb += fb.astype(np.float64)
        vboth += (ga & gb).astype(np.float64)
    fra = np.where(ka > 0, va / np.maximum(ka, 1.0), np.nan)
    frb = np.where(kb > 0, vb / np.maximum(kb, 1.0), np.nan)
    add('vargottama_frac_max', np.maximum(fra, frb))
    add('vargottama_frac_min', np.minimum(fra, frb))
    add('vargottama_both_n', np.where(known > 0, vboth, np.nan))
    for b in ('venus', 'moon', 'jupiter'):
        ga = np.where(np.isfinite(LA[b]), (SA[1][b] == SA[9][b]).astype(np.float64), np.nan)
        gb = np.where(np.isfinite(LB[b]), (SB[1][b] == SB[9][b]).astype(np.float64), np.nan)
        add('vargottama_sum_%s' % b, ga + gb)          # 0,1,2 — order-free by summing

    # Vaiseshikamsa-style count: in how many of the 15 divisions does a graha fall in
    # its OWN sign or its exaltation sign (strength), and in how many in its
    # debilitation sign (weakness).  Combined across partners as max/min.
    def dign(body, wanted):
        ca = np.zeros(n); cb = np.zeros(n)
        for v in _V:
            ca += _in_set(SA[v][body], wanted).astype(np.float64)
            cb += _in_set(SB[v][body], wanted).astype(np.float64)
        ca = np.where(np.isfinite(LA[body]), ca, np.nan)
        cb = np.where(np.isfinite(LB[body]), cb, np.nan)
        return ca, cb
    for b in ('venus', 'moon', 'jupiter'):
        code = _CODE[b]
        ca, cb = dign(b, tuple(_OWN[code]) + (_EXALT[code],))
        add('varga_strong_%s_max' % b, np.maximum(ca, cb))
        add('varga_strong_%s_min' % b, np.minimum(ca, cb))
    for b in ('venus', 'moon'):
        ca, cb = dign(b, (_DEBIL[_CODE[b]],))
        add('varga_debil_%s_max' % b, np.maximum(ca, cb))
        add('varga_debil_%s_min' % b, np.minimum(ca, cb))

    # ---- F. D30, the chart of evils -----------------------------------------------
    # The trimsamsa portion a graha falls in is owned by Mars, Saturn, Jupiter, Mercury
    # or Venus — and the portion's owner is exactly the lord of the resulting sign, so
    # it is read straight off the D30 sign.  Mars and Saturn portions are the malefic
    # ones; Jupiter, Mercury and Venus portions the benign ones.  Venus or the Moon in
    # a malefic trimsamsa is the textbook affliction of affection and of the mind.
    def d30frac(S, L, wanted):
        m = np.zeros(n); k = np.zeros(n)
        for b in _GRAHAS:
            f = np.isfinite(L[b])
            m += (f & _in_set(_lord(S[30][b]), wanted)).astype(np.float64)
            k += f.astype(np.float64)
        return np.where(k > 0, m / np.maximum(k, 1.0), np.nan)
    mal_a = d30frac(SA, LA, (_MAR, _SAT))
    mal_b = d30frac(SB, LB, (_MAR, _SAT))
    ben_a = d30frac(SA, LA, (_JUP, _MER, _VEN))
    ben_b = d30frac(SB, LB, (_JUP, _MER, _VEN))
    add('d30_malefic_frac_max', np.maximum(mal_a, mal_b))
    add('d30_malefic_frac_min', np.minimum(mal_a, mal_b))
    add('d30_benefic_frac_max', np.maximum(ben_a, ben_b))
    add('d30_benefic_frac_min', np.minimum(ben_a, ben_b))
    for b in ('venus', 'moon'):
        xa = np.where(np.isfinite(LA[b]),
                      _in_set(_lord(SA[30][b]), (_MAR, _SAT)).astype(np.float64), np.nan)
        xb = np.where(np.isfinite(LB[b]),
                      _in_set(_lord(SB[30][b]), (_MAR, _SAT)).astype(np.float64), np.nan)
        add('d30_malefic_sum_%s' % b, xa + xb)          # 0,1,2 — order-free by summing

    # ---- G. the other departments, through their own significator -----------------
    # Venus is the karaka of the spouse and the Moon of the mind; their sign distance
    # inside a division says how the two charts meet in THAT department: D3 courage,
    # D7 progeny, D10 career, D12 the parental line, D30 misfortune, D60 past karma.
    for v in (3, 7, 10, 12, 30, 60):
        add('d%d_dist_venus' % v, _sdist(SA[v]['venus'], SB[v]['venus']))
    for v in (7, 12, 30, 60):
        add('d%d_dist_moon' % v, _sdist(SA[v]['moon'], SB[v]['moon']))

    # ---- H. modern bodies (no varga doctrine) + row metadata ----------------------
    # Kept apart and clearly named: Uranus/Neptune/Pluto have no lordship, exaltation
    # or varga rule in Parasara, and at their speeds a shared division sign is mostly a
    # statement about the era both partners were born in.  Two columns only.
    for v, lab in ((1, 'D1'), (9, 'D9')):
        m = np.zeros(n); k = np.zeros(n)
        for b in _MODERN:
            f = np.isfinite(LA[b]) & np.isfinite(LB[b])
            m += (f & (SA[v][b] == SB[v][b])).astype(np.float64)
            k += f.astype(np.float64)
        add('modern_match_frac_%s' % lab, np.where(k > 0, m / np.maximum(k, 1.0), np.nan))
    n_year, n_day = _date_flags(df, n)
    add('meta_n_year_known', n_year)     # 0..2 — how many partners have a usable year
    add('meta_n_day_precision', n_day)   # 0..2 — how many have a full YYYY-MM-DD

    if len(set(names)) != len(names):
        raise ValueError('duplicate feature names in vedic_varga')
    X = (np.column_stack(cols).astype(np.float32) if cols
         else np.zeros((n, 0), dtype=np.float32))
    if X.shape != (n, len(names)):
        raise ValueError('vedic_varga shape %s != (%d, %d)' % (X.shape, n, len(names)))
    return X, names
