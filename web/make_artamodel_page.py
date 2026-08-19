"""make_artamodel_page.py — write web/artamodel.html (the prod explanation of ArtaModel, term by term) from the
deployed model's JSON. ship.py copies it into docs/. Usage: python web/make_artamodel_page.py"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
d = json.load(open(os.path.join(REPO, "research/sidereal/artamodel_deployed.json")))
lbp = os.path.join(REPO, "research/sidereal/artamodel_leaderboard.json")
lb = json.load(open(lbp)) if os.path.exists(lbp) else {"inner_auc": float("nan"), "stages": []}
used = d["explanation"]["used"]; unused = d["explanation"]["unused"]
TT = {"a": ("a·e<sup>i(θm−θd)</sup>", "mom's longitude minus dad's — the synastry angle"),
      "m": ("m·e<sup>i(θt−θm)</sup>", "the wedding-day longitude minus mom's — the wedding transiting mom"),
      "d": ("d·e<sup>i(θt−θd)</sup>", "the wedding-day longitude minus dad's — the wedding transiting dad"),
      "mn": ("mn·e<sup>iθm</sup>", "mom's own natal longitude"), "dn": ("dn·e<sup>iθd</sup>", "dad's own natal longitude"),
      "tn": ("tn·e<sup>iθt</sup>", "the wedding-day longitude itself")}
by_term = {}
for lab in unused:
    t, b = lab.split("_", 1); by_term.setdefault(t, []).append(b)
rows = "".join(f"<tr><td><code>{r['phasor']}</code></td><td>{r['body']}</td><td>{TT[r['term']][0]}</td><td class=num>{r['stages']}</td>"
               f"<td class=num>{r['contribution']:.3f}</td><td class=num>{r['phase_deg']:.0f}°</td><td class=meaning>{html.escape(r['meaning'])}</td></tr>" for r in used)
terms_html = "".join(f"<tr><td><b>{t}</b></td><td>{TT[t][0]}</td><td>{TT[t][1]}</td><td class=num>{14-len(by_term.get(t, []))}/14</td></tr>" for t in d["terms"])
page = f"""<title>ArtaModel</title>
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
<p class=eyebrow>ArtaMatch · the deployed model · fitted on {d['n_rows']:,} marriages</p>
<h1>ArtaModel, term by term</h1>
<p class=lede>A sidereal phase model of a marriage: his birth and birthplace, hers, and the wedding date, one probability out. Every term is written out below, with the weight the fitted model gave it — and with what the model turns out to be reading.</p>
<h2>The formula</h2>
<pre>y = | b + Σᵢ  aᵢ ·e^{{i(θmᵢ − θdᵢ)}}     mom's longitude minus dad's            (synastry)
             + mᵢ ·e^{{i(θtᵢ − θmᵢ)}}     the wedding sky minus mom's chart      (transit to mom)
             + dᵢ ·e^{{i(θtᵢ − θdᵢ)}}     the wedding sky minus dad's chart      (transit to dad)
             + mnᵢ·e^{{i θmᵢ}}            mom's own natal longitude
             + dnᵢ·e^{{i θdᵢ}}            dad's own natal longitude
             + tnᵢ·e^{{i θtᵢ}} |²         the wedding sky itself</pre>
<p>θ are <b>sidereal longitudes</b> (Lahiri, through Kerykeion and the Swiss Ephemeris) of fourteen bodies — Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Rāhu, Ketu, Chiron, Lilith. Nobody's birth <em>time</em> is recorded, so every birth is cast at <b>09:00 local time at the birthplace</b>; the wedding at 12:00 UT. <b>A term exists only when both of its phases exist</b> — an unknown wedding day drops the wedding terms, an unknown birth drops that partner's terms, and a missing phase contributes exactly zero.</p>
<h2>The six terms</h2><div class=tblwrap><table><thead><tr><th>term</th><th>phasor</th><th>meaning</th><th>bodies the deployed model uses</th></tr></thead><tbody>{terms_html}</tbody></table></div>
<h2>What the fitted model chose</h2>
<p>The deployed model is gradient boosting over <b>split single-sum fields</b>: each stage is one field |b + w·e<sup>iφ</sup>|² on <b>one</b> phasor, chosen at that stage as the phasor that best explains the current residual — so all 84 phasors of all six terms compete every time — and added to the logit. Fitted on all the data, {d['n_rows']:,} couples with both natal charts, for {len(d['stages'])} stages. Of the 84 phasors offered it chose <b>{len(used)}</b>:</p>
<div class=tblwrap><table><thead><tr><th>phasor</th><th>body</th><th>term</th><th>stages</th><th>swing in the logit</th><th>peak at φ</th><th>meaning</th></tr></thead><tbody>{rows}</tbody></table></div>
<p><b>Read plainly:</b> <code>a_uranus</code> is the age gap between the two births measured by Uranus (4.3° a year); <code>d_pluto</code>, <code>d_neptune</code>, <code>d_uranus</code> are the groom's age at the wedding measured by Pluto, Neptune and Uranus; <code>m_pluto</code> and <code>m_saturn</code> are the bride's. Never chosen at any stage: any natal phase (mn, dn), any wedding-sky phase (tn), or any of the fast bodies.</p>
<h2>What it scores — honestly</h2>
<div class=tiles>
<div class=tile><div class=k>train-only fit, inner temporal split</div><div class=v>{lb['inner_auc']:.4f}</div><div class=n>AUC; held out on couples born after 1900 ≈ 0.62–0.64</div></div>
<div class=tile><div class=k>the plain columns</div><div class=v>0.62–0.64</div><div class=n>two ages at the wedding, the gap, the start year</div></div>
<div class=tile><div class=k>ages held flat</div><div class=v class=hi>≈ 0.50</div><div class=n>AUC within 3-year cells of (his age, her age)</div></div>
<div class=tile><div class=k>Uranus alone</div><div class=v>0.6419</div><div class=n>vs the Sun alone 0.4728</div></div>
</div>
<p>Every point of ArtaModel's held-out AUC is the two partners' ages at the wedding and the gap between their births, read through the outer planets as clocks. It is exactly invariant to the ayanāṁśa (a constant offset cancels in a phase difference), to the birth hour and to the birthplace; Uranus alone equals the whole model; and it adds nothing to a plain model of the ages. We say so because we measured it, from every angle, on fixed populations — the study is <a href="https://huggingface.co/artaquest/artamodel/blob/main/ARTAMODEL.md">ARTAMODEL.md</a>.</p>
<h2>Use it</h2>
<p>The deployed weights, the scorer (<code>predict(dob_dad, lat, lon, dob_mom, lat, lon, wedding)</code> → probability + stage-by-stage account), the code and the study: <a href="https://huggingface.co/artaquest/artamodel">huggingface.co/artaquest/artamodel</a>. The data: <a href="https://www.kaggle.com/datasets/artaquest-foundation/artamatch-sidereal">artamatch-sidereal</a>; the competition: <a href="https://www.kaggle.com/competitions/artamatch-sidereal">artamatch-sidereal</a>. CC0.</p>
</div>"""
open(os.path.join(HERE, "artamodel.html"), "w").write(page)
print(f"  web/artamodel.html written ({len(page):,} chars, {len(used)} used phasors)")
