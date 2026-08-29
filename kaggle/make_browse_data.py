"""make_browse_data.py — shard the judged corpus so a browser can page through all 10,000.

The deliverable CSV is 8.9 MB because it carries every description in full. A reader who wants to check
our work should not have to download that to see the first screen. This writes:

  browse/index.json      counts, the reason vocabulary, and the shard list
  browse/p000.json ...   500 marriages each, only the fields the list shows

Each row keeps what makes a verdict checkable by a stranger: both names, both dates, the verdict, the
ground, the confidence, the quoted evidence, and the Wikipedia links it was read from. The full
description stays in the CSV, one click away, rather than in the page.
"""
import json, math, os
import pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
OUT = os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/almanac/browse")
PER = 500


def main():
    d = pd.read_csv(f"{BIO}/marriage_quality_binary.csv")
    d = d.reset_index(drop=True)
    os.makedirs(OUT, exist_ok=True)
    keep = []
    for _, r in d.iterrows():
        src = str(r.get("sources") or "")
        links = [s for s in src.split(" ") if s.startswith("http")][:2]
        keep.append({
            "a": str(r.name_a), "b": str(r.name_b),
            "da": str(r.dob_a), "db": str(r.dob_b),
            "g": int(bool(r.good)), "r": str(r.reason), "c": str(r.confidence)[:1],
            "e": str(r.evidence)[:240],
            "m": ("" if pd.isna(r.get("married")) else str(r.get("married"))[:10]),
            "u": links,
        })
    n = len(keep)
    shards = math.ceil(n / PER)
    for i in range(shards):
        json.dump(keep[i * PER:(i + 1) * PER],
                  open(f"{OUT}/p{i:03d}.json", "w"), ensure_ascii=False, separators=(",", ":"))
    reasons = d.reason.value_counts().to_dict()
    json.dump({"total": n, "per": PER, "shards": shards,
               "good": int(d.good.sum()), "bad": int((~d.good.astype(bool)).sum()),
               "reasons": {k: int(v) for k, v in reasons.items()},
               "csv": "marriage_quality_binary.csv"},
              open(f"{OUT}/index.json", "w"), indent=1)
    tot = sum(os.path.getsize(f"{OUT}/p{i:03d}.json") for i in range(shards))
    print(f"  {n:,} marriages -> {shards} shards of {PER}  ({tot/1e6:.1f} MB total, "
          f"{tot/shards/1024:.0f} KB per shard)")
    print(f"  first screen costs one {os.path.getsize(f'{OUT}/p000.json')/1024:.0f} KB fetch, "
          f"not {os.path.getsize(f'{BIO}/marriage_quality_binary.csv')/1e6:.1f} MB")


if __name__ == "__main__":
    main()
