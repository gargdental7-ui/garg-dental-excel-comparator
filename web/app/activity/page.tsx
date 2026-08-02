"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, Clock } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Badge } from "@/components/ui/Badge";
import { CompanySelector } from "@/components/CompanySelector";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { StaffSummaryEntry } from "@/lib/types";

function formatLastActive(iso: string | null): string {
  if (!iso) return "Never";
  const date = new Date(iso);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  return sameDay
    ? date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
    : date.toLocaleDateString();
}

export default function ActivityDashboardPage() {
  const me = useCurrentUser();
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [staff, setStaff] = useState<StaffSummaryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me?.role !== "super_admin" || !companyId) return;
    let cancelled = false;
    api.audit
      .staffSummary(companyId)
      .then((res) => {
        if (!cancelled) setStaff(res.staff);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail.message : "Could not load staff activity.");
      });
    return () => {
      cancelled = true;
    };
  }, [me, companyId]);

  if (me === undefined) return null;

  if (me === null || me.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <PageHeader icon={Activity} title="Staff Activity" description="See what a company's team has been up to." />
        <ErrorBanner message="You need Super Admin access to view this page." />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <PageHeader icon={Activity} title="Staff Activity" description="See what a company's team has been up to." />

      <div className="mb-4">
        <CompanySelector value={companyId} onChange={setCompanyId} />
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {staff.map((s) => (
          <Link
            key={s.id}
            href={`/activity/${s.id}?company_id=${companyId}`}
            prefetch={false}
            className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 transition hover:border-slate-400 dark:hover:border-slate-600 hover:shadow-md"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-50">{s.fullName}</h2>
              {!s.active && <Badge>Disabled</Badge>}
            </div>
            <p className="mt-3 text-2xl font-bold text-brand-navy dark:text-brand-cyan">{s.quotesToday}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">Quotes Created Today</p>
            <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <Clock className="h-3.5 w-3.5" />
              Last Active: {formatLastActive(s.lastActive)}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
