/**
 * contrast.mjs — WCAG contrast for every ink/surface pair the stylesheet actually uses.
 *
 * The brand allows two hues and no third accent, so the only lever here is LIGHTNESS. This script
 * exists because contrast is arithmetic: it should be computed and asserted, never eyeballed.
 * Exits non-zero if any ink falls under 4.5:1 on the surface it is used against.
 *
 *   node tools/contrast.mjs
 */
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
const token = (n) => {
  const m = css.match(new RegExp(`--${n}:\\s*(#[0-9a-fA-F]{6})`));
  if (!m) throw new Error(`token --${n} not found`);
  return m[1];
};

const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const lum = (h) => { const [r, g, b] = rgb(h).map(lin); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const ratio = (a, b) => {
  const [x, y] = [lum(a), lum(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
};

// The darkest surface any of these inks sits on — the worst case, so passing here passes everywhere.
const WORST = token("panel-2");
const INKS = ["text", "muted", "dim", "yang", "link"];
const FILLS = [["yin", "button"], ["yin-lift", "button hover"]];

let failed = 0;
console.log(`inks against the darkest surface ${WORST} (need 4.5:1)`);
for (const n of INKS) {
  const r = ratio(token(n), WORST);
  const ok = r >= 4.5;
  if (!ok) failed++;
  console.log(`  --${n.padEnd(6)} ${token(n)}  ${r.toFixed(2)}  ${ok ? "pass" : "FAIL"}`);
}
console.log(`\nwhite on the filled surfaces (need 4.5:1)`);
for (const [n, what] of FILLS) {
  const r = ratio("#ffffff", token(n));
  const ok = r >= 4.5;
  if (!ok) failed++;
  console.log(`  ${what.padEnd(12)} ${token(n)}  ${r.toFixed(2)}  ${ok ? "pass" : "FAIL"}`);
}
console.log(failed ? `\n${failed} FAILING` : "\nall pass");
process.exitCode = failed ? 1 : 0;
