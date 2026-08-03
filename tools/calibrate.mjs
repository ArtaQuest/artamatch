/**
 * calibrate.mjs — what a score is actually worth.
 *
 * Scores 20,000 random date pairs and prints the percentile table that src/engine/score.ts embeds,
 * plus the facts the UI quotes: the median pair, and the share clearing the traditional pass mark.
 *
 * (The ρ ≈ 0.95 correlation that killed the old 60/30/10 blend was measured on the retired
 * implementation before its removal — this script no longer computes the blend, because the blend
 * no longer exists to compute.)
 *
 *   npx esbuild src/engine/score.ts --format=esm --bundle --outfile=/tmp/score.mjs
 *   node tools/calibrate.mjs /tmp/score.mjs
 *
 * Deterministic: same seed, same answer, every time.
 */

const mod = await import(process.argv[2] ?? "/tmp/score.mjs");
const { matchPair } = mod;
// Optional second module for the three extra systems (numbersMatch/animalsMatch/sunSignsMatch):
//   npx esbuild src/engine/systems.ts --format=esm --bundle --outfile=/tmp/systems.mjs
//   node tools/calibrate.mjs /tmp/score.mjs /tmp/systems.mjs
const sys = process.argv[3] ? await import(process.argv[3]) : null;

const N = 20000;
const SEED = 13579;

let s = SEED;
const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
const date = () => {
  const y = 1930 + Math.floor(rnd() * 80);
  const m = 1 + Math.floor(rnd() * 12);
  const d = 1 + Math.floor(rnd() * 28);
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
};

const scores = [];
for (let i = 0; i < N; i++) {
  const m = matchPair(date(), date());
  if (m) scores.push(m.score);
}
scores.sort((a, b) => a - b);

const shareBelow = (v) => {
  let lo = 0, hi = scores.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (scores[mid] < v) lo = mid + 1; else hi = mid; }
  return Math.round((lo / scores.length) * 100);
};

const table = Array.from({ length: 37 }, (_, v) => shareBelow(v));
const q = (f) => scores[Math.floor(scores.length * f)];

console.log(`n = ${scores.length}, seed = ${SEED}\n`);
console.log("PERCENTILE_BELOW (index = score 0…36):");
console.log("  " + JSON.stringify(table));
console.log();
console.log(`median (MEDIAN_SCORE)      ${q(0.5)}`);
console.log(`share clearing 18 (PASS_RATE)  ${(scores.filter((x) => x >= 18).length / scores.length * 100).toFixed(0)}%`);
console.log();
console.log("band cutoffs, by percentile:");
for (const p of [0.25, 0.5, 0.75, 0.95]) console.log(`  p${(p * 100).toFixed(0).padStart(2)}  ${q(p)}`);
console.log();
console.log("distinct scores (ranking granularity):", new Set(scores).size);

if (sys) {
  const tally = (fn) => {
    let s2 = SEED;
    const r2 = () => { s2 = (s2 * 1664525 + 1013904223) % 4294967296; return s2 / 4294967296; };
    const d2 = () => {
      const y = 1930 + Math.floor(r2() * 80), m = 1 + Math.floor(r2() * 12), d = 1 + Math.floor(r2() * 28);
      return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    };
    const t = {};
    for (let i = 0; i < N; i++) { const r = fn(d2(), d2()); if (r) t[r.score] = (t[r.score] || 0) + 1; }
    const n = Object.values(t).reduce((a, b) => a + b, 0);
    return Object.fromEntries(Object.entries(t).sort((a, b) => +a[0] - +b[0]).map(([k, v]) => [k, +(v / n).toFixed(4)]));
  };
  console.log("\nNUMBERS_DIST  =", JSON.stringify(tally(sys.numbersMatch)));
  console.log("ANIMALS_DIST  =", JSON.stringify(tally(sys.animalsMatch)));
  console.log("SUNSIGNS_DIST =", JSON.stringify(tally(sys.sunSignsMatch)));
}
