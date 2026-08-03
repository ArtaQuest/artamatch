/**
 * kuta.ts — Ashtakoota Guna Milan, the eight-fold Vedic compatibility system. 36 points.
 *
 * This is the sidereal heart of ArtaMatch. Six of the eight kutas are computed purely from the two
 * Moons' nakshatra and rāśi, which is the one thing a birth DATE very nearly determines — that is
 * why a sidereal matcher can say something meaningful from dates alone where a Western one, which
 * leans on the Ascendant and therefore on the birth minute, cannot.
 *
 * Every kuta returns the RULE it applied and the EVIDENCE it read, not just a number. A score with
 * no visible derivation is indistinguishable from a random number, and the entire point of this tool
 * is that a stranger can check it.
 *
 * ── On the groom/bride axis ─────────────────────────────────────────────────────────────────────
 * The classical rules are written for a groom and a bride, and three of the eight (Varna, Gana, and
 * the two halves of Tara) are genuinely ASYMMETRIC — swap the two people and the total changes.
 * ArtaMatch matches arbitrary people who have not told it any such thing, and a ranked list must be
 * symmetric or it is incoherent: A's list and B's list would disagree about the same pair.
 *
 * So both orderings are always computed. The headline and all ranking use the MEAN of the two, and
 * any kuta whose two orderings disagree is flagged `orderSensitive` and shows both values with the
 * traditional rule stated. Nothing is hidden and nothing is silently symmetrised.
 */

import { type NakshatraInfo, type Gana, type YoniAnimal, GANA_LABEL, NADI_LABEL, YONI_LABEL } from "./nakshatra";
import { SIGNS, SIGN_LORD, type Body } from "./ephemeris";

// ── Varna ───────────────────────────────────────────────────────────────────────────────────────

export type Varna = "brahmin" | "kshatriya" | "vaishya" | "shudra";
const VARNA_RANK: Record<Varna, number> = { brahmin: 4, kshatriya: 3, vaishya: 2, shudra: 1 };
/** Plain names for the four groups. The tradition's own names come from a caste ordering; the
 *  groups themselves track the four elements, so they are named for that instead. The hierarchy is
 *  not hidden — the scoring rule states it plainly and invites the reader to discount it. */
export const VARNA_LABEL: Record<Varna, string> = {
  brahmin: "reflective", kshatriya: "driving", vaishya: "practical", shudra: "adaptable",
};

/** Moon sign → varna. It follows the elements exactly: water is Brāhmaṇa, fire Kṣatriya, earth
 *  Vaiśya, air Śūdra. */
const SIGN_VARNA: Varna[] = [
  "kshatriya", "vaishya", "shudra", "brahmin", "kshatriya", "vaishya",
  "shudra", "brahmin", "kshatriya", "vaishya", "shudra", "brahmin",
];

// ── Vashya ──────────────────────────────────────────────────────────────────────────────────────

export type VashyaGroup = "chatushpada" | "manava" | "jalachara" | "vanachara" | "keeta";
export const VASHYA_LABEL: Record<VashyaGroup, string> = {
  chatushpada: "four-footed",
  manava: "human",
  jalachara: "water-dwelling",
  vanachara: "wild",
  keeta: "small-creature",
};

/** Moon sign → vashya group. Sagittarius and Capricorn SPLIT at 15°, which is why this takes a
 *  longitude and not just a sign index — a rule that silently ignored the half-sign split would be
 *  wrong for one twelfth of all charts. */
export function vashyaGroup(rasi: number, degInSign: number): VashyaGroup {
  switch (rasi) {
    case 0: case 1: return "chatushpada";                              // Aries, Taurus
    case 2: case 5: case 6: case 10: return "manava";                  // Gemini, Virgo, Libra, Aquarius
    case 3: case 11: return "jalachara";                               // Cancer, Pisces
    case 4: return "vanachara";                                        // Leo
    case 7: return "keeta";                                            // Scorpio
    case 8: return degInSign < 15 ? "manava" : "chatushpada";          // Sagittarius splits at 15°
    case 9: return degInSign < 15 ? "chatushpada" : "jalachara";       // Capricorn splits at 15°
    default: return "manava";
  }
}

const VASHYA_ORDER: VashyaGroup[] = ["chatushpada", "manava", "jalachara", "vanachara", "keeta"];

/** Vashya score matrix, rows and columns in VASHYA_ORDER. Symmetric. */
const VASHYA_MATRIX: number[][] = [
  //          chatush  manava  jalachara  vanachara  keeta
  /* chatush   */ [2, 1, 1, 0, 1],
  /* manava    */ [1, 2, 0.5, 0, 1],
  /* jalachara */ [1, 0.5, 2, 1, 1],
  /* vanachara */ [0, 0, 1, 2, 0],
  /* keeta     */ [1, 1, 1, 0, 2],
];

// ── Yoni ────────────────────────────────────────────────────────────────────────────────────────

/** The 14 yoni animals in a fixed order — exported so tests can walk the full matrix. */
export const YONI_ORDER: YoniAnimal[] = [
  "horse", "elephant", "sheep", "serpent", "dog", "cat", "rat",
  "cow", "buffalo", "tiger", "deer", "monkey", "mongoose", "lion",
];

/**
 * Yoni compatibility, 0–4 — the full classical 14×14 table.
 *
 * Same animal is 4; the seven canonical MORTAL ENEMY pairs are 0; between them the table grades
 * 3 (friendly), 2 (neutral) and 1 (unfriendly). The table is symmetric, and the diagonal is all 4s.
 *
 * This is a real transcribed table, not a rule of thumb. An earlier version of this file computed
 * the grades from a short list of "enemy / friendly / unfriendly" pairs and defaulted everything
 * else to neutral — that reproduced only 55% of the actual table, and wrongly made elephant/sheep
 * mortal enemies when the tradition rates them FRIENDLY (3). Yoni is worth 4 of the 36 points, so
 * the shortcut was materially wrong. Hence the full grid.
 *
 * The seven enemy pairs, which every source agrees on: horse/buffalo, elephant/lion, sheep/monkey,
 * serpent/mongoose, dog/deer, cat/rat, cow/tiger.
 */
const YONI_MATRIX: number[][] = [
  //          hor  ele  she  ser  dog  cat  rat  cow  buf  tig  dee  mon  mng  lio
  /* horse    */ [4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1],
  /* elephant */ [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0],
  /* sheep    */ [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],
  /* serpent  */ [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],
  /* dog      */ [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1],
  /* cat      */ [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],
  /* rat      */ [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2],
  /* cow      */ [1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],
  /* buffalo  */ [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],
  /* tiger    */ [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1],
  /* deer     */ [3, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1],
  /* monkey   */ [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2],
  /* mongoose */ [2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2],
  /* lion     */ [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 2, 4],
];

export function yoniPoints(a: YoniAnimal, b: YoniAnimal): number {
  return YONI_MATRIX[YONI_ORDER.indexOf(a)][YONI_ORDER.indexOf(b)];
}

// ── Graha Maitri ────────────────────────────────────────────────────────────────────────────────

type Relation = "friend" | "neutral" | "enemy";

/**
 * Naisargika (natural) planetary friendship among the seven sign-lords. NOT symmetric — Mercury
 * counts the Moon an enemy while the Moon counts Mercury a friend, which is a real feature of the
 * system and not a transcription slip.
 */
const FRIENDSHIP: Record<string, { friends: Body[]; enemies: Body[] }> = {
  Sun:     { friends: ["Moon", "Mars", "Jupiter"], enemies: ["Venus", "Saturn"] },
  Moon:    { friends: ["Sun", "Mercury"], enemies: [] },
  Mars:    { friends: ["Sun", "Moon", "Jupiter"], enemies: ["Mercury"] },
  Mercury: { friends: ["Sun", "Venus"], enemies: ["Moon"] },
  Jupiter: { friends: ["Sun", "Moon", "Mars"], enemies: ["Mercury", "Venus"] },
  Venus:   { friends: ["Mercury", "Saturn"], enemies: ["Sun", "Moon"] },
  Saturn:  { friends: ["Mercury", "Venus"], enemies: ["Sun", "Moon", "Mars"] },
};

export function relationOf(from: Body, to: Body): Relation {
  const row = FRIENDSHIP[from];
  if (!row) return "neutral";
  if (row.friends.includes(to)) return "friend";
  if (row.enemies.includes(to)) return "enemy";
  return "neutral";
}

/** The 5-point ladder from the two lords' mutual view of each other. */
export function grahaMaitriPoints(lordA: Body, lordB: Body): { points: number; how: string } {
  if (lordA === lordB) return { points: 5, how: "both Moons are ruled by the same graha" };
  const ab = relationOf(lordA, lordB);
  const ba = relationOf(lordB, lordA);
  const pair = [ab, ba].sort().join("+");
  switch (pair) {
    case "friend+friend": return { points: 5, how: "mutual friends" };
    case "friend+neutral": return { points: 4, how: "one counts the other a friend, the other is neutral" };
    case "neutral+neutral": return { points: 3, how: "mutually neutral" };
    case "enemy+friend": return { points: 1, how: "one counts the other a friend, the other an enemy" };
    case "enemy+neutral": return { points: 0.5, how: "one is neutral, the other counts them an enemy" };
    case "enemy+enemy": return { points: 0, how: "mutual enemies" };
    default: return { points: 3, how: "mutually neutral" };
  }
}

// ── Gana ────────────────────────────────────────────────────────────────────────────────────────

const GANA_ORDER: Gana[] = ["deva", "manushya", "rakshasa"];

/** Gana matrix. Rows = the FIRST person's gana, columns = the SECOND person's. Asymmetric: the
 *  tradition is harder on a Rakshasa first-party than on a Rakshasa second-party. */
const GANA_MATRIX: number[][] = [
  //           deva  manushya  rakshasa
  /* deva     */ [6, 6, 0],
  /* manushya */ [5, 6, 0],
  /* rakshasa */ [1, 0, 6],
];

// ── the kuta result shape ───────────────────────────────────────────────────────────────────────

export type KutaKey = "varna" | "vashya" | "tara" | "yoni" | "grahaMaitri" | "gana" | "bhakoot" | "nadi";

export type KutaResult = {
  key: KutaKey;
  /** The name shown to a reader. Plain English — the traditional name is a footnote, not a label.
   *  Nobody should have to learn a vocabulary to read their own result. */
  name: string;
  /** The traditional name, kept for people who know it and for checking the working. */
  traditional: string;
  /** What this kuta claims to measure, in plain English. */
  measures: string;
  points: number;
  maxPoints: number;
  /** The exact rule that produced the number. */
  rule: string;
  /** The exact values read out of the two charts. */
  evidence: string;
  /** True when swapping the two people would change this kuta's score. */
  orderSensitive: boolean;
};

export type Dosha = {
  key: string;
  name: string;
  present: boolean;
  /** Present for both partners — which the tradition treats as cancelling. */
  mutual: boolean;
  cancelled: boolean;
  detail: string;
  caveat?: string;
};

export type GunaMilan = {
  kutas: KutaResult[];
  total: number;
  maxTotal: number;
  /** The conventional reading band for the total. */
  band: { label: string; note: string };
  doshas: Dosha[];
};

/** The one input each side of Guna Milan needs: where the Moon is, and Mars for the dosha check. */
export type KutaSide = {
  /** Sidereal longitude of the Moon. */
  moonLon: number;
  nakshatra: NakshatraInfo;
  rasi: number;
  degInSign: number;
  /** Sidereal longitude of Mars — used only by the Mangal dosha check. */
  marsLon: number;
  /** Sidereal longitude of Venus — the third Mangal reference point (see mangalFor). */
  venusLon: number;
};

/** Inclusive count from sign a to sign b, 1…12 — the tradition always counts inclusively. */
const countSigns = (a: number, b: number) => ((b - a + 12) % 12) + 1;
/** Inclusive count from nakshatra a to nakshatra b, 1…27. */
const countNak = (a: number, b: number) => ((b - a + 27) % 27) + 1;

export function bandFor(total: number): { label: string; note: string } {
  if (total >= 32) return { label: "Exceptional", note: "Far above the usual pass mark. The eight tests agree almost completely." };
  if (total >= 26) return { label: "Very good", note: "Comfortably above the usual pass mark of 18." };
  if (total >= 21) return { label: "Good", note: "Above the usual pass mark of 18." };
  if (total >= 18) return { label: "Acceptable", note: "Right around the mark traditionally treated as the minimum." };
  if (total >= 14) return { label: "Below threshold", note: "Under the usual minimum of 18, though several of the eight still agree." };
  return { label: "Poor", note: "Well under the usual minimum of 18." };
}

/** One ordering of Guna Milan. Call it twice, swapped, and average — see the file header. */
export function gunaMilanOrdered(a: KutaSide, b: KutaSide): GunaMilan {
  const kutas: KutaResult[] = [];

  // 1 · Varna — 1 point
  const varnaA = SIGN_VARNA[a.rasi], varnaB = SIGN_VARNA[b.rasi];
  kutas.push({
    key: "varna", name: "Ways of working", traditional: "Varna",
    measures: "Whether the way they each go about things sits comfortably together.",
    points: VARNA_RANK[varnaA] >= VARNA_RANK[varnaB] ? 1 : 0,
    maxPoints: 1,
    rule: "An old ranking of four temperaments, running reflective, driving, practical, adaptable. " +
      "It scores when the first person's sits at or above the second's. This is the one point in " +
      "thirty-six that carries an inherited hierarchy, and it is worth discounting if that sits " +
      "badly with you.",
    evidence: `${SIGNS[a.rasi]} is ${VARNA_LABEL[varnaA]}; ${SIGNS[b.rasi]} is ${VARNA_LABEL[varnaB]}.`,
    orderSensitive: VARNA_RANK[varnaA] !== VARNA_RANK[varnaB],
  });

  // 2 · Vashya — 2 points
  const vashA = vashyaGroup(a.rasi, a.degInSign), vashB = vashyaGroup(b.rasi, b.degInSign);
  kutas.push({
    key: "vashya", name: "Give and take", traditional: "Vashya",
    measures: "How much sway each naturally has over the other.",
    points: VASHYA_MATRIX[VASHYA_ORDER.indexOf(vashA)][VASHYA_ORDER.indexOf(vashB)],
    maxPoints: 2,
    rule: "Each Moon sign belongs to one of five old groupings. The same grouping scores the full " +
      "2; every other combination comes from a fixed table.",
    evidence: `${SIGNS[a.rasi]} is in the ${VASHYA_LABEL[vashA]} group; ` +
      `${SIGNS[b.rasi]} is in the ${VASHYA_LABEL[vashB]} group.`,
    orderSensitive: false,
  });

  // 3 · Tara — 3 points
  const taraAB = countNak(a.nakshatra.index, b.nakshatra.index) % 9;
  const taraBA = countNak(b.nakshatra.index, a.nakshatra.index) % 9;
  const badTara = (r: number) => r === 3 || r === 5 || r === 7;
  const goodCount = (badTara(taraAB) ? 0 : 1) + (badTara(taraBA) ? 0 : 1);
  kutas.push({
    key: "tara", name: "Good for each other", traditional: "Tara",
    measures: "Whether each tends to be lucky for the other's wellbeing.",
    points: goodCount === 2 ? 3 : goodCount === 1 ? 1.5 : 0,
    maxPoints: 3,
    rule: "Count the steps from one birth star to the other, both ways round the twenty-seven. " +
      "Positions 3, 5 and 7 out of every nine are the unlucky ones. Both directions clear scores " +
      "3, one clears 1.5, neither scores 0.",
    evidence: `${a.nakshatra.name} to ${b.nakshatra.name} is ` +
      `${countNak(a.nakshatra.index, b.nakshatra.index)} steps, landing on position ${taraAB || 9} ` +
      `of nine (${badTara(taraAB) ? "unlucky" : "clear"}). The other way is ` +
      `${countNak(b.nakshatra.index, a.nakshatra.index)} steps, position ${taraBA || 9} ` +
      `(${badTara(taraBA) ? "unlucky" : "clear"}).`,
    orderSensitive: false, // both directions are counted, so swapping changes nothing
  });

  // 4 · Yoni — 4 points
  kutas.push({
    key: "yoni", name: "Physical instinct", traditional: "Yoni",
    measures: "Physical and instinctive fit.",
    points: yoniPoints(a.nakshatra.yoni, b.nakshatra.yoni),
    maxPoints: 4,
    rule: "Each birth star carries an animal. The same animal scores the full 4, a friendly pair " +
      "3, an indifferent pair 2, an uneasy pair 1, and the seven traditional enemy pairs score 0.",
    evidence: `${a.nakshatra.name}'s animal is the ${YONI_LABEL[a.nakshatra.yoni].toLowerCase()}; ` +
      `${b.nakshatra.name}'s is the ${YONI_LABEL[b.nakshatra.yoni].toLowerCase()}.`,
    orderSensitive: false,
  });

  // 5 · Graha Maitri — 5 points
  const lordA = SIGN_LORD[a.rasi], lordB = SIGN_LORD[b.rasi];
  const gm = grahaMaitriPoints(lordA, lordB);
  kutas.push({
    key: "grahaMaitri", name: "Meeting of minds", traditional: "Graha Maitri",
    measures: "Whether their minds work in a similar way.",
    points: gm.points, maxPoints: 5,
    rule: "Each Moon sign has a planet that goes with it, and those planets are ranked friend, " +
      "neutral or enemy of one another. Both friends scores 5, friend and neutral 4, both neutral " +
      "3, friend and enemy 1, neutral and enemy 0.5, both enemies 0.",
    evidence: `${SIGNS[a.rasi]} goes with ${lordA}, ${SIGNS[b.rasi]} with ${lordB} — ${gm.how}.`,
    orderSensitive: false,
  });

  // 6 · Gana — 6 points
  const ganaA = a.nakshatra.gana, ganaB = b.nakshatra.gana;
  kutas.push({
    key: "gana", name: "Temperament", traditional: "Gana",
    measures: "The basic temperament each one brings.",
    points: GANA_MATRIX[GANA_ORDER.indexOf(ganaA)][GANA_ORDER.indexOf(ganaB)],
    maxPoints: 6,
    rule: "Every birth star is gentle, even-handed or forceful. The same temperament always scores " +
      "the full 6; a forceful one paired with a gentle one scores at or near zero.",
    evidence: `${a.nakshatra.name} is ${GANA_LABEL[ganaA]}; ${b.nakshatra.name} is ${GANA_LABEL[ganaB]}.`,
    orderSensitive: ganaA !== ganaB,
  });

  // 7 · Bhakoot — 7 points
  const fwd = countSigns(a.rasi, b.rasi), rev = countSigns(b.rasi, a.rasi);
  const pair = [fwd, rev].sort((x, y) => x - y).join("/");
  const bhakootFails = pair === "2/12" || pair === "5/9" || pair === "6/8";
  kutas.push({
    key: "bhakoot", name: "Life together", traditional: "Bhakoot",
    measures: "How a shared life would tend to go — money, health, pulling in one direction.",
    points: bhakootFails ? 0 : 7,
    maxPoints: 7,
    rule: "Count the signs from one Moon sign to the other, both ways round. Three particular " +
      "distances — 2 and 12, 5 and 9, 6 and 8 — score nothing at all. Every other distance scores " +
      "the full 7. There is no middle ground in this one.",
    evidence: `${SIGNS[a.rasi]} to ${SIGNS[b.rasi]} is ${fwd} signs, and ${rev} coming back` +
      `${bhakootFails ? " — one of the three difficult distances" : " — not one of the three difficult distances"}.`,
    orderSensitive: false,
  });

  // 8 · Nadi — 8 points, the single largest and the strictest
  const nadiA = a.nakshatra.nadi, nadiB = b.nakshatra.nadi;
  kutas.push({
    key: "nadi", name: "Underlying makeup", traditional: "Nadi",
    measures: "The deepest layer — how each one is built underneath everything else.",
    points: nadiA === nadiB ? 0 : 8,
    maxPoints: 8,
    rule: "Every birth star is airy and restless, hot and driven, or steady and settled. Different " +
      "types score the full 8. The same type scores nothing — the largest single deduction " +
      "anywhere in the thirty-six, on the reasoning that two people built the same way have no " +
      "spare capacity for each other.",
    evidence: `${a.nakshatra.name} is ${NADI_LABEL[nadiA]}; ${b.nakshatra.name} is ${NADI_LABEL[nadiB]}` +
      `${nadiA === nadiB ? " — the same" : " — different"}.`,
    orderSensitive: false,
  });

  const total = kutas.reduce((s, k) => s + k.points, 0);
  return { kutas, total, maxTotal: 36, band: bandFor(total), doshas: doshas(a, b, kutas) };
}

// ── doshas ──────────────────────────────────────────────────────────────────────────────────────

/**
 * Mangal (Kuja) dosha. Mars falling in house 1, 2, 4, 7, 8 or 12 counted whole-sign from a
 * reference point.
 *
 * There are THREE traditional reference points and the standard rule (Drik Panchang) is that a
 * person is non-Manglik only if none of the three is afflicted:
 *
 *   · the ASCENDANT — the primary one, and flatly impossible here. The Lagna advances ~15° an hour,
 *     a whole sign every two hours, all twelve in a day. Without a birth time it is not even
 *     probabilistically biased, so it is REFUSED rather than defaulted to noon and presented as
 *     fact. Defaulting would be inventing the answer.
 *   · the MOON (chandra-lagna) — degraded but usable: the Moon's ±6.6° date-only uncertainty gives
 *     roughly an 11% chance of the wrong rāśi.
 *   · VENUS (shukra) — safe without a time: Venus holds a sign for three to eight weeks, so only a
 *     birth on an ingress day is ambiguous at all.
 *
 * So ArtaMatch computes two of the three and says plainly that the third is unavailable.
 */
const MANGAL_HOUSES = [1, 2, 4, 7, 8, 12];

function afflicted(refLon: number, marsLon: number): boolean {
  const refSign = Math.floor(refLon / 30) % 12;
  const marsSign = Math.floor(marsLon / 30) % 12;
  return MANGAL_HOUSES.includes(countSigns(refSign, marsSign));
}

function mangalFor(side: KutaSide): { moon: boolean; venus: boolean; any: boolean } {
  const moon = afflicted(side.moonLon, side.marsLon);
  const venus = afflicted(side.venusLon, side.marsLon);
  return { moon, venus, any: moon || venus };
}

function doshas(a: KutaSide, b: KutaSide, kutas: KutaResult[]): Dosha[] {
  const out: Dosha[] = [];

  const nadi = kutas.find((k) => k.key === "nadi")!;
  if (nadi.points === 0) {
    // The classical exemptions: same nadi is not a dosha when the birth stars are the SAME but the
    // rāśi differs, or the rāśi is the same but the birth star differs.
    const sameNak = a.nakshatra.index === b.nakshatra.index;
    const sameRasi = a.rasi === b.rasi;
    const cancelled = (sameNak && !sameRasi) || (!sameNak && sameRasi);
    out.push({
      key: "nadi", name: "Built the same way underneath", present: true, mutual: true, cancelled,
      detail: `Both are ${NADI_LABEL[a.nakshatra.nadi]}, which costs the whole 8 points — the heaviest ` +
        `single deduction in the system.`,
      caveat: cancelled
        ? "The old texts let this one off when the birth stars and the Moon signs do not both coincide, " +
          "which is the case here."
        : undefined,
    });
  }

  const bhakoot = kutas.find((k) => k.key === "bhakoot")!;
  if (bhakoot.points === 0) {
    // Bhakoot dosha is conventionally waived when Graha Maitri is strong.
    const gm = kutas.find((k) => k.key === "grahaMaitri")!;
    out.push({
      key: "bhakoot", name: "An awkward distance between their Moon signs", present: true, mutual: true,
      cancelled: gm.points >= 4,
      detail: "Their two Moon signs sit at one of the three distances the tradition treats as hard " +
        "going, which costs the whole 7 points.",
      caveat: gm.points >= 4
        ? "Most readers set this one aside when the two minds get on well, as they do here."
        : undefined,
    });
  }

  const ma = mangalFor(a), mb = mangalFor(b);
  if (ma.any || mb.any) {
    // Dosha Samya, kept as an explicit three-way state rather than a silently-cancelled boolean:
    // "both" is the traditional mitigation, "one only" is the case that actually matters, and
    // neither would not be reported at all.
    const state: "both" | "one_only" = ma.any && mb.any ? "both" : "one_only";
    const refs = (m: typeof ma) =>
      [m.moon && "from the Moon", m.venus && "from Venus"].filter(Boolean).join(" and ");
    out.push({
      key: "mangal", name: "A harder placing for Mars", present: true,
      mutual: state === "both",
      cancelled: state === "both",
      detail: state === "both"
        ? `Both charts carry it — the first ${refs(ma)}, the second ${refs(mb)}.`
        : `Only ${ma.any ? "the first" : "the second"} chart carries it, ` +
          `${refs(ma.any ? ma : mb)}.`,
      caveat:
        "Checked two of the three ways the tradition asks for. The third needs to know which sign was " +
        "rising at the moment of birth, and that changes every two hours — a date alone cannot even " +
        "make a sensible guess at it, so it is left out rather than invented." +
        (state === "both"
          ? " Both of them having it is the let-off the tradition weights most heavily" +
            " — it is treated as balancing out."
          : ""),
    });
  }

  return out;
}

/**
 * Guna Milan without a groom/bride assignment: both orderings, and their mean.
 *
 * `total` is the mean and is what ranking uses, because ranking must be symmetric. `forward` and
 * `reverse` are both kept so the report can show the traditional single-ordering numbers whenever
 * the two disagree.
 */
export type SymmetricGunaMilan = {
  forward: GunaMilan;
  reverse: GunaMilan;
  /** Mean of the two orderings — symmetric, so safe to rank on. */
  total: number;
  maxTotal: number;
  band: { label: string; note: string };
  /** True when the two orderings disagree at all. */
  orderMatters: boolean;
  /** Per-kuta mean, with both orderings kept. */
  kutas: (KutaResult & { forwardPoints: number; reversePoints: number })[];
  doshas: Dosha[];
};

export function gunaMilan(a: KutaSide, b: KutaSide): SymmetricGunaMilan {
  const forward = gunaMilanOrdered(a, b);
  const reverse = gunaMilanOrdered(b, a);
  const total = (forward.total + reverse.total) / 2;
  const kutas = forward.kutas.map((k, i) => {
    const r = reverse.kutas[i];
    return { ...k, points: (k.points + r.points) / 2, forwardPoints: k.points, reversePoints: r.points };
  });
  return {
    forward, reverse, total, maxTotal: 36, band: bandFor(total),
    orderMatters: Math.abs(forward.total - reverse.total) > 1e-9,
    kutas,
    doshas: forward.doshas,
  };
}
