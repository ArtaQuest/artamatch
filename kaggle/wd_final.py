"""
wd_final.py — WIKIDATA ONLY. Death vs divorce, pure astrology/numerology, gender verified.

Corpus: ~/.artamatch-dev/sep4 — the maxed Wikidata extraction (all four relationship types, end date OR end
cause, at least one birth date, complete sex table): 25,407 train / 3,432 test, split strictly on the later
birth so the test half is people born after everyone in training.

Features: pure only. Every calendar integer, precision flag, occurrence count and the mortality prior removed,
so each input is a function of the two birth dates and the model can score a couple in no dataset.

GENDER. The corpus is gendered by construction: column a IS the man. So the features must be ALLOWED to read
the order — a_* is the husband's chart, b_* the wife's, signed arcs are husband-minus-wife. Whether they
actually do is measured, not assumed: the test half is rebuilt with the two dates swapped (its phases
recomputed from scratch, not shimmed) and rescored. If nothing moves, the feature set has erased gender.
"""
import json, os, subprocess, sys
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from pure_astro import load_families

D = os.path.expanduser(os.environ.get("AQ_D", "~/.artamatch-dev/sep4"))
FEAT = os.path.expanduser(os.environ.get("AQ_FEAT", "~/.artamatch-dev/sep4feat"))
HP = dict(n_estimators=300, learning_rate=0.05, max_depth=4, min_child_weight=30, subsample=0.8,
          colsample_bytree=0.7, reg_lambda=20.0, verbosity=0, n_jobs=4)


def phases(df, out):
    os.makedirs(out, exist_ok=True)
    df.to_csv(f"{out}/train.csv", index=False)
    df.head(2).drop(columns=[c for c in df.columns if c == "ended_in_divorce"]).assign(
        id=["x0", "x1"]).to_csv(f"{out}/test.csv", index=False)
    subprocess.run([sys.executable, "-u", os.path.join(CODE, "kerykeion_phases.py")], capture_output=True,
                   text=True, timeout=1800, env=dict(os.environ, AQ_SRC=out, AQ_OUT=out, AQ_NO_PLACE="1"))
    return np.load(f"{out}/phases.npz", allow_pickle=True)


def main():
    import xgboost as xgb
    tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{FEAT}/phases.npz", allow_pickle=True)
    byr = lambda d: np.fmax(pd.to_numeric(d.dob_a.str[:4], errors="coerce").replace(0, np.nan),
                            pd.to_numeric(d.dob_b.str[:4], errors="coerce").replace(0, np.nan))
    assert byr(te).min() > byr(tr).max(), "test is not strictly later-born"
    print(f"  WIKIDATA ONLY · train {len(tr):,} ({ytr.mean():.1%} artificial) · test {len(te):,} "
          f"({yte.mean():.1%}) · born to {int(byr(tr).max())} / from {int(byr(te).min())}", flush=True)

    Xtr, names = load_families(tr, Z, "train")
    Xte, _ = load_families(te, Z, "test")
    fam_of = np.array([n.split(":", 1)[0] for n in names])
    fams = sorted(set(fam_of))
    print(f"  {Xtr.shape[1]:,} pure features · {len(fams)} families", flush=True)

    later = np.nan_to_num(byr(tr).to_numpy(), nan=1900).astype(int)
    cuts = [np.quantile(later, q) for q in (0.40, 0.55, 0.70, 0.85, 1.0)]

    S, T, kept = [], [], []
    for f in fams:
        cols = np.where(fam_of == f)[0]
        if len(cols) < 3 or not np.isfinite(Xtr[:, cols]).any():
            continue
        s, t = G.forward_oof(Xtr[:, cols], Xte[:, cols], ytr, later, cuts, {"tree_method": "hist"}, seed=0)
        ok = np.isfinite(s)
        if ok.sum() < 2000:
            continue
        S.append(s); T.append(t); kept.append(f)
        print(f"    {f:<22} OOF {G.auc(ytr[ok], s[ok]):.4f}   TEST {G.auc(yte, t) if np.isfinite(t).all() else float('nan'):.4f}", flush=True)
    S = np.column_stack(S); T = np.column_stack(T)
    scored = np.isfinite(S).all(1)
    F = G.rankfeat(S[scored]); w, b = G.fit_nonneg(F, ytr[scored], np.ones(int(scored.sum())))
    print(f"\n  STACK over {len(kept)} members · train OOF {G.auc(ytr[scored], F @ w + b):.4f} on {int(scored.sum()):,}")
    print("  weights: " + " · ".join(f"{kept[i]} {100*w[i]/max(w.sum(),1e-9):.0f}%"
                                     for i in np.argsort(-w) if w[i] > 0))
    # test, read once
    Ft = np.column_stack([np.searchsorted(np.sort(S[scored][:, j]), T[:, j]) / int(scored.sum()) - 0.5
                          for j in range(len(kept))])
    zt = Ft @ w + b
    auc = G.auc(yte, zt)
    print(f"\n  TEST AUC (Wikidata only, strictly later-born, read once): {auc:.4f}   chance 0.5000")

    # ── GENDER: swap husband and wife, recompute phases from scratch, rescore
    sw = te.copy(); sw["dob_a"], sw["dob_b"] = te.dob_b.values, te.dob_a.values
    Zsw = phases(sw.assign(ended_in_divorce=0), os.path.expanduser(os.environ.get("AQ_SWAPDIR", "~/.artamatch-dev/wd_swap")))
    Xsw_raw, nsw = load_families(sw, Zsw, "train")
    pos = {nm: i for i, nm in enumerate(nsw)}
    Xsw = np.full((len(te), len(names)), np.nan, np.float32)
    for j, nm in enumerate(names):
        i = pos.get(nm)
        if i is not None:
            Xsw[:, j] = Xsw_raw[:, i]
    Fsw = np.zeros((len(te), len(kept)))
    for j, f in enumerate(kept):
        cols = np.where(fam_of == f)[0]
        m = xgb.XGBClassifier(random_state=0, **HP); m.fit(Xtr[:, cols], ytr)
        sc = m.predict_proba(Xsw[:, cols])[:, 1]
        Fsw[:, j] = np.searchsorted(np.sort(S[scored][:, j]), sc) / int(scored.sum()) - 0.5
    zsw = Fsw @ w + b
    p1, p2 = 1/(1+np.exp(-zt)), 1/(1+np.exp(-zsw))
    dz = np.abs(p1 - p2)
    print(f"\n  GENDER CHECK — husband and wife swapped, phases rebuilt, rescored:")
    print(f"    mean |ΔP| {np.nanmean(dz):.4f} · median {np.nanmedian(dz):.4f} · max {np.nanmax(dz):.4f}"
          f" · rows moving >1 point: {(dz > 0.01).mean():.0%}")
    print(f"    swapped-order TEST AUC {G.auc(yte, zsw):.4f} vs correct-order {auc:.4f}")
    print("    " + ("VERDICT: the model READS gender — column a is the husband and swapping changes the answer"
                    if np.nanmean(dz) > 0.005 else
                    "VERDICT: near-invariant under swap — the feature set is ERASING gender"))

    # deployment on the entire Wikidata corpus
    allf = pd.concat([tr[["dob_a", "dob_b", "start"]], te[["dob_a", "dob_b", "start"]]], ignore_index=True)
    yall = np.concatenate([ytr, yte]); Xall = np.vstack([Xtr, Xte])
    tag = os.environ.get("AQ_TAG", "wdf")
    ref = []
    for f in kept:
        cols = np.where(fam_of == f)[0]
        m = xgb.XGBClassifier(random_state=0, **HP); m.fit(Xall[:, cols], yall)
        m.save_model(os.path.expanduser(f"~/.artamatch-dev/{tag}_{f}.json"))
        ref.append(m.predict_proba(Xall[:, cols])[:, 1])
    np.savez_compressed(os.path.expanduser(f"~/.artamatch-dev/{tag}_ref.npz"),
                        T=np.column_stack(ref), fams=np.array(kept, dtype=object), w=w, b=b,
                        names=np.array(names, dtype=object))
    json.dump({"families": kept, "weights": w.tolist(), "bias": float(b), "test_auc": float(auc),
               "gender_mean_dP": float(np.nanmean(dz)), "n_deploy": int(len(allf))},
              open(os.path.expanduser(f"~/.artamatch-dev/{tag}.json"), "w"), indent=1)
    print(f"\n  deployed on the ENTIRE Wikidata corpus: {len(allf):,} pairs · saved")


if __name__ == "__main__":
    main()
