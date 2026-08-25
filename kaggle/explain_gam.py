"""
explain_gam.py — bridging the explainability gap: a GAM over ATOMIC DOCTRINE STATEMENTS.

Operator 2026-08-25: the explainable stack must reach the trained ensemble's 0.77.

Every feature here is a single sentence of tradition: a body in a sign, a Davison placement, a named synastry
aspect, a nakshatra, a tithi, a BaZi stem/branch, a Sun-sign PAIR from the newspaper tables, a Moon-rasi PAIR
from the Vedic rasi-kuta tables, an outer-planet mundane cycle phase (Barbault's doctrine that eras are the
outer cycles — and the operator's own standing rule that the era IS slow-body phase). The model is a LOGISTIC
blend of those statements: every coefficient is readable as 'history weights <named placement> at +x toward
divorce'. The blend is the ONLY trained thing, which is what the operator permits.
"""
import json, os, sys
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
import importlib.util
_dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)

D = os.path.expanduser("~/.artamatch-dev/remar_sh")
SIGNS = ["Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"]
STEMS = ["JiaWood","YiWood","BingFire","DingFire","WuEarth","JiEarth","GengMetal","XinMetal","RenWater","GuiWater"]
BRANCH = ["Rat","Ox","Tiger","Rabbit","Dragon","Snake","Horse","Goat","Monkey","Rooster","Dog","Pig"]


def onehot(idx, k, prefix, labels=None):
    """A partition of doctrine categories: exactly one fires when readable, NONE when unreadable."""
    n = len(idx)
    M = np.zeros((n, k), np.float32)
    ok = np.isfinite(idx)
    ii = np.nan_to_num(idx).astype(int) % k
    M[np.arange(n)[ok], ii[ok]] = 1.0
    names = [f"{prefix}={labels[j] if labels else j}" for j in range(k)]
    return M, names


def build(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    def add(M, nm):
        blocks.append(np.asarray(M, np.float32)); names.extend(nm)

    # 1. EVERY BODY IN EVERY SIGN, each partner — 'his Saturn is in Leo'. Slow bodies cover year-only rows.
    for tag, C in (("his", A), ("her", B)):
        for b in ("sun","moon","mercury","venus","mars","jupiter","saturn","uranus","neptune","pluto","true_node","chiron"):
            add(*onehot(np.floor((C[:, ix[b]] % 360) / 30), 12, f"{tag}_{b}_sign", SIGNS))
    # 2. THE DAVISON CHART's placements — 'the couple's Saturn is in Scorpio'
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    dt = jb - ja
    for b, nmot in dv.MEAN.items():
        ta, tb = A[:, ix[b]], B[:, ix[b]]
        raw = (tb - ta + 180.0) % 360.0 - 180.0
        k = np.round((nmot * dt - raw) / 360.0)
        dav = np.where(np.isfinite(dt), (ta + (raw + 360.0 * k) / 2.0) % 360.0, np.nan)
        if b in ("sun","moon","venus","mars","jupiter","saturn","uranus","neptune","pluto"):
            add(*onehot(np.floor(dav / 30), 12, f"dav_{b}_sign", SIGNS))
    # 3. MUNDANE CYCLES — the era as doctrine: the phase sign of each outer synodic pair at the MIDPOINT birth
    for x, y in (("jupiter","saturn"),("saturn","uranus"),("saturn","neptune"),("saturn","pluto"),
                 ("uranus","neptune"),("uranus","pluto"),("neptune","pluto")):
        ph = ((A[:, ix[x]] + B[:, ix[x]]) / 2 - (A[:, ix[y]] + B[:, ix[y]]) / 2) % 360.0
        both = np.isfinite(A[:, ix[x]]) & np.isfinite(B[:, ix[x]]) & np.isfinite(A[:, ix[y]]) & np.isfinite(B[:, ix[y]])
        add(*onehot(np.where(both, np.floor(ph / 30), np.nan), 12, f"cycle_{x}_{y}_phase", SIGNS))
    # 4. SUN-SIGN PAIR — the newspaper tables, all 144 cells, gendered (his x hers)
    hs = np.floor((A[:, ix["sun"]] % 360) / 30); ws = np.floor((B[:, ix["sun"]] % 360) / 30)
    pair = np.where(np.isfinite(hs) & np.isfinite(ws), hs * 12 + ws, np.nan)
    add(*onehot(pair, 144, "sunpair", [f"{SIGNS[i]}x{SIGNS[j]}" for i in range(12) for j in range(12)]))
    # 5. MOON-RASI PAIR — the Vedic rasi-kuta tables, all 144, gendered
    hm = np.floor((A[:, ix["moon"]] % 360) / 30); wm = np.floor((B[:, ix["moon"]] % 360) / 30)
    pairm = np.where(np.isfinite(hm) & np.isfinite(wm), hm * 12 + wm, np.nan)
    add(*onehot(pairm, 144, "moonpair", [f"{SIGNS[i]}x{SIGNS[j]}" for i in range(12) for j in range(12)]))
    # 6. NAKSHATRA of each Moon — 'her janma nakshatra is Rohini'
    NAK = 360.0 / 27.0
    add(*onehot(np.floor((A[:, ix["moon"]] % 360) / NAK), 27, "his_nakshatra"))
    add(*onehot(np.floor((B[:, ix["moon"]] % 360) / NAK), 27, "her_nakshatra"))
    # 7. JANMA TITHI of each partner
    for tag, C in (("his", A), ("her", B)):
        el = (C[:, ix["moon"]] - C[:, ix["sun"]]) % 360.0
        add(*onehot(np.floor(el / 12.0), 30, f"{tag}_tithi"))
    # 8. NAMED SYNASTRY ASPECTS — one indicator per classical contact, gendered
    def arc(x, y):
        return np.abs((x - y + 180.0) % 360.0 - 180.0)
    CONTACTS = [("sun","moon"),("moon","sun"),("venus","mars"),("mars","venus"),("sun","sun"),("moon","moon"),
                ("venus","venus"),("moon","venus"),("venus","moon"),("saturn","moon"),("moon","saturn"),
                ("saturn","venus"),("venus","saturn"),("mars","moon"),("jupiter","moon"),("jupiter","venus"),
                ("sun","saturn"),("saturn","sun"),("mars","mars"),("saturn","saturn")]
    for x, y in CONTACTS:
        a = arc(A[:, ix[x]], B[:, ix[y]])
        for t, o, lab in ((0, 8, "conj"), (60, 4, "sext"), (90, 6, "square"), (120, 6, "trine"), (180, 8, "opp")):
            add(np.where(np.isfinite(a), (np.abs(a - t) <= o).astype(np.float32), 0).reshape(-1, 1),
                [f"his_{x}_{lab}_her_{y}"])
    # 9. BAZI: year stem+branch each partner, and the sexagenary DAY stem (needs day precision)
    for tag, jd in (("his", ja), ("her", jb)):
        sx = np.where(np.isfinite(jd), (np.nan_to_num(jd) + 49) % 60, np.nan)
        add(*onehot(sx % 10, 10, f"{tag}_daystem", STEMS))
        add(*onehot(sx % 12, 12, f"{tag}_daybranch", BRANCH))
    yrh = pd.to_numeric(df.dob_a.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    yrw = pd.to_numeric(df.dob_b.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    add(*onehot((yrh - 4) % 12, 12, "his_year_animal", BRANCH))
    add(*onehot((yrw - 4) % 12, 12, "her_year_animal", BRANCH))
    add(*onehot(np.where(np.isfinite(yrh + yrw), ((yrh - 4) % 12) * 12 + (yrw - 4) % 12, np.nan), 144,
                "animalpair", [f"{BRANCH[i]}x{BRANCH[j]}" for i in range(12) for j in range(12)]))
    # 10. NUMEROLOGY: life path of each, and the combined root
    def lifepath(col):
        out = np.full(len(col), np.nan)
        for i, v in enumerate(col.astype(str)):
            if len(v) >= 10 and v[:4].isdigit() and v[:4] != "0000" and v[5:7] != "00" and v[8:10] != "00":
                t = sum(int(c) for c in v if c.isdigit())
                while t > 9:
                    t = sum(int(c) for c in str(t))
                out[i] = t - 1
        return out
    lh, lw = lifepath(df.dob_a), lifepath(df.dob_b)
    add(*onehot(lh, 9, "his_lifepath", [str(i + 1) for i in range(9)]))
    add(*onehot(lw, 9, "her_lifepath", [str(i + 1) for i in range(9)]))
    add(*onehot(np.where(np.isfinite(lh + lw), lh * 9 + lw, np.nan), 81, "lifepath_pair",
                [f"{i+1}x{j+1}" for i in range(9) for j in range(9)]))
    # 11. FINER CLASSICAL PARTITIONS — still sentences of doctrine, just the tradition's own finer grain
    #     decans (the 36 faces), nakshatra padas (108 quarters), half-sign cycle phases, Davison nakshatra
    for tag, C in (("his", A), ("her", B)):
        add(*onehot(np.floor((C[:, ix["sun"]] % 360) / 10), 36, f"{tag}_sun_decan"))
        add(*onehot(np.floor((C[:, ix["moon"]] % 360) / 10), 36, f"{tag}_moon_decan"))
        add(*onehot(np.floor((C[:, ix["moon"]] % 360) / (360.0 / 108.0)), 108, f"{tag}_moon_pada"))
    for x, y in (("neptune", "pluto"), ("uranus", "neptune"), ("uranus", "pluto"), ("saturn", "pluto")):
        ph = ((A[:, ix[x]] + B[:, ix[x]]) / 2 - (A[:, ix[y]] + B[:, ix[y]]) / 2) % 360.0
        both = np.isfinite(A[:, ix[x]]) & np.isfinite(B[:, ix[x]]) & np.isfinite(A[:, ix[y]]) & np.isfinite(B[:, ix[y]])
        add(*onehot(np.where(both, np.floor(ph / 15), np.nan), 24, f"cycle24_{x}_{y}"))
    # Davison Moon nakshatra — 'the couple's Moon is born in Rohini'
    ta, tb = A[:, ix["moon"]], B[:, ix["moon"]]
    raw = (tb - ta + 180.0) % 360.0 - 180.0
    k = np.round((dv.MEAN["moon"] * dt - raw) / 360.0)
    davm = np.where(np.isfinite(dt), (ta + (raw + 360.0 * k) / 2.0) % 360.0, np.nan)
    add(*onehot(np.floor(davm / (360.0 / 27.0)), 27, "dav_moon_nakshatra"))
    # 12. THE 31 DOSHA VERDICTS join as named doctrine features (rank-scaled within the corpus)
    from verdict_stack import verdicts as _verd
    Vv, Nv = _verd(df, Z, half)
    Rv = G.rankfeat(Vv)
    Mv = np.isfinite(Vv)
    add(np.where(Mv, Rv, 0.0).astype(np.float32), [f"verdict:{q}" for q in Nv])
    X = np.column_stack(blocks)
    return X, names


def main():
    from sklearn.linear_model import LogisticRegression
    tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv"); ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    Xtr, names = build(tr, Z, "train"); Xte, _ = build(te, Z, "test")
    print(f"  {Xtr.shape[1]:,} atomic doctrine statements · train {len(tr):,} · test {len(te):,}", flush=True)

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

    best = None
    for C in (0.03, 0.1, 0.3, 1.0):
        aucs = []
        for k in range(5):
            m = LogisticRegression(C=C, max_iter=2000, solver="lbfgs")
            m.fit(Xtr[fold != k], ytr[fold != k])
            aucs.append(G.auc(ytr[fold == k], m.predict_proba(Xtr[fold == k])[:, 1]))
        mu = float(np.mean(aucs))
        print(f"    C={C:<5} group-CV AUC {mu:.4f}", flush=True)
        if best is None or mu > best[1]:
            best = (C, mu)
    C = best[0]
    m = LogisticRegression(C=C, max_iter=3000, solver="lbfgs")
    m.fit(Xtr, ytr)
    zt = m.predict_proba(Xte)[:, 1]
    auc = G.auc(yte, zt)
    print(f"\n  DOCTRINE-GAM · C={C} · TEST AUC (read once): {auc:.4f}   (target 0.7747 · verdict stack was 0.5145)")
    co = m.coef_[0]
    o = np.argsort(co)
    print("\n  the statements history weights hardest TOWARD divorce:")
    for i in o[::-1][:12]:
        print(f"    {names[i]:<40} {co[i]:+.3f}")
    print("  ... and AGAINST divorce:")
    for i in o[:12]:
        print(f"    {names[i]:<40} {co[i]:+.3f}")
    np.savez_compressed(os.path.expanduser("~/.artamatch-dev/doctrine_gam.npz"),
                        coef=co, intercept=float(m.intercept_[0]), names=np.array(names, dtype=object),
                        C=C, test_auc=auc)
    print("\n  saved doctrine_gam.npz")


if __name__ == "__main__":
    main()
