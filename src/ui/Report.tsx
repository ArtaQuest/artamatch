/**
 * Report.tsx — the whole reading for one pair, as ONE document.
 *
 * There are no tabs. An earlier version hid four fifths of the page behind them, which meant the
 * evidence for a number lived on a different screen from the number. Everything now reads top to
 * bottom in the order a person actually asks: what is the score → how is it built → how sure are we
 * → what did it read → the eight tests one by one → the caveats → who these two are.
 *
 * Three drawn instruments carry the explaining, all linear (never a wheel, a brand rule), all in
 * the two brand colours, and none relying on colour alone — every mark is labelled or titled.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SIGNS, chartAt, julianDay, parseDate } from "../engine/ephemeris";
import { nakshatraOf } from "../engine/nakshatra";
import { gunaMilan, type KutaSide } from "../engine/kuta";
import { GANA_LABEL, NADI_LABEL, YONI_LABEL } from "../engine/nakshatra";
import {
  matchPair, PERCENTILE_BELOW, PERCENTILE_BELOW_NO_VARNA,
  TRADITIONAL_PASS, PASS_RATE, MEDIAN_SCORE, type Match, type ScoreOptions,
} from "../engine/score";
import { explainKuta, explainDosha, birthStarText, moonSignText, starTitle } from "../engine/interpret";
import type { Person } from "../data/people";
import { messageUrl, profileUrl } from "../data/artaquest";
import { Avatar, Meter, RangeBar } from "./bits";

export default function Report({ a, b, options, onClose }: {
  a: Person; b: Person; options: ScoreOptions; onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const match = matchPair(a.birthday, b.birthday, options);

  // Opening a reading replaces the whole right-hand column. Without this, focus fell to <body>:
  // a screen-reader user activated a row, the app's entire output appeared, and nothing was
  // announced and there was nowhere to navigate to. Moving focus to the heading names the pair and
  // puts the reading cursor at its start.
  useEffect(() => {
    heading.current?.focus();
  }, [a.id, b.id]);

  // Escape closes the reading — the only exit was a Close button nearly 7,000px above the fold
  // on a phone.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  /** A link that reproduces this reading anywhere. It carries the two names and dates — inputs,
   *  never conclusions — so the receiving browser computes the whole thing itself. */
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
  const msg = messageUrl(b) ?? messageUrl(a);
  const prof = profileUrl(b);
  const doshas = match.guna.doshas;
  const sameMoonSign = match.spanA.likeliest.rasi === match.spanB.likeliest.rasi;
  const sharedSign = sameMoonSign ? moonSignText(match.spanA.likeliest.rasi) : null;

  return (
    <div className="panel report">
      {/* A real heading, not a styled span: heading navigation used to jump straight from
          "Everyone (3)" to "How the score is built" with nothing saying whose reading this was.
          Not <header>, which would expose a SECOND banner landmark on the page. */}
      <div className="report-head">
        <Avatar person={a} />
        <Avatar person={b} />
        <h2 className="names" ref={heading} tabIndex={-1}>{a.name} &amp; {b.name}</h2>
        <button className="ghost" onClick={onClose}>Close</button>
      </div>

      {/* ── 1 · the answer ───────────────────────────────────────────────────────────────── */}
      <div className="hero">
        <span className={`num tone-${match.band.tone}`}>
          {fmt(match.distribution.expected)}
          <small>out of {match.maxScore}</small>
        </span>
        <span>
          <span className="verdict">
            {match.band.label}
            {!match.certain && (
              <span className="pill soft"
                title={`Nine of every ten birth-time combinations give a score in this range`}>
                {fmt(match.distribution.interval.lo)}–{fmt(match.distribution.interval.hi)} · 90% sure
              </span>
            )}
          </span>
          <span className="because">
            {match.certain ? (
              <>The two dates settle this outright — no birth time needed. Higher than{" "}
              <strong>{Math.min(99, match.percentile)} in 100</strong> randomly paired dates. {match.band.note}</>
            ) : (
              <>Averaged across every birth time the dates allow. Nine times in ten it lands
              between <strong>{fmt(match.distribution.interval.lo)}</strong> and{" "}
              <strong>{fmt(match.distribution.interval.hi)}</strong>; the single most likely reading
              is <strong>{fmt(match.distribution.modal.score)}</strong> at{" "}
              {Math.round(match.confidence * 100)}%. Higher than{" "}
              <strong>{Math.min(99, match.percentile)} in 100</strong> randomly paired dates. {match.band.note}</>
            )}
          </span>
          <Landscape score={match.distribution.expected} excluded={excluded.length > 0} />
        </span>
      </div>

      <p className="lede">
        Where the Moon sat when each of them was born is the whole basis of this.{" "}
        {shown.length === 8 ? "Eight" : "Seven"} old tests compare those two positions, worth{" "}
        {Math.min(...shown.map((k) => k.maxPoints))} to {Math.max(...shown.map((k) => k.maxPoints))}{" "}
        points each and adding up to {match.maxScore}.{" "}
        {excluded.length === 0 && (
          <>The traditional pass mark is {TRADITIONAL_PASS}, but {PASS_RATE} in 100 random pairs
          clear it and the middling pair scores about {MEDIAN_SCORE} — so the percentile above tells
          you far more than the pass mark does.</>
        )}
        {excluded.length > 0 && (
          <>Because one test is switched off, the percentile above is measured against a separately
          calibrated {match.maxScore}-point distribution — not the {36}-point one.</>
        )}
      </p>

      {/* ── 2 · how it is built ──────────────────────────────────────────────────────────── */}
      <Section n={1} title="How the score is built">
        <p className="say">
          {match.maxScore} points split unevenly across {shown.length} tests, drawn here to scale.
          Gold is earned. The three heaviest carry {6 + 7 + 8} points between them — as much as all
          the others put together — so they usually decide the headline.
        </p>
        <Anatomy kutas={shown} />
      </Section>

      {/* ── 3 · how sure ─────────────────────────────────────────────────────────────────── */}
      <Section n={2} title="How sure this is">
        {match.certain ? (
          <p className="say">
            Both Moons stayed in one birth star and one sign for the whole of their birth days, so
            not knowing what time of day either was born changes nothing at all. This is as firm as a
            reading from dates alone can be.
          </p>
        ) : (
          <>
            <p className="say">
              Nobody said what time of day either of them was born, and the Moon moves about 13
              degrees a day — far enough to land in a different birth star. So there is more than one
              honest answer. Every one the two dates allow is listed below, with its chance:
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
                  {match.distribution!.outcomes.map((o, i) => (
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
              Across every birth time the two dates allow the score runs from{" "}
              <strong>{fmt(match.distribution.support.min)}</strong> to{" "}
              <strong>{fmt(match.distribution.support.max)}</strong>, and nine times in ten it lands
              between <strong>{fmt(match.distribution.interval.lo)}</strong> and{" "}
              <strong>{fmt(match.distribution.interval.hi)}</strong>:
            </p>
            <RangeBar min={match.distribution.interval.lo} max={match.distribution.interval.hi}
              value={match.distribution.expected} scaleMin={0} scaleMax={match.maxScore} />

            <p className="say">
              And here is the same thing hour by hour. Every cell is one combination of birth
              hours — {a.name} down the side, {b.name} across the top, midnight to midnight — shaded
              by the score it gives. The blocks are where the answer changes, and their sizes are
              the probabilities in the table above.
            </p>
            <HourGrid a={a} b={b} match={match} options={options} />
          </>
        )}
      </Section>

      {/* ── 4 · what it read ─────────────────────────────────────────────────────────────── */}
      <Section n={3} title="What the tests actually read">
        <p className="say">
          Only the two Moons. This is the whole sky as one strip — 360 degrees, cut into the 12 signs
          (tall ticks) and the 27 equal birth-star stretches (short ticks). Each Moon is marked, and
          the faint band behind it is how far that Moon travelled during the birth day —{" "}
          {match.certain
            ? "here both bands stay inside one stretch all day, which is why the dates settle the answer."
            : "which is exactly where the uncertainty above comes from."}
        </p>
        <MoonRuler match={match} a={a} b={b} />
      </Section>

      {/* ── 5 · the eight tests ──────────────────────────────────────────────────────────── */}
      <Section n={4} title={`The ${shown.length} tests, one by one`}>
        <p className="say">
          Each shows what it read and the rule it applied, so any line can be checked by hand.
        </p>

        {excluded.length > 0 && (
          <p className="panel-note">
            One test is switched off in "What gets counted", and is left out of both this list and
            the total.
          </p>
        )}

        {match.guna.orderMatters && (
          <div className="note">
            <strong>Order matters in this pairing</strong>
            Three of the eight were written for a groom and a bride, and answer differently depending
            which way round you read them. Nobody has said who is who, so both ways are worked out
            and averaged: <strong>{fmt(match.guna.forward.total)}</strong> with {a.name} first,{" "}
            <strong>{fmt(match.guna.reverse.total)}</strong> with {b.name} first. The ranking uses
            the average, because otherwise your list and their list would disagree about the same pair.
          </div>
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
            <span className="detail"><b>What was read:</b> {k.evidence}</span>
            <span className="detail"><b>How it is scored:</b> {k.rule}</span>
            {k.forwardPoints !== k.reversePoints && (
              <span className="detail">
                <b>Order matters here:</b> {fmt(k.forwardPoints)} with {a.name} first,{" "}
                {fmt(k.reversePoints)} with {b.name} first. The average is used.
              </span>
            )}
          </div>
        ))}

        <div className="row total">
          <strong>Total</strong>
          <strong>
          {fmt(match.distribution.expected)} / {match.maxScore} — {match.band.label}
          {!match.certain && ` (${fmt(match.distribution.interval.lo)}–${fmt(match.distribution.interval.hi)})`}
        </strong>
        </div>
      </Section>

      {/* ── 6 · caveats ──────────────────────────────────────────────────────────────────── */}
      {doshas.length > 0 && (
        <Section n={5} title="Warnings the tradition raises">
          {doshas.map((d) => (
            <div key={d.key} className="note">
              <strong>{d.name}{d.cancelled ? " — traditionally set aside" : ""}</strong>
              {explainDosha(d)}
            </div>
          ))}
        </Section>
      )}

      {/* ── 7 · the people ───────────────────────────────────────────────────────────────── */}
      <Section n={doshas.length > 0 ? 6 : 5} title="The two of them">
        {/* When both Moons share a sign the emotional-style paragraph is identical for both, so it
            is said ONCE here rather than printed twice verbatim in adjacent columns. */}
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

/** Trim a trailing .0 — half points are real, but "7.0 / 7" reads like a rounding artefact. */
const fmt = (n: number) => (n % 1 === 0 ? String(n) : n.toFixed(1));

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="sec">
      <h3><i>{n}</i>{title}</h3>
      {children}
    </section>
  );
}

// ════════════════════════════════════════════════════════════════════════════════════════════════
// The instruments
// ════════════════════════════════════════════════════════════════════════════════════════════════

/**
 * Where this pair lands among all pairs: the measured score distribution as a strip of thin bars,
 * with this pair's bar picked out. This is the picture behind every "higher than N in 100" sentence
 * — the percentile stops being a claim and becomes a place you can see.
 */
function Landscape({ score, excluded }: { score: number; excluded: boolean }) {
  const table = excluded ? PERCENTILE_BELOW_NO_VARNA : PERCENTILE_BELOW;
  // The stored table is cumulative ("share scoring below n"), so differencing gives the share AT
  // each score: shares[i] = table[i+1] − table[i] = P(score === i). Bar i IS score i.
  //
  // This was off by one in both directions at once — the marker sat on Math.round(score) − 1 and
  // every tooltip said "score i+1" — so the gold "this pair" bar pointed at the wrong score and
  // the hover text disagreed with the bar it was on. Three reviewers found it independently.
  const shares = table.slice(1).map((v, i) => Math.max(0, v - table[i]));
  const peak = Math.max(...shares, 1);
  const at = Math.max(0, Math.min(shares.length - 1, Math.round(score)));
  return (
    <span className="landscape" role="img"
      aria-label={`Distribution of scores across random pairs; this pair scores ${fmt(score)}`}>
      {shares.map((share, i) => (
        <i key={i} className={i === at ? "here" : ""}
          // The marked bar keeps a floor of its own: at a rare score its true share is ~0, and a
          // 1px sliver is not a marker.
          style={{ height: `${i === at ? Math.max(18, (share / peak) * 100) : share > 0 ? Math.max(9, (share / peak) * 100) : 3}%` }}
          title={`Score ${i}: about ${share} in 100 random pairs`} />
      ))}
    </span>
  );
}

/**
 * The anatomy of the score: 36 = 1+2+3+4+5+6+7+8, drawn to scale. Each block is one test, as wide
 * as the points it can award and filled as far as the points it did. The total becomes visible
 * arithmetic — you can see that the last two blocks are half the board.
 */
function Anatomy({ kutas }: { kutas: Match["guna"]["kutas"] }) {
  // Every number here is repeated accessibly in the per-test list below, so the drawing itself is
  // decorative to a screen reader — otherwise it dumps sixteen context-free numbers into the tree.
  return (
    <div className="anatomy" aria-hidden="true">
      <span className="host">
        <span className="bar">
          {kutas.map((k, i) => (
            <span key={k.key} className="seg" style={{ flexGrow: k.maxPoints }}
              title={`Test ${i + 1} · ${k.name} — ${fmt(k.points)} of ${k.maxPoints}. ${k.measures}`}>
              {/* The earned number is drawn TWICE: once dark, once light, the light copy clipped to
                  the gold fill. Whichever background the digit lands on, the readable copy is the
                  one on top. A single dark copy centred over the whole block sat on the dark track
                  whenever a test scored under half — 1.3:1, and "0.5" rendered as "0", a wrong
                  number rather than a missing one. */}
              <b className="lo">{k.points > 0 ? fmt(k.points) : ""}</b>
              <i style={{
                width: `${(k.points / k.maxPoints) * 100}%`,
                // The clipped copy must be laid out against the SEGMENT's width, not the fill's,
                // or it re-centres inside the fill and the two copies drift apart.
                ["--segw" as string]: `${(k.maxPoints / k.points) * 100}%`,
              }}>
                <b className="hi">{k.points > 0 ? fmt(k.points) : ""}</b>
              </i>
              <u className={k.points >= k.maxPoints ? "onGold" : ""}>{k.maxPoints}</u>
            </span>
          ))}
        </span>
      </span>
      <span className="key">
        Inside each block: points earned. Bottom right: points available.
      </span>
    </div>
  );
}

/**
 * The sky as a ruler: the full 360° band, its 12 signs and 27 birth-star stretches, both Moons
 * marked, and the arc each swept during its birth day. The single picture of what the eight tests
 * read — with the uncertainty drawn on the same axis as the data rather than described separately.
 */
function MoonRuler({ match, a, b }: { match: Match; a: Person; b: Person }) {
  const rows = [
    { span: match.spanA, name: a.name, cls: "a" as const },
    { span: match.spanB, name: b.name, cls: "b" as const },
  ];
  const pct = (lon: number) => `${(lon / 360) * 100}%`;
  return (
    <div className="ruler-wrap">
      <div className="ruler" role="img"
        aria-label={`Where both Moons sat on the 360-degree band, and how far each moved during its birth day`}>
        {Array.from({ length: 27 }, (_, i) => (
          <span key={`n${i}`} className="tick star" style={{ left: pct((i * 360) / 27) }}
            title={starTitle(i)} />
        ))}
        {Array.from({ length: 12 }, (_, i) => (
          <span key={`s${i}`} className="tick sign" style={{ left: pct(i * 30) }} title={SIGNS[i]} />
        ))}
        {rows.map(({ span, name, cls }) => {
          const start = span.moonStartLon;
          const arc = span.moonArc;
          const wraps = start + arc > 360;
          return (
            <span key={cls}>
              <span className={`sweep ${cls}`}
                style={{ left: pct(start), width: wraps ? pct(360 - start) : pct(arc) }}
                title={`${name}'s Moon moved ${arc.toFixed(1)}° during the birth day`} />
              {/* A sweep that runs past 360° continues from the left edge. */}
              {wraps && (
                <span className={`sweep ${cls}`} style={{ left: 0, width: pct((start + arc) % 360) }} />
              )}
              <span className={`moon ${cls}`} style={{ left: pct(span.likeliest.lon) }}
                title={`${name}'s Moon — ${starTitle(span.likeliest.nakshatra.index)}, in ${SIGNS[span.likeliest.rasi]}`} />
            </span>
          );
        })}
      </div>
      <div className="legend">
        <span><i className="dot a" /> {a.name}'s Moon</span>
        <span><i className="dot b" /> {b.name}'s Moon</span>
        <span className="dim">tall ticks: the 12 signs · short ticks: the 27 birth stars</span>
      </div>
    </div>
  );
}

function PersonPanel({ person, span, showMoonSign }: {
  person: Person; span: Match["spanA"]; showMoonSign: boolean;
}) {
  const star = birthStarText(span.likeliest.nakshatra.index);
  const moonSign = showMoonSign ? moonSignText(span.likeliest.rasi) : null;
  return (
    <div className="who-panel">
      <h4>{person.name}</h4>
      {star && (
        <>
          <p className="say"><strong>{star.title}</strong> — their birth star, one of the 27 equal
            stretches of sky the Moon passes through each month.</p>
          <p className="say">{star.summary}</p>
          <p className="say dim">{star.inRelationships}</p>
        </>
      )}
      {moonSign && (
        <p className="say">
          <strong>Moon in {SIGNS[span.likeliest.rasi]} — {moonSign.title}.</strong> {moonSign.style}
        </p>
      )}
      <table className="data">
        <tbody>
          <tr><th>Temperament</th><td>{GANA_LABEL[span.likeliest.nakshatra.gana]}</td></tr>
          <tr><th>Its animal</th><td>{YONI_LABEL[span.likeliest.nakshatra.yoni]}</td></tr>
          <tr><th>Built</th><td>{NADI_LABEL[span.likeliest.nakshatra.nadi]}</td></tr>
          <tr><th>Moon that day</th><td>
            moved {span.moonArc.toFixed(1)}°
            {span.stable
              ? " — stayed in one birth star and one sign all day"
              : `, passing through ${span.states.length} readings: ` +
                span.states.map((s) => `${starTitle(s.nakshatra.index)} (${Math.round(s.share * 100)}%)`).join(", ")}
          </td></tr>
        </tbody>
      </table>
    </div>
  );
}


/**
 * The 24×24 hour grid: every combination of birth hours, shaded by the score it gives.
 *
 * The interval above is computed EXACTLY, by enumerating the handful of (birth star, sign,
 * mid-sign half) states each day contains — not by sampling this grid. (Checked: the exact method
 * agrees with a 240×240 sweep to 0.15 percentage points, and a 24×24 sample is measurably worse.)
 * This picture exists because it is the honest, legible answer to "how much does the missing hour
 * matter" — you can see the blocks, see where the boundaries fall, and see at a glance whether the
 * unknown hour changes anything at all.
 */
function HourGrid({ a, b, match, options }: {
  a: Person; b: Person; match: Match; options: ScoreOptions;
}) {
  const grid = useMemo(() => {
    const pa = parseDate(a.birthday), pb = parseDate(b.birthday);
    if (!pa || !pb) return null;
    const excluded = options.exclude ?? [];
    // 24 hourly sides per person, then 576 cheap arithmetic combinations.
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
              <i key={j}
                // Lightness carries the value; the title carries it in words, so the grid never
                // depends on colour alone.
                style={{ opacity: 0.15 + 0.85 * ((v - lo) / span) }}
                title={`${a.name} born ${String(i).padStart(2, "0")}:00–${String(i + 1).padStart(2, "0")}:00, ` +
                  `${b.name} born ${String(j).padStart(2, "0")}:00–${String(j + 1).padStart(2, "0")}:00 → ` +
                  `${v} of ${match.maxScore}`} />
            ))}
          </span>
        ))}
      </div>
      <div className="legend">
        <span><i className="dot swatch faint" /> {lo} of {match.maxScore}</span>
        <span><i className="dot swatch full" /> {hi} of {match.maxScore}</span>
        <span className="dim">
          {lo === hi
            ? "every hour gives the same answer — the shading is flat because the dates settle it"
            : `576 hour combinations · ${a.name} down the side, ${b.name} across the top`}
        </span>
      </div>
    </div>
  );
}
