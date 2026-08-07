/**
 * model.mjs — does the angle between two people's planets predict how many children they had?
 *
 * THE MODEL, as specified:
 *
 *     children  ~  ( b + SUM_i w_i * f( theta_i(father) - theta_i(mother) ) )^2
 *
 * f = sin for the GENDER-SENSITIVE model — sin is odd, so swapping the two people flips every feature
 * and the prediction changes — and f = cos for the GENDERLESS one, where cos is even and swapping
 * changes nothing. Fitting a free PHASE per body is not a third thing: w*sin(D - p) expands to
 * (w cos p) sin D - (w sin p) cos D, so amplitude-and-phase per body IS a sin coefficient and a cos
 * coefficient per body. "both harmonics" is that model.
 *
 * HOW IT IS FITTED. Start from ordinary least squares of sqrt(y) on the features — the square root is
 * the variance-stabilising transform for a count, and mu = u^2 makes that an exactly linear problem —
 * then refine with Gauss-Newton against the squared error on the COUNT itself, so the R-squared below
 * measures what it appears to measure. Without that refinement every model scores worse than simply
 * predicting the mean, because the sqrt fit is not trying to fit the mean.
 *
 * WHAT DECIDES WHETHER THERE IS ANYTHING HERE — and it is not the fit:
 *
 *  · GROUPED CROSS-VALIDATION, split by PERSON. People marry more than once, and the same father in
 *    two folds leaks. Nothing is scored on data it was fitted on.
 *  · A PERMUTATION NULL. Fathers are shuffled against mothers and the whole pipeline re-run. This is
 *    the only honest yardstick for a model with twenty free parameters: it says what test R-squared
 *    this exact model produces from data whose effect has been destroyed by construction.
 *  · CONFOUND CONTROLS, and they are the whole story. Neptune and Pluto move so slowly that the angle
 *    between two people's Plutos is a precise measurement of the gap between their birth YEARS, and a
 *    couple's era and age gap predict family size for reasons that have nothing to do with the sky —
 *    a marriage in 1750 produced more children than one in 1980. So the astrology is judged on what it
 *    adds ON TOP of era, age gap and marriage duration, and separately with the three outer planets
 *    removed, which is the cleanest way to ask whether anything survives that is not a clock.
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const ALL_BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const INNER = ALL_BODIES.slice(0, 7);

/**
 * THE MIDPOINT (composite) FEATURE:  cos( midpoint( theta_father , theta_mother ) )
 *
 * This is a different object from everything above, in two ways that decide what it can mean.
 *
 * 1. THE AVERAGE OF TWO ANGLES IS AMBIGUOUS MODULO 180 DEGREES. Writing (a + b) / 2 looks harmless
 *    and is not: adding a full turn to `a` leaves the angle unchanged but moves the "average" by half
 *    a turn, so cos of it FLIPS SIGN on an arbitrary branch choice. Longitudes arrive in [0, 360),
 *    which fixes a branch, but fixes it meaninglessly — two couples with the same true midpoint get
 *    opposite features depending on which side of 0 degrees their planets happen to fall.
 *    The circular midpoint is arg(e^ia + e^ib), the direction of the vector sum, and it is what is
 *    computed here. It is undefined only when the two are exactly opposite, where the sum vanishes.
 *
 * 2. IT IS A SUM, NOT A DIFFERENCE, so it does not describe a relationship at all. It is symmetric
 *    under swapping the two people — inherently genderless, with no sin counterpart to test — and it
 *    depends on where the planets ACTUALLY WERE, not on how far apart they were. The midpoint of two
 *    Plutos is essentially Pluto's position at the couple's average birth date. Where the difference
 *    features measure the gap between two birth years, this measures the years themselves, which
 *    makes it a stronger clock, not a weaker one. The prediction to check is that it scores HIGHER
 *    alone and adds even less on top of an era control.
 */
const midpoint = (aDeg, bDeg) => {
  const a = aDeg * D2R, b = bDeg * D2R;
  return Math.atan2(Math.sin(a) + Math.sin(b), Math.cos(a) + Math.cos(b));
};

let SEED = 20260805;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };

/** Parsed here rather than by the ephemeris's parseDate, which refuses anything outside 1800-2100 —
 *  right for a page that shows somebody their chart, wrong here, where it would silently delete every
 *  marriage before 1800 without saying so. The window is applied explicitly below instead. */
const parseDate = (iso) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};
const jdOf = (iso) => { const p = parseDate(iso); return p ? julianDay(p.y, p.m, p.d, 12) : null; };

/**
 * A DURATION IS ONLY USED WHEN IT IS PHYSICALLY POSSIBLE.
 *
 * Wikidata's marriage records are far dirtier than its birth records, and the damage lands squarely
 * on this target. Found here, in the collected set:
 *
 *   · a 1,535-YEAR MARRIAGE — start date typed as year 0180 for a couple born in the 1640s. One row
 *     like that dominates a squared-error fit on its own.
 *   · marriages starting BEFORE a partner was born — one begins in 1848 for a husband born in 1884.
 *   · 134 marriages over 70 years and 13 over 80, nearly all of them artefacts of the above.
 *
 * So a duration counts only if the marriage starts after both births, both partners were at least 12,
 * and it ran under 80 years. Anything else is a record that contradicts itself, and is dropped.
 *
 * WHAT IS *NOT* FIXED, because it cannot be: 32.9% of marriage start dates fall on 1 January, 120x
 * that day's share of the calendar, and 5.7% of death dates do too, 20.7x theirs. These are
 * year-precision values rendered as a date — P580 and P570 carry no precision filter here, unlike the
 * births. The year is still right, so a duration measured in decades carries about a year of noise:
 * enough to weaken a real effect, never enough to manufacture one. It is stated rather than hidden.
 */
const MAX_YEARS = 80, MIN_AGE_AT_MARRIAGE = 12;
const durationOf = (startJd, endJd, fBirthJd, mBirthJd) => {
  if (startJd === null || endJd === null) return null;
  const years = (endJd - startJd) / 365.2425;
  if (years <= 0 || years > MAX_YEARS) return null;
  const fAge = (startJd - fBirthJd) / 365.2425, mAge = (startJd - mBirthJd) / 365.2425;
  if (fAge < MIN_AGE_AT_MARRIAGE || mAge < MIN_AGE_AT_MARRIAGE) return null;
  return years;
};


/**
 * PLACEHOLDER BIRTH DATES, excluded rather than modelled.
 *
 * Wikidata truncates a year-precision date to 1 January and a month-precision date to the 1st, and
 * although this dataset only admits statements flagged as day-precision, the flag is not always
 * honest — somebody entering "born 1847" as a day-precision 1 January 1847 leaves no trace in the
 * precision field. It shows up in the distribution instead. Measured over all 198,985 birth dates
 * collected, against the 0.274% a calendar day should hold:
 *
 *     1 January          0.430%   1.57x expected — by a distance the most over-represented day
 *     the 1st of ANY month        1.10x expected — the same leak, one precision level up
 *
 * A placeholder date puts a person at a planetary position they were never at, so it is noise in the
 * features with no matching noise in the target: it can only wash a real effect out. Excluding costs
 * a little data and buys a cleaner test.
 *
 * A COUPLE is dropped when EITHER partner is affected, because the features are differences and one
 * bad date spoils all ten of them.
 *
 *   EXCLUDE=firsts  (default) drop couples where either was born on the 1st of ANY month — this
 *                             catches both leaks at once, since 1 January is a 1st too
 *   EXCLUDE=jan1              drop only the 1 January births
 *   EXCLUDE=none              keep everything, for comparison
 */
const EXCLUDE = process.env.EXCLUDE ?? "firsts";
const isPlaceholder = (iso) =>
  EXCLUDE === "none" ? false
    : EXCLUDE === "firsts" ? iso.endsWith("-01")
      : iso.endsWith("-01-01");


// ── linear algebra ──────────────────────────────────────────────────────────────────────────────
function solve(A, b) {
  const n = A.length, M = A.map((row, i) => [...row, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    [M[c], M[p]] = [M[p], M[c]];
    if (Math.abs(M[c][c]) < 1e-12) continue;
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = M[r][c] / M[c][c];
      for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k];
    }
  }
  return M.map((row, i) => (Math.abs(row[i]) < 1e-12 ? 0 : row[n] / row[i]));
}
function ls(X, y, ridge = 1e-6) {
  const p = X[0].length;
  const A = Array.from({ length: p }, () => new Float64Array(p));
  const b = new Float64Array(p);
  for (let i = 0; i < X.length; i++) {
    const xi = X[i], yi = y[i];
    for (let j = 0; j < p; j++) {
      b[j] += xi[j] * yi;
      for (let k = j; k < p; k++) A[j][k] += xi[j] * xi[k];
    }
  }
  for (let j = 0; j < p; j++) { for (let k = 0; k < j; k++) A[j][k] = A[k][j]; A[j][j] += ridge; }
  return solve(A.map((r) => [...r]), [...b]);
}
const dot = (w, x) => { let s = 0; for (let i = 0; i < w.length; i++) s += w[i] * x[i]; return s; };

/** Fit mu = (X w)^2 to y by least squares on the COUNT: sqrt-transform for a start, then Gauss-Newton.
 *  For mu = u^2 the Jacobian row is 2*u*x, so each step is a weighted least squares of the residual. */
function fitSquared(X, y) {
  let w = ls(X, y.map(Math.sqrt));
  const err = (ww) => { let s = 0; for (let i = 0; i < X.length; i++) s += (y[i] - dot(ww, X[i]) ** 2) ** 2; return s; };
  let cur = err(w);
  for (let it = 0; it < 4; it++) {
    const J = new Array(X.length), r = new Float64Array(X.length);
    for (let i = 0; i < X.length; i++) {
      const u = dot(w, X[i]);
      const row = new Float64Array(X[i].length);
      for (let j = 0; j < X[i].length; j++) row[j] = 2 * u * X[i][j];
      J[i] = row; r[i] = y[i] - u * u;
    }
    const step = ls(J, r, 1e-3);
    const next = w.map((v, j) => v + step[j]);
    const e = err(next);
    if (e < cur) { w = next; cur = e; } else break;
  }
  return w;
}

// ── the data ────────────────────────────────────────────────────────────────────────────────────
const raw = JSON.parse(readFileSync(process.argv[2] || "./data/dataset.json", "utf8"));
const YEAR_MIN = +(process.env.YEAR_MIN ?? 1800), YEAR_MAX = +(process.env.YEAR_MAX ?? 2012);

const rows = [];
let outside = 0, placeholders = 0, impossibleDuration = 0;
for (const r of raw) {
  const f = parseDate(r.fDob), m = parseDate(r.mDob);
  if (!f || !m || f.y < YEAR_MIN || f.y > YEAR_MAX || m.y < YEAR_MIN || m.y > YEAR_MAX) { outside++; continue; }
  if (isPlaceholder(r.fDob) || isPlaceholder(r.mDob)) { placeholders++; continue; }
  const fJd = julianDay(f.y, f.m, f.d, 12), mJd = julianDay(m.y, m.m, m.d, 12);
  const fl = ALL_BODIES.map((b) => siderealLongitude(b, fJd));
  const ml = ALL_BODIES.map((b) => siderealLongitude(b, mJd));
  // MARRIAGE DURATION. It ends at whichever came first: a stated end date, or the earlier of the two
  // deaths. It needs a start date, which only about half the couples have, so it is used on that
  // subsample rather than imputed for the rest.
  const startJd = jdOf(r.start);
  const ends = [r.end, r.fDod, r.mDod].map(jdOf).filter((v) => v !== null);
  const endJd = ends.length ? Math.min(...ends) : null;
  const duration = durationOf(startJd, endJd, fJd, mJd);
  if (startJd !== null && endJd !== null && duration === null) impossibleDuration++;
  rows.push({
    key: r.key, father: r.father, mother: r.mother, y: r.children,
    delta: fl.map((x, i) => ((x - ml[i]) % 360 + 360) % 360),
    mid: fl.map((x, i) => midpoint(x, ml[i])),
    fYear: f.y, mYear: m.y, gap: (fJd - mJd) / 365.2425,
    duration,
  });
}

console.log(`\nWIKIDATA MARRIAGES — ended by death or divorce, both births known to the day`);
console.log(`  couples collected                 : ${raw.length.toLocaleString()}`);
console.log(`  outside the ephemeris's verified window ${YEAR_MIN}-${YEAR_MAX} : ${outside.toLocaleString()}`);
console.log(`  dropped, a placeholder birth date (EXCLUDE=${EXCLUDE}) : ${placeholders.toLocaleString()}`);
console.log(`  USED                              : ${rows.length.toLocaleString()}`);
const ys = rows.map((r) => r.y);
const meanY = ys.reduce((a, b) => a + b, 0) / ys.length;
console.log(`  children: mean ${meanY.toFixed(3)}  sd ${Math.sqrt(ys.reduce((a, b) => a + (b - meanY) ** 2, 0) / ys.length).toFixed(3)}  max ${Math.max(...ys)}`);
const withDur = rows.filter((r) => r.duration !== null);
console.log(`  with a known marriage duration    : ${withDur.length.toLocaleString()} (${(100 * withDur.length / rows.length).toFixed(1)}%)`);
console.log(`  durations discarded as impossible : ${impossibleDuration.toLocaleString()}`);
if (withDur.length) {
  const d = withDur.map((r) => r.duration).sort((a, b) => a - b);
  console.log(`    duration: median ${d[d.length >> 1].toFixed(1)} y, 5th ${d[Math.floor(d.length * 0.05)].toFixed(1)}, 95th ${d[Math.floor(d.length * 0.95)].toFixed(1)}`);
  const dm = withDur.reduce((s, r) => s + r.duration, 0) / withDur.length;
  const ym = withDur.reduce((s, r) => s + r.y, 0) / withDur.length;
  let num = 0, dd = 0, yy = 0;
  for (const r of withDur) { num += (r.duration - dm) * (r.y - ym); dd += (r.duration - dm) ** 2; yy += (r.y - ym) ** 2; }
  console.log(`    correlation of duration with children: r = ${(num / Math.sqrt(dd * yy)).toFixed(4)}  — the yardstick every astrological number below is measured against`);
}

// ── features ────────────────────────────────────────────────────────────────────────────────────

const idx = (b) => ALL_BODIES.indexOf(b);
const sinF = (bs) => (r) => bs.map((b) => Math.sin(r.delta[idx(b)] * D2R));
const cosF = (bs) => (r) => bs.map((b) => Math.cos(r.delta[idx(b)] * D2R));
const bothF = (bs) => (r) => [...sinF(bs)(r), ...cosF(bs)(r)];
const midF = (bs) => (r) => bs.map((b) => Math.cos(r.mid[idx(b)]));
const midBothF = (bs) => (r) => bs.flatMap((b) => [Math.cos(r.mid[idx(b)]), Math.sin(r.mid[idx(b)])]);

/** Era as DECADE INDICATORS rather than a smooth curve. Pluto's angle is a far finer clock than any
 *  quadratic in the year, so a smooth era control leaves exactly the residual the outer planets can
 *  then "predict", and the astrology gets credit for reading a calendar. */
const DECADES = [];
for (let y = 1800; y <= 2010; y += 10) DECADES.push(y);
const CONTROLS = (r) => {
  const t = (r.fYear + r.mYear) / 2;
  return [...DECADES.map((d) => (t >= d && t < d + 10 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];
};

// ── an 80/20 train/test split, grouped by PERSON ────────────────────────────────────────────────
//
// Grouped, because people marry more than once: the same father appearing in both halves would let
// the model recognise him rather than predict him. A person is assigned a side once and both of that
// person's marriages follow, so no individual straddles the split.
const side = new Map();
for (const r of rows) {
  let s = side.get(r.father) ?? side.get(r.mother);
  if (s === undefined) s = rnd() < 0.8 ? "train" : "test";
  side.set(r.father, s); side.set(r.mother, s);
  r.side = s;
}

/**
 * Fit on the training 80%, score on the held-out 20%. Returns R^2 against the training mean, so zero
 * means "no better than guessing the average couple" and a negative number means actively worse.
 */
function evaluate(featureFn, controlFn, target, sample = rows) {
  const build = (r) => [1, ...(featureFn ? featureFn(r) : []), ...(controlFn ? controlFn(r) : [])];
  const tr = sample.filter((r) => r.side === "train"), te = sample.filter((r) => r.side === "test");
  const w = fitSquared(tr.map(build), tr.map(target));
  const mean = tr.reduce((s, r) => s + target(r), 0) / tr.length;
  let ssRes = 0, ssTot = 0;
  for (const r of te) { ssRes += (target(r) - dot(w, build(r)) ** 2) ** 2; ssTot += (target(r) - mean) ** 2; }
  return { r2: 1 - ssRes / ssTot, nTrain: tr.length, nTest: te.length };
}

const SETS = {
  "gendered   sin, all 10 bodies": sinF(ALL_BODIES),
  "genderless cos, all 10 bodies": cosF(ALL_BODIES),
  "both harmonics, all 10 bodies": bothF(ALL_BODIES),
  "gendered   sin, no outer planets": sinF(INNER),
  "genderless cos, no outer planets": cosF(INNER),
  "both harmonics, no outer planets": bothF(INNER),
  "MIDPOINT cos, all 10 bodies": midF(ALL_BODIES),
  "MIDPOINT cos+sin, all 10 bodies": midBothF(ALL_BODIES),
  "MIDPOINT cos, no outer planets": midF(INNER),
  "MIDPOINT cos+sin, no outer planets": midBothF(INNER),
};

// ── the two targets ─────────────────────────────────────────────────────────────────────────────
const TARGETS = [
  { name: "NUMBER OF CHILDREN", get: (r) => r.y, sample: rows },
  { name: "YEARS OF MARRIAGE", get: (r) => r.duration, sample: withDur },
];

const results = {};
for (const t of TARGETS) {
  const n0 = evaluate(null, null, t.get, t.sample);
  console.log(`\n════ TARGET: ${t.name} ════`);
  console.log(`  ${t.sample.length.toLocaleString()} couples — ${n0.nTrain.toLocaleString()} train / ${n0.nTest.toLocaleString()} test (80/20, split by person)`);
  const m = t.sample.reduce((s, r) => s + t.get(r), 0) / t.sample.length;
  console.log(`  mean ${m.toFixed(3)}   sd ${Math.sqrt(t.sample.reduce((s, r) => s + (t.get(r) - m) ** 2, 0) / t.sample.length).toFixed(3)}`);
  console.log(`\n  model                              astrology alone   + era & age gap`);
  results[t.name] = {};
  for (const [name, fn] of Object.entries(SETS)) {
    const alone = evaluate(fn, null, t.get, t.sample).r2;
    const ctrl = evaluate(fn, CONTROLS, t.get, t.sample).r2;
    results[t.name][name] = alone;
    console.log(`  ${name.padEnd(34)} ${alone.toFixed(5).padStart(9)}       ${ctrl.toFixed(5).padStart(9)}`);
  }
  const base = evaluate(null, CONTROLS, t.get, t.sample).r2;
  console.log(`  ${"era & age gap alone, NO astrology".padEnd(34)} ${"    —    "}       ${base.toFixed(5).padStart(9)}`);
}

// ── does knowing the marriage length help predict the children? ─────────────────────────────────
console.log(`\n════ AND FOR SCALE: what an ordinary, non-astrological fact is worth ════`);
{
  const durCtl = (r) => [...CONTROLS(r), r.duration / 10, (r.duration / 10) ** 2];
  const a = evaluate(null, CONTROLS, (r) => r.y, withDur).r2;
  const b = evaluate(null, durCtl, (r) => r.y, withDur).r2;
  console.log(`  predicting CHILDREN from era + age gap                : ${a.toFixed(5)}`);
  console.log(`  predicting CHILDREN from era + age gap + how long they were married : ${b.toFixed(5)}   (+${(b - a).toFixed(5)})`);
  for (const [name, fn] of Object.entries(SETS)) {
    const v = evaluate(fn, durCtl, (r) => r.y, withDur).r2;
    console.log(`  ${name.padEnd(34)} on top of all of that : ${v.toFixed(5)}   (${(v - b >= 0 ? "+" : "") + (v - b).toFixed(5)})`);
  }
}

// ── the permutation null, for both targets ──────────────────────────────────────────────────────
console.log(`\n════ THE PERMUTATION NULL — fathers shuffled against mothers, pipeline re-run ════`);
const NPERM = 200;
const realDeltas = rows.map((r) => r.delta);
for (const t of TARGETS) {
  console.log(`\n  target: ${t.name}`);
  for (const [name, fn] of Object.entries(SETS)) {
    const nulls = [];
    for (let p = 0; p < NPERM; p++) {
      const perm = [...Array(rows.length).keys()];
      for (let i = perm.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [perm[i], perm[j]] = [perm[j], perm[i]]; }
      for (let i = 0; i < rows.length; i++) rows[i].delta = realDeltas[perm[i]];
      nulls.push(evaluate(fn, null, t.get, t.sample).r2);
    }
    for (let i = 0; i < rows.length; i++) rows[i].delta = realDeltas[i];
    nulls.sort((a, b) => a - b);
    const real = results[t.name][name];
    const above = nulls.filter((v) => v >= real).length;
    console.log(`  ${name.padEnd(34)} real ${real.toFixed(5)}   null median ${nulls[NPERM >> 1].toFixed(5)}   95th ${nulls[Math.floor(NPERM * 0.95)].toFixed(5)}   p = ${((above + 1) / (NPERM + 1)).toFixed(4)}`);
  }
}

// ── the weights ─────────────────────────────────────────────────────────────────────────────────
console.log(`\n════ FITTED WEIGHTS, gender-sensitive, whole sample ════`);
for (const t of TARGETS) {
  for (const [label, bodies] of [["all 10 bodies", ALL_BODIES], ["no outer planets", INNER]]) {
    const build = (r) => [1, ...sinF(bodies)(r)];
    const w = fitSquared(t.sample.map(build), t.sample.map(t.get));
    console.log(`  ${t.name} / ${label}:  b = ${w[0].toFixed(4)}   amplitude ${Math.hypot(...w.slice(1)).toFixed(4)}`);
    console.log(`    ${bodies.map((b, i) => `${b} ${w[i + 1].toFixed(3)}`).join("  ")}`);
  }
}
