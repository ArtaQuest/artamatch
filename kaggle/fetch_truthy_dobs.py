"""Resolve multi-valued birth/death dates by Wikidata RANK: preferred > normal, never deprecated.
Writes ~/.artamatch-dev/truthy_dates.csv (qid, dob_truthy, death_truthy)."""
import json, os, time, urllib.request
import numpy as np, pandas as pd
UA = {"User-Agent": "ArtaMatch-audit/1.0 (research corpus verification)"}
OUT = os.path.expanduser("~/.artamatch-dev/truthy_dates.csv")
qids = list(np.load(os.path.expanduser("~/.artamatch-dev/_multi_dob_qids.npy")))
done = set()
if os.path.exists(OUT):
    done = set(pd.read_csv(OUT, dtype=str).qid)
qids = [q for q in qids if q not in done]
print(f"resolving {len(qids):,} persons ({len(done):,} already checkpointed)")

def render(ts, p):
    import re
    if not ts:
        return "0000-00-00"
    m = re.match(r"^[+-]?(\d{4})-(\d{2})-(\d{2})", ts)
    if not m or m[1] == "0000":
        return "0000-00-00"
    y, mo, d_ = m.groups()
    if p is None:
        return f"{y}-00-00" if (mo, d_) == ("01", "01") else f"{y}-{mo}-{d_}"
    if p <= 9:
        return f"{y}-00-00"
    if p == 10:
        return f"{y}-{mo}-00"
    return f"{y}-00-00" if (mo, d_) == ("01", "01") else f"{y}-{mo}-{d_}"

def best(cl):
    """truthy pick: preferred rank if any, else normal; deprecated never."""
    pref = [c for c in cl if c.get("rank") == "preferred"]
    norm = [c for c in cl if c.get("rank") == "normal"]
    for c in (pref or norm):
        try:
            v = c["mainsnak"]["datavalue"]["value"]
            return v["time"], v["precision"]
        except Exception:
            continue
    return None, None

for i in range(0, len(qids), 50):
    rows = []
    batch = qids[i:i + 50]
    url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=claims&ids="
           + "|".join(batch))
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                j = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = max(int(e.headers.get("Retry-After", "30") or 30), 30)
                print(f"  429 — backing off {wait}s", flush=True)
                time.sleep(wait)
            elif attempt == 5:
                raise
            else:
                time.sleep(10)
        except Exception:
            if attempt == 5:
                raise
            time.sleep(10)
    for q, e in j.get("entities", {}).items():
        cl = e.get("claims", {})
        bt, bp = best(cl.get("P569", []))
        dt, _ = best(cl.get("P570", []))
        dy = int(dt[1:5]) if dt and dt[1:5].isdigit() else ""
        rows.append((q, render(bt, bp), dy))
    pd.DataFrame(rows, columns=["qid", "dob_truthy", "death_truthy"]).to_csv(
        OUT, mode="a", header=not os.path.exists(OUT), index=False)
    if (i // 50) % 25 == 0:
        print(f"  {i + len(batch):,}/{len(qids):,}", flush=True)
    time.sleep(2.0)
print("saved truthy_dates.csv (checkpointed) — COMPLETE")
