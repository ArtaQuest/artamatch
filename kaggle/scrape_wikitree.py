"""
scrape_wikitree.py — ended relationships from WikiTree, the same target, an order of magnitude more of them.

WHY. Wikidata's ceiling for this target is about 27,000 usable pairs, and the power calculation says resolving
a +0.005 effect needs roughly 208,000. WikiTree carries both partners' birth and death dates AND a
`marriage_end_date` on the spouse link, which is exactly what the validated end-vs-death rule needs. Sampling
1,200 profile ids found labelable couples at 2.42% per id, which extrapolates to ~725,000 across its ~30M ids.

COURTESY, because this is a volunteer-run site and the numbers above are large:
  · one call carries 100 ids, so a full sweep is ~300,000 calls rather than 30 million
  · a deliberate delay between calls, and a small fixed number of streams — never a fan-out proportional to
    however many machines happen to be available
  · the User-Agent identifies the project and a contact address
  · every batch is written to its own file and skipped if already present, so a stop costs one batch and a
    resume re-fetches nothing

WHAT IS NOT DONE HERE. plus.wikitree.com — a companion site, not this API — returns "Your request was blocked
since it originates from an IP range blocked due to AI bots activity" and names a person to contact for access.
That is an explicit access-control decision, so it is not routed around, and nothing in this file touches that
host. The sanctioned path for a FULL bulk pull is WikiTree's own database dump, which needs an account and
agreement to their terms; this API sweep is for a working subset.
"""
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = os.environ.get("AQ_WT_OUT", os.path.expanduser("~/.artamatch-dev/wikitree"))
UA = "ArtaMatch research (https://artaquest.com; arash@artaquest.org)"
BATCH = 100
DELAY = float(os.environ.get("AQ_WT_DELAY", "1.0"))
LO = int(os.environ.get("AQ_WT_LO", "1"))
HI = int(os.environ.get("AQ_WT_HI", "30000000"))
STRIDE = int(os.environ.get("AQ_WT_STRIDE", "1"))       # this stream's slot, for a few parallel streams
NSTREAM = int(os.environ.get("AQ_WT_NSTREAM", "1"))
MAXCALLS = int(os.environ.get("AQ_WT_MAXCALLS", "20000"))
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.0f}s]", *a, flush=True)


def fetch(ids, tries=4):
    u = "https://api.wikitree.com/api.php?" + urllib.parse.urlencode(
        {"action": "getPeople", "keys": ",".join(map(str, ids)), "fields": "BirthDate,DeathDate,Spouses,Gender"})
    for k in range(tries):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as f:
                return json.load(f)
        except Exception as e:
            if k == tries - 1:
                raise                        # a failure must REACH the caller, never look like an empty range
            time.sleep(5 * (k + 1))          # back off rather than hammer
    raise RuntimeError("unreachable")


def rows_from(payload):
    """One row per spouse link that carries both birth dates. The end date may be absent; the label step
    decides what to do with that, not this one."""
    out = []
    if not payload:
        return out
    p = (payload[0].get("people") or {}) if isinstance(payload, list) else {}
    ok = lambda x: isinstance(x, str) and len(x) >= 4 and x[:4].isdigit() and x[:4] != "0000"
    for pid, v in p.items():
        if not isinstance(v, dict):
            continue
        sps = v.get("Spouses") or {}
        sps = list(sps.values()) if isinstance(sps, dict) else sps
        for s in (sps if isinstance(sps, list) else []):
            if not isinstance(s, dict):
                continue
            a, b = v.get("BirthDate", ""), s.get("BirthDate", "")
            if not (ok(a) and ok(b)):
                continue
            out.append({"a": str(pid), "b": str(s.get("Id", "")),
                        "adob": a, "bdob": b,
                        "adeath": v.get("DeathDate", ""), "bdeath": s.get("DeathDate", ""),
                        "agender": v.get("Gender", ""), "bgender": s.get("Gender", ""),
                        "start": s.get("marriage_date", ""), "end": s.get("marriage_end_date", "")})
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    starts = list(range(LO, HI, BATCH))
    rnd = random.Random(99)
    rnd.shuffle(starts)                      # spread the load over the id space instead of marching through it
    starts = [s for i, s in enumerate(starts) if i % NSTREAM == (STRIDE - 1)]
    log(f"stream {STRIDE}/{NSTREAM}: {len(starts):,} batches available, capped at {MAXCALLS:,} this run")
    got = calls = fails = 0
    for lo in starts[:MAXCALLS]:
        path = os.path.join(OUT, f"b{lo}.jsonl")
        if os.path.exists(path):
            continue
        # A FETCH THAT FAILED MUST NOT LEAVE A FILE. The first version wrote an empty batch on failure, which
        # is byte-identical to "this id range genuinely holds no couples" — so the resume logic skipped it
        # forever and 96% of batches came back empty while the API was answering fine in half a second.
        try:
            r = rows_from(fetch(range(lo, lo + BATCH)))
        except Exception as e:
            fails += 1
            log(f"  batch {lo} FAILED ({type(e).__name__}) — leaving it absent so it is retried")
            if fails % 5 == 0:
                log(f"  {fails} failures; backing off 60s"); time.sleep(60)
            continue
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            for row in r:
                f.write(json.dumps(row) + "\n")
        os.replace(tmp, path)                # atomic: a partial file is never mistaken for a finished batch
        got += len(r); calls += 1
        if calls % 50 == 0:
            log(f"  {calls:,} calls · {got:,} couples · {got/max(1,calls):.1f} per call · "
                f"{(time.time()-T0)/max(1,calls):.2f}s per call")
        time.sleep(DELAY)
    log(f"done: {calls:,} calls, {got:,} couples with both birth dates, {fails} failed batches left for retry")


if __name__ == "__main__":
    main()
