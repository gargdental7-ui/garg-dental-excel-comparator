"use client";

import { useState } from "react";
import { api } from "@/lib/apiClient";
import { ApiError, type ProductColumnMapping, type QuotationImportedProduct } from "@/lib/types";
import { FileDropInput } from "@/components/FileDropInput";
import { ColumnMappingField } from "@/components/ColumnMappingField";
import { ErrorBanner } from "@/components/ErrorBanner";

const EMPTY_MAPPING: ProductColumnMapping = {
  product_name: null,
  price: null,
  code: null,
  description: null,
  brand: null,
  model: null,
  origin: null,
  category: null,
  warranty: null,
  mrp: null,
  image_path: null,
};

export function ProductImportPanel({
  onImported,
}: {
  onImported: (products: QuotationImportedProduct[], fileName: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [sheet, setSheet] = useState<string>("");
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<ProductColumnMapping>(EMPTY_MAPPING);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imported, setImported] = useState(false);

  async function loadFile(nextFile: File, nextSheet?: string) {
    setBusy(true);
    setError(null);
    try {
      const inspection = await api.quotation.inspectProducts(nextFile, nextSheet);
      setSheetNames(inspection.sheet_names);
      setSheet(inspection.selected_sheet);
      setHeaders(inspection.headers);
      setMapping(inspection.suggested_mapping);
      setImported(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
      setHeaders([]);
    } finally {
      setBusy(false);
    }
  }

  async function handleImport() {
    if (!file || !sheet) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.quotation.importProducts(file, sheet, mapping);
      setImported(true);
      onImported(result.products, file.name);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
    } finally {
      setBusy(false);
    }
  }

  const canImport = !!file && !!sheet && !!mapping.product_name && !!mapping.price;

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Upload Product Excel</p>
      <ErrorBanner message={error} />
      <div className="mt-3 space-y-3">
        <FileDropInput
          label="Product Excel"
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
          <div className="rounded-md border border-slate-200 dark:border-slate-800 p-3">
            <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Column Mapping</p>
            <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
              Tell us which column in your file holds each piece of information. Anything left unmapped stays blank
              for manual completion.
            </p>
            <ColumnMappingField
              label="Product Name"
              required
              headers={headers}
              value={mapping.product_name}
              onChange={(v) => setMapping({ ...mapping, product_name: v })}
            />
            <ColumnMappingField
              label="Price"
              required
              headers={headers}
              value={mapping.price}
              onChange={(v) => setMapping({ ...mapping, price: v })}
            />
            <ColumnMappingField
              label="Code"
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
              label="Brand"
              headers={headers}
              value={mapping.brand}
              onChange={(v) => setMapping({ ...mapping, brand: v })}
            />
            <ColumnMappingField
              label="Model"
              headers={headers}
              value={mapping.model}
              onChange={(v) => setMapping({ ...mapping, model: v })}
            />
            <ColumnMappingField
              label="Origin"
              headers={headers}
              value={mapping.origin}
              onChange={(v) => setMapping({ ...mapping, origin: v })}
            />
            <ColumnMappingField
              label="Category"
              headers={headers}
              value={mapping.category}
              onChange={(v) => setMapping({ ...mapping, category: v })}
            />
            <ColumnMappingField
              label="Warranty"
              headers={headers}
              value={mapping.warranty}
              onChange={(v) => setMapping({ ...mapping, warranty: v })}
            />
            <ColumnMappingField
              label="MRP"
              headers={headers}
              value={mapping.mrp}
              onChange={(v) => setMapping({ ...mapping, mrp: v })}
            />
            <ColumnMappingField
              label="Image Path (optional)"
              headers={headers}
              value={mapping.image_path}
              onChange={(v) => setMapping({ ...mapping, image_path: v })}
            />
          </div>
        )}

        {headers.length > 0 && (
          <button
            type="button"
            disabled={!canImport || busy}
            onClick={handleImport}
            className="rounded-md bg-slate-800 dark:bg-slate-100 px-4 py-2 text-sm font-semibold text-white dark:text-slate-900 disabled:opacity-50"
          >
            {busy ? "Working..." : imported ? "Re-import Products" : "Import Products"}
          </button>
        )}
      </div>
    </div>
  );
}
