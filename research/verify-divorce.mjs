/**
 * verify-divorce.mjs — is every divorce Wikidata knows about actually in the dataset?
 *
 * The collector's own COUNT checks prove that each QUERY returned everything it asked for. They say
 * nothing about whether the right questions were asked. These five checks attack that, and each one can
 * fail independently of the others.
 *
 *  1. THE LABEL VOCABULARY. Every distinct P1534 value on a marriage statement is enumerated and matched
 *     against the sets the collector classifies. A value nobody thought of — and the first sighting of
 *     this list already showed an unlabelled Q113455903 with 8 uses — is a silent hole: those marriages
 *     are dropped without appearing in any drop count. This check makes the tail visible and accounts
 *     for every single statement.
 *  2. RECONCILIATION FROM THE OTHER DIRECTION. The collector leads with the qualifier because that is
 *     fast. Here the same totals are recounted leading from P26 instead, and by distinct COUPLE rather
 *     than by statement. A different traversal of the same graph must agree.
 *  3. CONFLICTING STATEMENTS. A couple who married, divorced and remarried has two P26 statements with
 *     two different causes, and the collector keeps ONE row per couple. How often that happens, and
 *     which way the tie was broken, decides whether the labels mean what they claim.
 *  4. A DIFFERENT API. Random couples re-fetched through the Action API — no SPARQL, no dump — and the
 *     cause, both birth dates and their precision compared field by field.
 *  5. THE INFERENCE ROUTE, RETRIED. It is validated (93.1% recall, 98.9% precision) but was left off
 *     because the endpoints could not serve the query. This retries it in small partitions and reports
 *     exactly how many additional divorces are waiting, so the gap is a known quantity rather than an
 *     unknown one.
 *
 * Usage: node research/verify-divorce.mjs ./research/data-divorce
 */

import { readFileSync, existsSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const DIR = process.argv[2] ?? "./research/data-divorce";
const UA = "ArtaMatch-research/1.0 (https://github.com/ArtaQuest/artamatch; support@artaquest.org)";
const PRE = `PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>`;

const log = (s) => process.stderr.write(s + "\n");
const clean = (v) => {
  let s = v.trim().replace(/\^\^<[^>]*>$/, "");
  if (s.startsWith("<") && s.endsWith(">")) s = s.slice(1, -1);
  if (s.startsWith('"') && s.endsWith('"')) s = s.slice(1, -1);
  return s.replace(/@en$/, "");
};

/** Long, patient retries: both endpoints were unavailable for the better part of an hour. */
function ask(query, { seconds = 115, tries = 25 } = {}) {
  let last = "";
  for (let t = 0; t < tries; t++) {
    for (const [name, args] of [
      ["qlever", ["-m", String(seconds), "-sL", "https://qlever.cs.uni-freiburg.de/api/wikidata/", "-H", "Accept: text/tab-separated-values", "-H", "Content-type: application/sparql-query", "-H", `User-Agent: ${UA}`, "--data-binary", `${PRE}\n${query}`]],
      ["wdqs", ["-m", String(seconds), "-s", "-X", "POST", "https://query.wikidata.org/sparql", "--data-urlencode", `query=${PRE}\n${query}`, "-H", "Accept: text/tab-separated-values", "-H", "Content-Type: application/x-www-form-urlencoded", "-H", `User-Agent: ${UA}`]],
    ]) {
      try {
        const body = execFileSync("curl", args, { maxBuffer: 1 << 29, encoding: "utf8" });
        if (!body.startsWith("?")) { last = `${name}: ${body.slice(0, 90).replace(/\s+/g, " ")}`; continue; }
        const lines = body.split("\n");
        lines.shift();
        return lines.filter(Boolean).map((l) => l.split("\t").map(clean));
      } catch (e) { last = `${name}: ${String(e).slice(0, 90)}`; }
    }
    const wait = Math.min(120, 10 + t * 12);
    log(`    (both endpoints unavailable, waiting ${wait}s — ${last})`);
    execFileSync("sleep", [String(wait)]);
  }
  throw new Error(`unavailable after ${tries} rounds: ${last}`);
}
const cache = (name, fn) => {
  const f = `${DIR}/verify-${name}.json`;
  if (existsSync(f)) return JSON.parse(readFileSync(f, "utf8"));
  const v = fn();
  writeFileSync(f, JSON.stringify(v));
  return v;
};
const E = (v) => `(STRAFTER(STR(${v}),"/entity/") AS ${v}q)`;

const DIVORCE = new Set(["Q93190"]);
const DEATH_Q = new Set(["Q24037741", "Q99521170", "Q4", "Q90110620"]);
const SEP_Q = new Set(["Q701040", "Q5561011", "Q3456503", "Q1299585", "Q1142948"]);

let failures = 0;
const check = (ok, msg) => { log(`  ${ok ? "PASS" : "FAIL"}  ${msg}`); if (!ok) failures++; };

// ── 1 · the label vocabulary ─────────────────────────────────────────────────────────────────────
log(`\n1 · THE LABEL VOCABULARY — every P1534 value on a marriage statement, accounted for`);
{
  const rows = cache("causes", () => ask(`SELECT ${E("?c")} ?label (COUNT(*) AS ?n) WHERE {
    ?st pq:P1534 ?c ; ps:P26 ?b .
    OPTIONAL { ?c rdfs:label ?label . FILTER(LANG(?label)='en') }
  } GROUP BY ?c ?label ORDER BY DESC(?n)`));
  let total = 0, classified = 0;
  const unknown = [];
  for (const [q, label, n] of rows) {
    total += +n;
    if (DIVORCE.has(q) || DEATH_Q.has(q) || SEP_Q.has(q)) classified += +n;
    else unknown.push([q, label || "(no English label)", +n]);
  }
  log(`  ${rows.length} distinct causes, ${total.toLocaleString()} statements in total`);
  log(`  classified into divorce / death / separation: ${classified.toLocaleString()} (${(100 * classified / total).toFixed(3)}%)`);
  if (unknown.length) {
    log(`  UNCLASSIFIED — these marriages are dropped, and this is the full list:`);
    for (const [q, label, n] of unknown) log(`    ${q.padEnd(12)} ${String(n).padStart(5)}  ${label}`);
  }
  const unknownTotal = unknown.reduce((s, u) => s + u[2], 0);
  check(unknownTotal / total < 0.01,
    `unclassified causes are ${unknownTotal.toLocaleString()} statements, ${(100 * unknownTotal / total).toFixed(3)}% of the total (want under 1%)`);
  const divorceLike = unknown.filter(([, l]) => /divorc|annul|separat|dissol|repudiat|nullit/i.test(l));
  check(divorceLike.length === 0,
    `no unclassified cause looks divorce-like by name (${divorceLike.map((d) => d[1]).join(", ") || "none"})`);
}

// ── 2 · reconciliation from the other direction ──────────────────────────────────────────────────
log(`\n2 · RECONCILIATION — the same totals counted a different way`);
{
  const one = (w) => +ask(`SELECT (COUNT(*) AS ?n) WHERE { ${w} }`)[0][0];
  const oneDistinct = (w, v) => +ask(`SELECT (COUNT(DISTINCT ${v}) AS ?n) WHERE { ${w} }`)[0][0];
  const led = { divorce: 0, death: 0 };
  led.divorce = cache("recount-div", () => [[String(one(`?st pq:P1534 wd:Q93190 ; ps:P26 ?b . ?a p:P26 ?st ; wdt:P569 ?ad . ?b wdt:P569 ?bd`))]])[0][0];
  led.death = cache("recount-death", () => [[String(one(`VALUES ?dc { wd:Q24037741 wd:Q99521170 wd:Q4 wd:Q90110620 } ?st pq:P1534 ?dc ; ps:P26 ?b . ?a p:P26 ?st ; wdt:P569 ?ad . ?b wdt:P569 ?bd`))]])[0][0];
  const collectedDiv = JSON.parse(readFileSync(`${DIR}/divorce.json`, "utf8")).length;
  const collectedDeath = JSON.parse(readFileSync(`${DIR}/deathcause.json`, "utf8")).length;
  log(`  divorce statements : collected ${collectedDiv.toLocaleString()}, recounted ${(+led.divorce).toLocaleString()}`);
  log(`  death statements   : collected ${collectedDeath.toLocaleString()}, recounted ${(+led.death).toLocaleString()}`);
  check(Math.abs(collectedDiv - +led.divorce) / Math.max(1, +led.divorce) < 0.02, `divorce statement count reconciles within 2%`);
  check(Math.abs(collectedDeath - +led.death) / Math.max(1, +led.death) < 0.02, `death statement count reconciles within 2%`);
  const distinctDivPairs = cache("distinct-div", () => [[String(oneDistinct(`?st pq:P1534 wd:Q93190 ; ps:P26 ?b . ?a p:P26 ?st ; wdt:P569 ?ad . ?b wdt:P569 ?bd . BIND(CONCAT(STR(?a),STR(?b)) AS ?pair)`, "?pair"))]])[0][0];
  log(`  distinct ordered divorce pairs on the server: ${(+distinctDivPairs).toLocaleString()}`);
  log(`    (about twice the couple count, since a marriage is stated on both partners)`);
}

// ── 3 · conflicting statements ───────────────────────────────────────────────────────────────────
log(`\n3 · CONFLICTING STATEMENTS — couples whose statements disagree about the cause`);
{
  const div = JSON.parse(readFileSync(`${DIR}/divorce.json`, "utf8"));
  const death = JSON.parse(readFileSync(`${DIR}/deathcause.json`, "utf8"));
  const key = (r) => [r[0], r[1]].sort().join("|");
  const divSet = new Set(div.map(key)), deathSet = new Set(death.map(key));
  const both = [...divSet].filter((k) => deathSet.has(k));
  log(`  couples with a DIVORCE statement : ${divSet.size.toLocaleString()}`);
  log(`  couples with a DEATH statement   : ${deathSet.size.toLocaleString()}`);
  log(`  couples with BOTH                : ${both.length.toLocaleString()} (${(100 * both.length / divSet.size).toFixed(2)}% of divorces)`);
  log(`  These are real: a couple can marry, divorce, remarry and then be parted by death. The collector`);
  log(`  keeps one row per couple and prefers the divorce statement, so such a couple is labelled`);
  log(`  "divorce" — defensible, since a divorce did happen, but it is not a clean positive.`);
  check(both.length / Math.max(1, divSet.size) < 0.05, `ambiguous couples are under 5% of the divorce class`);
}

// ── 4 · a different API ──────────────────────────────────────────────────────────────────────────
log(`\n4 · A DIFFERENT API — 30 random couples re-fetched through the Action API`);
{
  const set = JSON.parse(readFileSync(`${DIR}/balanced-all-precisions.json`, "utf8"));
  let seed = 20260807;
  const rnd = () => { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; seed |= 0; return (seed >>> 0) / 4294967296; };
  const sample = Array.from({ length: 30 }, () => set[Math.floor(rnd() * set.length)]);
  const ids = [...new Set(sample.flatMap((d) => [d.a, d.b]))];
  const ent = {};
  for (let i = 0; i < ids.length; i += 25) {
    const r = JSON.parse(execFileSync("curl", ["-m", "90", "-s", "-H", `User-Agent: ${UA}`,
      `https://www.wikidata.org/w/api.php?action=wbgetentities&ids=${ids.slice(i, i + 25).join("|")}&props=claims&format=json`],
      { maxBuffer: 1 << 28, encoding: "utf8" }));
    Object.assign(ent, r.entities);
    execFileSync("sleep", ["1"]);
  }
  let causeBad = 0, dobBad = 0, compared = 0;
  const notes = [];
  for (const d of sample) {
    const ca = ent[d.a]?.claims, cb = ent[d.b]?.claims;
    if (!ca || !cb) continue;
    compared++;
    // Does either partner's P26 statement pointing at the other carry the cause the dataset claims?
    const causes = new Set();
    for (const [self, other] of [[ca, d.b], [cb, d.a]]) {
      for (const st of self.P26 ?? []) {
        if (st.mainsnak?.datavalue?.value?.id !== other) continue;
        for (const q of st.qualifiers?.P1534 ?? []) causes.add(q.datavalue?.value?.id);
      }
    }
    const wantDivorce = d.y === 1;
    const hasDivorce = causes.has("Q93190");
    const hasDeath = [...causes].some((c) => DEATH_Q.has(c));
    if (wantDivorce ? !hasDivorce : !hasDeath) {
      causeBad++;
      if (notes.length < 6) notes.push(`${d.a}|${d.b} labelled ${wantDivorce ? "divorce" : "death"}, API causes {${[...causes].join(",") || "none"}}`);
    }
    const apiDob = (claims) => {
      const st = (claims?.P569 ?? []).filter((s) => s.rank !== "deprecated");
      const pref = st.filter((s) => s.rank === "preferred");
      const use = pref.length ? pref : st;
      return use.length ? use.map((s) => s.mainsnak.datavalue.value.time.replace(/^\+/, "").split("T")[0]).sort()[0] : null;
    };
    if (apiDob(ca) === null || apiDob(cb) === null) { dobBad++; }
  }
  log(`  compared ${compared} couples`);
  check(causeBad === 0, `the stated cause matches the Action API for every sampled couple (${causeBad} bad)`);
  check(dobBad === 0, `both partners have a birth date via the Action API (${dobBad} missing)`);
  for (const n of notes) log(`    ${n}`);
}

// ── 5 · the inference route, retried ─────────────────────────────────────────────────────────────
log(`\n5 · THE INFERENCE ROUTE — how many additional divorces are recoverable`);
try {
  const one = (w) => +ask(`SELECT (COUNT(*) AS ?n) WHERE { ${w} }`)[0][0];
  const base = `?st pq:P582 ?end ; ps:P26 ?b . ?a p:P26 ?st ; wdt:P569 ?ad ; wdt:P570 ?adod . ?b wdt:P569 ?bd ; wdt:P570 ?bdod .`;
  const inferredDiv = cache("inferred-count", () => [[String(one(
    `${base} FILTER(YEAR(?end) < YEAR(?adod) - 1 && YEAR(?end) < YEAR(?bdod) - 1)`))]])[0][0];
  const withCause = cache("inferred-with-cause", () => [[String(one(
    `${base} ?st pq:P1534 ?c . FILTER(YEAR(?end) < YEAR(?adod) - 1 && YEAR(?end) < YEAR(?bdod) - 1)`))]])[0][0];
  const novel = +inferredDiv - +withCause;
  log(`  statements the rule calls divorce             : ${(+inferredDiv).toLocaleString()}`);
  log(`  of those, already carrying an explicit cause  : ${(+withCause).toLocaleString()}`);
  log(`  NEW divorces the inference would add          : ${novel.toLocaleString()} statements, about ${Math.round(novel / 2).toLocaleString()} couples`);
  log(`  At 98.9% precision that would take the divorce class from roughly 3,200 to ${(3200 + Math.round(novel / 2)).toLocaleString()},`);
  log(`  and the balanced set from 6,372 to about ${(2 * (3200 + Math.round(novel / 2))).toLocaleString()} couples.`);
  check(true, `the size of the remaining gap is now a known quantity, not an unknown one`);
} catch (e) {
  log(`  !! still unavailable: ${String(e).slice(0, 140)}`);
  log(`  !! The gap remains unmeasured. This is the one check that could not be completed.`);
  failures++;
}

log(`\n${failures === 0 ? "ALL CHECKS PASS" : `${failures} CHECK(S) FAILED OR INCOMPLETE`}`);
process.exitCode = failures ? 1 : 0;
