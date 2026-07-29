"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FilePlus2, FileSpreadsheet, FileText, History, Layers } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { CompanySelector } from "@/components/CompanySelector";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError, type Company, type QuotationHistoryEntry } from "@/lib/types";

const ACTIONS = [
  {
    icon: FilePlus2,
    title: "Create New Quote",
    description: "Start a fresh quotation - Excel-assisted or fully manual.",
  },
  {
    icon: FileSpreadsheet,
    title: "Import Product Excel",
    description: "Jump straight into Excel-assisted mode with a product list.",
  },
];

export default function QuotationDashboardPage() {
  const me = useCurrentUser();
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [recent, setRecent] = useState<QuotationHistoryEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isSuperAdmin = me?.role === "super_admin";
  const resolvedCompanyId = isSuperAdmin ? companyId : (me?.companyId ?? null);

  useEffect(() => {
    if (!resolvedCompanyId) return;
    let cancelled = false;
    api.companies
      .list()
      .then((res) => {
        if (cancelled) return;
        setCompany(res.companies.find((c) => c.id === resolvedCompanyId) ?? null);
      })
      .catch(() => {
        // Non-fatal - the page still works without the display name.
      });
    api.quotationHistory
      .list({ companyId: resolvedCompanyId, page: 1 })
      .then((res) => {
        if (cancelled) return;
        setRecent(res.quotations.slice(0, 5));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail.message : "Could not load recent quotations.");
      });
    return () => {
      cancelled = true;
    };
  }, [resolvedCompanyId]);

  if (me === undefined) return null;
  if (me === null) return null;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <PageHeader
        icon={FileText}
        title="Smart Quotation Generator"
        description={company ? `${company.displayName} - build a professional proposal in minutes.` : "Build a professional proposal in minutes."}
      />

      {isSuperAdmin && (
        <div className="mb-6">
          <CompanySelector value={companyId} onChange={setCompanyId} />
        </div>
      )}

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {resolvedCompanyId && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {ACTIONS.map(({ icon: Icon, title, description }) => (
              <Link
                key={title}
                href={`/quotation/new?company_id=${encodeURIComponent(resolvedCompanyId)}`}
                className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 transition hover:border-slate-400 dark:hover:border-slate-600 hover:shadow-md"
              >
                <Icon className="h-5 w-5 text-brand-cyan" />
                <h2 className="mt-3 text-base font-semibold text-slate-900 dark:text-slate-50">{title}</h2>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{description}</p>
              </Link>
            ))}
            <Link
              href="/quotation/history"
              className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 transition hover:border-slate-400 dark:hover:border-slate-600 hover:shadow-md"
            >
              <History className="h-5 w-5 text-brand-cyan" />
              <h2 className="mt-3 text-base font-semibold text-slate-900 dark:text-slate-50">Quotation History</h2>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Reopen or re-download a past quotation.</p>
            </Link>
            {isSuperAdmin && (
              <Link
                href="/settings/company-assets"
                className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 transition hover:border-slate-400 dark:hover:border-slate-600 hover:shadow-md"
              >
                <Layers className="h-5 w-5 text-brand-cyan" />
                <h2 className="mt-3 text-base font-semibold text-slate-900 dark:text-slate-50">Company Assets</h2>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Manage the branded template, logo, and signatures.</p>
              </Link>
            )}
          </div>

          <div className="mt-10">
            <div className="mb-3 flex items-center gap-2">
              <History className="h-4 w-4 text-slate-500" />
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Recent Quotes</h2>
            </div>
            <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
              {recent === null ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Loading...</p>
              ) : recent.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">No quotations yet.</p>
              ) : (
                <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                  {recent.map((q) => (
                    <li key={q.id} className="flex justify-between py-2 text-sm">
                      <span>
                        #{String(q.quoteNumber).padStart(4, "0")} - {q.customerName}
                      </span>
                      <span className="text-slate-500">{new Date(q.createdAt).toLocaleDateString()}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
