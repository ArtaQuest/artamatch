/**
 * The browser scorer must agree with the fit that produced the weights.
 *
 * 200 corpus couples were scored in float64 by the Python closed-form fit, using Swiss Ephemeris
 * positions, and shipped inside the model file. This replays them through the TS engine.
 *
 * WHY THE TOLERANCE IS 0.01 AND NOT 1e-9. The fit used Swiss Ephemeris; the browser uses this
 * project's own built-in ephemeris, which is arcminute-accurate by design (tests/ephemeris.test.ts
 * holds it to per-body arcminute limits, the Moon to 2.5'). At k=1 an arcminute of longitude moves
 * a term by ~3e-4, and the measured spread over these 200 couples is: median score error 0.00017,
 * max 0.0068 — 0.34% of the corpus score IQR (2.00). In the only unit a reader sees, the PERCENTILE,
 * the worst displacement is 0.25 of one percentile point.
 *
 * These bounds are tight enough to catch what actually goes wrong — a dropped term, a flipped sign,
 * a broken table interpolation, a body index off by one — every one of which moves the score by
 * whole units, hundreds of times the ceiling here.
 */
import { describe, expect, it } from "vitest";
import model from "../src/data/tilldeath_model.json";
import { tillDeath } from "../src/engine/tilldeath";

const IQR = model.quantiles[300] - model.quantiles[100];

describe("till-death phasor model", () => {
  it("reproduces every shipped verification score", () => {
    let worst = 0;
    for (const v of model.verify as { dob_a: string; dob_b: string; score: number }[]) {
      worst = Math.max(worst, Math.abs(tillDeath(v.dob_a, v.dob_b).score - v.score));
    }
    expect(worst, `worst score error ${worst.toFixed(5)} (${(100 * worst / IQR).toFixed(2)}% of IQR)`)
      .toBeLessThan(0.01);
  });

  it("shows the same percentile the fit would", () => {
    const q = model.quantiles as number[];
    const pct = (s: number) => {
      let lo = 0, hi = q.length - 1;
      while (lo < hi) { const m = (lo + hi) >> 1; if (q[m] < s) lo = m + 1; else hi = m; }
      return lo / (q.length - 1);
    };
    let worst = 0;
    for (const v of model.verify as { dob_a: string; dob_b: string; score: number }[]) {
      worst = Math.max(worst, Math.abs(tillDeath(v.dob_a, v.dob_b).percentile - pct(v.score)));
    }
    expect(worst, `worst percentile shift ${(100 * worst).toFixed(3)} points`).toBeLessThan(0.005);
  });

  it("returns a usable report", () => {
    const r = tillDeath("1950-03-14", "1952-11-02");
    expect(r.percentile).toBeGreaterThanOrEqual(0);
    expect(r.percentile).toBeLessThanOrEqual(1);
    expect(r.p).toBeGreaterThan(0);
    expect(r.p).toBeLessThan(1);
    expect(r.drivers.length).toBe(8);
    expect(Math.abs(r.drivers[0].contribution)).toBeGreaterThanOrEqual(
      Math.abs(r.drivers[7].contribution));
  });

  it("is order-sensitive: the man's chart is not the woman's", () => {
    const a = tillDeath("1930-01-05", "1935-06-20").score;
    const b = tillDeath("1935-06-20", "1930-01-05").score;
    expect(Math.abs(a - b)).toBeGreaterThan(1e-6);
  });

  it("every term names a real body and a real trig function", () => {
    for (const t of model.terms as any[]) {
      expect(model.bodies[t.i]).toBeTruthy();
      if (t.j !== null) expect(model.bodies[t.j]).toBeTruthy();
      expect(["cos", "sin"]).toContain(t.trig);
      expect(Number.isFinite(t.w)).toBe(true);
    }
    expect((model.terms as any[]).length).toBe(48);
  });
});
