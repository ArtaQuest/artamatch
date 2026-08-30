"""For each rule of the deployed pair-only model: a no-background explanation, its tradition line(s),
and a concrete example couple (two birth dates in the product window 1946-2008) where the rule fires.
Conjunction rules explain each clause and join them. Usage: explain_pair.py <deploy.json> <out.json>"""
import json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs"))
import sweshim as SW
SW.load(os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/ephem4.bin"),
        os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/tables.json"))
SW.set_sid_mode(SW.SIDM_LAHIRI)
import scorer
scorer.init(SW)

ART = json.load(open(sys.argv[1]))
SIGNF = {"Ari":"Aries","Tau":"Taurus","Gem":"Gemini","Can":"Cancer","Leo":"Leo","Vir":"Virgo","Lib":"Libra",
         "Sco":"Scorpio","Sag":"Sagittarius","Cap":"Capricorn","Aqu":"Aquarius","Pis":"Pisces"}
SIGN12 = list(SIGNF.values())
NAKN = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha",
        "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula",
        "Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada",
        "Uttara Bhadrapada","Revati"]
ASP = {"conj":"conjunct","sext":"sextile","square":"square","trine":"trine","opp":"opposite",
       "quinc":"quincunx (150°)","semisext":"semi-sextile (30°)","quintile":"quintile (72°)",
       "biquintile":"biquintile (144°)","semisquare":"semi-square (45°)","sesquiquadrate":"sesquiquadrate (135°)"}
WD = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
KARANA = ["Kimstughna","Bava","Balava","Kaulava","Taitila","Gara","Vanija","Vishti","Shakuni","Chatushpada","Naga"]
NITYA = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarman","Dhriti","Shula","Ganda",
         "Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi","Vyatipata","Variyana","Parigha","Shiva",
         "Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"]
YONIA = ["Horse","Elephant","Sheep","Serpent","Dog","Cat","Rat","Cow","Buffalo","Tiger","Deer","Monkey",
         "Mongoose","Lion"]
RAJJUN = ["Pada (feet)","Kati (waist)","Nabhi (navel)","Kantha (throat)","Shiro (head)"]
VARNAN = ["Brahmin","Kshatriya","Vaishya","Shudra"]
DLORD = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
PLN = lambda b: {"true_node": "north node"}.get(b, b)
He = lambda t: "His" if t == "his" else "Her"

def tithi_h(i):
    i = int(i)
    if i == 14: return "Purnima (full-moon day)"
    if i == 29: return "Amavasya (new-moon day)"
    return f"{'waxing' if i < 15 else 'waning'} tithi {i % 15 + 1}"

def decan_h(i):
    i = int(i)
    return f"decan {i % 3 + 1} of {SIGN12[i // 3 % 12]}"

def human_clause(n):
    m = re.match(r"(his|her)_(\w+?)_sign=(\w+)$", n)
    if m: return f"{He(m[1])} {PLN(m[2])} in {SIGNF[m[3]]}"
    m = re.match(r"comp_(\w+?)_sign=(\w+)$", n)
    if m: return f"The couple's composite {PLN(m[1])} in {SIGNF[m[2]]}"
    m = re.match(r"comp_(\w+?)_decan=(\d+)$", n)
    if m: return f"The couple's composite {PLN(m[1])} in {decan_h(m[2])}"
    m = re.match(r"dav_(\w+?)_sign=(\w+)$", n)
    if m: return f"The couple's Davison {PLN(m[1])} in {SIGNF[m[2]]}"
    m = re.match(r"dav_(\w+?)_decan=(\d+)$", n)
    if m: return f"The couple's Davison {PLN(m[1])} in {decan_h(m[2])}"
    m = re.match(r"cycle_(\w+)_(\w+)_phase=(\w+)$", n)
    if m: return f"Born in the {SIGNF[m[3]]} phase of the {m[1].title()}–{m[2].title()} cycle"
    m = re.match(r"cycle24_(\w+)_(\w+)=(\d+)$", n)
    if m: return f"Born in half-sign step {int(m[3]) + 1} of 24 of the {m[1].title()}–{m[2].title()} cycle"
    m = re.match(r"cycle36_(\w+)_(\w+)=(\d+)$", n)
    if m: return f"Born with the {m[1].title()}–{m[2].title()} cycle in {decan_h(m[3])}"
    m = re.match(r"(sun|moon|nak|venus|mars)pair=(\w+)x(\w+)$", n)
    if m:
        b = {"sun": "Sun signs", "moon": "Moon signs", "venus": "Venus signs", "mars": "Mars signs",
             "nak": "nakṣatras"}[m[1]]
        if m[1] == "nak": return f"Their {b}: {NAKN[int(m[2])]} × {NAKN[int(m[3])]}"
        return f"Their {b}: {SIGNF[m[2]]} × {SIGNF[m[3]]}"
    m = re.match(r"(his|her)_nakshatra=(\d+)$", n)
    if m: return f"{He(m[1])} Moon in nakṣatra {NAKN[int(m[2]) % 27]}"
    m = re.match(r"(his|her)_moon_pada=(\d+)$", n)
    if m: return f"{He(m[1])} Moon in pāda {int(m[2]) % 4 + 1} of {NAKN[int(m[2]) // 4 % 27]}"
    m = re.match(r"(his|her)_(sun|moon)_decan=(\d+)$", n)
    if m: return f"{He(m[1])} {m[2].title()} in {decan_h(m[3])}"
    m = re.match(r"(his|her)_tithi=(\d+)$", n)
    if m: return f"{He(m[1])} birth on the {tithi_h(m[2])}"
    m = re.match(r"dav_tithi=(\d+)$", n)
    if m: return f"The couple's Davison Moon-phase: {tithi_h(m[1])}"
    m = re.match(r"comp_tithi=(\d+)$", n)
    if m: return f"The couple's composite Moon-phase: {tithi_h(m[1])}"
    m = re.match(r"comp_moon_nakshatra=(\d+)$", n)
    if m: return f"The couple's composite Moon in {NAKN[int(m[1]) % 27]}"
    m = re.match(r"dav_moon_nakshatra=(\d+)$", n)
    if m: return f"The couple's Davison Moon in {NAKN[int(m[1]) % 27]}"
    m = re.match(r"his_(\w+)_(\w+)_her_(\w+)$", n)
    if m and m[2] in ASP: return f"His {PLN(m[1])} {ASP[m[2]]} her {PLN(m[3])}"
    m = re.match(r"(his|her)_(\w+)_(\w+)_(comp|dav)_(\w+)$", n)
    if m and m[3] in ASP:
        kind = "composite" if m[4] == "comp" else "Davison"
        return f"{He(m[1])} {PLN(m[2])} {ASP[m[3]]} the couple's {kind} {PLN(m[5])}"
    m = re.match(r"(his|her)_sunmoon_mid_conj_other_(\w+)$", n)
    if m: return f"{He(m[1])} Sun/Moon midpoint conjunct the other's {PLN(m[2])}"
    m = re.match(r"(his|her)_(\w+)_antiscia_other_(\w+)$", n)
    if m: return f"{He(m[1])} {PLN(m[2])} antiscia (solstice mirror) on the other's {PLN(m[3])}"
    m = re.match(r"(his|her)_(\w+)_combust$", n)
    if m: return f"{He(m[1])} {PLN(m[2])} combust (within 8.5° of the Sun)"
    m = re.match(r"(his|her)_(\w+)_retro$", n)
    if m: return f"{He(m[1])} {PLN(m[2])} retrograde"
    m = re.match(r"(his_moon_her_saturn|her_moon_his_saturn)_house=(\d+)$", n)
    if m:
        a, b = ("his Moon", "her Saturn") if m[1].startswith("his") else ("her Moon", "his Saturn")
        h = int(m[2]) + 1
        tagl = " — the Sade Sati zone" if h in (1, 2, 12) else ""
        return f"{b.capitalize()} {h} sign{'s' if h > 1 else ''} from {a}{tagl}"
    m = re.match(r"(his_moon_her_saturn|her_moon_his_saturn)_sadesati$", n)
    if m:
        a, b = ("his Moon", "her Saturn") if m[1].startswith("his") else ("her Moon", "his Saturn")
        return f"{b.capitalize()} in the Sade Sati zone around {a}"
    m = re.match(r"(his|her)_daystem=(\w+)$", n)
    if m: return f"{He(m[1])} day master {re.sub(r'([A-Z])', r' \\1', m[2]).strip()}"
    m = re.match(r"(his|her)_daybranch=(\w+)$", n)
    if m: return f"{He(m[1])} day branch {m[2]}"
    m = re.match(r"(his|her)_monthbranch=(\w+)$", n)
    if m: return f"{He(m[1])} birth in the {m[2]} month"
    m = re.match(r"(his|her)_year_animal=(\w+)$", n)
    if m: return f"{He(m[1])} year animal {m[2]}"
    m = re.match(r"animalpair=(\w+)x(\w+)$", n)
    if m: return f"Their year animals: {m[1]} × {m[2]}"
    m = re.match(r"branchpair=(\w+)x(\w+)$", n)
    if m: return f"Their day branches: {m[1]} × {m[2]}"
    m = re.match(r"stempair=(\w+)x(\w+)$", n)
    if m: return (f"Their day masters: {re.sub(r'([A-Z])', r' \\1', m[1]).strip()} × "
                  f"{re.sub(r'([A-Z])', r' \\1', m[2]).strip()}")
    m = re.match(r"(his|her)_stem_season=(\w+?)x(\w+)$", n)
    if m: return f"{He(m[1])} day master {re.sub(r'([A-Z])', r' \\1', m[2]).strip()} born in the {m[3]} month"
    m = re.match(r"(his|her)_nayin=(\w+)$", n)
    if m: return f"{He(m[1])} Na Yin element {m[2]}"
    m = re.match(r"nayinpair=(\w+)x(\w+)$", n)
    if m: return f"Their Na Yin elements: {m[1]} × {m[2]}"
    m = re.match(r"kuapair=(\d+)$", n)
    if m: return f"His Kua {int(m[1]) // 9 + 1} × her Kua {int(m[1]) % 9 + 1}"
    m = re.match(r"ninestarpair=(\d+)$", n)
    if m: return f"His Nine Star Ki {int(m[1]) // 9 + 1} × hers {int(m[1]) % 9 + 1}"
    m = re.match(r"yonipair=(\d+)x(\d+)$", n)
    if m: return f"Their yonis: {YONIA[int(m[1])]} × {YONIA[int(m[2])]}"
    m = re.match(r"nadipair=(\w+)x(\w+)$", n)
    if m: return f"Their nāḍīs: {m[1]} × {m[2]}" + (" — the same channel (nāḍī doṣa)" if m[1] == m[2] else "")
    m = re.match(r"ganapair=(\w+)x(\w+)$", n)
    if m: return f"Their gaṇas: {m[1]} × {m[2]}"
    m = re.match(r"rajjupair=(\d+)x(\d+)$", n)
    if m: return f"Their rajjus: {RAJJUN[int(m[1])]} × {RAJJUN[int(m[2])]}"
    m = re.match(r"varnapair=(\d+)x(\d+)$", n)
    if m: return f"Their varṇas: {VARNAN[int(m[1])]} × {VARNAN[int(m[2])]}"
    m = re.match(r"vashyapair=(\d+)x(\d+)$", n)
    if m: return f"Their vaśya classes: {int(m[1]) + 1} × {int(m[2]) + 1}"
    m = re.match(r"tarapair=(\d+)$", n)
    if m: return f"Their tārā counts: {int(m[1]) // 9 + 1} × {int(m[1]) % 9 + 1}"
    m = re.match(r"dashalordpair=(\d+)$", n)
    if m: return f"Their birth daśā lords: {DLORD[int(m[1]) // 9]} × {DLORD[int(m[1]) % 9]}"
    m = re.match(r"(his|her)_karana=(\d+)$", n)
    if m: return f"{He(m[1])} birth karaṇa {KARANA[int(m[2])]}"
    m = re.match(r"(his|her)_nityayoga=(\d+)$", n)
    if m: return f"{He(m[1])} birth yoga {NITYA[int(m[2]) % 27]}"
    m = re.match(r"(his|her)_vara=(\d+)$", n)
    if m: return f"{He(m[1])} birth on a {WD[int(m[2])]}"
    m = re.match(r"varapair=(\d+)$", n)
    if m: return f"Their weekdays: {WD[int(m[1]) // 7]} × {WD[int(m[1]) % 7]}"
    m = re.match(r"(his|her)_lifepath=(\d+)$", n)
    if m: return f"{He(m[1])} life path {m[2]}"
    m = re.match(r"lifepath_pair=(\d+)x(\d+)$", n)
    if m: return f"Their life paths: {m[1]} × {m[2]}"
    m = re.match(r"(his|her)_birthday=(\d+)$", n)
    if m: return f"{He(m[1])} birth on the {int(m[2]) + 1}. of the month"
    m = re.match(r"(his|her)_attitude=(\d+)$", n)
    if m: return f"{He(m[1])} attitude number {int(m[2]) + 1}"
    m = re.match(r"(his|her)_(karmic_debt|master)_day$", n)
    if m: return f"{He(m[1])} birth on a {'karmic-debt' if m[2] == 'karmic_debt' else 'master-number'} day"
    m = re.match(r"gap_years=(\d+)$", n)
    if m: return f"An age gap of {m[1]} year{'s' if m[1] != '1' else ''}"
    if n == "gap_369_taboo": return "An age gap of 3, 6 or 9 years (the Chinese gap taboo)"
    if n == "same_birthday": return "Born on the same day of the same month"
    if n == "same_birth_month": return "Born in the same month"
    m = re.match(r"(his|her)_atmakaraka=(\w+)$", n)
    if m: return f"{He(m[1])} Ātmakāraka is {PLN(m[2])}"
    m = re.match(r"(his|her)_darakaraka=(\w+)$", n)
    if m: return f"{He(m[1])} Dārakāraka (spouse significator) is {PLN(m[2])}"
    m = re.match(r"(his|her)_darakaraka_sign=(\w+)$", n)
    if m: return f"{He(m[1])} Dārakāraka in {SIGNF[m[2]]}"
    m = re.match(r"(sun|moon|venus)_elempair=(\w+)x(\w+)$", n)
    if m: return f"His {m[1].title()} in a {m[2]} sign, hers in {'an' if m[3] in ('Earth','Air') else 'a'} {m[3]} sign"
    m = re.match(r"(sun|moon|venus)_modepair=(\w+)x(\w+)$", n)
    if m: return f"His {m[1].title()} in a {m[2]} sign, hers in a {m[3]} sign"
    m = re.match(r"(sun|moon|venus)_polpair=(\w+)x(\w+)$", n)
    if m: return f"His {m[1].title()} in a {m[2]} sign, hers in a {m[3]} sign"
    m = re.match(r"comp_(\w+)_(conj|square|opp|trine)_(\w+)$", n)
    if m: return f"The couple's composite {PLN(m[1])} {ASP[m[2]]} composite {PLN(m[3])}"
    m = re.match(r"kuta_(varna|vashya|tara|yoni|maitri|gana|bhakoot|nadi)=(\d+)$", n)
    if m:
        KM = {"varna": "Varṇa", "vashya": "Vaśya", "tara": "Tārā", "yoni": "Yoni", "maitri": "Graha Maitrī",
              "gana": "Gaṇa", "bhakoot": "Bhakūṭa", "nadi": "Nāḍī"}
        return f"{KM[m[1]]} kūṭa scores {m[2]} points"
    m = re.match(r"guna_total=(\d+)$", n)
    if m: return f"Guṇa Milan total: {m[1]} of 36 points"
    m = re.match(r"guna_band=(\w+)$", n)
    if m:
        return {"under18_rejected": "Guṇa Milan under 18 — classically rejected",
                "18to24_acceptable": "Guṇa Milan 18–24 — classically acceptable",
                "25to32_good": "Guṇa Milan 25–32 — classically good",
                "33plus_excellent": "Guṇa Milan 33+ — classically excellent"}[m[1]]
    m = re.match(r"mangal_(moon|venus)=(\w+)$", n)
    if m:
        who = {"neither": "neither is Manglik", "her_only": "she alone is Manglik",
               "his_only": "he alone is Manglik", "both": "both are Manglik"}[m[2]]
        return f"Mangal doṣa (Mars from the {m[1].title()}): {who}"
    m = re.match(r"(moon|venus)_d9pair=(\w+)x(\w+)$", n)
    if m: return f"Navāṁśa (D9) {m[1].title()} signs: {SIGNF[m[2]]} × {SIGNF[m[3]]}"
    m = re.match(r"(moon|venus)_h7pair=(\w+)x(\w+)$", n)
    if m: return f"7th-harmonic {m[1].title()} signs: {SIGNF[m[2]]} × {SIGNF[m[3]]}"
    m = re.match(r"(year|day)_branch_rel=(\w+)$", n)
    if m:
        RW = {"Clash": "clash (Liu Chong)", "Punishment": "punishment (Xing)", "Harm": "harm (Liu Hai)",
              "Break": "break (Po)", "SixHarmony": "six-harmony (Liu He)", "Trine": "trine (San He)",
              "Same": "the same branch", "None": "no named relation"}
        return f"Their {m[1]}-pillar branches form {RW[m[2]]}"
    m = re.match(r"(daymaster|nayin|year_elem)_rel=(\w+)$", n)
    if m:
        RW = {"Same": "share one element", "HeFeedsHer": "his element feeds hers",
              "SheFeedsHim": "her element feeds his", "HeControlsHer": "his element controls hers",
              "SheControlsHim": "her element controls his", "None": "stand apart"}
        base = {"daymaster": "day masters", "nayin": "Na Yin elements", "year_elem": "year elements"}[m[1]]
        return f"Their {base} {RW[m[2]]}"
    if n == "stem_he_combo": return "Their day stems form one of the five combinations (He)"
    if n == "vedha_pair": return "Their nakṣatras form a Vedha (mutual obstruction) pair"
    if n == "mahendra": return "Mahendra: his star counted from hers falls on a supportive count"
    if n == "stridirgha": return "Strīdīrgha: his star lies more than 13 counts from hers"
    m = re.match(r"(his|her)_(\w+)_from_other_moon=(\d+)$", n)
    if m: return f"{He(m[1])} {PLN(m[2])} in the {int(m[3]) + 1}. sign from the other's Moon"
    m = re.match(r"tithiclass_pair=(\w+)x(\w+)$", n)
    if m: return f"Their tithi classes: {m[1]} × {m[2]}"
    m = re.match(r"tithi_distance=(\d+)$", n)
    if m: return f"Their birth Moon-phases lie {m[1]} tithis apart"
    m = re.match(r"his_sun_her_moon_pair=(\w+)x(\w+)$", n)
    if m: return f"His Sun {SIGNF[m[1]]} × her Moon {SIGNF[m[2]]}"
    m = re.match(r"his_moon_her_sun_pair=(\w+)x(\w+)$", n)
    if m: return f"His Moon {SIGNF[m[1]]} × her Sun {SIGNF[m[2]]}"
    m = re.match(r"his_venus_her_mars_pair=(\w+)x(\w+)$", n)
    if m: return f"His Venus {SIGNF[m[1]]} × her Mars {SIGNF[m[2]]}"
    m = re.match(r"his_mars_her_venus_pair=(\w+)x(\w+)$", n)
    if m: return f"His Mars {SIGNF[m[1]]} × her Venus {SIGNF[m[2]]}"
    m = re.match(r"mercurypair=(\w+)x(\w+)$", n)
    if m: return f"Their Mercury signs: {SIGNF[m[1]]} × {SIGNF[m[2]]}"
    m = re.match(r"her_(\w+)_from_his_\w+=(\d+)$", n)
    if m: return f"Her {m[1].title()} in the {int(m[2]) + 1}. sign from his"
    m = re.match(r"his_(sun|moon)elem_her_(sun|moon)elem=(\w+)x(\w+)$", n)
    if m: return f"His {m[1].title()} in a {m[3]} sign, her {m[2].title()} in {'an' if m[4] in ('Earth','Air') else 'a'} {m[4]} sign"
    m = re.match(r"year_stempair=(\w+)x(\w+)$", n)
    if m: return (f"Their year stems: {re.sub(r'([A-Z])', r' \\1', m[1]).strip()} × "
                  f"{re.sub(r'([A-Z])', r' \\1', m[2]).strip()}")
    m = re.match(r"year_nayinpair=(\w+)x(\w+)$", n)
    if m: return f"Their year Na Yin elements: {m[1]} × {m[2]}"
    m = re.match(r"(his|her)_personal_year_in_(hers|his)=(\d+)$", n)
    if m: return f"{He(m[1])} personal year in the other's birth year: {int(m[3]) + 1}"
    m = re.match(r"bio_(physical|emotional|intellectual)=(\d+)$", n)
    if m:
        L = {"physical": 23, "emotional": 28, "intellectual": 33}[m[1]]
        return f"Biorhythm: their {m[1]} cycles sit {m[2]} of {L} days apart"
    m = re.match(r"eastwest_pair=(\w+)x(\w+)$", n)
    if m: return f"Feng-shui groups: {m[1]} × {m[2]}".replace("x", " × ")
    m = re.match(r"draconic_(sun|moon)pair=(\w+)x(\w+)$", n)
    if m: return f"Draconic {m[1].title()} signs: {SIGNF[m[2]]} × {SIGNF[m[3]]}"
    m = re.match(r"(his|her)_(\w+)_contrantiscia_other_(\w+)$", n)
    if m: return f"{He(m[1])} {PLN(m[2])} contra-antiscia (equinox mirror) on the other's {PLN(m[3])}"
    m = re.match(r"retro_(\w+)_pair=(\w+)$", n)
    if m:
        who = {"neither": "neither born under it", "her_only": "she alone born under it",
               "his_only": "he alone born under it", "both": "both born under it"}[m[2]]
        return f"{m[1].title()} retrograde: {who}"
    m = re.match(r"his_(\w+)_exactconj_her_(\w+)$", n)
    if m: return f"His {PLN(m[1])} exactly conjunct her {PLN(m[2])} (within one degree)"
    m = re.match(r"(gandanta_moon|vargottama_moon|vargottama_venus|combust_venus)_pair=(\w+)$", n)
    if m:
        base = {"gandanta_moon": "Moon in gaṇḍānta (the karmic knot)",
                "vargottama_moon": "Moon vargottama (same sign in D1 and D9)",
                "vargottama_venus": "Venus vargottama",
                "combust_venus": "Venus combust"}[m[1]]
        who = {"neither": "neither", "her_only": "hers only", "his_only": "his only", "both": "both"}[m[2]]
        return f"{base}: {who}"
    m = re.match(r"tzolkin_signpair=(\d+)$", n)
    if m:
        TZ = ["Imix","Ik","Akbal","Kan","Chicchan","Cimi","Manik","Lamat","Muluc","Oc","Chuen","Eb",
              "Ben","Ix","Men","Cib","Caban","Etznab","Cauac","Ahau"]
        v = int(m[1]); return f"Their Tzolkin day-signs: {TZ[v // 20]} × {TZ[v % 20]}"
    m = re.match(r"tzolkin_dist=(\d+)$", n)
    if m: return f"Their Tzolkin day-signs sit {m[1]} of 20 apart" + (" — the antipode" if m[1] == "10" else "")
    m = re.match(r"xiu_dist=(\d+)$", n)
    if m: return f"Their birth mansions (28 xiù) sit {m[1]} apart"
    m = re.match(r"ninestar_monthpair=(\d+)$", n)
    if m: return f"His Nine-Star month star {int(m[1]) // 9 + 1} × hers {int(m[1]) % 9 + 1}"
    m = re.match(r"attitude_pair=(\d+)$", n)
    if m: return f"Their attitude numbers: {int(m[1]) // 9 + 1} × {int(m[1]) % 9 + 1}"
    return n

FAMWHAT = [
 (r"^cycle(24|36)?_", "The slow outer planets circle each other over decades to centuries (Barbault's mundane cycles). The phase both partners were born under is their shared era — read here at sign, half-sign or decan grain."),
 (r"^comp_\w+_(sign|decan)|^comp_(tithi|moon_nakshatra)", "The composite chart (Ebertin): midpoint of the two charts, planet by planet — read as the chart of the relationship itself."),
 (r"^dav_", "The Davison chart: a real chart cast for the moment and place midway between the births — the relationship's own horoscope."),
 (r"^his_\w+_(conj|sext|square|trine|opp|quinc|semisext|quintile|biquintile|semisquare|sesquiquadrate)_her_", "Synastry: the angle between his planet and her planet. Conjunct = together; sextile 60°, square 90°, trine 120°, opposition 180°; the minors (30°, 45°, 72°, 135°, 144°, 150°) are Kepler's and Ebertin's finer harmonics."),
 (r"_(comp|dav)_\w+$", "A partner's natal planet in aspect to the couple's own derived chart (composite/Davison) — Hand's composite technique."),
 (r"sunmoon_mid", "Cosmobiology's marriage point: the midpoint of one's Sun and Moon, met by the other's planet."),
 (r"antiscia", "Antiscia: two points mirrored across the solstice axis behave as a hidden conjunction (Hellenistic doctrine)."),
 (r"combust", "Combustion: a planet swallowed by the Sun's rays (within 8.5°) is weakened in classical astrology."),
 (r"retro", "A planet moving backwards through the zodiac at birth."),
 (r"sadesati|_house=", "Sade Sati: Saturn transiting the 12th, 1st and 2nd signs around the Moon is Vedic astrology's famous seven-and-a-half-year trial — here read between the partners' charts."),
 (r"^(his|her)_\w+_sign=", "Where a planet sat in the sidereal zodiac at birth (Lahiri ayanāṁśa). Slow planets stay in one sign for years, so this partly reads a generation."),
 (r"^(sun|moon)pair=", "The classic his-sign × her-sign compatibility table, all 144 cells, learned from history instead of folklore."),
 (r"^(venus|mars)pair=", "The same pair table for the marriage planets: his Venus/Mars sign against hers."),
 (r"^nakpair=|nakshatra", "The 27 lunar mansions (nakṣatras) — the backbone of Vedic matching."),
 (r"pada", "Nakṣatra pādas: each mansion split in four."),
 (r"decan", "The 36 decans: each sign split in three — the tradition's finer grain."),
 (r"tithi", "The Moon-phase day (tithi), one of the five limbs of the Indian almanac."),
 (r"karana", "The karaṇa: half a tithi — eleven of them, seven moving and four fixed. Viṣṭi is avoided for beginnings."),
 (r"nityayoga", "The nitya yoga: the 27-fold sum of Sun and Moon longitudes, third limb of the pañcāṅga."),
 (r"vara", "The weekday of birth (vāra) — each day belongs to a planet."),
 (r"yonipair", "Yoni kūṭa: each nakṣatra has an animal nature; the pairing is matched for instinctive compatibility."),
 (r"nadipair", "Nāḍī kūṭa: the three pulse-channels. The same nāḍī for both is the gravest doṣa in Vedic matching."),
 (r"ganapair", "Gaṇa kūṭa: deva, manuṣya and rākṣasa temperaments paired."),
 (r"rajjupair", "Rajju kūṭa: the nakṣatras strung on five body-ropes; matching ropes are avoided."),
 (r"varnapair", "Varṇa kūṭa: the four classes assigned to Moon signs."),
 (r"vashyapair", "Vaśya kūṭa: which Moon signs hold sway over which."),
 (r"tarapair", "Tārā kūṭa: counting each partner's star from the other's, reduced to nine."),
 (r"dashalordpair", "Each birth nakṣatra belongs to a Vimśottarī daśā lord; the two lords are paired."),
 (r"daystem|stempair|stem_season", "BaZi: the day pillar's heavenly stem is the day master; its element against the birth season or the partner's stem is core Chinese matching."),
 (r"daybranch|branchpair|monthbranch", "BaZi: the earthly branches of the day and month pillars — the animal signs of Chinese astrology."),
 (r"year_animal|animalpair", "The Chinese year animal and the almanac's favourable/clashing pairings."),
 (r"nayin", "Na Yin: the sixty-cycle's poetic element names, five per pillar pair."),
 (r"kuapair", "Feng-shui Kua numbers from the birth year (Li Chun cut-off), his against hers — East/West group matching."),
 (r"ninestarpair", "Nine Star Ki: the year star of Japanese/Chinese nine-star astrology, paired."),
 (r"lifepath", "Numerology's life path: all digits of the birth date reduced to one number."),
 (r"birthday", "Numerology's birthday number: the day of the month itself."),
 (r"attitude", "Numerology's attitude number: day plus month, reduced."),
 (r"karmic_debt|master_day", "Numerology's karmic-debt days (13, 14, 16, 19) and master days (11, 22)."),
 (r"gap_", "The age gap itself — the slowest 'aspect' of all: the phase difference of the two birth moments."),
 (r"same_birth", "Born on the same day or month — calendar synastry."),
 (r"atmakaraka|darakaraka", "Jaimini astrology: the planet with the highest degree in its sign is the soul significator (Ātmakāraka), the lowest the spouse significator (Dārakāraka)."),
 (r"elempair|sunelem|moonelem", "The four elements of the signs (fire, earth, air, water) paired between the partners."),
 (r"^kuta_|^guna_", "Guṇa Milan: the Vedic 36-point match score — eight kūṭas (varṇa 1, vaśya 2, tārā 3, yoni 4, maitrī 5, gaṇa 6, bhakūṭa 7, nāḍī 8) summed; under 18 is classically rejected."),
 (r"^mangal_", "Mangal (Kuja) doṣa: Mars in the 1st, 2nd, 4th, 7th, 8th or 12th from the Moon marks a Manglik; tradition matches Manglik with Manglik."),
 (r"_d9pair", "The navāṁśa (D9): the ninth divisional chart, read above all for marriage."),
 (r"_h7pair", "The 7th harmonic (Addey): the chart multiplied by seven, the harmonic of union."),
 (r"_branch_rel", "The Chinese almanac's branch relations: six harmonies, trines, clashes, harms, punishments and breaks between the pillars."),
 (r"_rel=|stem_he_combo", "The five-element cycle between the two pillars: feeding (sheng), controlling (ke), or the five stem combinations."),
 (r"vedha|mahendra|stridirgha", "Further nakṣatra tests of the Vedic match: Vedha obstruction pairs, the Mahendra counts, Strīdīrgha distance."),
 (r"_from_other_moon", "Chandra-lagna overlay: the partner's planet counted from one's Moon sign, house by house."),
 (r"tithiclass|tithi_distance", "The tithi classes (Nandā, Bhadrā, Jayā, Riktā, Pūrṇā) and the distance between the two birth Moon-phases."),
 (r"his_sun_her_moon|his_moon_her_sun", "The luminary exchange: his Sun against her Moon and the reverse — the classical marriage axis."),
 (r"venus_her_mars|mars_her_venus", "The Venus–Mars cross: the attraction polarity between the charts."),
 (r"mercurypair", "The Mercury pair: how the two minds meet, sign against sign."),
 (r"_from_his_", "Whole-sign distance between the same planet in the two charts."),
 (r"year_stempair|year_nayin", "The year pillar: the birth years' heavenly stems and their Na Yin elements, paired."),
 (r"personal_year", "Numerology's personal-year cycle, each partner's year read in the other's birth year."),
 (r"^bio_", "Biorhythm matching: the 23-, 28- and 33-day cycles started at birth; the offset between two people is fixed for life."),
 (r"eastwest", "Feng-shui East/West group matching, from the Kua numbers."),
 (r"draconic_", "The draconic zodiac: each chart referred to its own lunar node — read for soul-level affinity."),
 (r"contrantiscia", "Contra-antiscia: points mirrored across the equinox axis, the second of the two classical mirrors."),
 (r"^retro_", "A planet moving backwards at birth — natal retrogrades, Venus above all, are read for how one loves."),
 (r"exactconj", "Graha yuddha: two planets within one degree are at war — the tightest contact there is."),
 (r"gandanta", "Gaṇḍānta: the knots where water signs give way to fire — junctions the tradition treats with awe."),
 (r"vargottama", "Vargottama: the same sign in the birth chart and the navāṁśa — a planet standing firm."),
 (r"tzolkin", "The Mayan Tzolkin: the 260-day sacred round, day-sign against day-sign."),
 (r"xiu_dist", "The 28 lunar mansions of the Chinese almanac, counted between the two birth days."),
 (r"ninestar_month", "Nine Star Ki, one level finer: the month star each partner was born under."),
 (r"attitude_pair", "Numerology's attitude numbers (day plus month), paired."),
 (r"modepair", "The three modes (cardinal, fixed, mutable) paired between the partners."),
 (r"polpair", "The yang/yin polarity of the signs paired between the partners."),
]

def whats(name):
    out = []
    for p in name.split(" AND "):
        for pat, txt in FAMWHAT:
            if re.search(pat, p):
                if txt not in out:
                    out.append(txt)
                break
    return out

def main():
    W = ART["weights"]
    dates = [(y, mth, 15) for y in range(1946, 2009) for mth in (1, 4, 7, 10)]
    charts = {d: scorer.chart(*d) for d in dates}
    rng = np.random.default_rng(9)
    need = dict(W)
    example = {}
    order = rng.permutation(len(dates) * len(dates))
    nd = len(dates)
    checked = 0
    for oi in order:
        if not need:
            break
        da, db = dates[oi // nd], dates[oi % nd]
        F = scorer.features(da, db, CA=charts[da], CB=charts[db])
        checked += 1
        for n in list(need):
            if all(p in F for p in n.split(" AND ")):
                example[n] = (f"e.g. him born {da[0]:04d}-{da[1]:02d}-{da[2]:02d}, "
                              f"her born {db[0]:04d}-{db[1]:02d}-{db[2]:02d}")
                del need[n]
        if checked % 8000 == 0:
            print(f"    scanned {checked:,} pairs · {len(need)} rules still unexampled", flush=True)
        if checked >= 60000:
            break
    out = []
    for n, w in sorted(W.items(), key=lambda kv: -kv[1]):
        clauses = n.split(" AND ")
        out.append({"name": n, "weight": w,
                    "human": " AND ".join(human_clause(c) for c in clauses),
                    "clauses": [human_clause(c) for c in clauses],
                    "what": whats(n),
                    "example": example.get(n),
                    "rare": n not in example})
    unt = [r["name"] for r in out if any(h == c for h, c in zip(r["clauses"], r["name"].split(" AND ")))]
    rare = sum(1 for r in out if r["rare"])
    print(f"  {len(out)} rules · {rare} rare (no example among living-era pairs) · untranslated {len(unt)}")
    for u in unt[:10]:
        print("    UNTRANSLATED:", u)
    json.dump({"meta": {k: ART[k] for k in ("model","alpha","cv_auc","test_auc_research","trained_on",
                                            "base_rate","intercept")},
               "calibration_isotonic": ART.get("calibration_isotonic"),
               "calibration_deciles": ART.get("calibration_deciles"), "rules": out},
              open(sys.argv[2], "w"), indent=1)
    print(f"  saved {sys.argv[2]}")

if __name__ == "__main__":
    main()
