import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { extname, join } from "node:path";

const DIST = "/Users/arash/Studio/artamatch/dist";
const OUT = "/private/tmp/claude-501/-Users-arash-Studio-artaquest/e237389f-673e-4ad4-a047-ee9f3cdec7b3/scratchpad/txt";
mkdirSync(OUT, { recursive: true });
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".map": "application/json", ".svg": "image/svg+xml", ".json": "application/json" };
const server = createServer((req, res) => {
  let p = decodeURIComponent(req.url.split("?")[0]).replace(/^\/artamatch/, "");
  if (p === "/" || p === "") p = "/index.html";
  const f = join(DIST, p);
  if (!existsSync(f)) { res.writeHead(404); return res.end("nf"); }
  res.writeHead(200, { "Content-Type": MIME[extname(f)] || "application/octet-stream" });
  res.end(readFileSync(f));
});
await new Promise((r) => server.listen(4404, r));

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();
await page.goto("http://localhost:4404/artamatch/", { waitUntil: "networkidle" });
await page.locator(".opt input").first().setChecked(false);
await page.locator(".rank-row").first().click();
await page.waitForSelector(".ruler");
const top = await page.evaluate(() => {
  const r = document.querySelector(".report");
  const grab = (s) => (r.querySelector(s) || {}).textContent || "";
  return {
    hero: grab(".hero").replace(/\s+/g, " "),
    lede: grab(".lede").replace(/\s+/g, " "),
    sec1: r.querySelectorAll(".sec")[0].textContent.replace(/\s+/g, " ").slice(0, 400),
    sec4title: [...r.querySelectorAll(".sec h3")].map((h) => h.textContent.replace(/\s+/g, " ")),
    note: [...r.querySelectorAll(".panel-note")].map((n) => n.textContent.replace(/\s+/g, " ")),
    segCount: r.querySelectorAll(".anatomy .seg").length,
    landscapeBars: r.querySelectorAll(".landscape i").length,
    landscapeHere: [...r.querySelectorAll(".landscape i")].findIndex((i) => i.classList.contains("here")),
    hereTitle: (r.querySelector(".landscape i.here") || {}).title,
    allTitles: [...r.querySelectorAll(".landscape i")].slice(0, 6).map((i) => i.title),
  };
});
writeFileSync(join(OUT, "toggleoff.json"), JSON.stringify(top, null, 2));
console.log(JSON.stringify(top, null, 2));
await page.screenshot({ path: join(OUT, "toggleoff-top.png"), clip: { x: 400, y: 150, width: 830, height: 750 } });
await ctx.close();
await browser.close();
server.close();
