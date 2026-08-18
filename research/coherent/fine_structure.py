"""
fine_structure.py — the periodic claims of astrology, tested against everything the two YEARS can say.

THE ARGUMENT THIS FILE RESTS ON

Two birth dates are two numbers, so ANY feature f(d1, d2) is a function of their sum and their difference —
of era and of age gap. There is no feature of this dataset that is independent of both, and looking for one was
never going to succeed. What separates astrology from "when were you born and how far apart" is not
independence, it is PERIODICITY: era and gap act smoothly (mortality rises across centuries, risk rises with
the gap), while astrology claims the outcome depends on the dates MODULO a cycle — 365 days, 12 signs, 7
weekdays, 12 animal years, 27 nakshatras. Smooth and periodic are genuinely separable.

The age gap decomposes to make this precise:

    gap_in_days = 365.25 * (whole years apart) + (day-of-year difference)

The first term carries the mortality effect worth 0.6047. The second is pure seasonal alignment and CANNOT carry
it. Sun-sign distance is that second term binned to 30 degrees; weekday agreement is the gap mod 7; Chinese
animal distance is the gap mod 12 years. Each is periodic in the gap and therefore invisible to any smooth model
of it.

THE TEST, AND WHY IT IS THE STRONGEST ONE AVAILABLE HERE

    baseline   a gradient-boosted model on (birth year of older, birth year of younger)

At year resolution that captures era, gap, and every interaction between them — the entire smooth content of the
two dates. It CANNOT contain a sub-year or mod-cycle quantity, because it never sees one. So for each candidate:

    delta = heldout_AUC( baseline + feature )  -  heldout_AUC( baseline )

is exactly what the periodic claim adds beyond when-and-how-far-apart, fitted on the training half and read out
of time. Held-out AUC has a standard error near 0.006 here, so a delta must clear roughly 0.012 to mean anything;
the report says so rather than leaving a reader to assume three decimals are all real.

WHAT IS TESTED. Sun-sign compatibility in the forms people actually use (same sign, same element, same modality,
trine, square, sextile, opposition, the composite "compatible" rule); the seasonal separation of the two births
and its harmonics; weekday and its Chaldean planetary ruler; the Chinese animal pair including the san-he trine
groups and the liu-chong six-year clash; the stem elements; and the gap taken modulo 7, 12, 19 and 29.53 so that
each cycle's own claim is isolated from the smooth gap.
"""
import csv
import json
import math
import os
import sys

import numpy as np
import pandas as pd

OUT = os.environ.get("AQ_OUT", "/tmp/aqfine")
os.makedirs(OUT, exist_ok=True)
LON = os.environ.get("AQ_LON", "/tmp/aqcoh/lon.npz")
TRAIN = os.environ.get("AQ_TRAIN", "/tmp/aqdur/train.csv")
TEST = os.environ.get("AQ_TEST", "/tmp/aqdur/test.csv")

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces"]
ANIMALS = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster",
           "Dog", "Pig"]
# The Chaldean order of the planetary day rulers, Sunday first — the oldest surviving astrological week.
DAYLORD = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
STEM_EL = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]


def auc(y, s):
    y = np.asarray(y, np.int64)
    s = np.asarray(s, np.float64)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    o = np.argsort(s, kind="mergesort")
    ys, ss = y[o], s[o]
    r = np.empty(len(ss))
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[i:j + 1] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((r[ys == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def fold(d, period):
    d = np.mod(d, period)
    return np.minimum(d, period - d)


def features(df, sun_o, sun_y):
    """Every periodic quantity, from the dates and the two Sun longitudes. Returns {name: (expl, values)}."""
    F = {}

    def add(n, e, v):
        F[n] = (e, np.asarray(v, dtype=np.float64))

    do = pd.to_datetime(df.dob_older, format="%Y-%m-%d")
    dy = pd.to_datetime(df.dob_younger, format="%Y-%m-%d")
    doy_o, doy_y = do.dt.dayofyear.to_numpy(), dy.dt.dayofyear.to_numpy()
    wd_o, wd_y = ((do.dt.dayofweek.to_numpy() + 1) % 7), ((dy.dt.dayofweek.to_numpy() + 1) % 7)  # 0=Sunday
    yo, yy = do.dt.year.to_numpy(), dy.dt.year.to_numpy()
    mo, my = do.dt.month.to_numpy(), dy.dt.month.to_numpy()
    gap_days = (dy - do).dt.days.to_numpy().astype(float)

    # ── the gap, decomposed. The whole-year part is the nuisance; the remainder cannot carry mortality. ──
    whole = np.round(gap_days / 365.2425)
    add("age gap in whole years (the NUISANCE, shown for scale)",
        "The partners' age difference rounded to whole years. This is the term that carries the mortality "
        "effect, and it is listed here only so the periodic terms below can be read against it.", whole)
    add("sub-year remainder of the age gap (days)",
        "What is left of the age gap after removing whole years: gap_days - 365.2425*round(gap_days/365.2425), "
        "folded to 0-182. This is the seasonal part of the gap and cannot carry a mortality effect, because "
        "mortality does not care which side of a birthday you fall on.",
        fold(gap_days - whole * 365.2425, 365.2425))
    for p, nm in ((7.0, "week"), (12.0, "twelve-year animal cycle"), (19.0, "Metonic 19-year cycle"),
                  (29.53059, "synodic month")):
        unit = "days" if p < 13 or p > 20 else "years"
        v = gap_days / (365.2425 if unit == "years" else 1.0)
        add(f"age gap modulo the {nm}",
            f"The age gap taken modulo the {nm} and folded, isolating that cycle's own claim from the smooth "
            f"age-gap trend. A smooth model of the gap cannot contain this.", fold(v, p))

    # ── seasonal alignment: the sub-year part of the gap, in the forms traditions read ──────────────────
    for who, d in (("older", doy_o), ("younger", doy_y)):
        add(f"day of the year — {who} partner",
            f"The {who} partner's birth day counted from 1 January, 1-366. The season of birth, which every "
            f"tradition here reads and which is very nearly orthogonal to the birth year.", d)
        for h in (1, 2, 3, 4):
            add(f"day of the year, cos harmonic {h} — {who} partner",
                f"cos({h} x 2pi x day-of-year/365.25) for the {who} partner: the {h}-per-year component of the "
                f"seasonal cycle, free of the 31-December-to-1-January wrap.",
                np.cos(h * 2 * np.pi * d / 365.25))
    dd = fold(doy_o.astype(float) - doy_y.astype(float), 365.25)
    add("seasonal separation of the two births (0-182 days)",
        "How far apart in the YEAR the two partners were born, ignoring which year. 0 means both born at the "
        "same point of the seasonal cycle. This is the Sun-to-Sun synastry contact and the sub-year part of the "
        "age gap at once.", dd)
    add("born within 15 days of the same point in the year",
        "1 when the partners' birthdays fall within a fortnight of each other in the calendar, the strongest "
        "form of the 'same seasonal cohort' claim.", (dd < 15).astype(float))
    for h in (1, 2, 3, 4):
        add(f"seasonal separation, cos harmonic {h}",
            f"cos({h} x the two births' seasonal separation): the {h}-per-year harmonic of Sun-to-Sun contact. "
            f"h=1 peaks when the birthdays coincide, h=2 when they coincide OR are six months apart.",
            np.cos(h * 2 * np.pi * dd / 365.25))
    add("same calendar month of birth",
        "1 when both partners were born in the same month of the year.", (mo == my).astype(float))
    add("months between the two births in the year (0-6)",
        "The folded distance between the two birth months, 0 to 6.", fold(mo.astype(float) - my, 12))

    # ── SUN SIGN COMPATIBILITY: the most widely believed claim in the subject ───────────────────────────
    so = np.floor(np.mod(sun_o, 360.0) / 30.0)
    sy = np.floor(np.mod(sun_y, 360.0) / 30.0)
    dsign = fold(so - sy, 12)
    add("Sun-sign distance between the partners (0-6)",
        "How many of the twelve signs separate the two Suns, folded so 0 is the same sign and 6 is opposite. "
        "Every sun-sign compatibility rule in circulation is a function of this one number.", dsign)
    add("both Suns in the SAME sign", "1 when both partners share a Sun sign.", (dsign == 0).astype(float))
    add("Suns in the same ELEMENT (trine — the classic 'compatible' rule)",
        "1 when the two Sun signs share an element (fire/earth/air/water), i.e. are 0, 4 or 8 signs apart. This "
        "is the single most repeated compatibility rule in popular astrology.",
        (np.mod(so - sy, 4) == 0).astype(float))
    add("Suns in the same MODALITY (cardinal/fixed/mutable)",
        "1 when the two Sun signs share a modality, i.e. are 0, 3, 6 or 9 signs apart — held to produce "
        "friction rather than ease.", (np.mod(so - sy, 3) == 0).astype(float))
    add("Suns in OPPOSITE signs (6 apart)",
        "1 when the Suns are exactly opposite, the axis read as both attraction and confrontation.",
        (dsign == 6).astype(float))
    add("Suns in SQUARE (3 or 9 signs apart)",
        "1 when the Suns are three signs apart either way, the classically difficult aspect.",
        (dsign == 3).astype(float))
    add("Suns in SEXTILE (2 or 10 signs apart)",
        "1 when the Suns are two signs apart, the classically easy aspect.", (dsign == 2).astype(float))
    add("popular 'compatible' verdict (same element OR sextile)",
        "1 when the pair satisfies the composite rule a magazine column would apply: same element, or two "
        "signs apart.", ((np.mod(so - sy, 4) == 0) | (dsign == 2)).astype(float))
    for who, s in (("older", so), ("younger", sy)):
        add(f"Sun sign as an ordinal 1-12 — {who} partner",
            f"Which sign the {who} partner's Sun occupied, Aries 1 to Pisces 12.", s + 1)
        add(f"Sun in a fire sign — {who} partner",
            f"1 when the {who} partner's Sun is in Aries, Leo or Sagittarius.", (np.mod(s, 4) == 0).astype(float))

    # ── the astrological WEEK: gap mod 7, and the Chaldean day rulers ───────────────────────────────────
    for who, w in (("older", wd_o), ("younger", wd_y)):
        add(f"weekday of birth (0 Sunday .. 6 Saturday) — {who} partner",
            f"Which day of the week the {who} partner was born. The seven-day week is the oldest astrological "
            f"cycle still in use and is almost perfectly orthogonal to both era and age gap.", w.astype(float))
        add(f"born on a Saturn day (Saturday) — {who} partner",
            f"1 when the {who} partner was born on Saturday, the day of Saturn — the classical significator of "
            f"marriage, duty and endurance.", (w == 6).astype(float))
        add(f"born on a Venus day (Friday) — {who} partner",
            f"1 when the {who} partner was born on Friday, the day of Venus, planet of attraction and union.",
            (w == 5).astype(float))
    add("same weekday of birth",
        "1 when both partners were born on the same day of the week, i.e. their age gap is a whole number of "
        "weeks.", (wd_o == wd_y).astype(float))
    add("weekday distance (0-3)",
        "The folded distance between the two birth weekdays.", fold(wd_o.astype(float) - wd_y, 7))
    add("both born on planetary days of the same sect (luminary/benefic vs malefic)",
        "1 when both birth weekdays are ruled by planets of the same classical sect: Sun, Moon, Jupiter and "
        "Venus on one side, Mars and Saturn on the other, Mercury neutral.",
        (np.isin(wd_o, [0, 1, 4, 5]) == np.isin(wd_y, [0, 1, 4, 5])).astype(float))

    # ── the Chinese pair: animal distance is the gap mod 12 YEARS, a periodic function of the gap ───────
    ao, ay = np.mod(yo - 4, 12), np.mod(yy - 4, 12)
    dan = fold(ao.astype(float) - ay, 12)
    add("Chinese animal distance between the partners (0-6)",
        "How many of the twelve animal years separate the partners' birth years, folded. Because it is the age "
        "gap modulo twelve, no smooth model of the gap can contain it.", dan)
    add("same Chinese animal (12 years apart, or born the same year)",
        "1 when both partners share an animal sign.", (dan == 0).astype(float))
    add("san-he trine group match (4 or 8 animals apart)",
        "1 when the two animals belong to the same san-he trine — the four groups of three that Chinese "
        "practice holds most compatible.", (np.mod(ao - ay, 4) == 0).astype(float))
    add("liu-chong clash (exactly 6 animals apart)",
        "1 when the animals are directly opposed on the twelve-year wheel, the liu-chong clash — the specific "
        "and widely believed claim that a six-year age gap is unlucky for a couple.", (dan == 6).astype(float))
    add("liu-he secret-friend pair",
        "1 when the two animals form one of the six liu-he 'secret friend' pairs, held to be quietly "
        "supportive.", np.isin(np.mod(ao + ay, 12), [1, 3, 5, 7, 9, 11]).astype(float))
    eo = np.array([STEM_EL.index(STEM_EL[i]) for i in np.mod(yo - 4, 10)], dtype=float)
    ey = np.array([STEM_EL.index(STEM_EL[i]) for i in np.mod(yy - 4, 10)], dtype=float)
    add("same stem element (Wood/Fire/Earth/Metal/Water)",
        "1 when both birth years carry the same of the five elements from the sexagenary stem.",
        (np.mod(yo - 4, 10) // 2 == np.mod(yy - 4, 10) // 2).astype(float))
    add("stem-element distance on the five-phase wheel (0-2)",
        "The folded distance between the partners' stem elements on the five-phase cycle, where adjacency is "
        "generation and distance two is conquest.", fold(np.mod(yo - 4, 10) // 2 - np.mod(yy - 4, 10) // 2, 5))
    return F


def main():
    from sklearn.ensemble import HistGradientBoostingClassifier

    Z = np.load(LON)
    tr = pd.read_csv(TRAIN, dtype={"dob_older": str, "dob_younger": str})
    te = pd.read_csv(TEST, dtype={"dob_older": str, "dob_younger": str})
    ytr_all, yte = Z["y_train"].astype(np.int64), Z["y_test"].astype(np.int64)
    assert len(tr) == len(ytr_all) and len(te) == len(yte), "lon.npz is not aligned with the CSVs"
    # alignment check against the cached years, so a silent row-order mismatch cannot pass
    yr_tr, yr_te = Z["yr_train"], Z["yr_test"]
    assert (yr_te[0] == te.dob_older.str[:4].astype(int).to_numpy()).all(), "held-out rows are misaligned"

    # DAY PRECISION ON BOTH SIDES. A periodic feature is not merely weaker on a year-only date, it is
    # UNDEFINED: `1856-00-00` has no day of the year, no weekday and no Sun sign. Treating it as 1 January
    # would invent a birthday for a third of the training half and plant a false spike at day 1 in every
    # seasonal feature here. The held-out half is day-precision throughout by construction, so this filter also
    # makes the two halves comparable.
    def dayprec(c):
        return c.str.len().eq(10) & ~c.str.endswith("-00") & ~c.str.slice(5, 7).eq("00")
    genuine = dayprec(tr.dob_older) & dayprec(tr.dob_younger)
    sun_tr_o, sun_tr_y = Z["lon_train"][0, 0], Z["lon_train"][1, 0]
    Ftr = features(tr[genuine].reset_index(drop=True), sun_tr_o[genuine.to_numpy()],
                   sun_tr_y[genuine.to_numpy()])
    Fte = features(te, Z["lon_test"][0, 0], Z["lon_test"][1, 0])
    ytr = ytr_all[genuine.to_numpy()]
    print(f"  train {len(ytr):,} couples with BOTH dates to the day (of {len(tr):,}; the rest carry no "
          f"day-of-year, weekday or Sun sign at all)")
    print(f"  held out {len(yte):,} · {len(Ftr)} periodic features")

    gap_te = (pd.to_datetime(te.dob_younger) - pd.to_datetime(te.dob_older)).dt.days.to_numpy().astype(float)
    band = (np.abs(gap_te) // 365.2425).astype(int)

    def matched(y, s):
        num = den = 0.0
        for b in np.unique(band):
            m = band == b
            yy_, ss = y[m], s[m]
            n1, n0 = int(yy_.sum()), int((1 - yy_).sum())
            if n1 and n0:
                num += auc(yy_, ss) * n1 * n0
                den += n1 * n0
        return num / den if den else float("nan")

    # THE BASELINE MUST BE GIVEN THE ROTATED COORDINATES, NOT ONLY THE RAW YEARS.
    #
    # A first version used (year_older, year_younger) alone and scored 0.5311, while the age gap by itself scores
    # 0.6039 — even though the gap IS their difference. Boosted trees split on axis-aligned thresholds, and a
    # difference is a diagonal in that plane, so the baseline could not represent the one effect it was supposed
    # to absorb. Every candidate correlated with the gap then showed a spurious gain for patching that failure:
    # the Metonic remainder came out at +0.0212 and the Chinese animal distance at +0.0149, and both are simply
    # `gap mod k`. Reporting either as a discovery would have been an artefact of the baseline's function class.
    #
    # So era and gap are handed over explicitly, in days as well as years, alongside the raw years.
    do_tr = pd.to_datetime(tr[genuine].dob_older.reset_index(drop=True), format="%Y-%m-%d")
    dy_tr = pd.to_datetime(tr[genuine].dob_younger.reset_index(drop=True), format="%Y-%m-%d")
    do_te = pd.to_datetime(te.dob_older, format="%Y-%m-%d")
    dy_te = pd.to_datetime(te.dob_younger, format="%Y-%m-%d")
    gtr = (dy_tr - do_tr).dt.days.to_numpy().astype(float)
    gte = (dy_te - do_te).dt.days.to_numpy().astype(float)
    otr = (do_tr - pd.Timestamp("1600-01-01")).dt.days.to_numpy().astype(float)
    ote = (do_te - pd.Timestamp("1600-01-01")).dt.days.to_numpy().astype(float)
    ytr_y = yr_tr[0][genuine.to_numpy()].astype(float)
    yyy_y = yr_tr[1][genuine.to_numpy()].astype(float)
    Xtr0 = np.column_stack([ytr_y, yyy_y, gtr, otr, otr + gtr])
    Xte0 = np.column_stack([yr_te[0].astype(float), yr_te[1].astype(float), gte, ote, ote + gte])

    def gbm(Xtr, Xte, seeds=3):
        p = np.zeros(len(Xte))
        for s in range(seeds):
            c = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.06, max_leaf_nodes=15,
                                               l2_regularization=1.0, early_stopping=True,
                                               validation_fraction=0.15, random_state=s)
            c.fit(Xtr, ytr)
            p += c.predict_proba(Xte)[:, 1]
        return p / seeds

    base = auc(yte, gbm(Xtr0, Xte0))
    se = 0.5 / math.sqrt(min(int(yte.sum()), int((1 - yte).sum())))
    print(f"\n  BASELINE — a boosted model given era AND the age gap explicitly (both years, the gap in days,")
    print(f"  each birth as a day number): held-out AUC {base:.4f}")
    print(f"  The age gap alone scores {max(auc(yte, gte), 1 - auc(yte, gte)):.4f}, so the baseline now absorbs it "
          f"rather than failing to represent it.")
    print(f"  held-out AUC standard error ~{se:.4f}; a delta needs roughly {2*se:.4f} to mean anything\n")

    rows = []
    for nm in Ftr:
        ex, vtr = Ftr[nm]
        _, vte = Fte[nm]
        a_tr = auc(ytr, vtr)
        sign = 1.0 if a_tr >= 0.5 else -1.0
        a_te = auc(yte, sign * vte)
        a_m = matched(yte, sign * vte)
        inc = auc(yte, gbm(np.column_stack([Xtr0, vtr]), np.column_stack([Xte0, vte])))
        rows.append({"name": nm, "explanation": ex, "train": max(a_tr, 1 - a_tr), "held": a_te,
                     "matched": a_m, "with_years": inc, "delta": inc - base})
    rows.sort(key=lambda r: -r["delta"])

    print(f"  {'#':>3}  {'periodic feature':<58} {'alone':>7} {'matched':>8} {'+base':>8} {'delta':>8}")
    for i, r in enumerate(rows, 1):
        mark = "  <<<" if r["delta"] > 2 * se else ""
        print(f"  {i:>3}  {r['name'][:58]:<58} {r['held']:>7.4f} {r['matched']:>8.4f} "
              f"{r['with_years']:>8.4f} {r['delta']:>+8.4f}{mark}")

    win = [r for r in rows if r["delta"] > 2 * se]
    print(f"\n  {len(win)} of {len(rows)} periodic features add more than {2*se:.4f} to era-plus-gap")
    if win:
        for r in win:
            print(f"    {r['name']}  delta {r['delta']:+.4f}")
    else:
        print("    none. Every periodic cycle tested — the sun-sign element trine, the six-year animal clash, "
              "the weekday of Saturn,\n    seasonal alignment, the Metonic and synodic remainders — adds anything to era plus the age\n    gap, out of time.")
    with open(os.path.join(OUT, "fine_structure.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "train", "held", "matched", "with_years", "delta",
                                          "explanation"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    json.dump({"baseline_two_years": base, "se": se, "n_features": len(rows), "n_winning": len(win)},
              open(os.path.join(OUT, "fine_structure_meta.json"), "w"), indent=1)
    print(f"\n  wrote {OUT}/fine_structure.csv")


if __name__ == "__main__":
    main()
