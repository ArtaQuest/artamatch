/**
 * marriagelife.mjs — total life lived inside the marriage.
 *
 * THE TARGET, as specified:
 *
 *     total  =  2 x duration  +  SUM over children of ( age of that child when the marriage ended )
 *
 * Two partner-years for every year the marriage lasted, plus one child-year for every year each child
 * had lived by the time it ended. Classified at the median so the classes are 50/50 and accuracy reads
 * against a 50% coin.
 *
 * ── Three definitional choices, each of which changes the number ─────────────────────────────────
 *
 *  1. CHILDREN BORN AFTER THE MARRIAGE ENDED have a negative age at the end. They are clamped to zero
 *     rather than allowed to subtract: a child born after a divorce did not un-live part of it. The
 *     count is reported.
 *  2. CHILDREN BORN BEFORE THE MARRIAGE BEGAN are, on the formula as written, credited with their
 *     whole age — including the years before the marriage existed. That is what is computed here,
 *     because it is what was asked for. Alongside it an OVERLAP variant is reported, counting only
 *     the years each child actually lived inside the marriage, `end - max(birth, start)`, which is
 *     the coherent reading of "life lived inside the marriage". Both are shown; they differ.
 *  3. A SUM OVER CHILDREN IS ONLY WELL DEFINED IF EVERY CHILD IS DATED. Just 44.7% of co-parented
 *     children on Wikidata have a day-precision birth date, and the missingness tracks notability and
 *     era rather than being random, so a partial sum would be biased downward in exactly the places
 *     the era controls also live. Only couples where EVERY co-parented child has a day-precision date
 *     are used — 85,220 of 99,497, including couples with no recorded children at all, whose sum is
 *     zero and whose total is simply twice the duration.
 *
 * ── And the arithmetic, again ───────────────────────────────────────────────────────────────────
 *
 * This target is very largely `2 x duration + n x (mean child age)`, so duration and the number of
 * children reconstruct most of it by arithmetic. They are reported as a ceiling, not as a rival, and
 * the astrology is judged against era and age gap — the same baseline as everywhere else in this
 * study — and then on what it adds on top of the mechanical terms.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/marriagelife.mjs <dataset.json>
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const norm360 = (x) => ((x % 360) + 360) % 360;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const CLASSICAL = PLANETS.slice(0, 7);
const MIN_DURATION = +(process.env.MIN_DURATION ?? 28.0);

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

// ── the data ────────────────────────────────────────────────────────────────────────────────────
const raw = JSON.parse(readFileSync(process.argv[2] ?? "./research/data/dataset.json", "utf8"));
const parseDate = (iso) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};
const jdOf = (iso) => { const p = parseDate(iso); return p ? julianDay(p.y, p.m, p.d, 12) : null; };
const isPlaceholder = (iso) => !iso || iso.endsWith("-01");
const YR = 365.2425;

const rows = [];
const drop = { births: 0, window: 0, noStart: 0, impossible: 0, childrenUndated: 0 };
let bornAfterEnd = 0, bornBeforeStart = 0;
for (const r of raw) {
  const f = parseDate(r.fDob), m = parseDate(r.mDob);
  if (!f || !m) { drop.births++; continue; }
  if (f.y < 1800 || f.y > 2012 || m.y < 1800 || m.y > 2012) { drop.window++; continue; }
  if (isPlaceholder(r.fDob) || isPlaceholder(r.mDob)) { drop.births++; continue; }
  // The sum is only well defined when every co-parented child carries a date.
  if ((r.childDobs?.length ?? 0) !== r.children) { drop.childrenUndated++; continue; }
  const fJd = julianDay(f.y, f.m, f.d, 12), mJd = julianDay(m.y, m.m, m.d, 12);
  const st = jdOf(r.start);
  if (st === null) { drop.noStart++; continue; }
  const ends = [jdOf(r.end), jdOf(r.fDod), jdOf(r.mDod)].filter((v) => v !== null);
  if (!ends.length) { drop.impossible++; continue; }
  const endJd = Math.min(...ends);
  const dur = (endJd - st) / YR;
  const ageF = (st - fJd) / YR, ageM = (st - mJd) / YR;
  if (dur <= 0 || dur > 80 || ageF < 12 || ageM < 12) { drop.impossible++; continue; }

  let childYears = 0, overlapYears = 0;
  for (const cd of r.childDobs) {
    const cj = jdOf(cd);
    if (cj === null) continue;
    const ageAtEnd = (endJd - cj) / YR;
    if (ageAtEnd < 0) bornAfterEnd++;
    if (cj < st) bornBeforeStart++;
    childYears += Math.max(0, ageAtEnd);
    overlapYears += Math.max(0, (endJd - Math.max(cj, st)) / YR);
  }
  rows.push({
    father: r.father, mother: r.mother,
    total: 2 * dur + childYears,
    overlap: 2 * dur + overlapYears,
    duration: dur, nChildren: r.children, childYears,
    ageAtMarriage: (ageF + ageM) / 2, ageF, ageM,
    fYear: f.y, mYear: m.y, gap: (fJd - mJd) / YR,
    fl: PLANETS.map((b) => siderealLongitude(b, fJd)),
    ml: PLANETS.map((b) => siderealLongitude(b, mJd)),
  });
}
const TARGET = process.env.OVERLAP ? "overlap" : "total";
const sortedT = rows.map((r) => r[TARGET]).sort((a, b) => a - b);
const MEDIAN = sortedT[sortedT.length >> 1];
for (const r of rows) r.label = r[TARGET] >= MEDIAN ? 1 : 0;
const base = rows.reduce((s, r) => s + r.label, 0) / rows.length;

console.log(`\nTOTAL LIFE LIVED INSIDE THE MARRIAGE  =  2 x duration + SUM(children's ages at the end)`);
console.log(`  definition in use: ${TARGET === "overlap" ? "OVERLAP (only years each child lived inside the marriage)" : "AS SPECIFIED (each child's full age at the end)"}`);
console.log(`  dropped: ${drop.childrenUndated.toLocaleString()} couples with an undated co-parented child, ` +
  `${drop.noStart.toLocaleString()} without a marriage start date, ${drop.impossible.toLocaleString()} impossible`);
console.log(`  USED: ${rows.length.toLocaleString()} couples, ${(100 * base).toFixed(1)}% positive — the coin is 50%`);
console.log(`  median total: ${MEDIAN.toFixed(1)} person-years   (range ${sortedT[0].toFixed(1)}-${sortedT[sortedT.length - 1].toFixed(1)})`);
console.log(`  children born after the marriage ended: ${bornAfterEnd.toLocaleString()} (clamped to zero)`);
console.log(`  children born before it began: ${bornBeforeStart.toLocaleString()} (credited in full by the formula as specified)`);
{
  const mean = (f) => rows.reduce((s, r) => s + f(r), 0) / rows.length;
  const corr = (f, g) => {
    const mf = mean(f), mg = mean(g);
    let x = 0, p = 0, q = 0;
    for (const r of rows) { x += (f(r) - mf) * (g(r) - mg); p += (f(r) - mf) ** 2; q += (g(r) - mg) ** 2; }
    return x / Math.sqrt(p * q);
  };
  const withKids = rows.filter((r) => r.nChildren > 0).length;
  console.log(`\n  couples with at least one recorded child: ${withKids.toLocaleString()} (${(100 * withKids / rows.length).toFixed(1)}%)`);
  console.log(`  the target against its own arithmetic parts:`);
  console.log(`    vs duration                    : r = ${corr((r) => r[TARGET], (r) => r.duration).toFixed(4)}`);
  console.log(`    vs number of children          : r = ${corr((r) => r[TARGET], (r) => r.nChildren).toFixed(4)}`);
  console.log(`    vs 2*duration + n*duration/2   : r = ${corr((r) => r[TARGET], (r) => 2 * r.duration + r.nChildren * r.duration / 2).toFixed(4)}`);
  console.log(`  the two definitions against each other: r = ${corr((r) => r.total, (r) => r.overlap).toFixed(4)}`);
}

// ── the split ───────────────────────────────────────────────────────────────────────────────────
const side = new Map();
for (const r of rows) {
  let s = side.get(r.father) ?? side.get(r.mother);
  if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
  side.set(r.father, s); side.set(r.mother, s);
  r.side = s;
}
const TR = rows.filter((r) => r.side === "train"), VA = rows.filter((r) => r.side === "val"), TE = rows.filter((r) => r.side === "test");
console.log(`\n  ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} validate · ${TE.length.toLocaleString()} test (split by person)`);

// ── features ────────────────────────────────────────────────────────────────────────────────────
const ixOf = (bs) => bs.map((b) => PLANETS.indexOf(b));
const diagH1 = (bs) => { const I = ixOf(bs); return (r) => I.flatMap((j) => { const d = (r.fl[j] - r.ml[j]) * D2R; return [Math.cos(d), Math.sin(d)]; }); };
const crossH1 = (bs) => { const I = ixOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) { const d = (r.fl[j] - r.ml[k]) * D2R; o.push(Math.cos(d), Math.sin(d)); } return o; }; };
const crossSq = (bs) => { const I = ixOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) o.push(Math.cos(2 * (r.fl[j] - r.ml[k]) * D2R)); return o; }; };
const ASPECTS = [0, 30, 60, 90, 120, 150, 180];
const crossOrb = (bs, orb) => { const I = ixOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) { const d = norm360(r.fl[j] - r.ml[k]), sep = d > 180 ? 360 - d : d; for (const a of ASPECTS) o.push(Math.exp(-(((sep - a) / orb) ** 2))); } return o; }; };

const DECADES = [];
for (let y = 1800; y <= 2010; y += 10) DECADES.push(y);
const ERA = (r) => {
  const t = (r.fYear + r.mYear) / 2;
  return [...DECADES.map((d) => (t >= d && t < d + 10 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];
};
const ERA_AGE = (r) => [...ERA(r), r.ageAtMarriage / 10, (r.ageAtMarriage / 10) ** 2, r.ageF / 10, r.ageM / 10];
// The mechanical terms: the target is largely 2*duration + n*(mean child age), so these two rebuild
// most of it by arithmetic. A ceiling, not a rival.
const MECHANICAL = (r) => [...ERA_AGE(r), r.duration / 10, (r.duration / 10) ** 2, r.nChildren, r.nChildren ** 2, r.nChildren * r.duration / 10];

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
  ["era + age gap (the study's baseline)", ERA],
  ["era + age gap + AGE AT MARRIAGE", ERA_AGE],
  ["era + age + duration + CHILD COUNT (arithmetic ceiling)", MECHANICAL],
  ["diagonal synastry, 10 planets", diagH1(PLANETS)],
  ["FULL 10x10 synastry, first harmonic", crossH1(PLANETS)],
  ["FULL 10x10 synastry, square harmonic only", crossSq(PLANETS)],
  ["FULL 10x10 synastry, Ptolemaic bumps orb 8 deg", crossOrb(PLANETS, 8)],
  ["diagonal synastry, classical 7 only", diagH1(CLASSICAL)],
  ["FULL 7x7 synastry, classical only, first harmonic", crossH1(CLASSICAL)],
  ["FULL 7x7 synastry, classical only, square harmonic only", crossSq(CLASSICAL)],
  ["FULL 10x10 synastry + era + age gap", (r) => [...crossH1(PLANETS)(r), ...ERA(r)]],
  ["FULL 10x10 synastry + era + age + age at marriage", (r) => [...crossH1(PLANETS)(r), ...ERA_AGE(r)]],
  ["FULL 10x10 synastry + the arithmetic ceiling", (r) => [...crossH1(PLANETS)(r), ...MECHANICAL(r)]],
];

console.log(`\n  ridge chosen on validation from ${RIDGES.join(", ")} — never on test\n`);
console.log(`  model                                                            cols  ridge    fit      val     test`);
const scored = [];
for (const [name, fn] of CONFIGS) {
  const r = evaluate(fn);
  scored.push({ name, ...r });
  console.log(`  ${name.padEnd(62)} ${String(r.np).padStart(4)}  ${String(r.ridge).padStart(5)}   ${(100 * r.fit).toFixed(2)}%  ${(100 * r.val).toFixed(2)}%  ${(100 * r.test).toFixed(2)}%`);
}

const eraOnly = scored[0], eraAge = scored[1], ceiling = scored[2];
// Astrology ALONE means no control term anywhere in the design — anything with a "+" in its name is
// a combined model and must not be reported as the astrology's own score.
const astro = scored.filter((s) => /synastry/.test(s.name) && !s.name.includes("+")).sort((a, b) => b.val - a.val)[0];
const combos = scored.filter((s) => /synastry/.test(s.name) && s.name.includes("+"));
const combined = combos.sort((a, b) => b.val - a.val)[0];
const clean = scored.filter((s) => /classical/.test(s.name)).sort((a, b) => b.val - a.val)[0];

console.log(`\n${"═".repeat(82)}`);
console.log(`  BEST ASTROLOGY ALONE: ${astro.name}`);
console.log(`    ${astro.np} columns — fit ${(100 * astro.fit).toFixed(2)}%, val ${(100 * astro.val).toFixed(2)}%, TEST ${(100 * astro.test).toFixed(2)}%`);
console.log(`  against era + age gap                    : ${(100 * eraOnly.test).toFixed(2)}%   (${(100 * (astro.test - eraOnly.test)).toFixed(2)} points)`);
console.log(`  against era + age gap + age at marriage  : ${(100 * eraAge.test).toFixed(2)}%   (${(100 * (astro.test - eraAge.test)).toFixed(2)} points)`);
console.log(`  the arithmetic ceiling (+ duration + n)  : ${(100 * ceiling.test).toFixed(2)}%`);
console.log(`  the coin                                 : 50.00%`);
console.log(`\n  BEST WITH ASTROLOGY ON TOP OF THE CONTROLS: ${combined.name}`);
{
  // Compare against the SAME control set without the astrology, so the number is what the astrology
  // added rather than what the controls were already worth.
  const ref = /arithmetic ceiling/.test(combined.name) ? ceiling : /age at marriage/.test(combined.name) ? eraAge : eraOnly;
  console.log(`    TEST ${(100 * combined.test).toFixed(2)}% against ${(100 * ref.test).toFixed(2)}% for the same controls alone` +
    ` — astrology adds ${(100 * (combined.test - ref.test)).toFixed(2)} points`);
}
console.log(`\n  THE CLEAN CASE — classical bodies only, nothing that can read the calendar:`);
console.log(`    ${clean.name}: TEST ${(100 * clean.test).toFixed(2)}% against a 50% coin`);
