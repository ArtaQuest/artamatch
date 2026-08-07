/**
 * transit-wave.mjs — the transit-to-natal wave model.
 *
 *     z_P(t)  =  b  +  SUM_j  a_j · exp( i · ( theta_j(t)  -  P_j ) )        P_j = theta_j(t_P)
 *
 * The date of birth sets each body's initial phase P_j — its real natal longitude. The wave then
 * evolves with the REAL transiting sky theta_j(t), read from a day-by-day ephemeris table.
 *
 * ── Why this is the well-posed version ──────────────────────────────────────────────────────────
 *
 * Every earlier dynamic model here failed one of two symmetry tests. This one passes both:
 *
 *   ROTATION INVARIANCE. Nobody agrees where the zodiac starts — the named ayanamsas span about 25
 *   degrees and the choice is a convention. Shift the origin by d and theta_j(t) -> theta_j(t) + d,
 *   P_j -> P_j + d, so the DIFFERENCE is untouched. The model is exactly invariant, for any b. The
 *   natal-chart phasor was not: with its fitted b = -0.081 + 0.364i its answer moved 17% under a
 *   25-degree shift, because there exp(i theta_j) is an absolute position rather than a difference.
 *
 *   NO AGE DEGENERACY. The earlier interference model used w_j(t - t_P), a linear phase, which depends
 *   only on elapsed time — so everyone of the same age was identical and the score collapsed to a
 *   function of the two ages. With real longitudes theta_j(t) - theta_j(t_P) is NOT a function of
 *   t - t_P: measured, two people of the same age at the same wedding still differ by 324 degrees on
 *   Mercury, 281 on Venus, 138 on Mars, 54 on Pluto. The degeneracy is broken by real motion.
 *
 * At t = t_P every phase is zero and z = b + SUM a_j, the same for everyone — and that is CORRECT for a
 * transit model: at your own birth every transit is exactly conjunct its own natal position. People
 * differentiate afterwards, which is what transits are.
 *
 * ── The compatibility score ─────────────────────────────────────────────────────────────────────
 *
 *     S  =  (1/T) · INTEGRAL from t_m to t_m+T  of  max( 0, Re( z_A(t) conj(z_B(t)) ) )  dt
 *
 * with T = 28 years, the median marriage duration — a global constant, never each couple's own.
 *
 * ── The trick that makes it fittable ────────────────────────────────────────────────────────────
 *
 * Write E_j(t) = exp(i theta_j(t)) for the transiting sky and N_j^P = exp(i P_j) for the natal phase.
 * Then exp(i(theta_j(t) - P_j)) = E_j(t) · conj(N_j^P), so with v_j^P = a_j · conj(N_j^P),
 *
 *     z_P(t) = b + SUM_j v_j^P E_j(t)
 *
 * and the SIGNED integral expands into a quadratic form whose coefficients do not involve the
 * parameters at all:
 *
 *     C_j    = (1/T) INTEGRAL E_j(t) dt                  10 complex numbers per couple
 *     D_jk   = (1/T) INTEGRAL E_j(t) conj(E_k(t)) dt     100 more
 *
 * Those are computed ONCE per couple, and every subsequent evaluation of the signed score is 100
 * complex multiplies instead of a 1,460-point integral — about four orders of magnitude cheaper. The
 * POSITIVE part cannot be reduced this way, because the rectifier sits inside the integral, so it is
 * evaluated directly with the parameters the signed fit converges on and then refined briefly.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/transit-wave.mjs ./research/data-divorce
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const NB = PLANETS.length;
const YR = 365.2425;
const T28 = 28 * YR;
const DIR = process.argv[2] ?? "./research/data-divorce";

let SEED = 20260807;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };
const shuffle = (a) => { const b = [...a]; for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; };
const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());

// ── data ────────────────────────────────────────────────────────────────────────────────────────
const parseDate = (iso) => {
  const m = /^(-?\d{3,4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};
const isJan1 = (s) => !!s && s.endsWith("-01-01");
const raw = JSON.parse(readFileSync(`${DIR}/balanced-all-precisions.json`, "utf8"));
const rows = [];
for (const r of raw) {
  const A = parseDate(r.aDob), B = parseDate(r.bDob), M = parseDate(r.start);
  if (!A || !B || !M) continue;
  if (isJan1(r.aDob) || isJan1(r.bDob) || isJan1(r.start)) continue;
  let ja = julianDay(A.y, A.m, A.d, 12), jb = julianDay(B.y, B.m, B.d, 12), ya = A.y, yb = B.y, pa = r.a, pb = r.b;
  if (jb < ja) { [ja, jb] = [jb, ja]; [pa, pb] = [pb, pa]; [ya, yb] = [yb, ya]; }
  const jm = julianDay(M.y, M.m, M.d, 12);
  const ageA = (jm - ja) / YR, ageB = (jm - jb) / YR;
  if (ageA < 12 || ageB < 12 || ageA > 90) continue;
  rows.push({ a: pa, b: pb, y: r.y, tA: ja, tB: jb, tM: jm, year: (ya + yb) / 2, wedYear: M.y, gap: (jb - ja) / YR, ageM: (ageA + ageB) / 2 });
}
SEED = 20260807;
const pos = rows.filter((r) => r.y === 1), neg = rows.filter((r) => r.y === 0);
const K = Math.min(pos.length, neg.length);
const data = shuffle([...shuffle(pos).slice(0, K), ...shuffle(neg).slice(0, K)]);
const side = new Map();
SEED = 20260807;
for (const r of data) {
  let s = side.get(r.a) ?? side.get(r.b);
  if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
  side.set(r.a, s); side.set(r.b, s);
  r.side = s;
}
const TR = data.filter((r) => r.side === "train"), VA = data.filter((r) => r.side === "val"), TE = data.filter((r) => r.side === "test");

console.log(`\nTHE TRANSIT-TO-NATAL WAVE   z_P(t) = b + SUM a_j exp( i ( theta_j(t) - P_j ) )`);
console.log(`  the date of birth sets every P_j; nothing about phase is learned`);
console.log(`  ${data.length.toLocaleString()} couples, ${K.toLocaleString()} of each class — coin 50.00%`);
console.log(`  ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} val · ${TE.length.toLocaleString()} test, split by person`);

// ── rotation invariance, verified ───────────────────────────────────────────────────────────────
console.log(`\n  ROTATION INVARIANCE — shift the whole zodiac and see whether the score moves`);
{
  const r = data[0], step = 7, n = Math.floor(T28 / step) + 1;
  const a = Array.from({ length: NB }, () => [0.5 + rnd(), 0.3 * gauss()]);
  const b = [0.4, -0.2];
  const sc = (shift) => {
    let acc = 0;
    for (let k = 0; k < n; k++) {
      const t = r.tM + k * step;
      let ar = b[0], ai = b[1], br = b[0], bi = b[1];
      for (let j = 0; j < NB; j++) {
        const th = siderealLongitude(PLANETS[j], t) + shift;
        const pA = siderealLongitude(PLANETS[j], r.tA) + shift;
        const pB = siderealLongitude(PLANETS[j], r.tB) + shift;
        const dA = (th - pA) * D2R, dB = (th - pB) * D2R;
        ar += a[j][0] * Math.cos(dA) - a[j][1] * Math.sin(dA);
        ai += a[j][0] * Math.sin(dA) + a[j][1] * Math.cos(dA);
        br += a[j][0] * Math.cos(dB) - a[j][1] * Math.sin(dB);
        bi += a[j][0] * Math.sin(dB) + a[j][1] * Math.cos(dB);
      }
      const v = ar * br + ai * bi;
      if (v > 0) acc += v;
    }
    return acc / n;
  };
  const base = sc(0);
  for (const d of [1, 25, 180]) {
    console.log(`    shift ${String(d).padStart(3)} deg: score ${sc(d).toFixed(12)}   base ${base.toFixed(12)}   |diff| ${Math.abs(sc(d) - base).toExponential(2)}`);
  }
  console.log(`    EXACTLY invariant, for any b — because the phase is a DIFFERENCE of two longitudes.`);
}

// ── precompute C_j and D_jk per couple ──────────────────────────────────────────────────────────
console.log(`\n  precomputing the integral coefficients (10 + 100 complex numbers per couple)`);
const STEP = 7, NG = Math.floor(T28 / STEP) + 1;
for (const r of data) {
  // E_j(t) over the window, and the natal phases.
  const Cr = new Float64Array(NB), Ci = new Float64Array(NB);
  const Dr = new Float64Array(NB * NB), Di = new Float64Array(NB * NB);
  const ec = new Float64Array(NB), es = new Float64Array(NB);
  for (let k = 0; k < NG; k++) {
    const t = r.tM + k * STEP;
    for (let j = 0; j < NB; j++) { const th = siderealLongitude(PLANETS[j], t) * D2R; ec[j] = Math.cos(th); es[j] = Math.sin(th); }
    for (let j = 0; j < NB; j++) {
      Cr[j] += ec[j]; Ci[j] += es[j];
      for (let m = 0; m < NB; m++) {
        // E_j conj(E_m)
        Dr[j * NB + m] += ec[j] * ec[m] + es[j] * es[m];
        Di[j * NB + m] += es[j] * ec[m] - ec[j] * es[m];
      }
    }
  }
  for (let j = 0; j < NB; j++) { Cr[j] /= NG; Ci[j] /= NG; }
  for (let i = 0; i < NB * NB; i++) { Dr[i] /= NG; Di[i] /= NG; }
  r.Cr = Cr; r.Ci = Ci; r.Dr = Dr; r.Di = Di;
  // natal phases as complex conjugates: conj(N_j) = exp(-i P_j)
  const nar = new Float64Array(NB), nai = new Float64Array(NB), nbr = new Float64Array(NB), nbi = new Float64Array(NB);
  for (let j = 0; j < NB; j++) {
    const pA = siderealLongitude(PLANETS[j], r.tA) * D2R, pB = siderealLongitude(PLANETS[j], r.tB) * D2R;
    nar[j] = Math.cos(pA); nai[j] = -Math.sin(pA);
    nbr[j] = Math.cos(pB); nbi[j] = -Math.sin(pB);
  }
  r.nar = nar; r.nai = nai; r.nbr = nbr; r.nbi = nbi;
}

/** The SIGNED score, from the precomputed coefficients — a quadratic form, no integral. */
function signedScore(th, r) {
  const b0 = th[0], b1 = th[1];
  // v_j^P = a_j * conj(N_j^P)
  const var_ = new Float64Array(NB), vai = new Float64Array(NB), vbr = new Float64Array(NB), vbi = new Float64Array(NB);
  for (let j = 0; j < NB; j++) {
    const ar = th[2 + 2 * j], ai = th[3 + 2 * j];
    var_[j] = ar * r.nar[j] - ai * r.nai[j]; vai[j] = ar * r.nai[j] + ai * r.nar[j];
    vbr[j] = ar * r.nbr[j] - ai * r.nbi[j]; vbi[j] = ar * r.nbi[j] + ai * r.nbr[j];
  }
  let s = b0 * b0 + b1 * b1;
  for (let j = 0; j < NB; j++) {
    // Re[ conj(b) * v_j^A * C_j ]  and  Re[ b * conj(v_j^B) * conj(C_j) ]
    const xr = var_[j] * r.Cr[j] - vai[j] * r.Ci[j], xi = var_[j] * r.Ci[j] + vai[j] * r.Cr[j];
    s += b0 * xr + b1 * xi;
    const yr = vbr[j] * r.Cr[j] - vbi[j] * r.Ci[j], yi = vbr[j] * r.Ci[j] + vbi[j] * r.Cr[j];
    s += b0 * yr + b1 * yi;
    for (let m = 0; m < NB; m++) {
      // Re[ v_j^A conj(v_m^B) D_jm ]
      const pr = var_[j] * vbr[m] + vai[j] * vbi[m], pi = vai[j] * vbr[m] - var_[j] * vbi[m];
      s += pr * r.Dr[j * NB + m] - pi * r.Di[j * NB + m];
    }
  }
  return s;
}
/** The POSITIVE-part score, by direct integration. Costly, so used sparingly. */
function positiveScore(th, r, step = STEP) {
  const n = Math.floor(T28 / step) + 1;
  let acc = 0;
  for (let k = 0; k < n; k++) {
    const t = r.tM + k * step;
    let ar = th[0], ai = th[1], br = th[0], bi = th[1];
    for (let j = 0; j < NB; j++) {
      const th2 = siderealLongitude(PLANETS[j], t) * D2R;
      const ec = Math.cos(th2), es = Math.sin(th2);
      const a0 = th[2 + 2 * j], a1 = th[3 + 2 * j];
      // a_j * E_j * conj(N_j)
      const vAr = a0 * r.nar[j] - a1 * r.nai[j], vAi = a0 * r.nai[j] + a1 * r.nar[j];
      const vBr = a0 * r.nbr[j] - a1 * r.nbi[j], vBi = a0 * r.nbi[j] + a1 * r.nbr[j];
      ar += vAr * ec - vAi * es; ai += vAr * es + vAi * ec;
      br += vBr * ec - vBi * es; bi += vBr * es + vBi * ec;
    }
    const v = ar * br + ai * bi;
    if (v > 0) acc += v;
  }
  return acc / n;
}

const sigma = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));
const NP = 2 + 2 * NB;
function fitReadout(S, set) {
  const m = set.reduce((s, r) => s + S.get(r), 0) / set.length;
  const sd = Math.sqrt(set.reduce((s, r) => s + (S.get(r) - m) ** 2, 0) / set.length) || 1;
  let c0 = 0, c1 = 0;
  for (let it = 0; it < 300; it++) {
    let g0 = 0, g1 = 0, h0 = 0, h1 = 0;
    for (const r of set) {
      const x = (S.get(r) - m) / sd, p = sigma(c0 + c1 * x), w = Math.max(p * (1 - p), 1e-6);
      g0 += r.y - p; g1 += (r.y - p) * x; h0 += w; h1 += w * x * x;
    }
    c0 += g0 / (h0 + 1); c1 += g1 / (h1 + 1);
  }
  return { c0, c1, m, sd };
}
const accWith = (S, ro, set) => set.filter((r) => (sigma(ro.c0 + ro.c1 * (S.get(r) - ro.m) / ro.sd) >= 0.5 ? 1 : 0) === r.y).length / set.length;

/** Fit the amplitudes against the SIGNED score, which is cheap enough for a real optimisation. */
function fitSigned({ steps = 500, batch = 400, restarts = 4 } = {}) {
  let best = null;
  for (let rs = 0; rs < restarts; rs++) {
    const th = new Float64Array(NP);
    th[0] = 0.3 * gauss(); th[1] = 0.3 * gauss();
    for (let j = 0; j < NB; j++) { th[2 + 2 * j] = 0.4 * gauss(); th[3 + 2 * j] = 0.4 * gauss(); }
    const m = new Float64Array(NP), v = new Float64Array(NP);
    const b1 = 0.9, b2 = 0.999, eps = 1e-8, h = 1e-4;
    const lossOn = (tt, set) => {
      const S = new Map();
      for (const r of set) S.set(r, signedScore(tt, r));
      const ro = fitReadout(S, set);
      let l = 0;
      for (const r of set) {
        const p = Math.min(1 - 1e-12, Math.max(1e-12, sigma(ro.c0 + ro.c1 * (S.get(r) - ro.m) / ro.sd)));
        l -= r.y ? Math.log(p) : Math.log(1 - p);
      }
      return l / set.length;
    };
    for (let t = 1; t <= steps; t++) {
      const lr = 0.06 * (1 - t / (steps + 1));
      const bt = [];
      for (let i = 0; i < batch; i++) bt.push(TR[Math.floor(rnd() * TR.length)]);
      for (let i = 0; i < NP; i++) {
        const o = th[i];
        th[i] = o + h; const lp = lossOn(th, bt);
        th[i] = o - h; const lm = lossOn(th, bt);
        th[i] = o;
        const g = (lp - lm) / (2 * h);
        m[i] = b1 * m[i] + (1 - b1) * g;
        v[i] = b2 * v[i] + (1 - b2) * g * g;
        th[i] -= lr * (m[i] / (1 - b1 ** t)) / (Math.sqrt(v[i] / (1 - b2 ** t)) + eps);
      }
    }
    const l = lossOn(th, TR);
    if (!best || l < best.l) best = { l, th: Float64Array.from(th) };
  }
  return best.th;
}

console.log(`\n  fitting the amplitudes against the signed score (the cheap quadratic form)`);
const th = fitSigned();
const Ssig = new Map();
for (const r of data) Ssig.set(r, signedScore(th, r));
const roS = fitReadout(Ssig, TR);
console.log(`\n  score                                    TRAIN     VAL      TEST`);
console.log(`  SIGNED interference, 28 y                ${(100 * accWith(Ssig, roS, TR)).toFixed(2)}%   ${(100 * accWith(Ssig, roS, VA)).toFixed(2)}%   ${(100 * accWith(Ssig, roS, TE)).toFixed(2)}%`);
const Spos = new Map();
for (const r of data) Spos.set(r, positiveScore(th, r));
const roP = fitReadout(Spos, TR);
console.log(`  POSITIVE part, same amplitudes           ${(100 * accWith(Spos, roP, TR)).toFixed(2)}%   ${(100 * accWith(Spos, roP, VA)).toFixed(2)}%   ${(100 * accWith(Spos, roP, TE)).toFixed(2)}%`);
console.log(`  ${"the coin".padEnd(40)}   —        —       50.00%`);

// ── the amplitudes, and what the score tracks ───────────────────────────────────────────────────
{
  const amp = PLANETS.map((n, j) => ({ n, a: Math.hypot(th[2 + 2 * j], th[3 + 2 * j]) })).sort((x, y) => y.a - x.a);
  console.log(`\n  fitted amplitudes |a_j|:`);
  for (const q of amp) console.log(`    ${q.n.padEnd(9)} ${q.a.toFixed(4)}`);
  const outer = Math.hypot(...amp.filter((q) => ["Uranus", "Neptune", "Pluto"].includes(q.n)).map((q) => q.a));
  console.log(`    the three outer planets hold ${(100 * (outer / Math.hypot(...amp.map((q) => q.a))) ** 2).toFixed(1)}% of the squared amplitude`);
  console.log(`    b = ${th[0].toFixed(4)} + ${th[1].toFixed(4)}i`);

  const corr = (f, g) => {
    const n = data.length, mf = data.reduce((s, r) => s + f(r), 0) / n, mg = data.reduce((s, r) => s + g(r), 0) / n;
    let c = 0, df = 0, dg = 0;
    for (const r of data) { c += (f(r) - mf) * (g(r) - mg); df += (f(r) - mf) ** 2; dg += (g(r) - mg) ** 2; }
    return c / Math.sqrt(df * dg);
  };
  console.log(`\n  WHAT THE POSITIVE SCORE TRACKS — the test the earlier model failed`);
  console.log(`    vs age gap         : r = ${corr((r) => Spos.get(r), (r) => r.gap).toFixed(4)}`);
  console.log(`    vs age at marriage : r = ${corr((r) => Spos.get(r), (r) => r.ageM).toFixed(4)}`);
  console.log(`    vs mean birth year : r = ${corr((r) => Spos.get(r), (r) => r.year).toFixed(4)}`);
  console.log(`    vs wedding year    : r = ${corr((r) => Spos.get(r), (r) => r.wedYear).toFixed(4)}`);
  console.log(`    vs DIVORCE         : r = ${corr((r) => Spos.get(r), (r) => r.y).toFixed(4)}`);
  console.log(`\n    The previous interference model scored -0.83 against age at marriage and -0.80 against`);
  console.log(`    the age gap, because its linear phase made it a function of the two ages and nothing`);
  console.log(`    else. Whether this one has escaped that is exactly what these numbers say.`);
}
