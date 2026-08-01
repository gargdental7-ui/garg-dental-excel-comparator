"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";
import {
  ApiError,
  type ExcelPreviewRow,
  type ExcelSource,
  type MasterExcelMetadata,
  type ProductColumnMapping,
  type QuotationImportedProduct,
} from "@/lib/types";
import { FileDropInput } from "@/components/FileDropInput";
import { ColumnMappingField } from "@/components/ColumnMappingField";
import { ErrorBanner } from "@/components/ErrorBanner";
import { ExcelPreviewTable } from "@/components/quotation/ExcelPreviewTable";
import { HeaderRowSelector } from "@/components/quotation/HeaderRowSelector";

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
  companyId,
}: {
  onImported: (products: QuotationImportedProduct[], fileName: string) => void;
  companyId?: string;
}) {
  const [excelSource, setExcelSource] = useState<ExcelSource>("upload");
  const [masterMeta, setMasterMeta] = useState<MasterExcelMetadata | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [sheet, setSheet] = useState<string>("");
  const [previewRows, setPreviewRows] = useState<ExcelPreviewRow[]>([]);
  const [detectedHeaderRow, setDetectedHeaderRow] = useState<number | null>(null);
  const [headerRow, setHeaderRow] = useState<number | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<ProductColumnMapping>(EMPTY_MAPPING);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imported, setImported] = useState(false);

  useEffect(() => {
    api.masterExcel.getMetadata(companyId).then(setMasterMeta).catch(() => setMasterMeta({ exists: false }));
  }, [companyId]);

  function resetFileState() {
    setSheetNames([]);
    setSheet("");
    setPreviewRows([]);
    setDetectedHeaderRow(null);
    setHeaderRow(null);
    setHeaders([]);
    setMapping(EMPTY_MAPPING);
    setImported(false);
  }

  async function loadFile(nextFile: File | null, nextSheet?: string, nextHeaderRow?: number, sourceOverride?: ExcelSource) {
    // sourceOverride exists because selectSource() calls setExcelSource()
    // and loadFile() in the same synchronous block - React state updates
    // aren't visible until the next render, so reading the `excelSource`
    // closure here would still see the *previous* value (e.g. still
    // "upload" right after switching to "company_master"), sending the
    // wrong excel_source to the backend and triggering "Please choose an
    // Excel file to upload" even though Company Master was selected.
    const source = sourceOverride ?? excelSource;
    setBusy(true);
    setError(null);
    try {
      const inspection = await api.quotation.inspectProducts(nextFile, nextSheet, nextHeaderRow, source, companyId);
      setSheetNames(inspection.sheet_names);
      setSheet(inspection.selected_sheet);
      setPreviewRows(inspection.preview_rows);
      setDetectedHeaderRow(inspection.detected_header_row);
      setHeaderRow(inspection.header_row);
      setHeaders(inspection.headers);
      setMapping(inspection.suggested_mapping);
      setImported(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
      setPreviewRows([]);
      setDetectedHeaderRow(null);
      setHeaderRow(null);
      setHeaders([]);
    } finally {
      setBusy(false);
    }
  }

  // Header row changes (clicking a preview row, typing a row number, or
  // "Use detected row") never require re-uploading the file - the browser
  // still holds it in `file` (or, for the company master source, the
  // backend re-downloads it from Storage), so this just re-requests with
  // the new header_row and the preview/mapping refresh from the response.
  function handleHeaderRowChange(row: number) {
    if (excelSource === "upload" && !file) return;
    setHeaderRow(row);
    loadFile(file, sheet, row);
  }

  async function handleImport() {
    if (!sheet || headerRow == null) return;
    if (excelSource === "upload" && !file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.quotation.importProducts(file, sheet, mapping, headerRow, excelSource, companyId);
      setImported(true);
      const sourceName = excelSource === "company_master" && masterMeta?.exists ? masterMeta.filename : (file?.name ?? "");
      onImported(result.products, sourceName);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
    } finally {
      setBusy(false);
    }
  }

  const canImport =
    (excelSource === "company_master" || !!file) && !!sheet && headerRow != null && !!mapping.product_name && !!mapping.price;

  function selectSource(source: ExcelSource) {
    setExcelSource(source);
    setFile(null);
    resetFileState();
    setError(null);
    if (source === "company_master") loadFile(null, undefined, undefined, source);
  }

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Product Excel</p>
      <ErrorBanner message={error} />

      <fieldset className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input type="radio" checked={excelSource === "upload"} onChange={() => selectSource("upload")} />
          Upload New Excel
        </label>
        <label
          className={`flex items-center gap-2 text-sm ${
            masterMeta?.exists ? "text-slate-700 dark:text-slate-300" : "text-slate-400 dark:text-slate-600"
          }`}
        >
          <input
            type="radio"
            checked={excelSource === "company_master"}
            disabled={!masterMeta?.exists}
            onChange={() => selectSource("company_master")}
          />
          Use Company Master Excel
          {masterMeta?.exists && <span className="text-xs text-slate-400 dark:text-slate-500">({masterMeta.filename})</span>}
        </label>
      </fieldset>
      {masterMeta !== null && !masterMeta.exists && (
        <p className="mb-3 text-xs text-slate-400 dark:text-slate-500">No Company Master Excel has been uploaded.</p>
      )}

      <div className="mt-3 space-y-3">
        {excelSource === "upload" && (
          <FileDropInput
            label="Product Excel"
            fileName={file?.name ?? null}
            fileSize={file?.size}
            onChange={(f) => {
              setFile(f);
              resetFileState();
              loadFile(f);
            }}
            onClear={() => {
              setFile(null);
              resetFileState();
              setError(null);
            }}
          />
        )}

        {sheetNames.length > 1 && (
          <div className="flex items-center gap-3">
            <label className="text-sm text-slate-700 dark:text-slate-300">Sheet:</label>
            <select
              value={sheet}
              onChange={(e) => {
                setSheet(e.target.value);
                loadFile(file, e.target.value);
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

        {previewRows.length > 0 && (
          <div className="space-y-3">
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Excel Preview</p>
              <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
                The highlighted row is used as the header. Click any row below to use it instead.
              </p>
              <ExcelPreviewTable rows={previewRows} headerRow={headerRow} onSelectRow={handleHeaderRowChange} />
            </div>

            <HeaderRowSelector
              detectedRow={detectedHeaderRow}
              headerRow={headerRow}
              maxRow={previewRows[previewRows.length - 1]?.row ?? previewRows.length}
              onChange={handleHeaderRowChange}
            />
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

        {previewRows.length > 0 && (
          <button
            type="button"
            disabled={!canImport || busy}
            onClick={handleImport}
            title={
              headerRow == null
                ? "Choose a header row above first"
                : !mapping.product_name || !mapping.price
                  ? "Map Product Name and Price above first"
                  : undefined
            }
            className="rounded-md bg-slate-800 dark:bg-slate-100 px-4 py-2 text-sm font-semibold text-white dark:text-slate-900 disabled:opacity-50"
          >
            {busy ? "Working..." : imported ? "Re-import Products" : "Import Products"}
          </button>
        )}
      </div>
    </div>
  );
}
