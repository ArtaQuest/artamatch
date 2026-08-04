/**
 * The affinity model makes exactly one kind of claim that can be wrong on its own terms.
 *
 * It cannot be wrong about compatibility — there is nothing to be right about; the largest test
 * ever run (Voas 2007, ~10 million married couples) found no effect at all. What it CAN be wrong
 * about is arithmetic: whether the number it prints is the average of the 576 charts it says it is,
 * whether the explanation adds up to the answer, whether it says the same thing when you swap the
 * two people, and whether the conventions nobody can source are quietly steering the result.
 *
 * Those are the tests. Every one of them is a statement the page makes out loud.
 */

import { describe, it, expect } from "vitest";
import {
  affinity, circularStats, valenceOf, widthFor, ASPECTS, BODY_ORB, BODY_NATURE, BODY_WEIGHT,
  affinityPercentile, AFFINITY_BELOW,
} from "../src/engine/affinity";
import { PERSONAL, GRID, hourlyLongitudes } from "../src/engine/synastry";
import { angleDiff, type Body } from "../src/engine/ephemeris";

const DATES = [
  "1999-12-06", "2004-12-27", "2004-12-21", "1994-02-15", "1965-07-27",
  "1988-02-29", "1943-06-11", "2011-09-30", "1975-01-01", "1957-10-04",
];

describe("circular statistics", () => {
  it("means angles as a resultant vector, not as a scalar average", () => {
    // The whole reason for the house rule. A naive mean of 359° and 1° is 180° — the exact
    // opposite of the truth, and the kind of error that would silently turn a same-place contact
    // into an opposite one.
    expect(circularStats([359, 1]).mean).toBeCloseTo(0, 9);
    expect(circularStats([-179, 179]).mean).toBeCloseTo(180, 6);
    expect(circularStats([10, 20, 30]).mean).toBeCloseTo(20, 6);
  });

  it("reports a spread that grows with the spread and vanishes without one", () => {
    expect(circularStats([45, 45, 45]).sd).toBeCloseTo(0, 9);
    expect(circularStats([40, 50]).sd).toBeGreaterThan(0);
    expect(circularStats([0, 90]).sd).toBeGreaterThan(circularStats([40, 50]).sd);
    // For a small spread the circular deviation agrees with the ordinary one.
    const xs = [10, 11, 12, 13, 14];
    const m = xs.reduce((a, b) => a + b, 0) / xs.length;
    const plain = Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length);
    expect(circularStats(xs).sd).toBeCloseTo(plain, 2);
  });
});

describe("the constants are what they claim to be", () => {
  it("uses the moiety rule on the traditional orbs, not an orb per angle", () => {
    // Lilly's table, and the rule that an orb belongs to the BODY: the allowance between two of
    // them is the sum of their halves. Moon (12) to Mercury (7) is 9.5°, so the Gaussian width is
    // half of that.
    expect((BODY_ORB.Moon + BODY_ORB.Mercury) / 2).toBe(9.5);
    expect(widthFor("Moon", "Mercury")).toBeCloseTo(4.75, 9);
    expect(widthFor("Sun", "Sun")).toBeCloseTo(7.5, 9);
    for (const b of PERSONAL) expect(BODY_ORB[b]).toBeGreaterThan(0);
  });

  it("gives the same-place contact no valence of its own — it takes the bodies'", () => {
    // The strongest consensus in the whole system, and the reason there is no 49-cell table here.
    expect(ASPECTS[0].degrees).toBe(0);
    expect(ASPECTS[0].valence).toBeNull();
    expect(valenceOf(0, "Venus", "Jupiter")).toBeCloseTo(0.75, 9);   // two gentle bodies
    expect(valenceOf(0, "Saturn", "Mars")).toBeCloseTo(-0.75, 9);    // two harsh ones
    expect(valenceOf(0, "Sun", "Mercury")).toBeCloseTo(0, 9);        // two neutral ones
    expect(BODY_NATURE.Jupiter).toBeGreaterThan(BODY_NATURE.Venus);
    expect(BODY_NATURE.Saturn).toBeLessThan(BODY_NATURE.Mars);
  });

  it("keeps every body weight positive, and does not normalise them", () => {
    // Positive yes, normalised no — the recorded adstopics ablation: a sum-to-one constraint
    // forces one shared swing and is measurably the wrong one.
    const ws = PERSONAL.map((b) => BODY_WEIGHT[b]);
    for (const w of ws) expect(w).toBeGreaterThan(0);
    expect(ws.reduce((a, b) => a + b, 0)).not.toBeCloseTo(1, 6);
  });

  it("offers the reader the one choice it cannot make for them", () => {
    expect(valenceOf(4, "Sun", "Moon", "hard")).toBeLessThan(0);
    expect(valenceOf(4, "Sun", "Moon", "easy")).toBeGreaterThan(0);
    // and nothing else changes with it
    for (let i = 0; i < 4; i++) {
      expect(valenceOf(i, "Sun", "Moon", "hard")).toBe(valenceOf(i, "Sun", "Moon", "easy"));
    }
  });
});

describe("the number is the average of the 576 charts", () => {
  it("matches a fully independent brute-force recomputation", () => {
    // Written out longhand here rather than reusing anything the engine does, so this is a check
    // of the model and not of itself.
    for (const [x, y] of [[DATES[0], DATES[2]], [DATES[4], DATES[5]], [DATES[6], DATES[7]]]) {
      const A = hourlyLongitudes(x), B = hourlyLongitudes(y);
      let total = 0, denom = 0;
      for (const bi of PERSONAL) {
        for (const bj of PERSONAL) {
          const imp = BODY_WEIGHT[bi] * BODY_WEIGHT[bj];
          denom += imp;
          const s = widthFor(bi as Body, bj as Body);
          for (let i = 0; i < GRID; i++) {
            for (let j = 0; j < GRID; j++) {
              const d = Math.abs(angleDiff(A.get(bi)![i], B.get(bj)![j]));
              for (let ai = 0; ai < ASPECTS.length; ai++) {
                const off = d - ASPECTS[ai].degrees;
                total += imp * valenceOf(ai, bi as Body, bj as Body) *
                  Math.exp(-(off * off) / (2 * s * s));
              }
            }
          }
        }
      }
      const longhand = total / (denom * GRID * GRID);
      expect(affinity(x, y)!.net, `${x} x ${y}`).toBeCloseTo(longhand, 12);
    }
  }, 60_000);

  it("explains itself exactly — the parts add up to the whole with no residual", () => {
    // The strongest explainability property available: not "these are the main reasons" but "these
    // ARE the answer". A page that showed a decomposition failing to sum would be illustrating,
    // not explaining.
    for (const x of DATES.slice(0, 5)) {
      for (const y of DATES.slice(5)) {
        const r = affinity(x, y)!;
        const sum = r.terms.reduce((s, t) => s + t.contribution, 0);
        expect(Math.abs(sum - r.net), `${x} x ${y}`).toBeLessThan(1e-12);
        const ease = r.terms.reduce((s, t) => s + t.ease, 0);
        const friction = r.terms.reduce((s, t) => s + t.friction, 0);
        expect(ease).toBeCloseTo(r.ease, 12);
        expect(friction).toBeCloseTo(r.friction, 12);
        expect(r.ease - r.friction).toBeCloseTo(r.net, 12);
      }
    }
  }, 60_000);

  it("keeps the closed form honest about how well it approximates the average", () => {
    // The factorisation is what makes the score EXPLAINABLE — weight from how well the angle is
    // known, compatibility from the mean angle — but it assumes a bell where the truth is a
    // trapezoid. The gap is reported on every reading, and it has to stay small enough that no
    // sentence built on the decomposition contradicts the number beside it.
    let worst = 0, where = "";
    for (const x of DATES) {
      for (const y of DATES) {
        if (x === y) continue;
        const r = affinity(x, y)!;
        if (r.agreement > worst) { worst = r.agreement; where = `${x} x ${y}`; }
      }
    }
    // The population spread of the score is about 0.056, so this is under 5% of one standard
    // deviation — well under one percentile point.
    expect(worst, `worst closed-form gap at ${where}`).toBeLessThan(0.0025);
  }, 60_000);

  it("gives the same answer whichever person is put first", () => {
    for (const x of DATES.slice(0, 4)) {
      for (const y of DATES.slice(4, 8)) {
        const forward = affinity(x, y)!, reverse = affinity(y, x)!;
        expect(reverse.net, `${x} / ${y}`).toBeCloseTo(forward.net, 12);
        expect(reverse.ease).toBeCloseTo(forward.ease, 12);
        expect(reverse.friction).toBeCloseTo(forward.friction, 12);
        // The ROWS are not symmetric, and should not be: your Sun to their Moon is a different
        // angle from your Moon to their Sun. They mirror.
        const key = (t: { bodyA: string; bodyB: string }) => `${t.bodyB}|${t.bodyA}`;
        const mirrored = new Map(reverse.terms.map((t) => [key(t), t]));
        for (const t of forward.terms) {
          const m = mirrored.get(`${t.bodyA}|${t.bodyB}`);
          expect(m).toBeDefined();
          expect(m!.contribution).toBeCloseTo(t.contribution, 12);
        }
      }
    }
  }, 60_000);

  it("never nets ease and friction behind the reader's back", () => {
    for (const x of DATES.slice(0, 4)) {
      const r = affinity(x, DATES[8])!;
      expect(r.ease).toBeGreaterThanOrEqual(0);
      expect(r.friction).toBeGreaterThanOrEqual(0);
      // Both are real quantities, not one number with a sign put on it.
      expect(r.ease).toBeGreaterThan(0);
      expect(r.friction).toBeGreaterThan(0);
    }
  });

  it("puts a band around every number, and the band contains it", () => {
    for (const x of DATES.slice(0, 3)) {
      for (const y of DATES.slice(3, 6)) {
        const r = affinity(x, y)!;
        expect(r.spread.min).toBeLessThanOrEqual(r.spread.lo);
        expect(r.spread.lo).toBeLessThanOrEqual(r.net);
        expect(r.net).toBeLessThanOrEqual(r.spread.hi);
        expect(r.spread.hi).toBeLessThanOrEqual(r.spread.max);
        expect(r.spread.sd).toBeGreaterThan(0);
      }
    }
  });

  it("refuses a date it cannot chart", () => {
    expect(affinity("2001-02-29", DATES[0])).toBeNull();
    expect(affinity(DATES[0], "not-a-date")).toBeNull();
  });
});

describe("the conventions are not steering the answer", () => {
  /** Rank correlation, the measure the page quotes. */
  function spearman(x: number[], y: number[]): number {
    const rank = (xs: number[]) => {
      const ix = xs.map((v, i) => [v, i] as const).sort((a, b) => a[0] - b[0]);
      const r = new Array(xs.length);
      ix.forEach(([, i], k) => (r[i] = k));
      return r;
    };
    const [rx, ry] = [rank(x), rank(y)];
    const mx = rx.reduce((a, b) => a + b, 0) / rx.length;
    const my = ry.reduce((a, b) => a + b, 0) / ry.length;
    let n = 0, dx = 0, dy = 0;
    for (let i = 0; i < rx.length; i++) {
      n += (rx[i] - mx) * (ry[i] - my); dx += (rx[i] - mx) ** 2; dy += (ry[i] - my) ** 2;
    }
    return n / Math.sqrt(dx * dy);
  }

  const pairs: [string, string][] = [];
  let seed = 20260804;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
  const date = () => {
    const y = 1930 + Math.floor(rnd() * 80), m = 1 + Math.floor(rnd() * 12), d = 1 + Math.floor(rnd() * 28);
    return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  };
  for (let i = 0; i < 200; i++) pairs.push([date(), date()]);
  const run = (o: Parameters<typeof affinity>[2] = {}) =>
    pairs.map(([a, b]) => affinity(a, b, { verify: false, ...o })!.net);

  it("orders people almost identically however the disputed angle is read — except one", () => {
    // This is the page's own claim, pinned. Everything the sources leave open barely moves the
    // ordering; the one documented dissent moves it enough to be worth a switch, and that number
    // is quoted on screen, so it must not drift silently.
    const base = run();
    const flipped = run({ opposite: "easy" });
    const rho = spearman(base, flipped);
    expect(rho, `opposite-as-easy now ranks at ${rho.toFixed(3)}`).toBeGreaterThan(0.6);
    expect(rho, "if this rises above 0.85 the switch is no longer worth offering")
      .toBeLessThan(0.85);
  }, 60_000);

  it("spreads the answer across the whole chart rather than only the well-pinned bodies", () => {
    // The weighting damps an angle the dates leave vague, and the Moon is the vaguest thing there
    // is. If that quietly reduced the Moon to a rounding error, "it reads the whole chart" would be
    // false. Measured: the Moon still carries about a fifth of the answer, second only to the Sun.
    const share = new Map<string, number>();
    for (const [a, b] of pairs.slice(0, 60)) {
      for (const t of affinity(a, b)!.terms) {
        share.set(t.bodyA, (share.get(t.bodyA) ?? 0) + Math.abs(t.contribution));
        share.set(t.bodyB, (share.get(t.bodyB) ?? 0) + Math.abs(t.contribution));
      }
    }
    const total = [...share.values()].reduce((a, b) => a + b, 0);
    const moon = share.get("Moon")! / total;
    expect(moon, `the Moon carries ${(moon * 100).toFixed(1)}% of the answer`).toBeGreaterThan(0.12);
    for (const b of PERSONAL) expect(share.get(b)! / total).toBeGreaterThan(0.05);
  }, 60_000);

  it("is not degenerate — it actually tells pairs apart", () => {
    const xs = run().sort((a, b) => a - b);
    const mean = xs.reduce((a, b) => a + b, 0) / xs.length;
    const sd = Math.sqrt(xs.reduce((a, b) => a + (b - mean) ** 2, 0) / xs.length);
    expect(sd).toBeGreaterThan(0.03);
    expect(xs[xs.length - 1] - xs[0]).toBeGreaterThan(6 * sd * 0.5);
  }, 30_000);
});

describe("the percentile — the only measured number in the model", () => {
  it("is monotone, bounded, and built from a committed table", () => {
    expect(AFFINITY_BELOW.length).toBeGreaterThan(0);
    let prev = -1;
    for (let raw = -0.3; raw <= 0.3; raw += 0.005) {
      const p = affinityPercentile(raw);
      expect(p).toBeGreaterThanOrEqual(0);
      expect(p).toBeLessThanOrEqual(100);
      expect(p).toBeGreaterThanOrEqual(prev);
      prev = p;
    }
    expect(affinityPercentile(-1)).toBe(0);
    expect(affinityPercentile(1)).toBe(100);
  });

  it("puts the middle of the random population near the middle of the scale", () => {
    let seed = 31337;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
    const date = () => {
      const y = 1930 + Math.floor(rnd() * 80), m = 1 + Math.floor(rnd() * 12), d = 1 + Math.floor(rnd() * 28);
      return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    };
    const ps: number[] = [];
    for (let i = 0; i < 300; i++) ps.push(affinityPercentile(affinity(date(), date(), { verify: false })!.net));
    ps.sort((a, b) => a - b);
    const median = ps[Math.floor(ps.length / 2)];
    expect(median, `median percentile is ${median}`).toBeGreaterThan(38);
    expect(median).toBeLessThan(62);
    // and the scale is used, not bunched
    expect(ps[Math.floor(ps.length * 0.05)]).toBeLessThan(20);
    expect(ps[Math.floor(ps.length * 0.95)]).toBeGreaterThan(80);
  }, 60_000);
});
