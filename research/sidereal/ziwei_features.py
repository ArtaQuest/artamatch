"""
ziwei_features.py — Zi Wei Dou Shu (紫微斗数) features through iztro, for both partners and the pair.

WHAT ZWDS IS, in one paragraph. A Chinese astrolabe of twelve palaces (命宫 life/soul, 兄弟 siblings, 夫妻 SPOUSE,
子女 children, 财帛 wealth, 疾厄 health, 迁移 travel, 交友 friends, 官禄 career, 田宅 property, 福德 spirit,
父母 parents), populated from the LUNAR birth date and the Chinese double-hour with fourteen major stars, fourteen
minor stars and a few dozen adjective stars, each major star with a brightness and possibly one of four annual
mutagens (禄 A, 权 B, 科 C, 忌 D). It is not a zodiac; nothing here is a longitude. The birth hour enters as the
double-hour, and 09:00 local is 巳 (index 5) everywhere on Earth, so this needs no time zone.

The tradition's relationship reading is the SPOUSE PALACE -- its major stars, their brightness, and whether the
malefics sit there -- read against the partner's own life palace. Those crossings are computed explicitly.

DAY PRECISION ONLY. The lunar day changes the whole astrolabe, so a year- or month-only birth gets NaN throughout;
nothing is imputed. iztro converts through lunar-typescript (astronomical, any year), verified against an
independent conversion at 1600, 1850 and 1899.

The `sex` parameter of iztro steers only the direction of the decadal limits (大限), which are not used here; it
is fixed to one value and the dataset reads no sex.
"""
import json
import os
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SCRIPT = os.path.join(HERE, "ziwei_batch.mjs")
PALACES = ["soul", "siblings", "spouse", "children", "wealth", "health", "surface", "friends", "career",
           "property", "spirit", "parents"]                                   # counter-clockwise from the life palace
MAJOR = ["emperor", "advisor", "sun", "general", "fortunate", "judge", "empress", "moon", "wolf", "rebel",
         "minister", "advocator", "marshal", "sage"]                          # iztro's en-US names for the 14
MINOR = ["aide", "artist", "assistant", "driven", "fickle", "helper", "horse", "ideologue", "impulsive", "money",
         "officer", "scholar", "spark", "tangled"]
BRANCH = ["zi", "chou", "yin", "mao", "chen", "si", "wu", "wei", "shen", "you", "xu", "hai"]
CLASS = {"water 2nd": 2, "wood 3rd": 3, "metal 4th": 4, "earth 5th": 5, "fire 6th": 6}
MUT = {"": 0, "A": 1, "B": 2, "C": 3, "D": 4}


def _bright(b):
    try:
        return float(b.strip("[]"))
    except Exception:
        return np.nan


def astrolabes(items):
    """items: list of (id, 'YYYY-MM-DD'). Returns {id: parsed astrolabe or None}. One node process for all."""
    if not items:
        return {}
    payload = "\n".join(json.dumps({"id": i, "date": d, "timeIndex": 5}) for i, d in items) + "\n"
    r = subprocess.run(["node", NODE_SCRIPT], input=payload, capture_output=True, text=True, timeout=3600)
    out = {}
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        out[d["id"]] = d if d.get("ok") else None
    return out


def person(a):
    """Features of one astrolabe dict (from astrolabes()); {} for None."""
    F = {}
    if not a:
        return F
    soul_idx = BRANCH.index(a["soulBranch"]) if a["soulBranch"] in BRANCH else np.nan
    body_idx = BRANCH.index(a["bodyBranch"]) if a.get("bodyBranch") in BRANCH else np.nan
    F["soul_branch"] = float(soul_idx); F["body_branch"] = float(body_idx)
    F["five_class"] = float(CLASS.get(a["fiveElementsClass"], np.nan))
    F["body_palace_offset"] = float((body_idx - soul_idx) % 12) if not (np.isnan(soul_idx) or np.isnan(body_idx)) else np.nan
    # palace order as iztro emits it may start anywhere; index every palace by its NAME's canonical position
    by_name = {p["name"]: p for p in a["palaces"]}
    star_pal = {}
    for pname in PALACES:
        p = by_name.get(pname)
        if p is None:
            continue
        pi = PALACES.index(pname)
        maj = p["major"]; mino = p["minor"]; adj = p["adj"]
        F[f"pal_{pname}_n_major"] = float(len(maj)); F[f"pal_{pname}_n_minor"] = float(len(mino))
        F[f"pal_{pname}_n_adj"] = float(len(adj))
        F[f"pal_{pname}_bright_sum"] = float(sum(_bright(s["brightness"]) for s in maj if s["brightness"])) if maj else 0.0
        F[f"pal_{pname}_has_mut_D"] = float(any(s["mutagen"] == "D" for s in maj + mino))
        F[f"pal_{pname}_has_mut_A"] = float(any(s["mutagen"] == "A" for s in maj + mino))
        F[f"pal_{pname}_branch"] = float(BRANCH.index(p["branch"])) if p["branch"] in BRANCH else np.nan
        for s in maj:
            star_pal[s["name"]] = (pi, _bright(s["brightness"]), MUT.get(s["mutagen"], 0))
        for s in mino:
            star_pal[s["name"]] = (pi, np.nan, MUT.get(s["mutagen"], 0))
        for s in maj:
            F[f"in_{pname}_{s['name']}"] = 1.0
    for st in MAJOR:
        pi, br, mu = star_pal.get(st, (np.nan, np.nan, np.nan))
        F[f"major_{st}_palace"] = float(pi); F[f"major_{st}_bright"] = br; F[f"major_{st}_mutagen"] = float(mu)
    for st in MINOR:
        pi, _, mu = star_pal.get(st, (np.nan, np.nan, np.nan))
        F[f"minor_{st}_palace"] = float(pi); F[f"minor_{st}_mutagen"] = float(mu)
    for pname in PALACES:
        for st in MAJOR:
            F.setdefault(f"in_{pname}_{st}", 0.0)
    return F


def couple(ao, ay):
    """Both partners' features (older_/younger_) plus the crossings the tradition reads."""
    O, Y = person(ao), person(ay)
    F = {f"older_{k}": v for k, v in O.items()}
    F.update({f"younger_{k}": v for k, v in Y.items()})
    if not O or not Y:
        return F
    so, sy = O["soul_branch"], Y["soul_branch"]
    if not (np.isnan(so) or np.isnan(sy)):
        d = (so - sy) % 12
        F["pair_soul_branch_distance"] = float(min(d, 12 - d))
        F["pair_soul_same"] = float(so == sy)
        F["pair_soul_liuhe"] = float((so + sy) % 12 == 1)              # 六合 pairs sum to 1 mod 12 (zi-chou, yin-hai...)
        F["pair_soul_liuchong"] = float(d == 6)                         # 六冲 opposition
        F["pair_soul_sanhe"] = float(d in (4, 8))                       # 三合 trine group
    F["pair_same_class"] = float(O["five_class"] == Y["five_class"]) if not (np.isnan(O["five_class"]) or np.isnan(Y["five_class"])) else np.nan
    # the spouse palace of each against the life palace of the other: shared major stars
    for st in MAJOR:
        a_sp = O.get(f"in_spouse_{st}", 0.0); b_soul = Y.get(f"in_soul_{st}", 0.0)
        b_sp = Y.get(f"in_spouse_{st}", 0.0); a_soul = O.get(f"in_soul_{st}", 0.0)
        F[f"pair_{st}_older_spouse_x_younger_soul"] = float(a_sp * b_soul)
        F[f"pair_{st}_younger_spouse_x_older_soul"] = float(b_sp * a_soul)
    F["pair_spouse_soul_overlap"] = float(sum(O.get(f"in_spouse_{s}", 0) * Y.get(f"in_soul_{s}", 0) for s in MAJOR)
                                          + sum(Y.get(f"in_spouse_{s}", 0) * O.get(f"in_soul_{s}", 0) for s in MAJOR))
    F["pair_spouse_bright_sum"] = O.get("pal_spouse_bright_sum", np.nan) + Y.get("pal_spouse_bright_sum", np.nan)
    F["pair_spouse_mut_D_either"] = float(bool(O.get("pal_spouse_has_mut_D", 0)) or bool(Y.get("pal_spouse_has_mut_D", 0)))
    return F


if __name__ == "__main__":
    A = astrolabes([("o", "1850-06-15"), ("y", "1858-02-03"), ("bad", "1858-00-00")])
    f = couple(A["o"], A["y"])
    print(f"  couple: {len(f)} features · year-only partner astrolabe -> {A['bad']}")
    for k in [k for k in f if k.startswith("pair_")][:8] + ["older_soul_branch", "older_five_class", "older_major_emperor_palace"]:
        print(f"    {k:<44} {f[k]}")
