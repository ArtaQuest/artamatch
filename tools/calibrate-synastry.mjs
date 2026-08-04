/**
 * calibrate-synastry.mjs — what a count of connections is worth, and whether the two old systems
 * agree with each other.
 *
 * The aspect layer was cut from this page once before for a good reason: a second, unscored system
 * beside a scored one invites the question "is nineteen connections good?" and cannot answer it.
 * It is back because the question CAN be answered — by measuring it. This script does that, over
 * the same 20,000 random pairs the score is calibrated on, and the page quotes what it finds.
 *
 *   echo 'export * from "./src/engine/score"; export * from "./src/engine/synastry";
 *         export * from "./src/engine/uncertainty";' |
 *     npx esbuild --bundle --format=esm --loader:.ts=ts --sourcefile=entry.ts --outfile=/tmp/syn.mjs
 *   node tools/calibrate-synastry.mjs /tmp/syn.mjs
 *
 * Deterministic: same seed, same answer, every time.
 */

const mod = await import(process.argv[2] ?? "/tmp/syn.mjs");
const { matchPair, synastryGrid } = mod;

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

const counts = [];   // the mean over the 576 charts — the honest count for a pair
const sds = [];      // and how much it wandered across them
const settled = [];  // connections no birth time could take away
const scores = [];
const byKind = new Map();

for (let i = 0; i < N; i++) {
  const isoA = date(), isoB = date();
  const m = matchPair(isoA, isoB);
  if (!m) continue;
  const g = synastryGrid(isoA, isoB);
  counts.push(g.count.mean);
  sds.push(g.count.sd);
  settled.push(g.connections.filter((c) => c.certain).length);
  scores.push(m.distribution.expected);
  for (const c of g.connections) byKind.set(c.kind, (byKind.get(c.kind) ?? 0) + c.probability);
}

const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
const pct = (xs, p) => {
  const t = [...xs].sort((a, b) => a - b);
  return t[Math.min(t.length - 1, Math.floor((p / 100) * t.length))];
};
const pearson = (xs, ys) => {
  const mx = mean(xs), my = mean(ys);
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < xs.length; i++) {
    num += (xs[i] - mx) * (ys[i] - my);
    dx += (xs[i] - mx) ** 2;
    dy += (ys[i] - my) ** 2;
  }
  return num / Math.sqrt(dx * dy);
};

const line = (label, xs) =>
  `${label.padEnd(22)} mean ${mean(xs).toFixed(1).padStart(5)}   ` +
  `5th ${String(pct(xs, 5)).padStart(3)}   25th ${String(pct(xs, 25)).padStart(3)}   ` +
  `median ${String(pct(xs, 50)).padStart(3)}   75th ${String(pct(xs, 75)).padStart(3)}   ` +
  `95th ${String(pct(xs, 95)).padStart(3)}   min ${Math.min(...xs)}   max ${Math.max(...xs)}`;

console.log(`${counts.length} random pairs, seed ${SEED}\n`);
console.log(line("connections per chart", counts));
console.log(line("its own spread (sd)", sds));
console.log(line("settled connections", settled));
console.log("");
for (const [kind, n] of [...byKind].sort((a, b) => b[1] - a[1])) {
  console.log(`  ${kind.padEnd(10)} ${(n / counts.length).toFixed(2)} per pair`);
}
console.log("");
console.log(`correlation, connection count vs Moon score : ${pearson(counts, scores).toFixed(3)}`);
console.log(`correlation, settled count    vs Moon score : ${pearson(settled, scores).toFixed(3)}`);
console.log("");
console.log("Read this before quoting a count on the page: if the spread is narrow, the NUMBER of");
console.log("connections is not a measurement of anything, and only WHICH ones is worth showing.");
