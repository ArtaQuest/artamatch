#!/bin/bash
# bio_model.sh — judged marriages -> corpora -> charts -> the doctrine-only pair-rule fit on each target.
set -e
PY=~/.artamatch-venv/bin/python
K=~/Studio/artamatch/kaggle
DEV=~/.artamatch-dev
cd $K
echo "== corpora from the judgements =="
$PY -u bio_corpus.py
for T in quality_ht quality_toxic quality_happy; do
  [ -d $DEV/$T ] || continue
  echo "== charts for $T =="
  cd ~/Studio/artamatch/research/sidereal
  AQ_SRC=$DEV/$T AQ_OUT=$DEV/$T AQ_NO_PLACE=1 $PY -u kerykeion_phases.py | tail -1
  cd $K
  echo "== fit: $T =="
  AQ_D=$DEV/$T AQ_BANK=base AQ_READ=1 AQ_OUT_MODEL=$DEV/${T}_model.json AQ_OUT_Z=$DEV/${T}_z.npy \
    $PY -u v20_final.py 2>&1 | tail -14
done
echo "BIO-MODEL-DONE"
