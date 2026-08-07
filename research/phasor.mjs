/**
 * phasor.mjs — each person as one complex number.
 *
 *     z(t)  =  b  +  SUM_j  a_j · exp( i ( w_j · t  +  p_j ) )
 *
 * w_j is body j's angular frequency (its mean motion), p_j its phase at the epoch, a_j a complex
 * amplitude. Ten bodies collapse to a single complex number per person.
 *
 * ── Why this is a better parameterisation than the 200-column cross-matrix ────────────────────────
 *
 * Expand the natural pair interaction and the reason appears:
 *
 *   z_A conj(z_B) = |b|^2
 *                 + b·SUM_k conj(a_k) e^{-i th_k(B)}  +  conj(b)·SUM_j a_j e^{i th_j(A)}
 *                 + SUM_j SUM_k  a_j conj(a_k) · exp( i ( th_j(A) - th_k(B) ) )
 *
 * That last term is a weighted sum over exactly the same 100 cross-pairs of angle differences the
 * full synastry model uses — but the weight on pair (j,k) is forced to be a_j conj(a_k), an OUTER
 * PRODUCT. So this is the full synastry matrix with its weight matrix constrained to RANK ONE:
 * 20 real parameters where the unconstrained version spends 200. If the tradition's claim is that one
 * coherent "signature" per person meets another, rank one is the right constraint and this should
 * generalise better. If the 200-parameter version is only fitting noise, this will match it.
 *
 * ── The parameterisation, and an equivalence worth knowing ───────────────────────────────────────
 *
 * w_j is KNOWN — body j's sidereal period in days, so w_j = 2*pi / P_j. b, a_j and p_j are learned.
 * a_j is taken REAL and p_j a separate real phase, which is exactly as expressive as a complex a_j with
 * p_j fixed at zero: a·exp(i(wt+p)) = (a·cos p + i·a·sin p)·exp(iwt). Two real parameters per body
 * either way. The (amplitude, phase) form is used because both halves mean something on their own.
 *
 * And note what this removes: with w_j from the orbital period and p_j learned, the model needs NO
 * EPHEMERIS. No Table-1 elements, no ayanamsa, no sidereal frame. It is a function of the two dates,
 * ten known periods, and twenty-two learned numbers. The ephemeris version is run alongside it purely
 * to measure how much is lost by treating each planet as a perfect circle.
 *
 * ── Two versions of theta ───────────────────────────────────────────────────────────────────────
 *
 *   EPHEMERIS   th_j(t) is the body's true sidereal longitude, eccentricity and all.
 *   MEAN MOTION th_j(t) = w_j·t + p_j exactly — a pure phasor, the formula as written, with w_j from
 *               the orbital period and p_j fitted out into a_j. Cleaner, and slightly wrong about
 *               where the planets actually were. Both are run, because the difference between them
 *               measures how much the model depends on real positions versus on periodicity alone.
 *
 * ── Fitting ─────────────────────────────────────────────────────────────────────────────────────
 *
 * The parameters enter as products, so the loss is not convex. Fitted by Adam on the logistic loss
 * with central-difference gradients — 27 parameters, so finite differences are cheap and, unlike a
 * hand-derived gradient, cannot be subtly wrong. Several random restarts, best training loss kept, and
 * the whole thing scored on a test set split by person.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/phasor.mjs ./research/data-divorce
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
/** Sidereal periods in days — the source of w_j = 2*pi / period for the pure-phasor version. */
const PERIOD = { Sun: 365.256, Moon: 27.32166, Mercury: 87.9691, Venus: 224.701, Mars: 686.980,
  Jupiter: 4332.59, Saturn: 10759.22, Uranus: 30688.5, Neptune: 60182, Pluto: 90560 };
const YR = 365.2425;
const DIR = process.argv[2] ?? "./research/data-divorce";
const EPOCH = 2451545.0;                                   // J2000, the t = 0 of the phasors

let SEED = 20260807;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };
const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());

// ── data ────────────────────────────────────────────────────────────────────────────────────────
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
  rows.push({
    a: pa, b: pb, y: r.y, year: (ya + yb) / 2, gap: (jb - ja) / YR,
    // EPHEMERIS angles, in radians.
    ea: PLANETS.map((x) => siderealLongitude(x, ja) * D2R),
    eb: PLANETS.map((x) => siderealLongitude(x, jb) * D2R),
    // PURE PHASOR angles: w_j * t with t in days from J2000. p_j is absorbed into a_j, so it is 0 here.
    ma: PLANETS.map((x) => (2 * Math.PI / PERIOD[x]) * (ja - EPOCH)),
    mb: PLANETS.map((x) => (2 * Math.PI / PERIOD[x]) * (jb - EPOCH)),
  });
}
SEED = 20260807;
const posR = rows.filter((r) => r.y === 1), negR = rows.filter((r) => r.y === 0);
const K = Math.min(posR.length, negR.length);
const data = shuffle([...shuffle(posR).slice(0, K), ...shuffle(negR).slice(0, K)]);

const side = new Map();
SEED = 20260807;
for (const r of data) {
  let s = side.get(r.a) ?? side.get(r.b);
  if (s === undefined) s = rnd() < 0.8 ? "train" : "test";
  side.set(r.a, s); side.set(r.b, s);
  r.side = s;
}
const TR = data.filter((r) => r.side === "train"), TE = data.filter((r) => r.side === "test");

console.log(`\nEACH PERSON AS ONE COMPLEX NUMBER   z = b + SUM a_j exp(i(w_j t + p_j))`);
console.log(`  ${data.length.toLocaleString()} couples, ${K.toLocaleString()} of each class — coin 50.00%`);
console.log(`  ${TR.length.toLocaleString()} train / ${TE.length.toLocaleString()} test, split by person`);

// Precompute cos and sin of every angle once — the fit touches them hundreds of thousands of times.
for (const r of data) {
  for (const [src, dst] of [["ea", "Ea"], ["eb", "Eb"], ["ma", "Ma"], ["mb", "Mb"]]) {
    r[dst] = { c: r[src].map(Math.cos), s: r[src].map(Math.sin) };
  }
}

const NB = PLANETS.length;
/**
 * Parameters, packed flat:
 *   [0..1]                 b       real and imaginary part
 *   [2 .. 2+NB-1]          a_j     real amplitude, one per body
 *   [2+NB .. 2+2NB-1]      p_j     real phase, one per body
 *   [2+2NB .. +4]          c0..c4  the readout on the pair interaction
 */
const NP = 2 + 2 * NB + 5;

function forward(th, r, which) {
  const A = which === "eph" ? r.Ea : r.Ma, B = which === "eph" ? r.Eb : r.Mb;
  let zar = th[0], zai = th[1], zbr = th[0], zbi = th[1];
  for (let j = 0; j < NB; j++) {
    const a = th[2 + j], p = th[2 + NB + j];
    const cp = Math.cos(p), sp = Math.sin(p);
    // a * exp(i(theta + p)) = a * (cos theta + i sin theta)(cos p + i sin p)
    zar += a * (A.c[j] * cp - A.s[j] * sp);
    zai += a * (A.s[j] * cp + A.c[j] * sp);
    zbr += a * (B.c[j] * cp - B.s[j] * sp);
    zbi += a * (B.s[j] * cp + B.c[j] * sp);
  }
  // z_A conj(z_B), the pair interaction, plus two magnitudes.
  const re = zar * zbr + zai * zbi;                  // alignment
  const im = zai * zbr - zar * zbi;                  // twist
  const mags = zar * zar + zai * zai + zbr * zbr + zbi * zbi;
  const sr = zar + zbr, si = zai + zbi;
  const comp = sr * sr + si * si;                    // |z_A + z_B|^2, the composite magnitude
  const o = 2 + 2 * NB;
  return th[o] + th[o + 1] * re + th[o + 2] * im + th[o + 3] * mags + th[o + 4] * comp;
}
const sigma = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));
function loss(th, set, which, l2 = 1e-4) {
  let s = 0;
  for (const r of set) {
    const p = Math.min(1 - 1e-12, Math.max(1e-12, sigma(forward(th, r, which))));
    s -= r.y ? Math.log(p) : Math.log(1 - p);
  }
  s /= set.length;
  for (let i = 0; i < th.length; i++) s += l2 * th[i] * th[i];
  return s;
}
const accuracy = (th, set, which) =>
  set.filter((r) => (sigma(forward(th, r, which)) >= 0.5 ? 1 : 0) === r.y).length / set.length;

/** Adam with central-difference gradients. 27 parameters, so this is cheap and cannot be mis-derived. */
function fit(which, { steps = 400, restarts = 6 } = {}) {
  let best = null;
  for (let rs = 0; rs < restarts; rs++) {
    const th = new Float64Array(NP);
    for (let i = 0; i < NP; i++) th[i] = 0.3 * gauss();
    for (let j = 0; j < NB; j++) th[2 + NB + j] = 2 * Math.PI * rnd();   // phases start spread over the circle
    th[2 + 2 * NB] = 0;                              // the readout starts at zero
    const m = new Float64Array(NP), v = new Float64Array(NP);
    const lr = 0.05, b1 = 0.9, b2 = 0.999, eps = 1e-8, h = 1e-4;
    for (let t = 1; t <= steps; t++) {
      for (let i = 0; i < NP; i++) {
        const o = th[i];
        th[i] = o + h; const lp = loss(th, TR, which);
        th[i] = o - h; const lm = loss(th, TR, which);
        th[i] = o;
        const g = (lp - lm) / (2 * h);
        m[i] = b1 * m[i] + (1 - b1) * g;
        v[i] = b2 * v[i] + (1 - b2) * g * g;
        th[i] -= lr * (m[i] / (1 - b1 ** t)) / (Math.sqrt(v[i] / (1 - b2 ** t)) + eps);
      }
    }
    const l = loss(th, TR, which);
    if (!best || l < best.l) best = { l, th: Float64Array.from(th) };
  }
  return best.th;
}

console.log(`\n  model                                                params   TRAIN     TEST`);
for (const [label, which] of [["EPHEMERIS angles", "eph"], ["PURE PHASOR, w_j t only", "mean"]]) {
  const th = fit(which);
  console.log(`  ${("phasor, " + label).padEnd(52)} ${String(NP).padStart(4)}   ${(100 * accuracy(th, TR, which)).toFixed(2)}%   ${(100 * accuracy(th, TE, which)).toFixed(2)}%`);
  if (which === "eph") {
    const amp = [];
    for (let j = 0; j < NB; j++) amp.push({ b: PLANETS[j], A: Math.abs(th[2 + j]),
      ph: (((th[2 + NB + j] * 180 / Math.PI) % 360) + 360) % 360 });
    amp.sort((x, y) => y.A - x.A);
    console.log(`\n    fitted amplitude a_j and phase p_j, largest amplitude first:`);
    for (const q of amp) console.log(`      ${q.b.padEnd(9)} a ${q.A.toFixed(4)}   p ${q.ph.toFixed(1)} deg`);
    const outer = Math.hypot(...amp.filter((q) => ["Uranus", "Neptune", "Pluto"].includes(q.b)).map((q) => q.A));
    const all = Math.hypot(...amp.map((q) => q.A));
    console.log(`      the three outer planets hold ${(100 * (outer / all) ** 2).toFixed(1)}% of the squared amplitude`);
    const o = 2 + 2 * NB;
    console.log(`\n    readout: c0 ${th[o].toFixed(4)}  Re ${th[o+1].toFixed(4)}  Im ${th[o+2].toFixed(4)}  |z|^2 ${th[o+3].toFixed(4)}  |zA+zB|^2 ${th[o+4].toFixed(4)}`);
    console.log(`    b = ${th[0].toFixed(4)} + ${th[1].toFixed(4)}i`);
  }
}

// ── the comparators, on the identical split ─────────────────────────────────────────────────────
console.log(`\n  for comparison, on the same couples and the same split:`);
{
  function solveSym(A, b, p) {
    const M = new Float64Array(p * (p + 1));
    for (let i = 0; i < p; i++) { for (let j = 0; j < p; j++) M[i * (p + 1) + j] = A[i * p + j]; M[i * (p + 1) + p] = b[i]; }
    for (let c = 0; c < p; c++) {
      let piv = c;
      for (let r = c + 1; r < p; r++) if (Math.abs(M[r * (p + 1) + c]) > Math.abs(M[piv * (p + 1) + c])) piv = r;
      if (piv !== c) for (let k = c; k <= p; k++) { const t = M[c * (p + 1) + k]; M[c * (p + 1) + k] = M[piv * (p + 1) + k]; M[piv * (p + 1) + k] = t; }
      const d = M[c * (p + 1) + c];
      if (Math.abs(d) < 1e-12) continue;
      for (let r = 0; r < p; r++) { if (r === c) continue; const f = M[r * (p + 1) + c] / d; if (f === 0) continue; for (let k = c; k <= p; k++) M[r * (p + 1) + k] -= f * M[c * (p + 1) + k]; }
    }
    const w = new Float64Array(p);
    for (let i = 0; i < p; i++) { const d = M[i * (p + 1) + i]; w[i] = Math.abs(d) < 1e-12 ? 0 : M[i * (p + 1) + p] / d; }
    return w;
  }
  const dotf = (w, x) => { let s = 0; for (let i = 0; i < w.length; i++) s += w[i] * x[i]; return s; };
  function fitLog(X, y, ridge, iters = 6) {
    const n = X.length, p = X[0].length, w = new Float64Array(p);
    let pos = 0;
    for (const v of y) pos += v;
    w[0] = Math.log((pos + 1) / (n - pos + 1));
    const A = new Float64Array(p * p), g = new Float64Array(p);
    for (let it = 0; it < iters; it++) {
      A.fill(0); g.fill(0);
      for (let i = 0; i < n; i++) {
        const xi = X[i], mu = sigma(dotf(w, xi)), wt = Math.max(mu * (1 - mu), 1e-6), rr = y[i] - mu;
        for (let j = 0; j < p; j++) { const xj = xi[j]; if (xj === 0) continue; g[j] += xj * rr; const wx = wt * xj; for (let k = j; k < p; k++) A[j * p + k] += wx * xi[k]; }
      }
      for (let j = 0; j < p; j++) { for (let k = 0; k < j; k++) A[j * p + k] = A[k * p + j]; A[j * p + j] += ridge; }
      const st = solveSym(A, g, p);
      for (let j = 0; j < p; j++) w[j] += st[j];
    }
    return w;
  }
  const BINS = [];
  for (let y = 1500; y <= 2000; y += 20) BINS.push(y);
  const sets = {
    "full 10x10 cross-matrix (unconstrained, 200)": (r) => { const o = []; for (let j = 0; j < NB; j++) for (let k = 0; k < NB; k++) o.push(Math.cos(r.ea[j] - r.eb[k]), Math.sin(r.ea[j] - r.eb[k])); return o; },
    "era + age gap, no astrology": (r) => [r.year < 1500 ? 1 : 0, ...BINS.map((b) => (r.year >= b && r.year < b + 20 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10],
  };
  for (const [name, fn] of Object.entries(sets)) {
    const build = (r) => Float64Array.from([1, ...fn(r)]);
    const w = fitLog(TR.map(build), Float64Array.from(TR.map((r) => r.y)), 10);
    const acc = (set) => set.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === r.y).length / set.length;
    console.log(`  ${name.padEnd(52)} ${String(build(TR[0]).length - 1).padStart(4)}   ${(100 * acc(TR)).toFixed(2)}%   ${(100 * acc(TE)).toFixed(2)}%`);
  }
  console.log(`  ${"the coin".padEnd(52)}   —       —       50.00%`);
}
