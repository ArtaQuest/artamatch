/**
 * three-dates.mjs — divorce or death, from three dates: both births and the wedding.
 *
 * ── What the marriage date adds ─────────────────────────────────────────────────────────────────
 *
 * Until now the model saw two birth dates. The wedding date opens a vocabulary it could not reach:
 *
 *   TRANSITS TO NATAL   where each planet stood on the wedding day, against where it stood at each
 *                       partner's birth. This is what an astrologer means by the marriage happening
 *                       under a particular sky, and it is the core of electional practice.
 *   THE WEDDING CHART   the aspects among the planets on the day itself.
 *   AGES AT MARRIAGE    derived from a birth date and the wedding date, and a strong ordinary predictor.
 *
 * ── The fair comparator, and why era is not cheating ─────────────────────────────────────────────
 *
 * Everything the astrology sees is computed from these three dates and nothing else. So is everything
 * the baseline sees: which 20-year window each birth falls in, which decade the wedding falls in, how
 * far apart the partners were born, and how old each was on the day. Those are not extra data smuggled
 * in — they are the same three numbers, encoded plainly instead of trigonometrically. That is what
 * makes the comparison a fair one rather than a handicap.
 *
 * ── The placeholder problem is worse here ────────────────────────────────────────────────────────
 *
 * 46.7% of marriage dates in this set fall on 1 January. Wikidata renders a year-precision date that
 * way, and a wedding-day sky computed from a placeholder is a sky the couple was never married under —
 * pure noise in exactly the features the marriage date was added to provide. Those rows are dropped
 * for the transit features, which costs about half the sample, and the classes are re-balanced
 * afterwards because the loss is not even between them.
 *
 * ── Two things carried over from improved.mjs, because they are what make a null result mean something
 *
 *   ORTHOGONALISATION   every astrological feature is replaced by the part of it the date design cannot
 *                       predict, with the projection fitted on the training set alone.
 *   AN ERA-PRESERVING NULL  partners shuffled only within a marriage decade, so the null keeps the era
 *                       structure and tests only who was matched with whom.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/three-dates.mjs ./research/data-divorce
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const YR = 365.2425;
const DIR = process.argv[2] ?? "./research/data-divorce";

let SEED = 20260807;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };
const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

// ── linear algebra ──────────────────────────────────────────────────────────────────────────────
function solveSym(A, b, p) {
  const M = new Float64Array(p * (p + 1));
  for (let i = 0; i < p; i++) { for (let j = 0; j < p; j++) M[i * (p + 1) + j] = A[i * p + j]; M[i * (p + 1) + p] = b[i]; }
  for (let c = 0; c < p; c++) {
    let piv = c;
    for (let r = c + 1; r < p; r++) if (Math.abs(M[r * (p + 1) + c]) > Math.abs(M[piv * (p + 1) + c])) piv = r;
    if (piv !== c) for (let k = c; k <= p; k++) { const t = M[c * (p + 1) + k]; M[c * (p + 1) + k] = M[piv * (p + 1) + k]; M[piv * (p + 1) + k] = t; }
    const d = M[c * (p + 1) + c];
    if (Math.abs(d) < 1e-12) continue;
    for (let r = 0; r < p; r++) {
      if (r === c) continue;
      const f = M[r * (p + 1) + c] / d;
      if (f === 0) continue;
      for (let k = c; k <= p; k++) M[r * (p + 1) + k] -= f * M[c * (p + 1) + k];
    }
  }
  const w = new Float64Array(p);
  for (let i = 0; i < p; i++) { const d = M[i * (p + 1) + i]; w[i] = Math.abs(d) < 1e-12 ? 0 : M[i * (p + 1) + p] / d; }
  return w;
}
const dotf = (w, x) => { let s = 0; for (let i = 0; i < w.length; i++) s += w[i] * x[i]; return s; };
const sigma = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));
function ridgeFit(X, y, ridge) {
  const n = X.length, p = X[0].length;
  const A = new Float64Array(p * p), g = new Float64Array(p);
  for (let i = 0; i < n; i++) {
    const xi = X[i], yi = y[i];
    for (let j = 0; j < p; j++) { const xj = xi[j]; if (xj === 0) continue; g[j] += xj * yi; for (let k = j; k < p; k++) A[j * p + k] += xj * xi[k]; }
  }
  for (let j = 0; j < p; j++) { for (let k = 0; k < j; k++) A[j * p + k] = A[k * p + j]; A[j * p + j] += ridge; }
  return solveSym(A, g, p);
}
function fitLogistic(X, y, ridge, iters = 6) {
  const n = X.length, p = X[0].length;
  const w = new Float64Array(p);
  let pos = 0;
  for (const v of y) pos += v;
  w[0] = Math.log((pos + 1) / (n - pos + 1));
  const A = new Float64Array(p * p), g = new Float64Array(p);
  for (let it = 0; it < iters; it++) {
    A.fill(0); g.fill(0);
    for (let i = 0; i < n; i++) {
      const xi = X[i], mu = sigma(dotf(w, xi)), wt = Math.max(mu * (1 - mu), 1e-6), r = y[i] - mu;
      for (let j = 0; j < p; j++) { const xj = xi[j]; if (xj === 0) continue; g[j] += xj * r; const wx = wt * xj; for (let k = j; k < p; k++) A[j * p + k] += wx * xi[k]; }
    }
    for (let j = 0; j < p; j++) { for (let k = 0; k < j; k++) A[j * p + k] = A[k * p + j]; A[j * p + j] += ridge; }
    const step = solveSym(A, g, p);
    let moved = 0;
    for (let j = 0; j < p; j++) { w[j] += step[j]; moved += Math.abs(step[j]); }
    if (moved < 1e-9) break;
  }
  return w;
}

// ── the data: three dates ───────────────────────────────────────────────────────────────────────
const parseDate = (iso) => {
  const m = /^(-?\d{3,4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};
const isJan1 = (iso) => !!iso && iso.endsWith("-01-01");

const raw = JSON.parse(readFileSync(`${DIR}/balanced-all-precisions.json`, "utf8"));
const rows = [];
const drop = { noStart: 0, jan1Birth: 0, jan1Wedding: 0, impossible: 0 };
for (const r of raw) {
  const A = parseDate(r.aDob), B = parseDate(r.bDob), W = parseDate(r.start);
  if (!A || !B) continue;
  if (isJan1(r.aDob) || isJan1(r.bDob)) { drop.jan1Birth++; continue; }
  if (!W) { drop.noStart++; continue; }
  if (isJan1(r.start)) { drop.jan1Wedding++; continue; }
  let ja = julianDay(A.y, A.m, A.d, 12), jb = julianDay(B.y, B.m, B.d, 12), ya = A.y, yb = B.y;
  let pa = r.a, pb = r.b;
  if (jb < ja) { [ja, jb] = [jb, ja]; [pa, pb] = [pb, pa]; [ya, yb] = [yb, ya]; }
  const jw = julianDay(W.y, W.m, W.d, 12);
  const ageA = (jw - ja) / YR, ageB = (jw - jb) / YR;
  if (ageA < 12 || ageB < 12 || ageA > 90) { drop.impossible++; continue; }
  rows.push({
    a: pa, b: pb, y: r.y,
    birthYear: (ya + yb) / 2, wedYear: W.y, gap: (jb - ja) / YR, ageA, ageB,
    la: PLANETS.map((x) => siderealLongitude(x, ja)),
    lb: PLANETS.map((x) => siderealLongitude(x, jb)),
    lw: PLANETS.map((x) => siderealLongitude(x, jw)),
  });
}
SEED = 20260807;
const posR = rows.filter((r) => r.y === 1), negR = rows.filter((r) => r.y === 0);
const K = Math.min(posR.length, negR.length);
const data = shuffle([...shuffle(posR).slice(0, K), ...shuffle(negR).slice(0, K)]);

console.log(`\nTHREE DATES — both births and the wedding`);
console.log(`  dropped: ${drop.jan1Birth.toLocaleString()} for a 1 January BIRTH, ${drop.noStart.toLocaleString()} with no wedding date,`);
console.log(`           ${drop.jan1Wedding.toLocaleString()} for a 1 January WEDDING (a placeholder sky), ${drop.impossible.toLocaleString()} impossible`);
console.log(`  ${data.length.toLocaleString()} couples after re-balancing, ${K.toLocaleString()} of each class — coin 50.00%`);

const side = new Map();
SEED = 20260807;
for (const r of data) {
  let s = side.get(r.a) ?? side.get(r.b);
  if (s === undefined) s = rnd() < 0.8 ? "train" : "test";
  side.set(r.a, s); side.set(r.b, s);
  r.side = s;
}
const TR = data.filter((r) => r.side === "train"), TE = data.filter((r) => r.side === "test");
console.log(`  ${TR.length.toLocaleString()} train / ${TE.length.toLocaleString()} test, split by person`);

// ── the plain encoding of the same three dates ──────────────────────────────────────────────────
const BB = [], WB = [];
for (let y = 1500; y <= 2000; y += 20) BB.push(y);
for (let y = 1500; y <= 2020; y += 10) WB.push(y);
const DATES = (r) => [
  r.birthYear < 1500 ? 1 : 0, ...BB.map((b) => (r.birthYear >= b && r.birthYear < b + 20 ? 1 : 0)),
  r.wedYear < 1500 ? 1 : 0, ...WB.map((b) => (r.wedYear >= b && r.wedYear < b + 10 ? 1 : 0)),
  r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10,
  r.ageA / 10, r.ageB / 10, (r.ageA / 10) ** 2, (r.ageB / 10) ** 2,
];

// ── astrological feature families ───────────────────────────────────────────────────────────────
const pairs = (u, v) => { const o = []; for (let j = 0; j < 10; j++) for (let k = 0; k < 10; k++) { const d = (u[j] - v[k]) * D2R; o.push(Math.cos(d), Math.sin(d)); } return o; };
const diag = (u, v) => { const o = []; for (let j = 0; j < 10; j++) { const d = (u[j] - v[j]) * D2R; o.push(Math.cos(d), Math.sin(d)); } return o; };
/** Natal synastry: the two charts against each other. What every earlier model used. */
const natal = (r) => pairs(r.la, r.lb);
/** Transits to natal: the wedding-day sky against each partner's birth sky, same body to same body. */
const transitDiag = (r) => [...diag(r.lw, r.la), ...diag(r.lw, r.lb)];
/** Transits, full cross-matrix, wedding against each partner. */
const transitCross = (r) => [...pairs(r.lw, r.la), ...pairs(r.lw, r.lb)];
/** The wedding chart's own internal aspects — the 45 unique body pairs on the day. */
const wedChart = (r) => { const o = []; for (let j = 0; j < 10; j++) for (let k = j + 1; k < 10; k++) { const d = (r.lw[j] - r.lw[k]) * D2R; o.push(Math.cos(d), Math.sin(d)); } return o; };
const everything = (r) => [...natal(r), ...transitDiag(r), ...wedChart(r)];

/** Replace each feature by the part the date design cannot predict. Projection fitted on TRAIN only. */
function orthogonalise(featureFn) {
  const E = (r) => Float64Array.from([1, ...DATES(r)]);
  const Etr = TR.map(E);
  const p = featureFn(TR[0]).length;
  const proj = [];
  for (let j = 0; j < p; j++) proj.push(ridgeFit(Etr, Float64Array.from(TR.map((r) => featureFn(r)[j])), 1e-3));
  return (r) => { const f = featureFn(r), e = E(r); return f.map((v, j) => v - dotf(proj[j], e)); };
}

const RIDGES = [0.3, 1, 3, 10, 30, 100];
function run(name, fn) {
  const build = (r) => Float64Array.from([1, ...fn(r)]);
  const X = TR.map(build), y = Float64Array.from(TR.map((r) => r.y));
  let best = null;
  for (const ridge of RIDGES) {
    let hit = 0;
    for (let k = 0; k < 5; k++) {
      const inn = TR.filter((_, i) => i % 5 !== k), out = TR.filter((_, i) => i % 5 === k);
      const w = fitLogistic(inn.map(build), Float64Array.from(inn.map((r) => r.y)), ridge);
      hit += out.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === r.y).length;
    }
    if (!best || hit > best.hit) best = { hit, ridge };
  }
  const w = fitLogistic(X, y, best.ridge);
  const hit = (set) => set.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === r.y).length;
  const tr = hit(TR) / TR.length, te = hit(TE) / TE.length;
  console.log(`  ${name.padEnd(54)} ${String(X[0].length - 1).padStart(4)}   ${(100 * tr).toFixed(2)}%   ${(100 * te).toFixed(2)}%`);
  return te;
}

console.log(`\n  model                                                  cols   TRAIN     TEST`);
console.log(`  ── the plain encoding of the three dates ──`);
const base = run("birth era + wedding era + age gap + ages at marriage", DATES);
console.log(`  ── astrology, raw ──`);
run("natal synastry (10x10)", natal);
run("TRANSITS to natal, diagonal (wedding vs each birth)", transitDiag);
run("TRANSITS to natal, full cross-matrix", transitCross);
run("the wedding chart's own aspects", wedChart);
const allRaw = run("natal + transits + wedding chart", everything);
console.log(`  ── astrology, orthogonalised to the three dates ──`);
const oNatal = run("natal synastry, ORTHOGONALISED", orthogonalise(natal));
const oTransit = run("transits to natal, ORTHOGONALISED", orthogonalise(transitDiag));
const oWed = run("wedding chart, ORTHOGONALISED", orthogonalise(wedChart));
const oAll = run("everything, ORTHOGONALISED", orthogonalise(everything));
console.log(`  ── the two together ──`);
run("everything + the plain date encoding", (r) => [...everything(r), ...DATES(r)]);
console.log(`  ${"the coin".padEnd(54)}   —       —       50.00%`);

// ── the era-preserving null ─────────────────────────────────────────────────────────────────────
console.log(`\n  ERA-PRESERVING NULL — partners shuffled only within a WEDDING decade`);
{
  const NPERM = 30;
  const groups = new Map();
  for (const r of data) { const d = Math.floor(r.wedYear / 10); (groups.get(d) ?? groups.set(d, []).get(d)).push(r); }
  const realB = data.map((r) => r.lb);
  const fn = orthogonalise(everything);
  const build = (r) => Float64Array.from([1, ...fn(r)]);
  const score = () => {
    const w = fitLogistic(TR.map(build), Float64Array.from(TR.map((r) => r.y)), 10);
    return TE.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === r.y).length / TE.length;
  };
  const real = score();
  const nulls = [];
  for (let p = 0; p < NPERM; p++) {
    for (const [, g] of groups) { const perm = shuffle(g.map((r) => r.lb)); g.forEach((r, i) => { r.lb = perm[i]; }); }
    nulls.push(score());
  }
  data.forEach((r, i) => { r.lb = realB[i]; });
  nulls.sort((a, b) => a - b);
  const above = nulls.filter((v) => v >= real).length;
  console.log(`    real ${(100 * real).toFixed(2)}%   null median ${(100 * nulls[NPERM >> 1]).toFixed(2)}%   95th ${(100 * nulls[Math.floor(NPERM * 0.95)]).toFixed(2)}%   p = ${((above + 1) / (NPERM + 1)).toFixed(3)}`);
}

// ── power ───────────────────────────────────────────────────────────────────────────────────────
{
  const n = TE.length, se = Math.sqrt(0.25 / n);
  console.log(`\n  POWER — test n = ${n.toLocaleString()}, se = ${(100 * se).toFixed(2)} points`);
  console.log(`    detectable at 80% power, 5% level: ${(100 * (0.5 + 2.8 * se)).toFixed(2)}%  (a lift of ${(100 * 2.8 * se).toFixed(2)} points)`);
  console.log(`    the plain three-date encoding    : ${(100 * base).toFixed(2)}%`);
  console.log(`    all astrology, raw               : ${(100 * allRaw).toFixed(2)}%`);
  console.log(`    all astrology, orthogonalised    : ${(100 * oAll).toFixed(2)}%`);
}
