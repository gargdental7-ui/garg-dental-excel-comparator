"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, Clock } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { CurrentUser, StaffSummaryEntry } from "@/lib/types";

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
  const [me, setMe] = useState<CurrentUser | null | undefined>(undefined);
  const [staff, setStaff] = useState<StaffSummaryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.auth
      .status()
      .then((status) => setMe(status.user ?? null))
      .catch(() => setMe(null));
  }, []);

  useEffect(() => {
    if (me?.role !== "admin") return;
    api.audit
      .staffSummary()
      .then((res) => setStaff(res.staff))
      .catch((err) => setError(err instanceof ApiError ? err.detail.message : "Could not load staff activity."));
  }, [me]);

  if (me === undefined) return null;

  if (me === null || me.role !== "admin") {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <PageHeader icon={Activity} title="Staff Activity" description="See what your team has been up to." />
        <ErrorBanner message="You need admin access to view this page." />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <PageHeader icon={Activity} title="Staff Activity" description="See what your team has been up to." />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {staff.map((s) => (
          <Link
            key={s.id}
            href={`/activity/${s.id}`}
            className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 transition hover:border-slate-400 dark:hover:border-slate-600 hover:shadow-md"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-50">{s.fullName}</h2>
              {!s.active && (
                <span className="rounded-full bg-slate-200 dark:bg-slate-800 px-2 py-0.5 text-xs text-slate-600 dark:text-slate-400">
                  Disabled
                </span>
              )}
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
