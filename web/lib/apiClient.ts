import {
  ApiError,
  type ApiErrorDetail,
  type AuditLogResponse,
  type AuthStatusResponse,
  type CollectionAnalyzeResponse,
  type CollectionInspectResponse,
  type ColumnMappingPair,
  type Company,
  type ComparatorAnalyzeResult,
  type ComparatorInspectResponse,
  type CreateCompanyRequest,
  type CreateUserRequest,
  type ExcelSource,
  type GenerateQuotationRequest,
  type InventoryAnalyzeResponse,
  type InventoryInspectResponse,
  type ManagedUser,
  type MasterExcelMetadata,
  type ProductColumnMapping,
  type QuotationHistoryFilters,
  type QuotationHistoryResponse,
  type QuotationProductsImportResponse,
  type QuotationProductsInspectResponse,
  type StaffSummaryEntry,
  type UpdateCompanyRequest,
  type UpdateUserRequest,
} from "./types";

async function readErrorDetail(res: Response): Promise<ApiErrorDetail> {
  let detail: ApiErrorDetail = { message: "An unexpected error occurred." };
  try {
    const body = await res.json();
    if (body?.detail) detail = body.detail;
  } catch {
    // response wasn't JSON - keep the generic message
  }
  return detail;
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(path, { method: "POST", body: form });
  if (!res.ok) {
    throw new ApiError(res.status, await readErrorDetail(res));
  }
  return res.json() as Promise<T>;
}

async function jsonRequest<T>(method: "GET" | "POST" | "PATCH" | "DELETE", path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await readErrorDetail(res));
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
    analyze: (currentFile: File, omsFile: File, columnMappings: ColumnMappingPair[]) => {
      const form = new FormData();
      form.append("current_file", currentFile);
      form.append("oms_file", omsFile);
      form.append("column_mappings", JSON.stringify(columnMappings));
      return postForm<ComparatorAnalyzeResult>(`/api/comparator/analyze`, form);
    },
    export: (currentFile: File, omsFile: File, columnMappings: ColumnMappingPair[]) => {
      const form = new FormData();
      form.append("current_file", currentFile);
      form.append("oms_file", omsFile);
      form.append("column_mappings", JSON.stringify(columnMappings));
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
    inspectProducts: (file: File | null, sheet?: string, headerRow?: number, excelSource: ExcelSource = "upload") => {
      const form = new FormData();
      form.append("excel_source", excelSource);
      if (file) form.append("file", file);
      if (sheet) form.append("sheet", sheet);
      if (headerRow != null) form.append("header_row", String(headerRow));
      return postForm<QuotationProductsInspectResponse>(`/api/quotation/products/inspect`, form);
    },
    importProducts: (
      file: File | null,
      sheet: string,
      mapping: ProductColumnMapping,
      headerRow?: number,
      excelSource: ExcelSource = "upload",
    ) => {
      const form = new FormData();
      form.append("excel_source", excelSource);
      if (file) form.append("file", file);
      form.append("sheet", sheet);
      form.append("mapping", JSON.stringify(mapping));
      if (headerRow != null) form.append("header_row", String(headerRow));
      return postForm<QuotationProductsImportResponse>(`/api/quotation/products/import`, form);
    },
    generate: (payload: GenerateQuotationRequest) => postJsonForBlob(`/api/quotation/generate`, payload),
  },
  masterExcel: {
    getMetadata: (companyId?: string) => {
      const qs = companyId ? `?company_id=${encodeURIComponent(companyId)}` : "";
      return jsonRequest<MasterExcelMetadata>("GET", `/api/master-excel${qs}`);
    },
    upload: async (file: File, companyId: string): Promise<MasterExcelMetadata> => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`/api/master-excel?company_id=${encodeURIComponent(companyId)}`, { method: "PUT", body: form });
      if (!res.ok) throw new ApiError(res.status, await readErrorDetail(res));
      return res.json() as Promise<MasterExcelMetadata>;
    },
    remove: (companyId: string) => jsonRequest<{ ok: true }>("DELETE", `/api/master-excel?company_id=${encodeURIComponent(companyId)}`),
    downloadUrl: (companyId: string) => `/api/master-excel/download?company_id=${encodeURIComponent(companyId)}`,
  },
  quotationHistory: {
    list: (filters: QuotationHistoryFilters = {}) => {
      const params = new URLSearchParams();
      if (filters.companyId) params.set("company_id", filters.companyId);
      if (filters.customer) params.set("customer", filters.customer);
      if (filters.quoteNumber != null) params.set("quote_number", String(filters.quoteNumber));
      if (filters.staffId) params.set("staff_id", filters.staffId);
      if (filters.dateFrom) params.set("date_from", filters.dateFrom);
      if (filters.dateTo) params.set("date_to", filters.dateTo);
      if (filters.page) params.set("page", String(filters.page));
      const qs = params.toString();
      return jsonRequest<QuotationHistoryResponse>("GET", `/api/quotation/history${qs ? `?${qs}` : ""}`);
    },
    downloadDocxUrl: (id: string, companyId?: string) =>
      `/api/quotation/history/${id}/download/docx${companyId ? `?company_id=${encodeURIComponent(companyId)}` : ""}`,
    downloadPdfUrl: (id: string, companyId?: string) =>
      `/api/quotation/history/${id}/download/pdf${companyId ? `?company_id=${encodeURIComponent(companyId)}` : ""}`,
  },
  audit: {
    staffSummary: (companyId: string) =>
      jsonRequest<{ staff: StaffSummaryEntry[] }>("GET", `/api/audit/staff-summary?company_id=${encodeURIComponent(companyId)}`),
    logs: (companyId: string, page: number = 1, staffId?: string) => {
      const params = new URLSearchParams({ company_id: companyId, page: String(page) });
      if (staffId) params.set("staff_id", staffId);
      return jsonRequest<AuditLogResponse>("GET", `/api/audit/logs?${params.toString()}`);
    },
  },
  auth: {
    login: (username: string, password: string) => jsonRequest<{ ok: true }>("POST", "/api/auth/login", { username, password }),
    logout: () => jsonRequest<{ ok: true }>("POST", "/api/auth/logout"),
    status: () => jsonRequest<AuthStatusResponse>("GET", "/api/auth/status"),
  },
  companies: {
    list: () => jsonRequest<{ companies: Company[] }>("GET", "/api/companies"),
    create: (payload: CreateCompanyRequest) => jsonRequest<Company>("POST", "/api/companies", payload),
    update: (companyId: string, payload: UpdateCompanyRequest) =>
      jsonRequest<Company>("PATCH", `/api/companies/${companyId}`, payload),
    remove: (companyId: string) => jsonRequest<{ ok: true }>("DELETE", `/api/companies/${companyId}`),
  },
  users: {
    list: (companyId: string) => jsonRequest<{ users: ManagedUser[] }>("GET", `/api/users?company_id=${encodeURIComponent(companyId)}`),
    create: (payload: CreateUserRequest) => jsonRequest<ManagedUser>("POST", "/api/users", payload),
    update: (userId: string, payload: UpdateUserRequest) => jsonRequest<ManagedUser>("PATCH", `/api/users/${userId}`, payload),
    resetPassword: (userId: string, companyId: string, newPassword: string) =>
      jsonRequest<{ ok: true }>("POST", `/api/users/${userId}/reset-password`, { company_id: companyId, new_password: newPassword }),
    remove: (userId: string, companyId: string) =>
      jsonRequest<{ ok: true }>("DELETE", `/api/users/${userId}?company_id=${encodeURIComponent(companyId)}`),
  },
};
