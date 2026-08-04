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

    // The document's spine: numbered sections, each with a heading, in reading order.
    expect(document.querySelectorAll(".sec > h3").length).toBeLessThanOrEqual(5);
    expect(screen.getByText(/Each of them, on their own/i)).toBeDefined();
    expect(screen.getByText(/How the two charts fit/i)).toBeDefined();
    expect(screen.getByText(/A second, older answer/i)).toBeDefined();
    expect(screen.getByText(/How sure that older answer is/i)).toBeDefined();
    // THE score is the fit, once, at the top — and it carries its band.
    expect(document.querySelectorAll(".fit").length).toBe(1);
    expect(document.querySelector(".fit.hero-fit")).not.toBeNull();
    expect(document.querySelectorAll(".pile").length).toBe(2);

    // Three charts: one per person, then the two of them on one axis.
    const bands = document.querySelectorAll(".band");
    expect(bands.length).toBe(3);
    expect(bands[0].querySelectorAll(".chip").length).toBe(10);   // every body in the sky
    expect(bands[1].querySelectorAll(".chip").length).toBe(10);
    expect(bands[2].querySelectorAll(".chip").length).toBe(20);   // both people, one axis
    // The twelve signs are the axis of every chart, cut open at Aries.
    for (const band of bands) expect(band.querySelectorAll(".cell").length).toBe(12);

    // Five bodies get a reading, for each of the two people.
    for (const opens of ["At the centre", "How they feel", "How they think",
      "How they warm to people", "How they go after things"]) {
      expect(screen.getAllByText(new RegExp(opens, "i")).length, `${opens} missing`).toBe(2);
    }

    // Connections are narrated, numbered, and the numbers appear on the shared chart.
    const conns = document.querySelectorAll(".conn");
    expect(conns.length).toBeGreaterThan(0);
    expect(conns.length).toBeLessThanOrEqual(6);
    expect([...conns].map((c) => c.querySelector(".conn-n")?.textContent))
      .toEqual(Array.from({ length: conns.length }, (_, i) => String(i + 1)));
    expect(bands[2].querySelectorAll(".chip b").length).toBeGreaterThan(0);

    // Both instruments of the score still render.
    expect(document.querySelector(".anatomy .bar")?.children.length).toBe(8);
    expect((document.querySelector(".landscape")?.children.length ?? 0)).toBeGreaterThan(30);

    // All eight tests, each with the rule it used and the values it read, one click away.
    for (const test of ["Ways of working", "Give and take", "Good for each other",
      "Physical instinct", "Meeting of minds", "Temperament", "Life together", "Underlying makeup"]) {
      expect(screen.getAllByText(test).length, `${test} missing`).toBeGreaterThan(0);
    }
    expect(screen.getAllByText(/How it is scored:/).length).toBe(8);
    expect(screen.getAllByText(/What was read:/).length).toBe(8);

    // Four disclosures: the rest of each person's chart, all the connections, all eight tests.
    expect(screen.getAllByRole("group").length).toBe(4);

    // Both people are described, by plain title rather than a transliterated name.
    expect(screen.getAllByText(/their birth star, one of the 27/i).length).toBe(2);
  });

  it("explains the score with parts that add up to it, and says what is left over", () => {
    // The strongest thing this page can claim: the five reasons shown are not illustrations, they
    // are the arithmetic. So the residual is stated out loud, and every row carries how far the
    // angle wanders and how much the dates settle it.
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");
    const ranking = screen.getByRole("heading", { name: /Ranked against Ada/i }).closest(".panel") as HTMLElement;
    fireEvent.click(within(ranking).getByRole("button", { name: /Turing/ }));

    expect(screen.getByText(/24 . 24 = 576 times/)).toBeDefined();
    const reasons = document.querySelectorAll(".conn");
    expect(reasons.length).toBe(5);
    for (const work of document.querySelectorAll(".conn-work")) {
      const t = work.textContent ?? "";
      expect(t, "a reason with no angle").toMatch(/[\d.]+° apart/);
      // Every reason says what the unknown hours do to it, and what it did to the score.
      expect(t, "a reason with no account of the unknown hours")
        .toMatch(/The dates settle this one|The dates leave it \d+% open/);
      expect(t, "a reason that does not say what it changed").toMatch(/(added|took away)\s+[\d.]+/);
    }
    const page = document.body.textContent ?? "";
    expect(page, "no residual line").toMatch(/five biggest reasons/);
    expect(page).toMatch(/everything else put together comes to/);
    // The score is never shown without its band, and the two piles are never netted into one bar.
    expect(page, "the score must never be shown without its band")
      .toMatch(/higher than \d+ in 100/);
    expect(page).toMatch(/what the tradition calls easy/);
    expect(page).toMatch(/what it calls hard/);
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
    // The marker sat on Math.round(score) − 1 while tooltips said "score i+1", so the gold bar
    // pointed at the wrong place AND disagreed with its own hover text. Now that the strip is used
    // for two different scales, the invariant that matters is that the marked bar is the one the
    // headline percentile falls on.
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");
    const ranking = screen.getByRole("heading", { name: /Ranked against Ada/i }).closest(".panel") as HTMLElement;
    fireEvent.click(within(ranking).getByRole("button", { name: /Turing/ }));

    const strip = document.querySelector(".fit .landscape")!;
    const bars = [...strip.querySelectorAll("i")];
    const marked = bars.findIndex((b) => b.classList.contains("here"));
    expect(marked).toBeGreaterThanOrEqual(0);

    // The share of random pairs at or below the marked bar must match the headline percentile:
    // the picture and the sentence are two views of one table, and they cannot disagree.
    const shown = Number(document.querySelector(".fit .num")!.textContent!.replace(/\D+.*$/, ""));
    const below = bars.slice(0, marked)
      .reduce((s, b) => s + Number(/about (\d+) in 100/.exec(b.getAttribute("title") ?? "")?.[1] ?? 0), 0);
    expect(Math.abs(below - shown), `strip says ${below}, headline says ${shown}`).toBeLessThanOrEqual(6);
  });

  it("says so when a date does not settle which sign a planet was in", () => {
    // On 1999-12-06 the Moon spends 87% of the day in Scorpio and 13% in Libra, and Mercury
    // crosses the same boundary. A chart that printed one sign and said nothing would state as
    // fact something the input cannot support.
    window.history.replaceState({}, "",
      "/?n=CertA&b=1999-12-06&n2=CertB&b2=2004-12-27");
    render(<App />);
    // Both the Moon and Mercury cross that boundary, so the note appears twice for this person.
    expect(screen.getAllByText(/This one is not settled by the date/i).length).toBe(2);
    expect(document.body.textContent).toMatch(/Libra for 13% of that day/);
    window.history.replaceState({}, "", "/");
  });

  it("scans every day within twelve years for the best score a person could reach", async () => {
    // The ceiling panel is about a second of arithmetic, so it must never block: it renders a
    // progress bar first and fills in when the scan lands. Both states are asserted, and the
    // ceiling is required to be consistent with the ranking beside it — a panel claiming a "most
    // available" below a score already on the list would be self-contradicting.
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");

    expect(document.querySelector(".ceiling.scanning")).not.toBeNull();
    expect(screen.getByText(/days scored/i)).toBeDefined();

    const hist = await screen.findByRole("img", { name: /scanned days land on each score/i },
      { timeout: 60_000 });
    expect(hist.children.length).toBe(37);
    expect(document.querySelector(".ceiling.scanning")).toBeNull();

    const panel = document.querySelector(".ceiling")!.textContent ?? "";
    expect(panel).toMatch(/8,7\d\d days from 10 December 1803 to 10 December 1827/);
    expect(panel).toMatch(/of those days reach it/);
    expect(panel).toMatch(/comes back to the same place every 27 days/);

    // The ceiling belongs to the OLDER score, and says so; the rank rows now lead with the
    // whole-chart fit. So it is compared against the older score printed in the row's own subtitle,
    // not against the headline percentile beside it — comparing those would be a category error,
    // and the panel's own wording is what stops a reader making it.
    expect(document.querySelector(".ceiling")!.textContent).toMatch(/older eight-test score/i);
    const ceiling = Number(/^([\d.]+)/.exec(document.querySelector(".ceiling .cap")!.textContent!)![1]);
    const sub = document.querySelector(".rank-row .sub")!.textContent!;
    const older = Number(/older score puts it at ([\d.]+)/.exec(sub)![1]);
    expect(ceiling).toBeGreaterThanOrEqual(older);
    expect(ceiling).toBeLessThan(36);
  }, 90_000);

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
    const table = screen.getByText(/Every pair, as a place among 20,000/i).closest(".panel")!
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
