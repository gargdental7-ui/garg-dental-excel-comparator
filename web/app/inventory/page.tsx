"use client";

import { useState } from "react";
import { api, downloadBlob } from "@/lib/apiClient";
import {
  ApiError,
  type InventoryAnalyzeResponse,
  type InventoryColumnMapping,
  type ProductMovement,
} from "@/lib/types";
import { FileDropInput } from "@/components/FileDropInput";
import { ColumnMappingField } from "@/components/ColumnMappingField";
import { ThresholdField } from "@/components/ThresholdField";
import { StatsPanel } from "@/components/StatsPanel";
import { PreviewTable } from "@/components/PreviewTable";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";

const EMPTY_MAPPING: InventoryColumnMapping = {
  code: null,
  description: null,
  unit: null,
  opening: null,
  received: null,
  delivered: null,
  balance: null,
  unit_cost: null,
  stock_value: null,
  brand: null,
  category: null,
};

// UI collects/shows these as percentages (70, 30); converted to 0-1 ratios
// (0.70, 0.30) just before sending, mirroring _read_thresholds in the
// desktop app's inventory_page.py.
const DEFAULT_THRESHOLD_PERCENTS = { fast_percent: 70, normal_percent: 30 };

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export default function InventoryPage() {
  const [file, setFile] = useState<File | null>(null);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [sheet, setSheet] = useState<string>("");
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<InventoryColumnMapping>(EMPTY_MAPPING);
  const [thresholdPercents, setThresholdPercents] = useState(DEFAULT_THRESHOLD_PERCENTS);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InventoryAnalyzeResponse | null>(null);

  function thresholdsPayload() {
    return {
      fast_ratio: thresholdPercents.fast_percent / 100,
      normal_ratio: thresholdPercents.normal_percent / 100,
    };
  }

  async function loadFile(nextFile: File, nextSheet?: string) {
    setBusy(true);
    setError(null);
    try {
      const inspection = await api.inventory.inspect(nextFile, nextSheet);
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
      const analysis = await api.inventory.analyze(file, sheet, mapping, thresholdsPayload());
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
      const { blob, filename } = await api.inventory.export(file, sheet, mapping, thresholdsPayload());
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
    setThresholdPercents(DEFAULT_THRESHOLD_PERCENTS);
    setResult(null);
    setError(null);
  }

  const requiredMapped =
    mapping.code && mapping.opening && mapping.received && mapping.delivered && mapping.balance;

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Inventory Movement Analyzer</h1>
      <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
        Upload a stock movement report to classify fast/slow/dead stock for the uploaded period.
      </p>

      <ErrorBanner message={error} />

      {!result && (
        <div className="mt-4 space-y-4">
          <FileDropInput
            label="Inventory / Stock Movement File"
            fileName={file?.name ?? null}
            onChange={(f) => {
              setFile(f);
              loadFile(f);
            }}
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
                  label="Product Code"
                  required
                  headers={headers}
                  value={mapping.code}
                  onChange={(v) => setMapping({ ...mapping, code: v })}
                />
                <ColumnMappingField
                  label="Description"
                  headers={headers}
                  value={mapping.description}
                  onChange={(v) => setMapping({ ...mapping, description: v })}
                />
                <ColumnMappingField
                  label="Unit"
                  headers={headers}
                  value={mapping.unit}
                  onChange={(v) => setMapping({ ...mapping, unit: v })}
                />
                <ColumnMappingField
                  label="Opening Quantity"
                  required
                  headers={headers}
                  value={mapping.opening}
                  onChange={(v) => setMapping({ ...mapping, opening: v })}
                />
                <ColumnMappingField
                  label="Received Quantity"
                  required
                  headers={headers}
                  value={mapping.received}
                  onChange={(v) => setMapping({ ...mapping, received: v })}
                />
                <ColumnMappingField
                  label="Delivered Quantity"
                  required
                  headers={headers}
                  value={mapping.delivered}
                  onChange={(v) => setMapping({ ...mapping, delivered: v })}
                />
                <ColumnMappingField
                  label="Current Balance"
                  required
                  headers={headers}
                  value={mapping.balance}
                  onChange={(v) => setMapping({ ...mapping, balance: v })}
                />
                <ColumnMappingField
                  label="Unit Cost (optional)"
                  headers={headers}
                  value={mapping.unit_cost}
                  onChange={(v) => setMapping({ ...mapping, unit_cost: v })}
                />
                <ColumnMappingField
                  label="Stock Value (optional)"
                  headers={headers}
                  value={mapping.stock_value}
                  onChange={(v) => setMapping({ ...mapping, stock_value: v })}
                />
                <ColumnMappingField
                  label="Brand (optional)"
                  headers={headers}
                  value={mapping.brand}
                  onChange={(v) => setMapping({ ...mapping, brand: v })}
                />
                <ColumnMappingField
                  label="Category (optional)"
                  headers={headers}
                  value={mapping.category}
                  onChange={(v) => setMapping({ ...mapping, category: v })}
                />
              </div>

              <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
                <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
                  Movement Rules (editable)
                </p>
                <ThresholdField
                  label="Fast Moving Ratio ≥"
                  suffix="%"
                  value={thresholdPercents.fast_percent}
                  onChange={(v) => setThresholdPercents({ ...thresholdPercents, fast_percent: v })}
                />
                <ThresholdField
                  label="Normal Moving Ratio ≥"
                  suffix="%"
                  value={thresholdPercents.normal_percent}
                  onChange={(v) => setThresholdPercents({ ...thresholdPercents, normal_percent: v })}
                />
                <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                  Movement Ratio = Delivered &divide; (Opening + Received) for the uploaded period only. Negative
                  Balance &rarr; NEGATIVE STOCK. Balance = 0 &rarr; OUT OF STOCK. Delivered = 0 and Balance &gt; 0
                  &rarr; NO MOVEMENT. Otherwise classified by the ratio above. A single period cannot prove
                  permanent dead stock - results describe the uploaded period only.
                </p>
              </div>

              <Button disabled={busy || !requiredMapped} onClick={handleAnalyze}>
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
              { label: "Total Products Analyzed", value: result.stats.total_products.toLocaleString() },
              { label: "Fast Moving", value: (result.stats.counts["FAST MOVING"] ?? 0).toLocaleString() },
              { label: "Normal Moving", value: (result.stats.counts["NORMAL MOVING"] ?? 0).toLocaleString() },
              { label: "Slow Moving", value: (result.stats.counts["SLOW MOVING"] ?? 0).toLocaleString() },
              { label: "No Movement", value: (result.stats.counts["NO MOVEMENT"] ?? 0).toLocaleString() },
              { label: "Negative Stock", value: (result.stats.counts["NEGATIVE STOCK"] ?? 0).toLocaleString() },
              { label: "Out Of Stock", value: (result.stats.counts["OUT OF STOCK"] ?? 0).toLocaleString() },
              { label: "Stock Exceptions", value: result.stats.exceptions_count.toLocaleString() },
              ...(result.stats.has_value_data
                ? [
                    { label: "Total Inventory Value", value: fmt(result.stats.total_inventory_value ?? 0) },
                    { label: "Value In No-Movement Stock", value: fmt(result.stats.value_no_movement ?? 0) },
                    { label: "Value In Slow-Moving Stock", value: fmt(result.stats.value_slow_moving ?? 0) },
                  ]
                : []),
            ]}
          />

          <PreviewTable<ProductMovement>
            rows={result.products_preview}
            totalCount={result.products_total_count}
            emptyMessage="No products were found."
            columns={[
              { header: "Code", render: (r) => r.code },
              { header: "Description", render: (r) => String(r.description ?? "") },
              { header: "Classification", render: (r) => r.classification },
              { header: "Balance", render: (r) => r.balance },
              { header: "Movement Ratio", render: (r) => r.movement_ratio.toFixed(2) },
            ]}
          />

          {result.exceptions_total_count > 0 && (
            <PreviewTable
              rows={result.exceptions_preview}
              totalCount={result.exceptions_total_count}
              columns={[
                { header: "Code", render: (r) => r.code },
                { header: "Reason", render: (r) => r.reason },
              ]}
            />
          )}

          <div className="flex gap-3">
            <Button onClick={handleExport} disabled={exporting}>
              {exporting ? "Preparing..." : "Export Inventory Analysis"}
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
