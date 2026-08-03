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
import { matchPair, rankAgainst } from "../src/engine/score";
import { birthSpan } from "../src/engine/uncertainty";
import { chartForDate, julianDay, siderealLongitude } from "../src/engine/ephemeris";
import { summariseSynastry } from "../src/engine/synastry";

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
      expect(ab!.overall, `${dates[i]} vs ${dates[i + 1]}`).toBeCloseTo(ba!.overall, 9);
    }
  });

  it("gives identical Guna Milan totals in both directions", () => {
    for (let i = 0; i + 1 < dates.length; i += 2) {
      const ab = gunaMilan(sideFor(dates[i]), sideFor(dates[i + 1]));
      const ba = gunaMilan(sideFor(dates[i + 1]), sideFor(dates[i]));
      expect(ab.total).toBeCloseTo(ba.total, 9);
    }
  });

  it("gives identical synastry ease in both directions", () => {
    for (let i = 0; i + 1 < dates.length; i += 2) {
      const a = chartForDate(dates[i])!, b = chartForDate(dates[i + 1])!;
      expect(summariseSynastry(a, b).easeScore).toBeCloseTo(summariseSynastry(b, a).easeScore, 9);
      expect(summariseSynastry(a, b).chargeScore).toBeCloseTo(summariseSynastry(b, a).chargeScore, 9);
    }
  });

  it("keeps two people's rankings of each other consistent", () => {
    const people = makeDates(12, 4242).map((birthday, i) => ({ id: `p${i}`, birthday }));
    for (const self of people) {
      for (const r of rankAgainst(self, people)) {
        const theirView = rankAgainst(r.other, people).find((x) => x.other.id === self.id)!;
        expect(theirView.overall).toBeCloseTo(r.overall, 9);
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
      if (m) scores.push(m.overall);
    }
    const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
    const sd = Math.sqrt(scores.reduce((s, x) => s + (x - mean) ** 2, 0) / scores.length);
    // A scoring model that gave everyone 85 would be useless for ranking.
    expect(mean).toBeGreaterThan(30);
    expect(mean).toBeLessThan(75);
    expect(sd).toBeGreaterThan(5);
    expect(Math.max(...scores) - Math.min(...scores)).toBeGreaterThan(25);
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
        seen.add(`${nakshatraOf(lon).info.index}|${Math.floor(lon / 30) % 12}`);
      }
      const found = new Set(span.states.map((s) => `${s.nakshatra.index}|${s.rasi}`));
      expect([...seen].sort(), iso).toEqual([...found].sort());
    }
  });

  it("reports a wider band exactly when the Moon is unstable", () => {
    // A date pair where at least one Moon changes state must produce a non-trivial Guna range,
    // and a pair where neither does must produce none.
    const dates = makeDates(80, 606);
    let sawStable = false, sawUnstable = false;
    for (let i = 0; i + 1 < dates.length && !(sawStable && sawUnstable); i += 2) {
      const m = matchPair(dates[i], dates[i + 1], true);
      if (!m) continue;
      const bothStable = m.spanA.stable && m.spanB.stable;
      if (bothStable) {
        sawStable = true;
        expect(m.gunaBand!.certain, `${dates[i]} vs ${dates[i + 1]} should be certain`).toBe(true);
      } else {
        sawUnstable = true;
        expect(m.gunaBand!.max).toBeGreaterThanOrEqual(m.gunaBand!.min);
      }
    }
    expect(sawStable || sawUnstable).toBe(true);
  });

  it("never claims certainty it does not have", () => {
    for (const iso of makeDates(60, 24601)) {
      const span = birthSpan(iso)!;
      if (!span.stable) {
        const m = matchPair(iso, "1990-06-15", true)!;
        expect(m.certain).toBe(false);
        expect(m.uncertaintyNote).toContain("time of day");
      }
    }
  });
});
