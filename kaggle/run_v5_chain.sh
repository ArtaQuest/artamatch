#!/bin/bash
# The finalisation chain, one shot: sweeps -> corpus v5 -> phases -> doctrine-only race -> one read.
set -e
PY=~/.artamatch-venv/bin/python
K=~/Studio/artamatch/kaggle
DEV=~/.artamatch-dev
cd $K
echo "== 1. multi-dob census on the verified harvest =="
AQ_MAR=$DEV/marriages2 $PY - << 'PYEOF'
import glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from build_remarriage import render, qid
d = pd.concat([pd.read_csv(f, dtype=str) for f in sorted(glob.glob(os.path.expanduser("~/.artamatch-dev/marriages2/d*.csv")))], ignore_index=True)
d["a"] = d.a.map(qid)
d["dob"] = [render(v, p) for v, p in zip(d.adob, d.aprec)]
g = d.groupby("a").dob.nunique()
md = sorted(g[g > 1].index)
np.save(os.path.expanduser("~/.artamatch-dev/_multi_dob_qids.npy"), np.array(md))
print(f"multi-dob persons on the verified harvest: {len(md):,}")
PYEOF
echo "== 2. truthy sweep (checkpointed; resumes) =="
$PY -u fetch_truthy_dobs.py
echo "== 3. jan-1 census + wikipedia verification =="
AQ_MAR=$DEV/marriages2 $PY - << 'PYEOF'
import glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from build_remarriage import qid
d = pd.concat([pd.read_csv(f, dtype=str, usecols=["a", "adob", "aprec"]) for f in sorted(glob.glob(os.path.expanduser("~/.artamatch-dev/marriages2/d*.csv")))], ignore_index=True)
d["a"] = d.a.map(qid)
p = pd.to_numeric(d.aprec, errors="coerce")
md = d.adob.astype(str).str.extract(r"^[+-]?\d{4}-(\d{2})-(\d{2})")
jan1 = sorted(set(d.a[(p >= 11) & (md[0] == "01") & (md[1] == "01")]))
np.save(os.path.expanduser("~/.artamatch-dev/_jan1_qids.npy"), np.array(jan1))
print(f"jan-1 candidates on the verified harvest: {len(jan1):,}")
PYEOF
$PY -u verify_jan1.py
echo "== 4. corpus v5 =="
AQ_MAR=$DEV/marriages2 AQ_OUT=$DEV/remar_sh5 AQ_TRUTHY=$DEV/truthy_dates.csv \
  AQ_JAN1=$DEV/jan1_verified.csv AQ_FULLPREC=1 AQ_DECEASED=1 $PY -u build_remarriage.py
echo "== 5. phases =="
cd ~/Studio/artamatch/research/sidereal
AQ_SRC=$DEV/remar_sh5 AQ_OUT=$DEV/remar_sh5 AQ_NO_PLACE=1 $PY -u kerykeion_phases.py
cd $K
echo "== 6. the race: two banks on CV, no reads =="
AQ_BANK=base $PY -u v20_final.py
AQ_BANK=wave4 $PY -u v20_final.py
echo "== 7. one read for the CV winner =="
WIN=$($PY -c "
import json, os
a = json.load(open(os.path.expanduser('~/.artamatch-dev/v20_cv_base.json')))
b = json.load(open(os.path.expanduser('~/.artamatch-dev/v20_cv_wave4.json')))
print('wave4' if b['cv'] > a['cv'] else 'base')")
echo "winner: $WIN"
AQ_BANK=$WIN AQ_READ=1 $PY -u v20_final.py
echo "== CHAIN COMPLETE =="
