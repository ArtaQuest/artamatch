"""Produce the match-page data: top younger matches for male 1994-02-15 from the FROZEN all-data model,
each with its top named doctrine reasons, phrased for a reader."""
import json, os, re, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal")); sys.path.insert(0,".")
import explain_gam as EG

ART = json.load(open(os.path.expanduser("~/Studio/artamatch/deploy/artamatch_v5/model.json")))
names = list(ART["coefficients"].keys()); co = np.array([ART["coefficients"][n] for n in names]); b0 = ART["intercept"]

SIGNS = {"Ari":"Aries","Tau":"Taurus","Gem":"Gemini","Can":"Cancer","Leo":"Leo","Vir":"Virgo","Lib":"Libra",
         "Sco":"Scorpio","Sag":"Sagittarius","Cap":"Capricorn","Aqu":"Aquarius","Pis":"Pisces"}
NAK = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha",
       "P.Phalguni","U.Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","P.Ashadha",
       "U.Ashadha","Shravana","Dhanishta","Shatabhisha","P.Bhadrapada","U.Bhadrapada","Revati"]
def humanise(nm):
    m = re.match(r"(his|her)_(\w+?)_sign=(\w+)", nm)
    if m: return f"{'His' if m[1]=='his' else 'Her'} {m[2].replace('true_node','north node').title()} in {SIGNS.get(m[3],m[3])}"
    m = re.match(r"dav_(\w+?)_sign=(\w+)", nm)
    if m: return f"The couple's {m[1].title()} in {SIGNS.get(m[2],m[2])} (Davison)"
    m = re.match(r"cycle_(\w+)_(\w+)_phase=(\w+)", nm)
    if m: return f"{m[1].title()}–{m[2].title()} era phase in {SIGNS.get(m[3],m[3])}"
    m = re.match(r"sunpair=(\w+)x(\w+)", nm)
    if m: return f"Sun signs {SIGNS.get(m[1],m[1])} × {SIGNS.get(m[2],m[2])}"
    m = re.match(r"moonpair=(\w+)x(\w+)", nm)
    if m: return f"Moon signs {SIGNS.get(m[1],m[1])} × {SIGNS.get(m[2],m[2])} (rāśi kūṭa)"
    m = re.match(r"(his|her)_nakshatra=(\d+)", nm)
    if m: return f"{'His' if m[1]=='his' else 'Her'} nakṣatra {NAK[int(m[2])%27]}"
    m = re.match(r"(his|her)_tithi=(\d+)", nm)
    if m: return f"{'His' if m[1]=='his' else 'Her'} janma tithi {int(m[2])}"
    m = re.match(r"his_(\w+)_(conj|sext|square|trine|opp)_her_(\w+)", nm)
    if m:
        A={"conj":"conjunct","sext":"sextile","square":"square","trine":"trine","opp":"opposite"}[m[2]]
        return f"His {m[1].title()} {A} her {m[3].title()}"
    m = re.match(r"(his|her)_daystem=(\w+)", nm)
    if m: return f"{'His' if m[1]=='his' else 'Her'} BaZi day master {re.sub(r'([A-Z])',r' \\1',m[2]).strip()}"
    m = re.match(r"(his|her)_daybranch=(\w+)", nm)
    if m: return f"{'His' if m[1]=='his' else 'Her'} day branch {m[2]}"
    m = re.match(r"(his|her)_year_animal=(\w+)", nm)
    if m: return f"{'His' if m[1]=='his' else 'Her'} year animal {m[2]}"
    m = re.match(r"animalpair=(\w+)x(\w+)", nm)
    if m: return f"Year animals {m[1]} × {m[2]}"
    m = re.match(r"(his|her)_lifepath=(\d+)", nm)
    if m: return f"{'His' if m[1]=='his' else 'Her'} life path {m[2]}"
    m = re.match(r"lifepath_pair=(\d+)x(\d+)", nm)
    if m: return f"Life paths {m[1]} × {m[2]}"
    return nm

gridd = os.path.expanduser("~/.artamatch-dev/match100")
df = pd.read_csv(f"{gridd}/train.csv", dtype=str)
Z = np.load(f"{gridd}/phases.npz", allow_pickle=True)
Xg, ng = EG.build(df, Z, "train")
pos = {nm: i for i, nm in enumerate(ng)}
X = np.zeros((len(df), len(names)), np.float32)
for j, nm in enumerate(names):
    i = pos.get(nm)
    if i is not None:
        X[:, j] = Xg[:, i]
z = X @ co + b0
p = 1 / (1 + np.exp(-z))
rows = []
for i in range(len(df)):
    if df.dob_b.iloc[i] <= "1994-02-15":
        continue
    contrib = co * X[i]
    o = np.argsort(contrib)
    favour = [(humanise(names[j]), round(float(contrib[j]), 3)) for j in o[:4] if contrib[j] < -0.03]
    against = [(humanise(names[j]), round(float(contrib[j]), 3)) for j in o[::-1][:2] if contrib[j] > 0.05]
    rows.append({"dob": df.dob_b.iloc[i], "p": round(float(p[i]), 4),
                 "age_gap": 2026 - int(df.dob_b.iloc[i][:4]) - 32 if False else abs(1994 - int(df.dob_b.iloc[i][:4])),
                 "favour": favour, "against": against})
rows.sort(key=lambda r: r["p"])
json.dump({"me": "1994-02-15", "model": ART["model"], "test_auc": ART["test_auc_read_once"],
           "cv_auc": ART["cv_auc"], "n_corpus": ART["corpus"], "rows": rows[:100]},
          open(os.path.expanduser("~/.artamatch-dev/match_page.json"), "w"), indent=1)
print(f"wrote match_page.json · {len(rows)} younger candidates · top: "
      + " · ".join(f"{r['dob']} {r['p']:.1%}" for r in rows[:3]))
print("\n#1 reasons:", json.dumps(rows[0], indent=1)[:600])
