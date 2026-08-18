"""
trad_coherent.py — coherent phasor fields: the whole chart as one interference intensity.

THE FORM, AND WHY IT IS NOT JUST ANOTHER BLOCK

    F(t) = | b + A * SUM_k a_k * exp( i * ( h * theta_k(t) - p_k ) ) |^2

Every other tradition in this project computes a NAMED quantity -- a nakshatra index, a Ptolemaic orb, a
sexagenary pillar -- and asks whether that named thing predicts. This one computes no named thing. It treats each
body's ecliptic longitude theta_k as the phase of a unit phasor, weights it by an amplitude a_k, rotates it by a
field-specific offset p_k, sums the lot coherently, adds a bias b, and takes the squared modulus. The result is an
interference intensity: the field is large where the chosen bodies' phases reinforce and small where they cancel.

WHY THAT FORM AND NOT ANOTHER. Because it CONTAINS the classical aspect as its two-body case and generalises it.
With b = 0, a = (1, 1) and h = 1,

    | exp(i*th1) + exp(i*th2) |^2  =  2 + 2*cos(th1 - th2)

which is exactly a conjunction/opposition term: maximal at th1 = th2, zero at 180 degrees. Set h = 2 and it is
the square/opposition harmonic; h = 3 the trine. So a bank of these fields spans every classical aspect, every
harmonic of one, and -- this is the part no hand-coded block reaches -- every MULTI-body resonance, where three or
four bodies must line up in a particular relative configuration for the field to peak. The offsets p_k are what
make it a family rather than a single statistic: they slide the peak of each body's contribution, so a field can
encode "Venus 40 degrees ahead of Saturn while Mars trines both" without anyone having to name that configuration.

Amplitude and phase are what an astrologer would call the strength and the orb of an influence. Nothing here is
learned by this module: the bank is drawn from a FIXED seed, so the columns are a deterministic function of this
file. That makes it a random-feature basis, which is the honest cheap version -- the fitted version, where a, p
and b are optimised against the label, lives in coherent_fit.py and must be fitted on the training half alone.

WHICH BODIES MAY ENTER A FIELD -- THE ONLY DESIGN DECISION THAT MATTERS HERE

A coherent field over SLOW bodies is an era clock wearing astrology's clothes, and it would score well for
entirely calendrical reasons. Over the 1600-1900 training span a body completes span/period cycles:

    Moon 4011 · Mercury 1246 · Venus 488 · Sun 300 · Mars 160 | Jupiter 25 · Saturn 10 | Uranus 3.6 · Neptune 1.8 · Pluto 1.2

Pluto's longitude is very nearly a linear function of the birth year across the whole training half, so
|b + A*exp(i*theta_Pluto)|^2 is a smooth ~1.2-cycle function of the year -- an excellent century detector that
reads nothing astrological. Uranus and Neptune are the same story. Jupiter and Saturn are borderline.

So the bank is split by speed and the blocks are reported separately:

    FAST      Sun Moon Mercury Venus Mars          era-blind BY CONSTRUCTION -- 160 to 4011 cycles, hopelessly
                                                   aliased against a 300-year trend. This is the honest test.
    CLASSICAL the visible seven (adds Jupiter, Saturn)   partly era-capable
    ALL       all eighteen bodies                        era-capable; expected to score, expected to be era

A FAST field that beats the era rule out of time would be a real result. An ALL field that beats it is the
confound restated, and the pair of numbers side by side is the measurement.

CROSS-PARTNER INTERFERENCE IS FREE, AND IS THE POINT. The sum runs over (slot, body) pairs, so when both
partners' bodies are in the same field the squared modulus expands to

    ... + 2*a_j*a_k*cos( theta_j^older - theta_k^younger - (p_j - p_k) ) + ...

-- every cross-chart pair term at once, with learned-in offsets. That is synastry, generalised: one column
carries the whole cross-aspect grid rather than one named contact.

WHAT IS EMITTED PER FIELD. The intensity |.|^2, and the argument of the sum as cos/sin (a circular pair). The
modulus discards the phase of the resultant, which is itself a meaningful angle -- the "direction" the chart's
bodies collectively point -- so it is kept rather than thrown away.

SHAPE CONTRACT. Width is a function of this file alone (BANK sizes and body-set sizes), never of the batch, and
the RNG is seeded once at import. A batch of any size produces identical columns.
"""
import numpy as np

# ── slots. Only the two birth charts are used. ────────────────────────────────────────────────────────────────
# The `wedding` slot exists in core.py and is NOT touched here: the relationship's own dates COMPUTE the label,
# so a wedding-chart phasor would be leakage, not a feature. `davison` is a pure function of the two birth dates
# and would be legal, but it adds nothing a coherent sum over both charts does not already contain.
iO, iY = 0, 1

# Body indices, matching core.BODIES order. Written out rather than imported so this module self-tests alone.
SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO = range(10)
TRUENODE, MEANNODE, LILITH, CHIRON, CERES, PALLAS, JUNO, VESTA = range(10, 18)

FAST = (SUN, MOON, MERCURY, VENUS, MARS)
CLASSICAL = (SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN)
ALL18 = tuple(range(18))

# Harmonics. 1 = conjunction/opposition scale, 2 = squares, 3 = trines, 4/6/8/12 = the higher harmonic charts
# every harmonic-astrology school reads.
HARMONICS = (1, 2, 3, 4, 6, 8, 12)

# Fields per block. Kept modest on purpose: the stack screens blocks, and a block wider than its neighbours wins
# selection by having more chances to be lucky rather than by carrying more signal.
BANK = 64

# How many (slot, body) terms enter one field. A field with 2-5 terms is a recognisable configuration; a field
# summing all 36 terms is a random walk whose modulus carries almost nothing.
TERMS = (2, 3, 4, 5)

SEED = 20260818


def _draw(bodies, rng, cross_only=False):
    """One bank of fields over a body set. Returns the parameter tuple, all fixed at import."""
    slots, bods, amps, phas, harm, bias = [], [], [], [], [], []
    pool = [(s, b) for s in (iO, iY) for b in bodies]
    for _ in range(BANK):
        m = int(rng.choice(TERMS))
        if cross_only:
            # Force at least one term from each partner, so every field is a genuine cross-chart interference
            # and none of them can degenerate into a one-sided chart statistic.
            m = max(m, 2)
            ko = rng.choice([p for p in pool if p[0] == iO], size=max(1, m // 2), replace=False)
            ky = rng.choice([p for p in pool if p[0] == iY], size=m - len(ko), replace=False)
            pick = [tuple(x) for x in list(ko) + list(ky)]
        else:
            idx = rng.choice(len(pool), size=m, replace=False)
            pick = [pool[i] for i in idx]
        s = np.zeros(len(pool), dtype=np.int64)          # unused, kept for shape symmetry
        slots.append([p[0] for p in pick])
        bods.append([p[1] for p in pick])
        # Amplitudes on the simplex-ish: a strong term and weaker companions, which is how an astrologer
        # weights a configuration (one ruling contact, modified by others).
        a = rng.dirichlet(np.full(m, 1.5)) * m
        amps.append(a)
        phas.append(rng.uniform(0.0, 2.0 * np.pi, size=m))
        harm.append(int(rng.choice(HARMONICS)))
        # A complex bias. |b| relative to sqrt(m) decides how deep the interference nulls go: b = 0 gives a
        # field that vanishes on perfect cancellation, a large |b| gives a shallow ripple on a plateau.
        r = float(rng.choice([0.0, 0.5, 1.0, 2.0])) * np.sqrt(m)
        bias.append(r * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi)))
    return slots, bods, amps, phas, harm, np.array(bias)


_RNG = np.random.default_rng(SEED)
_BANKS = {
    "fast": _draw(FAST, _RNG),
    "classical": _draw(CLASSICAL, _RNG),
    "all18": _draw(ALL18, _RNG),
    "cross_fast": _draw(FAST, _RNG, cross_only=True),
}


def _evaluate(LON, bank):
    """Intensity and resultant angle for one bank. LON is (NSLOT, NB, n) degrees; returns (n, 3*BANK)."""
    slots, bods, amps, phas, harm, bias = bank
    n = LON.shape[2]
    out = np.empty((n, 3 * BANK), dtype=np.float64)
    rad = np.pi / 180.0
    for f in range(BANK):
        h = harm[f]
        S = np.zeros(n, dtype=np.complex128)
        for s, b, a, p in zip(slots[f], bods[f], amps[f], phas[f]):
            S += a * np.exp(1j * (h * LON[s, b] * rad - p))
        Z = bias[f] + S
        out[:, 3 * f] = (Z.real ** 2 + Z.imag ** 2)          # |b + sum|^2 -- the field
        m = np.abs(Z)
        safe = np.where(m > 1e-12, m, 1.0)
        out[:, 3 * f + 1] = Z.real / safe                     # cos(arg Z)
        out[:, 3 * f + 2] = Z.imag / safe                     # sin(arg Z)
    return out


def build(E):
    LON = np.asarray(E.LON, dtype=np.float64)
    return {
        "coh: FAST bodies (Sun Moon Mercury Venus Mars) — era-blind by construction":
            np.ascontiguousarray(_evaluate(LON, _BANKS["fast"]), dtype=np.float64),
        "coh: classical seven — adds Jupiter and Saturn, partly era-capable":
            np.ascontiguousarray(_evaluate(LON, _BANKS["classical"]), dtype=np.float64),
        "coh: all eighteen bodies — era-capable, read beside the era rule":
            np.ascontiguousarray(_evaluate(LON, _BANKS["all18"]), dtype=np.float64),
        "coh: cross-partner interference only, FAST bodies — synastry generalised":
            np.ascontiguousarray(_evaluate(LON, _BANKS["cross_fast"]), dtype=np.float64),
    }


if __name__ == "__main__":
    # ── 1. the two-body identity the whole design rests on ────────────────────────────────────────────────
    rng = np.random.default_rng(1)
    th1, th2 = rng.uniform(0, 360, 500), rng.uniform(0, 360, 500)
    rad = np.pi / 180.0
    lhs = np.abs(np.exp(1j * th1 * rad) + np.exp(1j * th2 * rad)) ** 2
    rhs = 2 + 2 * np.cos((th1 - th2) * rad)
    assert np.allclose(lhs, rhs), np.abs(lhs - rhs).max()
    print(f"  |e^ith1 + e^ith2|^2 == 2 + 2cos(th1-th2) to {np.abs(lhs - rhs).max():.2e} — the classical aspect")

    # h = 2 must put its peak at 180 degrees as well as 0 — the square/opposition harmonic
    d = np.array([0.0, 90.0, 180.0])
    h2 = 2 + 2 * np.cos(2 * d * rad)
    assert np.isclose(h2[0], 4) and np.isclose(h2[1], 0) and np.isclose(h2[2], 4), h2
    print(f"  h=2 peaks at 0 and 180, nulls at 90: {h2.round(3)} — the hard-aspect harmonic")

    # ── 2. determinism and width: the shape contract verify_docs refuses to publish a change in ───────────
    class _E:
        pass
    for n in (7, 250):
        e = _E()
        e.LON = np.random.default_rng(n).uniform(0, 360, size=(6, 18, n))
        B = build(e)
        assert set(B) == set(build(e)), "block keys must not depend on the batch"
        for k, v in B.items():
            assert v.shape == (n, 3 * BANK), (k, v.shape)
            assert np.all(np.isfinite(v)), k
    print(f"  4 blocks x {3 * BANK} columns, identical for n=7 and n=250, all finite")

    # rebuilding the same batch must give byte-identical columns (the bank is drawn once, at import)
    e = _E(); e.LON = np.random.default_rng(5).uniform(0, 360, size=(6, 18, 64))
    a, b = build(e), build(e)
    for k in a:
        assert np.array_equal(a[k], b[k]), k
    print("  the bank is fixed at import: two builds of one batch are byte-identical")

    # ── 3. the wedding slot is never read ─────────────────────────────────────────────────────────────────
    e1 = _E(); e1.LON = np.random.default_rng(9).uniform(0, 360, size=(6, 18, 40))
    e2 = _E(); e2.LON = e1.LON.copy()
    e2.LON[2] = np.random.default_rng(10).uniform(0, 360, size=(18, 40))   # scramble the wedding slot
    e2.LON[3:] = np.random.default_rng(11).uniform(0, 360, size=(3, 18, 40))
    for k in build(e1):
        assert np.array_equal(build(e1)[k], build(e2)[k]), f"{k} READ A NON-BIRTH SLOT — that is leakage"
    print("  scrambling the wedding and progressed slots changes nothing: only the two birth charts are read")

    # ── 4. a field must actually vary, and vary with the CONFIGURATION not the epoch ───────────────────────
    e = _E(); e.LON = np.random.default_rng(3).uniform(0, 360, size=(6, 18, 4000))
    V = build(e)["coh: FAST bodies (Sun Moon Mercury Venus Mars) — era-blind by construction"]
    sd = V[:, 0::3].std(axis=0)
    assert (sd > 1e-6).all(), f"{int((sd <= 1e-6).sum())} dead fields"
    print(f"  every one of {BANK} FAST intensities varies (min sd {sd.min():.3f}, median {np.median(sd):.3f})")
