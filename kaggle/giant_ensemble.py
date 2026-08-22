"""
giant_ensemble.py — every system in the catalogue, one ensemble, and a contribution table that means something.

Runs on a Kaggle GPU kernel. Three things happen here:

  1. EVERY family is built and turned into forward-chained out-of-fold member scores (GPU XGBoost).
  2. They are combined two ways — a grouped non-negative rank stacker over the member scores, and one giant
     GPU-boosted model over every raw feature at once.
  3. Each family's CONTRIBUTION is measured three ways, and each of those twice.

On (3): a contribution table is the easiest thing in this project to get wrong. Every one of these systems is
keyed on a cycle of a birth year, and a cycle of the birth year is a cycle of the AGE — so a naive table ranks
the families by which of them best re-encodes how old the two people were, which is not what anybody means by
"contribution". So every figure is reported twice:

  RAW        held-out AUC, the number a leaderboard would show.
  CONTROLLED AUC pooled within cells that hold both ages (1y), the era (5y) and the exact pattern of which of
             the three dates are fully recorded. In that cell the age gap, each age and the wedding year all
             score exactly 0.5000, so whatever is left is not them.

and by three methods, because each answers a different question:

  ADD-ONE-IN   plain ages alone, plus this family. "What does it know on its own?"
  LEAVE-ONE-OUT  the full ensemble minus this family. "What would we lose without it?" — the honest marginal
               number, and usually far smaller than add-one-in, because the families are hugely redundant.
  WEIGHT SHARE the fraction of the non-negative stacker's mass this family's members take.

The yardstick printed beside the table is WHICH DAY OF THE MONTH the wedding was written down on — a pure
bookkeeping artefact with no astrological content. A family that does not clear that has found nothing.
"""
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

ON_KAGGLE = os.path.isdir("/kaggle/working")
DATA = os.environ.get("AQ_DATA", "/kaggle/input/artamatch-giant/" if ON_KAGGLE else os.path.expanduser("~/.artamatch-dev"))
CODE = os.environ.get("AQ_CODE", "/kaggle/input/artamatch-iv-code/sidereal" if ON_KAGGLE else os.path.expanduser("~/Studio/artamatch/research/sidereal"))
OUT = os.environ.get("AQ_OUT", "/kaggle/working" if ON_KAGGLE else os.path.expanduser("~/.artamatch-dev/giant"))
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, CODE)

QS = (0.40, 0.55, 0.70, 0.85, 1.0)
CELL, ERA = 1.0, 5.0


def gpu_params():
    """XGBoost on the T4 if there is one, silently on CPU if not — a kernel must not die for lack of a card."""
    try:
        import subprocess
        subprocess.run(["nvidia-smi"], capture_output=True, timeout=20, check=True)
        return dict(device="cuda", tree_method="hist"), True
    except Exception:
        return dict(device="cpu", tree_method="hist"), False


# ── the measurement ───────────────────────────────────────────────────────────────────────────────────────────
def auc(y, s):
    f = np.isfinite(s)
    y, s = y[f], s[f]
    if len(np.unique(y)) < 2:
        return float("nan")
    o = np.argsort(s, kind="mergesort"); s, y = s[o], y[o]
    r = np.arange(1, len(s) + 1, dtype=float)
    new = np.ones(len(s), bool); new[1:] = s[1:] != s[:-1]
    gid = np.cumsum(new) - 1
    r = (np.bincount(gid, weights=r) / np.bincount(gid))[gid]
    npos = y.sum(); nneg = len(y) - npos
    return float((r[y == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def matched_auc(y, s, *cells, min_cell=12):
    """AUC pooled inside cells only, as a within-cell rank sum with ties averaged."""
    ok = np.isfinite(s)
    for c in cells:
        ok = ok & np.isfinite(c)
    if ok.sum() < min_cell:
        return float("nan"), 0
    key = np.zeros(int(ok.sum()), dtype=np.int64)
    for c in cells:
        key = key * 100000 + c[ok].astype(np.int64)
    _, key = np.unique(key, return_inverse=True)
    yy = y[ok].astype(np.float64); ss = s[ok].astype(np.float64)
    o = np.lexsort((ss, key)); key, ss, yy = key[o], ss[o], yy[o]
    ncell = int(key[-1]) + 1
    counts = np.bincount(key, minlength=ncell)
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    rank = (np.arange(len(key)) - starts[key] + 1).astype(np.float64)
    new = np.ones(len(key), bool); new[1:] = (key[1:] != key[:-1]) | (ss[1:] != ss[:-1])
    gid = np.cumsum(new) - 1
    rank = (np.bincount(gid, weights=rank) / np.bincount(gid))[gid]
    npos = np.bincount(key, weights=yy, minlength=ncell); nneg = counts - npos
    rsum = np.bincount(key, weights=rank * yy, minlength=ncell)
    valid = (npos > 0) & (nneg > 0) & (counts >= min_cell)
    if not valid.any():
        return float("nan"), 0
    a = (rsum - npos * (npos + 1) / 2) / np.maximum(npos * nneg, 1)
    w = (npos * nneg)[valid]
    return float((a[valid] * w).sum() / w.sum()), int(w.sum())


def rankfeat(X):
    F = np.zeros_like(X, dtype=float)
    for j in range(X.shape[1]):
        f = np.isfinite(X[:, j])
        if f.sum() > 1:
            v = X[f, j]; r = np.argsort(np.argsort(v)) / max(1, len(v) - 1)
            F[f, j] = r - 0.5
    return F


def fit_nonneg(F, y, sw, lam=1e-3):
    """Non-negative logistic stack — monotone by construction, so no member can be used backwards."""
    from scipy.optimize import minimize
    n, m = F.shape; yy = 2.0 * y - 1.0
    def obj(th):
        w, b = th[:m], th[m]; z = F @ w + b
        p = 1 / (1 + np.exp(-yy * z)); g = -(yy * (1 - p)) * sw
        return (float(np.sum(sw * np.logaddexp(0, -yy * z)) / sw.sum() + lam * w @ w),
                np.concatenate([F.T @ g / sw.sum() + 2 * lam * w, [g.sum() / sw.sum()]]))
    r = minimize(obj, np.zeros(m + 1), jac=True, method="L-BFGS-B",
                 bounds=[(0, None)] * m + [(None, None)], options={"maxiter": 3000})
    return r.x[:m], r.x[m]


# ── the families ──────────────────────────────────────────────────────────────────────────────────────────────
# Every module was written with its own build() signature, so each gets a small adapter returning (X, names) for
# one half of the data. PHYSICS is deliberately absent: it needs birthplaces, and the operator removed location
# from this edition, so there is nothing honest for it to read.
WEB = os.environ.get("AQ_WEB", "/kaggle/input/artamatch-ephemeris" if ON_KAGGLE else os.path.expanduser("~/Studio/artamatch/web"))
_SW = {}


def swe():
    """The Swiss Ephemeris shim, loaded once. Three families need it; the rest must not pay for it."""
    if "sw" not in _SW:
        for cand in (WEB, os.path.join(os.path.dirname(CODE.rstrip("/")), "web"), os.path.expanduser("~/Studio/artamatch/web")):
            if os.path.exists(os.path.join(cand, "sweshim.py")) and cand not in sys.path:
                sys.path.insert(0, cand)
        import sweshim as SW
        eph = sorted(glob.glob(os.path.join(WEB, "**", "ephem4.bin"), recursive=True)) or [os.path.join(WEB, "ephem4.bin")]
        tab = sorted(glob.glob(os.path.join(WEB, "**", "tables.json"), recursive=True)) or [os.path.join(WEB, "tables.json")]
        SW.load(eph[0], tab[0])
        _SW["sw"] = SW
        _SW["codes"] = {n: getattr(SW, n.upper()) for n in
                        ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto")}
        _SW["cache"] = {}
    return _SW["sw"], _SW["codes"], _SW["cache"]


def _thetas(Z, half):
    s1, s2 = list(Z["slots"])
    return Z[f"theta_{s1}_{half}"], Z[f"theta_{s2}_{half}"], Z[f"theta_wed_{half}"], list(Z["bodies"])


def _ad_world(mod):
    return lambda df, Z, half: __import__(mod).build(df, Z, half)


def _ad_maya(df, Z, half):
    return __import__("maya_members_iv").build(df)


def _ad_calendar(df, Z, half):
    """calendar_members_iv.build returns a DICT of named blocks, not (X, names)."""
    blocks = __import__("calendar_members_iv").build(df)
    cols, names = [], []
    for nm, X in blocks.items():
        X = np.asarray(X, dtype=float)
        cols.append(X); names += [f"{nm}_{i}" for i in range(X.shape[1])]
    return np.column_stack(cols).astype(np.float32), names


def _ad_geometry(df, Z, half):
    A, B, W, bodies = _thetas(Z, half)
    return __import__("geometry_members_iv").build(A, B, W, bodies)


def _ad_electional(df, Z, half):
    """Returns (electional block, its names, a separate deep-numerology block) — three values, not two."""
    SW, codes, cache = swe()
    E, keys, N = __import__("electional_members_iv").build(df, SW, codes, cache)
    E = np.asarray(E, dtype=float); N = np.asarray(N, dtype=float)
    names = list(keys) + [f"numerology_{i}" for i in range(N.shape[1])]
    return np.column_stack([E, N]).astype(np.float32), names


def _ad_zodiac(df, Z, half):
    """aya_diff_tables gives {system: {year: offset}}, so the offset has to be looked up PER ROW by wedding year,
    and sign_feats returns a bare array — it has no names of its own."""
    m = __import__("zodiac_members_iv")
    A, B, W, bodies = _thetas(Z, half)
    j = {b: bodies.index(b) for b in ("sun", "moon", "venus")}
    yrs = pd.to_numeric(df.start.str[:4], errors="coerce").fillna(1900).to_numpy(dtype=float)
    SW, _, _ = swe()
    tabs = m.aya_diff_tables(SW, np.unique(yrs))
    FEAT = ["sun_hi", "sun_lo", "sun_dist", "sun_same", "sun_elem", "sun_mode", "moon_hi", "moon_lo", "moon_dist",
            "moon_same", "moon_elem", "sun_a_moon_b", "sun_b_moon_a", "ven_hi", "ven_lo", "ven_dist",
            "wed_sun_sign", "wed_sun_reach"]
    cols, names = [], []
    for aya, tab in tabs.items():
        d = np.array([tab.get(v, 0.0) for v in yrs], dtype=float)
        X = m.sign_feats(A[:, j["sun"]] - d, B[:, j["sun"]] - d, A[:, j["moon"]] - d, B[:, j["moon"]] - d,
                         A[:, j["venus"]] - d, B[:, j["venus"]] - d, W[:, j["sun"]] - d)
        cols.append(np.asarray(X, dtype=float)); names += [f"{aya}_{f}" for f in FEAT]
    return np.column_stack(cols).astype(np.float32), names


def _ad_extra(df, Z, half):
    """progressed() returns a DICT of per-slot (n, 5) longitude blocks."""
    swe()                                                     # progressed() imports sweshim itself
    m = __import__("extra_members_iv")
    out = m.progressed(df)
    BOD = ["sun", "moon", "mercury", "venus", "mars"]
    cols, names = [], []
    for slot, X in (out.items() if isinstance(out, dict) else [("prog", out)]):
        X = np.asarray(X, dtype=float)
        cols.append(X); names += [f"prog_{slot}_{BOD[i] if i < len(BOD) else i}" for i in range(X.shape[1])]
    lp = np.column_stack([[m.lifepath(v) for v in df[c]] for c in ("dob_a", "dob_b", "start")]).astype(float)
    cols.append(lp); names += ["lifepath_a", "lifepath_b", "lifepath_start"]
    return np.column_stack(cols).astype(np.float32), names


FAMILIES = [
    ("world",      _ad_world("world_members_iv"),  "rokuyō · tong shu · vivāha muhūrta · fasts · aṣṭakūṭa · chinese zodiac · nine star ki · weton · pawukon"),
    ("world2",     _ad_world("world2_members_iv"), "mangal doṣa · daśakūṭa · vimśottarī · kua/ba zhai · gunghap · bazi · aztec · ogham · runic · coptic · igbo"),
    ("world3",     _ad_world("world3_members_iv"), "손 없는 날 · widow year · yatyaza · wan phra · tu b'av · не в мае · moon-nights · rāhu kālam · akan · parsi"),
    ("calendar",   _ad_calendar,                   "jalali · islamic · hebrew · julian · chinese sexagenary"),
    ("maya",       _ad_maya,                       "tzolkʼin · haabʼ · long count · lords of the night"),
    ("geometry",   _ad_geometry,                   "draconic · antiscia · fixed stars · harmonics 5/7/9 · hour-marginalised signs"),
    ("electional", _ad_electional,                 "wedding sky: tithi · retrogrades · eclipse season · nakṣatra · planetary day and hour"),
    ("zodiac",     _ad_zodiac,                     "sign systems across five ayanamsas"),
    ("extra",      _ad_extra,                      "progressions · numerology life path"),
]


def build_families(tr, te, Z):
    """Build every family on both halves. A family that fails is REPORTED and skipped, never silently dropped —
    a missing family would otherwise show up as a contribution of zero, which reads as a finding."""
    out, failed = {}, []
    for fam, adapt, desc in FAMILIES:
        try:
            Xtr, names = adapt(tr, Z, "train")
            Xte, _ = adapt(te, Z, "test")
            Xtr = np.asarray(Xtr, dtype=np.float32); Xte = np.asarray(Xte, dtype=np.float32)
            if Xtr.shape[1] != Xte.shape[1]:
                raise ValueError(f"train/test width mismatch {Xtr.shape[1]} vs {Xte.shape[1]}")
            out[fam] = (Xtr, Xte, names, desc)
            log(f"  {fam:<11} {Xtr.shape[1]:>5} features   {desc[:70]}")
        except Exception as e:
            failed.append((fam, f"{type(e).__name__}: {e}"))
            log(f"  {fam:<11} SKIPPED — {type(e).__name__}: {e}")
    if failed:
        log(f"  !! {len(failed)} of {len(FAMILIES)} families did not build; they are ABSENT from the table below,")
        log("     which is not the same as contributing nothing")
    return out, failed


def forward_oof(X, Xte, y, later, cuts, params, seed=0):
    """Forward-chained OOF: fit on everything older than the cut, score what comes after. Never the reverse —
    fitting on the future and scoring the past lets an era clock read its own answer."""
    import xgboost as xgb
    rows = np.isfinite(X).any(1)
    s_tr = np.full(len(y), np.nan)
    P = dict(n_estimators=260, learning_rate=0.05, max_depth=4, min_child_weight=40, subsample=0.8,
             colsample_bytree=0.7, reg_lambda=20.0, verbosity=0, n_jobs=4, **params)
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]
        blk = rows & (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True)
        fit = rows & (later <= lo)
        if fit.sum() < 500 or len(np.unique(y[fit])) < 2 or not blk.any():
            continue
        c = xgb.XGBClassifier(random_state=seed, **P); c.fit(X[fit], y[fit])
        s_tr[blk] = c.predict_proba(X[blk])[:, 1]
    c = xgb.XGBClassifier(random_state=seed, **P)
    if rows.sum() >= 500 and len(np.unique(y[rows])) >= 2:
        c.fit(X[rows], y[rows])
        s_te = np.full(len(Xte), np.nan); rte = np.isfinite(Xte).any(1)
        if rte.any():
            s_te[rte] = c.predict_proba(Xte[rte])[:, 1]
    else:
        s_te = np.full(len(Xte), np.nan)
    return s_tr, s_te


def main():
    import xgboost as xgb
    params, on_gpu = gpu_params()
    log(f"xgboost {xgb.__version__} · {'T4 GPU' if on_gpu else 'CPU (no card found)'}")

    # Find the three inputs wherever they landed. A Kaggle dataset flattens or nests unpredictably depending on
    # how it was uploaded, and a kernel that dies on a path is a wasted GPU session.
    def find(name):
        direct = os.path.join(DATA, name)
        if os.path.exists(direct):
            return direct
        hits = sorted(glob.glob(os.path.join(DATA, "**", name), recursive=True))
        if not hits:
            raise SystemExit(f"could not find {name} anywhere under {DATA}")
        return hits[0]
    tr = pd.read_csv(find("train.csv"), dtype=str)
    te = pd.read_csv(find("test.csv"), dtype=str)
    phases = find("phases.npz")
    log(f"inputs: {find('train.csv')} · {phases}")
    Z = np.load(phases, allow_pickle=True)
    y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1)
    cuts = [np.quantile(later, q) for q in QS]
    pn = list(Z["plain_names"]); s1, s2 = list(Z["slots"])
    P, Pte = Z["plain_train"], Z["plain_test"]
    log(f"train {len(tr):,} · test {len(te):,} · positives {y.mean():.1%}")

    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    plain = lambda p: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]),
                                       np.abs(p[:, ia] - p[:, ib]), p[:, iy]])
    PLAIN_N = ["age_older", "age_younger", "age_gap", "start_year"]

    # the control cells
    aa, ab = P[:, ia], P[:, ib]
    ca = np.floor(np.fmax(aa, ab) / CELL); cb = np.floor(np.fmin(aa, ab) / CELL); ce = np.floor(P[:, iy] / ERA)
    full = lambda c: tr[c].fillna("").str.match(r"^\d{4}-(?!00)\d{2}-(?!00)\d{2}$").to_numpy().astype(float)
    prec = full("dob_a") * 4 + full("dob_b") * 2 + full("start")
    scored = later > cuts[0]
    CELLS = (ca, cb, ce, prec)
    def both(s):
        f = np.isfinite(s) & scored
        m, pairs = matched_auc(y[f], s[f], *[c[f] for c in CELLS])
        return auc(y[f], s[f]), m, pairs

    log("building families")
    fams, failed = build_families(tr, te, Z)
    if not fams:
        log("no family built — nothing to ensemble"); return

    # ── references, including the one that matters
    log("references")
    refs = {}
    for nm, sc in (("the age gap alone", -np.abs(aa - ab)),
                   ("the older partner's age", -np.fmax(aa, ab)),
                   ("the start year alone", P[:, iy]),
                   ("WHICH DAY OF THE MONTH the wedding was written down on",
                    pd.to_numeric(tr["start"].str[8:10], errors="coerce").to_numpy(dtype=float))):
        r, m, _ = both(sc); refs[nm] = dict(raw=r, controlled=m)
        log(f"  {nm:<56} raw {r:.4f}  controlled {m:.4f}")
    YARD = refs["WHICH DAY OF THE MONTH the wedding was written down on"]["controlled"]

    # ── level 1: one member score per family, plus the plain-ages baseline
    log("level 1 — forward-chained OOF member per family (GPU)")
    Xp, Xpte = plain(P), plain(Pte)
    members, mte, mnames, mfam = [], [], [], []
    s, st = forward_oof(Xp, Xpte, y, later, cuts, params)
    members.append(s); mte.append(st); mnames.append("plain ages"); mfam.append("plain")
    r, m, _ = both(s); log(f"  {'plain ages (the baseline everything is judged against)':<56} raw {r:.4f}  controlled {m:.4f}")
    for fam, (Xtr, Xte, names, desc) in fams.items():
        # the family ALONE (no ages) — what it knows by itself
        s, st = forward_oof(Xtr, Xte, y, later, cuts, params)
        members.append(s); mte.append(st); mnames.append(f"{fam} alone"); mfam.append(fam)
        r, m, _ = both(s)
        log(f"  {fam + ' alone':<56} raw {r:.4f}  controlled {m:.4f}")
    S = np.column_stack(members); Ste = np.column_stack(mte)

    # ── level 2a: the giant model — every raw feature from every family, at once
    log("level 2a — the giant model over every raw feature at once (GPU)")
    allX = np.column_stack([Xp] + [fams[f][0] for f in fams])
    allXte = np.column_stack([Xpte] + [fams[f][1] for f in fams])
    allnames = PLAIN_N + [f"{f}:{n}" for f in fams for n in fams[f][2]]
    log(f"  {allX.shape[0]:,} rows x {allX.shape[1]:,} features")
    g_tr, g_te = forward_oof(allX, allXte, y, later, cuts, params)
    r_g, m_g, _ = both(g_tr)
    log(f"  {'GIANT (all raw features)':<56} raw {r_g:.4f}  controlled {m_g:.4f}")

    # ── level 2b: the non-negative rank stack over the member scores
    log("level 2b — non-negative rank stack over the family members")
    oof = np.isfinite(S).any(1) & scored
    F = rankfeat(S[oof]); sw = np.ones(int(oof.sum()))
    w, b = fit_nonneg(F, y[oof], sw)
    z = np.full(len(y), np.nan); z[oof] = F @ w + b
    r_s, m_s, _ = both(z)
    log(f"  {'STACK (non-negative over members)':<56} raw {r_s:.4f}  controlled {m_s:.4f}")
    wshare = {}
    tot = w.sum() if w.sum() > 0 else 1.0
    for fam in set(mfam):
        wshare[fam] = float(sum(w[i] for i in range(len(w)) if mfam[i] == fam) / tot)

    # ── contribution, three ways, each of them twice
    log("contribution — add-one-in, leave-one-out, weight share")
    contrib = {}
    base_r, base_m, _ = both(members[0])                      # plain ages alone
    for fam in fams:
        # ADD-ONE-IN: plain ages + this family's raw features, nothing else
        Xa = np.column_stack([Xp, fams[fam][0]]); Xat = np.column_stack([Xpte, fams[fam][1]])
        s_add, _ = forward_oof(Xa, Xat, y, later, cuts, params)
        a_r, a_m, _ = both(s_add)
        # LEAVE-ONE-OUT: the giant model without this family
        keep = [f for f in fams if f != fam]
        Xl = np.column_stack([Xp] + [fams[f][0] for f in keep])
        Xlt = np.column_stack([Xpte] + [fams[f][1] for f in keep])
        s_lo, _ = forward_oof(Xl, Xlt, y, later, cuts, params)
        l_r, l_m, _ = both(s_lo)
        contrib[fam] = dict(
            desc=fams[fam][3], n_features=int(fams[fam][0].shape[1]),
            add_raw=a_r, add_controlled=a_m, add_gain_raw=a_r - base_r, add_gain_controlled=a_m - base_m,
            lofo_raw=l_r, lofo_controlled=l_m, lofo_cost_raw=r_g - l_r, lofo_cost_controlled=m_g - l_m,
            weight_share=wshare.get(fam, 0.0))
        log(f"  {fam:<11} alone {a_m:.4f} · adds {a_m - base_m:+.4f} · removing it costs {m_g - l_m:+.4f} · weight {wshare.get(fam,0):5.1%}")

    # ── the report
    lines = []
    P_ = lines.append
    P_("=" * 108)
    P_("THE GIANT ENSEMBLE — every date-keyed marriage system in the catalogue, and what each one contributes")
    P_("=" * 108)
    P_("")
    P_(f"{'REFERENCE':<58}{'RAW':>12}{'CONTROLLED':>14}")
    P_(f"{'':<58}{'held-out':>12}{'ages+era+prec flat':>14}")
    P_("-" * 108)
    for nm, v in refs.items():
        P_(f"  {nm:<56}{v['raw']:>12.4f}{v['controlled']:>14.4f}")
    P_("")
    P_(f"  {'plain ages alone (the baseline)':<56}{base_r:>12.4f}{base_m:>14.4f}")
    P_(f"  {'STACK (non-negative over family members)':<56}{r_s:>12.4f}{m_s:>14.4f}")
    P_(f"  {'GIANT (every raw feature at once)':<56}{r_g:>12.4f}{m_g:>14.4f}")
    P_("")
    P_("-" * 108)
    P_(f"{'CONTRIBUTION':<13}{'feats':>7}{'alone':>9}{'adds':>9}{'LOFO cost':>11}{'weight':>9}   {'vs the bookkeeping yardstick':<30}")
    P_(f"{'':<13}{'':>7}{'(ctrl)':>9}{'(ctrl)':>9}{'(ctrl)':>11}{'share':>9}")
    P_("-" * 108)
    for fam, c in sorted(contrib.items(), key=lambda kv: -kv[1]["add_controlled"]):
        d = c["add_controlled"] - YARD
        beats = f"beats it by {d:+.4f}" if d > 0 else f"below it by {d:+.4f}"
        P_(f"  {fam:<11}{c['n_features']:>7}{c['add_controlled']:>9.4f}{c['add_gain_controlled']:>+9.4f}"
           f"{c['lofo_cost_controlled']:>+11.4f}{c['weight_share']:>9.1%}   {beats:<30}")
    P_("-" * 108)
    P_("")
    if failed:
        P_("FAMILIES THAT DID NOT BUILD, and are therefore absent above rather than contributing zero:")
        for fam, why in failed:
            P_(f"  {fam:<11} {why}")
        P_("")
    P_(f"The yardstick is WHICH DAY OF THE MONTH the wedding was written down on: {YARD:.4f} controlled.")
    P_("It carries no astrological content whatsoever. Read every row above against it.")
    P_("")
    P_("Columns: 'alone' is plain ages plus that family and nothing else. 'add gain' is what it adds to the ages.")
    P_("'LOFO cost' is what the giant model loses when that family is removed — the honest marginal number, and")
    P_("far smaller than 'add gain' wherever the families are redundant with each other, which is nearly always.")
    rep = "\n".join(lines)
    print("\n" + rep, flush=True)
    open(os.path.join(OUT, "contribution_report.txt"), "w").write(rep + "\n")
    json.dump(dict(references=refs, contribution=contrib, yardstick=YARD, failed=dict(failed),
                   stack=dict(raw=r_s, controlled=m_s), giant=dict(raw=r_g, controlled=m_g),
                   baseline=dict(raw=base_r, controlled=base_m), on_gpu=on_gpu,
                   members=[dict(name=n, family=f) for n, f in zip(mnames, mfam)]),
              open(os.path.join(OUT, "contribution.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(OUT, "giant_members.npz"), S_train=S, S_test=Ste,
                        names=np.array(mnames), families=np.array(mfam),
                        giant_train=g_tr, giant_test=g_te, stack_train=z)
    log(f"wrote contribution_report.txt, contribution.json and giant_members.npz to {OUT}")


if __name__ == "__main__":
    main()
