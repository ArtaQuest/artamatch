/** TEMPORARY verification probe — delete after running. */

// @vitest-environment jsdom

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";

const BANNED = ["guna milan", "synastry", "sidereal", "vedic", "koota"];

describe("probe", () => {
  it("A: jsdom document in the unit-test env does NOT contain index.html head", () => {
    // This is the same environment tests/app.test.tsx runs in.
    const metas = [...document.querySelectorAll("meta[name=description]")];
    console.log("META TAGS PRESENT IN TEST DOM:", metas.length);
    console.log("HEAD HTML:", JSON.stringify(document.head.innerHTML));
    console.log("TITLE:", JSON.stringify(document.title));
    expect(metas.length).toBe(0); // nothing for a body/head sweep to catch
  });

  it("B: the shipped index.html breaches the same BANNED list the suite enforces", () => {
    const html = readFileSync("/Users/arash/Studio/artamatch/index.html", "utf8");
    const desc = /name="description"\s*\n?\s*content="([^"]*)"/m.exec(html)?.[1] ?? "";
    const title = /<title>([^<]*)<\/title>/.exec(html)?.[1] ?? "";
    const hits = BANNED.filter((w) => new RegExp(`\\b${w}\\b`, "i").test(desc + " " + title));
    console.log("DESCRIPTION:", JSON.stringify(desc));
    console.log("TITLE TAG:", JSON.stringify(title));
    console.log("BANNED TERMS PRESENT IN HEAD METADATA:", hits);
    expect(hits.length).toBe(0); // EXPECTED TO FAIL — proves the breach is real
  });
});
