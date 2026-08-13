"""
predict_partner.py — search birth dates and birthplaces for the highest-scoring partner.

WHAT IT DOES. Holds one person's birth data fixed, then sweeps candidate partners over a grid of birth dates
and every city above a million people, scores each candidate with the trained model, and returns the ranked
top N.

THE ONE THING THIS FILE HAS TO GET RIGHT is that a candidate's features are computed by *exactly* the same
code as a training row's. A prediction pipeline that recomputes features its own way is the classic way to
produce confident nonsense. So candidates are written into a couples file in the training schema, `core.load`
reads it, and the same tradition modules build the same blocks. Nothing here reimplements a feature.

    fixed partner   the person searching, e.g. 1994-02-15 10:00 local mean time, Tehran
    dates           a range of candidate birth dates, at a chosen step
    places          research/data-dob/cities1m.json — 937 cities over a million, with coordinates
    model           the bundle written by train_final.py: the fitted estimator plus the block keys it wants

Time is 10:00 LOCAL MEAN TIME at each candidate city, matching core.py's DEFAULT_HOUR convention — so a
candidate born in Tokyo and one born in Lima are both taken at ten in the morning where they were, which is
what makes the comparison between cities meaningful rather than an artefact of the prime meridian.

SCORES ARE MODEL OUTPUTS, NOT PROBABILITIES OF ANYTHING IN THE WORLD. The model was fitted on recorded
partnerships between notable people, its label is whether a couple has a recorded child together, and its
margin over the permitted baseline is small. A ranked list from it is a ranked list of what the model says.

Usage:
    /tmp/aqpy/bin/python predict_partner.py --dob 1994-02-15 --lat 35.6892 --lon 51.3890 \
        --from 1985-01-01 --to 2005-12-31 --step 7 --top 20
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CITIES = os.path.join(ROOT, "research/data-dob/cities1m.json")


def candidate_rows(fixed, cities, dates, sex_fixed="M"):
    """One row per (candidate birth date, city), in the training schema.

    The fixed person is always partner A or B by the older/younger convention core.py applies, so both
    orderings are handled there rather than here — this only has to state the two people honestly.
    """
    rows = []
    for d in dates:
        ds = d.isoformat()
        for c in cities:
            rows.append({
                "a": "SELF", "b": f"C_{ds}_{c['q']}",
                "aDob": fixed["dob"], "bDob": ds,
                "aPrec": 11, "bPrec": 11, "aWin": 1, "bWin": 1,
                "aDobKnown": 1, "bDobKnown": 1, "bothDobKnown": 1,
                "aSex": sex_fixed, "bSex": "F" if sex_fixed == "M" else "M",
                "relation": "spouse",
                "aSitelinks": 1, "bSitelinks": 1, "minSitelinks": 1, "maxSitelinks": 1,
                "bothProminent": 1,
                "aEnwiki": 0, "bEnwiki": 0, "aAwards": 0, "bAwards": 0,
                "aOccupations": 0, "bOccupations": 0,
                "aNatQ": [], "bNatQ": [], "aNatIso": [], "bNatIso": [],
                "aPob": "", "aPobCountry": "", "aLat": fixed["lat"], "aLon": fixed["lon"], "aGeoRes": 3,
                "bPob": c["q"], "bPobCountry": "", "bLat": c["lat"], "bLon": c["lon"], "bGeoRes": 3,
                "nKidsTogether": 0, "strictNegative": 0, "partnersWithKidsElsewhere": 0,
                "label": 0,                      # a placeholder; never read for prediction
                "_date": ds, "_city": c["name"], "_country": c.get("country", ""),
                "_pop": c.get("pop", 0), "_cq": c["q"],
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dob", required=True, help="the fixed person's birth date, YYYY-MM-DD")
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--sex", default="M", choices=["M", "F"])
    ap.add_argument("--from", dest="frm", default="1985-01-01")
    ap.add_argument("--to", dest="to", default="2005-12-31")
    ap.add_argument("--step", type=int, default=7, help="days between candidate birth dates")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--model", default=os.path.join(HERE, "final-model.joblib"))
    ap.add_argument("--min-pop", type=float, default=1e6)
    ap.add_argument("--cities", default="", help="comma-separated city names to restrict to; a shortlist "
                    "keeps the grid inside the places actually under consideration")
    ap.add_argument("--rows-per-batch", type=int, default=140000,
                    help="candidates per scoring process; bounded by the ephemeris arrays, which cost "
                         "about 6 kB per row")
    a = ap.parse_args()

    if not os.path.exists(a.model):
        sys.exit(f"no trained model at {a.model} — run train_final.py first")
    import joblib
    bundle = joblib.load(a.model)
    blocks_wanted, est = bundle["blocks"], bundle["estimator"]
    print(f"model: {bundle.get('label','?')} · {len(blocks_wanted)} blocks · "
          f"cross-validated AUC {bundle.get('auc', float('nan')):.4f}")

    cities = [c for c in json.load(open(CITIES)) if c.get("pop", 0) >= a.min_pop]
    if a.cities:
        want = [w.strip().lower() for w in a.cities.split(",") if w.strip()]
        bykey = {}
        for c in cities:
            bykey.setdefault(c["name"].lower(), c)
        picked, missing = [], []
        for w in want:
            hit = bykey.get(w) or next((c for c in cities if w in c["name"].lower()), None)
            if hit and hit["q"] not in {p["q"] for p in picked}:
                picked.append(hit)
            elif not hit:
                missing.append(w)
        if missing:
            print(f"  not found in the 1M city list: {', '.join(missing)}")
        cities = picked
        print(f"  restricted to {len(cities)} cities: {', '.join(c['name'] for c in cities)}")
    d0 = date.fromisoformat(a.frm)
    d1 = date.fromisoformat(a.to)
    dates = [d0 + timedelta(days=k) for k in range(0, (d1 - d0).days + 1, a.step)]
    print(f"grid: {len(dates):,} dates x {len(cities):,} cities = {len(dates)*len(cities):,} candidates")

    fixed = {"dob": a.dob, "lat": a.lat, "lon": a.lon}
    results = []
    tmpdir = tempfile.mkdtemp(prefix="aqpred-")
    # Batched by DATE CHUNK with every city in each chunk, not by city. core.load holds seven (6, 18, n)
    # float64 arrays, about 6 kB per candidate, so a batch of 140,000 costs ~0.9 GB — and batching the other
    # way round meant one process start per handful of rows, where the fixed cost of importing the modules
    # and building the blocks dominated everything.
    per_chunk = max(1, a.rows_per_batch // max(1, len(cities)))
    chunks = [dates[i:i + per_chunk] for i in range(0, len(dates), per_chunk)]
    print(f"  {len(chunks)} batches of up to {per_chunk} dates x {len(cities):,} cities")
    for bi, dch in enumerate(chunks, 1):
        rows = candidate_rows(fixed, cities, dch, a.sex)
        cf = os.path.join(tmpdir, f"cand{bi}.json")
        json.dump(rows, open(cf, "w"))
        env = dict(os.environ)
        env.update({"AQ_COUPLES": cf, "AQ_EPHEM_CACHE": os.path.join(tmpdir, f"eph{bi}.npz"),
                    "AQ_OUTDIR": tmpdir, "AQ_BLOCKS": os.path.join(tmpdir, f"blocks{bi}")})
        for k in ("AQ_SUBSAMPLE", "AQ_BALANCE"):
            env.pop(k, None)
        out = subprocess.run(
            [os.path.expanduser("~/.artamatch-venv/bin/python"),
             os.path.join(HERE, "_score_batch.py"), a.model, cf],
            env=env, capture_output=True, text=True, cwd=HERE)
        if out.returncode != 0:
            print(out.stdout[-1200:]); print(out.stderr[-1200:])
            sys.exit(f"scoring failed on batch {bi}")
        results += json.loads(out.stdout.strip().splitlines()[-1])
        os.remove(cf)
        best = max(r["score"] for r in results) if results else 0
        print(f"  batch {bi}/{len(chunks)} · {len(results):,} scored · best so far {best:.4f}", flush=True)

    results.sort(key=lambda r: -r["score"])
    print(f"\n  TOP {a.top} candidate partners\n")
    print(f"  {'#':>3}  {'birth date':<12} {'city':<26} {'country':<18} {'score':>8}")
    print(f"  {'-'*3}  {'-'*12} {'-'*26} {'-'*18} {'-'*8}")
    for k, r in enumerate(results[:a.top], 1):
        print(f"  {k:>3}  {r['date']:<12} {r['city'][:26]:<26} {r['country'][:18]:<18} {r['score']:>8.4f}")
    # Save EVERYTHING, not a top slice. A truncated file cannot answer "how much does the date matter
    # versus the city" — an earlier attempt drew that conclusion from the top 2,000 rows, which held only
    # 46 cities, and got it wrong.
    json.dump(results, open(os.path.join(HERE, "partner-search.json"), "w"))
    print(f"\n  all {len(results):,} scored candidates written to partner-search.json")


if __name__ == "__main__":
    main()
