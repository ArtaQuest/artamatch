/**
 * search.ts — the ceiling: the best score a person could reach, against every birth date in a
 * window, taken one day at a time.
 *
 * ── Why a ceiling is worth computing ────────────────────────────────────────────────────────────
 *
 * A score out of 36 sitting on its own invites the wrong question ("is 24 good?") and the
 * percentile answers it only in the aggregate. This answers it for THIS person: scan every single
 * date of birth within ±12 years, score all of them, and report the best that exists. Then a
 * reading has two anchors instead of one — how it compares to everybody, and how close it is to the
 * most this person could have got.
 *
 * It also punctures a superstition the page would otherwise encourage. The top score is not held by
 * one soulmate born on one magic day: the eight tests read the Moon, the Moon returns to the same
 * birth star every 27.3 days, so a few hundred of the ~8,766 days reach the same ceiling. That count
 * is reported, and it is the most honest thing on the panel.
 *
 * ── Doing 8,766 days quickly ────────────────────────────────────────────────────────────────────
 *
 * `matchPair` is the reference implementation and it is far too slow to call nine thousand times: it
 * builds a full ten-body chart per state. Every one of the eight tests reads the MOON ONLY, so this
 * builds a Moon-only side and skips the other nine bodies. The two warnings (which read Mars and
 * Venus) are not scored, so nothing is lost.
 *
 * A test asserts this agrees with `matchPair` exactly, on every day of a sampled month — a fast path
 * that quietly disagrees with the page's own arithmetic would be worse than no fast path.
 */

import { julianDay, parseDate, siderealLongitude, SIGNS } from "./ephemeris";
import { nakshatraOf } from "./nakshatra";
import { gunaMilan, type KutaKey, type KutaSide } from "./kuta";
import { birthSpan } from "./uncertainty";

/** One candidate date and what it scores. */
export type DayScore = { iso: string; expected: number; certain: boolean };

export type SearchResult = {
  /** The window, inclusive. */
  from: string;
  to: string;
  days: number;
  /** The highest expected score anywhere in the window. */
  ceiling: number;
  /** How many of the days reach within half a point of it — the anti-soulmate number. */
  atCeiling: number;
  /** The best days, nearest the person's own birthday first, so the example is a plausible age. */
  best: DayScore[];
  /** The worst score in the window, and the middle one — the range a person actually faces. */
  floor: number;
  median: number;
  /** Count of days at each whole score, 0…36 — the shape of what is available. */
  histogram: number[];
};

/** A Moon-only side. Mars and Venus are omitted deliberately: they feed the two warnings, and the
 *  warnings are not scored. */
function moonSide(lon: number): KutaSide {
  const rasi = Math.floor(lon / 30) % 12;
  return {
    moonLon: lon,
    nakshatra: nakshatraOf(lon).info,
    rasi,
    degInSign: lon - rasi * 30,
    marsLon: 0,
    venusLon: 0,
  };
}

/** The Moon states of one birth day: (birth star, sign, mid-sign half) and each one's share. */
type States = { lon: number; share: number }[];

/**
 * The distinct Moon states of a day, found the same exact way `uncertainty.ts` does — an hourly
 * scan for a change of state, then bisection inside the hour that changed.
 *
 * Duplicated here rather than imported because `birthSpan` also builds a chart, caches, computes an
 * arc and a zone widening, and none of that survives being called nine thousand times. The two are
 * held together by a test.
 */
function moonStates(y: number, m: number, d: number): States {
  const at = (h: number) => siderealLongitude("Moon", julianDay(y, m, d, h));
  const key = (h: number) => {
    const lon = at(h);
    const rasi = Math.floor(lon / 30) % 12;
    const half = (rasi === 8 || rasi === 9) && lon - rasi * 30 >= 15 ? 1 : 0;
    return { nak: nakshatraOf(lon).info.index, rasi, half };
  };

  const edges = [0];
  let prev = key(0);
  for (let h = 1; h <= 24; h++) {
    const here = key(h);
    if (here.nak !== prev.nak || here.rasi !== prev.rasi || here.half !== prev.half) {
      const before = prev;
      let a = h - 1, b = h;
      for (let i = 0; i < 26; i++) {
        const mid = (a + b) / 2;
        const k = key(mid);
        if (k.nak === before.nak && k.rasi === before.rasi && k.half === before.half) a = mid;
        else b = mid;
      }
      edges.push((a + b) / 2);
    }
    prev = here;
  }
  edges.push(24);

  const out: States = [];
  for (let i = 0; i < edges.length - 1; i++) {
    const w = edges[i + 1] - edges[i];
    if (w < 1e-6) continue;
    out.push({ lon: at((edges[i] + edges[i + 1]) / 2), share: w / 24 });
  }
  return out;
}

const iso = (y: number, m: number, d: number) =>
  `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

/** The expected score between one person's Moon states and another's. */
function expectedBetween(a: States, b: States, excluded: KutaKey[]): { expected: number; certain: boolean } {
  let expected = 0;
  let first: number | null = null;
  let certain = true;
  for (const sa of a) {
    const sideA = moonSide(sa.lon);
    for (const sb of b) {
      const g = gunaMilan(sideA, moonSide(sb.lon));
      const score = excluded.length
        ? g.kutas.filter((k) => !excluded.includes(k.key)).reduce((s, k) => s + k.points, 0)
        : g.total;
      expected += score * sa.share * sb.share;
      if (first === null) first = score;
      else if (score !== first) certain = false;
    }
  }
  return { expected, certain };
}

/**
 * The fast path applied to ONE date — the seam the tests hold against `matchPair`.
 *
 * Nothing in the app calls this; it exists so that "these two implementations agree" is a claim
 * that can be checked directly on any date, rather than inferred from the handful of dates a scan
 * happens to name as its best.
 */
export function fastExpected(isoSelf: string, isoOther: string, excluded: KutaKey[] = []): number | null {
  const a = birthSpan(isoSelf);
  const other = parseDate(isoOther);
  if (!a || !other) return null;
  return expectedBetween(
    a.states.map((s) => ({ lon: s.lon, share: s.share })),
    moonStates(other.y, other.m, other.d),
    excluded,
  ).expected;
}

/** Days scored between yields. Small enough that a caller can stop inside a frame, large enough
 *  that the generator machinery costs nothing measurable. */
const BATCH = 64;

/**
 * Score every birth date within ±`years` of `isoSelf`, one day at a time.
 *
 * A GENERATOR, not a function, because the scan takes about 900 ms and a page that freezes for
 * nine tenths of a second while you scroll it is broken. It yields the fraction done every 64 days;
 * the caller runs it for a slice of a frame and comes back. `bestWithin` below is the plain
 * synchronous wrapper, used by the tests and by anything that does not care about a frame budget.
 */
export function* scanWithin(
  isoSelf: string,
  years = 12,
  opts: { exclude?: KutaKey[]; keep?: number } = {},
): Generator<number, SearchResult | null, void> {
  const self = parseDate(isoSelf);
  const span = birthSpan(isoSelf);
  if (!self || !span) return null;
  const excluded = opts.exclude ?? [];
  const keep = opts.keep ?? 3;

  const selfStates: States = span.states.map((s) => ({ lon: s.lon, share: s.share }));

  const startJd = julianDay(self.y, self.m, self.d, 12) - Math.round(years * 365.25);
  const endJd = julianDay(self.y, self.m, self.d, 12) + Math.round(years * 365.25);
  const selfJd = julianDay(self.y, self.m, self.d, 12);

  const histogram = new Array(37).fill(0);
  const scores: number[] = [];
  const rows: (DayScore & { away: number })[] = [];
  let ceiling = -Infinity, floor = Infinity;

  for (let jd = startJd; jd <= endJd; jd += 1) {
    // Rebuilt from the Julian Day rather than stepped through the calendar, so leap days and month
    // lengths take care of themselves and no day is visited twice or skipped.
    const z = Math.floor(jd + 0.5);
    const alpha = Math.floor((z - 1867216.25) / 36524.25);
    const aa = z < 2299161 ? z : z + 1 + alpha - Math.floor(alpha / 4);
    const bb = aa + 1524;
    const cc = Math.floor((bb - 122.1) / 365.25);
    const dd = Math.floor(365.25 * cc);
    const ee = Math.floor((bb - dd) / 30.6001);
    const day = bb - dd - Math.floor(30.6001 * ee);
    const mon = ee < 14 ? ee - 1 : ee - 13;
    const yr = mon > 2 ? cc - 4716 : cc - 4715;
    if (yr < 1800 || yr > 2100) continue;

    const { expected, certain } = expectedBetween(selfStates, moonStates(yr, mon, day), excluded);
    scores.push(expected);
    histogram[Math.min(36, Math.max(0, Math.round(expected)))]++;
    if (expected > ceiling) ceiling = expected;
    if (expected < floor) floor = expected;
    rows.push({ iso: iso(yr, mon, day), expected, certain, away: Math.abs(jd - selfJd) });
    if (rows.length % BATCH === 0) yield (jd - startJd) / (endJd - startJd);
  }

  if (scores.length === 0) return null;
  // "At the ceiling" is a HALF POINT wide, not exact equality: the expected score is a weighted
  // mean over the day's Moon states, so two days holding the identical winning reading differ in
  // the fourth decimal and an equality test would report one day where there are hundreds.
  const atCeiling = rows.filter((r) => r.expected >= ceiling - 0.5).length;
  const best = rows
    .filter((r) => r.expected >= ceiling - 0.5)
    // Nearest the person's own birthday first: a ceiling reachable at 40 years apart is true and
    // useless, and the whole point of the window is that the answer be a plausible person.
    .sort((x, y) => y.expected - x.expected || x.away - y.away)
    .slice(0, keep)
    .map(({ iso, expected, certain }) => ({ iso, expected, certain }));

  const sorted = [...scores].sort((x, y) => x - y);
  return {
    from: rows[0].iso,
    to: rows[rows.length - 1].iso,
    days: rows.length,
    ceiling,
    atCeiling,
    best,
    floor,
    median: sorted[Math.floor(sorted.length / 2)],
    histogram,
  };
}

/** Run the whole scan at once. Blocks for about a second — fine in a test, not in a browser. */
export function bestWithin(
  isoSelf: string,
  years = 12,
  opts: { exclude?: KutaKey[]; keep?: number } = {},
): SearchResult | null {
  const gen = scanWithin(isoSelf, years, opts);
  let step = gen.next();
  while (!step.done) step = gen.next();
  return step.value;
}

/** Which Moon sign a date puts the Moon in — for the one-line "what the ceiling takes" sentence. */
export function moonSignOn(isoDate: string): string | null {
  const span = birthSpan(isoDate);
  return span ? SIGNS[span.likeliest.rasi] : null;
}
