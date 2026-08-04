/**
 * synastry.ts — the shared vocabulary of laying two charts over each other.
 *
 * This file used to hold a whole second system: every connection between two charts, each with a
 * probability computed in closed form from a difference of two uniforms and checked against a
 * 240×240 brute-force sweep. It worked, it was verified to a fraction of a percentage point, and
 * it is gone — because affinity.ts now answers the same question better. That model reads the same
 * angles, weights each by how firmly the two dates pin it down, and produces a number the parts add
 * up to exactly. Keeping the older list beside it would have put two overlapping accounts of the
 * same thing on one page, which is the failure this project has already made once.
 *
 * What survives is what more than one thing needs: which bodies are read, what each one stands for
 * in plain words, the five angles and how to say them, the 24×24 grid of possible birth hours, and
 * the shape a quantity measured across those 576 charts comes back in.
 */

import { type Body, julianDay, parseDate, siderealLongitude } from "./ephemeris";

/** The seven bodies a date of birth can say something personal about. Uranus, Neptune and Pluto are
 *  drawn on the charts but never scored: they hold one sign for 7–30 years, so a contact with one
 *  is shared by everybody born in that window — a fact about a generation, not about two people. */
export const PERSONAL: Body[] = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"];

/** What each body is taken to stand for, as a phrase that finishes "…, and …". Plain English: no
 *  reader needs to know what a body is said to rule to follow a sentence built out of these. */
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

/** The five angles this page reads, named in plain words rather than by their traditional terms.
 *  Their VALENCES live in affinity.ts, because that is where the scoring is. */
export const ASPECTS: { kind: string; degrees: number; joins: string; means: string }[] = [
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

/** Hours in a day, so the grid of possible birth times is 24 × 24 = 576 charts per pair. */
export const GRID = 24;

/** A quantity measured across all 576 charts. `lo`/`hi` are the 5th and 95th values, so the band
 *  holds nine readings in ten without assuming the spread is bell-shaped — it usually is not. */
export type Spread = { mean: number; sd: number; lo: number; hi: number; min: number; max: number };

/**
 * Each body's sidereal longitude at the midpoint of each of the 24 hours of a birth day.
 *
 * One honesty note that travels with this everywhere: a birth date is a LOCAL date and we are not
 * told the place, so this reads it as a universal-time day. A real local day can begin as much as
 * 12 hours before, or 14 after, the one measured here.
 */
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
