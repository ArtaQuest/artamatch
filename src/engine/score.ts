/**
 * score.ts — one score, and what it is worth.
 *
 * ── Why there is only one number now ────────────────────────────────────────────────────────────
 *
 * An earlier version of this file reported a 0–100 figure blended 60% from the traditional
 * eight-test score, 30% from an "ease" index and 10% from a "pull" index. Three things killed it,
 * all measured rather than argued (tools/calibrate.mjs):
 *
 *   · Ranking by the blend correlated with ranking by the traditional score alone at ρ = 0.954.
 *     The two invented components moved almost nothing while adding two unverifiable numbers to
 *     the page and a set of weights nobody could check.
 *   · The "pull" index barely varied — 10th percentile 56, 90th percentile 75. A measurement that
 *     returns roughly the same answer for everybody is not a measurement.
 *   · A 0–100 scale invited comparison to marks out of a hundred. 59 was the median. People read
 *     59 as a fail; it is exactly average.
 *
 * So the score is now the tradition's own: a total out of 36. It needs no weights from me, it has
 * a stated threshold that has been in use for centuries, and every one of its points is traceable
 * to a rule printed beside it. What was "ease" survives as a tie-break and as plain COUNTS of
 * helping and rubbing connections — numbers a reader can verify against the list underneath.
 *
 * ── And why the score is shown with a percentile ────────────────────────────────────────────────
 *
 * "22 out of 36, above the traditional pass mark of 18" reads as good news. It is not: 71% of
 * randomly paired dates clear 18, and the median pair scores 21. A threshold that four out of five
 * couples pass tells you almost nothing, and presenting it as an achievement is flattery. So every
 * score is shown against the distribution it actually comes from.
 */

import { type Chart, type Placement, chartAt, julianDay, parseDate, SIGNS } from "./ephemeris";
import { nakshatraOf } from "./nakshatra";
import { type KutaSide, type SymmetricGunaMilan, type KutaKey, gunaMilan } from "./kuta";
import { type SynAspect, summariseSynastry } from "./synastry";
import { type BirthSpan, birthSpan } from "./uncertainty";

/**
 * Share of random pairs scoring BELOW each whole mark, 0…36. Measured over 20,000 random date
 * pairs spanning 1930–2010 (tools/calibrate.mjs, deterministic seed, reproducible).
 *
 * This is what makes a score mean something. Without it, 22/36 is a number in a vacuum.
 */
export const PERCENTILE_BELOW = [
  0, 0, 0, 0, 1, 1, 2, 2, 2, 3, 3, 5, 7, 11, 13, 16, 20, 24, 29, 35,
  42, 48, 52, 58, 62, 69, 76, 83, 89, 94, 96, 98, 99, 99, 100, 100, 100,
];

/** The traditional minimum. Reported honestly: it is a low bar, not a badge. */
export const TRADITIONAL_PASS = 18;
/** Share of random pairs that clear TRADITIONAL_PASS — the context that makes it honest. */
export const PASS_RATE = 71;
/** The median random pair. */
export const MEDIAN_SCORE = 21;

/** Where a score sits among random pairs, 0–100. Linearly interpolated between whole marks. */
export function percentileOf(score: number): number {
  const clamped = Math.max(0, Math.min(36, score));
  const lo = Math.floor(clamped);
  const hi = Math.min(36, lo + 1);
  const t = clamped - lo;
  return Math.round(PERCENTILE_BELOW[lo] * (1 - t) + PERCENTILE_BELOW[hi] * t);
}

export type Band = { label: string; note: string; tone: "high" | "mid" | "low" };

/**
 * Bands set on the MEASURED distribution rather than on the tradition's own flattering thresholds.
 * "Above average" means above the median pair, which is what those words normally mean.
 */
export function bandOf(score: number): Band {
  const p = percentileOf(score);
  if (p >= 95) return { label: "Unusually high", tone: "high", note: "Higher than about 95 in 100 random pairs. Scores like this are rare." };
  if (p >= 75) return { label: "High", tone: "high", note: "In the top quarter of random pairs." };
  if (p >= 50) return { label: "Above average", tone: "mid", note: "Above the middle of the range, where half of all pairs sit." };
  if (p >= 25) return { label: "Below average", tone: "mid", note: "Below the middle of the range, but well inside the ordinary spread." };
  return { label: "Low", tone: "low", note: "In the bottom quarter of random pairs." };
}

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

/** The connections between two charts, described in things a reader can count. */
export type Connections = {
  /** Every connection found, strongest first. */
  all: SynAspect[];
  /** The handful worth leading with. */
  headline: SynAspect[];
  /** How many of the significant ones help, and how many rub. Countable against the list. */
  helps: number;
  rubs: number;
  /** helps − rubs. Used only to break ties in the ranking, never shown as a score. */
  lean: number;
};

/** Tests that can be switched off, with the reason a reader might want to. */
export const OPTIONAL_TESTS: { key: KutaKey; label: string; why: string }[] = [
  {
    key: "varna",
    label: "the first test",
    why: "It ranks four temperaments in a fixed order taken from an old caste hierarchy, and scores " +
      "only when the first person's sits at or above the second's. It is worth one point of " +
      "thirty-six. Leave it out if you would rather not have it counted.",
  },
];

export type Match = {
  /** THE score: the traditional total out of 36. */
  score: number;
  maxScore: number;
  /** Where that sits among random pairs. */
  percentile: number;
  band: Band;
  guna: SymmetricGunaMilan;
  connections: Connections;
  /** Present only on a full evaluation: every reading the two dates allow, with probabilities. */
  distribution: Distribution | null;
  /** The lowest and highest the score could be, given the unknown birth times. */
  range: { min: number; max: number } | null;
  /** True when the dates settle the answer outright. */
  certain: boolean;
  uncertaintyNote: string;
  spanA: BirthSpan;
  spanB: BirthSpan;
};

export type Outcome = {
  score: number;
  probability: number;
  labelA: string;
  labelB: string;
};

export type Distribution = {
  outcomes: Outcome[];
  /** How likely the headline reading is. 1 when the dates settle it. */
  confidence: number;
  certain: boolean;
};

function connectionsFrom(A: Chart, B: Chart): Connections {
  const s = summariseSynastry(A, B);
  // Count only the significant ones — the minor angles are shown but are too slight to count as
  // "a thing between them", and padding the tally with them would make the number unverifiable.
  const significant = s.aspects.filter((x) => x.def.major && x.weight >= 0.25);
  const helps = significant.filter((x) => x.valence > 0.15).length;
  const rubs = significant.filter((x) => x.valence < -0.15).length;
  return { all: s.aspects, headline: s.headline, helps, rubs, lean: helps - rubs };
}

function scoreOf(guna: SymmetricGunaMilan, excluded: KutaKey[]): number {
  if (excluded.length === 0) return guna.total;
  return guna.kutas.filter((k) => !excluded.includes(k.key)).reduce((s, k) => s + k.points, 0);
}

/** Substitute a Moon longitude into a chart — everything except the Moon moves so little in a day
 *  that one instant serves for all of it, while the Moon is the entire question. */
function withMoonAt(chart: Chart, jd: number): Chart {
  const moon = chartAt(jd, ["Moon"]).byBody.Moon;
  const placements = chart.placements.map((p) => (p.body === "Moon" ? moon : p));
  const byBody = { ...chart.byBody, Moon: moon } as Record<Placement["body"], Placement>;
  return { ...chart, placements, byBody };
}

export type ScoreOptions = { exclude?: KutaKey[] };

/**
 * Score one pair.
 *
 * `detailed` controls whether the probability distribution is worked out. Ranking a list evaluates
 * only the single best estimate; opening a report enumerates every reading the two dates allow.
 * The headline number is identical either way.
 */
export function matchPair(isoA: string, isoB: string, detailed = false, opts: ScoreOptions = {}): Match | null {
  const spanA = birthSpan(isoA);
  const spanB = birthSpan(isoB);
  if (!spanA || !spanB) return null;
  const excluded = opts.exclude ?? [];

  const guna = gunaMilan(sideFrom(spanA.chart), sideFrom(spanB.chart));
  const connections = connectionsFrom(spanA.chart, spanB.chart);
  const score = scoreOf(guna, excluded);

  const base = {
    score, maxScore: 36 - excluded.reduce((s, k) => s + (guna.kutas.find((x) => x.key === k)?.maxPoints ?? 0), 0),
    percentile: percentileOf(score), band: bandOf(score), guna, connections, spanA, spanB,
  };

  if (!detailed) {
    return {
      ...base, distribution: null, range: null,
      certain: spanA.stable && spanB.stable,
      uncertaintyNote: uncertaintyNote(spanA, spanB, null),
    };
  }

  // The eight tests depend on the Moon ONLY through which birth star and sign it is in. Each day
  // holds at most four such states, and each state's share of the day IS its probability under a
  // flat prior over birth times — so the possible readings are enumerated exactly, not sampled.
  const a = parseDate(isoA)!, b = parseDate(isoB)!;
  const raw: Outcome[] = [];
  for (const sa of spanA.states) {
    const ca = withMoonAt(spanA.chart, julianDay(a.y, a.m, a.d, (sa.fromHour + sa.toHour) / 2));
    for (const sb of spanB.states) {
      const cb = withMoonAt(spanB.chart, julianDay(b.y, b.m, b.d, (sb.fromHour + sb.toHour) / 2));
      raw.push({
        score: scoreOf(gunaMilan(sideFrom(ca), sideFrom(cb)), excluded),
        probability: sa.share * sb.share,
        labelA: `${sa.nakshatra.name} in ${sa.rasiName}`,
        labelB: `${sb.nakshatra.name} in ${sb.rasiName}`,
      });
    }
  }

  // Merge readings that come out the same, so one score is reported once with its total chance.
  const merged = new Map<string, Outcome>();
  for (const o of raw) {
    const prev = merged.get(o.score.toFixed(3));
    if (prev) prev.probability += o.probability;
    else merged.set(o.score.toFixed(3), { ...o });
  }
  const outcomes = [...merged.values()].sort((x, y) => y.probability - x.probability);
  const scores = outcomes.map((o) => o.score);

  return {
    ...base,
    distribution: { outcomes, confidence: outcomes[0]?.probability ?? 1, certain: outcomes.length === 1 },
    range: { min: Math.min(...scores), max: Math.max(...scores) },
    certain: outcomes.length === 1,
    uncertaintyNote: uncertaintyNote(spanA, spanB, outcomes.length === 1 ? null : { min: Math.min(...scores), max: Math.max(...scores) }),
  };
}

function describeStates(span: BirthSpan): string {
  if (span.stable) return `stayed in ${span.likeliest.nakshatra.name} all day`;
  // Name the sign too when the birth star alone would repeat — the Moon can change sign while
  // staying in one birth star, and "Punarvasu, then Punarvasu" reads as a bug rather than a fact.
  const names = span.states.map((s) => s.nakshatra.name);
  const ambiguous = names.some((n, i) => names.indexOf(n) !== i);
  return span.states
    .map((s) => `${s.nakshatra.name}${ambiguous ? ` in ${s.rasiName}` : ""} ` +
      `(${Math.round(s.share * 100)}% of the day)`)
    .join(", then ");
}

function uncertaintyNote(a: BirthSpan, b: BirthSpan, range: { min: number; max: number } | null): string {
  if (a.stable && b.stable) {
    return "Both Moons stay in one birth star and one sign for the whole of their birth day, so not " +
      "knowing the time of day changes nothing here. This is as firm as a reading from dates alone gets.";
  }
  const moving = [!a.stable && "the first", !b.stable && "the second"].filter(Boolean).join(" and ");
  const detail = [
    !a.stable ? `The first person's Moon ${describeStates(a)}.` : "",
    !b.stable ? `The second person's Moon ${describeStates(b)}.` : "",
  ].filter(Boolean).join(" ");
  const rangeText = range
    ? ` Across every time of day the two dates allow, the score runs from ${range.min.toFixed(1)} ` +
      `to ${range.max.toFixed(1)} out of 36.`
    : "";
  return `Without knowing the time of day, ${moving} Moon could have been in more than one birth ` +
    `star, and six of the eight tests read only where the Moon was. ${detail}${rangeText}`;
}

// ── ranking ─────────────────────────────────────────────────────────────────────────────────────

export type RankedMatch<T> = { other: T; match: Match; score: number };

/**
 * Rank everyone against one person.
 *
 * Sorted by the traditional score, then by whether the connections between them lean helpful. Both
 * halves are symmetric, so this list agrees with everyone else's about any shared pair.
 */
export function rankAgainst<T extends { id: string; birthday: string }>(
  self: T, others: T[], opts: ScoreOptions = {},
): RankedMatch<T>[] {
  const out: RankedMatch<T>[] = [];
  for (const other of others) {
    if (other.id === self.id) continue;
    const match = matchPair(self.birthday, other.birthday, false, opts);
    if (match) out.push({ other, match, score: match.score });
  }
  return out.sort((x, y) =>
    y.score - x.score || y.match.connections.lean - x.match.connections.lean);
}

export const signName = (i: number) => SIGNS[i];
