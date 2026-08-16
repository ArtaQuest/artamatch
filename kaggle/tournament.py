"""
tournament.py — the baselines, and then the accounts take turns beating each other.

THE SHAPE. `artafather` posts every tradition ALONE as a public baseline, so the leaderboard shows what each
tradition is worth on its own before anyone ensembles anything. Then the other accounts enter in turn: each reads
the current leaderboard, builds a stacked ensemble that tries to beat the best score posted so far, and submits it.
Every submission carries a message saying exactly what it is, so the leaderboard reads as a record rather than a
pile of numbers.

WHAT AN ENSEMBLE IS ALLOWED TO BE. A weighted stack over the same per-tradition base predictions the baselines use
— the same 19 traditions, the same held-out couples — with the weights fitted on the training half's out-of-fold
predictions. Each turn tries a different family: logistic over all bases; logistic over the top-k traditions by
their own out-of-fold score; a rank-average; a non-negative least-squares blend; boosting over the base columns.
None of them sees the held-out labels. The point is to find out how much stacking is worth on a TEMPORAL split,
which is a question the leaderboard is well placed to answer and one prompt cannot.

ONE PROCESS PER ACCOUNT, ALWAYS. The Kaggle client authenticates at IMPORT, so a credential swapped inside a
running process still acts as the account it started as. This script is invoked once per account per turn and
never rotates; the caller sequences the turns.

FIVE SUBMISSIONS PER ACCOUNT PER DAY, and that is not host-settable — three candidate field names all answer
"Cannot find field" and GetSubmissionLimits reports numAllowedNow: 5. So the twenty baselines take four days from
one account, and each ensemble account gets five turns a day. The runner records what it has already sent in a
ledger and resumes from there, so it can be invoked once a day and simply continues.

SUBMISSIONS ONLY SCORE ONCE THE METRIC IS SET. `CompetitionSettings` has no metric field, so that is one dropdown
in the UI. Until then a submission is accepted and sits at "pending"; the file is still uploaded and the message
still recorded, so nothing is lost — the scores appear when the metric does. `--dry-run` writes every file and
prints every message without submitting.

Usage:
    python tournament.py baselines <account>              # every tradition alone
    python tournament.py turn <account> <strategy>        # one ensemble entry: all|topk|rank|nnls|boost
    python tournament.py board                             # print the leaderboard
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import competition_metric as cm          # noqa: E402

COMP = os.environ.get("AQ_COMP", "artamatch-astrology")
MODEL = os.environ.get("AQ_MODEL", "/tmp/aqcleanmodel")
TEST = os.environ.get("AQ_TEST", "/tmp/aqclean/test.csv")
COMP_TEST = os.environ.get("AQ_COMP_TEST", "/tmp/aqcompclean/test.csv")
OUT = os.environ.get("AQ_SUBS", "/tmp/aqsubs")
DRY = "--dry-run" in sys.argv

NAMES = {
    "harmonics": "Chart geometry (harmonics)", "lunar_calendrical": "Eclipse and lunation cycles",
    "uranian": "Hamburg School / Uranian", "babylonian_egyptian": "Babylonian and Egyptian",
    "african": "African heliacal risings", "mesoamerican": "Maya Long Count and Calendar Round",
    "indigenous_americas": "Northern skywatching", "aboriginal_australian": "Australian Aboriginal",
    "modern_western": "Modern Western (Davison / composite)", "hellenistic": "Hellenistic",
    "persian_arabic": "Persian and Arabic", "vedic_core": "Jyotisa: naksatras, vargas, dasas",
    "vedic_ashtakavarga": "Astakavarga and sadbala", "vedic_match": "Vedic marriage matching (astakuta)",
    "chinese": "Chinese (BaZi, five phases)", "east_asian_deep": "Zi Wei, saju, zurkhai",
    "tibetan_seasia": "Tibetan, Burmese, Javanese", "polynesian": "Maori maramataka / Hawaiian mahina",
    "numerology": "Numerology (Pythagorean and Chaldean)",
}


def account(name):
    """Bind THIS process to one account. Refuses if the file names somebody else."""
    os.environ.pop("KAGGLE_API_TOKEN", None)
    cr = json.load(open(os.path.expanduser(f"~/.kaggle/kaggle.{name}.json")))
    if cr["username"] != name:
        raise SystemExit(f"the file for {name} names {cr['username']!r} — refusing")
    os.environ["KAGGLE_USERNAME"], os.environ["KAGGLE_KEY"] = cr["username"], cr["key"]
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    return api


def load_matrices():
    """The per-base predictions the trainer saved, aligned to the competition's test ids."""
    hdr = json.load(open(os.path.join(MODEL, "model.json")))
    base = hdr["base"]
    oof = np.load(os.path.join(MODEL, "oof_base.npy")).astype(np.float64)
    y_tr = np.load(os.path.join(MODEL, "y_train.npy")).astype(int)
    P_te = np.load(os.path.join(MODEL, "test_base.npy")).astype(np.float64)
    all_ids = pd.read_csv(TEST)["id"].to_numpy()
    comp_ids = pd.read_csv(COMP_TEST)["id"].to_numpy()
    pos = {i: k for k, i in enumerate(all_ids)}
    rows = np.array([pos[i] for i in comp_ids])
    return base, oof, y_tr, P_te[rows], comp_ids


def write_submission(ids, p, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.csv")
    pd.DataFrame({"id": ids, "parents_together": np.clip(p, 0, 1)}).to_csv(path, index=False)
    return path


LEDGER = os.path.join(OUT, "ledger.json")


def _ledger():
    return json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}


def _record(acct, name, message, ok):
    L = _ledger()
    L.setdefault(acct, {})[name] = {"message": message, "sent": bool(ok), "at": time.strftime("%Y-%m-%d %H:%M")}
    os.makedirs(OUT, exist_ok=True)
    json.dump(L, open(LEDGER, "w"), indent=1)


def already_sent(acct, name):
    return _ledger().get(acct, {}).get(name, {}).get("sent", False)


def submit(api, path, message, acct=None):
    name = os.path.basename(path)[:-4]
    if acct and already_sent(acct, name):
        print(f"    skip {name:<40} (already sent by {acct})")
        return "sent"
    if DRY:
        print(f"    DRY  {name:<40} {message[:70]}")
        return None
    for i in range(4):
        try:
            r = api.competition_submit(path, message, COMP, quiet=True)
            print(f"    sent {name:<40} {message[:70]}")
            if acct:
                _record(acct, name, message, True)
            return r
        except Exception as e:
            s = str(e)
            if "limit" in s.lower() or "429" in s or "exceeded" in s.lower():
                print(f"    daily limit reached — run again tomorrow, the ledger resumes: {s[:80]}")
                return "limit"
            if i == 3:
                print(f"    failed: {s[:120]}")
                return None
            time.sleep(5 * (i + 1))


def fit_tradition(base, oof, y_tr, P_te, slug):
    from sklearn.linear_model import LogisticRegression
    cols = [i for i, b in enumerate(base) if b["slug"] == slug]
    clf = LogisticRegression(max_iter=2000).fit(oof[:, cols], y_tr)
    return clf.predict_proba(P_te[:, cols])[:, 1], cols


def baselines(acct):
    api = account(acct)
    base, oof, y_tr, P_te, ids = load_matrices()
    slugs = sorted({b["slug"] for b in base})
    print(f"  {acct}: {len(slugs)} traditions as baselines, {len(ids):,} test couples")
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import cross_val_predict
    from sklearn.linear_model import LogisticRegression
    for slug in slugs:
        p, cols = fit_tradition(base, oof, y_tr, P_te, slug)
        # An honest out-of-fold estimate on the TRAINING half, so the message carries a number the entrant can
        # check without the private labels.
        cvp = cross_val_predict(LogisticRegression(max_iter=2000), oof[:, cols], y_tr, cv=5,
                                method="predict_proba")[:, 1]
        est = roc_auc_score(y_tr, cvp)
        path = write_submission(ids, p, f"baseline_{slug}")
        r = submit(api, path, f"BASELINE {NAMES.get(slug, slug)} alone — {len(cols)} block(s); "
                              f"train OOF {est:.4f}. Not an ensemble.", acct=acct)
        if r == "limit":
            return
    # And the reference nobody should lose to.
    te = pd.read_csv(COMP_TEST).set_index("id").loc[ids]
    era = -(te["dob_man"].str[:4].astype(int) + te["dob_woman"].str[:4].astype(int)).to_numpy(float)
    era = (era - era.min()) / (era.max() - era.min() + 1e-9)
    path = write_submission(ids, era, "reference_era_rule")
    submit(api, path, "REFERENCE the era rule: older couple = more likely. Beat this or you read the calendar.",
           acct=acct)


def ensemble(strategy, base, oof, y_tr, P_te, k=6):
    """One ensemble family. Every one fits on the training half's out-of-fold predictions only."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import cross_val_predict
    from sklearn.ensemble import HistGradientBoostingClassifier
    if strategy == "all":
        m = LogisticRegression(C=0.03, max_iter=4000)
        est = roc_auc_score(y_tr, cross_val_predict(m, oof, y_tr, cv=5, method="predict_proba")[:, 1])
        return m.fit(oof, y_tr).predict_proba(P_te)[:, 1], est, "logistic over all base predictions"
    if strategy == "topk":
        slugs = sorted({b["slug"] for b in base})
        score = {}
        for s in slugs:
            cols = [i for i, b in enumerate(base) if b["slug"] == s]
            score[s] = roc_auc_score(y_tr, cross_val_predict(LogisticRegression(max_iter=2000), oof[:, cols],
                                                             y_tr, cv=5, method="predict_proba")[:, 1])
        top = sorted(score, key=lambda s: -score[s])[:k]
        cols = [i for i, b in enumerate(base) if b["slug"] in top]
        m = LogisticRegression(C=0.03, max_iter=4000)
        est = roc_auc_score(y_tr, cross_val_predict(m, oof[:, cols], y_tr, cv=5, method="predict_proba")[:, 1])
        return (m.fit(oof[:, cols], y_tr).predict_proba(P_te[:, cols])[:, 1], est,
                f"logistic over the top-{k} traditions by train OOF: {', '.join(top)}")
    if strategy == "rank":
        from scipy.stats import rankdata
        R = np.column_stack([rankdata(P_te[:, j]) for j in range(P_te.shape[1])])
        Ro = np.column_stack([rankdata(oof[:, j]) for j in range(oof.shape[1])])
        est = roc_auc_score(y_tr, Ro.mean(1))
        return R.mean(1) / len(R), est, "rank-average of every base prediction"
    if strategy == "nnls":
        from scipy.optimize import nnls
        w, _ = nnls(oof, y_tr.astype(float))
        w = w / (w.sum() + 1e-12)
        est = roc_auc_score(y_tr, oof @ w)
        used = int((w > 1e-6).sum())
        return P_te @ w, est, f"non-negative least-squares blend, {used} bases with weight"
    if strategy == "boost":
        m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, random_state=7)
        est = roc_auc_score(y_tr, cross_val_predict(m, oof, y_tr, cv=5, method="predict_proba")[:, 1])
        return m.fit(oof, y_tr).predict_proba(P_te)[:, 1], est, "gradient boosting over the base predictions"
    raise SystemExit(f"unknown strategy {strategy}")


def turn(acct, strategy):
    api = account(acct)
    base, oof, y_tr, P_te, ids = load_matrices()
    p, est, what = ensemble(strategy, base, oof, y_tr, P_te)
    best = board_best(api)
    path = write_submission(ids, p, f"{acct}_{strategy}")
    msg = (f"ENSEMBLE by {acct}: {what}; train OOF {est:.4f}"
           + (f"; trying to beat the board's {best:.4f}" if best else ""))
    submit(api, path, msg, acct=acct)


def board_best(api):
    try:
        rows = api.competition_leaderboard_view(COMP, page_size=50) or []
        scores = [float(getattr(r, "score", None) or 0) for r in rows if getattr(r, "score", None)]
        return max(scores) if scores else None
    except Exception:
        return None


def board():
    api = account("artafather")
    rows = api.competition_leaderboard_view(COMP, page_size=50) or []
    print(f"  {'#':>2}  {'team':<24} {'score':>8}  submissions")
    for i, r in enumerate(rows, 1):
        print(f"  {i:>2}  {str(getattr(r,'team_name','?')):<24} {str(getattr(r,'score','pending')):>8}  "
              f"{getattr(r,'submission_count','?')}")
    if not rows:
        print("  (empty — the metric is not set yet, so nothing has scored)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "baselines":
        baselines(sys.argv[2])
    elif cmd == "turn":
        turn(sys.argv[2], sys.argv[3])
    elif cmd == "board":
        board()
