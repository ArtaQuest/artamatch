/** Find dates whose Moon stays in one birth star all day, by reading the app's own rows. */
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
await new Promise((r) => server.listen(4400, r));

const dates = [];
for (let d = 0; d < 400; d++) {
  const t = new Date(Date.UTC(1990, 0, 1 + d));
  dates.push(t.toISOString().slice(0, 10));
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.goto("http://localhost:4400/artamatch/", { waitUntil: "networkidle" });
await page.evaluate((ds) => {
  localStorage.setItem("artamatch.seeded.v1", "1");
  localStorage.setItem("artamatch.people.v1", JSON.stringify(
    ds.map((b, i) => ({ id: "x" + i, name: "P" + i, birthday: b, source: "manual", addedAt: 1 }))));
}, dates);
await page.reload({ waitUntil: "networkidle" });
const rows = await page.evaluate(() =>
  [...document.querySelectorAll(".person")].map((el) => ({
    txt: el.querySelector(".bd").textContent,
    stable: !el.querySelector(".tm"),
  })));
const stable = rows.map((r, i) => ({ ...r, date: dates[i] })).filter((r) => r.stable);
console.log("stable count", stable.length, "of", rows.length);
console.log(stable.slice(0, 12).map((s) => `${s.date}  ${s.txt}`).join("\n"));
await browser.close();
server.close();
