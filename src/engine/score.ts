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
 * So the score is the tradition's own: a total out of 36. It needs no weights from me, it has a
 * stated threshold in use for centuries, and every one of its points is traceable to a rule printed
 * beside it. A later pass removed the aspect layer that had survived alongside it as unscored
 * commentary — a second system beside a scored one invites exactly the question it cannot answer.
 * Ties now break on CONFIDENCE: where two pairs score the same, the one whose dates pin the score
 * down more firmly ranks higher.
 *
 * ── And why the score is shown with a percentile ────────────────────────────────────────────────
 *
 * "22 out of 36, above the traditional pass mark of 18" reads as good news. It is not: 71% of
 * randomly paired dates clear 18, and the median pair scores 21. A threshold that four out of five
 * couples pass tells you almost nothing, and presenting it as an achievement is flattery. So every
 * score is shown against the distribution it actually comes from.
 */

import { type Chart, type Placement, chartAt, julianDay, parseDate } from "./ephemeris";
import { nakshatraOf } from "./nakshatra";
import { type KutaSide, type SymmetricGunaMilan, type KutaKey, gunaMilan } from "./kuta";
import { type BirthSpan, birthSpan } from "./uncertainty";
import { starTitle } from "./interpret";

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

/**
 * The same table with the first test left out (max 35). A score computed without it must be
 * compared against the distribution of scores computed without it — comparing a 35-point score
 * against the 36-point distribution would quietly understate everyone by about half a point.
 * Same tool, same seed, `{exclude:['varna']}`.
 */
export const PERCENTILE_BELOW_NO_VARNA = [
  0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 5, 10, 12, 15, 18, 23, 29, 33, 40,
  46, 51, 55, 60, 68, 72, 80, 88, 94, 96, 97, 98, 99, 100, 100, 100,
];

/** The traditional minimum. Reported honestly: it is a low bar, not a badge. */
export const TRADITIONAL_PASS = 18;
/** Share of random pairs that clear TRADITIONAL_PASS — the context that makes it honest. */
export const PASS_RATE = 71;
/** The median random pair. */
export const MEDIAN_SCORE = 21;

/** Where a score sits among random pairs, 0–100. Linearly interpolated between whole marks.
 *  Pass the table matching how the score was computed — see PERCENTILE_BELOW_NO_VARNA. */
function percentileOf(score: number, table: number[] = PERCENTILE_BELOW): number {
  const max = table.length - 1;
  const clamped = Math.max(0, Math.min(max, score));
  const lo = Math.floor(clamped);
  const hi = Math.min(max, lo + 1);
  const t = clamped - lo;
  return Math.round(table[lo] * (1 - t) + table[hi] * t);
}

type Band = { label: string; note: string; tone: "high" | "mid" | "low" };

/**
 * Bands set on the MEASURED distribution rather than on the tradition's own flattering thresholds.
 * "Above average" means above the median pair, which is what those words normally mean.
 */
export function bandOf(score: number, table: number[] = PERCENTILE_BELOW): Band {
  const p = percentileOf(score, table);
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
  /** Every reading the two dates allow, with probabilities, an expectation and an interval.
   *  Always present: it costs at most sixteen evaluations, and a prediction without an interval
   *  is a prediction pretending to a precision it does not have. */
  distribution: Distribution;
  /** True when the dates settle the answer outright. */
  certain: boolean;
  /** How firmly the two dates pin the answer down, 0…1 — the chance both Moons really were where
   *  the headline says. Used to break ties in the ranking and shown as the "% sure" pill. */
  confidence: number;
  uncertaintyNote: string;
  spanA: BirthSpan;
  spanB: BirthSpan;
};

type Outcome = {
  score: number;
  probability: number;
  labelA: string;
  labelB: string;
};

/**
 * Everything the two dates allow, with probabilities — and the interval that follows from it.
 *
 * This is computed EXACTLY, not sampled. The eight tests read the Moon only through which birth
 * star, sign and mid-sign half it is in, so each person's day partitions into at most four states
 * whose shares ARE their probabilities under a flat prior over birth times. Enumerating the ≤16
 * combinations therefore gives the true distribution.
 *
 * Verified against brute force over the hour grid: agreement with a 240×240 sweep (57,600 hour
 * pairs) is within 0.15 percentage points — and a 24×24 sweep is measurably WORSE than this, off
 * by up to 1.3 points, because sampling 24 hours misses where the boundaries actually fall.
 */
export type Distribution = {
  outcomes: Outcome[];
  /** Probability-weighted mean. The right single number to rank on. */
  expected: number;
  /** The single most likely reading, and how likely it is. */
  modal: Outcome;
  /** The narrowest range of scores covering at least 90% of the probability. */
  interval: { lo: number; hi: number; covers: number };
  /** The full span of what is possible at all. */
  support: { min: number; max: number };
  /** How likely the single most likely reading is. 1 when the dates settle it. */
  confidence: number;
  certain: boolean;
};

/** The narrowest window over the outcomes that holds at least `mass` of the probability. */
function narrowestInterval(sorted: Outcome[], mass: number): { lo: number; hi: number; covers: number } {
  let best = { lo: sorted[0].score, hi: sorted[sorted.length - 1].score, covers: 1 };
  let bestWidth = Infinity;
  for (let i = 0; i < sorted.length; i++) {
    let acc = 0;
    for (let j = i; j < sorted.length; j++) {
      acc += sorted[j].probability;
      if (acc >= mass - 1e-9) {
        const width = sorted[j].score - sorted[i].score;
        if (width < bestWidth) {
          bestWidth = width;
          best = { lo: sorted[i].score, hi: sorted[j].score, covers: acc };
        }
        break;
      }
    }
  }
  return best;
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
 * Score one pair — always with its full distribution.
 *
 * There used to be a `detailed` flag so ranking could skip the distribution. It is gone: the
 * enumeration is at most sixteen cheap evaluations, and two code paths meant the ranking could
 * quietly disagree with the report. Every prediction now carries its interval, everywhere.
 */
export function matchPair(isoA: string, isoB: string, opts: ScoreOptions = {}): Match | null {
  const spanA = birthSpan(isoA);
  const spanB = birthSpan(isoB);
  if (!spanA || !spanB) return null;
  const excluded = opts.exclude ?? [];

  const guna = gunaMilan(sideFrom(spanA.chart), sideFrom(spanB.chart));
  // A score computed without a test must be ranked against the distribution computed without it.
  const table = excluded.includes("varna") ? PERCENTILE_BELOW_NO_VARNA : PERCENTILE_BELOW;

  // Enumerate every reading the two dates allow. Each person's day holds at most four (birth star,
  // sign, mid-sign half) states; each state's share of the day IS its probability under a flat
  // prior over birth times, so the joint over ≤16 combinations is the exact distribution.
  const a = parseDate(isoA)!, b = parseDate(isoB)!;
  const raw: Outcome[] = [];
  for (const sa of spanA.states) {
    const ca = withMoonAt(spanA.chart, julianDay(a.y, a.m, a.d, (sa.fromHour + sa.toHour) / 2));
    for (const sb of spanB.states) {
      const cb = withMoonAt(spanB.chart, julianDay(b.y, b.m, b.d, (sb.fromHour + sb.toHour) / 2));
      raw.push({
        score: scoreOf(gunaMilan(sideFrom(ca), sideFrom(cb)), excluded),
        probability: sa.share * sb.share,
        labelA: `${starTitle(sa.nakshatra.index)} · ${sa.rasiName}`,
        labelB: `${starTitle(sb.nakshatra.index)} · ${sb.rasiName}`,
      });
    }
  }

  // Merge only rows that are the SAME READING — same score AND the same two labels. Merging on
  // score alone once glued genuinely different readings under one row's labels with their combined
  // probability, so the table named the wrong reading with an inflated chance.
  const merged = new Map<string, Outcome>();
  for (const o of raw) {
    const key = `${o.score.toFixed(3)}|${o.labelA}|${o.labelB}`;
    const prev = merged.get(key);
    if (prev) prev.probability += o.probability;
    else merged.set(key, { ...o });
  }
  const outcomes = [...merged.values()].sort((x, y) => y.probability - x.probability);
  const byScore = [...outcomes].sort((x, y) => x.score - y.score);
  const scores = byScore.map((o) => o.score);

  const expected = outcomes.reduce((sum, o) => sum + o.score * o.probability, 0);
  const modal = outcomes[0];
  const distribution: Distribution = {
    outcomes,
    expected,
    modal,
    interval: narrowestInterval(byScore, 0.9),
    support: { min: scores[0], max: scores[scores.length - 1] },
    confidence: modal.probability,
    certain: outcomes.length === 1,
  };

  return {
    score: modal.score,
    maxScore: 36 - excluded.reduce((sum, k) => sum + (guna.kutas.find((x) => x.key === k)?.maxPoints ?? 0), 0),
    percentile: percentileOf(expected, table),
    band: bandOf(expected, table),
    guna,
    distribution,
    certain: distribution.certain,
    confidence: modal.probability,
    uncertaintyNote: uncertaintyNote(spanA, spanB, distribution),
    spanA, spanB,
  };
}

/** Trim a trailing .0 — half points are real, "18.0" reads like a rounding artefact. */
const fmt = (n: number) => (n % 1 === 0 ? String(n) : n.toFixed(1));

function describeStates(span: BirthSpan): string {
  if (span.stable) return `stayed in ${starTitle(span.likeliest.nakshatra.index)} all day`;
  // Name the sign too when the birth star alone would repeat — the Moon can change sign while
  // staying in one birth star, and "Punarvasu, then Punarvasu" reads as a bug rather than a fact.
  const names = span.states.map((s) => s.nakshatra.index);
  const ambiguous = names.some((n, i) => names.indexOf(n) !== i);
  return span.states
    .map((s) => `${starTitle(s.nakshatra.index)}${ambiguous ? ` in ${s.rasiName}` : ""} ` +
      `(${Math.round(s.share * 100)}% of the day)`)
    .join(", then ");
}

function uncertaintyNote(a: BirthSpan, b: BirthSpan, dist: Distribution): string {
  if (a.stable && b.stable) {
    return "Both Moons stay in one birth star and one sign for the whole of their birth day, so not " +
      "knowing the time of day changes nothing here. This is as firm as a reading from dates alone gets.";
  }
  const moving = [!a.stable && "the first", !b.stable && "the second"].filter(Boolean).join(" and ");
  const detail = [
    !a.stable ? `The first person's Moon ${describeStates(a)}.` : "",
    !b.stable ? `The second person's Moon ${describeStates(b)}.` : "",
  ].filter(Boolean).join(" ");
  const rangeText = dist.certain ? "" :
    ` Across every time of day the two dates allow, the score runs from ${fmt(dist.support.min)} ` +
    `to ${fmt(dist.support.max)}; nine times in ten it lands between ${fmt(dist.interval.lo)} ` +
    `and ${fmt(dist.interval.hi)}.`;
  return `Without knowing the time of day, ${moving} Moon could have been in more than one birth ` +
    `star, and every one of the eight tests reads the Moon. ${detail}${rangeText}`;
}

// ── ranking ─────────────────────────────────────────────────────────────────────────────────────

type RankedMatch<T> = { other: T; match: Match; score: number };

/**
 * Rank everyone against one person.
 *
 * Sorted by score, then — where two pairs score the same — by how firmly the dates pin that score
 * down, so a result the dates settle outranks one that merely might be true. Both keys are
 * symmetric, so this list agrees with everyone else's about any shared pair.
 */
export function rankAgainst<T extends { id: string; birthday: string }>(
  self: T, others: T[], opts: ScoreOptions = {},
): RankedMatch<T>[] {
  const out: RankedMatch<T>[] = [];
  for (const other of others) {
    if (other.id === self.id) continue;
    const match = matchPair(self.birthday, other.birthday, opts);
    if (match) out.push({ other, match, score: match.distribution.expected });
  }
  // Rank on the EXPECTED score — the mean over every birth time the dates allow — because that is
  // the right summary of a distribution. Ties break toward the tighter interval, so a settled
  // reading outranks a merely-possible one.
  return out.sort((x, y) =>
    y.score - x.score ||
    (x.match.distribution.interval.hi - x.match.distribution.interval.lo) -
    (y.match.distribution.interval.hi - y.match.distribution.interval.lo));
}

