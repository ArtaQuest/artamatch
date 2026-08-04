import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { extname, join } from "node:path";
const DIST = "/Users/arash/Studio/artamatch/dist";
const MIME = { ".html":"text/html", ".js":"text/javascript", ".css":"text/css", ".map":"application/json", ".svg":"image/svg+xml", ".json":"application/json" };
const server = createServer((req,res)=>{ let p=decodeURIComponent(req.url.split("?")[0]).replace(/^\/artamatch/,""); if(p==="/"||p==="")p="/index.html"; const f=join(DIST,p); if(!existsSync(f)){res.writeHead(404);return res.end("nf");} res.writeHead(200,{"Content-Type":MIME[extname(f)]||"application/octet-stream"}); res.end(readFileSync(f)); });
await new Promise(r=>server.listen(4400,r));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport:{width:1280,height:950} });
const U="http://localhost:4400/artamatch/";
const desc = () => page.evaluate(()=>{const e=document.activeElement; if(!e||e===document.body)return "BODY"; return `${e.tagName.toLowerCase()}${e.className?"."+String(e.className).trim().split(/\s+/).join("."):""} :: "${(e.getAttribute("aria-label")||e.textContent||"").trim().slice(0,50)}"`;});

console.log("=== form error announcement ===");
await page.goto(U,{waitUntil:"networkidle"});
await page.getByRole("button",{name:"Add to my list"}).focus();
await page.keyboard.press("Enter");
await page.waitForTimeout(120);
console.log(await page.evaluate(()=>{ const e=document.querySelector(".error"); if(!e) return "no error"; return { text:e.textContent.trim(), role:e.getAttribute("role"), ariaLive:e.getAttribute("aria-live"),
  nmDescribedBy:document.querySelector("#nm")?.getAttribute("aria-describedby"), nmInvalid:document.querySelector("#nm")?.getAttribute("aria-invalid"),
  activeEl:document.activeElement?.textContent?.trim().slice(0,25) };}));

console.log("\n=== matrix table ===");
await page.goto(U,{waitUntil:"networkidle"});
await page.getByRole("button",{name:/Everyone vs everyone/i}).click();
await page.waitForSelector("table.data");
console.log(await page.evaluate(()=>{ const ths=[...document.querySelectorAll("table.data th")]; const b=document.querySelector(".matrix-cell .link");
  return { thScopes: ths.map(t=>({t:t.textContent.trim().slice(0,12),scope:t.getAttribute("scope")})), caption:!!document.querySelector("table.data caption"),
    cellText:b?.textContent.trim(), cellTitle:b?.getAttribute("title"), cellAriaLabel:b?.getAttribute("aria-label") };}));


console.log("tab order in matrix view:");
await page.evaluate(()=>document.activeElement?.blur?.());
for (let i=0;i<26;i++){ await page.keyboard.press("Tab"); const d=await desc(); console.log("  "+(i+1)+" "+d); if(d==="BODY")break; }

console.log("\n=== report ===");
await page.goto(U,{waitUntil:"networkidle"});
await page.locator(".rank-row").first().click();
await page.waitForSelector(".ruler");
console.log("headings:", await page.evaluate(()=>[...document.querySelectorAll("h1,h2,h3,h4")].map(h=>h.tagName+" "+h.textContent.trim().slice(0,44))));
console.log("main landmarks =", await page.evaluate(()=>document.querySelectorAll("main,[role=main]").length));
console.log("a>button count =", await page.evaluate(()=>document.querySelectorAll("a button").length));
console.log("report tab order:");
await page.evaluate(()=>document.activeElement?.blur?.());
for (let i=0;i<30;i++){ await page.keyboard.press("Tab"); const d=await desc(); console.log("  "+(i+1)+" "+d); if(d==="BODY")break; }

console.log("\n=== a>button AX ===");
await page.goto(U+"?n=Ada&b=1815-12-10&n2=Alan&b2=1912-06-23",{waitUntil:"networkidle"});
console.log(await page.evaluate(()=>[...document.querySelectorAll("a")].map(a=>({href:a.getAttribute("href")?.slice(0,50), html:a.innerHTML.slice(0,80)}))));

console.log("\n=== anatomy label placement ===");
await page.goto(U,{waitUntil:"networkidle"});
await page.locator(".rank-row").first().click();
await page.waitForSelector(".anatomy");
console.log(await page.evaluate(()=>[...document.querySelectorAll(".anatomy .seg")].map(s=>{
  const fill=s.querySelector("i"), b=s.querySelector("b"), u=s.querySelector("u");
  const sr=s.getBoundingClientRect(), fw=fill.getBoundingClientRect().width;
  const br=b.getBoundingClientRect(), ur=u.getBoundingClientRect();
  return { test:s.getAttribute("title").split("—")[0].trim().slice(0,26), segW:+sr.width.toFixed(0), fillW:+fw.toFixed(0),
    earned:b.textContent, avail:u.textContent,
    earnedOnGold: (br.left+br.width/2-sr.left) < fw, availOnGold: (ur.left+ur.width/2-sr.left) < fw };})));

console.log("\n=== instruments AX ===");
console.log(await page.evaluate(()=>({ landscape:[document.querySelector(".landscape")?.getAttribute("role"),document.querySelector(".landscape")?.getAttribute("aria-label")],
  anatomy:[document.querySelector(".anatomy")?.getAttribute("role"),document.querySelector(".anatomy")?.getAttribute("aria-label")],
  ruler:[document.querySelector(".ruler")?.getAttribute("role"),document.querySelector(".ruler")?.getAttribute("aria-label")],
  meter:document.querySelector(".meter")?.getAttribute("role") })));

console.log("\n=== focus ring clipping (matrix scroll-x) ===");
await page.goto(U,{waitUntil:"networkidle"});
await page.getByRole("button",{name:/Everyone vs everyone/i}).click();
await page.waitForSelector("table.data");
await page.locator(".matrix-cell .link").last().focus();
console.log(await page.evaluate(()=>{ const el=document.activeElement, sc=el.closest(".scroll-x"); const er=el.getBoundingClientRect(), sr=sc.getBoundingClientRect(); const cs=getComputedStyle(sc);
  return { overflowX:cs.overflowX, overflowY:cs.overflowY, elBottom:+er.bottom.toFixed(1), containerBottom:+sr.bottom.toFixed(1), ringOutsideBy:+(er.bottom+4-sr.bottom).toFixed(1) };}));

console.log("\n=== zoom / reflow 320px and 400% ===");
await page.setViewportSize({width:320,height:800});
await page.goto(U,{waitUntil:"networkidle"});
console.log("h-overflow @320:", await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth));
await browser.close(); server.close();
