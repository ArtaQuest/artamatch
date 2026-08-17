#%% [markdown]
# # Two birth dates, one question: did the marriage last thirty years?
#
# This notebook builds the **ArtaMatch Duration** dataset from scratch, from live SPARQL against Wikidata. Every
# query is in the cells below, so anyone can re-run them and get a different answer as Wikidata changes.
#
# Three columns. That is the whole file.
#
# | column | meaning |
# |---|---|
# | `dob_man` | the man's date of birth |
# | `dob_woman` | the woman's date of birth |
# | `lasted_30_years` | 1 if the marriage lasted thirty years or longer, else 0 |
#
# The first column is the man and the second the woman — always, assigned from `P21` and never inherited from
# whatever order Wikidata happened to state the couple in. The marriage's own dates are used to compute the third
# column and are then **thrown away**; they are not inputs.
#
# ## The two halves are built by different rules, deliberately
#
# **The test set is strict.** Both partners known to the day, no placeholder dates, and the couple's **later**
# birth after 1850. That is what the leaderboard is scored on, so it is the half that must not be noisy.
#
# Note "later birth", not "both births". A man born 1845 married to a woman born 1860 is a held-out couple: the
# split places a couple by when the second of them was born. Requiring both partners after the cut dropped 1,416
# day-precision couples — 11.1% of the test half — out of the dataset entirely, since the training queries would
# not take them either.
#
# **The training set is as inclusive as the data allows.** A date may be known only to the month or only to the
# year, and **one partner may be missing from Wikidata entirely**. All three of these are real training rows:
#
# ```
# dob_man,dob_woman,lasted_30_years
# 1794-06-12,1801-03-27,1     <- both known to the day
# 1802-00-00,1809-11-00,0     <- his year only; her year and month
# 1777-04-30,0000-00-00,1     <- she is not in Wikidata at all, and the row is still worth learning from
# ```
#
# `00` means unknown and `0000-00-00` means absent, so precision is visible in the value rather than hidden in a
# separate column. A model that wants only clean rows filters them in one line; a model that wants every marriage
# has them. This is not a rounding decision — it is the difference between **12,661 training couples and 86,600**:
#
# | training rule | couples |
# |---|---|
# | both partners known to the day | 12,661 |
# | both partners, any precision | 30,110 |
# | **at least one partner, any precision** | **86,600** |
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
# ## Why 1600–1900, and why the split is at 1850
#
# Everybody born on or before 1900 is dead, which matters more here than for any other question in this project:
# a marriage still running cannot be labelled, and one that has not yet had thirty years cannot reach thirty.
# Closing the window at 1900 removes right-censoring — every marriage in this file has ended, and every positive
# was observable.
#
# The split is **temporal**: train on couples born up to 1850, predict the ones born after. Not "rank couples
# drawn from the years you learned from" but "learn from the earlier ones and predict the later ones".
#
# The base rate shifts across that boundary; it is printed below rather than asserted. Earlier-born couples died
# younger and their records are thinner, so fewer of their marriages reach thirty years.
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
# 1600–1900 it occurs **2.07×** as often as a median January day, while 2 January sits at 1.00× — a source that
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
MIN_YEARS = 30                    # the label's threshold
MAX_GAP_YEARS = 60
MALE, FEMALE = "Q6581097", "Q6581072"
JULIAN = "Q1985786"
SLICE = int(os.environ.get("AQ_YEAR_SLICE", "25"))
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
                with urllib.request.urlopen(req, timeout=900) as r:
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


def sparql_count(select, body):
    """How many rows the query should return, counted through the SAME projection it is read with."""
    q = f"{PREFIXES}\nSELECT (COUNT(*) AS ?n) WHERE {{ {{ SELECT {select} WHERE {{ {body} }} }} }}"
    d = json.loads(_fetch(q, "application/qlever-results+json"))
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
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out.columns = [c.strip().lstrip("?") for c in out.columns]
    for c in out.columns:
        out[c] = out[c].str.strip().str.strip('"')
    if len(out) < want:
        raise RuntimeError(f"{name}: got {len(out):,} rows, endpoint counted {want:,} — truncated, and a "
                           f"truncated marriage list silently mislabels couples")
    print(f"  {name}: {len(out):,} rows in {time.time()-t:.0f}s (count-verified)", flush=True)
    return out


SLICE_CACHE = os.path.join(OUT, "_dslices")


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
    stage = "whole-window count"
    try:
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
        print(f"  {name}: {stage} failed ({type(e).__name__}: {str(e)[:80]}) — falling back to "
              f"{SLICE}-year slices", flush=True)
    for lo in range(lo0, hi0 + 1, SLICE):
        hi = min(lo + SLICE - 1, hi0)
        cache = os.path.join(SLICE_CACHE, f"{tag}_{lo}_{hi}.csv")
        if os.path.exists(cache):
            frames.append(pd.read_csv(cache, dtype=str, keep_default_na=False))
            print(f"  {name} {lo}-{hi}: {len(frames[-1]):,} rows (cached)", flush=True)
            continue
        df = sparql(select, body_fn(lo, hi), f"{name} {lo}-{hi}", order=order)
        df.to_csv(cache + ".tmp", index=False)
        os.replace(cache + ".tmp", cache)
        frames.append(df)
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
    return s


PROJ = "?a ?b ?adob ?aprec ?bdob ?bprec ?asex ?bsex ?start ?end ?cause ?adeath ?bdeath"
SEX = "?a wdt:P21 ?asex . ?b wdt:P21 ?bsex ."

#%% [markdown]
# ## 2. The test set: both partners, to the day, 1851–1900
#
# `FILTER(STR(?a) < STR(?b))` keeps each pair once, since Wikidata states a marriage from both sides. That is
# safe: measured on the full window, 52,095 ordered pairs carry a start date against 26,085 unordered ones — a
# ratio of 1.997 — so both sides carry the qualifiers essentially always and reading one side loses ~0.14%.

#%%
frames = []
for rel in ("P26", "P451"):
    # CASE 1 — both partners born after the cut.
    def body(lo, hi, rel=rel):
        return (relationship(rel, dead=("a", "b")) + "\n  FILTER(STR(?a) < STR(?b))\n  " + SEX
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
    def straddle(lo, hi, rel=rel):
        return (relationship(rel, dead=("a", "b")) + "\n  " + SEX
                + dated('a', FLOOR, CUT, 11) + dated('b', lo, hi, 11))
    df = sparql_sliced(f"DISTINCT {PROJ}", straddle, f"test half straddling {CUT} ({rel})",
                       CUT + 1, CEIL, order="?a ?b")
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
for rel in ("P26", "P451"):
    def both(lo, hi, rel=rel):
        return (relationship(rel, dead=("a", "b")) + "\n  FILTER(STR(?a) < STR(?b))\n  " + SEX
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
        return (relationship(rel) + "\n  ?a wdt:P21 ?asex .\n"
                + dated('a', lo, hi, 9, drop_placeholders=False)
                + """
  OPTIONAL { ?b wdt:P21 ?bsex }
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
    for c in ("a", "b", "asex", "bsex", "cause"):
        mar[c] = mar.get(c, "").map(qid) if c in mar else ""
    for c in ("adob", "bdob", "start", "end", "adeath", "bdeath"):
        mar[c] = mar[c].str[:10] if c in mar else ""
    for c in ("aprec", "bprec"):
        mar[c] = pd.to_numeric(mar[c], errors="coerce").fillna(0).astype(int) if c in mar else 0
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
    mar["lasted_30_years"] = (mar["_dur"] >= MIN_YEARS).astype(int)
    return mar


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
    print(f"\n  {tag}: {len(m):,} labellable · {100*m['lasted_30_years'].mean():.1f}% reached {MIN_YEARS} years "
          f"· median duration {m['_dur'].median():.1f}")
    for src, g in m.groupby("_source"):
        print(f"      {src:<18} {len(g):>7,}  {100*g['lasted_30_years'].mean():5.1f}% reach {MIN_YEARS}")

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

#%% [markdown]
# ## 5. Sex decides which column, and nothing else may
#
# The man is column one. An earlier dataset in this project inherited the pair's Q-number ordering instead, which
# made that claim false for about half the rows and flipped the sign of every asymmetric feature.
#
# On a one-sided training row only one partner is known, so their sex alone decides which column they occupy and
# the other is `0000-00-00`. Where both sexes are recorded the couple must be opposite-sex; where only one is,
# the other is taken to be the opposite — which is what "the man is column one" has to mean for a row that names
# only a wife. A row whose two recorded sexes are the SAME is dropped rather than forced into the columns.

#%%
def to_columns(m, tag, strict):
    m = m.copy()
    if strict:
        keep = (((m["asex"] == MALE) & (m["bsex"] == FEMALE))
                | ((m["asex"] == FEMALE) & (m["bsex"] == MALE)))
        why = "opposite-sex, both recorded"
    else:
        same = (m["asex"] == m["bsex"]) & m["bsex"].ne("")
        keep = m["asex"].isin([MALE, FEMALE]) & ~same
        why = "the dated partner has a recorded sex and the pair is not known same-sex"
    print(f"  {tag}: {int(keep.sum()):,} of {len(m):,} usable on sex ({why})")
    m = m[keep].reset_index(drop=True)
    man_is_a = m["asex"].eq(MALE)
    m["dob_man"] = np.where(man_is_a, m["adob"], m["bdob"])
    m["dob_woman"] = np.where(man_is_a, m["bdob"], m["adob"])
    m["prec_man"] = np.where(man_is_a, m["aprec"], m["bprec"])
    m["prec_woman"] = np.where(man_is_a, m["bprec"], m["aprec"])
    m["man"] = np.where(man_is_a, m["a"], m["b"])
    m["woman"] = np.where(man_is_a, m["b"], m["a"])
    assert (m.loc[man_is_a, "dob_man"] == m.loc[man_is_a, "adob"]).all()
    assert (m.loc[~man_is_a, "dob_man"] == m.loc[~man_is_a, "bdob"]).all()
    print(f"      the man was partner A in {int(man_is_a.sum()):,} rows and B in {int((~man_is_a).sum()):,} — "
          f"which is why the column is assigned, never inherited")
    return m


test_c = to_columns(test_l, "test half", strict=True)
train_c = to_columns(train_l, "train half", strict=False)

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
    for side in ("man", "woman"):
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
    m["_pair"] = [f"{min(x, y)}|{max(x, y)}" for x, y in zip(m["man"], m["woman"])]
    # PREFER THE MORE PRECISE COPY, not merely a non-absent one. 3.5% of people carry two non-deprecated P569
    # statements at different precisions — Q104093886 has both 1830-01-01 (year) and 1830-07-20 (day) — so the
    # query returns two rows for the couple. Ranking only on "is it absent" left those tied, and the tie was
    # broken by whichever row the endpoint happened to return first, throwing away a known birthday for about
    # one couple in thirty for no reason at all.
    m["_prec"] = precision_class(m["dob_man"]) + precision_class(m["dob_woman"])
    m["_known"] = (m["dob_man"] != ABSENT).astype(int) + (m["dob_woman"] != ABSENT).astype(int)
    n0 = len(m)
    m = (m.sort_values(["_known", "_prec", "_dur"], ascending=[False, False, False])
          .drop_duplicates("_pair", keep="first").reset_index(drop=True))
    print(f"  {tag}: {n0 - len(m):,} duplicate rows collapsed (most dates first, then the most precise, then "
          f"the longest marriage) — {len(m):,} couples")
    return m


test_u = one_per_couple(test_c, "test half")
train_u = one_per_couple(train_c, "train half")

# The birth-gap sanity filter only applies where BOTH dates exist.
kept = []
for tag, m in (("test", test_u), ("train", train_u)):
    both = (m["dob_man"] != ABSENT) & (m["dob_woman"] != ABSENT)
    gap = np.abs(pd.to_numeric(m["dob_man"].str[:4], errors="coerce")
                 - pd.to_numeric(m["dob_woman"].str[:4], errors="coerce"))
    drop = both & (gap >= MAX_GAP_YEARS)
    if drop.any():
        print(f"  {tag}: {int(drop.sum()):,} couples born {MAX_GAP_YEARS}+ years apart — dropped")
    kept.append(m[~drop].reset_index(drop=True))
test_u, train_u = kept


def later_year(m):
    """The later of the two known birth years. With one partner absent this is the only known one, which is the
    right reading: the split asks when this couple lived, and an absent partner says nothing about that."""
    y = np.maximum(pd.to_numeric(m["dob_man"].str[:4], errors="coerce").fillna(0),
                   pd.to_numeric(m["dob_woman"].str[:4], errors="coerce").fillna(0))
    return y.astype(int)


test_u["_later"], train_u["_later"] = later_year(test_u), later_year(train_u)
test = test_u[test_u["_later"] > CUT].reset_index(drop=True)
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
test_people = set(test["man"]) | set(test["woman"])
test_people.discard("")
shares = train["man"].isin(test_people) | train["woman"].isin(test_people)
print(f"\n  {int(shares.sum()):,} training couples dropped for sharing a person with the held-out half")
train = train[~shares].reset_index(drop=True)

assert test["_later"].min() > CUT >= train["_later"].max(), "the split is not temporal"
tp = (set(train["man"]) | set(train["woman"])) - {""}
sp = (set(test["man"]) | set(test["woman"])) - {""}
assert not (tp & sp), f"{len(tp & sp)} people on both sides"
print(f"  train {len(train):,} couples (later known birth {train['_later'].min()}-{train['_later'].max()}) · "
      f"test {len(test):,} ({test['_later'].min()}-{test['_later'].max()})")
print(f"  checked: the split is temporal at {CUT}, and no person appears on both sides")
print(f"  positive rate: train {100*train['lasted_30_years'].mean():.2f}% · "
      f"test {100*test['lasted_30_years'].mean():.2f}%")
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
    tab = frame.groupby(y)["lasted_30_years"].agg(["mean", "size"])
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

n_both = int(((train["dob_man"] != ABSENT) & (train["dob_woman"] != ABSENT)).sum())
print(f"\n  the training half, by how much it knows:")
print(f"      {n_both:>7,} couples with BOTH dates ({100*n_both/max(len(train),1):.1f}%)")
print(f"      {len(train)-n_both:>7,} with one partner absent — kept, because the DURATION is known exactly")
for side in ("man", "woman"):
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
COLS = ["dob_man", "dob_woman", "lasted_30_years"]
for col in ("dob_man", "dob_woman"):
    assert test[col].str.match(r"^\d{4}-\d{2}-\d{2}$").all(), f"test.{col} malformed"
    assert not test[col].eq(ABSENT).any(), f"test.{col} has an absent date — the test half must be complete"
    assert not test[col].str.endswith("-00").any(), f"test.{col} is not day-precision"
    assert not (test[col].str[5:] == "01-01").any(), f"test.{col} still contains a 1 January"
    # EACH PARTNER IS IN THE WINDOW; THE COUPLE IS PLACED BY ITS LATER BIRTH. This asserted `y > CUT` on BOTH
    # columns, which contradicted the straddle fix in the very same file: a couple whose man was born 1845 and
    # whose wife was born 1860 is a held-out couple by the split rule, and its man's year is 1845. The query was
    # corrected to include those couples and this assertion was the copy that did not move — the same failure
    # mode as the split assertion that went on checking a floor the new data already cleared.
    y = test[col].str[:4].astype(int)
    assert ((y >= FLOOR) & (y <= CEIL)).all(), f"test.{col} outside {FLOOR}-{CEIL}"
assert (np.maximum(test["dob_man"].str[:4].astype(int),
                   test["dob_woman"].str[:4].astype(int)) > CUT).all(), \
    f"a held-out couple has BOTH births at or before {CUT} — it belongs in the training half"
print(f"  checked: every test date is day-precision inside {FLOOR}-{CEIL}, never a placeholder, and every "
      f"held-out couple's LATER birth is after {CUT}")
for col in ("dob_man", "dob_woman"):
    assert train[col].str.match(r"^\d{4}-\d{2}-\d{2}$").all(), f"train.{col} malformed"
assert not ((train["dob_man"] == ABSENT) & (train["dob_woman"] == ABSENT)).any(), \
    "a training row with no date at all carries no input"
print("  checked: every training row is well-formed and carries at least one date")

train = train.sample(frac=1.0, random_state=20260817).reset_index(drop=True)
test = test.sample(frac=1.0, random_state=20260818).reset_index(drop=True)
train[COLS].to_csv(os.path.join(OUT, "train.csv"), index=False)
test["id"] = [f"m{i:06d}" for i in range(len(test))]
test[["id", "dob_man", "dob_woman"]].to_csv(os.path.join(OUT, "test.csv"), index=False)
rng = np.random.default_rng(20260817)
sol = test[["id", "lasted_30_years"]].copy()
sol["Usage"] = np.where(rng.random(len(test)) < 0.30, "Public", "Private")
sol.to_csv(os.path.join(OUT, "solution.csv"), index=False)
samp = test[["id"]].copy()
samp["lasted_30_years"] = 0.5
samp.to_csv(os.path.join(OUT, "sample_submission.csv"), index=False)
for side in ("Public", "Private"):
    s = sol[sol["Usage"] == side]
    assert 0 < s["lasted_30_years"].sum() < len(s), f"the {side} half has one class only"
    print(f"    {side:<8} {len(s):>6,} rows, {100*s['lasted_30_years'].mean():5.2f}% positive")

print(f"\n  wrote train.csv ({len(train):,}) · test.csv ({len(test):,}) · solution.csv · sample_submission.csv")
print("\n  training rows, showing the three shapes it can take:")
ex = pd.concat([train[(train.dob_woman != ABSENT) & (train.dob_man.str[5:] != "00-00")].head(2),
                train[train.dob_man.str[5:] == "00-00"].head(2),
                train[train.dob_woman == ABSENT].head(2)])
print(ex[COLS].to_string(index=False))
print(f"\n  total build time {(time.time()-T0)/60:.1f} min")
