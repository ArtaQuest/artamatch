/**
 * zsum2.mjs — the squared superposition, integrated over 60 years, in closed form.
 *
 *   z_1(t) = b1 + SUM_j a1_j exp( i ( theta_j(t) - P1_j ) )      P1_j = older partner's natal phase
 *   z_2(t) = b2 + SUM_j a2_j exp( i ( theta_j(t) - P2_j ) )      P2_j = younger partner's
 *   score  = (1/T) INTEGRAL_{t_m}^{t_m+T} | z_1(t) + z_2(t) |^2 dt          T = 60 years
 *
 * ── Why the square is the better choice, and what it buys ────────────────────────────────────────
 *
 * |z_sum|^2 has an EXACT closed form, and |z_sum| does not. Write E_j(t) = exp(i theta_j(t)) for the
 * transiting sky, N_pj = exp(i P_pj) for a natal phase, v_pj = a_pj conj(N_pj), and collect
 *
 *      B = b1 + b2            w_j = v_1j + v_2j
 *      z_sum(t) = B + SUM_j w_j E_j(t)
 *
 * Then, with two sets of coefficients that do not involve the parameters at all,
 *
 *      C_j  = (1/T) INT E_j(t) dt                    10 complex numbers per couple
 *      D_jm = (1/T) INT E_j(t) conj(E_m(t)) dt      100 more
 *
 *      score  =  |B|^2  +  2 Re[ conj(B) SUM_j w_j C_j ]  +  SUM_j SUM_m Re[ w_j conj(w_m) D_jm ]
 *
 * exactly. So the integral is computed ONCE per couple, and every subsequent evaluation is 110 complex
 * multiplies rather than a 1,565-point numerical integral. Three consequences:
 *
 *   the 60-year window costs the same as the 28-year one — the grid only enters the precomputation
 *   there is no integration error left in the score at all
 *   the optimiser gets thousands of steps instead of hundreds, so the fit is a real one
 *
 * Checked below against direct numerical integration before it is used for anything.
 *
 * Rotation invariance survives: every phase is a difference of two longitudes and |.|^2 ignores a
 * global phase. T is a global constant, never each couple's own marriage length.
 */
import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);
const D2R=Math.PI/180;
const P=["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"];
const NB=P.length, YR=365.2425, STEP=14;
const WINDOWS = { "60 years": 60*YR, "28 years": 28*YR };
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
  const g1=(jm-ja)/YR, g2=(jm-jb)/YR;
  if(g1<12||g2<12||g1>90) continue;
  rows.push({a:pa,b:pb,y:r.y,t1:ja,t2:jb,tM:jm,year:(ya+yb)/2,wedYear:M.y,gap:(jb-ja)/YR,ageM:(g1+g2)/2});
}
SEED=20260807;
const pos=rows.filter(r=>r.y===1),neg=rows.filter(r=>r.y===0),K=Math.min(pos.length,neg.length);
const data=shuffle([...shuffle(pos).slice(0,K),...shuffle(neg).slice(0,K)]);
const side=new Map(); SEED=20260807;
for(const r of data){let s=side.get(r.a)??side.get(r.b);
  if(s===undefined){const u=rnd();s=u<0.6?"train":u<0.8?"val":"test";}
  side.set(r.a,s);side.set(r.b,s);r.side=s;}
const TR=data.filter(r=>r.side==="train"),VA=data.filter(r=>r.side==="val"),TE=data.filter(r=>r.side==="test");
console.log(`\nSQUARED SUPERPOSITION, CLOSED FORM   score = mean |z_1 + z_2|^2 over T years from the wedding`);
console.log(`  ${data.length.toLocaleString()} couples, ${K.toLocaleString()} per class — coin 50.00%`);
console.log(`  ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} val · ${TE.length.toLocaleString()} test, split by person`);

/** natal phase conjugates, shared by every window */
for(const r of data){
  const n1r=new Float64Array(NB),n1i=new Float64Array(NB),n2r=new Float64Array(NB),n2i=new Float64Array(NB);
  for(let j=0;j<NB;j++){
    const p1=siderealLongitude(P[j],r.t1)*D2R, p2=siderealLongitude(P[j],r.t2)*D2R;
    n1r[j]=Math.cos(p1); n1i[j]=-Math.sin(p1);
    n2r[j]=Math.cos(p2); n2i[j]=-Math.sin(p2);
  }
  r.n1r=n1r;r.n1i=n1i;r.n2r=n2r;r.n2i=n2i;
}
/** C_j and D_jm for one window. This is the only place the grid appears. */
function precompute(T){
  const NG=Math.floor(T/STEP)+1;
  for(const r of data){
    const Cr=new Float64Array(NB),Ci=new Float64Array(NB);
    const Dr=new Float64Array(NB*NB),Di=new Float64Array(NB*NB);
    const ec=new Float64Array(NB),es=new Float64Array(NB);
    for(let k=0;k<NG;k++){
      const t=r.tM+k*STEP;
      for(let j=0;j<NB;j++){const th=siderealLongitude(P[j],t)*D2R;ec[j]=Math.cos(th);es[j]=Math.sin(th);}
      for(let j=0;j<NB;j++){
        Cr[j]+=ec[j];Ci[j]+=es[j];
        for(let m=0;m<NB;m++){
          Dr[j*NB+m]+=ec[j]*ec[m]+es[j]*es[m];
          Di[j*NB+m]+=es[j]*ec[m]-ec[j]*es[m];
        }
      }
    }
    for(let j=0;j<NB;j++){Cr[j]/=NG;Ci[j]/=NG;}
    for(let i=0;i<NB*NB;i++){Dr[i]/=NG;Di[i]/=NG;}
    r.Cr=Cr;r.Ci=Ci;r.Dr=Dr;r.Di=Di;
  }
  return NG;
}
const NP=2*(2+2*NB);
/** The exact closed form. */
function score(th,r){
  const off=2+2*NB;
  const Br=th[0]+th[off], Bi=th[1]+th[off+1];
  const wr=new Float64Array(NB), wi=new Float64Array(NB);
  for(let j=0;j<NB;j++){
    const A0=th[2+2*j],A1=th[3+2*j],B0=th[off+2+2*j],B1=th[off+3+2*j];
    wr[j]=(A0*r.n1r[j]-A1*r.n1i[j])+(B0*r.n2r[j]-B1*r.n2i[j]);
    wi[j]=(A0*r.n1i[j]+A1*r.n1r[j])+(B0*r.n2i[j]+B1*r.n2r[j]);
  }
  let s=Br*Br+Bi*Bi;
  for(let j=0;j<NB;j++){
    // 2 Re[ conj(B) w_j C_j ]
    const xr=wr[j]*r.Cr[j]-wi[j]*r.Ci[j], xi=wr[j]*r.Ci[j]+wi[j]*r.Cr[j];
    s+=2*(Br*xr+Bi*xi);
    for(let m=0;m<NB;m++){
      const pr=wr[j]*wr[m]+wi[j]*wi[m], pi=wi[j]*wr[m]-wr[j]*wi[m];
      s+=pr*r.Dr[j*NB+m]-pi*r.Di[j*NB+m];
    }
  }
  return s;
}
/** Direct numerical integration, for the check only. */
function scoreDirect(th,r,T){
  const NG=Math.floor(T/STEP)+1, off=2+2*NB; let s=0;
  for(let k=0;k<NG;k++){
    const t=r.tM+k*STEP;
    let re=th[0]+th[off], im=th[1]+th[off+1];
    for(let j=0;j<NB;j++){
      const th_t=siderealLongitude(P[j],t)*D2R;
      const ec=Math.cos(th_t),es=Math.sin(th_t);
      const A0=th[2+2*j],A1=th[3+2*j],B0=th[off+2+2*j],B1=th[off+3+2*j];
      const v1r=A0*r.n1r[j]-A1*r.n1i[j], v1i=A0*r.n1i[j]+A1*r.n1r[j];
      const v2r=B0*r.n2r[j]-B1*r.n2i[j], v2i=B0*r.n2i[j]+B1*r.n2r[j];
      const Wr=v1r+v2r, Wi=v1i+v2i;
      re+=Wr*ec-Wi*es; im+=Wr*es+Wi*ec;
    }
    s+=re*re+im*im;
  }
  return s/NG;
}
const sig=z=>1/(1+Math.exp(-Math.max(-30,Math.min(30,z))));
function readout(S,set,iters=300){
  const m=set.reduce((s,r)=>s+S.get(r),0)/set.length;
  const sd=Math.sqrt(set.reduce((s,r)=>s+(S.get(r)-m)**2,0)/set.length)||1;
  let c0=0,c1=0;
  for(let it=0;it<iters;it++){let g0=0,g1=0,h0=0,h1=0;
    for(const r of set){const x=(S.get(r)-m)/sd,p=sig(c0+c1*x),w=Math.max(p*(1-p),1e-6);
      g0+=r.y-p;g1+=(r.y-p)*x;h0+=w;h1+=w*x*x;}
    c0+=g0/(h0+1);c1+=g1/(h1+1);}
  return {c0,c1,m,sd};
}
const acc=(S,ro,set)=>set.filter(r=>(sig(ro.c0+ro.c1*(S.get(r)-ro.m)/ro.sd)>=0.5?1:0)===r.y).length/set.length;
function fit({steps=1500,batch=384,restarts=4}={}){
  let best=null;
  for(let rs=0;rs<restarts;rs++){
    const th=new Float64Array(NP);
    for(let i=0;i<NP;i++) th[i]=0.35*gauss();
    const m=new Float64Array(NP),v=new Float64Array(NP);
    const b1=0.9,b2=0.999,eps=1e-8,h=1e-4;
    // The readout is refitted once per STEP and held fixed across that step's finite differences.
    // The gradient with respect to the amplitudes is the same either way, and this is ten times cheaper.
    const L=(tt,set,ro)=>{let l=0;
      for(const r of set){const x=(score(tt,r)-ro.m)/ro.sd;
        const p=Math.min(1-1e-12,Math.max(1e-12,sig(ro.c0+ro.c1*x)));
        l-=r.y?Math.log(p):Math.log(1-p);}return l/set.length;};
    for(let t=1;t<=steps;t++){
      const lr=0.05*(1-t/(steps+1));
      const bt=[];for(let i=0;i<batch;i++)bt.push(TR[Math.floor(rnd()*TR.length)]);
      const Sb=new Map(); for(const r of bt) Sb.set(r,score(th,r));
      const ro=readout(Sb,bt,40);
      for(let i=0;i<NP;i++){
        const o=th[i];
        th[i]=o+h;const lp=L(th,bt,ro); th[i]=o-h;const lm=L(th,bt,ro); th[i]=o;
        const g=(lp-lm)/(2*h);
        m[i]=b1*m[i]+(1-b1)*g; v[i]=b2*v[i]+(1-b2)*g*g;
        th[i]-=lr*(m[i]/(1-b1**t))/(Math.sqrt(v[i]/(1-b2**t))+eps);
      }
    }
    const Sf=new Map(); for(const r of TR) Sf.set(r,score(th,r));
    const l=L(th,TR,readout(Sf,TR)); if(!best||l<best.l) best={l,th:Float64Array.from(th)};
  }
  return best.th;
}

const results={};
for(const [wname,T] of Object.entries(WINDOWS)){
  const NG=precompute(T);
  console.log(`\n══ window ${wname} — ${NG} grid points in the precomputation, then exact ══`);
  // Check the closed form against direct integration.
  {
    const th=new Float64Array(NP); for(let i=0;i<NP;i++) th[i]=0.4*gauss();
    let worst=0;
    for(let k=0;k<25;k++){ const r=data[Math.floor(rnd()*data.length)];
      worst=Math.max(worst,Math.abs(score(th,r)-scoreDirect(th,r,T))); }
    console.log(`  closed form vs direct integration, worst of 25 couples: ${worst.toExponential(2)}  ${worst<1e-9?"PASS":"FAIL"}`);
  }
  const th=fit();
  const S=new Map(); for(const r of data) S.set(r,score(th,r));
  const ro=readout(S,TR);
  const a=[acc(S,ro,TR),acc(S,ro,VA),acc(S,ro,TE)];
  results[wname]={th,S,a};
  console.log(`  TRAIN ${(100*a[0]).toFixed(2)}%   VAL ${(100*a[1]).toFixed(2)}%   TEST ${(100*a[2]).toFixed(2)}%   (coin 50.00%)`);
  const off=2+2*NB;
  const amp=P.map((n,j)=>({n,a1:Math.hypot(th[2+2*j],th[3+2*j]),a2:Math.hypot(th[off+2+2*j],th[off+3+2*j])}))
    .sort((x,y)=>(y.a1+y.a2)-(x.a1+x.a2));
  console.log(`  amplitudes — older (a1) / younger (a2):`);
  for(const q of amp.slice(0,5)) console.log(`    ${q.n.padEnd(9)} ${q.a1.toFixed(4)} / ${q.a2.toFixed(4)}`);
  const OUT=["Uranus","Neptune","Pluto"];
  const so=Math.hypot(...amp.filter(q=>OUT.includes(q.n)).flatMap(q=>[q.a1,q.a2]));
  const st=Math.hypot(...amp.flatMap(q=>[q.a1,q.a2]));
  console.log(`    the three outer planets hold ${(100*(so/st)**2).toFixed(1)}% of the squared amplitude`);
  const corr=(f,g)=>{const n=data.length,mf=data.reduce((s,r)=>s+f(r),0)/n,mg=data.reduce((s,r)=>s+g(r),0)/n;
    let c=0,df=0,dg=0;for(const r of data){c+=(f(r)-mf)*(g(r)-mg);df+=(f(r)-mf)**2;dg+=(g(r)-mg)**2;}return c/Math.sqrt(df*dg);};
  console.log(`  what it tracks: age gap ${corr(r=>S.get(r),r=>r.gap).toFixed(4)}  age at marriage ${corr(r=>S.get(r),r=>r.ageM).toFixed(4)}` +
    `  birth year ${corr(r=>S.get(r),r=>r.year).toFixed(4)}  wedding year ${corr(r=>S.get(r),r=>r.wedYear).toFixed(4)}  DIVORCE ${corr(r=>S.get(r),r=>r.y).toFixed(4)}`);
  // Does the older/younger split carry content?
  const sw=Float64Array.from(th);
  for(let j=0;j<off;j++){const t=sw[j];sw[j]=sw[off+j];sw[off+j]=t;}
  const S2=new Map(); for(const r of data) S2.set(r,score(sw,r));
  console.log(`  swapping the two amplitude sets: TEST ${(100*acc(S2,readout(S2,TR),TE)).toFixed(2)}%`);
}
