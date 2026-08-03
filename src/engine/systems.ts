/**
 * systems.ts — three more date-only traditions, and an ensemble with no invented weights.
 *
 * The Moon-based 36-point system (score.ts) is the deepest reading a birth date supports, but it is
 * not the only tradition that works from a date alone. This module adds the three big ones that do:
 *
 *   · THE NUMBERS  — numerology's date number: add up all the digits of a birth date and reduce to
 *     a single figure. An old grouping sorts the nine numbers into three families, and reads two
 *     people from the same family as naturally in step.
 *   · THE YEAR ANIMALS — the Chinese twelve-year cycle. Each year has an animal, the animals form
 *     well-known teams and well-known feuds, and the tables for both are centuries old.
 *   · THE SUN SIGNS — the familiar Western star signs, compared by their classical elements
 *     (fire, earth, air, water). The Sun's sign is computed from its actual position, not from
 *     newspaper date ranges, so boundary days come out right.
 *
 * ── The ensemble rule, and why it is the only honest one available ──────────────────────────────
 *
 * An earlier version of this project blended sub-scores with weights I chose, and measurement
 * killed it (see score.ts). The ensemble here avoids that mistake structurally:
 *
 *   1. Each tradition keeps its OWN score on its OWN scale, shown with its own working.
 *   2. Each raw score is converted to a PERCENTILE against 20,000 random pairs — the same
 *      calibration treatment the Moon score gets, same seed, same tool (tools/calibrate.mjs).
 *      A percentile is the one scale every system shares without anyone choosing a conversion.
 *   3. The ensemble is the PLAIN MEAN of the percentiles. Equal weight is not "no choice", but it
 *      is the only choice that doesn't smuggle in an opinion about which tradition is truest —
 *      a question this page has no standing to answer.
 *
 * Coarse systems (an animal pairing has only five possible outcomes) use the standard midpoint
 * percentile rank — the share scoring below, plus half the share scoring the same — so a common
 * middling outcome sits near 50 rather than at the bottom of its band.
 */

import { julianDay, parseDate, siderealLongitude, ayanamsaDeg, norm360, SIGNS, type SignName } from "./ephemeris";

// ════════════════════════════════════════════════════════════════════════════════════════════════
// The numbers
// ════════════════════════════════════════════════════════════════════════════════════════════════

/** The three classical families ("concords") of the nine numbers. An established numerological
 *  grouping, not something invented here: {1,5,7} the thinkers, {2,4,8} the builders, {3,6,9} the
 *  feelers. Two people in the same family are read as naturally in step. */
const FAMILY: Record<number, "thinkers" | "builders" | "feelers"> = {
  1: "thinkers", 5: "thinkers", 7: "thinkers",
  2: "builders", 4: "builders", 8: "builders",
  3: "feelers", 6: "feelers", 9: "feelers",
};
export const FAMILY_LABEL = {
  thinkers: "the thinkers", builders: "the builders", feelers: "the feelers",
} as const;

export type DateNumber = {
  /** The displayed number — 1–9, or one of the master numbers 11, 22, 33 kept unreduced. */
  value: number;
  /** The single digit used for family lookup (masters reduce: 11→2, 22→4, 33→6). */
  digit: number;
  family: keyof typeof FAMILY_LABEL;
  isMaster: boolean;
};

const digitSum = (n: number): number => String(n).split("").reduce((s, c) => s + +c, 0);

/** The date number: every digit of YYYYMMDD summed, then reduced — keeping 11, 22 and 33 as the
 *  tradition does ("master numbers"), but grouping them by their reduced digit. */
export function dateNumber(iso: string): DateNumber | null {
  const p = parseDate(iso);
  if (!p) return null;
  let n = digitSum(p.y) + digitSum(p.m) + digitSum(p.d);
  while (n > 9 && n !== 11 && n !== 22 && n !== 33) n = digitSum(n);
  const digit = n > 9 ? digitSum(n) : n;
  return { value: n, digit, family: FAMILY[digit], isMaster: n > 9 };
}

export type NumbersResult = {
  a: DateNumber; b: DateNumber;
  /** 0–3: same number 3, same family 2, different families 1. */
  score: number;
  verdict: string;
};

export function numbersMatch(isoA: string, isoB: string): NumbersResult | null {
  const a = dateNumber(isoA), b = dateNumber(isoB);
  if (!a || !b) return null;
  const score = a.digit === b.digit ? 3 : a.family === b.family ? 2 : 1;
  const verdict =
    a.digit === b.digit
      ? `Both dates reduce to ${a.digit} — the same number, which this tradition reads as instant mutual recognition.`
      : a.family === b.family
        ? `${a.value} and ${b.value} belong to the same family (${FAMILY_LABEL[a.family]}), read as naturally in step.`
        : `${a.value} sits with ${FAMILY_LABEL[a.family]} and ${b.value} with ${FAMILY_LABEL[b.family]} — different families, so the tradition expects more translating.`;
  return { a, b, score, verdict };
}

// ════════════════════════════════════════════════════════════════════════════════════════════════
// The year animals
// ════════════════════════════════════════════════════════════════════════════════════════════════

export const ANIMALS = [
  "Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
  "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig",
] as const;
export type Animal = (typeof ANIMALS)[number];

const ELEMENTS = ["Wood", "Fire", "Earth", "Metal", "Water"] as const;

/** The six "secret friend" pairs — the strongest bond in the system. */
const SECRET_FRIENDS: [number, number][] = [[0, 1], [2, 11], [3, 10], [4, 9], [5, 8], [6, 7]];
/** The six "harm" pairs — quiet, wearing friction. */
const HARMS: [number, number][] = [[0, 7], [1, 6], [2, 5], [3, 4], [9, 10], [8, 11]];

const inPairs = (pairs: [number, number][], a: number, b: number) =>
  pairs.some(([x, y]) => (x === a && y === b) || (x === b && y === a));

export type AnimalYear = {
  animal: Animal;
  element: (typeof ELEMENTS)[number];
  year: number;
  /** True when the birthday sits on the early-February year boundary, where the animal itself is
   *  uncertain by a day. */
  boundary: boolean;
};

/**
 * The animal of a birth date. The traditional solar calendar starts the year at the "start of
 * spring", around 4 February — NOT on 1 January — so January babies belong to the previous year's
 * animal. The exact boundary moment varies by a day either side, so 3–5 February is flagged.
 */
export function animalYear(iso: string): AnimalYear | null {
  const p = parseDate(iso);
  if (!p) return null;
  const beforeSpring = p.m < 2 || (p.m === 2 && p.d < 4);
  const year = beforeSpring ? p.y - 1 : p.y;
  return {
    animal: ANIMALS[((year - 4) % 12 + 12) % 12],
    element: ELEMENTS[Math.floor((((year - 4) % 10 + 10) % 10) / 2)],
    year,
    boundary: p.m === 2 && p.d >= 3 && p.d <= 5,
  };
}

export type AnimalsResult = {
  a: AnimalYear; b: AnimalYear;
  /** 0–4: secret friends 4, same team 3, ordinary 2, harm pair 1, direct clash 0. */
  score: number;
  relation: string;
  verdict: string;
};

export function animalsMatch(isoA: string, isoB: string): AnimalsResult | null {
  const a = animalYear(isoA), b = animalYear(isoB);
  if (!a || !b) return null;
  const ia = ANIMALS.indexOf(a.animal), ib = ANIMALS.indexOf(b.animal);
  let score: number, relation: string, verdict: string;
  if (inPairs(SECRET_FRIENDS, ia, ib)) {
    score = 4; relation = "secret friends";
    verdict = `${a.animal} and ${b.animal} are one of the six "secret friend" pairs — the strongest bond the animal cycle names.`;
  } else if (ia % 4 === ib % 4 && ia !== ib) {
    score = 3; relation = "same team";
    verdict = `${a.animal} and ${b.animal} belong to the same team of three — animals four years apart, read as sharing an outlook.`;
  } else if ((ia + 6) % 12 === ib) {
    score = 0; relation = "direct clash";
    verdict = `${a.animal} and ${b.animal} sit directly opposite in the cycle — the classic clash pairing, the one the tables warn about first.`;
  } else if (inPairs(HARMS, ia, ib)) {
    score = 1; relation = "harm pair";
    verdict = `${a.animal} and ${b.animal} are one of the six "harm" pairs — not open conflict, but a quiet, wearing friction.`;
  } else if (ia === ib) {
    score = 2.5; relation = "same animal";
    verdict = `Two ${a.animal}s — the same animal, read as easy familiarity with a risk of sameness.`;
  } else {
    score = 2; relation = "no special tie";
    verdict = `${a.animal} and ${b.animal} have no named relationship in the cycle — neither teamed nor opposed.`;
  }
  return { a, b, score, relation, verdict };
}

// ════════════════════════════════════════════════════════════════════════════════════════════════
// The Sun signs
// ════════════════════════════════════════════════════════════════════════════════════════════════

const SIGN_ELEMENT = ["fire", "earth", "air", "water"] as const;
export type Element = (typeof SIGN_ELEMENT)[number];
export const elementOf = (sign: number): Element => SIGN_ELEMENT[sign % 4];

export type SunSign = {
  sign: number;
  signName: SignName;
  element: Element;
  /** True when the Sun changed sign during the birth day, so the sign itself depends on the
   *  unknown birth time. Roughly twelve days a year. */
  boundary: boolean;
};

/** The Sun's WESTERN (tropical) longitude — its sidereal position with the two zodiacs' offset put
 *  back. This is what makes the familiar star-sign dates come out right. */
function tropicalSunLon(jd: number): number {
  return norm360(siderealLongitude("Sun", jd) + ayanamsaDeg((jd - 2451545.0) / 36525));
}

export function sunSign(iso: string): SunSign | null {
  const p = parseDate(iso);
  if (!p) return null;
  const signAt = (h: number) => Math.floor(tropicalSunLon(julianDay(p.y, p.m, p.d, h)) / 30) % 12;
  const noon = signAt(12);
  return {
    sign: noon, signName: SIGNS[noon], element: elementOf(noon),
    boundary: signAt(0) !== signAt(24),
  };
}

export type SunSignsResult = {
  a: SunSign; b: SunSign;
  /** 0–3: same element 3, friendly elements 2.5, opposite signs 2, uneasy elements 1. */
  score: number;
  verdict: string;
};

export function sunSignsMatch(isoA: string, isoB: string): SunSignsResult | null {
  const a = sunSign(isoA), b = sunSign(isoB);
  if (!a || !b) return null;
  const friendly =
    (a.element === "fire" && b.element === "air") || (a.element === "air" && b.element === "fire") ||
    (a.element === "earth" && b.element === "water") || (a.element === "water" && b.element === "earth");
  const opposite = (a.sign + 6) % 12 === b.sign;
  let score: number, verdict: string;
  if (a.element === b.element) {
    score = 3;
    verdict = a.sign === b.sign
      ? `Both are ${a.signName} — the same sign, same element (${a.element}): instant understanding, and a risk of amplifying each other's habits.`
      : `${a.signName} and ${b.signName} are both ${a.element} signs — the classic easy pairing, speaking the same language by default.`;
  } else if (opposite) {
    score = 2;
    verdict = `${a.signName} and ${b.signName} sit directly opposite each other — the traditional attraction-of-opposites pairing, magnetic and polarised at once.`;
  } else if (friendly) {
    score = 2.5;
    verdict = `${a.signName} (${a.element}) and ${b.signName} (${b.element}) are friendly elements — ${a.element} and ${b.element} feed each other rather than compete.`;
  } else {
    score = 1;
    verdict = `${a.signName} (${a.element}) and ${b.signName} (${b.element}) mix elements that traditionally take more work — neither wrong, just differently wired.`;
  }
  return { a, b, score, verdict };
}

// ════════════════════════════════════════════════════════════════════════════════════════════════
// Calibration + ensemble
// ════════════════════════════════════════════════════════════════════════════════════════════════

/**
 * Measured share of 20,000 random pairs at each possible score — tools/calibrate.mjs, same seed as
 * the Moon-score table. Midpoint percentile rank = (share below) + (share at) / 2.
 */
export const NUMBERS_DIST: Record<string, number> = { "1": 0.6678, "2": 0.2226, "3": 0.1096 };
export const ANIMALS_DIST: Record<string, number> = {
  "0": 0.0843, "1": 0.0854, "2": 0.5032, "2.5": 0.0796, "3": 0.1647, "4": 0.0828,
};
export const SUNSIGNS_DIST: Record<string, number> = {
  "1": 0.4979, "2": 0.0816, "2.5": 0.1678, "3": 0.2526,
};

export function midpointPercentile(score: number, dist: Record<string, number>): number {
  let below = 0, at = 0;
  for (const [k, share] of Object.entries(dist)) {
    const v = Number(k);
    if (v < score) below += share;
    else if (v === score) at += share;
  }
  return Math.round((below + at / 2) * 100);
}

export type SystemReading = {
  key: "moon" | "numbers" | "animals" | "sunsigns";
  name: string;
  /** The raw result in the tradition's own units, as a short string. */
  raw: string;
  percentile: number;
  verdict: string;
  /** A caveat when this system's answer is itself uncertain from a date. */
  caveat?: string;
};

export type Ensemble = {
  systems: SystemReading[];
  /** Plain mean of the systems' percentiles. */
  percentile: number;
  /** How many of the systems put this pair at or above their own median pair. */
  aboveAverage: number;
  agreement: "agree-high" | "agree-low" | "mixed";
  summary: string;
};

/** The three extra systems for one pair, plus the ensemble over all four. The Moon reading comes in
 *  from score.ts as a percentile so this module stays independent of it. */
export function ensembleFor(
  isoA: string, isoB: string,
  moon: { percentile: number; score: number; maxScore: number },
): Ensemble | null {
  const num = numbersMatch(isoA, isoB);
  const ani = animalsMatch(isoA, isoB);
  const sun = sunSignsMatch(isoA, isoB);
  if (!num || !ani || !sun) return null;

  const systems: SystemReading[] = [
    {
      key: "moon", name: "The Moon score",
      raw: `${moon.score} of ${moon.maxScore}`,
      percentile: moon.percentile,
      verdict: "The deepest of the four — the eight-test reading this whole page is built around, from where the two Moons sat.",
    },
    {
      key: "numbers", name: "The numbers",
      raw: `${num.a.value} & ${num.b.value}`,
      percentile: midpointPercentile(num.score, NUMBERS_DIST),
      verdict: num.verdict,
    },
    {
      key: "animals", name: "The year animals",
      raw: `${ani.a.element} ${ani.a.animal} & ${ani.b.element} ${ani.b.animal}`,
      percentile: midpointPercentile(ani.score, ANIMALS_DIST),
      verdict: ani.verdict,
      caveat: [
        ani.a.boundary && "the first birthday sits on the early-February year boundary, so the animal itself is uncertain by a day",
        ani.b.boundary && "the second birthday sits on the early-February year boundary, so the animal itself is uncertain by a day",
      ].filter(Boolean).join("; ") || undefined,
    },
    {
      key: "sunsigns", name: "The Sun signs",
      raw: `${sun.a.signName} & ${sun.b.signName}`,
      percentile: midpointPercentile(sun.score, SUNSIGNS_DIST),
      verdict: sun.verdict,
      caveat: [
        sun.a.boundary && "the Sun changed sign during the first birthday, so the sign depends on the unknown birth time",
        sun.b.boundary && "the Sun changed sign during the second birthday, so the sign depends on the unknown birth time",
      ].filter(Boolean).join("; ") || undefined,
    },
  ];

  const percentile = Math.round(systems.reduce((s, x) => s + x.percentile, 0) / systems.length);
  const aboveAverage = systems.filter((x) => x.percentile >= 50).length;
  const agreement: Ensemble["agreement"] =
    aboveAverage === systems.length ? "agree-high"
      : aboveAverage === 0 ? "agree-low"
        : "mixed";

  const summary =
    agreement === "agree-high"
      ? `All four traditions place this pair at or above their own average — rare agreement.`
      : agreement === "agree-low"
        ? `All four traditions place this pair below their own average.`
        : `${aboveAverage} of the four traditions place this pair at or above their own average; the others disagree. Disagreement between systems is the normal case, and worth seeing rather than averaging away.`;

  return { systems, percentile, aboveAverage, agreement, summary };
}
