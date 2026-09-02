"""build_tradition_groupings.py — competition entry "tradition-groupings" (helper, does not touch
build_systems.py: it IMPORTS it and reuses states(), so the Li Chun year, the gendered Kua and the
sexagenary day are exactly the corpus's).

THE IDEA. The lean bank sees a discrete system only through the FIRST harmonic of its own circle
(k=1 on the 12-animal circle = cos of the raw animal difference), but no tradition scores a pair
that way. Each tradition scores on a COARSER circle — a grouping of the states — and that grouping
is a different pseudo-body, not a harmonic of the parent one (Wood = stems 0 AND 1: no harmonic of
the 10-stem circle is constant on a pair of adjacent states). So the groupings are written as
pseudo-bodies in their own right, each state on its own circle in the tradition's cyclic order:

  Chinese year (Li Chun boundary)
    cn_year_trine   4   San He trines: animal mod 4 (Rat-Dragon-Monkey, Ox-Snake-Rooster,
                        Tiger-Horse-Dog, Rabbit-Goat-Pig). Same trine = 0; the clash (Liu Chong,
                        opposite animals) lands at 2.
    cn_year_liuhe  12   THE SECRET-FRIEND MIRROR. His side: his animal. Her side: the animal that
                        is HER secret friend, (1 - hers) mod 12 (Rat-Ox, Tiger-Pig, Rabbit-Dog,
                        Dragon-Rooster, Snake-Monkey, Horse-Goat all sum to 1). his - her = 0 when
                        he is her Liu He partner; = 6 when he is her Liu Hai (harm: pairs sum to
                        7). A single k=1 phasor puts the friend at its peak and the harm at its
                        trough, 180 degrees apart — exactly the tradition's shape.
    cn_year_elem    5   stem element in the GENERATING (sheng) order Wood>Fire>Earth>Metal>Water:
                        diff 0 same, +1/-1 one generates the other, +-2 the controlling (ke) pair.
    cn_year_pol     2   stem polarity (yang/yin).
  Chinese day pillar (BaZi's spouse palace) — the same four on the sexagenary DAY
    cn_day_trine 4 · cn_day_liuhe 12 · cn_day_elem 5 · cn_day_pol 2
  Kua              cn_kua_group   2   East (1,3,4,9) / West (2,6,7,8) life groups
  Nine-Star Ki     ninestar_elem  5   1 Water · 2,5,8 Earth · 3,4 Wood · 6,7 Metal · 9 Fire, in
                                      sheng order Wood>Fire>Earth>Metal>Water
  Numerology       num_lp_parity  2   life path odd/even
                   num_lp_group   3   the three compatibility groups {1,5,7} {2,4,8} {3,6,9}

Writes AQ_DIR/comp_tradition-groupings_systems.npz in the systems.npz layout (theta_*_sys in
degrees, names, nstates) so the copied fitter reads it through the same SYSTEMS path.
"""
import os, sys, numpy as np, pandas as pd
import swisseph as swe
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_systems as B                      # reused, never edited

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
OUT = os.environ.get("AQ_SYSFILE", "comp_tradition-groupings_systems.npz")

GROUPINGS = [("cn_year_trine", 4), ("cn_year_liuhe", 12), ("cn_year_elem", 5), ("cn_year_pol", 2),
             ("cn_day_trine", 4), ("cn_day_liuhe", 12), ("cn_day_elem", 5), ("cn_day_pol", 2),
             ("cn_kua_group", 2), ("ninestar_elem", 5), ("num_lp_parity", 2), ("num_lp_group", 3)]
KUA_WEST = {2, 6, 7, 8}                                   # 1-based Kua numbers
NINESTAR_ELEM = {3: 0, 4: 0, 9: 1, 2: 2, 5: 2, 8: 2, 6: 3, 7: 3, 1: 4}   # 1-based star -> sheng index
LP_GROUP = {1: 0, 5: 0, 7: 0, 2: 1, 4: 1, 8: 1, 3: 2, 6: 2, 9: 2}         # 1-based life path

def grouping_states(st, female):
    """0-based grouping states from build_systems.states() output (all 0-based)."""
    ya, ys = st["cn_year_animal"], st["cn_year_stem"]
    da, ds = st["cn_day_branch"], st["cn_day_stem"]
    kua, star, lp = st["cn_kua"] + 1, st["nine_star"] + 1, st["num_lifepath"] + 1
    mirror = (lambda a: (1 - a) % 12) if female else (lambda a: a)
    return {"cn_year_trine": ya % 4, "cn_year_liuhe": mirror(ya), "cn_year_elem": ys // 2, "cn_year_pol": ys % 2,
            "cn_day_trine": da % 4, "cn_day_liuhe": mirror(da), "cn_day_elem": ds // 2, "cn_day_pol": ds % 2,
            "cn_kua_group": int(kua in KUA_WEST), "ninestar_elem": NINESTAR_ELEM[star],
            "num_lp_parity": lp % 2, "num_lp_group": LP_GROUP[lp]}

def angles(st, female):
    g = grouping_states(st, female)
    for n, N in GROUPINGS:
        assert 0 <= g[n] < N, (n, g[n])
    return [(g[n] + 1) * 360.0 / N for n, N in GROUPINGS]      # same state->angle rule as build_systems

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
    # sanity: every state of every grouping is populated on both sides
    for c, (n, N) in enumerate(GROUPINGS):
        for arr, who in ((A, "his"), (Bm, "her")):
            seen = len(np.unique(np.round(arr[:, c], 6)))
            assert seen == N, f"{who} {n}: {seen} of {N} states seen"
    np.savez_compressed(f"{D_}/{OUT}", theta_a_sys=A, theta_b_sys=Bm,
                        names=np.array([n for n, _ in GROUPINGS]), nstates=np.array([n for _, n in GROUPINGS]))
    print(f"wrote {D_}/{OUT} · {len(GROUPINGS)} grouping pseudo-bodies x {len(full):,} couples")
