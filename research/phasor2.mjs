/**
 * phasor2.mjs — the phasor model, corrected and pushed as far as it goes.
 *
 *     z_P  =  b  +  SUM_j  u_j · exp( i · w_j · t_P )        u_j complex, one per frequency
 *
 * ── Five things wrong with the first version, and what each fix buys ─────────────────────────────
 *
 * 1. THE READOUT WAS RANK-DEFICIENT. It used Re, Im, (|zA|^2+|zB|^2) and |zA+zB|^2 — but
 *    |zA+zB|^2 = |zA|^2 + |zB|^2 + 2·Re(zA conj zB), so three of those four features span two
 *    dimensions. One parameter was redundant and the ridge was silently absorbing a singular design.
 *    Replaced by an independent basis: Re, Im, |zA|^2, |zB|^2.
 *
 * 2. THE PARAMETERISATION WAS NEEDLESSLY NON-LINEAR. Writing a_j·exp(i(w_j t + p_j)) as an amplitude
 *    and a phase makes the model non-linear in its parameters and lets the phase wrap. One complex
 *    number u_j = a_j·exp(i p_j) is exactly as expressive and makes z LINEAR in the parameters, so the
 *    logit is a clean quadratic form and the optimisation is far better conditioned.
 *
 * 3. RANK ONE WAS A CHOICE, NOT A NECESSITY. The pair interaction weights cross-pair (j,k) by
 *    u_j conj(u_k), an outer product — rank one. With R independent sets and a free real coefficient
 *    per set, the weight matrix becomes a rank-R Hermitian form, interpolating from 1 to the
 *    unconstrained 200-parameter matrix. Rank is now swept.
 *
 * 4. THE FREQUENCY SET WAS NEVER QUESTIONED. Only the ten mean motions. Two additions matter:
 *      HARMONICS  2w_j and 3w_j. A second harmonic IS the square/opposition axis — the cos(2·phi) the
 *                 aspect tradition turns on — and no phasor model here could reach it.
 *      SYNODICS   w_j - w_k, the conjunction cycles. Jupiter-Saturn at about twenty years is among the
 *                 oldest cycles in the tradition, and it is NOT in the span of the individual motions.
 *
 * 5. THE OPTIMISER WAS UNDER-RUN. Mini-batch gradients buy two orders of magnitude more steps for the
 *    same work than full-batch finite differences did.
 *
 * ── The protocol ────────────────────────────────────────────────────────────────────────────────
 *
 * Split three ways by person: 60% train, 20% validation, 20% test. Rank, frequency set and ridge are
 * chosen on VALIDATION. The test set is scored ONCE, on the single winning configuration. Sweeping
 * rank and frequencies against a test set would guarantee beating any baseline eventually.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/phasor2.mjs ./research/data-divorce
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { julianDay } = await import(EPH);

const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const PERIOD = { Sun: 365.256363, Moon: 27.321661, Mercury: 87.9691, Venus: 224.700796, Mars: 686.9800,
  Jupiter: 4332.589, Saturn: 10759.22, Uranus: 30688.5, Neptune: 60182.0, Pluto: 90560.0 };
const YR = 365.2425;
const EPOCH = 2451545.0;
const DIR = process.argv[2] ?? "./research/data-divorce";

let SEED = 20260807;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };
const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());

// ── frequency sets ──────────────────────────────────────────────────────────────────────────────
const base = PLANETS.map((p) => ({ name: p, w: 2 * Math.PI / PERIOD[p] }));
const harmonics = [
  ...base,
  ...base.map((f) => ({ name: `2x${f.name}`, w: 2 * f.w })),
  ...base.map((f) => ({ name: `3x${f.name}`, w: 3 * f.w })),
];
const synodics = (() => {
  const out = [...base];
  for (let j = 0; j < base.length; j++) {
    for (let k = j + 1; k < base.length; k++) {
      const w = Math.abs(base[j].w - base[k].w);
      if (w > 1e-9) out.push({ name: `${base[j].name}-${base[k].name}`, w });
    }
  }
  return out;
})();
const everything = (() => {
  const seen = new Set(), out = [];
  for (const f of [...harmonics, ...synodics]) {
    const key = f.w.toExponential(9);
    if (seen.has(key)) continue;
    seen.add(key); out.push(f);
  }
  return out;
})();
const FREQ_SETS = {
  "10 mean motions": base,
  "+ 2nd and 3rd harmonics (30)": harmonics,
  "+ synodic pairs (55)": synodics,
  "harmonics AND synodics": everything,
};

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
  rows.push({ a: pa, b: pb, y: r.y, tA: ja - EPOCH, tB: jb - EPOCH, year: (ya + yb) / 2, gap: (jb - ja) / YR });
}
SEED = 20260807;
const posR = rows.filter((r) => r.y === 1), negR = rows.filter((r) => r.y === 0);
const KK = Math.min(posR.length, negR.length);
const data = shuffle([...shuffle(posR).slice(0, KK), ...shuffle(negR).slice(0, KK)]);
const side = new Map();
SEED = 20260807;
for (const r of data) {
  let s = side.get(r.a) ?? side.get(r.b);
  if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
  side.set(r.a, s); side.set(r.b, s);
  r.side = s;
}
const TR = data.filter((r) => r.side === "train"), VA = data.filter((r) => r.side === "val"), TE = data.filter((r) => r.side === "test");
console.log(`\nTHE PHASOR MODEL, CORRECTED AND PUSHED`);
console.log(`  ${data.length.toLocaleString()} couples, ${KK.toLocaleString()} of each class — coin 50.00%`);
console.log(`  ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} validate · ${TE.length.toLocaleString()} test, split by person`);
console.log(`  rank, frequency set and ridge chosen on VALIDATION; the test set is scored once, at the end.`);

/** Precompute exp(i w t) for both partners once per frequency set. */
function prepare(freqs) {
  const F = freqs.length;
  for (const r of data) {
    const ca = new Float64Array(F), sa = new Float64Array(F), cb = new Float64Array(F), sb = new Float64Array(F);
    for (let j = 0; j < F; j++) {
      const w = freqs[j].w;
      ca[j] = Math.cos(w * r.tA); sa[j] = Math.sin(w * r.tA);
      cb[j] = Math.cos(w * r.tB); sb[j] = Math.sin(w * r.tB);
    }
    r.ca = ca; r.sa = sa; r.cb = cb; r.sb = sb;
  }
  return F;
}

const sigma = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));

/**
 * Parameters, per rank component r: b_r (2 reals), u_j^(r) (2 reals each), and four readout
 * coefficients on that component's independent basis  Re, Im, |zA|^2, |zB|^2.  Plus one global bias.
 */
function layout(F, R) { return { per: 2 + 2 * F + 4, total: 1 + R * (2 + 2 * F + 4) }; }

function logitOf(th, r, F, R) {
  const { per } = layout(F, R);
  let z = th[0];
  for (let c = 0; c < R; c++) {
    const o = 1 + c * per;
    let ar = th[o], ai = th[o + 1], br = th[o], bi = th[o + 1];
    for (let j = 0; j < F; j++) {
      const ux = th[o + 2 + 2 * j], uy = th[o + 3 + 2 * j];
      ar += ux * r.ca[j] - uy * r.sa[j];
      ai += ux * r.sa[j] + uy * r.ca[j];
      br += ux * r.cb[j] - uy * r.sb[j];
      bi += ux * r.sb[j] + uy * r.cb[j];
    }
    const q = o + 2 + 2 * F;
    z += th[q] * (ar * br + ai * bi)            // Re(zA conj zB) — the interference
      + th[q + 1] * (ai * br - ar * bi)         // Im — the twist
      + th[q + 2] * (ar * ar + ai * ai)         // |zA|^2, the older partner alone
      + th[q + 3] * (br * br + bi * bi);        // |zB|^2, the younger alone
  }
  return z;
}
function loss(th, set, F, R, l2) {
  let s = 0;
  for (const r of set) {
    const p = Math.min(1 - 1e-12, Math.max(1e-12, sigma(logitOf(th, r, F, R))));
    s -= r.y ? Math.log(p) : Math.log(1 - p);
  }
  s /= set.length;
  for (let i = 1; i < th.length; i++) s += l2 * th[i] * th[i];
  return s;
}
const accOf = (th, set, F, R) => set.filter((r) => (sigma(logitOf(th, r, F, R)) >= 0.5 ? 1 : 0) === r.y).length / set.length;

/** Mini-batch Adam with central differences. Batching is what makes many steps affordable. */
function fit(F, R, l2, { steps = 1500, batch = 400, restarts = 3 } = {}) {
  const { total } = layout(F, R);
  let best = null;
  for (let rs = 0; rs < restarts; rs++) {
    const th = new Float64Array(total);
    const scale = 1 / Math.sqrt(F);
    for (let c = 0; c < R; c++) {
      const o = 1 + c * layout(F, R).per;
      th[o] = 0.2 * gauss(); th[o + 1] = 0.2 * gauss();
      for (let j = 0; j < F; j++) { th[o + 2 + 2 * j] = scale * gauss(); th[o + 3 + 2 * j] = scale * gauss(); }
      const q = o + 2 + 2 * F;
      for (let k = 0; k < 4; k++) th[q + k] = 0.05 * gauss();
    }
    const m = new Float64Array(total), v = new Float64Array(total);
    const b1 = 0.9, b2 = 0.999, eps = 1e-8, h = 1e-4;
    for (let t = 1; t <= steps; t++) {
      const lr = 0.05 * (1 - t / (steps + 1));                 // linear decay
      const bt = [];
      for (let i = 0; i < batch; i++) bt.push(TR[Math.floor(rnd() * TR.length)]);
      for (let i = 0; i < total; i++) {
        const o = th[i];
        th[i] = o + h; const lp = loss(th, bt, F, R, l2);
        th[i] = o - h; const lm = loss(th, bt, F, R, l2);
        th[i] = o;
        const g = (lp - lm) / (2 * h);
        m[i] = b1 * m[i] + (1 - b1) * g;
        v[i] = b2 * v[i] + (1 - b2) * g * g;
        th[i] -= lr * (m[i] / (1 - b1 ** t)) / (Math.sqrt(v[i] / (1 - b2 ** t)) + eps);
      }
    }
    const l = loss(th, TR, F, R, l2);
    if (!best || l < best.l) best = { l, th: Float64Array.from(th) };
  }
  return best.th;
}

// ── the sweep, scored on validation only ────────────────────────────────────────────────────────
console.log(`\n  freq set                        rank  ridge  params   TRAIN     VAL`);
const trials = [];
for (const [fname, freqs] of Object.entries(FREQ_SETS)) {
  const F = prepare(freqs);
  for (const R of (F <= 10 ? [1, 2, 4] : [1, 2])) {
    for (const l2 of [1e-4, 1e-3]) {
      const th = fit(F, R, l2, { steps: F <= 10 ? 1500 : 700, restarts: F <= 10 ? 3 : 2 });
      const tr = accOf(th, TR, F, R), va = accOf(th, VA, F, R);
      trials.push({ fname, freqs, F, R, l2, th, tr, va });
      console.log(`  ${fname.padEnd(30)} ${String(R).padStart(4)}  ${l2.toExponential(0).padStart(5)}  ${String(layout(F, R).total).padStart(5)}   ${(100 * tr).toFixed(2)}%   ${(100 * va).toFixed(2)}%`);
    }
  }
}

trials.sort((a, b) => b.va - a.va);
const win = trials[0];
prepare(win.freqs);
const te = accOf(win.th, TE, win.F, win.R);
console.log(`\n${"═".repeat(84)}`);
console.log(`  WINNER ON VALIDATION: ${win.fname}, rank ${win.R}, ridge ${win.l2.toExponential(0)}`);
console.log(`    ${layout(win.F, win.R).total} parameters — train ${(100 * win.tr).toFixed(2)}%   val ${(100 * win.va).toFixed(2)}%   TEST ${(100 * te).toFixed(2)}%`);
console.log(`    selection bias, val minus test: ${(100 * (win.va - te)).toFixed(2)} points`);

// ── the comparators on the identical split ──────────────────────────────────────────────────────
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
  function fitLog(X, y, ridge) {
    const n = X.length, p = X[0].length, w = new Float64Array(p);
    let pos = 0;
    for (const q of y) pos += q;
    w[0] = Math.log((pos + 1) / (n - pos + 1));
    const A = new Float64Array(p * p), g = new Float64Array(p);
    for (let it = 0; it < 6; it++) {
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
  const ERA = (r) => [r.year < 1500 ? 1 : 0, ...BINS.map((b) => (r.year >= b && r.year < b + 20 ? 1 : 0)), r.gap / 10, (r.gap / 10) ** 2, Math.abs(r.gap) / 10];
  const build = (r) => Float64Array.from([1, ...ERA(r)]);
  const w = fitLog(TR.map(build), Float64Array.from(TR.map((r) => r.y)), 10);
  const a = (set) => set.filter((r) => (sigma(dotf(w, build(r))) >= 0.5 ? 1 : 0) === r.y).length / set.length;
  console.log(`\n  era + age gap, no astrology (${build(TR[0]).length - 1} cols): train ${(100 * a(TR)).toFixed(2)}%   val ${(100 * a(VA)).toFixed(2)}%   TEST ${(100 * a(TE)).toFixed(2)}%`);
  console.log(`  the coin: 50.00%`);
}

// ── and what the winner is reading ──────────────────────────────────────────────────────────────
{
  const { per } = layout(win.F, win.R);
  const amps = win.freqs.map((f, j) => {
    let s = 0;
    for (let c = 0; c < win.R; c++) { const o = 1 + c * per; s += win.th[o + 2 + 2 * j] ** 2 + win.th[o + 3 + 2 * j] ** 2; }
    return { name: f.name, per: (2 * Math.PI / f.w) / YR, a: Math.sqrt(s) };
  }).sort((x, y) => y.a - x.a);
  console.log(`\n  the ten strongest frequencies in the winner, by total amplitude across rank components:`);
  for (const q of amps.slice(0, 10)) console.log(`    ${q.name.padEnd(20)} period ${q.per.toFixed(2).padStart(9)} y   |u| ${q.a.toFixed(4)}`);
  const slow = amps.filter((q) => q.per > 50).reduce((s, q) => s + q.a * q.a, 0);
  const tot = amps.reduce((s, q) => s + q.a * q.a, 0);
  console.log(`    frequencies with a period over 50 years hold ${(100 * slow / tot).toFixed(1)}% of the squared amplitude`);
  console.log(`    (a period longer than the sample's span cannot oscillate within it — it can only be a trend,`);
  console.log(`     which is to say a clock)`);
}
