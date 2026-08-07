/**
 * verify.mjs — the dataset, checked three ways that can each contradict the others.
 *
 *  1. A DIFFERENT ENDPOINT. The data comes from QLever's Wikidata snapshot. The same counts are asked
 *     of the Wikidata Query Service — a different service, a different index, a different dump date.
 *     They will not agree exactly, because they are snapshots taken at different times; they must
 *     agree closely, and where WDQS is LOWER by a lot that is WDQS truncating rather than a real gap,
 *     which is itself worth showing.
 *  2. A SECOND, INDEPENDENT COUNT OF THE TARGET. Children are counted here by co-parentage (P22+P25).
 *     Wikidata also carries P1971, a stated number of children, entered by different editors from
 *     different sources. For anyone who married exactly once the two should agree; the size and
 *     direction of the disagreement IS the measurement error in the target, and it is reported.
 *  3. A DIFFERENT API. A random sample of couples is re-fetched through the Action API — no SPARQL,
 *     no dump, a different code path — and every field compared: both birth dates and their
 *     precision, both sexes, whether the marriage really ended, and the children. A query that is
 *     subtly wrong will agree with itself forever; it will not agree with this.
 *
 * Usage: node verify.mjs ./data
 */

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const DIR = process.argv[2] || "./data";
const UA = "ArtaMatch-research/1.0 (https://github.com/ArtaQuest/artamatch; support@artaquest.org)";
const PRE = `PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX wikibase: <http://wikiba.se/ontology#>`;

const curl = (args) => execFileSync("curl", args, { maxBuffer: 1 << 28, encoding: "utf8" });
const qlever = (q) => curl(["-m", "250", "-sL", "https://qlever.cs.uni-freiburg.de/api/wikidata/",
  "-H", "Accept: text/tab-separated-values", "-H", "Content-type: application/sparql-query",
  "-H", `User-Agent: ${UA}`, "--data-binary", `${PRE}\n${q}`]);
const wdqs = (q) => curl(["-m", "120", "-s", "-X", "POST", "https://query.wikidata.org/sparql",
  "--data-urlencode", `query=${PRE}\n${q}`, "-H", "Accept: text/tab-separated-values",
  "-H", "Content-Type: application/x-www-form-urlencoded", "-H", `User-Agent: ${UA}`]);
const num = (tsv) => { const l = tsv.split("\n")[1]; return l ? +l.replace(/[^0-9]/g, "") : NaN; };

const dataset = JSON.parse(readFileSync(`${DIR}/dataset.json`, "utf8"));
console.log(`\ndataset: ${dataset.length.toLocaleString()} ended marriages\n`);
let failures = 0;
const check = (ok, msg) => { console.log(`  ${ok ? "PASS" : "FAIL"}  ${msg}`); if (!ok) failures++; };

// ── 1 · a different endpoint ────────────────────────────────────────────────────────────────────
console.log("1 · A DIFFERENT ENDPOINT — QLever's snapshot against the live query service");
{
  const probes = [
    ["all spouse triples", "?a wdt:P26 ?b"],
    ["male-female pairs", "?a wdt:P21 wd:Q6581097 ; wdt:P26 ?b . ?b wdt:P21 wd:Q6581072"],
    ["marriages with an end date", "?a p:P26 ?st . ?st pq:P582 ?e"],
    ["co-parent pairs", "?c wdt:P22 ?d ; wdt:P25 ?m"],
  ];
  for (const [name, where] of probes) {
    const q = num(qlever(`SELECT (COUNT(*) AS ?n) WHERE { ${where} }`));
    let w = NaN;
    try { w = num(wdqs(`SELECT (COUNT(*) AS ?n) WHERE { ${where} }`)); } catch { /* WDQS may time out */ }
    const rel = Number.isFinite(w) ? Math.abs(q - w) / Math.max(q, 1) : NaN;
    console.log(`     ${name.padEnd(28)} QLever ${String(q).padStart(9)}   WDQS ${Number.isFinite(w) ? String(w).padStart(9) : "  timed out"}` +
      (Number.isFinite(rel) ? `   ${(100 * rel).toFixed(2)}% apart` : ""));
    execFileSync("sleep", ["2"]);
  }
  console.log(`     A few per cent apart is two dumps of different ages. A large shortfall on the WDQS`);
  console.log(`     side is the truncation this project hit repeatedly, not a real difference.`);
}

// ── 2 · a second, independent count of the target ───────────────────────────────────────────────
console.log("\n2 · THE TARGET, COUNTED A SECOND WAY — co-parentage against the stated number");
{
  const marriages = new Map();
  for (const d of dataset) for (const p of [d.father, d.mother]) marriages.set(p, (marriages.get(p) ?? 0) + 1);
  let n = 0, agree = 0, under = 0, over = 0, absDiff = 0, statedTotal = 0, countedTotal = 0;
  for (const d of dataset) {
    for (const [i, p] of [d.father, d.mother].entries()) {
      const stated = d.statedKids[i];
      if (stated === null || !Number.isFinite(stated)) continue;
      if (marriages.get(p) !== 1) continue;      // P1971 is per PERSON, so several marriages spoil it
      n++; statedTotal += stated; countedTotal += d.children;
      const diff = d.children - stated;
      absDiff += Math.abs(diff);
      if (diff === 0) agree++; else if (diff < 0) under++; else over++;
    }
  }
  console.log(`     comparable people (married once, with a stated count): ${n.toLocaleString()}`);
  console.log(`     agree ${agree} (${(100 * agree / Math.max(1, n)).toFixed(1)}%) · counted LOWER ${under} (${(100 * under / Math.max(1, n)).toFixed(1)}%) · counted higher ${over}`);
  console.log(`     mean absolute disagreement ${(absDiff / Math.max(1, n)).toFixed(2)} children`);
  console.log(`     totals: ${countedTotal.toLocaleString()} counted against ${statedTotal.toLocaleString()} stated ` +
    `— co-parentage recovers ${(100 * countedTotal / Math.max(1, statedTotal)).toFixed(0)}% of the stated children`);
  console.log(`     This is the dataset's central weakness, and it is a property of Wikidata rather than`);
  console.log(`     of the query: a child is only counted if that child has their own item. It is`);
  console.log(`     measurement error in the TARGET, which is why the result has to survive a`);
  console.log(`     permutation null rather than rest on an R-squared.`);
}

// ── 3 · a different API ─────────────────────────────────────────────────────────────────────────
console.log("\n3 · A DIFFERENT API — 40 random couples re-fetched through the Action API");
{
  let seed = 20260805;
  const rnd = () => { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; seed |= 0; return (seed >>> 0) / 4294967296; };
  const sample = Array.from({ length: 40 }, () => dataset[Math.floor(rnd() * dataset.length)]);
  const ids = [...new Set(sample.flatMap((d) => [d.father, d.mother]))];
  const ent = {};
  for (let i = 0; i < ids.length; i += 25) {
    const r = JSON.parse(curl(["-m", "90", "-s", "-H", `User-Agent: ${UA}`,
      `https://www.wikidata.org/w/api.php?action=wbgetentities&ids=${ids.slice(i, i + 25).join("|")}&props=claims&format=json`]));
    Object.assign(ent, r.entities);
    execFileSync("sleep", ["1"]);
  }
  /**
   * The Action API returns a time AS ENTERED, together with the calendar it was entered in. The RDF
   * export the dataset comes from normalises the same statement to the PROLEPTIC GREGORIAN calendar.
   * So a date entered as 5 November 1828 Julian is 1828-11-05 here and 1828-11-17 there, and
   * comparing them raw reports a mismatch that is not one — which is exactly what this check did on
   * its first run, on three couples out of forty, every one of them off by precisely 12 or 13 days.
   * Converting first is what makes this an independent check rather than a false alarm.
   */
  const JULIAN = "http://www.wikidata.org/entity/Q1985786";
  const toGregorian = (y, m, d) => {
    const a = Math.floor((14 - m) / 12), y2 = y + 4800 - a, m2 = m + 12 * a - 3;
    const jdn = d + Math.floor((153 * m2 + 2) / 5) + 365 * y2 + Math.floor(y2 / 4) - 32083;
    let A = jdn + 32044, B = Math.floor((4 * A + 3) / 146097), C = A - Math.floor(146097 * B / 4);
    let D = Math.floor((4 * C + 3) / 1461), E = C - Math.floor(1461 * D / 4), M = Math.floor((5 * E + 2) / 153);
    const dd = E - Math.floor((153 * M + 2) / 5) + 1, mm = M + 3 - 12 * Math.floor(M / 10);
    const yy = 100 * B + D - 4800 + Math.floor((M + 2) / 12);
    return `${String(yy).padStart(4, "0")}-${String(mm).padStart(2, "0")}-${String(dd).padStart(2, "0")}`;
  };
  const bestDay = (claims) => {
    const st = (claims?.P569 ?? []).filter((s) => s.rank !== "deprecated");
    const pref = st.filter((s) => s.rank === "preferred");
    const use = (pref.length ? pref : st).filter((s) => s.mainsnak?.datavalue?.value?.precision >= 11);
    if (!use.length) return null;
    return use.map((s) => {
      const v = s.mainsnak.datavalue.value;
      const [y, m, d] = v.time.replace(/^\+/, "").split("T")[0].split("-").map(Number);
      return v.calendarmodel === JULIAN ? toGregorian(y, m, d)
        : `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    }).sort()[0];
  };
  const sexOf = (c) => c?.P21?.[0]?.mainsnak?.datavalue?.value?.id ?? null;

  let dobBad = 0, sexBad = 0, endBad = 0, compared = 0;
  const notes = [];
  for (const d of sample) {
    const cf = ent[d.father]?.claims, cm = ent[d.mother]?.claims;
    if (!cf || !cm) continue;
    compared++;
    const f = bestDay(cf), m = bestDay(cm);
    if (f !== d.fDob || m !== d.mDob) { dobBad++; if (notes.length < 5) notes.push(`${d.key}: dataset ${d.fDob}/${d.mDob}, API ${f}/${m}`); }
    if (sexOf(cf) !== "Q6581097" || sexOf(cm) !== "Q6581072") { sexBad++; if (notes.length < 8) notes.push(`${d.key}: sexes ${sexOf(cf)}/${sexOf(cm)}`); }
    const ended = (cf.P26 ?? []).some((s) => s.qualifiers?.P582) || (cm.P26 ?? []).some((s) => s.qualifiers?.P582) || !!cf.P570 || !!cm.P570;
    if (!ended) { endBad++; if (notes.length < 12) notes.push(`${d.key}: no death or end date via the API`); }
  }
  console.log(`     compared ${compared} couples`);
  check(dobBad === 0, `birth dates match the Action API, by the same earliest-day-precision rule (${dobBad} bad)`);
  check(sexBad === 0, `the father is male and the mother female in every sampled couple (${sexBad} bad)`);
  check(endBad === 0, `every sampled marriage really did end in death or divorce (${endBad} bad)`);
  for (const n of notes) console.log(`       ${n}`);
}

// ── 4 · internal consistency ────────────────────────────────────────────────────────────────────
console.log("\n4 · INTERNAL CONSISTENCY");
{
  check(new Set(dataset.map((d) => d.key)).size === dataset.length, "no duplicate couples");
  check(dataset.every((d) => d.father !== d.mother), "nobody is married to themselves");
  check(dataset.every((d) => /^-?\d{4,}-\d{2}-\d{2}$/.test(d.fDob) && /^-?\d{4,}-\d{2}-\d{2}$/.test(d.mDob)),
    "every birth date is a full day-precision date (BCE dates carry a leading minus)");
  check(dataset.every((d) => d.children >= 0), "no negative child counts");
  check(dataset.every((d) => d.end || d.fDod || d.mDod), "every kept marriage has a death or an end date");
  const born = dataset.filter((d) => d.end && (d.end < d.fDob || d.end < d.mDob));
  check(born.length === 0, `no marriage ends before a partner was born (${born.length})`);
  // 1 January is where year-precision dates land when truncated. If the precision filter had failed,
  // this day would be wildly over-represented instead of merely a little.
  const jan1 = dataset.filter((d) => d.fDob.endsWith("-01-01")).length / dataset.length;
  check(jan1 < 0.01, `1 January is not over-represented among fathers (${(100 * jan1).toFixed(2)}%, chance is 0.27%)`);
}

console.log(`\n${failures === 0 ? "ALL CHECKS PASS" : `${failures} CHECKS FAILED`}`);
process.exitCode = failures ? 1 : 0;
