/**
 * aspects.mjs — give the model the whole aspect vocabulary and see whether it finds anything.
 *
 * ── Why harmonics ───────────────────────────────────────────────────────────────────────────────
 *
 * Everything so far used sin(delta) and cos(delta) — the FIRST harmonic — and a first harmonic
 * physically cannot represent an aspect doctrine. cos(delta) cannot tell a sextile at 60 degrees from
 * a trine at 120 (it gives +0.5 and -0.5, opposite signs for two aspects the tradition calls the same
 * thing), and it cannot make 0 and 180 behave alike. Aspects are divisions of the circle by small
 * whole numbers, which is to say they live in the HIGHER harmonics:
 *
 *     cos(2·delta)  period 180 deg — THE SQUARE HARMONIC. Peaks at the conjunction and opposition,
 *                   troughs at the two squares. This is the one that makes 0 and 180 alike and 90
 *                   their opposite, and it is exactly the cos(2*phi) that the aspect-stability paper
 *                   turns out to be built on.
 *     cos(3·delta)  period 120 deg — the trines.
 *     cos(4·delta)  period  90 deg — the squares as a four-fold division.
 *     cos(6·delta)  period  60 deg — the sextiles.
 *     cos(12·delta) period  30 deg — the whole-sign grid, every aspect the tradition names.
 *
 * So the honest test is not to guess which aspects matter. It is to fit a FOURIER SERIES in the angle
 * difference, one for every body:
 *
 *     logit  =  b  +  SUM_j SUM_{n=1..N} [ a_jn·cos(n·delta_j) + c_jn·sin(n·delta_j) ]
 *
 * A Fourier series to order N can represent ANY function of the aspect angle with features no finer
 * than 360/N degrees. At N=12 that is every whole-sign aspect, every soft/hard grading, any orb, and
 * every weighting scheme anybody has ever proposed — simultaneously, with the weights fitted from the
 * data rather than assumed. If the aspect doctrine carries information about how long a marriage
 * lasts, this basis will find it. If this finds nothing, no aspect scheme expressible as a function of
 * the angle can do better.
 *
 * ── And the literal encoding too ────────────────────────────────────────────────────────────────
 *
 * Alongside the Fourier basis, the traditional form: a Gaussian bump on each of the seven Ptolemaic
 * aspects (0, 30, 60, 90, 120, 150, 180) with a settable orb. This is how an astrologer would write
 * it, and it is a strict subset of what the Fourier basis can express — worth running because it is
 * the actual claim, and because a narrow orb is sparser than a low-order series.
 *
 * ── The link ────────────────────────────────────────────────────────────────────────────────────
 *
 * Reported under BOTH links, since "square model" can mean either:
 *   · the logistic link, for comparability with every accuracy in this study;
 *   · the squared link mu = (b + sum)^2 as originally specified, which for a balanced binary target
 *     is fitted as least squares and thresholded at the class boundary.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/aspects.mjs <dataset.json>
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const norm360 = (x) => ((x % 360) + 360) % 360;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const INNER = PLANETS.slice(0, 7);
const OUTERS = new Set(["Uranus", "Neptune", "Pluto"]);

let SEED = 20260805;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };

// ── linear algebra, typed for speed: these designs run to a few hundred columns ──────────────────
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

/** Logistic regression by IRLS. Ridge is meaningful here: a Fourier basis to order 12 is nearly
 *  collinear across neighbouring harmonics, and without it the Hessian is numerically singular. */
function fitLogistic(X, y, { iters = 6, ridge = 1.0 } = {}) {
  const nRows = X.length, p = X[0].length;
  const w = new Float64Array(p);
  let pos = 0;
  for (const v of y) pos += v;
  w[0] = Math.log((pos + 1) / (nRows - pos + 1));
  const A = new Float64Array(p * p), g = new Float64Array(p);
  for (let it = 0; it < iters; it++) {
    A.fill(0); g.fill(0);
    for (let i = 0; i < nRows; i++) {
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

/** Least squares of sqrt-scaled target for the squared link mu = (Xw)^2, then Gauss-Newton. */
function fitSquared(X, y, ridge = 1.0) {
  const nRows = X.length, p = X[0].length;
  const A = new Float64Array(p * p), g = new Float64Array(p);
  const build = (target, weightFn, w0) => {
    A.fill(0); g.fill(0);
    for (let i = 0; i < nRows; i++) {
      const xi = X[i], sc = weightFn ? weightFn(dotf(w0, xi)) : 1, t = target[i] * (weightFn ? 1 : 1);
      for (let j = 0; j < p; j++) {
        const xj = xi[j] * sc;
        if (xj === 0) continue;
        g[j] += xj * t;
        for (let k = j; k < p; k++) A[j * p + k] += xj * xi[k] * sc;
      }
    }
    for (let j = 0; j < p; j++) { for (let k = 0; k < j; k++) A[j * p + k] = A[k * p + j]; A[j * p + j] += ridge; }
    return solveSym(A, g, p);
  };
  let w = build(y.map(Math.sqrt), null, null);
  for (let it = 0; it < 3; it++) {
    const r = new Float64Array(nRows);
    for (let i = 0; i < nRows; i++) { const u = dotf(w, X[i]); r[i] = y[i] - u * u; }
    A.fill(0); g.fill(0);
    for (let i = 0; i < nRows; i++) {
      const xi = X[i], u = dotf(w, xi), s = 2 * u;
      for (let j = 0; j < p; j++) {
        const xj = s * xi[j];
        if (xj === 0) continue;
        g[j] += xj * r[i];
        for (let k = j; k < p; k++) A[j * p + k] += xj * s * xi[k];
      }
    }
    for (let j = 0; j < p; j++) { for (let k = 0; k < j; k++) A[j * p + k] = A[k * p + j]; A[j * p + j] += ridge; }
    const step = solveSym(A, g, p);
    const err = (ww) => { let e = 0; for (let i = 0; i < nRows; i++) { const u = dotf(ww, X[i]); e += (y[i] - u * u) ** 2; } return e; };
    const next = new Float64Array(p);
    for (let j = 0; j < p; j++) next[j] = w[j] + step[j];
    if (err(next) < err(w)) w = next; else break;
  }
  return w;
}

// ── the data ────────────────────────────────────────────────────────────────────────────────────
const raw = JSON.parse(readFileSync(process.argv[2] ?? "./research/data/dataset.json", "utf8"));
const parseDate = (iso) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};
const jdOf = (iso) => { const p = parseDate(iso); return p ? julianDay(p.y, p.m, p.d, 12) : null; };

const rows = [];
for (const r of raw) {
  const f = parseDate(r.fDob), m = parseDate(r.mDob);
  if (!f || !m || f.y < 1800 || f.y > 2012 || m.y < 1800 || m.y > 2012) continue;
  if (r.fDob.endsWith("-01") || r.mDob.endsWith("-01")) continue;
  const fJd = julianDay(f.y, f.m, f.d, 12), mJd = julianDay(m.y, m.m, m.d, 12);
  const st = jdOf(r.start), en = [r.end, r.fDod, r.mDod].map(jdOf).filter((v) => v !== null);
  if (st === null || !en.length) continue;
  const dur = (Math.min(...en) - st) / 365.2425;
  if (dur <= 0 || dur > 80) continue;
  if ((st - fJd) / 365.2425 < 12 || (st - mJd) / 365.2425 < 12) continue;
  const fl = PLANETS.map((b) => siderealLongitude(b, fJd));
  const ml = PLANETS.map((b) => siderealLongitude(b, mJd));
  rows.push({
    father: r.father, mother: r.mother, duration: dur,
    fYear: f.y, mYear: m.y, gap: (fJd - mJd) / 365.2425,
    delta: fl.map((x, i) => norm360(x - ml[i])),
  });
}
const sortedDur = rows.map((r) => r.duration).sort((a, b) => a - b);
const CUT = sortedDur[sortedDur.length >> 1];
for (const r of rows) r.label = r.duration >= CUT ? 1 : 0;
const base = rows.reduce((s, r) => s + r.label, 0) / rows.length;

console.log(`\nASPECTS — did this marriage last ${CUT.toFixed(1)} years or longer?`);
console.log(`  ${rows.length.toLocaleString()} couples, ${(100 * base).toFixed(1)}% positive (balanced at the median, so the coin is 50%)`);

// ── the split: train / validate / test, grouped by person ────────────────────────────────────────
const side = new Map();
for (const r of rows) {
  let s = side.get(r.father) ?? side.get(r.mother);
  if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
  side.set(r.father, s); side.set(r.mother, s);
  r.side = s;
}
const TR = rows.filter((r) => r.side === "train"), VA = rows.filter((r) => r.side === "val"), TE = rows.filter((r) => r.side === "test");
console.log(`  ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} validate · ${TE.length.toLocaleString()} test (split by person)`);

// ── feature bases ───────────────────────────────────────────────────────────────────────────────
const ix = (bs) => bs.map((b) => PLANETS.indexOf(b));

/** Fourier series in the aspect angle, harmonics 1..N per body. */
const harmonics = (bodies, N) => {
  const I = ix(bodies);
  return (r) => {
    const out = [];
    for (const i of I) {
      const d = r.delta[i] * D2R;
      for (let n = 1; n <= N; n++) { out.push(Math.cos(n * d), Math.sin(n * d)); }
    }
    return out;
  };
};

/**
 * The traditional encoding: a Gaussian bump on each Ptolemaic aspect, with an orb.
 * An aspect is symmetric — 90 and 270 are the same square — so the bump is placed on the smaller of
 * the two arcs, which is what makes this a function of the ASPECT rather than of the direction.
 */
const ASPECTS = [0, 30, 60, 90, 120, 150, 180];
const orbBumps = (bodies, orb) => {
  const I = ix(bodies);
  return (r) => {
    const out = [];
    for (const i of I) {
      const d = r.delta[i], sep = d > 180 ? 360 - d : d;      // 0..180, the aspect angle proper
      for (const a of ASPECTS) out.push(Math.exp(-(((sep - a) / orb) ** 2)));
    }
    return out;
  };
};

const CONFIGS = [];
for (const N of [1, 2, 3, 4, 6, 12]) {
  CONFIGS.push({ name: `Fourier to order ${N}, 10 planets`, fn: harmonics(PLANETS, N), np: 10 * 2 * N });
  CONFIGS.push({ name: `Fourier to order ${N}, no outer planets`, fn: harmonics(INNER, N), np: 7 * 2 * N });
}
for (const orb of [4, 6, 8, 12]) {
  CONFIGS.push({ name: `Ptolemaic bumps, orb ${orb} deg, 10 planets`, fn: orbBumps(PLANETS, orb), np: 10 * 7 });
  CONFIGS.push({ name: `Ptolemaic bumps, orb ${orb} deg, no outer planets`, fn: orbBumps(INNER, orb), np: 7 * 7 });
}
// The single square harmonic on its own — the paper's cos(2*phi), nothing else.
CONFIGS.push({ name: `THE SQUARE HARMONIC cos(2d) alone, 10 planets`, fn: (r) => ix(PLANETS).map((i) => Math.cos(2 * r.delta[i] * D2R)), np: 10 });
CONFIGS.push({ name: `THE SQUARE HARMONIC cos(2d) alone, no outer planets`, fn: (r) => ix(INNER).map((i) => Math.cos(2 * r.delta[i] * D2R)), np: 7 });

// the baseline
const DECADES = [];
for (let y = 1800; y <= 2010; y += 10) DECADES.push(y);
const CONTROLS = (r) => {
  const t = (r.fYear + r.mYear) / 2;
  return [...DECADES.map((d) => (t >= d && t < d + 10 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];
};

const accLogit = (fn) => {
  const build = (r) => Float64Array.from([1, ...fn(r)]);
  const X = TR.map(build), y = Float64Array.from(TR.map((r) => r.label));
  const w = fitLogistic(X, y);
  const hit = (set) => set.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === r.label).length / set.length;
  return { val: hit(VA), test: hit(TE), fit: hit(TR), w, build };
};
const accSquared = (fn) => {
  // The squared link on a 0/1 target: fit mu = (Xw)^2 to the label, then call it positive above 0.5.
  const build = (r) => Float64Array.from([1, ...fn(r)]);
  const X = TR.map(build), y = Float64Array.from(TR.map((r) => r.label));
  const w = fitSquared(X, y);
  const hit = (set) => set.filter((r) => ((dotf(w, build(r)) ** 2 >= 0.5 ? 1 : 0) === r.label)).length / set.length;
  return { val: hit(VA), test: hit(TE), fit: hit(TR) };
};

const baseline = accLogit(CONTROLS);
console.log(`\n  BASELINE — era (22 decade flags) + age gap, no astrology`);
console.log(`    fit ${(100 * baseline.fit).toFixed(2)}%   validation ${(100 * baseline.val).toFixed(2)}%   test ${(100 * baseline.test).toFixed(2)}%`);

console.log(`\n  ── logistic link ──`);
console.log(`  model                                                  params    fit      val     test`);
const scored = [];
for (const c of CONFIGS) {
  const r = accLogit(c.fn);
  scored.push({ ...c, ...r });
  console.log(`  ${c.name.padEnd(52)} ${String(c.np).padStart(5)}   ${(100 * r.fit).toFixed(2)}%  ${(100 * r.val).toFixed(2)}%  ${(100 * r.test).toFixed(2)}%`);
}

console.log(`\n  ── the squared link, mu = (b + sum)^2, as originally specified ──`);
console.log(`  model                                                  params    fit      val     test`);
for (const c of CONFIGS.filter((c) => /order 2,|order 4,|order 12,|SQUARE HARMONIC|orb 6/.test(c.name))) {
  const r = accSquared(c.fn);
  console.log(`  ${c.name.padEnd(52)} ${String(c.np).padStart(5)}   ${(100 * r.fit).toFixed(2)}%  ${(100 * r.val).toFixed(2)}%  ${(100 * r.test).toFixed(2)}%`);
}

// ── the winner, once, on test ───────────────────────────────────────────────────────────────────
scored.sort((a, b) => b.val - a.val);
const win = scored[0];
console.log(`\n${"═".repeat(80)}`);
console.log(`  BEST BY VALIDATION: ${win.name} (${win.np} astrological parameters)`);
console.log(`    fit ${(100 * win.fit).toFixed(2)}%   validation ${(100 * win.val).toFixed(2)}%   TEST ${(100 * win.test).toFixed(2)}%`);
console.log(`    the baseline on the same test set: ${(100 * baseline.test).toFixed(2)}%`);
console.log(`    the coin: ${(100 * Math.max(base, 1 - base)).toFixed(2)}%`);
console.log(`    ${win.test > baseline.test ? "BEATS" : "DOES NOT BEAT"} the baseline, by ${(100 * (win.test - baseline.test)).toFixed(2)} points`);

// The inner-planet rows are the ones that matter: no outer planets means no calendar to read, so
// anything there is aspect information or nothing.
const innerBest = scored.filter((s) => /no outer/.test(s.name)).sort((a, b) => b.val - a.val)[0];
console.log(`\n  BEST WITH NO OUTER PLANETS — the only rows where a result could be about aspects`);
console.log(`  rather than about the calendar: ${innerBest.name}`);
console.log(`    fit ${(100 * innerBest.fit).toFixed(2)}%   validation ${(100 * innerBest.val).toFixed(2)}%   TEST ${(100 * innerBest.test).toFixed(2)}%   against a 50% coin`);
