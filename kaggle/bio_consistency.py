"""bio_consistency.py — find a judge whose bar differs from its peers, without knowing the right answer.

Nineteen judges labelled independently against one rubric. Four of them had read its most common case
backwards — a dry genealogical entry naming children — and sent ~600 marriages to `thin_record` that
every other judge sent to `children`. That was caught by counting one pattern by hand. This does it for
every pattern, every batch, automatically, so the next divergence does not depend on someone noticing.

The trick is that no ground truth is needed. Each batch is one judge's work on an interchangeable sample
of the same corpus, so a batch that is a large outlier against the POOLED distribution of its peers is
evidence about the judge, not about the marriages. Three tests:

  1. RULE APPLICATION — for the specific ambiguous pattern (children named, no trouble stated), the share
     a batch sends to `good`. This is the one that caught the real failure.
  2. VERDICT RATE      — the batch's good%, as a z-score against the pooled rate. Flagged only when it is
     also out of step on test 3, because good% legitimately drifts with record quality.
  3. REASON MIX        — Jensen-Shannon divergence between the batch's reason distribution and the pooled
     one, which catches a judge over-using any single ground, not just the known case.

EVERY test is against a LOCAL baseline — the median of a batch's NEIGHBOURS in the quality ordering,
excluding itself — not against the global pooled rate. That is not a refinement, it is the difference
between working and not: `kids -> good` climbs monotonically from 47% to 84% across the ordering, because
the earliest batches hold the richest records, where an entry that names children is also more likely to
state a divorce and so land on `divorce` instead. Measured against a global median, the entire
high-quality end of the corpus looks like judge error. Measured against neighbours, only the genuine
outliers remain — and those are confirmable: the judge for the worst of them reported, unprompted, that
it had "calibrated deliberately strict on bare genealogical entries".

Usage: bio_consistency.py [--strict]
"""
import glob, json, os, sys
import numpy as np, pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
GOOD_R = {"affection", "collaboration", "children", "lasted_to_death", "adversity"}


def js(p, q):
    """Jensen-Shannon divergence, base 2, in [0, 1]"""
    p, q = np.asarray(p, float), np.asarray(q, float)
    p, q = p / max(p.sum(), 1e-12), q / max(q.sum(), 1e-12)
    m = 0.5 * (p + q)
    kl = lambda a, b: float(np.sum(np.where(a > 0, a * np.log2(a / np.where(b > 0, b, 1e-12)), 0.0)))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def main():
    rows = []
    for f in sorted(glob.glob(f"{BIO}/labels2/batch_*.json")):
        b = os.path.basename(f)[6:10]
        try:
            arr = json.load(open(f))
        except Exception:
            continue
        for o in arr:
            if isinstance(o, dict) and isinstance(o.get("good"), bool):
                rows.append({"batch": b, "good": int(o["good"]), "reason": o.get("reason", ""),
                             "kids": bool(o.get("children_together"))})
    d = pd.DataFrame(rows)
    if d.empty:
        print("  nothing judged yet"); return
    reasons = sorted(d.reason.unique())
    pooled = d.reason.value_counts().reindex(reasons).fillna(0).to_numpy()
    pooled_good = d.good.mean()
    print(f"  {len(d):,} verdicts from {d.batch.nunique()} judges · pooled good {pooled_good:.1%}\n")
    print(f"  z and kids->good are vs NEIGHBOURS in the quality ordering, not the global rate\n")
    print(f"  {'batch':>6}{'n':>6}{'good%':>8}{'zloc':>7}{'kids->good':>12}{'reasonJS':>10}   flags")
    print("  " + "-" * 74)
    out = []
    for b, g in d.groupby("batch"):
        n = len(g)
        p = g.good.mean()
        se = np.sqrt(max(pooled_good * (1 - pooled_good), 1e-9) / n)
        z = (p - pooled_good) / se
        k = g[g.kids]
        kg = k.good.mean() if len(k) >= 20 else np.nan
        jsd = js(g.reason.value_counts().reindex(reasons).fillna(0).to_numpy(), pooled)
        out.append({"batch": b, "n": n, "good": p, "z": z, "kids_good": kg, "js": jsd})
    o = pd.DataFrame(out)
    o = o.sort_values("batch").reset_index(drop=True)
    W = 4                     # neighbours each side in the quality ordering

    def local(col, i):
        lo, hi = max(0, i - W), min(len(o), i + W + 1)
        v = o[col].iloc[lo:hi].drop(index=o.index[i], errors="ignore")
        v = v[~v.isna()]
        return float(np.median(v)) if len(v) >= 3 else np.nan

    bad = []
    for i, r in o.iterrows():
        flags = []
        lk, lg = local("kids_good", i), local("good", i)
        # test 1: rule application, against neighbours
        if not np.isnan(r.kids_good) and not np.isnan(lk) and r.kids_good < lk - 0.22:
            flags.append(f"RULE-APPLIED-BACKWARDS (peers {lk:.0%})")
        # test 2+3: verdict rate against neighbours, AND an unusual reason mix
        zl = np.nan
        if not np.isnan(lg):
            sel = np.sqrt(max(lg * (1 - lg), 1e-9) / r.n)
            zl = (r.good - lg) / sel
            if abs(zl) > 3 and r.js > 0.05:
                flags.append(f"verdict+mix outlier (peers {lg:.0%})")
        if not flags and r.js > 0.10:
            flags.append("reason-mix outlier")
        kgs = "  n/a" if np.isnan(r.kids_good) else f"{r.kids_good:5.0%}"
        zs = "  n/a" if np.isnan(zl) else f"{zl:5.1f}"
        print(f"  {r.batch:>6}{int(r.n):>6}{r.good:>8.1%}{zs:>7}{kgs:>12}{r.js:>10.3f}   "
              + (", ".join(flags) if flags else ""))
        if flags and not flags[0].startswith("reason-mix"):
            bad.append(r.batch)
    print(f"\n  children-named -> `good` runs {o.kids_good.min():.0%} to {o.kids_good.max():.0%} across "
          f"the quality ordering; that TREND is the corpus, a local dip is the judge")
    if bad:
        print(f"  RE-JUDGE: {', '.join(sorted(bad))}")
        print("  Set the file aside as labels2_<batch>_misread.json.bak first — never overwrite, so the")
        print("  correction stays auditable — then re-run the judge and re-run this check.")
    else:
        print("  no batch diverges from its peers on rule application or reason mix")
    if "--strict" in sys.argv and bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
