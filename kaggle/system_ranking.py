"""system_ranking.py — every named marriage-matching system, measured on its own.

The joint fit answers "which handful of statements, taken together, rank marriages best". It cannot
answer the question a reader actually asks, which is "does Ashtakoota work? does the Javanese neptu
calculation work? does biorhythm?" — because a system with real signal can be shut out of a joint model
by another that got there first.

So: fit each named system ALONE. Same bank, same pair-only gate, same group cross-validation, same
relaxed non-negative refit. Each system gets its own alpha chosen inside its own CV. Nothing here reads
the test set — every number is cross-validated on the training couples, which is what makes it safe to
run thirty-odd times.

The comparison is against the ONE permitted baseline: a two-parameter logistic on the signed difference
between the two birth dates.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v22_nnls import build, orient, apply_flip
from v12_fit import side
from denylist import clause_ok


def groups(ids):
    """couples that share a person are one group, so CV never splits a marriage graph component.
    Copied rather than imported: v24_fit reads sys.argv at module level."""
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]


D = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev/quality_good")
OUT = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/.artamatch-dev/system_ranking.json")
MIN_INTER = float(os.environ.get("AQ_MIN_INTERACTION", "0.25"))
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))
ALPHAS = (0.0005, 0.001, 0.002, 0.003, 0.005, 0.008)
SEEDS = (7, 23, 101)

# name -> (regex over statement names, tradition, one line of where it comes from)
SYSTEMS = [
 ("Javanese Weton (Primbon jodoh)", r"^weton_", "Java",
  "the two birthdays' neptu numbers are added and read off the Pegat/Ratu/Jodoh table"),
 ("Balinese Pawukon", r"^pawukon_", "Bali",
  "ten week-cycles of different lengths running at once across a 210-day round"),
 ("Ten Porutham", r"^porutham_", "Tamil Nadu / Sri Lanka",
  "the counts between the two birth stars: Dina, Mahendra, Stree-Deergha, Vedha, Rajju"),
 ("Papasamya (malefic balance)", r"^papasamya", "India",
  "not who is afflicted but whether the two are afflicted equally"),
 ("Ashtakoota / Guna Milan", r"^koota_|^guna_", "North India",
  "the eight kootas scored out of thirty-six"),
 ("Mangal / Kuja dosha", r"manglik|kuja", "India",
  "Mars in the houses that trouble a marriage, and whether both carry it"),
 ("Nadi and Bhakoot", r"nadi|bhakoot", "India",
  "the two kootas that carry a veto of their own"),
 ("Navamsa D9 cross-contacts", r"^d9_", "India",
  "the ninth-harmonic chart, which is the marriage chart"),
 ("Jaimini karakas", r"karaka", "India", "the Darakaraka, the planet that signifies the spouse"),
 ("Chinese six relations", r"^xiangxing|^xiangpo|^liuchong|^liuhe|^sanhe|^xianghai", "China",
  "San He, Liu He, Liu Chong, Liu Hai, Xiang Xing, Xiang Po"),
 ("Bazi pillars and stems", r"^bazi|^stem_|^stempair|daymaster", "China",
  "the day pillar's stem and branch, and their combinations and clashes"),
 ("Na Yin element", r"^nayin", "China", "the sixty-fold sound-element of the pillar"),
 ("Korean Gunghap", r"^gunghap", "Korea", "the outer animal reading and the inner element reading"),
 ("Nine Star Ki / Kua", r"^ninestar|kua", "Japan / China", "the nine-year star and the Feng Shui number"),
 ("Burmese Mahabote", r"^mahabote", "Myanmar", "the eight houses, weekday against the Burmese year"),
 ("Tibetan srog / lus / dbang / klung", r"^tib_", "Tibet", "the four forces of the Tibetan almanac"),
 ("Couple's I Ching hexagram", r"^iching_", "China",
  "plum-blossom: his number makes the upper trigram, hers the lower"),
 ("Geomantic Judge (ilm al-raml)", r"^geomancy_", "Arab world / Europe",
  "two figures added line by line, which is what a Judge is"),
 ("Biorhythm", r"^biorhythm", "modern",
  "the 23, 28 and 33-day cycles, whose only published use is compatibility"),
 ("Western synastry aspects", r"^his_[a-z]+_(conj|opp|trine|square|sext|semisext|quinc)_her_", "Europe",
  "the angles between one chart's planets and the other's"),
 ("Composite chart", r"^comp", "Europe", "the chart of the midpoints, read as a third entity"),
 ("Davison relationship chart", r"^dav", "Europe", "the chart of the midpoint in time"),
 ("Ebertin midpoints", r"^midhis|^midher", "Europe", "the Sun/Moon and Venus/Mars marriage axes"),
 ("Harmonic charts", r"^h[0-9]+_", "Europe", "the 5th, 7th, 9th and 12th harmonics"),
 ("Draconic charts", r"draconic", "Europe", "the chart measured from the Moon's node"),
 ("Antiscia", r"antiscia", "Europe", "reflections across the solstice axis"),
 ("Progressions and solar arc", r"^prog_|^sa_", "Europe", "the chart advanced a day for a year"),
 ("Sabian symbols", r"^sabian", "modern", "the 360 images, one to a degree"),
 ("Dodekatemoria", r"^dodekatemoria", "Hellenistic", "the sign a 2.5-degree twelfth points to"),
 ("Monomoiria", r"^monomoiria", "Hellenistic", "the planet ruling the single degree"),
 ("Kabbalah: 72 Names", r"^kab72", "Kabbalah", "the wheel of seventy-two names, five degrees each"),
 ("Sefer Yetzirah letters", r"^seferyetzirah", "Kabbalah", "the letters given to sign and element"),
 ("Arabic parts / lots", r"^lot_", "Arab world", "the Lot of Marriage and its companions"),
 ("Panchanga: tithi, yoga, karana", r"tithi|nityayoga|karana", "India", "the five limbs of the day"),
 ("Numerology: life path", r"lifepath", "Pythagorean", "the birth date reduced to one digit"),
 ("Numerology: Chaldean", r"^chaldean", "Chaldean", "the older reduction, which keeps compound numbers"),
 ("Numerology: pinnacles", r"pinnacle|challenge", "Pythagorean", "the four pinnacles and four challenges"),
 ("Tarot birth cards", r"^tarot", "Tarot", "the trump the birth date reduces to"),
 ("Maya Tzolkin and the oracle", r"^maya_|tzolkin|dreamspell", "Maya", "the 260-day count and its oracle"),
 ("Aztec Tonalpohualli", r"^aztec", "Aztec", "the same count in its Aztec form, with the day lords"),
 ("Norse runic half-months", r"^rune", "Norse", "the twenty-four runes over the year"),
 ("Egyptian (Nile) zodiac", r"^nile", "Egypt", "the twelve deities and their scattered dates"),
 ("Celtic tree calendar", r"celtic", "Celtic", "the thirteen trees"),
 ("Rudhyar cycle phases", r"^cyclephase|^cycle_|^cycle[0-9]|^cyclesep", "modern",
  "where two slow planets stand in their own cycle"),
]


def main():
    from sklearn.linear_model import Lasso, LogisticRegression
    import re
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    y = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(float)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X, names = build(tr, Z, "train")

    keep = np.array([clause_ok(n) for n in names]) & (X.sum(0) >= FLOOR) \
        & np.array([side(n) == "AB" for n in names])
    sc = json.load(open(os.path.expanduser("~/.artamatch-dev/interaction_scores.json")))
    # a statement the gate abstained on is absent from the file; treat that as failing, not passing
    inter = np.array([min((sc.get(p, 0.0) for p in n.split(" AND ")), default=0.0) for n in names])
    keep = keep & (inter >= MIN_INTER)
    X = X[:, keep]; names = [n for n, k in zip(names, keep) if k]
    gid = groups(ids)
    print(f"  {D.split('/')[-1]}: {len(tr):,} couples · {X.shape[1]:,} pair-only statements "
          f"at interaction >= {MIN_INTER}\n")

    # the one permitted baseline
    gap = (pd.to_datetime(tr.dob_a, errors="coerce") - pd.to_datetime(tr.dob_b, errors="coerce")
           ).dt.days.to_numpy(float)
    gap = np.nan_to_num(gap, nan=0.0)
    Xg = np.column_stack([gap / 365.25, (gap / 365.25) ** 2])
    oof = np.full(len(y), np.nan)
    fold0 = np.random.default_rng(7).integers(0, 5, gid.max() + 1)[gid]
    for k in range(5):
        lo = LogisticRegression(max_iter=2000).fit(Xg[fold0 != k], y[fold0 != k])
        oof[fold0 == k] = lo.predict_proba(Xg[fold0 == k])[:, 1]
    base = G.auc(y.astype(int), oof)
    print(f"  BASELINE  signed age gap, two parameters: CV AUC {base:.4f}\n")

    rows = []
    for label, pat, origin, blurb in SYSTEMS:
        cols = np.array([bool(re.search(pat, n)) for n in names])
        if cols.sum() < 2:
            continue
        Xs = X[:, cols]
        best = (None, -1.0, 0)
        for alpha in ALPHAS:
            accs = []
            nrule = 0
            for seed in SEEDS:
                fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
                oof = np.full(len(y), np.nan)
                for k in range(5):
                    trn = fold != k
                    flip, _ = orient(Xs[trn], y[trn])          # direction inside the fold only
                    Xf = apply_flip(Xs, flip)
                    m = Lasso(alpha=alpha, positive=True, max_iter=6000).fit(Xf[trn], y[trn])
                    surv = np.where(m.coef_ > 0)[0]
                    if len(surv) >= 1:
                        w, b = G.fit_nonneg(Xf[trn][:, surv], y[trn], np.ones(int(trn.sum())))
                        oof[fold == k] = Xf[fold == k][:, surv] @ w + b
                        nrule = max(nrule, len(surv))
                    else:
                        oof[fold == k] = 0.0
                accs.append(G.auc(y.astype(int), oof))
            a = float(np.mean(accs))
            if a > best[1]:
                best = (alpha, a, nrule)
        rows.append({"system": label, "origin": origin, "blurb": blurb,
                     "statements": int(cols.sum()), "alpha": best[0],
                     "cv_auc": round(best[1], 4), "rules": best[2]})
        print(f"  {best[1]:.4f}  {label:<34}{int(cols.sum()):>6,} stmts  "
              f"{'BEATS the age gap' if best[1] > base else ''}")

    rows.sort(key=lambda r: -r["cv_auc"])
    print(f"\n  {'rank':<5}{'CV AUC':<9}{'system':<36}{'origin':<24}stmts")
    for i, r in enumerate(rows, 1):
        print(f"  {i:<5}{r['cv_auc']:<9.4f}{r['system']:<36}{r['origin']:<24}{r['statements']:,}")
    json.dump({"baseline_age_gap_cv_auc": round(base, 4), "min_interaction": MIN_INTER,
               "n_couples": len(tr), "systems": rows}, open(OUT, "w"), indent=1)
    print(f"\n  saved {OUT}")


if __name__ == "__main__":
    main()
