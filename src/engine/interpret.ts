/**
 * interpret.ts — the words.
 *
 * Every rendered sentence that is not generated from a rule lives here or in src/data/corpus.json.
 * Two kinds: what each of the eight tests means at full, partial and no marks; and what each of the
 * 27 birth stars and 12 Moon signs is said to suggest.
 *
 * THE VOCABULARY RULE. The only specialist words allowed on screen are the 12 zodiac sign names.
 * Everything else is plain English: birth stars are named by their meaning ("The quick starter"),
 * never transliterated. The reader is assumed to know nothing. Two tests enforce this — one over
 * the rendered page, one over every string this module can produce — because a string escapes the
 * first the moment the UI stops rendering it.
 *
 * The voice is plain and non-fatalistic: tendencies described, never predictions made.
 */

import { type KutaResult, type Dosha } from "./kuta";
import corpus from "../data/corpus.json";

type Corpus = {
  birthStars: { index: number; name: string; title: string; summary: string; inRelationships: string }[];
  moonSigns: { index: number; sign: string; title: string; style: string }[];
  planets: { body: string; opens: string; what: string; readings: string[] }[];
};
const CORPUS = corpus as Corpus;

// ── the natal chart, body by body ───────────────────────────────────────────────────────────────

/**
 * The five bodies a birth DATE can say something personal about, in reading order, each with the
 * plain phrase that says what it is taken to stand for.
 *
 * Jupiter and Saturn are drawn on the chart and make connections, but get no paragraph: Jupiter
 * holds a sign for about a year and Saturn for two and a half, so a reading of them describes
 * everyone born around the same time. The three slowest are further out still. Where a placement
 * is shared with a whole cohort, saying so is more useful than a character sketch of the cohort.
 */
export const READ_BODIES = CORPUS.planets.map((p) => p.body);

export function planetMeta(body: string): { opens: string; what: string } | null {
  const row = CORPUS.planets.find((p) => p.body === body);
  return row ? { opens: row.opens, what: row.what } : null;
}

/** What this body in this sign is said to suggest — one plain sentence or two, never a prediction. */
export function planetReading(body: string, sign: number): string {
  return CORPUS.planets.find((p) => p.body === body)?.readings[sign] ?? "";
}

// ── the birth stars and Moon signs ──────────────────────────────────────────────────────────────

/** What their birth star is said to suggest, in plain words. */
export function birthStarText(index: number): { title: string; summary: string; inRelationships: string } | null {
  const row = CORPUS.birthStars.find((s) => s.index === index);
  return row ? { title: row.title, summary: row.summary, inRelationships: row.inRelationships } : null;
}

/**
 * The name a birth star goes by on this page: its plain-English title, never the Sanskrit name.
 * "The quick starter" carries meaning to a reader with no background; a transliterated name carries
 * none. The traditional names stay in the data for anyone checking against another source.
 */
export function starTitle(index: number): string {
  return CORPUS.birthStars.find((s) => s.index === index)?.title ?? `star ${index + 1} of 27`;
}

/** How someone with the Moon in this sign tends to handle feelings and closeness. */
export function moonSignText(index: number): { title: string; style: string } | null {
  const row = CORPUS.moonSigns.find((s) => s.index === index);
  return row ? { title: row.title, style: row.style } : null;
}

// ── the eight tests ─────────────────────────────────────────────────────────────────────────────

const KUTA_FULL: Record<string, string> = {
  varna: "The way they each go about things sits comfortably — neither is inclined to talk down to the other.",
  vashya: "Each has natural influence over the other, in a way that reads as mutual rather than one-sided.",
  tara: "Each one comes out lucky for the other, counted both ways round.",
  yoni: "The instinctive, physical side rates as well as this test allows.",
  grahaMaitri: "Their minds are natural allies.",
  gana: "Their basic temperaments match, so nothing has to be explained twice.",
  bhakoot: "Their Moon signs sit at a distance the tradition treats as good for building a life together.",
  nadi: "They are built differently underneath — the strongest single result available anywhere in this system.",
};

/** Middling results, said differently per test — eight identical "partial" sentences down one page
 *  reads as a template rather than a reading. */
const KUTA_PARTIAL: Record<string, string> = {
  varna: "Somewhere in between, on a test worth a single point either way.",
  vashya: "Neither yields easily to the other, but neither digs in either.",
  tara: "Lucky for each other in one direction and not the other, which is the commonest result here.",
  yoni: "Their instincts are neither the same nor at odds — different, and compatible enough.",
  grahaMaitri: "Their minds meet part of the way. Not the same wavelength, not opposed ones.",
  gana: "Their temperaments differ without clashing outright.",
  bhakoot: "",
  nadi: "",
};

const KUTA_NONE: Record<string, string> = {
  varna: "The tradition reads this way round as slightly against the grain. It is worth one point out of thirty-six, so it is the least of anyone's worries.",
  vashya: "Neither yields naturally to the other; influence has to be negotiated rather than assumed.",
  tara: "The count between their two birth stars lands on an unlucky position both ways round.",
  yoni: "Their two birth-star animals are traditional enemies — a blunt old way of saying the instincts differ.",
  grahaMaitri: "The two planets behind their Moon signs count each other enemies: minds that work differently at the root.",
  gana: "A forceful temperament against a gentler one — the sharpest warning this system gives about temperament.",
  bhakoot: "Their Moon signs sit at one of the three distances the tradition treats as hard going.",
  nadi: "They are built the same way underneath. This is the heaviest single deduction anywhere in the thirty-six.",
};

export function explainKuta(k: KutaResult): string {
  if (k.points >= k.maxPoints) return KUTA_FULL[k.key] ?? "";
  if (k.points <= 0) return KUTA_NONE[k.key] ?? "";
  return KUTA_PARTIAL[k.key] || `Part marks — ${k.points} of ${k.maxPoints}.`;
}

export function explainDosha(d: Dosha): string {
  // The heading already says whether it was set aside, so it is not repeated here.
  return `${d.detail} ${d.caveat ?? ""}`.trim();
}
