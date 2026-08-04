/**
 * people.ts — the two places a person can come from, behind one type.
 *
 * A MANUAL person is typed in by whoever is using the page and lives ONLY in their browser's
 * localStorage. It is never sent anywhere — there is no ArtaMatch server to send it to. That is the
 * whole privacy model, and it is worth being literal about it in the UI: dates of birth of people
 * who did not consent to being on a compatibility site are exactly the kind of thing that should not
 * leave the device.
 *
 * A PUBLIC person is an ArtaQuest member whose birthday is already public on their own profile
 * (artaquest.com publishes the whole database by design). Those are fetched read-only and cached.
 */

import { parseDate } from "../engine/ephemeris";

type PersonSource = "manual" | "artaquest";

export type Person = {
  id: string;
  name: string;
  /** YYYY-MM-DD. The only astrological input this system takes. */
  birthday: string;
  source: PersonSource;
  /** artaquest members only */
  slug?: string;
  avatar?: string;
  profileUrl?: string;
  addedAt?: number;
};

const KEY = "artamatch.people.v1";
const SELF_KEY = "artamatch.self.v1";
const SEEDED_KEY = "artamatch.seeded.v1";

const canStore = () => typeof localStorage !== "undefined";

/**
 * People the list starts with on a first visit.
 *
 * They are ordinary manual entries in every other respect — deletable, editable, and stored only in
 * this browser. The seed runs ONCE (guarded by SEEDED_KEY), so deleting one does not bring it back
 * on the next reload, which is the behaviour anyone would expect from a row with an × on it.
 */
const SEED_PEOPLE: { name: string; birthday: string }[] = [
  { name: "Ayse Altundal", birthday: "1999-12-06" },
  { name: "Elif Eda Ayan", birthday: "2004-12-27" },
  { name: "Lana El Jamal", birthday: "2004-12-21" },
];

function seeded(): Person[] {
  return SEED_PEOPLE.map((p) => ({
    id: newId(), name: p.name, birthday: p.birthday, source: "manual" as const, addedAt: Date.now(),
  }));
}

export function loadPeople(): Person[] {
  if (!canStore()) return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) {
      // First visit only. Once the seed has run, an empty list stays empty.
      if (localStorage.getItem(SEEDED_KEY)) return [];
      const people = seeded();
      localStorage.setItem(SEEDED_KEY, "1");
      // Persist immediately rather than waiting for the save effect. React StrictMode invokes a
      // useState initialiser twice in development; without this the second call would find no
      // stored list but a set seed flag, and return an empty one.
      localStorage.setItem(KEY, JSON.stringify(people));
      return people;
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Re-validate on read: a hand-edited or half-written localStorage entry should degrade to
    // "that row is gone", never to a chart computed from a nonsense date.
    return parsed.filter((p): p is Person =>
      p && typeof p.name === "string" && typeof p.birthday === "string" && !!parseDate(p.birthday));
  } catch {
    return [];
  }
}

export function savePeople(people: Person[]): void {
  if (!canStore()) return;
  try {
    localStorage.setItem(KEY, JSON.stringify(people));
  } catch {
    /* quota or private mode — the list simply does not persist, which is survivable */
  }
}

export function newId(): string {
  // crypto.randomUUID is not available on every browser/origin combination this may be opened from.
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `p_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

/** Which person the viewer is — used to rank "everyone else, against me". */
export function loadSelfId(): string | null {
  if (!canStore()) return null;
  return localStorage.getItem(SELF_KEY);
}

export function saveSelfId(id: string | null): void {
  if (!canStore()) return;
  if (id) localStorage.setItem(SELF_KEY, id);
  else localStorage.removeItem(SELF_KEY);
}

/** Validate a would-be entry, returning an error string or null. */
export function validatePerson(name: string, birthday: string): string | null {
  if (!name.trim()) return "Give them a name so you can tell the rows apart.";
  if (!birthday.trim()) return "A date of birth is the one thing this needs.";
  if (!parseDate(birthday)) {
    return "That is not a real calendar date. Use YYYY-MM-DD, between 1800 and 2100.";
  }
  return null;
}
