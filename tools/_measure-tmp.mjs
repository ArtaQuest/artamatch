import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync, mkdirSync } from "node:fs";
import { extname, join } from "node:path";

const DIST = "/Users/arash/Studio/artamatch/dist";
const OUT = "/private/tmp/claude-501/-Users-arash-Studio-artaquest/e237389f-673e-4ad4-a047-ee9f3cdec7b3/scratchpad/el";
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
await new Promise((r) => server.listen(4403, r));

const browser = await chromium.launch();
for (const w of [390, 1280]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 3 });
  const page = await ctx.newPage();
  await page.goto("http://localhost:4403/artamatch/?n=Ayse&b=1999-12-06&n2=Lana&b2=2004-12-21", { waitUntil: "networkidle" });
  await page.waitForSelector(".ruler");
  await page.locator(".anatomy").first().screenshot({ path: join(OUT, `zoom-anatomy-${w}.png`) });
  await page.locator(".ruler-wrap").first().screenshot({ path: join(OUT, `zoom-ruler-${w}.png`) });
  await page.locator(".landscape").first().screenshot({ path: join(OUT, `zoom-landscape-${w}.png`) });
  const m = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll(".anatomy .seg").forEach((seg, i) => {
      const b = seg.querySelector("b"), u = seg.querySelector("u");
      out.push({
        i: i + 1,
        segW: Math.round(seg.getBoundingClientRect().width),
        earnedText: b.textContent,
        earnedNeeds: Math.round(b.scrollWidth),
        earnedClipped: b.scrollWidth > seg.clientWidth + 0.5,
        maxText: u.textContent,
        maxNeeds: Math.round(u.getBoundingClientRect().width),
      });
    });
    // does the anatomy host scroll horizontally?
    const host = document.querySelector(".anatomy .host");
    return { segs: out, hostScroll: host.scrollWidth > host.clientWidth, hostW: host.clientWidth, barW: host.scrollWidth };
  });
  console.log(w, JSON.stringify(m, null, 1));
  await ctx.close();
}
await browser.close();
server.close();
