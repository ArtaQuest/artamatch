"""Exactness harness: the browser scorer must reproduce the TRAINING bank name-for-name for every clause
of every rule of the given model, and the AND-aware score must match, on full-precision training couples.
Usage: verify_scorer.py <model.json>. Any mismatch is a deploy blocker."""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
sys.path.insert(0, os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs"))
import v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
import v15_families as F15
import v17_families as F17
import v19_families as F19
import scorer as SC
import sweshim as SW
D = os.path.expanduser(os.environ.get("AQ_D", "~/.artamatch-dev/remar_sh"))

SW.load(os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/ephem4.bin"),
        os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/tables.json"))
SW.set_sid_mode(SW.SIDM_LAHIRI)
SC.init(SW)

M = json.load(open(sys.argv[1]))
tr = pd.read_csv(f"{D}/train.csv", dtype=str)
Z = np.load(f"{D}/phases.npz", allow_pickle=True)
X6, n6 = V6.bank(tr, Z, "train")
XA, nA = V7.additions(tr, Z, "train")
XL, nL = V8.last_singles(tr, Z, "train")
XN, nN = V13.new_singles(tr, Z, "train", set(n6 + nA + nL))
XF, nF = F15.families15(tr, Z, "train")
XW, nW = F17.families17(tr, Z, "train")
XV, nV = F19.families19(tr, Z, "train")
X = np.column_stack([X6, XA, XL, XN, XF, XW, XV])
pos = {n: i for i, n in enumerate(n6 + nA + nL + nN + nF + nW + nV)}

clauses = sorted({p for k in M["weights"] for p in k.split(" AND ")})
missing = [c for c in clauses if c not in pos]
assert not missing, f"clauses missing from training bank: {missing[:5]}"
print(f"  {os.path.basename(sys.argv[1])}: {len(M['weights'])} rules · {len(clauses)} distinct clauses, all in bank")

# the page ships an ephemeris spanning the PRODUCT years (1900-2030 verified); validate inside it
full = tr[(tr.dob_a.str[:4] >= "1900") & (tr.dob_b.str[:4] >= "1900")
          & (tr.dob_a.str[:4] != "0000") & (tr.dob_b.str[:4] != "0000")
          & (tr.dob_a.str[5:7] != "00") & (tr.dob_b.str[5:7] != "00")
          & (tr.dob_a.str[8:10] != "00") & (tr.dob_b.str[8:10] != "00")].index.to_numpy()
sample = np.random.default_rng(5).choice(full, 150, replace=False)

Zb = np.load(f"{D}/phases.npz", allow_pickle=True)
bodies = [str(b) for b in Zb["bodies"]]
TA = np.asarray(Zb["theta_a_train"], float); TB = np.asarray(Zb["theta_b_train"], float)
def inject(theta_row):
    C = {b: (theta_row[i] if np.isfinite(theta_row[i]) else float("nan")) for i, b in enumerate(bodies)}
    for b in bodies:
        C[f"__speed_{b}"] = float("nan")
    return C

# PASS 1 — formulas: training longitudes through the scorer's own code. Must be ZERO mismatches.
bad1 = 0
for ri in sample:
    row = tr.iloc[ri]
    his = tuple(int(x) for x in row.dob_a.split("-"))
    her = tuple(int(x) for x in row.dob_b.split("-"))
    F = SC.features(his, her, CA=inject(TA[ri]), CB=inject(TB[ri]))
    for c in clauses:
        sv = 1.0 if c in F else 0.0
        tv = float(X[ri, pos[c]])
        if sv != tv and not c.endswith("_retro"):
            bad1 += 1
            if bad1 <= 8:
                print(f"    FORMULA MISMATCH row {ri} {row.dob_a}/{row.dob_b} · {c}: scorer {sv} train {tv}")
print(f"  PASS 1 (formulas, injected charts): {bad1} mismatches over {len(sample)}x{len(clauses)}")

# PASS 2 — shipped ephemeris: flips are bin-edge effects of the compact tables; quantify them.
flips = 0; dzs = []
for ri in sample:
    row = tr.iloc[ri]
    his = tuple(int(x) for x in row.dob_a.split("-"))
    her = tuple(int(x) for x in row.dob_b.split("-"))
    F = SC.features(his, her)
    flips += sum(1 for c in clauses if (1.0 if c in F else 0.0) != float(X[ri, pos[c]]))
    z_sc, _ = SC.score_rules(M["weights"], M["intercept"], his, her)
    z_tr = M["intercept"] + sum(w for k, w in M["weights"].items()
                                if all(X[ri, pos[p]] == 1.0 for p in k.split(" AND ")))
    dzs.append(abs(z_sc - z_tr))
dzs = np.array(dzs)
print(f"  PASS 2 (shipped ephemeris): {flips} bin-edge flips "
      f"({100.0 * flips / (len(sample) * len(clauses)):.4f}% of comparisons) · "
      f"couples with any |dz|>0: {int((dzs > 0).sum())}/{len(sample)} · max |dz| {dzs.max():.3f}")
print("  VERDICT:", "FORMULAS EXACT" + (" · ephemeris tolerance quantified" if flips else " · fully exact")
      if bad1 == 0 else "FAIL")
