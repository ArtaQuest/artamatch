"""bio_keywords.py — label a marriage from its text, with keywords and nothing else.

No model call, no judge, no API. A description goes in, a score comes out, and the same description
always produces the same score. That buys three things the AI pass could not: it runs over the whole
corpus for nothing, it cannot drift between batches, and anyone can re-run it and get our numbers.

HOW. Every description becomes a bag of binary keyword indicators. An L1-penalised logistic
regression then picks the smallest set of keywords that reproduces the 10,000 existing judgements,
which is the only ground truth we have. The surviving keywords ARE the labeller — a weighted word
list a person can read, argue with and edit.

WHAT IS BEING MAXIMISED, AND WHAT MUST NOT BE. The AUC here is the keyword set against the EXISTING
LABELS: how well can text alone reproduce what the judges said. It is a measure of the labeller.
It must never be tuned against the astrology model's score — choosing a target because it flatters
the thing being measured is how a result becomes a fiction. So this file never sees a chart, and the
era check at the end is reported whether it is flattering or not.

  AQ_NGRAM=1,2     word n-gram range          AQ_MINDF=25    minimum document frequency
  AQ_CHAR=1        add character 3-5 grams (for the CJK share of the corpus, which has no spaces)
  AQ_TARGET=good   which column to reproduce
"""
import json, os, re, sys, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

BIO = os.path.expanduser("~/.artamatch-dev/bio")
OUT = os.path.expanduser(os.environ.get("AQ_OUT", "~/.artamatch-dev/keywords.json"))
NGRAM = tuple(int(x) for x in os.environ.get("AQ_NGRAM", "1,2").split(","))
MINDF = int(os.environ.get("AQ_MINDF", "25"))
CHAR = os.environ.get("AQ_CHAR", "0") == "1"
TARGET = os.environ.get("AQ_TARGET", "good")
CS = tuple(float(x) for x in os.environ.get(
    "AQ_CS", "0.003,0.01,0.03,0.1,0.3,1.0").split(","))
SEEDS = (7, 23, 101)

# Words that name WHO someone was rather than WHAT the marriage was. A keyword labeller will happily
# learn that "actress" means a 20th-century marriage and therefore a likelier divorce, which is the
# exact confound this project is trying to remove, so the professions and the century markers are
# refused by name before the fit ever sees them.
BAN = re.compile(
    r"^(actress|actor|film|movie|hollywood|television|tv|singer|band|album|rock|pop|jazz|"
    r"footballer|player|coach|nazi|soviet|ussr|nato|wwi|wwii|1[6-9]\d\d|20\d\d|19\d\d|"
    r"century|born|died|birth|death|aged|age)$")


STEM = int(os.environ.get("AQ_STEM", "0"))       # truncate every token to N characters
TFIDF = os.environ.get("AQ_TFIDF", "0") == "1"
L1R = float(os.environ.get("AQ_L1RATIO", "1.0"))  # 1.0 = pure lasso; below that, elastic net

_TOK = re.compile(r"(?u)\b\w[\w'-]+\b")


def _stem(t):
    """Crude prefix stemming. `divorce`, `divorced`, `divorcing` and `divorces` are one idea spread
    over four features, and each is weaker for it — worse in the inflected languages, where a fifth
    of this corpus lives. Truncating to N characters merges them without a language-specific
    stemmer, which we cannot have for twenty-one languages."""
    return " ".join(w[:STEM] for w in _TOK.findall(t.lower()))


def vectorise(texts):
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from scipy.sparse import hstack
    if STEM:
        texts = [_stem(t) for t in texts]
    mats, names = [], []
    V = TfidfVectorizer if TFIDF else CountVectorizer
    kw = dict(lowercase=True, ngram_range=NGRAM, min_df=MINDF,
              token_pattern=r"(?u)\b\w[\w'-]+\b")
    w = V(sublinear_tf=True, **kw) if TFIDF else V(binary=True, **kw)
    mats.append(w.fit_transform(texts)); names += list(w.get_feature_names_out())
    if CHAR:
        c = CountVectorizer(binary=True, lowercase=True, analyzer="char_wb",
                            ngram_range=(3, 5), min_df=MINDF * 4)
        mats.append(c.fit_transform(texts)); names += [f"~{s}" for s in c.get_feature_names_out()]
    X = hstack(mats).tocsr()
    keep = np.array([not BAN.match(n.split()[0]) for n in names])
    return X[:, keep], [n for n, k in zip(names, keep) if k]


def main():
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    d = pd.read_csv(f"{BIO}/marriage_quality_binary.csv")
    d["desc"] = d.description.fillna("").astype(str)
    y = d[TARGET].astype(int).to_numpy()
    X, names = vectorise(d.desc.tolist())
    print(f"  {len(d):,} descriptions · {X.shape[1]:,} candidate keywords "
          f"(n-grams {NGRAM[0]}-{NGRAM[1]}, min df {MINDF}{', + char grams' if CHAR else ''})")
    print(f"  target `{TARGET}` · {y.mean():.1%} positive\n")

    # couples that share a person go in the same fold, so a keyword cannot be learned from one
    # marriage and scored on that person's other marriage
    ids = pd.read_csv(f"{BIO}/marriage_quality_binary.csv", usecols=["pid_a", "pid_b"])
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    gid = pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]

    print(f"     {'C':>8}{'keywords':>10}{'CV AUC':>10}   per-seed")
    print("  " + "-" * 56)
    best = None
    for C in CS:
        accs, nk = [], 0
        for seed in SEEDS:
            fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
            oof = np.zeros(len(y))
            for k in range(5):
                trm, tem = fold != k, fold == k
                m = (LogisticRegression(C=C, penalty="l1", solver="liblinear", max_iter=3000)
                     if L1R >= 1.0 else
                     LogisticRegression(C=C, penalty="elasticnet", l1_ratio=L1R,
                                        solver="saga", max_iter=2000))
                m.fit(X[trm], y[trm])
                oof[tem] = m.decision_function(X[tem])
                nk = max(nk, int((m.coef_ != 0).sum()))
            accs.append(roc_auc_score(y, oof))
        a = float(np.mean(accs))
        print(f"     {C:>8g}{nk:>10,}{a:>10.4f}   {', '.join(f'{v:.4f}' for v in accs)}")
        if best is None or a > best[1]:
            best = (C, a, nk)
    print(f"\n  BEST C={best[0]:g} · {best[2]:,} keywords · CV AUC {best[1]:.4f}")

    m = ((LogisticRegression(C=best[0], penalty="l1", solver="liblinear", max_iter=5000)
          if L1R >= 1.0 else
          LogisticRegression(C=best[0], penalty="elasticnet", l1_ratio=L1R, solver="saga",
                             max_iter=3000)).fit(X, y))
    w = m.coef_.ravel()
    nz = np.where(w != 0)[0]
    order = nz[np.argsort(-np.abs(w[nz]))]
    print(f"\n  the {min(24, len(order))} strongest keywords")
    print(f"     {'weight':>8}  {'fires':>7}  keyword")
    for i in order[:24]:
        print(f"     {w[i]:>+8.3f}  {int(X[:, i].sum()):>7,}  {names[i]}")

    # what a keyword labeller would say about the era, reported whether or not it is flattering
    s = m.decision_function(X)
    mid = (pd.to_numeric(d.dob_a.astype(str).str[:4], errors="coerce")
           + pd.to_numeric(d.dob_b.astype(str).str[:4], errors="coerce")) / 2
    ok = mid.notna().to_numpy()
    r = np.corrcoef(s[ok], mid[ok])[0, 1]
    print(f"\n  correlation of the keyword score with the couple's birth year: {r:+.3f}")

    json.dump({"target": TARGET, "C": best[0], "cv_auc": best[1], "n_keywords": int(best[2]),
               "ngram": list(NGRAM), "min_df": MINDF, "char_grams": CHAR,
               "intercept": float(m.intercept_[0]),
               "keywords": {names[i]: round(float(w[i]), 4) for i in order}},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
