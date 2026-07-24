"use client";

import { useState } from "react";
import { api, downloadBlob } from "@/lib/apiClient";
import { ApiError, type CellDifference, type ColumnMappingPair, type ComparatorAnalyzeResult } from "@/lib/types";
import { FileDropInput } from "@/components/FileDropInput";
import { ColumnMappingBuilder } from "@/components/ColumnMappingBuilder";
import { MappedComparisonResults } from "@/components/MappedComparisonResults";
import { StatsPanel } from "@/components/StatsPanel";
import { PreviewTable } from "@/components/PreviewTable";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";

export default function ComparatorPage() {
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [omsFile, setOmsFile] = useState<File | null>(null);
  const [currentHeaders, setCurrentHeaders] = useState<string[]>([]);
  const [omsHeaders, setOmsHeaders] = useState<string[]>([]);
  const [mappings, setMappings] = useState<ColumnMappingPair[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComparatorAnalyzeResult | null>(null);
  const [exporting, setExporting] = useState(false);

  async function loadPair(nextCurrent: File | null, nextOms: File | null) {
    if (!nextCurrent || !nextOms) return;
    setBusy(true);
    setError(null);
    try {
      const inspection = await api.comparator.inspect(nextCurrent, nextOms);
      setCurrentHeaders(inspection.current_headers);
      setOmsHeaders(inspection.oms_headers);
      // Auto-seed mappings from identically-named shared columns (today's
      // default behavior) - the user can still repoint any pair to a
      // differently-named column, or add more.
      setMappings(inspection.comparable_columns.map((col) => ({ current_column: col, latest_column: col })));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
      setCurrentHeaders([]);
      setOmsHeaders([]);
      setMappings([]);
    } finally {
      setBusy(false);
    }
  }

  async function handleCompare() {
    if (!currentFile || !omsFile) return;
    if (mappings.length === 0) {
      setError("Please map at least one column to compare.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const analysis = await api.comparator.analyze(currentFile, omsFile, mappings);
      setResult(analysis);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
    } finally {
      setBusy(false);
    }
  }

  async function handleExport() {
    if (!currentFile || !omsFile) return;
    setExporting(true);
    setError(null);
    try {
      const { blob, filename } = await api.comparator.export(currentFile, omsFile, mappings);
      downloadBlob(blob, filename);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
    } finally {
      setExporting(false);
    }
  }

  function reset() {
    setCurrentFile(null);
    setOmsFile(null);
    setCurrentHeaders([]);
    setOmsHeaders([]);
    setMappings([]);
    setResult(null);
    setError(null);
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Excel Comparator</h1>
      <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
        Compare two Excel reports by product Code. Map one column for a quick single-field check, or several
        (including differently-named columns) for a full Column Comparison Report.
      </p>

      <ErrorBanner message={error} />

      {!result && (
        <div className="mt-4 space-y-4">
          <FileDropInput
            label="Current File"
            fileName={currentFile?.name ?? null}
            onChange={(file) => {
              setCurrentFile(file);
              loadPair(file, omsFile);
            }}
          />
          <FileDropInput
            label="Latest OMS File"
            fileName={omsFile?.name ?? null}
            onChange={(file) => {
              setOmsFile(file);
              loadPair(currentFile, file);
            }}
          />

          {currentHeaders.length > 0 && omsHeaders.length > 0 && (
            <ColumnMappingBuilder
              currentHeaders={currentHeaders}
              omsHeaders={omsHeaders}
              mappings={mappings}
              onChange={setMappings}
            />
          )}

          <Button disabled={!currentFile || !omsFile || busy || mappings.length === 0} onClick={handleCompare}>
            {busy ? "Working..." : "Compare Files"}
          </Button>
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-4">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-50">
            {result.mode === "mapped" ? "Column Comparison Report" : "Comparison Complete"}
          </h2>

          {result.mode === "legacy" && (
            <>
              <StatsPanel
                items={[
                  { label: "Products Compared", value: result.stats.total_compared.toLocaleString() },
                  { label: "Rows With Differences", value: result.stats.total_differences.toLocaleString() },
                  { label: "Field Changes", value: result.stats.total_field_differences.toLocaleString() },
                  { label: "New Codes In OMS", value: result.stats.new_codes_count.toLocaleString() },
                  { label: "Missing From OMS", value: result.stats.missing_from_oms_count.toLocaleString() },
                  { label: "Columns Compared", value: result.stats.compared_columns.join(", ") },
                ]}
              />

              {result.stats.duplicate_warnings.length > 0 && (
                <div className="rounded-md border border-amber-300 bg-amber-50 dark:border-amber-900 dark:bg-amber-950 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
                  <p className="mb-1 font-semibold">Duplicate Codes Found</p>
                  <ul className="list-disc pl-5">
                    {result.stats.duplicate_warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              <PreviewTable<CellDifference>
                rows={result.cell_differences_preview}
                totalCount={result.cell_differences_total_count}
                emptyMessage="No differences were found."
                columns={[
                  { header: "Code", render: (r) => r.code },
                  { header: "Column", render: (r) => r.column },
                  { header: "Old Value (Current File)", render: (r) => String(r.old_value ?? "") },
                  { header: "New Value (OMS File)", render: (r) => String(r.new_value ?? "") },
                ]}
              />
            </>
          )}

          {result.mode === "mapped" && <MappedComparisonResults result={result} />}

          <div className="flex gap-3">
            <Button onClick={handleExport} disabled={exporting}>
              {exporting ? "Preparing..." : "Save Result Excel"}
            </Button>
            <Button variant="secondary" onClick={reset}>
              New Comparison
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
