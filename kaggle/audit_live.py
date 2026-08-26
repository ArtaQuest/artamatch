"""Live Wikidata spot-check: sample shipped couples, refetch both partners from the live API, rebuild dob
rendering, gender order and the remarried-while-both-alive label independently, and compare. Disagreements
are classified by eye afterwards (live edits since the snapshot vs extraction bugs)."""
import json, os, sys, time, urllib.request
import numpy as np, pandas as pd
D = os.path.expanduser("~/.artamatch-dev/remar_sh2")
UA = {"User-Agent": "ArtaMatch-audit/1.0 (research corpus verification)"}

tr = pd.read_csv(f"{D}/train.csv", dtype=str)
ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
tr = pd.concat([tr.reset_index(drop=True), ids.reset_index(drop=True)], axis=1)
pos = tr[tr.ended_in_divorce == "1"]
neg = tr[tr.ended_in_divorce == "0"]
rng = np.random.default_rng(23)
sample = pd.concat([pos.iloc[rng.choice(len(pos), 60, replace=False)],
                    neg.iloc[rng.choice(len(neg), 40, replace=False)]])
qids = sorted(set(sample.pid_a) | set(sample.pid_b))
print(f"  {len(sample)} couples · {len(qids)} persons to fetch live")

ent = {}
for i in range(0, len(qids), 50):
    batch = qids[i:i + 50]
    url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=claims&ids="
           + "|".join(batch))
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    ent.update(j.get("entities", {}))
    time.sleep(1)
print(f"  fetched {len(ent)} entities")

def claims(q, p):
    return ent.get(q, {}).get("claims", {}).get(p, [])

def timeval(sn):
    try:
        return sn["datavalue"]["value"]["time"], sn["datavalue"]["value"]["precision"]
    except Exception:
        return None, None

def render(ts, p):
    if not ts:
        return "0000-00-00"
    import re
    m = re.match(r"^[+-]?(\d{4})-(\d{2})-(\d{2})", ts)
    if not m or m[1] == "0000":
        return "0000-00-00"
    y, mo, d = m.groups()
    if p is None:
        return f"{y}-00-00" if (mo, d) == ("01", "01") else f"{y}-{mo}-{d}"
    if p <= 9:
        return f"{y}-00-00"
    if p == 10:
        return f"{y}-{mo}-00"
    return f"{y}-00-00" if (mo, d) == ("01", "01") else f"{y}-{mo}-{d}"

def person(q):
    dob, dprec = (None, None)
    for c in claims(q, "P569"):
        dob, dprec = timeval(c.get("mainsnak", {}))
        if dob:
            break
    dy = None
    for c in claims(q, "P570"):
        t, _ = timeval(c.get("mainsnak", {}))
        if t and t[1:5].isdigit():
            dy = int(t[1:5]); break
    sex = ""
    for c in claims(q, "P21"):
        try:
            sex = c["mainsnak"]["datavalue"]["value"]["id"]; break
        except Exception:
            pass
    mars = []          # (spouse_qid, start_year or None)
    for c in claims(q, "P26"):
        try:
            sp = c["mainsnak"]["datavalue"]["value"]["id"]
        except Exception:
            sp = ""
        sy = None
        for qq in c.get("qualifiers", {}).get("P580", []):
            t, _ = timeval(qq)
            if t and t[1:5].isdigit():
                sy = int(t[1:5]); break
        mars.append((sp, sy))
    return {"dob": render(dob, dprec), "death": dy, "sex": sex, "mars": mars}

P = {q: person(q) for q in qids}
MALE, FEM = "Q6581097", "Q6581072"
agree = dob_mis = lab_mis = sex_mis = 0
rows = []
for _, r in sample.iterrows():
    pa, pb = r.pid_a, r.pid_b
    A, B = P.get(pa), P.get(pb)
    if not A or not B:
        continue
    ok_sex = (A["sex"] == MALE and B["sex"] == FEM)
    ok_dob = (A["dob"] == r.dob_a and B["dob"] == r.dob_b)
    # collapsed marriage index per spouse
    def collapsed(m):
        d_ = {}
        for sp, sy in m:
            if sy is None:
                continue
            key = sp or f"__unk{sy}"
            d_[key] = min(d_.get(key, 9999), sy)
        return d_
    ca, cb = collapsed(A["mars"]), collapsed(B["mars"])
    s = min(ca.get(pb, 9999), cb.get(pa, 9999))
    if s == 9999:
        live_lab = 0 if (len({sp for sp, _ in A["mars"]}) <= 1 and len({sp for sp, _ in B["mars"]}) <= 1) else None
    else:
        def rem(c, self_spouse, other_death):
            if other_death is None:
                return False
            return any(v > s and v < other_death for k, v in c.items() if k != self_spouse)
        live_lab = int(rem(ca, pb, B["death"]) or rem(cb, pa, A["death"]))
    ship = int(r.ended_in_divorce)
    ok_lab = (live_lab is not None and live_lab == ship)
    agree += ok_sex and ok_dob and ok_lab
    dob_mis += not ok_dob
    sex_mis += not ok_sex
    if live_lab is not None and live_lab != ship:
        lab_mis += 1
        rows.append((pa, pb, ship, live_lab))
print(f"\n  full agreement {agree}/{len(sample)} · dob mismatches {dob_mis} · sex mismatches {sex_mis} · "
      f"label mismatches {lab_mis}")
for pa, pb, s_, l_ in rows[:10]:
    print(f"    LABEL: {pa} x {pb} shipped {s_} live {l_}")

# classify the dob mismatches: multi-valued P569 (rank/pick ambiguity) vs genuine drift
print("\nDOB MISMATCH CLASSIFICATION")
for _, r in sample.iterrows():
    for side_, q, ship in (("a", r.pid_a, r.dob_a), ("b", r.pid_b, r.dob_b)):
        A = P.get(q)
        if not A or A["dob"] == ship:
            continue
        cl = claims(q, "P569")
        ranks = [c.get("rank") for c in cl]
        allr = []
        for c in cl:
            t, pz = timeval(c.get("mainsnak", {}))
            allr.append(render(t, pz))
        match_any = ship in allr
        print(f"  {q:<12} shipped {ship} · live-first {A['dob']} · {len(cl)} P569 claim(s) {ranks} · "
              f"shipped value {'IS one of the live claims' if match_any else 'NOT among live claims (drift/edit)'}")
