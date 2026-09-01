/**
 * tilldeath.ts — the shipped "Till Death Do Us Part" model, scored in the browser.
 *
 * score = bias + Σ w · trig(angle),   p = sigmoid(score)
 *
 * where every angle is built from two SIDEREAL birth charts at noon UT and nothing else. The 48
 * terms, their weights and the corpus score distribution all come from tilldeath_model.json,
 * fitted in closed form (three Newton steps) over 175,155 wiki marriages.
 *
 * Ten bodies come from the built-in ephemeris; true node, Chiron and mean Lilith are interpolated
 * from tilldeath_tables.json, sampled through the same Swiss Ephemeris path the corpus used.
 * tests/tilldeath.test.ts replays 200 corpus couples and fails if this file disagrees with the
 * fit by more than 1e-3 — a browser scorer that silently drifts has cost this project before.
 */
import model from "../data/tilldeath_model.json";
import tables from "../data/tilldeath_tables.json";
import { julianDay, siderealLongitude, type Body } from "./ephemeris";

const DEG = Math.PI / 180;

type Term = {
  trig: "cos" | "sin";
  kind: "diff" | "natM" | "natW" | "sum" | "aspM" | "aspW" | "midM" | "midW";
  i: number;
  j: number | null;
  w: number;
  label: string;
};

const TERMS = model.terms as Term[];
const BODIES = model.bodies as string[];
const BUILTIN: Record<string, Body> = {
  sun: "Sun", moon: "Moon", mercury: "Mercury", venus: "Venus", mars: "Mars",
  jupiter: "Jupiter", saturn: "Saturn", uranus: "Uranus", neptune: "Neptune", pluto: "Pluto",
};

/** table body → sidereal longitude in degrees, linear between samples */
function fromTable(name: "node" | "chiron" | "lilith", jd: number): number {
  const t = (tables as any)[name] as { step: number; v: number[] };
  const x = (jd - (tables as any).jd0) / t.step;
  const k = Math.max(0, Math.min(t.v.length - 2, Math.floor(x)));
  const f = x - k;
  const a = t.v[k] / 1000, b = t.v[k + 1] / 1000;
  // unwrap across the 360° seam before interpolating, or a wrap becomes a 359° sweep
  let d = b - a;
  if (d > 180) d -= 360;
  if (d < -180) d += 360;
  return (((a + f * d) % 360) + 360) % 360;
}

/** all 13 body longitudes (radians) for one birth date at noon UT */
export function chartRad(iso: string): number[] {
  const y = +iso.slice(0, 4), m = +iso.slice(5, 7), d = +iso.slice(8, 10);
  const jd = julianDay(y, m, d, 12);
  return BODIES.map((b) =>
    BUILTIN[b] !== undefined
      ? siderealLongitude(BUILTIN[b], jd) * DEG
      : fromTable(b as "node" | "chiron" | "lilith", jd) * DEG,
  );
}

function angleOf(t: Term, A: number[], B: number[]): number {
  switch (t.kind) {
    case "diff": return A[t.i] - B[t.i];
    case "natM": return A[t.i];
    case "natW": return B[t.i];
    case "sum":  return A[t.i] + B[t.i];
    case "aspM": return A[t.i] - A[t.j!];
    case "aspW": return B[t.i] - B[t.j!];
    case "midM": return A[t.i] + A[t.j!];
    case "midW": return B[t.i] + B[t.j!];
  }
}

export type TillDeath = {
  /** the raw linear score — the quantity the model is actually fitted on */
  score: number;
  /** sigmoid(score): the model's probability that this marriage came apart */
  p: number;
  /** where this score falls among all 175,155 corpus couples, 0..1 */
  percentile: number;
  /** the terms that moved this couple most, strongest first */
  drivers: { label: string; contribution: number }[];
};

/** score one couple from two birth dates (ISO, YYYY-MM-DD). Man first, as the corpus was built. */
export function tillDeath(manISO: string, womanISO: string): TillDeath {
  const A = chartRad(manISO), B = chartRad(womanISO);
  let score = model.bias;
  const parts: { label: string; contribution: number }[] = [];
  for (const t of TERMS) {
    const a = angleOf(t, A, B);
    const c = t.w * (t.trig === "cos" ? Math.cos(a) : Math.sin(a));
    score += c;
    parts.push({ label: t.label, contribution: c });
  }
  const q = model.quantiles as number[];
  let lo = 0, hi = q.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (q[mid] < score) lo = mid + 1; else hi = mid;
  }
  parts.sort((x, y) => Math.abs(y.contribution) - Math.abs(x.contribution));
  return {
    score,
    p: 1 / (1 + Math.exp(-score)),
    percentile: lo / (q.length - 1),
    drivers: parts.slice(0, 8),
  };
}

export const TILLDEATH_META = {
  edition: model.edition,
  cvAuc: model.cv_auc_broad,
  strict: model.strict_five_seed,
  nCorpus: model.n_corpus,
  nPositive: model.n_positive,
  nTerms: TERMS.length,
};
