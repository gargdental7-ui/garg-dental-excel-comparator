"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, History } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Pagination } from "@/components/ui/Pagination";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { AuditLogEntry } from "@/lib/types";

const ACTION_LABELS: Record<string, string> = {
  login: "Logged In",
  create_quotation: "Created Quote",
  upload_master_excel: "Uploaded Master Excel",
  delete_master_excel: "Deleted Master Excel",
  create_user: "Created User",
  update_user: "Updated User",
  enable_user: "Enabled User",
  disable_user: "Disabled User",
  delete_user: "Deleted User",
  reset_password: "Reset Password",
};

function describe(entry: AuditLogEntry): string {
  const label = ACTION_LABELS[entry.action] ?? entry.action;
  const meta = entry.metadata;
  if (entry.action === "create_quotation" && meta) {
    return `${label} #${meta.quote_number} - ${meta.customer_name}`;
  }
  if ((entry.action === "upload_master_excel" || entry.action === "delete_master_excel") && meta?.filename) {
    return `${label} (${meta.filename})`;
  }
  return label;
}

export default function StaffActivityTimelinePage() {
  return (
    <Suspense fallback={null}>
      <StaffActivityTimeline />
    </Suspense>
  );
}

function StaffActivityTimeline() {
  const params = useParams<{ userId: string }>();
  const searchParams = useSearchParams();
  const companyId = searchParams.get("company_id");
  const me = useCurrentUser();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me?.role !== "super_admin" || !companyId) return;
    let cancelled = false;
    api.audit
      .logs(companyId, page, params.userId)
      .then((res) => {
        if (cancelled) return;
        setLogs(res.logs);
        setTotal(res.total);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail.message : "Could not load activity.");
      });
    return () => {
      cancelled = true;
    };
  }, [me, companyId, page, params.userId]);

  if (me === undefined) return null;

  if (me === null || me.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <PageHeader icon={History} title="Staff Activity" description="Activity timeline." />
        <ErrorBanner message="You need Super Admin access to view this page." />
      </div>
    );
  }

  if (!companyId) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <PageHeader icon={History} title="Staff Activity" description="Activity timeline." />
        <ErrorBanner message="Missing company - go back to Staff Activity and click a staff card." />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <Link
        href="/activity"
        className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-brand-navy dark:text-slate-400 dark:hover:text-brand-cyan"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Staff Activity
      </Link>
      <h1 className="mb-6 text-2xl font-bold text-slate-900 dark:text-slate-50">Activity Timeline</h1>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <ol className="space-y-3">
        {logs.map((entry) => (
          <li
            key={entry.id}
            className="flex items-baseline gap-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-3"
          >
            <span className="w-20 shrink-0 text-xs text-slate-500 dark:text-slate-400">
              {new Date(entry.createdAt).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
            </span>
            <span className="text-sm text-slate-800 dark:text-slate-200">{describe(entry)}</span>
          </li>
        ))}
        {logs.length === 0 && <p className="text-sm text-slate-500 dark:text-slate-400">No activity recorded yet.</p>}
      </ol>
      <Pagination page={page} pageSize={50} total={total} onChange={setPage} />
    </div>
  );
}
