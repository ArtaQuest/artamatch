"""
gendered_synastry.py — the family that lets the model tell the HUSBAND from the WIFE.

Every other module was built order-free (max/min, absolute arcs) to stop the model learning column order as a
shortcut. On a gendered corpus — column a IS the man, asserted at build time — that same choice ERASES gender:
a swap test moved predictions by only 0.003. But the doctrines are asymmetric: Aṣṭakūṭa counts Tārā from the
BRIDE's nakṣatra to the groom's, Mangal Doṣa weighs the groom's Mars against the bride's Moon differently from
the reverse, and the whole tradition of synastry distinguishes whose Sun falls on whose Moon.

So every feature here is SIGNED or SIDED, husband-first by construction:
  · signed arcs husband-minus-wife per body, as sin/cos, plus their 2nd and 3rd harmonics
  · each partner's own longitudes as separate husband_/wife_ columns (identity, not max/min)
  · the signed SLOW arcs (Saturn/Uranus/Neptune/Pluto) — "husband older" in astrological dress, since a slow
    body's signed phase difference is the signed birth-order
  · directional Vedic: Tārā counted bride->groom AND groom->bride (they differ), directional Maṅgal (his Mars
    from her Moon, and hers from his), whose-Sun-on-whose-Moon both ways
"""
import numpy as np
import pandas as pd


def build(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float)   # the HUSBAND — column a is the man, asserted upstream
    B = np.asarray(Z[f"theta_b_{half}"], float)   # the WIFE
    cols, names = [], []
    use = [b for b in bodies if b not in ("ascendant", "medium_coeli")]
    ix = {b: bodies.index(b) for b in use}

    for b in use:
        d = (A[:, ix[b]] - B[:, ix[b]]) % 360.0   # SIGNED, husband minus wife
        r = np.radians(d)
        for h in (1, 2, 3):
            cols += [np.sin(h * r), np.cos(h * r)]
            names += [f"signed_arc_sin{h}_{b}", f"signed_arc_cos{h}_{b}"]
    for tag, C in (("husband", A), ("wife", B)):
        for b in use:
            r = np.radians(C[:, ix[b]] % 360.0)
            cols += [np.sin(r), np.cos(r)]
            names += [f"{tag}_sin_{b}", f"{tag}_cos_{b}"]

    NAKD = 360.0 / 27.0
    nak_h = np.floor((A[:, ix["moon"]] % 360) / NAKD)
    nak_w = np.floor((B[:, ix["moon"]] % 360) / NAKD)
    ok = np.isfinite(nak_h) & np.isfinite(nak_w)
    t_wg = np.where(ok, ((nak_h - nak_w) % 27 + 1) % 9, np.nan)   # Tārā counted bride -> groom
    t_gw = np.where(ok, ((nak_w - nak_h) % 27 + 1) % 9, np.nan)   # and groom -> bride: NOT the same number
    cols += [t_wg, t_gw, np.where(ok, np.isin(t_wg, [3, 5, 7]).astype(float), np.nan),
             np.where(ok, np.isin(t_gw, [3, 5, 7]).astype(float), np.nan)]
    names += ["tara_bride_to_groom", "tara_groom_to_bride", "tara_bad_b2g", "tara_bad_g2b"]

    hm = np.floor(((A[:, ix["mars"]] - B[:, ix["moon"]]) % 360) / 30) + 1   # his Mars from her Moon
    wm = np.floor(((B[:, ix["mars"]] - A[:, ix["moon"]]) % 360) / 30) + 1   # her Mars from his Moon
    cols += [hm, wm, np.where(np.isfinite(hm), np.isin(hm, [1, 2, 4, 7, 8, 12]).astype(float), np.nan),
             np.where(np.isfinite(wm), np.isin(wm, [1, 2, 4, 7, 8, 12]).astype(float), np.nan)]
    names += ["his_mars_from_her_moon", "her_mars_from_his_moon", "manglik_groom", "manglik_bride"]

    for nm, x, y in (("his_sun_her_moon", A[:, ix["sun"]], B[:, ix["moon"]]),
                     ("her_sun_his_moon", B[:, ix["sun"]], A[:, ix["moon"]]),
                     ("his_venus_her_mars", A[:, ix["venus"]], B[:, ix["mars"]]),
                     ("her_venus_his_mars", B[:, ix["venus"]], A[:, ix["mars"]])):
        d = np.abs((x - y + 180) % 360 - 180)
        cols += [d, np.clip(1 - d / 8.0, 0, 1)]
        names += [f"{nm}_arc", f"{nm}_conj8"]

    X = np.column_stack(cols).astype(np.float32)
    return X, names
