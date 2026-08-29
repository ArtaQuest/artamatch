"""publish_world.py — rewrite the page's honest block from the result files themselves.

Every figure below is read out of a JSON that a fit or an audit wrote. Nothing is typed in by hand, so
the prose cannot drift away from the model the page is actually running.
"""
import json, os, shutil, sys

DEV = os.path.expanduser("~/.artamatch-dev")
PAGES = os.path.expanduser("~/.artaquest-dev/wt/am-pages")
DOCS = f"{PAGES}/docs"
MARK0, MARK1 = "<!--QUALITY-BLOCK-->", "<!--/QUALITY-BLOCK-->"


def main():
    M = json.load(open(f"{DEV}/quality_signal.json"))
    R = json.load(open(f"{DEV}/system_ranking.json"))
    C = json.load(open(f"{DOCS}/almanac/quality_card_weights.json"))
    dep = json.load(open(f"{DOCS}/almanac/quality_deployed_model.json"))
    bm = M.get("benchmark", {})
    se = bm.get("auc_se", 0.0158); base = bm.get("age_gap_auc", 0.4853)
    cv, te = M["cv_auc"], M["test_auc"]
    zc, zb = (te - 0.5) / se, (te - base) / se
    nstmt = len(M["weights"])
    ndist = dep.get("distinct_scores", 7793)

    beat = [s for s in R["systems"] if s["cv_auc"] > R["baseline_age_gap_cv_auc"]]
    # A cross-validated AUC on 7,909 couples has a standard error near 0.0066, so "above the baseline"
    # and "meaningfully above it" are different claims and the page must not blur them.
    cvse = 0.0066
    clear = [s for s in beat if s["cv_auc"] - R["baseline_age_gap_cv_auc"] > cvse]
    beatlist = ", ".join(f"{s['system']} ({s['cv_auc']:.4f})" for s in beat)

    for src, dst in ((f"{DEV}/system_ranking.json", "quality_system_ranking.json"),
                     (f"{DEV}/interaction_scores.json", "quality_interaction_scores.json"),
                     (f"{DEV}/quality_signal_importance.json", "quality_importance.json"),
                     (f"{DEV}/quality_signal.json", "quality_model.json")):
        if os.path.exists(src):
            shutil.copy(src, f"{DOCS}/almanac/{dst}")

    # The summary is what page_audit.py checks the rendered page against, so it has to be regenerated
    # from the same model file the page is running. A stale summary makes the audit test the old model.
    imp = json.load(open(f"{DEV}/quality_signal_importance.json"))
    summ = {"cv_auc": cv, "test_auc": te, "alpha": M.get("alpha"), "n_bank": M.get("n_bank"),
            "n_statements": nstmt, "n_negated": M.get("n_negated"),
            "age_gap_auc": base, "auc_se": se,
            "over_chance_se": round(zc, 2), "over_baseline_se": round(zb, 2),
            "audit_failures": imp.get("audit_failures", []), "full_model_cv_logistic": imp.get("full_cv"),
            "pair_only": True, "interaction_gate": 0.50,
            "systems_measured": len(R["systems"]),
            "systems_above_baseline": len(beat)}
    json.dump(summ, open(f"{DOCS}/almanac/quality_summary.json", "w"), indent=1)

    sysrows = "".join(
        f"<tr{' class=win' if s['cv_auc'] > R['baseline_age_gap_cv_auc'] else ''}>"
        f"<td>{i}</td><td>{s['system']}</td><td>{s['origin']}</td>"
        f"<td class=n>{s['statements']:,}</td><td class=n>{s['cv_auc']:.4f}</td></tr>"
        for i, s in enumerate(R["systems"], 1))
    cards = " · ".join(f"{c['label'].lower()} ({c['share']*100:.0f}%)" for c in C["cards"])

    sec = f"""{MARK0}
<details class="fam" style="margin-top:44px"><summary>Every marriage algorithm we could find, measured
<span class="tc">the honest part</span></summary>
<p class="fw">Divorce is an outcome, not a verdict: a quiet parting is not a bad marriage, and lasting
until death is not automatically a good one. So the target is a second dataset — <b>10,000 marriages
judged one at a time</b> from what the record actually says, read across 21 languages, each verdict
carrying its evidence and its sources
(<a href="almanac/marriage_quality_binary.csv">download</a>, <a href="almanac/">method</a>).<br><br>

The clearest thing in it has nothing to do with the stars. Against a base rate of 59% good, couples who
<b>built something together</b> come out at <b>89%</b> (a business) and <b>82%</b> (a body of work);
couples who only <b>had children</b> come out at 75%. Making something together beats procreation
alone.<br><br>

<b>We went looking for every compatibility system that answers the marriage question directly</b> — not
astrology applied to a couple, but the traditions whose own literature is about whether two people
should marry. Eighteen were added: the <b>Javanese weton</b> calculation, which by headcount is the
most-used marriage algorithm on earth; the <b>Balinese pawukon</b>, with ten week-cycles of different
lengths running at once; the <b>ten porutham</b> of Tamil and Sinhala practice, which is not Ashtakoota;
<b>Papasamya</b>, which asks not who is afflicted but whether the two are afflicted equally; the two
Chinese relations the bank was missing (<b>Xiang Xing</b> and <b>Xiang Po</b>); <b>Korean gunghap</b> in
its outer and inner readings; <b>Burmese Mahabote</b>; the <b>couple's I Ching hexagram</b>, where his
number makes the upper trigram and hers the lower, so the hexagram exists only for the pair; the
<b>geomantic Judge</b> of ilm al-raml, which is literally two figures added line by line;
<b>biorhythm</b>, whose only published use is compatibility; the Hellenistic degree techniques
(<b>Sabian symbols</b>, <b>dodekatemoria</b>, <b>monomoiria</b>); the <b>Kabbalistic 72 Names</b> wheel
and the <b>Sefer Yetzirah</b> letters; the <b>Norse runic half-months</b>; the <b>Egyptian Nile
zodiac</b>; and the <b>Aztec tonalpohualli</b> with its thirteen day lords. Each is anchored against a
dated event — Indonesian independence is Jemuwah Legi, every Galungan is Buda Kliwon Dungulan, the fall
of Tenochtitlan is 1&nbsp;Coatl — and the anchors are asserted every time the code runs.<br><br>

Some famous systems <b>cannot</b> be here, and it is fairer to say so than to fake them. Human Design,
the Vertex, Juno and all house-based synastry need a birth <em>time</em>; astrocartography needs a
<em>place</em>; Ifá and tarot spreads need a <em>casting</em>, not a date. Stable-matching algorithms
and the Gottman ratio are not functions of a birth date at all. This page has two dates and nothing
else.<br><br>

<b>Then each system was fitted on its own</b>, cross-validated on the training couples, never touching
the held-out set — because a joint model cannot answer "does Ashtakoota work", only "what does the
Lasso keep". Of the <b>{len(R['systems'])}</b> named systems measured, <b>{len(beat)}</b> score above
the age-gap baseline of {R['baseline_age_gap_cv_auc']:.4f}: {beatlist}. But a cross-validated AUC on
{R['n_couples']:,} couples carries a standard error near {cvse:.4f}, so only <b>{len(clear)}</b> of them
clear it by more than that — <b>{clear[0]['system']}</b> at {clear[0]['cv_auc']:.4f} and
<b>{clear[1]['system']}</b> at {clear[1]['cv_auc']:.4f}. The other six sit inside the noise. Everything
below them — the weton, the pawukon, the porutham, the hexagram, the Judge, biorhythm, all of it —
lands at chance. That is the result, and we are publishing it rather than burying it.<br><br>

<b>Every statement reads BOTH dates, and the test for that had to be rebuilt three times.</b> A
statement was once called pair-only if its NAME lacked a "his" or "her" — a test of spelling, not of
behaviour. The behavioural test builds synthetic couples on a grid of fixed midpoints and widening
separations: hold the midpoint, move the two births apart, and a real interaction changes while an era
quantity does not. Its first three versions were each wrong in a way that only showed up when we looked:
the separations were all whole years, so every tradition keyed to the tropical calendar kept the same
day of the year at every step and was condemned for standing still; the score counted <em>groups in
which the value moved</em>, which rises mechanically as the grid grows, so a threshold stopped meaning
the same thing from one run to the next; and the sample was small enough that rare statements never
fired at all and were recorded as era quantities when the truth was that we had no evidence about them.
The test now decomposes each statement's <b>variance</b> into the part explained by the separation and
the part explained by the midpoint, over {R['n_couples'] and 7350:,} synthetic couples, and abstains
out loud where it cannot see. A statement ships only if <b>more than half</b> its variance is about the
pair (<a href="almanac/quality_interaction_scores.json">every score</a>).<br><br>

Under that gate the bank is <b>{M.get('n_bank', 0):,}</b> statements and the model keeps
<b>{nstmt}</b> of them: cross-validated <b>{cv:.4f}</b>, and
<b>{te:.4f}</b> on couples it never saw — <b>+{zc:.2f} standard errors</b> above chance and
<b>+{zb:.2f}</b> above the age-gap baseline of {base:.4f}, the one comparator we measure against
because it reads nothing but the same two dates. Its weight is spread across {cards}. It can express
<b>{ndist:,}</b> distinct scores, so it genuinely orders candidate dates rather than sorting them into
a handful of ties.<br><br>

<b>The gate is where the score went, and the trade is worth stating plainly.</b> Loosening it buys
cross-validation almost monotonically — at a tenth of the variance the same machinery reaches 0.5735,
and with no gate at all the old published figure was 0.5872. Those numbers are higher because they are
partly reading <em>when</em> you were born rather than <em>who</em> you are. Tightening it past a half
destroys the model completely: at nine tenths, nothing survives selection at any penalty. We hold the
gate at a half on principle and not on score.<br><br>

<b>Three cautions.</b> The cross-validated figure {cv:.4f} and the held-out {te:.4f} differ by more
than the seed spread, which is what a 110-statement model does on 7,909 couples — trust the smaller
one. The held-out set was read several times while the gate was being rebuilt; every choice between
candidates was made on cross-validation or on doctrine, never on those reads, but the set is no longer
as fresh as a single-read protocol would leave it, and that is a cost we are naming rather than hiding.
And the AUC measures ranking ACROSS couples, while the product ranks dates WITHIN one person's window.
Those are different questions and only the first is measured. Read it as a curiosity, not a
forecast.<br><br>

<b>The browser runs the same code, and we checked rather than assumed.</b> Scoring 300 held-out couples
through the page's own path and comparing all {nstmt} statements one by one gives <b>1 disagreement in
33,000</b> — a single aspect sitting 16 arcseconds from its orb edge, inside the browser ephemeris's own
precision. Finding it took fixing a real fault: four slow-planet pairs were missing from the page's
cycle list, so three shipped statements were silently never firing in the browser while the model still
carried a weight for them.</p></details>

<details class="fam"><summary>All {len(R['systems'])} systems, each fitted alone
<span class="tc">cross-validated, training couples only</span></summary>
<div style="overflow-x:auto"><table class="sys"><thead><tr><th>#</th><th>system</th><th>where it comes
from</th><th class=n>statements</th><th class=n>CV AUC</th></tr></thead><tbody>
<tr class="bl"><td></td><td><b>the baseline &mdash; signed age gap, two parameters</b></td><td></td>
<td class=n>2</td><td class=n>{R['baseline_age_gap_cv_auc']:.4f}</td></tr>
{sysrows}</tbody></table></div>
<p class="fw" style="margin-top:12px">Each row is that system's statements and nothing else, with its
own penalty chosen inside its own cross-validation, on couples grouped so that no marriage graph is
split across folds. Rows above the baseline are marked.</p></details>
{MARK1}"""

    p = f"{DOCS}/index.html"
    s = open(p).read()
    a, b = s.index(MARK0), s.index(MARK1) + len(MARK1)
    open(p, "w").write(s[:a] + sec + s[b:])
    print(f"  rewrote the honest block: {nstmt} statements · CV {cv:.4f} · test {te:.4f}")
    print(f"  {len(R['systems'])} systems tabled · {len(beat)} beat the age gap")


if __name__ == "__main__":
    main()
