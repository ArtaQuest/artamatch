/**
 * divorce-model.mjs — divorce or death, from two birth dates, on a 50/50 balanced set.
 *
 * ── The sample ──────────────────────────────────────────────────────────────────────────────────
 *
 * Built by collect-divorce.mjs from Wikidata's P1534 "end cause" qualifier — the largest open source
 * that says WHY a marriage ended and gives both partners' birth dates. FamiLinx, WikiTree and the
 * GEDCOM corpora are all larger and all useless here: they record births, deaths, marriages and
 * parentage, and divorce is the one life event genealogy does not capture. No ongoing marriages can
 * enter, because every row carries a stated cause.
 *
 * Exactly 50/50 by construction: deaths outnumber divorces roughly 7 to 4, so the divorce class is the
 * binding constraint and deaths are subsampled to match it, seeded.
 *
 * ── Which birth dates count, and why the rule is JANUARY 1 ONLY ───────────────────────────────────
 *
 * Wikidata's precision field says whether a date is known to the day, and it is the first filter. But
 * the field is not always honest — somebody entering "born 1904" as a day-precision 1 January leaves no
 * trace in it, and the distribution shows exactly that. Measured over the 198,985 birth dates in the
 * main study, against the 0.274% share a calendar day should hold:
 *
 *     1 January             0.430%   1.57x expected   <- year-precision placeholders, excluded
 *     the 1st of any month  ~3.6%    1.10x expected   <- month-precision leakage, KEPT
 *
 * Only 1 January is dropped: it is where the year-precision contamination lives, and dropping every
 * 1st-of-month date to chase a 1.10x excess costs eight times the sample for a fraction of the benefit.
 *
 * CAUTION: those figures are from the main study, which admitted only DAY-PRECISION births. This set
 * admits any precision in order to be as large as possible, so genuine year-precision dates are present
 * and every one of them renders as 1 January. The 1 January share here is therefore far higher than
 * 0.43%, and it is measured and printed below rather than assumed.
 *
 * ── Balance is restored AFTER filtering, not before ───────────────────────────────────────────────
 *
 * The collector balances the classes, then this filter removes rows — and it does not remove them
 * evenly, because a death-ended marriage is an older record and likelier to carry a placeholder date.
 * Filtering a balanced set therefore UNBALANCES it: the first run of this came out 53.50% positive
 * while still being described as 50/50, which would have had every accuracy read against the wrong
 * coin. So the subsample to exact equality happens last, after every filter has been applied.
 *
 * ── Pair ordering ───────────────────────────────────────────────────────────────────────────────
 *
 * The divorce query does not filter on sex, so there is no father/mother to order by. The pair is
 * ordered OLDER FIRST, which is well defined for every couple including same-sex ones and does not
 * depend on which partner Wikidata happened to state the marriage on. The difference features therefore
 * read "older minus younger" rather than "father minus mother" — a change of convention from the rest of
 * the study, and stated because it changes what the antisymmetric features mean.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/divorce-model.mjs ./research/data-divorce
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
/** Only 1 January is treated as a placeholder. See the header for the measured justification. */
const isJan1 = (iso) => iso.endsWith("-01-01");

function load(name, { dayOnly }) {
  const raw = JSON.parse(readFileSync(`${DIR}/${name}.json`, "utf8"));
  const out = [];
  const drop = { badDate: 0, jan1: 0, precision: 0 };
  let jan1Dates = 0, totalDates = 0;
  for (const r of raw) {
    const A = parseDate(r.aDob), B = parseDate(r.bDob);
    if (!A || !B) { drop.badDate++; continue; }
    totalDates += 2;
    if (isJan1(r.aDob)) jan1Dates++;
    if (isJan1(r.bDob)) jan1Dates++;
    if (isJan1(r.aDob) || isJan1(r.bDob)) { drop.jan1++; continue; }
    if (dayOnly && !(r.aPrec >= 11 && r.bPrec >= 11)) { drop.precision++; continue; }
    let ja = julianDay(A.y, A.m, A.d, 12), jb = julianDay(B.y, B.m, B.d, 12);
    let pa = r.a, pb = r.b;
    // Older first, so the ordering never depends on which partner the statement was written on.
    if (jb < ja) { [ja, jb] = [jb, ja]; [pa, pb] = [pb, pa]; }
    out.push({
      a: pa, b: pb, y: r.y,
      year: (A.y + B.y) / 2,
      gap: (jb - ja) / YR,
      fl: PLANETS.map((x) => siderealLongitude(x, ja)),
      ml: PLANETS.map((x) => siderealLongitude(x, jb)),
    });
  }
  // Exact 50/50, applied last so no later filter can undo it. Seeded.
  const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  SEED = 20260807;
  const pos = out.filter((r) => r.y === 1), neg = out.filter((r) => r.y === 0);
  const k = Math.min(pos.length, neg.length);
  const balanced = shuffle([...shuffle(pos).slice(0, k), ...shuffle(neg).slice(0, k)]);
  return { rows: balanced, drop, jan1Share: jan1Dates / Math.max(1, totalDates), beforeBalance: { pos: pos.length, neg: neg.length } };
}

const idxOf = (bs) => bs.map((b) => PLANETS.indexOf(b));
const midOf = (fa, mb) => {
  const A = fa * D2R, B = mb * D2R;
  const cx = Math.cos(A) + Math.cos(B), cy = Math.sin(A) + Math.sin(B);
  const n = Math.hypot(cx, cy);
  return n < 1e-12 ? [0, 0] : [cx / n, cy / n];
};
const diagH1 = (bs) => { const I = idxOf(bs); return (r) => I.flatMap((j) => { const d = (r.fl[j] - r.ml[j]) * D2R; return [Math.cos(d), Math.sin(d)]; }); };
const crossH1 = (bs) => { const I = idxOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) { const d = (r.fl[j] - r.ml[k]) * D2R; o.push(Math.cos(d), Math.sin(d)); } return o; }; };
const crossSq = (bs) => { const I = idxOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) o.push(Math.cos(2 * (r.fl[j] - r.ml[k]) * D2R)); return o; }; };
/**
 * The cross-matrix of MIDPOINTS, alongside the cross-matrix of differences.
 *
 * For each ordered pair of bodies (j from the older partner, k from the younger) there are two
 * angles worth forming, and they carry different information:
 *
 *   the DIFFERENCE  theta_j(A) - theta_k(B)   how far apart the two placements are — an aspect
 *   the MIDPOINT    arg(e^{i theta_j(A)} + e^{i theta_k(B)})   where the pair sits in the zodiac
 *
 * The midpoint is a SUM, so it is symmetric under swapping the two people and depends on where the
 * planets actually were rather than on their separation. It is computed circularly, as the direction of
 * the vector sum — the arithmetic mean (theta_j + theta_k)/2 is ambiguous modulo 180 degrees and its
 * cosine flips sign on an arbitrary branch choice, which over the main study's couples disagreed with
 * the circular midpoint in sign 18.1% of the time.
 *
 * Both matrices together give 100 pairs x 4 coefficients = 400 astrological parameters.
 */
const crossMid = (bs) => { const I = idxOf(bs); return (r) => { const o = []; for (const j of I) for (const k of I) { const [cx, cy] = midOf(r.fl[j], r.ml[k]); o.push(cx, cy); } return o; }; };
const crossAll = (bs) => (r) => [...crossH1(bs)(r), ...crossMid(bs)(r)];
/**
 * FOUR TERMS PER BODY — the diagonal model, fully specified.
 *
 *   cos(theta_j(A))    where the older partner's body j sat in the zodiac
 *   cos(theta_j(B))    where the younger partner's did
 *   cos(mid_j)         where the pair's circular midpoint sits
 *   sin(delta_j)       the signed separation — antisymmetric, so it flips if the two swap
 *
 * Four coefficients per body, ten bodies, forty astrological parameters plus an intercept. The first
 * two are individual placements rather than anything relational; the third is symmetric under swapping
 * the partners; the fourth is antisymmetric. Together they span the symmetric and antisymmetric parts
 * of the pair plus each person's own position, which is the full first-harmonic vocabulary available
 * from two angles without going to the cross-matrix.
 */
const fourTerm = (bs) => {
  const I = idxOf(bs);
  return (r) => {
    const o = [];
    for (const j of I) {
      o.push(Math.cos(r.fl[j] * D2R));
      o.push(Math.cos(r.ml[j] * D2R));
      o.push(midOf(r.fl[j], r.ml[j])[0]);
      o.push(Math.sin((r.fl[j] - r.ml[j]) * D2R));
    }
    return o;
  };
};
const midDiff = (bs) => { const I = idxOf(bs); return (r) => [...I.map((j) => midOf(r.fl[j], r.ml[j])[0]), ...I.map((j) => Math.sin((r.fl[j] - r.ml[j]) * D2R))]; };

const BINS = [];
for (let y = 1500; y <= 2000; y += 20) BINS.push(y);
const ERA = (r) => [r.year < 1500 ? 1 : 0, ...BINS.map((b) => (r.year >= b && r.year < b + 20 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];

const RIDGES = [0.3, 1, 3, 10, 30, 100];

function report(rows, title) {
  const side = new Map();
  SEED = 20260807;
  for (const r of rows) {
    let s = side.get(r.a) ?? side.get(r.b);
    if (s === undefined) s = rnd() < 0.8 ? "train" : "test";
    side.set(r.a, s); side.set(r.b, s);
    r.side = s;
  }
  const TR = rows.filter((r) => r.side === "train"), TE = rows.filter((r) => r.side === "test");
  const pos = rows.filter((r) => r.y === 1).length;
  console.log(`\n${"═".repeat(84)}`);
  console.log(`  ${title}`);
  console.log(`  ${rows.length.toLocaleString()} couples, ${pos.toLocaleString()} divorce / ${(rows.length - pos).toLocaleString()} death ` +
    `(${(100 * pos / rows.length).toFixed(2)}% positive) — ${TR.length.toLocaleString()} train / ${TE.length.toLocaleString()} test, split by person`);
  console.log(`${"═".repeat(84)}`);
  console.log(`  model                                                cols   TRAIN acc   TEST acc   raw correct`);
  const MODELS = [
    ["FOUR TERMS PER BODY, 10 planets", fourTerm(PLANETS)],
    ["FOUR TERMS PER BODY, classical 7 (no calendar)", fourTerm(CLASSICAL)],
    ["diagonal synastry, 10 planets", diagH1(PLANETS)],
    ["midpoint + difference, 10 planets", midDiff(PLANETS)],
    ["FULL 10x10 synastry, differences only", crossH1(PLANETS)],
    ["FULL 10x10 synastry, MIDPOINTS only", crossMid(PLANETS)],
    ["FULL 10x10 synastry, DIFFERENCES + MIDPOINTS", crossAll(PLANETS)],
    ["FULL 10x10 synastry, square harmonic only", crossSq(PLANETS)],
    ["diagonal synastry, classical 7 (no calendar)", diagH1(CLASSICAL)],
    ["midpoint + difference, classical 7", midDiff(CLASSICAL)],
    ["FULL 7x7 synastry, classical, differences only", crossH1(CLASSICAL)],
    ["FULL 7x7 synastry, classical, MIDPOINTS only", crossMid(CLASSICAL)],
    ["FULL 7x7 synastry, classical, DIFFS + MIDPOINTS", crossAll(CLASSICAL)],
    ["FULL 7x7 synastry, classical, square harmonic", crossSq(CLASSICAL)],
    ["era + age gap, NO astrology", ERA],
    ["DIFFS + MIDPOINTS + era + age gap", (r) => [...crossAll(PLANETS)(r), ...ERA(r)]],
  ];
  for (const [name, fn] of MODELS) {
    const build = (r) => Float64Array.from([1, ...fn(r)]);
    const X = TR.map(build), y = Float64Array.from(TR.map((r) => r.y));
    // Ridge picked by 5-fold cross-validation INSIDE the training set, so the test set is untouched.
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
    // Raw counts as well as percentages: two different feature sets scoring the same percentage to four
    // decimals is either a real tie at the same information ceiling or a duplicated row, and only the
    // counts distinguish them.
    console.log(`  ${name.padEnd(48)} ${String(X[0].length - 1).padStart(4)}    ${(100 * hTR / TR.length).toFixed(2)}%     ${(100 * hTE / TE.length).toFixed(2)}%   ${hTR}/${TR.length}  ${hTE}/${TE.length}`);
  }
  console.log(`  ${"the coin".padEnd(48)}   —        —         50.00%`);
}

// The three label regimes, so the effect of the inferred labels on the result is visible rather than
// assumed. "stated" is the cleanest and smallest; "all" is the largest and includes remarriage and
// end-date evidence at 99.0% measured precision.
const A = load("balanced-all-precisions", { dayOnly: false });
console.log(`\nDIVORCE OR DEATH — the largest balanced set, from birth dates alone`);
console.log(`  1 January share of birth dates in this set: ${(100 * A.jan1Share).toFixed(2)}% — far above the 0.27% a`);
console.log(`  calendar day is due, because any-precision births are admitted and a year-precision date`);
console.log(`  renders as 1 January. Dropped ${A.drop.jan1.toLocaleString()} couples for one; 1st of other months KEPT.`);
console.log(`  after filtering, before re-balancing: ${A.beforeBalance.pos.toLocaleString()} divorce / ${A.beforeBalance.neg.toLocaleString()} death`);
report(A.rows, "ALL BIRTH-DATE PRECISIONS — the largest sample");
const B = load("balanced-all-precisions", { dayOnly: true });
console.log(`\n  restricting to day-precision births costs a further ${B.drop.precision.toLocaleString()} couples`);
report(B.rows, "DAY-PRECISION BIRTHS ONLY — the cleanest dates");
const C = load("balanced-stated-cause-only", { dayOnly: false });
report(C.rows, "EXPLICITLY STATED CAUSES ONLY — the cleanest labels, no inference");
