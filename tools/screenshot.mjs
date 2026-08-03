import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFileSync, existsSync } from 'node:fs';
import { extname, join } from 'node:path';

const DIST = process.argv[2], OUT = process.argv[3];
const MIME = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.map':'application/json','.svg':'image/svg+xml'};
const server = createServer((req,res)=>{
  let p = decodeURIComponent(req.url.split('?')[0]).replace(/^\/artamatch/,'');
  if (p==='/'||p==='') p='/index.html';
  const f = join(DIST,p);
  if (!existsSync(f)) { res.writeHead(404); return res.end('nf'); }
  res.writeHead(200,{'Content-Type':MIME[extname(f)]||'application/octet-stream'});
  res.end(readFileSync(f));
});
await new Promise(r=>server.listen(4321,r));

const browser = await chromium.launch();
const errors = [];
async function shot(name, width, height, fn) {
  const ctx = await browser.newContext({viewport:{width,height}, deviceScaleFactor:2});
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type()==='error') errors.push(`[${name}] ${m.text()}`); });
  page.on('pageerror', e => errors.push(`[${name}] PAGEERROR ${e.message}`));
  await page.goto('http://localhost:4321/artamatch/', {waitUntil:'networkidle'});
  if (fn) await fn(page);
  await page.screenshot({path:`${OUT}/${name}.png`, fullPage:true});
  // Overflow check: nothing should push the document wider than the viewport.
  const ow = await page.evaluate(()=>document.documentElement.scrollWidth);
  const vw = await page.evaluate(()=>window.innerWidth);
  if (ow > vw + 1) errors.push(`[${name}] HORIZONTAL OVERFLOW: doc ${ow}px > viewport ${vw}px`);
  // Meter sanity: every meter must be a thin bar, not a block.
  const bad = await page.evaluate(()=>[...document.querySelectorAll('.meter')].filter(m=>m.getBoundingClientRect().height>12).length);
  if (bad) errors.push(`[${name}] ${bad} meter(s) taller than 12px — the inline-span bug is back`);
  await ctx.close();
  console.log('shot', name);
}

await shot('1-home-desktop', 1280, 900);
await shot('2-report-desktop', 1280, 900, async p => {
  await p.locator('.rank-row').first().click();
  await p.waitForSelector('.hero');
});
await shot('3-report-tests', 1280, 900, async p => {
  await p.locator('.rank-row').first().click();
  await p.getByRole('tab', {name:/eight tests/i}).click();
});
await shot('4-report-aspects', 1280, 900, async p => {
  await p.locator('.rank-row').first().click();
  await p.getByRole('tab', {name:/runs between/i}).click();
});
await shot('5-mobile-home', 390, 844);
await shot('6-mobile-report', 390, 844, async p => {
  await p.locator('.rank-row').first().click();
  await p.waitForSelector('.hero');
});

await browser.close(); server.close();
console.log(errors.length ? '\nPROBLEMS:\n'+errors.join('\n') : '\nno console errors, no overflow, meters OK');
