"""build_systems.py — every other system as a PSEUDO-BODY: its state, as an angle on its own circle.

Operator 2026-09-02: "take each system as a body with discrete (numerology) or continuous
(astrology) states; convert each state to an angle by the number of states — numerology has 9
states, so state 1 is 40 degrees." Then the same three angle families produce every aspect,
across systems too (his life path against her Venus, his animal against her animal).

Conventions are the LAB's (docs/scorer.py), so corpus and browser agree to the digit:
  day pillar  sx = (JDN + 49) mod 60 -> day stem sx mod 10, day branch sx mod 12
  year animal (Y - 4) mod 12, year stem (Y - 4) mod 10, on the plain calendar year
  Tzolkin     k = (JDN - 584283) mod 260 -> sign k mod 20, tone k mod 13
  nine-star   1 + (11 - (1 + (digitsum(Y) - 1) mod 9) - 1) mod 9
  life path   digits of YYYYMMDD summed to one digit
  birthday    the day of the month, 31 states
  lord of night  (JDN - 584283) mod 9
angle = (state + 1) * 360 / N for a 0-based state index, i.e. state 1 = 360/N degrees.
Writes AQ_DIR/systems.npz: theta_a_sys, theta_b_sys (rows x systems, degrees), names, nstates.
"""
import os, numpy as np, pandas as pd
D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt"))
def jdn(y, m, d):
    a = (14 - m) // 12; yy = y + 4800 - a; mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
def lifepath(y, m, d):
    t = sum(int(c) for c in f"{y:04d}{m:02d}{d:02d}")
    while t > 9: t = sum(int(c) for c in str(t))
    return t
def ninestar(y):
    return 1 + (11 - (1 + (sum(int(c) for c in str(y)) - 1) % 9) - 1) % 9
SYS = [("num_lifepath", 9), ("num_birthday", 31), ("cn_year_animal", 12), ("cn_year_stem", 10),
       ("cn_day_stem", 10), ("cn_day_branch", 12), ("nine_star", 9),
       ("tz_sign", 20), ("tz_tone", 13), ("lord_night", 9)]
def states(iso):
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    j = jdn(y, m, d); sx = (j + 49) % 60; k = (j - 584283) % 260
    return [lifepath(y, m, d) - 1, d - 1, (y - 4) % 12, (y - 4) % 10, sx % 10, sx % 12,
            ninestar(y) - 1, k % 20, k % 13, (j - 584283) % 9]
def angles(iso):
    return [(st + 1) * 360.0 / n for st, (_, n) in zip(states(iso), SYS)]
full = pd.read_csv(f"{D_}/full.csv", dtype=str)
A = np.array([angles(v) for v in full.true_dob_a], np.float64)
B = np.array([angles(v) for v in full.true_dob_b], np.float64)
np.savez_compressed(f"{D_}/systems.npz", theta_a_sys=A, theta_b_sys=B,
                    names=np.array([n for n, _ in SYS]), nstates=np.array([n for _, n in SYS]))
print(f"wrote {D_}/systems.npz · {len(SYS)} systems x {len(full):,} couples")
print("  example", full.true_dob_a.iloc[0], "->", dict(zip([n for n,_ in SYS], [round(x,1) for x in angles(full.true_dob_a.iloc[0])])))
