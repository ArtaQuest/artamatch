/**
 * calibrate-affinity.mjs — what an affinity score is worth, and whether it is worth anything.
 *
 * The raw score lives in about [-0.13, +0.21] and means nothing to a reader, so the page only ever
 * shows a percentile against the table this prints. It also runs the ABLATIONS, in the house style
 * of analysis/adstopics: every component has to earn its place against the model without it, and
 * every claim is stated against a baseline rather than on its own.
 *
 *   echo 'export * from "./src/engine/affinity"; export * from "./src/engine/score";' |
 *     npx esbuild --bundle --format=esm --loader:.ts=ts --sourcefile=e.ts --outfile=/tmp/aff.mjs
 *   node tools/calibrate-affinity.mjs /tmp/aff.mjs
 *
 * Deterministic: same seed, same answer, every time.
 */

const mod = await import(process.argv[2] ?? "/tmp/aff.mjs");
const { affinity, matchPair, AFFINITY_MIN, AFFINITY_MAX, AFFINITY_STEPS, BODY_WEIGHT, ASPECTS } = mod;

const N = Number(process.env.N ?? 20000);
const SEED = 13579;

let s = SEED;
const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
const date = () => {
  const y = 1930 + Math.floor(rnd() * 80);
  const m = 1 + Math.floor(rnd() * 12);
  const d = 1 + Math.floor(rnd() * 28);
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
};

const OPPOSITE = process.env.OPPOSITE ?? "hard";
const raw = [], guna = [], bandWidth = [], ease = [], friction = [];
// Does variance weighting quietly crush the Moon? The Sun moves ~1 degree a day and is pinned to a
// third of a degree; the Moon moves 13 and is not. If the Moon ends up carrying a couple of per
// cent of the answer then "it reads the whole chart" is false and the page must stop saying it.
const bodyWeight = new Map(), bodyShare = new Map();
const note = (m, k, v) => m.set(k, (m.get(k) ?? 0) + v);

for (let i = 0; i < N; i++) {
  const a = date(), b = date();
  // Every 40th pair is computed the slow way too, so the closed form is checked against brute
  // force on 500 fresh random pairs rather than only on the handful a test hard-codes.
  const withCheck = i % 40 === 0;
  const r = affinity(a, b, { verify: withCheck, opposite: OPPOSITE });
  if (!r) continue;
  raw.push(r.net);
  ease.push(r.ease); friction.push(r.friction);
  for (const t of r.terms) {
    note(bodyWeight, t.bodyA, t.confidence); note(bodyWeight, t.bodyB, t.confidence);
    note(bodyShare, t.bodyA, Math.abs(t.contribution)); note(bodyShare, t.bodyB, Math.abs(t.contribution));
  }
  if (withCheck) bandWidth.push({ gap: r.agreement, width: r.spread.hi - r.spread.lo });
  const m = matchPair(a, b);
  guna.push(m ? m.distribution.expected : 21);
}

const sorted = [...raw].sort((a, b) => a - b);
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
const sd = (xs) => { const m = mean(xs); return Math.sqrt(mean(xs.map((v) => (v - m) ** 2))); };
const at = (xs, p) => xs[Math.min(xs.length - 1, Math.floor((p / 100) * xs.length))];
const shareBelow = (v) => {
  let lo = 0, hi = sorted.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (sorted[mid] < v) lo = mid + 1; else hi = mid; }
  return Math.round((lo / sorted.length) * 100);
};
const pearson = (xs, ys) => {
  const mx = mean(xs), my = mean(ys);
  let n = 0, dx = 0, dy = 0;
  for (let i = 0; i < xs.length; i++) { n += (xs[i] - mx) * (ys[i] - my); dx += (xs[i] - mx) ** 2; dy += (ys[i] - my) ** 2; }
  return n / Math.sqrt(dx * dy);
};

console.log(`${raw.length} random pairs, seed ${SEED}, opposite read as ${OPPOSITE}\n`);
console.log(`ease        mean ${mean(ease).toFixed(4)}  sd ${sd(ease).toFixed(4)}`);
console.log(`friction    mean ${mean(friction).toFixed(4)}  sd ${sd(friction).toFixed(4)}`);
console.log(`net score   mean ${mean(raw).toFixed(4)}  sd ${sd(raw).toFixed(4)}  ` +
  `5th ${at(sorted, 5).toFixed(4)}  50th ${at(sorted, 50).toFixed(4)}  95th ${at(sorted, 95).toFixed(4)}  ` +
  `min ${sorted[0].toFixed(4)}  max ${sorted[sorted.length - 1].toFixed(4)}`);

const step = (AFFINITY_MAX - AFFINITY_MIN) / (AFFINITY_STEPS - 1);
const table = Array.from({ length: AFFINITY_STEPS }, (_, i) => shareBelow(AFFINITY_MIN + i * step));
console.log(`\nAFFINITY_BELOW_${OPPOSITE.toUpperCase()} (${AFFINITY_STEPS} steps from ${AFFINITY_MIN} to ${AFFINITY_MAX}):`);
console.log("  " + JSON.stringify(table));

if (bandWidth.length) {
  const gaps = bandWidth.map((b) => b.gap).sort((a, b) => a - b);
  const widths = bandWidth.map((b) => b.width).sort((a, b) => a - b);
  console.log(`\nclosed form vs brute force over ${gaps.length} pairs: ` +
    `median ${at(gaps, 50).toExponential(2)}  worst ${gaps[gaps.length - 1].toExponential(2)}`);
  console.log(`within-pair 90% band width: median ${at(widths, 50).toFixed(4)} ` +
    `vs population sd ${sd(raw).toFixed(4)}  ->  ratio ${(at(widths, 50) / sd(raw)).toFixed(2)}`);
  console.log(`  (a ratio near or above 1 means the unknown birth hours matter about as much as`);
  console.log(`   the difference between two couples — which is a finding, and belongs on the page)`);
}

console.log(`\nvs the traditional 36-point Moon score: pearson ${pearson(raw, guna).toFixed(3)}`);

// ── ABLATIONS AND ROBUSTNESS, in the adstopics house style: every component earns its place
// against the model without it, and every choice that could not be sourced is shown not to matter.
// Run on a subsample, because each variant re-scores every pair.
const M = Math.min(raw.length, Number(process.env.M ?? 700));
const rank = (xs) => { const ix = xs.map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]);
  const r = new Array(xs.length); ix.forEach(([, i], k) => (r[i] = k)); return r; };
const spearman = (x, y) => pearson(rank(x), rank(y));

let s2 = SEED; const rnd2 = () => { s2 = (s2 * 1664525 + 1013904223) % 4294967296; return s2 / 4294967296; };
const date2 = () => { const y = 1930 + Math.floor(rnd2() * 80), m = 1 + Math.floor(rnd2() * 12),
  d = 1 + Math.floor(rnd2() * 28); return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`; };
const sample = Array.from({ length: M }, () => [date2(), date2()]);
const runAll = (o = {}) => sample.map(([a, b]) => { const r = affinity(a, b, { verify: false, opposite: OPPOSITE, ...o }); return r ? r.net : 0; });

const baseRun = runAll();
const variants = [];
const saveA = ASPECTS.map((a) => a.valence);
const saveW = { ...BODY_WEIGHT };

const withAspects = (label, vals) => {
  ASPECTS.forEach((a, i) => (a.valence = vals[i]));
  variants.push([label, runAll()]);
  ASPECTS.forEach((a, i) => (a.valence = saveA[i]));
};
// The exchange rate: the one number with no traditional basis at all. Scaling the two hard angles
// IS scaling how many easy angles cancel one hard one.
for (const f of [0.5, 0.75, 1.5, 2.0]) withAspects(`exchange rate x${f}`, [null, 0.5, -f, 1, -f]);
// NOT via the ASPECTS table: the opposite angle's valence is served by the reader-facing switch,
// so mutating the table here changed nothing and the ablation dutifully reported a perfect 1.000 —
// an ablation that has stopped testing anything looks exactly like a component that does not matter.
variants.push(["opposite read as easy", runAll({ opposite: "easy" })]);
withAspects("sixth = third", [null, 1, -1, 1, -1]);
withAspects("same-place fixed at +1", [1, 0.5, -1, 1, -1]);
// Body importance: ordinal in the sources, numbered by us.
for (const b of Object.keys(BODY_WEIGHT)) BODY_WEIGHT[b] = 1;
variants.push(["all bodies equal", runAll()]);
Object.assign(BODY_WEIGHT, saveW);

// The two that undercut the model rather than flatter it. Reported for the same reason the paper
// this borrows its shape from reports its own centring as worth "only ~0.003 AUC": an ablation you
// only publish when it agrees with you is not an ablation.
// (Both are computed longhand in the test suite; see tests/affinity.test.ts.)

console.log(`\nROBUSTNESS AND ABLATIONS — rank correlation with the model as shipped (${M} pairs):`);
for (const [label, xs] of variants) {
  console.log(`  ${label.padEnd(26)} spearman ${spearman(baseRun, xs).toFixed(3)}`);
}

const bodies = Object.keys(BODY_WEIGHT);
const totalShare = [...bodyShare.values()].reduce((a, b) => a + b, 0);
console.log(`\nHOW MUCH EACH BODY ACTUALLY CARRIES (the check that "it reads the whole chart" is true):`);
for (const b of bodies) {
  const conf = bodyWeight.get(b) / (raw.length * 2 * bodies.length);
  console.log(`  ${b.padEnd(8)} mean confidence ${conf.toFixed(3)}   share of the answer ` +
    `${(100 * bodyShare.get(b) / totalShare).toFixed(1)}%   (stated importance ${BODY_WEIGHT[b]})`);
}
