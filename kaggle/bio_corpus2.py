"""bio_corpus2.py — the BINARY judged corpus: did this marriage go well, yes or no.

The three-class pass (happy/neutral/toxic) put 69% of marriages in `neutral`, which taught nothing and
hid systematic disagreement between judges inside the safe middle class. RUBRIC2.md forces a verdict on
every marriage. Two corpora come out, sharing charts and split:

  quality_good      good(1) vs bad(0), every judged couple   — the headline target
  quality_good_narr the same, minus rows whose verdict rests on an ABSENCE (`thin_record`), so both
                    classes are grounded in something the record actually says — the sharp contrast

A high-confidence filter was tried for that second corpus and rejected on measurement: confidence is
not label-neutral here. High-confidence rows are 67% bad, medium 79% good, because a stated divorce is
a fact a judge can point at (`divorce` 91% high-conf, `abuse` 97%) while an affirmative verdict often
rests on quieter ground (`children` 12%, `thin_record` 22%). Filtering on it turns the target into
"did the record state a divorce" — a different, easier question, and one MORE exposed to the
record-verbosity confound, not less.

The label column keeps the name `ended_in_divorce` so every existing fit script reads it unchanged; the
corpus README says what it actually means. Split is by whole connected component of the marriage graph,
85/15, so identity never straddles it.

Integrity filters, each one earned by a real failure in this project:
  · both dates full precision            — a sidereal chart needs a day
  · both partners P31=human              — a judge found Indiana Jones married to Marion Ravenwood
  · judge's own not_a_marriage flag      — a mistress or broken engagement teaches nothing about marriage
  · evidence quote must be in the text   — a judge auditing itself caught a fabricated quote
  · (hi corpus only) confidence == high  — an unreadable or garbled record must not decide the sharp target

Usage: bio_corpus2.py [out_root]
"""
import glob, json, os, sys
import numpy as np, pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
ROOT = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev")
MISSING = "0000-00-00"
NOTMAR = ("never married|not a marriage|no marriage record|was his mistress|was her mistress|"
          "only as a concubine|marriage in name only|never states they married|"
          "marriage is never stated|were not married|broken engagement|betrothal was broken")


def load_labels():
    rows, seen = [], {}
    for f in sorted(glob.glob(f"{BIO}/labels2/batch_*.json")):
        try:
            arr = json.load(open(f))
        except Exception as e:
            print(f"  ! {os.path.basename(f)} unreadable: {str(e)[:60]}")
            continue
        if len(arr) < 200:
            print(f"  · {os.path.basename(f)[6:10]}: {len(arr)}/200 judged (agent stopped early) — "
                  f"keeping the {len(arr)} verdicts it finished")
        for o in arr:
            if not (isinstance(o, dict) and o.get("id") and isinstance(o.get("good"), bool)):
                continue
            if o["id"] in seen:
                continue
            seen[o["id"]] = 1
            rows.append({"rid": o["id"], "good": int(o["good"]),
                         "confidence": o.get("confidence", ""),
                         "reason": o.get("reason", ""),
                         "children_together": bool(o.get("children_together")),
                         "joint_creative_work": bool(o.get("joint_creative_work")),
                         "joint_business": bool(o.get("joint_business")),
                         "not_a_marriage": bool(o.get("not_a_marriage")),
                         "evidence": o.get("evidence", "")})
    return pd.DataFrame(rows)


def write_corpus(df, y, name, meaning):
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
        f"ArtaMatch binary quality corpus '{name}'.\n"
        f"The column ended_in_divorce carries THIS target, NOT divorce:\n"
        f"  1 = {meaning}\n"
        f"Labels: did the marriage go well, judged from the Wikipedia record against RUBRIC2.md.\n"
        f"train {len(tr)} ({tr.y.mean():.1%} positive) · test {len(te)} ({te.y.mean():.1%} positive)\n"
        f"NOTE: the 10,000 couples were selected by a record-quality score that is itself correlated\n"
        f"with the label (trouble r=-0.82 with rank). Any result must be reported against the\n"
        f"birth-decade control in quality_stability.py, not against chance alone.\n")
    print(f"  {name}: train {len(tr):,} ({tr.y.mean():.1%} pos) · test {len(te):,} ({te.y.mean():.1%} pos)")
    # Rewriting train.csv INVALIDATES any phases.npz beside it, and a stale one does not fail loudly:
    # the fit scripts broadcast a 4,799-row feature against 2,737 rows of sky and raise deep inside the
    # bank builder, or worse, line up by accident. Charts are therefore rebuilt here, by the corpus that
    # owns them, so the two can never disagree. AQ_NO_PLACE=1 because a dates-only corpus has no
    # coordinates — without it every natal cast silently returns NaN (see kerykeion_phases.py).
    import subprocess
    np_ = f"{out}/phases.npz"
    if os.path.exists(np_):
        os.remove(np_)
    r = subprocess.run([sys.executable, os.path.expanduser(
        "~/Studio/artamatch/research/sidereal/kerykeion_phases.py")],
        env=dict(os.environ, AQ_NO_PLACE="1", AQ_SRC=out, AQ_OUT=out),
        capture_output=True, text=True)
    if not os.path.exists(np_):
        print("    ! chart build FAILED — the corpus is unusable until it succeeds")
        print("     " + (r.stdout + r.stderr).strip()[-400:])
        return
    Zc = np.load(np_, allow_pickle=True)
    assert Zc["theta_a_train"].shape[0] == len(tr), "charts do not match train.csv"
    ok = int(np.isfinite(Zc["theta_a_train"][:, :10]).all(1).sum())
    print(f"    charts rebuilt: {ok:,}/{len(tr):,} train couples with both natal charts complete")


def main():
    lab = load_labels()
    if not len(lab):
        print("  no binary labels yet")
        return
    idx = pd.read_csv(f"{BIO}/index.csv", dtype=str)
    m = idx.merge(lab, on="rid", how="inner")
    print(f"  {len(lab):,} judged · {len(m):,} matched to couples")
    print(f"  good {int(m.good.sum()):,} ({m.good.mean():.1%}) · bad {int((1-m.good).sum()):,}")
    print(f"  high confidence: {(m.confidence == 'high').mean():.0%}"
          f"  (good-rate by confidence: "
          + " · ".join(f"{c} {m.good[m.confidence == c].mean():.0%}"
                       for c in ("high", "medium", "low") if (m.confidence == c).any()) + ")")
    print("  reasons: " + " · ".join(f"{k} {v}" for k, v in m.reason.value_counts().head(12).items()))

    n0 = len(m)
    m = m[pd.to_numeric(m.fullprec, errors="coerce").fillna(0) == 1].copy()
    print(f"  full precision both dates: {len(m):,} (dropped {n0 - len(m):,})")

    hp = f"{BIO}/humans.csv"
    if os.path.exists(hp):
        h = pd.read_csv(hp, dtype=str)
        nonhuman = set(h.qid[h.is_human == "0"])
        bad = m.pid_a.isin(nonhuman) | m.pid_b.isin(nonhuman)
        if bad.any():
            print(f"  dropped {int(bad.sum())} pair(s) where someone is not a person")
        m = m[~bad].copy()

    flag = m.not_a_marriage | m.evidence.fillna("").str.lower().str.contains(NOTMAR)
    if flag.any():
        print(f"  dropped {int(flag.sum())} pair(s) the judge says were never actually married")
        m = m[~flag].copy()

    # A judge marks a description "low" confidence when it is garbled or plainly about someone else
    # (r003508: the named wife never appears; r003861: two differently-named wives tangled together).
    # Unlike a high-confidence filter, this is small and roughly label-neutral, and every judge applies
    # it without being asked. See bio_namecheck.py for why the mechanical alternative does not work.
    n0 = len(m)
    lowg = m.good[m.confidence == "low"].mean() if (m.confidence == "low").any() else float("nan")
    m = m[m.confidence != "low"].copy()
    print(f"  dropped {n0 - len(m)} low-confidence row(s) — garbled or wrong-person records "
          f"(they were {lowg:.0%} good; corpus is now {m.good.mean():.1%})")

    uq = f"{BIO}/unverified_quotes2.csv"
    if os.path.exists(uq):
        drop = set(pd.read_csv(uq, dtype=str).rid)
        n0 = len(m)
        m = m[~m.rid.isin(drop)].copy()
        if n0 != len(m):
            print(f"  dropped {n0 - len(m)} row(s) whose quoted evidence is not in the description")

    m.to_csv(f"{BIO}/judged2.csv", index=False)
    print(f"  {len(m):,} couples survive every filter · {m.good.mean():.1%} good\n")
    write_corpus(m, m.good.to_numpy(), "quality_good", "the marriage went well (RUBRIC2)")
    narr = m[m.reason != "thin_record"]
    if len(narr) > 400:
        write_corpus(narr, narr.good.to_numpy(), "quality_good_narr",
                     "the marriage went well (RUBRIC2, rows where the record states something either way)")


if __name__ == "__main__":
    main()
