"""comp_label-p1971_corpus.py — LABEL PURIFICATION for the children target (competition lens
"label-p1971"). Writes a COPIED corpus directory; never touches the source.

The standing label (tilldeath_wt3) is "children LINKED in Wikidata for the couple": y=0 blends real
childlessness with thin documentation. Purified rule, per couple (a = him, b = her):

  y=1 (linked children)             kept as 1 — unless a spouse STATES P1971=0 (contradiction: drop)
  y=0, a spouse states P1971 = 0    kept as 0 — explicit childlessness (a zero on either spouse settles
                                    the couple even if the other spouse has children elsewhere)
  y=0, a spouse states P1971 >= 1   the record knows of a child it has no item for: flipped to 1 ONLY
                                    if that spouse is in exactly one couple of the source corpus (so
                                    the child can only be this marriage's); otherwise dropped as
                                    ambiguous (the child may belong to another marriage)
  y=0, no P1971 either side         kept as 0 only if BOTH spouses have >= AQ_MIN_SITELINKS (deep
                                    records — a child would have been linked); dropped as thin

FALLBACK (the lens's own): if ~/.artamatch-dev/p1971.csv does not exist yet, only the depth rule
runs — negatives kept iff deep, positives unchanged. MODE is printed and stored in the report.

P1971, sitelinks and the couple multiplicity are used ONLY to choose rows and labels; nothing
here becomes a feature. Charts are the same rows of phases.npz, subset by mask (make_subset.py).
Also reports a free diagnostic: the standing model's out-of-fold scores (oof_nested_<std>.npy,
fitted on the noisy labels) scored on the kept rows under the OLD and the NEW labels.

env: AQ_SRC (default ~/.artamatch-dev/tilldeath_wt3) · AQ_OUT (default ~/.artamatch-dev/comp_label-p1971)
     AQ_P1971 (default ~/.artamatch-dev/p1971.csv) · AQ_MIN_SITELINKS (default 5) · AQ_FORCE_FALLBACK=1
"""
import json, os
from collections import Counter
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

SRC = os.path.expanduser(os.environ.get("AQ_SRC", "~/.artamatch-dev/tilldeath_wt3"))
OUT = os.path.expanduser(os.environ.get("AQ_OUT", "~/.artamatch-dev/comp_label-p1971"))
P1971 = os.path.expanduser(os.environ.get("AQ_P1971", "~/.artamatch-dev/p1971.csv"))
MIN = int(os.environ.get("AQ_MIN_SITELINKS", "5"))
STD_OOF = os.environ.get("AQ_STD_OOF", "oof_nested_k32_ortho_onlyXY_h1only.npy")
FORCE_FB = os.environ.get("AQ_FORCE_FALLBACK", "0") == "1"

full = pd.read_csv(f"{SRC}/full.csv", dtype=str)
ids = pd.read_csv(f"{SRC}/_train_ids.csv", dtype=str)
assert len(full) == len(ids) and (full.pid_a == ids.pid_a).all()
y0 = full.y.astype(int).to_numpy()
n = len(full)

sl = pd.read_csv(os.path.expanduser("~/.artamatch-dev/sitelinks.csv"), dtype={"pid": str})
sl = dict(zip(sl.pid, pd.to_numeric(sl.sitelinks, errors="coerce").fillna(0)))
deep = np.array([(sl.get(a, 0) >= MIN) and (sl.get(b, 0) >= MIN) for a, b in zip(full.pid_a, full.pid_b)])

mode = "depth-only fallback (p1971.csv absent)"
p_zero, p_pos = {}, {}          # pid -> True if an explicit 0 is stated / max stated count >= 1
if os.path.exists(P1971) and not FORCE_FB:
    pp = pd.read_csv(P1971, dtype=str)
    pp["n"] = pd.to_numeric(pp["n"], errors="coerce")
    pp = pp.dropna(subset=["n"])
    g = pp.groupby("pid")["n"]
    mx, mn = g.max(), g.min()
    # a person with several P1971 values: >=1 anywhere means a child exists; an explicit zero is
    # only trusted when NO value says otherwise
    p_pos = {k: True for k, v in mx.items() if v >= 1}
    p_zero = {k: True for k, v in mx.items() if v == 0}
    mode = f"p1971 ({len(mx):,} people state a count · {len(p_zero):,} explicit zeros)"
print(f"MODE: {mode} · depth = both spouses >= {MIN} sitelinks", flush=True)

mult = Counter(list(full.pid_a) + list(full.pid_b))     # couples per person in the SOURCE corpus
keep = np.zeros(n, bool); y1 = y0.copy(); src = full.src.astype(str).to_numpy().copy()
cnt = Counter()
for i, (a, b) in enumerate(zip(full.pid_a, full.pid_b)):
    za, zb = p_zero.get(a, False), p_zero.get(b, False)
    pa, pb = p_pos.get(a, False), p_pos.get(b, False)
    if y0[i] == 1:
        if za or zb:
            cnt["drop_contradiction(linked child vs stated 0)"] += 1; continue
        keep[i] = True; cnt["pos_linked"] += 1
    elif za or zb:
        keep[i] = True; cnt["neg_explicit_zero"] += 1; src[i] = "p1971=0"
    elif pa or pb:
        single = (pa and mult[a] == 1) or (pb and mult[b] == 1)
        if single:
            keep[i] = True; y1[i] = 1; src[i] = "p1971>=1"; cnt["pos_flipped_p1971"] += 1
        else:
            cnt["drop_ambiguous(p1971>=1, spouse in >1 couple)"] += 1
    elif deep[i]:
        keep[i] = True; cnt["neg_deep"] += 1; src[i] = "childless:deep"
    else:
        cnt["drop_thin_negative"] += 1

os.makedirs(OUT, exist_ok=True)
f2 = full[keep].copy(); f2["y"] = y1[keep]; f2["src"] = src[keep]
f2["outcome"] = np.where(f2.y == 1, "prospered", "failed:childless")
f2.to_csv(f"{OUT}/full.csv", index=False)
ids[keep].to_csv(f"{OUT}/_train_ids.csv", index=False)
f2[["dob_a", "dob_b", "start"]].assign(ended_in_divorce=f2.y.to_numpy()).to_csv(f"{OUT}/train.csv", index=False)
for f in ("test.csv", "solution.csv"):
    if os.path.exists(f"{SRC}/{f}"):
        pd.read_csv(f"{SRC}/{f}", dtype=str).to_csv(f"{OUT}/{f}", index=False)
for nz in ("phases.npz", "systems.npz"):
    if os.path.exists(f"{SRC}/{nz}"):
        Z = np.load(f"{SRC}/{nz}", allow_pickle=True)
        np.savez_compressed(f"{OUT}/{nz}", **{k: (Z[k][keep] if (hasattr(Z[k], "shape") and Z[k].shape[:1] == (n,)) else Z[k]) for k in Z.files})

# free diagnostic: the standing model's OOF (noisy-label fit) on the kept rows, old vs new labels
def within_era(yy, oo, dob):
    yr = pd.to_numeric(pd.Series(dob).astype(str).str.slice(0, 4), errors="coerce").to_numpy()
    dec = yr // 10 * 10; num = den = 0.0
    for d in np.unique(dec[np.isfinite(dec)]):
        r = dec == d
        if r.sum() >= 200 and 0 < yy[r].sum() < r.sum():
            num += roc_auc_score(yy[r], oo[r]) * r.sum(); den += r.sum()
    return num / den if den else float("nan")
diag = {}
if os.path.exists(f"{SRC}/{STD_OOF}"):
    oof = np.load(f"{SRC}/{STD_OOF}")
    diag = {"standing_oof": STD_OOF,
            "full_corpus_auc": round(float(roc_auc_score(y0, oof)), 4),
            "kept_rows_old_labels_auc": round(float(roc_auc_score(y0[keep], oof[keep])), 4),
            "kept_rows_new_labels_auc": round(float(roc_auc_score(y1[keep], oof[keep])), 4),
            "kept_rows_old_labels_within_era": round(within_era(y0[keep], oof[keep], full.dob_a[keep]), 4),
            "kept_rows_new_labels_within_era": round(within_era(y1[keep], oof[keep], full.dob_a[keep]), 4)}
rep = {"mode": mode, "min_sitelinks": MIN, "src": SRC, "out": OUT, "n_source": int(n), "n_kept": int(keep.sum()),
       "positives": int(y1[keep].sum()), "pos_rate": round(float(y1[keep].mean()), 4),
       "counts": dict(cnt), "standing_model_diagnostic": diag}
json.dump(rep, open(f"{OUT}/comp_label-p1971_corpus_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1), flush=True)
print(f"wrote {OUT}: {keep.sum():,} of {n:,} couples · y=1 {y1[keep].mean():.1%}", flush=True)
