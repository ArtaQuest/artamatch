#%% [markdown]
# # Two birth dates, one question: did they have a child together?
#
# This notebook builds the **ArtaMatch couples** dataset from scratch. Nothing is downloaded from a previous
# version of it — every row comes from live SPARQL against Wikidata, and the queries are in the cells below so
# anyone can re-run them and get a different answer as Wikidata changes.
#
# The output is deliberately, almost aggressively small: **three columns**.
#
# | column | meaning |
# |---|---|
# | `dob_man` | the man's date of birth, `YYYY-MM-DD`, with `00` for anything Wikidata does not know |
# | `dob_woman` | the woman's date of birth, same encoding |
# | `parents_together` | 1 if a child exists who names **both** of them as parents, else 0 |
#
# Two dates in, one bit out. No names, places, occupations, nationality or marriage dates.
#
# ## The version that matters: 1800–1950 only
#
# The previous build ran 1800–2026 and its dominant effect was not astrology, it was **exposure**. Recorded
# parenthood ran about 58% for couples born in the 1800s and 2% for the 1990s, because a couple born in 1990
# may not have finished having children and any child they do have has not had time to become notable enough
# for Wikidata to record. Any smooth function of two dates scores well on that data by identifying the era: a
# cohort-plus-exposure feature block alone reached AUC 0.7004.
#
# So this build takes **150 years of parents, 1800 to 1950 inclusive** — every one of whom has had a full
# reproductive life and whose children have had decades to be written about. What is left is generational and
# astrological structure, measured without the recency cliff doing the work. The residual gradient inside the
# window is printed below rather than assumed away.
#
# **Children are not restricted.** A child born any time proves its parents were a couple, so the label query
# puts no date bound and no notability bound on the child at all.
#
# ## Seven decisions, each of which changes the data
#
# 1. **Two universes, and the metric lives in the smaller one.** A couple qualifies either because Wikidata
#    states `P26` (spouse) / `P451` (unmarried partner), or because some person names both of them as its
#    father and mother. The second kind is *positive by construction*, and an early version of this dataset
#    that discovered couples only through their children made "has a child" identical to "was found via a
#    child" — the label was the discovery route wearing a disguise. That trap is avoided here by separating
#    the two jobs: co-parent pairs join the TRAINING half, and the held-out half is **declared partnerships
#    only**. Whatever the reported score measures, it cannot be measuring how a row was found.
# 2. **Any birth-date precision, and missing parts are written `00`.** Requiring day precision threw away
#    44,464 couples — a third of the window. But Wikidata writes a year-precision birth as `YYYY-01-01`, and
#    copying that through would make a year-only date indistinguishable from a genuine 1 January birthday: 42.7%
#    of rows carried at least one `-01-01`, so "is this a 1 January" became a readable proxy for how well
#    documented a person is, which correlates with whether a child was recorded. So an unknown component is
#    written as `00` instead — `1850-00-00` for a year, `1850-03-00` for a month, `1850-03-17` for a day. The
#    missingness is now a fact in the data rather than a coincidence a model has to be trusted not to exploit,
#    and it is the same encoding the precision grid uses for its `month` and `year` levels.
# 3. **A partner with no date at all is excluded, and not for convenience.** 133,617 such rows exist. The only
#    way to put one in a two-date table is to duplicate the other partner's date, which would make
#    `dob_man == dob_woman` in half the file; and a couple with one date cannot exhibit a two-chart
#    relationship, so those rows can teach a marginal rate but nothing about synastry. The precision grid
#    measures that case properly, on couples whose truth is known.
# 4. **Both partners must be human.** `P31 = Q5`. Not pedantry: Wikidata has 10,641 non-human entities with
#    declared partnerships, and George Jetson, Jane Jetson and Terry McGinnis all sat in an earlier build with
#    declared spouses and recorded children.
# 5. **A child must name BOTH partners** — `?child wdt:P22 ?father ; wdt:P25 ?mother`. A child naming one of
#    them says nothing about the pair. Both parental orientations are checked, because the pair is stored here
#    in a canonical order that has nothing to do with which one is the father.
# 6. **Sex comes from the parental role where there is one.** `P22` is father and `P25` is mother, so a
#    co-parent pair carries its own sexes and needs no `P21` — which is also the only reason ten pairs whose
#    father has no `P21` statement are in the data. Declared partnerships still need `P21` on both, because
#    the column order is what encodes sex and an arbitrary order makes that claim false.
# 7. **The split is by PERSON, not by row.** People appear in several partnerships. Splitting rows at random
#    would put one of somebody's relationships in train and another in test, and a model could recognise the
#    person instead of predicting the outcome. Connected components over the partnership graph go to one side
#    or the other whole.
#
# **The notability filter is gone.** The previous build required a Wikipedia article on at least one partner,
# which cost 30,454 couples. It was a proxy for documentation depth, and dropping it makes the data
# substantially more inclusive at the price of more false negatives — real children who are simply not
# recorded. That direction is the conservative one: unrecorded children *depress* a measured AUC, they do not
# inflate it.

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

# The parents' window. Both partners must be born inside it. The children are not bounded.
FLOOR, CEIL = 1800, 1950
MAX_GAP_YEARS = 60          # a sanity bound on data errors, not a claim about human pairing
MALE, FEMALE = "Q6581097", "Q6581072"

UA = "ArtaMatch/2.0 (https://www.artaquest.com) couples dataset build"


def _fetch(query, accept):
    req = urllib.request.Request(
        ENDPOINT + "?" + urllib.parse.urlencode({"query": query}),
        headers={"Accept": accept, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return r.read().decode("utf-8", "replace")


def sparql_count(select, body):
    """How many rows SHOULD the query return — counted through the SAME projection it will be read with.

    The first version counted `COUNT(*)` over the raw pattern while the reader asked for `DISTINCT ?f ?m`, so
    it compared 732,612 child statements against 366,889 distinct parent pairs and called a complete result
    incomplete. A completeness check is only worth having if it counts the same thing, so the select clause
    goes inside a subquery and DISTINCT is honoured on both sides.
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
        raise RuntimeError(f"{name}: got {len(out):,} rows but the endpoint counted {want:,} — the result is "
                           f"incomplete, and an incomplete parent list silently mislabels couples")
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


def stamp(iso, precision):
    """Wikidata's timeValue plus its timePrecision, as a date whose unknown parts are `00`.

    Precision 11 is a day, 10 a month, 9 a year. Wikidata pads the unknown parts with 01, so a year-precision
    birth arrives as `1850-01-01T00:00:00Z` and is indistinguishable from someone genuinely born on 1 January.
    Writing `1850-00-00` instead keeps the row and states what is not known.
    """
    p = int(precision)
    if p >= 11:
        return iso[:10]
    if p == 10:
        return iso[:7] + "-00"
    return iso[:4] + "-00-00"


def concrete(d):
    """The same date with `00` replaced by `01`, for anything that needs a real instant."""
    y, m, dd = d.split("-")
    return f"{y}-{m if m != '00' else '01'}-{dd if dd != '00' else '01'}"


# Both partners dated, at ANY precision from year upwards, both born inside the parents' window. The year
# bound is pushed into SPARQL rather than filtered afterwards so the transfer stays small.
def dated(a, b):
    return f"""
  ?{a} p:P569/psv:P569 ?{a}v . ?{a}v wikibase:timeValue ?{a}dob ; wikibase:timePrecision ?{a}prec .
  ?{b} p:P569/psv:P569 ?{b}v . ?{b}v wikibase:timeValue ?{b}dob ; wikibase:timePrecision ?{b}prec .
  FILTER(?{a}prec >= 9 && ?{b}prec >= 9)
  FILTER(YEAR(?{a}dob) >= {FLOOR} && YEAR(?{a}dob) <= {CEIL})
  FILTER(YEAR(?{b}dob) >= {FLOOR} && YEAR(?{b}dob) <= {CEIL})
"""


#%% [markdown]
# ## 1. Declared partnerships — the universe the score is measured in
#
# `FILTER(STR(?a) < STR(?b))` keeps each unordered pair once: Wikidata states a spouse relation from both
# sides, so without it every couple appears twice with the columns swapped, and after a split the same couple
# could land on both sides of it. The canonical order is by Q-number and says nothing about sex — `P21` does
# that, further down.

#%%
DECLARED_BODY = f"""
  ?a wdt:P26|wdt:P451 ?b .
  FILTER(STR(?a) < STR(?b))
  ?a wdt:P31 wd:Q5 . ?b wdt:P31 wd:Q5 .
  ?a wdt:P21 ?asex . ?b wdt:P21 ?bsex .
{dated('a', 'b')}"""
dc = sparql("DISTINCT ?a ?b ?adob ?bdob ?aprec ?bprec ?asex ?bsex", DECLARED_BODY,
            "declared partnerships", order="?a ?b")
for c in ("a", "b", "asex", "bsex"):
    dc[c] = dc[c].map(qid)
dc["adob"] = [stamp(v, p) for v, p in zip(dc["adob"], dc["aprec"])]
dc["bdob"] = [stamp(v, p) for v, p in zip(dc["bdob"], dc["bprec"])]
dc["route"] = "declared"
print(f"  distinct people: {len(set(dc['a']) | set(dc['b'])):,}")

#%% [markdown]
# ## 2. The children — every person is evidence that a couple existed
#
# This is the second of the two queries, and it is the one that brings the children in. A person with a father
# and a mother proves those two were a couple, whether or not Wikidata ever states a partnership between them.
#
# **The same fact is stated two different ways in Wikidata and both have to be asked for.** A child may name
# its parents (`P22` father, `P25` mother), or the parents may name the child (`P40`), and the two are not
# kept in sync: the child-side statement alone finds 67,198 pairs, the parent-side statement alone finds
# 67,378, and the union finds **93,738**. Asking only the obvious way would have missed 26,540 couples — 39%
# more than the first form returns by itself.
#
# The two branches know sex differently, so each binds it for itself. `P22`/`P25` ARE the sexes — father and
# mother — which is why that branch needs no `P21` at all and why ten pairs whose father has no `P21` statement
# survive. The `P40` branch has no roles, only two parents of one child, so it does require `P21` on both.
#
# **No bound of any kind is placed on the child.** Not a date, not a notability filter, not even a birth date:
# requiring the child to have one would discard 2,366 pairs, and a child born in 2015 attests its 1948-born
# parents perfectly well. It is the parents' window that defines the era.

#%%
COPARENT_BODY = f"""
  {{ ?child wdt:P22 ?a ; wdt:P25 ?b .
    BIND(wd:{MALE} AS ?asex) BIND(wd:{FEMALE} AS ?bsex) }}
  UNION
  {{ ?a wdt:P40 ?child . ?b wdt:P40 ?child .
    FILTER(STR(?a) < STR(?b))
    ?a wdt:P21 ?asex . ?b wdt:P21 ?bsex . }}
  ?a wdt:P31 wd:Q5 . ?b wdt:P31 wd:Q5 .
{dated('a', 'b')}"""
cop = sparql("DISTINCT ?a ?b ?adob ?bdob ?aprec ?bprec ?asex ?bsex", COPARENT_BODY,
             "co-parent pairs (P22/P25 or P40)", order="?a ?b")
for c in ("a", "b", "asex", "bsex"):
    cop[c] = cop[c].map(qid)
cop["adob"] = [stamp(v, p) for v, p in zip(cop["adob"], cop["aprec"])]
cop["bdob"] = [stamp(v, p) for v, p in zip(cop["bdob"], cop["bprec"])]
cop["route"] = "coparent"
print(f"  distinct people: {len(set(cop['a']) | set(cop['b'])):,}")
print(f"  distinct pairs: {len({frozenset((a, b)) for a, b in zip(cop['a'], cop['b'])}):,}")

#%% [markdown]
# ## 3. The label
#
# `parents_together` is 1 when some child names both partners. The co-parent query above already *is* that
# relation, so the label is a lookup against the unordered pairs it returned — which is why it is computed
# before the two universes are merged, and why both parental orientations are covered by construction.

#%%
shared_child = {frozenset((a, b)) for a, b in zip(cop["a"], cop["b"])}
print(f"  unordered pairs attested by a shared child: {len(shared_child):,}")

#%% [markdown]
# ## 4. Assemble, and account for every row that is dropped
#
# The funnel is printed in full. A dataset that reports only its final size is hiding its own decisions.

#%%
both = pd.concat([dc, cop], ignore_index=True)
both["_pair"] = [f"{min(a, b)}|{max(a, b)}" for a, b in zip(both["a"], both["b"])]

# TWO kinds of duplicate arrive here and they need different handling.
#
# The first is the same pair by both routes. The DECLARED copy must win, because that is the copy allowed into
# the held-out half. Sorting on the route NAME does the opposite — "coparent" sorts before "declared" — and
# that one wrong keep silently absorbed every declared pair that had a child, leaving the declared subset
# 0.00% positive and the held-out half with no positives at all. So the rank is explicit.
#
# The second is the same pair TWICE BY THE SAME ROUTE, because a person with two P569 statements (or two P21)
# multiplies out: 150,153 rows covered about 128,165 distinct pairs. Picking arbitrarily would make the file
# depend on row order, so the finest-precision date wins and ties break on the earlier date.
both["_rk"] = both["route"].map({"declared": 0, "coparent": 1})
# Finest precision wins. `00` is now legible in the string, so this counts how many components are known
# rather than guessing from a `-01-01` suffix that could have been a real birthday.
both["_spec"] = -((~both["adob"].str.endswith("-00")).astype(int)
                  + (~both["adob"].str.endswith("-00-00")).astype(int)
                  + (~both["bdob"].str.endswith("-00")).astype(int)
                  + (~both["bdob"].str.endswith("-00-00")).astype(int))
dup_pairs = int(both["_pair"].duplicated().sum())
both = (both.sort_values(["_rk", "_spec", "adob", "bdob"])
        .drop_duplicates("_pair", keep="first").reset_index(drop=True))
print(f"  {dup_pairs:,} duplicate rows collapsed to one per pair "
      f"(both-routes and repeated-statement duplicates together)")

funnel = [("declared partnership rows returned", len(dc)),
          ("co-parent pair rows returned", len(dc) + len(cop)),
          ("one row per distinct pair, declared copy preferred", len(both))]

# Opposite sex only: the column order carries sex, so a pair the data cannot sex has no place to go.
opp = both[((both["asex"] == MALE) & (both["bsex"] == FEMALE))
           | ((both["asex"] == FEMALE) & (both["bsex"] == MALE))].copy()
funnel.append(("opposite-sex only", len(opp)))

# Sex decides the columns. Nothing else may: an earlier version inherited the pair's Q-number order, which
# made "the first column is the man" false for 45,182 of 87,762 rows.
man_is_a = opp["asex"].eq(MALE)
opp["dob_man"] = np.where(man_is_a, opp["adob"], opp["bdob"])
opp["dob_woman"] = np.where(man_is_a, opp["bdob"], opp["adob"])
opp["man"] = np.where(man_is_a, opp["a"], opp["b"])
opp["woman"] = np.where(man_is_a, opp["b"], opp["a"])
assert (opp.loc[man_is_a, "dob_man"] == opp.loc[man_is_a, "adob"]).all()
assert (opp.loc[~man_is_a, "dob_man"] == opp.loc[~man_is_a, "bdob"]).all()
print(f"  the man was partner A in {int(man_is_a.sum()):,} rows and partner B in {int((~man_is_a).sum()):,}"
      f" — which is why the order is assigned rather than inherited")

def _years_between(a, b):
    """Signed years from b to a, resolution-independent.

    NOT `pd.to_datetime(x).astype("int64") / (365.2425 * 86400 * 1e9)`. That assumes nanoseconds, and pandas
    here returns MICROseconds for these columns, so every gap came out a thousandth of its true size. The
    symptom was a filter that silently removed nothing — the funnel printed "(+0)" — and 33 couples up to 115
    years apart survived into training, where core.py dropped them and broke the row alignment instead.
    Converting to datetime64[D] first makes the unit explicit and the arithmetic days, whatever pandas decides.
    """
    ca = pd.Series(list(a)).map(concrete)
    cb = pd.Series(list(b)).map(concrete)
    da = pd.to_datetime(ca).to_numpy(dtype="datetime64[D]").astype("int64")
    db = pd.to_datetime(cb).to_numpy(dtype="datetime64[D]").astype("int64")
    return (da - db) / 365.2425


gap = np.abs(_years_between(opp["dob_man"], opp["dob_woman"]))
# Strictly inside core.py's own bound, which drops anything `> 60`. Filtering at exactly the same number left
# boundary couples to be dropped downstream instead, and a row dropped after the features are built cannot be
# aligned with its prediction.
opp = opp[gap < MAX_GAP_YEARS].copy()
funnel.append((f"births less than {MAX_GAP_YEARS} years apart", len(opp)))
assert np.abs(_years_between(opp["dob_man"], opp["dob_woman"])).max() < MAX_GAP_YEARS

opp["parents_together"] = [int(frozenset((a, b)) in shared_child)
                           for a, b in zip(opp["a"], opp["b"])]
# Every co-parent row must be a positive: it was found through a child. If this ever fails, the label lookup
# and the universe have drifted apart and nothing downstream means anything.
assert opp.loc[opp["route"] == "coparent", "parents_together"].eq(1).all(), \
    "a co-parent pair came out negative — the label and the universe disagree"

print("\n  FUNNEL — every step removes rows, and the running difference says how many")
prev = None
for label, n in funnel:
    d = "" if prev is None else f"   ({n - prev:+,})"
    print(f"      {n:>9,}  {label}{d}")
    prev = n
pos = int(opp["parents_together"].sum())
print(f"\n  {pos:,} of {len(opp):,} ({100*pos/len(opp):.2f}%) have a child naming both partners")
for r, g in opp.groupby("route"):
    print(f"      {r:<9} {len(g):>8,} rows, {100*g['parents_together'].mean():5.2f}% positive")
# A co-parent row is positive by construction, so 100% there is correct. A DECLARED row is not, and a declared
# subset that is all-negative or all-positive means the label lookup and the universe have come apart — which
# is exactly what a mis-sorted deduplication did here once, invisibly, until this was asserted.
d_rate = opp.loc[opp["route"] == "declared", "parents_together"].mean()
assert 0.15 < d_rate < 0.85, (f"declared partnerships are {100*d_rate:.2f}% positive — the label lookup has "
                              f"come apart from the universe; a held-out half built from these cannot be scored")

#%% [markdown]
# ## 5. The residual era gradient, printed rather than assumed away
#
# Restricting the parents to 1800–1950 removes the recency cliff; it does not flatten the window completely.
# A couple born in 1945 had children in the 1970s, whose notability is recorded less thoroughly than that of
# an 1850-born couple's children. The rate per decade is the honest measure of what is left, and it is printed
# so that any claim about astrology can be read against it.

#%%
dec = opp["dob_man"].str[:4].astype(int) // 10 * 10
era = opp.groupby(dec)["parents_together"].agg(["mean", "size"])
print("  man's birth decade   rate    rows")
for d, row in era.iterrows():
    bar = "#" * int(round(40 * row["mean"]))
    print(f"      {int(d)}         {row['mean']:.3f}  {int(row['size']):>6,}  {bar}")
print(f"\n  spread across decades: {era['mean'].max() - era['mean'].min():.3f} "
      f"(the 1800-2026 build spanned about 0.56)")

#%% [markdown]
# ## 6. The split: by person, and the held-out half is declared partnerships only
#
# Two rules at once. People appear in several partnerships, so **connected components** of the partnership
# graph move to one side whole — otherwise a model could recognise a person rather than predict an outcome.
# And the held-out half takes **only declared partnerships**, because a co-parent pair is positive by
# construction and scoring on it would measure the discovery route. Co-parent pairs stay in training, where
# extra positives are simply more evidence.

#%%
parent = {}


def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(x, y):
    rx, ry = find(x), find(y)
    if rx != ry:
        parent[rx] = ry


for a, b in zip(opp["man"], opp["woman"]):
    union(a, b)
opp["group"] = [find(a) for a in opp["man"]]

groups = sorted(set(opp["group"]))
rng = np.random.default_rng(20260813)
rng.shuffle(groups)
# Aim for 20% of DECLARED rows in the held-out half. Co-parent rows never go there, so the fraction of groups
# is chosen against the declared subset rather than against the whole file.
declared_rows = opp[opp["route"] == "declared"]
per_group = declared_rows.groupby("group").size().to_dict()
target = 0.20 * len(declared_rows)
test_groups, acc = set(), 0
for g in groups:
    if acc >= target:
        break
    if per_group.get(g):
        test_groups.add(g)
        acc += per_group[g]

is_test = opp["group"].isin(test_groups) & opp["route"].eq("declared")
# A co-parent pair inside a held-out group must not go to training either: its people are in the test half and
# training on them is exactly the leak the person-split exists to prevent.
drop = opp["group"].isin(test_groups) & opp["route"].eq("coparent")
train = opp[~is_test & ~drop].copy()
test = opp[is_test].copy()
print(f"  {len(groups):,} person groups -> {len(groups)-len(test_groups):,} train / {len(test_groups):,} test")
print(f"  rows: {len(train):,} train ({100*len(train)/len(opp):.1f}%) · "
      f"{len(test):,} test ({100*len(test)/len(opp):.1f}%) · "
      f"{int(drop.sum()):,} co-parent rows dropped for sharing a held-out person")
print(f"  positive rate: train {100*train['parents_together'].mean():.2f}% · "
      f"test {100*test['parents_together'].mean():.2f}%")
t_rate = test["parents_together"].mean()
assert 0.15 < t_rate < 0.85, (f"the held-out half is {100*t_rate:.2f}% positive — an AUC needs both classes, "
                              f"and a single-class test set silently scores 0.5 for every model")
print(f"  the held-out half is {100*test['route'].eq('declared').mean():.0f}% declared partnerships")

tp = set(train["man"]) | set(train["woman"])
sp = set(test["man"]) | set(test["woman"])
assert not (tp & sp), f"{len(tp & sp)} people are on both sides of the split"
assert not (set(train["group"]) & set(test["group"])), "a person group is on both sides"
print("  checked: no person and no group appears on both sides")

#%% [markdown]
# ## 7. The files
#
# `train.csv` is the published dataset: three columns, no index, no metadata. The test half is written with an
# id so a competition can score it, and its answer key is kept separate.

#%%
# WHAT ACCEPTING YEAR PRECISION ACTUALLY COSTS, measured rather than asserted. A year-only birth is written
# YYYY-01-01 and is indistinguishable from a genuine 1 January birthday, so "is this date a 1 January" is
# readable by any model as a proxy for how well the person is documented — and documentation depth correlates
# with whether a child was recorded. This is the one real price of decision 2 and it is printed here so nobody
# has to take the trade-off on trust.
#
# It is not uniform across the metric: the precision grid coarsens both dates to YYYY-01-01 in its `year|year`
# cell, where every row then looks year-precision and the proxy carries no information at all. So the mean of
# the fifteen cells contains cells where this leak is impossible and cells where it is fully available.
def prec_of(col):
    return np.where(col.str.endswith("-00-00"), 9, np.where(col.str.endswith("-00"), 10, 11))


for name, frame in (("train", train), ("test", test)):
    pm, pw = prec_of(frame["dob_man"]), prec_of(frame["dob_woman"])
    both_day = ((pm == 11) & (pw == 11)).mean()
    any_year = ((pm == 9) | (pw == 9)).mean()
    ident = (frame["dob_man"] == frame["dob_woman"]).mean()
    print(f"  {name}: {100*both_day:.2f}% of rows know both days, {100*any_year:.2f}% have a year-only date, "
          f"{100*ident:.2f}% have two identical strings")
    for lbl, p in (("man", pm), ("woman", pw)):
        c = collections.Counter(p.tolist())
        print(f"      {lbl:<6} day {c[11]:>7,}   month {c[10]:>6,}   year {c[9]:>6,}")

# Shuffle before writing. The rows are currently in the order the deduplication left them, which is sorted by
# date, so the file opens on a run of year-precision 1800 entries and any consumer that takes a head instead of
# a sample would see one decade and call it the dataset.
train = train.sample(frac=1.0, random_state=20260813).reset_index(drop=True)
test = test.sample(frac=1.0, random_state=20260814).reset_index(drop=True)

COLS = ["dob_man", "dob_woman", "parents_together"]
train[COLS].to_csv(os.path.join(OUT, "train.csv"), index=False)

test = test.reset_index(drop=True)
test["id"] = [f"c{i:06d}" for i in range(len(test))]
test[["id", "dob_man", "dob_woman"]].to_csv(os.path.join(OUT, "test.csv"), index=False)
test[["id", "parents_together"]].to_csv(os.path.join(OUT, "solution.csv"), index=False)
samp = test[["id"]].copy()
samp["parents_together"] = 0.5
samp.to_csv(os.path.join(OUT, "sample_submission.csv"), index=False)

# THE WINDOW, ASSERTED ON WHAT WAS ACTUALLY WRITTEN. The year bound is already in the SPARQL, so this cannot
# fail — which is exactly why it is worth having: the bound is expressed in one place and enforced in another,
# and a filter that silently stops matching is the failure this project has already had once (a 60-year gap
# filter that removed nothing because of a unit error). Checking the files rather than the queries is the only
# version of this check that cannot be fooled by a query that changed meaning.
for name, frame in (("train", train), ("test", test)):
    for col in ("dob_man", "dob_woman"):
        yrs = frame[col].str[:4].astype(int)
        bad = frame[(yrs < FLOOR) | (yrs > CEIL)]
        assert bad.empty, (f"{len(bad)} rows in {name}.{col} fall outside {FLOOR}-{CEIL}, "
                           f"e.g. {bad[col].head(3).tolist()}")
        assert frame[col].str.match(r"^\d{4}-\d{2}-\d{2}$").all(), f"{name}.{col} is not all YYYY-MM-DD"
        # Precision is monotone: a known day with an unknown month is not a date, it is a bug.
        assert not ((frame[col].str[5:7] == "00") & (frame[col].str[8:10] != "00")).any(), \
            f"{name}.{col} has a known day under an unknown month"
print(f"  checked: every written row has both births in {FLOOR}-{CEIL}, well-formed, precision monotone")

print(f"\n  wrote train.csv ({len(train):,}) · test.csv ({len(test):,}) · solution.csv · sample_submission.csv")
print(train[COLS].head(3).to_string(index=False))
print(f"\n  total build time {(time.time()-T0)/60:.1f} min")
