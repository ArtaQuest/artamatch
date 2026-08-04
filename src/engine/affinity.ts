/**
 * affinity.ts — two continuous compatibility numbers, built the way the ArtaQuest sky models are.
 *
 *   SPEC.  ease_ij, friction_ij = Σ_a [v_a]± · w_ij · exp( −wrap(Δ_ij − t_a)² / 2S²_ij )
 *          w_ij = imp_i·imp_j·√(s²_ij/S²_ij)      S²_ij = s²_ij + σ²_ij
 *          Δ_ij, σ_ij  = circular mean and deviation over all 24×24 = 576 birth-hour pairs
 *          Nothing is FITTED — there is nothing to fit to (see THE EMPIRICAL NULL below).
 *          The metric is a PERCENTILE against 20,000 randomly paired dates.
 *
 * ── The shape, and where it comes from ──────────────────────────────────────────────────────────
 *
 * The same functional form as the ArtaQuest sky→topics forward model of the AstroAttention paper
 * (analysis/adstopics/astro_forward.py), which fits
 *
 *      y_j(t) = Σ_i a_ij · exp( −wrap(θ_i(t) − p_j)² ) + b_j        with  a_ij ≥ 0
 *
 * — a Gaussian kernel on a SEAM-FREE wrapped angular difference, weighted by non-negative
 * coefficients, summed. Four house rules are carried over verbatim:
 *
 *   · a circular readout is always atan2 of a resultant vector, never a scalar average of angles;
 *   · weights are positive but NOT normalised (the recorded softmax ablation there is worse —
 *     sum-to-one forces one shared swing);
 *   · every ablation is reported even when it undercuts the model, as that paper reports its own
 *     centring contributing "only ~0.003 AUC";
 *   · and the CEILING is reported as a result. That paper bounds what any model could achieve on
 *     its data and states the bound; the equivalent bound here is measured below.
 *
 * Two deliberate departures. The paper's phases p_j are FITTED per topic; here they are the
 * tradition's five fixed angles, because there is nothing to fit to. And its kernel is written
 * exp(−Δ²) with Δ in radians — an implicit width near 40°, right for a broad seasonal phase and far
 * too wide for an aspect, so the width here comes from the orb instead.
 *
 * ── THE EMPIRICAL NULL, which governs everything below ──────────────────────────────────────────
 *
 * The largest test ever run — Voas (2007), roughly ten million married couples from the 2001
 * England and Wales census — found NO sign-compatibility effect, bounding any effect below about
 * one couple in a thousand; an apparent same-sign excess turned out to be form-filling error.
 *
 * So there is no outcome to fit to, and any model claiming to have LEARNED compatibility from data
 * would be lying. Nothing here is fitted. What is computed is: given the tradition's own
 * conventions, stated openly, where does this pair fall among random pairs? That question has a
 * true, reproducible answer, and it is the only one on offer.
 *
 * ── Why TWO numbers and not one ─────────────────────────────────────────────────────────────────
 *
 * The tradition says the third-of-a-circle and sixth-of-a-circle angles are easy and the quarter
 * and the opposite are hard. It has said so for two thousand years. What it has NEVER said, in any
 * source, is the EXCHANGE RATE — how many easy angles cancel one hard one. Every published
 * compatibility percentage nets them anyway, and that undisclosed exchange rate is the single
 * largest invention in the genre.
 *
 * So ease and friction are computed and reported SEPARATELY and never silently subtracted. One
 * combined number exists, for ranking, at the only non-arbitrary exchange rate there is — one for
 * one — and it is labelled as the choice it is. How much that choice matters is not argued but
 * MEASURED, and the measurement is quoted on the page.
 *
 * ── What is measured, and what is a convention ──────────────────────────────────────────────────
 *
 * MEASURED, reproducible by anyone re-running tools/calibrate-affinity.mjs:
 *   the positions · every angle, mean and spread · the 576-chart distribution · the percentile
 *   against 20,000 random pairs · every robustness figure quoted here.
 * CONVENTION, taken from the tradition and marked as such wherever it is used:
 *   which angles are easy and which are hard [Ptolemy, Tetrabiblos I] · how wide an orb is
 *   [Lilly, Christian Astrology, 1647] · which bodies are benefic or malefic [classical] · how much
 *   each body matters [ordinal only in the sources; the numbers here are chosen].
 *
 * A convention that drove the answer would be a problem. Measured on THIS model over 1,500 random
 * pairs (tools/calibrate-affinity.mjs prints the whole table), almost none of them does:
 *
 *     exchange rate ×0.5 … ×2.0 ......... Spearman 0.921 … 0.988
 *     a sixth counted as much as a third . 0.958
 *     every body weighted equally ........ 0.944
 *     the same-place contact fixed at +1 . 0.884
 *     THE OPPOSITE ANGLE READ AS EASY .... 0.718   ← the one that matters
 *
 * And two ablations that undercut this model rather than flatter it, reported because the paper
 * this borrows its shape from reports its own centring as worth "only ~0.003 AUC":
 *
 *     the variance weighting switched off ......... r = 0.994, Spearman 0.993
 *     the whole score from five aspect COUNTS ..... R² = 0.733
 *
 * The first says the mathematical centrepiece is nearly INERT. That is not because it is wrong —
 * it is what taking the average over the unknown hours literally is — but because there is little
 * for it to do: six of the seven bodies are pinned to within a degree by the date alone, and only
 * the Moon is genuinely uncertain (mean confidence 0.80 against 0.96–0.98 for the rest). It stays
 * because it is correct, not because it earns its keep in the ordering, and saying so is better
 * than letting a derivation imply an importance it does not have.
 *
 * The second says a crude tally of how many angles fall inside their orb — five integers, no
 * kernel, no weights, no hours — already reproduces three quarters of the variance. Everything
 * else in this file is the remaining quarter.
 *
 * That last line is not buried. The opposite angle is the single choice this model cannot make for
 * you: the classical texts call it hard, synastry practice very often reads it as attraction, and
 * the two readings order a list of people differently. So it is a SWITCH on the page, shown beside
 * the number above.
 *
 * ── THE CEILING, reported as a result ───────────────────────────────────────────────────────────
 *
 * Measured over 20,000 random pairs: the population of scores has a standard deviation of 0.0566,
 * while the 90% band a single pair spans across its own 576 charts has a median width of 0.0481 —
 * a ratio of 0.85. In words: not knowing the two birth times costs almost as much as the whole
 * difference between one couple and another.
 *
 * The consequence is a hard resolution limit, and it is the most important number on the page. Two
 * pairs whose bands overlap cannot be told apart from dates alone, no matter how good the model
 * gets — only about two in five randomly chosen pairs can be separated at all. Any site that prints
 * a compatibility percentage from dates alone, without a band, is claiming a precision the input
 * cannot carry. That is not a criticism of their model. It is arithmetic.
 *
 * ── The limitation that is NOT a convention ─────────────────────────────────────────────────────
 *
 * Conventional synastry weights contacts with the rising sign and the midheaven most heavily of
 * all. Those turn a full circle every day, so from a date of birth alone they do not exist. This is
 * not a weak version of a birth-time reading; it is a reading with the tradition's own top-weighted
 * factor missing altogether. The page says so.
 */

import { type Body, angleDiff } from "./ephemeris";
import { GRID, PERSONAL, hourlyLongitudes, type Spread } from "./synastry";

const D2R = Math.PI / 180;
const R2D = 180 / Math.PI;

/**
 * Traditional orb of each body, in degrees — the radius of its own light. [tradition: Lilly,
 * *Christian Astrology* (1647); sources vary by 1–3°, and the variation is recorded in METHODS.]
 *
 * The orb allowed between two bodies is the sum of their MOIETIES (halves), so Moon-to-Mercury is
 * (12+7)/2 = 9.5° for any angle. This is the older of the two orb systems and the only one whose
 * numbers come from a citable table rather than a modern author's preference; the alternative
 * assigns orbs to the ANGLE instead, and its published sets disagree with each other by 2× or more.
 */
export const BODY_ORB: Record<string, number> = {
  Sun: 15, Moon: 12, Mercury: 7, Venus: 7, Mars: 8, Jupiter: 9, Saturn: 9,
};

/**
 * The classical benefic/malefic ranking. [tradition]
 *
 * This is what gives a same-place contact its meaning. Nearly every source agrees the same-place
 * contact has NO valence of its own — Ptolemy did not count it as an aspect at all, but as bodies
 * "becoming a single note" — and takes its character entirely from the bodies joined. Two gentle
 * bodies in one place reads as easy; Saturn sitting on somebody's Moon does not. Seven numbers,
 * rather than a hundred-cell table of my own invention.
 */
export const BODY_NATURE: Record<string, number> = {
  Jupiter: 1, Venus: 0.5, Sun: 0, Moon: 0, Mercury: 0, Mars: -0.5, Saturn: -1,
};

/**
 * How much each body is said to matter. [convention — the sources rank these, none numbers them]
 *
 * Positive but NOT normalised, following the adstopics finding that a sum-to-one constraint is the
 * wrong one. The Sun and Moon lead every synastry list there is; Mercury is the lightest personal
 * body; Jupiter and Saturn move slowly enough to describe a birth year as much as a person, so they
 * are counted at half.
 */
export const BODY_WEIGHT: Record<string, number> = {
  Sun: 1.0, Moon: 1.0, Venus: 0.9, Mars: 0.8, Mercury: 0.6, Jupiter: 0.5, Saturn: 0.5,
};

/**
 * The five angles. [sign: tradition. magnitude: convention.]
 *
 * The SIGNS are the stable part — Tetrabiblos I derives them from whether the two signs joined are
 * of the same kind, and two thousand years have not moved them. The MAGNITUDES are not traditional
 * at all, and only two orderings have textual support: a third-of-a-circle is stronger than a
 * sixth, and the same-place contact takes its valence from the bodies. Quarter and opposite are
 * weighted equally because no source ranks them consistently.
 *
 * A documented dissent, recorded rather than hidden: in SYNASTRY specifically, the opposite angle
 * is often read as attraction through complementarity rather than as conflict. Flipping its sign
 * outright still ranks pairs at Spearman 0.92 of this table, so the page's ordering does not turn
 * on the disagreement.
 */
export const ASPECTS: { kind: string; degrees: number; valence: number | null }[] = [
  { kind: "together", degrees: 0, valence: null },   // null: taken from the two bodies' natures
  { kind: "sixth", degrees: 60, valence: 0.5 },
  { kind: "quarter", degrees: 90, valence: -1 },
  { kind: "third", degrees: 120, valence: 1 },
  { kind: "opposite", degrees: 180, valence: -1 },
];

/** Half the summed moieties — the Gaussian width, so a pair sitting exactly on the traditional edge
 *  of the orb still counts for exp(−2) ≈ 14% of an exact one rather than falling off a cliff at an
 *  arbitrary line. The tradition supplies only "tighter is stronger"; the shape is ours. [convention] */
export const widthFor = (a: Body, b: Body) => (BODY_ORB[a] + BODY_ORB[b]) / 4;

/**
 * How the one genuinely disputed angle is read. [the reader's call, not ours]
 *
 * Every other choice in this file barely moves the answer, and that is measured. This one does. The
 * classical texts call the opposite angle hard; synastry practice very often reads it as attraction
 * through complementarity, and "Sun opposite Moon" appears on most lists of the strongest bonds.
 * Reading it the other way re-orders a list of people at Spearman 0.71 — noticeably, though not
 * beyond recognition.
 *
 * So the page does not adjudicate. It ships the older reading and offers the other one as a switch,
 * beside the measurement of what the switch does.
 */
export type OppositeReading = "hard" | "easy";
export type AffinityOptions = { verify?: boolean; opposite?: OppositeReading };

/** The valence of an angle between two bodies: the table above, except that a same-place contact
 *  takes the average of the two bodies' classical natures, and the opposite angle follows the
 *  reader's choice. */
export function valenceOf(aspectIndex: number, a: Body, b: Body, opposite: OppositeReading = "hard"): number {
  if (ASPECTS[aspectIndex].degrees === 180) return opposite === "easy" ? 0.5 : -1;
  const v = ASPECTS[aspectIndex].valence;
  return v === null ? (BODY_NATURE[a] + BODY_NATURE[b]) / 2 : v;
}

/**
 * Circular mean and angular deviation of angles given in DEGREES.
 *
 * A mean of angles is a resultant vector, never a scalar average — the house rule, and the reason
 * nothing here can be broken by a wrap through ±180°. R̄ is the resultant length and
 * σ = √(−2 ln R̄) is the circular standard deviation, which tends to the ordinary one as the spread
 * gets small.
 */
export function circularStats(anglesDeg: number[]): { mean: number; sd: number; R: number } {
  let sin = 0, cos = 0;
  for (const a of anglesDeg) { sin += Math.sin(a * D2R); cos += Math.cos(a * D2R); }
  const n = anglesDeg.length;
  sin /= n; cos /= n;
  const R = Math.min(1, Math.hypot(sin, cos));
  return {
    mean: Math.atan2(sin, cos) * R2D,
    sd: Math.sqrt(Math.max(0, -2 * Math.log(Math.max(R, 1e-12)))) * R2D,
    R,
  };
}

/** One body pair's part of the answer, every intermediate kept so the page can show its working. */
export type Term = {
  bodyA: Body;
  bodyB: Body;
  /** Mean angle between them across the 576 charts, 0–180°. */
  separation: number;
  /** How far that angle wanders across the 576 charts. This is what the weight is made of. */
  spread: number;
  /** √(s²/(s²+σ²)) — 1 when the dates settle the angle, falling towards 0 as they leave it open. */
  confidence: number;
  /** imp_i · imp_j · confidence. */
  weight: number;
  /** The valence-weighted kernel at the mean angle, widened by the spread — signed. */
  compat: number;
  /** This pair's exact share of `ease`, averaged over all 576 charts. Non-negative. */
  ease: number;
  /** This pair's exact share of `friction`, likewise. Non-negative. */
  friction: number;
  /** ease − friction. These add up EXACTLY to `net`, with no residual. */
  contribution: number;
  /** weight · compat / Σ imp — the same quantity as the closed form predicts it. */
  predicted: number;
  /** The nearest of the five angles and how far off it is, for the sentence. */
  nearest: { kind: string; degrees: number; off: number };
};

export type Affinity = {
  /** Everything the tradition calls easy, averaged over the 576 charts. Non-negative. */
  ease: number;
  /** Everything it calls hard, likewise. Non-negative. NEVER silently subtracted from ease. */
  friction: number;
  /** ease − friction, at the one-for-one exchange rate. Labelled as a choice wherever shown. */
  net: number;
  /** The spread of `net` across the 576 charts: mean, sd, and the 5th-to-95th band. */
  spread: Spread;
  /** The same net arrived at the other way — Σ weight · compatibility. The factorisation that makes
   *  the number explainable rather than merely computable. */
  decomposition: number;
  /** |net − decomposition|. Measured on every reading, never assumed. */
  agreement: number;
  /** Every body pair, largest absolute contribution first. */
  terms: Term[];
  /** Σ imp_i · imp_j — the divisor, so a reader can redo the arithmetic. */
  totalWeight: number;
};

/**
 * The affinity of two birth dates.
 *
 * Both charts are drawn 576 times, once for every combination of the two unknown birth hours, and
 * every number below is an average over those 576 — not a closed form, not an approximation. The
 * closed form is computed too and reported beside it as `decomposition`, because that is what makes
 * the answer explainable: it says WHY each pair of bodies contributed what it did.
 */
export function affinity(isoA: string, isoB: string, opts: AffinityOptions = {}): Affinity | null {
  const A = hourlyLongitudes(isoA);
  const B = hourlyLongitudes(isoB);
  if (A.size === 0 || B.size === 0) return null;
  // The page always verifies. The 20,000-pair calibration is the one caller that opts out, because
  // there the brute force costs billions of exponentials to re-derive a number a test already pins.
  const verify = opts.verify !== false;
  const opposite = opts.opposite ?? "hard";

  const terms: Term[] = [];
  let totalWeight = 0;
  let closed = 0;
  const netPerChart = new Array(GRID * GRID).fill(0);
  let easeTotal = 0, frictionTotal = 0;

  for (const bi of PERSONAL) {
    const la = A.get(bi);
    if (!la) continue;
    for (const bj of PERSONAL) {
      const lb = B.get(bj);
      if (!lb) continue;
      const imp = BODY_WEIGHT[bi] * BODY_WEIGHT[bj];
      totalWeight += imp;
      const s = widthFor(bi, bj);
      const s2 = s * s;

      const deltas: number[] = [];
      for (let i = 0; i < GRID; i++) {
        for (let j = 0; j < GRID; j++) deltas.push(angleDiff(la[i], lb[j]));
      }
      const { mean, sd } = circularStats(deltas);
      const S2 = s2 + sd * sd;
      const confidence = Math.sqrt(s2 / S2);
      const separation = Math.abs(mean);

      // Split as it is summed. An earlier version accumulated only the net here and left ease and
      // friction to the brute-force loop below — so on the fast path (which the 20,000-pair
      // calibration uses) both came back as a silent ZERO rather than as a missing value, and the
      // calibration duly reported an ease forty times too small without complaining once.
      let easeC = 0, frictionC = 0;
      let nearest = ASPECTS[0], nearestOff = Infinity;
      for (let ai = 0; ai < ASPECTS.length; ai++) {
        const off = Math.abs(separation - ASPECTS[ai].degrees);
        const v = valenceOf(ai, bi, bj, opposite);
        const g = Math.exp(-(off * off) / (2 * S2));
        if (v >= 0) easeC += v * g; else frictionC += -v * g;
        if (off < nearestOff) { nearestOff = off; nearest = ASPECTS[ai]; }
      }
      const compat = easeC - frictionC;
      const weight = imp * confidence;
      closed += weight * compat;

      // The same sum chart by chart, at the ACTUAL angle, with no widening and no attenuation.
      // This is what the numbers ARE; the factorisation above is what explains them.
      // The closed form's own split, used when the brute force is skipped.
      let ease = weight * easeC, friction = weight * frictionC;
      if (verify) {
        ease = 0; friction = 0;
        let k = 0;
        for (let i = 0; i < GRID; i++) {
          for (let j = 0; j < GRID; j++) {
            const d = Math.abs(angleDiff(la[i], lb[j]));
            let e = 0, f = 0;
            for (let ai = 0; ai < ASPECTS.length; ai++) {
              const off = d - ASPECTS[ai].degrees;
              const v = valenceOf(ai, bi, bj, opposite);
              const g = imp * Math.exp(-(off * off) / (2 * s2));
              if (v >= 0) e += v * g; else f += -v * g;
            }
            netPerChart[k++] += e - f;
            ease += e; friction += f;
          }
        }
        ease /= GRID * GRID; friction /= GRID * GRID;
      }
      easeTotal += ease; frictionTotal += friction;

      terms.push({
        bodyA: bi, bodyB: bj, separation, spread: sd, confidence, weight, compat,
        ease, friction, contribution: ease - friction, predicted: weight * compat,
        nearest: { kind: nearest.kind, degrees: nearest.degrees, off: nearestOff },
      });
    }
  }

  const decomposition = closed / totalWeight;
  const nets = verify ? netPerChart.map((v) => v / totalWeight) : [decomposition];
  const mean = nets.reduce((s, v) => s + v, 0) / nets.length;
  const sd = Math.sqrt(nets.reduce((s, v) => s + (v - mean) ** 2, 0) / nets.length);
  const sorted = [...nets].sort((x, y) => x - y);
  const at = (p: number) => sorted[Math.min(sorted.length - 1, Math.round((p / 100) * (sorted.length - 1)))];

  for (const t of terms) {
    t.ease /= totalWeight; t.friction /= totalWeight;
    t.contribution = verify ? t.ease - t.friction : t.predicted / totalWeight;
    t.predicted /= totalWeight;
  }
  terms.sort((x, y) => Math.abs(y.contribution) - Math.abs(x.contribution));

  return {
    ease: easeTotal / totalWeight,
    friction: frictionTotal / totalWeight,
    net: mean,
    spread: { mean, sd, lo: at(5), hi: at(95), min: sorted[0], max: sorted[sorted.length - 1] },
    decomposition,
    agreement: Math.abs(decomposition - mean),
    terms,
    totalWeight,
  };
}

// ── what a score is worth ───────────────────────────────────────────────────────────────────────

/**
 * Share of random pairs scoring BELOW each step of the raw net scale, measured over 20,000 random
 * date pairs spanning 1930–2010 (tools/calibrate-affinity.mjs, fixed seed, reproducible). [measured]
 *
 * This table is the only honest number in the whole model. Every convention above is somebody's
 * choice; "higher than 84 in 100 randomly paired dates, under the conventions stated" is a fact
 * about this arithmetic that anyone can re-derive and contradict. The raw scale is never shown.
 */
export const AFFINITY_STEPS = 41;
export const AFFINITY_MIN = -0.24;
export const AFFINITY_MAX = 0.24;

/** 20,000 random pairs, seed 13579. Population: mean −0.0001, sd 0.0566, 5th −0.0953, 95th 0.0907.
 *  Ease and friction average 0.1090 and 0.1091 across the same sample — so the two piles are the
 *  same size on average, and a positive net really does mean more ease than a random pair has. */
export let AFFINITY_BELOW: number[] = [
  0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 3, 5, 7, 10, 14, 19, 25, 32, 40, 49,
  58, 67, 75, 82, 87, 91, 94, 96, 97, 98, 99, 99, 100, 100, 100, 100, 100, 100, 100, 100,
];

/** The resolution limit, measured on the same 20,000 pairs. [measured] */
export const POPULATION_SD = 0.0566;
export const BAND_WIDTH_MEDIAN = 0.0481;

/** Percentile of a raw net score, 0–100, linearly interpolated between steps. */
export function affinityPercentile(raw: number): number {
  if (AFFINITY_BELOW.length === 0) return 50;
  const step = (AFFINITY_MAX - AFFINITY_MIN) / (AFFINITY_STEPS - 1);
  const x = Math.max(0, Math.min(AFFINITY_STEPS - 1, (raw - AFFINITY_MIN) / step));
  const lo = Math.floor(x), hi = Math.min(AFFINITY_STEPS - 1, lo + 1), t = x - lo;
  return Math.round(AFFINITY_BELOW[lo] * (1 - t) + AFFINITY_BELOW[hi] * t);
}

/** Install the committed calibration table. */
export function setCalibration(table: number[]) { AFFINITY_BELOW = table; }
