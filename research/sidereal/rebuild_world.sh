#!/bin/zsh
# Rebuild the whole world-systems measurement from a fresh dataset, into DURABLE storage.
# /private/tmp is wiped by macOS without warning and took the previous run's dataset, features and every
# built member with it — so every path here lives under ~/.artamatch-dev.
set -u
D=~/.artamatch-dev
SRC=$D/aq9c; FEAT=$D/aq9feat; SUB=$D/aq9sub
PY=~/.artamatch-venv/bin/python
cd ~/Studio/artamatch/research/sidereal || exit 1
mkdir -p $FEAT $SUB
say() { print -r -- "[$(date +%H:%M:%S)] $*" }

say "waiting for the scrape to produce train.csv + test.csv"
while [[ ! -s $SRC/train.csv || ! -s $SRC/test.csv ]]; do sleep 30; done
say "dataset: $(wc -l < $SRC/train.csv) train rows, $(wc -l < $SRC/test.csv) test rows"

if [[ ! -s $FEAT/phases.npz ]]; then
  say "building phases (the long leg — sidereal longitudes for every date)"
  AQ_SRC=$SRC AQ_OUT=$FEAT AQ_NO_PLACE=1 $PY -u kerykeion_phases.py > $FEAT/phases.log 2>&1 || { say "phases FAILED"; tail -5 $FEAT/phases.log; exit 1; }
fi
say "phases ready: $(du -h $FEAT/phases.npz | cut -f1)"

for m in world_members_iv world2_members_iv world3_members_iv; do
  out=$SUB/${m%%_members_iv}_members.npz
  [[ -s $out ]] && { say "$m already built"; continue }
  say "building $m"
  AQ_SRC=$SRC AQ_OUT=$SUB AQ_PHASES=$FEAT/phases.npz $PY -W error::RuntimeWarning -u $m.py > $SUB/${m%%_members_iv}.log 2>&1 \
    || { say "$m FAILED"; tail -5 $SUB/${m%%_members_iv}.log }
done

say "running the control"
AQ_SRC=$SRC AQ_OUT=$SUB AQ_PHASES=$FEAT/phases.npz $PY -u world_control_iv.py > $SUB/control_final.txt 2>&1
say "done — results in $SUB/control_final.txt"
head -20 $SUB/control_final.txt
