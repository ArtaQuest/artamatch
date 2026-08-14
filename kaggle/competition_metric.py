"""
competition_metric.py — the competition's scorer. Mean of the 15 per-cell AUCs.

WHY A CUSTOM SCORER AND NOT A BUILT-IN. The metric the operator specified is the mean of fifteen AUCs, one per
cell of a man x woman date-precision grid. Kaggle's built-in AUC would pool all 256,005 rows into one ranking,
and a pooled AUC is NOT the mean of the per-cell AUCs. The reason is dilution, and it is severe: every cell
holds the SAME held-out couples with the SAME labels, so of all the positive-negative pairs a pooled AUC ranks,
only one in fifteen is a pair from inside the same cell. Fourteen fifteenths of the score is therefore
comparing a positive in one cell against a negative in another — a question about the level of missing
information, not about the couples. A model whose ranking is perfect inside every single cell scores 1.000 on
this metric and can score near 0.5 pooled, purely from how its output happens to be offset from cell to cell;
`_selftest` constructs exactly that case and asserts the gap. Averaging within cells first is what makes the
score mean "how well does this rank couples, at each level of missing information".

HOW KAGGLE RUNS THIS. A community competition can be scored by a Kernels metric — a notebook exposing

    score(solution: pd.DataFrame, submission: pd.DataFrame, row_id_column_name: str) -> float

which Kaggle calls with the two frames already aligned and the row-id column named. That hook is the only
place a host-written scorer can live: `evaluation_metric` on the competition object is read-only, and
`UpdateCompetitionSettings` refuses the code-competition switches outright
(`OnlyAllowKernelSubmissions cannot be updated`, HTTP 403), so the metric is chosen once in the UI and this
file is what it points at.

THE GRID. Each partner's birth date is degraded independently over four levels — the full date, the month
only, the year only, absent — and the cell where BOTH are absent is excluded. With neither date there is no
input: every row in that cell carries the same placeholder, so no model can rank them and the cell would move
every competitor's average by the same constant without separating anyone. Four by four minus that one is
fifteen, and the held-out couples are duplicated across all fifteen so a submission is scored on every level
of missing information rather than only on clean dates.

Self-test: ~/.artamatch-venv/bin/python competition_metric.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dates as D          # noqa: E402  — the grid is defined once, in dates.py

CELL_COLUMN = "cell"
EXCLUDED = D.EXCLUDED_CELLS
N_CELLS = D.N_CELLS


class ParticipantVisibleError(Exception):
    """Kaggle shows this message to the competitor. Anything else surfaces as a generic scoring failure."""


def _auc(y, s):
    """Rank AUC with ties averaged, via the Mann-Whitney identity.

    Ties matter here rather than being a technicality: a competitor who submits the same probability for every
    row of a cell must score exactly 0.5 on it, not 0 or 1 depending on how the sort happened to break ties.
    """
    y = np.asarray(y, dtype=np.int8)
    s = np.asarray(s, dtype=np.float64)
    n1 = int(y.sum())
    n0 = y.size - n1
    if n1 == 0 or n0 == 0:
        return None                      # a cell with one class carries no ranking information
    order = np.argsort(s, kind="mergesort")
    s_sorted = s[order]
    ranks = np.empty(s.size, dtype=np.float64)
    i = 0
    while i < s.size:
        j = i
        while j + 1 < s.size and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2.0 + 1.0
        i = j + 1
    r = np.empty(s.size, dtype=np.float64)
    r[order] = ranks
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def score(solution: pd.DataFrame, submission: pd.DataFrame, row_id_column_name: str) -> float:
    target = [c for c in solution.columns if c not in (row_id_column_name, CELL_COLUMN, "Usage")]
    if not target:
        raise ParticipantVisibleError("the solution file carries no target column")
    target = target[0]

    pred_col = [c for c in submission.columns if c != row_id_column_name]
    if len(pred_col) != 1:
        raise ParticipantVisibleError(
            f"the submission must have exactly two columns, {row_id_column_name} and a prediction; "
            f"found {list(submission.columns)}")
    pred_col = pred_col[0]

    if CELL_COLUMN not in solution.columns:
        raise ParticipantVisibleError(f"the solution file has no '{CELL_COLUMN}' column, so per-cell AUCs "
                                      "cannot be computed")
    # Rename before merging. The submission's prediction column is normally called the same thing as the
    # solution's target — Kaggle's own sample_submission.csv is generated that way — and a merge would then
    # suffix BOTH to _x/_y, so every later lookup by the original name raises. Renaming to names that cannot
    # collide keeps the alignment independent of what the competitor called their column.
    sol = solution.rename(columns={target: "_y_true"})
    sub = submission.rename(columns={pred_col: "_y_pred"})[[row_id_column_name, "_y_pred"]]
    target, pred_col = "_y_true", "_y_pred"
    # Align on the row id rather than trusting row order. A submission sorted differently from the solution
    # would otherwise score against the wrong labels and produce a plausible number near 0.5 — the worst kind
    # of wrong, because nothing looks broken.
    if sub[row_id_column_name].duplicated().any():
        raise ParticipantVisibleError(f"the submission repeats some {row_id_column_name} values")
    merged = sol.merge(sub, on=row_id_column_name, how="left", validate="one_to_one")
    missing = int(merged[pred_col].isna().sum())
    if missing:
        raise ParticipantVisibleError(f"{missing:,} of {len(merged):,} rows have no prediction — a submission "
                                      f"must cover every row of {row_id_column_name}")
    p = pd.to_numeric(merged[pred_col], errors="coerce")
    if p.isna().any():
        raise ParticipantVisibleError("some predictions are not numbers")
    if not np.isfinite(p.to_numpy()).all():
        raise ParticipantVisibleError("some predictions are infinite or NaN")

    merged = merged[~merged[CELL_COLUMN].isin(EXCLUDED)]
    # EACH CASE SCORED SEPARATELY, THEN AVERAGED BY HOW MANY ROWS IT HAD. On this grid every cell holds the
    # same held-out couples, so the counts are equal and a weighted mean is arithmetically identical to a plain
    # one — which is exactly why the weighting is worth writing down rather than assumed: the moment a cell
    # loses rows (one class absent, a row unscored, a future grid that samples cells differently) an unweighted
    # mean starts giving a 40-row cell the same voice as a 25,000-row one.
    aucs, counts = {}, {}
    for cell, g in merged.groupby(CELL_COLUMN, sort=True):
        a = _auc(g[target].to_numpy(), pd.to_numeric(g[pred_col]).to_numpy())
        if a is not None:
            aucs[cell] = a
            counts[cell] = int(len(g))
    if not aucs:
        raise ParticipantVisibleError("no cell had both classes present, so no AUC could be computed")
    # Abstain loudly rather than quietly averaging a short list: a scorer that silently drops cells reports a
    # number for a different metric than the one the leaderboard claims to show.
    if len(aucs) != N_CELLS:
        raise ParticipantVisibleError(
            f"scored {len(aucs)} cells but this metric is the mean of {N_CELLS}; "
            f"missing {sorted(set(_expected_cells()) - set(aucs))}")
    w = np.array([counts[c] for c in aucs], dtype=np.float64)
    v = np.array([aucs[c] for c in aucs], dtype=np.float64)
    return float(np.sum(w * v) / np.sum(w))


def per_cell(solution, submission, row_id_column_name):
    """The same computation, but returning each case's AUC and its row count instead of one number.

    The leaderboard needs a scalar; a reader needs to see which case was hard and how much of the average it
    is entitled to. Both come from one code path so they cannot disagree.
    """
    out = {}
    sol = solution
    target = [c for c in sol.columns if c not in (row_id_column_name, CELL_COLUMN, "Usage")][0]
    pred = [c for c in submission.columns if c != row_id_column_name][0]
    m = (sol.rename(columns={target: "_y"})
         .merge(submission.rename(columns={pred: "_p"})[[row_id_column_name, "_p"]],
                on=row_id_column_name, how="inner", validate="one_to_one"))
    m = m[~m[CELL_COLUMN].isin(EXCLUDED)]
    for cell, g in m.groupby(CELL_COLUMN, sort=True):
        a = _auc(g["_y"].to_numpy(), pd.to_numeric(g["_p"]).to_numpy())
        out[cell] = {"auc": None if a is None else float(a), "n": int(len(g)),
                     "positives": int(g["_y"].sum())}
    return out


def _expected_cells():
    return list(D.CELLS)


def _selftest():
    """Three properties, each of which a wrong scorer fails.

    1. A perfect submission scores 1 and a reversed one scores 0 — orientation is not accidentally flipped.
    2. A constant submission scores exactly 0.5 — ties are averaged, not sorted arbitrarily.
    3. The average is WEIGHTED BY EACH CASE'S ROW COUNT, and a constructed case proves the weighting is
       actually applied: two cells with wildly different sizes and opposite scores must land near the big one.
    4. POOLED AUC AND THIS METRIC DISAGREE, which is the whole reason the scorer exists. The submission is
       built to rank PERFECTLY inside every cell — so this metric must return exactly 1.0 — while carrying a
       different additive offset per cell. Pooled AUC then collapses towards chance, because fourteen
       fifteenths of the pairs it ranks are cross-cell and those are decided by the offsets. No amount of
       skill inside the cells can repair it, which is what "pooled AUC is a different metric" means here.
    """
    rng = np.random.default_rng(11)
    cells = _expected_cells()
    ids, cell, y = [], [], []
    for c in cells:
        for i in range(200):
            ids.append(f"{i}_{c}")
            cell.append(c)
            y.append(int(rng.random() < 0.3))
    sol = pd.DataFrame({"id": ids, "parents_together": y, "cell": cell, "Usage": "Public"})
    y = np.asarray(y)

    perfect = pd.DataFrame({"id": ids, "parents_together": y * 1.0})
    assert abs(score(sol, perfect, "id") - 1.0) < 1e-12, score(sol, perfect, "id")
    rev = pd.DataFrame({"id": ids, "parents_together": 1.0 - y})
    assert abs(score(sol, rev, "id") - 0.0) < 1e-12, score(sol, rev, "id")
    const = pd.DataFrame({"id": ids, "parents_together": np.full(len(ids), 0.42)})
    assert abs(score(sol, const, "id") - 0.5) < 1e-12, score(sol, const, "id")
    print("  perfect=1.0  reversed=0.0  constant=0.5")

    # A shuffled submission must score the same as an ordered one: alignment is by id, not by position.
    perm = rng.permutation(len(ids))
    shuf = pd.DataFrame({"id": [ids[i] for i in perm], "parents_together": (y * 1.0)[perm]})
    assert abs(score(sol, shuf, "id") - 1.0) < 1e-12, "alignment is following row order, not the id"
    print("  a shuffled submission scores the same as an ordered one")

    # THE WEIGHTING IS APPLIED, not merely described. Build a solution whose cells differ hugely in size, score
    # one perfectly and one backwards, and check the answer follows the larger cell rather than sitting halfway.
    big, small = "full|full", "year|year"          # both survive the exclusion, so the weighting test is valid
    ids2, cell2, y2, p2 = [], [], [], []
    for c in cells:
        n = 2000 if c == big else (40 if c == small else 200)
        for i in range(n):
            yy = i % 2
            ids2.append(f"{c}#{i}")
            cell2.append(c)
            y2.append(yy)
            p2.append(yy if c != small else 1 - yy)      # perfect everywhere, reversed in the small cell
    sol2 = pd.DataFrame({"id": ids2, "parents_together": y2, "cell": cell2, "Usage": "Public"})
    sub2 = pd.DataFrame({"id": ids2, "parents_together": [float(x) for x in p2]})
    got = score(sol2, sub2, "id")
    unweighted = float(np.mean([1.0 if c != small else 0.0 for c in cells]))
    pc = per_cell(sol2, sub2, "id")
    print(f"  weighting : one 40-row cell scored 0 against fourteen larger cells scored 1 -> {got:.4f} "
          f"(unweighted would be {unweighted:.4f})")
    assert pc[small]["n"] == 40 and pc[big]["n"] == 2000, pc
    assert got > unweighted + 0.01, (got, unweighted)
    assert abs(got - 1.0) < 0.02, got

    # The disagreement with pooled AUC: perfect inside every cell, offset between cells.
    off = {c: i for i, c in enumerate(cells)}                  # a different additive offset per cell
    p = np.array([off[c] + 0.5 * yy for c, yy in zip(cell, y)], dtype=float)
    sub = pd.DataFrame({"id": ids, "parents_together": p})
    mine = score(sol, sub, "id")
    pooled = _auc(y, p)
    print(f"  perfect within every cell -> this metric {mine:.4f}, pooled AUC {pooled:.4f} "
          f"(a gap of {mine-pooled:.4f})")
    assert abs(mine - 1.0) < 1e-12, mine
    assert mine - pooled > 0.4, (mine, pooled)

    for bad, why in ((pd.DataFrame({"id": ids[:-5], "parents_together": 0.5}), "an incomplete submission"),
                     (pd.DataFrame({"id": ids, "p": "x"}), "a non-numeric prediction")):
        try:
            score(sol, bad, "id")
        except ParticipantVisibleError as e:
            print(f"  refused {why}: {str(e)[:66]}")
        else:
            raise AssertionError(f"{why} was accepted")
    print("  self-test passed")


if __name__ == "__main__":
    _selftest()
