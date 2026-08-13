"""
collect_chunked.py — build the feature blocks for ALL 134,957 couples on a 17 GB machine.

WHY CHUNKING IS NECESSARY. `run.py collect` calls each module's build(E) once for every couple. That is fine
at 60,000 rows and impossible at 134,957: trad_modern_western alone emits 5,846 columns, which is 6.3 GB of
float64 before it is cast down to float32 for storage, and it is one of six modules over 3 GB. Add the
ephemeris table itself (about 1 GB at this size) and the intermediates each module allocates while building,
and a single-pass run thrashes and dies. So the couples are built in contiguous slices and the slices are
concatenated per block.

WHY THAT IS EXACTLY EQUIVALENT, AND THE ONE CONDITION. Concatenating slices reproduces the full-size build if
and only if every emitted column is a function of its OWN ROW — never of a statistic taken across rows. A
z-score, a rank, a percentile bin edge or a min-max normalisation computed over the batch would all make a
chunked build differ from a whole one, silently. That condition was audited across all nineteen modules
rather than assumed; see the note in this project's log. Two things here enforce the rest of it:

  * AQ_KEEP_ALL_COLS=1 on every chunk. `collect` normally drops columns whose standard deviation is zero,
    and a 20,000-row slice legitimately has constant columns that the full set does not. Pruning per chunk
    would hand each chunk a DIFFERENT column set and the concatenation would misalign. Pruning is applied
    once, globally, after concatenation.
  * A UNIQUE ephemeris cache per chunk. core.py validates its cache by SHAPE alone, so two chunks of the
    same row count would collide and the second would silently be built on the first chunk's planetary
    positions — every feature wrong, nothing raised. Equal-sized chunks make that collision the default
    rather than a remote possibility, so the cache path carries the chunk index and is deleted after use.

WHAT IT DOES NOT DO. It does not chunk `astro_stack.py`. The stack needs the ephemeris, the target and the
person groups at full size, but only ONE block matrix at a time, so its peak is under 2 GB — and loading the
whole thing there is what gives the authoritative person grouping, computed by one union-find over all
134,957 couples instead of one per chunk.

Usage:
    cd astro && ~/.artamatch-venv/bin/python collect_chunked.py                 # all chunks, then merge
    cd astro && ~/.artamatch-venv/bin/python collect_chunked.py --merge-only    # merge existing chunks
"""
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "astro-out")
COUPLES = os.path.join(ROOT, "research/data-dob/couples-parents.json")
KEYS = os.path.join(OUT, "selected-keys.json")
ROWS = os.path.join(OUT, "rows.json")
CHUNKDIR = os.path.join(HERE, "chunks")
BLOCKS = os.path.join(HERE, "blocks")
CHUNK = int(os.environ.get("AQ_CHUNK") or 22000)
PY = os.path.expanduser("~/.artamatch-venv/bin/python")


def row_count():
    if not os.path.exists(ROWS):
        env = dict(os.environ)
        env.update({"AQ_COUPLES": COUPLES, "AQ_DUMP_ROWS": ROWS, "AQ_NO_PLACE": "1"})
        subprocess.run([PY, "-c", "import core; core.load()"], env=env, cwd=HERE, check=True)
    return int(json.load(open(ROWS))["n"])


def build_chunks(n):
    os.makedirs(CHUNKDIR, exist_ok=True)
    bounds = [(s, min(s + CHUNK, n)) for s in range(0, n, CHUNK)]
    print(f"{n:,} couples in {len(bounds)} chunks of up to {CHUNK:,}\n")
    keys = [r["key"] if isinstance(r, dict) else r for r in json.load(open(KEYS))]
    for ci, (lo, hi) in enumerate(bounds):
        cdir = os.path.join(CHUNKDIR, f"c{ci:02d}")
        done = os.path.join(cdir, "manifest.json")
        if os.path.exists(done):
            man = json.load(open(done))
            if len(man["blocks"]) >= len(keys):
                print(f"  chunk {ci:02d} [{lo:,}..{hi:,}) already complete — {len(man['blocks'])} blocks")
                continue
        os.makedirs(cdir, exist_ok=True)
        idx = os.path.join(cdir, "rows.npy")
        np.save(idx, np.arange(lo, hi, dtype=np.int64))
        cache = os.path.join(cdir, "ephem.npz")           # unique per chunk — see the docstring
        env = dict(os.environ)
        env.update({"AQ_COUPLES": COUPLES, "AQ_ROW_INDEX": idx, "AQ_ONLY_KEYS": KEYS,
                    "AQ_NO_PLACE": "1",          # the input contract: two dates and nothing else
                    "AQ_BLOCKS": cdir, "AQ_EPHEM_CACHE": cache,
                    "AQ_OUT_MANIFEST": done, "AQ_KEEP_ALL_COLS": "1", "AQ_OUTDIR": cdir})
        env.pop("AQ_SUBSAMPLE", None)
        env.pop("AQ_BALANCE", None)
        t0 = time.time()
        print(f"  chunk {ci:02d} [{lo:,}..{hi:,}) building…", flush=True)
        r = subprocess.run([PY, os.path.join(HERE, "run.py"), "collect"],
                           env=env, cwd=HERE, text=True, capture_output=True)
        if r.returncode != 0:
            sys.stdout.write(r.stdout[-4000:])
            sys.stderr.write(r.stderr[-4000:])
            raise SystemExit(f"chunk {ci} failed")
        tail = [l for l in r.stdout.splitlines() if "blocks," in l or "columns total" in l]
        print(f"  chunk {ci:02d} done in {time.time()-t0:.0f}s · {tail[-1] if tail else ''}", flush=True)
        if os.path.exists(cache):
            os.remove(cache)                              # 1 GB per chunk, and never reused
    return bounds


def merge(bounds):
    """Concatenate each block across chunks, then prune constant columns ONCE, globally."""
    os.makedirs(BLOCKS, exist_ok=True)
    mans = [json.load(open(os.path.join(CHUNKDIR, f"c{ci:02d}", "manifest.json")))
            for ci in range(len(bounds))]
    # THE REFERENCE KEY LIST IS THE SELECTION, NOT CHUNK 0. Seeding it from chunk 0 meant a block absent
    # from chunk 0 but present in every other chunk was silently dropped instead of raising — the failure
    # mode being a tradition that quietly leaves the model.
    want = [r["key"] if isinstance(r, dict) else r for r in json.load(open(KEYS))]
    keys = [k for k in want if any(b["key"] == k for m in mans for b in m["blocks"])]
    for m, (lo, hi) in zip(mans, bounds):
        got = {b["key"] for b in m["blocks"]}
        missing = [k for k in keys if k not in got]
        if missing:
            raise SystemExit(f"chunk [{lo}..{hi}) is missing {len(missing)} blocks: {missing[:3]}")
    never = [k for k in want if k not in keys]
    if never:
        raise SystemExit(f"{len(never)} selected blocks were built by NO chunk: {never[:3]}")
    print(f"\nmerging {len(keys)} blocks across {len(bounds)} chunks")
    out_blocks = []
    total_cols = dropped = 0
    for k in keys:
        parts = []
        for ci, m in enumerate(mans):
            b = next(x for x in m["blocks"] if x["key"] == k)
            parts.append(np.load(os.path.join(CHUNKDIR, f"c{ci:02d}", b["file"]), mmap_mode="r"))
        widths = {p.shape[1] for p in parts}
        if len(widths) != 1:
            raise SystemExit(f"{k}: chunks disagree on width {widths} — AQ_KEEP_ALL_COLS was not honoured")
        # EQUAL WIDTHS ARE NOT PROOF OF EQUIVALENCE. Two of these blocks once carried an across-row
        # dependency — trad_harmonics divided by the batch's median speed, trad_lunar_calendrical built its
        # Spica grid from the batch's date range — and both produced chunks of IDENTICAL width with
        # different values, so this check saw nothing. The real guard is /tmp/chunk_equiv-style testing that
        # a whole build and a chunked build agree bit for bit, which is now a precondition of running this
        # script at all; the width check only catches the coarser failure.
        X = np.concatenate([np.asarray(p) for p in parts], axis=0)
        keep = X.std(0) > 1e-12
        if keep.sum() == 0:
            print(f"  {k}: every column constant across all rows — skipped")
            continue
        kept_idx = np.flatnonzero(keep).tolist()
        full_cols = int(X.shape[1])
        X = X[:, keep]
        fn = k.replace("/", "_").replace(" ", "_") + ".npy"
        np.save(os.path.join(BLOCKS, fn), X.astype(np.float32))
        b0 = next(x for x in mans[0]["blocks"] if x["key"] == k)
        out_blocks.append({"key": k, "slug": b0["slug"], "kind": b0["kind"], "name": b0["name"],
                           "cols": int(X.shape[1]), "dropped_constant": int((~keep).sum()),
                           "kept_idx": kept_idx, "full_cols": full_cols, "file": fn})
        total_cols += int(X.shape[1]); dropped += int((~keep).sum())
        print(f"  {k[:66]:<66} {X.shape[0]:>7,} x {X.shape[1]:>5}"
              f"{'  (-' + str(int((~keep).sum())) + ' constant)' if (~keep).any() else ''}")
    man = {"blocks": out_blocks,
           "modules": mans[0]["modules"],
           "rows": int(sum(hi - lo for lo, hi in bounds)),
           "chunks": [[lo, hi] for lo, hi in bounds]}
    json.dump(man, open(os.path.join(HERE, "manifest.json"), "w"), indent=1)
    print(f"\n{len(out_blocks)} blocks · {total_cols:,} columns · {man['rows']:,} rows "
          f"· {dropped:,} constant columns pruned globally")
    print(f"wrote manifest.json and {BLOCKS}/")


def main():
    n = row_count()
    bounds = [(s, min(s + CHUNK, n)) for s in range(0, n, CHUNK)]
    if "--merge-only" not in sys.argv:
        bounds = build_chunks(n)
    merge(bounds)
    if "--keep-chunks" not in sys.argv:
        shutil.rmtree(CHUNKDIR, ignore_errors=True)
        print(f"removed {CHUNKDIR}")


if __name__ == "__main__":
    main()
