"""build_harmonic_mapping.py — competition entry "harmonic-mapping" (helper; IMPORTS build_systems
and reuses states(), never edits it, so Li Chun, the gendered Kua and the sexagenary day are the
corpus's own).

THE IDEA. A discrete system enters the bank as an angle s*360/N, so k=1 on that circle assumes the
states are ADJACENT in numeric order. For several traditions that adjacency is not the tradition's
geometry, and the lean bank (k=1 only) cannot recover the tradition's circle from the naive one —
a re-ordering of a prime-length circle is a HIGHER harmonic, a grouping is no harmonic at all. So
each tradition's own placement is written as its own pseudo-body, angle = the tradition's position:

  LO SHU compass (8 positions; the Later-Heaven trigram circle, N->NE->E->SE->S->SW->W->NW):
      1 N · 8 NE · 3 E · 4 SE · 9 S · 2 SW · 7 W · 6 NW; 5 is the CENTRE and has no direction, so it
      borrows by the tradition's gendered rule (man -> 2, woman -> 8, the same rule Kua uses).
      Applied to: life path, reduced birthday, attitude number, Kua, Nine-Star year, Nine-Star month.
  Tzolkin colour/direction (4): sign mod 4 — Imix East, Ik' North, Ak'bal West, K'an South …
      (Dreamspell Red/White/Blue/Yellow). On the 20-circle this is harmonic 5, absent from the lean bank.
  Weekday in CHALDEAN order (7): Saturn Jupiter Mars Sun Venus Mercury Moon — the heptagram
      whose every-third step gives the calendar week; position = (3*weekday + 3) mod 7.
  Nayin element (5, sheng order Wood>Fire>Earth>Metal>Water), day pillar and year pillar: the
      30 nayin carry an irregular element sequence (Sea Metal, Furnace Fire, Forest Wood, Roadside
      Earth, …), the classic 合婚 element match; NOT a harmonic of the 30-circle.
  Branch element (5, sheng order), day and year: Zi Water, Chou Earth, Yin/Mao Wood, Chen Earth,
      Si/Wu Fire, Wei Earth, Shen/You Metal, Xu Earth, Hai Water — Earth four times, irregular.
  Branch season / San Hui direction (4), day and year: Hai-Zi-Chou North, Yin-Mao-Chen East,
      Si-Wu-Wei South, Shen-You-Xu West — contiguous blocks, no harmonic of the 12-circle.
  Manzil quarter (4): mansion // 7 — the four seven-mansion seasons (the Chinese Four Symbols).

Writes AQ_DIR/comp_harmonic-mapping_systems.npz in the systems.npz layout (theta_*_sys degrees,
names, nstates) so the copied fitter reads it through the SYSTEMS path.
"""
import os, sys, numpy as np, pandas as pd
import swisseph as swe
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_systems as B                      # reused, never edited

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
OUT = os.environ.get("AQ_SYSFILE", "comp_harmonic-mapping_systems.npz")

MAPPED = [("lp_loshu", 8), ("bdr_loshu", 8), ("att_loshu", 8), ("kua_loshu", 8),
          ("ninestar_loshu", 8), ("ninestar_month_loshu", 8),
          ("tz_colour", 4), ("weekday_chaldean", 7),
          ("day_nayin_elem", 5), ("year_nayin_elem", 5),
          ("day_branch_elem", 5), ("year_branch_elem", 5),
          ("day_branch_season", 4), ("year_branch_season", 4),
          ("manzil_quarter", 4)]
LOSHU = {1: 0, 8: 1, 3: 2, 4: 3, 9: 4, 2: 5, 7: 6, 6: 7}          # 1-based number -> compass slot
# Wood 0 · Fire 1 · Earth 2 · Metal 3 · Water 4  (sheng order)
NAYIN15 = [3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4]              # the 30 nayin repeat after 15
BRANCH_ELEM = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]                   # Zi..Hai
CRT60 = {(s % 10, s % 12): s for s in range(60)}                     # (stem, branch) -> sexagenary index

def loshu(num1to9, female):
    if num1to9 == 5: num1to9 = 8 if female else 2
    return LOSHU[num1to9]

def mapped_states(st, female):
    """0-based states of the mapped pseudo-bodies from build_systems.states() output."""
    day60 = CRT60[(st["cn_day_stem"], st["cn_day_branch"])]
    year60 = CRT60[(st["cn_year_stem"], st["cn_year_animal"])]
    db, yb = st["cn_day_branch"], st["cn_year_animal"]
    return {"lp_loshu": loshu(st["num_lifepath"] + 1, female),
            "bdr_loshu": loshu(st["num_birthday_reduced"] + 1, female),
            "att_loshu": loshu(st["num_attitude"] + 1, female),
            "kua_loshu": loshu(st["cn_kua"] + 1, female),
            "ninestar_loshu": loshu(st["nine_star"] + 1, female),
            "ninestar_month_loshu": loshu(st["nine_star_month"] + 1, female),
            "tz_colour": st["tz_sign"] % 4,
            "weekday_chaldean": (3 * st["weekday"] + 3) % 7,
            "day_nayin_elem": NAYIN15[(day60 // 2) % 15],
            "year_nayin_elem": NAYIN15[(year60 // 2) % 15],
            "day_branch_elem": BRANCH_ELEM[db], "year_branch_elem": BRANCH_ELEM[yb],
            "day_branch_season": ((db + 1) // 3) % 4, "year_branch_season": ((yb + 1) // 3) % 4,
            "manzil_quarter": st["manzil"] // 7}

def angles(st, female):
    g = mapped_states(st, female)
    for n, N in MAPPED:
        assert 0 <= g[n] < N, (n, g[n])
    return [(g[n] + 1) * 360.0 / N for n, N in MAPPED]      # same state->angle rule as build_systems

if __name__ == "__main__":
    full = pd.read_csv(f"{D_}/full.csv", dtype=str)
    Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
    bodies = [str(b) for b in Z["bodies"]]; isun, imoon = bodies.index("sun"), bodies.index("moon")
    def side(col, theta, female):
        out = []
        for iso, row in zip(full[col], theta):
            y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
            aya = swe.get_ayanamsa_ut(swe.julday(y, m, d, 12.0))
            out.append(angles(B.states(y, m, d, float(row[isun]), float(row[imoon]), aya, female), female))
        return np.array(out, np.float64)
    A = side("true_dob_a", Z["theta_a_train"], False)
    Bm = side("true_dob_b", Z["theta_b_train"], True)
    for c, (n, N) in enumerate(MAPPED):
        for arr, who in ((A, "his"), (Bm, "her")):
            seen = len(np.unique(np.round(arr[:, c], 6)))
            assert seen == N, f"{who} {n}: {seen} of {N} states seen"
    # the mapped circle must differ from the naive one it came from (sanity, not a proof of signal)
    np.savez_compressed(f"{D_}/{OUT}", theta_a_sys=A, theta_b_sys=Bm,
                        names=np.array([n for n, _ in MAPPED]), nstates=np.array([n for _, n in MAPPED]))
    print(f"wrote {D_}/{OUT} · {len(MAPPED)} mapped pseudo-bodies x {len(full):,} couples")
