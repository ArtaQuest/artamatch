/**
 * collect-divorce.mjs — the largest balanced divorce-or-death dataset obtainable from birth dates.
 *
 * ── Why Wikidata, after looking elsewhere ────────────────────────────────────────────────────────
 *
 * FamiLinx (86M Geni.com profiles, Kaplanis et al. 2018) is the obvious candidate for scale and is
 * useless for this question: its individual records carry birth and death dates and locations and
 * gender, and NOTHING about marriage events. The 54-page empirical evaluation of the database mentions
 * marriage once, in passing. Genealogy corpora in general record births, deaths, marriages and
 * parentage — divorce is the one life event they almost never capture, because it leaves no descendant.
 * The same goes for WikiTree and GEDCOM collections. Census microdata (IPUMS) has marital status
 * including "divorced" but only ages rather than birth dates, and no way to pair the two ex-spouses.
 * Administrative divorce certificates do carry both parties' dates of birth and would be ideal; they
 * are not openly available.
 *
 * Wikidata's P1534 "end cause" qualifier is, as far as this search found, the largest OPEN source that
 * states why a marriage ended AND gives both partners' birth dates. So the job is to extract every last
 * usable row from it.
 *
 * ── Two routes to a label, and the second one is validated against the first ──────────────────────
 *
 *   EXPLICIT   P1534 says divorce (Q93190) or a death (Q24037741 death of spouse, Q99521170 death of
 *              subject, Q4 death, Q90110620 death of partner). ~9,960 divorce statements exist.
 *   INFERRED   The statement carries an end date (P582) and both partners' death dates, and the end
 *              precedes BOTH deaths by more than a year. A marriage that ended while both spouses were
 *              still alive did not end by death.
 *
 * The inferred route roughly doubles the positive class, so it is worth having — but only if it is
 * right. It is therefore CHECKED against the explicit labels on the rows that carry both, and the
 * agreement rate is reported. An inference that disagrees with the stated cause is not a bigger
 * dataset, it is a noisier one, and the numbers below decide which.
 *
 * ── Balance, and no ongoing marriages ────────────────────────────────────────────────────────────
 *
 * Deaths vastly outnumber divorces, so the divorce class is the binding constraint and the death class
 * is subsampled down to match it exactly, seeded. Every row must have an end date or a recorded death,
 * so a marriage that may still be running cannot enter either class.
 *
 * Birth dates are taken at ANY precision here, with the precision recorded, because the point is
 * maximum size. Day precision costs about a third of the sample; the analysis can stratify on it.
 *
 * Usage: node research/collect-divorce.mjs <outdir>
 */

import { writeFileSync, mkdirSync, existsSync, readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const OUT = process.argv[2] || "./research/data-divorce";
mkdirSync(OUT, { recursive: true });
const UA = "ArtaMatch-research/1.0 (https://github.com/ArtaQuest/artamatch; support@artaquest.org)";
const PRE = `PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX wikibase: <http://wikiba.se/ontology#>`;

const log = (s) => process.stderr.write(s + "\n");
let lastEndpoint = null;

/**
 * Ask both endpoints, with retries. QLever is faster and was returning 502 while this was written;
 * WDQS is slower and truncates large results silently, but every query here is small enough to be
 * safe on it. Whichever answers first wins, and each result is checked against a COUNT of its own
 * WHERE clause regardless of which one served it.
 */
const ENDPOINTS = [
  { name: "qlever", run: (q, s) => execFileSync("curl", ["-m", String(s), "-sL", "https://qlever.cs.uni-freiburg.de/api/wikidata/", "-H", "Accept: text/tab-separated-values", "-H", "Content-type: application/sparql-query", "-H", `User-Agent: ${UA}`, "--data-binary", `${PRE}\n${q}`], { maxBuffer: 1 << 29, encoding: "utf8" }) },
  { name: "wdqs", run: (q, s) => execFileSync("curl", ["-m", String(s), "-s", "-X", "POST", "https://query.wikidata.org/sparql", "--data-urlencode", `query=${PRE}\n${q}`, "-H", "Accept: text/tab-separated-values", "-H", "Content-Type: application/x-www-form-urlencoded", "-H", `User-Agent: ${UA}`], { maxBuffer: 1 << 29, encoding: "utf8" }) },
];

/**
 * `pin` forces one endpoint for the whole call. It matters: QLever and WDQS hold different dump
 * snapshots, so a COUNT served by one and a data query served by the other can never agree exactly —
 * the multispouse query came back with 64,856 usable rows against a COUNT of 64,855, one MORE than
 * existed, and read as truncation when it was actually two different days of Wikidata. Every
 * completeness check must therefore ask both of its questions of the same server.
 */
function ask(query, { seconds = 115, tries = 6, pin = null } = {}) {
  let last = "";
  for (let t = 0; t < tries; t++) {
    for (const ep of (pin ? ENDPOINTS.filter((e) => e.name === pin) : ENDPOINTS)) {
      try {
        const body = ep.run(query, seconds);
        if (!body.startsWith("?")) { last = `${ep.name}: ${body.slice(0, 120).replace(/\s+/g, " ")}`; continue; }
        lastEndpoint = ep.name;
        const lines = body.split("\n");
        lines.shift();
        const kept = lines.filter(Boolean).map((l) => l.split("\t").map(clean));
        // A row whose every column is empty is a real row with nothing in it — a blank node, or an
        // "unknown value" snak that STRAFTER reduces to "". It counts towards the server's COUNT and
        // cannot be used for anything, so it is reported separately rather than mistaken for truncation.
        const usable = kept.filter((r) => r.some((v) => v !== ""));
        usable.blank = kept.length - usable.length;
        return usable;
      } catch (e) { last = `${ep.name}: ${String(e).slice(0, 120)}`; }
    }
    execFileSync("sleep", [String(5 + t * 10)]);
    log(`  retry ${t + 1}: ${last}`);
  }
  throw new Error(`both endpoints failed: ${last}`);
}
const clean = (v) => {
  let s = v.trim().replace(/\^\^<[^>]*>$/, "");
  if (s.startsWith("<") && s.endsWith(">")) s = s.slice(1, -1);
  if (s.startsWith('"') && s.endsWith('"')) s = s.slice(1, -1);
  return s;
};
const E = (v) => `(STRAFTER(STR(${v}),"/entity/") AS ${v}q)`;

/** A query, plus a COUNT of the same WHERE clause. They must agree or the answer was truncated. */
function verified(name, where, select) {
  const f = `${OUT}/${name}.json`;
  if (existsSync(f)) { const v = JSON.parse(readFileSync(f, "utf8")); log(`${name}: ${v.length.toLocaleString()} (cached)`); return v; }
  const expect = +ask(`SELECT (COUNT(*) AS ?n) WHERE { ${where} }`)[0][0];
  const served = lastEndpoint;                       // whoever answered the COUNT must answer the data
  const rows = ask(`SELECT ${select} WHERE { ${where} }`, { pin: served });
  const blank = rows.blank ?? 0;
  const complete = rows.length + blank === expect;
  log(`${name}: ${rows.length.toLocaleString()} usable${blank ? ` + ${blank} blank` : ""} against a COUNT of ` +
    `${expect.toLocaleString()} from ${served} — ${complete ? "COMPLETE" : "TRUNCATED"}`);
  if (!complete) throw new Error(`${name} truncated: ${rows.length + blank} of ${expect}`);
  writeFileSync(f, JSON.stringify(rows));
  execFileSync("sleep", ["2"]);
  return rows;
}

// ── four narrow queries, each starting from a SELECTIVE pattern ──────────────────────────────────
//
// One broad query over P26 with a UNION and six OPTIONALs times both endpoints out. The fix is to lead
// with the qualifier rather than with the marriage: `?st pq:P1534 wd:Q93190` touches ten thousand
// statements where `?a p:P26 ?st` touches a million, and the planner follows the selective pattern.
// Same data, three orders of magnitude less work.
const TAIL = `
  OPTIONAL { ?st pq:P582 ?end }
  OPTIONAL { ?st pq:P580 ?start }
  OPTIONAL { ?a wdt:P570 ?adod }
  OPTIONAL { ?b wdt:P570 ?bdod }`;
const SELECT = `${E("?a")} ${E("?b")} ?ad ?bd ?end ?start ?adod ?bdod`;

/**
 * THE FULL CAUSE VOCABULARY, enumerated rather than guessed.
 *
 * verify-divorce.mjs lists every distinct P1534 value on a marriage statement — 126 of them — and the
 * first version of this collector knew about ten. The tail is small (168 statements, 0.64%) but it is
 * not empty, and it contained a SECOND annulment item (Q759734, distinct from Q701040) plus dissolution,
 * breakup, Mexican divorce, separation process and conscious uncoupling on the divorce side, and
 * widow/widower/widowhood and every specific manner of death on the other.
 *
 * Deliberately left OUT, because they name a REASON rather than an outcome and could precede either:
 * infidelity, adultery, abandonment, alcoholism, exile. And left out as data errors: "2005", "1958",
 * "present", "retirement", "declaration of war", "fall of the Berlin Wall", "schism", and the 68
 * label-less one-offs.
 */
const DIVORCE_Q = ["Q93190", "Q701040", "Q759734", "Q5561011", "Q3456503", "Q1299585", "Q1142948",
  "Q5282797", "Q100926628", "Q16557696", "Q898987", "Q65089925", "Q3564519", "Q21171241"];
const DEATH_Q = ["Q24037741", "Q99521170", "Q4", "Q90110620", "Q161936", "Q18646998", "Q179115",
  "Q16675060", "Q10737", "Q132821", "Q3882219", "Q210392", "Q21142718", "Q15747939", "Q267505",
  "Q1076426", "Q90130768", "Q110249015", "Q128952023", "Q84263196", "Q83737887", "Q10806",
  "Q2438548", "Q693726", "Q4086889", "Q18748141", "Q1356047", "Q3030513"];
const values = (qs) => qs.map((q) => `wd:${q}`).join(" ");

const divorceRows = verified("divorce2",
  `VALUES ?vc { ${values(DIVORCE_Q)} }
   ?st pq:P1534 ?vc ; ps:P26 ?b . ?a p:P26 ?st ; wdt:P569 ?ad . ?b wdt:P569 ?bd .${TAIL}`, SELECT);

const deathRows = verified("deathcause2",
  `VALUES ?dc { ${values(DEATH_Q)} }
   ?st pq:P1534 ?dc ; ps:P26 ?b . ?a p:P26 ?st ; wdt:P569 ?ad . ?b wdt:P569 ?bd .${TAIL}`, SELECT);

// Annulment, separation and the rest now count as divorce — the marriage ended while both partners
// were alive, which is the distinction this target is drawing — so there is no separate class left.
const sepRows = [];

// The inference pool: an end date and both deaths known, which is what makes "ended while both were
// alive" decidable. Led by the end-date qualifier, again for selectivity.
//
// This one is too big for a single response — it came back 53,025 of 59,454, silently. Partitioned by
// the END YEAR into buckets small enough to complete, each verified against its own COUNT, so the
// union is provably whole rather than probably whole. The buckets are uneven on purpose: divorce
// records cluster hard in the late twentieth century.
// A YEAR filter on the end date does not partition this — the filter is evaluated after the joins, so
// each bucket costs as much as the whole and every one of them times out. Partitioning by an INDEXED
// pattern does work: the first partner's sex. Every mixed-sex couple is reachable through the male
// bucket and again through the female one, so the two buckets together cover the pair set with
// duplicates rather than gaps, and the deduplication below was always going to run anyway.
//
// The inference route is OPTIONAL. It roughly doubles the positive class when it succeeds, and while
// this was written QLever was returning 502 on every request and WDQS was timing out on anything this
// size. Rather than block the whole dataset on an outage, a failure here is caught, reported, and the
// explicit labels — which are already verified complete — carry on alone.
/**
 * REMARRIAGE AS EVIDENCE OF SEPARATION.
 *
 * If a person married again while their previous spouse was still alive, that previous marriage ended
 * in something other than a death — which is exactly the distinction this target draws. This does not
 * need an end date on the statement at all, only two marriage START dates and one death date, so it
 * reaches couples the end-date rule cannot see. A widow remarrying after her husband died is NOT caught,
 * because the new marriage has to begin BEFORE the old partner's death.
 *
 * Fetched as every person with more than one recorded spouse, then all of that person's marriages with
 * their dates. Batched by ID, which is an index lookup and survives the endpoint being unwell.
 */
let remarriage = [];
try {
  const multi = verified("multispouse",
    `{ SELECT ?a WHERE { ?a wdt:P26 ?sp } GROUP BY ?a HAVING(COUNT(DISTINCT ?sp) > 1) }`, `${E("?a")}`)
    .map((r) => r[0]);
  log(`people with more than one recorded spouse: ${multi.length.toLocaleString()}`);
  const B2 = 800;
  for (let i = 0; i < multi.length; i += B2) {
    const slice = multi.slice(i, i + B2);
    const got = existsSync(`${OUT}/remar-${i}.json`)
      ? JSON.parse(readFileSync(`${OUT}/remar-${i}.json`, "utf8"))
      : (() => {
        const v = ask(`SELECT ${E("?a")} ${E("?b")} ?start ?end ?bdod WHERE {
          VALUES ?a { ${slice.map((q) => `wd:${q}`).join(" ")} }
          ?a p:P26 ?st . ?st ps:P26 ?b .
          OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end } OPTIONAL { ?b wdt:P570 ?bdod } }`);
        writeFileSync(`${OUT}/remar-${i}.json`, JSON.stringify(v));
        execFileSync("sleep", ["1"]);
        return v;
      })();
    remarriage.push(...got);
    process.stderr.write(`remarriage ${Math.min(i + B2, multi.length)}/${multi.length}\r`);
  }
  log(`\nmarriage statements for multiply-married people: ${remarriage.length.toLocaleString()}`);
} catch (e) {
  log(`\n!! the remarriage route failed: ${String(e).slice(0, 140)}`);
  remarriage = [];
}

// Each bucket stands alone. The male-partner bucket already reaches every mixed-sex couple whose
// statement is written on the husband, which is the large majority, so losing the female bucket to an
// outage costs coverage rather than correctness — and coverage that is reported rather than silent.
let endRows = [];
const endBuckets = { m: false, f: false };
for (const [tag, sex] of [["m", "wd:Q6581097"], ["f", "wd:Q6581072"]]) {
  try {
    endRows.push(...verified(`enddated-${tag}`,
      `?a wdt:P21 ${sex} ; p:P26 ?st ; wdt:P569 ?ad ; wdt:P570 ?adod .
       ?st pq:P582 ?end ; ps:P26 ?b .
       ?b wdt:P569 ?bd ; wdt:P570 ?bdod .
       OPTIONAL { ?st pq:P580 ?start }`,
      `${E("?a")} ${E("?b")} ?ad ?bd ?end ?start ?adod ?bdod`));
    endBuckets[tag] = true;
  } catch (e) {
    log(`  !! end-date bucket "${tag}" unavailable: ${String(e).slice(0, 120)}`);
  }
}
log(`enddated: ${endRows.length.toLocaleString()} rows; buckets complete: ` +
  `${Object.entries(endBuckets).filter(([, v]) => v).map(([k]) => k).join(", ") || "none"}` +
  `${endBuckets.m && endBuckets.f ? "" : " — coverage is partial, see the header"}`);

const rows = [
  ...divorceRows.map((r) => [...r, "DIVORCED"]),
  ...deathRows.map((r) => [...r, "DEATH"]),
  ...endRows.map((r) => [...r, null]),
];

// ── birth-date precision, in batches by ID ───────────────────────────────────────────────────────
const people = [...new Set(rows.flatMap((r) => [r[0], r[1]]))];
const prec = new Map();
const BATCH = 2000;
for (let i = 0; i < people.length; i += BATCH) {
  const slice = people.slice(i, i + BATCH);
  const got = existsSync(`${OUT}/prec-${i}.json`)
    ? JSON.parse(readFileSync(`${OUT}/prec-${i}.json`, "utf8"))
    : (() => {
      const v = ask(`SELECT ${E("?p")} ?d ?pr WHERE {
        VALUES ?p { ${slice.map((q) => `wd:${q}`).join(" ")} }
        ?p wdt:P569 ?d . ?p p:P569/psv:P569 ?tv . ?tv wikibase:timeValue ?d ; wikibase:timePrecision ?pr }`);
      writeFileSync(`${OUT}/prec-${i}.json`, JSON.stringify(v));
      execFileSync("sleep", ["1"]);
      return v;
    })();
  for (const [q, , pr] of got) prec.set(q, Math.max(prec.get(q) ?? 0, +pr));
  process.stderr.write(`precision ${Math.min(i + BATCH, people.length)}/${people.length}\r`);
}
log(`\nbirth-date precision resolved for ${prec.size.toLocaleString()} of ${people.length.toLocaleString()} people`);

// ── labelling ───────────────────────────────────────────────────────────────────────────────────
const DIVORCE = new Set(["DIVORCED"]);
const SEPARATIONS = new Set();   // folded into the divorce class; nothing is a third thing now
const DEATH = new Set(["DEATHCAUSE"]);
const day = (v) => (v ? v.split("T")[0] : null);
const yr = (v) => (v ? +v.split("-")[0] : null);

/** The inference: the marriage ended more than a year before BOTH partners died. */
const inferredDivorce = (r) =>
  r.end !== null && r.adod !== null && r.bdod !== null &&
  yr(r.end) < yr(r.adod) - 1 && yr(r.end) < yr(r.bdod) - 1;
/** Its complement, on rows where the inference is computable at all. */
const inferrable = (r) => r.end !== null && r.adod !== null && r.bdod !== null;

/**
 * Build, per person, the list of marriages with their start dates and the partner's death date, then
 * mark any marriage that a LATER marriage overlapped while the old partner was still alive.
 */
const marriagesOf = new Map();
for (const [a, b, start, end, bdod] of remarriage) {
  const arr = marriagesOf.get(a) ?? [];
  arr.push({ b, start: day(start), end: day(end), bdod: day(bdod) });
  marriagesOf.set(a, arr);
}
const separatedByRemarriage = new Set();
for (const [person, ms] of marriagesOf) {
  for (const m of ms) {
    if (!m.start || !m.bdod) continue;                    // need this marriage's start and the partner's death
    for (const other of ms) {
      if (other.b === m.b || !other.start) continue;
      // A later marriage that began while this partner was still alive.
      if (other.start > m.start && other.start < m.bdod) {
        separatedByRemarriage.add([person, m.b].sort().join("|"));
      }
    }
  }
}
log(`couples marked separated because one partner remarried while the other lived: ${separatedByRemarriage.size.toLocaleString()}`);

const couples = new Map();
for (const [a, b, ad, bd, end, start, adod, bdod, cause] of rows) {
  const key = [a, b].sort().join("|");
  const rec = {
    key, a, b, aDob: day(ad), bDob: day(bd),
    aPrec: prec.get(a) ?? null, bPrec: prec.get(b) ?? null,
    end: day(end), start: day(start),
    cause: cause === "DEATH" ? "DEATHCAUSE" : cause || null,
    adod: day(adod), bdod: day(bdod),
  };
  const prev = couples.get(key);
  // Keep the richest record for a couple: an explicit cause beats none, an end date beats none.
  if (!prev || (!prev.cause && rec.cause) || (!prev.end && rec.end)) couples.set(key, rec);
}
const all = [...couples.values()];
log(`\nstatements ${rows.length.toLocaleString()} -> distinct couples ${all.length.toLocaleString()}`);

// ── validate the inference against the explicit labels ──────────────────────────────────────────
log(`\nVALIDATING THE INFERENCE against the stated cause, on couples carrying both`);
{
  const both = all.filter((r) => r.cause && inferrable(r));
  const tp = both.filter((r) => DIVORCE.has(r.cause) && inferredDivorce(r)).length;
  const fn = both.filter((r) => DIVORCE.has(r.cause) && !inferredDivorce(r)).length;
  const fp = both.filter((r) => DEATH.has(r.cause) && inferredDivorce(r)).length;
  const tn = both.filter((r) => DEATH.has(r.cause) && !inferredDivorce(r)).length;
  const sep = both.filter((r) => SEPARATIONS.has(r.cause));
  log(`  comparable couples: ${both.length.toLocaleString()}`);
  log(`  stated DIVORCE  : rule agrees ${tp}, rule says death ${fn}   -> recall ${(tp / Math.max(1, tp + fn) * 100).toFixed(1)}%`);
  log(`  stated DEATH    : rule agrees ${tn}, rule says divorce ${fp} -> specificity ${(tn / Math.max(1, tn + fp) * 100).toFixed(1)}%`);
  log(`  precision of the inferred-divorce label: ${(tp / Math.max(1, tp + fp) * 100).toFixed(1)}%`);
  log(`  annulment / separation / repudiation among the comparable: ${sep.length} ` +
    `(rule calls ${sep.filter(inferredDivorce).length} of them divorce, which is arguably right)`);
}

// ── build the balanced set ──────────────────────────────────────────────────────────────────────
const label = (r) => {
  if (r.cause && DIVORCE.has(r.cause)) return { y: 1, how: "stated" };
  // Remarriage overrides an unstated death: if one of them married again while the other was alive,
  // this marriage did not end by death, whatever the absence of an end date might suggest.
  if (separatedByRemarriage.has(r.key)) return { y: 1, how: "remarriage" };
  if (r.cause && DEATH.has(r.cause)) return { y: 0, how: "stated" };
  if (r.cause && SEPARATIONS.has(r.cause)) return null;                 // neither class
  if (inferrable(r)) return { y: inferredDivorce(r) ? 1 : 0, how: "inferred" };
  // No end date and no computable inference: a death was recorded but nothing says the marriage ended
  // before it, so death is the only reading available. Rows with neither are ongoing and excluded.
  if (r.end === null && (r.adod || r.bdod)) return { y: 0, how: "assumed-death" };
  if (r.end !== null && !r.adod && !r.bdod) return null;                 // an end, but nobody known dead
  return null;
};

const labelled = [];
for (const r of all) {
  const l = label(r);
  if (!l) continue;
  if (!r.aDob || !r.bDob) continue;
  labelled.push({ ...r, y: l.y, how: l.how });
}
const pos = labelled.filter((r) => r.y === 1), neg = labelled.filter((r) => r.y === 0);
log(`\nLABELLED: ${labelled.length.toLocaleString()} couples — ${pos.length.toLocaleString()} divorce, ${neg.length.toLocaleString()} death`);
for (const how of ["stated", "remarriage", "inferred", "assumed-death"]) {
  const p = pos.filter((r) => r.how === how).length, n = neg.filter((r) => r.how === how).length;
  if (p || n) log(`  ${how.padEnd(14)}: ${p.toLocaleString()} divorce, ${n.toLocaleString()} death`);
}
const dayBoth = labelled.filter((r) => r.aPrec >= 11 && r.bPrec >= 11);
log(`  with BOTH births known to the day: ${dayBoth.length.toLocaleString()} ` +
  `(${dayBoth.filter((r) => r.y === 1).length.toLocaleString()} divorce)`);

// ── balance, seeded ─────────────────────────────────────────────────────────────────────────────
let SEED = 20260807;
const rnd = () => { SEED ^= SEED << 13; SEED ^= SEED >>> 17; SEED ^= SEED << 5; SEED |= 0; return (SEED >>> 0) / 4294967296; };
const shuffled = (arr) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

const build = (p, n, name) => {
  const k = Math.min(p.length, n.length);
  const out = shuffled([...shuffled(p).slice(0, k), ...shuffled(n).slice(0, k)]);
  writeFileSync(`${OUT}/${name}.json`, JSON.stringify(out));
  log(`  ${name}: ${out.length.toLocaleString()} couples, ${k.toLocaleString()} of each class (exactly 50/50)`);
  return out;
};
log(`\nBALANCED SETS (the divorce class is the binding constraint; deaths subsampled to match)`);
build(pos, neg, "balanced-all-precisions");
build(pos.filter((r) => r.aPrec >= 11 && r.bPrec >= 11), neg.filter((r) => r.aPrec >= 11 && r.bPrec >= 11), "balanced-day-precision");
build(pos.filter((r) => r.how === "stated"), neg.filter((r) => r.how === "stated"), "balanced-stated-cause-only");
