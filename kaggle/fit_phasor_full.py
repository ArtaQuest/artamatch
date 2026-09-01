"""fit_phasor_full.py — the COMPREHENSIVE sigmoid phasor (operator 2026-08-31):

    y_hat = sigmoid( a + SUM_i [ b_i cos(man_i - woman_i) + c_i sin(man_i - woman_i)
                               + d_i cos(man_i) + e_i sin(man_i)
                               + f_i cos(woman_i) + g_i sin(woman_i) ] )

Every block carries BOTH terms (the standing correction): a cos without its sin is a phasor whose
phase is pinned at zero, which nothing in the tradition asks for. Three sizes:

    full-k1     the formula as written, k=1 everywhere                     85 parameters
    full-h      every block at harmonics k=1..8                           673
    full-syn    cross-body synastry pairs (k<=8) + both natal blocks    3,585

Baselines stay him-only / her-only (fitted already: 0.6767 / 0.6742). BCE, pos-weighted, LBFGS,
wd swept over SEVEN values with a boundary check — a boundary optimum has burnt this project twice
today already.
"""
import json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P

D = os.path.expanduser("~/.artamatch-dev/tilldeath")
WDS = (3e-5, 3e-4, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1)
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def feats(ra, rb, kind, K):
    cols = []
    nb = ra.shape[1]
    def block(angle, kmax):
        for k in range(1, kmax + 1):
            cols.append(np.cos(k * angle)); cols.append(np.sin(k * angle))
    if kind == "full-k1":
        for i in range(nb):
            block(ra[:, i] - rb[:, i], 1); block(ra[:, i], 1); block(rb[:, i], 1)
    elif kind == "full-h":
        for i in range(nb):
            block(ra[:, i] - rb[:, i], K); block(ra[:, i], K); block(rb[:, i], K)
    elif kind == "full-syn":
        for i in range(nb):
            for j in range(nb):
                block(ra[:, i] - rb[:, j], K)
        for i in range(nb):
            block(ra[:, i], K); block(rb[:, i], K)
    return np.column_stack(cols).astype(np.float32)


def main():
    full = pd.read_csv(f"{D}/full.csv")
    y = full.y.to_numpy().astype(np.float32)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    tha, thb = Z["theta_a_train"], Z["theta_b_train"]
    okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
    ra, rb = np.deg2rad(tha[:, okb]), np.deg2rad(thb[:, okb])
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        pa, pb = find(a), find(b)
        if pa != pb: parent[pa] = pb
    gid = pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]
    folds = {s: np.random.default_rng(s).integers(0, P.NFOLD, gid.max() + 1)[gid] for s in P.SEEDS}
    yt = torch.from_numpy(y).to(P.DEV)
    pw = torch.tensor((len(y) - y.sum()) / y.sum(), device=P.DEV)

    report = {}
    for kind in ("full-k1", "full-h", "full-syn"):
        F = feats(ra, rb, kind, P.K)
        Ft = torch.from_numpy(F).to(P.DEV)
        log(f"== {kind}: {F.shape[1]} features ==")
        curve = {}
        for wd in WDS:
            fold = folds[7]
            oof = np.zeros(len(y), np.float32)
            for k in range(P.NFOLD):
                trm_t = torch.from_numpy(fold != k).to(P.DEV)
                zall, _, _ = P.fit_fold(Ft, yt, pw, trm_t, wd)
                oof[fold == k] = zall[fold == k]
            curve[wd] = float(roc_auc_score(y, oof))
        best = max(curve, key=curve.get)
        edge = "  <- BOUNDARY" if best in (WDS[0], WDS[-1]) else ""
        log("   wd: " + "  ".join(f"{w:g}:{curve[w]:.4f}" for w in WDS))
        log(f"   BEST wd {best:g} -> {curve[best]:.4f}{edge}")
        aucs = [curve[best]]
        for s in P.SEEDS[1:]:
            fold = folds[s]
            oof = np.zeros(len(y), np.float32)
            for k in range(P.NFOLD):
                trm_t = torch.from_numpy(fold != k).to(P.DEV)
                zall, _, _ = P.fit_fold(Ft, yt, pw, trm_t, best)
                oof[fold == k] = zall[fold == k]
            aucs.append(float(roc_auc_score(y, oof)))
        report[kind] = {"params": int(F.shape[1] + 1), "wd": best,
                        "wd_curve": {str(k): v for k, v in curve.items()},
                        "auc_by_seed": aucs, "auc_mean": float(np.mean(aucs))}
        log(f">> {kind}: mean {np.mean(aucs):.4f}")
        del F, Ft

    log("SUMMARY — comprehensive vs the fixed baselines (him 0.6767 · her 0.6742)")
    for kind, r in report.items():
        log(f"   {kind:<9}{r['params']:>6} params   AUC {r['auc_mean']:.4f}   "
            f"vs best solo {r['auc_mean'] - 0.6767:+.4f}")
    json.dump(report, open(f"{D}/report_full_phasor.json", "w"), indent=1)
    log(f"saved {D}/report_full_phasor.json")


if __name__ == "__main__":
    main()
