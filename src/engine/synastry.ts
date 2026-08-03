/**
 * synastry.ts — inter-chart aspects between two people, on SIDEREAL longitudes.
 *
 * This is the layer that answers "how do these two charts talk to each other", the way a Western
 * synastry report does — but measured in the sidereal zodiac, so it agrees with the Guna Milan layer
 * next door rather than quietly using a different zodiac for each half of the report.
 *
 * Two design decisions here matter more than any of the numbers:
 *
 * 1. OUTER-TO-OUTER ASPECTS ARE NEARLY WEIGHTLESS. Uranus, Neptune and Pluto take 84, 165 and 248
 *    years to go round. Everyone born within a few years of you shares your Uranus–Neptune angle, so
 *    counting those aspects as compatibility would score every pair of age-peers as soulmates and
 *    every cross-generational pair as doomed. It measures a birth cohort, not a relationship. Naive
 *    matchers get this wrong and it is the single largest systematic error available here.
 *
 * 2. THE SCORE IS SYMMETRIC. compatibility(A,B) must equal compatibility(B,A) or a ranked list is
 *    incoherent — A's list and B's list would disagree about the same pair. Symmetry is guaranteed
 *    structurally: the full cross-product of bodies is always evaluated, and PAIR_WEIGHT is defined
 *    on the UNORDERED pair. There is a property test that asserts it over random dates.
 */

import { type Body, type Chart, type Placement, BODIES, separation } from "./ephemeris";

export type AspectType =
  | "conjunction" | "opposition" | "trine" | "square" | "sextile"
  | "quincunx" | "sesquiquadrate" | "quintile" | "semisquare" | "semisextile";

export type AspectDef = {
  type: AspectType;
  angle: number;
  /** Base orb in degrees; widened by LUMINARY_BONUS when the Sun or Moon is involved. */
  orb: number;
  /** Major aspects carry full weight; minor ones are shown but barely move the score. */
  major: boolean;
  /** The plain-English name shown to a reader. The traditional term is kept in `label` for anyone
   *  who knows it, but it is never the only thing on screen. */
  plain: string;
  /** −1 friction … +1 ease. The conjunction is 0 because its quality depends on WHICH bodies meet
   *  (Venus with Jupiter is not Mars with Saturn) — it is resolved from body valence instead. */
  valence: number;
  label: string;
};

export const ASPECTS: AspectDef[] = [
  { type: "conjunction",    angle: 0,   orb: 8, major: true,  valence: 0,     label: "conjunction",    plain: "sitting together" },
  { type: "opposition",     angle: 180, orb: 8, major: true,  valence: -0.35, label: "opposition",     plain: "facing each other" },
  { type: "trine",          angle: 120, orb: 7, major: true,  valence: 1,     label: "trine",          plain: "flowing together" },
  { type: "square",         angle: 90,  orb: 7, major: true,  valence: -0.85, label: "square",         plain: "pulling against" },
  { type: "sextile",        angle: 60,  orb: 5, major: true,  valence: 0.7,   label: "sextile",        plain: "helping along" },
  { type: "quincunx",       angle: 150, orb: 3, major: false, valence: -0.5,  label: "quincunx",       plain: "not quite meeting" },
  { type: "sesquiquadrate", angle: 135, orb: 2, major: false, valence: -0.4,  label: "sesquiquadrate", plain: "niggling at" },
  { type: "quintile",       angle: 72,  orb: 2, major: false, valence: 0.5,   label: "quintile",       plain: "sparking off" },
  { type: "semisquare",     angle: 45,  orb: 2, major: false, valence: -0.4,  label: "semi-square",    plain: "rubbing against" },
  { type: "semisextile",    angle: 30,  orb: 2, major: false, valence: 0.25,  label: "semi-sextile",   plain: "brushing past" },
];

/** The Sun and Moon get wider orbs — standard practice, and defensible here: they are the brightest,
 *  fastest-acting factors and the ones every tradition weights most heavily. */
const LUMINARY_BONUS = 2;

/**
 * How positively or negatively a body colours a conjunction. Classical benefic/malefic, softened:
 * Venus and Jupiter are the benefics, Saturn and Mars the malefics, and the modern outer planets are
 * treated as disruptive rather than evil. A conjunction's valence is the mean of its two bodies', so
 * Venus–Jupiter reads as ease and Mars–Saturn as friction, which is what both traditions actually say.
 */
export const VALENCE: Record<Body, number> = {
  Sun: 0.35, Moon: 0.35, Mercury: 0.15, Venus: 1, Mars: -0.4,
  Jupiter: 0.9, Saturn: -0.8, Uranus: -0.35, Neptune: -0.2, Pluto: -0.5,
};

/** Relationship relevance of each body, before pairing. */
const BODY_RELEVANCE: Record<Body, number> = {
  Sun: 1, Moon: 1, Mercury: 0.55, Venus: 1, Mars: 0.8,
  Jupiter: 0.5, Saturn: 0.55, Uranus: 0.3, Neptune: 0.25, Pluto: 0.3,
};

const OUTER: Body[] = ["Uranus", "Neptune", "Pluto"];
const isOuter = (b: Body) => OUTER.includes(b);

/** Pairs the tradition treats as the load-bearing ones in a relationship reading. Symmetric by
 *  construction — looked up on the sorted pair. */
const SIGNATURE_PAIRS: Record<string, number> = {
  "Moon|Sun": 2.0,       // the classic marriage signature
  "Moon|Moon": 1.8,      // emotional rapport, how you rest around each other
  "Mars|Venus": 1.8,     // attraction and its wiring
  "Sun|Venus": 1.5,
  "Moon|Venus": 1.5,
  "Sun|Sun": 1.3,
  "Venus|Venus": 1.4,
  "Mars|Moon": 1.2,
  "Mars|Sun": 1.1,
  "Saturn|Venus": 1.2,   // commitment, or a cold ceiling — either way it is decisive
  "Moon|Saturn": 1.1,
  "Mercury|Mercury": 1.0, // whether talking is easy
  "Jupiter|Venus": 1.0,
  "Jupiter|Sun": 0.9,
  "Moon|Mercury": 0.9,
};

/** Importance of an aspect between two bodies. Defined on the UNORDERED pair, which is what makes
 *  the whole score symmetric. */
export function pairWeight(a: Body, b: Body): number {
  const key = [a, b].sort().join("|");
  const signature = SIGNATURE_PAIRS[key];
  if (signature !== undefined) return signature;
  // Two slow outer planets say nothing about a relationship — they say when you were both born.
  if (isOuter(a) && isOuter(b)) return 0.02;
  return BODY_RELEVANCE[a] * BODY_RELEVANCE[b];
}

export type SynAspect = {
  /** The body from the FIRST chart. */
  a: Placement;
  /** The body from the SECOND chart. */
  b: Placement;
  type: AspectType;
  def: AspectDef;
  /** Degrees away from exact. */
  orb: number;
  /** Widest orb allowed for this pairing, after the luminary bonus. */
  maxOrb: number;
  /** 1 = exact, 0 = at the very edge of orb. */
  exactness: number;
  /** −1 friction … +1 ease, after resolving a conjunction against body valence. */
  valence: number;
  /** How much this aspect counts: pair importance × exactness × major/minor. */
  weight: number;
  /** weight × valence — signed contribution to the ease score. */
  contribution: number;
};

function orbFor(def: AspectDef, a: Body, b: Body): number {
  const luminary = a === "Sun" || a === "Moon" || b === "Sun" || b === "Moon";
  return def.orb + (luminary && def.major ? LUMINARY_BONUS : 0);
}

/** Every aspect between chart A's bodies and chart B's bodies (the full cross product, so both
 *  A-Sun/B-Moon and A-Moon/B-Sun appear — they are genuinely different statements). */
export function synastryAspects(A: Chart, B: Chart, bodies: Body[] = BODIES): SynAspect[] {
  const out: SynAspect[] = [];
  for (const ba of bodies) {
    const pa = A.byBody[ba];
    if (!pa) continue;
    for (const bb of bodies) {
      const pb = B.byBody[bb];
      if (!pb) continue;
      const sep = separation(pa.lon, pb.lon);
      for (const def of ASPECTS) {
        const maxOrb = orbFor(def, ba, bb);
        const orb = Math.abs(sep - def.angle);
        if (orb > maxOrb) continue;
        const exactness = 1 - orb / maxOrb;
        const valence = def.type === "conjunction"
          ? (VALENCE[ba] + VALENCE[bb]) / 2
          : def.valence;
        const weight = pairWeight(ba, bb) * exactness * (def.major ? 1 : 0.25);
        out.push({
          a: pa, b: pb, type: def.type, def, orb, maxOrb, exactness, valence,
          weight, contribution: weight * valence,
        });
        break; // one aspect per body pair — the tightest match wins, and ASPECTS is ordered by size
      }
    }
  }
  return out.sort((x, y) => y.weight - x.weight);
}

export type SynastrySummary = {
  aspects: SynAspect[];
  /** Σ weight — how much the two charts engage each other at all. */
  totalWeight: number;
  /** Σ weight × valence — net ease. Positive is flowing, negative is friction. */
  netEase: number;
  /** netEase normalised into 0…100 against the engagement present. 50 = perfectly balanced. */
  easeScore: number;
  /** How charged the connection is, independent of whether it is easy: 0…100. */
  chargeScore: number;
  /** The aspects a report should lead with. */
  headline: SynAspect[];
  supportive: SynAspect[];
  challenging: SynAspect[];
};

/** Engagement at which chargeScore saturates. Calibrated so an ordinary pair lands near the middle
 *  of the range rather than everyone scoring 90+ — see tests/score.test.ts, which asserts the
 *  distribution over random pairs is actually spread out and not piled against a ceiling. */
const CHARGE_SATURATION = 9;

export function summariseSynastry(A: Chart, B: Chart): SynastrySummary {
  const aspects = synastryAspects(A, B);
  const totalWeight = aspects.reduce((s, x) => s + x.weight, 0);
  const netEase = aspects.reduce((s, x) => s + x.contribution, 0);

  // Ease is the weighted MEAN valence, rescaled to 0…100. Dividing by the weight actually present
  // (not by a fixed constant) means a pair with few but harmonious aspects is not punished for
  // being quiet — it reports ease, and chargeScore separately reports that there is little of it.
  const meanValence = totalWeight > 0 ? netEase / totalWeight : 0;
  const easeScore = Math.max(0, Math.min(100, 50 + 50 * meanValence));
  const chargeScore = Math.max(0, Math.min(100, 100 * (1 - Math.exp(-totalWeight / CHARGE_SATURATION))));

  const supportive = aspects.filter((x) => x.valence > 0.15 && x.def.major);
  const challenging = aspects.filter((x) => x.valence < -0.15 && x.def.major);

  return {
    aspects, totalWeight, netEase, easeScore, chargeScore,
    headline: aspects.slice(0, 8),
    supportive, challenging,
  };
}
