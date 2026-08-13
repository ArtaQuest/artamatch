"""
eval_grid.py — score the trained stack on the 15-cell grid and report the mean of the 15 AUCs.

WHY THIS IS CHUNKED AND WHY THAT NEEDED PROVING. The grid is 17,067 couples duplicated across 15 cells =
256,005 rows, and the feature matrix is 265 blocks totalling ~56,600 columns. Materialising that at once is
about 58 GB, so the rows are processed in chunks and the probabilities concatenated.

Chunking is only safe because no feature depends on the other rows in its batch. That was not true earlier in
this project: nine modules pruned columns by their variance ACROSS the batch, and four features (a harmonics
median, a Spica grid, a Uranian standard deviation, coverage gates) were computed over the row axis — each of
which makes a couple's features depend on who else happened to be in the same chunk, so a model trained on one
batching and scored on another is not the same model. Those are gone, and `--check` re-proves it here rather
than trusting that: the first rows are scored as one chunk and again as three, and the two must agree to the
bit. If that assertion ever fails, every number this file prints is meaningless.

WHAT IT WRITES
    grid_submission.csv   id,parents_together for all 256,005 rows — the competition submission
    grid_result.json      the 15 per-cell AUCs, their mean, and the same 15 cells for the signed-gap reference

Usage:
    AQ_MODEL=/tmp/aqfull2 AQ_GRID=/tmp/aqgrid ~/.artamatch-venv/bin/python eval_grid.py [--check]
"""
import csv
import gc
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASTRO = os.path.join(ROOT, "astro")
WEB = os.path.join(ROOT, "web")

sys.path.insert(0, HERE)
import dates as D          # noqa: E402

MODEL = os.environ.get("AQ_MODEL", "/tmp/aqfull2")
GRID = os.environ.get("AQ_GRID", "/tmp/aqgrid")
CHUNK = int(os.environ.get("AQ_CHUNK") or 8000)
CAND = "/tmp/aq_eval_grid_couples.json"
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def main():
    sys.path.insert(0, ASTRO)
    sys.path.insert(0, WEB)
    os.environ.update({"AQ_COUPLES": CAND, "AQ_NO_PLACE": "1", "AQ_KEEP_ALL_COLS": "1",
                       "AQ_NO_EPHEM_CACHE": "1", "AQ_EPHEM_CACHE": "/nonexistent.npz"})
    for k in ("AQ_SUBSAMPLE", "AQ_BALANCE", "AQ_ROW_INDEX", "AQ_ONLY_KEYS", "AQ_DUMP_ROWS", "AQ_LIMIT"):
        os.environ.pop(k, None)

    import sweshim
    sweshim.load(os.path.join(WEB, "ephem4.bin"), os.path.join(WEB, "tables.json"))
    sys.modules["swisseph"] = sweshim
    import core
    import predictor

    MODULES = [m[5:-3] for m in sorted(os.listdir(ASTRO))
               if m.startswith("trad_") and m.endswith(".py")
               and m[5:-3] not in ("electional", "muhurta", "wedding_transits")]

    stack = predictor.load(open(os.path.join(MODEL, "model.json")).read(),
                           open(os.path.join(MODEL, "model.npz"), "rb").read())

    rows = list(csv.DictReader(open(os.path.join(GRID, "test.csv"))))
    # A smoke-test cap. It exists so the code path can be exercised in a minute instead of thirteen, and it
    # prints a refusal banner because a partial grid cannot produce the metric — every cell must be complete.
    cap = int(os.environ.get("AQ_MAX_ROWS") or 0)
    if cap:
        rows = rows[:cap]
        log(f"AQ_MAX_ROWS={cap}: SMOKE TEST — the printed AUCs are NOT the metric")
    log(f"  {len(rows):,} grid rows · {len(MODULES)} tradition modules · chunk {CHUNK:,}")

    def couples(chunk):
        # Precision derived from the date, exactly as the trainer does it. If these two ever disagree the model
        # is scored on a different representation than it was fitted on.
        return [D.couple_record(i, r["dob_man"], r["dob_woman"]) for i, r in enumerate(chunk)]

    def features(chunk):
        json.dump(couples(chunk), open(CAND, "w"))
        E = core.load()
        if E.n != len(chunk):
            raise SystemExit(f"core kept {E.n} of {len(chunk)} rows — predictions could not be aligned")
        blocks = {}
        for slug in MODULES:
            for k, v in (__import__(f"trad_{slug}").build(E) or {}).items():
                if v is not None:
                    blocks[f"{slug}::{k}"] = np.asarray(v, dtype=np.float32)
        return blocks

    def predict(chunk):
        blocks = features(chunk)
        p, _ = stack.proba(blocks)
        del blocks
        gc.collect()
        return np.asarray(p, dtype=np.float64)

    if "--check" in sys.argv:
        # The whole file rests on a row's features not depending on who shares its chunk, so that is what is
        # asserted — EXACTLY, on the feature matrices themselves. The final probability is checked only to
        # float64 rounding: it comes out of dot products whose summation order legitimately changes with array
        # length, so demanding bit-equality there would fail on BLAS blocking rather than on a real defect.
        # The two bars are far apart — an across-row dependency moves a probability by ~1e-2, not ~1e-16 — so
        # the loose bar on the probability still catches everything the strict bar was meant to catch.
        probe = rows[:900]
        b1 = features(probe)
        b3 = {}
        for i in range(0, 900, 300):
            for k, v in features(probe[i:i + 300]).items():
                b3[k] = v if k not in b3 else np.vstack([b3[k], v])
        if set(b1) != set(b3):
            raise SystemExit(f"chunking changed WHICH blocks exist: {sorted(set(b1) ^ set(b3))[:6]}")
        bad = [k for k in b1 if b1[k].shape != b3[k].shape or not np.array_equal(b1[k], b3[k],
                                                                                equal_nan=True)]
        log(f"  FEATURE EQUIVALENCE: {len(b1)} blocks, {sum(v.shape[1] for v in b1.values()):,} columns, "
            f"{len(bad)} differ between 1x900 and 3x300")
        if bad:
            raise SystemExit(f"these blocks depend on their batch: {bad[:8]} — a model trained on one "
                             "batching is not the model being scored, so no number here would mean anything")
        p1, _ = stack.proba(b1)
        p3, _ = stack.proba(b3)
        d = float(np.abs(np.asarray(p1, dtype=np.float64) - np.asarray(p3, dtype=np.float64)).max())
        del b1, b3
        gc.collect()
        log(f"  probability agrees to {d:.3e} (float64 rounding; a batch dependency would show ~1e-2)")
        if d > 1e-12:
            raise SystemExit("the probabilities differ by more than rounding — something still reads the batch")
        log("  chunking is safe: features bit-identical, probability within rounding")

    out = np.empty(len(rows), dtype=np.float64)
    for s in range(0, len(rows), CHUNK):
        e = min(s + CHUNK, len(rows))
        out[s:e] = predict(rows[s:e])
        log(f"  {e:>7,}/{len(rows):,}  ({100*e/len(rows):5.1f}%)")

    sub = os.path.join(MODEL, "grid_submission.csv")
    with open(sub, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "parents_together"])
        for r, p in zip(rows, out):
            w.writerow([r["id"], f"{p:.6f}"])
    log(f"  wrote {sub} (mean {out.mean():.4f})")

    # Score it with the competition's own scorer, so the number reported here and the number the leaderboard
    # would show come from the same code rather than from two implementations that agree by luck.
    import pandas as pd

    sys.path.insert(0, HERE)
    import competition_metric as cm

    sol = pd.read_csv(os.path.join(GRID, "solution.csv"))
    subd = pd.read_csv(sub)
    if cap:
        sol = sol[sol["id"].isin(set(subd["id"]))]
        log("  smoke test: scoring only the rows that were predicted")
    mean15 = cm.score(sol, subd, "id")

    merged = sol.rename(columns={"parents_together": "_y"}).merge(
        subd.rename(columns={"parents_together": "_p"}), on="id", validate="one_to_one")
    per_cell = {c: cm._auc(g["_y"].to_numpy(), g["_p"].to_numpy())
                for c, g in merged.groupby("cell", sort=True)}

    # The one permitted reference, on the same rows and the same cells: a logistic on the signed gap. The gap
    # is joined ON THE ID, not assigned positionally — test.csv and solution.csv happen to be written in the
    # same order, but a reference that silently depends on that would be wrong the first time either file is
    # regenerated or filtered.
    from sklearn.linear_model import LogisticRegression

    def signed_years(df):
        """Signed years, woman minus man, resolution-independent.

        The nanosecond divisor this used to carry was wrong by 1000x because pandas returns microseconds for
        these columns. A monotone rescaling does not move an AUC, so the reference score was unaffected — but
        the same expression in the scraper turned a 60-year sanity filter into a no-op, so it is fixed in both
        places rather than left in the one where it happened not to matter.
        """
        dw = pd.to_datetime(df["dob_woman"].map(D.concrete)).to_numpy(dtype="datetime64[D]").astype("int64")
        dm = pd.to_datetime(df["dob_man"].map(D.concrete)).to_numpy(dtype="datetime64[D]").astype("int64")
        return (dw - dm) / 365.2425

    te = pd.read_csv(os.path.join(GRID, "test.csv"))
    te = te[["id"]].assign(_gap=signed_years(te))
    tr = pd.read_csv(os.path.join(GRID, "train.csv"))
    ref = LogisticRegression(max_iter=2000).fit(signed_years(tr).reshape(-1, 1),
                                               tr["parents_together"].to_numpy())
    merged = merged.merge(te, on="id", how="left", validate="one_to_one")
    if merged["_gap"].isna().any():
        raise SystemExit("some scored ids are absent from test.csv — the grid and the solution disagree")
    merged["_r"] = ref.predict_proba(merged["_gap"].to_numpy().reshape(-1, 1))[:, 1]
    ref_cell = {c: cm._auc(g["_y"].to_numpy(), g["_r"].to_numpy())
                for c, g in merged.groupby("cell", sort=True)}
    ref15 = float(np.mean(list(ref_cell.values())))

    LEV = ["full", "month", "year", "absent"]
    print(f"\n  MEAN OF 15 AUCs : {mean15:.4f}       reference (signed gap): {ref15:.4f}"
          f"       lift {mean15-ref15:+.4f}\n")
    print("  rows = man's date precision, columns = woman's\n")
    print("            " + "".join(f"{c:>10}" for c in LEV))
    for a in LEV:
        cells = "".join("         —" if a == "absent" and b == "absent"
                        else f"{per_cell[f'{a}|{b}']:>10.4f}" for b in LEV)
        print(f"  {a:<8}" + cells)

    json.dump({"metric": "mean of the 15 per-cell AUCs; absent x absent excluded",
               "mean15": mean15, "reference_signed_gap_mean15": ref15, "lift": mean15 - ref15,
               "per_cell": {k: float(v) for k, v in per_cell.items()},
               "reference_per_cell": {k: float(v) for k, v in ref_cell.items()},
               "couples": len(rows) // 15, "rows": len(rows)},
              open(os.path.join(MODEL, "grid_result.json"), "w"), indent=1)
    log(f"done in {(time.time()-T0)/60:.1f} min")


if __name__ == "__main__":
    main()
