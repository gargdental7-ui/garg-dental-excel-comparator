import {
  ApiError,
  type ApiErrorDetail,
  type CollectionAnalyzeResponse,
  type CollectionInspectResponse,
  type ComparatorAnalyzeResponse,
  type ComparatorInspectResponse,
  type GenerateQuotationRequest,
  type InventoryAnalyzeResponse,
  type InventoryInspectResponse,
  type ProductColumnMapping,
  type QuotationProductsImportResponse,
  type QuotationProductsInspectResponse,
} from "./types";

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(path, { method: "POST", body: form });
  if (!res.ok) {
    let detail: ApiErrorDetail = { message: "An unexpected error occurred." };
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response wasn't JSON - keep the generic message
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

async function postFormForBlob(path: string, form: FormData): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(path, { method: "POST", body: form });
  if (!res.ok) {
    let detail: ApiErrorDetail = { message: "An unexpected error occurred." };
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response wasn't JSON - keep the generic message
    }
    throw new ApiError(res.status, detail);
  }
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  const filename = match ? match[1] : "result.xlsx";
  const blob = await res.blob();
  return { blob, filename };
}

async function postJsonForBlob(path: string, body: unknown): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail: ApiErrorDetail = { message: "An unexpected error occurred." };
    try {
      const errorBody = await res.json();
      if (errorBody?.detail) detail = errorBody.detail;
    } catch {
      // response wasn't JSON - keep the generic message
    }
    throw new ApiError(res.status, detail);
  }
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  const filename = match ? match[1] : "quotation.docx";
  const blob = await res.blob();
  return { blob, filename };
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  comparator: {
    inspect: (currentFile: File, omsFile: File) => {
      const form = new FormData();
      form.append("current_file", currentFile);
      form.append("oms_file", omsFile);
      return postForm<ComparatorInspectResponse>(`/api/comparator/inspect`, form);
    },
    analyze: (currentFile: File, omsFile: File, selectedColumns: string[]) => {
      const form = new FormData();
      form.append("current_file", currentFile);
      form.append("oms_file", omsFile);
      form.append("selected_columns", JSON.stringify(selectedColumns));
      return postForm<ComparatorAnalyzeResponse>(`/api/comparator/analyze`, form);
    },
    export: (currentFile: File, omsFile: File, selectedColumns: string[]) => {
      const form = new FormData();
      form.append("current_file", currentFile);
      form.append("oms_file", omsFile);
      form.append("selected_columns", JSON.stringify(selectedColumns));
      return postFormForBlob(`/api/comparator/export`, form);
    },
  },
  collection: {
    inspect: (file: File, sheet?: string) => {
      const form = new FormData();
      form.append("file", file);
      if (sheet) form.append("sheet", sheet);
      return postForm<CollectionInspectResponse>(`/api/collection/inspect`, form);
    },
    analyze: (file: File, sheet: string, mapping: object, thresholds: object) => {
      const form = new FormData();
      form.append("file", file);
      form.append("sheet", sheet);
      form.append("mapping", JSON.stringify(mapping));
      form.append("thresholds", JSON.stringify(thresholds));
      return postForm<CollectionAnalyzeResponse>(`/api/collection/analyze`, form);
    },
    export: (file: File, sheet: string, mapping: object, thresholds: object) => {
      const form = new FormData();
      form.append("file", file);
      form.append("sheet", sheet);
      form.append("mapping", JSON.stringify(mapping));
      form.append("thresholds", JSON.stringify(thresholds));
      return postFormForBlob(`/api/collection/export`, form);
    },
  },
  inventory: {
    inspect: (file: File, sheet?: string) => {
      const form = new FormData();
      form.append("file", file);
      if (sheet) form.append("sheet", sheet);
      return postForm<InventoryInspectResponse>(`/api/inventory/inspect`, form);
    },
    analyze: (file: File, sheet: string, mapping: object, thresholds: object) => {
      const form = new FormData();
      form.append("file", file);
      form.append("sheet", sheet);
      form.append("mapping", JSON.stringify(mapping));
      form.append("thresholds", JSON.stringify(thresholds));
      return postForm<InventoryAnalyzeResponse>(`/api/inventory/analyze`, form);
    },
    export: (file: File, sheet: string, mapping: object, thresholds: object) => {
      const form = new FormData();
      form.append("file", file);
      form.append("sheet", sheet);
      form.append("mapping", JSON.stringify(mapping));
      form.append("thresholds", JSON.stringify(thresholds));
      return postFormForBlob(`/api/inventory/export`, form);
    },
  },
  quotation: {
    inspectProducts: (file: File, sheet?: string) => {
      const form = new FormData();
      form.append("file", file);
      if (sheet) form.append("sheet", sheet);
      return postForm<QuotationProductsInspectResponse>(`/api/quotation/products/inspect`, form);
    },
    importProducts: (file: File, sheet: string, mapping: ProductColumnMapping) => {
      const form = new FormData();
      form.append("file", file);
      form.append("sheet", sheet);
      form.append("mapping", JSON.stringify(mapping));
      return postForm<QuotationProductsImportResponse>(`/api/quotation/products/import`, form);
    },
    generate: (payload: GenerateQuotationRequest) => postJsonForBlob(`/api/quotation/generate`, payload),
  },
};
