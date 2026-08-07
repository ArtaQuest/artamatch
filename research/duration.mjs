/**
 * duration.mjs — predict how long the marriage lasted, on every couple the data can support.
 *
 * ── "All the data" ──────────────────────────────────────────────────────────────────────────────
 *
 * A duration needs a marriage START date, and that is the binding constraint: only 48,846 of the
 * 99,494 collected couples have one. Nothing can be done about that. But two filters used elsewhere
 * in this study were choices rather than necessities, and both are relaxed here:
 *
 *   the 1800-2012 window        + 7,512 couples, back to the fifteenth century and a handful earlier
 *   the 1st-of-month exclusion  + 2,749 couples with a placeholder-looking birth date
 *
 * That takes the sample from 38,216 to 48,477, a 27% increase. Both relaxations cost accuracy of the
 * FEATURES rather than of the target, and both cost it in the direction that makes astrology look
 * worse, not better: outside 1800-2050 the JPL Table-1 elements are extrapolation, so the outer
 * planets — the only bodies carrying anything in this study — drift; and a placeholder birth date puts
 * a person at a position they were never at. Neither can manufacture a signal. Both samples are
 * therefore reported side by side, and the maximal one is the headline because it was asked for.
 *
 * ── Two readings of "predict duration" ──────────────────────────────────────────────────────────
 *
 *   R^2 on the number of years — the natural reading, reported for the continuous target.
 *   accuracy at the median     — a 50/50 split, so accuracy reads against a 50% coin, and comparable
 *                                with every other number in this study.
 *
 * ── The era control has to be widened too ───────────────────────────────────────────────────────
 *
 * The decade flags used elsewhere run 1800-2010 and would leave every pre-1800 couple in a single
 * unmodelled bucket, which would flatter the astrology by crippling its comparator. The baseline here
 * uses 25-year bins from 1400 with a catch-all below, so it covers the same span the features do.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/duration.mjs <dataset.json>
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const norm360 = (x) => ((x % 360) + 360) % 360;
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
const sigma = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));

/** Ridge regression, for the continuous target. */
function fitRidge(X, y, ridge) {
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
function fitLogistic(X, y, ridge, iters = 5) {
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

// ── the data, with nothing dropped that does not have to be ─────────────────────────────────────
const raw = JSON.parse(readFileSync(process.argv[2] ?? "./research/data/dataset.json", "utf8"));
const parseDate = (iso) => {
  const m = /^(-?\d{3,4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};
const jdOf = (iso) => { const p = parseDate(iso); return p ? julianDay(p.y, p.m, p.d, 12) : null; };

const all = [];
const drop = { births: 0, noStart: 0, noEnd: 0, impossible: 0 };
for (const r of raw) {
  const f = parseDate(r.fDob), m = parseDate(r.mDob);
  if (!f || !m) { drop.births++; continue; }
  const fJd = julianDay(f.y, f.m, f.d, 12), mJd = julianDay(m.y, m.m, m.d, 12);
  const st = jdOf(r.start);
  if (st === null) { drop.noStart++; continue; }
  const ends = [jdOf(r.end), jdOf(r.fDod), jdOf(r.mDod)].filter((v) => v !== null);
  if (!ends.length) { drop.noEnd++; continue; }
  const dur = (Math.min(...ends) - st) / YR;
  const ageF = (st - fJd) / YR, ageM = (st - mJd) / YR;
  if (dur <= 0 || dur > 80 || ageF < 12 || ageM < 12) { drop.impossible++; continue; }
  all.push({
    father: r.father, mother: r.mother, duration: dur,
    fYear: f.y, mYear: m.y, gap: (fJd - mJd) / YR,
    inWindow: f.y >= 1800 && f.y <= 2012 && m.y >= 1800 && m.y <= 2012,
    placeholder: r.fDob.endsWith("-01") || r.mDob.endsWith("-01"),
    fl: PLANETS.map((b) => siderealLongitude(b, fJd)),
    ml: PLANETS.map((b) => siderealLongitude(b, mJd)),
  });
}

console.log(`\nPREDICTING MARRIAGE DURATION`);
console.log(`  collected couples                            : ${raw.length.toLocaleString()}`);
console.log(`  dropped, no marriage START date              : ${drop.noStart.toLocaleString()}   <- the binding constraint, unavoidable`);
console.log(`  dropped, no end (no stated end, no death)    : ${drop.noEnd.toLocaleString()}`);
console.log(`  dropped, physically impossible               : ${drop.impossible.toLocaleString()}`);
console.log(`  MAXIMAL SAMPLE                               : ${all.length.toLocaleString()}`);
const clean = all.filter((r) => r.inWindow && !r.placeholder);
console.log(`    of which inside 1800-2012 and unplaceholdered: ${clean.length.toLocaleString()} (what this study used before)`);
console.log(`    recovered by relaxing those two filters      : ${(all.length - clean.length).toLocaleString()}`);
{
  const y = all.map((r) => r.duration).sort((a, b) => a - b);
  const mean = y.reduce((s, v) => s + v, 0) / y.length;
  console.log(`  duration: mean ${mean.toFixed(2)} y, median ${y[y.length >> 1].toFixed(2)}, sd ` +
    `${Math.sqrt(y.reduce((s, v) => s + (v - mean) ** 2, 0) / y.length).toFixed(2)}, range ${y[0].toFixed(1)}-${y[y.length - 1].toFixed(1)}`);
  const early = all.filter((r) => !r.inWindow).length;
  console.log(`  couples outside the ephemeris's verified window: ${early.toLocaleString()} — their planetary`);
  console.log(`  positions are extrapolated, which blunts the features and cannot invent a signal.`);
}

// ── features ────────────────────────────────────────────────────────────────────────────────────
const ixOf = (bs) => bs.map((b) => PLANETS.indexOf(b));
const diagH1 = (bs) => { const I = ixOf(bs); return (r) => I.flatMap((j) => { const d = (r.fl[j] - r.ml[j]) * D2R; return [Math.cos(d), Math.sin(d)]; }); };
const crossH1 = (bs) => { const I = ixOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) { const d = (r.fl[j] - r.ml[k]) * D2R; o.push(Math.cos(d), Math.sin(d)); } return o; }; };
const crossH2 = (bs) => { const I = ixOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) { const d = (r.fl[j] - r.ml[k]) * D2R; o.push(Math.cos(d), Math.sin(d), Math.cos(2 * d), Math.sin(2 * d)); } return o; }; };
const crossSq = (bs) => { const I = ixOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) o.push(Math.cos(2 * (r.fl[j] - r.ml[k]) * D2R)); return o; }; };

/** Era bins wide enough to cover the maximal sample, so the baseline is not crippled by its own
 *  encoding on the couples the relaxed filters just let in. */
const BINS = [];
for (let y = 1400; y <= 2000; y += 25) BINS.push(y);
const ERA = (r) => {
  const t = (r.fYear + r.mYear) / 2;
  return [
    t < 1400 ? 1 : 0,
    ...BINS.map((b) => (t >= b && t < b + 25 ? 1 : 0)),
    r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10,
  ];
};

const RIDGES = [0.3, 1, 3, 10, 30, 100];

function run(sample, fn) {
  const side = new Map();
  SEED = 20260805;
  for (const r of sample) {
    let s = side.get(r.father) ?? side.get(r.mother);
    if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
    side.set(r.father, s); side.set(r.mother, s);
    r.side = s;
  }
  const TR = sample.filter((r) => r.side === "train"), VA = sample.filter((r) => r.side === "val"), TE = sample.filter((r) => r.side === "test");
  const med = sample.map((r) => r.duration).sort((a, b) => a - b)[sample.length >> 1];
  const build = (r) => Float64Array.from([1, ...fn(r)]);
  const X = TR.map(build);
  const yc = Float64Array.from(TR.map((r) => r.duration));
  const yb = Float64Array.from(TR.map((r) => (r.duration >= med ? 1 : 0)));
  const trMean = yc.reduce((s, v) => s + v, 0) / yc.length;

  let best = null;
  for (const ridge of RIDGES) {
    const wc = fitRidge(X, yc, ridge), wb = fitLogistic(X, yb, ridge);
    const r2 = (set) => {
      let ssr = 0, sst = 0;
      for (const r of set) { ssr += (r.duration - dotf(wc, build(r))) ** 2; sst += (r.duration - trMean) ** 2; }
      return 1 - ssr / sst;
    };
    const acc = (set) => set.filter((r) => (sigma(dotf(wb, build(r))) >= 0.5 ? 1 : 0) === (r.duration >= med ? 1 : 0)).length / set.length;
    const val = acc(VA);
    if (!best || val > best.val) best = { ridge, val, acc: acc(TE), accFit: acc(TR), r2: r2(TE), r2Fit: r2(TR) };
  }
  return { ...best, np: X[0].length - 1, n: sample.length, nTest: TE.length };
}

const CONFIGS = [
  ["era + age gap, NO astrology", ERA],
  ["diagonal synastry, 10 planets", diagH1(PLANETS)],
  ["FULL 10x10 synastry, first harmonic", crossH1(PLANETS)],
  ["FULL 10x10 synastry, harmonics 1+2", crossH2(PLANETS)],
  ["FULL 10x10 synastry, square harmonic only", crossSq(PLANETS)],
  ["diagonal synastry, classical 7 only", diagH1(CLASSICAL)],
  ["FULL 7x7 synastry, classical only", crossH1(CLASSICAL)],
  ["FULL 7x7 synastry, classical, square harmonic", crossSq(CLASSICAL)],
  ["FULL 10x10 synastry + era + age gap", (r) => [...crossH1(PLANETS)(r), ...ERA(r)]],
];

/**
 * The full classification report on the median-balanced sample.
 *
 * The median split makes this a genuinely balanced problem — exactly half the couples above, half
 * below — which is what lets precision, recall and accuracy all be read against the same 50% coin
 * without a moving baseline. Train and test are shown side by side; the gap between them is the only
 * way to see whether 200 columns have started memorising rather than predicting.
 */
function report(sample, label, fn) {
  const side = new Map();
  SEED = 20260805;
  for (const r of sample) {
    let s = side.get(r.father) ?? side.get(r.mother);
    if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
    side.set(r.father, s); side.set(r.mother, s);
    r.side = s;
  }
  const med = sample.map((r) => r.duration).sort((a, b) => a - b)[sample.length >> 1];
  const lab = (r) => (r.duration >= med ? 1 : 0);
  const TR = sample.filter((r) => r.side === "train"), VA = sample.filter((r) => r.side === "val"), TE = sample.filter((r) => r.side === "test");
  const build = (r) => Float64Array.from([1, ...fn(r)]);
  const X = TR.map(build), y = Float64Array.from(TR.map(lab));
  let best = null;
  for (const ridge of RIDGES) {
    const w = fitLogistic(X, y, ridge);
    const acc = (set) => set.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === lab(r)).length / set.length;
    const v = acc(VA);
    if (!best || v > best.v) best = { w, v, ridge };
  }
  const w = best.w;
  const table = (set) => {
    let tp = 0, fp = 0, fn2 = 0, tn = 0;
    for (const r of set) {
      const p = sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0, t = lab(r);
      if (p && t) tp++; else if (p && !t) fp++; else if (!p && t) fn2++; else tn++;
    }
    const safe = (a, b) => (b ? a / b : 0);
    const rows = [
      { cls: `0  (under ${med.toFixed(1)}y)`, prec: safe(tn, tn + fn2), rec: safe(tn, tn + fp), n: tn + fp },
      { cls: `1  (${med.toFixed(1)}y or longer)`, prec: safe(tp, tp + fp), rec: safe(tp, tp + fn2), n: tp + fn2 },
    ];
    for (const q of rows) q.f1 = q.prec + q.rec ? (2 * q.prec * q.rec) / (q.prec + q.rec) : 0;
    return { rows, acc: (tp + tn) / set.length, total: set.length, cm: { tp, fp, fn: fn2, tn } };
  };
  const a = table(TR), b = table(TE);
  console.log(`\n  ${label}   (ridge ${best.ridge}, ${build(sample[0]).length - 1} columns)`);
  console.log(`                              ┌─────────── TRAIN ───────────┐  ┌─────────── TEST ────────────┐`);
  console.log(`  class                        precision  recall     f1 support   precision  recall     f1 support`);
  for (let i = 0; i < 2; i++) {
    const x = a.rows[i], z = b.rows[i];
    console.log(`  ${x.cls.padEnd(26)}    ${x.prec.toFixed(3)}   ${x.rec.toFixed(3)}  ${x.f1.toFixed(3)}  ${String(x.n).padStart(6)}      ${z.prec.toFixed(3)}   ${z.rec.toFixed(3)}  ${z.f1.toFixed(3)}  ${String(z.n).padStart(6)}`);
  }
  const macro = (t) => t.rows.reduce((s, q) => s + q.f1, 0) / 2;
  console.log(`  ${"macro avg f1".padEnd(26)}                    ${macro(a).toFixed(3)}  ${String(a.total).padStart(6)}                      ${macro(b).toFixed(3)}  ${String(b.total).padStart(6)}`);
  console.log(`  ${"accuracy".padEnd(26)}                    ${a.acc.toFixed(3)}  ${String(a.total).padStart(6)}                      ${b.acc.toFixed(3)}  ${String(b.total).padStart(6)}`);
  console.log(`    confusion  TRAIN  tp ${a.cm.tp}  fp ${a.cm.fp}  fn ${a.cm.fn}  tn ${a.cm.tn}`);
  console.log(`               TEST   tp ${b.cm.tp}  fp ${b.cm.fp}  fn ${b.cm.fn}  tn ${b.cm.tn}`);
}

for (const [label, sample] of [["MAXIMAL SAMPLE", all], ["the narrower clean sample, for comparison", clean]]) {
  console.log(`\n${"═".repeat(84)}`);
  console.log(`  ${label} — ${sample.length.toLocaleString()} couples`);
  console.log(`${"═".repeat(84)}`);
  console.log(`  model                                            cols  ridge   acc fit   ACC test    R2 fit   R2 TEST`);
  const scored = [];
  for (const [name, fn] of CONFIGS) {
    const r = run(sample, fn);
    scored.push({ name, ...r });
    console.log(`  ${name.padEnd(46)} ${String(r.np).padStart(4)}  ${String(r.ridge).padStart(5)}   ${(100 * r.accFit).toFixed(2)}%   ${(100 * r.acc).toFixed(2)}%    ${r.r2Fit.toFixed(4)}   ${r.r2.toFixed(4)}`);
  }
  const bl = scored[0];
  const astro = scored.filter((s) => /synastry/.test(s.name) && !s.name.includes("+")).sort((a, b) => b.val - a.val)[0];
  const clean7 = scored.filter((s) => /classical/.test(s.name)).sort((a, b) => b.val - a.val)[0];
  console.log(`\n    best astrology alone : ${astro.name}`);
  console.log(`      accuracy ${(100 * astro.acc).toFixed(2)}% vs baseline ${(100 * bl.acc).toFixed(2)}%   (${(100 * (astro.acc - bl.acc)).toFixed(2)} points)`);
  console.log(`      R^2      ${astro.r2.toFixed(4)} vs baseline ${bl.r2.toFixed(4)}   (${(astro.r2 - bl.r2).toFixed(4)})`);
  console.log(`    best with no outer planets: ${clean7.name} — accuracy ${(100 * clean7.acc).toFixed(2)}%, R^2 ${clean7.r2.toFixed(4)}`);
}

// ── the classification reports, on the median-balanced maximal sample ────────────────────────────
{
  const med = all.map((r) => r.duration).sort((a, b) => a - b)[all.length >> 1];
  const pos = all.filter((r) => r.duration >= med).length;
  console.log(`\n${"═".repeat(84)}`);
  console.log(`  CLASSIFICATION REPORTS — median-balanced, cut at ${med.toFixed(2)} years`);
  console.log(`  ${all.length.toLocaleString()} couples: ${pos.toLocaleString()} at or above (${(100 * pos / all.length).toFixed(2)}%), ` +
    `${(all.length - pos).toLocaleString()} below (${(100 * (all.length - pos) / all.length).toFixed(2)}%) — the coin is 50%`);
  console.log(`${"═".repeat(84)}`);
  report(all, "era + age gap, NO astrology", ERA);
  report(all, "FULL 10x10 synastry, first harmonic", crossH1(PLANETS));
  report(all, "FULL 10x10 synastry + era + age gap", (r) => [...crossH1(PLANETS)(r), ...ERA(r)]);
  report(all, "diagonal synastry, classical 7 only (no calendar available)", diagH1(CLASSICAL));
  report(all, "FULL 7x7 synastry, classical, square harmonic only", crossSq(CLASSICAL));
}
