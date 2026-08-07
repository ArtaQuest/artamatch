/**
 * paper-model.mjs — the two-phase stability model of Ashrafnejad (2026), used as a predictor.
 *
 * ── WHAT THE PAPER CLAIMS, AND WHAT THIS TESTS ──────────────────────────────────────────────────
 *
 * The paper is explicit, in its own acknowledgements: "it makes no claim about astrology's predictive
 * validity." It argues that the aspect doctrine has an internal cyclical structure — that a single
 * cos(2*phi) wave reproduces the traditional soft/hard grading and forces a fair twelve-sign game — and
 * that is a claim about the doctrine's shape, not about people. Running it against marriage outcomes
 * therefore tests something the paper does not assert. Whatever the numbers below say, they neither
 * confirm nor refute the paper's actual argument.
 *
 * ── THE MODEL, RECONSTRUCTED AND VERIFIED ────────────────────────────────────────────────────────
 *
 * Sign k -> phase theta = 2*pi*k/12.  For a pair, phi = theta_them - theta_you.
 *
 *     tau   = cos(2*phi)            the sum of the two growth rates   (trace)
 *     delta = 0.75 + cos(2*phi)     their product                     (determinant)
 *     l     = sin(phi)              the lead: who is ahead
 *
 *     delta < 0                 ->  CONTEST   (a saddle; only the square, 90 degrees)
 *     delta > 0 and tau < 0     ->  WIN-WIN   (sextile, trine)
 *     delta > 0 and tau > 0     ->  LOSE-LOSE (conjunction, semisextile, quincunx, opposition)
 *     in a contest the side with l > 0 wins.
 *
 * The reward scale is not stated outright but is forced by two numbers the paper does give: 48 win-win,
 * 24 contest and 72 lose-lose cells of 144, and "about -1/6 of a point a round" for even play. Solving
 * 48w + 0 + 72l = -24 with w = +1 gives l = -1. So Win-Win = +1, Lose-Lose = -1, Contest = +1 to the
 * winner and -1 to the loser. Checked: this reconstruction reproduces Table 1 aspect for aspect, the
 * 48/24/72 split, the -1/6 mean, and "four win-wins, one win, one loss, six lose-loses" from any sign.
 *
 * ── ONE THING THAT MATTERS FOR APPLYING IT ───────────────────────────────────────────────────────
 *
 * The model is defined on WHOLE SIGNS — twelve discrete phases, 30 degrees apart — not on continuous
 * longitudes. So a body's position is quantised to its sign before phi is formed. That is the paper's
 * actual object, and it has a consequence worth stating in advance: quantising to 30-degree bins throws
 * away the fine angular resolution in which the calendar hides. Everything the earlier models in this
 * study were exploiting was that resolution. A sign-level model cannot read the era off Pluto, because
 * Pluto sits in one sign for twenty years.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/paper-model.mjs ./research/data-divorce
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const CLASSICAL = PLANETS.slice(0, 7);
const YR = 365.2425;
const DIR = process.argv[2] ?? "./research/data-divorce";

let SEED = 20260807;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };

// ── the paper's model ───────────────────────────────────────────────────────────────────────────
const signOf = (lonDeg) => Math.floor((((lonDeg % 360) + 360) % 360) / 30);        // 0..11
const phiOf = (signA, signB) => 30 * ((((signB - signA) % 12) + 12) % 12);          // degrees, 0..330
const tauOf = (phi) => Math.cos(2 * phi * D2R);
const deltaOf = (phi) => 0.75 + Math.cos(2 * phi * D2R);
const leadOf = (phi) => Math.sin(phi * D2R);
/** +1 Win-Win, -1 Lose-Lose, +/-1 in a contest by the lead, 0 when a contest cannot be decided. */
const rewardOf = (phi) => {
  if (deltaOf(phi) < 0) { const l = leadOf(phi); return l > 0 ? 1 : l < 0 ? -1 : 0; }
  return tauOf(phi) < 0 ? 1 : -1;
};
const CLASS = (phi) => (deltaOf(phi) < 0 ? 2 : tauOf(phi) < 0 ? 0 : 1);            // 0 WW, 1 LL, 2 Contest

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
      for (let j = 0; j < p; j++) {
        const xj = xi[j];
        if (xj === 0) continue;
        g[j] += xj * r;
        const wx = wt * xj;
        for (let k = j; k < p; k++) A[j * p + k] += wx * xi[k];
      }
    }
    for (let j = 0; j < p; j++) { for (let k = 0; k < j; k++) A[j * p + k] = A[k * p + j]; A[j * p + j] += ridge; }
    const step = solveSym(A, g, p);
    let moved = 0;
    for (let j = 0; j < p; j++) { w[j] += step[j]; moved += Math.abs(step[j]); }
    if (moved < 1e-9) break;
  }
  return w;
}

// ── the data ────────────────────────────────────────────────────────────────────────────────────
const parseDate = (iso) => {
  const m = /^(-?\d{3,4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};
const raw = JSON.parse(readFileSync(`${DIR}/balanced-all-precisions.json`, "utf8"));
const rows = [];
for (const r of raw) {
  const A = parseDate(r.aDob), B = parseDate(r.bDob);
  if (!A || !B) continue;
  if (r.aDob.endsWith("-01-01") || r.bDob.endsWith("-01-01")) continue;   // 1 January placeholders
  let ja = julianDay(A.y, A.m, A.d, 12), jb = julianDay(B.y, B.m, B.d, 12);
  let pa = r.a, pb = r.b;
  if (jb < ja) { [ja, jb] = [jb, ja]; [pa, pb] = [pb, pa]; }              // older first
  rows.push({
    a: pa, b: pb, y: r.y, year: (A.y + B.y) / 2, gap: (jb - ja) / YR,
    sa: PLANETS.map((x) => signOf(siderealLongitude(x, ja))),
    sb: PLANETS.map((x) => signOf(siderealLongitude(x, jb))),
  });
}
// Re-balance after filtering, exactly as elsewhere in this study: the filter does not remove evenly.
SEED = 20260807;
const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const posR = rows.filter((r) => r.y === 1), negR = rows.filter((r) => r.y === 0);
const K = Math.min(posR.length, negR.length);
const data = shuffle([...shuffle(posR).slice(0, K), ...shuffle(negR).slice(0, K)]);

console.log(`\nTHE PAPER'S MODEL AS A PREDICTOR OF DIVORCE`);
console.log(`  ${data.length.toLocaleString()} couples, ${K.toLocaleString()} of each class — the coin is 50.00%`);
console.log(`  positions quantised to WHOLE SIGNS, as the paper's model requires`);

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

// ── the paper's quantities as features ──────────────────────────────────────────────────────────
const idxOf = (bs) => bs.map((b) => PLANETS.indexOf(b));
const phiDiag = (r, j) => phiOf(r.sa[j], r.sb[j]);

/** The single score the paper's game defines: the mean reward over the bodies considered. */
const meanReward = (bs) => { const I = idxOf(bs); return (r) => [I.reduce((s, j) => s + rewardOf(phiDiag(r, j)), 0) / I.length]; };
/** Sun signs only — the model applied exactly as the tradition applies it, to two people's signs. */
const sunOnly = () => (r) => [rewardOf(phiOf(r.sa[0], r.sb[0]))];
/** One fitted weight per body on that body's reward. */
const rewardPerBody = (bs) => { const I = idxOf(bs); return (r) => I.map((j) => rewardOf(phiDiag(r, j))); };
/** The paper's three underlying quantities per body, unaggregated. */
const tauDeltaLead = (bs) => { const I = idxOf(bs); return (r) => I.flatMap((j) => { const p = phiDiag(r, j); return [tauOf(p), deltaOf(p), leadOf(p)]; }); };
/** The three-way class as one-hot per body — the classification with no reward scale imposed. */
const classOneHot = (bs) => { const I = idxOf(bs); return (r) => I.flatMap((j) => { const c = CLASS(phiDiag(r, j)); return [c === 0 ? 1 : 0, c === 1 ? 1 : 0, c === 2 ? 1 : 0]; }); };
/** The full cross-matrix of the paper's reward: every body of one against every body of the other. */
const rewardCross = (bs) => { const I = idxOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) o.push(rewardOf(phiOf(r.sa[j], r.sb[k]))); return o; }; };

const BINS = [];
for (let y = 1500; y <= 2000; y += 20) BINS.push(y);
const ERA = (r) => [r.year < 1500 ? 1 : 0, ...BINS.map((b) => (r.year >= b && r.year < b + 20 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];

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
  const hits = (set) => set.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === r.y).length;
  const hTR = hits(TR), hTE = hits(TE);
  console.log(`  ${name.padEnd(52)} ${String(X[0].length - 1).padStart(4)}   ${(100 * hTR / TR.length).toFixed(2)}%    ${(100 * hTE / TE.length).toFixed(2)}%   ${hTE}/${TE.length}`);
  return { w, hTE, n: TE.length };
}

console.log(`\n  model                                                cols   TRAIN     TEST     raw`);
run("the paper's score: mean reward, SUN SIGNS ONLY", sunOnly());
run("the paper's score: mean reward over 10 bodies", meanReward(PLANETS));
run("the paper's score: mean reward, classical 7", meanReward(CLASSICAL));
run("reward per body, 10 fitted weights", rewardPerBody(PLANETS));
run("reward per body, classical 7", rewardPerBody(CLASSICAL));
run("tau, delta and lead per body (30 features)", tauDeltaLead(PLANETS));
run("three-way class one-hot per body (30 features)", classOneHot(PLANETS));
run("reward over the full 10x10 cross-matrix", rewardCross(PLANETS));
run("reward cross-matrix, classical 7 (49)", rewardCross(CLASSICAL));
run("era + age gap, NO astrology", ERA);
run("the paper's cross-matrix + era + age gap", (r) => [...rewardCross(PLANETS)(r), ...ERA(r)]);
console.log(`  ${"the coin".padEnd(52)}   —       —        50.00%`);

// ── the score's own distribution, and its raw association with the outcome ───────────────────────
console.log(`\n  THE SCORE ITSELF — mean reward over 10 bodies, no fitting involved:`);
{
  const score = (r) => meanReward(PLANETS)(r)[0];
  const buckets = new Map();
  for (const r of data) {
    const b = Math.round(score(r) * 10) / 10;
    const e = buckets.get(b) ?? { n: 0, div: 0 };
    e.n++; e.div += r.y;
    buckets.set(b, e);
  }
  console.log(`    score   couples   divorced`);
  for (const b of [...buckets.keys()].sort((x, y) => x - y)) {
    const e = buckets.get(b);
    if (e.n < 30) continue;
    console.log(`    ${b.toFixed(1).padStart(5)}   ${String(e.n).padStart(7)}   ${(100 * e.div / e.n).toFixed(2)}%`);
  }
  const m = data.reduce((s, r) => s + score(r), 0) / data.length;
  const my = data.reduce((s, r) => s + r.y, 0) / data.length;
  let num = 0, dx = 0, dy = 0;
  for (const r of data) { num += (score(r) - m) * (r.y - my); dx += (score(r) - m) ** 2; dy += (r.y - my) ** 2; }
  console.log(`    correlation of the paper's score with divorce: r = ${(num / Math.sqrt(dx * dy)).toFixed(5)}`);
  console.log(`    (a higher score is meant to mean a more harmonious pairing, so a real effect would be negative)`);
}
