"""
trad_wedding_transits.py — the WEDDING DAY as a chart, read against both natal charts.

ONE IDEA, MANY ENCODINGS: what the sky on the wedding day was doing to each partner's birth sky.
Every other module in this family reads the two natal charts against each other. This one reads the
THIRD chart — the election itself (slot 2) — plus the two secondary progressions to it (slots 3, 4)
and the Davison chart (slot 5), against the two radices. Nothing here is a synastry feature between
the partners alone; every block involves the wedding instant or a direction to it.

WHERE THE DOCTRINE COMES FROM

  TRANSITS. Ptolemy, "Tetrabiblos" IV.10 ("On the divisions of the times"), reads the moving bodies
  against the natal places; the technique becomes explicit in Hephaistio and in the Persian
  tradition, and is the backbone of modern predictive work — Robert Hand, "Planets in Transit"
  (1976), is the standard reference and the source of the orbs used here. The five configurations
  are Ptolemy's own (Tetrabiblos I.13: conjunction, sextile 60, square 90, trine 120, opposition
  180 — the ratios of the whole circle to its parts).

  ORB IS A TRADITION-SPECIFIC PARAMETER, so three widths are used rather than one. 2.5 degrees is
  Hand's working transit orb for a slow body (he treats a transit as "in effect" within a couple of
  degrees and exact within minutes); 6 degrees is the ordinary modern aspect orb; 10 degrees is the
  generous end of the medieval moiety scheme (William Lilly, "Christian Astrology" 1647, p.107,
  gives Saturn and Jupiter orbs of 9-10 degrees, the Sun 15). Whether the tradition's tight orb or
  its wide orb carries the signal is exactly the sort of question three parallel blocks answer.

  APPLICATION AND SEPARATION — the central electional distinction, and the one this module is built
  around. Al-Biruni, "The Book of Instruction in the Elements of the Art of Astrology" (1029),
  sections 448-451, separates ittisal (application) from insiraf (separation): a contact that is
  still closing carries the event, one that has already passed is spent. Sahl ibn Bishr, "On
  Elections", and Bonatti, "Liber Astronomiae" tract 6, both require the significators of a
  marriage election to be APPLYING. Lilly devotes a chapter to it. Modern predictive practice keeps
  the rule (Bernadette Brady, "Predictive Astrology", 1992, on the transit's "ingress, exact and
  egress" phases).
  The implementation is exact for wedding-to-natal contacts and worth stating: a natal place does
  not move, so the signed residual r to the nearest aspect angle changes at exactly the transiting
  body's own longitude speed, dr/dt = SPD. The contact is therefore APPLYING when r and SPD have
  opposite signs and SEPARATING when they share one, and retrograde transits reverse it — which is
  why E.SPD's sign, not a table of "normal" motions, decides every applying flag here. Where both
  ends move (progressed to progressed, wedding to progressed) the relative speed is used, in
  consistent units: a real body's SPD is degrees per DAY, a progressed body's SPD is degrees per
  YEAR of life, because a day of ephemeris is a year under the day-for-a-year key.

  SECONDARY PROGRESSION, a day for a year. Placidus, "Physiomathematica" (1650), fixes the measure;
  Sakoian and Acker, "The Progressed Horoscope", and Robert Blaschke, "Astrology: A Language of
  Life" III, are the modern handbooks. Slots 3 and 4 are already progressed to the wedding by
  core.py, so the progressed chart needs no arithmetic here beyond reading the slot.

  SOLAR ARC DIRECTION. The progressed Sun's travel from its natal place is the solar arc (about a
  degree a year); the whole natal chart is then advanced by that single arc. Directly descended from
  the primary directions of Ptolemy and Naibod, made a technique in its own right by the Hamburg
  School (Alfred Witte) and by Noel Tyl, "Solar Arcs" (2001). Both directions are emitted: the
  wedding sky onto the directed chart, and the PARTNER's natal sky onto the directed chart — the
  latter is the classical "directions bring the promise of the radix to the other person".

  RELATIONSHIP CHARTS. The midpoint composite is the near midpoint of each pair of natal bodies
  (Ronald Davison; John Townley, "The Composite Chart", 1973; Robert Hand, "Planets in Composite",
  1975). The Davison chart is a real chart for the instant midway in time between the births (slot
  5). Transits to a relationship chart are standard modern practice, and the two charts disagree, so
  both are contacted separately.

  RETURNS AND LIFE-STAGE CYCLES. The solar return is the Sun's return to its natal degree — the
  wedding's distance from it, in degrees of solar motion, is the phase of the return year. The lunar
  return is the same for the Moon (27.32 days). The Saturn cycle (29.46 years; Grant Lewi,
  "Astrology for the Millions", 1940; Liz Greene, "Saturn", 1976), the Jupiter cycle (11.86 years)
  and the progressed lunation cycle (Dane Rudhyar, "The Lunation Cycle", 1967; Blaschke) are the
  four life-stage markers modern practice names, and all four are read as a phase, not an event.

  THE MARRIAGE-TIMING SHORTLIST. Transiting Jupiter or Saturn to the natal Sun, Moon or Venus;
  transiting Uranus to Venus; transiting Neptune or Pluto to Venus; the Jupiter and Saturn returns;
  transiting node to the lights; Jupiter or Saturn to Juno, the asteroid of the marriage bond. This
  is the list Hand (1976), Brady (1992) and Celeste Teal, "Predicting Events with Astrology" (1999),
  actually give for a marriage, and it is emitted as a deliberately tiny block so that a dozen
  well-chosen contacts can be compared against a thousand indiscriminate ones.

THE HARD DATA LIMIT AND THE PROXIES USED, NAMED PLAINLY

  Only DATES are known — no birth time, no wedding time, no place. Everything, including the
  wedding, is cast for 12:00 UT. That removes the part of electional doctrine that matters most:

    NO ASCENDANT OF THE ELECTION, NO MIDHEAVEN, NO HOUSES. Sahl and Bonatti both begin a marriage
    election with the Ascendant and the seventh house; neither is computable. There is no proxy for
    them in this module — a fabricated Ascendant would be a fabricated feature — so no block here
    claims one. What survives is the whole body-to-body layer, which is the majority of the
    technique and all of what transits and directions actually assert.
    NO PLANETARY HOUR. The hour lord of the election needs the local time and sunrise. Not
    attempted. (The planetary DAY lord needs only the date and is available from the weekday, but it
    belongs to the calendrical module, not here.)
    THE WEDDING TIME IS A NOON PROXY. A wedding at 12:00 UT is at worst about half a day from the
    real ceremony, so every transit orb below carries the error of half a day of that body's motion:
    negligible for Saturn (0.002 deg), about 6 degrees for the Moon. Lunar transit columns are
    therefore the weakest in every block and are kept only because the doctrine insists on the Moon.
    THE NATAL MOON is uncertain by the same +-6 degrees, so a Moon-to-Moon contact carries both
    errors. The lunar return block is a noon proxy twice over and says so.
    SECONDARY PROGRESSIONS inherit the noon assumption exactly; the progressed Moon moves about a
    degree a month, so its noon error is small in progressed terms even though its natal error is
    not.

  E.Y is never read, by any function in this file, for any purpose. Constant columns are pruned on
  the feature matrix alone.
"""

import numpy as np

TRADITION = ("Wedding-day transits and directions (electional application/separation, secondary "
             "progressions, solar arc, composite/Davison, returns and life-stage cycles)")

# ── instant slots (core.py's own order) ─────────────────────────────────────────────────────────
OLD, YNG, WED, PO, PY, DAV = 0, 1, 2, 3, 4, 5
YR = 365.2425
SUN_DEG_PER_DAY = 360.0 / YR          # 0.98565, the Sun's mean tropical motion
MOON_DEG_PER_DAY = 360.0 / 27.321582  # the sidereal month, for lunar-return distance in days

# ── the five Ptolemaic configurations (Tetrabiblos I.13) ───────────────────────────────────────
PTOL = (0.0, 60.0, 90.0, 120.0, 180.0)
PTOL_NAME = ("conj", "sext", "squa", "trin", "oppo")
HARD = (0.0, 90.0, 180.0)             # conjunction and the square family
SOFT = (60.0, 120.0)                  # the flowing pair

# ── minor and harmonic angles, by family, with the tight orbs those families use ────────────────
# octiles: Kepler, then Ebertin's 45-degree dial (orb about 1.5 deg)
# twelfth harmonic: semisextile 30 and quincunx 150
# quintiles: Kepler, "Harmonices Mundi" (1619)
# septiles: Addey and John Nelson
# noviles: navamsa in origin, brought west by Rudhyar and Addey
S7 = 360.0 / 7.0
FAMILIES = (
    ("octile", (45.0, 135.0)),
    ("twelfth", (30.0, 150.0)),
    ("quintile", (72.0, 144.0)),
    ("septile", (S7, 2.0 * S7, 3.0 * S7)),
    ("novile", (40.0, 80.0, 160.0)),
)
MINOR_ALL = tuple(sorted({a for _, fam in FAMILIES for a in fam}))
MINOR_ORB = 1.5

# ── body sets ──────────────────────────────────────────────────────────────────────────────────
C7N = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
M10N = C7N + ("Uranus", "Neptune", "Pluto")
MARN = ("Sun", "Moon", "Venus", "Mars", "Jupiter", "Saturn")     # the marriage significators
SIGN4 = ("Sun", "Moon", "Venus", "Juno")                          # what a marriage transit aims at


# ── primitives ─────────────────────────────────────────────────────────────────────────────────
def _wrap(d):
    """Signed angular difference in (-180, 180]."""
    return (np.asarray(d, dtype=np.float64) + 180.0) % 360.0 - 180.0


def _mid(a, b):
    """The NEAR midpoint of two longitudes — the composite convention (Hand, Townley)."""
    return np.mod(a + _wrap(b - a) / 2.0, 360.0)


def _ares(d, a):
    """Signed residual of a signed difference `d` to one aspect angle `a`, nearer side chosen."""
    r1 = _wrap(d - a)
    if a == 0.0 or a == 180.0:
        return r1
    r2 = _wrap(d + a)
    return np.where(np.abs(r1) <= np.abs(r2), r1, r2)


def _resid(d, angles):
    """Signed residual to the NEAREST of `angles`. Kept memory-light: one candidate at a time."""
    best = None
    for a in angles:
        r = _ares(d, a)
        best = r if best is None else np.where(np.abs(r) < np.abs(best), r, best)
    return best


def _k(r, w):
    """Gaussian orb kernel on a signed residual: 1 at exact, falling off over `w` degrees."""
    return np.exp(-0.5 * (np.asarray(r, dtype=np.float64) / w) ** 2)


def _apply_sign(r, rate):
    """+1 applying, -1 separating, 0 stationary.

    The residual changes at `rate`, so |r| shrinks exactly when r and rate have opposite signs.
    A retrograde transit (negative SPD) therefore flips the verdict, which is the whole point.
    """
    return -np.sign(r) * np.sign(rate)


def _fl(A):
    """(..., n) -> (n, prod of the leading axes), C-order and deterministic."""
    A = np.asarray(A, dtype=np.float64)
    return np.ascontiguousarray(np.moveaxis(A, -1, 0).reshape(A.shape[-1], -1))


def _pack(parts, n):
    """Stack a list of (n, k) / (n,) pieces into one (n, K) matrix."""
    cols = []
    for p in parts:
        p = np.asarray(p, dtype=np.float64)
        if p.ndim == 1:
            p = p[:, None]
        assert p.shape[0] == n, f"part has {p.shape[0]} rows, expected {n}"
        cols.append(p)
    return np.concatenate(cols, axis=1)


def _fin(X):
    """Force (n, k) float64, finite, and drop columns with no variance at all."""
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[:, None]
    X = np.ascontiguousarray(X)
    X[~np.isfinite(X)] = 0.0
    keep = X.std(axis=0) > 1e-12
    return X[:, keep] if keep.any() else X


def _grid(tr, na):
    """Signed transit angles for every (transiting, natal) pair: (T, C, n)."""
    return _wrap(np.asarray(tr)[:, None, :] - np.asarray(na)[None, :, :])


# ── block 1: the full 18x18 grid, circular ─────────────────────────────────────────────────────
def _b_circular(E):
    """Every wedding body to every natal body, both partners, as cos/sin of the signed difference.

    324 ordered pairs per partner. The circular form is the complete, orb-free statement of the
    transit: any aspect kernel at any width is a function of it, and its Fourier content is exactly
    Addey's harmonic analysis of the transit. Nothing is thresholded, so a linear model sees the
    first harmonic and a tree can carve out any angle it likes.

    Wedding time is a noon proxy: the lunar columns carry about +-6 degrees from that alone, and the
    natal lunar columns another +-6 from the birth time.
    """
    W = E.LON[WED]
    parts = []
    for nat in (E.LON[OLD], E.LON[YNG]):
        d = np.deg2rad(_grid(W, nat))
        parts += [_fl(np.cos(d)), _fl(np.sin(d))]
    return _fin(_pack(parts, E.n))


# ── block 2: the same grid as Ptolemaic orb kernels, three widths ──────────────────────────────
def _b_orbsweep(E):
    """The 18x18 grid at the five Ptolemaic angles, swept over THREE orb widths.

    Per pair and width, one column: the kernel on the residual to the nearest of the five angles.
    The three widths are the tradition's own disagreement made explicit — 2.5 degrees is Hand's
    working transit orb, 6 the ordinary modern orb, 10 the medieval moiety end (Lilly, CA p.107).

    ORDER-BLIND BY CONSTRUCTION: each column is the tighter of the couple's two orbs, max over the
    two partners, because we do not know which partner is bride and which groom and the doctrine's
    claim is about the couple. The partner-resolved version of the same grid is block 1 (exact
    angles, both partners) and block 3 (signed, both partners), so nothing is lost overall.
    """
    W = E.LON[WED]
    rO = _resid(_grid(W, E.LON[OLD]), PTOL)
    rY = _resid(_grid(W, E.LON[YNG]), PTOL)
    parts = [_fl(np.maximum(_k(rO, w), _k(rY, w))) for w in (2.5, 6.0, 10.0)]
    return _fin(_pack(parts, E.n))


# ── block 3: applying versus separating, signed, over the whole grid ───────────────────────────
def _b_applying(E):
    """The 18x18 grid at 6 degrees, SIGNED by application or separation. Both partners.

    +kernel where the transit is still closing on the aspect, -kernel where it has passed. This is
    al-Biruni's ittisal/insiraf (sections 448-451) and Bonatti's requirement that the significators
    of a marriage election be applying, as a single continuous feature per contact.

    The natal place is fixed, so the residual moves at exactly the transiting body's own speed and
    the verdict is exact rather than approximate; a retrograde transit reverses it. The magnitude is
    the ordinary 6-degree Ptolemaic kernel, so this block is a strict refinement of the unsigned
    6-degree grid, not a different measurement.
    """
    W, WS = E.LON[WED], E.SPD[WED]
    parts = []
    for nat in (E.LON[OLD], E.LON[YNG]):
        r = _resid(_grid(W, nat), PTOL)
        rate = np.broadcast_to(WS[:, None, :], r.shape)
        parts.append(_fl(_apply_sign(r, rate) * _k(r, 6.0)))
    return _fin(_pack(parts, E.n))


# ── block 4: the minor and harmonic angles over the whole grid ─────────────────────────────────
def _b_minor_wide(E):
    """The 18x18 grid against the MINOR and HARMONIC angles, both partners, one column per pair.

    The union of the octile (45/135), twelfth-harmonic (30/150), quintile (72/144), septile
    (51.43/102.86/154.29) and novile (40/80/160) families, at the 1.5-degree orb those families are
    traditionally worked to. One column per pair per partner: the kernel on the residual to the
    nearest minor angle of any family. Which family it was is resolved in block 6, on the classical
    seven, where the columns can afford to be named.
    """
    W = E.LON[WED]
    parts = []
    for nat in (E.LON[OLD], E.LON[YNG]):
        parts.append(_fl(_k(_resid(_grid(W, nat), MINOR_ALL), MINOR_ORB)))
    return _fin(_pack(parts, E.n))


# ── block 5: the classical seven only, named angles ────────────────────────────────────────────
def _b_classical(E):
    """The SEVEN VISIBLE BODIES only — what any pre-telescopic astrologer would actually have read.

    49 ordered pairs, five named Ptolemaic angles, the ordinary 6-degree orb, both partners: 490
    columns instead of the wide grid's thousands, and every one of them a contact a Hellenistic,
    Persian or Renaissance astrologer would recognise on sight. Uranus, Neptune, Pluto, the nodes,
    Lilith, Chiron and the asteroids are all deliberately absent: no tradition older than 1781 could
    see them, so their inclusion in the wide blocks is breadth, not doctrine.
    """
    W = E.LON[WED]
    c7 = [E.IDX[b] for b in C7N]
    parts = []
    for nat in (E.LON[OLD], E.LON[YNG]):
        d = _grid(W[c7], nat[c7])
        for a in PTOL:
            parts.append(_fl(_k(_ares(d, a), 6.0)))
    return _fin(_pack(parts, E.n))


# ── block 6: the classical seven, orb sweep + families + application ───────────────────────────
def _b_classical_detail(E):
    """The classical 7x7 grid again, with everything the wide blocks had to collapse.

    Per pair and partner: the nearest-Ptolemaic kernel at a tight 2.5 and a wide 10 degrees (the
    same sweep as block 2 but partner-resolved), the signed applying/separating kernel at 4 degrees
    (tighter than block 3, because application only matters near exactitude), and one named kernel
    for each of the five minor families at 1.5 degrees. Eight columns per contact, 784 in all.
    """
    W, WS = E.LON[WED], E.SPD[WED]
    c7 = [E.IDX[b] for b in C7N]
    parts = []
    for nat in (E.LON[OLD], E.LON[YNG]):
        d = _grid(W[c7], nat[c7])
        rp = _resid(d, PTOL)
        parts += [_fl(_k(rp, 2.5)), _fl(_k(rp, 10.0))]
        rate = np.broadcast_to(WS[c7][:, None, :], d.shape)
        parts.append(_fl(_apply_sign(rp, rate) * _k(rp, 4.0)))
        for _, fam in FAMILIES:
            parts.append(_fl(_k(_resid(d, fam), MINOR_ORB)))
    return _fin(_pack(parts, E.n))


# ── block 7: order-blind symmetric encodings ───────────────────────────────────────────────────
def _b_symmetric(E):
    """Encodings that cannot tell the older partner from the younger.

    We do not know which partner is which sex, and the doctrine's claim is about the couple, so a
    symmetric encoding is closer to what is actually being asserted than either ordering.

    Two identities make this cheap and are worth writing down, because they say what "symmetric"
    means here:
      SUM. a_old + a_yng = 2*W(t) - N_old(c) - N_yng(c) = 2*(W(t) - midpoint(c)) modulo 360. The sum
      of the two partners' transit angles IS the wedding body's angle to the MIDPOINT COMPOSITE
      position of that natal body, doubled — i.e. the transit read on the 180-degree dial. Emitted
      as cos/sin of the sum.
      ABSOLUTE DIFFERENCE. a_old - a_yng = N_yng(c) - N_old(c): the transiting body cancels
      completely, so the "absolute difference of the two transit angles" is nothing more than the
      partners' own natal separation for that body, the same for every transiting body. It is
      therefore emitted ONCE per body (18 of them, as cos and |sin|, which is the order-blind form)
      rather than 324 times.
      MIN and MAX ORB across the two partners, at 6 degrees, over the classical 7x7 grid: the looser
      and the tighter of the couple's two contacts.
    """
    W = E.LON[WED]
    c7 = [E.IDX[b] for b in C7N]
    dO = _grid(W[c7], E.LON[OLD][c7])
    dY = _grid(W[c7], E.LON[YNG][c7])
    s = np.deg2rad(_wrap(dO + dY))                     # = 2 * (transit angle to the composite)
    rO, rY = _resid(dO, PTOL), _resid(dY, PTOL)
    kO, kY = _k(rO, 6.0), _k(rY, 6.0)
    nat = _wrap(E.LON[YNG] - E.LON[OLD])               # per body, all 18: the partners' own gap
    parts = [_fl(np.cos(s)), _fl(np.sin(s)),
             _fl(np.minimum(kO, kY)), _fl(np.maximum(kO, kY)),
             _fl(np.cos(np.deg2rad(nat))), _fl(np.abs(np.sin(np.deg2rad(nat))))]
    return _fin(_pack(parts, E.n))


# ── block 8: transits to the relationship charts ───────────────────────────────────────────────
def _b_relationship(E):
    """The wedding sky onto the two RELATIONSHIP charts: midpoint composite and Davison.

    The composite body is the near midpoint of the two natal positions (Townley 1973; Hand 1975);
    the Davison body is a real position at the instant midway in time between the births (slot 5).
    Modern practice disputes which is the real relationship chart, so both are contacted separately
    and their disagreement is emitted as well — where the two charts differ by a quadrant, a transit
    to one is not a transit to the other, and that is a fact about the couple.

    Neither chart has an Ascendant here: the composite angles and the Davison angles both need birth
    places and times. Only the body-to-body layer is claimed.
    """
    W = E.LON[WED]
    m10 = [E.IDX[b] for b in M10N]
    c7 = [E.IDX[b] for b in C7N]
    comp = _mid(E.LON[OLD], E.LON[YNG])
    dav = E.LON[DAV]
    tr = [E.IDX[b] for b in ("Venus", "Jupiter", "Saturn")]
    sig = [E.IDX[b] for b in SIGN4]
    parts = []
    for tgt in (comp, dav):
        parts.append(_fl(_k(_resid(_grid(W[c7], tgt[m10]), PTOL), 6.0)))
        # the marriage significators in circular form, where the angle itself may matter
        d = np.deg2rad(_grid(W[tr], tgt[sig]))
        parts += [_fl(np.cos(d)), _fl(np.sin(d))]
    dis = np.abs(_wrap(comp - dav))                    # composite versus Davison, body by body
    parts += [dis.T, dis.mean(axis=0), dis.max(axis=0), (dis > 90.0).sum(axis=0).astype(np.float64)]
    return _fin(_pack(parts, E.n))


# ── block 9: transits to the progressed charts ─────────────────────────────────────────────────
def _b_to_progressed(E):
    """The wedding sky onto each partner's SECONDARY PROGRESSED chart (slots 3 and 4).

    A transit to a progressed place is standard modern predictive practice and is a different
    statement from a transit to the radix: the progressed chart is where the person has got to, the
    radix is what they were promised. Both partners are emitted separately here (the symmetric view
    of the same material is block 7's business).

    Application is computed against the RELATIVE rate, because a progressed place moves too: the
    transiting body at SPD degrees per day against a progressed body at SPD degrees per year, which
    is SPD/YR degrees per day under the day-for-a-year key.
    """
    W, WS = E.LON[WED], E.SPD[WED]
    c7 = [E.IDX[b] for b in C7N]
    m10 = [E.IDX[b] for b in M10N]
    mar = [E.IDX[b] for b in ("Sun", "Venus", "Jupiter", "Saturn", "Uranus")]
    sig = [E.IDX[b] for b in ("Sun", "Moon", "Venus")]
    parts = []
    for ps in (PO, PY):
        P, PS = E.LON[ps], E.SPD[ps]
        parts.append(_fl(_k(_resid(_grid(W[c7], P[m10]), PTOL), 6.0)))
        d = _grid(W[mar], P[sig])
        r = _resid(d, PTOL)
        rate = WS[mar][:, None, :] - PS[sig][None, :, :] / YR
        parts.append(_fl(_apply_sign(r, rate) * _k(r, 3.0)))
    return _fin(_pack(parts, E.n))


# ── block 10: progressed against progressed ────────────────────────────────────────────────────
def _b_prog_prog(E):
    """PROGRESSED-TO-PROGRESSED contacts between the two partners, at the wedding.

    Both charts have been advanced by the day-for-a-year key to the same date, so this is the pair's
    synastry as it stood on the wedding day rather than at birth — the one relationship measurement
    in this module that involves no transiting body at all. The 7x7 grid is ordered (older's
    progressed body against younger's progressed body), so both directions are already present.

    Progression orbs are tight in practice, so the kernel is at 3 degrees, and the applying sign
    uses the true relative rate: both sides move at their own progressed speed, in degrees per year.
    """
    c7 = [E.IDX[b] for b in C7N]
    A, AS = E.LON[PO][c7], E.SPD[PO][c7]
    B, BS = E.LON[PY][c7], E.SPD[PY][c7]
    d = _grid(A, B)
    r = _resid(d, PTOL)
    rate = AS[:, None, :] - BS[None, :, :]
    parts = [_fl(_k(r, 3.0)), _fl(_apply_sign(r, rate) * _k(r, 3.0))]
    # the pairs the technique actually names, in circular form
    for a, b in (("Sun", "Sun"), ("Moon", "Moon"), ("Sun", "Moon"), ("Moon", "Sun"),
                 ("Venus", "Mars"), ("Mars", "Venus")):
        x = np.deg2rad(_wrap(E.LON[PO][E.IDX[a]] - E.LON[PY][E.IDX[b]]))
        parts += [np.cos(x), np.sin(x)]
    return _fin(_pack(parts, E.n))


# ── block 11: solar arc directions ─────────────────────────────────────────────────────────────
def _b_solar_arc(E):
    """SOLAR ARC DIRECTED natal charts at the wedding, contacted two ways.

    The arc is the progressed Sun's distance from the natal Sun — about a degree a year, exact here
    because both ends are ephemeris positions (slot 3 or 4 against slot 0 or 1) rather than a
    nominal 1.0 degree key. The whole radix is advanced by that one arc (Witte; Tyl, "Solar Arcs",
    2001), which leaves every intra-chart angle unchanged, so the only thing a directed chart can
    say is what it now CONTACTS.

    Two contacts, both classical:
      the wedding sky onto the directed chart — the election meeting the direction;
      the PARTNER's natal sky onto the directed chart — my directions arriving at your radix, which
      is how the technique is read in a marriage question, and it is asymmetric, so both orderings
      are emitted.
    The two arcs and their difference are emitted as well (three columns): a solar arc is essentially
    the age in years, which is a legitimate covariate of the wedding and is stated openly here rather
    than smuggled in inside a kernel.
    """
    c7 = [E.IDX[b] for b in C7N]
    su = E.IDX["Sun"]
    W = E.LON[WED]
    arcO = _wrap(E.LON[PO][su] - E.LON[OLD][su])
    arcY = _wrap(E.LON[PY][su] - E.LON[YNG][su])
    dirO = np.mod(E.LON[OLD][c7] + arcO[None, :], 360.0)
    dirY = np.mod(E.LON[YNG][c7] + arcY[None, :], 360.0)
    parts = []
    for dr in (dirO, dirY):                                  # the election onto the directed chart
        parts.append(_fl(_k(_resid(_grid(W[c7], dr), PTOL), 6.0)))
    for nat, dr in ((E.LON[YNG][c7], dirO), (E.LON[OLD][c7], dirY)):
        parts.append(_fl(_k(_resid(_grid(nat, dr), PTOL), 3.0)))
    parts += [arcO, arcY, np.abs(_wrap(arcO - arcY))]
    return _fin(_pack(parts, E.n))


# ── block 12: returns and the life-stage cycles ────────────────────────────────────────────────
def _b_returns(E):
    """Where the wedding sat in each partner's SOLAR, LUNAR, SATURN, JUPITER and PROGRESSED-LUNAR
    cycles — the four life-stage markers modern practice names, plus the two returns.

    A return is not an aspect but a phase, so each is emitted as the signed distance in degrees, the
    equivalent distance in days from that body's own mean motion, the circular pair, and a kernel at
    exactitude. The Saturn and Jupiter cycles additionally carry the number of COMPLETED cycles at
    the wedding (age divided by the sidereal period), because a first Saturn return and a second are
    not the same event however identical the angle.

    Noon proxies, stated: the lunar return is uncertain twice over (natal Moon +-6 degrees, wedding
    Moon +-6 degrees), so its "days from return" column is worth about +-1 day out of 27. The solar
    return is good to a fraction of a day. The progressed lunation phase (Rudhyar, "The Lunation
    Cycle", 1967) is computed from the progressed slots and inherits only the natal noon error.
    Order-blind summaries (min and max across the two partners) close the block.
    """
    su, mo, ju, sa = E.IDX["Sun"], E.IDX["Moon"], E.IDX["Jupiter"], E.IDX["Saturn"]
    W = E.LON[WED]
    parts, keep = [], []
    for nslot, pslot in ((OLD, PO), (YNG, PY)):
        N, P = E.LON[nslot], E.LON[pslot]
        age = (E.JD[WED] - E.JD[nslot]) / YR
        sr = _wrap(W[su] - N[su])                            # solar return phase
        lr = _wrap(W[mo] - N[mo])                            # lunar return phase
        st = _wrap(W[sa] - N[sa])                            # Saturn cycle position
        jp = _wrap(W[ju] - N[ju])                            # Jupiter cycle position
        pl = _wrap(P[mo] - P[su])                            # progressed lunation phase
        pm = _wrap(P[mo] - N[mo])                            # progressed Moon's own return
        for x, w, per in ((sr, 6.0, SUN_DEG_PER_DAY), (lr, 10.0, MOON_DEG_PER_DAY)):
            parts += [x / per, np.cos(np.deg2rad(x)), np.sin(np.deg2rad(x)), _k(x, w)]
        for x, cyc in ((st, 29.457), (jp, 11.862)):
            parts += [np.cos(np.deg2rad(x)), np.sin(np.deg2rad(x)), _k(x, 6.0),
                      _k(_resid(x, HARD), 6.0), np.floor(age / cyc), np.mod(age / cyc, 1.0)]
        parts += [np.cos(np.deg2rad(pl)), np.sin(np.deg2rad(pl)), _k(pl, 15.0), _k(_wrap(pl - 180.0), 15.0),
                  np.cos(np.deg2rad(pm)), np.sin(np.deg2rad(pm)), _k(pm, 15.0)]
        keep.append((np.abs(sr), np.abs(lr), np.abs(st), np.abs(jp)))
    for a, b in zip(*keep):
        parts += [np.minimum(a, b), np.maximum(a, b)]
    return _fin(_pack(parts, E.n))


# ── block 13: the marriage-timing shortlist ────────────────────────────────────────────────────
# (transiting body, natal body, angles read for it, orb) — Hand "Planets in Transit" (1976);
# Brady "Predictive Astrology" (1992); Teal "Predicting Events with Astrology" (1999).
SHORTLIST = (
    ("Jupiter", "Sun", (0.0, 60.0, 120.0), 3.0),      # the benefic on the life-giver: the classic
    ("Jupiter", "Moon", (0.0, 60.0, 120.0), 3.0),
    ("Jupiter", "Venus", (0.0, 60.0, 120.0), 3.0),
    ("Jupiter", "Jupiter", (0.0,), 3.0),              # the Jupiter return, every 11.86 years
    ("Saturn", "Sun", (0.0, 90.0, 180.0), 3.0),       # commitment, and its weight
    ("Saturn", "Moon", (0.0, 90.0, 180.0), 3.0),
    ("Saturn", "Venus", (0.0, 90.0, 180.0), 3.0),
    ("Saturn", "Saturn", (0.0, 90.0, 180.0), 3.0),    # the Saturn return and its quarters (Lewi)
    ("Uranus", "Venus", (0.0, 90.0, 180.0), 2.0),     # the sudden turn in the affections
    ("Uranus", "Sun", (0.0, 90.0, 180.0), 2.0),
    ("Neptune", "Venus", (0.0, 90.0, 180.0), 2.0),    # idealisation
    ("Pluto", "Venus", (0.0, 90.0, 180.0), 2.0),      # compulsion
    ("Jupiter", "Juno", (0.0, 90.0, 120.0, 180.0), 3.0),   # Juno: the marriage bond itself
    ("Saturn", "Juno", (0.0, 90.0, 120.0, 180.0), 3.0),
    ("TrueNode", "Sun", (0.0, 180.0), 3.0),           # the nodal axis on the lights
    ("TrueNode", "Moon", (0.0, 180.0), 3.0),
    ("TrueNode", "Venus", (0.0, 180.0), 3.0),
    ("Sun", "Venus", (0.0,), 3.0),                    # the fast pair, for the day itself
    ("Venus", "Sun", (0.0,), 3.0),
)


def _b_shortlist(E):
    """The nineteen contacts the marriage-timing literature actually names, and nothing else.

    A deliberately tiny block: one column per named rule per partner, signed by application, plus a
    per-partner sum, the couple's total and its order-blind min and max. If the doctrine is right
    that these particular contacts time a marriage, a block this small should hold its own against
    the thousand-column grids, and that comparison is the reason it exists.
    """
    W, WS = E.LON[WED], E.SPD[WED]
    parts, tot = [], []
    for nat in (E.LON[OLD], E.LON[YNG]):
        cols = []
        for tb, nb, angles, orb in SHORTLIST:
            t, c = E.IDX[tb], E.IDX[nb]
            d = _wrap(W[t] - nat[c])
            r = _resid(d, angles)
            cols.append(_apply_sign(r, WS[t]) * _k(r, orb))
        M = np.stack(cols, axis=1)
        parts.append(M)
        s = np.abs(M).sum(axis=1)
        parts.append(s)
        tot.append(s)
    parts += [tot[0] + tot[1], np.minimum(tot[0], tot[1]), np.maximum(tot[0], tot[1])]
    return _fin(_pack(parts, E.n))


# ── block 14: testimony counts ─────────────────────────────────────────────────────────────────
def _b_tallies(E):
    """The transit picture as COUNTS — the form every pre-modern tradition actually judged in.

    Valens and Bonatti do not read a contact in isolation; they count testimonies. Per partner: the
    total 6-degree kernel weight each transiting body is delivering (18 columns), the total each
    natal body is receiving (18), applying versus separating weight, hard versus soft weight, the
    benefic pair (Venus, Jupiter) and the malefic pair (Mars, Saturn) landing on the marriage
    significators, and the weight arriving from retrograde bodies. Then the couple-level sums and
    absolute differences, which are order-blind.
    """
    W, WS = E.LON[WED], E.SPD[WED]
    sig = [E.IDX[b] for b in SIGN4]
    ben = [E.IDX[b] for b in ("Venus", "Jupiter")]
    mal = [E.IDX[b] for b in ("Mars", "Saturn")]
    parts, summ = [], []
    for nat in (E.LON[OLD], E.LON[YNG]):
        d = _grid(W, nat)
        r = _resid(d, PTOL)
        K = _k(r, 6.0)
        ap = _apply_sign(r, np.broadcast_to(WS[:, None, :], r.shape))
        KH = _k(_resid(d, HARD), 6.0)
        KS = _k(_resid(d, SOFT), 6.0)
        retro = (WS < 0.0).astype(np.float64)
        per_tr = K.sum(axis=1).T                                   # (n, 18) what each transit gives
        per_na = K.sum(axis=0).T                                   # (n, 18) what each place receives
        appl = (K * (ap > 0)).sum(axis=(0, 1))
        sepa = (K * (ap < 0)).sum(axis=(0, 1))
        hard = KH.sum(axis=(0, 1))
        soft = KS.sum(axis=(0, 1))
        benk = K[np.ix_(ben, sig)].sum(axis=(0, 1))
        malk = K[np.ix_(mal, sig)].sum(axis=(0, 1))
        retk = (K * retro[:, None, :]).sum(axis=(0, 1))
        stat = np.stack([appl, sepa, appl - sepa, hard, soft, hard - soft, benk, malk,
                         benk - malk, retk, K.sum(axis=(0, 1))], axis=1)
        parts += [per_tr, per_na, stat]
        summ.append(stat)
    parts += [summ[0] + summ[1], np.abs(summ[0] - summ[1])]
    return _fin(_pack(parts, E.n))


# ── the module's one public function ───────────────────────────────────────────────────────────
def build(E):
    """name -> (E.n, k) float64, every value finite. Fourteen blocks, all wedding-anchored."""
    return {
        "wt: wedding-to-natal 18x18 circular (both)": _b_circular(E),
        "wt: Ptolemaic orb sweep 18x18, 2.5-6-10deg": _b_orbsweep(E),
        "wt: applying vs separating signed 18x18": _b_applying(E),
        "wt: minor & harmonic angles 18x18": _b_minor_wide(E),
        "wt: classical 7x7 Ptolemaic angles 6deg": _b_classical(E),
        "wt: classical 7x7 orb sweep + families + application": _b_classical_detail(E),
        "wt: order-blind symmetric transit encodings": _b_symmetric(E),
        "wt: transits to composite & Davison": _b_relationship(E),
        "wt: transits to the progressed charts": _b_to_progressed(E),
        "wt: progressed-to-progressed at the wedding": _b_prog_prog(E),
        "wt: solar arc directed, both contacts": _b_solar_arc(E),
        "wt: returns & life-stage cycles": _b_returns(E),
        "wt: the marriage-timing shortlist (compact)": _b_shortlist(E),
        "wt: transit testimony counts": _b_tallies(E),
    }


if __name__ == "__main__":
    import time
    from core import load
    from evalx import quick

    E = load()
    t0 = time.time()
    B = build(E)
    dt = time.time() - t0
    print(f"{TRADITION}\n{len(B)} blocks built in {dt:.1f}s over {E.n} couples\n")

    # ── a visible check that the applying/separating verdict is the real thing, not a guess ──────
    # Take transiting Saturn to the older partner's natal Sun. The residual to the nearest
    # Ptolemaic angle must be shrinking when the sign says applying: step the transit forward by a
    # small dt using Saturn's own speed and confirm |r| went down for every applying couple.
    W, WS = E.LON[2], E.SPD[2]
    sa, su = E.IDX["Saturn"], E.IDX["Sun"]
    d0 = _wrap(W[sa] - E.LON[0][su])
    r0 = _resid(d0, PTOL)
    s0 = _apply_sign(r0, WS[sa])
    r1 = _resid(_wrap(d0 + WS[sa] * 0.5), PTOL)
    closing = np.abs(r1) < np.abs(r0)
    agree = (closing == (s0 > 0))
    print(f"applying check: transiting Saturn to natal Sun, {agree.mean()*100:.2f}% of couples agree "
          f"with a half-day forward step ({int((~agree).sum())} disagreements, which can only occur "
          f"within half a day's motion of exactitude)")
    assert agree.mean() > 0.99, "the applying/separating sign does not match forward motion"

    # the symmetric identity claimed in block 7: a_old + a_yng == 2*(transit angle to the composite)
    comp = _mid(E.LON[0], E.LON[1])
    lhs = _wrap(_wrap(W[sa] - E.LON[0][su]) + _wrap(W[sa] - E.LON[1][su]))
    rhs = _wrap(2.0 * _wrap(W[sa] - comp[su]))
    print(f"symmetry identity: max |sum of transit angles - 2x angle to composite| = "
          f"{np.abs(_wrap(lhs - rhs)).max():.2e} deg")
    assert np.abs(_wrap(lhs - rhs)).max() < 1e-8, "the composite midpoint identity is broken"

    # the solar arc must be the progressed Sun's own travel, about a degree a year of age
    arc = _wrap(E.LON[3][su] - E.LON[0][su])
    age = (E.JD[2] - E.JD[0]) / 365.2425
    print(f"solar arc check: arc/age in degrees per year, min {np.min(arc/age):.3f} "
          f"max {np.max(arc/age):.3f} (must sit near 1.0)")
    assert 0.9 < np.min(arc / age) and np.max(arc / age) < 1.05, "solar arc is not the Sun's travel"

    names = list(B)
    assert len(set(names)) == len(names), "duplicate block name"
    tot = 0
    for name, X in B.items():
        assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
        assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
        assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
        assert X.shape[1] >= 1, f"{name}: no columns"
        assert np.isfinite(X).all(), f"{name}: non-finite values"
        assert X.std(axis=0).max() > 1e-12, f"{name}: entirely constant"
        tot += X.shape[1]
    print()
    for name, X in B.items():
        a, u = quick(E, X)
        print(f"  {name:<54} {X.shape[1]:>5} cols   acc {100*a:5.2f}%   AUC {u:.4f}")
    print(f"\n{tot} columns across {len(B)} blocks")
    print("OK")
