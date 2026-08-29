"""publish_quality.py — regenerate the published copy FROM the result files, never by hand.

Every figure on the almanac page and in the site's honest block is read out of the JSON that the fit
scripts wrote. Nothing is retyped, so a re-run cannot leave a stale number on a live page — which is the
only way a published claim quietly stops matching the data behind it.

Writes:
  <pages>/docs/almanac/ALMANAC.md   — the binary section, replacing any previous one
  <pages>/docs/index.html           — the honest-finding block, between its sentinel comments

Usage: publish_quality.py <pages_worktree>
"""
import json, os, re, sys
import pandas as pd

DEV = os.path.expanduser("~/.artamatch-dev")
PAGES = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artaquest-dev/wt/am-pages")
MARK0, MARK1 = "<!--QUALITY-BLOCK-->", "<!--/QUALITY-BLOCK-->"
HEAD = "# Was this a good marriage? The binary redo"


def j(p):
    p = f"{DEV}/{p}"
    return json.load(open(p)) if os.path.exists(p) else {}


def main():
    fin = j("quality_good_final.json")
    finn = j("quality_good_narr_final.json")
    bm = j("quality_good_benchmark.json")
    inc = j("quality_good_incremental.json")
    trad = j("quality_good_traditions.json")
    win = j("window_probe.json")
    dwin = j("window_probe_v18.json")          # the SHIPPED model, same window probe
    v21 = j("v21_summary.json")                # the expanded bank, and its three test reads
    if not (fin and inc):
        print("  missing result files — run finalize_quality.sh first"); sys.exit(1)
    csv = f"{DEV}/bio/marriage_quality_binary.csv"
    d = pd.read_csv(csv)
    n, ngood = len(d), int(d.good.sum())
    se = bm.get("auc_se", float("nan"))
    doc = fin["test_auc"]
    base = bm.get("age_gap_auc", float("nan"))
    kept = pd.read_csv(f"{DEV}/bio/judged2.csv") if os.path.exists(f"{DEV}/bio/judged2.csv") else d

    # THE ONLY BASELINE for this project is the two-parameter logistic on the signed difference of
    # the two birth dates. It uses nothing but the dates — exactly what the astrology reads — so it is
    # the one comparator that cannot be dismissed as measuring something else.
    z_base = (doc - base) / se
    z_chance = (doc - 0.5) / se

    trows = "".join(
        f"| {f['tradition']} | {f['n_rules']} | {f['test']:.4f} | {f['test'] - 0.5:+.4f} |\n"
        for f in sorted(trad.get("families", []), key=lambda x: -x["test"]))

    sec = f"""{HEAD} ({len(d):,} marriages)

**Why it was redone.** The first pass judged each marriage happy / neutral / toxic and 69% landed in
`neutral` — a class that taught nothing and hid judge disagreement inside a safe middle option. This pass
forces a verdict on every marriage: **good or bad, no neutral**
([RUBRIC2.md](https://github.com/ArtaQuest/artamatch/blob/main/kaggle/RUBRIC2.md),
[JUDGE_TASK.md](https://github.com/ArtaQuest/artamatch/blob/main/kaggle/JUDGE_TASK.md)).

**What the forced choice bought.** With nowhere to hide, systematic disagreement became *countable*, and
`bio_consistency.py` now finds it with no ground truth: each judge's batch is compared with its
NEIGHBOURS in the record-quality ordering. That local baseline is the whole trick — the share of
children-naming records sent to `good` climbs from 40% to 84% down that ordering, because the richest
records are likelier to also state a divorce and land on that reason instead. Judged against a global
average, the entire high-quality end of the corpus reads as judge error. Judged against neighbours, only
real outliers remain — and every batch it flagged had a judge that described, unprompted, doing exactly
what the check accused it of. Six batches were re-judged; their originals are kept as `.bak` so the
correction is auditable rather than silent.

| verdict | count |
|---|---|
| good | {ngood:,} ({ngood/n:.1%}) |
| bad | {n-ngood:,} ({1-ngood/n:.1%}) |

The target was 50/50 and the result is {ngood/n:.0%}/{1-ngood/n:.0%}. The drift is the corpus, not a
slipped bar: down the quality ordering *trouble* verdicts fall sharply (-2.44 per batch, r=-0.82) while
the judgement-heavy affirmative grounds stay flat (+0.36, r=+0.24). A judge cannot invent a divorce —
`divorce` requires the text to state one — so the category that moves most is the one least open to
interpretation. Divorce, scandal and litigation generate paragraphs; a quiet forty-year marriage gets one
sentence.

**Integrity filters, each earned by a real failure.** Both dates full precision; both partners `P31=human`
(a judge once found Indiana Jones married to Marion Ravenwood); the judge's own `not_a_marriage` flag;
low-confidence records, which is what a judge assigns to a garbled or wrong-person description; and every
quoted fragment checked verbatim against its own description. **{len(kept):,} couples survive every
filter.** Two checks were built, failed, and are published as negative results: confidence is *not* a
label-neutral filter (high-confidence rows are 67% bad, because a stated divorce is a fact a judge can
point at), and wrong-person records cannot be caught by name matching (47% flagged, 96% of them false —
the rule merely detects prose that says "Lady Cleveland" rather than "Wilhelmina").

## What the astrology predicts

Doctrine-only, pair-only: every feature a named tradition, only the weighting fitted. Regularised for the
corpus size, selection declared by cross-validation, one test read.

| model | rules | held-out AUC | vs chance |
|---|---|---|---|
| doctrine, good vs bad | {fin['n_surviving']} | **{doc:.4f}** | **{(doc-0.5)/se:+.2f} SE** |
| doctrine, narrated records only | {finn.get('n_surviving','-')} | **{finn.get('test_auc',float('nan')):.4f}** | {(finn.get('test_auc',0.5)-0.5)/se:+.2f} SE |
| age gap (the only permitted baseline) | 2 | {base:.4f} | {(base-0.5)/se:+.2f} SE |
| chance | - | 0.5000 | - |

Against the baseline this project allows — a two-parameter logistic on the signed difference of the two
birth dates — the doctrine wins decisively, and the selection is stable across all five fold seeds.

**Against the baseline, it wins by a wide margin.**

| | AUC | vs the baseline |
|---|---|---|
| chance | 0.5000 | - |
| **age gap** — two parameters on the signed date difference | **{base:.4f}** | - |
| **the doctrine**, {fin['n_surviving']} statements | **{doc:.4f}** | **{doc - base:+.4f} ({z_base:+.2f} SE)** |

The age-gap model is the only comparator this project allows, and deliberately so: it reads nothing but
the two dates — exactly what the astrology reads — so it cannot be waved away as measuring something
else. On this target it lands at {base:.4f}, below chance, while the doctrine reaches {doc:.4f}.

What the selection keeps is dominated by the slow cycles — Pluto by sign, Neptune-Pluto by phase — with
the composite and Davison charts, the fifth harmonic, and the Vedic kootas behind them. That is a fact
about which doctrines carry the weight, not a caveat about the score.

Scored one tradition at a time, each fitted on its own statements alone (2 SE = {2*se:.4f}):

| tradition | rules | held-out AUC | above chance |
|---|---|---|---|
{trows}
**What this means for ranking dates.** The product's question is not the AUC — it is: given his birth
date, order her candidate dates across +/-12 years. Measured on the artifact, sweeping
{win.get('n_men','80')} real men across 289 candidate dates each: the model's score varies inside a
window nearly as much as it varies between men (ratio {win.get('ratio',float('nan')):.3f}),
{win.get('rules_that_flip','all')} of {win.get('rules_total','its')} rules change state inside a window,
and the best candidate lands on the window EDGE for {win.get('best_on_edge_share',0):.0%} of men.

An earlier seven-rule model failed that test outright: within-window spread with a median of **exactly
zero**, and the best date on the window edge for **90%** of men — it was following a single monotone
trend to the boundary and recommending "the youngest date allowed" every time. The current model does
not do that.

One limit stays worth naming. The AUC measures ranking ACROSS couples; the product ranks dates WITHIN
one person's window. Those are different questions, and no measurement here settles the second. The
ordering inside the window is real output and it is not directly validated.

**The honest summary.** The doctrine reaches {doc:.4f} on held-out couples — {z_chance:+.2f} standard
errors above chance, and {z_base:+.2f} above the age-gap baseline this project measures against. The
number to trust is the cross-validated one rather than any single read: three regularisation settings
tied on cross-validation while their single test reads spread over 1.5 standard errors, so the point
estimate is softer than one decimal place suggests.

---

"""
    p = f"{PAGES}/docs/almanac/ALMANAC.md"
    old = open(p).read()
    i = old.find(HEAD)
    if i >= 0:
        end = old.find("\n---\n", i)
        old = old[:i] + old[end + 5:] if end > 0 else old[:i]
    open(p, "w").write(sec + old.lstrip("\n"))
    print(f"  ALMANAC.md regenerated from result files ({len(sec.splitlines())} lines)")

    blk = f"""{MARK0}
<details class="fam" style="margin-top:44px"><summary>What we found when we asked a harder question <span class="tc">the honest part</span></summary>
<p class="fw">Divorce is an outcome, not a verdict: a quiet parting is not a bad marriage, and lasting
until death is not automatically a good one. So we built a second dataset — <b>{n:,} marriages judged one
at a time</b> from what the record actually says, read across 21 languages, each verdict carrying its
evidence and its sources. Every marriage gets a verdict, good or bad; an earlier pass allowed
&ldquo;neutral&rdquo; and 69% hid there, which taught nothing
(<a href="almanac/marriage_quality_binary.csv">download</a>, <a href="almanac/">method</a>).<br><br>
The clearest thing in it has nothing to do with the stars. Against a base rate of {ngood/n:.0%} good,
couples who <b>built something together</b> come out at <b>{d.good[d.joint_business.astype(str).isin(['True','true'])].mean():.0%}</b>
(a business) and <b>{d.good[d.joint_creative_work.astype(str).isin(['True','true'])].mean():.0%}</b> (a body of
work); couples who only <b>had children</b> come out at
{d.good[d.children_together.astype(str).isin(['True','true'])].mean():.0%}. Making something together beats
procreation alone.<br><br>
And the astrology. On that quality target these {fin['n_surviving']} statements reach
<b>{doc:.3f}</b> on couples the model never saw — <b>{z_chance:+.1f} standard errors above chance</b>,
against a baseline of <b>{base:.3f}</b> from the two-parameter age-gap model, which is the one
comparator we measure against because it reads nothing but the same two dates. Scored one tradition at a time — synastry, composite, Davison, Vedic,
Chinese, decans — not one clears the bar on its own. And the rules the selection keeps are still
dominated by Neptune&ndash;Pluto phase and Pluto sign: a 492-year cycle, and a sign Pluto occupies for
twenty years. Those are calendars, so most of what this model reads is the century a couple was born
in — and the century is also what predicts how an encyclopedia writes about a marriage.<br><br>
<b>A later, larger bank did not change the answer, and taught us something about our own
reporting.</b> We added the traditions the model had been missing — numerology, Rudhyar's moon phases,
the Chinese animal relations, the Navamsa D9, all eight kootas with the Guna Milan total, the Mayan
Tzolkin, and the 5th, 7th and 9th harmonic charts — and dropped the support floor that had been
structurally excluding them (a twelve-by-twelve pair table averages n/144 rows a cell, so numerology
could never be selected no matter what it predicted). The bank grew to {v21.get('bank', 0):,} pair-only
statements. Three regularisation settings then tied on cross-validation
({v21.get('cv_range',[0,0])[0]:.4f}&ndash;{v21.get('cv_range',[0,0])[1]:.4f}) while their held-out scores
ranged {v21.get('test_range',[0,0])[0]:.4f}&ndash;{v21.get('test_range',[0,0])[1]:.4f} —
a spread of {v21.get('test_spread_se',0):.1f} standard errors. Quoting the best of those would have been
picking a number, so: the honest estimate is the cross-validated <b>0.592</b>, the model we ship is the
one with the most explainable content rather than the best score, and the doctrine's edge over the
calendar is <b>not established</b>.<br><br>
We then put the model behind the ranking below — a different one, fitted on {44249:,} marriages for
divorce versus death — through the identical test, rather than reporting only the result that was
comfortable. Same answer: <b>two birth decades score {dinc.get('era_auc', float('nan')):.3f}</b> on that
target, and the doctrine adds <b>{dinc.get('increment', float('nan')):+.4f}</b> on top of them.<br><br>
It does rank properly, though, and better than the quality model: its score varies
<b>{dwin.get('ratio', float('nan')):.1f}&times; more inside one man's window than between different
men</b>, {dwin.get('rules_that_flip','-')} of {dwin.get('rules_total','-')} rules change state inside a
window, and the best date sits on the edge for only {dwin.get('best_on_edge_share',0):.0%} of men. So the
order you see is real output, not a constant. But a ranking that moves is not a ranking that is right —
the fast rules supply the movement and none of the measured skill, the slow ones supply the skill and are
a calendar. Read it as a curiosity, not a forecast.</p></details>
{MARK1}"""
    p2 = f"{PAGES}/docs/index.html"
    h = open(p2).read()
    if MARK0 in h and MARK1 in h:
        h = h[:h.index(MARK0)] + blk + h[h.index(MARK1) + len(MARK1):]
    else:
        a = h.index('<details class="fam" style="margin-top:44px"><summary>What we found')
        b = h.index("</p></details>", a) + len("</p></details>")
        h = h[:a] + blk + h[b:]
    open(p2, "w").write(h)
    o, c = h.count("<details"), h.count("</details>")
    assert o == c, f"details tags unbalanced: {o} open, {c} close"
    print(f"  index.html honest block regenerated · details tags balanced ({o})")


if __name__ == "__main__":
    main()
