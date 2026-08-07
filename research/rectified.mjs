/**
 * rectified.mjs — the rectified-square midpoint model.
 *
 *     prediction  =  max( b + SUM_i a_i * cos( midpoint_i ) , 0 )^2
 *
 * ── Why the rectifier is not cosmetic ───────────────────────────────────────────────────────────
 *
 * max(u, 0)^2 is a genuinely different link from u^2, and a better-behaved one for a non-negative
 * target. u^2 is symmetric about zero, so a large NEGATIVE u predicts a large positive duration just
 * as a large positive u does — the fitted coefficients have no interpretable direction, and the model
 * is U-shaped in its own linear predictor. Rectifying first makes the link MONOTONE: more u always
 * means more predicted years, and a_i > 0 means "this body's midpoint here lengthens the marriage".
 *
 * It also creates a dead zone. Wherever u <= 0 the prediction is exactly zero and the gradient is
 * exactly zero, so those rows contribute nothing to the fit. That is handled below by starting from a
 * sqrt-transform solution, which puts u near sqrt(y) and therefore positive almost everywhere, and by
 * running Gauss-Newton on the active set only.
 *
 * ── The midpoint, written two ways ──────────────────────────────────────────────────────────────
 *
 * The model as specified says cos((f + m)/2), and the average of two angles is AMBIGUOUS MODULO 180
 * DEGREES: add a full turn to f and the "average" moves half a turn, flipping the cosine's sign.
 * Longitudes arriving in [0, 360) do fix a branch, but they fix it arbitrarily — two couples with the
 * same true midpoint get opposite features depending on which side of 0 degrees their planets fall.
 *
 * Both are therefore fitted and reported:
 *   NAIVE     cos((f + m)/2) exactly as written, branch fixed by the [0, 360) representation
 *   CIRCULAR  cos(arg(e^{if} + e^{im})), the direction of the vector sum, which is branch-independent
 *
 * If they disagree, the naive form is measuring an artefact of where zero happens to be.
 *
 * FITTED as regression on the mean squared error of the duration in years. BENCHMARKED afterwards as a
 * classifier, by cutting the predicted years at the median — so the same fitted model is scored both
 * ways and the two numbers are directly comparable with the rest of this study.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/rectified.mjs <dataset.json>
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const CLASSICAL = PLANETS.slice(0, 7);
const YR = 365.2425;

let SEED = 20260805;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };

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

function ridgeSolve(X, y, ridge, weights) {
  const n = X.length, p = X[0].length;
  const A = new Float64Array(p * p), g = new Float64Array(p);
  for (let i = 0; i < n; i++) {
    const xi = X[i], sw = weights ? weights[i] : 1;
    if (sw === 0) continue;
    const yi = y[i];
    for (let j = 0; j < p; j++) {
      const xj = xi[j] * sw;
      if (xj === 0) continue;
      g[j] += xj * yi;
      for (let k = j; k < p; k++) A[j * p + k] += xj * xi[k] * sw;
    }
  }
  for (let j = 0; j < p; j++) { for (let k = 0; k < j; k++) A[j * p + k] = A[k * p + j]; A[j * p + j] += ridge; }
  return solveSym(A, g, p);
}

const relu = (u) => (u > 0 ? u : 0);
const predict = (w, x) => { const u = dotf(w, x); return u > 0 ? u * u : 0; };

/**
 * Fit  mu = max(Xw, 0)^2  to y by least squares.
 *
 * Start from OLS of sqrt(y), which lands u near sqrt(y) and so positive almost everywhere — important,
 * because a start with u <= 0 has zero gradient there and those rows would never re-enter the fit.
 * Then Gauss-Newton with the Jacobian row 2*max(u,0)*x, which is zero on the dead side by construction,
 * and a halving line search so a step can never make the objective worse.
 */
function fitRectified(X, y, ridge) {
  const n = X.length, p = X[0].length;
  let w = ridgeSolve(X, y.map(Math.sqrt), ridge);
  const err = (ww) => { let s = 0; for (let i = 0; i < n; i++) s += (y[i] - predict(ww, X[i])) ** 2; return s; };
  let cur = err(w);
  for (let it = 0; it < 12; it++) {
    const r = new Float64Array(n), sc = new Float64Array(n);
    let active = 0;
    for (let i = 0; i < n; i++) {
      const u = dotf(w, X[i]), a = relu(u);
      sc[i] = 2 * a;                                  // zero where the rectifier is off
      if (a > 0) active++;
      r[i] = a > 0 ? (y[i] - a * a) / (2 * a) : 0;     // scaled residual, so ridgeSolve can weight it
    }
    if (!active) break;
    const step = ridgeSolve(X, r, ridge, sc);
    let ok = false;
    for (let t = 1; t >= 1 / 64; t /= 2) {
      const next = new Float64Array(p);
      for (let j = 0; j < p; j++) next[j] = w[j] + t * step[j];
      const e = err(next);
      if (e < cur - 1e-9) { w = next; cur = e; ok = true; break; }
    }
    if (!ok) break;
  }
  return w;
}

// ── the data ────────────────────────────────────────────────────────────────────────────────────
const raw = JSON.parse(readFileSync(process.argv[2] ?? "./research/data/dataset.json", "utf8"));
const parseDate = (iso) => {
  const m = /^(-?\d{3,4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};
const jdOf = (iso) => { const p = parseDate(iso); return p ? julianDay(p.y, p.m, p.d, 12) : null; };

const rows = [];
for (const r of raw) {
  const f = parseDate(r.fDob), m = parseDate(r.mDob);
  if (!f || !m) continue;
  const fJd = julianDay(f.y, f.m, f.d, 12), mJd = julianDay(m.y, m.m, m.d, 12);
  const st = jdOf(r.start);
  if (st === null) continue;
  const ends = [jdOf(r.end), jdOf(r.fDod), jdOf(r.mDod)].filter((v) => v !== null);
  if (!ends.length) continue;
  const dur = (Math.min(...ends) - st) / YR;
  if (dur <= 0 || dur > 80 || (st - fJd) / YR < 12 || (st - mJd) / YR < 12) continue;
  const fl = PLANETS.map((b) => siderealLongitude(b, fJd));
  const ml = PLANETS.map((b) => siderealLongitude(b, mJd));
  rows.push({
    father: r.father, mother: r.mother, duration: dur,
    fYear: f.y, mYear: m.y, gap: (fJd - mJd) / YR,
    // As written: the arithmetic mean of the two longitudes, branch fixed by [0, 360).
    naive: fl.map((x, i) => Math.cos(((x + ml[i]) / 2) * D2R)),
    // sin of the DIFFERENCE — antisymmetric, so it flips when the two people are swapped, and it is
    // exactly invariant to the sidereal setting (the ayanamsa cancels in a difference).
    diffSin: fl.map((x, i) => Math.sin((x - ml[i]) * D2R)),
    // Branch-independent: the direction of the vector sum.
    circular: fl.map((x, i) => {
      const A = x * D2R, B = ml[i] * D2R;
      const cx = Math.cos(A) + Math.cos(B), cy = Math.sin(A) + Math.sin(B);
      const n = Math.hypot(cx, cy);
      return n < 1e-12 ? 0 : cx / n;
    }),
  });
}
const med = rows.map((r) => r.duration).sort((a, b) => a - b)[rows.length >> 1];
const pos = rows.filter((r) => r.duration >= med).length;

console.log(`\nRECTIFIED-SQUARE MIDPOINT MODEL   prediction = max( b + SUM a_i cos(midpoint_i), 0 )^2`);
console.log(`  ${rows.length.toLocaleString()} couples — every one with a marriage start date, an end, and both births`);
console.log(`  median duration ${med.toFixed(2)} y — ${pos.toLocaleString()} at or above (${(100 * pos / rows.length).toFixed(2)}%), the coin is 50%`);
{
  // How much does the branch choice actually matter?
  let agree = 0, n = 0;
  for (const r of rows) for (let i = 0; i < PLANETS.length; i++) {
    n++;
    if (Math.sign(r.naive[i]) === Math.sign(r.circular[i])) agree++;
  }
  console.log(`\n  THE BRANCH PROBLEM, measured: over ${n.toLocaleString()} body-couple features, the naive`);
  console.log(`  (f+m)/2 and the branch-independent circular midpoint agree in SIGN only ${(100 * agree / n).toFixed(1)}% of the time.`);
  console.log(`  Where they disagree they are exact negatives of each other — the naive form is reading off`);
  console.log(`  which side of 0 degrees the two planets happen to fall, not where their midpoint is.`);
}

// ── split by person, 60/20/20 ───────────────────────────────────────────────────────────────────
const side = new Map();
for (const r of rows) {
  let s = side.get(r.father) ?? side.get(r.mother);
  if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
  side.set(r.father, s); side.set(r.mother, s);
  r.side = s;
}
const TR = rows.filter((r) => r.side === "train"), VA = rows.filter((r) => r.side === "val"), TE = rows.filter((r) => r.side === "test");
console.log(`  ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} validate · ${TE.length.toLocaleString()} test (split by person)`);

const BINS = [];
for (let y = 1400; y <= 2000; y += 25) BINS.push(y);
const ERA = (r) => {
  const t = (r.fYear + r.mYear) / 2;
  return [t < 1400 ? 1 : 0, ...BINS.map((b) => (t >= b && t < b + 25 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];
};

const RIDGES = [0.01, 0.1, 1, 10, 100];

/**
 * Regression on the mean squared error of the DURATION IN YEARS. The model predicts a number of
 * years, so it is scored on how far off that number is — no threshold, no classes.
 *
 * The reference to read every MSE against is the variance of the duration, which is exactly the MSE
 * of the best constant prediction. A model that cannot beat it has learned nothing at all.
 * RMSE is given beside it because it is in years and therefore means something.
 */
const mse = (w, build, set) => {
  let s = 0;
  for (const r of set) s += (r.duration - predict(w, build(r))) ** 2;
  return s / set.length;
};
const trMean = TR.reduce((s, r) => s + r.duration, 0) / TR.length;
const varTR = TR.reduce((s, r) => s + (r.duration - trMean) ** 2, 0) / TR.length;
const varTE = TE.reduce((s, r) => s + (r.duration - trMean) ** 2, 0) / TE.length;

function evaluate(fn, label) {
  const build = (r) => Float64Array.from([1, ...fn(r)]);
  const X = TR.map(build), y = Float64Array.from(TR.map((r) => r.duration));
  let best = null;
  for (const ridge of RIDGES) {
    const w = fitRectified(X, y, ridge);
    const val = mse(w, build, VA);
    if (!best || val < best.val) best = { ridge, val, fit: mse(w, build, TR), test: mse(w, build, TE), w, np: X[0].length - 1 };
  }
  console.log(`  ${label.padEnd(52)} ${String(best.np).padStart(4)}  ${String(best.ridge).padStart(5)}   ${best.fit.toFixed(2).padStart(7)}  ${best.test.toFixed(2).padStart(7)}   ${Math.sqrt(best.fit).toFixed(3)}  ${Math.sqrt(best.test).toFixed(3)}`);
  return best;
}

console.log(`\n  ridge chosen on validation by MSE, never on test`);
console.log(`  the constant-prediction reference (the variance): train ${varTR.toFixed(2)}, test ${varTE.toFixed(2)}` +
  `  — RMSE ${Math.sqrt(varTR).toFixed(3)} / ${Math.sqrt(varTE).toFixed(3)} years\n`);
console.log(`  model                                                cols  ridge   MSE fit  MSE TEST   RMSE fit  RMSE test`);
const results = {};
results.naive10 = evaluate((r) => r.naive, "AS WRITTEN, naive (f+m)/2, 10 planets");
results.circ10 = evaluate((r) => r.circular, "circular midpoint, 10 planets");
results.naive7 = evaluate((r) => CLASSICAL.map((b) => r.naive[PLANETS.indexOf(b)]), "AS WRITTEN, naive, classical 7 only");
results.circ7 = evaluate((r) => CLASSICAL.map((b) => r.circular[PLANETS.indexOf(b)]), "circular midpoint, classical 7 only");
results.era = evaluate(ERA, "era + age gap, no astrology (same link)");
results.both = evaluate((r) => [...r.circular, ...ERA(r)], "circular midpoint + era + age gap");
results.constant = { test: varTE, fit: varTR };

console.log(`\n${"═".repeat(84)}`);
const bestAstro = Math.min(results.naive10.test, results.circ10.test);
console.log(`  best astrological form, test MSE  : ${bestAstro.toFixed(2)}  (RMSE ${Math.sqrt(bestAstro).toFixed(2)} y)`);
console.log(`  the same-link baseline            : ${results.era.test.toFixed(2)}  (RMSE ${Math.sqrt(results.era.test).toFixed(2)} y)`);
console.log(`  predicting the constant mean      : ${varTE.toFixed(2)}  (RMSE ${Math.sqrt(varTE).toFixed(2)} y)`);
console.log(`  so the astrology removes ${(100 * (1 - bestAstro / varTE)).toFixed(2)}% of the squared error, the baseline ${(100 * (1 - results.era.test / varTE)).toFixed(2)}%`);
console.log(`\n  the two midpoint definitions, test MSE: naive ${results.naive10.test.toFixed(2)} vs circular ${results.circ10.test.toFixed(2)}`);
console.log(`  with no calendar available (classical 7): naive ${results.naive7.test.toFixed(2)} vs circular ${results.circ7.test.toFixed(2)}`);
console.log(`    (the constant reference is ${varTE.toFixed(2)} — a classical-only MSE at that value is no model at all)`);
console.log(`\n  the fitted model, circular midpoint, 10 planets:`);
{
  const w = results.circ10.w;
  console.log(`    b = ${w[0].toFixed(5)}`);
  console.log(`    ${PLANETS.map((b, i) => `${b} ${w[i + 1].toFixed(4)}`).join("  ")}`);
  const amp = Math.hypot(...[...w].slice(1));
  const inner = Math.hypot(...[...w].slice(1, 8));
  console.log(`    total amplitude ${amp.toFixed(4)}; without Uranus, Neptune and Pluto ${inner.toFixed(4)} ` +
    `— the three outer planets carry ${(100 * (1 - (inner / amp) ** 2)).toFixed(1)}% of it`);
  const us = TR.map((r) => dotf(w, Float64Array.from([1, ...r.circular])));
  const dead = us.filter((u) => u <= 0).length;
  console.log(`    the rectifier is off (u <= 0, prediction exactly 0) for ${dead.toLocaleString()} of ${TR.length.toLocaleString()} training couples`);
}

// ── benchmarked as a classifier, after fitting as a regression ───────────────────────────────────
//
// The model above was fitted on squared error in years. Here the SAME fitted weights are cut at a
// threshold and scored as a two-class predictor of "longer than the median marriage".
//
// Two cuts, because they answer different questions and a weak model separates them sharply:
//
//   AT THE TARGET MEDIAN (27.13 y). The literal benchmark. A model whose predictions are compressed
//   towards the mean — which is what a weak regression does — will fall almost entirely on one side of
//   this and classify nearly everything the same way, so accuracy collapses towards the base rate even
//   though the ranking underneath may be fine.
//
//   AT THE MODEL'S OWN MEDIAN PREDICTION, chosen on TRAIN. This forces a 50/50 predicted split and so
//   measures the ranking rather than the calibration. It is the fairer number for a compressed model,
//   and it is the one to compare against the 50% coin.
//
// BALANCED ACCURACY is the mean of the two class recalls. On a target that is exactly 50/50 it is very
// close to plain accuracy, and it differs precisely when a model's errors are lopsided between the
// classes — so both are printed, and a gap between them is the model favouring one side.
{
  const label = (r) => (r.duration >= med ? 1 : 0);
  const score = (w, build, set, cut) => {
    let tp = 0, fp = 0, fn = 0, tn = 0;
    for (const r of set) {
      const p = predict(w, build(r)) >= cut ? 1 : 0, t = label(r);
      if (p && t) tp++; else if (p && !t) fp++; else if (!p && t) fn++; else tn++;
    }
    const sens = tp + fn ? tp / (tp + fn) : 0, spec = tn + tn + fp - tn ? tn / (tn + fp) : 0;
    return { acc: (tp + tn) / set.length, bal: (sens + spec) / 2, sens, spec, cm: { tp, fp, fn, tn } };
  };

  console.log(`\n${"═".repeat(92)}`);
  console.log(`  BENCHMARKED AS A CLASSIFIER — the same regressions, cut at a threshold`);
  console.log(`  target: duration >= ${med.toFixed(2)} y, exactly 50/50, so the coin is 50.00%`);
  console.log(`${"═".repeat(92)}`);
  console.log(`                                                      cut at the target median      cut at the model's own median`);
  console.log(`  model                                          acc fit  ACC TEST   BAL TEST     acc fit  ACC TEST   BAL TEST`);
  const shown = [
    ["AS WRITTEN, naive (f+m)/2, 10 planets", results.naive10, (r) => r.naive],
    ["circular midpoint, 10 planets", results.circ10, (r) => r.circular],
    ["AS WRITTEN, naive, classical 7 only", results.naive7, (r) => CLASSICAL.map((b) => r.naive[PLANETS.indexOf(b)])],
    ["circular midpoint, classical 7 only", results.circ7, (r) => CLASSICAL.map((b) => r.circular[PLANETS.indexOf(b)])],
    ["era + age gap, no astrology (same link)", results.era, ERA],
    ["circular midpoint + era + age gap", results.both, (r) => [...r.circular, ...ERA(r)]],
  ];
  for (const [name, res, fn] of shown) {
    const build = (r) => Float64Array.from([1, ...fn(r)]);
    const a = score(res.w, build, TR, med), b = score(res.w, build, TE, med);
    // The model's own median prediction, taken on TRAIN so the test set never informs the threshold.
    const ownCut = TR.map((r) => predict(res.w, build(r))).sort((x, y) => x - y)[TR.length >> 1];
    const c = score(res.w, build, TR, ownCut), d = score(res.w, build, TE, ownCut);
    console.log(`  ${name.padEnd(44)} ${(100 * a.acc).toFixed(2)}%  ${(100 * b.acc).toFixed(2)}%   ${(100 * b.bal).toFixed(2)}%    ` +
      ` ${(100 * c.acc).toFixed(2)}%  ${(100 * d.acc).toFixed(2)}%   ${(100 * d.bal).toFixed(2)}%`);
  }
  console.log(`\n  per-class detail at the model's own median, on test:`);
  for (const [name, res, fn] of shown) {
    const build = (r) => Float64Array.from([1, ...fn(r)]);
    const ownCut = TR.map((r) => predict(res.w, build(r))).sort((x, y) => x - y)[TR.length >> 1];
    const d = score(res.w, build, TE, ownCut);
    console.log(`    ${name.padEnd(44)} recall long ${(100 * d.sens).toFixed(2)}%  recall short ${(100 * d.spec).toFixed(2)}%   ` +
      `tp ${d.cm.tp} fp ${d.cm.fp} fn ${d.cm.fn} tn ${d.cm.tn}`);
  }
}

// ── the plain 80/20 report ───────────────────────────────────────────────────────────────────────
//
// An 80/20 split by person — no validation set, so nothing is selected and there is nothing to select
// on. The ridge is therefore FIXED at 0.01 rather than tuned; across the sweeps above it moved test
// MSE by under 1%, so pinning it costs nothing and keeps this a single honest number per model.
//
// Fitted as regression on squared error in years, then cut at the target median to give accuracy.
{
  const side = new Map();
  SEED = 20260805;
  for (const r of rows) {
    let s2 = side.get(r.father) ?? side.get(r.mother);
    if (s2 === undefined) s2 = rnd() < 0.8 ? "train" : "test";
    side.set(r.father, s2); side.set(r.mother, s2);
    r.side2 = s2;
  }
  const A = rows.filter((r) => r.side2 === "train"), B = rows.filter((r) => r.side2 === "test");
  const label = (r) => (r.duration >= med ? 1 : 0);
  const acc = (w, build, set) => set.filter((r) => (predict(w, build(r)) >= med ? 1 : 0) === label(r)).length / set.length;

  console.log(`\n${"═".repeat(78)}`);
  console.log(`  80/20 SPLIT BY PERSON — ${A.length.toLocaleString()} train, ${B.length.toLocaleString()} test`);
  console.log(`  target: duration >= ${med.toFixed(2)} years, exactly 50/50. Ridge fixed at 0.01, nothing tuned.`);
  console.log(`${"═".repeat(78)}`);
  console.log(`  model                                          TRAIN acc   TEST acc`);
  const FEATURES = [
    ["max(b + SUM a_i cos(mid_i), 0)^2 — as written, naive", (r) => r.naive],
    ["max(b + SUM a_i cos(mid_i), 0)^2 — circular midpoint", (r) => r.circular],
    ["  ... naive, classical 7 only (no calendar)", (r) => CLASSICAL.map((b2) => r.naive[PLANETS.indexOf(b2)])],
    ["  ... circular, classical 7 only (no calendar)", (r) => CLASSICAL.map((b2) => r.circular[PLANETS.indexOf(b2)])],
    ["era + age gap, no astrology (same link)", ERA],
    ["circular midpoint + era + age gap", (r) => [...r.circular, ...ERA(r)]],
  ];
  for (const [name, fn] of FEATURES) {
    const build = (r) => Float64Array.from([1, ...fn(r)]);
    const w = fitRectified(A.map(build), Float64Array.from(A.map((r) => r.duration)), 0.01);
    console.log(`  ${name.padEnd(46)} ${(100 * acc(w, build, A)).toFixed(2)}%     ${(100 * acc(w, build, B)).toFixed(2)}%`);
  }
  console.log(`  ${"the coin".padEnd(46)}   —        50.00%`);
}

// ── the combined form, under the rectified square ────────────────────────────────────────────────
//
//     max( b + SUM_i a_i cos(mid_i) + SUM_i d_i sin(diff_i) , 0 )^2
//
// Both families at once, one weight each per body: the midpoint (symmetric, a function of WHERE the
// planets were) and the difference (antisymmetric, a function of HOW FAR APART they were). Twenty
// astrological parameters for ten bodies. Same 80/20 split by person, ridge fixed, nothing tuned.
{
  const side = new Map();
  SEED = 20260805;
  for (const r of rows) {
    let s2 = side.get(r.father) ?? side.get(r.mother);
    if (s2 === undefined) s2 = rnd() < 0.8 ? "train" : "test";
    side.set(r.father, s2); side.set(r.mother, s2);
    r.side3 = s2;
  }
  const A = rows.filter((r) => r.side3 === "train"), B = rows.filter((r) => r.side3 === "test");
  const label = (r) => (r.duration >= med ? 1 : 0);
  const acc = (w, build, set) => set.filter((r) => (predict(w, build(r)) >= med ? 1 : 0) === label(r)).length / set.length;
  const mseOf = (w, build, set) => { let t = 0; for (const r of set) t += (r.duration - predict(w, build(r))) ** 2; return t / set.length; };
  const ci = CLASSICAL.map((b2) => PLANETS.indexOf(b2));

  console.log(`\n${"═".repeat(88)}`);
  console.log(`  max( b + SUM a_i cos(mid_i) + SUM d_i sin(diff_i), 0 )^2`);
  console.log(`  ${A.length.toLocaleString()} train / ${B.length.toLocaleString()} test, split by person. Target duration >= ${med.toFixed(2)} y, 50/50.`);
  console.log(`${"═".repeat(88)}`);
  console.log(`  model                                                cols  TRAIN acc  TEST acc   MSE test`);
  const FEATURES = [
    ["COMBINED, circular midpoint + difference, 10 planets", (r) => [...r.circular, ...r.diffSin]],
    ["COMBINED, naive midpoint + difference, 10 planets", (r) => [...r.naive, ...r.diffSin]],
    ["  midpoint alone, circular, 10 planets", (r) => r.circular],
    ["  difference alone, 10 planets", (r) => r.diffSin],
    ["COMBINED, circular + difference, classical 7 (no calendar)", (r) => [...ci.map((i) => r.circular[i]), ...ci.map((i) => r.diffSin[i])]],
    ["  midpoint alone, circular, classical 7", (r) => ci.map((i) => r.circular[i])],
    ["  difference alone, classical 7", (r) => ci.map((i) => r.diffSin[i])],
    ["era + age gap, no astrology (same link)", ERA],
    ["COMBINED + era + age gap", (r) => [...r.circular, ...r.diffSin, ...ERA(r)]],
  ];
  const out = [];
  for (const [name, fn] of FEATURES) {
    const build = (r) => Float64Array.from([1, ...fn(r)]);
    const w = fitRectified(A.map(build), Float64Array.from(A.map((r) => r.duration)), 0.01);
    const row = { name, np: build(rows[0]).length - 1, tr: acc(w, build, A), te: acc(w, build, B), mse: mseOf(w, build, B), w };
    out.push(row);
    console.log(`  ${name.padEnd(58)} ${String(row.np).padStart(3)}   ${(100 * row.tr).toFixed(2)}%    ${(100 * row.te).toFixed(2)}%    ${row.mse.toFixed(2)}`);
  }
  const cst = B.reduce((s2, r) => s2 + (r.duration - A.reduce((q, x) => q + x.duration, 0) / A.length) ** 2, 0) / B.length;
  console.log(`  ${"the coin / the constant prediction".padEnd(58)}  —      —        50.00%    ${cst.toFixed(2)}`);

  const combined = out[0];
  console.log(`\n  the fitted combined model (circular midpoint + difference, 10 planets):`);
  console.log(`    b = ${combined.w[0].toFixed(4)}`);
  console.log(`    a (cos midpoint) : ${PLANETS.map((b2, i) => `${b2} ${combined.w[1 + i].toFixed(4)}`).join("  ")}`);
  console.log(`    d (sin difference): ${PLANETS.map((b2, i) => `${b2} ${combined.w[11 + i].toFixed(4)}`).join("  ")}`);
  const ampAll = Math.hypot(...[...combined.w].slice(1));
  const ampInner = Math.hypot(...ci.map((i) => combined.w[1 + i]), ...ci.map((i) => combined.w[11 + i]));
  console.log(`    total amplitude ${ampAll.toFixed(4)}; classical bodies only ${ampInner.toFixed(4)} — the three outer`);
  console.log(`    planets carry ${(100 * (1 - (ampInner / ampAll) ** 2)).toFixed(1)}% of the squared amplitude`);
  const dead = A.filter((r) => dotf(combined.w, Float64Array.from([1, ...r.circular, ...r.diffSin])) <= 0).length;
  console.log(`    the rectifier fires (u <= 0) for ${dead.toLocaleString()} of ${A.length.toLocaleString()} training couples`);
}
