#%% [markdown]
# # Two birth dates, one question: did the marriage last thirty years?
#
# This notebook builds the **ArtaMatch Duration** dataset from scratch, from live SPARQL against Wikidata. The
# queries are in the cells below, so anyone can re-run them and get a different answer as Wikidata changes.
#
# The output is three columns.
#
# | column | meaning |
# |---|---|
# | `dob_man` | the man's date of birth, `YYYY-MM-DD`, known to the day |
# | `dob_woman` | the woman's date of birth, known to the day |
# | `lasted_30_years` | 1 if the marriage lasted thirty years or longer, else 0 |
#
# Two dates in, one bit out. No names, no places, no occupations — **and no marriage date**, which is the input a
# reader will most expect to see and the one most worth withholding: the wedding year encodes the era, and an
# 1830 marriage had less recorded room to reach thirty years than an 1880 one. The question is whether the two
# BIRTH dates carry anything.
#
# ## Where the label comes from
#
# Wikidata records a marriage as a `P26` statement with qualifiers, and an infobox renders them like this:
#
# > **Spouses**  Mileva Marić (m. 1903; div. 1919) · Elsa Löwenthal (m. 1919; died 1936)
#
# Those are the two cases, and the duration is computed the same way the infobox reads:
#
# * **an end date is recorded** (`P582`) — the marriage ran from `P580` to `P582`. Einstein's first: 16 years.
# * **no end date** — the marriage ran until somebody died, so the end is the EARLIER of the two death dates
#   (`P570`). Einstein's second: 1919 to Elsa's death in 1936, 17 years.
#
# `lasted_30_years` is then `(end - start) >= 30 years`, and nothing else. **A marriage ended by a death is not
# automatically a long one**: ended at twelve years it is a 0, at forty years it is a 1. Death buys no credit.
#
# ## Why 1600–1900, and why the split is 1850
#
# Everybody born on or before 1900 is dead. That matters more here than anywhere else in this project: a marriage
# still running cannot be labelled, and a marriage that has not yet had thirty years cannot reach thirty. Closing
# the window at 1900 removes right-censoring almost entirely — every marriage in this file has ended, and every
# positive was observable.
#
# The split is **temporal**: couples whose later birth falls up to 1850 train, and 1850–1900 are held out. So the
# task is not "rank couples drawn from the years you learned from" but "learn from the earlier couples and predict
# the later ones".
#
# **The base rate shifts across that boundary and it is worth knowing before you start**: about 32% of the
# training marriages reach thirty years against about 44% of the held-out ones. Earlier-born couples have shorter
# recorded marriages — they died younger and their records are thinner — so this is the reverse of the shift the
# parenthood version of this dataset had. It is printed below rather than asserted.
#
# ## The one confound worth naming out loud
#
# The two label cases behave very differently: marriages with a recorded END DATE reach thirty years about 16% of
# the time, while marriages that ran until a death do so about 53% of the time. A model cannot see which case a
# couple is in — that is not a column — but "ended while both spouses were alive" correlates with things it can
# see. This is the sharpest confound in the design, and the published baselines include a case-only reference so a
# leaderboard place can be read against it.

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
T0 = time.time()

FLOOR, CEIL = 1600, 1900          # everybody born inside this window is certainly dead
CUT = 1850                        # couples whose later birth is after this are held out
MIN_YEARS = 30                    # the label's threshold
MAX_GAP_YEARS = 60
MALE, FEMALE = "Q6581097", "Q6581072"
SLICE = int(os.environ.get("AQ_YEAR_SLICE", "25"))

# The end causes Wikidata actually records on a marriage, looked up rather than guessed. Only used for reporting
# how the file breaks down — the LABEL is duration, and never the cause.
BREAKDOWN = {"Q93190": "divorce", "Q701040": "annulment", "Q5561011": "marital separation",
             "Q3456503": "repudiation", "Q1299585": "declaration of nullity", "Q1142948": "legal separation"}
DEATHCAUSE = {"Q24037741": "death of spouse", "Q99521170": "death of subject", "Q4": "death",
              "Q90110620": "death of partner", "Q179115": "widow"}

ENDPOINTS = ["https://qlever.dev/api/wikidata", "https://query.wikidata.org/sparql"]
_DEAD = set()
for _ep in os.environ.get("AQ_SKIP_ENDPOINTS", "").split(","):
    if _ep.strip():
        _DEAD.update(b for b in ENDPOINTS if _ep.strip() in b)

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

    Both endpoints have their own failure mode and neither is a bug to retry harder: qlever answers 429 to a
    client that has asked a lot, and the Wikidata Query Service answers 504 when a query exceeds its 60 seconds.
    Slicing keeps queries small enough for the second; striking off keeps us from paying six backoffs per query to
    rediscover the first.
    """
    last = None
    live = [b for b in ENDPOINTS if b not in _DEAD] or list(ENDPOINTS)
    for base in live:
        acc = "application/sparql-results+json" if "query.wikidata.org" in base else accept
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
                if attempt == tries - 1:
                    if e.code == 429:
                        _DEAD.add(base)
                        print(f"    {base.split('/')[2]}: rate-limited — struck off for this run", flush=True)
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
    """Pages, count-verified, refusing TRUNCATION only — an extra row deduplicates away, a missing one lies."""
    t = time.time()
    want = sparql_count(select, body)
    frames, got = [], 0
    while got < want:
        q = (f"{PREFIXES}\nSELECT {select} WHERE {{ {body} }}" + (f" ORDER BY {order}" if order else "")
             + f" LIMIT {page} OFFSET {got}")
        raw = _fetch(q, "text/tab-separated-values")
        df = pd.read_csv(io.StringIO(raw), sep="\t", dtype=str, keep_default_na=False)
        if len(df) == 0:
            break
        # The Wikidata Query Service decorates values with a type suffix and wraps URIs in angle brackets;
        # qlever's TSV is plain. Normalise so both parse to the same frame.
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


def sparql_sliced(select, body_fn, name, order=None):
    """Fetch in year slices of the first partner and concatenate; each slice cached atomically."""
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
        os.replace(cache + ".tmp", cache)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    print(f"  {name}: {len(out):,} rows over {len(frames)} slices", flush=True)
    return out


def qid(s):
    return s.rsplit("/", 1)[-1].rstrip(">")


#%% [markdown]
# ## 1. Every marriage with a start date and two day-precision births
#
# `FILTER(STR(?a) < STR(?b))` keeps each pair once: Wikidata states a marriage from both sides.
#
# Three filters on each birth date, and the third is the one people miss. Day precision (`timePrecision >= 11`),
# inside the window, and **not 1 January** — among day-precision births 1 January occurs about 1.7 times as often
# as a median day, where 2 January and 31 December sit at 1.0, because a source that knew only the year was
# imported with a day anyway. Those records claim a precision they do not have.
#
# `wikibase:rank != DeprecatedRank` excludes birth dates Wikidata has explicitly marked wrong.

#%%
def dated(v, lo, hi):
    return f"""
  ?{v} p:P569 ?{v}st . ?{v}st psv:P569 ?{v}v .
  ?{v}st wikibase:rank ?{v}rank . FILTER(?{v}rank != wikibase:DeprecatedRank)
  ?{v}v wikibase:timeValue ?{v}dob ; wikibase:timePrecision ?{v}prec .
  FILTER(?{v}prec >= 11)
  FILTER(YEAR(?{v}dob) >= {lo} && YEAR(?{v}dob) <= {hi})
  FILTER(!(MONTH(?{v}dob) = 1 && DAY(?{v}dob) = 1))
"""


def marriage_body(lo, hi):
    # The slice bounds ?a only; ?b keeps the whole window, so each couple falls in exactly one slice.
    return f"""
  ?a p:P26 ?m . ?m ps:P26 ?b .
  ?m pq:P580 ?start .
  FILTER(STR(?a) < STR(?b))
  ?a wdt:P31 wd:Q5 . ?b wdt:P31 wd:Q5 .
  ?a wdt:P21 ?asex . ?b wdt:P21 ?bsex .
  OPTIONAL {{ ?m pq:P582 ?end }}
  OPTIONAL {{ ?m pq:P1534 ?cause }}
  OPTIONAL {{ ?a wdt:P570 ?adeath }}
  OPTIONAL {{ ?b wdt:P570 ?bdeath }}
{dated('a', lo, hi)}{dated('b', FLOOR, CEIL)}"""


mar = sparql_sliced("DISTINCT ?a ?b ?adob ?bdob ?asex ?bsex ?start ?end ?cause ?adeath ?bdeath",
                    marriage_body, "marriages with a start date", order="?a ?b")
for c in ("a", "b", "asex", "bsex", "cause"):
    mar[c] = mar[c].map(lambda s: qid(s) if s else "")
for c in ("adob", "bdob", "start", "end", "adeath", "bdeath"):
    mar[c] = mar[c].str[:10]
print(f"  distinct people: {len(set(mar['a']) | set(mar['b'])):,}")

#%% [markdown]
# ## 2. The duration, exactly as an infobox computes it
#
# End = the recorded end date if there is one, otherwise the earlier of the two deaths. A marriage with neither is
# unlabellable and is dropped, with the count printed.

#%%
YEAR = 365.2425


def as_days(s):
    """Days since 1600-01-01. Resolution-independent: `astype("int64")` on a datetime column returns MICROseconds
    here, not nanoseconds, and dividing by a nanosecond constant once turned a 60-year sanity filter into a no-op
    that removed nothing while reporting success."""
    d = pd.to_datetime(s, errors="coerce")
    return (d.to_numpy(dtype="datetime64[D]").astype("float64")
            - np.datetime64("1600-01-01").astype("datetime64[D]").astype("float64"))


start = as_days(mar["start"])
end_stated = as_days(mar["end"])
d_a, d_b = as_days(mar["adeath"]), as_days(mar["bdeath"])
first_death = np.fmin(np.where(np.isnan(d_a), np.inf, d_a), np.where(np.isnan(d_b), np.inf, d_b))
first_death = np.where(np.isinf(first_death), np.nan, first_death)

end = np.where(~np.isnan(end_stated), end_stated, first_death)
mar["_dur"] = (end - start) / YEAR
mar["_source"] = np.where(~np.isnan(end_stated), "end date stated", "ran until a death")

before = len(mar)
mar = mar[~np.isnan(end) & ~np.isnan(start)].reset_index(drop=True)
print(f"  {before - len(mar):,} marriages had neither an end date nor a death date — unlabellable, dropped")

# A negative duration is a data error, not a short marriage.
bad = mar["_dur"] < 0
if bad.any():
    print(f"  {int(bad.sum()):,} marriages ended BEFORE they started — dropped as data errors")
    mar = mar[~bad].reset_index(drop=True)

mar["lasted_30_years"] = (mar["_dur"] >= MIN_YEARS).astype(int)
print(f"\n  {len(mar):,} labellable marriages · {100*mar['lasted_30_years'].mean():.1f}% lasted "
      f"{MIN_YEARS}+ years")
for src, g in mar.groupby("_source"):
    print(f"      {src:<18} {len(g):>7,}  {100*g['lasted_30_years'].mean():5.1f}% reach {MIN_YEARS} years")
print("\n  THE CONFOUND, printed rather than described: those two rates differ enormously, and a model cannot")
print("  see which case a couple is in. It can see things that correlate with it, so the baselines include a")
print("  case-only reference.")

# How the endings break down, for the record. The label never uses the cause.
named = collections.Counter()
for c in mar["cause"]:
    if c in BREAKDOWN:
        named[BREAKDOWN[c]] += 1
    elif c in DEATHCAUSE:
        named["a death"] += 1
    elif c:
        named["other cause"] += 1
print(f"\n  of the {len(mar):,}, {sum(named.values()):,} state WHY they ended:")
for k, v in named.most_common():
    print(f"      {v:>6,}  {k}")

#%% [markdown]
# ## 3. Sex decides the columns, and nothing else may
#
# The first column is the man and the second the woman. An earlier dataset in this project inherited the pair's
# Q-number ordering instead, which made that claim false for about half the rows and scrambled the sign of every
# asymmetric feature.

#%%
opp = mar[((mar["asex"] == MALE) & (mar["bsex"] == FEMALE))
          | ((mar["asex"] == FEMALE) & (mar["bsex"] == MALE))].copy()
print(f"  opposite-sex only: {len(opp):,} of {len(mar):,}")
man_is_a = opp["asex"].eq(MALE)
opp["dob_man"] = np.where(man_is_a, opp["adob"], opp["bdob"])
opp["dob_woman"] = np.where(man_is_a, opp["bdob"], opp["adob"])
opp["man"] = np.where(man_is_a, opp["a"], opp["b"])
opp["woman"] = np.where(man_is_a, opp["b"], opp["a"])
assert (opp.loc[man_is_a, "dob_man"] == opp.loc[man_is_a, "adob"]).all()
assert (opp.loc[~man_is_a, "dob_man"] == opp.loc[~man_is_a, "bdob"]).all()
print(f"  the man was partner A in {int(man_is_a.sum()):,} rows and B in {int((~man_is_a).sum()):,} — which is "
      f"why the order is assigned, never inherited")

gap = np.abs(as_days(opp["dob_man"]) - as_days(opp["dob_woman"])) / YEAR
opp = opp[gap < MAX_GAP_YEARS].reset_index(drop=True)
print(f"  births less than {MAX_GAP_YEARS} years apart: {len(opp):,}")

# One row per couple. A couple married twice keeps its LONGEST marriage, because the question is whether these
# two people sustained a marriage, and the alternative — averaging, or picking the first — answers neither.
opp["_pair"] = [f"{min(a, b)}|{max(a, b)}" for a, b in zip(opp["man"], opp["woman"])]
dups = int(opp["_pair"].duplicated().sum())
opp = opp.sort_values("_dur", ascending=False).drop_duplicates("_pair", keep="first").reset_index(drop=True)
print(f"  {dups:,} duplicate pair rows collapsed, keeping the longest marriage: {len(opp):,} couples")

#%% [markdown]
# ## 4. The split is by TIME, and the boundary is asserted
#
# Couples whose later birth is after 1850 are held out. Person-disjointness is restored from the training side:
# any training couple sharing a person with a held-out couple is dropped, which costs training rows rather than
# compromising the test set — the test set is the measurement.

#%%
opp["_later"] = np.maximum(opp["dob_man"].str[:4].astype(int), opp["dob_woman"].str[:4].astype(int))
is_test = opp["_later"] > CUT
test_people = set(opp.loc[is_test, "man"]) | set(opp.loc[is_test, "woman"])
shares = opp["man"].isin(test_people) | opp["woman"].isin(test_people)
drop_person = shares & ~is_test
train = opp[~is_test & ~drop_person].reset_index(drop=True)
test = opp[is_test].reset_index(drop=True)
print(f"  {int(drop_person.sum()):,} training couples dropped for sharing a person with the held-out half")
print(f"  train {len(train):,} (later birth {train['_later'].min()}-{train['_later'].max()}) · "
      f"test {len(test):,} ({test['_later'].min()}-{test['_later'].max()})")
assert test["_later"].min() > CUT >= train["_later"].max(), "the split is not temporal"
print(f"  every held-out couple's later birth is after {CUT}; every training couple's is at or before it")
print(f"  positive rate: train {100*train['lasted_30_years'].mean():.2f}% · "
      f"test {100*test['lasted_30_years'].mean():.2f}%")
print("  those differ, and they should: earlier-born couples died younger and their records are thinner, so")
print("  fewer of their marriages reach thirty years. It is the reverse of the parenthood dataset's shift.")
tp = set(train["man"]) | set(train["woman"])
sp = set(test["man"]) | set(test["woman"])
assert not (tp & sp), f"{len(tp & sp)} people on both sides"
print("  checked: no person appears on both sides")

#%% [markdown]
# ## 5. The files

#%%
COLS = ["dob_man", "dob_woman", "lasted_30_years"]
for name, frame in (("train", train), ("test", test)):
    for col in ("dob_man", "dob_woman"):
        assert frame[col].str.match(r"^\d{4}-\d{2}-\d{2}$").all(), f"{name}.{col} malformed"
        assert not (frame[col].str[5:] == "01-01").any(), f"{name}.{col} still contains a 1 January"
        yrs = frame[col].str[:4].astype(int)
        assert ((yrs >= FLOOR) & (yrs <= CEIL)).all(), f"{name}.{col} outside {FLOOR}-{CEIL}"
print(f"  checked: every written date is day-precision, in {FLOOR}-{CEIL}, and never 1 January")

train = train.sample(frac=1.0, random_state=20260817).reset_index(drop=True)
test = test.sample(frac=1.0, random_state=20260818).reset_index(drop=True)
train[COLS].to_csv(os.path.join(OUT, "train.csv"), index=False)
test = test.reset_index(drop=True)
test["id"] = [f"m{i:06d}" for i in range(len(test))]
test[["id", "dob_man", "dob_woman"]].to_csv(os.path.join(OUT, "test.csv"), index=False)
rng = np.random.default_rng(20260817)
usage = np.where(rng.random(len(test)) < 0.30, "Public", "Private")
sol = test[["id", "lasted_30_years"]].copy()
sol["Usage"] = usage
sol.to_csv(os.path.join(OUT, "solution.csv"), index=False)
samp = test[["id"]].copy()
samp["lasted_30_years"] = 0.5
samp.to_csv(os.path.join(OUT, "sample_submission.csv"), index=False)
for side in ("Public", "Private"):
    s = sol[sol["Usage"] == side]
    assert 0 < s["lasted_30_years"].sum() < len(s), f"the {side} half has one class only"
    print(f"    {side:<8} {len(s):>6,} rows, {100*s['lasted_30_years'].mean():5.2f}% positive")

print(f"\n  wrote train.csv ({len(train):,}) · test.csv ({len(test):,}) · solution.csv · sample_submission.csv")
print(train[COLS].head(3).to_string(index=False))
print(f"\n  total build time {(time.time()-T0)/60:.1f} min")
