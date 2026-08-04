"use client";

import { useEffect, useState } from "react";
import { api } from "./apiClient";
import type { CurrentUser } from "./types";

/** undefined = not yet resolved, null = not authenticated. Every
 * super_admin-gated page was independently re-implementing this same
 * fetch-on-mount pattern - unified here.
 *
 * Sidebar.tsx (always mounted) plus whichever page is showing both call
 * this hook, so a naive fetch-on-mount fired the /api/auth/status round
 * trip (and the require_auth DB lookup behind it) at least twice per page
 * view. This module-level singleton shares one in-flight fetch across all
 * concurrent callers and keeps the result briefly cached so navigating
 * between pages doesn't refetch every time either.
 *
 * Safe against the account-switch stale-role bug fixed in commit cc904db:
 * that fix made login do a hard `window.location.href` navigation
 * specifically because client JS state (this cache included) doesn't
 * survive a full page reload. Logout must do the same - see
 * clearCurrentUserCache() below and its call site in Sidebar.tsx. */

const CACHE_TTL_MS = 30_000;

let cachedValue: CurrentUser | null | undefined = undefined;
let cachedAt = 0;
let inFlight: Promise<CurrentUser | null> | null = null;
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((listener) => listener());
}

function fetchCurrentUser(): Promise<CurrentUser | null> {
  if (inFlight) return inFlight;
  inFlight = api.auth
    .status()
    .then((status) => status.user ?? null)
    .catch(() => null)
    .then((user) => {
      cachedValue = user;
      cachedAt = Date.now();
      inFlight = null;
      notify();
      return user;
    });
  return inFlight;
}

/** Called on logout so a signed-out identity can never be served from the
 * cache to a component that reads it before the next hard navigation. */
export function clearCurrentUserCache() {
  cachedValue = undefined;
  cachedAt = 0;
  inFlight = null;
  notify();
}

export function useCurrentUser(): CurrentUser | null | undefined {
  const [me, setMe] = useState<CurrentUser | null | undefined>(() =>
    cachedValue !== undefined && Date.now() - cachedAt < CACHE_TTL_MS ? cachedValue : undefined
  );

  useEffect(() => {
    const listener = () => setMe(cachedValue);
    listeners.add(listener);

    // If the cache was already fresh, the useState initializer above
    // already captured it - no need to setState again here. Only kick off
    // a fetch (and update state once it resolves) when it wasn't.
    const isFresh = cachedValue !== undefined && Date.now() - cachedAt < CACHE_TTL_MS;
    if (!isFresh) {
      fetchCurrentUser().then((user) => setMe(user));
    }

    return () => {
      listeners.delete(listener);
    };
  }, []);

  return me;
}
