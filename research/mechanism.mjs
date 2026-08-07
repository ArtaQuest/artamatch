/**
 * mechanism.mjs — is the "signal" a clock?
 *
 * If the outer planets are carrying the couple's AGE GAP rather than anything about the two of them,
 * it will show directly: sin(theta_Pluto(father) - theta_Pluto(mother)) will be almost perfectly
 * correlated with how many years apart they were born, because Pluto moves so slowly that its angle
 * difference IS that gap, rescaled. This measures it body by body.
 */
import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);
const D2R = Math.PI/180;
const B = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"];
const raw = JSON.parse(readFileSync(process.argv[2] ?? "./data/dataset.json", "utf8"));
const P = (s)=>{const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(s??"");return m?{y:+m[1],m:+m[2],d:+m[3]}:null;};
const EXCLUDE = process.env.EXCLUDE ?? "firsts";
const isPlaceholder = (iso) => EXCLUDE === "none" ? false
  : EXCLUDE === "firsts" ? iso.endsWith("-01") : iso.endsWith("-01-01");
const rows=[];
for (const r of raw){
  const f=P(r.fDob), m=P(r.mDob);
  if(!f||!m||f.y<1800||f.y>2012||m.y<1800||m.y>2012) continue;
  if(isPlaceholder(r.fDob)||isPlaceholder(r.mDob)) continue;
  const fj=julianDay(f.y,f.m,f.d,12), mj=julianDay(m.y,m.m,m.d,12);
  const P2=(x)=>{const q=P(x);return q?julianDay(q.y,q.m,q.d,12):null;};
  const st=P2(r.start), en=[r.end,r.fDod,r.mDod].map(P2).filter(v=>v!==null);
  const dur = st!==null&&en.length&&Math.min(...en)>st ? (Math.min(...en)-st)/365.2425 : null;
  rows.push({gap:(fj-mj)/365.2425, y:r.children, dur,
    d:B.map(b=>((siderealLongitude(b,fj)-siderealLongitude(b,mj))%360+360)%360)});
}
const corr=(a,b)=>{const n=a.length,ma=a.reduce((s,v)=>s+v,0)/n,mb=b.reduce((s,v)=>s+v,0)/n;
  let x=0,p=0,q=0;for(let i=0;i<n;i++){x+=(a[i]-ma)*(b[i]-mb);p+=(a[i]-ma)**2;q+=(b[i]-mb)**2;}return x/Math.sqrt(p*q);};
const gap=rows.map(r=>r.gap), kids=rows.map(r=>r.y);
console.log(`\n${rows.length.toLocaleString()} couples. Correlation of each feature with the couple's AGE GAP in years,`);
console.log(`and with the number of children — the thing the model is actually supposed to predict.\n`);
const wd=rows.filter(r=>r.dur!==null), wdur=wd.map(r=>r.dur), wgap=wd.map(r=>r.gap);
console.log(`  body        sin vs age gap   cos vs age gap   sin vs children   sin vs YEARS MARRIED`);
for(let i=0;i<B.length;i++){
  const s=rows.map(r=>Math.sin(r.d[i]*D2R)), c=rows.map(r=>Math.cos(r.d[i]*D2R));
  const sd=wd.map(r=>Math.sin(r.d[i]*D2R));
  console.log(`  ${B[i].padEnd(10)} ${corr(s,gap).toFixed(4).padStart(9)}        ${corr(c,gap).toFixed(4).padStart(9)}        ${corr(s,kids).toFixed(4).padStart(9)}         ${corr(sd,wdur).toFixed(4).padStart(9)}`);
}
console.log(`\n  age gap itself vs children     : ${corr(gap,kids).toFixed(4)}`);
console.log(`  age gap itself vs years married: ${corr(wgap,wdur).toFixed(4)}`);
console.log(`  years married  vs children     : ${corr(wdur,wd.map(r=>r.y)).toFixed(4)}   <- the only real predictor in this dataset`);
