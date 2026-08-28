#!/bin/bash
# bio_wave.sh [n_workers] — one wave of article fetching across Azure containers.
# Idempotent: the shard list is always "articles we want minus articles we already have", so running it
# again picks up whatever the last wave missed (Azure student quota silently caps concurrent containers,
# so a wave that asks for 12 may only get 7 — this is how the rest arrive).
set -u
N=${1:-6}
RG=artaquest-relay
BIO=~/.artamatch-dev/bio
K=~/Studio/artamatch/kaggle
PY=~/.artamatch-venv/bin/python
SA=$(sed -n 1p $BIO/.azure); KEY=$(sed -n 2p $BIO/.azure); SAS=$(sed -n 3p $BIO/.azure)
TAG=$(date +%H%M%S)

$PY - "$N" << 'PYEOF'
import glob, gzip, json, os, sys
import pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from bio_langs import LANGS
N = int(sys.argv[1])
BIO = os.path.expanduser("~/.artamatch-dev/bio")
ORDER = {l: i for i, l in enumerate(LANGS)}
want = []
if os.path.exists(f"{BIO}/sitelinks.csv"):
    sl = pd.read_csv(f"{BIO}/sitelinks.csv", dtype=str).fillna("")
    sl = sl[(sl.lang != "") & (sl.title != "")]
    want += list(zip(sl.lang, sl.title))
if os.path.exists(f"{BIO}/titles.csv"):
    t = pd.read_csv(f"{BIO}/titles.csv", dtype=str).fillna("")
    want += [("en", x) for x in t.title[t.title != ""]]
want = list(dict.fromkeys(want))
have = set()
for f in glob.glob(f"{BIO}/pages/*.jsonl.gz"):
    with gzip.open(f, "rt") as fh:
        for line in fh:
            if line.strip():
                o = json.loads(line)
                lg = o.get("lang", "en")
                have.add((lg, o["title"]))
                if o.get("resolved"):
                    have.add((lg, o["resolved"]))
todo = [x for x in want if x not in have]
# English first, then the other languages in size order: the earliest waves should buy the most coverage
todo.sort(key=lambda x: ORDER.get(x[0], 99))
os.makedirs(f"{BIO}/shards", exist_ok=True)
CAP = 18000                      # ~40 min of work per worker, so a wave finishes inside its round cap
for i in range(N):
    json.dump([list(x) for x in todo[i::N][:CAP]], open(f"{BIO}/shards/w_{i:02d}.json", "w"))
print(f"want {len(want):,} · have {len(have):,} · fetching {len(todo):,} in {N} shards", flush=True)
PYEOF

for i in $(seq -f "%02g" 0 $((N-1))); do
  az storage blob upload --account-name $SA --account-key "$KEY" -c biofetch \
     -n w_$i.json -f $BIO/shards/w_$i.json --overwrite -o none 2>/dev/null
done
B64=$(base64 < $K/bio_worker.py | tr -d '\n')
LAUNCHED=0
for i in $(seq -f "%02g" 0 $((N-1))); do
  SU=$(printf '%s' "https://$SA.blob.core.windows.net/biofetch/w_$i.json?$SAS" | base64 | tr -d '\n')
  OU=$(printf '%s' "https://$SA.blob.core.windows.net/biofetch/res_${TAG}_$i.jsonl.gz?$SAS" | base64 | tr -d '\n')
  if az container create -g $RG -n bio-$TAG-$i --image python:3.11-slim --os-type Linux \
      --cpu 1 --memory 1.5 --restart-policy Never --location swedencentral \
      --environment-variables SCRIPT_B64="$B64" SHARD_URL_B64="$SU" OUT_URL_B64="$OU" \
      --command-line "sh -c 'echo \$SCRIPT_B64 | base64 -d > /w.py && python3 /w.py'" -o none 2>/dev/null
  then LAUNCHED=$((LAUNCHED+1)); echo "  worker $i up"; else echo "  worker $i REFUSED (quota)"; fi
done
echo "launched $LAUNCHED of $N"

# A wave is over when every worker has uploaded. ACI does NOT report liveness in instanceView.state
# (it reads None there — the earlier version broke the wave on that and lost five shards), so the
# authoritative signals are the uploaded results and each container's own currentState.
for round in $(seq 1 60); do
  DONE=$(az storage blob list --account-name $SA --account-key "$KEY" -c biofetch \
        --query "length([?starts_with(name,'res_${TAG}_')])" -o tsv 2>/dev/null || echo 0)
  LIVE=$(az container list -g $RG --query \
        "length([?starts_with(name,'bio-$TAG') && containers[0].instanceView.currentState.state=='Running'])" \
        -o tsv 2>/dev/null || echo 0)
  echo "  round $round: $DONE/$LAUNCHED uploaded · $LIVE reported running"
  [ "$DONE" -ge "$LAUNCHED" ] && break
  # ACI leaves currentState null while it provisions, so "not Running" never means "dead" — only the
  # uploaded results and the round cap may end a wave. A shard lost to a dead worker returns next wave.
  sleep 60
done
for i in $(seq -f "%02g" 0 $((N-1))); do
  az storage blob download --account-name $SA --account-key "$KEY" -c biofetch \
    -n res_${TAG}_$i.jsonl.gz -f $BIO/pages/res_${TAG}_$i.jsonl.gz --overwrite -o none 2>/dev/null
done
az container list -g $RG --query "[?starts_with(name,'bio-$TAG')].name" -o tsv 2>/dev/null | \
  while read c; do az container delete -g $RG -n "$c" --yes -o none 2>/dev/null; done
cd $K && $PY -u bio_assemble.py
echo "WAVE-$TAG-DONE"
