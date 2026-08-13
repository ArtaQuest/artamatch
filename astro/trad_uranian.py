"""
trad_uranian.py — Uranian astrology (the Hamburg School) and Ebertin's cosmobiology.

WHAT THIS TRADITION ACTUALLY DOES, AND WHY IT SUITS THIS DATASET

Alfred Witte's Hamburg School (Witte / Friedrich Sieggruen / Ludwig Rudolph, `Regelwerk fuer
Planetenbilder`, 1928 onwards) threw away signs, houses and the classical aspects and rebuilt
astrology on ONE object: the half-sum (Halbsumme, midpoint) of two factors, and the coincidence of
half-sums, which Witte called a `Planetenbild` — a planetary picture. Reinhold Ebertin's
cosmobiology (`Kombination der Gestirneinfluesse`, 1940; English `The Combination of Stellar
Influences`, "COSI") is the same machinery with a documented dictionary of readings and the
solar-arc direction as its timer.

That is a rare stroke of luck here, because the Hamburg method needs NO birth time in principle:
its factors are planets and its instrument is a rotating dial, not a house cusp. The one factor it
does use that we cannot have is the Meridian/Ascendant axis (Witte's `M` and `A`), and those are
simply omitted — see LIMITS below. Everything else in this module is the doctrine as written.

THE DIALS. A dial folds the circle, and each fold decides which aspects count as the same contact:
  360-dial   compared mod 180 - the axis itself: a factor on the midpoint OR on its opposition
  90-dial    compared mod 90  - Witte's signature tool. Conjunction, square and opposition to the
             axis collapse onto one point, so the whole hard cross reads as a single contact
  45-dial    compared mod 45  - Ebertin's hard-aspect series, adding the semisquare (45) and the
             sesquisquare (135): the multiples of 45 all fold onto one point. This is the dial of
             the 45-degree graphic ephemeris and of COSI's midpoint work
  22.5-dial  compared mod 22.5 - the 16th-harmonic extension used by later Uranian practice, which
             folds in the semi-semisquares as well. Emitted for the cross-chart body contacts and
             for the tally; the midpoint and picture work is kept on 90 and 45, because that is
             where Witte and Ebertin actually read them
A half-sum is unambiguous on every one of these dials: the two midpoints of a pair differ by 180
degrees, and 180 is a whole number of 90s, of 45s and of 22.5s, so `m` and `m + 180` fold to the
same dial degree. That is exactly why Witte worked mod 90.

THE ARITHMETIC, EXACTLY. Every Uranian statement is a linear equation in longitudes.
  "C stands on the A/B midpoint"    <=>  A + B - 2C == 0   (mod 2p on a dial of modulus p)
  "the picture A + B - C = D"       <=>  A + B - C - D == 0 (mod 2p)   [Witte's Regelwerk form]
Both are the same equation, and the residual expressed in real degrees of the occupying factor is
`0.5 * fold(A + B - C - D, 2p)`. That single function (`_hres`) generates every midpoint, every
planetary picture and every dial in this file, so there is no place for a plausible-looking
invention to hide.

WHAT IS BUILT (14 blocks)
  1  dial positions of every body on the 90- and 45-dial, circularly encoded
  2  cross-chart hard-aspect distance between the two radices on all four dials
  3  the same contacts as orb kernels at three Uranian orbs (0.5, 1, 2 degrees)
  4  own-chart midpoint trees: how many of my own half-sums each of my factors stands on
  5  cross-chart midpoint trees: how many of my half-sums the partner's factors stand on
  6  the COSI union/offspring midpoint axes, contacted by the partner and by the wedding sky
  7  the same COSI axes occupied inside each partner's own radix
  8  40 classical planetary pictures for marriage and children, in five owner configurations
  9  solar-arc directions: each radix advanced by its own solar arc to the wedding, read against
     the partner's radix and against the partner's directed chart
 10  solar-arc directed factors falling on the partner's COSI union/offspring axes
 11  the solar arc itself (magnitude and dial phase) — the directive measure
 12  the eight Uranian hypotheticals: dial positions and cross-chart contacts
 13  26 Uranian pictures for marriage and offspring built on the hypotheticals
 14  THE HAMBURG TALLY — the tradition's own numbers: how many contacts, and the benefic minus
     malefic balance under Ebertin's own valuations

THE HYPOTHETICALS. Witte's four (Cupido, Hades, Zeus, Kronos) and Sieggruen's four (Apollon,
Admetos, Vulkanus, Poseidon) are exposed by pyswisseph as `swe.CUPIDO` .. `swe.POSEIDON` and are
computed from built-in osculating elements, so they need no extra ephemeris file. This module
PROBES them at run time (`_hypotheticals`): every one of the 6 instants x 8 bodies must return a
finite, varying longitude, or blocks 12 and 13 are dropped entirely and `SKIPPED` says so. On this
installation they resolve. Their Uranian meanings, used to choose the pictures below, are Witte's:
Cupido = marriage, the family, the group; Hades = decay, illness, the sordid; Zeus = begetting,
procreation, directed fire; Kronos = authority, standing; Apollon = multiplicity, increase,
science; Admetos = blockage, narrowness, sterility; Vulkanus = great force; Poseidon = spirit.

SOLAR ARC, COMPUTED PROPERLY. The solar arc is the Sun's own secondary-progressed travel, which is
why it runs near one degree per year without being defined as such. `core` gives the secondary
progression as slots 3 and 4 (a day for a year), so the arc is
`arc = mod(LON[prog, Sun] - LON[birth, Sun], 360)` and the directed chart is a rigid rotation:
every natal factor, and therefore every half-sum, advances by that same arc (Ebertin, COSI, on
solar-arc directions). Both radices are directed to the wedding date.

LIMITS, STATED PLAINLY
  * NO MERIDIAN, NO ASCENDANT. Witte's personal points `M` (Meridian) and `A` (Ascendant) are half
    of classical Uranian practice — "M in the picture" is how the method makes a picture personal —
    and both need a birth time and place, which this dataset does not have. They are omitted, not
    proxied: a fabricated Meridian would put a fake factor into every picture and quietly corrupt
    the whole block. The Aries point (0 Aries, Witte's `Widderpunkt`, "the world, the public") IS
    used, because it is a fixed zodiacal reference and needs no birth data.
  * THE MOON IS UNCERTAIN BY ROUGHLY +-6 DEGREES at a noon-only birth. Uranian orbs are 1 degree.
    Every Moon-bearing picture is therefore blurred well past its own orb, and the same goes for
    any half-sum containing the Moon (which carries half the Moon's error, +-3 degrees). Nothing can
    fix that; the orb-kernel representations at width 2 degrees are the ones that degrade least.
  * SOLAR RETURN / KINETIC ARCS not attempted: they need the birth time to place the return.
  * THE HALF-SUM FACTOR LIST IS THE SCHOOL'S OWN, not everything `core` offers. Midpoints and
    pictures are taken over the ten bodies + the true lunar node + the Aries point (12 factors, 66
    axes), because that is Witte's list; running all 18 available bodies would give 153 axes of
    which half are asteroid half-sums no Uranian text reads. Chiron, Ceres and Juno do appear, in
    the cross-chart dial-distance block, where a body-to-body contact needs no doctrine to license
    it. MeanNode is dropped as a duplicate of TrueNode.
  * The Aries point contributes a constant column wherever it is encoded alone; zero-variance
    columns are pruned by `_Pack.out` so no block carries dead weight.

Interface: `TRADITION`, `build(E) -> {name: (E.n, k) float64}`. Deterministic, no randomness, no
file writes, reads only `core` (plus Swiss Ephemeris for the hypotheticals, through the same
`swe` handle and ephemeris path `core` has already configured).
"""

import numpy as np
import swisseph as swe

from core import load

TRADITION = "Uranian / Hamburg School (Witte, Sieggruen, Rudolph) & Ebertin cosmobiology"

# ── which factors the Hamburg School works with ─────────────────────────────────────────────────
# Witte's factor list is the ten bodies plus the lunar node plus M and A (omitted, see LIMITS) plus
# the Aries point. `Ari` is longitude 0 by definition.
CORE = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune",
        "Pluto", "TrueNode"]
MPF = CORE + ["Ari"]                       # the half-sum factor list: 12 factors, 66 axes
CROSS = CORE + ["Chiron", "Ceres", "Juno"]  # 14 bodies for the raw cross-chart dial distances
CONTACT = ["Sun", "Moon", "Venus", "Jupiter", "Saturn", "TrueNode"]   # what "contacts" an axis
DIRECTED = ["Sun", "Moon", "Venus", "Mars", "Jupiter", "Saturn"]      # solar-arc directed factors

HYP = ["Cupido", "Hades", "Zeus", "Kronos", "Apollon", "Admetos", "Vulkanus", "Poseidon"]

# ── Ebertin, The Combination of Stellar Influences: the midpoint axes read for union and offspring
# Sign is Ebertin's own valuation of the axis for marriage and children (+1 favourable, -1
# hindering, 0 ambivalent), used ONLY for the signed tally in block 14. Ebertin publishes no points
# total, so the arithmetic of that tally is ours; the VALUATIONS are his, quoted per line.
COSI = [
    ("Sun", "Moon", +1),          # COSI Su/Mo: "the marriage axis" - union of the sexes, conception
    ("Sun", "Venus", +1),         # Su/Ve: love, harmony, the wish to be joined
    ("Moon", "Venus", +1),        # Mo/Ve: the female principle, motherhood, affection
    ("Venus", "Jupiter", +1),     # Ve/Ju: happy love, a happy marriage, the birth of a child
    ("Moon", "Jupiter", +1),      # Mo/Ju: happy family life, the wish for children, a birth
    ("Sun", "Jupiter", +1),       # Su/Ju: healthy procreative power, fatherhood, fortunate union
    ("Venus", "Mars", +1),        # Ve/Ma: the sex act, procreation, marriage
    ("Mars", "Jupiter", +1),      # Ma/Ju: fruitful and successful procreation
    ("Moon", "TrueNode", +1),     # Mo/Node: association with a woman, the family bond
    ("Sun", "TrueNode", +1),      # Su/Node: association with a man, the marriage bond
    ("Venus", "TrueNode", +1),    # Ve/Node: a love union, marriage
    ("Jupiter", "TrueNode", +1),  # Ju/Node: a happy union, a birth, increase of the family
    ("Moon", "Mars", +1),         # Mo/Ma: female fertility, pregnancy, a premature birth
    ("Moon", "Saturn", -1),       # Mo/Sa: the sorrowful mother, separation from women, low fertility
    ("Venus", "Saturn", -1),      # Ve/Sa: inhibited love, separation, sterile feeling
    ("Saturn", "TrueNode", -1),   # Sa/Node: sad or restricted unions, separation
    ("Sun", "Saturn", -1),        # Su/Sa: estrangement, hindered vitality
    ("Mars", "Saturn", -1),       # Ma/Sa: destructive energy, an interrupted procreation
    ("Venus", "Neptune", -1),     # Ve/Ne: illusory love, deception, weak fertility
    ("Moon", "Neptune", -1),      # Mo/Ne: emotional deception, morbid or unclear feeling
    ("Moon", "Uranus", 0),        # Mo/Ur: sudden emotional excitement, unusual family circumstance
    ("Venus", "Uranus", 0),       # Ve/Ur: sudden love, love at first sight, irregular unions
    ("Moon", "Pluto", 0),         # Mo/Pl: deep emotional upheaval, pregnancy and birth
    ("Venus", "Pluto", 0),        # Ve/Pl: passionate love, fanatical eroticism, a birth
    ("Jupiter", "Pluto", 0),      # Ju/Pl: the urge to increase, great fortune
    ("Jupiter", "Uranus", 0),     # Ju/Ur: sudden good fortune, a happy release
]

# ── classical planetary pictures for marriage and children ──────────────────────────────────────
# Read as A + B = C + D, i.e. half-sum(A,B) coincides with half-sum(C,D) — Witte's Regelwerk form
# A + B - C = D. Where D repeats C the picture degenerates to "C stands on the A/B midpoint", the
# single commonest statement in the whole literature (e.g. Ve on Su/Mo = love within the marriage).
PIC = [
    ("Sun", "Moon", "Venus", "Jupiter", +1),        # the lights on the axis of happy love
    ("Sun", "Moon", "Venus", "Mars", +1),           # sexual union inside the marriage bond
    ("Sun", "Moon", "Venus", "TrueNode", +1),       # the love bond made public
    ("Sun", "Moon", "Jupiter", "TrueNode", +1),     # a fortunate union, a birth
    ("Sun", "Venus", "Moon", "Jupiter", +1),        # love and family happiness
    ("Venus", "Jupiter", "Moon", "TrueNode", +1),   # happy union with a woman
    ("Moon", "Jupiter", "Venus", "TrueNode", +1),   # the birth of a child
    ("Moon", "Jupiter", "Sun", "Venus", +1),        # family happiness through love
    ("Mars", "Jupiter", "Sun", "Moon", +1),         # fruitful procreation within the union
    ("Mars", "Jupiter", "Moon", "Venus", +1),       # successful procreation, fertility
    ("Venus", "Mars", "Moon", "Jupiter", +1),       # the sex act bringing a child
    ("Moon", "Venus", "Jupiter", "TrueNode", +1),   # motherhood, increase of the family
    ("Sun", "Jupiter", "Moon", "Venus", +1),        # the father and the mother
    ("Sun", "Venus", "Jupiter", "TrueNode", +1),    # publicly fortunate love
    ("Moon", "TrueNode", "Venus", "Jupiter", +1),   # the woman, love, and happiness
    ("Jupiter", "TrueNode", "Venus", "Mars", +1),   # a fruitful public union
    ("Sun", "Mars", "Moon", "Jupiter", +1),         # the procreative man and the family
    ("Mercury", "Venus", "Sun", "Moon", +1),        # the marriage agreement (Me = thought, contract)
    ("Moon", "Jupiter", "Mars", "TrueNode", +1),    # fruitful common action
    ("Moon", "Saturn", "Venus", "TrueNode", -1),    # restriction of the love union
    ("Venus", "Saturn", "Sun", "Moon", -1),         # separation inside the marriage
    ("Moon", "Saturn", "Jupiter", "TrueNode", -1),  # hindered increase of the family
    ("Mars", "Saturn", "Moon", "Jupiter", -1),      # an interrupted birth
    ("Venus", "Neptune", "Sun", "Moon", -1),        # an illusory union
    ("Moon", "Neptune", "Venus", "Jupiter", -1),    # weak or deceptive fertility
    ("Sun", "Moon", "Saturn", "TrueNode", -1),      # a sad or restricted union
    ("Moon", "Pluto", "Venus", "Jupiter", 0),       # birth after upheaval
    ("Venus", "Pluto", "Sun", "Moon", 0),           # passionate union
    ("Jupiter", "Pluto", "Moon", "Venus", 0),       # great increase
    ("Venus", "Uranus", "Sun", "Moon", 0),          # a sudden marriage
    ("Moon", "Uranus", "Venus", "Jupiter", 0),      # an unexpected birth
    ("Sun", "Moon", "Venus", "Venus", +1),          # Ve ON Su/Mo: love within the marriage
    ("Sun", "Moon", "Jupiter", "Jupiter", +1),      # Ju ON Su/Mo: a happy marriage, a birth
    ("Sun", "Moon", "Saturn", "Saturn", -1),        # Sa ON Su/Mo: separation, a cold union
    ("Venus", "Jupiter", "Moon", "Moon", +1),       # Mo ON Ve/Ju: motherhood
    ("Moon", "Jupiter", "Venus", "Venus", +1),      # Ve ON Mo/Ju: a loved child
    ("Venus", "Mars", "Jupiter", "Jupiter", +1),    # Ju ON Ve/Ma: conception, a child
    ("Sun", "Moon", "Mars", "Mars", 0),             # Ma ON Su/Mo: the sex act in the union
    ("Sun", "Moon", "Neptune", "Neptune", -1),      # Ne ON Su/Mo: an unclear or deceptive union
    ("Sun", "Moon", "Uranus", "Uranus", 0),         # Ur ON Su/Mo: a sudden or irregular union
]

# ── Uranian pictures built on the hypotheticals ─────────────────────────────────────────────────
# Cupido = marriage/family/group, Zeus = begetting, Apollon = multiplicity, Admetos = blockage,
# Hades = decay, Kronos = authority, Vulkanus = great force, Poseidon = spirit (Witte's Regelwerk;
# Niggemann, Uranian Astrology).
UPIC = [
    ("Moon", "Zeus", "Sun", "Venus", +1),           # procreation within love
    ("Moon", "Jupiter", "Zeus", "Cupido", +1),      # a child begotten into the family
    ("Venus", "Cupido", "Sun", "Moon", +1),         # the marriage itself
    ("Jupiter", "Cupido", "Moon", "Venus", +1),     # family happiness
    ("Zeus", "Cupido", "Sun", "Moon", +1),          # procreation inside the marriage
    ("Moon", "Cupido", "Venus", "Jupiter", +1),     # a happy family
    ("Venus", "Zeus", "Moon", "Jupiter", +1),       # loving procreation, a birth
    ("Cupido", "TrueNode", "Sun", "Moon", +1),      # the marriage bond made public
    ("Apollon", "Moon", "Venus", "Jupiter", +1),    # several children
    ("Apollon", "Jupiter", "Sun", "Moon", +1),      # expansion of the family
    ("Kronos", "Venus", "Sun", "Moon", 0),          # marriage to a person of standing
    ("Vulkanus", "Mars", "Moon", "Jupiter", 0),     # great force in procreation
    ("Poseidon", "Venus", "Sun", "Moon", 0),        # an idealised union
    ("Moon", "Admetos", "Venus", "Jupiter", -1),    # blocked fertility
    ("Zeus", "Admetos", "Sun", "Moon", -1),         # obstructed procreation
    ("Moon", "Hades", "Venus", "Jupiter", -1),      # illness or loss around a birth
    ("Admetos", "Cupido", "Sun", "Moon", -1),       # a narrowed, restricted family
    ("Hades", "Cupido", "Venus", "Jupiter", -1),    # a troubled family
    ("Venus", "Admetos", "Moon", "Jupiter", -1),    # love withheld, no increase
    ("Sun", "Moon", "Cupido", "Cupido", +1),        # Cu ON Su/Mo: marriage
    ("Sun", "Moon", "Zeus", "Zeus", +1),            # Ze ON Su/Mo: procreation
    ("Sun", "Moon", "Apollon", "Apollon", +1),      # Ap ON Su/Mo: a wide family, many children
    ("Sun", "Moon", "Admetos", "Admetos", -1),      # Ad ON Su/Mo: sterility, separation
    ("Sun", "Moon", "Hades", "Hades", -1),          # Ha ON Su/Mo: a sordid or sick union
    ("Venus", "Jupiter", "Zeus", "Zeus", +1),       # Ze ON Ve/Ju: a happily begotten child
    ("Moon", "Jupiter", "Cupido", "Cupido", +1),    # Cu ON Mo/Ju: the family increases
]

# Uranian orbs. Witte and Rudolph work at 1 degree on the 90-dial; Ebertin allows 1 deg 30' for the
# Sun/Moon axes. Three widths are emitted because the orb IS a doctrinal parameter.
ORBS = (0.5, 1.0, 2.0)
ORB = 1.0
ORB_COSI = 1.5


# ── the one piece of arithmetic ─────────────────────────────────────────────────────────────────
def _fold(x, p):
    """Signed offset of x into [-p/2, p/2) — one turn of a dial of modulus p."""
    return np.mod(np.asarray(x, dtype=np.float64) + 0.5 * p, p) - 0.5 * p


def _hres(S, dial):
    """Half-sum residual, in real degrees, for S = A + B - C - D on a dial of modulus `dial`.

    half-sum(A,B) == half-sum(C,D) mod `dial`  <=>  A+B-C-D == 0 mod 2*dial. `dial` is 180 for the
    360-dial (the midpoint axis, midpoint or opposition), 90 for Witte's 90-dial, 45 for the
    22.5-degree hard series.
    """
    return 0.5 * _fold(S, 2.0 * dial)


def _kern(r, w):
    """Gaussian orb kernel, 1 at exact contact."""
    return np.exp(-0.5 * (np.asarray(r, dtype=np.float64) / w) ** 2)


def _dd(a, b, p):
    """Absolute dial distance between two longitudes on a dial of modulus p."""
    return np.abs(_fold(a - b, p))


def _axes(names):
    return [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]


AXES = _axes(MPF)          # 66 half-sum axes over the 12 Hamburg factors


class _Pack:
    """Column accumulator: appends (n,) or (n,k) pieces, prunes dead columns, guarantees finite."""

    def __init__(self, n):
        self.n = n
        self.v = []

    def add(self, a):
        a = np.asarray(a, dtype=np.float64)
        if a.ndim == 1:
            a = a[:, None]
        assert a.shape[0] == self.n, f"bad rows {a.shape}"
        self.v.append(a)
        return self

    def out(self):
        X = np.concatenate(self.v, axis=1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        # NO VARIANCE PRUNING HERE, DELIBERATELY. This used to drop columns whose standard deviation was
        # zero in the batch being built, and that made a block's WIDTH a function of the DATA rather than
        # of the code. Two consequences, both silent: a scoring batch (one couple, or ten thousand
        # candidates sharing a fixed partner) has many constant columns, so prediction handed the model a
        # narrower and differently-ordered matrix than training did; and a full run built in row chunks
        # produced chunks of different widths that could not be concatenated. Constant columns are now
        # pruned exactly once, globally, by run.collect, which records `kept_idx` in the manifest so
        # prediction can select the same columns. Width is a function of the code alone.
        return np.ascontiguousarray(X, dtype=np.float64)


# ── factor tables ───────────────────────────────────────────────────────────────────────────────
def _hypotheticals(E):
    """The eight Uranian hypotheticals at all six instants, or None if they do not resolve.

    pyswisseph exposes them as swe.CUPIDO..swe.POSEIDON and computes them from built-in osculating
    elements. Probed here rather than assumed: a body that returned a constant or non-finite
    longitude would be a fabrication, so on any failure the caller drops the hypothetical blocks.
    """
    codes = []
    for nm in HYP:
        c = getattr(swe, nm.upper(), None)
        if c is None:
            return None
        codes.append(int(c))
    H = np.empty((E.LON.shape[0], len(codes), E.n), dtype=np.float64)
    cache = {}
    try:
        for s in range(E.LON.shape[0]):
            for k in range(E.n):
                jd = float(E.JD[s, k])
                key = round(jd, 6)
                v = cache.get(key)
                if v is None:
                    v = np.array([swe.calc_ut(jd, c, swe.FLG_SWIEPH | swe.FLG_SPEED)[0][0]
                                  for c in codes], dtype=np.float64)
                    cache[key] = v
                H[s, :, k] = v
    except Exception:
        return None
    if not np.isfinite(H).all():
        return None
    # A hypothetical that never moves is not a body — but this used to test `H[0].std(axis=1)`, and axis 1
    # of an (8, n) slice is the ROW axis, so whether the block existed at all depended on how much the
    # batch's dates happened to span. One couple, or a narrow chunk, and the whole tradition vanished. The
    # test now asks the ephemeris directly whether each hypothetical moves over a fixed century, which is a
    # question about the body.
    if not _hypotheticals_move(codes):
        return None
    return np.mod(H, 360.0)


_MOVE_OK = {}


def _hypotheticals_move(codes):
    """Does each hypothetical actually move? Asked of a FIXED century, not of the batch's own dates."""
    key = tuple(codes)
    if key in _MOVE_OK:
        return _MOVE_OK[key]
    ok = True
    try:
        for c in codes:
            a = swe.calc_ut(2415020.5, c, swe.FLG_SWIEPH | swe.FLG_SPEED)[0][0]   # 1900-01-01
            b = swe.calc_ut(2451545.0, c, swe.FLG_SWIEPH | swe.FLG_SPEED)[0][0]   # 2000-01-01
            if abs((b - a + 180.0) % 360.0 - 180.0) < 1.0:
                ok = False
                break
    except Exception:
        ok = False
    _MOVE_OK[key] = ok
    return ok


def _factors(E, H, slot):
    """name -> (n,) longitude, for one instant slot: the 18 bodies, the Aries point, hypotheticals."""
    d = {nm: np.asarray(E.LON[slot, E.IDX[nm]], dtype=np.float64) for nm in E.NAME}
    d["Ari"] = np.zeros(E.n, dtype=np.float64)
    if H is not None:
        for i, nm in enumerate(HYP):
            d[nm] = H[slot, i]
    return d


def _directed(E, H, birth, prog):
    """Solar-arc directed chart: every factor advanced by the Sun's secondary-progressed travel."""
    arc = np.mod(E.LON[prog, E.IDX["Sun"]] - E.LON[birth, E.IDX["Sun"]], 360.0)
    d = {nm: np.mod(np.asarray(E.LON[birth, E.IDX[nm]], dtype=np.float64) + arc, 360.0)
         for nm in E.NAME}
    if H is not None:
        for i, nm in enumerate(HYP):
            d[nm] = np.mod(H[birth, i] + arc, 360.0)
    return d, np.asarray(arc, dtype=np.float64)


def _trees(mp, oc, dial, orb, self_excl):
    """Midpoint trees. mp = chart owning the axes, oc = chart supplying the occupying factors.

    Cosmobiology's "midpoint tree" for a factor is the list of every half-sum axis it stands on
    (Ebertin, COSI, introduction). Returned as: hard count per occupying factor, soft (kernel) sum
    per occupying factor, and the soft sum per AXIS (how crowded each axis is).
    """
    n = oc[MPF[0]].shape[0]
    hard = np.zeros((n, len(MPF)))
    soft = np.zeros((n, len(MPF)))
    per = np.zeros((n, len(AXES)))
    for pi, (x, y) in enumerate(AXES):
        S = mp[x] + mp[y]
        for ci, c in enumerate(MPF):
            if self_excl and (c == x or c == y):
                continue
            r = np.abs(_hres(S - 2.0 * oc[c], dial))
            hard[:, ci] += (r <= orb)
            k = _kern(r, orb)
            soft[:, ci] += k
            per[:, pi] += k
    return hard, soft, per


def _pic_resid(fa, fb, pic, dial):
    """Residual of one picture. fa supplies A and B, fb supplies C and D (fa is fb for own-chart)."""
    A, B, C, D = pic[0], pic[1], pic[2], pic[3]
    return _hres(fa[A] + fa[B] - fb[C] - fb[D], dial)


def _pic_resid_mixed(f1, f2, pic, dial):
    """The combined-chart form: A and C from one radix, B and D from the other.

    The 90-degree dial is worked by laying the two charts on the same disc, so a half-sum may take
    one factor from each partner (Witte's Kombination). This is the owner pattern A_1 + B_2 vs
    C_1 + D_2.
    """
    A, B, C, D = pic[0], pic[1], pic[2], pic[3]
    return _hres(f1[A] + f2[B] - f1[C] - f2[D], dial)


# ── build ───────────────────────────────────────────────────────────────────────────────────────
def build(E):
    n = E.n
    H = _hypotheticals(E)
    FO = _factors(E, H, E.SLOT["older"])
    FY = _factors(E, H, E.SLOT["younger"])
    FW = _factors(E, H, E.SLOT["wedding"])
    DO, arc_o = _directed(E, H, E.SLOT["older"], E.SLOT["prog_older"])
    DY, arc_y = _directed(E, H, E.SLOT["younger"], E.SLOT["prog_younger"])
    out = {}

    # ── 1. dial positions ───────────────────────────────────────────────────────────────────────
    # A body's place on the 90-dial is lon mod 90; encoded circularly that is cos/sin(4*lon), and
    # the 45-dial is cos/sin(8*lon). No orb, no doctrine yet — just the dial the school reads on.
    p = _Pack(n)
    for F in (FO, FY, FW):
        for nm in E.NAME:
            for mult in (4.0, 8.0):
                r = np.deg2rad(mult * F[nm])
                p.add(np.cos(r)).add(np.sin(r))
    out["ura: 90/45-dial body positions (circular)"] = p.out()

    # ── 2. cross-chart hard-aspect distance on the dials ────────────────────────────────────────
    # Two radices laid on one dial: the folded distance between the older's factor and the younger's
    # is the whole of Uranian synastry at the body-to-body level. mod 180 keeps only conjunction and
    # opposition, mod 90 folds in the squares, mod 45 the semisquares, mod 22.5 the 16th harmonic.
    p = _Pack(n)
    for dial in (180.0, 90.0, 45.0, 22.5):
        for a in CROSS:
            for b in CROSS:
                p.add(_dd(FO[a], FY[b], dial))
    out["ura: cross-chart dial distance 360/90/45/22.5"] = p.out()

    # ── 3. the same contacts as orb kernels at three Uranian orbs ───────────────────────────────
    p = _Pack(n)
    for w in ORBS:
        for a in CORE:
            for b in CORE:
                p.add(_kern(_dd(FO[a], FY[b], 45.0), w))
    out["ura: cross-chart 45-dial orb kernels 0.5/1/2deg"] = p.out()

    # ── 4. own-chart midpoint trees ─────────────────────────────────────────────────────────────
    # For each radix and for the wedding sky: how many of that chart's own 66 half-sum axes each
    # factor stands on. This is Ebertin's tree, summarised as its size.
    p = _Pack(n)
    for F in (FO, FY, FW):
        h45, s45, per45 = _trees(F, F, 45.0, ORB, True)
        h90, s90, _ = _trees(F, F, 90.0, ORB, True)
        p.add(h45).add(s45).add(h90).add(s90)
        p.add(h45.sum(axis=1)).add(h90.sum(axis=1)).add(per45.max(axis=1))
    out["ura: own-chart midpoint trees (occupation counts)"] = p.out()

    # ── 5. cross-chart midpoint trees ───────────────────────────────────────────────────────────
    # The synastry form: how many of MY half-sums the partner's factors stand on, and how crowded
    # each of my axes is with the partner's factors. Emitted in both owner orders because the
    # statement is not symmetric.
    p = _Pack(n)
    for mp, oc in ((FO, FY), (FY, FO)):
        h45, s45, per45 = _trees(mp, oc, 45.0, ORB, False)
        h90, s90, _ = _trees(mp, oc, 90.0, ORB, False)
        p.add(h45).add(s45).add(h90).add(s90).add(per45)
        p.add(h45.sum(axis=1)).add(h90.sum(axis=1))
    out["ura: cross-chart midpoint trees (partner on my axes)"] = p.out()

    # ── 6. the COSI union/offspring axes, contacted from outside ────────────────────────────────
    # Ebertin's readings are statements about ONE axis being touched by ONE factor. Here the axis
    # belongs to one partner and the touching factor to the other, or to the wedding sky (the
    # cosmobiological transit test at the event).
    p = _Pack(n)
    for mp, oc in ((FO, FY), (FY, FO), (FO, FW), (FY, FW)):
        for a, b, _s in COSI:
            S = mp[a] + mp[b]
            for c in CONTACT:
                p.add(_kern(np.abs(_hres(S - 2.0 * oc[c], 45.0)), ORB_COSI))
    out["ura: COSI union/offspring axes contacted (synastry + wedding)"] = p.out()

    # ── 7. the COSI axes occupied inside each partner's own radix ───────────────────────────────
    p = _Pack(n)
    for F in (FO, FY):
        for a, b, _s in COSI:
            S = F[a] + F[b]
            for c in CONTACT:
                if c == a or c == b:
                    continue
                r = np.abs(_hres(S - 2.0 * F[c], 45.0))
                p.add(_kern(r, ORB_COSI)).add(r)
    out["ura: COSI axes occupied in own radix"] = p.out()

    # ── 8. classical planetary pictures for marriage and children ───────────────────────────────
    # Five owner configurations of A + B = C + D: inside the older's radix, inside the younger's,
    # the older's half-sum against the younger's, the reverse, and the mixed combined form.
    p = _Pack(n)
    for pic in PIC:
        for fa, fb in ((FO, FO), (FY, FY), (FO, FY), (FY, FO)):
            r = _pic_resid(fa, fb, pic, 45.0)
            p.add(r).add(_kern(np.abs(r), ORB))
        r = _pic_resid_mixed(FO, FY, pic, 45.0)
        p.add(r).add(_kern(np.abs(r), ORB))
    out["ura: planetary pictures, marriage & children (45-dial)"] = p.out()

    # ── 9. solar-arc directions to the partner's chart ──────────────────────────────────────────
    # Ebertin's timer. Each radix is advanced by its own solar arc to the wedding date and read
    # against the partner's radix (directed-to-radix) and against the partner's directed chart
    # (directed-to-directed), on the 45-dial.
    p = _Pack(n)
    for D, F in ((DO, FY), (DY, FO)):
        for a in CORE:
            for b in CORE:
                d = _dd(D[a], F[b], 45.0)
                p.add(_kern(d, ORB)).add(d)
    for a in CORE:
        for b in CORE:
            p.add(_kern(_dd(DO[a], DY[b], 45.0), ORB))
    out["ura: solar-arc directed contacts to partner (45-dial)"] = p.out()

    # ── 10. solar-arc directed factors on the partner's COSI axes ───────────────────────────────
    # The event statement of cosmobiology: a directed factor arriving on a natal union/offspring
    # axis. Because a directed chart is a rigid rotation, the partner's axis is natal here.
    p = _Pack(n)
    for D, mp in ((DO, FY), (DY, FO)):
        for a, b, _s in COSI:
            S = mp[a] + mp[b]
            for c in DIRECTED:
                p.add(_kern(np.abs(_hres(S - 2.0 * D[c], 45.0)), ORB))
    out["ura: solar-arc directed factors on partner COSI axes"] = p.out()

    # ── 11. the solar arc itself ────────────────────────────────────────────────────────────────
    # The arc is the directive measure of the whole method and is numerically the age at the
    # wedding in degrees (a degree for a year): stated plainly so the block is not mistaken for a
    # configuration feature. Its dial phase decides WHICH natal factors the arc can reach.
    p = _Pack(n)
    p.add(arc_o).add(arc_y).add(np.abs(arc_o - arc_y)).add(0.5 * (arc_o + arc_y))
    for a in (arc_o, arc_y):
        for mult in (4.0, 8.0):
            r = np.deg2rad(mult * a)
            p.add(np.cos(r)).add(np.sin(r))
        p.add(np.abs(_fold(a, 45.0))).add(np.abs(_fold(a, 90.0)))
    p.add(np.abs(_fold(arc_o - arc_y, 45.0)))
    out["ura: solar arc magnitude and dial phase"] = p.out()

    # ── 12/13. the hypotheticals ────────────────────────────────────────────────────────────────
    if H is not None:
        p = _Pack(n)
        for F in (FO, FY, FW):
            for nm in HYP:
                r = np.deg2rad(4.0 * F[nm])
                p.add(np.cos(r)).add(np.sin(r))
        for a in HYP:
            for b in HYP:
                d = _dd(FO[a], FY[b], 45.0)
                p.add(d).add(_kern(d, ORB))
        for a in HYP:                          # my hypothetical against the partner's lights
            for c in CONTACT:
                p.add(_kern(_dd(FO[a], FY[c], 45.0), ORB))
                p.add(_kern(_dd(FY[a], FO[c], 45.0), ORB))
        out["ura: hypotheticals dial positions & cross contacts"] = p.out()

        p = _Pack(n)
        for pic in UPIC:
            for fa, fb in ((FO, FO), (FY, FY), (FO, FY), (FY, FO)):
                r = _pic_resid(fa, fb, pic, 45.0)
                p.add(r).add(_kern(np.abs(r), ORB))
            r = _pic_resid_mixed(FO, FY, pic, 45.0)
            p.add(r).add(_kern(np.abs(r), ORB))
        out["ura: Uranian offspring/marriage pictures (hypotheticals)"] = p.out()

    # ── 14. THE HAMBURG TALLY — the tradition's own numbers ─────────────────────────────────────
    # A Uranian reading ends in a count: how many hard contacts the two dials share, how many of the
    # named pictures stand, and how the favourable ones balance against the hindering ones. The
    # counts are the school's own object; the +1/-1 valuations are Ebertin's per COSI line above.
    # Ebertin publishes no points total, so the ARITHMETIC of the balance is this module's, and it
    # is kept to a plain sum so it cannot smuggle in a tuned weight.
    p = _Pack(n)
    for orb in ORBS:
        c = np.zeros(n)
        for a in CORE:
            for b in CORE:
                c += (_dd(FO[a], FY[b], 45.0) <= orb)
        p.add(c)
    for orb in (1.0, 2.0):
        c = np.zeros(n)
        for a in CORE:
            for b in CORE:
                c += (_dd(FO[a], FY[b], 90.0) <= orb)
        p.add(c)
    for dial in (180.0, 22.5):
        c = np.zeros(n)
        for a in CORE:
            for b in CORE:
                c += (_dd(FO[a], FY[b], dial) <= ORB)
        p.add(c)
    soft = np.zeros(n)
    for a in CORE:
        for b in CORE:
            soft += _kern(_dd(FO[a], FY[b], 45.0), ORB)
    p.add(soft)

    h_oy, s_oy, _ = _trees(FO, FY, 45.0, ORB, False)
    h_yo, s_yo, _ = _trees(FY, FO, 45.0, ORB, False)
    p.add(h_oy.sum(axis=1)).add(h_yo.sum(axis=1)).add(h_oy.sum(axis=1) + h_yo.sum(axis=1))
    p.add(s_oy.sum(axis=1)).add(s_yo.sum(axis=1))
    for F in (FO, FY):
        h, s, _ = _trees(F, F, 45.0, ORB, True)
        p.add(h.sum(axis=1)).add(s.sum(axis=1))

    def cosi_tally(mp, oc, orb):
        cnt = np.zeros(n)
        sgn = np.zeros(n)
        ben = np.zeros(n)
        mal = np.zeros(n)
        for a, b, s in COSI:
            S = mp[a] + mp[b]
            for c in CONTACT:
                hit = (np.abs(_hres(S - 2.0 * oc[c], 45.0)) <= orb).astype(np.float64)
                cnt += hit
                sgn += s * hit
                if s > 0:
                    ben += hit
                elif s < 0:
                    mal += hit
        return cnt, sgn, ben, mal

    for mp, oc in ((FO, FY), (FY, FO), (FO, FW), (FY, FW)):
        cnt, sgn, ben, mal = cosi_tally(mp, oc, ORB_COSI)
        p.add(cnt).add(sgn).add(ben / (ben + mal + 1.0))
    for F in (FO, FY):
        cnt, sgn, ben, mal = cosi_tally(F, F, ORB_COSI)
        p.add(cnt).add(sgn).add(ben / (ben + mal + 1.0))
    for D, mp in ((DO, FY), (DY, FO)):
        cnt, sgn, ben, mal = cosi_tally(mp, D, ORB)
        p.add(cnt).add(sgn)

    def pic_tally(table, orb):
        cols = []
        for fa, fb in ((FO, FO), (FY, FY), (FO, FY), (FY, FO)):
            cnt = np.zeros(n)
            sgn = np.zeros(n)
            for pic in table:
                hit = (np.abs(_pic_resid(fa, fb, pic, 45.0)) <= orb).astype(np.float64)
                cnt += hit
                sgn += pic[4] * hit
            cols += [cnt, sgn]
        cnt = np.zeros(n)
        sgn = np.zeros(n)
        for pic in table:
            hit = (np.abs(_pic_resid_mixed(FO, FY, pic, 45.0)) <= orb).astype(np.float64)
            cnt += hit
            sgn += pic[4] * hit
        cols += [cnt, sgn]
        return cols

    for col in pic_tally(PIC, ORB):
        p.add(col)
    for col in pic_tally(PIC, 2.0):
        p.add(col)
    if H is not None:
        for col in pic_tally(UPIC, ORB):
            p.add(col)

    c = np.zeros(n)
    for D, F in ((DO, FY), (DY, FO)):
        s = np.zeros(n)
        for a in CORE:
            for b in CORE:
                s += (_dd(D[a], F[b], 45.0) <= ORB)
        p.add(s)
        c += s
    p.add(c)
    out["ura: the Hamburg tally (contact counts, benefic-malefic balance)"] = p.out()

    return out


# ── self-test ───────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import time

    from evalx import quick

    t0 = time.time()
    E = load()
    B = build(E)
    print(f"{TRADITION}\nbuilt {len(B)} blocks in {time.time() - t0:.1f}s over {E.n:,} couples\n")

    fail = 0
    seen = set()
    total = 0
    for name, X in B.items():
        try:
            assert name.startswith("ura: "), f"{name}: block name must carry the tradition tag"
            assert name not in seen, f"{name}: duplicate block name"
            seen.add(name)
            assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
            assert X.dtype == np.float64, f"{name}: dtype {X.dtype} is not float64"
            assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
            assert X.shape[1] >= 1, f"{name}: no columns"
            assert np.isfinite(X).all(), f"{name}: non-finite values"
            assert float(X.std(axis=0).max()) > 0, f"{name}: block is all-constant"
        except AssertionError as e:
            print(f"FAIL  {e}")
            fail += 1
            continue
        total += X.shape[1]
        acc, auc = quick(E, X)
        print(f"  {name:<62} {X.shape[1]:>5} cols   acc {100 * acc:5.2f}%   AUC {auc:.4f}")

    print(f"\ntotal columns {total:,}")
    if H_MISSING := ("ura: hypotheticals dial positions & cross contacts" not in B):
        print("SKIPPED: the eight Uranian hypotheticals did not resolve on this ephemeris; blocks "
              "12 and 13 omitted rather than faked.")
    if fail:
        print(f"\n{fail} block(s) FAILED")
        sys.exit(1)
    print("\nOK")
