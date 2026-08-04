import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { extname, join } from "node:path";

const DIST = "/Users/arash/Studio/artamatch/dist";
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".map": "application/json", ".svg": "image/svg+xml", ".json": "application/json" };
const server = createServer((req, res) => {
  let p = decodeURIComponent(req.url.split("?")[0]).replace(/^\/artamatch/, "");
  if (p === "/" || p === "") p = "/index.html";
  const f = join(DIST, p);
  if (!existsSync(f)) { res.writeHead(404); return res.end("nf"); }
  res.writeHead(200, { "Content-Type": MIME[extname(f)] || "application/octet-stream" });
  res.end(readFileSync(f));
});
await new Promise((r) => server.listen(4406, r));

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();

const probe = async (url, label) => {
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForSelector(".ruler");
  const r = await page.evaluate(() => {
    const rep = document.querySelector(".report");
    const notes = [...rep.querySelectorAll(".sec .note")].map((n) => n.textContent.replace(/\s+/g, " ").slice(0, 60));
    const orderLines = [...rep.querySelectorAll(".kuta .detail")]
      .filter((d) => /Order matters here/.test(d.textContent))
      .map((d) => d.textContent.replace(/\s+/g, " "));
    const moonRows = [...rep.querySelectorAll(".who-panel table.data tr")]
      .filter((tr) => /Moon that day/.test(tr.textContent))
      .map((tr) => tr.textContent.replace(/\s+/g, " "));
    return {
      notes,
      hasPairingNote: notes.some((n) => /Order matters in this pairing/.test(n)),
      orderLines, moonRows,
      sweepPx: [...rep.querySelectorAll(".ruler .sweep")].map((s) => Math.round(s.getBoundingClientRect().width)),
      moonPx: [...rep.querySelectorAll(".ruler .moon")].map((s) => Math.round(s.getBoundingClientRect().width)),
      hereIdx: [...rep.querySelectorAll(".landscape i")].findIndex((i) => i.classList.contains("here")),
      hereTitle: (rep.querySelector(".landscape i.here") || {}).title,
      score: rep.querySelector(".hero .num").textContent,
      sec2: rep.querySelectorAll(".sec")[1].textContent.replace(/\s+/g, " ").slice(0, 120),
    };
  });
  console.log("\n== " + label + " ==");
  console.log(JSON.stringify(r, null, 1));
};

await probe("http://localhost:4406/artamatch/?n=Mia&b=1990-03-17&n2=Sam&b2=1990-06-09", "certain (both stable)");
await probe("http://localhost:4406/artamatch/?n=Ada&b=1815-12-10&n2=Alan&b2=1912-06-23", "Ada/Alan");
await ctx.close();
await browser.close();
server.close();
