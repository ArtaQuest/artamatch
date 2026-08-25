"""Second, denser example pass: for rules still unexampled by the coarse grid, sweep random pairs over
the FULL product date space (any day, any month, 1946-2008). What stays rare after this is genuinely
era-locked, not grid-shadowed."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs"))
import sweshim as SW
SW.load(os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/ephem4.bin"),
        os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/tables.json"))
SW.set_sid_mode(SW.SIDM_LAHIRI)
import scorer
scorer.init(SW)

path = sys.argv[1]
J = json.load(open(path))
need = {r["name"] for r in J["rules"] if r["rare"]}
print(f"  {len(need)} rules entering the dense pass")
charts = {}
def ch(d):
    if d not in charts:
        charts[d] = scorer.chart(*d)
    return charts[d]
rng = np.random.default_rng(17)
found = {}
for i in range(120000):
    if not need:
        break
    da = (int(rng.integers(1946, 2009)), int(rng.integers(1, 13)), int(rng.integers(1, 29)))
    db = (int(rng.integers(1946, 2009)), int(rng.integers(1, 13)), int(rng.integers(1, 29)))
    F = scorer.features(da, db, CA=ch(da), CB=ch(db))
    for n in list(need):
        if all(p in F for p in n.split(" AND ")):
            found[n] = (f"e.g. him born {da[0]:04d}-{da[1]:02d}-{da[2]:02d}, "
                        f"her born {db[0]:04d}-{db[1]:02d}-{db[2]:02d}")
            need.discard(n)
    if (i + 1) % 20000 == 0:
        print(f"    {i+1:,} random pairs · {len(need)} still unexampled", flush=True)
for r in J["rules"]:
    if r["name"] in found:
        r["example"] = found[r["name"]]; r["rare"] = False
rare = sum(1 for r in J["rules"] if r["rare"])
print(f"  recovered {len(found)} · genuinely era-locked: {rare}")
json.dump(J, open(path, "w"), indent=1)
print(f"  updated {path}")
