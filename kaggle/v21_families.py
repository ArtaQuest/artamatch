"""
v21_families.py — wave 5, small and sharp. All both-date doctrine:
  - RUDHYAR'S EIGHT LUNATION PHASES (new, crescent, first quarter, gibbous, full, disseminating,
    last quarter, balsamic), his birth phase x hers — the lunation-cycle school of modern astrology;
  - the FIFTH HARMONIC (Addey's quintile harmonic of creative bonds) sign pairs for Venus and Moon;
  - BaZi LUCK-CYCLE DIRECTIONS (Da Yun): a man born in a yang year runs his decades forward, in a yin
    year backward; for a woman the reverse — his direction x hers;
  - the INAUSPICIOUS NITYA-YOGA class (the nine yogas the pancanga warns against), paired.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
import explain_gam as EG

BADYOGA = {0, 5, 8, 9, 12, 14, 16, 18, 26}     # Vishkambha Atiganda Shula Ganda Vyaghata Vajra Vyatipata Parigha Vaidhriti

def families21(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    add = lambda M, nm: (blocks.append(np.asarray(M, np.float32)), names.extend(nm))
    oh = EG.onehot
    PH = ["New", "Crescent", "FirstQuarter", "Gibbous", "Full", "Disseminating", "LastQuarter", "Balsamic"]
    pa = np.floor(((A[:, ix["moon"]] - A[:, ix["sun"]]) % 360) / 45)
    pb = np.floor(((B[:, ix["moon"]] - B[:, ix["sun"]]) % 360) / 45)
    add(*oh(np.where(np.isfinite(pa) & np.isfinite(pb), pa * 8 + pb, np.nan), 64, "moonphase8_pair",
            [f"{x}x{y}" for x in PH for y in PH]))
    S144 = [f"{EG.SIGNS[i]}x{EG.SIGNS[j]}" for i in range(12) for j in range(12)]
    for b in ("venus", "moon"):
        h5a = np.floor(((A[:, ix[b]] * 5) % 360) / 30); h5b = np.floor(((B[:, ix[b]] * 5) % 360) / 30)
        add(*oh(np.where(np.isfinite(h5a) & np.isfinite(h5b), h5a * 12 + h5b, np.nan), 144,
                f"{b}_h5pair", S144))
    ya = pd.to_numeric(df.dob_a.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    yb = pd.to_numeric(df.dob_b.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    # yang year stem = even index; man+yang runs forward, woman+yin runs forward
    fa = np.where(np.isfinite(ya), (((ya - 4) % 10) % 2 == 0).astype(float), np.nan)      # his forward
    fb = np.where(np.isfinite(yb), (((yb - 4) % 10) % 2 == 1).astype(float), np.nan)      # her forward
    add(*oh(np.where(np.isfinite(fa) & np.isfinite(fb), fa * 2 + fb, np.nan), 4, "dayun_pair",
            ["BothBackward", "HerForward", "HisForward", "BothForward"]))
    yga = np.floor(((A[:, ix["moon"]] + A[:, ix["sun"]]) % 360) / (360.0 / 27.0))
    ygb = np.floor(((B[:, ix["moon"]] + B[:, ix["sun"]]) % 360) / (360.0 / 27.0))
    ba = np.where(np.isfinite(yga), np.isin(yga, list(BADYOGA)).astype(float), np.nan)
    bb = np.where(np.isfinite(ygb), np.isin(ygb, list(BADYOGA)).astype(float), np.nan)
    add(*oh(np.where(np.isfinite(ba) & np.isfinite(bb), ba * 2 + bb, np.nan), 4, "badyoga_pair",
            ["neither", "her_only", "his_only", "both"]))
    return np.column_stack(blocks).astype(np.float32), names
