"""
v7_fit.py — every remaining doctrine hypothesis as indicators, and the relaxed non-negative sparse fit.

Bank additions over v6 (~1,600 statements): the full Ashtakoota PAIR MATRICES (yoni 14x14, gana 3x3, nadi 3x3,
varna 4x4, vashya 5x5, tara 9x9, rajju 5x5 — the published tables, cell by cell), Venus- and Mars-sign 144-cell
pair tables, element/modality/polarity pairs, the COMPOSITE midpoint chart (Ebertin) with placements and its
own afflictions, Sun/Moon-midpoint contacts (cosmobiology's marriage indicator), antiscia contacts, retrograde
and combustion flags, karana and nitya-yoga partitions, vara pairs, birthday numbers with karmic-debt and
master flags, the Chinese 3/6/9-year gap taboos, Kua 9x9, Nine-Star 9x9, natal dasha-lord 9x9, month-pillar
branches and Na Yin pairs.

Model: Lasso(positive=True) for SELECTION, then — the relaxed stage — a non-negative logistic refit on the
survivors only, removing the L1 shrinkage bias while staying linear, non-negative and sparse. Plain vs relaxed
chosen by group-CV; one test read for the winner.
"""
import json, os, sys
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
sys.path.insert(0, os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs"))
sys.path.insert(0, os.path.expanduser("~/.artaquest-dev/wt/am-pages/web"))
import giant_ensemble as G, explain_gam as EG
import v6_fit as V6
import world_members_iv as WM
D = os.path.expanduser("~/.artamatch-dev/remar_sh")
SIGNS = EG.SIGNS; BRANCH = EG.BRANCH; STEMS = EG.STEMS
YONI_ARR = np.array(WM.YONI); GANA_ARR = WM.GANA_ARR; NADI_ARR = WM.NADI_ARR
VARNA_ARR = np.array(WM.VARNA); VASHYA_ARR = np.array(WM.VASHYA)
RAJJU_ARR = None
try:
    import world2_members_iv as W2
    RAJJU_ARR = W2.RAJJU_ARR
except Exception:
    pass
NAYIN = [3,1,0,2,3,1,4,2,3,0,4,2,1,0,4,3,1,0,2,3,1,4,2,3,0,4,2,1,0,4]
import importlib.util
_dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)

_SPEED = {}
def speed_flags(df):
    """Retrograde flags per partner from the ephemeris itself, cached per (date, body)."""
    import sweshim as SW
    if not _SPEED:
        SW.load(os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/ephem4.bin"),
                os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/tables.json"))
        SW.set_sid_mode(SW.SIDM_LAHIRI)
        _SPEED["sw"] = SW
        _SPEED["codes"] = {"mercury": SW.MERCURY, "venus": SW.VENUS, "mars": SW.MARS,
                           "jupiter": SW.JUPITER, "saturn": SW.SATURN}
        _SPEED["cache"] = {}
    SW = _SPEED["sw"]; cache = _SPEED["cache"]
    out = {f"{t}_{b}_retro": np.zeros(len(df), np.float32)
           for t in ("his", "her") for b in _SPEED["codes"]}
    for t, col in (("his", df.dob_a), ("her", df.dob_b)):
        for i, v in enumerate(col.astype(str)):
            if len(v) >= 10 and v[:4].isdigit() and v[:4] != "0000" and v[5:7] != "00" and v[8:10] != "00":
                key = v[:10]
                if key not in cache:
                    try:
                        jd = SW.julday(int(v[:4]), int(v[5:7]), int(v[8:10]), 12.0)
                        cache[key] = {b: SW.calc_ut(jd, c)[3] for b, c in _SPEED["codes"].items()}
                    except Exception:
                        cache[key] = {}
                for b, sp in cache[key].items():
                    if sp < 0:
                        out[f"{t}_{b}_retro"][i] = 1.0
    return out


def additions(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    add = lambda M, nm: (blocks.append(np.asarray(M, np.float32)), names.extend(nm))
    oh = EG.onehot
    NAK = 360.0 / 27.0
    na = np.floor((A[:, ix["moon"]] % 360) / NAK); nb = np.floor((B[:, ix["moon"]] % 360) / NAK)
    ra = np.floor((A[:, ix["moon"]] % 360) / 30); rb = np.floor((B[:, ix["moon"]] % 360) / 30)
    okn = np.isfinite(na) & np.isfinite(nb)
    def tab_pair(arr, va, vb, k, pref, labels=None):
        pa = np.where(np.isfinite(va), arr[np.nan_to_num(va).astype(int) % len(arr)], np.nan)
        pb = np.where(np.isfinite(vb), arr[np.nan_to_num(vb).astype(int) % len(arr)], np.nan)
        pr = np.where(np.isfinite(pa) & np.isfinite(pb), pa * k + pb, np.nan)
        add(*oh(pr, k * k, pref, [f"{(labels[i] if labels else i)}x{(labels[j] if labels else j)}"
                                  for i in range(k) for j in range(k)]))
    tab_pair(YONI_ARR, na, nb, 14, "yonipair")
    tab_pair(GANA_ARR, na, nb, 3, "ganapair", ["Deva", "Manushya", "Rakshasa"])
    tab_pair(NADI_ARR, na, nb, 3, "nadipair", ["Adi", "Madhya", "Antya"])
    tab_pair(VARNA_ARR, ra, rb, 4, "varnapair")
    tab_pair(VASHYA_ARR, ra, rb, 5, "vashyapair")
    if RAJJU_ARR is not None:
        tab_pair(RAJJU_ARR, na, nb, 5, "rajjupair")
    tcount = np.where(okn, ((na - nb) % 27 + 1) % 9, np.nan)
    tcount2 = np.where(okn, ((nb - na) % 27 + 1) % 9, np.nan)
    add(*oh(np.where(okn, tcount * 9 + tcount2, np.nan), 81, "tarapair"))
    dl = np.where(np.isfinite(na), na % 9, np.nan); dlb = np.where(np.isfinite(nb), nb % 9, np.nan)
    add(*oh(np.where(np.isfinite(dl) & np.isfinite(dlb), dl * 9 + dlb, np.nan), 81, "dashalordpair"))
    for b in ("venus", "mars"):
        sa = np.floor((A[:, ix[b]] % 360) / 30); sb = np.floor((B[:, ix[b]] % 360) / 30)
        add(*oh(np.where(np.isfinite(sa) & np.isfinite(sb), sa * 12 + sb, np.nan), 144, f"{b}pair",
                [f"{SIGNS[i]}x{SIGNS[j]}" for i in range(12) for j in range(12)]))
    for b in ("sun", "moon", "venus"):
        sa = np.floor((A[:, ix[b]] % 360) / 30); sb = np.floor((B[:, ix[b]] % 360) / 30)
        ok = np.isfinite(sa) & np.isfinite(sb)
        add(*oh(np.where(ok, (sa % 4) * 4 + sb % 4, np.nan), 16, f"{b}_elempair",
                [f"{e1}x{e2}" for e1 in ("Fire","Earth","Air","Water") for e2 in ("Fire","Earth","Air","Water")]))
        add(*oh(np.where(ok, (sa % 3) * 3 + sb % 3, np.nan), 9, f"{b}_modepair",
                [f"{m1}x{m2}" for m1 in ("Cardinal","Fixed","Mutable") for m2 in ("Cardinal","Fixed","Mutable")]))
        add(*oh(np.where(ok, (sa % 2) * 2 + sb % 2, np.nan), 4, f"{b}_polpair",
                ["YangxYang", "YangxYin", "YinxYang", "YinxYin"]))
    # COMPOSITE (Ebertin midpoint) chart: circular midpoint per body, placements + own afflictions
    comp = {}
    for b in ("sun", "moon", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"):
        ta, tb = A[:, ix[b]], B[:, ix[b]]
        m = (ta + ((tb - ta + 180.0) % 360.0 - 180.0) / 2.0) % 360.0
        comp[b] = np.where(np.isfinite(ta) & np.isfinite(tb), m, np.nan)
        add(*oh(np.floor(comp[b] / 30), 12, f"comp_{b}_sign", SIGNS))
    arc = lambda x, y: np.abs((x - y + 180.0) % 360.0 - 180.0)
    for x, y in (("sun","moon"),("venus","saturn"),("venus","mars"),("moon","saturn"),("sun","saturn")):
        a = arc(comp[x], comp[y])
        for t, o, lab in ((0, 8, "conj"), (90, 6, "square"), (180, 8, "opp"), (120, 6, "trine")):
            add(np.where(np.isfinite(a), (np.abs(a - t) <= o).astype(np.float32), 0).reshape(-1, 1),
                [f"comp_{x}_{lab}_{y}"])
    # SUN/MOON MIDPOINT contacts — cosmobiology's marriage axis
    for tag, C1, C2 in (("his", A, B), ("her", B, A)):
        sm = (C1[:, ix["sun"]] + ((C1[:, ix["moon"]] - C1[:, ix["sun"]] + 180) % 360 - 180) / 2) % 360
        for b in ("sun", "moon", "venus"):
            a = arc(sm, C2[:, ix[b]])
            add(np.where(np.isfinite(a), (a <= 3.0).astype(np.float32), 0).reshape(-1, 1),
                [f"{tag}_sunmoon_mid_conj_other_{b}"])
    # ANTISCIA contacts (solstitial mirror)
    for tag, C1, C2 in (("his", A, B), ("her", B, A)):
        for b in ("sun", "moon", "venus"):
            ant = (180.0 - C1[:, ix[b]]) % 360.0
            for b2 in ("sun", "moon", "venus"):
                a = arc(ant, C2[:, ix[b2]])
                add(np.where(np.isfinite(a), (a <= 3.0).astype(np.float32), 0).reshape(-1, 1),
                    [f"{tag}_{b}_antiscia_other_{b2}"])
    # COMBUSTION
    for tag, C in (("his", A), ("her", B)):
        for b in ("mercury", "venus", "mars", "moon"):
            a = arc(C[:, ix[b]], C[:, ix["sun"]])
            add(np.where(np.isfinite(a), (a <= 8.5).astype(np.float32), 0).reshape(-1, 1),
                [f"{tag}_{b}_combust"])
    # RETROGRADES (ephemeris speed, day-precision only)
    for nm, v in speed_flags(df).items():
        add(v.reshape(-1, 1), [nm])
    # PANCHANGA partitions: karana class, nitya yoga, vara + vara pair
    for tag, C in (("his", A), ("her", B)):
        el = (C[:, ix["moon"]] - C[:, ix["sun"]]) % 360.0
        kidx = np.floor(el / 6.0)
        kt = np.where(kidx == 0, 0, np.where(kidx >= 57, 8 + (kidx - 57), (kidx - 1) % 7 + 1))
        add(*oh(np.where(np.isfinite(el), kt, np.nan), 11, f"{tag}_karana"))
        yg = np.floor(((C[:, ix["moon"]] + C[:, ix["sun"]]) % 360.0) / NAK)
        add(*oh(yg, 27, f"{tag}_nityayoga"))
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    wa = np.where(np.isfinite(ja), (np.nan_to_num(ja)) % 7, np.nan)
    wb = np.where(np.isfinite(jb), (np.nan_to_num(jb)) % 7, np.nan)
    add(*oh(wa, 7, "his_vara")); add(*oh(wb, 7, "her_vara"))
    add(*oh(np.where(np.isfinite(wa) & np.isfinite(wb), wa * 7 + wb, np.nan), 49, "varapair"))
    # NUMEROLOGY: birthday number, attitude, karmic debt, masters; gap taboos; same-date flags
    def dparts(col):
        y = pd.to_numeric(col.str[:4], errors="coerce").replace(0, np.nan)
        mo = pd.to_numeric(col.str[5:7], errors="coerce").replace(0, np.nan)
        dd = pd.to_numeric(col.str[8:10], errors="coerce").replace(0, np.nan)
        return y.to_numpy(float), mo.to_numpy(float), dd.to_numpy(float)
    ya, ma, da = dparts(df.dob_a); yb, mb, db = dparts(df.dob_b)
    red = lambda v: np.where(np.isfinite(v), 1 + (np.nan_to_num(v) - 1) % 9, np.nan)
    for tag, dd_, mo_ in (("his", da, ma), ("her", db, mb)):
        add(*oh(np.where(np.isfinite(dd_), dd_ - 1, np.nan), 31, f"{tag}_birthday"))
        add(*oh(red(dd_ + mo_) - 1, 9, f"{tag}_attitude"))
        add(np.column_stack([np.where(np.isfinite(dd_), np.isin(dd_, [13, 14, 16, 19]).astype(np.float32), 0),
                             np.where(np.isfinite(dd_), np.isin(dd_, [11, 22]).astype(np.float32), 0)]),
            [f"{tag}_karmic_debt_day", f"{tag}_master_day"])
    gap = np.abs(ya - yb)
    add(*oh(np.where(np.isfinite(gap) & (gap <= 15), gap, np.nan), 16, "gap_years"))
    add(np.column_stack([np.where(np.isfinite(gap), np.isin(gap, [3, 6, 9]).astype(np.float32), 0)]),
        ["gap_369_taboo"])
    same_bd = ((df.dob_a.str[5:] == df.dob_b.str[5:]) & (df.dob_a.str[5:7] != "00")).to_numpy(float)
    same_m = ((df.dob_a.str[5:7] == df.dob_b.str[5:7]) & (df.dob_a.str[5:7] != "00")).to_numpy(float)
    add(np.column_stack([same_bd, same_m]), ["same_birthday", "same_birth_month"])
    # KUA pair, NINE-STAR pair (year-based, Li Chun approximated at Feb 4)
    def kua_arr(y, mo, dd, male):
        yy = np.where((mo < 2) | ((mo == 2) & (dd < 4)), y - 1, y)
        s = np.where(np.isfinite(yy), 1 + (np.nan_to_num(yy) - 1) % 9, np.nan)
        def digsum(v):
            v = np.nan_to_num(v).astype(int)
            return np.array([1 + (sum(int(c) for c in str(x)) - 1) % 9 if x > 0 else 0 for x in v], float)
        ds = digsum(yy)
        k = np.where(male, 11 - ds, 4 + ds)
        k = 1 + (k - 1) % 9
        k = np.where(k == 5, np.where(male, 2, 8), k)
        return np.where(np.isfinite(yy), k, np.nan)
    ka = kua_arr(ya, ma if ma is not None else 7, da, True)
    kb = kua_arr(yb, mb, db, False)
    add(*oh(np.where(np.isfinite(ka) & np.isfinite(kb), (ka - 1) * 9 + (kb - 1), np.nan), 81, "kuapair"))
    ninestar = lambda y: np.where(np.isfinite(y),
                                  1 + (11 - np.array([1 + (sum(int(c) for c in str(int(v))) - 1) % 9 if np.isfinite(v) and v > 0 else 1 for v in y]) - 1) % 9, np.nan)
    sa9, sb9 = ninestar(ya), ninestar(yb)
    add(*oh(np.where(np.isfinite(sa9) & np.isfinite(sb9), (sa9 - 1) * 9 + (sb9 - 1), np.nan), 81, "ninestarpair"))
    # CHINESE month pillar branch + Na Yin of the day pillar
    mbra = np.where(np.isfinite(ma), np.where(da >= 5, ma, ma - 1) % 12, np.nan)
    mbrb = np.where(np.isfinite(mb), np.where(db >= 5, mb, mb - 1) % 12, np.nan)
    add(*oh(mbra, 12, "his_monthbranch", BRANCH)); add(*oh(mbrb, 12, "her_monthbranch", BRANCH))
    sxa = np.where(np.isfinite(ja), (np.nan_to_num(ja) + 49) % 60, np.nan)
    sxb = np.where(np.isfinite(jb), (np.nan_to_num(jb) + 49) % 60, np.nan)
    nya = np.where(np.isfinite(sxa), np.array(NAYIN)[np.nan_to_num(sxa).astype(int) // 2 % 30], np.nan)
    nyb = np.where(np.isfinite(sxb), np.array(NAYIN)[np.nan_to_num(sxb).astype(int) // 2 % 30], np.nan)
    EL = ["Wood", "Fire", "Earth", "Metal", "Water"]
    add(*oh(nya, 5, "his_nayin", EL)); add(*oh(nyb, 5, "her_nayin", EL))
    add(*oh(np.where(np.isfinite(nya) & np.isfinite(nyb), nya * 5 + nyb, np.nan), 25, "nayinpair",
            [f"{a}x{b}" for a in EL for b in EL]))
    return np.column_stack(blocks).astype(np.float32), names


def main():
    from sklearn.linear_model import Lasso
    tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv"); ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(float)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X6, n6 = V6.bank(tr, Z, "train"); X6t, _ = V6.bank(te, Z, "test")
    XA, nA = additions(tr, Z, "train"); XAt, _ = additions(te, Z, "test")
    Xtr = np.column_stack([X6, XA]); Xte = np.column_stack([X6t, XAt])
    names = n6 + nA
    print(f"  v7 bank: {Xtr.shape[1]:,} doctrine indicators ({len(nA):,} new)", flush=True)

    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    gid = pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]
    fold = np.random.default_rng(7).integers(0, 5, gid.max() + 1)[gid]

    yi = ytr.astype(int)
    results = {}
    for alpha in (1e-4, 1.5e-4, 2e-4, 3e-4, 5e-4):
        oofP = np.full(len(ytr), np.nan); oofR = np.full(len(ytr), np.nan); nz = []
        for k in range(5):
            m = Lasso(alpha=alpha, positive=True, max_iter=6000)
            m.fit(Xtr[fold != k], ytr[fold != k])
            oofP[fold == k] = Xtr[fold == k] @ m.coef_ + m.intercept_
            surv = np.where(m.coef_ > 0)[0]; nz.append(len(surv))
            if len(surv) >= 2:
                w, b = G.fit_nonneg(Xtr[fold != k][:, surv], yi[fold != k], np.ones(int((fold != k).sum())))
                oofR[fold == k] = Xtr[fold == k][:, surv] @ w + b
        aP, aR = G.auc(yi, oofP), G.auc(yi, oofR)
        results[(alpha, "plain")] = aP; results[(alpha, "relaxed")] = aR
        print(f"    alpha={alpha:<7} CV plain {aP:.4f} · RELAXED {aR:.4f} · survivors ~{int(np.mean(nz))}", flush=True)
    (alpha, mode), cv = max(results.items(), key=lambda kv: kv[1])
    print(f"\n  CV winner: {mode} at alpha={alpha} (CV {cv:.4f})")
    m = Lasso(alpha=alpha, positive=True, max_iter=10000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    if mode == "relaxed":
        w, b = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
        zt = Xte[:, surv] @ w + b
        weights = {names[i]: float(v) for i, v in zip(surv, w) if v > 0}
        b0 = float(b)
    else:
        zt = Xte @ m.coef_ + m.intercept_
        weights = {names[i]: float(m.coef_[i]) for i in surv}
        b0 = float(m.intercept_)
    auc = G.auc(yte, zt)
    print(f"  v7 {mode} · {len(weights)} surviving rules of {Xtr.shape[1]:,} · TEST AUC (read once): {auc:.4f}")
    print(f"  (v6 linear was 0.7635 · the SOTA trained ensemble 0.7747)")
    o = sorted(weights.items(), key=lambda kv: -kv[1])
    print("\n  heaviest new-bank survivors:")
    for k_, v in o[:20]:
        tag = " ←NEW" if k_ in set(nA) else ""
        print(f"    {k_:<44} +{v:.4f}{tag}")
    ztr = (Xtr[:, surv] @ (w if mode == 'relaxed' else m.coef_[surv])) + b0
    qs = np.quantile(ztr, np.linspace(0, 1, 11)); qs[0], qs[-1] = -1e9, 1e9
    calib = [{"lo": float(qs[k]), "hi": float(qs[k+1]), "share": float(ytr[(ztr >= qs[k]) & (ztr < qs[k+1])].mean())}
             for k in range(10)]
    json.dump({"model": f"ArtaMatch v7 — non-negative sparse ({mode})", "alpha": alpha, "mode": mode,
               "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4), "intercept": b0,
               "n_bank": int(Xtr.shape[1]), "n_surviving": len(weights),
               "weights": dict(o), "calibration_deciles": calib},
              open(os.path.expanduser("~/.artamatch-dev/v7_model.json"), "w"), indent=1)
    print("\n  saved v7_model.json")


if __name__ == "__main__":
    main()
