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
} from "../engine/interpret";
import type { Person } from "../data/people";
import { messageUrl, profileUrl } from "../data/artaquest";
import { Avatar, Meter } from "./bits";

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
      <div className="row" style={{ justifyContent: "space-between", marginBottom: "0.8rem" }}>
        <div className="row">
          <Avatar person={a} />
          <Avatar person={b} />
          <strong style={{ marginLeft: "0.3rem" }}>{a.name} &amp; {b.name}</strong>
        </div>
        <button className="ghost" onClick={onClose}>Close</button>
      </div>

      <div className="headline">
        <span className={`big tone-${band.tone}`}>{match.overall.toFixed(0)}</span>
        <span className="of">/ 100 · {band.label}</span>
        {match.band && !match.band.certain && (
          <span className="pill warn">
            could be {match.band.min.toFixed(0)}–{match.band.max.toFixed(0)} without birth times
          </span>
        )}
      </div>

      <p>{headlineSummary(a.name, b.name, match.overall, components.guna.total,
        components.easeScore, components.chargeScore)}</p>

      <div className="scores">
        <div className="scorecard">
          <div className="k">Guna Milan</div>
          <div className="v">{components.guna.total.toFixed(1)}<span style={{ fontSize: "0.8rem", color: "var(--muted)" }}> / 36</span></div>
          <Meter value={components.guna.total} max={36} />
          <div className="d">{components.guna.band.label}. {components.guna.band.note}</div>
        </div>
        <div className="scorecard">
          <div className="k">Ease</div>
          <div className="v">{components.easeScore.toFixed(0)}</div>
          <Meter value={components.easeScore} />
          <div className="d">How supportive the aspects between the charts are, on balance.</div>
        </div>
        <div className="scorecard">
          <div className="k">Charge</div>
          <div className="v">{components.chargeScore.toFixed(0)}</div>
          <Meter value={components.chargeScore} />
          <div className="d">How much contact there is at all — intensity, not compatibility.</div>
        </div>
      </div>

      <div className={`note ${match.certain ? "blue" : ""}`}>
        <strong>{match.certain ? "No birth time needed here" : "What the missing birth times cost"}</strong>
        <br />
        {match.uncertaintyNote}
      </div>

      {(msg || prof) && (
        <div className="row" style={{ marginBottom: "0.6rem" }}>
          {msg && <a href={msg} target="_blank" rel="noreferrer"><button>Message on ArtaQuest</button></a>}
          {prof && <a href={prof} target="_blank" rel="noreferrer"><button className="ghost">View profile</button></a>}
        </div>
      )}

      <div className="tabs" role="tablist">
        {([["summary", "Summary"], ["guna", "Guna Milan · 36"], ["aspects", "Aspects"], ["charts", "Positions"]] as [Tab, string][])
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
      {top.length === 0 && <p className="empty">These two charts make no significant contact at all.</p>}
      {top.map((asp, i) => (
        <div key={i} style={{ marginBottom: "0.8rem" }}>
          <div className="row" style={{ gap: "0.5rem" }}>
            <strong style={{ fontFamily: "var(--mono)" }}>{aspectLabel(asp)}</strong>
            <span className="pill">{formatOrb(asp.orb)} orb</span>
            <span className={`pill ${asp.valence > 0 ? "" : "warn"}`}>
              {asp.valence > 0.15 ? "supportive" : asp.valence < -0.15 ? "friction" : "neutral"}
            </span>
          </div>
          <p style={{ margin: "0.2rem 0 0", fontSize: "0.9rem" }}>{explainAspect(asp, a.name, b.name)}</p>
        </div>
      ))}

      {doshas.length > 0 && (
        <>
          <h3 style={{ marginTop: "1.2rem" }}>Doshas the tradition flags</h3>
          {doshas.map((d) => (
            <div key={d.key} className="note">
              <strong>{d.name}{d.cancelled ? " — traditionally cancelled" : ""}</strong>
              <br />{explainDosha(d)}
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
        Eight tests, 36 points. Six of them read the Moon's birth star and rāśi. The rule and the exact
        values read are shown for every one, so each line can be checked by hand.
      </p>

      <div className="note blue">
        <strong>What a date alone can carry</strong><br />
        Assuming noon with the true birth time unknown puts the Moon within ±6.6°. Against a 30° rāśi
        that is roughly an <strong>11% chance of the wrong sign</strong> — which would change Varna,
        Vashya, Graha Maitri and Bhakoot. Against a 13°20′ birth star it is roughly a{" "}
        <strong>25% chance of the wrong nakshatra</strong> — which would change Tara, Yoni, Gana and
        Nadi, <strong>21 of the 36 points</strong>. Pada-level rules are not attempted at all: the
        error exceeds two whole padas, so they are unusable without a clock rather than approximate.
      </div>

      {g.orderMatters && (
        <div className="note">
          <strong>Order matters in this pairing</strong><br />
          Three of the eight kutas are written for a groom and a bride and are genuinely asymmetric.
          ArtaMatch was not told who is who, so it computes both orderings and shows the mean:
          {" "}<strong>{g.forward.total.toFixed(0)}</strong> with {a.name} first,
          {" "}<strong>{g.reverse.total.toFixed(0)}</strong> with {b.name} first.
          Ranking uses the mean, because a ranked list has to be symmetric to make sense.
        </div>
      )}

      {g.kutas.map((k) => (
        <div className="kuta" key={k.key}>
          <div className="kuta-head">
            <span className="nm">{k.name}</span>
            <span className="sa">{k.sanskrit}</span>
            <span className={`pts ${k.points >= k.maxPoints ? "tone-high" : k.points <= 0 ? "tone-low" : ""}`}>
              {k.points} / {k.maxPoints}
            </span>
          </div>
          <Meter value={k.points} max={k.maxPoints} />
          <p className="measures">{k.measures}</p>
          <p className="evidence">{k.evidence}</p>
          <p className="rule"><em>Rule:</em> {k.rule}</p>
          <p className="rule">{explainKuta(k)}</p>
          {k.forwardPoints !== k.reversePoints && (
            <p className="rule">
              Asymmetric: {k.forwardPoints} with {a.name} first, {k.reversePoints} with {b.name} first.
            </p>
          )}
        </div>
      ))}

      <div className="row" style={{ marginTop: "1rem", justifyContent: "space-between" }}>
        <strong>Total</strong>
        <strong style={{ fontFamily: "var(--mono)" }}>{g.total.toFixed(1)} / 36 — {g.band.label}</strong>
      </div>
      {match.gunaBand && !match.gunaBand.certain && (
        <p className="panel-note" style={{ marginTop: "0.5rem" }}>
          Across every birth time these two dates allow, this total ranges from{" "}
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

  return (
    <>
      <h3>Aspect grid</h3>
      <p className="panel-note">
        {a.name}'s bodies down the side, {b.name}'s across the top. Gold is supportive, blue is
        friction. Read it as a table — that is what it is.
      </p>
      <div className="scroll-x">
        <table className="grid">
          <thead>
            <tr>
              <th aria-label="body" />
              {GRID_BODIES.map((bb) => <th key={bb} title={bb}>{BODY_GLYPH[bb]}</th>)}
            </tr>
          </thead>
          <tbody>
            {GRID_BODIES.map((ba) => (
              <tr key={ba}>
                <th title={ba}>{BODY_GLYPH[ba]}</th>
                {GRID_BODIES.map((bb) => {
                  const asp = lookup.get(`${ba}|${bb}`);
                  if (!asp) return <td key={bb} className="neutral" />;
                  const cls = asp.valence > 0.15 ? "ease" : asp.valence < -0.15 ? "friction" : "neutral";
                  return (
                    <td key={bb} className={`hit ${cls}`}
                      title={`${ba} ${asp.def.label} ${bb} — orb ${formatOrb(asp.orb)}`}>
                      {glyph[asp.type]}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 style={{ marginTop: "1.4rem" }}>Every major aspect, explained</h3>
      <p className="panel-note">{major.length} major aspects, ordered by how much each one counts.</p>
      {major.map((asp, i) => (
        <div className="aspect-line" key={i}>
          <span className="sym">{aspectLabel(asp)}</span>
          <span className="txt">{explainAspect(asp, a.name, b.name)}</span>
          <span className="orb">{formatOrb(asp.orb)}</span>
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
        Sidereal (Lahiri ayanamsa), computed at 12:00 UT on each birth date. Ayanamsa
        {" "}{spanA.chart.ayanamsa.toFixed(4)}° and {spanB.chart.ayanamsa.toFixed(4)}°.
      </p>
      <div className="cols">
        <PersonChart person={a} span={spanA} />
        <PersonChart person={b} span={spanB} />
      </div>
    </>
  );
}

function PersonChart({ person, span }: { person: Person; span: MatchProp["spanA"] }) {
  return (
    <div>
      <h3>{person.name} <span style={{ color: "var(--muted)", fontWeight: 400, fontFamily: "var(--mono)", fontSize: "0.85rem" }}>{person.birthday}</span></h3>
      <div className="scroll-x">
        <table className="data">
          <thead>
            <tr><th>Body</th><th>Sidereal position</th><th>Birth star</th><th className="num">Motion</th></tr>
          </thead>
          <tbody>
            {span.chart.placements.map((p) => {
              const nk = nakshatraOf(p.lon);
              return (
                <tr key={p.body}>
                  <td>{BODY_GLYPH[p.body]} {p.body}</td>
                  <td>{formatDegree(p.deg)} {SIGN_GLYPH[p.sign]} {SIGNS[p.sign]} <span style={{ color: "var(--muted)" }}>({RASI[p.sign]})</span></td>
                  <td>{nk.info.name} <span style={{ color: "var(--muted)" }}>pada {nk.pada}</span></td>
                  <td className="num">{p.retro ? "℞ " : ""}{p.speed.toFixed(2)}°/d</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <h4 style={{ marginTop: "0.9rem" }}>Birth star detail</h4>
      <table className="data">
        <tbody>
          <tr><th>Janma nakshatra</th><td>{span.likeliest.nakshatra.name} (pada {span.likeliest.pada})</td></tr>
          <tr><th>Lord</th><td>{span.likeliest.nakshatra.lord}</td></tr>
          <tr><th>Gana</th><td>{GANA_LABEL[span.likeliest.nakshatra.gana]}</td></tr>
          <tr><th>Yoni</th><td>{YONI_LABEL[span.likeliest.nakshatra.yoni]} ({span.likeliest.nakshatra.yoniGender})</td></tr>
          <tr><th>Nadi</th><td>{NADI_LABEL[span.likeliest.nakshatra.nadi]}</td></tr>
          <tr><th>Moon that day</th><td>
            moved {span.moonArc.toFixed(2)}°
            {span.stable
              ? " — stayed in one birth star and one rāśi all day"
              : ` — crossed into ${span.states.length} states: ` +
                span.states.map((s) => `${s.nakshatra.name} (${Math.round(s.share * 100)}%)`).join(", ")}
          </td></tr>
        </tbody>
      </table>
    </div>
  );
}
