/**
 * logistic.mjs — can the sin model tell a couple who had TWO OR MORE children from one who did not?
 *
 * The same features as model.mjs, the same 80/20 split grouped by person, the same placeholder
 * exclusion — but a classifier rather than a count model:
 *
 *     P(children >= 2)  =  sigma( b + SUM_i w_i * sin( theta_i(father) - theta_i(mother) ) )
 *
 * Fitted by iteratively reweighted least squares, which is Newton's method on the log-likelihood and
 * converges in a handful of steps for a problem this size.
 *
 * WHY NOT ACCURACY. About a quarter of these couples have two or more recorded children, so a model
 * that says "no" to everybody scores 76% and knows nothing. Accuracy is reported for completeness and
 * should be read against that base rate, never on its own. The honest numbers are:
 *
 *   · AUC — the probability the model scores a randomly chosen two-child couple above a randomly
 *     chosen other one. 0.5 is a coin, and it is threshold-free, so it cannot be flattered by a
 *     convenient cutoff.
 *   · McFadden's pseudo-R^2 — how much of the log-likelihood the features explain. This is the
 *     closest thing to the R^2 reported for the count models, and it is measured out of sample.
 *   · Brier score — mean squared error of the predicted probability. Lower is better.
 *
 * And, as everywhere else here, a PERMUTATION NULL: fathers shuffled against mothers, the whole
 * thing re-fitted, so the reported AUC can be read against what this model produces from data whose
 * effect has been destroyed by construction.
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
const THRESHOLD = +(process.env.THRESHOLD ?? 2);

/**
 * TARGET=children (default) — did this couple have THRESHOLD or more recorded children?
 * TARGET=divorce            — did this marriage end in DIVORCE rather than in a death?
 * TARGET=lasted             — did this marriage last LASTED_YEARS or longer?
 *
 * The "lasted" target carries a caveat the others do not: a duration needs a marriage start date, and
 * 32.9% of those fall on 1 January — year-precision values rendered as a date, since P580 carries no
 * precision filter here. So a duration is accurate to about a year, and near a cut at 12 years that
 * misplaces the couples sitting right on the boundary. It blunts a real effect; it cannot invent one.
 *
 * The divorce target uses P1534, the qualifier where Wikidata states WHY a marriage ended, and it is
 * the only honest source for it. An end DATE is not evidence of divorce: most recorded end dates mark
 * a death, and the collector's own "endedBy: statement" flag would misclassify thousands of widowings
 * as separations. Only couples with an explicit cause are used; annulment, separation and repudiation
 * are dropped rather than folded into either class, because they are neither.
 */
const TARGET = process.env.TARGET ?? "children";
/**
 * LASTED_YEARS=auto (the default) cuts at the MEDIAN duration, so the two classes are 50/50.
 *
 * That is what makes plain accuracy readable. On an unbalanced target it is not: at the 12-year cut
 * 74.9% of marriages are positive, so a model that says "yes" to everybody scores 74.9% and every
 * accuracy has to be read against a moving baseline. Balanced, the baseline is 50% for every model,
 * and the number means what it looks like it means.
 */
let LASTED_YEARS = process.env.LASTED_YEARS && process.env.LASTED_YEARS !== "auto"
  ? +process.env.LASTED_YEARS : null;
const DIVORCE = new Set(["Q93190"]);
const DEATH = new Set(["Q24037741", "Q99521170", "Q4", "Q90110620"]);

let SEED = 20260805;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };

const parseDate = (iso) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};

/** Wikidata truncates a year-precision date to 1 January and a month-precision one to the 1st, and the
 *  precision flag does not always catch it — 1 January runs 1.57x over its share of the calendar and
 *  the 1st of any month 1.10x. Those births are placeholders: a planetary position the person was
 *  never at. Excluded by default; see the README. */
const EXCLUDE = process.env.EXCLUDE ?? "firsts";
const isPlaceholder = (iso) =>
  EXCLUDE === "none" ? false : EXCLUDE === "firsts" ? iso.endsWith("-01") : iso.endsWith("-01-01");

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
const dot = (w, x) => { let s = 0; for (let i = 0; i < w.length; i++) s += w[i] * x[i]; return s; };
const sigma = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));

/** Logistic regression by IRLS — Newton's method on the log-likelihood, with a small ridge so a
 *  near-singular design cannot blow the step up. */
function fitLogistic(X, y, { iters = 8, ridge = 1e-4 } = {}) {
  const p = X[0].length;
  let w = new Array(p).fill(0);
  w[0] = Math.log((y.reduce((s, v) => s + v, 0) + 1) / (y.length - y.reduce((s, v) => s + v, 0) + 1));
  for (let it = 0; it < iters; it++) {
    const A = Array.from({ length: p }, () => new Float64Array(p));
    const g = new Float64Array(p);
    for (let i = 0; i < X.length; i++) {
      const xi = X[i], mu = sigma(dot(w, xi)), wt = Math.max(mu * (1 - mu), 1e-6), r = y[i] - mu;
      for (let j = 0; j < p; j++) {
        g[j] += xi[j] * r;
        for (let k = j; k < p; k++) A[j][k] += wt * xi[j] * xi[k];
      }
    }
    for (let j = 0; j < p; j++) { for (let k = 0; k < j; k++) A[j][k] = A[k][j]; A[j][j] += ridge; }
    const step = solve(A.map((r) => [...r]), [...g]);
    let moved = 0;
    for (let j = 0; j < p; j++) { w[j] += step[j]; moved += Math.abs(step[j]); }
    if (moved < 1e-8) break;
  }
  return w;
}

/** Rank-based AUC: the probability a random positive outranks a random negative. Ties count a half. */
function auc(scores, labels) {
  const order = scores.map((s, i) => [s, labels[i]]).sort((a, b) => a[0] - b[0]);
  let rankSum = 0, nPos = 0, i = 0;
  while (i < order.length) {
    let j = i;
    while (j < order.length && order[j][0] === order[i][0]) j++;
    const avgRank = (i + j + 1) / 2;                 // 1-based average rank across the tie block
    for (let k = i; k < j; k++) if (order[k][1] === 1) { rankSum += avgRank; nPos++; }
    i = j;
  }
  const nNeg = order.length - nPos;
  if (!nPos || !nNeg) return 0.5;
  return (rankSum - nPos * (nPos + 1) / 2) / (nPos * nNeg);
}

// ── the data ────────────────────────────────────────────────────────────────────────────────────
const raw = JSON.parse(readFileSync(process.argv[2] ?? "./research/data/dataset.json", "utf8"));
const YEAR_MIN = 1800, YEAR_MAX = 2012;
const rows = [];
let dropped = 0;
for (const r of raw) {
  const f = parseDate(r.fDob), m = parseDate(r.mDob);
  if (!f || !m || f.y < YEAR_MIN || f.y > YEAR_MAX || m.y < YEAR_MIN || m.y > YEAR_MAX) continue;
  if (isPlaceholder(r.fDob) || isPlaceholder(r.mDob)) { dropped++; continue; }
  if (TARGET === "divorce" && !DIVORCE.has(r.cause) && !DEATH.has(r.cause)) continue;
  const fJd = julianDay(f.y, f.m, f.d, 12), mJd = julianDay(m.y, m.m, m.d, 12);
  const fl = ALL_BODIES.map((b) => siderealLongitude(b, fJd));
  const ml = ALL_BODIES.map((b) => siderealLongitude(b, mJd));
  const jd = (x) => { const q = parseDate(x); return q ? julianDay(q.y, q.m, q.d, 12) : null; };
  const st = jd(r.start), en = [r.end, r.fDod, r.mDod].map(jd).filter((v) => v !== null);
  // Same physical-possibility rule as model.mjs: a 1,535-year marriage and marriages beginning before
  // a partner was born are records that contradict themselves, not data.
  const dur = (() => {
    if (st === null || !en.length) return null;
    const y = (Math.min(...en) - st) / 365.2425;
    if (y <= 0 || y > 80) return null;
    if ((st - fJd) / 365.2425 < 12 || (st - mJd) / 365.2425 < 12) return null;
    return y;
  })();
  if (TARGET === "lasted" && dur === null) continue;
  rows.push({
    father: r.father, mother: r.mother,
    children: r.children,
    duration: dur,
    label: TARGET === "divorce" ? (DIVORCE.has(r.cause) ? 1 : 0)
      : TARGET === "lasted" ? 0        // filled in below, once the median is known
        : (r.children >= THRESHOLD ? 1 : 0),
    delta: fl.map((x, i) => ((x - ml[i]) % 360 + 360) % 360),
    mid: fl.map((x, i) => midpoint(x, ml[i])),
    fYear: f.y, mYear: m.y, gap: (fJd - mJd) / 365.2425,
  });
}

if (TARGET === "lasted") {
  const sorted = rows.map((r) => r.duration).sort((a, b) => a - b);
  if (LASTED_YEARS === null) LASTED_YEARS = sorted[sorted.length >> 1];
  for (const r of rows) r.label = r.duration >= LASTED_YEARS ? 1 : 0;
}

const base = rows.reduce((s, r) => s + r.label, 0) / rows.length;
const QUESTION = TARGET === "divorce" ? "did this marriage end in DIVORCE rather than a death?"
  : TARGET === "lasted" ? `did this marriage last ${LASTED_YEARS.toFixed(1)} years or longer?`
    : `did this couple have ${THRESHOLD} or more recorded children?`;
const POS = TARGET === "divorce" ? "divorced"
  : TARGET === "lasted" ? `lasted ${LASTED_YEARS.toFixed(1)}y+` : `${THRESHOLD}+ children`;
console.log(`\nLOGISTIC REGRESSION — ${QUESTION}`);
console.log(`  couples                    : ${rows.length.toLocaleString()}  (${dropped.toLocaleString()} dropped as placeholder birth dates)`);
console.log(`  ${POS.padEnd(24)}   : ${rows.filter((r) => r.label).length.toLocaleString()} (${(100 * base).toFixed(1)}%)`);
// The trivial classifier is the MAJORITY class, which is not always the negative one: 75% of these
// marriages lasted 12 years or more, so "always say yes" is the bar to beat there and "always say no"
// is the bar everywhere else. Naming the wrong one would flatter every accuracy below.
{
  const majority = base > 0.5 ? "yes" : "no";
  console.log(`  so "always say ${majority}" scores ${(100 * Math.max(base, 1 - base)).toFixed(1)}% accurate and knows nothing — read AUC, not accuracy`);
}

// ── the distribution of both targets ────────────────────────────────────────────────────────────
//
// Printed because the shape is the result's context. Two thirds of these couples have NO recorded
// child, which is not two thirds childless — it is Wikidata not having an item for the child (the
// verifier measures this: co-parentage recovers about 30% of the stated counts). A target that is
// mostly a zero produced by missing data is a target that can only be predicted so far, and the
// binary cut at ${THRESHOLD} exists to ask the question in the form least damaged by that.
if (TARGET === "children") {
  const hist = new Map();
  for (const r of rows) { const k = Math.min(r.children, 10); hist.set(k, (hist.get(k) ?? 0) + 1); }
  console.log(`\n── distribution of the target: NUMBER OF CHILDREN (n = ${rows.length.toLocaleString()}) ──`);
  console.log(`  children    couples      share    cumulative`);
  let cum = 0;
  for (const k of [...hist.keys()].sort((a, b) => a - b)) {
    const v = hist.get(k); cum += v;
    const bar = "#".repeat(Math.round(60 * v / rows.length));
    console.log(`  ${(k === 10 ? "10+" : String(k)).padStart(4)}   ${String(v).padStart(9)}   ${(100 * v / rows.length).toFixed(2).padStart(6)}%   ${(100 * cum / rows.length).toFixed(1).padStart(6)}%  ${bar}`);
  }
  const mean = rows.reduce((s, r) => s + r.children, 0) / rows.length;
  console.log(`  mean ${mean.toFixed(3)}   sd ${Math.sqrt(rows.reduce((s, r) => s + (r.children - mean) ** 2, 0) / rows.length).toFixed(3)}   max ${Math.max(...rows.map((r) => r.children))}`);
  console.log(`  THE CUT: ${(100 * base).toFixed(1)}% at ${THRESHOLD}+, ${(100 * (1 - base)).toFixed(1)}% below — a ${(base / (1 - base)).toFixed(2)}:1 imbalance`);

  const wd = rows.filter((r) => r.duration !== null).map((r) => r.duration).sort((a, b) => a - b);
  if (wd.length) {
    console.log(`\n── distribution of the other target: YEARS OF MARRIAGE (n = ${wd.length.toLocaleString()}) ──`);
    const bins = [0, 5, 10, 20, 30, 40, 50, 60, 200];
    console.log(`  years       couples      share`);
    for (let i = 0; i < bins.length - 1; i++) {
      const v = wd.filter((d) => d >= bins[i] && d < bins[i + 1]).length;
      const lab = bins[i + 1] === 200 ? `${bins[i]}+` : `${bins[i]}-${bins[i + 1]}`;
      console.log(`  ${lab.padStart(7)}   ${String(v).padStart(9)}   ${(100 * v / wd.length).toFixed(2).padStart(6)}%  ${"#".repeat(Math.round(60 * v / wd.length))}`);
    }
    const dm = wd.reduce((s, v) => s + v, 0) / wd.length;
    console.log(`  mean ${dm.toFixed(1)}   median ${wd[wd.length >> 1].toFixed(1)}   sd ${Math.sqrt(wd.reduce((s, v) => s + (v - dm) ** 2, 0) / wd.length).toFixed(1)}   range ${wd[0].toFixed(1)}-${wd[wd.length - 1].toFixed(1)}`);
  }
}

// ── features and the split ──────────────────────────────────────────────────────────────────────

const idx = (b) => ALL_BODIES.indexOf(b);
const sinF = (bs) => (r) => bs.map((b) => Math.sin(r.delta[idx(b)] * D2R));
const cosF = (bs) => (r) => bs.map((b) => Math.cos(r.delta[idx(b)] * D2R));
const bothF = (bs) => (r) => [...sinF(bs)(r), ...cosF(bs)(r)];
const midF = (bs) => (r) => bs.map((b) => Math.cos(r.mid[idx(b)]));
const midBothF = (bs) => (r) => bs.flatMap((b) => [Math.cos(r.mid[idx(b)]), Math.sin(r.mid[idx(b)])]);
const DECADES = [];
for (let y = 1800; y <= 2010; y += 10) DECADES.push(y);
const CONTROLS = (r) => {
  const t = (r.fYear + r.mYear) / 2;
  return [...DECADES.map((d) => (t >= d && t < d + 10 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];
};

/**
 * Assign an 80/20 split, grouped by person so nobody straddles it.
 *
 * Taken as a FUNCTION of a seed, because one split is not a measurement. Re-running this study after
 * a small change to the collected data moved a held-out AUC from 0.586 to 0.572 on identical
 * modelling — split noise, not a finding. Comparisons between feature families are therefore made
 * over many splits below, and a single split is reported only for the detailed reports where a
 * concrete confusion matrix is the point.
 */
let TR = [], TE = [];
function makeSplit(seed) {
  SEED = seed;
  const side = new Map();
  for (const r of rows) {
    let s = side.get(r.father) ?? side.get(r.mother);
    if (s === undefined) s = rnd() < 0.8 ? "train" : "test";
    side.set(r.father, s); side.set(r.mother, s);
    r.side = s;
  }
  TR = rows.filter((r) => r.side === "train");
  TE = rows.filter((r) => r.side === "test");
}
makeSplit(20260805);

function evaluate(featureFn, controlFn) {
  const build = (r) => [1, ...(featureFn ? featureFn(r) : []), ...(controlFn ? controlFn(r) : [])];
  const w = fitLogistic(TR.map(build), TR.map((r) => r.label));
  const scores = TE.map((r) => sigma(dot(w, build(r))));
  const labels = TE.map((r) => r.label);
  const trainBase = TR.reduce((s, r) => s + r.label, 0) / TR.length;
  let ll = 0, llNull = 0, brier = 0, correct = 0;
  for (let i = 0; i < labels.length; i++) {
    const p = Math.min(1 - 1e-12, Math.max(1e-12, scores[i]));
    ll += labels[i] ? Math.log(p) : Math.log(1 - p);
    llNull += labels[i] ? Math.log(trainBase) : Math.log(1 - trainBase);
    brier += (labels[i] - scores[i]) ** 2;
    if ((scores[i] >= 0.5 ? 1 : 0) === labels[i]) correct++;
  }
  return {
    auc: auc(scores, labels),
    mcfadden: 1 - ll / llNull,
    brier: brier / labels.length,
    acc: correct / labels.length,
    w,
  };
}

const SETS = {
  "gendered   sin, all 10 bodies": sinF(ALL_BODIES),
  "genderless cos, all 10 bodies": cosF(ALL_BODIES),
  "both harmonics, all 10 bodies": bothF(ALL_BODIES),
  "gendered   sin, no outer planets": sinF(INNER),
  "genderless cos, no outer planets": cosF(INNER),
  "both harmonics, no outer planets": bothF(INNER),
  "MIDPOINT cos, all 10 bodies": midF(ALL_BODIES),
  "MIDPOINT cos, no outer planets": midF(INNER),
  // The two families together: cos of the midpoint AND sin of the difference, one weight each per
  // body. It nests both, so it can never score worse than either in training — the question is
  // whether it scores better OUT of sample, or whether the two are describing the same clock twice.
  "MIDPOINT cos + DIFFERENCE sin, all 10": (r) => [...midF(ALL_BODIES)(r), ...sinF(ALL_BODIES)(r)],
  "MIDPOINT cos + DIFFERENCE sin, no outer": (r) => [...midF(INNER)(r), ...sinF(INNER)(r)],
};

// ── the comparison, averaged over repeated splits ───────────────────────────────────────────────
{
  const REPS = +(process.env.REPS ?? 20);
  console.log(`\n── held-out AUC over ${REPS} independent 80/20 splits (mean +/- sd) ──`);
  const acc = new Map();
  for (let i = 0; i < REPS; i++) {
    makeSplit(20260805 + i * 7919);
    for (const [name, fn] of Object.entries(SETS)) {
      (acc.get(name) ?? acc.set(name, []).get(name)).push(evaluate(fn, null).auc);
    }
    (acc.get("era & age gap alone") ?? acc.set("era & age gap alone", []).get("era & age gap alone"))
      .push(evaluate(null, CONTROLS).auc);
  }
  const stat = (v) => {
    const m = v.reduce((s, x) => s + x, 0) / v.length;
    return [m, Math.sqrt(v.reduce((s, x) => s + (x - m) ** 2, 0) / v.length)];
  };
  const ordered = [...acc.entries()].map(([k, v]) => [k, ...stat(v)]).sort((a, b) => b[1] - a[1]);
  console.log(`  model                                        AUC     sd`);
  for (const [k, m, sd] of ordered) console.log(`  ${k.padEnd(40)} ${m.toFixed(4)}   ${sd.toFixed(4)}`);
  makeSplit(20260805);
}

// ── SIMPLE=1 · accuracy, and nothing else ───────────────────────────────────────────────────────
if (process.env.SIMPLE) {
  const REPS = +(process.env.REPS ?? 20);
  const trAcc = new Map(), teAcc = new Map();
  for (let i = 0; i < REPS; i++) {
    makeSplit(20260805 + i * 7919);
    const run = (name, fn, ctl) => {
      const build = (r) => [1, ...(fn ? fn(r) : []), ...(ctl ? ctl(r) : [])];
      const w = fitLogistic(TR.map(build), TR.map((r) => r.label));
      const hit = (set) => set.filter((r) => (sigma(dot(w, build(r))) >= 0.5 ? 1 : 0) === r.label).length / set.length;
      (trAcc.get(name) ?? trAcc.set(name, []).get(name)).push(hit(TR));
      (teAcc.get(name) ?? teAcc.set(name, []).get(name)).push(hit(TE));
    };
    for (const [name, fn] of Object.entries(SETS)) run(name, fn, null);
    run("era & age gap alone, NO astrology", null, CONTROLS);
  }
  const stat = (v) => {
    const m = v.reduce((s, x) => s + x, 0) / v.length;
    return [m, Math.sqrt(v.reduce((s, x) => s + (x - m) ** 2, 0) / v.length)];
  };
  console.log(`\n${"═".repeat(74)}`);
  console.log(`ACCURACY — ${QUESTION}`);
  console.log(`${rows.length.toLocaleString()} couples, ${(100 * base).toFixed(1)}% positive. ` +
    `${REPS} independent 80/20 splits, threshold 0.50.`);
  console.log(`${"═".repeat(74)}`);
  console.log(`  model                                       train      TEST     sd`);
  const ordered = [...teAcc.entries()].map(([k, v]) => [k, stat(v), stat(trAcc.get(k))])
    .sort((a, b) => b[1][0] - a[1][0]);
  for (const [k, [te, sd], [tr]] of ordered) {
    console.log(`  ${k.padEnd(40)} ${(100 * tr).toFixed(2)}%   ${(100 * te).toFixed(2)}%   ${(100 * sd).toFixed(2)}`);
  }
  const coin = Math.max(base, 1 - base);
  console.log(`  ${"the trivial classifier (majority class)".padEnd(40)}          ${(100 * coin).toFixed(2)}%`);
  process.exit(0);
}

console.log(`\n── held out on ${TE.length.toLocaleString()} couples (${TR.length.toLocaleString()} train, 80/20 split by person) ──`);
console.log(`  model                                 AUC     pseudo-R²    Brier    accuracy`);
const results = {};
for (const [name, fn] of Object.entries(SETS)) {
  const r = evaluate(fn, null);
  results[name] = r;
  console.log(`  ${name.padEnd(34)} ${r.auc.toFixed(4)}    ${r.mcfadden.toFixed(5).padStart(8)}   ${r.brier.toFixed(4)}    ${(100 * r.acc).toFixed(1)}%`);
}
{
  const r = evaluate(null, CONTROLS);
  console.log(`  ${"era & age gap alone, NO astrology".padEnd(34)} ${r.auc.toFixed(4)}    ${r.mcfadden.toFixed(5).padStart(8)}   ${r.brier.toFixed(4)}    ${(100 * r.acc).toFixed(1)}%`);
  console.log(`\n  with era & age gap alongside the astrology:`);
  for (const [name, fn] of Object.entries(SETS)) {
    const c = evaluate(fn, CONTROLS);
    console.log(`  ${name.padEnd(34)} ${c.auc.toFixed(4)}    ${c.mcfadden.toFixed(5).padStart(8)}   ${c.brier.toFixed(4)}    ${(100 * c.acc).toFixed(1)}%   (AUC ${(c.auc - r.auc >= 0 ? "+" : "") + (c.auc - r.auc).toFixed(4)} over era alone)`);
  }
}


// ── the classification report, sin model only ───────────────────────────────────────────────────
//
// A classification report needs a THRESHOLD, and that choice is where a report like this usually
// stops being honest. Two are shown:
//
//   0.50 — the default. This model never crosses it for anybody, so the positive class gets zero
//          precision and zero recall and the accuracy equals the base rate exactly. That is not a
//          formatting quirk; it is the result. A model with AUC 0.586 ranks slightly better than a
//          coin but is nowhere near confident enough to ever say "yes".
//
//   F1*  — the threshold that maximises F1 ON THE TRAINING SET, then applied unchanged to the test
//          set. Choosing it on test would be tuning on the answer, and would flatter every number
//          below. This is what the model can do when it is forced to make positive calls.
//
// Train and test are printed side by side, because the gap between them is the only way to see
// whether ten fitted weights have started memorising 62,000 couples.
function classificationReport(featureFn, label) {
  const build = (r) => [1, ...featureFn(r)];
  const w = fitLogistic(TR.map(build), TR.map((r) => r.label));
  const score = (r) => sigma(dot(w, build(r)));
  const trS = TR.map(score), teS = TE.map(score);
  const trY = TR.map((r) => r.label), teY = TE.map((r) => r.label);

  // F1-optimal threshold, chosen on TRAIN only.
  let best = { f1: -1, t: 0.5 };
  for (let t = 0.02; t < 0.98; t += 0.005) {
    let tp = 0, fp = 0, fn = 0;
    for (let i = 0; i < trS.length; i++) {
      const p = trS[i] >= t ? 1 : 0;
      if (p && trY[i]) tp++; else if (p) fp++; else if (trY[i]) fn++;
    }
    const f1 = tp ? (2 * tp) / (2 * tp + fp + fn) : 0;
    if (f1 > best.f1) best = { f1, t };
  }

  const table = (scores, ys, t) => {
    let tp = 0, fp = 0, fn = 0, tn = 0;
    for (let i = 0; i < scores.length; i++) {
      const p = scores[i] >= t ? 1 : 0;
      if (p && ys[i]) tp++; else if (p && !ys[i]) fp++; else if (!p && ys[i]) fn++; else tn++;
    }
    const safe = (a, b) => (b ? a / b : 0);
    const rows = [
      { cls: TARGET === "divorce" ? "0  (ended by death)" : TARGET === "lasted" ? `0  (under ${LASTED_YEARS.toFixed(1)}y)` : `0  (under ${THRESHOLD})`, prec: safe(tn, tn + fn), rec: safe(tn, tn + fp), n: tn + fp },
      { cls: TARGET === "divorce" ? "1  (divorced)" : TARGET === "lasted" ? `1  (${LASTED_YEARS.toFixed(1)}y or longer)` : `1  (${THRESHOLD} or more)`, prec: safe(tp, tp + fp), rec: safe(tp, tp + fn), n: tp + fn },
    ];
    for (const r of rows) r.f1 = r.prec + r.rec ? (2 * r.prec * r.rec) / (r.prec + r.rec) : 0;
    const total = tp + fp + fn + tn;
    return { rows, acc: (tp + tn) / total, total, cm: { tp, fp, fn, tn } };
  };

  console.log(`\n${"═".repeat(78)}`);
  console.log(`CLASSIFICATION REPORT — ${label}`);
  console.log(`${"═".repeat(78)}`);

  for (const [tname, t] of [["threshold 0.50 (default)", 0.5], [`threshold ${best.t.toFixed(3)} (F1-optimal, chosen on TRAIN)`, best.t]]) {
    console.log(`\n  ${tname}`);
    console.log(`                       ┌──────────── TRAIN ────────────┐  ┌──────────── TEST ─────────────┐`);
    console.log(`  class                 precision  recall      f1  support   precision  recall      f1  support`);
    const a = table(trS, trY, t), b = table(teS, teY, t);
    for (let i = 0; i < 2; i++) {
      const x = a.rows[i], y = b.rows[i];
      console.log(`  ${x.cls.padEnd(20)}     ${x.prec.toFixed(3)}   ${x.rec.toFixed(3)}   ${x.f1.toFixed(3)}   ${String(x.n).padStart(6)}` +
        `      ${y.prec.toFixed(3)}   ${y.rec.toFixed(3)}   ${y.f1.toFixed(3)}   ${String(y.n).padStart(6)}`);
    }
    const macro = (r) => r.rows.reduce((s, x) => s + x.f1, 0) / 2;
    const weighted = (r) => r.rows.reduce((s, x) => s + x.f1 * x.n, 0) / r.total;
    console.log(`  ${"macro avg f1".padEnd(20)}                     ${macro(a).toFixed(3)}   ${String(a.total).padStart(6)}` +
      `                      ${macro(b).toFixed(3)}   ${String(b.total).padStart(6)}`);
    console.log(`  ${"weighted avg f1".padEnd(20)}                     ${weighted(a).toFixed(3)}   ${String(a.total).padStart(6)}` +
      `                      ${weighted(b).toFixed(3)}   ${String(b.total).padStart(6)}`);
    console.log(`  ${"accuracy".padEnd(20)}                     ${a.acc.toFixed(3)}   ${String(a.total).padStart(6)}` +
      `                      ${b.acc.toFixed(3)}   ${String(b.total).padStart(6)}`);
    console.log(`    confusion  TRAIN  tp ${a.cm.tp}  fp ${a.cm.fp}  fn ${a.cm.fn}  tn ${a.cm.tn}`);
    console.log(`               TEST   tp ${b.cm.tp}  fp ${b.cm.fp}  fn ${b.cm.fn}  tn ${b.cm.tn}`);
  }
  const trAuc = auc(trS, trY), teAuc = auc(teS, teY);
  console.log(`\n  AUC       TRAIN ${trAuc.toFixed(4)}   TEST ${teAuc.toFixed(4)}   (gap ${(trAuc - teAuc).toFixed(4)})`);
  console.log(`  base rate TRAIN ${(trY.reduce((s, v) => s + v, 0) / trY.length).toFixed(4)}   TEST ${(teY.reduce((s, v) => s + v, 0) / teY.length).toFixed(4)}`);
}

classificationReport(sinF(ALL_BODIES), "DIFFERENCE sin, all 10 bodies");
classificationReport(midF(ALL_BODIES), "MIDPOINT cos, all 10 bodies");
classificationReport((r) => [...midF(ALL_BODIES)(r), ...sinF(ALL_BODIES)(r)], "MIDPOINT cos + DIFFERENCE sin, all 10 bodies");
classificationReport((r) => [...midF(INNER)(r), ...sinF(INNER)(r)], "MIDPOINT cos + DIFFERENCE sin, no outer planets");

// ── the permutation null ────────────────────────────────────────────────────────────────────────
console.log(`\n── the permutation null: fathers shuffled against mothers, re-fitted ──`);
const NPERM = 200;
const real = rows.map((r) => r.delta);
for (const [name, fn] of Object.entries(SETS)) {
  const nulls = [];
  for (let p = 0; p < NPERM; p++) {
    const perm = [...Array(rows.length).keys()];
    for (let i = perm.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [perm[i], perm[j]] = [perm[j], perm[i]]; }
    for (let i = 0; i < rows.length; i++) rows[i].delta = real[perm[i]];
    nulls.push(evaluate(fn, null).auc);
  }
  for (let i = 0; i < rows.length; i++) rows[i].delta = real[i];
  nulls.sort((a, b) => a - b);
  const got = results[name].auc;
  const above = nulls.filter((v) => v >= got).length;
  console.log(`  ${name.padEnd(34)} AUC ${got.toFixed(4)}   null median ${nulls[NPERM >> 1].toFixed(4)}   95th ${nulls[Math.floor(NPERM * 0.95)].toFixed(4)}   p = ${((above + 1) / (NPERM + 1)).toFixed(4)}`);
}

// ── the coefficients, as odds ratios ────────────────────────────────────────────────────────────
console.log(`\n── the sin model's coefficients, as odds ratios per unit of sin(delta) ──`);
for (const [label, bodies] of [["all 10 bodies", ALL_BODIES], ["no outer planets", INNER]]) {
  const w = results[`gendered   sin, ${label}`].w;
  console.log(`  ${label}:  intercept ${w[0].toFixed(4)}  (base odds ${Math.exp(w[0]).toFixed(3)})`);
  console.log(`    ${bodies.map((b, i) => `${b} ${Math.exp(w[i + 1]).toFixed(3)}`).join("  ")}`);
}
console.log(`\n  An odds ratio of 1.000 is a body that changes nothing. A feature spans -1 to +1, so the`);
console.log(`  full swing a body can produce is its ratio against its own reciprocal.`);
