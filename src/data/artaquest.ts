/**
 * artaquest.ts — read-only client for artaquest.com's public API.
 *
 * ArtaQuest publishes its entire database on purpose (radical transparency: every table, every row,
 * including every member's birthday). So this is a plain cross-origin GET against endpoints that
 * already answer with no credential at all — nothing is scraped and nothing private is touched.
 * The API echoes the requesting origin in Access-Control-Allow-Origin, so a GitHub Pages page can
 * read it directly and ArtaMatch needs no backend of its own.
 *
 * The birthday is not on the directory endpoint, only on the individual profile, so this is a
 * two-step fetch. Both steps are bounded by an explicit timeout — an external call without one is
 * how a page ends up hanging on a blank screen forever.
 */

import { type Person } from "./people";
import { parseDate } from "../engine/ephemeris";

export const ARTAQUEST_ORIGIN = "https://artaquest.com";
const API = `${ARTAQUEST_ORIGIN}/wp-json/aq/v1`;
const CACHE_KEY = "artamatch.artaquest.v1";
const CACHE_TTL_MS = 6 * 60 * 60 * 1000; // 6 hours — birthdays do not change

const TIMEOUT_MS = 12_000;
const CONCURRENCY = 4;

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const onAbort = () => controller.abort();
  signal?.addEventListener("abort", onAbort);
  try {
    const res = await fetch(url, { signal: controller.signal, credentials: "omit" });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

type LeaderboardItem = { id: number; name: string; slug: string; avatar?: string };
type ProfileResponse = { id: number; name: string; slug: string; avatar?: string; birthday?: string };

/** Run tasks with a small concurrency cap — polite to the host and avoids a burst of parallel
 *  connections that some browsers will queue anyway. */
async function pooled<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let cursor = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    for (;;) {
      const i = cursor++;
      if (i >= items.length) return;
      out[i] = await fn(items[i]);
    }
  });
  await Promise.all(workers);
  return out;
}

export type FetchResult = {
  people: Person[];
  /** Members present in the directory but carrying no usable birthday — reported, not hidden, so
   *  the count on screen always adds up to what was actually found. */
  skipped: { name: string; slug: string; reason: string }[];
  fetchedAt: number;
};

export function loadCached(): FetchResult | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as FetchResult;
    if (!parsed?.fetchedAt || Date.now() - parsed.fetchedAt > CACHE_TTL_MS) return null;
    // Validate the SHAPE, not just the age. A malformed-but-fresh entry (hand-edited storage, a
    // half-written write, an old schema) otherwise crashes the whole app at mount.
    if (!Array.isArray(parsed.people) || !Array.isArray(parsed.skipped)) return null;
    parsed.people = parsed.people.filter((p) =>
      p && typeof p.name === "string" && !!parseDate(String(p.birthday ?? "")));
    return parsed;
  } catch {
    return null;
  }
}

function cache(result: FetchResult): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(result));
  } catch {
    /* not fatal — it just refetches next time */
  }
}

/** Fetch the public member directory and each member's public birthday. */
export async function fetchPublicMembers(signal?: AbortSignal): Promise<FetchResult> {
  const directory = await getJson<{ items: LeaderboardItem[] }>(
    `${API}/leaderboard?limit=200`, signal,
  );
  const items = directory.items ?? [];

  const profiles = await pooled(items, CONCURRENCY, async (item) => {
    try {
      return await getJson<ProfileResponse>(
        `${API}/profile?slug=${encodeURIComponent(item.slug)}`, signal,
      );
    } catch {
      return null;
    }
  });

  const people: Person[] = [];
  const skipped: FetchResult["skipped"] = [];

  profiles.forEach((profile, i) => {
    const item = items[i];
    if (!profile) {
      skipped.push({ name: item.name, slug: item.slug, reason: "profile could not be read" });
      return;
    }
    const birthday = (profile.birthday ?? "").slice(0, 10);
    if (!parseDate(birthday)) {
      skipped.push({ name: item.name, slug: item.slug, reason: "no birthday on their public profile" });
      return;
    }
    people.push({
      id: `aq_${profile.slug}`,
      name: profile.name || item.name,
      birthday,
      source: "artaquest",
      slug: profile.slug,
      avatar: profile.avatar || item.avatar,
      profileUrl: `${ARTAQUEST_ORIGIN}/u/${profile.slug}`,
      addedAt: Date.now(),
    });
  });

  const result: FetchResult = { people, skipped, fetchedAt: Date.now() };
  // Cache only a USEFUL result. One flaky network window must not poison six hours of visits with
  // an empty snapshot; a genuinely-empty directory is indistinguishable, and refetching that is a
  // far smaller cost than hiding everyone.
  if (people.length > 0) cache(result);
  return result;
}

/**
 * Where to send someone who wants to reach out. ArtaQuest already has end-to-end encrypted member
 * messaging; `?with=<slug>` is its deep-link entry point. ArtaMatch deliberately does NOT build its
 * own messaging — re-implementing an E2EE channel to sit beside a working one would be strictly
 * worse for the people using it.
 */
export function messageUrl(person: Person): string | null {
  if (person.source !== "artaquest" || !person.slug) return null;
  return `${ARTAQUEST_ORIGIN}/messages?with=${encodeURIComponent(person.slug)}`;
}

export function profileUrl(person: Person): string | null {
  if (person.source !== "artaquest" || !person.slug) return null;
  return `${ARTAQUEST_ORIGIN}/u/${encodeURIComponent(person.slug)}`;
}

/** A shareable link that carries a manual entry in the URL, so two people can compare without
 *  either of them uploading anything anywhere. */
export function shareUrl(base: string, name: string, birthday: string): string {
  const u = new URL(base);
  u.searchParams.set("n", name);
  u.searchParams.set("b", birthday);
  return u.toString();
}
