// browser_verify.mjs — load the shipped page in a real browser and assert the numbers were PAINTED.
//
// It launches Chrome itself, drives it over the DevTools protocol and POLLS until the precision grid has rows.
// No npm dependency: Node's global WebSocket does the protocol and the GitHub runner already has Chrome. That
// matters for isolation — this repository publishes a static page and should not need a package.json to prove
// the page works.
//
// WHY POLLING AND NOT A SNAPSHOT. The obvious approach, `chrome --headless --dump-dom --virtual-time-budget`,
// returns this page with every statistic still showing its "—" placeholder and an empty grid: the snapshot is
// taken before the CDN fetch of Pyodide, numpy and astropy resolves. It reports a broken page for a working
// one, which is worse than no check at all, because the natural response is to go and "fix" the page.
//
// Usage:  node web/browser_verify.mjs <url> [chrome-binary]
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const URL_ = process.argv[2] || "http://127.0.0.1:8891/index.html";
const CANDIDATES = [
  process.argv[3], process.env.CHROME,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
].filter(Boolean);
const PORT = 9222 + (process.pid % 500);
const DEADLINE_MS = Number(process.env.VERIFY_TIMEOUT_MS || 300000);
const LEVELS = ["full", "month", "year", "absent"];

const sleep = ms => new Promise(r => setTimeout(r, ms));
const profile = mkdtempSync(join(tmpdir(), "aqchrome-"));

let child = null;
for (const bin of CANDIDATES) {
  try {
    child = spawn(bin, ["--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
      "--no-default-browser-check", "--disable-dev-shm-usage",
      `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, "about:blank"],
      { stdio: "ignore" });
    await sleep(1200);
    if (child.exitCode === null) { console.log(`  browser: ${bin}`); break; }
  } catch { /* try the next candidate */ }
  child = null;
}
if (!child) {
  console.error(`  no Chrome found; tried ${CANDIDATES.join(", ")}`);
  process.exit(2);
}

function done(code) {
  try { child.kill("SIGKILL"); } catch {}
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
  process.exit(code);
}

async function firstPage() {
  for (let i = 0; i < 80; i++) {
    try {
      const j = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = j.find(t => t.type === "page");
      if (p?.webSocketDebuggerUrl) return p;
    } catch { /* not listening yet */ }
    await sleep(500);
  }
  throw new Error("Chrome never exposed a page target");
}

const page = await firstPage();
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let id = 0;
const pending = new Map();
const errors = [];
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  if (m.method === "Runtime.exceptionThrown") {
    errors.push(m.params?.exceptionDetails?.exception?.description || m.params?.exceptionDetails?.text || "?");
  } else if (m.method === "Log.entryAdded" && m.params?.entry?.level === "error") {
    errors.push("console: " + String(m.params.entry.text || "").slice(0, 180));
  }
};
const send = (method, params = {}) => {
  const n = ++id;
  ws.send(JSON.stringify({ id: n, method, params }));
  return new Promise(res => pending.set(n, res));
};
async function ev(expression) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  return r.result?.result?.value;
}

await send("Runtime.enable");
await send("Log.enable");
await send("Page.enable");
await send("Page.navigate", { url: URL_ });

const t0 = Date.now();
let rows = 0;
while (Date.now() - t0 < DEADLINE_MS) {
  rows = (await ev(`document.querySelectorAll("#grid-tab tbody tr").length`)) || 0;
  if (rows > 0) break;
  const status = String((await ev(`(document.querySelector("#log")||{}).textContent||""`)) || "").slice(0, 70);
  process.stdout.write(`\r  waiting ${((Date.now() - t0) / 1000) | 0}s — ${status.padEnd(72)}`);
  await sleep(2000);
}
process.stdout.write("\r" + " ".repeat(100) + "\r");

const out = await ev(`(() => {
  const t = id => (document.getElementById(id) || {}).textContent || "(missing)";
  const tab = document.querySelector("#grid-tab");
  return {
    title: document.title,
    stats: { auc: t("s-auc"), clean: t("s-clean"), base: t("s-base"), lift: t("s-lift"), n: t("s-n") },
    grid: tab ? Array.from(tab.querySelectorAll("tr")).map(
      r => Array.from(r.querySelectorAll("th,td")).map(c => c.textContent.trim())) : [],
    note: t("grid-note"),
    detail: document.querySelectorAll("#grid-detail tbody tr").length,
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
  };
})()`) || {};

const grid = out.grid || [];
const body = grid.slice(1).flatMap(r => r.slice(1));
// Count what a cell IS rather than which glyph it uses for "empty": comparing against a literal em dash once
// failed a page whose blank cell was rendered exactly as intended.
const numeric = body.filter(c => /^0\.\d+$/.test(c)).length;

console.log(`  title  : ${out.title}`);
console.log(`  stats  : benchmark=${out.stats?.auc}  full|full=${out.stats?.clean}  ` +
            `reference=${out.stats?.base}  lift=${out.stats?.lift}  n=${out.stats?.n}`);
for (const r of grid) console.log("   " + r.map(c => String(c).padStart(11)).join(" |"));
console.log(`  note   : ${String(out.note || "").slice(0, 200)}`);

const checks = [
  ["the grid rendered 4 data rows + a header", grid.length === 5],
  ["16 body cells: 15 numeric and 1 blank", body.length === 16 && numeric === 15],
  ["the per-cell detail table filled all 15 rows", out.detail === 15],
  ["the headline statistic is a number, not a placeholder", /^0\.\d+$/.test(out.stats?.auc || "")],
  ["the axis header names the man first", (grid[0] || []).join(" ").includes("man")],
  ["every precision level is labelled", LEVELS.every(() =>
    (grid[0] || []).join(" ").match(/full|month|year|no date/))],
  ["the page does not scroll sideways", out.overflow === false],
  ["no console or runtime errors", errors.length === 0],
];
console.log("");
let ok = true;
for (const [label, pass] of checks) {
  console.log(`  [${pass ? "OK " : "FAIL"}] ${label}`);
  ok &&= pass;
}
if (errors.length) for (const e of errors.slice(0, 5)) console.log("     " + String(e).split("\n")[0].slice(0, 150));
console.log(ok ? "\n  the published page renders its own measurements" : "\n  the page is not publishable");
done(ok ? 0 : 1);
