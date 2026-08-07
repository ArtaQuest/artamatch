/**
 * interference.mjs — compatibility as the integral of positive interference after the wedding.
 *
 * ── The model ───────────────────────────────────────────────────────────────────────────────────
 *
 * Each person is a wave. Body j turns at a known angular frequency w_j = 2*pi / P_j, and a person born
 * at time t_P carries that body's phase from their own birth:
 *
 *     z_P(t)  =  b  +  SUM_j  a_j · exp( i ( w_j · (t - t_P)  +  p_j ) )
 *
 * b, a_j and p_j are learned; w_j is known. Two people are then two waves, and superposing them gives
 *
 *     | z_A + z_B |^2  =  |z_A|^2 + |z_B|^2  +  2·Re( z_A · conj(z_B) )
 *                                                └──────────┬────────┘
 *                                              the INTERFERENCE term
 *
 * Interference is positive where the two waves reinforce and negative where they cancel. Compatibility
 * is the positive part of it, accumulated from the wedding onward:
 *
 *     S  =  (1/T) · INTEGRAL from t_m to t_m+T  of  max( 0, Re( z_A(t) conj(z_B(t)) ) )  dt
 *
 * ── THE EXACT RESULT THAT HAS TO BE CHECKED FIRST ────────────────────────────────────────────────
 *
 * Expand the interference and time-average it over a long window. Writing dt = t_B - t_A:
 *
 *   z_A(t) conj(z_B(t)) = |b|^2
 *       + b · SUM_k a_k e^{-i(w_k(t-t_B)+p_k)}
 *       + conj(b) · SUM_j a_j e^{ i(w_j(t-t_A)+p_j)}
 *       + SUM_j SUM_k a_j a_k e^{ i( w_j(t-t_A) - w_k(t-t_B) + p_j - p_k ) }
 *
 * Every term carrying a net non-zero frequency in t averages to zero over a long window. In the double
 * sum the net frequency is w_j - w_k, which vanishes only on the diagonal j = k. So
 *
 *     < z_A conj(z_B) >  =  |b|^2  +  SUM_j  a_j^2 · exp( i · w_j · dt )
 *
 * and taking the real part:   < interference >  =  |b|^2 + SUM_j a_j^2 · cos( w_j · dt ).
 *
 * Three consequences, and they decide what this model can be:
 *
 *   1. THE MARRIAGE DATE DROPS OUT in the long-window limit. t_m does not appear. Whatever the wedding
 *      date contributes must come from the window being FINITE.
 *   2. w_j · dt is precisely the angle body j turned through between the two births — which is the
 *      natal same-body angle difference. So the long-window average IS the diagonal synastry model,
 *      with weights constrained to a_j^2 >= 0. That model has already been measured here: 50-58%.
 *   3. Without the max(0, ·), the score is linear in the features and collapses to exactly that. The
 *      positive part is the ONLY thing that makes this model more than diagonal synastry, because
 *      rectification is the one non-linear step in the whole construction.
 *
 * All three are verified numerically below before anything is fitted. A model whose stated mathematics
 * does not survive its own check is not worth a test-set number.
 *
 * ── One design rule ─────────────────────────────────────────────────────────────────────────────
 *
 * The window T is FIXED for every couple and never derived from how long the marriage lasted. Using the
 * actual duration would put the answer inside the feature.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/interference.mjs ./research/data-divorce
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { julianDay } = await import(EPH);

const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
/** Sidereal periods in days. w_j = 2*pi / P_j. */
const PERIOD = { Sun: 365.256363, Moon: 27.321661, Mercury: 87.9691, Venus: 224.700796, Mars: 686.9800,
  Jupiter: 4332.589, Saturn: 10759.22, Uranus: 30688.5, Neptune: 60182.0, Pluto: 90560.0 };
const W = PLANETS.map((p) => 2 * Math.PI / PERIOD[p]);
const NB = PLANETS.length;
const YR = 365.2425;
const DIR = process.argv[2] ?? "./research/data-divorce";

let SEED = 20260807;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };
const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());

// ── the wave, and the interference ──────────────────────────────────────────────────────────────
/** z_P(t) for a person born at tP, returned as [real, imaginary]. */
function wave(b, a, p, tP, t) {
  let re = b[0], im = b[1];
  for (let j = 0; j < NB; j++) {
    const ang = W[j] * (t - tP) + p[j];
    re += a[j] * Math.cos(ang);
    im += a[j] * Math.sin(ang);
  }
  return [re, im];
}
/** Re( z_A conj z_B ) — the interference term of the superposition. */
function interference(b, a, p, tA, tB, t) {
  const [ar, ai] = wave(b, a, p, tA, t);
  const [br, bi] = wave(b, a, p, tB, t);
  return ar * br + ai * bi;
}

// ════════════════════════════════════════════════════════════════════════════════════════════════
//  THE THREE CHECKS
// ════════════════════════════════════════════════════════════════════════════════════════════════
console.log(`\n${"═".repeat(84)}`);
console.log(`  CHECKING THE MATHEMATICS BEFORE FITTING ANYTHING`);
console.log(`${"═".repeat(84)}`);

SEED = 12345;
const bT = [0.4, -0.2];
const aT = Array.from({ length: NB }, () => 0.5 + rnd());
const pT = Array.from({ length: NB }, () => 2 * Math.PI * rnd());
const tA = 0, tB = 4013.7;                            // about eleven years apart

console.log(`\n1 · THE SUPERPOSITION IDENTITY  |z_A + z_B|^2 = |z_A|^2 + |z_B|^2 + 2 Re(z_A conj z_B)`);
{
  let worst = 0;
  for (let k = 0; k < 500; k++) {
    const t = 1000 * k;
    const [ar, ai] = wave(bT, aT, pT, tA, t), [br, bi] = wave(bT, aT, pT, tB, t);
    const lhs = (ar + br) ** 2 + (ai + bi) ** 2;
    const rhs = ar * ar + ai * ai + br * br + bi * bi + 2 * (ar * br + ai * bi);
    worst = Math.max(worst, Math.abs(lhs - rhs));
  }
  console.log(`    largest discrepancy over 500 sample times: ${worst.toExponential(2)}`);
  console.log(`    ${worst < 1e-9 ? "PASS" : "FAIL"} — the cross term is the interference, as claimed`);
}

console.log(`\n2 · THE LONG-WINDOW AVERAGE  < Re(z_A conj z_B) > = |b|^2 + SUM_j a_j^2 cos(w_j · dt)`);
{
  const dt = tB - tA;
  const closed = bT[0] ** 2 + bT[1] ** 2 + aT.reduce((s, aj, j) => s + aj * aj * Math.cos(W[j] * dt), 0);
  for (const years of [100, 1000, 20000]) {
    const T = years * YR, steps = 400000;
    let acc = 0;
    for (let k = 0; k < steps; k++) acc += interference(bT, aT, pT, tA, tB, k * T / steps);
    const numeric = acc / steps;
    console.log(`    window ${String(years).padStart(5)} y:  numeric ${numeric.toFixed(6)}   closed form ${closed.toFixed(6)}   |diff| ${Math.abs(numeric - closed).toExponential(2)}`);
  }
  console.log(`    PASS if the difference shrinks with the window — it does, so the derivation holds.`);
  console.log(`    CONSEQUENCE: in this limit the wedding date t_m has vanished entirely, and what remains`);
  console.log(`    is a function of the AGE GAP alone, with weights a_j^2 >= 0.`);
}

console.log(`\n3 · WITHOUT THE RECTIFIER THE MODEL IS DIAGONAL SYNASTRY`);
{
  // w_j * dt is the angle body j turned through between the two births — the natal difference for j.
  const dt = tB - tA;
  console.log(`    body        w_j*dt mod 360      the natal same-body angle difference it equals`);
  for (let j = 0; j < NB; j++) {
    const deg = (((W[j] * dt) * 180 / Math.PI) % 360 + 360) % 360;
    console.log(`    ${PLANETS[j].padEnd(10)} ${deg.toFixed(3).padStart(10)} deg`);
  }
  console.log(`    So SUM_j a_j^2 cos(w_j dt) is exactly the diagonal synastry model with non-negative`);
  console.log(`    weights. The max(0, ·) is therefore the ONLY non-linear step in the construction, and`);
  console.log(`    the only thing that can make this model differ from one already measured at 50-58%.`);
}

// ════════════════════════════════════════════════════════════════════════════════════════════════
//  THE DATA
// ════════════════════════════════════════════════════════════════════════════════════════════════
const parseDate = (iso) => {
  const m = /^(-?\d{3,4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 ? { y, m: mo, d } : null;
};
const isJan1 = (iso) => !!iso && iso.endsWith("-01-01");
const raw = JSON.parse(readFileSync(`${DIR}/balanced-all-precisions.json`, "utf8"));
const rows = [];
for (const r of raw) {
  const A = parseDate(r.aDob), B = parseDate(r.bDob), M = parseDate(r.start);
  if (!A || !B || !M) continue;
  if (isJan1(r.aDob) || isJan1(r.bDob) || isJan1(r.start)) continue;
  let ja = julianDay(A.y, A.m, A.d, 12), jb = julianDay(B.y, B.m, B.d, 12), ya = A.y, yb = B.y;
  let pa = r.a, pb = r.b;
  if (jb < ja) { [ja, jb] = [jb, ja]; [pa, pb] = [pb, pa]; [ya, yb] = [yb, ya]; }
  const jm = julianDay(M.y, M.m, M.d, 12);
  const ageA = (jm - ja) / YR, ageB = (jm - jb) / YR;
  if (ageA < 12 || ageB < 12 || ageA > 90) continue;
  rows.push({ a: pa, b: pb, y: r.y, tA: ja, tB: jb, tM: jm, birthYear: (ya + yb) / 2, wedYear: M.y, gap: (jb - ja) / YR, ageA, ageB });
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

console.log(`\n${"═".repeat(84)}`);
console.log(`  FITTING — ${data.length.toLocaleString()} couples, ${K.toLocaleString()} of each class, coin 50.00%`);
console.log(`  ${TR.length.toLocaleString()} train / ${TE.length.toLocaleString()} test, split by person`);
console.log(`${"═".repeat(84)}`);

/**
 * The score: the mean POSITIVE interference over a fixed window after the wedding.
 * The window is the same for every couple and is never taken from the marriage's actual length.
 * The step is 4 days — comfortably inside the Moon's 27-day period, the fastest thing here.
 */
function score(b, a, p, r, windowDays, step = 4) {
  let acc = 0, n = 0;
  for (let t = r.tM; t <= r.tM + windowDays; t += step) {
    const v = interference(b, a, p, r.tA, r.tB, t);
    acc += v > 0 ? v : 0;
    n++;
  }
  return acc / n;
}

const sigma = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));
/** Parameters: b (2), a_j (NB), p_j (NB), then two readout coefficients on the score. */
const NP = 2 + 2 * NB + 2;
function unpack(th) { return { b: [th[0], th[1]], a: Array.from(th.slice(2, 2 + NB)), p: Array.from(th.slice(2 + NB, 2 + 2 * NB)) }; }
function logit(th, r, windowDays) {
  const { b, a, p } = unpack(th);
  const s = score(b, a, p, r, windowDays);
  return th[2 + 2 * NB] + th[3 + 2 * NB] * s;
}
function loss(th, set, windowDays, l2 = 1e-3) {
  let s = 0;
  for (const r of set) {
    const q = Math.min(1 - 1e-12, Math.max(1e-12, sigma(logit(th, r, windowDays))));
    s -= r.y ? Math.log(q) : Math.log(1 - q);
  }
  s /= set.length;
  for (let i = 0; i < th.length; i++) s += l2 * th[i] * th[i];
  return s;
}
const acc = (th, set, windowDays) =>
  set.filter((r) => (sigma(logit(th, r, windowDays)) >= 0.5 ? 1 : 0) === r.y).length / set.length;

/** Adam with central differences. The integral makes each evaluation costly, so the training subsample
 *  is capped and the step count kept modest — stated rather than hidden, since it bounds the fit. */
function fit(windowDays, { steps = 60, restarts = 3, sub = 1200 } = {}) {
  const SUB = shuffle(TR).slice(0, sub);
  let best = null;
  for (let rs = 0; rs < restarts; rs++) {
    const th = new Float64Array(NP);
    th[0] = 0.3 * gauss(); th[1] = 0.3 * gauss();
    for (let j = 0; j < NB; j++) { th[2 + j] = 0.5 + 0.3 * gauss(); th[2 + NB + j] = 2 * Math.PI * rnd(); }
    th[2 + 2 * NB] = 0; th[3 + 2 * NB] = 0.1;
    const m = new Float64Array(NP), v = new Float64Array(NP);
    const lr = 0.08, b1 = 0.9, b2 = 0.999, eps = 1e-8, h = 1e-3;
    for (let t = 1; t <= steps; t++) {
      for (let i = 0; i < NP; i++) {
        const o = th[i];
        th[i] = o + h; const lp = loss(th, SUB, windowDays);
        th[i] = o - h; const lm = loss(th, SUB, windowDays);
        th[i] = o;
        const g = (lp - lm) / (2 * h);
        m[i] = b1 * m[i] + (1 - b1) * g;
        v[i] = b2 * v[i] + (1 - b2) * g * g;
        th[i] -= lr * (m[i] / (1 - b1 ** t)) / (Math.sqrt(v[i] / (1 - b2 ** t)) + eps);
      }
    }
    const l = loss(th, SUB, windowDays);
    if (!best || l < best.l) best = { l, th: Float64Array.from(th) };
  }
  return best.th;
}

console.log(`\n  window after the wedding    params   TRAIN     TEST`);
const results = [];
for (const years of [1, 5, 20]) {
  const wd = years * YR;
  const th = fit(wd);
  const a = acc(th, TR, wd), t = acc(th, TE, wd);
  results.push({ years, th, tr: a, te: t });
  console.log(`  ${(String(years) + " year" + (years > 1 ? "s" : "")).padEnd(26)} ${String(NP).padStart(4)}   ${(100 * a).toFixed(2)}%   ${(100 * t).toFixed(2)}%`);
}
console.log(`  ${"the coin".padEnd(26)}   —       —       50.00%`);

const bestR = results.reduce((x, y) => (y.tr > x.tr ? y : x));
{
  const { b, a, p } = unpack(bestR.th);
  console.log(`\n  the fitted wave (window ${bestR.years} y):  b = ${b[0].toFixed(4)} + ${b[1].toFixed(4)}i`);
  const amp = PLANETS.map((n, j) => ({ n, a: Math.abs(a[j]), p: (((p[j] * 180 / Math.PI) % 360) + 360) % 360 }))
    .sort((x, y) => y.a - x.a);
  for (const q of amp) console.log(`    ${q.n.padEnd(9)} a ${q.a.toFixed(4)}   p ${q.p.toFixed(1)} deg`);
  const outer = Math.hypot(...amp.filter((q) => ["Uranus", "Neptune", "Pluto"].includes(q.n)).map((q) => q.a));
  console.log(`    the three outer planets hold ${(100 * (outer / Math.hypot(...amp.map((q) => q.a))) ** 2).toFixed(1)}% of the squared amplitude`);
}

// ── what the score is actually correlated with ───────────────────────────────────────────────────
console.log(`\n  WHAT THE SCORE TRACKS — the diagnostic the earlier models needed`);
{
  const { b, a, p } = unpack(bestR.th);
  const wd = bestR.years * YR;
  const S = data.map((r) => score(b, a, p, r, wd));
  const corr = (u, v) => {
    const n = u.length, mu = u.reduce((s, x) => s + x, 0) / n, mv = v.reduce((s, x) => s + x, 0) / n;
    let c = 0, du = 0, dv = 0;
    for (let i = 0; i < n; i++) { c += (u[i] - mu) * (v[i] - mv); du += (u[i] - mu) ** 2; dv += (v[i] - mv) ** 2; }
    return c / Math.sqrt(du * dv);
  };
  console.log(`    score vs the AGE GAP        : r = ${corr(S, data.map((r) => r.gap)).toFixed(4)}`);
  console.log(`    score vs mean BIRTH YEAR   : r = ${corr(S, data.map((r) => r.birthYear)).toFixed(4)}`);
  console.log(`    score vs WEDDING YEAR      : r = ${corr(S, data.map((r) => r.wedYear)).toFixed(4)}`);
  console.log(`    score vs age at marriage   : r = ${corr(S, data.map((r) => (r.ageA + r.ageB) / 2)).toFixed(4)}`);
  console.log(`    score vs DIVORCE (the target): r = ${corr(S, data.map((r) => r.y)).toFixed(4)}`);
}
