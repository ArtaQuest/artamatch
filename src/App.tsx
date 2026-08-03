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
import { matchPair, rankAgainst, overallBand } from "./engine/score";
import { birthSpan } from "./engine/uncertainty";
import { SIGNS } from "./engine/ephemeris";
import Report from "./ui/Report";
import { Avatar, Mark, Meter } from "./ui/bits";

type View = "ranking" | "matrix";

export default function App() {
  const [people, setPeople] = useState<Person[]>(() => loadPeople());
  const [selfId, setSelfId] = useState<string | null>(() => loadSelfId());
  const [view, setView] = useState<View>("ranking");
  const [pair, setPair] = useState<[string, string] | null>(null);

  const [name, setName] = useState("");
  const [birthday, setBirthday] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<FetchResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  useEffect(() => { savePeople(people.filter((p) => p.source === "manual")); }, [people]);
  useEffect(() => { saveSelfId(selfId); }, [selfId]);

  // A shared link carries one person in the query string, so two people can compare without either
  // of them uploading anything.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const n = q.get("n"), b = q.get("b");
    if (n && b && !validatePerson(n, b)) {
      setPeople((prev) =>
        prev.some((p) => p.name === n && p.birthday === b)
          ? prev
          : [...prev, { id: newId(), name: n, birthday: b, source: "manual", addedAt: Date.now() }]);
      window.history.replaceState({}, "", window.location.pathname);
    }
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
    () => (self ? rankAgainst(self, people) : []),
    [self, people],
  );

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
            Sidereal compatibility from dates of birth alone — Ashtakoota Guna Milan and a full
            synastry report, with every point traced to the rule that produced it.
          </p>
        </div>
      </header>

      <div className="cols">
        <div>
          <section className="panel">
            <h2>Add someone</h2>
            <p className="panel-note">
              Stored in this browser only. Nothing you type here is sent anywhere.
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
            {formError && <p className="error">{formError}</p>}
            <button onClick={addPerson}>Add to my list</button>
          </section>

          <section className="panel">
            <h2>Public accounts</h2>
            <p className="panel-note">
              ArtaQuest members whose birthday is already public on their own profile.
            </p>
            <div className="row">
              <button className="ghost" onClick={runImport} disabled={importing}>
                {importing ? "Loading…" : "Load ArtaQuest members"}
              </button>
              {importResult && (
                <span className="pill aq">{importResult.people.length} loaded</span>
              )}
            </div>
            {importError && <p className="error">{importError}</p>}
            {importResult && importResult.skipped.length > 0 && (
              <p className="panel-note" style={{ marginTop: "0.6rem" }}>
                {importResult.skipped.length} member{importResult.skipped.length === 1 ? "" : "s"} skipped:{" "}
                {importResult.skipped.map((s) => `${s.name} (${s.reason})`).join("; ")}.
              </p>
            )}
          </section>

          <section className="panel">
            <h2>Everyone ({people.length})</h2>
            <p className="panel-note">
              {self ? <>Ranking against <strong>{self.name}</strong>. Tap another row to switch.</>
                : "Tap someone to rank everyone else against them."}
            </p>
            {people.length === 0 && <p className="empty">Nobody yet. Add a date of birth above.</p>}
            {people.map((p) => (
              <PersonRow key={p.id} person={p} isSelf={p.id === selfId}
                onPick={() => setSelfId(p.id)} onRemove={() => removePerson(p.id)} />
            ))}
          </section>
        </div>

        <div>
          {pairPeople ? (
            <Report a={pairPeople[0]} b={pairPeople[1]} onClose={() => setPair(null)} />
          ) : (
            <>
              <div className="tabs" role="tablist">
                <button role="tab" aria-selected={view === "ranking"}
                  className={view === "ranking" ? "on" : ""} onClick={() => setView("ranking")}>
                  Ranking
                </button>
                <button role="tab" aria-selected={view === "matrix"}
                  className={view === "matrix" ? "on" : ""} onClick={() => setView("matrix")}>
                  Everyone against everyone
                </button>
              </div>

              {view === "ranking"
                ? <Ranking self={self} ranked={ranked} onOpen={(id) => self && setPair([self.id, id])} />
                : <Matrix people={people} onOpen={(x, y) => setPair([x, y])} />}
            </>
          )}
        </div>
      </div>

      <footer className="footer">
        <p>
          Sidereal (Vedic) positions, Lahiri ayanamsa. The built-in ephemeris is verified against the
          Swiss Ephemeris across 1900–2100: the Moon agrees to <code>1.4′</code>, the Sun to{" "}
          <code>0.7′</code>. The unknown birth time moves the Moon by up to <code>±6.6°</code> —
          roughly 290× larger — which is why every Moon-dependent result here carries a range rather
          than a single confident number.
        </p>
        <p>
          Astrology is a shared symbolic language with no established causal mechanism. Nothing here
          predicts anything about anybody. Read it as a way of describing patterns, not as a verdict
          on a person.{" "}
          <a href="https://github.com/ArtaQuest/artamatch" target="_blank" rel="noreferrer">Source</a>.
        </p>
      </footer>
    </div>
  );
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
      <button className="who link" onClick={onPick} style={{ textAlign: "left" }}>
        <span className="nm">{person.name}</span>
        <span className="bd">
          {person.birthday}
          {moon && <> · {moon.nakshatra.name} · {SIGNS[moon.rasi]}</>}
          {span && !span.stable && " ·"}
        </span>
      </button>
      {span && !span.stable && <span className="pill warn" title="The Moon changed birth star during this day, so results carry a range">Moon moved</span>}
      {person.source === "artaquest" && <span className="pill aq">ArtaQuest</span>}
      {person.source === "manual" && (
        <button className="link" onClick={onRemove} aria-label={`Remove ${person.name}`}
          style={{ color: "var(--muted)" }}>×</button>
      )}
    </div>
  );
}

function Ranking({ self, ranked, onOpen }: {
  self: Person | null;
  ranked: ReturnType<typeof rankAgainst<Person>>;
  onOpen: (id: string) => void;
}) {
  if (!self) {
    return <div className="panel"><p className="empty">Pick who you are from the list to see a ranking.</p></div>;
  }
  if (ranked.length === 0) {
    return <div className="panel"><p className="empty">Add at least one more person to compare against {self.name}.</p></div>;
  }
  return (
    <div className="panel">
      <h2>Ranked against {self.name}</h2>
      <p className="panel-note">
        Scores are symmetric, so this list agrees with everyone else's about any shared pair.
        Tap a row for the full report.
      </p>
      <div className="rank">
        {ranked.map((r, i) => {
          const band = overallBand(r.overall);
          const unstable = !r.match.spanA.stable || !r.match.spanB.stable;
          const msg = messageUrl(r.other);
          return (
            <button className="rank-row" key={r.other.id} onClick={() => onOpen(r.other.id)}>
              <span className="pos">{i + 1}</span>
              <Avatar person={r.other} />
              <span>
                <span className="nm">{r.other.name}</span>
                <span className="sub">
                  Guna {r.match.components.guna.total.toFixed(1)}/36 ·
                  ease {r.match.components.easeScore.toFixed(0)} ·
                  charge {r.match.components.chargeScore.toFixed(0)}
                  {unstable && " · Moon moved"}
                </span>
                <Meter value={r.overall} />
              </span>
              {msg
                ? <a href={msg} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}
                    className="pill aq">Message</a>
                : <span />}
              <span className={`sc tone-${band.tone}`}>{r.overall.toFixed(0)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Matrix({ people, onOpen }: { people: Person[]; onOpen: (a: string, b: string) => void }) {
  const cells = useMemo(() => {
    const m = new Map<string, number>();
    for (let i = 0; i < people.length; i++) {
      for (let j = i + 1; j < people.length; j++) {
        const r = matchPair(people[i].birthday, people[j].birthday);
        if (r) {
          m.set(`${people[i].id}|${people[j].id}`, r.overall);
          m.set(`${people[j].id}|${people[i].id}`, r.overall);
        }
      }
    }
    return m;
  }, [people]);

  if (people.length < 2) {
    return <div className="panel"><p className="empty">Add at least two people to see the grid.</p></div>;
  }

  return (
    <div className="panel">
      <h2>Everyone against everyone</h2>
      <p className="panel-note">
        Every pair, scored out of 100. The grid is symmetric by construction. Tap a cell for the report.
      </p>
      <div className="scroll-x">
        <table className="data">
          <thead>
            <tr>
              <th />
              {people.map((p) => <th key={p.id} title={p.name}>{p.name.slice(0, 8)}</th>)}
            </tr>
          </thead>
          <tbody>
            {people.map((row) => (
              <tr key={row.id}>
                <th title={row.name}>{row.name.slice(0, 12)}</th>
                {people.map((col) => {
                  if (row.id === col.id) return <td key={col.id} className="matrix-cell self">—</td>;
                  const v = cells.get(`${row.id}|${col.id}`);
                  if (v === undefined) return <td key={col.id} className="matrix-cell self">·</td>;
                  const band = overallBand(v);
                  return (
                    <td key={col.id} className="matrix-cell">
                      <button className="link" onClick={() => onOpen(row.id, col.id)}
                        title={`${row.name} & ${col.name}`}>
                        <span className={`tone-${band.tone}`}>{v.toFixed(0)}</span>
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
