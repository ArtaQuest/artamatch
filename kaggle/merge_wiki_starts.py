"""
merge_wiki_starts.py — resolve the per-language harvest into ONE start date per couple, with the operator's trust
rule (2026-08-20): "if the person speaks that language then the second source should be trusted more."

Trust tiers per (pair, language) hit:
  0  the language is a PARTNER'S OWN — the primary language of a partner's birthplace country (coords →
     country via offline GeoNames → the country's principal wiki language); their home wiki knows their wedding best
  1  any other language
Resolution: highest tier wins; inside a tier, day-precision beats year-precision; then the majority year; then the
LANGS order (largest wikis first). Disagreements at the same tier are counted aloud. Writes AQ_DIR/_wikistarts.csv
(a, b, start, prec, lang, tier) for scrape_duration's AQ_WIKI_STARTS hook.
"""
import collections
import csv
import os
import sys

DIR = os.environ.get("AQ_DIR", "/tmp/aqwiki")
LANGS = [l for l in os.environ.get("AQ_LANGS", "en,de,fr,es,it,ru,ja,pt,pl,nl,sv,zh,uk,cs,fa,ar,tr,hu,fi,da,hy").split(",") if l]
CC_LANG = {"US": "en", "GB": "en", "IE": "en", "AU": "en", "NZ": "en", "CA": "en", "DE": "de", "AT": "de", "CH": "de", "FR": "fr", "BE": "fr",
           "ES": "es", "MX": "es", "AR": "es", "CL": "es", "CO": "es", "PE": "es", "VE": "es", "CU": "es", "UY": "es", "IT": "it", "RU": "ru",
           "BY": "ru", "KZ": "ru", "JP": "ja", "PT": "pt", "BR": "pt", "PL": "pl", "NL": "nl", "SE": "sv", "CN": "zh", "TW": "zh", "HK": "zh",
           "UA": "uk", "CZ": "cs", "SK": "cs", "IR": "fa", "AF": "fa", "EG": "ar", "SA": "ar", "IQ": "ar", "SY": "ar", "MA": "ar", "DZ": "ar",
           "TN": "ar", "JO": "ar", "LB": "ar", "TR": "tr", "HU": "hu", "FI": "fi", "DK": "da", "AM": "hy", "NO": "sv", "IS": "sv"}


def main():
    import reverse_geocoder as rg
    pool = {(r["a"], r["b"]): r for r in csv.DictReader(open(os.path.join(DIR, "pool.csv"))) if r["a"] != "#slice"}
    pts, keys = [], []
    for (a, b), r in pool.items():
        for s in ("a", "b"):
            if r[f"{s}lat"] and r[f"{s}lon"]:
                pts.append((float(r[f"{s}lat"]), float(r[f"{s}lon"]))); keys.append((a, b))
    own = collections.defaultdict(set)
    if pts:
        for k, res in zip(keys, rg.search(pts, mode=1)):
            lg = CC_LANG.get(res["cc"])
            if lg:
                own[k].add(lg)
    hits = collections.defaultdict(list)
    for r in csv.reader(open(os.path.join(DIR, "found.csv"))):
        if len(r) < 7:
            continue
        a, b, st, prec, lang = r[0], r[1], r[2], int(r[3]), r[4]
        hits[(a, b)].append((st, prec, lang))
    out = os.path.join(DIR, "_wikistarts.csv"); n_tier0 = n_conflict = 0
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["a", "b", "start", "prec", "lang", "tier"])
        for k, hs in hits.items():
            scored = sorted(((0 if lang in own[k] else 1, -prec, LANGS.index(lang) if lang in LANGS else 99, st, prec, lang) for st, prec, lang in hs))
            tier0 = [h for h in scored if h[0] == 0]
            cand = tier0 if tier0 else scored
            years = collections.Counter(h[3][:4] for h in cand)
            if len(years) > 1:
                n_conflict += 1
                best_year = max(years.items(), key=lambda kv: (kv[1], -min(h[2] for h in cand if h[3][:4] == kv[0])))[0]
                cand = [h for h in cand if h[3][:4] == best_year]
            top = cand[0]; n_tier0 += top[0] == 0
            w.writerow([k[0], k[1], top[3], top[4], top[5], top[0]])
    print(f"  {len(hits):,} couples dated · {n_tier0:,} from a partner's own language (tier 0) · {n_conflict:,} cross-language year disagreements resolved by tier/majority · wrote {out}")


if __name__ == "__main__":
    main()
