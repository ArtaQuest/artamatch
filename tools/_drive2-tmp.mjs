import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { extname, join } from "node:path";

const DIST = "/Users/arash/Studio/artamatch/dist";
const OUT = "/private/tmp/claude-501/-Users-arash-Studio-artaquest/e237389f-673e-4ad4-a047-ee9f3cdec7b3/scratchpad/shots";
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
await new Promise((r) => server.listen(4401, r));

const dump = async (page) => await page.evaluate(() => {
  const report = document.querySelector(".report");
  const lines = [];
  const walk = (el) => {
    for (const node of el.childNodes) {
      if (node.nodeType === 3) { const t = node.textContent.replace(/\s+/g, " ").trim(); if (t) lines.push(t); }
      else if (node.nodeType === 1) {
        const tag = node.tagName.toLowerCase();
        if (["h2", "h3", "h4"].includes(tag)) { lines.push("", "### " + node.textContent.replace(/\s+/g, " ").trim()); }
        else if (tag === "table") {
          lines.push("[TABLE]");
          for (const tr of node.querySelectorAll("tr")) lines.push("  | " + [...tr.querySelectorAll("th,td")].map((c) => c.textContent.replace(/\s+/g, " ").trim()).join(" | "));
        } else { walk(node); if (["p", "div", "section"].includes(tag)) lines.push(""); }
      }
    }
  };
  walk(report);
  return lines.join("\n").replace(/\n{3,}/g, "\n\n");
});

const browser = await chromium.launch();
for (const w of [390, 1280]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: w === 390 ? 844 : 900 } });
  const page = await ctx.newPage();
  // CERTAIN pair — both Moons stay in one birth star all day.
  await page.goto("http://localhost:4401/artamatch/?n=Mia&b=1990-03-17&n2=Sam&b2=1990-06-09", { waitUntil: "networkidle" });
  await page.waitForSelector(".ruler");
  await page.screenshot({ path: join(OUT, `certain2-${w}.png`), fullPage: true });
  if (w === 1280) writeFileSync(join(OUT, "text-certain2.txt"), await dump(page));
  const g = await page.evaluate(() => {
    const r = document.querySelector(".report").getBoundingClientRect();
    const sec2 = [...document.querySelectorAll(".sec")].find((s) => /How sure/.test(s.textContent));
    return { docHeight: document.documentElement.scrollHeight, reportHeight: Math.round(r.height), sec2Height: Math.round(sec2.getBoundingClientRect().height) };
  });
  console.log(w, JSON.stringify(g));

  // TOGGLE-OFF state — the optional test excluded.
  await page.goto("http://localhost:4401/artamatch/", { waitUntil: "networkidle" });
  await page.locator(".opt input").first().setChecked(false);
  await page.locator(".rank-row").first().click();
  await page.waitForSelector(".ruler");
  await page.screenshot({ path: join(OUT, `toggleoff-${w}.png`), fullPage: true });
  if (w === 1280) writeFileSync(join(OUT, "text-toggleoff.txt"), await dump(page));
  await ctx.close();
}
await browser.close();
server.close();
