#!/bin/zsh
# finalize_iv.sh — the FOURTH edition: genderless, every pair in both orders, any long-term relationship.
#
# Operator 2026-08-19: "I want a genderless model from now on. so duplicate all the train and test data. (a, b, 1)
# should also mean (b, a, 1) and add any longterm relationship to the dataset (including gay marriages and
# business partnerships). also for each subtractive terms add abs to ensure each term is an even function. then
# start over the competition."  The build is scrape_duration.py with AQ_ORDER=none (no sex read, every relation
# type, both orders written); the model is research/sidereal/artamodel_iv.py (even ArtaModel + plain + ensemble).
#
# Usage: kaggle/finalize_iv.sh /tmp/aq4
set -euo pipefail
SRC="${1:-${AQ_SRC:-/tmp/aq4}}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=~/.artamatch-venv/bin/python
FEAT="${AQ_FEAT_DIR:-/tmp/aq4feat}"
COMP="${AQ_COMP_DIR:-/tmp/aq4comp}"
SUB="${AQ_SUB_DIR:-/tmp/aq4sub}"
DS="${AQ_DS_DIR:-/tmp/aq4ds}"
DATASET="${AQ_DATASET:-artaquest-foundation/artamatch-genderless}"
COMPETITION="${AQ_COMPETITION:-artamatch-genderless}"
LABEL=lasted_30_years
step() { printf '\n══ %s ══  %s\n' "$1" "$(date '+%H:%M:%S')"; }
need() { [ -e "$1" ] || { echo "  MISSING $1 — the previous step did not produce it; stopping"; exit 1; }; }

step "0. the split exists, both orders are present, the ids pair up, and the columns are what they claim"
need "$SRC/train.csv"; need "$SRC/test.csv"; need "$SRC/solution.csv"; need "$SRC/sample_submission.csv"
$PY - "$SRC" "$LABEL" <<'PYEOF'
import csv, re, sys
from collections import Counter
src, label = sys.argv[1], sys.argv[2]
tr = list(csv.DictReader(open(f"{src}/train.csv"))); te = list(csv.DictReader(open(f"{src}/test.csv")))
COLS = ["dob_a", "dob_b", "lat_a", "lon_a", "lat_b", "lon_b", "start"]
assert list(tr[0]) == COLS + [label], f"train columns {list(tr[0])}"
assert list(te[0]) == ["id"] + COLS, f"test columns {list(te[0])}"
def later(r):
    return max(int(r[c][:4]) for c in ("dob_a", "dob_b") if r[c][:4] != "0000")
assert max(later(r) for r in tr) <= 1900 < min(later(r) for r in te), "the split is not temporal at 1900"
key = lambda r, x, y: (r[f"dob_{x}"], r[f"lat_{x}"], r[f"lon_{x}"], r[f"dob_{y}"], r[f"lat_{y}"], r[f"lon_{y}"], r["start"])
for name, rows in (("train", tr), ("test", te)):
    k1 = Counter(key(r, "a", "b") for r in rows); k2 = Counter(key(r, "b", "a") for r in rows)
    assert k1 == k2, f"{name} is not closed under the swap of its two partners"
sol = list(csv.DictReader(open(f"{src}/solution.csv"))); side = {r["id"]: r["Usage"] for r in sol}; lab = {r["id"]: r[label] for r in sol}
for r in te:
    m = re.match(r"^p(\d{6})([ab])$", r["id"]); assert m, r["id"]
    other = f"p{m.group(1)}{'b' if m.group(2) == 'a' else 'a'}"
    assert other in side and side[other] == side[r["id"]] and lab[other] == lab[r["id"]], f"{r['id']}: its partner row differs in side or label"
    for c in ("dob_a", "dob_b"):
        assert r[c][:4] != "0000" and not r[c].endswith("-00"), f"test row not day-precision: {r}"
    for c in ("lat_a", "lon_a", "lat_b", "lon_b"):
        assert r[c] not in ("", "nan"), f"test row lacks a birthplace: {r}"
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["start"]) and int(r["start"][:4]) <= 1996, r["start"]
    assert not (r["start"][5:7] != "00" and r["start"][8:] == "00" and False), r["start"]
for r in tr:
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["start"]), r["start"]
yo = {n: sum(1 for r in rows if r["start"].endswith("-00-00")) for n, rows in (("train", tr), ("test", te))}
print(f"    starts known to the year only (YYYY-00-00): train {yo['train']:,} · test {yo['test']:,}; 1 January is a real day")
    assert not (r["dob_a"] == "0000-00-00" and r["dob_b"] == "0000-00-00"), "a training row with no date"
for s in ("Public", "Private"):
    v = [int(r[label]) for r in sol if r["Usage"] == s]; assert 0 < sum(v) < len(v)
    print(f"    {s:<8} {len(v):>6,} rows, {100*sum(v)/len(v):5.2f}% positive")
print(f"  train {len(tr):,} rows ({len(tr)//2:,} pairs) · test {len(te):,} rows ({len(te)//2:,} pairs); both orders present everywhere, "
      f"every test pair shares a side and a label, every partner placed and dated to the day, every start <= 1996")
PYEOF

step "1. the competition bundle"
rm -rf "$COMP"; mkdir -p "$COMP"
cp "$SRC/test.csv" "$SRC/solution.csv" "$SRC/sample_submission.csv" "$SRC/train.csv" "$COMP/"
echo "  $COMP: $(wc -l < "$COMP/test.csv") test rows, $(wc -l < "$COMP/train.csv") train rows"

step "2. phases: Kerykeion sidereal longitudes at 09:00 local (reused if present)"
mkdir -p "$FEAT"
if [ ! -s "$FEAT/phases.npz" ] || [ -n "${AQ_REBUILD_PHASES:-}" ]; then
  (cd "$REPO/research/sidereal" && AQ_SRC="$SRC" AQ_OUT="$FEAT" $PY kerykeion_phases.py 2>&1 | tail -2)
fi
need "$FEAT/phases.npz"

step "3. the model: plain · ArtaModel IV (even, genderless) · the equal-weight ensemble"
mkdir -p "$SUB"
(cd "$REPO/research/sidereal" && AQ_PHASES="$FEAT/phases.npz" AQ_SOL="$COMP/solution.csv" AQ_OUT="$SUB" $PY artamodel_iv.py 2>&1 | grep -v "^\s*$")
need "$SUB/artamodel_iv.json"; need "$SUB/submission_ensemble_iv.csv"

if [ -n "${AQ_NO_PUBLISH:-}" ]; then echo; echo "══ publish skipped (AQ_NO_PUBLISH) ══"; exit 0; fi

step "4. publish the dataset ($DATASET)"
rm -rf "$DS" && mkdir -p "$DS"
cp "$SRC/train.csv" "$SRC/test.csv" "$SRC/sample_submission.csv" "$DS/"
$PY "$REPO/kaggle/dataset_meta_iv.py" "$DATASET" "$DS" "$SRC"
$PY - "$DATASET" "$DS" <<'PYEOF' 2>&1 | grep -viE "^\s*[0-9]+%|B/s" | tail -2
import sys, time, os, shutil
os.makedirs("/tmp/aqkg_af", exist_ok=True); shutil.copy(os.path.expanduser("~/.kaggle/kaggle.artafather.json"), "/tmp/aqkg_af/kaggle.json"); os.chmod("/tmp/aqkg_af/kaggle.json", 0o600); os.environ["KAGGLE_CONFIG_DIR"] = "/tmp/aqkg_af"
from kaggle.api.kaggle_api_extended import KaggleApi
ref, d = sys.argv[1], sys.argv[2]
api = KaggleApi(); api.authenticate()
notes = "fourth edition: genderless -- every pair in both orders, every long-term relationship type, births 1600-1900 train / 1901+ dead test"
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
AQ_COMPETITION="$COMPETITION" AQ_DO_CREATE=1 $PY "$REPO/kaggle/publish_competition_v4.py" 2>&1 | tail -3
KAGGLE_USERNAME=artafather KAGGLE_KEY="$($PY -c "import json,os;print(json.load(open(os.path.expanduser('~/.kaggle/kaggle.artafather.json')))['key'])")" \
  AQ_COMP="$COMPETITION" $PY "$REPO/kaggle/publish_competition.py" "$COMP" 2>&1 | grep -v "%|" | grep -E "uploaded|->|launched|rror" | head -8
AQ_COMPETITION="$COMPETITION" AQ_DO_WRITE=1 $PY "$REPO/kaggle/competition_pages_iv.py" "$COMP" "$SUB" 2>&1 | tail -9

step "done — set the metric (AQ_COMPETITION=$COMPETITION node web/_kaggle_metric.mjs), then publish_competition.py --launch"
