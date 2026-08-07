/**
 * collect.mjs — every ended marriage on Wikidata where both partners' birth dates are known to the
 * day, with the number of children the two of them had together.
 *
 * ── Why not the Wikidata Query Service ──────────────────────────────────────────────────────────
 *
 * Because it cannot answer this completely, and it does not say so when it fails. WDQS has a
 * 60-second limit and returns whatever it managed as a perfectly well-formed response, with no error
 * and no warning. Measured here, on the same query minutes apart: 930,633 marriage rows one run and
 * 878,746 the next. Its marriage end-date query returned 46,822 rows against a true 104,145 — it was
 * missing more than half the divorces and looked fine. Partitioning made it worse rather than better,
 * because the cost is the scan and not the answer: a STRENDS filter that should have cut the work
 * tenfold timed the query out instead, and a filter on the birth year timed out on every decade.
 *
 * So the data comes from QLever's public Wikidata endpoint, which holds a full dump, answers in
 * seconds, and carries the whole statement model — qualifiers and value nodes included. It is a fixed
 * snapshot rather than a live service, which for a study is the better property: these numbers can be
 * reproduced, where a live endpoint changes underneath you mid-collection.
 *
 * EVERY query is checked against a COUNT of its own WHERE clause. That check is not decoration — it
 * is what caught the truncation above, and nothing here is trusted without it.
 *
 * ── The traps in the data ───────────────────────────────────────────────────────────────────────
 *
 *  1. TRUNCATED DATES LOOK LIKE REAL ONES. wdt:P569 returns "1801-01-01" for a person whose birth is
 *     known only to the year, which would put thousands of people on 1 January and invent a planetary
 *     position for each. Precision is read for the TRUTHY statement specifically, by binding the same
 *     value through both wdt: and psv:, and anything below day precision is dropped, never rounded.
 *  2. THE VALUE IS PROLEPTIC GREGORIAN WHATEVER THE CALENDAR TAG SAYS. Shakespeare's is tagged Julian
 *     and reads 1564-05-03, which is 23 April Julian converted; Newton's reads 1643-01-04 for
 *     25 December 1642 Julian. Both checked here by hand against a conversion. The ephemeris used
 *     downstream also works in proleptic Gregorian, so the two agree and nothing is converted.
 *  3. ONE PERSON, SEVERAL BIRTH DATES, even among best-rank statements — Wikidata prefers neither of
 *     Shakespeare's two. The earliest day-precision truthy date wins, always, and the number of people
 *     affected is reported rather than hidden.
 *  4. EVERY COUPLE APPEARS TWICE, because P26 is stated on both partners. Deduplicated on the sorted
 *     pair of IDs.
 *  5. "NO CHILDREN RECORDED" IS NOT "NO CHILDREN". The dataset's central weakness. Children are
 *     counted as people carrying BOTH partners as parents, which is exact per couple and never
 *     confuses one marriage's children with another's — and it is cross-checked against the stated
 *     P1971 count in verify.mjs, where the disagreement is measured rather than assumed away.
 *  6. A MARRIAGE IS ENDED BY DEATH OR DIVORCE, AND BY NOTHING ELSE. Either the P26 statement carries
 *     an end date, or one of the partners has a recorded date of death. No inference from age: a
 *     couple born in 1750 with no death date recorded on either side is certainly dead and certainly
 *     not still married, but Wikidata does not say so, and this dataset only counts what is recorded.
 *     The cost of that strictness is reported below rather than buried.
 *
 * Usage: node collect.mjs <outdir>
 */

import { writeFileSync, mkdirSync, existsSync, readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const OUT = process.argv[2] || "./data";
mkdirSync(OUT, { recursive: true });
const ENDPOINT = "https://qlever.cs.uni-freiburg.de/api/wikidata/";
const UA = "ArtaMatch-research/1.0 (https://github.com/ArtaQuest/artamatch; support@artaquest.org)";
const PRE = `PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX wikibase: <http://wikiba.se/ontology#>`;

const log = (s) => process.stderr.write(s + "\n");

function ask(query, { seconds = 280, tries = 3 } = {}) {
  let last;
  for (let t = 0; t < tries; t++) {
    try {
      const body = execFileSync("curl", [
        "-m", String(seconds), "-sL", ENDPOINT,
        "-H", "Accept: text/tab-separated-values",
        "-H", "Content-type: application/sparql-query",
        "-H", `User-Agent: ${UA}`,
        "--data-binary", `${PRE}\n${query}`,
      ], { maxBuffer: 1 << 30, encoding: "utf8" });
      if (!body.startsWith("?")) throw new Error(body.slice(0, 200));
      const lines = body.split("\n");
      lines.shift();
      return lines.filter(Boolean).map((l) => l.split("\t").map(clean));
    } catch (e) { last = e; execFileSync("sleep", [String(4 + t * 6)]); }
  }
  throw new Error(`query failed: ${String(last).slice(0, 400)}`);
}
const clean = (v) => {
  let s = v.trim().replace(/\^\^<[^>]*>$/, "");
  if (s.startsWith("<") && s.endsWith(">")) s = s.slice(1, -1);
  if (s.startsWith('"') && s.endsWith('"')) s = s.slice(1, -1);
  return s;
};

/** A query, and a COUNT of the same WHERE clause. They must agree, or the result was truncated. */
function verified(name, where, select) {
  const f = `${OUT}/${name}.json`;
  if (existsSync(f)) { const v = JSON.parse(readFileSync(f, "utf8")); log(`${name}: ${v.length.toLocaleString()} (cached)`); return v; }
  const expect = +ask(`SELECT (COUNT(*) AS ?n) WHERE { ${where} }`)[0][0];
  const rows = ask(`SELECT ${select} WHERE { ${where} }`);
  log(`${name}: ${rows.length.toLocaleString()} rows against a COUNT of ${expect.toLocaleString()} — ` +
    `${rows.length === expect ? "COMPLETE" : "TRUNCATED"}`);
  if (rows.length !== expect) throw new Error(`${name} truncated: ${rows.length} of ${expect}`);
  writeFileSync(f, JSON.stringify(rows));
  return rows;
}

const E = (v) => `(STRAFTER(STR(${v}),"/entity/") AS ${v}q)`;

// ── the marriages ───────────────────────────────────────────────────────────────────────────────
//
// Husband first, so "father minus mother" downstream is unambiguous. Same-sex couples have no
// father/mother to difference and are counted separately below rather than silently dropped.
const MARRIAGE_WHERE = `
  ?a wdt:P21 wd:Q6581097 ; p:P26 ?st ; wdt:P569 ?ad .
  ?st ps:P26 ?b .
  ?b wdt:P21 wd:Q6581072 ; wdt:P569 ?bd .
  ?a p:P569/psv:P569 ?atv . ?atv wikibase:timeValue ?ad ; wikibase:timePrecision ?ap .
  ?b p:P569/psv:P569 ?btv . ?btv wikibase:timeValue ?bd ; wikibase:timePrecision ?bp .
  FILTER(?ap >= 11 && ?bp >= 11)
  OPTIONAL { ?st pq:P582 ?end }
  OPTIONAL { ?st pq:P580 ?start }
  # P1534 "end cause" — the only place Wikidata says WHY a marriage ended. Without it, a recorded end
  # date is not evidence of divorce: most of them mark a death.
  OPTIONAL { ?st pq:P1534 ?cause }
  OPTIONAL { ?a wdt:P570 ?adod }
  OPTIONAL { ?b wdt:P570 ?bdod }
  OPTIONAL { ?a wdt:P1971 ?akids }
  OPTIONAL { ?b wdt:P1971 ?bkids }`;
const marriages = verified("marriages", MARRIAGE_WHERE,
  `${E("?a")} ${E("?b")} ?ad ?bd ?end ?start ${E("?cause")} ?adod ?bdod ?akids ?bkids`);

// ── the children, by co-parentage ───────────────────────────────────────────────────────────────
const coparents = verified("coparents", `?c wdt:P22 ?d ; wdt:P25 ?m .`, `${E("?d")} ${E("?m")}`);

// ── the children's own birth dates, where they are known to the day ──────────────────────────────
//
// Needed for any target that asks how old the children were at some moment. Only 327,330 of the
// 732,201 co-parented children have a day-precision birth date — 44.7% — so a SUM over children is
// censored unevenly, and the censoring tracks notability and era rather than being random. Downstream
// this is handled by using only couples where EVERY co-parented child is dated, which is the only way
// to make such a sum well defined.
const childDates = verified("childdates",
  `?c wdt:P22 ?d ; wdt:P25 ?m ; wdt:P569 ?cd .
   ?c p:P569/psv:P569 ?ctv . ?ctv wikibase:timeValue ?cd ; wikibase:timePrecision ?cp .
   FILTER(?cp >= 11)`,
  `${E("?d")} ${E("?m")} ?cd`);

// ── what fraction of the marriage graph this is, for the record ─────────────────────────────────
const totals = existsSync(`${OUT}/totals.json`)
  ? JSON.parse(readFileSync(`${OUT}/totals.json`, "utf8"))
  : (() => {
    const one = (w) => +ask(`SELECT (COUNT(*) AS ?n) WHERE { ${w} }`)[0][0];
    const t = {
      allSpouseTriples: one("?a wdt:P26 ?b"),
      maleFemale: one("?a wdt:P21 wd:Q6581097 ; wdt:P26 ?b . ?b wdt:P21 wd:Q6581072"),
      sameSex: one("?a wdt:P21 ?s ; wdt:P26 ?b . ?b wdt:P21 ?s"),
      bothDated: one("?a wdt:P21 wd:Q6581097 ; wdt:P26 ?b ; wdt:P569 ?x . ?b wdt:P21 wd:Q6581072 ; wdt:P569 ?y"),
    };
    writeFileSync(`${OUT}/totals.json`, JSON.stringify(t));
    return t;
  })();

// ── join ────────────────────────────────────────────────────────────────────────────────────────
/**
 * The date part of a timestamp — everything before the T.
 *
 * NOT slice(0, 10). BCE dates carry a leading minus, so "-0009-07-31T00:00:00Z" sliced to ten
 * characters becomes "-0009-07-3" and silently loses a digit off the day. Four Roman couples in this
 * dataset were mangled that way before the consistency check found them.
 */
const day = (v) => (v ? v.split("T")[0] : null);

// One birth date per person, deterministically: the earliest day-precision truthy date.
const dob = new Map();
let ambiguous = 0;
for (const [a, b, ad, bd] of marriages) {
  for (const [id, d] of [[a, day(ad)], [b, day(bd)]]) {
    const cur = dob.get(id);
    if (cur === undefined) dob.set(id, d);
    else if (cur !== d) { ambiguous++; if (d < cur) dob.set(id, d); }
  }
}

const kidsOf = new Map();
for (const [d, m] of coparents) {
  const k = [d, m].sort().join("|");
  kidsOf.set(k, (kidsOf.get(k) ?? 0) + 1);
}

const childDobsOf = new Map();
for (const [d, m, cd] of childDates) {
  const k = [d, m].sort().join("|");
  const arr = childDobsOf.get(k) ?? [];
  arr.push(day(cd));
  childDobsOf.set(k, arr);
}

const couples = new Map();
const reasons = { ongoing: 0, byStatement: 0, byDeath: 0, impossible: 0 };
for (const [a, b, , , end, start, cause, adod, bdod, akids, bkids] of marriages) {
  // Ended by death or divorce, and by nothing else.
  const ended = !!end || !!adod || !!bdod;
  if (!ended) { reasons.ongoing++; continue; }
  // Wikidata contains genuinely impossible rows — a marriage recorded as ending before one of the
  // partners was born. Two of them are in here. They are dropped rather than modelled, and counted
  // rather than quietly removed, because a source that can be wrong about this can be wrong about
  // the rest of the row too.
  const e = day(end);
  if (e && (e < dob.get(a) || e < dob.get(b))) { reasons.impossible++; continue; }
  const key = [a, b].sort().join("|");
  const prev = couples.get(key);
  if (prev && (prev.end || !end)) continue;
  couples.set(key, {
    key, father: a, mother: b, fDob: dob.get(a), mDob: dob.get(b),
    end: day(end), start: day(start), cause: cause || null, fDod: day(adod), mDod: day(bdod),
    endedBy: end ? "statement" : "death",
    statedKids: [akids ? +akids : null, bkids ? +bkids : null],
    children: kidsOf.get(key) ?? 0,
    childDobs: childDobsOf.get(key) ?? [],
  });
}
for (const c of couples.values()) { if (c.endedBy === "statement") reasons.byStatement++; else reasons.byDeath++; }

const out = [...couples.values()];
writeFileSync(`${OUT}/dataset.json`, JSON.stringify(out));
log(`\nCOVERAGE OF THE MARRIAGE GRAPH`);
log(`  spouse triples in Wikidata                : ${totals.allSpouseTriples.toLocaleString()}`);
log(`  male-female pairs                         : ${totals.maleFemale.toLocaleString()}`);
log(`  same-sex pairs (no father/mother to difference) : ${totals.sameSex.toLocaleString()}`);
log(`  male-female, both with any birth date     : ${totals.bothDated.toLocaleString()}`);
log(`  ... and both known to the DAY             : ${marriages.length.toLocaleString()}`);
log(`\nDATASET`);
log(`  distinct couples at day precision         : ${(couples.size + reasons.ongoing).toLocaleString()}`);
log(`  dropped, no recorded death or divorce     : ${reasons.ongoing.toLocaleString()}`);
log(`  dropped, marriage ends before a birth (impossible source data) : ${reasons.impossible.toLocaleString()}`);
log(`  KEPT (ended by death or divorce)          : ${out.length.toLocaleString()}`);
log(`    ended by a stated end date (divorce or death) : ${reasons.byStatement.toLocaleString()}`);
log(`    ended by a recorded date of death             : ${reasons.byDeath.toLocaleString()}`);
log(`  people with more than one best-rank day-precision birth date : ${ambiguous}`);
log(`  couples with at least one recorded child  : ${out.filter((c) => c.children > 0).length.toLocaleString()}`);
log(`  children counted in total                 : ${out.reduce((s, c) => s + c.children, 0).toLocaleString()}`);
log(`  with a recorded marriage START date       : ${out.filter((c) => c.start).length.toLocaleString()}`);
log(`  with BOTH a start and an end (duration known exactly) : ${out.filter((c) => c.start && c.end).length.toLocaleString()}`);
{
  const full = out.filter((c) => c.childDobs.length === c.children);
  log(`  every co-parented child dated to the day : ${full.length.toLocaleString()} of ${out.length.toLocaleString()} couples ` +
    `(${full.filter((c) => c.children > 0).length.toLocaleString()} of them with at least one child)`);
}
{
  const DIVORCE = new Set(["Q93190"]);
  const DEATH = new Set(["Q24037741", "Q99521170", "Q4", "Q90110620"]);
  const d = out.filter((c) => DIVORCE.has(c.cause)).length, k = out.filter((c) => DEATH.has(c.cause)).length;
  log(`  with a stated END CAUSE: ${d.toLocaleString()} divorce, ${k.toLocaleString()} death ` +
    `(${out.filter((c) => c.cause && !DIVORCE.has(c.cause) && !DEATH.has(c.cause)).length.toLocaleString()} other: annulment, separation, repudiation)`);
}
