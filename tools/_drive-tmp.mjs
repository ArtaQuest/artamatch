/**
 * drive.mjs — fresh-eyes UX driver. Serves dist/, drives the report at 390 and 1280,
 * screenshots, and dumps the full document text with scroll offsets.
 */
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { extname, join } from "node:path";

const DIST = "/Users/arash/Studio/artamatch/dist";
const OUT = process.argv[2] || "/private/tmp/claude-501/-Users-arash-Studio-artaquest/e237389f-673e-4ad4-a047-ee9f3cdec7b3/scratchpad/shots";
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
await new Promise((r) => server.listen(4399, r));

const browser = await chromium.launch();
const BASE = "http://localhost:4399/artamatch/";

async function shot(page, tag, w) {
  await page.screenshot({ path: join(OUT, `${tag}-${w}.png`), fullPage: true });
  const geom = await page.evaluate(() => {
    const doc = document.documentElement;
    const out = { docHeight: doc.scrollHeight, viewport: window.innerHeight, blocks: [] };
    const report = document.querySelector(".report");
    if (report) {
      out.reportTop = report.getBoundingClientRect().top + window.scrollY;
      out.reportHeight = report.getBoundingClientRect().height;
      for (const el of report.querySelectorAll(".hero, .lede, .sec, .row.actions, .panel-note")) {
        const r = el.getBoundingClientRect();
        const h = el.querySelector("h3");
        out.blocks.push({
          cls: el.className,
          label: h ? h.textContent.trim() : el.textContent.trim().slice(0, 60),
          top: Math.round(r.top + window.scrollY),
          height: Math.round(r.height),
        });
      }
    }
    return out;
  });
  return geom;
}

async function textDump(page) {
  return await page.evaluate(() => {
    const report = document.querySelector(".report");
    if (!report) return "NO REPORT";
    const lines = [];
    const walk = (el, depth) => {
      for (const node of el.childNodes) {
        if (node.nodeType === 3) {
          const t = node.textContent.replace(/\s+/g, " ").trim();
          if (t) lines.push("  ".repeat(depth) + t);
        } else if (node.nodeType === 1) {
          const tag = node.tagName.toLowerCase();
          if (["h3", "h4", "h2"].includes(tag)) {
            lines.push("");
            lines.push("### " + node.textContent.replace(/\s+/g, " ").trim());
          } else if (tag === "table") {
            lines.push("[TABLE]");
            for (const tr of node.querySelectorAll("tr")) {
              lines.push("  | " + [...tr.querySelectorAll("th,td")].map((c) => c.textContent.replace(/\s+/g, " ").trim()).join(" | "));
            }
          } else if (["p", "div", "section", "span", "button", "li"].includes(tag)) {
            walk(node, depth);
            if (["p", "div", "section"].includes(tag)) lines.push("");
          } else {
            walk(node, depth);
          }
        }
      }
    };
    walk(report, 0);
    return lines.join("\n").replace(/\n{3,}/g, "\n\n");
  });
}

const results = {};

for (const w of [390, 1280]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: w === 390 ? 844 : 900 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [];
  page.on("console", (m) => m.type() === "error" && errs.push(m.text()));
  page.on("pageerror", (e) => errs.push(String(e)));

  // ── uncertain branch: default seed pair ────────────────────────────────
  await page.goto(BASE, { waitUntil: "networkidle" });
  await shot(page, "home", w);
  await page.locator(".rank-row").first().click();
  await page.waitForSelector(".ruler");
  results[`uncertain-${w}`] = await shot(page, "report-uncertain", w);
  if (w === 1280) writeFileSync(join(OUT, "text-uncertain.txt"), await textDump(page));

  // ── certain branch ──────────────────────────────────────────────────────
  await page.goto(BASE + "?n=Ada&b=1815-12-10&n2=Alan&b2=1912-06-23", { waitUntil: "networkidle" });
  await page.waitForSelector(".ruler");
  results[`certain-${w}`] = await shot(page, "report-certain", w);
  if (w === 1280) writeFileSync(join(OUT, "text-certain.txt"), await textDump(page));

  results[`errors-${w}`] = errs;
  await ctx.close();
}

writeFileSync(join(OUT, "geom.json"), JSON.stringify(results, null, 2));
console.log(JSON.stringify(results, null, 2));
await browser.close();
server.close();
