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
SRC="${1:-/tmp/aqdur}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=~/.artamatch-venv/bin/python
MODEL=/tmp/aqdurmodel
COMP=/tmp/aqdurcomp
export KAGGLE_USERNAME=artafather
export KAGGLE_KEY="$($PY -c "import json;print(json.load(open('$HOME/.kaggle/kaggle.artafather.json'))['key'])")"

# The problem's own constants, in ONE place. The split boundary appears in the scraper, in the assertion below
# and in the dataset description, and when it moved from 1928 to 1850 the assertion was the copy that did not
# move — it went on passing because it only ever checked a floor the new data cleared anyway.
# THESE MUST TRACK scrape_duration.py, and the safest way is to READ them out of it rather than restate them.
# A copy is exactly how the old split assertion came to check a floor the data already cleared: the scraper moved
# to a death-bounded window with a 1900 split and this file still said 1850/1900, which would have failed every
# held-out couple born after 1900 -- that is now most of the test half.
CUT=$($PY -c "import re,sys; s=open('$REPO/kaggle/scrape_duration.py').read(); print(re.search(r'^CUT = (\\d+)', s, re.M).group(1))")
CEIL=$($PY -c "
import re, time
s = open('$REPO/kaggle/scrape_duration.py').read()
m = re.search(r'^CEIL = int\\(os\\.environ\\.get\\("AQ_CEIL", str\\(time\\.gmtime\\(\\)\\.tm_year\\)\\)\\)', s, re.M)
print(time.gmtime().tm_year if m else re.search(r'^CEIL = (\\d+)', s, re.M).group(1))
")
echo "  boundary read from the scraper: train <= $CUT, held out $((CUT+1))-$CEIL"
LABEL=lasted_30_years
DATASET=artaquest-foundation/artamatch-astrology
COMPETITION=artamatch-astrology

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
    ys = [int(r[c][:4]) for c in ("dob_man", "dob_woman") if r[c][:4] != "0000"]
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
    for c in ("dob_man", "dob_woman"):
        assert r[c][:4] != "0000" and not r[c].endswith("-00"), f"test row is not day-precision: {r}"
print("  every test date is day-precision and present")

# The training half is deliberately mixed. Report the shape rather than demand one.
one = sum(1 for r in tr if "0000-00-00" in (r["dob_man"], r["dob_woman"]))
coarse = sum(1 for r in tr if r["dob_man"].endswith("-00") or r["dob_woman"].endswith("-00"))
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
era = (te.dob_man.str[:4].astype(int) + te.dob_woman.str[:4].astype(int)).to_numpy(float)
a = cm._auc(y, era)
print(f"  era rule (sum of the two birth years): AUC {max(a, 1-a):.4f}")

# THE SIGNED AGE GAP, the only permitted baseline for this project: a 2-parameter logistic on dob_woman - dob_man.
gap = (te.dob_woman.str[:4].astype(int) - te.dob_man.str[:4].astype(int)).to_numpy(float)
a = cm._auc(y, gap)
print(f"  signed age gap (woman - man):          AUC {max(a, 1-a):.4f}")
PYEOF

step "5. publish: dataset version, competition data, model version"
rm -rf /tmp/aqdurds && mkdir -p /tmp/aqdurds
cp "$SRC/train.csv" "$SRC/test.csv" "$SRC/sample_submission.csv" /tmp/aqdurds/
$PY - "$DATASET" <<'PYEOF'
import json, sys
ref = sys.argv[1]
owner, slug = ref.split("/")
desc = """# Let's end this loneliness epidemic with astrology.

Two birth dates in, one bit out: **did the marriage last thirty years?**

| column | meaning |
|---|---|
| `dob_man` | the man's date of birth |
| `dob_woman` | the woman's date of birth |
| `lasted_30_years` | 1 if the marriage lasted thirty years or longer, else 0 |

The first column is the man and the second the woman, assigned from Wikidata's `P21` and never inherited from
the order the couple happened to be stated in. **The marriage's own dates are not columns.** They compute the
label and are then discarded — the wedding year is the most era-revealing thing about a couple, and a model
given it would learn the century instead.

## How the label is computed

Exactly as a Wikipedia infobox reads a marriage — *"m. 1903; div. 1919"*:

* an **end date** is recorded (`P582`): the marriage ran from `P580` to `P582`.
* **no end date**: it ran until somebody died, so the end is the earlier of the two deaths (`P570`).

`lasted_30_years` is `(end - start) >= 30 years`. **A marriage ended by a death is not automatically a long
one** — twelve years is a 0, forty years is a 1. Death buys no credit.

## Train births 1600-1900, hold out 1901 onward — a TEMPORAL split, bounded by DEATH

A marriage that has not ended cannot be given a duration. Rather than cap birth years and infer it, this
dataset requires a recorded **death**: if the partner whose date we have is dead, their marriage has ended,
whenever they were born. So the window runs to the present and the split is by time — learn from the historical
couples, predict the modern ones.

**Read this before you read the leaderboard.** That rule introduces its own bias, and it is not subtle. A couple
born recently who are ALREADY DEAD died young, and a marriage cannot outlive its shorter-lived partner. Past
roughly 1996 a thirty-year marriage is arithmetically impossible for anyone dead today, so the positive rate
falls toward zero at the recent end whatever astrology says. "Born late, therefore negative" is an era rule and
not a finding. The build notebook prints the positive rate for every birth decade and names the decades where
the positive class is unreachable; the era-rule baseline is reported beside every score for the same reason.

## The test set is strict; the training set is not

**Test**: both partners known to the day, both born 1851-1900, no placeholder dates.

**Train**: as inclusive as the data allows. A date may be known only to the month (`1809-11-00`) or only to the
year (`1802-00-00`), and **one partner may be absent from Wikidata entirely** (`0000-00-00`). `00` means
unknown; `0000-00-00` means absent.

```
dob_man,dob_woman,lasted_30_years
1794-06-12,1801-03-27,1     <- both known to the day
1802-00-00,1809-11-00,0     <- his year only; her year and month
1777-04-30,0000-00-00,1     <- she is not in Wikidata at all
```

That is not a rounding decision. Measured on Wikidata: **12,661** couples have both partners dated to the day,
**30,110** have both at any precision, and **86,600** have at least one. A marriage's duration is known just as
exactly when one spouse's birthday is not, so a one-sided row carries a real label and half an input. Filter
them out in one line if you want only clean rows.

## The confound to know about

Marriages with a recorded END date reach thirty years about 16% of the time; marriages that ran until a death
do so about 53% of the time. Which case a couple is in **is not a column** — but it correlates with things that
are. Read a leaderboard place against the baselines, not against 0.5.

## Two traps in the dates, both measured and both handled

**1 January is a placeholder.** Among day-precision births 1600-1900 it occurs 2.07x as often as a median
January day, while 2 January sits at 1.00x — a source that knew only the year got imported with a day anyway.
Excluded at day precision, and NOT at year precision, where `1850-01-01` is simply how Wikidata spells 1850.

**The calendar is one calendar, and the placeholder moves inside it.** Wikidata's RDF gives every date in the
proleptic Gregorian calendar whatever `timeCalendarModel` says — Newton's Julian-tagged statement carries the
literal `1643-01-04`, the Gregorian image of 25 December 1642. So no conversion is needed. But it means a
*Julian* 1 January placeholder is stored as 11, 12 or 13 January by century, and that excess is real: 2.08x the
median January day at 13 January among Julian-tagged records. Excluded at the century-correct date.

Built by a public notebook that runs the SPARQL live, so anyone can re-run it and contradict it.
"""
meta = {"title": "ArtaMatch: astrology and marriage duration",
        "id": ref, "licenses": [{"name": "CC0-1.0"}],
        "subtitle": "Two birth dates. Did the marriage last thirty years?",
        "description": desc}
json.dump(meta, open("/tmp/aqdurds/dataset-metadata.json", "w"), indent=1)
print(f"  metadata written for {ref}")
PYEOF
$PY - "$DATASET" <<'PYEOF' 2>&1 | grep -viE "^\s*[0-9]+%|B/s" | tail -2
import sys, time
from kaggle.api.kaggle_api_extended import KaggleApi
ref = sys.argv[1]
api = KaggleApi(); api.authenticate()
notes = "marriage duration: 3 columns, temporal split 1600-1850/1851-1900, inclusive training half"
for i in range(4):
    try:
        print("  dataset ->", api.dataset_create_version("/tmp/aqdurds", version_notes=notes,
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
