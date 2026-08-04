/**
 * App.tsx — ArtaMatch.
 *
 * Two sources of people, one engine, three views.
 *
 * Manual entries live only in this browser's localStorage and are never transmitted — there is no
 * ArtaMatch server to transmit them to. Public entries are ArtaQuest members whose birthdays are
 * already public on their own profiles. That distinction is shown on every row rather than buried in
 * a privacy page, because it is the thing a user most needs to know before typing someone else's
 * date of birth into a website.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  type Person, loadPeople, savePeople, newId, loadSelfId, saveSelfId, validatePerson,
} from "./data/people";
import { fetchPublicMembers, loadCached, messageUrl, type FetchResult } from "./data/artaquest";
import { rankAgainst, OPTIONAL_TESTS, type ScoreOptions } from "./engine/score";
import { affinity, affinityPercentile } from "./engine/affinity";
import type { KutaKey } from "./engine/kuta";
import { birthSpan } from "./engine/uncertainty";
import { scanWithin, type SearchResult } from "./engine/search";
import { starTitle } from "./engine/interpret";
import Report from "./ui/Report";
import { Avatar, Mark, Meter } from "./ui/bits";

type View = "ranking" | "matrix";

export default function App() {
  const [people, setPeople] = useState<Person[]>(() => loadPeople());
  const [selfId, setSelfId] = useState<string | null>(() => loadSelfId());
  const [view, setView] = useState<View>("ranking");
  const [pair, setPair] = useState<[string, string] | null>(null);
  // Tests the reader has chosen to leave out. Kept here rather than inside the report so the
  // ranking and the report always agree about what is being counted.
  const [excluded, setExcluded] = useState<KutaKey[]>([]);
  // The one modelling choice the page refuses to make for the reader — see affinity.ts. Kept here
  // beside the other, so the ranking, the grid and every reading always agree about it.
  const [opposite, setOpposite] = useState<"hard" | "easy">("hard");
  const options = useMemo<ScoreOptions>(() => ({ exclude: excluded, opposite }), [excluded, opposite]);

  const [name, setName] = useState("");
  const [birthday, setBirthday] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<FetchResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  useEffect(() => { savePeople(people.filter((p) => p.source === "manual")); }, [people]);
  useEffect(() => { saveSelfId(selfId); }, [selfId]);

  // Never sit on a populated list with nobody selected — that shows "pick who you are" where a
  // ranking could be. Happens on a seeded first visit, and after deleting whoever was selected.
  useEffect(() => {
    if (people.length > 0 && !people.some((p) => p.id === selfId)) setSelfId(people[0].id);
  }, [selfId, people]);

  // A shared link carries one or two people in the query string, so a reading can be passed
  // around without anybody uploading anything. ?n=&b= adds one person; ?n2=&b2= adds a second and
  // opens the pair's reading directly.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const incoming: Person[] = [];
    for (const [nk, bk] of [["n", "b"], ["n2", "b2"]] as const) {
      const n = q.get(nk), b = q.get(bk);
      if (n && b && !validatePerson(n, b)) {
        incoming.push({ id: newId(), name: n, birthday: b, source: "manual", addedAt: Date.now() });
      }
    }
    if (incoming.length === 0) return;
    setPeople((prev) => {
      const merged = [...prev];
      const resolved: string[] = [];
      for (const person of incoming) {
        const existing = merged.find((p) => p.name === person.name && p.birthday === person.birthday);
        if (existing) { resolved.push(existing.id); continue; }
        merged.push(person); resolved.push(person.id);
      }
      if (resolved.length === 2) setPair([resolved[0], resolved[1]]);
      return merged;
    });
    window.history.replaceState({}, "", window.location.pathname);
  }, []);

  // Show any still-fresh cached import immediately, so a reload does not look empty.
  useEffect(() => {
    const cached = loadCached();
    if (cached) {
      setImportResult(cached);
      setPeople((prev) => mergePublic(prev, cached.people));
    }
  }, []);

  const addPerson = useCallback(() => {
    const err = validatePerson(name, birthday);
    if (err) { setFormError(err); return; }
    setFormError(null);
    const person: Person = {
      id: newId(), name: name.trim(), birthday: birthday.trim(),
      source: "manual", addedAt: Date.now(),
    };
    setPeople((prev) => [...prev, person]);
    if (!selfId) setSelfId(person.id);
    setName(""); setBirthday("");
  }, [name, birthday, selfId]);

  const removePerson = useCallback((id: string) => {
    setPeople((prev) => prev.filter((p) => p.id !== id));
    setSelfId((cur) => (cur === id ? null : cur));
    setPair((cur) => (cur && (cur[0] === id || cur[1] === id) ? null : cur));
  }, []);

  const runImport = useCallback(async () => {
    setImporting(true); setImportError(null);
    try {
      const result = await fetchPublicMembers();
      setImportResult(result);
      setPeople((prev) => mergePublic(prev, result.people));
    } catch (e) {
      setImportError(
        e instanceof Error
          ? `Could not reach artaquest.com (${e.message}). Manual entries still work offline.`
          : "Could not reach artaquest.com. Manual entries still work offline.",
      );
    } finally {
      setImporting(false);
    }
  }, []);

  const self = people.find((p) => p.id === selfId) ?? null;
  const ranked = useMemo(
    () => (self ? rankAgainst(self, people, options) : []),
    [self, people, options],
  );

  // A report whose people have gone (deleted, or replaced by an import) must close rather than
  // linger unresolved and spontaneously reopen when a later import restores the id.
  useEffect(() => {
    if (pair && (!people.some((p) => p.id === pair[0]) || !people.some((p) => p.id === pair[1]))) {
      setPair(null);
    }
  }, [pair, people]);

  const pairPeople = useMemo(() => {
    if (!pair) return null;
    const a = people.find((p) => p.id === pair[0]);
    const b = people.find((p) => p.id === pair[1]);
    return a && b ? ([a, b] as const) : null;
  }, [pair, people]);

  return (
    <div className="wrap">
      <header className="masthead">
        <Mark size={40} />
        <div style={{ flex: "1 1 260px" }}>
          <h1>ArtaMatch</h1>
          <p className="tag">
            Put in two dates of birth. You get each person's chart read on its own, then the two
            laid over each other to see where they touch, then one score out of 36 — all in plain
            words, and all with an honest account of what a date alone cannot tell you.
          </p>
        </div>
      </header>

      <main className="cols">
        <div>
          <section className="panel">
            <h2>Add someone</h2>
            <p className="panel-note">
              Kept in this browser and nowhere else. Nothing you type here is sent anywhere, because
              there is no server to send it to.
            </p>
            <div className="field">
              <label htmlFor="nm">Name</label>
              <input id="nm" type="text" value={name} autoComplete="off"
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addPerson()} />
            </div>
            <div className="field">
              <label htmlFor="bd">Date of birth</label>
              <input id="bd" type="date" value={birthday} min="1800-01-01" max="2100-12-31"
                onChange={(e) => setBirthday(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addPerson()} />
            </div>
            {formError && <p className="error" role="alert">{formError}</p>}
            <button onClick={addPerson}>Add to my list</button>
          </section>

          <section className="panel">
            <h2>Public accounts</h2>
            <p className="panel-note">
              People on ArtaQuest who have already made their birthday public on their own profile.
              You can message them from here.
            </p>
            <div className="row">
              <button className="ghost" onClick={runImport} disabled={importing}>
                {importing ? "Loading…" : "Load ArtaQuest members"}
              </button>
              {importResult && (
                <span className="pill aq">{importResult.people.length} loaded</span>
              )}
            </div>
            {importError && <p className="error" role="alert">{importError}</p>}
            {importResult && importResult.skipped.length > 0 && (
              <p className="panel-note" style={{ marginTop: "0.6rem" }}>
                {importResult.skipped.length} member{importResult.skipped.length === 1 ? "" : "s"} skipped:{" "}
                {importResult.skipped.map((s) => `${s.name} (${s.reason})`).join("; ")}.
              </p>
            )}
          </section>

          <section className="panel">
            <h2>What gets counted</h2>
            <p className="panel-note">
              Two choices this page will not make for you.
            </p>
            <label className="opt" style={{ marginBottom: "0.8rem" }}>
              <input type="checkbox" checked={opposite === "easy"}
                onChange={(e) => setOpposite(e.target.checked ? "easy" : "hard")} />
              <span>
                <b>Read two bodies sitting right across from each other as attraction</b>
                This is the one place the old sources genuinely disagree, and the only choice on this
                page that changes much: the classical texts call being directly opposite hard, while
                writers on couples very often read it as two people completing each other. Leave it
                off for the older reading. Turning it on reorders a list of people noticeably —
                measured at 0.72 out of 1 rank agreement, where every other choice we made scores
                above 0.88.
              </span>
            </label>
            {OPTIONAL_TESTS.map((t) => (
              <label className="opt" key={t.key}>
                <input type="checkbox" checked={!excluded.includes(t.key)}
                  onChange={(e) => setExcluded((prev) =>
                    e.target.checked ? prev.filter((k) => k !== t.key) : [...prev, t.key])} />
                <span>
                  <b>Count {t.label}</b>
                  {t.why}
                </span>
              </label>
            ))}
          </section>

          <section className="panel">
            <h2>Everyone ({people.length})</h2>
            <p className="panel-note">
              {self ? <>Everyone is being compared against <strong>{self.name}</strong>. Tap a
                different name to switch.</>
                : "Tap whoever you want to compare everyone else against."}
            </p>
            {people.length === 0 && <p className="empty">Nobody here yet. Add a date of birth above.</p>}
            {people.map((p) => (
              <PersonRow key={p.id} person={p} isSelf={p.id === selfId}
                onPick={() => setSelfId(p.id)} onRemove={() => removePerson(p.id)} />
            ))}
          </section>
        </div>

        <div>
          {pairPeople ? (
            <Report a={pairPeople[0]} b={pairPeople[1]} options={options} onClose={() => setPair(null)} />
          ) : (
            <>
              {/* Toggle buttons, not an ARIA tabs pattern. These carried role="tab" and
                  aria-selected without aria-controls, tabpanels, roving tabindex or arrow-key
                  handling — announcing "tab" to a screen reader promises keyboard behaviour that
                  was not there. aria-pressed says exactly what these are and needs nothing beyond
                  a native button. */}
              <div className="tabs" role="group" aria-label="Choose a view">
                <button aria-pressed={view === "ranking"}
                  className={view === "ranking" ? "on" : ""} onClick={() => setView("ranking")}>
                  Ranking
                </button>
                <button aria-pressed={view === "matrix"}
                  className={view === "matrix" ? "on" : ""} onClick={() => setView("matrix")}>
                  Everyone vs everyone
                </button>
              </div>

              {view === "ranking"
                ? <Ranking self={self} ranked={ranked} options={options}
                    onOpen={(id) => self && setPair([self.id, id])} />
                : <Matrix people={people} options={options} onOpen={(x, y) => setPair([x, y])} />}
            </>
          )}
        </div>
      </main>

      <footer className="footer">
        <p>
          <strong style={{ color: "var(--muted)" }}>Where the numbers come from.</strong> The
          positions of the Sun, Moon and planets are worked out here in your browser, and checked
          against the Swiss Ephemeris — the reference astronomers and astrologers both use — at
          nearly two thousand dates between 1900 and 2100. The Moon agrees to within about a
          fortieth of a degree.
        </p>
        <p>
          <strong style={{ color: "var(--muted)" }}>Why the time of day keeps coming up.</strong> The
          Moon travels about 13 degrees a day, and most of this tradition is built on exactly where
          it was. Not knowing the hour typically moves it about 6.6 degrees either way, up to 7.7 at
          the Moon’s fastest — hundreds of times bigger than any error in the maths. So nothing here
          is worked out once. Every reading is made 576 times, once for each combination of the two
          unknown birth hours, and what you are shown is the average and how far it moved.
        </p>
        <p>
          <strong style={{ color: "var(--muted)" }}>And what this is.</strong> There is no known way
          any of this could actually work. It is an old and carefully worked-out way of talking about
          people, not a science, and nothing here predicts anything about anybody. Read it the way
          you would read a character sketch someone wrote about you — interesting where it lands,
          harmless where it does not.{" "}
          <a href="https://github.com/ArtaQuest/artamatch" target="_blank" rel="noreferrer">
            All the workings are open
          </a>.
        </p>
      </footer>
    </div>
  );
}

/** Trim a trailing .0 — half points are real, "22.0" reads like a rounding artefact. */
export const fmtScore = (n: number) => (n % 1 === 0 ? String(n) : n.toFixed(1));

/** 1999-12-06 → 6 December 1999. Reading a date should not require parsing a format. */
const MONTHS = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];
export function formatBirthday(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return iso;
  return `${+m[3]} ${MONTHS[+m[2] - 1]} ${m[1]}`;
}

/** Public rows are replaced wholesale on each import; manual rows are never touched. */
function mergePublic(prev: Person[], incoming: Person[]): Person[] {
  const manual = prev.filter((p) => p.source === "manual");
  return [...manual, ...incoming];
}

function PersonRow({ person, isSelf, onPick, onRemove }: {
  person: Person; isSelf: boolean; onPick: () => void; onRemove: () => void;
}) {
  const span = useMemo(() => birthSpan(person.birthday), [person.birthday]);
  const moon = span?.likeliest;
  return (
    <div className={`person ${isSelf ? "is-self" : ""}`}>
      <Avatar person={person} />
      {/* Everything textual lives INSIDE the flexible column, so the name always gets the row's
          width. An earlier layout put the badges beside this column as flex siblings; on rows with
          two badges the name column collapsed to a few characters and the date wrapped word by
          word. The remove button is the only other sibling — a fixed, small one. */}
      {/* The selection driving the whole ranking was conveyed by a gold border alone. */}
      <button className="who link" onClick={onPick} aria-pressed={isSelf}
        style={{ textAlign: "left" }}>
        <span className="nm">
          {person.name}
          {person.source === "artaquest" && <span className="pill aq">ArtaQuest</span>}
        </span>
        <span className="bd">
          {formatBirthday(person.birthday)}
          {moon && <> · {starTitle(moon.nakshatra.index).toLowerCase()}</>}
          {span && !span.stable && (
            <span className="tm"
              title="The Moon changed birth star or sign during this day, so the time of day would change the result">
              {" "}· time matters
            </span>
          )}
        </span>
      </button>
      {person.source === "manual" && (
        <button className="link rm" onClick={onRemove} aria-label={`Remove ${person.name}`}>×</button>
      )}
    </div>
  );
}

function Ranking({ self, ranked, options, onOpen }: {
  self: Person | null;
  ranked: ReturnType<typeof rankAgainst<Person>>;
  options: ScoreOptions;
  onOpen: (id: string) => void;
}) {
  if (!self) {
    return <div className="panel"><p className="empty">Pick who you are from the list to see a ranking.</p></div>;
  }
  if (ranked.length === 0) {
    return <div className="panel"><p className="empty">Add at least one more person to compare against {self.name}.</p></div>;
  }
  const best = ranked.reduce<{ name: string; score: number } | null>((b, r) =>
    !b || r.match.distribution.expected > b.score
      ? { name: r.other.name, score: r.match.distribution.expected } : b, null);

  return (
    <div className="panel">
      <h2>Ranked against {self.name}</h2>
      <p className="panel-note">
        Ranked by how the two whole charts fit, averaged over all 576 combinations of the two
        unknown birth hours. <strong style={{ color: "var(--yang)" }}>Where two ranges overlap,
        those two cannot be told apart</strong> — and measured over 20,000 random pairs, the unknown
        birth times cost about as much as the whole difference between one couple and another, so
        that happens often. It is a limit of the input, not of the arithmetic. Tap a row for the
        full reading.
      </p>
      {/* The ceiling is computed on the OLDER score, so what it compares against must be the older
          score too — the best one on this list, which is not necessarily the top row, because the
          list is ordered by the whole-chart fit and the two disagree. Passing the row's raw fit
          here once printed "the best you have is 0.1" against a scale that runs to 36. */}
      <Ceiling self={self} options={options} best={best} />
      <div className="rank">
        {ranked.map((r, i) => {
          const m = r.match;
          const msg = messageUrl(r.other);
          return (
            <button className="rank-row" key={r.other.id} onClick={() => onOpen(r.other.id)}>
              <span className="pos">{i + 1}</span>
              <Avatar person={r.other} />
              <span className="body">
                <span className="nm">
                  {r.other.name}
                  {msg && <span className="pill aq" style={{ marginLeft: "0.4rem" }}>can message</span>}
                </span>
                <span className="sub">
                  higher than {r.percentile} in 100 random pairs · could be{" "}
                  {affinityPercentile(r.aff.spread.lo)}–{affinityPercentile(r.aff.spread.hi)}{" "}
                  depending on the hour · the older score puts it at{" "}
                  {fmtScore(m.distribution.expected)} of {m.maxScore}
                </span>
                <Meter value={r.percentile} max={100} gold={r.percentile >= 60} />
              </span>
              <span className={`sc tone-${r.percentile >= 75 ? "high" : r.percentile >= 40 ? "mid" : "low"}`}>
                {r.percentile}
                <small>in 100</small>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** How many years either side the ceiling search looks. Twelve is the user's call and it is a
 *  reasonable one: it is about the widest age gap most people would actually consider, and it is
 *  wide enough that the Moon's 27-day cycle repeats inside it hundreds of times. */
const CEILING_YEARS = 12;

/** Scans are pure and deterministic, so a result is worth keeping for as long as the page lives —
 *  flipping between two people should not re-earn a second of arithmetic each time. */
const CEILING_CACHE = new Map<string, SearchResult>();

/**
 * The ceiling: the best score this person could reach against ANY birth date within twelve years
 * of their own, every one of the ~8,767 days scored one at a time.
 *
 * Two things make this worth a second of a phone's time. It gives a score a second anchor — not
 * just "higher than 50 in 100 random pairs" but "out of a possible 29.5, for you specifically".
 * And it kills a superstition the rest of the page would otherwise feed: the top score is not held
 * by one person born on one magic day. The eight tests read the Moon, the Moon comes back to the
 * same birth star every 27.3 days, so scores of dates reach the identical ceiling. That count is
 * printed, and it is the most honest sentence on the panel.
 *
 * The scan is a generator driven in slices of about 20 ms, so the page keeps scrolling while it
 * runs, and it is abandoned the moment the selected person or the counted tests change.
 */
function Ceiling({ self, options, best }: {
  self: Person; options: ScoreOptions; best: { name: string; score: number } | null;
}) {
  const key = `${self.birthday}|${(options.exclude ?? []).join(",")}`;
  const [result, setResult] = useState<SearchResult | null>(() => CEILING_CACHE.get(key) ?? null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const cached = CEILING_CACHE.get(key);
    if (cached) { setResult(cached); setProgress(1); return; }
    setResult(null); setProgress(0);
    const gen = scanWithin(self.birthday, CEILING_YEARS, options);
    let stopped = false;
    const tick = () => {
      if (stopped) return;
      const started = performance.now();
      let step = gen.next();
      // One slice per frame, not one day per frame: a day costs a tenth of a millisecond, so
      // yielding after each would spend the whole budget on scheduling.
      while (!step.done && performance.now() - started < 20) step = gen.next();
      if (step.done) {
        if (step.value) { CEILING_CACHE.set(key, step.value); setResult(step.value); }
        setProgress(1);
      } else {
        setProgress(step.value);
        setTimeout(tick, 0);
      }
    };
    const handle = setTimeout(tick, 0);
    return () => { stopped = true; clearTimeout(handle); };
  }, [key, self.birthday, options]);

  if (!result) {
    return (
      <div className="ceiling scanning">
        <span className="lbl">
          Working out the best score {self.name} could reach against anyone born within{" "}
          {CEILING_YEARS} years — {Math.round(progress * 8767).toLocaleString()} days scored
        </span>
        <Meter value={progress} max={1} gold />
      </div>
    );
  }

  const share = Math.round(result.days / result.atCeiling);
  return (
    <div className="ceiling">
      <div className="top">
        <span className="cap">{fmtScore(result.ceiling)}<small>the most available</small></span>
        <p className="txt">
          <strong>Of the older eight-test score</strong>, that is the highest {self.name} can reach
          against <strong>any</strong> date of birth
          within {CEILING_YEARS} years of their own — every one of the{" "}
          {result.days.toLocaleString()} days from {formatBirthday(result.from)} to{" "}
          {formatBirthday(result.to)}, scored one at a time. The worst available is{" "}
          {fmtScore(result.floor)} and the middle of the range is {fmtScore(result.median)}.
        </p>
      </div>
      <Histogram result={result} bestHere={best?.score ?? null} />
      <p className="legend-note">
        <span className="key-a">the most available</span>
        {best && <span className="key-b">your best here</span>}
        <span className="dim">
          each bar is one score, as tall as the number of the {result.days.toLocaleString()} days
          that land on it
        </span>
      </p>
      <p className="txt dim">
        <strong>{result.atCeiling.toLocaleString()} of those days reach it</strong> — about one in
        every {share}. The eight tests read the Moon, and the Moon comes back to the same place
        every 27 days, so the top score belongs to a position in the sky rather than to a person.
        The nearest dates that reach it are{" "}
        {result.best.map((b) => formatBirthday(b.iso)).join(", ")}.
        {best && (
          <> The best <em>this</em> score can find on your list is {best.name} at{" "}
            {fmtScore(best.score)} — which is not the top row above, because that list is ordered by
            the whole-chart fit and the two readings disagree.</>
        )}
      </p>
    </div>
  );
}

/** The ~8,767 scanned days, one bar per whole score, with the ceiling and the best on the list
 *  marked. The same picture as the report's landscape strip, but of what is AVAILABLE to one
 *  person rather than what is common across everybody. */
function Histogram({ result, bestHere }: { result: SearchResult; bestHere: number | null }) {
  const peak = Math.max(...result.histogram, 1);
  const top = Math.round(result.ceiling);
  const here = bestHere === null ? -1 : Math.round(bestHere);
  return (
    <span className="hist" role="img"
      aria-label={`How many of the ${result.days} scanned days land on each score, from ` +
        `${fmtScore(result.floor)} to ${fmtScore(result.ceiling)}`}>
      {result.histogram.map((n, i) => (
        // A marked bar keeps its own floor. Only 71 of 8,767 days reach the ceiling, so drawn to
        // scale the gold marker is a two-pixel sliver — the one bar the reader is looking for,
        // and the hardest to see.
        <i key={i} className={i === top ? "top" : i === here ? "here" : ""}
          style={{ height: `${i === top || i === here ? Math.max(26, (n / peak) * 100)
            : n > 0 ? Math.max(6, (n / peak) * 100) : 2}%` }}
          title={`${n.toLocaleString()} of the ${result.days.toLocaleString()} days score ${i}` +
            (i === top ? " — the most available" : i === here ? " — your best on this list" : "")} />
      ))}
    </span>
  );
}

function Matrix({ people, options, onOpen }: { people: Person[]; options: ScoreOptions; onOpen: (a: string, b: string) => void }) {
  const cells = useMemo(() => {
    const m = new Map<string, number>();
    for (let i = 0; i < people.length; i++) {
      for (let j = i + 1; j < people.length; j++) {
        const r = affinity(people[i].birthday, people[j].birthday, { ...options, verify: false });
        if (r) {
          const p = affinityPercentile(r.net);
          m.set(`${people[i].id}|${people[j].id}`, p);
          m.set(`${people[j].id}|${people[i].id}`, p);
        }
      }
    }
    return m;
  }, [people, options]);

  if (people.length < 2) {
    return <div className="panel"><p className="empty">Add at least two people to see the grid.</p></div>;
  }

  return (
    <div className="panel">
      <h2>Everyone against everyone</h2>
      <p className="panel-note">
Every pair, as a place among 20,000 randomly paired dates. The grid is symmetric by construction,
        so it reads the same across as it does down — and none of these numbers should be read
        without the range behind it, which the full reading shows. Tap any cell.
      </p>
      <div className="scroll-x">
        <table className="data">
          <thead>
            <tr>
              <th />
              {people.map((p) => (
                <th key={p.id} scope="col" title={p.name}>{p.name.slice(0, 8)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {people.map((row) => (
              <tr key={row.id}>
                <th scope="row" title={row.name}>{row.name.slice(0, 12)}</th>
                {people.map((col) => {
                  if (row.id === col.id) return <td key={col.id} className="matrix-cell self">—</td>;
                  const v = cells.get(`${row.id}|${col.id}`);
                  if (v === undefined) return <td key={col.id} className="matrix-cell self">·</td>;
                  // The same score must wear the same colour here as it does in the report —
                  // including against the right distribution when a test is switched off.
                  const tone = v >= 75 ? "high" : v >= 40 ? "mid" : "low";
                  return (
                    <td key={col.id} className="matrix-cell">
                      <button className="link" onClick={() => onOpen(row.id, col.id)}
                        aria-label={`${row.name} and ${col.name} — higher than ${v} in 100 random pairs`}
                        title={`${row.name} & ${col.name} — higher than ${v} in 100 random pairs`}>
                        <span className={`tone-${tone}`}>{v}</span>
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
