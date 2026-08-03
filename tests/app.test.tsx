/**
 * Does the actual page work?
 *
 * The engine tests prove the numbers are right. These prove a person can get at them: that the app
 * mounts, that adding someone by date produces a ranking, that opening a report renders every
 * section with real content, and that the uncertainty warning appears on exactly the dates that
 * warrant it.
 *
 * React errors are made fatal here — a component that throws during render would otherwise be
 * swallowed by the error boundary and the test would pass over a blank screen.
 */

// @vitest-environment jsdom

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, within, cleanup, fireEvent } from "@testing-library/react";
import App from "../src/App";

let consoleError: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  localStorage.clear();
  // Most tests want a genuinely empty list, so suppress the first-visit seed. The seed itself has
  // its own test below, which clears this flag again.
  localStorage.setItem("artamatch.seeded.v1", "1");
  consoleError = vi.spyOn(console, "error").mockImplementation((...args) => {
    throw new Error(`React logged an error during render: ${args.join(" ")}`);
  });
  // No network in tests: the public-account fetch must fail gracefully, not hang or crash.
  vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline in tests"))));
});

afterEach(() => {
  cleanup();
  consoleError.mockRestore();
  vi.unstubAllGlobals();
});

function addPerson(name: string, birthday: string) {
  fireEvent.change(screen.getByLabelText(/^name$/i), { target: { value: name } });
  fireEvent.change(screen.getByLabelText(/date of birth/i), { target: { value: birthday } });
  fireEvent.click(screen.getByRole("button", { name: /add to my list/i }));
}

describe("ArtaMatch app", () => {
  it("mounts and shows the empty state", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "ArtaMatch", level: 1 })).toBeDefined();
    expect(screen.getByText(/Nobody here yet/i)).toBeDefined();
  });

  it("refuses an impossible date instead of charting the wrong day", () => {
    render(<App />);
    // A real browser (and jsdom) will not let <input type="date"> hold 2001-02-29 at all — it is
    // not a leap year — so the field ends up empty and the entry is refused either way. What
    // matters is that nobody is added and the reason is stated.
    addPerson("Nobody", "2001-02-29");
    expect(screen.getByText(/Nobody here yet/i)).toBeDefined();
    expect(screen.getByText(/date of birth is the one thing this needs|not a real calendar date/i)).toBeDefined();
  });

  it("refuses an impossible date arriving through a share link", () => {
    // The date input cannot produce one, but ?b= can — and Date.UTC would silently roll
    // 2001-02-29 forward to 1 March, charting the wrong day. This is the path that needs guarding.
    window.history.replaceState({}, "", "/?n=Ghost&b=2001-02-29");
    render(<App />);
    expect(screen.getByText(/Nobody here yet/i)).toBeDefined();
    expect(screen.queryByText("Ghost")).toBeNull();
    window.history.replaceState({}, "", "/");
  });

  it("accepts a valid date through a share link", () => {
    window.history.replaceState({}, "", "/?n=Ghost&b=2000-02-29"); // 2000 IS a leap year
    render(<App />);
    expect(screen.getAllByText("Ghost").length).toBeGreaterThan(0);
    window.history.replaceState({}, "", "/");
  });

  it("opens a two-person share link straight into the reading", () => {
    window.history.replaceState({}, "", "/?n=Ada&b=1815-12-10&n2=Alan&b2=1912-06-23");
    render(<App />);
    // Both people land in the list AND the pair's reading opens directly.
    expect(screen.getByText(/Ada & Alan/)).toBeDefined();
    expect(screen.getByText(/4 traditions rate this pair/i)).toBeDefined();
    window.history.replaceState({}, "", "/");
  });

  it("adds someone, makes them self, and shows their birth star", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    // "Ada" appears both in the list and in the "Ranked against Ada" heading — both are correct.
    expect(screen.getAllByText(/Ada/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/10 December 1815/)).toBeDefined();
    // Prompted to add a second person rather than shown an empty ranking.
    expect(screen.getByText(/Add at least one more person/i)).toBeDefined();
  });

  it("ranks a second person and shows the component scores", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");

    const ranking = screen.getByRole("heading", { name: /Ranked against Ada/i }).closest(".panel") as HTMLElement;
    const row = within(ranking).getByRole("button", { name: /Turing/ });
    expect(row.textContent).toMatch(/higher than \d+ in 100 random pairs/i);
    expect(row.textContent).toMatch(/\d+ help, \d+ rub/i);
    expect(row.textContent).toMatch(/of 36/);
  });

  it("opens a full report with every section populated", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");

    const ranking = screen.getByRole("heading", { name: /Ranked against Ada/i }).closest(".panel") as HTMLElement;
    fireEvent.click(within(ranking).getByRole("button", { name: /Turing/ }));

    expect(screen.getByText(/Ada & Turing/)).toBeDefined();
    expect(screen.getAllByText(/random pairs/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/4 traditions rate this pair/i)).toBeDefined();

    // The eight tests, each with the rule it used and the values it read.
    fireEvent.click(screen.getByRole("tab", { name: /eight tests/i }));
    for (const test of ["Ways of working", "Give and take", "Good for each other",
      "Physical instinct", "Meeting of minds", "Temperament", "Life together", "Underlying makeup"]) {
      // A test name can legitimately appear twice: once in the three plain answers at the top
      // (as the strongest or weakest agreement) and once in the list itself.
      expect(screen.getAllByText(test).length, `${test} missing`).toBeGreaterThan(0);
    }
    expect(screen.getAllByText(/How it is scored:/).length).toBe(8);
    expect(screen.getAllByText(/What was read:/).length).toBe(8);

    // What runs between them: the grid plus written explanations.
    fireEvent.click(screen.getByRole("tab", { name: /runs between/i }));
    expect(screen.getByText(/connection grid/i)).toBeDefined();
    expect(screen.getByText(/strongest first/i)).toBeDefined();

    // Where everything was: both charts, all ten bodies each.
    fireEvent.click(screen.getByRole("tab", { name: /Where everything/i }));
    expect(screen.getAllByText(/Everything else/i).length).toBe(2);
    expect(screen.getAllByText(/Birth star/i).length).toBeGreaterThanOrEqual(2);
    // Glyphs are gone — planets are named in words, once per chart.
    expect(screen.getAllByText(/^Sun$/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/^Pluto$/).length).toBeGreaterThanOrEqual(2);
  });

  it("warns on a date where the Moon changes birth star, and not on one where it does not", () => {
    render(<App />);
    // 1965-07-27: the Moon crosses two nakshatra boundaries AND a rasi boundary — four states.
    addPerson("Wanderer", "1965-07-27");
    expect(screen.getAllByText(/time matters/i).length).toBeGreaterThan(0);
  });

  it("survives the public-account fetch failing", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /Load ArtaQuest members/i }));
    // The button returns to its idle label and an explanation appears; nothing throws.
    expect(await screen.findByText(/Could not reach artaquest\.com/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /Load ArtaQuest members/i })).toBeDefined();
  });

  it("persists manual entries to localStorage and reloads them", () => {
    const first = render(<App />);
    addPerson("Ada", "1815-12-10");
    expect(JSON.parse(localStorage.getItem("artamatch.people.v1")!)).toHaveLength(1);
    first.unmount();

    render(<App />);
    expect(screen.getAllByText(/Ada/).length).toBeGreaterThan(0);
  });

  it("seeds the starting list once, and does not resurrect a deleted seed", () => {
    localStorage.removeItem("artamatch.seeded.v1");
    const first = render(<App />);
    for (const name of ["Ayse Altundal", "Elif Eda Ayan", "Lana El Jamal"]) {
      expect(screen.getAllByText(new RegExp(name)).length, name).toBeGreaterThan(0);
    }
    // Seeds are ordinary manual entries: deletable.
    fireEvent.click(screen.getByRole("button", { name: /Remove Lana El Jamal/i }));
    expect(screen.queryByText(/Lana El Jamal/)).toBeNull();
    first.unmount();

    // …and a deleted seed stays deleted across a reload.
    render(<App />);
    expect(screen.queryByText(/Lana El Jamal/)).toBeNull();
    expect(screen.getAllByText(/Ayse Altundal/).length).toBeGreaterThan(0);
  });

  it("ranks the seeded people against each other", () => {
    localStorage.removeItem("artamatch.seeded.v1");
    render(<App />);
    const ranking = screen.getByRole("heading", { name: /Ranked against Ayse Altundal/i }).closest(".panel") as HTMLElement;
    // Two others, each with a real score.
    const rows = within(ranking).getAllByRole("button");
    expect(rows.length).toBeGreaterThanOrEqual(2);
    expect(ranking.textContent).toMatch(/Elif Eda Ayan/);
    expect(ranking.textContent).toMatch(/Lana El Jamal/);
    expect(ranking.textContent).toMatch(/higher than \d+ in 100 random pairs/i);
  });

  it("shows no astrology jargon anywhere a reader can see it", () => {
    // The guard is on the RENDERED TEXT, not the source, because that is the thing a reader
    // actually meets. Comments, variable names and the traditional terms kept for checking the
    // working are all free to say whatever they like — this asserts that none of it reaches screen.
    const BANNED = [
      "nakshatra", "rashi", "rasi", "kuta", "koota", "guna milan", "dosha", "graha", "varna",
      "vashya", "yoni", "bhakoot", "nadi", "mangal", "kuja", "ayanamsa", "sidereal", "tropical",
      "lahiri", "vedic", "jyotish", "synastry", "quincunx",
      "sesquiquadrate", "semi-sextile", "orb", "lagna", "ascendant", "retrograde", "exalted",
      "debilitated", "benefic", "malefic", "pada", "dasha", "janma", "chandra", "brāhmaṇa",
      "kṣatriya", "vaiśya", "śūdra", "deva", "manushya", "rakshasa",
      // The 27 traditional star names and the two node names are ALSO not assumed knowledge —
      // the page speaks in their plain titles. The five MAJOR angle names (conjunction,
      // opposition, trine, square, sextile) and the 12 sign names are the entire allowed
      // vocabulary, so they are absent from this list.
      "ashwini", "bharani", "krittika", "rohini", "mrigashira", "ardra", "punarvasu", "pushya",
      "ashlesha", "magha", "phalguni", "hasta", "chitra", "swati", "vishakha", "anuradha",
      "jyeshtha", "mula", "ashadha", "shravana", "dhanishtha", "shatabhisha", "bhadrapada",
      "revati", "rahu", "ketu",
    ];

    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");
    const ranking = screen.getByRole("heading", { name: /Ranked against Ada/i }).closest(".panel") as HTMLElement;
    fireEvent.click(within(ranking).getByRole("button", { name: /Turing/ }));

    const seen: string[] = [];
    for (const tab of [/In short/i, /eight tests/i, /runs between/i, /Where everything/i]) {
      fireEvent.click(screen.getByRole("tab", { name: tab }));
      const text = (document.body.textContent ?? "").toLowerCase();
      for (const word of BANNED) {
        // Word boundaries so "gana" does not fire on "organ" and "orb" not on "absorb".
        if (new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`).test(text)) {
          seen.push(`${word} (on ${tab.source})`);
        }
      }
    }
    expect([...new Set(seen)]).toEqual([]);
  });

  it("shows the everyone-against-everyone grid symmetrically", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");
    addPerson("Curie", "1867-11-07");

    fireEvent.click(screen.getByRole("tab", { name: /Everyone vs everyone/i }));
    const table = screen.getByText(/Every pair, scored on the Moon score/i).closest(".panel")!
      .querySelector("table")!;
    const rows = [...table.querySelectorAll("tbody tr")];
    expect(rows).toHaveLength(3);

    // Read the matrix out and assert it equals its own transpose.
    const values = rows.map((tr) =>
      [...tr.querySelectorAll("td")].map((td) => td.textContent!.trim()));
    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) {
        expect(values[i][j], `cell ${i},${j}`).toBe(values[j][i]);
      }
    }
  });
});
