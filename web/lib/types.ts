// Shared request/response contract with the FastAPI backend (server/).

export interface ApiErrorDetail {
  message: string;
  error_type?: string;
}

export class ApiError extends Error {
  detail: ApiErrorDetail;
  status: number;
  constructor(status: number, detail: ApiErrorDetail) {
    super(detail.message);
    this.status = status;
    this.detail = detail;
  }
}

// ---------------------------------------------------------------- Comparator
export interface ComparatorInspectResponse {
  current_headers: string[];
  oms_headers: string[];
  current_row_count: number;
  oms_row_count: number;
  comparable_columns: string[];
}

export interface CellDifference {
  code: string;
  column: string;
  excel_row_index: number;
  old_value: unknown;
  new_value: unknown;
}

export interface ComparatorAnalyzeLegacyResponse {
  mode: "legacy";
  stats: {
    total_compared: number;
    total_differences: number;
    total_field_differences: number;
    new_codes_count: number;
    missing_from_oms_count: number;
    compared_columns: string[];
    duplicate_warnings: string[];
  };
  cell_differences_preview: CellDifference[];
  cell_differences_total_count: number;
}

// Kept as an alias - existing name, now precisely the legacy (single/same-
// name column) response shape returned when mode === "legacy".
export type ComparatorAnalyzeResponse = ComparatorAnalyzeLegacyResponse;

export interface ColumnMappingPair {
  current_column: string;
  latest_column: string;
}

export interface MappedFieldValue {
  current_column: string;
  latest_column: string;
  current_value: unknown;
  latest_value: unknown;
  changed: boolean;
  missing: boolean;
}

export interface MappedProductRow {
  code: string;
  excel_row_index: number;
  status: "changed" | "unchanged" | "added" | "removed";
  fields: MappedFieldValue[];
  changed_field_labels: string[];
}

export interface ComparatorAnalyzeMappedResponse {
  mode: "mapped";
  stats: {
    total_compared: number;
    total_changed: number;
    total_unchanged: number;
    total_added: number;
    total_removed: number;
    duplicate_warnings: string[];
    mappings: ColumnMappingPair[];
  };
  changed_preview: MappedProductRow[];
  changed_total_count: number;
  added_preview: MappedProductRow[];
  added_total_count: number;
  removed_preview: MappedProductRow[];
  removed_total_count: number;
}

export type ComparatorAnalyzeResult = ComparatorAnalyzeLegacyResponse | ComparatorAnalyzeMappedResponse;

// ---------------------------------------------------------------- Collection
export interface CollectionColumnMapping {
  customer: string | null;
  amount: string | null;
  days_overdue: string | null;
  due_date: string | null;
  last_payment_date: string | null;
  salesperson: string | null;
  invoice_number: string | null;
}

export interface CollectionThresholds {
  critical_days: number;
  high_days: number;
  medium_days: number;
  critical_amount: number;
  high_amount: number;
}

export interface InspectSheetResponse {
  sheet_names: string[];
  selected_sheet: string;
  headers: string[];
  row_count: number;
}

export interface CollectionInspectResponse extends InspectSheetResponse {
  suggested_mapping: CollectionColumnMapping;
}

export interface CustomerSummary {
  customer: string;
  total_outstanding: number;
  invoice_count: number;
  max_days_overdue: number;
  avg_days_overdue: number;
  oldest_due_date: string | null;
  salesperson: string | null;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "NORMAL";
}

export interface CollectionAnalyzeResponse {
  stats: {
    total_outstanding: number;
    total_customers: number;
    critical_count: number;
    high_count: number;
    critical_amount: number;
    high_priority_amount: number;
    amount_over_30: number;
    amount_over_60: number;
    amount_over_90: number;
  };
  customers_preview: CustomerSummary[];
  customers_total_count: number;
}

// ---------------------------------------------------------------- Inventory
export interface InventoryColumnMapping {
  code: string | null;
  description: string | null;
  unit: string | null;
  opening: string | null;
  received: string | null;
  delivered: string | null;
  balance: string | null;
  unit_cost: string | null;
  stock_value: string | null;
  brand: string | null;
  category: string | null;
}

export interface InventoryThresholds {
  fast_ratio: number;
  normal_ratio: number;
}

export interface InventoryInspectResponse extends InspectSheetResponse {
  suggested_mapping: InventoryColumnMapping;
}

export interface ProductMovement {
  code: string;
  description: unknown;
  unit: unknown;
  opening: number;
  received: number;
  delivered: number;
  balance: number;
  movement_ratio: number;
  classification: string;
  inventory_value: number | null;
  excel_row_index: number;
}

export interface StockException {
  code: string;
  reason: string;
  excel_row_index: number;
}

export interface InventoryAnalyzeResponse {
  stats: {
    total_products: number;
    counts: Record<string, number>;
    exceptions_count: number;
    has_value_data: boolean;
    total_inventory_value: number | null;
    value_no_movement: number | null;
    value_slow_moving: number | null;
  };
  products_preview: ProductMovement[];
  products_total_count: number;
  exceptions_preview: StockException[];
  exceptions_total_count: number;
}

// ---------------------------------------------------------------- Quotation
export interface ProductColumnMapping {
  product_name: string | null;
  price: string | null;
  code: string | null;
  description: string | null;
  brand: string | null;
  model: string | null;
  origin: string | null;
  category: string | null;
  warranty: string | null;
  mrp: string | null;
  image_path: string | null;
}

export interface ExcelPreviewRow {
  row: number;
  values: string[];
}

export interface QuotationProductsInspectResponse extends InspectSheetResponse {
  suggested_mapping: ProductColumnMapping;
  // First ~20 raw rows of the sheet, for the "confirm your header row"
  // preview - independent of whether a header row could be resolved yet.
  preview_rows: ExcelPreviewRow[];
  // The row automatic detection picked, for display, even when header_row
  // below reflects a manual override instead.
  detected_header_row: number | null;
  // The row actually used to build `headers`/`row_count`/`suggested_mapping`
  // - the manual override if one was sent, otherwise the detected row, or
  // null if neither is available (detection failed and no row was chosen
  // yet - never an error, just an empty/unresolved state).
  header_row: number | null;
  header_detected: boolean;
}

export interface QuotationImportedProduct {
  product_name: string;
  price: number;
  code: string;
  description: string;
  brand: string;
  model: string;
  origin: string;
  category: string;
  warranty: string;
  mrp: number;
  // Metadata only - a path/URL string as it appeared in the Excel. Never
  // resolved server-side (relative to the uploader's filesystem, not this
  // server); the browser offers to load it only when it's an http(s) URL.
  image_path: string;
}

export interface QuotationProductsImportResponse {
  products: QuotationImportedProduct[];
  products_total_count: number;
}

export interface QuotationCustomer {
  customer_name: string;
  contact_person: string;
  designation: string;
  company_name: string;
  address: string;
  phone: string;
  email: string;
  reference_number: string;
  notes: string;
}

export interface QuotationProposal {
  title: string;
  subject: string;
  quotation_date: string;
  validity: string;
  prepared_by: string;
  currency: string;
}

// Client-side working shape for a selected quotation line item - `id` is
// local only (React keys, edit/duplicate/delete) and never sent to the API.
export interface QuotationItem {
  id: string;
  product_name: string;
  price: number;
  quantity: number;
  code: string;
  description: string;
  brand: string;
  model: string;
  origin: string;
  category: string;
  warranty: string;
  mrp: number;
  discount_percent: number;
  discount_amount: number;
  image: string | null;
  features: string[];
  specifications: string[];
  installation_notes: string;
  additional_notes: string;
  accessories: string[];
  brochure_note: string;
}

export interface QuotationTotals {
  subtotal: number;
  discount: number;
  vat: number;
  grand_total: number;
}

export interface GenerateQuotationRequest {
  company_id: string;
  customer: QuotationCustomer;
  proposal: QuotationProposal;
  items: Omit<QuotationItem, "id">[];
}

// -------------------------------------------------------------------- Auth
export interface CurrentUser {
  id: string;
  username: string;
  fullName: string;
  role: "admin" | "staff";
  companyId: string;
}

export interface AuthStatusResponse {
  authenticated: boolean;
  user?: CurrentUser;
}

// ------------------------------------------------------------------- Users
export interface ManagedUser {
  id: string;
  username: string;
  fullName: string;
  role: "admin" | "staff";
  active: boolean;
  createdAt: string;
}

export interface CreateUserRequest {
  username: string;
  full_name: string;
  password: string;
  role: "admin" | "staff";
}

export interface UpdateUserRequest {
  full_name?: string;
  role?: "admin" | "staff";
  active?: boolean;
}

// ------------------------------------------------------------ Master Excel
export type ExcelSource = "upload" | "company_master";

export type MasterExcelMetadata =
  | { exists: false }
  | { exists: true; filename: string; uploadedAt: string; uploadedBy: string; fileSize: number };
