/** a11y probe: keyboard order, focus survival, accessible names. */
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
await new Promise((r) => server.listen(4399, r));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 950 } });
const URL0 = "http://localhost:4399/artamatch/";
await page.goto(URL0, { waitUntil: "networkidle" });

const desc = () => page.evaluate(() => {
  const e = document.activeElement;
  if (!e || e === document.body) return "BODY";
  return `${e.tagName.toLowerCase()}${e.className ? "." + String(e.className).trim().split(/\s+/).join(".") : ""} :: "${(e.getAttribute("aria-label") || e.textContent || "").trim().slice(0, 55)}"`;
});

async function tabOrder(n = 40) {
  await page.evaluate(() => document.body.focus?.());
  await page.evaluate(() => { document.activeElement?.blur?.(); });
  const out = [];
  for (let i = 0; i < n; i++) {
    await page.keyboard.press("Tab");
    const d = await desc();
    out.push(d);
    if (d === "BODY") break;
  }
  return out;
}

console.log("=== TAB ORDER, home ===");
(await tabOrder(30)).forEach((d, i) => console.log(String(i + 1).padStart(2) + " " + d));

// --- focus after opening a report from the keyboard
console.log("\n=== keyboard: open report from a rank row ===");
await page.goto(URL0, { waitUntil: "networkidle" });
await page.locator(".rank-row").first().focus();
console.log("before Enter, focus =", await desc());
await page.keyboard.press("Enter");
await page.waitForSelector(".ruler");
console.log("after Enter,  focus =", await desc());
console.log("report present =", await page.locator(".report").count());
console.log("next Tab lands on   =", (await page.keyboard.press("Tab"), await desc()));

console.log("\n=== keyboard: close the report ===");
await page.locator(".report-head button").first().focus();
console.log("before Enter, focus =", await desc());
await page.keyboard.press("Enter");
await page.waitForTimeout(120);
console.log("after close,  focus =", await desc());
console.log("next Tab lands on   =", (await page.keyboard.press("Tab"), await desc()));

// --- self selection semantics
console.log("\n=== people list: 'who am I' buttons ===");
await page.goto(URL0, { waitUntil: "networkidle" });
console.log(await page.evaluate(() => Array.from(document.querySelectorAll(".person")).map((row) => {
  const b = row.querySelector("button.who");
  return { selectedVisually: row.classList.contains("is-self"), ariaPressed: b.getAttribute("aria-pressed"), ariaCurrent: b.getAttribute("aria-current"), role: b.getAttribute("role"), name: b.textContent.trim().slice(0, 40) };
})));

// --- app tabs
console.log("\n=== app tabs ===");
console.log(await page.evaluate(() => {
  const list = document.querySelector('[role="tablist"]');
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  return {
    tablistAttrs: list ? Object.fromEntries(Array.from(list.attributes).map((a) => [a.name, a.value])) : null,
    tabs: tabs.map((t) => ({ name: t.textContent.trim(), ariaSelected: t.getAttribute("aria-selected"), ariaControls: t.getAttribute("aria-controls"), tabindex: t.getAttribute("tabindex") })),
    tabpanels: document.querySelectorAll('[role="tabpanel"]').length,
  };
}));
// arrow key behaviour
await page.locator('[role="tab"]').first().focus();
await page.keyboard.press("ArrowRight");
console.log("after ArrowRight on tab 1, focus =", await desc());
console.log("selected view still =", await page.evaluate(() => document.querySelector(".tabs button.on")?.textContent.trim()));

// --- form error announcement
console.log("\n=== form error ===");
await page.goto(URL0, { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Add to my list" }).focus();
await page.keyboard.press("Enter");
await page.waitForTimeout(100);
console.log(await page.evaluate(() => {
  const e = document.querySelector(".error");
  if (!e) return "no error shown";
  return { text: e.textContent.trim(), role: e.getAttribute("role"), ariaLive: e.getAttribute("aria-live"), id: e.id,
    inputDescribedBy: document.querySelector("#nm")?.getAttribute("aria-describedby"),
    inputInvalid: document.querySelector("#nm")?.getAttribute("aria-invalid"),
    focusAfter: document.activeElement?.textContent?.trim().slice(0, 30) };
}));

// --- matrix
console.log("\n=== matrix table ===");
await page.goto(URL0, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /Everyone vs everyone/i }).click();
await page.waitForSelector("table.data");
console.log(await page.evaluate(() => {
  const ths = Array.from(document.querySelectorAll("table.data th"));
  const cellBtns = Array.from(document.querySelectorAll(".matrix-cell .link"));
  return {
    thScopes: ths.map((t) => ({ text: t.textContent.trim().slice(0, 12), scope: t.getAttribute("scope") })),
    tableCaption: !!document.querySelector("table.data caption"),
    firstCellButtonText: cellBtns[0]?.textContent.trim(),
    firstCellButtonTitle: cellBtns[0]?.getAttribute("title"),
    firstCellAriaLabel: cellBtns[0]?.getAttribute("aria-label"),
  };
}));
const cell = page.locator(".matrix-cell .link").first();
console.log("matrix cell accessible name via AX =", JSON.stringify((await page.accessibility.snapshot({ root: await cell.elementHandle() }))));

// --- report AX tree of the actions row + headings
console.log("\n=== report: headings + action links ===");
await page.goto(URL0, { waitUntil: "networkidle" });
await page.locator(".rank-row").first().click();
await page.waitForSelector(".ruler");
console.log("headings:", await page.evaluate(() => Array.from(document.querySelectorAll("h1,h2,h3,h4")).map((h) => h.tagName + " " + h.textContent.trim().slice(0, 42))));
console.log("landmarks main =", await page.evaluate(() => document.querySelectorAll("main, [role=main]").length));
console.log("nested a>button =", await page.evaluate(() => document.querySelectorAll("a button").length));
console.log("hero markup:", await page.evaluate(() => document.querySelector(".hero")?.innerHTML.slice(0, 400)));

// --- anatomy legibility: which segments have their number over the dark track?
console.log("\n=== anatomy segment label placement ===");
console.log(await page.evaluate(() => Array.from(document.querySelectorAll(".anatomy .seg")).map((s) => {
  const fill = s.querySelector("i"), b = s.querySelector("b"), u = s.querySelector("u");
  const sw = s.getBoundingClientRect().width, fw = fill.getBoundingClientRect().width;
  const br = b.getBoundingClientRect(), ur = u.getBoundingClientRect(), sr = s.getBoundingClientRect();
  return { title: s.getAttribute("title").slice(0, 34), segW: +sw.toFixed(0), fillW: +fw.toFixed(0),
    earned: b.textContent, avail: u.textContent,
    earnedCentreOverFill: (br.left + br.width / 2 - sr.left) < fw,
    availOverFill: (ur.left + ur.width / 2 - sr.left) < fw };
})));

// --- MoonRuler / Anatomy AX
console.log("\n=== instruments AX ===");
console.log(await page.evaluate(() => ({
  landscapeRole: document.querySelector(".landscape")?.getAttribute("role"),
  landscapeLabel: document.querySelector(".landscape")?.getAttribute("aria-label"),
  anatomyRole: document.querySelector(".anatomy")?.getAttribute("role"),
  anatomyLabel: document.querySelector(".anatomy")?.getAttribute("aria-label"),
  rulerRole: document.querySelector(".ruler")?.getAttribute("role"),
  rulerLabel: document.querySelector(".ruler")?.getAttribute("aria-label"),
  meterRole: document.querySelector(".meter")?.getAttribute("role"),
})));

// --- focus ring clipping in scroll containers
console.log("\n=== focus visibility inside scroll containers ===");
await page.goto(URL0, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /Everyone vs everyone/i }).click();
await page.waitForSelector("table.data");
const last = page.locator(".matrix-cell .link").last();
await last.focus();
console.log(await page.evaluate(() => {
  const el = document.activeElement;
  const sc = el.closest(".scroll-x");
  const er = el.getBoundingClientRect(), sr = sc.getBoundingClientRect();
  const cs = getComputedStyle(sc);
  return { overflowX: cs.overflowX, overflowY: cs.overflowY,
    elBottom: +er.bottom.toFixed(1), containerBottom: +sr.bottom.toFixed(1),
    clippedBy: +(er.bottom + 4 - sr.bottom).toFixed(1) };
}));

await browser.close();
server.close();
