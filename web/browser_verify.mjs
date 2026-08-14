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

// spawn() reports a missing binary as an ASYNCHRONOUS 'error' event, not a synchronous throw, so a
// try/catch around it catches nothing: the first candidate here is a macOS path, and on Linux it took the
// whole process down with an unhandled 'error' before the loop could try google-chrome. Resolve on the
// event instead, and treat an immediate exit as a failure too.
function launch(bin) {
  const args = ["--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
    "--no-default-browser-check", "--disable-dev-shm-usage",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, "about:blank"];
  return new Promise(resolve => {
    let c;
    try { c = spawn(bin, args, { stdio: "ignore" }); } catch { return resolve(null); }
    let settled = false;
    const fail = () => { if (!settled) { settled = true; resolve(null); } };
    c.once("error", fail);
    c.once("exit", fail);
    setTimeout(() => { if (!settled) { settled = true; resolve(c); } }, 1500);
  });
}

let child = null;
const tried = [];
for (const bin of CANDIDATES) {
  tried.push(bin);
  child = await launch(bin);
  if (child) { console.log(`  browser: ${bin}`); break; }
}
if (!child) {
  console.error(`  no usable Chrome; tried ${tried.join(", ")}`);
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
    // The tradition table rendered ZERO rows on a shipped build: it was keyed on a tradition_auc field the
    // exporter had stopped writing, and an empty object is a perfectly good object. A whole section of the
    // page was blank and every other check still passed. (No backticks in here: this comment lives inside a
    // template literal, and the first one closes it.)
    trads: Array.from(document.querySelectorAll("#trad-tab tbody tr")).map(r => ({
      title: (r.querySelector("summary b") || {}).textContent || "",
      body: (r.querySelector("details p") || {}).textContent || "",
      blocks: r.querySelectorAll(".blocklist li").length,
      worked: Array.from(r.querySelectorAll(".worked li"))
        .map(li => li.textContent.trim()).filter(t => t && !/^computing/.test(t)),
      auc: (r.querySelectorAll("td")[1] || {}).textContent || "",
    })),
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

const tr = out.trads || [];
const described = tr.filter(t => t.title.length > 3 && t.body.length > 40 && t.blocks > 0);
console.log(`  traditions : ${tr.length} rows, ${described.length} with a title, an explanation and their blocks`);
for (const t of tr.slice(0, 3)) {
  console.log(`     ${t.auc.padStart(7)}  ${t.title}  (${t.blocks} blocks)`);
  for (const w of (t.worked || []).slice(0, 2)) console.log(`              ${w.slice(0, 96)}`);
}

// TYPE AN OUT-OF-WINDOW YEAR AND SEE WHAT THE PAGE DOES. `min`/`max` on a number input are advisory: 1994 can
// be typed straight past them, and a browser restoring form state from an earlier visit ignores them entirely.
// The page must pull the value back inside the window and refuse to offer a score it cannot give.
const clamp = await ev(`(() => {
  const host = document.querySelector("#a-dob");
  const y = host && host.querySelector(".dy");
  if (!y) return { ok: false, why: "no year input" };
  const min = Number(y.min), max = Number(y.max);
  y.value = "1994";
  y.dispatchEvent(new Event("input", { bubbles: true }));
  const after = y.value;
  const btn = document.querySelector("#go-pair");
  const note = (document.querySelector("#pair-window") || {}).textContent || "";
  return { min, max, after: Number(after), disabled: !!(btn && btn.disabled), note: note.slice(0, 120) };
})()`) || {};
console.log(`  clamping  : year input min=${clamp.min} max=${clamp.max}; typed 1994 became ${clamp.after}`);
console.log(`  notice    : ${clamp.note}`);

// The search inputs are `type="date"`, whose min/max are equally advisory. The old page scanned 5,114 dates and
// THEN reported that none of them could be scored — all of the work and none of the answer.
const finder = await ev(`(() => {
  const set = (id, v) => {
    const el = document.querySelector(id);
    if (!el) return null;
    el.value = v;
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return el.value;
  };
  return {
    self: set("#f-self", "1994-02-15"),
    from: set("#f-from", "1994-01-01"),
    to: set("#f-to", "2008-01-01"),
    min: (document.querySelector("#f-from") || {}).min,
    max: (document.querySelector("#f-to") || {}).max,
  };
})()`) || {};
console.log(`  search    : 1994-02-15/1994-01-01/2008-01-01 became ` +
            `${finder.self}/${finder.from}/${finder.to}  (min ${finder.min}, max ${finder.max})`);

const inWin = v => /^(\d{4})-/.test(v || "") && Number(String(v).slice(0, 4)) >= 1800
                   && Number(String(v).slice(0, 4)) <= 1950;

const checks = [
  ["the search inputs are clamped into the window too",
   inWin(finder.self) && inWin(finder.from) && inWin(finder.to),
   `${finder.self} / ${finder.from} / ${finder.to}`],
  ["the year input carries the model's window, not a hardcoded one",
   clamp.min === 1800 && clamp.max === 1950, `min=${clamp.min} max=${clamp.max}`],
  ["typing a year outside the window is pulled back inside it",
   clamp.after >= clamp.min && clamp.after <= clamp.max, `1994 stayed ${clamp.after}`],
  ["the page states the window next to the control", /\d{4}/.test(clamp.note || "")],
  ["the grid rendered 4 data rows + a header", grid.length === 5],
  ["the tradition table is not empty", tr.length > 0],
  ["every tradition is explained and lists its blocks", tr.length > 0 && described.length === tr.length,
   `${tr.length - described.length} row(s) missing a title, an explanation or their blocks`],
  ["every tradition shows a numeric AUC", tr.length > 0 && tr.every(t => /^0\.\d+$/.test(t.auc.trim()))],
  ["every tradition has a worked example computed for the pair on screen",
   tr.length > 0 && tr.every(t => (t.worked || []).length > 0),
   `${tr.filter(t => !(t.worked || []).length).length} of ${tr.length} rows have none`],
  ["the worked examples contain real numbers, not just prose",
   tr.length > 0 && tr.every(t => (t.worked || []).some(x => /\d/.test(x)))],
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
for (const [label, pass, detail] of checks) {
  console.log(`  [${pass ? "OK " : "FAIL"}] ${label}${!pass && detail ? "  — " + detail : ""}`);
  ok &&= pass;
}
if (errors.length) for (const e of errors.slice(0, 5)) console.log("     " + String(e).split("\n")[0].slice(0, 150));
console.log(ok ? "\n  the published page renders its own measurements" : "\n  the page is not publishable");
done(ok ? 0 : 1);
