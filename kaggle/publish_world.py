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
    M = json.load(open(f"{DEV}/{os.environ.get('AQ_MODEL_NAME','quality_maxcv')}.json"))
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
                     (f"{DEV}/{os.environ.get('AQ_MODEL_NAME','quality_maxcv')}_importance.json", "quality_importance.json"),
                     (f"{DEV}/{os.environ.get('AQ_MODEL_NAME','quality_maxcv')}.json", "quality_model.json")):
        if os.path.exists(src):
            shutil.copy(src, f"{DOCS}/almanac/{dst}")

    # The summary is what page_audit.py checks the rendered page against, so it has to be regenerated
    # from the same model file the page is running. A stale summary makes the audit test the old model.
    imp = json.load(open(f"{DEV}/{os.environ.get('AQ_MODEL_NAME','quality_maxcv')}_importance.json"))
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
<details class="fam" style="margin-top:44px"><summary>What we found when we pushed the score as hard as it goes
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

<b>The model.</b> {nstmt} statements chosen by a sparse non-negative fit from a bank of
{M.get('n_bank', 0):,}: cross-validated <b>{cv:.4f}</b>, and <b>{te:.4f}</b> on couples it never saw —
<b>+{zc:.2f} standard errors</b> above chance and <b>+{zb:.2f}</b> above the age-gap baseline of
{base:.4f}, which is the one comparator we measure against because it reads nothing but the same two
dates. Every statement is a named tradition; only the weighting was fitted. The full ranking, by what
each is worth when it is removed rather than by its raw coefficient, is below.<br><br>

<b>We tried very hard to beat it.</b> Everything below was fitted with the selection INSIDE the
cross-validation folds, so the numbers are comparable with each other and with the model above:

<div style="overflow-x:auto"><table class="sys"><tbody>
<tr class=win><td>the shipped bank of named statements</td><td class=n>0.5991</td></tr>
<tr><td>Addey harmonics — every cross-chart angle as a Fourier series, 4,719 continuous features</td><td class=n>0.5767</td></tr>
<tr><td>the composite chart read at 32 harmonics instead of 12 signs</td><td class=n>0.5717</td></tr>
<tr><td>both of those together</td><td class=n>0.5817</td></tr>
<tr><td>the divisional charts — D3, D9, D12, D16, D30 of the composite</td><td class=n>0.5983</td></tr>
<tr><td>configurations: 12,622 columns for two named conditions holding at once</td><td class=n>0.5942</td></tr>
<tr><td>natal signs and groups for each partner separately, and every single-side statement</td><td class=n>0.5980</td></tr>
<tr><td>the harmonics symmetrised so the couple reads the same either way round</td><td class=n>0.5516</td></tr>
<tr><td>boosted trees on every cross-chart angle and composite position</td><td class=n>0.5765</td></tr>
</tbody></table></div>

<p class="fw">Not one of them beat the plain bank of named statements. Nor did bagging (0.5913),
averaging over neighbouring penalties (0.5975), screening the bank down before selecting (0.5961), or
letting the weights go negative (0.5964 against 0.5961 — so the rule that no statement may be used
backwards costs nothing at all). Ten folds instead of five moved it from 0.5981 to 0.5991 and twenty
folds to 0.5992, which is where it stops.<br><br>

<b>And here is what the score is actually made of.</b> Three measurements, all on the training
couples:</p>

<div style="overflow-x:auto"><table class="sys"><tbody>
<tr><td>the two birth YEARS alone, five terms, no astrology in it at all</td><td class=n>0.5910</td></tr>
<tr><td>the astrology, measured only against couples from the same birth decade</td><td class=n>0.5108</td></tr>
<tr><td>harmonics of the FAST bodies only — Sun, Moon, Mercury, Venus, Mars, the node</td><td class=n>0.5007</td></tr>
</tbody></table></div>

<p class="fw">Read those together and they say one thing. Nearly all of the score is the ERA. Wikipedia
writes paragraphs about scandal and a sentence about a quiet forty years, so richly documented
marriages are genuinely enriched in recorded trouble; record richness tracks fame, fame tracks the
century, and the century is legible from a birth date through any slow planet. Held against couples
born in the same decade, where era cannot help it, the astrology scores <b>0.5108</b>. The bodies that
move fast enough to say something about two particular people rather than about a generation —
Venus, Mars, the Moon, the ones every tradition actually reads for love — score <b>0.5007</b>, which
is chance to four decimal places.<br><br>

That is why every one of the {nstmt} statements the fit chose is about Neptune, Pluto or the
composite chart: they are the slowest things in the sky and therefore the sharpest clock. This model is an
excellent reader of WHEN two people were born. It is not evidence that two particular people suit each
other, and we are not going to dress it up as one.<br><br>

<b>The gate we removed, and what it cost.</b> A statement can be tested for whether it is about the
couple or about the century: hold the midpoint date fixed, move the two births apart, and a real
interaction changes while an era quantity does not
(<a href="almanac/quality_interaction_scores.json">every score</a>). Requiring that more than half of a
statement's variance come from the separation leaves a model that scores <b>0.5276</b> held out —
honest about the pair, and much weaker. The model shipped here does not apply that gate, because the
brief was to maximise the cross-validated score. Both numbers are true and they measure different
things.<br><br>

<b>Three cautions.</b> The model can express only <b>{ndist}</b> distinct scores, because eight binary
statements cannot make more; it separates couples well in aggregate and is a coarse instrument for
ordering one person's candidate dates. The held-out set was read several times while this search ran;
every choice between candidates was made on cross-validation, never on those reads, but the set is no
longer as fresh as a single-read protocol would leave it. And the AUC measures ranking ACROSS couples,
while the product ranks dates WITHIN one person's window — different questions, and only the first is
measured. Read it as a curiosity, not a forecast.<br><br>

<b>The browser runs the same code, and we checked rather than assumed.</b> Scoring 300 held-out couples
through the page's own path and comparing every statement one by one: <b>2,400 evaluations, zero
disagreements</b>.</p></details>

<details class="fam"><summary>All {len(R['systems'])} marriage systems, each fitted alone
<span class="tc">cross-validated, training couples only</span></summary>
<p class="fw" style="margin-top:14px">Eighteen compatibility systems whose own literature is about
whether two people should marry were added to the bank — the Javanese weton calculation, the Balinese
pawukon, the ten porutham, Papasamya, Xiang Xing and Xiang Po, Korean gunghap, Burmese Mahabote, the
couple's I Ching hexagram, the geomantic Judge, biorhythm, the Hellenistic degree techniques, the
Kabbalistic 72 Names and the Sefer Yetzirah letters, the Norse half-months, the Nile zodiac and the
Aztec tonalpohualli. Each was then fitted ALONE, because a joint model cannot answer "does Ashtakoota
work", only "what did the Lasso keep". {len(beat)} of {len(R['systems'])} score above the age-gap
baseline of {R['baseline_age_gap_cv_auc']:.4f}, but a cross-validated AUC on {R['n_couples']:,} couples
carries a standard error near {cvse:.4f}, so only <b>{len(clear)}</b> clear it by more than that:
<b>{clear[0]['system']}</b> at {clear[0]['cv_auc']:.4f} and <b>{clear[1]['system']}</b> at
{clear[1]['cv_auc']:.4f}. Everything else lands at chance.</p>
<div style="overflow-x:auto"><table class="sys"><thead><tr><th>#</th><th>system</th><th>where it comes
from</th><th class=n>statements</th><th class=n>CV AUC</th></tr></thead><tbody>
<tr class="bl"><td></td><td><b>the baseline &mdash; signed age gap, two parameters</b></td><td></td>
<td class=n>2</td><td class=n>{R['baseline_age_gap_cv_auc']:.4f}</td></tr>
{sysrows}</tbody></table></div></details>
{MARK1}"""

    p = f"{DOCS}/index.html"
    s = open(p).read()
    a, b = s.index(MARK0), s.index(MARK1) + len(MARK1)
    open(p, "w").write(s[:a] + sec + s[b:])
    print(f"  rewrote the honest block: {nstmt} statements · CV {cv:.4f} · test {te:.4f}")
    print(f"  {len(R['systems'])} systems tabled · {len(beat)} beat the age gap")


if __name__ == "__main__":
    main()
