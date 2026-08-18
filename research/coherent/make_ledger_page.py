import csv, json, math, os
rows = list(csv.DictReader(open("research/coherent/named_ranking.csv")))
meta = json.load(open("research/coherent/named_ranking_meta.json"))
NUMK = ("Life Path","Personal Year","Birthday number","Chaldean","pillar","Attitude","digit sum",
        "relationship number","birth day","birth month","compatibility group")
SLOW = ("Saturn","Uranus","Neptune","Pluto","Chiron")
def cat(n):
    if any(k in n for k in NUMK): return "numerology"
    if "(older) to" in n: return "synastry"
    if "own chart" in n: return "natal aspect"
    if "nakshatra" in n or "pada" in n: return "vedic"
    if "Moon phase" in n or "illuminated" in n: return "lunation"
    return "single body"
data = []
for r in rows:
    n = r["name"]
    data.append({"n": n, "e": r["explanation"], "t": round(float(r["train"]),4),
                 "h": round(float(r["held"]),4), "m": round(float(r["matched"]),4),
                 "f": r["flipped"] == "True", "c": cat(n),
                 "s": any(b in n for b in SLOW)})
GAP, NULLMAX, YEAR = meta["age_gap"], meta["expected_null_max"], 0.5258
mm = sorted(d["m"] for d in data)
med = mm[len(mm)//2]
open("/tmp/feature_ledger.html","w").write(f"""<title>Astrology Feature Ledger</title>
<style>
:root {{
  --ground:#FBF9F4; --panel:#FFFFFF; --line:#DED7C8; --line-soft:#EAE4D6;
  --ink:#171A22; --ink-2:#4A4F5C; --ink-3:#7C8291;
  --gold:#9A6B0E; --gold-bright:#E8B923; --blue:#1746DC; --null:#B8B0A0;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ground:#080D18; --panel:#0E1524; --line:#222C42; --line-soft:#18202F;
    --ink:#EEF0F5; --ink-2:#A6AEC0; --ink-3:#6D7689;
    --gold:#E8B923; --gold-bright:#F2CE55; --blue:#7B9BFF; --null:#4A5266;
  }}
}}
:root[data-theme="dark"] {{
  --ground:#080D18; --panel:#0E1524; --line:#222C42; --line-soft:#18202F;
  --ink:#EEF0F5; --ink-2:#A6AEC0; --ink-3:#6D7689;
  --gold:#E8B923; --gold-bright:#F2CE55; --blue:#7B9BFF; --null:#4A5266;
}}
:root[data-theme="light"] {{
  --ground:#FBF9F4; --panel:#FFFFFF; --line:#DED7C8; --line-soft:#EAE4D6;
  --ink:#171A22; --ink-2:#4A4F5C; --ink-3:#7C8291;
  --gold:#9A6B0E; --gold-bright:#E8B923; --blue:#1746DC; --null:#B8B0A0;
}}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--ground); color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:17px; line-height:1.6; -webkit-text-size-adjust:100% }}
.wrap {{ max-width:1180px; margin:0 auto; padding:clamp(24px,5vw,64px) clamp(16px,4vw,40px) 96px }}
header {{ border-bottom:1px solid var(--line); padding-bottom:28px; margin-bottom:36px }}
.eyebrow {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11.5px;
  letter-spacing:.14em; text-transform:uppercase; color:var(--ink-3); margin:0 0 14px }}
h1 {{ font-size:clamp(30px,5.2vw,46px); line-height:1.08; margin:0 0 16px; font-weight:600;
  letter-spacing:-.015em; text-wrap:balance }}
.lede {{ font-size:clamp(17px,2.1vw,20px); color:var(--ink-2); margin:0; max-width:62ch }}
h2 {{ font-size:22px; margin:44px 0 6px; font-weight:600; letter-spacing:-.01em }}
h2 + .sub {{ color:var(--ink-3); font-size:15px; margin:0 0 20px }}
p {{ max-width:68ch; color:var(--ink-2) }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(158px,1fr)); gap:1px;
  background:var(--line-soft); border:1px solid var(--line-soft); margin:32px 0 8px }}
.tile {{ background:var(--panel); padding:16px 18px }}
.tile .k {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10.5px;
  letter-spacing:.1em; text-transform:uppercase; color:var(--ink-3); margin-bottom:7px }}
.tile .v {{ font-size:27px; font-variant-numeric:tabular-nums; letter-spacing:-.02em; line-height:1 }}
.tile .n {{ font-size:12.5px; color:var(--ink-3); margin-top:6px; line-height:1.4 }}
.hi {{ color:var(--gold) }}
figure {{ margin:34px 0; padding:22px 22px 12px; background:var(--panel); border:1px solid var(--line-soft) }}
figcaption {{ font-size:13.5px; color:var(--ink-3); margin-top:12px; max-width:78ch }}
svg {{ display:block; width:100%; height:auto; overflow:visible }}
.controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:26px 0 14px }}
input[type=search], select {{ font:inherit; font-size:15px; padding:8px 12px; color:var(--ink);
  background:var(--panel); border:1px solid var(--line); border-radius:0 }}
input[type=search] {{ flex:1 1 250px; min-width:0 }}
:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px }}
.count {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px; color:var(--ink-3) }}
.tblwrap {{ overflow-x:auto; border:1px solid var(--line-soft); background:var(--panel) }}
table {{ border-collapse:collapse; width:100%; font-size:14.5px; min-width:820px }}
thead th {{ position:sticky; top:0; background:var(--panel); text-align:left; font-weight:600;
  font-size:11.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--ink-3);
  padding:11px 12px; border-bottom:1px solid var(--line); cursor:pointer; white-space:nowrap;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace }}
thead th:hover {{ color:var(--ink) }}
thead th.on {{ color:var(--gold) }}
tbody td {{ padding:10px 12px; border-bottom:1px solid var(--line-soft); vertical-align:top }}
tbody tr:last-child td {{ border-bottom:0 }}
.num {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-variant-numeric:tabular-nums;
  text-align:right; white-space:nowrap }}
.fname {{ font-weight:600; letter-spacing:-.005em }}
.fexp {{ color:var(--ink-3); font-size:13px; line-height:1.5; margin-top:3px; max-width:70ch }}
.chip {{ display:inline-block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10px;
  letter-spacing:.07em; text-transform:uppercase; padding:2px 6px; border:1px solid var(--line);
  color:var(--ink-3); margin-right:6px }}
.flip {{ color:var(--null); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px }}
.above {{ color:var(--gold); font-weight:600 }}
.nullband {{ color:var(--null) }}
footer {{ margin-top:56px; padding-top:22px; border-top:1px solid var(--line); font-size:13.5px;
  color:var(--ink-3) }}
code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.88em;
  background:var(--line-soft); padding:1px 5px }}
</style>

<div class="wrap">
<header>
  <p class="eyebrow">ArtaMatch · held out on 13,250 couples born after 1900</p>
  <h1>667 astrology and numerology features, each with its own two-parameter&nbsp;AUC</h1>
  <p class="lede">Every feature named and explained, scored by a logistic on that feature alone.
  The median lands at 0.5001 and half of them reverse direction out of time.</p>
</header>

<div class="tiles">
  <div class="tile"><div class="k">age gap</div><div class="v hi">{GAP:.4f}</div>
    <div class="n">the one permitted non-astrology comparison</div></div>
  <div class="tile"><div class="k">best gap-matched</div><div class="v">{max(d['m'] for d in data):.4f}</div>
    <div class="n">Chiron longitude, cos — younger partner</div></div>
  <div class="tile"><div class="k">birth year alone</div><div class="v">{YEAR:.4f}</div>
    <div class="n">same control — what the era is worth</div></div>
  <div class="tile"><div class="k">median feature</div><div class="v nullband">{med:.4f}</div>
    <div class="n">gap-matched, over all 667</div></div>
  <div class="tile"><div class="k">reversed out of time</div><div class="v">51%</div>
    <div class="n">{meta['n_flipped']} of 667 flipped sign</div></div>
</div>

<h2>How to read the three columns</h2>
<p class="sub">Each row is one feature and one two-parameter logistic.</p>
<p><strong>Train</strong> is the feature's AUC on 25,000 training couples born 1600–1900, and it is the only
column used to order anything. <strong>Held out</strong> is the same feature on 13,250 couples born after 1900,
with <code>b₁</code>'s sign taken from the training half — never re-chosen using the answers.
<strong>Gap-matched</strong> is the held-out AUC computed <em>within</em> one-year age-gap bands.</p>
<p>That third column is the one that matters. The age gap alone scores {GAP:.4f}, so a feature that merely
encodes the difference between two dates scores well while saying nothing astrological. A slow planet's
separation between two charts is exactly such an encoding: Saturn moves 12.2° a year, so
Saturn-to-Saturn separation <em>is</em> the age gap, wrapped — it tops the raw table at 0.5700 and falls to
0.4942 once the gap is held flat.</p>
<p>Because 667 features were searched, the largest of that many pure-null draws is expected near
<strong>{NULLMAX:.4f}</strong>. Read the top of the table against that, not against 0.50. Six features clear it —
and all six are Saturn-or-slower longitudes, while the <em>birth year itself</em> scores {YEAR:.4f} under the
same control. They are the era wearing a planet's name.</p>

<figure>
  <svg id="hist" viewBox="0 0 900 250" role="img" aria-label="Distribution of gap-matched AUC across 667 features, centred on 0.50"></svg>
  <figcaption>Gap-matched AUC across all 667 features. The distribution is centred on 0.5001 — the shape of a
  null. Markers: 0.50 chance, the birth year at {YEAR:.4f}, the {NULLMAX:.4f} multiple-testing threshold, and
  the age gap at {GAP:.4f}.</figcaption>
</figure>

<h2>The ledger</h2>
<p class="sub">Sort by any column. Search matches names and explanations.</p>
<div class="controls">
  <input type="search" id="q" placeholder="Search 667 features and their explanations…" aria-label="Search features">
  <select id="cat" aria-label="Filter by category"><option value="">every category</option></select>
  <select id="only" aria-label="Filter by result">
    <option value="">all features</option>
    <option value="above">clears the null threshold</option>
    <option value="stable">held its direction out of time</option>
    <option value="slow">Saturn or slower</option>
    <option value="fast">faster than Saturn</option>
  </select>
  <span class="count" id="count"></span>
</div>
<div class="tblwrap"><table>
<thead><tr>
  <th data-k="n">Feature</th><th data-k="t" class="num">Train</th>
  <th data-k="h" class="num">Held out</th><th data-k="m" class="num on">Gap-matched</th>
</tr></thead><tbody id="body"></tbody></table></div>

<footer>Features defined in <code>research/coherent/named_features.py</code>, scored by
<code>rank_named.py</code>. Training half 25,000 genuine pairs (rows where an absent partner inherits the
other's instant are excluded — 41% of the raw training half, 0.1% of the held-out half). The gap-matched
estimator is validated in both directions: it removes the age gap (0.6046 → 0.4982) and preserves a planted
gap-independent signal (0.5958 → 0.5961). No birth times, so no houses, Ascendant or MC; no names, so no
Expression or Soul Urge numerology.</footer>
</div>

<script>
const DATA = {json.dumps(data, separators=(",",":"))};
const NULLMAX = {NULLMAX:.4f}, YEAR = {YEAR:.4f}, GAP = {GAP:.4f};
const body=document.getElementById('body'), q=document.getElementById('q'),
      cat=document.getElementById('cat'), only=document.getElementById('only'),
      count=document.getElementById('count');
[...new Set(DATA.map(d=>d.c))].sort().forEach(c=>{{
  const o=document.createElement('option'); o.value=c; o.textContent=c; cat.appendChild(o); }});
let key='m', dir=-1;
function fmt(v,hi){{ return `<span class="${{hi?'above':(Math.abs(v-0.5)<0.01?'nullband':'')}}">${{v.toFixed(4)}}</span>`; }}
function render(){{
  const t=q.value.trim().toLowerCase(), c=cat.value, o=only.value;
  let rs=DATA.filter(d=>{{
    if(c && d.c!==c) return false;
    if(o==='above' && d.m<=NULLMAX) return false;
    if(o==='stable' && d.f) return false;
    if(o==='slow' && !d.s) return false;
    if(o==='fast' && d.s) return false;
    if(t && !(d.n.toLowerCase().includes(t) || d.e.toLowerCase().includes(t))) return false;
    return true; }});
  rs.sort((a,b)=> key==='n' ? dir*a.n.localeCompare(b.n) : dir*(a[key]-b[key]));
  count.textContent = rs.length===DATA.length ? `${{rs.length}} features` : `${{rs.length}} of ${{DATA.length}}`;
  body.innerHTML = rs.map(d=>`<tr><td><div class="fname">${{d.n}}</div>
    <div class="fexp"><span class="chip">${{d.c}}</span>${{d.e}}${{d.f?' <span class="flip">· reversed out of time</span>':''}}</div></td>
    <td class="num">${{d.t.toFixed(4)}}</td><td class="num">${{fmt(d.h,false)}}</td>
    <td class="num">${{fmt(d.m, d.m>NULLMAX)}}</td></tr>`).join('');
}}
document.querySelectorAll('thead th').forEach(th=>th.addEventListener('click',()=>{{
  const k=th.dataset.k; dir = (k===key) ? -dir : (k==='n'?1:-1); key=k;
  document.querySelectorAll('thead th').forEach(x=>x.classList.toggle('on', x===th)); render(); }}));
[q,cat,only].forEach(el=>el.addEventListener('input',render));
render();

// histogram of gap-matched AUC
(function(){{
  const svg=document.getElementById('hist'), W=900,H=250, L=44,R=16,T=14,B=42;
  const lo=0.45, hi=0.58, nb=52, bins=new Array(nb).fill(0);
  DATA.forEach(d=>{{ let i=Math.floor((d.m-lo)/(hi-lo)*nb); if(i>=0&&i<nb) bins[i]++; }});
  const mx=Math.max(...bins), x=v=>L+(v-lo)/(hi-lo)*(W-L-R), y=v=>H-B-(v/mx)*(H-T-B);
  let s='';
  for(let g=0; g<=mx; g+=Math.ceil(mx/4)) s+=`<line x1="${{L}}" x2="${{W-R}}" y1="${{y(g)}}" y2="${{y(g)}}" stroke="var(--line-soft)" stroke-width="1"/>
    <text x="${{L-8}}" y="${{y(g)+4}}" text-anchor="end" font-size="11" fill="var(--ink-3)" font-family="ui-monospace,monospace">${{g}}</text>`;
  const bw=(W-L-R)/nb;
  bins.forEach((v,i)=>{{ if(!v) return;
    const c = (lo+(i+0.5)*(hi-lo)/nb) > NULLMAX ? 'var(--gold)' : 'var(--null)';
    s+=`<rect x="${{x(lo+i*(hi-lo)/nb)+1}}" y="${{y(v)}}" width="${{bw-2}}" height="${{H-B-y(v)}}" fill="${{c}}"/>`; }});
  [[0.50,'0.50 chance'],[YEAR,'birth year'],[NULLMAX,'null threshold'],[GAP,'age gap']].forEach(([v,lab],i)=>{{
    s+=`<line x1="${{x(v)}}" x2="${{x(v)}}" y1="${{T}}" y2="${{H-B}}" stroke="var(--blue)" stroke-width="1.5" stroke-dasharray="${{i?'4 3':'0'}}"/>
      <text x="${{x(v)}}" y="${{H-B+16}}" text-anchor="middle" font-size="10.5" fill="var(--blue)" font-family="ui-monospace,monospace">${{lab}}</text>
      <text x="${{x(v)}}" y="${{H-B+29}}" text-anchor="middle" font-size="10.5" fill="var(--ink-3)" font-family="ui-monospace,monospace">${{v.toFixed(3)}}</text>`; }});
  svg.innerHTML=s;
}})();
</script>""")
print("  wrote /tmp/feature_ledger.html", os.path.getsize("/tmp/feature_ledger.html")//1024, "KB")
