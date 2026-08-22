"""
world_control_iv.py — the control that decides whether any world system found anything.

Every one of these systems is keyed on the birth YEAR or a cycle of it, and a cycle of the year is a cycle of the
AGE. The Chinese zodiac branch IS year mod 12, so the branch distance between two people IS their age gap mod 12;
Nine Star Ki is year mod 9, the kua is year mod 9, the sexagenary pillar is a 60-cycle. A tree given any of these
can reconstruct the age gap and will score well without knowing anything about the tradition.

So the number that matters is a MATCHED AUC: concordance pooled WITHIN cells that hold the confounder flat.

Two cells, because the first one is not enough. Age cells — (age_a, age_b) rounded to three years — hold both
ages and therefore the gap. But they do NOT hold the ERA: within one age cell the wedding year still ranges over
a century, and the era is itself strongly predictive, so any system that encodes the wedding date scores on the
era alone. That is not a hypothetical: the start year by itself scores 0.5307 age-matched, and the best members
land at 0.5305–0.5315 — the era's value exactly, and no more.

So the decisive cell is AGE + ERA: (age_a, age_b, wedding decade). A system that clears chance THERE has found
something neither the two ages nor the era already says. Nothing else counts, and each reference below is printed
under the same two cells so every member can be read against the thing it might merely be re-encoding.
"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from artamodel import auc   # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq9c")
PH = os.environ.get("AQ_PHASES", "/tmp/aq9feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq9sub")
# the configuration below was CHOSEN, not assumed: it is the tightest cell at which all four references —
# the age gap, each partner's age, and the wedding year — sit at 0.5000 while enough comparable pairs survive
# to resolve a 0.005 effect. Looser era cells leak the era; tighter ones starve the sparse members.
CELL = float(os.environ.get("AQ_CELL", "1")); ERA = float(os.environ.get("AQ_ERA", "5"))
FULL = os.environ.get("AQ_FULLDATED", "") == "1"   # restrict to couples whose three dates are ALL complete


def matched_auc(y, s, *cells, min_cell=12):
    """AUC pooled within cells: Σ (concordant pairs) / Σ (comparable pairs), both counted inside a cell only.

    Vectorised as a within-cell rank sum — AUC = (Σ ranks of the positives − npos(npos+1)/2) / (npos·nneg) — with
    tied scores sharing an averaged rank, so a member that is constant inside a cell scores exactly 0.5 there
    rather than whatever the sort order happened to be.
    """
    ok = np.isfinite(s)
    for c in cells:
        ok = ok & np.isfinite(c)
    if ok.sum() < min_cell:
        return float("nan"), 0
    key = np.zeros(int(ok.sum()), dtype=np.int64)
    for c in cells:
        key = key * 100000 + c[ok].astype(np.int64)
    _, key = np.unique(key, return_inverse=True)
    yy = y[ok].astype(np.float64); ss = s[ok].astype(np.float64)
    order = np.lexsort((ss, key)); key, ss, yy = key[order], ss[order], yy[order]
    ncell = int(key[-1]) + 1
    counts = np.bincount(key, minlength=ncell)
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    rank = (np.arange(len(key)) - starts[key] + 1).astype(np.float64)
    newgrp = np.ones(len(key), bool); newgrp[1:] = (key[1:] != key[:-1]) | (ss[1:] != ss[:-1])
    gid = np.cumsum(newgrp) - 1
    rank = (np.bincount(gid, weights=rank) / np.bincount(gid))[gid]
    npos = np.bincount(key, weights=yy, minlength=ncell); nneg = counts - npos
    rsum = np.bincount(key, weights=rank * yy, minlength=ncell)
    valid = (npos > 0) & (nneg > 0) & (counts >= min_cell)
    if not valid.any():
        return float("nan"), 0
    aucs = (rsum - npos * (npos + 1) / 2) / np.maximum(npos * nneg, 1)
    w = (npos * nneg)[valid]
    return float((aucs[valid] * w).sum() / w.sum()), int(w.sum())


def main():
    Z = np.load(PH, allow_pickle=True); y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1)
    cut0 = np.quantile(later, 0.40); pn = list(Z["plain_names"]); s1, s2 = list(Z["slots"]); P = Z["plain_train"]
    aa = P[:, pn.index(f"age_{s1}_at_start")]; ab = P[:, pn.index(f"age_{s2}_at_start")]
    ca = np.floor(np.fmax(aa, ab) / CELL); cb = np.floor(np.fmin(aa, ab) / CELL)
    yrs = P[:, pn.index("start_year")]; ce = np.floor(yrs / ERA)
    gap = np.abs(aa - ab)
    print(f"age cells of {CELL:.0f} year(s) on BOTH partners, era cells of {ERA:.0f} year(s) on the wedding date\n")
    print(f"{'REFERENCE':<52} {'raw':>7} {'age':>8} {'+era+prec':>10}")
    # the two things a "tradition" is most likely to be re-encoding once age and era are pinned: WHERE IN THE YEAR
    # the wedding fell, and HOW PRECISELY the three dates are known (a fully dated couple is a better-documented
    # couple, and documentation correlates with everything)
    import pandas as _pd
    _tr = _pd.read_csv(f"{SRC}/train.csv", dtype=str)
    _doy = lambda c: _pd.to_datetime(_tr[c], errors="coerce", format="%Y-%m-%d").dt.dayofyear.astype("float64").to_numpy().copy()
    _full = lambda c: _tr[c].fillna("").str.match(r"^\d{4}-(?!00)\d{2}-(?!00)\d{2}$").to_numpy().astype(float)
    # precision must be held as the exact PATTERN of which dates are complete, not merely how many: holding the
    # COUNT flat still let Korean Gunghap read the difference between (a full, b partial) and (a partial, b full),
    # and that alone was half of its apparent 0.5225 — it falls to 0.5100 once the pattern is pinned.
    prec = _full("dob_a") * 4 + _full("dob_b") * 2 + _full("start")
    refs = (("the age gap alone", -gap), ("the older partner's age alone", -np.fmax(aa, ab)),
            ("the younger partner's age alone", -np.fmin(aa, ab)), ("the start year alone", yrs),
            ("WHERE IN THE YEAR the wedding fell", _doy("start")),
            ("HOW PRECISELY the three dates are known", prec),
            ("the birth day-of-year, partner a", _doy("dob_a")),
            # the yardstick that matters most for reading the table below: a pure bookkeeping artefact with no
            # astrological content whatsoever. Any "tradition" scoring at or under this has found nothing.
            ("WHICH DAY OF THE MONTH the wedding was recorded on",
             _pd.to_numeric(_tr["start"].str[8:10], errors="coerce").to_numpy(dtype=float)))
    keep = (prec == 3) if FULL else np.ones(len(y), bool)
    if FULL:
        print(f"RESTRICTED to the {int(keep.sum()):,} couples whose three dates are ALL complete, so date precision\n"
              f"is CONSTANT and cannot be what any system is reading.\n")
    for nm, sc in refs:
        f = np.isfinite(sc) & (later > cut0) & keep
        m, _ = matched_auc(y[f], sc[f], ca[f], cb[f]); m2, _ = matched_auc(y[f], sc[f], ca[f], cb[f], ce[f], prec[f])
        print(f"  {nm:<50} {auc(y[f], sc[f]):.4f} {m:8.4f} {m2:9.4f}")
    rows = []; seen = set()
    for path in sorted(glob.glob(f"{OUT}/*_members.npz")):
        fam = os.path.basename(path).replace("_members.npz", "")
        Zm = np.load(path, allow_pickle=True)
        if "S_train" not in Zm:
            continue
        S = Zm["S_train"]; nms = [str(v) for v in Zm["names"]]
        for j, nm in enumerate(nms):
            s = S[:, j]; f = np.isfinite(s) & (later > cut0) & keep
            if f.sum() < 500:
                continue
            raw = auc(y[f], s[f]); m, _ = matched_auc(y[f], s[f], ca[f], cb[f])
            m2, pairs = matched_auc(y[f], s[f], ca[f], cb[f], ce[f], prec[f])
            # the standard error of a pooled AUC is ~ 1/(2*sqrt(effective pairs)); print it so a 0.52 on a thin
            # member is not read as the same claim as a 0.52 on a thick one
            se = 0.5 / np.sqrt(pairs) if pairs else float("nan")
            if nm in seen:
                continue
            seen.add(nm)
            rows.append({"family": fam, "member": nm, "raw": raw, "age_matched": m, "age_era_matched": m2,
                         "n": int(f.sum()), "pairs": int(pairs), "se": se})
    g = lambda r: r["age_era_matched"] if r["age_era_matched"] == r["age_era_matched"] else 0
    rows.sort(key=lambda r: -g(r))
    print(f"\n{'MEMBER':<52} {'raw':>7} {'age':>8} {'+era+prec':>10} {'±se':>7} {'pairs':>11}")
    print("-" * 100)
    for r in rows:
        z = (g(r) - 0.5) / r["se"] if r["se"] == r["se"] and r["se"] > 0 else 0
        star = "  ← 3σ" if z > 3 else ""
        print(f"  {r['member'][:50]:<50} {r['raw']:.4f} {r['age_matched']:8.4f} {r['age_era_matched']:9.4f} "
              f"{r['se']:7.4f} {r['pairs']:11,}{star}")
    json.dump(rows, open(f"{OUT}/world_control.json", "w"), indent=1)
    live = [r for r in rows if r["se"] == r["se"] and r["se"] > 0 and (g(r) - 0.5) / r["se"] > 3]
    print(f"\n{len(live)} of {len(rows)} members are more than 3 standard errors above chance once the two ages,\n"
          f"the era AND the date precision are all held flat.")
    if not live:
        print("None of them. Every point of AUC any of these systems shows is the two ages, the era, or how fully\n"
              "the dates happen to be recorded — read back through a cycle of the birth year or the wedding date.\n"
              "Not one of them is a claim about the tradition.")


if __name__ == "__main__":
    main()
