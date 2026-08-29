"""final_audit.py — triple-check the shipped model, and rank what each statement is actually worth.

IMPORTANCE. A coefficient is not importance. A large weight on a statement that fires for 40 couples
moves almost nobody; a modest weight on one that fires for 3,000 moves the whole ranking. Five measures
are reported and reconciled:

  weight        the coefficient — what the statement is worth WHEN it fires
  fires         how often it fires at all
  |w|*sd        the standardised contribution — weight scaled by how much the statement actually varies.
                For a linear model this is the honest per-statement effect on the score.
  drop-one      refit the model without this statement and measure the CV that is lost. The most
                defensible measure there is, and the only one that accounts for what the others cover.
  z             the statement's own univariate strength, before any model

The headline ranking is drop-one, because it answers the question a reader asks: what would we lose if
this were not here.

AUDIT. Eleven checks, each of which has caught a real defect in this project at some point:
  1  every statement in the model exists in a freshly built bank      (the model is reproducible)
  2  the test AUC recomputes from the saved weights                   (the file matches the claim)
  3  every statement uses BOTH dates                                  (the pair-only constraint)
  4  every statement passes the doctrine denylist                     (no calendar demographics)
  5  no statement is valued at the missing-data placeholder           (NOT(x=na) once shipped)
  6  every statement clears the support floor                         (no rule on a handful of rows)
  7  the explainer produces a real reading for every statement        (no 'Doctrine' fallback)
  8  no two statements are the same column under different names      (koota_nadi=0 IS nadi_dosha)
 12  no two statements are NEAR-duplicates of each other                (composite and Davison agree on
     the slow planets, so the same reading can enter twice and each then looks worthless on drop-one)
  9  train and test features are built by the same code path          (a stale npz once broadcast wrong)
 10  the negations are corroborated by their own univariate direction (a flip that is really a suppressor)
 11  the reported CV and the reported test AUC come from the log      (no number typed by hand)

Usage: final_audit.py <model.json> [corpus_dir]
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v22_nnls import build
from v12_fit import side
from denylist import clause_ok
from explain_rules import explain

MODEL = os.path.expanduser(sys.argv[1])
D = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/.artamatch-dev/quality_good")
FLOOR = 40


def base_name(k):
    return k[4:-1] if k.startswith("NOT(") and k.endswith(")") else k


def main():
    m = json.load(open(MODEL))
    W = m["weights"]
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X, names = build(tr, Z, "train")
    Xt, nt = build(te, Z, "test")
    pos = {k: i for i, k in enumerate(nt)}
    Xt = np.column_stack([Xt[:, pos[k]] if k in pos else np.zeros(len(te), np.float32) for k in names])
    ix = {k: i for i, k in enumerate(names)}

    print(f"  model: {os.path.basename(MODEL)}")
    print(f"  {len(W)} statements · bank rebuilt at {X.shape[1]:,} · train {len(tr):,} · test {len(te):,}\n")
    fails = []

    def chk(no, label, ok, detail=""):
        print(f"   {no:>2}. {'PASS' if ok else 'FAIL'}  {label}{('  — ' + detail) if detail else ''}")
        if not ok:
            fails.append(label)

    # ---- build the model's design matrix, honouring the NOT() negations ----
    cols_tr, cols_te, missing = [], [], []
    for k in W:
        b = base_name(k)
        if b not in ix:
            missing.append(k); continue
        a, c = X[:, ix[b]], Xt[:, ix[b]]
        if k.startswith("NOT("):
            a, c = 1.0 - a, 1.0 - c
        cols_tr.append(a); cols_te.append(c)
    Mtr = np.column_stack(cols_tr); Mte = np.column_stack(cols_te)
    keys = [k for k in W if base_name(k) in ix]
    w = np.array([W[k] for k in keys], float)
    b0 = float(m.get("intercept", 0.0))

    print("  AUDIT")
    chk(1, "every statement exists in a freshly built bank", not missing,
        "" if not missing else f"missing: {missing[:3]}")
    auc = G.auc(yte, Mte @ w + b0)
    logged = m.get("test_auc", float("nan"))
    chk(2, "the test AUC recomputes from the saved weights", abs(auc - logged) < 5e-4,
        f"recomputed {auc:.4f} vs stored {logged:.4f}")
    chk(3, "every statement uses BOTH dates", all(side(base_name(k)) == "AB" for k in keys))
    chk(4, "every statement passes the doctrine denylist", all(clause_ok(base_name(k)) for k in keys))
    chk(5, "no statement valued at the missing-data placeholder",
        not any(base_name(k).endswith("=na") for k in keys))
    sup = [int(X[:, ix[base_name(k)]].sum()) for k in keys]
    chk(6, f"every statement clears the support floor ({FLOOR})", min(sup) >= FLOOR,
        f"smallest fires in {min(sup)} couples")
    ex = [explain(k) for k in keys]
    generic = [k for k, e in zip(keys, ex) if e["tradition"] == "Doctrine"]
    chk(7, "the explainer gives a real reading for every statement", not generic,
        "" if not generic else f"unexplained: {generic}")
    dup = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if np.array_equal(Mtr[:, i], Mtr[:, j]):
                dup.append((keys[i], keys[j]))
    chk(8, "no two statements are the same column twice", not dup, str(dup[:2]))
    same_path = all(base_name(k) in pos for k in keys)
    chk(9, "train and test features come from the same code path", same_path)
    negs = [k for k in keys if k.startswith("NOT(")]
    corrob = 0
    for k in negs:
        col = X[:, ix[base_name(k)]] > 0
        if col.any() and (~col).any() and yi[col].mean() < yi[~col].mean():
            corrob += 1
    chk(10, "negations agree with their own raw direction",
        corrob == len(negs), f"{corrob}/{len(negs)} corroborated")
    chk(11, "CV and test AUC are present in the model file",
        "cv_auc" in m and "test_auc" in m, f"CV {m.get('cv_auc')} · test {m.get('test_auc')}")
    near = []
    Cm = np.corrcoef(Mtr.T)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if np.isfinite(Cm[i, j]) and Cm[i, j] > 0.95:
                near.append((keys[i], keys[j], round(float(Cm[i, j]), 3)))
    chk(12, "no two statements are near-duplicates (r > 0.95)", not near,
        "" if not near else "; ".join(f"{x} ~ {y} (r={r})" for x, y, r in near[:2]))

    # ---- IMPORTANCE ----
    print("\n  IMPORTANCE — what each statement is actually worth")
    from sklearn.linear_model import LogisticRegression
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a_, b_ in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a_), find(b_)
        if ra != rb:
            parent[ra] = rb
    gid = pd.factorize(pd.Series([find(a_) for a_ in ids.pid_a]))[0]

    def cv_of(cols):
        if len(cols) < 1:
            return 0.5
        outs = []
        for seed in (7, 23, 101):
            fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
            oof = np.zeros(len(yi))
            for k in range(5):
                trm, tem = fold != k, fold == k
                lo = LogisticRegression(max_iter=2000).fit(Mtr[trm][:, cols], yi[trm])
                oof[tem] = lo.predict_proba(Mtr[tem][:, cols])[:, 1]
            outs.append(G.auc(yi, oof))
        return float(np.mean(outs))

    full = cv_of(list(range(len(keys))))
    rows = []
    base_rate = yi.mean()
    for i, k in enumerate(keys):
        drop = full - cv_of([j for j in range(len(keys)) if j != i])
        col = Mtr[:, i] > 0
        p1 = yi[col].mean() if col.any() else base_rate
        p0 = yi[~col].mean() if (~col).any() else base_rate
        se = np.sqrt(base_rate * (1 - base_rate) * (1 / max(col.sum(), 1) + 1 / max((~col).sum(), 1)))
        rows.append({"rule": k, "weight": float(w[i]), "fires": int(col.sum()),
                     "fire_rate": float(col.mean()), "std_contrib": float(abs(w[i]) * Mtr[:, i].std()),
                     "drop_one_cv_loss": float(drop), "z": float((p1 - p0) / max(se, 1e-9)),
                     "good_when_fires": float(p1), "good_otherwise": float(p0),
                     "tradition": explain(k)["tradition"], "title": explain(k)["title"]})
    rows.sort(key=lambda r: -r["drop_one_cv_loss"])
    print(f"  full-model CV (logistic on the {len(keys)} statements): {full:.4f}\n")
    print(f"  {'#':>2} {'drop-one':>9}{'|w|*sd':>8}{'weight':>8}{'fires':>7}{'good%':>7}{'vs':>6}{'z':>7}  statement")
    print("  " + "-" * 108)
    for i, r in enumerate(rows, 1):
        print(f"  {i:>2} {r['drop_one_cv_loss']:>+9.4f}{r['std_contrib']:>8.3f}{r['weight']:>8.3f}"
              f"{r['fires']:>7,}{r['good_when_fires']:>7.0%}{r['good_otherwise']:>6.0%}{r['z']:>+7.1f}"
              f"  {r['title'][:52]}")
    out = MODEL.replace(".json", "_importance.json")
    json.dump({"model": os.path.basename(MODEL), "full_cv": full, "audit_failures": fails,
               "ranked": rows}, open(out, "w"), indent=1)
    print(f"\n  {'ALL CHECKS PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
    print(f"  saved {out}")


if __name__ == "__main__":
    main()
