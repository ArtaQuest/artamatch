/**
 * The three extra traditions, and the ensemble over all four.
 *
 * Each system is pinned by known examples (a date whose number, animal and sign can be checked by
 * hand or against any published table), by symmetry, and by its calibration summing to one. The
 * ensemble is pinned to its stated rule — the plain mean of the four percentiles — so a quiet
 * reweighting cannot ship.
 */

import { describe, it, expect } from "vitest";
import {
  dateNumber, numbersMatch, animalYear, animalsMatch, sunSign, sunSignsMatch,
  ensembleFor, midpointPercentile, NUMBERS_DIST, ANIMALS_DIST, SUNSIGNS_DIST, ANIMALS,
} from "../src/engine/systems";
import { matchPair } from "../src/engine/score";

const DATES = [
  "1994-02-15", "1965-07-27", "1999-12-06", "2004-12-27", "1912-06-23",
  "1980-03-19", "1955-09-02", "2001-01-01", "1943-06-30", "1988-08-08",
];

describe("the numbers", () => {
  it("reduces known dates correctly, keeping master numbers", () => {
    // 1994-02-15: 1+9+9+4 + 0+2 + 1+5 = 31 → 4
    expect(dateNumber("1994-02-15")).toMatchObject({ value: 4, digit: 4, family: "builders" });
    // 1988-08-08: 1+9+8+8 + 0+8 + 0+8 = 42 → 6
    expect(dateNumber("1988-08-08")).toMatchObject({ value: 6, digit: 6, family: "feelers" });
    // 1975-11-11: 1+9+7+5 + 1+1 + 1+1 = 26 → 8
    expect(dateNumber("1975-11-11")).toMatchObject({ value: 8, family: "builders" });
    // A master number: 1910-10-10 → 1+9+1+0+1+0+1+0 = 13 → 4? No: 13 → 1+3 = 4. Find a real 11:
    // 1901-01-08 → 1+9+0+1+0+1+0+8 = 20 → 2. 1902-01-08 → 21 → 3. 1910-11-07 → 1+9+1+0+1+1+0+7=20.
    // 1957-05-05 → 1+9+5+7+0+5+0+5 = 32 → 5. 1948-11-11 → 1+9+4+8+1+1+1+1 = 26 → 8.
    // 1910-04-06 → 1+9+1+0+0+4+0+6 = 21. 2009-09-09 → 2+0+0+9+0+9+0+9 = 29 → 11 → MASTER.
    expect(dateNumber("2009-09-09")).toMatchObject({ value: 11, digit: 2, isMaster: true, family: "builders" });
  });

  it("is symmetric and stays on its scale", () => {
    for (const a of DATES) for (const b of DATES) {
      const ab = numbersMatch(a, b)!, ba = numbersMatch(b, a)!;
      expect(ab.score).toBe(ba.score);
      expect([1, 2, 3]).toContain(ab.score);
      expect(ab.verdict.length).toBeGreaterThan(20);
    }
  });
});

describe("the year animals", () => {
  it("gets known years right, including the early-February boundary", () => {
    expect(animalYear("1994-06-01")).toMatchObject({ animal: "Dog", element: "Wood", year: 1994 });
    expect(animalYear("2020-06-01")).toMatchObject({ animal: "Rat", element: "Metal" });
    expect(animalYear("1984-06-01")).toMatchObject({ animal: "Rat", element: "Wood" });
    // January belongs to the PREVIOUS year's animal — the year turns in early February.
    expect(animalYear("1994-01-15")).toMatchObject({ animal: "Rooster", year: 1993 });
    expect(animalYear("1994-02-03")).toMatchObject({ year: 1993, boundary: true });
    expect(animalYear("1994-02-04")).toMatchObject({ year: 1994, boundary: true });
    expect(animalYear("1994-02-06")).toMatchObject({ year: 1994, boundary: false });
  });

  it("applies the classical relations symmetrically", () => {
    // Rat & Ox: secret friends. Rat & Horse: direct clash. Rat & Dragon: same team.
    const y = (animal: string) => `${1996 + ANIMALS.indexOf(animal as never)}-06-01`; // 1996 = Rat
    expect(animalsMatch(y("Rat"), y("Ox"))!.score).toBe(4);
    expect(animalsMatch(y("Rat"), y("Horse"))!.score).toBe(0);
    expect(animalsMatch(y("Rat"), y("Dragon"))!.score).toBe(3);
    expect(animalsMatch(y("Rat"), y("Goat"))!.score).toBe(1);  // harm pair
    expect(animalsMatch(y("Rat"), y("Tiger"))!.score).toBe(2); // no special tie
    for (const a of DATES) for (const b of DATES) {
      expect(animalsMatch(a, b)!.score).toBe(animalsMatch(b, a)!.score);
    }
  });
});

describe("the Sun signs", () => {
  it("computes signs from the real Sun, not date ranges", () => {
    expect(sunSign("1994-02-15")!.signName).toBe("Aquarius");
    expect(sunSign("1994-08-15")!.signName).toBe("Leo");
    expect(sunSign("1994-12-25")!.signName).toBe("Capricorn");
    // A boundary day: the Sun changes sign during the day, and that is flagged rather than hidden.
    const days = ["1994-03-20", "1994-03-21", "1994-03-19"];
    expect(days.some((d) => sunSign(d)!.boundary)).toBe(true);
  });

  it("scores by element, symmetrically", () => {
    // Two fire signs: easy. Fire and water: uneasy. Opposites: the attraction pairing.
    expect(sunSignsMatch("1994-08-15", "1994-04-01")!.score).toBe(3);  // Leo & Aries, both fire
    expect(sunSignsMatch("1994-08-15", "1994-07-01")!.score).toBe(1);  // Leo & Cancer, fire/water
    expect(sunSignsMatch("1994-08-15", "1994-02-01")!.score).toBe(2);  // Leo & Aquarius, opposites
    for (const a of DATES) for (const b of DATES) {
      expect(sunSignsMatch(a, b)!.score).toBe(sunSignsMatch(b, a)!.score);
    }
  });
});

describe("calibration and the ensemble", () => {
  it("has distributions that sum to one", () => {
    for (const dist of [NUMBERS_DIST, ANIMALS_DIST, SUNSIGNS_DIST]) {
      const total = Object.values(dist).reduce((s, x) => s + x, 0);
      expect(Math.abs(total - 1)).toBeLessThan(0.01);
    }
  });

  it("gives midpoint percentiles that behave like percentiles", () => {
    // A direct clash sits near the bottom; secret friends near the top; the common middling
    // outcome sits near the middle rather than at the bottom of its band.
    expect(midpointPercentile(0, ANIMALS_DIST)).toBeLessThan(10);
    expect(midpointPercentile(4, ANIMALS_DIST)).toBeGreaterThan(90);
    expect(midpointPercentile(2, ANIMALS_DIST)).toBeGreaterThan(30);
    expect(midpointPercentile(2, ANIMALS_DIST)).toBeLessThan(70);
  });

  it("is the plain mean of the four percentiles — no hidden weights", () => {
    for (let i = 0; i + 1 < DATES.length; i += 2) {
      const m = matchPair(DATES[i], DATES[i + 1])!;
      const e = ensembleFor(DATES[i], DATES[i + 1],
        { percentile: m.percentile, score: m.score, maxScore: m.maxScore })!;
      expect(e.systems).toHaveLength(4);
      const mean = Math.round(e.systems.reduce((s, x) => s + x.percentile, 0) / 4);
      expect(e.percentile).toBe(mean);
      expect(e.aboveAverage).toBe(e.systems.filter((x) => x.percentile >= 50).length);
    }
  });

  it("is symmetric end to end", () => {
    for (let i = 0; i + 1 < DATES.length; i += 2) {
      const ma = matchPair(DATES[i], DATES[i + 1])!;
      const mb = matchPair(DATES[i + 1], DATES[i])!;
      const ea = ensembleFor(DATES[i], DATES[i + 1], { percentile: ma.percentile, score: ma.score, maxScore: ma.maxScore })!;
      const eb = ensembleFor(DATES[i + 1], DATES[i], { percentile: mb.percentile, score: mb.score, maxScore: mb.maxScore })!;
      expect(ea.percentile).toBe(eb.percentile);
    }
  });
});

describe("calibration drift", () => {
  it("keeps the embedded Moon-score facts honest against a live recomputation", () => {
    // 2,000 seeded pairs — a fast version of tools/calibrate.mjs. If a rule change shifts the
    // distribution, the embedded PASS_RATE / MEDIAN_SCORE / percentile table go stale silently;
    // this is the guard that makes them fail loudly instead.
    let s = 97531;
    const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
    const date = () => {
      const y = 1930 + Math.floor(rnd() * 80), m = 1 + Math.floor(rnd() * 12), d = 1 + Math.floor(rnd() * 28);
      return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    };
    const scores: number[] = [];
    for (let i = 0; i < 2000; i++) {
      const m = matchPair(date(), date());
      if (m) scores.push(m.score);
    }
    scores.sort((a, b) => a - b);
    const median = scores[Math.floor(scores.length / 2)];
    const passRate = (scores.filter((x) => x >= 18).length / scores.length) * 100;
    expect(Math.abs(median - 21)).toBeLessThanOrEqual(1);
    expect(Math.abs(passRate - 71)).toBeLessThanOrEqual(4);
  });
});
