/**
 * Structural invariants of the 27-nakshatra table.
 *
 * The attribute table is hand-entered reference data, which is exactly the kind of thing a typo
 * hides in forever. These tests do not check individual rows against a source — they check
 * PROPERTIES that the real system has and a typo would break: the gana thirds, the Vimshottari lord
 * cycle, the palindromic nadi pattern, and the yoni animal census.
 */

import { describe, it, expect } from "vitest";
import { NAKSHATRAS, NAK_ARC, nakshatraOf, type Gana, type Nadi } from "../src/engine/nakshatra";

describe("the 27 nakshatras", () => {
  it("has exactly 27, numbered in order", () => {
    expect(NAKSHATRAS).toHaveLength(27);
    NAKSHATRAS.forEach((n, i) => {
      expect(n.index).toBe(i);
      expect(n.num).toBe(i + 1);
      expect(n.name.length).toBeGreaterThan(2);
    });
  });

  it("divides the ecliptic into 27 equal 13°20′ arcs", () => {
    expect(NAK_ARC).toBeCloseTo(13 + 20 / 60, 10);
    expect(nakshatraOf(0).info.name).toBe("Ashwini");
    expect(nakshatraOf(359.99).info.name).toBe("Revati");
    // Boundaries land where they should: the 4th nakshatra starts at 3 × 13°20′ = 40°.
    expect(nakshatraOf(39.99).info.num).toBe(3);
    expect(nakshatraOf(40.01).info.num).toBe(4);
  });

  it("assigns four padas per nakshatra, each 3°20′", () => {
    expect(nakshatraOf(0).pada).toBe(1);
    expect(nakshatraOf(3.33).pada).toBe(1);
    expect(nakshatraOf(3.34).pada).toBe(2);
    expect(nakshatraOf(13.32).pada).toBe(4);
    for (let deg = 0; deg < 360; deg += 0.37) {
      const p = nakshatraOf(deg).pada;
      expect(p).toBeGreaterThanOrEqual(1);
      expect(p).toBeLessThanOrEqual(4);
    }
  });

  it("splits the ganas into exact thirds — 9 deva, 9 manushya, 9 rakshasa", () => {
    const counts: Record<Gana, number> = { deva: 0, manushya: 0, rakshasa: 0 };
    for (const n of NAKSHATRAS) counts[n.gana]++;
    expect(counts).toEqual({ deva: 9, manushya: 9, rakshasa: 9 });
  });

  it("splits the nadis into exact thirds — 9 each", () => {
    const counts: Record<Nadi, number> = { adi: 0, madhya: 0, antya: 0 };
    for (const n of NAKSHATRAS) counts[n.nadi]++;
    expect(counts).toEqual({ adi: 9, madhya: 9, antya: 9 });
  });

  it("follows the Vimshottari lord cycle, repeating three times", () => {
    const cycle = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"];
    NAKSHATRAS.forEach((n, i) => {
      expect(n.lord, `${n.name} (#${i + 1})`).toBe(cycle[i % 9]);
    });
  });

  it("follows the palindromic nadi pattern", () => {
    // Ādi, Madhya, Antya, Antya, Madhya, Ādi, Ādi, Madhya, Antya — then the same nine reflected,
    // then the first nine again. A single transposed row breaks this immediately.
    const block1: Nadi[] = ["adi", "madhya", "antya", "antya", "madhya", "adi", "adi", "madhya", "antya"];
    const block2: Nadi[] = ["antya", "madhya", "adi", "adi", "madhya", "antya", "antya", "madhya", "adi"];
    const expected = [...block1, ...block2, ...block1];
    NAKSHATRAS.forEach((n, i) => {
      expect(n.nadi, `${n.name} (#${i + 1})`).toBe(expected[i]);
    });
  });

  it("uses 14 yoni animals, each twice except the lone mongoose", () => {
    const counts = new Map<string, number>();
    for (const n of NAKSHATRAS) counts.set(n.yoni, (counts.get(n.yoni) ?? 0) + 1);
    expect(counts.size).toBe(14);
    expect(counts.get("mongoose")).toBe(1); // Uttara Ashadha is the only one
    for (const [animal, count] of counts) {
      if (animal !== "mongoose") expect(count, animal).toBe(2);
    }
    // 13 × 2 + 1 = 27
    expect([...counts.values()].reduce((a, b) => a + b, 0)).toBe(27);
  });

  it("gives every nakshatra a yoni gender", () => {
    for (const n of NAKSHATRAS) {
      expect(["male", "female"]).toContain(n.yoniGender);
    }
  });
});
