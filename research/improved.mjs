/**
 * improved.mjs — the same question, asked properly.
 *
 * Everything before this judged astrology by one of two crude devices: DROP the outer planets, or put
 * era in the SAME linear model and see who wins. Both are blunt instruments.
 *
 *   Dropping Uranus, Neptune and Pluto removes the calendar leak and whatever genuine astrology those
 *   three carry, in one motion. A null result then means "no signal OR the signal lived in the bodies
 *   we deleted", and those are different claims.
 *
 *   Putting era alongside astrology in one linear fit lets them compete for shared variance. The
 *   coefficient astrology ends up with depends on the collinearity, not only on its own information.
 *
 * And one question was never asked at all: IF a small real effect existed, would this design see it?
 * Until that is answered, "no signal" and "underpowered" are the same sentence.
 *
 * ── The five changes ────────────────────────────────────────────────────────────────────────────
 *
 * 1. ORTHOGONALISATION INSTEAD OF ABLATION. Every astrological feature is regressed on the era design
 *    and replaced by its RESIDUAL. All ten bodies stay. What survives is, by construction, the part of
 *    each feature that the calendar cannot explain — so a model on residuals can only be reading
 *    something else. This is the exact version of what the outer-planet ablation was approximating.
 *
 * 2. FEATURES THAT CANNOT LEAK THE CALENDAR EVEN IN PRINCIPLE. The Sun's sidereal longitude is very
 *    nearly the day of the year, and the difference of two people's days-of-year carries no century
 *    information whatsoever. Likewise each person's MOON PHASE — the Sun-to-Moon angle within one
 *    chart — cycles every 29.5 days. These are era-free by their period, not by our filtering.
 *
 * 3. AN ERA-PRESERVING PERMUTATION NULL. Shuffling partners at random destroys the era structure along
 *    with the pairing, so the null is easier than it should be. Shuffling only WITHIN a birth decade
 *    keeps the era distribution intact and tests the pairing alone.
 *
 * 4. NON-LINEARITY. Every model so far is linear in its features. Gradient-boosted stumps on the same
 *    features can find an interaction a logistic regression cannot — the tradition, after all, claims
 *    that combinations matter, which is an interaction claim.
 *
 * 5. A POWER ANALYSIS. With this many couples, what is the smallest true accuracy lift this design
 *    would detect four times out of five? Stated up front, so the null result below has a size.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/improved.mjs ./research/data-divorce
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
    for (let j = 0; j < p; j++) {
      const xj = xi[j];
      if (xj === 0) continue;
      g[j] += xj * yi;
      for (let k = j; k < p; k++) A[j * p + k] += xj * xi[k];
    }
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

/**
 * Gradient-boosted stumps on the logistic loss. Depth-1 trees, so each one splits on a single feature
 * at a single threshold — enough to find a monotone-or-not relationship in any one feature, and,
 * across many rounds, interactions between them.
 */
function fitBoost(X, y, { rounds = 200, rate = 0.1, bins = 16 } = {}) {
  const n = X.length, p = X[0].length;
  const base = Math.log((y.reduce((s, v) => s + v, 0) + 1) / (n - y.reduce((s, v) => s + v, 0) + 1));
  const F = new Float64Array(n).fill(base);
  const trees = [];
  // Pre-bin every feature once: candidate thresholds are quantiles, so the search is O(bins) per feature.
  const thresholds = [];
  for (let j = 0; j < p; j++) {
    const col = X.map((r) => r[j]).sort((a, b) => a - b);
    const th = [];
    for (let q = 1; q < bins; q++) th.push(col[Math.floor(q * n / bins)]);
    thresholds.push([...new Set(th)]);
  }
  for (let t = 0; t < rounds; t++) {
    const g = new Float64Array(n), h = new Float64Array(n);
    for (let i = 0; i < n; i++) { const mu = sigma(F[i]); g[i] = y[i] - mu; h[i] = Math.max(mu * (1 - mu), 1e-6); }
    let best = null;
    for (let j = 0; j < p; j++) {
      for (const th of thresholds[j]) {
        let gl = 0, hl = 0, gr = 0, hr = 0;
        for (let i = 0; i < n; i++) {
          if (X[i][j] <= th) { gl += g[i]; hl += h[i]; } else { gr += g[i]; hr += h[i]; }
        }
        if (hl < 1e-6 || hr < 1e-6) continue;
        const gain = (gl * gl) / (hl + 1) + (gr * gr) / (hr + 1);
        if (!best || gain > best.gain) best = { gain, j, th, vl: gl / (hl + 1), vr: gr / (hr + 1) };
      }
    }
    if (!best) break;
    trees.push(best);
    for (let i = 0; i < n; i++) F[i] += rate * (X[i][best.j] <= best.th ? best.vl : best.vr);
  }
  return { base, rate, trees };
}
const boostPredict = (m, x) => {
  let F = m.base;
  for (const t of m.trees) F += m.rate * (x[t.j] <= t.th ? t.vl : t.vr);
  return sigma(F);
};

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
  if (r.aDob.endsWith("-01-01") || r.bDob.endsWith("-01-01")) continue;
  let ja = julianDay(A.y, A.m, A.d, 12), jb = julianDay(B.y, B.m, B.d, 12), ya = A.y, yb = B.y;
  let pa = r.a, pb = r.b;
  if (jb < ja) { [ja, jb] = [jb, ja]; [pa, pb] = [pb, pa]; [ya, yb] = [yb, ya]; }
  const la = PLANETS.map((x) => siderealLongitude(x, ja)), lb = PLANETS.map((x) => siderealLongitude(x, jb));
  // Day of year: era-free by construction, and very nearly the Sun's own position.
  const doy = (d) => { const p = parseDate(d); const j = julianDay(p.y, 1, 1, 12); return (julianDay(p.y, p.m, p.d, 12) - j) / 365.2425 * 360; };
  const doyA = doy(ja === julianDay(A.y, A.m, A.d, 12) ? r.aDob : r.bDob);
  const doyB = doy(ja === julianDay(A.y, A.m, A.d, 12) ? r.bDob : r.aDob);
  // Moon phase within each chart: the Sun-to-Moon angle. A 29.5-day cycle carries no century.
  const phaseA = ((la[1] - la[0]) % 360 + 360) % 360;
  const phaseB = ((lb[1] - lb[0]) % 360 + 360) % 360;
  rows.push({
    a: pa, b: pb, y: r.y, year: (ya + yb) / 2, gap: (jb - ja) / YR,
    la, lb, doyA, doyB, phaseA, phaseB,
  });
}
SEED = 20260807;
const posR = rows.filter((r) => r.y === 1), negR = rows.filter((r) => r.y === 0);
const K = Math.min(posR.length, negR.length);
const data = shuffle([...shuffle(posR).slice(0, K), ...shuffle(negR).slice(0, K)]);

console.log(`\nASKING IT PROPERLY — ${data.length.toLocaleString()} couples, ${K.toLocaleString()} of each class, coin 50.00%`);

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

// ── the era design, and the orthogonaliser ──────────────────────────────────────────────────────
const BINS = [];
for (let y = 1500; y <= 2000; y += 20) BINS.push(y);
const ERA = (r) => [r.year < 1500 ? 1 : 0, ...BINS.map((b) => (r.year >= b && r.year < b + 20 ? 1 : 0)),
  r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];

/**
 * Replace each astrological feature by the part of it the era design cannot predict.
 *
 * The projection is FITTED ON THE TRAINING SET ONLY and then applied to both, so no test information
 * leaks through the orthogonalisation. After this, a model on the residuals cannot be reading the
 * calendar, because the calendar's linear span has been subtracted out of every column.
 */
function orthogonalise(featureFn) {
  const E = (r) => Float64Array.from([1, ...ERA(r)]);
  const Etr = TR.map(E);
  const p = featureFn(TR[0]).length;
  const projections = [];
  for (let j = 0; j < p; j++) {
    projections.push(ridgeFit(Etr, Float64Array.from(TR.map((r) => featureFn(r)[j])), 1e-3));
  }
  return (r) => {
    const f = featureFn(r), e = E(r);
    return f.map((v, j) => v - dotf(projections[j], e));
  };
}

// ── feature families ────────────────────────────────────────────────────────────────────────────
const crossH1 = (r) => { const o = []; for (let j = 0; j < 10; j++) for (let k = 0; k < 10; k++) { const d = (r.la[j] - r.lb[k]) * D2R; o.push(Math.cos(d), Math.sin(d)); } return o; };
const diagH1 = (r) => { const o = []; for (let j = 0; j < 10; j++) { const d = (r.la[j] - r.lb[j]) * D2R; o.push(Math.cos(d), Math.sin(d)); } return o; };
/** Era-free by period: day-of-year difference and each partner's moon phase, with harmonics. */
const eraFree = (r) => {
  const dd = (r.doyA - r.doyB) * D2R, dp = (r.phaseA - r.phaseB) * D2R;
  const o = [];
  for (let n = 1; n <= 4; n++) o.push(Math.cos(n * dd), Math.sin(n * dd), Math.cos(n * dp), Math.sin(n * dp));
  for (const v of [r.doyA, r.doyB, r.phaseA, r.phaseB]) o.push(Math.cos(v * D2R), Math.sin(v * D2R));
  return o;
};

const RIDGES = [0.3, 1, 3, 10, 30, 100];
function run(name, featureFn, { boost = false } = {}) {
  const build = (r) => Float64Array.from([1, ...featureFn(r)]);
  const X = TR.map(build), y = Float64Array.from(TR.map((r) => r.y));
  let acc;
  if (boost) {
    const m = fitBoost(X, y);
    const hit = (set) => set.filter((r) => (boostPredict(m, build(r)) >= 0.5 ? 1 : 0) === r.y).length;
    acc = [hit(TR) / TR.length, hit(TE) / TE.length];
  } else {
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
    acc = [hit(TR) / TR.length, hit(TE) / TE.length];
  }
  console.log(`  ${name.padEnd(56)} ${String(X[0].length - 1).padStart(4)}   ${(100 * acc[0]).toFixed(2)}%   ${(100 * acc[1]).toFixed(2)}%`);
  return acc[1];
}

console.log(`\n1 · ORTHOGONALISED — every feature stripped of everything the era design can predict`);
console.log(`  model                                                    cols   TRAIN     TEST`);
run("era + age gap alone (the reference)", ERA);
const rawCross = run("full 10x10 synastry, RAW", crossH1);
const orthCross = run("full 10x10 synastry, ORTHOGONALISED to era", orthogonalise(crossH1));
const orthDiag = run("diagonal synastry, ORTHOGONALISED to era", orthogonalise(diagH1));
console.log(`  → orthogonalising costs ${(100 * (rawCross - orthCross)).toFixed(2)} points, from ${(100 * rawCross).toFixed(2)}% to ${(100 * orthCross).toFixed(2)}%`);

console.log(`\n2 · ERA-FREE BY CONSTRUCTION — day-of-year and moon phase, periods of a year or a month`);
const efAcc = run("day-of-year + moon phase, harmonics to 4", eraFree);
run("... and orthogonalised as well, for good measure", orthogonalise(eraFree));

console.log(`\n3 · NON-LINEAR — boosted stumps, which can find interactions a logistic fit cannot`);
run("full 10x10 synastry, RAW, boosted", crossH1, { boost: true });
run("full 10x10 synastry, ORTHOGONALISED, boosted", orthogonalise(crossH1), { boost: true });
run("era + age gap, boosted", ERA, { boost: true });
run("day-of-year + moon phase, boosted", eraFree, { boost: true });

// ── 4 · the era-preserving permutation null ─────────────────────────────────────────────────────
console.log(`\n4 · ERA-PRESERVING NULL — partners shuffled only WITHIN a birth decade`);
{
  const NPERM = 40;
  const decade = (r) => Math.floor(r.year / 10);
  const groups = new Map();
  for (const r of data) { const d = decade(r); (groups.get(d) ?? groups.set(d, []).get(d)).push(r); }
  const realB = data.map((r) => r.lb);
  const fn = orthogonalise(crossH1);
  const build = (r) => Float64Array.from([1, ...fn(r)]);
  const score = () => {
    const w = fitLogistic(TR.map(build), Float64Array.from(TR.map((r) => r.y)), 10);
    return TE.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === r.y).length / TE.length;
  };
  const real = score();
  const nulls = [];
  for (let p = 0; p < NPERM; p++) {
    for (const [, g] of groups) {
      const perm = shuffle(g.map((r) => r.lb));
      g.forEach((r, i) => { r.lb = perm[i]; });
    }
    nulls.push(score());
  }
  data.forEach((r, i) => { r.lb = realB[i]; });
  nulls.sort((a, b) => a - b);
  const above = nulls.filter((v) => v >= real).length;
  console.log(`  orthogonalised synastry: real ${(100 * real).toFixed(2)}%   null median ${(100 * nulls[NPERM >> 1]).toFixed(2)}%` +
    `   95th ${(100 * nulls[Math.floor(NPERM * 0.95)]).toFixed(2)}%   p = ${((above + 1) / (NPERM + 1)).toFixed(3)}`);
  console.log(`  A within-decade shuffle keeps the era distribution and destroys only the pairing, so this`);
  console.log(`  null is the hard one: beating it means the model knows something about WHO is with WHOM.`);
}

// ── 5 · power ───────────────────────────────────────────────────────────────────────────────────
console.log(`\n5 · POWER — what could this design have detected?`);
{
  const n = TE.length;
  // A binomial test of accuracy against 0.5: sd of the estimate is sqrt(0.25/n).
  const se = Math.sqrt(0.25 / n);
  const mde80 = 0.5 + (1.96 + 0.84) * se;     // 5% two-sided, 80% power
  const mde50 = 0.5 + 1.96 * se;
  console.log(`  test set n = ${n.toLocaleString()}, standard error of an accuracy estimate = ${(100 * se).toFixed(2)} points`);
  console.log(`  smallest accuracy detectable at 80% power, 5% level : ${(100 * mde80).toFixed(2)}%  (a lift of ${(100 * (mde80 - 0.5)).toFixed(2)} points)`);
  console.log(`  merely significant at the 5% level                  : ${(100 * mde50).toFixed(2)}%  (a lift of ${(100 * (mde50 - 0.5)).toFixed(2)} points)`);
  console.log(`  observed, era-free features                        : ${(100 * efAcc).toFixed(2)}%`);
  console.log(`  observed, orthogonalised synastry                  : ${(100 * orthCross).toFixed(2)}%`);
  console.log(`\n  So this design would reliably catch a true effect worth ${(100 * (mde80 - 0.5)).toFixed(1)} accuracy points or more.`);
  console.log(`  Anything smaller than that could be real and still invisible here — which is the honest`);
  console.log(`  limit of the claim, and it is a limit on the DATA, not on the model.`);
}
