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
// Port 0 lets the OS pick a free one. A fixed port meant two audits could not run at once — and
// they do, whenever a reviewer is driving the page while CI or a developer runs this.
await new Promise((r) => server.listen(0, r));
const PORT = server.address().port;
const ORIGIN = `http://localhost:${PORT}/artamatch/`;

const browser = await chromium.launch();
const errors = [];

const VIEWPORTS = [
  ["m360", 360, 780], ["m390", 390, 844], ["t768", 768, 1024], ["d1280", 1280, 900], ["d1600", 1600, 900],
];

// Each state: a name and a driver that gets the page there from a fresh load. The report is ONE
// document now, so there are no report tabs to drive — a single scroll covers the whole reading.
const STATES = [
  // Wait for the ceiling scan to finish rather than photographing its progress bar: the finished
  // panel is the state with the numbers, the histogram and the layout worth auditing.
  ["home", async (p) => { await p.waitForSelector(".ceiling .hist", { timeout: 30000 }); }],
  ["report", async (p) => { await p.locator(".rank-row").first().click(); await p.waitForSelector(".anatomy"); }],
  ["matrix", async (p) => { await p.getByRole("button", { name: /Everyone vs everyone/i }).click(); }],
  ["toggle-off", async (p) => {
    await p.locator(".opt input").first().setChecked(false);
    await p.locator(".rank-row").first().click();
    await p.waitForSelector(".anatomy");
  }],
  // A pair whose dates settle the answer outright — the OTHER branch of section 2. Found by
  // search: both Moons stay in one birth star and one sign all day, which is rare enough that
  // the earlier hand-picked pair did not qualify and this branch went unrendered for a while.
  ["certain", async (p) => {
    await p.goto(`${ORIGIN}?n=Certain%20A&b=1984-02-08&n2=Certain%20B&b2=1967-08-26`,
      { waitUntil: "networkidle" });
    await p.waitForSelector(".anatomy");
  }],
  // The extremes of the score range, where the landscape strip's "this pair" label sits hard
  // against an edge and could clip.
  ["lowest", async (p) => {
    await p.goto(`${ORIGIN}?n=Low%20A&b=2004-09-23&n2=Low%20B&b2=1990-08-20`,
      { waitUntil: "networkidle" });
    await p.waitForSelector(".anatomy");
  }],
  ["highest", async (p) => {
    await p.goto(`${ORIGIN}?n=High%20A&b=1983-09-01&n2=High%20B&b2=1969-03-23`,
      { waitUntil: "networkidle" });
    await p.waitForSelector(".anatomy");
  }],
];

async function audit(page, tag) {
  const problems = await page.evaluate(() => {
    const out = [];
    // `html { overflow-x: hidden }` clamps documentElement.scrollWidth to the viewport, so the
    // obvious check could never fire — this gate was decorative for its whole life. Measure the
    // body (not clamped), and also walk for any element whose box genuinely exceeds the viewport.
    if (document.body.scrollWidth > window.innerWidth + 1) {
      out.push(`HORIZONTAL OVERFLOW: body ${document.body.scrollWidth}px > viewport ${window.innerWidth}px`);
    }
    // Inside a deliberate horizontal scroller, a wide box is the point, not a bug. Detected from
    // the COMPUTED overflow rather than a hardcoded class list — the list silently stopped covering
    // everything the moment a new scroller was added, and reported the new chart as broken.
    const inScroller = (el) => {
      for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
        const ox = getComputedStyle(n).overflowX;
        if (ox === "auto" || ox === "scroll") return true;
      }
      return false;
    };
    for (const el of document.querySelectorAll("body *")) {
      const r = el.getBoundingClientRect();
      if (r.width === 0) continue;
      if (inScroller(el)) continue;
      if (r.right > window.innerWidth + 2 || r.left < -2) {
        out.push(`overflows viewport: <${el.tagName.toLowerCase()} class="${el.className}"> ` +
          `left ${Math.round(r.left)} right ${Math.round(r.right)} vs ${window.innerWidth}`);
        break; // one report per state is enough to act on
      }
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
    // The three instruments must be present and complete wherever the report is.
    if (document.querySelector(".report")) {
      const segs = document.querySelectorAll(".anatomy .seg").length;
      if (segs < 7) out.push(`anatomy bar has ${segs} blocks, expected 7 or 8`);
      const here = document.querySelector(".landscape .here");
      if (!here) out.push("landscape strip does not mark this pair");
      else {
        // The "this pair" label is absolutely positioned and centred on its bar; at the extremes
        // it can run past the strip. Compare against the page, not the strip, since a little
        // overhang inside the panel is fine but off-screen is not.
        const lab = getComputedStyle(here, "::after");
        const r = here.getBoundingClientRect();
        const approx = parseFloat(lab.width) || 52;
        if (r.left + r.width / 2 - approx / 2 < 0) out.push("landscape label clips off the left edge");
        if (r.left + r.width / 2 + approx / 2 > window.innerWidth) out.push("landscape label clips off the right edge");
      }
    }

    // A name showing under 70px of itself has lost its column — layout failure, not typography.
    for (const nm of document.querySelectorAll(".person .nm")) {
      if (nm.scrollWidth > nm.clientWidth + 2 && nm.clientWidth < 70) {
        out.push(`name column collapsed to ${Math.round(nm.clientWidth)}px ("${nm.textContent.trim().slice(0, 16)}")`);
      }
    }

    // SHEARED TEXT. A label clipped by its own box is worse than a missing one when it is a
    // number: "0.5" sheared to "0" is a WRONG figure, not an absent one, and that shipped once.
    // Any short label in a fixed-width box is checked, at every width.
    for (const el of document.querySelectorAll(".anatomy .seg b, .anatomy .seg u, .band .chip, .band .cell")) {
      if (getComputedStyle(el).display === "none") continue;
      if (el.scrollWidth > el.clientWidth + 1) {
        out.push(`text sheared by its box: <${el.tagName.toLowerCase()} class="${el.className}"> ` +
          `"${el.textContent.trim()}" needs ${el.scrollWidth}px, has ${el.clientWidth}`);
      }
    }

    // THE CHART. Its whole job is to put a planet where the planet was, and the lane packing is
    // the only thing stopping two labels from sitting on top of each other. Both are checked in
    // the rendered DOM rather than trusted from the arithmetic that produced it.
    for (const band of document.querySelectorAll(".band")) {
      const chips = [...band.querySelectorAll(".chip")].map((c) => {
        const r = c.getBoundingClientRect();
        return { r, name: c.textContent.trim() };
      });
      for (let i = 0; i < chips.length; i++) {
        for (let j = i + 1; j < chips.length; j++) {
          const a = chips[i].r, b = chips[j].r;
          if (a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1) {
            out.push(`chart labels overlap: "${chips[i].name}" and "${chips[j].name}"`);
          }
        }
      }
      const bandBox = band.getBoundingClientRect();
      for (const { r, name } of chips) {
        if (r.left < bandBox.left - 1 || r.right > bandBox.right + 1) {
          out.push(`chart label "${name}" hangs off the band`);
        }
      }
    }
    if (document.querySelector(".report")) {
      const bands = document.querySelectorAll(".band");
      if (bands.length !== 3) out.push(`report has ${bands.length} charts, expected 3`);
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
    await page.goto(ORIGIN, { waitUntil: "networkidle" });
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
