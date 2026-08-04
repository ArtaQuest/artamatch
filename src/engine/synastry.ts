/**
 * synastry.ts — where two sidereal charts touch, and how sure each touch is.
 *
 * Synastry is the old practice of laying one person's chart over another's and reading the ANGLES
 * between their planets. It is the second thing this page does with a pair of dates, and it is
 * deliberately kept separate from the score: the eight tests read only the two Moons, and nothing
 * here adds a point to them.
 *
 * ── Which bodies, and why not all of them ───────────────────────────────────────────────────────
 *
 * Seven: the Sun, Moon, Mercury, Venus, Mars, Jupiter and Saturn. Uranus, Neptune and Pluto are
 * left out on purpose. Pluto spends 12–30 years in one sign, so "your Pluto is opposite my Sun" is
 * true of everybody born in a two-decade window — it is a fact about a generation, not about two
 * people. They are still drawn on the chart, because they are in the sky and leaving them out
 * would be a different kind of lie; they simply do not make connections here.
 *
 * ── How close counts as close ───────────────────────────────────────────────────────────────────
 *
 * There is no agreed rule, and no measurement that could settle it — this is a convention, and it
 * is stated on the page as one: 8° when the Sun or the Moon is involved, 6° otherwise, for every
 * angle. Wider orbs for the two brightest bodies is the commonest convention in use.
 *
 * ── The part that is actually ours: 576 charts, not one ─────────────────────────────────────────
 *
 * A birth DATE does not fix a planet's longitude; it fixes an ARC the planet crossed that day. So
 * "these two are a quarter-circle apart" is not a fact — it is a fact with a spread.
 *
 * `synastryGrid` therefore draws BOTH charts 24 × 24 = 576 times, once for every combination of the
 * two unknown birth hours, and reports every quantity as a mean, a standard deviation and a 5th-to
 * -95th band: the angle between each pair of bodies, how far that angle sits from the exact one,
 * and even how many connections the two charts have at all. Nothing on the synastry section is a
 * bare number.
 *
 * A CLOSED FORM is kept below (`aspectProbability`) and is not used to render anything: it exists
 * to check the grid. Under a flat prior over birth times each longitude is nearly uniform over its
 * day's arc, so the angle between two of them is a DIFFERENCE OF TWO UNIFORMS — a trapezoid with an
 * exact area. tests/synastry.test.ts holds the grid, the closed form and a 240×240 brute-force
 * sweep against each other; all three agree to a fraction of a percentage point, which is what
 * makes the simple, explainable method the one worth showing.
 */

import { type Body, angleDiff, julianDay, parseDate, siderealLongitude, SIGNS } from "./ephemeris";

/** The seven bodies a date of birth can say something personal about. */
export const PERSONAL: Body[] = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"];

/** What each body is taken to stand for, as a phrase that finishes "…, and …". Plain English: no
 *  reader needs to know what a planet is said to rule to follow a sentence built out of these. */
export const STANDS_FOR: Record<string, string> = {
  Sun: "what {name} is aiming at",
  Moon: "how {name} feels",
  Mercury: "how {name} thinks and talks",
  Venus: "what {name} finds lovely",
  Mars: "how {name} goes after what they want",
  Jupiter: "where {name} takes chances",
  Saturn: "what {name} takes seriously",
};

export const standsFor = (body: Body, name: string) =>
  (STANDS_FOR[body] ?? "").replace("{name}", name);

/** The five angles this page reads, named in plain words rather than by their traditional terms. */
export type AspectKind = "together" | "sixth" | "quarter" | "third" | "opposite";

export const ASPECTS: { kind: AspectKind; degrees: number; joins: string; means: string }[] = [
  {
    kind: "together", degrees: 0,
    joins: "sits in the same place as",
    means: "These two act as one thing. Whatever stirs one stirs the other, which is as often a " +
      "problem as it is a gift.",
  },
  {
    kind: "sixth", degrees: 60,
    joins: "is a sixth of the way round the sky from",
    means: "A quiet, easy fit. It helps whenever either of them thinks to use it, and it goes " +
      "unnoticed the rest of the time.",
  },
  {
    kind: "quarter", degrees: 90,
    joins: "is a quarter of the way round the sky from",
    means: "This is where the friction is. It is usually also where the interest is — people rarely " +
      "stay curious about someone who never pushes back.",
  },
  {
    kind: "third", degrees: 120,
    joins: "is a third of the way round the sky from",
    means: "This part runs by itself. Neither has to work at it, so neither tends to notice it is " +
      "there.",
  },
  {
    kind: "opposite", degrees: 180,
    joins: "sits directly opposite",
    means: "Each of them does the thing the other does not. That reads as attraction or as " +
      "irritation, and very often as both at once.",
  },
];

/** 8° when the Sun or the Moon is involved, 6° otherwise. A convention, stated as one. */
export const orbFor = (a: Body, b: Body): number =>
  a === "Sun" || a === "Moon" || b === "Sun" || b === "Moon" ? 8 : 6;

/**
 * What a count of connections is worth — measured, over the same 20,000 random pairs the score is
 * calibrated on (tools/calibrate-synastry.mjs, seed 13579).
 *
 * The answer is: nothing. Every pair of dates has somewhere between ten and twenty connections, the
 * median is fifteen, and the count correlates with the eight-test score at 0.03 — which is to say
 * not at all. These two old systems, handed the same two dates, do not agree with each other.
 *
 * This is the fact that lets the synastry section exist without becoming a second scoreboard. The
 * page says it out loud, near the top, and then shows WHICH connections rather than how many. Left
 * unsaid, "you have 19 connections!" would read as a result, and it is not one.
 */
export const CONNECTIONS_MEDIAN = 15;
export const CONNECTIONS_LO = 10;   // 5th percentile of random pairs
export const CONNECTIONS_HI = 20;   // 95th
export const CONNECTIONS_VS_SCORE = 0.03;

// ── the probability ─────────────────────────────────────────────────────────────────────────────

const clamp = (x: number, lo: number, hi: number) => (x < lo ? lo : x > hi ? hi : x);

/**
 * P(X − Y ≤ z) for independent X ~ U(0, p) and Y ~ U(0, q).
 *
 * The area of {x > y + z} inside the p×q rectangle, integrated in one piece: the integrand
 * clamp(p − y − z, 0, p) is flat at p up to y = −z, linear until y = p − z, then zero.
 * Degenerate widths (a planet that barely moves, or is standing still at a turn) are handled
 * explicitly rather than dividing by zero.
 */
export function diffOfUniformsCdf(z: number, p: number, q: number): number {
  const EPS = 1e-12;
  if (p < EPS && q < EPS) return z >= 0 ? 1 : 0;
  if (p < EPS) return 1 - clamp(-z, 0, q) / q;   // X is a point: Z = −Y
  if (q < EPS) return clamp(z, 0, p) / p;        // Y is a point: Z = X
  const y1 = clamp(-z, 0, q);
  const y2 = clamp(p - z, 0, q);
  const above = p * y1 + ((p - z) * (y2 - y1) - (y2 * y2 - y1 * y1) / 2);
  return 1 - above / (p * q);
}

/**
 * One body's day, as STEPS + 1 longitudes at equally spaced instants — a piecewise-linear picture
 * of where it was, unwrapped through 360°.
 *
 * A single straight arc from midnight to midnight is not enough. Mercury near one of its turns
 * decelerates to a standstill and back, so it lingers at one end of its arc and races the other;
 * treating the crossing as even overstated one probability by 1.7 points. Cutting the day into
 * two-hour pieces and taking each piece as even is exact to a rounding error, and costs thirteen
 * ephemeris calls per body instead of two.
 */
export const STEPS = 12;
export type Arc = { body: Body; lon: number; steps: number[]; from: number; to: number; speed: number };

/**
 * Probability that the angle between two arcs lands within `orb` of `target`.
 *
 * Each body's day is a mixture of STEPS equally likely pieces, and within a piece its longitude is
 * uniform. So the angle between them is a mixture of STEPS² differences-of-uniforms, each with an
 * exact area. The arcs are at most ~15° wide (the Moon, at its fastest), so a shifted band can wrap
 * the circle at most once — hence the three-term k loop. Both signs of the target are counted,
 * since "a quarter of the way round" is the same relationship whichever of the two is ahead.
 */
export function aspectProbability(a: Arc, b: Arc, target: number, orb: number): number {
  const targets = target === 0 || target === 180 ? [target] : [target, -target];
  const weight = 1 / ((a.steps.length - 1) * (b.steps.length - 1));
  let total = 0;

  for (let i = 0; i + 1 < a.steps.length; i++) {
    const aLo = Math.min(a.steps[i], a.steps[i + 1]);
    const p = Math.abs(a.steps[i + 1] - a.steps[i]);
    for (let j = 0; j + 1 < b.steps.length; j++) {
      const bLo = Math.min(b.steps[j], b.steps[j + 1]);
      const q = Math.abs(b.steps[j + 1] - b.steps[j]);
      const c = aLo - bLo;
      for (const t of targets) {
        for (let k = -1; k <= 1; k++) {
          const hi = diffOfUniformsCdf(t + 360 * k + orb - c, p, q);
          const lo = diffOfUniformsCdf(t + 360 * k - orb - c, p, q);
          if (hi > lo) total += (hi - lo) * weight;
        }
      }
    }
  }
  return Math.min(1, total);
}

// ── charts and connections ──────────────────────────────────────────────────────────────────────

/** Every body's arc across one birth day, plus its position at the instant the page reads. */
export function arcsFor(iso: string, jdEstimate: number, bodies: Body[] = PERSONAL): Arc[] {
  const d = parseDate(iso);
  if (!d) return [];
  return bodies.map((body) => {
    // Unwrap through 360° step by step: daily motion never exceeds ~15°, so the signed short way
    // round IS the real travel. Taking raw differences would read a midnight-crossing Moon as
    // running 350° backwards and hand the probability a 350°-wide arc.
    const steps: number[] = [siderealLongitude(body, julianDay(d.y, d.m, d.d, 0))];
    for (let i = 1; i <= STEPS; i++) {
      const raw = siderealLongitude(body, julianDay(d.y, d.m, d.d, (i / STEPS) * 24));
      steps.push(steps[i - 1] + angleDiff(raw, steps[i - 1]));
    }
    const lon = siderealLongitude(body, jdEstimate);
    return { body, lon, steps, from: steps[0], to: steps[STEPS], speed: steps[STEPS] - steps[0] };
  });
}

/** Human-readable position, e.g. "12° Aquarius". */
export const atSign = (lon: number) => {
  const s = Math.floor(lon / 30) % 12;
  return `${Math.floor(lon - s * 30)}° ${SIGNS[s]}`;
};

// ── the 24 × 24 grid: the method the page actually reports ──────────────────────────────────────

/** Hours in a day, so the grid is 24 × 24 = 576 charts per pair. */
export const GRID = 24;

/** A quantity measured across all 576 charts. `lo`/`hi` are the 5th and 95th values, so the band
 *  holds nine readings in ten without assuming the spread is bell-shaped — it usually is not. */
export type Spread = { mean: number; sd: number; lo: number; hi: number; min: number; max: number };

function spreadOf(values: number[]): Spread {
  const n = values.length;
  const mean = values.reduce((s, v) => s + v, 0) / n;
  const sd = Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / n);
  const sorted = [...values].sort((a, b) => a - b);
  const at = (p: number) => sorted[Math.min(n - 1, Math.max(0, Math.round((p / 100) * (n - 1))))];
  return { mean, sd, lo: at(5), hi: at(95), min: sorted[0], max: sorted[n - 1] };
}

export type Connection = {
  kind: AspectKind;
  aspect: (typeof ASPECTS)[number];
  bodyA: Body;
  bodyB: Body;
  /** Positions at the instant the page draws the two charts. */
  lonA: number;
  lonB: number;
  orb: number;
  /** The angle between the two bodies, across all 576 charts. */
  separation: Spread;
  /** How far that angle sits from the exact one, across all 576 charts. */
  off: Spread;
  /** Share of the 576 in which the angle really falls inside the orb, 0…1. */
  probability: number;
  /** True when all 576 agree. */
  certain: boolean;
  /**
   * How strong the connection is, 0…1 — the one number the list is ordered by.
   *
   * The average, over all 576 charts, of how close the angle is as a fraction of the orb, counting
   * a chart where it misses as nothing. An angle that is exact in every chart scores 1; one that is
   * exact in half of them and absent in the rest scores about a half; one that only ever scrapes
   * inside the orb scores near zero.
   *
   * Ordering by PROBABILITY alone was tried and thrown away: it is a fact about the planets' speed
   * rather than about the pair, so the six slowest-moving connections always won and the Moon —
   * the most personal body there is, and the one the whole score is built on — could never appear
   * in the list at all. This combines closeness and certainty in one figure without inventing a
   * weight for either.
   */
  strength: number;
};

export type SynastryGrid = {
  connections: Connection[];
  /** How many connections each of the 576 charts had — the honest form of "they have 14". */
  count: Spread;
  /** Every longitude used, [body][hour], for whoever wants to re-do the arithmetic. */
  hoursA: Map<Body, number[]>;
  hoursB: Map<Body, number[]>;
};

/** Each body's sidereal longitude at the midpoint of each of the 24 hours of a birth day. */
export function hourlyLongitudes(iso: string, bodies: Body[] = PERSONAL): Map<Body, number[]> {
  const out = new Map<Body, number[]>();
  const d = parseDate(iso);
  if (!d) return out;
  for (const body of bodies) {
    out.set(body, Array.from({ length: GRID }, (_, h) =>
      siderealLongitude(body, julianDay(d.y, d.m, d.d, h + 0.5))));
  }
  return out;
}

/**
 * Pick the connections worth a paragraph: the strongest, but at most two involving any one planet
 * on either side, so a single busy planet cannot fill the whole list with itself.
 */
export function narrate(connections: Connection[], limit: number): Connection[] {
  const usedA = new Map<Body, number>(), usedB = new Map<Body, number>();
  const out: Connection[] = [];
  for (const c of connections) {
    if (out.length >= limit) break;
    if ((usedA.get(c.bodyA) ?? 0) >= 2 || (usedB.get(c.bodyB) ?? 0) >= 2) continue;
    usedA.set(c.bodyA, (usedA.get(c.bodyA) ?? 0) + 1);
    usedB.set(c.bodyB, (usedB.get(c.bodyB) ?? 0) + 1);
    out.push(c);
  }
  return out;
}

/**
 * Draw both charts 576 times — once for every combination of the two unknown birth hours — and
 * report what varies.
 *
 * This is the whole method, and it is the reason every number on the synastry section carries a
 * give-or-take. A single chart drawn at noon would state "their Moons are 3° apart" as a fact; the
 * grid says "3° apart on average, give or take 6, and inside the orb in 71% of the 576" — which is
 * what a date of birth can actually support.
 *
 * One connection is kept per pair of bodies: the angle that holds in the most of the 576, ties
 * broken by the closest average fit. (The five angles are 30–60° apart and the orbs are 6–8°, so
 * two rarely compete — but a pair of fast Moons can drift across 30°, and then they do.)
 */
export function synastryGrid(isoA: string, isoB: string, bodies: Body[] = PERSONAL): SynastryGrid {
  const hoursA = hourlyLongitudes(isoA, bodies);
  const hoursB = hourlyLongitudes(isoB, bodies);
  const connections: Connection[] = [];
  // Connections per chart, indexed by the same [hourA][hourB] the separations are measured on.
  const perChart = new Array(GRID * GRID).fill(0);

  for (const a of bodies) {
    const la = hoursA.get(a);
    if (!la) continue;
    for (const b of bodies) {
      const lb = hoursB.get(b);
      if (!lb) continue;
      const orb = orbFor(a, b);

      const seps: number[] = [];
      for (let i = 0; i < GRID; i++) {
        for (let j = 0; j < GRID; j++) seps.push(Math.abs(angleDiff(la[i], lb[j])));
      }

      let best: {
        aspect: (typeof ASPECTS)[number]; offs: number[]; hits: boolean[];
        share: number; strength: number;
      } | null = null;
      for (const aspect of ASPECTS) {
        const offs = seps.map((s) => Math.abs(s - aspect.degrees));
        const hits = offs.map((o) => o <= orb);
        const share = hits.filter(Boolean).length / hits.length;
        if (share === 0) continue;
        const strength = offs.reduce((s, o) => s + Math.max(0, 1 - o / orb), 0) / offs.length;
        if (!best || strength > best.strength) best = { aspect, offs, hits, share, strength };
      }
      // Below one chart in twenty this is a coincidence of the grid's corners, not a connection.
      if (!best || best.share < 0.05) continue;

      for (let k = 0; k < best.hits.length; k++) if (best.hits[k]) perChart[k]++;
      connections.push({
        kind: best.aspect.kind, aspect: best.aspect, bodyA: a, bodyB: b, orb,
        lonA: la[12], lonB: lb[12],
        separation: spreadOf(seps),
        off: spreadOf(best.offs),
        probability: best.share,
        certain: best.share > 0.9995,
        strength: best.strength,
      });
    }
  }

  // Strongest first — closeness and certainty in one figure. See `strength` above for why not
  // probability, which merely ranks the planets by how slowly they move.
  connections.sort((x, y) => y.strength - x.strength);
  return { connections, count: spreadOf(perChart), hoursA, hoursB };
}
