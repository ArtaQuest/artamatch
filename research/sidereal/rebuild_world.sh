#!/bin/zsh
# Rebuild the whole measurement from a fresh dataset, into DURABLE storage.
# /private/tmp is wiped by macOS without warning and took the previous run's dataset, features and every built
# member with it — so every path here lives under ~/.artamatch-dev.
set -u
D=~/.artamatch-dev
SRC=$D/aq9c; FEAT=$D/aq9feat; SUB=$D/aq9sub
PY=~/.artamatch-venv/bin/python
K=~/Studio/artamatch/kaggle
cd ~/Studio/artamatch/research/sidereal || exit 1
mkdir -p $FEAT $SUB
say() { print -r -- "[$(date +%H:%M:%S)] $*" }

# 1. the P21 sex table — AQ_ORDER=sex cannot order the pair without it
say "waiting for the sex lookup to finish"
while pgrep -qf sex_lookup.py; do sleep 30; done
[[ -s $SRC/_sex.csv ]] || { say "sex table missing — stopping"; exit 1 }
say "sex table: $(wc -l < $SRC/_sex.csv) rows"

# 2. the dataset. The slice cache survived, so this replays from disk rather than re-querying Wikidata.
if [[ ! -s $SRC/train.csv ]]; then
  say "assembling the dataset from the cached slices"
  ( cd $SRC && AQ_ORDER=sex AQ_DATES_ONLY=1 AQ_MIN_YEARS=30 AQ_SEX_CSV=$SRC/_sex.csv \
      $PY -u ~/Studio/artamatch/kaggle/scrape_duration.py > $SRC/assemble.log 2>&1 ) \
    || { say "assembly FAILED"; tail -8 $SRC/assemble.log; exit 1 }
fi
say "dataset: $(( $(wc -l < $SRC/train.csv) - 1 )) train rows, $(( $(wc -l < $SRC/test.csv) - 1 )) test rows"

# 3. phases — the long leg
if [[ ! -s $FEAT/phases.npz ]]; then
  say "building phases (sidereal longitudes for every date)"
  AQ_SRC=$SRC AQ_OUT=$FEAT AQ_NO_PLACE=1 $PY -u kerykeion_phases.py > $FEAT/phases.log 2>&1 \
    || { say "phases FAILED"; tail -8 $FEAT/phases.log; exit 1 }
fi
say "phases: $(du -h $FEAT/phases.npz | cut -f1)"

# 4. the per-family members and the control (local, CPU — the GPU run is the giant ensemble on Kaggle)
for m in world_members_iv world2_members_iv world3_members_iv; do
  out=$SUB/${m%%_members_iv}_members.npz
  [[ -s $out ]] && { say "$m already built"; continue }
  say "building $m"
  AQ_SRC=$SRC AQ_OUT=$SUB AQ_PHASES=$FEAT/phases.npz $PY -W error::RuntimeWarning -u $m.py > $SUB/${m%%_members_iv}.log 2>&1 \
    || { say "$m FAILED"; tail -6 $SUB/${m%%_members_iv}.log }
done
say "running the control"
AQ_SRC=$SRC AQ_OUT=$SUB AQ_PHASES=$FEAT/phases.npz $PY -u world_control_iv.py > $SUB/control_final.txt 2>&1
say "control written to $SUB/control_final.txt"

# 5. package what the Kaggle GPU kernel needs
say "packaging the Kaggle payload"
P=$D/kagglepkg; rm -rf $P; mkdir -p $P
cp $SRC/train.csv $SRC/test.csv $P/
cp $FEAT/phases.npz $P/
say "payload: $(du -sh $P | cut -f1) — ready to upload as a Kaggle dataset"
say "ALL DONE"
