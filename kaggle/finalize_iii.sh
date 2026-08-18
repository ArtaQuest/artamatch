#!/bin/zsh
# finalize_iii.sh — the THIRD edition: birthplaces, 09:00 local, sidereal features (PyJHora + iztro).
#
# Why a separate chain. finalize.sh's model step trains the tropical nineteen-tradition stack, and the operator's
# instruction for this edition is "only focus on sidereal models". So the model here is research/sidereal:
# build_sidereal.py (features) and rank_sidereal.py (every family alone, a pre-registered pool as the entry).
# Everything else -- the split checks, the dataset publish, the competition upload, the pages -- follows the
# same discipline as the earlier chains, on the eight-column files.
#
# Usage: kaggle/finalize_iii.sh /tmp/aq3
set -euo pipefail
SRC="${1:-${AQ_SRC:-/tmp/aq3}}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=~/.artamatch-venv/bin/python
FEAT="${AQ_FEAT_DIR:-/tmp/aq3feat}"
COMP="${AQ_COMP_DIR:-/tmp/aq3comp}"
DS="${AQ_DS_DIR:-/tmp/aq3ds}"
DATASET="${AQ_DATASET:-artaquest-foundation/artamatch-sidereal}"
COMPETITION="${AQ_COMPETITION:-artamatch-sidereal}"
LABEL=lasted_30_years
step() { printf '\n══ %s ══  %s\n' "$1" "$(date '+%H:%M:%S')"; }
need() { [ -e "$1" ] || { echo "  MISSING $1 — the previous step did not produce it; stopping"; exit 1; }; }

step "0. the split exists, its boundary and its columns are what they claim"
need "$SRC/train.csv"; need "$SRC/test.csv"; need "$SRC/solution.csv"; need "$SRC/sample_submission.csv"
$PY - "$SRC" "$LABEL" <<'PYEOF'
import csv, re, sys
src, label = sys.argv[1], sys.argv[2]
tr = list(csv.DictReader(open(f"{src}/train.csv"))); te = list(csv.DictReader(open(f"{src}/test.csv")))
COLS = ["dob_dad", "dob_mom", "lat_dad", "lon_dad", "lat_mom", "lon_mom", "start"]
assert list(tr[0]) == COLS + [label], f"train columns {list(tr[0])}"
assert list(te[0]) == ["id"] + COLS, f"test columns {list(te[0])}"
def later(r):
    ys = [int(r[c][:4]) for c in ("dob_dad", "dob_mom") if r[c][:4] != "0000"]; return max(ys)
assert max(later(r) for r in tr) <= 1900 < min(later(r) for r in te), "the split is not temporal at 1900"
for r in te:
    for c in ("dob_dad", "dob_mom"):
        assert r[c][:4] != "0000" and not r[c].endswith("-00"), f"test row not day-precision: {r}"
    for c in ("lat_dad", "lon_dad", "lat_mom", "lon_mom"):
        assert r[c] not in ("", "nan"), f"test row lacks a birthplace: {r}"
    assert -90 <= float(r["lat_dad"]) <= 90 and -180 <= float(r["lon_dad"]) <= 180
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["start"]) and int(r["start"][:4]) <= 1996, r["start"]
for r in tr:
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["start"]), r["start"]
    assert not (r["dob_dad"] == "0000-00-00" and r["dob_mom"] == "0000-00-00"), "a training row with no date"
sol = list(csv.DictReader(open(f"{src}/solution.csv")))
for side in ("Public", "Private"):
    s = [int(r[label]) for r in sol if r["Usage"] == side]
    assert 0 < sum(s) < len(s); print(f"    {side:<8} {len(s):>6,} rows, {100*sum(s)/len(s):5.2f}% positive")
both = sum(1 for r in tr if r["lat_dad"] not in ("", "nan") and r["lat_mom"] not in ("", "nan"))
print(f"  train {len(tr):,} (both places known in {both:,}) · test {len(te):,}, every partner placed and dated to the day, "
      f"every start <= 1996")
PYEOF

step "1. the competition bundle"
rm -rf "$COMP"; mkdir -p "$COMP"
cp "$SRC/test.csv" "$SRC/solution.csv" "$SRC/sample_submission.csv" "$SRC/train.csv" "$COMP/"
echo "  $COMP: $(wc -l < "$COMP/test.csv") test rows, $(wc -l < "$COMP/train.csv") train rows"

step "2. sidereal features: PyJHora + iztro at 09:00 local (~10-15 min)"
rm -rf "$FEAT"; mkdir -p "$FEAT"
(cd "$REPO/research/sidereal" && AQ_SRC="$SRC" AQ_OUT="$FEAT" $PY build_sidereal.py 2>&1 | grep -v "added to system path")
need "$FEAT/sidereal.npz"

step "3. every sidereal family alone, the single features, and the pre-registered pool"
(cd "$REPO/research/sidereal" && AQ_FEAT="$FEAT/sidereal.npz" AQ_SOL="$COMP/solution.csv" AQ_OUT="$FEAT" \
  $PY rank_sidereal.py 2>&1 | grep -v "added to system path")
need "$FEAT/sidereal_ranking.json"; need "$FEAT/submission.csv"

if [ -n "${AQ_NO_PUBLISH:-}" ]; then echo; echo "══ publish skipped (AQ_NO_PUBLISH) ══"; exit 0; fi

step "4. publish the dataset ($DATASET)"
rm -rf "$DS" && mkdir -p "$DS"
cp "$SRC/train.csv" "$SRC/test.csv" "$SRC/sample_submission.csv" "$DS/"
$PY "$REPO/kaggle/dataset_meta_iii.py" "$DATASET" "$DS" "$SRC"
$PY - "$DATASET" "$DS" <<'PYEOF' 2>&1 | grep -viE "^\s*[0-9]+%|B/s" | tail -2
import sys, time
from kaggle.api.kaggle_api_extended import KaggleApi
ref, d = sys.argv[1], sys.argv[2]
api = KaggleApi(); api.authenticate()
notes = "third edition: birthplaces (lat/lon) and the start date; charts to be cast at 09:00 local; births 1600-1900 train / 1901+ dead test"
for i in range(4):
    try:
        try:
            print("  dataset ->", api.dataset_create_new(d, public=True, quiet=True, dir_mode="skip"))
        except Exception as e0:
            if "already exists" not in str(e0).lower() and "409" not in str(e0):
                raise
            print("  dataset ->", api.dataset_create_version(d, version_notes=notes, quiet=True, dir_mode="skip"))
        break
    except Exception as e:
        print(f"  attempt {i+1}: {str(e)[:100]}"); time.sleep(4 * (i + 1))
PYEOF

step "5. the competition ($COMPETITION): create if needed, upload data + answer key, write pages"
AQ_COMPETITION="$COMPETITION" AQ_DO_CREATE=1 $PY "$REPO/kaggle/publish_competition_v3.py" 2>&1 | tail -3
KAGGLE_USERNAME=artafather KAGGLE_KEY="$($PY -c "import json,os;print(json.load(open(os.path.expanduser('~/.kaggle/kaggle.artafather.json')))['key'])")" \
  AQ_COMP="$COMPETITION" $PY "$REPO/kaggle/publish_competition.py" "$COMP" 2>&1 | grep -v "%|" | grep -E "uploaded|->|launched" | head -8
AQ_COMPETITION="$COMPETITION" AQ_DO_WRITE=1 $PY "$REPO/kaggle/competition_pages_iii.py" "$COMP" "$FEAT" 2>&1 | tail -9

step "done — set the metric (web/_kaggle_metric.mjs), then publish_competition.py --launch"
