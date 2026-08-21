#%% [markdown]
# # Two birth dates, one question: did the marriage last thirty years?
#
# This notebook builds the **ArtaMatch Duration** dataset from scratch, from live SPARQL against Wikidata. Every
# query is in the cells below, so anyone can re-run them and get a different answer as Wikidata changes.
#
# Four columns. That is the whole file.
#
# | column | meaning |
# |---|---|
# | `dob_dad` | the man's date of birth (Wikidata P21 male) |
# | `dob_mom` | the woman's date of birth (P21 female) |
# | `lat_dad`, `lon_dad` | his place of birth, decimal degrees (empty when Wikidata has none) |
# | `lat_mom`, `lon_mom` | her place of birth |
#
# **The columns are ordered by SEX in this edition (operator, 2026-08-18: "switch to gendered model (mom and
# dad) instead of old first"): dad first, mom second, read from P21.** A pair that is not one man and one woman
# has no such order and is excluded from this edition, counted in the build log. The two-dates editions order by
# age and read no sex; they keep every couple. An absent partner (`0000-00-00`) may now be in EITHER column.
# | `start` | the date the relationship began — the wedding date for a marriage — `YYYY-MM-DD` |
#
# **The place of birth is an input (third edition, operator 2026-08-18: "use pob and the local time to encode
# their time of birth as 9:00 AM").** Nobody's birth TIME is in Wikidata, so every chart in this project is cast
# at a fixed hour; with the place known that hour can be a LOCAL one -- 09:00 at the birthplace, converted to
# UT through the historical time zone of the coordinates -- which gives the chart an ascendant and houses for
# the first time. The convention is the dataset's, stated here, not a fact about anyone: 09:00 local, every row.
# | `lasted_30_years` | 1 if the relationship lasted thirty years or longer, else 0 |
#
# **The start is an input now (operator, 2026-08-18: "start over and use marriage year", then "use jan 1 for
# all").** The first edition computed the label from the relationship's own dates and discarded them; this one
# keeps the START, as a full date. Wikidata's `P580` qualifier is often year-precision and the query did not fetch
# that qualifier's precision flag, so a year-only start comes back as `YYYY-01-01` -- and that is what is
# published, on the operator's instruction. The consequence is stated rather than hidden: a start of `1 January`
# in this file is USUALLY a year-only record and only sometimes a real New Year's Day wedding, and nothing in
# the value tells the two apart. The year is exact in every row. What the column buys a model: each partner's
# AGE at the start, the era the relationship began in, the wedding chart where the day is real, and -- for the
# held-out half -- the ceiling on how long it could possibly have run before 2026 (see the test filter below).
#
# **Any relationship two people chose**: a marriage (`P26`), an unmarried or same-sex partnership (`P451`), a
# business or sporting partnership (`P1327`), or Wikidata's general "significant person" relation (`P3342`, with
# every pair that also carries a family link excluded). Family relations are not here — a sibling does not
# "last".
#
# The first column is the **older** partner, computed from the two dates themselves. **Nothing here reads a
# sex**, which is why same-sex couples are included by construction rather than by a special case. The
# relationship's own dates are used to compute the third column and are then **thrown away**; they are not
# inputs.
#
# ## The two halves are built by different rules, deliberately
#
# **The test set is strict.** Both partners known to the day, both **dead**, no placeholder dates, and the
# couple's **later** birth after 1900. That is what the leaderboard is scored on, so it is the half that must not
# be noisy.
#
# Note "later birth", not "both births". A man born 1895 married to a woman born 1910 is a held-out couple: the
# split places a couple by when the second of them was born. Requiring both partners after the cut dropped 1,416
# day-precision couples — 11.1% of the test half — out of the dataset entirely, since the training queries would
# not take them either.
#
# **The training set is as inclusive as the data allows.** A date may be known only to the month or only to the
# year, and **one partner may be missing from Wikidata entirely**. All three of these are real training rows:
#
# ```
# dob_dad,dob_mom,start,lasted_30_years
# 1794-06-12,1801-03-27,1823-05-19,1     <- both known to the day; wed 19 May 1823
# 1802-00-00,1809-11-00,1831-01-01,0     <- one year only; the other's year and month; the start known to the year
# 1777-04-30,0000-00-00,1799-09-02,1     <- the partner is not in Wikidata at all, and the row is still worth learning from
# ```
#
# `00` means unknown and `0000-00-00` means absent, so precision is visible in the value rather than hidden in a
# separate column. A model that wants only clean rows filters them in one line; a model that wants every marriage
# has them. This is not a rounding decision — measured on Wikidata, it is an order of magnitude:
#
# | training rule | pairs |
# |---|---|
# | both partners known to the day | 12,661 |
# | both partners, any precision | 30,110 |
# | at least one partner, any precision | 86,602 |
# | **the same, with the window opened to 1900 by requiring death** | **135,619** |
#
# A marriage's duration is known just as exactly when one spouse's birthday is not, so a one-sided row carries a
# real label and half the input. Discarding it was throwing away six sevenths of the data.

#%% [markdown]
# ## Where the label comes from
#
# Wikidata records a marriage as a `P26` statement with qualifiers, which an infobox renders like this:
#
# > **Spouses**  Mileva Marić (m. 1903; div. 1919) · Elsa Löwenthal (m. 1919; died 1936)
#
# Those are the two cases, and the duration is computed exactly as the infobox reads:
#
# * **an end date is recorded** (`P582`) — the marriage ran from `P580` to `P582`. Einstein's first: 16 years.
# * **no end date** — it ran until somebody died, so the end is the EARLIER of the two death dates (`P570`).
#   Einstein's second: 1919 to Elsa's death in 1936, 17 years.
#
# `lasted_30_years` is `(end − start) >= 30 years` and nothing else. **A marriage ended by a death is not
# automatically a long one**: twelve years is a 0, forty years is a 1. Death buys no credit.
#
# The third column is this classification rather than the duration in years because the competition is scored by
# AUC, which needs a binary label. The duration is what produces it and is printed in the summaries below.
#
# ## Death is the boundary, not a birth year
#
# A marriage that has not ended cannot be given a duration. An earlier version of this dataset handled that by
# stopping at births of 1900, on the grounds that everybody born by then is certainly dead — which is true, and
# also a proxy. Requiring a recorded **death** proves the same thing directly and without a ceiling, so the
# window runs to the present: **train on births 1600–1900, hold out 1901 onward**, and require the partner whose
# date we have to be dead. That is worth 135,619 pairs against 86,602.
#
# The split is **temporal**: learn from the historical couples and predict the modern ones. Not "rank couples
# drawn from the years you learned from".
#
# **AND IT INTRODUCES ITS OWN BIAS, which the build measures rather than hopes about.** A couple born recently who
# are ALREADY DEAD died young, and a marriage cannot outlive its shorter-lived partner. Past roughly 1996 a
# thirty-year marriage is arithmetically impossible for anyone dead by now, so the positive rate must fall to zero
# at the recent end whatever astrology says — and "born late → negative" is an era rule, not a finding. The build
# prints the positive rate per birth decade, names every decade where the positive class is unreachable, and says
# what share of each half sits in them. Read the held-out score against that table.
#
# ## The one confound worth naming out loud
#
# The two label cases behave very differently: marriages with a recorded END date reach thirty years about 16% of
# the time, while marriages that ran until a death do so about 53% of the time. A model cannot see which case a
# couple is in — that is not a column — but "ended while both spouses were alive" correlates with things it can
# see. This is the sharpest confound in the design, and the published baselines include a case-only reference so
# a leaderboard place can be read against it.
#
# ## Two traps in the dates, both measured
#
# **1 January is a placeholder, and it is excluded from the TEST HALF ONLY.** Among day-precision births
# 1600–1900 it occurred **2.07×** as often as a median January day, while 2 January sits at 1.00× — a source that
# knew only the year was imported with a day anyway. The test half is the measurement and must not contain dates
# claiming a precision they do not have; the training half keeps them, because 193 pairs of noise are worth more
# than 193 fewer rows.
#
# It is never excluded at year precision, in either half, where `1850-01-01` is simply how Wikidata spells
# "1850": a filter that removed them there deleted every coarse date in the file, and was quietly costing 17,000
# training couples before the interaction was measured.
#
# **The calendar is one calendar, and the placeholder moves inside it.** Wikidata's RDF gives every date in the
# proleptic **Gregorian** calendar whatever `timeCalendarModel` says — Newton's Julian-tagged statement carries
# the literal `1643-01-04`, the Gregorian image of 25 December 1642. So no conversion is needed and no date is on
# a different footing from another. But it means a **Julian** 1 January placeholder is stored as 11, 12 or 13
# January depending on the century, and that excess is measurably there: **2.08×** the median January day at 13
# January among Julian-tagged records, where 11 and 12 January sit at 0.68× and 1.04×. Excluded at the
# century-correct date, for Julian-tagged records only — and again, from the test half only.
#
# ## Every marriage of every person, and each couple once
#
# A person with three spouses contributes three rows: the dedup key is the COUPLE, never the person. What
# collapses is the same pair arriving twice — which it does routinely, because the one-sided query runs from each
# partner's side independently. Of those copies the better-dated one wins, and a couple who married each other
# twice keeps its longest marriage, since the question is whether these two sustained one.

#%%
import collections
import concurrent.futures
import hashlib
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
T0 = time.time()

# THE WINDOW IS NOW BOUNDED BY DEATH, NOT BY A BIRTH YEAR (operator, 2026-08-17). The old design closed at 1900
# because everybody born by then is certainly dead, and a marriage that has not ended cannot be given a duration.
# Requiring a recorded DEATH does that job directly and without a ceiling: if the partner we have a date for is
# dead, their marriage has ended, whenever they were born. So the span opens to the present and the split moves to
# 1900 — train on the historical couples, predict the modern ones.
FLOOR = 1600
CEIL = int(os.environ.get("AQ_CEIL", str(time.gmtime().tm_year)))
CUT = 1900                        # couples whose later known birth is after this are held out
MIN_YEARS = int(os.environ.get("AQ_MIN_YEARS", "30"))     # the label's threshold (EDITION V, operator 2026-08-20: 50 — the sweep showed AUC rising with the cut while 50 keeps an 11% positive class)
LABEL = f"lasted_{MIN_YEARS}_years"
# DATA-ERROR CEILING: one train "marriage" read 173 years (a wrong-century end date). Nothing real outlasts the
# test half's own maximum (91), so anything past 85 is a recording error, dropped and counted — never labelled.
MAX_DUR_YEARS = float(os.environ.get("AQ_MAX_DUR_YEARS", "85"))
MAX_GAP_YEARS = 60
# THE RELATIONSHIPS. Any partnership two people chose: marriage, an unmarried partnership, a business or sporting
# partnership, and Wikidata's general "significant person" relation. Family relations (sibling, relative,
# godparent) and student-of are NOT here: they are not chosen partnerships and "lasting" means nothing for a
# sibling. Measured 2026-08-17 with a start date, one dated partner and a datable end: P26 212,444 pairs,
# P451 4,766, P3342 1,158, P1327 665. Same-sex marriages number 123 and are in by construction, since nothing
# here reads a sex.
RELS = {"P26": "marriage", "P451": "unmarried partnership",
        "P1327": "business or sport partnership", "P3342": "significant person (non-family)"}

# THIRD EDITION, operator 2026-08-18: "clean up the dataset and only allow male x female marriages". AQ_RELS
# restricts the relationship types built into the CSVs -- P26 alone for this edition -- without touching the
# queries or the cache (each type is its own cached family). The male + female requirement is applied by
# order_by_sex; the two together make this a dataset of marriages between a man and a woman, and nothing else.
_ONLY = [r for r in os.environ.get("AQ_RELS", "").split(",") if r]
if _ONLY:
    RELS = {k: v for k, v in RELS.items() if k in _ONLY}
    print(f"  AQ_RELS: this build keeps only {sorted(RELS)}", flush=True)
JULIAN = "Q1985786"
# TEN, BECAUSE THAT IS WHAT THE CACHE IS. The whole slice cache on disk was fetched in ten-year slices, and a
# slice is looked up under `{tag}_{lo}_{hi}.csv`, so a run at any other width misses every file and starts
# refetching from a rate-limited endpoint -- which is exactly what a fresh run at the old default of 25 did
# (2026-08-18: "6 slices, 6 to fetch" against a complete cache, then qlever 429s). The width is part of the
# cache key in effect if not in name.
SLICE = int(os.environ.get("AQ_YEAR_SLICE", "10"))
ABSENT = "0000-00-00"

# The end causes Wikidata records on a marriage, looked up rather than guessed. Used only to REPORT how the file
# breaks down; the label is duration and never reads the cause.
BREAKDOWN = {"Q93190": "divorce", "Q701040": "annulment", "Q5561011": "marital separation",
             "Q3456503": "repudiation", "Q1299585": "declaration of nullity", "Q1142948": "legal separation"}
DEATHCAUSE = {"Q24037741": "death of spouse", "Q99521170": "death of subject", "Q4": "death",
              "Q90110620": "death of partner", "Q179115": "widow"}

ENDPOINTS = ["https://qlever.dev/api/wikidata", "https://query.wikidata.org/sparql"]

# A RATE LIMIT EXPIRES, SO THE STRIKE-OFF HAS TO EXPIRE TOO. This was a permanent set: the first endpoint to
# answer 429 six times was abandoned for the rest of the run. On a build that takes hours that is exactly wrong —
# qlever's limit lifted after about forty minutes while the build was still grinding through WDQS 502s, unable to
# go back to the endpoint that was answering trivial queries in 0.2s. `_DEAD` now records WHEN each endpoint was
# struck off and lets it back in after a cooldown. Permanent skips still exist, via AQ_SKIP_ENDPOINTS, because
# that is a human deciding rather than a heuristic guessing.
_DEAD = {}                      # base -> monotonic time it was struck off
_BANNED = set()                 # never retried, operator's choice
DEAD_COOLDOWN = float(os.environ.get("AQ_ENDPOINT_COOLDOWN", "600"))
for _ep in os.environ.get("AQ_SKIP_ENDPOINTS", "").split(","):
    if _ep.strip():
        _BANNED.update(b for b in ENDPOINTS if _ep.strip() in b)


def live_endpoints():
    """Endpoints worth trying now: never-banned, and either never struck off or past their cooldown."""
    now = time.monotonic()
    for base, when in list(_DEAD.items()):
        if now - when >= DEAD_COOLDOWN:
            del _DEAD[base]
            print(f"    {base.split('/')[2]}: cooldown elapsed — trying it again", flush=True)
    out = [b for b in ENDPOINTS if b not in _BANNED and b not in _DEAD]
    # Never return nothing: if everything is cooling down, try whatever is not permanently banned rather than
    # failing the run on a timer.
    return out or [b for b in ENDPOINTS if b not in _BANNED] or list(ENDPOINTS)

UA = "ArtaMatch/4.0 (https://www.artaquest.com) marriage duration dataset build"

PREFIXES = """
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX wikibase: <http://wikiba.se/ontology#>
"""


def _fetch(query, accept, tries=6):
    """One HTTP call, with backoff, a fallback endpoint, and a rate-limited endpoint struck off for the run.

    Each endpoint has its own failure mode and neither is fixed by retrying harder: qlever answers 429 to a
    client that has asked a lot, and the Wikidata Query Service answers 504 when a query exceeds its 60 seconds.
    Slicing keeps queries small enough for the second; striking off saves paying six backoffs per query to
    rediscover the first.
    """
    last = None
    live = live_endpoints()
    for base in live:
        # TRANSLATE the requested format for this endpoint; do NOT override it. This line used to read
        # `"application/sparql-results+json" if "query.wikidata.org" in base else accept`, which was right for
        # the COUNT path (qlever's JSON dialect name means nothing to WDQS) and silently wrong for the PAGING
        # path, which asks for TSV. WDQS then answered JSON, `read_csv(sep="\t")` parsed the JSON text as a
        # single column named `{`, and the truncation check passed because 91,142 lines of JSON is more rows
        # than the query expected. Two whole slices of the build were garbage that looked fine.
        acc = accept
        if "query.wikidata.org" in base and "json" in accept:
            acc = "application/sparql-results+json"
        for attempt in range(tries):
            req = urllib.request.Request(base + "?" + urllib.parse.urlencode({"query": query}),
                                         headers={"Accept": acc, "User-Agent": UA})
            try:
                # 300s, not 900. WDQS answers or 504s inside 60s and qlever cost-429s inside 30s, so a socket
                # that is still open at five minutes is a hang, not a slow answer -- and at 900s a single hang
                # cost fifteen minutes. Build 12 made zero progress in an hour with only ten HTTP failures logged;
                # the rest of the hour was spent inside stalled sockets.
                with urllib.request.urlopen(req, timeout=300) as r:
                    return r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                last = e
                if e.code not in (429, 500, 502, 503, 504):
                    raise
                # A 429 ON A HEAVY QUERY DOES NOT CLEAR IN 80 SECONDS, so do not spend 155s of backoff
                # rediscovering that. qlever answers a trivial query 200 while refusing these, which means its
                # limit is priced on query COST, not request count — the budget is spent and waiting inside one
                # request cannot refill it. Give up after two tries and let the cooldown bring the endpoint
                # back later, when it can actually help. A 5xx still gets the full backoff: that IS often
                # transient.
                patience = 2 if e.code == 429 else tries
                if attempt >= patience - 1:
                    if e.code in (429, 500, 502, 503):
                        _DEAD[base] = time.monotonic()
                        print(f"    {base.split('/')[2]}: HTTP {e.code} — struck off for "
                              f"{DEAD_COOLDOWN/60:.0f} min, then retried", flush=True)
                    break
                wait = min(90, 5 * (2 ** attempt))
                print(f"    {base.split('/')[2]}: HTTP {e.code}; waiting {wait}s", flush=True)
                time.sleep(wait)
            except Exception as e:
                last = e
                if attempt == tries - 1:
                    break
                time.sleep(5 * (attempt + 1))
    raise last if last else RuntimeError("no endpoint answered")


def sparql_count(select, body, tries=4):
    """How many rows the query should return, counted through the SAME projection it is read with.

    A 200 IS NOT NECESSARILY JSON. WDQS answers a stressed request with HTTP 200 and a truncated or non-JSON
    body — seen live as `JSONDecodeError after every retry` — and `_fetch` cannot catch that, because it retries
    on status codes and 200 is a success. So the parse is the real health check, and a body that will not parse
    is treated as the transient server failure it is rather than escalated to the caller. Without this, one
    truncated response spent a slice's entire retry budget re-issuing an expensive query.
    """
    q = f"{PREFIXES}\nSELECT (COUNT(*) AS ?n) WHERE {{ {{ SELECT {select} WHERE {{ {body} }} }} }}"
    raw = None
    for attempt in range(tries):
        raw = _fetch(q, "application/qlever-results+json")
        try:
            d = json.loads(raw)
            break
        except ValueError:
            if attempt == tries - 1:
                raise RuntimeError(f"the count endpoint answered 200 with {len(raw)} bytes that are not JSON, "
                                   f"{tries} times: {raw[:160]!r}")
            wait = 10 * (attempt + 1)
            print(f"    count: 200 with a non-JSON body ({len(raw)} bytes) — waiting {wait}s and asking again",
                  flush=True)
            time.sleep(wait)
    if isinstance(d.get("res"), list) and d["res"]:
        return int(str(d["res"][0][0]).split('"')[1])
    binds = (d.get("results") or {}).get("bindings") or []
    if binds:
        return int(next(iter(binds[0].values()))["value"])
    raise RuntimeError(f"count failed on both dialects: {str(d)[:200]}")


def sparql(select, body, name, order=None, page=200000):
    """Pages, then checks the SHAPE and the row count.

    A row count alone is not a validation. When the endpoint answered JSON to a TSV request, every response
    parsed into one column called `{` — and the count check passed, because a JSON document has more lines than
    the query had rows. So the projected variables are asserted to be present before anything is returned: the
    columns are the thing that proves the parse, and the count only proves nothing was dropped.
    """
    t = time.time()
    want = sparql_count(select, body)
    expect = [v.lstrip("?") for v in select.replace("DISTINCT", "").split()]
    frames, got = [], 0
    while got < want:
        q = (f"{PREFIXES}\nSELECT {select} WHERE {{ {body} }}" + (f" ORDER BY {order}" if order else "")
             + f" LIMIT {page} OFFSET {got}")
        raw = _fetch(q, "text/tab-separated-values")
        df = pd.read_csv(io.StringIO(raw), sep="\t", dtype=str, keep_default_na=False)
        got_cols = [c.strip().lstrip("?") for c in df.columns]
        missing = [v for v in expect if v not in got_cols]
        if missing:
            raise RuntimeError(
                f"{name}: the response is not the TSV this query projected — missing {missing}, got columns "
                f"{got_cols[:6]}. The first 120 bytes were {raw[:120]!r}. A row count cannot catch this, which "
                f"is why the columns are checked.")
        if len(df) == 0:
            break
        # The Wikidata Query Service decorates values with a type suffix and quotes literals; qlever's TSV is
        # plain. Normalise so both dialects parse to the same frame.
        for c in df.columns:
            df[c] = (df[c].str.replace(r"\^\^<[^>]*>$", "", regex=True)
                          .str.replace(r'^"(.*)"$', r"\1", regex=True))
        frames.append(df)
        got += len(df)
    # AN EMPTY RESULT STILL HAS COLUMNS. A slice that legitimately returns nothing -- births 2001-2025 with both
    # partners dead -- used to come back as pd.DataFrame(), which has no columns, was cached as a one-byte file,
    # and crashed the NEXT run with EmptyDataError the moment it was read back. Zero rows is an answer; a file
    # with no header is not one.
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=expect)
    out.columns = [c.strip().lstrip("?") for c in out.columns]
    for c in out.columns:
        out[c] = out[c].str.strip().str.strip('"')
    if len(out) < want:
        raise RuntimeError(f"{name}: got {len(out):,} rows, endpoint counted {want:,} — truncated, and a "
                           f"truncated marriage list silently mislabels couples")
    print(f"  {name}: {len(out):,} rows in {time.time()-t:.0f}s (count-verified)", flush=True)
    return out


SLICE_CACHE = os.path.join(OUT, "_dslices")


_WHOLE_TOO_BIG = set()      # query tags that already failed as one request; do not pay the timeout twice
SLICE_FREE_MAX = 60000     # a result set this small has never timed out; slicing it only multiplies round trips


def sparql_sliced(select, body_fn, name, lo0, hi0, order=None):
    """Fetch in year slices and concatenate; each slice cached atomically so a 429 costs one slice, not the run.

    SLICING IS A TIMEOUT REMEDY, NOT A HABIT. The Wikidata Query Service gives a query 60 seconds, so a large
    result set has to be cut into pieces — but asking for a small one in eleven pieces pays eleven round trips
    and eleven chances of a 429 to fetch what one query returns comfortably. P451 (unmarried partner) is the
    case that made this obvious: 112 partnerships in the whole 1600-1900 window, and the sliced version was
    spending 22 of the build's 41 remaining requests on them. So the whole-window count is asked for first, and
    a small answer is fetched in one go.
    """
    frames = []
    os.makedirs(SLICE_CACHE, exist_ok=True)
    # THE CACHE KEY INCLUDES THE QUERY, not just its name. It used to be the name alone, which meant editing a
    # query while keeping its label served the OLD answer forever — and the edit that exposed this added a
    # column, so the stale rows would have come back with the wrong shape under the right name. A cache keyed on
    # anything less than the request is a cache that can lie about what it holds.
    qhash = hashlib.sha256((select + "|" + body_fn(lo0, hi0)).encode()).hexdigest()[:10]
    tag = "".join(ch if ch.isalnum() else "_" for ch in name) + "_" + qhash
    whole = os.path.join(SLICE_CACHE, f"{tag}_{lo0}_{hi0}_whole.csv")
    if os.path.exists(whole):
        out = pd.read_csv(whole, dtype=str, keep_default_na=False)
        print(f"  {name}: {len(out):,} rows (cached, unsliced)", flush=True)
        return out
    # Either step here may fail — the count can 504 and so can the single big fetch, since a small result set is
    # not necessarily a fast query. Both failures fall through to slicing, which is the whole point of keeping
    # slicing around; the only thing that must not happen is failing the run over an optimisation.
    # THE UNSLICED ATTEMPT IS WORTH ONE TRY AND NOT MORE. It pays a full 504 -- about 65 seconds -- at the head
    # of every sliced query, and once a run has learned that a query is too big for one request, every later
    # query of the same shape pays it again for nothing. The memo is keyed on the query HASH, so it stops the
    # SAME query paying twice within a run and deliberately does NOT generalise across relationship types --
    # P451 is 4,766 pairs and fits one request comfortably where P26 does not, and assuming otherwise would slice
    # a query that needs no slicing into thirty. AQ_NO_WHOLE=1 skips the attempt outright, which is the right
    # setting only when every remaining query is known to be large.
    # The unsliced attempt is remembered only within a process (`_WHOLE_TOO_BIG` is a set), so a FRESH run pays
    # it again for every family -- and the very first thing a fresh run does is hit qlever with the biggest
    # query it has, get struck off for ten minutes, and print nothing else for that long. When the slice cache is
    # already complete there is nothing to gain from it, so it is skipped by default whenever the cache
    # directory exists; AQ_NO_WHOLE=0 forces the attempt.
    skip_whole = os.environ.get("AQ_NO_WHOLE", "1" if os.path.isdir(SLICE_CACHE) else "0") == "1"
    if skip_whole or tag in _WHOLE_TOO_BIG:
        print(f"  {name}: skipping the unsliced attempt (known too big for one request)", flush=True)
        raise_whole = False
    else:
        raise_whole = True
    stage = "whole-window count"
    try:
        if not raise_whole:
            raise RuntimeError("skipped")
        n = sparql_count(select, body_fn(lo0, hi0))
        if n > SLICE_FREE_MAX:
            print(f"  {name}: {n:,} rows over {lo0}-{hi0} — slicing by {SLICE} years", flush=True)
        else:
            print(f"  {name}: {n:,} rows over the whole {lo0}-{hi0} window — small enough for one query",
                  flush=True)
            stage = "unsliced fetch"
            out = sparql(select, body_fn(lo0, hi0), name, order=order)
            out.to_csv(whole + ".tmp", index=False)
            os.replace(whole + ".tmp", whole)
            return out
    except Exception as e:
        if raise_whole:
            _WHOLE_TOO_BIG.add(tag)
            print(f"  {name}: {stage} failed ({type(e).__name__}: {str(e)[:80]}) — falling back to "
                  f"{SLICE}-year slices", flush=True)
    # SLICES RUN CONCURRENTLY, because the wall clock is dominated by WAITING rather than by querying.
    # Measured over 33 minutes of one build: 19 slices fetched, 7 minutes actually inside queries, 26 minutes
    # in retry sleeps after 504s and 502s. Serially, a stuck slice blocks every slice behind it; concurrently,
    # its sleep overlaps their work. The cap is deliberately small -- WDQS's own guidance is around five
    # concurrent queries, and the goal is to stop wasting our own sleeps, not to lean on their service.
    #
    # Each slice is independent and cached under its own name, so this changes nothing about the result: the
    # frames are reassembled in slice order below, not in completion order.
    WORKERS = max(1, int(os.environ.get("AQ_SLICE_WORKERS", "4")))
    ROUNDS = int(os.environ.get("AQ_SLICE_ROUNDS", "12"))
    spans = []
    for lo in range(lo0, hi0 + 1, SLICE):
        hi = min(lo + SLICE - 1, hi0)
        cache = os.path.join(SLICE_CACHE, f"{tag}_{lo}_{hi}.csv")
        if os.path.exists(cache) and os.path.getsize(cache) < 8:
            # A one-byte file is the columnless-empty bug from an earlier build. Refetch rather than crash.
            print(f"  {name} {lo}-{hi}: cached file is headerless — refetching", flush=True)
            os.remove(cache)
        spans.append((lo, hi, cache))

    def one_slice(span):
        lo, hi, cache = span
        if os.path.exists(cache):
            df = pd.read_csv(cache, dtype=str, keep_default_na=False)
            print(f"  {name} {lo}-{hi}: {len(df):,} rows (cached)", flush=True)
            return df
        for round_ in range(ROUNDS):
            try:
                df = sparql(select, body_fn(lo, hi), f"{name} {lo}-{hi}", order=order)
                df.to_csv(cache + ".tmp", index=False)
                os.replace(cache + ".tmp", cache)
                return df
            except Exception as e:
                # A slice whose fetch exhausts every endpoint sleeps and tries the whole slice again, growing
                # 3, 6, 9 ... up to 15 minutes over twelve rounds -- about two hours of patience. A build has to
                # OUTLAST an outage rather than need a person at 2am, and every slice already fetched is cached.
                if round_ == ROUNDS - 1:
                    raise
                wait = min(900, 180 * (round_ + 1))
                print(f"    {name} {lo}-{hi}: {type(e).__name__} after every retry — sleeping {wait//60} min, "
                      f"then round {round_ + 2} of {ROUNDS}", flush=True)
                time.sleep(wait)

    todo = [sp for sp in spans if not os.path.exists(sp[2])]
    if WORKERS > 1 and len(todo) > 1:
        print(f"  {name}: {len(spans)} slices, {len(todo)} to fetch, {WORKERS} at a time", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            frames = list(pool.map(one_slice, spans))
    else:
        frames = [one_slice(sp) for sp in spans]
    out = pd.concat(frames, ignore_index=True)
    print(f"  {name}: {len(out):,} rows over {len(frames)} slices", flush=True)
    return out


def qid(s):
    return s.rsplit("/", 1)[-1].rstrip(">") if isinstance(s, str) and s else ""


#%% [markdown]
# ## 1. The date filter, precision-aware and calendar-aware
#
# Three things this gets right that a simpler version does not.
#
# **The precision floor is a parameter**, because the two halves want different ones: 11 (day) for the test set,
# 9 (year) for training.
#
# **The 1 January exclusion is gated on precision.** `FILTER(!(MONTH = 1 && DAY = 1))` applied at year precision
# deletes the entire coarse half of the data, because `1850-01-01` is how Wikidata spells the year 1850.
#
# **The Julian image of 1 January is excluded at the century-correct date** — 11 Jan for births to 1700, 12 Jan
# to 1800, 13 Jan after — for records `timeCalendarModel` marks as Julian.
#
# `wikibase:rank != DeprecatedRank` drops birth dates Wikidata has explicitly marked wrong.

#%%
def dated(v, lo, hi, prec, drop_placeholders=True):
    """The birth-date pattern. `drop_placeholders` excludes the 1 January artefacts.

    THE PLACEHOLDER EXCLUSION IS FOR THE TEST HALF ONLY (operator, 2026-08-17). It costs 193 of 86,804 pairs, so
    it was never about volume — but the test half is the measurement and must not contain dates claiming a
    precision they do not have, while the training half is better off with the noise than short of the rows.

    Both exclusions travel on one flag because they are the same artefact seen twice: a source that knew only the
    year, imported with a day anyway. In a Gregorian-dated record that lands on 1 January; in a Julian-dated one
    the RDF's Gregorian rendering puts it on 11, 12 or 13 January depending on the century.
    """
    s = f"""
  ?{v} p:P569 ?{v}st . ?{v}st psv:P569 ?{v}val .
  ?{v}st wikibase:rank ?{v}rank . FILTER(?{v}rank != wikibase:DeprecatedRank)
  ?{v}val wikibase:timeValue ?{v}dob ; wikibase:timePrecision ?{v}prec ;
          wikibase:timeCalendarModel ?{v}cal .
  FILTER(?{v}prec >= {prec})
  FILTER(YEAR(?{v}dob) >= {lo} && YEAR(?{v}dob) <= {hi})"""
    if drop_placeholders:
        s += f"""
  FILTER(!(?{v}prec >= 11 && MONTH(?{v}dob) = 1 && DAY(?{v}dob) = 1))
  FILTER(!(?{v}prec >= 11 && ?{v}cal = wd:{JULIAN} && MONTH(?{v}dob) = 1 &&
           ((YEAR(?{v}dob) <= 1700 && DAY(?{v}dob) = 11) ||
            (YEAR(?{v}dob) >  1700 && YEAR(?{v}dob) <= 1800 && DAY(?{v}dob) = 12) ||
            (YEAR(?{v}dob) >  1800 && DAY(?{v}dob) = 13))))"""
    return s


# The relationship and everything needed to date its end. `?rel` is P26 (marriage) or P451 (unmarried partner);
# romantic relationships were asked for and P451 turns out to be numerically tiny — 112 partnerships against
# 86,600 marriages — but it costs one extra query and it is the honest reading of "not necessarily marriages".
def relationship(rel, dead=("a",)):
    """The relationship and everything needed to date its end.

    `dead` names the partners whose death date is REQUIRED rather than optional, and it is what replaces the old
    1900 birth ceiling. A recorded death proves the marriage ended, so it can be given a duration no matter when
    the couple was born — where a birth-year cap only proves it by proxy. The partners not named here keep an
    OPTIONAL death, because a one-sided row's absent spouse has no death date to require and the row is still
    perfectly labellable from the partner we do have.
    """
    s = f"""
  ?a p:{rel} ?m . ?m ps:{rel} ?b .
  ?m pq:P580 ?start .
  ?a wdt:P31 wd:Q5 . ?b wdt:P31 wd:Q5 .
  OPTIONAL {{ ?m pq:P582 ?end }}
  OPTIONAL {{ ?m pq:P1534 ?cause }}"""
    for v in ("a", "b"):
        s += (f"\n  ?{v} wdt:P570 ?{v}death ." if v in dead
              else f"\n  OPTIONAL {{ ?{v} wdt:P570 ?{v}death }}")
    # PLACE OF BIRTH (third edition, operator 2026-08-18: "use pob and the local time to encode their time of
    # birth as 9:00 AM"). The birthplace's coordinates, through the place item: P19 is the place, P625 its
    # point. OPTIONAL on both partners -- a person without a recorded birthplace still carries a labellable row
    # -- and the test half requires it separately, downstream, where the requirement is visible. Truthy `wdt:`
    # so a person with two birthplace statements at different ranks contributes the preferred one; a person
    # with two at equal rank contributes two rows, and the couple dedupe keeps one.
    for v in ("a", "b"):
        s += f"\n  OPTIONAL {{ ?{v} wdt:P19 ?{v}place . ?{v}place wdt:P625 ?{v}pob }}"
    if rel == "P3342":
        # NO FAMILY RELATIONSHIPS (operator, 2026-08-17). P3342 "significant person" is Wikidata's catch-all and
        # its guidance says to prefer a specific property where one exists -- so a parent or sibling should be
        # under P22/P25/P40/P3373 rather than here -- but that is guidance, not a constraint. Any P3342 pair that
        # ALSO carries a family link in either direction is excluded: parent, child, sibling, relative, godparent,
        # and the deprecated brother/sister properties. This is a FILTER NOT EXISTS, which is expensive, but
        # P3342 is about 1,200 pairs and the cost is nothing; it is NOT applied to P26/P451/P1327, which are
        # chosen partnerships by definition even when the partners happen to be cousins.
        s += """
  FILTER NOT EXISTS {
    VALUES ?fam { wdt:P22 wdt:P25 wdt:P40 wdt:P3373 wdt:P1038 wdt:P1290 wdt:P8810 wdt:P7 wdt:P9 }
    { ?a ?fam ?b } UNION { ?b ?fam ?a }
  }"""
    if not dead:
        # WHAT THE LABEL ACTUALLY NEEDS IS A DATABLE END, and a death is only one way to have one. A marriage
        # with a recorded divorce is dated exactly, whether or not Wikidata knows when either partner died —
        # measured, requiring the death alone discarded 1,371 of 136,992 perfectly labellable pairs, 1.0%.
        #
        # The test queries still name their partners in `dead`, so they emit the same SPARQL as before and their
        # fetched slices stay valid. This branch is the training half, where the extra rows are.
        s += "\n  FILTER(BOUND(?adeath) || BOUND(?bdeath) || BOUND(?end))"
    return s


PROJ = "?a ?b ?adob ?aprec ?bdob ?bprec ?start ?end ?cause ?adeath ?bdeath ?apob ?bpob"

#%% [markdown]
# ## 2. The test set: both partners, to the day, 1851–1900
#
# `FILTER(STR(?a) < STR(?b))` keeps each pair once, since Wikidata states a marriage from both sides. That is
# safe: measured on the full window, 52,095 ordered pairs carry a start date against 26,085 unordered ones — a
# ratio of 1.997 — so both sides carry the qualifiers essentially always and reading one side loses ~0.14%.

#%%
frames = []
for rel in RELS:
    # CASE 1 — both partners born after the cut.
    def body(lo, hi, rel=rel):
        return (relationship(rel, dead=("a", "b")) + "\n  FILTER(STR(?a) < STR(?b))\n"
                + dated('a', lo, hi, 11) + dated('b', CUT + 1, CEIL, 11))
    df = sparql_sliced(f"DISTINCT {PROJ}", body, f"test half ({rel})", CUT + 1, CEIL, order="?a ?b")
    df["rel"] = rel
    frames.append(df)

    # CASE 2 — THE STRADDLE, and it is not a rounding error. The split rule places a couple by its LATER
    # birth, so a man born 1845 married to a woman born 1860 belongs in the held-out half. Requiring BOTH
    # partners to be born after the cut dropped every such couple from the test half AND from the training
    # half, since neither query would take them: measured, 1,416 day-precision couples, 11.1% of what the
    # test half should be.
    #
    # This is a second query rather than a `FILTER(YEAR(?ad) > CUT || YEAR(?bd) > CUT)` on one because that
    # disjunction times out on WDQS (504). The two year ranges here are DISJOINT, which also means `?a` is
    # always the earlier-born partner and `?b` the later one, so each couple matches exactly once and no
    # `STR(?a) < STR(?b)` tiebreak is needed — adding one would in fact drop half of them.
    #
    # SLICE THE EXPENSIVE SIDE. This sliced ?b over one decade and left ?a ranging across the whole
    # 1600-1900 at day precision, which is the larger set by far -- so the bounded variable was the cheap one
    # and the query 502'd or 504'd every time. Measured on the same afternoon: sliced on ?b it fails after 27s;
    # sliced on ?a it answers in 32s with 2,014 rows. Same result set, opposite cost.
    #
    # Slicing on ?a still partitions correctly: the two year ranges are disjoint, so a straddling couple's
    # earlier-born partner is always ?a and falls in exactly one slice.
    def straddle(lo, hi, rel=rel):
        return (relationship(rel, dead=("a", "b")) + "\n"
                + dated('a', lo, hi, 11) + dated('b', CUT + 1, CEIL, 11))
    df = sparql_sliced(f"DISTINCT {PROJ}", straddle, f"test half straddling {CUT} ({rel})",
                       FLOOR, CUT, order="?a ?b")
    df["rel"] = rel
    frames.append(df)
raw_test = pd.concat(frames, ignore_index=True)
print(f"  test half raw: {len(raw_test):,} rows including the couples that straddle {CUT}")

#%% [markdown]
# ## 3. The training set: one partner is enough
#
# Two queries per relationship type, because "at least one of them is dated" is a union and SPARQL prices a
# `UNION` badly here. The first takes couples where BOTH are dated to the year or better; the second constrains
# only `?a` and imposes **nothing at all** on `?b` — no date, no sex, no existence beyond being a human Wikidata
# knows about — which is what produces the `1777-04-30 × 0000-00-00` rows.
#
# The second query deliberately has no `FILTER(STR(?a) < STR(?b))`: it must run from each partner's side
# independently, since the case it exists for is precisely the one where only one side is dated. The two results
# are deduplicated by couple afterwards, keeping the better-populated copy, so a couple found by both queries
# keeps both of its dates.

#%%
frames = []
for rel in RELS:
    def both(lo, hi, rel=rel):
        return (relationship(rel, dead=()) + "\n  FILTER(STR(?a) < STR(?b))\n"
                + dated('a', lo, hi, 9, drop_placeholders=False)
                + dated('b', FLOOR, CUT, 9, drop_placeholders=False))
    df = sparql_sliced(f"DISTINCT {PROJ}", both, f"train both dated ({rel})", FLOOR, CUT, order="?a ?b")
    df["rel"] = rel
    frames.append(df)

    # `?b`'s date is OPTIONAL and PROJECTED, not omitted. Leaving it out entirely meant the build could not
    # tell "this partner has no recorded birth date" from "this partner has one I did not ask for", and wrote
    # `0000-00-00` for both. Two things went wrong at once: a spouse with a perfectly good birth date was
    # published as absent, and a couple whose later birth falls after the cut — so a HELD-OUT couple — was
    # placed in the training half. An OPTIONAL costs far less than the `FILTER NOT EXISTS` that would be the
    # alternative, and it tells the truth: absence is now observed rather than assumed.
    def one(lo, hi, rel=rel):
        return (relationship(rel, dead=()) + "\n"
                + dated('a', lo, hi, 9, drop_placeholders=False)
                + """
  OPTIONAL {
    ?b p:P569 ?bst . ?bst psv:P569 ?bval .
    ?bst wikibase:rank ?brank . FILTER(?brank != wikibase:DeprecatedRank)
    ?bval wikibase:timeValue ?bdob ; wikibase:timePrecision ?bprec .
  }""")
    df = sparql_sliced(f"DISTINCT {PROJ}", one, f"train one dated ({rel})", FLOOR, CUT, order="?a ?b")
    df["rel"] = rel
    frames.append(df)
raw_train = pd.concat(frames, ignore_index=True)

#%% [markdown]
# ## 4. The duration, exactly as an infobox computes it
#
# End = the stated end date if there is one, else the earlier of the two deaths. A relationship with neither is
# unlabellable and is dropped, with the count printed.

#%%
YEAR = 365.2425


def as_days(s):
    """Days since 1600-01-01 at DAY resolution, with a MISSING date as a genuine NaN.

    Two traps here, both of which have already cost this project a wrong dataset.

    `pd.to_datetime(...).astype("int64")` returns MICROseconds, not nanoseconds; dividing by a nanosecond
    constant once turned a 60-year sanity filter into a no-op that removed nothing while printing success. Hence
    the explicit `datetime64[D]`.

    And `NaT.astype("float64")` is **-9.223372036854776e+18, a finite float** — not NaN. So `np.isnan` says
    False, and a marriage with no recorded end date reads as one that ended 25 billion years BC. That silently
    dropped every death-ended marriage as "ended before it started", which is over half the file and most of the
    positive class. The mask has to come from `pd.isna` on the datetimes, before the cast.
    """
    d = pd.to_datetime(pd.Series(list(s), dtype=object).replace("", np.nan), errors="coerce")
    out = (d.to_numpy(dtype="datetime64[D]").astype("float64")
           - np.datetime64("1600-01-01").astype("datetime64[D]").astype("float64"))
    out[np.asarray(pd.isna(d))] = np.nan
    return out


def label(mar, tag):
    """Attach `_dur`, `_source` and `lasted_30_years`; drop what cannot be labelled."""
    mar = mar.copy()
    for c in ("a", "b", "cause"):
        mar[c] = mar.get(c, "").map(qid) if c in mar else ""
    for c in ("adob", "bdob", "start", "end", "adeath", "bdeath"):
        mar[c] = mar[c].str[:10] if c in mar else ""
    for c in ("aprec", "bprec"):
        mar[c] = pd.to_numeric(mar[c], errors="coerce").fillna(0).astype(int) if c in mar else 0
    # THE BIRTHPLACE, from Wikidata's WKT literal `Point(lon lat)` -- longitude FIRST, which is the WKT
    # convention and the reverse of how a person says it. Missing -> NaN on both. Parsed once, here, so every
    # later stage sees numbers.
    for v in ("a", "b"):
        col = mar[f"{v}pob"] if f"{v}pob" in mar else pd.Series([""] * len(mar), index=mar.index)
        m = col.astype(str).str.extract(r"Point\(\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s*\)")
        mar[f"{v}lon"] = pd.to_numeric(m[0], errors="coerce")
        mar[f"{v}lat"] = pd.to_numeric(m[1], errors="coerce")
        bad = mar[f"{v}lat"].abs().gt(90) | mar[f"{v}lon"].abs().gt(180)
        mar.loc[bad, [f"{v}lat", f"{v}lon"]] = np.nan
    start = as_days(mar["start"])
    stated = as_days(mar["end"])
    d_a, d_b = as_days(mar["adeath"]), as_days(mar["bdeath"])
    first_death = np.fmin(np.where(np.isnan(d_a), np.inf, d_a), np.where(np.isnan(d_b), np.inf, d_b))
    first_death = np.where(np.isinf(first_death), np.nan, first_death)
    end = np.where(~np.isnan(stated), stated, first_death)
    mar["_dur"] = (end - start) / YEAR
    mar["_source"] = np.where(~np.isnan(stated), "end date stated", "ran until a death")
    # The guard for the NaT trap described in as_days: a missing date must be NaN, never a finite sentinel. If
    # this ever fires, the "ended before it started" filter below is about to delete a whole class of marriage.
    for nm, arr in (("start", start), ("stated end", stated), ("first death", first_death)):
        finite = arr[~np.isnan(arr)]
        assert finite.size == 0 or finite.min() > -1e6, \
            f"{tag}: {nm} contains a non-NaN sentinel ({finite.min():.3g}) — a missing date is being read as a " \
            f"real one, and every row missing it is about to be dropped as a data error"
    n0 = len(mar)
    mar = mar[~np.isnan(end) & ~np.isnan(start)].reset_index(drop=True)
    print(f"  {tag}: {n0 - len(mar):,} of {n0:,} had neither an end date nor a death — unlabellable, dropped")
    bad = mar["_dur"] < 0
    if bad.any():
        print(f"  {tag}: {int(bad.sum()):,} ended BEFORE they started — dropped as data errors")
        mar = mar[~bad].reset_index(drop=True)
    bad_dur = mar["_dur"] > MAX_DUR_YEARS
    if bad_dur.any():
        print(f"  {tag}: {int(bad_dur.sum()):,} rows with an impossible duration (> {MAX_DUR_YEARS:.0f} years) — data errors, dropped")
        mar = mar[~bad_dur].reset_index(drop=True)
    mar[LABEL] = (mar["_dur"] >= MIN_YEARS).astype(int)
    # THE START YEAR, kept. It is exact at every precision of the underlying date, which is why it and not the
    # full date is the column (see the header). Two sanity rules, both data errors when violated: a start must
    # not precede either KNOWN birth, and it must sit inside the window the whole file lives in.
    mar["start_year"] = pd.to_numeric(mar["start"].str[:4], errors="coerce")
    ya = pd.to_numeric(mar["adob"].str[:4], errors="coerce")
    yb = pd.to_numeric(mar["bdob"].str[:4], errors="coerce")
    before_birth = (mar["start_year"] < ya) | (mar["start_year"] < yb)      # NaN compares False: absent = fine
    n_bb = int(before_birth.sum())
    if n_bb:
        print(f"  {tag}: {n_bb:,} started BEFORE a partner was born — dropped as data errors")
        mar = mar[~before_birth].reset_index(drop=True)
    inwin = mar["start_year"].between(FLOOR, CEIL)
    if (~inwin).any():
        print(f"  {tag}: {int((~inwin).sum()):,} with a start year outside {FLOOR}-{CEIL} — dropped")
        mar = mar[inwin].reset_index(drop=True)
    mar["start_year"] = mar["start_year"].astype(int)
    # THE COLUMN THAT SHIPS is the date itself AT ITS PRECISION (operator 2026-08-19: "ensure that YYYY-01-01 is not
    # same as YYYY-00-00"). Wikidata's time value spells a year-only start as YYYY-01-01 and a month-only one as
    # YYYY-MM-01; the qualifier's timePrecision (9 year · 10 month · 11 day), fetched by kaggle/start_precision.py
    # for every start on the 1st of a month, turns those into YYYY-00-00 and YYYY-MM-00 -- the same spelling the
    # births have always had -- so a real 1 January is a real 1 January. A start the lookup could not answer keeps
    # the literal and is counted aloud.
    sp = _start_prec_table()
    if sp:
        keyed = [sp.get((a, b, st)) or sp.get((b, a, st)) for a, b, st in zip(mar["a"], mar["b"], mar["start"])]
        day1 = mar["start"].str[8:10] == "01"
        n_year = sum(1 for k, d in zip(keyed, day1) if d and k == 9); n_month = sum(1 for k, d in zip(keyed, day1) if d and k == 10)
        n_unk = sum(1 for k, d in zip(keyed, day1) if d and k is None)
        mar["start"] = [s[:4] + "-00-00" if (d and k == 9) else (s[:7] + "-00" if (d and k == 10) else s) for s, k, d in zip(mar["start"], keyed, day1)]
        print(f"  {tag}: starts on the 1st of a month -> {n_year:,} year-only (YYYY-00-00), {n_month:,} month-only (YYYY-MM-00), "
              f"{int(day1.sum()) - n_year - n_month - n_unk:,} real days, {n_unk:,} without a precision answer (kept as written)")
    assert mar["start"].str.match(r"^\d{4}-\d{2}-\d{2}$").all(), f"{tag}: a malformed start date survived"
    return mar


_SP = None


def _start_prec_table():
    """(a, b, start10) -> precision, from the lookup kaggle/start_precision.py writes; empty when absent."""
    global _SP
    if _SP is None:
        path = os.environ.get("AQ_START_PREC", "/tmp/aqdur/_startprec.csv"); _SP = {}
        if os.path.exists(path):
            import csv as _csv
            for r in _csv.reader(open(path)):
                if len(r) == 4 and r[3]:
                    _SP[(r[0], r[1], r[2])] = int(r[3])
            print(f"  start precision: {len(_SP):,} answers read from {path}", flush=True)
        else:
            print(f"  start precision: {path} absent -- starts keep Wikidata's literal spelling", flush=True)
        try:
            _SP.update(_extra_prec)
        except NameError:
            pass
    return _SP


# ── THE WIKI-HARVEST ROWS (operator 2026-08-20: dates recovered from 21 language Wikipedias) ─────────────────────
# kaggle/wiki_start_harvest.py + merge_wiki_starts.py date the P26 marriages Wikidata knows but carries no P580
# for; AQ_WIKI_STARTS points at the trust-merged file and AQ_WIKI_POOL at the candidate pool. Every row flows
# through the SAME label(), filters, dedup and split as the queried rows; its start precision rides the same
# _start_prec_table the P580 spellings use, so a year-only harvested start ships as YYYY-00-00 like every other.
_WIKI_STARTS = os.environ.get("AQ_WIKI_STARTS", "")
if _WIKI_STARTS and os.path.exists(_WIKI_STARTS):
    _wpool = pd.read_csv(os.environ.get("AQ_WIKI_POOL", "/tmp/aqwiki/pool.csv"), dtype=str, keep_default_na=False)
    _wpool = _wpool[_wpool["a"] != "#slice"].drop_duplicates(["a", "b"])
    _wst = pd.read_csv(_WIKI_STARTS, dtype=str, keep_default_na=False)
    _w = _wst.merge(_wpool, on=["a", "b"], how="inner")
    # the label needs day-parseable dates: a year-only harvested start reads YYYY-01-01 here (Wikidata's own
    # spelling convention) and is re-encoded to YYYY-00-00 at write-out through the precision table below
    _w["start_lit"] = _w["start"].str.replace(r"-00-00$", "-01-01", regex=True).str.replace(r"-00$", "-01", regex=True)
    _w["end_lit"] = np.where(_w["end"] != "", _w["end"], np.where(_w.get("end_year", pd.Series([""] * len(_w))).fillna("") != "", _w.get("end_year", pd.Series([""] * len(_w))).fillna("") + "-01-01", ""))
    frame = pd.DataFrame({"a": "http://www.wikidata.org/entity/" + _w["a"], "b": "http://www.wikidata.org/entity/" + _w["b"],
                          "adob": _w["adob"], "aprec": _w["aprec"], "bdob": _w["bdob"], "bprec": _w["bprec"],
                          "start": _w["start_lit"], "end": _w["end_lit"], "cause": "", "adeath": _w["adeath"], "bdeath": _w["bdeath"],
                          "apob": np.where((_w["alat"] != "") & (_w["alon"] != ""), "Point(" + _w["alon"] + " " + _w["alat"] + ")", ""),
                          "bpob": np.where((_w["blat"] != "") & (_w["blon"] != ""), "Point(" + _w["blon"] + " " + _w["blat"] + ")", ""),
                          "rel": "P26wiki"})
    ya = pd.to_numeric(frame["adob"].str[:4], errors="coerce").fillna(0); yb = pd.to_numeric(frame["bdob"].str[:4], errors="coerce").fillna(0)
    later_w = np.maximum(ya, yb)
    is_test = (later_w > CUT) & (pd.to_numeric(_w["aprec"], errors="coerce") >= 11) & (pd.to_numeric(_w["bprec"], errors="coerce") >= 11)
    wiki_test = frame[is_test.to_numpy()]; wiki_train = frame[(later_w <= CUT).to_numpy()]
    n_lost = int(((later_w > CUT) & ~is_test).sum())
    print(f"  wiki harvest: {len(frame):,} dated couples joined the pipeline — {len(wiki_train):,} to the training half, "
          f"{len(wiki_test):,} to the held-out half, {n_lost:,} post-{CUT} couples too coarse for the test's day-precision rule (dropped)")
    raw_test = pd.concat([raw_test, wiki_test], ignore_index=True)
    raw_train = pd.concat([raw_train, wiki_train], ignore_index=True)
    # the harvested precisions ride the same start-precision table as Wikidata's own
    _extra_prec = {(r["a"], r["b"], r["start_lit"][:10]): (11 if not r["start"].endswith("-00") else (10 if not r["start"].endswith("-00-00") else 9)) for _, r in _w.iterrows()}
else:
    _extra_prec = {}

test_l = label(raw_test, "test half")
train_l = label(raw_train, "train half")


def scope_partners(m, tag):
    """A partner's date is either INSIDE the window, or the couple is out of scope. Never silently absent.

    The one-sided query projects `?b`'s date as an OPTIONAL over ALL of Wikidata, not just 1600-1900, which is
    what makes absence observable. The consequence is that `?b` may come back with a real date from 1540 or
    1953. Writing that as `0000-00-00` would publish a spouse who is on Wikidata as though they were not, and
    keeping it would put a birth outside the dataset's declared range and outside the ephemeris span. So the
    couple is dropped and counted: the dataset's contract is that every date it contains is a real date inside
    1600-1900, and a row that cannot honour that is not a row.
    """
    m = m.copy()
    for side in ("a", "b"):
        col = f"{side}dob"
        has = m[col].str.len() >= 4
        yr = pd.to_numeric(m[col].str[:4], errors="coerce")
        out = has & (~yr.between(FLOOR, CEIL))
        if out.any():
            print(f"  {tag}: {int(out.sum()):,} couples dropped — partner {side.upper()} is dated outside "
                  f"{FLOOR}-{CEIL} ({sorted(set(m.loc[out, col].str[:4]))[:5]}...), so the couple is out of "
                  f"scope rather than absent")
            m = m[~out].reset_index(drop=True)
    return m


test_l = scope_partners(test_l, "test half")
train_l = scope_partners(train_l, "train half")

for tag, m in (("test", test_l), ("train", train_l)):
    print(f"\n  {tag}: {len(m):,} labellable · {100*m[LABEL].mean():.1f}% reached {MIN_YEARS} years "
          f"· median duration {m['_dur'].median():.1f}")
    for src, g in m.groupby("_source"):
        print(f"      {src:<18} {len(g):>7,}  {100*g[LABEL].mean():5.1f}% reach {MIN_YEARS}")

print("\n  THE CONFOUND, printed rather than described: those two rates differ enormously, and a model cannot")
print("  see which case a couple is in — it is not a column. It can see things that correlate with it, so the")
print("  published baselines include a case-only reference to read a leaderboard place against.")

named = collections.Counter()
for c in pd.concat([test_l["cause"], train_l["cause"]]):
    if c in BREAKDOWN:
        named[BREAKDOWN[c]] += 1
    elif c in DEATHCAUSE:
        named["a death"] += 1
    elif c:
        named["other cause"] += 1
print(f"\n  {sum(named.values()):,} relationships state WHY they ended (the label never reads this):")
for k, v in named.most_common():
    print(f"      {v:>6,}  {k}")

print("\n  by relationship type (labellable rows, before dedup):")
for tag, m in (("test", test_l), ("train", train_l)):
    for rel, g in m.groupby("rel"):
        print(f"      {tag:<5} {RELS.get(rel, rel):<30} {len(g):>8,}  {100*g[LABEL].mean():5.1f}% "
              f"reach {MIN_YEARS} years")

#%% [markdown]
# ## 5. AGE decides which column, and nothing else may
#
# The older partner is column one, whatever anybody's sex. The ordering key is the birth date itself, compared at
# whatever precision each side has, with ties broken by Q-number so the order is a deterministic function of the
# row — two runs cannot disagree.
#
# The previous version of this dataset ordered by sex, from `P21`. That had two costs. It dropped every couple
# whose two recorded sexes matched, which is the only reason same-sex partnerships were absent; and it dropped
# every couple where a partner had no recorded sex, for a column assignment that carries no information the two
# dates do not already contain. Age is free, always available, and asymmetric in a way a model can use: every
# asymmetric feature now means "older partner versus younger" on every row.
#
# **A one-sided row has no age order**, so the known partner goes first and the absent one second. That is the
# only choice that invents nothing — putting the absent partner first would claim they were older.

#%%
SEX_CSV = os.environ.get("AQ_SEX_CSV", "/tmp/aqdur/_sex.csv")
MALE, FEMALE = "Q6581097", "Q6581072"


def _sex_table():
    """Q-id -> P21 value, from the side lookup sex_lookup.py writes (a query change would have refetched every
    slice; the ids were already in the cache, so P21 was asked for by itself)."""
    if not os.path.exists(SEX_CSV):
        raise SystemExit(f"{SEX_CSV} is missing — run kaggle/sex_lookup.py first (the dad/mom ordering needs P21)")
    t = pd.read_csv(SEX_CSV, header=None, names=["qid", "sex"], dtype=str).fillna("")
    return dict(zip(t.qid, t.sex))


def order_by_sex(m, tag):
    """DAD is column one and MOM column two (third edition, operator 2026-08-18: "switch to gendered model (mom
    and dad) instead of old first").

    The order is read from Wikidata's P21 for each partner: Q6581097 male -> dad, Q6581072 female -> mom. A pair
    that is not exactly one of each -- both male, both female, either sex unrecorded, or a value other than those
    two -- has no dad/mom order and is EXCLUDED FROM THIS EDITION, counted aloud below. That is a consequence of
    the ordering rule the operator chose for this edition, not a claim about anyone; the two-dates editions,
    which order by age and read no sex, keep every couple.

    A one-sided row (partner b without a date) is still orderable when b's sex is on file, because b is a
    Wikidata item; it keeps its side. Ties cannot occur: the rule never compares the two partners.
    """
    m = m.copy()
    n0 = len(m)
    sex = _sex_table()
    sa = m["a"].map(lambda q: sex.get(q, "")); sb = m["b"].map(lambda q: sex.get(q, ""))
    a_dad = (sa == MALE) & (sb == FEMALE)
    b_dad = (sa == FEMALE) & (sb == MALE)
    keep = a_dad | b_dad
    both_m = ((sa == MALE) & (sb == MALE)).sum(); both_f = ((sa == FEMALE) & (sb == FEMALE)).sum()
    unk = (~keep).sum() - both_m - both_f
    print(f"  {tag}: {int(keep.sum()):,} of {n0:,} rows are one man + one woman and take the dad/mom order; "
          f"excluded from this edition: {int(both_m):,} male-male, {int(both_f):,} female-female, {int(unk):,} with a sex "
          f"unrecorded or outside those two values")
    m = m[keep].reset_index(drop=True); a_first = a_dad[keep].to_numpy()
    m["dob_dad"] = np.where(a_first, m["adob"], m["bdob"]); m["dob_mom"] = np.where(a_first, m["bdob"], m["adob"])
    m["prec_dad"] = np.where(a_first, m["aprec"], m["bprec"]); m["prec_mom"] = np.where(a_first, m["bprec"], m["aprec"])
    for q in ("lat", "lon"):
        m[f"{q}_dad"] = np.where(a_first, m[f"a{q}"], m[f"b{q}"]); m[f"{q}_mom"] = np.where(a_first, m[f"b{q}"], m[f"a{q}"])
    m["dad"] = np.where(a_first, m["a"], m["b"]); m["mom"] = np.where(a_first, m["b"], m["a"])
    return m



def order_genderless(m, tag):
    """FOURTH EDITION (operator 2026-08-19: "I want a genderless model from now on"): no sex is read and no order
    is claimed. Slot one / slot two are `a` / `b` -- the query's own order, which is the Q-id string order and
    carries nothing -- except on a one-sided row, where the KNOWN partner takes slot one (the only order that
    invents nothing). Every pair is kept: male-female, male-male, female-female, sex unrecorded. The files then
    carry every pair in BOTH orders (see section 8), so (a, b, y) and (b, a, y) are both rows and a model is
    symmetric by the data rather than by a column convention. The internal column names stay dad/mom until the
    write-out only so the checks below need no second copy; they are renamed to _a/_b in the files.
    """
    m = m.copy()
    a_known = m["adob"].fillna("").astype(str).str[:4].str.isdigit().to_numpy()
    b_known = m["bdob"].fillna("").astype(str).str[:4].str.isdigit().to_numpy()
    a_first = ~(~a_known & b_known)
    print(f"  {tag}: {len(m):,} rows, all kept (no sex read); {int((~a_first).sum()):,} one-sided rows put the "
          f"known partner first")
    m["dob_dad"] = np.where(a_first, m["adob"], m["bdob"]); m["dob_mom"] = np.where(a_first, m["bdob"], m["adob"])
    m["prec_dad"] = np.where(a_first, m["aprec"], m["bprec"]); m["prec_mom"] = np.where(a_first, m["bprec"], m["aprec"])
    for q in ("lat", "lon"):
        m[f"{q}_dad"] = np.where(a_first, m[f"a{q}"], m[f"b{q}"]); m[f"{q}_mom"] = np.where(a_first, m[f"b{q}"], m[f"a{q}"])
    m["dad"] = np.where(a_first, m["a"], m["b"]); m["mom"] = np.where(a_first, m["b"], m["a"])
    return m


GENDERLESS = os.environ.get("AQ_ORDER", "") == "none"
# AQ_ORDER=sex (operator 2026-08-21): GENDERED male x female only — order_by_sex drops same-sex and unknown-sex
# pairs (counted aloud) and puts the MAN first; the files keep the a/b column names with a = the man, one row per
# couple (no both-orders duplication).
GENDERED_AB = os.environ.get("AQ_ORDER", "") == "sex"
_order = order_genderless if GENDERLESS else order_by_sex
test_c = _order(test_l, "test half")
train_c = _order(train_l, "train half")

#%% [markdown]
# ## 6. `00` for unknown, `0000-00-00` for absent
#
# Wikidata stores a year-precision date as `1850-01-01` and a month-precision one as `1850-03-01`, so the day and
# month have to be **erased** rather than trusted — that `01` is not a claim about January or the first. The
# precision comes from `wikibase:timePrecision`, projected by the queries, rather than being guessed back out of
# the literal.

#%%
def encode(dob, prec):
    """`YYYY-MM-DD`, `YYYY-MM-00`, `YYYY-00-00`, or `0000-00-00` when there is no date at all."""
    out = []
    for d, p in zip(dob, prec):
        d = d or ""
        if len(d) < 4 or not d[:4].isdigit():
            out.append(ABSENT)
        elif p >= 11:
            out.append(d[:10])
        elif p == 10:
            out.append(d[:7] + "-00")
        else:
            out.append(d[:4] + "-00-00")
    return np.array(out, dtype=object)


for frame in (test_c, train_c):
    for side in ("dad", "mom"):
        frame[f"dob_{side}"] = encode(frame[f"dob_{side}"].fillna("").to_numpy(),
                                      frame[f"prec_{side}"].to_numpy())

#%% [markdown]
# ## 7. One row per couple, then the split, with both asserted
#
# A couple with two recorded marriages keeps the LONGEST: the question is whether these two people sustained a
# marriage, and averaging or taking the first answers neither. A one-sided row is dropped when the same couple
# was also found fully dated, since it is the same marriage with less information — which is why the sort puts
# the better-populated copy first.

#%%
def precision_class(col):
    """3 = day, 2 = month, 1 = year, 0 = absent — read back off the encoded string.

    Written out because the obvious one-liner is wrong in two ways at once. `(d.str[5:] != "00-00")` counts a
    MONTH-precision date as a day-precision one, since "1809-11-00"[5:] is "11-00"; and subtracting the absent
    count afterwards double-subtracts, because "0000-00-00"[5:] is already "00-00" and never counted. Together
    those reported 130 day-precision women where there are about 17,000, which looked like a catastrophic data
    fault rather than a bad print.
    """
    day = ~col.str.endswith("-00")
    absent = col.eq(ABSENT)
    year = col.str[5:].eq("00-00") & ~absent
    month = col.str.endswith("-00") & ~year & ~absent
    return (day * 3 + month * 2 + year * 1).astype(int)


def one_per_couple(m, tag):
    m = m.copy()
    m["_pair"] = [f"{min(x, y)}|{max(x, y)}" for x, y in zip(m["dad"], m["mom"])]
    # PREFER THE MORE PRECISE COPY, not merely a non-absent one. 3.5% of people carry two non-deprecated P569
    # statements at different precisions — Q104093886 has both 1830-01-01 (year) and 1830-07-20 (day) — so the
    # query returns two rows for the couple. Ranking only on "is it absent" left those tied, and the tie was
    # broken by whichever row the endpoint happened to return first, throwing away a known birthday for about
    # one couple in thirty for no reason at all.
    m["_prec"] = precision_class(m["dob_dad"]) + precision_class(m["dob_mom"])
    m["_known"] = (m["dob_dad"] != ABSENT).astype(int) + (m["dob_mom"] != ABSENT).astype(int)
    m["_places"] = m["lat_dad"].notna().astype(int) + m["lat_mom"].notna().astype(int)
    n0 = len(m)
    m = (m.sort_values(["_known", "_prec", "_places", "_dur"], ascending=[False, False, False, False])
          .drop_duplicates("_pair", keep="first").reset_index(drop=True))
    print(f"  {tag}: {n0 - len(m):,} duplicate rows collapsed (most dates first, then the most precise, then "
          f"the longest marriage) — {len(m):,} couples")
    return m


test_u = one_per_couple(test_c, "test half")
train_u = one_per_couple(train_c, "train half")

# The birth-gap sanity filter only applies where BOTH dates exist.
kept = []
for tag, m in (("test", test_u), ("train", train_u)):
    both = (m["dob_dad"] != ABSENT) & (m["dob_mom"] != ABSENT)
    gap = np.abs(pd.to_numeric(m["dob_dad"].str[:4], errors="coerce")
                 - pd.to_numeric(m["dob_mom"].str[:4], errors="coerce"))
    drop = both & (gap >= MAX_GAP_YEARS)
    if drop.any():
        print(f"  {tag}: {int(drop.sum()):,} couples born {MAX_GAP_YEARS}+ years apart — dropped")
    kept.append(m[~drop].reset_index(drop=True))
test_u, train_u = kept


def later_year(m):
    """The later of the two known birth years. With one partner absent this is the only known one, which is the
    right reading: the split asks when this couple lived, and an absent partner says nothing about that."""
    y = np.maximum(pd.to_numeric(m["dob_dad"].str[:4], errors="coerce").fillna(0),
                   pd.to_numeric(m["dob_mom"].str[:4], errors="coerce").fillna(0))
    return y.astype(int)


test_u["_later"], train_u["_later"] = later_year(test_u), later_year(train_u)
test = test_u[test_u["_later"] > CUT].reset_index(drop=True)
# THE PLACE, required in the held-out half. The whole point of this edition is a chart cast at 09:00 LOCAL, and
# there is no local time without a place. Counted aloud, because it is the largest single filter on the test half.
no_place = test["lat_dad"].isna() | test["lat_mom"].isna()
print(f"  {int(no_place.sum()):,} of {len(test):,} held-out couples lack a birthplace for a partner — removed "
      f"(the training half keeps such rows, with the place empty)")
test = test[~no_place].reset_index(drop=True)
# THE CEILING, applied to the held-out half only. Every held-out couple is dead by CEIL, so a relationship that
# began after CEIL - MIN_YEARS cannot have lasted MIN_YEARS: its label is 0 by arithmetic, not by anything a
# model could learn. Left in, such rows are free points for whoever notices and noise for whoever does not, and
# either way they measure the calendar rather than the couple. They are removed here and counted aloud. The
# training half is unaffected: every training couple was born by CUT, so no start there is anywhere near CEIL.
too_late = test["start_year"] > CEIL - MIN_YEARS
if too_late.any():
    print(f"  {int(too_late.sum()):,} held-out couples began after {CEIL - MIN_YEARS} — {MIN_YEARS} years before "
          f"{CEIL} is impossible, so their label is 0 by arithmetic; removed from the test half")
    test = test[~too_late].reset_index(drop=True)
# A couple the one-sided query found whose LATER birth falls after the cut belongs to the held-out era, so it is
# excluded from training here — and it cannot enter the test half either unless BOTH its dates are
# day-precision, which the test queries require. That is the correct outcome and not an oversight: a coarse
# straddling couple is unusable on both sides. Counted rather than dropped in silence.
straddling = int((train_u["_later"] > CUT).sum())
if straddling:
    print(f"  {straddling:,} couples found by the one-sided query have their later birth after {CUT} — held-out "
          f"era, so excluded from training; they join the test half only if both dates are day-precision")
train = train_u[(train_u["_later"] <= CUT) & (train_u["_later"] >= FLOOR)].reset_index(drop=True)

# PERSON-DISJOINT, restored from the TRAINING side. A training couple sharing a person with a held-out couple is
# dropped: that costs training rows rather than compromising the test set, and the test set is the measurement.
test_people = set(test["dad"]) | set(test["mom"])
test_people.discard("")
shares = train["dad"].isin(test_people) | train["mom"].isin(test_people)
print(f"\n  {int(shares.sum()):,} training couples dropped for sharing a person with the held-out half")
train = train[~shares].reset_index(drop=True)

assert test["_later"].min() > CUT >= train["_later"].max(), "the split is not temporal"
tp = (set(train["dad"]) | set(train["mom"])) - {""}
sp = (set(test["dad"]) | set(test["mom"])) - {""}
assert not (tp & sp), f"{len(tp & sp)} people on both sides"
print(f"  train {len(train):,} couples (later known birth {train['_later'].min()}-{train['_later'].max()}) · "
      f"test {len(test):,} ({test['_later'].min()}-{test['_later'].max()})")
print(f"  checked: the split is temporal at {CUT}, and no person appears on both sides")
print(f"  positive rate: train {100*train[LABEL].mean():.2f}% · "
      f"test {100*test[LABEL].mean():.2f}%")
print("  those differ, and they should: earlier-born couples died younger and their records are thinner, so")
print("  fewer of their marriages reach thirty years.")

#%% [markdown]
# ### The rate by birth decade, and the ceiling that death imposes
#
# This table is the most important diagnostic in the build, because the design that removed one bias introduced
# another. Requiring a recorded death is what lets the window run to the present — but a couple born recently who
# are *already dead* died young, and a marriage cannot outlive the shorter-lived partner. Past roughly 1996 a
# thirty-year marriage is arithmetically impossible for anyone dead by now, so the positive rate must fall to
# zero at the recent end whatever astrology says.
#
# A model can score on that alone: "born late → negative" is an era rule, not a finding. So the rate is printed
# per decade and the last decade where a positive is even *possible* is named. If the held-out half is dominated
# by decades that cannot produce a positive, the leaderboard measures the calendar again — and the fix is to cap
# the test window, not to hope.

#%%
print("\n  positive rate by the couple's LATER birth decade:")
for name, frame in (("train", train), ("test", test)):
    y = frame["_later"] // 10 * 10
    tab = frame.groupby(y)[LABEL].agg(["mean", "size"])
    tab = tab[tab["size"] >= 25]
    if tab.empty:
        continue
    print(f"    {name}:")
    for dec, row in tab.iterrows():
        # The soonest a couple born in `dec` could reach 30 married years, if they married at 20.
        earliest_possible = int(dec) + 20 + MIN_YEARS
        flag = "  <- 30 years IMPOSSIBLE for anyone dead by now" if earliest_possible > CEIL else ""
        print(f"      {int(dec)}s  {100*row['mean']:5.1f}%  ({int(row['size']):>6,} couples){flag}")
    impossible = tab.index[(tab.index + 20 + MIN_YEARS) > CEIL]
    if len(impossible):
        n_imp = int(tab.loc[impossible, "size"].sum())
        print(f"      {n_imp:,} of {int(tab['size'].sum()):,} {name} couples are in a decade where the "
              f"positive class is unreachable ({100*n_imp/int(tab['size'].sum()):.1f}%)")

print("\n  positive rate by the START decade (the wedding decade for a marriage):")
for name, frame in (("train", train), ("test", test)):
    tab = frame.groupby(frame["start_year"] // 10 * 10)[LABEL].agg(["mean", "size"])
    tab = tab[tab["size"] >= 25]
    print(f"    {name}:")
    for dec, row in tab.iterrows():
        print(f"      {int(dec)}s  {100*row['mean']:5.1f}%  ({int(row['size']):>6,} couples)")
print("\n  positive rate by the DAD's age at the start (where his birth is known):")
for name, frame in (("train", train), ("test", test)):
    yo = pd.to_numeric(frame["dob_dad"].str[:4], errors="coerce")
    age = (frame["start_year"] - yo)
    ok = yo.notna()
    tab = frame[ok].groupby(pd.cut(age[ok], [0, 20, 25, 30, 35, 40, 50, 60, 200], right=False),
                            observed=True)[LABEL].agg(["mean", "size"])
    tab = tab[tab["size"] >= 25]
    print(f"    {name}:")
    if tab.empty:
        print(f"      (no band with >= 25 couples: {len(frame):,} rows, {int(ok.sum()):,} with a known dad birth, "
              f"start_year dtype {frame['start_year'].dtype}, age min {age[ok].min()} max {age[ok].max()})")
    for band, row in tab.iterrows():
        print(f"      {str(band):<10} {100*row['mean']:5.1f}%  ({int(row['size']):>6,} couples)")

n_both = int(((train["dob_dad"] != ABSENT) & (train["dob_mom"] != ABSENT)).sum())
print(f"\n  the training half, by how much it knows:")
print(f"      {n_both:>7,} couples with BOTH dates ({100*n_both/max(len(train),1):.1f}%)")
print(f"      {len(train)-n_both:>7,} with one partner absent — kept, because the DURATION is known exactly")
for side in ("dad", "mom"):
    pc = precision_class(train[f"dob_{side}"])
    print(f"      {side:<5}: {int((pc == 3).sum()):>7,} to the day · {int((pc == 2).sum()):>6,} to the month · "
          f"{int((pc == 1).sum()):>6,} to the year · {int((pc == 0).sum()):>6,} absent")
    assert int(pc.notna().sum()) == len(train), "every row must fall in exactly one precision class"

#%% [markdown]
# ## 8. The files
#
# The test set is asserted strictly — every date day-precision, in window, never a placeholder. Those assertions
# are the reason the two halves were built by separate queries rather than filtered out of one.

#%%
COLS = ["dob_dad", "dob_mom", "lat_dad", "lon_dad", "lat_mom", "lon_mom", "start",
        LABEL]
for col in ("dob_dad", "dob_mom"):
    assert test[col].str.match(r"^\d{4}-\d{2}-\d{2}$").all(), f"test.{col} malformed"
    assert not test[col].eq(ABSENT).any(), f"test.{col} has an absent date — the test half must be complete"
    assert not test[col].str.endswith("-00").any(), f"test.{col} is not day-precision"
    # 1 January in a test birth is REAL when its precision flag said day (the wiki-harvest rows carry Wikidata's
    # own timePrecision; the original query-side rows still exclude placeholders upstream) — counted, not asserted
    n_jan1 = int((test[col].str[5:] == "01-01").sum())
    if n_jan1:
        print(f"  test.{col}: {n_jan1:,} genuine 1 January birthdays (day-precision on Wikidata's own flag)")
    # EACH PARTNER IS IN THE WINDOW; THE COUPLE IS PLACED BY ITS LATER BIRTH. This asserted `y > CUT` on BOTH
    # columns, which contradicted the straddle fix in the very same file: a couple whose man was born 1845 and
    # whose wife was born 1860 is a held-out couple by the split rule, and its man's year is 1845. The query was
    # corrected to include those couples and this assertion was the copy that did not move — the same failure
    # mode as the split assertion that went on checking a floor the new data already cleared.
    y = test[col].str[:4].astype(int)
    assert ((y >= FLOOR) & (y <= CEIL)).all(), f"test.{col} outside {FLOOR}-{CEIL}"
assert (np.maximum(test["dob_dad"].str[:4].astype(int),
                   test["dob_mom"].str[:4].astype(int)) > CUT).all(), \
    f"a held-out couple has BOTH births at or before {CUT} — it belongs in the training half"
print(f"  checked: every test date is day-precision inside {FLOOR}-{CEIL}, never a placeholder, and every "
      f"held-out couple's LATER birth is after {CUT}")
for name, frame in (("test", test), ("train", train)):
    assert frame["start"].str.match(r"^\d{4}-\d{2}-\d{2}$").all(), f"{name}.start malformed"
    assert (frame["start"].str[:4].astype(int) == frame["start_year"]).all(), f"{name}: start and start_year disagree"
    sy = frame["start_year"]
    assert sy.between(FLOOR, CEIL).all(), f"{name}.start outside {FLOOR}-{CEIL}"
    for col in ("dob_dad", "dob_mom"):
        yr = pd.to_numeric(frame[col].str[:4], errors="coerce")
        known = frame[col] != ABSENT
        assert (sy[known] >= yr[known]).all(), f"{name}: a relationship starts before the {col} birth"
assert (test["start_year"] <= CEIL - MIN_YEARS).all(), \
    f"a held-out couple began after {CEIL - MIN_YEARS}: its label is 0 by arithmetic and it must not be scored"
for side in ("dad", "mom"):
    assert test[f"lat_{side}"].notna().all() and test[f"lon_{side}"].notna().all(), f"test.{side} lacks a place"
    assert test[f"lat_{side}"].between(-90, 90).all() and test[f"lon_{side}"].between(-180, 180).all()
    ok = train[f"lat_{side}"].isna() | (train[f"lat_{side}"].between(-90, 90) & train[f"lon_{side}"].between(-180, 180))
    assert ok.all(), f"train.{side}: a coordinate out of range"
    # A partner whose DATE is absent is still a Wikidata item and may well have a recorded birthPLACE -- the
    # one-sided rows are "no date on file", not "no person". The first run asserted the opposite and failed on
    # 1,000-odd honest rows. Kept as data: a place without a date casts no chart, but it is a real fact about
    # the partner and a model may read it (latitude, longitude) as it likes.
    absent = train[f"dob_{side}"] == ABSENT
    n_place_no_date = int(train.loc[absent, f"lat_{side}"].notna().sum())
    if n_place_no_date:
        print(f"  {n_place_no_date:,} training rows know the {side} partner's birthplace but not their birth date — kept")
np_ = {n: int((f["lat_dad"].notna() & f["lat_mom"].notna()).sum()) for n, f in (("train", train), ("test", test))}
print(f"  checked: every held-out partner has a birthplace inside the world; training rows may leave it empty — "
      f"both places known in {np_['train']:,} of {len(train):,} training rows and all {np_['test']:,} test rows")
jan1 = {n: int((f["start"].str[5:] == "00-00").sum()) for n, f in (("train", train), ("test", test))}
print(f"  checked: every start is a YYYY-MM-DD date inside {FLOOR}-{CEIL}, never before a known birth, and no "
      f"held-out relationship began too late for {MIN_YEARS} years before {CEIL}")
print(f"  starts known to the YEAR only (YYYY-00-00): train {jan1['train']:,} of "
      f"{len(train):,} ({100*jan1['train']/len(train):.1f}%) · test {jan1['test']:,} of {len(test):,} "
      f"({100*jan1['test']/len(test):.1f}%)")
for col in ("dob_dad", "dob_mom"):
    assert train[col].str.match(r"^\d{4}-\d{2}-\d{2}$").all(), f"train.{col} malformed"
assert not ((train["dob_dad"] == ABSENT) & (train["dob_mom"] == ABSENT)).any(), \
    "a training row with no date at all carries no input"
print("  checked: every training row is well-formed and carries at least one date")

train = train.sample(frac=1.0, random_state=20260817).reset_index(drop=True)
test = test.sample(frac=1.0, random_state=20260818).reset_index(drop=True)
# AQ_DUMP_DUR: the raw duration in years beside each written row (an INTERNAL side file, never published) — for
# threshold sweeps ("which survival cut is most predictable"). Aligned to the PRE-both-orders frames; the pair
# key joins it to either order.
if os.environ.get("AQ_DUMP_DUR"):
    for _nm, _fr in (("train", train), ("test", test)):
        pd.DataFrame({"dob_dad": _fr["dob_dad"], "dob_mom": _fr["dob_mom"], "start": _fr["start"], "dur_years": _fr["_dur"].round(3)}).to_csv(
            os.environ["AQ_DUMP_DUR"].replace(".csv", f"_{_nm}.csv"), index=False)
    print(f"  durations dumped beside the rows -> {os.environ['AQ_DUMP_DUR']}")
if GENDERLESS:
    # FOURTH EDITION: every pair in BOTH orders. (a, b, y) and (b, a, y) are both rows of train; every test pair
    # is two rows, `p<n>a` and `p<n>b`, scored together and on the same Public/Private side, so a submission
    # that is not symmetric in its two partners is penalised by the metric itself rather than by a rule.
    REN = {"dob_dad": "dob_a", "dob_mom": "dob_b", "lat_dad": "lat_a", "lon_dad": "lon_a", "lat_mom": "lat_b", "lon_mom": "lon_b"}
    SWAP = {"dob_a": "dob_b", "dob_b": "dob_a", "lat_a": "lat_b", "lat_b": "lat_a", "lon_a": "lon_b", "lon_b": "lon_a"}

    def both_orders(frame):
        f1 = frame.rename(columns=REN); f2 = f1.rename(columns=SWAP)[f1.columns]
        f1 = f1.copy(); f2 = f2.copy(); f1["_ord"] = "a"; f2["_ord"] = "b"; f1["_pairno"] = np.arange(len(f1)); f2["_pairno"] = np.arange(len(f2))
        return pd.concat([f1, f2], ignore_index=True)
    COLS = [REN.get(c, c) for c in COLS]
    train = both_orders(train).sample(frac=1.0, random_state=20260819).reset_index(drop=True)
    test = both_orders(test)
    test["id"] = [f"p{n:06d}{o}" for n, o in zip(test["_pairno"], test["_ord"])]
    test = test.sample(frac=1.0, random_state=20260819).reset_index(drop=True)
    rng = np.random.default_rng(20260817)
    side_of_pair = np.where(rng.random(test["_pairno"].max() + 1) < 0.30, "Public", "Private")
    print(f"  GENDERLESS: every pair written in both orders -- train {len(train):,} rows ({len(train)//2:,} pairs), "
          f"test {len(test):,} rows ({len(test)//2:,} pairs); the two rows of a pair share a Public/Private side")
    train[COLS].to_csv(os.path.join(OUT, "train.csv"), index=False, float_format="%.4f")
    test[["id", "dob_a", "dob_b", "lat_a", "lon_a", "lat_b", "lon_b", "start"]]\
        .to_csv(os.path.join(OUT, "test.csv"), index=False, float_format="%.4f")
    sol = test[["id", LABEL]].copy()
    sol["Usage"] = side_of_pair[test["_pairno"].to_numpy()]
elif GENDERED_AB:
    REN = {"dob_dad": "dob_a", "dob_mom": "dob_b", "lat_dad": "lat_a", "lon_dad": "lon_a", "lat_mom": "lat_b", "lon_mom": "lon_b"}
    train = train.rename(columns=REN); test = test.rename(columns=REN); COLS = [REN.get(c, c) for c in COLS]
    print(f"  GENDERED: one row per couple, column a IS the man (P21), column b the woman — "
          f"{len(train):,} train rows, {len(test):,} test rows")
    train[COLS].to_csv(os.path.join(OUT, "train.csv"), index=False, float_format="%.4f")
    test["id"] = [f"m{i:06d}" for i in range(len(test))]
    test[["id", "dob_a", "dob_b", "lat_a", "lon_a", "lat_b", "lon_b", "start"]]\
        .to_csv(os.path.join(OUT, "test.csv"), index=False, float_format="%.4f")
    rng = np.random.default_rng(20260817)
    sol = test[["id", LABEL]].copy()
    sol["Usage"] = np.where(rng.random(len(test)) < 0.30, "Public", "Private")
    sol.to_csv(os.path.join(OUT, "solution.csv"), index=False)
    samp = test[["id"]].copy(); samp[LABEL] = 0.5
    samp.to_csv(os.path.join(OUT, "sample_submission.csv"), index=False)
else:
    train[COLS].to_csv(os.path.join(OUT, "train.csv"), index=False, float_format="%.4f")
    test["id"] = [f"m{i:06d}" for i in range(len(test))]
    test[["id", "dob_dad", "dob_mom", "lat_dad", "lon_dad", "lat_mom", "lon_mom", "start"]]\
        .to_csv(os.path.join(OUT, "test.csv"), index=False, float_format="%.4f")
    rng = np.random.default_rng(20260817)
    sol = test[["id", LABEL]].copy()
    sol["Usage"] = np.where(rng.random(len(test)) < 0.30, "Public", "Private")
sol.to_csv(os.path.join(OUT, "solution.csv"), index=False)
samp = test[["id"]].copy()
samp[LABEL] = 0.5
samp.to_csv(os.path.join(OUT, "sample_submission.csv"), index=False)
for side in ("Public", "Private"):
    s = sol[sol["Usage"] == side]
    assert 0 < s[LABEL].sum() < len(s), f"the {side} half has one class only"
    print(f"    {side:<8} {len(s):>6,} rows, {100*s[LABEL].mean():5.2f}% positive")

print(f"\n  wrote train.csv ({len(train):,}) · test.csv ({len(test):,}) · solution.csv · sample_submission.csv")
print("\n  training rows, showing the three shapes it can take:")
_c1, _c2 = ("dob_a", "dob_b") if (GENDERLESS or GENDERED_AB) else ("dob_dad", "dob_mom")
ex = pd.concat([train[(train[_c2] != ABSENT) & (train[_c1].str[5:] != "00-00")].head(2),
                train[train[_c1].str[5:] == "00-00"].head(2),
                train[train[_c2] == ABSENT].head(2)])
print(ex[COLS].to_string(index=False))
print(f"\n  total build time {(time.time()-T0)/60:.1f} min")
