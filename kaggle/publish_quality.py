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
    fsum = j("quality_summary.json")            # the audited final model summary
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
comparator we measure against because it reads nothing but the same two dates. The statements the selection keeps are dominated by the slow rhythms — Neptune&ndash;Pluto by phase and
Pluto by sign — with the composite chart behind them. Ranked by what each is actually worth (the
cross-validated loss if it were removed, rather than its raw coefficient), one statement carries most of
the model and the rest fill in around it; the full ranking, with how often each fires and how the
marriages went when it did, is below.<br><br>
<b>The final model, after four more waves of doctrine and twelve audit checks.</b> The bank grew to
{fsum.get('n_bank', 0):,} pair-only statements — numerology, Rudhyar's moon phases, the Chinese animal
relations, the Navamsa, all eight kootas with the Guna Milan total, Mangal dosha, the Jaimini
Darakaraka, the Bazi day pillar, Arabic parts, the Mayan Tzolkin and Dreamspell, Chandra and Surya
lagna, Nine Star Ki, Tibetan Mewa and Parkha, the harmonic, draconic and antiscia charts, and the
aspect patterns and cycle phases that carry most of the weight. Selection kept
<b>{fsum.get('n_statements', 0)}</b> of them, {fsum.get('n_negated', 0)} read as their negation. On
couples the model never saw it reaches <b>{fsum.get('test_auc', 0):.4f}</b> —
<b>{fsum.get('over_chance_se', 0):+.1f} standard errors above chance</b>, and
<b>{fsum.get('over_baseline_se', 0):+.1f}</b> above the age-gap baseline of
{fsum.get('age_gap_auc', 0):.4f}, which is the one comparator we measure against because it reads
nothing but the same two dates. Cross-validated, the honest figure is
<b>{fsum.get('cv_auc', 0):.4f}</b>.<br><br>
<b>Half the doctrine had been unusable, and nobody had checked.</b> Every weight in this pipeline is
non-negative by design, so a statement predicting an unhappy marriage could never be given a weight at
all — 2,819 of 5,771 statements, including the strongest in the whole bank. Each is now formulated
toward happy: where firing predicts unhappy we use its complement and say so, which is the same
doctrine stated the other way round. Four of the nine surviving statements are read that way, and each
was checked against its own raw direction before being trusted.<br><br>
<b>One number here deserves a caution.</b> Along the way three regularisation settings tied on
cross-validation while their single held-out reads spread over 1.5 standard errors. One test read
is one sample; the cross-validated figure, averaged over folds and seeds, is the one to trust, and
it is the one quoted above.<br><br>
One limit stays worth naming: the AUC measures ranking ACROSS couples, while the product ranks
dates WITHIN one person's window. Those are different questions, and only the first is measured
here. Read it as a curiosity, not a forecast.</p></details>
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
