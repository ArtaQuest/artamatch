"""
world2_members_iv.py — the systems still missing after world_members_iv.py.

That module took the calendars and the day-election rules. This one takes the remaining MATCHING algorithms that
are consulted by very large numbers of people and are computable from dates alone — plus the four regional
calendars we had no reader for.

INDIA — the rules a family actually asks about, beyond the 36 points
  MANGAL / KUJA DOṢA   Mars in the 1st, 2nd, 4th, 7th, 8th or 12th from the Moon (and from Venus). After Guṇa
                       Milan this is the single most-consulted rule in Indian marriage, and it carries the classic
                       cancellation: both Maṅglik cancels.
  DAŚAKŪṬA (South)     the four kūṭas the southern reckoning adds to the northern eight — RAJJU (same rajju is
                       the dosha the south weighs heaviest), VEDHA (the afflicting nakṣatra pairs), MAHENDRA and
                       STRĪ DĪRGHA (the counted distances between the two Moons' nakṣatras).
  VIMŚOTTARĪ DAŚĀ      whose planetary period each partner was born in, and which was running on the wedding day.
  TAMIL / MALAYALAM    the sidereal solar month — Āḍi and Mārgaḻi are the months a Tamil wedding is not held in.

EAST ASIA
  KUA / BA ZHAI (八宅)  the gender-dependent kua number, East group {1,3,4,9} against West group {2,6,7,8}, and the
                       eight-relation table between two people — of which YAN NIAN (延年) is literally the
                       longevity-and-relationship relation. Used across China, Vietnam, Malaysia and Singapore.
  NAPEUM OHAENG (납음오행) the sixty-pillar "sound element", which is the core of Korean gunghap (궁합).
  BAZI DAY MASTER (八字) each partner's day stem, and the ten-gods relation between the two day masters.
  BURMESE MAHABOTE     the eight-day planetary week (Wednesday split at noon) and the born-year house.

ELSEWHERE
  AZTEC TONALPOHUALLI  the 260-day count read the Aztec way — its own twenty day-signs, the trecena, the Nine
                       Lords of the Night and the Thirteen Lords of the Day — distinct from the Maya module.
  CELTIC OGHAM         the thirteen-month tree calendar of modern folk astrology.
  NORSE RUNIC          the twenty-four rune half-months.
  COPTIC / ETHIOPIAN   the thirteen-month calendar.
  IGBO FOUR-DAY WEEK   Eke · Orie · Afọ · Nkwọ.
  THERAVĀDA VASSA      the three lunar months of the rains retreat, when no Thai, Lao, Khmer or Burmese wedding
                       is held (named _approx: derived from the lunisolar month, not the Thai civil almanac).
Writes AQ_OUT/world2_members.npz.
"""
import datetime as dt
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from artamodel import auc   # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq9c"); PH = os.environ.get("AQ_PHASES", "/tmp/aq9feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq9sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)

# ── India ─────────────────────────────────────────────────────────────────────────────────────────────────────────
RAJJU = {0: [0, 8, 9, 17, 18, 26], 1: [1, 7, 10, 16, 19, 25], 2: [2, 6, 11, 15, 20, 24], 3: [3, 5, 12, 14, 21, 23], 4: [4, 13, 22]}
RAJJU_ARR = np.full(27, -1, int)
for g, lst in RAJJU.items():
    for n in lst:
        RAJJU_ARR[n] = g
VEDHA = [(0, 17), (1, 16), (2, 15), (3, 14), (4, 13), (5, 12), (6, 20), (7, 19), (8, 18), (9, 26), (10, 25), (11, 24), (21, 23)]
VEDHA_SET = set(VEDHA) | {(b, a) for a, b in VEDHA}
DASHA_LORDS = ["ketu", "venus", "sun", "moon", "mars", "rahu", "jupiter", "saturn", "mercury"]
DASHA_YEARS = np.array([7, 20, 6, 10, 7, 18, 16, 19, 17], float)
# ── East Asia ─────────────────────────────────────────────────────────────────────────────────────────────────────
# 納音五行, the sound element of each of the 30 sexagenary pillar-PAIRS: 0 wood 1 fire 2 earth 3 metal 4 water
NAPEUM = [3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4, 3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4]
# 八宅: for each kua, [Sheng Chi, Tian Yi, Yan Nian, Fu Wei, Ho Hai, Wu Gui, Liu Sha, Chueh Ming] as the OTHER kua
BAZHAI_ROWS = {1: [4, 3, 9, 1, 7, 8, 6, 2], 3: [9, 1, 4, 3, 2, 6, 8, 7], 4: [1, 9, 3, 4, 8, 7, 2, 6], 9: [3, 4, 1, 9, 6, 2, 7, 8],
               2: [8, 7, 6, 2, 3, 4, 9, 1], 6: [7, 8, 2, 6, 4, 3, 1, 9], 7: [6, 2, 8, 7, 1, 9, 4, 3], 8: [2, 6, 7, 8, 9, 1, 3, 4]}
BAZHAI = {a: {b: i for i, b in enumerate(row)} for a, row in BAZHAI_ROWS.items()}
EAST_GROUP = {1, 3, 4, 9}
GEN = {(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)}; OVR = {(0, 2), (2, 4), (4, 1), (1, 3), (3, 0)}
MAHABOTE = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu"]
AZTEC_LORDS_NIGHT = 9; AZTEC_LORDS_DAY = 13


def digitsum(y):
    s = sum(int(c) for c in str(int(y)))
    while s > 9:
        s = sum(int(c) for c in str(s))
    return s


def kua(year, male, month=1, day=1):
    """The Ba Zhai / Gua number. Gender-dependent by construction — the dataset is gendered, so this is well posed.

    The year here is the CHINESE solar year, which turns at Lì Chūn (~4 February), not 1 January — a January birth
    carries the previous year's kua. The star itself is an unbroken 9-year cycle, verified against 1864 = 上元甲子
    = 一白; the familiar "10 minus the last two digits" is a 1900s-only mnemonic and is wrong before 1900.
    """
    if year <= 0:
        return np.nan
    if (month, day) < (2, 4):
        year -= 1
    s = digitsum(year)
    k = (11 - s) if male else (4 + s)
    k = ((k - 1) % 9) + 1
    if k == 5:
        k = 2 if male else 8
    return float(k)


def vimshottari(nak_frac, at_years):
    """Which mahādaśā lord is running `at_years` after a birth whose Moon sat at nakṣatra fraction `nak_frac`."""
    out = np.full(len(nak_frac), np.nan)
    ok = np.isfinite(nak_frac) & np.isfinite(at_years)
    n = np.nan_to_num(nak_frac); start = (np.floor(n) % 9).astype(int); frac = n - np.floor(n)
    elapsed = DASHA_YEARS[start] * frac                      # how much of the birth lord had already run
    t = np.nan_to_num(at_years) + elapsed
    total = DASHA_YEARS.sum()
    t = t % total
    for i in range(len(out)):
        if not ok[i]:
            continue
        acc = 0.0; j = start[i]
        for _ in range(9):
            acc += DASHA_YEARS[j]
            if t[i] < acc:
                out[i] = j; break
            j = (j + 1) % 9
    return out


def day_extras(dstr):
    """Calendars and day-cycles world_members did not read."""
    if not isinstance(dstr, str) or len(dstr) < 10 or dstr.endswith("-00") or dstr[:4] == "0000":
        return [np.nan] * 12
    try:
        d = dt.date(int(dstr[:4]), int(dstr[5:7]), int(dstr[8:10]))
    except Exception:
        return [np.nan] * 12
    J = d.toordinal() + 1721425
    sx = (J + 49) % 60
    napeum = float(NAPEUM[sx // 2])
    # Aztec tonalpōhualli — the same 260-day engine as the Tzolkʼin, read with the Aztec sign set and lords.
    # The Aztec-to-Maya correlation is genuinely disputed in the scholarship, so the +160 here is an ASSUMED
    # alignment, not a verified one. It costs little: every PAIR feature below is a difference on the cycle and
    # is therefore exactly invariant to the choice, and the single-date features are a relabelling of the same
    # 260 categories (not quite invariant, since the tree splits them as numbers, but close to it). If the
    # correlation is ever settled, changing this constant is the whole fix.
    az = (J - 584283 + 160) % 260
    az_sign = az % 20; az_num = (az % 13) + 1; az_trecena = az // 13
    lord_night = (J % 9) + 1; lord_day = (J % 13) + 1
    igbo = J % 4                                              # Eke · Orie · Afọ · Nkwọ
    ogham = min(12, ((d.timetuple().tm_yday - 1) * 13) // 365)  # 13 tree-months
    rune = min(23, ((d.timetuple().tm_yday - 1) * 24) // 365)   # 24 rune half-months
    try:
        from convertdate import coptic
        cy, cm, cd = coptic.from_gregorian(d.year, d.month, d.day)
    except Exception:
        cm = cd = np.nan
    mahabote_day = d.weekday()                                 # the 8-day Burmese week splits Wednesday; no birth
    return [napeum, float(az_sign), float(az_num), float(az_trecena), float(lord_night), float(lord_day),
            float(igbo), float(ogham), float(rune), float(cm) if cm == cm else np.nan,
            float(cd) if cd == cd else np.nan, float(mahabote_day)]


EXN = ["napeum_ohaeng", "aztec_sign", "aztec_number", "aztec_trecena", "lord_of_night", "lord_of_day",
       "igbo_week", "ogham_month", "rune_halfmonth", "coptic_month", "coptic_day", "mahabote_day"]


def build(df, Z, half):
    bodies = list(Z["bodies"]); s1, s2 = list(Z["slots"])
    A = Z[f"theta_{s1}_{half}"]; B = Z[f"theta_{s2}_{half}"]; W = Z[f"theta_wed_{half}"]
    imoon, imars, iven, isun = (bodies.index(b) for b in ("moon", "mars", "venus", "sun"))
    cols = []; names = []
    NAKD = 360 / 27

    # ── MANGAL / KUJA DOṢA — Mars counted from the Moon, and from Venus
    for tag, C in (("a", A), ("b", B)):
        for ref, rn in ((imoon, "moon"), (iven, "venus")):
            h = np.floor(((C[:, imars] - C[:, ref]) % 360) / 30) + 1
            cols.append(np.column_stack([h, np.where(np.isfinite(h), np.isin(h, [1, 2, 4, 7, 8, 12]).astype(float), np.nan)]))
            names += [f"{tag}_mars_house_from_{rn}", f"{tag}_manglik_from_{rn}"]
    hA = np.floor(((A[:, imars] - A[:, imoon]) % 360) / 30) + 1; hB = np.floor(((B[:, imars] - B[:, imoon]) % 360) / 30) + 1
    mok = np.isfinite(hA) & np.isfinite(hB)                  # np.isin turns NaN into False, so mask explicitly
    ma = np.isin(hA, [1, 2, 4, 7, 8, 12]).astype(float); mb = np.isin(hB, [1, 2, 4, 7, 8, 12]).astype(float)
    cols.append(np.column_stack([np.where(mok, ma * mb, np.nan), np.where(mok, np.abs(ma - mb), np.nan),
                                 np.where(mok, ma + mb, np.nan)]))
    names += ["manglik_both_cancels", "manglik_one_only", "manglik_count"]

    # ── DAŚAKŪṬA — the four southern kūṭas
    na = A[:, imoon] % 360 / NAKD; nb = B[:, imoon] % 360 / NAKD
    # a NaN Moon (a year-only birth date) casts to a garbage int and would silently INDEX the rajju and vedha
    # tables, fabricating a kūṭa for a couple whose Moon we never knew — mask those rows out instead
    moon_ok = np.isfinite(na) & np.isfinite(nb)
    ia = np.floor(np.nan_to_num(na)).astype(int) % 27; ib = np.floor(np.nan_to_num(nb)).astype(int) % 27
    NA = lambda v: np.where(moon_ok, v, np.nan)
    rajju_same = (RAJJU_ARR[ia] == RAJJU_ARR[ib]).astype(float)
    shiro = ((RAJJU_ARR[ia] == 4) & rajju_same.astype(bool)).astype(float)
    vedha = np.array([1.0 if (x, y) in VEDHA_SET else 0.0 for x, y in zip(ia, ib)])
    cnt = ((ib - ia) % 27) + 1; cnt2 = ((ia - ib) % 27) + 1
    mahendra = np.isin(cnt, [4, 7, 10, 13, 16, 19, 22, 25]).astype(float)
    stree = (cnt >= 13).astype(float)
    cols.append(np.column_stack([NA(RAJJU_ARR[ia]), NA(RAJJU_ARR[ib]), NA(rajju_same), NA(shiro), NA(vedha),
                                 NA(cnt), NA(cnt2), NA(mahendra), NA(stree)]))
    names += ["a_rajju", "b_rajju", "rajju_same", "rajju_shiro_dosha", "vedha_dosha", "count_a_to_b", "count_b_to_a",
              "mahendra", "stree_deergha"]

    # ── VIMŚOTTARĪ DAŚĀ — the period each was born in, and the one running at the wedding
    yr = lambda s: pd.to_numeric(s.str[:4], errors="coerce").to_numpy(dtype=float)
    ya, yb, ys = yr(df.dob_a), yr(df.dob_b), yr(df.start)
    for tag, nf, y0 in (("a", na, ya), ("b", nb, yb)):
        cols.append(np.column_stack([np.floor(nf) % 9, vimshottari(nf, np.zeros(len(nf))), vimshottari(nf, ys - y0)]))
        names += [f"{tag}_dasha_birth_lord", f"{tag}_dasha_at_birth", f"{tag}_dasha_at_wedding"]
    da = vimshottari(na, ys - ya); db = vimshottari(nb, ys - yb)
    cols.append((da == db).astype(float).reshape(-1, 1)); names.append("dasha_same_at_wedding")

    # ── TAMIL / MALAYALAM sidereal solar month of the wedding
    sm = np.floor((W[:, isun] % 360) / 30)
    cols.append(np.column_stack([sm, np.isin(sm, [3, 8]).astype(float)])); names += ["solar_month", "aadi_or_margazhi"]

    # ── KUA / BA ZHAI — gendered: column a is male by the dataset's construction
    md = lambda s: (pd.to_numeric(s.str[5:7], errors="coerce").fillna(1).to_numpy(int), pd.to_numeric(s.str[8:10], errors="coerce").fillna(1).to_numpy(int))
    (mA, dA), (mB, dB) = md(df.dob_a), md(df.dob_b)
    ka = np.array([kua(v, True, m, d) for v, m, d in zip(np.nan_to_num(ya), mA, dA)])
    kb = np.array([kua(v, False, m, d) for v, m, d in zip(np.nan_to_num(yb), mB, dB)])
    look = lambda x, y: BAZHAI.get(int(x), {}).get(int(y), np.nan) if np.isfinite(x) and np.isfinite(y) else np.nan
    rel = np.array([look(x, y) for x, y in zip(ka, kb)])
    # the classical table is genuinely DIRECTIONAL among the four bad relations (Xun reads Qian as Chueh Ming while
    # Qian reads Xun as Ho Hai), so carry both directions rather than picking a convention I cannot verify
    rev = np.array([look(y, x) for x, y in zip(ka, kb)])
    ea = np.array([1.0 if np.isfinite(x) and int(x) in EAST_GROUP else (0.0 if np.isfinite(x) else np.nan) for x in ka])
    eb = np.array([1.0 if np.isfinite(x) and int(x) in EAST_GROUP else (0.0 if np.isfinite(x) else np.nan) for x in kb])
    cols.append(np.column_stack([ka, kb, rel, rev, np.fmax(rel, rev), np.fmin(rel, rev), (rel < 4).astype(float),
                                 (rel == 2).astype(float), ((rel == 7) | (rev == 7)).astype(float), ea, eb, (ea == eb).astype(float)]))
    names += ["kua_a", "kua_b", "bazhai_relation", "bazhai_relation_rev", "bazhai_worst", "bazhai_best",
              "bazhai_good", "bazhai_yan_nian", "bazhai_chueh_ming_either", "east_group_a", "east_group_b", "same_group"]

    # ── the extra calendars, per date
    for tag, s in (("a", df.dob_a), ("b", df.dob_b), ("wed", df.start)):
        E = np.array([day_extras(v) for v in s], dtype=float)
        cols.append(E); names += [f"{tag}_{n}" for n in EXN]
        if tag == "a":
            Ea = E
        elif tag == "b":
            Eb = E
    # ── KOREAN GUNGHAP — the sound elements of the two birth pillars against each other
    pa = Ea[:, EXN.index("napeum_ohaeng")]; pb = Eb[:, EXN.index("napeum_ohaeng")]
    g = np.array([1.0 if (x, y) in GEN or (y, x) in GEN else 0.0 for x, y in zip(np.nan_to_num(pa, nan=-1).astype(int), np.nan_to_num(pb, nan=-1).astype(int))])
    o = np.array([1.0 if (x, y) in OVR or (y, x) in OVR else 0.0 for x, y in zip(np.nan_to_num(pa, nan=-1).astype(int), np.nan_to_num(pb, nan=-1).astype(int))])
    ok = np.isfinite(pa) & np.isfinite(pb)
    cols.append(np.column_stack([np.where(ok, g, np.nan), np.where(ok, o, np.nan), np.where(ok, (pa == pb).astype(float), np.nan)]))
    names += ["gunghap_generate", "gunghap_overcome", "gunghap_same_element"]
    # ── AZTEC pair relation on the 260-day count
    aa = Ea[:, EXN.index("aztec_sign")]; ab = Eb[:, EXN.index("aztec_sign")]
    az_ok = np.isfinite(aa) & np.isfinite(ab)
    cols.append(np.column_stack([np.where(az_ok, (aa == ab).astype(float), np.nan), np.where(az_ok, (aa - ab) % 20, np.nan),
                                 np.where(az_ok, (Ea[:, EXN.index("aztec_number")] - Eb[:, EXN.index("aztec_number")]) % 13, np.nan)]))
    names += ["aztec_same_sign", "aztec_sign_dist", "aztec_number_dist"]
    return np.column_stack(cols).astype(np.float32), names


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True); y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); s1, s2 = list(Z["slots"])
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    Xtr, names = build(tr, Z, "train"); log(f"train built: {Xtr.shape[1]} features"); Xte, _ = build(te, Z, "test"); log("test built")
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    plain = lambda p: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]), np.abs(p[:, ia] - p[:, ib]), p[:, iy]])
    prm = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.7, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)
    mt, me, mn, meta = [], [], [], []
    def member(cols, name):
        Xa = Xtr[:, cols]; Xb = Xte[:, cols]; rows = np.isfinite(Xa).any(1); s_tr = np.full(len(y), np.nan)
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = rows & (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); fit = rows & (later <= lo)
            if fit.sum() < 500:
                continue
            c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[fit], y[fit]); s_tr[blk] = c.predict_proba(Xa[blk])[:, 1]
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[rows], y[rows])
        s_te = np.full(len(Xb), np.nan); rte = np.isfinite(Xb).any(1); s_te[rte] = c.predict_proba(Xb[rte])[:, 1]
        f = np.isfinite(s_tr) & (later > cuts[0]); o = auc(y[f], s_tr[f]) if f.sum() > 500 else float("nan")
        mt.append(s_tr); me.append(s_te); mn.append(name); meta.append({"member": name, "forward_oof": o, "n_features": len(cols)})
        log(f"  {name:<48} {len(cols):>3} feats · fwd-OOF {o:.4f}")
    idx = lambda p: [i for i, n in enumerate(names) if p(n)]
    member(idx(lambda n: "manglik" in n or "mars_house" in n), "MANGAL / KUJA DOṢA (Manglik matching)")
    member(idx(lambda n: n.split("_", 1)[-1] in ("rajju", "rajju_same", "rajju_shiro_dosha") or n.startswith(("rajju", "vedha", "count_", "mahendra", "stree"))), "DAŚAKŪṬA — the four southern kūṭas")
    member(idx(lambda n: "dasha" in n), "VIMŚOTTARĪ DAŚĀ (period at birth and at wedding)")
    member(idx(lambda n: n.startswith(("kua_", "bazhai", "east_group", "same_group"))), "KUA / BA ZHAI (八宅 East–West group)")
    member(idx(lambda n: "napeum" in n or n.startswith("gunghap")), "KOREAN GUNGHAP (납음오행 sound element)")
    member(idx(lambda n: "aztec" in n or "lord_of" in n), "AZTEC TONALPŌHUALLI + the lords")
    member(idx(lambda n: any(k in n for k in ("ogham", "rune", "coptic", "igbo", "mahabote", "solar_month", "aadi"))), "OGHAM · RUNIC · COPTIC · IGBO · MAHABOTE · TAMIL")
    member(list(range(len(names))), "WORLD2 ALL (no ages)")
    Xtr = np.column_stack([plain(ptr), Xtr]); Xte = np.column_stack([plain(pte), Xte]); names = ["age_older", "age_younger", "age_gap", "start_year"] + names
    member(list(range(len(names))), "PLAIN + WORLD2 ALL")
    np.savez_compressed(os.path.join(OUT, "world2_members.npz"), S_train=np.column_stack(mt), S_test=np.column_stack(me),
                        names=np.array(mn), meta=json.dumps(meta), feature_names=np.array(names, dtype=object))
    log(f"wrote {OUT}/world2_members.npz with {len(mn)} members")


if __name__ == "__main__":
    main()
