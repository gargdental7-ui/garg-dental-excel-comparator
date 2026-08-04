"use client";

import { useState } from "react";
import { Landmark } from "lucide-react";
import { api, downloadBlob } from "@/lib/apiClient";
import {
  ApiError,
  type CollectionAnalyzeResponse,
  type CollectionColumnMapping,
  type CustomerSummary,
} from "@/lib/types";
import { FileDropInput } from "@/components/FileDropInput";
import { ColumnMappingField } from "@/components/ColumnMappingField";
import { ThresholdField } from "@/components/ThresholdField";
import { StatsPanel } from "@/components/StatsPanel";
import { PreviewTable } from "@/components/PreviewTable";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";
import { PageHeader } from "@/components/PageHeader";

const EMPTY_MAPPING: CollectionColumnMapping = {
  customer: null,
  amount: null,
  days_overdue: null,
  due_date: null,
  last_payment_date: null,
  salesperson: null,
  invoice_number: null,
};

const DEFAULT_THRESHOLDS = {
  critical_days: 90,
  high_days: 60,
  medium_days: 30,
  critical_amount: 100000,
  high_amount: 50000,
};

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export default function CollectionPage() {
  const [file, setFile] = useState<File | null>(null);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [sheet, setSheet] = useState<string>("");
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<CollectionColumnMapping>(EMPTY_MAPPING);
  const [thresholds, setThresholds] = useState(DEFAULT_THRESHOLDS);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CollectionAnalyzeResponse | null>(null);

  async function loadFile(nextFile: File, nextSheet?: string) {
    setBusy(true);
    setError(null);
    try {
      const inspection = await api.collection.inspect(nextFile, nextSheet);
      setSheetNames(inspection.sheet_names);
      setSheet(inspection.selected_sheet);
      setHeaders(inspection.headers);
      setMapping(inspection.suggested_mapping);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
      setHeaders([]);
    } finally {
      setBusy(false);
    }
  }

  async function handleAnalyze() {
    if (!file || !sheet) return;
    setBusy(true);
    setError(null);
    try {
      const analysis = await api.collection.analyze(file, sheet, mapping, thresholds);
      setResult(analysis);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
    } finally {
      setBusy(false);
    }
  }

  async function handleExport() {
    if (!file || !sheet) return;
    setExporting(true);
    setError(null);
    try {
      const { blob, filename } = await api.collection.export(file, sheet, mapping, thresholds);
      downloadBlob(blob, filename);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
    } finally {
      setExporting(false);
    }
  }

  function reset() {
    setFile(null);
    setSheetNames([]);
    setSheet("");
    setHeaders([]);
    setMapping(EMPTY_MAPPING);
    setThresholds(DEFAULT_THRESHOLDS);
    setResult(null);
    setError(null);
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <PageHeader
        icon={Landmark}
        title="Collection Priority Analyzer"
        description="Upload an outstanding/receivables report to find out who to follow up with first."
      />

      <ErrorBanner message={error} />

      {!result && (
        <div className="mt-4 space-y-4">
          <FileDropInput
            label="Outstanding / Receivables File"
            fileName={file?.name ?? null}
            fileSize={file?.size}
            onChange={(f) => {
              setFile(f);
              loadFile(f);
            }}
            onClear={reset}
          />

          {sheetNames.length > 1 && (
            <div className="flex items-center gap-3">
              <label className="text-sm text-slate-700 dark:text-slate-300">Sheet:</label>
              <select
                value={sheet}
                onChange={(e) => {
                  setSheet(e.target.value);
                  if (file) loadFile(file, e.target.value);
                }}
                className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm"
              >
                {sheetNames.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          )}

          {headers.length > 0 && (
            <>
              <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
                <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Column Mapping</p>
                <ColumnMappingField
                  label="Customer / Party Name"
                  required
                  headers={headers}
                  value={mapping.customer}
                  onChange={(v) => setMapping({ ...mapping, customer: v })}
                />
                <ColumnMappingField
                  label="Outstanding Amount"
                  required
                  headers={headers}
                  value={mapping.amount}
                  onChange={(v) => setMapping({ ...mapping, amount: v })}
                />
                <ColumnMappingField
                  label="Days Overdue"
                  headers={headers}
                  value={mapping.days_overdue}
                  onChange={(v) => setMapping({ ...mapping, days_overdue: v })}
                />
                <ColumnMappingField
                  label="Due Date"
                  headers={headers}
                  value={mapping.due_date}
                  onChange={(v) => setMapping({ ...mapping, due_date: v })}
                />
                <ColumnMappingField
                  label="Last Payment Date"
                  headers={headers}
                  value={mapping.last_payment_date}
                  onChange={(v) => setMapping({ ...mapping, last_payment_date: v })}
                />
                <ColumnMappingField
                  label="Salesperson"
                  headers={headers}
                  value={mapping.salesperson}
                  onChange={(v) => setMapping({ ...mapping, salesperson: v })}
                />
                <ColumnMappingField
                  label="Invoice Number"
                  headers={headers}
                  value={mapping.invoice_number}
                  onChange={(v) => setMapping({ ...mapping, invoice_number: v })}
                />
              </div>

              <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
                <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
                  Priority Rules (editable)
                </p>
                <ThresholdField
                  label="Critical Overdue Days"
                  value={thresholds.critical_days}
                  onChange={(v) => setThresholds({ ...thresholds, critical_days: v })}
                />
                <ThresholdField
                  label="High Overdue Days"
                  value={thresholds.high_days}
                  onChange={(v) => setThresholds({ ...thresholds, high_days: v })}
                />
                <ThresholdField
                  label="Medium Overdue Days"
                  value={thresholds.medium_days}
                  onChange={(v) => setThresholds({ ...thresholds, medium_days: v })}
                />
                <ThresholdField
                  label="Critical Amount"
                  value={thresholds.critical_amount}
                  onChange={(v) => setThresholds({ ...thresholds, critical_amount: v })}
                />
                <ThresholdField
                  label="High Amount"
                  value={thresholds.high_amount}
                  onChange={(v) => setThresholds({ ...thresholds, high_amount: v })}
                />
                <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                  Rule: CRITICAL if overdue days or amount clear the Critical bar; HIGH if they clear the High bar;
                  MEDIUM if overdue days clear the Medium bar; otherwise NORMAL. Accounts with 3+ open invoices
                  move up one priority level. Nothing owed (&le; 0) is always NORMAL.
                </p>
              </div>

              <Button disabled={busy || !mapping.customer || !mapping.amount} onClick={handleAnalyze}>
                {busy ? "Working..." : "Analyze"}
              </Button>
            </>
          )}
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-4">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-50">Analysis Complete</h2>
          <StatsPanel
            items={[
              { label: "Total Outstanding", value: fmt(result.stats.total_outstanding) },
              { label: "Total Customers With Outstanding", value: result.stats.total_customers.toLocaleString() },
              { label: "Critical Accounts", value: result.stats.critical_count.toLocaleString() },
              { label: "High Priority Accounts", value: result.stats.high_count.toLocaleString() },
              { label: "Amount Over 90 Days", value: fmt(result.stats.amount_over_90) },
            ]}
          />

          <PreviewTable<CustomerSummary>
            rows={result.customers_preview}
            totalCount={result.customers_total_count}
            emptyMessage="No customers with activity were found."
            columns={[
              { header: "Customer", render: (r) => r.customer },
              { header: "Priority", render: (r) => r.priority },
              { header: "Total Outstanding", render: (r) => fmt(r.total_outstanding) },
              { header: "Invoices", render: (r) => r.invoice_count },
              { header: "Max Days Overdue", render: (r) => r.max_days_overdue },
              { header: "Salesperson", render: (r) => r.salesperson ?? "" },
            ]}
          />

          <div className="flex flex-wrap gap-3">
            <Button onClick={handleExport} disabled={exporting}>
              {exporting ? "Preparing..." : "Export Collection Report"}
            </Button>
            <Button variant="secondary" onClick={reset}>
              New Analysis
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
