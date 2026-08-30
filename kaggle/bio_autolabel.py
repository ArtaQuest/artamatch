"""bio_autolabel.py — run the keyword labeller over every description we have.

The keyword set from bio_keywords.py reproduces the 10,000 human-checked judgements at CV AUC 0.877.
This applies it to the whole assembled corpus, which costs nothing and drifts not at all, and — the
part that matters — keeps only the marriages the keywords are CONFIDENT about.

A score near the decision boundary is a marriage the text does not settle. Labelling it anyway is
exactly the mistake RUBRIC2 made when it sent thin records to `bad`. So the score is thresholded at
both ends and the middle is dropped, which is the same margin idea as RUBRIC3 expressed in a
continuous score instead of two integers.

The model is fitted on the 10,000 judged rows and applied to the rest; the judged rows keep their own
human-checked label, so nothing is overwritten by its own prediction.

-> ~/.artamatch-dev/bio/autolabel.csv
"""
import json, os, sys, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

BIO = os.path.expanduser("~/.artamatch-dev/bio")
C = float(os.environ.get("AQ_C", "1.5"))
KEEP = float(os.environ.get("AQ_KEEP", "0.60"))    # keep this share, split between the two tails


def main():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    judged = pd.read_csv(f"{BIO}/marriage_quality_binary.csv")
    judged["desc"] = judged.description.fillna("").astype(str)
    allm = pd.read_csv(f"{BIO}/marriages.csv", dtype=str)
    allm["desc"] = allm.description.fillna("").astype(str)
    allm["ya"] = pd.to_numeric(allm.dob_a.astype(str).str[:4], errors="coerce")
    allm["yb"] = pd.to_numeric(allm.dob_b.astype(str).str[:4], errors="coerce")
    allm["mid"] = (allm.ya + allm.yb) / 2
    weak = pd.to_numeric(allm.get("weak_name", 0), errors="coerce").fillna(0)
    allm = allm[(weak == 0) & allm.name_a.notna() & allm.name_b.notna() & allm.mid.notna()]
    allm = allm[allm.desc.str.len() >= 100].reset_index(drop=True)

    V = TfidfVectorizer(sublinear_tf=True, lowercase=True, ngram_range=(1, 2), min_df=10,
                        token_pattern=r"(?u)\b\w[\w'-]+\b")
    V.fit(pd.concat([judged.desc, allm.desc]))
    Xj, Xa = V.transform(judged.desc), V.transform(allm.desc)
    y = judged.good.astype(int).to_numpy()
    m = LogisticRegression(C=C, penalty="l1", solver="liblinear", max_iter=5000).fit(Xj, y)
    nk = int((m.coef_ != 0).sum())
    print(f"  {nk:,} keywords fitted on {len(judged):,} judged marriages")

    s = m.decision_function(Xa)
    lo, hi = np.quantile(s, [KEEP / 2, 1 - KEEP / 2])
    lab = np.where(s <= lo, 0, np.where(s >= hi, 1, -1))
    out = allm.assign(score=s, label=lab, human=0)

    # A row that a person already judged keeps that judgement. The keyword model was FITTED on those
    # rows, so its prediction for them is in-sample and worth nothing; using it would also quietly
    # replace 10,000 checked labels with a model's opinion of them.
    key = lambda f: f.pid_a.astype(str) + "|" + f.pid_b.astype(str)
    truth = dict(zip(key(judged), judged.good.astype(int)))
    k = key(out)
    seen = k.map(truth)
    out.loc[seen.notna(), "label"] = seen[seen.notna()].astype(int).values
    out.loc[seen.notna(), "human"] = 1
    used = out[out.label >= 0].copy()
    print(f"  scored {len(out):,} · kept {len(used):,} "
          f"({int(used.human.sum()):,} human-judged + {int((1-used.human).sum()):,} keyword-labelled)"
          f" · {used.label.mean():.1%} happy")

    # is the confident set still a clock? weight it decade x class and see
    used["dec"] = (used.mid // 10 * 10).astype(int)
    n = used.groupby(["dec", "label"]).size().rename("n").reset_index()
    used = used.merge(n, on=["dec", "label"], how="left")
    used["weight"] = 1.0 / used.n
    used["weight"] *= len(used) / used.weight.sum()

    X = np.column_stack([used.mid, used.mid ** 2])
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    yy = used.label.to_numpy(); f = np.arange(len(used)) % 5
    for tag, wgt in (("unweighted", None), ("decade-weighted", used.weight.to_numpy())):
        oof = np.zeros(len(used))
        for k in range(5):
            tr = f != k
            lr = LogisticRegression(max_iter=1000)
            lr.fit(X[tr], yy[tr], sample_weight=None if wgt is None else wgt[tr])
            oof[~tr] = lr.predict_proba(X[~tr])[:, 1]
        print(f"  era AUC, birth years alone, {tag:<16}"
              f"{roc_auc_score(yy, oof, sample_weight=wgt):.4f}")

    used[["pid_a", "pid_b", "dob_a", "dob_b", "name_a", "name_b",
          "score", "label", "weight", "human"]].to_csv(f"{BIO}/autolabel.csv", index=False)
    print(f"  wrote {BIO}/autolabel.csv")

    if os.environ.get("AQ_WRITE_CORPUS") == "1":
        import bio_corpus2 as B2
        d = used.rename(columns={"label": "_y"})
        B2.write_corpus(d[["pid_a", "pid_b", "dob_a", "dob_b"]].copy(), d._y.to_numpy(),
                        os.environ.get("AQ_CORPUS_NAME", "quality_auto"),
                        "the marriage went well (human judgement where we have one, "
                        "keyword labeller elsewhere)")


if __name__ == "__main__":
    main()
