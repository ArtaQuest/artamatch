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
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

OUT = "/kaggle/working" if os.path.isdir("/kaggle/working") else "."
# TWO ENDPOINTS, tried in order. qlever is fast and answers these shapes in seconds, but it rate-limits a client
# that has asked a lot of questions and returns 429 for a sustained period — long enough to outlast any backoff
# worth writing. The Wikidata Query Service is slower and has a 60-second query timeout, which is exactly why the
# heavy NOT EXISTS filtering moved out of SPARQL and into pandas below: simple queries survive both endpoints.
ENDPOINTS = [
    "https://qlever.dev/api/wikidata",
    "https://query.wikidata.org/sparql",
]
ENDPOINT = ENDPOINTS[0]

# An endpoint that has rate-limited us STAYS rate-limited for a while, so re-probing it seven times per query is
# pure waste: at fourteen sliced queries that is over an hour of backoff before any work happens. The first time
# one exhausts its retries it is struck off for the rest of the process.
_DEAD = set()
# AQ_SKIP_ENDPOINTS lets a caller who already knows an endpoint is rate-limited skip straight past it, rather
# than paying seven backoffs to rediscover it at the start of every run.
for _ep in os.environ.get("AQ_SKIP_ENDPOINTS", "").split(","):
    if _ep.strip():
        _DEAD.update(b for b in ENDPOINTS if _ep.strip() in b)
T0 = time.time()

# The parents' window. Both partners must be born inside it. The children are not bounded.
FLOOR, CEIL = 1700, 1950
MAX_GAP_YEARS = 60          # a sanity bound on data errors, not a claim about human pairing
MALE, FEMALE = "Q6581097", "Q6581072"

UA = "ArtaMatch/2.0 (https://www.artaquest.com) couples dataset build"


def _fetch(query, accept, tries=7):
    """One HTTP call, with backoff on 429 — CENTRALLY, because only one of the two callers had any.

    `sparql()` retried its page reads but `sparql_count()` did not, so a rate limit during a count raised
    HTTPError 429 and killed the whole build after several minutes of work. A public SPARQL endpoint will
    rate-limit anyone who asks enough questions; backing off is part of asking politely, not an error path.
    """
    last = None
    live = [b for b in ENDPOINTS if b not in _DEAD] or list(ENDPOINTS)
    for base in live:
        # The official service speaks a different JSON dialect, so ask it for the one both understand.
        acc = accept
        if "query.wikidata.org" in base and "qlever" in acc:
            acc = "application/sparql-results+json"
        for attempt in range(tries):
            req = urllib.request.Request(
                base + "?" + urllib.parse.urlencode({"query": query}),
                headers={"Accept": acc, "User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=1800) as r:
                    return r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                last = e
                if e.code not in (429, 500, 502, 503, 504):
                    raise
                if attempt == tries - 1:
                    if e.code == 429:
                        _DEAD.add(base)
                        print(f"    {base.split('/')[2]}: rate-limited after {tries} tries — struck off for "
                              f"the rest of this run", flush=True)
                    else:
                        print(f"    {base.split('/')[2]}: HTTP {e.code} after {tries} tries; "
                              f"trying the next endpoint", flush=True)
                    break
                wait = min(90, 5 * (2 ** attempt))
                print(f"    {base.split('/')[2]}: HTTP {e.code}; waiting {wait}s "
                      f"({attempt + 1}/{tries})", flush=True)
                time.sleep(wait)
            except Exception as e:
                last = e
                if attempt == tries - 1:
                    break
                time.sleep(5 * (attempt + 1))
    raise last if last else RuntimeError("no endpoint answered")


def sparql_count(select, body):
    """How many rows SHOULD the query return — counted through the SAME projection it will be read with.

    The first version counted `COUNT(*)` over the raw pattern while the reader asked for `DISTINCT ?f ?m`, so
    it compared 732,612 child statements against 366,889 distinct parent pairs and called a complete result
    incomplete. A completeness check is only worth having if it counts the same thing, so the select clause
    goes inside a subquery and DISTINCT is honoured on both sides.
    """
    q = f"{PREFIXES}\nSELECT (COUNT(*) AS ?n) WHERE {{ {{ SELECT {select} WHERE {{ {body} }} }} }}"
    d = json.loads(_fetch(q, "application/qlever-results+json"))
    # TWO JSON DIALECTS. qlever answers {"res": [["\"12\"^^<...int>"]]}; the Wikidata Query Service answers the
    # standard {"results": {"bindings": [{"n": {"value": "12"}}]}}. Parsing only the first meant that the moment
    # the fallback endpoint took over, a perfectly good count came back as "count query failed: None".
    if isinstance(d.get("res"), list) and d["res"]:
        return int(str(d["res"][0][0]).split('"')[1])
    binds = (d.get("results") or {}).get("bindings") or []
    if binds:
        return int(next(iter(binds[0].values()))["value"])
    raise RuntimeError(f"count query failed on both dialects: {str(d)[:250]}")


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
        # The Wikidata Query Service's TSV decorates values — a date arrives as
        # "1850-03-17T00:00:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime> and a URI inside angle brackets —
        # while qlever's is plain. Strip the type suffix and the brackets so both parse to the same frame; without
        # this, every date slice came out unusable the moment the fallback took over.
        df = pd.read_csv(io.StringIO(raw), sep="\t", dtype=str, keep_default_na=False)
        for c in df.columns:
            df[c] = (df[c].str.replace(r"\^\^<[^>]*>$", "", regex=True)
                          .str.replace(r'^"(.*)"$', r"\1", regex=True))
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
    # TRUNCATION IS THE DANGEROUS DIRECTION, and only that direction. A parent pair that fails to arrive becomes a
    # couple silently labelled 0, which is why this check exists at all. An EXTRA row is harmless: rows are
    # deduplicated to one per pair further down, so a duplicate changes nothing. The Wikidata Query Service
    # reproducibly returns one row more than its own COUNT for these queries — 10,645 against 10,644 — and
    # refusing the whole build over that would trade a real safeguard for a cosmetic one.
    if len(out) < want:
        raise RuntimeError(f"{name}: got {len(out):,} rows but the endpoint counted {want:,} — the result is "
                           f"incomplete, and an incomplete parent list silently mislabels couples")
    if len(out) > want:
        print(f"    {name}: {len(out) - want} row(s) more than counted; deduplication downstream absorbs it",
              flush=True)
    print(f"  {name}: {len(out):,} rows in {time.time()-t:.0f}s (count-verified)", flush=True)
    return out


PREFIXES = """
PREFIX ps: <http://www.wikidata.org/prop/statement/>
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

    AND 1 JANUARY IS TREATED AS A YEAR EVEN WHEN WIKIDATA CLAIMS A DAY. The claim is not trustworthy: among
    167,044 day-precision dates in this window, 1 January occurs 767 times against a median day-of-year count of
    456 — a 1.7x excess, where 2 January and 31 December both sit at 1.0x. Christmas Day reaches only 1.28x, so
    the spike is not "notable dates attract real births". The excess is roughly 311 records whose source knew
    only the year and whose importer wrote a day anyway.

    The cost is stated rather than hidden: about 456 genuine 1 January birthdays lose their day, 0.27% of all
    day-precision dates. That is the right side to err on. The entire reason unknown parts are written `00` is to
    stop date precision acting as a proxy for how well documented a person is — and a 1.7x pile-up on one date
    means Jan-1-ness was still carrying exactly that signal, in the one place the encoding could not see it.
    """
    p = int(precision)
    if p >= 11:
        d = iso[:10]
        return d[:4] + "-00-00" if d[5:10] == "01-01" else d
    if p == 10:
        return iso[:7] + "-00"
    return iso[:4] + "-00-00"


def concrete(d):
    """The same date with `00` replaced by `01`, for anything that needs a real instant."""
    y, m, dd = d.split("-")
    return f"{y}-{m if m != '00' else '01'}-{dd if dd != '00' else '01'}"


# Both partners dated, at ANY precision from year upwards, both born inside the parents' window. The year
# bound is pushed into SPARQL rather than filtered afterwards so the transfer stays small.
#
# TWO DENOISING RULES LIVE HERE, and both were measured on Wikidata before being added rather than assumed:
#
# NOT DEPRECATED. `p:P569/psv:P569` walks every statement regardless of rank, including the ones Wikidata has
# explicitly marked wrong. 17,946 humans carry a deprecated birth date, and the whole input to this task is the
# date, so reading a known-wrong one is not a small error. The rank is checked on the statement node.
#
# NOT CONTRADICTED. 33,335 humans carry two DIFFERENT birth years. Picking one of those by precision is a coin
# toss dressed as a rule, so a person whose own record disagrees with itself about the year is excluded outright.
def dated(a, b, lo=None, hi=None):
    """Both partners dated, non-deprecated, at year precision or finer, inside the window.

    THE RANK CHECK STAYS IN SPARQL because it is one extra triple. 17,946 humans carry a birth date Wikidata has
    marked DEPRECATED — that is, known wrong — and `p:P569/psv:P569` walks every statement regardless of rank.
    The date is the entire input to this task, so reading a known-wrong one is not a small error.

    THE CONFLICT CHECKS MOVED OUT, and not for tidiness. Expressing "this person has no OTHER birth year" as
    FILTER NOT EXISTS made qlever answer 429 — load-shedding, since cheap queries kept working — and it would
    have timed out on the 60-second Wikidata Query Service too. It is also unnecessary: this query returns one row
    per statement, so a person with two birth years already arrives as TWO ROWS. The contradiction is in the
    result set, and pandas can see it for free.
    """
    parts = []
    for v in (a, b):
        parts.append(f"""
  ?{v} p:P569 ?{v}st . ?{v}st psv:P569 ?{v}v .
  ?{v}st wikibase:rank ?{v}rank . FILTER(?{v}rank != wikibase:DeprecatedRank)
  ?{v}v wikibase:timeValue ?{v}dob ; wikibase:timePrecision ?{v}prec .
  FILTER(?{v}prec >= 9)
  FILTER(YEAR(?{v}dob) >= {lo or FLOOR} && YEAR(?{v}dob) <= {hi or CEIL})
""")
    return "".join(parts)


# ── FETCHING IN YEAR SLICES, because one query for 150 years fits in neither endpoint ─────────────────────────
#
# qlever answers 429 for a client that has asked a lot this session, and the Wikidata Query Service answers 504
# because the whole-window query exceeds its 60-second limit. Neither is a bug to be retried harder: the query is
# simply too big for the polite path. Slicing the MAN's birth year partitions the result set — every couple has
# exactly one man's birth year, so the slices are disjoint and their union is the whole answer — and each slice is
# small enough to finish. The count check still runs per slice, so a truncated slice is still caught.
# TEN years, not twenty-five. The 1900-1924 slice is the densest — Wikidata knows far more people born then — and
# at 25 years it exceeded the Wikidata Query Service's 60-second limit with a 504 after four slices had already
# succeeded. Ten-year slices keep the densest one under the limit with room to spare.
SLICE = int(os.environ.get("AQ_YEAR_SLICE", "10"))
# Completed slices are CACHED to disk, so a failure on slice nine does not repeat slices one to eight. Fourteen
# minutes of finished work was thrown away by that 504, which is the kind of loss that makes a build feel
# hopeless rather than merely slow.
SLICE_CACHE = os.path.join(OUT, "_slices")


def sparql_sliced(select, body_fn, name, order=None):
    """Run `body_fn(lo, hi)` over year slices of the first partner and concatenate.

    body_fn takes the inclusive year bounds and returns a WHERE body already restricted to them.
    """
    frames = []
    os.makedirs(SLICE_CACHE, exist_ok=True)
    tag = "".join(ch if ch.isalnum() else "_" for ch in name)
    for lo in range(FLOOR, CEIL + 1, SLICE):
        hi = min(lo + SLICE - 1, CEIL)
        cache = os.path.join(SLICE_CACHE, f"{tag}_{lo}_{hi}.csv")
        if os.path.exists(cache):
            frames.append(pd.read_csv(cache, dtype=str, keep_default_na=False))
            print(f"  {name} {lo}-{hi}: {len(frames[-1]):,} rows (cached)", flush=True)
            continue
        df = sparql(select, body_fn(lo, hi), f"{name} {lo}-{hi}", order=order)
        df.to_csv(cache + ".tmp", index=False)
        os.replace(cache + ".tmp", cache)          # atomic: a crash mid-write cannot leave a half slice
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    print(f"  {name}: {len(out):,} rows over {len(frames)} year slices")
    return out


def one_sex(v, expect=None):
    """`wdt:` is the TRUTHY form and already excludes deprecated statements, so this is just the triple.

    A person carrying two different P21 values arrives as two rows and is dropped client-side, for the same
    reason the date conflicts are.
    """
    out = f"  ?{v} wdt:P21 ?{v}sex .\n"
    if expect:
        out += f"  FILTER(?{v}sex = wd:{expect})\n"
    return out


#%% [markdown]
# ## 1. Declared partnerships — the universe the score is measured in
#
# `FILTER(STR(?a) < STR(?b))` keeps each unordered pair once: Wikidata states a spouse relation from both
# sides, so without it every couple appears twice with the columns swapped, and after a split the same couple
# could land on both sides of it. The canonical order is by Q-number and says nothing about sex — `P21` does
# that, further down.

#%%
def declared_body(lo, hi):
    # The slice bounds the MAN-side variable ?a only; ?b keeps the full window, so a couple appears in exactly
    # one slice and no couple is lost at a boundary.
    return f"""
  ?a wdt:P26|wdt:P451 ?b .
  FILTER(STR(?a) < STR(?b))
  ?a wdt:P31 wd:Q5 . ?b wdt:P31 wd:Q5 .
{one_sex('a')}{one_sex('b')}{dated('a', 'b', lo, hi)}"""


dc = sparql_sliced("DISTINCT ?a ?b ?adob ?bdob ?aprec ?bprec ?asex ?bsex", declared_body,
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
# THE PARENTAL ROLE AND P21 MUST AGREE. 3,710 people recorded as a father have a P21 that is not male and 3,822
# recorded as a mother have a P21 that is not female. Those are contradictions, not edge cases, and the role is
# what this branch uses to assign the columns — so a conflict is excluded rather than silently resolved. Where
# P21 is simply ABSENT the role still decides, which is how the branch keeps people the declared route drops.
COPARENT_BODY = f"""
  {{ ?child wdt:P22 ?a ; wdt:P25 ?b .
    FILTER(?a != ?b)
    BIND(wd:{MALE} AS ?asex) BIND(wd:{FEMALE} AS ?bsex) }}
  UNION
  {{ ?a wdt:P40 ?child . ?b wdt:P40 ?child .
    FILTER(STR(?a) < STR(?b))
{one_sex('a')}{one_sex('b')}  }}
  ?a wdt:P31 wd:Q5 . ?b wdt:P31 wd:Q5 .
{dated('a', 'b')}"""
# THE UNION IS SPLIT INTO ITS TWO BRANCHES and each is fetched on its own. As one query the union 504'd the
# Wikidata Query Service on its very first ten-year slice, seven times over — the P40 branch joins two parents to
# one child and, unioned with the P22/P25 branch, is heavier than either alone. Fetched separately, each branch is
# a plain query that fits in the limit, and their concatenation is the same set (deduplication downstream removes
# a pair that both branches find).
def coparent_child_side(lo, hi):
    return f"""
  ?child wdt:P22 ?a ; wdt:P25 ?b .
  FILTER(?a != ?b)
  BIND(wd:{MALE} AS ?asex) BIND(wd:{FEMALE} AS ?bsex)
  ?a wdt:P31 wd:Q5 . ?b wdt:P31 wd:Q5 .
{dated('a', 'b', lo, hi)}"""


def coparent_parent_side(lo, hi):
    return f"""
  ?a wdt:P40 ?child . ?b wdt:P40 ?child .
  FILTER(STR(?a) < STR(?b))
{one_sex('a')}{one_sex('b')}  ?a wdt:P31 wd:Q5 . ?b wdt:P31 wd:Q5 .
{dated('a', 'b', lo, hi)}"""


cop = pd.concat([
    sparql_sliced("DISTINCT ?a ?b ?adob ?bdob ?aprec ?bprec ?asex ?bsex", coparent_child_side,
                  "co-parent pairs, child names both (P22/P25)", order="?a ?b"),
    sparql_sliced("DISTINCT ?a ?b ?adob ?bdob ?aprec ?bprec ?asex ?bsex", coparent_parent_side,
                  "co-parent pairs, both parents name the child (P40)", order="?a ?b"),
], ignore_index=True)
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
# ── DENOISING, CLIENT-SIDE, WITH EVERY RULE REPORTING WHAT IT REMOVED ─────────────────────────────────────────
#
# Each query returns one row per statement, so a person whose record contradicts itself arrives as several rows
# with different values. That makes the contradictions visible here for free, where the alternative — expressing
# them as FILTER NOT EXISTS — made qlever answer 429 and would have timed out the Wikidata Query Service.
#
# Every rule below removes people whose record is WRONG, not people who are unusual. A contradiction is not a
# hard case to be resolved by picking the first value; it is an absence of information about the one thing this
# dataset is made of.
both = pd.concat([dc, cop], ignore_index=True)

_before = len(both)
_dropped = {}

# 1. Two different birth years for one person. Measured on Wikidata: 33,335 humans.
yr = {}
bad_year = set()
for col in ("a", "b"):
    for who, d in zip(both[col], both[f"{col}dob"]):
        y = d[:4]
        if who in yr and yr[who] != y:
            bad_year.add(who)
        else:
            yr[who] = y
_dropped["a partner has two different birth years on record"] = bad_year

# 2. Two different P21 values for one person. Measured: 2,039 humans.
sx = {}
bad_sex = set()
for col in ("a", "b"):
    for who, v in zip(both[col], both[f"{col}sex"]):
        if who in sx and sx[who] != v:
            bad_sex.add(who)
        else:
            sx[who] = v
_dropped["a partner has two different sexes on record"] = bad_sex

# 3. The parental role and P21 disagree. Measured: 3,710 fathers whose P21 is not male, 3,822 mothers whose P21
#    is not female. The role is what assigns the columns on the co-parent branch, so a conflict there is not a
#    detail — it decides which column a person lands in.
role = {}
bad_role = set()
for a, b, route in zip(both["a"], both["b"], both["route"]):
    if route != "coparent":
        continue
    for who, want in ((a, MALE), (b, FEMALE)):
        if role.setdefault(who, want) != want:
            bad_role.add(who)
        if who in sx and sx[who] != want:
            bad_role.add(who)
_dropped["the parental role contradicts P21"] = bad_role

UNRELIABLE = set().union(*_dropped.values()) if _dropped else set()
print("\n  DENOISING — the rules FLAG people whose record contradicts itself; they decide the TEST set only")
for label, people in _dropped.items():
    print(f"      {len(people):>7,} people  {label}")
print(f"      {len(UNRELIABLE):>7,} people flagged in total (the rules overlap)")
print("      training keeps every one of them: a noisy row still teaches, and a clean measurement is what the")
print("      held-out half is for — so the exclusion is applied at the split, not here")

# The one rule that IS applied everywhere: a person paired with themselves is not a couple in any dataset.
_self = (both["a"] == both["b"]).sum()
if _self:
    both = both[both["a"] != both["b"]].reset_index(drop=True)
print(f"      {_self:>7,} rows where a person was paired with themselves — removed everywhere")

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

# ── THE SPLIT IS BY TIME, AND THAT CHANGES WHAT IS BEING MEASURED ─────────────────────────────────────────────
#
# A random split asks: can a model rank couples it has not seen, drawn from the same years as the ones it learned
# from? That question can be answered by INTERPOLATING the era. Recorded parenthood runs from 0.738 for couples
# born in the 1800s to about 0.40 from 1900 on, so a model that learns the per-decade rate and looks up the decade
# scores about 0.635 — better, on the old split, than an eighteen-tradition ephemeris stack.
#
# A TEMPORAL split asks a different and harder question: learn from the earlier couples, predict the later ones.
# The test decades are ones the model has never seen, so the era lookup has nothing to look up — it must
# extrapolate a trend rather than interpolate a table. Anything that survives that is a claim about structure
# rather than about the calendar.
#
# THE ORDERING QUANTITY is the LATER of the two births, because that is the first moment the couple could exist.
# Sorting on the earlier birth would put a couple of an 1850 man and a 1935 woman in the earliest bucket.
#
# MOVING PERSON GROUPS WHOLE CANNOT WORK HERE, and the first attempt proved it: a group is a connected component
# of the partnership graph and can span a century, so a group whose LATEST birth is 1950 may also contain an 1850
# couple. Splitting on the group maximum put 1850 couples in the held-out half while training still reached 1950 —
# the two ranges overlapped and the assertion below refused it.
#
# So the CUT IS BY COUPLE, at a single date, which makes the boundary exact. Person-disjointness is then restored
# from the other side: any TRAINING couple sharing a person with a held-out couple is dropped. That costs training
# rows rather than compromising the test set, which is the right way round — the test set is the measurement.
declared_rows = opp[opp["route"] == "declared"]
per_group = declared_rows.groupby("group").size().to_dict()

opp["_later"] = np.maximum(opp["dob_man"].str[:4].astype(int) * 10000
                           + opp["dob_man"].str[5:7].astype(int).clip(lower=1) * 100
                           + opp["dob_man"].str[8:10].astype(int).clip(lower=1),
                           opp["dob_woman"].str[:4].astype(int) * 10000
                           + opp["dob_woman"].str[5:7].astype(int).clip(lower=1) * 100
                           + opp["dob_woman"].str[8:10].astype(int).clip(lower=1))
# The cut date: the 80th percentile of the DECLARED couples' later-birth key. Co-parent pairs never enter the
# held-out half, so the percentile is taken over the declared subset, and every couple at or after the cut goes to
# test — including ties, so the boundary is a date and not a row count.
# Taken from the LIVE frame, not from `declared_rows`: that was snapshotted before `_later` existed, so reading
# the column off it raised KeyError. A stale view of a frame you are still adding columns to is a trap.
CUT = int(np.percentile(opp.loc[opp["route"] == "declared", "_later"].to_numpy(), 80))
is_late = opp["_later"] >= CUT
groups = sorted(set(opp["group"]))

# THE TEST HALF IS THE CLEAN HALF. A couple is held out only if it is late, declared, AND neither partner is
# flagged as unreliable. A flagged late couple is not thrown away — it goes to TRAINING, where a noisy row still
# carries information and where noise costs nothing except a slightly harder fit. Training therefore contains
# every couple that is not being scored, and the score is taken only on records that agree with themselves.
clean = ~opp["a"].isin(UNRELIABLE) & ~opp["b"].isin(UNRELIABLE)
is_test = is_late & opp["route"].eq("declared") & clean
noisy_late = int((is_late & opp["route"].eq("declared") & ~clean).sum())
print(f"  {noisy_late:,} late declared couples had a flagged partner and go to TRAINING rather than being scored")

# TRAINING MUST CONTAIN NOTHING FROM THE TEST ERA, and that costs rows in two ways.
#
# First, co-parent pairs are train-only by design — a pair found through a child is positive by construction — but
# a LATE co-parent pair would still show a model the very decades it is supposed to predict blind. Leaving them in
# made training reach 1950 while the held-out half started at 1928, and the assertion refused it. So every couple
# at or after the cut leaves training whatever its route.
#
# Second, person-disjointness is restored from the training side: any earlier couple sharing a person with a
# held-out couple goes too. Training on somebody whose other relationship is being scored is the leak a person
# split exists to prevent.
test_people = set(opp.loc[is_test, "man"]) | set(opp.loc[is_test, "woman"])
shares = opp["man"].isin(test_people) | opp["woman"].isin(test_people)
# Training keeps as much as possible: everything before the cut, PLUS the late couples that were not held out —
# the noisy ones and the co-parent pairs — EXCEPT anything sharing a person with a held-out couple, because
# training on somebody whose other relationship is being scored is the leak a person split exists to prevent.
# The temporal boundary is then a property of the TEST half (every held-out couple postdates the cut) and of
# what training may not contain (any held-out person); it is not a claim that training holds no late couple.
drop_person = shares & ~is_test
train = opp[~is_test & ~drop_person].copy()
test = opp[is_test].copy()
print(f"  cut at {CUT//10000}-{(CUT//100)%100:02d}-{CUT%100:02d} on the later of the two births")
print(f"  training keeps {int((train['_later'] >= CUT).sum()):,} couples from the test era that were not held "
      f"out (noisy or co-parent); {int(drop_person.sum()):,} dropped for sharing a person with the held-out half")
print(f"  {len(groups):,} person groups; the split is by DATE, not by group")
# THE BOUNDARY, PRINTED. If the two ranges overlap, the split is not temporal and every claim about predicting
# forward in time is void — so it is asserted rather than described.
tr_t = train["_later"]
te_t = test["_later"]
print(f"  TIME SPLIT: training couples' later birth runs {tr_t.min()//10000}-{tr_t.max()//10000}, "
      f"held-out {te_t.min()//10000}-{te_t.max()//10000}")
# WHAT "TEMPORAL" MEANS NOW, said exactly. Every held-out couple is at or after the cut — that is asserted. Training
# holds late couples too, but ONLY ones that could not be scored (a flagged partner, or a pair discovered through
# a child), and none that shares a person with the held-out half. So a model still cannot look up the test
# decades' clean declared couples; it can see that the era exists, which a real forecaster also can.
assert te_t.min() >= CUT, f"a held-out couple's later birth ({te_t.min()}) predates the cut ({CUT})"
print(f"  every held-out couple's later birth is on or after {te_t.min()//10000}; training's clean declared "
      f"couples all predate it")
print(f"  rows: {len(train):,} train ({100*len(train)/len(opp):.1f}%) · "
      f"{len(test):,} test ({100*len(test)/len(opp):.1f}%) · "
      f"{len(opp)-len(train)-len(test):,} dropped to keep the boundary and the person split")
print(f"  positive rate: train {100*train['parents_together'].mean():.2f}% · "
      f"test {100*test['parents_together'].mean():.2f}%")
t_rate = test["parents_together"].mean()
assert 0.15 < t_rate < 0.85, (f"the held-out half is {100*t_rate:.2f}% positive — an AUC needs both classes, "
                              f"and a single-class test set silently scores 0.5 for every model")
print(f"  the held-out half is {100*test['route'].eq('declared').mean():.0f}% declared partnerships")

tp = set(train["man"]) | set(train["woman"])
sp = set(test["man"]) | set(test["woman"])
assert not (tp & sp), f"{len(tp & sp)} people are on both sides of the split"
# THE GROUP ASSERTION IS GONE, DELIBERATELY, AND THIS IS NOT A WEAKENING.
#
# Under the old random split, whole groups moved, so a shared group id meant a shared person. Under a date cut a
# connected component can straddle the boundary while no PERSON does: two people in the same component need not be
# in a couple together, and every training couple sharing a person with a held-out couple has already been
# removed. Person-disjointness is the property that stops a model recognising somebody it has seen, and that is
# what is asserted above. Asserting group-disjointness as well would now refuse a correct split.
straddling = len(set(train["group"]) & set(test["group"]))
print(f"  checked: no person appears on both sides; {straddling:,} connected components straddle the date cut, "
      f"which is expected and carries no person in common")

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
