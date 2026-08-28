"""bio_corpus.py — turn the judged marriages into modelling corpora.

The new target is the QUALITY of the marriage as the historical record describes it, judged one couple at
a time against RUBRIC.md: happy / neutral / toxic. Three binary corpora come out of it, all sharing the
same charts and the same component split:

  quality_ht     toxic(1) vs happy(0)      — the cleanest contrast, the headline target
  quality_toxic  toxic(1) vs everything(0) — "will this go wrong"
  quality_happy  happy(1) vs everything(0) — "will this flourish"

Only couples whose BOTH dates are full precision enter: a chart needs a day. The label column keeps the
name `ended_in_divorce` so every existing fit script reads it unchanged — in these corpora it means the
target above, and the corpus README says so.

Split: whole connected components of the marriage graph, 85/15, as in the divorce corpora — identity
never straddles the split. Usage: bio_corpus.py [out_root]
"""
import glob, json, os, sys
import numpy as np, pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
ROOT = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev")
MISSING = "0000-00-00"


def load_labels():
    rows = []
    for f in sorted(glob.glob(f"{BIO}/labels/batch_*.json")):
        try:
            arr = json.load(open(f))
        except Exception as e:
            print(f"  ! {os.path.basename(f)} unreadable: {str(e)[:60]}")
            continue
        for o in arr:
            if isinstance(o, dict) and o.get("id") and o.get("label") in ("happy", "neutral", "toxic"):
                rows.append({"rid": o["id"], "label": o["label"],
                             "confidence": o.get("confidence", ""),
                             "children_together": bool(o.get("children_together")),
                             "joint_creative_work": bool(o.get("joint_creative_work")),
                             "joint_business": bool(o.get("joint_business")),
                             "conflict": bool(o.get("conflict")),
                             "infidelity": bool(o.get("infidelity")),
                             "abuse": bool(o.get("abuse")),
                             "evidence": o.get("evidence", "")})
    return pd.DataFrame(rows).drop_duplicates("rid")


def write_corpus(df, y, name):
    """df: couples with pid_a/pid_b/dob_a/dob_b · y: 0/1 target aligned with df"""
    d = df.copy()
    d["y"] = y
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(d.pid_a, d.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    comp = np.array([find(a) for a in d.pid_a])
    rng = np.random.default_rng(42)
    uniq = rng.permutation(np.unique(comp))
    sizes = pd.Series(comp).value_counts()
    cum = np.cumsum([sizes[c] for c in uniq])
    te_comps = set(uniq[cum <= int(len(d) * 0.15)])
    is_te = np.array([c in te_comps for c in comp])
    tr, te = d[~is_te].copy(), d[is_te].copy()
    out = f"{ROOT}/{name}"
    os.makedirs(out, exist_ok=True)
    te.insert(0, "id", [f"r{i:06d}" for i in range(len(te))])
    for f in (tr, te):
        f["start"] = MISSING
    tr.rename(columns={"y": "ended_in_divorce"})[["dob_a", "dob_b", "start", "ended_in_divorce"]].to_csv(
        f"{out}/train.csv", index=False)
    te[["id", "dob_a", "dob_b", "start"]].to_csv(f"{out}/test.csv", index=False)
    te.rename(columns={"y": "ended_in_divorce"})[["id", "ended_in_divorce"]].to_csv(
        f"{out}/solution.csv", index=False)
    tr[["pid_a", "pid_b"]].assign(y_rule=tr.y, y_alive=tr.y).to_csv(f"{out}/_train_ids.csv", index=False)
    te[["id", "pid_a", "pid_b"]].assign(y_rule=te.y, y_alive=te.y).to_csv(f"{out}/_test_ids.csv", index=False)
    open(f"{out}/README.txt", "w").write(
        f"ArtaMatch quality corpus '{name}'.\n"
        f"The column ended_in_divorce carries THIS target, not divorce:\n"
        f"  {name}: 1 = {'toxic' if 'toxic' in name or name.endswith('ht') else 'happy'}, 0 = the contrast class.\n"
        f"Labels: marriage quality judged from the Wikipedia record against RUBRIC.md.\n"
        f"train {len(tr)} ({tr.y.mean():.1%} positive) · test {len(te)} ({te.y.mean():.1%} positive)\n")
    print(f"  {name}: train {len(tr):,} ({tr.y.mean():.1%} pos) · test {len(te):,} ({te.y.mean():.1%} pos)")


def main():
    lab = load_labels()
    idx = pd.read_csv(f"{BIO}/index.csv", dtype=str)
    m = idx.merge(lab, on="rid", how="inner")
    print(f"  {len(lab):,} judged · {len(m):,} matched to couples")
    if not len(m):
        return
    dist = m.label.value_counts()
    print("  label distribution: " + " · ".join(f"{k} {v:,} ({v/len(m):.0%})" for k, v in dist.items()))
    print("  contributions seen: " + " · ".join(
        f"{c} {int(m[c].sum()):,}" for c in ("children_together", "joint_creative_work", "joint_business",
                                             "conflict", "infidelity", "abuse")))
    hi = (m.confidence == "high").mean()
    print(f"  high confidence: {hi:.0%}")
    fp = pd.to_numeric(m.fullprec, errors="coerce").fillna(0) == 1
    m = m[fp].copy()
    print(f"  {len(m):,} of them have both dates to the day (charts need a day)")
    m.to_csv(f"{BIO}/judged.csv", index=False)
    # The judges mark an unreadable or wrong-person description "low" — those must not decide the
    # sharpest target, where every row is meant to be a clear case.
    ht = m[(m.label != "neutral") & (m.confidence != "low")]
    write_corpus(ht, (ht.label == "toxic").astype(int).to_numpy(), "quality_ht")
    write_corpus(m, (m.label == "toxic").astype(int).to_numpy(), "quality_toxic")
    write_corpus(m, (m.label == "happy").astype(int).to_numpy(), "quality_happy")


if __name__ == "__main__":
    main()
