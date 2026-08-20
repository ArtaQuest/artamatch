"""
az_harvest.py — run wiki_start_harvest's HARVEST phase on Azure containers, one shard of languages per container
(operator 2026-08-20: "don't forget to use az servers to avoid rate limits" — 21 wikis read from 21 egress IPs
instead of this laptop's one; also residential-vs-datacenter differences cut both ways, so failures per language
are counted aloud and anything a container cannot get is left for a local resume).

MECHANICS (the az_fetch.py pattern): the inputs are far too big for the 128 KB argument cap, so pool.csv,
sitelinks.jsonl and wiki_start_harvest.py are uploaded once to the PUBLIC HF repo (artaquest/artamodel, under
wikiharvest/) and each container curls them; results come back through `az container logs` as base64-gzipped CSV
between markers (a few MB gzipped fits the ~4 MB log cap because each container carries only 2 languages).
Usage: AQ_DO_FETCH=1 python az_harvest.py          (plan only without the flag)
"""
import base64
import gzip
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)); DIR = os.environ.get("AQ_DIR", "/tmp/aqwiki")
RG = os.environ.get("AQ_AZ_RG", "artaquest-relay"); LOC = os.environ.get("AQ_AZ_LOC", "swedencentral"); IMAGE = "python:3.12-slim"
LANGS = [l for l in os.environ.get("AQ_LANGS", "en,de,fr,es,it,ru,ja,pt,pl,nl,sv,zh,uk,cs,fa,ar,tr,hu,fi,da,hy").split(",") if l]
PER = int(os.environ.get("AQ_LANGS_PER_CONTAINER", "2"))
HF = "https://huggingface.co/artaquest/artamodel/resolve/main/wikiharvest"
WORKER = r'''
import base64, gzip, os, subprocess, sys, urllib.request
os.makedirs("/tmp/aqwiki", exist_ok=True)
HF = sys.argv[1]; LANGS = sys.argv[2]
for f in ("pool.csv.gz", "sitelinks.jsonl.gz", "wiki_start_harvest.py"):
    with urllib.request.urlopen(HF + "/" + f, timeout=300) as r:
        data = r.read()
    p = "/tmp/aqwiki/" + f.replace(".gz", "")
    open(p, "wb").write(gzip.decompress(data) if f.endswith(".gz") else data)
    print("got", f, flush=True)
env = dict(os.environ, AQ_DIR="/tmp/aqwiki", AQ_LANGS=LANGS)
r = subprocess.run([sys.executable, "-u", "/tmp/aqwiki/wiki_start_harvest.py", "harvest"], env=env)
blob = base64.b64encode(gzip.compress(open("/tmp/aqwiki/found.csv", "rb").read() if os.path.exists("/tmp/aqwiki/found.csv") else b"")).decode()
print("###ROWS###", flush=True)
for i in range(0, len(blob), 100000):
    print(blob[i:i + 100000], flush=True)
print("###DONE###", flush=True)
'''


def upload():
    from huggingface_hub import HfApi, CommitOperationAdd
    tok = open(os.path.expanduser("~/.artaquest-dev/hf_token_pro")).read().strip(); api = HfApi(token=tok)
    for src, dst in ((os.path.join(DIR, "pool.csv"), "pool.csv.gz"), (os.path.join(DIR, "sitelinks.jsonl"), "sitelinks.jsonl.gz")):
        open(f"/tmp/{dst}", "wb").write(gzip.compress(open(src, "rb").read()))
    ops = [CommitOperationAdd("wikiharvest/pool.csv.gz", "/tmp/pool.csv.gz"), CommitOperationAdd("wikiharvest/sitelinks.jsonl.gz", "/tmp/sitelinks.jsonl.gz"),
           CommitOperationAdd("wikiharvest/wiki_start_harvest.py", os.path.join(HERE, "wiki_start_harvest.py"))]
    api.create_commit("artaquest/artamodel", ops, commit_message="wikiharvest bundle for the Azure containers (public inputs: the undated-marriage pool + sitelinks)")
    print("  bundle uploaded to HF", flush=True)


def run():
    shards = [LANGS[i:i + PER] for i in range(0, len(LANGS), PER)]
    print(f"  {len(LANGS)} languages -> {len(shards)} containers ({PER}/container)", flush=True)
    if os.environ.get("AQ_DO_FETCH") != "1":
        print("  PLAN ONLY — AQ_DO_FETCH=1 to upload the bundle and create the containers"); return
    upload()
    w64 = base64.b64encode(WORKER.encode()).decode(); names = []
    for i, sh in enumerate(shards):
        cname = f"aqwiki{i}"
        cmd = f"/bin/sh -c \"echo {w64} | base64 -d > /w.py && python /w.py {HF} {','.join(sh)}\""
        assert len(cmd) < 100_000
        subprocess.run(["az", "container", "create", "-g", RG, "-n", cname, "--image", IMAGE, "--os-type", "Linux", "--cpu", "1", "--memory", "1.5",
                        "--restart-policy", "Never", "--location", LOC, "--command-line", cmd, "-o", "none"], check=False)
        names.append((cname, sh)); print(f"    started {cname}: {','.join(sh)}", flush=True)
    out = os.path.join(DIR, "found.csv"); have = set()
    if os.path.exists(out):
        for r in open(out):
            have.add(r.split(",")[0] + r)
    done = set(); t0 = time.time()
    with open(out, "a") as f:
        while len(done) < len(names) and time.time() - t0 < 4 * 3600:
            time.sleep(60)
            for cname, sh in names:
                if cname in done:
                    continue
                logs = subprocess.run(["az", "container", "logs", "-g", RG, "-n", cname], capture_output=True, text=True).stdout or ""
                if "###DONE###" in logs:
                    blob = "".join(logs.split("###ROWS###", 1)[1].split("###DONE###", 1)[0].split())
                    try:
                        rows = gzip.decompress(base64.b64decode(blob)).decode()
                    except Exception as e:
                        print(f"    {cname}: log decode failed ({e}) — leave for the local resume", flush=True); done.add(cname); continue
                    n = 0
                    for line in rows.splitlines():
                        key = line.split(",")[0] + line
                        if line and key not in have:
                            f.write(line + "\n"); have.add(key); n += 1
                    f.flush(); done.add(cname); print(f"    {cname} ({','.join(sh)}): {n:,} rows merged", flush=True)
                    subprocess.run(["az", "container", "delete", "-g", RG, "-n", cname, "--yes", "-o", "none"], check=False)
    print(f"  {len(done)}/{len(names)} containers harvested -> {out}; anything missing resumes locally via `wiki_start_harvest.py harvest`", flush=True)


if __name__ == "__main__":
    run()
