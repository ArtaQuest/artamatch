// ziwei_batch.mjs — Zi Wei Dou Shu (紫微斗数) astrolabes in bulk through iztro, read from stdin as JSON lines.
// Input line:  {"id": "...", "date": "YYYY-MM-DD", "timeIndex": 5}      timeIndex 5 = 巳时 09:00-11:00
// Output line: {"id": ..., "ok": true, "soul": ..., "body": ..., "fiveElementsClass": ..., "soulBranch": ...,
//               "palaces": [{"name":..., "branch":..., "major":[{"name","brightness","mutagen"}], "minor":[...], "adj":[...]}]}
// The sex parameter only steers the decadal-limit direction; the dataset reads no sex, so it is fixed and stated.
import { astro } from "iztro";
import readline from "node:readline";
const rl = readline.createInterface({ input: process.stdin });
for await (const line of rl) {
  if (!line.trim()) continue;
  const q = JSON.parse(line);
  try {
    const a = astro.bySolar(q.date, q.timeIndex ?? 5, "male", true, "en-US");
    const palaces = a.palaces.map(p => ({
      name: p.name, branch: p.earthlyBranch, stem: p.heavenlyStem, isBody: !!p.isBodyPalace,
      major: p.majorStars.map(s => ({ name: s.name, brightness: s.brightness || "", mutagen: s.mutagen || "" })),
      minor: p.minorStars.map(s => ({ name: s.name, brightness: s.brightness || "", mutagen: s.mutagen || "" })),
      adj: p.adjectiveStars.map(s => s.name),
    }));
    process.stdout.write(JSON.stringify({ id: q.id, ok: true, soul: a.soul, body: a.body,
      fiveElementsClass: a.fiveElementsClass, soulBranch: a.earthlyBranchOfSoulPalace,
      bodyBranch: a.earthlyBranchOfBodyPalace, palaces }) + "\n");
  } catch (e) {
    process.stdout.write(JSON.stringify({ id: q.id, ok: false, error: String(e).slice(0, 120) }) + "\n");
  }
}
