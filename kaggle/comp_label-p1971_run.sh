#!/bin/zsh
# comp_label-p1971_run.sh — the ONE real run for the label-p1971 entry. Builds the purified corpus
# (p1971.csv if it exists at run time, else the lens's depth-only fallback — MODE is printed),
# runs the one-chart baselines on those rows (with within-era), then the nested fit with the
# standing-best knobs (lean bank XY, k=1, ortho, K=32 fixed, 5 outer folds, ablate estimate).
# Touches only ~/.artamatch-dev/comp_label-p1971/ and comp_* files. Never edits a shared file.
set -e
cd ~/Studio/artamatch/kaggle
PY=~/.artamatch-venv/bin/python
export AQ_DIR=${AQ_DIR:-~/.artamatch-dev/comp_label-p1971}
export AQ_SRC=${AQ_SRC:-~/.artamatch-dev/tilldeath_wt3}
export AQ_OUT=$AQ_DIR
export AQ_MIN_SITELINKS=${AQ_MIN_SITELINKS:-5}
echo "=== [1/3] corpus (label purification)"; $PY comp_label-p1971_corpus.py
echo "=== [2/3] one-chart baselines on the SAME rows/labels"; $PY comp_label-p1971_baselines.py
echo "=== [3/3] nested fit, standing-best knobs, purified labels"
AQ_KMAX=${AQ_KMAX:-32} AQ_NOUTER=${AQ_NOUTER:-5} AQ_NO_INNER=${AQ_NO_INNER:-1} AQ_ABLATE=1 \
AQ_ORTHO=1 AQ_ONLY_FAM=XY AQ_ONLY_HARM=1 $PY comp_label-p1971.py
echo "=== SUMMARY (label-p1971)"
$PY - <<PYEOF
import json, glob, os
D = os.path.expanduser("$AQ_DIR")
c = json.load(open(f"{D}/comp_label-p1971_corpus_report.json"))
print("MODE:", c["mode"], "| rows", c["n_kept"], "of", c["n_source"], "| pos_rate", c["pos_rate"], "| counts", c["counts"])
print("STANDING-MODEL OOF ON THESE ROWS:", c["standing_model_diagnostic"])
b = json.load(open(f"{D}/comp_label-p1971_baselines.json"))
print("BASELINES:", {k: round(v, 4) for k, v in b.items() if k != "within_era"}, "| within_era", {k: round(v, 4) for k, v in b["within_era"].items()})
for f in sorted(glob.glob(f"{D}/ablate_comp_label-p1971_*.json")):
    a = json.load(open(f))
    print(f"NESTED {a['nested_auc']:.4f}  WITHIN-ERA {a['within_era_auc']:.4f}  [{a['tag']}]  per-fold {[x['fold_auc'] for x in a['per_fold']]}")
    print(f"PAIR LIFT over best one-chart: {a['nested_auc'] - max(b['him_only'], b['her_only']):+.4f} pooled · within-era {a['within_era_auc'] - max(b['within_era']['him only (complete solo algebra)'], b['within_era']['her only (complete solo algebra)']):+.4f}")
PYEOF
