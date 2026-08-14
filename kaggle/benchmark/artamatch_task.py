# %% [markdown]
# ArtaMatch: two birth dates, one shared child — an ArtaQuest Foundation benchmark.
#
# THE SCORE IS THE MEAN OF FOURTEEN AUCs, and the scorer is this file. A community competition on Kaggle can
# only be scored by one of Kaggle's built-in metrics — the API refuses to make one a code competition
# (`OnlyAllowKernelSubmissions cannot be updated`, 403) — so the metric the operator specified lives here,
# where the grading code is mine.
#
# THE TASK. Each item is a declared couple from Wikidata reduced to the two things a stranger can check: the
# man's birth date and the woman's. The question is whether a child exists who names BOTH of them as parents.
# The model is asked for a PROBABILITY, not a yes or no, because an AUC over binary answers throws away
# everything except the threshold and collapses into balanced accuracy.
#
# THE FIFTEEN CELLS. Each partner's date is degraded independently over four levels — the full date, the month
# only, the year only, absent — which is a 4x4 grid, and the cell where BOTH are absent is dropped: with
# neither date there is no input, every item would be identical, and the cell could not rank anyone. That
# leaves fourteen. AUC is computed within each cell and the fifteen are averaged, so a model that is good on
# clean dates and useless on vague ones scores worse than one that degrades gracefully — which is the point.
#
# WHAT TO COMPARE A SCORE AGAINST. Chance is 0.5, but 0.5 is not the bar: a two-parameter logistic on the
# SIGNED difference between the two dates (woman minus man) is computed here on the same couples and the same
# fourteen cells, and printed beside the model's number. That is the reference this task is scored against.
#
# THE WINDOW MATTERS. Everyone in this data was born 1800-1950. An earlier version ran to 2026, and its
# dominant effect was exposure rather than anything about the pairing: recorded parenthood ran about 58% for
# couples born in the 1800s and 2% for the 1990s, because a couple born in 1990 may not have finished having
# children and any child they do have has not had time to become notable enough to record. Restricting the
# window leaves a residual gradient of 0.385 across decades against roughly 0.56 before — smaller, real, and
# not zero.
#
# The couples are drawn from the PUBLIC training half of
# artaquest-foundation/artamatch-two-birth-dates (CC0), so nothing here is a held-out answer key — a
# benchmark whose answers sit in a public file would be measuring recall, and this one is meant to measure
# whether two dates carry anything at all.

# %%
import csv
import glob
import json
import random
import re

import kaggle_benchmarks as kbench

SEED = 20260813
N_COUPLES = 60          # per cell; 14 cells x 60 = 900 judgements per model
# Couples per prompt. Batching is what makes the fifteen-cell grid affordable: judged one at a time this task
# would be 900 model-proxy calls, and the daily allowance is $10 against a task run costing roughly $2. At 30
# per prompt it is 2 calls per cell, 30 per model, and the whole five-model field fits inside two days.
BATCH = 30
LEVELS = ["full", "month", "year", "absent"]
# Two of the sixteen combinations are not scored, and the scorer, the grid and this task must agree on which.
# absent|absent has no input at all; month|month is a case the records essentially never present — 18 real pairs
# out of 107,698, where an AUC is noise. (Kept as a literal here because a Kaggle benchmark notebook cannot
# import the repository's dates.py; the list is asserted against the published metric in the task text.)
EXCLUDED = {("absent", "absent"), ("month", "month")}
CELLS = [(a, b) for a in LEVELS for b in LEVELS if (a, b) not in EXCLUDED]
NO_DATE = "1900-01-01"

PROMPT = """You are given {n} couples. For each, the only facts available are the man's date of birth and the
woman's date of birth — nothing else. No names, no places, no occupations.

Dates are YYYY-MM-DD, and `00` means that part is NOT KNOWN: `1889-00-00` is a birth in 1889 with the month and
day unrecorded, `1889-04-00` is April 1889 with the day unrecorded. Everyone here was born between 1800 and
1950, so all of them have had a full lifetime in which to have children.

For each couple, estimate the PROBABILITY that a child exists who names both of them as parents.

Answer with exactly {n} lines, each of the form
  <number>: <probability between 0 and 100>
and nothing else. No explanation, no preamble.

{items}"""


# An unknown component is written `00`, the same encoding the dataset itself uses: `1889-00-00` is a year and
# `1889-04-00` a month. Coarsening is IDEMPOTENT, so a date that only ever had a year is indistinguishable from
# one coarsened down to a year — which is what makes the `year|year` cell a question about ranking rather than
# about how well documented somebody is.
def month_only(d):
    return d[:7] + "-00"


def year_only(d):
    return d[:4] + "-00-00"


COARSEN = {"full": None, "month": month_only, "year": year_only, "absent": "absent"}


def degrade(man, woman, lm, lw):
    """The man's date at level lm and the woman's at lw.

    Coarsen first, substitute second. An absent partner takes the other's date AS THE MODEL SEES IT — doing
    the substitution first would give the absent partner a full date copied from someone whose own record had
    already been cut back to a month, putting precision into the item that exists nowhere in its inputs.
    """
    m, w = man, woman
    if COARSEN[lm] not in (None, "absent"):
        m = COARSEN[lm](m)
    if COARSEN[lw] not in (None, "absent"):
        w = COARSEN[lw](w)
    if COARSEN[lm] == "absent":
        m = w
    if COARSEN[lw] == "absent":
        w = m
    return m, w


def find_train():
    for pattern in ("/kaggle/input/artamatch-two-birth-dates/train.csv",
                    "/kaggle/input/*/train.csv", "/kaggle/input/**/train.csv", "**/train.csv"):
        hits = sorted(glob.glob(pattern, recursive=True))
        if hits:
            return hits[0]
    raise RuntimeError("train.csv not found; attach artaquest-foundation/artamatch-two-birth-dates. "
                       f"/kaggle/input holds {sorted(glob.glob('/kaggle/input/*'))}")


def load_couples():
    """A balanced draw, so a cell's AUC is not dominated by the class prior.

    The corpus is 29.8% positive. Drawing at random would give a model that says "probably not" to everything
    a respectable-looking accuracy while its AUC stayed at chance — balancing removes that distraction and
    makes the AUC the only thing being measured.
    """
    rows = []
    with open(find_train()) as f:
        for r in csv.DictReader(f):
            if r.get("dob_man") and r.get("dob_woman"):
                rows.append((r["dob_man"], r["dob_woman"], int(r["parents_together"])))
    rows.sort()                                   # a stable order before seeding: no wall clock, no dict order
    rng = random.Random(SEED)
    pos = [r for r in rows if r[2] == 1]
    neg = [r for r in rows if r[2] == 0]
    rng.shuffle(pos)
    rng.shuffle(neg)
    half = N_COUPLES // 2
    picked = pos[:half] + neg[:half]
    rng.shuffle(picked)
    return picked


def auc(y, s):
    """Rank AUC with ties averaged. Written out because a benchmark should not depend on sklearn being present."""
    pairs = sorted(zip(s, y))
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    n1 = sum(1 for _, yy in pairs if yy == 1)
    n0 = len(pairs) - n1
    if n1 == 0 or n0 == 0:
        return 0.5
    s1 = sum(r for r, (_, yy) in zip(ranks, pairs) if yy == 1)
    return (s1 - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def parse(text, n):
    """Pull n probabilities out of whatever the model said. Missing or unparseable answers become 0.5."""
    out = [0.5] * n
    for line in (text or "").splitlines():
        m = re.match(r"\s*(\d+)\s*[:.)-]\s*([0-9]*\.?[0-9]+)", line)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        if 0 <= idx < n:
            v = float(m.group(2))
            out[idx] = min(max(v / 100.0 if v > 1.0 else v, 0.0), 1.0)
    return out


@kbench.task(
    name="ArtaMatch: two birth dates, one shared child",
    description="Mean of 14 AUCs over a man x woman date-precision grid, absent x absent excluded.",
)
def artamatch_two_birth_dates_one_shared_child(llm) -> float:
    couples = load_couples()
    y = [c[2] for c in couples]
    per_cell = {}
    for lm, lw in CELLS:
        scores = []
        for start in range(0, len(couples), BATCH):
            chunk = couples[start:start + BATCH]
            items = "\n".join(
                f"{i+1}. man born {degrade(m, w, lm, lw)[0]}, woman born {degrade(m, w, lm, lw)[1]}"
                for i, (m, w, _) in enumerate(chunk))
            reply = llm.prompt(PROMPT.format(n=len(chunk), items=items))
            scores += parse(getattr(reply, "text", str(reply)), len(chunk))
        per_cell[f"{lm}|{lw}"] = auc(y, scores)
        print(f"  {lm:>6} x {lw:<6}  AUC {per_cell[f'{lm}|{lw}']:.4f}", flush=True)

    # Weighted by each cell's row count, to match the published metric exactly. Every cell here holds the same
    # couples so the weights are equal and this equals a plain mean — the point is that the definition and the
    # code say the same thing, so a future change to how cells are sampled cannot silently diverge.
    counts = {k: len(couples) for k in per_cell}
    tot = sum(counts.values())
    mean_cells = sum(per_cell[k] * counts[k] for k in per_cell) / tot

    # The reference, on the same couples and the same fourteen cells, so the model's number has something to
    # be compared with other than chance. The orientation is fixed, not chosen per cell: picking whichever of
    # AUC and 1-AUC is larger would let the reference read the labels and flatter itself on every cell where
    # it is worse than chance.
    gap_auc = []
    for lm, lw in CELLS:
        d = [degrade(m, w, lm, lw) for m, w, _ in couples]
        signed = [(int(w[:4]) * 365 + int(w[5:7]) * 30 + int(w[8:10]))
                  - (int(m[:4]) * 365 + int(m[5:7]) * 30 + int(m[8:10])) for m, w in d]
        gap_auc.append(auc(y, signed))
    print(f"\n  weighted mean of {len(per_cell)} AUCs            : {mean_cells:.4f}")
    print(f"  reference, signed gap (woman-man)  : {sum(gap_auc)/len(gap_auc):.4f}")
    print(f"\n  cells: {json.dumps({k: round(v, 4) for k, v in per_cell.items()})}")
    return mean_cells


artamatch_two_birth_dates_one_shared_child.run(kbench.llm)
