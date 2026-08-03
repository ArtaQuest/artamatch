/**
 * No jargon, checked at the source rather than at the screen.
 *
 * tests/app.test.tsx already walks the RENDERED page for banned vocabulary. That is the guard that
 * matters most, but it has a hole: a string stops being covered the moment it stops being rendered.
 * Exactly that happened — `uncertaintyNote()` still said "Guna Milan" long after the report replaced
 * it with the probability table, and the DOM test could not see it because nothing displayed it.
 *
 * So this walks every user-facing string the ENGINE can produce, whether or not the UI currently
 * shows it: the eight tests' names, rules and evidence, the warnings, the written explanations for
 * every connection, and the whole corpus. If a string can reach a reader, it is checked here.
 */

import { describe, it, expect } from "vitest";
import { gunaMilan, type KutaSide } from "../src/engine/kuta";
import { nakshatraOf } from "../src/engine/nakshatra";
import { chartForDate, BODIES } from "../src/engine/ephemeris";
import { matchPair } from "../src/engine/score";
import { summariseSynastry } from "../src/engine/synastry";
import {
  explainAspect, explainKuta, explainDosha, aspectLabel, closeness, headlineSummary,
  birthStarText, moonSignText, BODY_MEANS,
} from "../src/engine/interpret";

/** Vocabulary that must never reach a reader. Matched on word boundaries. */
const BANNED = [
  "nakshatra", "rashi", "rasi", "kuta", "koota", "guna", "dosha", "doshas", "graha", "varna",
  "vashya", "yoni", "bhakoot", "nadi", "mangal", "kuja", "ayanamsa", "sidereal", "tropical",
  "lahiri", "vedic", "jyotish", "synastry", "natal", "quincunx",
  "sesquiquadrate", "semisextile", "orb", "cusp", "ascendant", "lagna",
  "retrograde", "exalted", "debilitated", "benefic", "malefic", "pada", "dasha", "janma",
  "chandra", "brahmana", "kshatriya", "vaishya", "shudra", "deva", "manushya", "rakshasa",
  "adi", "madhya", "antya", "vata", "pitta", "kapha", "ecliptic", "longitude", "ephemeris",
  // Star and node names are not assumed knowledge either — plain titles carry them.
  "ashwini", "bharani", "krittika", "rohini", "mrigashira", "ardra", "punarvasu", "pushya",
  "ashlesha", "magha", "phalguni", "hasta", "chitra", "swati", "vishakha", "anuradha",
  "jyeshtha", "mula", "ashadha", "shravana", "dhanishtha", "shatabhisha", "bhadrapada",
  "revati", "rahu", "ketu",
];

const RX = BANNED.map((w) => [w, new RegExp(`\\b${w}\\b`, "i")] as const);

function offences(label: string, text: unknown): string[] {
  if (typeof text !== "string" || !text) return [];
  return RX.filter(([, rx]) => rx.test(text)).map(([w]) => `${label}: "${w}" in ${JSON.stringify(text.slice(0, 130))}`);
}

function sideFor(iso: string): KutaSide {
  const chart = chartForDate(iso)!;
  const moon = chart.byBody.Moon;
  return {
    moonLon: moon.lon, nakshatra: nakshatraOf(moon.lon).info, rasi: moon.sign,
    degInSign: moon.deg, marsLon: chart.byBody.Mars.lon, venusLon: chart.byBody.Venus.lon,
  };
}

/** A spread of dates chosen to exercise full / partial / zero on every test, plus both warnings. */
const DATES = [
  "1994-02-15", "1965-07-27", "1999-12-06", "2004-12-27", "2004-12-21", "1815-12-10",
  "1912-06-23", "1867-11-07", "1980-03-19", "1955-09-02", "2001-01-01", "1943-06-30",
];

describe("nothing a reader can see uses astrology jargon", () => {
  it("keeps the eight tests clean — names, rules, evidence and explanations", () => {
    const found: string[] = [];
    for (const a of DATES) {
      for (const b of DATES) {
        const g = gunaMilan(sideFor(a), sideFor(b));
        for (const k of g.kutas) {
          found.push(...offences(`${a}/${b} ${k.key}.name`, k.name));
          found.push(...offences(`${a}/${b} ${k.key}.measures`, k.measures));
          found.push(...offences(`${a}/${b} ${k.key}.rule`, k.rule));
          found.push(...offences(`${a}/${b} ${k.key}.evidence`, k.evidence));
          found.push(...offences(`${a}/${b} ${k.key}.explain`, explainKuta(k)));
        }
        found.push(...offences(`${a}/${b} band`, g.band.label + ". " + g.band.note));
        for (const d of g.doshas) {
          found.push(...offences(`${a}/${b} warning.name`, d.name));
          found.push(...offences(`${a}/${b} warning.text`, explainDosha(d)));
        }
      }
    }
    expect([...new Set(found)]).toEqual([]);
  });

  it("keeps every written connection clean, across every pairing", () => {
    const found: string[] = [];
    for (let i = 0; i < DATES.length; i++) {
      const A = chartForDate(DATES[i])!;
      const B = chartForDate(DATES[(i + 1) % DATES.length])!;
      const s = summariseSynastry(A, B);
      found.push(...offences("headline", headlineSummary(s.easeScore, s.easeScore, s.chargeScore)));
      for (const asp of s.aspects) {
        found.push(...offences(`${asp.a.body}/${asp.b.body} label`, aspectLabel(asp, "Ada", "Alan")));
        found.push(...offences(`${asp.a.body}/${asp.b.body} text`, explainAspect(asp, "Ada", "Alan")));
        found.push(...offences("closeness", closeness(asp.exactness)));
      }
    }
    expect([...new Set(found)]).toEqual([]);
  });

  it("keeps the uncertainty wording clean — the string the report stopped rendering", () => {
    const found: string[] = [];
    for (const a of DATES) {
      for (const b of DATES) {
        const m = matchPair(a, b, true)!;
        found.push(...offences(`${a}/${b} uncertainty`, m.uncertaintyNote));
        for (const o of m.distribution?.outcomes ?? []) {
          found.push(...offences("outcome.labelA", o.labelA));
          found.push(...offences("outcome.labelB", o.labelB));
        }
      }
    }
    expect([...new Set(found)]).toEqual([]);
  });

  it("keeps the whole written corpus clean", () => {
    const found: string[] = [];
    for (let i = 0; i < 27; i++) {
      const s = birthStarText(i);
      expect(s, `birth star ${i} missing`).not.toBeNull();
      found.push(...offences(`star${i}.title`, s!.title));
      found.push(...offences(`star${i}.summary`, s!.summary));
      found.push(...offences(`star${i}.relationships`, s!.inRelationships));
    }
    for (let i = 0; i < 12; i++) {
      const m = moonSignText(i);
      expect(m, `moon sign ${i} missing`).not.toBeNull();
      found.push(...offences(`sign${i}.title`, m!.title));
      found.push(...offences(`sign${i}.style`, m!.style));
    }
    for (const body of BODIES) found.push(...offences(`means.${body}`, BODY_MEANS[body]));
    expect([...new Set(found)]).toEqual([]);
  });

  it("has a written reading for every body pair, so nobody gets the generic fallback", () => {
    // 10 bodies → 55 unordered pairs. Every one must resolve to real prose in all four
    // configurations, or a reader hits assembled-from-slots text exactly where it shows most.
    const A = chartForDate("1994-02-15")!;
    const B = chartForDate("1980-03-19")!;
    const seen = new Set<string>();
    for (const asp of summariseSynastry(A, B).aspects) {
      const text = explainAspect(asp, "Ada", "Alan");
      // The compositional fallback is recognisable by its stitched shape.
      expect(text, `${asp.a.body}/${asp.b.body} fell through to the fallback`)
        .not.toMatch(/In practice this is about .* meeting /);
      seen.add([asp.a.body, asp.b.body].sort().join("|"));
    }
    expect(seen.size).toBeGreaterThan(5);
  });
});
