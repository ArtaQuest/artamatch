/**
 * Report.tsx — the whole reading for one pair, as ONE short document.
 *
 * It answers four questions in the order people ask them, and stops:
 *
 *   the score        →  what is it, and is that good
 *   1 · the points   →  where each point came from
 *   2 · how sure     →  what the unknown birth hours do to it
 *   3 · the two      →  who these people are, and what the tradition warns about
 *
 * It got here by deletion. It was once four tabs; then six sections, four diagrams and 1,972 words
 * — twelve phone screens. The sky ruler went because the score depends only on the RELATIONSHIP
 * between the two Moons, never their absolute positions, so it drew data no test reads; the test
 * cards state the same thing in words, more precisely. The per-test rule and evidence went behind
 * "show the working" — still there, still checkable, no longer shouting over the answer.
 *
 * Three diagrams survive because each answers a different question and none repeats a number:
 * the landscape strip (is this good), the anatomy bar (why this number), the hour grid (where the
 * range comes from).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SIGNS, chartAt, julianDay, parseDate } from "../engine/ephemeris";
import { nakshatraOf, GANA_LABEL, NADI_LABEL, YONI_LABEL } from "../engine/nakshatra";
import { gunaMilan, type KutaSide } from "../engine/kuta";
import {
  matchPair, PERCENTILE_BELOW, PERCENTILE_BELOW_NO_VARNA, type Match, type ScoreOptions,
} from "../engine/score";
import { explainKuta, explainDosha, birthStarText, moonSignText, starTitle } from "../engine/interpret";
import type { Person } from "../data/people";
import { messageUrl, profileUrl } from "../data/artaquest";
import { Avatar, Meter } from "./bits";

/** Trim a trailing .0 — half points are real, "18.0" reads like a rounding artefact. */
const fmt = (n: number) => (n % 1 === 0 ? String(n) : n.toFixed(1));

export default function Report({ a, b, options, onClose }: {
  a: Person; b: Person; options: ScoreOptions; onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const match = matchPair(a.birthday, b.birthday, options);

  // Opening a reading replaces the whole right-hand column. Without this, focus fell to <body>:
  // a screen-reader user activated a row, the app's entire output appeared, and nothing was
  // announced. Focusing the heading names the pair and starts the reading cursor at its top.
  useEffect(() => { heading.current?.focus(); }, [a.id, b.id]);

  // Escape closes — on a phone the only other exit is thousands of pixels up.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  /** A link that reproduces this reading anywhere: it carries the two names and dates — inputs,
   *  never conclusions — so the receiving browser works the whole thing out itself. */
  const shareReading = useCallback(() => {
    const u = new URL(window.location.href);
    u.search = "";
    u.searchParams.set("n", a.name); u.searchParams.set("b", a.birthday);
    u.searchParams.set("n2", b.name); u.searchParams.set("b2", b.birthday);
    const done = () => { setCopied(true); setTimeout(() => setCopied(false), 2500); };
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(u.toString()).then(done, done);
    else { window.prompt("Copy this link", u.toString()); done(); }
  }, [a, b]);

  if (!match) {
    return (
      <div className="panel">
        <p className="error">One of these dates is not a real calendar date, so nothing can be worked out from it.</p>
        <button className="ghost" onClick={onClose}>Back</button>
      </div>
    );
  }

  const excluded = (options.exclude ?? []) as string[];
  const shown = match.guna.kutas.filter((k) => !excluded.includes(k.key));
  const d = match.distribution;
  const msg = messageUrl(b) ?? messageUrl(a);
  const prof = profileUrl(b);
  const doshas = match.guna.doshas;
  const sameMoonSign = match.spanA.likeliest.rasi === match.spanB.likeliest.rasi;
  const sharedSign = sameMoonSign ? moonSignText(match.spanA.likeliest.rasi) : null;

  return (
    <div className="panel report">
      <div className="report-head">
        <Avatar person={a} />
        <Avatar person={b} />
        <h2 className="names" ref={heading} tabIndex={-1}>{a.name} &amp; {b.name}</h2>
        <button className="ghost" onClick={onClose}>Close</button>
      </div>

      {/* ── the answer ───────────────────────────────────────────────────────────────────── */}
      <div className="hero">
        <span className={`num tone-${match.band.tone}`}>
          {fmt(d.expected)}
          <small>out of {match.maxScore}</small>
        </span>
        <span>
          <span className="verdict">{match.band.label}</span>
          <span className="because">
            Higher than <strong>{Math.min(99, match.percentile)} in 100</strong> randomly paired
            dates. {match.certain
              ? "The two dates settle this outright — no birth time needed."
              : <>Nobody knows what time of day either was born, so the honest answer is a range:
                nine times in ten it lands between <strong>{fmt(d.interval.lo)}</strong> and{" "}
                <strong>{fmt(d.interval.hi)}</strong>.</>}
          </span>
          <Landscape score={d.expected} excluded={excluded.length > 0} />
        </span>
      </div>

      {/* ── 1 · where the points came from ───────────────────────────────────────────────── */}
      <Section n={1} title="Where the points came from">
        <p className="say">
          {shown.length} old tests compare where the two Moons sat — nothing else about the two
          people enters the score. They are worth different amounts, drawn here to scale: the three
          heaviest carry {6 + 7 + 8} of the {match.maxScore} points between them, as much as all
          the others put together.
        </p>
        <Anatomy kutas={shown} />

        {match.guna.orderMatters && (
          <p className="say dim">
            Three of these were written for a groom and a bride and answer differently depending
            which way round you read them. Nobody said who is who, so both ways are worked out and
            averaged: {fmt(match.guna.forward.total)} with {a.name} first,{" "}
            {fmt(match.guna.reverse.total)} with {b.name} first.
          </p>
        )}

        {shown.map((k, i) => (
          <div className="kuta" key={k.key}>
            <div className="kuta-head">
              <span className="nm"><i>{i + 1}</i>{k.name}</span>
              <span className={`pts ${k.points >= k.maxPoints ? "tone-high" : k.points <= 0 ? "tone-low" : ""}`}>
                {fmt(k.points)} / {k.maxPoints}
              </span>
            </div>
            <Meter value={k.points} max={k.maxPoints} gold={k.points > 0} />
            <span className="says">{k.measures} {explainKuta(k)}</span>
            {/* The rule and the values it read stay one click away rather than gone: eight tests
                × three dense paragraphs buried the answer under its own footnotes. */}
            <details className="working">
              <summary>Show the working</summary>
              <span className="detail"><b>What was read:</b> {k.evidence}</span>
              <span className="detail"><b>How it is scored:</b> {k.rule}</span>
              {k.forwardPoints !== k.reversePoints && (
                <span className="detail">
                  <b>Order matters here:</b> {fmt(k.forwardPoints)} with {a.name} first,{" "}
                  {fmt(k.reversePoints)} with {b.name} first — the average is used.
                </span>
              )}
            </details>
          </div>
        ))}

        <div className="row total">
          <strong>Total</strong>
          <strong>
            {fmt(d.expected)} / {match.maxScore} — {match.band.label}
            {!match.certain && ` (${fmt(d.interval.lo)}–${fmt(d.interval.hi)})`}
          </strong>
        </div>
      </Section>

      {/* ── 2 · how sure ─────────────────────────────────────────────────────────────────── */}
      <Section n={2} title="How sure this is">
        {match.certain ? (
          <p className="say">
            Both Moons stayed in one birth star and one sign for the whole of their birth days, so
            not knowing what time of day either was born changes nothing at all. This is as firm as
            a reading from dates alone can be.
          </p>
        ) : (
          <>
            <p className="say">
              The Moon moves about 13 degrees a day — far enough to land in a different birth star
              between breakfast and bedtime. Without the hour of birth there is more than one honest
              answer, so here is every one the two dates allow:
            </p>
            <div className="scroll-x">
              <table className="data">
                <thead>
                  <tr>
                    <th>Chance</th><th className="num">Score</th>
                    <th>{a.name}'s birth star</th><th>{b.name}'s birth star</th>
                  </tr>
                </thead>
                <tbody>
                  {d.outcomes.map((o, i) => (
                    <tr key={i} className={i === 0 ? "lead" : undefined}>
                      <td className="num">{Math.round(o.probability * 100)}%</td>
                      <td className="num">{fmt(o.score)}</td>
                      <td>{o.labelA}</td>
                      <td>{o.labelB}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="say">
              The same thing hour by hour. Every cell is one combination of birth hours —{" "}
              {a.name} down the side, {b.name} across the top, midnight to midnight — shaded by the
              score it gives. The blocks are where the answer changes.
            </p>
            <HourGrid a={a} b={b} match={match} options={options} />
          </>
        )}
      </Section>

      {/* ── 3 · the caveats and the people ───────────────────────────────────────────────── */}
      {doshas.length > 0 && (
        <Section n={3} title="Warnings the tradition raises">
          {doshas.map((x) => (
            <div key={x.key} className="note">
              <strong>{x.name}{x.cancelled ? " — traditionally set aside" : ""}</strong>
              {explainDosha(x)}
            </div>
          ))}
        </Section>
      )}

      <Section n={doshas.length > 0 ? 4 : 3} title="The two of them">
        {sameMoonSign && sharedSign && (
          <p className="say">
            <strong>Both have the Moon in {SIGNS[match.spanA.likeliest.rasi]} — {sharedSign.title}.</strong>{" "}
            {sharedSign.style} They share this, which the fifth test reads as minds that work the
            same way.
          </p>
        )}
        <div className="cols">
          <PersonPanel person={a} span={match.spanA} showMoonSign={!sameMoonSign} />
          <PersonPanel person={b} span={match.spanB} showMoonSign={!sameMoonSign} />
        </div>
      </Section>

      <div className="row actions">
        {msg && <a href={msg} target="_blank" rel="noreferrer"><button>Message on ArtaQuest</button></a>}
        {prof && <a href={prof} target="_blank" rel="noreferrer"><button className="ghost">View profile</button></a>}
        <button className="ghost" onClick={shareReading}>
          {copied ? "Link copied" : "Copy a link to this reading"}
        </button>
        <button className="ghost" onClick={onClose}>Back to the ranking</button>
      </div>
      <p className="panel-note">
        The link carries only the two names and dates — whoever opens it works everything out fresh.
      </p>
    </div>
  );
}

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="sec">
      <h3><i>{n}</i>{title}</h3>
      {children}
    </section>
  );
}

/**
 * Where this pair lands among all pairs: the measured distribution as thin bars, with this pair's
 * bar picked out. The picture behind every "higher than N in 100" sentence — the percentile stops
 * being a claim and becomes a place you can see.
 */
function Landscape({ score, excluded }: { score: number; excluded: boolean }) {
  const table = excluded ? PERCENTILE_BELOW_NO_VARNA : PERCENTILE_BELOW;
  // The table is cumulative ("share scoring below n"), so differencing gives the share AT each
  // score: shares[i] = table[i+1] − table[i] = P(score === i). Bar i IS score i — this was once
  // off by one in both directions at once, marker and tooltip disagreeing with each other.
  const shares = table.slice(1).map((v, i) => Math.max(0, v - table[i]));
  const peak = Math.max(...shares, 1);
  const at = Math.max(0, Math.min(shares.length - 1, Math.round(score)));
  return (
    <span className="landscape" role="img"
      aria-label={`Distribution of scores across random pairs; this pair scores ${fmt(score)}`}>
      {shares.map((share, i) => (
        <i key={i} className={i === at ? "here" : ""}
          // The marked bar keeps its own floor: at a rare score the true share is ~0, and a 1px
          // sliver is not a marker.
          style={{ height: `${i === at ? Math.max(18, (share / peak) * 100) : share > 0 ? Math.max(9, (share / peak) * 100) : 3}%` }}
          title={`Score ${i}: about ${share} in 100 random pairs`} />
      ))}
    </span>
  );
}

/**
 * The anatomy of the score: 36 = 1+2+3+4+5+6+7+8, drawn to scale. Each block is one test, as wide
 * as the points it can award and filled as far as the points it did. The total becomes visible
 * arithmetic — you can see that the last three blocks are half the board.
 */
function Anatomy({ kutas }: { kutas: Match["guna"]["kutas"] }) {
  // Every number here is repeated accessibly in the per-test list below, so to a screen reader the
  // drawing is decorative — otherwise it dumps sixteen context-free numbers into the tree.
  return (
    <div className="anatomy" aria-hidden="true">
      <span className="host">
        <span className="bar">
          {kutas.map((k, i) => (
            // The 1-point block is only 12px wide on a phone and 21px on desktop, so a two- or
            // three-character label cannot fit and gets sheared into a WRONG number ("0.5" showing
            // as "0"). Measured, not guessed: below three characters of room, the figure is left to
            // the meter and the card underneath, which both state it exactly.
            <span key={k.key} className="seg" data-narrow={k.maxPoints <= 1 || undefined}
              style={{ flexGrow: k.maxPoints }}
              title={`Test ${i + 1} · ${k.name} — ${fmt(k.points)} of ${k.maxPoints}. ${k.measures}`}>
              {/* Each number is drawn twice, the light copy clipped to the gold fill, so whichever
                  background the digit lands on the readable copy is on top. A single dark copy sat
                  on the dark track whenever a test scored under half — 1.3:1, and "0.5" rendered
                  as "0", a wrong number rather than a missing one. */}
              <b className="lo">{k.points > 0 ? fmt(k.points) : ""}</b>
              <i style={{
                width: `${(k.points / k.maxPoints) * 100}%`,
                ["--segw" as string]: `${(k.maxPoints / k.points) * 100}%`,
              }}>
                <b className="hi">{k.points > 0 ? fmt(k.points) : ""}</b>
              </i>
              <u className={k.points >= k.maxPoints ? "onGold" : ""}>{k.maxPoints}</u>
            </span>
          ))}
        </span>
      </span>
      <span className="key">Inside each block: points earned. Bottom right: points available.</span>
    </div>
  );
}

/**
 * The 24×24 hour grid: every combination of birth hours, shaded by the score it gives.
 *
 * The interval is computed EXACTLY — by enumerating the handful of (birth star, sign, mid-sign
 * half) states each day holds, not by sampling this grid. (Checked: the exact method agrees with a
 * 240×240 sweep to 0.15 percentage points, and a 24×24 sample is measurably worse.) This picture
 * exists because it is the legible answer to "how much does the missing hour matter" — you can see
 * the blocks, and see at a glance whether it matters at all.
 */
function HourGrid({ a, b, match, options }: {
  a: Person; b: Person; match: Match; options: ScoreOptions;
}) {
  const grid = useMemo(() => {
    const pa = parseDate(a.birthday), pb = parseDate(b.birthday);
    if (!pa || !pb) return null;
    const excluded = options.exclude ?? [];
    const sideAt = (p: { y: number; m: number; d: number }, h: number): KutaSide => {
      const c = chartAt(julianDay(p.y, p.m, p.d, h + 0.5));
      const moon = c.byBody.Moon;
      return {
        moonLon: moon.lon, nakshatra: nakshatraOf(moon.lon).info, rasi: moon.sign,
        degInSign: moon.deg, marsLon: c.byBody.Mars.lon, venusLon: c.byBody.Venus.lon,
      };
    };
    const sa = Array.from({ length: 24 }, (_, h) => sideAt(pa, h));
    const sb = Array.from({ length: 24 }, (_, h) => sideAt(pb, h));
    const cells: number[][] = [];
    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < 24; i++) {
      const row: number[] = [];
      for (let j = 0; j < 24; j++) {
        const g = gunaMilan(sa[i], sb[j]);
        const v = excluded.length
          ? g.kutas.filter((k) => !excluded.includes(k.key)).reduce((s, k) => s + k.points, 0)
          : g.total;
        row.push(v);
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
      cells.push(row);
    }
    return { cells, lo, hi };
  }, [a.birthday, b.birthday, options]);

  if (!grid) return null;
  const { cells, lo, hi } = grid;
  const span = hi - lo || 1;

  return (
    <div className="hourgrid-wrap">
      <div className="hourgrid" role="img"
        aria-label={`Score for each of the 576 combinations of birth hours, ranging from ${lo} to ${hi} out of ${match.maxScore}`}>
        {cells.map((row, i) => (
          <span className="hrow" key={i}>
            {row.map((v, j) => (
              // Lightness carries the value; the title carries it in words, so nothing here
              // depends on colour alone.
              <i key={j} style={{ opacity: 0.15 + 0.85 * ((v - lo) / span) }}
                title={`${a.name} born ${String(i).padStart(2, "0")}:00–${String(i + 1).padStart(2, "0")}:00, ` +
                  `${b.name} born ${String(j).padStart(2, "0")}:00–${String(j + 1).padStart(2, "0")}:00 → ` +
                  `${fmt(v)} of ${match.maxScore}`} />
            ))}
          </span>
        ))}
      </div>
      <div className="legend">
        <span><i className="dot swatch faint" /> {fmt(lo)} of {match.maxScore}</span>
        <span><i className="dot swatch full" /> {fmt(hi)} of {match.maxScore}</span>
        <span className="dim">576 hour combinations</span>
      </div>
    </div>
  );
}

function PersonPanel({ person, span, showMoonSign }: {
  person: Person; span: Match["spanA"]; showMoonSign: boolean;
}) {
  const star = birthStarText(span.likeliest.nakshatra.index);
  const moonSign = showMoonSign ? moonSignText(span.likeliest.rasi) : null;
  // A day where the Moon changes sign inside one birth star would print the same title twice, so
  // the sign disambiguates when a title repeats.
  const titles = span.states.map((s) => s.nakshatra.index);
  const ambiguous = titles.some((t, i) => titles.indexOf(t) !== i);
  return (
    <div className="who-panel">
      <h4>{person.name}</h4>
      {star && (
        <p className="say">
          <strong>{star.title}</strong> — their birth star, one of the 27 equal stretches of sky the
          Moon passes through each month. {star.summary}
        </p>
      )}
      {/* The rest is a character sketch of one person, on a page about a pair — worth having, not
          worth 800px of the scroll. It was the second-largest block on the page. */}
      <details className="working">
        <summary>More about {person.name}</summary>
        {star && <p className="say dim">{star.inRelationships}</p>}
        {moonSign && (
          <p className="say">
            <strong>Moon in {SIGNS[span.likeliest.rasi]} — {moonSign.title}.</strong> {moonSign.style}
          </p>
        )}
        <table className="data">
          <tbody>
            <tr><th scope="row">Temperament</th><td>{GANA_LABEL[span.likeliest.nakshatra.gana]}</td></tr>
            <tr><th scope="row">Its animal</th><td>{YONI_LABEL[span.likeliest.nakshatra.yoni]}</td></tr>
            <tr><th scope="row">Built</th><td>{NADI_LABEL[span.likeliest.nakshatra.nadi]}</td></tr>
            <tr><th scope="row">Moon that day</th><td>
              moved {span.moonArc.toFixed(1)}°
              {span.stable
                ? " — stayed in one birth star and one sign all day"
                : `, passing through ${span.states.length} readings: ` +
                  span.states.map((s) =>
                    `${starTitle(s.nakshatra.index)}${ambiguous ? ` in ${s.rasiName}` : ""} ` +
                    `(${Math.round(s.share * 100)}%)`).join(", ")}
            </td></tr>
          </tbody>
        </table>
      </details>
    </div>
  );
}
