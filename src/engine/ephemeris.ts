/**
 * ephemeris.ts — a dependency-free SIDEREAL (Vedic / Jyotish) ephemeris.
 *
 * Places the Sun, Moon and Mercury…Pluto in the sidereal zodiac — the constellation-aligned zodiac
 * fixed to the stars rather than to the moving equinox — for any date between roughly 1700 and 2200.
 *
 * Tropical longitude is measured from the vernal equinox of date, which precesses westward ~50.3″/yr.
 * Sidereal longitude is measured from a fixed point among the stars. The difference is the AYANAMSA
 * (~24.2° today). We use LAHIRI (Chitrapaksha), the Indian government standard for Jyotish, so the Sun
 * enters 0° sidereal Aries around 14 April (Mesha Saṅkrānti) rather than at the March equinox.
 *
 * Method, and why each piece was chosen — every one is verified against the Swiss Ephemeris in
 * tests/ephemeris.test.ts, which is the only reason to believe any of it:
 *
 *   Moon      Meeus, *Astronomical Algorithms* ch. 47 (the truncated ELP-2000/82 series, 45 of the 60
 *             longitude terms) plus nutation in longitude. The Moon is the single most important body
 *             here — Guna Milan is built almost entirely on its nakshatra, and a nakshatra is only
 *             13°20′ wide — so it gets the good series rather than the cheap one.
 *   Sun …     JPL/Standish low-precision Keplerian elements, Table 1 — for EVERY planet. The
 *   Pluto     longer-range Table 2a was tried for the outer planets and measured WORSE inside
 *             1900–2100 (see the ELEMENTS comment and tools/compare-elements.mjs).
 *
 * Everything here is PURE and DETERMINISTIC — no Date.now(), no I/O, no network. The same input
 * always produces the same chart, which is what makes the compatibility report reproducible by a
 * stranger who wants to contradict it.
 */

export type Body =
  | "Sun" | "Moon" | "Mercury" | "Venus" | "Mars"
  | "Jupiter" | "Saturn" | "Uranus" | "Neptune" | "Pluto";

/** The bodies, in the order the report lists them. */
export const BODIES: Body[] = [
  "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
];

export const SIGNS = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
] as const;
type SignName = (typeof SIGNS)[number];

/** The sign lords (sign index → ruling graha). Classical rulership only: Jyotish assigns no signs to
 *  Uranus, Neptune or Pluto, and Graha Maitri depends on this table being the classical one. */
export const SIGN_LORD: Body[] = [
  "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
  "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
];

const D2R = Math.PI / 180;
const R2D = 180 / Math.PI;
const sin = (d: number) => Math.sin(d * D2R);
const cos = (d: number) => Math.cos(d * D2R);
const norm360 = (x: number) => { x %= 360; return x < 0 ? x + 360 : x; };

/** Signed angular difference a − b, folded to (−180, 180]. */
export const angleDiff = (a: number, b: number) => {
  let d = (a - b) % 360;
  if (d > 180) d -= 360;
  if (d <= -180) d += 360;
  return d;
};

// ── time ────────────────────────────────────────────────────────────────────────────────────────

/** Gregorian calendar date (+ fractional UT hour) → Julian Day. */
export function julianDay(y: number, m: number, d: number, hourUT = 0): number {
  if (m <= 2) { y -= 1; m += 12; }
  const A = Math.floor(y / 100);
  const B = 2 - A + Math.floor(A / 4);
  return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d + B - 1524.5 + hourUT / 24;
}

/** Julian Day → { y, m, d, hour } (UT), the inverse of julianDay. */
export function fromJulianDay(jd: number): { y: number; m: number; d: number; hour: number } {
  const z = Math.floor(jd + 0.5);
  const f = jd + 0.5 - z;
  const alpha = Math.floor((z - 1867216.25) / 36524.25);
  const a = z < 2299161 ? z : z + 1 + alpha - Math.floor(alpha / 4);
  const b = a + 1524;
  const c = Math.floor((b - 122.1) / 365.25);
  const dd = Math.floor(365.25 * c);
  const e = Math.floor((b - dd) / 30.6001);
  const day = b - dd - Math.floor(30.6001 * e);
  const m = e < 14 ? e - 1 : e - 13;
  const y = m > 2 ? c - 4716 : c - 4715;
  return { y, m, d: day, hour: f * 24 };
}

const centuries = (jd: number) => (jd - 2451545.0) / 36525;

// ── ayanamsa ────────────────────────────────────────────────────────────────────────────────────

/**
 * Lahiri (Chitrapaksha) ayanamsa in degrees at Julian centuries T from J2000 — the angle subtracted
 * from a tropical longitude to land in the sidereal zodiac.
 *
 * The coefficients are a least-squares fit to the Swiss Ephemeris' own SIDM_LAHIRI over 1900–2100
 * (see tools/fit-ayanamsa.py). A quadratic is used because precession is not linear — and it turns
 * out to be enough: the residual across 1975 samples is below 1e-6°, i.e. Swiss Ephemeris' Lahiri is
 * itself a quadratic and this reproduces it rather than approximating it.
 */
const AYANAMSA_C0 = 23.85709235;
const AYANAMSA_C1 = 1.39688796;
const AYANAMSA_C2 = 0.00030709;
export const ayanamsaDeg = (T: number): number => AYANAMSA_C0 + AYANAMSA_C1 * T + AYANAMSA_C2 * T * T;

// ── the Moon (Meeus ch. 47) ─────────────────────────────────────────────────────────────────────

// [D, M, M', F, coefficient in 1e-6 deg] — the 45 largest terms of Σl. Terms carrying M are scaled by
// E^|M| to account for the slow change in the Earth's orbital eccentricity.
const MOON_TERMS: [number, number, number, number, number][] = [
  [0, 0, 1, 0, 6288774], [2, 0, -1, 0, 1274027], [2, 0, 0, 0, 658314], [0, 0, 2, 0, 213618],
  [0, 1, 0, 0, -185116], [0, 0, 0, 2, -114332], [2, 0, -2, 0, 58793], [2, -1, -1, 0, 57066],
  [2, 0, 1, 0, 53322], [2, -1, 0, 0, 45758], [0, 1, -1, 0, -40923], [1, 0, 0, 0, -34720],
  [0, 1, 1, 0, -30383], [2, 0, 0, -2, 15327], [0, 0, 1, 2, -12528], [0, 0, 1, -2, 10980],
  [4, 0, -1, 0, 10675], [0, 0, 3, 0, 10034], [4, 0, -2, 0, 8548], [2, 1, -1, 0, -7888],
  [2, 1, 0, 0, -6766], [1, 0, -1, 0, -5163], [1, 1, 0, 0, 4987], [2, -1, 1, 0, 4036],
  [2, 0, 2, 0, 3994], [4, 0, 0, 0, 3861], [2, 0, -3, 0, 3665], [0, 1, -2, 0, -2689],
  [2, 0, -1, 2, -2602], [2, -1, -2, 0, 2390], [1, 0, 1, 0, -2348], [2, -2, 0, 0, 2236],
  [0, 1, 2, 0, -2120], [0, 2, 0, 0, -2069], [2, -2, -1, 0, 2048], [2, 0, 1, -2, -1773],
  [2, 0, 0, 2, -1595], [4, -1, -1, 0, 1215], [0, 0, 2, 2, -1110], [3, 0, -1, 0, -892],
  [2, 1, 1, 0, -810], [4, -1, -2, 0, 759], [0, 2, -1, 0, -713], [2, 2, -1, 0, -700],
  [2, 1, -2, 0, 691],
];

/** Nutation in longitude Δψ, degrees — the small (≤ 0.005°) wobble that separates the mean equinox
 *  from the true one. Included so our longitudes match the Swiss Ephemeris' apparent positions. */
function nutationLon(T: number): number {
  const omega = 125.04452 - 1934.136261 * T;
  const Ls = 280.4665 + 36000.7698 * T;
  const Lm = 218.3165 + 481267.8813 * T;
  return (-17.2 * sin(omega) - 1.32 * sin(2 * Ls) - 0.23 * sin(2 * Lm) + 0.21 * sin(2 * omega)) / 3600;
}

/** Apparent geocentric longitude of the Moon, degrees, referred to the true equinox of date. */
function moonLongitude(jd: number): number {
  const T = centuries(jd);
  const T2 = T * T, T3 = T2 * T, T4 = T3 * T;
  const Lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T2 + T3 / 538841 - T4 / 65194000;
  const D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T2 + T3 / 545868 - T4 / 113065000;
  const M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T2 + T3 / 24490000;
  const Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T2 + T3 / 69699 - T4 / 14712000;
  const F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T2 - T3 / 3526000 + T4 / 863310000;
  const A1 = 119.75 + 131.849 * T;
  const A2 = 53.09 + 479264.290 * T;
  const E = 1 - 0.002516 * T - 0.0000074 * T2;

  let sigma = 0;
  for (const [d, m, mp, f, coeff] of MOON_TERMS) {
    const ecc = m === 0 ? 1 : Math.abs(m) === 1 ? E : E * E;
    sigma += coeff * ecc * sin(d * D + m * M + mp * Mp + f * F);
  }
  sigma += 3958 * sin(A1) + 1962 * sin(Lp - F) + 318 * sin(A2);

  return norm360(Lp + sigma / 1e6 + nutationLon(T));
}

// ── the planets (JPL/Standish) ──────────────────────────────────────────────────────────────────

type Elements = {
  c: [number, number, number, number, number, number]; // a, e, I, L, ϖ, Ω at J2000
  r: [number, number, number, number, number, number]; // their rates, per Julian century
};

/**
 * JPL/Standish Table 1 (nominally 1800–2050), used for EVERY planet.
 *
 * JPL also publishes a Table 2a valid 3000 BC – 3000 AD, with extra long-period b/c/s/f terms, and
 * the obvious guess is that it should be used for the slow outer planets. It was tried and MEASURED
 * against the Swiss Ephemeris era by era (tools/compare-elements.mjs), and it is worse everywhere
 * that matters: over 1900–2100 it costs 4–6× accuracy on Uranus, Neptune and Pluto and gains nothing
 * on Jupiter or Saturn. Table 2a is fitted across six millennia, so it is looser inside any one
 * century — and one century is all a birth-date matcher ever needs. Measured, not assumed.
 */
const ELEMENTS: Record<string, Elements> = {
  Mercury: {
    c: [0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593],
    r: [0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081],
  },
  Venus: {
    c: [0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255],
    r: [0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418],
  },
  Earth: {
    c: [1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0],
    r: [0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0],
  },
  Mars: {
    c: [1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891],
    r: [0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343],
  },
  Jupiter: {
    c: [5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909],
    r: [-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106],
  },
  Saturn: {
    c: [9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448],
    r: [-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794],
  },
  Uranus: {
    c: [19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503],
    r: [-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589],
  },
  Neptune: {
    c: [30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574],
    r: [0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664],
  },
  Pluto: {
    c: [39.48211675, 0.24882730, 17.14001206, 238.92903833, 224.06891629, 110.30393684],
    r: [-0.00031596, 0.00005170, 0.00004818, 145.20780515, -0.04062942, -0.01183482],
  },
};

/** Solve Kepler's equation M = E − e·sin E for the eccentric anomaly, in degrees. */
function kepler(M: number, e: number): number {
  M = ((M + 180) % 360 + 360) % 360 - 180;
  let E = M + e * R2D * sin(M);
  for (let i = 0; i < 12; i++) {
    const dM = M - (E - e * R2D * sin(E));
    const step = dM / (1 - e * cos(E));
    E += step;
    if (Math.abs(step) < 1e-12) break;
  }
  return E;
}

/** Heliocentric J2000 ecliptic rectangular coordinates (AU). */
function helio(planet: string, T: number): [number, number, number] {
  const el = ELEMENTS[planet];
  const a = el.c[0] + el.r[0] * T;
  const e = el.c[1] + el.r[1] * T;
  const I = el.c[2] + el.r[2] * T;
  const L = el.c[3] + el.r[3] * T;
  const wbar = el.c[4] + el.r[4] * T;
  const Om = el.c[5] + el.r[5] * T;

  const w = wbar - Om;
  const E = kepler(L - wbar, e);
  const xp = a * (cos(E) - e);
  const yp = a * Math.sqrt(1 - e * e) * sin(E);
  const cw = cos(w), sw = sin(w), cO = cos(Om), sO = sin(Om), cI = cos(I), sI = sin(I);
  return [
    (cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp,
    (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp,
    sw * sI * xp + cw * sI * yp,
  ];
}

// General precession in longitude, deg per Julian century — carries a J2000-frame longitude to the
// equinox of date. The Keplerian elements are J2000; the Moon series is already of date.
const PRECESSION = 1.396971;

/** Geocentric TROPICAL longitude of date, degrees. */
function tropicalLongitude(body: Body, jd: number): number {
  if (body === "Moon") return moonLongitude(jd);
  const T = centuries(jd);
  const [xe, ye] = helio("Earth", T);
  let lon: number;
  if (body === "Sun") {
    lon = R2D * Math.atan2(-ye, -xe);
  } else {
    const [xp, yp] = helio(body, T);
    lon = R2D * Math.atan2(yp - ye, xp - xe);
  }
  return norm360(lon + PRECESSION * T);
}

// ── charts ──────────────────────────────────────────────────────────────────────────────────────

export type Placement = {
  body: Body;
  /** Sidereal ecliptic longitude, 0–360°. */
  lon: number;
  /** Sign index 0–11 (0 = Aries / Meṣa). */
  sign: number;
  signName: SignName;
  /** Degrees into the sign, 0–30. */
  deg: number;
  retro: boolean;
  /** Motion in degrees per day — negative when retrograde. */
  speed: number;
};

export type Chart = {
  jd: number;
  /** The UT instant this chart is for, as an ISO string. */
  iso: string;
  ayanamsa: number;
  placements: Placement[];
  byBody: Record<Body, Placement>;
};

/** The sidereal longitude of one body at one instant. Exported because the uncertainty model scans
 *  the Moon across a day and does not want to build a whole chart per step. */
export function siderealLongitude(body: Body, jd: number): number {
  return norm360(tropicalLongitude(body, jd) - ayanamsaDeg(centuries(jd)));
}

function place(body: Body, jd: number): Placement {
  const lon = siderealLongitude(body, jd);
  // Central difference over ±6h: robust across a station, where a one-sided difference can report
  // the wrong direction for a planet that turns during the step.
  const speed = angleDiff(siderealLongitude(body, jd + 0.25), siderealLongitude(body, jd - 0.25)) * 2;
  const sign = Math.floor(lon / 30) % 12;
  return { body, lon, sign, signName: SIGNS[sign], deg: lon - sign * 30, retro: speed < 0, speed };
}

/** A sidereal chart for a Julian Day. */
export function chartAt(jd: number, bodies: Body[] = BODIES): Chart {
  const placements = bodies.map((b) => place(b, jd));
  const byBody = {} as Record<Body, Placement>;
  for (const p of placements) byBody[p.body] = p;
  // Round to the nearest MINUTE before decomposing, so the carry propagates through the hour and
  // the date. Rounding minutes after splitting produced "04:60" → printed as "04:00", an hour (and
  // at midnight a whole day) before the instant the placements were computed at.
  const { y, m, d, hour } = fromJulianDay(Math.round(jd * 1440) / 1440);
  const hh = Math.floor(hour + 1e-9);
  const mm = Math.round((hour - hh) * 60);
  const iso = `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}` +
    `T${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}Z`;
  return { jd, iso, ayanamsa: ayanamsaDeg(centuries(jd)), placements, byBody };
}

/** Parse a strict YYYY-MM-DD, rejecting calendar-impossible dates.
 *
 *  Date.UTC ROLLS OVER (2001-02-29 becomes 2001-03-01) so isNaN never fires on a bad date — the
 *  round-trip check below is what actually rejects it. Without this a mistyped birthday would
 *  silently chart a different day and every number downstream would be quietly wrong. */
export function parseDate(iso: string): { y: number; m: number; d: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!match) return null;
  const y = +match[1], m = +match[2], d = +match[3];
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;
  const probe = new Date(Date.UTC(y, m - 1, d));
  if (probe.getUTCFullYear() !== y || probe.getUTCMonth() !== m - 1 || probe.getUTCDate() !== d) return null;
  // Standish's Table 1 elements are stated for 1800–2050 and this engine is VERIFIED against the
  // Swiss Ephemeris over 1900–2100. Refuse anything outside the range we can stand behind rather
  // than quietly extrapolating.
  if (y < 1800 || y > 2100) return null;
  return { y, m, d };
}

/** The chart for a birth DATE at a given UT hour (default noon — the midpoint of the unknown day). */
export function chartForDate(iso: string, hourUT = 12): Chart | null {
  const parsed = parseDate(iso);
  if (!parsed) return null;
  return chartAt(julianDay(parsed.y, parsed.m, parsed.d, hourUT));
}
