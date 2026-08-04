/** Measure the three instruments in a real browser on the built page. */
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { extname, join } from "node:path";

const DIST = "/Users/arash/Studio/artamatch/dist";
const OUT = "/private/tmp/claude-501/-Users-arash-Studio-artaquest/e237389f-673e-4ad4-a047-ee9f3cdec7b3/scratchpad/instr2";
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".map": "application/json", ".svg": "image/svg+xml", ".json": "application/json" };
const server = createServer((req, res) => {
  let p = decodeURIComponent(req.url.split("?")[0]).replace(/^\/artamatch/, "");
  if (p === "/" || p === "") p = "/index.html";
  const f = join(DIST, p);
  if (!existsSync(f)) { res.writeHead(404); return res.end("nf"); }
  res.writeHead(200, { "Content-Type": MIME[extname(f)] || "application/octet-stream" });
  res.end(readFileSync(f));
});
await new Promise((r) => server.listen(4712, r));

const browser = await chromium.launch();

const measure = () => {
  const out = {};
  const R = (el) => { const r = el.getBoundingClientRect(); return { l: +r.left.toFixed(2), r: +r.right.toFixed(2), w: +r.width.toFixed(2), t: +r.top.toFixed(2), h: +r.height.toFixed(2) }; };

  const ls = document.querySelector(".landscape");
  if (ls) {
    const bars = [...ls.querySelectorAll("i")];
    const here = bars.findIndex((b) => b.classList.contains("here"));
    const lr = ls.getBoundingClientRect();
    const cs = here >= 0 ? getComputedStyle(bars[here], "::after") : null;
    const br = here >= 0 ? bars[here].getBoundingClientRect() : null;
    const lw = cs ? parseFloat(cs.width) || 0 : 0;
    out.landscape = {
      strip: R(ls), barCount: bars.length, hereIndex: here,
      hereTitle: bars[here]?.getAttribute("title"),
      hereHeight: here >= 0 ? +br.height.toFixed(1) : null,
      neighbourHeights: here >= 0 ? bars.slice(Math.max(0, here - 2), here + 3).map((b) => +b.getBoundingClientRect().height.toFixed(1)) : null,
      ariaLabel: ls.getAttribute("aria-label"),
      labelW: lw, labelContent: cs?.content,
      labelLeft: br ? +(br.left + br.width / 2 - lw / 2).toFixed(2) : null,
      labelRight: br ? +(br.left + br.width / 2 + lw / 2).toFixed(2) : null,
      stripLeft: +lr.left.toFixed(2), stripRight: +lr.right.toFixed(2),
      panel: R(document.querySelector(".report")),
      firstTitle: bars[0]?.getAttribute("title"),
      lastTitle: bars[bars.length - 1]?.getAttribute("title"),
    };
  }

  const bar = document.querySelector(".anatomy .bar");
  if (bar) {
    const segs = [...bar.querySelectorAll(".seg")];
    const ws = segs.map((s) => s.getBoundingClientRect().width);
    out.anatomy = {
      barW: +bar.getBoundingClientRect().width.toFixed(2), segCount: segs.length,
      widths: ws.map((w) => +w.toFixed(2)),
      ratiosToFirst: ws.map((w) => +(w / ws[0]).toFixed(3)),
      segs: segs.map((s) => ({
        max: s.querySelector("u")?.textContent,
        earned: s.querySelector("b")?.textContent,
        fillStyle: s.querySelector("i")?.style.width,
        fillPx: +(s.querySelector("i")?.getBoundingClientRect().width ?? 0).toFixed(2),
        fillFrac: +((s.querySelector("i")?.getBoundingClientRect().width ?? 0) / s.getBoundingClientRect().width).toFixed(3),
        earnedInk: (() => {
          const b = s.querySelector("b"); if (!b || !b.textContent) return null;
          const rng = document.createRange(); rng.selectNodeContents(b);
          const ink = rng.getBoundingClientRect(); const sr = s.getBoundingClientRect();
          return { w: +ink.width.toFixed(1), overflows: ink.width > sr.width + 0.5,
                   overlapsMaxLabel: (() => { const u = s.querySelector("u"); if (!u) return false;
                     const ur = u.getBoundingClientRect(); return ur.left < ink.right - 0.5 && ur.right > ink.left + 0.5; })() };
        })(),
        maxInk: (() => { const u = s.querySelector("u"); if (!u) return null;
          const rng = document.createRange(); rng.selectNodeContents(u);
          const ink = rng.getBoundingClientRect(); const sr = s.getBoundingClientRect();
          return { w: +ink.width.toFixed(1), clippedLeft: +(sr.left - ink.left).toFixed(1) }; })(),
      })),
      copy: [...document.querySelectorAll(".sec")][0]?.querySelector(".say")?.textContent.replace(/\s+/g, " ").trim(),
    };
  }

  const ruler = document.querySelector(".ruler");
  if (ruler) {
    const rr = ruler.getBoundingClientRect();
    out.ruler = {
      w: +rr.width.toFixed(2),
      starTicks: ruler.querySelectorAll(".tick.star").length,
      signTicks: ruler.querySelectorAll(".tick.sign").length,
      totalTicks: ruler.querySelectorAll(".tick").length,
      sweeps: [...ruler.querySelectorAll(".sweep")].map((s) => ({
        cls: s.className, left: s.style.left, width: s.style.width,
        title: s.getAttribute("title"),
        pxW: +s.getBoundingClientRect().width.toFixed(2),
        pxL: +(s.getBoundingClientRect().left - rr.left).toFixed(2),
        overRight: +(s.getBoundingClientRect().right - rr.right).toFixed(2),
      })),
      moons: [...ruler.querySelectorAll(".moon")].map((m) => ({
        cls: m.className, left: m.style.left, title: m.getAttribute("title"),
        pxL: +(m.getBoundingClientRect().left - rr.left).toFixed(2),
        pxW: +m.getBoundingClientRect().width.toFixed(2),
        clippedLeft: +(rr.left - m.getBoundingClientRect().left).toFixed(2),
        clippedRight: +(m.getBoundingClientRect().right - rr.right).toFixed(2),
      })),
    };
  }

  out.lede = document.querySelector(".report .lede")?.textContent.replace(/\s+/g, " ").trim();
  out.heroScore = document.querySelector(".report .hero .num")?.textContent.replace(/\s+/g, " ").trim();
  out.because = document.querySelector(".report .because")?.textContent.replace(/\s+/g, " ").trim();
  out.secTitles = [...document.querySelectorAll(".report .sec h3")].map((h) => h.textContent.trim());
  out.docOverflow = document.documentElement.scrollWidth > window.innerWidth + 1;
  return out;
};

const cases = [
  ["hi355-1280", "1977-04-21", "1947-06-18", false, 1280],
  ["hi355-360", "1977-04-21", "1947-06-18", false, 360],
  ["hi345-360", "1977-01-14", "1952-09-21", false, 360],
  ["low3-360", "1990-01-03", "1990-01-18", false, 360],
  ["low3-1280", "1990-01-03", "1990-01-18", false, 1280],
  ["hi355-novarna-360", "1977-04-21", "1947-06-18", true, 360],
  ["wrap1-360", "1990-01-05", "1990-06-12", false, 360],
  ["wrap2-360", "1990-03-28", "1990-07-04", false, 360],
];

const results = {};
for (const [label, da, db, noVarna, width] of cases) {
  const ctx = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") errs.push("console:" + m.text()); });
  await page.goto(`http://localhost:4712/artamatch/?n=Aa&b=${da}&n2=Bb&b2=${db}`, { waitUntil: "networkidle" });
  if (noVarna) {
    await page.locator(".opt input").first().setChecked(false);
    await page.waitForTimeout(120);
  }
  await page.waitForSelector(".ruler");
  await page.waitForTimeout(150);
  results[label] = await page.evaluate(measure);
  results[label].errors = errs;
  await page.screenshot({ path: `${OUT}/${label}.png`, fullPage: true });
  await ctx.close();
}

await browser.close();
server.close();
console.log(JSON.stringify(results, null, 1));
