"""For each surviving v6 rule: a no-background explanation and a concrete example (a date, or a couple)
where the rule actually fires — found by scanning real dates through the same ephemeris the page uses."""
import json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs"))
sys.path.insert(0, os.path.expanduser("~/.artaquest-dev/wt/am-pages/web"))
import sweshim as SW
SW.load(os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/ephem4.bin"),
        os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/tables.json"))
SW.set_sid_mode(SW.SIDM_LAHIRI)
import scorer
scorer.init(SW)

ART = json.load(open(os.path.expanduser("~/.artamatch-dev/v6_model.json")))
W = ART["weights"]
SIGNF = {"Ari":"Aries","Tau":"Taurus","Gem":"Gemini","Can":"Cancer","Leo":"Leo","Vir":"Virgo","Lib":"Libra",
         "Sco":"Scorpio","Sag":"Sagittarius","Cap":"Capricorn","Aqu":"Aquarius","Pis":"Pisces"}
NAKN = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha",
        "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula",
        "Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada",
        "Uttara Bhadrapada","Revati"]
FAMWHAT = {
 "sign": "Where a planet sat in the sidereal zodiac at birth. Slow planets stay in one sign for years, so this partly reads the generation someone belongs to.",
 "dav": "The Davison chart: a chart cast for the moment exactly midway between the two births — astrologers read it as the chart of the relationship itself.",
 "cycle": "The slow outer planets meet in cycles lasting decades to centuries. Which phase of the cycle you were both born under marks your shared era.",
 "sunpair": "The classic 'his sign × her sign' compatibility table — every pairing of the twelve, learned from history instead of folklore.",
 "moonpair": "The Vedic version of the pair table, using the Moon's sign (rāśi) of each partner.",
 "nakpair": "The 27 lunar mansions (nakṣatras) paired bride × groom — the finest grid in Vedic matching.",
 "nak": "The Moon's lunar mansion at birth — the 27 nakṣatras are the backbone of Vedic marriage matching.",
 "tithi": "The Moon-phase day of birth (1–30), one of the five limbs of the Indian almanac.",
 "contact": "A synastry aspect: the angle between his planet and her planet. Conjunct=together, square=90°, trine=120°, opposite=180°.",
 "daystem": "The BaZi day master: the element of the Chinese day pillar someone was born on.",
 "daybranch": "The branch of the Chinese day pillar — the day's animal sign.",
 "branchpair": "His day-branch against hers — the Chinese almanac reads certain pairs as clashing or harmonising.",
 "stempair": "His day-master element against hers — the five-element relation of the two day pillars.",
 "animal": "The Chinese year animal — the twelve-year cycle.",
 "animalpair": "His year animal against hers — the pairings every Chinese almanac lists as favourable or clashing.",
 "lifepath": "Numerology's life path: all digits of the birth date reduced to one number.",
 "lifepath_pair": "His life path against hers — the numerology pairing grids.",
 "decan": "The 36 decans: each sign split in three — the tradition's finer grain.",
 "pada": "Nakṣatra pādas: each lunar mansion split in four.",
 "cycle24": "The same outer-planet cycle, read at half-sign resolution.",
 "dav_moon_nakshatra": "The Davison Moon's lunar mansion — the couple's own nakṣatra."}


def fam_of(n):
    for k in ("dav_moon_nakshatra","cycle24","decan","pada","cycle","dav","sunpair","moonpair","nakpair",
              "branchpair","stempair","animalpair","lifepath_pair","daystem","daybranch","animal","lifepath",
              "nakshatra","tithi"):
        if k in n:
            return {"nakshatra":"nak"}.get(k,k)
    if re.match(r"his_\w+_(conj|sext|square|trine|opp)_her_", n): return "contact"
    if "_sign=" in n: return "sign"
    return "sign"


def human(n):
    h = {"conj":"conjunct","sext":"sextile","square":"square","trine":"trine","opp":"opposite"}
    m = re.match(r"(his|her)_(\w+?)_sign=(\w+)$", n)
    if m: return f"{'His' if m[1]=='his' else 'Her'} {m[2].replace('true_node','north node')} in {SIGNF[m[3]]}"
    m = re.match(r"dav_(\w+?)_sign=(\w+)$", n)
    if m: return f"The couple's {m[1]} in {SIGNF[m[2]]} (Davison)"
    m = re.match(r"cycle_(\w+)_(\w+)_phase=(\w+)$", n)
    if m: return f"{m[1].title()}–{m[2].title()} era phase in {SIGNF[m[3]]}"
    m = re.match(r"cycle24_(\w+)_(\w+)=(\d+)$", n)
    if m: return f"{m[1].title()}–{m[2].title()} cycle, half-sign {int(m[3])+1} of 24"
    m = re.match(r"sunpair=(\w+)x(\w+)$", n)
    if m: return f"Sun signs {SIGNF[m[1]]} × {SIGNF[m[2]]}"
    m = re.match(r"moonpair=(\w+)x(\w+)$", n)
    if m: return f"Moon signs {SIGNF[m[1]]} × {SIGNF[m[2]]}"
    m = re.match(r"nakpair=(\d+)x(\d+)$", n)
    if m: return f"Nakṣatras {NAKN[int(m[1])]} × {NAKN[int(m[2])]}"
    m = re.match(r"(his|her)_nakshatra=(\d+)$", n)
    if m: return f"{'His' if m[1]=='his' else 'Her'} nakṣatra {NAKN[int(m[2])%27]}"
    m = re.match(r"(his|her)_moon_pada=(\d+)$", n)
    if m: return f"{'His' if m[1]=='his' else 'Her'} Moon in pāda {int(m[2])%4+1} of {NAKN[int(m[2])//4%27]}"
    m = re.match(r"(his|her)_(sun|moon)_decan=(\d+)$", n)
    if m: return f"{'His' if m[1]=='his' else 'Her'} {m[2]} in decan {int(m[3])%3+1} of {SIGNF[list(SIGNF)[int(m[3])//3%12]]}"
    m = re.match(r"(his|her)_tithi=(\d+)$", n)
    if m: return f"{'His' if m[1]=='his' else 'Her'} birth tithi {int(m[2])+1}"
    m = re.match(r"his_(\w+)_(conj|sext|square|trine|opp)_her_(\w+)$", n)
    if m: return f"His {m[1]} {h[m[2]]} her {m[3]}"
    m = re.match(r"(his|her)_daystem=(\w+)$", n)
    if m: return f"{'His' if m[1]=='his' else 'Her'} day master {re.sub(r'([A-Z])',r' \\1',m[2]).strip()}"
    m = re.match(r"(his|her)_daybranch=(\w+)$", n)
    if m: return f"{'His' if m[1]=='his' else 'Her'} day branch {m[2]}"
    m = re.match(r"(his|her)_year_animal=(\w+)$", n)
    if m: return f"{'His' if m[1]=='his' else 'Her'} year animal {m[2]}"
    m = re.match(r"animalpair=(\w+)x(\w+)$", n)
    if m: return f"Year animals {m[1]} × {m[2]}"
    m = re.match(r"branchpair=(\w+)x(\w+)$", n)
    if m: return f"Day branches {m[1]} × {m[2]}"
    m = re.match(r"stempair=(\w+)x(\w+)$", n)
    if m: return f"Day masters {re.sub(r'([A-Z])',r' \\1',m[1]).strip()} × {re.sub(r'([A-Z])',r' \\1',m[2]).strip()}"
    m = re.match(r"(his|her)_lifepath=(\d+)$", n)
    if m: return f"{'His' if m[1]=='his' else 'Her'} life path {m[2]}"
    m = re.match(r"lifepath_pair=(\d+)x(\d+)$", n)
    if m: return f"Life paths {m[1]} × {m[2]}"
    m = re.match(r"dav_moon_nakshatra=(\d+)$", n)
    if m: return f"The couple's Moon in {NAKN[int(m[1])%27]} (Davison)"
    return n


def main():
    # a pool of charts to search for examples
    pool = []
    for y in range(1935, 2006, 2):
        for mth in (2, 6, 10):
            pool.append((y, mth, 15))
    feats_single = {}
    for d in pool:
        F = scorer.features(d, d)          # his-side features of d, her-side of same d
        feats_single[d] = F
    out = []
    for n, w in ART["weights"].items():
        ex = None
        pair = any(k in n for k in ("pair", "dav", "cycle", "his_") and []) or True
        # single-person rules: search the pool on the right side
        m1 = re.match(r"(his|her)_", n)
        if m1 and "_conj_" not in n and "_sext_" not in n and "_square_" not in n and "_trine_" not in n and "_opp_" not in n:
            side = m1[1]
            for d, F in feats_single.items():
                key = n if side == "his" else n
                probe = scorer.features(d, d)
                if n in probe:
                    ex = f"e.g. someone born {d[0]:04d}-{d[1]:02d}-{d[2]:02d}"
                    break
        if ex is None:
            # couple rules: search pool x pool (coarse) until it fires
            found = False
            for i, da in enumerate(pool[::2]):
                for db in pool[::2]:
                    F = scorer.features(da, db)
                    if n in F:
                        ex = (f"e.g. him born {da[0]:04d}-{da[1]:02d}-{da[2]:02d}, "
                              f"her born {db[0]:04d}-{db[1]:02d}-{db[2]:02d}")
                        found = True; break
                if found: break
        out.append({"name": n, "weight": w, "human": human(n), "family": fam_of(n),
                    "what": FAMWHAT.get(fam_of(n), ""), "example": ex or "rare — no example in the scan"})
        print(f"  {human(n):<52} +{w:.4f}  {out[-1]['example']}", flush=True)
    json.dump({"meta": {k: ART[k] for k in ("model","alpha","cv_auc","test_auc","intercept","n_bank","n_surviving")},
               "calibration_deciles": ART["calibration_deciles"], "rules": out},
              open(os.path.expanduser("~/.artamatch-dev/v6_rules.json"), "w"), indent=1)
    print(f"\n  {len(out)} rules explained with examples -> v6_rules.json")


if __name__ == "__main__":
    main()
