"""fit_phasor_torch.py — the sidereal phasor with a SIGMOID head, in pytorch (operator 2026-08-31).

THE MODEL, exactly as ordered:

    y_hat = sigmoid( b + SUM_i a_i cos(man_i - woman_i) + SUM_i c_i sin(man_i - woman_i) )

which is a logistic regression on the phasor basis — CONVEX, so no restarts, no rectification
dead-zone, one optimum per fit. Balanced BCE (pos_weight = negatives/positives), and a small swept
L2 because the harmonic columns of one body are correlated.

VARIANTS (same folds, seeds and corpus as every other fit on tilldeath):
    exact      k=1, same-body cross-chart differences      29 parameters   <- the formula as written
    harmonic   k=1..8 per same-body difference            225   (trine = 3rd harmonic, square = 4th)
    synastry   every his-body x her-body pair, k=1..8   3,137
    him / her  natal phasors on one chart's own angles   225 each    <- the only baselines

Runs on MPS. LBFGS full-batch: convex problem, ~tens of iterations to the optimum.
"""
import json, os, time, warnings
import numpy as np, pandas as pd
import torch
warnings.filterwarnings("ignore")

D = os.path.expanduser("~/.artamatch-dev/tilldeath")
NFOLD, SEEDS = 10, (7, 23, 101)
K = 8
WDS = (3e-5, 3e-4, 3e-3)
DEV = "mps" if torch.backends.mps.is_available() else "cpu"
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def features(ra, rb, kind, K):
    cols = []
    nb = ra.shape[1]
    if kind == "exact":
        for i in range(nb):
            d = ra[:, i] - rb[:, i]; cols += [np.cos(d), np.sin(d)]
    elif kind == "harmonic":
        for i in range(nb):
            d = ra[:, i] - rb[:, i]
            for k in range(1, K + 1):
                cols += [np.cos(k * d), np.sin(k * d)]
    elif kind == "synastry":
        for i in range(nb):
            for j in range(nb):
                d = ra[:, i] - rb[:, j]
                for k in range(1, K + 1):
                    cols += [np.cos(k * d), np.sin(k * d)]
    elif kind in ("him", "her"):
        r = ra if kind == "him" else rb
        for i in range(nb):
            for k in range(1, K + 1):
                cols += [np.cos(k * r[:, i]), np.sin(k * r[:, i])]
    return np.column_stack(cols).astype(np.float32)


def fit_fold(Ft, yt, pw, trm_t, wd, iters=80):
    """balanced logistic ridge by full-batch LBFGS; returns logits for ALL rows"""
    p = Ft.shape[1]
    wv = torch.zeros(p, device=DEV, requires_grad=True)
    b = torch.zeros(1, device=DEV, requires_grad=True)
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=pw, reduction="mean")
    opt = torch.optim.LBFGS([wv, b], max_iter=iters, history_size=12,
                            tolerance_grad=1e-9, tolerance_change=1e-11,
                            line_search_fn="strong_wolfe")
    Ftr, ytr = Ft[trm_t], yt[trm_t]

    def closure():
        opt.zero_grad()
        z = Ftr @ wv + b
        loss = lossf(z, ytr) + wd * (wv * wv).sum()
        loss.backward()
        return loss
    opt.step(closure)
    with torch.no_grad():
        return (Ft @ wv + b).cpu().numpy(), wv.detach().cpu().numpy(), float(b)


def main():
    from sklearn.metrics import roc_auc_score
    full = pd.read_csv(f"{D}/full.csv")
    y = full.y.to_numpy().astype(np.float32)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    tha, thb = Z["theta_a_train"], Z["theta_b_train"]
    okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
    bodies = [str(b) for b, o in zip(Z["bodies"], okb) if o]
    ra, rb = np.deg2rad(tha[:, okb]), np.deg2rad(thb[:, okb])
    log(f"{len(y):,} couples · {int(y.sum()):,} positives · {len(bodies)} bodies · device {DEV}")

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
    folds = {s: np.random.default_rng(s).integers(0, NFOLD, gid.max() + 1)[gid] for s in SEEDS}
    yt_all = torch.from_numpy(y).to(DEV)
    pw = torch.tensor((len(y) - y.sum()) / y.sum(), device=DEV)

    report = {}
    for kind in ("him", "her", "exact", "harmonic", "synastry"):
        F = features(ra, rb, kind, K)
        Ft = torch.from_numpy(F).to(DEV)
        log(f"== {kind}: {F.shape[1]} features ==")
        # pick wd on seed 7, then score all seeds at the winner
        per_wd = {}
        for wd in WDS:
            fold = folds[7]
            oof = np.zeros(len(y), np.float32)
            for k in range(NFOLD):
                trm_t = torch.from_numpy(fold != k).to(DEV)
                zall, _, _ = fit_fold(Ft, yt_all, pw, trm_t, wd)
                oof[fold == k] = zall[fold == k]
            per_wd[wd] = (float(roc_auc_score(y, oof)), oof)
        wd = max(per_wd, key=lambda w: per_wd[w][0])
        log(f"   wd sweep: " + "  ".join(f"{w:g}:{per_wd[w][0]:.4f}" for w in WDS) +
            f"  -> wd {wd:g}")
        np.save(f"{D}/oof_sig_{kind}.npy", per_wd[wd][1])
        aucs = [per_wd[wd][0]]
        for s in SEEDS[1:]:
            fold = folds[s]
            oof = np.zeros(len(y), np.float32)
            for k in range(NFOLD):
                trm_t = torch.from_numpy(fold != k).to(DEV)
                zall, _, _ = fit_fold(Ft, yt_all, pw, trm_t, wd)
                oof[fold == k] = zall[fold == k]
            aucs.append(float(roc_auc_score(y, oof)))
        report[kind] = {"params": int(F.shape[1] + 1), "wd": wd,
                        "auc_by_seed": aucs, "auc_mean": float(np.mean(aucs))}
        log(f">> {kind}: seeds {['%.4f' % a for a in aucs]} · mean {np.mean(aucs):.4f}")
        del F, Ft

    log("SUMMARY (sigmoid phasor · mean over 3 seeds)")
    for kind, r in report.items():
        log(f"   {kind:<10}{r['params']:>6} params   AUC {r['auc_mean']:.4f}")
    best_pair = max(("exact", "harmonic", "synastry"), key=lambda k: report[k]["auc_mean"])
    lift = report[best_pair]["auc_mean"] - max(report["him"]["auc_mean"], report["her"]["auc_mean"])
    log(f"   best pair variant: {best_pair} · over best solo {lift:+.4f}")
    report["_summary"] = {"best_pair": best_pair, "lift_over_best_solo": float(lift), "device": DEV}
    json.dump(report, open(f"{D}/report_sigmoid_phasor.json", "w"), indent=1)
    log(f"saved {D}/report_sigmoid_phasor.json")


if __name__ == "__main__":
    main()
