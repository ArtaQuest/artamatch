#!/bin/bash
# finalize_quality.sh — the whole binary marriage-quality chain, in dependency order.
#
# Every step is idempotent and every number in the almanac comes from this run, so the published
# figures cannot drift from the labels. Order matters: the consistency check gates the corpus, and the
# corpus rebuilds the sidereal charts it invalidates.
set -euo pipefail
V=~/.artamatch-venv/bin/python
D=~/.artamatch-dev
cd "$(dirname "$0")"
L=$D/FINAL.log; : > "$L"

say() { printf '\n########## %s\n' "$1" | tee -a "$L"; }

say "1. JUDGE CONSISTENCY — is any judge out of step with its neighbours?"
$V bio_consistency.py 2>&1 | tail -12 | tee -a "$L"

say "2. EVIDENCE — does every verdict rest on words in its own description?"
$V bio_verify2.py --flag 2>&1 | tee -a "$L"

say "3. CORPUS — filters, label balance, and the charts it rebuilds"
$V bio_corpus2.py 2>&1 | tee -a "$L"

say "4. DELIVERABLE CSV"
$V bio_deliver2.py 2>&1 | tee -a "$L"

say "5. BASELINES"
$V quality_benchmark.py quality_good quality_good_narr 2>&1 | tee -a "$L"

for c in quality_good quality_good_narr; do
  say "6. POOLED DOCTRINE FIT — $c"
  $V quality_fit.py $D/$c $D/${c}_final.json 2>&1 | tail -20 | tee -a "$L"
done

say "7. ERA CONTROL + SELECTION STABILITY"
AQ_MODEL=$D/quality_good_final.json $V quality_stability.py $D/quality_good 2>&1 | tail -12 | tee -a "$L"

say "8. INCREMENTAL OVER ERA — the decisive test"
$V quality_incremental.py $D/quality_good 2>&1 | tail -16 | tee -a "$L"

say "9. EVERY TRADITION, SCORED AGAINST ERA"
$V quality_by_tradition.py $D/quality_good 2>&1 | tee -a "$L"

say "10. WINDOW PROBE — can it order dates inside +/-12 years?"
$V quality_window_probe.py $D/quality_good $D/quality_good_final.json 80 2>&1 | tail -10 | tee -a "$L"

printf '\nfull log: %s\n' "$L"
