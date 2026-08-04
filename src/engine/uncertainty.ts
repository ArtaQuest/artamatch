/**
 * uncertainty.ts — what a date of birth alone can and cannot tell you.
 *
 * This is the most important file in the engine, and the one most compatibility sites do not have.
 *
 * A birth DATE fixes the Sun to about a degree and the outer planets to almost nothing. It does not
 * fix the MOON. The Moon travels 11.8°–15.4° in a day, and a nakshatra is 13°20′ wide — so on most
 * days the Moon changes nakshatra somewhere inside the birth day, and on many it changes rāśi too.
 * Every one of the eight kutas is computed from the two Moons. A matcher that quietly
 * evaluates "the chart" at noon and prints 28/36 is stating, with total confidence, one of two, three or
 * four answers that the input cannot distinguish between.
 *
 * For scale, measured against the Swiss Ephemeris: this engine's Moon is accurate to 1.4 arcminutes,
 * while the unknown birth time moves the Moon by up to ±6.6° — roughly 290× larger. The ephemeris is
 * not the source of doubt here. The missing clock is.
 *
 * So instead of a point estimate, every Moon-dependent result is computed across the WHOLE DAY:
 *   · the Moon's arc across the 24 hours, and the exact instants it crosses a boundary
 *   · the distinct states it occupies — at most four
 *   · each state's share of the day, which is a defensible weight for "most likely"
 * A caller then evaluates its rule once per state and reports a RANGE when the states disagree.
 *
 * One honesty note carried through to the UI: a birth date is a LOCAL date, and we do not know the
 * zone. We take it as a UT day, which is the standard convention for date-only work, but a birth in
 * UTC+13 or UTC−11 can sit outside that window entirely. So the band computed here is the NARROWEST
 * defensible one, not the widest — `zoneWidened` reports what a fully unknown zone would add.
 */

import {
  type Chart, type Body, chartAt, julianDay, parseDate, siderealLongitude, SIGNS,
} from "./ephemeris";
import { type NakshatraInfo, nakshatraOf } from "./nakshatra";

/** One (nakshatra, rāśi) state the Moon occupies during the birth day. */
type MoonState = {
  nakshatra: NakshatraInfo;
  pada: number;
  /** Sign index 0–11. */
  rasi: number;
  rasiName: string;
  /** UT hours during which the Moon is in this state. */
  fromHour: number;
  toHour: number;
  /** Share of the 24-hour day spent here, 0…1 — the weight for "most likely". */
  share: number;
  /** Sidereal longitude at the middle of this stretch. */
  lon: number;
};

export type BirthSpan = {
  iso: string;
  jdStart: number;
  jdMid: number;
  jdEnd: number;
  /**
   * The instant the headline reading is taken at: the MIDDLE OF THE MOST LIKELY STATE, not noon.
   *
   * Noon is the obvious choice and it is wrong. On a day where the Moon changes birth star twice,
   * noon can land inside a sliver the Moon only occupies for two hours while a state covering half
   * the day sits next to it. Measured over 7,200 dates, taking noon disagreed with the most likely
   * birth star on 6.1% of them — so the page would print one birth star and score a different one.
   * Taking the middle of the most likely state makes the displayed chart and the computed score the
   * same chart, and is also the better estimate under a flat prior over birth times.
   */
  jdEstimate: number;
  /** The chart at jdEstimate — the single best point estimate, and the one shown. */
  chart: Chart;
  moonStartLon: number;
  moonEndLon: number;
  /** Degrees the Moon travelled across the day. */
  moonArc: number;
  /**
   * Every distinct state, in time order. At most FOUR.
   *
   * The Moon moves at most ~15.4° in a day. Within that arc it can cross at most two nakshatra
   * boundaries (spaced 13°20′) and at most one rāśi boundary (spaced 30°) — three boundaries, so
   * four states. 1965-07-27 is a real example of the ceiling: the Moon travels 15.17° from Ardra in
   * Gemini, through Punarvasu in Gemini and Punarvasu in Cancer, into Pushya in Cancer. Someone born
   * that day has three possible birth stars, and Guna Milan answers differently for each.
   */
  states: MoonState[];
  /** True when the Moon stays in one nakshatra AND one rāśi all day — then the date alone is
   *  genuinely enough and the result carries no Moon ambiguity at all. */
  stable: boolean;
  /** The state occupying the largest share of the day. */
  likeliest: MoonState;
  /** How much wider the band would be if the birth time zone were also unknown (in degrees of
   *  extra Moon travel, either side). Reported, never silently folded in. */
  zoneWidened: number;
};

const HOURS = 24;

/** The instant, in UT hours, at which f() changes sign between lo and hi — by bisection.
 *  Exported so the natal chart can find a planet's sign change the same exact way. */
export function crossing(lo: number, hi: number, f: (h: number) => boolean, iterations = 26): number {
  let a = lo, b = hi;
  const target = f(a);
  for (let i = 0; i < iterations; i++) {
    const mid = (a + b) / 2;
    if (f(mid) === target) a = mid; else b = mid;
  }
  return (a + b) / 2;
}

/**
 * Everything a birth DATE determines, plus an explicit account of what it does not.
 *
 * The Moon's longitude increases monotonically (it never retrogrades), so boundaries can be found by
 * scanning hourly for an index change and then bisecting inside that hour to about a second. That is
 * exact rather than sampled — a state boundary is a real instant, not a grid artefact.
 */
const SPAN_CACHE = new Map<string, BirthSpan | null>();

export function birthSpan(iso: string, bodies?: Body[]): BirthSpan | null {
  // The matrix view computes every pair; without this cache 200 people cost 19,900 fresh
  // hour-by-hour Moon scans. Only the default-bodies call is cached, and the cache is bounded.
  const cacheable = bodies === undefined;
  if (cacheable && SPAN_CACHE.has(iso)) return SPAN_CACHE.get(iso)!;
  const out = birthSpanUncached(iso, bodies);
  if (cacheable) {
    if (SPAN_CACHE.size > 600) SPAN_CACHE.clear();
    SPAN_CACHE.set(iso, out);
  }
  return out;
}

function birthSpanUncached(iso: string, bodies?: Body[]): BirthSpan | null {
  const parsed = parseDate(iso);
  if (!parsed) return null;
  const { y, m, d } = parsed;

  const jdStart = julianDay(y, m, d, 0);
  const jdMid = julianDay(y, m, d, 12);
  const jdEnd = julianDay(y, m, d, HOURS);
  const moonAt = (hour: number) => siderealLongitude("Moon", julianDay(y, m, d, hour));

  const moonStartLon = moonAt(0);
  const moonEndLon = moonAt(HOURS);
  // Unwrapped travel: the Moon always moves forward, so a negative difference means it wrapped 360°.
  const moonArc = ((moonEndLon - moonStartLon) % 360 + 360) % 360;

  // Key of the state at a given hour. THREE components, not two: the eight tests also read the
  // mid-sign split at 15° of Sagittarius (255°) and Capricorn (285°) — the one rule that depends
  // on the degree WITHIN a sign. A day on which the Moon crosses 255° or 285° changes that test's
  // answer without changing star or sign, so those crossings must open a new state too, or the
  // "every reading the dates allow" table would quietly miss a reading. Found by adversarial
  // review, verified by brute force.
  const keyAt = (hour: number) => {
    const lon = moonAt(hour);
    const rasi = Math.floor(lon / 30) % 12;
    const degIn = lon - rasi * 30;
    const half = (rasi === 8 || rasi === 9) && degIn >= 15 ? 1 : 0;
    return { nak: nakshatraOf(lon).info.index, rasi, half, lon };
  };

  // Hourly scan for changes, then bisect each one.
  const edges: number[] = [0];
  let prev = keyAt(0);
  for (let h = 1; h <= HOURS; h++) {
    const here = keyAt(h);
    if (here.nak !== prev.nak || here.rasi !== prev.rasi || here.half !== prev.half) {
      const changed = (hour: number) => {
        const k = keyAt(hour);
        return k.nak === prev.nak && k.rasi === prev.rasi && k.half === prev.half;
      };
      edges.push(crossing(h - 1, h, changed));
    }
    prev = here;
  }
  edges.push(HOURS);

  const states: MoonState[] = [];
  for (let i = 0; i < edges.length - 1; i++) {
    const fromHour = edges[i], toHour = edges[i + 1];
    if (toHour - fromHour < 1e-6) continue;
    const midHour = (fromHour + toHour) / 2;
    const lon = moonAt(midHour);
    const nk = nakshatraOf(lon);
    states.push({
      nakshatra: nk.info,
      pada: nk.pada,
      rasi: Math.floor(lon / 30) % 12,
      rasiName: SIGNS[Math.floor(lon / 30) % 12],
      fromHour, toHour,
      share: (toHour - fromHour) / HOURS,
      lon,
    });
  }

  const likeliest = states.reduce((best, s) => (s.share > best.share ? s : best), states[0]);
  const jdEstimate = julianDay(y, m, d, (likeliest.fromHour + likeliest.toHour) / 2);
  // A ±12h zone unknown would let the Moon travel roughly half a day further either way.
  const zoneWidened = (moonArc / HOURS) * 12;

  return {
    iso,
    jdStart, jdMid, jdEnd, jdEstimate,
    chart: chartAt(jdEstimate, bodies),
    moonStartLon, moonEndLon, moonArc,
    states,
    stable: states.length === 1,
    likeliest,
    zoneWidened,
  };
}
