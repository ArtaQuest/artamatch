"""target_cca.py — the proxy for happiness that the sky explains best, in closed form.

THE REFRAMING. Hill-climbing over twelve keyword-group weights was searching a space of targets by
hand. But the question "which combination of words in the record does astrology best explain" is
canonical correlation analysis, and CCA has a closed form: find directions u in the astrology design
and v in the keyword design that maximise corr(Xu, Tv). The label is then a threshold of Tv — a
weighted keyword score, exactly the kind of thing bio_label_apply.py already ships — and u is the
astrology model that reads it.

!! THE `astro AUC` COLUMN THIS FILE PRINTS IS LEAKED. READ THIS BEFORE BELIEVING IT. !!

The canonical direction is fitted on ALL search couples, including the rows in every cross-validation
test fold. The label is therefore built with knowledge of the sky on the rows the sky is then scored
against, and the cross-validation only refits the sky-to-label regression — never the construction of
the label. The model ends up predicting a function of itself, and the column reads 0.85-0.89, which is
not astrology working. It is the leak, and it was left visible with this warning rather than deleted,
because a number like that appearing in a log is exactly how a project talks itself into a result.

CCA does not see a label, which is what made the leak easy to miss: there is no target to leak FROM.
The leaked quantity is the sky itself. The honest way to run this is a further split — fit the
direction on one part of the search half, apply it to the other — and the number that actually counts
is target_confirm.py, which freezes whatever definition came out of here and spends the confirm third
that bio_pool.py set aside before any of this existed. That protocol is unaffected by this fault,
because the confirm couples were never seen by the CCA either.

REGULARISATION BY TRUNCATION. With 3,000 astrology statements and 6,000 keywords over 9,643 couples,
an unregularised CCA would find a correlation of 1.0 and mean nothing. Both views are first reduced
to their leading singular directions, which is a clean, single-knob regulariser, and the number of
components is swept rather than assumed.

EXPLAINABLE AT THE END. The winning text direction is a dense weighting of 6,000 keywords, which no
one can read. It is therefore sparsified — the top-N keywords by absolute weight, refitted — and the
cost of that sparsification is measured rather than hoped away.
"""
import json, os, sys, time, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))

POOL = os.path.expanduser("~/.artamatch-dev/quality_pool")
OUT = os.path.expanduser(os.environ.get("AQ_RESULT", "~/.artamatch-dev/target_cca.json"))
KX = tuple(int(x) for x in os.environ.get("AQ_KX", "40,80,160,320").split(","))
KT = tuple(int(x) for x in os.environ.get("AQ_KT", "40,80,160,320").split(","))
KEEP = float(os.environ.get("AQ_KEEP", "0.60"))
LAM = float(os.environ.get("AQ_LAM", "300"))
NFOLD, SEEDS = 5, (7, 23)
TOPN = tuple(int(x) for x in os.environ.get("AQ_TOPN", "50,150,400,1000").split(","))


def fast_auc(y, s):
    o = np.argsort(s, kind="stable")
    r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1)
    ss = s[o]; i = 0
    while i < len(ss):
        j = i + 1
        while j < len(ss) and ss[j] == ss[i]:
            j += 1
        if j > i + 1:
            r[o[i:j]] = (i + 1 + j) / 2.0
        i = j
    n1 = y.sum(); n0 = len(y) - n1
    return 0.5 if n1 == 0 or n0 == 0 else (r[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def text_design(texts):
    from sklearn.feature_extraction.text import CountVectorizer
    from bio_label_apply import _allowed
    V = CountVectorizer(binary=True, lowercase=True, ngram_range=(1, 2), min_df=10,
                        token_pattern=r"(?u)\b\w[\w'-]+\b")
    X = V.fit_transform(texts)
    vocab = V.get_feature_names_out()
    keep = np.array([_allowed(t) for t in vocab])
    return X[:, keep].toarray().astype(np.float64), [t for t, k in zip(vocab, keep) if k]


def astro_cv_auc(Xa, gid, y, mask):
    """grouped ridge CV of the sky against a given label — the honest evaluation of one target"""
    from scipy.linalg import cho_factor, cho_solve
    Xc = Xa - Xa.mean(0)
    outs = []
    for s in SEEDS:
        fold = np.random.default_rng(s).integers(0, NFOLD, gid.max() + 1)[gid]
        pred = np.full(len(y), np.nan)
        for k in range(NFOLD):
            tr = (fold != k) & mask
            if tr.sum() < 200 or len(np.unique(y[tr])) < 2:
                continue
            A = Xc[tr]; t = y[tr] - y[tr].mean()
            c = cho_factor(A.T @ A + LAM * np.eye(A.shape[1]), lower=True, check_finite=False)
            beta = cho_solve(c, A.T @ t, check_finite=False)
            pred[fold == k] = Xc[fold == k] @ beta
        m = mask & np.isfinite(pred)
        if m.sum() < 200 or len(np.unique(y[m])) < 2:
            return 0.5
        outs.append(fast_auc(y[m].astype(int), pred[m]))
    return float(np.mean(outs))


def label_of(score, keep):
    lo, hi = np.quantile(score, [keep / 2, 1 - keep / 2])
    return (score >= hi).astype(int), (score <= lo) | (score >= hi)


def main():
    from target_fast import load
    sp, H, gid, Xa, anames = load()
    T, tnames = text_design(sp.desc.fillna("").astype(str))
    print(f"  {len(sp):,} search couples · sky {Xa.shape[1]:,} statements · "
          f"text {T.shape[1]:,} keywords")

    Xc = Xa - Xa.mean(0); Tc = T - T.mean(0)
    t0 = time.time()
    Ux, Sx, Vxt = np.linalg.svd(Xc, full_matrices=False)
    Ut, St, Vtt = np.linalg.svd(Tc, full_matrices=False)
    print(f"  both views decomposed in {time.time()-t0:.0f}s\n")

    # the reference: the shipped keyword labeller's own score, as a target
    from bio_label_apply import present
    M = json.load(open(os.path.expanduser("~/.artamatch-dev/label_model.json")))
    wt, b = M["weights"], M["intercept"]
    ref_score = np.array([b + sum(wt[k] for k in present(t) if k in wt)
                          for t in sp.desc.fillna("").astype(str)])
    y0, m0 = label_of(ref_score, KEEP)
    a0 = astro_cv_auc(Xa, gid, y0, m0)
    print(f"  the shipped auto-labeller as a target: {a0:.4f} on {int(m0.sum()):,} couples\n")

    print("  !! the astro AUC column below is LEAKED — see the note at the top of this file")
    print(f"  {'kx':>5}{'kt':>5}{'canon r':>10}{'astro AUC':>11}{'kept':>8}")
    print("  " + "-" * 40)
    best = (a0, None, None, 0, 0)
    for kx in KX:
        A = Ux[:, :kx]
        for kt in KT:
            B = Ut[:, :kt]
            u_, s_, v_ = np.linalg.svd(A.T @ B, full_matrices=False)
            # text-side canonical direction, mapped back to keyword weights
            vtxt = (Vtt[:kt].T * np.where(St[:kt] > 1e-9, 1.0 / St[:kt], 0.0)) @ v_[0]
            sc = Tc @ vtxt
            y, m = label_of(sc, KEEP)
            a = astro_cv_auc(Xa, gid, y, m)
            print(f"  {kx:>5}{kt:>5}{s_[0]:>10.4f}{a:>11.4f}{int(m.sum()):>8,}")
            if a > best[0]:
                best = (a, vtxt, (kx, kt), int(m.sum()), s_[0])
    if best[1] is None:
        print("\n  nothing beat the shipped labeller"); return
    a, vtxt, (kx, kt), kept, r = best
    print(f"\n  BEST kx={kx} kt={kt} · canonical r={r:.4f} · astro AUC {a:.4f} "
          f"(shipped labeller {a0:.4f})")

    print(f"\n  sparsifying the text direction — the dense one is unreadable")
    print(f"  {'keywords':>10}{'astro AUC':>11}")
    sparse = []
    for n_ in TOPN:
        idx = np.argsort(-np.abs(vtxt))[:n_]
        v2 = np.zeros_like(vtxt); v2[idx] = vtxt[idx]
        y2, m2 = label_of(Tc @ v2, KEEP)
        a2 = astro_cv_auc(Xa, gid, y2, m2)
        sparse.append({"n": n_, "auc": a2})
        print(f"  {n_:>10,}{a2:>11.4f}")

    top = np.argsort(-np.abs(vtxt))[:40]
    print(f"\n  the 40 keywords the sky leans on most")
    print(f"  {'keyword':<28}{'weight':>9}")
    for i in top:
        print(f"  {tnames[i]:<28}{vtxt[i]:>+9.4f}")
    json.dump({"kx": kx, "kt": kt, "canonical_r": float(r), "astro_auc": a,
               "shipped_labeller_auc": a0, "kept": kept, "keep": KEEP, "lam": LAM,
               "sparse": sparse,
               "weights": {tnames[i]: float(vtxt[i])
                           for i in np.argsort(-np.abs(vtxt))[:2000]}},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  saved {OUT}")
    print("  This is the SEARCH half. target_confirm.py spends the held-back third, once.")


if __name__ == "__main__":
    main()
