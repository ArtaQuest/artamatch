#!/bin/zsh
# finalize.sh — everything that follows the scrape, in the only order it can run.
#
# Each step depends on the one before it: the trainer needs the split, the ranking needs the trainer's saved
# matrices, the publish steps need the model, the tournament needs the ranking's per-tradition predictions. So it
# is one script rather than five commands typed in an order that will eventually be typed wrong. Every step
# refuses to continue if the one before it did not produce what it promised.
#
# Usage: kaggle/finalize.sh /tmp/aqclean          # the directory the scrape wrote train.csv / test.csv into
set -euo pipefail
SRC="${1:-/tmp/aqclean}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=~/.artamatch-venv/bin/python
MODEL=/tmp/aqcleanmodel
COMP=/tmp/aqcompclean
export KAGGLE_USERNAME=artafather
export KAGGLE_KEY="$($PY -c "import json;print(json.load(open('$HOME/.kaggle/kaggle.artafather.json'))['key'])")"

step() { printf '\n══ %s ══\n' "$1"; }
need() { [ -e "$1" ] || { echo "  MISSING $1 — the previous step did not produce it; stopping"; exit 1; }; }

step "0. the split exists and its boundary is what it claims"
need "$SRC/train.csv"; need "$SRC/test.csv"; need "$SRC/solution.csv"
$PY - "$SRC" <<'PY'
import csv, sys
src=sys.argv[1]
def later(r): return max(r["dob_man"][:4], r["dob_woman"][:4])
tr=[later(r) for r in csv.DictReader(open(f"{src}/train.csv"))]
te=[later(r) for r in csv.DictReader(open(f"{src}/test.csv"))]
print(f"  train {len(tr):,} rows, later birth {min(tr)}-{max(tr)}")
print(f"  test  {len(te):,} rows, later birth {min(te)}-{max(te)}")
assert min(te) >= "1928", "held-out couples must all postdate the cut"
PY

step "1. the competition test set: day-precision couples only, one row each"
rm -rf "$COMP"; $PY "$REPO/kaggle/build_dayday_test.py" "$SRC" "$COMP" | tail -6
cp "$SRC/train.csv" "$COMP/train.csv"

step "2. train the stack (19 traditions, ~45 min)"
rm -rf "$MODEL"
AQ_TRAIN="$SRC/train.csv" AQ_TEST="$SRC/test.csv" AQ_OUT="$MODEL" $PY "$REPO/kaggle/train_on_csv.py" 2>&1 \
  | grep -E "blocks ·|BASELINE|STACK|exported|wrote submission|done in|Traceback|core kept" || true
need "$MODEL/model.json"; need "$MODEL/oof_base.npy"; need "$MODEL/test_base.npy"

step "3. every tradition alone, ranked on the held-out set"
AQ_MODEL="$MODEL" AQ_TEST="$SRC/test.csv" AQ_SOL="$COMP/solution.csv" $PY "$REPO/kaggle/rank_traditions.py"
need "$MODEL/tradition_ranking.json"

step "4. the ensemble's own held-out score, for the record"
$PY - "$MODEL" "$COMP" <<'PY'
import sys, pandas as pd
sys.path.insert(0, "/Users/arash/Studio/artamatch/kaggle")
import competition_metric as cm
M, C = sys.argv[1], sys.argv[2]
sol = pd.read_csv(f"{C}/solution.csv"); sub = pd.read_csv(f"{M}/submission.csv")
m = sol.merge(sub.rename(columns={"parents_together": "p"}), on="id")
print(f"  ensemble on {len(m):,} day-precision held-out couples: AUC {cm._auc(m.parents_together, m.p):.4f}")
for side in ("Public", "Private"):
    s = m[m.Usage == side]; print(f"    {side:<8} {cm._auc(s.parents_together, s.p):.4f}  ({len(s):,})")
PY

step "5. publish: dataset version, competition data + solution, model version, ephemeris already live"
rm -rf /tmp/aqds10 && mkdir -p /tmp/aqds10 && cp "$SRC/train.csv" /tmp/aqds10/ && cp /tmp/aqds9/dataset-metadata.json /tmp/aqds10/
$PY - <<'PY'
import json
m=json.load(open('/tmp/aqds10/dataset-metadata.json'))
m["description"]=m["description"].replace("later birth falls\non or before 1928-10-07","later birth falls\non or before the cut").replace("1800-1950","1700-1950").replace("born between 1800","born between 1700")
m["description"]=("# Let's end this loneliness epidemic with astrology.\n\nTHIS VERSION: parents born 1700-1950 (the floor moved back a century, +11% couples), TEMPORAL split, "
  "and the held-out half DENOISED — records that contradict themselves (two birth years, two sexes, a parental role that disagrees with P21, "
  "a deprecated birth date) are kept in TRAINING but never scored. Numerology joins the eighteen astrological traditions.\n\n") + m["description"].split("\n\n",1)[1]
json.dump(m,open('/tmp/aqds10/dataset-metadata.json','w'),indent=1); print("  metadata updated")
PY
$PY - <<'PY' 2>&1 | grep -viE "^\s*[0-9]+%|B/s" | tail -1
import time
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi(); api.authenticate()
for i in range(4):
    try: print("  dataset ->", api.dataset_create_version("/tmp/aqds10", version_notes="1700-1950, temporal split, denoised held-out half, numerology", quiet=True, dir_mode="skip")); break
    except Exception as e: print(f"  attempt {i+1}: {str(e)[:80]}"); time.sleep(4*(i+1))
PY
AQ_COMP=artamatch-astrology $PY "$REPO/kaggle/publish_competition.py" "$COMP" 2>&1 | grep -E "uploaded|databundle|500|Error" | tail -4 || true
(cd "$REPO/kaggle" && AQ_MODEL_DIR="$MODEL" $PY publish_model.py 2>&1 | grep -viE "^\s*[0-9]+%|B/s" | tail -2) || true

step "6. the page: inject, ship, verify"
(cd "$REPO" && AQ_MODEL="$MODEL" AQ_TRAIN="$SRC/train.csv" $PY web/inject_benchmark.py && $PY web/ship.py 2>&1 | grep -E "end to end|wrote docs" && $PY web/verify_docs.py docs 2>&1 | tail -1 && $PY web/test_runner.py docs 2>&1 | tail -1)

step "7. the tournament: artafather's baselines (5/day; the ledger resumes tomorrow)"
AQ_MODEL="$MODEL" AQ_TEST="$SRC/test.csv" AQ_COMP_TEST="$COMP/test.csv" $PY "$REPO/kaggle/tournament.py" baselines artafather

step "done — the remaining baselines and the ensemble turns run daily via tournament.py"
