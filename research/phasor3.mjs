/**
 * phasor3.mjs — the phasor model on a day-by-day ephemeris table over the whole dataset span.
 *
 *     z_P  =  b  +  SUM_m  u_m · exp( i · THETA_m( t_P ) )        u_m complex, one per channel
 *
 * ── What changes from phasor2 ───────────────────────────────────────────────────────────────────
 *
 * The angle is no longer w_j·t. A linear phase treats every planet as a perfect circle turning at a
 * constant rate, which is wrong by up to a couple of degrees for the eccentric orbits (Mercury, Mars)
 * and wrong about the Moon by rather more. Here every angle is the ACTUAL sidereal longitude, read from
 * a table computed for every single day the dataset touches — 511 to 2026, about 553,000 days per body.
 *
 * A table rather than a call per row for three reasons: the same date recurs across couples so the work
 * is shared; the interference integral needs positions at hundreds of times per couple and a lookup is
 * two orders of magnitude cheaper than an ephemeris evaluation; and having the whole span in memory
 * makes it possible to check the table against direct computation, which is done below.
 *
 * ── The channels ────────────────────────────────────────────────────────────────────────────────
 *
 * With real angles the frequency set of phasor2 becomes a set of ANGLE CHANNELS, each an exp(i·something)
 * built from the tabulated longitudes:
 *
 *   PLANETS    exp(i·th_j)                     10 channels — where each body actually is
 *   HARMONICS  exp(2i·th_j), exp(3i·th_j)      20 more — the 2nd harmonic IS the square/opposition
 *                                              axis, the cos(2*phi) the aspect tradition turns on
 *   SYNODIC    exp(i·(th_j - th_k))            45 more — the real relative angle between two bodies,
 *                                              which is what a conjunction cycle is
 *
 * The synodic channels are the interesting addition: w_j - w_k was an approximation to them in
 * phasor2, and with a table the true relative angle is available instead.
 *
 * ── A LIMIT THAT HAS TO BE STATED ───────────────────────────────────────────────────────────────
 *
 * The dataset reaches back to the sixth century. The JPL Table-1 elements this ephemeris uses are
 * stated for 1800-2050 and were verified here against the Swiss Ephemeris over 1900-2100. Every
 * position before 1800 is extrapolation, and the further back the worse. 96% of the dataset's dates
 * fall after 1800, so the effect is small — but it is a real error in the FEATURES, and error in the
 * features can only wash a signal out, never manufacture one.
 *
 * Usage: EPH=/tmp/aq-eph.mjs node research/phasor3.mjs ./research/data-divorce
 */

import { readFileSync } from "node:fs";
const EPH = process.env.EPH ?? "/tmp/aq-eph.mjs";
const { siderealLongitude, julianDay } = await import(EPH);

const D2R = Math.PI / 180;
const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"];
const NB = PLANETS.length;
const YR = 365.2425;
const DIR = process.argv[2] ?? "./research/data-divorce";

let SEED = 20260807;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };
const shuffle = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());

// ── the data, first, so the table covers exactly what is needed ──────────────────────────────────
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
  rows.push({ a: pa, b: pb, y: r.y, ja, jb, year: (ya + yb) / 2, gap: (jb - ja) / YR });
}
SEED = 20260807;
const posR = rows.filter((r) => r.y === 1), negR = rows.filter((r) => r.y === 0);
const KK = Math.min(posR.length, negR.length);
const data = shuffle([...shuffle(posR).slice(0, KK), ...shuffle(negR).slice(0, KK)]);

// ── the day-by-day table ────────────────────────────────────────────────────────────────────────
const JD0 = Math.floor(Math.min(...data.map((r) => r.ja))) - 2;
const JD1 = Math.ceil(Math.max(...data.map((r) => r.jb))) + 2;
const NDAY = JD1 - JD0 + 1;
console.log(`\nA DAY-BY-DAY EPHEMERIS OVER THE WHOLE SPAN`);
console.log(`  Julian day ${JD0} to ${JD1} — ${NDAY.toLocaleString()} days, ${NB} bodies, ${(NDAY * NB * 16 / 1e6).toFixed(1)} MB as cos/sin pairs`);
const COS = [], SIN = [];
for (let j = 0; j < NB; j++) { COS.push(new Float64Array(NDAY)); SIN.push(new Float64Array(NDAY)); }
for (let d = 0; d < NDAY; d++) {
  const jd = JD0 + d;
  for (let j = 0; j < NB; j++) {
    const th = siderealLongitude(PLANETS[j], jd) * D2R;
    COS[j][d] = Math.cos(th); SIN[j][d] = Math.sin(th);
  }
}
const idx = (jd) => Math.round(jd) - JD0;

// ── triple-check the table ──────────────────────────────────────────────────────────────────────
console.log(`\n  CHECKING THE TABLE against direct ephemeris calls`);
{
  let worst = 0, worstAt = null;
  SEED = 999;
  for (let k = 0; k < 400; k++) {
    const jd = JD0 + Math.floor(rnd() * NDAY);
    const d = idx(jd);
    for (let j = 0; j < NB; j++) {
      const th = siderealLongitude(PLANETS[j], jd) * D2R;
      const e = Math.max(Math.abs(COS[j][d] - Math.cos(th)), Math.abs(SIN[j][d] - Math.sin(th)));
      if (e > worst) { worst = e; worstAt = `${PLANETS[j]} at jd ${jd}`; }
    }
  }
  console.log(`    largest cos/sin discrepancy over 400 random days x ${NB} bodies: ${worst.toExponential(2)} (${worstAt})`);
  console.log(`    ${worst < 1e-12 ? "PASS" : "FAIL"} — the table is the ephemeris, not an approximation of it`);
  // How much did the linear w*t phasor of phasor2 actually get wrong?
  const PERIOD = { Sun: 365.256363, Moon: 27.321661, Mercury: 87.9691, Venus: 224.700796, Mars: 686.9800,
    Jupiter: 4332.589, Saturn: 10759.22, Uranus: 30688.5, Neptune: 60182.0, Pluto: 90560.0 };
  console.log(`\n    and how wrong the linear w*t phasor was, in degrees of longitude:`);
  for (let j = 0; j < NB; j++) {
    const w = 2 * Math.PI / PERIOD[PLANETS[j]];
    let worstDeg = 0;
    for (let k = 0; k < 300; k++) {
      const jd = JD0 + Math.floor(rnd() * NDAY);
      const real = Math.atan2(SIN[j][idx(jd)], COS[j][idx(jd)]);
      const lin = w * (jd - 2451545.0);
      let diff = ((real - lin) % (2 * Math.PI) + 3 * Math.PI) % (2 * Math.PI) - Math.PI;
      worstDeg = Math.max(worstDeg, Math.abs(diff) * 180 / Math.PI);
    }
    console.log(`      ${PLANETS[j].padEnd(9)} up to ${worstDeg.toFixed(1).padStart(6)} deg away from the true longitude`);
  }
  console.log(`    A linear phase is not a small approximation — over five centuries the accumulated`);
  console.log(`    difference is large, so the two models are not variants of each other.`);
}

// ── channels built from the table ────────────────────────────────────────────────────────────────
/** Each channel is a function (dayIndex) -> [cos, sin] of some angle built from the real longitudes. */
function buildChannels(kind) {
  const ch = [];
  for (let j = 0; j < NB; j++) ch.push({ name: PLANETS[j], f: (d) => [COS[j][d], SIN[j][d]] });
  if (kind === "harmonics" || kind === "all") {
    for (const n of [2, 3]) {
      for (let j = 0; j < NB; j++) {
        ch.push({ name: `${n}x${PLANETS[j]}`, f: (d) => {
          // cos(n*th), sin(n*th) by repeated angle addition — no atan2, no trig call.
          let c = COS[j][d], s = SIN[j][d], cc = c, ss = s;
          for (let q = 1; q < n; q++) { const nc = cc * c - ss * s, ns = ss * c + cc * s; cc = nc; ss = ns; }
          return [cc, ss];
        } });
      }
    }
  }
  if (kind === "synodic" || kind === "all") {
    for (let j = 0; j < NB; j++) for (let k = j + 1; k < NB; k++) {
      ch.push({ name: `${PLANETS[j]}-${PLANETS[k]}`, f: (d) =>
        [COS[j][d] * COS[k][d] + SIN[j][d] * SIN[k][d], SIN[j][d] * COS[k][d] - COS[j][d] * SIN[k][d]] });
    }
  }
  return ch;
}
const CHANNEL_SETS = {
  "10 real longitudes": "planets",
  "+ 2nd and 3rd harmonics (30)": "harmonics",
  "+ real synodic angles (55)": "synodic",
  "everything (75)": "all",
};

const side = new Map();
SEED = 20260807;
for (const r of data) {
  let s = side.get(r.a) ?? side.get(r.b);
  if (s === undefined) { const u = rnd(); s = u < 0.6 ? "train" : u < 0.8 ? "val" : "test"; }
  side.set(r.a, s); side.set(r.b, s);
  r.side = s;
}
const TR = data.filter((r) => r.side === "train"), VA = data.filter((r) => r.side === "val"), TE = data.filter((r) => r.side === "test");
console.log(`\n  ${data.length.toLocaleString()} couples, ${KK.toLocaleString()} per class — ${TR.length.toLocaleString()} train · ${VA.length.toLocaleString()} val · ${TE.length.toLocaleString()} test`);
console.log(`  channels, rank and ridge chosen on VALIDATION; the test set is scored once.`);

/** Precompute every channel's cos/sin for both partners of every couple. */
function prepare(kind) {
  const ch = buildChannels(kind), F = ch.length;
  for (const r of data) {
    const da = idx(r.ja), db = idx(r.jb);
    const ca = new Float64Array(F), sa = new Float64Array(F), cb = new Float64Array(F), sb = new Float64Array(F);
    for (let m = 0; m < F; m++) {
      const [c1, s1] = ch[m].f(da), [c2, s2] = ch[m].f(db);
      ca[m] = c1; sa[m] = s1; cb[m] = c2; sb[m] = s2;
    }
    r.ca = ca; r.sa = sa; r.cb = cb; r.sb = sb;
  }
  return { ch, F };
}

const sigma = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));
const layout = (F, R) => ({ per: 2 + 2 * F + 4, total: 1 + R * (2 + 2 * F + 4) });
function logitOf(th, r, F, R) {
  const { per } = layout(F, R);
  let z = th[0];
  for (let c = 0; c < R; c++) {
    const o = 1 + c * per;
    let ar = th[o], ai = th[o + 1], br = th[o], bi = th[o + 1];
    for (let m = 0; m < F; m++) {
      const ux = th[o + 2 + 2 * m], uy = th[o + 3 + 2 * m];
      ar += ux * r.ca[m] - uy * r.sa[m];
      ai += ux * r.sa[m] + uy * r.ca[m];
      br += ux * r.cb[m] - uy * r.sb[m];
      bi += ux * r.sb[m] + uy * r.cb[m];
    }
    const q = o + 2 + 2 * F;
    z += th[q] * (ar * br + ai * bi) + th[q + 1] * (ai * br - ar * bi)
      + th[q + 2] * (ar * ar + ai * ai) + th[q + 3] * (br * br + bi * bi);
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

function fit(F, R, l2, { steps = 1200, batch = 384, restarts = 2 } = {}) {
  const { total } = layout(F, R);
  let best = null;
  for (let rs = 0; rs < restarts; rs++) {
    const th = new Float64Array(total);
    const scale = 1 / Math.sqrt(F);
    for (let c = 0; c < R; c++) {
      const o = 1 + c * layout(F, R).per;
      th[o] = 0.2 * gauss(); th[o + 1] = 0.2 * gauss();
      for (let m = 0; m < F; m++) { th[o + 2 + 2 * m] = scale * gauss(); th[o + 3 + 2 * m] = scale * gauss(); }
      const q = o + 2 + 2 * F;
      for (let k = 0; k < 4; k++) th[q + k] = 0.05 * gauss();
    }
    const mm = new Float64Array(total), vv = new Float64Array(total);
    const b1 = 0.9, b2 = 0.999, eps = 1e-8, h = 1e-4;
    for (let t = 1; t <= steps; t++) {
      const lr = 0.05 * (1 - t / (steps + 1));
      const bt = [];
      for (let i = 0; i < batch; i++) bt.push(TR[Math.floor(rnd() * TR.length)]);
      for (let i = 0; i < total; i++) {
        const o = th[i];
        th[i] = o + h; const lp = loss(th, bt, F, R, l2);
        th[i] = o - h; const lm = loss(th, bt, F, R, l2);
        th[i] = o;
        const g = (lp - lm) / (2 * h);
        mm[i] = b1 * mm[i] + (1 - b1) * g;
        vv[i] = b2 * vv[i] + (1 - b2) * g * g;
        th[i] -= lr * (mm[i] / (1 - b1 ** t)) / (Math.sqrt(vv[i] / (1 - b2 ** t)) + eps);
      }
    }
    const l = loss(th, TR, F, R, l2);
    if (!best || l < best.l) best = { l, th: Float64Array.from(th) };
  }
  return best.th;
}

console.log(`\n  channel set                       rank  ridge  params   TRAIN     VAL`);
const trials = [];
for (const [cname, kind] of Object.entries(CHANNEL_SETS)) {
  const { ch, F } = prepare(kind);
  const ranks = F <= 10 ? [1, 2, 4] : F <= 30 ? [1, 2] : [1];
  const steps = F <= 10 ? 1200 : F <= 30 ? 700 : 400;
  for (const R of ranks) {
    for (const l2 of [1e-4, 1e-3]) {
      const th = fit(F, R, l2, { steps, restarts: F <= 10 ? 2 : 1 });
      const tr = accOf(th, TR, F, R), va = accOf(th, VA, F, R);
      trials.push({ cname, kind, ch, F, R, l2, th, tr, va });
      console.log(`  ${cname.padEnd(32)} ${String(R).padStart(4)}  ${l2.toExponential(0).padStart(5)}  ${String(layout(F, R).total).padStart(5)}   ${(100 * tr).toFixed(2)}%   ${(100 * va).toFixed(2)}%`);
    }
  }
}

trials.sort((a, b) => b.va - a.va);
const win = trials[0];
prepare(win.kind);
const te = accOf(win.th, TE, win.F, win.R);
console.log(`\n${"═".repeat(84)}`);
console.log(`  WINNER ON VALIDATION: ${win.cname}, rank ${win.R}, ridge ${win.l2.toExponential(0)}`);
console.log(`    ${layout(win.F, win.R).total} parameters — train ${(100 * win.tr).toFixed(2)}%   val ${(100 * win.va).toFixed(2)}%   TEST ${(100 * te).toFixed(2)}%`);
console.log(`    selection bias, val minus test: ${(100 * (win.va - te)).toFixed(2)} points`);

// ── what the winner reads ───────────────────────────────────────────────────────────────────────
{
  const { per } = layout(win.F, win.R);
  const amps = win.ch.map((c, m) => {
    let s = 0;
    for (let k = 0; k < win.R; k++) { const o = 1 + k * per; s += win.th[o + 2 + 2 * m] ** 2 + win.th[o + 3 + 2 * m] ** 2; }
    return { name: c.name, a: Math.sqrt(s) };
  }).sort((x, y) => y.a - x.a);
  console.log(`\n  the ten strongest channels by amplitude:`);
  for (const q of amps.slice(0, 10)) console.log(`    ${q.name.padEnd(22)} |u| ${q.a.toFixed(4)}`);
  const OUT = /Uranus|Neptune|Pluto/;
  const outer = Math.hypot(...amps.filter((q) => OUT.test(q.name)).map((q) => q.a));
  const tot = Math.hypot(...amps.map((q) => q.a));
  console.log(`    channels involving an outer planet hold ${(100 * (outer / tot) ** 2).toFixed(1)}% of the squared amplitude`);
}
