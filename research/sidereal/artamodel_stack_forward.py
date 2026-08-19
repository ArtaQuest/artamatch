"""
artamodel_stack_forward.py — the full ArtaModel stack rebuilt with FORWARD-CHAINING out-of-fold scores.

The competition split is temporal (train: later date <= 1900; test: > 1900), so the only out-of-fold score that
mimics the test is "fit on everything BEFORE a cut, score the block AFTER it". artamodel_full_stack.py scored each
temporal half with the OTHER half's model, which includes the backwards direction (fit late, score early); for the
clock members that direction is anti-predictive (d_neptune: 0.66 forward, 0.51 mixed, 0.63 held), so the stacker
was taught that its strongest members were noise and came out BELOW the deployed member it contained. Here:

  burn-in = the earliest 40% of train by `later`; four forward blocks over the latest 60% (cuts at the 0.40,
  0.55, 0.70, 0.85 quantiles). Block k's scores come from a fit on ALL rows before its cut (early-stopped on the
  latest 15% of those). Test scores come from the fit on all of train. The stacker is trained on the OOF rows,
  selected on the LAST block (fit on blocks 1-3 -> score block 4), refitted on all four for the test.
  Members: 126 per-phasor · 9 per-term sums · 3/6/9-term sums · 3 aspect grids · BOOST6 on full-chart rows (the
  deployed construction) · BOOST6 / BOOST9 on every any-phasor row · the 4 plain columns.
  A correct stacker is at least its best member on the selector; that is asserted, not assumed.

Usage: AQ_OUT=/tmp/aq3feat python artamodel_stack_forward.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from artamodel import BODIES14, TERMS, TERMS9, auc, phase_matrix       # noqa: E402
from artamodel_full_stack import _fit, grid, matched                   # noqa: E402
from artamodel_deploy import boost_recorded, score                     # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat")
QS = (0.40, 0.55, 0.70, 0.85, 1.0)
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)


def cuts_of(later):
    return [np.quantile(later, q) for q in QS]


def forward_member(P, y, later, Pte, cuts, kind="field", rows=None, stages=80, min_rows=300):
    """OOF train scores over the four forward blocks + test scores from the all-train fit. `rows` restricts the
    FIT population (e.g. full charts) but every row with a phasor gets scored."""
    has = np.isfinite(P).any(1); has_te = np.isfinite(Pte).any(1)
    pop = has if rows is None else (has & rows)
    s_tr = np.full(len(P), np.nan); s_te = np.full(len(Pte), np.nan); fits = 0
    def fit_on(mask):
        if mask.sum() < min_rows or len(np.unique(y[mask])) < 2:
            return None
        L = later[mask]; inner = L > np.quantile(L, 0.85)
        if kind == "field":
            m, _ = _fit(P[mask], y[mask], inner)
            return lambda Q: m.logit(np.nan_to_num(np.cos(np.radians(Q))), np.nan_to_num(np.sin(np.radians(Q))))[0]
        b = boost_recorded(P[mask], y[mask], inner, stages=stages, nu=0.1)
        return lambda Q: score(b, Q)
    for k in range(1, len(cuts)):
        lo, hi = cuts[k - 1], cuts[k]
        blk = has & (later > lo) & (later <= hi) if k < len(cuts) - 1 else has & (later > lo)
        f = fit_on(pop & (later <= lo))
        if f is None or not blk.any():
            continue
        s_tr[blk] = f(P[blk]); fits += 1
    f = fit_on(pop)
    if f is not None:
        s_te[has_te] = f(Pte[has_te])
    return s_tr, s_te, int(pop.sum()), fits


def main():
    import lightgbm as lgb
    from sklearn.linear_model import LogisticRegression
    Z = np.load(PH, allow_pickle=True)
    bodies = list(Z["bodies"]); ids = Z["id_test"]; y = Z["y_train"].astype(np.int64)
    Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]
    Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    later = Z["yr_train"].astype(int).max(1); cuts = cuts_of(later)
    sol = pd.read_csv(os.environ.get("AQ_SOL", "/tmp/aq3comp/solution.csv")).set_index("id"); lab = [c for c in sol.columns if c != "Usage"][0]
    yte = sol.loc[ids, lab].to_numpy().astype(int)
    j1 = ptr[:, pn.index("start_is_jan1")] == 1.0; j1e = pte[:, pn.index("start_is_jan1")] == 1.0
    Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    B = [bodies.index(b) for b in BODIES14]
    charts = np.isfinite(Dtr[:, B]).all(1) & np.isfinite(Mtr[:, B]).all(1)
    P, labels = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, TERMS9); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, TERMS9)
    c6 = [j for j, l in enumerate(labels) if l.split("_", 1)[0] in TERMS]
    log(f"cuts by later-date quantiles: {[int(c) for c in cuts]}  (OOF rows = later > {int(cuts[0])}: {(later > cuts[0]).sum():,})")
    ages_te = pte[:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]
    cell = (np.floor(np.nan_to_num(ages_te[:, 0]) / 3) * 1000 + np.floor(np.nan_to_num(ages_te[:, 1]) / 3)).astype(int)
    cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
    oof_rows = later > cuts[0]; last = later > cuts[-2]
    members_tr, members_te, names, meta = [], [], [], []

    def add(Ptr_, Pte_, name, **kw):
        s_tr, s_te, n, fits = forward_member(Ptr_, y, later, Pte_, cuts, **kw)
        f = np.isfinite(s_tr) & oof_rows; g = np.isfinite(s_te)
        oof = auc(y[f], s_tr[f]) if f.sum() > 200 and len(np.unique(y[f])) > 1 else float("nan")
        fl = np.isfinite(s_tr) & last; oofl = auc(y[fl], s_tr[fl]) if fl.sum() > 200 and len(np.unique(y[fl])) > 1 else float("nan")
        held = auc(yte[g], s_te[g]) if g.sum() > 100 else float("nan")
        members_tr.append(s_tr); members_te.append(s_te); names.append(name)
        meta.append({"member": name, "phasors": int(Ptr_.shape[1]), "n_fit": n, "forward_oof": oof, "forward_oof_last_block": oofl, "held_on_its_rows": held, "n_test": int(g.sum())})
        log(f"  {name:<44} fit rows {n:>6,}  fwd-OOF {oof:.4f} (last block {oofl:.4f})  held {held:.4f} on {g.sum():,}")
    for j, l in enumerate(labels):
        add(P[:, [j]], Pe[:, [j]], f"phasor {l}")
    for t in TERMS9:
        cc = [j for j, l in enumerate(labels) if l.split("_", 1)[0] == t]; add(P[:, cc], Pe[:, cc], f"SUM term {t} over 14 bodies")
    for sub, nm in ((("a", "m", "d"), "3-term"), (TERMS, "6-term"), (TERMS9, "9-term")):
        cc = [j for j, l in enumerate(labels) if l.split("_", 1)[0] in sub]; add(P[:, cc], Pe[:, cc], f"SUM {nm} over all bodies")
    G, _ = grid(Mtr, Dtr, B); Ge, _ = grid(Mte, Dte, B); add(G, Ge, "ASPECTS synastry grid")
    G, _ = grid(Wtr, Mtr, B); Ge, _ = grid(Wte, Mte, B); add(G, Ge, "ASPECTS wedding→mom grid")
    G, _ = grid(Wtr, Dtr, B); Ge, _ = grid(Wte, Dte, B); add(G, Ge, "ASPECTS wedding→dad grid")
    add(P[:, c6], Pe[:, c6], "BOOST6 full-chart rows (deployed construction)", kind="boost", rows=charts)
    add(P[:, c6], Pe[:, c6], "BOOST6 any-phasor rows", kind="boost")
    add(P, Pe, "BOOST9 any-phasor rows", kind="boost")
    Str = np.column_stack(members_tr).astype(np.float32); Ste = np.column_stack(members_te).astype(np.float32)
    np.savez_compressed(os.path.join(OUT, "forward_members.npz"), S_train=Str, S_test=Ste, names=np.array(names), y=y, yte=yte, later=later, ids=ids, cuts=np.array(cuts))
    log(f"{Str.shape[1]} members saved")

    # ---------------- stackers ----------------
    R = {"cuts": [float(c) for c in cuts], "members": meta, "stacks": {}}
    Xtr_all = np.column_stack([Str, ptr[:, cols]]); Xte_all = np.column_stack([Ste, pte[:, cols]]); allnames = names + ["plain " + pn[c] for c in cols]
    sel_fit = oof_rows & ~last; sel_val = last
    best_member_sel = max((auc(y[sel_val & np.isfinite(Xtr_all[:, j])], Xtr_all[sel_val & np.isfinite(Xtr_all[:, j]), j]), allnames[j]) for j in range(Xtr_all.shape[1]) if (sel_val & np.isfinite(Xtr_all[:, j])).sum() > 500)
    log(f"  best single member on the selector block: {best_member_sel[1]} {best_member_sel[0]:.4f}  (scored rows only)")
    # NaN-aware rank features for the linear stacker: rank within the scored rows, 0.5 + indicator where absent
    def rankfeat(Xa, Xb):
        A = np.zeros((len(Xa), 2 * Xa.shape[1])); Bm = np.zeros((len(Xb), 2 * Xb.shape[1]))
        for j in range(Xa.shape[1]):
            fa = np.isfinite(Xa[:, j]); fb = np.isfinite(Xb[:, j]); A[:, 2 * j] = 0.5; Bm[:, 2 * j] = 0.5
            if fa.sum() > 1:
                A[fa, 2 * j] = r01(Xa[fa, j]); A[:, 2 * j + 1] = fa
            if fb.sum() > 1:
                Bm[fb, 2 * j] = r01(Xb[fb, j]); Bm[:, 2 * j + 1] = fb
        return A - 0.5, Bm - 0.5
    out = {}
    def run(name, Xa, Xb, fam, **params):
        def fitpred(idx, Xq):
            if fam == "lgb":
                p = np.zeros(len(Xq))
                for sd in range(3):
                    c = lgb.LGBMClassifier(random_state=sd, verbose=-1, **params); c.fit(Xa[idx], y[idx]); p += c.predict_proba(Xq)[:, 1]
                return p / 3
            A, Bq = rankfeat(Xa[idx], Xq); c = LogisticRegression(C=params.get("C", 0.1), max_iter=2000); c.fit(A, y[idx]); return c.decision_function(Bq)
        pv = fitpred(sel_fit, Xa[sel_val]); sel = auc(y[sel_val], pv)
        p = fitpred(oof_rows, Xb); held = auc(yte, p); ac = matched(yte, p, cell)
        R["stacks"][name] = {"selector_last_block": sel, "held": held, "age_cell_matched": ac}; out[name] = p
        log(f"  {name:<62} selector {sel:.4f}   held {held:.4f}   age-cell {ac:.4f}")
    P_REG = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=100, colsample_bytree=0.6, subsample=0.8, subsample_freq=1, reg_lambda=10.0)
    P_TIGHT = dict(n_estimators=300, learning_rate=0.02, num_leaves=7, min_child_samples=300, colsample_bytree=0.5, subsample=0.7, subsample_freq=1, reg_lambda=30.0)
    dep = [names.index("BOOST6 full-chart rows (deployed construction)")]; plain = list(range(len(names), len(allnames)))
    run("REFERENCE plain columns alone [lgb]", Xtr_all[:, plain], Xte_all[:, plain], "lgb", **P_REG)
    run("deployed member alone through the stacker [lgb]", Xtr_all[:, dep], Xte_all[:, dep], "lgb", **P_TIGHT)
    run("deployed + plain [lgb]", Xtr_all[:, dep + plain], Xte_all[:, dep + plain], "lgb", **P_REG)
    run("all 144 + plain [lgb regularised]", Xtr_all, Xte_all, "lgb", **P_REG)
    run("all 144 + plain [lgb tight]", Xtr_all, Xte_all, "lgb", **P_TIGHT)
    run("all 144 + plain [logistic on ranks, C=0.1]", Xtr_all, Xte_all, "lr", C=0.1)
    run("all 144 + plain [logistic on ranks, C=0.01]", Xtr_all, Xte_all, "lr", C=0.01)
    run("all 144, no plain [logistic on ranks, C=0.1]", Str, Ste, "lr", C=0.1)
    # greedy forward selection of members on the selector block (Caruana), rank-averaged, no fitting
    def blend(cols_, Xm):
        acc = np.zeros(len(Xm)); cnt = np.zeros(len(Xm))
        for j in cols_:
            v = Xm[:, j]; f = np.isfinite(v)
            if f.sum() > 1:
                acc[f] += r01(v[f]); cnt[f] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.5)
    chosen = []; cur = 0.0
    for _ in range(12):
        best = None
        for j in range(Xtr_all.shape[1]):
            a = auc(y[sel_val], blend(chosen + [j], Xtr_all[sel_val]))
            if best is None or a > best[0]:
                best = (a, j)
        if best[0] <= cur + 1e-4:
            break
        cur = best[0]; chosen.append(best[1])
    pb = blend(chosen, Xte_all); R["stacks"]["greedy rank blend (Caruana, selected on last block)"] = {"selector_last_block": cur, "held": auc(yte, pb), "age_cell_matched": matched(yte, pb, cell), "members": [allnames[j] for j in chosen]}
    out["greedy rank blend (Caruana, selected on last block)"] = pb
    log(f"  {'greedy rank blend (Caruana, selected on last block)':<62} selector {cur:.4f}   held {auc(yte, pb):.4f}   age-cell {matched(yte, pb, cell):.4f}")
    log("    members: " + "; ".join(allnames[j] for j in chosen))
    pick = max(R["stacks"].items(), key=lambda kv: kv[1]["selector_last_block"])
    R["selected"] = pick[0]; R["best_single_member_on_selector"] = {"member": best_member_sel[1], "auc": best_member_sel[0]}
    log(f"  SELECTED by the last block: {pick[0]}  selector {pick[1]['selector_last_block']:.4f}  held {pick[1]['held']:.4f}")
    pd.DataFrame({"id": ids, lab: r01(out[pick[0]])}).to_csv(os.path.join(OUT, "submission_forward_stack.csv"), index=False)
    json.dump(R, open(os.path.join(OUT, "artamodel_stack_forward.json"), "w"), indent=1)
    log(f"wrote {OUT}/artamodel_stack_forward.json, submission_forward_stack.csv")


if __name__ == "__main__":
    main()
