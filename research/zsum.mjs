/**
 * zsum.mjs — two waves, superposed, integrated for 28 years of marriage.
 *
 *   z_1(t) = b1 + SUM_j a1_j exp( i ( theta_j(t) - P1_j ) )     P1_j = the older partner's natal phase
 *   z_2(t) = b2 + SUM_j a2_j exp( i ( theta_j(t) - P2_j ) )     P2_j = the younger partner's
 *   score  = (1/T) INTEGRAL_{t_m}^{t_m+28y} | z_1(t) + z_2(t) | dt
 *
 * The date of birth sets every phase; only the amplitudes are learned. 44 parameters. Rotation-invariant
 * by construction, because every phase is a DIFFERENCE of two longitudes and |.| ignores a global phase.
 *
 * Fitted on the closed-form L2 score (a quadratic form in the 44 parameters, using precomputed integral
 * coefficients), then the specified L1 score is evaluated with those amplitudes. T = 28 years is a global
 * constant, never each couple's own duration.
 */
import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);
const D2R=Math.PI/180;
const P=["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"];
const NB=P.length, YR=365.2425, T28=28*YR, STEP=14;
const DIR=process.argv[2] ?? "./research/data-divorce";
let SEED=20260807;
const rnd=()=>{SEED^=SEED<<13;SEED^=SEED>>>17;SEED^=SEED<<5;SEED|=0;return (SEED>>>0)/4294967296;};
const shuffle=a=>{const b=[...a];for(let i=b.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[b[i],b[j]]=[b[j],b[i]];}return b;};
const gauss=()=>Math.sqrt(-2*Math.log(rnd()+1e-12))*Math.cos(2*Math.PI*rnd());
const pd=iso=>{const m=/^(-?\d{3,4})-(\d{2})-(\d{2})$/.exec(iso??"");if(!m)return null;
  const y=+m[1],mo=+m[2],d=+m[3];return mo>=1&&mo<=12&&d>=1&&d<=31?{y,m:mo,d}:null;};
const j1=s=>!!s&&s.endsWith("-01-01");

const raw=JSON.parse(readFileSync(`${DIR}/balanced-all-precisions.json`,"utf8"));
const rows=[];
for(const r of raw){
  const A=pd(r.aDob),B=pd(r.bDob),M=pd(r.start);
  if(!A||!B||!M||j1(r.aDob)||j1(r.bDob)||j1(r.start)) continue;
  let ja=julianDay(A.y,A.m,A.d,12), jb=julianDay(B.y,B.m,B.d,12), ya=A.y, yb=B.y, pa=r.a, pb=r.b;
  if(jb<ja){[ja,jb]=[jb,ja];[pa,pb]=[pb,pa];[ya,yb]=[yb,ya];}
  const jm=julianDay(M.y,M.m,M.d,12);
  const ag1=(jm-ja)/YR, ag2=(jm-jb)/YR;
  if(ag1<12||ag2<12||ag1>90) continue;
  rows.push({a:pa,b:pb,y:r.y,t1:ja,t2:jb,tM:jm,year:(ya+yb)/2,wedYear:M.y,gap:(jb-ja)/YR,ageM:(ag1+ag2)/2});
}
SEED=20260807;
const pos=rows.filter(r=>r.y===1), neg=rows.filter(r=>r.y===0), K=Math.min(pos.length,neg.length);
const data=shuffle([...shuffle(pos).slice(0,K),...shuffle(neg).slice(0,K)]);
const side=new Map(); SEED=20260807;
for(const r of data){let s=side.get(r.a)??side.get(r.b);
  if(s===undefined){const u=rnd();s=u<0.6?"train":u<0.8?"val":"test";}
  side.set(r.a,s);side.set(r.b,s);r.side=s;}
const TR=data.filter(r=>r.side==="train"),VA=data.filter(r=>r.side==="val"),TE=data.filter(r=>r.side==="test");
console.log(`\nz_sum = z_1 + z_2,  score = mean |z_sum| over 28 years from the wedding`);
console.log(`  ${data.length.toLocaleString()} couples, ${K.toLocaleString()} per class — coin 50.00%`);
console.log(`  ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} val · ${TE.length.toLocaleString()} test, split by person`);

// Per couple: the transiting sky on the grid, and both partners' natal phases (as conjugates).
const NG=Math.floor(T28/STEP)+1;
console.log(`  grid: ${NG} points at ${STEP}-day steps; precomputing`);
for(const r of data){
  const gc=new Float64Array(NG*NB), gs=new Float64Array(NG*NB);
  for(let k=0;k<NG;k++){const t=r.tM+k*STEP;
    for(let j=0;j<NB;j++){const th=siderealLongitude(P[j],t)*D2R;gc[k*NB+j]=Math.cos(th);gs[k*NB+j]=Math.sin(th);}}
  r.gc=gc; r.gs=gs;
  const n1r=new Float64Array(NB),n1i=new Float64Array(NB),n2r=new Float64Array(NB),n2i=new Float64Array(NB);
  for(let j=0;j<NB;j++){
    const p1=siderealLongitude(P[j],r.t1)*D2R, p2=siderealLongitude(P[j],r.t2)*D2R;
    n1r[j]=Math.cos(p1); n1i[j]=-Math.sin(p1);      // conj(exp(i P1_j))
    n2r[j]=Math.cos(p2); n2i[j]=-Math.sin(p2);
  }
  r.n1r=n1r;r.n1i=n1i;r.n2r=n2r;r.n2i=n2i;
}
const NP=2*(2+2*NB);   // b1,a1 then b2,a2

/** z_sum(t) at grid point k. */
function zsum(th,r,k){
  let re=th[0]+th[2+2*NB], im=th[1]+th[3+2*NB];
  const off=2+2*NB;
  for(let j=0;j<NB;j++){
    const ec=r.gc[k*NB+j], es=r.gs[k*NB+j];
    const A0=th[2+2*j],A1=th[3+2*j];
    const v1r=A0*r.n1r[j]-A1*r.n1i[j], v1i=A0*r.n1i[j]+A1*r.n1r[j];
    re+=v1r*ec-v1i*es; im+=v1r*es+v1i*ec;
    const B0=th[off+2+2*j],B1=th[off+3+2*j];
    const v2r=B0*r.n2r[j]-B1*r.n2i[j], v2i=B0*r.n2i[j]+B1*r.n2r[j];
    re+=v2r*ec-v2i*es; im+=v2r*es+v2i*ec;
  }
  return [re,im];
}
const scoreL1=(th,r)=>{let s=0;for(let k=0;k<NG;k++){const[x,y]=zsum(th,r,k);s+=Math.hypot(x,y);}return s/NG;};
const scoreL2=(th,r)=>{let s=0;for(let k=0;k<NG;k++){const[x,y]=zsum(th,r,k);s+=x*x+y*y;}return s/NG;};

const sig=z=>1/(1+Math.exp(-Math.max(-30,Math.min(30,z))));
function readout(S,set){
  const m=set.reduce((s,r)=>s+S.get(r),0)/set.length;
  const sd=Math.sqrt(set.reduce((s,r)=>s+(S.get(r)-m)**2,0)/set.length)||1;
  let c0=0,c1=0;
  for(let it=0;it<300;it++){let g0=0,g1=0,h0=0,h1=0;
    for(const r of set){const x=(S.get(r)-m)/sd,p=sig(c0+c1*x),w=Math.max(p*(1-p),1e-6);
      g0+=r.y-p;g1+=(r.y-p)*x;h0+=w;h1+=w*x*x;}
    c0+=g0/(h0+1);c1+=g1/(h1+1);}
  return {c0,c1,m,sd};
}
const acc=(S,ro,set)=>set.filter(r=>(sig(ro.c0+ro.c1*(S.get(r)-ro.m)/ro.sd)>=0.5?1:0)===r.y).length/set.length;

function fit(scorer,{steps=220,batch=260,restarts=3}={}){
  let best=null;
  for(let rs=0;rs<restarts;rs++){
    const th=new Float64Array(NP);
    for(let i=0;i<NP;i++) th[i]=0.35*gauss();
    const m=new Float64Array(NP),v=new Float64Array(NP);
    const b1=0.9,b2=0.999,eps=1e-8,h=1e-4;
    const L=(tt,set)=>{const S=new Map();for(const r of set)S.set(r,scorer(tt,r));
      const ro=readout(S,set);let l=0;
      for(const r of set){const p=Math.min(1-1e-12,Math.max(1e-12,sig(ro.c0+ro.c1*(S.get(r)-ro.m)/ro.sd)));
        l-=r.y?Math.log(p):Math.log(1-p);}return l/set.length;};
    for(let t=1;t<=steps;t++){
      const lr=0.07*(1-t/(steps+1));
      const bt=[];for(let i=0;i<batch;i++)bt.push(TR[Math.floor(rnd()*TR.length)]);
      for(let i=0;i<NP;i++){
        const o=th[i];
        th[i]=o+h;const lp=L(th,bt); th[i]=o-h;const lm=L(th,bt); th[i]=o;
        const g=(lp-lm)/(2*h);
        m[i]=b1*m[i]+(1-b1)*g; v[i]=b2*v[i]+(1-b2)*g*g;
        th[i]-=lr*(m[i]/(1-b1**t))/(Math.sqrt(v[i]/(1-b2**t))+eps);
      }
    }
    const l=L(th,TR); if(!best||l<best.l) best={l,th:Float64Array.from(th)};
  }
  return best.th;
}

// Rotation invariance, on the assembled model.
{
  const th=new Float64Array(NP); for(let i=0;i<NP;i++) th[i]=0.4*gauss();
  const r=data[0];
  const shifted=(d)=>{
    let s=0;
    for(let k=0;k<NG;k++){
      const t=r.tM+k*STEP;
      let re=th[0]+th[2+2*NB], im=th[1]+th[3+2*NB]; const off=2+2*NB;
      for(let j=0;j<NB;j++){
        const th_t=siderealLongitude(P[j],t)+d, p1=siderealLongitude(P[j],r.t1)+d, p2=siderealLongitude(P[j],r.t2)+d;
        const d1=(th_t-p1)*D2R, d2=(th_t-p2)*D2R;
        re+=th[2+2*j]*Math.cos(d1)-th[3+2*j]*Math.sin(d1); im+=th[2+2*j]*Math.sin(d1)+th[3+2*j]*Math.cos(d1);
        re+=th[off+2+2*j]*Math.cos(d2)-th[off+3+2*j]*Math.sin(d2); im+=th[off+2+2*j]*Math.sin(d2)+th[off+3+2*j]*Math.cos(d2);
      }
      s+=Math.hypot(re,im);
    }
    return s/NG;
  };
  const base=shifted(0);
  console.log(`\n  ROTATION INVARIANCE of |z_sum|:`);
  for(const d of [1,25,180]) console.log(`    shift ${String(d).padStart(3)} deg -> ${shifted(d).toFixed(12)}   |diff| ${Math.abs(shifted(d)-base).toExponential(2)}`);
}

console.log(`\n  fitting on the L2 score (|z_sum|^2), which is smooth and cheap`);
const th2=fit(scoreL2);
console.log(`  fitting on the L1 score (|z_sum|) as specified`);
const th1=fit(scoreL1,{steps:140,batch:200,restarts:2});

console.log(`\n  score                                       TRAIN     VAL      TEST`);
for(const [nm,th,sc] of [["|z_sum| , fitted on |z_sum|",th1,scoreL1],
                          ["|z_sum| , fitted on |z_sum|^2",th2,scoreL1],
                          ["|z_sum|^2, fitted on |z_sum|^2",th2,scoreL2]]){
  const S=new Map(); for(const r of data) S.set(r,sc(th,r));
  const ro=readout(S,TR);
  console.log(`  ${nm.padEnd(42)} ${(100*acc(S,ro,TR)).toFixed(2)}%   ${(100*acc(S,ro,VA)).toFixed(2)}%   ${(100*acc(S,ro,TE)).toFixed(2)}%`);
}
console.log(`  ${"the coin".padEnd(42)}   —        —       50.00%`);

// Diagnostics on the specified L1 model.
{
  const S=new Map(); for(const r of data) S.set(r,scoreL1(th1,r));
  const corr=(f,g)=>{const n=data.length,mf=data.reduce((s,r)=>s+f(r),0)/n,mg=data.reduce((s,r)=>s+g(r),0)/n;
    let c=0,df=0,dg=0;for(const r of data){c+=(f(r)-mf)*(g(r)-mg);df+=(f(r)-mf)**2;dg+=(g(r)-mg)**2;}return c/Math.sqrt(df*dg);};
  console.log(`\n  WHAT THE |z_sum| SCORE TRACKS`);
  console.log(`    vs age gap         : r = ${corr(r=>S.get(r),r=>r.gap).toFixed(4)}`);
  console.log(`    vs age at marriage : r = ${corr(r=>S.get(r),r=>r.ageM).toFixed(4)}`);
  console.log(`    vs mean birth year : r = ${corr(r=>S.get(r),r=>r.year).toFixed(4)}`);
  console.log(`    vs wedding year    : r = ${corr(r=>S.get(r),r=>r.wedYear).toFixed(4)}`);
  console.log(`    vs DIVORCE         : r = ${corr(r=>S.get(r),r=>r.y).toFixed(4)}`);
  const off=2+2*NB;
  const amp=P.map((n,j)=>({n,a1:Math.hypot(th1[2+2*j],th1[3+2*j]),a2:Math.hypot(th1[off+2+2*j],th1[off+3+2*j])}))
    .sort((x,y)=>(y.a1+y.a2)-(x.a1+x.a2));
  console.log(`\n  fitted amplitudes — older partner (a1) and younger (a2):`);
  for(const q of amp) console.log(`    ${q.n.padEnd(9)} a1 ${q.a1.toFixed(4)}   a2 ${q.a2.toFixed(4)}`);
  const OUT=["Uranus","Neptune","Pluto"];
  const so=Math.hypot(...amp.filter(q=>OUT.includes(q.n)).flatMap(q=>[q.a1,q.a2]));
  const st=Math.hypot(...amp.flatMap(q=>[q.a1,q.a2]));
  console.log(`    the three outer planets hold ${(100*(so/st)**2).toFixed(1)}% of the squared amplitude`);
  // Does the older/younger asymmetry carry content? Swap the two partners' amplitudes and re-score.
  const sw=Float64Array.from(th1);
  for(let j=0;j<2+2*NB;j++){const t=sw[j];sw[j]=sw[off+j];sw[off+j]=t;}
  const S2=new Map(); for(const r of data) S2.set(r,scoreL1(sw,r));
  const ro2=readout(S2,TR);
  console.log(`\n  swapping the two partners' amplitude sets: TEST ${(100*acc(S2,ro2,TE)).toFixed(2)}%`);
  console.log(`    (if the older/younger distinction carries content, this should be clearly worse)`);
}
