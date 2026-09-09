"""finalize_page.py <ver> <research.json> <deploy.json> <rules.json> <corpus_n> — point the page at a
model version: install almanac artifacts, regenerate the rules section, inject counts and the honest AUC."""
import json, re, sys, html as H
ver, research_p, deploy_p, rules_p, corpus_n = sys.argv[1:6]
R_ = json.load(open(research_p)); D_ = json.load(open(deploy_p)); J = json.load(open(rules_p))
rules = J["rules"]
open(f"docs/almanac/{ver}_model.json", "w").write(open(deploy_p).read())
open(f"docs/almanac/{ver}_rules.json", "w").write(open(rules_p).read())

def esc(t): return H.escape(t, quote=False)
def lead_group(name):
    c = name.split(" AND ")[0]
    if " AND " in name: return ("C", "Compound rules — two or three statements at once")
    if re.match(r"^cycle(24|36)?_", c): return ("A1", "The great cycles — your shared era")
    if c.startswith("comp_"): return ("A2", "The couple's composite chart")
    if c.startswith("dav_"): return ("A3", "The couple's Davison chart")
    if re.match(r"^his_\w+_(conj|sext|square|trine|opp|quinc|semisext|exactconj)_her_", c): return ("B1", "Synastry — his planet meets hers")
    if re.search(r"(yoni|nadi|gana|rajju|varna|vashya|tara|dashalord)pair|^kuta_|^guna_|mangal|vedha|mahendra|stridirgha|gandanta|vargottama", c): return ("B3", "Vedic matching")
    if re.search(r"(animal|branch|stem|nayin|kua|ninestar|xiu)|_rel=|dayun", c): return ("B4", "Chinese & Nine-Star matching")
    if re.search(r"(elem|mode|pol)pair|elem_", c): return ("B5", "Elements, modes & polarity")
    if re.search(r"_house=|sadesati|_from_other_moon", c): return ("B6", "Overlays — around the Moon")
    if re.search(r"sunmoon_mid|antiscia", c): return ("B7", "Midpoints & mirrors")
    if re.search(r"lifepath|birthday|attitude|personal_year|karmic|master", c): return ("B8", "Numerology")
    if re.search(r"pair=|_pair|tithi|karana|nityayoga|nakshatra|pada|decan|phase|d9|h7|h5|draconic|retro|combust|tzolkin|moonphase", c): return ("B2", "The pair tables & panchanga")
    return ("B0", "Other couple rules")
groups = {}
for r in rules:
    groups.setdefault(lead_group(r["name"]), []).append(r)
parts = []
for (gk, title), rs in sorted(groups.items(), key=lambda kv: -sum(r["weight"] for r in kv[1])):
    rs.sort(key=lambda r: -r["weight"])
    rows = []
    for r in rs:
        ex = esc(r["example"]) if r["example"] else "rare — belongs to an era no one alive was born in"
        tip = esc(" · ".join(r["what"])).replace('"', "&quot;")
        hum = esc(r["human"]).replace(" AND ", ' <b class="andj">AND</b> ')
        rows.append(f'<div class="rule" title="{tip}"><span class="rn">{hum}</span>'
                    f'<span class="rw">+{r["weight"]:.3f}</span><div class="re">{ex}</div></div>')
    parts.append(f'<details class="fam"><summary>{esc(title)} <span class="tc">{len(rs)} rule{"s" if len(rs)!=1 else ""}</span></summary>'
                 + "".join(rows) + "</details>")
seen = {}
for r in rules:
    for w in r["what"]:
        seen[w] = seen.get(w, 0) + 1
leg = "".join(f'<div class="rule"><span class="rn">{esc(t)}</span><span class="rw">{c}×</span></div>'
              for t, c in sorted(seen.items(), key=lambda kv: -kv[1]))
parts.append(f'<details class="fam"><summary>The traditions inside <span class="tc">{len(seen)} doctrines</span></summary>{leg}</details>')
section = "".join(parts)

s = open("docs/index.html").read()
lines = s.split("\n")
ix = [i for i, l in enumerate(lines) if l.startswith('<details class="fam"><summary>')]
assert len(ix) == 1, ix
lines[ix[0]] = section
s = "\n".join(lines)
s = re.sub(r'almanac/v\d+_model\.json', f'almanac/{ver}_model.json', s)
s = re.sub(r'almanac/v\d+_rules\.json', f'almanac/{ver}_rules.json', s)
n = len(rules)
s = s.replace("RN_RULES", f"<b>{n}</b>")
s = re.sub(r'a sparse regression kept <b>\d+</b>', f'a sparse regression kept <b>{n}</b>', s)
s = re.sub(r'held-out AUC [\d.]+', f'held-out AUC {R_["test_auc"]:.3f}', s)
s = re.sub(r'trained on all [\d,]+ full-precision couples', f'trained on all {corpus_n} full-precision couples', s)
s = re.sub(r'centuries of recorded\nmarriages decided', 'centuries of recorded\nmarriages decided', s)
open("docs/index.html", "w").write(s)
nrare = sum(1 for r in rules if r["rare"])
print(f"page -> {ver}: {n} rules · {len(groups)} groups · {nrare} rare · AUC {R_['test_auc']:.4f} · corpus {corpus_n}")
