#!/bin/zsh
# launch.sh — wait for the dataset build to land, then finalize, publish and deploy, in one unattended run.
#
# WHY ONE SCRIPT. The build takes hours and finishes at an hour nobody is watching. Everything after it is
# deterministic and every step has been proven against a fixture, so there is no reason for a person to type the
# next command. What must NOT happen is finalizing on the wrong data: this waits for the build PROCESS to exit,
# then demands the four CSVs and the scraper's own "checked:" lines in its log before touching anything.
#
# Usage: kaggle/launch.sh <build-pid> <build-log> [src-dir]
#   e.g. kaggle/launch.sh 61500 /tmp/aqdur/build12.log /tmp/aqdur
set -euo pipefail
PID="$1"; LOG="$2"; SRC="${3:-/tmp/aqdur}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=~/.artamatch-venv/bin/python
export KAGGLE_USERNAME=artafather
export KAGGLE_KEY="$($PY -c "import json;print(json.load(open('$HOME/.kaggle/kaggle.artafather.json'))['key'])")"

step() { printf '\n══ %s ══  %s\n' "$1" "$(date '+%H:%M:%S')"; }

step "waiting for the build (pid $PID) to exit"
while kill -0 "$PID" 2>/dev/null; do sleep 60; done
echo "  build process has exited"

step "the build must have WRITTEN and CHECKED its files, not merely exited"
for f in train.csv test.csv solution.csv sample_submission.csv; do
  [ -s "$SRC/$f" ] || { echo "  MISSING or empty $SRC/$f — the build did not finish; refusing to continue"; exit 1; }
done
grep -q "wrote train.csv" "$LOG" || { echo "  the log has no 'wrote train.csv' — refusing"; exit 1; }
grep -q "checked: every test date is day-precision" "$LOG" || { echo "  the log has no test-half check line — refusing"; exit 1; }
if grep -qE "Traceback|AssertionError" "$LOG"; then
  echo "  the log contains a Traceback/AssertionError — refusing to finalize on a build that raised"; exit 1
fi
echo "  train.csv $(wc -l < "$SRC/train.csv") lines · test.csv $(wc -l < "$SRC/test.csv") lines · log clean"

step "finalize: split checks, train, rank, score, publish dataset + competition + model, ship page, tournament"
"$REPO/kaggle/finalize.sh" "$SRC"

step "publish the build notebook (public, re-runnable proof of the dataset)"
(cd "$REPO/kaggle" && $PY publish_notebook.py 2>&1 | tail -3) || echo "  notebook publish failed — continuing; rerun publish_notebook.py by hand"

step "publish the benchmark task (a new version of artamatch-astrology)"
(cd "$REPO/kaggle/benchmark" && AQ_DO_CREATE=1 $PY create_recipe.py 2>&1 | tail -4) || echo "  benchmark push failed — continuing; rerun create_recipe.py by hand"

step "deploy the page: commit docs/ + sources and push main (GitHub Pages builds from docs/)"
cd "$REPO"
# The page gates ran inside finalize step 6; do not deploy a docs/ that did not pass them.
$PY web/verify_docs.py docs 2>&1 | tail -1 | grep -q "publishable" || { echo "  docs/ is not publishable — not deploying"; exit 1; }
git add docs kaggle web astro METHODS.md README.md 2>/dev/null || true
git commit -q -m "Ship: relationship-duration model, dataset, competition and page

Any relationship two people chose (marriage, unmarried or same-sex partnership,
business partnership, non-family significant person), older partner first,
births 1600-1900 to train and 1901+ dead couples held out. The page headlines
the temporal held-out AUC against the era rule; the precision grid is retired.
Built and finalized unattended by kaggle/launch.sh from a build whose own
assertions passed." || echo "  nothing new to commit"
git push origin HEAD:main 2>&1 | tail -2
echo "  pushed — GitHub Pages will publish docs/ from main"

step "done"
