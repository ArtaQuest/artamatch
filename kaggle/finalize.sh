#!/bin/zsh
# finalize.sh — everything that follows the scrape, in the only order it can run.
#
# Each step depends on the one before it: the trainer needs the split, the ranking needs the trainer's saved
# matrices, the publish steps need the model, the tournament needs the ranking's per-tradition predictions. So it
# is one script rather than five commands typed in an order that will eventually be typed wrong. Every step
# refuses to continue if the one before it did not produce what it promised.
#
# Usage: kaggle/finalize.sh /tmp/aqdur          # the directory scrape_duration.py wrote its four CSVs into
set -euo pipefail
# THE EDITION. 2026-08-18, operator: "start over and use marriage year. i.e., new dataset and new competition".
# The second edition keeps the relationship's START YEAR as an input, so it lives under its own directories and
# its own Kaggle slugs; the first edition's artefacts (/tmp/aqdur*, artamatch-astrology) are left untouched.
# Every one of these can be overridden from the environment to run the first edition again.
SRC="${1:-${AQ_SRC:-/tmp/aqmy}}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=~/.artamatch-venv/bin/python
MODEL="${AQ_MODEL_DIR:-/tmp/aqmymodel}"
COMP="${AQ_COMP_DIR:-/tmp/aqmycomp}"
DS="${AQ_DS_DIR:-/tmp/aqmyds}"
export KAGGLE_USERNAME=artafather
export KAGGLE_KEY="$($PY -c "import json;print(json.load(open('$HOME/.kaggle/kaggle.artafather.json'))['key'])")"

# The problem's own constants, in ONE place. The split boundary appears in the scraper, in the assertion below
# and in the dataset description, and when it moved from 1928 to 1850 the assertion was the copy that did not
# move — it went on passing because it only ever checked a floor the new data cleared anyway.
# THESE MUST TRACK scrape_duration.py, and the safest way is to READ them out of it rather than restate them.
# A copy is exactly how the old split assertion came to check a floor the data already cleared: the scraper moved
# to a death-bounded window with a 1900 split and this file still said 1850/1900, which would have failed every
# held-out couple born after 1900 -- that is now most of the test half.
# READ THE CONSTANTS BY EXECUTING THEM, not by matching them. A regex for
# `CEIL = int(os.environ.get("AQ_CEIL", str(time.gmtime().tm_year)))` did not survive this heredoc's escaping,
# and the numeric fallback could never match a CEIL that is computed rather than written -- so the whole
# finalize died on an AttributeError before it trained anything. Executing the two assignment lines cannot
# disagree with the scraper about what they say.
read -r CUT CEIL <<<"$($PY -c "
import os, re, time
src = open('$REPO/kaggle/scrape_duration.py').read()
ns = {'os': os, 'time': time}
for line in src.splitlines():
    if re.match(r'^(CUT|CEIL|FLOOR) *=', line):
        exec(line, ns)
print(ns['CUT'], ns['CEIL'])
")"
echo "  boundary read from the scraper: train <= $CUT, held out $((CUT+1))-$CEIL"
LABEL=lasted_30_years
DATASET="${AQ_DATASET:-artaquest-foundation/artamatch-marriage-year}"
COMPETITION="${AQ_COMPETITION:-artamatch-marriage-year}"

# NOTE on the heredocs below: a lone `-` immediately before one makes zsh report "redirection with no
# command". Blocks that pass arguments keep the `-` (it makes them sys.argv); the rest omit it, since python
# reads its script from stdin either way.

step() { printf '\n══ %s ══\n' "$1"; }
need() { [ -e "$1" ] || { echo "  MISSING $1 — the previous step did not produce it; stopping"; exit 1; }; }

step "0. the split exists, and its boundary is what it claims"
need "$SRC/train.csv"; need "$SRC/test.csv"; need "$SRC/solution.csv"; need "$SRC/sample_submission.csv"
$PY - "$SRC" "$CUT" "$CEIL" "$LABEL" <<'PYEOF'
import csv, sys
src, cut, ceil, label = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]


def later(r):
    """The later of the two KNOWN birth years. A training row may have one partner absent as 0000-00-00, and
    max() on the raw strings would make that absent partner the later one at year zero."""
    ys = [int(r[c][:4]) for c in ("dob_older", "dob_younger") if r[c][:4] != "0000"]
    assert ys, f"a row with no date at all: {r}"
    return max(ys)


tr = list(csv.DictReader(open(f"{src}/train.csv")))
te = list(csv.DictReader(open(f"{src}/test.csv")))
try_ = [later(r) for r in tr]
tey = [later(r) for r in te]
print(f"  train {len(tr):,} rows, later known birth {min(try_)}-{max(try_)}")
print(f"  test  {len(te):,} rows, later known birth {min(tey)}-{max(tey)}")
assert max(try_) <= cut < min(tey), f"the split is not temporal at {cut}"
assert max(tey) <= ceil, f"a held-out couple was born after {ceil} and may not be dead"
print(f"  the split is temporal at {cut}, and nothing is born after {ceil}")

# The test half must be strictly day-precision and complete — it is the measurement.
for r in te:
    for c in ("dob_older", "dob_younger"):
        assert r[c][:4] != "0000" and not r[c].endswith("-00"), f"test row is not day-precision: {r}"
print("  every test date is day-precision and present")

# THE START YEAR, the second edition's new input. An integer year in every row of both halves; never before a
# known birth; and in the held-out half never so late that thirty years before the ceiling is impossible.
for name, rows in (("train", tr), ("test", te)):
    for r in rows:
        sy = r["start_year"]
        assert sy.isdigit() and 1600 <= int(sy) <= ceil, f"{name}: start_year {sy!r} is not a year in range: {r}"
        for c in ("dob_older", "dob_younger"):
            if r[c][:4] != "0000":
                assert int(sy) >= int(r[c][:4]), f"{name}: relationship starts before the {c} birth: {r}"
assert max(int(r["start_year"]) for r in te) <= ceil - 30, \
    "a held-out relationship began too late for thirty years before the ceiling; its label is 0 by arithmetic"
sy_te = [int(r["start_year"]) for r in te]; sy_tr = [int(r["start_year"]) for r in tr]
print(f"  start_year present everywhere: train {min(sy_tr)}-{max(sy_tr)} · test {min(sy_te)}-{max(sy_te)} "
      f"(<= {ceil-30}, so thirty years is always possible)")

# The training half is deliberately mixed. Report the shape rather than demand one.
one = sum(1 for r in tr if "0000-00-00" in (r["dob_older"], r["dob_younger"]))
coarse = sum(1 for r in tr if r["dob_older"].endswith("-00") or r["dob_younger"].endswith("-00"))
print(f"  training half: {one:,} rows with one partner absent · {coarse:,} with a coarse date")

sol = list(csv.DictReader(open(f"{src}/solution.csv")))
assert label in sol[0], f"solution.csv has no {label} column: {list(sol[0])}"
for side in ("Public", "Private"):
    s = [int(r[label]) for r in sol if r["Usage"] == side]
    assert 0 < sum(s) < len(s), f"the {side} half has one class only"
    print(f"    {side:<8} {len(s):>6,} rows, {100*sum(s)/len(s):5.2f}% positive")
PYEOF

step "1. the competition bundle"
# The scraper already emits one row per couple at day precision, with the Public/Private split assigned. There
# is nothing left for build_dayday_test.py to do — it existed to collapse a test set that had one row per
# precision cell, and this test set never had those.
rm -rf "$COMP"; mkdir -p "$COMP"
cp "$SRC/test.csv" "$SRC/solution.csv" "$SRC/sample_submission.csv" "$SRC/train.csv" "$COMP/"
echo "  $COMP: $(wc -l < "$COMP/test.csv") test rows, $(wc -l < "$COMP/train.csv") train rows"

step "2. train the stack (19 traditions incl. numerology, ~45 min)"
rm -rf "$MODEL"
AQ_TRAIN="$SRC/train.csv" AQ_TEST="$SRC/test.csv" AQ_OUT="$MODEL" $PY "$REPO/kaggle/train_on_csv.py" 2>&1 \
  | grep -E "blocks ·|BASELINE|STACK|exported|wrote submission|done in|Traceback|core kept" || true
need "$MODEL/model.json"; need "$MODEL/oof_base.npy"; need "$MODEL/test_base.npy"

step "3. every tradition alone, ranked on the held-out set"
AQ_MODEL="$MODEL" AQ_TEST="$SRC/test.csv" AQ_SOL="$COMP/solution.csv" $PY "$REPO/kaggle/rank_traditions.py"
need "$MODEL/tradition_ranking.json"

step "4. the ensemble's held-out score, and the two references it must be read against"
$PY - "$MODEL" "$COMP" "$LABEL" <<'PYEOF'
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/Users/arash/Studio/artamatch/kaggle")
import competition_metric as cm
M, C, LABEL = sys.argv[1], sys.argv[2], sys.argv[3]
sol = pd.read_csv(f"{C}/solution.csv")
sub = pd.read_csv(f"{M}/submission.csv")
pred = [c for c in sub.columns if c != "id"][0]
m = sol.merge(sub.rename(columns={pred: "p"}), on="id")
y = m[LABEL].to_numpy()
print(f"  ensemble on {len(m):,} held-out day-precision couples: AUC {cm._auc(y, m.p):.4f}")
for side in ("Public", "Private"):
    s = m[m.Usage == side]
    print(f"    {side:<8} {cm._auc(s[LABEL], s.p):.4f}  ({len(s):,})")

# THE ERA RULE, the reference every claim in this project is measured against. On a temporal split a model that
# scores above chance but below this has read the calendar rather than the couple.
te = pd.read_csv(f"{C}/test.csv").set_index("id").loc[m.id]
era = (te.dob_older.str[:4].astype(int) + te.dob_younger.str[:4].astype(int)).to_numpy(float)
a = cm._auc(y, era)
print(f"  era rule (sum of the two birth years): AUC {max(a, 1-a):.4f}")

# THE SECOND EDITION'S REFERENCE. With the start year given, each partner's AGE AT THE START is the strongest
# ordinary predictor in the problem (older partner's age alone: 0.6351 held out on the first build; boosted
# trees on the two ages: 0.6486). That, and not the two-dates age gap, is what a leaderboard place must be read
# against now, so it is what `baseline_auc` carries. Fitted on the training rows where both ages are known.
if "start_year" in te.columns:
    from sklearn.ensemble import HistGradientBoostingClassifier
    trn = pd.read_csv(f"{C}/train.csv", dtype={"dob_older": str, "dob_younger": str})
    def ages(df):
        yo = pd.to_numeric(df.dob_older.str[:4], errors="coerce").where(df.dob_older != "0000-00-00")
        yy = pd.to_numeric(df.dob_younger.str[:4], errors="coerce").where(df.dob_younger != "0000-00-00")
        return np.column_stack([df.start_year - yo, df.start_year - yy])
    Atr, Ate = ages(trn), ages(te)
    okr = ~np.isnan(Atr).any(1)
    pb = np.zeros(len(te))
    for sd in range(3):
        cl = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                            l2_regularization=1.0, early_stopping=True,
                                            validation_fraction=0.15, random_state=sd)
        cl.fit(Atr[okr], trn.loc[okr, LABEL].to_numpy())
        pb += cl.predict_proba(Ate)[:, 1]
    ages_auc = cm._auc(y, pb / 3)
    a_old = cm._auc(y, Ate[:, 0]); a_old = max(a_old, 1 - a_old)
    print(f"  the older partner's AGE AT THE START alone:  AUC {a_old:.4f}")
    print(f"  boosted trees on the two ages at the start: AUC {ages_auc:.4f}   <- the reference for this edition")

# THE AGE GAP, the first edition's only permitted baseline: a 2-parameter logistic on dob_younger - dob_older.
#
# AND IT IS WRITTEN BACK INTO result.json, because the page was publishing the WRONG ONE. train_on_csv.py
# computes `baseline_auc` out-of-fold on the TRAINING half, where the gap is worth 0.5388; every published
# surface then set that beside the HELD-OUT ensemble at 0.5862 and read a +0.047 lift off two different row
# sets. On the held-out rows the gap is worth 0.6047, so the true comparison is a 0.019 LOSS. A baseline
# measured on other rows than the model is not a baseline, and the error ran in the flattering direction.
#
# The logistic needs no fitting for this number: b0 + b1*gap is monotone in gap and AUC is invariant under a
# monotone transform, so max(auc, 1-auc) IS the two-parameter model's AUC, with the sign of b1 the only choice.
gap = (te.dob_younger.str[:4].astype(int) - te.dob_older.str[:4].astype(int)).to_numpy(float)
a = cm._auc(y, gap)
gap_heldout = max(a, 1 - a)
print(f"  age gap (younger - older):             AUC {gap_heldout:.4f}")
ens = cm._auc(y, m.p)
print(f"  the ensemble is {'ABOVE' if ens > gap_heldout else 'BELOW'} the age-gap baseline on the same rows "
      f"({ens:.4f} vs {gap_heldout:.4f}, {ens-gap_heldout:+.4f})")
rp = f"{M}/result.json"
res = json.load(open(rp))
res["baseline_heldout_auc"] = float(gap_heldout)
# Only on the FIRST correction, or a rerun would record the corrected figure as the original and the
# training-half number would be lost. `setdefault` makes this step idempotent.
res.setdefault("baseline_train_auc", float(res.get("baseline_auc", float("nan"))))
res["baseline_auc"] = float(gap_heldout)       # what every page reads -- now on the model's own rows
if "start_year" in te.columns:
    res["baseline_gap_auc"] = float(gap_heldout)
    res["baseline_auc"] = float(ages_auc)          # the second edition's reference: the two ages at the start
    res["baseline_older_age_auc"] = float(a_old)
    res["baseline_name"] = "boosted trees on the two ages at the start"
res["heldout_auc"] = float(ens)
json.dump(res, open(rp, "w"), indent=1)
print(f"  wrote baseline_heldout_auc={gap_heldout:.4f} into result.json (was {res['baseline_train_auc']:.4f}, "
      f"measured on the training half)")

# model.json is what the PAGE reads, and it carried the training-half baseline under a name that did not say so,
# sitting directly beside the held-out ensemble. Relabel it on the model's own rows. The old figure is kept
# under an explicit name rather than dropped -- it is a real number, it was just never a baseline for this
# comparison.
mp = f"{M}/model.json"
mj = json.load(open(mp))
b = mj.setdefault("baseline", {})
stale = b.pop("logistic on the age gap (younger - older)", None)
b["logistic on the age gap (younger - older), held out"] = float(gap_heldout)
if stale is not None:
    b["the same logistic measured out-of-fold on the TRAINING half (not a baseline for the held-out score)"] = float(stale)
mj.setdefault("heldout", {})["age_gap"] = float(gap_heldout)
mj.setdefault("temporal", {})["age_gap"] = float(gap_heldout)
json.dump(mj, open(mp, "w"), indent=1)
print(f"  model.json baseline relabelled to the held-out age gap {gap_heldout:.4f}"
      + (f" (training-half {stale:.4f} kept under its own name)" if stale is not None else ""))
PYEOF

step "5. publish: dataset version, competition data, model version"
rm -rf "$DS" && mkdir -p "$DS"
cp "$SRC/train.csv" "$SRC/test.csv" "$SRC/sample_submission.csv" "$DS/"
$PY - "$DATASET" "$DS" <<'PYEOF'
import json, sys
ref = sys.argv[1]
owner, slug = ref.split("/")
desc = """# Let's end this loneliness epidemic with astrology.

Two birth dates and the year it began, one bit out: **did the relationship last thirty years?**

| column | meaning |
|---|---|
| `dob_older` | the older partner's date of birth |
| `dob_younger` | the younger partner's date of birth |
| `start_year` | the year the relationship began — the wedding year for a marriage |
| `lasted_30_years` | 1 if the relationship lasted thirty years or longer, else 0 |

**Second edition.** The first edition of this dataset (`artamatch-astrology`) computed the label from the
relationship's own dates and then discarded them. This one **keeps the start year as an input**. It is given as
a year rather than a full date because Wikidata's `P580` qualifier is often year-precision and the build did not
fetch its precision flag — a month and day would be placeholders for a large share of rows and could not be told
from real ones. The year is exact at every precision. What it buys a model is real: each partner's **age at the
start**, the **era** the relationship began in, and — for the held-out half — the ceiling on how long it could
possibly have run.

**Any relationship two people chose**: a marriage, an unmarried partnership, a business or sporting
partnership, or Wikidata's general "significant person" relation (`P26`, `P451`, `P1327`, `P3342`). Same-sex
couples are in by construction, because nothing here reads a sex: the first column is simply the older partner,
computed from the two dates.

## How the label is computed

Exactly as a Wikipedia infobox reads a marriage — *"m. 1903; div. 1919"* — and the same for every other
relationship type:

* an **end date** is recorded (`P582`): the relationship ran from `P580` to `P582`.
* **no end date**: it ran until somebody died, so the end is the earlier of the two deaths (`P570`).

`lasted_30_years` is `(end - start) >= 30 years`. **A relationship ended by a death is not automatically a long
one** — twelve years is a 0, forty years is a 1. Death buys no credit.

## Train births 1600-1900, hold out 1901 onward — a TEMPORAL split, bounded by DEATH

A relationship that has not ended cannot be given a duration. Rather than cap birth years and infer it, this
dataset requires a **datable end** — a recorded end date, or a recorded death of a partner — and the held-out
half requires both partners to be dead. So the window runs to the present and the split is by time: learn from
the historical couples, predict the modern ones.

**Read this before you read the leaderboard.** That rule has a consequence you can now compute exactly, because
the start year is a column: a held-out couple is dead by 2026, so a relationship that began in year *s* cannot
have lasted longer than *2026 − s*. Relationships that began after **1996** cannot reach thirty years at all —
their label would be 0 by arithmetic — and they are **removed from the test set** rather than left in as free
points. Nearer the boundary the effect is soft but real: the later the start, the more "both already dead"
selects for early deaths, and an early death ends a relationship. The build notebook prints the positive rate by
start decade and by age at the start so you can see exactly where it bites. **The training half, all born by
1900, contains no couple for whom this ceiling ever binds** — a model cannot learn it from the rows; it has to
come from the definition.

## The test set is strict; the training set is not

**Test**: both partners known to the day, both dead, no placeholder dates, the couple's later birth after 1900,
the start year at or before 1996.

**Train**: as inclusive as the data allows. A date may be known only to the month (`1809-11-00`) or only to the
year (`1802-00-00`), and **one partner may be absent from Wikidata entirely** (`0000-00-00`, always in the
second column, since a one-sided row has no age order). `00` means unknown; `0000-00-00` means absent. The start
year is present in every row of both halves.

```
dob_older,dob_younger,start_year,lasted_30_years
1794-06-12,1801-03-27,1823,1     <- both known to the day; began 1823
1802-00-00,1809-11-00,1831,0     <- one year only; the other year and month
1777-04-30,0000-00-00,1799,1     <- the second partner is not in Wikidata at all
```

That is not a rounding decision. Measured on Wikidata, requiring both partners to the day gives about a tenth of
the rows that requiring one partner at any precision does. A relationship's duration is known just as exactly
when one partner's birthday is not, so a one-sided row carries a real label and half an input. Filter them out
in one line if you want only clean rows.

## The confounds to know about

Relationships with a recorded END date reach thirty years far less often than ones that ran until a death.
Which case a couple is in **is not a column** — but it correlates with things that are. And with the start year
given, **age at the start** and the **age gap** are strong, ordinary predictors that owe nothing to any tradition.
Read a leaderboard place against those, not against 0.5.

## Two traps in the dates, both measured and both handled

**1 January is a placeholder.** Among day-precision births 1600-1900 it occurs 2.07x as often as a median
January day, while 2 January sits at 1.00x — a source that knew only the year got imported with a day anyway.
Excluded from the TEST half at day precision; kept in the training half as noise worth having; never excluded
at year precision, where `1850-01-01` is simply how Wikidata spells 1850.

**The calendar is one calendar, and the placeholder moves inside it.** Wikidata's RDF gives every date in the
proleptic Gregorian calendar whatever `timeCalendarModel` says — Newton's Julian-tagged statement carries the
literal `1643-01-04`, the Gregorian image of 25 December 1642. So no conversion is needed. But it means a
*Julian* 1 January placeholder is stored as 11, 12 or 13 January by century, and that excess is real: 2.08x the
median January day at 13 January among Julian-tagged records. Excluded from the test half at the
century-correct date.

Built by a public notebook that runs the SPARQL live, so anyone can re-run it and contradict it.
"""
meta = {"title": "ArtaMatch: two birth dates and a start year",
        "id": ref, "licenses": [{"name": "CC0-1.0"}],
        "subtitle": "Two birth dates, older first, and the year it began. Did the relationship last thirty years?",
        "description": desc}
json.dump(meta, open(sys.argv[2] + "/dataset-metadata.json", "w"), indent=1)
print(f"  metadata written for {ref}")
PYEOF
$PY - "$DATASET" "$DS" <<'PYEOF' 2>&1 | grep -viE "^\s*[0-9]+%|B/s" | tail -2
import sys, time
from kaggle.api.kaggle_api_extended import KaggleApi
ref = sys.argv[1]
api = KaggleApi(); api.authenticate()
notes = "second edition: the START YEAR is a column; births 1600-1900 train / 1901+ dead test; test excludes starts after 1996"
for i in range(4):
    try:
        # A NEW dataset the first time, a new version after that. dataset_create_version on a slug that does
        # not exist yet answers 404 rather than creating it.
        try:
            print("  dataset ->", api.dataset_create_new(sys.argv[2], public=True, quiet=True, dir_mode="skip"))
        except Exception as e0:
            if "already exists" not in str(e0).lower() and "409" not in str(e0):
                raise
            print("  dataset ->", api.dataset_create_version(sys.argv[2], version_notes=notes,
                                                             quiet=True, dir_mode="skip"))
        break
    except Exception as e:
        print(f"  attempt {i+1}: {str(e)[:100]}")
        time.sleep(4 * (i + 1))
PYEOF
AQ_COMP="$COMPETITION" $PY "$REPO/kaggle/publish_competition.py" "$COMP" 2>&1 \
  | grep -E "uploaded|databundle|500|Error" | tail -4 || true
(cd "$REPO/kaggle" && AQ_MODEL_DIR="$MODEL" $PY publish_model.py 2>&1 \
  | grep -viE "^\s*[0-9]+%|B/s" | tail -2) || true

if [ -n "${AQ_SKIP_PAGE:-}" ]; then
  echo; echo "══ 6-8 skipped (AQ_SKIP_PAGE): the web page and the tournament are first-edition surfaces; the page takes two dates only ══"
  exit 0
fi
step "6. the page: inject, ship, verify"
(cd "$REPO" && AQ_MODEL="$MODEL" AQ_TRAIN="$SRC/train.csv" $PY web/inject_benchmark.py \
  && $PY web/ship.py 2>&1 | grep -E "end to end|wrote docs" \
  && $PY web/verify_docs.py docs 2>&1 | tail -1 \
  && $PY web/test_runner.py docs 2>&1 | tail -1)

step "7. the tournament: every account sends its ensembles, five a day each"
# One process per account, in sequence — the Kaggle client authenticates at IMPORT, so a credential swapped
# inside a running process still acts as the account it started as. The ledger makes each call idempotent, so
# re-running this tomorrow continues rather than repeats.
for acct in artafather arash0ash ashranet ashraasn; do
  if [ -f "$HOME/.kaggle/kaggle.$acct.json" ]; then
    printf '\n  ── %s ──\n' "$acct"
    AQ_MODEL="$MODEL" AQ_TEST="$SRC/test.csv" AQ_COMP_TEST="$COMP/test.csv" AQ_COMP="$COMPETITION" \
      $PY "$REPO/kaggle/tournament.py" round "$acct" || true
  fi
done

step "8. the board as it stands"
AQ_MODEL="$MODEL" AQ_TEST="$SRC/test.csv" AQ_COMP_TEST="$COMP/test.csv" AQ_COMP="$COMPETITION" \
  $PY "$REPO/kaggle/tournament.py" board || true

step "done — run kaggle/tournament.py round <account> daily to continue the contest"
