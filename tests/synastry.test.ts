/**
 * The synastry layer's one real claim: that the probability attached to every connection is right.
 *
 * "Their Moons are a third of the circle apart, in 62% of the birth times the two dates allow" is a
 * strong sentence, and it is worthless if the 62% is decorative. So the closed form is checked here
 * against brute force — actually computing the two longitudes at 240×240 pairs of birth hours and
 * counting — over dates chosen to include the hard cases: a fast Moon, a planet turning round, a
 * body crossing 0° at midnight.
 */

import { describe, it, expect } from "vitest";
import { angleDiff, julianDay, parseDate, siderealLongitude, type Body } from "../src/engine/ephemeris";
import {
  ASPECTS, CONNECTIONS_HI, CONNECTIONS_LO, CONNECTIONS_MEDIAN, CONNECTIONS_VS_SCORE, PERSONAL,
  arcsFor, aspectProbability, diffOfUniformsCdf, narrate, orbFor, synastryGrid,
} from "../src/engine/synastry";
import { matchPair } from "../src/engine/score";
import { birthSpan } from "../src/engine/uncertainty";

const DATES = [
  "1999-12-06", "2004-12-27", "2004-12-21", "1965-07-27", "1988-02-29",
  "1943-06-11", "2011-09-30", "1975-01-01", "2000-03-15", "1957-10-04",
];

/** Longitude at each of N evenly spaced instants across the birth day. */
function samples(iso: string, body: Body, n: number): number[] {
  const d = parseDate(iso)!;
  return Array.from({ length: n }, (_, i) =>
    siderealLongitude(body, julianDay(d.y, d.m, d.d, ((i + 0.5) / n) * 24)));
}

describe("difference of two uniforms", () => {
  it("matches the analytic cases", () => {
    // X, Y ~ U(0,1): P(X−Y ≤ 0) = 1/2, and the tails are triangles.
    expect(diffOfUniformsCdf(0, 1, 1)).toBeCloseTo(0.5, 12);
    expect(diffOfUniformsCdf(0.5, 1, 1)).toBeCloseTo(0.875, 12);
    expect(diffOfUniformsCdf(-0.5, 1, 1)).toBeCloseTo(0.125, 12);
    expect(diffOfUniformsCdf(-1.0001, 1, 1)).toBe(0);
    expect(diffOfUniformsCdf(1.0001, 1, 1)).toBe(1);
  });

  it("handles a body that does not move", () => {
    // Y a point at 0 → Z = X ~ U(0,4).
    expect(diffOfUniformsCdf(1, 4, 0)).toBeCloseTo(0.25, 12);
    // X a point at 0 → Z = −Y ~ U(−4,0).
    expect(diffOfUniformsCdf(-1, 0, 4)).toBeCloseTo(0.75, 12);
    // Both points → deterministic 0.
    expect(diffOfUniformsCdf(-0.001, 0, 0)).toBe(0);
    expect(diffOfUniformsCdf(0, 0, 0)).toBe(1);
  });

  it("is a proper distribution — monotone, and 0 to 1 across the support", () => {
    let prev = -1;
    for (let z = -3; z <= 3; z += 0.05) {
      const v = diffOfUniformsCdf(z, 2, 1);
      expect(v).toBeGreaterThanOrEqual(prev - 1e-12);
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
      prev = v;
    }
    expect(diffOfUniformsCdf(-1.001, 2, 1)).toBe(0);
    expect(diffOfUniformsCdf(2.001, 2, 1)).toBe(1);
  });
});

describe("aspect probability vs brute force", () => {
  it("agrees with a 240×240 sweep of birth hours on every date pair and angle", () => {
    const N = 240;
    let worst = 0;
    let worstWhere = "";
    let compared = 0;

    for (let i = 0; i < DATES.length; i++) {
      for (let j = i + 1; j < DATES.length; j++) {
        const isoA = DATES[i], isoB = DATES[j];
        const arcsA = arcsFor(isoA, birthSpan(isoA)!.jdEstimate);
        const arcsB = arcsFor(isoB, birthSpan(isoB)!.jdEstimate);
        const sampA = new Map(PERSONAL.map((b) => [b, samples(isoA, b, N)]));
        const sampB = new Map(PERSONAL.map((b) => [b, samples(isoB, b, N)]));

        for (const a of arcsA) {
          for (const b of arcsB) {
            const orb = orbFor(a.body, b.body);
            const la = sampA.get(a.body)!, lb = sampB.get(b.body)!;
            for (const aspect of ASPECTS) {
              let hits = 0;
              for (let x = 0; x < N; x++) {
                for (let y = 0; y < N; y++) {
                  if (Math.abs(Math.abs(angleDiff(la[x], lb[y])) - aspect.degrees) <= orb) hits++;
                }
              }
              const brute = hits / (N * N);
              const exact = aspectProbability(a, b, aspect.degrees, orb);
              // Only the interesting cases: a pair that is nowhere near the angle agrees at 0 on
              // both sides and would flatter the measurement.
              if (brute === 0 && exact === 0) continue;
              compared++;
              const err = Math.abs(brute - exact);
              if (err > worst) {
                worst = err;
                worstWhere = `${isoA} ${a.body} / ${isoB} ${b.body} @ ${aspect.degrees}°: ` +
                  `closed form ${exact.toFixed(4)}, brute ${brute.toFixed(4)}`;
              }
            }
          }
        }
      }
    }

    // Every non-trivial case is compared, and the error is STATED rather than assumed. Measured
    // worst disagreement: 0.06 percentage points, and part of that is the 240×240 grid's own
    // coarseness rather than the closed form's. A single straight arc per body instead of twelve
    // pieces measured 1.73 points here — thirty times worse — which is why the pieces exist.
    expect(compared).toBeGreaterThan(300);
    expect(worst, `worst disagreement — ${worstWhere}`).toBeLessThan(0.002);
  }, 120_000);
});

describe("the 24 × 24 grid — the method the page reports", () => {
  it("agrees with the closed form about how often each connection holds", () => {
    // The grid is what the page shows, because "we drew both charts 576 times" is a sentence
    // anybody can follow. This is the check that the simple method is also the right one: 576
    // samples of a smooth quantity, against an exact area.
    let worst = 0, worstWhere = "", compared = 0;
    for (let i = 0; i < DATES.length; i++) {
      for (let j = i + 1; j < DATES.length; j++) {
        const isoA = DATES[i], isoB = DATES[j];
        const grid = synastryGrid(isoA, isoB);
        const arcsA = arcsFor(isoA, birthSpan(isoA)!.jdEstimate);
        const arcsB = arcsFor(isoB, birthSpan(isoB)!.jdEstimate);
        for (const c of grid.connections) {
          const a = arcsA.find((x) => x.body === c.bodyA)!;
          const b = arcsB.find((x) => x.body === c.bodyB)!;
          const exact = aspectProbability(a, b, c.aspect.degrees, c.orb);
          compared++;
          const err = Math.abs(exact - c.probability);
          if (err > worst) {
            worst = err;
            worstWhere = `${isoA} ${c.bodyA} / ${isoB} ${c.bodyB} @ ${c.aspect.degrees}°: ` +
              `grid ${c.probability.toFixed(4)}, closed form ${exact.toFixed(4)}`;
          }
        }
      }
    }
    expect(compared).toBeGreaterThan(200);
    // Measured: the grid's worst disagreement with the exact area is 1.9 points of probability,
    // and it lands where you would want it to — on a connection sitting right on the edge of its
    // orb, where the honest answer is "about two times in three" and nobody would act differently
    // on 62% than on 64%. Every connection that is settled, or nearly so, agrees far more closely.
    expect(worst, `worst grid-vs-exact gap — ${worstWhere}`).toBeLessThan(0.03);
  }, 60_000);

  it("never records two angles for the same pair of bodies", () => {
    for (const isoA of DATES) {
      for (const isoB of DATES) {
        if (isoA === isoB) continue;
        const cs = synastryGrid(isoA, isoB).connections;
        const seen = new Set(cs.map((c) => `${c.bodyA}|${c.bodyB}`));
        expect(seen.size).toBe(cs.length);
      }
    }
  });

  it("gives every connection a mean, a spread and a band that contains it", () => {
    const cs = synastryGrid(DATES[0], DATES[1]).connections;
    expect(cs.length).toBeGreaterThan(0);
    // Ordered by STRENGTH — closeness and certainty in one figure — not by probability, which
    // only ranks the planets by how slowly they move and shut the Moon out of the list entirely.
    for (let i = 1; i < cs.length; i++) {
      expect(cs[i].strength).toBeLessThanOrEqual(cs[i - 1].strength);
    }
    for (const c of cs) {
      expect(c.strength).toBeGreaterThan(0);
      expect(c.strength).toBeLessThanOrEqual(1);
      // Strength can never exceed how often the thing holds at all, nor claim more closeness
      // than the mean miss allows.
      expect(c.strength).toBeLessThanOrEqual(c.probability + 1e-9);
    }
    for (const c of cs) {
      expect(c.probability).toBeGreaterThan(0);
      expect(c.probability).toBeLessThanOrEqual(1);
      expect(c.orb).toBe(orbFor(c.bodyA, c.bodyB));
      for (const s of [c.separation, c.off]) {
        expect(s.sd).toBeGreaterThanOrEqual(0);
        expect(s.min).toBeLessThanOrEqual(s.lo);
        expect(s.lo).toBeLessThanOrEqual(s.hi);
        expect(s.hi).toBeLessThanOrEqual(s.max);
        expect(s.mean).toBeGreaterThanOrEqual(s.min - 1e-9);
        expect(s.mean).toBeLessThanOrEqual(s.max + 1e-9);
      }
      // A settled connection has nothing to be unsure about; an unsettled one must show it.
      if (c.certain) expect(c.off.max).toBeLessThanOrEqual(c.orb + 1e-9);
    }
  });

  it("counts the connections per chart, not once for the pair", () => {
    // The headline "they have 14 connections" is itself a prediction, so it carries its own
    // spread across the 576 charts — and the mean must be consistent with the individual shares.
    for (const [x, y] of [[DATES[0], DATES[1]], [DATES[3], DATES[4]], [DATES[6], DATES[9]]]) {
      const g = synastryGrid(x, y);
      const fromShares = g.connections.reduce((s, c) => s + c.probability, 0);
      expect(g.count.mean).toBeCloseTo(fromShares, 6);
      expect(g.count.min).toBeLessThanOrEqual(g.count.mean);
      expect(g.count.max).toBeGreaterThanOrEqual(g.count.mean);
    }
  });

  it("reads the same pair of dates the same way whichever is put first", () => {
    // Not symmetric in the readings (his Moon to her Venus is a different sentence from hers to
    // his) but the SET of connections must be a mirror image — anything else is a bug in the
    // arithmetic rather than a fact about the pair.
    const forward = synastryGrid(DATES[2], DATES[5]).connections;
    const reverse = synastryGrid(DATES[5], DATES[2]).connections;
    expect(reverse.length).toBe(forward.length);
    const key = (a: string, b: string, k: string) => `${a}|${b}|${k}`;
    const mirrored = new Map(reverse.map((c) => [key(c.bodyB, c.bodyA, c.kind), c]));
    for (const c of forward) {
      const other = mirrored.get(key(c.bodyA, c.bodyB, c.kind));
      expect(other, `${c.bodyA}/${c.bodyB} ${c.kind} missing when reversed`).toBeDefined();
      expect(other!.probability).toBeCloseTo(c.probability, 10);
      expect(other!.separation.mean).toBeCloseTo(c.separation.mean, 8);
    }
  });

  it("keeps the Moon in reach of the narrated list", () => {
    // The reason `strength` exists. Ranking by probability put the six slowest-moving pairs at the
    // top of every reading, so the Moon — the most personal body, and the one the entire score is
    // built from — was structurally unable to appear. Over a spread of real pairs it must now
    // reach the narrated six a fair share of the time.
    let withMoon = 0, pairs = 0;
    for (let i = 0; i < DATES.length; i++) {
      for (let j = i + 1; j < DATES.length; j++) {
        pairs++;
        const top = narrate(synastryGrid(DATES[i], DATES[j]).connections, 6);
        if (top.some((c) => c.bodyA === "Moon" || c.bodyB === "Moon")) withMoon++;
      }
    }
    expect(withMoon / pairs, `Moon narrated in ${withMoon} of ${pairs} pairs`).toBeGreaterThan(0.3);
  }, 30_000);

  it("never lets one planet fill the narrated list with itself", () => {
    for (let i = 0; i < DATES.length; i++) {
      for (let j = i + 1; j < DATES.length; j++) {
        const top = narrate(synastryGrid(DATES[i], DATES[j]).connections, 6);
        const perA = new Map<string, number>(), perB = new Map<string, number>();
        for (const c of top) {
          perA.set(c.bodyA, (perA.get(c.bodyA) ?? 0) + 1);
          perB.set(c.bodyB, (perB.get(c.bodyB) ?? 0) + 1);
        }
        for (const n of [...perA.values(), ...perB.values()]) expect(n).toBeLessThanOrEqual(2);
      }
    }
  }, 30_000);

  it("leaves the three slowest bodies out — they describe a generation, not a person", () => {
    for (const c of synastryGrid(DATES[0], DATES[3]).connections) {
      expect(PERSONAL).toContain(c.bodyA);
      expect(PERSONAL).toContain(c.bodyB);
    }
  });
});

describe("what a count of connections is worth", () => {
  it("keeps the numbers the page quotes honest against a live recomputation", () => {
    // The synastry section makes ONE claim that is not about this pair: that the number of
    // connections is meaningless, because everybody has ten to twenty and the count has nothing to
    // do with the score. Those figures are printed on screen, so they cannot be allowed to drift
    // away from what the code now produces. Recomputed here over a smaller sample than
    // tools/calibrate-synastry.mjs uses (20,000), with the tolerance a smaller sample deserves.
    let seed = 24680;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
    const date = () => {
      const y = 1930 + Math.floor(rnd() * 80);
      const m = 1 + Math.floor(rnd() * 12);
      const d = 1 + Math.floor(rnd() * 28);
      return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    };

    const counts: number[] = [], scores: number[] = [];
    for (let i = 0; i < 900; i++) {
      const a = date(), b = date();
      const m = matchPair(a, b);
      if (!m) continue;
      counts.push(synastryGrid(a, b).count.mean);
      scores.push(m.distribution.expected);
    }
    const sorted = [...counts].sort((x, y) => x - y);
    const at = (p: number) => sorted[Math.floor((p / 100) * sorted.length)];
    const mean = (xs: number[]) => xs.reduce((s, v) => s + v, 0) / xs.length;
    const mc = mean(counts), ms = mean(scores);
    const rho = counts.reduce((s, _, i) => s + (counts[i] - mc) * (scores[i] - ms), 0) /
      Math.sqrt(counts.reduce((s, v) => s + (v - mc) ** 2, 0) *
        scores.reduce((s, v) => s + (v - ms) ** 2, 0));

    expect(Math.round(at(50)), "median connections").toBe(CONNECTIONS_MEDIAN);
    expect(Math.abs(at(5) - CONNECTIONS_LO), `5th percentile now ${at(5).toFixed(1)}`).toBeLessThan(1.5);
    expect(Math.abs(at(95) - CONNECTIONS_HI), `95th percentile now ${at(95).toFixed(1)}`).toBeLessThan(1.5);
    // The claim on the page is "not at all", so what has to hold is that it stays near zero — not
    // that it reproduces 0.03 to the digit on a twentieth of the sample.
    expect(Math.abs(rho), `correlation with the score is now ${rho.toFixed(3)}`).toBeLessThan(0.12);
    expect(CONNECTIONS_VS_SCORE).toBeLessThan(0.1);
  }, 120_000);
});
