/**
 * score.ts — the two instruments, combined into one number, with the working kept.
 *
 * ArtaMatch runs two INDEPENDENT compatibility instruments over the same sidereal positions:
 *
 *   1. GUNA MILAN (Ashtakoota) — the canonical Vedic system, 36 points across eight tests, computed
 *      almost entirely from the two Moons. This is the sidereal instrument proper, and it is the one
 *      a date of birth can actually feed.
 *   2. SYNASTRY — the inter-chart aspect picture, weighted for relationship relevance, giving an
 *      EASE reading (does this flow) and a CHARGE reading (is there anything there at all).
 *
 * They are kept separate on screen because they measure different things and can honestly disagree.
 * The combined number exists because the request was for a ranking, and a ranking needs one number.
 *
 * WEIGHTS, AND WHY. Guna Milan carries 60%: it is the sidereal system this tool is built on, it is
 * the most robust to date-only input, and it is the one with 1,500 years of stated rules rather than
 * a weighting somebody chose. Ease carries 30%. Charge carries only 10% — a charged connection is
 * not the same as a compatible one, and letting intensity dominate would rank the most turbulent
 * pairings highest. These are stated here rather than buried so anyone can disagree with them
 * specifically, and every component is reported separately so the blend can be ignored entirely.
 */

import { type Chart, type Placement, chartAt, julianDay, parseDate, SIGNS } from "./ephemeris";
import { nakshatraOf } from "./nakshatra";
import { type KutaSide, type SymmetricGunaMilan, gunaMilan } from "./kuta";
import { type SynastrySummary, summariseSynastry } from "./synastry";
import { type BirthSpan, birthSpan } from "./uncertainty";

export const WEIGHT_GUNA = 0.60;
export const WEIGHT_EASE = 0.30;
export const WEIGHT_CHARGE = 0.10;

function sideFrom(chart: Chart): KutaSide {
  const moon = chart.byBody.Moon;
  return {
    moonLon: moon.lon,
    nakshatra: nakshatraOf(moon.lon).info,
    rasi: moon.sign,
    degInSign: moon.deg,
    marsLon: chart.byBody.Mars.lon,
    venusLon: chart.byBody.Venus.lon,
  };
}

export type MatchComponents = {
  guna: SymmetricGunaMilan;
  synastry: SynastrySummary;
  /** 0…100 */
  gunaScore: number;
  easeScore: number;
  chargeScore: number;
  overall: number;
};

function componentsFor(chartA: Chart, chartB: Chart): MatchComponents {
  const guna = gunaMilan(sideFrom(chartA), sideFrom(chartB));
  const synastry = summariseSynastry(chartA, chartB);
  const gunaScore = (guna.total / guna.maxTotal) * 100;
  const overall =
    WEIGHT_GUNA * gunaScore + WEIGHT_EASE * synastry.easeScore + WEIGHT_CHARGE * synastry.chargeScore;
  return {
    guna, synastry, gunaScore,
    easeScore: synastry.easeScore,
    chargeScore: synastry.chargeScore,
    overall,
  };
}

export type Band = { min: number; max: number; spread: number; certain: boolean };

export type Match = {
  /** The headline reading, taken at 12:00 UT on both sides — the single best point estimate. */
  components: MatchComponents;
  overall: number;
  /** The range the overall score takes across every birth time the two dates allow. Present only on
   *  a full (detailed) evaluation. */
  band: Band | null;
  gunaBand: Band | null;
  /** True when the answer does not depend on the unknown birth times at all. */
  certain: boolean;
  /** Plain-language account of what the missing clocks cost, or "" when they cost nothing. */
  uncertaintyNote: string;
  spanA: BirthSpan;
  spanB: BirthSpan;
};

/** Substitute a Moon longitude into a chart — everything except the Moon moves so little in a day
 *  that noon is a fine estimate for it, while the Moon is the entire question. */
function withMoonAt(chart: Chart, jd: number): Chart {
  const moonChart = chartAt(jd, ["Moon"]);
  const moon = moonChart.byBody.Moon;
  const placements = chart.placements.map((p) => (p.body === "Moon" ? moon : p));
  const byBody = { ...chart.byBody, Moon: moon } as Record<Placement["body"], Placement>;
  return { ...chart, placements, byBody };
}

/** Evenly spaced sample instants across a birth day, always including noon. */
function sampleHours(steps: number): number[] {
  return Array.from({ length: steps }, (_, i) => (i * 24) / (steps - 1));
}

/** A full report samples every three hours on each side — 81 birth-time combinations. Ranking uses
 *  only the noon estimate, because a list of 50 people is 1,225 pairs and the band is reported
 *  separately anyway. The headline number is identical either way. */
const DETAIL_STEPS = 9;

/**
 * Score one pair.
 *
 * `detailed` controls whether the uncertainty band is computed. Ranking a list evaluates only the
 * noon estimate (one evaluation per pair); opening a single report evaluates the 9×9 grid of birth
 * times so the band is real rather than asserted. The headline number is identical either way.
 */
export function matchPair(isoA: string, isoB: string, detailed = false): Match | null {
  const spanA = birthSpan(isoA);
  const spanB = birthSpan(isoB);
  if (!spanA || !spanB) return null;

  const components = componentsFor(spanA.chart, spanB.chart);

  if (!detailed) {
    return {
      components, overall: components.overall, band: null, gunaBand: null,
      certain: spanA.stable && spanB.stable,
      uncertaintyNote: uncertaintyNote(spanA, spanB, null),
      spanA, spanB,
    };
  }

  const hours = sampleHours(DETAIL_STEPS);
  const a = parseDate(isoA)!, b = parseDate(isoB)!;
  const chartsA = hours.map((h) => withMoonAt(spanA.chart, julianDay(a.y, a.m, a.d, h)));
  const chartsB = hours.map((h) => withMoonAt(spanB.chart, julianDay(b.y, b.m, b.d, h)));

  let minO = Infinity, maxO = -Infinity, minG = Infinity, maxG = -Infinity;
  for (const ca of chartsA) {
    for (const cb of chartsB) {
      const c = componentsFor(ca, cb);
      if (c.overall < minO) minO = c.overall;
      if (c.overall > maxO) maxO = c.overall;
      if (c.guna.total < minG) minG = c.guna.total;
      if (c.guna.total > maxG) maxG = c.guna.total;
    }
  }

  const band: Band = { min: minO, max: maxO, spread: maxO - minO, certain: maxO - minO < 0.5 };
  const gunaBand: Band = { min: minG, max: maxG, spread: maxG - minG, certain: maxG - minG < 1e-9 };

  return {
    components, overall: components.overall, band, gunaBand,
    certain: gunaBand.certain && band.certain,
    uncertaintyNote: uncertaintyNote(spanA, spanB, gunaBand),
    spanA, spanB,
  };
}

function describeStates(span: BirthSpan): string {
  if (span.stable) return `stays in ${span.likeliest.nakshatra.name} all day`;
  // Name the rāśi too whenever the birth star alone would repeat — the Moon can change rāśi while
  // staying in one nakshatra, and "Punarvasu, then Punarvasu" reads as a bug rather than a fact.
  const names = span.states.map((s) => s.nakshatra.name);
  const ambiguous = names.some((n, i) => names.indexOf(n) !== i);
  return span.states
    .map((s) => `${s.nakshatra.name}${ambiguous ? ` in ${s.rasiName}` : ""} ` +
      `(${Math.round(s.share * 100)}% of the day)`)
    .join(", then ");
}

function uncertaintyNote(a: BirthSpan, b: BirthSpan, gunaBand: Band | null): string {
  if (a.stable && b.stable) {
    return "Both Moons stay in one birth star and one rāśi for the whole of their birth day, so " +
      "the missing birth times change nothing here. This reading is as firm as a dated chart gets.";
  }
  const moving = [!a.stable && "the first", !b.stable && "the second"].filter(Boolean).join(" and ");
  const detail = [
    !a.stable ? `First person's Moon: ${describeStates(a)}.` : "",
    !b.stable ? `Second person's Moon: ${describeStates(b)}.` : "",
  ].filter(Boolean).join(" ");
  const bandText = gunaBand && !gunaBand.certain
    ? ` Across every birth time the two dates allow, Guna Milan ranges from ${gunaBand.min.toFixed(1)} ` +
      `to ${gunaBand.max.toFixed(1)} of 36.`
    : "";
  return `Without a birth time, ${moving} Moon could be in more than one birth star on that date, ` +
    `and six of the eight kutas are read off the Moon. ${detail}${bandText}`;
}

// ── ranking ─────────────────────────────────────────────────────────────────────────────────────

export type RankedMatch<T> = {
  other: T;
  match: Match;
  overall: number;
};

/** Rank everyone against one person. Symmetric scoring means this list agrees with everyone
 *  else's list about any shared pair. */
export function rankAgainst<T extends { id: string; birthday: string }>(
  self: T, others: T[],
): RankedMatch<T>[] {
  const out: RankedMatch<T>[] = [];
  for (const other of others) {
    if (other.id === self.id) continue;
    const match = matchPair(self.birthday, other.birthday);
    if (!match) continue;
    out.push({ other, match, overall: match.overall });
  }
  return out.sort((x, y) => y.overall - x.overall);
}

export type MatrixCell = { a: string; b: string; overall: number | null };

/** Every pair in a group — the full matrix, computed once for the grid view. */
export function pairMatrix<T extends { id: string; birthday: string }>(people: T[]): MatrixCell[] {
  const out: MatrixCell[] = [];
  for (let i = 0; i < people.length; i++) {
    for (let j = i + 1; j < people.length; j++) {
      const m = matchPair(people[i].birthday, people[j].birthday);
      out.push({ a: people[i].id, b: people[j].id, overall: m ? m.overall : null });
    }
  }
  return out;
}

/** A short, plain summary of where a score sits. */
export function overallBand(score: number): { label: string; tone: "high" | "mid" | "low" } {
  if (score >= 72) return { label: "Strong", tone: "high" };
  if (score >= 58) return { label: "Good", tone: "high" };
  if (score >= 45) return { label: "Mixed", tone: "mid" };
  if (score >= 32) return { label: "Difficult", tone: "low" };
  return { label: "Poor", tone: "low" };
}

export const signName = (i: number) => SIGNS[i];
