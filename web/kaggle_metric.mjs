import { chromium } from "playwright";
const SLUG = process.env.AQ_COMPETITION || "artamatch-sidereal";
const log = (m) => console.log("  " + m);
const browser = await chromium.connectOverCDP(process.env.AQ_CDP || "http://127.0.0.1:9222", { timeout: 20000 });
const ctx = browser.contexts()[0]; const page = await ctx.newPage(); page.setDefaultTimeout(25000);
try {
  await page.goto(`https://www.kaggle.com/competitions/${SLUG}/settings/evaluation`, { waitUntil: "commit", timeout: 30000 });
  await page.waitForTimeout(6000);
  await page.mouse.move(900, 600); await page.mouse.wheel(0, 900); await page.waitForTimeout(1200);
  const already = await page.locator("text=Roc Auc Score").count();
  const sel = page.getByRole("button", { name: "Select Metric" });
  if (await sel.count()) {
    await sel.first().click(); await page.waitForTimeout(2500);
    const row = page.locator("tr, [role=row]").filter({ hasText: "Roc Auc Score" }).first();
    await row.locator("input[type=radio], [role=radio], button").first().click(); await page.waitForTimeout(800);
    await page.getByRole("button", { name: /^Select$/ }).last().click(); await page.waitForTimeout(3000);
  } else { log("no 'Select Metric' button (metric may already be set: " + already + " mentions of Roc Auc Score)"); }
  const txt = (await page.locator("body").innerText()).replace(/\s+/g, " ");
  const m = txt.match(/Metric ?(.{0,60}Roc Auc Score[^.]{0,20})/); log("metric now: " + (m ? m[1] : "NOT FOUND") + (txt.includes("Metric updated") ? " · Metric updated" : ""));
} catch (e) { log("ERROR " + String(e).slice(0, 200)); }
finally { await page.close().catch(()=>{}); await browser.close().catch(()=>{}); process.exit(0); }
