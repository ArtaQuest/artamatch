/**
 * nakshatra.ts — the 27 lunar mansions and the attributes Guna Milan reads off them.
 *
 * The sidereal ecliptic is divided into 27 nakshatras of 13°20′ each, starting at 0° sidereal Aries.
 * The Moon's nakshatra at birth is the Janma Nakshatra, the "birth star" — the single most personal
 * point in a Vedic chart, and the thing six of the eight kutas are computed from.
 *
 * The attribute table below is load-bearing: get one row wrong and every match involving that
 * nakshatra is wrong, silently. It was cross-checked four ways (three independent research passes
 * plus this one) and is additionally guarded by STRUCTURAL invariants in tests/nakshatra.test.ts —
 * exactly 9 nakshatras per gana, the Vimshottari lord cycle repeating three times, the palindromic
 * nadi pattern, and 13 yoni animals appearing twice with mongoose appearing once. Those invariants
 * are properties of the real system, so a typo cannot survive them.
 */

export const NAK_ARC = 360 / 27; // 13°20′

export type Gana = "deva" | "manushya" | "rakshasa";
export type Nadi = "adi" | "madhya" | "antya";
export type YoniGender = "male" | "female";

export type YoniAnimal =
  | "horse" | "elephant" | "sheep" | "serpent" | "dog" | "cat" | "rat"
  | "cow" | "buffalo" | "tiger" | "deer" | "monkey" | "mongoose" | "lion";

export type NakshatraInfo = {
  index: number;          // 0-based
  num: number;            // 1-based, how the tradition numbers them
  name: string;
  /** Vimshottari dasha lord — also the lord used by Tara Kuta interpretations. */
  lord: string;
  gana: Gana;
  yoni: YoniAnimal;
  yoniGender: YoniGender;
  nadi: Nadi;
};

type Row = [string, string, Gana, YoniAnimal, YoniGender, Nadi];

// name, lord, gana, yoni animal, yoni gender, nadi
const ROWS: Row[] = [
  ["Ashwini",           "Ketu",    "deva",     "horse",    "male",   "adi"],
  ["Bharani",           "Venus",   "manushya", "elephant", "male",   "madhya"],
  ["Krittika",          "Sun",     "rakshasa", "sheep",    "female", "antya"],
  ["Rohini",            "Moon",    "manushya", "serpent",  "male",   "antya"],
  ["Mrigashira",        "Mars",    "deva",     "serpent",  "female", "madhya"],
  ["Ardra",             "Rahu",    "manushya", "dog",      "female", "adi"],
  ["Punarvasu",         "Jupiter", "deva",     "cat",      "female", "adi"],
  ["Pushya",            "Saturn",  "deva",     "sheep",    "male",   "madhya"],
  ["Ashlesha",          "Mercury", "rakshasa", "cat",      "male",   "antya"],
  ["Magha",             "Ketu",    "rakshasa", "rat",      "male",   "antya"],
  ["Purva Phalguni",    "Venus",   "manushya", "rat",      "female", "madhya"],
  ["Uttara Phalguni",   "Sun",     "manushya", "cow",      "female", "adi"],
  ["Hasta",             "Moon",    "deva",     "buffalo",  "female", "adi"],
  ["Chitra",            "Mars",    "rakshasa", "tiger",    "female", "madhya"],
  ["Swati",             "Rahu",    "deva",     "buffalo",  "male",   "antya"],
  ["Vishakha",          "Jupiter", "rakshasa", "tiger",    "male",   "antya"],
  ["Anuradha",          "Saturn",  "deva",     "deer",     "female", "madhya"],
  ["Jyeshtha",          "Mercury", "rakshasa", "deer",     "male",   "adi"],
  ["Mula",              "Ketu",    "rakshasa", "dog",      "male",   "adi"],
  ["Purva Ashadha",     "Venus",   "manushya", "monkey",   "male",   "madhya"],
  ["Uttara Ashadha",    "Sun",     "manushya", "mongoose", "male",   "antya"],
  ["Shravana",          "Moon",    "deva",     "monkey",   "female", "antya"],
  ["Dhanishta",         "Mars",    "rakshasa", "lion",     "female", "madhya"],
  ["Shatabhisha",       "Rahu",    "rakshasa", "horse",    "female", "adi"],
  ["Purva Bhadrapada",  "Jupiter", "manushya", "lion",     "male",   "adi"],
  ["Uttara Bhadrapada", "Saturn",  "manushya", "cow",      "male",   "madhya"],
  ["Revati",            "Mercury", "deva",     "elephant", "female", "antya"],
];

export const NAKSHATRAS: NakshatraInfo[] = ROWS.map(([name, lord, gana, yoni, yoniGender, nadi], i) => ({
  index: i, num: i + 1, name, lord, gana, yoni, yoniGender, nadi,
}));

export const NAK_NAMES = NAKSHATRAS.map((n) => n.name);

/** Where a sidereal longitude falls: which nakshatra, and which of its four 3°20′ padas. */
export function nakshatraOf(lon: number): { info: NakshatraInfo; pada: number; degIn: number } {
  const l = ((lon % 360) + 360) % 360;
  const index = Math.floor(l / NAK_ARC) % 27;
  const degIn = l - index * NAK_ARC;
  return { info: NAKSHATRAS[index], pada: Math.floor(degIn / (NAK_ARC / 4)) + 1, degIn };
}

/** Longitude at which a nakshatra begins. */
export const nakshatraStart = (index: number) => index * NAK_ARC;

/** Human labels, for the report. */
export const GANA_LABEL: Record<Gana, string> = {
  deva: "Deva (divine)",
  manushya: "Manushya (human)",
  rakshasa: "Rakshasa (demonic)",
};

export const NADI_LABEL: Record<Nadi, string> = {
  adi: "Ādi (Vāta)",
  madhya: "Madhya (Pitta)",
  antya: "Antya (Kapha)",
};

export const YONI_LABEL: Record<YoniAnimal, string> = {
  horse: "Horse", elephant: "Elephant", sheep: "Sheep", serpent: "Serpent", dog: "Dog",
  cat: "Cat", rat: "Rat", cow: "Cow", buffalo: "Buffalo", tiger: "Tiger", deer: "Deer",
  monkey: "Monkey", mongoose: "Mongoose", lion: "Lion",
};
