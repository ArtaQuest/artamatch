"""bio_worker.py — runs INSIDE an Azure container (or locally). Fetches English Wikipedia wikitext for
its shard of article titles and uploads one gzipped JSONL to blob storage.
Env: SHARD_URL (SAS url of the shard json), OUT_URL (SAS url to PUT the result), UA."""
import gzip, json, os, sys, time, urllib.parse, urllib.request
UA = os.environ.get("UA", "ArtaMatch research (https://artaquest.com; arash@artaquest.org)")
API = "https://{lang}.wikipedia.org/w/api.php"

def get(url, tries=5, data=None, headers=None):
    h = {"User-Agent": UA}
    h.update(headers or {})
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=h, method="PUT" if data is not None else "GET")
            with urllib.request.urlopen(req, timeout=180) as f:
                return f.read()
        except Exception as e:
            code = getattr(e, "code", 0)
            if code == 429:
                time.sleep(30)
            elif k == tries - 1:
                raise
            else:
                time.sleep(6 * (k + 1))

import base64 as _b64
def _url(name):
    v = os.environ.get(name + "_B64")
    return _b64.b64decode(v).decode() if v else os.environ[name]
shard = json.loads(get(_url("SHARD_URL")).decode())
# a shard is either a bare list of English titles (wave 1) or [lang, title] pairs (multilingual waves)
if shard and isinstance(shard[0], str):
    shard = [["en", t] for t in shard]
bylang = {}
for lang, t in shard:
    bylang.setdefault(lang, []).append(t)
print(f"shard: {len(shard)} titles across {len(bylang)} languages", flush=True)
def upload(rows, suffix=""):
    buf = gzip.compress("\n".join(json.dumps(o, ensure_ascii=False) for o in rows).encode())
    url = _url("OUT_URL")
    if suffix:
        url = url.replace(".jsonl.gz?", f".part{suffix}.jsonl.gz?")
    get(url, data=buf, headers={"x-ms-blob-type": "BlockBlob"})
    print(f"uploaded {len(rows)} pages{'' if not suffix else ' (part ' + suffix + ')'}, "
          f"{len(buf)/1e6:.1f} MB", flush=True)

out = []
last_ckpt = 0
B = 20
work = [(lang, ts[i:i + B]) for lang, ts in bylang.items() for i in range(0, len(ts), B)]
for i, (lang, batch) in enumerate(work):
    q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "revisions",
                                "rvprop": "content", "rvslots": "main", "formatversion": "2",
                                "redirects": "1", "titles": "|".join(batch)})
    try:
        j = json.loads(get(API.format(lang=lang) + "?" + q).decode())
    except Exception as e:
        print(f"  {lang} batch {i} failed: {str(e)[:70]}", flush=True)
        continue
    norm = {}
    for r in j.get("query", {}).get("normalized", []) + j.get("query", {}).get("redirects", []):
        norm[r["to"]] = r["from"]
    for pg in j.get("query", {}).get("pages", []):
        if "revisions" not in pg:
            continue
        txt = pg["revisions"][0].get("slots", {}).get("main", {}).get("content", "")
        t = pg.get("title", "")
        out.append({"lang": lang, "title": norm.get(t, t), "resolved": t, "wikitext": txt[:120000]})
    if i % 25 == 0:
        print(f"  {i}/{len(work)} batches · kept {len(out)}", flush=True)
    if len(out) - last_ckpt >= 4000:
        try:
            upload(out, f"{i:05d}")
            last_ckpt = len(out)
        except Exception as e:
            print(f"  checkpoint failed: {str(e)[:60]}", flush=True)
    time.sleep(0.4)
upload(out)
print(f"DONE {len(out)} pages", flush=True)
