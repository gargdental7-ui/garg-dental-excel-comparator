"use client";

import { useEffect, useState } from "react";
import { api } from "./apiClient";
import type { CurrentUser } from "./types";

/** undefined = not yet resolved, null = not authenticated. Every
 * super_admin-gated page was independently re-implementing this same
 * fetch-on-mount pattern - unified here. */
export function useCurrentUser(): CurrentUser | null | undefined {
  const [me, setMe] = useState<CurrentUser | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    api.auth
      .status()
      .then((status) => {
        if (!cancelled) setMe(status.user ?? null);
      })
      .catch(() => {
        if (!cancelled) setMe(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return me;
}
