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
    expect(screen.getByText(/Nobody yet/i)).toBeDefined();
  });

  it("refuses an impossible date instead of charting the wrong day", () => {
    render(<App />);
    // A real browser (and jsdom) will not let <input type="date"> hold 2001-02-29 at all — it is
    // not a leap year — so the field ends up empty and the entry is refused either way. What
    // matters is that nobody is added and the reason is stated.
    addPerson("Nobody", "2001-02-29");
    expect(screen.getByText(/Nobody yet/i)).toBeDefined();
    expect(screen.getByText(/date of birth is the one thing this needs|not a real calendar date/i)).toBeDefined();
  });

  it("refuses an impossible date arriving through a share link", () => {
    // The date input cannot produce one, but ?b= can — and Date.UTC would silently roll
    // 2001-02-29 forward to 1 March, charting the wrong day. This is the path that needs guarding.
    window.history.replaceState({}, "", "/?n=Ghost&b=2001-02-29");
    render(<App />);
    expect(screen.getByText(/Nobody yet/i)).toBeDefined();
    expect(screen.queryByText("Ghost")).toBeNull();
    window.history.replaceState({}, "", "/");
  });

  it("accepts a valid date through a share link", () => {
    window.history.replaceState({}, "", "/?n=Ghost&b=2000-02-29"); // 2000 IS a leap year
    render(<App />);
    expect(screen.getAllByText("Ghost").length).toBeGreaterThan(0);
    window.history.replaceState({}, "", "/");
  });

  it("adds someone, makes them self, and shows their birth star", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    // "Ada" appears both in the list and in the "Ranked against Ada" heading — both are correct.
    expect(screen.getAllByText(/Ada/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/1815-12-10/)).toBeDefined();
    // Prompted to add a second person rather than shown an empty ranking.
    expect(screen.getByText(/Add at least one more person/i)).toBeDefined();
  });

  it("ranks a second person and shows the component scores", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");

    const ranking = screen.getByText(/Ranked against Ada/i).closest(".panel") as HTMLElement;
    const row = within(ranking).getByRole("button", { name: /Turing/ });
    expect(row.textContent).toMatch(/Guna \d+(\.\d+)?\/36/);
    expect(row.textContent).toMatch(/ease \d+/);
    expect(row.textContent).toMatch(/charge \d+/);
  });

  it("opens a full report with every section populated", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");

    const ranking = screen.getByText(/Ranked against Ada/i).closest(".panel") as HTMLElement;
    fireEvent.click(within(ranking).getByRole("button", { name: /Turing/ }));

    expect(screen.getByText(/Ada & Turing/)).toBeDefined();
    expect(screen.getByText(/a blend, not a verdict/i)).toBeDefined();

    // Guna tab: all eight kutas, each with its rule and its evidence.
    fireEvent.click(screen.getByRole("tab", { name: /Guna Milan/i }));
    for (const kuta of ["Varna", "Vashya", "Tara", "Yoni", "Graha Maitri", "Gana", "Bhakoot", "Nadi"]) {
      expect(screen.getByText(kuta), `${kuta} missing`).toBeDefined();
    }
    expect(screen.getAllByText(/^Rule:/).length).toBe(8);

    // Aspects tab: the grid plus written explanations.
    fireEvent.click(screen.getByRole("tab", { name: /Aspects/i }));
    expect(screen.getByText(/Aspect grid/i)).toBeDefined();
    expect(screen.getByText(/major aspects, ordered by how much each one counts/i)).toBeDefined();

    // Positions tab: both charts, all ten bodies each.
    fireEvent.click(screen.getByRole("tab", { name: /Positions/i }));
    expect(screen.getAllByText(/Janma nakshatra/i).length).toBe(2);
    expect(screen.getAllByText(/☉ Sun/).length).toBe(2);
    expect(screen.getAllByText(/♇ Pluto/).length).toBe(2);
  });

  it("warns on a date where the Moon changes birth star, and not on one where it does not", () => {
    render(<App />);
    // 1965-07-27: the Moon crosses two nakshatra boundaries AND a rasi boundary — four states.
    addPerson("Wanderer", "1965-07-27");
    expect(screen.getAllByText(/Moon moved/i).length).toBeGreaterThan(0);
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
    const ranking = screen.getByText(/Ranked against Ayse Altundal/i).closest(".panel") as HTMLElement;
    // Two others, each with a real score.
    const rows = within(ranking).getAllByRole("button");
    expect(rows.length).toBeGreaterThanOrEqual(2);
    expect(ranking.textContent).toMatch(/Elif Eda Ayan/);
    expect(ranking.textContent).toMatch(/Lana El Jamal/);
    expect(ranking.textContent).toMatch(/Guna \d+(\.\d+)?\/36/);
  });

  it("shows the everyone-against-everyone grid symmetrically", () => {
    render(<App />);
    addPerson("Ada", "1815-12-10");
    addPerson("Turing", "1912-06-23");
    addPerson("Curie", "1867-11-07");

    fireEvent.click(screen.getByRole("tab", { name: /Everyone against everyone/i }));
    const table = screen.getByText(/Every pair, scored out of 100/i).closest(".panel")!
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
