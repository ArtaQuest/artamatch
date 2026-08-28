#!/bin/bash
# bio_launch.sh <n_shards> — shard the article titles, upload, and fan out ACI workers in swedencentral.
set -e
N=${1:-10}
RG=artaquest-relay
BIO=~/.artamatch-dev/bio
SA=$(sed -n 1p $BIO/.azure); KEY=$(sed -n 2p $BIO/.azure); SAS=$(sed -n 3p $BIO/.azure)
python3 - "$N" << 'PYEOF'
import json, os, sys
import pandas as pd
N = int(sys.argv[1])
BIO = os.path.expanduser("~/.artamatch-dev/bio")
t = pd.read_csv(f"{BIO}/titles.csv", dtype=str)
t = t[t.title.notna() & (t.title != "")]
titles = sorted(set(t.title))
os.makedirs(f"{BIO}/shards", exist_ok=True)
for i in range(N):
    json.dump(titles[i::N], open(f"{BIO}/shards/shard_{i:02d}.json", "w"))
print(f"{len(titles):,} titles -> {N} shards of ~{len(titles)//N:,}")
PYEOF
for i in $(seq -f "%02g" 0 $((N-1))); do
  az storage blob upload --account-name $SA --account-key "$KEY" -c biofetch \
     -n shard_$i.json -f $BIO/shards/shard_$i.json --overwrite -o none
done
echo "shards uploaded"
B64=$(base64 < ~/Studio/artamatch/kaggle/bio_worker.py | tr -d '\n')
for i in $(seq -f "%02g" 0 $((N-1))); do
  SU=$(printf '%s' "https://$SA.blob.core.windows.net/biofetch/shard_$i.json?$SAS" | base64 | tr -d '\n')
  OU=$(printf '%s' "https://$SA.blob.core.windows.net/biofetch/out_$i.jsonl.gz?$SAS" | base64 | tr -d '\n')
  az container create -g $RG -n biofetch-$i --image python:3.11-slim --os-type Linux \
    --cpu 1 --memory 1.5 --restart-policy Never --location swedencentral \
    --environment-variables SCRIPT_B64="$B64" SHARD_URL_B64="$SU" OUT_URL_B64="$OU" \
    --command-line "sh -c 'echo \$SCRIPT_B64 | base64 -d > /w.py && python3 /w.py'" -o none &
done
wait
echo "launched $N workers"
