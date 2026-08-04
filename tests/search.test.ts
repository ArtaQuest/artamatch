/**
 * The ceiling scan has one dangerous property: it is a SECOND implementation of the score.
 *
 * `matchPair` builds a full ten-body chart per Moon state; the scan builds a Moon-only side and
 * skips nine bodies, because it has to do that nine thousand times. Two code paths for one number
 * is exactly how a page ends up quietly disagreeing with itself — a panel announcing "the most you
 * could score is 29.5" while the reading for that very date says 28. So the first test here is not
 * about the ceiling at all: it is that the fast path and the reference agree, to the last decimal,
 * on every day of a month.
 */

import { describe, it, expect } from "vitest";
import { bestWithin, fastExpected, scanWithin, moonSignOn } from "../src/engine/search";
import { matchPair } from "../src/engine/score";
import { parseDate } from "../src/engine/ephemeris";

const SELF = "1999-12-06";

describe("the fast path is the same arithmetic", () => {
  it("agrees with matchPair to the last decimal, on every day of four whole months", () => {
    // Whole months rather than a handful of dates: the disagreements worth catching only appear
    // when the Moon changes birth star or sign inside the day, and that is about half the calendar.
    let checked = 0;
    for (const month of ["2001-03", "1994-07", "1965-07", "2012-11"]) {
      for (let d = 1; d <= 31; d++) {
        const iso = `${month}-${String(d).padStart(2, "0")}`;
        const ref = matchPair(SELF, iso);
        if (!ref) continue;               // 31st of a 30-day month
        expect(fastExpected(SELF, iso), iso).toBeCloseTo(ref.distribution.expected, 10);
        checked++;
      }
    }
    expect(checked).toBeGreaterThan(115);
  }, 60_000);

  it("agrees with matchPair when a test is switched off too", () => {
    for (const iso of ["2001-03-14", "1965-07-27", "2004-12-21", "1988-02-29"]) {
      const ref = matchPair(SELF, iso, { exclude: ["varna"] })!;
      expect(fastExpected(SELF, iso, ["varna"]), iso).toBeCloseTo(ref.distribution.expected, 10);
    }
  });

  it("puts the reference score of every best day at the ceiling", () => {
    // The strongest possible statement of agreement: take the dates the scan NAMES as best, run
    // the page's own reference implementation on them, and require the same number.
    for (const self of [SELF, "2004-12-27", "1965-07-27"]) {
      const scan = bestWithin(self, 12, { keep: 12 })!;
      expect(scan.best.length).toBeGreaterThan(0);
      for (const day of scan.best) {
        const ref = matchPair(self, day.iso)!;
        expect(ref.distribution.expected, `${self} vs ${day.iso}`).toBeCloseTo(day.expected, 9);
        expect(day.expected).toBeGreaterThanOrEqual(scan.ceiling - 0.5);
      }
    }
  }, 60_000);
});

describe("the window", () => {
  it("covers twelve years either side, one day at a time, with nothing skipped or repeated", () => {
    const scan = bestWithin(SELF, 12)!;
    const from = parseDate(scan.from)!, to = parseDate(scan.to)!;
    expect(from.y).toBe(1987);
    expect(to.y).toBe(2011);
    // 24 years of days, give or take the leap-day rounding in 365.25.
    expect(scan.days).toBeGreaterThan(8760);
    expect(scan.days).toBeLessThan(8775);
    // The histogram must account for every day scanned — a day dropped on the floor would quietly
    // shrink the search without changing anything visible.
    expect(scan.histogram.reduce((s, n) => s + n, 0)).toBe(scan.days);
  }, 30_000);

  it("scales with the window", () => {
    const narrow = bestWithin(SELF, 1)!;
    const wide = bestWithin(SELF, 12)!;
    expect(narrow.days).toBeLessThan(800);
    expect(wide.days).toBeGreaterThan(narrow.days * 10);
    // A wider search can only ever find at least as good a day.
    expect(wide.ceiling).toBeGreaterThanOrEqual(narrow.ceiling - 1e-9);
  }, 30_000);

  it("is deterministic", () => {
    const a = bestWithin("2004-12-21", 12)!;
    const b = bestWithin("2004-12-21", 12)!;
    expect(b).toEqual(a);
  }, 30_000);

  it("respects a switched-off test", () => {
    const all = bestWithin(SELF, 12)!;
    const less = bestWithin(SELF, 12, { exclude: ["varna"] })!;
    // Dropping a test worth one point can only lower a ceiling, never raise it.
    expect(less.ceiling).toBeLessThanOrEqual(all.ceiling + 1e-9);
    expect(less.ceiling).toBeGreaterThan(all.ceiling - 1.01);
  }, 30_000);
});

describe("what the panel claims", () => {
  it("finds a ceiling well short of a perfect 36, and many days that reach it", () => {
    // Both halves matter for honesty. Nobody gets 36 — so a page that implied a perfect match was
    // out there would be lying — and the top score is held by HUNDREDS of days, not one, because
    // the Moon comes back to the same place every 27 days. That is the anti-soulmate number.
    for (const self of [SELF, "2004-12-27", "2004-12-21", "1980-03-19"]) {
      const scan = bestWithin(self, 12)!;
      expect(scan.ceiling).toBeLessThan(36);
      expect(scan.ceiling).toBeGreaterThan(scan.median);
      expect(scan.atCeiling).toBeGreaterThan(10);
      expect(scan.atCeiling).toBeLessThan(scan.days / 20);
      expect(scan.floor).toBeLessThan(scan.median);
    }
  }, 60_000);

  it("yields progress as it goes, so a page can stay responsive", () => {
    const gen = scanWithin(SELF, 12);
    const seen: number[] = [];
    let step = gen.next();
    while (!step.done) { seen.push(step.value); step = gen.next(); }
    expect(seen.length).toBeGreaterThan(50);
    for (let i = 1; i < seen.length; i++) expect(seen[i]).toBeGreaterThan(seen[i - 1]);
    expect(seen[0]).toBeGreaterThanOrEqual(0);
    expect(seen[seen.length - 1]).toBeLessThanOrEqual(1);
    expect(step.value!.days).toBeGreaterThan(8760);
  }, 30_000);

  it("refuses a date it cannot chart rather than returning a wrong ceiling", () => {
    expect(bestWithin("2001-02-29", 12)).toBeNull();
    expect(bestWithin("not-a-date", 12)).toBeNull();
    expect(moonSignOn("2001-02-29")).toBeNull();
  });
});
