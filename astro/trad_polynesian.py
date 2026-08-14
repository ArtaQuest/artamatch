"""
trad_polynesian.py — Māori maramataka and Hawaiian mahina: the named nights of the lunar month.

WHY THIS TRADITION IS HERE AT ALL, AND WHAT IT HONESTLY ADDS

Both systems are living and actively practised. The maramataka has been through a substantial revival and is
published as fishing and planting calendars across Aotearoa; the Hawaiian mahina is taught, printed and used the
same way. Neither was represented in this stack, and coverage of living traditions is a stated goal — so the
gap was worth closing on its own terms.

But the honest accounting matters more than the addition. The QUANTITY these calendars are built from — the
Moon's elongation from the Sun, which fixes the night of the lunar month — is ALREADY computed twice in this
stack: `trad_lunar_calendrical` takes the synodic phase per slot, and `trad_vedic_core` derives tithi from
exactly the same difference divided by 12°. A third module recomputing elongation would add a duplicate, not a
tradition. The Pleiades are likewise already present, with real coordinates, in `trad_aboriginal_australian`.

So this module deliberately does NOT contribute the elongation. What it contributes is the part no other module
expresses — three things:

  1. THE QUALITY CLASSES. Neither calendar treats the lunar month as a smooth cycle. Both sort the nights into
     named classes with opposite reputations, and the map from night to class is sharply non-monotonic: in the
     maramataka Whiro (the new moon) and the Korekore nights are unproductive, while the Tangaroa nights and
     Rākaunui (full) are the best of the month — a night-29 and a night-22 sit at opposite ends of the same
     smooth variable. A model given only sin/cos of the phase cannot represent that; a one-hot of the class can.
  2. THE ANAHULU. The Hawaiian month is three ten-night periods — hoʻonui (waxing), poepoe (full), emi (waning)
     — which is a different partition of the same cycle from the eight-phase or thirty-tithi divisions
     elsewhere, and the ʻOle and Kāloa nights recur within it on their own four-night sub-rhythm.
  3. THE YEAR ANCHOR. Both traditions begin the year from the heliacal rising of the Pleiades — Matariki, or
     Makaliʻi — with Puanga (Rigel) used in place of Matariki in parts of Aotearoa where the Pleiades sit low.
     That anchors "where in the year" to a STAR rather than to a solstice or an equinox, so the resulting
     month-of-year is offset from every solar calendar in the stack and drifts against them with precession.

THE LIMIT, SAID PLAINLY. A lunar night begins at a local sunset and every instant here is a fixed hour UT with
no birthplace, so a birth in the hours around sunset belongs to the neighbouring night and we cannot tell which.
One night's slip moves the name and can move the class. This is the same irreducible noise the Mesoamerican
module documents for its day counts, and it cannot be reduced with two dates alone.

THE NIGHT LISTS. Both are given in full below and both vary by iwi and by island — a fact the sources state
themselves rather than a defect of this implementation. The maramataka sequence follows the widely published
Te Ao Māori ordering (Whiro through Mutuwhenua); the Hawaiian follows the standard thirty-night list
(Hilo through Muku) as recorded by Malo and Kamakau. Where authorities differ on a single night's reputation the
coarser class is used, since a disputed night should not carry a confident label.
"""
import numpy as np

# ── the thirty nights, Māori ─────────────────────────────────────────────────────────────────────────────────
MARAMATAKA = [
    "Whiro", "Tirea", "Hoata", "Ōuenuku", "Okoro", "Tamatea-āio", "Tamatea-kai-ariki", "Huna",
    "Ari-roa", "Maure", "Māwharu", "Ōhua", "Atua-whakahaehae", "Turu", "Rākaunui",
    "Rākau-matohi", "Takirau", "Oike", "Korekore-te-whiwhia", "Korekore-te-rawea",
    "Korekore-piri-ki-Tangaroa", "Tangaroa-ā-mua", "Tangaroa-ā-roto", "Tangaroa-kiokio",
    "Ōtāne", "Ōrongonui", "Ōmutu", "Mutuwhenua", "Whiro-whanaunga", "Ōhoata",
]
# Five classes, from the reputations these nights carry in the published calendars. The point of this block is
# that the map is NOT monotonic in the phase: 0 (new) and 21-23 (last quarter) are as far apart on the smooth
# cycle as they could be, and land in the worst and best classes respectively.
M_CLASS = {
    "dark": [0, 27, 28],                          # Whiro and Mutuwhenua: the moonless nights, unproductive
    "korekore": [18, 19, 20],                     # the Korekore nights: low energy, poor for planting
    "tangaroa": [21, 22, 23],                     # the Tangaroa nights: the most productive of the month
    "full": [13, 14, 15],                         # Turu, Rākaunui, Rākau-matohi: strong, good for fishing
    "ordinary": None,                             # everything else
}

# ── the thirty nights, Hawaiian ──────────────────────────────────────────────────────────────────────────────
MAHINA = [
    "Hilo", "Hoaka", "Kūkahi", "Kūlua", "Kūkolu", "Kūpau", "ʻOlekūkahi", "ʻOlekūlua", "ʻOlekūkolu", "ʻOlepau",
    "Huna", "Mōhalu", "Hua", "Akua", "Hoku", "Māhealani", "Kulu", "Lāʻaukūkahi", "Lāʻaukūlua", "Lāʻaupau",
    "ʻOlekūkahi-2", "ʻOlekūlua-2", "ʻOlepau-2", "Kāloakūkahi", "Kāloakūlua", "Kāloapau", "Kāne", "Lono",
    "Mauli", "Muku",
]
ANAHULU = ["hoʻonui", "poepoe", "emi"]            # waxing / full / waning, ten nights each
OLE = [6, 7, 8, 9, 20, 21, 22]                    # the ʻOle nights: rough seas, poor for fishing
KALOA = [23, 24, 25]                              # the Kāloa nights: good for planting

# The Pleiades and Rigel in ecliptic longitude, and how they move.
#
# Alcyone sits near 59.7 deg of tropical ecliptic longitude at J2000 and Rigel near 76.4. Both are fixed stars,
# so what changes is the reference frame: general precession in longitude carries them forward at about
# 1.3968 deg per century, which over the 1800-1950 window this model is fitted on is roughly two degrees. Two
# degrees is a real shift for a heliacal rising — the Sun covers it in two days — so it is applied rather than
# ignored. This is a longitude only: it does not attempt a rising, which needs a latitude and a horizon.
ALCYONE_J2000 = 59.73
RIGEL_J2000 = 76.42
PRECESSION_DEG_PER_DAY = 1.3968 / 36524.22
J2000 = 2451545.0


def _oh(idx, k):
    """One-hot, with out-of-range folded rather than dropped."""
    idx = np.asarray(idx, dtype=np.int64) % k
    out = np.zeros((len(idx), k), dtype=np.float64)
    out[np.arange(len(idx)), idx] = 1.0
    return out


def _cyc(x, period, h=1):
    """Sin/cos pairs at h harmonics, so a cyclic quantity has no artificial seam."""
    x = np.asarray(x, dtype=np.float64) * (2.0 * np.pi / period)
    return np.concatenate([np.stack([np.sin(k * x), np.cos(k * x)], axis=-1) for k in range(1, h + 1)], axis=-1)


def _cdist(a, b, k):
    """Shortest distance between two positions on a circle of k steps."""
    d = np.mod(np.asarray(a, np.float64) - np.asarray(b, np.float64), k)
    return np.minimum(d, k - d)


def _elong(E, slot):
    """Moon minus Sun, 0..360. Recomputed here only to derive the NIGHT; the phase itself is another module's.

    core lays these arrays out as [SLOT, BODY, ROW] — `E.LON[slot, body]` is a vector over couples. The first
    version of this module wrote `E.LON[:, slot, E.IDX["Moon"]]`, which indexes the slot axis with a colon, the
    body axis with a slot and the row axis with a body index. It did not crash and it did not warn, because the
    probe had six couples and there are six slots, so every axis was length 6 and the transposition was invisible.
    Four unrelated couples came out on the same lunar night; that coincidence is the only thing that gave it away.
    """
    return np.mod(E.LON[slot, E.IDX["Moon"]] - E.LON[slot, E.IDX["Sun"]], 360.0)


def nights(E, slot):
    """The night of the lunar month, 0..29, from the elongation. Night 0 begins at conjunction."""
    return np.floor(_elong(E, slot) / 12.0).astype(np.int64) % 30


def _class_index(night):
    """Map a night onto its maramataka class. `ordinary` is the fallback, deliberately last."""
    order = ["dark", "korekore", "tangaroa", "full"]
    out = np.full(len(night), len(order), dtype=np.int64)          # index 4 == ordinary
    for i, name in enumerate(order):
        for n in M_CLASS[name]:
            out[night == n] = i
    return out


def _star_lon(jd, base):
    return np.mod(base + PRECESSION_DEG_PER_DAY * (np.asarray(jd, np.float64) - J2000), 360.0)


def build(E):
    iO, iY, iDV = 0, 1, 5
    SLOTS = (iO, iY, iDV)
    B = {}

    n = {s: nights(E, s) for s in SLOTS}
    cls = {s: _class_index(n[s]) for s in SLOTS}

    # 1 ── the classes, and the pair relation between them ───────────────────────────────────────
    # This is the block that is not a duplicate of anything: a one-hot of a non-monotonic map, plus whether the
    # two people were born into the same class and into which pair of classes.
    c = [_oh(cls[s], 5) for s in SLOTS]
    c.append(np.stack([(cls[iO] == cls[iY]).astype(np.float64),
                       (cls[iO] == 2).astype(np.float64) * (cls[iY] == 2),      # both Tangaroa
                       (cls[iO] == 0).astype(np.float64) * (cls[iY] == 0),      # both dark
                       ((cls[iO] == 0) ^ (cls[iY] == 0)).astype(np.float64),    # one dark, one not
                       ], axis=-1))
    c.append(_oh(cls[iO] * 5 + cls[iY], 25))                                    # the ordered class pair
    B["pol: maramataka night classes and their pairing"] = np.concatenate(c, axis=1)

    # 2 ── the anahulu, the ʻOle and Kāloa sub-rhythms, and the night distance ───────────────────
    c = []
    for s in SLOTS:
        ana = (n[s] // 10) % 3
        c += [_oh(ana, 3),
              np.stack([np.isin(n[s], OLE).astype(np.float64),
                        np.isin(n[s], KALOA).astype(np.float64),
                        (n[s] % 10).astype(np.float64) / 9.0], axis=-1),
              _cyc(n[s] % 10, 10, 2)]
    c.append(np.stack([_cdist(n[iO], n[iY], 30).astype(np.float64),
                       ((n[iO] // 10) == (n[iY] // 10)).astype(np.float64),
                       (np.isin(n[iO], OLE) & np.isin(n[iY], OLE)).astype(np.float64),
                       (np.isin(n[iO], KALOA) & np.isin(n[iY], KALOA)).astype(np.float64)], axis=-1))
    c.append(_cyc(n[iO] - n[iY], 30, 3))
    B["pol: mahina anahulu and the Ole/Kaloa nights"] = np.concatenate(c, axis=1)

    # 3 ── the year anchored on Matariki and Puanga rather than on a solstice ────────────────────
    c = []
    for s in SLOTS:
        sun = E.LON[s, E.IDX["Sun"]]
        for base in (ALCYONE_J2000, RIGEL_J2000):
            sep = np.mod(sun - _star_lon(E.JD[s], base), 360.0)
            c += [_cyc(sep, 360.0, 3),
                  np.stack([_cdist(sep, 0.0, 360.0) / 180.0,
                            # A heliacal rising needs the Sun far enough from the star to let it be seen; the
                            # conventional threshold is around 10-12 degrees of elongation.
                            (np.minimum(sep, 360.0 - sep) > 12.0).astype(np.float64)], axis=-1)]
    sepO = np.mod(E.LON[iO, E.IDX["Sun"]] - _star_lon(E.JD[iO], ALCYONE_J2000), 360.0)
    sepY = np.mod(E.LON[iY, E.IDX["Sun"]] - _star_lon(E.JD[iY], ALCYONE_J2000), 360.0)
    c.append(_cyc(sepO - sepY, 360.0, 3))
    c.append((_cdist(sepO, sepY, 360.0) / 180.0)[:, None])
    B["pol: Matariki and Puanga, the star-anchored year"] = np.concatenate(c, axis=1)

    return {k: np.ascontiguousarray(v, np.float64) for k, v in B.items()}


def _selftest():
    class E:
        pass

    # core's REAL layout: [SLOT, BODY, ROW] for LON and [SLOT, ROW] for JD. The row count is deliberately NOT 6:
    # with six couples and six slots every axis is the same length and a transposed index cannot be detected,
    # which is exactly how the first version of this module shipped nonsense past its own self-test.
    NSLOT = 6
    n_rows = 11
    assert n_rows != NSLOT, "the row count must differ from the slot count or a transposition hides"
    rng = np.random.default_rng(11)
    E.IDX = {"Sun": 0, "Moon": 1}
    E.JD = np.stack([np.linspace(2380000.0, 2430000.0, n_rows)] * NSLOT, axis=0)
    lon = np.zeros((NSLOT, 2, n_rows))
    lon[:, 0, :] = rng.uniform(0, 360, (NSLOT, n_rows))
    lon[:, 1, :] = np.mod(lon[:, 0, :] + np.linspace(0, 348, n_rows)[None, :], 360.0)
    E.LON = lon
    E.n = n_rows
    assert E.JD.shape == (NSLOT, n_rows) and E.LON.shape == (NSLOT, 2, n_rows)

    assert len(MARAMATAKA) == 30 and len(MAHINA) == 30, (len(MARAMATAKA), len(MAHINA))
    assert len(set(MARAMATAKA)) == 30 and len(set(MAHINA)) == 30, "a night name is duplicated"
    covered = sorted(i for v in M_CLASS.values() if v for i in v)
    assert len(covered) == len(set(covered)), f"a night is in two classes: {covered}"
    assert max(covered) < 30 and min(covered) >= 0

    nn = nights(E, 0)
    assert nn.min() >= 0 and nn.max() <= 29, (nn.min(), nn.max())
    # Night 0 at conjunction, night 15 near opposition: the anchor is the new moon, as both traditions have it.
    E2 = E
    lon2 = lon.copy()
    lon2[:, 1, :] = lon2[:, 0, :]                       # exact conjunction
    E2.LON = lon2
    assert (nights(E2, 0) == 0).all(), nights(E2, 0)
    # 186 deg, not 180: an exact 180 sits precisely on the night-14/15 boundary and floating point drops some
    # rows to 179.999..., so the strict assertion failed on correct arithmetic. Test inside a night, not on its edge.
    lon2[:, 1, :] = np.mod(lon2[:, 0, :] + 186.0, 360.0)
    assert (nights(E2, 0) == 15).all(), nights(E2, 0)
    lon2[:, 1, :] = np.mod(lon2[:, 0, :] + 6.0, 360.0)
    assert (nights(E2, 0) == 0).all(), nights(E2, 0)
    lon2[:, 1, :] = np.mod(lon2[:, 0, :] + 354.0, 360.0)
    assert (nights(E2, 0) == 29).all(), nights(E2, 0)
    E2.LON = lon

    ci = _class_index(np.arange(30))
    assert ci[0] == 0 and ci[27] == 0, "Whiro and Mutuwhenua must be dark"
    assert ci[22] == 2, "Tangaroa-ā-roto must be the productive class"
    assert ci[14] == 3, "Rākaunui must be the full class"
    assert ci[5] == 4, "an unlisted night must fall through to ordinary"
    # The map must be NON-MONOTONIC in the night, which is the entire reason this block exists.
    assert not (np.all(np.diff(ci) >= 0) or np.all(np.diff(ci) <= 0)), "class map is monotonic in the night"

    B = build(E)
    print(f"  {len(B)} blocks")
    for k, v in B.items():
        assert v.shape[0] == n_rows and v.ndim == 2, (k, v.shape)
        assert np.isfinite(v).all(), f"{k} has non-finite values"
        print(f"    {v.shape[1]:>4} cols  {k}")
    # Precession must actually move the star, and by about the right amount over this window.
    # Distinct couples must land on distinct nights: an all-equal column is the signature of a transposed read.
    nO, nY = nights(E, 0), nights(E, 1)
    assert len(set(nO.tolist())) > 1, f"every couple got the same night for slot 0: {nO.tolist()}"
    assert len(set(nY.tolist())) > 1, f"every couple got the same night for slot 1: {nY.tolist()}"

    d = _star_lon(2430000.0, ALCYONE_J2000) - _star_lon(2380000.0, ALCYONE_J2000)
    assert 1.7 < d < 2.2, f"precession over the window came out {d:.3f} deg, expected about 1.9"
    print(f"  Alcyone moves {d:.3f}° of longitude across the fitted window")
    print("  self-test passed")


if __name__ == "__main__":
    _selftest()
