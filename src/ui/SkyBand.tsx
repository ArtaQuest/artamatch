/**
 * SkyBand.tsx — the chart, drawn as a straight line rather than a circle.
 *
 * A natal chart is traditionally a wheel. A wheel is a bad drawing for this page and for this
 * input, for two reasons that are worth writing down:
 *
 *   · A wheel's ROTATION carries the houses and the rising sign, and a birth date fixes neither of
 *     them. Drawing the circle anyway would put a real-looking orientation on a chart that has
 *     none, which is the one thing this page must not do.
 *   · A circle on a 360-pixel phone is either illegible or cropped, and the labels collide near
 *     the top and bottom in a way no packing can fix.
 *
 * Cut the circle open at the start of Aries and lay it flat, and both problems go: it is the same
 * twelve signs in the same order, an angle becomes a HORIZONTAL DISTANCE you can measure with your
 * eye, and two people can share one axis so that "in the same place" is literally a chip sitting
 * above a chip.
 *
 * The band MEASURES the width it has been given and draws itself to fit it — never wider. A first
 * version was a fixed 720px inside a horizontal scroller, and on a phone that showed Aries to Leo
 * and hid the rest behind a swipe, which throws away the one thing this drawing is for: seeing both
 * planets and the gap between them at the same time. Narrow just means more lanes, and at that
 * point the sign names go to three letters rather than being sheared by their cells.
 *
 * Whatever the measured width, every label position is computed and CLAMPED in the same pixel
 * coordinate system it renders in, so nothing can be pushed off either end and the lane packing is
 * exact rather than hopeful.
 */

import { useLayoutEffect, useRef, useState } from "react";
import { SIGNS, type Body } from "../engine/ephemeris";

/** Wider than this gains nothing — the planets are already legible and the band starts to look
 *  like a ruler nobody asked for. */
const BAND_MAX = 720;
const BAND_MIN = 280;
const CHIP_W = 76;
const CHIP_H = 19;
const LANE_H = 21;
const AXIS_H = 22;
/** Below this a cell cannot hold "Sagittarius", so every sign goes to three letters together —
 *  abbreviating only the long ones would read as an error rather than a convention. */
const SHORT_NAME_BELOW = 48;

export type Chip = {
  body: Body;
  /** Sidereal longitude, 0–360. */
  lon: number;
  retro: boolean;
  /** Faded: on the chart because it was in the sky, but making no connections. */
  faint?: boolean;
  /** Numbers of the connections it takes part in, matching the list below the chart. */
  badges?: number[];
};

type Placed = Chip & { x: number; left: number; lane: number };

/**
 * Lay chips out so none overlaps: sort by position, then drop each into the first lane whose last
 * chip has already finished. Deterministic, and it never needs to measure the DOM.
 */
function pack(chips: Chip[], bandW: number, chipW: number): { placed: Placed[]; lanes: number } {
  const laneEnds: number[] = [];
  const placed = chips
    .map((c) => {
      const x = (c.lon / 360) * bandW;
      return { ...c, x, left: Math.max(0, Math.min(bandW - chipW, x - chipW / 2)), lane: 0 };
    })
    .sort((a, b) => a.left - b.left)
    .map((c) => {
      let lane = laneEnds.findIndex((end) => end <= c.left - 3);
      if (lane === -1) { lane = laneEnds.length; laneEnds.push(0); }
      laneEnds[lane] = c.left + chipW;
      return { ...c, lane };
    });
  return { placed, lanes: Math.max(1, laneEnds.length) };
}

/** One planet's label. The connection numbers go BEFORE the name, inside the same flex row, so the
 *  chip's fixed width holds all of it — a badge floated into the corner would sit on top of a long
 *  name like "Mercury", and the audit forbids text that overflows its box. */
function ChipEl({ c, top, tone, chipW }: { c: Placed; top: number; tone: "a" | "b"; chipW: number }) {
  const badges = c.badges?.slice(0, 2) ?? [];
  return (
    <span className={`chip ${tone}${c.faint ? " faint" : ""}`}
      style={{ left: `${c.left}px`, top: `${top}px`, width: `${chipW}px`, height: `${CHIP_H}px` }}
      title={`${c.body} at ${Math.floor(c.lon % 30)}° ${SIGNS[Math.floor(c.lon / 30) % 12]}` +
        (c.retro ? " — appearing to move backwards against the stars" : "") +
        (c.badges?.length ? ` — connection ${c.badges.join(", ")}` : "")}>
      {badges.map((n) => <b key={n}>{n}</b>)}
      <span className="nm">{c.body}</span>
      {c.retro && <u>&#9668;</u>}
    </span>
  );
}

/**
 * One or two people on one axis of twelve signs.
 *
 * With two, the first person's planets sit above the line and the second's below it, so a shared
 * position is a vertical stack — the one relationship in synastry that needs no explaining at all.
 */
export default function SkyBand({ above, below, label, tone = "a" }: {
  above: Chip[];
  below?: Chip[];
  label: string;
  /** Which of the two brand hues the upper row wears. The lower row is always the other one. */
  tone?: "a" | "b";
}) {
  // Measured, not assumed. jsdom has no ResizeObserver, so tests keep the full width — which is
  // the right default anyway for anything that cannot measure.
  const host = useRef<HTMLDivElement>(null);
  const [bandW, setBandW] = useState(BAND_MAX);
  useLayoutEffect(() => {
    const el = host.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const fit = () => setBandW(Math.max(BAND_MIN, Math.min(BAND_MAX, el.clientWidth)));
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const cellW = bandW / 12;
  const chipW = Math.min(CHIP_W, bandW);
  const shortNames = cellW < SHORT_NAME_BELOW;
  const top = pack(above, bandW, chipW);
  const bottom = below ? pack(below, bandW, chipW) : null;
  const topH = top.lanes * LANE_H;
  const bottomH = bottom ? bottom.lanes * LANE_H : 0;
  const height = topH + AXIS_H + bottomH;

  return (
    <div className="band-scroll" ref={host}>
      <div className="band" style={{ width: `${bandW}px`, height: `${height}px` }}
        role="img" aria-label={label}>
        {/* The twelve signs, in order, each exactly a twelfth of the sky. */}
        {SIGNS.map((s, i) => (
          <span key={s} className={`cell${i % 2 ? " alt" : ""}`} title={s}
            style={{ left: `${i * cellW}px`, width: `${cellW}px`, top: `${topH}px`, height: `${AXIS_H}px` }}>
            {shortNames ? s.slice(0, 3) : s}
          </span>
        ))}

        {/* A leader from each planet's EXACT longitude down to its label, which may have been
            nudged inwards to stay on the band. Without it a clamped chip would quietly misreport
            where its planet was — a drawing that lies by a few degrees to keep its text tidy.
            Lane 0 sits against the axis; further lanes stack away from it. */}
        {top.placed.map((c) => (
          <span key={`la-${c.body}`} className={`lead ${tone}`} style={{
            left: `${c.x}px`,
            top: `${topH - (c.lane + 1) * LANE_H + CHIP_H}px`,
            height: `${(c.lane + 1) * LANE_H - CHIP_H}px`,
          }} />
        ))}
        {top.placed.map((c) => (
          <ChipEl key={`a-${c.body}`} c={c} tone={tone} chipW={chipW}
            top={topH - (c.lane + 1) * LANE_H} />
        ))}

        {bottom?.placed.map((c) => (
          <span key={`lb-${c.body}`} className="lead b" style={{
            left: `${c.x}px`, top: `${topH + AXIS_H}px`, height: `${c.lane * LANE_H + 2}px`,
          }} />
        ))}
        {bottom?.placed.map((c) => (
          <ChipEl key={`b-${c.body}`} c={c} tone="b" chipW={chipW}
            top={topH + AXIS_H + c.lane * LANE_H + 2} />
        ))}
      </div>
    </div>
  );
}
