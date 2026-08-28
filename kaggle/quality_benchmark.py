"""quality_benchmark.py — what the doctrine model has to beat on the marriage-quality targets.

Two reference points, both read on the same held-out couples:
  · chance (0.5000)
  · the standing baseline for this project: a two-parameter logistic on the SIGNED difference of the
    two birth dates. It is the one comparator that is allowed here, because it uses nothing but the
    two dates — exactly what the astrology reads — and so cannot be dismissed as a confound.

Also reports the base rate and the standard error of a test AUC at that size, so a difference between
two models can be judged against what the test set can actually resolve.
"""
import glob, json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
import giant_ensemble as G
DEV = os.path.expanduser("~/.artamatch-dev")


def jdn(s):
    y, m, d = (int(x) for x in str(s).split("-"))
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def auc_se(y):
    """Hanley-McNeil standard error of an AUC at 0.5, given the class counts"""
    n1 = int(np.sum(y)); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    a = 0.5
    q1 = a / (2 - a); q2 = 2 * a * a / (1 + a)
    return float(np.sqrt((a * (1 - a) + (n1 - 1) * (q1 - a * a) + (n0 - 1) * (q2 - a * a)) / (n1 * n0)))


def main():
    from sklearn.linear_model import LogisticRegression
    print(f"{'target':<16}{'n test':>8}{'pos':>7}{'chance':>9}{'age-gap':>10}{'AUC SE':>9}")
    targets = sys.argv[1:] or ["quality_good", "quality_good_narr"]
    for t in targets:
        d = f"{DEV}/{t}"
        if not os.path.exists(f"{d}/train.csv"):
            continue
        tr = pd.read_csv(f"{d}/train.csv", dtype=str)
        te = pd.read_csv(f"{d}/test.csv", dtype=str)
        sol = pd.read_csv(f"{d}/solution.csv")
        ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
        yte = sol.ended_in_divorce.to_numpy().astype(int)
        gtr = np.array([[jdn(a) - jdn(b)] for a, b in zip(tr.dob_a, tr.dob_b)], float) / 365.25
        gte = np.array([[jdn(a) - jdn(b)] for a, b in zip(te.dob_a, te.dob_b)], float) / 365.25
        m = LogisticRegression(max_iter=2000).fit(gtr, ytr)
        agegap = G.auc(yte, m.predict_proba(gte)[:, 1])
        print(f"{t:<16}{len(yte):>8,}{yte.mean():>6.1%}{0.5:>9.4f}{agegap:>10.4f}{auc_se(yte):>9.4f}")
        json.dump({"target": t, "n_test": int(len(yte)), "pos_rate": float(yte.mean()),
                   "age_gap_auc": float(agegap), "auc_se": auc_se(yte)},
                  open(f"{DEV}/{t}_benchmark.json", "w"), indent=1)


if __name__ == "__main__":
    main()
