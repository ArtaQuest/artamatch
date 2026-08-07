/**
 * interference28.mjs — compatibility as positive interference integrated over 28 years of marriage.
 *
 *     S  =  (1/T) · INTEGRAL from t_m to t_m + 28y  of  max( 0, Re( z_A(t) · conj(z_B(t)) ) )  dt
 *
 *     z_P(t)  =  b  +  SUM_j  u_j · exp( i · w_j · (t - t_P) )
 *
 * T = 28 years, the median marriage duration in this corpus. It is a GLOBAL CONSTANT, identical for
 * every couple — not each couple's own duration, which would put the answer inside the feature.
 *
 * ── Why this can be computed at all ─────────────────────────────────────────────────────────────
 *
 * The first attempt tried to fit b and u_j end-to-end through the integral, which needs 48 loss
 * evaluations per optimiser step, each one an integral over every couple: hours of work for a model
 * whose long-window limit is already known in closed form. Two things make it tractable instead:
 *
 *   ONE PASS IS CHEAP. Evaluating S for all 9,574 couples on a 7-day grid over 28 years is about 280
 *   million operations — two seconds. It is only the FITTING that was expensive.
 *
 *   THE AMPLITUDES ARE ALREADY FITTED. phasor2/phasor3 learned u_j from the same couples. So S is
 *   computed with those amplitudes and only the two readout coefficients are fitted here — which is a
 *   logistic regression on one feature and takes no time at all.
 *
 * That answers the actual question — does the 28-year positive-interference score predict divorce? —
 * without pretending to a joint optimum the earlier attempt never reached either.
 *
 * ── The grid ────────────────────────────────────────────────────────────────────────────────────
 *
 * 7-day steps: 1,460 samples over 28 years. The fastest component is the Moon at 27.3 days, so 7 days
 * is just under four samples per cycle — adequate for an integral, and the coarser 30-day variant is
 * run alongside to show the answer does not depend on it.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/interference28.mjs ./research/data-divorce
 */
import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { julianDay } = await import(EPH);
const PLANETS = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"];
const PERIOD = { Sun:365.256363, Moon:27.321661, Mercury:87.9691, Venus:224.700796, Mars:686.9800,
  Jupiter:4332.589, Saturn:10759.22, Uranus:30688.5, Neptune:60182.0, Pluto:90560.0 };
const W = PLANETS.map(p => 2*Math.PI/PERIOD[p]);
const NB = PLANETS.length, YR = 365.2425;
const DIR = process.argv[2] ?? "./research/data-divorce";
let SEED = 20260807;
const rnd = () => { SEED^=SEED<<13; SEED^=SEED>>>17; SEED^=SEED<<5; SEED|=0; return (SEED>>>0)/4294967296; };
const shuffle = a => { const b=[...a]; for(let i=b.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[b[i],b[j]]=[b[j],b[i]];} return b; };

const parseDate = iso => { const m=/^(-?\d{3,4})-(\d{2})-(\d{2})$/.exec(iso??""); if(!m) return null;
  const y=+m[1],mo=+m[2],d=+m[3]; return mo>=1&&mo<=12&&d>=1&&d<=31?{y,m:mo,d}:null; };
const isJan1 = s => !!s && s.endsWith("-01-01");
const raw = JSON.parse(readFileSync(`${DIR}/balanced-all-precisions.json`,"utf8"));
const rows = [];
for (const r of raw) {
  const A=parseDate(r.aDob), B=parseDate(r.bDob), M=parseDate(r.start);
  if(!A||!B||!M) continue;
  if(isJan1(r.aDob)||isJan1(r.bDob)||isJan1(r.start)) continue;
  let ja=julianDay(A.y,A.m,A.d,12), jb=julianDay(B.y,B.m,B.d,12), ya=A.y, yb=B.y, pa=r.a, pb=r.b;
  if(jb<ja){[ja,jb]=[jb,ja];[pa,pb]=[pb,pa];[ya,yb]=[yb,ya];}
  const jm=julianDay(M.y,M.m,M.d,12);
  const ageA=(jm-ja)/YR, ageB=(jm-jb)/YR;
  if(ageA<12||ageB<12||ageA>90) continue;
  rows.push({a:pa,b:pb,y:r.y,tA:ja,tB:jb,tM:jm,year:(ya+yb)/2,wedYear:M.y,gap:(jb-ja)/YR,ageM:(ageA+ageB)/2});
}
SEED=20260807;
const pos=rows.filter(r=>r.y===1), neg=rows.filter(r=>r.y===0), K=Math.min(pos.length,neg.length);
const data=shuffle([...shuffle(pos).slice(0,K),...shuffle(neg).slice(0,K)]);
const side=new Map(); SEED=20260807;
for(const r of data){ let s=side.get(r.a)??side.get(r.b); if(s===undefined) s=rnd()<0.8?"train":"test";
  side.set(r.a,s); side.set(r.b,s); r.side=s; }
const TR=data.filter(r=>r.side==="train"), TE=data.filter(r=>r.side==="test");

console.log(`\nPOSITIVE INTERFERENCE INTEGRATED OVER 28 YEARS OF MARRIAGE`);
console.log(`  ${data.length.toLocaleString()} couples, ${K.toLocaleString()} of each class — coin 50.00%`);
console.log(`  ${TR.length.toLocaleString()} train / ${TE.length.toLocaleString()} test, split by person`);
console.log(`  window T = 28 years, the median marriage duration — a global constant, not each couple's own`);

/** The score: mean positive interference over [t_m, t_m + T]. */
function scoreAll(u, b, T, step) {
  const n = Math.floor(T/step)+1;
  const out = new Float64Array(data.length);
  for (let i=0;i<data.length;i++){
    const r=data[i]; let acc=0;
    for(let k=0;k<n;k++){
      const t=r.tM+k*step;
      let ar=b[0], ai=b[1], br=b[0], bi=b[1];
      for(let j=0;j<NB;j++){
        const pa=W[j]*(t-r.tA), pb=W[j]*(t-r.tB);
        const ux=u[2*j], uy=u[2*j+1];
        const ca=Math.cos(pa), sa=Math.sin(pa), cb=Math.cos(pb), sb=Math.sin(pb);
        ar+=ux*ca-uy*sa; ai+=ux*sa+uy*ca;
        br+=ux*cb-uy*sb; bi+=ux*sb+uy*cb;
      }
      const v=ar*br+ai*bi;
      if(v>0) acc+=v;
    }
    out[i]=acc/n;
  }
  return out;
}

const sigma=z=>1/(1+Math.exp(-Math.max(-30,Math.min(30,z))));
/** One-feature logistic regression, fitted on train, scored on test. */
function evalScore(S,label){
  const iTR=[],iTE=[];
  data.forEach((r,i)=>(r.side==="train"?iTR:iTE).push(i));
  const m=iTR.reduce((s,i)=>s+S[i],0)/iTR.length;
  const sd=Math.sqrt(iTR.reduce((s,i)=>s+(S[i]-m)**2,0)/iTR.length)||1;
  let c0=0,c1=0;
  for(let it=0;it<200;it++){
    let g0=0,g1=0,h0=0,h1=0;
    for(const i of iTR){ const x=(S[i]-m)/sd, p=sigma(c0+c1*x), w=Math.max(p*(1-p),1e-6);
      g0+=data[i].y-p; g1+=(data[i].y-p)*x; h0+=w; h1+=w*x*x; }
    c0+=g0/(h0+1); c1+=g1/(h1+1);
  }
  const acc=set=>set.reduce((n,i)=>n+((sigma(c0+c1*(S[i]-m)/sd)>=0.5?1:0)===data[i].y?1:0),0)/set.length;
  const corr=(u,v)=>{const n=u.length,mu=u.reduce((s,x)=>s+x,0)/n,mv=v.reduce((s,x)=>s+x,0)/n;
    let c=0,du=0,dv=0;for(let i=0;i<n;i++){c+=(u[i]-mu)*(v[i]-mv);du+=(u[i]-mu)**2;dv+=(v[i]-mv)**2;}return c/Math.sqrt(du*dv);};
  const all=data.map((_,i)=>i);
  console.log(`  ${label.padEnd(46)} ${(100*acc(iTR)).toFixed(2)}%   ${(100*acc(iTE)).toFixed(2)}%   r=${corr(all.map(i=>S[i]),all.map(i=>data[i].y)).toFixed(4)}`);
  return {S,accTE:acc(iTE)};
}

// The amplitudes the phasor fit converged on: Pluto and Neptune dominant, everything else small.
// Used as given rather than refitted through the integral, for the reason in the header.
const uPhasor = new Float64Array(2*NB);
const AMP = { Pluto:0.7717, Neptune:0.5375, Uranus:0.2030, Mercury:0.0736, Sun:0.0585,
  Saturn:0.0270, Mars:0.0222, Venus:0.0173, Moon:0.0097, Jupiter:0.0051 };
const PH = { Pluto:134.4, Neptune:112.0, Uranus:223.1, Mercury:79.6, Sun:256.7,
  Saturn:6.8, Mars:19.6, Venus:319.1, Moon:17.9, Jupiter:5.3 };
PLANETS.forEach((p,j)=>{ const a=AMP[p], ph=PH[p]*Math.PI/180;
  uPhasor[2*j]=a*Math.cos(ph); uPhasor[2*j+1]=a*Math.sin(ph); });
const bPhasor=[-0.0807,0.3636];

console.log(`\n  score                                          TRAIN     TEST     corr with divorce`);
const T28 = 28*YR;
evalScore(scoreAll(uPhasor,bPhasor,T28,7), "28y positive interference, 7-day grid");
evalScore(scoreAll(uPhasor,bPhasor,T28,30), "28y positive interference, 30-day grid");
// Equal amplitudes: no fitted weighting at all, the plainest possible version.
const uFlat=new Float64Array(2*NB); for(let j=0;j<NB;j++) uFlat[2*j]=1;
evalScore(scoreAll(uFlat,[0,0],T28,7), "28y, EQUAL amplitudes, no fitting at all");
// Inner planets only: nothing that can read the calendar.
const uInner=new Float64Array(2*NB); for(let j=0;j<7;j++){uInner[2*j]=uPhasor[2*j];uInner[2*j+1]=uPhasor[2*j+1];}
evalScore(scoreAll(uInner,bPhasor,T28,7), "28y, classical 7 only (no calendar)");
// The signed integral, for contrast: no rectifier, so provably diagonal synastry in the long run.
{
  const n=Math.floor(T28/7)+1, out=new Float64Array(data.length);
  for(let i=0;i<data.length;i++){ const r=data[i]; let acc=0;
    for(let k=0;k<n;k++){ const t=r.tM+k*7;
      let ar=bPhasor[0],ai=bPhasor[1],br=bPhasor[0],bi=bPhasor[1];
      for(let j=0;j<NB;j++){ const pa=W[j]*(t-r.tA),pb=W[j]*(t-r.tB);
        const ux=uPhasor[2*j],uy=uPhasor[2*j+1];
        ar+=ux*Math.cos(pa)-uy*Math.sin(pa); ai+=ux*Math.sin(pa)+uy*Math.cos(pa);
        br+=ux*Math.cos(pb)-uy*Math.sin(pb); bi+=ux*Math.sin(pb)+uy*Math.cos(pb); }
      acc+=ar*br+ai*bi; }
    out[i]=acc/n; }
  evalScore(out, "28y SIGNED integral (no rectifier)");
}
console.log(`  ${"the coin".padEnd(46)}   —        50.00%`);

// What does the score track?
{
  const S=scoreAll(uPhasor,bPhasor,T28,7);
  const corr=(u,v)=>{const n=u.length,mu=u.reduce((s,x)=>s+x,0)/n,mv=v.reduce((s,x)=>s+x,0)/n;
    let c=0,du=0,dv=0;for(let i=0;i<n;i++){c+=(u[i]-mu)*(v[i]-mv);du+=(u[i]-mu)**2;dv+=(v[i]-mv)**2;}return c/Math.sqrt(du*dv);};
  const arr=Array.from(S);
  console.log(`\n  WHAT THE 28-YEAR SCORE TRACKS`);
  console.log(`    vs age gap          : r = ${corr(arr,data.map(r=>r.gap)).toFixed(4)}`);
  console.log(`    vs mean birth year  : r = ${corr(arr,data.map(r=>r.year)).toFixed(4)}`);
  console.log(`    vs wedding year     : r = ${corr(arr,data.map(r=>r.wedYear)).toFixed(4)}`);
  console.log(`    vs age at marriage  : r = ${corr(arr,data.map(r=>r.ageM)).toFixed(4)}`);
  console.log(`    vs DIVORCE          : r = ${corr(arr,data.map(r=>r.y)).toFixed(4)}`);
}
