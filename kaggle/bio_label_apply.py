"""bio_label_apply.py — the auto-labeller: a readable table of keywords, and nothing else.

FULLY EXPLAINABLE, AND THAT IS A DESIGN CONSTRAINT, NOT A HOPE. The model is

    score = intercept + sum of w(k) over the keywords k PRESENT in the description

so a keyword contributes the same amount wherever it appears, the contributions add up to the score
exactly, and any single marriage can be explained by printing the words that were found next to the
number each one moved. `--explain` does precisely that and its lines sum to the score it prints.

WHAT THIS COST, MEASURED. The accurate form of this model is tf-idf with L2 normalisation, which
scores 0.8780. It is also not explainable in the sense above: L2 normalisation divides by the length
of the whole document, so `divorced` is worth one thing in a short entry and another in a long one,
and no fixed table can describe it. Binary presence over content words scores 0.8520. The 0.0260 is the
price of being able to show a person why their marriage was labelled as it was: 0.0113 for dropping
the normalisation, and 0.0150 more for refusing function words and the profession and era terms that
name WHO someone was rather than what the marriage was.

PORTABLE BY CONSTRUCTION. The model file is a keyword-to-weight table in JSON — no vectoriser, no
idf, no library version. A stranger with the table and this file gets our labels back. `--verify`
checks the reimplementation here against scikit-learn on all 10,000 judged rows.

SCALE. Descriptions stream in chunks and are never all held at once, so memory is flat and time is
linear. 174,124 couples in couples.csv have two birth dates; 32,502 have a description assembled so
far. The gap is a Wikipedia fetch, not a labelling problem — `--bench` prints the arithmetic.

  --sweep               choose the penalty by grouped cross-validation
  --fit                 fit at the chosen penalty and write the table
  --verify              reimplementation vs scikit-learn, every judged row
  --explain N           show why row N got its score
  --apply IN OUT        stream-score any csv with a `description` column
  --bench N             throughput and memory at N rows
"""
import json, os, re, sys, time, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

BIO = os.path.expanduser("~/.artamatch-dev/bio")
MODEL = os.path.expanduser(os.environ.get("AQ_LABEL_MODEL", "~/.artamatch-dev/label_model.json"))
C = float(os.environ.get("AQ_C", "0.2"))
MINDF = int(os.environ.get("AQ_MINDF", "10"))
CHUNK = int(os.environ.get("AQ_CHUNK", "20000"))
TOK = re.compile(r"(?u)\b\w[\w'-]+\b")


def present(text):
    """the set of unigrams and bigrams in one description, formed as sklearn forms them"""
    w = TOK.findall(text.lower())
    s = set(w)
    s.update(f"{w[i]} {w[i+1]}" for i in range(len(w) - 1))
    return s


def score_one(text, wt, intercept):
    return intercept + sum(wt[k] for k in present(text) if k in wt)


def _data():
    d = pd.read_csv(f"{BIO}/marriage_quality_binary.csv")
    d["desc"] = d.description.fillna("").astype(str)
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(d.pid_a, d.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    gid = pd.factorize(pd.Series([find(a) for a in d.pid_a]))[0]
    return d, d.good.astype(int).to_numpy(), gid


# A keyword that a reader would not accept as evidence about a marriage does not belong in a model
# whose whole purpose is to be readable. Two kinds are refused by name, before any fitting:
#   FUNCTION WORDS  `is`, `to`, `been`, `had` carry real weight because they correlate with sentence
#                   style and article length. "is: +0.23" explains nothing to anybody.
#   WHO THEY WERE   `actor`, `film`, `soviet`, a year — these name the century and the profession,
#                   and the era is exactly the confound this project spends its time removing.
STOP = set("""a an the and or but if then than that this these those of in on at by for with from to
into over under again further once here there all any both each few more most other some such only own
same so too very can will just should now is are was were be been being have has had having do does did
doing i me my we our you your he him his she her it its they them their who whom which what when where
why how as also however although while after before during about against between out up down off no not
nor s t d ll m o re ve y""".split())
BANNED = re.compile(
    r"^(actor|actress|film|films|movie|hollywood|television|singer|band|album|rock|jazz|opera|"
    r"footballer|player|coach|politician|nazi|soviet|ussr|nato|army|war|century|"
    r"born|died|birth|death|aged|age|[0-9]+)$")


def _allowed(t):
    parts = t.split()
    return not any(p in STOP or BANNED.match(p) for p in parts)


def _vec(texts, min_df=None):
    from sklearn.feature_extraction.text import CountVectorizer
    V = CountVectorizer(binary=True, lowercase=True, ngram_range=(1, 2),
                        min_df=min_df or MINDF, token_pattern=r"(?u)\b\w[\w'-]+\b")
    X = V.fit_transform(texts)
    vocab = V.get_feature_names_out()
    keep = np.array([_allowed(t) for t in vocab])
    V._aq_vocab = [t for t, k in zip(vocab, keep) if k]
    return V, X[:, keep]


def sweep():
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    d, y, gid = _data()
    V, X = _vec(d.desc)
    print(f"  {len(d):,} rows · {X.shape[1]:,} candidate keywords\n")
    print(f"     {'C':>7}{'keywords':>10}{'CV AUC':>9}   per-seed")
    for c in (0.05, 0.1, 0.15, 0.2, 0.3, 0.5):
        accs, nk = [], 0
        for s in (7, 23, 101):
            fold = np.random.default_rng(s).integers(0, 5, gid.max() + 1)[gid]
            oof = np.zeros(len(y))
            for k in range(5):
                tr, te = fold != k, fold == k
                m = LogisticRegression(C=c, penalty="l1", solver="liblinear",
                                       max_iter=5000, random_state=0).fit(X[tr], y[tr])
                oof[te] = m.decision_function(X[te]); nk = max(nk, int((m.coef_ != 0).sum()))
            accs.append(roc_auc_score(y, oof))
        print(f"     {c:>7}{nk:>10,}{np.mean(accs):>9.4f}   "
              f"{', '.join(f'{v:.4f}' for v in accs)}")


def fit():
    from sklearn.linear_model import LogisticRegression
    d, y, _ = _data()
    V, X = _vec(d.desc)
    m = LogisticRegression(C=C, penalty="l1", solver="liblinear", max_iter=8000, random_state=0).fit(X, y)
    vocab = V._aq_vocab; w = m.coef_.ravel()
    # NOT rounded. Rounding to five decimals looks tidier and puts a 7.5e-03 error on the score,
    # because 435 keywords each carry their own rounding and the errors add. The table is the model;
    # it stores what the model actually is.
    wt = {vocab[i]: float(w[i]) for i in np.nonzero(w)[0]}
    wt = dict(sorted(wt.items(), key=lambda kv: -abs(kv[1])))
    json.dump({"model": "binary keyword presence, L1 logistic", "C": C, "min_df": MINDF,
               "ngram": [1, 2], "intercept": float(m.intercept_[0]),
               "n_keywords": len(wt), "weights": wt},
              open(MODEL, "w"), ensure_ascii=False, indent=1)
    print(f"  {len(wt):,} keywords · intercept {m.intercept_[0]:+.4f}")
    print(f"  wrote {MODEL} ({os.path.getsize(MODEL)/1e3:.0f} KB)")
    pos = [k for k, v in wt.items() if v > 0][:10]
    neg = [k for k, v in wt.items() if v < 0][:10]
    print(f"  strongest for a good marriage: {', '.join(pos)}")
    print(f"  strongest against:             {', '.join(neg)}")


def verify():
    """Does present() + a dict lookup reproduce the sparse matrix product, exactly?

    An earlier version of this REFITTED the model here and compared the new coefficients against the
    saved table. liblinear does not return bit-identical coefficients across runs, so that check was
    measuring solver determinism and failing for a reason that had nothing to do with the thing being
    verified. The saved weights are now placed back on the vectoriser's own vocabulary and multiplied
    through sklearn's matrix, which isolates the reimplementation and nothing else."""
    from sklearn.metrics import roc_auc_score
    M = json.load(open(MODEL)); wt, b = M["weights"], M["intercept"]
    d, y, _ = _data()
    V, X = _vec(d.desc)
    vocab = list(V._aq_vocab)
    pos = {t: i for i, t in enumerate(vocab)}
    w = np.zeros(len(vocab))
    missing = 0
    for k, v in wt.items():
        if k in pos:
            w[pos[k]] = v
        else:
            missing += 1
    if missing:
        print(f"  !! {missing} saved keywords are absent from the vocabulary")
    ref = X @ w + b
    t0 = time.time()
    got = np.array([score_one(t, wt, b) for t in d.desc])
    dt = time.time() - t0
    diff = np.abs(ref - got)
    print(f"  {len(d):,} rows scored both ways · portable path {len(d)/dt:,.0f} rows/s")
    print(f"  max |sklearn - table| = {diff.max():.3e}   mean {diff.mean():.3e}")
    print(f"  AUC sklearn {roc_auc_score(y, ref):.6f} · table {roc_auc_score(y, got):.6f}"
          f"   (IN-SAMPLE — this checks arithmetic, not accuracy; the honest figure is the one"
          f" from --sweep)")
    print("  " + ("AGREES" if diff.max() < 1e-6 else "!! DISAGREES — the table is wrong"))


def explain(i):
    M = json.load(open(MODEL)); wt, b = M["weights"], M["intercept"]
    d, y, _ = _data()
    r = d.iloc[i]
    hits = sorted(((k, wt[k]) for k in present(r.desc) if k in wt),
                  key=lambda kv: -abs(kv[1]))
    tot = b + sum(v for _, v in hits)
    print(f"  {r.name_a} & {r.name_b}   (judged: {'good' if r.good else 'bad'})")
    print(f"  {r.desc[:220].strip()}...\n")
    print(f"  {'keyword':<28}{'contributes':>12}")
    print("  " + "-" * 40)
    print(f"  {'(intercept)':<28}{b:>+12.3f}")
    for k, v in hits[:20]:
        print(f"  {k:<28}{v:>+12.3f}")
    if len(hits) > 20:
        print(f"  {f'... and {len(hits)-20} more':<28}{sum(v for _,v in hits[20:]):>+12.3f}")
    print("  " + "-" * 40)
    print(f"  {'score':<28}{tot:>+12.3f}   -> {'good' if tot > 0 else 'bad'}")


def apply_to(src, dst):
    M = json.load(open(MODEL)); wt, b = M["weights"], M["intercept"]
    n, t0, first = 0, time.time(), True
    for chunk in pd.read_csv(src, dtype=str, chunksize=CHUNK):
        col = "description" if "description" in chunk.columns else "desc"
        s = np.array([score_one(str(t), wt, b) for t in chunk[col].fillna("")])
        chunk.drop(columns=[col]).assign(label_score=s).to_csv(
            dst, mode="w" if first else "a", header=first, index=False)
        first = False; n += len(chunk)
        print(f"    {n:,} rows · {n/(time.time()-t0):,.0f}/s", flush=True)
    print(f"  scored {n:,} rows in {time.time()-t0:.0f}s -> {dst}")


def bench(N):
    M = json.load(open(MODEL)); wt, b = M["weights"], M["intercept"]
    d = pd.read_csv(f"{BIO}/marriages.csv", dtype=str, usecols=["description"]).description
    pool = (d.fillna("").astype(str).tolist() * (N // 32000 + 2))[:N]
    t0 = time.time()
    for t in pool:
        score_one(t, wt, b)
    dt = time.time() - t0
    import resource
    mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1e6 if sys.platform == "darwin" else 1e3)
    rate = N / dt
    print(f"  {N:,} descriptions in {dt:.1f}s = {rate:,.0f} rows/s · peak RSS {mb:,.0f} MB")
    for t in (174_124, 300_000, 1_000_000):
        print(f"    {t:,} rows -> {t/rate/60:.1f} min on one core")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--sweep" in a: sweep()
    if "--fit" in a: fit()
    if "--verify" in a: verify()
    if "--explain" in a: explain(int(a[a.index("--explain") + 1]))
    if "--apply" in a: apply_to(a[a.index("--apply") + 1], a[a.index("--apply") + 2])
    if "--bench" in a: bench(int(a[a.index("--bench") + 1]))
