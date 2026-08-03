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
export const VARNA_LABEL: Record<Varna, string> = {
  brahmin: "Brāhmaṇa", kshatriya: "Kṣatriya", vaishya: "Vaiśya", shudra: "Śūdra",
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
  chatushpada: "Chatuṣpada (four-footed)",
  manava: "Mānava (human)",
  jalachara: "Jalachara (water-dwelling)",
  vanachara: "Vanachara (wild)",
  keeta: "Keeṭa (insect)",
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
  /* vanachara */ [0, 0, 1, 2, 1],
  /* keeta     */ [1, 1, 1, 1, 2],
];

// ── Yoni ────────────────────────────────────────────────────────────────────────────────────────

/** The 14 yoni animals in a fixed order — exported so tests can walk the full matrix. */
export const YONI_ORDER: YoniAnimal[] = [
  "horse", "elephant", "sheep", "serpent", "dog", "cat", "rat",
  "cow", "buffalo", "tiger", "deer", "monkey", "mongoose", "lion",
];

/**
 * Yoni compatibility, 0–4. Same animal is 4; the classical MORTAL ENEMY pairs are 0 and everything
 * between is graded 3 (friendly), 2 (neutral) or 1 (unfriendly).
 *
 * The enemy pairs are the memorable part of the system and the part worth checking hardest:
 * horse/buffalo, elephant/sheep, serpent/mongoose, dog/deer, cat/rat, monkey/sheep, cow/tiger,
 * lion/elephant.
 */
const YONI_ENEMIES: [YoniAnimal, YoniAnimal][] = [
  ["horse", "buffalo"], ["elephant", "lion"], ["sheep", "monkey"], ["serpent", "mongoose"],
  ["dog", "deer"], ["cat", "rat"], ["cow", "tiger"], ["elephant", "sheep"],
];

const YONI_UNFRIENDLY: [YoniAnimal, YoniAnimal][] = [
  ["horse", "elephant"], ["serpent", "rat"], ["dog", "sheep"], ["cat", "dog"],
  ["monkey", "lion"], ["cow", "buffalo"], ["deer", "tiger"], ["lion", "deer"],
];

const YONI_FRIENDLY: [YoniAnimal, YoniAnimal][] = [
  ["horse", "sheep"], ["elephant", "cow"], ["cow", "buffalo"], ["deer", "monkey"],
  ["cat", "mongoose"], ["rat", "mongoose"], ["serpent", "cat"], ["tiger", "lion"],
];

function inPairs(pairs: [YoniAnimal, YoniAnimal][], a: YoniAnimal, b: YoniAnimal): boolean {
  return pairs.some(([x, y]) => (x === a && y === b) || (x === b && y === a));
}

export function yoniPoints(a: YoniAnimal, b: YoniAnimal): number {
  if (a === b) return 4;
  if (inPairs(YONI_ENEMIES, a, b)) return 0;
  if (inPairs(YONI_UNFRIENDLY, a, b)) return 1;
  if (inPairs(YONI_FRIENDLY, a, b)) return 3;
  return 2;
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
  name: string;
  sanskrit: string;
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
};

/** Inclusive count from sign a to sign b, 1…12 — the tradition always counts inclusively. */
const countSigns = (a: number, b: number) => ((b - a + 12) % 12) + 1;
/** Inclusive count from nakshatra a to nakshatra b, 1…27. */
const countNak = (a: number, b: number) => ((b - a + 27) % 27) + 1;

export function bandFor(total: number): { label: string; note: string } {
  if (total >= 32) return { label: "Exceptional", note: "Far above the conventional threshold — the eight tests agree almost completely." };
  if (total >= 26) return { label: "Very good", note: "Comfortably above the conventional threshold of 18." };
  if (total >= 21) return { label: "Good", note: "Above the conventional threshold of 18." };
  if (total >= 18) return { label: "Acceptable", note: "At or just above the threshold traditionally treated as the minimum." };
  if (total >= 14) return { label: "Below threshold", note: "Under the conventional minimum of 18, though several kutas still agree." };
  return { label: "Poor", note: "Well under the conventional minimum of 18." };
}

/** One ordering of Guna Milan. Call it twice, swapped, and average — see the file header. */
export function gunaMilanOrdered(a: KutaSide, b: KutaSide): GunaMilan {
  const kutas: KutaResult[] = [];

  // 1 · Varna — 1 point
  const varnaA = SIGN_VARNA[a.rasi], varnaB = SIGN_VARNA[b.rasi];
  kutas.push({
    key: "varna", name: "Varna", sanskrit: "वर्ण",
    measures: "Whether their working temperaments sit comfortably together.",
    points: VARNA_RANK[varnaA] >= VARNA_RANK[varnaB] ? 1 : 0,
    maxPoints: 1,
    rule: "1 point when the first person's varna is equal to or higher than the second's, else 0.",
    evidence: `${SIGNS[a.rasi]} → ${VARNA_LABEL[varnaA]} (rank ${VARNA_RANK[varnaA]}); ` +
      `${SIGNS[b.rasi]} → ${VARNA_LABEL[varnaB]} (rank ${VARNA_RANK[varnaB]}).`,
    orderSensitive: VARNA_RANK[varnaA] !== VARNA_RANK[varnaB],
  });

  // 2 · Vashya — 2 points
  const vashA = vashyaGroup(a.rasi, a.degInSign), vashB = vashyaGroup(b.rasi, b.degInSign);
  kutas.push({
    key: "vashya", name: "Vashya", sanskrit: "वश्य",
    measures: "Mutual influence — how naturally each yields to the other.",
    points: VASHYA_MATRIX[VASHYA_ORDER.indexOf(vashA)][VASHYA_ORDER.indexOf(vashB)],
    maxPoints: 2,
    rule: "The two Moon signs' vashya groups are looked up in the classical 5×5 table (same group = 2).",
    evidence: `${SIGNS[a.rasi]} ${a.degInSign.toFixed(1)}° → ${VASHYA_LABEL[vashA]}; ` +
      `${SIGNS[b.rasi]} ${b.degInSign.toFixed(1)}° → ${VASHYA_LABEL[vashB]}.`,
    orderSensitive: false,
  });

  // 3 · Tara — 3 points
  const taraAB = countNak(a.nakshatra.index, b.nakshatra.index) % 9;
  const taraBA = countNak(b.nakshatra.index, a.nakshatra.index) % 9;
  const badTara = (r: number) => r === 3 || r === 5 || r === 7;
  const goodCount = (badTara(taraAB) ? 0 : 1) + (badTara(taraBA) ? 0 : 1);
  kutas.push({
    key: "tara", name: "Tara", sanskrit: "तारा",
    measures: "Whether each is fortunate for the other's wellbeing.",
    points: goodCount === 2 ? 3 : goodCount === 1 ? 1.5 : 0,
    maxPoints: 3,
    rule: "Count inclusively between the two birth stars in each direction, take each count mod 9. " +
      "Remainders 3, 5 and 7 are inauspicious. Both auspicious = 3, one = 1.5, neither = 0.",
    evidence: `${a.nakshatra.name} → ${b.nakshatra.name} = ${countNak(a.nakshatra.index, b.nakshatra.index)}, ` +
      `mod 9 = ${taraAB} (${badTara(taraAB) ? "inauspicious" : "auspicious"}); reverse = ` +
      `${countNak(b.nakshatra.index, a.nakshatra.index)}, mod 9 = ${taraBA} ` +
      `(${badTara(taraBA) ? "inauspicious" : "auspicious"}).`,
    orderSensitive: false, // both directions are counted, so swapping changes nothing
  });

  // 4 · Yoni — 4 points
  kutas.push({
    key: "yoni", name: "Yoni", sanskrit: "योनि",
    measures: "Physical and instinctive compatibility.",
    points: yoniPoints(a.nakshatra.yoni, b.nakshatra.yoni),
    maxPoints: 4,
    rule: "Each birth star carries an animal. Same animal = 4, friendly = 3, neutral = 2, " +
      "unfriendly = 1, classical mortal enemies = 0.",
    evidence: `${a.nakshatra.name} → ${YONI_LABEL[a.nakshatra.yoni]} (${a.nakshatra.yoniGender}); ` +
      `${b.nakshatra.name} → ${YONI_LABEL[b.nakshatra.yoni]} (${b.nakshatra.yoniGender}).`,
    orderSensitive: false,
  });

  // 5 · Graha Maitri — 5 points
  const lordA = SIGN_LORD[a.rasi], lordB = SIGN_LORD[b.rasi];
  const gm = grahaMaitriPoints(lordA, lordB);
  kutas.push({
    key: "grahaMaitri", name: "Graha Maitri", sanskrit: "ग्रहमैत्री",
    measures: "Mental affinity — whether their minds are natural allies.",
    points: gm.points, maxPoints: 5,
    rule: "The two Moon signs' ruling grahas are compared in the natural friendship table: " +
      "mutual friends 5, friend+neutral 4, mutual neutral 3, friend+enemy 1, neutral+enemy 0.5, " +
      "mutual enemies 0.",
    evidence: `${SIGNS[a.rasi]} is ruled by ${lordA}, ${SIGNS[b.rasi]} by ${lordB} — ${gm.how}.`,
    orderSensitive: false,
  });

  // 6 · Gana — 6 points
  const ganaA = a.nakshatra.gana, ganaB = b.nakshatra.gana;
  kutas.push({
    key: "gana", name: "Gana", sanskrit: "गण",
    measures: "Temperament — the disposition each brings to the other.",
    points: GANA_MATRIX[GANA_ORDER.indexOf(ganaA)][GANA_ORDER.indexOf(ganaB)],
    maxPoints: 6,
    rule: "The two birth stars' ganas are looked up in the classical 3×3 table. Same gana always " +
      "scores 6; a Rakshasa paired with a Deva or Manushya scores at or near zero.",
    evidence: `${a.nakshatra.name} → ${GANA_LABEL[ganaA]}; ${b.nakshatra.name} → ${GANA_LABEL[ganaB]}.`,
    orderSensitive: ganaA !== ganaB,
  });

  // 7 · Bhakoot — 7 points
  const fwd = countSigns(a.rasi, b.rasi), rev = countSigns(b.rasi, a.rasi);
  const pair = [fwd, rev].sort((x, y) => x - y).join("/");
  const bhakootFails = pair === "2/12" || pair === "5/9" || pair === "6/8";
  kutas.push({
    key: "bhakoot", name: "Bhakoot", sanskrit: "भकूट",
    measures: "The shape of the shared life — prosperity, health, direction together.",
    points: bhakootFails ? 0 : 7,
    maxPoints: 7,
    rule: "Count inclusively between the two Moon signs both ways. The pairs 2/12, 5/9 and 6/8 " +
      "score zero (Bhakoot dosha); every other relationship scores the full 7.",
    evidence: `${SIGNS[a.rasi]} → ${SIGNS[b.rasi]} = ${fwd}, reverse = ${rev} → ${pair}` +
      `${bhakootFails ? " — a dosha pair" : " — not a dosha pair"}.`,
    orderSensitive: false,
  });

  // 8 · Nadi — 8 points, the single largest and the strictest
  const nadiA = a.nakshatra.nadi, nadiB = b.nakshatra.nadi;
  kutas.push({
    key: "nadi", name: "Nadi", sanskrit: "नाडी",
    measures: "Constitutional type — the deepest and most heavily weighted test.",
    points: nadiA === nadiB ? 0 : 8,
    maxPoints: 8,
    rule: "Different nadi scores the full 8. The SAME nadi scores zero — Nadi dosha, the most " +
      "serious single failure in the system.",
    evidence: `${a.nakshatra.name} → ${NADI_LABEL[nadiA]}; ${b.nakshatra.name} → ${NADI_LABEL[nadiB]}` +
      `${nadiA === nadiB ? " — the same nadi" : " — different nadis"}.`,
    orderSensitive: false,
  });

  const total = kutas.reduce((s, k) => s + k.points, 0);
  return { kutas, total, maxTotal: 36, band: bandFor(total), doshas: doshas(a, b, kutas) };
}

// ── doshas ──────────────────────────────────────────────────────────────────────────────────────

/** Mangal (Kuja) dosha counted from the MOON, because a birth date gives no Ascendant. */
function mangalFromMoon(side: KutaSide): boolean {
  const marsSign = Math.floor(side.marsLon / 30) % 12;
  const house = countSigns(side.rasi, marsSign); // 1…12, Moon sign as the first house
  return [1, 2, 4, 7, 8, 12].includes(house);
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
      key: "nadi", name: "Nadi dosha", present: true, mutual: true, cancelled,
      detail: `Both birth stars are ${NADI_LABEL[a.nakshatra.nadi]}, so Nadi scores 0 of 8 — the ` +
        `heaviest single deduction in the system.`,
      caveat: cancelled
        ? "Traditionally exempt here: the birth stars and rāśis do not both coincide, which the " +
          "classical texts treat as cancelling the dosha."
        : undefined,
    });
  }

  const bhakoot = kutas.find((k) => k.key === "bhakoot")!;
  if (bhakoot.points === 0) {
    // Bhakoot dosha is conventionally waived when Graha Maitri is strong.
    const gm = kutas.find((k) => k.key === "grahaMaitri")!;
    out.push({
      key: "bhakoot", name: "Bhakoot dosha", present: true, mutual: true,
      cancelled: gm.points >= 4,
      detail: "The two Moon signs stand in one of the three afflicted relationships, so Bhakoot " +
        "scores 0 of 7.",
      caveat: gm.points >= 4
        ? "Commonly waived here: Graha Maitri is strong, which most authorities treat as cancelling " +
          "Bhakoot dosha."
        : undefined,
    });
  }

  const mangalA = mangalFromMoon(a), mangalB = mangalFromMoon(b);
  if (mangalA || mangalB) {
    out.push({
      key: "mangal", name: "Mangal (Kuja) dosha", present: true, mutual: mangalA && mangalB,
      cancelled: mangalA && mangalB,
      detail: mangalA && mangalB
        ? "Both charts carry Mangal dosha counted from the Moon."
        : `Mars falls in an afflicted house from the Moon for ${mangalA ? "the first" : "the second"} person only.`,
      caveat: "Counted from the MOON, not the Ascendant — a birth date gives no Ascendant, so this " +
        "is the chandra-lagna variant. A birth time would be needed for the standard reading, and " +
        "the two can disagree." + (mangalA && mangalB
          ? " Both partners carrying it is traditionally treated as cancelling it." : ""),
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
