"""bio_derive3.py — turn RUBRIC3's two scores into the training target, and weight away the era.

Two jobs, both pure functions of the label files. Judges nothing.

1. THE LABEL. margin = w - t; happy at >= +2, unhappy at <= -2, everything else unused. The judge
   never saw this rule, which is the point: it cannot be gamed toward a balance.

2. THE ERA. Matching each negative to a positive from the same birth decade removes the confound
   (era AUC 0.5792 -> 0.5030 on the previous corpus) but discards whichever class is smaller in each
   decade — and this pool is heavily skewed to 1880-1940, so matching would throw away most of the
   modern rows. Inverse-propensity WEIGHTING reaches the same place without discarding anything:
   give every row weight 1 / n(its decade, its class), so each decade contributes equal mass and,
   inside each decade, the two classes contribute equal mass. Class then carries no information about
   decade, which is exactly what matching buys, at no cost in data.

   Every downstream fit must pass these weights through. A weighted AUC is the honest figure; the
   unweighted one is the old confounded number under a new name.

3. THE HELD-OUT 485. People appearing in both a happy and an unhappy marriage are the only clean test
   of the product's actual claim — same person, same era, different partner. They are marked here and
   must be excluded from every fit.

-> ~/.artamatch-dev/bio/target3.csv  with columns rid, pid_a, pid_b, dob_a, dob_b, label, weight, holdout
"""
import glob, json, os, sys
import numpy as np
import pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
GROUNDS = {"aff", "collab", "kids", "endured", "divorce", "harm", "none"}


def read_labels():
    rows, bad = [], 0
    for f in sorted(glob.glob(f"{BIO}/labels3/batch_*.jsonl")):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
                rows.append({"rid": o["i"], "w": int(o["w"]), "t": int(o["t"]),
                             "ground": o.get("g", ""), "quote": o.get("q", ""),
                             "not_a_marriage": int(o.get("nm", 0)),
                             "children": int(o.get("ch", 0)),
                             "creative": int(o.get("cw", 0)), "business": int(o.get("cb", 0)),
                             "batch": os.path.basename(f)})
            except Exception:
                bad += 1
    if bad:
        print(f"  {bad} unparseable lines skipped")
    return pd.DataFrame(rows)


def main():
    lab = read_labels()
    if lab.empty:
        print("  no label files yet — nothing to derive"); sys.exit(0)
    pool = pd.read_csv(f"{BIO}/pool3.csv")
    d = pool.merge(lab, on="rid", how="inner")
    print(f"  {len(lab):,} judgements · {len(d):,} matched to the pool")

    bad = ~d.ground.isin(GROUNDS) | ~d.w.between(0, 3) | ~d.t.between(0, 3)
    if bad.any():
        print(f"  {int(bad.sum())} rows fail the schema and are dropped")
        d = d[~bad]
    d = d[d.not_a_marriage == 0]

    d["margin"] = d.w - d.t
    d["label"] = np.where(d.margin >= 2, 1, np.where(d.margin <= -2, 0, -1))
    used = d[d.label >= 0].copy()
    print(f"  {len(used):,} usable ({len(used)/max(len(d),1):.1%} of judgements) · "
          f"{used.label.mean():.1%} happy")

    used["dec"] = (used.mid // 10 * 10).astype(int)
    n = used.groupby(["dec", "label"]).size().rename("n").reset_index()
    used = used.merge(n, on=["dec", "label"], how="left")
    used["weight"] = 1.0 / used.n
    used["weight"] *= len(used) / used.weight.sum()          # mean weight 1, for readable losses

    long = pd.concat([used[["pid_a", "label"]].rename(columns={"pid_a": "pid"}),
                      used[["pid_b", "label"]].rename(columns={"pid_b": "pid"})])
    c = long.groupby("pid").label.agg(["size", "sum"])
    disc = set(c[(c["sum"] > 0) & (c["sum"] < c["size"])].index)
    used["holdout"] = (used.pid_a.isin(disc) | used.pid_b.isin(disc)).astype(int)
    print(f"  {len(disc):,} people appear on both sides -> {int(used.holdout.sum()):,} rows held out")

    out = used[["rid", "pid_a", "pid_b", "dob_a", "dob_b", "w", "t", "ground", "quote",
                "children", "creative", "business", "label", "weight", "holdout"]]
    out.to_csv(f"{BIO}/target3.csv", index=False)
    print(f"  wrote {BIO}/target3.csv")

    # the check that decides whether any of this worked
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    tr = used[used.holdout == 0]
    X = np.column_stack([tr.mid, tr.mid ** 2]); X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    y = tr.label.to_numpy(); f = np.arange(len(tr)) % 5
    oof = np.zeros(len(tr))
    for k in range(5):
        m_ = f != k
        oof[~m_] = LogisticRegression(max_iter=1000).fit(
            X[m_], y[m_], sample_weight=tr.weight.to_numpy()[m_]).predict_proba(X[~m_])[:, 1]
    print(f"\n  ERA CHECK — birth years alone, weighted: AUC "
          f"{roc_auc_score(y, oof, sample_weight=tr.weight):.4f}  (0.50 is the target; "
          f"the old corpus was 0.5792)")


if __name__ == "__main__":
    main()
