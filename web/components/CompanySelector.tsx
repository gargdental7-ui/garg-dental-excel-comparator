"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";
import type { Company } from "@/lib/types";

/** Used by every Super-Admin-only page that needs "which company am I
 * looking at" - staff never see this, since they're always implicitly
 * scoped to their own company by the backend. */
export function CompanySelector({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (companyId: string) => void;
}) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.companies
      .list()
      .then((res) => {
        if (cancelled) return;
        const active = res.companies.filter((c) => c.active);
        setCompanies(active);
        if (!value && active.length > 0) onChange(active[0].id);
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only load once on mount
  }, []);

  if (!loaded) return null;

  if (companies.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No companies yet.</p>;
  }

  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500"
    >
      {companies.map((c) => (
        <option key={c.id} value={c.id}>
          {c.displayName}
        </option>
      ))}
    </select>
  );
}
