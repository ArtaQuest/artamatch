# ArtaMatch — where this stands

**Target.** Among relationships that ENDED, did they end NATURALLY (a partner died) or ARTIFICIALLY (divorce,
annulment, separation)? **Inputs: two birth dates. Nothing else** — no wedding date, no era, no places.

## The result

| | AUC |
|---|---|
| baseline (what two dates give free: the years, their gap, how completely each is recorded) | **0.5764** |
| stack of all 59 astrological members | **0.5764** |
| **gain from every astrology and numerology system combined** | **+0.0000** |

Every member contributes exactly zero. Not admitted, so absent from the stack, so unable to move the number in
either direction — the worst any component can do is nothing, by construction.

The same run admits a PLANTED control (the answer buried in noise) at +0.2619 and rejects pure NOISE at exactly
zero. The gate is neither too tight to see a real effect nor too loose to admit a fake one, and that is what
makes the zero readable.

## What is in the catalogue

~60 systems, every anchor checked against a published value ([WORLD_SYSTEMS.md](WORLD_SYSTEMS.md)):
Vedic (Ashtakoota's 8 kutas, Dashakoota's 4 southern, Mangal Dosha, Vimshottari, Ashtakavarga, **varga charts
D1-D60 including the navamsa**) · Chinese (four-pillar BaZi with hidden stems and ten gods, zodiac matrix, Tong
Shu, 28 mansions, Kua/Ba Zhai) · Japanese (Rokuyo, Nine Star Ki) · Korean (gunghap, son-eomneun-nal) · Javanese
weton · Balinese Pawukon · Tibetan · Maya · Aztec · Hellenistic · Uranian midpoint dials · Arabic lots · the
classical aspect doctrine with smooth orbs · 60 fixed stars with precession · declination and dignities ·
harmonics 2-9 · draconic · antiscia · five ayanamsas · Hebrew, Islamic, Jalali, Coptic, Ogham, runic, Igbo,
Akan, Parsi calendars · Pythagorean, Chaldean, Lo Shu and Vedic numerology.

## Why the zero is trustworthy

- **No leak.** Test half is strictly later-BORN, shares no person and no birth date with training, read once.
- **Four gates**, not one: all-folds, mean-fold, bootstrap 5th percentile, and a permutation test — the only
  gate that prices in family WIDTH. Read every test gain against its own null (+0.027 to +0.079), never zero.
- **Pooled evaluation**: 15,687 rows scored instead of 2,801, each once, by the latest model fitted before it.
- **Missing-date augmentation**: three masked copies in the fit so year-only and no-year inputs are trained on.
- **Controls in every run.** A plant that must be admitted, a noise that must be rejected.

## The honest limit, which is now the binding one

The corpus can resolve an effect of about **+0.011**. The effects in question live nearer **+0.005**. That needs
~200,000 labelled couples; Wikidata yields ~27,000 and is exhausted (relaxing to "both partners dead" was
measured at 35.7% accurate and is unusable). **Every null here is therefore partly a statement about the
sample, not only about the doctrine** — and no amount of further astrology fixes that.

WikiTree holds ~725,000 labelable couples, but its dumps are permission-gated: "Do not access or use the data
without permission." A bulk sweep of its public API was stopped on reading that, with 30,231 couples collected
and unused, pending a request to jamie@wikitree.com.

## Bugs this project found, all of one kind

A failure that looks like a result:
- a completeness log reporting **0 complete charts** on a file holding 26,680 (it counted the ascendant, which
  needs a birth time nobody has)
- an admission gate **rejecting its own planted answer** worth 0.83, because a fold's fit block held zero
  scored rows
- a **fabricated Sun** handed to every month-precision birth, inherited silently by every module reading it
- a failed fetch **writing an empty batch file** indistinguishable from "this range is genuinely empty", so
  96% of a sweep was thrown away while the API answered fine
- an input loader that would have paired a **181,596-row table with 89,467-row features** and reported
  confident numbers for data that never lined up

Each was caught by a check, none by reading the code. That is the argument for the controls.
