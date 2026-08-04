/**
 * Report.tsx — the whole reading for one pair, as ONE document that reads top to bottom.
 *
 * It answers five questions in the order a person actually asks them:
 *
 *   the score       →  what is it, and is that good
 *   1 · each of us  →  who does this say I am — the two sidereal charts, read one at a time
 *   2 · the two     →  where do our charts touch — synastry, drawn on one shared band
 *   3 · the points  →  where the number came from
 *   4 · how sure    →  what the two unknown birth hours do to all of it
 *
 * ── The rule the whole page is built on ─────────────────────────────────────────────────────────
 *
 * Nothing here is a bare number. A date of birth fixes a DAY, not an instant, so every statement is
 * made 576 times — once for each combination of the two unknown birth hours — and reported with its
 * mean, its give-or-take and how often it held. The score has its exact distribution, each planet
 * has the share of the day it spent in the sign shown, and each connection has how many of the 576
 * charts actually contained it.
 *
 * ── Two systems, and why only one of them scores ────────────────────────────────────────────────
 *
 * The aspect layer was cut from this page once, because a second unscored system beside a scored
 * one invites "is nineteen connections good?" and cannot answer it. It is back because that
 * question now HAS an answer, measured over 20,000 random pairs: every pair has between ten and
 * twenty connections, the median is fifteen, and the count agrees with the eight-test score at 0.03
 * out of 1. The page says so out loud and then shows WHICH connections rather than how many.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { chartAt, julianDay, parseDate, type Body } from "../engine/ephemeris";
import { nakshatraOf, GANA_LABEL, NADI_LABEL, YONI_LABEL } from "../engine/nakshatra";
import { gunaMilan, type KutaSide } from "../engine/kuta";
import {
  matchPair, PERCENTILE_BELOW, PERCENTILE_BELOW_NO_VARNA, type Match, type ScoreOptions,
} from "../engine/score";
import { natalChart, GENERATIONAL, type NatalChart } from "../engine/natal";
import { ASPECTS, standsFor, GRID, PERSONAL } from "../engine/synastry";
import {
  affinity, affinityPercentile, AFFINITY_BELOW, AFFINITY_MIN, AFFINITY_MAX, AFFINITY_STEPS,
  BODY_ORB, type Affinity, type Term,
} from "../engine/affinity";
import {
  explainKuta, explainDosha, birthStarText, starTitle, planetMeta, planetReading, READ_BODIES,
} from "../engine/interpret";
import type { Person } from "../data/people";
import { formatBirthday } from "../App";
import { messageUrl, profileUrl } from "../data/artaquest";
import { Avatar, Meter } from "./bits";
import SkyBand, { type Chip } from "./SkyBand";

/** Trim a trailing .0 — half points are real, "18.0" reads like a rounding artefact. */
const fmt = (n: number) => (n % 1 === 0 ? String(n) : n.toFixed(1));
const pct = (p: number) => Math.round(p * 100);
const deg = (d: number) => `${d.toFixed(1)}°`;

/** How many of the 49 body pairs get a paragraph of their own. Five, with the leftover stated —
 *  five rows that do NOT account for the answer would be an illustration pretending to explain it,
 *  so the share they cover is printed beside them and the rest are one click away, in full. */
const NARRATED = 5;

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

  const charts = useMemo(() => {
    if (!match) return null;
    return {
      a: natalChart(a.birthday, match.spanA.jdEstimate),
      b: natalChart(b.birthday, match.spanB.jdEstimate),
    };
  }, [a.birthday, b.birthday, match?.spanA.jdEstimate, match?.spanB.jdEstimate]);

  const aff = useMemo(() => affinity(a.birthday, b.birthday, { opposite: options.opposite }),
    [a.birthday, b.birthday, options.opposite]);

  if (!match || !charts?.a || !charts.b || !aff) {
    return (
      <div className="panel">
        <p className="error">One of these dates is not a real calendar date, so nothing can be worked out from it.</p>
        <button className="ghost" onClick={onClose}>Back</button>
      </div>
    );
  }

  const excluded = (options.exclude ?? []) as string[];
  const kutas = match.guna.kutas.filter((k) => !excluded.includes(k.key));
  const d = match.distribution;
  const msg = messageUrl(b) ?? messageUrl(a);
  const prof = profileUrl(b);
  const doshas = match.guna.doshas;
  // The five biggest reasons for the score, and what is left over. Five rather than all 49 —
  // and the leftover is stated, not hidden, because five rows that do NOT account for the answer
  // would be an illustration pretending to be an explanation.
  const narrated = aff.terms.slice(0, NARRATED);
  const shown = narrated.reduce((s, t) => s + t.contribution, 0);
  const rest = aff.net - shown;
  const shareShown = Math.round(100 * narrated.reduce((s, t) => s + Math.abs(t.contribution), 0) /
    aff.terms.reduce((s, t) => s + Math.abs(t.contribution), 0));

  // Which chips carry which number, so the chart and the list point at each other.
  const badgesA = new Map<Body, number[]>();
  const badgesB = new Map<Body, number[]>();
  narrated.forEach((c, i) => {
    badgesA.set(c.bodyA, [...(badgesA.get(c.bodyA) ?? []), i + 1]);
    badgesB.set(c.bodyB, [...(badgesB.get(c.bodyB) ?? []), i + 1]);
  });

  const chipsFor = (chart: NatalChart, badges: Map<Body, number[]>): Chip[] =>
    chart.bodies.map((x) => ({
      body: x.body, lon: x.lon, retro: x.retro,
      badges: badges.get(x.body),
      faint: !badges.has(x.body),
    }));

  const fullMarks = kutas.filter((k) => k.points >= k.maxPoints);
  const noMarks = kutas.filter((k) => k.points <= 0);

  return (
    <div className="panel report">
      <div className="report-head">
        <Avatar person={a} />
        <Avatar person={b} />
        <h2 className="names" ref={heading} tabIndex={-1}>{a.name} &amp; {b.name}</h2>
        <button className="ghost" onClick={onClose}>Close</button>
      </div>

      {/* ── the answer ───────────────────────────────────────────────────────────────────── */}
      <Fit aff={aff} a={a.name} b={b.name} hero />

      <p className="lede">
        This page shows the whole of its working. Below: each chart on its own, then the two laid
        over each other with the five biggest reasons for that number, and then an older tradition's
        entirely separate answer — which, measured over 20,000 random pairs, agrees with this one
        almost not at all. Every number was worked out{" "}
        <strong>{GRID} × {GRID} = {GRID * GRID} times</strong>, once for each combination of the two
        unknown birth hours, and is given with how far it moved.
      </p>

      {/* ── 1 · the two charts, one at a time ────────────────────────────────────────────── */}
      <Section n={1} title="Each of them, on their own">
        <p className="say">
          A birth date places every planet in one of the twelve signs. It does not place them in
          houses, and it does not say which sign was rising — those turn a full circle every day, so
          from a date alone they are not approximate, they are simply unknown. Nothing below quietly
          fills them in. What is here is the layer a date really settles.
        </p>
        <PersonChart person={a} chart={charts.a} span={match.spanA} tone="a" />
        <PersonChart person={b} chart={charts.b} span={match.spanB} tone="b" />
      </Section>

      {/* ── 2 · the two charts together ──────────────────────────────────────────────────── */}
      <Section n={2} title="How the two charts fit">
        <p className="say">
          Now both on one line. {a.name}'s bodies sit above it and {b.name}'s below, so where a gold
          label stands directly over a blue one, those two were in the same part of the sky. The
          other connections are fixed distances apart — a quarter of the way round, a third, or
          right across from each other.
        </p>
        <SkyBand
          above={chipsFor(charts.a, badgesA)}
          below={chipsFor(charts.b, badgesB)}
          label={`${a.name}'s planets above the twelve signs and ${b.name}'s below them, ` +
            `with the ${narrated.length} strongest connections numbered`}
        />
        <p className="legend-note">
          <span className="key-a">{a.name}</span>
          <span className="key-b">{b.name}</span>
          <span className="dim">◄ appearing to move backwards · faded = making no connection · numbers match the list below</span>
        </p>

        <p className="say">
          Below are the <strong>five biggest reasons</strong> for that number, out of{" "}
          {aff.terms.length}. They are {shareShown}% of it; everything else put together comes to{" "}
          {rest >= 0 ? "+" : ""}{rest.toFixed(3)}. Each line is one of {a.name}'s bodies against one
          of {b.name}'s, the angle between them averaged over the {GRID * GRID} charts, and what
          that angle added or took away.
        </p>
        {narrated.map((t, i) => (
          <ReasonCard key={`${t.bodyA}-${t.bodyB}`} t={t} n={i + 1} a={a.name} b={b.name}
            // What an angle means is the same wherever it turns up, so it is explained the FIRST
            // time and not again. Five paragraphs each ending in the same stock sentence read as a
            // form letter, and a reader stops seeing the part that IS about them.
            explain={narrated.findIndex((x) => x.nearest.kind === t.nearest.kind) === i} />
        ))}

        <details className="working">
          <summary>All {aff.terms.length} pairs, and where every number came from</summary>
          <p className="say dim">
            <b>How the number is made.</b> Each of {a.name}'s seven bodies is compared with each of{" "}
            {b.name}'s. For every one of the {GRID * GRID} charts the angle between them is measured,
            and scored against the five angles the tradition names, weighted by how much each body
            is said to matter and by <strong>how firmly the two dates pin that angle down</strong>.
            The {aff.terms.length} results below are averaged over all {GRID * GRID} charts and add
            up to the number above exactly — no remainder, nothing rounded away.
          </p>
          <p className="say dim">
            <b>What is a choice and what is a measurement.</b> Which angles are called easy or hard
            comes from the tradition, and so does how close still counts as close — each body has its
            own allowance ({PERSONAL.map((x) => `${x} ${BODY_ORB[x]}°`).join(", ")}), and two bodies
            are allowed the average of theirs. How much each of them <em>matters</em> is our choice;
            the sources rank them but never number them. All of that is a convention. The one
            measured thing is the percentile: where this pair falls among 20,000 randomly paired
            dates put through exactly the same arithmetic.
          </p>
          <div className="scroll-x">
            <table className="data">
              <thead>
                <tr>
                  <th>{a.name}</th><th>{b.name}</th><th>Angle</th>
                  <th className="num">Apart</th><th className="num">Sure</th>
                  <th className="num">Added</th>
                </tr>
              </thead>
              <tbody>
                {aff.terms.map((t, i) => (
                  <tr key={i} className={i < NARRATED ? "lead" : undefined}>
                    <td>{t.bodyA}</td>
                    <td>{t.bodyB}</td>
                    <td>{angleName(t.nearest.kind)}</td>
                    <td className="num">{deg(t.separation)} ± {deg(t.spread)}</td>
                    <td className="num">{pct(t.confidence)}%</td>
                    <td className="num">{t.contribution >= 0 ? "+" : ""}{t.contribution.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="say dim">
            "Apart" is the angle between the two, averaged over the {GRID * GRID} charts, with how
            far it wanders across them. "Sure" is how firmly the two dates settle it — a body that
            barely moves in a day is near 100%, the Moon is not, and anything unsure counts for
            proportionally less. "Added" is what the pair put into the total, and these{" "}
            {aff.terms.length} numbers sum to it exactly.
          </p>
        </details>
      </Section>

      {/* ── 3 · where the score came from ────────────────────────────────────────────────── */}
      <Section n={3} title="A second, older answer — and it disagrees">
        <p className="say">
          {kutas.length} old tests compare where the two Moons sat — and nothing else. Not the Sun,
          not the angles above, nothing but the Moon. It is a completely separate tradition with a
          completely separate answer, and across 20,000 random pairs the two line up at{" "}
          <strong>0.01 out of 1</strong>: knowing one tells you nothing about the other. Both are
          shown because that disagreement is the most useful thing either of them says. The eight
          are worth different amounts, drawn here to scale: the three heaviest carry {6 + 7 + 8} of
          the {match.maxScore} points between them, as much as all the others together.
        </p>
        <Anatomy kutas={kutas} />
        <p className="say">
          {fullMarks.length > 0
            ? <>Full marks on {list(fullMarks.map((k) => k.name.toLowerCase()))}. </>
            : <>Nothing scored full marks. </>}
          {noMarks.length > 0
            ? <>Nothing at all on {list(noMarks.map((k) => k.name.toLowerCase()))}. </>
            : <>Every test put something on the board. </>}
          The rest landed in between.
        </p>

        {match.guna.orderMatters && (
          <p className="say dim">
            Three of these were written for a groom and a bride and answer differently depending
            which way round you read them. Nobody said who is who, so both ways are worked out and
            averaged: {fmt(match.guna.forward.total)} with {a.name} first,{" "}
            {fmt(match.guna.reverse.total)} with {b.name} first.
          </p>
        )}

        <details className="working">
          <summary>All {kutas.length} tests, one at a time</summary>
          {kutas.map((k, i) => (
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
                  {fmt(k.reversePoints)} with {b.name} first — the average is used.
                </span>
              )}
            </div>
          ))}
        </details>

        <Landscape table={excluded.length ? PERCENTILE_BELOW_NO_VARNA : PERCENTILE_BELOW}
          index={Math.round(d.expected)}
          label={`Distribution of the older score across random pairs; this pair scores ${fmt(d.expected)}`} />
        <div className="row total">
          <strong>Total</strong>
          <strong>
            {fmt(d.expected)} / {match.maxScore} — {match.band.label}
            {!match.certain && ` (${fmt(d.interval.lo)}–${fmt(d.interval.hi)})`}
          </strong>
        </div>
      </Section>

      {/* ── 4 · how sure ─────────────────────────────────────────────────────────────────── */}
      <Section n={4} title="How sure that older answer is">
        {match.certain ? (
          <p className="say">
            Both Moons stayed in one birth star and one sign for the whole of their birth days, so
            not knowing what time of day either was born changes this older score not at all. That
            is as firm as a reading from dates alone can be — and rarer than you would think.
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
                      <td className="num">{pct(o.probability)}%</td>
                      <td className="num">{fmt(o.score)}</td>
                      <td>{o.labelA}</td>
                      <td>{o.labelB}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="say">
              The same thing hour by hour — the {GRID * GRID} charts, drawn. Every cell is one
              combination of birth hours, {a.name} down the side and {b.name} across the top,
              midnight to midnight, shaded by the score it gives. The blocks are where the answer
              changes.
            </p>
            <HourGrid a={a} b={b} match={match} options={options} />
          </>
        )}
      </Section>

      {doshas.length > 0 && (
        <Section n={5} title="Warnings the tradition raises">
          {doshas.map((x) => (
            <div key={x.key} className="note">
              <strong>{x.name}{x.cancelled ? " — traditionally set aside" : ""}</strong>
              {explainDosha(x)}
            </div>
          ))}
        </Section>
      )}

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

/** "a, b and c" — an Oxford-comma-free list, because these are read aloud in prose. */
function list(items: string[]): string {
  if (items.length <= 1) return items[0] ?? "";
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
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
 * One person's chart, and what it is said to suggest.
 *
 * Five bodies get a paragraph. Jupiter and Saturn are drawn and make connections but get no
 * character reading: Jupiter holds a sign for about a year, Saturn for two and a half, so a
 * paragraph about them is a paragraph about everybody born that year. The three slowest are named
 * with their windows and left at that.
 */
function PersonChart({ person, chart, span, tone }: {
  person: Person; chart: NatalChart; span: Match["spanA"]; tone: "a" | "b";
}) {
  const star = birthStarText(span.likeliest.nakshatra.index);
  const titles = span.states.map((s) => s.nakshatra.index);
  const ambiguous = titles.some((t, i) => titles.indexOf(t) !== i);
  const chips: Chip[] = chart.bodies.map((x) => ({
    body: x.body, lon: x.lon, retro: x.retro, faint: !READ_BODIES.includes(x.body),
  }));
  /** The sign, plus the other one when the date genuinely does not settle it. Used everywhere a
   *  placement is printed — including the slow bodies in the fold, which cross boundaries too. */
  const signPhrase = (body: Body) => {
    const row = chart.byBody[body];
    if (row.settled) return row.signName;
    const other = row.chances.filter((c) => c.sign !== row.sign)
      .map((c) => `${c.signName} for ${pct(c.share)}% of that day`).join(", ");
    return `${row.signName} — though the date does not settle it: ${other}`;
  };

  return (
    <div className={`who-chart ${tone}`}>
      <h4>{person.name}</h4>
      <span className="born">born {formatBirthday(person.birthday)}</span>
      <SkyBand above={chips} tone={tone}
        label={`${person.name}'s planets across the twelve signs`} />
      <p className="legend-note">
        <span className="dim">
          The twelve signs, cut open at the start of Aries and laid flat. ◄ means the planet was
          appearing to move backwards against the stars — the Earth overtaking it, not the planet
          turning round.
        </span>
      </p>

      {READ_BODIES.map((body) => {
        const row = chart.byBody[body as Body];
        const meta = planetMeta(body);
        if (!row || !meta) return null;
        return (
          <p className="say" key={body}>
            <strong>{meta.opens} — {body} in {row.signName}
              {row.retro ? ", moving backwards" : ""}.</strong>{" "}
            {planetReading(body, row.sign)}
            {!row.settled && (
              <span className="dim">
                {" "}This one is not settled by the date: {row.chances.map((c) => `${c.signName} for ${pct(c.share)}% of that day`)
                  .join(", ")}. The reading above is the likelier of them.
              </span>
            )}
          </p>
        );
      })}

      <details className="working">
        <summary>The rest of {person.name}'s chart</summary>
        <p className="say dim">
          <strong>Jupiter in {signPhrase("Jupiter")}</strong> — where they take chances — and{" "}
          <strong>Saturn in {signPhrase("Saturn")}</strong> — what they take seriously.
          Jupiter holds one sign for about a year and Saturn for two and a half, so these are shared
          with most people born around the same time. They still make connections with another
          chart, which is why they are drawn.
        </p>
        <p className="say dim">
          {GENERATIONAL.map((g) => `${g.body} in ${signPhrase(g.body)}`).join("; ")} —
          these three hold a sign for {GENERATIONAL.map((g) => g.years).join(", ")} respectively, so
          they describe a generation rather than a person, and get no reading here.
        </p>
        {star && (
          <p className="say">
            <strong>{star.title}</strong> — their birth star, one of the 27 equal stretches of sky
            the Moon passes through each month, and the thing the eight tests below actually read.
            {" "}{star.summary} {star.inRelationships}
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
                    `(${pct(s.share)}%)`).join(", ")}
            </td></tr>
          </tbody>
        </table>
      </details>
    </div>
  );
}

/** The five angles, named the way the page names them. */
export function angleName(kind: string): string {
  return kind === "together" ? "same place" : kind === "opposite" ? "opposite" : `a ${kind}`;
}

/**
 * THE SCORE, and the two piles it is made of.
 *
 * Shown as a percentile because the raw scale is meaningless to anybody, and with a BAND because
 * the two unknown birth hours move it about as much as the whole difference between one couple and
 * another — measured: the band a pair spans across its own 576 charts has a median width of
 * 0.048 against a population spread of 0.057. Two pairs whose bands overlap cannot be told apart
 * from dates alone by any model at all. That is the ceiling, and it is stated rather than dodged.
 *
 * Ease and friction are drawn separately and never quietly subtracted. The tradition has said for
 * two thousand years which angles are easy and which are hard; it has never once said how many easy
 * ones cancel a hard one. Every compatibility percentage ever published nets them anyway, and that
 * undisclosed exchange rate is the largest invented number in the genre. Here it is one for one,
 * said out loud, and measured to barely matter.
 */
function Fit({ aff, a, b, hero }: { aff: Affinity; a: string; b: string; hero?: boolean }) {
  const p = affinityPercentile(aff.net);
  const lo = affinityPercentile(aff.spread.lo);
  const hi = affinityPercentile(aff.spread.hi);
  const settled = hi - lo <= 12;
  const peak = Math.max(aff.ease, aff.friction, 1e-9);
  return (
    <div className={`fit${hero ? " hero-fit" : ""}`}>
      <div className="fit-head">
        <span className={`num tone-${p >= 75 ? "high" : p >= 40 ? "mid" : "low"}`}>
          {p}<small>in 100</small>
        </span>
        <p className="txt">
          Putting every angle between {a}'s seven bodies and {b}'s through the tradition's own rules,
          this pair comes out <strong>higher than {p} in 100</strong> randomly paired dates.{" "}
          {settled
            ? <>The two unknown birth times barely move it — anywhere from {lo} to {hi} in 100.</>
            : <>The two unknown birth times move it a long way: anywhere from{" "}
              <strong>{lo}</strong> to <strong>{hi}</strong> in 100, and nothing in the dates can
              narrow that.</>}
        </p>
      </div>

      <Landscape table={AFFINITY_BELOW}
        index={Math.round(((aff.net - AFFINITY_MIN) / (AFFINITY_MAX - AFFINITY_MIN)) * (AFFINITY_STEPS - 1))}
        label={`Where this pair falls among 20,000 randomly paired dates: higher than ${p} in 100`} />

      <div className="piles">
        <span className="pile">
          <span className="lbl">what the tradition calls easy</span>
          <span className="bar ease"><i style={{ width: `${(aff.ease / peak) * 100}%` }} /></span>
          <span className="v">{aff.ease.toFixed(3)}</span>
        </span>
        <span className="pile">
          <span className="lbl">what it calls hard</span>
          <span className="bar friction"><i style={{ width: `${(aff.friction / peak) * 100}%` }} /></span>
          <span className="v">{aff.friction.toFixed(3)}</span>
        </span>
      </div>
      <p className="legend-note">
        <span className="dim">
          These two are kept apart on purpose. The tradition says which angles are easy and which
          are hard; it has never said how many easy ones cancel a hard one, so any single number has
          to invent that exchange rate. This one uses one for one — and changing it by half or by
          double barely moves who ranks above whom.
        </span>
      </p>
    </div>
  );
}

/** One reason for the score: what the angle is, what the tradition makes of it, and the arithmetic. */
function ReasonCard({ t, n, a, b, explain }: {
  t: Term; n: number; a: string; b: string; explain: boolean;
}) {
  const prose = ASPECTS.find((x) => x.kind === t.nearest.kind);
  const sure = t.confidence > 0.97;
  return (
    <div className={`conn ${t.contribution >= 0 ? "good" : "hard"}`}>
      <p className="say">
        <span className="conn-n">{n}</span>
        <strong>{a}'s {t.bodyA} {prose?.joins ?? "sits near"} {b}'s {t.bodyB}.</strong>{" "}
        That is {standsFor(t.bodyA, a)}, and {standsFor(t.bodyB, b)}.
        {explain && prose && ` ${prose.means}`}
      </p>
      <p className="say dim conn-work">
        {deg(t.separation)} apart {sure ? "" : `— give or take ${deg(t.spread)} — `}on average
        across the {GRID * GRID} charts, which is {t.nearest.off < 1 ? "as near as makes no odds to"
          : `${deg(t.nearest.off)} from`} {angleName(t.nearest.kind)}.{" "}
        {sure
          ? <>The dates settle this one.</>
          : <>The dates leave it {pct(1 - t.confidence)}% open, so it counts for proportionally
            less.</>}{" "}
        It {t.contribution >= 0 ? "added" : "took away"}{" "}
        <strong>{Math.abs(t.contribution).toFixed(3)}</strong>.
      </p>
    </div>
  );
}

/**
 * Where this pair lands among all pairs: the measured distribution as thin bars, with this pair's
 * bar picked out. The picture behind every "higher than N in 100" sentence — the percentile stops
 * being a claim and becomes a place you can see.
 */
function Landscape({ table, index, label }: { table: number[]; index: number; label: string }) {
  // The table is cumulative ("share scoring below n"), so differencing gives the share AT each
  // step: shares[i] = table[i+1] − table[i]. Bar i IS step i — this was once off by one in both
  // directions at once, marker and tooltip disagreeing with each other.
  const shares = table.slice(1).map((v, i) => Math.max(0, v - table[i]));
  const peak = Math.max(...shares, 1);
  const at = Math.max(0, Math.min(shares.length - 1, index));
  return (
    <span className="landscape" role="img" aria-label={label}>
      {shares.map((share, i) => (
        <i key={i} className={i === at ? "here" : ""}
          // The marked bar keeps its own floor: at a rare score the true share is ~0, and a 1px
          // sliver is not a marker.
          style={{ height: `${i === at ? Math.max(18, (share / peak) * 100) : share > 0 ? Math.max(9, (share / peak) * 100) : 3}%` }}
          title={`about ${share} in 100 random pairs land here`} />
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
 * The score's interval is computed EXACTLY — by enumerating the handful of (birth star, sign,
 * mid-sign half) states each day holds, not by sampling this grid. (Checked: the exact method
 * agrees with a 240×240 sweep to 0.15 percentage points, and a 24×24 sample is measurably worse,
 * because a score JUMPS at a boundary and sampling misses where the boundary falls. The synastry
 * section above reports the grid directly, because an angle is smooth and 576 samples of it are
 * as good as the exact area — checked, to within 1.9 points of probability.) This picture exists
 * because it is the legible answer to "how much does the missing hour matter".
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
