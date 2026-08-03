/** Small shared pieces. Kept together because none of them is big enough to deserve a file. */

import type { Person } from "../data/people";

export function Mark({ size = 34 }: { size?: number }) {
  return (
    <svg className="mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="13" fill="none" stroke="var(--yin)" strokeWidth="3.5" />
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

export function Meter({ value, max = 100 }: { value: number; max?: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return <span className="meter"><i style={{ width: `${pct}%` }} /></span>;
}

/** A score with its band tone. */
export function Score({ value, tone }: { value: number; tone: "high" | "mid" | "low" }) {
  return <span className={`sc tone-${tone}`}>{value.toFixed(0)}</span>;
}
