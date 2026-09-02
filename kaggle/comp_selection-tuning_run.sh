#!/bin/bash
# comp_selection-tuning_run.sh — the ONE real run for the "selection-tuning" entry.
# Three arms, serial, same corpus rows/labels as the standing best, standing-best knobs
# (ortho, family XY, K cap 32, 5 outer folds, K fixed = no inner CV, ablate estimate):
#   A  lean bank (k=1, 169 candidates), plain argmax pick, multiplicity-corrected stop grid
#   B  all-XY-harmonics bank (13 harmonics, 2,197 candidates), same pick + grid
#   C  lean bank, STABILITY pick (argmax of the min score over 5 inner subsamples) + grid
# alpha=0 on every grid = never stop = the standing procedure at this budget (the control).
# Touches only comp_* files and comp_selection-tuning_* outputs in $AQ_DIR. No shared file is edited.
set -e
cd ~/Studio/artamatch/kaggle
PY=~/.artamatch-venv/bin/python
export AQ_DIR=${AQ_DIR:-~/.artamatch-dev/tilldeath_wt3}
export AQ_KMAX=${AQ_KMAX:-32} AQ_NOUTER=${AQ_NOUTER:-5} AQ_NO_INNER=${AQ_NO_INNER:-1} AQ_ABLATE=1
export AQ_ORTHO=1 AQ_ONLY_FAM=XY
export AQ_ZSTOP=${AQ_ZSTOP:-0,1,0.05,0.001}
echo "=== [A/3] lean bank (169), argmax pick, stop grid $AQ_ZSTOP";      AQ_ONLY_HARM=1 $PY comp_selection-tuning.py
echo "=== [B/3] all XY harmonics (2,197), argmax pick, stop grid";       $PY comp_selection-tuning.py
echo "=== [C/3] lean bank (169), STABILITY pick (5 subsamples), stop grid"; AQ_ONLY_HARM=1 AQ_STAB=1 $PY comp_selection-tuning.py
echo "=== SUMMARY (selection-tuning)"
$PY - <<PYEOF
import json, glob, os
D = os.path.expanduser("$AQ_DIR"); K = "$AQ_KMAX"; O = "$AQ_NOUTER"
for f in sorted(glob.glob(f"{D}/ablate_comp_selection-tuning_k{K}_o{O}_*_zgrid.json")):
    a = json.load(open(f)); print("ARM", a["tag"], "| bank", a["n_phasors"], "| stab", a["stab"])
    for al, g in a["grid"].items():
        print(f"  alpha {al:>6}  NESTED {g['nested_auc']:.4f}  WITHIN-ERA {g['within_era_auc']:.4f}  phasors/fold {g['phasors_per_fold']} mean {g['mean_phasors']}  per-fold {g['per_fold_auc']}")
    for i, pf in enumerate(a["per_fold"]):
        zt = pf["ztrace"]; print(f"  fold {i} z-trace (step,z,cal,p_free): " + " ".join(f"{s}:{z:.0f}" for s, z, c, pf_ in zt))
PYEOF
