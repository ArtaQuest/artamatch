"""
rank_traditions.py — every tradition scored ALONE on the held-out set, and ranked.

WHY THIS IS CHEAP AND WHY IT IS HONEST. The stack keeps every base model's prediction, so a tradition's standalone
score needs no new training: take the base models that belong to that tradition, combine their held-out
predictions the way the stack would if it had nothing else, and score that. Every tradition is measured on the
SAME couples with the SAME metric as the ensemble, so the ranking and the leaderboard number sit on one scale.

WHAT "ALONE" MEANS. A tradition may contribute up to three base models. Its standalone score is a logistic
regression over just those base predictions, fitted on the training half's out-of-fold predictions and applied to
the held-out half — a mini-stack per tradition. That is fairer than taking its best single block, which would
reward traditions for having more blocks to be lucky with, and fairer than averaging, which would punish a
tradition with one strong block and two weak ones.

WHAT IS PRINTED. A ranked table: rank, tradition, held-out AUC, how many base models it has, and whether it beats
the era rule computed on the same rows. That last column is the one that matters on a temporal split — a
tradition above chance but below the era rule has read the calendar.

Usage: AQ_MODEL=/tmp/aqcleanmodel AQ_TEST=/tmp/aqclean/test.csv AQ_SOL=/tmp/aqcompclean/solution.csv
       ~/.artamatch-venv/bin/python rank_traditions.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import competition_metric as cm          # noqa: E402

MODEL = os.environ.get("AQ_MODEL", "/tmp/aqcleanmodel")
SOL = os.environ.get("AQ_SOL", "/tmp/aqcompclean/solution.csv")
TEST = os.environ.get("AQ_TEST", "/tmp/aqclean/test.csv")

# Human-facing names, matching the page.
NAMES = {
    "harmonics": "Chart geometry (harmonics)", "lunar_calendrical": "Eclipse and lunation cycles",
    "uranian": "Hamburg School / Uranian", "babylonian_egyptian": "Babylonian and Egyptian",
    "african": "African heliacal risings", "mesoamerican": "Maya Long Count and Calendar Round",
    "indigenous_americas": "Northern skywatching", "aboriginal_australian": "Australian Aboriginal",
    "modern_western": "Modern Western (Davison / composite)", "hellenistic": "Hellenistic",
    "persian_arabic": "Persian and Arabic", "vedic_core": "Jyotiṣa: nakṣatras, vargas, daśās",
    "vedic_ashtakavarga": "Aṣṭakavarga and ṣaḍbala", "vedic_match": "Vedic marriage matching (aṣṭakūṭa)",
    "chinese": "Chinese (BaZi, five phases)", "east_asian_deep": "Zǐ Wēi, saju, zurkhai",
    "tibetan_seasia": "Tibetan, Burmese, Javanese", "polynesian": "Māori maramataka / Hawaiian mahina",
    "numerology": "Numerology (Pythagorean and Chaldean)",
}


def main():
    hdr = json.load(open(os.path.join(MODEL, "model.json")))
    base = hdr["base"]
    # Out-of-fold base predictions on the training half, and base predictions on the held-out half. Both are
    # written by train_on_csv.py beside the model.
    oof = np.load(os.path.join(MODEL, "oof_base.npy"))            # (n_train, n_base)
    y_tr = np.load(os.path.join(MODEL, "y_train.npy"))
    P_te = np.load(os.path.join(MODEL, "test_base.npy"))          # (n_test, n_base)
    test_ids = pd.read_csv(TEST)["id"].to_numpy()
    sol = pd.read_csv(SOL).set_index("id")
    # The target column is whatever the solution file calls it — `lasted_30_years` for the duration dataset,
    # `parents_together` for the retired parenthood one. Hardcoding it silently ranked nothing when it changed.
    lab = [c for c in sol.columns if c != "Usage"]
    if len(lab) != 1:
        raise SystemExit(f"solution.csv should have one target column beside Usage, found {lab}")
    lab = lab[0]
    keep = np.isin(test_ids, sol.index.to_numpy())
    P_te, ids = P_te[keep], test_ids[keep]
    y_te = sol.loc[ids, lab].to_numpy()
    usage = sol.loc[ids, "Usage"].to_numpy()
    print(f"  target column: {lab}")

    print(f"  {len(base)} base models, {oof.shape[0]:,} training couples, {len(ids):,} held-out day-precision couples")

    # The era rule on the same held-out rows: older couple = more likely. The bar every tradition must clear.
    te = pd.read_csv(TEST).set_index("id").loc[ids]
    era = -(te["dob_older"].str[:4].astype(int) + te["dob_younger"].str[:4].astype(int)).to_numpy(float)
    era_auc = max(cm._auc(y_te, era), 1 - cm._auc(y_te, era))

    slugs = sorted({b["slug"] for b in base})
    rows = []
    for slug in slugs:
        cols = [i for i, b in enumerate(base) if b["slug"] == slug]
        clf = LogisticRegression(max_iter=2000, C=1.0).fit(oof[:, cols], y_tr)
        p = clf.predict_proba(P_te[:, cols])[:, 1]
        a = cm._auc(y_te, p)
        pub = usage == "Public"
        # Plain Python types, because json.dump refuses numpy's. `a > era_auc` is a numpy bool when `a` is a numpy
        # float, and that crashed the ranking's write step -- caught on a fixture, before the real run.
        rows.append({"tradition": slug, "name": NAMES.get(slug, slug), "auc": float(a),
                     "public": float(cm._auc(y_te[pub], p[pub])), "private": float(cm._auc(y_te[~pub], p[~pub])),
                     "n_base": int(len(cols)), "beats_era": bool(a > era_auc)})
    # And the full ensemble, from the same files, so the table has its top line.
    meta_w = np.array(hdr.get("meta", {}).get("w", []), dtype=float)
    if meta_w.size == len(base):
        z = P_te @ meta_w + float(hdr.get("meta", {}).get("b", 0.0))
        p_all = 1 / (1 + np.exp(-z))
    else:
        clf = LogisticRegression(max_iter=2000).fit(oof, y_tr)
        p_all = clf.predict_proba(P_te)[:, 1]
    a_all = cm._auc(y_te, p_all)

    rows.sort(key=lambda r: -r["auc"])
    print(f"\n  RANKED, held-out AUC, temporal split. Era rule on these rows: {era_auc:.4f}\n")
    print(f"  {'#':>2}  {'tradition':<40} {'AUC':>7} {'public':>8} {'private':>8}  {'blocks':>6}  vs era")
    print(f"  {'':>2}  {'THE FULL ENSEMBLE':<40} {a_all:>7.4f} {'':>8} {'':>8}  {len(base):>6}  "
          f"{'above' if a_all > era_auc else 'below'}")
    for i, r in enumerate(rows, 1):
        print(f"  {i:>2}  {r['name']:<40} {r['auc']:>7.4f} {r['public']:>8.4f} {r['private']:>8.4f}  "
              f"{r['n_base']:>6}  {'above' if r['beats_era'] else 'below'}")

    out = {"era_rule": float(era_auc), "ensemble": float(a_all), "n_test": int(len(ids)),
           "traditions": rows}
    json.dump(out, open(os.path.join(MODEL, "tradition_ranking.json"), "w"), indent=1)
    print(f"\n  wrote {os.path.join(MODEL, 'tradition_ranking.json')}")


if __name__ == "__main__":
    main()
