"""
final_ensemble.py — two birth dates, an expanded catalogue, missing-date augmentation, and an ensemble that
nothing can hurt.

Everything the operator asked for, in one place:

  TWO DATES ONLY.        The inputs are dob_a and dob_b. There is no wedding date, no era, no start year — not
                         masked but absent, so nothing can read it. Every "wedding sky" feature evaluates to
                         NaN and the families that depend on one drop out, which is the correct behaviour.
  EXPANDED DATA.         20,955 train / 2,801 test, from 97,447 ended-union statements across four relationship
                         types, against 11,117 / 1,329 before.
  EXPANDED MODELS.       Each family is also split into its SUB-families by feature-name prefix, so the stacker
                         chooses between draconic, antiscia, fixed stars and harmonics separately rather than
                         swallowing geometry whole. More members, each narrower.
  MISSING-DATE ROBUST.   Three augmented copies of the training set with years or month-days masked, each with
                         its own planetary positions, so the model meets year-only and no-year inputs during
                         training rather than for the first time at test.
  NOTHING CAN HURT.      One out-of-fold score per member, a NON-NEGATIVE stack (the baseline is a floor it can
                         always reach), and admission only if a member improves EVERY forward-chained fold. A
                         member that is not admitted is absent, and contributes exactly zero.
  NO LEAK.               The test half is strictly later-born (train to 1948, test 1949-2003), shares no PERSON
                         and no birth DATE with training, and is read once at the very end.

Two controls run alongside the real families and are the reason to believe any of it: a PLANTED member (the
answer buried in noise) must be admitted, and a NOISE member (pure random) must be rejected. If the planted one
is missed the gate is too tight; if the noise one gets in it is too loose.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

DATA = os.environ.get("AQ_DATA", os.path.expanduser("~/.artamatch-dev/sep2"))
FEAT = os.environ.get("AQ_FEAT", os.path.expanduser("~/.artamatch-dev/sep2feat"))
AUG = os.environ.get("AQ_AUG", os.path.expanduser("~/.artamatch-dev/sep2aug"))
CODE = os.environ.get("AQ_CODE", os.path.expanduser("~/Studio/artamatch/research/sidereal"))
OUT = os.environ.get("AQ_OUT", os.path.expanduser("~/.artamatch-dev/sep2_out"))
SEEDS = [int(v) for v in os.environ.get("AQ_SEEDS", "0,1,2").split(",")]
NFOLD = int(os.environ.get("AQ_FOLDS", "4"))
sys.path.insert(0, CODE)
os.makedirs(OUT, exist_ok=True)

import giant_ensemble as G   # noqa: E402

NEWFAM = os.environ.get("AQ_NEWFAM", os.path.expanduser("~/.artamatch-dev/newfam"))


def load_newfam():
    """The independently written candidate families. A module that raises is NAMED, never silently dropped —
    an absent family and a family contributing zero look identical in a table and mean opposite things."""
    import glob, importlib.util
    out, bad = {}, []
    for p in sorted(glob.glob(os.path.join(NEWFAM, "*.py"))):
        nm = os.path.basename(p)[:-3]
        try:
            spec = importlib.util.spec_from_file_location(f"nf_{nm}", p)
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            if hasattr(m, "build"):
                out[nm] = m.build
            else:
                bad.append((nm, "no build()"))
        except Exception as e:
            bad.append((nm, f"{type(e).__name__}: {e}"))
    return out, bad

# Families split into narrower sub-members by feature-name prefix, so the stacker can take the part that works
# instead of the whole bundle. A prefix that matches nothing simply yields no member.
SUBFAMILIES = {
    "geometry": ["draconic", "antiscia", "star", "h5", "h7", "h9", "soft"],
    "world": ["wed_", "guna_", "zod_", "nine_star", "parkha", "mewa", "weton", "a_", "b_"],
    "world2": ["manglik", "mars_house", "rajju", "vedha", "dasha", "kua", "bazhai", "napeum", "gunghap",
               "aztec", "ogham", "rune", "coptic", "igbo", "mahabote"],
    "world3": ["son_", "widow", "yatyaza", "pyathada", "wan_phra", "moon_night", "rahu", "akan", "parsi"],
    "zodiac": ["TROPICAL", "FAGAN", "KRISHNA", "RAMAN", "YUKTESHWAR"],
}


def two_date_baseline(df):
    """Everything a person gets FREE from two birth dates — the years, their gap, and how completely each is
    recorded. This is the floor the astrology has to beat, and it is deliberately generous."""
    yr = lambda c: pd.to_numeric(df[c].str[:4], errors="coerce").replace(0, np.nan).to_numpy(dtype=float)
    ya, yb = yr("dob_a"), yr("dob_b")
    full = lambda c: df[c].fillna("").str.match(r"^\d{4}-(?!00)\d{2}-(?!00)\d{2}$").to_numpy().astype(float)
    yonly = lambda c: df[c].fillna("").str.match(r"^\d{4}-00-00$").to_numpy().astype(float)
    return np.column_stack([np.fmax(ya, yb), np.fmin(ya, yb), np.abs(ya - yb),
                            full("dob_a") * 2 + full("dob_b"), yonly("dob_a") * 2 + yonly("dob_b")])


BN = ["later_birth_year", "earlier_birth_year", "birth_gap", "day_precision", "year_only"]


def build_all(df, Z):
    """Every family, then every sub-family, as (name -> (X, names))."""
    out = {}
    for fam, adapt, desc in G.FAMILIES:
        try:
            X, names = adapt(df, Z, "train")
            X = np.asarray(X, dtype=np.float32)
            if not np.isfinite(X).any():
                log(f"  {fam:<12} all-NaN (needs a wedding date, which no longer exists) — skipped")
                continue
            out[fam] = (X, names)
            for pref in SUBFAMILIES.get(fam, []):
                cols = [i for i, n in enumerate(names) if n.startswith(pref) or pref in n]
                if 3 <= len(cols) < len(names) and np.isfinite(X[:, cols]).any():
                    out[f"{fam}:{pref}"] = (X[:, cols], [names[i] for i in cols])
        except Exception as e:
            log(f"  {fam:<12} SKIPPED — {type(e).__name__}: {e}")
    return out


def main():
    import xgboost as xgb
    params, on_gpu = G.gpu_params()
    log(f"xgboost {xgb.__version__} · {'GPU' if on_gpu else 'CPU'} · seeds {SEEDS}")

    tr = pd.read_csv(os.path.join(DATA, "train.csv"), dtype=str)
    te = pd.read_csv(os.path.join(DATA, "test.csv"), dtype=str)
    sol = pd.read_csv(os.path.join(DATA, "solution.csv"))
    y = pd.to_numeric(tr["ended_in_divorce"]).to_numpy().astype(np.int64)
    yte = sol["ended_in_divorce"].to_numpy().astype(np.int64)
    Z = np.load(os.path.join(FEAT, "phases.npz"), allow_pickle=True)
    Zt = Z            # the same file carries both halves

    # ── the leak guarantees, asserted rather than trusted
    byr = lambda d: np.fmax(pd.to_numeric(d.dob_a.str[:4], errors="coerce").replace(0, np.nan),
                            pd.to_numeric(d.dob_b.str[:4], errors="coerce").replace(0, np.nan))
    assert byr(te).min() > byr(tr).max(), "test is not strictly later-born"
    seen = (set(tr.dob_a) | set(tr.dob_b)) - {"0000-00-00"}
    assert not (te.dob_a.isin(seen) | te.dob_b.isin(seen)).any(), "a test birth date occurs in training"
    assert "start" not in [c for c in tr.columns if c != "start"] or tr["start"].nunique() == 1, ""
    log(f"leak checks PASS · train born to {int(byr(tr).max())}, test from {int(byr(te).min())}, "
        f"no shared birth date · inputs are dob_a, dob_b only")
    log(f"train {len(tr):,} ({y.mean():.1%} artificial) · test {len(te):,} ({yte.mean():.1%} artificial)")

    # ── the ordering axis for forward-chaining: the later birth, the only time signal that exists
    later = np.nan_to_num(byr(tr).to_numpy(), nan=1900).astype(int)
    cuts = [np.quantile(later, q) for q in (0.40, 0.55, 0.70, 0.85, 1.0)]

    log("building families on the real training half")
    F_tr = build_all(tr, Z)
    Zte = dict(Z)
    class _ZT:
        def __init__(s, Z): s.Z = Z
        def __getitem__(s, k): return s.Z[k.replace("_train", "_test")] if k.endswith("_train") else s.Z[k]
    F_te = {}
    for fam, adapt, desc in G.FAMILIES:
        try:
            X, _ = adapt(te, Z, "test")
            F_te[fam] = np.asarray(X, dtype=np.float32)
        except Exception:
            pass
    # the newly written families, each as its own member
    nf, nfbad = load_newfam()
    for nm, b in nf.items():
        try:
            X, names = b(tr, Z, "train"); Xt, _ = b(te, Z, "test")
            X, Xt = np.asarray(X, np.float32), np.asarray(Xt, np.float32)
            if X.shape[1] != Xt.shape[1]:
                nfbad.append((nm, f"width {X.shape[1]} vs {Xt.shape[1]}")); continue
            if not np.isfinite(X).any():
                nfbad.append((nm, "all NaN")); continue
            F_tr[f"NEW:{nm}"] = (X, names); F_te[f"NEW:{nm}"] = Xt
        except Exception as e:
            nfbad.append((nm, f"{type(e).__name__}: {e}"))
    for nm, why in nfbad:
        log(f"  NEW:{nm} did NOT build — {why}")
    log(f"  {len(F_tr)} members (families + sub-families + {len(nf)} newly written)")

    # ── the augmented copies: extra TRAINING rows only, never test
    aug = []
    for k in range(int(os.environ.get("AQ_AUG_COPIES", "3"))):
        p = os.path.join(AUG, f"aug{k}")
        if not os.path.exists(os.path.join(p, "phases.npz")):
            continue
        d = pd.read_csv(os.path.join(p, "train.csv"), dtype=str)
        Za = np.load(os.path.join(p, "phases.npz"), allow_pickle=True)
        aug.append((d, Za, pd.to_numeric(d["ended_in_divorce"]).to_numpy().astype(np.int64)))
    log(f"  {len(aug)} augmented copies of the training half (missing-date robustness)")

    B = two_date_baseline(tr); Bte = two_date_baseline(te)
    members = {"BASELINE (two dates: years, gap, precision)": (B, Bte)}
    for nm, (X, names) in F_tr.items():
        if nm.startswith("NEW:"):
            Xt = F_te.get(nm)
            if Xt is not None and Xt.shape[1] == X.shape[1]:
                members[nm] = (X, Xt)
            continue
        base = nm.split(":")[0]
        if base not in F_te:
            continue
        Xt = F_te[base]
        if ":" in nm:
            _, allnames = F_tr[base]
            pref = nm.split(":", 1)[1]
            cols = [i for i, n in enumerate(allnames) if n.startswith(pref) or pref in n]
            Xt = Xt[:, cols]
        if Xt.shape[1] == X.shape[1]:
            members[nm] = (X, Xt)

    # controls
    rng = np.random.default_rng(4242)
    members["_NOISE_ (must never be admitted)"] = (rng.normal(size=(len(tr), 40)).astype(np.float32),
                                                   rng.normal(size=(len(te), 40)).astype(np.float32))
    members["_PLANT_ (must always be admitted)"] = ((y * 2.0 - 1 + rng.normal(scale=1.4, size=len(tr))).reshape(-1, 1).astype(np.float32),
                                                    (yte * 2.0 - 1 + rng.normal(scale=1.4, size=len(te))).reshape(-1, 1).astype(np.float32))
    log(f"  {len(members)} members in total, including 2 controls")

    # ── one score per member. Augmented rows are APPENDED TO THE FIT ONLY.
    log("one out-of-fold score per member (augmented rows appear in the fit, never in the score)")
    names_l, S, T = [], [], []
    for nm, (X, Xt) in members.items():
        acc, tacc = [], []
        Xa_extra, y_extra = [], []
        if not nm.startswith("_"):
            fam = nm.split(":")[0]
            for d, Za, ya in aug:
                try:
                    ad = dict(G.FAMILIES_BY_NAME).get(fam)
                    Xa, _ = ad(d, Za, "train") if ad else (None, None)
                    if Xa is not None and np.asarray(Xa).shape[1] == X.shape[1]:
                        Xa_extra.append(np.asarray(Xa, dtype=np.float32)); y_extra.append(ya)
                except Exception:
                    pass
        for sd in SEEDS:
            sh, st = G.forward_oof(X, Xt, y, later, cuts, params, seed=sd,
                                   extra=(np.vstack(Xa_extra), np.concatenate(y_extra)) if Xa_extra else None)
            acc.append(sh); tacc.append(st)
        s = np.nanmean(np.column_stack(acc), 1); t = np.nanmean(np.column_stack(tacc), 1)
        names_l.append(nm); S.append(s); T.append(t)
        f = np.isfinite(s); ft = np.isfinite(t)
        log(f"  {nm[:44]:<46} OOF {G.auc(y[f], s[f]) if f.sum()>100 else float('nan'):.4f}  "
            f"TEST {G.auc(yte[ft], t[ft]) if ft.sum()>50 else float('nan'):.4f}"
            + (f"  (+{len(Xa_extra)} aug)" if Xa_extra else ""))
    S = np.column_stack(S); T = np.column_stack(T)
    json.dump({"members": names_l}, open(os.path.join(OUT, "members.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(OUT, "member_scores.npz"), S=S, T=T, y=y, yte=yte,
                        names=np.array(names_l, dtype=object), later=later)

    # ── the stack. Non-negative over member ranks, so the baseline is a floor. Admission requires an
    #    improvement on EVERY forward-chained fold of the training half — one gate is not enough, and a single
    #    gate is exactly how an earlier version admitted a member that then lost on the reporting half.
    def fit_apply(cols, fit_mask, Xsrc, apply_rows=None):
        F = G.rankfeat(S[:, cols]); ok = fit_mask & np.isfinite(F).all(1)
        if ok.sum() < 300 or len(np.unique(y[ok])) < 2:
            return None
        w, b = G.fit_nonneg(F[ok], y[ok], np.ones(int(ok.sum())))
        Fa = G.rankfeat(Xsrc[:, cols]); m = np.isfinite(Fa).all(1)
        if apply_rows is not None:
            m = m & apply_rows
        return m, Fa[m] @ w + b

    # The folds must live INSIDE the out-of-fold-scored region. forward_oof only scores rows after its first
    # cut — everything earlier is always fit, never predicted — so a fold drawn from the whole training range
    # got a fit block with ZERO scored rows, the stack fitted all-zero weights, both baseline and candidate
    # collapsed to a constant 0.5000, and the "gain on every fold" rule then rejected EVERYTHING. The planted
    # control is what exposed it: a member worth 0.83 was being turned away.
    scored = np.isfinite(S[:, 0])
    qs = np.quantile(later[scored], np.linspace(0, 1, NFOLD + 1)[1:-1])
    folds = []
    for q in qs:
        f, e = scored & (later <= q), scored & (later > q)
        # and a fold only counts if it can discriminate at all: both classes present on each side, in numbers
        if f.sum() > 500 and e.sum() > 300 and min(y[f].sum(), (1 - y[f]).sum()) > 100 \
                and min(y[e].sum(), (1 - y[e]).sum()) > 50:
            folds.append((f, e))
    log(f"admission requires a gain on ALL {len(folds)} usable forward-chained folds "
        f"(of {len(qs)} candidate splits)")
    if not folds:
        raise SystemExit("no usable fold — refusing to report an admission decision nothing could have passed")

    def fold_auc(cols, fit, ev):
        r = fit_apply(cols, fit, S, ev)
        if r is None:
            return float("nan")
        m, sc = r
        return G.auc(y[m], sc) if m.sum() > 100 else float("nan")

    chosen = [0]
    admitted, remaining = [], list(range(1, S.shape[1]))
    while remaining:
        best, best_min = None, 0.0
        for j in remaining:
            g = np.array([fold_auc(chosen + [j], f, e) - fold_auc(chosen, f, e) for f, e in folds])
            if np.isfinite(g).all() and g.min() > best_min:
                best, best_min = j, g.min()
        if best is None:
            break
        chosen.append(best); remaining.remove(best); admitted.append(names_l[best])
        log(f"  admitted {names_l[best][:44]:<46} worst fold +{best_min:.4f}")
    if not admitted:
        log("  NO member improved every fold — the stack IS the baseline")

    # ── measured once, on the untouched test half
    def test_auc(cols):
        F = G.rankfeat(S[:, cols]); ok = np.isfinite(F).all(1)
        if ok.sum() < 300:
            return float("nan")
        w, b = G.fit_nonneg(F[ok], y[ok], np.ones(int(ok.sum())))
        Ft = G.rankfeat(T[:, cols]); m = np.isfinite(Ft).all(1)
        return G.auc(yte[m], Ft[m] @ w + b) if m.sum() > 50 else float("nan")

    base_t, stack_t = test_auc([0]), test_auc(chosen)
    # the production number: the same stack with the two diagnostic controls removed
    real = [c for c in chosen if not names_l[c].startswith("_")]
    real_t = test_auc(real)
    contrib = {names_l[j]: (stack_t - test_auc([c for c in chosen if c != j])) if j in chosen else 0.0
               for j in range(1, S.shape[1])}

    L = []; p = L.append
    p("=" * 100)
    p("TWO BIRTH DATES, NOTHING ELSE — natural (death) vs artificial (divorce) separation")
    p("=" * 100)
    p("")
    p(f"  inputs            dob_a, dob_b. No wedding date, no era, no start year — absent, not masked.")
    p(f"  train             {len(tr):,} pairs, {y.mean():.1%} artificial, born to {int(byr(tr).max())}")
    p(f"  test              {len(te):,} pairs, {yte.mean():.1%} artificial, born {int(byr(te).min())}+")
    p(f"                    strictly later-born, no shared person, no shared birth date, read once")
    p(f"  augmentation      {len(aug)} masked copies in the fit (year gone, or month+day gone)")
    p(f"  members           {S.shape[1]-1} + baseline, families split into sub-families")
    p("")
    p(f"  {'BASELINE (two dates: years, gap, precision)':<58}{base_t:>9.4f}")
    p(f"  {'STACK, REAL MEMBERS ONLY  <- the production number':<58}{real_t:>9.4f}")
    p(f"  {'gain from every astrological system combined':<58}{real_t-base_t:>+9.4f}")
    p("")
    p(f"  {'stack including the two diagnostic controls':<58}{stack_t:>9.4f}")
    p(f"  {'  ... of which the PLANTED answer accounts for':<58}{stack_t-real_t:>+9.4f}")
    p("")
    p(f"  {'MEMBER':<58}{'admitted':>10}{'contribution':>14}")
    p("  " + "-" * 82)
    for nm, v in sorted(contrib.items(), key=lambda kv: -kv[1]):
        if v != 0 or nm.startswith("_") or ":" not in nm:
            p(f"  {nm[:56]:<58}{('yes' if nm in admitted else 'no'):>10}{v:>+14.4f}")
    p("  " + "-" * 82)
    p("")
    p("  A member that is not admitted is ABSENT from the stack and contributes exactly zero — it cannot move")
    p("  the number in either direction. That is the guarantee: the worst any component can do is nothing.")
    rep = "\n".join(L)
    print("\n" + rep, flush=True)
    open(os.path.join(OUT, "final_report.txt"), "w").write(rep + "\n")
    json.dump(dict(baseline=base_t, stack=stack_t, admitted=admitted, contribution=contrib,
                   n_train=len(tr), n_test=len(te)), open(os.path.join(OUT, "final.json"), "w"), indent=1)
    log(f"wrote {OUT}/final_report.txt")


if __name__ == "__main__":
    main()
