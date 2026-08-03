/**
 * Report.tsx — the full compatibility report for one pair.
 *
 * Laid out the way a professional synastry report is: the headline first, then the evidence, then
 * the interpretation — never a number without the rule that produced it directly beside it.
 *
 * There is deliberately NO chart wheel. The aspect grid is a table, which is what the underlying
 * data actually is, reads on a phone, and does not need a legend.
 */

import { useMemo, useState } from "react";
import { BODIES, SIGN_GLYPH, BODY_GLYPH, SIGNS, RASI, type Body } from "../engine/ephemeris";
import { nakshatraOf, GANA_LABEL, NADI_LABEL, YONI_LABEL } from "../engine/nakshatra";
import { matchPair, overallBand } from "../engine/score";
import { synastryAspects, type SynAspect } from "../engine/synastry";
import {
  explainAspect, explainKuta, explainDosha, aspectLabel, formatOrb, formatDegree, headlineSummary,
  closeness, BODY_MEANS, birthStarText, moonSignText,
} from "../engine/interpret";
import type { Person } from "../data/people";
import { messageUrl, profileUrl } from "../data/artaquest";
import { Avatar, Meter, RangeBar } from "./bits";

type Tab = "summary" | "guna" | "aspects" | "charts";

export default function Report({ a, b, onClose }: { a: Person; b: Person; onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("summary");
  // The detailed evaluation samples 81 birth-time combinations, so it is memoised on the pair.
  const match = useMemo(() => matchPair(a.birthday, b.birthday, true), [a.birthday, b.birthday]);

  if (!match) {
    return (
      <div className="panel">
        <p className="error">One of these dates is not a real calendar date, so no chart can be cast.</p>
        <button className="ghost" onClick={onClose}>Back</button>
      </div>
    );
  }

  const { components, spanA, spanB } = match;
  const band = overallBand(match.overall);
  const msg = messageUrl(b) ?? messageUrl(a);
  const prof = profileUrl(b);

  return (
    <div className="panel">
      <div className="report-head">
        <Avatar person={a} />
        <Avatar person={b} />
        <span className="names">{a.name} &amp; {b.name}</span>
        <button className="ghost" onClick={onClose}>Close</button>
      </div>

      <div className="hero">
        <span className={`num tone-${band.tone}`}>
          {match.overall.toFixed(0)}
          <small>out of 100</small>
        </span>
        <span>
          <span className="verdict">{band.label}</span>
          <span className="because">
            {headlineSummary(components.guna.total, components.easeScore, components.chargeScore)}
          </span>
          {match.band && !match.band.certain && (
            <RangeBar min={match.band.min} max={match.band.max} value={match.overall} />
          )}
        </span>
      </div>

      {match.distribution && !match.distribution.certain && (
        <div className="note">
          <strong>
            This reading is about {Math.round(match.distribution.confidence * 100)}% likely
          </strong>
          Nobody told us what time of day either of them was born, and the Moon moves far enough in a
          day to change the answer. These are all the readings the two dates allow:
          <div className="scroll-x" style={{ marginTop: "0.5rem" }}>
            <table className="data">
              <thead>
                <tr><th>Chance</th><th>Score out of 36</th><th>{a.name}'s birth star</th><th>{b.name}'s</th></tr>
              </thead>
              <tbody>
                {match.distribution.outcomes.map((o, i) => (
                  <tr key={i} style={i === 0 ? { color: "var(--yang)" } : undefined}>
                    <td className="num">{Math.round(o.probability * 100)}%</td>
                    <td className="num">{o.guna.toFixed(1)}</td>
                    <td>{o.labelA}</td>
                    <td>{o.labelB}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="scores">
        <div className="scorecard">
          <span className="k">Traditional score</span>
          <span className="v">{components.guna.total.toFixed(1)} <em>/ 36</em></span>
          <Meter value={components.guna.total} max={36} gold />
          <span className="d">{components.guna.band.label}. {components.guna.band.note}</span>
        </div>
        <div className="scorecard">
          <span className="k">How easy</span>
          <span className="v">{components.easeScore.toFixed(0)}</span>
          <Meter value={components.easeScore} gold />
          <span className="d">Whether the connections between them lean supportive or difficult.</span>
        </div>
        <div className="scorecard">
          <span className="k">How much pull</span>
          <span className="v">{components.chargeScore.toFixed(0)}</span>
          <Meter value={components.chargeScore} />
          <span className="d">How much there is between them at all. Intensity, not compatibility.</span>
        </div>
      </div>

      {match.certain && (
        <div className="note blue">
          <strong>The dates settle this one</strong>
          Both Moons stay put for the whole of their birth day, so not knowing the time of day
          changes nothing here.
        </div>
      )}

      {(msg || prof) && (
        <div className="row" style={{ marginBottom: "0.7rem" }}>
          {msg && <a href={msg} target="_blank" rel="noreferrer"><button>Message on ArtaQuest</button></a>}
          {prof && <a href={prof} target="_blank" rel="noreferrer"><button className="ghost">View profile</button></a>}
        </div>
      )}

      <div className="tabs" role="tablist">
        {([["summary", "In short"], ["guna", "The eight tests"], ["aspects", "What runs between them"],
           ["charts", "Where everything was"]] as [Tab, string][])
          .map(([key, lbl]) => (
            <button key={key} role="tab" aria-selected={tab === key}
              className={tab === key ? "on" : ""} onClick={() => setTab(key)}>{lbl}</button>
          ))}
      </div>

      {tab === "summary" && <Summary match={match} a={a} b={b} />}
      {tab === "guna" && <Guna match={match} a={a} b={b} />}
      {tab === "aspects" && <Aspects match={match} a={a} b={b} />}
      {tab === "charts" && <Charts a={a} b={b} spanA={spanA} spanB={spanB} />}
    </div>
  );
}

type MatchProp = NonNullable<ReturnType<typeof matchPair>>;

function Summary({ match, a, b }: { match: MatchProp; a: Person; b: Person }) {
  const { components } = match;
  const top = components.synastry.headline.slice(0, 6);
  const doshas = components.guna.doshas;

  return (
    <>
      <h3>What stands out</h3>
      {top.length === 0 && <p className="empty">There is very little running between these two either way.</p>}
      {top.map((asp, i) => (
        <div className="aspect-line" key={i}>
          <span className="top">
            <span className="sym">{aspectLabel(asp, a.name, b.name)}</span>
            <span className={`pill ${asp.valence > 0.15 ? "" : asp.valence < -0.15 ? "warn" : "soft"}`}>
              {asp.valence > 0.15 ? "helps" : asp.valence < -0.15 ? "rubs" : "mixed"}
            </span>
            <span className="pill soft" title={`${formatOrb(asp.orb)} from exact`}>
              {closeness(asp.exactness)}
            </span>
          </span>
          <span className="txt">{explainAspect(asp, a.name, b.name)}</span>
        </div>
      ))}

      {doshas.length > 0 && (
        <>
          <h3 style={{ marginTop: "1.2rem" }}>Warnings the tradition raises</h3>
          {doshas.map((d) => (
            <div key={d.key} className="note">
              <strong>{d.name}{d.cancelled ? " — traditionally set aside" : ""}</strong>
              {explainDosha(d)}
            </div>
          ))}
        </>
      )}
    </>
  );
}

function Guna({ match, a, b }: { match: MatchProp; a: Person; b: Person }) {
  const g = match.components.guna;
  return (
    <>
      <p className="panel-note">
        Eight tests, 36 points between them. Six of the eight read only where the Moon was. Each one
        shows the rule it used and the exact thing it read, so you can check any line by hand.
      </p>

      <div className="note blue">
        <strong>What a date alone can carry</strong><br />
        The Moon moves about 13 degrees in a day. A Moon sign is 30 degrees wide, so without knowing
        the time of birth there is roughly an <strong>11% chance of the wrong Moon sign</strong> —
        which would change four of the eight tests. A birth star is only 13 degrees wide, so there is
        roughly a <strong>25% chance of the wrong birth star</strong> — which would change the other
        four, <strong>21 of the 36 points</strong>. Finer divisions than that are not attempted at
        all: the uncertainty swallows them whole, so they would be guesswork dressed up as arithmetic.
      </div>

      {g.orderMatters && (
        <div className="note">
          <strong>Order matters in this pairing</strong><br />
          Three of the eight tests were written for a groom and a bride, and they give different
          answers depending on which way round you read them. Nobody has said who is who here, so
          both ways are worked out and the average is used:
          {" "}<strong>{g.forward.total.toFixed(0)}</strong> with {a.name} first,
          {" "}<strong>{g.reverse.total.toFixed(0)}</strong> with {b.name} first.
          The ranking uses the average, because otherwise your list and their list would disagree
          about the same pair.
        </div>
      )}

      {g.kutas.map((k) => (
        <div className="kuta" key={k.key}>
          <div className="kuta-head">
            <span className="nm">{k.name}</span>
            <span className={`pts ${k.points >= k.maxPoints ? "tone-high" : k.points <= 0 ? "tone-low" : ""}`}>
              {k.points} / {k.maxPoints}
            </span>
          </div>
          <Meter value={k.points} max={k.maxPoints} gold={k.points > 0} />
          <span className="says">{k.measures} {explainKuta(k)}</span>
          <span className="detail"><b>What was read:</b> {k.evidence}</span>
          <span className="detail"><b>How it is scored:</b> {k.rule}</span>
          {k.forwardPoints !== k.reversePoints && (
            <span className="detail">
              <b>Order matters here:</b> {k.forwardPoints} with {a.name} first,
              {" "}{k.reversePoints} with {b.name} first. The average is used.
            </span>
          )}
        </div>
      ))}

      <div className="row" style={{ marginTop: "1rem", justifyContent: "space-between" }}>
        <strong>Total</strong>
        <strong style={{ fontFamily: "var(--mono)" }}>{g.total.toFixed(1)} / 36 — {g.band.label}</strong>
      </div>
      {match.gunaBand && !match.gunaBand.certain && (
        <p className="panel-note" style={{ marginTop: "0.5rem" }}>
          Across every time of day these two dates allow, this total runs from{" "}
          {match.gunaBand.min.toFixed(1)} to {match.gunaBand.max.toFixed(1)}.
        </p>
      )}
    </>
  );
}

const GRID_BODIES: Body[] = BODIES;

function Aspects({ match, a, b }: { match: MatchProp; a: Person; b: Person }) {
  const aspects = useMemo(
    () => synastryAspects(match.spanA.chart, match.spanB.chart),
    [match],
  );
  const lookup = useMemo(() => {
    const m = new Map<string, SynAspect>();
    for (const asp of aspects) m.set(`${asp.a.body}|${asp.b.body}`, asp);
    return m;
  }, [aspects]);

  const glyph: Record<string, string> = {
    conjunction: "☌", opposition: "☍", trine: "△", square: "□", sextile: "✶",
    quincunx: "⚻", sesquiquadrate: "⚼", quintile: "Q", semisquare: "∠", semisextile: "⚺",
  };

  const major = aspects.filter((x) => x.def.major);
  // Split off the outer-to-outer pairings. They are real, but they are facts about a birth cohort,
  // not about these two people — giving them the same paragraph treatment as a Sun–Moon contact
  // would overstate them exactly where the reader is least able to tell.
  const OUTERS: Body[] = ["Uranus", "Neptune", "Pluto"];
  const isGenerational = (x: SynAspect) => OUTERS.includes(x.a.body) && OUTERS.includes(x.b.body);
  const personal = major.filter((x) => !isGenerational(x));
  const generational = major.filter(isGenerational);

  return (
    <>
      <h3>The connection grid</h3>
      <p className="panel-note">
        {a.name} down the side, {b.name} across the top. Every filled square is a connection between
        one thing in each of them. Gold squares help; blue squares rub. Hover a square to see what it is.
      </p>
      <div className="scroll-x">
        <table className="grid">
          <thead>
            <tr>
              <th aria-label="body" />
              {GRID_BODIES.map((bb) => (
                <th key={bb} title={`${bb} — ${BODY_MEANS[bb]}`}>{BODY_GLYPH[bb]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {GRID_BODIES.map((ba) => (
              <tr key={ba}>
                <th title={`${ba} — ${BODY_MEANS[ba]}`}>{BODY_GLYPH[ba]}</th>
                {GRID_BODIES.map((bb) => {
                  const asp = lookup.get(`${ba}|${bb}`);
                  if (!asp) return <td key={bb} className="neutral" />;
                  const cls = asp.valence > 0.15 ? "ease" : asp.valence < -0.15 ? "friction" : "neutral";
                  return (
                    <td key={bb} className={cls}
                      title={`${a.name}'s ${BODY_MEANS[ba]} ${asp.def.plain} ${b.name}'s ${BODY_MEANS[bb]} — ${closeness(asp.exactness)} (${formatOrb(asp.orb)} from exact)`}>
                      {glyph[asp.type]}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="legend">
        <span><i style={{ background: "rgba(232,185,35,0.6)" }} /> helps</span>
        <span><i style={{ background: "rgba(74,114,240,0.7)" }} /> rubs</span>
        <span><i style={{ background: "var(--panel-2)", border: "1px solid var(--line-2)" }} /> nothing much</span>
      </div>

      <h3 style={{ marginTop: "1.4rem" }}>Every strong connection, explained</h3>
      <p className="panel-note">
        {personal.length} of them, strongest first. "Strongest" means the two things involved matter
        most to a relationship, and the connection sits closest to exact.
        {generational.length > 0 && (
          <> {generational.length} further connections are left out here: they run between the
          slowest-moving planets, which take between 84 and 248 years to go round. Almost everybody
          born in the same few years shares them, so they describe a generation rather than these two
          — and they are weighted to almost nothing in the score for the same reason.</>
        )}
      </p>
      {personal.map((asp, i) => (
        <div className="aspect-line" key={i}>
          <span className="top">
            <span className="sym">{aspectLabel(asp, a.name, b.name)}</span>
            <span className="pill soft" title={`${formatOrb(asp.orb)} from exact`}>{closeness(asp.exactness)}</span>
          </span>
          <span className="txt">{explainAspect(asp, a.name, b.name)}</span>
        </div>
      ))}
    </>
  );
}

function Charts({ a, b, spanA, spanB }: {
  a: Person; b: Person; spanA: MatchProp["spanA"]; spanB: MatchProp["spanB"];
}) {
  return (
    <>
      <p className="panel-note">
        Where each planet sat on the day they were born, measured against the constellations — the
        older of the two zodiacs, and the one this whole tradition is built on. Taken at the most
        likely moment of the day, given that nobody knows the hour.
      </p>
      <div className="cols">
        <PersonChart person={a} span={spanA} />
        <PersonChart person={b} span={spanB} />
      </div>
    </>
  );
}

function PersonChart({ person, span }: { person: Person; span: MatchProp["spanA"] }) {
  const star = birthStarText(span.likeliest.nakshatra.index);
  const moonSign = moonSignText(span.likeliest.rasi);
  return (
    <div>
      <h3>{person.name} <span style={{ color: "var(--muted)", fontWeight: 400, fontFamily: "var(--mono)", fontSize: "0.85rem" }}>{person.birthday}</span></h3>
      <div className="scroll-x">
        <table className="data">
          <thead>
            <tr><th>What</th><th>Where it sat</th><th>Birth star</th><th className="num">Moving</th></tr>
          </thead>
          <tbody>
            {span.chart.placements.map((p) => {
              const nk = nakshatraOf(p.lon);
              return (
                <tr key={p.body}>
                  <td title={BODY_MEANS[p.body]}>{BODY_GLYPH[p.body]} {p.body}<br />
                    <span style={{ color: "var(--dim)", fontSize: "0.72rem" }}>{BODY_MEANS[p.body]}</span></td>
                  <td>{formatDegree(p.deg)} {SIGN_GLYPH[p.sign]} {SIGNS[p.sign]} <span style={{ color: "var(--muted)" }}>({RASI[p.sign]})</span></td>
                  {/* The quarter-division is deliberately NOT shown. It is 3°20′ wide and the
                      unknown birth time moves the Moon by up to ±6.6°, so it would be a number
                      with no information in it — precision this page has already said it lacks. */}
                  <td>{nk.info.name}</td>
                  <td className="num" title={`${p.speed.toFixed(2)}° per day`}>
                    {p.retro ? "backwards" : "forwards"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {star && (
        <div className="note blue" style={{ marginTop: "0.9rem" }}>
          <strong>{span.likeliest.nakshatra.name} — {star.title}</strong>
          {star.summary} <em style={{ opacity: 0.85 }}>{star.inRelationships}</em>
        </div>
      )}
      {moonSign && (
        <p className="panel-note" style={{ marginTop: "0.4rem" }}>
          <b style={{ color: "var(--muted)" }}>Moon in {SIGNS[span.likeliest.rasi]} — {moonSign.title}.</b>{" "}
          {moonSign.style}
        </p>
      )}

      <h4 style={{ marginTop: "0.9rem" }}>Their birth star</h4>
      <table className="data">
        <tbody>
          <tr><th>Birth star</th><td>{span.likeliest.nakshatra.name}</td></tr>
          <tr><th>Its planet</th><td>{span.likeliest.nakshatra.lord}</td></tr>
          <tr><th>Temperament</th><td>{GANA_LABEL[span.likeliest.nakshatra.gana]}</td></tr>
          <tr><th>Its animal</th><td>{YONI_LABEL[span.likeliest.nakshatra.yoni]}</td></tr>
          <tr><th>Built</th><td>{NADI_LABEL[span.likeliest.nakshatra.nadi]}</td></tr>
          <tr><th>Moon that day</th><td>
            moved {span.moonArc.toFixed(2)}°
            {span.stable
              ? " — stayed in one birth star and one sign all day"
              : ` — passed through ${span.states.length} different readings: ` +
                span.states.map((s) => `${s.nakshatra.name} (${Math.round(s.share * 100)}%)`).join(", ")}
          </td></tr>
        </tbody>
      </table>
    </div>
  );
}
