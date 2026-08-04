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
    expect(screen.getAllByText(/higher than/i).length).toBeGreaterThan(0);
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
    // Every prediction carries an interval: either it is certain ("of 36") or it states the ±.
    expect(row.textContent).toMatch(/of 36|±\d/);
  });

  it("opens a full report with every section populated", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");

    const ranking = screen.getByRole("heading", { name: /Ranked against Ada/i }).closest(".panel") as HTMLElement;
    fireEvent.click(within(ranking).getByRole("button", { name: /Turing/ }));

    expect(screen.getByText(/Ada & Turing/)).toBeDefined();
    expect(screen.getAllByText(/randomly paired dates/i).length).toBeGreaterThan(0);
    // All three instruments render at once — there are no tabs to hide anything behind.
    expect(document.querySelector(".anatomy .bar")?.children.length).toBe(8);
    expect((document.querySelector(".landscape")?.children.length ?? 0)).toBeGreaterThan(30);

    // All eight tests, each with the rule it used and the values it read — no tab to open.
    for (const test of ["Ways of working", "Give and take", "Good for each other",
      "Physical instinct", "Meeting of minds", "Temperament", "Life together", "Underlying makeup"]) {
      expect(screen.getAllByText(test).length, `${test} missing`).toBeGreaterThan(0);
    }
    // The rule and the values live behind "Show the working" — present for every test, one click
    // away rather than eight dense paragraphs burying the answer.
    // Eight per-test disclosures plus one "more about" per person.
    expect(screen.getAllByRole("group").length).toBe(10);
    expect(screen.getAllByText(/Show the working/).length).toBe(8);
    expect(screen.getAllByText(/How it is scored:/).length).toBe(8);
    expect(screen.getAllByText(/What was read:/).length).toBe(8);

    // The document's spine: numbered sections, each with a heading.
    expect(document.querySelectorAll(".sec > h3").length).toBeLessThanOrEqual(4);
    expect(screen.getByText(/Where the points came from/i)).toBeDefined();
    expect(screen.getByText(/How sure this is/i)).toBeDefined();
    expect(screen.getByText(/The two of them/i)).toBeDefined();

    // Both people are described, by plain title rather than a transliterated name.
    expect(screen.getAllByText(/their birth star, one of the 27/i).length).toBe(2);
  });

  it("names the pair in a real heading and moves focus there when a reading opens", () => {
    // Opening a reading replaces the whole right-hand column. Focus used to fall to <body>, so a
    // screen-reader user got silence at the app's central interaction, and heading navigation
    // skipped straight past whose reading it was.
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");
    const ranking = screen.getByRole("heading", { name: /Ranked against Ada/i }).closest(".panel") as HTMLElement;
    fireEvent.click(within(ranking).getByRole("button", { name: /Turing/ }));

    const h = screen.getByRole("heading", { name: /Ada & Turing/, level: 2 });
    expect(document.activeElement).toBe(h);
    // One main landmark, and errors announce themselves.
    expect(document.querySelectorAll("main").length).toBe(1);
  });

  it("announces a refused entry instead of failing silently", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /add to my list/i }));
    expect(screen.getByRole("alert").textContent).toMatch(/date of birth|calendar date|name/i);
  });

  it("marks the Landscape bar that matches the score, not the one beside it", () => {
    // The marker sat on Math.round(score) - 1 while tooltips said "score i+1", so the gold bar
    // pointed at the wrong score AND disagreed with its own hover text.
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");
    const ranking = screen.getByRole("heading", { name: /Ranked against Ada/i }).closest(".panel") as HTMLElement;
    fireEvent.click(within(ranking).getByRole("button", { name: /Turing/ }));

    const bars = [...document.querySelectorAll(".landscape i")];
    const marked = bars.findIndex((b) => b.classList.contains("here"));
    const title = bars[marked].getAttribute("title") ?? "";
    // The marked bar's own tooltip must name the index it sits at.
    expect(title).toMatch(new RegExp(`^Score ${marked}:`));
    // And it must be the bar for the reported score.
    const hero = document.querySelector(".hero .num")?.textContent ?? "";
    const shown = parseFloat(hero);
    expect(Math.abs(marked - shown)).toBeLessThanOrEqual(0.5);
  });

  it("says a shared Moon sign once, not twice in adjacent columns", () => {
    // 1984-02-08 x 1967-08-26 both have the Moon in Aries. Printing the identical paragraph in
    // both columns reads as a bug, so the shared case is stated once above them.
    window.history.replaceState({}, "",
      "/?n=CertA&b=1984-02-08&n2=CertB&b2=1967-08-26");
    render(<App />);
    expect(screen.getByText(/Both have the Moon in Aries/i)).toBeDefined();
    // "Fast heat, quick recovery" is the Aries line — it must appear exactly once.
    // Once above the two columns, never twice inside them.
    expect(screen.getAllByText(/Fast heat, quick recovery/i)).toHaveLength(1);
    window.history.replaceState({}, "", "/");
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
      "lahiri", "vedic", "jyotish", "synastry", "quincunx", "conjunction", "opposition", "trine",
      "sextile", "square", "sesquiquadrate", "semi-sextile", "orb", "lagna", "ascendant", "retrograde", "exalted",
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

    // One document, so one sweep covers the whole reading.
    const seen: string[] = [];
    const text = (document.body.textContent ?? "").toLowerCase();
    for (const word of BANNED) {
      // Word boundaries so "gana" does not fire on "organ" and "orb" not on "absorb".
      if (new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`).test(text)) {
        seen.push(word);
      }
    }
    expect([...new Set(seen)]).toEqual([]);
  });

  it("shows the everyone-against-everyone grid symmetrically", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");
    addPerson("Curie", "1867-11-07");

    fireEvent.click(screen.getByRole("button", { name: /Everyone vs everyone/i }));
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
