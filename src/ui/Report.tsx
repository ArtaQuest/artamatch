/**
 * Report.tsx — the full reading for one pair.
 *
 * Ordered the way a person actually reads: the answer, then how confident it is, then what it is
 * built from, then everything else. A number never appears without the rule that produced it
 * somewhere on the same screen.
 *
 * There is no chart wheel. The connection grid is a table, which is what the data is, reads on a
 * phone, and needs no legend to interpret.
 */

import { useCallback, useMemo, useState } from "react";
import { BODIES, SIGNS, type Body } from "../engine/ephemeris";
import { GANA_LABEL, NADI_LABEL, YONI_LABEL } from "../engine/nakshatra";
import {
  matchPair, PERCENTILE_BELOW, PERCENTILE_BELOW_NO_VARNA,
  TRADITIONAL_PASS, PASS_RATE, MEDIAN_SCORE, type Match, type ScoreOptions,
} from "../engine/score";
import { synastryAspects, type SynAspect } from "../engine/synastry";
import {
  explainAspect, explainKuta, explainDosha, aspectLabel, formatOrb,
  closeness, BODY_MEANS, birthStarText, moonSignText, starTitle,
} from "../engine/interpret";
import type { Person } from "../data/people";
import { messageUrl, profileUrl } from "../data/artaquest";
import { Avatar, Meter, RangeBar } from "./bits";

type Tab = "short" | "tests" | "between" | "where";

const TABS: [Tab, string][] = [
  ["short", "In short"],
  ["tests", "The eight tests"],
  ["between", "What runs between them"],
  ["where", "Where everything was"],
];

export default function Report({ a, b, options, onClose }: {
  a: Person; b: Person; options: ScoreOptions; onClose: () => void;
}) {
  const [tab, setTab] = useState<Tab>("short");
  const [copied, setCopied] = useState(false);
  // A link that reproduces THIS reading on any browser: both names and dates in the query string.
  // Everything is recomputed on arrival, so the link carries inputs, never conclusions.
  const shareReading = useCallback(() => {
    const u = new URL(window.location.href);
    u.search = "";
    u.searchParams.set("n", a.name); u.searchParams.set("b", a.birthday);
    u.searchParams.set("n2", b.name); u.searchParams.set("b2", b.birthday);
    const done = () => { setCopied(true); setTimeout(() => setCopied(false), 2500); };
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(u.toString()).then(done, done);
    else { window.prompt("Copy this link", u.toString()); done(); }
  }, [a, b]);
  const match = useMemo(
    () => matchPair(a.birthday, b.birthday, true, options),
    [a.birthday, b.birthday, options],
  );

  if (!match) {
    return (
      <div className="panel">
        <p className="error">One of these dates is not a real calendar date, so nothing can be worked out from it.</p>
        <button className="ghost" onClick={onClose}>Back</button>
      </div>
    );
  }

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
        <span className={`num tone-${match.band.tone}`}>
          {match.score % 1 === 0 ? match.score : match.score.toFixed(1)}
          <small>out of {match.maxScore}</small>
        </span>
        <span>
          <span className="verdict">
            {match.band.label}
            {match.distribution && !match.distribution.certain && (
              <span className="pill soft" style={{ marginLeft: "0.5rem" }}>
                ~{Math.round(match.distribution.confidence * 100)}% sure
              </span>
            )}
          </span>
          <span className="because">
            Higher than <strong>{match.percentile} in 100</strong> randomly paired dates.{" "}
            {match.band.note} The strip below shows where that sits: every possible score, sized by
            how often random pairs land on it, with this pair marked.
          </span>
          <Landscape score={match.score} excluded={(options.exclude ?? []).length > 0} />
        </span>
      </div>

      <ScoreAnatomy match={match} />

      {match.range && match.range.max > match.range.min && (
        <div className="note blue">
          <strong>If the birth times were known</strong>
          The score could sit anywhere from {match.range.min} to {match.range.max} out of{" "}
          {match.maxScore}, depending on the hours nobody recorded:
          <RangeBar min={match.range.min} max={match.range.max} value={match.score}
            scaleMin={0} scaleMax={match.maxScore} />
        </div>
      )}

      <Answers match={match} a={a} b={b} excluded={(options.exclude ?? []) as string[]} />

      {match.distribution && !match.distribution.certain && (
        <div className="note">
          <strong>Only about {Math.round(match.distribution.confidence * 100)}% sure of this one</strong>
          Nobody said what time of day either of them was born, and the Moon moves far enough in a day
          to land in a different birth star. Each row below is a reading the two dates allow, with how
          likely it is:
          <div className="scroll-x" style={{ marginTop: "0.5rem" }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Chance</th><th>Score</th>
                  <th>{a.name}'s birth star</th><th>{b.name}'s birth star</th>
                </tr>
              </thead>
              <tbody>
                {match.distribution.outcomes.map((o, i) => (
                  <tr key={i} style={i === 0 ? { color: "var(--yang)" } : undefined}>
                    <td className="num">{Math.round(o.probability * 100)}%</td>
                    <td className="num">{o.score % 1 === 0 ? o.score : o.score.toFixed(1)}</td>
                    <td>{o.labelA}</td>
                    <td>{o.labelB}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {(msg || prof) && (
        <div className="row" style={{ marginBottom: "0.7rem" }}>
          {msg && <a href={msg} target="_blank" rel="noreferrer"><button>Message on ArtaQuest</button></a>}
          {prof && <a href={prof} target="_blank" rel="noreferrer"><button className="ghost">View profile</button></a>}
        </div>
      )}

      <div className="row" style={{ marginBottom: "0.7rem" }}>
        <button className="ghost" onClick={shareReading}>
          {copied ? "Link copied" : "Copy a link to this reading"}
        </button>
        <span className="panel-note" style={{ margin: 0 }}>
          The link carries only the two names and dates — whoever opens it computes everything fresh.
        </span>
      </div>

      <div className="tabs" role="tablist">
        {TABS.map(([key, lbl]) => (
          <button key={key} role="tab" aria-selected={tab === key}
            className={tab === key ? "on" : ""} onClick={() => setTab(key)}>{lbl}</button>
        ))}
      </div>

      {tab === "short" && <InShort match={match} a={a} b={b} />}
      {tab === "tests" && <Tests match={match} a={a} b={b} excluded={(options.exclude ?? []) as string[]} />}
      {tab === "between" && <Between match={match} a={a} b={b} />}
      {tab === "where" && <Where a={a} b={b} match={match} />}
    </div>
  );
}

/** The three plain statements that answer what most people came to ask. */
function Answers({ match, a, b, excluded }: { match: Match; a: Person; b: Person; excluded: string[] }) {
  const { helps, rubs } = match.connections;
  const strongest = match.connections.headline[0];
  // A test the reader switched off must not be quoted back as their best or worst agreement.
  const counted = match.guna.kutas.filter((k) => !excluded.includes(k.key));
  const weakest = [...counted].sort((x, y) =>
    x.points / x.maxPoints - y.points / y.maxPoints)[0];
  const best = [...counted].sort((x, y) =>
    y.points / y.maxPoints - x.points / x.maxPoints)[0];

  return (
    <div className="answers">
      <div className="answer">
        <span className="q">Where do they agree most?</span>
        <span className="ans">
          <strong>{best.name}</strong> — {best.points} of {best.maxPoints}. {best.measures}
        </span>
      </div>
      <div className="answer">
        <span className="q">And least?</span>
        <span className="ans">
          <strong>{weakest.name}</strong> — {weakest.points} of {weakest.maxPoints}. {weakest.measures}
        </span>
      </div>
      <div className="answer">
        <span className="q">What runs between them?</span>
        <span className="ans">
          <strong>{helps} connection{helps === 1 ? "" : "s"} help{helps === 1 ? "s" : ""}</strong> and{" "}
          <strong>{rubs} rub{rubs === 1 ? "s" : ""}</strong>. You can count them in the list.
          {strongest && <> The strongest is {aspectLabel(strongest, a.name, b.name)}.</>}
        </span>
      </div>
    </div>
  );
}

function InShort({ match, a, b }: { match: Match; a: Person; b: Person }) {
  const top = match.connections.headline.slice(0, 5);
  const doshas = match.guna.doshas;

  return (
    <>
      <div className="note blue">
        <strong>How the Moon score works, in four sentences</strong>
        Where the Moon sat when each of them was born is the whole basis of this. Eight old tests
        compare those two positions, each worth a different number of points, adding up to
        thirty-six. {TRADITIONAL_PASS} is the traditional pass mark, but {PASS_RATE} in 100 random
        pairs clear it and the middling pair scores about {MEDIAN_SCORE}, so the percentile above
        tells you far more than the pass mark does. Nobody knows what time of day anyone was born,
        and the Moon moves about 13 degrees a day, so where that changes the answer this page shows
        you every answer it could be.
      </div>

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

function Tests({ match, a, b, excluded }: { match: Match; a: Person; b: Person; excluded: string[] }) {
  const g = match.guna;
  const shown = g.kutas.filter((k) => !excluded.includes(k.key));
  return (
    <>
      <p className="panel-note">
        Eight tests, {g.maxTotal} points between them. Every one of them reads where the Moon was —
        nothing else about the two people enters the score.
        Each shows the rule it used and the exact thing it read, so any line can be checked by hand.
        And this is the thing they all read — the two Moons, on the sky's full 360° band:
      </p>

      <MoonRuler match={match} a={a} b={b} />

      <div className="note blue">
        <strong>What a date alone can carry</strong>
        The Moon moves about 13 degrees in a day. A Moon sign is 30 degrees wide, so without the time
        of birth there is roughly an <strong>11% chance of the wrong Moon sign</strong>, which would
        change four of the eight tests. A birth star is only 13 degrees wide, so there is roughly a{" "}
        <strong>25% chance of the wrong birth star</strong>, which would change the other four —{" "}
        <strong>21 of the 36 points</strong>. Finer divisions than that are not attempted at all,
        because the uncertainty swallows them whole.
      </div>

      {g.orderMatters && (
        <div className="note">
          <strong>Order matters in this pairing</strong>
          Three of the eight were written for a groom and a bride, and give different answers
          depending which way round you read them. Nobody has said who is who here, so both ways are
          worked out and the average used: <strong>{g.forward.total}</strong> with {a.name} first,{" "}
          <strong>{g.reverse.total}</strong> with {b.name} first. The ranking uses the average,
          because otherwise your list and their list would disagree about the same pair.
        </div>
      )}

      {excluded.length > 0 && (
        <p className="panel-note">
          One test is switched off in "What gets counted" and is left out of both the list and the
          total below.
        </p>
      )}
      {shown.map((k, i) => (
        <div className="kuta" key={k.key}>
          <div className="kuta-head">
            <span className="nm">
              <span style={{ color: "var(--dim)", fontFamily: "var(--mono)", marginRight: "0.45rem" }}>
                {i + 1}
              </span>
              {k.name}
            </span>
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
              <b>Order matters here:</b> {k.forwardPoints} with {a.name} first,{" "}
              {k.reversePoints} with {b.name} first. The average is used.
            </span>
          )}
        </div>
      ))}

      <div className="row" style={{ marginTop: "1rem", justifyContent: "space-between" }}>
        <strong>Total</strong>
        <strong style={{ fontFamily: "var(--mono)" }}>
          {match.score} / {match.maxScore} — {match.band.label}
        </strong>
      </div>
    </>
  );
}

const GRID_BODIES: Body[] = BODIES;
const OUTERS: Body[] = ["Uranus", "Neptune", "Pluto"];

function Between({ match, a, b }: { match: Match; a: Person; b: Person }) {
  const aspects = useMemo(
    () => synastryAspects(match.spanA.chart, match.spanB.chart),
    [match],
  );
  const lookup = useMemo(() => {
    const m = new Map<string, SynAspect>();
    for (const asp of aspects) m.set(`${asp.a.body}|${asp.b.body}`, asp);
    return m;
  }, [aspects]);

  // Major angle names are allowed vocabulary, abbreviated to fit a cell; the minor angles are
  // not, so they show as a plain dot and speak through their tooltip.
  const mark: Record<string, string> = {
    conjunction: "cnj", opposition: "opp", trine: "tri", square: "sqr", sextile: "sxt",
  };
  const SHORT: Record<Body, string> = {
    Sun: "Sun", Moon: "Moon", Mercury: "Mer", Venus: "Ven", Mars: "Mars",
    Jupiter: "Jup", Saturn: "Sat", Uranus: "Ura", Neptune: "Nep", Pluto: "Plu",
  };

  const major = aspects.filter((x) => x.def.major);
  const isGenerational = (x: SynAspect) => OUTERS.includes(x.a.body) && OUTERS.includes(x.b.body);
  const personal = major.filter((x) => !isGenerational(x));
  const generational = major.filter(isGenerational);

  return (
    <>
      <div className="note blue">
        <strong>These do not count towards the score</strong>
        The eight tests are the score. What follows is a second, separate way of looking at the same
        two people — the angles between where their planets sat. It is here because it says things
        the eight tests do not, but it is commentary, not arithmetic.
        <br /><br />
        One thing worth knowing: an angle between two planets is the same number whichever zodiac you
        measure from. The two traditions disagree about where the zodiac starts, and that changes
        which sign something falls in — but it cannot change the angle between two things. So this
        half of the page is not mixing systems, even though it looks like it might be.
      </div>

      <h3>The connection grid</h3>
      <p className="panel-note">
        {a.name} down the side, {b.name} across the top. Every filled square is one connection. Gold
        helps, blue rubs. Hover any square to read it out in words.
      </p>
      <div className="scroll-x">
        <table className="grid">
          <thead>
            <tr>
              <th aria-label="body" />
              {GRID_BODIES.map((bb) => (
                <th key={bb} title={`${bb} — ${BODY_MEANS[bb]}`}>{SHORT[bb]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {GRID_BODIES.map((ba) => (
              <tr key={ba}>
                <th title={`${ba} — ${BODY_MEANS[ba]}`}>{SHORT[ba]}</th>
                {GRID_BODIES.map((bb) => {
                  const asp = lookup.get(`${ba}|${bb}`);
                  if (!asp) return <td key={bb} className="flat" />;
                  const cls = asp.valence > 0.15 ? "ease" : asp.valence < -0.15 ? "friction" : "flat";
                  return (
                    <td key={bb} className={cls}
                      title={`${a.name}'s ${BODY_MEANS[ba]} ${asp.def.plain} ${b.name}'s ${BODY_MEANS[bb]} — ${closeness(asp.exactness)}`}>
                      {mark[asp.type] ?? "·"}
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
        {personal.length} of them, strongest first — meaning the two things involved matter most to a
        relationship and the connection sits closest to exact.
        {generational.length > 0 && (
          <> {generational.length} more are left out: they run between the slowest planets, which take
          between 84 and 248 years to go round, so almost everybody born in the same few years shares
          them. They describe a generation, not these two.</>
        )}
      </p>
      {personal.map((asp, i) => (
        <div className="aspect-line" key={i}>
          <span className="top">
            <span className="sym">{aspectLabel(asp, a.name, b.name)}</span>
            <span className="pill soft" title={`${formatOrb(asp.orb)} from exact`}>
              {closeness(asp.exactness)}
            </span>
          </span>
          <span className="txt">{explainAspect(asp, a.name, b.name)}</span>
        </div>
      ))}
    </>
  );
}

function Where({ a, b, match }: { a: Person; b: Person; match: Match }) {
  return (
    <>
      <p className="panel-note">
        Where each planet sat on the day they were born, measured against the constellations — the
        older of the two zodiacs, and the one this tradition is built on. Taken at the most likely
        moment of the day, since nobody knows the hour.
      </p>
      <div className="cols">
        <PersonChart person={a} span={match.spanA} />
        <PersonChart person={b} span={match.spanB} />
      </div>
    </>
  );
}

function PersonChart({ person, span }: { person: Person; span: Match["spanA"] }) {
  const star = birthStarText(span.likeliest.nakshatra.index);
  const moonSign = moonSignText(span.likeliest.rasi);
  return (
    <div>
      <h3>
        {person.name}{" "}
        <span style={{ color: "var(--muted)", fontWeight: 400, fontSize: "0.85rem" }}>
          {person.birthday}
        </span>
      </h3>

      {star && (
        <div className="note blue">
          <strong>Their birth star: {star.title}</strong>
          {star.summary} <em style={{ opacity: 0.85 }}>{star.inRelationships}</em>
        </div>
      )}
      {moonSign && (
        <p className="panel-note">
          <b style={{ color: "var(--muted)" }}>
            Moon in {SIGNS[span.likeliest.rasi]} — {moonSign.title}.
          </b>{" "}
          {moonSign.style}
        </p>
      )}

      <table className="data">
        <tbody>
          <tr><th>Birth star</th><td>{starTitle(span.likeliest.nakshatra.index)} — one of the 27
            equal stretches of sky the Moon passes through each month</td></tr>
          <tr><th>Temperament</th><td>{GANA_LABEL[span.likeliest.nakshatra.gana]}</td></tr>
          <tr><th>Its animal</th><td>{YONI_LABEL[span.likeliest.nakshatra.yoni]}</td></tr>
          <tr><th>Built</th><td>{NADI_LABEL[span.likeliest.nakshatra.nadi]}</td></tr>
          <tr><th>Moon that day</th><td>
            moved {span.moonArc.toFixed(1)}°
            {span.stable
              ? " — stayed in one birth star and one sign all day"
              : ` — passed through ${span.states.length} different readings: ` +
                span.states.map((s) => `${starTitle(s.nakshatra.index)} (${Math.round(s.share * 100)}%)`).join(", ")}
          </td></tr>
        </tbody>
      </table>

      <h4 style={{ marginTop: "0.9rem" }}>Everything else</h4>
      <div className="scroll-x">
        <table className="data">
          <thead>
            <tr><th>What</th><th>Where it sat</th><th className="num">Moving</th></tr>
          </thead>
          <tbody>
            {span.chart.placements.map((p) => (
              <tr key={p.body}>
                <td>
                  {p.body}<br />
                  <span style={{ color: "var(--dim)", fontSize: "0.72rem" }}>{BODY_MEANS[p.body]}</span>
                </td>
                <td>{p.deg.toFixed(1)}° into {SIGNS[p.sign]}</td>
                <td className="num" title={`${p.speed.toFixed(2)}° per day`}>
                  {p.retro ? "backwards" : "forwards"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════════════════════════════════════
// The explainability instruments. All linear — never a wheel — and none relies on colour alone:
// every mark carries a label or a tooltip, because the brand allows exactly two hues.
// ════════════════════════════════════════════════════════════════════════════════════════════════

/**
 * Where this pair lands among all pairs: the measured score distribution as a strip of thin bars,
 * with this pair's score highlighted. This is the picture behind every "higher than N in 100"
 * sentence on the page — the percentile stops being a claim and becomes a place you can see.
 */
function Landscape({ score, excluded }: { score: number; excluded: boolean }) {
  const table = excluded ? PERCENTILE_BELOW_NO_VARNA : PERCENTILE_BELOW;
  // The cumulative table differences into per-score shares.
  const shares = table.slice(1).map((v, i) => Math.max(0, v - table[i]));
  const peak = Math.max(...shares);
  const at = Math.min(shares.length - 1, Math.max(0, Math.round(score) - (score > Math.round(score) ? 0 : 1)));
  return (
    <span className="landscape" aria-hidden="true">
      {shares.map((share, i) => (
        <i key={i}
          className={i === at ? "here" : ""}
          style={{ height: `${Math.max(share > 0 ? 8 : 2, (share / peak) * 100)}%` }}
          title={`Score ${i + 1}: about ${share} in 100 random pairs land here`} />
      ))}
    </span>
  );
}

/**
 * The anatomy of the score: 36 = 1+2+3+4+5+6+7+8, drawn to scale. Each segment is one of the
 * eight tests, wide in proportion to the points it can award, filled gold in proportion to the
 * points it did award. The whole number becomes visible arithmetic — a reader can SEE that the
 * two heaviest tests carry as much as the other six together, and exactly where this pair's
 * points came from and went missing.
 */
function ScoreAnatomy({ match }: { match: Match }) {
  const kutas = match.guna.kutas.filter((k) =>
    (match.maxScore === 36) || k.key !== "varna");
  return (
    <div className="anatomy">
      <span className="cap">
        How the score is built — eight tests worth 1 through 8 points, drawn to scale. Gold is
        earned; hover any block for its name and result.
      </span>
      <span className="host"><span className="bar">
        {kutas.map((k, i) => (
          <span key={k.key} className="seg" style={{ flexGrow: k.maxPoints }}
            title={`Test ${i + 1} · ${k.name} — ${k.points} of ${k.maxPoints}. ${k.measures}`}>
            <i style={{ width: `${(k.points / k.maxPoints) * 100}%` }} />
            <b>{k.points > 0 ? k.points % 1 === 0 ? k.points : k.points.toFixed(1) : ""}</b>
            <u>{k.maxPoints}</u>
          </span>
        ))}
      </span></span>
      <span className="cap dim">
        Numbers inside each block are points earned; beneath, the points available. The two heaviest
        tests ({kutas[kutas.length - 2]?.name.toLowerCase()} and {kutas[kutas.length - 1]?.name.toLowerCase()})
        carry {7 + 8} of the {match.maxScore} between them — as much as the other six together, so
        they usually decide the headline.
      </span>
    </div>
  );
}

/**
 * The sky's ruler: the full 360° band the Moon travels, divided into the 27 equal birth-star
 * stretches (light ticks) and the 12 signs (heavy ticks), with each person's Moon marked — and the
 * band it swept during their birth day, which is the uncertainty made visible. This is the one
 * picture that shows WHAT the eight tests actually read.
 */
export function MoonRuler({ match, a, b }: { match: Match; a: Person; b: Person }) {
  const spans = [
    { span: match.spanA, name: a.name, cls: "a" },
    { span: match.spanB, name: b.name, cls: "b" },
  ];
  const pct = (lon: number) => `${(lon / 360) * 100}%`;
  return (
    <div className="ruler-wrap">
      <div className="ruler" aria-hidden="true">
        {Array.from({ length: 27 }, (_, i) => (
          <span key={`n${i}`} className="tick star" style={{ left: pct((i * 360) / 27) }}
            title={starTitle(i)} />
        ))}
        {Array.from({ length: 12 }, (_, i) => (
          <span key={`s${i}`} className="tick sign" style={{ left: pct(i * 30) }} title={SIGNS[i]} />
        ))}
        {spans.map(({ span, name, cls }) => {
          const start = span.moonStartLon;
          const arc = span.moonArc;
          const wraps = start + arc > 360;
          return (
            <span key={cls}>
              <span className={`sweep ${cls}`} style={{
                left: pct(start), width: wraps ? pct(360 - start) : pct(arc),
              }} title={`${name}'s Moon swept ${arc.toFixed(1)}° during the birth day`} />
              {wraps && <span className={`sweep ${cls}`} style={{ left: 0, width: pct((start + arc) % 360) }} />}
              <span className={`moon ${cls}`} style={{ left: pct(span.likeliest.lon) }}
                title={`${name}'s Moon — ${starTitle(span.likeliest.nakshatra.index)}, in ${SIGNS[span.likeliest.rasi]}`} />
            </span>
          );
        })}
      </div>
      <div className="legend">
        <span><i style={{ background: "var(--yang)", borderRadius: "50%" }} /> {a.name}'s Moon</span>
        <span><i style={{ background: "var(--yin-lift)", borderRadius: "50%" }} /> {b.name}'s Moon</span>
        <span>tall ticks: the 12 signs · short ticks: the 27 birth-star stretches · the faint band
          behind each dot is how far that Moon travelled during the birth day</span>
      </div>
    </div>
  );
}
