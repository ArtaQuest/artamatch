"""
verdict_stack.py — EVERY FEATURE IS A TRADITION'S OWN VERDICT. Only the ensembling is trained.

Operator 2026-08-25: "every feature must be a tradition. only the ensembling must be trained. do not learn
feature that can't be explained by a tradition."

So there is NO learned feature model anywhere in this file. Each member below is a doctrine's own stated rule,
computed exactly as the tradition states it, ORIENTED by the tradition (its 'bad for the marriage' pole scores
+1 toward divorce), and never fitted. The ONLY trained numbers are the non-negative combination weights of the
final stack — which are themselves readable as 'how much weight history gives each tradition'.
"""
import json, os, sys
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from pure_astro import load_families

D = os.path.expanduser("~/.artamatch-dev/remar_sh")


def col(X, names, want):
    i = names.index(want) if want in names else None
    return X[:, i].astype(float) if i is not None else np.full(len(X), np.nan)


def verdicts(df, Z, half):
    """One column per tradition, each the tradition's own verdict, oriented toward divorce."""
    X, names = load_families(df, Z, half)
    c = lambda w: col(X, names, w)
    V, N = [], []
    def v(name, val):
        V.append(np.asarray(val, float)); N.append(name)

    # ── VEDIC. Guna Milan: the deficit from 36 is the tradition's own failure measure; below 18 is a refusal.
    v("vedic_guna_deficit", (36.0 - c("world:guna_guna_total")) / 36.0)
    v("vedic_nadi_dosha", 1.0 - c("world:guna_nadi") / 8.0)          # nadi score 0 IS the dosha
    v("vedic_bhakoot_dosha", 1.0 - c("world:guna_bhakoot") / 7.0)
    v("vedic_rajju_dosha", c("world2:rajju_same"))
    v("vedic_vedha_dosha", c("world2:vedha_dosha"))
    v("vedic_tara_dosha_b2g", c("gendered_synastry:tara_bad_b2g"))   # directional, bride to groom
    v("vedic_tara_dosha_g2b", c("gendered_synastry:tara_bad_g2b"))
    one_manglik = np.abs(c("gendered_synastry:manglik_groom") - c("gendered_synastry:manglik_bride"))
    v("vedic_manglik_unmatched", one_manglik)                        # one Manglik only: the classical affliction
    v("vedic_moon_gandanta", np.fmax(c("degree_lore:h_moon_gandanta"), c("degree_lore:w_moon_gandanta")))
    v("vedic_moon_mrtyu", np.fmax(c("degree_lore:h_moon_mrtyu"), c("degree_lore:w_moon_mrtyu")))
    v("vedic_kemadruma_either", np.fmax(c("degree_lore:h_kemadruma"), c("degree_lore:w_kemadruma")))
    v("vedic_gajakesari_both", 1.0 - c("degree_lore:h_gajakesari") * c("degree_lore:w_gajakesari"))
    v("vedic_rikta_tithi_either", np.fmax(c("panchanga_natal:h_rikta"), c("panchanga_natal:w_rikta")))
    v("vedic_tithi_kuta_dosha", c("panchanga_natal:tithi_kuta_bad"))
    v("vedic_vara_lords_enemies", 1.0 - c("panchanga_natal:vara_lords_friends"))
    v("vedic_eclipse_born_either", np.fmax(c("panchanga_natal:h_eclipse_born"), c("panchanga_natal:w_eclipse_born")))

    # ── CHINESE. The zodiac matrix as the almanac scores it; Ba Zhai's eight relations; kong wang; gunghap.
    zod = (c("world:liu_chong") + c("world:liu_hai") + c("world:xiang_xing")
           - c("world:san_he") - c("world:liu_he"))
    v("chinese_zodiac_score", zod)
    v("chinese_bazhai_bad", (c("world2:bazhai_relation") >= 4).astype(float)
      + np.where(np.isfinite(c("world2:bazhai_relation")), 0.0, np.nan))
    v("chinese_kongwang_spouse_void", np.fmax(c("degree_lore:wife_in_husband_void"),
                                              c("degree_lore:husband_in_wife_void")))
    v("chinese_day_branch_clash", c("degree_lore:day_branch_clash"))
    v("korean_gunghap_overcome", c("world2:gunghap_overcome") - c("world2:gunghap_generate"))
    v("kua_groups_differ", 1.0 - c("world2:same_group"))
    v("nine_star_not_generating", 1.0 - c("world:nine_star_generate"))

    # ── JAVANESE weton: Pegat ('divorce') is literally the tradition's own divorce verdict.
    v("javanese_weton_pegat", c("world:weton_pegat"))

    # ── WESTERN synastry, the classical weighted reading: luminaries and Venus contacts, harmonious minus hard
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in ("sun", "moon", "venus", "mars", "saturn", "jupiter")}
    def arc(x, y):
        return np.abs((x - y + 180.0) % 360.0 - 180.0)
    def asp(a, t, orb):
        return np.clip(1 - np.abs(a - t) / orb, 0, 1)
    harm = np.zeros(len(df)); hard = np.zeros(len(df)); seen = np.zeros(len(df))
    PAIRS = [("sun", "moon", 4), ("moon", "venus", 3), ("venus", "mars", 3), ("sun", "venus", 2),
             ("sun", "sun", 2), ("moon", "moon", 2), ("jupiter", "moon", 2), ("jupiter", "venus", 2)]
    MAL = [("saturn", "moon", 3), ("saturn", "venus", 3), ("mars", "moon", 2), ("saturn", "sun", 2)]
    for x, y, wgt in PAIRS:
        a = arc(A[:, ix[x]], B[:, ix[y]]); ok = np.isfinite(a)
        harm += np.where(ok, wgt * (asp(a, 0, 8) + asp(a, 120, 6) + asp(a, 60, 4)), 0); seen += ok
        hard += np.where(ok, wgt * (asp(a, 90, 6) + asp(a, 180, 8) * 0.5), 0)
    for x, y, wgt in MAL:
        a = arc(A[:, ix[x]], B[:, ix[y]]); ok = np.isfinite(a)
        hard += np.where(ok, wgt * (asp(a, 0, 6) + asp(a, 90, 6) + asp(a, 180, 8)), 0); seen += ok
    tot = np.where(seen > 3, (hard - harm) / np.maximum(seen, 1), np.nan)
    v("western_synastry_affliction", tot)
    # elements of the two Suns, the newspaper tradition: same or compatible element good, square bad
    es = np.floor((A[:, ix["sun"]] % 360) / 30) % 4; ew = np.floor((B[:, ix["sun"]] % 360) / 30) % 4
    oke = np.isfinite(es) & np.isfinite(ew)
    compat = (es == ew) | (np.abs(es - ew) == 2)                     # fire-air, earth-water pairings
    v("western_sun_elements_clash", np.where(oke, (~compat).astype(float), np.nan))

    # ── DAVISON: the couple's own chart afflicted — Venus-Saturn or Sun-Moon hard contacts in the Davison
    dav_vs_hard = c("davison_chart:davint_venus_saturn_0") + c("davison_chart:davint_venus_saturn_90") \
        + c("davison_chart:davint_venus_saturn_180")
    v("davison_venus_saturn_afflicted", dav_vs_hard)
    v("davison_luminaries_hard", c("davison_chart:davint_sun_moon_90") + c("davison_chart:davint_sun_moon_180"))

    # ── NUMEROLOGY: the popular rules by their own arithmetic
    v("bio_incompatibility", 1.0 - c("numerology_extra:bio_compat_mean"))
    v("numerology_root_disharmony", 1.0 - c("numerology_extra:combined_root_harmonious"))
    v("loshu_shared_missing", c("numerology_extra:loshu_shared_missing"))

    return np.column_stack(V), N


def main():
    tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    Vtr, N = verdicts(tr, Z, "train"); Vte, _ = verdicts(te, Z, "test")
    print(f"  {len(N)} tradition verdicts · train {len(tr):,} · test {len(te):,}", flush=True)
    print("\n  each verdict ALONE on the held-out test (oriented: higher = tradition says worse):")
    for j, nm in enumerate(N):
        okj = np.isfinite(Vte[:, j])
        if okj.sum() > 300 and len(np.unique(yte[okj])) > 1:
            print(f"    {nm:<34} test AUC {G.auc(yte[okj], Vte[okj, j]):.4f}   (n={int(okj.sum()):,})", flush=True)
    # THE ONLY TRAINED STEP: non-negative weights over the verdicts' within-corpus ranks, and nothing else.
    # Two rules keep it fully explainable:
    #   1. A verdict enters ONLY in the direction its tradition states (weights are >= 0 on the tradition's
    #      own "bad for the marriage" pole). A tradition that anti-predicts here goes to weight zero — it is
    #      never flipped, because a flipped tradition is no longer that tradition.
    #   2. A MISSING verdict says nothing. The first version filled missing with the mid-rank, and the fit
    #      promptly put 100% of its weight on the one verdict whose MISSINGNESS pattern (day-precision, hence
    #      era) predicted the label — a channel no tradition states. Now the weights are fitted where the
    #      verdicts are jointly present, and a couple is scored by the RENORMALISED weighted mean of the
    #      verdicts that exist for them.
    Rtr, Rte = G.rankfeat(Vtr), G.rankfeat(Vte)
    # Fit the weights through the SAME renormalised function that scores a couple, over EVERY training row.
    # Fitting on the jointly-covered subset put 95% of the mass on one day-precision-only tradition and left
    # half the corpus unscorable; optimising the deployed function itself forces weight onto the traditions
    # that can actually see each stratum (year-capable ones for year-only couples).
    from scipy.optimize import minimize
    Mtr = np.isfinite(Vtr)
    R0 = np.where(Mtr, Rtr, 0.0)
    def unpack(th):
        return np.maximum(th[:Vtr.shape[1]], 0.0), th[-2], th[-1]
    def obj(th):
        w_, a_, c_ = unpack(th)
        denom = Mtr @ w_
        ok = denom > 1e-9
        sc = np.zeros(len(ytr)); sc[ok] = (R0 @ w_)[ok] / denom[ok]
        z = a_ * sc + c_
        pz = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        eps = 1e-7
        ll = -(ytr * np.log(pz + eps) + (1 - ytr) * np.log(1 - pz + eps))
        return float(np.mean(np.where(ok, ll, 0.0))) + 1e-3 * float((w_ ** 2).sum())
    th0 = np.concatenate([np.full(Vtr.shape[1], 0.5), [4.0, -3.0]])
    res = minimize(obj, th0, method="L-BFGS-B",
                   bounds=[(0, None)] * Vtr.shape[1] + [(0.1, 50), (-10, 10)], options={"maxiter": 400})
    w, _, _ = unpack(res.x)
    def score(R, V):
        # availability comes from the VERDICTS, not the rank matrix — rankfeat fills its gaps with 0.0, so a
        # mask on R sees every verdict as present and the renormalisation silently never happens
        m = np.isfinite(V)
        wm = (np.where(m, R, 0.0) * w).sum(1)
        avail = (m * w).sum(1)
        return np.where(avail > 1e-9, wm / avail, np.nan)
    zt = score(Rte, Vte)
    m = np.isfinite(zt)
    auc = G.auc(yte[m], zt[m])
    print(f"\n  test coverage: {m.mean():.0%} of couples receive a verdict score")
    print(f"\n  weights fitted through the renormalised scorer on all {len(ytr):,} training rows")
    print(f"\n  VERDICT STACK — only the weights are trained · TEST AUC (read once): {auc:.4f}")
    print("  the traditions history weights most:")
    for i in np.argsort(-w):
        if w[i] > 0:
            print(f"    {N[i]:<34} {100*w[i]/max(w.sum(),1e-9):.0f}%")
    np.savez_compressed(os.path.expanduser("~/.artamatch-dev/verdict_stack.npz"),
                        w=w, names=np.array(N, dtype=object),
                        rank_ref=Vtr)                                # reference distribution for ranking new couples
    json.dump({"names": N, "weights": w.tolist(), "test_auc": float(auc)},
              open(os.path.expanduser("~/.artamatch-dev/verdict_stack.json"), "w"), indent=1)
    print("  saved")


if __name__ == "__main__":
    main()
