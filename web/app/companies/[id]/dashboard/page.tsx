"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, LayoutDashboard } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { Company, CompanyDashboard } from "@/lib/types";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function StatTile({ value, label }: { value: React.ReactNode; label: string }) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
      <p className="text-2xl font-bold text-brand-navy dark:text-brand-cyan">{value}</p>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{label}</p>
    </div>
  );
}

export default function CompanyDashboardPage() {
  const params = useParams<{ id: string }>();
  const me = useCurrentUser();
  const [company, setCompany] = useState<Company | null>(null);
  const [dashboard, setDashboard] = useState<CompanyDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me?.role !== "super_admin") return;
    let cancelled = false;
    Promise.all([api.companies.list(), api.companies.dashboard(params.id)])
      .then(([companiesRes, dashboardRes]) => {
        if (cancelled) return;
        setCompany(companiesRes.companies.find((c) => c.id === params.id) ?? null);
        setDashboard(dashboardRes);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail.message : "Could not load the company dashboard.");
      });
    return () => {
      cancelled = true;
    };
  }, [me, params.id]);

  if (me === undefined) return null;

  if (me === null || me.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <PageHeader icon={LayoutDashboard} title="Company Dashboard" description="Stats for a single company." />
        <ErrorBanner message="You need Super Admin access to view this page." />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <Link
        href="/companies"
        prefetch={false}
        className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-brand-navy dark:text-slate-400 dark:hover:text-brand-cyan"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Companies
      </Link>
      <PageHeader
        icon={LayoutDashboard}
        title={company ? company.displayName : "Company Dashboard"}
        description="At-a-glance stats for this company."
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {dashboard && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatTile value={dashboard.quotationsToday} label="Quotations Today" />
            <StatTile value={dashboard.quotationsThisMonth} label="Quotations This Month" />
            <StatTile value={dashboard.totalCustomers} label="Total Customers" />
            <StatTile value={dashboard.mostActiveStaff ?? "—"} label="Most Active Staff" />
            <StatTile value={dashboard.activeSignatureCount} label="Active Signatures" />
            <StatTile value={formatBytes(dashboard.storageBytes)} label="Storage Used (approx.)" />
          </div>

          <div className="mt-6 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Details</h2>
            <dl className="grid gap-3 sm:grid-cols-2 text-sm">
              <div>
                <dt className="text-slate-500 dark:text-slate-400">Last Quotation</dt>
                <dd className="text-slate-800 dark:text-slate-100">
                  {dashboard.lastQuotation
                    ? `#${String(dashboard.lastQuotation.quoteNumber).padStart(4, "0")} - ${dashboard.lastQuotation.customerName} (${new Date(dashboard.lastQuotation.createdAt).toLocaleDateString()})`
                    : "None yet"}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">Master Excel Version</dt>
                <dd className="text-slate-800 dark:text-slate-100">
                  {dashboard.masterExcelVersion ?? "Not uploaded"}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">Quotation Template Version</dt>
                <dd className="text-slate-800 dark:text-slate-100">{dashboard.templateVersion ?? "Not uploaded"}</dd>
              </div>
            </dl>
          </div>
        </>
      )}
    </div>
  );
}
