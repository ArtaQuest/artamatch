/** Small shared pieces. Kept together because none of them is big enough to deserve a file. */

import type { Person } from "../data/people";

export function Mark({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" style={{ display: "block", flex: "0 0 auto" }}>
      <circle cx="16" cy="16" r="13" fill="none" stroke="var(--yin-lift)" strokeWidth="3.5" />
      <path
        d="M10 22 L16 8 L22 22 M12.6 17.5 h6.8"
        fill="none" stroke="var(--yang)" strokeWidth="3.2"
        strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  );
}

export function Avatar({ person }: { person: Person }) {
  if (person.avatar) {
    return <img className="avatar" src={person.avatar} alt="" loading="lazy" />;
  }
  const initial = person.name.trim().charAt(0).toUpperCase() || "?";
  return <span className="avatar ph" aria-hidden="true">{initial}</span>;
}

/** A simple filled bar. A DIV, not a span — an inline box ignores height, which is how an earlier
 *  version of this turned every 6px meter into a full-height gradient block. */
export function Meter({ value, max = 100, gold = false }: { value: number; max?: number; gold?: boolean }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={`meter${gold ? " gold" : ""}`}>
      <i style={{ width: `${pct}%` }} />
    </div>
  );
}

/**
 * The range bar — the whole span a score could take, with the best estimate marked on it.
 *
 * This is the honest picture whenever the birth times are unknown. A single big number implies a
 * precision the input does not have; showing the band, with the likeliest value marked inside it,
 * says the true thing without needing a sentence to walk it back.
 */
export function RangeBar({ min, max, value, scaleMin = 0, scaleMax = 100 }: {
  min: number; max: number; value: number; scaleMin?: number; scaleMax?: number;
}) {
  const pct = (v: number) => {
    const span = scaleMax - scaleMin || 1;
    return Math.max(0, Math.min(100, ((v - scaleMin) / span) * 100));
  };
  const left = pct(min);
  const width = Math.max(1.5, pct(max) - left);
  return (
    <div className="rangebar">
      <span className="track" />
      <span className="span" style={{ left: `${left}%`, width: `${width}%` }} />
      <span className="mark" style={{ left: `${pct(value)}%` }} />
      <span className="ends" style={{ position: "absolute", left: 0, right: 0, top: "19px" }}>
        <span>{scaleMin}</span>
        <span>{scaleMax}</span>
      </span>
    </div>
  );
}
