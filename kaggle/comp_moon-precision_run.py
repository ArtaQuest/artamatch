"""comp_moon-precision_run.py — the Kaggle translation of the moon-precision entry's ONE chained command:
three configs of comp_moon-precision.py in sequence, identical settings (AQ_KMAX=32 AQ_NOUTER=5
AQ_NO_INNER=1 AQ_ABLATE=1 AQ_ORTHO=1 AQ_ONLY_FAM=XY — overridable from the environment):
  A_MOONCAP   AQ_MOON_KMAX=2                  the entry (Moon phasors k>2 removed before selection)
  B_UNCAPPED  AQ_MOON_KMAX=0                  control: the all-harmonic XY bank
  C_H1ONLY    AQ_MOON_KMAX=0 AQ_ONLY_HARM=1   control: the standing k=1-only XY bank
AQ_DIR comes from run.py (its corpus copy); each config writes ablate_<tag>.json there, which run.py
sweeps into out/. A SUMMARY block at the end re-reads the three jsons so the numbers sit together."""
import glob, json, os, subprocess, sys
D = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
BASE = {"AQ_KMAX": "32", "AQ_NOUTER": "5", "AQ_NO_INNER": "1", "AQ_ABLATE": "1", "AQ_ORTHO": "1", "AQ_ONLY_FAM": "XY"}
CFGS = [("A_MOONCAP", {"AQ_MOON_KMAX": "2"}),
        ("B_UNCAPPED", {"AQ_MOON_KMAX": "0"}),
        ("C_H1ONLY", {"AQ_MOON_KMAX": "0", "AQ_ONLY_HARM": "1"})]
HERE = os.path.dirname(os.path.abspath(__file__))
rcs = {}
for lab, extra in CFGS:
    e = dict(os.environ)
    for k, v in BASE.items(): e.setdefault(k, v)
    e.pop("AQ_ONLY_HARM", None)          # only C narrows the ladder; never inherit it into A/B
    e.update(extra)
    print(f"=== {lab} " + " ".join(f"{k}={e[k]}" for k in sorted(e) if k.startswith("AQ_")), flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, "comp_moon-precision.py")], env=e)
    rcs[lab] = r.returncode
    print(f"=== {lab} rc={r.returncode}", flush=True)

print("=== SUMMARY (moon-precision)", flush=True)
for lab, suffix in (("A_MOONCAP", "onlyXY_moonk2"), ("B_UNCAPPED", "onlyXY_moonuncapped"), ("C_H1ONLY", "onlyXY_h1only_moonuncapped")):
    fs = sorted(glob.glob(f"{D}/ablate_comp_moon-precision_*_{suffix}.json"))
    if not fs:
        print(f"{lab}: no ablate json (rc={rcs.get(lab)})", flush=True); continue
    a = json.load(open(fs[-1]))
    print(f"{lab}: NESTED {a['nested_auc']:.4f}  WITHIN-ERA {a['within_era_auc']:.4f}  phasors {a['n_phasors']:,}  "
          f"per-fold {[x['fold_auc'] for x in a['per_fold']]}  [{a['tag']}]", flush=True)
sys.exit(max(rcs.values()) if rcs else 1)
