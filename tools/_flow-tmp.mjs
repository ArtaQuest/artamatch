import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync, mkdirSync } from "node:fs";
import { extname, join } from "node:path";

const DIST = "/Users/arash/Studio/artamatch/dist";
const OUT = "/private/tmp/claude-501/-Users-arash-Studio-artaquest/e237389f-673e-4ad4-a047-ee9f3cdec7b3/scratchpad/flow";
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
await new Promise((r) => server.listen(4405, r));

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
const page = await ctx.newPage();
await page.goto("http://localhost:4405/artamatch/", { waitUntil: "networkidle" });
const row = page.locator(".rank-row").first();
await row.scrollIntoViewIfNeeded();
await page.screenshot({ path: join(OUT, "01-before-tap.png") });
const before = await page.evaluate(() => window.scrollY);
await row.click();
await page.waitForSelector(".ruler");
const after = await page.evaluate(() => {
  const head = document.querySelector(".report-head");
  const hero = document.querySelector(".hero");
  return {
    scrollY: window.scrollY,
    headTop: Math.round(head.getBoundingClientRect().top),
    heroTop: Math.round(hero.getBoundingClientRect().top),
    docHeight: document.documentElement.scrollHeight,
  };
});
console.log("scrollY before tap:", before, "after:", JSON.stringify(after));
await page.screenshot({ path: join(OUT, "02-after-tap.png") });

// scroll to very bottom of the report and see what the exit looks like
await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
await page.screenshot({ path: join(OUT, "03-bottom.png") });
const bottom = await page.evaluate(() => {
  const btns = [...document.querySelectorAll(".report button, .report a")].map((b) => b.textContent.trim());
  const closeRect = document.querySelector(".report-head .ghost").getBoundingClientRect();
  return { buttons: btns, closeTopFromViewport: Math.round(closeRect.top), scrollY: window.scrollY };
});
console.log("bottom:", JSON.stringify(bottom));

// how many screenfuls to reach section 6
const secTops = await page.evaluate(() => [...document.querySelectorAll(".sec")].map((s) => ({
  t: s.querySelector("h3").textContent.replace(/\s+/g, " "),
  top: Math.round(s.getBoundingClientRect().top + window.scrollY),
})));
console.log("sections:", JSON.stringify(secTops, null, 1));
await ctx.close();
await browser.close();
server.close();
