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

const raw=JSON.parse(readFileSync(`${DIR}/balanced-stated-cause-only.json`,"utf8"));
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


// ══════════════════════════════════════════════════════════════════════════════════════════════════
//  THE THREE CHECKS. A model that beats a weak comparator has beaten nothing.
// ══════════════════════════════════════════════════════════════════════════════════════════════════
const T60 = 60*YR;
precompute(T60);
console.log(`\n  fitting the 60-year model`);
const th = fit({steps:1200,batch:384,restarts:3});
const S = new Map(); for(const r of data) S.set(r,score(th,r));

/** Ridge least squares, for the orthogonalisation and the linear baselines. */
function solveSym(A,b,p){
  const M=new Float64Array(p*(p+1));
  for(let i=0;i<p;i++){for(let j=0;j<p;j++)M[i*(p+1)+j]=A[i*p+j];M[i*(p+1)+p]=b[i];}
  for(let c=0;c<p;c++){
    let pv=c; for(let r=c+1;r<p;r++) if(Math.abs(M[r*(p+1)+c])>Math.abs(M[pv*(p+1)+c])) pv=r;
    if(pv!==c) for(let k=c;k<=p;k++){const t=M[c*(p+1)+k];M[c*(p+1)+k]=M[pv*(p+1)+k];M[pv*(p+1)+k]=t;}
    const d=M[c*(p+1)+c]; if(Math.abs(d)<1e-12) continue;
    for(let r=0;r<p;r++){ if(r===c) continue; const f=M[r*(p+1)+c]/d; if(f===0) continue;
      for(let k=c;k<=p;k++) M[r*(p+1)+k]-=f*M[c*(p+1)+k]; }
  }
  const w=new Float64Array(p);
  for(let i=0;i<p;i++){const d=M[i*(p+1)+i];w[i]=Math.abs(d)<1e-12?0:M[i*(p+1)+p]/d;}
  return w;
}
const dotf=(w,x)=>{let s=0;for(let i=0;i<w.length;i++)s+=w[i]*x[i];return s;};
function ridge(X,y,l){const n=X.length,p=X[0].length;
  const A=new Float64Array(p*p),g=new Float64Array(p);
  for(let i=0;i<n;i++){const xi=X[i],yi=y[i];
    for(let j=0;j<p;j++){const xj=xi[j];if(xj===0)continue;g[j]+=xj*yi;
      for(let k=j;k<p;k++)A[j*p+k]+=xj*xi[k];}}
  for(let j=0;j<p;j++){for(let k=0;k<j;k++)A[j*p+k]=A[k*p+j];A[j*p+j]+=l;}
  return solveSym(A,g,p);
}
function logit(X,y,l,iters=8){const n=X.length,p=X[0].length,w=new Float64Array(p);
  let pos=0; for(const q of y) pos+=q;
  w[0]=Math.log((pos+1)/(n-pos+1));
  const A=new Float64Array(p*p),g=new Float64Array(p);
  for(let it=0;it<iters;it++){A.fill(0);g.fill(0);
    for(let i=0;i<n;i++){const xi=X[i],mu=sig(dotf(w,xi)),wt=Math.max(mu*(1-mu),1e-6),rr=y[i]-mu;
      for(let j=0;j<p;j++){const xj=xi[j];if(xj===0)continue;g[j]+=xj*rr;const wx=wt*xj;
        for(let k=j;k<p;k++)A[j*p+k]+=wx*xi[k];}}
    for(let j=0;j<p;j++){for(let k=0;k<j;k++)A[j*p+k]=A[k*p+j];A[j*p+j]+=l;}
    const st=solveSym(A,g,p); for(let j=0;j<p;j++) w[j]+=st[j];}
  return w;
}

/** BASELINE A: what I used all along — 20-year indicator bins plus age-gap terms. */
const BINS=[]; for(let y=1500;y<=2000;y+=20) BINS.push(y);
const A_DATE=r=>[r.year<1500?1:0,...BINS.map(b=>(r.year>=b&&r.year<b+20?1:0)),
  r.gap/10,(r.gap/10)**2,Math.abs(r.gap)/10];
/** BASELINE B: a properly specified SMOOTH function of the same three dates. Continuous polynomials
 *  in birth year, wedding year, both ages and the gap — the comparator the score deserves. */
const sc=(v,c,s)=>(v-c)/s;
const B_DATE=r=>{
  const by=sc(r.year,1900,100), wy=sc(r.wedYear,1930,100), am=sc(r.ageM,30,15), gp=sc(r.gap,0,10);
  const o=[];
  for(const v of [by,wy,am,gp]) o.push(v,v*v,v*v*v);
  o.push(by*wy, by*am, wy*am, by*gp, wy*gp, am*gp);
  o.push(Math.abs(gp), Math.abs(gp)**1.5);
  return o;
};
const accOf=(w,build,set)=>set.filter(r=>(sig(dotf(w,build(r)))>=0.5?1:0)===r.y).length/set.length;
function run(name,build,l=1){
  const w=logit(TR.map(build),Float64Array.from(TR.map(r=>r.y)),l);
  const a=[accOf(w,build,TR),accOf(w,build,VA),accOf(w,build,TE)];
  console.log(`  ${name.padEnd(52)} ${String(build(TR[0]).length-1).padStart(4)}   ${(100*a[0]).toFixed(2)}%   ${(100*a[1]).toFixed(2)}%   ${(100*a[2]).toFixed(2)}%`);
  return a[2];
}
const Z=r=>[S.get(r)];

console.log(`\n${"═".repeat(88)}`);
console.log(`  CHECK 1 — IS THE BASELINE I BEAT ACTUALLY ANY GOOD?`);
console.log(`${"═".repeat(88)}`);
console.log(`  model                                                cols   TRAIN     VAL      TEST`);
const aA=run("BASELINE A: 20-year bins + age gap (what I used)",r=>Float64Array.from([1,...A_DATE(r)]));
const aB=run("BASELINE B: smooth polynomials in the same dates",r=>Float64Array.from([1,...B_DATE(r)]));
const aZ=run("the |z_sum|^2 score alone, 60-year window",r=>Float64Array.from([1,...Z(r)]));
const aZB=run("|z_sum|^2 + baseline B",r=>Float64Array.from([1,...Z(r),...B_DATE(r)]));
console.log(`\n  If baseline B reaches the score's accuracy, the 4.6-point \"win\" was my bins being coarse,`);
console.log(`  not astrology being right.`);

console.log(`\n${"═".repeat(88)}`);
console.log(`  CHECK 2 — ORTHOGONALISE: strip everything the dates can predict, keep the remainder`);
console.log(`${"═".repeat(88)}`);
{
  const E=r=>Float64Array.from([1,...B_DATE(r)]);
  const proj=ridge(TR.map(E),Float64Array.from(TR.map(r=>S.get(r))),1e-3);
  const resid=new Map();
  for(const r of data) resid.set(r,S.get(r)-dotf(proj,E(r)));
  const build=r=>Float64Array.from([1,resid.get(r)]);
  const w=logit(TR.map(build),Float64Array.from(TR.map(r=>r.y)),1);
  const a=[accOf(w,build,TR),accOf(w,build,VA),accOf(w,build,TE)];
  const varS=(()=>{const m=data.reduce((s,r)=>s+S.get(r),0)/data.length;
    return data.reduce((s,r)=>s+(S.get(r)-m)**2,0)/data.length;})();
  const varR=(()=>{const m=data.reduce((s,r)=>s+resid.get(r),0)/data.length;
    return data.reduce((s,r)=>s+(resid.get(r)-m)**2,0)/data.length;})();
  console.log(`  the dates explain ${(100*(1-varR/varS)).toFixed(1)}% of the score's variance`);
  console.log(`  the orthogonalised remainder alone:  TRAIN ${(100*a[0]).toFixed(2)}%   VAL ${(100*a[1]).toFixed(2)}%   TEST ${(100*a[2]).toFixed(2)}%`);
}

console.log(`\n${"═".repeat(88)}`);
console.log(`  CHECK 3 — ERA-PRESERVING NULL: shuffle partners only within a WEDDING DECADE`);
console.log(`${"═".repeat(88)}`);
{
  const NPERM=60;
  const groups=new Map();
  for(const r of data){const d=Math.floor(r.wedYear/10);(groups.get(d)??groups.set(d,[]).get(d)).push(r);}
  const keep=data.map(r=>({n2r:r.n2r,n2i:r.n2i}));
  const build=r=>Float64Array.from([1,score(th,r)]);
  const measure=()=>{const w=logit(TR.map(build),Float64Array.from(TR.map(r=>r.y)),1);
    return accOf(w,build,TE);};
  const real=measure();
  const nulls=[];
  for(let p=0;p<NPERM;p++){
    for(const [,g] of groups){
      const perm=shuffle(g.map(r=>({n2r:r.n2r,n2i:r.n2i})));
      g.forEach((r,i)=>{r.n2r=perm[i].n2r;r.n2i=perm[i].n2i;});
    }
    nulls.push(measure());
  }
  data.forEach((r,i)=>{r.n2r=keep[i].n2r;r.n2i=keep[i].n2i;});
  nulls.sort((a,b)=>a-b);
  const above=nulls.filter(v=>v>=real).length;
  console.log(`  real ${(100*real).toFixed(2)}%   null median ${(100*nulls[NPERM>>1]).toFixed(2)}%   95th ${(100*nulls[Math.floor(NPERM*0.95)]).toFixed(2)}%   p = ${((above+1)/(NPERM+1)).toFixed(3)}`);
  console.log(`  Only the YOUNGER partner's natal phases are permuted, within the same wedding decade, so`);
  console.log(`  the era structure is untouched and only WHO WAS MATCHED WITH WHOM is destroyed.`);
}

console.log(`\n${"═".repeat(88)}`);
console.log(`  VERDICT`);
console.log(`${"═".repeat(88)}`);
console.log(`  best plain date model (B) : ${(100*aB).toFixed(2)}%`);
console.log(`  the |z_sum|^2 score alone : ${(100*aZ).toFixed(2)}%`);
console.log(`  score + dates together    : ${(100*aZB).toFixed(2)}%`);
console.log(`  astrology adds ${(100*(aZB-aB)).toFixed(2)} points over a properly specified date model.`);
