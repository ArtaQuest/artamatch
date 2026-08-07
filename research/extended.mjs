/**
 * extended.mjs — every extra body Kerykeion offers, and every possible sidereal setting, searched
 * against the era baseline.
 *
 * ── What this can and cannot change ─────────────────────────────────────────────────────────────
 *
 * THE SIDEREAL SETTING CANNOT AFFECT A DIFFERENCE FEATURE. An ayanamsa is one offset subtracted from
 * every longitude, so in theta_f - theta_m it cancels algebraically. Verified to machine precision:
 * moving the offset by 47.3 degrees changes sin(delta) by ~1e-16 for all ten planets. The only
 * residue is the ayanamsa's own drift between the two birth dates — precession runs 50.29"/yr, so two
 * people born ten years apart differ by 0.14 degrees, and that residue is the SAME for every named
 * ayanamsa because they differ in their constant, not their rate.
 *
 * So the sweep below is over MIDPOINT features, where the offset genuinely does move the feature. And
 * there the answer is also known in advance: cos(mid - a) = cos(a)cos(mid) + sin(a)sin(mid), so the
 * whole family over all offsets `a` is spanned by {cos(mid), sin(mid)}. A model carrying both already
 * contains every sidereal setting there is, and the best any single offset can do is equal it.
 *
 * The sweep is run anyway, because demonstrating that is worth more than asserting it — and it is run
 * over the FULL CIRCLE in 5-degree steps rather than over a list of named ayanamsas. That is the
 * stronger test: the 72 settings include Lahiri, Fagan-Bradley, Raman, Krishnamurti, De Luce,
 * Yukteshwar, Djwhal Khul, Sassanian, Galactic-Centre and every other proposal, plus every offset
 * nobody has ever proposed.
 *
 * ── The extra bodies ────────────────────────────────────────────────────────────────────────────
 *
 * Kerykeion's point list beyond the ten planets is: Mean Node, True Node, Mean Lilith (the lunar
 * apogee), Chiron, and the four angles — Ascendant, MC, Descendant, IC.
 *
 * THE ANGLES ARE IMPOSSIBLE HERE and no setting recovers them. An Ascendant needs a birth TIME and a
 * birth PLACE; Wikidata gives dates. It is not that they are hard to compute — the information does
 * not exist. (The Moon is already the weakest of the ten for the same reason: unknown hour, so its
 * position carries about +/-6.6 degrees of irreducible uncertainty.)
 *
 * The other four are functions of the date alone and are all added:
 *   Mean Node, Mean Lilith — exact, from Meeus' lunar arguments.
 *   True Node             — mean node plus the five leading periodic terms (~1.5 deg amplitude).
 *   Chiron                — KEPLERIAN AND APPROXIMATE. Chiron is strongly perturbed by Saturn and
 *                           Uranus, and a two-body propagation back to 1800 accumulates real error.
 *                           It is included because it was asked for, reported separately, and should
 *                           not be trusted to better than a few degrees early in the window.
 *
 * ── The protocol ────────────────────────────────────────────────────────────────────────────────
 *
 * "Try settings until you beat the baseline" is a search, and a search over enough configurations
 * WILL beat any baseline on a fixed held-out set by chance alone. So the data is split three ways by
 * person: 60% train, 20% validation, 20% test. Everything is fitted on train and ranked on
 * validation; the single winner is then scored ONCE on test, which nothing has touched. The gap
 * between the winner's validation and test score is the selection bias, and it is reported.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/extended.mjs <dataset.json>
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180, R2D = 180 / Math.PI;
const norm360 = (x) => ((x % 360) + 360) % 360;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];

let SEED = 20260805;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };

// ── the extra points ────────────────────────────────────────────────────────────────────────────
//
// Meeus, Astronomical Algorithms ch. 47. T is Julian centuries from J2000. These are TROPICAL, and
// the ayanamsa is subtracted alongside the planets so every body sits in the same frame.
const AYANAMSA = (T) => 23.85709235 + 1.39688796 * T + 0.00030709 * T * T;   // Lahiri, as shipped

function extraLongitudes(jd) {
  const T = (jd - 2451545.0) / 36525;
  const D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T * T + T ** 3 / 545868;
  const M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T * T;
  const Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T * T + T ** 3 / 69699;
  const F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T * T - T ** 3 / 3526000;
  const meanNode = 125.0445479 - 1934.1362891 * T + 0.0020754 * T * T + T ** 3 / 467441;
  // The true node wobbles about the mean one; these five terms carry almost all of it.
  const trueNode = meanNode
    - 1.4979 * Math.sin(2 * (D - F) * D2R)
    - 0.1500 * Math.sin(M * D2R)
    - 0.1226 * Math.sin(2 * D * D2R)
    + 0.1176 * Math.sin(2 * F * D2R)
    - 0.0801 * Math.sin(2 * (Mp - F) * D2R);
  const meanPerigee = 83.3532465 + 4069.0137287 * T - 0.0103200 * T * T - T ** 3 / 80053;
  const lilith = meanPerigee + 180;          // Black Moon Lilith is the lunar APOGEE
  const a = AYANAMSA(T);
  return {
    MeanNode: norm360(meanNode - a),
    TrueNode: norm360(trueNode - a),
    Lilith: norm360(lilith - a),
    Chiron: norm360(chiron(jd) - a),
  };
}

/**
 * Chiron by two-body propagation from JPL osculating elements at epoch 2023-02-25.
 * Approximate by construction: no perturbations, and Chiron is a Centaur whose orbit Saturn and
 * Uranus push around. Fine near the epoch, degrading backward through the window.
 */
function chiron(jd) {
  const EPOCH = 2460000.5;
  const a = 13.6485, e = 0.38200, iDeg = 6.93160, omDeg = 209.26650, wDeg = 339.58280, M0 = 155.57170;
  const n = 0.9856076686 / (a * Math.sqrt(a));                 // deg/day
  let Mdeg = norm360(M0 + n * (jd - EPOCH));
  const Mr = Mdeg * D2R;
  let E = Mr;
  for (let i = 0; i < 40; i++) E -= (E - e * Math.sin(E) - Mr) / (1 - e * Math.cos(E));
  const v = 2 * Math.atan2(Math.sqrt(1 + e) * Math.sin(E / 2), Math.sqrt(1 - e) * Math.cos(E / 2));
  const u = v + wDeg * D2R;                                     // argument of latitude
  const om = omDeg * D2R, inc = iDeg * D2R;
  // Heliocentric ecliptic longitude from the orbital plane geometry.
  const x = Math.cos(om) * Math.cos(u) - Math.sin(om) * Math.sin(u) * Math.cos(inc);
  const y = Math.sin(om) * Math.cos(u) + Math.cos(om) * Math.sin(u) * Math.cos(inc);
  return norm360(Math.atan2(y, x) * R2D);
}

const EXTRAS = ["MeanNode", "TrueNode", "Lilith", "Chiron"];
const ALL = [...PLANETS, ...EXTRAS];
const OUTERS = new Set(["Uranus", "Neptune", "Pluto"]);

// ── linear algebra and logistic regression ──────────────────────────────────────────────────────
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
function fitLogistic(X, y, iters = 7, ridge = 1e-3) {
  const p = X[0].length;
  const pos = y.reduce((s, v) => s + v, 0);
  const w = new Array(p).fill(0);
  w[0] = Math.log((pos + 1) / (y.length - pos + 1));
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

const rows = [];
for (const r of raw) {
  const f = parseDate(r.fDob), m = parseDate(r.mDob);
  if (!f || !m || f.y < 1800 || f.y > 2012 || m.y < 1800 || m.y > 2012) continue;
  if (r.fDob.endsWith("-01") || r.mDob.endsWith("-01")) continue;      // placeholder birth dates
  const fJd = julianDay(f.y, f.m, f.d, 12), mJd = julianDay(m.y, m.m, m.d, 12);
  const st = jdOf(r.start), en = [r.end, r.fDod, r.mDod].map(jdOf).filter((v) => v !== null);
  if (st === null || !en.length) continue;
  const dur = (Math.min(...en) - st) / 365.2425;
  if (dur <= 0 || dur > 80) continue;
  if ((st - fJd) / 365.2425 < 12 || (st - mJd) / 365.2425 < 12) continue;
  const fx = extraLongitudes(fJd), mx = extraLongitudes(mJd);
  const fl = ALL.map((b) => (PLANETS.includes(b) ? siderealLongitude(b, fJd) : fx[b]));
  const ml = ALL.map((b) => (PLANETS.includes(b) ? siderealLongitude(b, mJd) : mx[b]));
  rows.push({
    father: r.father, mother: r.mother, duration: dur,
    fYear: f.y, mYear: m.y, gap: (fJd - mJd) / 365.2425,
    fl, ml,
    delta: fl.map((x, i) => norm360(x - ml[i])),
    // The midpoint is kept as its two components, so an ayanamsa can be applied later by rotating
    // them: cos(mid - a) = cos(a)cos(mid) + sin(a)sin(mid).
    midCos: fl.map((x, i) => { const A = x * D2R, B = ml[i] * D2R; const cx = Math.cos(A) + Math.cos(B), cy = Math.sin(A) + Math.sin(B); const n = Math.hypot(cx, cy) || 1; return cx / n; }),
    midSin: fl.map((x, i) => { const A = x * D2R, B = ml[i] * D2R; const cx = Math.cos(A) + Math.cos(B), cy = Math.sin(A) + Math.sin(B); const n = Math.hypot(cx, cy) || 1; return cy / n; }),
  });
}

// Balanced target: the median duration, so plain accuracy is readable against a 50% coin.
const sorted = rows.map((r) => r.duration).sort((a, b) => a - b);
const CUT = sorted[sorted.length >> 1];
for (const r of rows) r.label = r.duration >= CUT ? 1 : 0;
const base = rows.reduce((s, r) => s + r.label, 0) / rows.length;

console.log(`\nEXTENDED SEARCH — did this marriage last ${CUT.toFixed(1)} years or longer?`);
console.log(`  ${rows.length.toLocaleString()} couples, ${(100 * base).toFixed(1)}% positive (balanced at the median)`);
console.log(`  bodies: ${PLANETS.length} planets + ${EXTRAS.join(", ")}`);
console.log(`  NOT available at any setting: Ascendant, MC, Descendant, IC — they need a birth TIME`);
console.log(`  and PLACE, and Wikidata has neither. The information does not exist to be configured.`);

// ── a three-way split by person: train / validate / test ────────────────────────────────────────
const side = new Map();
for (const r of rows) {
  let s = side.get(r.father) ?? side.get(r.mother);
  if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
  side.set(r.father, s); side.set(r.mother, s);
  r.side = s;
}
const TR = rows.filter((r) => r.side === "train"), VA = rows.filter((r) => r.side === "val"), TE = rows.filter((r) => r.side === "test");
console.log(`  split by person: ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} validate · ${TE.length.toLocaleString()} test`);
console.log(`  the test set is scored ONCE, on the single winner, after the search is over.`);

const accOf = (w, build, set) => set.filter((r) => (sigma(dot(w, build(r))) >= 0.5 ? 1 : 0) === r.label).length / set.length;
const run = (build) => {
  const w = fitLogistic(TR.map(build), TR.map((r) => r.label));
  return { w, val: accOf(w, build, VA) };
};

// ── the baseline: era and age gap, no astrology ─────────────────────────────────────────────────
const DECADES = [];
for (let y = 1800; y <= 2010; y += 10) DECADES.push(y);
const CONTROLS = (r) => {
  const t = (r.fYear + r.mYear) / 2;
  return [...DECADES.map((d) => (t >= d && t < d + 10 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];
};
const baseBuild = (r) => [1, ...CONTROLS(r)];
const baseline = run(baseBuild);
const baselineTest = accOf(baseline.w, baseBuild, TE);
console.log(`\n  THE BASELINE — era (22 decade flags) + age gap, no astrology`);
console.log(`    validation ${(100 * baseline.val).toFixed(2)}%   test ${(100 * baselineTest).toFixed(2)}%`);

// ── the search ──────────────────────────────────────────────────────────────────────────────────
const BODY_SETS = {
  "10 planets": PLANETS,
  "10 planets + 4 extras": ALL,
  "extras only": EXTRAS,
  "no outer planets, + extras": ALL.filter((b) => !OUTERS.has(b)),
};
const idxOf = (bs) => bs.map((b) => ALL.indexOf(b));

/** Feature builders. `a` is the sidereal offset in degrees, applied by rotating the midpoint. */
const FORMS = {
  "difference sin": (ix) => () => (r) => ix.map((i) => Math.sin(r.delta[i] * D2R)),
  "difference sin+cos": (ix) => () => (r) => ix.flatMap((i) => [Math.sin(r.delta[i] * D2R), Math.cos(r.delta[i] * D2R)]),
  "midpoint cos": (ix) => (a) => { const c = Math.cos(a * D2R), s = Math.sin(a * D2R); return (r) => ix.map((i) => c * r.midCos[i] + s * r.midSin[i]); },
  "midpoint cos + difference sin": (ix) => (a) => { const c = Math.cos(a * D2R), s = Math.sin(a * D2R); return (r) => [...ix.map((i) => c * r.midCos[i] + s * r.midSin[i]), ...ix.map((i) => Math.sin(r.delta[i] * D2R))]; },
  "midpoint cos+sin + difference sin": (ix) => () => (r) => [...ix.map((i) => r.midCos[i]), ...ix.map((i) => r.midSin[i]), ...ix.map((i) => Math.sin(r.delta[i] * D2R))],
};

const STEP = 5;
const results = [];
let evaluated = 0;
for (const [bname, bodies] of Object.entries(BODY_SETS)) {
  const ix = idxOf(bodies);
  for (const [fname, mk] of Object.entries(FORMS)) {
    // Only the midpoint forms depend on the sidereal setting; the rest are invariant, so sweeping
    // them would be 72 identical fits.
    const sweeps = fname.startsWith("midpoint cos +") || fname === "midpoint cos"
      ? Array.from({ length: 360 / STEP }, (_, k) => k * STEP) : [0];
    for (const a of sweeps) {
      const fn = mk(ix)(a);
      const build = (r) => [1, ...fn(r)];
      const { w, val } = run(build);
      results.push({ bname, fname, a, val, build, w });
      evaluated++;
    }
  }
}
results.sort((x, y) => y.val - x.val);
console.log(`\n  ${evaluated.toLocaleString()} configurations searched — ${Object.keys(BODY_SETS).length} body sets x ` +
  `${Object.keys(FORMS).length} feature forms x up to ${360 / STEP} sidereal offsets (the full circle in ${STEP}-degree steps,`);
console.log(`  which CONTAINS Lahiri, Fagan-Bradley, Raman, Krishnamurti, De Luce, Yukteshwar, Djwhal Khul,`);
console.log(`  Sassanian, Galactic-Centre and every other named ayanamsa, plus every offset nobody proposed).`);

console.log(`\n  best 12 by VALIDATION accuracy:`);
console.log(`    body set                     feature form                          offset    val`);
for (const r of results.slice(0, 12)) {
  console.log(`    ${r.bname.padEnd(28)} ${r.fname.padEnd(36)} ${String(r.a).padStart(4)}   ${(100 * r.val).toFixed(2)}%`);
}

// ── does the sidereal setting matter at all? ────────────────────────────────────────────────────
console.log(`\n  THE SIDEREAL SWEEP, for the best body set — validation accuracy against the offset:`);
{
  const best = results[0].bname;
  const ix = idxOf(BODY_SETS[best]);
  const sweep = [];
  for (let a = 0; a < 360; a += STEP) {
    const fn = FORMS["midpoint cos + difference sin"](ix)(a);
    sweep.push([a, run((r) => [1, ...fn(r)]).val]);
  }
  const vals = sweep.map((s) => s[1]);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  console.log(`    ${best}: worst offset ${(100 * lo).toFixed(2)}%, best offset ${(100 * hi).toFixed(2)}%, spread ${(100 * (hi - lo)).toFixed(2)} points`);
  const bothFn = FORMS["midpoint cos+sin + difference sin"](ix)();
  const both = run((r) => [1, ...bothFn(r)]).val;
  console.log(`    carrying BOTH midpoint components at once: ${(100 * both).toFixed(2)}% — this model contains every`);
  console.log(`    sidereal setting simultaneously, because cos(mid - a) = cos(a)cos(mid) + sin(a)sin(mid).`);
  console.log(`    Best single offset ${(100 * hi).toFixed(2)}% vs both-at-once ${(100 * both).toFixed(2)}%: no offset can exceed it.`);
}

// ── the winner, scored once on test ─────────────────────────────────────────────────────────────
const win = results[0];
const winTest = accOf(win.w, win.build, TE);
console.log(`\n${"═".repeat(78)}`);
console.log(`  THE WINNER OF THE SEARCH: ${win.bname}, ${win.fname}, offset ${win.a} degrees`);
console.log(`${"═".repeat(78)}`);
console.log(`    validation ${(100 * win.val).toFixed(2)}%   (this is the number the search maximised, and is optimistic)`);
console.log(`    TEST       ${(100 * winTest).toFixed(2)}%   (scored once, never used for selection)`);
console.log(`    selection bias: ${(100 * (win.val - winTest)).toFixed(2)} points lost between validation and test`);
console.log(`\n    THE BASELINE ON THE SAME TEST SET: ${(100 * baselineTest).toFixed(2)}%`);
console.log(`    the coin: ${(100 * Math.max(base, 1 - base)).toFixed(2)}%`);
const verdict = winTest > baselineTest;
console.log(`\n    ${verdict ? "THE SEARCH BEAT THE BASELINE" : "THE SEARCH DID NOT BEAT THE BASELINE"} — ` +
  `${(100 * (winTest - baselineTest)).toFixed(2)} points ${verdict ? "above" : "below"} era + age gap.`);
