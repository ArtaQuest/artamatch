"""make_artamodel_page.py — write web/artamodel.html (the prod explanation of ArtaModel, term by term) from the
deployed model's JSON. ship.py copies it into docs/. Usage: python web/make_artamodel_page.py"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
d = json.load(open(os.path.join(REPO, "research/sidereal/artamodel_iv_deployed.json")))
R = json.load(open(os.path.join(REPO, "research/sidereal/artamodel_iv.json")))
used = d["explanation"]["used"]; unused = d["explanation"]["unused"]
TT = {"a": ("a·e<sup>i|θ1−θ2|</sup>", "the absolute synastry angle between the two natal charts — even under the swap"),
      "t1": ("t1·e<sup>i|θt−θ1|</sup>", "the wedding sky to partner 1's natal longitude"),
      "t2": ("t2·e<sup>i|θt−θ2|</sup>", "the wedding sky to partner 2's natal longitude"),
      "n1": ("n1·e<sup>iθ1</sup>", "partner 1's own natal longitude"), "n2": ("n2·e<sup>iθ2</sup>", "partner 2's own natal longitude"),
      "tn": ("tn·e<sup>iθt</sup>", "the wedding-day longitude itself")}
by_term = {}
for lab in unused:
    t, b = lab.split("_", 1); by_term.setdefault(t, []).append(b)
rows = "".join(f"<tr><td><code>{r['phasor']}</code></td><td>{r['body']}</td><td>{TT[r['term']][0]}</td><td class=num>{r['stages']}</td>"
               f"<td class=num>{r['contribution']:.3f}</td><td class=num>{r['phase_deg']:.0f}°</td><td class=meaning>{html.escape(r['meaning'])}</td></tr>" for r in used)
terms_html = "".join(f"<tr><td><b>{t}</b></td><td>{TT[t][0]}</td><td>{TT[t][1]}</td><td class=num>{14-len(by_term.get(t, []))}/14</td></tr>" for t in d["terms"])
page = f"""<title>ArtaModel IV</title>
<style>
:root{{--bg:#FBF9F4;--panel:#fff;--line:#DED7C8;--soft:#EAE4D6;--ink:#171A22;--ink2:#4A4F5C;--ink3:#7C8291;--gold:#9A6B0E;--blue:#1746DC}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#080D18;--panel:#0E1524;--line:#222C42;--soft:#18202F;--ink:#EEF0F5;--ink2:#A6AEC0;--ink3:#6D7689;--gold:#E8B923;--blue:#7B9BFF}}}}
:root[data-theme="dark"]{{--bg:#080D18;--panel:#0E1524;--line:#222C42;--soft:#18202F;--ink:#EEF0F5;--ink2:#A6AEC0;--ink3:#6D7689;--gold:#E8B923;--blue:#7B9BFF}}
:root[data-theme="light"]{{--bg:#FBF9F4;--panel:#fff;--line:#DED7C8;--soft:#EAE4D6;--ink:#171A22;--ink2:#4A4F5C;--ink3:#7C8291;--gold:#9A6B0E;--blue:#1746DC}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:clamp(24px,5vw,64px) clamp(16px,4vw,40px) 96px}}
.eyebrow{{font:11.5px ui-monospace,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);margin:0 0 14px}}
h1{{font-size:clamp(30px,5vw,46px);line-height:1.08;margin:0 0 14px;font-weight:600;letter-spacing:-.015em;text-wrap:balance}}h2{{font-size:22px;margin:44px 0 10px;font-weight:600}}
p{{max-width:70ch;color:var(--ink2)}} .lede{{font-size:20px;color:var(--ink2);max-width:62ch}}
pre{{background:var(--panel);border:1px solid var(--soft);padding:16px 18px;overflow-x:auto;font:14px/1.55 ui-monospace,Menlo,monospace;color:var(--ink)}}
.tblwrap{{overflow-x:auto;border:1px solid var(--soft);background:var(--panel);margin:14px 0}}table{{border-collapse:collapse;width:100%;font-size:14.5px;min-width:760px}}
th{{text-align:left;font:11.5px ui-monospace,Menlo,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);padding:10px 12px;border-bottom:1px solid var(--line)}}
td{{padding:9px 12px;border-bottom:1px solid var(--soft);vertical-align:top}}td.num{{font-family:ui-monospace,Menlo,monospace;text-align:right;white-space:nowrap}}td.meaning{{color:var(--ink3);font-size:13px}}
.hi{{color:var(--gold);font-weight:600}}a{{color:var(--blue)}}code{{font-family:ui-monospace,Menlo,monospace;font-size:.9em;background:var(--soft);padding:1px 5px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1px;background:var(--soft);border:1px solid var(--soft);margin:24px 0}}
.tile{{background:var(--panel);padding:16px 18px}}.tile .k{{font:10.5px ui-monospace,Menlo,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);margin-bottom:6px}}.tile .v{{font-size:26px;font-variant-numeric:tabular-nums}}.tile .n{{font-size:12.5px;color:var(--ink3);margin-top:4px}}
</style><div class=wrap>
<p class=eyebrow>ArtaMatch · the deployed model · fourth edition · genderless · fitted on {d['n_rows']:,} rows</p>
<h1>ArtaModel IV, term by term</h1>
<p class=lede>A genderless sidereal phase model of a long-term relationship: two births and birthplaces — in no order — and the date it began, one probability out. Every term is written out below, with the weight the fitted model gave it — and with what the model turns out to be reading.</p>
<h2>The formula</h2>
<pre>y = | b + Σᵢ  aᵢ ·e^{{i|θ1ᵢ − θ2ᵢ|}}     the absolute synastry angle          (even under the swap)
             + t1ᵢ·e^{{i|θtᵢ − θ1ᵢ|}}     the wedding sky to partner 1's chart
             + t2ᵢ·e^{{i|θtᵢ − θ2ᵢ|}}     the wedding sky to partner 2's chart
             + n1ᵢ·e^{{i θ1ᵢ}}            partner 1's own natal longitude
             + n2ᵢ·e^{{i θ2ᵢ}}            partner 2's own natal longitude
             + tnᵢ·e^{{i θtᵢ}} |²         the wedding sky itself</pre>
<p>θ are <b>sidereal longitudes</b> (Lahiri, through Kerykeion and the Swiss Ephemeris) of fourteen bodies — Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Rāhu, Ketu, Chiron, Lilith. <b>Genderless:</b> no sex is read; "partner 1" and "partner 2" are whichever order you give — every phase <em>difference</em> enters as its wrapped absolute value |Δθ| in [0°, 180°], so each term is an even function of the swap, the training data carries every pair in both orders, and the scorer averages the two orders so the answer is exactly the same either way. Every long-term relationship Wikidata records is in the data — marriages of every kind, unmarried partnerships, business and sporting partnerships. Nobody's birth <em>time</em> is recorded, so every birth is cast at <b>09:00 local time at the birthplace</b>; the start at 12:00 UT. <b>A term exists only when both of its phases exist</b> — an unknown start day drops the wedding-sky terms, an unknown birth drops that partner's terms, and a missing phase contributes exactly zero.</p>
<h2>The six terms</h2><div class=tblwrap><table><thead><tr><th>term</th><th>phasor</th><th>meaning</th><th>bodies the deployed model uses</th></tr></thead><tbody>{terms_html}</tbody></table></div>
<h2>What the fitted model chose</h2>
<p>The deployed model is gradient boosting over <b>split single-sum fields</b>: each stage is one field |b + w·e<sup>iφ</sup>|² on <b>one</b> phasor, chosen at that stage as the phasor that best explains the current residual — so all 84 phasors of all six terms compete every time — and added to the logit. Fitted on all the data, {d['n_rows']:,} rows with both natal charts (every pair in both orders), for {len(d['stages'])} stages. Of the 84 phasors offered it chose <b>{len(used)}</b>:</p>
<div class=tblwrap><table><thead><tr><th>phasor</th><th>body</th><th>term</th><th>stages</th><th>swing in the logit</th><th>peak at φ</th><th>meaning</th></tr></thead><tbody>{rows}</tbody></table></div>
<p><b>Read plainly:</b> <code>a_uranus</code> is the absolute gap between the two births measured by Uranus (4.3° a year); <code>t1_neptune</code> and <code>t2_neptune</code> are each partner's age at the start measured by Neptune (2.2° a year) — chosen as a pair, as a genderless model should. Never chosen at any stage: any natal phase (n1, n2), any wedding-sky phase (tn), or any of the fast bodies.</p>
<h2>What it scores — honestly</h2>
<div class=tiles>
<div class=tile><div class=k>ArtaModel IV, train-only fit, held out</div><div class=v>{R['artamodel']['held']:.4f}</div><div class=n>AUC on {R['n_test_pairs']:,} pairs born after 1900 (both orders); public board 0.6101</div></div>
<div class=tile><div class=k>the plain columns</div><div class=v>{R['plain']['held']:.4f}</div><div class=n>the two ages at the start, |gap|, the start year; public board 0.6000</div></div>
<div class=tile><div class=k>ages held flat</div><div class=v class=hi>{R['artamodel']['age_cell_matched']:.4f}</div><div class=n>AUC within 3-year cells of (older age, younger age)</div></div>
<div class=tile><div class=k>plain + ArtaModel IV</div><div class=v>{R['ensemble']['held']:.4f}</div><div class=n>equal-weight rank average; public board 0.6144</div></div>
</div>
<p>What ArtaModel IV reads is the two partners' ages at the start and the absolute gap between their births, through the outer planets as clocks — the same finding as every edition before it, now without a sex in the model: it is exactly invariant to the ayanāṁśa (a constant offset cancels in a phase difference), to the birth hour and to the birthplace, and its gain over the plain ages is small and mostly the ages read twice. The age-cell-matched figure is what is left once the two ages are held flat. We say so because we measured it — the study is <a href="https://huggingface.co/artaquest/artamodel/blob/main/ARTAMODEL.md">ARTAMODEL.md</a>.</p>
<h2>Use it</h2>
<p>The deployed weights, the scorer (<code>predict(dob_1, lat, lon, dob_2, lat, lon, start)</code> → probability + the stage-by-stage account of both orders; symmetric by construction), the code and the study: <a href="https://huggingface.co/artaquest/artamodel">huggingface.co/artaquest/artamodel</a>. The data: <a href="https://www.kaggle.com/datasets/artaquest-foundation/artamatch-genderless">artamatch-genderless</a>; the competition: <a href="https://www.kaggle.com/competitions/artamatch-genderless">artamatch-genderless</a>. CC0.</p>
</div>"""
open(os.path.join(HERE, "artamodel.html"), "w").write(page)
print(f"  web/artamodel.html written ({len(page):,} chars, {len(used)} used phasors)")
