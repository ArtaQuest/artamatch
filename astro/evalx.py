"""
evalx.py — the one scorer. Every tradition module and every ensemble is measured through this.

WHAT IT GUARANTEES

  PERSON-DISJOINT SPLITS. Some people appear in more than one marriage in this dataset. A random row
    split would put the same person's charts on both sides and inflate everything. Splits are therefore
    made over the union-find person groups computed in core.py, never over rows.
  THE SAME SPLITS FOR EVERYONE. The split list is seeded and shared, so two feature blocks are compared
    on identical test sets and a difference between them cannot be a difference of split luck.
  MANY SPLITS, NEVER ONE. Every score is a mean over N splits with its standard deviation reported. A
    single split on this data swings several points; one lucky split is not a result.
  HONEST STACKING. Meta-learners are trained on OUT-OF-FOLD base predictions only, produced by an inner
    group-aware fold inside each outer training set. A base model never predicts on data it saw.

METRICS: accuracy (the classes are balanced exactly, so 50% is chance) and ROC AUC.

Usage:
    from core import load
    from evalx import quick, score, MODELS
    E = load()
    quick(E, X)                       # fast single-number check while developing a module
    score(E, {"my block": X})         # the real thing: every model, every split
"""

import os
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, GroupKFold

N_SPLITS = 20
TEST_FRAC = 0.30
SEED = 20260809


def splits(E, n=N_SPLITS, test=TEST_FRAC, seed=SEED):
    gss = GroupShuffleSplit(n_splits=n, test_size=test, random_state=seed)
    return list(gss.split(np.zeros(E.n), E.Y, groups=E.gid))


def _clean(X):
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[:, None]
    return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


# ── the model zoo ───────────────────────────────────────────────────────────────────────────────
def MODELS(nfeat):
    """Model factories.

    n_jobs is deliberately 1 everywhere. The sweep already runs one process per (block, representation),
    so a forest asking for every core inside each of six workers spawned eight subprocesses each and drove
    the load average past 300 — the machine spent its time context-switching rather than fitting. Kept small enough to run over dozens of blocks, wide enough to be fair.

    Linear, tree, kernel, neighbour, and neural families are all present, because feature
    representations that suit one can be invisible to another: an aspect-orb block is nearly linear,
    while a sign-pair block is pure interaction and needs a tree or a kernel to see anything.
    """
    npc = int(max(2, min(64, nfeat // 2)))
    m = {
        "logistic L2 (C=0.01)": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.01, max_iter=3000)),
        "logistic L2 (C=0.1)": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000)),
        "logistic L2 (C=1)": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=3000)),
        "logistic L1 (C=0.1)": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, penalty="l1", solver="liblinear", max_iter=3000)),
        "hist gradient boosting": lambda: HistGradientBoostingClassifier(max_iter=_n(300), learning_rate=0.06, max_leaf_nodes=15, l2_regularization=1.0, random_state=0),
        "random forest": lambda: RandomForestClassifier(n_estimators=_n(400), min_samples_leaf=4, n_jobs=1, random_state=0),
        "extra trees": lambda: ExtraTreesClassifier(n_estimators=_n(400), min_samples_leaf=4, n_jobs=1, random_state=0),
        "MLP (128,64)": lambda: make_pipeline(StandardScaler(), MLPClassifier((128, 64), alpha=1e-2, max_iter=600, early_stopping=True, random_state=0)),
        "SVM rbf": lambda: make_pipeline(StandardScaler(), SVC(C=1.0, gamma="scale", probability=True, random_state=0)),
        "kNN (k=45)": lambda: make_pipeline(StandardScaler(), KNeighborsClassifier(45)),
        "LDA": lambda: make_pipeline(StandardScaler(), LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        "gaussian NB": lambda: make_pipeline(StandardScaler(), GaussianNB()),
    }
    m.update(_boosters(nfeat))
    if nfeat > 8:
        m["PCA + logistic"] = lambda: make_pipeline(StandardScaler(), PCA(n_components=npc, random_state=0), LogisticRegression(C=1.0, max_iter=3000))
        m["PCA + SVM rbf"] = lambda: make_pipeline(StandardScaler(), PCA(n_components=npc, random_state=0), SVC(C=2.0, probability=True, random_state=0))
    return m


# ── state-of-the-art gradient boosting, when the environment has it ─────────────────────────────
# XGBoost, LightGBM and CatBoost are the three that win tabular competitions, and all three are
# preinstalled on Kaggle. Locally LightGBM cannot even load its OpenMP library, so each import is
# guarded and the zoo simply omits what is missing rather than failing. Every one is pinned to a single
# thread: the sweep parallelises over blocks, so inner threading only causes contention.
# A sweep-speed scale factor. At 70,000 rows a catboost with 800 iterations takes minutes per fit, and
# 54 (block, representation) jobs x 7 models x 6 splits made the deep stage a six-hour run that completed
# nothing in its first ten minutes. FAST=0.3 cuts every booster's iteration budget proportionally; the
# final model is refitted at full budget, so only the SEARCH is cheapened, not the result.
FAST = float(os.environ.get("AQ_FAST", "1.0"))


def _n(x):
    return max(60, int(x * FAST))


def _boosters(nfeat):
    out = {}
    try:
        from xgboost import XGBClassifier
        out["xgboost"] = lambda: XGBClassifier(
            n_estimators=_n(600), learning_rate=0.03, max_depth=5, subsample=0.8,
            colsample_bytree=0.6, reg_lambda=2.0, min_child_weight=4, n_jobs=1,
            tree_method="hist", eval_metric="logloss", random_state=0)
        out["xgboost deep"] = lambda: XGBClassifier(
            n_estimators=_n(1200), learning_rate=0.015, max_depth=8, subsample=0.7,
            colsample_bytree=0.4, reg_lambda=5.0, min_child_weight=8, n_jobs=1,
            tree_method="hist", eval_metric="logloss", random_state=0)
    except Exception:
        pass
    try:
        from lightgbm import LGBMClassifier
        out["lightgbm"] = lambda: LGBMClassifier(
            n_estimators=_n(800), learning_rate=0.03, num_leaves=31, subsample=0.8,
            subsample_freq=1, colsample_bytree=0.6, reg_lambda=2.0, min_child_samples=20,
            n_jobs=1, verbose=-1, random_state=0)
        out["lightgbm dart"] = lambda: LGBMClassifier(
            boosting_type="dart", n_estimators=_n(600), learning_rate=0.05, num_leaves=63,
            colsample_bytree=0.5, reg_lambda=3.0, n_jobs=1, verbose=-1, random_state=0)
    except Exception:
        pass
    try:
        from catboost import CatBoostClassifier
        out["catboost"] = lambda: CatBoostClassifier(
            iterations=_n(800), learning_rate=0.03, depth=6, l2_leaf_reg=6.0,
            rsm=0.6, thread_count=1, verbose=0, allow_writing_files=False, random_seed=0)
    except Exception:
        pass
    return out


def _proba(mdl, X):
    if hasattr(mdl, "predict_proba"):
        return mdl.predict_proba(X)[:, 1]
    d = mdl.decision_function(X)
    return 1 / (1 + np.exp(-d))


def fit_predict(factory, X, y, tr, te):
    mdl = factory()
    mdl.fit(X[tr], y[tr])
    p = _proba(mdl, X[te])
    return p


def quick(E, X, model="hist gradient boosting", n=5):
    """A fast check while developing. Not a result — `score` is."""
    X = _clean(X)
    y = E.Y
    accs, aucs = [], []
    for tr, te in splits(E, n=n):
        p = fit_predict(MODELS(X.shape[1])[model], X, y, tr, te)
        accs.append(((p > 0.5).astype(float) == y[te]).mean())
        aucs.append(roc_auc_score(y[te], p))
    return float(np.mean(accs)), float(np.mean(aucs))


def score(E, blocks, models=None, n=N_SPLITS, verbose=True, only=None):
    """Score every block with every model over the shared splits.

    Returns {(block, model): dict(acc, acc_sd, auc, auc_sd)}.
    """
    sp = splits(E, n=n)
    out = {}
    for bname, X in blocks.items():
        X = _clean(X)
        zoo = models or MODELS(X.shape[1])
        if only:
            zoo = {k: v for k, v in zoo.items() if k in only}
        for mname, f in zoo.items():
            A, U = [], []
            for tr, te in sp:
                try:
                    p = fit_predict(f, X, E.Y, tr, te)
                except Exception as e:
                    A, U = [], []
                    if verbose:
                        print(f"  {bname} / {mname}: FAILED {str(e)[:70]}")
                    break
                A.append(((p > 0.5).astype(float) == E.Y[te]).mean())
                U.append(roc_auc_score(E.Y[te], p))
            if not A:
                continue
            out[(bname, mname)] = {"acc": float(np.mean(A)), "acc_sd": float(np.std(A)),
                                   "auc": float(np.mean(U)), "auc_sd": float(np.std(U)),
                                   "cols": X.shape[1]}
            if verbose:
                r = out[(bname, mname)]
                print(f"  {bname[:34]:<34} {mname[:24]:<24} {100*r['acc']:>6.2f}% +-{100*r['acc_sd']:>4.2f}"
                      f"   AUC {r['auc']:.4f}")
    return out


def oof_matrix(E, blocks, chosen, inner=5, seed=SEED):
    """Out-of-fold base predictions for stacking, over group-aware inner folds.

    `chosen` is a list of (block_name, model_name). Returns (n_couples, n_base) of OOF probabilities.
    Every value is produced by a model that did NOT see that couple's group in training.
    """
    P = np.zeros((E.n, len(chosen)))
    gkf = GroupKFold(n_splits=inner)
    folds = list(gkf.split(np.zeros(E.n), E.Y, groups=E.gid))
    for j, (bn, mn) in enumerate(chosen):
        X = _clean(blocks[bn])
        f = MODELS(X.shape[1])[mn]
        for tr, te in folds:
            P[te, j] = fit_predict(f, X, E.Y, tr, te)
    return P
