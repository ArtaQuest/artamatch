#!/bin/bash
# bio_supervise.sh — when the title sweep finishes, fan the article fetch out across Azure containers,
# collect the shards, and rebuild the marriage descriptions. Idempotent: rerun tops up what is missing.
set -u
N=${N:-12}
RG=artaquest-relay
BIO=~/.artamatch-dev/bio
K=~/Studio/artamatch/kaggle
PY=~/.artamatch-venv/bin/python
SA=$(sed -n 1p $BIO/.azure); KEY=$(sed -n 2p $BIO/.azure); SAS=$(sed -n 3p $BIO/.azure)

echo "== waiting for the title sweep =="
while pgrep -f bio_titles.py > /dev/null; do sleep 60; done
grep -c COMPLETE $BIO/../bio_titles.log > /dev/null 2>&1 || true
echo "titles: $(wc -l < $BIO/titles.csv) rows"

echo "== sharding and launching $N workers =="
$PY - "$N" << 'PYEOF'
import json, os, sys, glob, gzip
import pandas as pd
N = int(sys.argv[1])
BIO = os.path.expanduser("~/.artamatch-dev/bio")
t = pd.read_csv(f"{BIO}/titles.csv", dtype=str)
t = t[t.title.notna() & (t.title != "")]
titles = sorted(set(t.title))
have = set()
for f in glob.glob(f"{BIO}/pages/*.jsonl.gz"):
    with gzip.open(f, "rt") as fh:
        for line in fh:
            if line.strip():
                o = json.loads(line)
                have.add(o["title"]); have.add(o.get("resolved", ""))
todo = [x for x in titles if x not in have]
os.makedirs(f"{BIO}/shards", exist_ok=True)
for i in range(N):
    json.dump(todo[i::N], open(f"{BIO}/shards/shard_{i:02d}.json", "w"))
print(f"{len(titles):,} titles · {len(have):,} already fetched · {len(todo):,} to go -> {N} shards")
PYEOF

for i in $(seq -f "%02g" 0 $((N-1))); do
  az storage blob upload --account-name $SA --account-key "$KEY" -c biofetch \
     -n shard_$i.json -f $BIO/shards/shard_$i.json --overwrite -o none 2>/dev/null
  az storage blob delete --account-name $SA --account-key "$KEY" -c biofetch -n out_$i.jsonl.gz -o none 2>/dev/null
done
B64=$(base64 < $K/bio_worker.py | tr -d '\n')
for i in $(seq -f "%02g" 0 $((N-1))); do
  az container delete -g $RG -n biofetch-$i --yes -o none 2>/dev/null
  SU=$(printf '%s' "https://$SA.blob.core.windows.net/biofetch/shard_$i.json?$SAS" | base64 | tr -d '\n')
  OU=$(printf '%s' "https://$SA.blob.core.windows.net/biofetch/out_$i.jsonl.gz?$SAS" | base64 | tr -d '\n')
  az container create -g $RG -n biofetch-$i --image python:3.11-slim --os-type Linux \
    --cpu 1 --memory 1.5 --restart-policy Never --location swedencentral \
    --environment-variables SCRIPT_B64="$B64" SHARD_URL_B64="$SU" OUT_URL_B64="$OU" \
    --command-line "sh -c 'echo \$SCRIPT_B64 | base64 -d > /w.py && python3 /w.py'" -o none 2>/dev/null &
done
wait
echo "launched"

echo "== collecting =="
for round in $(seq 1 90); do
  DONE=$(az storage blob list --account-name $SA --account-key "$KEY" -c biofetch \
        --query "length([?starts_with(name,'out_')])" -o tsv 2>/dev/null || echo 0)
  echo "  round $round: $DONE/$N shards uploaded"
  [ "$DONE" -ge "$N" ] && break
  sleep 60
done
for i in $(seq -f "%02g" 0 $((N-1))); do
  az storage blob download --account-name $SA --account-key "$KEY" -c biofetch \
    -n out_$i.jsonl.gz -f $BIO/pages/wave_$i.jsonl.gz --overwrite -o none 2>/dev/null
done
for i in $(seq -f "%02g" 0 $((N-1))); do az container delete -g $RG -n biofetch-$i --yes -o none 2>/dev/null; done
echo "== rebuilding descriptions =="
cd $K && $PY -u bio_assemble.py && $PY -u bio_rank.py
echo "BIO-PIPELINE-DONE"
