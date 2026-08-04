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
await new Promise((r) => server.listen(4402, r));

const browser = await chromium.launch();
const cases = [
  ["unc", "http://localhost:4402/artamatch/?n=Ayse&b=1999-12-06&n2=Lana&b2=2004-12-21"],
  ["cer", "http://localhost:4402/artamatch/?n=Mia&b=1990-03-17&n2=Sam&b2=1990-06-09"],
];
for (const w of [390, 1280]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: w === 390 ? 844 : 900 } });
  const page = await ctx.newPage();
  for (const [tag, url] of cases) {
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForSelector(".ruler");
    // first screenful, as a visitor sees it
    await page.screenshot({ path: join(OUT, `${tag}-${w}-fold1.png`) });
    await page.evaluate(() => window.scrollTo(0, window.innerHeight));
    await page.screenshot({ path: join(OUT, `${tag}-${w}-fold2.png`) });
    for (const sel of [".hero", ".anatomy", ".ruler-wrap", ".landscape"]) {
      const el = page.locator(sel).first();
      if (await el.count()) await el.screenshot({ path: join(OUT, `${tag}-${w}-${sel.replace(/\W/g, "")}.png`) });
    }
    const secs = page.locator(".sec");
    const n = await secs.count();
    for (let i = 0; i < Math.min(n, 3); i++) {
      await secs.nth(i).screenshot({ path: join(OUT, `${tag}-${w}-sec${i + 1}.png`) });
    }
  }
  await ctx.close();
}
await browser.close();
server.close();
console.log("ok");
