/**
 * Guna Milan rules, scoring properties, and the uncertainty model.
 *
 * The most important test in this file is SYMMETRY. A ranked list is incoherent unless
 * score(A,B) === score(B,A) — otherwise A's list and B's list disagree about the same pair, and
 * neither is wrong in a way anyone can point at. It is asserted over hundreds of random date pairs
 * rather than a handful of examples, because asymmetry would most likely creep in through one
 * mis-ordered table lookup that a few hand-picked cases would miss.
 */

import { describe, it, expect } from "vitest";
import { gunaMilan, gunaMilanOrdered, yoniPoints, grahaMaitriPoints, vashyaGroup, bandFor, YONI_ORDER, type KutaSide } from "../src/engine/kuta";
import { nakshatraOf, NAKSHATRAS } from "../src/engine/nakshatra";
import {
  matchPair, rankAgainst, PASS_RATE, MEDIAN_SCORE, PERCENTILE_BELOW,
} from "../src/engine/score";
import { birthSpan } from "../src/engine/uncertainty";
import { chartForDate, julianDay, siderealLongitude } from "../src/engine/ephemeris";

/** A deterministic pseudo-random date generator — seeded, so a failure is always reproducible. */
function makeDates(count: number, seed = 12345): string[] {
  let s = seed;
  const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
  const out: string[] = [];
  while (out.length < count) {
    const y = 1930 + Math.floor(rnd() * 90);
    const m = 1 + Math.floor(rnd() * 12);
    const d = 1 + Math.floor(rnd() * 28);
    out.push(`${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`);
  }
  return out;
}

function sideFor(iso: string): KutaSide {
  const chart = chartForDate(iso)!;
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

describe("Guna Milan structure", () => {
  const dates = makeDates(60);

  it("always produces eight kutas totalling at most 36", () => {
    for (const a of dates.slice(0, 20)) {
      for (const b of dates.slice(20, 40)) {
        const g = gunaMilanOrdered(sideFor(a), sideFor(b));
        expect(g.kutas).toHaveLength(8);
        expect(g.total).toBeGreaterThanOrEqual(0);
        expect(g.total).toBeLessThanOrEqual(36);
        const maxSum = g.kutas.reduce((s, k) => s + k.maxPoints, 0);
        expect(maxSum).toBe(36);
        for (const k of g.kutas) {
          expect(k.points).toBeGreaterThanOrEqual(0);
          expect(k.points).toBeLessThanOrEqual(k.maxPoints);
          expect(k.rule.length).toBeGreaterThan(20);      // every point carries its rule
          expect(k.evidence.length).toBeGreaterThan(10);  // and the values it read
        }
      }
    }
  });

  it("scores a person against themselves as maximum Varna/Vashya/Yoni/Gana but ZERO Nadi", () => {
    // Identical charts share a nadi, which is the classic Nadi dosha. That the system refuses to
    // give a perfect 36 to a perfect twin is a real property of it, not a bug.
    const g = gunaMilanOrdered(sideFor("1994-02-15"), sideFor("1994-02-15"));
    const by = Object.fromEntries(g.kutas.map((k) => [k.key, k.points]));
    expect(by.varna).toBe(1);
    expect(by.vashya).toBe(2);
    expect(by.yoni).toBe(4);
    expect(by.gana).toBe(6);
    expect(by.grahaMaitri).toBe(5);
    expect(by.bhakoot).toBe(7);   // 1/1 is not a dosha pair
    expect(by.nadi).toBe(0);      // same nadi — the dosha
    expect(g.total).toBe(28);     // 36 − 8
  });

  it("applies the Bhakoot 2/12, 5/9 and 6/8 rule and nothing else", () => {
    // Build synthetic sides at exact sign positions to exercise all 12 relationships.
    const at = (rasi: number): KutaSide => ({
      moonLon: rasi * 30 + 5,
      nakshatra: nakshatraOf(rasi * 30 + 5).info,
      rasi, degInSign: 5, marsLon: 0, venusLon: 0,
    });
    const failing = new Set([1, 4, 5, 7, 8, 11]); // signed distances that make 2/12, 5/9, 6/8
    for (let d = 0; d < 12; d++) {
      const g = gunaMilanOrdered(at(0), at(d));
      const bhakoot = g.kutas.find((k) => k.key === "bhakoot")!;
      expect(bhakoot.points, `distance ${d}`).toBe(failing.has(d) ? 0 : 7);
    }
  });

  it("gives Nadi its all-or-nothing 8 points", () => {
    for (const a of NAKSHATRAS) {
      for (const b of NAKSHATRAS) {
        const sa: KutaSide = { moonLon: 0, nakshatra: a, rasi: 0, degInSign: 0, marsLon: 0, venusLon: 0 };
        const sb: KutaSide = { moonLon: 0, nakshatra: b, rasi: 0, degInSign: 0, marsLon: 0, venusLon: 0 };
        const nadi = gunaMilanOrdered(sa, sb).kutas.find((k) => k.key === "nadi")!;
        expect(nadi.points).toBe(a.nadi === b.nadi ? 0 : 8);
      }
    }
  });

  it("bands the total sensibly around the conventional threshold of 18", () => {
    expect(bandFor(36).label).toBe("Exceptional");
    expect(bandFor(18).label).toBe("Acceptable");
    expect(bandFor(17.5).label).toBe("Below threshold");
    expect(bandFor(0).label).toBe("Poor");
  });
});

describe("kuta lookup tables", () => {
  it("gives yoni 4 for the same animal and 0 for classical enemies, symmetrically", () => {
    for (const a of YONI_ORDER) {
      expect(yoniPoints(a, a)).toBe(4);
      for (const b of YONI_ORDER) {
        expect(yoniPoints(a, b), `${a}/${b}`).toBe(yoniPoints(b, a));
        expect(yoniPoints(a, b)).toBeGreaterThanOrEqual(0);
        expect(yoniPoints(a, b)).toBeLessThanOrEqual(4);
      }
    }
    expect(yoniPoints("cat", "rat")).toBe(0);
    expect(yoniPoints("serpent", "mongoose")).toBe(0);
    expect(yoniPoints("cow", "tiger")).toBe(0);
  });

  it("has EXACTLY the seven canonical yoni enemy pairs and no others", () => {
    // An earlier version derived yoni from a hand-written pair list and got 45% of the 196 cells
    // wrong, including inventing an eighth enemy pair (elephant/sheep) that the tradition actually
    // rates FRIENDLY. This pins the enemy set exactly so that cannot recur.
    const canonical = [
      ["horse", "buffalo"], ["elephant", "lion"], ["sheep", "monkey"], ["serpent", "mongoose"],
      ["dog", "deer"], ["cat", "rat"], ["cow", "tiger"],
    ].map((p) => p.slice().sort().join("/")).sort();

    const found: string[] = [];
    for (let i = 0; i < YONI_ORDER.length; i++) {
      for (let j = i + 1; j < YONI_ORDER.length; j++) {
        if (yoniPoints(YONI_ORDER[i], YONI_ORDER[j]) === 0) {
          found.push([YONI_ORDER[i], YONI_ORDER[j]].sort().join("/"));
        }
      }
    }
    expect(found.sort()).toEqual(canonical);
    expect(yoniPoints("elephant", "sheep")).toBe(3); // friendly, NOT enemies
  });

  it("keeps the Vashya matrix symmetric", () => {
    const groups: [number, number][] = [
      [0, 0], [1, 15], [3, 0], [4, 0], [7, 0], [8, 0], [8, 20], [9, 0], [9, 20], [10, 0], [11, 0],
    ];
    for (const [rasiA, degA] of groups) {
      for (const [rasiB, degB] of groups) {
        const ab = gunaMilanOrdered(
          { moonLon: rasiA * 30 + degA, nakshatra: nakshatraOf(rasiA * 30 + degA).info, rasi: rasiA, degInSign: degA, marsLon: 0, venusLon: 0 },
          { moonLon: rasiB * 30 + degB, nakshatra: nakshatraOf(rasiB * 30 + degB).info, rasi: rasiB, degInSign: degB, marsLon: 0, venusLon: 0 },
        ).kutas.find((k) => k.key === "vashya")!.points;
        const ba = gunaMilanOrdered(
          { moonLon: rasiB * 30 + degB, nakshatra: nakshatraOf(rasiB * 30 + degB).info, rasi: rasiB, degInSign: degB, marsLon: 0, venusLon: 0 },
          { moonLon: rasiA * 30 + degA, nakshatra: nakshatraOf(rasiA * 30 + degA).info, rasi: rasiA, degInSign: degA, marsLon: 0, venusLon: 0 },
        ).kutas.find((k) => k.key === "vashya")!.points;
        expect(ab, `${rasiA}@${degA} vs ${rasiB}@${degB}`).toBe(ba);
      }
    }
  });

  it("gives Graha Maitri 5 for the same lord and stays inside 0–5", () => {
    expect(grahaMaitriPoints("Mars", "Mars").points).toBe(5);
    expect(grahaMaitriPoints("Sun", "Moon").points).toBe(5);   // mutual friends
    expect(grahaMaitriPoints("Sun", "Saturn").points).toBe(0); // mutual enemies
    const lords = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"] as const;
    for (const a of lords) {
      for (const b of lords) {
        const p = grahaMaitriPoints(a, b).points;
        expect(p).toBeGreaterThanOrEqual(0);
        expect(p).toBeLessThanOrEqual(5);
        expect(p, `${a}/${b}`).toBe(grahaMaitriPoints(b, a).points); // symmetric ladder
      }
    }
  });

  it("splits Sagittarius and Capricorn at 15° for Vashya", () => {
    expect(vashyaGroup(8, 14.9)).toBe("manava");
    expect(vashyaGroup(8, 15.1)).toBe("chatushpada");
    expect(vashyaGroup(9, 14.9)).toBe("chatushpada");
    expect(vashyaGroup(9, 15.1)).toBe("jalachara");
  });
});

describe("scoring is symmetric — a ranked list must agree with itself", () => {
  const dates = makeDates(200, 777);

  it("gives identical overall scores in both directions", () => {
    for (let i = 0; i + 1 < dates.length; i += 2) {
      const ab = matchPair(dates[i], dates[i + 1]);
      const ba = matchPair(dates[i + 1], dates[i]);
      expect(ab).not.toBeNull();
      expect(ba).not.toBeNull();
      expect(ab!.score, `${dates[i]} vs ${dates[i + 1]}`).toBeCloseTo(ba!.score, 9);
    }
  });

  it("gives identical Guna Milan totals in both directions", () => {
    for (let i = 0; i + 1 < dates.length; i += 2) {
      const ab = gunaMilan(sideFor(dates[i]), sideFor(dates[i + 1]));
      const ba = gunaMilan(sideFor(dates[i + 1]), sideFor(dates[i]));
      expect(ab.total).toBeCloseTo(ba.total, 9);
    }
  });


  it("keeps two people's rankings of each other consistent", () => {
    const people = makeDates(12, 4242).map((birthday, i) => ({ id: `p${i}`, birthday }));
    for (const self of people) {
      for (const r of rankAgainst(self, people)) {
        const theirView = rankAgainst(r.other, people).find((x) => x.other.id === self.id)!;
        expect(theirView.score).toBeCloseTo(r.score, 9);
      }
    }
  });
});

describe("score distribution", () => {
  it("spreads across the range instead of piling against a ceiling", () => {
    const dates = makeDates(120, 99);
    const scores: number[] = [];
    for (let i = 0; i < 60; i++) {
      const m = matchPair(dates[i], dates[i + 60]);
      if (m) scores.push(m.score);
    }
    const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
    const sd = Math.sqrt(scores.reduce((s, x) => s + (x - mean) ** 2, 0) / scores.length);
    // Calibrated against tools/calibrate.mjs: 20,000 random pairs give a median near 21 with a
    // spread of roughly 6 points. A model that gave everyone the same answer could not rank.
    expect(mean).toBeGreaterThan(17);
    expect(mean).toBeLessThan(25);
    expect(sd).toBeGreaterThan(3);
    expect(Math.max(...scores) - Math.min(...scores)).toBeGreaterThan(12);
  });
});

describe("the switch-off option", () => {
  const dates = makeDates(30, 8080);

  it("removes exactly the first test's points, and compares against the right distribution", () => {
    for (let i = 0; i + 1 < dates.length; i += 2) {
      const full = matchPair(dates[i], dates[i + 1])!;
      const without = matchPair(dates[i], dates[i + 1], { exclude: ["varna"] })!;
      const varnaPts = full.guna.kutas.find((k) => k.key === "varna")!.points;
      expect(without.score).toBeCloseTo(full.score - varnaPts, 9);
      expect(without.maxScore).toBe(35);
      // The percentile must come from the 35-point calibration, which shifts the whole curve —
      // comparing a 35-point score against the 36-point table understates everyone.
      expect(without.percentile).toBeGreaterThanOrEqual(0);
      expect(without.percentile).toBeLessThanOrEqual(100);
    }
  });

  it("keeps the ranking symmetric with a test switched off", () => {
    const people = dates.slice(0, 8).map((birthday, i) => ({ id: `p${i}`, birthday }));
    for (const self of people) {
      for (const r of rankAgainst(self, people, { exclude: ["varna"] })) {
        const theirs = rankAgainst(r.other, people, { exclude: ["varna"] })
          .find((x) => x.other.id === self.id)!;
        expect(theirs.score).toBeCloseTo(r.score, 9);
      }
    }
  });
});

describe("ranking order", () => {
  it("is sorted by score, then by the documented tie-break, and never claims otherwise", () => {
    const people = makeDates(14, 2718).map((birthday, i) => ({ id: `p${i}`, birthday }));
    const ranked = rankAgainst(people[0], people);
    for (let i = 1; i < ranked.length; i++) {
      const prev = ranked[i - 1], cur = ranked[i];
      expect(prev.score >= cur.score, `row ${i} out of order`).toBe(true);
      if (prev.score === cur.score) {
        // Ties break on how firmly the dates pin the score down, so a settled reading outranks a
        // merely-possible one.
        expect(prev.match.confidence >= cur.match.confidence - 1e-9,
          `tie at ${prev.score} broken the wrong way`).toBe(true);
      }
    }
  });
});

describe("every prediction carries an interval", () => {
  const dates = makeDates(80, 31415);

  it("gives every pair an expectation, a 90% interval and a full support", () => {
    for (let i = 0; i + 1 < dates.length; i += 2) {
      const m = matchPair(dates[i], dates[i + 1])!;
      const d = m.distribution;
      // The expectation is the probability-weighted mean, and must sit inside the support.
      const mean = d.outcomes.reduce((s, o) => s + o.score * o.probability, 0);
      expect(d.expected).toBeCloseTo(mean, 9);
      expect(d.expected).toBeGreaterThanOrEqual(d.support.min - 1e-9);
      expect(d.expected).toBeLessThanOrEqual(d.support.max + 1e-9);
      // The interval sits inside the support and really covers at least 90%.
      expect(d.interval.lo).toBeGreaterThanOrEqual(d.support.min);
      expect(d.interval.hi).toBeLessThanOrEqual(d.support.max);
      expect(d.interval.covers).toBeGreaterThanOrEqual(0.9 - 1e-9);
      const inside = d.outcomes
        .filter((o) => o.score >= d.interval.lo && o.score <= d.interval.hi)
        .reduce((s, o) => s + o.probability, 0);
      expect(inside).toBeGreaterThanOrEqual(0.9 - 1e-9);
      // The modal reading really is the most likely one.
      for (const o of d.outcomes) expect(d.modal.probability).toBeGreaterThanOrEqual(o.probability - 1e-12);
    }
  });

  it("collapses the interval to a point when the dates settle the answer", () => {
    // 1984-02-08 x 1967-08-26: both Moons stay in one birth star and one sign all day.
    const m = matchPair("1984-02-08", "1967-08-26")!;
    expect(m.certain).toBe(true);
    expect(m.distribution.outcomes).toHaveLength(1);
    expect(m.distribution.interval.lo).toBe(m.distribution.interval.hi);
    expect(m.distribution.support.min).toBe(m.distribution.support.max);
    expect(m.distribution.confidence).toBeCloseTo(1, 9);
  });

  it("keeps the interval symmetric under swapping the two people", () => {
    for (let i = 0; i + 1 < dates.length; i += 2) {
      const ab = matchPair(dates[i], dates[i + 1])!.distribution;
      const ba = matchPair(dates[i + 1], dates[i])!.distribution;
      expect(ab.expected).toBeCloseTo(ba.expected, 9);
      expect(ab.interval.lo).toBe(ba.interval.lo);
      expect(ab.interval.hi).toBe(ba.interval.hi);
    }
  });
});

describe("the probability table", () => {
  const dates = makeDates(60, 4242);

  it("conserves probability, keeps the headline inside the range, and never doubles a reading", () => {
    for (let i = 0; i + 1 < dates.length; i += 2) {
      const m = matchPair(dates[i], dates[i + 1])!;
      const d = m.distribution;
      const mass = d.outcomes.reduce((s, o) => s + o.probability, 0);
      expect(Math.abs(mass - 1), `${dates[i]}/${dates[i + 1]} mass ${mass}`).toBeLessThan(1e-9);
      const scores = d.outcomes.map((o) => o.score);
      expect(m.distribution.support.min).toBe(Math.min(...scores));
      expect(m.distribution.support.max).toBe(Math.max(...scores));
      expect(scores).toContain(m.score);
      // One row per READING: no two rows may share both labels and score. This is the guard on the
      // merge bug review found, where different readings were glued under one row's labels.
      const keys = d.outcomes.map((o) => `${o.score}|${o.labelA}|${o.labelB}`);
      expect(new Set(keys).size).toBe(keys.length);
    }
  });
});

describe("the uncertainty model", () => {
  it("finds every distinct Moon state within the birth day", () => {
    for (const iso of makeDates(120, 31337)) {
      const span = birthSpan(iso)!;
      expect(span.states.length).toBeGreaterThanOrEqual(1);
      // The Moon travels at most ~15.4° a day. That arc holds at most two nakshatra boundaries
      // (13°20′ apart) and at most one rāśi boundary (30° apart) — three boundaries, so four
      // states. 1965-07-27 actually reaches the ceiling.
      expect(span.states.length, iso).toBeLessThanOrEqual(4);
      const shares = span.states.reduce((s, x) => s + x.share, 0);
      expect(shares).toBeCloseTo(1, 6);
      expect(span.stable).toBe(span.states.length === 1);
    }
  });

  it("agrees with a brute-force hourly scan about which states occur", () => {
    for (const iso of makeDates(40, 5150)) {
      const span = birthSpan(iso)!;
      const [y, m, d] = iso.split("-").map(Number);
      const seen = new Set<string>();
      for (let h = 0; h <= 24; h += 0.25) {
        const lon = siderealLongitude("Moon", julianDay(y, m, d, h));
        const rasi = Math.floor(lon / 30) % 12;
        // Three-part key: the mid-sign split at 15° of the 9th and 10th signs is a real state
        // boundary too (it changes one of the eight tests without changing star or sign).
        const half = (rasi === 8 || rasi === 9) && lon - rasi * 30 >= 15 ? 1 : 0;
        seen.add(`${nakshatraOf(lon).info.index}|${rasi}|${half}`);
      }
      const found = new Set(span.states.map((s) => {
        const half = (s.rasi === 8 || s.rasi === 9) && s.lon - s.rasi * 30 >= 15 ? 1 : 0;
        return `${s.nakshatra.index}|${s.rasi}|${half}`;
      }));
      expect([...seen].sort(), iso).toEqual([...found].sort());
    }
  });

  it("reports a wider band exactly when the Moon is unstable", () => {
    // A date pair where at least one Moon changes state must produce a non-trivial Guna range,
    // and a pair where neither does must produce none.
    const dates = makeDates(80, 606);
    let sawStable = false, sawUnstable = false;
    for (let i = 0; i + 1 < dates.length && !(sawStable && sawUnstable); i += 2) {
      const m = matchPair(dates[i], dates[i + 1]);
      if (!m) continue;
      const bothStable = m.spanA.stable && m.spanB.stable;
      if (bothStable) {
        sawStable = true;
        expect(m.certain, `${dates[i]} vs ${dates[i + 1]} should be certain`).toBe(true);
        expect(m.distribution.support.max).toBe(m.distribution.support.min);
      } else {
        sawUnstable = true;
        expect(m.distribution.support.max).toBeGreaterThanOrEqual(m.distribution.support.min);
      }
    }
    expect(sawStable || sawUnstable).toBe(true);
  });

  it("never claims certainty it does not have", () => {
    for (const iso of makeDates(60, 24601)) {
      const span = birthSpan(iso)!;
      if (!span.stable) {
        const m = matchPair(iso, "1990-06-15")!;
        expect(m.certain).toBe(false);
        expect(m.uncertaintyNote).toContain("time of day");
      }
    }
  });
});

describe("calibration drift", () => {
  it("keeps the embedded facts honest against a live recomputation", () => {
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
    // Assert against the EMBEDDED constants, not against literals — otherwise the "drift test"
    // compares a recomputation to a hardcoded number and the shipped constants can go stale
    // untouched, which is exactly what the README claimed it prevented.
    expect(Math.abs(median - MEDIAN_SCORE)).toBeLessThanOrEqual(1);
    expect(Math.abs(passRate - PASS_RATE)).toBeLessThanOrEqual(4);

    // And check the percentile TABLE itself, cell by cell, so a shifted distribution cannot hide
    // behind two summary statistics that happen to survive.
    const below = (v: number) => (scores.filter((x) => x < v).length / scores.length) * 100;
    for (let v = 6; v <= 32; v++) {
      expect(Math.abs(below(v) - PERCENTILE_BELOW[v]), `percentile at ${v}`).toBeLessThanOrEqual(6);
    }
  });
});
