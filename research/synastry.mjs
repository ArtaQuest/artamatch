/**
 * synastry.mjs — the full cross-matrix, which is what synastry actually means.
 *
 * ── What was missing until now ──────────────────────────────────────────────────────────────────
 *
 * Every model in this study so far used only the DIAGONAL: Sun-to-Sun, Moon-to-Moon, ten same-body
 * angle differences. That is not synastry. Synastry is the whole grid — his Venus to her Mars, his
 * Saturn to her Moon, every body against every body:
 *
 *     delta_jk  =  theta_j(father) - theta_k(mother)        for all j, k
 *
 * Ten bodies give 100 cross-pairs, of which the ten same-body ones are the diagonal used so far. The
 * ninety off-diagonal pairs are where the tradition puts most of its weight — a Venus-Mars contact or
 * a Saturn-Moon square is the sort of thing a synastry reading is actually about — and they have not
 * been tested here at all. This tests them, with the aspect harmonics from aspects.mjs applied to
 * every cell of the grid rather than only to the diagonal.
 *
 * ── The clean case, and why it is the one that matters ───────────────────────────────────────────
 *
 * A cross-pair can leak the calendar just as a same-body pair can, and in more ways: Sun-to-Pluto
 * mixes a day-of-year against a birth-year, so it carries era information even though the two bodies
 * differ. The uncontaminated test is therefore the 7x7 grid over the classical bodies only — Sun
 * through Saturn, forty-nine pairs, no outer planet anywhere in the design. Anything there is aspect
 * information or it is nothing.
 *
 * ── Ridge ───────────────────────────────────────────────────────────────────────────────────────
 *
 * A hundred cross-pairs times two harmonic components is two hundred columns, many of them nearly
 * collinear (his Sun to her Moon and his Sun to her Mercury move together for weeks at a time). The
 * ridge is therefore a real hyperparameter and is chosen ON VALIDATION, never on test, and the sweep
 * is reported so the choice is visible rather than tuned quietly.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/synastry.mjs <dataset.json>
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const norm360 = (x) => ((x % 360) + 360) % 360;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const CLASSICAL = PLANETS.slice(0, 7);

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

function fitLogistic(X, y, ridge, iters = 5) {
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

// ── the data: full longitude vectors for both partners ──────────────────────────────────────────
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
  rows.push({
    father: r.father, mother: r.mother, duration: dur,
    fYear: f.y, mYear: m.y, gap: (fJd - mJd) / 365.2425,
    fl: PLANETS.map((b) => siderealLongitude(b, fJd)),
    ml: PLANETS.map((b) => siderealLongitude(b, mJd)),
  });
}
const sortedDur = rows.map((r) => r.duration).sort((a, b) => a - b);
const CUT = sortedDur[sortedDur.length >> 1];
for (const r of rows) r.label = r.duration >= CUT ? 1 : 0;
const base = rows.reduce((s, r) => s + r.label, 0) / rows.length;

console.log(`\nSIDEREAL SYNASTRY — the full cross-matrix`);
console.log(`  target: did this marriage last ${CUT.toFixed(1)} years or longer?`);
console.log(`  ${rows.length.toLocaleString()} couples, ${(100 * base).toFixed(1)}% positive — the coin is 50%`);

const side = new Map();
for (const r of rows) {
  let s = side.get(r.father) ?? side.get(r.mother);
  if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
  side.set(r.father, s); side.set(r.mother, s);
  r.side = s;
}
const TR = rows.filter((r) => r.side === "train"), VA = rows.filter((r) => r.side === "val"), TE = rows.filter((r) => r.side === "test");
console.log(`  ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} validate · ${TE.length.toLocaleString()} test (split by person)`);

// ── the cross-matrix bases ──────────────────────────────────────────────────────────────────────
const ixOf = (bs) => bs.map((b) => PLANETS.indexOf(b));

/** All cross-pairs j (father) x k (mother), first harmonic: sin and cos of each difference. */
const crossH1 = (bs) => {
  const I = ixOf(bs);
  return (r) => {
    const out = [];
    for (const j of I) for (const k of I) {
      const d = (r.fl[j] - r.ml[k]) * D2R;
      out.push(Math.cos(d), Math.sin(d));
    }
    return out;
  };
};
/** All cross-pairs, harmonics 1 and 2 — the second is the square/opposition harmonic. */
const crossH2 = (bs) => {
  const I = ixOf(bs);
  return (r) => {
    const out = [];
    for (const j of I) for (const k of I) {
      const d = (r.fl[j] - r.ml[k]) * D2R;
      out.push(Math.cos(d), Math.sin(d), Math.cos(2 * d), Math.sin(2 * d));
    }
    return out;
  };
};
/** The square harmonic alone across the whole grid. */
const crossSq = (bs) => {
  const I = ixOf(bs);
  return (r) => {
    const out = [];
    for (const j of I) for (const k of I) out.push(Math.cos(2 * (r.fl[j] - r.ml[k]) * D2R));
    return out;
  };
};
/** The traditional reading: a Gaussian bump on each Ptolemaic aspect, for every cross-pair. */
const ASPECTS = [0, 30, 60, 90, 120, 150, 180];
const crossOrb = (bs, orb) => {
  const I = ixOf(bs);
  return (r) => {
    const out = [];
    for (const j of I) for (const k of I) {
      const d = norm360(r.fl[j] - r.ml[k]), sep = d > 180 ? 360 - d : d;
      for (const a of ASPECTS) out.push(Math.exp(-(((sep - a) / orb) ** 2)));
    }
    return out;
  };
};
/** The diagonal only — what every earlier model in this study used, for direct comparison. */
const diagH1 = (bs) => {
  const I = ixOf(bs);
  return (r) => I.flatMap((j) => { const d = (r.fl[j] - r.ml[j]) * D2R; return [Math.cos(d), Math.sin(d)]; });
};

const DECADES = [];
for (let y = 1800; y <= 2010; y += 10) DECADES.push(y);
const CONTROLS = (r) => {
  const t = (r.fYear + r.mYear) / 2;
  return [...DECADES.map((d) => (t >= d && t < d + 10 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];
};

/** Fit at several ridges, pick the best on VALIDATION, then report that one's test score. */
const RIDGES = [0.3, 1, 3, 10, 30, 100];
function evaluate(fn) {
  const build = (r) => Float64Array.from([1, ...fn(r)]);
  const X = TR.map(build), y = Float64Array.from(TR.map((r) => r.label));
  let best = null;
  for (const ridge of RIDGES) {
    const w = fitLogistic(X, y, ridge);
    const hit = (set) => set.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === r.label).length / set.length;
    const val = hit(VA);
    if (!best || val > best.val) best = { ridge, val, test: hit(TE), fit: hit(TR) };
  }
  return { ...best, np: X[0].length - 1 };
}

const CONFIGS = [
  ["BASELINE era + age gap, no astrology", CONTROLS],
  ["diagonal only, 10 planets (what this study used before)", diagH1(PLANETS)],
  ["FULL 10x10 synastry, first harmonic", crossH1(PLANETS)],
  ["FULL 10x10 synastry, harmonics 1+2", crossH2(PLANETS)],
  ["FULL 10x10 synastry, square harmonic cos(2d) only", crossSq(PLANETS)],
  ["FULL 10x10 synastry, Ptolemaic bumps orb 8 deg", crossOrb(PLANETS, 8)],
  ["diagonal only, classical 7 (no outer planets)", diagH1(CLASSICAL)],
  ["FULL 7x7 synastry, classical only, first harmonic", crossH1(CLASSICAL)],
  ["FULL 7x7 synastry, classical only, harmonics 1+2", crossH2(CLASSICAL)],
  ["FULL 7x7 synastry, classical only, square harmonic only", crossSq(CLASSICAL)],
  ["FULL 7x7 synastry, classical only, Ptolemaic bumps orb 8 deg", crossOrb(CLASSICAL, 8)],
];

console.log(`\n  ridge chosen on validation from ${RIDGES.join(", ")} — never on test\n`);
console.log(`  model                                                          cols  ridge    fit      val     test`);
const scored = [];
for (const [name, fn] of CONFIGS) {
  const r = evaluate(fn);
  scored.push({ name, ...r });
  console.log(`  ${name.padEnd(60)} ${String(r.np).padStart(4)}  ${String(r.ridge).padStart(5)}   ${(100 * r.fit).toFixed(2)}%  ${(100 * r.val).toFixed(2)}%  ${(100 * r.test).toFixed(2)}%`);
}

const baseline = scored[0];
const astro = scored.slice(1).sort((a, b) => b.val - a.val);
const winner = astro[0];
const classical = scored.filter((s) => /classical/.test(s.name)).sort((a, b) => b.val - a.val)[0];

console.log(`\n${"═".repeat(80)}`);
console.log(`  BEST SYNASTRY MODEL BY VALIDATION: ${winner.name}`);
console.log(`    ${winner.np} columns, ridge ${winner.ridge} — fit ${(100 * winner.fit).toFixed(2)}%, validation ${(100 * winner.val).toFixed(2)}%, TEST ${(100 * winner.test).toFixed(2)}%`);
console.log(`    the baseline on the same test set: ${(100 * baseline.test).toFixed(2)}%`);
console.log(`    ${winner.test > baseline.test ? "BEATS" : "DOES NOT BEAT"} it, by ${(100 * (winner.test - baseline.test)).toFixed(2)} points`);
console.log(`\n  THE CLEAN CASE — classical bodies only, no outer planet anywhere in the design, so`);
console.log(`  nothing in it can read the calendar: ${classical.name}`);
console.log(`    ${classical.np} columns — fit ${(100 * classical.fit).toFixed(2)}%, validation ${(100 * classical.val).toFixed(2)}%, TEST ${(100 * classical.test).toFixed(2)}%, coin 50.00%`);
console.log(`\n  What the off-diagonal is worth: the full grid against the diagonal alone,`);
const d10 = scored.find((s) => /diagonal only, 10/.test(s.name)), f10 = scored.find((s) => /FULL 10x10 synastry, first/.test(s.name));
const d7 = scored.find((s) => /diagonal only, classical/.test(s.name)), f7 = scored.find((s) => /FULL 7x7 synastry, classical only, first/.test(s.name));
console.log(`    10 planets : diagonal ${(100 * d10.test).toFixed(2)}% -> full grid ${(100 * f10.test).toFixed(2)}%  (${(100 * (f10.test - d10.test)).toFixed(2)} points, ${d10.np} -> ${f10.np} columns)`);
console.log(`    classical 7: diagonal ${(100 * d7.test).toFixed(2)}% -> full grid ${(100 * f7.test).toFixed(2)}%  (${(100 * (f7.test - d7.test)).toFixed(2)} points, ${d7.np} -> ${f7.np} columns)`);
