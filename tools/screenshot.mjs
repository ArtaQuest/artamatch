/**
 * screenshot.mjs — the visual audit. Serves dist/, drives a real browser through every state at
 * five widths, screenshots each, and asserts the layout invariants that have actually broken:
 *
 *   · no horizontal overflow anywhere (the classic mobile failure)
 *   · no console or page errors
 *   · meters stay thin bars (an inline-span bug once made them full-height blocks)
 *   · people rows stay rows (a flex-sibling bug once squeezed names to "Ar…" and stacked the
 *     date word-by-word — a broken row is TALL, so height is the tell)
 *   · every real button keeps a usable tap target
 *
 * Usage: node tools/screenshot.mjs <distDir> <outDir>   — exits non-zero on any problem.
 */

import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { extname, join } from "node:path";

const DIST = process.argv[2], OUT = process.argv[3];
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".map": "application/json", ".svg": "image/svg+xml", ".json": "application/json" };
const server = createServer((req, res) => {
  let p = decodeURIComponent(req.url.split("?")[0]).replace(/^\/artamatch/, "");
  if (p === "/" || p === "") p = "/index.html";
  const f = join(DIST, p);
  if (!existsSync(f)) { res.writeHead(404); return res.end("nf"); }
  res.writeHead(200, { "Content-Type": MIME[extname(f)] || "application/octet-stream" });
  res.end(readFileSync(f));
});
await new Promise((r) => server.listen(4321, r));

const browser = await chromium.launch();
const errors = [];

const VIEWPORTS = [
  ["m360", 360, 780], ["m390", 390, 844], ["t768", 768, 1024], ["d1280", 1280, 900], ["d1600", 1600, 900],
];

// Each state: a name and a driver that gets the page there from a fresh load.
const STATES = [
  ["home", async () => {}],
  ["report", async (p) => { await p.locator(".rank-row").first().click(); await p.waitForSelector(".hero"); }],
  ["tests", async (p) => {
    await p.locator(".rank-row").first().click();
    await p.getByRole("tab", { name: /eight tests/i }).click();
    await p.waitForSelector(".ruler");
  }],
  ["between", async (p) => {
    await p.locator(".rank-row").first().click();
    await p.getByRole("tab", { name: /runs between/i }).click();
  }],
  ["where", async (p) => {
    await p.locator(".rank-row").first().click();
    await p.getByRole("tab", { name: /Where everything/i }).click();
  }],
  ["matrix", async (p) => { await p.getByRole("tab", { name: /Everyone vs everyone/i }).click(); }],
  ["toggle-off", async (p) => {
    await p.locator(".opt input").first().setChecked(false);
    await p.locator(".rank-row").first().click();
    await p.waitForSelector(".hero");
  }],
];

async function audit(page, tag) {
  const problems = await page.evaluate(() => {
    const out = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) {
      out.push(`HORIZONTAL OVERFLOW: doc ${doc.scrollWidth}px > viewport ${window.innerWidth}px`);
    }
    for (const m of document.querySelectorAll(".meter")) {
      const h = m.getBoundingClientRect().height;
      if (h > 12) out.push(`meter ${Math.round(h)}px tall — the inline-span bug is back`);
    }
    for (const row of document.querySelectorAll(".person")) {
      const h = row.getBoundingClientRect().height;
      if (h > 88) out.push(`person row ${Math.round(h)}px tall — the squeezed-column bug is back (${row.textContent.slice(0, 40)})`);
    }
    for (const b of document.querySelectorAll("button")) {
      const r = b.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue; // hidden state
      if (r.height < 26 || r.width < 26) {
        out.push(`tap target ${Math.round(r.width)}x${Math.round(r.height)}px: "${(b.textContent || b.getAttribute("aria-label") || "?").trim().slice(0, 24)}"`);
      }
    }
    // A name showing under 70px of itself has lost its column — layout failure, not typography.
    for (const nm of document.querySelectorAll(".person .nm")) {
      if (nm.scrollWidth > nm.clientWidth + 2 && nm.clientWidth < 70) {
        out.push(`name column collapsed to ${Math.round(nm.clientWidth)}px ("${nm.textContent.trim().slice(0, 16)}")`);
      }
    }
    return out;
  });
  for (const p of problems) errors.push(`[${tag}] ${p}`);
}

for (const [vname, width, height] of VIEWPORTS) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 2 });
  for (const [sname, drive] of STATES) {
    const page = await ctx.newPage();
    page.on("console", (m) => { if (m.type() === "error") errors.push(`[${vname}/${sname}] console: ${m.text()}`); });
    page.on("pageerror", (e) => errors.push(`[${vname}/${sname}] PAGEERROR ${e.message}`));
    await page.goto("http://localhost:4321/artamatch/", { waitUntil: "networkidle" });
    try {
      await drive(page);
    } catch (e) {
      errors.push(`[${vname}/${sname}] drive failed: ${String(e).split("\n")[0]}`);
    }
    await page.waitForTimeout(120);
    await page.screenshot({ path: `${OUT}/${vname}-${sname}.png`, fullPage: true });
    await audit(page, `${vname}/${sname}`);
    await page.close();
  }
  await ctx.close();
}

await browser.close();
server.close();
console.log(`${VIEWPORTS.length * STATES.length} shots taken`);
console.log(errors.length ? `\nPROBLEMS (${errors.length}):\n` + errors.join("\n") : "\nall states clean at all widths");
if (errors.length) process.exitCode = 1;
