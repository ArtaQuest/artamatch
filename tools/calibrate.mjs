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
