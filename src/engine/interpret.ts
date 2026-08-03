/**
 * interpret.ts — the words.
 *
 * A compatibility report that prints "Venus square Mars, orb 2°14′" and stops has told the reader
 * nothing they can use. This module turns each measured fact into a sentence, the way AstroSeek's
 * partner report does.
 *
 * It is COMPOSITIONAL rather than a table of several hundred hand-written paragraphs: each body has
 * a relational role, each aspect has a mode, and the two combine. Then the pairs the tradition
 * actually leads with — Sun–Moon, Venus–Mars, Moon–Moon and their kin — carry bespoke text that
 * overrides the composition, because those are the ones a reader came for and generic phrasing
 * shows most there.
 *
 * The voice is plain and non-fatalistic on purpose. These are described as tendencies and shapes,
 * never as predictions or verdicts about people who did not ask to be assessed.
 */

import { type Body } from "./ephemeris";
import { type AspectType, type SynAspect } from "./synastry";
import { type KutaResult, type Dosha } from "./kuta";

// ── bodies ──────────────────────────────────────────────────────────────────────────────────────

type Role = {
  /** What this body stands for in a relationship reading. */
  noun: string;
  /** A short phrase naming what the person brings through it. */
  brings: string;
};

const ROLE: Record<Body, Role> = {
  Sun: { noun: "sense of self", brings: "who they take themselves to be" },
  Moon: { noun: "emotional weather", brings: "what they need in order to feel safe" },
  Mercury: { noun: "way of thinking and talking", brings: "how they explain themselves" },
  Venus: { noun: "way of loving", brings: "what they find beautiful and how they show affection" },
  Mars: { noun: "drive and temper", brings: "how they pursue things, and how they argue" },
  Jupiter: { noun: "sense of possibility", brings: "where they are generous and where they overreach" },
  Saturn: { noun: "sense of duty and limit", brings: "what they take seriously and where they go cold" },
  Uranus: { noun: "need for freedom", brings: "what they refuse to have decided for them" },
  Neptune: { noun: "imagination and blind spots", brings: "what they idealise" },
  Pluto: { noun: "capacity for intensity", brings: "what they will not let go of" },
};

// ── aspects ─────────────────────────────────────────────────────────────────────────────────────

type Mode = { verb: string; quality: string; tone: "ease" | "friction" | "fusion" | "polarity" };

const MODE: Record<AspectType, Mode> = {
  conjunction: { verb: "sits directly on", quality: "fused — they amplify each other, for better and worse", tone: "fusion" },
  opposition: { verb: "faces", quality: "a see-saw: real attraction across a real gap", tone: "polarity" },
  trine: { verb: "flows with", quality: "easy, and easy enough to be taken for granted", tone: "ease" },
  square: { verb: "grinds against", quality: "friction that keeps returning until it is worked out", tone: "friction" },
  sextile: { verb: "opens toward", quality: "an opportunity that has to be taken deliberately", tone: "ease" },
  quincunx: { verb: "sits awkwardly beside", quality: "a persistent mismatch neither can quite name", tone: "friction" },
  sesquiquadrate: { verb: "chafes at", quality: "low-level irritation rather than open conflict", tone: "friction" },
  quintile: { verb: "plays with", quality: "a creative, slightly unusual spark", tone: "ease" },
  semisquare: { verb: "rubs against", quality: "a small recurring snag", tone: "friction" },
  semisextile: { verb: "brushes", quality: "a mild, mostly helpful contact", tone: "ease" },
};

// ── bespoke text for the pairs a report leads with ──────────────────────────────────────────────

type Bespoke = Partial<Record<"fusion" | "ease" | "friction" | "polarity", string>>;

/** Keyed on the SORTED body pair, so it is symmetric like everything else here. */
const SIGNATURE: Record<string, Bespoke> = {
  "Moon|Sun": {
    fusion: "The classical marriage signature. One person's identity sits exactly where the other's " +
      "emotional needs are — a strong instinctive recognition, often mistaken for having known each " +
      "other before. It is the single most quoted contact in the tradition.",
    ease: "The classical marriage signature in its easiest form: what one is naturally reassures the " +
      "other without either having to work at it. Steadying rather than exciting.",
    friction: "Identity and emotional need pull against each other. Neither is wrong; they simply " +
      "want the day arranged differently, and that tends to surface in small domestic decisions " +
      "rather than big arguments.",
    polarity: "A genuine pull across a genuine difference: each is drawn to something in the other " +
      "they do not have themselves. It sustains interest and it does not resolve.",
  },
  "Moon|Moon": {
    fusion: "The same emotional weather. Comfort is instant and needs little explaining — the risk " +
      "is that shared blind spots go unchallenged, because nobody in the room finds them strange.",
    ease: "Their emotional rhythms agree. Rest is easy in each other's company and neither has to " +
      "translate what they are feeling.",
    friction: "Their emotional rhythms are genuinely out of step — one settles where the other " +
      "unsettles. Workable, but it needs saying out loud rather than assumed.",
    polarity: "Opposite emotional needs that answer each other: what one lacks, the other has too " +
      "much of. Complementary and tiring in roughly equal measure.",
  },
  "Mars|Venus": {
    fusion: "The attraction contact. Desire and affection land on the same point — this is the one " +
      "the tradition associates with physical chemistry, and it is usually obvious to both.",
    ease: "Wanting and being wanted line up comfortably. Attraction here is warm rather than " +
      "urgent, and it lasts.",
    friction: "Strong attraction that keeps catching on the details — pace, timing, who moves " +
      "first. Charged rather than comfortable.",
    polarity: "Classic magnetism across a gap. Pursuit and receptivity sit at opposite ends and " +
      "keep reaching for each other.",
  },
  "Sun|Venus": {
    fusion: "Being liked and being oneself are the same act here. Easy warmth, and easy flattery.",
    ease: "One simply finds the other pleasant to be around — an underrated thing to have.",
    friction: "Affection and self-regard get tangled: what one offers as love, the other can hear " +
      "as a correction.",
    polarity: "Attraction that runs through difference in taste rather than agreement.",
  },
  "Moon|Venus": {
    fusion: "Affection and emotional need coincide — a gentle, domestic sort of closeness.",
    ease: "Kindness comes naturally in both directions. Quietly one of the best contacts to have.",
    friction: "What one finds affectionate, the other can find insufficient — a mismatch in how " +
      "care is expressed rather than whether it exists.",
    polarity: "Each wants to be loved in the way the other does not naturally give.",
  },
  "Saturn|Venus": {
    fusion: "Love meets duty. This is the commitment contact — it makes things last, and it can " +
      "make them cold. Which of the two depends almost entirely on what else is present.",
    ease: "Affection with structure under it: unhurried, reliable, and inclined to stay.",
    friction: "One reaches for warmth and meets a rule. The most common single source of a slow " +
      "chill in an otherwise good match.",
    polarity: "Commitment and freedom of affection pull against each other, and keep negotiating.",
  },
  "Moon|Saturn": {
    fusion: "Emotional need meets restraint. Steadying if both want steadying; heavy if one does not.",
    ease: "One provides the ground the other's feelings can stand on. Undramatic and durable.",
    friction: "One needs reassurance at exactly the moment the other withdraws into duty.",
    polarity: "Care and self-sufficiency face each other across the table.",
  },
  "Mercury|Mercury": {
    fusion: "They think in the same idiom — conversation needs no translation.",
    ease: "Talking is easy. Explanations land the first time, which quietly prevents a great many " +
      "arguments.",
    friction: "They reason differently enough that plain statements get misheard. Nothing " +
      "insurmountable, but it does require repeating things.",
    polarity: "Opposite ways of thinking that sharpen each other — good argument, tiring small talk.",
  },
};

const bespokeFor = (a: Body, b: Body): Bespoke | undefined => SIGNATURE[[a, b].sort().join("|")];

/** One paragraph explaining one inter-chart aspect. */
export function explainAspect(asp: SynAspect, nameA: string, nameB: string): string {
  const bodyA = asp.a.body, bodyB = asp.b.body;
  const mode = MODE[asp.type];

  const custom = bespokeFor(bodyA, bodyB)?.[mode.tone];
  if (custom) return custom;

  const roleA = ROLE[bodyA], roleB = ROLE[bodyB];
  const generational = isOuter(bodyA) && isOuter(bodyB);
  if (generational) {
    return `A slow, generational contact — everyone born within a few years of ${nameA} and ` +
      `${nameB} shares it. Listed for completeness; it says almost nothing about these two ` +
      `specifically, and it is weighted accordingly.`;
  }

  return `${nameA}'s ${roleA.noun} ${mode.verb} ${nameB}'s ${roleB.noun}: ${mode.quality}. ` +
    `In practice this is about ${roleA.brings} meeting ${roleB.brings}.`;
}

const OUTERS: Body[] = ["Uranus", "Neptune", "Pluto"];
const isOuter = (b: Body) => OUTERS.includes(b);

/** A one-line label, e.g. "Sun ☌ Moon". */
export function aspectLabel(asp: SynAspect): string {
  const glyph: Record<AspectType, string> = {
    conjunction: "☌", opposition: "☍", trine: "△", square: "□", sextile: "✶",
    quincunx: "⚻", sesquiquadrate: "⚼", quintile: "Q", semisquare: "∠", semisextile: "⚺",
  };
  return `${asp.a.body} ${glyph[asp.type]} ${asp.b.body}`;
}

export function formatOrb(orb: number): string {
  const deg = Math.floor(orb);
  const min = Math.round((orb - deg) * 60);
  return min === 60 ? `${deg + 1}°00′` : `${deg}°${String(min).padStart(2, "0")}′`;
}

/** Degrees into a sign, as the tradition writes them. */
export function formatDegree(deg: number): string {
  const d = Math.floor(deg);
  const m = Math.round((deg - d) * 60);
  return m === 60 ? `${d + 1}°00′` : `${d}°${String(m).padStart(2, "0")}′`;
}

// ── kutas ───────────────────────────────────────────────────────────────────────────────────────

const KUTA_FULL: Record<string, string> = {
  varna: "Their working temperaments sit comfortably — neither is inclined to talk down to the other.",
  vashya: "Each has natural influence over the other, in a way that reads as mutual rather than one-sided.",
  tara: "Each birth star is fortunate for the other's wellbeing, counted in both directions.",
  yoni: "Instinctive and physical compatibility is rated at its maximum by this test.",
  grahaMaitri: "The two minds are natural allies — the planets ruling their Moons are friends.",
  gana: "Their basic dispositions belong to the same order, so nothing has to be explained twice.",
  bhakoot: "The two Moon signs stand in a relationship the tradition treats as prosperous for a shared life.",
  nadi: "Different constitutional types — the strongest single result available in the whole system.",
};

const KUTA_NONE: Record<string, string> = {
  varna: "The tradition reads this ordering as slightly against the grain. It is worth one point of thirty-six.",
  vashya: "Neither yields naturally to the other; influence has to be negotiated rather than assumed.",
  tara: "The count between the two birth stars falls in an inauspicious remainder in both directions.",
  yoni: "The two birth-star animals are classical enemies — the tradition's blunt way of saying the instincts differ.",
  grahaMaitri: "The planets ruling the two Moons regard each other as enemies: minds that work differently at the root.",
  gana: "A Rakshasa disposition paired against a Deva or Manushya one — the tradition's sharpest temperament warning.",
  bhakoot: "Bhakoot dosha: the Moon signs stand in one of the three afflicted relationships.",
  nadi: "Nadi dosha — the same constitutional type. This is the heaviest single deduction in Guna Milan.",
};

export function explainKuta(k: KutaResult): string {
  if (k.points >= k.maxPoints) return KUTA_FULL[k.key] ?? "";
  if (k.points <= 0) return KUTA_NONE[k.key] ?? "";
  const pct = Math.round((k.points / k.maxPoints) * 100);
  return `Partial agreement — ${k.points} of ${k.maxPoints} (${pct}%). The rule found something to ` +
    `work with rather than a clean match or a clean failure.`;
}

export function explainDosha(d: Dosha): string {
  if (d.cancelled) {
    return `${d.detail} ${d.caveat ?? ""} On the classical exemptions this one does not stand.`.trim();
  }
  return `${d.detail} ${d.caveat ?? ""}`.trim();
}

/** The two or three sentences that go at the very top of a report. */
export function headlineSummary(
  nameA: string, nameB: string, overall: number, gunaTotal: number,
  ease: number, charge: number,
): string {
  const gunaPart = gunaTotal >= 18
    ? `Guna Milan gives ${gunaTotal.toFixed(1)} of 36, above the conventional threshold of 18`
    : `Guna Milan gives ${gunaTotal.toFixed(1)} of 36, under the conventional threshold of 18`;

  const easePart = ease >= 60 ? "the aspects between the charts lean supportive"
    : ease >= 45 ? "the aspects between the charts are mixed"
    : "the aspects between the charts lean difficult";

  const chargePart = charge >= 65 ? "and there is a lot of contact between them"
    : charge >= 35 ? "with a moderate amount of contact between them"
    : "though the two charts barely touch, which usually reads as indifference rather than conflict";

  return `${nameA} and ${nameB}: ${gunaPart}; ${easePart}, ${chargePart}. ` +
    `The combined figure is ${overall.toFixed(0)} out of 100 — a blend, not a verdict.`;
}
