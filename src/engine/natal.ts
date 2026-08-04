/**
 * natal.ts — one person's own sidereal chart, and the honest limits of one drawn from a date.
 *
 * ── What a date of birth can and cannot draw ────────────────────────────────────────────────────
 *
 * A full natal chart has three layers: which sign each planet is in, which HOUSE it is in, and
 * which sign was rising. Only the first survives a missing birth time. Houses and the rising sign
 * turn a full circle every 24 hours — the rising sign changes every two hours — so from a date
 * alone they are not approximate, they are unknown. This file draws the layer that survives and
 * the page says plainly that the other two are missing. It does not quietly default them to
 * sunrise, which is the usual dodge.
 *
 * ── Even the surviving layer has edges ──────────────────────────────────────────────────────────
 *
 * A planet near a sign boundary at midnight is in two signs that day. So every body reports the
 * signs it could be in and the SHARE of the day it spent in each — found the exact way, by
 * scanning hourly for a change and bisecting inside the hour that changed, never by sampling.
 *
 * The Moon does this on about two days in five. Everything else does it rarely: Mercury moves at
 * most ~2.2° in a day, Saturn ~0.13°, so their sign is settled unless the date lands on the
 * crossing itself.
 */

import {
  type Body, type Placement, BODIES, SIGNS, chartAt, julianDay, parseDate, siderealLongitude,
} from "./ephemeris";
import { crossing } from "./uncertainty";

/** One sign a body could have been in on a birth day, and how much of the day it held it. */
export type SignChance = { sign: number; signName: string; share: number };

export type NatalBody = {
  body: Body;
  /** Position at the instant the page reads — the middle of the Moon's likeliest stretch. */
  lon: number;
  sign: number;
  signName: string;
  /** Degrees into the sign, 0–30. */
  deg: number;
  /** Appearing to move backwards against the stars, from here. */
  retro: boolean;
  /** Every sign the date allows, largest share first. One entry means the date settles it. */
  chances: SignChance[];
  /** Share of the day spent in the sign shown above, 0…1. */
  certainty: number;
  /** True when the date settles the sign outright. */
  settled: boolean;
};

export type NatalChart = {
  iso: string;
  jd: number;
  bodies: NatalBody[];
  byBody: Record<Body, NatalBody>;
};

const HOURS = 24;

/** Which signs a body occupied across a birth day, with each one's share of the 24 hours. */
function signChances(body: Body, y: number, m: number, d: number): SignChance[] {
  const at = (hour: number) => siderealLongitude(body, julianDay(y, m, d, hour));
  const signAt = (hour: number) => Math.floor(at(hour) / 30) % 12;

  const edges: number[] = [0];
  let prev = signAt(0);
  for (let h = 1; h <= HOURS; h++) {
    const here = signAt(h);
    if (here !== prev) {
      const before = prev;
      edges.push(crossing(h - 1, h, (hour) => signAt(hour) === before));
    }
    prev = here;
  }
  edges.push(HOURS);

  const byIndex = new Map<number, number>();
  for (let i = 0; i < edges.length - 1; i++) {
    const width = edges[i + 1] - edges[i];
    if (width < 1e-6) continue;
    const sign = signAt((edges[i] + edges[i + 1]) / 2);
    byIndex.set(sign, (byIndex.get(sign) ?? 0) + width / HOURS);
  }
  return [...byIndex.entries()]
    .map(([sign, share]) => ({ sign, signName: SIGNS[sign], share }))
    .sort((a, b) => b.share - a.share);
}

/**
 * The chart for one birth date, read at `jd`.
 *
 * `jd` comes from the same place the score does — the middle of the Moon's likeliest stretch of the
 * day — so the chart drawn on the page and the chart the eight tests scored are the same chart.
 * Passing noon instead would occasionally print one sign and score another.
 */
export function natalChart(iso: string, jd: number, bodies: Body[] = BODIES): NatalChart | null {
  const parsed = parseDate(iso);
  if (!parsed) return null;
  const { y, m, d } = parsed;
  const chart = chartAt(jd, bodies);

  const rows = chart.placements.map((p: Placement): NatalBody => {
    const chances = signChances(p.body, y, m, d);
    const here = chances.find((c) => c.sign === p.sign);
    return {
      body: p.body,
      lon: p.lon,
      sign: p.sign,
      signName: p.signName,
      deg: p.deg,
      retro: p.retro,
      chances,
      certainty: here?.share ?? 1,
      settled: chances.length === 1,
    };
  });

  const byBody = {} as Record<Body, NatalBody>;
  for (const r of rows) byBody[r.body] = r;
  return { iso, jd, bodies: rows, byBody };
}

/**
 * The three slow bodies, and how long they sit in one sign.
 *
 * Stated so the page can say why they get no personal reading: everyone born within these windows
 * shares the placement, so it describes a cohort and not a person. They are still drawn, because
 * they were in the sky.
 */
export const GENERATIONAL: { body: Body; years: string }[] = [
  { body: "Uranus", years: "about seven years" },
  { body: "Neptune", years: "about fourteen years" },
  { body: "Pluto", years: "between twelve and thirty years" },
];
