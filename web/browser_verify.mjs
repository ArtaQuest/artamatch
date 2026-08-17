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
  // SURFACE THE EXCEPTION. This returned undefined on a throw, so a syntax or runtime error inside an evaluated
  // block came back looking like "the page has no such element" and every assertion downstream failed with
  // `undefined` instead of naming the actual fault.
  const exc = r.result?.exceptionDetails;
  if (exc) {
    const d = exc.exception?.description || exc.text || JSON.stringify(exc);
    console.error(`  !! evaluate threw: ${String(d).split("\n")[0].slice(0, 200)}`);
    evalErrors.push(d);
  }
  return r.result?.result?.value;
}
const evalErrors = [];

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

// THE POINT OF THE WIDER RANGE: a modern pair must come back with a real probability, and the answer must say
// it is an extrapolation. Refusing it was the bug; answering it silently would be the next one.
const modernScore = await ev(`(async () => {
  const setY = (sel, v) => { const y = document.querySelector(sel).querySelector(".dy");
    y.value = String(v); y.dispatchEvent(new Event("input", { bubbles: true })); };
  setY("#a-dob", 1994); setY("#b-dob", 1998);
  document.querySelector("#go-pair").click();
  for (let i = 0; i < 90; i++) {
    const big = document.querySelector("#pair-out .big");
    if (big && /%/.test(big.textContent)) {
      return { pct: big.textContent.trim(),
               warned: /extrapolat/i.test(document.querySelector("#pair-out").textContent || "") };
    }
    await new Promise(r => setTimeout(r, 1000));
  }
  return { pct: null, warned: false, text: (document.querySelector("#pair-out") || {}).textContent || "" };
})()`) || {};
console.log(`  1994x1998 : scored ${modernScore.pct || "(nothing)"}, ` +
            `extrapolation warning ${modernScore.warned ? "shown" : "MISSING"}`);

// A PHONE-WIDTH PASS. Every check above ran at the default headless size, so a control that took three
// full-width rows per date — pushing the button off the screen — passed all of them. Layout is measured here,
// not eyeballed: the date control must occupy ONE row, nothing may spill its parent except the tables that are
// deliberately inside an overflow-x container, and the body must not scroll sideways.
await send("Emulation.setDeviceMetricsOverride",
  { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
await sleep(900);
const phone = await ev(`(() => {
  const host = document.querySelector("#a-dob");
  const parts = host ? Array.from(host.children).map(el => el.getBoundingClientRect()) : [];
  // Cluster tops with a tolerance. An <input> and a <select> can differ by a pixel inside the SAME grid row,
  // and counting exact tops reported a correct one-row layout as two rows.
  const sorted = parts.map(b => b.top).sort((x, y) => x - y);
  const tops = new Set();
  for (const t of sorted) {
    if (![...tops].some(u => Math.abs(u - t) <= 6)) tops.add(t);
  }
  const spill = [];
  for (const el of document.querySelectorAll("body *")) {
    const b = el.getBoundingClientRect();
    if (!b.width && !b.height) continue;
    // Anything inside a deliberate horizontal-scroll container is allowed to be wider than the viewport.
    if (el.closest(".scroll")) continue;
    const p = el.parentElement && el.parentElement.getBoundingClientRect();
    if (p && b.right - p.right > 1) spill.push((el.id ? "#" + el.id : el.tagName.toLowerCase())
      + " by " + Math.round(b.right - p.right) + "px");
  }
  const btn = document.querySelector("#go-pair");
  const why = document.querySelector("#pair-window");
  return { viewport: document.documentElement.clientWidth,
           scrollW: document.documentElement.scrollWidth,
           parts: parts.length, rows: tops.size,
           // The decisive measure: one row means the control is no taller than its tallest part.
           hostH: host ? Math.round(host.getBoundingClientRect().height) : 0,
           partH: parts.length ? Math.round(Math.max(...parts.map(b => b.height))) : 0,
           controlW: parts.length ? Math.round(parts.reduce((a, b) => a + b.width, 0)) : 0,
           spill: spill.slice(0, 8), spillTotal: spill.length,
           // The reason a disabled button is disabled has to be on screen with it.
           whyVisible: !!(why && why.getBoundingClientRect().height > 0),
           whyBelowBtn: !!(btn && why && why.getBoundingClientRect().top >= btn.getBoundingClientRect().top),
           gapPx: (btn && why) ? Math.round(why.getBoundingClientRect().top - btn.getBoundingClientRect().bottom) : -1,
           // CLIPPED TEXT IS INVISIBLE TO EVERY OTHER CHECK. A select whose widest option does not fit renders
           // its value truncated — "15" as "1" plus the arrow — while the DOM value stays correct, the element
           // does not overflow its parent and the page does not scroll. The day column was 34px of text room
           // against 45px of need at every width, and it read as a control that would not select.
           clipped: (() => {
             const bad = [];
             const cv = document.createElement("canvas").getContext("2d");
             for (const el of document.querySelectorAll("input, select, button")) {
               const cs = getComputedStyle(el);
               const avail = el.getBoundingClientRect().width
                 - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)
                 - parseFloat(cs.borderLeftWidth) - parseFloat(cs.borderRightWidth);
               cv.font = cs.font;
               let need = 0, txt = "";
               if (el.tagName === "SELECT") {
                 for (const o of el.options) {
                   const w = cv.measureText(o.textContent).width;
                   if (w > need) { need = w; txt = o.textContent; }
                 }
                 need += 18;                       // the arrow the browser draws inside the box
               } else {
                 txt = el.value || el.textContent || "";
                 need = cv.measureText(txt).width + (el.type === "number" ? 4 : 0);
               }
               if (need > avail + 0.5) {
                 // No backticks and no escaped quotes. This code is inside a template literal, so a backtick
                 // closes it AND a backslash escape is consumed by the literal before Chrome sees it — the
                 // string " \"" arrives as " "" and is a syntax error. Plain concatenation, no quote chars.
                 bad.push((el.id ? "#" + el.id : el.tagName.toLowerCase()) + " [" +
                          txt.slice(0, 10) + "] needs " + Math.round(need) + " has " + Math.round(avail));
               }
             }
             return bad.slice(0, 6);
           })(),
           // A button that is usable must not LOOK unusable, and one that is unusable must say so.
           btnDisabled: !!(btn && btn.disabled),
           btnCursor: btn ? getComputedStyle(btn).cursor : "",
           btnOpacity: btn ? getComputedStyle(btn).opacity : "" };
})()`) || {};
console.log(`  phone     : ${phone.viewport}px viewport, date control ${phone.parts} parts on ` +
            `${phone.rows} row(s) totalling ${phone.controlW}px; ${phone.spillTotal} element(s) spilling, ` +
            `${(phone.clipped || []).length} clipping their text`);
if ((phone.clipped || []).length) console.log(`              ${phone.clipped.join("; ")}`);
if (phone.spillTotal) console.log(`              ${(phone.spill || []).join(", ")}`);
await send("Emulation.clearDeviceMetricsOverride");
await sleep(400);

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
  // Move BOTH years together. Setting one alone leaves the pair decades apart and trips the 60-year rule, so
  // the page's correct refusal reads as a failure of the thing actually being tested.
  const y2 = document.querySelector("#b-dob").querySelector(".dy");
  const type = v => {
    y.value = String(v); y.dispatchEvent(new Event("input", { bubbles: true }));
    y2.value = String(Number(v) + 4); y2.dispatchEvent(new Event("input", { bubbles: true }));
    return { year: Number(y.value), other: Number(y2.value),
             note: (document.querySelector("#pair-window") || {}).textContent || "",
             disabled: !!(document.querySelector("#go-pair") || {}).disabled }; };
  const modern = type("1994");        // answerable, and extrapolation
  const future = type("2200");        // not a birth date
  const fitted = type(String(min + 89));
  return { min, max, modern, future, fitted };
})()`) || {};
console.log(`  range     : year input min=${clamp.min} max=${clamp.max}`);
console.log(`  1994      : kept as ${clamp.modern?.year}, button ${clamp.modern?.disabled ? "disabled" : "enabled"}`);
console.log(`              ${String(clamp.modern?.note || "").slice(0, 108)}`);
console.log(`  2200      : became ${clamp.future?.year}`);

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

// Read the bounds off the inputs instead of restating them. Hardcoding 1800-1950 here failed the moment the
// computable range widened to the present, reporting a stale expectation as a page defect.
const fLo = Number(String(finder.min || "1600-01-01").slice(0, 4));
const fHi = Number(String(finder.max || "2026-12-31").slice(0, 4));
const inWin = v => /^(\d{4})-/.test(v || "")
                   && Number(String(v).slice(0, 4)) >= fLo && Number(String(v).slice(0, 4)) <= fHi;

const checks = [
  ["the search inputs stay inside the computable range",
   inWin(finder.self) && inWin(finder.from) && inWin(finder.to),
   `${finder.self} / ${finder.from} / ${finder.to} against ${fLo}-${fHi}`],
  ["the computable range reaches the present, not only the fitted years",
   clamp.min === 1600 && clamp.max >= 2026, `min=${clamp.min} max=${clamp.max}`],
  ["a modern year is accepted rather than refused",
   clamp.modern?.year === 1994 && clamp.modern?.disabled === false, `1994 -> ${clamp.modern?.year}`],
  ["and it is labelled as an extrapolation",
   /extrapolat/i.test(clamp.modern?.note || ""), clamp.modern?.note?.slice(0, 70)],
  ["a year in the future is still pulled back",
   (clamp.future?.year || 9999) <= clamp.max, `2200 -> ${clamp.future?.year}`],
  ["a year inside the fitted range is not warned about",
   !/extrapolat/i.test(clamp.fitted?.note || ""), clamp.fitted?.note?.slice(0, 70)],
  ["a modern pair actually returns a probability", /%$/.test(modernScore.pct || ""),
   modernScore.pct || String(modernScore.text || "").slice(0, 90)],
  ["and the answer itself says it is an extrapolation", modernScore.warned === true],
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
  // Two of the sixteen combinations are not scored — absent|absent has no input at all, month|month is a case
  // the records essentially never present — so the matrix must show fourteen numbers and two blanks.
  ["16 body cells: 14 numeric and 2 blank", body.length === 16 && numeric === 14,
   `${numeric} numeric, ${body.length - numeric} blank`],
  ["the per-cell detail table filled all 14 rows", out.detail === 14, `${out.detail} rows`],
  ["the headline statistic is a number, not a placeholder", /^0\.\d+$/.test(out.stats?.auc || "")],
  ["the axis header names the man first", (grid[0] || []).join(" ").includes("man")],
  ["every precision level is labelled", LEVELS.every(() =>
    (grid[0] || []).join(" ").match(/full|month|year|no date/))],
  ["the page does not scroll sideways", out.overflow === false],
  ["at 390px the date control is a single row",
   phone.rows === 1 && phone.hostH > 0 && phone.hostH <= phone.partH + 8,
   `${phone.rows} row(s), control ${phone.hostH}px vs tallest part ${phone.partH}px`],
  ["at 390px it fits the viewport", phone.controlW > 0 && phone.controlW <= phone.viewport,
   `${phone.controlW}px in ${phone.viewport}px`],
  ["at 390px nothing spills its container outside a scroll region", phone.spillTotal === 0,
   (phone.spill || []).join(", ")],
  ["at 390px the body still does not scroll sideways", phone.scrollW <= phone.viewport + 1,
   `scrollWidth ${phone.scrollW} vs ${phone.viewport}`],
  ["the reason a pair cannot be scored sits right under the button",
   phone.whyVisible && phone.whyBelowBtn && phone.gapPx >= 0 && phone.gapPx < 40, `gap ${phone.gapPx}px`],
  ["no control clips its own text at 390px", (phone.clipped || []).length === 0,
   (phone.clipped || []).join("; ")],
  ["an enabled button looks enabled", phone.btnDisabled || (phone.btnCursor === "pointer"
    && Number(phone.btnOpacity) >= 0.9), `cursor ${phone.btnCursor}, opacity ${phone.btnOpacity}`],
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
