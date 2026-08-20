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
SINK = (open("/tmp/aqwiki/blob_base.txt").read().strip() + "?" + open("/tmp/aqwiki/sas.txt").read().strip()) if os.path.exists("/tmp/aqwiki/sas.txt") else ""
LANGS = [l for l in os.environ.get("AQ_LANGS", "en,de,fr,es,it,ru,ja,pt,pl,nl,sv,zh,uk,cs,fa,ar,tr,hu,fi,da,hy").split(",") if l]
PER = int(os.environ.get("AQ_LANGS_PER_CONTAINER", "2"))
HF = "https://huggingface.co/artaquest/artamodel/resolve/main/wikiharvest"
WORKER = r'''
import base64, gzip, os, subprocess, sys, urllib.request  # noqa
os.makedirs("/tmp/aqwiki", exist_ok=True)
HF = sys.argv[1]; LANGS = sys.argv[2]; JSH = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "none" else ""
SINK = sys.argv[4]; SHARD_ID = sys.argv[5]
for f in ("pool.csv.gz", "sitelinks.jsonl.gz", "found.csv.gz", "wiki_start_harvest.py"):
    with urllib.request.urlopen(HF + "/" + f, timeout=300) as r:
        data = r.read()
    p = "/tmp/aqwiki/" + f.replace(".gz", "")
    open(p, "wb").write(gzip.decompress(data) if f.endswith(".gz") else data)
    if f == "found.csv.gz":
        open("/tmp/aqwiki/found.seed", "wb").write(gzip.decompress(data))
    print("got", f, flush=True)
env = dict(os.environ, AQ_DIR="/tmp/aqwiki", AQ_LANGS=LANGS)
if JSH:
    env["AQ_JOB_SHARD"] = JSH
lg = open("/tmp/run.log", "w")
r = subprocess.run([sys.executable, "-u", "/tmp/aqwiki/wiki_start_harvest.py", "harvest"], env=env, stdout=lg, stderr=subprocess.STDOUT)
lg.close()
seed = open("/tmp/aqwiki/found.seed", "rb").read() if os.path.exists("/tmp/aqwiki/found.seed") else b""
data = open("/tmp/aqwiki/found.csv", "rb").read() if os.path.exists("/tmp/aqwiki/found.csv") else b""
def put(name, payload):
    req = urllib.request.Request(SINK.split("?")[0] + "/" + name + "?" + SINK.split("?", 1)[1], data=payload, method="PUT", headers={"x-ms-blob-type": "BlockBlob"})
    for i in range(6):
        try:
            urllib.request.urlopen(req, timeout=120); return True
        except Exception:
            import time; time.sleep(10 * (i + 1))
    return False
ok = put("found_" + SHARD_ID + ".csv.gz", gzip.compress(data[len(seed):]))
put("log_" + SHARD_ID + ".txt", open("/tmp/run.log", "rb").read()[-200000:])
print("###DONE### upload=" + str(ok) + " exit=" + str(r.returncode), flush=True)
'''


def upload():
    from huggingface_hub import HfApi, CommitOperationAdd
    tok = open(os.path.expanduser("~/.artaquest-dev/hf_token_pro")).read().strip(); api = HfApi(token=tok)
    for src, dst in ((os.path.join(DIR, "pool.csv"), "pool.csv.gz"), (os.path.join(DIR, "sitelinks.jsonl"), "sitelinks.jsonl.gz"), (os.path.join(DIR, "found.csv"), "found.csv.gz")):
        open(f"/tmp/{dst}", "wb").write(gzip.compress(open(src, "rb").read()))
    ops = [CommitOperationAdd("wikiharvest/pool.csv.gz", "/tmp/pool.csv.gz"), CommitOperationAdd("wikiharvest/sitelinks.jsonl.gz", "/tmp/sitelinks.jsonl.gz"),
           CommitOperationAdd("wikiharvest/found.csv.gz", "/tmp/found.csv.gz"), CommitOperationAdd("wikiharvest/wiki_start_harvest.py", os.path.join(HERE, "wiki_start_harvest.py"))]
    api.create_commit("artaquest/artamodel", ops, commit_message="wikiharvest bundle for the Azure containers (public inputs: the undated-marriage pool + sitelinks)")
    print("  bundle uploaded to HF", flush=True)


def run():
    # intra-wiki sharding: en in six slices, the other big wikis in two, the rest 3 languages per container
    SPLIT = {"en": 6, "de": 2, "fr": 2, "ru": 2, "ar": 2, "sv": 2, "es": 2, "ja": 2}
    rest = [l for l in LANGS if l not in SPLIT]
    shards = [([l], f"{k}/{n}") for l, n in SPLIT.items() if l in LANGS for k in range(n)] + [(rest[i:i + PER], "") for i in range(0, len(rest), PER)]
    print(f"  {len(LANGS)} languages -> {len(shards)} containers ({PER}/container)", flush=True)
    if os.environ.get("AQ_DO_FETCH") != "1":
        print("  PLAN ONLY — AQ_DO_FETCH=1 to upload the bundle and create the containers"); return
    upload()
    w64 = base64.b64encode(WORKER.encode()).decode(); names = []
    for i, (sh, jsh) in enumerate(shards):
        cname = f"aqwiki{i}"
        sid = f"{'_'.join(sh)}_{(jsh or 'all').replace('/', 'of')}"
        cmd = f"/bin/sh -c \"echo {w64} | base64 -d > /w.py && python /w.py {HF} {','.join(sh)} {jsh or 'none'} '{SINK}' {sid}\""
        assert len(cmd) < 100_000
        subprocess.run(["az", "container", "create", "-g", RG, "-n", cname, "--image", IMAGE, "--os-type", "Linux", "--cpu", "1", "--memory", "1.5",
                        "--restart-policy", "Never", "--location", LOC, "--command-line", cmd, "-o", "none"], check=False)
        names.append((cname, sh, jsh)); print(f"    started {cname}: {','.join(sh)} {jsh}", flush=True)
    import urllib.request as _ur
    out = os.path.join(DIR, "found.csv"); have = set()
    if os.path.exists(out):
        for r in open(out):
            have.add(r.split(",")[0] + r)
    sids = {f"{'_'.join(sh)}_{(jsh or 'all').replace('/', 'of')}": (cname, sh) for cname, sh, jsh in names}
    done = set(); t0 = time.time()
    with open(out, "a") as f:
        while len(done) < len(sids) and time.time() - t0 < 3 * 3600:
            time.sleep(45)
            for sid, (cname, sh) in sids.items():
                if sid in done:
                    continue
                try:
                    with _ur.urlopen(SINK.split("?")[0] + f"/found_{sid}.csv.gz?" + SINK.split("?", 1)[1], timeout=60) as r_:
                        rows = gzip.decompress(r_.read()).decode()
                except Exception:
                    continue
                n = 0
                for line in rows.splitlines():
                    key = line.split(",")[0] + line
                    if line and key not in have:
                        f.write(line + "\n"); have.add(key); n += 1
                f.flush(); done.add(sid); print(f"    {sid} ({cname}): {n:,} rows merged", flush=True)
                subprocess.run(["az", "container", "delete", "-g", RG, "-n", cname, "--yes", "-o", "none"], check=False)
    print(f"  {len(done)}/{len(sids)} shards harvested -> {out}; anything missing resumes locally via `wiki_start_harvest.py harvest`", flush=True)


if __name__ == "__main__":
    run()
