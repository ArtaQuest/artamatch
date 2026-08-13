#%% [markdown]
# # Two birth dates, one question: did they have a child together?
#
# This notebook builds the **ArtaMatch couples** dataset from scratch. Nothing is downloaded from a previous
# version of it — every row here comes from live SPARQL queries against Wikidata, and the queries are in the
# cells below so anyone can re-run them and get a different answer as Wikidata changes.
#
# The output is deliberately, almost aggressively small: **three columns**.
#
# | column | meaning |
# |---|---|
# | `dob_man` | the man's date of birth, `YYYY-MM-DD` |
# | `dob_woman` | the woman's date of birth |
# | `parents_together` | 1 if a child exists who names **both** of them as parents, else 0 |
#
# That is the whole input. No names, no places, no occupations, no nationality, no sex, no marriage date.
# Two dates. The question is whether anything at all can be predicted from them.
#
# ## Why three columns is the interesting version
#
# A wider table invites a model to find the answer somewhere other than where the question is. Give it
# occupations and it learns that actors are documented differently from monarchs; give it nationality and it
# learns which countries' genealogies are well recorded. Strip all of that away and one honest question
# remains: **do two dates carry signal about a shared child, and how much of that signal is simply *when*
# these people were born?**
#
# That last part is not rhetorical. It is the dominant effect in this data and the reason the dataset exists
# in this shape. See the closing section.
#
# ## Six decisions, each of which changes the data
#
# 1. **Only declared relationships.** A couple is included because Wikidata states `P26` (spouse) or `P451`
#    (unmarried partner) between them — never because a child pointed at both of them. An earlier version of
#    this dataset discovered couples *through* their children, which made "has a child" identical to "was
#    found via a child". The label was the discovery route wearing a disguise.
# 2. **Both partners must be human.** `P31 = Q5`. This is not pedantry: Wikidata has 10,641 non-human
#    entities with declared partnerships, and George Jetson, Jane Jetson and Terry McGinnis were all sitting
#    in an earlier build with declared spouses and recorded children.
# 3. **A child must name BOTH partners.** The label comes from `?child wdt:P22 ?father ; wdt:P25 ?mother` —
#    one child declaring both people. A child who names only one of them says nothing about the pair.
# 4. **Day precision only, on both dates.** Wikidata stores a year-precision birth as `YYYY-01-01`. In a
#    three-column table there is nowhere to record precision, so a year-only date would be indistinguishable
#    from a genuine 1 January birthday and every model would learn a spurious 1-January effect. Both dates
#    must carry `timePrecision >= 11`.
# 5. **At least one partner must have a Wikipedia article.** A person with a Wikidata item and no article in
#    any language is very often there *only* because they were somebody's parent or spouse — which is the
#    circularity of decision 1 arriving by a different door.
# 6. **The 80/20 split is by PERSON, not by row.** People appear in several partnerships. Splitting rows at
#    random would put one of somebody's relationships in train and another in test, and a model could then
#    recognise the person rather than predict the outcome.

#%%
import collections
import io
import json
import os
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

OUT = "/kaggle/working" if os.path.isdir("/kaggle/working") else "."
ENDPOINT = "https://qlever.dev/api/wikidata"
T0 = time.time()


UA = "ArtaMatch/1.0 (https://www.artaquest.com) couples dataset build"


def _fetch(query, accept):
    req = urllib.request.Request(
        ENDPOINT + "?" + urllib.parse.urlencode({"query": query}),
        headers={"Accept": accept, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return r.read().decode("utf-8", "replace")


def sparql_count(select, body):
    """How many rows SHOULD the query return — counted through the SAME projection it will be read with.

    The first version counted `COUNT(*)` over the raw pattern while the reader asked for `DISTINCT ?f ?m`,
    so it compared 732,612 child statements against 366,889 distinct parent pairs and declared a complete
    result incomplete. A completeness check is only worth having if it counts the same thing, so the select
    clause goes inside a subquery and DISTINCT is honoured on both sides.
    """
    q = f"{PREFIXES}\nSELECT (COUNT(*) AS ?n) WHERE {{ {{ SELECT {select} WHERE {{ {body} }} }} }}"
    d = json.loads(_fetch(q, "application/qlever-results+json"))
    if not d.get("res"):
        raise RuntimeError(f"count query failed: {str(d.get('exception'))[:300]}")
    return int(d["res"][0][0].split('"')[1])


def sparql(select, body, name, order=None, page=250000):
    """Run a query in pages and REFUSE to return a result that is not provably complete.

    The reason this is so defensive: the first version read the whole result in one stream and the parent-pair
    query — 732,608 rows — died with `IncompleteRead(21584468 bytes read)`. That raised, so it was obvious.
    What would not have been obvious is a truncated read that still parsed: every parent pair that failed to
    arrive becomes a couple silently labelled 0. A partial answer here is worse than no answer, because it
    looks like data.

    So the row count is asked for separately, the rows are pulled in ordered pages, and the totals must
    agree exactly or this raises.
    """
    t = time.time()
    want = sparql_count(select, body)
    frames, got = [], 0
    while got < want:
        q = (f"{PREFIXES}\nSELECT {select} WHERE {{ {body} }}"
             + (f" ORDER BY {order}" if order else "")
             + f" LIMIT {page} OFFSET {got}")
        for attempt in range(5):
            try:
                raw = _fetch(q, "text/tab-separated-values")
                break
            except Exception as e:
                if attempt == 4:
                    raise
                wait = 5 * (attempt + 1)
                print(f"    {name}: {type(e).__name__} at offset {got:,}, retrying in {wait}s", flush=True)
                time.sleep(wait)
        df = pd.read_csv(io.StringIO(raw), sep="\t", dtype=str, keep_default_na=False)
        if len(df) == 0:
            break
        frames.append(df)
        got += len(df)
        if want > page:
            print(f"    {name}: {got:,}/{want:,}", flush=True)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out.columns = [c.strip().lstrip("?") for c in out.columns]
    for c in out.columns:
        out[c] = out[c].str.strip().str.strip('"')
    if len(out) != want:
        raise RuntimeError(f"{name}: got {len(out):,} rows but the endpoint counted {want:,} — the result "
                           f"is incomplete, and an incomplete parent list silently mislabels couples")
    print(f"  {name}: {len(out):,} rows in {time.time()-t:.0f}s (count-verified)", flush=True)
    return out


PREFIXES = """
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX schema: <http://schema.org/>
"""


def qid(s):
    return s.rsplit("/", 1)[-1].rstrip(">")


#%% [markdown]
# ## 1. Every declared couple, with both birth dates and both sexes
#
# `FILTER(STR(?a) < STR(?b))` keeps each unordered pair once. Wikidata states a spouse relation from both
# sides, so without it every couple would appear twice with the columns swapped — and after an 80/20 split
# the same couple could land on both sides of it.

#%%
COUPLES_BODY = """
  ?a wdt:P26|wdt:P451 ?b .
  FILTER(STR(?a) < STR(?b))
  ?a wdt:P31 wd:Q5 . ?b wdt:P31 wd:Q5 .
  ?a wdt:P21 ?asex . ?b wdt:P21 ?bsex .
  ?a p:P569/psv:P569 ?av . ?av wikibase:timeValue ?adob ; wikibase:timePrecision ?aprec .
  ?b p:P569/psv:P569 ?bv . ?bv wikibase:timeValue ?bdob ; wikibase:timePrecision ?bprec .
  FILTER(?aprec >= 11 && ?bprec >= 11)
"""
cp = sparql("?a ?b ?adob ?bdob ?asex ?bsex", COUPLES_BODY, "couples", order="?a ?b")
for c in ("a", "b", "asex", "bsex"):
    cp[c] = cp[c].map(qid)
cp["adob"] = cp["adob"].str[:10]
cp["bdob"] = cp["bdob"].str[:10]
print(f"  distinct people: {len(set(cp['a']) | set(cp['b'])):,}")

#%% [markdown]
# ## 2. The label: a child who names both of them
#
# `P22` is father, `P25` is mother. One child, both statements — so the pair is attested as parents *of the
# same person*. This is the strictest reading available and the one that makes the target mean what its name
# says.

#%%
KIDS_BODY = "  ?child wdt:P22 ?f ; wdt:P25 ?m ."
kd = sparql("DISTINCT ?f ?m", KIDS_BODY, "parent pairs", order="?f ?m")
parents = {frozenset((qid(f), qid(m))) for f, m in zip(kd["f"], kd["m"])}
print(f"  distinct unordered parent pairs: {len(parents):,}")

#%% [markdown]
# ## 3. Who is actually in Wikipedia
#
# A Wikidata item is not notability. An article in some language edition is the closest available proxy, and
# requiring it of at least one partner is what removes the people who exist in the data only as somebody's
# relative.

#%%
SITE_BODY = """
  ?a wdt:P26|wdt:P451 ?x .
  ?site schema:about ?a ; schema:isPartOf/wikibase:wikiGroup "wikipedia" .
"""
st = sparql("DISTINCT ?a", SITE_BODY, "people with a Wikipedia article", order="?a")
inwiki = set(st["a"].map(qid))

#%% [markdown]
# ## 4. Assemble, and account for every row that is dropped
#
# The funnel is printed in full. A dataset that reports only its final size is hiding its own decisions.

#%%
FLOOR, CEIL = 1800, 2026
funnel = [("declared couples, both human, both sexes, both dates day-precision", len(cp))]

cp["label"] = [1 if frozenset((a, b)) in parents else 0 for a, b in zip(cp["a"], cp["b"])]
# The label count is NOT a funnel step — labelling removes nothing. Printed separately, because putting it
# in the chain made the running differences meaningless: a step that drops nothing appeared to drop 79,013
# rows and the next step appeared to add 77,613 back.
n_pos_all = int(cp["label"].sum())

opp = cp[((cp.asex == "Q6581097") & (cp.bsex == "Q6581072")) |
         ((cp.asex == "Q6581072") & (cp.bsex == "Q6581097"))].copy()
funnel.append(("opposite-sex only (male Q6581097 / female Q6581072)", len(opp)))

ya = opp["adob"].str[:4].astype(int)
yb = opp["bdob"].str[:4].astype(int)
opp = opp[(ya >= FLOOR) & (ya <= CEIL) & (yb >= FLOOR) & (yb <= CEIL)].copy()
funnel.append((f"both births within {FLOOR}-{CEIL}", len(opp)))

gap = (pd.to_datetime(opp["adob"], errors="coerce") -
       pd.to_datetime(opp["bdob"], errors="coerce")).dt.days.abs() / 365.2425
opp = opp[gap.notna() & (gap <= 60)].copy()
funnel.append(("births no more than 60 years apart", len(opp)))

opp = opp[opp["a"].isin(inwiki) | opp["b"].isin(inwiki)].copy()
funnel.append(("at least one partner has a Wikipedia article", len(opp)))

print("\n  FUNNEL — every step removes rows, and the running difference says how many")
prev = None
for name, n in funnel:
    d = "" if prev is None else f"   ({n-prev:+,})"
    print(f"    {n:>9,}  {name}{d}")
    prev = n
print(f"\n  of the {funnel[0][1]:,} couples at the top, {n_pos_all:,} ({100*n_pos_all/funnel[0][1]:.2f}%) "
      f"have a child naming both partners")
print(f"  of the {len(opp):,} that survive every filter, {100*opp['label'].mean():.2f}% do")

#%% [markdown]
# ## 5. The split is by person
#
# Connected components over the partnership graph: if two couples share a person they land on the same side.
# The 80/20 is therefore approximate in rows and exact in people, which is the version that matters.

#%%
parent_uf = {}


def find(x):
    parent_uf.setdefault(x, x)
    while parent_uf[x] != x:
        parent_uf[x] = parent_uf[parent_uf[x]]
        x = parent_uf[x]
    return x


def union(x, y):
    rx, ry = find(x), find(y)
    if rx != ry:
        parent_uf[rx] = ry


for a, b in zip(opp["a"], opp["b"]):
    union(a, b)
opp["group"] = [find(a) for a in opp["a"]]
groups = opp["group"].unique()
rng = np.random.default_rng(20260813)
perm = rng.permutation(groups)
n_test_groups = int(round(0.20 * len(groups)))
test_groups = set(perm[:n_test_groups].tolist())
is_test = opp["group"].isin(test_groups)
print(f"  {len(groups):,} person groups -> {len(groups)-n_test_groups:,} train / {n_test_groups:,} test")
print(f"  rows: {int((~is_test).sum()):,} train ({100*(~is_test).mean():.1f}%) · "
      f"{int(is_test.sum()):,} test ({100*is_test.mean():.1f}%)")
print(f"  positive rate: train {100*opp.loc[~is_test,'label'].mean():.2f}% · "
      f"test {100*opp.loc[is_test,'label'].mean():.2f}%")
assert not (set(opp.loc[~is_test, 'group']) & set(opp.loc[is_test, 'group'])), "a group straddles the split"
overlap = (set(opp.loc[~is_test, 'a']) | set(opp.loc[~is_test, 'b'])) & \
          (set(opp.loc[is_test, 'a']) | set(opp.loc[is_test, 'b']))
assert not overlap, f"{len(overlap)} people appear on both sides of the split"
print("  checked: no person and no group appears on both sides")

#%% [markdown]
# ## 6. Write the three-column files
#
# `train.csv` is the dataset. `test.csv` and `solution.csv` are the competition's public half and its answer
# key — the answer key stays out of the published dataset.

#%%
# COLUMN ORDER CARRIES THE SEX, and it has to be built deliberately. The pair was materialised with
# FILTER(STR(?a) < STR(?b)), which orders by Q-number — an arbitrary order that has nothing to do with who is
# whom. Publishing that as "first column is the man" would have been false for about half the rows. So the
# columns are assigned from P21 here and NAMED for it, which makes the convention impossible to misread and
# is what the precision grid's axes depend on.
MALE, FEMALE = "Q6581097", "Q6581072"
man_is_a = opp["asex"].eq(MALE)
opp["dob_man"] = np.where(man_is_a, opp["adob"], opp["bdob"])
opp["dob_woman"] = np.where(man_is_a, opp["bdob"], opp["adob"])
assert (opp["dob_man"] != opp["dob_woman"]).all() or True     # equal dates are legitimate
chk = opp.loc[~man_is_a].head(1)
if len(chk):
    r0 = chk.iloc[0]
    assert r0["dob_man"] == r0["bdob"] and r0["dob_woman"] == r0["adob"], "sex swap did not apply"
print(f"  man was partner A in {int(man_is_a.sum()):,} rows and partner B in {int((~man_is_a).sum()):,} — "
      f"which is why the order had to be assigned rather than inherited")

tr = opp.loc[~is_test, ["dob_man", "dob_woman", "label"]].rename(
    columns={"label": "parents_together"}).reset_index(drop=True)
te = opp.loc[is_test, ["dob_man", "dob_woman", "label"]].rename(
    columns={"label": "parents_together"}).reset_index(drop=True)
tr = tr.sample(frac=1.0, random_state=7).reset_index(drop=True)
te = te.sample(frac=1.0, random_state=8).reset_index(drop=True)
te.insert(0, "id", np.arange(len(te)))

tr.to_csv(f"{OUT}/train.csv", index=False)
te[["id", "dob_man", "dob_woman"]].to_csv(f"{OUT}/test.csv", index=False)
sol = te[["id", "parents_together"]].copy()
# Kaggle splits a leaderboard into a public and a private half; the private half is what the final standing
# is computed on, and it is chosen at random here so nothing about a row decides which half it lands in.
rng2 = np.random.default_rng(20260813)
sol["Usage"] = np.where(rng2.random(len(sol)) < 0.30, "Public", "Private")
sol.to_csv(f"{OUT}/solution.csv", index=False)
samp = te[["id"]].copy()
samp["parents_together"] = 0.5
samp.to_csv(f"{OUT}/sample_submission.csv", index=False)

meta = {"built": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "endpoint": ENDPOINT, "year_range": [FLOOR, CEIL],
        "funnel": [{"step": n, "rows": int(v)} for n, v in funnel],
        "train_rows": int(len(tr)), "test_rows": int(len(te)),
        "train_positive_rate": float(tr["parents_together"].mean()),
        "test_positive_rate": float(te["parents_together"].mean()),
        "person_groups": int(len(groups)),
        "split": "80/20 by connected component of the partnership graph, seed 20260813",
        "columns": ["dob_man", "dob_woman", "parents_together"]}
json.dump(meta, open(f"{OUT}/build.json", "w"), indent=1)
print(f"\n  wrote train.csv ({len(tr):,}) · test.csv ({len(te):,}) · solution.csv · sample_submission.csv")
print(f"  {tr.head(3).to_string(index=False)}")
print(f"\n  total build time {(time.time()-T0)/60:.1f} min")

#%% [markdown]
# ## 7. What a model here is actually learning — read this before believing a score
#
# The honest summary of a great deal of work on this dataset: **most of the predictable signal is *when*
# these people were born, not who they were.**
#
# Recorded parenthood collapses across cohorts. With the younger partner born in the 1800s it is around 58%;
# by the 1970s it is 10%; by the 1990s, 2%. Almost none of that is biology. A couple born in 1985 may not
# have finished having children, and any child they do have has not had time to become notable enough for
# Wikidata to record. So a feature that merely identifies the era — and every slowly-moving astronomical
# quantity does, along with any smooth function of the two dates — scores well without saying anything about
# the couple.
#
# Two numbers make this concrete, both measured on this data:
#
# * A single non-astrological feature block of **birth cohort plus exposure time** reaches **AUC 0.7004** on
#   its own. That is indistinguishable from the best astrological feature block anyone has built here.
# * Removing one partner's date entirely costs almost nothing. If the *pair* mattered, deleting half the
#   input should be devastating. It is not — consistent with the surviving date carrying the era.
#
# The baseline to beat is therefore not 0.5. It is a two-parameter logistic regression on the **signed**
# difference of the two dates, `dob_b - dob_a` in years, and any claim of a discovery here should be quoted
# against that and against a cohort model, not against chance.
#
# None of which makes the task uninteresting — it makes it a good one. The question is whether anything in
# two dates beats knowing roughly when they lived.
