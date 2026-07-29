"use client";

import { useEffect, useState } from "react";
import { History, FileText, FileDown } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Table, type TableColumn } from "@/components/ui/Table";
import { Pagination } from "@/components/ui/Pagination";
import { Badge } from "@/components/ui/Badge";
import { CompanySelector } from "@/components/CompanySelector";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { QuotationHistoryEntry } from "@/lib/types";

export default function QuotationHistoryPage() {
  const me = useCurrentUser();
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [entries, setEntries] = useState<QuotationHistoryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [customer, setCustomer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const isSuperAdmin = me?.role === "super_admin";

  useEffect(() => {
    if (!me) return;
    if (isSuperAdmin && !companyId) return; // waiting on the company selector
    let cancelled = false;
    api.quotationHistory
      .list({ companyId: companyId ?? undefined, customer: customer || undefined, page })
      .then((res) => {
        if (cancelled) return;
        setEntries(res.quotations);
        setTotal(res.total);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.detail.message : "Could not load quotation history.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [me, isSuperAdmin, companyId, customer, page]);

  if (me === undefined) return null;
  if (me === null) return null;

  const columns: TableColumn<QuotationHistoryEntry>[] = [
    { header: "Quote #", render: (q) => `#${String(q.quoteNumber).padStart(4, "0")}` },
    { header: "Customer", render: (q) => q.customerName },
    ...(isSuperAdmin ? [{ header: "Staff", render: (q: QuotationHistoryEntry) => q.createdBy }] : []),
    { header: "Date", render: (q) => new Date(q.createdAt).toLocaleDateString() },
    {
      header: "Status",
      render: (q) => (q.status === "final" ? <Badge tone="success">Final</Badge> : <Badge tone="warning">PDF Pending</Badge>),
    },
    {
      header: "Download",
      render: (q) => (
        <div className="flex gap-2">
          <a
            href={api.quotationHistory.downloadDocxUrl(q.id, companyId ?? undefined)}
            title="Download DOCX"
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <FileText className="h-4 w-4" />
          </a>
          {q.hasPdf && (
            <a
              href={api.quotationHistory.downloadPdfUrl(q.id, companyId ?? undefined)}
              title="Download PDF"
              className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <FileDown className="h-4 w-4" />
            </a>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-5xl p-6">
      <PageHeader
        icon={History}
        title="Quotation History"
        description={isSuperAdmin ? "Search and reopen every quotation for a company." : "Quotations you've generated."}
      />

      {isSuperAdmin && (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <CompanySelector value={companyId} onChange={setCompanyId} />
          <input
            type="text"
            placeholder="Search by customer name..."
            value={customer}
            onChange={(e) => {
              setLoading(true);
              setCustomer(e.target.value);
              setPage(1);
            }}
            className="w-full max-w-sm rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500"
          />
        </div>
      )}

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <Table
        columns={columns}
        rows={entries}
        rowKey={(q) => q.id}
        emptyMessage={loading ? "Loading..." : "No quotations yet."}
      />
      <Pagination
        page={page}
        pageSize={25}
        total={total}
        onChange={(newPage) => {
          setLoading(true);
          setPage(newPage);
        }}
      />
    </div>
  );
}
